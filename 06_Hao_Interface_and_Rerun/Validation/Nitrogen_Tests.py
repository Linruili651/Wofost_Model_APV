"""Water/N mass balance, input-source guards and spatial coupling checks / , . """
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
import hashlib,json,runpy,unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
registry=runpy.run_path(str(ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
registry['install']();n=registry['load_module']('nitrogen_engine');api=registry['load_module']('RE')

class NitrogenChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=n.NitrogenConfig(crop_id='spring_barley',nitrogen_inputs=n.REFERENCE,
            accept_reference_scenario=True,accept_demo_assumptions=True)
        cls.data=n.load_inputs(cls.cfg)

    def test_field_unknowns_remain_blocked_for_all_six(self):
        for crop in n.base.crop_catalog():
            cfg=replace(self.cfg,crop_id=crop,nitrogen_inputs=n.DEFAULT_FIELD,accept_reference_scenario=False)
            data=n.load_inputs(cfg);issues=n.preflight(data,cfg)
            self.assertIsNone(data['site']['NO3I']);self.assertIsNone(data['site']['NH4I'])
            self.assertIsNone(data['fertilizer_events_by_crop'][crop])
            self.assertIn('site.NO3I',issues);self.assertTrue(any('field_sources.' in s for s in issues))
            with self.assertRaises(n.MissingNitrogenInputs):n.evaluate(cfg)

    def test_reference_requires_explicit_flag_and_unknown_is_not_zero_fertilizer(self):
        self.assertTrue(n.preflight(self.data,replace(self.cfg,accept_reference_scenario=False)))
        unknown=deepcopy(self.data);unknown['fertilizer_events']=None
        self.assertTrue(any('fertilizer_events' in i for i in n.preflight(unknown,self.cfg)))
        with self.assertRaises(ValueError):
            api.evaluate_crop_yield(crop_id='spring_barley',mode='NWLP_MLWB_SNOMIN',nitrogen_inputs=n.REFERENCE,
                accept_demo_assumptions=True,accept_reference_scenario=True)

    def test_all_crop_layer_refinement_preserves_nitrogen_and_sources(self):
        for crop in n.base.crop_catalog():
            _,soil,site,info=n.parameters(replace(self.cfg,crop_id=crop),self.data)
            self.assertAlmostEqual(sum(site['NO3I']),30.0)
            self.assertAlmostEqual(sum(site['NH4I']),5.0)
            depths=np.cumsum([l['Thickness'] for l in soil['SoilProfileDescription']['SoilLayers']])
            self.assertAlmostEqual(depths[-1],120.)
            self.assertTrue(np.any(np.isclose(depths,info['applied_root_limit_cm'])))
        manifest=json.loads((n.INPUTS/'Source_Manifest.json').read_text(encoding='utf-8'))
        for entry in manifest:
            self.assertEqual(hashlib.sha256((n.INPUTS/entry['path']).read_bytes()).hexdigest(),entry['sha256'])

    def test_eighteen_reference_runs_and_boundary_accounting(self):
        path=ROOT/'06_Hao_Interface_and_Rerun/Rerun_Results/Nitrogen_Verification/Reference_Runs.json'
        rows=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(rows),18)
        for row in rows:
            self.assertEqual(row['status'],'reference_only_mature')
            payload=json.loads((ROOT/row['output_directory']/'Hao_Crop_Water_Nitrogen.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['executed_engine_sha256'],json.loads((ROOT/'TRANSLATION_VERIFICATION.json').read_text(encoding='utf-8'))['source_engine_sha256'])
            self.assertFalse(payload['eligible_for_field_optimization'])
            if row['mode']=='NWLP_MLWB_SNOMIN':
                self.assertGreaterEqual(row['nitrogen_leaching_kg_N_ha'],0.)
                self.assertLess(row['water_balance_max_abs_residual_mm'],0.001)
                self.assertLess(row['nitrogen_balance_max_abs_residual_kg_N_ha'],0.001)
                daily=pd.read_csv(ROOT/row['output_directory']/'Daily_Water_Nitrogen.csv')
                soil=pd.read_csv(ROOT/row['output_directory']/'Daily_Soil_Nitrogen.csv')
                self.assertGreaterEqual(soil[['nitrate_N_kg_ha','ammonium_N_kg_ha']].to_numpy().min(),-1e-8)
                self.assertAlmostEqual(daily.nitrate_leaching_kg_N_ha_day.sum()+daily.ammonium_leaching_kg_N_ha_day.sum(),row['nitrogen_leaching_kg_N_ha'],places=8)
                self.assertAlmostEqual(payload['pcse_native_nitrate_last_layer_out_kg_N_ha']+payload['pcse_native_ammonium_last_layer_out_kg_N_ha'],
                    payload['nitrogen_leaching_kg_N_ha']+payload['last_layer_internal_upward_N_kg_N_ha'],places=8)
                if row['crop_id']=='soybean':self.assertGreater(row['biological_N_fixation_kg_N_ha'],0.)
            else:self.assertIsNone(row['nitrogen_leaching_kg_N_ha'])

    def test_published_mineral_fertilizer_event_and_n_balance(self):
        cfg=replace(self.cfg,crop_id='potato')
        frame,_=n.base.prepare_weather(cfg.base_config());data=deepcopy(self.data)
        # Official notebook cell 30 May-1 event; year relabelled to synthetic TMY only.
        data['fertilizer_events']=[dict(date='2002-05-01',amount=85.,application_depth=10.,cnratio=0.,
            f_orgmat=0.,f_NH4N=0.5,f_NO3N=0.5,initial_age=0.,source=data['source']+'; cell 30; reference-only year relabelling')]
        result=n.run_point(frame,cfg,data)
        self.assertAlmostEqual(result['fertilizer_N_applied_kg_N_ha'],85.,places=8)
        self.assertLess(abs(result['nitrogen_balance_residual_kg_N_ha']),0.001)
        n.base.save_json(ROOT/'06_Hao_Interface_and_Rerun/Validation/Fertilizer_Check.json',
            dict(case='published potato May-1 event, synthetic year, technical test only / PotatoTMY, ',
                event=data['fertilizer_events'][0],applied_N_kg_ha=result['fertilizer_N_applied_kg_N_ha'],
                nitrogen_balance_residual_kg_N_ha=result['nitrogen_balance_residual_kg_N_ha']))

    def test_pointwise_radiation_rain_interface_and_same_input_identity(self):
        cfg=self.cfg;grid=n.base.GroundGrid(nx=2,ny=1)
        frame,_=n.base.prepare_weather(cfg.base_config())
        baseline,_=n.evaluate(cfg,grid=grid)
        rows=[]
        for _,point in grid.points().iterrows():
            for day,light,rain in zip(frame.day,frame.IRRAD,frame.RAIN_mm_day):
                rows.append(dict(day=day,scenario_id='synthetic_n_interface_test',point_id=point.point_id,
                    x_m=point.x_m,y_m=point.y_m,cell_area_m2=point.cell_area_m2,
                    total_Wh_m2_day=light/3600,effective_rain_mm_day=rain))
        table=pd.DataFrame(rows)
        payload,_=n.evaluate(cfg,radiation=table,scenario_id='synthetic_n_interface_test',
            provenance={'source':'Software test: same natural radiation/rain at both points; not APV observations / , '},grid=grid,baseline=baseline)
        self.assertAlmostEqual(payload['relative_yield_to_natural'],1.,places=8)
        self.assertAlmostEqual(payload['nitrogen_leaching_kg_N_ha'],baseline['nitrogen_leaching_kg_N_ha'],places=8)
        with self.assertRaises(ValueError):n.evaluate(cfg,radiation=table.iloc[:-1],scenario_id='synthetic_n_interface_test',provenance={'source':'missing-day test'},grid=grid)

if __name__=='__main__':unittest.main(verbosity=2)
