"""Controlled daily adapter for the two specifically reviewed Tianze models.

No .ipynb loading/eval occurs here. Only bundled, readable .py adapters are imported
after allow_run=True. Real Radiance remains an external dependency.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date, timedelta
import importlib
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import math
import shutil
import threading

import numpy as np
import pandas as pd

from legacy_bridge import ROOT, GroundGrid, fingerprint, save_json, sha256

_LOCK = threading.Lock()  # RadianceObj changes process cwd: never thread parallelise candidates.
KINDS = {"fixed": "tianze_fixed", "tracking": "tianze_tracking"}


def preflight():
    packages = {}
    for name in ("pcse", "bifacial-radiance", "pvlib", "numpy", "pandas"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    programs = {name: shutil.which(name) for name in ("rtrace", "oconv", "genbox", "xform", "gencumulativesky")}
    ready = all(packages[name] for name in ("bifacial-radiance", "pvlib")) and all(programs.values())
    return dict(radiance_ready=ready, packages=packages, programs=programs,
                note="PATH ; . ")


def get_defaults():
    # Parsed literals during artifact build; does not import/execute radiation code.
    import json
    return json.loads((ROOT / '05_Tianze_Files' / "Tianze_Defaults.json").read_text(encoding="utf-8"))


def _check_inputs(design, module_spec, array_spec, albedo, grid):
    numeric = [v for group in (design, module_spec, array_spec) for v in group.values()
               if isinstance(v, (float, int)) and not isinstance(v, bool)]
    if not all(math.isfinite(float(v)) for v in numeric):
        raise ValueError("Radiation inputs must be finite.")
    if not 0 <= albedo <= 1:
        raise ValueError("Albedo must be between 0 and 1.")
    for key in ("module_x", "module_y", "module_thickness", "xcell", "ycell"):
        if module_spec[key] <= 0:
            raise ValueError(f"{key}  must be positive.")
    for key in ("n_mods", "n_rows"):
        if type(array_spec[key]) is not int or array_spec[key] <= 0:
            raise ValueError(f"{key}  must be a positive integer.")
    for key in ("numcellsx", "numcellsy"):
        if type(module_spec[key]) is not int or module_spec[key] <= 0:
            raise ValueError(f"{key}  must be a positive integer.")
    for key in ("glass_total_transmittance", "glass_specular_reflectance", "glass_haze", "bifaciality"):
        if not 0 <= module_spec[key] <= 1:
            raise ValueError(f"{key}  must be between 0 and 1.")
    if module_spec["glass_total_transmittance"] + module_spec["glass_specular_reflectance"] > 1 + 1e-12:
        raise ValueError("Glass transmittance plus reflectance cannot exceed 1.")
    if module_spec["glass_specular_reflectance"] >= 1:
        raise ValueError(" trans  1. ")
    if design["pitch"] < module_spec["module_y"]:
        raise ValueError(" pitch ,  GCR. ")
    if min(design[k] for k in ("xcellgap", "ycellgap", "xgap_conventional")) < 0:
        raise ValueError("Cell and module gaps cannot be negative.")
    if "tilt" in design and (not 0 <= design["tilt"] <= 90 or design["clearance_height"] <= grid.z_m):
        raise ValueError("Tilt must be within 0-90 degrees; the module lower edge must be above the sampling plane.")
    grid.points()


def _read_exact_day(module, demo, scenario):
    """Retain exactly EPW hours 1..24, including next-day 00:00 right edge."""
    day = date.fromisoformat(scenario.start_date)
    if scenario.start_date != scenario.end_date:
        raise ValueError("The controlled radiation adapter computes one day per call.")
    mapped = day.replace(year=module.SETTINGS.reference_year)
    end = mapped + timedelta(days=1)
    met = demo.readWeatherFile(
        weatherFile=str(module.WEATHER_DIRECTORY / scenario.weather_filename),
        starttime=f"{mapped:%Y-%m-%d}_0100", endtime=f"{end:%Y-%m-%d}_0000",
        coerce_year=module.SETTINGS.reference_year, label="right")
    # Check the actual cumulative-sky input against the same 24 raw EPW records.
    sky = pd.read_csv(demo.gencumsky_metfile, sep=r"\s+", header=None)
    epw = pd.read_csv(module.WEATHER_DIRECTORY / scenario.weather_filename, skiprows=8, header=None)
    selected = epw[(epw[1] == day.month) & (epw[2] == day.day)]
    if len(selected) != 24 or len(sky) != 8760 or sky.shape[1] != 2:
        raise ValueError("Daily cumulative sky input requires 24 complete hours and an annual placeholder table of 8760 rows.")
    # Original Tianze code and bifacial_radiance -G weather files use GHI, DHI.
    if not np.allclose(sky.sum().to_numpy(float), selected[[13, 15]].sum().to_numpy(float), rtol=1e-5, atol=.05):
        raise ValueError(" EPW  GHI/DHI . , . ")
    return met


def _configure_capture(module, kind, grid, captured):
    """Extend only the ground readout; leave optics/geometry/angle-bin tracing intact."""
    scan, cell_area = grid.scan()
    count = len(grid.points())
    # All four scenarios now use the same fixed planted-area coordinate system.
    module.make_ground_projection_scan = lambda *args, **kwargs: (dict(scan), cell_area)
    module.make_shared_ground_scan = lambda *args, **kwargs: (dict(scan), cell_area)
    # Do not write Tianze's historical CSVs or reindex their columns.
    module.save_selected_results = lambda *args, **kwargs: None
    module.read_cultivation_weather = lambda demo, scenario: _read_exact_day(module, demo, scenario)
    if kind == "fixed":
        def analyze_ground(context, design, module_spec, array_spec, calculate_components, calculate_shading):
            if not calculate_components or calculate_shading:
                raise ValueError(" Linrui ,  Hao . ")
            analysis = module.br.AnalysisObj(context.total_octfile, context.simulation_name, hpc=module.SETTINGS.hpc)
            result = analysis.analysis(context.total_octfile, f"crop_daily_{context.pv_type}_{context.run_id}",
                                       scan, accuracy=module.SETTINGS.accuracy)
            total = np.asarray(result["Wm2"], dtype=float)
            direct = module.trace_direct_ground_irradiation(analysis, context.direct_octfile, scan)
            captured[context.pv_type] = dict(total=total.copy(), direct=direct.copy())
            return dict(ground_total_incident_energy_Wh_period=float(total.sum() * cell_area),
                        ground_direct_incident_energy_Wh_period=float(direct.sum() * cell_area),
                        ground_diffuse_incident_energy_Wh_period=float((total - direct).sum() * cell_area)), None
        module.analyze_ground = analyze_ground
    else:
        original = module.analyze_ground_at_angle
        def capture_angle(theta, context, ground_scan, calculate_components):
            total, direct = original(theta, context, ground_scan, calculate_components)
            arrays = captured.setdefault(context.pv_type, dict(total=np.zeros(count), direct=np.zeros(count)))
            arrays["total"] += total
            arrays["direct"] += direct
            return total, direct
        module.analyze_ground_at_angle = capture_angle


def run_tianze_daily(kind, days, grid: GroundGrid, *, design=None, module_spec=None, array_spec=None,
                      albedo=.20, epw_path=None, allow_run=False, accuracy="high"):
    """Real daily Radiance calls with checkpointing. One design yields both constructions.

    Returns a point/day DataFrame and its provenance. Never generates stand-in radiation.
    Safe default: do not import/run external radiation packages without allow_run=True.
    """
    if not allow_run:
        raise PermissionError(".  allow_run=True. ")
    if kind not in KINDS or accuracy not in ("low", "high"):
        raise ValueError("kind  fixed / tracking; accuracy  low / high. ")
    deps = preflight()
    if not deps["radiance_ready"]:
        raise RuntimeError("Radiance .  preflight();  Python  rtrace . ")
    defaults = get_defaults()[kind]
    design = dict(defaults["design"] if design is None else design)
    module_spec = dict(defaults["module"] if module_spec is None else module_spec)
    array_spec = dict(defaults["array"] if array_spec is None else array_spec)
    _check_inputs(design, module_spec, array_spec, albedo, grid)
    epw_path = Path(epw_path or ROOT / '03_Precipitation' / "Aachen_TMY_Weather.epw").resolve()
    if not epw_path.is_file() or epw_path.suffix.lower() != ".epw":
        raise ValueError(" EPW ,  Notebook . ")
    days = [pd.Timestamp(d).date() for d in days]
    if not days or sorted(set(days)) != days:
        raise ValueError("days , , . ")
    if any((d.month, d.day) == (2, 29) for d in days):
        raise ValueError("365  TMY  2  29 . ")
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError(" Python , Radiance . ")
    try:
        from handoff_loader import load_module
        module = load_module(KINDS[kind])
        # Restore reviewed defaults/functions when a notebook cell is rerun.
        module = importlib.reload(module)
        module.SETTINGS = replace(module.SETTINGS, accuracy=accuracy,
            ground_grid_x=grid.nx, ground_grid_y=grid.ny, ground_sensor_height=grid.z_m)
        module.WEATHER_DIRECTORY = epw_path.parent
        candidate = (module.PVDesign if kind == "fixed" else module.TrackingDesign)(**design)
        spec, array = module.ModuleSpecification(**module_spec), module.ArraySpecification(**array_spec)
        module.validate_cell_array_fit(candidate, spec)
        protocol = dict(adapter="tianze-daily-points-v1", kind=kind, design=design,
            module=module_spec, array=array_spec, albedo=albedo, grid=asdict(grid),
            tmy_reference_year=module.SETTINGS.reference_year, settings=asdict(module.SETTINGS),
            epw_sha256=sha256(epw_path), source_notebook_sha256=defaults["source_sha256"],
            extracted_model_sha256=sha256(module.__file__), bridge_sha256=sha256(__file__),
            radiance_binary_sha256={name: sha256(path) for name, path in deps.get("programs", {}).items() if path},
            dependencies=deps, crop_use="daily total shortwave; direct/diffuse retained for auditing only")
        key = fingerprint(protocol)
        cache = ROOT / '05_Tianze_Files' / "Radiation_Cache-" / key
        cache.mkdir(parents=True, exist_ok=True)
        save_json(cache / "Protocol-.json", protocol)
        batches, captured = [], {}
        _configure_capture(module, kind, grid, captured)
        points = grid.points()
        for number, day in enumerate(days, 1):
            path = cache / f"Day-_{day}.csv"
            checksum = cache / f"Day-_{day}.sha256"
            if path.exists() and checksum.exists() and checksum.read_text().strip() == sha256(path):
                batch = pd.read_csv(path)
                print(f"{kind} {number}/{len(days)} {day}: Using completed daily cache")
            else:
                captured.clear()
                scenario = module.CultivationScenario(scenario_name=f"crop_{kind}_{key[:12]}", crop_name="wheat",
                    start_date=str(day), end_date=str(day), weather_filename=epw_path.name, albedo=albedo)
                print(f"{kind} {number}/{len(days)} {day}:  Radiance( + )", flush=True)
                _, ground = module.model_for_optimization(candidate, scenario, spec, array,
                                                          calculate_linrui=True, calculate_hao=False)
                rows = []
                for pv_type in ("semi_transparent", "conventional"):
                    if pv_type not in captured or pv_type not in ground:
                        raise ValueError("Tianze  Linrui . ")
                    total, direct = captured[pv_type]["total"], captured[pv_type]["direct"]
                    if total.shape != (len(points),) or direct.shape != total.shape:
                        raise ValueError("Radiance Sampling point. ")
                    if not np.isfinite(total).all() or not np.isfinite(direct).all() or min(total.min(), direct.min()) < 0:
                        raise ValueError("Radiance /, , . ")
                    residual = total - direct
                    if (residual < 0).any():
                        raise ValueError("Total minus direct radiation is negative; check numerical precision and the direct component definition. Values are not automatically clipped.")
                    integrated = float(np.dot(total, points.cell_area_m2))
                    if not math.isclose(integrated, ground[pv_type]["ground_total_incident_energy_Wh_period"], rel_tol=1e-8, abs_tol=1e-6):
                        raise ValueError(" Linrui . ")
                    item = points.copy()
                    item.insert(0, "day", str(day))
                    item.insert(1, "scenario_id", f"{kind}_{pv_type}")
                    item["total_Wh_m2_day"] = total
                    item["direct_Wh_m2_day"] = direct
                    item["diffuse_residual_Wh_m2_day"] = residual
                    item["IRRAD_J_m2_day"] = total * 3600
                    rows.append(item)
                batch = pd.concat(rows, ignore_index=True)
                # Commit a complete day only. A checksum-less interrupted day is never reused.
                batch.to_csv(path, index=False, encoding="utf-8")
                checksum.write_text(sha256(path), encoding="ascii")
            batches.append(batch)
        result = pd.concat(batches, ignore_index=True)
        protocol.update(candidate_id=key, first_day=str(days[0]), last_day=str(days[-1]),
                        cached_directory=str(cache), radiation_data_sha256=fingerprint(result.to_dict("records")))
        return result, protocol
    finally:
        _LOCK.release()
