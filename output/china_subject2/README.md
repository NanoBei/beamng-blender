# 中国 C1 科目二写实场地

当前成果为用户确认的 **V07 闭环布局，90 × 60 m**，米制、Z 轴向上。五项考试场地各一处；发卡弯、大路和回程路为平面，科目二坡道保留 10% 恒坡。出口经西侧回程路接回入口。本项目保留 Blender 成果，并已按用户后续要求生成面向 **BeamNG.drive 0.39** 的地图安装包；尚未在游戏内加载或驾驶验证。

## 当前 BeamNG 地图包

2026-10-14，用户确认将 V07 转为 BeamNG 地图，目标版本 0.39。

- **[地图 ZIP](beamng_v1/china_c1_subject2_v1.zip)** · [Windows 安装与试车说明](beamng_v1/Windows安装与试车说明.txt)
- [转换说明、脚本与资源](beamng_v1/README.md) · [离线验收](beamng_v1/validation_report.json)
- [导出 DAE 读回预览](beamng_v1/previews/01_game_assets_overview.png)（不是游戏截图）

独立碰撞、烘焙材质及 3 个出生点已配置。C63 仅保留在原 Blender 文件中；地图驾驶使用游戏内车辆。

## 当前 V07 成果

2026-10-14：用户确认闭环图后，已通过 Blender MCP 完成建模。

- **[最终可编辑 Blender 模型](blender_v07/china_subject2_v07_final.blend)** · [基础几何检查点](blender_v07/china_subject2_v07_geometry.blend)
- [完整说明、生成脚本与参数](blender_v07/README.md) · [本版参数快照](blender_v07/parameters_v07.json)
- [斜俯视全景](blender_v07/previews/01_overview.png) · [总俯视](blender_v07/previews/02_top.png) · [S 弯局部](blender_v07/previews/06_s_curve.png)
- [保存后 62 项几何检查](blender_v07/validation_report.json) · [10 张预览检查记录](blender_v07/visual_review.json)
- [已确认的 V07 平面图](layout_proposal_v07/README.md)

倒库与侧方 8 m 直连，S 弯保持两段 135°、外半径 7.5 m、净宽 3.5 m；总俯视图旋转展示以便辨认 S 形。原发卡弯及 5 m 大路按 1:1 XY 轮廓加入，新副本路面统一 Z=0。没有添加隧道、雨雾或湿滑等项目。原山区项目、V03 场景与原始参数未覆盖，开始前还另存了实时 Blender 场景。

## 历史 V03（100 × 75 m）

**以下保留旧版成果、布局与重建记录；当前模型以以上 V07 文件为准。**

### V03 成果

- **最终场景：** [china_subject2_v03_final.blend](blender/china_subject2_v03_final.blend)。含详细植被、路面颗粒、磨损漆线、设施和车辆。
- [V02 材质细化检查点](blender/china_subject2_v02_detailed.blend)：保留供回退比较。
- [V01 基础几何](blender/china_subject2_v01_geometry.blend)：场地、标线、路缘、相机与尺寸标注。
- [全景](previews/01_overview.png) · [总俯视](previews/02_top.png) · [倒库](previews/03_reverse.png) · [侧方](previews/04_parallel.png) · [坡道](previews/05_hill.png) · [S 弯](previews/06_s_curve.png) · [直角弯](previews/07_right_angle.png)
- [参数](parameters.json) · [实际网格验收报告](reports/validation_report.json) · [建模位置与路线记录](reports/build_manifest.json)

所有 `.blend` 都是独立文件；最终文件重新打开即可使用，贴图/字体打包或使用内部程序材质。后台制作没有修改发卡弯项目文件。

## 场地参数

尺寸公式的参考车辆由用户指定：A4L 长 4.858 m，车身宽 1.847 m（不含后视镜），高 1.439 m，轴距 2.908 m。

| 项目 | 参数 |
| --- | --- |
| 倒库 | 库长 5.558 m、宽 2.447 m；库前车道 7.287 m；从库位同侧边至控制线各 7.287 m |
| 侧方 | 库长 8.287 m、宽 2.647 m；旁侧车道 3.5705 m |
| S 弯 | 外半径 7.5 m、内半径 4 m；两段相切反向 135° 圆弧，净宽 3.5 m |
| 直角弯 | 净宽 3.908 m；外侧两臂各 10 m；90° 转角 |
| 坡道 | 净宽 3.5 m，恒坡 10%（约 5.71°），坡底/坡顶竖曲线半径 30 m |

坡道恒坡段水平长 20 m，圆弧过渡每端水平长约 2.985112 m。单侧上坡总水平长 25.970223 m、升高 2.297769 m；顶部平台 6 m，再对称下降，总水平长 57.940446 m。停车基准线距上坡起点水平 12 m，两侧控制线中心各偏移 0.65 m。

布局、连接道路和未规定细节为用户批准的建模设计值：100 × 75 m 地块、4.5 m 连接道路、10 m 连接弯中心线半径、0.15 m 普通线宽、1 m 实线/1 m 间隔、0.3 m 漆线外侧铺装边带、0.18 m 宽/0.15 m 高路缘。停车位和车道的净尺寸量取漆线内缘；横向坡道控制线量取中心。

路径为西侧入口 → 西南倒库 → 西北侧方 → 北侧坡道 → 东侧 S 弯 → 东南直角弯 → 南侧出口。原资料引用历史培训场尺寸；本模型不宣称符合现行考试场地认证标准。

## 材质与编辑

浅灰混凝土用于考试项目，连接道路使用较深沥青；白色标线、黄色坡道停车线、黑黄路缘分开制作。路面颜色差异、细颗粒、凹凸及漆面磨损来自内部材质节点；接缝、修补、裂纹、轮胎印和排水口为独立细节对象。实景照片仅用作参考，没有直接贴到路面。

集合：`01_Roads` 道路，`02_Markings` 漆线，`03_Facilities` 设施，`04_Landscape` 植被，`05_ReferenceCar_HIGH` 高精车，`06_ReferenceCar_PROXY` 轻量车，`07_Dimensions` 尺寸层，`08_Presentation` 展示相机/灯光/说明。

- 尺寸层默认隐藏，可在 Outliner 中切换；数值汇总也在参数文件与验收报告中。
- 视口显示约 26 万三角面的轻量 C63；渲染使用约 939 万三角面的高精网格。高精车网格在视图层隐藏，轻量车集合禁止渲染，二者共用同一位置父对象。
- 普通编辑不需要显示高精车。若手动切换版本，应同时隐藏另一套，避免重叠。
- C63 保留自己的实车比例：4.756 × 1.839 × 1.426 m、含镜宽 2.020 m、轴距 2.840 m；没有将场地尺寸改成 C63 公式。

## 重建与验收

在项目根目录运行；使用 Blender 5.2.2，无需安装其他建模插件。第三方文件禁止脚本自动执行。

```sh
python3 output/china_subject2/prepare_inputs.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender/build_scene.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender/finalize_scene.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender/validate_scene.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender/render_previews.py
```

归档准备脚本从用户原始 Downloads 文件和本仓库先前校准的 C63 复制资料。资料已归档后，重建只需运行后四条命令。修改参数后重建会替换同名生成文件；请先复制想保留的版本。

验收脚本独立打开最终场景，从实际网格量取库位、车道、控制线、圆弧、坡道和车辆尺寸；检查道路段接缝及标线下方的道路支撑，目标尺寸误差 ≤ 1 mm。它不执行驾驶、转向轨迹或认证测试。

2026-10-14：最终 V03 的 44 项检查全部通过；7 张 1600 × 1200 预览已逐张查看，见 [视觉检查记录](reports/visual_review.json)。已通过 Blender MCP 打开最终场景，并先另存了此前未保存的默认场景。

## 来源和本地文件

- 原文档：[尺寸资料](references/documents/C1_subject2_reference_dimensions.md)、[实景图集](references/documents/subject2_realworld_references.md)。
- [12 张图片的来源、真实格式及 SHA-256](references/manifest.json)。在线扩展名与文件格式不同的图片，按真实格式归档。
- 车模为用户提供的 `98-mercedes-amg-c63.rar`，本项目复用同一源文件已经校准的静态版本。原始 `.blend` SHA-256：`1a144d39f38ebf275762fed9a9a5b92b9d40341416398d6ee83b243c7962c315`。
- C63 作者 [wishingchain](https://free3d.com/user/wishingchain)，[模型页](https://free3d.com/3d-model/mercedes-amg-c63-hi-poly-model-partially-rigged-805791.html)。沿用原素材记录的 Personal Use License，视频使用需署名。源文件、引用照片和含第三方车模的 `.blend` 仅本地保存，由 `.gitignore` 排除；未上传或发布。
