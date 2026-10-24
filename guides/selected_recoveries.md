# Selected recovery episodes

The homepage contains **6 LIBERO-PRO and 6 RoboCasa365 successful recovery episodes**, with continuous simulator motion and visible English **Judge → Cause → Sub → Fine** output. RoboCasa365 includes **three mobile-base navigation recoveries and three manipulation recoveries**. GitHub features three of these exact video files. Every selected episode has a recorded failure followed by correction and a positive final environment success check.

## What these demonstrations establish

These are **GPT-proxy workflow demonstrations with a simulator-state-assisted analytical controller**, not outputs from a trained RynnBrain or Embodied-Corrector checkpoint. Private simulator positions guide the analytical executor and may assist the proxy's next decision. They must not be presented as an observation-only model evaluation or compared directly with the manuscript's frozen-VLA results.

These are independent episodes across task and seed variations, **not 12 distinct tasks**. Selection was conditioned on successful recovery; this gallery is **not a benchmark success-rate estimate**. Initial failures may be intentionally induced, including an empty placement, a high grasp, insufficient drawer opening, or an incorrect navigation waypoint and heading. The navigation cases are fresh simulator episodes with action-based perturbations, not replays of a successful demonstration dataset.

The three seed-7 LIBERO records were retained from the earlier run; their Chinese decisions were translated to English for display without changing event order, timing or outcomes. The other records were written in English after preceding feedback. Decisions and feedback are retained as recorded, including intermediate mistaken assessments and subsequent corrections.

## Episode manifest

| # | Suite | Recovery challenge | Seed | Environment steps | Final check | Record |
| --- | --- | --- | ---: | ---: | --- | --- |
| 01 | LIBERO-PRO | Restore drawer access and correct the grasp | 7 | 1422 | Success | [JSON](../docs/assets/recovery/libero-articulation-r1.json) |
| 02 | LIBERO-PRO | Recover from blocked access and a missed placement | 11 | 3242 | Success | [JSON](../docs/assets/recovery/curated-libero-articulation-s11.json) |
| 03 | LIBERO-PRO | Correct placement on the wrong side | 7 | 746 | Success | [JSON](../docs/assets/recovery/libero-relational-r2.json) |
| 04 | LIBERO-PRO | Restore the intended spatial relation | 11 | 596 | Success | [JSON](../docs/assets/recovery/curated-libero-relational-s11.json) |
| 05 | LIBERO-PRO | Recover both objects into the basket | 7 | 1349 | Success | [JSON](../docs/assets/recovery/libero-multiobject-r2.json) |
| 06 | LIBERO-PRO | Restore an omitted pickup before packing | 11 | 1166 | Success | [JSON](../docs/assets/recovery/curated-libero-multiobject-s11.json) |
| 07 | RoboCasa365 | Correct the route and dock at the stove | 11 | 958 | Success | [JSON](../docs/assets/recovery/nav-rc-recovery-stove-s11.json) |
| 08 | RoboCasa365 | Recover the route to the fridge | 23 | 663 | Success | [JSON](../docs/assets/recovery/nav-rc-recovery-fridge-s23.json) |
| 09 | RoboCasa365 | Clear the arm and navigate to the toaster | 37 | 1435 | Success | [JSON](../docs/assets/recovery/nav-rc-recovery-toaster-s37.json) |
| 10 | RoboCasa365 | Recover a slipped garlic grasp and separate both objects | 11 | 2217 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s11.json) |
| 11 | RoboCasa365 | Regrasp the sweet potato and separate both objects | 23 | 1375 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s23.json) |
| 12 | RoboCasa365 | Restore the missing pickup before placement | 37 | 1076 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s37.json) |

## Navigation evidence

Navigation uses RoboCasa365's `NavigateKitchen` task and the real PandaOmron mobile-base actions. No robot position, object position, or simulator state is assigned after initialization. A third-person camera follows the actual base so the full robot remains visible; camera motion does not move the robot. The official task requires the base to be within 0.20 m of the target and the heading difference to have cosine at least 0.98 (about 0.20 rad).

| Target | Seed | Actual base path | Final position error | Final heading error | Official result |
| --- | ---: | ---: | ---: | ---: | --- |
| Stove | 11 | 2.070 m | 0.066 m | 0.075 rad | Success |
| Fridge | 23 | 2.477 m | 0.063 m | 0.079 rad | Success |
| Toaster | 37 | 2.187 m | 0.160 m | 0.077 rad | Success |

The initial incorrect waypoint/heading is explicitly marked as a controlled failure setup in each video. Subsequent diagnoses follow observed frames and execution feedback. The JSON records contain the target, post-perturbation state, measured base trajectory, final pose, official checks, and source hashes. The toaster episode also retains the unsuccessful first correction and the subsequent arm-clearance recovery.

## Recording and verification

- The simulator runs at 20 control steps per second and records at 10 frames per second. Every recorded frame is retained at its native 1× rate, with no reset or omitted action inside an episode.
- The only added footage is a three-second hold of the final scene and verified outcome. Robot motion comes from continuous simulation, not still-image animation.
- Every cover is extracted from the encoded video's actual first frame.
- Per-episode JSON records preserve task, seed, rates, continuous-episode flags, decision timestamps, feedback and final outcome. Raw-video and action-trace SHA-256 hashes bind the records to archived source material.
- Final success comes from the simulator's own success predicate. An intermediate `Judge: success` assesses the preceding substep and does not by itself establish full task completion.
- Failed attempts remain in the experiment archive and are not relabelled as successful. Zero-action camera preflight checks are setup checks, not navigation attempts. Three previously displayed cheese-bowl recoveries remain archived but are no longer in the active selection.

## Navigation runner

With the RoboCasa365 environment installed, launch a continuous navigation session:

```bash
MUJOCO_GL=egl python scripts/simulations/navigation_harness.py  \
  --backend robocasa365 --task NavigateKitchen --seed 23 --layout 1 --style 1  \
  --overview --horizon 10000 --output runs/navigation-example
```

The runner waits for sequential `commands/000.json`, `001.json`, … files. The public episode records retain the exact command objects. Observe each preceding outcome before supplying the next correction. `navigate` accepts a world-space `position`, `yaw`, `steps`, and position `tolerance`; ordinary arm actions from `interactive_harness.py` remain available. State localization is privileged and must be disclosed. Per-episode TensorBoard events are written automatically to the output directory.

[Open the 12-video gallery](https://pm1255.github.io/embodied-corrector/?v=navigation-6x6#simulations) · [Download selected records](../docs/assets/recovery/execution-records.zip) · [Media verification](../validation/selected-recoveries-20261024.json)
