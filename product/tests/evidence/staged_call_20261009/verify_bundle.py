"""Read-only, standard-library integrity/rendering verification; no model execution."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
REPO=R.parents[3]
H=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return (R/p).read_text(encoding='utf-8')
def render(common,stage,task,raw,outputs,body):
 prior='\n\n'.join('Stage '+k+' output:\n'+v for k,v in outputs.items()) if outputs else 'None'
 for k,v in {'STAGE_ID':stage,'TASK':task,'RAW_SOURCES':raw,'PRIOR_OUTPUTS':prior}.items():common=common.replace('{'+k+'}',v)
 return (common+'\n\n'+body).encode('utf-8')
def main():
 manifest=json.loads(read('BUNDLE_MANIFEST.json'))
 for path,digest in manifest['files'].items():
  p=REPO/path
  assert p.is_file() and H(p.read_bytes())==digest, f'integrity mismatch: {path}'
 state=json.loads(read('STATE.json')); task=read('TASK.txt'); common=read('templates/COMMON.txt');n=0
 for arm in ['X','Y']:
  prev={}
  for st in 'ABCDEF':
   rec=next(x for x in state['execution_records'] if x['arm']==arm and x['stage']==st)
   packet=render(common,st,task,read(f'{arm}/SOURCES.txt'),prev,read(f'templates/{st}.txt'))
   assert packet==(R/arm/st/'PROMPT.txt').read_bytes()
   assert H(packet)==rec['input_sha256']
   out=read(f'{arm}/{st}/OUTPUT.txt');assert H(out.encode())==rec['output_sha256'];prev[st]=out;n+=1
 guard=read('repair_v1/INTERPRETATION_GUARD.txt').rstrip('\n')
 repaired=common.replace('\n\nTask:\n','\n\n'+guard+'\n\nTask:\n');prev={'A':read('Y/A/OUTPUT.txt')}
 for st in 'BCDEF':
  rec=next(x for x in state['repair_v1']['execution_records'] if x['stage']==st)
  packet=render(repaired,st,task,read('Y/SOURCES.txt'),prev,read(f'templates/{st}.txt'))
  assert packet==(R/'repair_v1'/st/'PACKET.txt').read_bytes()
  assert H(packet)==rec['packet_sha256']
  out=read(f'repair_v1/{st}/OUTPUT.txt');assert H(out.encode())==rec['output_sha256'];prev[st]=out;n+=1
 print(f'PASS: {len(manifest["files"])} file hashes; {n} exact stage-packet reconstructions. Byte integrity only; no semantic PASS.')
if __name__=='__main__':main()
