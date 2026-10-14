from PIL import Image, ImageDraw, ImageFont
import math,json,csv,html
from pathlib import Path
D=Path(__file__).resolve().parent
W,H=2600,1900
im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
INK='#26394a'; MUT='#647687'; BLUE='#42bce8'; GREEN='#8de27c'; YELLOW='#f5d95b'; DIM='#536f8c'; RED='#bd5261'
def poly(ps,fill,outline=None,width=2):
 d.polygon(ps,fill=fill)
 if outline:d.line(ps+[ps[0]],fill=outline,width=width,joint='curve')
 svg.append(f'<polygon points="'+ ' '.join(f'{x:.2f},{y:.2f}' for x,y in ps)+f'" fill="{fill}" stroke="{outline or "none"}" stroke-width="{width}"/>')
def line(ps,color=INK,width=2,dash=False):
 if len(ps)<2:return
 if dash:
  # SVG dash lengths and raster dash lengths both in drawing pixels.
  phase=0
  for a,b in zip(ps,ps[1:]):
   le=math.dist(a,b);steps=max(1,math.ceil(le/2))
   for k in range(steps):
    t=k/steps;t2=(k+1)/steps
    if int((phase+le*t)/9)%2==0:d.line([(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),(a[0]+(b[0]-a[0])*t2,a[1]+(b[1]-a[1])*t2)],fill=color,width=width)
   phase+=le
 else:d.line(ps,fill=color,width=width,joint='curve')
 svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in ps)+f'" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"'+(' stroke-dasharray="9 9"' if dash else '')+'/>')
def rect(box,fill,outline=None):
 x,y,x2,y2=box;poly([(x,y),(x2,y),(x2,y2),(x,y2)],fill,outline)
def text(x,y,s,size=28,color=INK,anchor='la',bg=False):
 f=ImageFont.truetype(FONT,size); bb=d.textbbox((x,y),s,font=f,anchor=anchor)
 if bg:rect((bb[0]-7,bb[1]-3,bb[2]+7,bb[3]+5),'white')
 d.text((x,y),s,font=f,fill=color,anchor=anchor)
 svg.append(f'<text x="{x}" y="{y+size if anchor.endswith("a") else y}" font-family="Hiragino Sans GB,Microsoft YaHei,sans-serif" font-size="{size}" fill="{color}" text-anchor="'+('middle' if anchor[0]=='m' else 'start')+'">'+html.escape(s)+'</text>')
def dot(p,r=5,color=INK):
 x,y=p;d.ellipse((x-r,y-r,x+r,y+r),fill=color);svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')
def arrow(a,b,color=DIM,width=2,both=False):
 line([a,b],color,width)
 def head(p,q):
  an=math.atan2(q[1]-p[1],q[0]-p[0]);sz=12
  poly([q,(q[0]-sz*math.cos(an-.35),q[1]-sz*math.sin(an-.35)),(q[0]-sz*math.cos(an+.35),q[1]-sz*math.sin(an+.35))],color)
 head(a,b)
 if both:head(b,a)
def P(p):return (150+33*p[0],1720-33*p[1])
def off(row,k):
 t=math.radians(row['heading_deg']);return(row['x']-k*math.sin(t),row['y']+k*math.cos(t))
road_w=2.775; main_w=4.; half=road_w/2
segs=[];samples=[];keys=[];p=(11.,44.);h=-25.;s=0
for i,(kind,val,turn) in enumerate([('line',20.,0),('arc',1.9875,-145.),('line',12.,0),('arc',1.9875,145.),('line',8.,0)]):
 start=p;h0=h;ln=val if kind=='line' else val*math.radians(abs(turn));n=math.ceil(ln/.04);c=None
 if kind=='arc':
  sg=1 if turn>0 else -1;t=math.radians(h);c=(p[0]-sg*val*math.sin(t),p[1]+sg*val*math.cos(t))
 rows=[]
 for j in range(n+1):
  u=j/n;hh=h0+turn*u;t=math.radians(hh)
  if kind=='line':q=(start[0]+ln*u*math.cos(t),start[1]+ln*u*math.sin(t))
  else:q=(c[0]+sg*val*math.sin(t),c[1]-sg*val*math.cos(t))
  row={'station_m':s+ln*u,'x':q[0],'y':q[1],'z':0.,'heading_deg':hh,'segment':i+1};rows.append(row)
 samples.extend(rows if i==0 else rows[1:]);keys.append({'id':f'P{i}','x':start[0],'y':start[1],'station_m':s})
 p=q;h=hh
 segs.append({'id':f'S{i+1}' if kind=='line' else ('C1' if i==1 else 'C2'),'kind':kind,'start':start,'end':p,'start_station_m':s,'length_m':ln,'start_heading_deg':h0,'end_heading_deg':h,'radius_m':val if kind=='arc' else None,'turn_deg':turn,'inner_included_angle_deg':180-abs(turn) if kind=='arc' else None,'center':c,'inner_radius_m':val-half if kind=='arc' else None,'outer_radius_m':val+half if kind=='arc' else None})
 s+=ln
keys.append({'id':'P5','x':p[0],'y':p[1],'station_m':s})
for seg in segs:
 if seg['kind']!='arc':continue
 sg=1 if seg['turn_deg']>0 else -1
 t0=math.radians(seg['start_heading_deg']);t1=math.radians(seg['end_heading_deg'])
 aa=(seg['start'][0]-sg*half*math.sin(t0),seg['start'][1]+sg*half*math.cos(t0))
 bb=(seg['end'][0]-sg*half*math.sin(t1),seg['end'][1]+sg*half*math.cos(t1))
 run=seg['inner_radius_m']*math.tan(math.radians(abs(seg['turn_deg'])/2))
 pi=(aa[0]+run*math.cos(t0),aa[1]+run*math.sin(t0))
 seg['inner_tangent_start']=aa;seg['inner_tangent_end']=bb;seg['inner_tangent_intersection']=pi

def side_clip(k,yclip=42):
 out=[]
 for a,b in zip(samples,samples[1:]):
  aa=off(a,k);bb=off(b,k)
  if aa[1]>yclip>=bb[1]:
   t=(yclip-aa[1])/(bb[1]-aa[1]);out.append((aa[0]+t*(bb[0]-aa[0]),yclip))
  if bb[1]<=yclip:out.append(bb)
 return out
right=side_clip(-half);left=side_clip(half)
boundary=[(0,42)]+right+list(reversed(left))+[(44,42),(44,46),(0,46)]
# Main header
text(90,40,'手绘道路 · 参数化俯视图',48)
text(92,105,'道路俯视图  /  V5.0 · C1 / C2 内夹角 = 35° · 内侧圆角 R0.60  /  单位：米  /  原图结构保留，几何尺寸重建',23,MUT)
line([(90,145),(2510,145)],INK,2)
# metric grid
for x in range(0,46,5):
 line([P((x,5)),P((x,46))],'#ecf0f3',1);text(P((x,5))[0],1570,str(x),18,MUT,'ma')
for y in range(5,46,5):
 line([P((0,y)),P((46,y))],'#ecf0f3',1);text(102,P((0,y))[1]-15,str(y),18,MUT)
# zone strips sampled by chainage; sides relative to P0 -> P5
s1=segs[1]['start_station_m'];mid=s1+segs[1]['length_m']/2;s3=segs[3]['start_station_m'];e3=s3+segs[3]['length_m']
# left external side on first right bend; right internal side first bend
zones=[{'id':'G1','type':'berm','side':'left','from_m':8.8,'to_m':mid}, {'id':'Y1','type':'unguarded_edge','side':'right','from_m':2.,'to_m':mid}, {'id':'Y2','type':'unguarded_edge','side':'left','from_m':mid,'to_m':s3}, {'id':'G2','type':'berm','side':'right','from_m':mid,'to_m':s3}, {'id':'G3','type':'berm','side':'left','from_m':s3,'to_m':s}, {'id':'Y3','type':'unguarded_edge','side':'right','from_m':s3,'to_m':s}]
for zone in zones:
 sg=1 if zone['side']=='left' else -1
 rows=[r for r in samples if zone['from_m']<=r['station_m']<=zone['to_m']]
 inner=[off(r,sg*(half+.10)) for r in rows];outer=[off(r,sg*(half+.50)) for r in rows]
 zone['marker_polyline']=[off(r,sg*(half+.30)) for r in rows]
 poly([P(q) for q in inner+outer[::-1]],GREEN if zone['type']=='berm' else YELLOW)
# unified surface
poly([P(q) for q in boundary],'#f3f5f7',INK,3)
# guardrail exactly open at junction plus .3m terminal setback
rail_y=41.6
rr=side_clip(-(half+.4),rail_y)[0][0];ll=side_clip(half+.4,rail_y)[0][0]
rails=[[(0,46.4),(44,46.4)],[(0,41.6),(rr-.3,41.6)],[(ll+.3,41.6),(44,41.6)]]
for rail in rails:line([P(q) for q in rail],BLUE,10)
# axis / construction centerline (not lane paint)
line([P((0,44)),P((44,44))],DIM,2,True)
line([P((r['x'],r['y'])) for r in samples],DIM,2,True)
# vehicle footprint on middle straight
carrow=min(samples,key=lambda r:abs(r['station_m']-(s3-4.2)));ct=(carrow['x'],carrow['y']);ang=math.radians(carrow['heading_deg']);u=(math.cos(ang),math.sin(ang));v=(-u[1],u[0])
car=[(ct[0]+a*u[0]+b*v[0],ct[1]+a*u[1]+b*v[1]) for a,b in [(-2.503,-.925),(2.503,-.925),(2.503,.925),(-2.503,.925)]]
poly([P(q) for q in car],'#d6e8fa','#528abd',3)
arrow(P((ct[0]-u[0],ct[1]-u[1])),P((ct[0]+u[0],ct[1]+u[1])),'#528abd',3)
# dimension main length
for x in [0,44]:line([(P((x,0))[0],185),(P((x,0))[0],200)],DIM)
arrow((150,184),(1602,184),DIM,both=True);text(876,148,'大路绘制长度 44.00 m',24,DIM,'ma',True)
# main width arrow at far right
arrow(P((40,42)),P((40,46)),DIM,both=True);text(*P((40.8,45.3)),'4.00 m',27,DIM,bg=True)
# narrow width cross first line at station 12
rw=min(samples,key=lambda r:abs(r['station_m']-12))
a=off(rw,-half);b=off(rw,half);arrow(P(a),P(b),RED,3,True)
line([P(a),(P(a)[0]-95,P(a)[1]+55)],RED,2);text(P(a)[0]-320,P(a)[1]+60,'小路净宽 2.775 m',29,RED,bg=True)
# segment labels in whitespace
text(970,402,'直线 20.00 m · 航向 -25°',27,DIM,bg=True)
text(1080,780,'直线 12.00 m · 航向 -170°',26,DIM,bg=True)
text(920,1000,'直线 8.00 m · 航向 -25°',26,DIM,bg=True)
# curve constructions and text
for idx in [1,3]:
 seg=segs[idx];c=seg['center'];a=seg['start'];b=seg['end']
 dot(P(c),3,DIM)
 # Curve IDs are in the leaders.
 hmid=(seg['start_heading_deg']+seg['end_heading_deg'])/2;sg=1 if seg['turn_deg']>0 else -1;t=math.radians(hmid)
 q=(c[0]+sg*seg['radius_m']*math.sin(t),c[1]-sg*seg['radius_m']*math.cos(t))
 arrow(P(c),P(q),DIM)
 if idx==1:
  tx,ty=1330,500
  line([P(q),(tx-30,ty+60)],DIM)
 else:
  tx,ty=175,860
  line([P(q),(tx+225,ty+60)],DIM)
 text(tx,ty,seg['id']+'  内夹角 35°',32,INK,bg=True)
 text(tx,ty+44,('右转' if sg<0 else '左转')+' 145°（对应转向角）',23,RED,bg=True)
 text(tx,ty+83,f'内侧圆角 R = {seg["inner_radius_m"]:.2f} m',27,RED,bg=True)
 text(tx,ty+123,f'中心线 R = {seg["radius_m"]:.4f}',22,MUT,bg=True)
 text(tx,ty+158,f'外侧 R = {seg["outer_radius_m"]:.4f}',22,MUT,bg=True)
# Enlarged C2 profile. C1 is its mirror; all dimensions identical.
rect((175,1160,1400,1635),'#f7f9fb','#d7e0e7')
text(200,1180,'弯道局部放大 · C2（C1 镜像同形）',29,INK)
text(200,1234,'内夹角：35°',27,RED)
text(200,1280,'内侧仅留 R0.60 m 小圆角',26,RED)
text(200,1328,'路面净宽：2.775 m',25,INK)
text(200,1373,'外侧半径：3.375 m',24,MUT)
text(200,1420,'直路 → 短圆角 → 直路',23,MUT)
text(200,1510,'本轮建议值，按参考图收紧造型。',22,MUT)
def Z(q):return (965+40*q[0],1400-40*q[1])
r=1.9875
rows=[]
t0=math.radians(-162.5);t1=math.radians(-17.5)
start=(r*math.sin(t0),-r*math.cos(t0));end=(r*math.sin(t1),-r*math.cos(t1))
for j in range(31):
 t=j/30;rows.append({'x':start[0]-5*(1-t)*math.cos(t0),'y':start[1]-5*(1-t)*math.sin(t0),'heading_deg':-162.5})
for j in range(1,121):
 h=-162.5+145*j/120;t=math.radians(h);rows.append({'x':r*math.sin(t),'y':-r*math.cos(t),'heading_deg':h})
for j in range(1,31):
 t=j/30;rows.append({'x':end[0]+5*t*math.cos(t1),'y':end[1]+5*t*math.sin(t1),'heading_deg':-17.5})
inside=[off(row,half) for row in rows];outside=[off(row,-half) for row in rows]
poly([Z(q) for q in outside+inside[::-1]],'#e9eef3',INK,3)
line([Z((row['x'],row['y'])) for row in rows],DIM,2,True)
# Actual inner-edge virtual apex and its 35-degree opening.
ai=(.6*math.sin(t0),-.6*math.cos(t0));bi=(.6*math.sin(t1),-.6*math.cos(t1))
length=.6*math.tan(math.radians(72.5));vi=(ai[0]+length*math.cos(t0),ai[1]+length*math.sin(t0))
line([Z(ai),Z(vi),Z(bi)],RED,2,True)
arc=[(vi[0]+1.3*math.cos(math.radians(a)),vi[1]+1.3*math.sin(math.radians(a))) for a in [(-17.5+35*j/40) for j in range(41)]]
line([Z(q) for q in arc],RED,3)
text(*Z((vi[0]+3.1,-.3)),'35°',25,RED,'ma',True)
# Emphasize only the tiny inner fillet in red.
fillet=[(.6*math.sin(math.radians(-162.5+145*j/100)),-.6*math.cos(math.radians(-162.5+145*j/100))) for j in range(101)]
line([Z(q) for q in fillet],RED,5)
line([Z((-.6,0)),(1090,1360),(1170,1330)],RED,2)
text(1100,1288,'R0.60 m',24,RED,bg=True)
# points
label_offsets=[(-35,-48),(-35,-42),(18,6),(-65,-42),(17,12),(18,2)]
for key,(dx,dy) in zip(keys,label_offsets):
 q=P((key['x'],key['y']));dot(q,5);text(q[0]+dx,q[1]+dy,key['id'],24,INK,bg=True)
text(500,332,'接入角 25°',25,DIM,bg=True)
# axes, scale
arrow((1480,1460),(1610,1460),DIM);arrow((1480,1460),(1480,1330),DIM)
text(1620,1440,'+X',21,DIM);text(1463,1290,'+Y',21,DIM)
# Orientation arrows identify +X and +Y.
for i in range(4):rect((1420+i*82.5,1580,1502.5+i*82.5,1594),INK if i%2==0 else '#bbc9d3')
text(1420,1603,'0',20,MUT);text(1750,1603,'10 m',20,MUT,'ma')
# right panel
rect((1790,195,2510,1635),'#f4f7fa')
def heading(y,t):text(1825,y,t,30);line([(1825,y+51),(2470,y+51)],'#cdd8e0')
heading(218,'01  尺寸基准')
for y,t in [(287,'大路路面宽：4.000 m'),(334,'小路路面宽：2.775 m'),(381,'取帕萨特 Pro 车身宽：1.850 m'),(428,'计算：1.850 × 1.5 = 2.775'),(475,'车身居中时，每侧余量 0.4625 m')]:text(1825,y,t,25)
text(1825,523,'宽度不另加路肩；车宽不计后视镜。',23,MUT)
heading(590,'02  防护与地形图例')
for y,col,t in [(671,BLUE,'蓝色｜大路两侧护栏，路口留空'),(734,GREEN,'绿色｜土坡防护区'),(797,YELLOW,'黄色｜无护栏边坎')]:
 line([(1828,y+20),(1908,y+20)],col,18);text(1930,y,t,24)
text(1825,859,'色带仅表达区域，不计入路面宽。',23,MUT)
text(1825,900,'虚线为建模中心线，不是道路标线。',23,MUT)
heading(966,'03  图纸定位坐标')
text(1825,1038,'点       X / m        Y / m        里程 / m',24,MUT)
for j,k in enumerate(keys):
 text(1825,1085+j*45,f'{k["id"]}     {k["x"]:7.3f}      {k["y"]:7.3f}       {k["station_m"]:7.3f}',23)
text(1825,1380,f'小路中心线总长：{s:.3f} m',25)
text(1825,1425,'全部 Z = 0；高差与纵坡待定。',24,MUT)
text(1825,1470,'1 Blender Unit = 1 m',24,MUT)
text(1825,1520,'本版仅更新图纸。',23,MUT)
# footer
line([(90,1670),(2510,1670)],INK,2)
text(92,1700,'建模说明',29)
text(92,1750,'本轮造型建议：C1 / C2 内夹角均为 35°，内侧圆角均为 R0.60 m；大路 4 m、小路 2.775 m。',25,MUT)
text(92,1800,'内夹角取两侧直线内边缘的开口角；仅作造型图，未校核帕萨特转弯轨迹。本版不制作 Blender 底模。',24,MUT)
text(2390,1844,'PLAN 05',22,MUT)
im.save(D/'road_plan.png');svg.append('</svg>');(D/'road_plan.svg').write_text('\n'.join(svg))

for seg in segs:
 if seg['kind']!='arc':continue
 vertex=seg['inner_tangent_intersection']
 va=[x-y for x,y in zip(seg['inner_tangent_start'],vertex)]
 vb=[x-y for x,y in zip(seg['inner_tangent_end'],vertex)]
 measured=math.degrees(math.acos(sum(x*y for x,y in zip(va,vb))/(math.hypot(*va)*math.hypot(*vb))))
 assert abs(measured-35)<1e-8
 print(seg['id'], 'inner opening degrees:', measured)
