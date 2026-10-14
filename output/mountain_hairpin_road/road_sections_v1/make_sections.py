from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math,json,csv,zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from pypdf import PdfReader
D=Path(__file__).resolve().parent
W,H=2400,1600;FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
INK='#233c50';MUT='#667d8e';BLUE='#168bb7';GREEN='#60b26d';GPALE='#ddeddb';YELLOW='#d6ad36';RED='#ba5261';GRID='#e8edf1'
class Sheet:
 def __init__(self,title,sub,num):
  self.im=Image.new('RGB',(W,H),'white');self.d=ImageDraw.Draw(self.im)
  self.text(85,48,title,45);self.text(88,124,sub,24,MUT);self.line([(85,182),(2315,182)],INK,2)
  self.text(85,1508,'方案 A · 高程及地形尺寸为建议值，待确认；平面依据已确认 V5。',23,MUT)
  self.text(2180,1510,f'{num:02d} / 05',22,MUT)
 def text(self,x,y,t,size=26,c=INK,anchor='la',bg=False):
  f=ImageFont.truetype(FONT,size)
  if bg:
   bb=self.d.textbbox((x,y),t,font=f,anchor=anchor);self.d.rectangle((bb[0]-6,bb[1]-3,bb[2]+6,bb[3]+4),fill='white')
  self.d.text((x,y),t,font=f,fill=c,anchor=anchor)
 def line(self,pts,c=INK,w=2,dash=False):
  if not dash:self.d.line(pts,fill=c,width=w,joint='curve');return
  for a,b in zip(pts,pts[1:]):
   length=math.dist(a,b);n=max(1,math.ceil(length/12))
   for j in range(n):
    t=j/n;tt=min(1,t+6/max(length,1))
    self.d.line([(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),(a[0]+(b[0]-a[0])*tt,a[1]+(b[1]-a[1])*tt)],fill=c,width=w)
 def rect(self,box,c,edge=None):self.d.rectangle(box,fill=c,outline=edge,width=2)
 def poly(self,pts,c):self.d.polygon(pts,fill=c)
 def dot(self,p,r=5,c=BLUE):self.d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill=c)
 def arrow(self,a,b,c=BLUE,both=False,w=2):
  self.line([a,b],c,w)
  def tip(p,q):
   t=math.atan2(q[1]-p[1],q[0]-p[0]);r=12
   self.poly([q,(q[0]-r*math.cos(t-.35),q[1]-r*math.sin(t-.35)),(q[0]-r*math.cos(t+.35),q[1]-r*math.sin(t+.35))],c)
  tip(a,b)
  if both:tip(b,a)
 def panel(self,title):
  self.rect((1830,245,2315,1410),'#f4f7fa');self.text(1860,274,title,30);self.line([(1860,326),(2285,326)],'#cbd7df')
 def save(self,name):self.im.save(D/name);return D/name
# V5 exact horizontal alignment. This file never executes or changes V5 drawing source.
segments=[];p=(11.,44.);h=-25.;s=0.;keys=[{'id':'P0','s':0.,'x':11.,'y':44.}]
for idx,(kind,val,turn) in enumerate([('line',20.,0),('arc',1.9875,-145.),('line',12.,0),('arc',1.9875,145.),('line',8.,0)]):
 length=val if kind=='line' else val*math.radians(abs(turn));c=None
 if kind=='arc':
  sign=1 if turn>0 else -1;t=math.radians(h);c=(p[0]-sign*val*math.sin(t),p[1]+sign*val*math.cos(t))
 seg={'kind':kind,'s0':s,'s1':s+length,'p':p,'heading':h,'turn':turn,'radius':val if c else None,'center':c,'name':['直线 S1','弯道 C1','直线 S2','弯道 C2','直线 S3'][idx]};segments.append(seg)
 if c:
  t=math.radians(h+turn);p=(c[0]+sign*val*math.sin(t),c[1]-sign*val*math.cos(t))
 else:p=(p[0]+length*math.cos(math.radians(h)),p[1]+length*math.sin(math.radians(h)))
 h+=turn;s+=length;keys.append({'id':f'P{idx+1}','s':s,'x':p[0],'y':p[1]})
L=s
# Gradients are linear between breakpoints. Their integrals form a smooth continuous profile.
breaks=[0,4,18,20,keys[2]['s'],keys[2]['s']+2,keys[3]['s']-2,keys[3]['s'],keys[4]['s'],keys[4]['s']+2,L-2,L]
raw=[0,.09,.09,.04,.04,.09,.09,.04,.04,.09,.09,0]
raw_drop=sum((b-a)*(g+j)/2 for a,b,g,j in zip(breaks,breaks[1:],raw,raw[1:]))
TOTAL_DROP=4.0
factor=TOTAL_DROP/raw_drop;grades=[-g*factor for g in raw]
zbreak=[0.]
for a,b,g,j in zip(breaks,breaks[1:],grades,grades[1:]):zbreak.append(zbreak[-1]+(b-a)*(g+j)/2)
def height(st):
 for i in range(len(breaks)-1):
  if st<=breaks[i+1]+1e-8:
   t=st-breaks[i];ds=breaks[i+1]-breaks[i];rate=(grades[i+1]-grades[i])/ds
   return zbreak[i]+grades[i]*t+.5*rate*t*t,grades[i]+rate*t
 return zbreak[-1],grades[-1]
def at(st):
 seg=next((x for x in segments if st<=x['s1']+1e-8),segments[-1]);t=st-seg['s0'];h=seg['heading']
 if seg['kind']=='line':x=seg['p'][0]+t*math.cos(math.radians(h));y=seg['p'][1]+t*math.sin(math.radians(h))
 else:
  sign=1 if seg['turn']>0 else -1;h+=sign*math.degrees(t/seg['radius']);c=seg['center'];x=c[0]+sign*seg['radius']*math.sin(math.radians(h));y=c[1]-sign*seg['radius']*math.cos(math.radians(h))
 z,g=height(st);return {'s':st,'x':x,'y':y,'z':z,'heading':h,'grade':g}
def offset(r,k):
 t=math.radians(r['heading']);return(r['x']-k*math.sin(t),r['y']+k*math.cos(t))
sections=[{'id':'A-A','label':'普通直线路段','s':12.,'berm_side':-1}, {'id':'B-B','label':'C1 弯道出口侧','s':segments[1]['s0']+.75*(segments[1]['s1']-segments[1]['s0']),'berm_side':1}, {'id':'C-C','label':'C2 弯道中部','s':(segments[3]['s0']+segments[3]['s1'])/2,'berm_side':-1}]
for sec in sections:sec.update(at(sec['s']))
# PAGE 1: cross-section location plan.
sh=Sheet('切面定位图','沿 P0 → P5 行驶；A-A、B-B、C-C 均垂直于各自位置的道路中心线。',1)
def P(q):return(180+31*q[0],1720-31*q[1])
rows=[at(L*i/1100) for i in range(1101)];half=2.775/2
# Clip branch edges where they emerge from the main road.
def clip(k):
 out=[]
 for a,b in zip(rows,rows[1:]):
  a=offset(a,k);b=offset(b,k)
  if a[1]>42>=b[1]:
   t=(42-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),42))
  if b[1]<=42:out.append(b)
 return out
bd=[(0,42)]+clip(-half)+clip(half)[::-1]+[(44,42),(44,46),(0,46)]
sh.poly([P(q) for q in bd],'#eaf0f5');sh.line([P(q) for q in bd+[bd[0]]],INK,3)
sh.line([P((r['x'],r['y'])) for r in rows],BLUE,2,True)
for k in keys:
 q=P((k['x'],k['y']));sh.dot(q);dx,dy=(-65,15) if k['id']=='P2' else (-15,-42);sh.text(q[0]+dx,q[1]+dy,k['id'],25,bg=True)
for sec in sections:
 a=P(offset(sec,half+.8));b=P(offset(sec,-half-.8));sh.line([a,b],RED,4)
 sh.text(a[0]-25,a[1]-38,sec['id'].split('-')[0],27,RED,bg=True)
 sh.text(b[0]+8,b[1]+5,sec['id'].split('-')[0],27,RED,bg=True)
sh.text(370,258,'大路宽 4.000 m',29);sh.text(1110,540,'小路宽 2.775 m',28,BLUE)
sh.panel('切面位置与方向')
for i,sec in enumerate(sections):
 y=360+i*250;sh.text(1860,y,sec['id']+'  '+sec['label'],27,RED)
 sh.text(1860,y+54,f'里程 K0+{sec["s"]:06.3f}',24)
 sh.text(1860,y+98,f'中心高程 {sec["z"]:+.3f} m',24)
 side='左侧土坡 / 右侧边坎' if sec['berm_side']==-1 else '左侧边坎 / 右侧土坡'
 sh.text(1860,y+145,side,23,MUT)
sh.text(1860,1140,'左右按行驶方向定义。',23,MUT);sh.text(1860,1190,'横断面左侧对应行驶左侧。',22,MUT)
sh.text(1860,1270,'高程基准：P0 = 0.000 m',23,BLUE)
sh.rect((175,1240,1700,1400),'#f6f8fa');sh.text(205,1270,'平面参数沿用已确认版本',29)
sh.text(205,1330,'C1 / C2 内夹角 35°；内侧圆角 R0.60 m；本次只增加切面与建议高程。',25,MUT)
files=[sh.save('01_切面定位图.png')]
# PAGE 2: longitudinal profile.
sh=Sheet('道路纵断面图','沿小路中心线展开 · P0 为相对高程零点 · 起点接大路，末端下坡 4.00 m（建议）',2)
X=lambda st:180+30*st;Y=lambda z:430-120*z
for st in range(0,51,5):sh.line([(X(st),300),(X(st),1030)],GRID);sh.text(X(st),1046,str(st),22,MUT,'ma')
for z in [0,-1,-2,-3,-4]:sh.line([(180,Y(z)),(1700,Y(z))],GRID);sh.text(100,Y(z)-15,f'{z:.0f}',24,MUT)
sh.text(95,258,'高程 / m',23,MUT);sh.text(1540,1080,'累计里程 / m',24,MUT)
for seg in segments:
 col='#f4dfae' if seg['kind']=='arc' else '#dcebf5';sh.rect((X(seg['s0']),275,X(seg['s1']),319),col)
 sh.text((X(seg['s0'])+X(seg['s1']))/2,280,seg['name'],23,INK,'ma')
pts=[(X(L*i/800),Y(height(L*i/800)[0])) for i in range(801)]
sh.line(pts,BLUE,5)
for i,k in enumerate(keys):
 z,g=height(k['s']);q=(X(k['s']),Y(z));sh.dot(q,6,BLUE);sh.text(q[0]-17,q[1]-46,k['id'],25,BLUE,bg=True)
for sec in sections:
 q=(X(sec['s']),Y(sec['z']));sh.line([q,(q[0],1030)],RED,2,True);sh.dot(q,6,RED);sh.text(q[0],1098,sec['id'],24,RED,'ma',True)
sh.arrow((1750,Y(0)),(1750,Y(-4)),RED,True);sh.text(1605,630,'总高差',24,RED,bg=True);sh.text(1610,673,'4.00 m',26,RED,bg=True)
sh.panel('建议纵坡方案')
notes=[('起点 P0', '+0.000 m'),('终点 P5', '-4.000 m'),('中心线长度', f'{L:.3f} m'),('平均下坡',f'{4/L*100:.2f}%'),('直段最大下坡', f'{.09*factor*100:.2f}%'),('弯道段下坡', f'{.04*factor*100:.2f}%')]
for i,(a,b) in enumerate(notes):sh.text(1860,355+i*112,a,23,MUT);sh.text(1860,394+i*112,b,31,BLUE)
sh.text(1860,1060,'起点、末端坡度渐变至 0%。',22,MUT)
sh.text(1860,1110,'各段之间平顺变坡。',23,MUT)
sh.text(1860,1175,'竖向放大 4 倍；',24,RED)
sh.text(1860,1215,'图上斜角不是实际坡角。',23,RED)
sh.text(1860,1305,'高差、纵坡均待确认。',24,RED)
sh.rect((130,1190,1740,1430),'#f6f8fa');sh.text(155,1210,'控制点高程表',27)
sh.text(155,1270,'控制点',23,MUT);sh.text(155,1320,'里程 m',23,MUT);sh.text(155,1370,'高程 m',23,MUT)
for i,k in enumerate(keys):
 x=390+i*218;sh.text(x,1270,k['id'],24,INK,'ma');sh.text(x,1320,f'{k["s"]:.3f}',24,INK,'ma');sh.text(x,1370,f'{height(k["s"])[0]:+.3f}',24,BLUE,'ma')
files.append(sh.save('02_道路纵断面图.png'))
# PAGES 3-5: equal-scale transverse sections, mirrored according to the original zone colors.
for page,sec in enumerate(sections,3):
 sh=Sheet(f'{sec["id"]} 横断面 · {sec["label"]}',f'K0+{sec["s"]:06.3f} · 面向 P0 → P5 行进方向 · 横纵比例相同 · 中心高程 {sec["z"]:+.3f} m',page)
 side=sec['berm_side'];cross=.02
 local=lambda x:side*cross*x
 bermedge=(side*half,.02775);bermtop=(side*(half+2.25),1.52775);bermfar=(side*(half+3.25),1.52775)
 cutedge=(-side*half,-.02775);cutfoot=(-side*(half+1.5),-3.02775);cutfar=(-side*(half+2.5),-3.02775)
 roadleft=(-half,local(-half));roadright=(half,local(half))
 Q=lambda q:(900+140*q[0],650-140*q[1])
 for x in range(-5,6):sh.line([Q((x,2.1)),Q((x,-3.55))],GRID)
 for z in [2,1,0,-1,-2,-3]:sh.line([Q((-5,z)),Q((5,z))],GRID)
 surface=sorted([bermfar,bermtop,bermedge,cutedge,cutfoot,cutfar],key=lambda q:q[0]);soil=surface+[(surface[-1][0],-3.6),(surface[0][0],-3.6)]
 sh.poly([Q(q) for q in soil],'#f1ece0');sh.line([Q(q) for q in surface],INK,3)
 sh.line([Q(bermfar),Q(bermtop),Q(bermedge)],GREEN,7);sh.line([Q(cutedge),Q(cutfoot),Q(cutfar)],YELLOW,7)
 sh.line([Q(roadleft),Q(roadright)],BLUE,9)
 sh.line([Q((0,.4)),Q((0,-.6))],MUT,2,True);sh.dot(Q((0,0)),6,BLUE)
 # Width and crossfall, both measured on the road surface.
 for x in [-half,half]:sh.line([Q((x,local(x))),Q((x,.65))],BLUE,2)
 sh.arrow(Q((-half,.55)),Q((half,.55)),BLUE,True)
 sh.text(900,505,'路面净宽 2.775 m',29,BLUE,'ma',True)
 sh.arrow(Q((side*.8,-.32)),Q((-side*.8,-.32)),BLUE)
 sh.text(900,720,'横坡 2% · 坡向临坎侧',24,BLUE,'ma',True)
 sh.text(900,771,'两侧路缘高差 0.0555 m',22,MUT,'ma',True)
 # Height dimensions: each relative to its own road edge.
 bx=side*(half+3.35);cx=-side*(half+2.9)
 sh.arrow(Q((bx,.02775)),Q((bx,1.52775)),GREEN,True)
 sh.arrow(Q((cx,-.02775)),Q((cx,-3.02775)),YELLOW,True)
 sh.text(220 if side==-1 else 1450,360,'土坡高 1.50 m',28,GREEN,bg=True)
 sh.text(245 if side==-1 else 1440,404,'竖:横 = 1:1.5',24,GREEN,bg=True)
 sh.text(270 if side==-1 else 1460,446,'坡角约 33.7°',23,GREEN,bg=True)
 tx=1430 if side==-1 else 135
 sh.text(tx,830,'边坎落差 3.00 m',26,YELLOW,bg=True)
 sh.text(tx,877,'竖:横 = 1:0.5',23,YELLOW,bg=True)
 sh.text(tx,921,'坡角约 63.4°',23,YELLOW,bg=True)
 sh.text(180,1138,'行驶左侧',25,MUT);sh.text(1490,1138,'行驶右侧',25,MUT)
 sh.panel('横断面建议参数')
 notes=[f'中心高程：{sec["z"]:+.3f} m',f'左路缘：{sec["z"]+roadleft[1]:+.3f} m',f'右路缘：{sec["z"]+roadright[1]:+.3f} m',f'土坡顶：{sec["z"]+1.52775:+.3f} m',f'边坎脚：{sec["z"]-3.02775:+.3f} m']
 for i,t in enumerate(notes):sh.text(1860,360+i*69,t,24,BLUE)
 for i,t in enumerate(['土坡水平展开：2.25 m','边坎水平展开：1.50 m','图中路面不另加路肩。','高度相对各自路缘计量。','横坡建议向临坎侧排水。','本版不另设弯道超高。']):sh.text(1860,780+i*67,t,23,MUT)
 sh.text(1860,1240,'以上地形及横坡待确认。',23,RED)
 sh.rect((160,1220,1740,1420),'#f6f8fa')
 sh.text(190,1240,'这一刀表达什么',28)
 if side==-1:desc='左侧为绿色土坡，右侧为黄色无护栏边坎；路面从左向右降低。'
 else:desc='左侧为黄色无护栏边坎，右侧为绿色土坡；路面从右向左降低。'
 sh.text(190,1295,desc,25,MUT)
 sh.text(190,1350,'两侧地形高度按相邻路缘计算；未表达路面结构厚度。',24,MUT)
 files.append(sh.save(f'{page:02d}_{sec["id"]}_横断面.png'))
# Supporting data and drawings only. No Blender output and no changes to approved V5.
meta={'status':'proposed_unconfirmed','source_plan':'V5 approved curvature only','unit':'m','datum':'P0 relative elevation = 0','length_m':L,'total_drop_m':4,'profile_interpolation':'linear gradient, integrated analytically; continuous elevation and grade','profile_breakpoints':[{'station_m':a,'z_m':z,'grade_percent':g*100} for a,z,g in zip(breaks,zbreak,grades)],'key_points':[dict(k,z=height(k['s'])[0]) for k in keys],'sections':sections,'crossfall_percent':2,'berm_height_above_adjacent_edge_m':1.5,'berm_slope_V_to_H':[1,1.5],'drop_below_adjacent_edge_m':3,'drop_slope_V_to_H':[1,.5],'notes':['All elevation, longitudinal grade, crossfall and terrain heights are suggestions awaiting user confirmation.','Crossfall transitions between left and right drainage directions are not yet designed.','35-degree hairpin opening and 0.60 m inner radius from approved V5 retained; vehicle swept path remains unverified.']}
(D/'section_parameters.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
with (D/'profile_samples.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=['station_m','elevation_m','grade_percent']);writer.writeheader()
 for i in range(501):st=L*i/500;z,g=height(st);writer.writerow({'station_m':st,'elevation_m':z,'grade_percent':g*100})
(D/'说明.txt').write_text('道路断面建议图纸，共5页：切面定位图、完整纵断面、A-A直线段横断面、B-B C1弯道出口侧横断面、C-C C2弯道中部横断面。\n本套沿用V5已确认平面，坡度、高程及地形尺寸尚待确认。\n假定由P0向P5下坡4米，P0为相对零高程；纵断面竖向放大4倍。\n横断面以行驶方向区分左右，图中横纵同尺度。\n路面宽2.775米，单向横坡2%朝临坎侧；土坡高1.5米，坡比竖:横=1:1.5；边坎落差3米，坡比竖:横=1:0.5。\n相邻路段排水侧变化处的横坡转换尚未设计。本轮图纸不作为完整三维模型或车辆通行验证。\n')
# PDF pages embed the inspected high-resolution drawings without font substitutions.
pdf=D.parent/'pdf'/'道路纵横断面_建议版.pdf';c=canvas.Canvas(str(pdf),pagesize=landscape(A3));pw,ph=landscape(A3)
c.setTitle('道路纵横断面建议版 - V5平面配套');c.setAuthor('Codex')
for f in files:
 ih=pw*H/W;c.drawImage(str(f),0,(ph-ih)/2,width=pw,height=ih);c.showPage()
c.save()
assert len(PdfReader(str(pdf)).pages)==5
assert abs(height(L)[0]+4)<1e-10
assert all(b>a for a,b in zip(breaks,breaks[1:]))
assert all(abs(height(k['s'])[0]-height(k['s']+1e-7)[0])<1e-6 for k in keys[:-1])
# Compact overview for chat; originals retain full size.
thumb=Image.new('RGB',(1600,1067),'white')
for i,f in enumerate(files[1:]):
 a=Image.open(f);a.thumbnail((800,533));thumb.paste(a,((i%2)*800,(i//2)*533))
thumb.save(D/'断面图总览.png')
with zipfile.ZipFile(D/'道路纵横断面_完整图纸包.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files+[D/'section_parameters.json',D/'profile_samples.csv',D/'说明.txt',pdf]:z.write(f,f.name)
print(json.dumps({'pdf':str(pdf),'length_m':L,'end_z':height(L)[0],'max_grade_percent':min(grades)*100,'bend_grade_percent':-.04*factor*100,'sections':sections},ensure_ascii=False))
