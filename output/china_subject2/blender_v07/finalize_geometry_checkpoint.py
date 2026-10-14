"""Apply the same numerical normals and camera corrections to the base checkpoint."""
import bpy
import bmesh
import math
import json
from pathlib import Path

D = Path(__file__).resolve().parent
path = D / 'china_subject2_v07_geometry.blend'
bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
backup = D / 'before_v07_geometry_qa.blend'
if not backup.exists():
    bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
count = 0
for obj in bpy.data.collections['01_Roads'].objects:
    if not obj.name.startswith('ROAD_'):
        continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    for face in bm.faces:
        if face.normal.z < 0:
            face.normal_flip()
            count += 1
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
for name in ('CAM_Top', 'CAM_SCurve'):
    bpy.data.objects[name].rotation_euler = (0, 0, math.pi / 2)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(path))
bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
negative = sum(p.normal.z < 0 for o in bpy.data.collections['01_Roads'].objects
               if o.name.startswith('ROAD_') for p in o.data.polygons)
assert negative == 0, negative
assert abs(bpy.data.objects['CAM_Top'].rotation_euler.z - math.pi / 2) < 1e-6
(D / 'geometry_checkpoint_qa.json').write_text(json.dumps({
    'flipped_tiny_union_triangles': count,
    'reopened_checkpoint_negative_road_normals': negative,
    'top_camera_matches_approved_plan': True,
    'passed': True,
}, indent=2) + '\n')
print('Base checkpoint corrected, saved and reopened:', count, 'tiny windings')
