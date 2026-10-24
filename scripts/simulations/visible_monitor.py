from pathlib import Path
import argparse,json,time
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--spec',default='visible_case_specs.json');args=parser.parse_args();root=Path(args.root);runs=root/'runs';specs=json.loads((root/args.spec).read_text());out=runs/'visible-overview';out.mkdir(exist_ok=True);w=EventFileWriter(str(out/'tensorboard'))
for step in range(10000):
 states=[]
 for s in specs:
  try:states.append(json.loads((runs/('visible-recovery-'+s['id'])/'status.json').read_text()))
  except (FileNotFoundError,json.JSONDecodeError):states.append(dict(state='waiting'))
 values={'collection/target':len(specs),'collection/waiting':sum(s['state']=='waiting' for s in states),'collection/running':sum(s['state'] in ['ready','executing','waiting_for_gpt'] for s in states),'collection/verified_success':sum(s.get('success',False) for s in states),'collection/failed':sum(s['state'] in ['failed','initialization_failed'] or s['state']=='complete' and not s.get('success') for s in states),'collection/progress':sum(s.get('success',False) for s in states)/len(specs),'collection/physics_steps':sum(s.get('step',0) for s in states)}
 w.add_event(Event(wall_time=time.time(),step=step,summary=Summary(value=[Summary.Value(tag=k,simple_value=float(v)) for k,v in values.items()])));w.flush();(out/'status.json').write_text(json.dumps(values,indent=2))
 if values['collection/verified_success']==len(specs):break
 time.sleep(15)
w.close()
