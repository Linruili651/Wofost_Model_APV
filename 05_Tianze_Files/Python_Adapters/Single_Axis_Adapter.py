"""Tianze original definitions, extracted without executing Notebook cells.
Source: 03_optimization_ready_single_axis_radiation_model.ipynb
SHA256: 2e9904d5feed4ed0bf8b0aa86c02d0022c4a2c075b4fb1fd47bafad771a922c4
No automatic run, PATH mutation, directory creation or notebook loading.
Daily crop-specific adaptations are separately visible in radiation_bridge.py.
"""
from __future__ import annotations


from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import atan2, ceil, cos, degrees, radians, sin
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import os
import subprocess
import sys
import numpy as np
import pandas as pd
import bifacial_radiance as br

PROJECT_ROOT = Path(__file__).resolve().parent
WEATHER_DIRECTORY = PROJECT_ROOT / "inputs"
RESULTS_DIRECTORY = PROJECT_ROOT / "runs" / "unused_original_csv_paths"
LINRUI_RESULTS_FILE = RESULTS_DIRECTORY / "Linrui_tracking.csv"
HAO_RESULTS_FILE = RESULTS_DIRECTORY / "Hao_radiation_tracking.csv"

# Cell 2: Input structures used by the single-axis comparison model

# Human-readable scenario label, crop, cultivation period, shared weather, and albedo.
@dataclass(frozen=True)
class CultivationScenario:
    scenario_name: str
    crop_name: str
    start_date: str
    end_date: str
    weather_filename: str
    albedo: float


# Shared module envelope, semi-transparent cell layout, bifaciality, and glass optics.
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
    reference_year: int = 2001
    xgap_semi_transparent: float = 0.0
    target_angle_delta_deg: float = 5.0
    ground_grid_x: int = 15
    ground_grid_y: int = 15
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
    direct_octfiles: dict
    unshaded_ground_irradiation_Wh_m2_period: float


SETTINGS = ModelSettings()

# Cell 3: Inputs edited by Linrui and Hao

# Input labels used below:
# BOTH/physics = affects both people's irradiation calculations.
# BOTH/record = identifies both CSV rows but does not alter ray tracing.
# HAO/design = a candidate design variable normally supplied by Hao's optimizer.
# HAO/output or LINRUI/physics = primarily owned by that named output.
# Every field must keep its stated Python type. For an unused numeric field, use
# the suggested valid placeholder; never enter arbitrary letters or symbols.

# LINRUI/output switch; Hao may leave False. Both switches False runs nothing.
GET_LINRUI_GROUND_IRRADIATION = False
# HAO/output switch; Linrui may leave False.
GET_HAO_ARRAY_RESULTS = False

# Put this EPW file inside AgriPV/weather/ and enter only its file name here.
# The TMY is relabelled to calendar year 2001; its weather values still come
# from the representative historical months stored inside the EPW file.
# Only month and day select the cultivation period. If the end month/day is
# earlier than the start month/day, the model automatically wraps over New Year.
# If the weather data changes, use a new file name rather than silently replacing
# an existing file with different data under the same name.
scenario = CultivationScenario(
    scenario_name="Aachen_Crop_A_single_axis_001",  # BOTH/record: unique case label.
    crop_name="Crop_A",  # BOTH/record: retained for crop linkage; no ray-tracing effect.
    start_date="2001-03-01",  # BOTH/physics: first included TMY calendar date.
    end_date="2001-03-30",  # BOTH/physics: last included TMY calendar date.
    weather_filename="Aachen_PVGIS_TMY.epw",  # BOTH/physics: EPW inside weather/.
    albedo=0.20,  # BOTH/physics: ground short-wave reflectance, decimal 0 to 1.
)

# Enter the shared outer module dimensions and semi-transparent cell layout.
# Bifaciality is the semi-transparent rear/front response ratio. The conventional
# scene uses only the outer dimensions and cell counts; it ignores cell sizes,
# cell gaps, bifaciality, and all glass inputs as physical construction data.
module_specification = ModuleSpecification(
    name="LONGi_LR5_72HGD",  # BOTH/record: module identifier.
    module_x=1.134,  # BOTH/physics: outer width along the tracker axis, metres.
    module_y=2.278,  # BOTH/physics: rotating chord across rows, metres.
    module_thickness=0.030,  # BOTH/physics: module/glass thickness, metres.
    numcellsx=6,  # BOTH/physics: cell and conventional integration columns.
    numcellsy=24,  # BOTH/physics: cell and conventional integration rows.
    xcell=0.182,  # BOTH/physics: semi-transparent cell width, metres.
    ycell=0.091,  # BOTH/physics: semi-transparent cell length, metres.
    bifaciality=0.80,  # HAO/output: rear/front response, decimal 0 to 1.
    glass_total_transmittance=0.88,  # LINRUI/physics: transmitted fraction.
    glass_specular_reflectance=0.08,  # LINRUI/physics: mirror-reflected fraction.
    glass_haze=0.20,  # LINRUI/physics: diffuse fraction of transmitted irradiation.
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

# Cell 4: Geometry, angle-bin, tracker, and optical validation

# Calculate the active-cell grid and remaining glass margins.
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
        "edge_x": (module_spec.module_x - grid_x) / 2,
        "edge_y": (module_spec.module_y - grid_y) / 2,
    }


# Stop before Radiance if the physical cells exceed the outer module envelope.
def validate_cell_array_fit(
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> None:
    geometry = module_geometry(design, module_spec)
    tolerance_m = 1.0e-9
    overflow_x = geometry["grid_x"] > module_spec.module_x + tolerance_m
    overflow_y = geometry["grid_y"] > module_spec.module_y + tolerance_m
    if not overflow_x and not overflow_y:
        return

    direction = (
        "both x and y directions"
        if overflow_x and overflow_y
        else "the x direction"
        if overflow_x
        else "the y direction"
    )
    print(f"ERROR: The semi-transparent cell array exceeds the module in {direction}.")
    if overflow_x:
        print(
            f"x direction: cell array = {geometry['grid_x']:.6f} m, "
            f"module = {module_spec.module_x:.6f} m."
        )
    if overflow_y:
        print(
            f"y direction: cell array = {geometry['grid_y']:.6f} m, "
            f"module = {module_spec.module_y:.6f} m."
        )
    print("Reduce the corresponding cell size, cell count, or cell gap in Cell 3.")
    raise ValueError(
        "Invalid semi-transparent module geometry; Radiance was not started "
        "and no result was appended to either CSV file."
    )


# Use a target of about 5 degrees while exactly dividing each half rotation range.
def actual_tracker_angle_delta(limit_angle: float, target_delta: float) -> float:
    half_steps = max(1, ceil(limit_angle / target_delta))
    return limit_angle / half_steps


# Map month/day inputs onto one TMY calendar, wrapping the end into the next year.
def cultivation_period_bounds(
    scenario: CultivationScenario,
) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    start_input = pd.Timestamp(scenario.start_date)
    end_input = pd.Timestamp(scenario.end_date)
    for field_name, timestamp in (("start_date", start_input), ("end_date", end_input)):
        if (timestamp.month, timestamp.day) == (2, 29):
            raise ValueError(
                f"{field_name} cannot be February 29 because the reference TMY year "
                f"{SETTINGS.reference_year} is not a leap year."
            )

    start = pd.Timestamp(
        year=SETTINGS.reference_year,
        month=start_input.month,
        day=start_input.day,
    )
    crosses_new_year = (end_input.month, end_input.day) < (
        start_input.month,
        start_input.day,
    )
    end = pd.Timestamp(
        year=SETTINGS.reference_year + int(crosses_new_year),
        month=end_input.month,
        day=end_input.day,
    )
    return start, end, crosses_new_year


# Validate all shared and tracking inputs before creating temporary or CSV files.
def validate_model_inputs(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> dict:
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
    if SETTINGS.target_angle_delta_deg <= 0.0:
        raise ValueError("target_angle_delta_deg must be positive.")
    if not isinstance(design.backtrack, (bool, np.bool_)):
        raise TypeError("backtrack must be True or False.")
    if not 0.0 <= scenario.albedo <= 1.0:
        raise ValueError("albedo must be between 0 and 1.")
    if not 0.0 <= module_spec.bifaciality <= 1.0:
        raise ValueError("bifaciality must be between 0 and 1.")

    optical_values = {
        "glass_total_transmittance": module_spec.glass_total_transmittance,
        "glass_specular_reflectance": module_spec.glass_specular_reflectance,
        "glass_haze": module_spec.glass_haze,
    }
    invalid_optics = [name for name, value in optical_values.items() if not 0.0 <= value <= 1.0]
    if invalid_optics:
        raise ValueError(f"These glass inputs must be between 0 and 1: {', '.join(invalid_optics)}.")
    if module_spec.glass_specular_reflectance >= 1.0:
        raise ValueError("glass_specular_reflectance must be below 1 for the Radiance trans material.")
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

    angle_delta = actual_tracker_angle_delta(
        design.limit_angle,
        SETTINGS.target_angle_delta_deg,
    )
    return {
        "gcr": gcr,
        "angle_delta_deg": angle_delta,
        "minimum_clearance_m": minimum_clearance,
    }


# Fill the glass envelope outside the active-cell grid.
def glass_margin_text(
    module_name: str,
    glass_material_name: str,
    geometry: dict,
    module_spec: ModuleSpecification,
) -> str:
    # bifacial_radiance shifts an even number of cell columns by half one cell.
    centre_x = module_spec.xcell / 2 if module_spec.numcellsx % 2 == 0 else 0.0
    edge_x = geometry["edge_x"]
    edge_y = geometry["edge_y"]
    grid_x = geometry["grid_x"]
    grid_y = geometry["grid_y"]

    # Left/right strips span the full length; lower/upper strips close the ends.
    strips = [
        ("left", edge_x, module_spec.module_y, centre_x - module_spec.module_x / 2, -module_spec.module_y / 2),
        ("right", edge_x, module_spec.module_y, centre_x + grid_x / 2, -module_spec.module_y / 2),
        ("lower", grid_x, edge_y, centre_x - grid_x / 2, -module_spec.module_y / 2),
        ("upper", grid_x, edge_y, centre_x - grid_x / 2, grid_y / 2),
    ]
    return "\n".join(
        f"! genbox {glass_material_name} {module_name}_glass_{side} "
        f"{width:.6f} {length:.6f} {module_spec.module_thickness:.6f} "
        f"| xform -t {xstart:.6f} {ystart:.6f} "
        f"{-module_spec.module_thickness / 2:.6f}"
        for side, width, length, xstart, ystart in strips
    )

# Cell 5: Tracking-angle skies, modules, scenes, and octrees

# Approximate measured total transmission and haze with a Radiance trans material.
def add_hazy_glass_material(
    demo: br.RadianceObj,
    module_spec: ModuleSpecification,
    material_name: str,
) -> None:
    nonabsorbed_colour = (
        module_spec.glass_total_transmittance
        / (1.0 - module_spec.glass_specular_reflectance)
    )
    transmitted_specular_fraction = 1.0 - module_spec.glass_haze
    material_text = (
        f"void trans {material_name}\n"
        "0\n"
        "0\n"
        f"7 {nonabsorbed_colour:.8f} {nonabsorbed_colour:.8f} "
        f"{nonabsorbed_colour:.8f} {module_spec.glass_specular_reflectance:.8f} "
        f"0.0 1.0 {transmitted_specular_fraction:.8f}\n"
    )
    material_file = Path("materials") / f"{material_name}.rad"
    material_file.write_text(material_text, encoding="ascii")
    demo.materialfiles.append(str(material_file))


# Retain only the direct-horizontal part of one angle bin's filtered TMY file.
def make_direct_only_cumulative_weather(
    full_weather_file: Path,
    direct_weather_file: Path,
) -> None:
    sky_inputs = pd.read_csv(
        full_weather_file,
        sep=r"\s+",
        header=None,
        names=["GHI", "DHI"],
    )
    direct_horizontal = (sky_inputs["GHI"] - sky_inputs["DHI"]).clip(lower=0.0)
    # Keep direct hours active in gencumulativesky when the true DHI is zero.
    diffuse_epsilon = np.where(direct_horizontal > 0.0, 1.0e-3, 0.0)
    pd.DataFrame(
        {
            "GHI": direct_horizontal + diffuse_epsilon,
            "DHI": diffuse_epsilon,
        }
    ).to_csv(
        direct_weather_file,
        index=False,
        header=False,
        sep=" ",
    )


# Make file-safe labels for negative and decimal tracker-angle keys.
def angle_file_label(theta: float) -> str:
    return f"{float(theta):+.6f}".replace("+", "p").replace("-", "m").replace(".", "d")


# Read one ordinary or New-Year-wrapping cultivation period from one TMY EPW.
def read_cultivation_weather(
    demo: br.RadianceObj,
    scenario: CultivationScenario,
):
    start, end, crosses_new_year = cultivation_period_bounds(scenario)
    weather_file = WEATHER_DIRECTORY / scenario.weather_filename
    if not crosses_new_year:
        return demo.readWeatherFile(
            weatherFile=str(weather_file),
            starttime=f"{start:%Y-%m-%d}_0000",
            endtime=f"{end:%Y-%m-%d}_2300",
            coerce_year=SETTINGS.reference_year,
        )

    # gencumulativesky requires one 8760-hour calendar. Keep the selected
    # year-end and year-start hours in that calendar and zero every other hour.
    weather_data, metadata = demo._readEPW(
        epwfile=str(weather_file),
        label="right",
        coerce_year=SETTINGS.reference_year,
    )
    timezone = weather_data.index.tz
    start_boundary = start.tz_localize(timezone)
    end_boundary = end.replace(year=SETTINGS.reference_year).replace(
        hour=23
    ).tz_localize(timezone)
    selected_hours = (weather_data.index >= start_boundary) | (
        weather_data.index <= end_boundary
    )
    text_columns = weather_data.select_dtypes(include=["object", "string"]).columns
    numeric_columns = weather_data.columns.difference(text_columns)
    weather_data.loc[~selected_hours, text_columns] = "0"
    weather_data.loc[~selected_hours, numeric_columns] = 0
    return demo.readWeatherData(
        metadata=metadata,
        metdata=weather_data,
        coerce_year=SETTINGS.reference_year,
        label="right",
    )


# Trace one open horizontal ground sensor and sum all full-sky angle bins.
def trace_unshaded_tracking_reference(
    demo: br.RadianceObj,
    trackerdict: dict,
    run_id: str,
) -> float:
    open_scan = {
        "xstart": 0.0,
        "ystart": 0.0,
        "zstart": SETTINGS.ground_sensor_height,
        "xinc": 0.0,
        "yinc": 0.0,
        "zinc": 0.0,
        "sx_xinc": 0.0,
        "sx_yinc": 0.0,
        "sx_zinc": 0.0,
        "Nx": 1,
        "Ny": 1,
        "Nz": 1,
        "orient": "0 0 -1",
    }
    period_reference = 0.0
    for theta in sorted(trackerdict):
        label = angle_file_label(theta)
        open_octfile = demo.makeOct(
            filelist=[*demo.materialfiles, trackerdict[theta]["skyfile"]],
            octname=f"open_ground_{label}_{run_id}",
        )
        analysis = br.AnalysisObj(open_octfile, demo.name, hpc=SETTINGS.hpc)
        result = analysis.analysis(
            open_octfile,
            f"open_ground_{label}_{run_id}",
            open_scan,
            accuracy=SETTINGS.accuracy,
        )
        period_reference += float(np.asarray(result["Wm2"], dtype=float)[0])
    return period_reference


# Create the physical semi-transparent module or one opaque conventional module.
def create_selected_module(
    demo: br.RadianceObj,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    pv_type: str,
    module_xgap: float,
    run_id: str,
):
    module_name = f"{module_spec.name}_{pv_type}_{run_id}"
    if pv_type == "semi_transparent":
        glass_material_name = f"agripv_hazy_glass_{run_id}"
        add_hazy_glass_material(demo, module_spec, glass_material_name)
        geometry = module_geometry(design, module_spec)
        module = demo.makeModule(
            name=module_name,
            x=module_spec.module_x,
            y=module_spec.module_y,
            z=module_spec.module_thickness,
            xgap=module_xgap,
            ygap=0.0,
            numpanels=1,
            cellModule=geometry["cell_module"],
            glass=True,
            glassEdge=0.0,
            bifi=module_spec.bifaciality,
            customtext=glass_margin_text(
                module_name,
                glass_material_name,
                geometry,
                module_spec,
            ),
        )
        # Replace bifacial_radiance's stock clear glass with the requested optics.
        module.text = module.text.replace("stock_glass", glass_material_name)
        module.compileText(rewriteModulefile=True, json=False)
    else:
        # No glass, cells, cell gaps, bifacial rear, or transparent regions.
        module = demo.makeModule(
            name=module_name,
            x=module_spec.module_x,
            y=module_spec.module_y,
            z=module_spec.module_thickness,
            xgap=module_xgap,
            ygap=0.0,
            numpanels=1,
            glass=False,
            modulematerial="black",
            bifi=0.0,
        )

    # Preserve the same outer envelope while applying construction-specific xgap.
    module.x = module_spec.module_x
    module.y = module_spec.module_y
    module.scenex = module_spec.module_x + module_xgap
    module.sceney = module_spec.module_y
    return module


# Build all angle-bin scenes and full/direct octrees for one construction.
def create_tracking_scene(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    derived: dict,
    pv_type: str,
    module_xgap: float,
    run_id: str,
    run_directory: Path,
    create_direct_octrees: bool,
    unshaded_ground_reference: float | None,
) -> TrackingSimulationContext:
    run_directory.mkdir(parents=True, exist_ok=True)
    demo = br.RadianceObj(
        name=f"{pv_type}_single_axis_{run_id}",
        path=str(run_directory),
        hpc=SETTINGS.hpc,
    )
    demo.setGround(scenario.albedo)

    # Read the requested TMY period, including a wrap from December into January.
    metdata = read_cultivation_weather(demo, scenario)

    # Compute hourly tracker angles, round them to the exact-divisor angle spacing,
    # and group the period into one weather CSV per angle.
    trackerdict = demo.set1axis(
        metdata=metdata,
        azimuth=design.axis_azimuth,
        limit_angle=design.limit_angle,
        angledelta=derived["angle_delta_deg"],
        backtrack=design.backtrack,
        gcr=derived["gcr"],
        cumulativesky=True,
    )
    if not trackerdict:
        raise ValueError("No sun-up tracker-angle bins were created for the selected period.")
    trackerdict = demo.genCumSky1axis(trackerdict)

    # Hao's open-ground reference uses the same sum of full angle-bin skies.
    if unshaded_ground_reference is None:
        unshaded_ground_reference = trace_unshaded_tracking_reference(
            demo,
            trackerdict,
            run_id,
        )

    # Linrui additionally needs a direct-only sky for every occupied angle bin.
    direct_skyfiles = {}
    if create_direct_octrees:
        for theta in sorted(trackerdict):
            label = angle_file_label(theta)
            direct_weather_file = Path("EPWs") / f"direct_only_{label}_{run_id}.csv"
            make_direct_only_cumulative_weather(
                Path(trackerdict[theta]["csvfile"]),
                direct_weather_file,
            )
            direct_skyfiles[theta] = demo.genCumSky(
                gencumsky_metfile=str(direct_weather_file),
                savefile=f"1axis_direct_{label}_{run_id}",
            )

    # Rotate the complete selected module geometry into one scene per angle bin.
    module = create_selected_module(
        demo,
        design,
        module_spec,
        pv_type,
        module_xgap,
        run_id,
    )
    trackerdict = demo.makeScene1axis(
        trackerdict=trackerdict,
        module=module,
        sceneDict={
            "pitch": design.pitch,
            "hub_height": design.hub_height,
            "nMods": array_spec.n_mods,
            "nRows": array_spec.n_rows,
        },
        cumulativesky=True,
    )

    # Full octrees contain direct, diffuse, glass, reflection, and array geometry.
    trackerdict = demo.makeOct1axis(
        trackerdict=trackerdict,
        customname=f"_{pv_type}_full_{run_id}",
    )

    # Direct octrees use the same scene at each angle but its direct-only sky.
    direct_octfiles = {}
    if create_direct_octrees:
        for theta in sorted(trackerdict):
            label = angle_file_label(theta)
            direct_octfiles[theta] = demo.makeOct(
                filelist=[
                    *demo.materialfiles,
                    direct_skyfiles[theta],
                    *demo._getradfiles(trackerdict[theta]["scenes"]),
                ],
                octname=f"1axis_{label}_{pv_type}_direct_{run_id}",
            )

    return TrackingSimulationContext(
        run_id=run_id,
        pv_type=pv_type,
        simulation_name=demo.name,
        trackerdict=trackerdict,
        direct_octfiles=direct_octfiles,
        unshaded_ground_irradiation_Wh_m2_period=float(unshaded_ground_reference),
    )

# Cell 6: Moving module sensors; two local-Y points per cell or numerical patch

# Expand one module-centre point into one rectangular sensor grid at the current angle.
def make_rectangular_surface_scans(
    analysis: br.AnalysisObj,
    scene,
    module_number: int,
    row_number: int,
    module_spec: ModuleSpecification,
    first_x: float,
    first_y: float,
    spacing_x: float,
    spacing_y: float,
    surface_offset: float,
) -> tuple[dict, dict]:
    front_scan, back_scan = analysis.moduleAnalysis(
        scene,
        modWanted=module_number,
        rowWanted=row_number,
        sensorsx=1,
        sensorsy=1,
        frontsurfaceoffset=surface_offset,
        backsurfaceoffset=surface_offset,
    )

    # Read each angle scene's actual surface orientation. These local axes rotate
    # every sensor coordinate together with the tracker.
    azimuth = radians(float(scene.sceneDict["azimuth"]))
    tilt = radians(float(scene.sceneDict["tilt"]))
    x_axis = (-cos(azimuth), sin(azimuth), 0.0)
    y_axis = (
        -cos(tilt) * sin(azimuth),
        -cos(tilt) * cos(azimuth),
        sin(tilt),
    )

    # Move each surface to the first local point and add local X/Y increments.
    for scan in (front_scan, back_scan):
        scan["xstart"] = float(scan["xstart"]) + first_x * x_axis[0] + first_y * y_axis[0]
        scan["ystart"] = float(scan["ystart"]) + first_x * x_axis[1] + first_y * y_axis[1]
        scan["zstart"] = float(scan["zstart"]) + first_y * y_axis[2]
        scan.update(
            {
                "sx_xinc": spacing_x * x_axis[0],
                "sx_yinc": spacing_x * x_axis[1],
                "sx_zinc": 0.0,
                "xinc": spacing_y * y_axis[0],
                "yinc": spacing_y * y_axis[1],
                "zinc": spacing_y * y_axis[2],
                "Nx": module_spec.numcellsx,
                "Ny": module_spec.numcellsy,
                "Nz": 1,
            }
        )
    return front_scan, back_scan


# Create two grids per face: one at -Y/4 and one at +Y/4 of every cell/patch.
def make_module_surface_scans(
    analysis: br.AnalysisObj,
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
        centre_x = module_spec.xcell / 2 if module_spec.numcellsx % 2 == 0 else 0.0
        first_x = -geometry["grid_x"] / 2 + centre_x + module_spec.xcell / 2
        first_cell_lower_edge = -geometry["grid_y"] / 2
        first_y_values = (
            first_cell_lower_edge + represented_y / 4,
            first_cell_lower_edge + 3 * represented_y / 4,
        )
        surface_offset = module_spec.module_thickness / 2 + 0.001
        sample_area_m2 = module_spec.xcell * module_spec.ycell / 2
    else:
        # Split the opaque surface into the same number of equal patches and put
        # two points within each patch; cells and cell gaps are not physical here.
        spacing_x = module_spec.module_x / module_spec.numcellsx
        spacing_y = module_spec.module_y / module_spec.numcellsy
        represented_y = spacing_y
        first_x = -module_spec.module_x / 2 + spacing_x / 2
        first_patch_lower_edge = -module_spec.module_y / 2
        first_y_values = (
            first_patch_lower_edge + represented_y / 4,
            first_patch_lower_edge + 3 * represented_y / 4,
        )
        surface_offset = SETTINGS.conventional_surface_offset
        sample_area_m2 = spacing_x * spacing_y / 2

    front_scans = []
    back_scans = []
    for first_y in first_y_values:
        front_scan, back_scan = make_rectangular_surface_scans(
            analysis,
            scene,
            module_number,
            row_number,
            module_spec,
            first_x,
            first_y,
            spacing_x,
            spacing_y,
            surface_offset,
        )
        front_scans.append(front_scan)
        back_scans.append(back_scan)
    return front_scans, back_scans, sample_area_m2

# Cell 7: Per-angle module integration and the one fixed shared ground grid

# Trace one module at one tracker-angle bin.
def analyze_module_at_angle(
    position: tuple[int, int],
    theta: float,
    context: TrackingSimulationContext,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
) -> tuple[float, float]:
    row_number, module_number = position
    angle_entry = context.trackerdict[theta]
    scene = angle_entry["scenes"][0]
    total_octfile = angle_entry["octfile"]
    analysis = br.AnalysisObj(total_octfile, context.simulation_name, hpc=SETTINGS.hpc)
    front_scans, back_scans, sample_area_m2 = make_module_surface_scans(
        analysis,
        context,
        scene,
        module_number,
        row_number,
        design,
        module_spec,
    )

    # Semi-transparent rear sensors are skipped when bifaciality is zero. The
    # conventional rear is always skipped and never becomes an output.
    trace_rear = context.pv_type == "semi_transparent" and module_spec.bifaciality > 0.0
    label = angle_file_label(theta)
    front_sum = 0.0
    rear_sum = 0.0
    for local_y_index, (front_scan, back_scan) in enumerate(zip(front_scans, back_scans), start=1):
        analysis_name = (
            f"{context.pv_type}_{label}_r{row_number:02d}_m{module_number:02d}_"
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

    front_energy = front_sum * sample_area_m2
    rear_effective_energy = rear_sum * sample_area_m2 * module_spec.bifaciality
    return front_energy, rear_effective_energy


# Sum every module at one angle, parallelizing only across module positions.
def analyze_array_at_angle(
    theta: float,
    context: TrackingSimulationContext,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> tuple[float, float]:
    positions = [
        (row_number, module_number)
        for row_number in range(1, array_spec.n_rows + 1)
        for module_number in range(1, array_spec.n_mods + 1)
    ]

    def run_module(position: tuple[int, int]) -> tuple[float, float]:
        return analyze_module_at_angle(position, theta, context, design, module_spec)

    front_total = 0.0
    rear_total = 0.0
    with ThreadPoolExecutor(max_workers=SETTINGS.n_workers) as executor:
        for front_energy, rear_energy in executor.map(run_module, positions):
            front_total += front_energy
            rear_total += rear_energy
    return front_total, rear_total


# Build one fixed 15 × 15 world-coordinate grid large enough for both constructions
# and every permitted tracker angle. This keeps the paired comparison area identical.
def make_shared_ground_scan(
    reference_scene,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> tuple[dict, float]:
    # Use the tracking scene's exact local X orientation for the torque-tube axis.
    scene_azimuth = radians(float(reference_scene.sceneDict["azimuth"]))
    u_axis = np.array([-cos(scene_azimuth), sin(scene_azimuth)])
    v_axis = np.array([-sin(scene_azimuth), -cos(scene_azimuth)])

    # Match bifacial_radiance's module/row centring and take the union of both xgaps.
    central_module = round(array_spec.n_mods / 1.999)
    central_row = round(array_spec.n_rows / 1.999)

    def module_offsets(module_xgap: float) -> np.ndarray:
        module_pitch_x = module_spec.module_x + module_xgap
        return np.asarray(
            [
                (module_number - 1) * module_pitch_x
                - module_pitch_x * (central_module - 1)
                for module_number in range(1, array_spec.n_mods + 1)
            ],
            dtype=float,
        )

    semi_offsets = module_offsets(SETTINGS.xgap_semi_transparent)
    conventional_offsets = module_offsets(design.xgap_conventional)
    semi_shift = module_spec.xcell / 2 if module_spec.numcellsx % 2 == 0 else 0.0
    u_min = min(
        float(semi_offsets.min() + semi_shift - module_spec.module_x / 2),
        float(conventional_offsets.min() - module_spec.module_x / 2),
    ) - SETTINGS.ground_border_m
    u_max = max(
        float(semi_offsets.max() + semi_shift + module_spec.module_x / 2),
        float(conventional_offsets.max() + module_spec.module_x / 2),
    ) + SETTINGS.ground_border_m

    row_offsets = np.asarray(
        [
            (row_number - 1) * design.pitch - design.pitch * (central_row - 1)
            for row_number in range(1, array_spec.n_rows + 1)
        ],
        dtype=float,
    )
    # The horizontal state has the largest ground projection across a row.
    v_min = float(row_offsets.min() - module_spec.module_y / 2 - SETTINGS.ground_border_m)
    v_max = float(row_offsets.max() + module_spec.module_y / 2 + SETTINGS.ground_border_m)

    # Put one sensor at the centre of each equal ground cell.
    u_step = (u_max - u_min) / SETTINGS.ground_grid_x
    v_step = (v_max - v_min) / SETTINGS.ground_grid_y
    u_start = u_min + u_step / 2
    v_start = v_min + v_step / 2
    origin_x = float(reference_scene.sceneDict.get("originx", 0.0))
    origin_y = float(reference_scene.sceneDict.get("originy", 0.0))
    scan = {
        "xstart": origin_x + u_start * u_axis[0] + v_start * v_axis[0],
        "ystart": origin_y + u_start * u_axis[1] + v_start * v_axis[1],
        "zstart": SETTINGS.ground_sensor_height,
        "sx_xinc": u_step * u_axis[0],
        "sx_yinc": u_step * u_axis[1],
        "sx_zinc": 0.0,
        "xinc": v_step * v_axis[0],
        "yinc": v_step * v_axis[1],
        "zinc": 0.0,
        "Nx": SETTINGS.ground_grid_x,
        "Ny": SETTINGS.ground_grid_y,
        "Nz": 1,
        "orient": "0 0 -1",
    }
    return scan, u_step * v_step


# Trace direct-only cumulative sky with one ambient level. It retains direct sky
# and regular transmission while excluding glass-scattered/reflected contributions.
def trace_direct_ground_irradiation(
    analysis: br.AnalysisObj,
    direct_octfile: str,
    scan: dict,
) -> np.ndarray:
    line_points = analysis._linePtsMakeDict(scan)
    completed = subprocess.run(
        [
            "rtrace", "-i", "-ab", "1", "-aa", "0.1",
            "-ar", "256", "-ad", "2048", "-as", "256",
            "-h", "-ov", direct_octfile,
        ],
        input=line_points,
        text=True,
        capture_output=True,
        check=True,
    )
    rgb = np.asarray(
        [
            [float(value) for value in line.split()]
            for line in completed.stdout.splitlines()
            if line.strip()
        ],
        dtype=float,
    )
    return rgb.mean(axis=1)


# Trace one angle's fixed ground grid under its full and optional direct sky.
def analyze_ground_at_angle(
    theta: float,
    context: TrackingSimulationContext,
    ground_scan: dict,
    calculate_components: bool,
) -> tuple[np.ndarray, np.ndarray | None]:
    angle_entry = context.trackerdict[theta]
    total_octfile = angle_entry["octfile"]
    analysis = br.AnalysisObj(total_octfile, context.simulation_name, hpc=SETTINGS.hpc)
    label = angle_file_label(theta)
    total_result = analysis.analysis(
        total_octfile,
        f"ground_15x15_total_{label}_{context.pv_type}_{context.run_id}",
        ground_scan,
        accuracy=SETTINGS.accuracy,
    )
    total_irradiation = np.asarray(total_result["Wm2"], dtype=float)
    direct_irradiation = None
    if calculate_components:
        direct_irradiation = trace_direct_ground_irradiation(
            analysis,
            context.direct_octfiles[theta],
            ground_scan,
        )
    return total_irradiation, direct_irradiation


# Sum all occupied tracker-angle bins into the unchanged Linrui/Hao outputs.
def analyze_tracking_construction(
    context: TrackingSimulationContext,
    ground_scan: dict,
    ground_cell_area_m2: float,
    design: TrackingDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_linrui: bool,
    calculate_hao: bool,
) -> tuple[dict, dict, float | None]:
    front_period = 0.0
    rear_period = 0.0
    ground_total_period = np.zeros(SETTINGS.ground_grid_x * SETTINGS.ground_grid_y)
    ground_direct_period = np.zeros_like(ground_total_period) if calculate_linrui else None

    # Angle bins remain sequential to avoid nested parallelism and file collisions.
    for theta in sorted(context.trackerdict):
        if calculate_hao:
            front_angle, rear_angle = analyze_array_at_angle(
                theta,
                context,
                design,
                module_spec,
                array_spec,
            )
            front_period += front_angle
            rear_period += rear_angle

        total_angle, direct_angle = analyze_ground_at_angle(
            theta,
            context,
            ground_scan,
            calculate_components=calculate_linrui,
        )
        ground_total_period += total_angle
        if calculate_linrui:
            ground_direct_period += direct_angle

    array_metrics = {}
    if calculate_hao:
        array_metrics["array_front_effective_incident_energy_Wh_period"] = front_period
        if context.pv_type == "semi_transparent":
            array_metrics["array_rear_effective_incident_energy_Wh_period"] = rear_period

    ground_components = {}
    if calculate_linrui:
        ground_diffuse_period = ground_total_period - ground_direct_period
        ground_components = {
            "ground_direct_incident_energy_Wh_period": float(
                ground_direct_period.sum() * ground_cell_area_m2
            ),
            "ground_diffuse_incident_energy_Wh_period": float(
                ground_diffuse_period.sum() * ground_cell_area_m2
            ),
            "ground_total_incident_energy_Wh_period": float(
                ground_total_period.sum() * ground_cell_area_m2
            ),
        }

    shading_loss = None
    if calculate_hao:
        unshaded_reference = context.unshaded_ground_irradiation_Wh_m2_period
        if unshaded_reference <= 0.0:
            raise ValueError(
                "Ground shading cannot be calculated because the selected period "
                "has zero unshaded global horizontal irradiation."
            )
        shading_loss = 1.0 - float(ground_total_period.mean()) / unshaded_reference
    return array_metrics, ground_components, shading_loss

# Cell 8: Persistent single-axis scenario records and selective model execution

# Save only scenario, module, array, candidate tracking design, and final outputs.
def build_input_record(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    derived: dict,
) -> dict:
    return {
        # CultivationScenario
        "scenario_name": scenario.scenario_name,
        "crop_name": scenario.crop_name,
        "period_start": scenario.start_date,
        "period_end": scenario.end_date,
        "weather_filename": scenario.weather_filename,
        "albedo": scenario.albedo,
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
        "derived_gcr": derived["gcr"],
        "actual_angle_delta_deg": derived["angle_delta_deg"],
        "xcellgap_m": design.xcellgap,
        "ycellgap_m": design.ycellgap,
        "xgap_conventional_m": design.xgap_conventional,
    }


# Append one successful candidate without overwriting earlier candidates.
def append_result_row(result_file: Path, result_row: dict) -> None:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame([result_row])
    write_header = not result_file.exists() or result_file.stat().st_size == 0
    if not write_header:
        previous = pd.read_csv(result_file)
        columns = list(new_row.columns)
        if columns != list(previous.columns):
            previous.reindex(columns=columns).to_csv(
                result_file,
                index=False,
                encoding="utf-8",
            )
        new_row = new_row.reindex(columns=columns)
    new_row.to_csv(
        result_file,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8",
    )


# Append only the selected person's final single-axis row.
def save_selected_results(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    derived: dict,
    comparison_metrics: dict,
    ground_summary: dict,
    calculate_linrui: bool,
    calculate_hao: bool,
) -> None:
    common_record = build_input_record(
        design,
        scenario,
        module_spec,
        array_spec,
        derived,
    )
    if calculate_hao:
        hao_record = common_record.copy()
        # Hao's result table does not need Linrui's three glass-optics inputs.
        for field in (
            "semi_transparent_glass_total_transmittance",
            "semi_transparent_glass_specular_reflectance",
            "semi_transparent_glass_haze",
        ):
            hao_record.pop(field)
        hao_record.update(comparison_metrics)
        append_result_row(HAO_RESULTS_FILE, hao_record)

    if calculate_linrui:
        linrui_record = common_record.copy()
        linrui_record.update(
            {
                f"{pv_type}_{name}": value
                for pv_type, metrics in ground_summary.items()
                for name, value in metrics.items()
            }
        )
        append_result_row(LINRUI_RESULTS_FILE, linrui_record)


# Calculate requested outputs, save summaries, and delete all Radiance intermediates.
def model_for_optimization(
    design: TrackingDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_linrui: bool = True,
    calculate_hao: bool = True,
) -> tuple[dict, dict]:
    comparison_metrics = {}
    ground_summary = {}
    shading_metrics = {}
    if not calculate_linrui and not calculate_hao:
        return comparison_metrics, ground_summary

    # All failures below this line still precede CSV writing; invalid inputs never
    # produce a partial result row.
    derived = validate_model_inputs(design, scenario, module_spec, array_spec)
    print(
        f"Derived GCR = {derived['gcr']:.6f}; actual angle-bin spacing = "
        f"{derived['angle_delta_deg']:.6f} degrees; conservative minimum clearance = "
        f"{derived['minimum_clearance_m']:.3f} m."
    )

    original_directory = Path.cwd().resolve()
    run_id = uuid4().hex[:8]
    constructions = (
        ("semi_transparent", SETTINGS.xgap_semi_transparent),
        ("conventional", design.xgap_conventional),
    )
    unshaded_ground_reference = None if calculate_hao else 0.0
    shared_ground_scan = None
    shared_ground_cell_area = None

    with TemporaryDirectory(prefix=f"agripv_single_axis_{run_id}_") as temporary_directory:
        try:
            for pv_type, module_xgap in constructions:
                context = create_tracking_scene(
                    design,
                    scenario,
                    module_spec,
                    array_spec,
                    derived,
                    pv_type,
                    module_xgap,
                    run_id,
                    Path(temporary_directory) / pv_type,
                    create_direct_octrees=calculate_linrui,
                    unshaded_ground_reference=unshaded_ground_reference,
                )
                if unshaded_ground_reference is None:
                    unshaded_ground_reference = (
                        context.unshaded_ground_irradiation_Wh_m2_period
                    )

                # The first construction defines one union grid that is reused
                # without coordinate changes by the second construction.
                if shared_ground_scan is None:
                    first_theta = sorted(context.trackerdict)[0]
                    reference_scene = context.trackerdict[first_theta]["scenes"][0]
                    shared_ground_scan, shared_ground_cell_area = make_shared_ground_scan(
                        reference_scene,
                        design,
                        module_spec,
                        array_spec,
                    )

                construction_metrics, ground_components, ground_shading_loss = (
                    analyze_tracking_construction(
                        context,
                        shared_ground_scan,
                        shared_ground_cell_area,
                        design,
                        module_spec,
                        array_spec,
                        calculate_linrui,
                        calculate_hao,
                    )
                )
                if calculate_hao:
                    comparison_metrics.update(
                        {
                            f"{pv_type}_{name}": value
                            for name, value in construction_metrics.items()
                        }
                    )
                    shading_metrics[
                        f"{pv_type}_ground_shading_loss_fraction_period"
                    ] = ground_shading_loss
                if calculate_linrui:
                    ground_summary[pv_type] = ground_components
        finally:
            # RadianceObj changes cwd; leave its directory before temporary cleanup.
            os.chdir(original_directory)

    # Preserve the fixed-tilt output order: three array results, then two losses.
    comparison_metrics.update(shading_metrics)
    save_selected_results(
        design,
        scenario,
        module_spec,
        array_spec,
        derived,
        comparison_metrics,
        ground_summary,
        calculate_linrui,
        calculate_hao,
    )
    return comparison_metrics, ground_summary
