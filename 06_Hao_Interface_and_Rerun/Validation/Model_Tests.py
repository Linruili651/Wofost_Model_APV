"""Software/physics checks; synthetic shade/rain are NEVER APV observations."""

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry["install"]()
_registry["load_module"]("RE")
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd


from crop_engine import ModelConfig,GroundGrid,prepare_weather,run_point,evaluate,crop_catalog,load_parameters
from RE import evaluate_crop_yield


class ModelChecks(unittest.TestCase):
    def test_calendar_and_harvest_organ_contract(self):
        self.assertEqual(set(crop_catalog()),{"winter_wheat","spring_barley","grain_maize","potato","sugar_beet","soybean"})
        self.assertEqual(ModelConfig(crop_id="winter_wheat").weather_config().start,"2001-10-15")
        self.assertEqual(ModelConfig(crop_id="spring_barley").weather_config().start,"2002-03-26")
        self.assertEqual(crop_catalog()["potato"]["organ"],"tuber")
        self.assertEqual(crop_catalog()["sugar_beet"]["organ"],"storage_root")

    def test_all_crops_soil_and_root_boundaries(self):
        for crop_id in crop_catalog():
            config=ModelConfig(crop_id=crop_id,mode="WLP_MLWB",accept_demo_assumptions=True)
            crop,soil,site,info=load_parameters(config)
            layers=soil["SoilProfileDescription"]["SoilLayers"]
            lower=np.cumsum([l["Thickness"] for l in layers])
            self.assertAlmostEqual(float(lower[-1]),200)
            self.assertTrue(np.any(np.isclose(lower,crop["RDMCR"])))
            self.assertTrue(np.any(np.isclose(lower,166)))
            self.assertTrue(all(5<=l["Thickness"]<=20.000001 for l in layers))
            self.assertLessEqual(crop["RDMCR"],105)
            self.assertEqual(info["soil_unit"],"L5102_K342")

    def test_rain_response_and_water_conservation(self):
        config=ModelConfig(crop_id="winter_wheat",accept_demo_assumptions=True)
        frame,_=prepare_weather(config)
        wet_pp=run_point(frame,config)
        dry_pp=run_point(frame,config,effective_rain=np.zeros(len(frame)))
        self.assertAlmostEqual(wet_pp["storage_organ_DM_kg_ha"],7992.376529021289,places=6)
        self.assertAlmostEqual(wet_pp["storage_organ_DM_kg_ha"],dry_pp["storage_organ_DM_kg_ha"],places=8)
        self.assertIsNone(wet_pp["water"]["drainage_bottom_mm"])
        wlp=replace(config,mode="WLP_MLWB")
        wet=run_point(frame,wlp)
        dry=run_point(frame,wlp,effective_rain=np.zeros(len(frame)))
        self.assertLess(dry["storage_organ_DM_kg_ha"],wet["storage_organ_DM_kg_ha"])
        self.assertGreater(wet["water"]["drainage_bottom_mm"],0)
        self.assertLess(abs(wet["water_balance_residual_mm"]),0.001)
        self.assertLess(abs(dry["water_balance_residual_mm"]),0.001)
        self.assertGreater(wet["soil_daily"].groupby("layer").SM_m3_m3.std().max(),0.001)

    def test_daily_point_interface_and_missing_input(self):
        config=ModelConfig(crop_id="spring_barley",accept_demo_assumptions=True)
        weather,_=prepare_weather(config)
        grid=GroundGrid(nx=2,ny=1)
        baseline,_=evaluate(config,grid=grid)
        rows=[]
        for _,point in grid.points().iterrows():
            for day,rad in zip(weather.day,weather.IRRAD):
                rows.append(dict(day=day,scenario_id="synthetic_software_test_only",
                    point_id=point.point_id,x_m=point.x_m,y_m=point.y_m,cell_area_m2=point.cell_area_m2,
                    total_Wh_m2_day=rad/3600,effective_rain_mm_day=float(weather.loc[weather.day==day,"RAIN_mm_day"].iloc[0])))
        table=pd.DataFrame(rows)
        result,folder=evaluate(config,radiation=table,scenario_id="synthetic_software_test_only",
            provenance={"source":"synthetic unit test: same radiation as natural; NOT Tianze/APV data"},grid=grid,baseline=baseline)
        self.assertAlmostEqual(result["relative_yield_to_natural"],1.0,places=10)
        self.assertAlmostEqual(result["yield_kg_DM_ha"],baseline["yield_kg_DM_ha"],places=8)
        self.assertEqual(len(pd.read_csv(folder/"Point_Summary.csv")),2)
        with self.assertRaises(ValueError):
            evaluate(config,radiation=table.iloc[:-1],scenario_id="synthetic_software_test_only",
                provenance={"source":"deliberate missing-day test"},grid=grid)
        invalid=table.copy();invalid.loc[0,"effective_rain_mm_day"]=-1
        with self.assertRaises(ValueError):
            evaluate(config,radiation=invalid,scenario_id="synthetic_software_test_only",
                provenance={"source":"deliberate invalid-rain test"},grid=grid)
        with self.assertRaises(ValueError):
            evaluate(config,radiation=table,scenario_id="synthetic_software_test_only",
                provenance={"source":"mismatched-baseline test"},grid=grid,
                baseline={"scenario_id":"natural_light","comparison_fingerprint":"wrong_crop_or_mode"})

    def test_hao_wrapper_uses_real_storage_organ_model(self):
        data,folder=evaluate_crop_yield(crop_id="potato",mode="PP",accept_demo_assumptions=True,return_details=True)
        self.assertEqual(data["harvest_organ"],"tuber")
        self.assertNotIn("total_grain_DM_kg_on_plot",data)
        self.assertIsNone(data["fresh_or_marketable_yield_t_ha"])
        self.assertIsNone(data["nitrogen_leaching_kg_N_ha"])
        self.assertGreater(data["yield_kg_DM_ha"],0)

    def test_assumptions_require_explicit_selection(self):
        frame,_=prepare_weather(ModelConfig())
        with self.assertRaises(ValueError):run_point(frame,ModelConfig())


if __name__=="__main__":unittest.main(verbosity=2)
