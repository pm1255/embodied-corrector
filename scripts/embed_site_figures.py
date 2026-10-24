"""Bundle the six paper figures into HTML so dropped asset requests cannot hide them.

Run after replacing a figure asset. data-source retains the editable source path;
the video-gallery renderer preserves these tags when regenerating its own section.
"""
import base64
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / 'docs'
page = DOCS / 'index.html'
count = 0


def embed(match):
    global count
    tag = match.group(0)
    if 'data-fallback=' not in tag:
        return tag
    source = re.search(r' data-source="([^"]+)"', tag)
    source = source.group(1) if source else re.search(r' src="([^"]+)"', tag).group(1)
    assert source.startswith(('assets/figures/', 'assets/cases/')) and source.endswith('.webp')
    payload = base64.b64encode((DOCS / source).read_bytes()).decode('ascii')
    tag = re.sub(r' src="[^"]+"', ' src="data:image/webp;base64,' + payload + '"', tag)
    if 'data-source=' not in tag:
        tag = tag.replace(' data-fallback=', f' data-source="{source}" data-fallback=')
    count += 1
    return tag


html = re.sub(r'<img\b[^>]*>', embed, page.read_text())
assert count == 6, f'Expected six manuscript figures, found {count}'
page.write_text(html)
print(f'Embedded {count} original figures in {len(html.encode()):,} bytes of HTML')
