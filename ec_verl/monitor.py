from pathlib import Path
import json, time
from torch.utils.tensorboard import SummaryWriter

STAGES = ("data", "sft_assess", "sft_plan", "nepo", "evaluation")


class Monitor:
    def __init__(self, root, scope="smoke"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.writer = SummaryWriter(str(self.root / "tensorboard" / scope))
        self.state = {s: "waiting" for s in STAGES}
        self.scope = scope
        self.log = {"scope": scope, "stages": self.state}
        self.status()

    def status(self, stage=None, state=None):
        if stage:
            self.state[stage] = state
        for s in STAGES:
            for v in ("waiting", "running", "complete", "failed"):
                self.writer.add_scalar(
                    f"status/{s}/{v}", float(self.state[s] == v), int(time.time())
                )
        self.log["updated"] = time.time()
        (self.root / "status.json").write_text(json.dumps(self.log, indent=2))
        self.writer.flush()

    def scalars(self, values, step):
        for k, v in values.items():
            self.writer.add_scalar(k, float(v), step)
        self.writer.flush()
        with (self.root / "metrics.jsonl").open("a") as f:
            f.write(
                json.dumps(
                    {"step": step, "time": time.time(), **values}, allow_nan=False
                )
                + "\n"
            )

    def checkpoint(self, path, step):
        self.writer.add_text("checkpoints/path", str(path), step)
        self.scalars({"checkpoints/saved_step": step}, step)

    def close(self):
        self.writer.close()
