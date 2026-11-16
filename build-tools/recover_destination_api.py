"""Recover the exact MU1417 guidance/destination API classes from an existing J9 ROM extraction.

Uses the previously prepared jxe2jar/deps in --recovery-root; downloads nothing.
Output is build input only, never a deployable replacement for OEM data classes.
"""
import argparse,contextlib,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'de/audi/atip/base/IFrameworkAccess':'cb27ed1bcfc808cd42c46464e936955e345c9a5dc1cd6bb35f8e25b05dbda393',
 'de/audi/tghu/navi/app/NavigationEnv':'8dc3b1dbd19f906bc40a91c2d5bdaab5ae59c858d541d91f43e445967432f0d5',
 'org/dsi/ifc/navigation/BapTurnToInfo':'5bd0bc8ce0543bdc433bd6a41c240b75837d4ef3ab57fcae5e9f96f836aab0f0',
 'de/audi/atip/interapp/combi/bap/navi/data/CombiBAPNaviDestination':'2623cd8b7703cd7f3c5c127d8275230057a804e42e1b8b965d3ff77c0d9c6e8b',
 'de/audi/atip/interapp/combi/bap/navi/data/CombiBAPDestinationInfo':'904cbe0bc273cfbd4e94e5831abc8b6f0c2649570a568dff22dca1138e2871dc',
}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--recovery-root',type=Path,required=True)
 p.add_argument('--output',type=Path,default=ROOT/'build/porsche-destination-api.jar')
 args=p.parse_args();source=args.recovery_root
 sys.path[:0]=[str(source/'deps'),str(source/'jxe2jar/src')]
 from jxe import J9ROMClass
 from common import ReaderStream
 from jxe2jar import create_class
 s=ReaderStream.bytes_to_stream((source/'rom.classes').read_bytes())
 for _ in range(3):s.read_u32()
 count=s.read_u32();s.read_relative();toc=s.read_relative();s.set(toc)
 entries=[(s.read_string_ref(),s.read_relative()) for _ in range(count)]
 args.output.parent.mkdir(parents=True,exist_ok=True);staged=args.output.with_suffix('.new.jar')
 try:
  with zipfile.ZipFile(staged,'w',zipfile.ZIP_DEFLATED) as jar,args.output.with_suffix('.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
   for name,ptr in entries:
    if name in EXPECTED:create_class(J9ROMClass.read_at(s,name,ptr,count),jar)
  with zipfile.ZipFile(staged) as jar:
   if set(jar.namelist())!={n+'.class' for n in EXPECTED}:raise ValueError('Missing exact destination classes')
   for name,expected in EXPECTED.items():
    if hashlib.sha256(jar.read(name+'.class')).hexdigest()!=expected:raise ValueError('Unsupported destination class: '+name)
  staged.replace(args.output)
 finally:
  if staged.exists():staged.unlink()
 print('PORSCHE_DESTINATION_API_VERIFIED',args.output)
if __name__=='__main__':main()
