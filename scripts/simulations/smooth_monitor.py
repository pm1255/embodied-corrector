"""Read-only progress monitor for successful-source and recovery collection."""
from pathlib import Path
import argparse,json,time
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--spec',default='smooth_case_specs.json');a=p.parse_args();root=Path(a.root);runs=root/'runs'
spec_path=root/a.spec
if not spec_path.exists() and a.spec=='smooth_case_specs.json':spec_path=root/'smooth_manifest.json'
w=EventFileWriter(str(runs/'smooth-overview/tensorboard'))
for step in range(10000):
 specs=json.loads(spec_path.read_text());values={}
 for mode in ['baseline','recovery']:
  states=[]
  for item in specs:
   path=runs/('smooth-'+mode+'-'+item['id'])/'status.json'
   try:states.append(json.loads(path.read_text()))
   except (FileNotFoundError,json.JSONDecodeError):states.append({'state':'waiting'})
  values.update({mode+'/target':len(specs),mode+'/waiting':sum(s['state']=='waiting' for s in states),mode+'/running':sum(s['state'] in ['ready','executing','waiting_for_gpt'] for s in states),mode+'/verified_success':sum(s.get('success',False) for s in states),mode+'/failed':sum(s['state']=='failed' or s['state']=='complete' and not s.get('success') for s in states),mode+'/progress':sum(s.get('success',False) for s in states)/len(specs),mode+'/physics_steps':sum(s.get('step',0) for s in states)})
 w.add_event(Event(wall_time=time.time(),step=step,summary=Summary(value=[Summary.Value(tag=k,simple_value=float(v)) for k,v in values.items()])));w.flush()
 (runs/'smooth-overview/status.json').write_text(json.dumps(values,indent=2))
 if values['recovery/verified_success']==len(specs):break
 time.sleep(15)
w.close()
