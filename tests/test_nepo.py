import numpy as np
import torch
import pytest
from ec_verl.nepo import NEPOConfig, gated_signal, nepo_advantage, policy_loss


def test_probability_gap_not_log_ratio():
    p = torch.tensor([[0.2, 0.8]])
    q = torch.tensor([[0.4, 0.4]])
    d, g, gap = gated_signal(
        p.log(),
        q.log(),
        torch.ones_like(p),
        torch.ones_like(p),
        NEPOConfig(kappa=1, beta=0.5),
    )
    torch.testing.assert_close(gap, torch.tensor([[0.2, -0.4]]))
    torch.testing.assert_close(d, torch.tensor([[0.2, -0.2]]))


def test_high_entropy_only_gates_negative():
    p = torch.tensor([[0.2, 0.8, 0.2, 0.8]], requires_grad=True)
    q = torch.tensor([[0.4, 0.4, 0.4, 0.4]], requires_grad=True)
    d, _, _ = gated_signal(
        p.log(),
        q.log(),
        torch.tensor([[0.0, 0.0, 10.0, 10.0]]),
        torch.ones_like(p),
        NEPOConfig(),
    )
    assert (
        d[0, 0] == d[0, 2] and abs(d[0, 3]) < abs(d[0, 1]) / 100 and not d.requires_grad
    )


def test_padding_and_assessment_zeroed():
    p = torch.tensor([[0.2, 0.3, 0.1]])
    mask = torch.tensor([[0.0, 1.0, 0.0]])
    d, _, _ = gated_signal(p.log(), (p + 0.1).log(), p, mask, NEPOConfig())
    assert d[0, 0] == 0 and d[0, 2] == 0 and d[0, 1] > 0


def test_identical_prefix_zero():
    p = torch.randn(2, 4).log_softmax(-1)
    d, _, _ = gated_signal(p, p, torch.ones_like(p), torch.ones_like(p), NEPOConfig())
    assert d.count_nonzero() == 0


def test_verl_gradient_direction():
    old = torch.tensor([[-1.0, -1.0]])
    new = old.clone().requires_grad_()
    adv = torch.tensor([[1.0, -1.0]])
    loss, _ = policy_loss(old, new, adv, torch.ones_like(old))
    loss.backward()
    assert new.grad[0, 0] < 0 and new.grad[0, 1] > 0


def test_grpo_group_normalization_and_nepo():
    old = torch.full((4, 3), -1.0)
    mask = torch.ones_like(old)
    rewards = torch.zeros_like(old)
    rewards[:, -1] = torch.tensor([0.0, 1.0, 2.0, 4.0])
    adv, metrics = nepo_advantage(
        rewards, mask, np.array(["a", "a", "b", "b"]), old, old, mask, mask
    )
    torch.testing.assert_close(adv[0], adv[2])
    torch.testing.assert_close(adv[1], adv[3])
    assert adv[0, 0] < 0 < adv[1, 0]


def test_singleton_rejected():
    x = torch.ones(1, 2)
    with pytest.raises(ValueError):
        nepo_advantage(x, x, np.array(["a"]), x, x, x, x)


def test_invalid_mask_rejected():
    x = torch.ones(2, 2)
    with pytest.raises(ValueError):
        nepo_advantage(x, torch.zeros_like(x), np.array(["a", "a"]), x, x, x, x)


def test_verl_registry_returns_tensor_pair():
    from verl.trainer.ppo.core_algos import get_adv_estimator_fn

    x = torch.ones(2, 3)
    advantages, returns = get_adv_estimator_fn("embodied_nepo")(
        x, x, np.array(["a", "a"]), -x, -x, x, x
    )
    assert isinstance(returns, torch.Tensor)
    torch.testing.assert_close(advantages, returns)
