import bpy,json,hashlib,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments
scene=bpy.context.scene;mid=segments[2]
def state(o):
    p=np.empty((len(o.data.vertices),3),dtype=np.float32);o.data.vertices.foreach_get('co',p.ravel())
    return hashlib.sha256(p.tobytes()+repr(list(map(list,o.matrix_world))).encode()).hexdigest()
protected={o.name:state(o) for o in scene.objects if o.type=='MESH' and not o.name.startswith(('V16_Small_Rail','V16_Small_WBeam','C63'))}
car=bpy.data.objects['REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm'];pose=car.matrix_world.copy()
first=bpy.data.objects['V16_Small_Rail_Post_1'];third=bpy.data.objects['V16_Small_Rail_Post_3']
shift=third.location-first.location
caps=[o for o in scene.objects if o.name.startswith('V16_Small_Rail_End')]
cap=min(caps,key=lambda o:(o.location-first.location).length)
old_end=list(cap.location);cap.location+=shift
remove_names=['V16_Small_WBeam_1','V16_Small_WBeam_2','V16_Small_Rail_Post_1','V16_Small_Rail_Post_2','V16_Small_Rail_Spacer_1','V16_Small_Rail_Spacer_2']
for o in scene.objects:
    if o.name.startswith('V16_Small_Rail_Bolt'):
        along=float((np.array(o.location[:2])-mid['start'])@mid['t'])
        if along<4.0:remove_names.append(o.name)
for name in remove_names:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
assert all(state(bpy.data.objects[name])==value for name,value in protected.items())
assert car.matrix_world==pose
posts=[o for o in scene.objects if o.name.startswith('V16_Small_Rail_Post')]
assert len(posts)==5
assert len([o for o in scene.objects if o.name.startswith('V16_Small_WBeam')])==4
report={'source':'V17','shortened_at':'C1 upper-hairpin end only','retreated_length_m':3.5,'previous_guardrail_length_m':10.5,'new_guardrail_length_m':7.0,'new_start_after_C1_m':4.25,'old_cap_position':old_end,'new_cap_position':list(cap.location),'remaining_posts':len(posts),'removed_objects':remove_names,'other_mesh_objects_unchanged':len(protected),'car_pose_unchanged':True,'beamng_updated':False,'turning_path_verified':False}
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2))
# Detail uses the same general view direction as the previous overview.
cam=bpy.data.objects.new('Camera_V18_Guardrail_Clearance',bpy.data.cameras.new('Camera_V18_Guardrail_Clearance'));scene.collection.objects.link(cam)
cam.location=(8,9,23);target=Vector((26.5,33.6,-2));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=16.5
scene.render.image_settings.file_format='PNG';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.camera=cam;scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.filepath=str(OUT/'guardrail_detail.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v18_short_guardrail.blend'))
bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.filepath=str(OUT/'overview.png');bpy.ops.render.render(write_still=True)
scene.camera=cam;scene.render.resolution_x=1500;scene.render.resolution_y=1100
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v18_short_guardrail.blend'))
print(json.dumps(report,indent=2))
