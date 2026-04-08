"""
common.py — Shared utilities for Burger Wars data art.
"""
import functools
import math
import random


# ════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════

WIDTH = 6000
HEIGHT = 4000

# McDonald's palette (deep crimson / burnt gold)
MCD_PRIMARY   = (139, 26, 26)    # #8B1A1A deep crimson
MCD_SECONDARY = (184, 134, 11)   # #B8860B burnt gold
MCD_HIGHLIGHT = (205, 51, 51)    # #CD3333 vivid crimson
MCD_SHADOW    = (74, 14, 14)     # #4A0E0E dark maroon

# Burger King palette (midnight blue / bronze orange)
BK_PRIMARY    = (27, 42, 74)     # #1B2A4A midnight blue
BK_SECONDARY  = (205, 127, 50)   # #CD7F32 bronze orange
BK_HIGHLIGHT  = (46, 74, 122)    # #2E4A7A bright blue
BK_SHADOW     = (13, 21, 32)     # #0D1520 deep navy

CONTESTED_COLOR = (105, 95, 88)  # Muted grey-brown


# ════════════════════════════════════════════════════════════════════
# DOMINANCE LOGIC
# ════════════════════════════════════════════════════════════════════

def classify_dominance(mcd_ratio: float, bk_ratio: float) -> str:
    """Classify a country's dominance category based on share ratios."""
    if mcd_ratio > 0.70:
        return "mcd_dominant"
    elif mcd_ratio > 0.55:
        return "mcd_advantage"
    elif bk_ratio > 0.70:
        return "bk_dominant"
    elif bk_ratio > 0.55:
        return "bk_advantage"
    else:
        return "contested"


def dominance_to_height(dominance: str, chain: str) -> float:
    """
    Map dominance category + chain to normalized height [0.0, 1.0].
    A store rises high when its chain dominates that country.
    """
    height_map = {
        ("mcd_dominant",  "mcd"): 0.90,
        ("mcd_dominant",  "bk"):  0.10,
        ("mcd_advantage", "mcd"): 0.65,
        ("mcd_advantage", "bk"):  0.30,
        ("contested",     "mcd"): 0.50,
        ("contested",     "bk"):  0.50,
        ("bk_advantage",  "mcd"): 0.30,
        ("bk_advantage",  "bk"):  0.65,
        ("bk_dominant",   "mcd"): 0.10,
        ("bk_dominant",   "bk"):  0.90,
    }
    return height_map.get((dominance, chain), 0.50)


def dominance_to_color(dominance: str, chain: str, strength: float) -> tuple:
    """
    Map dominance + chain + strength to RGB tuple.
    strength: 0.0 (contested/muted) -> 1.0 (dominant/vivid)
    """
    def lerp_color(a, b, t):
        return tuple(max(0, min(255, int(a[i] + (b[i] - a[i]) * t))) for i in range(3))

    if dominance == "contested":
        return CONTESTED_COLOR

    if chain == "mcd":
        base = MCD_PRIMARY
        vivid = MCD_HIGHLIGHT
    else:
        base = BK_PRIMARY
        vivid = BK_HIGHLIGHT

    return lerp_color(base, vivid, strength)


def dominance_strength(dominance: str) -> float:
    """Return 0.0-1.0 visual strength for a dominance category."""
    return {
        "mcd_dominant":  1.0,
        "mcd_advantage": 0.6,
        "contested":     0.0,
        "bk_advantage":  0.6,
        "bk_dominant":   1.0,
    }.get(dominance, 0.0)


# ════════════════════════════════════════════════════════════════════
# SQUARIFIED TREEMAP
# ════════════════════════════════════════════════════════════════════

def squarify(sizes: list, x: float, y: float, width: float, height: float) -> list:
    """
    Squarified treemap layout (iterative).
    Returns list of dicts: {x, y, w, h, index}
    sizes: list of positive numbers (proportional areas)
    """
    if not sizes:
        return []

    total = sum(sizes)
    if total == 0:
        return []

    area = width * height
    normalized = [s / total * area for s in sizes]
    indices = list(range(len(sizes)))

    rects = []
    # Stack holds (sizes_slice, indices_slice, x, y, w, h)
    stack = [(normalized, indices, x, y, width, height)]

    while stack:
        cur_sizes, cur_indices, cx, cy, cw, ch = stack.pop()

        if not cur_sizes:
            continue
        if len(cur_sizes) == 1:
            rects.append({'x': cx, 'y': cy, 'w': cw, 'h': ch, 'index': cur_indices[0]})
            continue

        if cw >= ch:
            # Split horizontally into columns
            best_ratio = float('inf')
            split = 1
            col_area = 0
            for i in range(1, len(cur_sizes) + 1):
                col_area += cur_sizes[i - 1]
                col_w = col_area / ch if ch > 0 else 0
                worst = max(
                    (col_w * col_w / (s / ch) if ch > 0 and s > 0 else float('inf'))
                    for s in cur_sizes[:i]
                )
                if worst < best_ratio:
                    best_ratio = worst
                    split = i

            col_area = sum(cur_sizes[:split])
            col_w = col_area / ch if ch > 0 else 0

            new_cy = cy
            for i in range(split):
                cell_h = cur_sizes[i] / col_w if col_w > 0 else 0
                rects.append({'x': cx, 'y': new_cy, 'w': col_w, 'h': cell_h, 'index': cur_indices[i]})
                new_cy += cell_h

            if cur_sizes[split:]:
                stack.append((cur_sizes[split:], cur_indices[split:], cx + col_w, cy, cw - col_w, ch))
        else:
            # Split vertically into rows
            best_ratio = float('inf')
            split = 1
            row_area = 0
            for i in range(1, len(cur_sizes) + 1):
                row_area += cur_sizes[i - 1]
                row_h = row_area / cw if cw > 0 else 0
                worst = max(
                    (row_h * row_h / (s / cw) if cw > 0 and s > 0 else float('inf'))
                    for s in cur_sizes[:i]
                )
                if worst < best_ratio:
                    best_ratio = worst
                    split = i

            row_area = sum(cur_sizes[:split])
            row_h = row_area / cw if cw > 0 else 0

            new_cx = cx
            for i in range(split):
                cell_w = cur_sizes[i] / row_h if row_h > 0 else 0
                rects.append({'x': new_cx, 'y': cy, 'w': cell_w, 'h': row_h, 'index': cur_indices[i]})
                new_cx += cell_w

            if cur_sizes[split:]:
                stack.append((cur_sizes[split:], cur_indices[split:], cx, cy + row_h, cw, ch - row_h))

    return rects


# ════════════════════════════════════════════════════════════════════
# PERLIN NOISE
# ════════════════════════════════════════════════════════════════════

@functools.lru_cache(maxsize=None)
def _build_perm(seed: int) -> tuple:
    rng = random.Random(seed)
    perm = list(range(256))
    rng.shuffle(perm)
    doubled = perm * 2
    return tuple(doubled)  # tuple for lru_cache (must be hashable)


def perlin_noise(x: float, y: float, seed: int = 0) -> float:
    """
    Simple 2D gradient noise. Returns value roughly in [-1, 1].
    Deterministic for given (x, y, seed). Permutation table cached per seed.
    """
    def _grad(h, dx, dy):
        h = h & 3
        if h == 0: return  dx + dy
        if h == 1: return -dx + dy
        if h == 2: return  dx - dy
        return -dx - dy

    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(a, b, t):
        return a + t * (b - a)

    perm = _build_perm(seed)

    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)

    u = _fade(xf)
    v = _fade(yf)

    aa = perm[perm[xi] + yi]
    ab = perm[perm[xi] + yi + 1]
    ba = perm[perm[xi + 1] + yi]
    bb = perm[perm[xi + 1] + yi + 1]

    return _lerp(
        _lerp(_grad(aa, xf,     yf),     _grad(ba, xf - 1, yf),     u),
        _lerp(_grad(ab, xf,     yf - 1), _grad(bb, xf - 1, yf - 1), u),
        v
    )
