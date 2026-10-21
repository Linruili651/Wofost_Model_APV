# Implementation Update-

## Nitrogen extension added 2026-10-20-

Use `02_WLP_Model/Nitrogen_Extension/README.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling.

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed.

**Boundary clarification

# Source Note-

This detailed note predates the six-folder layout; use this folder's README for current commands.








||/||
| --- | --- | --- |
|`LEGENDE_SPALTEN_DBF.txt`|/|FK, NFK, KF, ,|
|`INFO_ONP.txt`, `Tabelle_ONP.xlsx`||;  DICKE_SCH, FK_SCH, NFK_SCH, LK_SCH, KF_SCH, LD_SCH, HM_BDA|
|`INFO_JDM.txt`, `Tabelle_JDM.xlsx`|1–20 dm ,|;  10 cm|
|`INFO_KRZ.txt`, `Tabelle_KRZ.xlsx`|, , 1.5 m, 2 m|;|




BK50  ONP  `DICKE_SCH`(dm), `SUM_DICKE_OBEN`, `SUM_DICKE_SCH` ; JDM  `WEA`(, dm) `WEG`. , , . 1 dm = 10 cm.





BK50  ONP :

- `FK_SCH`, `NFK_SCH`, `LK_SCH`:  mm/dm; , .
- `SAND_SCH`, `SILT_SCH`, `TON_SCH`, `HM_BDA`: . , , .


BK50  ONP  pF 2.5 ;  `PFFieldCapacity` .  `SMfromPF`  `CONDfromPF` , . , , .









|||/Treatment|
| --- | --- | --- |
|`NO3I`,  `NH4I`|BK50|Nmin ;|
|`FSOMI`|BK50 ,|, /|
|C:N `CNRatioSOMI`|,|;|
|, , ,|||
|/|||
|pH `Soil_pH`,  `CRAIRC`||; BK50  `ZPH_A`, `ZPH_G`  pH,  pH|
|,||SNOMIN , ,|











||||
| --- | --- | --- |
||`RD`|cm; ,|
||`SM`, `WC`|/,|
|,|`WTRAT`, `EVST`|, cm ;  mm  10|
||`TSR`|,|
||`BOTTOMFLOW`, `BOTTOMFLOWT`|/;|
|/|`NO3LEACHCUM`, `NH4LEACHCUM`|SNOMIN ,  kg N/ha;|
||`NDENITCUM`|,  N2O|
||`NLOSSCUM`|,|
