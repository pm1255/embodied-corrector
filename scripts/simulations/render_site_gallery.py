"""Render the twelve verified recovery episodes into the homepage."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
catalog = json.loads((ROOT / 'docs/assets/recovery/catalog.json').read_text())
assert len(catalog) == 12 and len({x['id'] for x in catalog}) == 12
assert all(x['success'] and x['kind'] == 'gpt_proxy' for x in catalog)
groups, directory = [], []
for suite, anchor in [('LIBERO-PRO', 'libero-videos'), ('RoboCasa365', 'robocasa-videos')]:
    items = [x for x in catalog if x['suite'] == suite]
    if not items:
        continue
    directory.append(f'<a href="#{anchor}">{suite} <strong>{len(items)}</strong></a>')
    cards = []
    for item in items:
        identity, title = escape(item['id'], quote=True), escape(item['title'])
        record = json.loads((ROOT / 'docs/assets/recovery' / (item['id'] + '.json')).read_text())
        assert record['result']['success'] and record['events'][-1]['official_success']
        seed, base = record['manifest']['seed'], 'assets/recovery/' + identity
        cards.append(f'''          <article class="episode-card" id="case-{identity}" data-playback-speed="1" data-lead-seconds="0">
            <div class="episode-title"><span>{catalog.index(item)+1:02d}</span><h4>{title}</h4></div>
            <video id="video-{identity}" controls playsinline preload="none" data-poster="{base}-poster.jpg?v=recovery-12" aria-label="{suite} · {title} · Seed {seed}" src="{base}.mp4?v=recovery-12"></video>
            <div class="episode-copy"><p class="episode-meta">{escape(item['challenge'])} · Seed {seed} · 1×</p><div class="episode-actions"><span class="simulation-outcome">Recovery succeeded</span><button type="button" class="episode-record-button" data-expand="{identity}">Expand video ↗</button><button type="button" class="episode-record-button" data-record="{identity}" data-record-path="{base}.json" aria-haspopup="dialog">Execution record ↗</button></div></div>
          </article>''')
    groups.append(f'''      <section class="episode-suite" id="{anchor}" aria-labelledby="{anchor}-title">
        <div class="episode-suite-heading"><h3 id="{anchor}-title">{suite} <span>{len(items)} videos</span></h3><a href="#simulations">Back to directory ↑</a></div>
        <div class="episode-grid">
{chr(10).join(cards)}
        </div>
      </section>''')

block = '''    <!-- BEGIN SIMULATION GALLERY -->
    <section id="simulations" class="section container simulation-section" aria-labelledby="simulations-title" lang="en">
      <div class="section-heading"><p class="eyebrow">FAILURE → DIAGNOSIS → RECOVERY</p><h2 id="simulations-title">12 selected recovery episodes</h2><p>See the failure, follow Judge → Cause → Sub → Fine, and watch the task reach a verified successful outcome. Expand a video to read the complete brain output.</p></div>
      <nav class="episode-directory" aria-label="Video episode directory">''' + ''.join(directory) + '''<span>Continuous footage · Original speed · First-frame covers</span></nav>
      <p class="simulation-scope">These selected demonstrations use a GPT proxy with simulator-state-assisted analytical control, not the trained RynnBrain model. They are 12 independent episodes across task and seed variations, not 12 distinct tasks or an estimate of benchmark success rate.</p>
''' + '\n'.join(groups) + '''
      <div class="simulation-footer"><p>Every selected episode contains an observed failure, recorded corrective decisions and a positive final environment success check. The complete episode is retained without a reset or omitted actions.</p><div><a class="text-link" href="https://github.com/pm1255/embodied-corrector/blob/main/guides/selected_recoveries.md">Episode provenance and verification ↗</a><a class="text-link" href="assets/recovery/execution-records.zip" download>Download execution records ↓</a></div></div>
    </section>
    <dialog id="episode-dialog" aria-labelledby="episode-dialog-title">
      <form method="dialog"><button class="dialog-close" type="submit" aria-label="Close execution record">×</button></form>
      <h2 id="episode-dialog-title">Execution record</h2><p id="episode-dialog-description"></p>
      <a class="text-link" id="episode-original-record" href="assets/recovery/catalog.json">English JSON record ↗</a>
      <div id="simulation-events" aria-live="polite"></div>
    </dialog>
    <dialog id="video-dialog" aria-labelledby="video-dialog-title">
      <form method="dialog"><button class="dialog-close" type="submit" aria-label="Close expanded video">×</button></form>
      <h2 id="video-dialog-title">Recovery episode</h2>
      <video id="expanded-video" controls playsinline preload="none" aria-label="Expanded recovery episode"></video>
    </dialog>
    <!-- END SIMULATION GALLERY -->'''
page = ROOT / 'docs/index.html'
source = page.read_text()
start = source.index('    <!-- BEGIN SIMULATION GALLERY -->')
end = source.index('    <!-- END SIMULATION GALLERY -->') + len('    <!-- END SIMULATION GALLERY -->')
page.write_text((source[:start] + block + source[end:]).replace('Videos · 50', 'Videos · 12'))
print(f'Rendered {len(catalog)} verified recovery cards into {page}')
