"""Read the paired precipitation supplement without editing original EPW/bridge."""
import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path


def attach_precipitation(weather, epw_path, supplement_path, *, component):
    """Return copied weather + provenance. component must be 'liquid_rain'."""
    if component != "liquid_rain":
        raise ValueError("This adapter supports liquid_rain only; snowmelt is not implemented.")
    epw_path = Path(epw_path)
    data = json.loads(Path(supplement_path).read_text(encoding="utf-8"))
    if hashlib.sha256(epw_path.read_bytes()).hexdigest() != data["source_epw_sha256"]:
        raise ValueError("Supplement belongs to a different EPW file.")
    lookup = {}
    with epw_path.open(encoding="utf-8-sig") as stream:
        epw_rows = list(csv.reader(stream))
    years = {}
    for row in epw_rows[8:]:
        month, year = int(row[1]), int(row[0])
        if month in years and years[month] != year:
            raise ValueError("EPW month contains inconsistent source years.")
        years[month] = year
    for row in data["records"]:
        key = row["month_day"]
        source = date.fromisoformat(row["source_date"])
        rain = row["rain_mm_day"]
        if key in lookup or source.strftime("%m-%d") != key or source.year != years[source.month]:
            raise ValueError("Duplicate or mismatched source date.")
        if rain is None or not math.isfinite(rain) or rain < 0:
            raise ValueError("Missing or invalid liquid rainfall.")
        lookup[key] = row
    expected = {date(2001, m, d).strftime("%m-%d")
                for m in range(1, 13) for d in range(1, __import__("calendar").monthrange(2001, m)[1]+1)}
    if set(lookup) != expected:
        raise ValueError("Supplement must cover exactly 365 non-leap days.")
    result = weather.copy(deep=True)
    keys = [day.strftime("%m-%d") for day in result.day]
    if any(key not in lookup for key in keys):
        raise ValueError("Unsupported or missing model day (including February 29).")
    if result.day.duplicated().any():
        raise ValueError("Duplicate weather date.")
    result["RAIN_mm_day"] = [lookup[key]["rain_mm_day"] for key in keys]
    result["precipitation_source_date"] = [lookup[key]["source_date"] for key in keys]
    metadata = dict(rainfall_missing_days=0, rainfall_component="liquid rain only; snowmelt excluded",
                    rainfall_source_url=data["source_url"], rainfall_daily_timezone=data["daily_timezone"],
                    rainfall_status=data["status"], rainfall_grid=data["returned_grid"],
                    rainfall_supplement_sha256=hashlib.sha256(Path(supplement_path).read_bytes()).hexdigest(),
                    rainfall_limitations=data["limitations"])
    return result, metadata
