# Source Note-来源记录

This detailed note predates the six-folder layout; use this folder's README for current commands. / 本详细记录早于六目录整理，当前命令以本目录说明为准。

# Aachen 农业光伏：BK50 土壤数据库交接说明

整理日期：2026-10-19（Europe/Berlin）。本资料用于 Aachen 农业光伏研究后续的土壤、根系、水分和氮过程建模。

## 数据与范围

- 数据名称：IS BK 50 — Bodenkarte von Nordrhein-Westfalen 1 : 50.000。
- 发布机构：Geologischer Dienst Nordrhein-Westfalen（GD NRW）。
- 空间范围：北威州全域，覆盖 Aachen；本次保留官方全库，尚未选定具体农田或提取 Aachen 某个土壤剖面。
- 原始文件：`ISBK50_EPSG25832_GeoPackage.zip`。这是数据库压缩包，不是已经可以直接运行 WOFOST 的参数文件。
- 数据格式：GeoPackage，官方数据库位于压缩包内 `BK50_GPKG/BK50_A.gpkg`。
- 坐标系：EPSG:25832，ETRS89 / UTM zone 32N，坐标单位为米，不是经纬度。
- 下载对象的服务器 Last-Modified 为 2026-03-12；门户中的元数据更新日期可能不同，不将门户更新日期当作土壤实测日期。
- 精确字节数、下载响应信息和 SHA-256 校验值见 `download_source.json` 和 `SHA256SUMS.txt`。完整性结果以其中 `zip_crc_check` 为准。

## 怎么打开和交接

1. 将本文件夹中的资料一起交接。官方原始 ZIP、说明、来源和校验文件应一起保留。
2. 解压官方 ZIP，保持内部目录不变；其中含数据库、字段释义、土壤剖面说明和方法文档。
3. 用 QGIS 打开 `BK50_GPKG/BK50_A.gpkg`，在图层属性和属性表中查看数据。不要运行来历不明的项目脚本；本次验证只读取 SQLite 结构和数据。
4. 确认具体模拟地块后，按位置查询土壤图斑，保留土壤代码及各层深度、属性和来源。单独一个 Aachen 城市名称或天气站坐标不能代表所有农田土壤。
5. 选择模型后，再把对应图斑的土壤资料转换为模型要求的参数；本次不修改现有模型和作物参数。

官方压缩包约 611 MiB（640,838,185 bytes），解压全部内容约 1.68 GiB。随库部分图斑说明通过相对路径关联，完整解压有利于保留这些关联。

## 农业光伏研究需要覆盖的过程

| 研究内容 | 数据与模型如何分工 | 本次资料的用途与缺项 |
| --- | --- | --- |
| 扎根深度 | 土壤限制深度与作物初始根深、根深增长率和作物最大根深共同决定；WOFOST 根系为简化表示 | BK50 可提供土层、可生根情况等依据；作物的 RDI、RRI、RDMCR 仍需作物参数，不能直接用土层厚度替代 |
| 水分收支 | 降雨/灌溉进入土壤，水分经蒸发、蒸腾、地表径流和剖面底部排水离开 | BK50 可支持土壤蓄水及导水参数估计；仍需逐日天气、初始水分和管理输入 |
| 氮淋失 | 氮随土层水流迁移；需要显式氮平衡模块 | BK50 不是初始矿质氮数据库，不能提供每层模拟起始日的 NO3I、NH4I 和施肥记录 |
| 氮转化损失 | 应区分反硝化、氨挥发、侵蚀/径流携氮等过程 | SNOMIN 包含反硝化，但不能据此宣称已覆盖全部氮损失途径；BK50 的反硝化潜力不是逐日实际通量 |
| 板下空间差异 | 板下、滴水边缘和行间的光照、降雨和蒸散条件可能不同 | 单一土壤柱不自动模拟板面汇水和横向迁移；后续需定义分区、输入修正及面积权重，必要时增加空间水流模型 |

## 后续模型选择

如果只比较水分胁迫，可使用 WOFOST 的 WLP 版本。若研究指标包含氮淋失，建议优先评估 PCSE 中的 `Wofost81_NWLP_MLWB_SNOMIN`：WOFOST 8.1 作物模块 + 多层水分平衡（MLWB）+ 分层碳氮平衡（SNOMIN）。这是根据官方模型文档和源码作出的候选方案判断，尚未完成 Aachen 参数化、运行或实测验证。

普通 `Wofost72_WLP_CWB` 没有土壤氮平衡。仅把 PP 改成 WLP 不会自动得到氮流失结果。若后续升级模型版本，应为 PP、WLP 和水氮限制情景统一版本与作物参数，避免把版本差异误当成处理效应。

分层模型还需要每层厚度、容重、有机质、C:N、持水曲线和非饱和导水曲线；单个田间持水量或饱和导水率不能替代整条曲线。nFK 是植物可利用水容量，不等于 WOFOST 的 SMFCF；分类等级与连续数值也需区分。

详细过程覆盖、输入缺项与后续输出口径见 `01_根系水分氮过程覆盖与缺项.md`。

## 来源和许可

- 官方数据目录：https://www.opengeodata.nrw.de/produkte/geologie/boden/BK/ISBK50/
- 官方数据介绍：https://open.nrw/dataset/ab0f265c-dabe-4bcd-869a-d97dc328c141
- 原始 ZIP：https://www.opengeodata.nrw.de/produkte/geologie/boden/BK/IS04_Soil_and_Python-土壤条件与Python/BK50_Official_Database-BK50官方数据库.zip
- 许可：Datenlizenz Deutschland – Namensnennung – Version 2.0（dl-de/by-2-0）。许可页面：https://www.govdata.de/dl-de/by-2-0
- 模型组合依据：https://pcse.readthedocs.io/en/stable/_modules/pcse/models.html

建议保留的来源标注：Geologischer Dienst NRW, IS BK 50 – Bodenkarte von Nordrhein-Westfalen 1 : 50.000, dl-de/by-2-0, https://open.nrw/dataset/ab0f265c-dabe-4bcd-869a-d97dc328c141 ，下载于 2026-10-19。

官方原始 ZIP 保持原样。额外的说明、字段清单及验证记录由本次整理产生；后续如裁剪、换算或推算参数，应在论文和交接中标明相应加工。
