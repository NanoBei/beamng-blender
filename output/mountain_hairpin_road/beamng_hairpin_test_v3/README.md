# 家乡双发卡弯 BeamNG 驾驶测试包 V3

对应最新 Blender V20：大路净柏油路面 5 m，小路水泥路面 3 m；主路水平，小路直段约 10°、两弯平均约 3°并轻微内倾。上方渠在 C1 入弯前 2 m 结束，下方渠从 C2 出弯后 4 m 开始；两条小路渠均净宽 0.5 m、深 0.6 m，撤掉渠段已填平。

## 下载与安装

- [地图 ZIP](tight_hairpin_drive_v3.zip)
- [Windows 导入与试车说明](Windows导入与试车说明.txt)
- [独立读回检查](validation_report.json)
- [导出对象记录](export_report.json)

将 ZIP 复制到 Windows，不解压，放入 BeamNG 启动器打开的用户目录 `mods` 文件夹。在 Freeroam 搜索 **Hometown Hairpin Drive V3**，选择 Main Road 出生点。建议停用 V1/V2，避免选错地图。

## 导出范围与碰撞

10 个 DAE 资产：大路、小路、地形/新增土坡/填平路肩、全部排水渠、裸石、护栏外观、护栏简化碰撞、植被、水泥切缝及地块展示侧墙。驾驶碰撞覆盖前六项中的道路、地形、沟渠、石块与简化梁柱；草丛、切缝和展示侧墙无碰撞。小路收短后的 7 m 护栏另建 4 根实心梁、5 根立柱的闭合碰撞代理。

本版修复旧隐藏主路护栏代理在后台导出时世界矩阵未更新的问题；导出前显示代理并更新场景，读回检查其位置在实际护栏处。源 V20 场景保持本地，导出过程不覆盖源模型。

C63/A4L 等参考车辆、灯光、相机、展示底板均不进入地图包。用户提供的 C63 仅按个人使用许可保留于本地 Blender 文件；本 ZIP 不提供可驾驶车辆。可以使用游戏自带或已安装的车辆模组试车。

## 验证与限制

使用独立 Collada 解析器读回 DAE，核对米制/Z-up、材质与贴图路径、三角面/法线、净铺装宽度、出生点支撑、24 个裸石闭合及铺装净空、护栏代理闭合与位置、沟渠落轮空间、填平路肩以及悬崖落差；检查 ZIP 目录及完整性。两张 2048×2048 颜色贴图由本地道路/地形材质烘焙。

**尚未在 Windows BeamNG 内加载、重载和驾驶验证。** 离线检查通过表示文件准备完成，动态会车、发卡弯通过性和轮胎/悬架表现仍需游戏实测。干燥水泥摩擦为试拟基准。

导出脚本为 `export_map.py`，输入 `blender_trial_v20_main5m_drain_setback/road_trial_v20_main5m_drain_setback.blend`；`validate_package.py` 可检查临时 `package/` 或解压现成 ZIP。`package/` 为忽略的临时输出，提交 ZIP、预览和报告即可。

2026-10-14 核对的官方说明：[DAE 资产与碰撞流程](https://documentation.beamng.com/modding/levels/level_creation/section11/)、[TSStatic 碰撞配置](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/)、[逐行关卡对象文件](https://documentation.beamng.com/modding/levels/level_formats/items/)。
