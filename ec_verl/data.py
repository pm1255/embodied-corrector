"""JSONL inputs, source-level split, and verl parquet export."""

import argparse, json, random
from pathlib import Path
from dataclasses import asdict
from .schema import Example, load_examples, check_split, format_response
from .prompts import messages


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(e), ensure_ascii=False) + "\n" for e in rows)
    )


def make_fixture(root):
    """Construct software fixtures, never label them as the released benchmark."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    templates = [
        (
            "operation",
            "Place the {o} in the basket.",
            "Place the {o}.",
            "The gripper is empty. The {o} remains on the floor.",
            "failure",
            "The {o} was not grasped.",
            "Pick up the {o}.",
            "Locate the {o}; grasp it; verify attachment; lift; place in the basket.",
        ),
        (
            "operation",
            "Put the {o} on the plate.",
            "Grasp the {o}.",
            "The gripper closes above the {o}. The object remains in the sink.",
            "failure",
            "The grasp is too high.",
            "Lower the gripper to the {o}.",
            "Open the gripper; align with the {o}; descend; close; verify attachment.",
        ),
        (
            "navigation",
            "Go to the {o} and open it.",
            "Navigate to the {o}.",
            "The {o} is visible but outside arm reach.",
            "failure",
            "The robot stopped too far from the {o}.",
            "Approach the {o}.",
            "Choose a reachable stop; navigate closer; verify reachability; open the {o}.",
        ),
        (
            "operation",
            "Place the {o} in the cabinet.",
            "Open the cabinet.",
            "The cabinet door is open. The {o} is on the table.",
            "success",
            "none",
            "Pick up the {o}.",
            "Locate the {o}; grasp it; verify attachment; move it into the open cabinet.",
        ),
    ]
    allrows = []
    for split, objects in [
        ("train", ["bowl", "cup", "carton", "drawer"]),
        ("eval", ["mug", "bottle"]),
    ]:
        rows = []
        for j, o in enumerate(objects):
            for k, t in enumerate(templates):
                d, task, sub, obs, judge, cause, nxt, fine = t
                values = [s.format(o=o) for s in (task, sub, obs, cause, nxt, fine)]
                e = Example(
                    id=f"fixture-{split}-{j}-{k}",
                    source_trajectory=f"fixture-source-{split}-{j}-{k}",
                    domain=d,
                    task=values[0],
                    previous_subtask=values[1],
                    observation=values[2],
                    history=[{"action": values[1], "feedback": values[2]}],
                    target=dict(
                        Judge=judge, Cause=values[3], Sub=values[4], Fine=values[5]
                    ),
                    provenance="synthetic_software_fixture",
                )
                rows.append(e)
        write_rows(root / f"{split}.jsonl", rows)
        allrows.append(rows)
    check_split(*allrows)
    (root / "PROVENANCE.md").write_text(
        "Synthetic language-only software fixtures. Not EmbodiedDiag-Bench, not real robot data, and not a reproduction of paper accuracy. Train and evaluation source IDs are disjoint.\n"
    )
    return {
        "train": len(allrows[0]),
        "eval": len(allrows[1]),
        "provenance": "synthetic_software_fixture",
    }


def export_parquet(rows, output):
    import pandas as pd

    records = []
    for e in rows:
        records.append(
            dict(
                data_source="embodied_diag",
                prompt=messages(e),
                ability="physical_failure_correction",
                reward_model={
                    "style": "rule",
                    "ground_truth": json.dumps(
                        {"target": e.target, "rubric": e.rubric}
                    ),
                },
                extra_info={
                    "id": e.id,
                    "source_trajectory": e.source_trajectory,
                    "domain": e.domain,
                    "verified_prefix": format_response(e.target, ("Judge", "Cause")),
                    "provenance": e.provenance,
                },
                images=e.images,
            )
        )
    pd.DataFrame(records).to_parquet(output, index=False)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("fixture")
    q.add_argument("--output", required=True)
    q = sub.add_parser("validate")
    q.add_argument("--train", required=True)
    q.add_argument("--eval", required=True)
    q = sub.add_parser("parquet")
    q.add_argument("--input", required=True)
    q.add_argument("--output", required=True)
    q = sub.add_parser("split")
    q.add_argument("--input", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("--eval-fraction", type=float, default=0.1)
    q.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    if a.command == "fixture":
        print(json.dumps(make_fixture(a.output)))
    elif a.command == "validate":
        tr, ev = load_examples(a.train), load_examples(a.eval)
        check_split(tr, ev)
        print(json.dumps({"train": len(tr), "eval": len(ev), "source_overlap": 0}))
    elif a.command == "parquet":
        export_parquet(load_examples(a.input), a.output)
    else:
        rows = load_examples(a.input)
        sources = sorted({e.source_trajectory for e in rows})
        if not 0 < a.eval_fraction < 1 or len(sources) < 2:
            raise ValueError("Need >=2 sources and evaluation fraction in (0,1)")
        random.Random(a.seed).shuffle(sources)
        held = set(
            sources[
                : max(1, min(len(sources) - 1, round(len(sources) * a.eval_fraction)))
            ]
        )
        tr = [e for e in rows if e.source_trajectory not in held]
        ev = [e for e in rows if e.source_trajectory in held]
        check_split(tr, ev)
        write_rows(Path(a.output) / "train.jsonl", tr)
        write_rows(Path(a.output) / "eval.jsonl", ev)


if __name__ == "__main__":
    main()
