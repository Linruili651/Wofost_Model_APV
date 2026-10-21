from __future__ import annotations


from dataclasses import dataclass, asdict


from datetime import date, datetime, timezone


from pathlib import Path


from copy import deepcopy


from importlib.metadata import version


import csv


import hashlib


import json


import math


import os


import sys


from uuid import uuid4


import numpy as np


import pandas as pd


import yaml


ROOT = Path(__file__).resolve().parents[2]


ADAPTER_VERSION = "crop-bridge-1.0"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def replace_with_retry(source, destination, attempts=40, delay=0.05):
    """Replace a closed output file despite brief Windows reader/preview locks."""
    import time
    source, destination = Path(source), Path(destination)
    for attempt in range(attempts):
        try:
            return source.replace(destination)
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(min(delay * (attempt + 1), 0.25))


def save_json(path, value):
    def serializable(item):
        if isinstance(item, dict):
            return {str(k): serializable(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [serializable(v) for v in item]
        return item
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(serializable(value), ensure_ascii=False, indent=2, default=str, allow_nan=False)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    replace_with_retry(temporary,path)


def new_run(project):
    # A new folder for every run: never overwrite the official website's records.
    names = {"PP":"PP", "WLP_MLWB":"WLP_MLWB",
             "winter_wheat":"Winter_Wheat", "spring_barley":"Spring_Barley",
             "grain_maize":"Grain_Maize", "potato":"Potato",
             "sugar_beet":"Sugar_Beet", "soybean":"Soybean"}
    relative = Path(*[names.get(part, part) for part in str(project).split("/")])
    path = ROOT / '06_Hao_Interface_and_Rerun/Rerun_Results' / relative / ("Run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=False)
    return path


def load_pcse():
    if version("pcse") != "6.0.13":
        raise RuntimeError("Use pcse==6.0.13, matching the verified model version.")
    # Matches the website's isolated first-import behavior. Never change HOME.
    if "pcse" not in sys.modules:
        from unittest.mock import patch
        runtime = ROOT / '06_Hao_Interface_and_Rerun/Shared_Core' / "Runtime_Cache-"
        runtime.mkdir(parents=True, exist_ok=True)
        expanduser = os.path.expanduser
        with patch("os.path.expanduser", lambda p: str(runtime) if p == "~" else expanduser(p)):
            import pcse
    import pcse
    return pcse


@dataclass(frozen=True)
class CropConfig:
    # This is an explicit illustrative Aachen configuration, NOT a calibrated local trial.
    variety: str = "Winter_wheat_103"
    start: str = "2001-10-15"
    end: str = "2002-08-31"
    start_type: str = "sowing"
    accept_demo_assumptions: bool = False
    allow_missing_rain_for_pp: bool = False
    epw_wind_height_m: float = 10.0
    angstrom_a: float = .29
    angstrom_b: float = .49

    def dates(self):
        first, last = date.fromisoformat(self.start), date.fromisoformat(self.end)
        if last <= first or (last - first).days > 365:
            raise ValueError("The crop season must contain 2 to 366 days in chronological order.")
        days = list(pd.date_range(first, last).date)
        if any(d.month == 2 and d.day == 29 for d in days):
            raise ValueError(" TMY  365 ;  2  29 . ")
        if self.start_type not in ("sowing", "emergence"):
            raise ValueError("start_type  sowing() emergence(). ")
        if self.epw_wind_height_m not in (2.0, 10.0):
            raise ValueError(" 2 m  10 m → 2 m . ")
        return days


def read_epw_daily(path, config):
    """EPW hour 1..24 belongs to its printed month/day; never average a monthly total."""
    days = config.dates()
    path = Path(path)
    with path.open(encoding="utf-8-sig") as handle:
        loc = next(csv.reader(handle))
    if loc[0] != "LOCATION":
        raise ValueError("EPW  LOCATION . ")
    latitude, longitude, tz, elevation = map(float, loc[6:10])
    h = pd.read_csv(path, skiprows=8, header=None)
    if len(h) != 8760 or h.shape[1] < 35:
        raise ValueError(" 8760  EPW TMY, . ")
    fields = {"month": 1, "day": 2, "hour": 3, "temp": 6, "dew": 7,
              "ghi": 13, "dni": 14, "dhi": 15, "wind": 21, "rain": 33, "rain_period": 34}
    hourly = pd.DataFrame({name: pd.to_numeric(h[col], errors="raise") for name, col in fields.items()})
    if not np.isfinite(hourly.to_numpy()).all():
        raise ValueError("EPW . ")
    if ((hourly.temp >= 99.9) | (hourly.dew >= 99.9) | (hourly.wind >= 999) |
        (hourly[["ghi", "dni", "dhi"]] >= 9999).any(axis=1)).any():
        raise ValueError("EPW , , . ")
    if (hourly[["ghi", "dni", "dhi", "wind"]] < 0).any().any():
        raise ValueError("EPW . ")
    # Daily mean actual vapour pressure from hourly dewpoint (hPa).
    hourly["vap"] = 6.108 * np.exp(17.27 * hourly.dew / (hourly.dew + 237.3))
    grouped = {}
    for key, group in hourly.groupby(["month", "day"]):
        if sorted(group.hour.tolist()) != list(range(1, 25)):
            raise ValueError(f"{key}  has missing or duplicate hours.")
        valid_rain = bool(((group.rain < 999) & (group.rain >= 0) & (group.rain_period == 1)).all())
        grouped[key] = dict(TMIN=float(group.temp.min()), TMAX=float(group.temp.max()),
                            TEMP=float(group.temp.mean()), VAP=float(group.vap.mean()),
                            WIND=float(group.wind.mean()), IRRAD=float(group.ghi.sum()) * 3600,
                            DHI_Wh_m2_day=float(group.dhi.sum()),
                            RAIN_mm_day=float(group.rain.sum()) if valid_rain else None)
    records = []
    for day in days:
        if (day.month, day.day) not in grouped:
            raise ValueError(f"TMY  {day:%m-%d}. ")
        records.append(dict(day=day, LAT=latitude, LON=longitude, ELEV=elevation,
                            **grouped[(day.month, day.day)]))
    frame = pd.DataFrame(records)
    metadata = dict(epw_sha256=sha256(path), latitude=latitude, longitude=longitude,
                    elevation_m=elevation, time_zone_utc_offset=tz, weather_type="TMY, not observed 2001/2002",
                    rainfall_missing_days=int(frame.RAIN_mm_day.isna().sum()),
                    epw_wind_height_assumed_m=config.epw_wind_height_m,
                    vapour_pressure_method="mean of hourly dewpoint-derived vapour pressure")
    return frame, metadata


def _weather_provider(frame, config, radiation):
    load_pcse()
    from pcse.base import WeatherDataProvider, WeatherDataContainer
    from pcse.util import reference_ET, wind10to2
    missing = frame.RAIN_mm_day.isna().any()
    if missing and not config.allow_missing_rain_for_pp:
        raise ValueError("EPW .  PP , ; . ")
    values = np.asarray(radiation, dtype=float)
    if len(values) != len(frame) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("IRRAD , ,  J/m²/day. ")
    provider = WeatherDataProvider()
    provider.latitude, provider.longitude, provider.elevation = map(float, frame.iloc[0][["LAT", "LON", "ELEV"]])
    provider.description = ["Aachen EPW + reviewed daily radiation adapter; WOFOST72 PP only"]
    provider.angstA, provider.angstB = config.angstrom_a, config.angstrom_b
    for row, irrad in zip(frame.to_dict("records"), values):
        wind = wind10to2(row["WIND"]) if config.epw_wind_height_m == 10 else row["WIND"]
        e0, es0, et0 = reference_ET(row["day"], row["LAT"], row["ELEV"], row["TMIN"], row["TMAX"],
                                   float(irrad), row["VAP"], wind, config.angstrom_a, config.angstrom_b)
        provider._store_WeatherDataContainer(WeatherDataContainer(
            DAY=row["day"], LAT=row["LAT"], LON=row["LON"], ELEV=row["ELEV"],
            IRRAD=float(irrad), TMIN=row["TMIN"], TMAX=row["TMAX"], TEMP=row["TEMP"],
            VAP=row["VAP"], WIND=wind, E0=e0 / 10, ES0=es0 / 10, ET0=et0 / 10,
            RAIN=0.0 if pd.isna(row["RAIN_mm_day"]) else row["RAIN_mm_day"] / 10), row["day"])
    return provider


def validate_radiation(frame, radiation, scenario_id, grid):
    required = {"day", "scenario_id", "point_id", "x_m", "y_m", "cell_area_m2", "total_Wh_m2_day"}
    if not required.issubset(radiation.columns):
        raise ValueError(f"Missing radiation columns: {sorted(required - set(radiation.columns))};  Wh . ")
    selected = radiation[radiation.scenario_id == scenario_id].copy()
    if selected.empty:
        raise ValueError(f"Radiation table does not contain scenario  {scenario_id}. ")
    selected["day"] = pd.to_datetime(selected.day, errors="raise").dt.date
    if selected.duplicated(["day", "point_id"]).any():
        raise ValueError("Duplicate radiation record for the same point and date.")
    expected = grid.points()
    if set(selected.point_id) != set(expected.point_id):
        raise ValueError("Sampling points do not match the configured field.")
    expected_days = set(frame.day)
    for pid, group in selected.groupby("point_id"):
        if set(group.day) != expected_days:
            raise ValueError(f" {pid}  does not cover the configured crop season; 30 days cannot be extrapolated to a full season.")
        point = expected.loc[expected.point_id == pid].iloc[0]
        for key in ("x_m", "y_m", "cell_area_m2"):
            if not np.allclose(pd.to_numeric(group[key]), point[key], rtol=0, atol=1e-9):
                raise ValueError("A sampling point changed location or representative area; continuous simulation is invalid.")
    vals = selected[["total_Wh_m2_day", "cell_area_m2", "x_m", "y_m"]].to_numpy(float)
    if not np.isfinite(vals).all() or (selected.total_Wh_m2_day < 0).any():
        raise ValueError("Radiation must be finite and nonnegative; missing values cannot be replaced by 0.")
    if "direct_Wh_m2_day" in selected and "diffuse_residual_Wh_m2_day" in selected:
        components = selected[["direct_Wh_m2_day", "diffuse_residual_Wh_m2_day"]].to_numpy(float)
        if not np.isfinite(components).all() or (components < 0).any():
            raise ValueError("/,  Radiance , . ")
        if not np.allclose(components.sum(axis=1), selected.total_Wh_m2_day, atol=1e-6, rtol=1e-6):
            raise ValueError("Direct plus diffuse radiation does not equal total radiation.")
    return selected.sort_values(["point_id", "day"])


@dataclass(frozen=True)
class GroundGrid:
    # Common WORLD coordinates for all four PV scenarios; this is an explicit example plot.
    x_min: float = -16.0
    x_max: float = 16.0
    y_min: float = -16.0
    y_max: float = 16.0
    nx: int = 15
    ny: int = 15
    z_m: float = .05

    def points(self):
        if not all(math.isfinite(float(v)) for v in asdict(self).values()):
            raise ValueError("Field parameters must be finite.")
        if self.x_max <= self.x_min or self.y_max <= self.y_min or self.z_m <= 0:
            raise ValueError("Invalid field extent or sensor height.")
        if not isinstance(self.nx, int) or not isinstance(self.ny, int) or min(self.nx, self.ny) < 1:
            raise ValueError("Grid dimensions must be positive integers.")
        dx, dy = (self.x_max - self.x_min) / self.nx, (self.y_max - self.y_min) / self.ny
        # Matches AnalysisObj._linePtsMakeDict order: outer Nx, inner Ny (Nz=1).
        return pd.DataFrame([dict(point_id=f"p{i:03d}_{j:03d}", x_m=self.x_min + (i + .5) * dx,
                                  y_m=self.y_min + (j + .5) * dy, cell_area_m2=dx * dy)
                             for i in range(self.nx) for j in range(self.ny)])

    def scan(self):
        points = self.points()
        dx, dy = (self.x_max - self.x_min) / self.nx, (self.y_max - self.y_min) / self.ny
        return dict(xstart=float(points.iloc[0].x_m), ystart=float(points.iloc[0].y_m), zstart=self.z_m,
                    sx_xinc=dx, sx_yinc=0., sx_zinc=0., xinc=0., yinc=dy, zinc=0.,
                    Nx=self.nx, Ny=self.ny, Nz=1, orient="0 0 -1"), dx * dy
