"""Calibrate the supplied C63 mesh and replace only the V13 reference collection.

Run Blender with --disable-autoexec and the source .blend open. The source file
has no embedded texts; freeze evaluated meshes to remove old wheel drivers.
"""
import bpy, math, json, hashlib, os
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

OUT=Path(__file__).resolve().parent
SOURCE=OUT/'source/Mercedes AMG C63.blend'
ROAD_SOURCE=Path(os.environ.get('C63_ROAD_SOURCE',str(OUT.parent/'blender_trial_v13_a4l_reference/road_trial_v13_a4l_reference.blend')))
COLNAME='REFERENCE_Mercedes_AMG_C63_EXCLUDE_FROM_MAP'
TARGET={'length':4.756,'body_width':1.839,'mirror_width':2.020,'height':1.426,'wheelbase':2.840}
AUTHOR='wishingchain'
URL='https://free3d.com/3d-model/mercedes-amg-c63-hi-poly-model-partially-rigged-805791.html'
SPEC='https://static.oneweb.mercedes-benz.com/css-oom-assets/en-lb/pdf/mercedes-amg-c-class-owners-manual-supplement-june-2018-1.pdf'
KEEP=['body.003','Plane','Tail lights','Front lights','Upper Grille','Lower Grille',
      'back  left tire','back right tire','Front right tire.','Front left tire']

def mesh_points(o):
    p=np.empty((len(o.data.vertices),3));o.data.vertices.foreach_get('co',p.ravel());return p

def components(me):
    parents=list(range(len(me.vertices)))
    def find(i):
        while i!=parents[i]:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for ed in me.edges:
        a,b=ed.vertices;parents[find(a)]=find(b)
    groups={}
    for i in range(len(parents)):groups.setdefault(find(i),[]).append(i)
    return list(groups.values())

def material(name,color,rough,metal,trans=0,coat=0,emission=0):
    m=bpy.data.materials.new('C63_V14_'+name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    p.inputs['Coat Weight'].default_value=coat;p.inputs['Coat Roughness'].default_value=.22
    p.inputs['Transmission Weight'].default_value=trans
    if emission:
        p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    m.diffuse_color=(*color,1);return m

materials={
 'bodypaint':material('Black_Metallic_Paint',(.032,.040,.049),.28,.55,coat=.38),
 'Window':material('Tinted_Windows',(.017,.027,.037),.23,.28),
 'Tires':material('Rubber',(.018,.021,.024),.78,0),
 'Alloy':material('Alloy_Chrome',(.46,.49,.52),.24,.85),
 'Trim':material('Grille_Trim',(.009,.012,.015),.4,.28),
 'Brake lights':material('Tail_Lens',(.37,.01,.008),.27,.18,emission=.12),
 'Glass(headlights)':material('Headlight_Clear_Lens',(.82,.88,.94),.15,0,trans=.86),
 'Headlight(Emission)':material('Headlight_Reflector',(.65,.73,.8),.24,.25,emission=.15),
}
scene=bpy.context.scene
for o in scene.objects:
    for mod in o.modifiers:
        if mod.type=='SUBSURF':mod.levels=mod.render_levels
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
frozen={}; raw={}; mirror_indices=[]
for name in KEEP:
    o=bpy.data.objects[name];e=o.evaluated_get(deps)
    me=bpy.data.meshes.new_from_object(e,preserve_all_data_layers=True,depsgraph=deps)
    me.transform(e.matrix_world)
    n=bpy.data.objects.new('C63_'+name.replace(' ','_').replace('.','_'),me)
    P=mesh_points(n);raw[name]=P.copy();frozen[name]=n
    if name=='body.003':
        for ids in components(me):
            C=P[ids];lo=C.min(0);hi=C.max(0)
            # Two disconnected mirror housings and two support stalks.
            if lo[1]>1.2 and hi[1]<1.8 and lo[2]>1.1 and max(abs(lo[0]),abs(hi[0]))>1:
                mirror_indices.extend(ids)
    for slot,m in enumerate(list(me.materials)):
        if m and m.name in materials:me.materials[slot]=materials[m.name]
    n['source_object']=name;n['source_author']=AUTHOR;n['reference_only']=True

assert mirror_indices,'Could not identify mirror components'
bodyP=raw['body.003'];body_mask=np.ones(len(bodyP),dtype=bool);body_mask[mirror_indices]=False
source_body=bodyP[body_mask]
allP=np.concatenate(list(raw.values()))
source_min=allP.min(0);source_max=allP.max(0)
front_names=[k for k in raw if 'Front' in k and 'tire' in k]
rear_names=[k for k in raw if 'back' in k and 'tire' in k]
centres={k:(raw[k].min(0)+raw[k].max(0))/2 for k in front_names+rear_names}
front_y=float(np.mean([centres[k][1] for k in front_names]));rear_y=float(np.mean([centres[k][1] for k in rear_names]))
sw=TARGET['body_width']/(source_body[:,0].max()-source_body[:,0].min())
sh=TARGET['height']/(source_max[2]-source_min[2])
# Rear and front overhangs from the period Mercedes dimension drawing.
source_y=[source_min[1],front_y,rear_y,source_max[1]]
target_x=[2.378,1.524,-1.316,-2.378]
mirror_shift=TARGET['mirror_width']/2-source_max[0]*sw
wheel_offsets={}
for name,o in frozen.items():
    P=raw[name];Q=np.column_stack((np.interp(P[:,1],source_y,target_x),P[:,0]*sw,(P[:,2]-source_min[2])*sh))
    if 'tire' in name.lower():
        c=centres[name];isfront=name in front_names;target_center=1.524 if isfront else -1.316
        # Preserve circular wheels, calibrating wheel centres independently of overhangs.
        Q[:,0]=target_center-(P[:,1]-c[1])*sh
        Q[:,2]=(P[:,2]-P[:,2].min())*sh
        wheel_offsets[name]=target_center
        o['axle']='front' if isfront else 'rear'
    if name=='body.003':
        M=np.array(mirror_indices);Q[M,1]+=np.sign(Q[M,1])*mirror_shift
        # Join the roots of the mirror supports to their original body attachment.
        for ids in components(o.data):
            if not body_mask[ids].any():
                C=P[ids]
                if C[:,2].min()<1.2:
                    t=(abs(C[:,0])-abs(C[:,0]).min())/max(np.ptp(abs(C[:,0])),1e-9)
                    Q[ids,1]-=np.sign(Q[ids,1])*mirror_shift*(1-t)
        attr=o.data.attributes.new('exclude_from_body_width','BOOLEAN','POINT')
        for i in mirror_indices:attr.data[i].value=True
    o.data.vertices.foreach_set('co',Q.ravel());o.data.update()

# Remove source cameras, planes, duplicate hidden body, controls, and source world.
for o in list(bpy.data.objects):
    if o not in frozen.values():bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
coll=bpy.data.collections.new(COLNAME);scene.collection.children.link(coll)
root=bpy.data.objects.new('REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm',None);coll.objects.link(root)
for o in frozen.values():coll.objects.link(o);o.parent=root
root['export_to_beamng']=False;root['source_author']=AUTHOR;root['source_url']=URL
root['license_note']='Free3D Personal Use License; source and derivative mesh kept local, excluded from public git'
root['specification_url']=SPEC
for k,v in TARGET.items():root[k+'_m']=v
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.name='Mercedes_AMG_C63_Reference_Only'
world=bpy.data.worlds.new('C63_Studio');world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.34,.34,.34,1);bg.inputs['Strength'].default_value=.6
scene.world=world

def camera(name,pos,target,scale):
    c=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(c)
    c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    c.data.type='ORTHO';c.data.ortho_scale=scale;return c

cam=camera('C63_Asset_Camera',(6.2,-4.6,3.5),(0,0,.65),7);scene.camera=cam
for name,pos,power,size in [('Key',(2,-3,6),900,5),('Fill',(-3,3,5),650,4)]:
    d=bpy.data.lights.new('C63_'+name,'AREA');d.energy=power;d.size=size
    l=bpy.data.objects.new('C63_'+name,d);scene.collection.objects.link(l);l.location=pos;l.rotation_euler=(Vector((0,0,.7))-l.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
bpy.context.view_layer.update()

def measure(collection):
    Ps=[];body_width_points=[];wheels={}
    for o in collection.objects:
        if o.type!='MESH':continue
        p=mesh_points(o);Ps.append(p)
        a=o.data.attributes.get('exclude_from_body_width')
        mask=np.array([not v.value for v in a.data]) if a else np.ones(len(p),dtype=bool)
        body_width_points.append(p[mask])
        if o.get('axle'):
            lo=p.min(0);hi=p.max(0);wheels[o.name]={'axle':o['axle'],'center':((lo+hi)/2).tolist(),'ground_z':float(lo[2]),'radius_xz':[(hi[0]-lo[0])/2,(hi[2]-lo[2])/2]}
    p=np.concatenate(Ps);bp=np.concatenate(body_width_points)
    length,width,height=p.max(0)-p.min(0)
    bw=np.ptp(bp[:,1]);wb=np.mean([w['center'][0] for w in wheels.values() if w['axle']=='front'])-np.mean([w['center'][0] for w in wheels.values() if w['axle']=='rear'])
    assert np.allclose([length,bw,width,height,wb],[4.756,1.839,2.020,1.426,2.840],atol=.00005),[length,bw,width,height,wb]
    assert all(abs(w['ground_z'])<.00005 for w in wheels.values())
    return {'length_m':float(length),'body_width_m':float(bw),'width_including_mirrors_m':float(width),'height_m':float(height),'wheelbase_m':float(wb),'wheels':wheels}

report={'source_blend_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_author':AUTHOR,'source_url':URL,
 'specification_url':SPEC,'target_dimensions_m':TARGET,'source_axis':{'forward':'-Y','up':'Z'},
 'correction':{'lateral_scale':sw,'vertical_scale':sh,'longitudinal_source_stations':source_y,'target_X_stations':target_x,'mirror_outward_shift_m':mirror_shift,'wheel_driver_baked':True,'subdivision':'source render level, baked'},
 'actual':measure(coll),'static_reference_only':True}
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.data.orphans_purge(do_recursive=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'mercedes_amg_c63_reference.blend'))

# Replace only the reference collection in the current road scene.
bpy.ops.wm.open_mainfile(filepath=str(ROAD_SOURCE))
scene=bpy.context.scene
def environment_signature():
    result={}
    for o in scene.objects:
        if o.type!='MESH' or any(c.name.startswith('REFERENCE_') for c in o.users_collection):continue
        payload=([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons],[list(r) for r in o.matrix_world],[m.name if m else None for m in o.data.materials])
        result[o.name]=hashlib.sha256(repr(payload).encode()).hexdigest()
    return result
before=environment_signature()
for c in list(bpy.data.collections):
    if c.name.startswith('REFERENCE_Audi_A4L'):
        for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)
with bpy.data.libraries.load(str(OUT/'mercedes_amg_c63_reference.blend'),link=False) as (src,dst):dst.collections=[COLNAME]
coll=dst.collections[0];scene.collection.children.link(coll)
root=next(o for o in coll.objects if o.type=='EMPTY');root.location=(7.5,44.25,0)
front=camera('Camera_V14_C63_Front',(13.5,39.6,3.5),(7.5,44.25,.7),7.5)
rear=camera('Camera_V14_C63_Rear',(1,40,3.3),(7.5,44.25,.7),7.5)
top=camera('Camera_V14_C63_Road_Scale',(7.5,44.25,20),(7.5,44.25,0),9)
report['actual_in_road_scene']=measure(coll)
report['road_and_environment_unchanged']=before==environment_signature()
report['environment_mesh_objects_verified']=len(before);assert report['road_and_environment_unchanged']
report['roads_m']={'main':4.5,'small':2.7705,'small_to_car_body_width_ratio':2.7705/1.839,
 'small_centered_straight_clearance_per_side_body_m':(2.7705-1.839)/2,
 'small_centered_straight_clearance_per_side_mirrors_m':(2.7705-2.020)/2}
(OUT/'geometry_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
for name,c,w,h in [('c63_front',front,1500,1000),('c63_rear',rear,1500,1000),('road_scale_top',top,1400,1000),('overview',bpy.data.objects['Camera_V11_Overview'],1500,1100)]:
    scene.camera=c;scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.camera=front;scene.render.resolution_x=1500;scene.render.resolution_y=1000
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v14_c63_reference.blend'))
print(json.dumps(report,indent=2))
