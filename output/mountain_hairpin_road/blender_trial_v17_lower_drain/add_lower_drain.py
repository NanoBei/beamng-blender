import bpy,bmesh,math,sys,json,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments,curves,R,smooth
scene=bpy.context.scene
road=bpy.data.objects['Road_Surface_Small_Concrete_2p85m'];terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
main=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m'];car=bpy.data.objects['REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm']
def signature(o):return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons],list(map(list,o.matrix_world)))).encode()).hexdigest()
unchanged={o.name:signature(o) for o in [road,main]};carpose=car.matrix_world.copy()
def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
rb=tree(road);original_tb=tree(terrain)
def hit(bvh,q):return bvh.ray_cast(Vector((float(q[0]),float(q[1]),20)),Vector((0,0,-1)),80)[0]
def route(s):
    g=next((g for g in segments if g['s']-1e-6<=s<=g['s']+g['length']+1e-6),segments[-1]);a=s-g['s']
    h=g['h'] if g['kind']=='line' else g['h']+g['sg']*a/R
    q=g['start']+a*g['t'] if g['kind']=='line' else g['c']+g['sg']*R*np.array([math.sin(h),-math.cos(h)])
    return q,np.array([-math.sin(h),math.cos(h)])
def edge(s,sign=1):
    q,n=route(s);n=n*sign;lo,hi=0.,2.9
    for _ in range(23):
        d=(lo+hi)/2
        if hit(rb,q+n*d):lo=d
        else:hi=d
    xy=q+n*(lo-1e-4);p=hit(rb,xy);assert p is not None
    return np.array(p),n
coll=bpy.data.collections.new('V17_Lower_Road_Drain');scene.collection.children.link(coll)
def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);coll.objects.link(o)
    if mat:d.materials.append(mat)
    return o
soil=bpy.data.materials['Terrain_Continuous_Grass_Earth'];steel=bpy.data.materials['V11_Galvanized_Steel'];concrete=bpy.data.materials['V11_Drain_Concrete']
# Remove old presentation labels; preserve all road and vehicle geometry.
old=bpy.data.collections.get('REFERENCE_Preview_Scale_EXCLUDE_FROM_MAP')
if old:
    for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
mid=segments[2];u=mid['t'];n=mid['n'];start=mid['start'];end_s=mid['s']+mid['length']

protected={o.name:signature(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('V16_')}
# 3: follow actual outer paved edge through lower exit straight soil side.
last=segments[4]
ss=np.linspace(last['s']+2.0,last['s']+last['length']-.15,151)
rows=[edge(float(s),1) for s in ss]
P=np.array([p for p,n0 in rows]);N=np.array([n0 for p,n0 in rows])
# Cut an actual open trench and a short bank transition out of the old ground.
# Outer replacement boundary uses exact terrain ray elevations.
outer=P[:,:2]+N*1.55
outerz=[]
for q in outer:
    h=hit(original_tb,q);assert h is not None;outerz.append(h.z)
outline=np.vstack([P[:,:2]-N*.002,outer[::-1]])
v=[(float(x),float(y),z) for z in [-30.,20.] for x,y in outline];m=len(outline)
f=[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]+[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
cutter=mesh('TEMP_Drain_Excavation',v,f,None)
bm=bmesh.new();bm.from_mesh(cutter.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cutter.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');terrain.select_set(True);bpy.context.view_layer.objects.active=terrain
mod=terrain.modifiers.new('Drain excavation','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;mod.solver='EXACT'
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
# U profile: 0.50 m clear width, 0.60 m deep, 0.12 m concrete walls.
profile=[(0,0),(.12,0),(.12,-.60),(.62,-.60),(.62,0),(.74,0)]
v=[]
for p,normal in rows:
    for d,z in profile:v.append((*(p[:2]+normal*d),p[2]+z))
f=[];k=len(profile)
for i in range(len(rows)-1):
    for j in range(k-1):a=i*k+j;f.append((a,a+k,a+k+1,a+1))
ditch=mesh('V17_Small_Road_U_Drain_Clear_0p50_Deep_0p60',v,f,concrete)
# Give the bed/walls physical thickness beneath the visible U profile.
mod=ditch.modifiers.new('Concrete thickness','SOLIDIFY');mod.thickness=.12;mod.offset=-1
# Sloping earth starts after the channel's outer wall.
v=[]
for (p,normal),zout in zip(rows,outerz):
    for d,t in [(.74,0),(.94,.20),(1.2,.55),(1.55,1)]:
        v.append((*(p[:2]+normal*d),float(p[2]*(1-t)+zout*t)))
f=[]
for i in range(len(rows)-1):
    for j in range(3):a=i*4+j;f.append((a,a+4,a+5,a+1))
bank=mesh('V17_Drain_Outer_Soil_Bank',v,f,soil)
a=bank.data.attributes.new('GrassFactor','FLOAT','POINT')
for x in a.data:x.value=.72
for f in bank.data.polygons:f.use_smooth=True
# Close the exposed earth faces at both ends of the replaced strip.
for index in [0,len(rows)-1]:
    p,normal=rows[index];zz=outerz[index]
    coords=[(*(p[:2]+normal*d),p[2]+z) for d,z in [(0,0),(.12,0),(.12,-.6),(.62,-.6),(.62,0),(.74,0)]]
    coords.extend([(*(p[:2]+normal*1.55),zz),(*(p[:2]+normal*1.55),min(zz,p[2])-.8),(*p[:2],p[2]-.8)])
    mesh('V17_Drain_End_Earth_'+str(index),coords,[tuple(range(len(coords)))],soil)

# Shift only stones belonging to this lower-straight verge, retaining stone shapes.
newtb=tree(terrain);banktree=tree(bank);moved=[]
def nearest_drain(q):
    i=int(np.linalg.norm(P[:,:2]-q,axis=1).argmin())
    return i,float((q-P[i,:2])@N[i]),float(np.linalg.norm(q-P[i,:2]))
for ob in list(scene.objects):
    if not ob.name.startswith('Roadside_Rock'):continue
    p=np.mean([list(v.co) for v in ob.data.vertices],axis=0)
    along=float((p[:2]-last['start'])@last['t'])
    i,d,dist=nearest_drain(p[:2])
    if 1.5<along<16.1 and 0<d<1.35 and dist<1.5:
        shift=N[i]*max(0,1.12-d)
        for vert in ob.data.vertices:vert.co.x+=shift[0];vert.co.y+=shift[1]
        q=p[:2]+shift;hh=[h for h in [hit(newtb,q),hit(banktree,q)] if h]
        if hh:
            dz=max(h.z for h in hh)-.1-min(v.co.z for v in ob.data.vertices)
            for vert in ob.data.vertices:vert.co.z+=dz
        moved.append(ob.name)
grass=bpy.data.objects.get('Sparse_Grass_Clumps')
if grass:
    bm=bmesh.new();bm.from_mesh(grass.data);remove=[]
    for face in list(bm.faces):
        vv=list(face.verts);bottom=sorted(vv,key=lambda v:v.co.z)[:2];q=(bottom[0].co+bottom[1].co)/2
        along=float((np.array(q[:2])-last['start'])@last['t'])
        i,d,dist=nearest_drain(np.array(q[:2]))
        if not 1.9<along<15.9 or dist>1.7:continue
        if -.03<d<.77:remove.append(face);continue
        hh=[h for h in [hit(newtb,q),hit(banktree,q)] if h]
        if hh:
            dz=max(h.z for h in hh)-.015-q.z
            for vert in vv:vert.co.z+=dz
    if remove:bmesh.ops.delete(bm,geom=remove,context='FACES')
    bm.to_mesh(grass.data);bm.free();grass.data.update()
assert all(signature(bpy.data.objects[name])==sig for name,sig in unchanged.items())
assert all(signature(bpy.data.objects[name])==sig for name,sig in protected.items())
assert car.matrix_world==carpose
newtb=tree(terrain);db=tree(ditch);depths=[]
for i in [10,35,65,95,125,145]:
    p,out=rows[i];q=p[:2]+out*.37;ground=hit(newtb,q);floor=hit(db,q)
    assert floor is not None
    assert ground is None or ground.z<floor.z-.02,(i,ground,floor)
    depths.append(float(p[2]-floor.z))
    assert hit(rb,q) is None,'Drain occupies road'
assert all(abs(d-.6)<.001 for d in depths)
report={'source':'V16 roadside layout','road_width_m':2.85,'paved_geometry_unchanged':True,'car_pose_unchanged':True,'v16_guardrail_and_upper_drain_unchanged':True,'new_drain_side':'lower exit straight uphill/northeast side','new_drain_length_m':float(ss[-1]-ss[0]),'start_after_C2_exit_m':2.0,'clear_width_m':.5,'depth_m':.6,'depth_ray_checks_m':depths,'relocated_rocks':moved,'beamng_updated':False}
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2))
scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200
scene.render.filepath=str(OUT/'overview.png');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v17_lower_drain.blend'))
bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_V16_Top'];scene.render.resolution_x=1500;scene.render.resolution_y=1500;scene.render.filepath=str(OUT/'top_view.png');bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v17_lower_drain.blend'))
print(json.dumps(report,indent=2))
