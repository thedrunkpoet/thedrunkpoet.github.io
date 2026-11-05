#!/usr/bin/env python3
"""Tiny static-site builder for thedrunkpoet.com.

Usage (run inside a design folder):
    python build.py     # builds this design into ./dist  (what you deploy)

Entries: entries/YYYY-MM-DD-slug.md with optional front matter (title, date, mood).
"""
import datetime as dt
import html
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
ENTRIES = ROOT / "entries"
DIST = ROOT / "dist"
SITE_NAME = "The Drunk Poet"
TAGLINE = "words, mostly after midnight"


def parse_entry(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        text = text[m.end():]
    stem = path.stem
    dm = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", stem)
    date_str = meta.get("date") or (dm.group(1) if dm else dt.date.today().isoformat())
    slug = dm.group(2) if dm else stem
    date = dt.date.fromisoformat(date_str)
    title = meta.get("title") or slug.replace("-", " ").title()
    body = markdown.markdown(text, extensions=["extra", "smarty", "sane_lists"])
    plain = re.sub(r"<[^>]+>", "", body)
    words = len(plain.split())
    first_p = re.search(r"<p>(.*?)</p>", body, re.S)
    excerpt = re.sub(r"<[^>]+>", "", first_p.group(1)) if first_p else ""
    if len(excerpt) > 180:
        excerpt = excerpt[:180].rsplit(" ", 1)[0] + "…"
    return {
        "title": title,
        "slug": slug,
        "date": date,
        "mood": meta.get("mood", ""),
        "body": body,
        "excerpt": excerpt,
        "reading": f"{max(1, round(words / 220))} min read",
        "url": f"{date:%Y}/{date:%m}/{slug}/",
    }


def load_entries() -> list:
    es = [parse_entry(p) for p in sorted(ENTRIES.glob("*.md"))]
    es.sort(key=lambda e: e["date"], reverse=True)
    return es


def block(tpl: str, name: str):
    """Return (template_without_block_marked, inner) for <!--name-->..<!--/name-->."""
    m = re.search(rf"<!--{name}-->(.*?)<!--/{name}-->", tpl, re.S)
    return (m.group(1), m) if m else (None, None)


def fill(tpl: str, data: dict) -> str:
    for k, v in data.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    return tpl


def cond(tpl: str, name: str, data):
    """Keep <!--name-->..<!--/name--> filled with data, or drop it if data is None."""
    inner, m = block(tpl, name)
    if m is None:
        return tpl
    return tpl[: m.start()] + (fill(inner, data) if data else "") + tpl[m.end():]


def entry_data(e: dict, root: str) -> dict:
    d = e["date"]
    return {
        "title": html.escape(e["title"]),
        "url": root + e["url"],
        "date_iso": d.isoformat(),
        "date_short": f"{d:%d %b}",
        "date_long": f"{d:%A, %d %B %Y}".replace(" 0", " "),
        "year": d.year,
        "month_label": f"{d:%B %Y}",
        "day": f"{d.day}",
        "mon": f"{d:%b}",
        "mood": html.escape(e["mood"]),
        "excerpt": html.escape(e["excerpt"]),
        "reading": e["reading"],
        "body": e["body"],
    }


def build_theme(out: Path):
    tdir = ROOT / "templates"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    layout = (tdir / "layout.html").read_text()
    entries = load_entries()
    common = {"site_name": SITE_NAME, "tagline": TAGLINE}

    def page(rel: str, title: str, content: str, depth: int, desc: str = ""):
        root = "../" * depth if depth else "./"
        html_out = fill(layout, {
            **common, "page_title": title, "content": content, "root": root,
            "desc": html.escape(desc or TAGLINE),
        })
        p = out / rel / "index.html" if rel else out / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_out, encoding="utf-8")

    # --- index
    idx = (tdir / "index.html").read_text()
    side_tpl, sm = block(idx, "sideitem")
    if sm:
        rows = [fill(side_tpl, {**entry_data(o, ""), "current": ""}) for o in entries]
        idx = idx[: sm.start()] + "".join(rows) + idx[sm.end():]
    idx = fill(idx, {**common, "count": len(entries)})
    page("", SITE_NAME, idx, 0)

    # --- entries
    etpl = (tdir / "entry.html").read_text()
    for i, e in enumerate(entries):
        depth = 3
        root = "../" * depth
        newer = entries[i - 1] if i > 0 else None
        older = entries[i + 1] if i + 1 < len(entries) else None
        t = cond(etpl, "newer", entry_data(newer, root) if newer else None)
        t = cond(t, "older", entry_data(older, root) if older else None)
        t = cond(t, "mood", {"mood": html.escape(e["mood"])} if e["mood"] else None)
        side_tpl, sm = block(t, "sideitem")
        if sm:
            rows = []
            for o in entries:
                od = entry_data(o, root)
                od["current"] = ' class="current" aria-current="page"' if o is e else ""
                rows.append(fill(side_tpl, od))
            t = t[: sm.start()] + "".join(rows) + t[sm.end():]
        t = fill(t, entry_data(e, root))
        page(e["url"].rstrip("/"), f"{e['title']} — {SITE_NAME}", t, depth, e["excerpt"])

    # --- archive
    if (tdir / "archive.html").exists():
        atpl = (tdir / "archive.html").read_text()
        item_tpl, m = block(atpl, "item")
        month_tpl, _ = block(item_tpl, "month")
        core = re.sub(r"<!--month-->.*?<!--/month-->", "", item_tpl, flags=re.S)
        parts, last = [], None
        for e in entries:
            d = entry_data(e, "../")
            if month_tpl and d["month_label"] != last:
                parts.append(fill(month_tpl, d))
                last = d["month_label"]
            parts.append(fill(core, d))
        atpl = atpl[: m.start()] + "".join(parts) + atpl[m.end():]
        page("archive", f"Archive — {SITE_NAME}", fill(atpl, common), 1)

    # --- about
    if (tdir / "about.html").exists():
        page("about", f"About — {SITE_NAME}", fill((tdir / "about.html").read_text(), common), 1)

    # --- assets
    shutil.copy(ROOT / "style.css", out / "style.css")
    if (ROOT / "fonts").exists():
        shutil.copytree(ROOT / "fonts", out / "fonts")
    if (ROOT / "fonts.html").exists():
        shutil.copy(ROOT / "fonts.html", out / "fonts.html")
    base = "https://thedrunkpoet.com/"
    urls = [(base, entries[0]["date"] if entries else None), (base + "archive/", None), (base + "about/", None)]
    urls += [(base + e["url"], e["date"]) for e in entries]
    sm = "".join(
        f"<url><loc>{u}</loc>" + (f"<lastmod>{d.isoformat()}</lastmod>" if d else "") + "</url>"
        for u, d in urls
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + sm + "</urlset>\n"
    )
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n")
    (out / "CNAME").write_text("thedrunkpoet.com\n")
    (out / ".nojekyll").write_text("")
    print(f"built {ROOT.name}: {len(entries)} entries -> {out.relative_to(ROOT)}")


def main():
    build_theme(DIST)


if __name__ == "__main__":
    main()
