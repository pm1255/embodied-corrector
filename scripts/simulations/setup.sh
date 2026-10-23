#!/usr/bin/env bash
set -euo pipefail
EC_SIM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$EC_SIM_ROOT"
python3 - <<'PY'
import json, subprocess
from pathlib import Path
root=Path.cwd()
for source in json.loads((root/'scripts/simulations/sources.json').read_text()):
    target=root/'vendor'/source['name']
    if not target.exists():
        subprocess.run(['git','clone','https://github.com/'+source['repository']+'.git',str(target)],check=True)
    actual=subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
    if actual!=source['commit']:
        dirty=subprocess.check_output(['git','-C',str(target),'status','--porcelain'],text=True)
        if dirty:raise SystemExit('Local vendor modifications; preserve them before changing revision: '+str(target))
        subprocess.run(['git','-C',str(target),'checkout','--detach',source['commit']],check=True)
PY
python3 -m venv .venv-libero
.venv-libero/bin/pip install 'numpy<2' scipy mujoco==3.2.3 robosuite==1.4.1 pillow opencv-python-headless pyyaml tqdm termcolor imageio imageio-ffmpeg h5py lxml gym easydict bddl future matplotlib tensorboard cloudpickle
.venv-libero/bin/pip install --no-deps -e vendor/LIBERO-PRO
python3 -m venv .venv-robocasa
.venv-robocasa/bin/pip install numpy==2.2.5 numba==0.61.2 scipy==1.15.3 mujoco==3.3.1 pillow opencv-python-headless pyyaml tqdm termcolor imageio imageio-ffmpeg h5py lxml gymnasium easydict pynput pygame hidapi tensorboard requests
.venv-robocasa/bin/pip install --no-deps -e vendor/robosuite -e vendor/robocasa
.venv-libero/bin/python scripts/simulations/prepare_tasks.py
printf '%s\n' 'Python environments prepared. Install RoboCasa assets following guides/simulation_report_zh.md before starting a RoboCasa episode.'
