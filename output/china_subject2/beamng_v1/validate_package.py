"""Independent pycollada readback; geometry, hierarchy, references and ZIP validation."""
import json,sys,math,hashlib,zipfile,re
from pathlib import Path
import numpy as np
from PIL import Image
D=Path(__file__).resolve().parent
for deps in [D/'.deps',Path('/private/tmp/beamng-dae-validator')]:
    if deps.exists():sys.path.insert(0,str(deps))
import collada
LEVEL='china_c1_subject2_v1';PACKAGE=D/'package';ROOT=PACKAGE/'levels'/LEVEL
R=json.loads((D/'export_report.json').read_text());G=json.loads((D.parent/'blender_v07/geometry_input.json').read_text())
materials=json.loads((ROOT/'main.materials.json').read_text())
# Package only a preview of the actual DAE/material readback.
with Image.open(D/'previews/01_game_assets_overview.png') as im:
    im.convert('RGB').resize((1200,900)).save(ROOT/'preview.jpg',quality=92)
(ROOT/'README_zh.txt').write_text((D/'Windows安装与试车说明.txt').read_text())
report={'target_game':'BeamNG.drive 0.39','beamng_runtime_tested':False,'checks':{},'failures':[],'assets':{}}
def require(name,ok,detail=None):
    report['checks'][name]={'passed':bool(ok),'detail':detail}
    if not ok:report['failures'].append(name)
def near(name,a,b,tol=.001):
    err=float(np.max(np.abs(np.array(a)-np.array(b))));require(name,err<=tol,{'actual':np.asarray(a).tolist(),'expected':np.asarray(b).tolist(),'max_error':err,'tolerance':tol})
read={}
for path in sorted((ROOT/'art/shapes').glob('*.dae')):
    dae=collada.Collada(str(path),ignore=[])
    require(path.stem+'_parses',not dae.errors and dae.scene is not None,[str(e) for e in dae.errors])
    require(path.stem+'_units',dae.assetInfo.unitmeter==1 and dae.assetInfo.upaxis=='Z_UP')
    node_stats=R['assets'][path.stem]['nodes'];by_gid={}
    for inst in dae.scene.objects('geometry'):
        entries=[]
        for p in inst.primitives():
            assert p.material.name in materials
            t=p.vertex[p.vertex_index].astype(float);n=p.normal[p.normal_index].astype(float);uv=p.texcoordset[0][p.texcoord_indexset[0]].astype(float)
            assert np.isfinite(t).all() and np.isfinite(n).all() and np.isfinite(uv).all()
            assert len(p.vertex)<=65535
            assert np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1).min()>5e-10
            entries.append((t,n,uv,p.material.name))
        by_gid[inst.original.id]=entries
    read[path.stem]=by_gid
    count=sum(len(t) for entries in by_gid.values() for t,n,u,m in entries)
    require(path.stem+'_counts',count==sum(s['triangles'] for s in node_stats),count)
    import xml.etree.ElementTree as ET
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'};xml=ET.parse(path)
    base=xml.find('.//c:visual_scene/c:node[@id="base00"]',ns)
    start=base.find('c:node[@id="start01"]',ns)
    require(path.stem+'_hierarchy',start is not None)
    has_col=R['assets'][path.stem]['collision_triangles']>0
    require(path.stem+'_collision_detail',(base.find('c:node[@id="collision-1"]',ns) is not None)==has_col)
    for node in start.findall('c:node',ns):
        name=node.attrib['name'];assert name.startswith('Colmesh_') and name.endswith('-1') or re.search(r'_L\d+$',name)
    report['assets'][path.stem]={'stored_triangles':count,'render_triangles':R['assets'][path.stem]['render_triangles'],'collision_triangles':R['assets'][path.stem]['collision_triangles'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def entries(asset,role='render'):
    return [v for gid,rows in read[asset].items() if ('_collision_' in gid)==(role=='collision') and (role=='collision' or '_L1_' in gid or asset=='tree' and '_L150_' in gid) for v in rows]
def tris(asset,role='render'):
    return np.concatenate([t for t,n,u,m in entries(asset,role)])
roadnames=['road_flat_concrete','road_flat_asphalt','road_hillramp']
road=np.concatenate([tris(a,'collision') for a in roadnames])
for a in roadnames:
    t=tris(a,'collision');v=tris(a,'render');near(a+'_collision_matches_render',t,v,1e-8)
    cr=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);require(a+'_upward',np.all(cr[:,2]>0))
    if 'flat' in a:near(a+'_flat_z',np.max(abs(t[:,:,2])),0,1e-7)
area=sum(abs(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])[:,2]).sum()/2 for t in [tris(a,'collision') for a in roadnames])
near('pavement_projected_area',area,G['geometry_preparation']['pavement_union_area_m2'],.005)
hill=tris('road_hillramp','collision');hp=hill.reshape(-1,3);near('hill_horizontal_length',np.ptp(hp[:,0]),G['hill']['total']);near('hill_height',hp[:,2].max(),G['hill']['height'])
xz=np.unique(hp[:,[0,2]],axis=0);xz=xz[np.argsort(xz[:,0])];slopes=np.diff(xz[:,1])/np.diff(xz[:,0]);station=G['hill']['start'][0]-xz[:,0];mask=(station[:-1]>3.1)&(station[1:]<22.8)
near('hill_constant_grade',[slopes[mask].min(),slopes[mask].max()],[-.1,-.1],.0003);near('hill_ends_at_ground',xz[[0,-1],1],[0,0]);require('hill_transitions',np.max(abs(np.diff(slopes)))<.003,float(np.max(abs(np.diff(slopes)))))
# Independent vertical intersection of actual DAE collision triangles.
road_min=road[:,:,:2].min(1);road_max=road[:,:,:2].max(1)
def ray(x,y,t=road,mins=road_min,maxs=road_max):
    mask=(mins[:,0]<=x+1e-6)&(maxs[:,0]>=x-1e-6)&(mins[:,1]<=y+1e-6)&(maxs[:,1]>=y-1e-6);q=t[mask]
    if not len(q):return None
    a=q[:,1,:2]-q[:,0,:2];b=q[:,2,:2]-q[:,0,:2];p=np.array([x,y])-q[:,0,:2];den=a[:,0]*b[:,1]-a[:,1]*b[:,0];ok=abs(den)>1e-12
    q,a,b,p,den=q[ok],a[ok],b[ok],p[ok],den[ok]
    u=(p[:,0]*b[:,1]-p[:,1]*b[:,0])/den;v=(a[:,0]*p[:,1]-a[:,1]*p[:,0])/den;ok=(u>=-1e-4)&(v>=-1e-4)&(u+v<=1+1e-4)
    z=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2]);return float(z[ok].max()) if ok.any() else None
bad=[];samples=0
for r in G['routes']:
    for x,y,h,w in r['rows'][::max(1,len(r['rows'])//100)]:
        for offset in [-w/2+.02,0,w/2-.02]:
            xx=x-math.sin(h)*offset;yy=y+math.cos(h)*offset;samples+=1
            if ray(xx,yy) is None:bad.append([r['name'],xx,yy])
require('loop_and_branches_full_width_support',not bad,{'samples':samples,'gaps':bad[:20]})
paint=tris('markings');pv=np.unique(paint.reshape(-1,3),axis=0)
# Compare all surviving exported paint points to the approved input, including the slope.
expected=np.array([p for m in G['markings'] if not m['name'].startswith('DETAIL_') for p in m['vertices']]);expected[:,2]+=.004
# Integer coordinate hashes avoid a scipy dependency; exact nearest distance for the handful of roundoff edges.
lookup={tuple(np.round(p/.0001).astype(int)) for p in expected};unmatched=[p for p in pv if tuple(np.round(p/.0001).astype(int)) not in lookup]
maxerr=max([float(np.linalg.norm(expected-p,axis=1).min()) for p in unmatched],default=0)
require('paint_preserves_approved_XYZ',maxerr<.001,{'vertices':len(pv),'max_unmatched_nearest_m':maxerr})
lifts=[];unsupported=[]
for x,y,z in pv[::max(1,len(pv)//3000)]:
    zz=ray(x,y)
    if zz is None:unsupported.append([x,y,z])
    else:lifts.append(z-zz)
require('paint_support',not unsupported,unsupported[:5]);near('paint_lift',[min(lifts),max(lifts)],[.006,.006],.0001)
# Cross-sections through exported paint verify net widths and bay boundaries.
# Sample the parallel lane beyond the bay opening; its opening dashes lie inside the lane.
# Sample the return straight away from its directional arrow.
def intervals(axis,value,low,high):
    result=[]
    for q in paint:
        if q[:,axis].min()>value or q[:,axis].max()<value:continue
        hit=[]
        for a,b in zip(q,np.roll(q,-1,axis=0)):
            if (a[axis]-value)*(b[axis]-value)<=0 and abs(b[axis]-a[axis])>1e-10:
                t=(value-a[axis])/(b[axis]-a[axis]);hit.append(float(a[1-axis]+t*(b[1-axis]-a[1-axis])))
        if len(hit)>=2 and low<=min(hit)<=max(hit)<=high:result.append([min(hit),max(hit)])
    merged=[]
    for a,b in sorted(result):
        if merged and a<=merged[-1][1]+1e-5:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    return merged
for name,axis,value,low,high,w in [('reverse_bay_width',1,3,10,18,2.447),('reverse_aisle_width',0,10,5,15,7.287),('parallel_bay_length',1,6.5,30,45,8.287),('parallel_lane_width',0,40,8,13,3.5705),('main_road_net_width',0,25,40,47,5),('return_road_net_width',1,27,-10,-4,4.5)]:
    it=intervals(axis,value,low,high);require(name+'_two_edges',len(it)==2,it)
    if len(it)==2:near(name,it[1][0]-it[0][1],w)
# Collision remains outside the net exam/road pavement, apart from support beds.
sys.path.insert(0,str(D.parent/'blender_v07/.deps'))
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
net=unary_union([Polygon(p['xy']) for p in G['net_footprints']]).buffer(-.001)
curb=tris('curbs','collision');centres=curb.mean(1)
require('curbs_outside_clear_width',not any(net.contains(Point(x,y)) for x,y,z in centres))
for asset in ['signs','fence','tree']:
    t=tris(asset,'collision');verts=t.reshape(-1,3)
    if asset=='tree':continue
    require(asset+'_collision_outside_lane',not any(net.contains(Point(x,y)) for x,y,z in verts))
# Ensure there is no unexpected rigid collision on the paint, leaves or grass.
for asset in ['markings','surface_details','grass_tufts']:require(asset+'_no_collision',R['assets'][asset]['collision_triangles']==0)
require('tree_has_low_lod',any('_L1_' in s for s in read['tree']) and any('_L150_' in s for s in read['tree']))
items=[]
for p in (ROOT/'main').rglob('items.level.json'):items.extend(json.loads(l) for l in p.read_text().splitlines() if l.strip())
names=[i['name'] for i in items];require('unique_scene_names',len(names)==len(set(names)))
require('mission_group_root',json.loads((ROOT/'main/items.level.json').read_text())=={'class':'SimGroup','name':'MissionGroup'})
info=json.loads((ROOT/'info.json').read_text());require('default_spawn_exists',info['defaultSpawnPointName'] in names)
for s in info['spawnPoints']:require(s['objectname']+'_registered',s['objectname'] in names)
for sp in [x for x in items if x['class']=='SpawnSphere']:
    x,y,z=sp['position'];zs=[ray(x+dx,y+dy) for dx in [-2.5,0,2.5] for dy in [-1.1,0,1.1]]
    require(sp['name']+'_vehicle_footprint_supported',all(h is not None and abs(h)<.001 for h in zs),zs)
    require(sp['name']+'_above_ground',.2<z<1)
paths=[]
def walk(v):
    if isinstance(v,dict):
        for x in v.values():walk(x)
    elif isinstance(v,list):
        for x in v:walk(x)
    elif isinstance(v,str):
        assert '/Users/' not in v and '\\' not in v
        if v.startswith('/levels/'):
            paths.append(v);assert (PACKAGE/v.lstrip('/')).is_file(),v
walk(items);walk(materials);require('all_virtual_paths_resolve',True,len(paths))
require('no_reference_car_export',all(not n.startswith(('REFERENCE','C63','CAR','DISPLAY','LABEL','DIM')) for a in R['assets'].values() for n in a['source_objects']))
require('source_blend_unchanged',hashlib.sha256(Path(R['source_blend']).read_bytes()).hexdigest()==R['source_sha256'])
texturestats={}
for p in (ROOT/'art/textures').glob('*.png'):
    with Image.open(p) as im:
        arr=np.array(im);texturestats[p.name]={'size':list(im.size),'rgb_std':float(arr[:,:,:3].std()),'alpha_min':int(arr[:,:,3].min()) if arr.shape[-1]==4 else None};im.load()
    require(p.name+'_nonempty',arr[:,:,:3].max()>0)
report['texture_stats']=texturestats
for p in info['previews']:require('preview_exists', (ROOT/p).is_file())
require('ground_model_resolves',materials['c1v1_concrete']['groundType'] in json.loads((ROOT/'groundModels/c1_dry_concrete.json').read_text()))
report['render_triangles_instanced']=sum(R['assets'][Path(i['shapeName']).stem]['render_triangles'] for i in items if i['class']=='TSStatic')
report['collision_triangles_instanced']=sum(R['assets'][Path(i['shapeName']).stem]['collision_triangles'] for i in items if i['class']=='TSStatic')
report['passed']=not report['failures']
if report['passed']:
    archive=D/(LEVEL+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(PACKAGE).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(p.startswith('levels/'+LEVEL+'/') for p in z.namelist())
        report['archive_files']=len(z.namelist())
    report['zip_bytes']=archive.stat().st_size;report['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
(D/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','assets','texture_stats']},ensure_ascii=False,indent=2))
if not report['passed']:raise RuntimeError(str(report['failures']))
