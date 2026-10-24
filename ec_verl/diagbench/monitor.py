"""Lightweight TensorBoard logging; no GPU/torch import for data or scoring."""
import json
import time
from pathlib import Path
from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
from tensorboard.summary.writer.event_file_writer import EventFileWriter

STAGES = ('data', 'model', 'collect', 'judge', 'aggregate')


class Monitor:
    def __init__(self, root, scope='diagbench'):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'status.json'
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            'scope': scope, 'stages': {s: 'waiting' for s in STAGES}}
        self.writer = EventFileWriter(str(self.root / 'tensorboard' / scope))
        self.status()

    def scalars(self, values, step):
        now = time.time()
        self.writer.add_event(Event(wall_time=now, step=int(step), summary=Summary(
            value=[Summary.Value(tag=k, simple_value=float(v)) for k, v in values.items()])))
        self.writer.flush()
        with (self.root / 'metrics.jsonl').open('a') as stream:
            stream.write(json.dumps({'step': step, 'time': now, **values}, allow_nan=False) + '\n')

    def status(self, stage=None, state=None):
        if stage is not None:
            if stage not in STAGES or state not in ('waiting', 'running', 'complete', 'failed'):
                raise ValueError('Unknown stage/state')
            self.state['stages'][stage] = state
        self.state['updated'] = time.time()
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, indent=2) + '\n')
        temporary.replace(self.path)
        self.scalars({f'status/{s}/{v}': self.state['stages'][s] == v
                      for s in STAGES for v in ('waiting', 'running', 'complete', 'failed')},
                     int(self.state['updated']))

    def close(self):
        self.writer.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--stage', choices=STAGES, required=True)
    p.add_argument('--state', choices=('waiting', 'running', 'complete', 'failed'), required=True)
    p.add_argument('--scope', default='smoke')
    a = p.parse_args()
    m = Monitor(a.output, a.scope)
    try:
        m.status(a.stage, a.state)
    finally:
        m.close()
