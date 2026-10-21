- PVGIS_Original_TMY_Hourly.csv:  8760 , UTC , W/m².
- Open_Field_Hourly_Matched.csv:  GHI, DNI, DHI, .
- Open_Field_Daily_Matched.csv: 382 ,  24 . GHI  Wh/m²/day,  3600  WOFOST  IRRAD,  J/m²/day.



Open-field radiation was obtained from the same PVGIS typical meteorological year dataset used to drive the photovoltaic radiation simulations. Global horizontal, direct normal, and diffuse horizontal irradiance were extracted from the source weather data. The open-field forcing followed the same timestamp conversion and solar-position treatment as the shaded simulations. Hourly global horizontal irradiance was integrated over each local-standard-time day and converted to daily shortwave radiation for WOFOST. The simulation years represent synthetic calendar labels rather than observed historical growing seasons.
