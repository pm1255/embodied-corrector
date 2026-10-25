# Distinct successful recovery demonstrations

Twelve different tasks: six LIBERO-PRO and six RoboCasa365. These are authored, simulator-state-assisted demonstrations, not RynnBrain inference or benchmark results.

Each continuous episode starts without a premature Judge/Cause label. Observed errors are followed by English diagnosis and corrective actions. The original environment success predicate passes at the end. Failed attempts remain in the collection archive; only completed successful episodes are selected here.

Every physical action frame is retained at native 20 fps and 1× speed. There is no frame interpolation, stitching, or state restoration after failure. A three-second hold makes the final result readable. Covers are the first frames of the encoded videos.

| Suite | Original task | Observed error types | Final result |
| --- | --- | --- | --- |
| LIBERO-PRO | [Put the black bowl in the bottom drawer of the cabinet and close it](../docs/assets/recovery/distinct-recovery-01-drawer.json) | high grasp; partial drawer closure with hand withdrawal | Success |
| LIBERO-PRO | [Put the yellow and white mug in the microwave and close it](../docs/assets/recovery/distinct-recovery-02-microwave.json) | lateral grasp offset; incomplete door closure | Success |
| LIBERO-PRO | [Turn on the stove and put the moka pot on it](../docs/assets/recovery/distinct-recovery-03-stove.json) | missed switch contact; placement offset | Success |
| LIBERO-PRO | [Put both the cream cheese box and the butter in the basket](../docs/assets/recovery/distinct-recovery-04-basket.json) | lateral grasp offset; placement outside basket | Success |
| LIBERO-PRO | [Put the white mug on the left plate and put the yellow and white mug on the right plate](../docs/assets/recovery/distinct-recovery-05-mugs.json) | high grasp; placement on wrong plate | Success |
| LIBERO-PRO | [Pick up the book and place it in the back compartment of the caddy](../docs/assets/recovery/distinct-recovery-06-book.json) | lateral grasp offset; placement outside organizer | Success |
| RoboCasa365 | [Place the fruits in the fridge on the cutting board by the sink to make a fruit bowl. Leave the non-fruit items in the fridge.](../docs/assets/recovery/distinct-recovery-07-fruits.json) | wrong-direction navigation; missed fruit grasp | Success |
| RoboCasa365 | [Transport the chicken drumstick from the fridge to the microwave and turn on the microwave.](../docs/assets/recovery/distinct-recovery-08-thaw.json) | high grasp; incomplete microwave door closure | Success |
| RoboCasa365 | [Pick the mug from the cabinet, place it under the coffee machine dispenser, and press the start button.](../docs/assets/recovery/distinct-recovery-09-coffee.json) | wrong-direction navigation; missed start button | Success |
| RoboCasa365 | [Pick up the cup and bowl from the counter, place them in the dishwasher, and close the dishwasher door.](../docs/assets/recovery/distinct-recovery-10-dishwasher.json) | high grasp; premature door-closing withdrawal | Success |
| RoboCasa365 | [Pick the tangerine, cucumber from the counter and place them in the cabinet. Then close the cabinet.](../docs/assets/recovery/distinct-recovery-11-cleanup.json) | wrong-direction navigation; high grasp | Success |
| RoboCasa365 | [Move the pot and pan from the stove into the sink.](../docs/assets/recovery/distinct-recovery-12-cookware.json) | lateral handle-grasp offset; wrong-direction navigation | Success |

## Evidence and limits

The JSON records contain exact commands, decision timing, feedback, available successful-source hashes, frame counts and motion measurements. Additional grasp or door-closing adjustments are retained in the continuous footage. Selection on final success does not estimate a success rate.

Controllers use quintic paths, bounded action changes and physical contacts. Stiffer bounded Cartesian control is used for the dishwasher door and pot lift; masses, friction, collision geometry, gripper force and physical actuator limits are unchanged. Recorded scenes and torso posture, when reused, are restored only during episode initialization. The cookware episode starts from the original seeded scene and uses commands validated in successful calibration runs; it does not replay a saved source state. Brief startup settling and contact transients remain visible; no motion smoothing or frame removal is applied.

## Reproduction

Use `scripts/simulations/distinct_harness.py` with `distinct_case_specs.json`. Collect and verify a successful source, then use `--baseline` to reuse its initialization, or start from the original seeded scene with a calibrated command sequence as in TransportCookware. Submit numbered JSON commands, inspect feedback, and finish only after the original success predicate passes. `--trajectory-only` is limited to source collection. Commands and failed attempts are retained. TensorBoard logs distinguish waiting, running, completed and failed collection states.
