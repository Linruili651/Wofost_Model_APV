# Missing Field Parameters-地块待补参数

Unknowns remain null and block every crop; sourced generic model values do not establish local measurements. / 未知值保留null并阻止六作物运行，通用来源参数不等于当地测量。

| Parameter-参数 | Needed evidence-所需依据 |
| --- | --- |
| `field_location_and_profile_confirmation` | Confirm actual APV plot / 确认实际农业光伏地块与剖面 |
| `NO3I` | Date-specific nitrate-N per layer including deep soil / 提供起始日各层硝态氮，含深层 |
| `NH4I` | Date-specific ammonium-N per layer / 提供起始日各层铵态氮 |
| `FSOMI` | Layer organic matter fraction / 提供各层有机质质量分数 |
| `CNRatioSOMI` | Layer soil organic C:N ratio / 提供各层有机碳氮比 |
| `Soil_pH` | Layer pH with measurement method / 提供分层pH及测定方法 |
| `fertilizer_events` | Per-crop fertilizer dates, type, amount, form fractions and depth; unknown is null / 六作物施肥日期、类型、用量、形态比例及深度；未知保留null |
| `rain_N_concentrations` | NH4-N and NO3-N concentration or an explicit sourced scenario / 降雨氮浓度或有来源的明确情景 |
| `initial_water_and_surface_conditions` | Confirm WAV/SMLIM/infiltration settings / 确认初始水分与地表参数 |
| `simulation_year_and_CO2` | Current weather is synthetic TMY; specify intended scenario / 当前天气为拼接TMY，确认情景年份及CO2 |
