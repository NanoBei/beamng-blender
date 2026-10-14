"""Run in Blender with V11 loaded. Preserve the driving surface, refine its edges."""
import bpy, bmesh, math, json, random, bisect, hashlib
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT=Path(__file__).resolve().parent
scene=bpy.context.scene;SOURCE=bpy.data.filepath
road=bpy.data.objects['Road_Surface_Small_Concrete_2p7705m']
terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
main=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m']
rng=random.Random(1201)

def snapshot(ob):return np.array([tuple(v.co) for v in ob.data.vertices],dtype=np.float32).tobytes()
road_before=snapshot(road);main_before=snapshot(main)
def tree(ob):return BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
original_terrain=tree(terrain);rbvh=tree(road)
def hit(bvh,p):return bvh.ray_cast(Vector((p[0],p[1],20)),Vector((0,0,-1)),60)[0]

def recolor(mat,dark,light):
    ramp=next(n for n in mat.node_tree.nodes if n.type=='VALTORGB')
    ramp.color_ramp.elements[0].color=(*dark,1);ramp.color_ramp.elements[-1].color=(*light,1)
    mat.diffuse_color=(*[(a+b)/2 for a,b in zip(dark,light)],1)
recolor(main.data.materials[0],(.110,.115,.120),(.190,.195,.200))
recolor(road.data.materials[0],(.190,.185,.175),(.300,.290,.265))
main.data.materials[0].name='V12_Weathered_Midgray_Asphalt'
road.data.materials[0].name='V12_Aged_Gray_Concrete'

# Walk the actual road boundary in its face-winding direction. Outward normals
# identify the existing uphill/downhill sides, including both filled hairpins.
counts=Counter();directed={}
for p in road.data.polygons:
    ids=list(p.vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted((a,b)));counts[key]+=1;directed[key]=(a,b)
nxt={a:b for key,(a,b) in directed.items() if counts[key]==1}
start=next(iter(nxt));ids=[start];current=nxt[start]
while current!=start:ids.append(current);current=nxt[current]
assert len(ids)==len(nxt)
points=[road.data.vertices[i].co.copy() for i in ids]
lengths=[(points[(i+1)%len(points)]-p).to_2d().length for i,p in enumerate(points)]
cumulative=np.r_[0,np.cumsum(lengths)];perimeter=float(cumulative[-1])
def boundary(s):
    s%=perimeter;i=min(bisect.bisect_right(cumulative,s)-1,len(points)-1)
    return points[i].lerp(points[(i+1)%len(points)],float((s-cumulative[i])/lengths[i]))
def sample(s):
    p=boundary(s);t=(boundary(s+.12)-boundary(s-.12)).to_2d().normalized();n=Vector((t.y,-t.x))
    delta=[]
    for d in [.3,.7,1.2]:
        h=hit(original_terrain,p.to_2d()+n*d);delta.append(None if h is None else h.z-p.z)
    # Entry and terminating cross-section are not road-side obstacles.
    if p.y>41.35 or s<1 or 54<s<57.5:kind='transition'
    elif delta[1] is not None and delta[0] is not None:
        if delta[1]>.12 and delta[0]>-.03:kind='uphill'
        elif delta[1]<-.55 and delta[0]<-.07:kind='cliff'
        else:kind='transition'
    else:kind='transition'
    return {'s':s,'p':p,'n':n,'kind':kind,'delta':delta}
samples=[sample(s) for s in np.arange(0,perimeter,.08)]
edgekd=KDTree(len(samples))
for i,row in enumerate(samples):edgekd.insert(Vector((*row['p'][:2],0)),i)
edgekd.balance()
roadkd=KDTree(len(road.data.vertices))
for v in road.data.vertices:roadkd.insert(Vector((v.co.x,v.co.y,0)),v.index)
roadkd.balance()

# Raise a small earth toe on uphill edges; compress the existing descending
# ground horizontally near cliff edges, preserving the deeper terrain.
before_terrain=np.array([tuple(v.co) for v in terrain.data.vertices])
changed_up=changed_down=0;shared=[]
for v in terrain.data.vertices:
    _,ri,rd=roadkd.find(Vector((v.co.x,v.co.y,0)))
    if rd<1e-5:shared.append(v.index);continue
    if v.co.y>41.5:continue
    _,i,distance=edgekd.find(Vector((v.co.x,v.co.y,0)));row=samples[i]
    d=(v.co.to_2d()-row['p'].to_2d()).dot(row['n'])
    if not .01<d<1.8 or distance>1.9:continue
    p=row['p'];n=row['n'];fade=min(1,max(0,(41.4-p.y)/1.2))
    if row['kind']=='uphill':
        bump=.18*(1-math.exp(-d/.045))*math.exp(-(d/.58)**2)
        target=max(v.co.z,p.z+bump)
        v.co.z+=(target-v.co.z)*fade
        changed_up+=1
    elif row['kind']=='cliff':
        farther=d+.75*(1-math.exp(-d/.08))*math.exp(-(d/.95)**2)
        target=hit(original_terrain,p.to_2d()+n*farther)
        if target is not None:
            v.co.z+=(min(v.co.z,target.z)-v.co.z)*fade;changed_down+=1
terrain.data.update();tbvh=tree(terrain)

# Convex, closed, low-poly rocks are both visible geometry and the actual
# collision geometry. Keep the paved width clear, partly bury the rocks in soil.
rocks=bpy.data.collections.new('V12_Rock_Obstacles_COLLISION');scene.collection.children.link(rocks)
mat=bpy.data.materials.new('V12_Exposed_Stone');mat.use_nodes=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Roughness'].default_value=.94
coords=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=13
links.new(coords.outputs['Object'],noise.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.12,.115,.095,1);ramp.color_ramp.elements[1].color=(.29,.28,.235,1)
links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bs.inputs['Base Color'])
mat.diffuse_color=(.22,.21,.18,1)
rock_records=[];s=1.8
while s<perimeter:
    row=sample(s);s+=rng.uniform(.85,1.75)
    if row['kind']!='uphill':continue
    if sample(row['s']-.45)['kind']!='uphill' or sample(row['s']+.45)['kind']!='uphill':continue
    p=row['p'];n=row['n'];t=Vector((-n.y,n.x))
    half_length=rng.uniform(.24,.48);half_width=rng.uniform(.17,.29);height=rng.uniform(.23,.40)
    centre=p.to_2d()+n*(half_width+.045)
    if hit(tbvh,centre) is None:continue
    bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=2,radius=1)
    for v in bm.verts:v.co*=rng.uniform(.86,1.12)
    cloud=[v.co.copy() for v in bm.verts];bm.clear()
    for co in cloud:bm.verts.new(co)
    # Convex hull eliminates tiny concave pockets that can snag wheel nodes.
    hull=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    remove=set(hull.get('geom_interior',[])+hull.get('geom_unused',[]))
    if remove:bmesh.ops.delete(bm,geom=list(remove),context='VERTS')
    xyz=np.array([tuple(v.co) for v in bm.verts]);lo=xyz.min(0);span=xyz.max(0)-lo
    for v in bm.verts:
        local=(np.array(v.co)-lo)/span
        lateral=(local[1]*2-1)*half_width
        q=centre+t*((local[0]*2-1)*half_length)+n*lateral
        v.co=(q.x,q.y,p.z-.12+local[2]*(height+.12))
    # Tight inner corners need an additional small outward shift so no vertex
    # intrudes into the actual road polygon, even when its boundary is curved.
    for attempt in range(12):
        if not any(hit(rbvh,v.co) is not None for v in bm.verts):break
        for v in bm.verts:v.co.x+=n.x*.035;v.co.y+=n.y*.035
    else:bm.free();continue
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    data=bpy.data.meshes.new(f'Roadside_Rock_{len(rock_records)+1:02d}');bm.to_mesh(data);bm.free()
    ob=bpy.data.objects.new(data.name,data);rocks.objects.link(ob);data.materials.append(mat)
    ob['export_collision']=True;ob['road_edge_s_m']=row['s'];ob['height_above_edge_m']=height
    rock_records.append({'object':ob.name,'edge_point_m':list(p),'outward_normal':list(n),'height_above_edge_m':height,'edge_s_m':row['s']})

# Adjust existing grass roots to changed terrain, without adding collision to
# decorative grass or fine concrete joints.
grass=bpy.data.objects.get('Sparse_Grass_Clumps')
for face in grass.data.polygons:
    vs=[grass.data.vertices[i] for i in face.vertices]
    centre=(vs[0].co+vs[1].co)/2
    if centre.y>46:continue
    h=hit(tbvh,centre)
    if h:
        dz=h.z-.015-centre.z
        for v in vs:v.co.z+=dz
grass.data.update()

# Separate simpler guardrail collision rails/posts from visual wave profiles,
# bolts and reflectors. The beam is a narrow continuous solid at the same site.
collision=bpy.data.collections.new('V12_Guardrail_Collision_Only');scene.collection.children.link(collision)
steel=bpy.data.materials['V11_Galvanized_Steel']
for run,(a,b) in enumerate([(0,11.617231369),(20.676401138,44)],1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=((a+b)/2,41.811,.695));o=bpy.context.object
    o.name=f'COL_Guardrail_Beam_{run}';o.dimensions=(b-a,.113,.316)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    collision.objects.link(o);o.hide_render=True;o.hide_viewport=True;o.data.materials.append(steel)
for src in list(scene.objects):
    if src.name.startswith('Guardrail_Post_'):
        o=src.copy();o.data=src.data.copy();o.name='COL_'+src.name;collision.objects.link(o);o.hide_render=True;o.hide_viewport=True

# Verify closed rocks, lateral clearance, shared road/soil edges and actual
# downward ray hits beside the unprotected drop sections.
rock_checks=[]
for ob in rocks.objects:
    bm=bmesh.new();bm.from_mesh(ob.data)
    assert all(e.is_manifold for e in bm.edges),ob.name
    volume=bm.calc_volume(signed=True);assert volume>0,ob.name;bm.free()
    assert not any(hit(rbvh,v.co) is not None for v in ob.data.vertices),ob.name
    bvh=tree(ob);p=np.mean([list(v.co) for v in ob.data.vertices],axis=0);h=hit(bvh,p)
    assert h is not None
    rock_checks.append({'object':ob.name,'closed':True,'signed_volume_m3':volume,'top_hit':list(h)})
cliff_checks=[]
for row in samples[::15]:
    if row['kind']!='cliff':continue
    p=row['p'];n=row['n'];q=p.to_2d()+n*.35
    old=hit(original_terrain,q);new=hit(tbvh,q)
    if old and new:cliff_checks.append({'edge':list(p),'sample_xy':list(q),'drop_before_m':p.z-old.z,'drop_after_m':p.z-new.z})
assert cliff_checks and np.median([r['drop_after_m'] for r in cliff_checks])>.7
assert road_before==snapshot(road) and main_before==snapshot(main)
assert max(abs(terrain.data.vertices[i].co.z-before_terrain[i,2]) for i in shared)==0
report={'source_scene':SOURCE,'road_geometry_unchanged':True,'road_geometry_sha256':hashlib.sha256(road_before).hexdigest(),
        'main_geometry_unchanged':True,'shared_edge_vertices_pinned':len(shared),'terrain_vertices_raised':changed_up,'terrain_vertices_lowered':changed_down,
        'nominal_small_width_m':2.7705,'main_width_m':4.5,'rock_count':len(rock_records),'rock_height_trial_range_m':[.23,.40],
        'earth_toe_trial_height_m':.18,'rock_geometry_checks':rock_checks,'cliff_ray_checks':cliff_checks,
        'beamng_runtime_tested':False,'purpose':'Static driving-obstacle test, not a calibrated real-road safety model'}
(OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
(OUT/'rock_layout.json').write_text(json.dumps(rock_records,indent=2))
print('V12 rocks',len(rock_records),'median cliff drop at 0.35m',np.median([r['drop_after_m'] for r in cliff_checks]),flush=True)

def camera(name,pos,target,scale):
    ob=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(ob)
    ob.location=pos;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.type='ORTHO';ob.data.ortho_scale=scale
    return ob
cams=[('overview',bpy.data.objects['Camera_V11_Overview'],1500,1100),
      ('hairpins_detail',bpy.data.objects['Camera_V11_Hairpins'],1450,1100),
      ('roadside_rocks',camera('Camera_V12_Roadside_Rocks',(25,18,5),(22,28.8,-3),12),1400,1000),
      ('cliff_edge',camera('Camera_V12_Cliff_Edge',(21,15,3),(18.5,23.1,-4.5),12),1400,1000),
      ('main_road_detail',bpy.data.objects['Camera_V11_Main_Detail'],1400,1000)]
scene.render.image_settings.file_format='PNG';scene.cycles.samples=40;scene.cycles.use_denoising=True
for name,cam,w,h in cams:
    scene.camera=cam;scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
scene.camera=cams[1][1];scene.render.resolution_x=1450;scene.render.resolution_y=1100
notes=bpy.data.texts.new('V12_Driving_Collision_Notes')
notes.write('V12: aged midgray concrete and lighter asphalt. Road driving vertices unchanged. Uphill earth toes and closed convex rocks (0.23-0.40 m above edge) are physical obstacles. Cliff shoulders narrowed using existing lower terrain, no protective curb or guardrail. Dedicated simple guardrail collider collection is hidden in Blender and used by export. Reference Audi is a size prop, not a driveable car. BeamNG runtime not tested.\n')
for ob in bpy.context.selected_objects:ob.select_set(False)
road.select_set(True);bpy.context.view_layer.objects.active=road
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v12_driving_edges.blend'))
print('V12 SAVED',flush=True)
