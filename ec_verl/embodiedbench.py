"""Execute the real EB-ALFRED Gym environment through a local Qwen service.

This adapter does not claim simulator success from a model answer. Only the
environment's task_success predicate is scored; no scripted/mock fallback exists.
"""

import argparse, json, os, sys, io
from pathlib import Path
import requests
from PIL import Image
from .monitor import Monitor
from .schema import parse_response


def parse_action(answer, n_actions):
    try:
        obj = json.loads(
            answer.strip().removeprefix("```json").removesuffix("```").strip()
        )
        action = obj["action_id"]
        if type(action) is int and 0 <= action < n_actions:
            return action
    except (ValueError, KeyError, TypeError):
        pass
    raise ValueError("Model did not produce a valid in-range action_id")


def run_episode(
    env, endpoint, output, max_steps=30, corrector_endpoint=None, monitor=None
):
    observation = env.reset()
    history = []
    success = False
    done = False
    executed = 0
    correction = None
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    for step in range(max_steps):
        if monitor:
            monitor.scalars(
                {
                    "evaluation/episode_step": step,
                    "evaluation/step_budget_used": step / max_steps,
                },
                step,
            )
        picture = Image.fromarray(observation["head_rgb"])
        buffer = io.BytesIO()
        picture.save(buffer, format="PNG")
        picture.save(root / f"step-{step:03d}.png")
        # Explicit allowlist: never pass task_success, object_states or hidden metadata.
        public = {
            "task": env.episode_language_instruction,
            "actions": dict(enumerate(env.language_skill_set)),
            "history": history,
        }
        if correction:
            public["previous_correction"] = correction
        prompt = (
            "Choose the next action using the image and public action history. Return JSON with action_id (integer) and reason (string).\n"
            + json.dumps(public)
        )
        response = requests.post(
            endpoint,
            data={"sentence": prompt},
            files={"image": ("observation.png", buffer.getvalue(), "image/png")},
            timeout=300,
        )
        response.raise_for_status()
        answer = response.json()["response"]
        try:
            action = parse_action(answer, len(env.language_skill_set))
        except ValueError:
            history.append(
                {
                    "step": step,
                    "action": "invalid model response",
                    "feedback": "Output a valid action_id.",
                    "model_response": answer,
                }
            )
            continue
        observation, reward, done, info = env.step(action, reasoning=answer)
        executed += 1
        history.append(
            {
                "step": step,
                "action": env.language_skill_set[action],
                "feedback": str(info.get("env_feedback", "")),
                "model_response": answer,
            }
        )
        (root / "trace.json").write_text(json.dumps(history, indent=2))
        success = bool(info["task_success"])
        if corrector_endpoint and not done:
            evidence = {
                "task": env.episode_language_instruction,
                "previous_subtask": env.language_skill_set[action],
                "history": [
                    {k: h[k] for k in ("step", "action", "feedback")}
                    for h in history[-6:]
                ],
                "observation": str(info.get("env_feedback", "")),
            }
            buf = io.BytesIO()
            Image.fromarray(observation["head_rgb"]).save(buf, format="PNG")
            cr = requests.post(
                corrector_endpoint,
                data={"sentence": json.dumps(evidence)},
                files={"image": ("post.png", buf.getvalue(), "image/png")},
                timeout=300,
            )
            cr.raise_for_status()
            correction = cr.json()["response"]
            history[-1]["correction"] = correction
            history[-1]["correction_raw"] = cr.json().get("raw_response", correction)
            history[-1]["correction_format_valid"] = (
                parse_response(correction) is not None
            )
        (root / "trace.json").write_text(json.dumps(history, indent=2))
        if done:
            break
    if not executed:
        raise RuntimeError("No valid simulator action executed")
    result = {
        "success": success,
        "steps": len(history),
        "executed_actions": executed,
        "environment_done": bool(done),
        "adapter_step_limit_reached": not bool(done),
        "correction_enabled": bool(corrector_endpoint),
        "correction_calls": sum("correction" in h for h in history),
        "valid_structured_corrections": sum(
            h.get("correction_format_valid", False) for h in history
        ),
        "source": "EBAlfEnv.task_success",
        "mock": False,
    }
    (root / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--endpoint", default="http://127.0.0.1:18127/respond")
    p.add_argument("--output", required=True)
    p.add_argument(
        "--subset",
        default="base",
        choices=[
            "base",
            "common_sense",
            "complex_instruction",
            "spatial",
            "visual_appearance",
            "long_horizon",
        ],
    )
    p.add_argument("--episodes", type=int, default=1)
    p.add_argument("--max-steps", type=int, default=30)
    p.add_argument("--display", default="1")
    p.add_argument("--corrector-endpoint")
    p.add_argument("--thor-executable")
    a = p.parse_args()
    repo = Path(a.repo).resolve()
    root = Path(a.output).resolve()
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    if a.episodes < 1 or a.max_steps < 1:
        raise ValueError("episodes and max-steps must be positive")
    if not (repo / "embodiedbench/envs/eb_alfred/data/json_2.1.0").is_dir():
        raise FileNotFoundError(
            "Official EB-ALFRED data missing; run scripts/setup_embodiedbench.sh"
        )
    import importlib

    module = importlib.import_module("embodiedbench.envs.eb_alfred.EBAlfEnv")
    module.X_DISPLAY = a.display
    if a.thor_executable:
        # Defaults were bound at import time; configure this official constructor.
        original = module.ThorConnector.__init__

        def init_with_build(self, *args, **kwargs):
            kwargs["build_path"] = str(Path(a.thor_executable).resolve())
            original(self, *args, **kwargs)

        module.ThorConnector.__init__ = init_with_build
    monitor = Monitor(root, "eb_alfred")
    (root / "config.json").write_text(json.dumps(vars(a), indent=2))
    env = None
    try:
        requests.get(
            a.endpoint.rsplit("/", 1)[0] + "/health", timeout=10
        ).raise_for_status()
        monitor.status("evaluation", "running")
        env = module.EBAlfEnv(
            eval_set=a.subset,
            exp_name=root.name,
            selected_indexes=list(range(a.episodes)),
            resolution=300,
        )
        results = []
        for i in range(a.episodes):
            r = run_episode(
                env,
                a.endpoint,
                root / f"episode-{i:04d}",
                a.max_steps,
                a.corrector_endpoint,
                monitor,
            )
            results.append(r)
            monitor.scalars(
                {
                    "evaluation/progress": (i + 1) / a.episodes,
                    "evaluation/success_rate": sum(x["success"] for x in results)
                    / len(results),
                },
                i + 1,
            )
        summary = {
            "subset": a.subset,
            "episodes": len(results),
            "success_rate": sum(x["success"] for x in results) / len(results),
            "environment": "official EB-ALFRED",
            "results": results,
        }
        (root / "metrics.json").write_text(json.dumps(summary, indent=2))
        monitor.status("evaluation", "complete")
        print(json.dumps(summary))
    except Exception:
        monitor.status("evaluation", "failed")
        raise
    finally:
        if env is not None:
            env.close()
        monitor.close()


if __name__ == "__main__":
    main()
