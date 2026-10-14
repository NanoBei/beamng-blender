import bpy, math, sys, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import curves,R
scene=bpy.context.scene
root=bpy.data.objects['REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm']
road=bpy.data.objects['Road_Surface_Small_Concrete_2p7705m']
verts=[road.matrix_world@v.co for v in road.data.vertices]
faces=[list(p.vertices) for p in road.data.polygons]
bvh=BVHTree.FromPolygons(verts,faces)
def height(x,y):
    hit=bvh.ray_cast(Vector((float(x),float(y),20)),Vector((0,0,-1)))[0]
    return None if hit is None else hit.z
arc=curves[0]; heading=(arc['h']+arc['he'])/2
u=np.array([math.cos(heading),math.sin(heading)]);v=np.array([-u[1],u[0]])
apex=arc['c']+arc['sg']*R*np.array([math.sin(heading),-math.cos(heading)])
# Move 0.5 m toward the inside for a less edge-constrained static pose.
# This is not a validated steering trajectory.
xy=apex-.5*v
wheelobjects=[o for o in root.children if o.get('axle')]
wheelpoints={}
for o in wheelobjects:
    p=np.empty((len(o.data.vertices),3));o.data.vertices.foreach_get('co',p.ravel())
    wheelpoints[o.name]=p
contacts=[]
for name,p in wheelpoints.items():
    center=(p.min(0)+p.max(0))/2
    w=xy+center[0]*u+center[1]*v
    z=height(*w)
    assert z is not None,(name,w)
    contacts.append([center[0],center[1],z])
fit=np.linalg.lstsq(np.array([[x,y,1] for x,y,z in contacts]),np.array([z for x,y,z in contacts]),rcond=None)[0]
X=Vector((u[0],u[1],fit[0])).normalized()
Y=Vector((v[0],v[1],fit[1]));Y=(Y-X*Y.dot(X)).normalized();Z=X.cross(Y).normalized()
rot=Matrix((X,Y,Z)).transposed()
root.rotation_euler=rot.to_euler();root.location=(float(xy[0]),float(xy[1]),float(fit[2]))
bpy.context.view_layer.update()
# Align the four tyre supports to the road's local plane, retaining the rigid static car.
clearances=[]
for name,p in wheelpoints.items():
    q=p@np.array(rot).T+np.array(root.location)
    low=q[np.argmin(q[:,2])]; z=height(*low[:2]);assert z is not None
    clearances.append(float(low[2]-z))
root.location.z-=min(clearances)
bpy.context.view_layer.update()
report={'placement':'C1 apex, 0.5 m inward from nominal centreline, tangent heading; static pose only','position_m':list(root.location),'heading_deg':math.degrees(heading),'car_scale':list(root.scale),'tyre_lowest_point_clearance_m':[x-min(clearances) for x in clearances], 'road_width_straight_m':2.7705,'road_centerline_arc_radius_m':R,'static_pose_is_not_a_turning_path':True}
# The actual paved outline, used only for geometric static-plan checks.
edges={}
for f in faces:
    for a,b in zip(f,f[1:]+f[:1]):
        key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
boundary=np.array([[verts[a][:2],verts[b][:2]] for (a,b),count in edges.items() if count==1])
# Cross sections at front axle, rear axle and body ends: ray cast across road width.
sections=[]
for station in [-2.378,-1.316,0,1.524,2.378]:
    samples=[]
    for offset in np.linspace(-3,3,601):
        q=xy+station*u+offset*v
        if height(*q) is not None:samples.append(float(offset))
    sections.append({'car_local_x_m':station,'paved_offsets_from_car_centre_m':([min(samples),max(samples)] if samples else [])})
report['paved_cross_sections']=sections
(OUT/'placement_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
cam=bpy.data.objects.new('Camera_C63_C1_True_Top',bpy.data.cameras.new('Camera_C63_C1_True_Top'))
scene.collection.objects.link(cam)
# Vertical orthographic view, north is +Y, no perspective distortion.
cam.location=(float(apex[0]-1.5),float(apex[1]+.25),25);cam.rotation_euler=(0,0,0)
cam.data.type='ORTHO';cam.data.ortho_scale=12.8;scene.camera=cam
scene.render.resolution_x=1700;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'c63_c1_top.png')
# Camera overlays are separate reference objects, do not alter the road environment.
col=bpy.data.collections.new('REFERENCE_Preview_Scale_EXCLUDE_FROM_MAP');scene.collection.children.link(col)
mat=bpy.data.materials.new('Preview_Scale_White');mat.use_nodes=True
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(1,1,1,1);p.inputs['Emission Color'].default_value=(1,1,1,1);p.inputs['Emission Strength'].default_value=1
cx,cy=cam.location.x,cam.location.y
bx,by=cx-5.7,cy-4.9
cu=bpy.data.curves.new('One_metre_scale','CURVE');cu.dimensions='3D';cu.bevel_depth=.025;cu.bevel_resolution=1
for coords in [[(bx,by,3),(bx+1,by,3)],[(bx,by-.10,3),(bx,by+.10,3)],[(bx+1,by-.10,3),(bx+1,by+.10,3)]]:
    s=cu.splines.new('POLY');s.points.add(1)
    for pnt,coord in zip(s.points,coords):pnt.co=(*coord,1)
o=bpy.data.objects.new('Scale_1m',cu);col.objects.link(o);cu.materials.append(mat)
for text,pos,size in [('1 m',(bx+.3,by+.2,3),.23),('C63 / C1',(cx-5.7,cy+4.65,3),.32),('STATIC SCALE VIEW',(cx-5.7,cy+4.27,3),.18)]:
    d=bpy.data.curves.new('Label_'+text,'FONT');d.body=text;d.size=size;d.materials.append(mat)
    o=bpy.data.objects.new(d.name,d);col.objects.link(o);o.location=pos
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'c63_c1_static_preview.blend'))
bpy.ops.render.render(write_still=True)
print(json.dumps(report,indent=2))
