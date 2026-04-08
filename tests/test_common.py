import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from common import (
    classify_dominance,
    dominance_to_height,
    dominance_to_color,
    squarify,
    perlin_noise,
)

# ── dominance classification ──────────────────────────────────────────

def test_classify_mcd_dominant():
    assert classify_dominance(0.85, 0.15) == "mcd_dominant"

def test_classify_mcd_advantage():
    assert classify_dominance(0.60, 0.40) == "mcd_advantage"

def test_classify_contested():
    assert classify_dominance(0.50, 0.50) == "contested"

def test_classify_bk_advantage():
    assert classify_dominance(0.38, 0.62) == "bk_advantage"

def test_classify_bk_dominant():
    assert classify_dominance(0.20, 0.80) == "bk_dominant"

# ── height mapping ────────────────────────────────────────────────────

def test_height_mcd_dominant_mcd_store():
    h = dominance_to_height("mcd_dominant", "mcd")
    assert 0.8 <= h <= 1.0

def test_height_bk_store_in_mcd_dominant():
    h = dominance_to_height("mcd_dominant", "bk")
    assert 0.0 <= h <= 0.2

def test_height_contested():
    h = dominance_to_height("contested", "mcd")
    assert 0.35 <= h <= 0.65

# ── color mapping ─────────────────────────────────────────────────────

def test_color_mcd_dominant_returns_crimson_family():
    r, g, b = dominance_to_color("mcd_dominant", "mcd", strength=1.0)
    assert r > g and r > b

def test_color_bk_dominant_returns_blue_family():
    r, g, b = dominance_to_color("bk_dominant", "bk", strength=1.0)
    assert b > r

def test_color_contested_is_desaturated():
    r, g, b = dominance_to_color("contested", "mcd", strength=0.0)
    spread = max(r, g, b) - min(r, g, b)
    assert spread < 60

def test_color_returns_0_255_range():
    r, g, b = dominance_to_color("mcd_advantage", "mcd", strength=0.6)
    assert all(0 <= c <= 255 for c in (r, g, b))

# ── squarified treemap ────────────────────────────────────────────────

def test_squarify_total_area():
    sizes = [10, 5, 3, 2]
    rects = squarify(sizes, x=0, y=0, width=100, height=20)
    total = sum(r['w'] * r['h'] for r in rects)
    assert abs(total - 100 * 20) < 1.0

def test_squarify_count():
    sizes = [10, 5, 3]
    rects = squarify(sizes, x=0, y=0, width=100, height=100)
    assert len(rects) == 3

def test_squarify_no_overlap():
    sizes = [30, 20, 15, 10, 5]
    rects = squarify(sizes, x=0, y=0, width=100, height=100)
    for i, a in enumerate(rects):
        for j, b in enumerate(rects):
            if i == j:
                continue
            overlap_x = not (a['x'] + a['w'] <= b['x'] or b['x'] + b['w'] <= a['x'])
            overlap_y = not (a['y'] + a['h'] <= b['y'] or b['y'] + b['h'] <= a['y'])
            assert not (overlap_x and overlap_y), f"Rects {i} and {j} overlap"

# ── perlin noise ──────────────────────────────────────────────────────

def test_perlin_returns_float():
    v = perlin_noise(1.5, 2.3, seed=42)
    assert isinstance(v, float)

def test_perlin_range():
    values = [perlin_noise(x * 0.1, y * 0.1, seed=0) for x in range(20) for y in range(20)]
    assert all(-1.5 <= v <= 1.5 for v in values)

def test_perlin_deterministic():
    assert perlin_noise(1.0, 2.0, seed=99) == perlin_noise(1.0, 2.0, seed=99)
