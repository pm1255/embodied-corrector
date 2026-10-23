'use strict';

// Reported manuscript values. Percentages are success/accuracy scores;
// differences are absolute percentage points, never relative percentages.
const diagnosis = [
  ['GPT-5.5',[72.7,39.4,52.8,39.8],[65.4,41.1,57.7,43.2]],
  ['RoboBrain2.5-4B',[26.1,21.2,31.5,12.2],[29.7,24.1,33.5,12.3]],
  ['RynnBrain-8B',[23.4,19.4,23.6,13.6],[31.6,25.8,31.9,18.7]],
  ['InternVL3-8B',[21.8,17.7,48.3,26.2],[32.1,26.8,40.1,17.9]],
  ['MiMo-Embodied-7B',[31.6,25.3,30.1,16.9],[35.6,27.6,22.2,19.3]],
  ['Qwen2.5-VL-7B',[23.2,19.3,52.5,23.8],[28.8,26,33.7,13.5]],
  ['Qwen3-VL-32B',[48.7,39.8,49.5,29.2],[42.9,34.3,54.6,33.2]],
  ['RynnBrain-SFT',[68.6,66.7,75.9,53.4],[62.5,61.6,80.7,51.4]],
  ['RynnBrain-OPD',[70,68,79,57],[65.4,61,80,54]],
  ['RynnBrain-GRPO',[73,69.2,74.2,51.5],[63.6,62.1,76.3,49.6]],
  ['RynnBrain-NEPO (ours)',[72.6,71.6,79.6,58.2],[64.9,63.7,81.2,54.6]],
  ['w/o Entropy Gate',[69.9,68.5,73.1,50.8],[63.1,61.4,75,48.7]]
];
const planning = [
  ['GPT-4o',64,54,68,46,52,54],['Claude-3.7-Sonnet',68,68,70,68,62,70],
  ['Llama-3.2-11B-Vision-Instruct',24,8,16,22,6,6],['InternVL3-8B',20,14,14,12,0,2],
  ['Ovis2-16B',26,16,24,12,16,4],['Qwen3-VL-32B',62,48,46,42,38,46],
  ['Gemma-3-12B-IT',32,26,38,22,20,12],['RoboBrain2.5-4B',22,16,34,6,16,24],
  ['MiMo-Embodied-7B',20,16,24,18,20,18],['RynnBrain-8B',30,28,44,26,24,28],
  ['RynnBrain-SFT',72,48,62,54,56,52],['RynnBrain-OPD',74,50,64,52,58,54],
  ['RynnBrain-GRPO',76,54,72,56,60,58],['RynnBrain-NEPO (ours)',78,56,74,60,64,62],
  ['w/o Entropy Gate',74,52,68,54,58,56]
];
const codeResults = [
  ['GPT-5.5 self-correction',76,44,80,60,61,58,72,77,58,66],
  ['RynnBrain-8B',72,36,72,56,48,46,64,62,45,49],
  ['RynnBrain-NEPO (ours)',76,40,80,64,69,67,82,85,56,70]
];
const vlaResults = [
  ['π₀',34.6,6.1,1.1],['π₀ + Corrector',24.4,11.3,6.3],
  ['π₀.₅',39.6,7.1,1.2],['π₀.₅ + Corrector',35.6,12.5,7.3]
];
const caseData = {
  prerequisite:{env:'LIBERO-PRO · L1 · PREREQUISITE',title:'Pick up before placing.',failure:'The program attempts placement with an empty gripper. The orange-juice carton is still on the floor.',correction:'Restore the omitted dependency: localize the carton, grasp it, verify attachment, and lift before transport.',outcome:'The regenerated program places the carton inside the basket; the environment confirms task completion.',caption:'Figure 7 · Twelve raw observations from the failed rollout followed by the corrected rollout. These are separate executions, not one continuous trajectory.',alt:'Twelve frames of an empty-gripper placement attempt followed by corrected carton pickup, lift, and basket placement.',figure:7},
  target:{env:'LIBERO-PRO · L2 · TARGET GROUNDING',title:'Ground the right bowl.',failure:'A dark non-bowl region enters the candidate set. Plausible arm motions act on the wrong referent.',correction:'Ground the plate, ramekin, and actual bowls. Apply the requested “not between” relation and reject invalid masks.',outcome:'The corrected program grasps the other black bowl and places it on the plate. The environment accepts the final relation.',caption:'Figure 8 · Twelve raw observations from a false-target execution followed by a corrected rollout with verified bowl placement.',alt:'Twelve simulated observations showing a false-target execution and corrected grounding and placement of the requested black bowl.',figure:8},
  avocado:{env:'ROBOCASA365 · R1 · FROZEN π₀.₅',title:'Align before closing.',failure:'The gripper stays too high and laterally offset. Repeated closure fails to enclose the avocado in the sink.',correction:'Use empty-grasp history and the current observation to adjust approach height and lateral alignment before closing and lifting.',outcome:'The avocado leaves the sink and reaches the plate. The low-level VLA remains frozen throughout.',caption:'Figure 9 · Twelve observations from one continuous rollout, spanning the failed grasp state and successful continuation after correction.',alt:'Twelve frames of a high and offset avocado grasp, followed by directional realignment and transfer from the sink to the plate.',figure:9},
  onion:{env:'ROBOCASA365 · R2 · FROZEN π₀.₅',title:'Reposition. Then grasp.',failure:'The gripper closes too late, knocks the onion, and leaves it in the sink. Repeating closure does not restore the grasp.',correction:'Coordinate forward, lateral, and downward repositioning before closure. Update the approach as visual evidence changes.',outcome:'The corrected approach encloses the onion and transfers it to the plate, satisfying the environment’s task predicate.',caption:'Figure 10 · Twelve observations from one continuous rollout, showing late closure and the subsequent coordinated recovery.',alt:'Twelve frames of late gripper closure with an onion remaining in the sink, followed by coordinated approach, grasp, and successful placement.',figure:10}
};

const panel = document.querySelector('#results-panel');
let currentResult = 'diagnosis';
let currentDomain = 1;
let currentPolicy = 'pi05';
const number = n => Number.isInteger(n) ? String(n) : n.toFixed(1);
const mean = a => a.reduce((s,n)=>s+n,0)/a.length;
function table(headers, rows, note){
  return `<details class="data-table"><summary>View exact values and all compared models</summary><div class="table-scroll" role="region" aria-label="Detailed result values" tabindex="0"><table><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr class="${String(r[0]).includes('ours')||String(r[0]).includes('+ Corrector')?'highlight':''}">${r.map((c,i)=>i===0?`<th scope="row">${c}</th>`:`<td>${typeof c==='number'?number(c):c}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="table-caption">${note}</p></details>`;
}
function legend(series){return `<div class="legend">${series.map(s=>`<span><i class="${s.class||''}" aria-hidden="true"></i>${s.name}</span>`).join('')}</div>`;}
function chart(labels,series,max=100,deltas=[]){
  const description=labels.map((label,i)=>`${label}: ${series.map(s=>`${s.name} ${number(s.values[i])}%`).join(', ')}`).join('; ');
  return `<div class="chart-meta"><span>Success / accuracy (%)</span><span>Scale: 0–${max}% · higher is better</span></div><div role="img" aria-label="${description}"><div class="bar-chart ${labels.length>4?'many-bars':''}" style="--groups:${labels.length}" aria-hidden="true">${labels.map((_,i)=>`<div class="bar-group">${series.map(s=>`<div class="chart-bar ${s.class||''}" style="--bar-height:${s.values[i]/max*100}%"><span class="bar-value">${number(s.values[i])}</span></div>`).join('')}</div>`).join('')}</div><div class="chart-labels" style="--groups:${labels.length}" aria-hidden="true">${labels.map((l,i)=>`<span>${l}${deltas[i]?`<small>${deltas[i]}</small>`:''}</span>`).join('')}</div></div>`;
}
function header(kicker,title,text,source,page){return `<div class="result-header"><div><p class="small-label">${kicker}</p><h3>${title}</h3><p>${text}</p></div><a class="source-pill" href="assets/paper.pdf#page=${page}" target="_blank" rel="noopener">${source} ↗</a></div>`;}
function renderResults(){
  let html='';
  if(currentResult==='diagnosis'){
    const base=diagnosis[2][currentDomain],ours=diagnosis[10][currentDomain];
    const order=[2,3,0,1];
    const series=[{name:'RynnBrain-8B',values:order.map(i=>base[i])},{name:'Embodied-Corrector (NEPO)',class:'ours',values:order.map(i=>ours[i])}];
    html=header('EMBODIEDDIAG-BENCH','From outcome recognition to usable correction.','Held-out failures evaluate outcome judgment, cause diagnosis, subtask selection, and fine-grained planning.','Table 1',6)+
      `<div class="result-controls">${legend(series)}<label class="result-select">Task domain <select id="domain-select"><option value="1" ${currentDomain===1?'selected':''}>Navigation</option><option value="2" ${currentDomain===2?'selected':''}>Operation</option></select></label></div>`+
      chart(['Judge','Cause','Sub','Fine'],series)+
      `<div class="result-takeaway"><strong>${number(ours[2])}% Judge · ${number(ours[3])}% Cause.</strong> Gains extend from recognizing the outcome to identifying why it happened and deciding how to recover.</div><p class="result-caveat">Embodied-Corrector is the RynnBrain-NEPO checkpoint in the manuscript. Source trajectories and successful prefixes are held out from training.</p>`+
      table(['Model','Sub','Fine','Judge','Cause'],diagnosis.map(r=>[r[0],...r[currentDomain]]),`Table 1 · ${currentDomain===1?'Navigation':'Operation'} scores (%) · Column order follows the manuscript; the chart presents assessment before planning.`);
  } else if(currentResult==='planning'){
    const series=[{name:'RynnBrain-8B',values:planning[9].slice(1)},{name:'Embodied-Corrector (NEPO)',class:'ours',values:planning[13].slice(1)}];
    html=header('EB-ALFRED','Correction training transfers to ordinary planning.','Frozen checkpoints receive the same instruction, observation, action space, history, and step limit, with no explicit failure prompt or corrective Harness.','Table 2',7)+
      `<div class="result-controls">${legend(series)}</div>`+chart(['Base','Common','Complex','Visual','Spatial','Long'],series)+
      `<div class="result-takeaway"><strong>78% on Base · 74% on Complex · 64% on Spatial.</strong> The trained model improves over the base RynnBrain checkpoint on all six subsets.</div><p class="result-caveat">This is transfer to external planning tasks, not a claim of best performance on every subset. The full comparison includes stronger results from other models on Common, Visual, and Long.</p>`+
      table(['Model','Base','Common','Complex','Visual','Spatial','Long'],planning,'Table 2 · All entries are planning scores (%), reproduced from the manuscript.');
  } else if(currentResult==='code'){
    const summary=r=>[mean(r.slice(1,5)),mean(r.slice(5)),mean(r.slice(1))].map(x=>Math.round(x*10)/10);
    const series=[{name:'RynnBrain-8B',values:summary(codeResults[1])},{name:'GPT-5.5 self-correction',class:'other',values:summary(codeResults[0])},{name:'Embodied-Corrector (NEPO)',class:'ours',values:summary(codeResults[2])}];
    html=header('FIXED GPT-5.5 + ANALYTIC ROBOT FUNCTIONS','Better correction for the same code generator.','The planner, robot functions, perception module, and execution budget remain fixed. The VLA function is disabled; only the correction component changes.','Table 3',8)+
      `<div class="result-controls">${legend(series)}</div>`+chart(['OmniBehavior','LIBERO-PRO','All 10 conditions'],series)+
      `<div class="result-takeaway"><strong>55.0% → 68.9% macro-average success (+13.9 pp).</strong> Embodied-Corrector improves over the untrained RynnBrain corrective brain in all ten execution conditions.</div><p class="result-caveat">Chart values are unweighted averages derived from Table 3: four OmniBehavior conditions and six LIBERO-PRO conditions. Gains are measured against RynnBrain-8B, not GPT-5.5 self-correction; the latter averages 65.2%.</p>`+
      table(['Correction component','Rad.-Nav','Rad.-Op','Soda-Nav','Soda-Op','Obj.-P','Obj.-T','Goal-P','Goal-T','Spa.-P','Spa.-T'],codeResults,'Table 3 · Controlled correction comparison (%). The first four conditions are OmniBehavior; the remaining six are LIBERO-PRO. Earlier OpenVLA/π₀/π₀.₅ rows in the manuscript use external protocols and are not included in this controlled comparison.');
  } else {
    const idx=currentPolicy==='pi05'?2:0, name=currentPolicy==='pi05'?'π₀.₅':'π₀';
    const base=vlaResults[idx].slice(1),ours=vlaResults[idx+1].slice(1);
    const deltas=base.map((n,i)=>`${ours[i]-n>=0?'+':''}${(ours[i]-n).toFixed(1)} pp`);
    const series=[{name:`Frozen ${name}`,values:base},{name:`${name} + Embodied-Corrector`,class:'ours',values:ours}];
    html=header('ROBOCASA365 · FROZEN VLA','Reduce the burden of long, compositional instructions.','The execution library exposes only the frozen VLA. Correction produces short, state-conditioned subtasks; low-level policy parameters and the execution interface remain unchanged.','Figure 4',8)+
      `<div class="result-controls">${legend(series)}<label class="result-select">Policy <select id="policy-select"><option value="pi05" ${currentPolicy==='pi05'?'selected':''}>π₀.₅</option><option value="pi0" ${currentPolicy==='pi0'?'selected':''}>π₀</option></select></label></div>`+
      chart(['Atomic-Seen','Composite-Seen','Composite-Unseen'],series,50,deltas)+
      `<div class="result-takeaway"><strong>Composite-Unseen: ${number(base[2])}% → ${number(ours[2])}% (${deltas[2]}).</strong> Decomposition helps the frozen executor handle long-horizon dependencies.</div><p class="result-caveat"><strong>Atomic-task tradeoff:</strong> Atomic-Seen falls from ${number(base[0])}% to ${number(ours[0])}%. Reformulating already short instructions can introduce language-interface errors. The improvement is specific to composite task structure.</p>`+
      table(['Policy','Atomic-Seen','Composite-Seen','Composite-Unseen'],vlaResults,'Figure 4 · Task success (%). The frozen-VLA evaluation covers 18 atomic-seen, 16 composite-seen, and 16 composite-unseen tasks. Each brain-assisted condition uses 50 trials per task.');
  }
  panel.innerHTML=html;
  panel.setAttribute('aria-labelledby',`tab-${currentResult}`);
  document.querySelector('#domain-select')?.addEventListener('change',e=>{currentDomain=Number(e.target.value);renderResults();document.querySelector('#domain-select').focus();});
  document.querySelector('#policy-select')?.addEventListener('change',e=>{currentPolicy=e.target.value;renderResults();document.querySelector('#policy-select').focus();});
}
function renderCase(key){
  const c=caseData[key];
  const target=document.querySelector('#case-panel');
  target.setAttribute('aria-labelledby',`case-${key}`);
  target.innerHTML=`<figure class="case-media"><button class="figure-button" type="button" data-zoom="assets/cases/${key}.webp" data-caption="${c.caption}" aria-label="Enlarge ${key} recovery frames"><img src="assets/cases/${key}.webp" width="1310" height="980" loading="lazy" alt="${c.alt}"><span class="zoom-hint" aria-hidden="true">↗</span></button><figcaption>${c.caption}</figcaption></figure><div class="case-copy"><span class="small-label">${c.env}</span><h3>${c.title}</h3><div class="case-step"><strong>FAILED EXECUTION</strong><p>${c.failure}</p></div><div class="case-step"><strong>GROUNDED CORRECTION</strong><p>${c.correction}</p></div><div class="case-step"><strong>VERIFIED OUTCOME</strong><p>${c.outcome}</p></div><span class="case-verification">Environment-verified · Simulation</span></div>`;
}
function setupTabs(selector,callback){
  const list=document.querySelector(selector),buttons=[...list.querySelectorAll('[role="tab"]')];
  const select=button=>{buttons.forEach(b=>{b.setAttribute('aria-selected',String(b===button));b.tabIndex=b===button?0:-1;});callback(button);};
  buttons.forEach((button,index)=>{
    button.addEventListener('click',()=>select(button));
    button.addEventListener('keydown',event=>{
      let next;
      if(event.key==='ArrowRight')next=(index+1)%buttons.length;
      if(event.key==='ArrowLeft')next=(index-1+buttons.length)%buttons.length;
      if(event.key==='Home')next=0;
      if(event.key==='End')next=buttons.length-1;
      if(next!==undefined){event.preventDefault();select(buttons[next]);buttons[next].focus();}
    });
  });
}
setupTabs('.result-tabs',button=>{currentResult=button.dataset.result;renderResults();});
setupTabs('.case-tabs',button=>renderCase(button.dataset.case));
renderResults();renderCase('prerequisite');

const themeButton=document.querySelector('.theme-toggle');
function setTheme(theme){
  document.documentElement.dataset.theme=theme;
  themeButton.setAttribute('aria-label',`Switch to ${theme==='dark'?'light':'dark'} theme`);
  document.querySelector('meta[name="theme-color"]').content=theme==='dark'?'#14141d':'#f9f9fd';
}
try{setTheme(localStorage.getItem('ec-theme')==='dark'?'dark':'light');}catch{setTheme('light');}
themeButton.addEventListener('click',()=>{
  const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';setTheme(theme);
  try{localStorage.setItem('ec-theme',theme);}catch{/* Local file previews may restrict storage. */}
});
const menuButton=document.querySelector('.menu-toggle'),nav=document.querySelector('#main-nav');
function closeMenu(){nav.classList.remove('is-open');menuButton.setAttribute('aria-expanded','false');menuButton.setAttribute('aria-label','Open navigation');}
menuButton.addEventListener('click',()=>{const open=nav.classList.toggle('is-open');menuButton.setAttribute('aria-expanded',String(open));menuButton.setAttribute('aria-label',open?'Close navigation':'Open navigation');});
nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('is-open')){closeMenu();menuButton.focus();}});
document.addEventListener('click',e=>{if(!e.target.closest('.site-header'))closeMenu();});

const dialog=document.querySelector('#figure-dialog');
let figureTrigger=null;
document.addEventListener('click',event=>{
  const trigger=event.target.closest('[data-zoom]');if(!trigger)return;
  figureTrigger=trigger;
  const image=document.querySelector('#figure-image');image.src=trigger.dataset.zoom;
  image.alt=trigger.querySelector('img')?.alt||trigger.dataset.caption;
  document.querySelector('#figure-caption').textContent=trigger.dataset.caption;
  dialog.showModal();
});
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
dialog.addEventListener('close',()=>figureTrigger?.focus({preventScroll:true}));
if('IntersectionObserver' in window){
  const links=[...nav.querySelectorAll('a')];
  const observer=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting)links.forEach(a=>{const active=a.hash===`#${e.target.id}`;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}},{rootMargin:'-15% 0px -65% 0px',threshold:0});
  ['overview','method','results','cases'].forEach(id=>observer.observe(document.getElementById(id)));
}
