# -*- coding: utf-8 -*-
"""Regenerate live/panel.json's patch_notes[] from index.html's Update History.

The in-game Events panel shows the same release list as the website. Keeping two
hand-written copies in step never survives contact with a release, so this derives one
from the other: index.html is the single source of truth, and this rewrites the feed to
match it exactly -- entity-decoded and with absolute URLs, because the game renders the
text raw and OS.shell_open needs a full URL.

    python tools/sync_panel_patch_notes.py

Run it after adding a release row to index.html, then commit and push both.
Only patch_notes[] is touched; events[] and _howto are left exactly as they are.
"""
import io, json, os, re, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://echoesofcreation.net/"
# How many releases the in-game panel lists. The panel is a narrow side panel, not an
# archive -- its "All patch notes" row always links to the full history, so this only
# decides how many get a shortcut. Change it and re-run; it needs no client build.
LIMIT = 3
ROW = re.compile(r'<a class="upd-row[^"]*"\s+href="([^"]+)"(.*?)</a>', re.S)


def field(body, cls):
    m = re.search(r'upd-%s">([^<]*)' % cls, body)
    return html.unescape(m.group(1)).strip() if m else ""


def main():
    index = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    rows = []
    for href, body in ROW.findall(index):
        ver = field(body, "ver").lstrip("vV")
        if not ver:
            continue
        rows.append({
            "version": ver,
            "name": field(body, "name"),
            "date": field(body, "date"),
            "url": href if href.startswith("http") else SITE + href.lstrip("/"),
        })
    if not rows:
        raise SystemExit("no upd-row entries found in index.html — did the markup change?")
    rows = rows[:LIMIT]   # index.html is newest-first, so this is the latest LIMIT

    path = os.path.join(ROOT, "live", "panel.json")
    feed = json.load(io.open(path, encoding="utf-8"))
    before = len(feed.get("patch_notes", []))
    feed["patch_notes"] = rows
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    print("patch_notes: %d -> %d (newest %d of the site's list)" % (before, len(rows), LIMIT))
    for r in rows:
        print("  v%-8s %-28s %s" % (r["version"], r["name"], r["date"]))


if __name__ == "__main__":
    main()
