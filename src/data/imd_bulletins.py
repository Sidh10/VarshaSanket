"""IMD Extended Range Forecast bulletin acquisition.

Source: "Current Weather Status and Extended Range Forecast for the next two
weeks", published weekly by IMD as press-release PDFs. Archive listing:

    https://internal.imd.gov.in/pages/press_release_mausam.php

FILENAMES ARE NEVER CONSTRUCTED. They are always read from the archive listing.
This is not a style preference -- D-15 recorded THREE separate occasions where a
guessed filename returned 404 and nearly produced a false "this resource does
not exist" conclusion:

    * a guessed PR number (`20260604_pr_5040.pdf`) that does not exist, when the
      real bulletin was `..._pr_5053.pdf`
    * guessed query parameters on the sub-divisional page
    * a guessed archive filename (`Monthly_Climate_Summary_...png`) when the real
      pattern was `Monthly_Clim_Summary_....pdf`

The press-release number is an opaque sequential id with no derivable relation to
the date. There is no pattern to infer. Read the listing.

Also note (D-15 addendum 1): `internal.imd.gov.in/press_release/` -- the DIRECTORY
-- returns HTTP 200 with a body reading "You are not authorised to access here."
Individual PDFs under it serve normally. A status-code-only reachability check on
that path is misleading.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from dataclasses import dataclass

import requests

ARCHIVE_URL = "https://internal.imd.gov.in/pages/press_release_mausam.php"
PDF_BASE = "https://internal.imd.gov.in"
UA = {"User-Agent": "VarshaSanket/0.1 (SIH26086 research prototype)"}

ERF_TITLE_MARKER = "extended range"


@dataclass(frozen=True)
class Bulletin:
    date: dt.date
    url: str
    title: str
    path: str | None = None


def fetch_archive_index(cache_dir: str = "data/raw/bulletins") -> list[Bulletin]:
    """Read the archive listing and return every Extended Range bulletin in it.

    Returns ALL of them (year-round), unfiltered by season -- callers filter.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cached = os.path.join(cache_dir, "_archive_index.html")
    if os.path.exists(cached):
        html = open(cached, encoding="utf-8", errors="replace").read()
    else:
        r = requests.get(ARCHIVE_URL, headers=UA, timeout=180, verify=True)
        r.raise_for_status()
        html = r.text
        open(cached, "w", encoding="utf-8").write(html)

    out: list[Bulletin] = []
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", html):
        m = re.search(r'href\s*=\s*["\']([^"\']+\.pdf)["\']', row, re.I)
        if not m:
            continue
        text = re.sub(r"(?s)<[^>]+>", " ", row)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if ERF_TITLE_MARKER not in text.lower():
            continue
        d = re.search(r"/(\d{8})_pr", m.group(1))
        if not d:
            continue
        out.append(
            Bulletin(
                date=dt.datetime.strptime(d.group(1), "%Y%m%d").date(),
                url=PDF_BASE + m.group(1).replace("..", ""),
                title=text,
            )
        )
    return out


def select_jjas(bulletins: list[Bulletin], years: tuple[int, int]) -> list[Bulletin]:
    """JJAS bulletins in `years`, de-duplicated by date.

    IMD sometimes posts the SAME bulletin under two press-release numbers on one
    date. D-15 addendum 1 verified three such pairs are byte-identical (MD5
    match), so keeping one per date loses nothing. Doing this silently would be
    wrong, hence this docstring and the returned count.
    """
    seen: dict[dt.date, Bulletin] = {}
    for b in sorted(bulletins, key=lambda x: (x.date, x.url)):
        if not (6 <= b.date.month <= 9):
            continue
        if not (years[0] <= b.date.year <= years[1]):
            continue
        seen.setdefault(b.date, b)
    return list(seen.values())


def download(
    bulletins: list[Bulletin], cache_dir: str = "data/raw/bulletins", retries: int = 3
) -> list[Bulletin]:
    """Fetch each bulletin PDF. Retries because the host drops connections."""
    os.makedirs(cache_dir, exist_ok=True)
    out = []
    for b in bulletins:
        path = os.path.join(cache_dir, f"{b.date:%Y%m%d}.pdf")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            out.append(Bulletin(b.date, b.url, b.title, path))
            continue
        ok = False
        for _ in range(retries):
            try:
                r = requests.get(b.url, headers=UA, timeout=180, verify=True)
                if r.status_code == 200 and r.content[:5] == b"%PDF-":
                    open(path, "wb").write(r.content)
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(3)
        out.append(Bulletin(b.date, b.url, b.title, path if ok else None))
    return out


def extract_texts(
    bulletins: list[Bulletin], cache_path: str = "data/cache/bulletin_texts.json"
) -> dict[str, str]:
    """Extract the text layer of each PDF. All bulletins carry a real text layer
    (D-15 addendum 1 measured 100%), so no OCR path is needed."""
    if os.path.exists(cache_path):
        return json.load(open(cache_path, encoding="utf-8"))

    import pypdf

    texts: dict[str, str] = {}
    for b in bulletins:
        if not b.path or not os.path.exists(b.path):
            continue
        try:
            raw = "\n".join(
                (p.extract_text() or "") for p in pypdf.PdfReader(b.path).pages
            )
        except Exception:
            continue
        texts[f"{b.date:%Y%m%d}"] = re.sub(r"\s+", " ", raw)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False)
    return texts


def load_jjas_bulletin_texts(
    years: tuple[int, int], cache_dir: str = "data/raw/bulletins"
) -> dict[str, str]:
    """One-call convenience: archive -> JJAS selection -> download -> text."""
    idx = fetch_archive_index(cache_dir)
    sel = select_jjas(idx, years)
    got = download(sel, cache_dir)
    return extract_texts(got)


if __name__ == "__main__":
    idx = fetch_archive_index()
    print(f"Extended Range bulletins in archive listing: {len(idx)}")
    sel = select_jjas(idx, (2021, 2026))
    print(f"JJAS 2021-2026, de-duplicated by date: {len(sel)}")
    got = download(sel)
    n_ok = sum(1 for b in got if b.path)
    print(f"downloaded: {n_ok}/{len(got)}")
    texts = extract_texts(got)
    print(f"text extracted: {len(texts)}")
