#!/usr/bin/env python3
"""
generate_tectonic.py — Composition B: Tectonic Plates
Computes per-tile geometry for ~58,000 store tiles.
Output: data/tectonic_geometry.json (consumed by blend_tectonic.py)
"""
import json
import math
import os
import random
import sys

from common import (
    squarify, perlin_noise,
    classify_dominance, dominance_to_height, dominance_to_color,
    dominance_strength,
)

DATA_FILE = "data/stores.json"
OUTPUT_FILE = "data/tectonic_geometry.json"

# Scene dimensions (Blender units, camera will frame these)
SCENE_W = 100.0
SCENE_H = 66.7   # 3:2 aspect for 6000x4000

# Height range in Blender units
MIN_HEIGHT = 0.1
MAX_HEIGHT = 8.0

# Fault line gap between different-dominance clusters
FAULT_GAP = 0.15

# Perlin noise scale for edge displacement
NOISE_SCALE = 0.3
NOISE_AMPLITUDE = 0.4

SEED = 42


def build_country_clusters(stores, countries):
    """
    Group stores by country. Returns dict: country_code → list of stores.
    Sorted by total store count descending (largest countries first in treemap).
    """
    clusters = {}
    for s in stores:
        code = s["country"]
        if code not in clusters:
            clusters[code] = []
        clusters[code].append(s)

    sorted_clusters = dict(
        sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)
    )
    return sorted_clusters


def displace_rect_edges(x, y, w, h, seed_x, seed_y):
    """
    Apply Perlin noise to the four edges of a rectangle to make it slightly organic.
    Returns list of (vx, vy) tuples forming a polygon (8 points: 2 per edge midpoint).
    """
    def noise_offset(px, py):
        n = perlin_noise(px * NOISE_SCALE, py * NOISE_SCALE, seed=SEED)
        return n * NOISE_AMPLITUDE

    mid_top    = (x + w/2,     y + h + noise_offset(seed_x, seed_y + 1))
    mid_bottom = (x + w/2,     y     + noise_offset(seed_x, seed_y - 1))
    mid_left   = (x     + noise_offset(seed_x - 1, seed_y), y + h/2)
    mid_right  = (x + w + noise_offset(seed_x + 1, seed_y), y + h/2)

    return [
        (x,     y),
        (mid_bottom[0], mid_bottom[1]),
        (x + w, y),
        (mid_right[0],  mid_right[1]),
        (x + w, y + h),
        (mid_top[0],    mid_top[1]),
        (x,     y + h),
        (mid_left[0],   mid_left[1]),
    ]


def uniform_grid_layout(n, x, y, w, h):
    """
    Fast O(n) grid layout for n equal-sized items in a rectangle.
    Returns list of {x, y, w, h} dicts.
    Chooses cols/rows to minimize aspect ratio distortion.
    """
    if n == 0:
        return []
    if n == 1:
        return [{'x': x, 'y': y, 'w': w, 'h': h}]

    # Find best cols/rows to approximate the rect aspect ratio
    aspect = w / h if h > 0 else 1.0
    cols = max(1, round(math.sqrt(n * aspect)))
    rows = math.ceil(n / cols)
    # Adjust if we overshoot
    while cols * rows < n:
        cols += 1

    cell_w = w / cols
    cell_h = h / rows

    rects = []
    for idx in range(n):
        col = idx % cols
        row = idx // cols
        rects.append({
            'x': x + col * cell_w,
            'y': y + row * cell_h,
            'w': cell_w,
            'h': cell_h,
        })
    return rects


def compute_tiles(stores, countries):
    """
    Returns list of tile dicts, one per store:
    {
        vertices: [(x,y), ...],  # 2D polygon footprint (8 points)
        height: float,            # extrusion height in Blender units
        color: [r,g,b],           # 0-255
        chain: "mcd"|"bk",
        country: str,
        dominance: str,
    }
    """
    clusters = build_country_clusters(stores, countries)
    country_sizes = [len(v) for v in clusters.values()]
    country_codes = list(clusters.keys())

    # Layout country blocks via treemap
    print("  Computing country-level treemap...")
    rects = squarify(country_sizes, x=0, y=0, width=SCENE_W, height=SCENE_H)
    print(f"  Country layout done: {len(rects)} rects")

    tiles = []

    for i, (rect, code) in enumerate(zip(rects, country_codes)):
        if i % 10 == 0:
            print(f"  Processing country {i+1}/{len(rects)}: {code} ({len(clusters[code])} stores)...")

        country_stores = clusters[code]
        n = len(country_stores)
        if n == 0:
            continue

        rx, ry, rw, rh = rect['x'], rect['y'], rect['w'], rect['h']
        country_info = countries.get(code, {})
        dominance = country_info.get("dominance", "contested")

        # Subtract fault gap from edges for visual separation
        rx += FAULT_GAP / 2
        ry += FAULT_GAP / 2
        rw -= FAULT_GAP
        rh -= FAULT_GAP
        if rw <= 0 or rh <= 0:
            continue

        # Use fast uniform grid for sub-tiles (all stores have equal weight)
        sub_rects = uniform_grid_layout(n, rx, ry, rw, rh)

        for sub_rect, store in zip(sub_rects, country_stores):
            sx = sub_rect['x']
            sy = sub_rect['y']
            sw = sub_rect['w']
            sh = sub_rect['h']

            if sw < 0.001 or sh < 0.001:
                continue

            chain = store["chain"]
            strength = dominance_strength(dominance)
            raw_h = dominance_to_height(dominance, chain)
            blender_h = MIN_HEIGHT + raw_h * (MAX_HEIGHT - MIN_HEIGHT)

            color = dominance_to_color(dominance, chain, strength)

            verts = displace_rect_edges(
                sx, sy, sw, sh,
                seed_x=sx * 0.5,
                seed_y=sy * 0.5
            )

            tiles.append({
                "vertices": verts,
                "height": round(blender_h, 3),
                "color": list(color),
                "chain": chain,
                "country": code,
                "dominance": dominance,
            })

    return tiles


def main():
    print("=== Generating Tectonic Plates geometry ===")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run data/fetch_osm.py first.")
        sys.exit(1)
    with open(DATA_FILE) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: {DATA_FILE} is not valid JSON: {e}")
            sys.exit(1)
    if "stores" not in data or "countries" not in data:
        print(f"Error: {DATA_FILE} is missing 'stores' or 'countries' keys. Re-run data/fetch_osm.py.")
        sys.exit(1)

    stores = data["stores"]
    countries = data["countries"]

    print(f"Processing {len(stores):,} stores across {len(countries)} countries...")
    tiles = compute_tiles(stores, countries)
    print(f"Generated {len(tiles):,} tiles")

    output = {
        "tiles": tiles,
        "scene": {"width": SCENE_W, "height": SCENE_H, "max_height": MAX_HEIGHT},
        "summary": {
            "tile_count": len(tiles),
            "mcd_tiles": sum(1 for t in tiles if t["chain"] == "mcd"),
            "bk_tiles": sum(1 for t in tiles if t["chain"] == "bk"),
        }
    }

    print(f"Writing to {OUTPUT_FILE}...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)

    print(f"Done. McD: {output['summary']['mcd_tiles']:,}, BK: {output['summary']['bk_tiles']:,}")


if __name__ == "__main__":
    main()
