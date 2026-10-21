# Execution Summary-运行汇总

## Experiment scope confirmed by Hao-据Hao说明确认的实验范围

Panel type and mounting form are separate factors. Conventional means traditional opaque PV; semi-transparent is the other panel type. Fixed tilt, single-axis tracking and vertical PV are three mounting forms. Their full combination gives six cases. / 组件类型与安装形式是两个独立维度：传统组件（conventional）与半透明组件；固定倾角、单轴跟踪和垂直安装是三种安装形式，全部组合共六组。

| Mounting form-安装形式 | Conventional-传统组件 | Semi-transparent-半透明组件 |
| --- | --- | --- |
| Fixed tilt-固定倾角 | Within Hao's stated scope / Hao已做范围 | Within Hao's stated scope / Hao已做范围 |
| Single axis-单轴跟踪 | Within Hao's stated scope / Hao已做范围 | Outside Hao's stated scope / Hao未做 |
| Vertical-垂直安装 | Within Hao's stated scope / Hao已做范围 | Outside Hao's stated scope / Hao未做 |

Hao's stated scope therefore contains **four cases**, with the two semi-transparent extensions excluded because of time constraints. This scope comes from the user's relay of Hao's explanation, not an independent audit of Hao's full experimental results. / 因此，Hao说明的现有范围为**四组**；受时间限制，单轴半透明与垂直半透明两组未做。该范围依据用户转述Hao的说明，未独立核验Hao的完整实验结果。

The three notebooks stored here contain both construction branches. Codex's previous one-hour checks exercised all six combinations in these copies. Those checks establish short-run code execution only; they do not establish six completed formal experiments by Hao. Preserve these test records as technical evidence, and keep the two additional semi-transparent checks outside Hao's four-case experimental scope. / 本目录三个笔记本的代码含两种组件分支，Codex此前的一小时检查确实运行了六种组合；这只说明这些代码分支可以短时执行，不代表Hao完成了六组正式实验。保留运行记录作为技术检查证据，其中新增的两组半透明测试不计入Hao现有四组实验。

The existing six-crop × PP/WLP natural-light baseline (12 runs) is a separate crop-model check. It does not establish completion of these four APV cases coupled to the crop model. / 之前六种作物×PP/WLP的12组自然光基线属于另一项作物模型检查，不能据此认为这四组农业光伏方案已与作物模型全部耦合完成。

All three models completed actual Radiance calculations, including both constructions, both PV faces and ground direct/diffuse/total results. / 三个模型都完成了实际Radiance计算，覆盖两种组件结构、板面正背面、地面直射/散射/总辐射。

**Scope / 范围：** Aachen TMY, 2024-06-21 12:00–13:00 local standard time (end exclusive); 2×2 modules; 4×4 ground sensors; original 6×24 cell layout; low accuracy; two workers. Both recipient output switches enabled in the executed copy. / Aachen典型年天气、当地标准时2024年6月21日12至13时（不含13时）；2×2组件；4×4地面点；原6×24电池片布局；low精度；两个工作线程；执行副本启用两类输出。

| Model-模型 | Status-状态 | New outputs-新生成结果 | Time-耗时 |
| --- | --- | --- | --- |
| `fixed_tilt` / 固定倾角 | Passed / 成功 | Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao逐小时1行4个能量值；Linrui时段汇总1行6个地面能量值。 | 31.88 s / 秒 |
| `vertical_pv` / 垂直光伏 | Passed / 成功 | Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao逐小时1行4个能量值；Linrui时段汇总1行6个地面能量值。 | 23.26 s / 秒 |
| `single_axis` / 单轴跟踪 | Passed / 成功 | Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao逐小时1行4个能量值；Linrui时段汇总1行6个地面能量值。 | 28.07 s / 秒 |

## Numerical values-数值记录

All entries below are Wh integrated over the corresponding array or evaluation land, for this one-hour case. Different geometries have different evaluation footprints; do not interpret these land-integrated totals as area-normalized comparisons. / 下表均为本次一小时算例对相应阵列或评价土地积分后的Wh。不同几何的评价面积不同，土地积分总值不能直接当作单位面积对比。

| Model-模型 | Semi front-半透明正面 | Semi effective rear-半透明有效背面 | Opaque front-常规正面 | Opaque effective rear-常规有效背面 | Semi ground total-半透明地面总量 | Opaque ground total-常规地面总量 |
| --- | --- | --- | --- | --- | --- | --- |
| 固定倾角 | 8648.963 | 1152.251 | 9367.461 | 1244.732 | 32214.448 | 32099.256 |
| 垂直光伏 | 2481.280 | 1305.557 | 2682.054 | 1409.246 | 28564.972 | 27086.713 |
| 单轴跟踪 | 7820.693 | 1135.675 | 8469.585 | 1223.462 | 32811.302 | 32689.300 |

The ground diffuse column is total minus the direct-only trace, so it includes scattered/reflected contributions. / 地面散射列按总量减直射量计算，包含散射与反射贡献。

## Evidence and limits-证据与边界

- `Run_Results-运行结果/`: each model has the actual executed notebook, two new CSVs, execution log and structured record. Original notebook saved outputs are not used as evidence for this run. / 每个模型均保存实际执行副本、两个新CSV、日志和结构化记录；原文件自带历史输出不作为本次成功证据。
- Checks passed: unchanged source hashes; four finite positive PV energy values; six finite nonnegative ground values; direct + diffuse = total; one row per output; valid executed notebooks; tracker angle within ±45°. These are execution and internal-consistency checks, not experimental validation. / 来源哈希一致、四个板面值有限且为正、六个地面值有限且非负、直射加散射等于总量、输出行数及执行笔记本格式均通过；跟踪角在±45°内。这些属于执行与内部一致性检查，并非实验校准。
- No default full-period runs, full-season runs or crop/soil coupling were performed. This run does not validate soil layers, rooting depth, nitrogen loss, rain redistribution or electrical yield. / 本次未运行原默认完整时段、完整生长季或作物土壤耦合，不验证土壤分层、扎根深度、氮流失、降雨重分配或发电量。
- `single_axis` has both outputs disabled by default, and `vertical_pv` has the ground output disabled. The explicit override cell enables them for this check. / 单轴原件两个输出默认关闭，垂直原件地面输出默认关闭；本次用明确覆盖单元打开。
- `Tested_Environment-测试环境.json` and `Tested_Requirements-测试环境依赖.txt` record the separate Python 3.13.5 radiation environment and Radiance 6.0.2. The existing PCSE crop environment was left untouched. / 独立辐射环境记录为Python3.13.5和Radiance6.0.2，原有PCSE作物环境未修改。
