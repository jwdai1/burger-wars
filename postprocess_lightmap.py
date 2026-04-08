#!/usr/bin/env python3
"""
postprocess_lightmap.py — Territory Light Map post-processing
Adds vignette, sharpening, title overlay, and legend.
Input:  output/lightmap_raw.png
Output: output/lightmap.png
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INPUT_PNG  = "output/lightmap_raw.png"
OUTPUT_PNG = "output/lightmap.png"
WIDTH, HEIGHT = 6000, 4000


# ── Mercator (mirrors generate_lightmap.py exactly) ──────────────────────────
def mercator_to_pixel(lat: float, lon: float):
    x = (lon + 180.0) / 360.0 * WIDTH
    lat_rad = math.radians(lat)
    lat_rad = max(-1.484, min(1.484, lat_rad))
    merc_y = math.log(math.tan(math.pi / 4 + lat_rad / 2))
    y = (1.0 - merc_y / math.pi) * HEIGHT / 2.0
    return x, y


def add_vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    """Radial vignette — darkens edges to focus on center."""
    arr = np.array(img).astype(np.float32) / 255.0
    h, w = arr.shape[:2]
    cx, cy = w / 2, h / 2
    Y, X = np.mgrid[0:h, 0:w]
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    vignette = 1.0 - strength * np.clip(dist, 0, 1) ** 1.5
    arr *= vignette[:, :, np.newaxis]
    return Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8), "RGB")


def add_subtle_sharpen(img: Image.Image, amount: float = 0.4) -> Image.Image:
    """Unsharp mask — brings out micro-detail."""
    blurred = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    arr  = np.array(img,     dtype=np.float32)
    blur = np.array(blurred, dtype=np.float32)
    sharpened = arr + amount * (arr - blur)
    return Image.fromarray(sharpened.clip(0, 255).astype(np.uint8), "RGB")


def get_font(size: int, bold: bool = False):
    """Try system fonts; fall back to PIL default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def add_title(draw: ImageDraw.Draw, width: int, height: int):
    """Bottom-center title: chain names + store counts."""
    # Main title
    font_lg = get_font(120, bold=True)
    font_sm = get_font(54)

    title = "McDONALD'S  vs  BURGER KING"
    sub   = "36,009                           15,207 stores"

    # Shadow pass then text
    tx = width // 2
    ty = height - 280

    # Draw glow behind title
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 0)]:
        draw.text((tx + dx, ty + dy), title, font=font_lg,
                  fill=(255, 140, 0, 60), anchor="ms")

    draw.text((tx, ty), title, font=font_lg,
              fill=(230, 230, 230, 220), anchor="ms")

    draw.text((tx, ty + 100), sub, font=font_sm,
              fill=(160, 160, 160, 180), anchor="ms")

    # Colored sub-labels for each chain
    left_label  = "36,009"
    right_label = "15,207 stores"
    draw.text((tx - 540, ty + 100), left_label,  font=font_sm,
              fill=(255, 100, 30, 220), anchor="ms")
    draw.text((tx + 60, ty + 100), right_label, font=font_sm,
              fill=(40, 140, 255, 220), anchor="ms")


def add_country_labels(draw: ImageDraw.Draw, countries_data: dict):
    """
    Label top-10 countries by total store count.
    Position labels at the centroid of their store cluster.
    """
    font = get_font(46)
    font_sm = get_font(34)

    # Sort by total
    ranked = sorted(
        countries_data.items(),
        key=lambda kv: kv[1]["mcd_count"] + kv[1]["bk_count"],
        reverse=True
    )[:10]

    # Approximate centroids for major markets (Mercator px)
    centroids = {
        "US":  (37.5,   -95.0),   # CONUS center
        "CN":  (35.5,   104.0),
        "JP":  (37.0,   137.0),
        "DE":  (51.0,    10.0),
        "FR":  (46.5,     2.5),
        "GB":  (53.0,    -2.0),
        "CA":  (56.0,   -96.0),
        "BR":  (-14.0,  -51.0),
        "AU":  (-25.0,  134.0),
        "KR":  (37.0,   128.0),
        "RU":  (60.0,    60.0),
        "ES":  (40.0,    -4.0),
        "IT":  (43.0,    12.0),
        "PL":  (52.0,    19.0),
        "MX":  (24.0,  -102.0),
        "IN":  (20.0,    79.0),
        "NL":  (52.3,     5.3),
        "SE":  (60.0,    18.0),
        "TR":  (39.0,    35.0),
        "TH":  (15.0,   101.0),
    }

    for code, stats in ranked:
        if code not in centroids:
            continue
        lat, lon = centroids[code]
        x, y = mercator_to_pixel(lat, lon)

        total = stats["mcd_count"] + stats["bk_count"]
        label = f"{stats['name']}\n{total:,}"

        mcd_r = stats["mcd_count"] / total if total else 0.5
        # Color: McD-dominant=warm, BK-dominant=cool, contested=grey
        if mcd_r > 0.65:
            color = (255, 130, 60, 200)
        elif mcd_r < 0.35:
            color = (60, 160, 255, 200)
        else:
            color = (200, 200, 200, 180)

        # Subtle shadow
        for dx, dy in [(-1, 1), (1, 1)]:
            draw.text((x + dx, y + dy), label, font=font_sm,
                      fill=(0, 0, 0, 120), anchor="mm")
        draw.text((x, y), label, font=font, fill=color, anchor="mm")


def main():
    print("=== Lightmap Post-Processing ===")

    print("Loading raw render...")
    img = Image.open(INPUT_PNG).convert("RGB")
    print(f"  {img.width}×{img.height}")

    print("Vignette...")
    img = add_vignette(img, strength=0.5)

    print("Sharpening...")
    img = add_subtle_sharpen(img, amount=0.35)

    print("Loading country data for labels...")
    with open("data/stores.json") as f:
        data = json.load(f)
    countries = data.get("countries", {})

    print("Adding labels and title...")
    draw = ImageDraw.Draw(img, "RGBA")
    add_country_labels(draw, countries)
    add_title(draw, img.width, img.height)

    # Flatten RGBA operations back to RGB
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    print(f"Saving {OUTPUT_PNG}...")
    img.save(OUTPUT_PNG, quality=95)
    print(f"Done → {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
