"""Draw a dimensioned 2D proposal. Reads saved road data; never starts Blender."""
from pathlib import Path
import sys, math, json, html, zipfile, collections, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
OLD = json.loads((D.parent/'parameters.json').read_text())
sys.path.insert(0, str(ROOT/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
from road_profile import segments as hp_segments, profile as hp_profile, LENGTH as hp_length

# Dimensions are net usable widths. All placement changes below are proposals.
SITE = (100., 75.)
BASE_Y = 11.5
HILL_Y = 31.5
BENCH_Y = 71.5
SHIFT = np.array([33., 27.])  # Rigid translation only: existing P0 becomes (44, 71).
deg = math.radians
routes, surfaces = [], []

def straight(a, b, w, w2=None):
    a,b=np.array(a,float),np.array(b,float)
    h=math.atan2(*(b-a)[::-1]); n=max(2,math.ceil(np.linalg.norm(b-a)/.15))
    return np.array([[*(a+(b-a)*t),h,w+(0 if w2 is None else w2-w)*t] for t in np.linspace(0,1,n+1)])

def arc(a,h,delta,r,w,w2=None):
    a=np.array(a,float);sg=1 if delta>0 else -1
    c=a+sg*r*np.array([-math.sin(h),math.cos(h)])
    out=[]
    for t in np.linspace(0,1,max(12,math.ceil(abs(delta)*r/.08))+1):
        th=h+delta*t;q=c+sg*r*np.array([math.sin(th),-math.cos(th)])
        out.append([*q,th,w+(0 if w2 is None else w2-w)*t])
    return np.array(out)

def strip(rows,extra=0):
    n=np.column_stack([-np.sin(rows[:,2]),np.cos(rows[:,2])])
    a=rows[:,:2]+n*(rows[:,3:4]/2+extra)
    b=rows[:,:2]-n*(rows[:,3:4]/2+extra)
    return np.vstack([a,b[::-1]])

def add(name,rows,kind='connector'):
    routes.append(dict(name=name,rows=rows,kind=kind))
    surfaces.append(dict(name=name,poly=strip(rows),kind=kind))
    return rows[-1,:2]

rev_x0=18.; rev_x1=rev_x0+2*7.287+2.447
par_x0=rev_x1+8.; par_x1=par_x0+8.287
add('入口',straight((0,BASE_Y),(14,BASE_Y),4.5))
add('倒库入口渐变',straight((14,BASE_Y),(rev_x0,BASE_Y),4.5,7.287))
add('01 倒库车道',straight((rev_x0,BASE_Y),(rev_x1,BASE_Y),7.287),'exam')
add('倒库至侧方 8m',straight((rev_x1,BASE_Y),(par_x0,BASE_Y),7.287,3.5705))
add('02 侧方车道',straight((par_x0,BASE_Y),(par_x1+7.5,BASE_Y),3.5705),'exam')
add('侧方出口渐变',straight((par_x1+7.5,BASE_Y),(62,BASE_Y),3.5705,4.5))
add('综合直线',straight((62,BASE_Y),(85,BASE_Y),4.5))
add('东侧回转',arc((85,BASE_Y),0,math.pi,10,4.5,3.5))
run=30*math.sin(math.atan(.1));rise=30*(1-math.cos(math.atan(.1)))
up=20+2*run; hill_length=2*up+6;hill_end=85-hill_length
add('03 坡道',straight((85,HILL_Y),(hill_end,HILL_Y),3.5),'hill')
ra_start=hill_end-7.5;ra_x=ra_start-(10-3.908/2);ra_end_y=HILL_Y+(10-3.908/2)
add('坡道至直角 7.5m',straight((hill_end,HILL_Y),(ra_start,HILL_Y),3.5,3.908))
ra_poly=np.array([(ra_start,HILL_Y-1.954),(ra_x-1.954,HILL_Y-1.954),(ra_x-1.954,ra_end_y),(ra_x+1.954,ra_end_y),(ra_x+1.954,HILL_Y+1.954),(ra_start,HILL_Y+1.954)])
surfaces.append(dict(name='04 直角转弯',poly=ra_poly,kind='exam'))
add('直角至S 7.5m',straight((ra_x,ra_end_y),(ra_x,ra_end_y+7.5),3.908,3.5))
s1=arc((ra_x,ra_end_y+7.5),math.pi/2,-deg(135),5.75,3.5)
s2=arc(s1[-1,:2],s1[-1,2],deg(135),5.75,3.5)
add('05 S弯第一段',s1,'exam');sp=add('05 S弯第二段',s2,'exam')
add('S弯出口',straight(sp,(sp[0],61.5),3.5,4.5))
add('接入集散道',arc((sp[0],61.5),math.pi/2,-math.pi/2,10,4.5,5.0))
add('北侧双向集散道',straight((15,BENCH_Y),(100,BENCH_Y),5.0),'collector')
add('西侧回程上弯',arc((15,BENCH_Y),math.pi,math.pi/2,10,5.0,4.5),'return')
add('西侧回程',straight((5,61.5),(5,21.5),4.5),'return')
add('西侧回程下弯',arc((5,21.5),-math.pi/2,math.pi/2,10,4.5),'return')

rev_bay=np.array([(rev_x0+7.287,BASE_Y-3.6435),(rev_x0+7.287+2.447,BASE_Y-3.6435),(rev_x0+7.287+2.447,BASE_Y-3.6435-5.558),(rev_x0+7.287,BASE_Y-3.6435-5.558)])
par_bay=np.array([(par_x0,BASE_Y-3.5705/2),(par_x1,BASE_Y-3.5705/2),(par_x1,BASE_Y-3.5705/2-2.647),(par_x0,BASE_Y-3.5705/2-2.647)])
surfaces.extend([dict(name='倒库库位',poly=rev_bay,kind='exam'),dict(name='侧方库位',poly=par_bay,kind='exam')])

# Read the actual V20 small-road footprint from the already exported local mesh.
archive=ROOT/'output/mountain_hairpin_road/beamng_hairpin_test_v3/tight_hairpin_drive_v3.zip'
with zipfile.ZipFile(archive) as z:
    mesh_name=next(n for n in z.namelist() if n.endswith('/small_road.dae'))
    r=ET.fromstring(z.read(mesh_name))
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
verts=np.fromstring(r.find('.//c:source/c:float_array',ns).text,sep=' ').reshape(-1,3)
tri=r.find('.//c:triangles',ns)
faces=np.fromstring(tri.find('c:p',ns).text,sep=' ',dtype=int).reshape(-1,3,3)[:,:,0]
counts=collections.Counter();directed={}
for face in faces:
    for a,b in zip(face,np.roll(face,-1)):
        key=tuple(sorted((int(a),int(b)))); counts[key]+=1;directed[key]=(int(a),int(b))
nxt={a:b for key,(a,b) in directed.items() if counts[key]==1}
ids=[next(iter(nxt))]
while nxt[ids[-1]]!=ids[0]:ids.append(nxt[ids[-1]])
assert len(ids)==len(nxt)
hp_poly=verts[ids,:2]+SHIFT
surfaces.append(dict(name='06 原V20发卡弯',poly=hp_poly,kind='hairpin'))
hp_rows=[]
for seg in hp_segments:
    if seg['kind']=='line':rr=straight(seg['start']+SHIFT,seg['end']+SHIFT,3)
    else:rr=arc(seg['start']+SHIFT,seg['h'],seg['he']-seg['h'],1.9875,3)
    hp_rows.extend(rr.tolist())
hp_rows=np.array(hp_rows)
hp_tail=hp_rows[-1,:2]; tail_grade=deg(10)
ease_length=30*math.sin(tail_grade);ease_drop=30*(1-math.cos(tail_grade))
flat_start=hp_tail+ease_length*np.array([math.cos(deg(-25)),math.sin(deg(-25))])
add('发卡弯末端竖曲线',straight(hp_tail,flat_start,3),'hairpin_new')
flat_curve=arc(flat_start,deg(-25),deg(25),6,3)
pad_start=add('低端接平台',flat_curve,'hairpin_new')
pad=np.array([(pad_start[0],pad_start[1]-6),(pad_start[0]+12,pad_start[1]-6),(pad_start[0]+12,pad_start[1]+6),(pad_start[0],pad_start[1]+6)])
surfaces.append(dict(name='低端调头平台',poly=pad,kind='hairpin_new'))
pad_z=float(hp_profile(hp_length))-ease_drop

# Geometry-driven drawing: PNG and SVG share identical primitives.
W,H=2800,2440;S=24;X0,Y0=190,1980
im=Image.new('RGB',(W,H),'#fcfcf8');dr=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="#fcfcf8"/>']
FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
C={'ink':'#21383d','muted':'#58716e','green':'#dfe9d7','road':'#eef1ed','exam':'#dce9ef','hill':'#cbdde8','hairpin':'#edc38d','hairpin_new':'#f5dec0','collector':'#e7ebe5','return':'#e7ebe5','blue':'#29719d','orange':'#a96624'}
def p(q):return X0+S*q[0],Y0-S*q[1]
def line(ps,col='#21383d',width=2,dash=False):
    ps=[tuple(q) for q in ps]
    if dash:
        phase=0
        for a,b in zip(ps,ps[1:]):
            length=math.dist(a,b);n=max(1,math.ceil(length/2))
            for i in range(n):
                t=i/n;u=(i+1)/n
                if int((phase+t*length)/10)%2==0:dr.line([(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])),(a[0]+u*(b[0]-a[0]),a[1]+u*(b[1]-a[1]))],fill=col,width=width)
            phase+=length
    else:dr.line(ps,fill=col,width=width,joint='curve')
    svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in ps)+f'" fill="none" stroke="{col}" stroke-width="{width}" stroke-linejoin="round"'+(' stroke-dasharray="10 10"' if dash else '')+'/>')
def polygon(ps,fill,stroke=None,width=2):
    ps=[tuple(q) for q in ps];dr.polygon(ps,fill=fill)
    if stroke:dr.line(ps+[ps[0]],fill=stroke,width=width,joint='curve')
    svg.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in ps)+f'" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
def rect(b,fill,stroke=None):
    x,y,x2,y2=b;polygon([(x,y),(x2,y),(x2,y2),(x,y2)],fill,stroke)
def txt(x,y,s,size=31,col=None,anchor='mm',bg=None):
    col=col or C['ink'];font=ImageFont.truetype(FONT,size)
    if bg:
        bb=dr.textbbox((x,y),s,font=font,anchor=anchor);rect((bb[0]-8,bb[1]-6,bb[2]+8,bb[3]+6),bg)
    dr.text((x,y),s,font=font,fill=col,anchor=anchor)
    # Pillow middle anchor is visually aligned using the actual ink bounding box.
    bx=dr.textbbox((0,0),s,font=font,anchor=anchor)
    svg.append(f'<text x="{x:.2f}" y="{y-(bx[1]+bx[3])/2+size*.36:.2f}" text-anchor="'+('middle' if anchor[0]=='m' else 'start')+f'" font-family="Hiragino Sans GB, sans-serif" font-size="{size}" fill="{col}">'+html.escape(s)+'</text>')
def mt(q,s,size=31,col=None,bg=None):txt(*p(q),s,size,col,bg=bg)
def arrow(a,b,col=None,width=4,both=False,head=14):
    col=col or C['blue'];a,b=tuple(a),tuple(b);line([a,b],col,width)
    def ah(u,v):
        t=math.atan2(v[1]-u[1],v[0]-u[0]);polygon([v,(v[0]-head*math.cos(t-.4),v[1]-head*math.sin(t-.4)),(v[0]-head*math.cos(t+.4),v[1]-head*math.sin(t+.4))],col)
    ah(a,b)
    if both:ah(b,a)
def ma(a,b,col=None,width=4,both=False):arrow(p(a),p(b),col,width,both)
def label(q,title,sub=None):
    mt(q,title,37,bg='#fcfcf8')
    if sub:mt((q[0],q[1]-1.9),sub,25,C['muted'],bg='#fcfcf8')

txt(190,65,'科目二 + 山区专项 · 场地重排草案',57,anchor='lm')
txt(190,128,'V04 / 待确认平面方案     每项目 1 处     总地块 100 × 75 m     只画图，未改 Blender 模型',30,C['muted'],anchor='lm')
line([(190,158),(2590,158)],C['ink'],2)
polygon([p((0,0)),p((100,0)),p((100,75)),p((0,75))],C['green'],'#6f8874',3)
for x in range(10,100,10):line([p((x,0)),p((x,75))],'#d1dec8',1)
for y in range(10,75,10):line([p((0,y)),p((100,y))],'#d1dec8',1)
# Reserve land around the depression; this is a design envelope, not exact terrain.
earth=np.array([(39,68.9),(67,68.9),(73,57),(87,54),(87,35.9),(70,35.9),(60,42),(43,49)])
polygon([p(q) for q in earth],'#dfd4bb')
line([p(q) for q in list(earth)+[earth[0]]],'#b7a37c',2,True)
for sf in surfaces:
    col=C.get(sf['kind'],C['road'])
    polygon([p(q) for q in sf['poly']],col)
# Net-width edges; omit end caps so adjoining pieces read as a continuous road.
for r in routes:
    a=r['rows'];n=np.column_stack([-np.sin(a[:,2]),np.cos(a[:,2])])
    for sg in [-1,1]:line([p(q) for q in a[:,:2]+sg*n*a[:,3:4]/2],'#82918d',2)
for pp in [ra_poly,rev_bay,par_bay,hp_poly,pad]:line([p(q) for q in list(pp)+[pp[0]]],'#82918d',2)
# Parking paint and stop controls.
for x in [rev_x0,rev_x1]:line([p((x,BASE_Y-3.6435)),p((x,BASE_Y+3.6435))],'#fcfcf8',5,True)
for pp in [rev_bay,par_bay]:line([p(q) for q in list(pp)+[pp[0]]],'#fcfcf8',5)
for x in [73-.65,73,73+.65]:line([p((x,HILL_Y-1.75)),p((x,HILL_Y+1.75))],'#cc9b29',6 if x==73 else 3)
for x in [85-up,85-up-6]:line([p((x,HILL_Y-1.75)),p((x,HILL_Y+1.75))],'#93aab5',2)
# Proposed optional modules occupy the existing straight, not separate duplicate roads.
for a,b,col in [(62,72,'#b8d9da'),(75,83.5,'#d0c9df')]:
    polygon([p(q) for q in [(a,BASE_Y-2.25),(b,BASE_Y-2.25),(b,BASE_Y+2.25),(a,BASE_Y+2.25)]],col)
    for x in np.arange(a+.5,b,.9):line([p((x,BASE_Y-2.25)),p((x+.6,BASE_Y+2.25))],'#98b7b6' if a==62 else '#ada3be',1)
# Trace the functional route with directional arrows, not continuous coloured ribbons.
for a,b in [((1,11.5),(11,11.5)),((20,11.5),(24,11.5)),((36,11.5),(41,11.5)),((54,11.5),(57,11.5)),((86,12),(90,13)),((94,20),(94,24)),((88,31),(83,31.5)),((79,31.5),(76,31.5)),((49,31.5),(45,31.5)),((24,31.5),(21,31.5)),((ra_x,41),(ra_x,45)),((sp[0],57),(sp[0],60)),((35,69),(38,70.8)),((85,72),(95,72))]:ma(a,b)
ma((23,70.8),(17,70.8),C['muted']);ma((5,55),(5,48),C['muted']);ma((5,28),(5,23),C['muted'])
for idx in [190,410,700]:
    i=min(idx,len(hp_rows)-15);a=hp_rows[i,:2];b=hp_rows[i+14,:2];ma(a,b,C['orange'],4,True)
# Core labels and restrained leader lines.
label((26.5,21),'01  倒车入库','单库 · 库位 5.558 × 2.447 m')
line([p((26.5,17.5)),p((26.5,15.3))],C['muted'],2)
label((46.5,21),'02  侧方停车','单库 · 库位 8.287 × 2.647 m')
line([p((46.5,17.4)),p((46.5,13.8))],C['muted'],2)
ma((rev_x1,16.3),(par_x0,16.3),C['blue'],2,True)
mt(((rev_x1+par_x0)/2,17.6),'直连 8 m',25,C['blue'],'#fcfcf8')
label((59,39),'03  坡道定点停车 / 起步','10% · 总投影 57.94 m · 顶部 +2.30 m')
line([p((59,35.7)),p((59,33.5))],C['muted'],2)
mt((70,28),'上坡 ←',25,C['blue']);mt((43,28),'← 下坡',25,C['blue']);mt((56,28),'平台 6 m',23,C['muted'])
label((20,25),'04  直角转弯','净宽 3.908 m / 外臂 10 m')
line([p((20,27.3)),p((16,29.5))],C['muted'],2)
label((22.5,60.7),'05  标准 S 弯','R外 7.5 m · 宽 3.5 m · 2 × 135°')
line([p((23,57.4)),p((23,54))],C['muted'],2)
label((82,64),'06  坡度双发卡弯','按 V20 原比例移植 / 专项支线')
line([p((74,61.5)),p((64,60))],C['orange'],2)
mt((81,58.6),'直段约 10°（17.6%）',27,C['orange'],bg='#fcfcf8')
mt((81,56.7),'两弯内夹角 35° · 直段宽 3 m',26,C['orange'],bg='#fcfcf8')
mt((77.1,44.6),'12 × 12 m',31,C['orange'])
mt((77.1,42.4),'低端调头平台',31,C['orange'])
mt((77.1,40.2),f'标高约 {pad_z:.2f} m',25,C['orange'])
mt((76.7,36.7),'多把调头 / 原路上坡返回',24,C['orange'],bg='#fcfcf8')
line([p((66.3,46)),p((70,48.5))],C['orange'],2)
mt((72.5,50.2),'新增约 5.21 m 缓坡接平',24,C['orange'],bg='#fcfcf8')
mt((48.8,66.8),'入口 ±0.00 m',24,C['orange'],bg='#fcfcf8')
mt((51.2,53.1),'C2',24,C['orange'],bg='#fcfcf8');mt((65.2,58.9),'C1',24,C['orange'],bg='#fcfcf8')
mt((4.8,40),'回程',28,C['muted'],bg=C['green'])
mt((69,75.9),'北侧 5 m 双向集散道 · 专项回程向西接回入口',26,C['muted'],bg='#fcfcf8')
mt((97.3,68.1),'主线出口 →',29,C['blue'],bg='#fcfcf8')
mt((4.5,7.5),'入口 →',33,C['blue'],bg='#fcfcf8')
label((65.8,5),'07  雨雾 / 湿滑段','10 m · 普通练习时关闭')
label((82.5,5),'08  模拟隧道','8.5 m · 直路原位加罩')
mt((39.5,43),'绿化 / 检修留地',28,C['muted'])
mt((39.5,41),'为坡道与低洼区留边坡空间',22,C['muted'])
# Scale, orientation and dimension witness lines.
for x in [0,100]:line([p((x,0)),p((x,-2.8))],C['muted'],2)
ma((0,-2.2),(100,-2.2),C['muted'],2,True);mt((50,-2.2),'100 m',28,C['muted'],bg='#fcfcf8')
for y in [0,75]:line([p((0,y)),p((-3.5,y))],C['muted'],2)
ma((-2.5,0),(-2.5,75),C['muted'],2,True)
txt(*p((-4.3,37.5)),'75 m',28,C['muted'])
ma((96,59),(96,64),C['ink'],4);mt((96,65.5),'N',33)
for i in range(4):
    a=p((87+i*2.5,3));b=p((89.5+i*2.5,2.55));rect((*a,*b),C['ink'] if i%2==0 else '#fcfcf8',C['ink'])
mt((87,1.3),'0',23);mt((97,1.3),'10 m',23)

# The footer is part of the approval sheet, not a construction certification.
line([(190,2075),(2590,2075)],C['ink'],2)
txt(190,2120,'布局变化',35,anchor='lm')
txt(190,2174,'倒库 → 侧方：原约 45.4 m 绕行 → 8.0 m 直连；五项各一处，考试尺寸沿用已确认参数。',31,anchor='lm')
txt(190,2226,'同一块 7,500 m² 地块：五项基础训练 + 原坡度发卡弯 + 两处直线扩展，不复制库位。',31,anchor='lm')
txt(190,2278,'橙色支线为单车往返；低端平台和接平段是新增设计。隧道、雨雾 / 湿滑为可选扩展。',31,anchor='lm')
txt(190,2332,'确认重点：项目顺序、发卡弯往返方式、两项扩展是否保留。仅平面规划，尚未校核车辆转弯轨迹。',29,C['muted'],anchor='lm')
im.save(D/'layout_v04.png');svg.append('</svg>');(D/'layout_v04.svg').write_text('\n'.join(svg))

# Independent 2D raster footprint checks (5 cm grid); intentionally joined road ends excluded.
RES=20
def mask(polys):
    img=Image.new('1',(int(SITE[0]*RES)+1,int(SITE[1]*RES)+1));dd=ImageDraw.Draw(img)
    for pp in polys:dd.polygon([(float(x*RES),float(y*RES)) for x,y in pp],fill=1)
    return np.asarray(img,dtype=bool)
basic=[s['poly'] for s in surfaces if s['kind'] not in ['hairpin','hairpin_new','collector','return'] and s['name']!='接入集散道']
special=[s['poly'] for s in surfaces if s['kind'] in ['hairpin','hairpin_new']]
overlap=int(np.count_nonzero(mask(basic)&mask(special)))/RES**2
outside=[]
for sf in surfaces:
    q=sf['poly'];bad=(q[:,0]<-1e-6)|(q[:,0]>100+1e-6)|(q[:,1]<-1e-6)|(q[:,1]>75+1e-6)
    if bad.any():outside.append(sf['name'])
old_connector=4+10*math.pi+8+2
report={'status':'proposed_unconfirmed','blender_started_or_modified':False,'site_m':SITE,'site_area_m2':7500,'one_of_each_basic_project':True,'old_reverse_to_parallel_connector_m':old_connector,'new_reverse_to_parallel_connector_m':8.,'connector_reduction_percent':100*(1-8/old_connector),'basic_vs_special_pavement_overlap_m2_at_5cm_resolution':overlap,'road_footprints_outside_site':outside,'hairpin_source':'V20 small_road.dae in existing BeamNG V3 ZIP, read only','hairpin_xy_transform':{'rotation_degrees':0,'scale':1,'translation_m':SHIFT.tolist()},'hairpin_original_tail_z_m':float(hp_profile(hp_length)),'new_vertical_transition':{'radius_m':30,'horizontal_m':ease_length,'extra_drop_m':ease_drop},'new_low_pad':{'size_m':[12,12],'z_m':pad_z},'new_flat_curve_radius_m':6,'normal_connector_radius_m':10,'s_curve_end_to_collector_curve_straight_m':61.5-float(sp[1]),'caveats':['Planning footprint only; kerbs, earthworks, retaining walls, vertical joining and vehicle swept paths need detailed design after approval.','12 m pad is a multi-point turnaround allowance, not a demonstrated one-manoeuvre turning circle.','Original steep-road dynamic driving has not been verified.','The old approved training dimensions are retained; this is not a certified official examination facility.']}
(D/'layout_parameters.json').write_text(json.dumps({'report':report,'approved_dimensions':OLD['dimensions'],'proposed_sequence':['01倒库','02侧方','07雨雾/湿滑（可关闭）','08隧道（可选）','03坡道','04直角','05标准S','主线出口或06发卡弯支线'],'route_segments':[{'name':q['name'],'kind':q['kind'],'start':q['rows'][0].tolist(),'end':q['rows'][-1].tolist()} for q in routes],'road_footprints':[{'name':s['name'],'kind':s['kind'],'points_m':np.round(s['poly'][::max(1,len(s['poly'])//1000)],5).tolist()} for s in surfaces]},ensure_ascii=False,indent=2))
(D/'planning_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
assert overlap==0, 'Special pavement intersects a basic route'
assert not outside, 'A road leaves the site'
