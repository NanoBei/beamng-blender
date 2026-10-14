"""Final visual and geometric QA corrections; preserve the v02 checkpoint."""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/china_subject2_v02_detailed.blend'))
s=bpy.context.scene
# Exact shared domain boundary. Avoid -1e-16 metre coordinates at exit ray tests.
clamped=0
for o in bpy.data.collections['01_Roads'].objects[:]+bpy.data.collections['02_Markings'].objects[:]:
    if o.type!='MESH':continue
    for v in o.data.vertices:
        for axis in [0,1]:
            if abs(v.co[axis])<1e-8 and v.co[axis]!=0:v.co[axis]=0;clamped+=1
    o.data.update()
# Inner L paint bands meet at an edge, rather than overlapping in one square.
o=bpy.data.objects['LINE_RightAngle_InnerWest'];miny=min(v.co.y for v in o.data.vertices)
for v in o.data.vertices:
    if abs(v.co.y-miny)<1e-5:v.co.y+=.15
# Centre the southbound approach arrow on the road.
for v in bpy.data.objects['ARROW_6'].data.vertices:v.co.x+=2
# Put grates wholly in the 30 cm shoulder, including the elevated ramp.
P=json.loads((ROOT/'parameters.json').read_text());D=P['dimensions'];Q=P['design_defaults']
manifest=json.loads((ROOT/'reports/build_manifest.json').read_text());rm=manifest['ramp']
def profile(st):
    if st<0 or st>rm['total']:return 0
    if st>rm['up']+6:st=rm['total']-st
    elif st>=rm['up']:return rm['height']
    if st<=rm['run']:return 30-math.sqrt(900-st*st)
    if st<=rm['run']+20:return rm['rise']+(st-rm['run'])*.1
    q=rm['up']-st;return rm['height']-(30-math.sqrt(900-q*q))
ax=sum(v.co.x for v in bpy.data.objects['ROAD_RightAngleApproach'].data.vertices[-2:])/2
original=[(10,12),(24,12),(17,46),(25,46),(38,32),(6,58),(30,63),(82,63),(ax+2.12,25)]
target=[(10,12.0565,0),(24,12.0565,0),(17,41.91475,0),(25,41.91475,0),(36.45,32,math.pi/2),(2.45,54.5,math.pi/2),(30,62.95,0),(82,62.95,0),(ax+2.254,25,math.pi/2)]
for i,((ox,oy),(nx,ny,a)) in enumerate(zip(original,target)):
    objects=[bpy.data.objects['DRAIN_Frame_'+str(i)]]+[bpy.data.objects['DRAIN_Grate_'+str(i)+'_'+str(k)] for k in range(9)]
    for o in objects:
        for v in o.data.vertices:
            x,y=v.co.x-ox,v.co.y-oy;v.co.x=nx+math.cos(a)*x-math.sin(a)*y;v.co.y=ny+math.sin(a)*x+math.cos(a)*y
            if i in [6,7]:v.co.z+=profile(v.co.x-26)
land=bpy.data.collections['04_Landscape'];random.seed(739)
leafm=[bpy.data.materials['C1_Leaves_'+str(i)] for i in range(3)]
wood=bpy.data.materials['C1_Tree_bark']
soil=bpy.data.materials.new('C1_Dry_soil');soil.use_nodes=True;soil.diffuse_color=(.14,.105,.06,1)
soil_bs=next(n for n in soil.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
soil_bs.inputs['Base Color'].default_value=(.14,.105,.06,1);soil_bs.inputs['Roughness'].default_value=.97

def newmesh(name,verts,faces,materials,indices=None):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);land.objects.link(o)
    for m in materials:me.materials.append(m)
    if indices:
        for p,i in zip(me.polygons,indices):p.material_index=i
    return o

def branch(name,a,b,r1,r2):
    a=Vector(a);b=Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,1,0))).normalized();v=d.cross(u)
    vs=[]
    for p,r in [(a,r1),(b,r2)]:
        for j in range(7):vs.append(tuple(p+r*(math.cos(j*2*math.pi/7)*u+math.sin(j*2*math.pi/7)*v)))
    return newmesh(name,vs,[(i,(i+1)%7,(i+1)%7+7,i+7) for i in range(7)],[wood])
crowns=[o for o in land.objects if o.name.startswith('TREE_Crown_')]
bytree={}
for o in crowns:bytree.setdefault(o.name.split('_')[2],[]).append(o)
for key,objects in bytree.items():
    trunk=bpy.data.objects['TREE_Trunk_'+key];base=trunk.location.copy();base.z=0
    vs=[];fs=[];indices=[]
    for crown in objects:
        centre=crown.location.copy();scale=crown.scale.copy()
        for j in range(1300):
            d=Vector((random.gauss(0,1),random.gauss(0,1),random.gauss(0,1))).normalized();rad=random.random()**(.40)
            p=centre+Vector((d.x*scale.x,d.y*scale.y,d.z*scale.z))*rad
            n=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-.3,1))).normalized();u=n.cross(Vector((0,1,0))).normalized();v=n.cross(u)
            length=random.uniform(.12,.24);width=length*random.uniform(.32,.50);idx=len(vs)
            # Six-vertex folded leaf, not billboard spheres.
            vs.extend([tuple(p-u*length*.5),tuple(p-u*length*.18+v*width*.5),tuple(p+u*length*.30+v*width*.32),tuple(p+u*length*.5),tuple(p+u*length*.30-v*width*.32),tuple(p-u*length*.18-v*width*.5)])
            fs.append(tuple(idx+k for k in range(6)));indices.append(random.randrange(3))
        for j in range(4):
            dest=centre+Vector((random.uniform(-.7,.7)*scale.x,random.uniform(-.7,.7)*scale.y,random.uniform(-.4,.5)*scale.z))
            a=Vector((base.x,base.y,centre.z*.53));mid=a.lerp(dest,.6)
            branch('TREE_Branch_'+key+'_'+str(len(vs))+'_'+str(j),a,mid,.045,.022)
            branch('TREE_Twig_'+key+'_'+str(len(vs))+'_'+str(j),mid,dest,.022,.006)
    newmesh('TREE_IndividualLeaves_'+key,vs,fs,leafm,indices)
    for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    # Irregular soil at the trunk base anchors trees to the terrain.
    ring=[(base.x,base.y,-.023)]
    for i in range(24):
        a=i*math.tau/24;r=random.uniform(.45,.65);ring.append((base.x+math.cos(a)*r,base.y+math.sin(a)*r,-.023))
    newmesh('TREE_SoilRing_'+key,ring,[(0,i+1,(i+1)%24+1) for i in range(24)],[soil])
# Fine gravel variation and worn paint: remain separate editable materials.
for name in ['C1_Weathered_light_concrete','C1_Connector_asphalt']:
    m=bpy.data.materials[name];n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    geo=next(x for x in n if x.type=='NEW_GEOMETRY');fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=95;fine.inputs['Detail'].default_value=2;l.new(geo.outputs['Position'],fine.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.45,.45,.45,1);ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(1,1,1,1)
    l.new(fine.outputs['Fac'],ramp.inputs[0]);previous=bs.inputs['Base Color'].links[0].from_socket
    mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=.33;l.new(previous,mul.inputs[1]);l.new(ramp.outputs[0],mul.inputs[2]);l.new(mul.outputs[0],bs.inputs['Base Color'])
for name in ['C1_Offwhite_road_paint','C1_Safety_yellow']:
    m=bpy.data.materials[name];n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');fine=next(x for x in n if x.type=='TEX_NOISE' and x.inputs['Scale'].default_value>10)
    r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.28;r.color_ramp.elements[0].color=(0,0,0,1);r.color_ramp.elements[1].position=.39;r.color_ramp.elements[1].color=(1,1,1,1);l.new(fine.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],bs.inputs['Alpha'])
s.view_settings.exposure=.3
bpy.data.lights['Sun_afternoon'].energy=3.2
s['qa_revision']='v03: exact exit boundary, non-overlapping corner paint, shoulder grates, centred arrow, detailed foliage and surface grain'
s.camera=bpy.data.objects['CAM_Overview']
bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/china_subject2_v03_final.blend'))
(ROOT/'reports/finalization.json').write_text(json.dumps({'clamped_boundary_coordinates':clamped,'trees_with_individual_leaves':len(bytree),'output':'blender/china_subject2_v03_final.blend'},indent=2))
print('FINAL saved',flush=True)
