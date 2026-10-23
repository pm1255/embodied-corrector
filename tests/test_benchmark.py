import pytest
from ec_verl.embodiedbench import parse_action


def test_valid_action():
    assert parse_action('{"action_id": 2, "reason": "approach"}', 4) == 2


def test_invalid_action():
    for x in [
        '{"action_id": true}',
        '{"action_id": -1}',
        '{"action_id": 2.5}',
        '{"action_id": 99}',
        "Task succeeded",
    ]:
        with pytest.raises(ValueError):
            parse_action(x, 4)
