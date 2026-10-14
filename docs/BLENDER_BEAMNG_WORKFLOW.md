# Blender 与 BeamNG 地图工作流程

这份记录供后续对话直接继续本仓库的道路模型和驾驶场地开发。它记录的是已用过的流程和证据，不代表尚未做过的游戏验证。

## 当前项目位置

- 当前最新为 [V16 路侧布局](../output/mountain_hairpin_road/blender_trial_v16_roadside_layout/README.md)：两弯之间的西北侧加约 10.5 m 护栏；东南侧改为约 3 m 试拟无防护陡坎；上方进弯路段/C1 外侧加净宽 0.5 m、深 0.6 m 排水渠后再接土坡。V15 2.85 m 铺装几何及 C63 直路摆位未变。BeamNG V2 未更新，未来需新护栏碰撞代理并导出沟渠/新地形。

- 上一版宽度试调为 [V15 小路 2.85 m](../output/mountain_hairpin_road/blender_trial_v15_width_285/README.md)。两侧各扩 0.03975 m，路缘土坡与石块同步；C63 保持 C1 弯顶向内借位 0.5 m 的静态位置。原 V14 大路停车版保留。**BeamNG V2 仍为 2.7705 m，未打包本次变化**，导出时需改源文件及小路对象名为 `Road_Surface_Small_Concrete_2p85m`。

- 上一版 Blender 场景入口为 [V14 用户提供的 C63](../output/mountain_hairpin_road/blender_trial_v14_c63_reference/README.md)，上一版为 [V13 A4L](../output/mountain_hairpin_road/blender_trial_v13_a4l_reference/README.md)。V13/V14 仅更换参考车，V12 道路环境与 BeamNG V2 包保持有效；地图导出器继续使用 V12。另有独立车模可用于其他场地。
- 当前最新为 [V12 驾驶练习路缘](../output/mountain_hairpin_road/blender_trial_v12_driving_edges/README.md) 和配套 [BeamNG V2 测试包](../output/mountain_hairpin_road/beamng_hairpin_test_v2/README.md)：灰色路面、上坡侧土坎/裸石碰撞、无防护悬崖路缘。V12/V2 取代下列 V11/V1 作为当前继续开发的入口，旧版保留作比较。
- 所有模型按项目放在 [`output/`](../output/) 下。当前已完成道路项目为 [`mountain_hairpin_road/`](../output/mountain_hairpin_road/)，科目二项目在 [`china_subject2/`](../output/china_subject2/)。
- 已确认发卡弯的 Blender 场景：[`road_trial_v9_flat_main.blend`](../output/mountain_hairpin_road/blender_trial_v9_flat_main/road_trial_v9_flat_main.blend)。
- 上一版 [V11 道路尺寸与设施](../output/mountain_hairpin_road/blender_trial_v11_road_details/README.md) 奠定了 4.5 m 柏油大路、2.7705 m 水泥小路、A4L 尺寸参考车、排水渠和波形钢护栏；继承 [V10 内弯平顺修正](../output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins/README.md) 的两弯约 3° 平均缓降和轻微内倾。当前 V12 保留这些道路参数。
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
- 内弯补角可能跨过原中心线圆弧的圆心。此处不能直接用最近中心线里程或极角计算高程，否则会出现高度跳变和接近竖直的细小路面。V10 改用连续曲面并平顺接回直路；同时改善瘦长三角形连接。轻微内倾不能独自消除过大的弯道纵向落差，需要一起设计接坡。

## 发卡弯项目当前参数与历史区别

这些参数只约束发卡弯项目，不能直接套到科目二地图：

- 用户最新指定大路宽 4.5 m、标高 0，整段水平；无中心线、柏油表面。V9/V10 历史宽度为 4 m。
- 当前 V15 小路标准直段为 2.85 m；此前 V11–V14 按中国 Audi A4L 车身宽 1.847 m 的 1.5 倍，直线名义宽 2.7705 m，水泥表面；V9/V10 为 2.775 m。该宽度来自用户估计，不是实测。弯内补角和入口喇叭口仍保留。
- 参考车按 A4L 长 4.858 m、宽 1.847 m（不含后视镜）、高 1.439 m、轴距 2.908 m，默认置于大路；只是静态尺度参考，不代表已完成车辆通过性仿真。
- V13 用户明确选择“先替换 Blender 参考车，外形像 A4L／A6L、尺寸准确即可”。检索后自行建立简化 A4L，未使用下载网格或贴图。实际几何核对长宽高和轴距；后视镜约 2.068 m 总宽为外观试拟值。不要把它写成官方 CAD、精确曲面或可驾驶 BeamNG 模组。第三方车辆以后若需进入公开仓库，应先记录来源、许可和修改范围。
- V14 用户提供 `98-mercedes-amg-c63.rar`，换为该文件内的 C63 三厢模型。校正为 4.756 × 1.839 × 1.426 m、轴距 2.840 m、含镜宽 2.020 m，仍放大路；**没有按 C63 重新更改小路宽度**。源作者 wishingchain，Free3D 页面为个人使用许可，V14 `.gitignore` 排除源文件和衍生 `.blend`，不要误传到公开仓库。网格有旧轮胎驱动，导入静态道路前冻结评估结果；保留车身/镜壳宽度区别，不能把总宽压成车身宽。尺寸边界已核验，但轮距、胎宽、悬架、转向未做实车物理校准。
- 小路入口约 6 m 渐变到中心线下坡 10°，直路保留约 10°；V10/V11 两弯平均约 3°、弯心内倾约 3%，各 5 m 平顺接坡；末端直线 16 m，中心标高约 -6.073 m。历史 V9 末端约 -8.874 m。
- 两处发卡弯的内夹角按既有确认平面图，内侧圆角半径 1 m；局部补角用于缓和急转。
- 只在大路靠小路侧保留两段直护栏，V11 改为带立柱、螺栓和端头的波形钢护栏。外侧按最新要求改为净宽 0.5 m、深 0.6 m 排水渠，接植被土坡，替代历史无防护深坎。U 形断面、0.12 m 壁底厚和外坡约 1.35 m 高为试拟值，未实测。
- 10° 是直路中心线纵坡，不代表全路各点坡度。V10/V11 已消除内弯过陡折面，但入口仍保留旧版局部横坡；实车是否跳动、蹭底或悬轮尚未检查。
- V11 将大路与小路拆分并新增设施。后续 BeamNG 导出必须更新对象清单、材质和水泥地面物理类型，不能直接复用 V1 导出选择器。细微切缝和草丛是视觉对象，不宜作为独立驾驶障碍。
- V12 用户确认土坡侧石块突出路缘约 20–40 cm、土坎约 10–20 cm。已生成 43 个闭合凸石块，铺装范围不受侵占。悬崖侧压缩原有路肩下降区，路缘外 0.35 m 采样落差中位约 1.71 m，属于建模试拟结果而非实测。道路本体顶点与 V11 完全相同。

## BeamNG 静态地图导出要点

当前执行脚本为 [`beamng_hairpin_test_v2/export_map.py`](../output/mountain_hairpin_road/beamng_hairpin_test_v2/export_map.py)，输入 V12 场景；旧 V1 导出器不兼容新版对象列表。V2 关卡 ID 为 `tight_hairpin_drive_v2`。

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
- V2 将碰撞与细节拆开：路面/土坡约 5 万总碰撞三角面（含岩石、沟渠及护栏代理），43 个石块使用闭合低面数可见网格；护栏用不可见 TSStatic 的简化实心梁柱。草丛、切缝、可见护栏细节和展示剖面墙没有碰撞。隐藏护栏碰撞代理的游戏行为仍需验证。
- 石块闭合与法线正确还不够：V2 独立读回 DAE 后计算石块 XY 凸包与铺装三角形交叠面积，确认没有挤占正常道路；同时按导出地形重新射线采样悬崖高差。不要只在 Blender 查看外观后声称物理碰撞正常。
- V2 的 `HP2_CONCRETE` 是本地图独立干燥硬路面物理基准，摩擦系数尚未实测校准。A4L 静态尺寸模型不随地图导出，也不能代表动态 A4L 的转向、悬架或碰撞。

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
