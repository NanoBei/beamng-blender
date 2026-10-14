# V07：闭环科目二场地 Blender 模型

2026-10-14，按用户确认的 [V07 闭环平面图](../layout_proposal_v07/layout_v07.png) 制作。地块 **90 × 60 m**，米制、Z 轴向上。科目二五项各一处，发卡弯与大路压平，科目二坡道保留原坡度。本次没有制作 BeamNG 文件。

## 打开与预览

- **最终可编辑模型：** [china_subject2_v07_final.blend](china_subject2_v07_final.blend)
- [基础几何检查点](china_subject2_v07_geometry.blend)
- [开始前保存的原实时场景](before_v07_live_scene.blend)，包含原场景当时的未保存状态；原 V03 文件未覆盖。
- [斜俯视总图](previews/01_overview.png) · [与平面图同朝向的俯视图](previews/02_top.png)
- [倒车入库](previews/03_reverse.png) · [侧方停车](previews/04_parallel.png) · [坡道](previews/05_hill.png)
- [S 弯](previews/06_s_curve.png) · [直角转弯](previews/07_right_angle.png)
- [平面发卡弯](previews/08_flat_hairpin.png) · [回程闭环](previews/09_return_loop.png) · [大路与 C63](previews/10_main_road.png)

## 已实现的布局与尺寸

考试路线：**倒库 → 侧方 → S 弯 → 直角 → 坡道 → 西侧回程 → 倒库入口**。倒库至侧方为 8 m 直连；回程路净宽 4.5 m，两端中心线 R10 圆弧。中部大路两端接入考试连接道路。

| 部分 | 本版参数 |
| --- | --- |
| 倒库 | 库长 5.558 m、库宽 2.447 m；库前车道 7.287 m；左右控制线距离各 7.287 m |
| 侧方 | 库长 8.287 m、库宽 2.647 m；旁侧车道 3.5705 m |
| S 弯 | 两段 135° 相切反向圆弧；外半径 7.5 m、内半径 4 m、净宽 3.5 m |
| 直角 | 净宽 3.908 m；两条外臂各 10 m |
| 科目二坡道 | 10% 恒坡，R30 竖曲线；平台 6 m；总水平投影 57.940446 m，最高 2.297769 m |
| 平面发卡弯 | 复用原 V20 小路的实际 XY 轮廓、内弯补角和喇叭口；直段净宽 3 m，路面 Z=0 |
| 大路 | 原段 44 × 5 m，向两端延伸接通；路面 Z=0 |

全部净尺寸按漆线内缘量取。普通线宽 0.15 m，外侧留 0.30 m 铺装边带；黑黄路缘宽 0.18 m、高 0.15 m，位于有效车道以外。坡道停车基准线距上坡起点水平 12 m，前后控制线中心各距 0.65 m。

坐标延用平面图原点：X=-10–80 m、Y=0–60 m。顶视相机的朝向与确认图一致，北在画面右侧。**V06 的 150° S 弯试拟没有进入本模型。**

原山区发卡弯文件未修改。新模型只保留其平面道路形状，取消纵坡、横坡、悬崖和深沟；不含隧道、雨雾或湿滑等额外项目。

## 材质、设施与车辆

复用已完成 V03 的程序材质：浅灰混凝土、较深沥青、细骨料、色差、磨损白漆及黄色停车线。增加板块接缝、修补、轻微裂纹、短轮胎印、排水格栅、项目标牌、少量围栏及绿化。参考照片中的车辆、阴影、教学叠加标记没有贴入地面。

平面道路经过二维求并与分区三角化；混凝土和沥青在交叉口共用边界，没有整块重叠路面。坡道单独按竖曲线采样，停车线及边线贴合路面；实体挡墙承托坡道，不引入原山区地形。

保留原 C63 高精渲染版本 **9,394,692 三角面**，视口使用 **259,722 三角面** 的轻量副本。二者共享父对象与位置，默认只在相应显示模式出现一套；C63 放在大路上作为静态比例参考。长 4.756 m、车身宽 1.839 m、含镜宽 2.020 m、高 1.426 m、轴距 2.840 m。

模型作者 [wishingchain](https://free3d.com/user/wishingchain)，来源为用户提供的同一 C63 压缩包及已校准独立车模，沿用已记录的 Personal Use License。含第三方车模的文件仅本地保留，`.gitignore` 排除，未发布。

## 集合与编辑

- `01_Roads`：平面混凝土、平面沥青、独立坡道与挡墙。
- `02_Markings`：可单独编辑的边线、库位线、控制线、箭头。
- `03_Facilities`：黑黄路缘、标牌、排水口、围栏与路面细节。
- `04_Landscape`：地块、树木和草丛。
- `05_ReferenceCar_HIGH` / `06_ReferenceCar_PROXY`：高精车与轻量车。
- `07_Dimensions`：默认隐藏的技术尺寸文字。
- `08_Presentation`：相机、灯光、展示底板和项目说明文字。

文件内贴图和中文字体已打包，其他路面材质来自节点。车辆高精网格采用视图层隐藏，轻量集合禁止渲染；若手动切换，请保持只显示一套。

## 验收与实现文件

[验收报告](validation_report.json) 从另一个 Blender 进程重新打开最终文件，直接读取世界坐标网格，**62 项检查全部通过**。检查包括：库位与车道尺寸、S 弯圆弧和夹角、回程路宽与圆弧、主路 5 m 净宽、平面路面零高程、坡道坡度与竖曲线、停车线间距、道路接通、标线支撑与高度、设施净空、C63 比例和四轮落地、资源完整性。

已逐张查看 [10 张最终预览](visual_review.json)，检查整体布局、坡道接地、S 弯边线、平面发卡弯和回程路口。

关键尺寸容差 1 mm；标线距实际路面的实测范围约 1.996–2.015 mm。验收是模型几何检查，不等于车辆转向通过性、实际驾驶或现行考场认证测试。原资料与 A4L 尺寸来源继续保留在 [项目参考资料](../references/)。

- [本版参数快照](parameters_v07.json)：已确认布局、来源尺寸和实施假设。
- [几何准备脚本](prepare_geometry.py)：只读归档平面图与原道路边界，输出 [统一几何输入](geometry_input.json)。
- [Blender 生成脚本](build_model.py)：复用原材质、车模及树木资产，按统一输入生成场景。
- [最终修整记录](finalization.json) · [尺寸验收脚本](validate_model.py) · [渲染脚本](render_previews.py)。

首次二维准备使用 NumPy、Pillow 和项目内的 Shapely 2.1.2。Shapely 只安装在本目录 `.deps/`；Blender 本身不需要安装这些第三方库，读取生成后的 JSON 即可。

重建前请保留现有成果版本。由项目根目录执行：

```sh
/Users/macmini/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 output/china_subject2/blender_v07/prepare_geometry.py
/Applications/Blender.app/Contents/MacOS/Blender --background output/china_subject2/blender_v07/before_v07_live_scene.blend --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender_v07/build_model.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender_v07/validate_model.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/blender_v07/render_previews.py
```

本轮实际建模通过已安装的 Blender MCP 完成；保存后的验收和渲染使用独立后台进程。
