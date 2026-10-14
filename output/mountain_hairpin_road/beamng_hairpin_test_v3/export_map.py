"""Export V20 to a separate driving-test map. Run with its saved blend loaded.

Low-poly rocks use their exact visible surface. Guardrail visuals have no
collision; simpler solid beams/posts are exported as hidden colliding TSStatics.
The small test scene intentionally retains exact road/terrain triangle collision.
"""
import bpy, json, math, xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT=Path(__file__).resolve().parent
LEVEL='tight_hairpin_drive_v3'
ROOT=OUT/'package'/'levels'/LEVEL
SHAPES=ROOT/'art'/'shapes';TEXTURES=ROOT/'art'/'textures'
for p in [SHAPES,TEXTURES,ROOT/'main',ROOT/'groundModels']:p.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
road=bpy.data.objects['Road_Surface_Small_Concrete_3m']
main=bpy.data.objects['Road_Surface_Main_Asphalt_5m']
terrain=bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
bank=bpy.data.objects['Drainage_Outer_Vegetated_Bank']
ditch=bpy.data.objects['Drainage_Channel_Clear_0p50m_Deep_0p60m']
walls=bpy.data.objects['Terrain_Block_Sides']
rocks=sorted(bpy.data.collections['V12_Rock_Obstacles_COLLISION'].objects,key=lambda o:o.name)
rails=sorted([o for o in scene.objects if o.type=='MESH' and o.name.startswith(('Guardrail_','V16_Small_Rail_','V16_Small_WBeam_'))],key=lambda o:o.name)
colliders=sorted(bpy.data.collections['V12_Guardrail_Collision_Only'].objects,key=lambda o:o.name)
grass=[bpy.data.objects['Sparse_Grass_Clumps']]
joints=[o for o in scene.objects if o.name.startswith('Concrete_Visual_Joint_')]
# Include all V16-V20 roadside banks, filled shoulders and actual U-channels.
soil_parts=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('V16_Drain_','V17_Drain_'))]
soil_parts += [o for o in scene.objects if o.type=='MESH' and '_V20_' in o.name]
small_drains=[bpy.data.objects[n] for n in ['V16_Small_Road_U_Drain_Clear_0p50_Deep_0p60','V17_Small_Road_U_Drain_Clear_0p50_Deep_0p60']]
# Build simple, closed collision proxies at the shortened small-road rail.
for src in list(rails):
    if src.name.startswith('V16_Small_WBeam_'):
        points=[src.matrix_world@v.co for v in src.data.vertices]
        a=sum(points[:9],Vector())/9;b=sum(points[-9:],Vector())/9
        bpy.ops.mesh.primitive_cube_add(size=1,location=(a+b)/2)
        o=bpy.context.object;o.name='COL_'+src.name
        o.rotation_euler=(b-a).to_track_quat('X','Z').to_euler()
        o.dimensions=((b-a).length,.113,.316)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(bpy.data.materials['V11_Galvanized_Steel']);colliders.append(o)
    elif src.name.startswith('V16_Small_Rail_Post_'):
        o=src.copy();o.data=src.data.copy();o.name='COL_'+src.name;scene.collection.objects.link(o);colliders.append(o)
all_objects=[road,main,terrain,bank,ditch,walls]+rocks+rails+colliders+grass+joints+soil_parts+small_drains
assert all(not o.name.startswith(('A4L','REFERENCE','Presentation')) for o in all_objects)
assert len(rocks)>20

# Hidden viewport proxies otherwise retain stale identity world matrices.
for ob in colliders:
    ob.hide_viewport=False
    ob.hide_set(False)
bpy.context.view_layer.update()

# Boolean excavation left an empty material slot on some earth faces.
for ob in [terrain,bank]+soil_parts:
    for i,mat in enumerate(ob.data.materials):
        if mat is None:ob.data.materials[i]=bpy.data.materials['Terrain_Continuous_Grass_Earth']

for ob in all_objects:
    uv=ob.data.uv_layers.get('BeamNG_UV') or ob.data.uv_layers.new(name='BeamNG_UV')
    ob.data.uv_layers.active=uv
    for loop in ob.data.loops:
        q=ob.matrix_world@ob.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=((q.x+3)/50,(q.y-12)/39.5)

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.render.bake.margin=8;scene.render.bake.use_selected_to_active=False
scene.render.bake.use_clear=False
def bake(objects,filename):
    im=bpy.data.images.new(filename,width=2048,height=2048,alpha=False)
    im.colorspace_settings.name='sRGB'
    mats=set(m for o in objects for m in o.data.materials)
    restore=[]
    for mat in mats:
        nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');old=out.inputs['Surface'].links[0].from_socket
        em=nt.nodes.new('ShaderNodeEmission');nt.links.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
        nt.links.new(em.outputs[0],out.inputs['Surface'])
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;nt.nodes.active=tex
        restore.append((nt,bs,out,old,em,tex))
    for ob in objects:
        bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.bake(type='EMIT')
    im.filepath_raw=str(TEXTURES/filename);im.file_format='PNG';im.save()
    for nt,bs,out,old,em,tex in restore:
        nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em)
        nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    print('Baked',filename,flush=True)
bake([terrain,bank]+soil_parts,'terrain.color.png')
bake([main,road],'road.color.png')

materials={
 'hp3_asphalt':((1,1,1,1),.92,0,'ASPHALT'),
 'hp3_concrete':((1,1,1,1),.94,0,'HP3_CONCRETE'),
 'hp3_drain':((.33,.34,.315,1),.9,0,'HP3_CONCRETE'),
 'hp3_terrain_grass':((1,1,1,1),.96,0,'GRASS'),
 'hp3_terrain_soil':((1,1,1,1),.96,0,'DIRT'),
 'hp3_earth_side':((.25,.205,.16,1),1,0,'DIRT'),
 'hp3_rock':((.22,.21,.18,1),.94,0,'ROCK'),
 'hp3_guardrail':((.47,.52,.55,1),.36,.78,'METAL'),
 'hp3_reflector':((.86,.83,.66,1),.3,0,'METAL'),
 'hp3_joint':((.15,.15,.14,1),1,0,'HP3_CONCRETE'),
 'hp3_blade_green':((.19,.25,.055,1),1,0,'GRASS'),
 'hp3_blade_dry':((.34,.30,.13,1),1,0,'GRASS'),
 'hp3_blade_dark':((.12,.20,.04,1),1,0,'GRASS'),
}

NS = 'http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('', NS)
def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, '{'+NS+'}'+tag, {k:str(v) for k,v in attrs.items()})
    if text is not None: node.text = text
    return node
def floats(values):
    return ' '.join(format(float(x), '.9g') for x in values)

report = {'source_blend': bpy.data.filepath, 'units':'meters', 'up_axis':'Z_UP',
          'collision_mode':'Visible Mesh Final (intentional exact surface for small test map)',
          'beamng_runtime_tested':False, 'assets':{}}

def export_dae(asset_name, objects, default_material, raw=False):
    root = ET.Element('{'+NS+'}COLLADA', version='1.4.1')
    asset=el(root,'asset'); contrib=el(asset,'contributor')
    el(contrib,'authoring_tool','Hometown hairpin V20 / BeamNG V3 exporter')
    el(asset,'created','2026-10-14T00:00:00Z'); el(asset,'modified','2026-10-14T00:00:00Z')
    el(asset,'unit',name='meter',meter=1); el(asset,'up_axis','Z_UP')
    effects=el(root,'library_effects'); mats=el(root,'library_materials')
    for name,(color,rough,metal,ground) in materials.items():
        fx=el(effects,'effect',id=name+'-effect'); common=el(fx,'profile_COMMON')
        tech=el(common,'technique',sid='common'); lambert=el(tech,'lambert')
        diffuse=el(lambert,'diffuse'); el(diffuse,'color',floats(color))
        material=el(mats,'material',id=name,name=name)
        el(material,'instance_effect',url='#'+name+'-effect')
    geoms=el(root,'library_geometries'); scenes=el(root,'library_visual_scenes')
    visual=el(scenes,'visual_scene',id='Scene',name='Scene')
    base=el(visual,'node',id='base00',name='base00',type='NODE')
    start=el(base,'node',id='start01',name='start01',type='NODE')
    counts=[]
    dg=bpy.context.evaluated_depsgraph_get()
    for number,ob in enumerate(objects):
        evaluated=None
        if raw: mesh=ob.data
        else:
            evaluated=ob.evaluated_get(dg)
            mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
        mesh.calc_loop_triangles()
        gid=f'{asset_name}_{number:02d}'
        geom=el(geoms,'geometry',id=gid+'-mesh',name=gid); m=el(geom,'mesh')
        points=[ob.matrix_world @ v.co for v in mesh.vertices]
        normalmat=ob.matrix_world.to_3x3().inverted().transposed()
        normals=[(normalmat @ n.vector).normalized() for n in mesh.corner_normals]
        uv=mesh.uv_layers.get('BeamNG_UV')
        assert uv is not None
        def source(suffix,values,names):
            sid=gid+'-'+suffix; s=el(m,'source',id=sid)
            el(s,'float_array',floats(values),id=sid+'-array',count=len(values))
            t=el(s,'technique_common')
            a=el(t,'accessor',source='#'+sid+'-array',count=len(values)//len(names),stride=len(names))
            for name in names: el(a,'param',name=name,type='float')
            return sid
        pos=source('positions',[x for p in points for x in p],['X','Y','Z'])
        norm=source('normals',[x for n in normals for x in n],['X','Y','Z'])
        uvs=source('uv',[x for l in uv.data for x in l.uv],['S','T'])
        vert=el(m,'vertices',id=gid+'-vertices'); el(vert,'input',semantic='POSITION',source='#'+pos)
        groups=defaultdict(list); degenerate=0
        grass=mesh.attributes.get('GrassFactor')
        for tri in mesh.loop_triangles:
            a,b,c=[points[i] for i in tri.vertices]
            if (b-a).cross(c-a).length_squared < 1e-16:
                degenerate += 1; continue
            material=default_material
            if ob.name.startswith('Guardrail_Reflector'): material='hp3_reflector'
            if ob.name=='Sparse_Grass_Clumps': material=['hp3_blade_green','hp3_blade_dry','hp3_blade_dark'][tri.material_index]
            if grass is not None:
                material='hp3_terrain_grass' if sum(grass.data[i].value for i in tri.vertices)/3 >= .5 else 'hp3_terrain_soil'
            for vi,li in zip(tri.vertices,tri.loops): groups[material].extend([vi,li,li])
        for material,indices in groups.items():
            tr=el(m,'triangles',material=material,count=len(indices)//9)
            el(tr,'input',semantic='VERTEX',source='#'+gid+'-vertices',offset=0)
            el(tr,'input',semantic='NORMAL',source='#'+norm,offset=1)
            el(tr,'input',semantic='TEXCOORD',source='#'+uvs,offset=2,set=0)
            el(tr,'p',' '.join(map(str,indices)))
        node=el(start,'node',id=gid+'_a1',name=gid+'_a1',type='NODE')
        inst=el(node,'instance_geometry',url='#'+gid+'-mesh')
        bind=el(inst,'bind_material'); common=el(bind,'technique_common')
        for material in groups:
            instmat=el(common,'instance_material',symbol=material,target='#'+material)
            el(instmat,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set=0)
        counts.append({'object':ob.name,'vertices':len(points),'triangles':sum(len(v)//9 for v in groups.values()),'degenerate_removed':degenerate})
        if evaluated: evaluated.to_mesh_clear()
    sc=el(root,'scene'); el(sc,'instance_visual_scene',url='#Scene')
    ET.ElementTree(root).write(SHAPES/(asset_name+'.dae'),encoding='utf-8',xml_declaration=True)
    report['assets'][asset_name]=counts
    print('Exported',asset_name,sum(c['triangles'] for c in counts),'triangles',flush=True)



export_dae('main_road',[main],'hp3_asphalt',raw=True)
export_dae('small_road',[road],'hp3_concrete',raw=True)
export_dae('terrain',[terrain,bank]+soil_parts,'hp3_terrain_grass',raw=True)
export_dae('drainage',[ditch]+small_drains,'hp3_drain')
export_dae('roadside_rocks',rocks,'hp3_rock',raw=True)
export_dae('guardrails_visual',rails,'hp3_guardrail')
export_dae('guardrails_collision',colliders,'hp3_guardrail',raw=True)
export_dae('vegetation',grass,'hp3_blade_green',raw=True)
export_dae('concrete_joints',joints,'hp3_joint',raw=True)
export_dae('earth_sides',[walls],'hp3_earth_side',raw=True)

game_mats={}
for name,(color,rough,metal,ground) in materials.items():
    stage={'baseColorFactor':list(color),'roughnessFactor':rough,'metallicFactor':metal}
    texture='terrain.color.png' if name.startswith('hp3_terrain') else ('road.color.png' if name in ['hp3_asphalt','hp3_concrete'] else None)
    if texture:stage['baseColorMap']=f'/levels/{LEVEL}/art/textures/{texture}'
    game_mats[name]={'name':name,'class':'Material','mapTo':name,'version':1.5,'Stages':[stage,{},{},{}],
                     'groundType':ground,'doubleSided':name.startswith('hp3_blade'),'translucent':False,
                     'useAnisotropic':True,'materialTag0':'Road and Path'}
(ROOT/'main.materials.json').write_text(json.dumps(game_mats,indent=2))
# Explicit dry hard-surface baseline, not measured real-road tire friction.
ground={'HP3_CONCRETE':{'staticFrictionCoefficient':1.0,'slidingFrictionCoefficient':.8,
    'hydrodynamicFriction':.01,'stribeckVelocity':6,'strength':1,'roughnessCoefficient':0,
    'defaultDepth':0,'shearStrength':0,'collisiontype':'ASPHALT','skidMarks':True}}
(ROOT/'groundModels'/'hairpin_dry_concrete.json').write_text(json.dumps(ground,indent=2))

I=[1,0,0,0,1,0,0,0,1]
items=[
 {'class':'LevelInfo','name':'theLevelInfo','gravity':-9.80665,'nearClip':.1,'visibleDistance':1500,'fogDensity':0,'fogAtmosphereHeight':1000,'canvasClearColor':[160,190,220,255]},
 {'class':'TimeOfDay','name':'tod','startTime':0,'time':0,'play':False,'dayLength':1800,'axisTilt':23.44,'latitude':30,'longitude':120,'year':2026,'month':6,'day':20,'utcOffset':'8'},
 {'class':'ScatterSky','name':'sunsky'},
 {'class':'CloudLayer','name':'clouds','coverage':.1,'windSpeed':.03,'windDirection':[1,0],'altitudeKm':4},
 {'class':'SpawnSphere','name':'spawns_default','dataBlock':'SpawnSphereMarker','position':[7.5,44.5,.6],'rotationMatrix':[0,-1,0,1,0,0,0,0,1],'scale':[1,1,1]},
]
decorative={'guardrails_visual','vegetation','concrete_joints','earth_sides'}
for asset in report['assets']:
    items.append({'class':'TSStatic','name':'hairpin3_'+asset,'shapeName':f'/levels/{LEVEL}/art/shapes/{asset}.dae',
      'position':[0,0,0],'rotationMatrix':I,'scale':[1,1,1],
      'collisionType':'None' if asset in decorative else 'Visible Mesh Final',
      'decalType':'None' if asset in decorative else 'Visible Mesh Final',
      'isRenderEnabled':asset!='guardrails_collision','canSave':True})
(ROOT/'main'/'items.level.json').write_text('\n'.join(json.dumps(x,separators=(',',':')) for x in items)+'\n')
info={'title':'Hometown Hairpin Drive V3','description':'V20 prototype: 5 m flat asphalt road, 3 m concrete lane, two smoothed hairpins, exposed colliding rocks and unguarded drops. Dry-surface physics baseline; game testing required.',
      'authors':'Custom road project','size':[50,40],'previews':['preview.jpg'],'defaultSpawnPointName':'spawns_default',
      'spawnPoints':[{'translationId':'Main Road','objectname':'spawns_default','description':'Flat main road beside the 0.5 x 0.6 m drainage channel','preview':'preview.jpg'}],
      'supportsTraffic':False,'supportsTimeOfDay':True,'roadRules':{'rightHandDrive':False}}
(ROOT/'info.json').write_text(json.dumps(info,indent=2))
(ROOT/'README_zh.txt').write_text((OUT/'Windows导入与试车说明.txt').read_text())

report['source_parameters']=json.loads((OUT.parent/'blender_trial_v20_main5m_drain_setback'/'validation_report.json').read_text())
report['source_parameters']['cliff_ray_checks']=[]
rb=BVHTree.FromPolygons([road.matrix_world@v.co for v in road.data.vertices],[list(p.vertices) for p in road.data.polygons])
tb=BVHTree.FromPolygons([terrain.matrix_world@v.co for v in terrain.data.vertices],[list(p.vertices) for p in terrain.data.polygons])
import sys,numpy as np
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments
mid=segments[2]
for along in [2,4,6,8,10]:
    q=mid['start']+along*mid['t'];lo,hi=0.,2.
    for _ in range(25):
        d=(lo+hi)/2;p=q+d*mid['n']
        if rb.ray_cast(Vector((*p,20)),Vector((0,0,-1)))[0]:lo=d
        else:hi=d
    p=q+(lo-1e-4)*mid['n'];edge=rb.ray_cast(Vector((*p,20)),Vector((0,0,-1)))[0]
    sample=p+.4*mid['n'];ground=tb.ray_cast(Vector((*sample,20)),Vector((0,0,-1)))[0]
    assert edge is not None and ground is not None and edge.z-ground.z>1.5
    report['source_parameters']['cliff_ray_checks'].append({'edge':list(edge),'sample_xy':sample.tolist(),'drop_after_m':edge.z-ground.z})
report['small_guardrail_collision_proxies']=[o.name for o in colliders if o.name.startswith('COL_V16_')]
assert len(report['small_guardrail_collision_proxies'])==9
report['small_drain_floor_checks']=[]
for ob in small_drains:
    rows=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]).reshape(-1,6,3)
    for i in np.linspace(1,len(rows)-2,5).astype(int):
        row=rows[i];floor=(row[2]+row[3])/2
        report['small_drain_floor_checks'].append({'object':ob.name,'xy':floor[:2].tolist(),'floor_z':float(floor[2]),'lip_z':float(row[1,2])})
report['filled_shoulder_checks']=[]
for ob in soil_parts:
    if 'Filled_Drain_Shoulder' in ob.name:
        rows=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]).reshape(-1,2,3)
        for i in np.linspace(1,len(rows)-2,5).astype(int):
            p=rows[i].mean(0);report['filled_shoulder_checks'].append({'xy':p[:2].tolist(),'z':float(p[2])})
report['collision_by_asset']={it['name'].removeprefix('hairpin3_'):it['collisionType'] for it in items if it['class']=='TSStatic'}
report['collision_note']='Exact low-poly rock surfaces; simplified solid rail/post proxies; raw road and earth triangle surfaces; no grass/joint/presentation collisions.'
report['physics_note']='Dry concrete coefficients are uncalibrated trial baseline, not real-world driving validation.'
report['excluded_reference_car']=True
bvh=BVHTree.FromPolygons([v.co.copy() for v in main.data.vertices],[list(p.vertices) for p in main.data.polygons])
support=[]
for x in [5,7.5,10]:
    for y in [43.25,44.25,45.25]:
        h=bvh.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),30)[0]
        assert h is not None and abs(h.z)<1e-6;support.append(list(h))
report['spawn_support_raycast']=support
(OUT/'export_report.json').write_text(json.dumps(report,indent=2))

keep={o.name for o in [road,main,terrain,bank,ditch,walls]+rocks+rails+grass+joints+soil_parts+small_drains}
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render=ob.name not in keep
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=92;scene.render.filepath=str(ROOT/'preview.jpg')
bpy.ops.render.render(write_still=True)
print('EXPORT V3 COMPLETE',flush=True)
