"""Real-model checks: multimodal retention, causal alignment, immutable old policy."""

import argparse, json
from pathlib import Path
import torch
from .model import ModelIO, split_planning_tokens
from .schema import load_examples, format_response


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--device", default="cuda")
    a = p.parse_args()
    torch.set_num_threads(4)
    io = ModelIO(a.model, a.device, dtype="bfloat16")
    ex = load_examples(a.data)[0]
    enc = io.encode(ex)
    response = io.tokenizer.encode(
        format_response(ex.target) + io.tokenizer.eos_token, add_special_tokens=False
    )
    boundary = split_planning_tokens(io.tokenizer, response)
    assert boundary is not None, "Tokenizer does not preserve the planning boundary"
    prefix = io.append(enc, response[:boundary])
    versions = [p._version for p in io.model.parameters()]
    with torch.no_grad():
        full, h = io.token_stats(enc, response, entropy=True)
        plan, _ = io.token_stats(prefix, response[boundary:])
    assert torch.isfinite(full).all() and torch.isfinite(h).all() and (h >= -1e-4).all()
    torch.testing.assert_close(full[:, boundary:], plan, atol=1e-5, rtol=1e-5)
    assert versions == [p._version for p in io.model.parameters()]
    assert response[-1] == io.tokenizer.eos_token_id
    retained = {
        k: tuple(v.shape) for k, v in enc.items() if "pixel" in k or "grid" in k
    }
    if ex.images:
        assert retained and io.vision
        for k in retained:
            assert prefix[k].data_ptr() == enc[k].data_ptr()
    out = {
        "passed": True,
        "model": a.model,
        "vision": io.vision,
        "image_tensors": retained,
        "response_tokens": len(response),
        "planning_boundary": boundary,
        "same_prefix_max_error": float((full[:, boundary:] - plan).abs().max()),
        "old_policy_unchanged": True,
        "eos_retained": True,
    }
    Path(a.output).write_text(json.dumps(out, indent=2))
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
