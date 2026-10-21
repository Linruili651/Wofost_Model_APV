# Source Note-来源记录

This detailed note predates the six-folder layout; use this folder's README for current commands. / 本详细记录早于六目录整理，当前命令以本目录说明为准。

# 降雨补充使用说明

这是与原 EPW 来源月份配套的 ERA5 候选降水数据，用于明确假设的 TMY 演示计算。

## 文件与入口

- 03_Precipitation-降水条件/Precipitation_Supplement-降水补充.json：365 天数据、源日期、单位、下载链接、网格与限制。
- precipitation_adapter.py：按月日匹配到模型日期，校验 EPW 哈希、365 天完整性、非负雨量和来源年份。
- Tianze_Crop_Hao_with_precipitation.ipynb：新增入口，配置天气后自动读入补充液态雨。
- 原 Notebook、bridge.py 和 EPW 均保持原样；原入口不会自动读取本补充。
- precipitation_sources/open_meteo_era5_fixed_UTCplus1_raw.json：原始 API 响应，保留用于追溯。

解压整个新压缩包，在包目录启动 Jupyter，打开新增入口。
沿用原环境 pcse==6.0.13；在第 3 节核对示例假设。
要运行自然光照示例，将 accept_demo_assumptions 设为 True。
allow_missing_rain_for_pp 可保持 False，因为补充后无需以零填补缺雨。
不会自动执行 Radiance；遮阴计算仍需原模型要求的环境与实际完整季节辐射输入。

已有代码也可以显式调用：

```python
from precipitation_adapter import attach_precipitation
weather, rainfall_info = attach_precipitation(
    weather, EPW, ROOT / 'inputs' / 'Aachen_TMY_precipitation_supplement.json',
    component='liquid_rain')
weather_info.update(rainfall_info)
```

## 数据解释

rain_mm_day 为液态降雨，单位 mm/day，是本接口送入 RAIN_mm_day 的字段。
precipitation_mm_day 包括雨与降雪水当量；snowfall_cm_day 为降雪厚度，单位 cm/day。
不要把 cm 的降雪厚度直接当作 mm 的水量。
本版不处理融雪，液态雨单独驱动只是演示假设，不能代表完整冬季水量平衡。
原 bridge 在建立 PCSE 天气对象时把 mm 除以 10 转成 cm；不应再次换算。

## 年份与时区

一月至十二月来源年依次为 2020、2020、2016、2020、2007、2017、2009、2011、2007、2014、2015、2018。
源日期保留，模型日期按月日映射；不把模拟用的 2001/2002 当作真实气象年份。
数据按原 EPW LOCATION 的 +1 时区采用固定 UTC+1 日界，无夏令时。
早先试查的 GMT 候选文件未用于本包；仍需核对原提供方的时间定义与辐射时移。

## 适用范围

ERA5 是网格再分析数据，不是地块实测；与 PVGIS 的网格、版本和提取方式未证实完全一致。
TMY 拼接月份未按降水选取，不能代表连续历史作物季或典型干旱序列。
开阔地降雨不等于光伏板下有效降雨，未处理板面集流与空间重分配。
当前 PP 模式保持不变，补雨不等于有灌溉计算或动态土壤蓄水计算。
如需灌溉需求，另需土壤水分模型、初始条件和灌溉规则。
补充后的土壤蒸发若被输出，也仅是这些假设下的模型量，不是实测验证结果。

数据：Open-Meteo Historical Weather API，ERA5/Copernicus，CC BY 4.0。
说明：https://open-meteo.com/en/docs/historical-weather-api
完整请求与下载时间见 JSON。原始响应包含所请求年份的全年记录，补充文件仅选取对应月份。
