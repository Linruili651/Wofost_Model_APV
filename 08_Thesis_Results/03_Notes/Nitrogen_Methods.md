# Nitrogen leaching: implemented method and interpretation


## Thesis-ready English methods

The water-limited analysis was extended using WOFOST 8.1 coupled to the multilayer water balance and the SNOMIN soil nitrogen module. This additional experiment simulated crop growth, soil water availability, nitrogen uptake and nitrogen transformations within a common daily framework. The original WOFOST 7.3 PP and water-limited simulations were retained as a separate experiment. Differences between these experiments therefore cannot be attributed exclusively to nitrogen availability, since the model configuration and management assumptions also differ.

An estimated soil nitrogen scenario was constructed because field measurements of initial mineral nitrogen and fertiliser applications were unavailable. The hydraulic properties of the BK50 candidate profile L5102_K342 were retained, including its 200 cm profile depth and the 105 cm reference rooting-depth limit; crop-specific rooting limits were also respected. SoilGrids estimates of soil organic carbon and pH were incorporated at the Aachen weather location (50.801° N, 6.088° E). Soil organic matter was calculated from organic carbon using a carbon fraction of 0.58. SoilGrids total nitrogen was archived but was not treated as plant-available mineral nitrogen. Reference C:N ratios of 17 in the upper 25 cm and 25 below this depth were adopted from the existing SNOMIN example configuration. Initial mineral nitrogen was set to 30 kg nitrate-N ha−1 and 5 kg ammonium-N ha−1 in the upper 25 cm, distributed in proportion to layer thickness; deeper layers were assigned zero initial mineral nitrogen as an explicit scenario assumption. These estimates and reference values do not constitute a measured nitrogen profile for the study site.

The six crops were simulated under open-field conditions, fixed-tilt conventional PV and fixed-tilt semi-transparent PV. Each PV treatment retained the complete seasonal radiation series at 225 spatial points, and a separate soil–crop simulation was performed for each point. Corresponding light treatments used the same meteorological forcing, rainfall, initial soil conditions and management rules. A common production target was defined for each crop as 90% of its open-field WOFOST 8.1 potential harvest-organ dry-matter yield. This target served as an evaluation benchmark rather than a constraint guaranteed by the management algorithm. Simulated inputs were calculated independently at each point and subsequently aggregated using equal area weights over the common 1,024 m² plot. This represents idealised spatially differentiated management.

Daily irrigation was triggered when root-zone plant-available water fell below 50% of the capacity between field capacity and wilting point. The calculated application restored this fraction towards 90%, after subtracting the known rainfall for the current day, subject to a maximum of 5 mm d−1 and a minimum application of 1 mm. Irrigation efficiency was set to one. Adaptive mineral nitrogen applications were based on a seven-day uptake buffer, calculated from the crop parameter for maximum daily nitrogen uptake and its non-fixing fraction. When available root-zone mineral nitrogen fell below half of this buffer, an application was calculated to replenish the buffer. Applications were separated by at least seven days, restricted to development stages 0–1.3, and capped at 80 kg N ha−1 per event and 400 kg N ha−1 per crop season. Applied nitrogen comprised equal nitrate-N and ammonium-N fractions and was incorporated at 10 cm depth. Soybean retained the fixed-fraction biological nitrogen fixation assumption in its crop parameters and received no routine mineral nitrogen under the chosen management rule. These thresholds were analyst-defined scenario settings, not calibrated management recommendations or the solution to a minimum-input optimisation problem.

Irrigation and fertiliser applications were passed to the existing PCSE processes through management signals, without replacing the crop growth, water balance or nitrogen transformation equations. The SNOMIN reference concentrations of 1 mg ammonium-N L−1 and 4 mg nitrate-N L−1 were retained for infiltrating water; the implementation consequently assumes these concentrations for both rainfall-derived and irrigation-derived infiltration. Seasonal nitrogen leaching was calculated as the cumulative downward nitrate-N and ammonium-N flux through the base of the 200 cm soil profile. Internal transfers between layers were excluded from this boundary flux. Denitrification and the model's upper-boundary nitrogen export were recorded separately. Totals were integrated until each crop simulation ended and therefore represent crop-season losses rather than annual losses including the post-harvest period.

The completed experiment comprised 18 crop–light combinations and 2,706 managed soil–crop seasons, accompanied by 2,706 WOFOST 8.1 potential-production reference seasons. Recorded management commands were checked against the quantities received by the model, and water and nitrogen mass balances were evaluated for every managed point simulation. Maximum absolute residuals were below 0.001 mm and 0.001 kg N ha−1, respectively. These checks establish numerical consistency; they do not establish agreement with field observations. The analysis is interpreted as a conditional scenario assessment because initial nitrogen, organic-matter dynamics, management thresholds and parts of the soil profile were estimated or transferred from reference sources.








> All 18 managed crop–light combinations produced usable harvest results. Fifteen combinations attained the common production target, whereas all three sugar-beet treatments remained below it. No irrigation was triggered under the specified weather, initial-water and management assumptions. Reduced inputs in treatments that failed to attain the target were not interpreted as savings at equal production.


- : `02_WLP_Model/Nitrogen_Extension/`.
- : `04_Soil_and_Python/Nitrogen_Inputs/Aachen_BK50_SoilGrids_Target.json`.
- : `07_Full_Season_Run/target_resource_run/`.
- : `08_Thesis_Results/05_Target_Inputs/`.
- : `08_Thesis_Results/View_Final_Figures.html`.
- : [PCSE SNOMIN](https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/snomin.html), [PCSE engine](https://pcse.readthedocs.io/en/stable/_modules/pcse/engine.html), [SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html). , .
