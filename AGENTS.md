# 仓库协作约定

开始新的道路或驾驶场地任务前，先读：

- [`docs/BLENDER_BEAMNG_WORKFLOW.md`](docs/BLENDER_BEAMNG_WORKFLOW.md)：建模、文件管理、导出、BeamNG 打包和已知限制。
- [`output/mountain_hairpin_road/README.md`](output/mountain_hairpin_road/README.md)：已完成发卡弯项目的成果索引与模型参数。
- [`output/china_subject2/README.md`](output/china_subject2/README.md)：科目二项目当前状态和待确认信息。

约定：

- 与用户用中文沟通；把用户明确确认的尺寸和造型作为约束，不自行改回旧方案。
- 每个模型放在 `output/<项目名>/` 下。不要清理、覆盖其他项目或未确认的原始素材。
- 以米为单位、Z 轴朝上；改动 Blender 场景前另存版本，保留上一版便于回退。
- 将展示用相机、灯光、参考车和地板与游戏碰撞/渲染对象分开；导出前检查对象清单和材质。
- 声称“可导入”只表示完成了文件准备。只有目标 BeamNG 版本实际加载、重载并驾驶检查后，才可说游戏内验证通过。
- 如要宣称符合现行中国驾考标准，先核实用户所在地区和标准来源；不得把示意尺寸当作官方规范。
