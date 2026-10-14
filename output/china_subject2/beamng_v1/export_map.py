"""Export the approved V07 in an isolated Blender process. Source is never overwritten."""
import bpy, math, json, sys, hashlib
from pathlib import Path
from collections import defaultdict
from mathutils import Matrix, Vector
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
from beamng_io import write_dae
SOURCE=D.parent/'blender_v07/china_subject2_v07_final.blend'
LEVEL='china_c1_subject2_v1';ROOT=D/'package/levels'/LEVEL
TEX=ROOT/'art/textures';SHAPES=ROOT/'art/shapes'
for p in [TEX,SHAPES,ROOT/'main',ROOT/'groundModels',D/'previews']:p.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),use_scripts=False)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_game_working.blend'))
scene=bpy.context.scene
source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
G=json.loads((D.parent/'blender_v07/geometry_input.json').read_text())
excluded=[]
for cn in ['05_ReferenceCar_HIGH','06_ReferenceCar_PROXY','07_Dimensions','08_Presentation']:
    col=bpy.data.collections[cn]
    for o in list(col.all_objects):
        if o.type in {'CAMERA','LIGHT'}:continue
        excluded.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update()
# Source road/curb geometry is immutable; only export-copy paint lift changes.
for o in scene.objects:
    if o.name.startswith(('LINE_','ARROW_')):o.location.z+=.004
    elif o.name.startswith('DETAIL_'):o.location.z+=.002

# Geometry creation is limited to game ground outside the site and simple fence proxies.
def make_mesh(name,verts,faces,material):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    o=bpy.data.objects.new(name,m);scene.collection.objects.link(o);m.materials.append(material);return o
rings=[(-160,-130,230,0),(-160,60,230,190),(-160,0,-10,60),(80,0,230,60)]
v=[];f=[]
for a,b,c,d in rings:
    k=len(v);v.extend([(a,b,-.03),(c,b,-.03),(c,d,-.03),(a,d,-.03)]);f.append((k,k+1,k+2,k+3))
outer=make_mesh('GAME_OuterGround',v,f,bpy.data.materials['C1_Grass_ground'])
# UV0 atlas for broad surfaces, 2 m tiled paint, dominant-axis mapping for small props.
def uv_for(o,mode='atlas'):
    if o.type!='MESH':return
    uv=o.data.uv_layers.get('BeamNG_UV') or o.data.uv_layers.new(name='BeamNG_UV');o.data.uv_layers.active=uv
    for p in o.data.polygons:
        normal=o.matrix_world.to_3x3()@p.normal;axis=max(range(3),key=lambda i:abs(normal[i]))
        for li in p.loop_indices:
            q=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
            coords=((q.x+10)/90,q.y/60) if mode=='atlas' else ((q.x/2,q.y/2) if mode=='paint' else (q.y/2,q.z/2) if axis==0 else (q.x/2,q.z/2) if axis==1 else (q.x/2,q.y/2))
            uv.data[li].uv=coords
for o in scene.objects:
    if o.type=='MESH':uv_for(o,'atlas' if o.name.startswith(('ROAD_','LAND_','GAME_Outer')) else 'paint' if o.name.startswith(('LINE_','ARROW_')) else 'box')

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4
scene.render.bake.margin=4;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=True
# Bake the original node colors without lighting, keeping UV and object-space geometry fixed.
def bake_color(objects,filename,size,channel='Base Color'):
    image=bpy.data.images.new(filename,width=size,height=size,alpha=True)
    image.colorspace_settings.name='sRGB' if channel=='Base Color' else 'Non-Color'
    restore=[]
    for mat in set(m for o in objects for m in o.data.materials if m):
        nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
        old=out.inputs['Surface'].links[0].from_socket
        em=nt.nodes.new('ShaderNodeEmission');sock=bs.inputs[channel]
        if sock.is_linked:nt.links.new(sock.links[0].from_socket,em.inputs['Color'])
        else:
            vv=sock.default_value;em.inputs['Color'].default_value=vv if hasattr(vv,'__len__') else (vv,vv,vv,1)
        nt.links.new(em.outputs[0],out.inputs['Surface'])
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.nodes.active=tex
        restore.append((nt,out,old,em,tex))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(TEX/filename);image.file_format='PNG';image.save()
    for nt,out,old,em,tex in restore:
        nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em);nt.nodes.remove(tex)
    print('Baked',filename,flush=True);return image
roads=[bpy.data.objects[n] for n in ['ROAD_Flat_Concrete','ROAD_Flat_Asphalt','ROAD_HillRamp']]
# One temporary bake mesh prevents padding from separate bakes overwriting adjacent materials.
vs=[];fs=[];mis=[];roadmats=[bpy.data.materials[n] for n in ['C1_Weathered_light_concrete','C1_Connector_asphalt']]
for o in roads:
    k=len(vs);vs.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices]);fs.extend([tuple(k+i for i in p.vertices) for p in o.data.polygons]);mis.extend([roadmats.index(o.data.materials[0])]*len(o.data.polygons))
baker=make_mesh('BAKE_RoadAtlas',vs,fs,roadmats[0]);baker.data.materials.append(roadmats[1])
for p,mi in zip(baker.data.polygons,mis):p.material_index=mi
uv_for(baker);roadimage=bake_color([baker],'road_atlas.color.png',4096)
bpy.data.objects.remove(baker,do_unlink=True)
baker=make_mesh('BAKE_Ground',[(-10,0,-.03),(80,0,-.03),(80,60,-.03),(-10,60,-.03)],[(0,1,2,3)],bpy.data.materials['C1_Grass_ground']);uv_for(baker)
groundimage=bake_color([baker],'grass_atlas.color.png',2048);bpy.data.objects.remove(baker,do_unlink=True)
baker=make_mesh('BAKE_Paint',[(0,0,0),(2,0,0),(2,2,0),(0,2,0)],[(0,1,2,3)],bpy.data.materials['C1_Offwhite_road_paint']);uv_for(baker,'paint')
paintimage=bake_color([baker],'paint.color.png',512);alpha=bake_color([baker],'paint_alpha.data.png',512,'Alpha')
import numpy as np
rgba=np.array(paintimage.pixels[:],dtype=np.float32).reshape(-1,4);rgba[:,3]=np.array(alpha.pixels[:],dtype=np.float32).reshape(-1,4)[:,0]
paintimage.pixels.foreach_set(rgba.ravel());paintimage.save();bpy.data.objects.remove(baker,do_unlink=True)
# Portable PBR factors. Road/grass/paint use the baked original colors.
matkeys={'C1_Weathered_light_concrete':'concrete','C1_Connector_asphalt':'asphalt','C1_Grass_ground':'grass',
'C1_Offwhite_road_paint':'white','C1_Safety_yellow':'yellow','C1_Curb_charcoal':'black','C1_Expansion_joint':'joint',
'C1_Galvanised_steel':'metal','C1_Sign_blue':'blue','C1_Rendered_masonry':'masonry','C1_Concrete_repairs':'repair',
'C1_Subtle_rubber_scuffs':'tire','C1_Dry_soil':'soil','C1_Tree_bark':'bark',**{f'C1_Leaves_{i}':f'leaves{i}' for i in range(3)}}
materials={};mapping={}
for name,key in matkeys.items():
    mat=bpy.data.materials[name];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    color=list(bs.inputs['Base Color'].default_value)
    ramps=[n for n in mat.node_tree.nodes if n.type=='VALTORGB']
    if bs.inputs['Base Color'].is_linked and ramps:
        color=list(np.mean([list(e.color) for e in ramps[0].color_ramp.elements],axis=0));color[3]=1.
    tex='road_atlas.color.png' if key in ['concrete','asphalt'] else 'grass_atlas.color.png' if key=='grass' else 'paint.color.png' if key=='white' else None
    if tex:color=[1,1,1,1]
    ground='C1V1_CONCRETE' if key in ['concrete','yellow','black','masonry','repair'] else 'ASPHALT' if key=='asphalt' else 'GRASS' if key.startswith(('grass','leaves')) else 'DIRT' if key=='soil' else 'METAL' if key=='metal' else 'WOOD' if key=='bark' else 'ASPHALT'
    target='c1v1_'+key;mapping[name]=target
    materials[target]={'color':color,'roughness':float(bs.inputs['Roughness'].default_value),'metallic':float(bs.inputs['Metallic'].default_value),'ground':ground,'texture':tex,'doubleSided':key.startswith('leaves'),'alphaTest':key=='white'}
    # Rewire the export-copy viewport for previewing the same color data as the game.
    if tex:
        nt=mat.node_tree;n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.get(tex);nt.links.new(n.outputs['Color'],bs.inputs['Base Color'])
        if key=='white':nt.links.new(n.outputs['Alpha'],bs.inputs['Alpha'])
    else:
        for link in list(bs.inputs['Base Color'].links):mat.node_tree.links.remove(link)
        bs.inputs['Base Color'].default_value=color

report={'source_blend':str(SOURCE),'source_sha256':source_sha,'target_game':'BeamNG.drive 0.39','level_id':LEVEL,
'units':'metres','up_axis':'Z_UP','beamng_runtime_tested':False,'assets':{},'excluded_objects':excluded,
'paint_height_m':.006,'detail_height_m':.004,'source_dimensions_unchanged':True,'instances':[],'materials':materials}
removed=defaultdict(int)
def collect(objects,pre=None,low_tree=False):
    triangles=[];dg=bpy.context.evaluated_depsgraph_get();pre=pre or Matrix.Identity(4)
    for o in objects:
        if low_tree and '_Twig_' in o.name:continue
        eo=o.evaluated_get(dg);m=eo.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
        if not m:continue
        m.calc_loop_triangles();mw=pre@o.matrix_world;nm=mw.to_3x3().inverted().transposed()
        pts=[mw@v.co for v in m.vertices];norms=[(nm@n.vector).normalized() for n in m.corner_normals]
        uv=m.uv_layers.get('BeamNG_UV')
        for t in m.loop_triangles:
            if low_tree and 'IndividualLeaves' in o.name and t.polygon_index%3:continue
            pp=[pts[i] for i in t.vertices];cross=(pp[1]-pp[0]).cross(pp[2]-pp[0])
            if cross.length<1e-9:removed[o.name]+=1;continue
            n=[norms[i] for i in t.loops]
            # Deform-safe source normals for gameplay surfaces.
            if o.name.startswith('ROAD_') and cross.z<0:
                pp[1],pp[2]=pp[2],pp[1];cross=-cross
            if o.name.startswith('ROAD_'):n=[cross.normalized()]*3
            u=[tuple(uv.data[i].uv) for i in t.loops] if uv else [(p.x/2,p.z/2) for p in pp]
            mat=m.materials[t.material_index];target=mapping[mat.name]
            triangles.append(([tuple(p) for p in pp],[tuple(v) for v in n],u,target))
        eo.to_mesh_clear()
    return triangles
I=[1,0,0,0,1,0,0,0,1]
items=[{'class':'LevelInfo','name':'theLevelInfo','gravity':-9.80665,'nearClip':.05,'visibleDistance':1200,'fogDensity':0,'fogAtmosphereHeight':1000},
{'class':'TimeOfDay','name':'tod','startTime':.15,'time':.15,'play':False,'dayLength':1800},
{'class':'ScatterSky','name':'sunsky','rayleighScattering':.0025,'sunSize':1.0}]
def add_asset(name,objects,collide=False,colliders=None,levels=None,position=None,scale=None):
    high=collect(objects) if levels is None else levels[max(levels)]
    lods=levels or {1:high};col=collect(colliders) if colliders is not None else high if collide else []
    stats=write_dae(SHAPES/(name+'.dae'),name,lods,col,materials)
    report['assets'][name]={'source_objects':[o.name for o in objects],'nodes':stats,'render_triangles':len(high),'collision_triangles':len(col)}
    if position is not False:
        item={'class':'TSStatic','name':'c1_'+name,'shapeName':f'/levels/{LEVEL}/art/shapes/{name}.dae','position':position or [0,0,0],'rotationMatrix':I,'scale':scale or [1,1,1],
        'collisionType':'Collision Mesh' if col else 'None','decalType':'Collision Mesh' if col else 'None','isRenderEnabled':True,'canSave':True}
        items.append(item);report['instances'].append(item)
    print('Exported',name,'visual',len(high),'collision',len(col),flush=True)
for name in ['ROAD_Flat_Concrete','ROAD_Flat_Asphalt','ROAD_HillRamp']:add_asset(name.lower(),[bpy.data.objects[name]],True)
add_asset('hill_retaining',[bpy.data.objects['BED_Hill_Retaining']],True)
add_asset('curbs',[bpy.data.objects['CURBS_BlackYellow']],True)
add_asset('site_ground',[bpy.data.objects['LAND_Site90x60']],True)
add_asset('outer_ground',[outer],True)
add_asset('markings',list(bpy.data.collections['02_Markings'].objects))
fac=list(bpy.data.collections['03_Facilities'].objects)
add_asset('surface_details',[o for o in fac if o.name.startswith(('DETAIL_','DRAIN_','RETAINING_'))])
add_asset('signs',[o for o in fac if o.name.startswith('SIGN_')],colliders=[o for o in fac if o.name.startswith(('SIGN_Post_','SIGN_Board_'))])
# One thin solid panel for each existing fence run, avoiding 800 tiny physics objects.
proxies=[]
for i,(x1,y1,x2,y2) in enumerate([(-9.7,59.7,79.7,59.7),(79.7,.3,79.7,59.7),(-9.97,.3,-9.97,26.5),(-9.97,33.5,-9.97,59.7)]):
    a=Vector((x1,y1,0));b=Vector((x2,y2,0));t=(b-a).normalized();n=Vector((-t.y,t.x,0))*.025
    points=[a-n,b-n,b+n,a+n];vs=[tuple(p+Vector((0,0,z))) for z in [0,1.3] for p in points]
    o=make_mesh('COL_Fence_'+str(i),vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],bpy.data.materials['C1_Galvanised_steel']);uv_for(o,'box');proxies.append(o)
add_asset('fence',[o for o in fac if o.name.startswith('FENCE_')],colliders=proxies)
for o in proxies:o.hide_render=True;o.hide_set(True)
land=list(bpy.data.collections['04_Landscape'].objects)
add_asset('grass_tufts',[o for o in land if o.name=='GRASS_SparseTufts'])
trees=[o for o in land if o.name.startswith('TREE_V07_0_')]
x,y,s=G['vegetation'][0];pre=Matrix.Scale(1/s,4)@Matrix.Translation(Vector((-x,-y,0)))
lods={150:collect(trees,pre),1:collect(trees,pre,True)}
col=collect([o for o in trees if 'Trunk' in o.name],pre)
report['assets']['tree']={'source_objects':[o.name for o in trees],'nodes':write_dae(SHAPES/'tree.dae','tree',lods,col,materials),'render_triangles':len(lods[150]),'collision_triangles':len(col)}
for i,(x,y,s) in enumerate(G['vegetation']):
    item={'class':'TSStatic','name':'c1_tree_'+str(i),'shapeName':f'/levels/{LEVEL}/art/shapes/tree.dae','position':[x,y,0],'rotationMatrix':I,'scale':[s,s,s],'collisionType':'Collision Mesh','decalType':'None','isRenderEnabled':True}
    items.append(item);report['instances'].append(item)
# Grass blades are single-sided triangles in Blender; the game material needs both sides.
materials['c1v1_leaves1']['doubleSided']=True
spawns=[('spawns_default','Exam Start / 考试入口',[9,10,.65]),('spawns_main','Main Road / 大路',[30,43.5,.65]),('spawns_scurve','S Curve / 曲线行驶入口',[45,10,.65])]
for name,title,p in spawns:items.append({'class':'SpawnSphere','name':name,'dataBlock':'SpawnSphereMarker','position':p,'rotationMatrix':[0,-1,0,1,0,0,0,0,1],'scale':[1,1,1]})
(ROOT/'main/MissionGroup').mkdir(exist_ok=True)
(ROOT/'main/items.level.json').write_text(json.dumps({'class':'SimGroup','name':'MissionGroup'})+'\n')
(ROOT/'main/MissionGroup/items.level.json').write_text('\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in items)+'\n')
game_mats={}
for name,m in materials.items():
    stage={'baseColorFactor':m['color'],'roughnessFactor':m['roughness'],'metallicFactor':m['metallic']}
    if m['texture']:stage['baseColorMap']=f'/levels/{LEVEL}/art/textures/'+m['texture']
    game_mats[name]={'name':name,'class':'Material','mapTo':name,'version':1.5,'Stages':[stage,{},{},{}],
    'groundType':m['ground'],'doubleSided':m['doubleSided'],'translucent':False,'alphaTest':m['alphaTest'],'alphaRef':128,'useAnisotropic':True,'materialTag0':'Road and Path'}
(ROOT/'main.materials.json').write_text(json.dumps(game_mats,ensure_ascii=False,indent=2))
(ROOT/'groundModels/c1_dry_concrete.json').write_text(json.dumps({'C1V1_CONCRETE':{'staticFrictionCoefficient':1,'slidingFrictionCoefficient':.8,'hydrodynamicFriction':.01,'stribeckVelocity':6,'strength':1,'roughnessCoefficient':0,'defaultDepth':0,'shearStrength':0,'collisiontype':'ASPHALT','skidMarks':True}},indent=2))
(ROOT/'info.json').write_text(json.dumps({'title':'China C1 Subject 2 - Closed Loop','description':'C1 科目二闭环训练场：五项各一处，平面发卡弯与大路，10% 坡道。Built for BeamNG.drive 0.39; offline-checked, game testing pending.','authors':'Custom C1 training ground project','size':[390,320],'previews':['preview.jpg'],'defaultSpawnPointName':'spawns_default','spawnPoints':[{'translationId':t,'objectname':n,'description':t,'preview':'preview.jpg'} for n,t,p in spawns],'supportsTraffic':False,'supportsTimeOfDay':True,'roadRules':{'rightHandDrive':False}},ensure_ascii=False,indent=2))
report['removed_degenerate_triangles']=dict(removed);report['spawn_points']=[{'name':n,'position':p,'intended_forward':[1,0,0]} for n,t,p in spawns]
report['collision_note']='Dedicated Colmesh nodes; exact low-poly driving surfaces and curbs, simplified fence panels, tree trunks only. No paint, grass or leaf collision.'
report['physics_note']='Dry concrete baseline; uncalibrated, no wet simulation or exam scoring logic.'
(D/'export_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Save a separate game asset workspace; do not include it in the installation ZIP.
scene['scope']='BeamNG 0.39 export-copy; original V07 unchanged; runtime testing pending'
scene.camera=bpy.data.objects['CAM_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.cycles.samples=24
bpy.ops.file.make_paths_relative();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_game_assets.blend'))
print('EXPORT COMPLETE',flush=True)
