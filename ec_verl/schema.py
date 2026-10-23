"""Public evidence and offline supervision have deliberately separate interfaces."""

from dataclasses import dataclass, field
from pathlib import Path
import json
import re

FIELDS = ("Judge", "Cause", "Sub", "Fine")
PUBLIC_FIELDS = ("task", "previous_subtask", "history", "observation", "images")


@dataclass
class Example:
    id: str
    source_trajectory: str
    domain: str
    task: str
    previous_subtask: str
    observation: str
    history: list = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    target: dict = field(default_factory=dict)
    rubric: dict = field(default_factory=dict)
    provenance: str = "user_supplied"

    def public(self):
        return {k: getattr(self, k) for k in PUBLIC_FIELDS}

    def validate(self, require_target=True):
        if not self.id or not self.source_trajectory:
            raise ValueError("id and source_trajectory are required")
        if self.domain not in {"navigation", "operation"}:
            raise ValueError(f"Invalid domain: {self.domain}")
        if not isinstance(self.history, list) or not isinstance(self.images, list):
            raise ValueError("history and images must be lists")
        if require_target:
            if set(self.target) != set(FIELDS):
                raise ValueError(f"{self.id}: expected exactly {FIELDS}")
            if self.target["Judge"] not in {"success", "failure"}:
                raise ValueError("Judge must be success or failure")
            if any(
                not isinstance(v, str) or not v.strip() for v in self.target.values()
            ):
                raise ValueError("Targets must be nonempty strings")
        return self


def load_examples(path, require_target=True):
    path = Path(path)
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        ex = Example(**obj).validate(require_target)
        ex.images = [
            str((path.parent / p).resolve()) if not Path(p).is_absolute() else p
            for p in ex.images
        ]
        missing = [p for p in ex.images if not Path(p).is_file()]
        if missing:
            raise FileNotFoundError(f"{ex.id}: missing observations {missing}")
        rows.append(ex)
    if not rows or len({r.id for r in rows}) != len(rows):
        raise ValueError("Empty dataset or duplicate example IDs")
    return rows


def check_split(train, evaluation):
    overlap = {e.source_trajectory for e in train} & {
        e.source_trajectory for e in evaluation
    }
    ids = {e.id for e in train} & {e.id for e in evaluation}
    if overlap or ids:
        raise ValueError(
            f"Train/evaluation leakage: source trajectories={sorted(overlap)}, ids={sorted(ids)}"
        )


def format_response(target, fields=FIELDS):
    return "\n".join(f"{k}: {target[k]}" for k in fields)


def parse_response(text):
    matches = list(re.finditer(r"(?m)^\s*(Judge|Cause|Sub|Fine):\s*", text))
    if [m.group(1) for m in matches] != list(FIELDS):
        return None
    parsed = {
        m.group(1): text[
            m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)
        ].strip()
        for i, m in enumerate(matches)
    }
    parsed["Judge"] = parsed["Judge"].lower()
    if parsed["Judge"] not in {"success", "failure"} or any(
        not v for v in parsed.values()
    ):
        return None
    return parsed


def normalize_deployed_response(text):
    """Accept equivalent four-field JSON at the service boundary only.

    Training retains its strict line-oriented token boundaries. Never invent a
    missing field or silently accept duplicate/extra JSON keys.
    """
    parsed = parse_response(text)
    if parsed is not None:
        return format_response(parsed), parsed

    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("Duplicate field")
            obj[key] = value
        return obj

    try:
        obj = json.loads(
            text.strip().removeprefix("```json").removesuffix("```").strip(),
            object_pairs_hook=unique_pairs,
        )
        if not isinstance(obj, dict) or set(obj) != set(FIELDS):
            return text, None
        if any(not isinstance(v, str) or not v.strip() for v in obj.values()):
            return text, None
        canonical = format_response(obj)
        parsed = parse_response(canonical)
        return (format_response(parsed), parsed) if parsed else (text, None)
    except (ValueError, TypeError):
        return text, None
