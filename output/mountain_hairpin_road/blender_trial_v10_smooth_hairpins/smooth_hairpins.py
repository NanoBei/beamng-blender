"""Run in an independent Blender process with the V9 scene already loaded."""
import bpy, bmesh, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from road_profile import corrected_heights,mesh_stats,profile,old_profile,curves,LENGTH,BANK,TRANSITION
scene=bpy.context.scene
road=bpy.data.objects['Road_Surface_4m_and_2.775m']
terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
original=np.array([list(v.co) for v in road.data.vertices])
original_faces=np.array([list(p.vertices) for p in road.data.polygons])
original_bvh=BVHTree.FromPolygons([v.co.copy() for v in road.data.vertices],original_faces.tolist(),all_triangles=True)
new_z=corrected_heights(original[:,:2],original[:,2])
delta=new_z-original[:,2]

scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1250;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'

def camera(name,position,target,scale):
    ob=bpy.data.objects.get(name)
    if ob is None:
        ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(ob)
    ob.location=position;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    ob.data.type='ORTHO';ob.data.ortho_scale=scale
    return ob

cams=[]
for i,arc in enumerate(curves):
    centre=arc['c']; z=float((profile(arc['s']+arc['length']/2)+old_profile(arc['s']+arc['length']/2))/2)
    offset=(8,-10,8) if i==0 else (-9,-7,8)
    target=(centre[0],centre[1],z)
    cams.append(camera(f'Camera_V10_Inner_C{i+1}',tuple(np.array(target)+offset),target,11))
scene.camera=cams[0];scene.render.filepath=str(OUT/'c1_before.png');bpy.ops.render.render(write_still=True)

# Improve poorly shaped triangles in the existing plan, without moving/deleting vertices.
bm=bmesh.new();bm.from_mesh(road.data);bm.verts.ensure_lookup_table()
for v in bm.verts:v.co.z=0
bmesh.ops.beautify_fill(bm,faces=list(bm.faces),edges=list(bm.edges))
for v in bm.verts:v.co.z=float(new_z[v.index])
bm.to_mesh(road.data);bm.free();road.data.update()
for p in road.data.polygons:p.use_smooth=True
assert np.array_equal(np.array([list(v.co)[:2] for v in road.data.vertices]),original[:,:2])

# Lift adjacent earth with a smooth weighted interpolation, preserving shared boundaries.
kd=KDTree(len(original))
for i,p in enumerate(original):kd.insert(Vector((p[0],p[1],0)),i)
kd.balance()
old_terrain=np.array([list(v.co) for v in terrain.data.vertices])
shared_errors=[]
for v in terrain.data.vertices:
    if v.co.y>=42-1e-6: continue
    neighbours=kd.find_n(Vector((v.co.x,v.co.y,0)),12)
    nearest=neighbours[0]
    if nearest[2]<1e-4:
        v.co.z=float(new_z[nearest[1]])
        shared_errors.append(abs(v.co.z-new_z[nearest[1]]))
    else:
        distances=np.array([row[2] for row in neighbours]); indices=np.array([row[1] for row in neighbours])
        weights=1/np.maximum(distances,.01)**3
        lift=float(weights@delta[indices]/weights.sum())*math.exp(-(distances[0]/6)**2)
        v.co.z+=lift
terrain.data.update()
tkd=KDTree(len(terrain.data.vertices))
for v in terrain.data.vertices:tkd.insert(Vector((v.co.x,v.co.y,0)),v.index)
tkd.balance()
for v in bpy.data.objects['Terrain_Block_Sides'].data.vertices:
    if v.co.z>-24.9:
        _,i,d=tkd.find(Vector((v.co.x,v.co.y,0)))
        if d<1e-3:v.co.z=terrain.data.vertices[i].co.z

new_bvh=BVHTree.FromPolygons([v.co.copy() for v in road.data.vertices],[list(p.vertices) for p in road.data.polygons],all_triangles=True)
car=bpy.data.objects.get('Sedan_Size_Reference_5.006x1.850')
if car:
    origin=Vector((car.location.x,car.location.y,20))
    old_hit=original_bvh.ray_cast(origin,Vector((0,0,-1)),60)[0]
    new_hit=new_bvh.ray_cast(origin,Vector((0,0,-1)),60)[0]
    if old_hit and new_hit:car.location.z+=new_hit.z-old_hit.z
for ob in bpy.data.collections.get('GUIDES_Profile_Points').objects:
    s=ob.get('station_m')
    if s is not None:ob.location.z=float(profile(s));ob['elevation_m']=float(profile(s))

road['hairpin_mean_longitudinal_angle_deg']=3.
road['hairpin_apex_inward_crossfall_percent']=3.
road['hairpin_transition_length_m']=TRANSITION
road['longitudinal_angle_deg']=10.
road['longitudinal_angle_note']='10 deg on straight sections; 3 deg average on each hairpin; 5 m approach transitions'
road['end_z']=float(profile(LENGTH))
road['surface_revision']='V10 smooth filled inner corners and gentle inward bank'

updated=np.array([list(v.co) for v in road.data.vertices]); faces=np.array([list(p.vertices) for p in road.data.polygons])
report={'source_scene':'V9 live scene snapshot','plan_vertices_unchanged':True,
        'main_road_max_height_error_m':float(np.max(np.abs(updated[updated[:,1]>=42-1e-6,2]))),
        'road_before':mesh_stats(original,original_faces),'road_after':mesh_stats(updated,faces),
        'hairpin_mean_grade_deg':3,'inward_crossfall_at_apex_percent':3,'approach_transition_m':TRANSITION,
        'end_z_before_m':float(old_profile(LENGTH)),'end_z_after_m':float(profile(LENGTH)),
        'shared_road_terrain_vertices':len(shared_errors),'max_shared_boundary_height_error_m':float(max(shared_errors)),
        'beamng_runtime_tested':False,'status':'model preview pending user review'}
tri=updated[faces]; centres=tri.mean(1)
for i,arc in enumerate(curves):
    mask=np.linalg.norm(centres[:,:2]-arc['c'],axis=1)<3.5
    report[f'curve_{i+1}']=mesh_stats(updated,faces[mask])
assert report['main_road_max_height_error_m']==0
assert report['road_after']['faces_over_30deg']==0
assert all(report[f'curve_{i+1}']['max_face_slope_deg']<12 for i in range(2)),report
assert report['max_shared_boundary_height_error_m']<1e-5
(OUT/'surface_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)

notes=bpy.data.texts.get('V10_Surface_Notes') or bpy.data.texts.new('V10_Surface_Notes')
notes.clear();notes.write('V10 试调：两处发卡内弯补角改为连续曲面。弯道平均纵坡约3度，弯心内倾约3%，两端各5米渐变接回10度直路。大路仍水平，XY平面、道路边界不变。末端中心标高约-6.073米，原版-8.874米。尚未BeamNG实测。\n')
for i,cam in enumerate(cams):
    scene.camera=cam;scene.render.filepath=str(OUT/f'c{i+1}_after.png');bpy.ops.render.render(write_still=True)
overview=camera('Camera_V10_Overview',(40,5,22),(23,31,-3.5),36)
scene.camera=overview;scene.render.filepath=str(OUT/'hairpins_overview.png');bpy.ops.render.render(write_still=True)
scene.camera=cams[0]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v10_smooth_hairpins.blend'))
print('V10 SAVED',flush=True)
