"""Render saved V07 without changing the delivered blend."""
import bpy,os,json
from pathlib import Path
D=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(D/'china_subject2_v07_final.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=int(os.environ.get('C1_SAMPLES','32'));s.cycles.use_denoising=True
s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.035
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    s.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
    print('DEVICES',[(d.name,d.type,d.use) for d in prefs.devices],flush=True)
except Exception as e:print('CPU fallback',e,flush=True);s.cycles.device='CPU'
for o in bpy.data.collections['05_ReferenceCar_HIGH'].all_objects:o.hide_set(False)
bpy.data.collections['06_ReferenceCar_PROXY'].hide_render=True
bpy.context.view_layer.update()
manifest=json.loads((D/'build_manifest.json').read_text());cams=manifest['previews']
keys=os.environ.get('C1_VIEWS',','.join(cams)).split(',');out=D/'previews';out.mkdir(exist_ok=True)
for key in keys:
    s.camera=bpy.data.objects[cams[key]]
    if key=='02_top':s.render.resolution_x=1500;s.render.resolution_y=2100
    else:s.render.resolution_x=1800;s.render.resolution_y=1350
    s.render.resolution_percentage=100;s.render.filepath=str(out/(key+'.png'))
    bpy.ops.render.render(write_still=True);print('RENDERED',key,flush=True)
