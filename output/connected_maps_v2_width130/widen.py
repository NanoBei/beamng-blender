"""Widen exported mountain geometry without scaling road length/elevation."""
from pathlib import Path
import json, sys
import xml.etree.ElementTree as ET
from collections import Counter
import numpy as np
D=Path(__file__).resolve().parent
ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'output/china_subject2/beamng_v1'))
from beamng_io import write_dae
sys.path.insert(0,str(ROOT/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
from road_profile import segments
SOURCE=ROOT/'output/beamng_existing_map_v3/package/art/hometown_hairpin_v3/shapes'
OUT=D/'widened_source';OUT.mkdir(exist_ok=True)
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}

def read(path):
    result=[]
    for geo in ET.parse(path).findall('.//c:library_geometries/c:geometry',NS):
        mesh=geo.find('c:mesh',NS);arrays={}
        for src in mesh.findall('c:source',NS):
            stride=int(src.find('c:technique_common/c:accessor',NS).get('stride'))
            arrays[src.get('id')]=np.fromstring(src.find('c:float_array',NS).text,sep=' ').reshape(-1,stride)
        verts={v.get('id'):v.find('c:input',NS).get('source')[1:] for v in mesh.findall('c:vertices',NS)}
        triangles=[]
        for tri in mesh.findall('c:triangles',NS):
            inputs=tri.findall('c:input',NS);width=1+max(int(i.get('offset')) for i in inputs)
            ids=np.fromstring(tri.find('c:p',NS).text,sep=' ',dtype=int).reshape(-1,3,width)
            fields={i.get('semantic'):i for i in inputs};values=[]
            for key in ['VERTEX','NORMAL','TEXCOORD']:
                inp=fields[key];src=inp.get('source')[1:]
                if key=='VERTEX':src=verts[src]
                values.append(arrays[src][ids[:,:,int(inp.get('offset'))]])
            triangles.extend((p,n,u,tri.get('material')) for p,n,u in zip(*values))
        result.append(triangles)
    return result

road=[t for g in read(SOURCE/'small_road.dae') for t in g]
old=np.array([t[0] for t in road])
verts,inv=np.unique(np.round(old.reshape(-1,3),7),axis=0,return_inverse=True)
faces=inv.reshape(-1,3)
counts=Counter();directed={}
for f in faces:
    for a,b in zip(f,np.roll(f,-1)):
        k=tuple(sorted((a,b)));counts[k]+=1;directed[k]=(a,b)
nxt={a:b for k,(a,b) in directed.items() if counts[k]==1}
ids=[next(iter(nxt))]
while nxt[ids[-1]]!=ids[0]:
    ids.append(nxt[ids[-1]])
    assert len(ids)<=len(nxt)
assert len(ids)==len(nxt),'Expected one road boundary'
P=verts[ids,:2];E=np.roll(P,-1,axis=0)-P
length=np.linalg.norm(E,axis=1);T=E/length[:,None]
assert np.sum(P[:,0]*np.roll(P[:,1],-1)-P[:,1]*np.roll(P[:,0],-1))>0
N=np.column_stack([T[:,1],-T[:,0]])
end=segments[-1]['end'];tangent=segments[-1]['t']
cap=(np.abs((P-end)@tangent)<.002)&(np.abs((np.roll(P,-1,axis=0)-end)@tangent)<.002)
entry=(P[:,1]>41.999)&(np.roll(P,-1,axis=0)[:,1]>41.999)
delta=.45;displacements=np.zeros_like(P)
stations=np.r_[0,np.cumsum(length)];perimeter=stations[-1]
def boundary_at(s):
    s=s%perimeter
    return np.array([np.interp(s,stations,np.r_[P[:,j],P[0,j]]) for j in [0,1]])
for i in range(len(P)):
    normals=[N[j] for j in [(i-1)%len(P),i] if not cap[j] and not entry[j]]
    if not normals:continue
    if len(normals)==1:d=normals[0]*delta
    else:
        # DAE coordinates contain millimetre-long boundary edges. Estimate their
        # tangent over 16 cm so quantization noise cannot reverse an offset edge.
        tangent0=boundary_at(stations[i]+.08)-boundary_at(stations[i]-.08)
        tangent0/=np.linalg.norm(tangent0)
        d=np.array([tangent0[1],-tangent0[0]])*delta
    if abs((P[i]-end)@tangent)<.2:
        side=np.array([-tangent[1],tangent[0]])
        d=delta*side*np.sign((P[i]-end)@side)
    f=np.clip((42-P[i,1]),0,1);displacements[i]=d*f*f*(3-2*f)

def inside(q,polygon=P):
    a=polygon;b=np.roll(a,-1,axis=0)
    x=q[:,0,None];y=q[:,1,None]
    cross=((a[:,1]>y)!=(b[:,1]>y)) & (x < (b[:,0]-a[:,0])*(y-a[:,1])/(b[:,1]-a[:,1]+1e-30)+a[:,0])
    return np.count_nonzero(cross,axis=1)%2==1

def shift(points):
    out=np.zeros_like(points)
    for start in range(0,len(points),192):
        q=points[start:start+192,:2];a=q[:,None,:]-P[None,:,:]
        f=np.clip(np.sum(a*E,axis=2)/(length**2),0,1)
        dist2=np.sum((a-f[:,:,None]*E)**2,axis=2);idx=dist2.argmin(1);r=np.arange(len(q))
        fraction=f[r,idx];distance=np.sqrt(dist2[r,idx])
        d=displacements[idx]*(1-fraction[:,None])+displacements[(idx+1)%len(P)]*fraction[:,None]
        wi=np.clip(1-distance/1.5,0,1);wi=wi*wi*(3-2*wi)
        wo=1-np.clip((distance-1.8)/2.2,0,1);wo=wo*wo*(3-2*wo)
        d*=np.where(inside(q),wi,wo)[:,None];d[q[:,1]>=42-1e-6]=0
        out[start:start+len(q),:2]=d
    # Main road widens away from the small-road junction, as in V20.
    out[:,1]+=1.5*np.clip((points[:,1]-42)/5,0,1)
    return out

def rotate_normals(before,after,normals):
    a=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0]);a/=np.maximum(np.linalg.norm(a,axis=1)[:,None],1e-20)
    b=np.cross(after[:,1]-after[:,0],after[:,2]-after[:,0]);b/=np.maximum(np.linalg.norm(b,axis=1)[:,None],1e-20)
    v=np.cross(a,b)[:,None,:];c=np.sum(a*b,axis=1)[:,None,None]
    return normals+np.cross(v,normals)+np.cross(v,np.cross(v,normals))/np.maximum(1+c,1e-8)

stats={};newroad=None
for path in sorted(SOURCE.glob('*.dae')):
    output=[]
    for group in read(path):
        if not group:continue
        p=np.array([t[0] for t in group]);n=np.array([t[1] for t in group]);flat=p.reshape(-1,3)
        unique,idx=np.unique(flat,axis=0,return_inverse=True)
        change=shift(unique)
        if path.stem.startswith('guardrails_') and flat[:,1].min()>41.4:
            # Main-road near-side rail stays at the unchanged Y=42 edge.
            # The small-road displacement field must not push it into the main road.
            change[:]=0
        if path.stem=='small_road':
            # Smooth interior displacement with fixed boundary offsets; this avoids
            # folding very thin existing triangles around the filled hairpin corners.
            boundary_keys={tuple(v) for v in np.round(verts[ids],7)}
            fixed=np.array([tuple(v) in boundary_keys for v in np.round(unique,7)])
            f=idx.reshape(-1,3)
            edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
            edges=np.unique(np.sort(edges,axis=1),axis=0)
            edges=np.concatenate([edges,edges[:,::-1]])
            weight=1/np.maximum(np.linalg.norm(unique[edges[:,0],:2]-unique[edges[:,1],:2],axis=1),1e-6)
            total=np.bincount(edges[:,0],weights=weight,minlength=len(unique))
            for iteration in range(2000):
                smooth=np.column_stack([np.bincount(edges[:,0],weights=weight*change[edges[:,1],j],minlength=len(unique))/total for j in [0,1]])
                change[~fixed,:2]=smooth[~fixed]
                if iteration%50==49:
                    probe=(unique+change)[idx].reshape(p.shape)
                    areas=np.cross(probe[:,1]-probe[:,0],probe[:,2]-probe[:,0])[:,2]
                    if np.all(areas>0):break
            print('Interior smoothing iterations',iteration+1,flush=True)
        changed=unique+change;new=changed[idx].reshape(p.shape)
        newn=rotate_normals(p,new,n)
        if path.stem=='small_road':
            cross=lambda a:np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0])[:,2]
            bad=cross(p)*cross(new)<=0
            if np.any(bad):
                print('Flipped triangles',int(bad.sum()),'of',len(p), 'positions',p[bad].mean(1).tolist()[:15],flush=True)
            assert not np.any(bad),'Road triangle flipped'
            assert np.array_equal(p[:,:,2],new[:,:,2])
            newroad=new
        if path.stem=='main_road':
            assert abs(np.ptp(new[:,:,1])-6.5)<1e-6
            assert np.all(new[:,:,2]==0)
        output.extend((a,b,t[2],t[3]) for a,b,t in zip(new,newn,group))
    colors={t[3]:{'color':[1,1,1,1]} for t in output}
    write_dae(OUT/path.name,'wide_'+path.stem,{1:output},[],colors)
    stats[path.stem]={'triangles':len(output)}
    print('Widened',path.stem,len(output),flush=True)

newpoly=P+shift(np.column_stack([P,np.zeros(len(P))]))[:,:2]
checks=[]
for si,along in [(0,12),(0,15),(2,5),(2,7),(4,5),(4,11)]:
    seg=segments[si];q=seg['start']+along*seg['t'];width=0
    for sign in [-1,1]:
        low,high=0.,3.
        for _ in range(35):
            mid=(low+high)/2
            if inside((q+sign*mid*seg['n'])[None],newpoly)[0]:low=mid
            else:high=mid
        width+=(low+high)/2
    checks.append({'station':seg['s']+along,'width':width})
assert all(abs(c['width']-3.9)<.002 for c in checks),checks
np.savez_compressed(D/'small_road_mesh.npz',triangles=newroad,boundary=newpoly)
report=dict(main_width=6.5,small_width=3.9,small_each_side_added=.45,main_outer_side_added=1.5,small_width_checks=checks,small_elevations_unchanged=True,small_flipped_triangles=0,assets=stats)
(D/'width_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
