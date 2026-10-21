# 亚琛：六种光伏组合与 PP/WLP 运行计划

用户本次确认的计算范围为：普通（conventional）和半透明（semi_transparent）两种组件，分别采用固定倾角、单轴跟踪、垂直三种安装形式，共六种光伏组合。六种作物分别运行 PP 与 WLP，再与各自露天基线比较。

## 代码能覆盖哪些组合

| 安装形式 | 当前原始文件 | 普通组件分支 | 半透明组件分支 |
| --- | --- | --- | --- |
| 固定倾角 | `Three_Radiation_Notebooks-三个辐射模型/Original_Notebooks-原始笔记本/fixed_tilt-固定倾角.ipynb` | 有 | 有 |
| 单轴跟踪 | `Three_Radiation_Notebooks-三个辐射模型/Original_Notebooks-原始笔记本/single_axis-单轴跟踪.ipynb` | 有 | 有 |
| 垂直 | `Three_Radiation_Notebooks-三个辐射模型/Original_Notebooks-原始笔记本/vertical_pv-垂直光伏.ipynb` | 有 | 有 |

三个文件的构造循环均包含 conventional、semi_transparent 两个分支。已有三模型一小时执行记录也分别保存了这两个分支的地面结果。它们证明代码分支能够短时执行，不代表六个完整生长季计算已经完成。

旧版两个文件 `02_optimization_ready_radiation_model.ipynb` 和 `03_optimization_ready_single_axis_radiation_model.ipynb` 只对应固定与跟踪两类形式。旧逐日适配器的 KINDS 也只有 fixed、tracking，尚不能据此声称已经接好新版垂直模型。

## 为什么未手动下载也可能“运行成功”

运行 WOFOST 并不要求重新运行 Radiance。早期 Aachen 冬小麦 Notebook 的验证记录明确为 `real_radiance_run_performed: false`；该版可直接从天气文件完成露天作物计算。

对于这三个较新的辐射文件，原始默认开关分别为：

| 安装形式 | GET_LINRUI_GROUND_IRRADIATION（地面） | GET_HAO_ARRAY_RESULTS（板面） | 默认行为 |
| --- | --- | --- | --- |
| 固定倾角 | True | True | 启用两类辐射输出，需要调用外部程序 |
| 单轴跟踪 | False | False | model_for_optimization 提前返回空结果，不做 Radiance 计算 |
| 垂直 | False | True | 算板面，未启用给作物使用的地面结果 |

固定倾角原 Notebook 自带保存的输出，因此看见旧表格不等于刚刚重新计算了它。确认一次运行的实际情况，应查看该次新生成的文件和执行记录。用户没有手动运行系统安装器，也不排除项目或运行环境已经提供了便携 Radiance。当前已单独在本文件夹完成软件下载和运行配置。

## “跑两遍”具体指什么

对于相同天气、光伏几何、材料和固定采样网格，每种光伏组合生成一套板下辐射，供 PP/WLP 共用。两种模式分别重新运行作物生长和水分过程，不能只把模式标签改名后使用同一产量。

- 光伏情景结果：6 种光伏组合 × 6 种作物 × 2 种模式 = 72 组。
- 露天基线结果：6 种作物 × 2 种模式 = 12 组；露天不按光伏安装形式重复建组。
- 总计 84 组作物情景汇总结果。若逐空间点运行，每组结果会包含多次 WOFOST 调用。

这里的六套辐射可以共享同一 TMY 全年计算中的对应月日，并按各作物日历提取；不需要每换作物都重复计算同一板下采样面的光。若采样面随作物冠层高度变化，则需另行定义辐射耦合方案。

图的组织仍可为 12 张：每种作物、每种模式一张；每张左侧比较产量，右侧比较蒸腾与土壤蒸发，均包含露天和六种光伏组合七个处理。WLP 的实际耗水与灌溉需求应区别报告。

## 当前尚需完成的连接

这些新版原始文件的地面结果主要是选定时段、选定面积的总能量，不能把整季总量直接当作逐日 WOFOST 输入。完整计算需要在固定研究种植区提取每日地面辐射，保留每个空间点及代表面积、统一单位，核验所有作物季完整覆盖后再分别运行 PP/WLP。

本目录新增的 `Aachen_Six_Scenarios-亚琛六组合计划.json` 与 `Aachen_84_Crop_Comparisons-亚琛84组作物计划.csv` 是任务清单。它们没有把一小时检查写成完整生长季结果，也没有补造未计算的辐射或产量。

Hao 先前转述的四组既有实验范围保留为历史说明。本次用户计划覆盖六组，不据此宣称 Hao 先前已经完成全部六组正式实验。
