# V13：Audi A4L 简化外观参考车

用户确认本次仅替换 Blender 参考车，外形像 A4L／A6L、尺寸准确即可。采用 A4L，默认停在大路上。道路、地形、石块、排水渠和护栏继承 V12。

## 文件

- [道路场景](road_trial_v13_a4l_reference.blend)：完整 V13，参考车位于 `(7.5, 44.25, 0)`，车头朝 +X。
- [独立车模](audi_a4l_reference_asset.blend)：只有参考车及展示相机/灯光，车辆原点为地面，车头 +X，单位米。也可通过 Append 导入 `REFERENCE_Audi_A4L_EXCLUDE_FROM_MAP` 集合。
- [车头预览](a4l_front.png)、[车尾预览](a4l_rear.png)、[侧面预览](a4l_side.png)、[全景](overview.png)。均为 Blender 渲染。
- [尺寸检查](geometry_report.json)、[最终文件读回检查](saved_file_validation.json) 与 [可复现建模脚本](build_a4l.py)。脚本输入为已保存 V12 场景。

## 尺寸与外观范围

| 参数 | 数值 |
| --- | --- |
| 长 × 车身宽 × 高 | 4.858 × 1.847 × 1.439 m |
| 轴距 | 2.908 m |
| 前悬 / 后悬 | 0.907 / 1.043 m |
| 前 / 后轮中心 X | +1.522 / −1.386 m |
| 含展开后视镜总宽 | 模型约 2.068 m，为外观试拟值，未按实测校准 |

车身尺寸和轴距按下列奥迪中国资料；选用舒适悬架对应的 1.439 m 高度。参数表不代表所有 A4L 年款和配置均相同。

外形为自行建立的简化模型，含三厢轮廓、轮拱、四环中网、灯组、四门车窗、门把手、后视镜和轮毂。车身曲面、灯组轮廓、轮胎及后视镜属于近似造型；不是厂商 CAD、扫描模型或某一配置的精确外观复刻。无完整内饰、悬架、转向或车辆物理。

实际评估几何包围尺寸误差小于 0.05 mm（仅指数字模型整体包围尺寸，并非外观精度）。生成前后逐对象比对 139 个非车辆网格的顶点、面、变换与材质槽，确认环境未改变。

两个最终 `.blend` 已通过独立进程重新打开，读回车身几何、轮胎几何中心与四轮最低点：轴距 2.908 m，四轮最低点落在 Z=0，独立车模场景不含道路对象。

Blender 5.2.2 的 `bpy.data.libraries.write({scene})` 在本机尝试中发生原生崩溃。独立车模改用独立进程打开 V13、移除非车模对象、移动到原点后正常 `save_as_mainfile`；见 `export_reference_asset.py`。如需重新导出，使用该脚本，不要再用局部场景库写出。

本次没有改动 BeamNG V2 ZIP：参考车一直排除在地图导出外，V2 仍对应同一套 V12/V13 道路环境。本模型不能直接作为 BeamNG 可驾驶车辆。

## 网上检索与使用素材

2026-10-14 查阅：

- [奥迪中国 A4L 官方外观页面](https://www.audi.cn/zh/models/a/a4/a4l.specification.html)。
- [奥迪 A4L 车型配置与尺寸](https://www.audi.cn/content/dam/OneWeb/faw_vw/pdf/202601/a4/A4L_%E8%BD%A6%E5%9E%8B%E6%8A%98%E9%A1%B5.pdf)：4858 / 1847 / 1439 mm、轴距 2908 mm。
- [奥迪 A4L 尺寸图](https://www.audi.cn/content/dam/OneWeb/faw_vw/pdf/2023%E6%9B%B4%E6%96%B0%E8%BD%A6%E5%9E%8B%E6%8A%98%E9%A1%B5/11-3/Audi_A4L.pdf)：907 / 1043 mm 前后悬；图中 1411 mm 是另一悬架配置的高度，未套用到本版。
- [Sketchfab Audi A4 B9 / Nieve5677](https://sketchfab.com/3d-models/audi-a4-b9-7ba4f7fa8f32436a9685a8abaa5da302)：页面标示 CC BY 4.0，下载弹出登录要求；是普通 A4，不是中国 A4L。未下载或使用。
- [BlendSwap Audi A4 / amogh](https://blendswap.com/blend/8638)：页面标示 CC BY，下载需登录。未下载或使用。

最终没有引入第三方网格或贴图；车模几何由本项目脚本生成，以上链接作为资料及后续素材选项保留。Audi 名称和四环用于说明所参考车型，不表示官方提供或认可。
