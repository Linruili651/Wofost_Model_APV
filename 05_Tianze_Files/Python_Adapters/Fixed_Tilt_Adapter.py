"""Tianze original definitions, extracted without executing Notebook cells.
Source: 02_optimization_ready_radiation_model.ipynb
SHA256: 11d6c0ece6706beed953500cee21fa4581353d81afe5301a033127c17bbcd194
No automatic run, PATH mutation, directory creation or notebook loading.
Daily crop-specific adaptations are separately visible in radiation_bridge.py.
"""
from __future__ import annotations


from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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
LINRUI_RESULTS_FILE = RESULTS_DIRECTORY / "Linrui_fixed.csv"
HAO_RESULTS_FILE = RESULTS_DIRECTORY / "Hao_radiation_fixed.csv"

# Cell 2: Input structures used by the comparison model

# Human-readable scenario label, crop, cultivation period, shared weather, and albedo.
@dataclass(frozen=True)
class CultivationScenario:
    scenario_name: str
    crop_name: str
    start_date: str
    end_date: str
    weather_filename: str
    albedo: float


# Shared module envelope, cell layout, bifaciality, and glass optical properties.
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


# Variables supplied by Hao's optimizer.
@dataclass(frozen=True)
class PVDesign:
    tilt: float
    pitch: float
    azimuth: float
    clearance_height: float
    xcellgap: float
    ycellgap: float
    xgap_conventional: float


# Numerical and site settings kept constant within one optimization run.
@dataclass(frozen=True)
class ModelSettings:
    reference_year: int = 2001
    xgap_semi_transparent: float = 0.0
    ground_grid_x: int = 15
    ground_grid_y: int = 15
    ground_border_m: float = 1.0
    ground_sensor_height: float = 0.05
    conventional_bifaciality: float = 0.0
    conventional_surface_offset: float = 0.005
    accuracy: str = "high"
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
    direct_octfile: str | None
    unshaded_ground_irradiation_Wh_m2_period: float


SETTINGS = ModelSettings()

# Cell 3: Inputs edited by Linrui and Hao

# Input labels used below:
# BOTH/physics = affects both irradiation calculations.
# BOTH/record = identifies both CSV rows but does not change the ray tracing.
# HAO/output or LINRUI/physics = primarily owned by that named output.
# Every field must still keep its stated Python type. For an unused numeric field,
# use the suggested valid placeholder; never enter arbitrary letters or symbols.

# LINRUI/output switch; Hao may leave False. Both switches False runs nothing.
GET_LINRUI_GROUND_IRRADIATION = False
# HAO/output switch; Linrui may leave False.
GET_HAO_ARRAY_RESULTS = True

# Put this EPW file inside AgriPV/weather/ and enter only its file name here.
# The TMY is relabelled to calendar year 2001; its weather values still come
# from the representative historical months stored inside the EPW file.
# Only month and day select the cultivation period. If the end month/day is
# earlier than the start month/day, the model automatically wraps over New Year.
# Project rule: if the weather data changes, use a new file name; never replace
# an existing EPW with different contents under the same file name.
scenario = CultivationScenario(
    scenario_name="Aachen_Crop_A_case_001",  # BOTH/record: unique readable case label.
    crop_name="Crop_A",  # BOTH/record: retained for crop-model linkage; no ray-tracing effect.
    start_date="2001-03-01",  # BOTH/physics: first included TMY calendar date.
    end_date="2001-03-30",  # BOTH/physics: last included TMY calendar date.
    weather_filename="Aachen_PVGIS_TMY.epw",  # BOTH/physics: EPW file inside weather/.
    albedo=0.20,  # BOTH/physics: ground short-wave reflectance, decimal 0 to 1.
)

# Enter the shared outer module dimensions and the semi-transparent cell layout.
# Enter bifaciality as a decimal rear/front response ratio (for example, 0.80).
# Enter the three glass optical inputs from 0 to 1. Total transmittance plus
# specular reflectance should not exceed 1; haze splits the transmitted share.
# The conventional scene uses only the outer dimensions and cell counts; it ignores
# xcell, ycell, xcellgap, and ycellgap as physical geometry.
module_specification = ModuleSpecification(
    name="LONGi_LR5_72HGD",  # BOTH/record: module identifier; no direct ray-tracing effect.
    module_x=1.134,  # BOTH/physics: outer module width along a row, metres.
    module_y=2.278,  # BOTH/physics: outer module length across the slope, metres.
    module_thickness=0.030,  # BOTH/physics: module/glass envelope thickness, metres.
    numcellsx=6,  # BOTH/physics: cell columns and conventional integration columns.
    numcellsy=24,  # BOTH/physics: cell rows and conventional integration rows.
    xcell=0.182,  # BOTH/physics: semi-transparent cell width, metres.
    ycell=0.091,  # BOTH/physics: semi-transparent cell length, metres.
    bifaciality=0.80,  # HAO/output: rear/front response, 0 to 1; Linrui may use 1.0.
    glass_total_transmittance=0.88,  # LINRUI/physics: transmitted share; Hao may keep 0.88.
    glass_specular_reflectance=0.08,  # LINRUI/physics: reflected share; Hao may keep 0.08.
    glass_haze=0.2,  # LINRUI/physics: diffuse share, 0 to 1; Hao may keep 0.0 if haze is not varied.
)

# Enter the number of modules in each row and the number of rows once.
array_specification = ArraySpecification(
    n_mods=5,  # BOTH/physics: number of modules in each row, positive integer.
    n_rows=5,  # BOTH/physics: number of array rows, positive integer.
)

# The optimizer replaces these seven values for every paired comparison.
# xcellgap and ycellgap affect only the semi-transparent module.
# xgap_conventional affects only the gaps between conventional modules.
candidate_design = PVDesign(
    tilt=25.0,  # BOTH/physics: fixed module tilt from horizontal, degrees.
    pitch=7.0,  # BOTH/physics: centre-to-centre row spacing, metres.
    azimuth=180.0,  # BOTH/physics: module-facing azimuth, degrees.
    clearance_height=3.0,  # BOTH/physics: lower-edge clearance, metres.
    xcellgap=0.0004,  # BOTH/physics: semi-transparent horizontal cell gap, metres.
    ycellgap=0.00235,  # BOTH/physics: semi-transparent vertical cell gap, metres.
    xgap_conventional=0.20,  # BOTH/physics: gap between conventional modules, metres.
)

# Cell 4: Geometry validation, variable cell grid, and glass margins

# Calculate the active-cell grid and the remaining glass margins.
def module_geometry(
    design: PVDesign,
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


# Stop before Radiance starts if the physical cells do not fit inside the module.
def validate_cell_array_fit(
    design: PVDesign,
    module_spec: ModuleSpecification,
) -> None:
    geometry = module_geometry(design, module_spec)
    tolerance_m = 1.0e-9
    overflow_x = geometry["grid_x"] > module_spec.module_x + tolerance_m
    overflow_y = geometry["grid_y"] > module_spec.module_y + tolerance_m

    if not overflow_x and not overflow_y:
        return

    if overflow_x and overflow_y:
        direction = "both x and y directions"
    elif overflow_x:
        direction = "the x direction"
    else:
        direction = "the y direction"

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


# Fill the glass envelope outside the active-cell grid.
def glass_margin_text(
    module_name: str,
    glass_material_name: str,
    geometry: dict,
    module_spec: ModuleSpecification,
) -> str:
    # bifacial_radiance shifts an even number of cell columns by half one cell.
    centre_x = (
        module_spec.xcell / 2
        if module_spec.numcellsx % 2 == 0
        else 0.0
    )

    edge_x = geometry["edge_x"]
    edge_y = geometry["edge_y"]
    grid_x = geometry["grid_x"]
    grid_y = geometry["grid_y"]

    # Left and right strips span the full module length.
    strips = [
        (
            "left",
            edge_x,
            module_spec.module_y,
            centre_x - module_spec.module_x / 2,
            -module_spec.module_y / 2,
        ),
        (
            "right",
            edge_x,
            module_spec.module_y,
            centre_x + grid_x / 2,
            -module_spec.module_y / 2,
        ),
        # Lower and upper strips fill the remaining length around the cell grid.
        (
            "lower",
            grid_x,
            edge_y,
            centre_x - grid_x / 2,
            -module_spec.module_y / 2,
        ),
        (
            "upper",
            grid_x,
            edge_y,
            centre_x - grid_x / 2,
            grid_y / 2,
        ),
    ]

    return "\n".join(
        f"! genbox {glass_material_name} {module_name}_glass_{side} "
        f"{width:.6f} {length:.6f} {module_spec.module_thickness:.6f} "
        f"| xform -t {xstart:.6f} {ystart:.6f} "
        f"{-module_spec.module_thickness / 2:.6f}"
        for side, width, length, xstart, ystart in strips
    )


# Cell 5: Full/direct cumulative skies, selected construction, scene, and octrees

# Approximate measured total transmission and haze with a Radiance trans material.
def add_hazy_glass_material(
    demo: br.RadianceObj,
    module_spec: ModuleSpecification,
    material_name: str,
) -> None:
    # Total transmission and specular reflection come from ModuleSpecification.
    # Haze controls the regular-versus-diffuse split of transmitted light.
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


# Retain only the direct-horizontal part of the already filtered TMY period.
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
    # gencumulativesky skips an hour when DHI is exactly zero, including its
    # direct beam. A negligible epsilon keeps direct hours active without
    # materially contributing diffuse energy.
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


# Trace one open horizontal-ground sensor under the same cumulative sky.
def trace_unshaded_ground_irradiation(
    demo: br.RadianceObj,
    full_sky: str,
    run_id: str,
) -> float:
    demo.skyfiles = [full_sky]
    open_octfile = demo.makeOct(octname=f"unshaded_ground_full_{run_id}")
    analysis = br.AnalysisObj(open_octfile, demo.name, hpc=SETTINGS.hpc)
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
    open_result = analysis.analysis(
        open_octfile,
        f"unshaded_ground_{run_id}",
        open_scan,
        accuracy=SETTINGS.accuracy,
    )
    return float(np.asarray(open_result["Wm2"], dtype=float)[0])


# Build one Radiance scene for one construction and one cultivation period.
def create_period_scene(
    design: PVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    pv_type: str,
    module_xgap: float,
    run_id: str,
    run_directory: Path,
    create_direct_octree: bool,
    unshaded_ground_reference: float | None,
) -> SimulationContext:
    # Keep the two comparison scenes isolated from each other.
    run_directory.mkdir(parents=True, exist_ok=True)
    demo = br.RadianceObj(
        name=f"{pv_type}_{run_id}",
        path=str(run_directory),
        hpc=SETTINGS.hpc,
    )
    demo.setGround(scenario.albedo)

    # Read the requested TMY period, including a wrap from December into January.
    start, end, _ = cultivation_period_bounds(scenario)
    read_cultivation_weather(demo, scenario)
    full_weather_file = Path(demo.gencumsky_metfile)
    full_sky = demo.genCumSky(
        gencumsky_metfile=str(full_weather_file),
        savefile=f"cultivation_full_{start:%m%d}_{end:%m%d}",
    )
    if unshaded_ground_reference is None:
        unshaded_ground_reference = trace_unshaded_ground_irradiation(
            demo, full_sky, run_id
        )

    module_name = f"{module_spec.name}_{pv_type}_{run_id}"
    if pv_type == "semi_transparent":
        # Physical cells and hazy glass margins create the semi-transparent module.
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
                module_name, glass_material_name, geometry, module_spec
            ),
        )
        # bifacial_radiance hard-codes stock_glass for the main envelope.
        module.text = module.text.replace("stock_glass", glass_material_name)
        module.compileText(rewriteModulefile=True, json=False)
    else:
        # The conventional module is one opaque box: no cellModule and no glass.
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
            bifi=SETTINGS.conventional_bifaciality,
        )

    # Apply the same envelope while preserving this construction's module gap.
    module.x = module_spec.module_x
    module.y = module_spec.module_y
    module.scenex = module_spec.module_x + module_xgap
    module.sceney = module_spec.module_y

    # All remaining scene inputs are shared by the paired comparison.
    scene = demo.makeScene(
        module=module,
        sceneDict={
            "tilt": design.tilt,
            "pitch": design.pitch,
            "azimuth": design.azimuth,
            "clearance_height": design.clearance_height,
            "nMods": array_spec.n_mods,
            "nRows": array_spec.n_rows,
        },
        radname=f"scene_{pv_type}_{run_id}",
    )

    # The full octree contains direct sky, diffuse sky, and all scene interactions.
    demo.skyfiles = [full_sky]
    total_octfile = demo.makeOct(octname=f"{pv_type}_full_{run_id}")

    # Linrui also needs a direct-only sky for the one-level sensor trace.
    direct_octfile = None
    if create_direct_octree:
        direct_weather_file = Path("EPWs") / f"direct_only_{run_id}.csv"
        make_direct_only_cumulative_weather(full_weather_file, direct_weather_file)
        direct_sky = demo.genCumSky(
            gencumsky_metfile=str(direct_weather_file),
            savefile=f"cultivation_direct_{start:%m%d}_{end:%m%d}",
        )
        demo.skyfiles = [direct_sky]
        direct_octfile = demo.makeOct(octname=f"{pv_type}_direct_{run_id}")

    return SimulationContext(
        run_id=run_id,
        pv_type=pv_type,
        module_xgap=module_xgap,
        simulation_name=demo.name,
        scene=scene,
        total_octfile=total_octfile,
        direct_octfile=direct_octfile,
        unshaded_ground_irradiation_Wh_m2_period=unshaded_ground_reference,
    )

# Cell 6: Dynamic surface grids; conventional modules use only the front grid

# Expand one module-centre scan into a rectangular integration grid.
def make_rectangular_surface_scans(
    analysis: br.AnalysisObj,
    scene,
    module_number: int,
    row_number: int,
    design: PVDesign,
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

    # Rotate local module X/Y directions into global scene coordinates.
    azimuth = np.radians(design.azimuth)
    tilt = np.radians(design.tilt)
    x_axis = (-np.cos(azimuth), np.sin(azimuth), 0.0)
    y_axis = (
        -np.cos(tilt) * np.sin(azimuth),
        -np.cos(tilt) * np.cos(azimuth),
        np.sin(tilt),
    )

    # Move both surfaces to the first centre and add grid increments.
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


# Select physical cell centres or equal opaque patches, and return represented area.
def make_module_surface_scans(
    analysis: br.AnalysisObj,
    context: SimulationContext,
    module_number: int,
    row_number: int,
    design: PVDesign,
    module_spec: ModuleSpecification,
) -> tuple[dict, dict, float]:
    if context.pv_type == "semi_transparent":
        # One point represents one physical semi-transparent cell.
        geometry = module_geometry(design, module_spec)
        spacing_x = module_spec.xcell + design.xcellgap
        spacing_y = module_spec.ycell + design.ycellgap
        centre_x = module_spec.xcell / 2 if module_spec.numcellsx % 2 == 0 else 0.0
        first_x = -geometry["grid_x"] / 2 + centre_x + module_spec.xcell / 2
        first_y = -geometry["grid_y"] / 2 + module_spec.ycell / 2
        surface_offset = module_spec.module_thickness / 2 + 0.001
        sample_area_m2 = module_spec.xcell * module_spec.ycell
    else:
        # One point represents one equal patch of the complete opaque surface.
        spacing_x = module_spec.module_x / module_spec.numcellsx
        spacing_y = module_spec.module_y / module_spec.numcellsy
        first_x = -module_spec.module_x / 2 + spacing_x / 2
        first_y = -module_spec.module_y / 2 + spacing_y / 2
        surface_offset = SETTINGS.conventional_surface_offset
        sample_area_m2 = spacing_x * spacing_y

    front_scan, back_scan = make_rectangular_surface_scans(
        analysis,
        context.scene,
        module_number,
        row_number,
        design,
        module_spec,
        first_x,
        first_y,
        spacing_x,
        spacing_y,
        surface_offset,
    )
    return front_scan, back_scan, sample_area_m2

# Cell 7: Per-module integration, array totals, and paired 15 × 15 ground grids

# Calculate both surfaces for semi-transparent modules and front only for conventional.
def analyze_module(
    position: tuple[int, int],
    context: SimulationContext,
    design: PVDesign,
    module_spec: ModuleSpecification,
) -> tuple[float, float]:
    row_number, module_number = position
    analysis = br.AnalysisObj(
        context.total_octfile,
        context.simulation_name,
        hpc=SETTINGS.hpc,
    )

    # The construction selects the scan geometry and represented area once.
    front_scan, back_scan, sample_area_m2 = make_module_surface_scans(
        analysis,
        context,
        module_number,
        row_number,
        design,
        module_spec,
    )
    analysis_name = (
        f"{context.pv_type}_r{row_number:02d}_m{module_number:02d}_{context.run_id}"
    )
    trace_rear = (
        context.pv_type == "semi_transparent" and module_spec.bifaciality > 0.0
    )
    if not trace_rear:
        # A conventional module, or a semi-transparent module with zero
        # bifaciality, has no effective rear-cell contribution.
        # Trace only its front surface; do not run the rear Radiance scan.
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

    # Centre irradiation times represented area approximates module energy.
    front_energy = float(np.asarray(front["Wm2"], dtype=float).sum() * sample_area_m2)
    rear_effective_energy = (
        0.0
        if back is None
        else float(
            np.asarray(back["Wm2"], dtype=float).sum()
            * sample_area_m2
            * module_spec.bifaciality
        )
    )
    return front_energy, rear_effective_energy


# Sum all module positions into the requested array-wide outputs.

def analyze_array(
    context: SimulationContext,
    design: PVDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> dict:
    positions = [
        (row_number, module_number)
        for row_number in range(1, array_spec.n_rows + 1)
        for module_number in range(1, array_spec.n_mods + 1)
    ]

    # Run different modules in parallel using half of the logical CPUs.
    def run_module(position: tuple[int, int]) -> tuple[float, float]:
        return analyze_module(position, context, design, module_spec)

    front_total = 0.0
    rear_total = 0.0
    with ThreadPoolExecutor(max_workers=SETTINGS.n_workers) as executor:
        for front_energy, rear_energy in executor.map(run_module, positions):
            front_total += front_energy
            rear_total += rear_energy

    array_metrics = {
        "array_front_effective_incident_energy_Wh_period": front_total,
    }
    if context.pv_type == "semi_transparent":
        array_metrics["array_rear_effective_incident_energy_Wh_period"] = rear_total
    return array_metrics


# Build a uniform ground grid over the projected footprint plus a 1 m border.
def make_ground_projection_scan(
    context: SimulationContext,
    design: PVDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
) -> tuple[dict, float]:
    azimuth = np.radians(design.azimuth)
    tilt = np.radians(design.tilt)

    # Local U follows modules within one row; local V follows successive rows.
    u_axis = np.array([-np.cos(azimuth), np.sin(azimuth)])
    v_axis = np.array([-np.sin(azimuth), -np.cos(azimuth)])

    # Match bifacial_radiance's exact module and row centring convention.
    central_module = round(array_spec.n_mods / 1.99)
    central_row = round(array_spec.n_rows / 1.99)
    module_pitch_x = module_spec.module_x + context.module_xgap
    module_offsets = np.array(
        [
            (module_number - 1) * module_pitch_x
            - module_pitch_x * (central_module - 1)
            for module_number in range(1, array_spec.n_mods + 1)
        ]
    )
    row_offsets = np.array(
        [
            (row_number - 1) * design.pitch
            - design.pitch * (central_row - 1)
            for row_number in range(1, array_spec.n_rows + 1)
        ]
    )

    # Only the detailed even-column cell module has bifacial_radiance's U shift.
    module_centre_shift = (
        module_spec.xcell / 2
        if context.pv_type == "semi_transparent" and module_spec.numcellsx % 2 == 0
        else 0.0
    )
    projected_module_y = module_spec.module_y * abs(np.cos(tilt))

    # Add one metre on all four sides of this construction's projection.
    u_min = (
        module_offsets.min() + module_centre_shift
        - module_spec.module_x / 2 - SETTINGS.ground_border_m
    )
    u_max = (
        module_offsets.max() + module_centre_shift
        + module_spec.module_x / 2 + SETTINGS.ground_border_m
    )
    v_min = row_offsets.min() - projected_module_y / 2 - SETTINGS.ground_border_m
    v_max = row_offsets.max() + projected_module_y / 2 + SETTINGS.ground_border_m

    # Place one sensor at the centre of each of the 15 × 15 equal ground cells.
    u_step = (u_max - u_min) / SETTINGS.ground_grid_x
    v_step = (v_max - v_min) / SETTINGS.ground_grid_y
    u_start = u_min + u_step / 2
    v_start = v_min + v_step / 2

    origin_x = float(context.scene.sceneDict.get("originx", 0.0))
    origin_y = float(context.scene.sceneDict.get("originy", 0.0))

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
    ground_cell_area_m2 = u_step * v_step
    return scan, ground_cell_area_m2


# Trace direct-only cumulative sky with one ambient level. The first level
# performs the sensor's hemispherical irradiance integration. With no second
# level, it retains open-sky direct light and regular transmission but excludes
# glass-scattered transmission, and reflected/other indirect contributions.
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


# Trace the 225 ground cells once, then derive only the requested outputs.
def analyze_ground(
    context: SimulationContext,
    design: PVDesign,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_components: bool,
    calculate_shading: bool,
) -> tuple[dict, float | None]:
    analysis = br.AnalysisObj(
        context.total_octfile,
        context.simulation_name,
        hpc=SETTINGS.hpc,
    )
    scan, ground_cell_area_m2 = make_ground_projection_scan(
        context,
        design,
        module_spec,
        array_spec,
    )
    total_raytrace = analysis.analysis(
        context.total_octfile,
        f"ground_15x15_total_{context.pv_type}_{context.run_id}",
        scan,
        accuracy=SETTINGS.accuracy,
    )

    total_irradiation = np.asarray(total_raytrace["Wm2"], dtype=float)
    ground_components = {}

    if calculate_components:
        direct_irradiation = trace_direct_ground_irradiation(
            analysis, context.direct_octfile, scan
        )
        diffuse_irradiation = total_irradiation - direct_irradiation

        # Multiplying each Wh/m2 midpoint result by its cell area gives Wh.
        ground_components = {
            "ground_direct_incident_energy_Wh_period": float(
                direct_irradiation.sum() * ground_cell_area_m2
            ),
            "ground_diffuse_incident_energy_Wh_period": float(
                diffuse_irradiation.sum() * ground_cell_area_m2
            ),
            "ground_total_incident_energy_Wh_period": float(
                total_irradiation.sum() * ground_cell_area_m2
            ),
        }

    ground_shading_loss = None
    if calculate_shading:
        unshaded_reference = context.unshaded_ground_irradiation_Wh_m2_period
        if unshaded_reference <= 0.0:
            raise ValueError(
                "Ground shading cannot be calculated because the selected period "
                "has zero unshaded global horizontal irradiation."
            )
        ground_shading_loss = (
            1.0 - float(total_irradiation.mean()) / unshaded_reference
        )

    return ground_components, ground_shading_loss

# Cell 8: Persistent scenario records and selective temporary comparison

# Save only the four editable input groups: scenario, module, array, and design.
def build_input_record(
    design: PVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
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
        # PVDesign
        "tilt_deg": design.tilt,
        "pitch_m": design.pitch,
        "azimuth_deg": design.azimuth,
        "clearance_height_m": design.clearance_height,
        "xcellgap_m": design.xcellgap,
        "ycellgap_m": design.ycellgap,
        "xgap_conventional_m": design.xgap_conventional,
    }


# Append one completed candidate without overwriting previous optimization runs.
def append_result_row(result_file: Path, result_row: dict) -> None:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame([result_row])
    write_header = not result_file.exists() or result_file.stat().st_size == 0

    # If an older CSV has extra columns, keep its rows but reduce it to the
    # current input-and-output schema before appending the new result.
    if not write_header:
        previous = pd.read_csv(result_file)
        columns = list(new_row.columns)
        if columns != list(previous.columns):
            previous.reindex(columns=columns).to_csv(
                result_file, index=False, encoding="utf-8"
            )
        new_row = new_row.reindex(columns=columns)

    new_row.to_csv(
        result_file,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8",
    )


# Save only the final selected Linrui/Hao summaries; raw Radiance files remain temporary.
def save_selected_results(
    design: PVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
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
    )

    if calculate_hao:
        hao_record = common_record.copy()
        # Hao's CSV does not need the three glass-optics inputs.
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


# Calculate only the requested outputs, save summaries, then delete intermediates.
def model_for_optimization(
    design: PVDesign,
    scenario: CultivationScenario,
    module_spec: ModuleSpecification,
    array_spec: ArraySpecification,
    calculate_linrui: bool = True,
    calculate_hao: bool = True,
) -> tuple[dict, dict]:
    comparison_metrics = {}
    ground_summary = {}
    shading_metrics = {}

    # With both switches off, avoid creating temporary scenes or result rows.
    if not calculate_linrui and not calculate_hao:
        return comparison_metrics, ground_summary

    # Validate before creating a run ID, temporary files, Radiance scenes, or CSV rows.
    validate_cell_array_fit(design, module_spec)

    original_directory = Path.cwd().resolve()
    run_id = uuid4().hex[:8]
    constructions = (
        ("semi_transparent", SETTINGS.xgap_semi_transparent),
        ("conventional", design.xgap_conventional),
    )
    unshaded_ground_reference = None if calculate_hao else 0.0

    with TemporaryDirectory(prefix=f"agripv_comparison_{run_id}_") as temporary_directory:
        try:
            for pv_type, module_xgap in constructions:
                context = create_period_scene(
                    design,
                    scenario,
                    module_spec,
                    array_spec,
                    pv_type,
                    module_xgap,
                    run_id,
                    Path(temporary_directory) / pv_type,
                    create_direct_octree=calculate_linrui,
                    unshaded_ground_reference=unshaded_ground_reference,
                )
                if unshaded_ground_reference is None:
                    unshaded_ground_reference = (
                        context.unshaded_ground_irradiation_Wh_m2_period
                    )

                if calculate_hao:
                    construction_metrics = analyze_array(
                        context,
                        design,
                        module_spec,
                        array_spec,
                    )
                    comparison_metrics.update(
                        {
                            f"{pv_type}_{name}": value
                            for name, value in construction_metrics.items()
                        }
                    )

                if calculate_linrui or calculate_hao:
                    ground_components, ground_shading_loss = analyze_ground(
                        context,
                        design,
                        module_spec,
                        array_spec,
                        calculate_components=calculate_linrui,
                        calculate_shading=calculate_hao,
                    )
                    if calculate_linrui:
                        ground_summary[pv_type] = ground_components
                    if calculate_hao:
                        shading_metrics[
                            f"{pv_type}_ground_shading_loss_fraction_period"
                        ] = ground_shading_loss
        finally:
            # Leave RadianceObj's working directory before temporary cleanup.
            os.chdir(original_directory)

    comparison_metrics.update(shading_metrics)

    save_selected_results(
        design,
        scenario,
        module_spec,
        array_spec,
        comparison_metrics,
        ground_summary,
        calculate_linrui,
        calculate_hao,
    )
    return comparison_metrics, ground_summary
