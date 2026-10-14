"""Independent Collada readback and BeamNG package reference checks."""
import sys, json, math, hashlib, zipfile
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, '/private/tmp/beamng-dae-validator')
import collada

OUT=Path(__file__).resolve().parent
PACKAGE=OUT/'package'
LEVEL=PACKAGE/'levels'/'tight_hairpin_test'
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
            assert primitive.material.name in materials
            triangles=vertices[primitive.vertex_index]
            cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            area=np.linalg.norm(cross,axis=1)
            assert (area>1e-8).all()
            tri_count+=len(triangles); bounds.append(vertices)
            if path.stem=='road':
                assert (cross[:,2]>0).all(), 'Road has inverted driving triangles'
                main=vertices[vertices[:,1]>=42-1e-6]
                assert np.abs(main[:,2]).max()<1e-6
                min_road_normal_z=min(min_road_normal_z,float((cross[:,2]/area).min()))
    assert tri_count==sum(x['triangles'] for x in report['assets'][path.stem])
    points=np.concatenate(bounds)
    results[path.name]={'instances':len(instances),'triangles':tri_count,'bounds_min':points.min(0).tolist(),'bounds_max':points.max(0).tolist(),'parsed_by':'pycollada 0.9.3'}
    if path.stem=='road': results[path.name]['min_upward_normal_z']=min_road_normal_z

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
        assert item['collisionType']=='Visible Mesh Final'
        assert item['scale']==[1,1,1]
        assert item['rotationMatrix']==[1,0,0,0,1,0,0,0,1]
for preview in info['previews']: assert (LEVEL/preview).is_file()
with Image.open(LEVEL/'art'/'textures'/'terrain.color.png') as im:
    assert im.size==(2048,2048)
    rgb=np.array(im.convert('RGB'))
    assert rgb.std()>10
    results['terrain_texture']={'size':list(im.size),'rgb_min':rgb.min(axis=(0,1)).tolist(),'rgb_max':rgb.max(axis=(0,1)).tolist()}

archive=OUT/'tight_hairpin_test_v1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_file(): z.write(path,path.relative_to(PACKAGE).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(name.startswith('levels/tight_hairpin_test/') for name in z.namelist())
    results['archive_files']=z.namelist()
results['zip_bytes']=archive.stat().st_size
results['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
results['beamng_runtime_tested']=False
(OUT/'validation_report.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
