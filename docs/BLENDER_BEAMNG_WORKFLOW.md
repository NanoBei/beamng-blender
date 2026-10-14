# Blender 与 BeamNG 地图工作流程

这份记录供后续对话直接继续本仓库的道路模型和驾驶场地开发。它记录的是已用过的流程和证据，不代表尚未做过的游戏验证。

## 当前项目位置

- 所有模型按项目放在 [`output/`](../output/) 下。当前已完成道路项目为 [`mountain_hairpin_road/`](../output/mountain_hairpin_road/)，科目二项目在 [`china_subject2/`](../output/china_subject2/)。
- 已确认发卡弯的 Blender 场景：[`road_trial_v9_flat_main.blend`](../output/mountain_hairpin_road/blender_trial_v9_flat_main/road_trial_v9_flat_main.blend)。
- 已确认的 35° 平面图和纵横断面图包也保存在该项目子目录中，参见该项目 README。
- BeamNG 测试 ZIP：[`tight_hairpin_test_v1.zip`](../output/mountain_hairpin_road/beamng_hairpin_test_v1/tight_hairpin_test_v1.zip)。压缩包内地图目录必须从 `levels/tight_hairpin_test/` 开始。
- BeamNG 测试包做过 Collada、网格、JSON、路径和 ZIP 离线检查；**尚未在 BeamNG.drive 内加载、保存重载或驾驶测试**。Windows 游戏在另一台电脑上。

## Blender 建模

- 本项目制作时使用 Blender 5.2.2。实际场景可优先通过已连接的 Blender MCP 查看和编辑；操作后用场景信息和视图检查结果。工具不可用时，可用 Blender 后台脚本处理已保存的 `.blend`，不要在重置场景的前提下误操作用户的实时场景。
- 该 Blender 版本未提供内置 Collada 导出操作。本项目通过 [`export_map.py`](../output/mountain_hairpin_road/beamng_hairpin_test_v1/export_map.py) 写出 DAE；若升级 Blender 或换用导出插件，先重新验证尺度、材质名、UV、法线和碰撞。
- 模型坐标用米、Z-up。分清道路的 XY 平面形状与 Z 高程；入口坡度、弯道内外侧、横坡和接缝需要分别检查。
- 用户确认的方案要记录为数字和文字，不只依赖对话：工作宽度、弯角定义、内圆角、坡度起点与过渡、地块边界、护栏边、末端长度。
- 对 Blender 场景里的展示对象（参考车、相机、柔光、展示地板）使用清楚的命名或集合。导出前只选游戏资产，并核对导出列表，避免参考物混入地图。
- 用新文件名保存每个确认版本。不要覆盖最后一个已确认且可打开的 `.blend`；修改失败时回退到上一版。

## 发卡弯项目已经确认的参数

这些参数只约束发卡弯项目，不能直接套到科目二地图：

- 大路宽 4 m、标高 0，整段水平；小路直线宽 2.775 m。
- 小路入口约 6 m 渐变到中心线下坡 10°，随后约 10°；末端直线 16 m。
- 两处发卡弯的内夹角按既有确认平面图，内侧圆角半径 1 m；局部补角用于缓和急转。
- 大路外侧没有护栏，边缘保留无防护落差；只保留靠小路一侧的两段直护栏。
- 10° 是中心线纵坡，不代表整个路面上所有点或三角面都是 10°。导出的几何检查发现内弯存在更陡的局部路面；实车是否跳动、蹭底或悬轮尚未检查。

## BeamNG 静态地图导出要点

BeamNG 官方流程说明和本项目经验如下。BeamNG 文档会随版本更新，开始新地图时应重读链接中的当前说明。

- 单独静态网格使用 DAE；采用米、Z-up，导出前应用变换、检查外法线并三角化。DAE 至少要有一个 UV 集；贴图用 PNG。
- `main.materials.json` 的材质 `mapTo` 必须与 DAE 中的材质/材质槽名称完全匹配。文件路径使用 `/levels/<关卡名>/...`，不可写当前电脑上的绝对文件路径。
- `main/items.level.json` 是逐行 JSON：每行一个对象，不能包成 JSON 数组。`TSStatic.shapeName` 必须指向 ZIP 中实际存在的 DAE；单位变换应为位置、旋转矩阵和缩放的有效数值。
- `info.json` 中的默认出生点必须与 `main/items.level.json` 里的 `SpawnSphere` 名称一致，并放在可承载车辆、远离边缘的位置。
- 道路/护栏/地形可拆为多个 DAE，以便分别设材质和碰撞。检查材质的物理路面类型，不要只看渲染颜色。
- BeamNG 官方建议重型资产使用简化碰撞网格。本项目第一版为了精确保留路面形状而采用整张可视网格碰撞，约 5.2 万个三角形，配置为 `Visible Mesh Final`。这是小范围的试验权衡；新地图优先把路面碰撞单独简化并在游戏里驾驶验证。
- ZIP 应直接包含 `levels/<levelName>/...`，不要再套一层项目文件夹。Windows 安装时将 ZIP 不解压放入启动器打开的 BeamNG 用户文件夹 `mods` 目录。
- 首次地图测试按顺序确认：地图列表可见、正确出生、尺度与朝向正确、路面和地形有碰撞、材质路径无警告、保存并重载正常、低速/目标车辆驾驶正常。记录游戏版本和 `beamng.log` 错误。
- 当前导入包未在游戏内实测。官方第一关卡模板以及每版游戏存档格式可能与手写 JSON 有差异；如加载失败，优先用目标版本的 World Editor 创建空地图并保存，再比对实际文件结构，不要盲目改 Blender 网格。

## 新建中国科目二项目的起点

见 [`output/china_subject2/README.md`](../output/china_subject2/README.md)。目前只确定用户要开始做“中国科目二地图模型”；尚未确定地区、考试项目组合、场地尺寸、车辆、布局来源、视觉风格或是否要求符合某地现行考试标准。开始布置前把这些作为需求逐项确认或以用户给的实地图/草图为准。不要猜测全国统一的项目尺寸。

建议顺序：确定用户想复刻的科目二项目和边界 → 输出带尺寸、转弯半径和路线方向的俯视草案 → 用户确认 → Blender 分版本建模 → 建立低面数驾驶碰撞面 → 按目标 BeamNG 版本做一个小型可加载地图 → 在 Windows 游戏中记录加载与驾驶问题 → 修正后再打包。

## 官方参考

- [BeamNG 关卡制作概览、目录和首个可玩关卡检查表](https://documentation.beamng.com/modding/levels/level_creation/section1/)
- [BeamNG Blender → DAE 资源流程、UV、材质和碰撞](https://documentation.beamng.com/modding/levels/level_creation/section11/)
- [BeamNG TSStatic 及碰撞模式](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/)
- [BeamNG `items.level.json` 逐行格式](https://documentation.beamng.com/modding/levels/level_formats/items/)
- [BeamNG 材质 JSON](https://documentation.beamng.com/modding/file_formats/materials/)
- [BeamNG 地面物理模型](https://documentation.beamng.com/modding/levels/level_formats/groundmodels/)
- [BeamNG Windows 模组安装](https://documentation.beamng.com/tutorials/mods/installing-mods/)
