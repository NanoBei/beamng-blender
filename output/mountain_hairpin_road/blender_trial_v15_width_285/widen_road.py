import bpy, sys, json
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments,curves
scene=bpy.context.scene
road=bpy.data.objects['Road_Surface_Small_Concrete_2p7705m']
root=bpy.data.objects['REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm']
pose=root.matrix_world.copy()
old=np.array([tuple(v.co) for v in road.data.vertices]);faces=[list(p.vertices) for p in road.data.polygons]
counts=Counter();directed={}
for f in faces:
    for a,b in zip(f,f[1:]+f[:1]):
        k=tuple(sorted((a,b)));counts[k]+=1;directed[k]=(a,b)
nxt={a:b for k,(a,b) in directed.items() if counts[k]==1}
ids=[next(iter(nxt))]
while nxt[ids[-1]]!=ids[0]:ids.append(nxt[ids[-1]])
assert len(ids)==len(nxt)
P=old[ids,:2];E=np.roll(P,-1,axis=0)-P;length=np.linalg.norm(E,axis=1);T=E/length[:,None]
N=np.column_stack([T[:,1],-T[:,0]])
delta=(2.85-2.7705)/2
# Offset side edges; leave the entry and terminal cap stations fixed.
end=segments[-1]['end'];end_t=segments[-1]['t']
cap=(np.abs((P-end)@end_t)<.002)&(np.abs((np.roll(P,-1,axis=0)-end)@end_t)<.002)
entry=(P[:,1]>41.999)&(np.roll(P,-1,axis=0)[:,1]>41.999)
D=np.zeros_like(P)
for i in range(len(P)):
    prev=(i-1)%len(P)
    normals=[N[j] for j in [prev,i] if not cap[j] and not entry[j]]
    if not normals:continue
    if len(normals)==1:d=normals[0]*delta
    else:
        s=normals[0]+normals[1];d=s*delta/max(np.dot(s,normals[0]),.4)
    # Smoothly meet the unchanged main-road mouth.
    t=np.clip((42-P[i,1])/1.,0,1);d*=t*t*(3-2*t)
    D[i]=d

def displacement(points,fade=True):
    result=[]
    for start in range(0,len(points),256):
        q=points[start:start+256,:2]
        a=q[:,None,:]-P[None,:,:]
        f=np.clip(np.sum(a*E[None,:,:],axis=2)/(length**2)[None,:],0,1)
        dist2=np.sum((a-f[:,:,None]*E[None,:,:])**2,axis=2)
        idx=dist2.argmin(1);r=np.arange(len(q));ff=f[r,idx];d=np.sqrt(dist2[r,idx])
        shift=D[idx]*(1-ff[:,None])+D[(idx+1)%len(P)]*ff[:,None]
        if fade:
            w=np.clip(1-d/1.38,0,1);w=w*w*(3-2*w);shift*=w[:,None]
        shift[q[:,1]>=42-1e-6]=0
        result.append(shift)
    return np.concatenate(result)

main=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m']
main_before=np.array([tuple(v.co) for v in main.data.vertices])
terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
kdt=KDTree(len(old))
for i,p in enumerate(old):kdt.insert(Vector(p),i)
kdt.balance();shared=[]
for v in terrain.data.vertices:
    _,idx,d=kdt.find(v.co)
    if d<1e-5:shared.append((v.index,idx))
changed=[]
for ob in scene.objects:
    if ob.type!='MESH' or any(c.name.startswith('REFERENCE') for c in ob.users_collection):continue
    if not (ob==road or ob.name.startswith(('Terrain_','Concrete_Visual_Joint','Roadside_Rock')) or ob.name=='Sparse_Grass_Clumps'):continue
    pts=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices])
    if ob.name.startswith('Roadside_Rock'):
        shift=np.repeat(displacement(pts.mean(0)[None,:],fade=False),len(pts),axis=0)
    else:shift=displacement(pts)
    if not np.any(np.abs(shift)>1e-10):continue
    pts[:,:2]+=shift;inv=ob.matrix_world.inverted()
    for vert,p in zip(ob.data.vertices,pts):vert.co=inv@Vector(p)
    ob.data.update();changed.append(ob.name)
road.name='Road_Surface_Small_Concrete_2p85m'
road['small_road_width_m']=2.85;road['straight_road_width_m']=2.85
road['width_note']='V15: 2.85 m straight sections; side offset +0.03975 m; retained local filled hairpins'
road['surface_revision']='V15 2.85 m trial width; V10 smooth elevations retained'
new=np.array([tuple(v.co) for v in road.data.vertices])
assert np.array_equal(old[:,2],new[:,2])
assert np.array_equal(main_before,np.array([tuple(v.co) for v in main.data.vertices]))
assert all((terrain.data.vertices[i].co-road.data.vertices[j].co).length<1e-5 for i,j in shared)
road.data.calc_loop_triangles();tri=np.array([list(p.vertices) for p in road.data.loop_triangles])
def cross(points):
    a=points[tri[:,1],:2]-points[tri[:,0],:2];b=points[tri[:,2],:2]-points[tri[:,0],:2]
    return a[:,0]*b[:,1]-a[:,1]*b[:,0]
assert np.all(cross(new)*cross(old)>0),'Flipped road triangle'
bvh=BVHTree.FromPolygons([v.co for v in road.data.vertices],faces)
def hit(q):return bvh.ray_cast(Vector((float(q[0]),float(q[1]),20)),Vector((0,0,-1)))[0]
checks=[]
for seg,along in [(segments[0],12),(segments[0],15),(segments[2],5),(segments[2],7),(segments[4],5),(segments[4],11)]:
    q=seg['start']+along*seg['t']; sides=[]
    for sign in [-1,1]:
        low,high=0.,2.
        for _ in range(26):
            mid=(low+high)/2
            if hit(q+sign*mid*seg['n']) is not None:low=mid
            else:high=mid
        sides.append((low+high)/2)
    checks.append({'station_m':float(seg['s']+along),'width_m':sum(sides)})
assert all(abs(c['width_m']-2.85)<.001 for c in checks),checks
# Check the roadside stone footprints still stay outside the paved surface.
rock_bad=[]
for ob in scene.objects:
    if ob.name.startswith('Roadside_Rock'):
        if any(hit((ob.matrix_world@v.co)[:2]) is not None for v in ob.data.vertices):rock_bad.append(ob.name)
assert not rock_bad,rock_bad
assert root.matrix_world==pose
report={'target_width_m':2.85,'previous_width_m':2.7705,'each_side_increase_m':delta,'measured_straight_sections':checks,'both_hairpin_sides_offset':True,'main_road_unchanged':True,'road_vertex_elevations_unchanged':True,'shared_road_terrain_vertices_verified':len(shared),'road_triangle_flips':0,'rock_vertices_intruding_on_pavement':rock_bad,'car_pose_unchanged':True,'changed_objects':changed,'beamng_package_updated':False}
(OUT/'width_validation.json').write_text(json.dumps(report,indent=2))
for ob in bpy.data.objects:
    if ob.type=='FONT' and ob.data.body=='STATIC SCALE VIEW':ob.data.body='ROAD WIDTH 2.85 m / STATIC VIEW'
scene.render.filepath=str(OUT/'c63_c1_top_285.png');scene.cycles.samples=40
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v15_width_285.blend'))
bpy.ops.render.render(write_still=True)
print(json.dumps(report,indent=2))
