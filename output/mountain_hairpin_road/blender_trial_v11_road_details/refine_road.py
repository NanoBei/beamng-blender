"""Build V11 from the saved V10 scene, in a separate Blender process.

The V10 height field and inner-corner filling remain intact. Dimensions in metres.
"""
import bpy, bmesh, math, json, sys, random
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / 'blender_trial_v10_smooth_hairpins'))
from road_profile import nearest, curves, segments, smooth, mesh_stats
scene = bpy.context.scene
SOURCE = bpy.data.filepath
WIDTH = 1.847 * 1.5
random.seed(41)

def collection(name):
    c = bpy.data.collections.new(name); scene.collection.children.link(c); return c

roads = collection('V11_Driving_Surfaces')
fixtures = collection('V11_Roadside_Fixtures')
vegetation = collection('V11_Vegetation_Visual')
reference = collection('REFERENCE_Audi_A4L_EXCLUDE_FROM_MAP')

def move_to(o, c):
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o)

def mesh(name, verts, faces, mat, coll=fixtures):
    data = bpy.data.meshes.new(name); data.from_pydata(verts, [], faces); data.update()
    o = bpy.data.objects.new(name, data); coll.objects.link(o)
    if mat: data.materials.append(mat)
    return o

def material(name, color, rough=.7, metal=0):
    m = bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*color,1)
    return m

def textured(name, dark, light, scale, bump):
    m=material(name,light,.88); n=m.node_tree.nodes; l=m.node_tree.links
    p=next(n for n in n if n.type=='BSDF_PRINCIPLED')
    coords=n.new('ShaderNodeTexCoord'); noise=n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=scale; noise.inputs['Detail'].default_value=3
    l.new(coords.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(*dark,1); ramp.color_ramp.elements[1].color=(*light,1)
    l.new(noise.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs['Color'],p.inputs['Base Color'])
    b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.24; b.inputs['Distance'].default_value=bump
    l.new(noise.outputs['Fac'],b.inputs['Height']); l.new(b.outputs['Normal'],p.inputs['Normal'])
    return m

def cube(name, pos, size, mat, coll=fixtures, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos); o=bpy.context.object; o.name=name
    o.dimensions=size; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move_to(o,coll); o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Small edge radius','BEVEL'); mod.width=bevel; mod.segments=2
    return o

def cylinder(name,pos,radius,depth,mat,coll=fixtures,rotation=(0,0,0),vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=pos,rotation=rotation)
    o=bpy.context.object; o.name=name; o.data.materials.append(mat); move_to(o,coll)
    for p in o.data.polygons: p.use_smooth=len(p.vertices)==4
    return o

asphalt=textured('V11_Unmarked_Rural_Asphalt',(.045,.052,.056),(.105,.115,.12),100,.002)
concrete=textured('V11_Small_Road_Concrete',(.34,.335,.31),(.54,.53,.49),6,.0018)
ditchmat=textured('V11_Drain_Concrete',(.26,.27,.25),(.40,.41,.38),18,.001)
steel=material('V11_Galvanized_Steel',(.47,.52,.55),.36,.78)
jointmat=material('V11_Concrete_Joints',(.15,.15,.14),.95)
soilmat=bpy.data.materials['Terrain_Continuous_Grass_Earth']

# Width changes: expand the flat main road only toward its outer side. Small-road
# straight widths shrink by 4.5 mm; taper the minute correction around filled tips.
def adjusted_xy(P):
    out=P.copy(); lower=P[:,1]<42-1e-6
    if lower.any():
        pts=P[lower]; s,indices,Q=nearest(pts)
        weight=np.ones(len(pts))
        for arc in curves:
            weight*=smooth((np.linalg.norm(pts-arc['c'],axis=1)-1)/2)
        weight*=smooth((42-pts[:,1])/2)
        out[lower]=pts+(Q-pts)*(1-WIDTH/2.775)*weight[:,None]
    above=~lower
    out[above,1]=42+(P[above,1]-42)*1.125
    return out

road=bpy.data.objects['Road_Surface_4m_and_2.775m']
original=np.array([list(v.co) for v in road.data.vertices])
for v,xy in zip(road.data.vertices,adjusted_xy(original[:,:2])): v.co.x,v.co.y=xy
bm=bmesh.new(); bm.from_mesh(road.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.co.y>=42-1e-5 for v in f.verts)],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(road.data); bm.free(); road.data.update()
road.name='Road_Surface_Small_Concrete_2p7705m'; move_to(road,roads)
road.data.materials.clear(); road.data.materials.append(concrete)
road['small_road_width_m']=WIDTH; road['straight_road_width_m']=WIDTH
road['main_road_width_m']=4.5; road['surface_revision']='V11 concrete; retained V10 smooth hairpins'
road['width_note']='2.7705 m on straight sections; retained local corner filling and junction flare'
main=mesh('Road_Surface_Main_Asphalt_4p5m',[(0,42,0),(44,42,0),(44,46.5,0),(0,46.5,0)],[(0,1,2),(0,2,3)],asphalt,roads)
main['width_m']=4.5; main['elevation_m']=0.; main['center_line']=False
thick=main.modifiers.new('Asphalt edge thickness','SOLIDIFY'); thick.thickness=.10; thick.offset=-1

terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
bm=bmesh.new(); bm.from_mesh(terrain.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,46,0),plane_no=(0,1,0),clear_outer=True)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(terrain.data); bm.free()
for v,xy in zip(terrain.data.vertices,adjusted_xy(np.array([list(v.co)[:2] for v in terrain.data.vertices]))):
    v.co.x,v.co.y=xy
    # Meet the new drainage lip at ground level, replacing the old outer cliff.
    if v.co.y>46.3: v.co.z=0
terrain.data.update()

kd=KDTree(len(road.data.vertices))
for v in road.data.vertices: kd.insert(Vector((v.co.x,v.co.y,0)),v.index)
kd.balance()
attr=terrain.data.attributes.get('GrassFactor')
distances=[]
for v in terrain.data.vertices:
    _,idx,d=kd.find(Vector((v.co.x,v.co.y,0)))
    distances.append(d)
    if d<4.5 and v.co.z>road.data.vertices[idx].co.z+.12:
        strength=.8*(1-float(smooth((d-2)/2.5)))*float(smooth((v.co.z-road.data.vertices[idx].co.z-.12)/.5))
        attr.data[v.index].value*=1-strength

# Soften inherited soil-mesh ridges near the road while pinning its shared edge.
neighbors=[set() for _ in terrain.data.vertices]
for e in terrain.data.edges:
    a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
base_z=np.array([v.co.z for v in terrain.data.vertices]); z=base_z.copy()
weights=np.array([.45*float(smooth((d-.06)/.7))*(1-float(smooth((d-3)/3)))
                  if v.co.y<41.8 and -2.9<v.co.x<46.9 else 0
                  for v,d in zip(terrain.data.vertices,distances)])
for _ in range(6):
    mean=np.array([np.mean(z[list(ns)]) if ns else z[i] for i,ns in enumerate(neighbors)])
    z=np.clip(z+weights*(mean-z),base_z-.35,base_z+.35)
for v,value in zip(terrain.data.vertices,z):v.co.z=float(value)
terrain.data.update()

# A U-shaped open concrete channel. 0.50 m clear internal width and 0.60 m
# vertical depth from the road/lip. Wall and floor thicknesses are trial values.
profile=[(46.50,0),(46.62,0),(46.62,-.6),(47.12,-.6),(47.12,0),(47.24,0),(47.24,-.72),(46.50,-.72)]
verts=[(x,y,z) for x in [-3,47] for y,z in profile]; count=len(profile)
faces=[(j,(j+1)%count,(j+1)%count+count,j+count) for j in range(count)]
faces.extend([tuple(range(count-1,-1,-1)),tuple(range(count,count*2))])
ditch=mesh('Drainage_Channel_Clear_0p50m_Deep_0p60m',verts,faces,ditchmat)
bm=bmesh.new();bm.from_mesh(ditch.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ditch.data);bm.free()
ditch['clear_width_m']=.5; ditch['depth_m']=.6; ditch['wall_thickness_trial_m']=.12

verts=[]; faces=[]; NX=101; NY=17
for j in range(NY):
    y=47.24+(51-47.24)*j/(NY-1); t=j/(NY-1)
    for i in range(NX):
        x=-3+50*i/(NX-1)
        z=1.35*math.sin(t*math.pi/2)+.09*math.sin(x*.5)*math.sin(t*math.pi)
        verts.append((x,y,z))
for j in range(NY-1):
    for i in range(NX-1):
        a=j*NX+i; faces.extend([(a,a+1,a+NX+1),(a,a+NX+1,a+NX)])
bank=mesh('Drainage_Outer_Vegetated_Bank',verts,faces,soilmat)
grass=bank.data.attributes.new('GrassFactor','FLOAT','POINT')
for v in bank.data.vertices:
    grass.data[v.index].value=.70+.2*math.sin(v.co.x*.7+v.co.y)
for p in bank.data.polygons:p.use_smooth=True
bank['height_trial_m']=1.35

# Rebuild the presentation cut sides along actual boundary vertices, removing
# the obsolete straight 3 m drop behind the main road.
for name in ['Terrain_Block_Sides','Terrain_Block_Bottom']:
    o=bpy.data.objects.get(name)
    if o:bpy.data.objects.remove(o,do_unlink=True)
sideverts=[]; sidefaces=[]
for obj in [terrain,bank,ditch]:
    for edge in obj.data.edges:
        a,b=[obj.data.vertices[i].co.copy() for i in edge.vertices]
        boundary=any(abs(a[k]-value)<1e-4 and abs(b[k]-value)<1e-4 for k,value in [(0,-3),(0,47),(1,12),(1,51)])
        if boundary and (a-b).length>1e-5:
            n=len(sideverts);sideverts.extend([tuple(a),tuple(b),(b.x,b.y,-25),(a.x,a.y,-25)])
            sidefaces.append((n,n+1,n+2,n+3))
mesh('Terrain_Block_Sides',sideverts,sidefaces,bpy.data.materials['Terrain_Cut_Base'])
mesh('Terrain_Block_Bottom',[(-3,12,-25),(47,12,-25),(47,51,-25),(-3,51,-25)],[(3,2,1,0)],bpy.data.materials['Terrain_Cut_Base'])

# More realistic straight W-beam steel guardrails on the small-road side only.
old_beams=[bpy.data.objects[n] for n in ['Main_Guardrail_Beam_1','Main_Guardrail_Beam_2']]
ranges=[]
for ob in old_beams:
    points=[ob.matrix_world@Vector(c) for c in ob.bound_box]
    ranges.append((min(p.x for p in points),max(p.x for p in points)))
for ob in list(bpy.data.objects):
    if ob.name.startswith(('Main_Guardrail_Beam','Rail_Post_')):bpy.data.objects.remove(ob,do_unlink=True)
cross=[(.0,.54),(.065,.555),(.105,.605),(.065,.65),(.0,.695),(.065,.74),(.105,.79),(.065,.835),(.0,.85)]
for run,(a,b) in enumerate(ranges,1):
    ends=np.linspace(a,b,max(2,math.ceil((b-a)/4)+1))
    for panel,(start,end) in enumerate(zip(ends[:-1],ends[1:])):
        v=[(x,41.76+y,z) for x in [start,end] for y,z in cross]; n=len(cross)
        ob=mesh(f'Guardrail_WBeam_{run}_{panel}',v,[(j,j+1,j+1+n,j+n) for j in range(n-1)],steel)
        mod=ob.modifiers.new('3 mm steel','SOLIDIFY');mod.thickness=.003
    for i,x in enumerate(ends):
        cylinder(f'Guardrail_Post_{run}_{i}',(x,41.59,.24),.07,1.08,steel)
        cube(f'Guardrail_Spacer_{run}_{i}',(x,41.69,.695),(.16,.18,.16),steel,bevel=.009)
        for z in [.605,.79]:
            cylinder(f'Guardrail_Bolt_{run}_{i}',(x,41.875,z),.014,.018,steel,rotation=(math.pi/2,0,0),vertices=6)
        if i%2==0:
            cube(f'Guardrail_Reflector_{run}_{i}',(x,41.89,.72),(.075,.009,.075),material(f'Reflector_{run}_{i}',(.86,.83,.66),.3),bevel=.006)
    # Closed end plates keep each rail horizontal at the road opening.
    for x in [a,b]:
        cube(f'Guardrail_End_Cap_{run}',(x,41.81,.695),(.04,.14,.31),steel,bevel=.018)

# Replace the old scale car with a simple A4L dimension reference. Body width
# excludes mirrors. Wheelbase and overhangs use the official dimensional drawing.
for ob in list(bpy.data.objects):
    if ob.name.startswith('Sedan'):bpy.data.objects.remove(ob,do_unlink=True)
car=bpy.data.objects.new('REFERENCE_Audi_A4L_4858x1847x1439mm',None);reference.objects.link(car)
car.location=(7.5,44.25,0); car['body_length_m']=4.858;car['body_width_excluding_mirrors_m']=1.847
car['height_m']=1.439;car['wheelbase_m']=2.908;car['export_to_beamng']=False
paint=material('A4L_Reference_Silver_Blue',(.19,.32,.40),.28,.55)
glassmat=material('A4L_Reference_Glass',(.026,.055,.073),.2,.2)
rubber=material('A4L_Reference_Tyre',(.018,.021,.024),.84)
rim=material('A4L_Reference_Wheel',(.39,.44,.46),.24,.78)
white=material('A4L_Lamps',(.83,.85,.77),.25)
red=material('A4L_Tail_Lamps',(.44,.017,.01),.28)
def carpart(ob):ob.parent=car;return ob
carpart(cube('A4L_Body_Dimension_Envelope',(0,0,.61),(4.858,1.847,.62),paint,reference,.09))
v=[(-1.52,-.79,.88),(1.22,-.79,.88),(1.22,.79,.88),(-1.52,.79,.88),(-1.02,-.68,1.409),(.58,-.68,1.409),(.58,.68,1.409),(-1.02,.68,1.409)]
carpart(mesh('A4L_Cabin',v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],glassmat,reference))
carpart(cube('A4L_Roof',(-.22,0,1.424),(1.64,1.39,.03),paint,reference,.012))
for x in [-1.386,1.522]:
    for y in [-.792,.792]:
        carpart(cylinder('A4L_Tyre',(x,y,.33),.33,.245,rubber,reference,(math.pi/2,0,0),24))
        carpart(cylinder('A4L_Alloy_Wheel',(x,y+math.copysign(.124,y),.33),.218,.014,rim,reference,(math.pi/2,0,0),16))
for y in [-.62,.62]:
    carpart(cube('A4L_Headlamp',(2.405,y,.69),(.04,.40,.105),white,reference,.02))
    carpart(cube('A4L_Taillamp',(-2.405,y,.70),(.04,.38,.10),red,reference,.015))
carpart(cube('A4L_Grille',(2.406,0,.53),(.038,.77,.26),rubber,reference,.045))

# Fine concrete slab joints along the straights, with height sampled from the
# actual surface. These are visual marks, not physical ledges or holes.
bvh=BVHTree.FromPolygons([v.co.copy() for v in road.data.vertices],[list(p.vertices) for p in road.data.polygons])
for seg in segments:
    if seg['kind']!='line':continue
    for along in np.arange(3,seg['length']-1,3):
        station=seg['s']+along
        if station<9:continue
        centre=seg['start']+along*seg['t']; points=[]
        for side,along_off in [(-1,-.004),(1,-.004),(1,.004),(-1,.004)]:
            p=centre+side*(WIDTH/2-.02)*seg['n']+along_off*seg['t']
            hit=bvh.ray_cast(Vector((p[0],p[1],20)),Vector((0,0,-1)),50)[0]
            if hit:points.append((p[0],p[1],hit.z+.001))
        if len(points)==4:mesh(f'Concrete_Visual_Joint_s{station:.2f}',points,[(0,1,2,3)],jointmat,vegetation)

# Sparse low grass on the uphill soil, denser beside the far drainage bank.
tbvh=BVHTree.FromPolygons([v.co.copy() for v in terrain.data.vertices],[list(p.vertices) for p in terrain.data.polygons])
bbvh=BVHTree.FromPolygons([v.co.copy() for v in bank.data.vertices],[list(p.vertices) for p in bank.data.polygons])
grassmats=[material('V11_Grass_Olive',(.19,.25,.055)),material('V11_Grass_Dry',(.34,.30,.13)),material('V11_Grass_Green',(.12,.20,.04))]
gv=[];gf=[];gmi=[]; clumps=0
for _ in range(1900):
    outer=random.random()<.47
    x=random.uniform(-2.8,46.8) if outer else random.uniform(7,35)
    y=random.uniform(47.32,50.9) if outer else random.uniform(19,41.5)
    hit,normal,_,_= (bbvh if outer else tbvh).ray_cast(Vector((x,y,20)),Vector((0,0,-1)),50)
    if hit is None or normal.z<.45:continue
    if not outer:
        _,idx,d=kd.find(Vector((x,y,0)))
        if not .6<d<3.6 or hit.z<road.data.vertices[idx].co.z+.2:continue
    clumps+=1
    for _ in range(random.randint(4,7)):
        theta=random.random()*math.tau;w=random.uniform(.01,.025);h=random.uniform(.08,.24)
        dx,dy=math.cos(theta)*w,math.sin(theta)*w; n=len(gv)
        px=x+random.uniform(-.06,.06);py=y+random.uniform(-.06,.06)
        gv.extend([(px-dx,py-dy,hit.z-.015),(px+dx,py+dy,hit.z-.015),(px+dy*3,py-dx*3,hit.z+h)])
        gf.append((n,n+1,n+2));gmi.append(random.randrange(3))
gr=mesh('Sparse_Grass_Clumps',gv,gf,grassmats[0],vegetation)
for m in grassmats[1:]:gr.data.materials.append(m)
for p,i in zip(gr.data.polygons,gmi):p.material_index=i

# Numerical checks: measured geometry, unchanged hairpin elevations, flush seams.
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(c) for o in car.children if o.type=='MESH' for c in o.bound_box]
size=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
arr=np.array([list(v.co) for v in road.data.vertices]); faces=np.array([list(p.vertices) for p in road.data.polygons])
shared=[]
for v in terrain.data.vertices:
    _,idx,d=kd.find(Vector((v.co.x,v.co.y,0)))
    if d<1e-5:shared.append(abs(v.co.z-road.data.vertices[idx].co.z))
report={'source_scene':SOURCE,'main_width_m':4.5,'main_elevation_error_m':max(abs(v.co.z) for v in main.data.vertices),
        'small_straight_width_m':WIDTH,'small_width_basis':'1.5 x 1.847 m body width, excluding mirrors',
        'reference_car_measured_size_m':size,'reference_car_world_position_m':list(car.location),
        'reference_car_wheelbase_m':2.908,'drain_clear_width_m':profile[3][0]-profile[2][0],
        'drain_depth_m':profile[1][1]-profile[2][1],'drain_wall_thickness_trial_m':.12,
        'guardrail_runs_x_m':ranges,'road_mesh':mesh_stats(arr,faces),
        'shared_road_terrain_vertices':len(shared),'max_shared_boundary_error_m':max(shared),
        'grass_clumps':clumps,'hairpin_height_field':'unchanged from V10','beamng_package_updated':False,'beamng_runtime_tested':False}
for i,arc in enumerate(curves):
    centres=arr[faces].mean(1);mask=np.linalg.norm(centres[:,:2]-arc['c'],axis=1)<3.5
    report[f'curve_{i+1}']=mesh_stats(arr,faces[mask])
assert abs(size[0]-4.858)<1e-5 and abs(size[1]-1.847)<1e-5 and abs(size[2]-1.439)<1e-5,size
assert report['main_elevation_error_m']==0 and report['road_mesh']['faces_over_30deg']==0
assert report['max_shared_boundary_error_m']<1e-5
assert all(report[f'curve_{i+1}']['max_face_slope_deg']<12 for i in range(2))
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)

def camera(name,position,target,scale):
    o=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(o)
    o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type='ORTHO';o.data.ortho_scale=scale;return o

scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
cameras=[('overview',camera('Camera_V11_Overview',(56,2,42),(22,33,-2),57),1500,1100),
         ('main_road_detail',camera('Camera_V11_Main_Detail',(20,31,11),(9,44.7,.1),19),1400,1000),
         ('drainage_detail',camera('Camera_V11_Drainage',(21,45,9),(18,46.8,-.15),4),1250,1000),
         ('top_view',camera('Camera_V11_Top',(22,32,75),(22,32,0),55),1400,1100),
         ('hairpins_detail',camera('Camera_V11_Hairpins',(39,5,23),(23,31,-3),35),1400,1100)]
notes=bpy.data.texts.new('V11_Parameters_and_Export_Notes')
notes.write('V11: main asphalt 4.5m flat, no center line; small concrete 2.7705m nominal; V10 smooth hairpins retained. A4L body 4.858x1.847x1.439m, wheelbase2.908m; excludes mirrors and export. U drain clear0.5m x depth0.6m, wall0.12m trial. Outer bank height1.35m trial. Guardrail straight W-beam with posts/bolts/endcaps. Grass sparse on uphill banks. BeamNG ZIP remains V9; re-export requires new objects/material mappings/physical concrete.\n')
for name,cam,w,h in cameras:
    scene.camera=cam;scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
scene.camera=cameras[0][1];scene.render.resolution_x=1500;scene.render.resolution_y=1100
for o in bpy.context.selected_objects:o.select_set(False)
car.select_set(True);bpy.context.view_layer.objects.active=car
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v11_road_details.blend'))
print('V11 SAVED',flush=True)
