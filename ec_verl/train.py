"""Inspectable single-node NEPO trainer using verl DataProto and PPO/GRPO kernels.

The rollout and verified-prefix passes share the unchanged current policy, then
the optimizer steps only after all old-policy statistics have been collected.
"""

import argparse, json, random, hashlib
from pathlib import Path
import numpy as np
import torch
from verl import DataProto
from .schema import load_examples, check_split, format_response
from .model import ModelIO, split_planning_tokens
from .nepo import NEPOConfig, nepo_advantage, policy_loss
from .reward import score_response
from .monitor import Monitor


def sample_fingerprint(model):
    h = hashlib.sha256()
    for name, p in model.named_parameters():
        if p.requires_grad:
            h.update(name.encode())
            h.update(p.detach().float().cpu().numpy().tobytes())
    return h.hexdigest()


def save_checkpoint(io, optimizer, root, stage, step, monitor):
    path = Path(root) / "checkpoints" / f"{stage}-{step:04d}"
    io.save(path)
    torch.save(
        {
            "optimizer": optimizer.state_dict(),
            "torch_rng": torch.get_rng_state(),
            "step": step,
            "stage": stage,
        },
        path / "trainer_state.pt",
    )
    monitor.checkpoint(path, step)
    return path


def run_sft(io, rows, stage, steps, optimizer, monitor, root):
    monitor.status(stage, "running")
    fields = ("Judge", "Cause") if stage == "sft_assess" else ("Sub", "Fine")
    before = sample_fingerprint(io.model)
    for step in range(1, steps + 1):
        ex = rows[(step - 1) % len(rows)]
        enc = io.encode(ex)
        # Keep the same deployment prompt. In planning SFT the verified
        # assessment is an assistant prefix and receives no planning loss.
        if stage == "sft_plan":
            prefix = io.tokenizer.encode(
                format_response(ex.target, ("Judge", "Cause")) + "\n",
                add_special_tokens=False,
            )
            enc = io.append(enc, prefix)
        target = format_response(ex.target, fields) + (
            io.tokenizer.eos_token if stage == "sft_plan" else "\n"
        )
        tokens = io.tokenizer.encode(target, add_special_tokens=False)
        optimizer.zero_grad(set_to_none=True)
        lp, _ = io.token_stats(enc, tokens)
        loss = -lp.mean()
        if not torch.isfinite(loss):
            raise FloatingPointError("Nonfinite SFT loss")
        loss.backward()
        grad = torch.nn.utils.clip_grad_norm_(io.model.parameters(), 1.0)
        optimizer.step()
        monitor.scalars(
            {
                f"{stage}/loss": loss.item(),
                f"{stage}/progress": step / steps,
                f"{stage}/gradient_norm": grad.item(),
            },
            step,
        )
    path = save_checkpoint(io, optimizer, root, stage, steps, monitor)
    after = sample_fingerprint(io.model)
    if before == after:
        raise RuntimeError("SFT did not change trainable parameters")
    monitor.status(stage, "complete")
    return path


def collect_rollouts(io, ex, group_size, max_new_tokens, cfg):
    prompt = io.encode(ex)
    records = []
    for _ in range(group_size):
        tokens, text = io.generate(prompt, max_new_tokens, sample=True)
        with torch.no_grad():
            old, entropy = io.token_stats(prompt, tokens, entropy=True)
            teacher = old.clone()
            planning = torch.zeros_like(old)
            boundary = split_planning_tokens(io.tokenizer, tokens)
            if boundary is not None:
                # Replace only the assessment prefix; keep image, task and sampled y identical.
                verified = format_response(ex.target, ("Judge", "Cause")) + "\n"
                verified_tokens = io.tokenizer.encode(
                    verified, add_special_tokens=False
                )
                teacher_prompt = io.append(prompt, verified_tokens)
                teacher_plan, _ = io.token_stats(teacher_prompt, tokens[boundary:])
                teacher[:, boundary:] = teacher_plan
                planning[:, boundary:] = 1
        scores = score_response(text, ex.target, ex.rubric)
        records.append(
            dict(
                tokens=tokens,
                text=text,
                old=old[0],
                teacher=teacher[0],
                entropy=entropy[0],
                planning=planning[0],
                scores=scores,
                boundary=boundary,
            )
        )
    width = max(len(r["tokens"]) for r in records)

    def pad(key):
        return torch.stack(
            [
                torch.nn.functional.pad(r[key], (0, width - len(r["tokens"])))
                for r in records
            ]
        )

    mask = torch.zeros(group_size, width, device=io.device)
    rewards = torch.zeros_like(mask)
    for i, r in enumerate(records):
        mask[i, : len(r["tokens"])] = 1
        rewards[i, len(r["tokens"]) - 1] = r["scores"]["reward"]
    data = DataProto.from_dict(
        tensors={
            "old_log_probs": pad("old"),
            "teacher_log_probs": pad("teacher"),
            "old_entropy": pad("entropy"),
            "planning_mask": pad("planning"),
            "response_mask": mask,
            "token_level_rewards": rewards,
        },
        non_tensors={"uid": np.array([ex.id] * group_size, dtype=object)},
    )
    advantages, metrics = nepo_advantage(
        **{
            k: data.batch[k]
            for k in (
                "token_level_rewards",
                "response_mask",
                "old_log_probs",
                "teacher_log_probs",
                "old_entropy",
                "planning_mask",
            )
        },
        index=data.non_tensor_batch["uid"],
        nepo_config=cfg,
    )
    data.batch["advantages"] = advantages
    return prompt, records, data, metrics


def run_nepo(
    io, rows, steps, optimizer, monitor, root, group_size, max_new_tokens, cfg
):
    monitor.status("nepo", "running")
    total_planning = 0
    total_signal = 0.0
    before = sample_fingerprint(io.model)
    for step in range(1, steps + 1):
        ex = rows[(step - 1) % len(rows)]
        prompt, records, data, metrics = collect_rollouts(
            io, ex, group_size, max_new_tokens, cfg
        )
        optimizer.zero_grad(set_to_none=True)
        denominator = data.batch["response_mask"].sum()
        losses = []
        for i, r in enumerate(records):
            lp, _ = io.token_stats(prompt, r["tokens"])
            length = len(r["tokens"])
            loss, _ = policy_loss(
                data.batch["old_log_probs"][i : i + 1, :length],
                lp,
                data.batch["advantages"][i : i + 1, :length],
                data.batch["response_mask"][i : i + 1, :length],
                cfg.clip_ratio,
            )
            weighted = loss * length / denominator
            if not torch.isfinite(weighted):
                raise FloatingPointError("Nonfinite NEPO loss")
            weighted.backward()
            losses.append(weighted.detach().item())
        grad = torch.nn.utils.clip_grad_norm_(io.model.parameters(), 1.0)
        optimizer.step()
        total_planning += metrics["nepo/planning_tokens"]
        total_signal += metrics["nepo/delta_abs_mean"] * metrics["nepo/planning_tokens"]
        metrics.update(
            {
                "nepo/loss": sum(losses),
                "nepo/reward": np.mean([r["scores"]["reward"] for r in records]),
                "nepo/format_valid": np.mean(
                    [r["scores"]["format_valid"] for r in records]
                ),
                "nepo/gradient_norm": grad.item(),
                "nepo/progress": step / steps,
            }
        )
        monitor.scalars(metrics, step)
        with (Path(root) / "rollouts.jsonl").open("a") as f:
            for r in records:
                f.write(
                    json.dumps(
                        {
                            "step": step,
                            "id": ex.id,
                            "text": r["text"],
                            "scores": r["scores"],
                            "planning_boundary": r["boundary"],
                            "token_ids": r["tokens"],
                        }
                    )
                    + "\n"
                )
    path = save_checkpoint(io, optimizer, root, "nepo", steps, monitor)
    after = sample_fingerprint(io.model)
    proof = {
        "before": before,
        "after": after,
        "parameters_changed": before != after,
        "planning_tokens": total_planning,
        "absolute_nepo_signal": total_signal,
    }
    (Path(root) / "nepo_proof.json").write_text(json.dumps(proof, indent=2))
    if total_planning == 0:
        raise RuntimeError(
            "No generated planning boundary: NEPO was not exercised. Increase SFT before retrying."
        )
    if before == after:
        raise RuntimeError("NEPO did not update parameters")
    if cfg.coefficient > 0 and total_signal == 0:
        raise RuntimeError(
            "All NEPO signals were zero; this run did not exercise privileged guidance"
        )
    monitor.status("nepo", "complete")
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--train", required=True)
    p.add_argument("--eval", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--dtype", default="float32", choices=["float32", "bfloat16"])
    p.add_argument("--lora", action="store_true")
    p.add_argument("--sft-steps", type=int, default=8)
    p.add_argument("--nepo-steps", type=int, default=2)
    p.add_argument("--group-size", type=int, default=2)
    p.add_argument("--max-new-tokens", type=int, default=160)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--scope", default="smoke", choices=["smoke", "formal"])
    p.add_argument("--kappa", type=float, default=1.0)
    p.add_argument("--beta", type=float, default=0.5)
    p.add_argument("--opd-coef", type=float, default=1.0)
    p.add_argument("--threads", type=int, default=4)
    a = p.parse_args()
    root = Path(a.output)
    if (root / "config.json").exists():
        raise FileExistsError("Run already exists; use a new output path")
    if min(a.sft_steps, a.nepo_steps) < 1 or a.group_size < 2:
        raise ValueError("Need positive training steps and group_size >= 2")
    torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    random.seed(a.seed)
    monitor = Monitor(root, a.scope)
    (root / "config.json").write_text(json.dumps(vars(a), indent=2))
    active = "data"
    try:
        monitor.status("data", "running")
        train = load_examples(a.train)
        evaluation = load_examples(a.eval)
        check_split(train, evaluation)
        if a.scope == "formal" and any(
            e.provenance.startswith(("synthetic", "paper_")) for e in train + evaluation
        ):
            raise ValueError(
                "Demonstration fixtures cannot be reported as a formal benchmark"
            )
        monitor.scalars(
            {
                "data/train_examples": len(train),
                "data/eval_examples": len(evaluation),
                "data/progress": 1,
            },
            0,
        )
        monitor.status("data", "complete")
        io = ModelIO(a.model, a.device, a.lora, a.dtype)
        optimizer = torch.optim.AdamW(
            [p for p in io.model.parameters() if p.requires_grad],
            lr=a.learning_rate,
            weight_decay=0,
        )
        for active in ("sft_assess", "sft_plan"):
            run_sft(io, train, active, a.sft_steps, optimizer, monitor, root)
        active = "nepo"
        final = run_nepo(
            io,
            train,
            a.nepo_steps,
            optimizer,
            monitor,
            root,
            a.group_size,
            a.max_new_tokens,
            NEPOConfig(a.opd_coef, a.kappa, a.beta),
        )
        active = "evaluation"
        from .evaluate import evaluate

        scores = evaluate(
            io, evaluation, root / "evaluation", a.max_new_tokens, monitor
        )
        (root / "complete.json").write_text(
            json.dumps(
                {"checkpoint": str(final), "evaluation": scores, "scope": a.scope},
                indent=2,
            )
        )
        print(
            json.dumps(
                {"complete": True, "checkpoint": str(final), "evaluation": scores}
            ),
            flush=True,
        )
    except Exception:
        monitor.status(active, "failed")
        raise
    finally:
        monitor.close()


if __name__ == "__main__":
    main()
