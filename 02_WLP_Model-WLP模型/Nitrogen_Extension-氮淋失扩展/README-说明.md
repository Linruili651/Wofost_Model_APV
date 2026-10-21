# Nitrogen Extension Handoff-氮淋失扩展交接说明

Updated / 更新：2026-10-20（Europe/Berlin）。

## Delivered behavior-本次交付

The new `NWLP_MLWB_SNOMIN` entry couples WOFOST 8.1, multilayer soil water and SNOMIN soil carbon/nitrogen. It calculates layer NH4/NO3 stocks, crop soil-N uptake, biological fixation, mineralisation/nitrification/denitrification and soil-water-driven N transport. / 新入口将WOFOST8.1、多层水分平衡与SNOMIN碳氮模块接入，输出分层铵态氮/硝态氮、土壤供氮吸收、固氮、矿化/硝化/反硝化及随土层水流迁移的氮。

**Six reference nitrogen runs succeeded; six Aachen field cases are blocked by explicitly listed missing inputs. This is not six calibrated Aachen nitrogen-leaching estimates.** / **六种作物的有来源技术对照水氮运行均成功；六种作物的Aachen地块计算均因明确缺项而被阻止，不是六组已校准的Aachen氮淋失估计。**

The historical WOFOST7.3 PP/WLP entries and results remain available. Matching WOFOST8.1 `PP81` and `WLP81` reference checks were also run: six crops × three modes = 18 new reference runs. Use version-matched comparisons; an old 7.3 yield minus a new 8.1 yield does not isolate nitrogen effects. / 保留旧WOFOST7.3的PP/WLP入口与结果；另补跑同版本8.1的PP81与WLP81，共六作物×三种模式=18组新技术对照，避免把版本差异当成氮效应。

## Inputs and their evidence-输入与来源

| Input-输入 | Evidence-来源及处理 |
| --- | --- |
| Six crop parameter sets-六作物参数 | Downloaded the official WOFOST81 branch at a fixed commit; kept the existing six variety IDs. Full original YAML, URLs and SHA-256 are included. Generic source parameters, not local calibration. / 固定提交下载官方8.1参数，保留原六品种编号；原YAML、URL及哈希齐全，未冒充本地校准。 |
| Soil organic matter, pH, C:N, initial NH4/NO3-土壤有机质、pH、碳氮比与初始矿质氮 | Official PCSE notebook 12 provides a complete Dutch demonstration profile: 25/15/20/60 cm, total 120 cm, with sourced values. Used only in the explicitly enabled technical reference. / 官方示例提供25/15/20/60cm、总深120cm的完整荷兰示例剖面，仅用于明确启用的技术对照。 |
| SNOMIN reaction parameters-氮转化参数 | Published notebook values and the exact installed PCSE6.0.13 site-provider source are archived. They are model references, not measured Aachen rate constants. / 归档官方示例值及已装PCSE6.0.13的参数源文件，不冒充Aachen实测速率。 |
| Regional mineral N-NRW矿质氮参考 | Archived NRW 2026 winter/summer Nmin pages. They provide regional seasonal mineral-N totals; they do not supply the required field/date/species-specific full-profile initial conditions. / 已下载NRW冬夏作物Nmin资料；区域时段总矿质氮不能直接拆分为本地全剖面的硝态/铵态氮初值。 |
| Fertilization-施肥 | Field records remain null. The reference is an explicitly unfertilised technical control ([]), not an unknown field filled with zero. A separate software check uses the official potato May-1 event, 85 kg N/ha, relabelled to the synthetic year. / 地块施肥保留null；技术对照明确设为不施肥处理[]，不将未知当零。另以官方马铃薯5月1日85kgN/ha事件改为拼接年份，单独检查施肥信号。 |
| Aachen initial N and organic/pH profile-Aachen地块初值 | Remain null pending actual plot confirmation, dated soil observations and sourced management. The old WLP FSOMI=0/C:N=10/pH=6.5 placeholders are explicitly removed from the new field template. / 待确认地块、起始日土样和有来源的管理信息；新地块模板已移除旧WLP的有机质0、碳氮比10、pH6.5占位值。 |

`Aachen_Field_Inputs-Aachen地块待补输入.json` is the strict default. Both values and `field_sources` must be completed, and resolved items removed from `missing_parameters`; unknowns stop execution. `Published_Reference-有来源技术对照.json` is separate and requires an explicit flag. No reference N values were copied into the Aachen field template. / 默认使用严格地块模板，数值与field_sources来源均需补齐，并更新已解决的缺项；未知值阻止运行。官方技术对照另存并需显式启用，没有将示例氮值写入Aachen地块模板。

**Reference choices:** retained the published 400ppm CO2 and rain NH4-N=1/NO3-N=4 mgN/L; these are source-example values, not current atmosphere/local deposition. NOTINF uses the documented PCSE default 0 for this rain-fed control instead of the drip-irrigated example's 1. This change and its source are recorded in JSON. / 对照保留官方示例的400ppm CO2及雨水铵态氮1/硝态氮4mgN/L，均不代表当前大气或本地沉降。雨养对照将原滴灌示例NOTINF=1改为有文档来源的默认0，变更与依据已逐项记录。

## Nitrogen boundary audit-氮淋失边界核对

`nitrogen_leaching_kg_N_ha` = nitrate-N + ammonium-N crossing the bottom of the entire simulated soil profile. The reference boundary is **120cm**, not the crop's changing root depth and not the older BK50 200cm boundary. / 接口氮淋失是离开整个模拟剖面底部的硝态氮加铵态氮。当前技术对照边界为**120cm**，不是动态根深，也不是旧BK50剖面的200cm。

Inspection of PCSE6.0.13 shows its native `NO3LEACHCUM`/`NH4LEACHCUM` accumulate `RNO3OUT[-1]`/`RNH4OUT[-1]`; those layer-outflow arrays can include upward movement into the layer above. This extension audits actual rate components before integration, subtracts that internal upward component from the reported profile-bottom leaching and retains native counters under `pcse_native_*`. No installed PCSE equations are modified. / 已核对6.0.13源码，原生累计变量累加末层流出数组，而该数组可能包括流向上一层的返流。本扩展在积分前核对通量，将这部分内部返流从对外报告的剖面底部淋失扣除，并以pcse_native_*保留原始值，未改写已安装PCSE的方程。

The bundled source also exports N at a negative top water-flow boundary. This is recorded separately as `pcse_native_top_boundary_N_export_kg_N_ha` so the N budget closes; it is a model-accounting term, not a validated estimate of runoff N or ammonia volatilisation. Native `NLOSSCUM` is preserved as `model_N_loss_kg_N_ha`; it is not a complete environmental N-loss total. / 原生实现还会随负的上边界水通量输出氮，现以独立字段记账以核对氮守恒，不解释为已验证的径流携氮或氨挥发；原NLOSSCUM另存为模块原生指标，不称为全部环境氮损失。

Each result includes daily crop/N summaries, layer NH4/NO3 in **kg N/ha per layer**, water flows, cumulative profile leaching, crop soil-N uptake, and fixation. Soybean retains the sourced `NFIX_FR=0.8`; biological fixation is not counted as soil N loss. / 输出含逐日生长氮汇总、分层kgN/ha的硝态/铵态氮、水通量、累计底部淋失、土壤供氮吸收与固氮。大豆保留来源参数NFIX_FR=0.8，固氮不计为土壤氮流失。

Daily rows follow PCSE state timestamps; a cumulative increment is the integrated preceding timestep. These simulations stop at crop maturity/termination. Winter wheat crosses autumn/winter, while spring crops have shorter exposure; the totals are not annual leaching and cannot be compared without matching the accounting window. Continuing after harvest/crop rotation is a later extension. / 逐日行遵循PCSE状态时刻，累计量增量对应前一积分步。模拟到作物成熟/结束为止；冬小麦跨秋冬，春播作物暴露时段更短。这些不是年淋失量，跨作物比较需统一核算窗口；收获后持续模拟及轮作需另行扩展。

## Run from package root-从交接包根目录运行

Use the crop environment (PCSE6.0.13), separately from the radiation environment. / 使用作物环境PCSE6.0.13，与辐射环境分开。

```powershell
python -m pip install -r "06_Hao_Interface_and_Rerun-Hao接口与复跑/Requirements-运行依赖.txt"
python "02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/Run_Nitrogen-运行氮模块.py" --crop all --check-only --accept-demo-assumptions
```

The strict command currently reports six blocked cases and returns a nonzero code. That is the intended missing-data behavior; it has not calculated six zeros. / 严格检查当前会列出六组缺项并返回非零退出码，这是正确的缺项行为，不是计算出六个零。

To reproduce the sourced technical checks only / 仅复跑有来源的技术对照：

```powershell
python "02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/Run_Nitrogen-运行氮模块.py" --crop all --mode all --nitrogen-inputs "04_Soil_and_Python-土壤条件与Python/Nitrogen_Inputs-氮输入/Published_Reference-有来源技术对照.json" --accept-reference-scenario --accept-demo-assumptions
```

`--mode NWLP_MLWB_SNOMIN` runs only the six water/N cases; `--mode all` runs all 18 version-matched checks. New run folders are created, preserving existing detailed results; the latest overview is refreshed. / 仅跑六组水氮用NWLP_MLWB_SNOMIN，all跑18组；逐次新建详细结果目录，保留历史，刷新最新汇总。

Hao can load `Hao_Interface-给Hao的接口.py` and call `evaluate_crop_water_nitrogen(...)` for the payload and output folder. A radiation DataFrame must cover every daily point; `effective_rain_mm_day` supplies explicitly defined local rain. The existing three Tianze hourly/period radiation files are not automatically full-season daily crop inputs. / Hao可调用新增水氮接口获取结果字典和目录；光照表需覆盖逐日逐点，局地有效降雨由明确的effective_rain_mm_day输入。天泽三个逐小时/时段文件不会自动变成完整季节的作物逐日输入。

Reference payloads have `scenario_kind=reference_only` and `eligible_for_field_optimization=false`. The scalar yield optimizer rejects them; request detailed outputs for technical evaluation. / 技术对照带有明确标识，标量产量优化接口会拒绝直接使用，技术评估需取完整结果。

## Official sources-官方来源

- [PCSE SNOMIN source and model citation](https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/snomin.html)
- [Official SNOMIN example notebook](https://github.com/ajwdewit/pcse_notebooks/blob/master/12%20Simulating%20with%20WOFOST%208.1%20SNOMIN.ipynb)
- [Official WOFOST81 crop branch](https://github.com/ajwdewit/WOFOST_crop_parameters/tree/wofost81)
- [NRW Nmin references](https://www.landwirtschaftskammer.de/landwirtschaft/ackerbau/duengung/basisinfos/nmin/index.htm)

Frozen source commits, original files and hashes are in the nitrogen inputs' `Source_Manifest-参数来源清单.json`. / 固定提交、原始文件及哈希见氮输入目录来源清单。
