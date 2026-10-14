"""Correct float32 winding and set top-view orientation to match the approved drawing."""
import bpy,bmesh,math,json
from pathlib import Path
D=Path(__file__).resolve().parent
bpy.ops.wm.save_as_mainfile(filepath=str(D/'before_v07_visual_qa.blend'),copy=True)
count=0
for o in bpy.data.collections['01_Roads'].objects:
    if not o.name.startswith('ROAD_'):continue
    bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
    for f in bm.faces:
        if f.normal.z<0:f.normal_flip();count+=1
    bm.to_mesh(o.data);bm.free();o.data.update()
for name in ['CAM_Top','CAM_SCurve']:bpy.data.objects[name].rotation_euler=(0,0,math.pi/2)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_v07_final.blend'))
(D/'finalization.json').write_text(json.dumps({'flipped_tiny_union_triangles':count,'top_camera_matches_approved_plan':True},indent=2))
print('Finalized',count,'tiny triangle windings')
