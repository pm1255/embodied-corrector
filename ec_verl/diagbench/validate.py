#!/usr/bin/env python3
"""Check annotation structure, complete video coverage, and SHA-256 checksums."""
import argparse
import collections
import concurrent.futures
import json
from pathlib import Path

from .evaluate import digest, load, save, trajectory_role


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--hash', action='store_true', help='Also hash every video; reads about 5 GB')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    info = json.loads((root / 'dataset_info.json').read_text())
    all_ids, all_videos = set(), set()
    counts, role_counts = {}, collections.Counter()
    for unit, expected in [('step', info['step_rows']), ('traj', info['trajectory_rows'])]:
        rows = load(root / f'data/bench_small_{unit}.jsonl')
        if len(rows) != expected:
            raise ValueError(f'{unit}: expected {expected} rows, found {len(rows)}')
        counts[unit] = len(rows)
        for row in rows:
            if row['id'] in all_ids:
                raise ValueError(f'Duplicate ID: {row["id"]}')
            all_ids.add(row['id'])
            placeholders = sum(m['content'].count('<video>') for m in row['messages'] if m['role'] == 'user')
            if placeholders != len(row['videos']):
                raise ValueError(f'Placeholder/video count differs: {row["id"]}')
            if row['messages'][-1]['role'] != 'assistant':
                raise ValueError(f'Missing reference answer: {row["id"]}')
            for path in row['videos']:
                file = (root / path).resolve()
                if Path(path).is_absolute() or not file.is_relative_to(root) or not file.is_file() or path.startswith('quarantine/'):
                    raise ValueError(f'Invalid/missing package video: {path}')
                all_videos.add(path)
            if unit == 'traj':
                for i, message in enumerate(row['messages']):
                    if message['role'] == 'assistant':
                        role = trajectory_role(row['messages'], i)
                        if row['assistant_roles'][str(i)] != role:
                            raise ValueError('Wrong trajectory role annotation')
                        role_counts[role] += 1
    media = load(root / 'media_manifest.jsonl')
    if len(media) != len({r['path'] for r in media}) or not all_videos.issubset({r['path'] for r in media if r['usable']}):
        raise ValueError('Media manifest has duplicates or missing/unusable files')
    exclusions = load(root / 'data/excluded_rows.jsonl')
    excluded_ids = {r['id'] for r in exclusions}
    if len(excluded_ids) != len(exclusions) or excluded_ids & all_ids:
        raise ValueError('Duplicate or overlapping exclusion IDs')
    original_ids, original_videos = set(), set()
    for unit, expected in [('step', info['original_step_rows']), ('traj', info['original_trajectory_rows'])]:
        rows = load(root / f'data/original/bench_small_{unit}.jsonl')
        if len(rows) != expected:
            raise ValueError('Wrong original annotation count')
        for row in rows:
            original_ids.add(row['id'])
            original_videos.update(row['videos'])
    if original_ids != all_ids | excluded_ids or original_videos != {r['path'] for r in media}:
        raise ValueError('Original/validated/exclusion/media partitions disagree')
    def check(row):
        path = root / row['path']
        if path.stat().st_size != row['bytes']:
            raise ValueError(f'File size mismatch: {row["path"]}')
        if args.hash and digest(path) != row['sha256']:
            raise ValueError(f'Hash mismatch: {row["path"]}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(check, media))
    if len(media) != info['video_count'] or sum(r['bytes'] for r in media) != info['video_bytes']:
        raise ValueError('Dataset info and media manifest disagree')
    report = {'valid': True, 'rows': counts, 'unique_videos': len(media),
              'video_bytes': sum(r['bytes'] for r in media), 'sha256_checked': args.hash,
              'quarantined_videos': info['quarantined_video_count'],
              'excluded_rows': len(exclusions),
              'trajectory_turns_by_role': dict(role_counts)}
    if args.report:
        save(args.report, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
