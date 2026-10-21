# Soil Conditions and Python-土壤条件与Python

## Nitrogen extension added 2026-10-20-已新增氮淋失扩展

Use `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/README-说明.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling. / 已新增WOFOST81/SNOMIN入口，六作物有来源技术对照水氮及同版本PP81/WLP81共18组完成；六组Aachen地块检查均因缺项明确停止。旧WOFOST73的PP/WLP仍不计算土壤氮循环。参数、缺项与边界见扩展说明。

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed. / 本次不宣称已完成实际整季农业光伏水氮耦合；Hao现有实验范围仍为已确认的四组。

- `BK50_Official_Database-BK50官方数据库.zip`: complete official database. / 完整官方数据库。
- `Soil_Inputs-土壤输入/`: candidate units, ONP extract and prepared soil profile. / 候选土壤、ONP 土层提取与模型剖面。
- `BK50_Extractor-BK50数据提取.py`: extract a reviewed soil code from the database. / 按复核后的土壤代码提取数据。
- `BK50_Profile_Adapter-BK50剖面适配.py`: prepare the explicit demonstration hydraulic profile. / 整理明确标注假设的演示水力剖面。
- `Field_Definitions-字段说明/` and `Model_References-模型依据/`: definitions and references. / 字段定义和模型依据。

For extraction, first install `Extraction_Requirements-土壤提取依赖.txt`. / 提取前先安装本目录的土壤提取依赖。

```powershell
python -m pip install -r "04_Soil_and_Python-土壤条件与Python/Extraction_Requirements-土壤提取依赖.txt"
python "04_Soil_and_Python-土壤条件与Python/BK50_Extractor-BK50数据提取.py" --unit L5102_K342
```

The example code is a nearby candidate, not an identified APV field. Do not convert a groundwater/stagnation unit into a freely draining soil by renaming it. / 示例代码对应附近候选土壤，并非已确认农光伏地块；不能通过改名把地下水或滞水土壤当作自由排水土壤。

Raw paths such as `BK50_GPKG/BK50_A.gpkg` refer to files inside the original official ZIP. / `BK50_GPKG/BK50_A.gpkg` 等原始路径指官方 ZIP 内部文件。
