# V14：用户提供的 Mercedes-AMG C63 参考车

用用户提供的 `98-mercedes-amg-c63.rar` 替换 V13 简化 A4L；保留完整原始模型文件与上一版道路。车头朝 +X，默认停在大路 `(7.5, 44.25, 0)`。

## 成果

- [完整道路场景](road_trial_v14_c63_reference.blend)
- [独立 C63 车模](mercedes_amg_c63_reference.blend)：原点落地，单位米；可 Append `REFERENCE_Mercedes_AMG_C63_EXCLUDE_FROM_MAP` 集合复用。
- [车头预览](c63_front.png)、[车尾预览](c63_rear.png)、[俯视比例](road_scale_top.png)、[全景](overview.png)
- [几何校正报告](geometry_report.json)、[最终文件读回检查](saved_file_validation.json)
- `replace_c63.py`：以压缩包内原始 `.blend` 为输入；`C63_ROAD_SOURCE` 可指定当前道路场景，否则使用 V13。运行时关闭 Blender 脚本自动执行。

## 按实车校正的尺寸

依据外形及四门结构，将素材作为 W205 C63 三厢轿车参考。参数来自 [奔驰 2018 AMG 用户手册补充册，第 38 页（PDF 第 41 页）](https://static.oneweb.mercedes-benz.com/css-oom-assets/en-lb/pdf/mercedes-amg-c-class-owners-manual-supplement-june-2018-1.pdf)。

| 项目 | 当前模型 |
| --- | --- |
| 长 | 4.756 m |
| 车身宽，不含后视镜 | 1.839 m |
| 宽，含展开后视镜 | 2.020 m |
| 高 | 1.426 m |
| 轴距 | 2.840 m |
| 前悬 / 后悬 | 0.854 / 1.062 m |
| 大路 | 4.5 m，水平 |
| 小路直线名义宽 | 2.7705 m，约 1.51 倍 C63 车身宽 |

前后悬参照[同期奔驰车型手册尺寸图](https://www.mercedesonlease.co.uk/wp-content/uploads/2017/04/c-class-saloon-estate.pdf)。同一代不同市场、年款与配置可能有差异；此处不是当前混动 C63 S E PERFORMANCE 的尺寸。

仅按平直路段、车辆居中且与道路平行计算：小路每侧车身净余量约 0.466 m，计入后视镜约 0.375 m。这不代表发卡弯动态通过性。

## 处理与验证

- 源模型前向 −Y，转换为项目 +X；原文件没有实车单位标定。分开校正车身长、宽、高、轴距与后视镜宽度，避免把含后视镜总宽误当成车身宽。
- 以原作者渲染细分等级固化网格；轮胎旋转驱动与旧控制器不带入道路。轮胎在 XZ 平面保留圆形，四轮最低点放至 Z=0；轮距、胎宽、悬架和转向未做实车物理校准。
- 保留用户车模的外形和部件，更新旧版材质为黑色金属车漆、深色车窗、轮胎、轮毂及灯罩材质。源文件缺少的 HDRI 和蓝图图片不属于车身贴图；它们及原场景背景、重复隐藏车身不导入。
- 完整场景和独立车模分别重新打开，测量实际网格长宽高、轴距、四轮落地，检查没有缺失的已用贴图。
- 比对 139 个非车辆环境网格的顶点、面、变换、材质槽，确认道路、护栏、石块、沟渠与地形未改变。

仍是 Blender 静态参考车，不是 BeamNG 可驾驶车辆。BeamNG V2 地图包保持有效；车辆没有加入地图导出。

## 来源与文件分发

源文件：用户本地提供的 `98-mercedes-amg-c63.rar`，仅解包其中 `Mercedes AMG C63.blend`；`.blend1` 未解包。

模型作者：[wishingchain](https://free3d.com/user/wishingchain)。对应[Free3D 模型页](https://free3d.com/3d-model/mercedes-amg-c63-hi-poly-model-partially-rigged-805791.html)的文件名、大小、创建时间与所提供文件一致；页面标示 **Personal Use License**，作者要求视频使用时署名。

原始车模与含该车模的 `.blend` 保留本地，目录中的 `.gitignore` 已排除这些二进制文件，防止随公开 GitHub 仓库再分发。未来若要公开模型文件，需另行确认相应许可。原始网格未被当作本项目原创。
