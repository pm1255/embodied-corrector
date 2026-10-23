import argparse, json
from pathlib import Path
from .schema import load_examples, FIELDS
from .reward import score_response
from .model import ModelIO
from .monitor import Monitor


def evaluate(io, rows, output, max_new_tokens=160, monitor=None):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    if monitor:
        monitor.status("evaluation", "running")
    results = []
    for i, e in enumerate(rows):
        _, text = io.generate(io.encode(e), max_new_tokens, sample=False)
        scored = score_response(text, e.target, e.rubric)
        results.append(
            dict(
                id=e.id,
                source_trajectory=e.source_trajectory,
                domain=e.domain,
                prediction=text,
                **scored,
            )
        )
        if monitor:
            monitor.scalars(
                {
                    "evaluation/progress": (i + 1) / len(rows),
                    "evaluation/examples_complete": i + 1,
                },
                i + 1,
            )
        (root / "predictions.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results)
        )

    def aggregate(rs):
        n = len(rs)
        return {
            "n": n,
            **{k: sum(r["fields"][k] for r in rs) / n for k in FIELDS},
            "joint": sum(r["joint"] for r in rs) / n,
            "format_valid": sum(r["format_valid"] for r in rs) / n,
        }

    summary = {
        "overall": aggregate(results),
        "domains": {
            d: aggregate([r for r in results if r["domain"] == d])
            for d in sorted({r["domain"] for r in results})
        },
        "grader": "explicit_field_rubric_v1",
        "provenance": sorted({r.provenance for r in rows}),
        "official_paper_reproduction": False,
    }
    (root / "metrics.json").write_text(json.dumps(summary, indent=2))
    if monitor:
        monitor.scalars(
            {f"evaluation/{k}": v for k, v in summary["overall"].items() if k != "n"},
            len(rows),
        )
        monitor.status("evaluation", "complete")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--dtype", default="float32")
    p.add_argument("--max-new-tokens", type=int, default=160)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    rows = load_examples(a.data)
    rows = rows[: a.limit] if a.limit else rows
    m = Monitor(a.output, "evaluation")
    try:
        print(
            json.dumps(
                evaluate(
                    ModelIO(a.model, a.device, dtype=a.dtype),
                    rows,
                    a.output,
                    a.max_new_tokens,
                    m,
                )
            )
        )
    finally:
        m.close()


if __name__ == "__main__":
    main()
