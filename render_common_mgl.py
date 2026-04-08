"""
render_common_mgl.py — Shared moderngl utilities for Burger Wars renderers.
"""
import math
import numpy as np
import moderngl


# ── Matrix math ───────────────────────────────────────────────────────────────

def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2)
    m = np.zeros((4, 4), dtype='f4')
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def orthographic(left, right, bottom, top, near, far):
    m = np.zeros((4, 4), dtype='f4')
    m[0, 0] = 2 / (right - left)
    m[1, 1] = 2 / (top - bottom)
    m[2, 2] = -2 / (far - near)
    m[0, 3] = -(right + left) / (right - left)
    m[1, 3] = -(top + bottom) / (top - bottom)
    m[2, 3] = -(far + near) / (far - near)
    m[3, 3] = 1.0
    return m


def look_at(eye, center, up):
    eye    = np.array(eye,    dtype='f4')
    center = np.array(center, dtype='f4')
    up     = np.array(up,     dtype='f4')
    f = center - eye;  f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.eye(4, dtype='f4')
    m[0, :3] = r;  m[0, 3] = -np.dot(r, eye)
    m[1, :3] = u;  m[1, 3] = -np.dot(u, eye)
    m[2, :3] = -f; m[2, 3] =  np.dot(f, eye)
    return m


def mat_mul(*mats):
    result = mats[0]
    for m in mats[1:]:
        result = result @ m
    return result


# ── Geometry builders ─────────────────────────────────────────────────────────

def triangulate_polygon(verts_2d):
    """Fan-triangulate a convex polygon. Returns list of (v0,v1,v2) index tuples."""
    n = len(verts_2d)
    tris = []
    for i in range(1, n - 1):
        tris.append((0, i, i + 1))
    return tris


def build_prism_verts(verts_2d, height, color_rgb):
    """
    Build vertex data for an extruded polygon prism.
    Returns numpy array of shape (N, 9): x,y,z, nx,ny,nz, r,g,b  (floats, color 0-1)
    """
    n = len(verts_2d)
    verts = []
    r, g, b = color_rgb[0] / 255.0, color_rgb[1] / 255.0, color_rgb[2] / 255.0
    # Slightly darker for sides
    rs, gs, bs = r * 0.62, g * 0.62, b * 0.62

    # Top face triangles (normal up: 0,0,1)
    top_tris = triangulate_polygon(verts_2d)
    for i0, i1, i2 in top_tris:
        for idx in (i0, i1, i2):
            x, y = verts_2d[idx]
            verts += [x, y, height, 0.0, 0.0, 1.0, r, g, b]

    # Side faces (quads → 2 triangles each)
    for i in range(n):
        j = (i + 1) % n
        x0, y0 = verts_2d[i]
        x1, y1 = verts_2d[j]
        # Normal: perpendicular to edge, pointing outward (rough approx)
        ex, ey = x1 - x0, y1 - y0
        nx, ny = ey, -ex
        length = math.sqrt(nx*nx + ny*ny)
        if length > 1e-8:
            nx /= length; ny /= length
        else:
            nx, ny = 0.0, 0.0
        # Two triangles for quad (bottom-left, bottom-right, top-right) + (bottom-left, top-right, top-left)
        # Bottom: z=0, Top: z=height
        verts += [x0, y0, 0.0,      nx, ny, 0.0, rs, gs, bs]
        verts += [x1, y1, 0.0,      nx, ny, 0.0, rs, gs, bs]
        verts += [x1, y1, height,   nx, ny, 0.0, rs, gs, bs]

        verts += [x0, y0, 0.0,      nx, ny, 0.0, rs, gs, bs]
        verts += [x1, y1, height,   nx, ny, 0.0, rs, gs, bs]
        verts += [x0, y0, height,   nx, ny, 0.0, rs, gs, bs]

    return np.array(verts, dtype='f4')


def build_box_verts(cx, cy, half, height, color_rgb):
    """
    Build vertex data for a rectangular box prism centered at (cx, cy).
    half: half-size of the square base
    Returns numpy array of shape (N, 9)
    """
    verts_2d = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]
    return build_prism_verts(verts_2d, height, color_rgb)


# ── Shaders ───────────────────────────────────────────────────────────────────

SHADOW_VERT = """
#version 410
in vec3 in_position;
uniform mat4 light_mvp;
void main() {
    gl_Position = light_mvp * vec4(in_position, 1.0);
}
"""

SHADOW_FRAG = """
#version 410
out float fragDepth;
void main() {
    fragDepth = gl_FragCoord.z;
}
"""

MAIN_VERT = """
#version 410
in vec3 in_position;
in vec3 in_normal;
in vec3 in_color;

uniform mat4 mvp;
uniform mat4 light_mvp;

out vec3 v_color;
out vec3 v_normal;
out vec4 v_light_pos;

void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
    v_color     = in_color;
    v_normal    = in_normal;
    v_light_pos = light_mvp * vec4(in_position, 1.0);
}
"""

MAIN_FRAG = """
#version 410
in vec3 v_color;
in vec3 v_normal;
in vec4 v_light_pos;

uniform sampler2D shadow_map;
uniform vec3 light_dir;
uniform float ambient;

out vec4 f_color;

float shadow_factor(vec4 lpos) {
    vec3 proj = lpos.xyz / lpos.w * 0.5 + 0.5;
    if (proj.z > 1.0) return 0.0;
    float closest = texture(shadow_map, proj.xy).r;
    float bias = max(0.008 * (1.0 - dot(normalize(v_normal), -normalize(light_dir))), 0.002);
    return (proj.z - bias > closest) ? 0.75 : 0.0;
}

void main() {
    float diff    = max(dot(normalize(v_normal), normalize(-light_dir)), 0.0);
    float shadow  = shadow_factor(v_light_pos);
    float light   = ambient + (1.0 - shadow) * diff * (1.0 - ambient);
    f_color = vec4(v_color * light, 1.0);
}
"""


# ── Renderer context ──────────────────────────────────────────────────────────

def create_context_and_fbo(width, height):
    ctx = moderngl.create_standalone_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)
    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((width, height), 4)],
        depth_attachment=ctx.depth_texture((width, height)),
    )
    return ctx, fbo


def create_shadow_fbo(ctx, size=4096):
    depth_tex = ctx.depth_texture((size, size))
    fbo = ctx.framebuffer(depth_attachment=depth_tex)
    return fbo, depth_tex


def render_to_image(ctx, fbo, width, height):
    """Read framebuffer → PIL Image."""
    from PIL import Image
    data = fbo.read(components=3)
    img = Image.frombytes('RGB', (width, height), data)
    return img.transpose(Image.FLIP_TOP_BOTTOM)
