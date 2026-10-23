"""Local inference endpoints for the official EmbodiedBench custom-model API."""

import argparse, io, json, threading
import torch
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from .model import ModelIO
from .prompts import SYSTEM
from .schema import normalize_deployed_response


def create_app(engine, corrector=None):
    app = FastAPI(title="Embodied-Corrector inference")
    lock = threading.Lock()
    corrector = corrector or engine

    def infer(model, sentence, picture, correct=False):
        msgs = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": sentence}],
            }
        ]
        if correct:
            msgs.insert(0, {"role": "system", "content": SYSTEM})
        text = model.processor.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        enc = model.processor(text=[text], images=[picture], return_tensors="pt")
        enc = {
            k: v.to(model.device) if isinstance(v, torch.Tensor) else v
            for k, v in enc.items()
        }
        _, answer = model.generate(enc, 256 if correct else 192, sample=False)
        return answer

    @app.get("/health")
    def health():
        return {"ready": True, "vision": engine.vision, "backend": "transformers"}

    @app.post("/respond")
    async def respond(sentence: str = Form(...), image: UploadFile = File(...)):
        content = await image.read()
        if len(content) > 12 * 1024 * 1024:
            raise HTTPException(413, "Image exceeds 12 MB")
        try:
            picture = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception as exc:
            raise HTTPException(400, "Invalid image") from exc
        if not engine.vision:
            raise HTTPException(
                400, "Visual benchmark requires a vision-language model"
            )
        with lock, torch.no_grad():
            answer = infer(engine, sentence, picture)
        return {"response": answer}

    @app.post("/correct")
    async def correct(sentence: str = Form(...), image: UploadFile = File(...)):
        content = await image.read()
        if len(content) > 12 * 1024 * 1024:
            raise HTTPException(413, "Image exceeds 12 MB")
        try:
            picture = Image.open(io.BytesIO(content)).convert("RGB")
            evidence = json.loads(sentence)
            if set(evidence) - {"task", "previous_subtask", "history", "observation"}:
                raise ValueError("Only public evidence is accepted")
        except Exception as exc:
            raise HTTPException(400, "Invalid image or public evidence") from exc
        if not corrector.vision:
            raise HTTPException(400, "Corrector requires a vision-language model")
        with lock, torch.no_grad():
            answer = infer(corrector, json.dumps(evidence), picture, True)
        normalized, fields = normalize_deployed_response(answer)
        return {"response": normalized, "fields": fields, "raw_response": answer}

    return app


def main():
    import uvicorn

    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--corrector-model")
    p.add_argument("--device", default="cuda")
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--port", type=int, default=18127)
    p.add_argument("--host", default="127.0.0.1")
    a = p.parse_args()
    torch.set_num_threads(4)
    engine = ModelIO(a.model, a.device, dtype=a.dtype)
    correction = (
        ModelIO(a.corrector_model, a.device, dtype=a.dtype)
        if a.corrector_model
        else None
    )
    uvicorn.run(create_app(engine, correction), host=a.host, port=a.port)


if __name__ == "__main__":
    main()
