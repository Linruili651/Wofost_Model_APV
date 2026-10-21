# Three Radiation Notebooks-三个辐射模型

## Current Aachen calculation plan-当前亚琛计算计划（2026-10-19）

The user now plans all six combinations (two constructions × three mounting forms), each coupled to PP/WLP for six crops. The three code files contain both construction branches. This is the current calculation plan; the four-case scope described below refers to Hao's previously stated completed experimental scope. See `../六种光伏组合与PP_WLP运行计划.md` for the 72 PV comparisons plus 12 open-field baselines. / 用户当前计划计算全部六种组合（两种组件×三种安装形式），再分别对六作物运行PP/WLP。三个代码文件都包含两种组件分支。下文四组范围为此前转述Hao既有实验的历史说明；当前计划及72组光伏、12组露天基线见上一级文件夹的运行计划。

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

## Located originals-找到的原件

The screenshot files were found under `外部贡献`, with `(1)` added to their filenames. The copies in `Original_Notebooks-原始笔记本` retain every original byte, including saved old outputs. See the source manifest for hashes. / 截图对应的文件在工作区“外部贡献”下，文件名多了 `(1)`。原始笔记本目录内的副本逐字节一致，原文件自带的历史输出也保留；哈希见来源清单。

| Notebook-笔记本 | Purpose-用途 | Original defaults-原始默认设置 |
| --- | --- | --- |
| `fixed_tilt-固定倾角.ipynb` | Fixed tilt, azimuth, row pitch and clearance; compare semi-transparent and opaque constructions. / 固定倾角、朝向、行距和离地高度，比较半透明与常规不透光组件。 | 25° tilt, south facing, 3 m clearance; 2024-10-01 through 2024-10-02; both outputs on. / 倾角25°、朝南、离地3米，10月1日至2日，两类输出均开启。 |
| `vertical_pv-垂直光伏.ipynb` | Tilt fixed at 90°, lower edge at ground level; front east/rear west by default. / 垂直90°安装、下缘贴地，默认正面朝东、背面朝西。 | 2024-06-21; Hao on, ground off. / 6月21日，仅Hao板面输出开启，地面输出关闭。 |
| `single_axis-单轴跟踪.ipynb` | Hourly single-axis rotation with angle limit and backtracking. / 逐小时单轴旋转，考虑转角限值和回溯跟踪。 | North–south axis, 3 m hub, ±45°, backtracking; 2024-03-01 through 2024-03-30; BOTH outputs off. / 南北轴、轴高3米、转角±45°、开启回溯；3月1日至30日；两类输出默认都关闭，直接运行不会模拟。 |

## Inputs and outputs-输入输出

All three use the Aachen EPW weather, module dimensions and cell layout, glass optical assumptions, array size, row pitch and geometry. Each compares two constructions: physical opaque cells with transmitting glass/gaps, and a conventional opaque module. / 三者均读取 Aachen EPW 天气、组件与电池片尺寸、玻璃光学假设、阵列规模、行距及安装几何。每个文件分别计算半透明结构和常规不透光结构。

- **Hao:** four hourly array-integrated incident-energy columns (front/rear × two constructions), unit **Wh per hour interval for the whole array**. Rear results already include each construction's bifaciality. These are inputs for energy calculations; electrical conversion, inverter efficiency and losses are absent. / 四列逐小时全阵列入射能量（正背面×两种结构），单位为整个阵列在该小时间隔的Wh；背面已乘双面率，后续不可再重复乘。未计算电转换、逆变器效率及电气损失。
- **Linrui:** six ground energy totals (direct/diffuse/total × two constructions), unit **Wh integrated over the selected land and whole selected period**, one row per run. They are neither daily W/m² nor ready-to-use WOFOST daily MJ/m². Divide by the correct land area, aggregate each day and convert units before crop coupling; a whole-season total alone cannot recover the daily series. / 六个地面能量总值（直射/散射/总辐射×两种结构），是评价土地范围与整个选定时段积分后的Wh，每次运行一行。并非逐日W/m²或可直接输入WOFOST的逐日MJ/m²；需按正确面积归一化、逐日组织并换算单位，单独季节总值不能还原逐日数据。

`crop_name` is a record label here. No crop growth, roots, soil water, precipitation redistribution or nitrogen leaching is simulated in these notebooks. Those belong to the crop/soil modules. / 这里的作物名只是记录标签，不计算生长、根系、土壤水分、板面降雨重分配或氮淋失；这些应由作物与土壤模块负责。

## Execution scope-运行范围

The run copies explicitly select 2024-06-21 12:00–13:00 in EPW local standard time, 2×2 modules, a 4×4 ground grid, two workers and low accuracy, with BOTH outputs enabled. Cell count, module dimensions, glass, rear weighting and each model's default installation geometry remain unchanged. / 本次运行副本明确设为EPW当地标准时2024年6月21日12:00–13:00、2×2组件、4×4地面网格、2个工作线程、low精度，并开启板面与地面两类输出。电池片数量、组件尺寸、玻璃、背面权重与各模型默认安装几何保持原值。

These are short numerical execution checks, not the original full-period default runs, a full growing season, parameter calibration or a complete APV–WOFOST coupling. The executed copies contain their explicit override cell. See `Execution_Summary-运行汇总.md` and per-model logs for actual pass/failure status. / 这是短时数值执行检查，不代表原默认全时段、完整生长季、参数校准或农业光伏与WOFOST完整耦合。执行副本中保留了明确的参数覆盖单元；实际成功或失败状态见运行汇总与各模型日志。

## Rerun environment-复跑环境

Use a separate Python environment for radiation dependencies. Radiance command-line tools (`rtrace`, `oconv`, `genbox`, `xform`, `gendaylit`) and the Radiance `lib` directory must also be available through PATH and RAYPATH. / 建议独立配置辐射Python环境；还需将Radiance外部程序加入PATH，将其lib支持库加入RAYPATH。

Official sources / 官方来源：[bifacial_radiance](https://github.com/NatLabRockies/bifacial_radiance)、[Radiance installation](https://www.radiance-online.org/download-install/installation-information)、[Radiance 6.0.2 Windows archive used here](https://github.com/LBNL-ETA/Radiance/releases/download/rad6R0P2/Radiance_c1700d56_Windows.zip)。

Keep the older notebooks and adapters in the parent folder for provenance. The older daily bridge was not verified against these three newer hourly/period schemas; this handoff does not silently substitute one for the other. / 上一级目录的旧版笔记本与适配器保留供追溯。原有逐日接口尚未对这三个新版的逐小时/时段输出结构验证，本次整理没有直接替换旧接口。

From this three-model folder, install the recorded dependencies and run the portable launcher. It checks all three models by default, creates a new timestamped folder and preserves prior outputs. The launcher sets weather/output paths; the original notebook's `weather/` layout need not be created. / 在本目录安装记录的依赖后运行便携入口；默认检查三个模型，结果写入新时间戳目录，保留之前结果。入口会设置天气和输出路径，无需手动搭建原笔记本的weather目录。

```powershell
python -m pip install -r "Tested_Requirements-测试环境依赖.txt"
python "Run_Three_Models-运行三个模型.py" --radiance-home "C:/Radiance"
```

If PATH and RAYPATH are configured, omit `--radiance-home`. To run just one, add `--model fixed_tilt`, `--model vertical_pv` or `--model single_axis`. / 已配置PATH和RAYPATH时可省略外部程序根目录参数；只运行一个模型可使用上述model参数。默认入口只跑说明中的一小时样例，完整时段需另行修改参数并确认输出时间分辨率。
