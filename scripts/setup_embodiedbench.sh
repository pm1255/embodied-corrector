#!/usr/bin/env bash
set -euo pipefail
: "${EC_EB_ROOT:?Set EC_EB_ROOT to a new directory for the official EmbodiedBench checkout}"
git clone https://github.com/EmbodiedBench/EmbodiedBench.git "$EC_EB_ROOT"
cd "$EC_EB_ROOT"
git checkout 9be4e980e9cd6bcb38373cd4aab7c32724bdd401
# The simulator has its own dependency environment, independent of verl/CUDA.
conda env create -f conda_envs/environment.yaml
conda run -n embench pip install -e .
git lfs install --local
git clone https://huggingface.co/datasets/EmbodiedBench/EB-ALFRED embodiedbench/envs/eb_alfred/data/json_2.1.0
git -C embodiedbench/envs/eb_alfred/data/json_2.1.0 checkout af55cc721725ed058830fd7a8aee66c1f69efbaa
git rev-parse HEAD > embodiedbench-source-commit.txt
printf '%s\n' 'Start the simulator display with: conda run -n embench python -m embodiedbench.envs.eb_alfred.scripts.startx 1'
