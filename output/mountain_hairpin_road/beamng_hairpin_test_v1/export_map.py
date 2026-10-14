"""Export the approved v9 scene without changing the original .blend.

The small test map intentionally uses Visible Mesh Final collision to preserve
the exact road triangles, including the two modified inner-corner patches.
"""
import bpy, json, math, xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
LEVEL = 'tight_hairpin_test'
ROOT = OUT / 'package' / 'levels' / LEVEL
SHAPES = ROOT / 'art' / 'shapes'
TEXTURES = ROOT / 'art' / 'textures'
for p in [SHAPES, TEXTURES, ROOT / 'main']:
    p.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
road = bpy.data.objects['Road_Surface_4m_and_2.775m']
terrain = bpy.data.objects['Terrain_Berms_and_Unguarded_Drops']
rails = sorted([o for o in scene.objects if o.type == 'MESH' and o.name.startswith(('Main_Guardrail_Beam_', 'Rail_Post_'))], key=lambda o:o.name)
walls = bpy.data.objects['Terrain_Block_Sides']
assert len([o for o in rails if o.name.startswith('Main_Guardrail')]) == 2
assert max(abs(v.co.z) for v in road.data.vertices if v.co.y >= 42-1e-6) < 1e-6
assert not bpy.data.objects.get('Main_Guardrail_Beam_0')

# Make one non-overlapping world-planar UV atlas for the terrain color bake.
for ob in [terrain, road, walls] + rails:
    uv = ob.data.uv_layers.get('BeamNG_UV') or ob.data.uv_layers.new(name='BeamNG_UV')
    ob.data.uv_layers.active = uv
    for loop in ob.data.loops:
        q = ob.matrix_world @ ob.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((q.x + 3)/50, (q.y - 12)/37)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.bake.margin = 8
scene.render.bake.use_selected_to_active = False
bpy.ops.object.select_all(action='DESELECT')
terrain.select_set(True)
bpy.context.view_layer.objects.active = terrain
im = bpy.data.images.new('hairpin_terrain_color', width=2048, height=2048, alpha=False)
im.colorspace_settings.name = 'sRGB'
mat = terrain.data.materials[0]
nt = mat.node_tree
bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
output = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
old_surface = output.inputs['Surface'].links[0].from_socket
em = nt.nodes.new('ShaderNodeEmission')
if bs.inputs['Base Color'].is_linked:
    nt.links.new(bs.inputs['Base Color'].links[0].from_socket, em.inputs['Color'])
else:
    em.inputs['Color'].default_value = bs.inputs['Base Color'].default_value
nt.links.new(em.outputs[0], output.inputs['Surface'])
tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = im
nt.nodes.active = tex
print('Baking terrain color', flush=True)
bpy.ops.object.bake(type='EMIT')
im.filepath_raw = str(TEXTURES / 'terrain.color.png'); im.file_format = 'PNG'; im.save()
nt.links.new(old_surface, output.inputs['Surface']); nt.nodes.remove(em)
# Use the baked image for the preview as well as the game export.
nt.links.new(tex.outputs['Color'], bs.inputs['Base Color'])

NS = 'http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('', NS)
def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, '{'+NS+'}'+tag, {k:str(v) for k,v in attrs.items()})
    if text is not None: node.text = text
    return node
def floats(values):
    return ' '.join(format(float(x), '.9g') for x in values)

materials = {
    'hp_asphalt': ((.105,.12,.135,1), .92, 0, 'ASPHALT'),
    'hp_terrain_grass': ((1,1,1,1), .96, 0, 'GRASS'),
    'hp_terrain_soil': ((1,1,1,1), .96, 0, 'DIRT'),
    'hp_earth_side': ((.25,.205,.16,1), 1, 0, 'DIRT'),
    'hp_guardrail': ((.45,.53,.57,1), .4, .65, 'METAL'),
}
report = {'source_blend': bpy.data.filepath, 'units':'meters', 'up_axis':'Z_UP',
          'collision_mode':'Visible Mesh Final (intentional exact surface for small test map)',
          'beamng_runtime_tested':False, 'assets':{}}

def export_dae(asset_name, objects, default_material, raw=False):
    root = ET.Element('{'+NS+'}COLLADA', version='1.4.1')
    asset=el(root,'asset'); contrib=el(asset,'contributor')
    el(contrib,'authoring_tool','Hairpin v9 static mesh exporter')
    el(asset,'created','2026-10-13T00:00:00Z'); el(asset,'modified','2026-10-13T00:00:00Z')
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
            if grass is not None:
                material='hp_terrain_grass' if sum(grass.data[i].value for i in tri.vertices)/3 >= .5 else 'hp_terrain_soil'
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

export_dae('road',[road],'hp_asphalt',raw=True)
export_dae('terrain',[terrain],'hp_terrain_grass',raw=True)
export_dae('earth_sides',[walls],'hp_earth_side',raw=True)
export_dae('guardrails',rails,'hp_guardrail')

# Game PBR materials. Soil/grass share one atlas, with distinct physical surfaces.
game_mats={}
for name,(color,rough,metal,ground) in materials.items():
    stage={'baseColorFactor':list(color),'roughnessFactor':rough,'metallicFactor':metal}
    if name.startswith('hp_terrain'):
        stage['baseColorMap']=f'/levels/{LEVEL}/art/textures/terrain.color.png'
    game_mats[name]={'name':name,'class':'Material','mapTo':name,'version':1.5,
        'Stages':[stage,{}, {}, {}],'doubleSided':False,'translucent':False,
        'groundType':ground,'materialTag0':'Road and Path','useAnisotropic':True}
(ROOT/'main.materials.json').write_text(json.dumps(game_mats,indent=2))

I=[1,0,0,0,1,0,0,0,1]
items=[
 {'class':'LevelInfo','name':'theLevelInfo','gravity':-9.80665,'nearClip':.1,'visibleDistance':1500,'fogDensity':0,'fogAtmosphereHeight':1000,'canvasClearColor':[160,190,220,255]},
 {'class':'TimeOfDay','name':'tod','startTime':0,'time':0,'play':False,'dayLength':1800,'axisTilt':23.44,'latitude':30,'longitude':120,'year':2026,'month':6,'day':20,'utcOffset':'8'},
 {'class':'ScatterSky','name':'sunsky'},
 {'class':'CloudLayer','name':'clouds','coverage':.1,'windSpeed':.03,'windDirection':[1,0],'altitudeKm':4},
 {'class':'SpawnSphere','name':'spawns_default','dataBlock':'SpawnSphereMarker','position':[7,44,.6], 'rotationMatrix':[0,-1,0,1,0,0,0,0,1],'scale':[1,1,1]},
]
for asset_name in report['assets']:
    items.append({'class':'TSStatic','name':'hairpin_'+asset_name,'shapeName':f'/levels/{LEVEL}/art/shapes/{asset_name}.dae',
        'position':[0,0,0],'rotationMatrix':I,'scale':[1,1,1],'collisionType':'Visible Mesh Final',
        'decalType':'Visible Mesh Final','canSave':True})
(ROOT/'main'/'items.level.json').write_text('\n'.join(json.dumps(x,separators=(',',':')) for x in items)+'\n')
info={'title':'Tight Hairpin Test','description':'Compact double-hairpin driving test. Flat 4 m main road; 2.775 m lane; approximately 10 degree descent after an entry transition. Prototype imported from the approved Blender v9 model.',
    'authors':'Custom road project','size':[50,37],'previews':['preview.jpg'],
    'defaultSpawnPointName':'spawns_default','spawnPoints':[{'translationId':'Main Road','objectname':'spawns_default','description':'Flat main road near the downhill entrance','preview':'preview.jpg'}],
    'supportsTraffic':False,'supportsTimeOfDay':True,'roadRules':{'rightHandDrive':False}}
(ROOT/'info.json').write_text(json.dumps(info,indent=2))

# Check a vehicle-sized footprint on the exported raw road, not on the studio floor.
bvh=BVHTree.FromPolygons([road.matrix_world @ v.co for v in road.data.vertices], [list(p.vertices) for p in road.data.polygons],all_triangles=True)
hits=[]
for x in [4.5,7,9.5]:
    for y in [43.05,44,44.95]:
        hit=bvh.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),30)[0]
        assert hit is not None and abs(hit.z)<1e-4, (x,y,hit)
        hits.append([x,y,hit.z])
report['spawn_support_raycast']=hits
report['source_parameters']=json.loads((OUT.parent/'blender_trial_v9_flat_main'/'flat_main_validation.json').read_text())
(OUT/'export_report.json').write_text(json.dumps(report,indent=2))

# Fresh preview of v9; exclude the sizing car and all presentation-only floor objects.
keep={o.name for o in [road,terrain,walls]+rails}
for ob in scene.objects:
    if ob.type=='MESH': ob.hide_render=ob.name not in keep
cam=bpy.data.objects['Camera_Overview']
cam.location=(57,-23,47)
cam.rotation_euler=(Vector((22,31,-3))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=64
scene.camera=cam
scene.cycles.samples=24; scene.cycles.use_denoising=True
scene.render.resolution_x=1280; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=92
scene.render.filepath=str(ROOT/'preview.jpg')
bpy.ops.render.render(write_still=True)
print('EXPORT COMPLETE',flush=True)
