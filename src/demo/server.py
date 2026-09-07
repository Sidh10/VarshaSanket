"""Local demo server. `python -m src.demo.server` then open http://localhost:8765

The theta slider drives the REAL decision engine: every slider move hits
`/api/decide?l_reseed=<n>`, which calls `build_payload()` -> `decide()` ->
`_expected_loss()`. There is no precomputed lookup table. Computation is a few
microseconds, so the response is immediate.

stdlib only -- no Flask/FastAPI, no new dependency, nothing to fail on demo day.
The case is fixed (2018-07-15 soybean, src/demo/case.py); the ONLY variable is
l_reseed.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import urllib.parse

from src.demo.case import build_case
from src.demo.payload import build_payload

PORT = 8765
_CASE = None  # built once at startup


def _payload(l_reseed: float) -> dict:
    global _CASE
    if _CASE is None:
        _CASE = build_case()
    lr = max(3000.0, min(40000.0, float(l_reseed)))
    return build_payload(_CASE, lr)


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
        if parsed.path == "/api/decide":
            q = urllib.parse.parse_qs(parsed.query)
            try:
                lr = float(q.get("l_reseed", ["18000"])[0])
                body = json.dumps(_payload(lr)).encode("utf-8")
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
    _CASE = build_case()  # populate the module global so /api/decide reuses it
    print(f"VarshaSanket demo -> http://localhost:{PORT}")
    print("  theta slider drives the real decision engine. Ctrl-C to stop.")
    with _Server(("127.0.0.1", PORT), Handler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
