# BeamNG 驾驶测试包 V2（对应 Blender V12）

`tight_hairpin_drive_v2.zip` 为新的完整地图测试包，关卡名 **Hometown Hairpin Drive V2**，目录 `levels/tight_hairpin_drive_v2/`，与旧 V1 地图分开。

## 内容

- 水平 4.5 m 灰色柏油大路、2.7705 m 旧水泥小路、两个已平顺化的发卡弯。
- 土坡侧略高土坎、43 块露出路缘约 23–40 cm 的石块；悬崖侧无护栏，越过路缘后接陡降坡面。
- 0.5 m 净宽 × 0.6 m 深的排水渠、外侧植被土坡、靠小路侧的波形钢护栏。
- 道路、地形、石块、排水渠的静态碰撞。石块用低面数闭合可见网格精确碰撞；护栏使用单独简化碰撞梁/柱。草丛和细切缝不碰撞。
- 不包含可驾驶 Audi A4L，也不导出尺寸参考车、展示地板或模型底板。用游戏内车辆驾驶；若要求 A4L 动态特性，需要另行配置合适车辆。

## 已完成的检查

`validate_package.py` 使用 pycollada 独立读回 DAE，检查单位、路径、材质、三角面朝向、石块闭合和铺装范围外的净空、悬崖落差与导出一致、各对象碰撞开关、出生点支撑和 ZIP 完整性。详细结果为 `validation_report.json`；模型侧与导出清单见 `export_report.json`。

采用约 5 万个碰撞三角面的局部测试地图。为保存急弯和路缘的实际形状，路面/土坡使用 `Visible Mesh Final`；低面数石块也采用同样方式。护栏外观不碰撞，隐藏的简化梁柱碰撞体负责接触。这是本地图的明确取舍，未进行性能实测。

水泥路使用本地图独立的 `HP2_CONCRETE` 干燥硬路面基准：静摩擦系数 1.0、滑动摩擦系数 0.8，未根据实地路面校准；路面颜色不会自动决定抓地力。柏油、土、草地、石头和金属分别映射地面类型。不要把本版驾驶结果等同于真实道路的安全通过能力。

**尚未在 Windows BeamNG 中加载、保存重载或驾驶验证。** 尤其需验证：出生正常、护栏隐藏碰撞体工作、石块能接触车轮/车身、路缘没有隐形支撑、土坡地面类型正确。当前游戏版本的材质与地面模型支持如有差异，以游戏日志和 World Editor 实测修正。

## Windows 操作

见 [`Windows导入与试车说明.txt`](Windows导入与试车说明.txt)。复制 ZIP 到游戏用户目录下的 `mods`，不解压；Freeroam 搜索 **Hometown Hairpin Drive V2**。建议停用旧 V1 以免选错地图。

## 重建

用 Blender 后台打开相邻 `blender_trial_v12_driving_edges/road_trial_v12_driving_edges.blend`，运行本目录 `export_map.py`。脚本导出独立素材并烘焙地形/路面贴图，不保存或覆盖 Blender 源场景。随后在装有 numpy、Pillow、pycollada 的 Python 环境执行 `validate_package.py` 生成并校验 ZIP。

验证器优先使用本机此前装在 `/private/tmp/beamng-dae-validator` 的 pycollada；临时目录失效时需在使用的 Python 环境安装 pycollada。生成的 `package/` 已在 ZIP 检查后清理，交付只保留 ZIP、预览和源脚本。再次验证会把现有 ZIP 解压到临时目录后检查；重新导出会重建 `package/`。

依据：[BeamNG 静态物体碰撞设置](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/)、[模型与碰撞制作建议](https://documentation.beamng.com/modding/levels/level_creation/section11/)、[关卡地面物理模型](https://documentation.beamng.com/modding/levels/level_formats/groundmodels/)。
