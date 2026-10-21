# Soil Conditions and Python-Python

## Nitrogen extension added 2026-10-20-

Use `02_WLP_Model/Nitrogen_Extension/README.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling.

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed.

- `BK50_Official_Database-BK50.zip`: complete official database.
- `Soil_Inputs/`: candidate units, ONP extract and prepared soil profile.
- `BK50_Extractor.py`: extract a reviewed soil code from the database.
- `BK50_Profile_Adapter.py`: prepare the explicit demonstration hydraulic profile.
- `Field_Definitions/` and `Model_References/`: definitions and references.

For extraction, first install `Extraction_Requirements.txt`.

```powershell
python -m pip install -r "04_Soil_and_Python/Extraction_Requirements.txt"
python "04_Soil_and_Python/BK50_Extractor.py" --unit L5102_K342
```

The example code is a nearby candidate, not an identified APV field. Do not convert a groundwater/stagnation unit into a freely draining soil by renaming it.

Raw paths such as `BK50_GPKG/BK50_A.gpkg` refer to files inside the original official ZIP. / `BK50_GPKG/BK50_A.gpkg`  ZIP .
