# READ-ONLY SOURCE EXPORT for interface inspection. Final cells may run simulations.
# Extracted without executing the original notebook.
# Cell 1: Imports, external tools, and project folders

# Standard-library imports.
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
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

    # On macOS, prefer the installed native executable over bundled Linux binaries.
    executable_folders = native_bins if sys.platform == "darwin" else [bundled_data, *native_bins]
    os.environ["PATH"] = os.pathsep.join(
        [*(str(folder) for folder in executable_folders), os.environ.get("PATH", "")]
    )

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
# AgriPV/notebooks/this_notebook.ipynb
# AgriPV/weather/user_weather_file.epw
# AgriPV/results/Linrui_vertical_pv_scenarios.csv
# AgriPV/results/Hao_vertical_pv_hourly_scenarios.csv
WORKING_DIRECTORY = Path.cwd().resolve()
PROJECT_ROOT = (
    WORKING_DIRECTORY.parent
    if WORKING_DIRECTORY.name.lower() == "notebooks"
    else WORKING_DIRECTORY
)
WEATHER_DIRECTORY = PROJECT_ROOT / "weather"
RESULTS_DIRECTORY = PROJECT_ROOT / "results"
LINRUI_RESULTS_FILE = RESULTS_DIRECTORY / "Linrui_vertical_pv_scenarios.csv"
HAO_RESULTS_FILE = RESULTS_DIRECTORY / "Hao_vertical_pv_hourly_scenarios.csv"
configure_external_tools()

# Cell 2: Input structures used by the comparison model

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


# Vertical candidate inputs. Tilt is fixed and cannot be passed to the constructor.
@dataclass(frozen=True)
class VerticalPVDesign:
    pitch: float
    azimuth: float
    xcellgap: float
    ycellgap: float
    xgap_conventional: float
    tilt: float = field(default=90.0, init=False)
    clearance_height: float = field(default=0.0, init=False)


# Numerical and site settings kept constant within one optimization run.
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


# Minimal handles needed while one of the two temporary scenes is running.
@dataclass
class SimulationContext:
    run_id: str
    pv_type: str
    module_xgap: float
    simulation_name: str
    scene: object
    total_octfile: str


# Cell 3: Inputs edited by Linrui and Hao

# Before running, check: all numeric inputs must be finite (no NaN or infinity).
# Counts must be positive integers; dimensions positive; gaps nonnegative.
# Glass inputs and bifacialities must be in [0, 1]; transmittance + reflectance <= 1.
# Existing fit, period and collision checks do not replace these user checks.
# Input labels used below:
# BOTH/physics = affects both irradiation calculations.
# BOTH/record = identifies both CSV rows but does not change the ray tracing.
# HAO/output or LINRUI/physics = primarily owned by that named output.
# Every field must still keep its stated Python type. For an unused numeric field,
# use the suggested valid placeholder; never enter arbitrary letters or symbols.

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
GET_HAO_ARRAY_RESULTS = True

# Put this EPW file inside AgriPV/weather/ and enter only its file name here.
# This Aachen EPW matches PVGIS 5.3 TMY built from 2005-2023 candidates.
# Reuse typical weather on the actual dates below; this is NOT a weather forecast.
# Use YYYY-MM-DD for complete days, or YYYY-MM-DD HH:00 for hourly bounds.
# An explicit end time is EXCLUSIVE: 15:00 to 17:00 contains two hours.
# Use EPW local standard time (no DST); write explicit years for winter seasons.
# Ground-mounted vertical panels can intersect ground sensor centres.
# If the shared land grid hits a panel, change its counts as prompted.
# Project rule: if the weather data changes, use a new file name; never replace
# an existing EPW with different contents under the same file name.
scenario = CultivationScenario(
    scenario_name="Aachen_Crop_A_vertical_001",  # BOTH/record: unique readable case label.
    crop_name="Crop_A",  # BOTH/record: retained for crop-model linkage; no ray-tracing effect.
    start_date="2024-06-21",  # BOTH/physics: inclusive date or whole-hour start.
    end_date="2024-06-21",  # BOTH/physics: full final day, or exclusive whole-hour end.
    weather_filename="Aachen_PVGIS_TMY.epw",  # BOTH/physics: EPW file inside weather/.
    weather_time_basis="pvgis_utc",  # BOTH/physics: audited PVGIS UTC row order.
    # For ordinary EPW with genuine local-standard-time rows, use "local_standard".
    ground_grid_x=16,  # LINRUI/physics: positive integer; ground-grid columns.
    ground_grid_y=16,  # LINRUI/physics: positive integer; ground-grid rows; total sensors = x * y.
)

# Enter the shared outer module dimensions and the semi-transparent cell layout.
# Enter each construction's rear/front response ratio independently, from 0 to 1.
# The 0.80 values below are examples, not verified module datasheet values.
# Set a construction's bifaciality to 0 for monofacial PV; its rear scan is skipped.
# Enter the three glass optical inputs from 0 to 1. Total transmittance plus
# specular reflectance should not exceed 1; haze splits the transmitted share.
# The conventional scene uses the outer dimensions, cell counts, and its own bifaciality; it ignores
# xcell, ycell, xcellgap, and ycellgap as physical geometry.
# Glass values below are illustrative assumptions, not verified LONGi data.
# Supply whole-pane properties for the intended glass thickness: one optical
# sheet represents them. Changing thickness alone does not recompute optics.
module_specification = ModuleSpecification(
    name="LONGi_LR5_72HGD",  # BOTH/record: module identifier; no direct ray-tracing effect.
    module_x=1.134,  # BOTH/physics: outer module width along a row, metres.
    module_y=2.278,  # BOTH/physics: vertical module height, metres.
    module_thickness=0.030,  # BOTH/geometry: nominal envelope/opaque thickness (m); not glass absorption length.
    numcellsx=6,  # BOTH/physics: cell columns and conventional integration columns.
    numcellsy=24,  # BOTH/physics: cell rows and conventional integration rows.
    xcell=0.182,  # BOTH/physics: semi-transparent cell width, metres.
    ycell=0.091,  # BOTH/physics: semi-transparent cell length, metres.
    bifaciality=0.80,  # HAO/output: semi-transparent rear/front response; no ground-light effect.
    conventional_bifaciality=0.80,  # HAO/output: conventional rear/front response; 0 = monofacial.
    glass_total_transmittance=0.88,  # BOTH/physics: whole-pane total transmittance (constant coefficient), 0 to 1.
    glass_specular_reflectance=0.08,  # BOTH/physics: whole-pane specular reflectance (constant coefficient), 0 to 1.
    glass_haze=0.2,  # BOTH/physics: approximate diffuse share of whole-pane transmission, 0 to 1.
)

# Editable candidate array: 5 by 5 is only an example, not a model limit.
array_specification = ArraySpecification(
    n_mods=5,  # BOTH/physics: number of modules in each row, positive integer.
    n_rows=5,  # BOTH/physics: number of array rows, positive integer.
)

# Hao supplies these five candidate values; tilt is always 90 degrees.
# Azimuth describes the FRONT normal, not the row direction.
# 90 = front east / rear west; 180 = front south / rear north.
# The lower module edge is fixed at ground level (clearance = 0 m).
# xcellgap and ycellgap affect only the semi-transparent module.
# xgap_conventional affects only the gaps between conventional modules.
candidate_design = VerticalPVDesign(
    pitch=7.0,  # BOTH/physics: centre-to-centre row spacing, metres.
    azimuth=90.0,  # BOTH/physics: front-face bearing; 90 = east, degrees.
    xcellgap=0.0004,  # BOTH/physics: semi-transparent horizontal cell gap, metres.
    ycellgap=0.00235,  # BOTH/physics: semi-transparent vertical cell gap, metres.
    xgap_conventional=0.20,  # BOTH/physics: gap between conventional modules, metres.
)

# Cell 4: Geometry validation, variable cell grid, and equivalent glass

# Calculate the active-cell grid used for fit checks and sensor placement.
def module_geometry(
    design: VerticalPVDesign,
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


# Stop before Radiance starts if the physical cells do not fit inside the module.
def validate_cell_array_fit(
    design: VerticalPVDesign,
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
        "both x and y directions" if len(overflow_axes) == 2
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
    design: VerticalPVDesign,
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


# Cell 6: Vertical front/rear surface grids, one centre sensor per cell or patch

# Build sensor coordinates directly in float64. The library's generic scan helper
# rounds positions to float16, which can swallow millimetre offsets in wide arrays.
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


# Semi-transparent sensors represent cell area; opaque sensors represent equal
# patches of the full module. Both constructions retain the same sensor counts.
def make_module_surface_scans(
    context: SimulationContext,
    module_number: int,
    row_number: int,
    design: VerticalPVDesign,
    module_spec: ModuleSpecification,
) -> tuple[dict, dict, float]:
    if context.pv_type == 'semi_transparent':
        geometry = module_geometry(design, module_spec)
        spacing_x = module_spec.xcell + design.xcellgap
        spacing_y = module_spec.ycell + design.ycellgap
        centre_x = round(module_spec.xcell / 2, 6) if module_spec.numcellsx % 2 == 0 else 0.0
        first_x = -geometry['grid_x'] / 2 + centre_x + module_spec.xcell / 2
        first_y = -geometry['grid_y'] / 2 + module_spec.ycell / 2
        surface_offset = module_spec.module_thickness / 2 + 0.001
        sample_area_m2 = module_spec.xcell * module_spec.ycell
    else:
        spacing_x = module_spec.module_x / module_spec.numcellsx
        spacing_y = module_spec.module_y / module_spec.numcellsy
        first_x = -module_spec.module_x / 2 + spacing_x / 2
        first_y = -module_spec.module_y / 2 + spacing_y / 2
        surface_offset = SETTINGS.conventional_surface_offset
        sample_area_m2 = spacing_x * spacing_y

    front_scan, back_scan = make_rectangular_surface_scans(
        context.scene, module_number, row_number, module_spec,
        first_x, first_y, spacing_x, spacing_y, surface_offset,
    )
    return front_scan, back_scan, sample_area_m2


# Cell 7: Shared hourly tracing; Hao hourly outputs and Linrui period sums

def analyze_module(
    position: tuple[int, int],
    context: SimulationContext,
    module_spec: ModuleSpecification,
    scans,
) -> tuple[float, float]:
    row_number, module_number = position
    analysis = br.AnalysisObj(
        context.total_octfile,
        context.simulation_name,
        hpc=SETTINGS.hpc,
    )

    front_scan, back_scan, sample_area_m2 = scans
    analysis_name = (
        f"{context.pv_type}_r{row_number:02d}_m{module_number:02d}_{context.run_id}"
    )
    bifaciality = (
        module_spec.bifaciality
        if context.pv_type == "semi_transparent"
        else module_spec.conventional_bifaciality
    )
    trace_rear = bifaciality > 0.0
    if not trace_rear:
        # Either construction can be monofacial; skip its unnecessary rear scan.
        front = analysis.analysis(
            context.total_octfile,
            analysis_name,
            front_scan,
            accuracy=SETTINGS.accuracy,
        )
        back = None
    else:
        front, back = analysis.analysis(
            context.total_octfile,
            analysis_name,
            front_scan,
            back_scan,
            accuracy=SETTINGS.accuracy,
        )

    # Representative hourly irradiance [W/m2] times represented area gives incident power [W].
    front_power = float(np.asarray(front["Wm2"], dtype=float).sum() * sample_area_m2)
    rear_effective_power = (
        0.0
        if back is None
        else float(
            np.asarray(back["Wm2"], dtype=float).sum()
            * sample_area_m2
            * bifaciality
        )
    )
    return front_power, rear_effective_power


def analyze_array(context, module_spec, positions, executor, surface_scans) -> tuple[float, float]:
    # Reuse one pool and the fixed sensor geometry throughout this run.
    def run_module(position):
        return analyze_module(position, context, module_spec, surface_scans[position])
    return tuple(np.sum(list(executor.map(run_module, positions)), axis=0))


def make_shared_ground_scan(scenario, design, module_spec, array_spec) -> tuple[dict, float]:
    # Same world-coordinate land and sensors for both constructions, centred at (0, 0).
    # Width follows the conventional array, including its inter-module gaps.
    azimuth = np.radians(round(design.azimuth, 2))
    u = np.array([-np.cos(azimuth), np.sin(azimuth)])
    v = np.array([-np.sin(azimuth), -np.cos(azimuth)])
    width = (array_spec.n_mods * module_spec.module_x
             + (array_spec.n_mods - 1) * design.xgap_conventional
             + 2 * SETTINGS.ground_border_m)
    projected_y = 0.0
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
            module = create_selected_module(
                demo, design, module_spec, pv_type, module_xgap, f"hourly_{run_id}",
            )
            scene = demo.makeScene(
                module=module,
                sceneDict=dict(tilt=design.tilt, pitch=design.pitch, azimuth=design.azimuth,
                               clearance_height=design.clearance_height,
                               nMods=array_spec.n_mods, nRows=array_spec.n_rows,
                               **centred_scene_origin(module, pv_type, module_spec, array_spec,
                                                      design.pitch, design.azimuth)),
                radname=f"hourly_{pv_type}_{run_id}",
            )
            context = SimulationContext(
                run_id=run_id, pv_type=pv_type, module_xgap=module_xgap,
                simulation_name=demo.name, scene=scene, total_octfile="",
            )
            surface_scans = {
                position: make_module_surface_scans(context, position[1], position[0], design, module_spec)
                for position in positions
            }
            if calculate_linrui:
                check_vertical_ground_scan(ground_scan, context, design, module_spec, array_spec)
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
                # Vertical geometry is reused; only the hourly sky changes.
                octfile = demo.makeOct(
                    filelist=[*demo.materialfiles, skyfile, *demo._getradfiles([scene])],
                    octname=f"hourly_{pv_type}_{hour_key}_{run_id}",
                )
                context.run_id = f"{run_id}_{hour_key}"
                context.total_octfile = octfile
                if calculate_hao:
                    power_values = analyze_array(context, module_spec, positions, executor, surface_scans)
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


def check_vertical_ground_scan(scan, context, design, module_spec, array_spec):
    # Keep exact grid centres and weights; reject points inside a panel envelope.
    azimuth = np.radians(round(design.azimuth, 2))
    u = np.array([-np.cos(azimuth), np.sin(azimuth)])
    v = np.array([-np.sin(azimuth), -np.cos(azimuth)])
    first = np.array([scan["xstart"], scan["ystart"]])
    ground_u = first @ u + np.arange(scan["Nx"]) * np.dot([scan["sx_xinc"], scan["sx_yinc"]], u)
    ground_v = first @ v + np.arange(scan["Ny"]) * np.dot([scan["xinc"], scan["yinc"]], v)
    module_offsets = (np.arange(array_spec.n_mods) - (array_spec.n_mods - 1) / 2) * (module_spec.module_x + context.module_xgap)
    row_offsets = (np.arange(array_spec.n_rows) - (array_spec.n_rows - 1) / 2) * design.pitch
    inside_u = np.any(np.abs(ground_u[:, None] - module_offsets) <= module_spec.module_x / 2 + 1e-9, axis=1)
    distance = row_offsets - ground_v[:, None]
    low, high = ((-module_spec.module_thickness / 2, module_spec.module_thickness / 2)
                 if context.pv_type == "semi_transparent" else (0.0, module_spec.module_thickness))
    inside_v = np.any((distance >= low - 1e-9) & (distance <= high + 1e-9), axis=1)
    if 0 <= SETTINGS.ground_sensor_height <= module_spec.module_y and inside_u.any() and inside_v.any():
        raise ValueError(
            f"{context.pv_type}: ground sensor centres intersect vertical panels. "
            "Change ground_grid_y in Cell 3. No result has been appended to either CSV."
        )


# Cell 8: Persistent scenario records and selective temporary comparison

# Save the four input groups and the fixed ground-albedo assumption.
def build_input_record(
    design: VerticalPVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
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
        # VerticalPVDesign
        "tilt_deg": design.tilt,
        "pitch_m": design.pitch,
        "azimuth_deg": design.azimuth,
        "clearance_height_m": design.clearance_height,
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


# Save only the final selected Linrui/Hao summaries; raw Radiance files remain temporary.
def save_selected_results(
    design, scenario, module_spec, array_spec,
    run_id, hao_hourly, ground_summary, calculate_linrui, calculate_hao, weather_timing,
) -> None:
    common_record = build_input_record(design, scenario, module_spec, array_spec)
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


# Calculate only the requested outputs, save summaries, then delete intermediates.
def model_for_optimization(
    design: VerticalPVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_linrui: bool = True,
    calculate_hao: bool = True,
) -> tuple[pd.DataFrame, dict]:
    hao_hourly = pd.DataFrame()
    ground_summary = {}

    # With both switches off, avoid creating temporary scenes or result rows.
    if not calculate_linrui and not calculate_hao:
        return hao_hourly, ground_summary

    # Validate before creating a run ID, temporary files, Radiance scenes, or CSV rows.
    cultivation_period_bounds(scenario)
    validate_cell_array_fit(design, module_spec)
    for field in ("bifaciality", "conventional_bifaciality"):
        if not 0.0 <= getattr(module_spec, field) <= 1.0:
            raise ValueError(f"{field} must be between 0 and 1.")

    if calculate_linrui:
        validate_ground_grid(scenario)
    original_directory = Path.cwd().resolve()
    run_id = uuid4().hex[:8]
    with TemporaryDirectory(prefix=f"agripv_vertical_{run_id}_") as temporary_directory:
        try:
            hao_hourly, ground_summary, weather_timing = calculate_hourly_results(
                design, scenario, module_spec, array_spec, run_id,
                Path(temporary_directory) / "hourly", calculate_hao, calculate_linrui,
            )
        finally:
            # Leave RadianceObj's working directory before temporary cleanup.
            os.chdir(original_directory)

    save_selected_results(
        design, scenario, module_spec, array_spec,
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

