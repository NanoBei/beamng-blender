"""Run in a disposable Blender process after opening the saved V13 scene."""
import bpy
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
scene=bpy.context.scene
ref=bpy.data.collections['REFERENCE_Audi_A4L_EXCLUDE_FROM_MAP']
root=next(o for o in ref.objects if o.type=='EMPTY')
cam=bpy.data.objects['Camera_V13_A4L_Front']
offset=root.location.copy();root.location=(0,0,0);cam.location-=offset
keep=set(ref.objects)|{cam}|{o for o in scene.objects if o.type=='LIGHT'}
for o in list(bpy.data.objects):
    if o not in keep:bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):
    if c!=ref and not c.all_objects:bpy.data.collections.remove(c)
scene.name='Audi_A4L_Reference_Only';scene.camera=cam
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
root['mirror_width_trial_m']=2.06769
# Give the retained key light an appropriate position relative to the car.
for o in scene.objects:
    if o.type=='LIGHT' and o.data.type!='SUN':o.location-=offset
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=(0,0,.7)
        area.spaces.active.region_3d.view_distance=7
bpy.data.orphans_purge(do_recursive=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'audi_a4l_reference_asset.blend'))
