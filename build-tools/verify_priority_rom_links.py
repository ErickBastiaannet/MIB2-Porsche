"""Offline member/signature audit against the recovered MU1417 ROM metadata.

Does not execute OEM initializers, emulate QNX or prove J9 VM startup. Platform
classes absent from this application ROM are reported explicitly, not guessed.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

def class_info(data):
    stream=io.BytesIO(data)
    def u2():return struct.unpack('>H',stream.read(2))[0]
    def u4():return struct.unpack('>I',stream.read(4))[0]
    assert u4()==0xCAFEBABE
    minor,major=u2(),u2();cp=[None]*u2();i=1
    while i<len(cp):
        tag=stream.read(1)[0]
        if tag==1:cp[i]=(tag,stream.read(u2()).decode('utf-8',errors='replace'))
        elif tag in (3,4):cp[i]=(tag,stream.read(4))
        elif tag in (5,6):cp[i]=(tag,stream.read(8));i+=1
        elif tag in (7,8):cp[i]=(tag,u2())
        elif tag in (9,10,11,12):cp[i]=(tag,u2(),u2())
        else:raise ValueError('Non-legacy constant pool tag '+str(tag))
        i+=1
    def utf(i):return cp[i][1]
    def cls(i):return utf(cp[i][1]) if i else None
    access,name,parent=u2(),cls(u2()),cls(u2())
    interfaces=[cls(u2()) for _ in range(u2())]
    def attrs():
        for _ in range(u2()):u2();stream.seek(u4(),1)
    def members():
        result={}
        for _ in range(u2()):
            flags,n,d=u2(),utf(u2()),utf(u2());result[(n,d)]=flags;attrs()
        return result
    fields,methods=members(),members()
    refs=[]
    for item in cp:
        if item and item[0] in (9,10,11):
            nt=cp[item[2]];refs.append((item[0],cls(item[1]),utf(nt[1]),utf(nt[2])))
    if major>48:raise ValueError('Class version above MU1417 J9: '+name)
    return {'name':name,'parent':parent,'interfaces':interfaces,'fields':fields,'methods':methods,
            'access':access,'major':major,'minor':minor,'refs':refs}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recovery-root',type=Path,required=True)
    p.add_argument('--jar',type=Path,default=Path('build/navigation-priority/PorscheNavigationPriority.test.jar'))
    p.add_argument('--output',type=Path,default=Path('build/navigation-priority/rom-link-audit.json'))
    a=p.parse_args();romfile=a.recovery_root/'rom.classes'
    sys.path[:0]=[str(a.recovery_root/'deps'),str(a.recovery_root/'jxe2jar/src')]
    from common import ReaderStream,StreamCursor
    from jxe import J9ROMMethod,J9ROMField
    rombytes=romfile.read_bytes();s=ReaderStream.bytes_to_stream(rombytes)
    for _ in range(3):s.read_u32()
    count=s.read_u32();s.read_relative();toc=s.read_relative();s.set(toc)
    pointers=dict((s.read_string_ref(),s.read_relative()) for _ in range(count))
    with zipfile.ZipFile(a.jar) as jar:
        classes={n[:-6]:class_info(jar.read(n)) for n in jar.namelist() if n.endswith('.class')}
    cache={};read_failures={}
    def get(name):
        if name in classes:return classes[name]
        if name in cache:return cache[name]
        cache[name]=None
        if name not in pointers:return None
        try:
            # Read signatures directly; no bytecode conversion or execution.
            with contextlib.redirect_stdout(io.StringIO()),StreamCursor(s,pointers[name]):
                s.read_u32();s.read_u32();actual=s.read_string_ref();parent=s.read_string_ref();access=s.read_u32()
                ni=s.read_u32();ip=s.read_relative()
                with StreamCursor(s,ip):interfaces=[s.read_string_ref() for _ in range(ni)]
                nm=s.read_u32();mp=s.read_relative()
                with StreamCursor(s,mp):methods=[J9ROMMethod.read(s) for _ in range(nm)]
                nf=s.read_u32();fp=s.read_relative()
                with StreamCursor(s,fp):fields=[J9ROMField.read(s) for _ in range(nf)]
            assert actual==name
            cache[name]={'name':name,'parent':parent,'interfaces':interfaces,'access':access,
                         'methods':{(m.name,m.signature):m.modifier for m in methods},
                         'fields':{(f.name,f.signature):f.access_flag for f in fields}}
        except Exception as e:read_failures[name]=type(e).__name__+': '+str(e)
        return cache[name]
    def resolve(owner,key,kind,seen):
        if owner in seen:return 'missing',None
        seen.add(owner);c=get(owner)
        if c is None:return 'unavailable',None
        if key in c[kind]:return 'found',(owner,c[kind][key])
        if key[0]=='<init>':return 'missing',None
        unknown=False
        for parent in [c['parent'],*c['interfaces']]:
            if not parent:continue
            state,found=resolve(parent,key,kind,seen)
            if state=='found':return state,found
            unknown|=state=='unavailable'
        return ('unavailable' if unknown else 'missing'),None
    checked=0;missing=[];unverified=[];access_errors=[]
    for caller,c in classes.items():
        for tag,owner,name,desc in c['refs']:
            state,target=resolve(owner,(name,desc),'fields' if tag==9 else 'methods',set())
            item={'caller':caller,'owner':owner,'member':name,'descriptor':desc}
            if state=='found':
                checked+=1
                declared,flags=target
                if flags&2 and caller!=declared:access_errors.append(item)
            elif state=='missing':missing.append(item)
            else:unverified.append(item)
    report={'jar_sha256':hashlib.sha256(a.jar.read_bytes()).hexdigest(),
            'rom_sha256':hashlib.sha256(rombytes).hexdigest(),'candidate_classes':len(classes),
            'class_versions':sorted({c['major'] for c in classes.values()}),
            'resolved_member_references':checked,'missing_members':missing,
            'private_access_errors':access_errors,'unverified_references':unverified,
            'rom_read_failures':read_failures,'qnx_j9_execution_verified':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('ROM_LINK_AUDIT',json.dumps({k:report[k] for k in ['candidate_classes','class_versions','resolved_member_references']}),
          'missing='+str(len(missing)),'access_errors='+str(len(access_errors)),
          'unverified='+str(len(unverified)),'read_failures='+str(len(read_failures)))
    # An unavailable reference is not evidence of a missing API, but it still
    # prevents declaring this offline audit complete (including optional code).
    if missing or access_errors or unverified or read_failures:raise SystemExit(1)

if __name__=='__main__':main()
