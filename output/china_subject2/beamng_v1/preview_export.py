"""Render actual exported DAE+material JSON readback, not the original authoring meshes."""
import bpy,json,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector,Matrix
D=Path(__file__).resolve().parent;ROOT=D/'package/levels/china_c1_subject2_v1'
R=json.loads((D/'export_report.json').read_text());M=json.loads((ROOT/'main.materials.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(D/'china_subject2_game_assets.blend'),use_scripts=False)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_dae_readback.blend'))
for o in list(bpy.context.scene.objects):
    if o.type not in {'LIGHT','CAMERA'}:bpy.data.objects.remove(o,do_unlink=True)
mat={}
for key,data in M.items():
    m=bpy.data.materials.new('BEAM_'+key);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');s=data['Stages'][0]
    bs.inputs['Base Color'].default_value=s['baseColorFactor'];bs.inputs['Roughness'].default_value=s['roughnessFactor'];bs.inputs['Metallic'].default_value=s['metallicFactor']
    if s.get('baseColorMap'):
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(D/'package'/s['baseColorMap'].lstrip('/')),check_existing=True);m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        if data.get('alphaTest'):
            mathnode=m.node_tree.nodes.new('ShaderNodeMath');mathnode.operation='GREATER_THAN';mathnode.inputs[1].default_value=data['alphaRef']/255;m.node_tree.links.new(tex.outputs['Alpha'],mathnode.inputs[0]);m.node_tree.links.new(mathnode.outputs[0],bs.inputs['Alpha'])
    mat[key]=m
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'};meshes={}
for asset,stats in R['assets'].items():
    tree=ET.parse(ROOT/'art/shapes'/f'{asset}.dae');target_lod=150 if asset=='tree' else 1
    selected=[]
    for node in tree.findall('.//c:visual_scene/c:node/c:node/c:node',ns):
        if not node.attrib['name'].endswith('_L'+str(target_lod)):continue
        inst=node.find('c:instance_geometry',ns)
        if inst is not None:selected.append(inst.attrib['url'][1:])
    meshes[asset]=[]
    for gid in selected:
        element=tree.find(f'.//c:geometry[@id="{gid}"]/c:mesh',ns)
        sources={}
        for s in element.findall('c:source',ns):
            vals=list(map(float,s.find('c:float_array',ns).text.split()));stride=int(s.find('c:technique_common/c:accessor',ns).attrib['stride']);sources[s.attrib['id']]=[tuple(vals[i:i+stride]) for i in range(0,len(vals),stride)]
        posid=element.find('c:vertices/c:input',ns).attrib['source'][1:];positions=sources[posid];faces=[];matids=[];slots=[];uvs={};norms={}
        for tr in element.findall('c:triangles',ns):
            target=tr.attrib['material']
            if target not in slots:slots.append(target)
            inputs={i.attrib['semantic']:i for i in tr.findall('c:input',ns)};stride=max(int(i.attrib['offset']) for i in inputs.values())+1
            ix=list(map(int,tr.find('c:p',ns).text.split()));rows=[ix[i:i+stride] for i in range(0,len(ix),stride)]
            for j in range(0,len(rows),3):
                face=[]
                for row in rows[j:j+3]:
                    vi=row[int(inputs['VERTEX'].attrib['offset'])];face.append(vi)
                    uvs[vi]=sources[inputs['TEXCOORD'].attrib['source'][1:]][row[int(inputs['TEXCOORD'].attrib['offset'])]]
                    norms[vi]=sources[inputs['NORMAL'].attrib['source'][1:]][row[int(inputs['NORMAL'].attrib['offset'])]]
                faces.append(face);matids.append(slots.index(target))
        mesh=bpy.data.meshes.new(gid);mesh.from_pydata(positions,[],faces);mesh.update()
        for key in slots:mesh.materials.append(mat[key])
        for p,idx in zip(mesh.polygons,matids):p.material_index=idx;p.use_smooth=True
        uv=mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
        mesh.normals_split_custom_set([norms[l.vertex_index] for l in mesh.loops])
        meshes[asset].append(mesh)
items=[json.loads(l) for l in (ROOT/'main/MissionGroup/items.level.json').read_text().splitlines()]
for item in items:
    if item['class']!='TSStatic':continue
    asset=Path(item['shapeName']).stem
    for j,mesh in enumerate(meshes[asset]):
        o=bpy.data.objects.new(item['name']+'_'+str(j),mesh);bpy.context.scene.collection.objects.link(o);o.location=item['position'];o.scale=item['scale']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='METAL'
    scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative();bpy.ops.wm.save_as_mainfile(filepath=str(D/'china_subject2_dae_readback.blend'))
for name,cam,size in [('01_game_assets_overview','CAM_Overview',(1600,1200)),('02_game_assets_top','CAM_Top',(1200,1680)),('03_game_assets_hill','CAM_Hill',(1600,1200))]:
    scene.camera=bpy.data.objects[cam];scene.render.resolution_x,scene.render.resolution_y=size;scene.render.filepath=str(D/'previews'/f'{name}.png');bpy.ops.render.render(write_still=True)
print('DAE readback previews complete',flush=True)
