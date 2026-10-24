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
        kind = '脚本控制' if item['kind'] == 'scripted' else 'GPT 代理交互'
        speed = item.get('playback_speed', 2)
        outcome = '官方任务完成' if item['success'] else '官方任务未完成'
        status = '' if item['success'] else ' incomplete'
        base = 'assets/simulations/' + identity
        cards.append(f'''          <article class="episode-card" id="case-{identity}" data-playback-speed="{speed}" data-lead-seconds="{item.get('lead_seconds', 0)}">
            <div class="episode-title"><span>{index:02d}</span><h4>{title}</h4></div>
            <video id="video-{identity}" controls playsinline preload="none" poster="{base}-poster.jpg?v=first-frame-2" aria-label="{suite} · {title} · 种子 {seed}" src="{base}.mp4"></video>
            <div class="episode-copy"><p class="episode-meta">{kind} · 种子 {seed} · {speed}×</p><div class="episode-actions"><span class="simulation-outcome{status}">{outcome}</span><button type="button" class="episode-record-button" data-record="{identity}" aria-haspopup="dialog">执行记录 ↗</button></div></div>
          </article>''')
    groups.append(f'''      <section class="episode-suite" id="{anchor}" aria-labelledby="{anchor}-title">
        <div class="episode-suite-heading"><h3 id="{anchor}-title">{suite} <span>{len(items)} 个视频</span></h3><a href="#simulations">回到案例目录 ↑</a></div>
        <div class="episode-grid">
{chr(10).join(cards)}
        </div>
      </section>''')

block = '''    <!-- BEGIN SIMULATION GALLERY -->
    <section id="simulations" class="section container simulation-section" aria-labelledby="simulations-title" lang="zh-CN">
      <div class="section-heading"><p class="eyebrow">CONTINUOUS SIMULATION / 连续仿真</p><h2 id="simulations-title">50 个连续视频案例</h2><p>全部案例直接展示在下方，点击视频即可播放；静止封面取自视频第一帧。</p></div>
      <nav class="episode-directory" aria-label="视频案例目录"><a href="#libero-videos">LIBERO-PRO <strong>20</strong></a><a href="#robocasa-videos">RoboCasa365 <strong>30</strong></a><span>完整回合 · 保留成功与未完成结果</span></nav>
      <p class="simulation-scope">6 个 GPT 代理交互案例与 44 个脚本控制回合，均使用仿真状态辅助定位。这些是独立回合，不是 50 种任务，也不代表训练模型的基准成绩。</p>
''' + '\n'.join(groups) + '''
      <div class="simulation-footer"><p>LIBERO-PRO 官方完成 9 / 20，RoboCasa365 官方完成 0 / 30。每个案例保留任务、种子、连续录像及原始动作记录。</p><div><a class="text-link" href="https://github.com/pm1255/embodied-corrector/blob/main/guides/simulation_report_zh.md">全部尝试与运行说明 ↗</a><a class="text-link" href="assets/simulations/execution-records.zip" download>下载动作与日志 ↓</a></div></div>
    </section>
    <dialog id="episode-dialog" aria-labelledby="episode-dialog-title">
      <form method="dialog"><button class="dialog-close" type="submit" aria-label="关闭执行记录">×</button></form>
      <h2 id="episode-dialog-title">执行记录</h2><p id="episode-dialog-description"></p>
      <a class="text-link" id="episode-original-record" href="assets/simulations/libero-articulation-r1.json">原始 JSON 记录 ↗</a>
      <div id="simulation-events" aria-live="polite"></div>
    </dialog>
    <!-- END SIMULATION GALLERY -->'''
page = ROOT / 'docs/index.html'
source = page.read_text()
start = source.index('    <!-- BEGIN SIMULATION GALLERY -->')
end = source.index('    <!-- END SIMULATION GALLERY -->') + len('    <!-- END SIMULATION GALLERY -->')
page.write_text(source[:start] + block + source[end:])
print(f'Rendered {len(catalog)} video cards into {page}')
