# 双发卡弯道路项目

此目录保存用户已确认的道路方案、最终 Blender 场景、断面图纸和 BeamNG 测试包。详细协作约定见仓库根目录 [`AGENTS.md`](../../AGENTS.md)；Blender 与 BeamNG 操作记录见 [`docs/BLENDER_BEAMNG_WORKFLOW.md`](../../docs/BLENDER_BEAMNG_WORKFLOW.md)。

## 成果

- 2026-10-15 最新追加填充版：[`../connected_maps_v4_innerfill_more/`](../connected_maps_v4_innerfill_more/)，两个内弯比 V3 各再补 0.6 m，最深处累计 1.8 m；C1 护栏末端收短一跨以让出新增路面。已热加载、截图及碰撞射线检查，本次未进行完整转弯驾驶验证。V3 保留，详见该目录 `使用说明.txt`。

- 2026-10-15 内弯补宽更新：[`../connected_maps_v3_innerfill/`](../connected_maps_v3_innerfill/)，两个发卡弯内侧各补入约 1.2 m、增加约 2.4 m² 铺装，局部坡面衔接，裁去新路面下方旧土体干涉。大路 6.5 m / 小路直段 3.9 m 保留。实际测试范围及恢复步骤见该目录 `使用说明.txt`，未宣称完成两处整弯的车辆通过性验证。

- 2026-10-15 当前游戏派生版：[`../connected_maps_v2_width130/`](../connected_maps_v2_width130/)，家乡大路净宽 **6.5 m**、小路标准直段 **3.9 m**，均比上一版增加 30%；保留与科目二、Gridmap V2 的连通和原游戏混凝土纹理。此版直接调整游戏 DAE，原 V20 Blender 和 BeamNG V3 ZIP 保留。检查记录及恢复步骤见该目录 `使用说明.txt`。

- [`beamng_hairpin_test_v3/`](beamng_hairpin_test_v3/)：当前 BeamNG 导入包，对应 V20，含 5 m/3 m 道路、最新沟渠/填平路肩、收短小路护栏碰撞和悬崖地形。修复旧隐藏主路碰撞体导出位置，已离线读回检查，未在 Windows 游戏内验证。

- [`blender_trial_v20_main5m_drain_setback/`](blender_trial_v20_main5m_drain_setback/)：当前模型，大路净铺装 5 m；小路 3 m 不变，上方渠退至 C1 入弯前 2 m，下方渠退至 C2 出弯后 4 m，撤去沟渠处填平接土坡。附大路双车、整体和排水渠俯视图。已同步至 BeamNG V3。

- [`blender_trial_v19_width_3m/`](blender_trial_v19_width_3m/)：上一版，小路加宽至 3 m，路侧设施同步外移；核实大路铺装净宽 4.5 m、不含排水渠，新增双 C63 俯视比例图。BeamNG 包未同步。

- [`blender_trial_v18_short_guardrail/`](blender_trial_v18_short_guardrail/)：上一版，C1 出弯端护栏收回 3.5 m，保留约 7 m 和 5 根立柱，端板同步收回。其余 V17 模型与车辆摆位保持。

- [`blender_trial_v17_lower_drain/`](blender_trial_v17_lower_drain/)：上一版，在用户箭头所指的 C2 出弯后下方直路土坡侧追加净宽 0.5 m、深 0.6 m 排水渠，石块移到渠外；保留 V16 其他布局。

- [`blender_trial_v16_roadside_layout/`](blender_trial_v16_roadside_layout/)：上一版路侧调整，按用户 1/2/3 标注添加小路护栏、无防护陡坎及排水渠；小路仍宽 2.85 m，C63 保持直段中央。新增斜俯视和俯视预览，BeamNG 包尚未同步。

- [`c63_straight_preview_285/`](c63_straight_preview_285/)：用户确认的 C63 直段居中俯视图，道路沿用 V15 的 2.85 m 宽度。

- [`blender_trial_v15_width_285/`](blender_trial_v15_width_285/)：上一版宽度试调，小路直段加宽至 2.85 m，两弯补角及入口渐变保留，土坡/石块随路缘调整。C63 保持 C1 弯顶摆位，附同角度俯视图。BeamNG V2 尚未更新此宽度。

- [`blender_trial_v14_c63_reference/`](blender_trial_v14_c63_reference/)：上一版 Blender 场景，换用用户提供的 Mercedes-AMG C63 车模，按 W205 三厢车型校正长宽高、含镜宽度及轴距，仍停在大路；保留全部道路环境。素材为个人使用许可，原始和衍生车模 `.blend` 仅本地保存。
- [`blender_trial_v13_a4l_reference/`](blender_trial_v13_a4l_reference/)：上一版参考车，原尺寸方块车替换为自行制作的 A4L 简化外观参考车，增加四环中网、灯组、轮拱、车窗、门把手及后视镜。仍停在大路上；另有可复用独立车模。保留 V12 全部道路环境，不是可驾驶车辆。
- [`blender_trial_v12_driving_edges/`](blender_trial_v12_driving_edges/)：当前道路环境基线，水泥调暗、柏油调浅；按用户确认的 20–40 cm 石块、10–20 cm 土坎在土坡侧建立驾驶障碍，悬崖侧收窄路肩并保留无防护陡降。路面形状和高程未变。
- [`beamng_hairpin_test_v2/`](beamng_hairpin_test_v2/)：对应 V12 的新版完整驾驶测试包，含石块/土坎/路缘碰撞、独立简化护栏碰撞和路面物理配置；已离线检查，未在 Windows 游戏内验证。

- [`blender_trial_v11_road_details/`](blender_trial_v11_road_details/)：当前最新细化版，A4L 尺寸参考车放在大路上；大路改为 4.5 m 无中心线柏油路，小路约 2.77 m 水泥路；新增净宽 0.5 m、深 0.6 m 排水渠、外侧植被土坡及波形钢护栏。保留 V10 两弯平顺高程，待查看外观与试拟设施细节。

- [`blender_trial_v10_smooth_hairpins/`](blender_trial_v10_smooth_hairpins/)：最新试调，修正两处内弯陡折面、平顺接坡并加入轻微内倾；待用户看图确认，尚未生成对应 BeamNG 包。末端随降坡调整抬高约 2.8 m。

- [`road_plan_v5_tight35/`](road_plan_v5_tight35/)：已确认的 35° 发卡内夹角俯视图与可编辑源文件。
- [`road_sections_v1/`](road_sections_v1/)：道路定位图、纵断面、三张横断面及完整图纸 ZIP。
- [`blender_trial_v9_flat_main/`](blender_trial_v9_flat_main/)：最终 Blender 场景 V9，含水平大路、10° 小路中心线坡度、护栏与内弯调整。
- [`beamng_hairpin_test_v1/`](beamng_hairpin_test_v1/)：BeamNG 测试 ZIP、Windows 安装说明、预览、DAE 导出与离线检查脚本。

## 当前限制

BeamNG ZIP V3 对应 V20；V2 对应 V12–V14 相同的道路环境，V13/V14 只替换不导出的参考车；旧 V1 仍对应 V9。二者均未在 BeamNG.drive 实际加载和驾驶验证。新版完成离线格式、网格、石块碰撞与铺装净空、路缘落差检查；车辆是否跳动、蹭底、撞石或坠落，仍需在 Windows 游戏内确认。Blender A4L/C63 均仅是静态外观与尺寸参考车。
