"""Optional Ray job boundary for a single-GPU verl-kernel training run.

Explicitly not a distributed FSDP implementation. Each run owns one GPU and
uses the same tested NEPO implementation as the local entry point.
"""

import argparse, sys
import ray


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--address")
    p.add_argument("--cpus", type=int, default=4)
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    args = a.args[1:] if a.args[:1] == ["--"] else a.args
    if not args:
        raise ValueError("Pass train arguments after --")
    ray.init(
        address=a.address,
        runtime_env={
            "env_vars": {
                "TOKENIZERS_PARALLELISM": "false",
                "VERL_USE_EXTERNAL_PLUGINS": "none",
            }
        },
    )

    @ray.remote(num_gpus=1, num_cpus=a.cpus)
    def train_worker(argv):
        from ec_verl.train import main as train_main

        sys.argv = ["ec-train", *argv]
        train_main()
        return {"complete": True}

    try:
        print(ray.get(train_worker.remote(args)))
    finally:
        ray.shutdown()


if __name__ == "__main__":
    main()
