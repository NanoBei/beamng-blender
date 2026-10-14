"""Read the saved mesh geometry independently, report measured dimensions and support."""
import bpy, math, json, numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];P=json.loads((ROOT/'parameters.json').read_text());report={'checks':{},'failures':[]}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/china_subject2_v03_final.blend'))
scene=bpy.context.scene;bpy.context.view_layer.update()
def pts(name):
    o=bpy.data.objects[name] if isinstance(name,str) else name
    a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);a=a.reshape(-1,3).astype(np.float64)
    m=np.array(o.matrix_world);return a@m[:3,:3].T+m[:3,3]
def bounds(name):
    p=pts(name);return p.min(0),p.max(0)
def check(name,actual,expected,tol=.001):
    error=float(np.max(np.abs(np.array(actual)-np.array(expected))));ok=error<=tol
    report['checks'][name]={'actual':np.asarray(actual).tolist(),'expected':np.asarray(expected).tolist(),'max_error':error,'passed':ok}
    if not ok:report['failures'].append(name)
def require(name,ok,detail=None):
    report['checks'][name]={'passed':bool(ok),'detail':detail}
    if not ok:report['failures'].append(name)
# Measured painted inner edges, not object custom properties.
l=bounds('LINE_Reverse_Left');r=bounds('LINE_Reverse_Right');back=bounds('LINE_Reverse_Back')
check('reverse_bay_width',r[0][0]-l[1][0],2.447)
check('reverse_bay_length',l[1][1]-back[1][1],5.558)
check('reverse_aisle_width',bounds('LINE_ReverseAisle_L')[0][1]-bounds('LINE_ReverseAisle_R')[1][1],7.287)
check('reverse_left_control_h',l[1][0]-bounds('LINE_Reverse_Control_Left')[1][0],7.287)
check('reverse_right_control_h',bounds('LINE_Reverse_Control_Right')[0][0]-r[0][0],7.287)
check('parallel_bay_length',bounds('LINE_Parallel_East')[0][0]-bounds('LINE_Parallel_West')[1][0],8.287)
check('parallel_bay_width',bounds('LINE_Parallel_Back')[0][1]-bounds('LINE_ParallelLane_R')[0][1],2.647)
check('parallel_lane_width',bounds('LINE_ParallelLane_R')[0][1]-bounds('LINE_ParallelLane_L')[1][1],3.5705)
check('right_angle_vertical_width',bounds('LINE_RightAngle_OuterEast')[0][0]-bounds('LINE_RightAngle_InnerWest')[1][0],3.908)
check('right_angle_horizontal_width',bounds('LINE_RightAngle_InnerNorth')[0][1]-bounds('LINE_RightAngle_OuterSouth')[1][1],3.908)
check('right_angle_vertical_outer_arm',bounds('LINE_RightAngle_OuterEast')[1][1]-bounds('LINE_RightAngle_OuterSouth')[1][1],10)
check('right_angle_horizontal_outer_arm',bounds('LINE_RightAngle_OuterEast')[0][0]-bounds('LINE_RightAngle_OuterSouth')[0][0],10)
# Circle fit to the actual paint inner-edge vertices; no stored radius reused.
for name in ['SCurve_First','SCurve_Second']:
    for side in ['L','R']:
        p=pts('LINE_'+name+'_'+side)[::2,:2]
        A=np.column_stack([2*p[:,0],2*p[:,1],np.ones(len(p))]);b=(p*p).sum(1);v=np.linalg.lstsq(A,b,rcond=None)[0]
        c=v[:2];rad=np.linalg.norm(p-c,axis=1);expected=7.5 if np.mean(rad)>5 else 4
        check(name+'_'+side+'_radius',rad.tolist(),[expected]*len(rad),.001)
        # Compact the report after retaining actual extrema.
        report['checks'][name+'_'+side+'_radius']['actual']={'min':float(rad.min()),'max':float(rad.max()),'fit_center':c.tolist()}
        report['checks'][name+'_'+side+'_radius']['expected']=expected
        a=np.unwrap(np.arctan2(p[:,1]-c[1],p[:,0]-c[0]));check(name+'_'+side+'_sweep_degrees',abs(math.degrees(a[-1]-a[0])),135,.001)
for side in ['L','R']:check('S_tangent_join_'+side,pts('LINE_SCurve_First_'+side)[-2:],pts('LINE_SCurve_Second_'+side)[:2],.001)
# Actual station mesh on the slope.
p=pts('ROAD_HillRamp')[::2];xs=p[:,0];zs=p[:,2];order=np.argsort(xs);xs=xs[order];zs=zs[order]
check('ramp_lane_width',bounds('LINE_HillRamp_L')[0][1]-bounds('LINE_HillRamp_R')[1][1],3.5)
check('ramp_peak_height',zs.max(),2.297768587400651)
check('ramp_length',xs.max()-xs.min(),57.94044628251987)
check('ramp_ground_joins',[zs[0],zs[-1]],[0,0])
dx=np.diff(xs);dz=np.diff(zs);mask=(dx>1e-5)&(xs[:-1]>29.1)&(xs[1:]<48.8)
slopes=dz[mask]/dx[mask];check('ramp_constant_grade',slopes.tolist(),[.1]*len(slopes),.0002)
report['checks']['ramp_constant_grade']['actual']={'min':float(slopes.min()),'max':float(slopes.max())};report['checks']['ramp_constant_grade']['expected']=.1
slope=dz[dx>1e-5]/dx[dx>1e-5];require('ramp_continuous_grade',float(np.max(np.abs(np.diff(slope))))<.004,{'max_neighbor_grade_difference':float(np.max(np.abs(np.diff(slope))))})
centres={n:float(pts('LINE_Ramp_'+n)[:,0].mean()) for n in ['Before','Stop','After']}
check('ramp_stop_station',centres['Stop']-xs.min(),12)
check('ramp_control_offsets',[centres['Stop']-centres['Before'],centres['After']-centres['Stop']],[.65,.65])
# Verify every route hand-off from actual road edge vertices.
manifest=json.loads((ROOT/'reports/build_manifest.json').read_text());segments=manifest['route_segments'];gap=[]
for a,b in zip(segments,segments[1:]):
    if a['name']=='RightAngleApproach':continue
    A=pts('ROAD_'+a['name'])[-2:];B=pts('ROAD_'+b['name'])[:2];gap.append(float(np.max(np.linalg.norm(A-B,axis=1))))
require('route_edge_joins',max(gap)<.001,{'max_join_gap_m':max(gap)})
# Build a roads-only BVH. Decals and cars cannot hide unsupported paint.
verts=[];faces=[]
for o in bpy.data.collections['01_Roads'].objects:
    if o.type!='MESH' or not o.name.startswith('ROAD_'):continue
    p=pts(o);offset=len(verts);verts.extend(p.tolist());faces.extend([tuple(offset+i for i in poly.vertices) for poly in o.data.polygons])
bvh=BVHTree.FromPolygons(verts,faces,all_triangles=False)
unsupported=[];heights=[]
for o in bpy.data.collections['02_Markings'].objects:
    if o.type!='MESH':continue
    p=pts(o)
    for q in p[::max(1,len(p)//200)]:
        loc,normal,index,dist=bvh.ray_cast(Vector((q[0],q[1],q[2]+1)),Vector((0,0,-1)),5)
        if loc is None:unsupported.append(o.name);break
        heights.append(float(q[2]-loc.z))
require('paint_supported_by_road',not unsupported,unsupported)
require('paint_close_to_surface',not heights or (min(heights)>-.001 and max(heights)<.004),{'min_lift_m':min(heights),'max_lift_m':max(heights)})
road_down=[]
for o in bpy.data.collections['01_Roads'].objects:
    if o.name.startswith('ROAD_') and len(o.data.vertices)>20 and any(p.normal.z<.5 for p in o.data.polygons):road_down.append(o.name)
require('ribbon_surface_normals_up',not road_down,road_down)
# Grates and kerbs must not reduce the clear lane or parking dimensions.
cv=[];cf=[]
for section in manifest['route_segments']:
    name=section['name'];a=pts('LINE_'+name+'_R')[::2];b=pts('LINE_'+name+'_L')[::2]
    off=len(cv)
    for u,v in zip(a,b):cv.extend([u.tolist(),v.tolist()])
    cf.extend([(off+2*i,off+2*i+2,off+2*i+3,off+2*i+1) for i in range(len(a)-1)])
def clear_rect(x0,x1,y0,y1):
    off=len(cv);cv.extend([(x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0)]);cf.append(tuple(off+i for i in range(4)))
clear_rect(l[1][0],r[0][0],back[1][1],l[1][1])
clear_rect(bounds('LINE_Parallel_West')[1][0],bounds('LINE_Parallel_East')[0][0],bounds('LINE_ParallelLane_R')[0][1],bounds('LINE_Parallel_Back')[0][1])
east=bounds('LINE_RightAngle_OuterEast')[0][0];south=bounds('LINE_RightAngle_OuterSouth')[1][1]
clear_rect(east-3.908,east,south,27);clear_rect(east-10,east,south,south+3.908)
clear_bvh=BVHTree.FromPolygons(cv,cf,all_triangles=False)
intrusions=[]
for o in bpy.data.collections['03_Facilities'].objects:
    if not (o.name.startswith('DRAIN_Frame_') or o.name.startswith('SIGN_Post_')):continue
    for p in pts(o):
        hit,*_=clear_bvh.ray_cast(Vector((p[0],p[1],10)),Vector((0,0,-1)),20)
        if hit is not None:intrusions.append(o.name);break
cp=pts('CURBS_BlackYellow').reshape(-1,8,3).mean(axis=1)
for p in cp:
    hit,*_=clear_bvh.ray_cast(Vector((p[0],p[1],10)),Vector((0,0,-1)),20)
    if hit is not None:intrusions.append('CURBS_BlackYellow');break
require('facilities_clear_of_driving_width',not intrusions,intrusions)
# Precise high-detail car geometry in its placement parent's coordinates.
coll=bpy.data.collections['05_ReferenceCar_HIGH'];root=next(o for o in coll.objects if o.type=='EMPTY');inv=np.array(root.matrix_world.inverted())
lo=np.full(3,np.inf);hi=-lo.copy();blo=np.inf;bhi=-np.inf;wheel=[];tri=0
for o in coll.objects:
    if o.type!='MESH':continue
    p=pts(o);p=p@inv[:3,:3].T+inv[:3,3];lo=np.minimum(lo,p.min(0));hi=np.maximum(hi,p.max(0));tri+=sum(len(f.vertices)-2 for f in o.data.polygons)
    attr=o.data.attributes.get('exclude_from_body_width')
    if attr:
        values=np.empty(len(p),dtype=np.bool_);attr.data.foreach_get('value',values);bp=p[~values]
    else:bp=p
    if len(bp):blo=min(blo,float(bp[:,1].min()));bhi=max(bhi,float(bp[:,1].max()))
    if o.get('axle'):
        mid=(p.min(0)+p.max(0))/2;wheel.append({'axle':o['axle'],'x':float(mid[0]),'bottom':float(p[:,2].min())})
check('C63_length_bodywidth_mirrorwidth_height',[hi[0]-lo[0],bhi-blo,hi[1]-lo[1],hi[2]-lo[2]],[4.756,1.839,2.020,1.426])
wb=np.mean([w['x'] for w in wheel if w['axle']=='front'])-np.mean([w['x'] for w in wheel if w['axle']=='rear'])
check('C63_wheelbase',wb,2.840);check('C63_four_wheels_ground',[w['bottom'] for w in wheel],[0]*4)
proxy=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in bpy.data.collections['06_ReferenceCar_PROXY'].objects if o.type=='MESH')
require('C63_proxy_budget',proxy<=300000,{'triangles':proxy,'high_triangles':tri})
require('C63_display_modes',bpy.data.collections['06_ReferenceCar_PROXY'].hide_render and all(o.hide_get() for o in coll.objects if o.type=='MESH'))
missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.users and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
require('no_missing_used_textures',not missing,missing)
missing_fonts=[f.filepath for f in bpy.data.fonts if f.users and f.filepath and f.filepath!='<builtin>' and not f.packed_file and not Path(bpy.path.abspath(f.filepath)).is_file()]
require('no_missing_used_fonts',not missing_fonts,missing_fonts)
require('unit_metres',scene.unit_settings.scale_length==1 and scene.unit_settings.system=='METRIC')
check('site_dimensions',np.subtract(*reversed(bounds('LAND_Site100x75')))[:2],[100,75])
report['passed']=not report['failures'];report['file']='blender/china_subject2_v03_final.blend'
(ROOT/'reports/validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'failures':report['failures'],'proxy_triangles':proxy},ensure_ascii=False),flush=True)
if report['failures']:raise RuntimeError('Geometry validation failed: '+str(report['failures']))
