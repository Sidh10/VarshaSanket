"""Local demo server. `python -m src.demo.server` then open http://localhost:8765

Two screens, one server, one cached case -- SAME discipline throughout:

  "/"         the ORIGINAL single-case screen. The theta slider drives the
              REAL decision engine: every slider move hits
              `/api/decide?l_reseed=<n>`, which calls `build_payload()` ->
              `decide()` -> `_expected_loss()`. No lookup table.
  "/profiles" the per-farmer profile screen (D-26/D-27). Selecting one of
              four illustrative demo profiles hits
              `/api/profile_decide?profile=<A|B|C|D>`, which calls
              `build_profile_payload()` -> `decide_for_profile()` -> the SAME
              `decide()`. Risk preference lives ONLY inside the selected
              profile card here -- there is deliberately no floating
              theta/l_reseed slider on this screen (see profiles.py and
              DISCUSSION.md D-27 on why re-adding one here would double-count
              risk that the profile's own multiplier already applied).

stdlib only -- no Flask/FastAPI, no new dependency, nothing to fail on demo day.
Both screens share ONE cached `DemoCase` (2018-07-15, built once at startup,
no live IMD call). The single-case screen additionally fixes the crop
(soybean); the profile screen's crop follows whichever demo profile is
selected.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import urllib.parse

from src.demo.case import build_case
from src.demo.payload import build_payload
from src.demo.profiles import DEMO_PROFILES, build_profile_payload

PORT = 8765
_CASE = None  # built once at startup, shared by both screens


def _get_case():
    global _CASE
    if _CASE is None:
        _CASE = build_case()
    return _CASE


def _payload(l_reseed: float) -> dict:
    case = _get_case()
    lr = max(3000.0, min(40000.0, float(l_reseed)))
    return build_payload(case, lr)


def _profile_payload(profile_key: str) -> dict:
    case = _get_case()
    return build_profile_payload(case, profile_key)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VarshaSanket - demo (2018-07-15, soybean)</title>
<style>
 :root{--sow:#2e7d32;--wait:#c62828;--fragile:#f9a825;--ink:#222;--mut:#666;--line:#ddd}
 *{box-sizing:border-box} body{font:15px/1.5 system-ui,sans-serif;color:var(--ink);margin:0;background:#fafafa}
 .wrap{max-width:960px;margin:0 auto;padding:24px}
 h1{font-size:20px;margin:0 0 2px} .sub{color:var(--mut);margin:0 0 18px;font-size:13px}
 .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:16px}
 .card h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:0 0 10px}
 .row{display:flex;gap:16px;flex-wrap:wrap} .row>.card{flex:1;min-width:260px}
 .rec{font-size:26px;font-weight:700} .rec.sow{color:var(--sow)} .rec.wait{color:var(--wait)}
 .badge{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:12px;margin-left:8px;vertical-align:middle}
 .badge.robust{background:#e8f5e9;color:var(--sow)} .badge.fragile{background:#fff8e1;color:#b8860b}
 input[type=range]{width:100%} .theta{font-variant-numeric:tabular-nums;font-weight:700}
 .bars{margin-top:10px} .bar{position:relative;height:34px;background:#f0f0f0;border-radius:6px;margin:6px 0;overflow:hidden}
 .bar>span{position:absolute;left:0;top:0;bottom:0;background:#bbb;transition:width .08s linear}
 .bar.sow>span{background:var(--sow)} .bar.wait>span{background:var(--wait)}
 .bar>label{position:absolute;left:8px;top:7px;font-size:13px;color:#fff;font-weight:600;text-shadow:0 1px 2px rgba(0,0,0,.35)}
 .bar>b{position:absolute;right:8px;top:7px;font-size:13px;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 1px 2px rgba(0,0,0,.35)}
 .enbox{border-left:3px solid #888;padding:4px 0 4px 12px;margin:8px 0}
 .enbox .v{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
 .enbox .u{color:var(--mut);font-size:12px}
 .en1{border-color:#1565c0} .en2{border-color:#6a1b9a}
 pre.adv{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,Consolas,monospace;background:#f7f7f7;border:1px solid var(--line);border-radius:6px;padding:12px;margin:0}
 .prob{display:flex;gap:8px;margin-top:6px} .prob div{flex:1;text-align:center;background:#f0f0f0;border-radius:6px;padding:6px}
 .prob b{display:block;font-size:16px;font-variant-numeric:tabular-nums} .prob small{color:var(--mut)}
 .ci{color:var(--mut);font-size:12px;font-variant-numeric:tabular-nums}
 .note{color:var(--mut);font-size:12px;margin-top:8px}
 .flip{color:var(--mut);font-size:12px;margin-top:6px}
 svg{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px}
</style></head><body><div class="wrap">
<h1>VarshaSanket &mdash; demo case</h1>
<p class="sub" id="casesub">2018-07-15 &middot; soybean &middot; monsoon core zone (regional, not block-resolved)</p>
<p class="sub"><a href="/profiles">&rarr; Per-farmer profile demo</a> (same date &amp; regime prior, four illustrative farmers, no slider)</p>

<div class="card">
 <h2>&theta; slider &mdash; live expected-loss recomputation</h2>
 <div>Re-seeding loss L<sub>reseed</sub>: <span class="theta" id="lrv"></span> INR/ha
   &nbsp;|&nbsp; L<sub>delay</sub> fixed at <span id="ldv"></span>
   &nbsp;|&nbsp; &theta; = L<sub>reseed</sub>/L<sub>delay</sub> = <span class="theta" id="thv"></span></div>
 <input type="range" id="sl" min="3000" max="30000" step="100">
 <div style="margin-top:12px"><span class="rec" id="rec"></span><span class="badge" id="rob"></span></div>
 <div class="bars">
   <div class="bar sow" id="bsow"><span></span><label>E[loss | SOW now]</label><b id="vsow"></b></div>
   <div class="bar wait" id="bwait"><span></span><label>E[loss | WAIT]</label><b id="vwait"></b></div>
 </div>
 <div class="flip" id="flip"></div>
</div>

<div class="row">
 <div class="card">
  <h2>Effective-N &mdash; two different numbers, not merged</h2>
  <div class="enbox en1"><div class="v" id="en1v"></div>
    <div class="u" id="en1u"></div><div class="u" id="en1m"></div></div>
  <div class="enbox en2"><div class="v" id="en2v"></div>
    <div class="u" id="en2u"></div><div class="u" id="en2m"></div></div>
 </div>
 <div class="card">
  <h2>Stage 1 base rate &mdash; not a forecast</h2>
  <div class="prob" id="prob"></div>
  <div class="ci" id="ci"></div>
  <div class="note" id="brw"></div>
  <div class="note" id="brc"></div>
  <div class="note" id="brs"></div>
 </div>
</div>

<div class="card">
 <h2>Full farmer advisory (WhatsApp, EN) &mdash; the real output</h2>
 <pre class="adv" id="adv"></pre>
 <div class="note" id="advmeta"></div>
</div>

<div class="card">
 <h2>Regional risk display &mdash; one region, one colour, not a choropleth</h2>
 <div id="svg"></div>
</div>

<script>
const $=id=>document.getElementById(id);
const fmt=n=>Math.round(n).toLocaleString('en-IN');
async function update(){
  const lr=$('sl').value;
  const r=await fetch('/api/decide?l_reseed='+lr); const d=await r.json();
  // slider readouts
  $('lrv').textContent=fmt(d.case.l_reseed);
  $('ldv').textContent=fmt(d.case.l_delay);
  $('thv').textContent=d.case.theta.toFixed(3);
  // decision
  const dec=d.decision, rec=$('rec');
  rec.textContent=dec.recommendation.toUpperCase();
  rec.className='rec '+dec.recommendation;
  const rob=$('rob');
  rob.textContent=dec.robust?'robust across uncertainty':'FRAGILE - band straddles the decision';
  rob.className='badge '+(dec.robust?'robust':'fragile');
  const mx=Math.max(dec.e_loss_sow,dec.e_loss_wait,1);
  $('bsow').querySelector('span').style.width=(100*dec.e_loss_sow/mx)+'%';
  $('bwait').querySelector('span').style.width=(100*dec.e_loss_wait/mx)+'%';
  $('vsow').textContent=fmt(dec.e_loss_sow)+' /ha';
  $('vwait').textContent=fmt(dec.e_loss_wait)+' /ha';
  $('flip').textContent='Recommendation flips SOW\\u2192WAIT near \\u03b8\\u2248'+dec.theta_recommendation_flip
     +'.  Below \\u03b8\\u2248'+dec.theta_robust_boundary+' the SOW call is robust; above it the point estimate still says SOW but the uncertainty band straddles the decision.';
  // effective-N
  $('en1v').textContent=d.effective_n.stage1.value+' '+d.effective_n.stage1.unit;
  $('en1u').textContent=d.effective_n.stage1.label;
  $('en1m').textContent=d.effective_n.stage1.means;
  $('en2v').textContent=d.effective_n.stage2.value+' '+d.effective_n.stage2.unit;
  $('en2u').textContent=d.effective_n.stage2.label+' ('+d.effective_n.stage2.agreement+')';
  $('en2m').textContent=d.effective_n.stage2.means;
  // base rate
  const P=d.base_rate.probabilities, lo=d.base_rate.ci_lower, hi=d.base_rate.ci_upper;
  $('prob').innerHTML=Object.keys(P).map(k=>
    '<div><b>'+(100*P[k]).toFixed(0)+'%</b><small>'+k+'</small></div>').join('');
  $('ci').textContent='95% CI  '+Object.keys(P).map(k=>
    k+' ['+(100*lo[k]).toFixed(0)+'-'+(100*hi[k]).toFixed(0)+'%]').join('   ');
  $('brw').textContent=d.base_rate.wording;
  $('brc').textContent=d.base_rate.ci_note;
  $('brs').textContent=d.base_rate.no_skill_number_note;
  // advisory
  $('adv').textContent=d.advisory.text;
  $('advmeta').textContent=d.advisory.char_count+' chars  |  language '+d.advisory.language
     +(d.advisory.verified_language?' (verified)':' (UNVERIFIED)')
     +'  |  evidence lines: '+d.advisory.evidence_lines.length
     +'  |  ICAR disclosure shown: '+d.advisory.disclosure_shown;
  // risk svg
  $('svg').innerHTML=d.risk.svg;
}
$('sl').addEventListener('input',update);
window.addEventListener('load',()=>{ $('sl').value=18000; update(); });
</script>
</div></body></html>"""


PROFILES_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VarshaSanket - per-farmer profile demo</title>
<style>
 :root{--sow:#2e7d32;--wait:#c62828;--fragile:#f9a825;--ink:#222;--mut:#666;--line:#ddd}
 *{box-sizing:border-box} body{font:15px/1.5 system-ui,sans-serif;color:var(--ink);margin:0;background:#fafafa}
 .wrap{max-width:960px;margin:0 auto;padding:24px}
 h1{font-size:20px;margin:0 0 2px} .sub{color:var(--mut);margin:0 0 18px;font-size:13px}
 .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:16px}
 .card h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:0 0 10px}
 .row{display:flex;gap:16px;flex-wrap:wrap} .row>.card{flex:1;min-width:260px}
 .rec{font-size:26px;font-weight:700} .rec.sow{color:var(--sow)} .rec.wait{color:var(--wait)}
 .badge{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:12px;margin-left:8px;vertical-align:middle}
 .badge.robust{background:#e8f5e9;color:var(--sow)} .badge.fragile{background:#fff8e1;color:#b8860b}
 .badge.illustrative{background:#eee;color:var(--mut);margin-left:0}
 .bars{margin-top:10px} .bar{position:relative;height:34px;background:#f0f0f0;border-radius:6px;margin:6px 0;overflow:hidden}
 .bar>span{position:absolute;left:0;top:0;bottom:0;background:#bbb;transition:width .08s linear}
 .bar.sow>span{background:var(--sow)} .bar.wait>span{background:var(--wait)}
 .bar>label{position:absolute;left:8px;top:7px;font-size:13px;color:#fff;font-weight:600;text-shadow:0 1px 2px rgba(0,0,0,.35)}
 .bar>b{position:absolute;right:8px;top:7px;font-size:13px;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 1px 2px rgba(0,0,0,.35)}
 pre.adv{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,Consolas,monospace;background:#f7f7f7;border:1px solid var(--line);border-radius:6px;padding:12px;margin:0}
 .prob{display:flex;gap:8px;margin-top:6px} .prob div{flex:1;text-align:center;background:#f0f0f0;border-radius:6px;padding:6px}
 .prob b{display:block;font-size:16px;font-variant-numeric:tabular-nums} .prob small{color:var(--mut)}
 .ci{color:var(--mut);font-size:12px;font-variant-numeric:tabular-nums}
 .note{color:var(--mut);font-size:12px;margin-top:8px}
 svg{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px}
 .farmers{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
 .fcard{border:2px solid var(--line);border-radius:10px;padding:12px;cursor:pointer;background:#fff;text-align:left;font:inherit;color:inherit}
 .fcard:hover{border-color:#999}
 .fcard.sel{border-color:#1565c0;background:#eef4fc}
 .fcard .flabel{font-weight:700;font-size:13px;margin-bottom:4px}
 .fcard .ftraits{font-size:12px;color:var(--mut);line-height:1.5}
 .fcard .fdemo{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.03em;color:#b8860b;background:#fff8e1;border-radius:8px;padding:1px 6px;margin-top:6px}
 table.econ{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
 table.econ th,table.econ td{text-align:right;padding:4px 8px;border-bottom:1px solid var(--line)}
 table.econ th:first-child,table.econ td:first-child{text-align:left}
 table.econ th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase}
 .eff{color:#1565c0;font-weight:600}
 .base{color:var(--mut)}
 .notmodelled{border:1px dashed #999;border-radius:8px;padding:14px;background:#fafafa}
 .notmodelled h3{margin:0 0 8px;color:var(--mut);font-size:15px}
 .hidden{display:none}
</style></head><body><div class="wrap">
<h1>VarshaSanket &mdash; per-farmer profile demo</h1>
<p class="sub" id="casesub">Loading case...</p>
<p class="sub"><a href="/">&larr; Back to single-case theta-slider demo</a></p>

<div class="card">
 <h2>Choose a demo farmer</h2>
 <p class="note" style="margin-top:0">
   Four <b>illustrative demo profiles</b> &mdash; not real registered users; there is no farmer database.
   Risk preference is a trait of the selected farmer card below, not a separate slider on this screen
   (a floating theta slider on top of a per-farmer profile would double-count risk that the profile
   already applies to the loss side &mdash; see DISCUSSION.md D-27). Every profile is scored against the
   SAME 2018-07-15 regime prior as the single-case demo.
 </p>
 <div class="farmers" id="farmers"></div>
</div>

<div id="result" class="hidden">

<div class="card" id="decisioncard">
 <h2>Recommendation</h2>
 <div><span class="rec" id="rec"></span><span class="badge" id="rob"></span></div>
 <div class="bars">
   <div class="bar sow" id="bsow"><span></span><label>E[loss | SOW now]</label><b id="vsow"></b></div>
   <div class="bar wait" id="bwait"><span></span><label>E[loss | WAIT]</label><b id="vwait"></b></div>
 </div>
</div>

<div class="notmodelled hidden" id="notmodelledcard">
 <h3 id="nmapplic"></h3>
 <p id="nmreason"></p>
</div>

<div class="row">
 <div class="card" id="econcard">
  <h2>Loss inputs &mdash; base (crop default) vs effective (this farmer)</h2>
  <table class="econ">
   <thead><tr><th></th><th>L<sub>reseed</sub></th><th>L<sub>delay</sub></th><th>alpha</th><th>theta</th></tr></thead>
   <tbody>
    <tr class="base"><td>base (crop default)</td><td id="b_lr"></td><td id="b_ld"></td><td id="b_al"></td><td id="b_th"></td></tr>
    <tr class="eff"><td>effective (post multiplier)</td><td id="e_lr"></td><td id="e_ld"></td><td id="e_al"></td><td id="e_th"></td></tr>
   </tbody>
  </table>
  <p class="note" id="mult"></p>
  <p class="note">All figures ILLUSTRATIVE &mdash; not calibrated to surveyed farm economics (same standard as the base crop-loss thresholds).</p>
 </div>
 <div class="card">
  <h2>Stage 1 base rate &mdash; not a forecast, same for every farmer</h2>
  <div class="prob" id="prob"></div>
  <div class="ci" id="ci"></div>
  <div class="note">Based on 20-year averages for this date, not a forecast for this year. Identical across all four profiles &mdash; only the loss side changes.</div>
 </div>
</div>

<div class="card">
 <h2>Full farmer advisory (WhatsApp, EN) &mdash; the real output</h2>
 <pre class="adv" id="adv"></pre>
 <div class="note" id="advmeta"></div>
</div>

<div class="card">
 <h2>Regional risk display &mdash; one region, one colour, not a choropleth</h2>
 <div id="svg"></div>
</div>

</div>
</div>

<script>
const $=id=>document.getElementById(id);
const fmt=n=>Math.round(n).toLocaleString('en-IN');
const PROFILES=[
 {key:'A',crop:'soybean',label:'A \\u2014 rainfed, black soil, risk-tolerant',
  traits:'soybean \\u00b7 rainfed \\u00b7 clay (black) soil \\u00b7 risk-tolerant \\u00b7 pre-sowing'},
 {key:'B',crop:'cotton',label:'B \\u2014 irrigated, sandy soil, risk-averse',
  traits:'cotton \\u00b7 assured irrigation \\u00b7 sandy soil \\u00b7 risk-averse \\u00b7 pre-sowing'},
 {key:'C',crop:'soybean',label:'C \\u2014 partial irrigation, black soil, risk-tolerant',
  traits:'soybean \\u00b7 partial irrigation \\u00b7 clay (black) soil \\u00b7 risk-tolerant \\u00b7 pre-sowing \\u00b7 near-tie call'},
 {key:'D',crop:'soybean',label:'D \\u2014 already sown (germination)',
  traits:'soybean \\u00b7 partial irrigation \\u00b7 loam soil \\u00b7 neutral risk \\u00b7 SOWN, germination stage'},
];
let selected=null;

function renderFarmerCards(){
  $('farmers').innerHTML=PROFILES.map(p=>
    '<button class="fcard" id="fc_'+p.key+'" onclick="selectProfile(\\''+p.key+'\\')">'
    +'<div class="flabel">Demo profile '+p.label+'</div>'
    +'<div class="ftraits">'+p.traits+'</div>'
    +'<div class="fdemo">illustrative demo profile, not a real user</div>'
    +'</button>').join('');
}

async function selectProfile(key){
  selected=key;
  for(const p of PROFILES){ $('fc_'+p.key).classList.toggle('sel', p.key===key); }
  const r=await fetch('/api/profile_decide?profile='+key); const d=await r.json();
  $('result').classList.remove('hidden');

  // base rate (same panel regardless of applicability)
  const P=d.base_rate.probabilities, lo=d.base_rate.ci_lower, hi=d.base_rate.ci_upper;
  $('prob').innerHTML=Object.keys(P).map(k=>
    '<div><b>'+(100*P[k]).toFixed(0)+'%</b><small>'+k+'</small></div>').join('');
  $('ci').textContent='95% CI  '+Object.keys(P).map(k=>
    k+' ['+(100*lo[k]).toFixed(0)+'-'+(100*hi[k]).toFixed(0)+'%]').join('   ');

  const noDecision = (d.decision===null);
  $('decisioncard').classList.toggle('hidden', noDecision);
  $('econcard').classList.toggle('hidden', noDecision);
  $('notmodelledcard').classList.toggle('hidden', !noDecision);

  if(noDecision){
    $('nmapplic').textContent='No SOW/WAIT recommendation \\u2014 applicability: '+d.applicability;
    $('nmreason').textContent=d.not_modelled_reason;
    $('adv').textContent='(not applicable for this farmer \\u2014 the pre-sowing SOW/WAIT advisory does not apply once the crop is already sown)';
    $('advmeta').textContent='';
    $('svg').innerHTML='';
    return;
  }

  const dec=d.decision, rec=$('rec');
  rec.textContent=dec.recommendation.toUpperCase();
  rec.className='rec '+dec.recommendation;
  const rob=$('rob');
  rob.textContent=dec.robust?'robust across uncertainty':'FRAGILE - band straddles the decision';
  rob.className='badge '+(dec.robust?'robust':'fragile');
  const mx=Math.max(dec.e_loss_sow,dec.e_loss_wait,1);
  $('bsow').querySelector('span').style.width=(100*dec.e_loss_sow/mx)+'%';
  $('bwait').querySelector('span').style.width=(100*dec.e_loss_wait/mx)+'%';
  $('vsow').textContent=fmt(dec.e_loss_sow)+' /ha';
  $('vwait').textContent=fmt(dec.e_loss_wait)+' /ha';

  // economics: base vs effective, clearly labelled
  const b=d.economics.base, e=d.economics.effective, m=d.economics.multipliers;
  $('b_lr').textContent=fmt(b.l_reseed); $('b_ld').textContent=fmt(b.l_delay); $('b_al').textContent=b.alpha.toFixed(2); $('b_th').textContent=d.economics.base_theta.toFixed(3);
  $('e_lr').textContent=fmt(e.l_reseed); $('e_ld').textContent=fmt(e.l_delay); $('e_al').textContent=e.alpha.toFixed(2); $('e_th').textContent=d.economics.effective_theta.toFixed(3);
  $('mult').textContent='Multipliers applied by this farmer\\'s profile: L_reseed \\u00d7'+m.l_reseed.toFixed(2)
     +'  L_delay \\u00d7'+m.l_delay.toFixed(2)+'  alpha \\u00d7'+m.alpha.toFixed(2)
     +'  (base values are the crop default; effective values are what decide() actually used for this farmer)';

  // advisory
  $('adv').textContent=d.advisory.text;
  $('advmeta').textContent=d.advisory.char_count+' chars  |  language '+d.advisory.language
     +(d.advisory.verified_language?' (verified)':' (UNVERIFIED)')
     +'  |  evidence lines: '+d.advisory.evidence_lines.length
     +'  |  ICAR disclosure shown: '+d.advisory.disclosure_shown;

  // risk svg
  $('svg').innerHTML=d.risk.svg;
}

async function init(){
  renderFarmerCards();
  const r=await fetch('/api/profile_decide?profile=A'); const d=await r.json();
  $('casesub').textContent=d.base_rate.probabilities ? '2018-07-15 \\u00b7 monsoon core zone (regional, not block-resolved) \\u00b7 same regime prior for every farmer' : '';
  selectProfile('A');
}
window.addEventListener('load', init);
</script>
</div></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path in ("/profiles", "/profiles.html", "/profiles/"):
            self._send(200, PROFILES_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/decide":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                lr = float(q.get("l_reseed", ["18000"])[0])
                body = json.dumps(_payload(lr)).encode("utf-8")
                self._send(200, body, "application/json")
            except Exception as e:  # never crash the demo
                self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")
            return
        if parsed.path == "/api/profile_decide":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                key = q.get("profile", ["A"])[0]
                if key not in DEMO_PROFILES:
                    raise ValueError(f"unknown profile {key!r}; have {list(DEMO_PROFILES)}")
                body = json.dumps(_profile_payload(key)).encode("utf-8")
                self._send(200, body, "application/json")
            except Exception as e:  # never crash the demo
                self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


class _Server(socketserver.ThreadingTCPServer):
    # ThreadingTCPServer so a slow first request cannot block the whole demo;
    # allow_reuse_address so a restart during rehearsal doesn't hit WinError 10048.
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    global _CASE
    print("Building the demo case (cached data, no live IMD call)...")
    _CASE = build_case()  # populate the module global so both screens reuse it
    print(f"VarshaSanket demo -> http://localhost:{PORT}")
    print("  /          theta slider drives the real decision engine.")
    print("  /profiles  four illustrative demo farmers, same decision engine.")
    print("  Ctrl-C to stop.")
    with _Server(("127.0.0.1", PORT), Handler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
