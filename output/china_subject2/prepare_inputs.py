"""Archive user inputs and public visual references; never connects to Blender."""
from pathlib import Path
import concurrent.futures, hashlib, json, re, shutil, urllib.request

ROOT = Path(__file__).resolve().parent
for d in ('references/documents','references/images','assets','blender','previews','reports'):
    (ROOT/d).mkdir(parents=True, exist_ok=True)
names = ['C1_subject2_reference_dimensions.md','subject2_realworld_references.md']
items=[]
for name in names:
    src=Path('/Users/macmini/Downloads')/name
    dst=ROOT/'references/documents'/name
    shutil.copy2(src,dst)
    for label,url in re.findall(r'!\[([^\]]*)\]\((https://[^)]+)\)',dst.read_text()):
        items.append((len(items)+1,label,url,name))

def fetch(item):
    i,label,url,doc=item
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data=response.read()
        mime=response.headers.get('Content-Type')
    ext='.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data.startswith(b'\xff\xd8\xff') else None
    if not ext: raise ValueError('Not an image: '+url)
    rel=f'references/images/{i:02d}{ext}'
    (ROOT/rel).write_bytes(data)
    return dict(label=label,url=url,document=doc,path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),server_content_type=mime,actual_format=ext[1:],use='visual reference only; not a texture')

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    manifest=list(pool.map(fetch,items))
(ROOT/'references/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
source=ROOT.parent/'mountain_hairpin_road/blender_trial_v14_c63_reference/mercedes_amg_c63_reference.blend'
shutil.copy2(source,ROOT/'assets/mercedes_amg_c63_reference.blend')
print(json.dumps({'images':len(manifest),'bytes':sum(x['bytes'] for x in manifest),'vehicle_copied':source.is_file()},ensure_ascii=False))
