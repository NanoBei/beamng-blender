"""Build approved V07 in the live Blender, preserving materials and calibrated C63.
The caller must first save a copy of the live scene to before_v07_live_scene.blend.
To reproduce in background, open that backup with --disable-autoexec and run this file.
"""
import bpy,bmesh,math,json,ast,random
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.geometry import tessellate_polygon
D=Path(__file__).resolve().parent;ROOT=D.parent
G=json.loads((D/'geometry_input.json').read_text());P=G['parameters'];Q=P['design_defaults']
assert (D/'before_v07_live_scene.blend').exists(),'Save the live scene before this operation'
scene=bpy.context.scene
assert bpy.data.objects.get('TREE_Trunk_0'), 'Rebuild from before_v07_live_scene.blend, not from a generated V07 file'
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_v07_working.blend'))
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.name='C1_V07_ClosedLoop_90x60m'
# Preserve the existing calibrated car and a detailed tree as editable linked instances.
high=bpy.data.collections['05_ReferenceCar_HIGH'];proxy=bpy.data.collections['06_ReferenceCar_PROXY']
keep=set(high.all_objects)|set(proxy.all_objects)
trunk=bpy.data.objects.get('TREE_Trunk_0');tree_prototypes=[]
if trunk:
    base=trunk.matrix_world.translation.copy();base.z=0
    for ob in list(scene.objects):
        if ob.type=='MESH' and (ob.name in ['TREE_Trunk_0','TREE_IndividualLeaves_0','TREE_SoilRing_0'] or ob.name.startswith(('TREE_Branch_0_','TREE_Twig_0_'))):
            data=ob.data.copy();data.transform(Matrix.Translation(-base)@ob.matrix_world)
            tree_prototypes.append((ob.name,data))
for ob in list(scene.objects):
    if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
for c in list(scene.collection.children):
    if c not in [high,proxy]:
        scene.collection.children.unlink(c)
        if c.users==0:bpy.data.collections.remove(c)
C={'ReferenceCar_HIGH':high,'ReferenceCar_PROXY':proxy}
for name in ['01_Roads','02_Markings','03_Facilities','04_Landscape','07_Dimensions','08_Presentation']:
    c=bpy.data.collections.new(name);scene.collection.children.link(c);C[name[3:]]=c
matnames={'concrete':'C1_Weathered_light_concrete','asphalt':'C1_Connector_asphalt','white':'C1_Offwhite_road_paint',
          'yellow':'C1_Safety_yellow','black':'C1_Curb_charcoal','grass':'C1_Grass_ground','joint':'C1_Expansion_joint',
          'metal':'C1_Galvanised_steel','blue':'C1_Sign_blue','cream':'C1_Rendered_masonry','repair':'C1_Concrete_repairs',
          'tire':'C1_Subtle_rubber_scuffs','soil':'C1_Dry_soil','wood':'C1_Tree_bark'}
mats={k:bpy.data.materials[v] for k,v in matnames.items()}
globals().update(mats)
src=ast.parse((ROOT/'blender/build_scene.py').read_text())
fnames={'mesh','move_collection','box','rect','polygon','text_obj','camera','ribbon_line','sign'}
exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in fnames],type_ignores=[]),'shared_blender_helpers','exec'))
font=bpy.data.fonts.load('/System/Library/Fonts/Hiragino Sans GB.ttc')
for row in G['roads']:
    o=mesh(row['name'],row['vertices'],row['faces'],mats[row['material']]);o['layout']='approved V07'
    o['surface']='10% exam hill' if row['name']=='ROAD_HillRamp' else 'flat Z=0'
    # Very thin union triangles can change winding when Blender stores float32 vertices.
    bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
    for face in bm.faces:
        if face.normal.z<0:face.normal_flip()
    bm.to_mesh(o.data);bm.free();o.data.update()
for row in G['markings']:
    if row['name'].startswith('DETAIL_'):continue
    mesh(row['name'],row['vertices'],row['faces'],mats[row['material']],'Markings')
hill=G['hill'];hs=hill['start'];he=hill['end'];total=hill['total'];peak=hill['height'];up=hill['up'];run=hill['run'];rise=hill['rise']
def ascent(s):
    if s<=run:return 30-math.sqrt(max(0,900-s*s))
    if s<=run+20:return rise+(s-run)*.1
    q=up-s;return peak-(30-math.sqrt(max(0,900-q*q)))
def ramp_z(s):
    if s<=0 or s>=total:return 0.
    if s<up:return ascent(s)
    if s<=up+6:return peak
    return ascent(total-s)
# Solid retaining bed; only the exam hill is raised above the flat ground.
top=next(r for r in G['roads'] if r['name']=='ROAD_HillRamp')['vertices']
v=[];f=[]
for i in range(len(top)//2):
    x=top[2*i][0];z=top[2*i][2]
    for y,zz in [(hs[1]-2.38,-.18),(hs[1]+2.38,-.18),(hs[1]+2.38,z),(hs[1]-2.38,z)]:v.append((x,y,zz))
for i in range(len(top)//2-1):
    for j in [0,1,3]:f.append((4*i+j,4*(i+1)+j,4*(i+1)+(j+1)%4,4*i+(j+1)%4))
# Include the narrow shoulder ledges under the kerbs, but not a second overlapping road top.
for side in [-1,1]:
    for i in range(len(top)//2-1):
        a,b=top[2*i],top[2*(i+1)];off=len(v)
        v.extend([(a[0],hs[1]+side*2.2,a[2]),(b[0],hs[1]+side*2.2,b[2]),(b[0],hs[1]+side*2.38,b[2]),(a[0],hs[1]+side*2.38,a[2])])
        f.append((off,off+1,off+2,off+3) if side==1 else (off+3,off+2,off+1,off))
mesh('BED_Hill_Retaining',v,f,cream,'Roads')
box('LAND_Site90x60',(35,30,-.20),(90,60,.34),grass,'Landscape')
box('DISPLAY_Ground',(35,30,-.42),(125,95,.10),cream,'Presentation')
# Kerbs are split into metre-scale blocks in a single editable mesh.
v=[];f=[];mi=[];cube=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
for b in G['curbs']:
    off=len(v);v += [(x,y,z) for (x,y),z in zip(b['xy'],b['z'])];v += [(x,y,z+.15) for (x,y),z in zip(b['xy'],b['z'])]
    f += [tuple(off+i for i in face) for face in cube];mi += [b['material']]*6
curbs=mesh('CURBS_BlackYellow',v,f,yellow,'Facilities');curbs.data.materials.append(black)
for p,m in zip(curbs.data.polygons,mi):p.material_index=m

root=next(o for o in high.objects if o.type=='EMPTY')
root.location=(20,42.45,0);root.rotation_euler=(0,0,0)
for o in high.all_objects:
    if o.type=='MESH':o.hide_set(True);o.hide_render=False
for o in proxy.all_objects:o.hide_set(False)
high.hide_render=False;high.hide_viewport=False;proxy.hide_render=True;proxy.hide_viewport=False
scene['car_display']='High detail render; <=300k triangle proxy in viewport; common calibrated parent'
scene['asset_license']='C63 by wishingchain / Free3D Personal Use License; local files only'

# Cameras follow the approved plan orientation (+Y points to the right in the top view).
cams={}
cams['01_overview']=camera('CAM_Overview',(112,-102,113),(35,30,.3),117)
cams['02_top']=camera('CAM_Top',(35,30,130),(35,30,0),100)
cams['02_top'].rotation_euler=(0,0,math.pi/2)
cams['03_reverse']=camera('CAM_Reverse',(27,-12,34),(14.5,9,0),28)
cams['04_parallel']=camera('CAM_Parallel',(47,-7,29),(36,9.4,0),26)
cams['05_hill']=camera('CAM_Hill',(57,8,31),(35,55.18,1),64)
cams['06_s_curve']=camera('CAM_SCurve',(54,20,65),(54,20,0),29)
cams['06_s_curve'].rotation_euler=(0,0,math.pi/2)
cams['07_right_angle']=camera('CAM_RightAngle',(90,15,28),(70,32,0),24)
cams['08_flat_hairpin']=camera('CAM_FlatHairpin',(47,-4,47),(23,31,0),42)
cams['09_return_loop']=camera('CAM_ReturnLoop',(-44,0,50),(-2,33,0),55)
cams['10_main_road']=camera('CAM_MainRoad',(35,22,12),(20,43.5,0),27)
world=bpy.data.worlds.new('V07_Daylight');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.59,.70,.85,1);bg.inputs['Strength'].default_value=.5
sd=bpy.data.lights.new('V07_Sun','SUN');sd.energy=3.0;sd.angle=math.radians(10)
sun=bpy.data.objects.new('V07_Sun',sd);C['Presentation'].objects.link(sun);sun.rotation_euler=(math.radians(26),math.radians(-24),math.radians(-28))
scene.camera=cams['01_overview'];scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.25
C['Dimensions'].hide_render=True;C['Dimensions'].hide_viewport=True
for text,loc in [('Reverse 5.558 x 2.447 m',(14.5,1,.06)),('Parallel 8.287 x 2.647 m',(35,5,.06)),
                 ('S 135 deg / R7.5-R4 / W3.5',(53,22,.06)),('Right angle W3.908',(70,32,.06)),
                 ('Hill 10% / R30 / H2.298',(35,55.18,2.5)),('Return W4.5 / R10',(-7,30,.06)),('Flat Z=0 / W3',(23,31,.06))]:
    text_obj('DIM_'+text,text,loc,.45,blue,'Dimensions')
scene['approved_layout']='V07: 90x60m; closed loop; S135; flat V20 hairpin + main; 10% exam hill'
scene['parameter_file']='//parameters_v07.json';scene['geometry_input']='//geometry_input.json'
scene['scope']='Blender model only; user reference dimensions; no certification or driving simulation'
scene['route_order']='Reverse > Parallel > S curve > Right angle > Hill > Return > Reverse'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_v07_geometry.blend'))
print('V07 geometry checkpoint saved',flush=True)

# Surface detail, modest landscaping and functional site furniture.
for row in G['markings']:
    if row['name'].startswith('DETAIL_'):mesh(row['name'],row['vertices'],row['faces'],mats[row['material']],'Facilities')
random.seed(1248)
for i,(x,y,scale) in enumerate(G['vegetation']):
    for name,data in tree_prototypes:
        o=bpy.data.objects.new('TREE_V07_'+str(i)+'_'+name,data);C['Landscape'].objects.link(o)
        o.location=(x,y,0);o.scale=(scale,scale,scale)
v=[];f=[]
for x,y,h in G['grass_points']:
    j=len(v);v.extend([(x-.03,y,-.03),(x+.03,y,-.03),(x+.015,y+.02,h)]);f.append((j,j+1,j+2))
mesh('GRASS_SparseTufts',v,f,bpy.data.materials['C1_Leaves_1'],'Landscape')
# Drain grates lie in the reserved paved band, outside paint and clear width.
# Explicit positions use shoulder centre offsets, not a generic nearest road guess.
drains=[(9,6.0565,0),(20,13.9435,0),(35,12.08525,0),(43,7.91475,0),(-9.55,25,math.pi/2),(-9.55,38,math.pi/2),(63,46.3,0)]
for i,(x,y,h) in enumerate(drains):
    frame=box(f'DRAIN_Frame_{i}',(0,0,.001),(.72,.26,.004),black)
    frame.location=(x,y,0);frame.rotation_euler.z=h
    for k in range(10):
        local_x=-.30+k*.067
        o=box(f'DRAIN_Grate_{i}_{k}',(0,0,.004),(.025,.19,.004),metal)
        # Helper box geometry is local around the supplied centre, so transform directly.
        o.location=(x+local_x*math.cos(h),y+local_x*math.sin(h),0);o.rotation_euler.z=h
for index,label,x,y in [(1,'倒车入库',8,17),(2,'侧方停车',35,4.5),(3,'曲线行驶',63,19),
                        (4,'直角转弯',77.7,31),(5,'坡道起步',61,58.6),(6,'平面发卡弯',18,37),(7,'循环回程',-3,25)]:sign(index,label,x,y)
# Ground presentation titles are separated from the physical exam paint.
for text,x,y in [('01 REVERSE',13,19),('02 PARALLEL',35,3),('03 S-CURVE',62,17),
                 ('04 RIGHT ANGLE',68,25),('05 HILL START',33,59),('FLAT HAIRPINS',21,35),('RETURN LOOP',-3,30)]:
    text_obj('LABEL_'+text,text,(x,y,.015),.50,cream,'Presentation')
for x in range(8,62,4):
    z=ramp_z(hs[0]-x)
    if z>.2:
        for y in [hs[1]-2.385,hs[1]+2.385]:box('RETAINING_PanelJoint',(x,y,z/2),(.012,.008,z),joint)
# A restrained fence along the outer boundary, with an open western gate.
for name,a,b in [('N',(-9.7,59.7),(79.7,59.7)),('E',(79.7,.3),(79.7,59.7)),
                 ('W1',(-9.97,.3),(-9.97,26.5)),('W2',(-9.97,33.5),(-9.97,59.7))]:
    aa=Vector((*a,0));bb=Vector((*b,0));N=math.ceil((bb-aa).length/2.6)
    for i in range(N+1):
        p=aa.lerp(bb,i/N);box('FENCE_Post_'+name+str(i),(p.x,p.y,.65),(.05,.05,1.3),metal)
    for z in [.35,1.15]:ribbon_line('FENCE_Rail_'+name+str(z),[(a[0],a[1],z),(b[0],b[1],z)],.035,metal)
    for i in range(math.ceil((bb-aa).length/.28)):
        p=aa.lerp(bb,i/max(1,math.ceil((bb-aa).length/.28)));box('FENCE_Wire_'+name+str(i),(p.x,p.y,.75),(.009,.009,.95),metal)

scene['car_high_triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in high.objects if o.type=='MESH')
scene['car_proxy_triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in proxy.objects if o.type=='MESH')
scene['v07_source_file']='//before_v07_live_scene.blend'
scene['s_curve_angle_degrees']=135;scene['flat_road_elevation']=0;scene['ramp_peak_m']=peak
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':
        region=area.spaces.active.region_3d;region.view_location=Vector((35,30,0));region.view_distance=105
        region.view_rotation=Quaternion((1,0,0),math.radians(28))
        area.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative();bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_v07_final.blend'))
(D/'build_manifest.json').write_text(json.dumps(dict(file='china_subject2_v07_final.blend',previews={k:v.name for k,v in cams.items()},
    objects=len(scene.objects),trees=len(G['vegetation']),car_high_triangles=scene['car_high_triangles'],car_proxy_triangles=scene['car_proxy_triangles'],
    source_plan='layout_proposal_v07',geometry_summary=G['geometry_preparation']),ensure_ascii=False,indent=2))
print('V07 detailed model saved',len(scene.objects),'objects',flush=True)
