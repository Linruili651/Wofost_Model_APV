# 最终代码包下载说明（2026-10-21）

已按用户确认，仅保留代码包；额外的1.7GB原始数据库与全部逐点逐日结果大备份已停止上传。

- 可直接解压的完整代码与复现输入包：Aachen_Hao_Final_Run_20261021_GitHub_Ready.zip（39,555,913字节，4,685个文件）。
- Google Drive单文件下载：https://drive.google.com/file/d/1lSA3ySaFGG21axucPuUCqG8iufiz4Y6y/view?usp=drivesdk
- GitHub私有仓库：https://github.com/Linruili651/Wofost_Model_APV

来源是 Update/Aachen_Hao_统一运行项目，包含最后一次补上的初始氮设置、补水补氮规则、模型代码、天气与保存的辐射输入，以及2026-10-21最终复跑材料。已核对1168个最终运行代码与输入文件的哈希。

初始矿质氮35kgN/ha（硝态氮30、铵态氮5），含分层有机质、碳氮比和pH估计。氮参数在04/Nitrogen_Inputs下的Aachen_BK50_SoilGrids_Target-目标投入估计情景.json；补氮规则与入口在02/Nitrogen_Extension下。属于估计参数管理实验，尚未经田间验证。

从Drive下载ZIP即可直接解压。若仅从GitHub下载：先下载并解压整个仓库，再运行Restore_Portable_Package.ps1，将portable-package目录内19个已校验分块恢复为相同的代码ZIP。GitHub内的部分源码和参数已展开，便于查看；完整项目布局在ZIP内。

代码ZIP的SHA-256：0cba86f4e18903ea3ddb2ca39e97a65ba719d07d4f0a865d5abdd97ab3b60485

代码包保留源码、复现输入、依赖清单与汇总/复跑记录；不包含本机虚拟环境、原始BK50数据库ZIP、原生Radiance二进制及全部压缩逐日明细。已有辐射输入可用于作物复跑；重算Radiance需另行准备原生程序。完整核验清单为同目录Verified_Final_Run_Inputs.json。

Partial_Backup_Not_Required-未完成大备份_无需下载 子文件夹仅保存此前少量成功上传的大备份分卷，不完整，无需下载。包内较早的备份计划说明以本页最终范围为准。