#!/usr/bin/env python3
"""Build the "Take the Stage" profile: animated SVG pieces + README.md.

    python3 scripts/gen_profile.py

Inputs : profile.config.json (what to show; edit this)
         assets/profile.json  (live data, refreshed by scripts/fetch_profile_data.py)
Outputs: assets/stage/*.svg and README.md (both generated, do not hand-edit)

GitHub renders SVGs as <img>: CSS animation works, links inside don't. So every
clickable thing (each project, post, contact) is its own small SVG wrapped in
<a>. Pieces below the hero have transparent backgrounds so the gaps between
images are invisible, and they're drawn to read on both light and dark GitHub.
"""
import datetime
import glob
import json
import math
import os
import random
import re
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8") as source:
    CFG = json.load(source)
with open(os.path.join(ROOT, "assets", "profile.json"), encoding="utf-8") as source:
    DATA = json.load(source)
OUT_DIR = os.path.join(ROOT, "assets", "stage")
REL = "assets/stage"
W = 900

ACCENT, BLACK, WHITE = CFG.get("accent_color", "#0F57BE"), "#000", "#fff"
MONO = "'JetBrains Mono','Fira Code','SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
SANS = "'Arial Black','Helvetica Neue',Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
COLLAGE_FONTS = [
    "Impact,'Arial Black',sans-serif",
    "Georgia,'Times New Roman',serif",
    "'Courier New',Courier,monospace",
    "'Arial Black',Arial,sans-serif",
    "'Trebuchet MS',Verdana,sans-serif",
]
TILE_SCHEMES = [(WHITE, BLACK), (ACCENT, WHITE), (BLACK, WHITE), (WHITE, ACCENT)]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt(n):
    return f"{n:,}"


def uid(*parts):
    return "u" + format(zlib.crc32("|".join(map(str, parts)).encode()), "x")


BASE_CSS = """
.pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,1.7,.4,1) both}
@keyframes pop{0%{transform:scale(0) rotate(-40deg);opacity:0}60%{transform:scale(1.3) rotate(8deg);opacity:1}100%{transform:scale(1) rotate(0)}}
.wob{transform-box:fill-box;transform-origin:center;animation:wob 1.6s ease-in-out infinite alternate}
@keyframes wob{from{transform:rotate(-4deg) translateY(-1px)}to{transform:rotate(4deg) translateY(2px)}}
.slamL{animation:slamL .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes slamL{from{transform:translateX(-1100px)}to{transform:none}}
.slamR{animation:slamR .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes slamR{from{transform:translateX(1100px)}to{transform:none}}
.drop{transform-box:fill-box;transform-origin:center;animation:drop .5s cubic-bezier(.2,1.6,.4,1) both}
@keyframes drop{from{transform:translateY(-400px) rotate(-30deg);opacity:0}to{transform:none;opacity:1}}
.thump{transform-box:fill-box;transform-origin:center;animation:thump 1.2s ease-in-out infinite}
@keyframes thump{0%,100%{transform:scale(1)}12%{transform:scale(1.15)}24%{transform:scale(1)}}
.blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.marquee{animation:marquee linear infinite}
@keyframes marquee{to{transform:translateX(var(--d))}}
.type{transform-box:fill-box;transform-origin:0 50%;animation:type linear both}
@keyframes type{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@media (prefers-reduced-motion:reduce){*{animation-duration:0s!important;animation-iteration-count:1!important;animation-delay:0s!important}}
"""


def svg(w, h, title, body, css="", defs="", clip_round=None):
    clip = ""
    if clip_round is not None:
        defs += f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="{clip_round}"/></clipPath>'
        body = f'<g clip-path="url(#frame)">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><style>{BASE_CSS}{css}</style>"
        f"<defs>{defs}</defs>{clip}{body}</svg>\n"
    )


def collage(text, x, y, size, rng, delay=0.0, step=0.06, schemes=TILE_SCHEMES, wobble=0.3, outline=False):
    """Ransom-note letters: each glyph its own cut-paper tile, font, tilt and pop-in."""
    out, cx = [], x
    for i, ch in enumerate(text):
        if ch == " ":
            cx += size * 0.4
            continue
        s = size * rng.uniform(0.82, 1.16)
        w, h = s * 0.8, s * 1.02
        bg, fg = rng.choice(schemes)
        font = rng.choice(COLLAGE_FONTS)
        rot, dy = rng.uniform(-10, 10), rng.uniform(-0.09, 0.09) * size
        glyph = ch.upper() if rng.random() < 0.72 or not ch.isalpha() else ch.lower()
        j = lambda: rng.uniform(-0.07, 0.07) * s  # noqa: E731  ragged paper edges
        pts = f"{-w/2+j():.1f},{-h/2+j():.1f} {w/2+j():.1f},{-h/2+j():.1f} {w/2+j():.1f},{h/2+j():.1f} {-w/2+j():.1f},{h/2+j():.1f}"
        stroke = ' stroke="#000" stroke-width="2"' if outline else ""
        tile = (
            f'<polygon points="{pts}" fill="{bg}"{stroke}/>'
            f'<text y="{s*0.32:.1f}" font-size="{s*0.86:.1f}" fill="{fg}" font-family="{font}" font-weight="900" text-anchor="middle">{esc(glyph)}</text>'
        )
        if rng.random() < wobble:
            tile = f'<g class="wob" style="animation-delay:{-rng.uniform(0,2):.2f}s">{tile}</g>'
        out.append(
            f'<g transform="translate({cx+w/2:.1f},{y+dy:.1f}) rotate({rot:.1f})">'
            f'<g class="pop" style="animation-delay:{delay+i*step:.2f}s">{tile}</g></g>'
        )
        cx += w * 1.04
    return "".join(out)


def marquee(text, x, y, width, size, fill, speed=55):
    unit = text + "   ★   "
    tw = len(unit) * size * 0.6
    cid = uid("mq", text, x, y)
    return (
        f'<clipPath id="{cid}"><rect x="{x}" y="{y-size*1.2:.0f}" width="{width}" height="{size*1.8:.0f}"/></clipPath>'
        f'<g clip-path="url(#{cid})"><g class="marquee" style="--d:-{tw:.1f}px;animation-duration:{tw/speed:.1f}s" '
        f'font-family="{MONO}" font-size="{size}" font-weight="700" fill="{fill}">'
        + "".join(
            f'<text x="{x+k*tw:.1f}" y="{y}" textLength="{tw:.1f}" lengthAdjust="spacing" xml:space="preserve">{esc(unit)}</text>'
            for k in range(2 + int(width // tw))
        )
        + "</g></g>"
    )


def wrap(text, n):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


# ------------------------------------------------------------------ data

STATS = DATA["stats"]


def targets():
    out = []
    for t in CFG["targets"]:
        r = DATA["repos"].get(t["repo"], {})
        out.append({
            "label": t.get("label") or t["repo"].upper(),
            "tag": (t.get("tag") or r.get("language") or "").upper(),
            "stars": r.get("stars", 0),
            "wip": t.get("wip", False),
            "url": t.get("url") or r.get("url") or f"https://github.com/{t.get('owner', CFG['github_username'])}/{t['repo']}",
            "description": t.get("description") or r.get("description", "").strip(),
        })
    return out


def posts():
    pc = CFG.get("posts", {})
    if pc.get("count", 3) <= 0:
        return []
    seen, out = set(), []
    for p in sorted(DATA["posts"], key=lambda post: post["date"], reverse=True):
        series = re.split(r"\s*(?:#\d|:)", p["title"])[0].strip().lower()
        if pc.get("one_per_series", True) and series in seen:
            continue
        seen.add(series)
        out.append(p)
        if len(out) >= min(3, pc.get("count", 3)):
            break
    return out


# ------------------------------------------------------------------ pieces

def hero():
    rng = random.Random(42)
    H = 380
    css = """
.spin{transform-box:view-box;transform-origin:735px 190px;animation:spin 40s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
"""
    defs = '<pattern id="dots" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="5" cy="5" r="2.1" fill="#000" fill-opacity=".28"/></pattern>'
    b = [f'<rect width="{W}" height="{H}" fill="{ACCENT}"/>']
    rays = []
    for i in range(16):
        a0, a1 = math.radians(i * 22.5), math.radians(i * 22.5 + 11)
        rays.append(f"M735,190 L{735+900*math.cos(a0):.0f},{190+900*math.sin(a0):.0f} L{735+900*math.cos(a1):.0f},{190+900*math.sin(a1):.0f}Z")
    b.append(f'<path class="spin" d="{" ".join(rays)}" fill="#000" fill-opacity=".22"/>')
    b.append(f'<rect width="{W}" height="{H}" fill="url(#dots)"/>')
    b.append(
        '<g class="slamL">'
        '<polygon points="0,0 580,0 552,50 568,54 500,190 522,196 440,380 0,380" fill="#fff"/>'
        '<polygon points="0,0 560,0 532,46 548,50 482,186 502,192 422,380 0,380" fill="#000"/></g>'
    )
    first, last = CFG["name"]
    b.append(collage(first, 30, 92, 74, rng, delay=0.45))
    b.append(collage(last, 70, 186, 66, rng, delay=0.9, schemes=[(WHITE, BLACK), (ACCENT, BLACK), (WHITE, ACCENT), (ACCENT, WHITE)]))
    role = CFG["role"]
    bw = min(525, len(role) * 12 + 40)
    b.append(
        f'<g class="slamL" style="animation-delay:1.3s"><g transform="translate(34,244) skewX(-16)">'
        f'<rect width="{bw:.0f}" height="34" fill="#fff"/>'
        f'<text x="14" y="25" font-family="{SANS}" font-size="19" fill="#000" letter-spacing="1">{esc(role)}</text></g>'
        f'<text x="36" y="304" font-family="{MONO}" font-size="13" font-weight="700" fill="{ACCENT}">{esc(" ▸ ".join(CFG["stack"]))}</text></g>'
    )
    b.append(
        f'<text x="36" y="350" font-family="{MONO}" font-size="11" fill="#fff" opacity=".7">SYS://{esc(CFG.get("runtime", "SYSTEMS"))} ONLINE  ·  LOC: {esc(CFG["location"])}  ·  <tspan class="blink">█</tspan></text>'
    )
    stamps = [
        (fmt(STATS["contributions"]), "CONTRIBS", 668, 92, -7, (WHITE, BLACK)),
        (fmt(STATS["stars"]), "STARS", 806, 186, 6, (BLACK, WHITE)),
        (str(STATS["repos"]), "REPOS", 672, 286, -3, (WHITE, ACCENT)),
    ]
    for i, (num, lbl, x, y, rot, (bg, fg)) in enumerate(stamps):
        b.append(
            f'<g transform="translate({x},{y}) rotate({rot})"><g class="drop" style="animation-delay:{1.7+i*.2:.2f}s">'
            f'<polygon points="-70,-46 72,-52 66,44 -66,50" fill="#000" transform="translate(7,7)"/>'
            f'<polygon points="-70,-46 72,-52 66,44 -66,50" fill="{bg}"/>'
            f'<text y="10" font-family="{SANS}" font-size="40" fill="{fg}" text-anchor="middle">{num}</text>'
            f'<text y="34" font-family="{MONO}" font-size="12" font-weight="700" fill="{fg}" text-anchor="middle" letter-spacing="2">{lbl}</text></g></g>'
        )
    title = f"{first.title()} {last.title()} — {role.title()}. {fmt(STATS['contributions'])} contributions, {fmt(STATS['stars'])} stars, {STATS['repos']} public repos."
    return svg(W, H, title, "".join(b), css, defs, clip_round=14)


def about():
    lines = wrap(CFG["about"], 80)
    H = 70 + len(lines) * 26
    b = []
    pts = f"14,22 {W-10},8 {W-24},{H-10} 4,{H-4}"
    b.append(f'<g class="slamR"><polygon points="{pts}" fill="{ACCENT}" transform="translate(8,6)"/>'
             f'<polygon points="{pts}" fill="#000" stroke="#fff" stroke-width="3"/></g>')
    b.append(
        f'<g class="drop" style="animation-delay:.35s"><g transform="translate(36,4) rotate(-4) skewX(-12)">'
        f'<rect width="150" height="34" fill="#fff" stroke="#000" stroke-width="2"/>'
        f'<text x="14" y="25" font-family="{SANS}" font-size="19" fill="#000">{esc(CFG["name"][0])}</text></g></g>'
    )
    t = 0.7
    for i, line in enumerate(lines):
        y = 62 + i * 26
        n, dur = len(line), len(line) * 0.018
        cid = uid("ab", i)
        b.append(
            f'<clipPath id="{cid}"><rect class="type" style="animation-delay:{t:.2f}s;animation-duration:{dur:.2f}s" x="40" y="{y-20}" width="{W-80}" height="28"/></clipPath>'
            f'<text clip-path="url(#{cid})" x="44" y="{y}" font-family="{SANS}" font-size="17" fill="#fff" font-weight="400">{esc(line)}</text>'
        )
        t += dur + 0.05
    b.append(f'<polygon class="blink" points="{W-60},{H-34} {W-44},{H-34} {W-52},{H-24}" fill="{ACCENT}"/>')
    return svg(W, H, CFG["about"], "".join(b))


def section(title, seed):
    rng = random.Random(seed)
    H = 76
    b = [
        f'<g class="slamL"><polygon points="10,58 {W-40},40 {W-44},50 12,66" fill="{ACCENT}"/></g>',
        collage(title, 20, 38, 40, rng, delay=0.1, step=0.04, wobble=0.2, outline=True),
    ]
    return svg(W, H, title, "".join(b))


def menu_item(i, n, t):
    H = 86
    cycle = n * 1.3
    a, z = 100 * i / n, 100 * (i + 1) / n
    on = f"{a+0.5:.1f}%,{z-0.5:.1f}%{{opacity:1;transform:none}}"
    off_before = f"0%,{a:.1f}%{{opacity:0;transform:translateX(-14px)}}" if i else ""
    off_after = f"{z:.1f}%,100%{{opacity:0;transform:translateX(-14px)}}" if i < n - 1 else ""
    kf = off_before + on + off_after
    if i == 0:
        kf = f"0%{{opacity:1;transform:none}}{z-0.5:.1f}%{{opacity:1;transform:none}}{z:.1f}%,100%{{opacity:0;transform:translateX(-14px)}}"
    css = f"""
.hl{{animation:hl {cycle:.1f}s steps(1) infinite}}
@keyframes hl{{{kf}}}
.menu{{animation:menu .4s cubic-bezier(.2,1.5,.4,1) both}}
@keyframes menu{{from{{transform:translate(950px,0)}}to{{transform:none}}}}
"""
    x = 64 + min(i, 4) * 16
    bw = 640
    # tag · status/stars; stars are hidden when zero
    status = f'<tspan class="blink" fill="{ACCENT}">IN DEV ●</tspan>' if t["wip"] else (f"★ {t['stars']}" if t["stars"] else "")
    right = " · ".join(x for x in (esc(t["tag"]), status) if x)
    description = t["description"]
    if len(description) > 82:
        description = description[:79].rstrip() + "…"
    b = [
        f'<g class="menu" style="animation-delay:{.15+i*.1:.2f}s">',
        f'<g class="hl"><polygon points="{x-18},{6} {x+bw+30},{0} {x+bw+14},{H-4} {x-30},{H-2}" fill="#fff" stroke="#000" stroke-width="2"/>'
        f'<polygon points="{x-8},{11} {x+bw+18},{6} {x+bw+6},{H-9} {x-18},{H-7}" fill="{ACCENT}"/>'
        f'<text x="{x-58}" y="{H/2+9}" font-family="{SANS}" font-size="26" fill="{ACCENT}">▶</text></g>',
        f'<g transform="translate({x},14) skewX(-14)">'
        f'<rect x="6" y="5" width="{bw}" height="60" fill="{ACCENT}"/>'
        f'<rect width="{bw}" height="60" fill="#000" stroke="#fff" stroke-width="2"/>'
        f'<text x="18" y="25" font-family="{SANS}" font-size="{19 if len(t["label"]) < 20 else 15}" fill="#fff">{esc(t["label"])}</text>'
        f'<text x="{bw-14}" y="23" font-family="{MONO}" font-size="12" font-weight="700" fill="#fff" text-anchor="end">{right}</text>'
        f'<text x="18" y="46" font-family="{SANS}" font-size="12" fill="#fff" font-weight="400">{esc(description)}</text></g>',
        "</g>",
    ]
    title = f"{t['label']}: {t['description'] or t['tag']}" + (" (in development)" if t["wip"] else (f" — {t['stars']} stars" if t["stars"] else ""))
    return svg(W, H, title, "".join(b), css)


def post_item(i, p, latest):
    rng = random.Random(100 + i)
    H = 96
    d = datetime.date.fromisoformat(p["date"])
    rot = [-1.2, 0.9, -0.6, 1.1][i % 4]
    lines = wrap(p["title"], 55)
    if len(lines) > 2:
        lines = [lines[0], lines[1][:52].rstrip() + "…"]
    b = [
        f'<g transform="rotate({rot} 450 48)"><g class="drop" style="animation-delay:{.15+i*.15:.2f}s">',
        f'<polygon points="30,12 {W-30},8 {W-36},{H-8} 34,{H-4}" fill="{ACCENT}" transform="translate(7,5)"/>',
        f'<polygon points="30,12 {W-30},8 {W-36},{H-8} 34,{H-4}" fill="#fff" stroke="#000" stroke-width="3"/>',
        f'<g transform="translate(52,18) skewX(-10)"><rect width="78" height="38" fill="#000"/>'
        f'<text x="39" y="17" font-family="{SANS}" font-size="16" fill="#fff" text-anchor="middle">{d.day:02d}</text>'
        f'<text x="39" y="32" font-family="{MONO}" font-size="11" font-weight="700" fill="{ACCENT}" text-anchor="middle">{d.strftime("%b %Y").upper()}</text></g>',
        "".join(f'<text x="150" y="{39+j*25}" font-family="{SERIF}" font-size="18" font-style="italic" font-weight="700" fill="#000">{esc(line)}</text>' for j, line in enumerate(lines)),
    ]
    if latest:
        b.append(f'<g transform="translate({W-120},64) rotate(8)"><g class="thump">' + collage("NEW!", 0, 5, 18, rng, delay=.6, step=.05, wobble=0) + "</g></g>")
    b.append("</g></g>")
    return svg(W, H, f"{p['title']} ({d.isoformat()})", "".join(b))


def all_posts_item():
    H = 48
    b = [f'<g class="slamR" style="animation-delay:.6s"><g transform="translate({W-300},8) skewX(-14)">'
         f'<rect x="5" y="4" width="250" height="30" fill="{ACCENT}"/><rect width="250" height="30" fill="#000" stroke="#fff" stroke-width="2"/>'
         f'<text x="125" y="21" font-family="{SANS}" font-size="14" fill="#fff" text-anchor="middle">{esc(CFG.get("posts", {}).get("all_posts_label", "ALL POSTS"))} ▸</text></g></g>']
    return svg(W, H, "All posts", "".join(b))


def contact(i, c):
    w, h = 190, 68
    rot = [-5, 4, -3, 5, -4, 3][i % 6]
    bg, fg = [(BLACK, WHITE), (WHITE, BLACK), (ACCENT, WHITE)][i % 3]
    sh = ACCENT if bg != ACCENT else BLACK
    label = c["label"]
    fs = 20 if len(label) <= 9 else 15
    b = [
        f'<g transform="rotate({rot} {w/2} {h/2})"><g class="pop" style="animation-delay:{.1+i*.1:.2f}s">',
        f'<polygon points="14,14 {w-10},10 {w-16},{h-12} 10,{h-10}" fill="{sh}" transform="translate(6,5)"/>',
        f'<polygon points="14,14 {w-10},10 {w-16},{h-12} 10,{h-10}" fill="{bg}" stroke="#000" stroke-width="2.5"/>',
        f'<text x="{w/2}" y="{h/2+fs*0.36:.1f}" font-family="{SANS}" font-size="{fs}" fill="{fg}" text-anchor="middle">{esc(label)}</text>',
        "</g></g>",
    ]
    return svg(w, h, label, "".join(b))


def activity_card():
    metrics = [
        ("contributions", "TOTAL CONTRIBUTIONS"),
        ("private_contributions", "ANON. PRIVATE ACTIVITY"),
        ("commits", "VISIBLE COMMITS"),
        ("pull_requests", "VISIBLE PULL REQUESTS"),
        ("reviews", "VISIBLE PR REVIEWS"),
        ("issues", "VISIBLE ISSUES OPENED"),
    ]
    body = [f'<rect x="8" y="8" width="884" height="260" rx="12" fill="#000" stroke="{ACCENT}" stroke-width="3"/>']
    for i, (key, label) in enumerate(metrics):
        x, y = 40 + (i % 3) * 290, 58 + (i // 3) * 90
        body.append(
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="30" fill="#fff">{fmt(STATS[key])}</text>'
            f'<text x="{x}" y="{y+24}" font-family="{MONO}" font-size="11" fill="#fff">{label}</text>'
        )
    body.append(f'<path d="M32 198 H868" stroke="{ACCENT}" stroke-width="2"/>')
    for i, line in enumerate([
        "ALL-TIME / SINCE ACCOUNT CREATION / UPDATED DAILY",
        "Totals include private activity shared through GitHub contribution settings.",
        "Private activity is anonymous; the visible breakdown excludes hidden details.",
    ]):
        body.append(f'<text x="34" y="{220+i*17}" font-family="{MONO}" font-size="11" fill="#fff">{esc(line)}</text>')
    title = "; ".join(f"{label.title()}: {fmt(STATS[key])}" for key, label in metrics)
    return svg(W, 280, title, "".join(body))


def ticker():
    H = 40
    last = posts()[0]["title"].upper() if posts() else ""
    text = (f"{fmt(STATS['contributions'])} CONTRIBUTIONS   ★   {fmt(STATS['private_contributions'])} ANON. PRIVATE   ★   {fmt(STATS['commits'])} VISIBLE COMMITS   ★   {fmt(STATS['stars'])} STARS   ★   {STATS['repos']} PUBLIC REPOS   ★   "
            f"{STATS['followers']} FOLLOWERS   ★   {CFG.get('ticker_message', last)}   ★   THANKS FOR STOPPING BY")
    b = [f'<g transform="skewX(-14)"><rect x="20" y="6" width="{W-34}" height="28" fill="#000" stroke="{ACCENT}" stroke-width="3"/></g>',
         marquee(text, 18, 26, W - 40, 13, "#fff")]
    return svg(W, H, text.title(), "".join(b))


# ------------------------------------------------------------------ assemble

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(OUT_DIR, "*.svg")):
        os.remove(f)

    def write(name, content):
        with open(os.path.join(OUT_DIR, name), "w") as f:
            f.write(content)
        return f"{REL}/{name}"

    tg, ps = targets(), posts()
    first, last = CFG["name"]
    md = [
        "<!--\n  GENERATED by scripts/gen_profile.py. Do not edit by hand.\n"
        "  To change what's shown, edit profile.config.json and run:\n"
        "      python3 scripts/gen_profile.py\n"
        "  (the \"Refresh profile\" GitHub Action also does this daily with fresh stats/posts)\n-->\n",
        f'<p align="center"><img src="{write("hero.svg", hero())}" width="100%" alt="{esc(first.title())} {esc(last.title())}, {esc(CFG["role"].title())}. {fmt(STATS["contributions"])} contributions, {fmt(STATS["stars"])} stars, {STATS["repos"]} public repos." /></p>\n',
        f'<p align="center"><img src="{write("activity.svg", activity_card())}" width="100%" alt="All-time GitHub contributions, anonymous private activity, visible commits, pull requests, reviews, and issues" /></p>\n',
        f'<p align="center"><img src="{write("about.svg", about())}" width="100%" alt="{esc(CFG["about"])}" /></p>\n',
        f'<p align="center"><img src="{write("h-targets.svg", section("SELECT TARGET", 1))}" width="100%" alt="Select target" /><br>',
    ]
    for i, t in enumerate(tg):
        alt = f"{t['label']}: {t['description'] or t['tag']}"
        md.append(f'<a href="{esc(t["url"])}"><img src="{write(f"target-{i}.svg", menu_item(i, len(tg), t))}" width="100%" alt="{esc(alt)}" /></a><br>')
    md.append("</p>\n")
    if ps:
        md.append(f'<p align="center"><img src="{write("h-intel.svg", section("LATEST BLOGS", 2))}" width="100%" alt="Latest blog posts" /><br>')
        for i, p in enumerate(ps):
            md.append(f'<a href="{esc(p["url"])}"><img src="{write(f"post-{i}.svg", post_item(i, p, i == 0))}" width="100%" alt="{esc(p["title"])}" /></a><br>')
        if CFG.get("posts", {}).get("all_posts_url"):
            md.append(f'<a href="{esc(CFG["posts"]["all_posts_url"])}"><img src="{write("all-posts.svg", all_posts_item())}" width="100%" alt="All posts" /></a>')
        md.append("</p>\n")
    md.append(f'<p align="center"><img src="{write("h-contact.svg", section("CONTACT", 3))}" width="100%" alt="Contact" /><br>')
    for i, c in enumerate(CFG.get("contacts", [])):
        src = write(f"contact-{slug(c['label'])}.svg", contact(i, c))
        md.append(f'<a href="{esc(c["url"])}"><img src="{src}" height="46" alt="{esc(c["label"].title())}" /></a>')
    md.append("</p>\n")
    md.append(f'<p align="center"><img src="{write("ticker.svg", ticker())}" width="100%" alt="Stats ticker" /></p>\n')

    if CFG.get("badges"):
        md.append('<p align="center">')
        for badge in CFG["badges"]:
            md.append(f'<a href="{esc(badge["url"])}"><img src="{esc(badge["image"])}" alt="{esc(badge["label"])}" /></a>')
        md.append('</p>\n')
    md.append('<p align="center"><sub>Design adapted from <a href="https://github.com/basteez/basteez">basteez/basteez</a>.</sub></p>\n')

    with open(os.path.join(ROOT, "README.md"), "w") as f:
        f.write("\n".join(md))
    print(f"wrote README.md + {len(glob.glob(os.path.join(OUT_DIR, '*.svg')))} SVGs in {REL}/")


if __name__ == "__main__":
    main()

