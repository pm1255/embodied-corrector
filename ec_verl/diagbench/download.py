"""Fetch and verify the pinned public DiagBench release before extraction."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import zipfile

REVISION = '93a7e12e7e89459c16269d2ffc8416ab0e1be338'
ARCHIVE = 'EmbodiedDiag-Bench-small-20261024.zip'
SHA256 = 'fa4c95649fb44b703aa545c773a96a8d7482eb4e65083befb4405bb4d1d6e31f'
SIZE = 5170502918
URL = f'https://modelscope.cn/api/v1/datasets/KagaKouko/diagbench/repo?Revision={REVISION}&FilePath={ARCHIVE}'


def verify(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    if path.stat().st_size != SIZE or h.hexdigest() != SHA256:
        raise ValueError(f'Archive size/SHA-256 mismatch: {path}')


def safe_extract(archive, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            target = (destination / info.filename).resolve()
            if (not target.is_relative_to(destination) or Path(info.filename).is_absolute()
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError(f'Unsafe archive member: {info.filename}')
        z.extractall(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/diagbench'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / ARCHIVE
    if not archive.exists():
        partial = archive.with_suffix('.zip.part')
        subprocess.run(['curl', '--fail', '--location', '--retry', '5', '--continue-at', '-',
                        '--output', str(partial), URL], check=True)
        verify(partial)
        partial.replace(archive)
    else:
        verify(archive)
    safe_extract(archive, args.output)
    root = args.output / ARCHIVE.removesuffix('.zip')
    (args.output / 'provenance.json').write_text(json.dumps({
        'dataset': 'KagaKouko/diagbench', 'revision': REVISION, 'archive': ARCHIVE,
        'bytes': SIZE, 'sha256': SHA256, 'source': URL, 'root': str(root.resolve())}, indent=2) + '\n')
    print(root.resolve())


if __name__ == '__main__':
    main()
