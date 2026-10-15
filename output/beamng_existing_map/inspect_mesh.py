import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from collections import Counter
from PIL import Image, ImageDraw

ROOT=Path(__file__).parent
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
def read_mesh(path):
    tree=ET.parse(path)
    mesh=tree.find('.//c:mesh',NS)
    arrays={s.get('id'):np.fromstring(s.find('c:float_array',NS).text,sep=' ').reshape(-1,int(s.find('c:technique_common/c:accessor',NS).get('stride'))) for s in mesh.findall('c:source',NS)}
    pos_id=mesh.find('c:vertices/c:input',NS).get('source')[1:]
    triangles=[]
    for tr in mesh.findall('c:triangles',NS):
        inputs=tr.findall('c:input',NS)
        stride=max(int(i.get('offset')) for i in inputs)+1
        off=int(next(i for i in inputs if i.get('semantic')=='VERTEX').get('offset'))
        ind=np.fromstring(tr.find('c:p',NS).text,sep=' ',dtype=int).reshape(-1,stride)[:,off].reshape(-1,3)
        triangles.append(ind)
    return tree,arrays[pos_id],np.concatenate(triangles)

if __name__=='__main__':
    _,v,f=read_mesh(ROOT/'package/art/hairpin_road/shapes/road.dae')
    u,inv=np.unique(np.round(v,5),axis=0,return_inverse=True)
    faces=inv[f]
    edges=Counter(tuple(sorted(e)) for t in faces for e in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])])
    border=[e for e,c in edges.items() if c==1]
    print(json.dumps({'positions':v.shape,'triangles':f.shape,'unique':u.shape,'edges':len(border),'firstVertices':v[:25].tolist()}))
    im=Image.new('RGB',(1100,1000),'white');d=ImageDraw.Draw(im)
    def p(v):return (60+v[0]*20,970-v[1]*18)
    for e in border:d.line([p(u[e[0]]),p(u[e[1]])],fill='black',width=2)
    for x in range(0,46,5):
        for y in range(15,50,5):d.text(p((x,y)),f'{x},{y}',fill='gray')
    im.save(ROOT/'mesh_boundary.png')
    np.savez(ROOT/'road_arrays.npz',v=v,f=f,boundary=u[np.unique(border)])
