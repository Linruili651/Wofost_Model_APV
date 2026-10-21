# READ-ONLY SOURCE EXPORT for interface inspection. Final cells may run simulations.
# Extracted without executing the original notebook.
# Cell 1: Imports, external tools, and project folders

# Standard-library imports.
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import os
import subprocess
import sys

# Third-party imports.
import numpy as np
import pandas as pd
import pvlib
import bifacial_radiance as br


# Add the executables used by bifacial_radiance to the current environment.
def configure_external_tools() -> None:
    bundled_data = Path(br.__file__).resolve().parent / "data"
    radiance_roots = (
        Path("/usr/local/radiance"),
        Path("/opt/homebrew/opt/radiance"),
        Path.home() / "Radiance",
    )
    native_bins = [root / "bin" for root in radiance_roots if (root / "bin").exists()]

    # On macOS, prefer installed native executables over bundled Linux binaries.
    executable_folders = native_bins if sys.platform == "darwin" else [bundled_data, *native_bins]
    os.environ["PATH"] = os.pathsep.join(
        [*(str(folder) for folder in executable_folders), os.environ.get("PATH", "")]
    )

    # Radiance searches RAYPATH for its support libraries.
    radiance_libraries = [
        root / "lib"
        for root in radiance_roots
        if (root / "lib").exists()
    ]
    if radiance_libraries:
        os.environ["RAYPATH"] = os.pathsep.join(
            [*(str(folder) for folder in radiance_libraries), "."]
        )


# Resolve this cross-platform project layout:
# AgriPV/notebooks/single_axis.ipynb
# AgriPV/weather/user_weather_file.epw
# AgriPV/results/Linrui_single_axis_scenarios.csv
# AgriPV/results/Hao_single_axis_hourly_scenarios.csv
WORKING_DIRECTORY = Path.cwd().resolve()
PROJECT_ROOT = (
    WORKING_DIRECTORY.parent
    if WORKING_DIRECTORY.name.lower() == "notebooks"
    else WORKING_DIRECTORY
)
WEATHER_DIRECTORY = PROJECT_ROOT / "weather"
RESULTS_DIRECTORY = PROJECT_ROOT / "results"
LINRUI_RESULTS_FILE = RESULTS_DIRECTORY / "Linrui_single_axis_scenarios.csv"
HAO_RESULTS_FILE = RESULTS_DIRECTORY / "Hao_single_axis_hourly_scenarios.csv"
configure_external_tools()

# Cell 2: Input structures used by the single-axis comparison model

# Human-readable scenario label, crop, cultivation period, weather, and ground grid.
@dataclass(frozen=True)
class CultivationScenario:
    scenario_name: str
    crop_name: str
    start_date: str
    end_date: str
    weather_filename: str
    ground_grid_x: int
    ground_grid_y: int
    weather_time_basis: str = "pvgis_utc"


# Shared envelope, semi-transparent cells/glass, and independent bifacialities.
@dataclass(frozen=True)
class ModuleSpecification:
    name: str
    module_x: float
    module_y: float
    module_thickness: float
    numcellsx: int
    numcellsy: int
    xcell: float
    ycell: float
    bifaciality: float
    conventional_bifaciality: float
    glass_total_transmittance: float
    glass_specular_reflectance: float
    glass_haze: float


# Number of modules in each row and number of rows, shared by both constructions.
@dataclass(frozen=True)
class ArraySpecification:
    n_mods: int
    n_rows: int


# Candidate variables supplied by Hao's optimizer for the single-axis array.
@dataclass(frozen=True)
class TrackingDesign:
    pitch: float
    axis_azimuth: float
    hub_height: float
    limit_angle: float
    backtrack: bool
    xcellgap: float
    ycellgap: float
    xgap_conventional: float


# Numerical settings kept constant within one optimization study.
@dataclass(frozen=True)
class ModelSettings:
    # Fixed broadband ground reflectance; no seasonal, snow, or crop-stage changes.
    ground_albedo: float = 0.20
    xgap_semi_transparent: float = 0.0
    ground_border_m: float = 1.0
    ground_sensor_height: float = 0.05
    conventional_surface_offset: float = 0.005
    accuracy: str = "low"
    hpc: bool = True
    n_workers: int = max(1, (os.cpu_count() or 1) // 2)


# Handles for all angle scenes belonging to one temporary construction.
@dataclass
class TrackingSimulationContext:
    run_id: str
    pv_type: str
    simulation_name: str
    trackerdict: dict


# Cell 3: Inputs edited by Linrui and Hao

# Before running, check: all numeric inputs must be finite (no NaN or infinity).
# Counts must be positive integers; dimensions positive; gaps nonnegative.
# Glass inputs and bifacialities must be in [0, 1]; transmittance + reflectance <= 1.
# Existing fit, period and collision checks do not replace these user checks.
# Input labels used below:
# BOTH/physics = affects both people's irradiation calculations.
# BOTH/record = identifies both CSV rows but does not alter ray tracing.
# HAO/design = a candidate design variable normally supplied by Hao's optimizer.
# HAO/output or LINRUI/physics = primarily owned by that named output.
# Every field must keep its stated Python type. For an unused numeric field, use
# the suggested valid placeholder; never enter arbitrary letters or symbols.

# BOTH/numerics: choose exactly "low" (faster) or "high" (more ray-tracing effort).
# Shared by both constructions, Hao's PV scans and Linrui's total-light scans.
# Does not change sensor counts or time steps. The direct-only scan keeps its
# separate no-diffuse-bounce settings for direct/diffuse separation.
SETTINGS = ModelSettings(
    accuracy="low",  # User-defined; recorded in both result CSVs.
)

# LINRUI/output switch; Hao may leave False. Both switches False runs nothing.
GET_LINRUI_GROUND_IRRADIATION = False
# HAO/output switch; Linrui may leave False.
GET_HAO_ARRAY_RESULTS = False

# Put this EPW file inside AgriPV/weather/ and enter only its file name here.
# This Aachen EPW matches PVGIS 5.3 TMY built from 2005-2023 candidates.
# Reuse typical weather on the actual dates below; this is NOT a weather forecast.
# Use YYYY-MM-DD for complete days, or YYYY-MM-DD HH:00 for hourly bounds.
# An explicit end time is EXCLUSIVE: 15:00 to 17:00 contains two hours.
# Use EPW local standard time (no DST); write explicit years for winter seasons.
# If the weather data changes, use a new file name rather than silently replacing
# an existing file with different data under the same name.
scenario = CultivationScenario(
    scenario_name="Aachen_Crop_A_single_axis_001",  # BOTH/record: unique case label.
    crop_name="Crop_A",  # BOTH/record: retained for crop linkage; no ray-tracing effect.
    start_date="2024-03-01",  # BOTH/physics: inclusive date or whole-hour start.
    end_date="2024-03-30",  # BOTH/physics: full final day, or exclusive whole-hour end.
    weather_filename="Aachen_PVGIS_TMY.epw",  # BOTH/physics: EPW inside weather/.
    weather_time_basis="pvgis_utc",  # BOTH/physics: audited PVGIS UTC row order.
    # For ordinary EPW with genuine local-standard-time rows, use "local_standard".
    ground_grid_x=15,  # LINRUI/physics: positive integer; ground-grid columns.
    ground_grid_y=15,  # LINRUI/physics: positive integer; ground-grid rows; total sensors = x * y.
)

# Enter the shared outer module dimensions and semi-transparent cell layout.
# Enter each construction's rear/front response ratio independently, from 0 to 1.
# The 0.80 values below are examples, not verified module datasheet values.
# Set a construction's bifaciality to 0 for monofacial PV; its rear scan is skipped.
# The conventional scene uses the envelope, cell counts, and its own bifaciality;
# it ignores cell sizes, cell gaps, and all glass inputs as physical construction data.
# Glass values below are illustrative assumptions, not verified LONGi data.
# Supply whole-pane properties for the intended glass thickness: one optical
# sheet represents them. Changing thickness alone does not recompute optics.
module_specification = ModuleSpecification(
    name="LONGi_LR5_72HGD",  # BOTH/record: module identifier.
    module_x=1.134,  # BOTH/physics: outer width along the tracker axis, metres.
    module_y=2.278,  # BOTH/physics: rotating chord across rows, metres.
    module_thickness=0.030,  # BOTH/geometry: nominal envelope/opaque thickness (m); not glass absorption length.
    numcellsx=6,  # BOTH/physics: cell and conventional integration columns.
    numcellsy=24,  # BOTH/physics: cell and conventional integration rows.
    xcell=0.182,  # BOTH/physics: semi-transparent cell width, metres.
    ycell=0.091,  # BOTH/physics: semi-transparent cell length, metres.
    bifaciality=0.80,  # HAO/output: semi-transparent rear/front response; no ground-light effect.
    conventional_bifaciality=0.80,  # HAO/output: conventional rear/front response; 0 = monofacial.
    glass_total_transmittance=0.88,  # BOTH/physics: whole-pane total transmittance (constant coefficient), 0 to 1.
    glass_specular_reflectance=0.08,  # BOTH/physics: whole-pane specular reflectance (constant coefficient), 0 to 1.
    glass_haze=0.20,  # BOTH/physics: approximate diffuse share of whole-pane transmission, 0 to 1.
)

# Enter the array size once. Hao's optimizer can replace these integers per candidate.
array_specification = ArraySpecification(
    n_mods=5,  # HAO/design and BOTH/physics: modules in each row.
    n_rows=5,  # HAO/design and BOTH/physics: number of tracker rows.
)

# The optimizer replaces these single-axis candidate values for each comparison.
# `axis_azimuth` is the compass bearing of the tracker torque tube, not the
# time-varying module-facing azimuth. `hub_height` is the rotation-axis height.
# GCR is not entered independently; the model derives GCR = module_y / pitch.
candidate_design = TrackingDesign(
    pitch=7.0,  # HAO/design and BOTH/physics: row-centre spacing, metres.
    axis_azimuth=180.0,  # HAO/design and BOTH/physics: tracker-axis bearing, degrees.
    hub_height=3.0,  # HAO/design and BOTH/physics: torque-tube height, metres.
    limit_angle=45.0,  # HAO/design and BOTH/physics: symmetric rotation limit, ±degrees.
    backtrack=True,  # HAO/design and BOTH/physics: enable row-shading backtracking.
    xcellgap=0.0004,  # HAO/design: semi-transparent horizontal cell gap, metres.
    ycellgap=0.00235,  # HAO/design: semi-transparent vertical cell gap, metres.
    xgap_conventional=0.20,  # HAO/design: conventional inter-module gap, metres.
)

# Cell 4: Geometry, tracker, calendar, and optical validation

# Calculate the active-cell grid used for fit checks and sensor placement.
def module_geometry(
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> dict:
    grid_x = (
        module_spec.numcellsx * module_spec.xcell
        + (module_spec.numcellsx - 1) * design.xcellgap
    )
    grid_y = (
        module_spec.numcellsy * module_spec.ycell
        + (module_spec.numcellsy - 1) * design.ycellgap
    )
    return {
        "cell_module": {
            "numcellsx": module_spec.numcellsx,
            "numcellsy": module_spec.numcellsy,
            "xcell": module_spec.xcell,
            "ycell": module_spec.ycell,
            "xcellgap": design.xcellgap,
            "ycellgap": design.ycellgap,
        },
        "grid_x": grid_x,
        "grid_y": grid_y,
    }


# Stop before Radiance if the physical cells exceed the outer module envelope.
def validate_cell_array_fit(
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> None:
    geometry = module_geometry(design, module_spec)
    tolerance_m = 1.0e-9
    overflow_axes = [
        axis for axis in ("x", "y")
        if geometry[f"grid_{axis}"] > getattr(module_spec, f"module_{axis}") + tolerance_m
    ]
    if not overflow_axes:
        return

    direction = (
        "both x and y directions"
        if len(overflow_axes) == 2
        else f"the {overflow_axes[0]} direction"
    )
    print(f"ERROR: The semi-transparent cell array exceeds the module in {direction}.")
    for axis in overflow_axes:
        print(
            f"{axis} direction: cell array = {geometry[f'grid_{axis}']:.6f} m, "
            f"module = {getattr(module_spec, f'module_{axis}'):.6f} m."
        )
    print("Reduce the corresponding cell size, cell count, or cell gap in Cell 3.")
    raise ValueError(
        "Invalid semi-transparent module geometry; Radiance was not started "
        "and no result was appended to either CSV file."
    )


# Preserve actual calendar years and support winter periods across New Year.
def cultivation_period_bounds(scenario):
    end_text = str(scenario.end_date).strip()
    start = pd.Timestamp(scenario.start_date)
    end = pd.Timestamp(end_text)
    if pd.isna(start) or pd.isna(end):
        raise ValueError("Enter valid start_date and end_date in Cell 3.")
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError("Use dates/times without a timezone; the EPW supplies standard time.")
    if start != start.floor("h") or end != end.floor("h"):
        raise ValueError("Period endpoints must be whole hours; subhourly intervals are not modelled.")
    # Retain the previous same-year winter wrap, but never wrap reversed hours
    # within one day into an unintended year-long simulation.
    if end.date() < start.date() and end.year == start.year:
        end = end.replace(year=end.year + 1)
    if len(end_text) == 10 and end_text[4] == "-" and end_text[7] == "-":
        end += pd.Timedelta(days=1)  # Date-only end includes that entire day.
    if end <= start:
        raise ValueError("The exclusive end must be later than the start.")
    return start, end


# Validate all shared and tracking inputs before creating temporary or CSV files.
def validate_model_inputs(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> float:
    validate_cell_array_fit(design, module_spec)

    # Validate the discrete geometry and requested period.
    if array_spec.n_mods < 1 or array_spec.n_rows < 1:
        raise ValueError("n_mods and n_rows must both be positive integers.")
    if module_spec.numcellsx < 1 or module_spec.numcellsy < 1:
        raise ValueError("numcellsx and numcellsy must both be positive integers.")
    cultivation_period_bounds(scenario)
    weather_path = WEATHER_DIRECTORY / scenario.weather_filename
    if not weather_path.is_file():
        raise FileNotFoundError(
            f"Weather file not found: {weather_path}. Put it inside AgriPV/weather/."
        )

    # Validate scalar physical and optical values.
    positive_dimensions = {
        "module_x": module_spec.module_x,
        "module_y": module_spec.module_y,
        "module_thickness": module_spec.module_thickness,
        "xcell": module_spec.xcell,
        "ycell": module_spec.ycell,
        "pitch": design.pitch,
        "hub_height": design.hub_height,
    }
    invalid_dimensions = [name for name, value in positive_dimensions.items() if value <= 0]
    if invalid_dimensions:
        raise ValueError(f"These dimensions must be positive: {', '.join(invalid_dimensions)}.")
    if min(design.xcellgap, design.ycellgap, design.xgap_conventional) < 0:
        raise ValueError("Cell gaps and xgap_conventional cannot be negative.")
    if not 0.0 < design.limit_angle <= 90.0:
        raise ValueError("limit_angle must be greater than 0 and at most 90 degrees.")
    if not isinstance(design.backtrack, (bool, np.bool_)):
        raise TypeError("backtrack must be True or False.")
    if not 0.0 <= module_spec.bifaciality <= 1.0:
        raise ValueError("bifaciality must be between 0 and 1.")
    if not 0.0 <= module_spec.conventional_bifaciality <= 1.0:
        raise ValueError("conventional_bifaciality must be between 0 and 1.")

    optical_values = {
        "glass_total_transmittance": module_spec.glass_total_transmittance,
        "glass_specular_reflectance": module_spec.glass_specular_reflectance,
        "glass_haze": module_spec.glass_haze,
    }
    invalid_optics = [name for name, value in optical_values.items() if not 0.0 <= value <= 1.0]
    if invalid_optics:
        raise ValueError(f"These glass inputs must be between 0 and 1: {', '.join(invalid_optics)}.")
    if module_spec.glass_specular_reflectance >= 1.0:
        raise ValueError("glass_specular_reflectance must be below 1 for this transmitting-glass model.")
    if (
        module_spec.glass_total_transmittance
        + module_spec.glass_specular_reflectance
        > 1.0 + 1.0e-12
    ):
        raise ValueError("glass_total_transmittance + glass_specular_reflectance cannot exceed 1.")

    # Derive GCR from one geometric source of truth instead of asking for it twice.
    gcr = module_spec.module_y / design.pitch
    if not 0.0 < gcr <= 1.0:
        raise ValueError(
            "Derived GCR = module_y / pitch must be in (0, 1]. Increase pitch "
            "or reduce the rotating module chord."
        )

    # Check the lowest point of the rotating rectangular module over ±limit_angle.
    critical_angle = degrees(atan2(module_spec.module_y, module_spec.module_thickness))
    clearance_angle = min(design.limit_angle, critical_angle)
    vertical_half_extent = 0.5 * (
        module_spec.module_y * sin(radians(clearance_angle))
        + module_spec.module_thickness * cos(radians(clearance_angle))
    )
    minimum_clearance = design.hub_height - vertical_half_extent
    if minimum_clearance <= SETTINGS.ground_sensor_height:
        raise ValueError(
            "The tracker can intersect the ground/sensor plane. Increase hub_height "
            "or reduce module_y, module_thickness, or limit_angle."
        )

    return gcr


# Represent whole-pane optics once; no duplicate glass box or edge strips.
def equivalent_glass_text(
    module_name: str,
    glass_material_name: str,
    module_spec: ModuleSpecification,
    cell_thickness: float,
) -> str:
    # One two-sided optical sheet represents the complete pane, including margins.
    # Put it inside the opaque cell bodies, not on either cell face: cells still
    # block light, while every unobstructed gap ray crosses the glass only once.
    centre_x = round(module_spec.xcell / 2, 6) if module_spec.numcellsx % 2 == 0 else 0.0
    x0, x1 = centre_x - module_spec.module_x / 2, centre_x + module_spec.module_x / 2
    y0, y1 = -module_spec.module_y / 2, module_spec.module_y / 2
    z = cell_thickness / 2
    return (
        f"{glass_material_name} polygon {module_name}_equivalent_glass\n"
        "0\n0\n12\n"
        f"{x0:.12g} {y0:.12g} {z:.12g}\n"
        f"{x1:.12g} {y0:.12g} {z:.12g}\n"
        f"{x1:.12g} {y1:.12g} {z:.12g}\n"
        f"{x0:.12g} {y1:.12g} {z:.12g}\n"
    )

# Ground sensor resolution is user-selectable; never accept zero or fractional counts.
def validate_ground_grid(scenario: CultivationScenario) -> None:
    for name in ("ground_grid_x", "ground_grid_y"):
        value = getattr(scenario, name)
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer in Cell 3.")


def centred_scene_origin(module, pv_type, module_spec, array_spec, pitch, azimuth):
    # Centre the physical envelope at world (0, 0), for odd/even array sizes.
    azimuth = np.radians(round(float(azimuth), 2))
    u = np.array([-np.cos(azimuth), np.sin(azimuth)])
    v = np.array([-np.sin(azimuth), -np.cos(azimuth)])
    cell_shift = (round(module_spec.xcell / 2, 6)
                  if pv_type == "semi_transparent" and module_spec.numcellsx % 2 == 0 else 0.0)
    centre_u = ((array_spec.n_mods + 1) / 2 - round(array_spec.n_mods / 1.999)) * module.scenex + cell_shift
    centre_v = ((array_spec.n_rows + 1) / 2 - round(array_spec.n_rows / 1.999)) * pitch
    origin = -centre_u * u - centre_v * v
    return dict(originx=float(origin[0]), originy=float(origin[1]))


# Cell 5: Shared actual-year weather, hourly solar skies, and module materials

def add_hazy_glass_material(
    demo: br.RadianceObj,
    module_spec: ModuleSpecification,
    material_name: str,
) -> None:
    # Constant, grey whole-pane coefficients: regular + Lambertian transmission.
    # BRTDfunc avoids trans's additional Fresnel rescaling of these coefficients.
    # Both sides share the same optics; no bulk refraction or path-length loss.
    transmission = module_spec.glass_total_transmittance
    reflection = module_spec.glass_specular_reflectance
    regular = transmission * (1.0 - module_spec.glass_haze)
    diffuse = transmission * module_spec.glass_haze
    material_text = (
        f"void BRTDfunc {material_name}\n"
        f"10 {reflection:.10g} {reflection:.10g} {reflection:.10g} "
        f"{regular:.10g} {regular:.10g} {regular:.10g} 0 0 0 .\n"
        "0\n"
        f"9 0 0 0 0 0 0 {diffuse:.10g} {diffuse:.10g} {diffuse:.10g}\n"
    )
    material_file = Path("materials") / f"{material_name}.rad"
    material_file.write_text(material_text, encoding="ascii")
    demo.materialfiles.append(str(material_file))


def read_hourly_cultivation_weather(demo, scenario):
    # A non-leap reference is used ONLY to index the 8760 source weather records.
    # Solar positions are calculated separately on the actual requested dates.
    weather_path = WEATHER_DIRECTORY / scenario.weather_filename
    raw, metadata = demo._readEPW(
        epwfile=str(weather_path), label="right", coerce_year=2001,
    )
    with weather_path.open(encoding="utf-8-sig") as handle:
        header = [next(handle) for _ in range(8)]
    offset_line = next((line for line in header if "Irradiance Time Offset (h):" in line), None)
    offset_h = float(offset_line.split(":", 1)[1]) if offset_line else -0.5

    if scenario.weather_time_basis == "pvgis_utc":
        if offset_line is None:
            raise ValueError("pvgis_utc requires the PVGIS irradiance offset in COMMENTS 2.")
        # Audited PVGIS export: row hour 1 contains JSON 00:00 UTC values.
        # Interpret its row labels in UTC FIRST, then convert to EPW standard time.
        # Do not apply this reinterpretation to an ordinary local-time EPW.
        raw.index = raw.index.tz_localize(None).tz_localize("UTC").tz_convert(raw.index.tz)
    elif scenario.weather_time_basis != "local_standard":
        raise ValueError("weather_time_basis must be 'pvgis_utc' or 'local_standard'.")

    start, end = cultivation_period_bounds(scenario)
    hour_starts = pd.date_range(
        start, end, freq="h", inclusive="left", tz=raw.index.tz,
    )
    # TMY recycling is by LOCAL month/day/hour, after the source time conversion.
    source_keys = pd.Index((raw.index - pd.Timedelta(hours=1)).strftime("%m-%d-%H"))
    target_keys = hour_starts.strftime("%m-%d-%H").to_numpy(copy=True)
    leap_mask = (hour_starts.month == 2) & (hour_starts.day == 29)
    # Explicit agreed convention: repeat Feb 28 weather, not its solar position.
    target_keys[leap_mask] = hour_starts[leap_mask].strftime("02-28-%H")
    if not source_keys.is_unique:
        raise ValueError("The source EPW must contain exactly one record per TMY hour.")
    positions = source_keys.get_indexer(target_keys)
    if (positions < 0).any():
        raise ValueError("The source EPW does not contain all required TMY month/day/hour records.")
    selected = raw.iloc[positions].copy()
    selected.index = hour_starts + pd.Timedelta(hours=1)
    # Both Hao and Linrui use the same actual-year irradiance sampling instants.
    sampling_times = selected.index + pd.Timedelta(hours=offset_h)
    solar = pvlib.solarposition.get_solarposition(
        sampling_times, metadata["latitude"], metadata["longitude"], metadata["altitude"],
    )
    # Reusing typical weather may put small historical DNI at a below-horizon
    # target-year instant. Suppress that nonphysical beam; retain measured DHI.
    below_horizon = solar["elevation"].to_numpy() <= 0
    suppressed_beam_hours = int(((selected["DNI"].to_numpy() > 0) & below_horizon).sum())
    selected.loc[below_horizon, "DNI"] = 0.0
    # GHI is re-derived for the target-year geometry. gendaylit consumes DNI/DHI.
    selected["GHI"] = selected["DHI"].to_numpy() + selected["DNI"].to_numpy() * np.maximum(
        0.0, np.sin(np.radians(solar["elevation"].to_numpy())),
    )
    lit = selected["GHI"].to_numpy() > 0
    metdata = br.MetObj(selected, metadata, label="right") if lit.any() else None
    if metdata is not None:
        # Override the wrapper's default midpoint/sunrise adjustment.
        metdata.solpos = solar.iloc[np.flatnonzero(lit)].copy()
        metdata.sunrisesetdata["corrected_timestamp"] = pd.Series(
            sampling_times[lit], index=metdata.sunrisesetdata.index,
        )
    timing = {
        "weather_time_basis": scenario.weather_time_basis,
        "irradiance_offset_from_hour_end_h": offset_h,
        "leap_day_weather": "repeat_Feb28",
        "leap_day_reused_hours": int(leap_mask.sum()),
        "below_horizon_dni_suppressed_hours": suppressed_beam_hours,
        "solar_position_start_year": start.year,
        "weather_scenario": "TMY_representative_weather_not_forecast",
    }
    print(f"Solar period: [{start.isoformat()}, {end.isoformat()}); TMY weather, not a forecast.")
    print(f"Weather clock: {scenario.weather_time_basis}; irradiance offset = {offset_h:g} h from hour end.")
    if leap_mask.any():
        print("February 29: reused February 28 weather; solar position uses the actual leap day.")
    if suppressed_beam_hours:
        print(f"Suppressed historical DNI below the target-year horizon: {suppressed_beam_hours} hours.")
    return hour_starts, sampling_times, metdata, timing


def make_hourly_sky(demo, metdata, timeindex):
    # Full-spectrum solar sky. Never infer a replacement sun angle from old GHI.
    sun_elevation = float(metdata.solpos.iloc[timeindex]["elevation"])
    if sun_elevation <= 0:
        # Diffuse twilight: isotropic upper sky, no below-horizon direct sun.
        # This is an explicit approximation for positive DHI at twilight.
        dhi = float(metdata.dhi[timeindex])
        albedo = float(demo.ground.ReflAvg[0])
        skyfile = Path("skies") / f"twilight_{timeindex}.rad"
        skyfile.write_text(
            f"void glow twilight_sky\n0\n0\n4 {dhi / np.pi} {dhi / np.pi} {dhi / np.pi} 0\n"
            "twilight_sky source sky\n0\n0\n4 0 0 1 180\n"
            f"void glow twilight_ground\n0\n0\n4 {albedo*dhi/np.pi} {albedo*dhi/np.pi} {albedo*dhi/np.pi} 0\n"
            "twilight_ground source ground\n0\n0\n4 0 0 -1 180\n"
            f"void plastic ground_mat\n0\n0\n5 {albedo} {albedo} {albedo} 0 0\n"
            "ground_mat ring groundplane\n0\n0\n8 0 0 -.01 0 0 1 0 100\n",
            encoding="ascii",
        )
        return str(skyfile)
    # The installed wrapper skips DHI=0; epsilon preserves a direct-only hour.
    original_dhi = metdata.dhi[timeindex]
    if original_dhi == 0 and metdata.dni[timeindex] > 0:
        metdata.dhi[timeindex] = 1.0e-6
    try:
        skyfile = demo.gendaylit(timeindex=timeindex, metdata=metdata)
    finally:
        metdata.dhi[timeindex] = original_dhi
    if skyfile is None:
        raise ValueError(f"No hourly sky generated for {metdata.datetime[timeindex]}.")
    return skyfile


def create_selected_module(
    demo: br.RadianceObj,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    pv_type: str,
    module_xgap: float,
    run_id: str,
):
    module_name = f"{module_spec.name}_{pv_type}_{run_id}"
    module_parameters = dict(
        name=module_name, x=module_spec.module_x, y=module_spec.module_y,
        z=module_spec.module_thickness, xgap=module_xgap, ygap=0.0, numpanels=1,
    )
    if pv_type == "semi_transparent":
        glass_material_name = f"agripv_hazy_glass_{run_id}"
        add_hazy_glass_material(demo, module_spec, glass_material_name)
        geometry = module_geometry(design, module_spec)
        # Keep the original 1 mm opaque cells, but do not generate stock glass.
        cell_thickness = 0.001
        module = demo.makeModule(
            **dict(module_parameters, z=cell_thickness),
            cellModule=geometry["cell_module"],
            glass=False,
            bifi=module_spec.bifaciality,
            customtext=equivalent_glass_text(
                module_name, glass_material_name, module_spec, cell_thickness,
            ),
        )
    else:
        # Opaque geometry: no glass, cells, cell gaps, or transparent regions.
        # Bifacial response is independent of optical transparency.
        module = demo.makeModule(
            **module_parameters,
            glass=False,
            modulematerial="black",
            bifi=module_spec.conventional_bifaciality,
        )

    # Preserve the same outer envelope while applying construction-specific xgap.
    module.x = module_spec.module_x
    module.y = module_spec.module_y
    module.scenex = module_spec.module_x + module_xgap
    module.sceney = module_spec.module_y
    return module


# Cell 6: Moving module sensors; two local-Y points per cell or numerical patch

# Expand one module-centre point into one rectangular sensor grid at the current angle.
def make_rectangular_surface_scans(
    scene, module_number, row_number, module_spec,
    first_x, first_y, spacing_x, spacing_y, surface_offset,
) -> tuple[dict, dict]:
    # Calculate in float64; do not use moduleAnalysis's float16 sensor origins.
    # Match the angles and height actually serialized by the scene generator.
    sd, module = scene.sceneDict, scene.module
    azimuth = np.radians(round(float(sd["azimuth"]), 2))
    tilt = np.radians(round(float(sd["tilt"]), 2))
    u = np.array([-np.cos(azimuth), np.sin(azimuth), 0.0])
    v = np.array([-np.sin(azimuth), -np.cos(azimuth), 0.0])
    slope = np.cos(tilt) * v + np.array([0.0, 0.0, np.sin(tilt)])
    normal = -np.sin(tilt) * v + np.array([0.0, 0.0, np.cos(tilt)])
    height = float(scene.text.split(" -t ", 1)[1].split()[2])
    centre = np.array([sd.get("originx", 0.0), sd.get("originy", 0.0), height])
    centre += (module_number - round(sd["nMods"] / 1.999)) * module.scenex * u
    centre += (row_number - round(sd["nRows"] / 1.999)) * sd["pitch"] * v
    first = centre + first_x * u + first_y * slope
    scans = []
    for offset, orient in (
        (module.offsetfromaxis + module.z + surface_offset, -normal),
        (module.offsetfromaxis - surface_offset, normal),
    ):
        point = first + offset * normal
        dx, dy = spacing_x * u, spacing_y * slope
        scans.append(dict(
            xstart=float(point[0]), ystart=float(point[1]), zstart=float(point[2]),
            sx_xinc=float(dx[0]), sx_yinc=float(dx[1]), sx_zinc=float(dx[2]),
            xinc=float(dy[0]), yinc=float(dy[1]), zinc=float(dy[2]),
            Nx=module_spec.numcellsx, Ny=module_spec.numcellsy, Nz=1,
            orient=" ".join(f"{value:.12g}" for value in orient),
        ))
    return scans[0], scans[1]


# Create two grids per face: one at -Y/4 and one at +Y/4 of every cell/patch.
def make_module_surface_scans(
    context: TrackingSimulationContext,
    scene,
    module_number: int,
    row_number: int,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> tuple[list[dict], list[dict], float]:
    if context.pv_type == "semi_transparent":
        # The two points remain inside every physical active cell.
        geometry = module_geometry(design, module_spec)
        spacing_x = module_spec.xcell + design.xcellgap
        spacing_y = module_spec.ycell + design.ycellgap
        represented_y = module_spec.ycell
        centre_x = round(module_spec.xcell / 2, 6) if module_spec.numcellsx % 2 == 0 else 0.0
        first_x = -geometry["grid_x"] / 2 + centre_x + module_spec.xcell / 2
        first_lower_edge = -geometry["grid_y"] / 2
        surface_offset = module_spec.module_thickness / 2 + 0.001
        sample_area_m2 = module_spec.xcell * module_spec.ycell / 2
    else:
        # Split the opaque surface into the same number of equal patches and put
        # two points within each patch; cells and cell gaps are not physical here.
        spacing_x = module_spec.module_x / module_spec.numcellsx
        spacing_y = module_spec.module_y / module_spec.numcellsy
        represented_y = spacing_y
        first_x = -module_spec.module_x / 2 + spacing_x / 2
        first_lower_edge = -module_spec.module_y / 2
        surface_offset = SETTINGS.conventional_surface_offset
        sample_area_m2 = spacing_x * spacing_y / 2

    # Both constructions sample the quarter and three-quarter local-Y positions.
    first_y_values = (
        first_lower_edge + represented_y / 4,
        first_lower_edge + 3 * represented_y / 4,
    )
    front_scans = []
    back_scans = []
    for first_y in first_y_values:
        front_scan, back_scan = make_rectangular_surface_scans(
            scene, module_number, row_number, module_spec,
            first_x, first_y, spacing_x, spacing_y, surface_offset,
        )
        front_scans.append(front_scan)
        back_scans.append(back_scan)
    return front_scans, back_scans, sample_area_m2

# Cell 7: Shared hourly tracing; Hao hourly outputs and Linrui period sums

def analyze_module_at_hour(
    position: tuple[int, int],
    hour_key: str,
    context: TrackingSimulationContext,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> tuple[float, float]:
    row_number, module_number = position
    angle_entry = context.trackerdict[hour_key]
    scene = angle_entry["scenes"][0]
    total_octfile = angle_entry["octfile"]
    analysis = br.AnalysisObj(total_octfile, context.simulation_name, hpc=SETTINGS.hpc)
    front_scans, back_scans, sample_area_m2 = make_module_surface_scans(
        context, scene, module_number, row_number, design, module_spec,
    )

    # Either construction can be bifacial; zero skips its rear Radiance scans.
    bifaciality = (
        module_spec.bifaciality
        if context.pv_type == "semi_transparent"
        else module_spec.conventional_bifaciality
    )
    trace_rear = bifaciality > 0.0
    front_sum = 0.0
    rear_sum = 0.0
    for local_y_index, (front_scan, back_scan) in enumerate(zip(front_scans, back_scans), start=1):
        analysis_name = (
            f"{context.pv_type}_{hour_key}_r{row_number:02d}_m{module_number:02d}_"
            f"y{local_y_index}_{context.run_id}"
        )
        if trace_rear:
            front, back = analysis.analysis(
                total_octfile,
                analysis_name,
                front_scan,
                back_scan,
                accuracy=SETTINGS.accuracy,
            )
            rear_sum += float(np.asarray(back["Wm2"], dtype=float).sum())
        else:
            front = analysis.analysis(
                total_octfile,
                analysis_name,
                front_scan,
                accuracy=SETTINGS.accuracy,
            )
        front_sum += float(np.asarray(front["Wm2"], dtype=float).sum())

    front_power = front_sum * sample_area_m2
    rear_effective_power = rear_sum * sample_area_m2 * bifaciality
    return front_power, rear_effective_power


def analyze_array_at_hour(
    hour_key: str,
    context: TrackingSimulationContext,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    positions, executor,
) -> tuple[float, float]:
    def run_module(position: tuple[int, int]) -> tuple[float, float]:
        return analyze_module_at_hour(position, hour_key, context, design, module_spec)

    return tuple(np.sum(list(executor.map(run_module, positions)), axis=0))


def make_shared_ground_scan(scenario, design, module_spec, array_spec) -> tuple[dict, float]:
    # Same world-coordinate land and sensors for both constructions, centred at (0, 0).
    # Width follows the conventional array, including its inter-module gaps.
    azimuth = np.radians(round((design.axis_azimuth - 90) % 180, 2))
    u = np.array([-np.cos(azimuth), np.sin(azimuth)])
    v = np.array([-np.sin(azimuth), -np.cos(azimuth)])
    width = (array_spec.n_mods * module_spec.module_x
             + (array_spec.n_mods - 1) * design.xgap_conventional
             + 2 * SETTINGS.ground_border_m)
    projected_y = module_spec.module_y
    length = (array_spec.n_rows - 1) * design.pitch + projected_y + 2 * SETTINGS.ground_border_m
    du, dv = width / scenario.ground_grid_x, length / scenario.ground_grid_y
    first = (-width / 2 + du / 2) * u + (-length / 2 + dv / 2) * v
    scan = dict(
        xstart=float(first[0]), ystart=float(first[1]), zstart=SETTINGS.ground_sensor_height,
        sx_xinc=float(du * u[0]), sx_yinc=float(du * u[1]), sx_zinc=0.0,
        xinc=float(dv * v[0]), yinc=float(dv * v[1]), zinc=0.0,
        Nx=scenario.ground_grid_x, Ny=scenario.ground_grid_y, Nz=1, orient="0 0 -1",
    )
    return scan, du * dv


def trace_direct_ground_irradiation(analysis, octfile, scan):
    # Hourly gendaylit contains an explicit sun, unlike the old cumulative glow.
    # Zero ambient bounces keeps its beam/regular transmission, excluding diffuse
    # sky, diffuse glass scattering and diffuse surface reflection. -dr 0 disables
    # secondary virtual-source reflections in this direct component.
    completed = subprocess.run(
        ["rtrace", "-i", "-ab", "0", "-av", "0", "0", "0", "-dr", "0",
         "-dt", "0", "-dj", "0", "-h", "-ov", octfile],
        input=analysis._linePtsMakeDict(scan), text=True, capture_output=True, check=True,
    )
    rgb = np.asarray([[float(value) for value in line.split()]
                      for line in completed.stdout.splitlines() if line.strip()], dtype=float)
    return rgb.mean(axis=1)


def analyze_ground_hour(octfile, simulation_name, scan, cell_area_m2, analysis_name):
    # One hour's W/m2 -> W after area integration; caller multiplies by duration_h.
    analysis = br.AnalysisObj(octfile, simulation_name, hpc=SETTINGS.hpc)
    full = analysis.analysis(octfile, analysis_name, scan, accuracy=SETTINGS.accuracy)
    total = float(np.asarray(full["Wm2"], dtype=float).sum() * cell_area_m2)
    direct = float(trace_direct_ground_irradiation(analysis, octfile, scan).sum() * cell_area_m2)
    return np.array([direct, total - direct, total])


def calculate_hourly_results(
    design, scenario, module_spec, array_spec, run_id, run_directory,
    calculate_hao, calculate_linrui,
) -> tuple[pd.DataFrame, dict, dict]:
    # One row per hour, including zero-radiation night hours, in EPW local STANDARD time.
    results = None
    ground_summary = {}
    constructions = (
        ("semi_transparent", SETTINGS.xgap_semi_transparent),
        ("conventional", design.xgap_conventional),
    )
    positions = [(row, mod) for row in range(1, array_spec.n_rows + 1)
                 for mod in range(1, array_spec.n_mods + 1)] if calculate_hao else []
    if calculate_linrui:
        ground_scan, ground_area = make_shared_ground_scan(scenario, design, module_spec, array_spec)
    # Workers are started lazily; a Linrui-only run submits no module tasks.
    with ThreadPoolExecutor(max_workers=SETTINGS.n_workers) as executor:
        for pv_type, module_xgap in constructions:
            construction_directory = run_directory / pv_type
            construction_directory.mkdir(parents=True, exist_ok=True)
            demo = br.RadianceObj(
                name=f"{pv_type}_hourly_{run_id}", path=str(construction_directory),
                hpc=SETTINGS.hpc,
            )
            demo.setGround(SETTINGS.ground_albedo)
            if results is None:
                hour_starts, solar_times, metdata, timing = read_hourly_cultivation_weather(demo, scenario)
                results = pd.DataFrame(index=hour_starts)
                results["hour_start"] = hour_starts.map(lambda t: t.isoformat())
                results["hour_end"] = (hour_starts + pd.Timedelta(hours=1)).map(lambda t: t.isoformat())
                results["duration_h"] = 1.0
                results["solar_timestamp"] = solar_times.map(lambda t: t.isoformat())
                results[["tracker_theta_deg", "surface_tilt_deg", "surface_azimuth_deg"]] = np.nan
            module = create_selected_module(
                demo, design, module_spec, pv_type, module_xgap, f"hourly_{run_id}",
            )
            trackerdict = {} if metdata is None else demo.set1axis(
                metdata=metdata, azimuth=design.axis_azimuth, limit_angle=design.limit_angle,
                angledelta=None, backtrack=design.backtrack, gcr=module_spec.module_y / design.pitch,
                cumulativesky=False,
            )
            columns = [
                f"{pv_type}_array_{face}_effective_incident_energy_Wh_hour"
                for face in ("front", "rear")
            ]
            results[columns] = 0.0
            ground_energy = np.zeros(3)
            for timeindex, hour_end in enumerate([] if metdata is None else metdata.datetime):
                hour_start = hour_end - pd.Timedelta(hours=1)
                hour_key = hour_end.strftime("%Y-%m-%d_%H%M")
                skyfile = make_hourly_sky(demo, metdata, timeindex)
                # No angle binning: both outputs use this hour's tracker orientation.
                entry = trackerdict.get(hour_key)
                if entry is None:
                    # Diffuse twilight has no sun-tracking angle; assume horizontal parking.
                    if metdata.dni[timeindex] > 0:
                        raise ValueError(f"Positive DNI but no tracker angle at {hour_key}.")
                    entry = dict(surf_azm=(design.axis_azimuth - 90) % 360,
                                 surf_tilt=0.0, theta=0.0, ghi=metdata.ghi[timeindex])
                # Store the original pvlib orientation (before Radiance's signed-tilt conversion).
                results.loc[hour_start, ["tracker_theta_deg", "surface_tilt_deg", "surface_azimuth_deg"]] = [
                    entry["theta"], entry["surf_tilt"], entry["surf_azm"],
                ]
                hourly_scene = demo.makeScene1axis(
                    trackerdict={hour_key: entry.copy()}, module=module,
                    sceneDict=dict(pitch=design.pitch, hub_height=design.hub_height,
                                   nMods=array_spec.n_mods, nRows=array_spec.n_rows,
                                   **centred_scene_origin(module, pv_type, module_spec, array_spec,
                                                          design.pitch, entry["surf_azm"] % 180)),
                    cumulativesky=False,
                )
                scene = hourly_scene[hour_key]["scenes"][0]
                octfile = demo.makeOct(
                    filelist=[*demo.materialfiles, skyfile, *demo._getradfiles([scene])],
                    octname=f"hourly_{pv_type}_{hour_key}_{run_id}",
                )
                hourly_scene[hour_key]["octfile"] = octfile
                context = TrackingSimulationContext(
                    run_id=run_id, pv_type=pv_type, simulation_name=demo.name,
                    trackerdict=hourly_scene,
                )
                if calculate_hao:
                    power_values = analyze_array_at_hour(hour_key, context, design, module_spec, positions, executor)
                    # Treat each TMY sample as representative of one hour:
                    # sum(E_sensor [W/m2] * area [m2]) * duration [h] = incident energy [Wh].
                    # Rear weighting by this construction's bifaciality already occurs in the scan.
                    results.loc[hour_start, columns] = np.asarray(power_values) * results.loc[hour_start, "duration_h"]
                if calculate_linrui:
                    ground_energy += analyze_ground_hour(
                        octfile, demo.name, ground_scan, ground_area,
                        f"ground_{pv_type}_{hour_key}_{run_id}",
                    ) * results.loc[hour_start, "duration_h"]
                if (timeindex + 1) % 24 == 0:
                    print(f"Hourly {pv_type}: {timeindex + 1}/{len(metdata.datetime)} irradiated hours completed.", flush=True)
            print(f"{pv_type}: completed {len(hour_starts)} hourly intervals.", flush=True)
            if calculate_linrui:
                ground_summary[pv_type] = {
                    f"ground_{component}_incident_energy_Wh_period": float(value)
                    for component, value in zip(("direct", "diffuse", "total"), ground_energy)
                }
    hao_hourly = results.reset_index(drop=True) if calculate_hao else pd.DataFrame()
    return hao_hourly, ground_summary, timing


# Cell 8: Persistent single-axis scenario records and selective model execution

# Save the four input groups, fixed ground albedo, and final outputs.
def build_input_record(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    gcr: float,
) -> dict:
    start, end = cultivation_period_bounds(scenario)
    return {
        # CultivationScenario
        "scenario_name": scenario.scenario_name,
        "crop_name": scenario.crop_name,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "period_boundary_convention": "start_inclusive_end_exclusive",
        "weather_filename": scenario.weather_filename,
        "accuracy": SETTINGS.accuracy,  # Numerical setting selected in Cell 3.
        "albedo": SETTINGS.ground_albedo,  # Fixed assumption, retained for traceability.
        "ground_grid_x": scenario.ground_grid_x,
        "ground_grid_y": scenario.ground_grid_y,
        # ModuleSpecification
        "module_name": module_spec.name,
        "module_x_m": module_spec.module_x,
        "module_y_m": module_spec.module_y,
        "module_thickness_m": module_spec.module_thickness,
        "numcellsx": module_spec.numcellsx,
        "numcellsy": module_spec.numcellsy,
        "xcell_m": module_spec.xcell,
        "ycell_m": module_spec.ycell,
        "semi_transparent_bifaciality": module_spec.bifaciality,
        "conventional_bifaciality": module_spec.conventional_bifaciality,
        "semi_transparent_glass_total_transmittance": module_spec.glass_total_transmittance,
        "semi_transparent_glass_specular_reflectance": module_spec.glass_specular_reflectance,
        "semi_transparent_glass_haze": module_spec.glass_haze,
        # ArraySpecification
        "array_n_mods": array_spec.n_mods,
        "array_n_rows": array_spec.n_rows,
        # TrackingDesign and its derived, reproducibility-relevant values
        "pitch_m": design.pitch,
        "axis_azimuth_deg": design.axis_azimuth,
        "hub_height_m": design.hub_height,
        "limit_angle_deg": design.limit_angle,
        "backtrack": bool(design.backtrack),
        "derived_gcr": gcr,
        "xcellgap_m": design.xcellgap,
        "ycellgap_m": design.ycellgap,
        "xgap_conventional_m": design.xgap_conventional,
    }


# Append complete results without overwriting historical runs.
def append_result_rows(result_file: Path, new_rows: pd.DataFrame) -> None:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    write_header = not result_file.exists() or result_file.stat().st_size == 0
    if not write_header:
        old_columns = list(pd.read_csv(result_file, nrows=0).columns)
        # Preserve historical columns and values if new input fields have been added.
        columns = list(dict.fromkeys([*old_columns, *new_rows.columns]))
        if columns != old_columns:
            previous = pd.read_csv(result_file).reindex(columns=columns)
            previous.to_csv(result_file, index=False, encoding="utf-8")
        new_rows = new_rows.reindex(columns=columns)
    new_rows.to_csv(result_file, mode="a", header=write_header, index=False, encoding="utf-8")


# Append Hao's hourly rows and/or Linrui's single cultivation-period row.
def save_selected_results(
    design, scenario, module_spec, array_spec, gcr,
    run_id, hao_hourly, ground_summary, calculate_linrui, calculate_hao, weather_timing,
) -> None:
    common_record = build_input_record(design, scenario, module_spec, array_spec, gcr)
    common_record.update(run_id=run_id, **weather_timing)
    if calculate_hao:
        hao_record = {key: value for key, value in common_record.items() if "glass_" not in key}
        rows = pd.DataFrame([hao_record] * len(hao_hourly))
        rows = pd.concat([rows, hao_hourly.reset_index(drop=True)], axis=1)
        append_result_rows(HAO_RESULTS_FILE, rows)
    if calculate_linrui:
        common_record.update({
            f"{pv_type}_{name}": value
            for pv_type, metrics in ground_summary.items()
            for name, value in metrics.items()
        })
        append_result_rows(LINRUI_RESULTS_FILE, pd.DataFrame([common_record]))


# Calculate requested outputs, save summaries, and delete all Radiance intermediates.
def model_for_optimization(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_linrui: bool = True,
    calculate_hao: bool = True,
) -> tuple[pd.DataFrame, dict]:
    hao_hourly = pd.DataFrame()
    ground_summary = {}
    if not calculate_linrui and not calculate_hao:
        return hao_hourly, ground_summary

    # All failures below this line still precede CSV writing; invalid inputs never
    # produce a partial result row.
    gcr = validate_model_inputs(design, scenario, module_spec, array_spec)
    print(f"Derived GCR = {gcr:.6f}; hourly tracking without angle bins.")

    if calculate_linrui:
        validate_ground_grid(scenario)
    original_directory = Path.cwd().resolve()
    run_id = uuid4().hex[:8]
    with TemporaryDirectory(prefix=f"agripv_single_axis_{run_id}_") as temporary_directory:
        try:
            hao_hourly, ground_summary, weather_timing = calculate_hourly_results(
                design, scenario, module_spec, array_spec, run_id,
                Path(temporary_directory) / "hourly", calculate_hao, calculate_linrui,
            )
        finally:
            # RadianceObj changes cwd; leave its directory before temporary cleanup.
            os.chdir(original_directory)

    save_selected_results(
        design, scenario, module_spec, array_spec, gcr,
        run_id, hao_hourly, ground_summary, calculate_linrui, calculate_hao, weather_timing,
    )
    return hao_hourly, ground_summary


# Cell 9: Run selected outputs; Hao hourly rows, Linrui one period row

# Clear previous results before a rerun, including failed reruns.
hao_hourly = pd.DataFrame()
ground_summary = {}
hao_hourly, ground_summary = model_for_optimization(
    candidate_design, scenario, module_specification, array_specification,
    calculate_linrui=GET_LINRUI_GROUND_IRRADIATION,
    calculate_hao=GET_HAO_ARRAY_RESULTS,
)
if GET_HAO_ARRAY_RESULTS:
    display(hao_hourly.head(8))
    print(f"Hao: {len(hao_hourly)} hourly rows appended to {HAO_RESULTS_FILE}")
if GET_LINRUI_GROUND_IRRADIATION:
    display(pd.Series({
        f"{pv_type}_{name}": value
        for pv_type, metrics in ground_summary.items()
        for name, value in metrics.items()
    }, name="Value"))
    print(f"Linrui: one cultivation-period row appended to {LINRUI_RESULTS_FILE}")
if not GET_LINRUI_GROUND_IRRADIATION and not GET_HAO_ARRAY_RESULTS:
    print("Both switches are False. No simulation ran and no CSV was saved.")

