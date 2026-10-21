# Tianze Files-Tianze提供的文件

## 文件归属更正（用户确认，2026-10-19）

`Tianze_Crop_Hao_Jupyter.zip`、`Y.ipynb` 和 `RE.py` 是 Linrui 自己编写、准备交给 Hao 的衔接材料，不计为 Tianze 提供的原件。原始目录只是共同存放位置。天泽部分以辐射程序及其输入输出为主；Linrui 的运行包、使用入口和优化器接口属于用户交付 Hao 的部分。详见本目录文件总清单。

## 已定位给 Linrui 的地面辐射接口（2026-10-19）

三个新版原件通过 `model_for_optimization` 的第二返回值 `ground_summary` 输出地面结果，并在同一 CSV 中分开保存 `conventional` 与 `semi_transparent`。接口说明、原件保存输出、源码行号、只读 CSV 读取器和向 Tianze 索取的准确文件名均在 [Ground_Output_Interface-地面辐射接口](Ground_Output_Interface-地面辐射接口/接口定位与向天泽索取文件.md)。本次检查找到固定倾角原件中自带的两天地面合计显示，但未在当前原始文件及原 ZIP 内找到完整 Linrui 结果 CSV。


## Radiance 已下载并配置（亚琛，2026-10-19）

新增 `Radiance_Runtime-Radiance运行环境/`，包含官方 Windows 原始压缩包、解压后的程序和支持库，以及独立的本地 Python 环境。入口为本目录 `Start_Tianze_Aachen.ps1`；默认仅检查环境，`-Action smoke` 执行一个小时的亚琛短时试算。说明见 [README_Radiance.md](README_Radiance.md)，实际检查结果保存在运行环境目录。


- `Three_Radiation_Notebooks-三个辐射模型/`: the three screenshot notebooks, unchanged originals, short-run copies, outputs, logs and usage notes. Start here for fixed tilt, vertical PV and single-axis tracking. / 截图对应的三个辐射模型：原文件、短时运行副本、结果、日志和说明；固定倾角、垂直与单轴模型从这里查看。
- `Original_Files-原始文件/`: the two previously collected, older optimization-ready radiation notebooks, original weather and schema sample. They are distinct from the three files above. / 此前收集的两个旧版优化辐射笔记本、原始天气与格式样例，与上面三个文件分别保留。
- `Python_Adapters-Python适配/`: exported older definitions and the older daily radiation bridge; not yet validated against the three newer output schemas. / 旧版导出定义及逐日辐射接口，尚未对三个新版输出结构验证。
- `Tianze_Defaults-Tianze默认配置.json`: older adapter configuration. / 旧版适配器默认配置。
- `Radiation_Requirements-辐射依赖.txt`: unpinned optional dependencies for the older adapter. Consult the new three-model folder for its tested environment. / 旧适配器的可选依赖，三个新文件的测试环境见其子目录。

Radiation output is incident energy, not electrical generation or crop yield. New short runs and their limits are documented in the three-model folder. / 辐射输出为入射能量，不是发电量或作物产量；三个新文件的短时运行结果和边界见子目录。

## APV experiment scope-农业光伏实验范围

Hao's stated cases are fixed tilt × conventional/semi-transparent, single axis × conventional, and vertical × conventional: **four cases**. Two panel types × three mounting forms would give six cases in total. The short six-combination code checks in the Tianze folder do not establish six formal experiments by Hao. See `Experiment_Scope-实验范围.md` in the three-notebook folder. / 据Hao说明，现有范围是固定倾角×传统/半透明、单轴×传统、垂直×传统，共**四组**。两种组件×三种安装形式全部组合才是六组；天泽目录内六种组合的短时程序检查不代表Hao完成六组正式实验。详情见三个辐射模型目录内的实验范围说明。
