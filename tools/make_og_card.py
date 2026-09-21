#!/usr/bin/env python3
"""Render the 1200x630 social card at public/og-card.png.

Why a separate image: the only large image the site had was the portrait
profile.jpg (900x1200). Handed to a share card it gets centre-cropped, so a
link posted to LINE or X showed a slice of a face and no words. A landscape
card carries the name, the service and the entry price instead.

Colours and fonts mirror public/assets/site-r12-*.css so the card and the page
read as the same site. Re-run after changing the copy:

    python3 tools/make_og_card.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
OUT = PUBLIC / "og-card.png"

W, H = 1200, 630

PAPER = (251, 250, 247)
INK = (22, 23, 29)
ICHO = (177, 146, 47)
ICHO_SOFT = (239, 230, 200)
ASAGI = (95, 149, 168)
GREY = (99, 100, 107)

GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
GOTHIC_BOLD = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(GOTHIC, size)


def ginkgo(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float) -> None:
    """The same ginkgo-leaf mark the site uses as its logo."""
    pts = [
        (50, 8), (42, 30), (20, 44), (8, 50),
        (20, 56), (42, 70), (50, 92),
        (58, 70), (80, 56), (92, 50),
        (80, 44), (58, 30),
    ]
    draw.polygon(
        [(cx + (x - 50) * scale, cy + (y - 50) * scale) for x, y in pts],
        fill=ICHO,
    )


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Soft band behind the portrait so the photo edge is intentional.
    d.rectangle([(W - 430, 0), (W, H)], fill=ICHO_SOFT)
    # Top and bottom rules, echoing the site's header/footer trim.
    d.rectangle([(0, 0), (W, 10)], fill=ICHO)
    d.rectangle([(0, H - 6), (W, H)], fill=ASAGI)

    # Portrait, cropped to the band and bled to the bottom edge.
    src = PUBLIC / "profile.jpg"
    if src.exists():
        photo = Image.open(src).convert("RGB")
        band_w, band_h = 430, H
        ratio = max(band_w / photo.width, band_h / photo.height)
        photo = photo.resize(
            (round(photo.width * ratio), round(photo.height * ratio)),
            Image.LANCZOS,
        )
        left = (photo.width - band_w) // 2
        img.paste(photo.crop((left, 0, left + band_w, band_h)), (W - band_w, 0))

    x = 74
    ginkgo(d, x + 18, 96, 0.52)
    d.text((x + 56, 74), "黒田塾", font=font(GOTHIC_BOLD, 46), fill=INK)

    d.text(
        (x, 170),
        "東大卒・黒田清友の",
        font=font(GOTHIC_BOLD, 54),
        fill=INK,
    )
    d.text(
        (x, 238),
        "オンライン家庭教師",
        font=font(GOTHIC_BOLD, 62),
        fill=INK,
    )
    d.text(
        (x, 314),
        "と受験コーチング",
        font=font(GOTHIC_BOLD, 62),
        fill=INK,
    )

    d.rectangle([(x, 410), (x + 96, 415)], fill=ICHO)

    d.text(
        (x, 448),
        "中学受験・大学受験／オンラインと対面に対応",
        font=font(GOTHIC, 29),
        fill=GREY,
    )
    d.text(
        (x, 497),
        "面談のみ 24,000円／授業のみ 30,000円",
        font=font(GOTHIC_BOLD, 31),
        fill=ASAGI,
    )
    d.text(
        (x, 546),
        "月額・税込／無料相談はオンラインで30分",
        font=font(GOTHIC, 26),
        fill=GREY,
    )

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
