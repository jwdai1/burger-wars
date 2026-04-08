#!/usr/bin/env python3
"""
postprocess.py — Final image processing for both compositions.
- Levels adjustment + sharpening + vignette
- Label and title overlay
Input:  output/tectonic_raw.png, output/siege_raw.png
Output: output/tectonic.png,     output/siege.png
"""
import json
import os
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

OUTPUT_DIR = "output"


def load_font(size):
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def adjust_levels(img, shadows=8, highlights=245, gamma=1.10):
    """Stretch levels: remap [shadows, highlights] → [0, 255] with gamma."""
    img = img.convert("RGB")
    r, g, b = img.split()
    def stretch(ch):
        return ch.point(lambda p: max(0, min(255,
            int(max(0.0, (p - shadows) / max(highlights - shadows, 1)) ** (1/gamma) * 255)
        )))
    return Image.merge("RGB", [stretch(r), stretch(g), stretch(b)])


def sharpen(img, factor=1.4):
    return ImageEnhance.Sharpness(img).enhance(factor)


def add_vignette(img, strength=0.45):
    w, h = img.size
    from PIL import ImageChops
    import math
    # Radial gradient vignette
    vign = Image.new("L", (w, h), 255)
    cx, cy = w // 2, h // 2
    max_dist = math.sqrt(cx**2 + cy**2)
    pixels = []
    for y in range(h):
        row = []
        for x in range(w):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2) / max_dist
            val = int(255 * (1.0 - strength * dist**1.5))
            row.append(max(0, min(255, val)))
        pixels.append(row)
    # Fast approach: use Gaussian blur on a black-border mask
    vign = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(vign)
    steps = 80
    for i in range(steps):
        margin = int(min(w, h) * 0.35 * (i / steps) ** 1.2)
        alpha = int(255 * (1 - (i / steps) ** 0.6 * strength))
        draw.rectangle([margin, margin, w - margin, h - margin], outline=(alpha, alpha, alpha))
    vign = vign.filter(ImageFilter.GaussianBlur(radius=min(w, h) // 6))
    return ImageChops.multiply(img.convert("RGB"), vign)


def add_title_siege(img):
    """Title overlay for Siege Wall."""
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_title = load_font(80)
    font_sub   = load_font(42)

    title    = "McDONALD'S  vs  BURGER KING"
    subtitle = "36,009 stores                    15,207 stores worldwide"

    cx = w // 2
    ty = 55

    # Shadow
    for ox, oy in [(3, 3), (-1, -1)]:
        draw.text((cx + ox, ty + oy),    title,    font=font_title, fill=(0, 0, 0, 160), anchor="mt")
        draw.text((cx + ox, ty + oy + 100), subtitle, font=font_sub, fill=(0, 0, 0, 140), anchor="mt")

    # Text
    draw.text((cx, ty),       title,    font=font_title, fill=(240, 232, 218, 235), anchor="mt")
    draw.text((cx, ty + 100), subtitle, font=font_sub,   fill=(190, 182, 168, 200), anchor="mt")

    return img


def add_labels_tectonic(img):
    """Legend overlay for Tectonic Plates."""
    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_head = load_font(36)
    font_item = load_font(26)

    with open("data/stores.json") as f:
        data = json.load(f)

    countries = data["countries"]
    top10 = sorted(countries.values(), key=lambda c: c["total"], reverse=True)[:10]

    lx = 60
    ly = h - 420
    draw.text((lx, ly - 50), "TOP MARKETS", font=font_head, fill=(210, 200, 188, 200))

    for i, c in enumerate(top10):
        dom = c["dominance"]
        if "mcd" in dom:
            col = (190, 70, 70, 200)
        elif "bk" in dom:
            col = (70, 100, 175, 200)
        else:
            col = (150, 142, 135, 180)
        text = f"{c['name']:20s}  {c['mcd_count']:5,} McD  /  {c['bk_count']:5,} BK"
        draw.text((lx, ly + i * 36), text, font=font_item, fill=col)

    # Title
    draw.text((w // 2, 55), "BURGER WARS", font=load_font(90), fill=(230, 220, 208, 220), anchor="mt")
    draw.text((w // 2, 160), "McDonald's vs Burger King — Global Territory", font=load_font(40), fill=(180, 170, 158, 180), anchor="mt")

    return img


def process(raw_path, out_path, composition):
    if not os.path.exists(raw_path):
        print(f"  Skipping {raw_path} — not found")
        return
    print(f"  Processing {raw_path}...")
    img = Image.open(raw_path).convert("RGB")

    img = adjust_levels(img, shadows=6, highlights=248, gamma=1.15)
    img = sharpen(img, factor=1.3)
    img = add_vignette(img, strength=0.40)

    img = img.convert("RGBA")
    draw_img = img.convert("RGB")

    if composition == "siege":
        draw_img = add_title_siege(draw_img)
    elif composition == "tectonic":
        draw_img = add_labels_tectonic(draw_img)

    draw_img.save(out_path, "PNG", compress_level=6)
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"  → {out_path} ({size_mb:.1f} MB)")


def main():
    print("=== Post-processing ===")
    process(f"{OUTPUT_DIR}/tectonic_raw.png", f"{OUTPUT_DIR}/tectonic.png", "tectonic")
    process(f"{OUTPUT_DIR}/siege_raw.png",    f"{OUTPUT_DIR}/siege.png",    "siege")
    print("Done.")


if __name__ == "__main__":
    main()
