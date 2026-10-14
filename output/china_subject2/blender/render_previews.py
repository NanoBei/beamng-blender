"""Render saved scenes independently; never alters delivered .blend files."""
import bpy, os, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
filename=os.environ.get('C1_RENDER_FILE','china_subject2_v03_final.blend')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender'/filename))
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=int(os.environ.get('C1_SAMPLES','32'));s.cycles.use_denoising=True
s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.04
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='METAL';prefs.get_devices()
    gpu=False
    for d in prefs.devices:
        d.use=d.type=='METAL';gpu|=d.use
    s.cycles.device='GPU' if gpu else 'CPU'
    print('DEVICES',[(d.name,d.type,d.use) for d in prefs.devices],flush=True)
except Exception as e: print('CPU fallback',str(e),flush=True);s.cycles.device='CPU'
# High mesh is hidden only in the viewport; explicitly enable it for render evaluation.
if '05_ReferenceCar_HIGH' in bpy.data.collections:
    for o in bpy.data.collections['05_ReferenceCar_HIGH'].all_objects:o.hide_set(False)
if '06_ReferenceCar_PROXY' in bpy.data.collections:bpy.data.collections['06_ReferenceCar_PROXY'].hide_render=True
cams={'01_overview':'CAM_Overview','02_top':'CAM_Top','03_reverse':'CAM_Reverse','04_parallel':'CAM_Parallel','05_hill':'CAM_Hill','06_s_curve':'CAM_SCurve','07_right_angle':'CAM_RightAngle'}
keys=os.environ.get('C1_VIEWS',','.join(cams)).split(',')
width=int(os.environ.get('C1_WIDTH','1600'));s.render.resolution_x=width;s.render.resolution_y=round(width*.75);s.render.resolution_percentage=100
prefix=os.environ.get('C1_PREFIX','')
for key in keys:
    s.camera=bpy.data.objects[cams[key]]
    # True overhead orientation: screen up = world +Y.
    if key=='02_top':s.camera.rotation_euler=(0,0,0)
    s.render.filepath=str(ROOT/'previews'/(prefix+key+'.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED',key,flush=True)
