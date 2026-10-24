#!/usr/bin/env python3
"""Minimal local OpenAI-compatible image endpoint using Transformers (one request at a time)."""
import argparse
import base64
import io
import json
import threading
import time
import hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--served-model-name', default='rynnbrain')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18409)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--metadata-output', type=Path)
    args = parser.parse_args()
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    torch.set_num_threads(2)
    torch.manual_seed(0)
    print('Loading processor and model', flush=True)
    processor = AutoProcessor.from_pretrained(args.model_path, local_files_only=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_path, dtype=torch.bfloat16, device_map=args.device,
        attn_implementation='sdpa', local_files_only=True).eval()
    print('Model loaded', flush=True)
    import transformers
    import PIL
    metadata = {'model_path': str(Path(args.model_path).resolve()),
                'served_model_name': args.served_model_name,
                'config_sha256': hashlib.sha256((Path(args.model_path) / 'config.json').read_bytes()).hexdigest(),
                'torch': torch.__version__, 'transformers': transformers.__version__,
                'pillow': PIL.__version__, 'dtype': 'bfloat16', 'attention': 'sdpa',
                'seed': 0, 'device': args.device,
                'gpu': torch.cuda.get_device_name(args.device) if args.device.startswith('cuda') else None}
    if args.metadata_output:
        args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_output.write_text(json.dumps(metadata, indent=2) + '\n')
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, data):
            blob = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)

        def do_GET(self):
            if self.path == '/v1/models':
                self.respond(200, {'object': 'list', 'data': [{'id': args.served_model_name,
                              'object': 'model', 'owned_by': 'local-transformers'}]})
            else:
                self.respond(404, {'error': 'Unknown route'})

        def do_POST(self):
            if self.path != '/v1/chat/completions':
                return self.respond(404, {'error': 'Unknown route'})
            try:
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if body['model'] != args.served_model_name:
                    raise ValueError('Wrong served model name')
                if body.get('stream') or body.get('temperature', 0) != 0:
                    raise ValueError('This validation server supports non-streaming greedy decoding only')
                images, messages = [], []
                for message in body['messages']:
                    content = message['content']
                    if isinstance(content, list):
                        converted = []
                        for part in content:
                            if part['type'] == 'image_url':
                                url = part['image_url']['url']
                                if not url.startswith('data:image/'):
                                    raise ValueError('Only inline base64 images are supported')
                                with Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1]))) as image:
                                    images.append(image.convert('RGB'))
                                converted.append({'type': 'image'})
                            elif part['type'] == 'text':
                                converted.append(part)
                            else:
                                raise ValueError('Unsupported content part')
                        content = converted
                    messages.append({'role': message['role'], 'content': content})
                started = time.monotonic()
                with lock, torch.inference_mode():
                    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                          **body.get('chat_template_kwargs', {}))
                    inputs = processor(text=[text], images=images or None, padding=True, return_tensors='pt').to(args.device)
                    prompt_length = inputs['input_ids'].shape[1]
                    generated = model.generate(**inputs, max_new_tokens=int(body.get('max_tokens', 2048)), do_sample=False)
                    tokens = generated[0, prompt_length:]
                    content = processor.decode(tokens, skip_special_tokens=True)
                    eos = model.generation_config.eos_token_id
                    eos = eos if isinstance(eos, list) else [eos]
                    finish = 'stop' if int(tokens[-1]) in eos else 'length'
                    count = len(tokens)
                    del inputs, generated, tokens
                print(json.dumps({'images': len(images), 'prompt_tokens': prompt_length,
                                  'completion_tokens': count, 'seconds': round(time.monotonic() - started, 2)}), flush=True)
                self.respond(200, {'id': 'local-validation', 'object': 'chat.completion', 'model': args.served_model_name,
                                  'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content},
                                               'finish_reason': finish}],
                                  'usage': {'prompt_tokens': prompt_length, 'completion_tokens': count,
                                            'total_tokens': prompt_length + count}})
            except Exception as error:
                import traceback
                traceback.print_exc()
                self.respond(500, {'error': {'message': f'{type(error).__name__}: {error}'}})

    print(f'Listening on {args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
