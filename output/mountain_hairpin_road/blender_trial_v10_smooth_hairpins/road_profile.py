"""V10: smooth height patches over both hairpins, retaining every plan vertex.

No angular height coordinate is used inside the filled inner corners: the
R1 fillet crosses the old curve centre, where an atan2-based height is singular.
"""
import math
import numpy as np

R = 1.9875
GRADE = math.tan(math.radians(10))
TURN_GRADE = math.tan(math.radians(3))
BANK = .03
TRANSITION = 5.
CORE_RADIUS = 1.
BLEND_RADIUS = 2.
START = 2 / math.sin(math.radians(25))

def smooth(t):
    t = np.clip(t, 0, 1)
    return t*t*t*(10+t*(-15+6*t))

segments=[]; pos=np.array([11.,44.]); head=math.radians(-25); station=0.
for kind, amount, turn in [('line',20,0),('arc',R,-145),('line',12,0),('arc',R,145),('line',16,0)]:
    sg=np.sign(turn); length=amount if kind=='line' else amount*abs(math.radians(turn))
    tangent=np.array([math.cos(head),math.sin(head)])
    normal=np.array([-math.sin(head),math.cos(head)])
    center=pos+sg*amount*normal if kind=='arc' else None
    end_head=head+math.radians(turn)
    end=pos+length*tangent if kind=='line' else center+sg*amount*np.array([math.sin(end_head),-math.cos(end_head)])
    segments.append(dict(kind=kind,start=pos.copy(),end=end.copy(),s=station,length=length,
                         h=head,he=end_head,t=tangent,n=normal,c=center,sg=sg))
    pos=end; head=end_head; station+=length
LENGTH=station
curves=[seg for seg in segments if seg['kind']=='arc']

def nearest(P):
    candidates=[]
    for seg in segments:
        if seg['kind']=='line':
            along=np.clip((P-seg['start'])@seg['t'],0,seg['length'])
            q=seg['start']+along[:,None]*seg['t']
        else:
            v=P-seg['c']; start_angle=math.atan2(*(seg['start']-seg['c'])[::-1])
            angle=np.arctan2(v[:,1],v[:,0])
            delta=np.mod(seg['sg']*(angle-start_angle),2*math.pi)
            along=R*delta
            outside=along>seg['length']
            nearer_start=np.sum((P-seg['start'])**2,axis=1)<np.sum((P-seg['end'])**2,axis=1)
            along=np.where(outside,np.where(nearer_start,0,seg['length']),along)
            h=seg['h']+seg['sg']*along/R
            q=seg['c']+seg['sg']*R*np.column_stack([np.sin(h),-np.cos(h)])
        candidates.append((np.sum((P-q)**2,axis=1),seg['s']+along,q))
    d=np.array([c[0] for c in candidates]); s=np.array([c[1] for c in candidates])
    indices=d.argmin(0)
    q=np.array([c[2] for c in candidates])
    return s[indices,np.arange(len(P))],indices,q[indices,np.arange(len(P))]

def old_profile(s):
    t=np.maximum(np.asarray(s)-START,0)
    return -GRADE*np.where(t<6,t*t/12,t-3)

grid=np.linspace(0,LENGTH,50001)
grade=GRADE*np.clip((grid-START)/6,0,1)
for arc in curves:
    a=arc['s']; b=a+arc['length']
    window=smooth((grid-(a-TRANSITION))/TRANSITION)*(1-smooth((grid-b)/TRANSITION))
    chord=np.linalg.norm(arc['end']-arc['start'])
    k=TURN_GRADE*arc['length']/chord
    end_grade=k*math.cos(arc['length']/(2*R))
    grade-=(GRADE-end_grade)*window
    in_arc=(grid>=a)&(grid<=b)
    grade[in_arc]=k*np.cos((grid[in_arc]-(a+b)/2)/R)
elevation=-np.r_[0,np.cumsum((grade[:-1]+grade[1:])*.5*np.diff(grid))]
def profile(s): return np.interp(s,grid,elevation)

def corrected_heights(P,old_z):
    s,indices,Q=nearest(P)
    normals=np.array([seg['n'] for seg in segments])[indices]
    lateral=np.sum((P-Q)*normals,axis=1)
    z=profile(s)+.02*lateral
    weights=[]; targets=[]
    for arc in curves:
        v=P-arc['c']; radius=np.linalg.norm(v,axis=1)
        chord=arc['end']-arc['start']; chord_length=np.linalg.norm(chord); direction=chord/chord_length
        drop=profile(arc['s'])-profile(arc['s']+arc['length'])
        centre_z=(profile(arc['s'])+profile(arc['s']+arc['length']))/2
        # The radial term gives a gentle inward bank at the apex, with a smooth centre.
        def plane(X):
            V=X-arc['c']; rr=np.linalg.norm(V,axis=1)
            return centre_z-(V@direction)*drop/chord_length+BANK*(np.sqrt(rr**2+.5**2)-math.sqrt(R*R+.25))
        target=plane(P)
        a=arc['s']; b=a+arc['length']
        before=1-smooth((a-s)/TRANSITION)
        after=1-smooth((s-b)/TRANSITION)
        station_weight=before*after
        on_arc=(s>=a)&(s<=b)
        z+=station_weight*(target-plane(Q)-.02*lateral)
        z=np.where(on_arc,target,z)
        weights.append(1-smooth((radius-CORE_RADIUS)/(BLEND_RADIUS-CORE_RADIUS)))
        targets.append(target)
    w=np.array(weights); total=w.sum(0)
    # Non-overlapping cores, normalized blending on the middle connecting straight.
    normalize=np.maximum(total,1)
    z=z*np.maximum(1-total,0)+(w*np.array(targets)).sum(0)/normalize
    preserve_entry=1-smooth((s-12)/3)
    z=z*(1-preserve_entry)+old_z*preserve_entry
    z=np.where(P[:,1]>=42-1e-6,0,z)
    return z

def mesh_stats(vertices,faces):
    t=vertices[faces]
    cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); area=np.linalg.norm(cross,axis=1)/2
    slope=np.degrees(np.arctan2(np.linalg.norm(cross[:,:2],axis=1),cross[:,2]))
    return {'triangles':len(faces),'max_face_slope_deg':float(slope.max()),
            'faces_over_30deg':int((slope>30).sum()),'area_over_30deg_m2':float(area[slope>30].sum()),
            'max_slope_on_faces_over_1cm2_deg':float(slope[area>1e-4].max())}

if __name__=='__main__':
    import json
    raw=json.load(open('/private/tmp/hairpin_v9_meshes.json'))['Road_Surface_4m_and_2.775m']
    vertices=np.array(raw['vertices']); faces=np.array(raw['faces'])
    updated=vertices.copy(); updated[:,2]=corrected_heights(vertices[:,:2],vertices[:,2])
    print(json.dumps({'before':mesh_stats(vertices,faces),'after':mesh_stats(updated.astype(np.float32).astype(float),faces),
                      'end_z_old':float(old_profile(LENGTH)),'end_z_new':float(profile(LENGTH)),
                      'curve_centres':[c['c'].tolist() for c in curves]},indent=2))
