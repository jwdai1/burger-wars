#!/usr/bin/env python3
"""
generate_lightmap.py — Territory Light Map
51,216 McDonald's and Burger King stores rendered as additive light accumulation.
Each store is a Gaussian glow blob. Dense areas burn bright.
Continents emerge from store distribution alone — no borders, no outlines.

Output: output/lightmap_raw.png (6000x4000)
"""
import json
import math
import os
import time

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# ── Canvas ────────────────────────────────────────────────────────────────────
WIDTH   = 6000
HEIGHT  = 4000

# ── Glow parameters ───────────────────────────────────────────────────────────
# Sigma in pixels — small point + heavy bloom applied later
POINT_SIGMA   = 3.5     # tight core Gaussian per store
BLOOM_SIGMA_1 = 18.0    # first bloom pass (tight halo)
BLOOM_SIGMA_2 = 60.0    # second bloom pass (wide atmospheric glow)
BLOOM_MIX_1   = 0.55    # weight of tight bloom
BLOOM_MIX_2   = 0.30    # weight of wide bloom

# ── Brand colors ──────────────────────────────────────────────────────────────
MCD_COLOR = np.array([1.00, 0.27, 0.00], dtype=np.float32)   # red-orange
BK_COLOR  = np.array([0.00, 0.47, 1.00], dtype=np.float32)   # electric blue

# Overlap hotspots (both chains dense → warm white/yellow)
# Handled naturally by additive blending

# ── Tone mapping ──────────────────────────────────────────────────────────────
EXPOSURE  = 2.8   # overall brightness multiplier before tone map
GAMMA     = 1.9   # output gamma


def mercator_to_pixel(lat: float, lon: float):
    """
    Web Mercator (EPSG:3857) → pixel coordinates.
    Longitude -180..180 → 0..WIDTH
    Latitude clipped to ±85.05°, projected nonlinearly → 0..HEIGHT
    """
    x = (lon + 180.0) / 360.0 * WIDTH

    lat_rad = math.radians(lat)
    # Clamp to avoid infinity at poles
    lat_rad = max(-1.484, min(1.484, lat_rad))
    merc_y = math.log(math.tan(math.pi / 4 + lat_rad / 2))
    # merc_y in range [-π, π], map to [HEIGHT, 0] (north = top)
    y = (1.0 - merc_y / math.pi) * HEIGHT / 2.0

    return x, y


def splat_gaussian(canvas: np.ndarray, x: float, y: float,
                   color: np.ndarray, sigma: float):
    """
    Add a Gaussian blob of given color to the float32 canvas.
    Uses a small kernel stamped at (x, y) — fast per-store.
    """
    r = int(sigma * 3.5)
    ix, iy = int(round(x)), int(round(y))

    # Kernel bounds
    x0 = max(0, ix - r)
    x1 = min(WIDTH,  ix + r + 1)
    y0 = max(0, iy - r)
    y1 = min(HEIGHT, iy + r + 1)

    if x0 >= x1 or y0 >= y1:
        return

    # Gaussian kernel (relative to store center)
    kx = np.arange(x0, x1) - x
    ky = np.arange(y0, y1) - y
    gx = np.exp(-0.5 * (kx / sigma) ** 2)
    gy = np.exp(-0.5 * (ky / sigma) ** 2)
    kernel = np.outer(gy, gx)   # (h, w)

    canvas[y0:y1, x0:x1, 0] += kernel * color[0]
    canvas[y0:y1, x0:x1, 1] += kernel * color[1]
    canvas[y0:y1, x0:x1, 2] += kernel * color[2]


def tone_map_aces(x: np.ndarray) -> np.ndarray:
    """
    ACES filmic tone mapping — preserves color saturation in bright regions.
    Input: linear HDR float (any positive value)
    Output: [0, 1] LDR
    """
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0)


def main():
    t0 = time.time()
    print("=== Territory Light Map ===")

    print("Loading store data...")
    with open("data/stores.json") as f:
        data = json.load(f)
    stores = data["stores"]
    print(f"  {len(stores):,} stores loaded")

    mcd_stores = [s for s in stores if s["chain"] == "mcd"]
    bk_stores  = [s for s in stores if s["chain"] == "bk"]
    print(f"  McDonald's: {len(mcd_stores):,}  |  Burger King: {len(bk_stores):,}")

    # ── Accumulation buffers (float32, no saturation) ─────────────────────────
    print("Allocating canvas...")
    mcd_buf = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    bk_buf  = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)

    # ── Splat stores ──────────────────────────────────────────────────────────
    print(f"Splatting {len(mcd_stores):,} McDonald's stores...")
    t1 = time.time()
    skipped = 0
    for i, s in enumerate(mcd_stores):
        try:
            x, y = mercator_to_pixel(s["lat"], s["lon"])
        except (ValueError, KeyError):
            skipped += 1
            continue
        splat_gaussian(mcd_buf, x, y, MCD_COLOR, POINT_SIGMA)
        if i % 10000 == 0:
            print(f"  MCD {i:,}/{len(mcd_stores):,}  ({time.time()-t1:.1f}s)")
    print(f"  Done. Skipped: {skipped}")

    print(f"Splatting {len(bk_stores):,} Burger King stores...")
    t1 = time.time()
    skipped = 0
    for i, s in enumerate(bk_stores):
        try:
            x, y = mercator_to_pixel(s["lat"], s["lon"])
        except (ValueError, KeyError):
            skipped += 1
            continue
        splat_gaussian(bk_buf, x, y, BK_COLOR, POINT_SIGMA)
        if i % 5000 == 0:
            print(f"  BK {i:,}/{len(bk_stores):,}  ({time.time()-t1:.1f}s)")
    print(f"  Done. Skipped: {skipped}")

    # ── Bloom passes ──────────────────────────────────────────────────────────
    print("Applying bloom...")

    def bloom(buf: np.ndarray) -> np.ndarray:
        """Two-pass Gaussian bloom added back to original."""
        b1 = gaussian_filter(buf, sigma=[BLOOM_SIGMA_1, BLOOM_SIGMA_1, 0])
        b2 = gaussian_filter(buf, sigma=[BLOOM_SIGMA_2, BLOOM_SIGMA_2, 0])
        return buf + BLOOM_MIX_1 * b1 + BLOOM_MIX_2 * b2

    print("  Blooming McDonald's buffer...")
    mcd_bloom = bloom(mcd_buf)
    print("  Blooming Burger King buffer...")
    bk_bloom  = bloom(bk_buf)

    # ── Combine channels ──────────────────────────────────────────────────────
    print("Compositing...")
    canvas = mcd_bloom + bk_bloom   # additive — overlap becomes white/yellow

    # ── Tone mapping ──────────────────────────────────────────────────────────
    print("Tone mapping...")
    canvas *= EXPOSURE
    canvas = tone_map_aces(canvas)

    # ── Gamma ─────────────────────────────────────────────────────────────────
    canvas = np.power(np.clip(canvas, 0, 1), 1.0 / GAMMA)

    # ── Convert to uint8 ─────────────────────────────────────────────────────
    img_arr = (canvas * 255).clip(0, 255).astype(np.uint8)

    os.makedirs("output", exist_ok=True)
    out_path = "output/lightmap_raw.png"
    print(f"Saving {out_path}...")
    img = Image.fromarray(img_arr, "RGB")
    img.save(out_path)

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s → {out_path}")


if __name__ == "__main__":
    main()
