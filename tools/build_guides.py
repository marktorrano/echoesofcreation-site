"""Build the player guides (guides.html + guide-<id>.html) from the game's in-game help.

The source is the game repo's data/help.json, read AT A GIT REVISION -- never the working
tree. help.json gains entries for features before they ship, and the site must only describe
what players already have. Bump GAME_REV to the commit the live client was built from.

Also rewrites sitemap.xml so new guide pages are listed.

    python tools/build_guides.py                 # uses GAME_REV below
    python tools/build_guides.py --rev <commit>  # after a release
"""
import argparse
import datetime
import html
import json
import pathlib
import re
import subprocess

SITE = pathlib.Path(__file__).resolve().parent.parent
GAME_REPO = pathlib.Path("F:/Users/User/Game")
GAME_REV = "1bebd609"  # last help.json change in the 0.2.17 client (2026-09-28)
GAME_VERSION = "0.2.17"
BASE = "https://echoesofcreation.net/"
STEAM = "https://store.steampowered.com/app/4685890/Echoes_of_Creation_Origin/"
DISCORD = "https://discord.gg/JjrmEN9exb"
LATEST_NOTES = "patch-notes-0.2.17.html"

# Hub sections, in order. A help category not listed here is not published.
SECTIONS = [
    ("New Players", "Start here: your first hour, the controls, and how a character grows.",
     ["getting_started", "controls", "classes", "stats_leveling", "skills", "quests", "death", "saving"]),
    ("Combat", "Fighting by hand and on auto, and what the monsters do back.",
     ["combat", "auto_combat", "status_effects", "monsters", "elite_monsters", "bosses", "battle_dungeon"]),
    ("Gear & Items", "Equipment, upgrades, the bag and everything that goes in it.",
     ["equipment", "loadouts", "inventory", "potions", "wardrobe", "potential", "life_skills"]),
    ("Economy", "Gold, Lumina and trading with other players.",
     ["currency", "marketplace", "diamond_shop", "patrons_crest", "mail", "loot_history"]),
    ("Playing Together", "Parties, guilds, friends and the faction war.",
     ["multiplayer", "party", "guild", "friends", "faction_war", "leaderboard"]),
    ("World & Collections", "Getting around, daily routines and things to collect.",
     ["world_map", "waypoints", "day_night", "events", "daily_activities", "achievements",
      "monsterpedia", "mounts", "pets"]),
]

BULLET = re.compile(r"^\s*(?:[-*\u2022])\s+(.*)$")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
LABEL = re.compile(r"^([A-Z][A-Za-z0-9'&+ /()-]{1,32}):\s+(.+)$")


def esc(s):
    return html.escape(s, quote=True)


def inline(line):
    line = re.sub(r" {2,}", " ", line)
    m = LABEL.match(line)
    if m:
        return f"<strong>{esc(m.group(1))}:</strong> {esc(m.group(2))}"
    return esc(line)


def body_html(body):
    """Lines -> paragraphs, with runs of bullet or numbered lines as lists."""
    out, run, kind = [], [], None

    def flush():
        nonlocal run, kind
        if run:
            out.append(f"<{kind}>" + "".join(f"<li>{inline(x)}</li>" for x in run) + f"</{kind}>")
        run, kind = [], None

    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        b, n = BULLET.match(line), NUMBERED.match(line)
        k = "ul" if b else "ol" if n else None
        if k:
            if kind != k:
                flush()
                kind = k
            run.append((b or n).group(1))
        else:
            flush()
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return "\n".join(out)


def plain(s):
    return re.sub(r"\s+", " ", s).strip()


def describe(cat):
    """Meta description: the first sentences of the guide, under ~155 chars."""
    text = plain(" ".join(e["body"] for e in cat["entries"]))
    text = re.sub(r"^[-*\u2022\d.)\s]+", "", text)
    out = ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if len(out) + len(sent) > 150:
            break
        out = (out + " " + sent).strip()
    if not out:
        out = text[:150].rsplit(" ", 1)[0] + "..."
    return f"{cat['name']} guide for Echoes of Creation. {out}"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{url}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{url}">
  <meta property="og:site_name" content="Echoes of Creation">
  <meta property="og:image" content="{base}images/hero-banner.webp">
  <meta property="og:image:width" content="1344">
  <meta property="og:image:height" content="768">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{base}images/hero-banner.webp">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="icon" href="favicon.ico?v=2" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png?v=2">
  <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png?v=2">
  <link rel="apple-touch-icon" href="apple-touch-icon.png?v=2">
  <link rel="stylesheet" href="css/style.css">
  <style>
    .guide-hero {{ min-height: 36vh; display: flex; align-items: center; justify-content: center; text-align: center;
      padding: 120px 20px 50px;
      background: linear-gradient(180deg, rgba(10, 8, 14, 0.92), rgba(10, 8, 14, 0.78)), url('images/hero-banner.webp') center/cover no-repeat; }}
    .guide-hero .hero-subtitle {{ margin-top: 12px; max-width: 680px; margin-left: auto; margin-right: auto; }}
    .guide-crumbs {{ font-size: 0.85rem; color: rgba(255,255,255,0.5); margin-bottom: 14px; letter-spacing: 0.04em; }}
    .guide-crumbs a {{ color: var(--color-gold, #d4a853); text-decoration: none; }}
    .guide-wrap {{ max-width: 820px; margin: 0 auto; }}
    .guide-toc {{ background: var(--color-surface, #1a1a2e); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
      padding: 18px 22px; margin-bottom: 36px; }}
    .guide-toc h2 {{ font-family: var(--font-display, Georgia, serif); font-size: 1rem; color: var(--color-gold, #d4a853);
      letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 10px; }}
    .guide-toc ol {{ margin: 0; padding-left: 20px; columns: 2 240px; column-gap: 28px; }}
    .guide-toc li {{ margin: 4px 0; break-inside: avoid; }}
    .guide-toc a {{ color: var(--color-text, #e0ddd5); text-decoration: none; }}
    .guide-toc a:hover {{ color: var(--color-gold, #d4a853); }}
    .guide-entry {{ margin-bottom: 34px; scroll-margin-top: 90px; }}
    .guide-entry h2 {{ font-family: var(--font-display, Georgia, serif); font-size: 1.35rem; color: var(--color-gold, #d4a853);
      margin: 0 0 12px; letter-spacing: 0.02em; }}
    .guide-entry p, .guide-entry li {{ color: rgba(255,255,255,0.82); line-height: 1.75; }}
    .guide-entry p {{ margin: 0 0 10px; }}
    .guide-entry ul, .guide-entry ol {{ margin: 0 0 12px; padding-left: 22px; }}
    .guide-entry strong {{ color: var(--color-text, #e0ddd5); }}
    .guide-nav {{ display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: 44px;
      padding-top: 22px; border-top: 1px solid rgba(255,255,255,0.08); }}
    .guide-nav a {{ color: var(--color-gold, #d4a853); text-decoration: none; }}
    .guide-fine {{ color: rgba(255,255,255,0.4); font-size: 0.85rem; margin-top: 28px; text-align: center; }}
    .hub-section {{ margin-bottom: 48px; }}
    .hub-section h2 {{ font-family: var(--font-display, Georgia, serif); color: var(--color-gold, #d4a853); font-size: 1.5rem; margin: 0 0 6px; }}
    .hub-section > p {{ color: rgba(255,255,255,0.6); margin: 0 0 18px; }}
    .hub-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }}
    .hub-card {{ display: block; padding: 18px 20px; border-radius: 8px; text-decoration: none;
      background: var(--color-surface, #1a1a2e); border: 1px solid rgba(255,255,255,0.06);
      transition: border-color 0.3s, transform 0.3s; }}
    .hub-card:hover {{ border-color: rgba(212,168,83,0.45); transform: translateY(-2px); }}
    .hub-card h3 {{ font-family: var(--font-display, Georgia, serif); color: var(--color-text, #e0ddd5); font-size: 1.1rem; margin: 0 0 6px; }}
    .hub-card p {{ color: rgba(255,255,255,0.55); font-size: 0.9rem; line-height: 1.5; margin: 0; }}
    @media (max-width: 620px) {{ .guide-toc ol {{ columns: 1; }} }}
  </style>
  <script type="application/ld+json">
{ld}
  </script>
</head>
<body>

  <!-- Navigation -->
  <nav class="navbar" id="navbar">
    <div class="nav-container">
      <a href="index.html" class="nav-logo"><img src="images/logo.png" alt="Echoes of Creation" class="nav-logo-img"></a>
      <button class="nav-toggle" id="nav-toggle" aria-label="Toggle menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
      <ul class="nav-links" id="nav-links">
        <li><a href="index.html#about">About</a></li>
        <li><a href="index.html#classes">Classes</a></li>
        <li><a href="index.html#world">World</a></li>
        <li><a href="guides.html">Guides</a></li>
        <li><a href="index.html#faq">FAQ</a></li>
        <li><a href="{notes}">Patch Notes</a></li>
        <li><a href="{discord}" class="nav-discord-link" target="_blank" rel="noopener">Discord</a></li>
      </ul>
    </div>
  </nav>
"""

FOOT = """
  <!-- CTA -->
  <section class="section section-dark">
    <div class="container" style="text-align:center;">
      <h2 class="section-title">Play Free on Steam</h2>
      <p class="section-subtitle">Echoes of Creation is a free-to-play online 3D action RPG for Windows.</p>
      <div class="hero-actions" style="justify-content:center;">
        <a href="{steam}" class="btn btn-play" target="_blank" rel="noopener">Play on Steam</a>
        <a href="{discord}" class="btn btn-secondary" target="_blank" rel="noopener">Join the Discord</a>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-brand">
          <h3>Echoes of Creation</h3>
          <p>A free-to-play online 3D action RPG</p>
        </div>
        <div class="footer-links">
          <a href="index.html#about">Story</a>
          <a href="index.html#classes">Classes</a>
          <a href="guides.html">Guides</a>
          <a href="index.html#faq">FAQ</a>
          <a href="{notes}">Patch Notes</a>
          <a href="{discord}" target="_blank" rel="noopener">Discord</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2026 Echoes of Creation. All rights reserved.</p>
      </div>
    </div>
  </footer>

  <script src="js/main.js"></script>
</body>
</html>
"""


def page(title, desc, url, ld, body):
    common = dict(base=BASE, notes=LATEST_NOTES, discord=DISCORD, steam=STEAM)
    ld_txt = "\n".join("  " + l for l in json.dumps(ld, indent=2, ensure_ascii=False).split("\n"))
    ld_txt = ld_txt.replace("</", "<\\/")
    return (HEAD.format(title=esc(title), desc=esc(desc), url=url, ld=ld_txt, **common)
            + body + FOOT.format(**common))


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


def build(rev):
    raw = subprocess.run(["git", "-C", str(GAME_REPO), "show", f"{rev}:data/help.json"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    cats = {c["id"]: c for c in json.loads(raw)["categories"]}
    order = [cid for _, _, ids in SECTIONS for cid in ids if cid in cats]
    missing = [cid for _, _, ids in SECTIONS for cid in ids if cid not in cats]
    if missing:
        print("not in help.json at", rev, "-- skipped:", ", ".join(missing))
    today = datetime.date.today().isoformat()
    files = {}

    for i, cid in enumerate(order):
        cat = cats[cid]
        name = cat["name"]
        fname = f"guide-{cid.replace('_', '-')}.html"
        url = BASE + fname
        title = f"{name} Guide | Echoes of Creation"
        desc = describe(cat)
        entries = cat["entries"]
        ids = []
        for e in entries:
            s = slug(e["title"]) or "section"
            while s in ids:
                s += "-2"
            ids.append(s)
        toc = "".join(f'<li><a href="#{s}">{esc(e["title"])}</a></li>' for s, e in zip(ids, entries))
        secs = "\n".join(
            f'        <section class="guide-entry" id="{s}">\n          <h2>{esc(e["title"])}</h2>\n'
            f'          {body_html(e["body"])}\n        </section>' for s, e in zip(ids, entries))
        prev_l = (f'<a href="guide-{order[i - 1].replace("_", "-")}.html">&laquo; {esc(cats[order[i - 1]]["name"])}</a>'
                  if i > 0 else '<a href="guides.html">&laquo; All guides</a>')
        next_l = (f'<a href="guide-{order[i + 1].replace("_", "-")}.html">{esc(cats[order[i + 1]]["name"])} &raquo;</a>'
                  if i + 1 < len(order) else '<a href="guides.html">All guides &raquo;</a>')
        ld = [
            {"@context": "https://schema.org", "@type": "Article", "headline": f"{name} Guide",
             "description": desc, "url": url, "dateModified": today, "inLanguage": "en",
             "image": BASE + "images/hero-banner.webp",
             "author": {"@type": "Organization", "name": "Torrano Dev"},
             "publisher": {"@type": "Organization", "name": "Torrano Dev"},
             "about": {"@type": "VideoGame", "name": "Echoes of Creation", "url": BASE}},
            crumbs_ld([("Home", BASE), ("Guides", BASE + "guides.html"), (name, url)]),
        ]
        body = f"""
  <header class="guide-hero">
    <div>
      <div class="guide-crumbs"><a href="index.html">Home</a> &rsaquo; <a href="guides.html">Guides</a> &rsaquo; {esc(name)}</div>
      <h1 class="hero-title">{esc(name)}</h1>
      <p class="hero-subtitle">An Echoes of Creation guide</p>
    </div>
  </header>

  <section class="section">
    <div class="container">
      <div class="guide-wrap">
        <nav class="guide-toc" aria-label="On this page">
          <h2>On this page</h2>
          <ol>{toc}</ol>
        </nav>
{secs}
        <div class="guide-nav">{prev_l}{next_l}</div>
        <p class="guide-fine">Written for game version {GAME_VERSION}. Found something out of date? Tell us on <a href="{DISCORD}" target="_blank" rel="noopener" style="color:inherit;">Discord</a>.</p>
      </div>
    </div>
  </section>
"""
        files[fname] = page(title, desc, url, ld, body)

    # Hub
    blocks = []
    for sec_name, blurb, ids in SECTIONS:
        cards = "".join(
            f'\n          <a class="hub-card" href="guide-{cid.replace("_", "-")}.html"><h3>{esc(cats[cid]["name"])}</h3>'
            f'<p>{esc(", ".join(e["title"] for e in cats[cid]["entries"][:3]))}</p></a>'
            for cid in ids if cid in cats)
        blocks.append(f'      <div class="hub-section" id="{slug(sec_name)}">\n        <h2>{esc(sec_name)}</h2>\n'
                      f'        <p>{esc(blurb)}</p>\n        <div class="hub-grid">{cards}\n        </div>\n      </div>')
    hub_desc = ("Player guides for Echoes of Creation, the free-to-play online 3D action RPG: getting started, "
                "classes, combat, auto-hunt, gear upgrades, the marketplace, guilds, mounts and pets.")
    hub_ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Echoes of Creation Guides",
         "description": hub_desc, "url": BASE + "guides.html",
         "about": {"@type": "VideoGame", "name": "Echoes of Creation", "url": BASE},
         "hasPart": [{"@type": "Article", "headline": f"{cats[c]['name']} Guide",
                      "url": BASE + f"guide-{c.replace('_', '-')}.html"} for c in order]},
        crumbs_ld([("Home", BASE), ("Guides", BASE + "guides.html")]),
    ]
    hub_body = """
  <header class="guide-hero">
    <div>
      <div class="guide-crumbs"><a href="index.html">Home</a> &rsaquo; Guides</div>
      <h1 class="hero-title">Player Guides</h1>
      <p class="hero-subtitle">Everything the in-game help covers, on one page you can keep open beside the game.</p>
    </div>
  </header>

  <section class="section">
    <div class="container">
""" + "\n".join(blocks) + f"""
      <p class="guide-fine">Written for game version {GAME_VERSION}. In game, the same help is under the Help button.</p>
    </div>
  </section>
"""
    files["guides.html"] = page("Player Guides | Echoes of Creation", hub_desc, BASE + "guides.html", hub_ld, hub_body)

    for fname, text in files.items():
        path = SITE / fname
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != text:
            path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(files)} guide pages from help.json @ {rev}")
    write_sitemap(today)


def write_sitemap(today):
    rows = []
    pages = sorted(SITE.glob("*.html"), key=lambda p: (p.name != "index.html", p.name != "guides.html", p.name))
    for p in pages:
        d = subprocess.run(["git", "-C", str(SITE), "log", "-1", "--format=%cs", "--", p.name],
                           capture_output=True, text=True).stdout.strip() or today
        url = BASE + ("" if p.name == "index.html" else p.name)
        pr = ("1.0" if p.name == "index.html" else "0.9" if p.name == "guides.html"
              else "0.3" if p.name in ("eula.html", "privacy.html")
              else "0.8" if p.name.startswith("guide-") else "0.6")
        rows.append(f"  <url><loc>{url}</loc><lastmod>{d}</lastmod><priority>{pr}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    (SITE / "sitemap.xml").write_text(xml, encoding="utf-8", newline="\n")
    print(len(rows), "urls in sitemap.xml")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default=GAME_REV)
    build(ap.parse_args().rev)
