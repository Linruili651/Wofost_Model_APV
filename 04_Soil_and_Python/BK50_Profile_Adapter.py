"""Explicit, uncalibrated hydraulic-curve preparation from a reviewed BK50 ONP extract."""

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry["install"]()
from copy import deepcopy
from pathlib import Path
import argparse
import json
import math

ROOT = _package_root
HYDRAULIC_REFERENCE = "https://escomp.github.io/CTSM/release-clm5.0/tech_note/Hydrology/CLM50_Tech_Note_Hydrology.html"


def prepare_demo(source_path=None, output_path=None):
    source_path = Path(source_path or ROOT / "04_Soil_and_Python/Soil_Inputs/Selected_ONP_Demo.json")
    output_path = Path(output_path or ROOT / "04_Soil_and_Python/Soil_Inputs/Soil_Profile_Demo.json")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    rows = sorted(source["rows"], key=lambda row: row["NR_SCH"])
    if not rows or any(row["GW_STUFE"] != 0 or row["SW_STUFE"] != 0 for row in rows):
        raise ValueError("This adapter supports only an explicitly selected GW0/SW0 freely draining demonstration.")
    layers, fits, excluded = [], [], []
    for row in rows:
        upper, lower = float(row["SUM_DICKE_OBEN"]) * 10, float(row["SUM_DICKE_SCH"]) * 10
        if upper >= 200 or lower <= upper:
            excluded.append(dict(layer=row["NR_SCH"], reason="ONP layer begins beyond the 200cm analysis window; capped cumulative bottom is not greater than top.", row=row))
            continue
        # ONP fields are water mm per dm soil: divide by 100 for m3/m3.
        fc = float(row["FK_SCH"]) / 100
        wp = (float(row["FK_SCH"]) - float(row["NFK_SCH"])) / 100
        sat = (float(row["FK_SCH"]) + float(row["LK_SCH"])) / 100
        ks = float(row["KF_SCH"])
        if not 0 < wp < fc < sat < 1 or ks <= 0:
            raise ValueError(f"Invalid water-content anchors in soil layer {row['NR_SCH']}")
        # Clapp-Hornberger/Campbell power-law shape, fitted to ONP pF=2.5 and 4.2 anchors.
        # The shape and unsaturated K are estimated, not measured BK50 curves.
        b = math.log(10 ** (4.2 - 2.5)) / math.log(fc / wp)
        air_entry_cm = 10 ** 2.5 * (fc / sat) ** b
        air_entry_pf = math.log10(air_entry_cm)
        pfs = sorted(set([-1., 0., 1., 1.5, 2., 2.5, 3., 3.5, 4., 4.2, 4.5, 5., 6., air_entry_pf]))
        sm, cond = [], []
        for pf in pfs:
            theta = min(sat, sat * (10 ** pf / air_entry_cm) ** (-1 / b))
            logk = math.log10(ks) + (2 * b + 3) * math.log10(theta / sat)
            sm.extend([pf, theta]); cond.extend([pf, logk])
        # Minor rounding differences exist between raw DICKE_SCH and cumulative boundaries.
        # Use documented cumulative top/bottom for a continuous profile, not a 0.1dm overlap.
        layer = dict(SoilID=f"{row['EINHEIT_NAME']}_layer_{row['NR_SCH']}",
                     Thickness=lower-upper, SMfromPF=sm, CONDfromPF=cond,
                     RHOD=float(row["LD_SCH"]), CRAIRC=0.06,
                     FSOMI=0.0, CNRatioSOMI=10.0, Soil_pH=6.5)
        # FSOMI/C:N/pH are interface placeholders UNUSED by WLP; never pass them into SNOMIN.
        layers.append(layer)
        fits.append(dict(layer=row["NR_SCH"], upper_cm=upper, lower_cm=lower,
                         raw_DICKE_SCH_dm=row["DICKE_SCH"], theta_fc=fc, theta_wp=wp, theta_sat=sat,
                         Ks_cm_day=ks, fitted_b=b, air_entry_cm=air_entry_cm,
                         density_source="BK50 LD_SCH estimated bulk density"))
    result = dict(status="BK50_DERIVED_UNCALIBRATED_DEMONSTRATION", field_validated=False,
                  source=source, hydraulic_fit=fits, excluded_rows=excluded,
                  demonstration_soil_root_limit_cm=float(source["selected_map_feature"]["TIEFE"])*10,
                  SoilProfileDescription=dict(PFFieldCapacity=2.5, PFWiltingPoint=4.2,
                    SurfaceConductivity=float(rows[0]["KF_SCH"]), SoilLayers=layers,
                    SubSoilType=dict(deepcopy(layers[-1]), Thickness=200.), GroundWater=None),
                  assumptions=["Nearby illustrative soil, not an identified APV field.",
                    "Full mapped 0-200cm profile; effective rooting depth is separate.",
                    "Power-law curves fitted to FC/WP and Ks; unsaturated K is not measured.",
                    "CRAIRC=0.06 is an uncalibrated aeration threshold.",
                    "FSOMI, C:N and pH are unused WLP interface placeholders; NOT nitrogen inputs.",
                    "No groundwater, preferential flow, snow/ice, panel runoff redistribution or lateral flow."],
                  hydraulic_reference=HYDRAULIC_REFERENCE,
                  nitrogen_inputs_ready=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    data=prepare_demo(args.source,args.output)
    print(data["status"], "layers:", len(data["SoilProfileDescription"]["SoilLayers"]))
