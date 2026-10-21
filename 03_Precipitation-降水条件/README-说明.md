# Precipitation Conditions-降水条件

- `Aachen_TMY_Weather-Aachen典型年天气.epw`: shared weather file. / 两种模式共同使用的天气文件。
- `Precipitation_Supplement-降水补充.json`: 365-day source-month-matched liquid rainfall. / 与来源月份匹配的 365 天液态降雨。
- `Precipitation_Adapter-降水适配.py`: date/source/hash validation and rainfall attachment. / 日期、来源、哈希校验与降雨接入。
- `Original_Data-原始数据/`: original ERA5 response. / ERA5 原始响应。
- `Detailed_Method-详细方法.md`: detailed source and timing assumptions. / 来源和时间假设的详细记录。

This is TMY demonstration weather, not a continuous observed year. Snowmelt and panel redistribution are not implemented. / 这是 TMY 演示天气，不是连续历史年；未实现融雪和板面降雨重分配。
