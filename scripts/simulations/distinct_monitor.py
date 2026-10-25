"""Read sealed/running records without interrupting simulation workers."""
import json
import time
from pathlib import Path
from interactive_harness import Metrics

root=Path(__file__).resolve().parent
specs=json.loads((root/'distinct_case_specs.json').read_text())
out=root/'runs/distinct-overview';out.mkdir(parents=True,exist_ok=True)
metrics=Metrics(out)
for step in range(100000):
    rows={};values={}
    for mode in ['baseline','recovery']:
        states=[]
        for spec in specs:
            paths=sorted((root/'runs').glob(f'distinct-{mode}-{spec["id"]}-attempt*/status.json'))
            state={'state':'waiting','step':0}
            if paths:
                try:state=json.loads(max(paths,key=lambda x:x.stat().st_mtime).read_text())
                except (FileNotFoundError,json.JSONDecodeError):pass
            states.append(state);rows[mode+'/'+spec['id']]=state
            values[mode+'/'+spec['id']+'/physics_steps']=state.get('step',0)
            values[mode+'/'+spec['id']+'/waiting']=state['state']=='waiting'
            values[mode+'/'+spec['id']+'/success']=bool(state.get('success',False))
        values.update({mode+'/target':len(specs),mode+'/waiting':sum(s['state']=='waiting' for s in states),
            mode+'/running':sum(s['state'] in ['ready','executing','waiting_for_gpt'] for s in states),
            mode+'/verified_success':sum(bool(s.get('success',False)) for s in states),
            mode+'/failed':sum(s['state'] in ['failed','initialization_failed'] or s['state']=='complete' and not s.get('success',False) for s in states),
            mode+'/progress':sum(bool(s.get('success',False)) for s in states)/len(specs),
            mode+'/physics_steps':sum(s.get('step',0) for s in states)})
    metrics.add(values,step)
    (out/'status.json').write_text(json.dumps({'metrics':values,'tasks':rows},indent=2))
    if values['recovery/verified_success']==len(specs):break
    time.sleep(15)
