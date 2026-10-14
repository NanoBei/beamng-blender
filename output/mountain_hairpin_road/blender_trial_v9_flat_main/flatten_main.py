import bpy,bmesh,math,json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
out=Path('/Users/macmini/work/active/beamng-blender/output/blender_trial_v9_flat_main')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'before_flattening.blend'),copy=True)
road=bpy.data.objects['Road_Surface_4m_and_2.775m'];terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
# Cut the junction at the exact edge of the main road so no tilted triangle crosses it.
for ob in (road,terrain):
 bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Vector((0,42,0)),plane_no=Vector((0,1,0)),clear_inner=False,clear_outer=False)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
# Reuse the established alignment only, without executing the scene builder.
src=Path('/Users/macmini/work/active/beamng-blender/output/blender_trial_v6_10deg/build_trial.py').read_text()
exec(src[src.index('segs=[];'):src.index('breaks=np.array')])
exec(src[src.index('def nearest(P):'):src.index('def field(P):')])
g=math.tan(math.radians(10));s0=2/math.sin(math.radians(25));ramp=6.
def profile(s):
 t=np.maximum(np.asarray(s)-s0,0)
 return -g*np.where(t<ramp,t*t/(2*ramp),t-ramp/2)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
P=np.array([(v.co.x,v.co.y) for v in road.data.vertices]);oldz=np.array([v.co.z for v in road.data.vertices]);_,ss,_=nearest(P)
z=oldz+profile(ss)+g*ss
# Across the oblique mouth, blend the edge elevations down from the horizontal main road.
z=np.where(P[:,1]>=42-1e-6,0,z*smooth((42-P[:,1])/1.5))
deltas=z-oldz
for v,zz in zip(road.data.vertices,z):v.co.z=float(zz)
road.data.update()
assert max(abs(v.co.z) for v in road.data.vertices if v.co.y>=42-1e-6)<1e-7
kd=KDTree(len(P))
for i,q in enumerate(P):kd.insert(Vector((float(q[0]),float(q[1]),0)),i)
kd.balance()
# Shared boundary vertices receive exactly the same uplift; nearby soil blends outward.
for v in terrain.data.vertices:
 if v.co.y>=46-1e-6:continue
 _,idx,dist=kd.find(Vector((v.co.x,v.co.y,0)))
 v.co.z+=float(deltas[idx])*math.exp(-(dist/8)**2)
terrain.data.update()
terrain_kd=KDTree(len(terrain.data.vertices))
for v in terrain.data.vertices:terrain_kd.insert(Vector((v.co.x,v.co.y,0)),v.index)
terrain_kd.balance()
wall=bpy.data.objects['Terrain_Block_Sides']
for v in wall.data.vertices:
 if v.co.z>-24.9:
  _,i,dist=terrain_kd.find(Vector((v.co.x,v.co.y,0)))
  if dist<1e-3:v.co.z=terrain.data.vertices[i].co.z
wall.data.update()
# Keep straight rails, resizing their posts to meet the updated verge.
bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
for ob in bpy.data.objects:
 if ob.name.startswith(('Rail_Post_1_','Rail_Post_2_')):
  hit=bvh.ray_cast(Vector((ob.location.x,ob.location.y,100)),Vector((0,0,-1)),200)[0]
  assert hit is not None
  bottom=hit.z-.12;top=.8;length=top-bottom;assert length>0
  lo=min(v.co.z for v in ob.data.vertices);hi=max(v.co.z for v in ob.data.vertices)
  for v in ob.data.vertices:v.co.z=((v.co.z-lo)/(hi-lo)-.5)*length
  ob.location.z=(top+bottom)/2;ob.data.update()
car=bpy.data.objects['Sedan_Size_Reference_5.006x1.850'];car.location.z+=float(profile(31.8)+g*31.8)
for ob in bpy.data.collections['GUIDES_Profile_Points'].objects:
 s=ob.get('station_m')
 if s is not None:ob.location.z=float(profile(s));ob['elevation_m']=float(profile(s))
road['main_road_elevation_m']=0.;road['main_road_is_flat']=True;road['downhill_start_station_m']=s0;road['entry_transition_length_m']=ramp;road['end_z']=float(profile(L))
# Inspect actual geometry, including triangle edges crossing the junction.
mainfaces=[f for f in road.data.polygons if all(road.data.vertices[i].co.y>=42-1e-6 for i in f.vertices)]
assert all(max(abs(road.data.vertices[i].co.z) for i in f.vertices)<1e-7 for f in mainfaces)
rbvh=BVHTree.FromPolygons([v.co for v in road.data.vertices],[list(f.vertices) for f in road.data.polygons],all_triangles=True)
main_error=0
for x in np.linspace(.1,43.9,90):
 for y in np.linspace(42.001,45.999,9):
  hit=rbvh.ray_cast(Vector((float(x),float(y),100)),Vector((0,0,-1)),200)[0];assert hit is not None
  main_error=max(main_error,abs(hit.z))
assert main_error<1e-4,main_error
scene=bpy.context.scene;cam=bpy.data.objects.get('Camera_Flat_Main')
if cam is None:
 data=bpy.data.cameras.new('Camera_Flat_Main');cam=bpy.data.objects.new('Camera_Flat_Main',data);scene.collection.objects.link(cam)
cam.location=(41,20,21);cam.rotation_euler=(Vector((22,42,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=50;scene.camera=cam
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.region_3d.view_camera_zoom=20
note=bpy.data.texts.get('READ_ME_模型说明')
if note:note.write('\nV9：整条大路（y=42至46）严格水平，标高0。小路从大路边缘起坡，入口约6米沿中心线逐渐过渡至10度；之后保持10度。替代此前从大路中线立即下坡的高程方式。\n')
report={'main_road_z_m':0,'main_mesh_height_error_m':main_error,'downhill_start_station_m':s0,'entry_transition_length_m':ramp,'downstream_angle_deg':10,'end_z_m':float(profile(L)),'outer_drop_m':3,'inner_radius_m':1.0}
(out/'flat_main_validation.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'road_trial_v9_flat_main.blend'))
print(json.dumps(report))
