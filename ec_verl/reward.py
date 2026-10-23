"""Explicit, inspectable field rubric; not the manuscript's unavailable official grader."""

import re
from .schema import FIELDS, parse_response


def normalize(s):
    return " ".join(re.findall(r"[\w]+", s.lower()))


def score_response(text, target, rubric=None):
    parsed = parse_response(text)
    scores = {k: 0.0 for k in FIELDS}
    if parsed is None:
        return {"format_valid": 0.0, "fields": scores, "joint": 0.0, "reward": 0.0}
    rubric = rubric or {}
    scores["Judge"] = float(parsed["Judge"] == target["Judge"])
    for k in FIELDS[1:]:
        rule = rubric.get(k)
        answer = normalize(parsed[k])
        if not rule:
            scores[k] = float(answer == normalize(target[k]))
            continue
        groups = rule.get("required", [])
        hits = [any(normalize(term) in answer for term in group) for group in groups]
        forbidden = any(normalize(term) in answer for term in rule.get("forbidden", []))
        positions = [answer.find(normalize(term)) for term in rule.get("ordered", [])]
        ordered = all(p >= 0 for p in positions) and positions == sorted(positions)
        scores[k] = float(bool(groups) and all(hits) and not forbidden and ordered)
    joint = float(all(scores[k] == 1 for k in FIELDS))
    return {
        "format_valid": 1.0,
        "fields": scores,
        "joint": joint,
        "reward": sum(scores.values()) / 4,
    }


def compute_score(data_source, solution_str, ground_truth, extra_info=None):
    """verl custom_reward_function entry point; ground_truth is JSON."""
    import json

    obj = json.loads(ground_truth) if isinstance(ground_truth, str) else ground_truth
    return score_response(solution_str, obj["target"], obj.get("rubric"))["reward"]
