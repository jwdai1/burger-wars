#!/usr/bin/env python3
"""
render_siege_mgl.py — Composition C: Siege Wall
Renders 50k rectangular block prisms using moderngl.
Output: output/siege_raw.png (6000x4000)
"""
import json
import math
import os
import sys
import time

import numpy as np
import moderngl
from PIL import Image

from render_common_mgl import (
    perspective, look_at, orthographic, mat_mul,
    build_box_verts,
    SHADOW_VERT, SHADOW_FRAG, MAIN_VERT, MAIN_FRAG,
    create_context_and_fbo, create_shadow_fbo, render_to_image,
)

GEOM_FILE  = "data/siege_geometry.json"
OUTPUT_PNG = "output/siege_raw.png"
WIDTH, HEIGHT = 6000, 4000
SHADOW_SIZE   = 4096


def build_geometry(blocks, block_base):
    half = block_base / 2
    print(f"  Building geometry for {len(blocks):,} blocks...")
    chunks = []
    for blk in blocks:
        chunk = build_box_verts(blk["x"], blk["y"], half, blk["height"], blk["color"])
        chunks.append(chunk)
    all_verts = np.concatenate(chunks, axis=0).reshape(-1, 9)
    print(f"  Vertices: {len(all_verts):,}")
    return all_verts


def main():
    t0 = time.time()
    print("=== Siege Wall — moderngl renderer ===")

    if not os.path.exists(GEOM_FILE):
        print(f"Error: {GEOM_FILE} not found. Run generate_siege.py first.")
        sys.exit(1)

    print("Loading geometry...")
    with open(GEOM_FILE) as f:
        geom = json.load(f)

    blocks     = geom["blocks"]
    scene      = geom["scene"]
    SW, SH     = scene["width"], scene["height"]
    wall_x     = scene["wall_x"]
    block_base = scene["block_base"]

    # ── Build VBO ─────────────────────────────────────────────────────────────
    all_verts = build_geometry(blocks, block_base)

    # ── OpenGL context ────────────────────────────────────────────────────────
    print("Creating OpenGL context...")
    ctx, fbo = create_context_and_fbo(WIDTH, HEIGHT)
    shadow_fbo, shadow_tex = create_shadow_fbo(ctx, SHADOW_SIZE)

    vbo = ctx.buffer(all_verts.astype('f4').tobytes())

    shadow_prog = ctx.program(vertex_shader=SHADOW_VERT, fragment_shader=SHADOW_FRAG)
    main_prog   = ctx.program(vertex_shader=MAIN_VERT,   fragment_shader=MAIN_FRAG)

    shadow_vao = ctx.vertex_array(shadow_prog, [(vbo, '3f 3x4 3x4', 'in_position')])
    main_vao   = ctx.vertex_array(main_prog,   [(vbo, '3f 3f 3f',   'in_position', 'in_normal', 'in_color')])

    # ── Camera: low frontal — wall fills frame, block heights dramatic ────────
    cx = wall_x  # 50
    cy = SH / 2  # 33.35

    # Eye 35 units south, 15 units up → ~23° elevation; tight frame fills with geometry
    eye    = (cx, cy - 35, 15)
    center = (cx, cy,       3)
    up     = (0.0, 1.0,   0.0)

    view = look_at(eye, center, up)
    proj = perspective(72, WIDTH / HEIGHT, 1.0, 300.0)
    mvp  = proj @ view

    # ── Lighting: angled from upper-front-left, side-lights the wall ─────────
    lx, ly, lz = cx - 30, cy - 60, 70
    light_view = look_at((lx, ly, lz), (cx, cy, 0), (0, 1, 0))
    light_proj = orthographic(-80, 80, -65, 65, 1.0, 250.0)
    light_mvp  = light_proj @ light_view
    light_dir  = np.array([-0.3, -0.6, -1.0], dtype='f4')
    light_dir /= np.linalg.norm(light_dir)

    # ── Shadow pass ───────────────────────────────────────────────────────────
    print("Shadow pass...")
    shadow_fbo.use()
    ctx.viewport = (0, 0, SHADOW_SIZE, SHADOW_SIZE)
    ctx.clear(depth=1.0)
    shadow_prog['light_mvp'].write(light_mvp.astype('f4').T.tobytes())
    shadow_vao.render(moderngl.TRIANGLES)

    # ── Main render pass ──────────────────────────────────────────────────────
    print(f"Main render pass ({WIDTH}×{HEIGHT})...")
    fbo.use()
    ctx.viewport = (0, 0, WIDTH, HEIGHT)
    ctx.clear(0.03, 0.03, 0.06, 1.0)  # keep cool background

    shadow_tex.use(location=0)
    main_prog['mvp'].write(mvp.astype('f4').T.tobytes())
    main_prog['light_mvp'].write(light_mvp.astype('f4').T.tobytes())
    main_prog['shadow_map'].value = 0
    main_prog['light_dir'].write(light_dir.tobytes())
    main_prog['ambient'].value = 0.65  # raised: shadow + dark blue side needs floor light

    main_vao.render(moderngl.TRIANGLES)

    # ── Save ─────────────────────────────────────────────────────────────────
    os.makedirs("output", exist_ok=True)
    print("Reading framebuffer...")
    img = render_to_image(ctx, fbo, WIDTH, HEIGHT)
    img.save(OUTPUT_PNG)
    ctx.release()

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s → {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
