#!/usr/bin/env python3
"""
generate_siege.py — Composition C: Siege Wall
Packs 40k McD blocks (left) and 18k BK blocks (right) facing a central void.
Output: data/siege_geometry.json
"""
import json
import math
import os
import random
import sys

from common import (
    dominance_to_height, dominance_to_color,
    dominance_strength,
)

DATA_FILE = "data/stores.json"
OUTPUT_FILE = "data/siege_geometry.json"

SCENE_W = 100.0
SCENE_H = 66.7

# The central void (no man's land)
WALL_X = SCENE_W / 2   # Center line
VOID_HALF = 1.0        # Total void width = 2.0 units

# Block size (uniform for all stores)
BLOCK_BASE = 0.30      # Square base width/depth

# Height range
MIN_HEIGHT = 0.2
MAX_HEIGHT = 7.0

# Density gradient
COMPRESSION_NEAR = 0.75   # Tighter packing near wall
COMPRESSION_FAR  = 1.20   # Looser packing at edge

SEED = 42


def pack_side(stores_by_country, side, countries):
    """
    Pack blocks for one side (McD=left, BK=right).
    side: "mcd" or "bk"
    Returns list of block dicts.
    """
    rng = random.Random(SEED + (1 if side == "bk" else 0))

    sorted_countries = sorted(
        stores_by_country.items(),
        key=lambda kv: len(kv[1]),
        reverse=True
    )

    blocks = []

    if side == "mcd":
        x_near = WALL_X - VOID_HALF
        x_far  = 0.0
    else:
        x_near = WALL_X + VOID_HALF
        x_far  = SCENE_W

    x_range = abs(x_near - x_far)

    y_cursor = 0.0
    total_stores = sum(len(s) for _, s in sorted_countries)

    for code, stores in sorted_countries:
        if not stores:
            continue

        country_info = countries.get(code, {})
        dominance = country_info.get("dominance", "contested")

        n = len(stores)
        battalion_h = (n / total_stores) * SCENE_H
        battalion_h = max(battalion_h, BLOCK_BASE * 2)

        y_start = y_cursor
        y_end = min(y_cursor + battalion_h, SCENE_H)
        y_cursor = y_end

        cols_near = max(1, int(x_range * 0.4 / (BLOCK_BASE * COMPRESSION_NEAR)))
        cols_far  = max(1, int(x_range * 0.6 / (BLOCK_BASE * COMPRESSION_FAR)))
        total_cols = cols_near + cols_far

        rows = max(1, int(battalion_h / BLOCK_BASE))

        slots = [(col, row) for col in range(total_cols) for row in range(rows)]
        rng.shuffle(slots)
        used_slots = slots[:n]

        for i, (col, row) in enumerate(used_slots):
            store = stores[i]
            chain = store["chain"]
            strength = dominance_strength(dominance)
            raw_h = dominance_to_height(dominance, chain)
            blender_h = MIN_HEIGHT + raw_h * (MAX_HEIGHT - MIN_HEIGHT)
            color = dominance_to_color(dominance, chain, strength)

            if col < cols_near:
                t = col / max(cols_near - 1, 1)
                if side == "mcd":
                    x = x_near - (1 - t) * (x_range * 0.4)
                else:
                    x = x_near + (1 - t) * (x_range * 0.4)
            else:
                t = (col - cols_near) / max(cols_far - 1, 1)
                if side == "mcd":
                    x = x_near - x_range * 0.4 - t * (x_range * 0.6)
                else:
                    x = x_near + x_range * 0.4 + t * (x_range * 0.6)

            x += rng.uniform(-0.05, 0.05)
            y = y_start + (row / max(rows - 1, 1)) * (y_end - y_start)
            y += rng.uniform(-0.05, 0.05)
            y = max(0, min(SCENE_H, y))

            blocks.append({
                "x": round(x, 4),
                "y": round(y, 4),
                "height": round(blender_h, 3),
                "color": list(color),
                "chain": chain,
                "country": code,
                "dominance": dominance,
            })

    return blocks


def main():
    print("=== Generating Siege Wall geometry ===")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run data/fetch_osm.py first.")
        sys.exit(1)
    with open(DATA_FILE) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: {DATA_FILE} is not valid JSON: {e}")
            sys.exit(1)

    stores = data["stores"]
    countries = data["countries"]

    mcd_stores = [s for s in stores if s["chain"] == "mcd"]
    bk_stores  = [s for s in stores if s["chain"] == "bk"]
    print(f"McD: {len(mcd_stores):,}  BK: {len(bk_stores):,}")

    def group_by_country(store_list):
        clusters = {}
        for s in store_list:
            c = s["country"]
            if c not in clusters:
                clusters[c] = []
            clusters[c].append(s)
        return clusters

    mcd_by_country = group_by_country(mcd_stores)
    bk_by_country  = group_by_country(bk_stores)

    print("Packing McD blocks (left side)...")
    mcd_blocks = pack_side(mcd_by_country, "mcd", countries)

    print("Packing BK blocks (right side)...")
    bk_blocks = pack_side(bk_by_country, "bk", countries)

    all_blocks = mcd_blocks + bk_blocks
    print(f"Total blocks: {len(all_blocks):,}")

    output = {
        "blocks": all_blocks,
        "scene": {
            "width": SCENE_W,
            "height": SCENE_H,
            "wall_x": WALL_X,
            "void_half": VOID_HALF,
            "block_base": BLOCK_BASE,
            "max_height": MAX_HEIGHT,
        },
        "summary": {
            "mcd_blocks": len(mcd_blocks),
            "bk_blocks":  len(bk_blocks),
            "total":      len(all_blocks),
        }
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)

    print(f"Written to {OUTPUT_FILE}")
    print(f"McD: {len(mcd_blocks):,}  BK: {len(bk_blocks):,}")


if __name__ == "__main__":
    main()
