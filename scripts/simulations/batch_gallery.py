"""Record bounded continuous gallery episodes, with explicit scripted provenance.

No learned model is called. Feedback labels are deterministic summaries of
privileged simulator measurements, never model predictions or paper results.
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from interactive_harness import Session, Metrics


def run(spec, root):
    out = root / 'runs' / spec['id']
    if (out / 'manifest.json').exists():
        raise FileExistsError(f'Refusing to overwrite {out}')
    args = SimpleNamespace(backend=spec['backend'], task=spec['task'], output=str(out),
                           seed=spec['seed'], layout=spec.get('layout',1), style=spec.get('style',1), horizon=2600)
    try:
        session = Session(args)
    except Exception as exc:
        out.mkdir(parents=True, exist_ok=True)
        (out/'status.json').write_text(json.dumps({
            'state':'initialization_failed', 'error':str(exc),
            'step':0, 'commands_completed':0}, indent=2))
        metrics=Metrics(out)
        metrics.add({'status/running':0,'status/failed':1},0)
        metrics.writer.close()
        raise
    session.manifest.update(brain='none; scripted feedback controller',
        output_schema=[], record_origin='deterministic simulator feedback, not LLM inference',
        gallery_spec=spec, executor_version='gallery-script-v1',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'manifest.json').write_text(json.dumps(session.manifest, indent=2))

    def act(command, note):
        idx=len(session.events)
        command={**command, 'brain':None, 'controller_note':note}
        (session.commands/f'{idx:03d}.json').write_text(json.dumps(command,indent=2))
        session.status('executing',command_index=idx)
        start=session.step
        before=session.snapshot(f'{idx:03d}-before')
        feedback=session.execute(command)
        after=session.snapshot(f'{idx:03d}-after')
        event=dict(index=idx,step_start=start,step_end=session.step,brain=None,
            controller_note=note,command=command,feedback=feedback,
            official_success=session.success(),
            private_controller_diagnostics={'before':before,'after':after})
        session.events.append(event)
        (out/'events.json').write_text(json.dumps(session.events,indent=2))
        session.metrics.add({'execution/completed_commands':idx+1,
                             'execution/official_success':event['official_success']},session.step)
        return feedback

    try:
        act({'action':'wait','steps':10},'Observe the initial scene; no learned model is used.')
        for i, pair in enumerate(spec['pairs']):
            if session.step>1400 or session.success():break
            obj,target=pair
            offset=[.045,0,.025] if 'bowl' in obj else [0,0,.005]
            feedback=act({'action':'pick','object':obj,'offset':offset,
                          'yaw_degrees':90 if 'cheese' in obj else 0,'lift':.18},
                         f'Attempt to grasp {obj}; object position comes from simulator state.')
            if not feedback['object_follows_gripper']:
                offset=[0,.045,.025] if 'bowl' in obj else [0,0,.015]
                feedback=act({'action':'pick','object':obj,'offset':offset,
                              'yaw_degrees':90,'lift':.18},
                             f'Previous lift was {feedback["object_lift_m"]:.3f} m; change grasp offset and orientation.')
            if feedback['object_follows_gripper']:
                act({'action':'place','object':obj,'target':target,'offset':[0,0,.045]},
                    f'Measured lift passed 0.05 m; attempt placement at {target}. This does not certify task success.')
            else:
                act({'action':'gripper','close':-1,'steps':12},
                    'Lift check failed again; release and continue without claiming successful placement.')
        act({'action':'wait','steps':30},'Let contacts settle before the official task predicate is evaluated.')
        act({'action':'finish'},'End this bounded episode; retain the official success or failure.')
        result=dict(success=session.success(),steps=session.step,commands=len(session.events),
                    brain_records=0,termination='script_budget',identity='scripted demonstration')
        (out/'result.json').write_text(json.dumps(result,indent=2))
        session.metrics.add({'status/running':0,'status/complete':1,
            'evaluation/completed_episodes':1,'evaluation/progress':1,
            'evaluation/success':result['success']},session.step)
        session.status('complete',**result)
    except Exception as exc:
        session.status('failed',error=str(exc))
        session.metrics.add({'status/running':0,'status/failed':1},session.step)
        raise
    finally:
        session.writer.close()
        (out/'actions.json').write_text(json.dumps(session.trace))
        session.env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('case');p.add_argument('--root',default='.')
    a=p.parse_args();spec=next(s for s in json.loads(Path(a.manifest).read_text()) if s['id']==a.case)
    run(spec,Path(a.root).resolve())
