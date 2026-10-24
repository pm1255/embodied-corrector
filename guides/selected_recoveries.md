# Visible failure followed by diagnosis and recovery

The gallery contains **6 LIBERO-PRO and 6 RoboCasa365 episodes**. Every RoboCasa episode combines real mobile-base navigation with two object placements in one uninterrupted simulation. All selected episodes end with a positive official environment task predicate.

## Scope

These are **GPT-authored proxy demonstrations using privileged simulator-state-assisted analytical control**, not trained Embodied-Corrector / RynnBrain evaluation. Known RoboCasa instruction prefixes are replayed with preceding-feedback checks; later grasp corrections are authored from the current execution observations. No trained checkpoint is queried. The selected successful episodes cover task, seed, and perturbation variations; they are not 12 distinct tasks or a success-rate estimate.

RoboCasa uses `OrganizeVegetables` with an explicitly adapted mobile start. At initialization only, the base is moved 0.75 m away from the original prep pose. The native manipulation success predicate is unchanged. This is a navigation-and-manipulation demonstration variant, not the unmodified benchmark protocol or `NavigateKitchen` alone. The original instruction remains the title.

## Temporal order

1. Execute the initial action without Judge/Cause text.
2. Observe the actual missed contact or increased distance to the prep pose.
3. Present the recorded Judge, Cause, Sub, and Fine guidance.
4. Recover through actual simulator actions and verify the complete task.

All RoboCasa episodes intentionally move toward an incorrect waypoint before their first diagnosis. Three also close above a vegetable after returning to the prep counter. LIBERO retains real missed-handle or raised-grasp recordings from the previous collection, with larger action views and the premature opening diagnosis removed. The recordings are not motion synthesized from still images.

## Recording and control

Native 20 Hz control, every action frame recorded at 20 fps, and 1× playback. Quintic reference paths and bounded action changes provide gradual acceleration and braking. No frames are skipped or interpolated; no simulator state is restored or assigned after initialization. The only added frames are a three-second final result hold. Every poster is extracted from the encoded first frame.

RoboCasa has a fixed whole-robot camera and a simultaneous counter close-up. The navigation controller transforms the held arm pose into the base coordinate frame before switching references; this prevents the arm drifting toward an invalid world-coordinate target.

The successful-reference trajectories were collected in simulation. Their hashes, reference waypoints, executed indices, observed failures, task checks, and motion measurements are preserved in each public JSON. Failed controller and camera probes and command-wait timeouts remain archived. Successful task predicates before an archival timeout are distinguished from a properly completed collection; those timed-out runs are not presented as the selected completed runs.

## Episodes

| Suite | Original task | Seed / variant | First diagnosis | Final task |
| --- | --- | --- | ---: | --- |
| LIBERO-PRO | [Open the top layer of the drawer and put the cream cheese inside](../docs/assets/recovery/visible-recovery-libero-articulation-s7.json) | 7 / Missed handle contact | 7.70 s | Success |
| LIBERO-PRO | [Open the top layer of the drawer and put the cream cheese inside](../docs/assets/recovery/visible-recovery-libero-articulation-s11.json) | 11 / Missed handle contact | 7.65 s | Success |
| LIBERO-PRO | [Pick the akita black bowl not between the plate and the ramekin and place it on the plate](../docs/assets/recovery/visible-recovery-libero-relational-s7.json) | 7 / Raised grasp contact | 13.50 s | Success |
| LIBERO-PRO | [Pick the akita black bowl not between the plate and the ramekin and place it on the plate](../docs/assets/recovery/visible-recovery-libero-relational-s11.json) | 11 / Raised grasp contact | 13.60 s | Success |
| LIBERO-PRO | [Put both the cream cheese box and the butter in the basket](../docs/assets/recovery/visible-recovery-libero-multiobject-s7.json) | 7 / Raised grasp contact | 14.25 s | Success |
| LIBERO-PRO | [Put both the cream cheese box and the butter in the basket](../docs/assets/recovery/visible-recovery-libero-multiobject-s11.json) | 11 / Raised grasp contact | 14.55 s | Success |
| RoboCasa365 | [Place the garlic and the mushroom on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s37-away.json) | 37 / Wrong-way navigation | 5.00 s | Success |
| RoboCasa365 | [Place the garlic and the mushroom on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s37-side.json) | 37 / Wrong-way navigation + high grasp | 5.15 s | Success |
| RoboCasa365 | [Place the tangerine and the sweet potato on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s23-away.json) | 23 / Wrong-way navigation | 5.00 s | Success |
| RoboCasa365 | [Place the tangerine and the sweet potato on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s23-side.json) | 23 / Wrong-way navigation + high grasp | 5.15 s | Success |
| RoboCasa365 | [Place the tangerine and the garlic on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s11-away.json) | 11 / Wrong-way navigation | 5.00 s | Success |
| RoboCasa365 | [Place the tangerine and the garlic on separate cutting boards.](../docs/assets/recovery/visible-recovery-rc-mobile-s11-side.json) | 11 / Wrong-way navigation + high grasp | 5.15 s | Success |

## Navigation measurements

| Seed / variant | Initial distance | After wrong route | Corrected docking error | Base path |
| --- | ---: | ---: | ---: | ---: |
| 37 / away | 0.750 m | 1.120 m | 0.006 m | 1.530 m |
| 37 / side | 0.750 m | 0.956 m | 0.005 m | 1.380 m |
| 23 / away | 0.750 m | 1.120 m | 0.006 m | 1.530 m |
| 23 / side | 0.750 m | 0.956 m | 0.005 m | 1.380 m |
| 11 / away | 0.750 m | 1.121 m | 0.006 m | 1.654 m |
| 11 / side | 0.750 m | 0.956 m | 0.005 m | 1.512 m |

## Reproduction

Use the pinned simulator setup in [setup.sh](../scripts/simulations/setup.sh). The source manipulation trajectories use `smooth_harness.py` and `smooth_case_specs.json`. The mobile-start configuration is in `visible_case_specs.json`. After collecting the source for the corresponding seed:

```bash
python mobile_recovery_harness.py --spec visible_case_specs.json --case rc-mobile-s37-side --baseline runs/smooth-baseline-rc-vegetables-s37 --output runs/visible-recovery-rc-mobile-s37-side
```

The session accepts numbered JSON commands under `commands/`. The exact command objects are in each execution record. Read feedback before diagnosing a failure. End with `finish` only after checking the task predicate. Every run writes TensorBoard data, and the overview reader aggregates waiting, running, failed, verified-success and physics-step counts.

[Project gallery](https://pm1255.github.io/embodied-corrector/?v=visible-failure-12#simulations) · [Execution records](../docs/assets/recovery/execution-records.zip) · [Verification](../validation/visible-failures-20261025.json)
