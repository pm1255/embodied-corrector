"""Overlay recorded four-field decisions on every frame of a continuous episode.

No motion is synthesized or omitted. The output keeps the source recording rate;
only a final three-second hold is added to make the verified outcome readable.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG, WHITE, MUTED, ACCENT = '#111a2a', '#f6f7fb', '#b9c5d8', '#a0e8ce'


def render(raw, record_path, output, title, ffmpeg, font_dir):
    record = json.loads(record_path.read_text())
    meta, events, result = record['manifest'], record['events'], record['result']
    assert result['success'] and events[-1]['official_success'], 'Only verified recoveries belong in this gallery'
    assert any(e.get('brain', {}).get('Judge') == 'failure' for e in events if e.get('brain'))
    assert meta['continuous_episode'] and not meta['reset_after_failure']
    assert all(not any('\u4e00' <= c <= '\u9fff' for c in str(e.get('brain', ''))) for e in events)
    fps, hz = meta['recording_fps'], meta['control_frequency_hz']
    fonts = {}

    def font(size, bold=False):
        key = size, bold
        if key not in fonts:
            fonts[key] = ImageFont.truetype(str(font_dir / ('Arial Bold.ttf' if bold else 'Arial.ttf')), size)
        return fonts[key]

    def text(d, x, y, value, size=25, color=WHITE, bold=False):
        d.text((x, y), value, font=font(size, bold), fill=color)

    def lines(value, size, width):
        out, line = [], ''
        for word in value.split():
            candidate = (line + ' ' + word).strip()
            if font(size).getlength(candidate) > width and line:
                out.append(line)
                line = word
            else:
                line = candidate
        return out + [line]

    def panel(event, final=False):
        im = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(im)
        text(d, 48, 26, 'EMBODIED-CORRECTOR', 20, ACCENT, True)
        text(d, 1390, 26, f'GPT proxy  /  Seed {meta["seed"]}  /  1×', 20, MUTED)
        title_size = 38
        while font(title_size, True).getlength(title) > 1824 and title_size > 26:
            title_size -= 1
        assert font(title_size, True).getlength(title) <= 1824, 'Original task title exceeds the available width'
        text(d, 48, 77, title, title_size, WHITE, True)
        d.line((48, 140, 1872, 140), fill='#344158', width=1)
        text(d, 32, 157, 'BRAIN OUTPUT' if event.get('brain') else 'INITIAL ATTEMPT', 21, ACCENT, True)
        text(d, 680, 157, 'CONTINUOUS SIMULATOR RECORDING', 21, ACCENT, True)
        brain = event.get('brain')
        if brain:
            brain = dict(brain)
            brain['Judge'] = 'Failure — recovery needed' if brain['Judge'] == 'failure' else 'Success — previous substep verified'
            if final:
                brain['Judge'] = 'Success — task completed'
        else:
            brain = {'Action': 'Navigate to the prep counter.' if meta.get('navigation_and_manipulation') else 'Approach and grasp the target.', 'Stage': 'Attempt → Observe → Correct', 'Timing': 'Diagnosis follows the observed action outcome.'}
        size = 29
        while sum(len(lines(brain[k], size, 580)) * size * 1.22 + 44 for k in brain) > 802:
            size -= 1
        assert size >= 24, 'Decision text is too long to present legibly'
        y = 204
        for key in brain:
            text(d, 32, y, key, 22, '#ffbea8' if key in ['Judge', 'Cause'] else ACCENT, True)
            y += 31
            for line in lines(brain[key], size, 580):
                text(d, 32, y, line, size)
                y += size * 1.22
            y += 13
        text(d, 32, 1034, 'GPT proxy · State-assisted control', 18, MUTED)
        text(d, 680, 1034, 'OFFICIAL RESULT: SUCCESS' if final else 'Continuous episode · No reset after failure', 20, ACCENT if final else MUTED, final)
        return im

    rw, rh = meta.get('raw_width', 640), meta.get('raw_height', 512)
    active = [e for e in events if e['step_end'] > e['step_start']]
    output.parent.mkdir(parents=True, exist_ok=True)
    reader = subprocess.Popen([ffmpeg, '-v', 'error', '-i', str(raw), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    writer = subprocess.Popen([ffmpeg, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-threads', '4', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE)
    cache, n, ei, last = {}, 0, 0, None
    while True:
        buf = reader.stdout.read(rw * rh * 3)
        if not buf:
            break
        assert len(buf) == rw * rh * 3
        step = (n + 1) * hz / fps
        while ei + 1 < len(active) and step > active[ei]['step_end']:
            ei += 1
        event = active[ei]
        if ei not in cache:
            cache[ei] = panel(event)
        im = cache[ei].copy()
        frame = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(rh, rw, 3))
        last = Image.new('RGB', (1208, 810), BG)
        scale = min(1208/rw, 810/rh)
        frame = frame.resize((round(rw*scale), round(rh*scale)), Image.Resampling.LANCZOS)
        last.paste(frame, ((1208-frame.width)//2, (810-frame.height)//2))
        im.paste(last, (680, 200))
        d = ImageDraw.Draw(im)
        d.line((680, 1016, 680 + 1208 * min(1, step / result['steps']), 1016), fill=ACCENT, width=3)
        writer.stdin.write(im.tobytes())
        n += 1
    assert abs(n - result['steps'] * fps / hz) <= 1, (n, result['steps'])
    final = panel(events[-1], final=True)
    final.paste(last, (680, 200))
    for _ in range(fps * 3):
        writer.stdin.write(final.tobytes())
    writer.stdin.close()
    assert writer.wait() == 0 and reader.wait() == 0
    # Poster is extracted from the encoded output's actual first frame.
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(output), '-frames:v', '1', '-q:v', '2', str(output.with_name(output.stem + '-poster.jpg'))], check=True)
    final.save(output.with_name(output.stem + '-final.jpg'), quality=93)
    print(json.dumps(dict(case=record['case'], frames=n, speed=1, final_success=True, output=str(output))), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['raw', 'record', 'output', 'font-dir']:
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--title', required=True)
    p.add_argument('--ffmpeg', default='ffmpeg')
    a = p.parse_args()
    render(a.raw, a.record, a.output, a.title, a.ffmpeg, a.font_dir)
