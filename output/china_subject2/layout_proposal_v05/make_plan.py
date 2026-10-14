"""V05: five-project-only 2D plan; does not run Blender or load hairpin assets."""
from pathlib import Path
import json, math, html
import numpy as np
from PIL import Image, ImageDraw, ImageFont
D=Path(__file__).resolve().parent
PARAM=json.loads((D.parent/'parameters.json').read_text())
SITE=(80.,60.); routes=[]; surfaces=[]
W,H=2500,2170;S=27;X0,Y0=170,1810
im=Image.new('RGB',(W,H),'#fcfcf8');dr=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="#fcfcf8"/>']
FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
C={'ink':'#21383d','muted':'#58716e','green':'#dfe9d7','road':'#eef1ed','exam':'#dce9ef','hill':'#cbdde8','blue':'#29719d'}
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

# Net dimensions come from the already approved parameter file.
d=PARAM['dimensions'];defaults=PARAM['design_defaults'];by=11.5
rv,pv,sv,cv=d['reverse'],d['parallel'],d['s_curve'],d['right_angle']
rx0=6.;rx1=rx0+2*rv['control_each_side']+rv['width']
px0=rx1+8.;px1=px0+pv['length']
add('入口',straight((0,by),(2,by),4.5))
add('倒库入口渐变',straight((2,by),(rx0,by),4.5,rv['aisle_width']))
add('01倒库车道',straight((rx0,by),(rx1,by),rv['aisle_width']),'exam')
add('倒库至侧方8米直连',straight((rx1,by),(px0,by),rv['aisle_width'],pv['lane_width']))
add('02侧方车道',straight((px0,by),(px1+7.5,by),pv['lane_width']),'exam')
add('侧方至S弯',straight((px1+7.5,by),(50,by),pv['lane_width'],sv['width']))
sr=(sv['inner_radius']+sv['outer_radius'])/2;angle=math.radians(sv['angle_degrees'])
s1=arc((50,by),0,angle,sr,sv['width']);s2=arc(s1[-1,:2],s1[-1,2],-angle,sr,sv['width'])
add('03S弯第一段',s1,'exam');se=add('03S弯第二段',s2,'exam')
ra_entry=se+np.array([7.5,0]); cw=cv['width'];arm=defaults['right_angle_outer_arm'];shift=arm-cw/2
corner=ra_entry+np.array([shift,0]);ra_exit=corner+np.array([0,shift])
add('S弯至直角7.5米',straight(se,ra_entry,sv['width'],cw))
cx,cy=corner;ex=ra_entry[0];ey=ra_exit[1]
ra=np.array([(ex,cy-cw/2),(cx+cw/2,cy-cw/2),(cx+cw/2,ey),(cx-cw/2,ey),(cx-cw/2,cy+cw/2),(ex,cy+cw/2)])
surfaces.append(dict(name='04直角转弯',poly=ra,kind='exam'))
turn_start=ra_exit+np.array([0,7.5])
add('直角出口7.5米',straight(ra_exit,turn_start,cw,4.5))
hill_start=add('连接坡道',arc(turn_start,math.pi/2,math.pi/2,10,4.5,3.5))
grade=d['ramp']['grade'];radius=defaults['ramp_vertical_radius'];constant=defaults['ramp_constant_grade_horizontal'];platform=defaults['ramp_platform_length']
run=radius*math.sin(math.atan(grade));rise=radius*(1-math.cos(math.atan(grade)))
up=constant+2*run;hill_total=2*up+platform;hill_h=constant*grade+2*rise
hill_end=hill_start-np.array([hill_total,0])
add('05坡道',straight(hill_start,hill_end,d['ramp']['width']),'hill')
add('出口',straight(hill_end,(0,hill_end[1]),3.5,4.5))
ry=by-rv['aisle_width']/2
bay=np.array([(rx0+rv['control_each_side'],ry),(rx0+rv['control_each_side']+rv['width'],ry),(rx0+rv['control_each_side']+rv['width'],ry-rv['length']),(rx0+rv['control_each_side'],ry-rv['length'])])
py=by-pv['lane_width']/2
pb=np.array([(px0,py),(px1,py),(px1,py-pv['width']),(px0,py-pv['width'])])
surfaces.extend([dict(name='倒库库位',poly=bay,kind='exam'),dict(name='侧方库位',poly=pb,kind='exam')])

txt(170,62,'科目二五项 · 紧凑布局草案',58,anchor='lm')
txt(170,124,'V05 / 待确认     五项各一处     倒库与侧方直连     保持已确认项目尺寸',31,C['muted'],anchor='lm')
line([(170,160),(2330,160)],C['ink'],2)
polygon([p((0,0)),p((80,0)),p((80,60)),p((0,60))],C['green'],'#6f8874',3)
for x in range(10,80,10):line([p((x,0)),p((x,60))],'#d1dec8',1)
for y in range(10,60,10):line([p((0,y)),p((80,y))],'#d1dec8',1)
for sf in surfaces:polygon([p(q) for q in sf['poly']],C.get(sf['kind'],C['road']))
for r in routes:
    a=r['rows'];n=np.column_stack([-np.sin(a[:,2]),np.cos(a[:,2])])
    for sg in [-1,1]:line([p(q) for q in a[:,:2]+sg*n*a[:,3:4]/2],'#82918d',2)
for pp in [ra,bay,pb]:line([p(q) for q in list(pp)+[pp[0]]],'#82918d',2)
for x in [rx0,rx1]:line([p((x,by-rv['aisle_width']/2)),p((x,by+rv['aisle_width']/2))],'#fcfcf8',5,True)
for pp in [bay,pb]:line([p(q) for q in list(pp)+[pp[0]]],'#fcfcf8',5)
stop=hill_start[0]-defaults['ramp_stop_horizontal_station']
for x in [stop-.65,stop,stop+.65]:line([p((x,hill_start[1]-1.75)),p((x,hill_start[1]+1.75))],'#cc9b29',6 if x==stop else 3)
for x in [hill_start[0]-up,hill_start[0]-up-platform]:line([p((x,hill_start[1]-1.75)),p((x,hill_start[1]+1.75))],'#93aab5',2)
for a,b in [((0.5,by),(4,by)),((8,by),(12,by)),((25,by),(29,by)),((42,by),(46,by)),((59,cy),(63,cy)),((cx,40.3),(cx,44.5)),((71.9,51),(69.7,53.5)),((61,hill_start[1]),(56,hill_start[1])),((29,hill_start[1]),(24,hill_start[1])),((4,hill_start[1]),(.5,hill_start[1]))]:ma(a,b)
for rr in [s1,s2]:
    k=len(rr)//2;ma(rr[k-10,:2],rr[k+10,:2])
label((14.5,22),'01  倒车入库','库位 5.558 × 2.447 m')
mt((14.5,18.2),'库前车道净宽 7.287 m',25,C['muted'],bg='#fcfcf8')
line([p((14.5,16.8)),p((14.5,15.4))],C['muted'],2)
label((35.2,22),'02  侧方停车','库位 8.287 × 2.647 m')
mt((35.2,18.2),'旁侧车道净宽 3.5705 m',25,C['muted'],bg='#fcfcf8')
line([p((35.2,16.8)),p((35.2,13.6))],C['muted'],2)
ma((rx1,15.6),(px0,15.6),C['blue'],2,True)
mt(((rx1+px0)/2,16.8),'直连 8 m',25,C['blue'],bg='#fcfcf8')
label((42,36),'03  曲线行驶（S 弯）','R外 7.5 m · 净宽 3.5 m')
mt((42,32.3),'两段反向相切 135° 圆弧',25,C['muted'],bg='#fcfcf8')
line([p((49,31.7)),p((54,27))],C['muted'],2)
label((65.5,24),'04  直角转弯','净宽 3.908 m / 外臂 10 m')
line([p((67,26)),p((69,29.3))],C['muted'],2)
label((36,49),'05  坡道定点停车 / 起步','10% · 总投影 57.94 m · 高约 2.30 m')
line([p((36,51.2)),p((36,54.7))],C['muted'],2)
mt((51.5,53.5),'上坡 ←',25,C['blue']);mt((21,53.5),'← 下坡',25,C['blue']);mt((34.7,53.5),'平台 6 m',24,C['muted'])
mt((7,7.3),'入口 →',35,C['blue'],bg='#fcfcf8')
mt((7,53),'← 出口',35,C['blue'],bg='#fcfcf8')
mt((20,39.5),'绿化与检修留地',31,C['muted'])
mt((20,37.5),'不再布置额外训练项目',25,C['muted'])
ma((76.5,5),(76.5,10),C['ink'],4);mt((76.5,11.5),'N',32)
for i in range(4):
    a=p((62+i*2.5,3));b=p((64.5+i*2.5,2.55));rect((*a,*b),C['ink'] if i%2==0 else '#fcfcf8',C['ink'])
mt((62,1.4),'0',23);mt((72,1.4),'10 m',23)
for x in [0,80]:line([p((x,0)),p((x,-2.8))],C['muted'],2)
ma((0,-2.2),(80,-2.2),C['muted'],2,True);mt((40,-2.2),'80 m',29,C['muted'],bg='#fcfcf8')
for y in [0,60]:line([p((0,y)),p((-3,y))],C['muted'],2)
ma((-2.3,0),(-2.3,60),C['muted'],2,True);mt((-4.3,30),'60 m',29,C['muted'])
line([(170,1930),(2330,1930)],C['ink'],2)
txt(170,1980,'地块建议 80 × 60 m = 4,800 m²，比原 100 × 75 m 缩小 36%；项目净尺寸不缩放。',32,anchor='lm')
txt(170,2032,'路线：入口 → 倒库 → 侧方 → S 弯 → 直角 → 坡道 → 出口。五项各一处。',32,anchor='lm')
txt(170,2084,'仅平面规划；本版待确认，Blender 模型尚未修改。',29,C['muted'],anchor='lm')
im.save(D/'layout_v05.png');svg.append('</svg>');(D/'layout_v05.svg').write_text('\n'.join(svg))

outside=[]
for sf in surfaces:
    q=sf['poly'];bad=(q[:,0]<-1e-6)|(q[:,0]>SITE[0]+1e-6)|(q[:,1]<-1e-6)|(q[:,1]>SITE[1]+1e-6)
    if bad.any():outside.append(sf['name'])
RES=20
def mask(pp):
    m=Image.new('1',(int(SITE[0]*RES)+1,int(SITE[1]*RES)+1));dd=ImageDraw.Draw(m)
    dd.polygon([(float(x*RES),float(y*RES)) for x,y in pp],fill=1)
    return np.asarray(m,bool)
project_polys={'reverse':[strip(routes[2]['rows']),bay], 'parallel':[strip(routes[4]['rows']),pb], 's_curve':[strip(s1),strip(s2)], 'right_angle':[ra], 'ramp':[next(sf['poly'] for sf in surfaces if sf['name']=='05坡道')]}
masks={k:np.logical_or.reduce([mask(p) for p in pp]) for k,pp in project_polys.items()}
overlaps={}
keys=list(masks)
for i,a in enumerate(keys):
    for b in keys[i+1:]:
        area=np.count_nonzero(masks[a]&masks[b])/RES**2
        if area:overlaps[a+' / '+b]=area
report={'status':'pending_user_confirmation','blender_modified':False,'site_m':SITE,'area_m2':4800,'area_reduction_vs_v03_percent':36,'project_counts':{k:1 for k in project_polys},'extra_projects':[],'reverse_to_parallel_connector_m':8,'approved_dimensions':d,'hill':{'horizontal_total_m':hill_total,'height_m':hill_h,'start':hill_start.tolist(),'end':hill_end.tolist()},'road_polygons_outside_site':outside,'project_overlap_m2_at_5cm_grid':overlaps,'clearance_note':'Planning net pavement only; exact shoulders, signs, ramp earthworks and swept paths await approved detailed design.'}
(D/'planning_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(D/'layout_parameters.json').write_text(json.dumps({'report':report,'routes':[{'name':r['name'],'kind':r['kind'],'start':r['rows'][0].tolist(),'end':r['rows'][-1].tolist()} for r in routes],'footprints':[{'name':s['name'],'points_m':s['poly'].tolist()} for s in surfaces]},ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2));assert not outside and not overlaps
