# Successful-reference recovery videos

The project page contains **6 LIBERO-PRO and 6 RoboCasa365 recovery episodes**, including **three real mobile-base navigation episodes**. Every selected episode ends with a positive official environment success check. Original task instructions are used as video titles; titles, narration, subtitles, and **Judge → Cause → Sub → Fine** output are English.

## Scope and provenance

These are **GPT-proxy demonstrations with simulator-state-assisted analytical control**, separate from trained Embodied-Corrector / RynnBrain evaluation. The controller uses privileged simulator object poses. The proxy's decisions are written after observing the preceding execution feedback. Selection is conditioned on successful recovery: these 12 episodes cover task and seed variations and are **not 12 distinct tasks or a benchmark success-rate estimate**.

The source trajectories were **newly collected and verified in the simulator**, not downloaded human demonstrations. First, a deterministic controller completes the original task and saves its successful trajectory and reference waypoints. A fresh episode with the same seed introduces a controlled contact-height offset or an early navigation stop. After diagnosing the resulting failure, `source_reference` reads the saved successful waypoints and smoothly rejoins that path from the perturbed state. If contact has displaced an object, a subsequent observed-state correction updates its grasp and placement targets. The source waypoints are used directly; simulator states are never assigned or replayed after initialization. Some episodes include a successful approach prefix before the intervention.

Each public record includes the source baseline outcome, reference waypoints, source hashes, actual executed reference indices, English decisions, action timing, final outcome, and measured motion evidence. Failed collection and recovery attempts remain in the experiment archive and are not relabelled as successes.

## Recording and motion

The controller runs at **20 Hz** and records **every action frame at native 20 fps**, played at **1× speed**. Quintic paths provide gradual acceleration and braking; damped feedback and bounded action changes reduce abrupt corrections. Navigation keeps the arm stable relative to the mobile base. Motion comes from actual simulator actions, with no image-sequence animation, optical-flow interpolation, skipped actions, or reset after failure. A three-second final hold makes the result readable. Every cover is extracted from the encoded video's exact first frame.

The introductory film uses English narration and subtitles over continuous excerpts from these same recordings. Its 24 fps presentation repeats source frames where needed and does not synthesize robot motion. The gallery retains each full episode.

Kinematic summaries are descriptive measurements, not a guarantee of zero perceptible jitter. Small contact and controller corrections remain part of physical simulation. A substep's `reached` flag and the environment's final task predicate are distinct: contact-constrained targets may not meet the strict Cartesian tolerance even when the task succeeds.

## Selected episodes

| # | Suite | Original task | Seed | Steps | Final result |
| --- | --- | --- | ---: | ---: | --- |
| 01 | LIBERO-PRO | [Open the top layer of the drawer and put the cream cheese inside](../docs/assets/recovery/smooth-recovery-libero-articulation-s7.json) | 7 | 996 | Success |
| 02 | LIBERO-PRO | [Open the top layer of the drawer and put the cream cheese inside](../docs/assets/recovery/smooth-recovery-libero-articulation-s11.json) | 11 | 1000 | Success |
| 03 | LIBERO-PRO | [Pick the akita black bowl not between the plate and the ramekin and place it on the plate](../docs/assets/recovery/smooth-recovery-libero-relational-s7.json) | 7 | 811 | Success |
| 04 | LIBERO-PRO | [Pick the akita black bowl not between the plate and the ramekin and place it on the plate](../docs/assets/recovery/smooth-recovery-libero-relational-s11.json) | 11 | 820 | Success |
| 05 | LIBERO-PRO | [Put both the cream cheese box and the butter in the basket](../docs/assets/recovery/smooth-recovery-libero-multiobject-s7.json) | 7 | 1501 | Success |
| 06 | LIBERO-PRO | [Put both the cream cheese box and the butter in the basket](../docs/assets/recovery/smooth-recovery-libero-multiobject-s11.json) | 11 | 1507 | Success |
| 07 | RoboCasa365 | [Navigate to the stove.](../docs/assets/recovery/smooth-recovery-rc-navigation-s11.json) | 11 | 529 | Success |
| 08 | RoboCasa365 | [Place the tangerine and the garlic on separate cutting boards.](../docs/assets/recovery/smooth-recovery-rc-vegetables-s11.json) | 11 | 2469 | Success |
| 09 | RoboCasa365 | [Navigate to the fridge.](../docs/assets/recovery/smooth-recovery-rc-navigation-s23.json) | 23 | 487 | Success |
| 10 | RoboCasa365 | [Place the tangerine and the sweet potato on separate cutting boards.](../docs/assets/recovery/smooth-recovery-rc-vegetables-s23.json) | 23 | 1497 | Success |
| 11 | RoboCasa365 | [Navigate to the toaster.](../docs/assets/recovery/smooth-recovery-rc-navigation-s37.json) | 37 | 379 | Success |
| 12 | RoboCasa365 | [Place the garlic and the mushroom on separate cutting boards.](../docs/assets/recovery/smooth-recovery-rc-vegetables-s37.json) | 37 | 1400 | Success |

## Navigation evidence

Navigation uses RoboCasa365 `NavigateKitchen` and actual PandaOmron base actions. A third-person camera follows the base; camera motion does not move the robot. The official condition requires a target distance of at most 0.20 m and a heading-error cosine of at least 0.98. The controlled early stop leaves that condition false before recovery.

| Destination | Seed | Base path | Final position error | Final heading error |
| --- | ---: | ---: | ---: | ---: |
| Stove | 11 | 1.689 m | 0.010 m | 0.000 rad |
| Fridge | 23 | 2.206 m | 0.020 m | 0.000 rad |
| Toaster | 37 | 1.736 m | 0.003 m | 0.000 rad |

## Runner

Use the pinned simulator setup in [the simulation setup script](../scripts/simulations/setup.sh). `scripts/simulations/smooth_case_specs.json` contains all 12 deterministic collection plans. From the simulation working directory containing `tasks/`, run the matching environment's Python:

```bash
python smooth_harness.py --spec smooth_case_specs.json --case rc-navigation-s23 --mode baseline --output runs/source-fridge
python smooth_harness.py --spec smooth_case_specs.json --case rc-navigation-s23 --mode recovery --baseline runs/source-fridge --output runs/recovery-fridge
```

The recovery session waits for `commands/000.json`, `001.json`, and so on. Observe feedback before supplying the next decision; the public episode records preserve exact command objects. `source_reference` accepts optional `begin` and `end` waypoint indices. Stop using a `finish` command after checking the actual task outcome. Both modes automatically write TensorBoard events; `python smooth_monitor.py --root . --spec smooth_case_specs.json` aggregates baseline and recovery waiting/running/success states.

[Open the gallery](https://pm1255.github.io/embodied-corrector/?v=smooth-en-12#simulations) · [Download records](../docs/assets/recovery/execution-records.zip) · [Media verification](../validation/smooth-recoveries-20261025.json)
