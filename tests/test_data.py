import json
import pytest
from ec_verl.data import make_fixture
from ec_verl.schema import load_examples, check_split, parse_response, format_response
from ec_verl.prompts import messages
from ec_verl.reward import score_response


def test_fixture_and_source_split(tmp_path):
    make_fixture(tmp_path)
    tr = load_examples(tmp_path / "train.jsonl")
    ev = load_examples(tmp_path / "eval.jsonl")
    check_split(tr, ev)
    ev[0].source_trajectory = tr[0].source_trajectory
    with pytest.raises(ValueError):
        check_split(tr, ev)


def test_labels_never_in_deployment_prompt(tmp_path):
    make_fixture(tmp_path)
    e = load_examples(tmp_path / "train.jsonl")[0]
    original = messages(e)
    e.target = {k: "PRIVATE_SENTINEL" for k in e.target}
    e.rubric = {"secret": "PRIVATE_SENTINEL"}
    assert messages(e) == original and "PRIVATE_SENTINEL" not in json.dumps(messages(e))
    assert "PRIVATE_SENTINEL" in json.dumps(messages(e, "sft_plan"))


def test_parser_rejects_duplicate_fields():
    x = "Judge: failure\nCause: missed grasp\nSub: grasp\nFine: verify\nCause: invented"
    assert parse_response(x) is None


def test_scores_not_self_reported(tmp_path):
    make_fixture(tmp_path)
    e = load_examples(tmp_path / "train.jsonl")[0]
    assert score_response(format_response(e.target), e.target)["joint"] == 1
    assert score_response("I succeeded. Reward: 1.0", e.target)["reward"] == 0


def test_ordered_rubric():
    t = {
        "Judge": "failure",
        "Cause": "grasp missed",
        "Sub": "pick object",
        "Fine": "open grasp verify",
    }
    rule = {
        "Fine": {
            "required": [["open"], ["grasp"], ["verify"]],
            "ordered": ["open", "grasp", "verify"],
        }
    }
    assert score_response(format_response(t), t, rule)["fields"]["Fine"] == 1
    wrong = {**t, "Fine": "verify grasp open"}
    assert score_response(format_response(wrong), t, rule)["fields"]["Fine"] == 0


def test_deployment_json_normalization_preserves_fields():
    from ec_verl.schema import normalize_deployed_response

    target = {
        "Judge": "failure",
        "Cause": "Object is not visible.",
        "Sub": "Approach the counter.",
        "Fine": "Move closer and verify visibility.",
    }
    text, fields = normalize_deployed_response(json.dumps(target))
    assert fields == target and parse_response(text) == target


def test_deployment_json_rejects_ambiguous_or_incomplete_fields():
    from ec_verl.schema import normalize_deployed_response

    for text in [
        '{"Judge":"failure","Judge":"success"}',
        '{"Judge":"failure"}',
        '{"Judge":true,"Cause":"x","Sub":"y","Fine":"z"}',
    ]:
        assert normalize_deployed_response(text) == (text, None)
