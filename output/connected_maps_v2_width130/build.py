"""Standalone Gridmap connection variant. Original packages remain untouched."""
from pathlib import Path
import json, math, sys, shutil
import xml.etree.ElementTree as ET
import numpy as np

D=Path(__file__).resolve().parent
ROOT=D.parents[1]
OLD=ROOT/'output/beamng_existing_map_v3/package'
PKG=D/'package'
ASSET=PKG/'art/codex_connected_v2_width130'
SHAPES=ASSET/'shapes'
SHAPES.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'output/china_subject2/beamng_v1'))
from beamng_io import write_dae
sys.path.insert(0,str(ROOT/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
import road_profile
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
MAT='connected_grid_concrete'
SOIL='connected_earth'
colors={MAT:{'color':[1,1,1,1]},SOIL:{'color':[.32,.30,.22,1]}}
stats={}

def read_mesh(path):
    doc=ET.parse(path); render=[]; collision=[]
    for geo in doc.findall('.//c:library_geometries/c:geometry',NS):
        target=collision if geo.get('name','').lower().startswith('colmesh') else render
        mesh=geo.find('c:mesh',NS); arrays={}
        for src in mesh.findall('c:source',NS):
            acc=src.find('c:technique_common/c:accessor',NS)
            arrays[src.get('id')]=np.fromstring(src.find('c:float_array',NS).text,sep=' ').reshape(-1,int(acc.get('stride')))
        verts={v.get('id'):v.find('c:input[@semantic="POSITION"]',NS).get('source')[1:] for v in mesh.findall('c:vertices',NS)}
        for tri in mesh.findall('c:triangles',NS):
            ins=tri.findall('c:input',NS); width=max(int(i.get('offset')) for i in ins)+1
            ids=np.fromstring(tri.find('c:p',NS).text,sep=' ',dtype=int).reshape(-1,3,width)
            fields={i.get('semantic'):i for i in ins}
            values=[]
            for key in ['VERTEX','NORMAL','TEXCOORD']:
                i=fields[key]; source=i.get('source')[1:]
                if key=='VERTEX':source=verts[source]
                values.append(arrays[source][ids[:,:,int(i.get('offset'))]])
            mat=tri.get('material');colors[mat]={'color':[1,1,1,1]}
            target.extend((p,n,u,mat) for p,n,u in zip(*values))
    return render,collision

def save_mesh(name,render,collision=None):
    write_dae(SHAPES/(name+'.dae'),name,{1:render},collision or [],colors)
    stats[name]={'render_triangles':len(render),'collision_triangles':len(collision or [])}

def triangle(points,mat=MAT):
    p=np.asarray(points,float);cross=np.cross(p[1]-p[0],p[2]-p[0]);norm=cross/np.linalg.norm(cross)
    return p,np.tile(norm,(3,1)),p[:,:2]/2,mat

def clip_half(poly,axis,value,keep_greater):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        av=a[axis] if isinstance(axis,int) else np.dot(a[:2],axis)
        bv=b[axis] if isinstance(axis,int) else np.dot(b[:2],axis)
        da=(av-value)*(1 if keep_greater else -1)
        db=(bv-value)*(1 if keep_greater else -1)
        if da>=-1e-10:out.append(a)
        if (da<0)!=(db<0):out.append(a+(b-a)*(da/(da-db)))
    return out

def cut_convex(tris,planes):
    # 3D clipping also handles vertical fence triangles and interpolates UV/normals.
    out=[]
    for p,n,u,m in tris:
        remaining=[np.r_[a,b,c] for a,b,c in zip(p,n,u)]
        for axis,val,inside in planes:
            outside=clip_half(remaining,axis,val,not inside) if remaining else []
            for j in range(1,len(outside)-1):
                v=np.array([outside[0],outside[j],outside[j+1]])
                if np.linalg.norm(np.cross(v[1,:3]-v[0,:3],v[2,:3]-v[0,:3]))>1e-10:
                    out.append((v[:,:3],v[:,3:6],v[:,6:8],m))
            remaining=clip_half(remaining,axis,val,inside) if remaining else []
    return out

def cut_gate(tris):
    return cut_convex(tris,[(0,74,True),(0,84,False),(1,40.5,True),(1,46.5,False)])

# Reuse exact pavement triangles with world-scale UVs and the original Gridmap concrete textures.
modified={}
for asset,names,offset in [('china_subject2_v1',['road_flat_asphalt','road_flat_concrete','road_hillramp'],[-1700,-1500]),('hometown_hairpin_v3',['main_road','small_road'],[-1580,-1490])]:
    for name in names:
        render,col=read_mesh((D/'widened_source' if asset=='hometown_hairpin_v3' else OLD/'art'/asset/'shapes')/(name+'.dae'))
        remap=lambda ts:[(p,n,(p[:,:2]+offset)/2,MAT) for p,n,u,m in ts]
        key=asset+'_'+name
        save_mesh(key,remap(render),remap(col))
        modified[(asset,name)]=key
for name in ['curbs','fence','markings']:
    render,col=read_mesh(OLD/'art/china_subject2_v1/shapes'/(name+'.dae'))
    key='china_subject2_v1_'+name
    save_mesh(key,cut_gate(render),cut_gate(col))
    modified[('china_subject2_v1',name)]=key

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def line(a,b,spacing=.5):
    return np.linspace(a,b,max(2,int(np.ceil(np.linalg.norm(np.array(b)-a)/spacing))+1))

def arc(start,heading,turn,radius):
    h=math.radians(heading);delta=math.radians(turn);sign=np.sign(delta)
    c=np.array(start)+sign*radius*np.array([-math.sin(h),math.cos(h)])
    angle=np.linspace(h,h+delta,max(2,int(abs(delta)*radius/.5)+1))
    return c+sign*radius*np.column_stack([np.sin(angle),-np.cos(angle)])

tail=np.r_[road_profile.segments[-1]['end']+[-1580,-1490],114+road_profile.profile(road_profile.LENGTH)]
tangent=road_profile.segments[-1]['t']
side=np.array([-tangent[1],tangent[0]])
localtail=tail[:2]-[-1580,-1490]
along=float(localtail@tangent);across=float(localtail@side)
mouth=[(tangent,along-.08,True),(tangent,along+12,False),(side,across-2.55,True),(side,across+2.55,False)]
for name in ['terrain','roadside_rocks','vegetation']:
    render,col=read_mesh(D/'widened_source'/(name+'.dae'))
    key='hometown_hairpin_v3_'+name
    save_mesh(key,cut_convex(render,mouth),cut_convex(col,mouth))
    modified[('hometown_hairpin_v3',name)]=key
# Every widened mountain component, including drainage and rail collision, is replaced.
for path in sorted((D/'widened_source').glob('*.dae')):
    key=('hometown_hairpin_v3',path.stem)
    if key in modified:continue
    render,col=read_mesh(path)
    target='hometown_hairpin_v3_'+path.stem+('_r2' if path.stem.startswith('guardrails_') else '')
    save_mesh(target,render,col)
    modified[key]=target
arc_end=tail[:2]+18*tangent
arc_start=arc_end-20*np.array([math.sin(math.radians(155)),1-math.cos(math.radians(155))])
pieces=[line(np.array([-1628.,-1456.5]),[-1615,-1456.5]),arc([-1615,-1456.5],0,-90,15)]
pieces.append(line(pieces[-1][-1],[-1600,arc_start[1]+15]))
pieces.append(arc(pieces[-1][-1],-90,90,15))
pieces.append(line(pieces[-1][-1],arc_start))
pieces.append(arc(arc_start,0,155,20))
pieces.append(line(pieces[-1][-1],tail[:2]))
xy=np.concatenate([pieces[0]]+[p[1:] for p in pieces[1:]])
s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))];L=s[-1]
startBlend=smooth(s/12);endBlend=smooth((s-(L-20))/20)
base=startBlend*(1-endBlend);last=endBlend*math.tan(math.radians(10))
integrate=lambda v:float(np.trapezoid(v,s))
grade=(tail[2]-101-integrate(last))/integrate(base)*base+last
z=101+np.r_[0,np.cumsum((grade[:-1]+grade[1:])*.5*np.diff(s))]
width=4-.1*endBlend;bank=-.02/1.3*endBlend
routes={'between_sites':dict(xy=xy,z=z,width=width,bank=bank,s=s)}
xy=line(np.array([-1905.,-1470]),[-1708,-1470])
s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
z=100+smooth((xy[:,0]+1898)/35)
width=3.5+smooth((xy[:,0]+1720)/12)
routes['original_to_subject2']=dict(xy=xy,z=z,width=width,bank=np.zeros(len(xy)),s=s)

allprobes=[];road_data={}
connection_origin=np.array([-1700.,-1500.,100.])
for name,r in routes.items():
    xy,z,w,b,s=[r[k] for k in ['xy','z','width','bank','s']]
    d=np.gradient(xy,axis=0);d/=np.linalg.norm(d,axis=1)[:,None]
    if name=='between_sites':d[-1]=-tangent
    normal=np.column_stack([-d[:,1],d[:,0]])
    left=np.column_stack([xy+normal*w[:,None]/2,z+b*w/2])
    right=np.column_stack([xy-normal*w[:,None]/2,z-b*w/2])
    pavement=[];earth=[]
    # Road shoulders and grounded side slopes. Existing terrain safely intersects their buried bases.
    bases=np.minimum(z-.02,100.94) if name=='between_sites' else np.minimum(z-.02,99.98)
    outer=w/2+.55+np.maximum(z-bases,0)*1.5
    a=np.column_stack([xy+normal*outer[:,None],bases]);b0=np.column_stack([xy-normal*outer[:,None],bases])
    for i in range(len(xy)-1):
        pavement.extend([triangle([left[i],right[i],right[i+1]]),triangle([left[i],right[i+1],left[i+1]])])
        for row1,row2 in [(a,left),(right,b0)]:
            earth.extend([triangle([row1[i],row2[i],row2[i+1]],SOIL),triangle([row1[i],row2[i+1],row1[i+1]],SOIL)])
    localize=lambda ts:[(p-connection_origin,n,u,m) for p,n,u,m in ts]
    save_mesh(name+'_local',localize(pavement))
    save_mesh(name+'_earth_local',localize(earth))
    for i in range(0,len(xy)-1,8):
        for lateral in [-.85,0,.85]:
            # Probe face interiors, avoiding exact shared edges where castRayStatic
            # occasionally misses both adjacent triangles even on original game meshes.
            f=.37
            p=(1-f)*(xy[i]+normal[i]*w[i]/2*lateral)+f*(xy[i+1]+normal[i+1]*w[i+1]/2*lateral)
            h=(1-f)*(z[i]+r['bank'][i]*w[i]/2*lateral)+f*(z[i+1]+r['bank'][i+1]*w[i+1]/2*lateral)
            allprobes.append({'route':name,'s':float(s[i]+f*(s[i+1]-s[i])),'x':float(p[0]),'y':float(p[1]),'z':float(h)})
    maxgrade=float(np.max(np.abs(np.diff(z)/np.diff(s))))
    assert maxgrade<.178 and abs(z[-1]-(tail[2] if name=='between_sites' else 101))<1e-6
    road_data[name]={'length_m':float(s[-1]),'maximum_grade':maxgrade,'nodes':np.column_stack([xy,z,w,r['bank']]).tolist()}

terrain=json.loads((D/'original_concrete_terrain.json').read_text(encoding='utf-8-sig'))
stage={'baseColorFactor':[1,1,1,1],'baseColorMap':terrain['baseColorDetailTex'],'normalMap':terrain['normalDetailTex'],'roughnessMap':terrain['roughnessDetailTex'],'roughnessFactor':1,'metallicFactor':0}
materials={MAT:{'name':MAT,'class':'Material','mapTo':MAT,'version':1.5,'Stages':[stage,{},{},{}],'groundType':terrain['groundmodelName'],'useAnisotropic':True},SOIL:{'name':SOIL,'class':'Material','mapTo':SOIL,'version':1.5,'Stages':[{'baseColorFactor':[.32,.30,.22,1],'roughnessFactor':1},{},{},{}],'groundType':'DIRT'}}
(ASSET/'main.materials.json').write_text(json.dumps(materials,indent=2),encoding='utf8')
matdir=PKG/'levels/gridmap_v2/art/codex_connected_v2_width130';matdir.mkdir(parents=True,exist_ok=True)
(matdir/'main.materials.json').write_text(json.dumps(materials,indent=2),encoding='utf8')

items=[{'name':'ConnectedMapComponents','class':'SimGroup','groupPosition':'0 0 0'}]
for asset,prefab,offset in [('china_subject2_v1','subject2',[-1700,-1500,101]),('hometown_hairpin_v3','hometown',[-1580,-1490,114])]:
    for ln in (OLD/'art'/asset/(prefab+'.prefab.json')).read_text(encoding='utf8').splitlines()[1:]:
        item=json.loads(ln);item['__parent']='ConnectedMapComponents'
        item['position']=(np.array(item['position'])+offset).tolist()
        key=(asset,Path(item['shapeName']).stem)
        if key in modified:item['shapeName']='/art/codex_connected_v2_width130/shapes/'+modified[key]+'.dae'
        items.append(item)
for name in road_data:
    for suffix in ['', '_earth']:
        items.append({'name':'linked_'+name+suffix,'class':'TSStatic','__parent':'ConnectedMapComponents','shapeName':'/art/codex_connected_v2_width130/shapes/'+name+suffix+'_local.dae','position':connection_origin.tolist(),'scale':[1,1,1],'collisionType':'Visible Mesh Final','decalType':'Visible Mesh Final'})
(ASSET/'connected.prefab.json').write_text('\n'.join(json.dumps(i,separators=(',',':')) for i in items)+'\n',encoding='utf8')
shutil.copyfile(D/'load.lua', ASSET/'load.lua')
rootitems=[json.loads(x) for x in (D/'backup/mission_before.level.json').read_text(encoding='utf8').splitlines() if x.strip()]
rootitems=[x for x in rootitems if x.get('name') not in ['codex_subject2_v1','codex_hometown_v3','codex_connected_v1']]
rootitems.append({'name':'codex_connected_v2_width130','class':'SimGroup','__parent':'MissionGroup'})
level=PKG/'levels/gridmap_v2/main/MissionGroup';(level/'codex_connected_v2_width130').mkdir(parents=True,exist_ok=True)
(level/'items.level.json').write_text('\n'.join(json.dumps(i,separators=(',',':')) for i in rootitems)+'\n',encoding='utf8')
(level/'codex_connected_v2_width130/items.level.json').write_text(json.dumps({'name':'CodexConnectedV2Width130','class':'Prefab','__parent':'codex_connected_v2_width130','filename':'/art/codex_connected_v2_width130/connected.prefab.json','position':[0,0,0],'rotationMatrix':[1,0,0,0,1,0,0,0,1],'scale':[1,1,1],'loadMode':'Automatic'})+'\n',encoding='utf8')
(D/'plan.json').write_text(json.dumps({'routes':road_data,'tail':tail.tolist(),'assets':stats,'material_source':terrain,'gate_rectangle_local':[74,40.5,84,46.5]},indent=2),encoding='utf8')
(D/'collision_probes.json').write_text(json.dumps(allprobes),encoding='utf8')
print(json.dumps({n:{k:v for k,v in d.items() if k!='nodes'} for n,d in road_data.items()},indent=2))
print('Generated',len(items)-1,'objects and',len(allprobes),'road probes. Source geometry and archive files preserved.')
