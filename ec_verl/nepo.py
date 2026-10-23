"""Equations (1)–(2): sampled-token probability gap, asymmetric entropy gate."""

from dataclasses import dataclass
import torch
from verl.trainer.ppo.core_algos import (
    compute_grpo_outcome_advantage,
    compute_policy_loss_vanilla,
    register_adv_est,
)
from omegaconf import OmegaConf


@dataclass
class NEPOConfig:
    coefficient: float = 1.0
    kappa: float = 1.0
    beta: float = 0.5
    clip_ratio: float = 0.2
    normalize_grpo: bool = True


def gated_signal(student_logp, teacher_logp, entropy, planning_mask, config):
    if config.beta <= 0 or config.coefficient < 0:
        raise ValueError("beta must be positive and coefficient nonnegative")
    if not (
        student_logp.shape == teacher_logp.shape == entropy.shape == planning_mask.shape
    ):
        raise ValueError("NEPO tensors must align by sampled planning token")
    if (planning_mask < 0).any() or (planning_mask > 1).any():
        raise ValueError("Invalid planning mask")
    with torch.no_grad():
        gap = teacher_logp.float().exp() - student_logp.float().exp()
        gate = torch.sigmoid((config.kappa - entropy.float()) / config.beta)
        delta = (gap.clamp_min(0) + gate * gap.clamp_max(0)) * planning_mask
    return delta, gate, gap


def nepo_advantage(
    token_level_rewards,
    response_mask,
    index,
    old_log_probs,
    teacher_log_probs,
    old_entropy,
    planning_mask,
    nepo_config=None,
    **kwargs,
):
    cfg = nepo_config or NEPOConfig()
    if (planning_mask > response_mask).any():
        raise ValueError("Planning mask includes padding or invalid response positions")
    if any(sum(index == i) < 2 for i in set(index)):
        raise ValueError("GRPO requires at least two responses per prompt")
    group, _ = compute_grpo_outcome_advantage(
        token_level_rewards,
        response_mask,
        index,
        norm_adv_by_std_in_grpo=cfg.normalize_grpo,
    )
    delta, gate, gap = gated_signal(
        old_log_probs, teacher_log_probs, old_entropy, planning_mask, cfg
    )
    adv = (group + cfg.coefficient * delta).detach() * response_mask
    return adv, {
        "nepo/gap_abs_mean": float(
            (gap.abs() * planning_mask).sum() / planning_mask.sum().clamp_min(1)
        ),
        "nepo/negative_gate_mean": float(
            (gate * (gap < 0) * planning_mask).sum()
            / ((gap < 0) * planning_mask).sum().clamp_min(1)
        ),
        "nepo/planning_tokens": float(planning_mask.sum()),
        "nepo/delta_abs_mean": float(
            delta.abs().sum() / planning_mask.sum().clamp_min(1)
        ),
        "nepo/student_entropy": float(
            (old_entropy * planning_mask).sum() / planning_mask.sum().clamp_min(1)
        ),
    }


@register_adv_est("embodied_nepo")
def verl_nepo_advantage(*args, **kwargs):
    """verl's estimator contract is (advantages, returns), both tensors.

    A trainer must explicitly supply the aligned teacher/old-policy statistics.
    Selecting the estimator alone does not implement the teacher forward pass.
    """
    advantages, _ = nepo_advantage(*args, **kwargs)
    return advantages, advantages.clone()


def policy_loss(old_logp, new_logp, advantages, mask, clip_ratio=0.2):
    cfg = OmegaConf.create(
        {
            "clip_ratio": clip_ratio,
            "clip_ratio_low": clip_ratio,
            "clip_ratio_high": clip_ratio,
            "clip_ratio_c": 3.0,
            "global_batch_info": {},
        }
    )
    return compute_policy_loss_vanilla(
        old_logp, new_logp, advantages, mask, "token-mean", cfg
    )
