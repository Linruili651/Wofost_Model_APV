# Nitrogen Inputs-氮输入

`Aachen_Field_Inputs-Aachen地块待补输入.json` is the strict default with unknown values explicitly null. `Published_Reference-有来源技术对照.json` is a separate source-example technical scenario. / 默认地块输入的未知值明确留null；官方示例技术对照另存，不将其当作Aachen参数。

`Crop_Parameters_81-WOFOST81作物参数` contains six original crop YAMLs from a fixed official commit. `Source_Records-来源记录` contains the source notebooks, model/source files and NRW Nmin pages. `Source_Manifest-参数来源清单.json` records URLs and hashes. / 作物参数目录含六份固定官方提交的原YAML；来源记录含示例笔记本、模型源码与NRW矿质氮资料；清单记录URL与哈希。

The NRW tables are seasonal total mineral-N references, not a species-specific complete field initial profile. No nitrate/ammonium split, deep-layer zero or field fertilizer schedule was inferred from them. / NRW表是时段矿质氮总量参考，没有据此推定硝态/铵态比例、深层为零或地块施肥制度。

Run instructions, parameter decisions, missing fields and boundary definitions are in `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/README-说明.md`. / 参数选择、缺项、边界及运行方法见水分模型目录中的氮淋失扩展说明。
