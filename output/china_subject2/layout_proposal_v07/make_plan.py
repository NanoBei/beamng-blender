"""Dimensioned 2D proposal only. Never opens, writes, or executes Blender files."""
from pathlib import Path
import ast, collections, hashlib, html, json, math, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARAM = json.loads((D.parent / 'parameters.json').read_text())
SITE = (90., 60.)
SITE_MIN = np.array([-10., 0.])
SITE_MAX = np.array([80., 60.])
SHIFT = np.array([0., -1.])
S_ANGLE = 135.  # User chose to retain the original dimensions and rotate the display.
routes, surfaces = [], []

# Reuse the archived V05 drawing primitives without executing its scene generation.
source = ast.parse((D.parent / 'layout_proposal_v05/make_plan.py').read_text())
helpers = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef)
                          and n.name != 'mask'], type_ignores=[])
exec(compile(helpers, 'archived_v05_drawing_helpers', 'exec'))

d, defaults = PARAM['dimensions'], PARAM['design_defaults']
rv, pv, sv, cv = [d[k] for k in ('reverse', 'parallel', 's_curve', 'right_angle')]
by = 10.
rx0 = 6.; rx1 = rx0 + 2 * rv['control_each_side'] + rv['width']
px0 = rx1 + 8.; px1 = px0 + pv['length']
add('倒库入口渐变', straight((3, by), (rx0, by), 4.5, rv['aisle_width']))
add('01倒库车道', straight((rx0, by), (rx1, by), rv['aisle_width']), 'exam')
add('倒库至侧方8米直连', straight((rx1, by), (px0, by), rv['aisle_width'], pv['lane_width']))
add('02侧方车道', straight((px0, by), (px1 + 7.5, by), pv['lane_width']), 'exam')
add('侧方至S弯', straight((px1 + 7.5, by), (50, by), pv['lane_width'], sv['width']))
sr = (sv['inner_radius'] + sv['outer_radius']) / 2
angle = math.radians(S_ANGLE)
s1 = arc((50, by), 0, angle, sr, sv['width'])
s2 = arc(s1[-1, :2], s1[-1, 2], -angle, sr, sv['width'])
add('03S弯第一段', s1, 'exam'); se = add('03S弯第二段', s2, 'exam')
ra_entry = se + [7.5, 0]
cw = cv['width']; arm = defaults['right_angle_outer_arm']; arm_center = arm - cw / 2
corner = ra_entry + [arm_center, 0]; ra_exit = corner + [0, arm_center]
cx, cy = corner; ex, ey = ra_entry[0], ra_exit[1]
add('S弯至直角7.5米', straight(se, ra_entry, sv['width'], cw))
ra = np.array([(ex, cy-cw/2), (cx+cw/2, cy-cw/2), (cx+cw/2, ey),
               (cx-cw/2, ey), (cx-cw/2, cy+cw/2), (ex, cy+cw/2)])
surfaces.append(dict(name='04直角转弯', poly=ra, kind='exam'))
turn_start = ra_exit + [0, 7.5]
add('直角出口7.5米', straight(ra_exit, turn_start, cw, 4.5))
hill_start = add('连接坡道', arc(turn_start, math.pi/2, math.pi/2, 10, 4.5, 3.5))
grade = d['ramp']['grade']; radius = defaults['ramp_vertical_radius']
constant = defaults['ramp_constant_grade_horizontal']; platform = defaults['ramp_platform_length']
run = radius * math.sin(math.atan(grade)); rise = radius * (1-math.cos(math.atan(grade)))
up = constant + 2*run; hill_total = 2*up + platform; hill_h = constant*grade + 2*rise
hill_end = hill_start - [hill_total, 0]
add('05坡道', straight(hill_start, hill_end, d['ramp']['width']), 'hill')
exit_end = np.array([3., hill_end[1]])
add('考试出口渐变', straight(hill_end, exit_end, 3.5, 4.5))
loop_top = arc(exit_end, math.pi, math.pi/2, 10, 4.5)
loop_x = float(loop_top[-1, 0])
add('回程上弯R10', loop_top, 'loop')
loop_straight = straight(loop_top[-1, :2], (loop_x, by+10), 4.5)
add('西侧回程直道', loop_straight, 'loop')
loop_bottom = arc((loop_x, by+10), -math.pi/2, math.pi/2, 10, 4.5)
add('回程下弯R10', loop_bottom, 'loop')
add('场地出入口', straight((-10, 30), (loop_x, 30), 4.5), 'loop')
ry = by-rv['aisle_width']/2; bx = rx0+rv['control_each_side']
bay = np.array([(bx, ry), (bx+rv['width'], ry), (bx+rv['width'], ry-rv['length']), (bx, ry-rv['length'])])
py = by-pv['lane_width']/2
pb = np.array([(px0, py), (px1, py), (px1, py-pv['width']), (px0, py-pv['width'])])
surfaces.extend([dict(name='倒库库位', poly=bay, kind='exam'), dict(name='侧方库位', poly=pb, kind='exam')])

# Actual saved V20 pavement boundary, including its inner-corner fills and flared mouth.
# Reading the already-local export archive does not create a BeamNG deliverable.
archive = ROOT/'output/mountain_hairpin_road/beamng_hairpin_test_v3/tight_hairpin_drive_v3.zip'
ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
source_records = {}
def source_pavement(member):
    with zipfile.ZipFile(archive) as z:
        name = next(n for n in z.namelist() if n.endswith('/'+member+'.dae'))
        data = z.read(name)
    root = ET.fromstring(data)
    mesh = root.find('.//c:mesh', ns)
    position_id = mesh.find('c:vertices/c:input', ns).attrib['source'][1:]
    positions = next(n for n in mesh.findall('c:source', ns) if n.attrib['id'] == position_id)
    verts = np.fromstring(positions.find('c:float_array', ns).text, sep=' ').reshape(-1, 3)
    tri = mesh.find('c:triangles', ns)
    inputs = tri.findall('c:input', ns)
    stride = max(int(n.attrib['offset']) for n in inputs)+1
    vi = next(int(n.attrib['offset']) for n in inputs if n.attrib['semantic'] == 'VERTEX')
    faces = np.fromstring(tri.find('c:p', ns).text, sep=' ', dtype=int).reshape(-1, 3, stride)[:, :, vi]
    counts, directed = collections.Counter(), {}
    for f in faces:
        for a, b in zip(f, np.roll(f, -1)):
            key = tuple(sorted((int(a), int(b)))); counts[key] += 1; directed[key] = (int(a), int(b))
    nxt = {a: b for key, (a, b) in directed.items() if counts[key] == 1}
    ids = [next(iter(nxt))]
    while nxt[ids[-1]] != ids[0]:
        ids.append(nxt[ids[-1]])
        assert len(ids) <= len(nxt)
    assert len(ids) == len(nxt)
    xy = verts[ids, :2]+SHIFT
    source_records[member] = dict(archive=str(archive.relative_to(ROOT)), member=name,
        sha256=hashlib.sha256(data).hexdigest(), source_bounds_m=[verts.min(0).tolist(), verts.max(0).tolist()],
        boundary_vertices=len(ids), translation_xy_m=SHIFT.tolist(), rotation_degrees=0, xy_scale=1,
        proposed_z_m=0, max_xy_translation_error_m=float(np.abs(xy-SHIFT-verts[ids, :2]).max()))
    return xy

main_poly, hp_poly = source_pavement('main_road'), source_pavement('small_road')
surfaces.extend([dict(name='原V20大路44×5米', poly=main_poly, kind='flat'),
                 dict(name='原V20双发卡弯', poly=hp_poly, kind='flat')])
sys.path.insert(0, str(ROOT/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
from road_profile import segments as hp_segments
hp_rows = []
for seg in hp_segments:
    rr = (straight(seg['start']+SHIFT, seg['end']+SHIFT, 3) if seg['kind'] == 'line' else
          arc(seg['start']+SHIFT, seg['h'], seg['he']-seg['h'], 1.9875, 3))
    hp_rows.extend(rr.tolist())
hp_rows = np.array(hp_rows); hp_tail = hp_rows[-1, :2]
return_arc = arc(hp_tail, math.radians(-25), math.radians(115), 10, 3)
re = add('发卡末端平面连接弯R10', return_arc, 'flat_connector')
return_line = straight(re, (re[0], 43.5), 3)
add('发卡回接大路', return_line, 'flat_connector')
main_extension = straight((44, 43.5), (cx, 43.5), 5)
add('原大路延伸接科目二连接道', main_extension, 'flat_connector')
add('原大路西端接回程道', straight((0, 43.5), (loop_x, 43.5), 5), 'flat_connector')

project_polys = {'reverse': [strip(next(r['rows'] for r in routes if r['name']=='01倒库车道')), bay],
                 'parallel': [strip(next(r['rows'] for r in routes if r['name']=='02侧方车道')), pb],
                 's_curve': [strip(s1), strip(s2)], 'right_angle': [ra],
                 'ramp': [next(sf['poly'] for sf in surfaces if sf['name'] == '05坡道')]}
flat_polys = [sf['poly'] for sf in surfaces if sf['kind'] in ('flat', 'flat_connector')]
RES = 20
def mask(pp):
    m = Image.new('1', (int(SITE[0]*RES)+1, int(SITE[1]*RES)+1))
    ImageDraw.Draw(m).polygon([tuple((q-SITE_MIN)*RES) for q in pp], fill=1)
    return np.asarray(m, bool)
masks = {k: np.logical_or.reduce([mask(pp) for pp in polys]) for k, polys in project_polys.items()}
flat_mask = np.logical_or.reduce([mask(pp) for pp in flat_polys])
union_mask = np.logical_or.reduce([mask(sf['poly']) for sf in surfaces])
connectivity = Image.fromarray(union_mask.astype('uint8')*255).copy()
seed_y, seed_x = np.argwhere(union_mask)[0]
ImageDraw.floodfill(connectivity, (int(seed_x), int(seed_y)), 128)
unreachable_pixels = int(np.count_nonzero(np.asarray(connectivity) == 255))
overlaps = {}
for i, a in enumerate(masks):
    for b in list(masks)[i+1:]:
        area = np.count_nonzero(masks[a] & masks[b])/RES**2
        if area: overlaps[a+' / '+b] = area
flat_exam_overlap = {k: np.count_nonzero(m & flat_mask)/RES**2 for k, m in masks.items()}
outside = [sf['name'] for sf in surfaces if ((sf['poly'] < SITE_MIN-1e-6) | (sf['poly'] > SITE_MAX+1e-6)).any()]
def poly_distance(a, b):
    def to_edges(q, p):
        edge = np.roll(p, -1, axis=0)-p
        lengths = np.sum(edge**2, axis=1)
        best = float('inf')
        for chunk in np.array_split(q, max(1, math.ceil(len(q)/100))):
            delta = chunk[:, None, :]-p[None, :, :]
            t = np.clip(np.sum(delta*edge, axis=2)/np.maximum(lengths, 1e-16), 0, 1)
            best = min(best, float(np.linalg.norm(delta-t[:, :, None]*edge, axis=2).min()))
        return best
    return min(to_edges(a, b), to_edges(b, a))
return_polys = [strip(return_arc), strip(return_line)]
s_return_gap = min(poly_distance(a, b) for a in project_polys['s_curve'] for b in return_polys)
main_ra_gap = poly_distance(strip(main_extension), ra)
reserve = defaults['line_width']+defaults['shoulder_beyond_paint']+defaults['curb_width']
loop_polys = [strip(loop_top),strip(loop_straight),strip(loop_bottom)]
loop_mask = np.logical_or.reduce([mask(pp) for pp in loop_polys])
loop_exam_overlap = {k: np.count_nonzero(m & loop_mask)/RES**2 for k,m in masks.items()}
closed_names = ['倒库入口渐变','01倒库车道','倒库至侧方8米直连','02侧方车道','侧方至S弯',
                '03S弯第一段','03S弯第二段','S弯至直角7.5米','04直角转弯','直角出口7.5米',
                '连接坡道','05坡道','考试出口渐变','回程上弯R10','西侧回程直道','回程下弯R10']
closed_rows = {r['name']:r['rows'] for r in routes}
closed_rows['04直角转弯'] = np.array([[*ra_entry,0,cw],[*corner,0,cw],[*ra_exit,math.pi/2,cw]])
seams = []
for a,b in zip(closed_names,closed_names[1:]+closed_names[:1]):
    aa,bb = closed_rows[a][-1],closed_rows[b][0]
    seams.append(dict(from_segment=a,to_segment=b,gap_m=float(np.linalg.norm(aa[:2]-bb[:2])),
                      heading_gap_deg=float(abs(math.degrees(math.atan2(math.sin(aa[2]-bb[2]),math.cos(aa[2]-bb[2])))))))
report = dict(status='pending_user_confirmation', blender_modified=False, site_m=SITE, area_m2=5400,
    site_bounds_xy_m=[SITE_MIN.tolist(),SITE_MAX.tolist()],
    counts={k: 1 for k in project_polys}, reverse_to_parallel_straight_m=8,
    s_curve_proposal=dict(outer_radius_m=7.5, inner_radius_m=4, net_width_m=3.5,
        angle_each_deg=S_ANGLE, baseline_angle_each_deg=135, type='user retained original dimensions',
        changed_curvature=False, changed_total_heading_sweep=False, presentation_rotation_degrees=-90),
    exam_return=dict(width_m=4.5,corner_centerline_radius_m=10,elevation_m=0,
        west_centerline_x_m=loop_x,centerline_length_m=float(math.pi*10+loop_top[-1,1]-(by+10)),
        direction='hill exit -> west return -> reverse parking entry',closed_route=closed_names,
        seam_checks=seams,project_overlap_m2_at_5cm_grid=loop_exam_overlap),
    flattened_source=source_records, flat_zone_elevation_m=0,
    original_exam_hill=dict(horizontal_length_m=hill_total, height_m=hill_h, constant_grade=grade,
                            start_m=hill_start.tolist(), end_m=hill_end.tolist()),
    new_flat_connections=dict(radius_m=10, width_m=3, main_extension_width_m=5,
                              main_extension_length_m=float(cx-44), intersection_center_m=[float(cx),43.5]),
    outside_site=outside, exam_pair_overlap_m2_at_5cm_grid=overlaps,
    pavement_connectivity_at_5cm_grid=dict(all_connected=unreachable_pixels == 0, unreachable_pixels=unreachable_pixels),
    flat_zone_vs_exam_overlap_m2_at_5cm_grid=flat_exam_overlap,
    critical_pavement_gaps_m=dict(s_curve_to_flat_return=s_return_gap, main_extension_to_right_angle=main_ra_gap),
    paint_shoulder_curb_reserve_each_side_m=reserve,
    remaining_gap_after_two_reserves_m=dict(s_curve_to_flat_return=s_return_gap-2*reserve,
                                          main_extension_to_right_angle=main_ra_gap-2*reserve),
    scope_exclusions=['tunnel', 'rain/fog/wet-surface projects', 'mountain terrain/cliff/deep ditch'],
    limitations='2D pavement planning checks only. Junction fillets, hill retaining structure, swept paths and Blender geometry await approval.')
assert not outside and not overlaps and not any(flat_exam_overlap.values())
assert unreachable_pixels == 0
assert s_return_gap > 2*reserve and main_ra_gap > 2*reserve
assert not any(loop_exam_overlap.values())
assert max(s['gap_m'] for s in seams)<1e-9
assert max(s['heading_gap_deg'] for s in seams)<1e-9
(D/'planning_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
(D/'layout_parameters.json').write_text(json.dumps(dict(report=report, approved_baseline_dimensions=d,
    proposal_design_values=dict(base_lane_y_m=by, flat_translation_xy_m=SHIFT.tolist(), s_angle_each_degrees=S_ANGLE,
                               return_lane_width_m=4.5,return_radius_m=10,display_rotation_degrees=-90),
    routes=[dict(name=r['name'], kind=r['kind'], start=r['rows'][0].tolist(), end=r['rows'][-1].tolist()) for r in routes],
    footprints=[dict(name=s['name'], points_m=s['poly'].tolist()) for s in surfaces]), ensure_ascii=False, indent=2))

# Rotate the presentation clockwise as a whole, preserving every world-space dimension.
# The S curve reads horizontally in this orientation; labels stay upright.
FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
C=dict(ink='#21383d',muted='#5e716c',green='#e5ecdd',road='#f0f2ee',exam='#d4e7f0',
       hill='#c1d9e7',blue='#24739d',flat='#e7c397',flat_connector='#f5dfbf',orange='#995b22',
       loop='#bfe1d7',teal='#207c72')
W,H=2350,3260;S=30;X0,Y0=230,280
im=Image.new('RGB',(W,H),'#fcfcf8');dr=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
     f'<rect width="{W}" height="{H}" fill="#fcfcf8"/>']
def p(q):return X0+S*q[1],Y0+S*(q[0]-SITE_MIN[0])
def label(q,title,sub=None):
    x,y=p(q);txt(x,y,title,35,bg='#fcfcf8')
    if sub:txt(x,y+51,sub,25,C['muted'],bg='#fcfcf8')
txt(150,62,'考试路线闭环 · 科目二与平面发卡弯',52,anchor='lm')
txt(150,119,'V07 / 待确认     五项各一处     S 弯保留 135°     地块 90 × 60 m',30,C['muted'],anchor='lm')
for x,fill,name in [(150,C['exam'],'科目二项目'),(600,C['loop'],'出口接回入口'),
                    (1080,C['flat'],'原发卡弯与大路'),(1670,C['flat_connector'],'平面连接段')]:
    rect((x,165,x+40,191),fill);txt(x+55,180,name,27,anchor='lm')
polygon([p((-10,0)),p((80,0)),p((80,60)),p((-10,60))],C['green'],'#80917a',3)
for x in range(0,80,10):line([p((x,0)),p((x,60))],'#d2dfca',1)
for y in range(10,60,10):line([p((-10,y)),p((80,y))],'#d2dfca',1)
for sf in surfaces:polygon([p(q) for q in sf['poly']],C.get(sf['kind'],C['road']))
def exterior_line(poly):
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        delta=b-a;length=np.linalg.norm(delta)
        if length<1e-8:continue
        normal=np.array([-delta[1],delta[0]])/length
        points=np.linspace(a,b,max(2,math.ceil(length/.08)+1));run=[]
        for q in points:
            sides=[]
            for sign in [-1,1]:
                ix,iy=np.round((q+sign*.12*normal-SITE_MIN)*RES).astype(int)
                sides.append(0<=iy<union_mask.shape[0] and 0<=ix<union_mask.shape[1] and union_mask[iy,ix])
            if sides[0]!=sides[1]:run.append(p(q))
            else:
                if len(run)>1:line(run,'#85918b',2)
                run=[]
        if len(run)>1:line(run,'#85918b',2)
for sf in surfaces:exterior_line(sf['poly'])
for x in [rx0,rx1]:line([p((x,by-rv['aisle_width']/2)),p((x,by+rv['aisle_width']/2))],'#ffffff',5,True)
for pp in [bay,pb]:line([p(q) for q in list(pp)+[pp[0]]],'#ffffff',5)
stop=hill_start[0]-defaults['ramp_stop_horizontal_station']
for x in [stop-.65,stop,stop+.65]:line([p((x,hill_start[1]-1.75)),p((x,hill_start[1]+1.75))],'#c89d2d',6 if x==stop else 3)
for x in [hill_start[0]-up,hill_start[0]-up-platform]:line([p((x,hill_start[1]-1.75)),p((x,hill_start[1]+1.75))],'#7e9eaf',2)
for a,b in [((3.5,by),(5.3,by)),((8,by),(12,by)),((25,by),(29,by)),((42,by),(46,by)),
            ((59.5,cy),(63,cy)),((cx,39),(cx,41.3)),((cx,44.7),(cx,46.4)),
            ((71.5,51),(69.1,53.7)),((60,hill_start[1]),(55,hill_start[1])),
            ((27,hill_start[1]),(22,hill_start[1])),((9.7,hill_start[1]),(6.7,hill_start[1]))]:ma(a,b)
for rr in [s1,s2]:
    k=len(rr)//2;ma(rr[k-12,:2],rr[k+12,:2])
for rr in [loop_top,loop_bottom]:
    k=len(rr)//2;ma(rr[k-13,:2],rr[k+13,:2],C['teal'],5)
for ya,yb in [(40,36),(28,24)]:ma((loop_x,ya),(loop_x,yb),C['teal'],5)
ma((-9.7,30),(-7.3,30),C['teal'],3,True)
for a,b in [((3,43.5),(7,43.5)),((22,43.5),(27,43.5)),((52,43.5),(58,43.5)),
            ((re[0],31),(re[0],36)),((-1.3,43.5),(-4.5,43.5))]:ma(a,b,C['orange'],3,True)
for seg in hp_segments:
    if seg['kind']=='line':
        a=seg['start']+SHIFT;b=seg['end']+SHIFT
        ma(a*.45+b*.55,a*.65+b*.35,C['orange'],3,True)
k=len(return_arc)//2;ma(return_arc[k-15,:2],return_arc[k+15,:2],C['orange'],3,True)

label((13,20),'01  倒车入库','库位 5.558 × 2.447 m')
line([p((13,15.4)),p((13,13.9))],C['muted'],2)
ma((rx1,15.2),(px0,15.2),C['blue'],2,True)
mt((27,19.5),'直连 8 m',26,C['blue'],bg='#fcfcf8')
label((35.1,3),'02 侧方停车','8.287 × 2.647 m')
line([p((35.1,4.6)),p((35.1,5.4))],C['muted'],2)
label((64,16.8),'03  曲线行驶 · S 弯','保留两段 135°，仅旋转图纸展示')
x,y=p((64,16.8));txt(x,y+96,'R外 7.5 m / R内 4 m / 净宽 3.5 m',24,C['muted'],bg='#fcfcf8')
line([p((61.8,17.7)),p((55.2,19.8))],C['muted'],2)
label((69,22.5),'04  直角转弯','净宽 3.908 m')
line([p((70.7,25.5)),p((72.4,28.1))],C['muted'],2)
for yy,ss,sz in [(1420,'05 坡道',35),(1472,'定点停车 / 起步',27),(1522,'坡度 10%',27),
                 (1572,'高约 2.30 m',26),(1622,'总投影 57.94 m',25)]:txt(2180,yy,ss,sz)
line([(2050,1520),(1950,1520)],C['muted'],2)
mt((50,59.1),'上坡',24,C['blue']);mt((16,59.1),'下坡',24,C['blue']);mt((34.7,59.1),'平台 6 m',23,C['muted'])
label((18,49.5),'原模型大路','原段 44 × 5 m')
line([p((20.8,48.3)),p((20.8,46.2))],C['orange'],2)
label((5.5,27.5),'平面双发卡弯','原轮廓 1:1 / 小路宽 3 m')
x,y=p((5.5,27.5));txt(x,y+96,'高程统一为 0',25,C['orange'],bg='#fcfcf8')
line([p((9.8,31.3)),p((18,37.5))],C['orange'],2)
mt((40.5,24),'R10 平面连接',25,C['orange'],bg='#fcfcf8')
line([p((39.5,24)),p((38,20.4))],C['orange'],2)
label((-2.8,25.8),'出口 → 回程 → 入口','单向回程 / 净宽 4.5 m / Z = 0')
line([p((-4,26)),p((-5.4,26))],C['teal'],2)
mt((-1.5,49.4),'R10',27,C['teal'],bg='#fcfcf8')
mt((-1.8,16.2),'R10',27,C['teal'],bg='#fcfcf8')
mt((3,6.2),'考试入口',29,C['blue'],bg='#fcfcf8')
mt((6.5,59.1),'考试出口',29,C['blue'],bg='#fcfcf8')
mt((-2.2,39.1),'大路接回程道',25,C['orange'],bg='#fcfcf8')
mt((-11.6,30),'场地出入口',28,C['teal'],bg='#fcfcf8')
ma((76,49),(76,54),C['ink'],4);mt((76,56),'N',29)
for i in range(4):
    polygon([p(q) for q in [(75,4+i*2.5),(75.45,4+i*2.5),(75.45,6.5+i*2.5),(75,6.5+i*2.5)]],
            C['ink'] if i%2==0 else '#fcfcf8',C['ink'])
mt((77,4),'0',23);mt((77,14),'10 m',23)
ma((-10,-3.5),(80,-3.5),C['muted'],2,True);mt((35,-5.3),'90 m',29,C['muted'],bg='#fcfcf8')
for x in [-10,80]:line([p((x,0)),p((x,-4.2))],C['muted'],2)
ma((82.1,0),(82.1,60),C['muted'],2,True);mt((82.1,30),'60 m',29,C['muted'],bg='#fcfcf8')
for y in [0,60]:line([p((80,y)),p((82.8,y))],C['muted'],2)
line([(150,3100),(2200,3100)],C['ink'],2)
txt(150,3150,'闭环：倒库 → 侧方 → S 弯 → 直角 → 坡道 → 西侧回程 → 倒库入口。',30,anchor='lm')
txt(150,3203,'图纸顺时针旋转 90°；项目尺寸保持。仅更新平面草案，尚未修改 Blender。',28,C['muted'],anchor='lm')
im.save(D/'layout_v07.png');(D/'layout_v07.svg').write_text('\n'.join(svg+['</svg>']))
print(json.dumps(report,ensure_ascii=False,indent=2))
