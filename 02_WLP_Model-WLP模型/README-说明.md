# WLP Model-WLP模型

## Adaptive inputs / 第二种实验：目标补水补氮

使用同目录 `Nitrogen_Extension-氮淋失扩展/Start_Target_Inputs-后台启动.ps1` 开始或恢复。规则、初始条件、来源及输出路径见 `Nitrogen_Extension-氮淋失扩展/README_Target_Inputs-目标补水补氮说明.md`。新队列采用WOFOST81/SNOMIN，相同规则计算实际补水、补氮及氮淋失，并检查共同产量目标；原WLP73入口仍是雨养水分模拟。

## Nitrogen extension added 2026-10-20-已新增氮淋失扩展

Use `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/README-说明.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling. / 已新增WOFOST81/SNOMIN入口，六作物有来源技术对照水氮及同版本PP81/WLP81共18组完成；六组Aachen地块检查均因缺项明确停止。旧WOFOST73的PP/WLP仍不计算土壤氮循环。参数、缺项与边界见扩展说明。

The active full-season scope is open field, fixed-tilt conventional PV and fixed-tilt semi-transparent PV. Tracking/vertical cases are excluded. The adaptive-input queue uses estimated/reference soil-N conditions and is not a field-validated nitrogen experiment. / 当前范围为露天及两种固定板，未包含跟踪和垂直系统；目标补给队列采用估计/参考氮条件，非田间验证实验。

Run `Run_WLP-运行WLP.ipynb` or `Run_WLP-运行WLP.py`. / 运行本目录的 WLP 笔记本或 Python 入口。

The model is Wofost73_WLP_MLWB. Soil inputs come from `../04_Soil_and_Python-土壤条件与Python/Soil_Inputs-土壤输入/`. / 模型为 Wofost73_WLP_MLWB，土壤输入位于土壤目录。

It calculates root uptake, layered storage/flow, evaporation, transpiration, runoff and bottom drainage. Nitrogen leaching is not included. / 计算根系吸水、分层储水与水流、蒸发、蒸腾、径流和底部排水，不含氮淋失。

Results: `../06_Hao_Interface_and_Rerun-Hao接口与复跑/Rerun_Results-复跑结果/WLP_MLWB-分层水分限制/`. / 结果保存在 Hao 文件夹的 WLP 复跑目录。

The demonstration soil and water curves require field review and calibration. / 演示土壤和水力曲线仍需实际地块复核与标定。
