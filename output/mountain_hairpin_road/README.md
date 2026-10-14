# 双发卡弯道路项目

此目录保存用户已确认的道路方案、最终 Blender 场景、断面图纸和 BeamNG 测试包。详细协作约定见仓库根目录 [`AGENTS.md`](../../AGENTS.md)；Blender 与 BeamNG 操作记录见 [`docs/BLENDER_BEAMNG_WORKFLOW.md`](../../docs/BLENDER_BEAMNG_WORKFLOW.md)。

## 成果

- [`road_plan_v5_tight35/`](road_plan_v5_tight35/)：已确认的 35° 发卡内夹角俯视图与可编辑源文件。
- [`road_sections_v1/`](road_sections_v1/)：道路定位图、纵断面、三张横断面及完整图纸 ZIP。
- [`blender_trial_v9_flat_main/`](blender_trial_v9_flat_main/)：最终 Blender 场景 V9，含水平大路、10° 小路中心线坡度、护栏与内弯调整。
- [`beamng_hairpin_test_v1/`](beamng_hairpin_test_v1/)：BeamNG 测试 ZIP、Windows 安装说明、预览、DAE 导出与离线检查脚本。

## 当前限制

BeamNG ZIP 已完成离线文件和网格检查，但尚未在 BeamNG.drive 实际加载和驾驶验证。发卡内弯的局部路面比中心线纵坡更陡；车辆是否跳动、蹭底或悬轮仍需在 Windows 游戏内确认。
