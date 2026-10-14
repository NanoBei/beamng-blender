"""Dimensioned 2D proposal only. Never opens, writes, or executes Blender files."""
from pathlib import Path
import ast, collections, hashlib, html, json, math, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARAM = json.loads((D.parent / 'parameters.json').read_text())
SITE = (80., 60.)
SHIFT = np.array([0., -1.])
S_ANGLE = 150.  # Proposed custom practice variant, not an approved standard dimension.
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
add('入口', straight((0, by), (2, by), 4.5))
add('倒库入口渐变', straight((2, by), (rx0, by), 4.5, rv['aisle_width']))
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
add('出口', straight(hill_end, (0, hill_end[1]), 3.5, 4.5))
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

project_polys = {'reverse': [strip(routes[2]['rows']), bay], 'parallel': [strip(routes[4]['rows']), pb],
                 's_curve': [strip(s1), strip(s2)], 'right_angle': [ra],
                 'ramp': [next(sf['poly'] for sf in surfaces if sf['name'] == '05坡道')]}
flat_polys = [sf['poly'] for sf in surfaces if sf['kind'] in ('flat', 'flat_connector')]
RES = 20
def mask(pp):
    m = Image.new('1', (int(SITE[0]*RES)+1, int(SITE[1]*RES)+1))
    ImageDraw.Draw(m).polygon([(float(x*RES), float(y*RES)) for x, y in pp], fill=1)
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
outside = [sf['name'] for sf in surfaces if ((sf['poly'] < -1e-6) | (sf['poly'] > np.array(SITE)+1e-6)).any()]
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
report = dict(status='pending_user_confirmation', blender_modified=False, site_m=SITE, area_m2=4800,
    counts={k: 1 for k in project_polys}, reverse_to_parallel_straight_m=8,
    s_curve_proposal=dict(outer_radius_m=7.5, inner_radius_m=4, net_width_m=3.5,
        angle_each_deg=S_ANGLE, baseline_angle_each_deg=135, type='custom practice, awaiting confirmation',
        changed_curvature=False, changed_total_heading_sweep=True),
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
(D/'planning_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
(D/'layout_parameters.json').write_text(json.dumps(dict(report=report, approved_baseline_dimensions=d,
    proposal_design_values=dict(base_lane_y_m=by, flat_translation_xy_m=SHIFT.tolist(), s_angle_each_degrees=S_ANGLE),
    routes=[dict(name=r['name'], kind=r['kind'], start=r['rows'][0].tolist(), end=r['rows'][-1].tolist()) for r in routes],
    footprints=[dict(name=s['name'], points_m=s['poly'].tolist()) for s in surfaces]), ensure_ascii=False, indent=2))

# Common metric scale, no artistic distortion of either road footprint.
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
C = dict(ink='#21383d', muted='#5e716c', green='#e5ecdD', road='#f0f2ee', exam='#d4e7f0',
         hill='#c1d9e7', blue='#24739d', flat='#e7c397', flat_connector='#f5dfbf', orange='#995b22')
W, H = 2800, 2390; S = 30; X0, Y0 = 180, 2050
def new_canvas():
    global im, dr, svg
    im = Image.new('RGB', (W, H), '#fcfcf8'); dr = ImageDraw.Draw(im)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="#fcfcf8"/>']
def save(name):
    im.save(D/(name+'.png')); (D/(name+'.svg')).write_text('\n'.join(svg+['</svg>']))
new_canvas()
txt(180, 65, '科目二 + 平面双发卡弯 · 融合布局', 56, anchor='lm')
txt(180, 125, 'V06 / 待确认     80 × 60 m     五项各一处     总图 S 弯试拟 150°，另附 135° 对照', 31, C['muted'], anchor='lm')
for x, fill, name in [(180,C['exam'],'科目二项目'),(690,C['flat'],'原模型道路 · 压平复用'),(1380,C['flat_connector'],'新增平面连接段')]:
    rect((x,170,x+45,196),fill);txt(x+60,184,name,28,anchor='lm')
txt(2580,184,'网格 10 m',25,C['muted'],anchor='rm')
polygon([p((0,0)),p((80,0)),p((80,60)),p((0,60))],C['green'],'#80917a',3)
for x in range(10,80,10):line([p((x,0)),p((x,60))],'#d2dfca',1)
for y in range(10,60,10):line([p((0,y)),p((80,y))],'#d2dfca',1)
# Drawing all fills then the union boundary leaves intended junctions open.
for sf in surfaces:polygon([p(q) for q in sf['poly']],C.get(sf['kind'],C['road']))
# Each original surface boundary is faint, then junction crossing lines are suppressed
# using a raster union edge on PNG. SVG retains only external boundary portions below.
def exterior_line(poly):
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        delta=b-a;length=np.linalg.norm(delta)
        if length < 1e-8:continue
        normal=np.array([-delta[1],delta[0]])/length
        points=np.linspace(a,b,max(2,math.ceil(length/.08)+1))
        run=[]
        for q in points:
            sides=[]
            for sign in [-1,1]:
                ix,iy=np.round((q+sign*.12*normal)*RES).astype(int)
                sides.append(0 <= iy < union_mask.shape[0] and 0 <= ix < union_mask.shape[1] and union_mask[iy,ix])
            if sides[0] != sides[1]:run.append(p(q))
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
for a,b in [((.6,by),(4,by)),((8,by),(12,by)),((25,by),(29,by)),((42,by),(46,by)),
            ((58,cy),(61.5,cy)),((cx,40.2),(cx,42.2)),((cx,44.7),(cx,46.6)),
            ((68.9,53.2),(66.2,55.7)),((59,hill_start[1]),(54,hill_start[1])),
            ((27,hill_start[1]),(22,hill_start[1])),((3,hill_start[1]),(.4,hill_start[1]))]:ma(a,b)
for rr in [s1,s2]:
    k=len(rr)//2;ma(rr[k-10,:2],rr[k+10,:2])
for a,b in [((3,43.5),(7,43.5)),((22,43.5),(27,43.5)),((52,43.5),(58,43.5)),((re[0],31),(re[0],36))]:
    ma(a,b,C['orange'],3,True)
for seg in hp_segments:
    if seg['kind']=='line':
        a=seg['start']+SHIFT;b=seg['end']+SHIFT
        ma(a*.45+b*.55,a*.65+b*.35,C['orange'],3,True)
k=len(return_arc)//2;ma(return_arc[k-15,:2],return_arc[k+15,:2],C['orange'],3,True)

label((13.5,19.6),'01  倒车入库','5.558 × 2.447 m')
line([p((13.5,16.8)),p((13.5,13.9))],C['muted'],2)
ma((rx1,14.7),(px0,14.7),C['blue'],2,True);mt(((rx1+px0)/2,16),'直连 8 m',25,C['blue'],bg='#fcfcf8')
label((35.3,3.5),'02  侧方停车','8.287 × 2.647 m')
line([p((35.3,4.5)),p((35.3,5.4))],C['muted'],2)
label((65.5,17),'03  S 弯加弯试拟','两段 150° · 待确认')
mt((65.5,13.2),'R外 7.5 m / 净宽 3.5 m',25,C['muted'],bg='#fcfcf8')
line([p((58.2,19.3)),p((55.8,21.2))],C['muted'],2)
label((66,25.2),'04  直角转弯','净宽 3.908 m')
line([p((69,26.4)),p((70,29.3))],C['muted'],2)
label((33.5,52.3),'05  坡道定点停车 / 起步','10% · 总投影 57.94 m · 高约 2.30 m')
line([p((33.5,53.4)),p((33.5,55.1))],C['muted'],2)
mt((49,59.3),'上坡 ←',24,C['blue']);mt((16,59.3),'← 下坡',24,C['blue']);mt((32.4,59.3),'平台 6 m',23,C['muted'])
mt((23,47.6),'原模型大路 44 × 5 m · Z = 0',32,C['orange'],bg='#fcfcf8')
mt((57,47.6),'延伸接通科目二道路',29,C['orange'],bg='#fcfcf8')
mt((57,45.9),'新增长 27.30 m / 宽 5 m',23,C['muted'],bg='#fcfcf8')
label((6.6,34),'平面双发卡弯','原轮廓 1:1 / 路宽 3 m')
mt((6.6,30.3),'高程统一为 0',25,C['orange'],bg='#fcfcf8')
line([p((11.1,30.3)),p((15.8,28.6))],C['orange'],2)
mt((39.1,26.7),'R10 平面连接',25,C['orange'],bg='#fcfcf8')
line([p((39.1,25.8)),p((40.3,21.7))],C['orange'],2)
mt((57.5,38),'大路与考试连接道相接',26,C['muted'],bg='#fcfcf8')
line([p((66.5,38)),p((cx-1,43.5))],C['muted'],2)
mt((5,6.3),'考试入口 →',28,C['blue'],bg='#fcfcf8')
mt((5,53.8),'← 考试出口',28,C['blue'],bg='#fcfcf8')
mt((5,40),'大路出入口',25,C['orange'],bg='#fcfcf8')
ma((76.8,4),(76.8,8.2),C['ink'],4);mt((76.8,9.6),'N',29)
for i in range(4):
    a=p((61+i*2.5,3));b=p((63.5+i*2.5,2.55));rect((*a,*b),C['ink'] if i%2==0 else '#fcfcf8',C['ink'])
mt((61,1.4),'0',23);mt((71,1.4),'10 m',23)
ma((0,-2.2),(80,-2.2),C['muted'],2,True);mt((40,-2.2),'80 m',30,C['muted'],bg='#fcfcf8')
for x in [0,80]:line([p((x,0)),p((x,-2.8))],C['muted'],2)
ma((-2.3,0),(-2.3,60),C['muted'],2,True);mt((-4.3,30),'60 m',28,C['muted'])
for y in [0,60]:line([p((0,y)),p((-3,y))],C['muted'],2)
line([(180,2180),(2580,2180)],C['ink'],2)
txt(180,2230,'蓝色路线：倒库 → 侧方 → S 弯 → 直角 → 坡道。棕色道路：平面发卡弯与大路连通。',30,anchor='lm')
txt(180,2282,'地块仍为 4,800 m²；新旧道路按实际尺度落位。150° 为自定义练习提案，其余项目净尺寸保留。',29,anchor='lm')
txt(180,2334,'本轮仅平面图，未改 Blender。发卡区高程统一为 0；坡道项目保留 10%。',28,C['muted'],anchor='lm')
save('layout_v06')

# A fair same-radius, same-scale comparison, both rotated together for recognisable S silhouettes.
W,H=2000,1200;S=33;X0,Y0=0,0
new_canvas()
txt(90,65,'S 弯变化对比 · 同半径 / 同宽 / 同比例',48,anchor='lm')
txt(90,120,'增加圆弧转过的角度，让 S 形更收拢；圆弧半径和弯心曲率保持不变。',28,C['muted'],anchor='lm')
comparison=[]
for angle_deg, ox, title, fill in [(135,70,'原方案：每段 135°',C['exam']),(150,1050,'加弯试拟：每段 150°',C['flat'])]:
    a=math.radians(angle_deg);r1=arc((0,0),0,a,sr,3.5);r2=arc(r1[-1,:2],r1[-1,2],-a,sr,3.5)
    rows=np.vstack([r1,r2[1:]])
    # Rotate both by -90 degrees, not separately fit-to-box.
    rot=np.array([[0,1],[-1,0]])
    pp=strip(rows)@rot.T;xy=rows[:,:2]@rot.T
    shift=np.array([ox+50,390])-np.array([pp[:,0].min()*S,-pp[:,1].max()*S])
    def cp(q):return (shift[0]+q[0]*S,shift[1]-q[1]*S)
    txt(ox+430,225,title,39)
    txt(ox+430,280,'保留已确认尺寸' if angle_deg==135 else '待确认 · 自定义练习角度',27,C['muted'])
    polygon([cp(q) for q in pp],fill,'#6d8280',3)
    line([cp(q) for q in xy],C['muted'],2,True)
    for rr in [r1,r2]:
        k=len(rr)//2;arrow(cp(rr[k-12,:2]@rot.T),cp(rr[k+12,:2]@rot.T),C['blue'],4)
    txt(ox+430,850,f'总转向量 {2*angle_deg}°  /  中心线长 {2*sr*a:.2f} m',29)
    txt(ox+430,905,'外半径 7.5 m · 内半径 4 m · 净宽 3.5 m',28,C['muted'])
    comparison.append(dict(angle_each_deg=angle_deg,total_heading_sweep_deg=2*angle_deg,
        centerline_length_m=2*sr*a,endpoint_m=rows[-1,:2].tolist()))
line([(1000,200),(1000,950)],'#d5ddd5',2)
line([(90,980),(1910,980)],C['ink'],2)
txt(90,1030,'150° 每段多转 15°，整段中心线约增加 3.01 m；它改变的是回弯程度。',31,anchor='lm')
txt(90,1085,'若要更小的转弯半径，需要另改 R 值。本次先保留 R 值，用 150° 作为总图试拟。',29,C['muted'],anchor='lm')
txt(90,1140,'两幅均由圆弧参数绘制，统一旋转展示；未增加第二处 S 弯场地。',28,C['muted'],anchor='lm')
save('s_curve_comparison')
(D/'s_curve_comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
