"""HF model execution, with multimodal evidence retained in both NEPO views."""

from pathlib import Path
import torch
from transformers import AutoConfig, AutoTokenizer, AutoProcessor, AutoModelForCausalLM
from .prompts import messages


class ModelIO:
    def __init__(
        self, path, device="cpu", lora=False, dtype="float32", max_image_pixels=65536
    ):
        from peft import LoraConfig, PeftModel, get_peft_model

        self.device = torch.device(device)
        adapter = Path(path) / "adapter_config.json"
        if adapter.exists():
            import json

            base = json.loads(adapter.read_text())["base_model_name_or_path"]
        else:
            base = path
        cfg = AutoConfig.from_pretrained(base, trust_remote_code=False)
        self.vision = hasattr(cfg, "vision_config")
        self.tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=False)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.processor = (
            AutoProcessor.from_pretrained(
                base, min_pixels=3136, max_pixels=max_image_pixels
            )
            if self.vision
            else None
        )
        if self.vision:
            from transformers import AutoModelForImageTextToText

            cls = AutoModelForImageTextToText
        else:
            cls = AutoModelForCausalLM
        dt = getattr(torch, dtype)
        self.model = cls.from_pretrained(
            base, torch_dtype=dt, attn_implementation="eager", trust_remote_code=False
        ).to(self.device)
        if adapter.exists():
            self.model = PeftModel.from_pretrained(self.model, path, is_trainable=lora)
        elif lora:
            self.model = get_peft_model(
                self.model,
                LoraConfig(
                    r=8,
                    lora_alpha=16,
                    lora_dropout=0.0,
                    target_modules=["q_proj", "v_proj"],
                    task_type="CAUSAL_LM",
                ),
            )
        # Stochastic dropout would invalidate the shared-old-policy comparison.
        for module in self.model.modules():
            if isinstance(module, torch.nn.Dropout):
                module.p = 0.0
        self.model.eval()

    def encode(self, ex, stage="nepo"):
        msgs = messages(ex, stage)
        if ex.images and not self.vision:
            raise ValueError(
                "Image inputs require a VL model; refusing to silently drop them"
            )
        renderer = self.processor or self.tokenizer
        text = renderer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        if self.vision:
            from PIL import Image

            ims = [Image.open(p).convert("RGB") for p in ex.images]
            enc = self.processor(text=[text], images=ims or None, return_tensors="pt")
        else:
            enc = self.tokenizer(text, return_tensors="pt", add_special_tokens=False)
        return {
            k: v.to(self.device) if isinstance(v, torch.Tensor) else v
            for k, v in enc.items()
        }

    def append(self, enc, tokens):
        tokens = torch.as_tensor(tokens, device=self.device, dtype=torch.long).reshape(
            1, -1
        )
        type_keys = ("token_type_ids", "mm_token_type_ids")
        out = {
            k: v
            for k, v in enc.items()
            if k not in ("input_ids", "attention_mask", "position_ids", *type_keys)
        }
        out["input_ids"] = torch.cat([enc["input_ids"], tokens], -1)
        out["attention_mask"] = torch.ones_like(out["input_ids"])
        for key in type_keys:
            if key in enc:
                out[key] = torch.cat([enc[key], torch.zeros_like(tokens)], -1)
        return out

    def token_stats(self, enc, response, entropy=False):
        # The next-token logit at prompt_length-1 predicts response[0].
        if not response:
            raise ValueError("Empty response")
        full = self.append(enc, response)
        output = self.model(**full, use_cache=False)
        offset = enc["input_ids"].shape[1] - 1
        logits = output.logits[:, offset : offset + len(response), :].float()
        logz = torch.logsumexp(logits, -1)
        tokens = torch.tensor(response, device=self.device).reshape(1, -1, 1)
        lp = logits.gather(-1, tokens).squeeze(-1) - logz
        h = logz - (logits.softmax(-1) * logits).sum(-1) if entropy else None
        return lp, h

    @torch.no_grad()
    def generate(self, enc, max_new_tokens=160, sample=False):
        self.model.eval()
        kwargs = dict(
            max_new_tokens=max_new_tokens,
            do_sample=sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            use_cache=True,
        )
        if sample:
            kwargs.update(temperature=1.0, top_p=1.0, top_k=0)
        generated = self.model.generate(**enc, **kwargs)[
            0, enc["input_ids"].shape[1] :
        ].tolist()
        # EOS is part of the sampled action and must remain in the loss mask.
        return generated, self.tokenizer.decode(generated, skip_special_tokens=True)

    def save(self, path):
        self.model.save_pretrained(path, safe_serialization=True)
        self.tokenizer.save_pretrained(path)
        if self.processor:
            self.processor.save_pretrained(path)


def split_planning_tokens(tokenizer, response):
    """Return a boundary only if the response contains a complete ordered prefix.

    Never retokenize the sampled continuation. Decode prefixes to find the exact
    first token belonging to the Sub field; reject a token straddling the boundary.
    """
    import re

    text = tokenizer.decode(
        response, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    marks = list(re.finditer(r"(?m)^(Judge|Cause|Sub|Fine):", text))
    if [m.group(1) for m in marks][:3] != ["Judge", "Cause", "Sub"]:
        return None
    pos = marks[2].start()
    for k in range(1, len(response)):
        prefix = tokenizer.decode(
            response[:k], skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        if len(prefix) == pos and text.startswith(prefix):
            return k
        if len(prefix) > pos:
            break
    return None
