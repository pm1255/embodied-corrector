"""Render every catalog episode into the homepage, including without JavaScript."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
catalog = json.loads((ROOT / 'docs/assets/simulations/catalog.json').read_text())
groups = []
for suite, anchor in [('LIBERO-PRO', 'libero-videos'), ('RoboCasa365', 'robocasa-videos')]:
    items = [item for item in catalog if item['suite'] == suite]
    cards = []
    for index, item in enumerate(items, 1):
        identity = escape(item['id'], quote=True)
        title = escape(item['title'])
        record = json.loads((ROOT / ('docs/assets/simulations/' + item['id'] + '.json')).read_text())
        seed = record['manifest']['seed']
        kind = 'Scripted control' if item['kind'] == 'scripted' else 'GPT proxy'
        speed = item.get('playback_speed', 2)
        outcome = 'Task completed' if item['success'] else 'Task incomplete'
        status = '' if item['success'] else ' incomplete'
        base = 'assets/simulations/' + identity
        cards.append(f'''          <article class="episode-card" id="case-{identity}" data-playback-speed="{speed}" data-lead-seconds="{item.get('lead_seconds', 0)}">
            <div class="episode-title"><span>{index:02d}</span><h4>{title}</h4></div>
            <video id="video-{identity}" controls playsinline preload="none" data-poster="{base}-poster.jpg?v=english-6" aria-label="{suite} · {title} · Seed {seed}" src="{base}.mp4?v=english-6"></video>
            <div class="episode-copy"><p class="episode-meta">{kind} · Seed {seed} · {speed}×</p><div class="episode-actions"><span class="simulation-outcome{status}">{outcome}</span><button type="button" class="episode-record-button" data-record="{identity}" aria-haspopup="dialog">Execution record ↗</button></div></div>
          </article>''')
    groups.append(f'''      <section class="episode-suite" id="{anchor}" aria-labelledby="{anchor}-title">
        <div class="episode-suite-heading"><h3 id="{anchor}-title">{suite} <span>{len(items)} videos</span></h3><a href="#simulations">Back to directory ↑</a></div>
        <div class="episode-grid">
{chr(10).join(cards)}
        </div>
      </section>''')

block = '''    <!-- BEGIN SIMULATION GALLERY -->
    <section id="simulations" class="section container simulation-section" aria-labelledby="simulations-title" lang="en">
      <div class="section-heading"><p class="eyebrow">CONTINUOUS SIMULATION</p><h2 id="simulations-title">50 continuous video episodes</h2><p>All 50 episodes are shown below. Select any video to play; every poster is its own first frame.</p></div>
      <nav class="episode-directory" aria-label="Video episode directory"><a href="#libero-videos">LIBERO-PRO <strong>20</strong></a><a href="#robocasa-videos">RoboCasa365 <strong>30</strong></a><span>Full episodes · Completed and incomplete outcomes</span></nav>
      <p class="simulation-scope">Six GPT proxy interactions and 44 scripted episodes use simulator state for localization. These are separate episodes, not 50 distinct tasks or benchmark scores from the trained model.</p>
''' + '\n'.join(groups) + '''
      <div class="simulation-footer"><p>Official task completion: LIBERO-PRO 9 / 20; RoboCasa365 0 / 30. Each episode retains its task, seed, continuous recording, and execution record.</p><div><a class="text-link" href="https://github.com/pm1255/embodied-corrector/blob/main/guides/simulation_report.md">Episode provenance and running instructions ↗</a><a class="text-link" href="assets/simulations/english-execution-records.zip" download>Download English execution records ↓</a></div></div>
    </section>
    <dialog id="episode-dialog" aria-labelledby="episode-dialog-title">
      <form method="dialog"><button class="dialog-close" type="submit" aria-label="Close execution record">×</button></form>
      <h2 id="episode-dialog-title">Execution record</h2><p id="episode-dialog-description"></p>
      <a class="text-link" id="episode-original-record" href="assets/simulations/records-en/libero-articulation-r1.json">English JSON record ↗</a>
      <div id="simulation-events" aria-live="polite"></div>
    </dialog>
    <!-- END SIMULATION GALLERY -->'''
page = ROOT / 'docs/index.html'
source = page.read_text()
start = source.index('    <!-- BEGIN SIMULATION GALLERY -->')
end = source.index('    <!-- END SIMULATION GALLERY -->') + len('    <!-- END SIMULATION GALLERY -->')
page.write_text(source[:start] + block + source[end:])
print(f'Rendered {len(catalog)} video cards into {page}')
