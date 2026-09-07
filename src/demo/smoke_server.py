"""Start the demo server in a thread, hit every route, stop. `python -m src.demo.smoke_server`

Proves the slider endpoint returns a live, real-engine decision over HTTP and
that the SOW<->WAIT flip is reachable through the actual server, not just the
in-process check in run_demo.py.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request

from src.demo import server as srv


def _get(path: str) -> tuple[int, bytes]:
    r = urllib.request.urlopen(f"http://127.0.0.1:{srv.PORT}{path}", timeout=15)
    return r.status, r.read()


def main() -> None:
    srv._CASE = srv.build_case()
    httpd = srv._Server(("127.0.0.1", srv.PORT), srv.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    try:
        st, body = _get("/")
        assert st == 200 and b"<title>VarshaSanket" in body, "index page bad"
        print(f"GET /                    -> {st}, {len(body)} bytes, has slider: "
              f"{b'id=\"sl\"' in body}")

        seen = {}
        for lr in (5000, 9000, 11400, 11500, 25000):
            st, body = _get(f"/api/decide?l_reseed={lr}")
            d = json.loads(body)
            dec = d["decision"]
            seen[lr] = dec["recommendation"]
            print(f"GET /api/decide lr={lr:>6} -> {st}  theta={d['case']['theta']:.3f}  "
                  f"E[sow]={dec['e_loss_sow']:>7.0f}  E[wait]={dec['e_loss_wait']:>7.0f}  "
                  f"{dec['recommendation'].upper()}  robust={dec['robust']}")

        assert seen[5000] == "sow" and seen[25000] == "wait", "flip not reachable over HTTP"
        # last payload: full contract present
        assert d["effective_n"]["stage1"]["value"] == 20
        assert 3.0 < d["effective_n"]["stage2"]["value"] < 5.5
        assert len(d["advisory"]["evidence_lines"]) == 2
        assert d["advisory"]["disclosure_shown"] is True
        assert d["risk"]["svg"].startswith("<svg")
        assert "not a forecast" in d["base_rate"]["wording"]

        try:
            _get("/nope")
            raise AssertionError("/nope should 404")
        except urllib.error.HTTPError as e:
            print(f"GET /nope                -> {e.code} (expected 404)")
            assert e.code == 404
        print("\nSMOKE: PASS -- slider flip reachable over HTTP; full payload contract intact")
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
