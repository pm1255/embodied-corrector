"""Atomically submit one externally generated four-field command to a local run."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--command', type=Path, required=True)
args = parser.parse_args()
status = json.loads((args.run / 'status.json').read_text())
if status['state'] != 'waiting_for_gpt':
    raise SystemExit('Run is not waiting for a command: ' + status['state'])
command = json.loads(args.command.read_text())
brain = command.get('brain')
if brain is not None:
    if list(brain) != ['Judge', 'Cause', 'Sub', 'Fine']:
        raise SystemExit('Expected ordered Judge, Cause, Sub, Fine fields')
    if brain['Judge'] not in ['success', 'failure']:
        raise SystemExit('Judge must be success or failure')
    if not all(isinstance(v, str) and v.strip() for v in brain.values()):
        raise SystemExit('Four fields must be nonempty strings')
index = status['commands_completed']
destination = args.run / 'commands' / f'{index:03d}.json'
if destination.exists():
    raise SystemExit('Command already exists; refusing to overwrite')
temporary = destination.with_suffix('.tmp')
temporary.write_text(json.dumps(command, ensure_ascii=False, indent=2))
temporary.replace(destination)
print(destination)
