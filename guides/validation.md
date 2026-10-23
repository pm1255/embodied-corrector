# Executed validation · 2026-10-24

The single-GPU training and real EB-ALFRED integration ran successfully as software. **The model did not solve the one evaluated simulator task**, and the teaching-example diagnostic joint score was 0/2. These records establish pipeline execution, not paper-level performance.

## Training

- Model: Qwen3-VL-2B-Instruct; one H100; BF16; LoRA rank 8, alpha 16.
- SFT: 12 Judge/Cause updates, then 12 Sub/Fine updates.
- NEPO: 2 updates, group size 2, maximum 192 generated tokens.
- Learning rate: 2e-4; κ=1, β=0.5, λ=1, PPO clip=0.2; engineering defaults.
- 154 sampled planning tokens received nonzero privileged guidance.
- Trainable parameter fingerprints changed; sum of absolute NEPO signal was 2.1188925.
- Saving and reloading the adapter produced identical outputs on both evaluation examples.
- Eighteen numerical, data and interface tests passed on the final code.

The four teaching examples are derived from manuscript figures. Two were used for training and two for evaluation, with disjoint source IDs. They are not the official diagnostic benchmark. The evaluation achieved 2/2 valid output formats and 0/2 joint four-field matches.

Records: [NEPO proof](../validation/nepo_proof.json), [training metrics](../validation/training_metrics.jsonl), [real-model alignment](../validation/model_checks.json).

## Real EB-ALFRED

- Official EmbodiedBench commit: `9be4e980e9cd6bcb38373cd4aab7c32724bdd401`.
- Official dataset commit: `af55cc721725ed058830fd7a8aee66c1f69efbaa`.
- Base subset, index 0; one unique task. The same task was rerun after a service-format fix; these runs are not independent tasks.
- Base Qwen planner and the trained NEPO adapter as corrector.
- 11 real environment action calls; 10 correction calls; 10 structurally valid four-field responses.
- Environment `done=true`; the adapter did not hit its external step limit.
- **Success: 0/1.** Action calls include environment-rejected actions. Correct format does not imply correct reasoning.

[Final environment metrics](../validation/eb_alfred_metrics.json) are taken directly from the environment's `task_success` predicate. No simulator mock or scripted recovery was substituted.

## Runtime and compatibility

Validated with Python 3.12; container PyTorch `2.8.0a0+5228986c39.nv25.5`; Transformers 5.5.3; PEFT 0.19.0; Ray 2.49.2; TensorDict 0.10.0; NumPy 1.26.4; TensorBoard 2.16.2. The fresh-install script selects release PyTorch 2.8.0, which differs from the container's pre-release build.

AI2-THOR 2.1.0 ran with Flask 2.0.3 and Werkzeug 2.0.3. The default NVIDIA EGL selection crashed Xvfb in the tested container; selecting Mesa for the renderer resolved it. Qwen inference remained on the CUDA GPU. See [environment settings](embodiedbench.md).

## Scope

Native distributed verl RayPPOTrainer/FSDP, full benchmark coverage, other simulator backends, optimizer-state resume and manuscript-table reproduction are not implemented or validated. Full official data and grader were not available with the supplied paper. The project page presents manuscript-reported results separately from the software checks here.
