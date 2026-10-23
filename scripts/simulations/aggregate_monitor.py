from pathlib import Path
import json,time
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
import argparse
p=argparse.ArgumentParser();p.add_argument('--logdir',default='runs/simulations');args=p.parse_args()
root=Path(args.logdir);w=EventFileWriter(str(root/'overview/tensorboard'));step=0
while True:
 values={};states=[]
 for p in root.glob('*/status.json'):
  s=json.loads(p.read_text());m=p.parent/'manifest.json'
  if not m.exists():continue
  b=json.loads(m.read_text())['backend'];states.append((b,s))
 for backend in ['libero_pro','robocasa365']:
  ss=[s for b,s in states if b==backend];complete=[s for s in ss if s['state']=='complete']
  values.update({backend+'/evaluation/completed_episodes':len(complete),backend+'/evaluation/successful_episodes':sum(s.get('success',False) for s in complete),backend+'/execution/physics_steps':sum(s['step'] for s in ss),backend+'/status/waiting':not bool(ss),backend+'/status/active_episodes':sum(s['state'] in ['waiting_for_gpt','executing','ready'] for s in ss)})
 w.add_event(Event(wall_time=time.time(),step=step,summary=Summary(value=[Summary.Value(tag=k,simple_value=float(v)) for k,v in values.items()])));w.flush();step+=1;time.sleep(10)
