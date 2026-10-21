"""Hao optimizer entry: actual WOFOST model execution, no radiation-times-factor placeholder."""

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry["install"]()
from crop_engine import ModelConfig, evaluate, GroundGrid


def evaluate_crop_yield(radiation_input=None, *, crop_id="winter_wheat", mode="PP",
                        scenario_id="natural_light", provenance=None, grid=None,
                        accept_demo_assumptions=False, baseline=None, return_details=False,
                        nitrogen_inputs=None, accept_reference_scenario=False, harvest_year=2002):
    """Return storage-organ dry matter kg/ha, or (payload, run_dir) when requested.

    radiation_input: daily-by-point DataFrame or CSV filename for APV; None for natural light.
    The schema is described in 00_Handoff_Guide.md. An incomplete grain season raises instead of
    returning an invented zero. Price/fresh-weight conversions belong to the caller.
    """
    if mode in ("NWLP_MLWB_SNOMIN", "PP81", "WLP81"):
        n = _registry["load_module"]("nitrogen_engine")
        config = n.NitrogenConfig(crop_id=crop_id, mode=mode, harvest_year=harvest_year,
            nitrogen_inputs=nitrogen_inputs or n.DEFAULT_FIELD,
            accept_reference_scenario=accept_reference_scenario,
            accept_demo_assumptions=accept_demo_assumptions)
        # Source examples are for technical validation, never silently enter field optimization.
        data = n.load_inputs(config)
        if data.get("scenario_kind") == "reference_only" and not return_details:
            raise ValueError("Reference-only nitrogen scenarios require return_details=True; not eligible for field optimization / ")
        payload, folder = n.evaluate(config, radiation=radiation_input, scenario_id=scenario_id,
            provenance=provenance, grid=grid, baseline=baseline)
        if return_details:
            return payload, folder
        if not payload.get("eligible_for_field_optimization") or payload.get("yield_kg_DM_ha") is None:
            raise ValueError("Nitrogen result not eligible for field optimization / ")
        return float(payload["yield_kg_DM_ha"])
    config=ModelConfig(crop_id=crop_id,mode=mode,harvest_year=harvest_year,accept_demo_assumptions=accept_demo_assumptions)
    payload,folder=evaluate(config,radiation=radiation_input,scenario_id=scenario_id,
                            provenance=provenance,grid=grid,baseline=baseline)
    if return_details:
        return payload,folder
    if payload["yield_kg_DM_ha"] is None:
        raise ValueError(f"Grain not mature at cutoff; do not optimise this result. See {folder}")
    return float(payload["yield_kg_DM_ha"])


def evaluate_crop_water_nitrogen(radiation_input=None, **kwargs):
    """Return (water/N payload, run directory); missing field inputs raise explicitly.
    ; . . 
    """
    kwargs.setdefault("mode", "NWLP_MLWB_SNOMIN")
    kwargs["return_details"] = True
    return evaluate_crop_yield(radiation_input, **kwargs)
