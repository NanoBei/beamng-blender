"""Independent Collada readback and BeamNG package reference checks."""
import sys, json, math, hashlib, zipfile, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, '/private/tmp/beamng-dae-validator')
import collada

OUT=Path(__file__).resolve().parent
PACKAGE=OUT/'package'
temporary_package=None
if not (PACKAGE/'levels'/'tight_hairpin_drive_v3'/'info.json').is_file():
    temporary_package=tempfile.TemporaryDirectory(prefix='hairpin-v2-audit-')
    PACKAGE=Path(temporary_package.name)
    with zipfile.ZipFile(OUT/'tight_hairpin_drive_v3.zip') as z:
        assert all(n.startswith('levels/tight_hairpin_drive_v3/') and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(PACKAGE)
LEVEL=PACKAGE/'levels'/'tight_hairpin_drive_v3'
report=json.loads((OUT/'export_report.json').read_text())
materials=json.loads((LEVEL/'main.materials.json').read_text())
results={}
for path in sorted(LEVEL.rglob('*.dae')):
    dae=collada.Collada(str(path), ignore=[])
    assert dae.scene is not None and not dae.errors, (path,dae.errors)
    bounds=[]; tri_count=0; min_road_normal_z=1
    instances=list(dae.scene.objects('geometry'))
    assert len(instances)==len(report['assets'][path.stem])
    for inst in instances:
        for primitive in inst.primitives():
            vertices=primitive.vertex
            assert np.isfinite(vertices).all()
            assert np.isfinite(primitive.normal).all()
            assert np.isfinite(primitive.texcoordset[0]).all()
            assert primitive.texcoordset[0].min()>-.01 and primitive.texcoordset[0].max()<1.02
            assert primitive.material.name in materials
            triangles=vertices[primitive.vertex_index]
            cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            area=np.linalg.norm(cross,axis=1)
            assert (area>1e-8).all()
            tri_count+=len(triangles); bounds.append(vertices)
            if path.stem in ['main_road','small_road']:
                assert (cross[:,2]>0).all(), 'Road has inverted driving triangles'
                main=vertices[vertices[:,1]>=42-1e-6]
                if len(main): assert np.abs(main[:,2]).max()<1e-6
                min_road_normal_z=min(min_road_normal_z,float((cross[:,2]/area).min()))
    assert tri_count==sum(x['triangles'] for x in report['assets'][path.stem])
    points=np.concatenate(bounds)
    results[path.name]={'instances':len(instances),'triangles':tri_count,'bounds_min':points.min(0).tolist(),'bounds_max':points.max(0).tolist(),'parsed_by':'pycollada 0.9.3'}
    if path.stem in ['main_road','small_road']: results[path.name]['min_upward_normal_z']=min_road_normal_z

items=[json.loads(line) for line in (LEVEL/'main'/'items.level.json').read_text().splitlines()]
names=[item['name'] for item in items]
assert len(names)==len(set(names))
info=json.loads((LEVEL/'info.json').read_text())
assert info['defaultSpawnPointName'] in names
assert all(s['objectname'] in names for s in info['spawnPoints'])
def verify_paths(value):
    if isinstance(value,dict):
        for v in value.values(): verify_paths(v)
    elif isinstance(value,list):
        for v in value: verify_paths(v)
    elif isinstance(value,str) and value.startswith('/levels/'):
        assert (PACKAGE/value.lstrip('/')).is_file(),value
for obj in [materials,items]: verify_paths(obj)
for item in items:
    if item['class']=='TSStatic':
        assert item['collisionType'] in ['None','Visible Mesh Final']
        assert item['scale']==[1,1,1]
        assert item['rotationMatrix']==[1,0,0,0,1,0,0,0,1]
for preview in info['previews']: assert (LEVEL/preview).is_file()
with Image.open(LEVEL/'art'/'textures'/'terrain.color.png') as im:
    assert im.size==(2048,2048)
    rgb=np.array(im.convert('RGB'))
    assert rgb.std()>10
    results['terrain_texture']={'size':list(im.size),'rgb_min':rgb.min(axis=(0,1)).tolist(),'rgb_max':rgb.max(axis=(0,1)).tolist()}

def triangles(asset):
    data=collada.Collada(str(LEVEL/'art'/'shapes'/f'{asset}.dae'))
    return [(inst.original.id,primitive.vertex[primitive.vertex_index].astype(float),primitive)
            for inst in data.scene.objects('geometry') for primitive in inst.primitives()]

road_tri=np.concatenate([x[1] for x in triangles('small_road')])
terrain_tri=np.concatenate([x[1] for x in triangles('terrain')])
def ray_height(tris,x,y):
    mask=(tris[:,:,0].min(1)<=x+1e-7)&(tris[:,:,0].max(1)>=x-1e-7)&(tris[:,:,1].min(1)<=y+1e-7)&(tris[:,:,1].max(1)>=y-1e-7)
    t=tris[mask]
    if not len(t):return None
    a=t[:,1,:2]-t[:,0,:2];b=t[:,2,:2]-t[:,0,:2];p=np.array([x,y])-t[:,0,:2]
    den=a[:,0]*b[:,1]-a[:,1]*b[:,0];good=abs(den)>1e-12
    t,a,b,p,den=t[good],a[good],b[good],p[good],den[good]
    u=(p[:,0]*b[:,1]-p[:,1]*b[:,0])/den;v=(a[:,0]*p[:,1]-a[:,1]*p[:,0])/den
    inside=(u>=-1e-5)&(v>=-1e-5)&(u+v<=1+1e-5)
    z=t[:,0,2]+u*(t[:,1,2]-t[:,0,2])+v*(t[:,2,2]-t[:,0,2])
    return float(z[inside].max()) if inside.any() else None

def cross2(a,b):return a[0]*b[1]-a[1]*b[0]
def convex_hull(points):
    pts=sorted(set(map(tuple,points)));lower=[];upper=[]
    for target,seq in [(lower,pts),(upper,reversed(pts))]:
        for p in seq:
            while len(target)>=2 and cross2(np.subtract(target[-1],target[-2]),np.subtract(p,target[-1]))<=0:target.pop()
            target.append(p)
    return np.array(lower[:-1]+upper[:-1])
def overlap_area(triangle,hull):
    polygon=list(triangle)
    for a,b in zip(hull,np.roll(hull,-1,axis=0)):
        if not polygon:return 0
        out=[];previous=polygon[-1];pd=cross2(b-a,previous-a)
        for current in polygon:
            cd=cross2(b-a,current-a)
            if (cd>=0)!=(pd>=0):out.append(previous+(current-previous)*pd/(pd-cd))
            if cd>=0:out.append(current)
            previous,pd=current,cd
        polygon=out
    return abs(sum(cross2(a,b) for a,b in zip(polygon,polygon[1:]+polygon[:1])))*.5 if polygon else 0

rock_audit=[]
for name,tris,primitive in triangles('roadside_rocks'):
    edges={}
    for tri in primitive.vertex_index:
        for a,b in zip(tri,np.roll(tri,-1)):
            edge=tuple(sorted((int(a),int(b))));edges[edge]=edges.get(edge,0)+1
    assert all(count==2 for count in edges.values()),name
    volume=float(np.einsum('ij,ij->i',tris[:,0],np.cross(tris[:,1],tris[:,2])).sum()/6)
    assert volume>0
    hull=convex_hull(tris[:,:,:2].reshape(-1,2));lo=hull.min(0);hi=hull.max(0)
    mask=(road_tri[:,:,0].max(1)>lo[0])&(road_tri[:,:,0].min(1)<hi[0])&(road_tri[:,:,1].max(1)>lo[1])&(road_tri[:,:,1].min(1)<hi[1])
    overlap=sum(overlap_area(t[:,:2],hull) for t in road_tri[mask])
    assert overlap<1e-5,(name,overlap)
    centre=tris.reshape(-1,3).mean(0);top=ray_height(tris,*centre[:2]);earth=ray_height(terrain_tri,*centre[:2])
    rock_audit.append({'geometry':name,'closed':True,'volume_m3':volume,'pavement_overlap_m2':overlap,'height_above_soil_at_center_m':None if earth is None or top is None else top-earth})
results['rock_collision_audit']=rock_audit
results['visibly_exposed_rock_centres']=sum(r['height_above_soil_at_center_m'] is not None and r['height_above_soil_at_center_m']>.01 for r in rock_audit)
assert results['visibly_exposed_rock_centres']>=20
checks=[]
for sample in report['source_parameters']['cliff_ray_checks']:
    x,y=sample['sample_xy'];z=ray_height(terrain_tri,x,y)
    assert z is not None and ray_height(road_tri,x,y) is None
    drop=sample['edge'][2]-z
    assert abs(drop-sample['drop_after_m'])<.002
    checks.append(drop)
# Independently measure the exported paved widths, excluding channels.
main_tri=np.concatenate([x[1] for x in triangles('main_road')])
assert abs(main_tri[:,:,1].max()-main_tri[:,:,1].min()-5)<1e-6
assert np.abs(main_tri[:,:,2]).max()<1e-6
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments
widths=[]
for seg,along in [(segments[0],12),(segments[0],15),(segments[2],5),(segments[2],7),(segments[4],5),(segments[4],11)]:
    q=seg['start']+along*seg['t'];sides=[]
    for sign in [-1,1]:
        lo,hi=0.,2.
        for _ in range(25):
            d=(lo+hi)/2;p=q+sign*d*seg['n']
            if ray_height(road_tri,*p) is not None:lo=d
            else:hi=d
        sides.append((lo+hi)/2)
    widths.append(sum(sides))
assert all(abs(w-3)<.002 for w in widths),widths
results['measured_main_paved_width_m']=5.
results['measured_small_straight_widths_m']=widths
# Read back actual channel floors and fill strips to rule out hidden support.
drain_tri=np.concatenate([x[1] for x in triangles('drainage')])
drain_checks=[]
for sample in report['small_drain_floor_checks']:
    x,y=sample['xy'];floor=ray_height(drain_tri,x,y);soil=ray_height(terrain_tri,x,y)
    assert floor is not None and abs(floor-sample['floor_z'])<.002,(sample,floor)
    assert soil is None or soil<floor-.015,(sample,soil,floor)
    assert ray_height(road_tri,x,y) is None
    assert abs(sample['lip_z']-floor-.6)<.002
    drain_checks.append({'xy':[x,y],'depth_m':sample['lip_z']-floor,'soil_height':soil})
results['small_channel_readback']=drain_checks
for sample in report['filled_shoulder_checks']:
    x,y=sample['xy'];z=ray_height(terrain_tri,x,y)
    assert z is not None and abs(z-sample['z'])<.004,(sample,z)
    assert ray_height(drain_tri,x,y) is None
results['filled_shoulder_readback_count']=len(report['filled_shoulder_checks'])
# Each newly shortened rail proxy must remain closed and outward oriented.
small_rail_names=[]
for entry,(name,tris,primitive) in zip(report['assets']['guardrails_collision'],triangles('guardrails_collision')):
    edges={}
    for tri in primitive.vertex_index:
        for a,b in zip(tri,np.roll(tri,-1)):
            edge=tuple(sorted((int(a),int(b))));edges[edge]=edges.get(edge,0)+1
    assert all(v==2 for v in edges.values()),entry['object']
    volume=np.einsum('ij,ij->i',tris[:,0],np.cross(tris[:,1],tris[:,2])).sum()/6
    assert volume>0,entry['object']
    if entry['object'].startswith('COL_Guardrail_'):
        assert tris[:,:,1].min()>41.4 and tris[:,:,1].max()<42.,entry['object']
        assert tris[:,:,0].min()>-.08 and tris[:,:,0].max()<44.08,entry['object']
    if entry['object'].startswith('COL_V16_'):
        assert tris[:,:,1].min()>31 and tris[:,:,1].max()<34,entry['object']
        assert tris[:,:,0].min()>16 and tris[:,:,0].max()<25,entry['object']
    if entry['object'].startswith('COL_V16_'):small_rail_names.append(entry['object'])
assert len(small_rail_names)==9
results['new_small_guardrail_closed_proxies']=small_rail_names
results['cliff_drop_samples_m']=checks
assert np.median(checks)>.7
by_name={i['name']:i for i in items}
assert by_name['hairpin3_roadside_rocks']['collisionType']=='Visible Mesh Final'
assert by_name['hairpin3_guardrails_collision']['collisionType']=='Visible Mesh Final'
assert by_name['hairpin3_guardrails_collision']['isRenderEnabled'] is False
for asset in ['guardrails_visual','vegetation','concrete_joints','earth_sides']:
    assert by_name['hairpin3_'+asset]['collisionType']=='None'
assert set(report['assets'])=={'main_road','small_road','terrain','drainage','roadside_rocks','guardrails_visual','guardrails_collision','vegetation','concrete_joints','earth_sides'}
ground=json.loads((LEVEL/'groundModels'/'hairpin_dry_concrete.json').read_text())
assert materials['hp3_concrete']['groundType'] in ground
assert all(not entry['object'].startswith(('A4L','REFERENCE','Presentation','Terrain_Block_Bottom')) for entries in report['assets'].values() for entry in entries)
results['collision_triangles']=sum(results[f'{asset}.dae']['triangles'] for asset in ['main_road','small_road','terrain','drainage','roadside_rocks','guardrails_collision'])

archive=OUT/'tight_hairpin_drive_v3.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_file(): z.write(path,path.relative_to(PACKAGE).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(name.startswith('levels/tight_hairpin_drive_v3/') for name in z.namelist())
    results['archive_files']=z.namelist()
results['zip_bytes']=archive.stat().st_size
results['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
results['beamng_runtime_tested']=False
(OUT/'validation_report.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
