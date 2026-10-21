# Implementation Update-实现更新

## Nitrogen extension added 2026-10-20-已新增氮淋失扩展

Use `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/README-说明.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling. / 已新增WOFOST81/SNOMIN入口，六作物有来源技术对照水氮及同版本PP81/WLP81共18组完成；六组Aachen地块检查均因缺项明确停止。旧WOFOST73的PP/WLP仍不计算土壤氮循环。参数、缺项与边界见扩展说明。

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed. / 本次不宣称已完成实际整季农业光伏水氮耦合；Hao现有实验范围仍为已确认的四组。

**Boundary clarification / 边界补充：** In installed PCSE6.0.13, native last-layer cumulative N outflow can include internal upward flow. The new interface audits this and separately reports actual profile-bottom transport and native top-boundary accounting; consult its guide before using the historical output-variable descriptions below. / 已装6.0.13末层累计流出可含内部向上流动；新接口已核对并分开报告底部迁移及原生上边界记账，下面旧说明中的累计变量应结合新指南使用。

# Source Note-来源记录

This detailed note predates the six-folder layout; use this folder's README for current commands. / 本详细记录早于六目录整理，当前命令以本目录说明为准。

# Aachen 农业光伏：根系、水分与氮过程的覆盖范围

核查日期：2026-10-19。依据官方 BK50 压缩包中 `Tabellen_Erlaeuterungen` 的字段说明，以及 PCSE 官方模型文档和本地 PCSE 源码。本文是数据和模型适配核查，不是已经完成的模拟结果。

## 结论

BK50 可作为 Aachen 土壤剖面和水力特性的基础数据，不能独立提供完整的水氮模型参数。若研究内容包括随排水发生的氮淋失，优先评估 `Wofost81_NWLP_MLWB_SNOMIN`。普通水分限制 WLP 模型不含相应的土壤氮循环。

这个组合能表示简化根深变化、分层水流、土壤矿质氮转化和剖面底部氮淋失；它不是农业光伏的完整二维/三维土壤模型，也不能自动涵盖所有氮损失途径。

## 1. 已核实的数据字段

原始说明和另存的 UTF-8 版本位于 `字段说明`。原文说明中的表名未必与 GeoPackage 的图层名一致；需根据实际表结构和土壤代码关联。

| 随库资料 | 空间/深度口径 | 对本研究的作用 |
| --- | --- | --- |
| `LEGENDE_SPALTEN_DBF.txt` | 主图斑/土壤单元属性 | FK、NFK、KF、地下水和滞水分级、反硝化潜力等字段释义 |
| `INFO_ONP.txt`、`Tabelle_ONP.xlsx` | 按土壤质地层 | 优先用来组织分层模型输入；包括 DICKE_SCH、FK_SCH、NFK_SCH、LK_SCH、KF_SCH、LD_SCH、HM_BDA 等 |
| `INFO_JDM.txt`、`Tabelle_JDM.xlsx` | 1–20 dm 的逐深度资料，部分列为截至该深度的累计或平均值 | 适合查看垂直变化；不能把每一行的累计值直接当成一个 10 cm 土层的值 |
| `INFO_KRZ.txt`、`Tabelle_KRZ.xlsx` | 耕地有效根区、草地有效根区、1.5 m、2 m 等参考深度 | 可核对不同根区的总蓄水量及有效根区；不能混用参考深度 |

`Tabelle_*.xlsx` 是原始官方数据库的配套数据表，未在本次修改、重算或重排。

## 2. 根系深度

WOFOST 中应分别准备：土壤允许的根系深度 `RDMSOL`，以及作物的初始根深 `RDI`、根深增长率 `RRI`、最大根深 `RDMCR`。实际最大根深受土壤和作物两者限制。土壤图中的耕地有效根深不应未经判断就直接等同于某个具体作物的最大根深。

BK50 的 ONP 表提供 `DICKE_SCH`（dm）、`SUM_DICKE_OBEN`、`SUM_DICKE_SCH` 等层位信息；JDM 说明中还有 `WEA`（耕地有效根深，dm）与 `WEG`。这些可作为根区设置和约束的依据，但不能代替作物参数、实测根长密度或根系结构。1 dm = 10 cm。

光伏遮阴是否改变根深增长或根系分配，需要另外的证据和参数化；模型有根深变量，并不代表它已自动重现该响应。

模型依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/crop/root_dynamics.html

## 3. 土壤水分与水分损失

分层水分平衡应检查入渗、土层间水流、蒸发、蒸腾、地表径流和剖面底部通量。应分别报告这些量，避免把有益的作物蒸腾和深层排水笼统合并成“水分流失”。

BK50 的 ONP 字段：

- `FK_SCH`、`NFK_SCH`、`LK_SCH`：单位 mm/dm；分别为田间持水量、植物可利用水容量和空气容量。
- `KF_SCH`：cm/d，饱和导水率；不能直接替代整条非饱和导水曲线。
- `LD_SCH`：g/cm³，按孔隙属性推算的容重；不是地块容重实测值。
- `SAND_SCH`、`SILT_SCH`、`TON_SCH`、`HM_BDA`：体积百分比。若传递函数要求质量百分比，需先完成口径转换，不能直接照填。
- 主图斑的 `FK`、`NFK`、`LK` 为参考深度内的毫米水柱总量，不是体积含水率。

作为后续参数整理的候选换算：若对应同一土层，且确认字段口径适用，可由 `FK_SCH / 100` 估计体积田间含水率，由 `(FK_SCH - NFK_SCH) / 100` 估计 pF 4.2 附近的含水率，由 `(FK_SCH + LK_SCH) / 100` 估计孔隙度。此处仅说明单位和定义关系，本次未生成这些模型参数；地下水/滞水影响、粗颗粒及孔隙分类需按官方方法另行核对。

BK50 的 ONP 定义以 pF 2.5 区分田间持水与空气容量；模型的 `PFFieldCapacity` 应与之统一。多层模块需要完整的 `SMfromPF` 与 `CONDfromPF` 表，少数持水点仍不足以唯一确定曲线。可考虑有依据的土壤传递函数，并记录方法、适用条件和不确定性。

还缺：模拟起始日水分剖面、逐日天气、灌溉管理以及需要的边界条件。若图斑有明显地下水或滞水影响，应先核对所选水分模块的边界假设，不能直接按自由排水处理。

水分模块依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/multilayer_waterbalance.html

土层输入依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/soil_profile.html

## 4. 氮淋失与其他氮损失

SNOMIN 源码包含硝态氮和铵态氮随土层水流迁移、作物吸收、矿化/固定、硝化和反硝化等过程。其累计底部淋失取自最后一层的流出量，代表离开整个模拟剖面的氮，不能直接称为“离开当前根区的氮”。若研究根区边界通量，需要另外在对应深度记录和定义。

可作为后续输出候选的变量包括 `NO3LEACHCUM`、`NH4LEACHCUM`、`NDENITCUM`。该实现的 `NLOSSCUM` 为这三者之和，不等于所有环境途径的总氮损失；尤其不能由此推导出已计算氨挥发、侵蚀携氮或全部径流携氮。

BK50 的 `DEN_0_5`、`DEN_6_10`、`DEN_11_20` 是反硝化潜力字段，不是逐日/年度实际反硝化量，也不能当作初始硝态氮或反硝化速率常数。土壤总氮也不能直接替代矿质氮初值。

氮模块仍需准备：

| 输入 | 当前情况 | 后续来源/处理 |
| --- | --- | --- |
| 各层初始硝态氮 `NO3I`、铵态氮 `NH4I` | 未从 BK50 获得模拟起始日观测 | 同地块 Nmin 测定优先；没有时用有来源的范围做情景分析 |
| 土壤有机质质量分数 `FSOMI` | BK50 有腐殖质相关体积口径，不能直接作为质量分数 | 核对剖面资料并转换口径，或补充合适的有机质/有机碳数据 |
| 土壤有机质 C:N `CNRatioSOMI` | 未确认已有直接、适用数值 | 剖面分析或适用文献；必须记录假设 |
| 施肥日期、数量、形态、施入深度 | 土壤图不提供管理记录 | 研究方案或真实田间管理数据 |
| 有机物投入/残茬及其性质 | 当前未准备 | 按模拟管理范围补充 |
| 土层 pH `Soil_pH`、临界空气含量 `CRAIRC` | 尚未准备为模型输入 | 从剖面资料或适用文献补充；BK50 的 `ZPH_A`、`ZPH_G` 是管理目标 pH，不能直接称为当前实测 pH |
| 氮转化参数、沉降输入 | 当前未校准 | 核对 SNOMIN 参数定义、适用范围与默认值，做必要敏感性分析 |

把缺项留空并明确记录，比填入无来源的默认值更有利于后续复现。本次没有虚构 Aachen 的初始氮浓度或施肥制度。

氮模块依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/snomin.html

方法论文：https://doi.org/10.1016/j.eja.2024.127099 （文献信息来自官方模块说明；本次未以全文核查代替源码核查。）

## 5. 农业光伏边界与比较设计

建议后续明确板下、滴水边缘、行间和露天对照的面积及输入。仅降低辐射，不会自动产生板面汇水、遮雨、横向水分流动或相应的氮迁移；相关过程需要额外的空间划分和输入设定。分区间存在显著横向交换时，独立土壤柱加面积平均的近似需要重新评估。

建议在相同模型版本、作物、土壤、年份和管理条件下比较 PP、WLP 与水氮限制情景，并保留面积权重、水量和氮量平衡。若研究真实年份的水氮流失，应使用对应年份的天气和管理；TMY 典型气象年可用于代表性情景，但不能当成该实际年份的天气。

正式交给模型前，应完成：地块定位和土壤代码选择、分层参数转换、水力曲线估计、初始水氮与管理补充、输出深度/单位确认，以及合理性和收支检查。本次完成数据库获取与适配说明，模型实现按用户安排留待后续。

模型组合依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/models.html

## 6. 后续应核对的输出口径

本次本地核查所见 PCSE 版本为 6.0.13，离线官方参考页面为 6.0 文档。以下是源码中的变量名，尚未运行或导出；实现时需显式配置需要保存的输出并确认单位，不应假设默认输出已经包含全部指标。

| 指标 | 源码变量候选 | 解释 |
| --- | --- | --- |
| 根深 | `RD` | cm；简化根深，不是根长密度剖面 |
| 土壤水分 | `SM`、`WC` | 分层含水率/储水量，核对每层和总量的口径 |
| 蒸腾、土壤蒸发 | `WTRAT`、`EVST` | 水分模块的累计量，cm 水柱；转 mm 需乘 10 |
| 地表径流 | `TSR` | 累计水量，不能据此推定有径流携氮模型 |
| 剖面底部排水 | `BOTTOMFLOW`、`BOTTOMFLOWT` | 多层水分模块的瞬时/累计底部通量；与根区边界的通量不同 |
| 硝态氮/铵态氮淋失 | `NO3LEACHCUM`、`NH4LEACHCUM` | SNOMIN 累计底部淋失，源码将其换算为 kg N/ha；土层状态数组的单位需另查 |
| 反硝化 | `NDENITCUM` | 累计反硝化氮，不能直接当成单独的 N2O 排放量 |
| 模块内汇总氮损失 | `NLOSSCUM` | 上述两种底部淋失与反硝化之和，不能称为覆盖所有途径的总环境氮损失 |
