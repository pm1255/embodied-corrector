# Selected recovery episodes

The homepage contains 12 selected, successful simulator episodes with continuous motion and visible English **Judge → Cause → Sub → Fine** output. GitHub features three of these exact video files. Every selected episode has an observed failure followed by correction and a positive final environment success check.

## What these demonstrations establish

These are **GPT-proxy workflow demonstrations with a simulator-state-assisted analytical controller**, not outputs from a trained RynnBrain or Embodied-Corrector checkpoint. Private simulator positions guide the analytical executor and may assist the proxy's next decision. They must not be presented as an observation-only model evaluation or compared directly with the manuscript's frozen-VLA results.

There are **9 LIBERO-PRO and 3 RoboCasa365 episodes**, including repeated task families with different seeds. They are independent episodes, **not 12 distinct tasks**. Selection was conditioned on successful recovery; the selected gallery is **not a benchmark success-rate estimate**. Some initial failures were intentionally induced (for example, an empty placement, a high grasp, or insufficient drawer opening).

The three seed-7 LIBERO records were retained from the earlier run; their Chinese decisions were translated to English for display without changing event order, timing or outcomes. The nine new records were written in English after preceding feedback. Decisions and feedback are retained as recorded, including intermediate mistaken assessments and subsequent corrections.

## Episode manifest

| # | Suite | Recovery challenge | Seed | Environment steps | Final check | Record |
| --- | --- | --- | ---: | ---: | --- | --- |
| 01 | LIBERO-PRO | Restore drawer access and correct the grasp | 7 | 1422 | Success | [JSON](../docs/assets/recovery/libero-articulation-r1.json) |
| 02 | LIBERO-PRO | Recover from blocked access and a missed placement | 11 | 3242 | Success | [JSON](../docs/assets/recovery/curated-libero-articulation-s11.json) |
| 03 | LIBERO-PRO | Correct placement on the wrong side | 7 | 746 | Success | [JSON](../docs/assets/recovery/libero-relational-r2.json) |
| 04 | LIBERO-PRO | Restore the intended spatial relation | 11 | 596 | Success | [JSON](../docs/assets/recovery/curated-libero-relational-s11.json) |
| 05 | LIBERO-PRO | Recover both objects into the basket | 7 | 1349 | Success | [JSON](../docs/assets/recovery/libero-multiobject-r2.json) |
| 06 | LIBERO-PRO | Restore an omitted pickup before packing | 11 | 1166 | Success | [JSON](../docs/assets/recovery/curated-libero-multiobject-s11.json) |
| 07 | LIBERO-PRO | Regrasp and place the cheese in the bowl | 11 | 657 | Success | [JSON](../docs/assets/recovery/curated-libero-cheesebowl-s11.json) |
| 08 | LIBERO-PRO | Correct the grasp after scene rearrangement | 23 | 522 | Success | [JSON](../docs/assets/recovery/curated-libero-cheesebowl-s23.json) |
| 09 | LIBERO-PRO | Recover a shifted object into the bowl | 37 | 536 | Success | [JSON](../docs/assets/recovery/curated-libero-cheesebowl-s37.json) |
| 10 | RoboCasa365 | Recover a slipped garlic grasp and separate both objects | 11 | 2217 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s11.json) |
| 11 | RoboCasa365 | Regrasp the sweet potato and separate both objects | 23 | 1375 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s23.json) |
| 12 | RoboCasa365 | Restore the missing pickup before placement | 37 | 1076 | Success | [JSON](../docs/assets/recovery/curated-rc-organizevegetables-s37.json) |

## Recording and verification

- The simulator runs at 20 control steps per second and records at 10 frames per second. The gallery keeps every recorded frame at its native 1× rate, with no reset or omitted action inside an episode.
- The only added footage is a three-second hold of the final scene and verified outcome. There is no image-sequence substitute for robot motion.
- Every cover is extracted from the encoded video's actual first frame.
- Per-episode JSON records preserve task, seed, control and recording rates, continuous-episode flags, decision timestamps, feedback and final outcome. Available raw-video and action-trace SHA-256 hashes bind the records to the archived source material.
- Final success comes from each simulator's own success predicate. A proxy's intermediate `Judge: success` evaluates the preceding substep and does not by itself establish full task completion.
- Failed historical and new attempts remain in the experiment archive. They are excluded from this presentation selection, not relabelled as successful. The new Colorful Salsa seed-11 attempt ended unsuccessfully and is not in this gallery.

[Open the 12-video gallery](https://pm1255.github.io/embodied-corrector/#simulations) · [Download all selected records](../docs/assets/recovery/execution-records.zip) · [Media verification](../validation/selected-recoveries-20261024.json)
