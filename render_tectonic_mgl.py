#!/usr/bin/env python3
"""
render_tectonic_mgl.py — Composition B: Tectonic Plates
Renders 51k organic polygon prisms using moderngl.
Output: output/tectonic_raw.png (6000x4000)
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
    build_prism_verts,
    SHADOW_VERT, SHADOW_FRAG, MAIN_VERT, MAIN_FRAG,
    create_context_and_fbo, create_shadow_fbo, render_to_image,
)

GEOM_FILE  = "data/tectonic_geometry.json"
OUTPUT_PNG = "output/tectonic_raw.png"
WIDTH, HEIGHT = 6000, 4000
SHADOW_SIZE   = 4096


def build_geometry(tiles):
    """Pack all tile prisms into a single vertex buffer."""
    print(f"  Building geometry for {len(tiles):,} tiles...")
    chunks = []
    for tile in tiles:
        verts_2d = [tuple(v) for v in tile["vertices"]]
        h = tile["height"]
        c = tile["color"]
        chunk = build_prism_verts(verts_2d, h, c)
        chunks.append(chunk)
    all_verts = np.concatenate(chunks, axis=0).reshape(-1, 9)
    print(f"  Vertices: {len(all_verts):,}")
    return all_verts


def main():
    t0 = time.time()
    print("=== Tectonic Plates — moderngl renderer ===")

    if not os.path.exists(GEOM_FILE):
        print(f"Error: {GEOM_FILE} not found. Run generate_tectonic.py first.")
        sys.exit(1)

    print("Loading geometry...")
    with open(GEOM_FILE) as f:
        geom = json.load(f)

    tiles = geom["tiles"]
    scene = geom["scene"]
    SW, SH = scene["width"], scene["height"]  # 100, 66.7

    # ── Build VBO ─────────────────────────────────────────────────────────────
    all_verts = build_geometry(tiles)

    # ── OpenGL context ────────────────────────────────────────────────────────
    print("Creating OpenGL context...")
    ctx, fbo = create_context_and_fbo(WIDTH, HEIGHT)
    shadow_fbo, shadow_tex = create_shadow_fbo(ctx, SHADOW_SIZE)

    # ── Upload geometry ───────────────────────────────────────────────────────
    vbo = ctx.buffer(all_verts.astype('f4').tobytes())

    shadow_prog = ctx.program(vertex_shader=SHADOW_VERT, fragment_shader=SHADOW_FRAG)
    main_prog   = ctx.program(vertex_shader=MAIN_VERT,   fragment_shader=MAIN_FRAG)

    stride = 9 * 4  # 9 floats × 4 bytes
    shadow_vao = ctx.vertex_array(shadow_prog, [(vbo, '3f 3x4 3x4', 'in_position')])
    main_vao   = ctx.vertex_array(main_prog,   [(vbo, '3f 3f 3f',   'in_position', 'in_normal', 'in_color')])

    # ── Camera: oblique overhead filling frame, Google-Earth style ───────────
    cx, cy = SW / 2, SH / 2  # 50, 33.35

    # Wide overhead: pull back to see entire 100×66.7 scene
    # Eye: offset south and high, looking at scene center
    eye    = (cx - 8, cy - 70, 110)
    center = (cx,     cy,       0)
    up     = (0.0,    1.0,     0.0)

    view = look_at(eye, center, up)
    proj = perspective(44, WIDTH / HEIGHT, 1.0, 400.0)
    mvp  = proj @ view

    # ── Light: upper-left diagonal ────────────────────────────────────────────
    lx, ly, lz = cx - 50, cy - 80, 120
    light_view = look_at((lx, ly, lz), (cx, cy, 0), (0, 1, 0))
    light_proj = orthographic(-80, 80, -65, 65, 1.0, 300.0)
    light_mvp  = light_proj @ light_view
    light_dir  = np.array([lx - cx, ly - cy, lz], dtype='f4')
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
    ctx.clear(0.08, 0.07, 0.06, 1.0)  # was 0.06, 0.05, 0.04

    shadow_tex.use(location=0)
    main_prog['mvp'].write(mvp.astype('f4').T.tobytes())
    main_prog['light_mvp'].write(light_mvp.astype('f4').T.tobytes())
    main_prog['shadow_map'].value = 0
    main_prog['light_dir'].write(light_dir.tobytes())
    main_prog['ambient'].value = 0.55  # raised: shadow factor 0.75 makes faces very dark

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
