"""
Render a "palette wall" showcase image from the data-derived palettes.

This is our own generated content (built from data/palettes.json), so it carries
no third-party image licensing. Used as the README hero.

    python scripts/make_showcase.py
    python scripts/make_showcase.py --cols 4 --out assets/palette-wall.png
"""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# curated, recognisable, visually diverse (filtered to what exists)
FEATURED = [
    "cottagecore", "vaporwave", "dark-academia", "cybergoth",
    "cyberpunk", "weirdcore", "coquette", "mallsoft",
    "y2k", "goblincore", "fairycore", "cottagegoth",
    "kidcore", "grunge", "light-academia", "dreamcore",
    "angelcore", "clowncore", "royalcore", "witchcore",
    "fairy-grunge", "baddie", "barbiecore", "gorpcore",
    "balletcore", "twee", "normcore", "acidwave",
]

BG = (14, 14, 18)
INK = (243, 243, 246)
MUTE = (150, 150, 165)
FAINT = (95, 95, 110)

FONT_CANDIDATES = {
    "display": [("/System/Library/Fonts/Supplemental/Futura.ttc", 0)],
    "text": [("/System/Library/Fonts/HelveticaNeue.ttc", 0),
             ("/System/Library/Fonts/Supplemental/Arial.ttf", 0)],
}


def load_font(kind, size):
    for path, idx in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size=size, index=idx)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def tracked(draw, xy, text, font, fill, spacing):
    """Draw text with letter spacing (tracking), return total width."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing
    return x - xy[0] - spacing


def tracked_width(draw, text, font, spacing):
    return sum(draw.textlength(c, font=font) + spacing for c in text) - spacing


def rounded_strip(colors, w, h, radius):
    """A rounded horizontal strip split into equal color segments."""
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    n = max(len(colors), 1)
    seg = w / n
    for i, hexcol in enumerate(colors):
        rgb = tuple(int(hexcol[j:j + 2], 16) for j in (1, 3, 5))
        d.rectangle([round(i * seg), 0, round((i + 1) * seg), h], fill=rgb + (255,))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius,
                                           fill=255)
    strip.putalpha(mask)
    return strip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "palette-wall.png"))
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=1800)
    args = ap.parse_args()

    with open(os.path.join(DATA, "palettes.json"), encoding="utf-8") as f:
        palettes = json.load(f)
    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        names = {r["slug"]: r.get("name", r["slug"]) for r in json.load(f)}

    cards = [(names.get(s, s), [c["hex"] for c in palettes[s]["colors"][:6]])
             for s in FEATURED if s in palettes][:24]

    W = args.width
    cols = args.cols
    rows = (len(cards) + cols - 1) // cols
    margin = 90
    gutter = 46
    card_w = (W - 2 * margin - (cols - 1) * gutter) // cols
    swatch_h = 74
    label_h = 40
    card_h = label_h + swatch_h
    row_gap = 58
    head_h = 300
    foot_h = 150
    H = head_h + rows * card_h + (rows - 1) * row_gap + foot_h

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = load_font("display", 82)
    f_sub = load_font("text", 30)
    f_label = load_font("text", 22)
    f_foot = load_font("text", 24)

    # header
    tracked(d, (margin, 96), "AESTHETICS WIKI", f_title, INK, 6)
    d.text((margin + 4, 205),
           "1,201 internet aesthetics  .  data-derived colour palettes  .  a Claude skill",
           font=f_sub, fill=MUTE)

    # cards
    y0 = head_h
    for i, (name, colors) in enumerate(cards):
        r, c = divmod(i, cols)
        x = margin + c * (card_w + gutter)
        y = y0 + r * (card_h + row_gap)
        tracked(d, (x + 2, y), name.upper(), f_label, MUTE, 3)
        strip = rounded_strip(colors, card_w, swatch_h, radius=14)
        img.paste(strip, (x, y + label_h), strip)

    # footer
    foot_y = H - foot_h + 40
    d.line([(margin, foot_y - 24), (W - margin, foot_y - 24)], fill=(34, 34, 42),
           width=2)
    d.text((margin + 2, foot_y), "MARSO  DESIGN", font=f_foot, fill=INK)
    tail = "github.com/marso-design/aesthetics-wiki"
    d.text((W - margin - d.textlength(tail, font=f_foot), foot_y), tail,
           font=f_foot, fill=FAINT)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    img.save(args.out, optimize=True)
    print("wrote %s  (%d cards, %dx%d)" % (args.out, len(cards), W, H))


if __name__ == "__main__":
    main()
