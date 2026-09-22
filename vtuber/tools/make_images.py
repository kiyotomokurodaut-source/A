#!/usr/bin/env python3
"""Derive every web image from the two source artworks in ``art/``.

Run this only when the source art changes::

    pip install pillow
    python3 tools/make_images.py

The output lands in ``assets/img/`` and is committed, so neither the site
build nor the deploy needs Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art"
OUT = ROOT / "assets" / "img"

# Never upscale: the portrait is 906px wide and the key visual 1672px.
PORTRAIT_WIDTHS = (420, 640, 900)
KEYVISUAL_WIDTHS = (800, 1200, 1600)

# The face sits in the upper third of the portrait; crop the avatar around it
# rather than around the geometric centre.
AVATAR_BOX = (135, 200, 835, 900)


def save_webp(im: Image.Image, name: str, quality: int = 86) -> None:
    path = OUT / name
    im.save(path, "WEBP", quality=quality, method=6)
    print(f"  {name:32s} {im.width}x{im.height}  {path.stat().st_size // 1024} KB")


def widths(im: Image.Image, stem: str, sizes: tuple[int, ...], quality: int = 86) -> None:
    for w in sizes:
        if w > im.width:
            continue
        h = round(im.height * w / im.width)
        save_webp(im.resize((w, h), Image.LANCZOS), f"{stem}-{w}.webp", quality)


def rounded_icon(src: Image.Image, size: int) -> Image.Image:
    """Square avatar with a soft night-blue backdrop, for favicons."""
    icon = src.resize((size, size), Image.LANCZOS).convert("RGBA")
    backdrop = Image.new("RGBA", (size, size), (9, 18, 48, 255))
    backdrop.alpha_composite(icon)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * 4 - 1, size * 4 - 1), radius=size, fill=255
    )
    backdrop.putalpha(mask.resize((size, size), Image.LANCZOS))
    return backdrop


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    portrait = Image.open(ART / "portrait.jpg").convert("RGB")
    keyvisual = Image.open(ART / "keyvisual.png").convert("RGB")

    print("portrait ->")
    widths(portrait, "portrait", PORTRAIT_WIDTHS, quality=88)

    print("key visual ->")
    widths(keyvisual, "keyvisual", KEYVISUAL_WIDTHS, quality=84)

    # A heavily blurred, darkened key visual used as a CSS backdrop. Small on
    # purpose: it is never seen sharp.
    print("hero backdrop ->")
    blur = keyvisual.resize((320, 180), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
    blur = Image.blend(blur, Image.new("RGB", blur.size, (6, 11, 34)), 0.45)
    save_webp(blur.resize((1280, 720), Image.LANCZOS), "hero-glow.webp", quality=70)

    print("avatar / icons ->")
    face = portrait.crop(AVATAR_BOX)
    widths(face, "avatar", (240, 480), quality=90)
    for size in (180, 512):
        icon = rounded_icon(face, size)
        icon.save(OUT / f"icon-{size}.png")
        print(f"  icon-{size}.png")
    face.resize((32, 32), Image.LANCZOS).save(OUT / "favicon.png")
    print("  favicon.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
