#!/usr/bin/env python3
"""Build the per-event invitation pages from index.html (the full invite).

index.html is the single source. This script writes one folder per event
(mehndi/, shaadi/, ...) holding a copy of the page with only that event,
plus each page's WhatsApp/Facebook preview image.

Run from anywhere:  python3 tools/build.py
"""
import pathlib
import re
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SITE_ALL = "https://fabihawedsfarooq.vercel.app/"

# Every event the full invite contains, in page order.
EVENTS = {
    "mehndi": {
        "label": "Mehndi",
        "url": "https://fabihawedsfarooq-mehndi.vercel.app/",
        "cover": '<b style="color:var(--rani)">Mehndi · Thursday 5 Nov 2026</b> · Karachi',
        "summary": "Mehndi · Thursday 5 November 2026 · VOCO Ballroom, Karachi",
        "files": ["qr/mehndi.svg", "mehndi.ics"],
    },
    "shaadi": {
        "label": "Shaadi",
        "url": "https://fabihawedsfarooq-shaadi.vercel.app/",
        "cover": '<b style="color:var(--burgundy)">Shaadi · Saturday 7 Nov 2026</b> · Karachi',
        "summary": "Shaadi · Saturday 7 November 2026 · Sky Deck Banquet, Karachi",
        "files": ["qr/shadi.svg", "shadi.ics"],
    },
}

# Shrinks the cover so it fits a 1200x630 link-preview card.
OG_CSS = (".cover{padding:20px!important}.cover__verse-en{margin-bottom:10px!important}"
          ".cover__date{margin:12px 0 18px!important}.cover__names{font-size:70px!important}"
          ".seal{width:92px!important;height:92px!important;font-size:24px!important}"
          ".cover__hint,.music{display:none!important}.cover .cluster{--size:210px!important}")


def sub_once(pattern, repl, text, flags=0):
    out, n = re.subn(pattern, lambda _: repl, text, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f"build: pattern not found: {pattern[:60]}")
    return out


def event_page(master, key):
    ev = EVENTS[key]
    page = master.replace(SITE_ALL, ev["url"])
    title = f"Fabiha &amp; Farooq · {ev['label']} Invitation"
    page = sub_once(r"<title>.*?</title>", f"<title>{title}</title>", page)
    page = sub_once(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{title}">', page)
    page = sub_once(r'<meta name="description" content="[^"]*">',
                    f'<meta name="description" content="You are cordially invited to the wedding of Fabiha Siddiqui &amp; Syed Farooq Iqbal. {ev["summary"]}.">', page)
    page = sub_once(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{ev["summary"]}">', page)
    page = sub_once(r'<p class="cover__date">.*?</p>', f'<p class="cover__date">{ev["cover"]}</p>', page, re.S)

    for other, oev in EVENTS.items():
        if other == key:
            continue
        label = oev["label"]
        # the event's chapter, its chip on the invitation and its link in the dock
        page = sub_once(rf"        <!-- =+ {label} =+ -->.*?(?=        <!-- =+ )", "", page, re.S)
        page = sub_once(rf'\s*<a class="chip chip--{other}" href="#{other}">.*?</a>', "", page, re.S)
        page = sub_once(rf'\s*<a href="#{other}" data-section="{other}">{label}</a>', "", page)
    return page


def render_preview(html_path, out_jpg):
    """Screenshot the cover at 1200x630 and save a small JPEG (WhatsApp skips large images)."""
    src = html_path.read_text()
    tmp = html_path.with_name("_og.html")
    tmp.write_text(src.replace("</style>", OG_CSS + "</style>", 1))
    with tempfile.TemporaryDirectory() as prof:
        png = pathlib.Path(prof) / "og.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={prof}", "--window-size=1200,630",
                        "--virtual-time-budget=4000", f"--screenshot={png}", tmp.as_uri()],
                       check=True, capture_output=True)
        tmp.unlink()
        quality = 78
        while True:
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality),
                            str(png), "--out", str(out_jpg)], check=True, capture_output=True)
            if out_jpg.stat().st_size < 120_000 or quality <= 50:
                break
            quality -= 8
    print(f"  preview {out_jpg.relative_to(ROOT)}  {out_jpg.stat().st_size // 1024} KB")


def main():
    master = (ROOT / "index.html").read_text()
    print("full invite")
    render_preview(ROOT / "index.html", ROOT / "og-image.jpg")
    for key, ev in EVENTS.items():
        out = ROOT / key
        print(f"{ev['label']} only -> {key}/")
        out.mkdir(exist_ok=True)
        (out / "index.html").write_text(event_page(master, key))
        for f in ev["files"]:
            (out / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, out / f)
        (out / ".vercelignore").write_text(".vercel\n.env*\n")
        render_preview(out / "index.html", out / "og-image.jpg")


if __name__ == "__main__":
    main()
