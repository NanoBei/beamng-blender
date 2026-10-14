import bpy, sys, json, math
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
road=bpy.data.objects['Road_Surface_Small_Concrete_2p85m']
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
delta=(3.0-2.85)/2
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

oldbvh=BVHTree.FromPolygons([Vector(p) for p in old],faces)
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
            inside=np.array([oldbvh.ray_cast(Vector((float(x),float(y),20)),Vector((0,0,-1)))[0] is not None for x,y in q])
            wi=np.clip(1-d/1.425,0,1);wi=wi*wi*(3-2*wi)
            wo=1-np.clip((d-1.8)/2.2,0,1);wo=wo*wo*(3-2*wo)
            w=np.where(inside,wi,wo);shift*=w[:,None]
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
    if not (ob==road or ob.name.startswith(('Terrain_','Concrete_Visual_Joint','Roadside_Rock','V16_','V17_')) or ob.name=='Sparse_Grass_Clumps'):continue
    pts=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices])
    if ob.name.startswith(('Roadside_Rock','V16_Small_Rail')):
        shift=np.repeat(displacement(pts.mean(0)[None,:],fade=False),len(pts),axis=0)
    else:shift=displacement(pts)
    if not np.any(np.abs(shift)>1e-10):continue
    if ob.name.startswith('V16_Small_Rail'):
        ob.location.x+=float(shift[0,0]);ob.location.y+=float(shift[0,1]);changed.append(ob.name);continue
    pts[:,:2]+=shift;inv=ob.matrix_world.inverted()
    for vert,p in zip(ob.data.vertices,pts):vert.co=inv@Vector(p)
    ob.data.update();changed.append(ob.name)
road.name='Road_Surface_Small_Concrete_3m'
road['small_road_width_m']=3.;road['straight_road_width_m']=3.
road['width_note']='V19: 3.00 m straight sections; side offset +0.075 m; retained local filled hairpins'
road['surface_revision']='V19 3.00 m trial width; V10 smooth elevations retained'
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
assert all(abs(c['width_m']-3.)<.001 for c in checks),checks
# Check the roadside stone footprints still stay outside the paved surface.
rock_bad=[]
for ob in scene.objects:
    if ob.name.startswith('Roadside_Rock'):
        if any(hit((ob.matrix_world@v.co)[:2]) is not None for v in ob.data.vertices):rock_bad.append(ob.name)
assert not rock_bad,rock_bad
assert root.matrix_world==pose
report={'target_width_m':3.,'previous_width_m':2.85,'each_side_increase_m':delta,'measured_straight_sections':checks,'both_hairpin_sides_offset':True,'main_road_unchanged':True,'road_vertex_elevations_unchanged':True,'shared_road_terrain_vertices_verified':len(shared),'road_triangle_flips':0,'rock_vertices_intruding_on_pavement':rock_bad,'car_pose_unchanged':True,'changed_objects':changed,'beamng_package_updated':False}

# Verify each U-channel retains its clear width/depth after the verge displacement.
channels=[]
for name in ['V16_Small_Road_U_Drain_Clear_0p50_Deep_0p60','V17_Small_Road_U_Drain_Clear_0p50_Deep_0p60']:
    ob=bpy.data.objects[name];p=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]).reshape(-1,6,3)
    widths=np.linalg.norm(p[:,4,:2]-p[:,1,:2],axis=1);depths=p[:,1,2]-p[:,2,2]
    assert np.max(np.abs(widths-.5))<.003,(name,widths.min(),widths.max())
    assert np.max(np.abs(depths-.6))<.0001
    channels.append({'name':name,'clear_width_min_m':float(widths.min()),'clear_width_max_m':float(widths.max()),'depth_m':float(depths.mean())})
report['small_drain_checks']=channels
report['main_pavement_y_edges_m']=[float(main_before[:,1].min()),float(main_before[:,1].max())]
assert report['main_pavement_y_edges_m']==[42.,46.5]
ditch=bpy.data.objects['Drainage_Channel_Clear_0p50m_Deep_0p60m']
dp=np.array([tuple(ditch.matrix_world@v.co) for v in ditch.data.vertices])
report['main_drain_y_extent_m']=[float(dp[:,1].min()),float(dp[:,1].max())]
report['main_paved_width_excludes_drain_m']=4.5
report['two_cars_clearance']={'body_width_m':1.839,'including_mirrors_m':2.02,'total_body_gap_m':4.5-2*1.839,'total_mirror_gap_m':4.5-2*2.02,'mirror_centre_gap_m':2.25-2.02,'mirror_edge_gap_each_m':1.125-1.01}
(OUT/'width_validation.json').write_text(json.dumps(report,indent=2))
scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG'
scene.camera=bpy.data.objects['Camera_C63_Straight_True_Top'];scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.filepath=str(OUT/'small_road_3m.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v19_width_3m.blend'))
bpy.ops.render.render(write_still=True)
# Linked mesh instances for a separate two-car width illustration, no size changes.
meeting=bpy.data.collections.new('REFERENCE_Main_Road_Meeting_Preview');scene.collection.children.link(meeting)
for i,(y,heading) in enumerate([(43.125,0),(45.375,math.pi)]):
    r=root.copy();r.name='REFERENCE_Meeting_C63_'+str(i+1);meeting.objects.link(r);r.location=(7.5,y,0);r.rotation_euler=(0,0,heading);r.scale=(1,1,1)
    for src in root.children:
        o=src.copy();o.data=src.data;o.name='Meeting_'+str(i+1)+'_'+src.name;meeting.objects.link(o);o.parent=r;o.matrix_parent_inverse=src.matrix_parent_inverse.copy();o.matrix_basis=src.matrix_basis.copy()
cam=bpy.data.objects.new('Camera_V19_Main_Meeting_Top',bpy.data.cameras.new('Camera_V19_Main_Meeting_Top'));scene.collection.objects.link(cam);cam.location=(7.5,44.25,20);cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=8.3
scene.camera=cam;scene.render.resolution_x=1500;scene.render.resolution_y=1300;scene.render.filepath=str(OUT/'main_road_two_cars.png')
bpy.context.view_layer.update()
# Check actual world meshes fit the paved road, including mirrors, at real scale.
world_bounds=[]
for r in [o for o in meeting.objects if o.type=='EMPTY']:
    lo=np.full(3,np.inf);hi=-lo
    for o in r.children:
        pts=np.empty((len(o.data.vertices),3));o.data.vertices.foreach_get('co',pts.ravel());M=np.array(o.matrix_world);pts=pts@M[:3,:3].T+M[:3,3];lo=np.minimum(lo,pts.min(0));hi=np.maximum(hi,pts.max(0))
    assert lo[1]>42 and hi[1]<46.5
    assert abs((hi-lo)[1]-2.02)<.0001
    assert abs(lo[2])<.0001
    world_bounds.append({'min':lo.tolist(),'max':hi.tolist()})
report['two_car_measured_world_bounds']=world_bounds
(OUT/'width_validation.json').write_text(json.dumps(report,indent=2))
bpy.ops.render.render(write_still=True)
meeting.hide_render=True;meeting.hide_viewport=True
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.filepath=str(OUT/'overview.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v19_width_3m.blend'))
print(json.dumps(report,indent=2))
