"""Video sampling compatible with the historical small benchmark protocol."""
import base64
import functools
import io
import json
import subprocess
from pathlib import Path

from PIL import Image


def sample_indices(n, duration, max_frames=6, fps=None):
    count = min(n, max(4, min(32, round(duration * (1.0 if fps is None else fps)))))
    indices = sorted({round(i * (n - 1) / (count - 1)) for i in range(count)}) if count > 1 else [0]
    if len(indices) > max_frames:
        stride = len(indices) / max_frames
        indices = [indices[int(i * stride)] for i in range(max_frames)]
    return indices


def probe(path):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=nb_frames,avg_frame_rate,width,height:format=duration', '-of', 'json', str(path)
    ], check=True, capture_output=True, text=True, timeout=60)
    info = json.loads(result.stdout)
    if not info.get('streams'):
        raise ValueError(f'No video stream: {path}')
    stream = info['streams'][0]
    duration = float(info['format']['duration'])
    num, den = map(float, stream['avg_frame_rate'].split('/'))
    n = stream.get('nb_frames')
    n = int(n) if n and n != 'N/A' else round(duration * num / den)
    if n < 1 or duration <= 0:
        raise ValueError(f'Invalid video duration/frame count: {path}')
    return duration, n, stream


@functools.lru_cache(maxsize=96)
def image_parts(path, max_frames=6, fps=None):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    duration, n, _ = probe(path)
    indices = sample_indices(n, duration, max_frames, fps)
    selection = '+'.join(f'eq(n\\,{i})' for i in indices)
    result = subprocess.run([
        'ffmpeg', '-v', 'error', '-threads', '1', '-i', str(path),
        '-filter_threads', '1', '-vf', f'select={selection},scale=448:-1',
        '-vsync', '0', '-f', 'image2pipe', '-vcodec', 'png', '-threads', '1', 'pipe:1'
    ], check=True, capture_output=True, timeout=120)
    signature = b'\x89PNG\r\n\x1a\n'
    parts = []
    for chunk in result.stdout.split(signature)[1:]:
        with Image.open(io.BytesIO(signature + chunk)) as image:
            rgb = image.convert('RGB')
            buffer = io.BytesIO()
            rgb.save(buffer, format='PNG')
        parts.append({'type': 'image_url', 'image_url': {
            'url': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        }})
    if len(parts) != len(indices):
        raise ValueError(f'Decoded {len(parts)} of {len(indices)} requested frames: {path}')
    return parts


def to_chat(messages, videos, max_frames=6, fps=None):
    output, cursor = [], 0
    for message in messages:
        if message['role'] != 'user' or '<video>' not in message['content']:
            output.append(dict(message))
            continue
        pieces = message['content'].split('<video>')
        content = []
        for i, piece in enumerate(pieces):
            if piece.strip():
                content.append({'type': 'text', 'text': piece})
            if i < len(pieces) - 1:
                if cursor >= len(videos):
                    raise ValueError('More video placeholders than supplied videos')
                content.extend(image_parts(str(videos[cursor]), max_frames, fps))
                cursor += 1
        output.append({'role': message['role'], 'content': content})
    if cursor != len(videos):
        raise ValueError(f'{cursor} video placeholders but {len(videos)} supplied videos')
    return output
