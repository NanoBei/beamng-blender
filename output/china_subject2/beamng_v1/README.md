# 中国 C1 科目二闭环地图 · BeamNG V1

目标游戏：**BeamNG.drive 0.39**。以用户确认的 [Blender V07](../blender_v07/README.md) 为源，生成可安装的自由驾驶地图包、独立 DAE、PNG 材质和出生点。原 V07、原山区发卡弯及其他项目均未改动。

**已完成文件转换，123 项离线检查通过，尚未在 BeamNG.drive 0.39 内加载、重载或驾驶验证。** 当前主机是 macOS，游戏运行在用户的 Windows 电脑。预览图来自导出 DAE 与材质 JSON 重新读入 Blender，不是游戏截图。

## 使用

- **[地图安装包 china_c1_subject2_v1.zip](china_c1_subject2_v1.zip)**
- **[Windows 安装与试车说明](Windows安装与试车说明.txt)**
- [离线验收报告](validation_report.json) · [导出资产清单](export_report.json)
- [导出资源全景](previews/01_game_assets_overview.png) · [俯视图](previews/02_game_assets_top.png) · [坡道](previews/03_game_assets_hill.png)
- [游戏资产工作文件](china_subject2_game_assets.blend) · [DAE 独立读回工作文件](china_subject2_dae_readback.blend)

将 ZIP **不解压**放入 BeamNG 启动器打开的当前用户目录 `mods` 文件夹，在 Freeroam 搜索 **China C1 Subject 2 - Closed Loop**。默认出生点 **Exam Start / 考试入口**，另有大路和 S 弯入口，共 3 个。安装方式依据 [BeamNG 官方说明](https://documentation.beamng.com/tutorials/mods/installing-mods/)。

## 保留的场地

- 考试区 **90 × 60 m**，五项各一处，倒库至侧方 8 m 直连，出口回到入口。
- S 弯外半径 7.5 m、内半径 4 m，两段 135°；净宽 3.5 m。
- 发卡弯、大路和回程路均 Z=0；科目二坡道保留 10% 恒坡、R30 竖曲线、2.297769 m 顶高。
- 库位、车道、控制线、直角弯均使用 V07 原几何。主要道路使用独立碰撞网格，与可视路面一致。
- 保留黑黄路缘、白色标线、黄色停车线、中文标牌、排水格栅、围栏和树木。
- 场外补充 Z=-0.03 m 的平整草地支撑，整体支撑范围 390 × 320 m，考试区域位置与尺寸不变。

这是自由驾驶地图，没有考试自动评分、交通 AI、隧道或雨雾/湿滑项目。可驾驶车辆使用游戏自带车辆或用户已有模组。Blender 中的 C63 静态参考车、尺寸文字、展示底板和地面展示标题均不进入地图；包内没有第三方车模网格。

## 网格与材质

共 **13 个 DAE**，道路、坡道挡墙、路缘、地块、外部草地、标线、路面细节、标牌、围栏、草丛及树木按用途拆分。10 棵树复用一个树模型，并有高低两档 LOD；只有树干有碰撞。合计可视实例约 **292,764 三角面**，碰撞实例 **38,212 三角面**。

碰撞采用官方 `base00 → start01` 下的 `Colmesh_*‑1` 节点及 `collision-1` detail，TSStatic 选择 `Collision Mesh`。道路保留精确低面数形状；围栏使用 4 个简单实心面板代理，保留入口开口。标线、接缝、轮胎印、格栅小细节、草丛及树叶没有独立刚体碰撞。每个导出子网格限制在 54,000 顶点以内。

原程序材质的颜色通过无光照烘焙转为 PNG：路面 4096²、草地 2048²、白漆 512²（含磨损透明度）。粗糙度及金属度转换为 PBR 参数。原 Blender 程序凹凸未作为切线法线贴图导出；最终观感与 BeamNG 光照及材质系统有关。白漆/箭头在游戏副本中离路面 6 mm，细节 4 mm，用于减轻远距离深度闪烁；XY 净尺寸保持不变。

材质统一前缀 `c1v1_`，虚拟路径只使用 `/levels/china_c1_subject2_v1/`。自定义 `C1V1_CONCRETE` 为干燥硬路面摩擦基准，没有覆盖游戏全局同名路面，尚未按真实轮胎/路面实测校准。

## 验收范围

[validate_package.py](validate_package.py) 使用独立 pycollada 解析实际 DAE；检查坐标、法线、UV、三角面、材质绑定、LOD/碰撞层级和 ZIP 内的真实路径，重新量取库位/车道宽度、坡道高程与坡度，检查 6,546 个道路横向/中心线支撑点、标线贴地及 3 个出生点的车辆占地范围。原 Blender SHA-256 保持不变。

[preview_export.py](preview_export.py) 从最终 DAE 重建全部可视对象，并按 `main.materials.json` 建立预览材质。[三张读回图已逐张检查](visual_review.json)，场地布局、平面发卡弯、坡道与材质均可见。静态文件检查不替代实际游戏的轮胎接触、转向、碰撞、性能及保存重载测试。

## 可复现脚本

由仓库根目录运行。先备份想保留的同名输出；命令只改动 `beamng_v1` 下的生成文件。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/beamng_v1/export_map.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python output/china_subject2/beamng_v1/preview_export.py
python3 output/china_subject2/beamng_v1/validate_package.py
```

Blender 侧使用内置 Python/NumPy 与 [beamng_io.py](beamng_io.py)，不依赖 Collada 插件。独立验证需 NumPy、Pillow、pycollada 0.9.3 和 Shapely 2.1.2；本次使用已安装的工作区运行时、临时 pycollada 依赖和 V07 的 `.deps`。最终 ZIP 不含 `.blend`、脚本、参考资料、机器绝对路径或游戏缓存。

格式依据：[DAE 资产管线](https://documentation.beamng.com/modding/levels/level_creation/section11/)、[静态物体及碰撞](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/)、[碰撞/LOD 命名](https://documentation.beamng.com/modding/levels/level_creation/section5/)、[逐行场景 JSON](https://documentation.beamng.com/modding/levels/level_formats/items/)、[出生点](https://documentation.beamng.com/modding/levels/level_classes/spawn/)、[物理路面](https://documentation.beamng.com/modding/levels/level_formats/groundmodels/)。资料访问日期 2026-10-14。
