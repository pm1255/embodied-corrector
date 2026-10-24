#!/usr/bin/env python3
"""Portable collect -> judge -> aggregate runner for EmbodiedDiag-Bench small."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .media import image_parts, to_chat
from .monitor import Monitor

PROTOCOL = 'small-portable-v1-question-roles'
MEDIA_OVERRIDES = {}
FMT_PLAN = ('\n\nRespond strictly in this format: '
            '<answer>subtask: <the next action> <the specific target object or destination></answer>')
FMT_CRIT = ('\n\nRespond strictly in this format: '
            '<think> what the robot did in the video and, if it failed, the exact cause </think>'
            '<answer> succeeded or failed, and the reason </answer>')
JUDGE_SYS = ('你是严格的评测裁判。给你机器人任务的【标准答案】和【模型回答】, 以及相关视频帧。'
             '只判断模型回答与标准答案在语义上是否一致, 不要解释。严格按要求只输出 JSON。')


def load(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def block(answer, tag):
    match = re.search(rf'<{tag}>(.*?)</{tag}>', answer, re.S)
    return match.group(1).strip() if match else ''


def subtask(answer):
    body = block(answer, 'answer') or answer
    match = re.search(r'subtask:\s*(.+)', body)
    if match:
        return re.split(r'</answer>|\n|action:', match.group(1))[0].strip().lower()
    match = re.search(r'redo "([^"]+)"|current subtask \(still\):\s*([^.\n]+)', body, re.I)
    if match:
        return (match.group(1) or match.group(2)).strip().lower()
    if re.search('fault is the navigation', body, re.I):
        return 'navigate'
    return body.strip().lower()


def verdict(answer):
    return 'fail' if re.search(r'\bfail', block(answer, 'answer') or answer, re.I) else 'ok'


def subset(row, trajectory=False):
    if trajectory:
        text = ' '.join(m['content'] for m in row['messages'])
        return 'nav' if len(re.findall(r'navigat|move to', text, re.I)) >= 2 else 'manip'
    text = ' '.join(m['content'] for m in row['messages'] if m['role'] != 'assistant')
    text += row['messages'][-1]['content']
    return 'nav' if re.search(r'navigat|move to|drive the base|站位|导航', text, re.I) else 'manip'


def trajectory_role(messages, index):
    question = messages[index - 1]['content'].rsplit('Question:', 1)[-1].strip()
    if question.startswith('Did what the robot just executed succeed?'):
        return 'critic'
    if question.startswith('Looking at the current situation, is the overall task complete?'):
        return 'planner'
    raise ValueError(f'Unrecognized trajectory question at message {index}')


def resolve_video(path, root):
    path = MEDIA_OVERRIDES.get(str(path), path)
    path = Path(path)
    if path.is_absolute():
        return str(path)
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'Video path escapes dataset root: {path}')
    return str(resolved)


def window(messages, videos, keep=3):
    count = sum(m['content'].count('<video>') for m in messages)
    drop = max(0, count - keep)
    output, remaining = [], drop
    for message in messages:
        value = dict(message)
        take = min(value['content'].count('<video>'), remaining)
        value['content'] = value['content'].replace('<video>', '', take)
        remaining -= take
        output.append(value)
    return output, videos[drop:count]


def jobs(args):
    steps, trajectories = load(args.step_file), load(args.traj_file)
    for i, row in enumerate(steps):
        row.setdefault('id', f'small-step-{i:06d}')
    for i, row in enumerate(trajectories):
        row.setdefault('id', f'small-traj-{i:06d}')
    if args.smoke:
        buckets = {}
        for row in steps:
            key = (row['source'], row['role'], subset(row),
                   verdict(row['messages'][-1]['content']) if row['role'] == 'critic' else 'planner')
            buckets.setdefault(key, row)
        steps = list(buckets.values())
        trajectories = [min((r for r in trajectories if r['source'] == source),
                            key=lambda r: sum(m['role'] == 'assistant' for m in r['messages']))
                        for source in sorted({r['source'] for r in trajectories})]
    selection = {'smoke': args.smoke, 'step_ids': [r['id'] for r in steps],
                 'trajectory_ids': [r['id'] for r in trajectories]}
    result = []
    for row in steps:
        result.append({'id': row['id'], 'unit': 'step', 'role': row['role'], 'source': row['source'],
                       'sub': subset(row), 'videos': row['videos'], 'context': row['messages'][:-1],
                       'gt_answer': row['messages'][-1]['content']})
    for row in trajectories:
        for i, message in enumerate(row['messages']):
            if message['role'] != 'assistant':
                continue
            context, videos = window(row['messages'][:i], row['videos'])
            result.append({'id': f"{row['id']}-turn-{i:04d}", 'unit': 'traj',
                           'traj_id': row['rollout_id'], 'turn_index': i,
                           'role': trajectory_role(row['messages'], i), 'source': row['source'],
                           'sub': subset(row, True), 'videos': videos, 'context': context,
                           'gt_answer': message['content']})
    for row in result:
        row['gt_subtask'] = subtask(row['gt_answer'])
        row['gt_verdict'] = verdict(row['gt_answer'])
        row['gt_reason'] = (block(row['gt_answer'], 'think') + ' ' + block(row['gt_answer'], 'answer')).strip()
    return result, selection


def post(args, chat, limit, judge=False):
    payload = {'model': args.model, 'messages': chat, 'max_tokens': limit, 'temperature': 0}
    if judge:
        payload['chat_template_kwargs'] = {'enable_thinking': False}
    token = os.environ.get('BENCH_API_KEY')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    for attempt in range(3):
        try:
            request = urllib.request.Request(args.api, json.dumps(payload).encode(), headers)
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                value = json.load(response)
            choice = value['choices'][0]
            content = choice['message'].get('content')
            if not isinstance(content, str) or not content.strip():
                raise ValueError('Model returned empty content')
            if judge and choice.get('finish_reason') == 'length':
                raise ValueError(f'Generation reached max_tokens={limit}; increase the token limit')
            return content, {'finish_reason': choice.get('finish_reason'),
                             'truncated': choice.get('finish_reason') == 'length', 'usage': value.get('usage')}
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors='replace')[:1500]
            if error.code < 500 or attempt == 2:
                raise RuntimeError(f'HTTP {error.code}: {detail}') from error
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))


def collect_one(row, args):
    context = [dict(m) for m in row['context']]
    for message in reversed(context):
        if message['role'] == 'user':
            message['content'] += FMT_CRIT if row['role'] == 'critic' else FMT_PLAN
            break
    videos = [resolve_video(p, args.root) for p in row['videos']]
    chat = to_chat(context, videos, 16 if row['unit'] == 'traj' else 6,
                   5.0 if row['unit'] == 'traj' else None)
    out, response = post(args, chat, args.max_tokens)
    return {**{k: v for k, v in row.items() if k != 'context'}, 'out': out, 'response': response}


def judge_one(row, args):
    image_list = []
    for path in row['videos']:
        image_list.extend(image_parts(resolve_video(path, args.root), 6, None))
    if row['role'] == 'critic':
        prompt = (f"【标准结论】该步执行: {row['gt_verdict']} (ok=成功/fail=失败)\n"
                  f"【标准原因】{row['gt_reason'][:600]}\n【模型回答】{row['out'][:800]}\n"
                  '请判断:1) 模型对该步成败的结论是否与标准一致; '
                  '2) 模型给出的原因是否与标准原因一致(可参考视频是否真的如此)。'
                  '只输出 JSON: {"verdict":"YES/NO","reason":"YES/NO"}')
        expected = {'verdict': {'YES', 'NO'}, 'reason': {'YES', 'NO'}}
    else:
        prompt = (f"【标准下一步子任务】{row['gt_subtask']}\n【模型回答】{row['out'][:800]}\n"
                  '请分别判断模型给出的下一步:1) 动作类型是否与标准一致'
                  '(如 抓取/放置/导航/开/关 等大类); 2) 操作的目标对象/目的地是否与标准一致。'
                  '目标无法判断时 target 填 NA。'
                  '只输出 JSON: {"action":"YES/NO","target":"YES/NO/NA"}')
        expected = {'action': {'YES', 'NO'}, 'target': {'YES', 'NO', 'NA'}}
    chat = [{'role': 'system', 'content': JUDGE_SYS}, {'role': 'user', 'content':
            image_list[:8] + [{'type': 'text', 'text': prompt}]}]
    attempts = []
    for attempt in range(3):
        out, response = post(args, chat, args.judge_max_tokens, judge=True)
        attempts.append({'out': out, 'response': response})
        match = re.search(r'\{.*\}', out, re.S)
        try:
            judgment = json.loads(match.group()) if match else {}
        except json.JSONDecodeError:
            judgment = {}
        if isinstance(judgment, dict) and all(
                isinstance(judgment.get(key), str) and judgment[key] in values
                for key, values in expected.items()):
            return {**row, 'judge': judgment, 'judge_response': response,
                    'judge_attempts': attempts, 'judge_format_retries': attempt}
        # Preserve the original criteria and media. Ask the judge to produce its
        # own enum values; never coerce prose into a score or infer a verdict.
        schema = {key: '/'.join(sorted(values)) for key, values in expected.items()}
        chat = chat + [{'role': 'assistant', 'content': out}, {'role': 'user', 'content':
            '输出格式不合要求。保持原始评判标准，只输出包含以下字段的 JSON；'
            '每个字段必须为列出的一个枚举值，不得写解释文本：' +
            json.dumps(schema, ensure_ascii=False)}]
    raise ValueError(f'Invalid judge result for {row["id"]} after 3 attempts: {attempts}')


def aggregate(rows, expected_jobs):
    by_id = {r['id']: r for r in rows}
    expected = {r['id']: r for r in expected_jobs}
    if len(by_id) != len(rows) or set(by_id) != set(expected):
        raise ValueError(f'Incomplete/duplicate results: expected {len(expected)}, received {len(rows)}')
    cells, trajectories = collections.defaultdict(list), collections.defaultdict(list)
    for key, expected_row in expected.items():
        row = by_id[key]
        if any(row.get(k) != v for k, v in expected_row.items() if k != 'context'):
            raise ValueError(f'Result does not match current benchmark: {key}')
        judge = row['judge']
        required = ['verdict', 'reason'] if row['role'] == 'critic' else ['action', 'target']
        if 'error' in row or any(k not in judge for k in required):
            raise ValueError(f'Missing/invalid judgment: {key}')
        allowed = {'verdict': {'YES', 'NO'}, 'reason': {'YES', 'NO'},
                   'action': {'YES', 'NO'}, 'target': {'YES', 'NO', 'NA'}}
        if any(judge[k] not in allowed[k] for k in required):
            raise ValueError(f'Invalid judgment value: {key}')
        if row['unit'] == 'step':
            base = (row['source'], row['sub'])
            if row['role'] == 'planner':
                action = judge['action'] == 'YES'
                cells[base + ('subtask',)].append(action)
                cells[base + ('fine',)].append(action and judge['target'] == 'YES')
            else:
                cells[base + ('judge',)].append(judge['verdict'] == 'YES')
                if row['gt_verdict'] == 'fail':
                    cells[base + ('cause_failure_only',)].append(judge['reason'] == 'YES')
        elif row['role'] == 'planner':
            trajectories[(row['source'], row['traj_id'])].append((row['turn_index'], judge['action'] == 'YES'))
    for (source, _), turns in trajectories.items():
        correctness = [correct for _, correct in sorted(turns)]
        cells[(source, 'all', 'trajectory_success')].append(all(correctness))
        cells[(source, 'all', 'trajectory_mean_progress')].append(sum(correctness) / len(correctness))
    return {'protocol': PROTOCOL, 'complete': True, 'decision_count': len(rows),
            'truncated_prediction_count': sum(r.get('response', {}).get('truncated', False) for r in rows),
            'trajectory_count': len(trajectories), 'metrics': [
                {'source': source, 'subset': sub, 'metric': metric, 'n': len(values),
                 'sum': sum(values), 'percent': 100 * sum(values) / len(values)}
                for (source, sub, metric), values in sorted(cells.items())]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['collect', 'judge', 'aggregate'])
    parser.add_argument('--root', type=Path, required=True, help='Extracted DiagBench package root')
    parser.add_argument('--step-file', type=Path)
    parser.add_argument('--traj-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--api', default='http://127.0.0.1:18409/v1/chat/completions')
    parser.add_argument('--model')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--max-tokens', type=int, default=2048)
    parser.add_argument('--judge-max-tokens', type=int, default=256)
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--smoke', action='store_true', help='One step per source/role/subset/verdict bucket plus two complete short trajectories')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--media-overrides', type=Path, help='Optional local recovery map used before packaging')
    args = parser.parse_args(argv)
    if args.workers < 1 or min(args.max_tokens, args.judge_max_tokens, args.timeout) <= 0:
        parser.error('Workers, token budgets and timeout must be positive')
    if args.stage != 'aggregate' and not args.model:
        parser.error('--model is required for collect/judge')
    monitor = Monitor(args.output, 'smoke' if args.smoke else 'formal')
    try:
        run(args, monitor)
    except BaseException:
        monitor.status(args.stage, 'failed')
        raise
    finally:
        monitor.close()


def run(args, monitor):
    MEDIA_OVERRIDES.clear()
    if args.media_overrides:
        MEDIA_OVERRIDES.update(json.loads(args.media_overrides.read_text()))
    args.root = args.root.resolve()
    args.step_file = args.step_file or args.root / 'data/bench_small_step.jsonl'
    args.traj_file = args.traj_file or args.root / 'data/bench_small_traj.jsonl'
    args.output.mkdir(parents=True, exist_ok=True)
    expected, selection = jobs(args)
    if not expected or len({r['id'] for r in expected}) != len(expected):
        raise ValueError('Empty selection or duplicate benchmark IDs')
    monitor.status('data', 'complete')
    monitor.scalars({'data/decisions': len(expected)}, 0)
    monitor.status(args.stage, 'running')
    if args.stage == 'aggregate':
        metadata = {s: json.loads((args.output / f'{s}_metadata.json').read_text())
                    for s in ('collect', 'judge')}
        identity = {'protocol': PROTOCOL, 'smoke': args.smoke,
                    'step_sha256': digest(args.step_file), 'traj_sha256': digest(args.traj_file),
                    'media_manifest_sha256': digest(args.root / 'media_manifest.jsonl'),
                    'expected_decisions': len(expected)}
        if any(meta.get(k) != v for meta in metadata.values() for k, v in identity.items()):
            raise ValueError('Run metadata does not match current benchmark selection')
        if metadata['judge'].get('predictions_sha256') != digest(args.output / 'predictions.jsonl'):
            raise ValueError('Predictions changed after judging')
        predictions = load(args.output / 'predictions.jsonl')
        prediction_map = {r['id']: r for r in predictions}
        if len(prediction_map) != len(predictions) or set(prediction_map) != {r['id'] for r in expected}:
            raise ValueError('Incomplete or duplicate predictions')
        judgments = load(args.output / 'judged.jsonl')
        for row in judgments:
            original = prediction_map.get(row['id'], {})
            if row.get('out') != original.get('out') or row.get('response') != original.get('response'):
                raise ValueError('Judgment does not match the collected prediction')
        summary = aggregate(judgments, expected)
        summary['models'] = {s: meta['model'] for s, meta in metadata.items()}
        save(args.output / 'summary.json', summary)
        monitor.scalars({f"scores/{r['source']}/{r['subset']}/{r['metric']}": r['percent']
                         for r in summary['metrics']}, len(expected))
        monitor.status('aggregate', 'complete')
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    metadata = {'protocol': PROTOCOL, 'stage': args.stage, 'model': args.model,
                'api': args.api, 'smoke': args.smoke,
                'step_sha256': digest(args.step_file), 'traj_sha256': digest(args.traj_file),
                'max_tokens': args.max_tokens, 'judge_max_tokens': args.judge_max_tokens,
                'media_manifest_sha256': digest(args.root / 'media_manifest.jsonl'),
                'media_overrides': MEDIA_OVERRIDES,
                'expected_decisions': len(expected), 'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    path = args.output / ('predictions.jsonl' if args.stage == 'collect' else 'judged.jsonl')
    metadata_path = args.output / f'{args.stage}_metadata.json'
    if args.stage == 'judge':
        metadata['predictions_sha256'] = digest(args.output / 'predictions.jsonl')
    if path.exists() and not args.resume:
        raise ValueError(f'{path} already exists; use --resume or a new output directory')
    if args.resume and path.exists() and not metadata_path.exists():
        raise ValueError('Cannot resume results without their original metadata')
    if args.resume and metadata_path.exists():
        old = json.loads(metadata_path.read_text())
        if any(old.get(k) != v for k, v in metadata.items() if k != 'timestamp_utc'):
            raise ValueError('Resume settings differ from the recorded run')
    inputs = expected if args.stage == 'collect' else load(args.output / 'predictions.jsonl')
    if args.stage == 'judge' and (len(inputs) != len(expected) or {r['id'] for r in inputs} != {r['id'] for r in expected} or any('error' in r for r in inputs)):
        raise ValueError('Collect must finish without errors before judging')
    by_id = {r['id']: r for r in expected}
    for row in inputs:
        if any(row.get(k) != v for k, v in by_id[row['id']].items() if k != 'context'):
            raise ValueError(f"Input does not match current benchmark: {row['id']}")
    previous = load(path) if args.resume and path.exists() else []
    completed = {r['id']: r for r in previous if 'error' not in r}
    if len(completed) != len([r for r in previous if 'error' not in r]):
        raise ValueError('Duplicate successful IDs in output')
    if not set(completed).issubset({r['id'] for r in inputs}):
        raise ValueError('Resume output contains unknown IDs')
    for row in completed.values():
        if any(row.get(k) != v for k, v in by_id[row['id']].items() if k != 'context'):
            raise ValueError('Resume results do not match current benchmark')
    save(metadata_path, metadata)
    save(args.output / 'selection.json', selection)
    with path.open('w', encoding='utf-8') as stream:
        for row in completed.values():
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    todo = [r for r in inputs if r['id'] not in completed]
    function = collect_one if args.stage == 'collect' else judge_one
    def run(row):
        try:
            return function(row, args)
        except Exception as error:
            return {**{k: v for k, v in row.items() if k != 'context'}, 'error': f'{type(error).__name__}: {error}'}
    failures = 0
    successful = len(completed)
    monitor.scalars({f'{args.stage}/completed': successful,
                     f'{args.stage}/progress': successful / len(expected)}, successful)
    print(f'{args.stage}: {len(completed)} already complete, {len(todo)} pending, smoke={args.smoke}', flush=True)
    with path.open('a', encoding='utf-8') as stream, concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, row in enumerate(executor.map(run, todo), 1):
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            failures += 'error' in row
            successful += 'error' not in row
            monitor.scalars({f'{args.stage}/completed': successful,
                             f'{args.stage}/progress': successful / len(expected),
                             f'{args.stage}/errors': failures,
                             f'{args.stage}/last_truncated': row.get('response', {}).get('truncated', False)},
                            len(completed) + i)
            print(f"{i}/{len(todo)} {row['id']} {'ERROR ' + row['error'] if 'error' in row else 'OK'}", flush=True)
    if failures:
        raise SystemExit(f'{failures} requests failed; fix errors and repeat with --resume. No complete score produced.')
    if args.stage == 'judge':
        save(args.output / 'summary.json', aggregate(load(path), expected))
    monitor.status(args.stage, 'complete')


if __name__ == '__main__':
    main()
