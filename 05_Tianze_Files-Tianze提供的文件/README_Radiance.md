# 亚琛 Tianze 模型：Radiance 是什么，怎样运行

Radiance 是一套计算光线在三维场景中传播的软件。输入包括天空辐射、太阳方向、组件位置、尺寸和材料；它追踪光线受到的遮挡、透射、反射，计算指定位置接收到的辐射。这里关心的输出是作物位置的太阳辐射。

天泽的 Python 代码负责组织模型；bifacial-radiance 是 Python 与外部 Radiance 程序之间的接口。真正计算会调用 `oconv`、`rtrace` 等程序，所以只安装 Python 包不够。本次已把它们下载到此处，并准备了独立 Python 环境。

工作流程：亚琛天气与光伏布置 → 天泽代码 / bifacial-radiance 调用 Radiance → 板下辐射 → WOFOST PP/WLP → 作物产量与耗水。

本配置只处理亚琛，不读取其他地点案例数据。Radiance 本身不计算作物生长、土壤水分或灌溉；WOFOST 读取已有辐射文件时，也不需要每次重新做光线追踪。

## 文件在哪里

- `Radiance_Runtime-Radiance运行环境/Radiance_c1700d56_Windows.zip`：从 LBNL 官方 GitHub release 实际下载的 Windows 原始压缩包，约 33.6 MB。
- `Radiance_Runtime-Radiance运行环境/Radiance_6.0.2/`：已经解压的 `bin` 程序与 `lib` 支持库。
- `Radiance_Runtime-Radiance运行环境/.venv/`：本地独立 Python 辐射环境，与作物模型环境分开。
- `Radiance_Runtime-Radiance运行环境/DOWNLOAD_SOURCE-下载来源.json`：下载地址、版本、大小、SHA-256 和官方资产摘要。
- `Radiance_Runtime-Radiance运行环境/INSTALLATION_CHECK-安装检查.json`：实际 Python、软件版本及程序调用路径。
- `Radiance_Runtime-Radiance运行环境/AACHEN_SMOKE_CHECK-亚琛短时验证.json`：本次短时物理计算的状态与结果路径。

使用官方正式版本 Radiance 6.0.2，与已测试的 Tianze 运行版本一致；bifacial-radiance 0.5.4、pvlib 0.16.1，完整 Python 依赖记录在 `requirements-radiation-lock.txt`。原始压缩包通过 CRC 和 GitHub 提供的 SHA-256 比对。

## 怎样运行

在当前这个 Tianze 文件夹打开 PowerShell，只检查环境：

```powershell
.\Start_Tianze_Aachen.ps1
```

执行固定倾角的一小时亚琛试算：

```powershell
.\Start_Tianze_Aachen.ps1 -Action smoke -Model fixed_tilt
```

分别运行垂直或单轴跟踪，将 `-Model` 改成 `vertical_pv` 或 `single_axis`；`all` 会顺序运行三种形式。运行入口使用单独的执行副本，原始 notebook 保留。

为兼容 Windows 原生程序对中文路径的处理，入口会把已下载的程序和支持库准备到专用临时执行目录，只为本进程和子进程配置 PATH/RAYPATH。下载原件与主要结果仍保留在本文件夹；不需要用户手动修改系统 PATH。

测试使用 Aachen TMY 天气、6 月 21 日 12:00–13:00（示例日期标签）、2×2 组件和 4×4 地面点。新结果写入 `Three_Radiation_Notebooks-三个辐射模型/Rerun_Results-复跑结果/`，每次新建目录。它验证软件调用与数据输出，不能代替六种作物的完整季节辐射或田间校准。

如需在 Jupyter 中调用当前环境的 Radiance，先使用本文件夹 `.venv/Scripts/python.exe` 对应的 Python 内核，再加入初始化单元：

```python
from pathlib import Path
import sys
runtime = Path(r"填写此处 Radiance_Runtime-Radiance运行环境 文件夹的绝对路径")
sys.path.insert(0, str(runtime))
from runtime_env import configure
configure()
```

## 搬到另一台电脑

Windows 程序压缩包可以保留；Python 虚拟环境需要在目标电脑重新创建。使用 Python 3.13，在 `Radiance_Runtime-Radiance运行环境` 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-radiation-lock.txt
```

然后从上一级文件夹运行 `Start_Tianze_Aachen.ps1`。光伏布置和输出分支的实验范围仍以原交接说明为准，本次软件配置不扩大已经完成的实验范围。

## 官方资料

- Radiance 介绍：https://www.radiance-online.org/about
- Tianze 提供的安装说明：https://bifacial-radiance.readthedocs.io/en/stable/user_guide/installation.html
- 本次正式版本：https://github.com/LBNL-ETA/Radiance/releases/tag/rad6R0P2
