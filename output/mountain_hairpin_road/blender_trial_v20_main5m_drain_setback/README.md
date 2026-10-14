# V20：大路 5 米，小路排水渠退离发卡弯

按用户要求，大路净柏油铺装从 4.5 m 加宽到 5.0 m，不包含排水渠。靠小路的边缘保持 Y=42 m，另一侧扩至 Y=47 m，外侧排水渠及土坡整体外移 0.5 m。大路仍水平，无中心线。小路保持 3 m，路面形状、高程、原 C63 摆位及 V18 收短后的护栏不变。

小路排水渠试拟退让距离：上方渠在 C1 入弯前 2 m 结束，取消沿 C1 外侧绕弯的沟渠；下方渠从 C2 出弯后 4 m 开始，较 V19 再后退 2 m。撤去部分填为与原渠两侧顶面齐平的土质路肩，衔接外侧土坡；新的沟渠端头补土封口。保留的沟渠仍为净宽 0.5 m、深 0.6 m。上述退让距离为本轮试拟值，待用户看图确认。

## 文件

- `road_trial_v20_main5m_drain_setback.blend`：完整模型。
- `main_road_5m_two_cars.png`：大路两辆真实尺寸 C63 反向并排。
- `overview.png`：道路整体斜俯视。
- `drain_setbacks_top.png`：排水渠退让后的俯视。
- `adjust_width_and_drains.py`：以 V19 为输入的修改脚本。
- `validation_report.json`：大路净宽与水平高程、小路和护栏未改、沟渠宽深和射线检查结果。

两辆车身宽 1.839 m 的 C63 占用后，5 m 大路总余量 1.322 m；按含镜 2.020 m 算，总余量 0.960 m。图中含镜车间距 0.48 m，两侧各 0.24 m。仅为静态比例展示，没有做动态会车验证。双车集合 `REFERENCE_Main_Road_Meeting_Preview` 默认隐藏，切换到 `Camera_V20_Main_Meeting_Top` 并开启集合可查看。

本地场景含个人使用许可的 C63 衍生网格，`.blend` 不上传公开仓库。已导出为 [BeamNG V3](../beamng_hairpin_test_v3/README.md)，经过离线读回检查，未在 Windows 游戏验证。后续从 V20 导出，主路对象名改为 `Road_Surface_Main_Asphalt_5m`，小路为 `Road_Surface_Small_Concrete_3m`，更新沟渠、填土及碰撞对象，并排除所有参考车辆。
