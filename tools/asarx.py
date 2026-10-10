import sys,struct,json,os
a,out,pat=sys.argv[1:4]
f=open(a,'rb')
f.read(4);_,_,_,hl=struct.unpack('<IIII',f.read(16)) if False else (0,0,0,0)
f.seek(0);hdr=f.read(16);_,hsz,_,jlen=struct.unpack('<IIII',hdr)
h=json.loads(f.read(jlen));base=8+hsz
def walk(n,p):
    for k,v in n.get('files',{}).items():
        q=p+'/'+k
        if 'files' in v: yield from walk(v,q)
        else: yield q,v
import re
lst=[(p,v) for p,v in walk(h,'')]
if pat=='LIST':
    for p,v in lst: print(v['size'],p)
else:
    for p,v in lst:
        if re.search(pat,p) and 'offset' in v:
            f.seek(base+int(v['offset']));d=f.read(v['size'])
            o=os.path.join(out,p.lstrip('/'));os.makedirs(os.path.dirname(o),exist_ok=True);open(o,'wb').write(d)
            print('x',p)
