#!/usr/bin/env python3
"""Build the VRM avatar of Hongou Nemuri from code.

Everything -- mesh, skeleton, skin weights, textures, expressions and
spring bones -- is generated here, so the model can be tweaked by editing
numbers and re-running::

    pip install numpy pillow
    python3 model/make_vrm.py                 # writes model/nemuri.vrm
    python3 model/make_vrm.py --thumbnail model/preview/thumbnail.png

The output is VRM 0.0 (glTF 2.0 + the ``VRM`` extension), the version that
VSeeFace, VMagicMirror, 3tene, cluster and VRoid Hub all accept.

Conventions (VRM 0.0): metres, +Y up, the character faces -Z, and her right
hand is on +X. Every bone has an identity rotation (the T-pose *is* the
rest pose), which is what VRM requires.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def v3(x, y, z):
    return np.array([x, y, z], dtype=np.float64)


def norm(v):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def spline(ctrl):
    """Catmull-Rom through (s, value) control points -> f(s)."""
    p = np.asarray(ctrl, dtype=np.float64)
    q = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1 : i + 3]
        for t in np.linspace(0, 1, 24, endpoint=False):
            out.append(
                0.5
                * (
                    2 * p1
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3
                )
            )
    out.append(p[-1])
    out = np.array(out)
    return lambda s: np.interp(s, out[:, 0], out[:, 1])


def sph(theta, phi):
    """Unit direction. theta from the top, phi=0 is the face, +phi is her right."""
    theta, phi = np.broadcast_arrays(np.asarray(theta, dtype=np.float64), np.asarray(phi, dtype=np.float64))
    return np.stack(
        [np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1
    )


# --------------------------------------------------------------------------
# palette (sRGB). The named ones come from site.json / the key visual.
# --------------------------------------------------------------------------

SKIN = "#FFE7DC"
SKIN_SHADE = "#F4C4C0"
HAIR_CYAN = ("#46BFE6", "#72E8F6", "#B8F8FF")  # root, middle, tip
HAIR_PINK = ("#E07DB9", "#F5A8D4", "#FFD3EA")
GOGGLE = "#FD54F7"
GOGGLE_GREY = "#7C849C"
LENS = "#E6B8FF"
HOODIE = "#343A7E"
HOODIE_SHADE = "#1B1E4C"
TANK = "#FFFFFF"
TANK_TRIM = "#8FD6F4"
SHORTS = "#2B3060"
SOCKS = "#23222F"
LASH = "#2A1B3D"
BROW = "#4A6FA0"
IRIS_DARK = "#1C2B86"
IRIS_MID = "#2F63D9"
IRIS_LIGHT = "#72E0FF"
CHOKER = "#1C1B26"

# --------------------------------------------------------------------------
# skeleton
# --------------------------------------------------------------------------


class Skeleton:
    def __init__(self):
        self.names: list[str] = []
        self.parent: list[int] = []
        self.pos: list[np.ndarray] = []
        self.human: dict[str, int] = {}

    def add(self, name, parent, pos, human=None):
        self.names.append(name)
        self.parent.append(-1 if parent is None else self.id(parent))
        self.pos.append(np.asarray(pos, dtype=np.float64))
        if human:
            self.human[human] = len(self.names) - 1
        return len(self.names) - 1

    def id(self, name):
        return self.names.index(name)

    def p(self, name):
        return self.pos[self.id(name)]


# Proportions: about 1.50 m tall, a little over six heads.
HIPS_Y = 0.80
C = v3(0.0, 1.362, 0.0)  # head centre
UPPER_ARM_X = 0.115
ELBOW_X = 0.345
WRIST_X = 0.545
ARM_Y = 1.145


def build_skeleton() -> Skeleton:
    sk = Skeleton()
    sk.add("Root", None, v3(0, 0, 0))
    sk.add("J_Hips", "Root", v3(0, HIPS_Y, 0), "hips")
    sk.add("J_Spine", "J_Hips", v3(0, 0.88, 0), "spine")
    sk.add("J_Chest", "J_Spine", v3(0, 0.98, 0), "chest")
    sk.add("J_UpperChest", "J_Chest", v3(0, 1.08, 0), "upperChest")
    sk.add("J_Neck", "J_UpperChest", v3(0, 1.200, 0.004), "neck")
    sk.add("J_Head", "J_Neck", v3(0, 1.252, 0.004), "head")
    for side, sx in (("L", -1), ("R", 1)):
        lr = "left" if side == "L" else "right"
        sk.add(f"J_Eye_{side}", "J_Head", v3(sx * 0.037, C[1] - 0.031, -0.035), f"{lr}Eye")
        sk.add(f"J_Shoulder_{side}", "J_UpperChest", v3(sx * 0.025, ARM_Y, 0), f"{lr}Shoulder")
        sk.add(f"J_UpperArm_{side}", f"J_Shoulder_{side}", v3(sx * UPPER_ARM_X, ARM_Y, 0), f"{lr}UpperArm")
        sk.add(f"J_LowerArm_{side}", f"J_UpperArm_{side}", v3(sx * ELBOW_X, ARM_Y, 0), f"{lr}LowerArm")
        sk.add(f"J_Hand_{side}", f"J_LowerArm_{side}", v3(sx * WRIST_X, ARM_Y, 0), f"{lr}Hand")
        for finger, (z, x0, scale) in FINGERS.items():
            prev = f"J_Hand_{side}"
            x = x0
            for seg, seglen in zip(("Proximal", "Intermediate", "Distal"), FINGER_SEGS):
                name = f"J_{finger}{seg}_{side}"
                sk.add(name, prev, v3(sx * x, ARM_Y - 0.002, z), f"{lr}{finger}{seg}")
                prev = name
                x += seglen * scale
            sk.add(f"J_{finger}Tip_{side}", prev, v3(sx * x, ARM_Y - 0.002, z))
        prev = f"J_Hand_{side}"
        p = v3(sx * THUMB_ROOT[0], THUMB_ROOT[1], THUMB_ROOT[2])
        d = THUMB_DIR * v3(sx, 1, 1)
        for seg, seglen in zip(("Proximal", "Intermediate", "Distal"), THUMB_SEGS):
            name = f"J_Thumb{seg}_{side}"
            sk.add(name, prev, p.copy(), f"{lr}Thumb{seg}")
            prev = name
            p = p + d * seglen
        sk.add(f"J_ThumbTip_{side}", prev, p.copy())
        sk.add(f"J_UpperLeg_{side}", "J_Hips", v3(sx * 0.074, 0.765, 0), f"{lr}UpperLeg")
        sk.add(f"J_LowerLeg_{side}", f"J_UpperLeg_{side}", v3(sx * 0.070, 0.430, 0.004), f"{lr}LowerLeg")
        sk.add(f"J_Foot_{side}", f"J_LowerLeg_{side}", v3(sx * 0.068, 0.078, 0.012), f"{lr}Foot")
        sk.add(f"J_Toes_{side}", f"J_Foot_{side}", v3(sx * 0.068, 0.022, -0.070), f"{lr}Toes")
    return sk


# finger -> (z, x of the proximal joint, length scale). Palms face down in the
# T-pose, so the thumb points forward (-Z) and the index finger is the one
# next to it.
FINGERS = {
    "Index": (-0.021, 0.612, 0.95),
    "Middle": (-0.0065, 0.616, 1.0),
    "Ring": (0.0080, 0.613, 0.95),
    "Little": (0.0215, 0.605, 0.78),
}
FINGER_SEGS = (0.026, 0.018, 0.016)
FINGER_R = {"Index": 0.0074, "Middle": 0.0076, "Ring": 0.0072, "Little": 0.0064}
THUMB_ROOT = (0.556, ARM_Y - 0.008, -0.020)
THUMB_DIR = norm(v3(0.55, -0.12, -0.83))
THUMB_SEGS = (0.026, 0.022, 0.019)

# --------------------------------------------------------------------------
# geometry primitives
# --------------------------------------------------------------------------


def loft(rings, cap0=False, cap1=False, closed=True):
    """Skin a (R, N, 3) stack of rings. Returns P, UV, I, ring-param, col-param.

    When ``closed`` each ring is a loop (a seam column is duplicated so the
    texture can wrap); otherwise each ring is an open polyline (a ribbon).
    """
    rings = np.asarray(rings, dtype=np.float64)
    R, N, _ = rings.shape
    if closed:
        grid = np.concatenate([rings, rings[:, :1]], axis=1)
        cols = N + 1
    else:
        grid = rings
        cols = N
    u = np.linspace(0, 1, cols)
    v = np.linspace(0, 1, R)
    uu, vv = np.meshgrid(u, v)
    idx = np.arange(R * cols).reshape(R, cols)
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
    tris = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    P = grid.reshape(-1, 3)
    UV = np.stack([uu, vv], -1).reshape(-1, 2)
    ring = np.repeat(np.arange(R, dtype=np.float64), cols)
    col = np.tile(u, R)
    P, UV, ring, col = list(P), list(UV), list(ring), list(col)
    tris = list(tris)
    centres = rings.mean(axis=1)
    for do, r in ((cap0, 0), (cap1, R - 1)):
        if not do:
            continue
        ci = len(P)
        P.append(centres[r])
        UV.append(np.array([0.5, float(r) / max(R - 1, 1)]))
        ring.append(float(r))
        col.append(0.5)
        for j in range(cols - 1):
            # the two ends face opposite ways
            tri = [ci, idx[r, j + 1], idx[r, j]] if r == 0 else [ci, idx[r, j], idx[r, j + 1]]
            tris.append(np.array(tri))
    P = np.array(P)
    I = np.array(tris, dtype=np.int64)
    # Make the winding face away from the ring centres.
    ring_arr = np.array(ring)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    cent = P[I].mean(axis=1)
    ref = centres[np.clip(np.round(ring_arr[I[:, 0]]).astype(int), 0, R - 1)]
    if np.sum(np.einsum("ij,ij->i", fn, cent - ref)) < 0:
        I = I[:, ::-1]
    return P, np.array(UV), I, ring_arr, np.array(col)


def frame_rings(path, radii_a, radii_b, n, up_hint=None, shape=None):
    """Rings of ellipses swept along ``path`` (M, 3)."""
    path = np.asarray(path, dtype=np.float64)
    M = len(path)
    T = np.gradient(path, axis=0)
    T = norm(T)
    hint = v3(0, 1, 0) if up_hint is None else np.asarray(up_hint, dtype=np.float64)
    rings = np.zeros((M, n, 3))
    ang = np.linspace(-math.pi, math.pi, n, endpoint=False)
    for i in range(M):
        e2 = hint - T[i] * np.dot(hint, T[i])
        if np.linalg.norm(e2) < 1e-6:
            e2 = v3(0, 0, 1) - T[i] * T[i][2]
        e2 = norm(e2)
        e1 = np.cross(e2, T[i])
        a, b = radii_a[i], radii_b[i]
        ca, sa = np.cos(ang), np.sin(ang)
        if shape is not None:
            ca, sa = shape(ca, sa, i)
        rings[i] = path[i] + np.outer(ca * a, e1) + np.outer(sa * b, e2)
    return rings


def torus_rings(centre, axis, R, r, nu=48, nv=10):
    axis = norm(axis)
    ref = v3(0, 1, 0) if abs(axis[1]) < 0.9 else v3(1, 0, 0)
    e1 = norm(np.cross(axis, ref))
    e2 = np.cross(axis, e1)
    rings = []
    for k in range(nu + 1):
        a = 2 * math.pi * k / nu
        radial = e1 * math.cos(a) + e2 * math.sin(a)
        c = centre + radial * R
        ring = [c + (radial * math.cos(b) + axis * math.sin(b)) * r for b in np.linspace(0, 2 * math.pi, nv, endpoint=False)]
        rings.append(ring)
    return np.array(rings)


def sphere_rings(centre, radius, nlat=12, nlon=16, scale=(1, 1, 1)):
    rings = []
    for i in range(nlat + 1):
        th = math.pi * (0.001 + 0.998 * i / nlat)
        ring = [centre + radius * np.array(scale) * sph(th, ph) for ph in np.linspace(-math.pi, math.pi, nlon, endpoint=False)]
        rings.append(ring)
    return np.array(rings)


def compute_normals(P, I):
    key = np.round(P * 2e4).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    acc = np.zeros((inv.max() + 1, 3))
    for k in range(3):
        np.add.at(acc, inv[I[:, k]], fn)
    N = norm(acc[inv])
    bad = np.linalg.norm(acc[inv], axis=1) < 1e-14
    N[bad] = (0, 1, 0)
    return N


def raycast_z(tri_P, xy, z0=-1.0):
    """First hit of rays from (x, y, z0) along +Z against triangles."""
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    v0, v1, v2 = tri_P[:, 0], tri_P[:, 1], tri_P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = v3(0, 0, 1)
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(a) > 1e-12
    v0, e1, e2, h, a = v0[ok], e1[ok], e2[ok], h[ok], a[ok]
    f = 1.0 / a
    out = np.full(len(xy), np.nan)
    for start in range(0, len(xy), 256):
        o = np.column_stack([xy[start : start + 256], np.full(len(xy[start : start + 256]), z0)])
        s = o[:, None, :] - v0[None]
        u = f[None] * np.einsum("rtk,tk->rt", s, h)
        q = np.cross(s, e1[None])
        v = f[None] * q[..., 2]
        t = f[None] * np.einsum("rtk,tk->rt", q, e2)
        hit = (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > 0)
        t = np.where(hit, t, np.inf)
        out[start : start + 256] = z0 + t.min(axis=1)
    return out


# --------------------------------------------------------------------------
# skin weights
# --------------------------------------------------------------------------


def chain_weights(s, nb, blend=0.22):
    """Weights (n, nb) for a chain where bone k owns s in [k, k+1)."""
    s = np.clip(np.asarray(s, dtype=np.float64), 0, nb - 1e-6)
    n = len(s)
    W = np.zeros((n, nb))
    i = np.floor(s).astype(int)
    f = s - i
    prev_w = np.where((f < blend) & (i > 0), 0.5 * (1 - smoothstep(0, blend, f)), 0.0)
    next_w = np.where((f > 1 - blend) & (i < nb - 1), 0.5 * smoothstep(1 - blend, 1, f), 0.0)
    rows = np.arange(n)
    W[rows, i] = 1 - prev_w - next_w
    W[rows, np.maximum(i - 1, 0)] += prev_w
    W[rows, np.minimum(i + 1, nb - 1)] += next_w
    return W


def chain_param(c, joints):
    """Map a coordinate to chain parameter given monotone joint coordinates."""
    joints = np.asarray(joints, dtype=np.float64)
    if joints[0] > joints[-1]:
        return np.interp(-np.asarray(c), -joints, np.arange(len(joints)))
    return np.interp(c, joints, np.arange(len(joints)))


def pack(bones, W):
    W = np.asarray(W, dtype=np.float64)
    if W.ndim == 1:
        W = W[:, None]
    bones = np.asarray(bones, dtype=np.int64)
    if W.shape[1] < 4:
        W = np.hstack([W, np.zeros((len(W), 4 - W.shape[1]))])
        bones = np.concatenate([bones, np.zeros(4 - len(bones), dtype=np.int64)])
    order = np.argsort(-W, axis=1)[:, :4]
    Wt = np.take_along_axis(W, order, 1)
    J = bones[order]
    Wt = Wt / np.maximum(Wt.sum(axis=1, keepdims=True), 1e-12)
    J[Wt <= 0] = 0
    return J, Wt


def single(bone, n):
    return pack([bone], np.ones((n, 1)))


# --------------------------------------------------------------------------
# mesh containers
# --------------------------------------------------------------------------


class Prim:
    def __init__(self, material: str):
        self.material = material
        self.P, self.UV, self.J, self.W, self.I = [], [], [], [], []
        self.N = []
        self.morphs: dict[str, list[tuple[int, np.ndarray]]] = {}
        self.count = 0

    def add(self, P, UV, JW, I, morphs=None, normals=None):
        P = np.asarray(P, dtype=np.float64)
        self.P.append(P)
        self.UV.append(np.asarray(UV, dtype=np.float64))
        self.J.append(JW[0])
        self.W.append(JW[1])
        self.I.append(np.asarray(I, dtype=np.int64) + self.count)
        self.N.append(compute_normals(P, np.asarray(I)) if normals is None else normals)
        for name, delta in (morphs or {}).items():
            self.morphs.setdefault(name, []).append((self.count, np.asarray(delta)))
        self.count += len(P)

    def arrays(self, morph_names):
        P = np.concatenate(self.P)
        out = {
            "P": P,
            "N": np.concatenate(self.N),
            "UV": np.concatenate(self.UV),
            "J": np.concatenate(self.J),
            "W": np.concatenate(self.W),
            "I": np.concatenate(self.I),
            "morphs": [],
        }
        for name in morph_names:
            d = np.zeros_like(P)
            for off, delta in self.morphs.get(name, []):
                d[off : off + len(delta)] = delta
            out["morphs"].append(d)
        return out


# --------------------------------------------------------------------------
# the body
# --------------------------------------------------------------------------

# Torso profile: y -> (half width, depth to the front, depth to the back)
TORSO = np.array(
    [
        # y      a      front  back
        [0.705, 0.070, 0.050, 0.055],
        [0.725, 0.118, 0.066, 0.074],
        [0.760, 0.132, 0.074, 0.082],
        [0.810, 0.133, 0.074, 0.080],
        [0.860, 0.114, 0.066, 0.068],
        [0.905, 0.101, 0.062, 0.064],
        [0.950, 0.100, 0.064, 0.064],
        [0.995, 0.106, 0.078, 0.066],
        [1.030, 0.110, 0.088, 0.068],
        [1.065, 0.112, 0.083, 0.068],
        [1.100, 0.116, 0.068, 0.066],
        [1.135, 0.122, 0.060, 0.062],
        [1.160, 0.116, 0.054, 0.058],
        [1.178, 0.092, 0.047, 0.052],
        [1.190, 0.056, 0.041, 0.045],
        [1.203, 0.040, 0.037, 0.039],
        [1.240, 0.037, 0.036, 0.038],
        [1.300, 0.036, 0.035, 0.037],
        [1.330, 0.030, 0.030, 0.030],
    ]
)
TORSO_TOP, TORSO_BOTTOM = 1.33, 0.705


def torso_profile(y):
    return (
        np.interp(y, TORSO[:, 0], TORSO[:, 1]),
        np.interp(y, TORSO[:, 0], TORSO[:, 2]),
        np.interp(y, TORSO[:, 0], TORSO[:, 3]),
    )


def torso_point(y, phi, grow=0.0):
    a, bf, bb = torso_profile(y)
    b = np.where(np.cos(phi) > 0, bf, bb)
    z_shift = np.interp(y, [1.15, 1.2, 1.33], [0.0, 0.004, 0.006])
    return np.stack(
        [(a + grow) * np.sin(phi), np.broadcast_to(y, np.shape(phi)), -(b + grow) * np.cos(phi) + z_shift], -1
    )


def torso_bones(sk):
    return [sk.id(n) for n in ("J_Hips", "J_Spine", "J_Chest", "J_UpperChest", "J_Neck", "J_Head")]


TORSO_JOINTS = [0.60, 0.88, 0.98, 1.08, 1.20, 1.252, 1.6]


def torso_weights(sk, y):
    s = chain_param(y, TORSO_JOINTS)
    return pack(torso_bones(sk), chain_weights(s, 6, blend=0.3))


def build_body(sk, prims):
    body = prims["Body"]
    # --- torso -----------------------------------------------------------
    ys = np.concatenate([np.linspace(TORSO_BOTTOM, 1.14, 34), np.linspace(1.147, TORSO_TOP, 26)])
    phis = np.linspace(-math.pi, math.pi, 64, endpoint=False)
    rings = np.array([torso_point(y, phis) for y in ys])
    P, UV, I, ring, col = loft(rings, cap0=True, cap1=False)
    y = P[:, 1]
    UV = np.column_stack([col * 0.5, (TORSO_TOP - y) / (TORSO_TOP - TORSO_BOTTOM)])
    body.add(P, UV, torso_weights(sk, y), I)

    # --- arms ------------------------------------------------------------
    for side, sx in (("L", -1), ("R", 1)):
        xs = np.linspace(0.075, WRIST_X + 0.012, 30)
        path = np.column_stack([sx * xs, np.full_like(xs, ARM_Y), np.zeros_like(xs)])
        r = np.interp(xs, [0.075, 0.12, 0.2, 0.33, 0.36, 0.46, 0.54, 0.56], [0.030, 0.034, 0.031, 0.026, 0.025, 0.022, 0.019, 0.019])
        rz = r * np.interp(xs, [0.3, 0.5, 0.56], [1.0, 1.08, 1.25])
        rings = frame_rings(path, r, rz, 18, up_hint=v3(0, 1, 0))
        P, _, I, ring, col = loft(rings, cap0=True, cap1=True)
        ax = np.abs(P[:, 0])
        UV = np.column_stack([0.75 + col * 0.25, np.clip((ax - 0.07) / 0.5, 0, 1) * 0.5])
        bones = [sk.id(f"J_Shoulder_{side}"), sk.id(f"J_UpperArm_{side}"), sk.id(f"J_LowerArm_{side}"), sk.id(f"J_Hand_{side}")]
        s = chain_param(ax, [0.0, UPPER_ARM_X, ELBOW_X, WRIST_X, 0.7])
        W = chain_weights(s, 4, blend=0.2)
        body.add(P, UV, pack(bones, W), I)
        build_hand(sk, body, side, sx)

    # --- legs ------------------------------------------------------------
    for side, sx in (("L", -1), ("R", 1)):
        ys = np.linspace(0.84, 0.045, 36)
        xs = sx * np.interp(ys, [0.045, 0.43, 0.84], [0.068, 0.070, 0.066])
        zs = np.interp(ys, [0.045, 0.3, 0.43, 0.84], [0.012, 0.010, 0.004, 0.004])
        path = np.column_stack([xs, ys, zs])
        r = np.interp(
            ys,
            [0.045, 0.09, 0.16, 0.30, 0.40, 0.45, 0.55, 0.70, 0.78, 0.84],
            [0.024, 0.025, 0.030, 0.043, 0.037, 0.039, 0.050, 0.062, 0.066, 0.064],
        )
        rings = frame_rings(path, r, r * 0.98, 20, up_hint=v3(0, 0, -1))
        P, _, I, ring, col = loft(rings, cap0=True, cap1=True)
        UV = np.column_stack([0.5 + col * 0.25, np.clip((0.84 - P[:, 1]) / 0.795, 0, 1)])
        bones = [sk.id("J_Hips"), sk.id(f"J_UpperLeg_{side}"), sk.id(f"J_LowerLeg_{side}"), sk.id(f"J_Foot_{side}")]
        s = chain_param(P[:, 1], [0.95, 0.765, 0.43, 0.078, -0.1])
        W = chain_weights(s, 4, blend=0.25)
        body.add(P, UV, pack(bones, W), I)


def build_hand(sk, body, side, sx):
    hand = sk.id(f"J_Hand_{side}")
    # palm
    xs = np.linspace(WRIST_X - 0.004, 0.618, 10)
    path = np.column_stack([sx * xs, np.full_like(xs, ARM_Y - 0.002), np.zeros_like(xs)])
    wz = np.interp(xs, [WRIST_X, 0.56, 0.60, 0.618], [0.022, 0.029, 0.032, 0.028])
    hy = np.interp(xs, [WRIST_X, 0.58, 0.618], [0.015, 0.012, 0.009])
    rings = frame_rings(path, wz, hy, 16, up_hint=v3(0, 1, 0))
    P, _, I, _, _ = loft(rings, cap0=True, cap1=True)
    UV = np.column_stack([np.full(len(P), 0.9), np.full(len(P), 0.75)])
    body.add(P, UV, single(hand, len(P)), I)

    def finger(names, pts, radius):
        pts = np.asarray(pts)
        # resample the polyline into many points
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        acc = np.concatenate([[0], np.cumsum(seg)])
        ts = np.linspace(0, acc[-1], 14)
        path = np.column_stack([np.interp(ts, acc, pts[:, k]) for k in range(3)])
        r = radius * np.interp(ts / acc[-1], [0, 0.7, 0.95, 1.0], [1.0, 0.9, 0.75, 0.3])
        rings = frame_rings(path, r, r * 0.9, 10, up_hint=v3(0, 1, 0))
        P, _, I, ring, _ = loft(rings, cap0=True, cap1=True)
        # arc-length parameter per vertex -> bone chain
        s_of_ring = np.interp(ts, acc, np.arange(len(pts)))
        s = np.interp(ring, np.arange(len(ts)), s_of_ring)
        W = chain_weights(s, len(names), blend=0.25)
        UV = np.column_stack([np.full(len(P), 0.9), np.full(len(P), 0.75)])
        body.add(P, UV, pack([sk.id(n) for n in names], W), I)

    for f in FINGERS:
        names = [f"J_{f}{seg}_{side}" for seg in ("Proximal", "Intermediate", "Distal")]
        pts = [sk.p(n) for n in names] + [sk.p(f"J_{f}Tip_{side}")]
        pts[0] = pts[0] - v3(sx * 0.012, 0, 0)
        finger(names, pts, FINGER_R[f])
    names = [f"J_Thumb{seg}_{side}" for seg in ("Proximal", "Intermediate", "Distal")]
    pts = [sk.p(n) for n in names] + [sk.p(f"J_ThumbTip_{side}")]
    pts[0] = pts[0] - THUMB_DIR * v3(sx, 1, 1) * 0.01
    finger(names, pts, 0.0092)


# --------------------------------------------------------------------------
# head and face
# --------------------------------------------------------------------------


def head_shape(theta, phi):
    d = sph(theta, phi)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    X = x * 0.086
    Y = np.where(y > 0, y * 0.100, y * 0.112)
    Z = np.where(z < 0, z * 0.090, z * 0.098)
    h = np.clip(-Y / 0.112, 0, 1)
    # A narrow anime jaw that comes forward to a soft chin.
    X = X * (1 - 0.34 * h**1.4)
    Z = Z * (1 - 0.25 * h**2) - 0.052 * h**2
    # Flatten the face a touch so the features sit on a calm plane.
    front = smoothstep(0.2, 0.9, -z) * smoothstep(-0.2, 0.3, 0.6 - np.abs(y))
    Z = Z + 0.006 * front
    return C + np.stack([X, Y, Z], -1)


def face_uv(P):
    """Wrap the face texture around the head like a cylinder, front at u=0.5."""
    rel = np.asarray(P) - C
    return np.column_stack([0.5 + np.arctan2(rel[:, 0], -rel[:, 2]) / (2 * math.pi), 0.5 - rel[:, 1] / 0.26])


def build_head(sk, prims):
    th = np.linspace(0.002, math.pi - 0.002, 44)
    ph = np.linspace(-math.pi, math.pi, 64, endpoint=False) + math.pi  # seam at the back
    rings = np.array([head_shape(t, ph) for t in th])
    P, _, I, _, _ = loft(rings)
    UV = face_uv(P)
    head = sk.id("J_Head")
    prims["FaceSkin"].add(P, UV, single(head, len(P)), I)
    tris = P[I]
    front = tris[:, :, 2].mean(axis=1) < -0.01
    return tris[front]


class FaceDecals:
    """Features drawn as thin meshes on the face, so they can morph."""

    def __init__(self, sk, prims, tris):
        self.sk, self.prims, self.tris = sk, prims, tris

    def place(self, xy, lift):
        xy = np.asarray(xy, dtype=np.float64)
        z = raycast_z(self.tris, xy + C[:2])
        if np.isnan(z).any():
            raise RuntimeError("a face decal fell off the head")
        return np.column_stack([xy[:, 0] + C[0], xy[:, 1] + C[1], z - lift])

    def grid(self, prim, bone, fn, ns, nt, lift, morphs, uv=None):
        """fn(s, t, variant) -> (x, y) relative to the head centre."""
        s = np.linspace(0, 1, ns)
        t = np.linspace(0, 1, nt)
        ss, tt = np.meshgrid(s, t)
        ss, tt = ss.ravel(), tt.ravel()
        base = self.place(np.column_stack(fn(ss, tt, None)), lift)
        deltas = {}
        for name in morphs:
            deltas[name] = self.place(np.column_stack(fn(ss, tt, name)), lift) - base
        idx = np.arange(ns * nt).reshape(nt, ns)
        a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
        I = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([a, d, c], -1).reshape(-1, 3)])
        # Must face -Z. A feature that is closed at rest (the open mouth) has no
        # area to judge by, so fall back to its first morph target.
        for ref in [base] + [base + d for d in deltas.values()]:
            fn_ = np.cross(ref[I[:, 1]] - ref[I[:, 0]], ref[I[:, 2]] - ref[I[:, 0]])[:, 2].sum()
            if abs(fn_) > 1e-9:
                break
        if fn_ > 0:
            I = I[:, ::-1]
        UV = np.column_stack([ss, tt]) if uv is None else uv(ss, tt)
        normals = np.tile(v3(0, 0, -1), (len(base), 1))
        self.prims[prim].add(base, UV, single(bone, len(base)), I, deltas, normals)


EYE_W, EYE_H = 0.040, 0.033
EYE_Y = -0.031
UPPER = spline([(0, 0.06), (0.22, 0.44), (0.5, 0.53), (0.78, 0.44), (1.0, 0.10)])
LOWER = spline([(0, 0.02), (0.25, -0.38), (0.55, -0.47), (0.85, -0.34), (1.0, 0.08)])


def eye_curves(sx):
    ex = sx * 0.037

    def X(s):
        return ex + sx * (np.asarray(s) - 0.5) * EYE_W

    def top(s):
        return EYE_Y + UPPER(s) * EYE_H

    def bot(s):
        return EYE_Y + LOWER(s) * EYE_H

    def closed(s):  # where the lid lands when blinking: a soft smile curve
        return EYE_Y - 0.009 - 0.003 * np.sin(math.pi * np.clip(s, 0, 1)) + 0.004 * np.asarray(s)

    def joy(s):  # ^ ^
        return EYE_Y - 0.004 + 0.010 * np.sin(math.pi * np.clip(s, 0, 1)) ** 0.8

    return X, top, bot, closed, joy


def build_face(sk, prims, tris):
    fd = FaceDecals(sk, prims, tris)
    head = sk.id("J_Head")
    for side, sx in (("L", -1), ("R", 1)):
        X, top, bot, closed, joy = eye_curves(sx)
        blink, joyname = f"Blink_{side}", f"EyeJoy_{side}"

        def white(s, t, m, top=top, bot=bot, X=X, closed=closed, joy=joy, blink=blink, joyname=joyname):
            if m == blink:
                return X(s), closed(s) + 0 * t
            if m == joyname:
                return X(s), joy(s) + 0 * t
            return X(s), top(s) * (1 - t) + bot(s) * t

        fd.grid("EyeWhite", head, white, 16, 6, 0.0006, [blink, joyname])

        # Iris: a tall ellipse, clipped by its own texture; follows the eye bone.
        icx, icy = sx * 0.037 + sx * 0.0015, EYE_Y - 0.0005
        irx, iry = 0.0118, 0.0158

        def iris(s, t, m, X=X, closed=closed, joy=joy, icx=icx, icy=icy, sx=sx, blink=blink, joyname=joyname):
            x = icx + (s - 0.5) * 2 * irx
            y = icy + (0.5 - t) * 2 * iry
            se = np.clip(0.5 + sx * (x - sx * 0.037) / EYE_W, 0, 1)
            if m == blink:
                return x, closed(se) + 0.0004 + 0 * t
            if m == joyname:
                return x, joy(se) + 0.0004 + 0 * t
            return x, y

        fd.grid("Iris", sk.id(f"J_Eye_{side}"), iris, 12, 14, 0.0012, [blink, joyname])

        # Upper lashes, thick at the outer corner with a small flick.
        thick = spline([(0, 0.0016), (0.3, 0.0030), (0.7, 0.0042), (1.0, 0.0050)])

        def lash_s(s):
            return -0.03 + np.asarray(s) * 1.16

        def lash(s, t, m, X=X, top=top, closed=closed, joy=joy, blink=blink, joyname=joyname, sx=sx):
            u = lash_s(s)
            uc = np.clip(u, 0, 1)
            over = np.clip(u - 1, 0, None)
            x = X(uc) + sx * over * EYE_W * 0.9
            th = thick(uc) * (1 - (over / 0.13) ** 1.5 * 0.85)
            if m == blink:
                base = closed(uc) - over * 0.030
                return x, base - 0.0006 + t * th * 0.85
            if m == joyname:
                base = joy(uc) - over * 0.06
                return x, base - 0.0006 + t * th * 0.9
            base = top(uc) - over * 0.045
            return x, base - 0.0008 + t * th

        fd.grid("Line", head, lash, 30, 2, 0.0018, [blink, joyname])

        # Short lower lash at the outer half.
        def lower(s, t, m, X=X, bot=bot, closed=closed, joy=joy, blink=blink, joyname=joyname):
            u = 0.5 + np.asarray(s) * 0.5
            if m == blink:
                return X(u), closed(u) + 0.0002 * t
            if m == joyname:
                return X(u), joy(u) + 0.0002 * t
            return X(u), bot(u) - 0.0002 + t * 0.0011 * np.sin(math.pi * s) ** 0.5

        fd.grid("Line", head, lower, 10, 2, 0.0016, [blink, joyname])

        # Brows (mostly behind the bangs, but they sell the expressions).
        def brow(s, t, m, sx=sx):
            x = sx * (0.036 + (np.asarray(s) - 0.45) * 0.040)
            y = 0.004 + 0.004 * np.sin(math.pi * s) - 0.002 * s
            if m == "BrowAngry":
                y = y - 0.006 * (1 - s) + 0.002 * s
            elif m == "BrowSorrow":
                y = y + 0.006 * (1 - s) - 0.003 * s
            elif m == "BrowUp":
                y = y + 0.004
            th = 0.0022 * (1 - 0.5 * s)
            return x, y + t * th

        fd.grid("Line", head, brow, 12, 2, 0.0010, ["BrowAngry", "BrowSorrow", "BrowUp"])

    # ---- mouth -----------------------------------------------------------
    MY = -0.083

    def line_curve(s, m):
        x = (np.asarray(s) - 0.5) * 0.013
        y = MY + 0.0018 * ((2 * np.asarray(s) - 1) ** 2)
        if m == "MouthSorrow":
            y = MY + 0.0012 - 0.0022 * ((2 * np.asarray(s) - 1) ** 2)
        if m == "MouthAngry":
            x = x * 0.8
            y = MY + 0.0008 - 0.0012 * ((2 * np.asarray(s) - 1) ** 2)
        return x, y

    OPEN = {
        # name: (width, upper-curve lift at corners, depth, roundness, arch)
        "MouthA": (0.019, 0.0020, 0.0150, 0.8, 0.0),
        "MouthI": (0.024, 0.0020, 0.0055, 0.5, 0.0),
        "MouthU": (0.010, 0.0006, 0.0075, 0.5, 0.0012),
        "MouthE": (0.021, 0.0024, 0.0095, 0.6, 0.0),
        "MouthO": (0.014, 0.0003, 0.0120, 0.5, 0.0020),
        "MouthFun": (0.024, 0.0040, 0.0150, 0.7, 0.0),
    }

    def mouth_line(s, t, m):
        x, y = line_curve(s, m)
        th = 0.0012
        if m in OPEN:
            w, lift, depth, rnd, arch = OPEN[m]
            x = (np.asarray(s) - 0.5) * w
            y = MY + lift * ((2 * np.asarray(s) - 1) ** 2) + 0.0006 + arch * np.sin(math.pi * np.asarray(s))
            th = 0.0
        return x, y + (t - 0.5) * th * (1 - 0.6 * np.abs(2 * np.asarray(s) - 1))

    fd.grid("Line", head, mouth_line, 16, 2, 0.0012, list(OPEN) + ["MouthSorrow", "MouthAngry"])

    def mouth_inner(s, t, m):
        x, y = line_curve(s, None)
        if m in OPEN:
            w, lift, depth, rnd, arch = OPEN[m]
            x = (np.asarray(s) - 0.5) * w
            up = MY + lift * ((2 * np.asarray(s) - 1) ** 2) + 0.0006 + arch * np.sin(math.pi * np.asarray(s))
            lo = MY + 0.0006 - depth * np.sin(math.pi * np.asarray(s)) ** rnd
            y = up * (1 - t) + lo * t
        return x, y

    fd.grid("Mouth", head, mouth_inner, 16, 8, 0.0008, list(OPEN))


# --------------------------------------------------------------------------
# hair
# --------------------------------------------------------------------------

HC = C + v3(0, 0.012, 0.006)
HR = dict(rx=0.104, ryu=0.114, ryd=0.112, rzf=0.103, rzb=0.114)


def shell(d, scale=1.0):
    d = norm(d)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    ry = np.where(y > 0, HR["ryu"], HR["ryd"])
    rz = np.where(z < 0, HR["rzf"], HR["rzb"])
    r = 1 / np.sqrt((x / HR["rx"]) ** 2 + (y / ry) ** 2 + (z / rz) ** 2)
    return HC + d * (r * scale)[..., None]


HAIR_COLS = {"cyan": 0, "pink": 1, "fade": 2}  # texture column per colour


class HairBuilder:
    def __init__(self, sk, prim):
        self.sk, self.prim = sk, prim
        self.chains: list[tuple[str, int]] = []  # (group, root bone index)
        self.n = 0

    def clump(self, theta0, phi0, theta1, drop, width, thick, colour="cyan", group="hair",
              scale=1.0, flare=0.012, curl=0.010, dphi=0.0, forward=0.0, bones=3, twist=0.0):
        """One lock: hugs the head shell, then falls, tapering to a point."""
        t0, t1 = math.radians(theta0), math.radians(theta1)
        p0, p1 = math.radians(phi0), math.radians(phi0 + dphi)
        on = max(int(abs(t1 - t0) / math.radians(4)) + 2, 4)
        ths = np.linspace(t0, t1, on)
        phs = np.linspace(p0, p1, on)
        part1 = shell(sph(ths, phs), scale)
        pts = [*part1]
        n_free = 0
        if drop > 0:
            n_free = max(int(drop / 0.008) + 3, 5)
            start = part1[-1]
            out = start - HC
            out[1] = 0
            out = norm(out)
            tng = norm(part1[-1] - part1[-2])
            for k in range(1, n_free + 1):
                t = k / n_free
                down = v3(0, -1, 0) * drop * t
                # ease from the shell tangent into gravity
                ease = tng * 0.0
                side = out * (flare * math.sin(math.pi * min(t * 1.2, 1.0)) - curl * t**3)
                fwd = v3(0, 0, -1) * forward * t
                pts.append(start + down + ease + side + fwd)
        pts = np.array(pts)
        M = len(pts)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        arc = np.concatenate([[0], np.cumsum(seg)])
        tt = arc / arc[-1]
        T = norm(np.gradient(pts, axis=0))
        rel = pts - HC
        rel[:, 1] *= np.where(np.arange(M) >= on, 0.15, 1.0)
        Nn = norm(rel - T * np.einsum("ij,ij->i", rel, T)[:, None])
        B = norm(np.cross(T, Nn))
        w = width * np.clip((1 - tt) ** 0.65 * (1 + 0.35 * np.sin(math.pi * tt)), 0, None)
        h = thick * np.clip((1 - tt) ** 0.5, 0, None) + 0.0006
        m = 12
        ang = np.linspace(-math.pi, math.pi, m, endpoint=False)
        rings = np.zeros((M, m, 3))
        for i in range(M):
            ca, sa = np.cos(ang), np.sin(ang)
            tw = twist * tt[i]
            b = B[i] * math.cos(tw) + Nn[i] * math.sin(tw)
            nn = Nn[i] * math.cos(tw) - B[i] * math.sin(tw)
            bend = -0.45 * w[i] * ca**2  # edges curl toward the head
            rings[i] = pts[i] + nn * (h[i] * 0.9) + np.outer(ca * w[i], b) + np.outer(sa * h[i] + bend, nn)
        P, _, I, ring, col = loft(rings)
        c0 = HAIR_COLS[colour] / 3
        UV = np.column_stack([c0 + 0.02 + col * (1 / 3 - 0.04), np.interp(ring, np.arange(M), tt)])
        # bones: head for the part that hugs the scalp, then a chain
        head = self.sk.id("J_Head")
        if n_free and bones:
            k0 = on - 1
            kk = np.linspace(k0, M - 1, bones + 1)
            names = []
            parent = "J_Head"
            for j in range(bones + 1):
                pos = pts[int(round(kk[j]))]
                name = f"J_Hair{self.n:02d}_{j}" if j < bones else f"J_Hair{self.n:02d}_end"
                self.sk.add(name, parent, pos)
                names.append(name)
                parent = name
            self.chains.append((group, self.sk.id(names[0])))
            s_ring = np.interp(ring, [0, k0] + list(kk[1:]), [0, 1] + list(range(2, bones + 2)))
            W = chain_weights(s_ring, bones + 1, blend=0.3)
            JW = pack([head] + [self.sk.id(n) for n in names[:-1]], W)
        else:
            JW = single(head, len(P))
        self.prim.add(P, UV, JW, I)
        self.n += 1

    def cap(self):
        """Scalp shell under the locks, so no skin shows between them."""
        phs = np.linspace(-math.pi, math.pi, 64, endpoint=False) + math.pi
        tmax = np.radians(40 + 70 * ((1 - np.cos(phs)) / 2) ** 0.55)
        rings = []
        for i in range(24):
            f = i / 23
            rings.append(shell(sph(0.01 + f * tmax, phs), 0.985))
        P, _, I, ring, col = loft(np.array(rings), cap0=True)
        UV = np.column_stack([np.full(len(P), 0.15), 0.05 + ring / 23 * 0.25])
        self.prim.add(P, UV, single(self.sk.id("J_Head"), len(P)), I)

    def ahoge(self):
        base = shell(sph(math.radians(4), 0.0), 1.0)
        pts = np.array(
            [base, base + v3(0.002, 0.020, -0.004), base + v3(0.006, 0.042, 0.002),
             base + v3(0.004, 0.058, 0.018), base + v3(-0.004, 0.060, 0.034), base + v3(-0.010, 0.052, 0.042)]
        )
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        acc = np.concatenate([[0], np.cumsum(seg)])
        ts = np.linspace(0, acc[-1], 22)
        path = np.column_stack([np.interp(ts, acc, pts[:, k]) for k in range(3)])
        tt = ts / acc[-1]
        w = 0.0075 * (1 - tt) ** 0.7 + 0.0003
        h = 0.0022 * (1 - tt) ** 0.5 + 0.0003
        rings = frame_rings(path, w, h, 10, up_hint=v3(1, 0, 0))
        P, _, I, ring, col = loft(rings)
        UV = np.column_stack([0.02 + col * 0.29, np.interp(ring, np.arange(len(ts)), tt)])
        names = []
        parent = "J_Head"
        for j, k in enumerate((0, 10, 21)):
            name = f"J_Ahoge_{j}" if j < 2 else "J_Ahoge_end"
            self.sk.add(name, parent, path[k])
            names.append(name)
            parent = name
        self.chains.append(("ahoge", self.sk.id(names[0])))
        s = np.interp(ring, [0, 10, 21], [0, 1, 2])
        W = chain_weights(s, 2, blend=0.3)
        self.prim.add(P, UV, pack([self.sk.id(n) for n in names[:2]], W), I)


def build_hair(sk, prims):
    hb = HairBuilder(sk, prims["Hair"])
    hb.cap()
    # crown: short locks that radiate from the whorl, no bones
    for k in range(10):
        ph = -180 + k * 36 + 10
        hb.clump(2, ph, 55 + 25 * (1 - math.cos(math.radians(ph))) / 2, 0, 0.030, 0.006, bones=0)
    # back and sides: a bob that ends at the collarbone and flicks inward
    back = list(range(62, 299, 12))
    for k, ph in enumerate(back):
        colour = "pink" if ph in (122, 230) else ("fade" if ph in (86, 266) else "cyan")
        hb.clump(16 + (k % 3) * 5, ph, 98, 0.125 + 0.014 * math.sin(k * 1.7), 0.034, 0.010, colour,
                 group="hair", flare=0.008, curl=0.008, dphi=(ph - 180) * -0.06)
    # inner colour: pink layer tucked under the bob, a little longer
    for ph in range(82, 285, 24):
        hb.clump(40, ph, 100, 0.142, 0.030, 0.006, "pink", group="hair", scale=0.955, flare=0.004, curl=0.010)
    # side locks framing the face; her right side (+X) is the pink one
    for ph, colour, drop in ((52, "pink", 0.175), (66, "pink", 0.16), (-52, "fade", 0.175), (-66, "cyan", 0.16)):
        hb.clump(20, ph, 84, drop, 0.022, 0.007, colour, group="side", flare=0.004, curl=-0.002,
                 forward=0.012, dphi=-ph * 0.05, bones=4)
    # bangs: long, split in the middle, one falling between the eyes
    bangs = [
        (-44, 16, 0.070, "cyan", 0.016),
        (-33, 13, 0.060, "cyan", 0.016),
        (-22, 10, 0.050, "cyan", 0.016),
        (-11, 9, 0.058, "pink", 0.014),
        (-1, 10, 0.074, "cyan", 0.013),
        (10, 9, 0.052, "cyan", 0.015),
        (21, 10, 0.060, "pink", 0.016),
        (32, 13, 0.058, "pink", 0.016),
        (44, 16, 0.072, "pink", 0.016),
    ]
    for ph, t0, drop, colour, width in bangs:
        hb.clump(t0, ph, 66, drop, width, 0.0055, colour, group="bangs", flare=0.004, curl=0.0,
                 dphi=ph * 0.12, forward=0.004, bones=2)
    hb.ahoge()
    return hb


# --------------------------------------------------------------------------
# clothes and accessories
# --------------------------------------------------------------------------


def build_clothes(sk, prims):
    head = sk.id("J_Head")
    neck = sk.id("J_Neck")

    # ---- hoodie: sleeves ------------------------------------------------
    for side, sx in (("L", -1), ("R", 1)):
        xs = np.linspace(0.195, WRIST_X + 0.020, 26)
        path = np.column_stack([sx * xs, ARM_Y - 0.004 - 0.004 * np.sin(np.linspace(0, math.pi, 26)), np.zeros_like(xs)])
        r = np.interp(xs, [0.195, 0.21, 0.30, 0.40, 0.47, 0.50, 0.515, 0.565], [0.041, 0.046, 0.046, 0.043, 0.040, 0.033, 0.029, 0.030])
        rings = frame_rings(path, r, r, 20, up_hint=v3(0, 1, 0))
        P, UV, I, ring, col = loft(rings)
        ax = np.abs(P[:, 0])
        bones = [sk.id(f"J_UpperArm_{side}"), sk.id(f"J_LowerArm_{side}"), sk.id(f"J_Hand_{side}")]
        W = chain_weights(chain_param(ax, [UPPER_ARM_X, ELBOW_X, WRIST_X, 0.7]), 3, blend=0.2)
        prims["Hoodie"].add(P, UV, pack(bones, W), I)
        # rib cuff and the rolled edge where it slid off the shoulder
        for x0, rr, tube in ((0.505, 0.031, 0.006), (0.197, 0.043, 0.005)):
            rings = torus_rings(v3(sx * x0, ARM_Y - 0.004, 0), v3(1, 0, 0), rr, tube, 28, 8)
            P, UV, I, _, _ = loft(rings, closed=True)
            W = chain_weights(chain_param(np.abs(P[:, 0]), [UPPER_ARM_X, ELBOW_X, WRIST_X, 0.7]), 3, blend=0.2)
            prims["HoodieRib"].add(P, UV, pack(bones, W), I)

    # ---- hoodie: body, open at the front and slipped off the shoulders ---
    alphas = np.linspace(math.radians(52), math.radians(308), 44)

    def top_edge(al):
        side = np.abs(np.sin(al))
        return 1.045 + 0.062 * side**3 - 0.03 * (np.cos(al) > 0) * np.cos(al) ** 2

    ys_t = np.linspace(0, 1, 24)
    rings = []
    for f in ys_t:
        yb = 0.765 - 0.012 * np.cos(alphas)
        y = yb + (top_edge(alphas) - yb) * f
        pts = torso_point(y, alphas, grow=0.024)
        pts[:, 0] += np.sign(pts[:, 0]) * np.abs(np.sin(alphas)) ** 4 * smoothstep(0.98, 1.105, y) * 0.07
        pts[:, 1] += np.abs(np.sin(alphas)) ** 6 * smoothstep(1.02, 1.1, y) * 0.004
        # a looser hem
        pts[:, 0] += np.sign(pts[:, 0]) * (1 - f) ** 3 * 0.01
        rings.append(pts)
    rings = np.array(rings)
    P, UV, I, ring, col = loft(rings, closed=False)
    W_t = chain_weights(chain_param(P[:, 1], TORSO_JOINTS), 6, blend=0.3)
    arm = smoothstep(0.13, 0.20, np.abs(P[:, 0])) * smoothstep(1.0, 1.10, P[:, 1])
    Wm = np.hstack([W_t * (1 - arm)[:, None], (arm * (P[:, 0] < 0))[:, None], (arm * (P[:, 0] > 0))[:, None]])
    bones = torso_bones(sk) + [sk.id("J_UpperArm_L"), sk.id("J_UpperArm_R")]
    prims["Hoodie"].add(P, UV, pack(bones, Wm), I)

    # hood bunched up along the top edge, and the zip tapes down the front
    top = rings[-1]
    hood_r = 0.005 + 0.023 * np.cos(np.linspace(-math.pi / 2, math.pi / 2, len(top))) ** 2
    back_out = norm(top - v3(0, 1.0, 0.0) * v3(0, 1, 0) - v3(0, 0, 0) * 0)
    path = top + v3(0, 0.004, 0) + norm(top * v3(1, 0, 1)) * 0.004
    rings2 = frame_rings(path, hood_r, hood_r * 0.8, 12, up_hint=v3(0, 1, 0))
    P, UV, I, ring, col = loft(rings2, cap0=True, cap1=True)
    W_t = chain_weights(chain_param(P[:, 1], TORSO_JOINTS), 6, blend=0.3)
    arm = smoothstep(0.13, 0.20, np.abs(P[:, 0])) * smoothstep(1.0, 1.10, P[:, 1])
    Wm = np.hstack([W_t * (1 - arm)[:, None], (arm * (P[:, 0] < 0))[:, None], (arm * (P[:, 0] > 0))[:, None]])
    prims["HoodieRib"].add(P, UV, pack(bones, Wm), I)
    del back_out
    for edge in (rings[:, 0], rings[:, -1]):
        rr = np.full(len(edge), 0.0045)
        rings3 = frame_rings(edge, rr, rr * 0.6, 8, up_hint=v3(0, 0, -1))
        P, UV, I, _, _ = loft(rings3, cap0=True, cap1=True)
        prims["Zip"].add(P, UV, torso_weights(sk, P[:, 1]), I)
    # hem rib
    hem = rings[0]
    rr = np.full(len(hem), 0.008)
    rings4 = frame_rings(hem, rr, rr * 0.8, 10, up_hint=v3(0, 1, 0))
    P, UV, I, _, _ = loft(rings4, cap0=True, cap1=True)
    prims["HoodieRib"].add(P, UV, torso_weights(sk, P[:, 1]), I)

    # ---- choker: two black bands and the white "nap switch" ---------------
    for y in (1.212, 1.197):
        a, bf, bb = torso_profile(y)
        phis = np.linspace(-math.pi, math.pi, 40, endpoint=False)
        ring = torso_point(y, phis, grow=0.0035)
        ring = np.vstack([ring, ring[:1]])
        rr = np.full(len(ring), 0.0027)
        rings = frame_rings(ring, rr, rr * 1.3, 8, up_hint=v3(0, 1, 0))
        P, UV, I, _, _ = loft(rings)
        prims["Choker"].add(P, UV, single(neck, len(P)), I)
    front = torso_point(1.197, np.array([0.0]), grow=0.0035)[0]
    bead = front + v3(0, -0.0085, -0.004)
    rings = sphere_rings(bead, 0.0068)
    P, UV, I, _, _ = loft(rings)
    prims["Bead"].add(P, UV, single(neck, len(P)), I)
    rings = torus_rings(front + v3(0, -0.0015, -0.003), v3(1, 0, 0), 0.0028, 0.0009, 16, 6)
    P, UV, I, _, _ = loft(rings)
    prims["Zip"].add(P, UV, single(neck, len(P)), I)

    # ---- goggles pushed up on the head ------------------------------------
    def strap_dir(psi):
        th = math.radians(33) + math.radians(64) * (1 - np.cos(psi)) / 2
        return sph(th, psi)

    psis = np.linspace(-math.pi, math.pi, 72, endpoint=False)
    strap = shell(strap_dir(psis), 1.0)
    outward = norm(strap - HC)
    strap = strap + outward * 0.014
    strap = np.vstack([strap, strap[:1]])
    T = norm(np.gradient(strap, axis=0))
    rings = []
    for i, p in enumerate(strap):
        o = norm(p - HC)
        bvec = norm(np.cross(T[i], o))
        rings.append([p + bvec * 0.0115 + o * 0.0016, p - bvec * 0.0115 + o * 0.0016,
                      p - bvec * 0.0115 - o * 0.0016, p + bvec * 0.0115 - o * 0.0016])
    P, UV, I, _, _ = loft(np.array(rings))
    prims["GoggleGrey"].add(P, UV, single(head, len(P)), I)

    lens_centres = []
    for sx in (-1, 1):
        psi = math.radians(26) * sx
        d = strap_dir(np.array(psi))
        base = shell(d, 1.0)
        ax = norm(base - HC)
        # tip the lenses forward a little, like they were just pushed up
        ax = norm(ax + v3(0, 0, -0.35))
        c = base + ax * 0.024
        lens_centres.append((c, ax))
        rings = torus_rings(c, ax, 0.0255, 0.0075, 40, 12)
        P, UV, I, _, _ = loft(rings)
        prims["Goggle"].add(P, UV, single(head, len(P)), I)
        # cup down to the strap
        cup = []
        for k, (off, rad) in enumerate(((0.0, 0.029), (-0.010, 0.028), (-0.018, 0.024))):
            ring = torus_rings(c + ax * off, ax, rad, 0.0001, 40, 1)[:-1, 0]
            cup.append(ring)
        P, UV, I, _, _ = loft(np.array(cup), cap1=True)
        prims["Goggle"].add(P, UV, single(head, len(P)), I)
        rings = torus_rings(c + ax * 0.005, ax, 0.0195, 0.0032, 36, 8)
        P, UV, I, _, _ = loft(rings)
        prims["GoggleGrey"].add(P, UV, single(head, len(P)), I)
        disc = torus_rings(c + ax * 0.0035, ax, 0.0195, 0.0001, 36, 1)[:-1, 0]
        rings = np.array([disc, c + ax * 0.0075 + (disc - c - ax * 0.0035) * 0.2])
        P, UV, I, _, _ = loft(rings, cap1=True)
        prims["Lens"].add(P, UV, single(head, len(P)), I)
    (c1, a1), (c2, a2) = lens_centres
    path = np.array([c1 + (c2 - c1) * t + norm(a1 + a2) * (0.004 + 0.004 * math.sin(math.pi * t)) for t in np.linspace(0.18, 0.82, 10)])
    rr = np.full(len(path), 0.0045)
    rings = frame_rings(path, rr, rr, 10, up_hint=norm(a1 + a2))
    P, UV, I, _, _ = loft(rings, cap0=True, cap1=True)
    prims["GoggleGrey"].add(P, UV, single(head, len(P)), I)

    # ---- sneakers ---------------------------------------------------------
    for side, sx in (("L", -1), ("R", 1)):
        foot, toes = sk.id(f"J_Foot_{side}"), sk.id(f"J_Toes_{side}")
        zs = np.linspace(0.055, -0.135, 22)
        hw = np.interp(zs, [-0.135, -0.12, -0.08, -0.02, 0.03, 0.055], [0.018, 0.030, 0.038, 0.035, 0.032, 0.022])
        top = np.interp(zs, [-0.135, -0.12, -0.07, -0.02, 0.02, 0.055], [0.030, 0.040, 0.052, 0.080, 0.100, 0.095])
        bot = np.full_like(zs, 0.016)
        rings = []
        ang = np.linspace(-math.pi, math.pi, 20, endpoint=False)
        for z, w, t, b in zip(zs, hw, top, bot):
            ca, sa = np.cos(ang), np.sin(ang)
            sq = np.sign(ca) * np.abs(ca) ** 0.7, np.sign(sa) * np.abs(sa) ** 0.7
            x = sx * 0.068 + sq[1] * w
            y = (t + b) / 2 + sq[0] * (t - b) / 2
            rings.append(np.column_stack([x, y, np.full_like(x, z)]))
        rings = np.array(rings)
        P, UV, I, ring, col = loft(rings, cap0=True, cap1=True)
        W = chain_weights(chain_param(-P[:, 2], [-0.1, 0.03, 0.2]), 2, blend=0.3)
        prims["Shoe"].add(P, UV, pack([foot, toes], W), I)
        sole = rings.copy()
        sole[..., 1] = np.clip(sole[..., 1], None, 0.03) - 0.014
        sole[..., 0] = sx * 0.068 + (sole[..., 0] - sx * 0.068) * 1.07
        sole[:, :, 2] = np.clip(sole[:, :, 2] * 1.03, -0.14, 0.06)
        P, UV, I, ring, col = loft(sole, cap0=True, cap1=True)
        W = chain_weights(chain_param(-P[:, 2], [-0.1, 0.03, 0.2]), 2, blend=0.3)
        prims["Sole"].add(P, UV, pack([foot, toes], W), I)
        # a pink collar around the ankle opening
        rings = torus_rings(v3(sx * 0.068, 0.098, 0.030), v3(0, 1, 0.25), 0.029, 0.0045, 24, 8)
        P, UV, I, _, _ = loft(rings)
        prims["Sole"].add(P, UV, single(foot, len(P)), I)


# --------------------------------------------------------------------------
# textures
# --------------------------------------------------------------------------


def rgb255(h):
    return tuple(int(round(c * 255)) for c in hex_rgb(h))


def tex_body(size=1024):
    img = np.zeros((size, size, 3), dtype=np.float64)
    img[:] = hex_rgb(SKIN)
    H = size
    # torso: u in [0, .5], v 0..1 = y 1.33 .. 0.705
    px = np.arange(size // 2)
    py = np.arange(H)
    uu, vv = np.meshgrid((px + 0.5) / (size / 2), (py + 0.5) / H)
    phi = uu * 2 * math.pi - math.pi
    y = TORSO_TOP - vv * (TORSO_TOP - TORSO_BOTTOM)
    ap = np.degrees(np.abs(phi))
    neck_front = 1.052 + 0.052 * (ap / 30) ** 2.2
    strap_front = (ap > 27) & (ap < 42)
    strap_back = (ap > 138) & (ap < 153)
    top = np.where(ap < 30, neck_front, 1.098)
    top = np.where(ap > 150, 1.110, top)
    top = np.where(strap_front | strap_back, 1.20, top)
    tank = (y < top) & (y > 0.842)
    shorts = y <= 0.846
    torso = img[:, : size // 2]
    torso[tank] = hex_rgb(TANK)
    # trim follows every edge of the top
    edge = tank & ((top - y < 0.007) | (strap_front & ((np.abs(ap - 27) < 1.3) | (np.abs(ap - 42) < 1.3)) & (y > 1.03))
                   | (strap_back & ((np.abs(ap - 138) < 1.3) | (np.abs(ap - 153) < 1.3)) & (y > 1.06)))
    edge &= y < 1.195
    torso[edge] = hex_rgb(TANK_TRIM)
    torso[shorts] = hex_rgb(SHORTS)
    torso[(y > 0.83) & (y <= 0.846)] = hex_rgb("#3A4180")
    stitch = (np.abs(ap - 180) < 0.6) & shorts | ((np.abs(y - 0.828) < 0.0012) & shorts)
    torso[stitch] = hex_rgb("#6C7AC4")
    img[:, : size // 2] = torso
    # legs: u in [.5,.75], v 0..1 = y 0.84 .. 0.045
    leg = img[:, size // 2 : size * 3 // 4]
    yl = 0.84 - (py + 0.5) / H * 0.795
    Y = np.repeat(yl[:, None], leg.shape[1], axis=1)
    leg[Y > 0.690] = hex_rgb(SHORTS)
    leg[(Y > 0.690) & (Y < 0.702)] = hex_rgb("#3A4180")
    leg[Y < 0.370] = hex_rgb(SOCKS)
    leg[(Y < 0.355) & (Y > 0.345)] = hex_rgb("#F59BCF")
    leg[(Y < 0.338) & (Y > 0.330)] = hex_rgb(HAIR_CYAN[1])
    img[:, size // 2 : size * 3 // 4] = leg
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    return im.filter(ImageFilter.GaussianBlur(0.6))


def tex_face(tris, w=1024, h=512):
    im = Image.new("RGB", (w, h), rgb255(SKIN))
    over = Image.new("RGBA", (w, h), (255, 150, 170, 0))
    d = ImageDraw.Draw(over)

    def px(x, y):  # head-relative metres on the face -> pixels
        z = raycast_z(tris, [(x + C[0], y + C[1])])[0]
        u, v = face_uv([(x + C[0], y + C[1], z)])[0]
        return (u * w, v * h)

    for sx in (-1, 1):
        cx, cy = px(sx * 0.044, -0.056)
        ex, _ = px(sx * 0.060, -0.056)
        rx, ry = abs(ex - cx), 0.009 / 0.26 * h
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(255, 150, 170, 150))
    over = over.filter(ImageFilter.GaussianBlur(7))
    d = ImageDraw.Draw(over)
    for sx in (-1, 1):
        for k in range(3):
            x0, y0 = px(sx * (0.037 + k * 0.007), -0.053)
            x1, y1 = px(sx * (0.037 + k * 0.007) - 0.003, -0.061)
            d.line((x0, y0, x1, y1), fill=(240, 110, 140, 150), width=2)
    # a hint of a nose
    nx, ny = px(0.0, -0.056)
    d.ellipse((nx - 1.5, ny - 1.5, nx + 1.5, ny + 1.5), fill=(230, 160, 160, 160))
    im = im.convert("RGBA")
    im.alpha_composite(over)
    return im.convert("RGB")


def tex_hair(w=512, h=512):
    img = np.zeros((h, w, 3))
    v = (np.arange(h) + 0.5) / h
    cols = [HAIR_CYAN, HAIR_PINK, None]
    for k in range(3):
        if k < 2:
            root, mid, tip = (np.array(hex_rgb(c)) for c in cols[k])
        else:
            root, mid = (np.array(hex_rgb(c)) for c in HAIR_CYAN[:2])
            tip = np.array(hex_rgb(HAIR_PINK[1]))
        g = np.where(v[:, None] < 0.45, root + (mid - root) * (v[:, None] / 0.45), mid + (tip - mid) * ((v[:, None] - 0.45) / 0.55))
        img[:, k * w // 3 : (k + 1) * w // 3] = g[:, None, :]
    rng = np.random.default_rng(7)
    # fine strands: darker lines that fade toward the tips
    for k in range(3):
        for _ in range(9):
            x = k * w // 3 + rng.integers(8, w // 3 - 8)
            ln = rng.uniform(0.35, 0.9)
            ys = np.arange(int(h * ln))
            img[ys, x] *= 0.9
            img[ys, x + 1] *= 0.94
    # a soft sheen band
    band = np.exp(-((v - 0.2) / 0.045) ** 2)[:, None, None]
    img = img + (1 - img) * band * 0.45
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    return im.filter(ImageFilter.GaussianBlur(0.8))


def tex_iris(size=256):
    ss = size * 4
    im = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:ss, 0:ss] / ss - 0.5
    r = np.sqrt((xx / 0.5) ** 2 + (yy / 0.5) ** 2)
    t = np.clip(yy / 0.5 * 0.5 + 0.5, 0, 1)[..., None]
    dark, mid, light = (np.array(hex_rgb(c)) for c in (IRIS_DARK, IRIS_MID, IRIS_LIGHT))
    col = np.where(t < 0.55, dark + (mid - dark) * (t / 0.55), mid + (light - mid) * ((t - 0.55) / 0.45))
    col = np.where((r > 0.86)[..., None], dark * 0.8, col)
    pupil = np.sqrt((xx / 0.2) ** 2 + ((yy + 0.03) / 0.26) ** 2) < 1
    col[pupil] = np.array(hex_rgb("#10164D"))
    # radial streaks
    ang = np.arctan2(yy, xx)
    streak = (np.sin(ang * 22) * 0.5 + 0.5) ** 6 * ((r > 0.35) & (r < 0.82))
    col = col + (np.array(hex_rgb("#9EEBFF")) - col) * (streak[..., None] * 0.35 * t)
    a = (r < 1.0).astype(np.float64)
    arr = np.dstack([np.clip(col, 0, 1), a])
    im = Image.fromarray((arr * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    # highlights: a big one up-left, a small one down-right, a pink glint
    d.ellipse((ss * 0.18, ss * 0.16, ss * 0.43, ss * 0.40), fill=(255, 255, 255, 255))
    d.ellipse((ss * 0.60, ss * 0.62, ss * 0.72, ss * 0.74), fill=(255, 255, 255, 255))
    d.ellipse((ss * 0.62, ss * 0.20, ss * 0.70, ss * 0.28), fill=(255, 190, 235, 255))
    return im.resize((size, size), Image.LANCZOS)


def tex_eyewhite(size=64):
    v = (np.arange(size) + 0.5) / size
    top = np.array(hex_rgb("#CFC6EC"))
    white = np.array([1.0, 1.0, 1.0])
    g = top + (white - top) * smoothstep(0.0, 0.45, v)[:, None]
    img = np.repeat(g[:, None, :], size, axis=1)
    return Image.fromarray((img * 255).astype(np.uint8))


def tex_mouth(size=128):
    img = np.zeros((size, size, 3))
    v = (np.arange(size) + 0.5) / size
    u = (np.arange(size) + 0.5) / size
    uu, vv = np.meshgrid(u, v)
    img[:] = hex_rgb("#7A2346")
    tongue = ((uu - 0.5) / 0.32) ** 2 + ((vv - 1.0) / 0.45) ** 2 < 1
    img[tongue] = hex_rgb("#FF8DA6")
    teeth = vv < 0.14
    img[teeth] = hex_rgb("#FFFFFF")
    # the fang, on her right (the texture is not mirrored: u grows to +X)
    for fx in (0.30, 0.70):
        fang = (vv < 0.30) & (np.abs(uu - fx) < 0.07 * (1 - vv / 0.30))
        img[fang] = hex_rgb("#FFFFFF")
    border = (vv > 0.93) | (uu < 0.03) | (uu > 0.97)
    img[border] = hex_rgb("#5A1832")
    return Image.fromarray((img * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))


# --------------------------------------------------------------------------
# materials (glTF + VRM0 MToon properties)
# --------------------------------------------------------------------------

MATERIALS = {
    # name: dict(color, shade, tex, blend, outline, cull, outline_color)
    "Body": dict(color="#FFFFFF", shade="#E9C5D3", tex="body", outline=0.10, outline_color="#8A5A7A"),
    "FaceSkin": dict(color="#FFFFFF", shade="#F4D0D2", tex="face", outline=0.0, shade_shift=-0.3),
    "EyeWhite": dict(color="#FFFFFF", shade="#FFFFFF", tex="eyewhite", outline=0.0),
    "Iris": dict(color="#FFFFFF", shade="#FFFFFF", tex="iris", blend="cutout", outline=0.0),
    "Line": dict(color=LASH, shade=LASH, outline=0.0),
    "Mouth": dict(color="#FFFFFF", shade="#FFFFFF", tex="mouth", outline=0.0),
    "Hair": dict(color="#FFFFFF", shade="#9C9EE0", tex="hair", outline=0.11, outline_color="#3E5C9A", cull="off"),
    "Hoodie": dict(color=HOODIE, shade=HOODIE_SHADE, outline=0.10, outline_color="#10122E", cull="off"),
    "HoodieRib": dict(color="#2C3170", shade="#171A42", outline=0.08, outline_color="#10122E"),
    "Zip": dict(color="#5560A8", shade="#2C3170", outline=0.04, outline_color="#262A50"),
    "Choker": dict(color=CHOKER, shade="#0C0C12", outline=0.03, outline_color="#000000"),
    "Bead": dict(color="#FFFFFF", shade="#D7DBF0", outline=0.03, outline_color="#5A5F80"),
    "Goggle": dict(color=GOGGLE, shade="#B23BC4", outline=0.08, outline_color="#5E1A6E", cull="off"),
    "GoggleGrey": dict(color=GOGGLE_GREY, shade="#4B5169", outline=0.06, outline_color="#262A3C"),
    "Lens": dict(color=LENS, shade="#B98BE8", blend="transparent", alpha=0.7, outline=0.0),
    "Shoe": dict(color="#F6F6FB", shade="#C9CAE3", outline=0.08, outline_color="#4C4F74"),
    "Sole": dict(color="#F59BCF", shade="#D86BAE", outline=0.06, outline_color="#6E2B58"),
}
MESHES = {
    "Body": ["Body"],
    "Face": ["FaceSkin", "EyeWhite", "Iris", "Line", "Mouth"],
    "Hair": ["Hair"],
    "Clothes": ["Hoodie", "HoodieRib", "Zip", "Choker", "Bead", "Shoe", "Sole"],
    "Goggles": ["Goggle", "GoggleGrey", "Lens"],
}
MORPHS = [
    "Blink_L", "Blink_R", "EyeJoy_L", "EyeJoy_R",
    "MouthA", "MouthI", "MouthU", "MouthE", "MouthO", "MouthFun", "MouthSorrow", "MouthAngry",
    "BrowUp", "BrowAngry", "BrowSorrow",
]


def mtoon_props(name, spec, tex_index):
    blend = spec.get("blend", "opaque")
    mode = {"opaque": 0, "cutout": 1, "transparent": 2}[blend]
    color = list(hex_rgb(spec["color"])) + [spec.get("alpha", 1.0)]
    shade = list(hex_rgb(spec["shade"])) + [1.0]
    outline = spec.get("outline", 0.0)
    oc = list(hex_rgb(spec.get("outline_color", "#000000"))) + [1.0]
    cull = {"off": 0, "front": 1, "back": 2}[spec.get("cull", "back")]
    floats = {
        "_Cutoff": 0.5, "_BumpScale": 1.0, "_ReceiveShadowRate": 1.0, "_ShadingGradeRate": 1.0,
        "_ShadeShift": spec.get("shade_shift", -0.1), "_ShadeToony": 0.92, "_LightColorAttenuation": 0.0,
        "_IndirectLightIntensity": 0.1, "_RimLightingMix": 0.0, "_RimFresnelPower": 1.0, "_RimLift": 0.0,
        "_OutlineWidth": outline, "_OutlineScaledMaxDistance": 1.0, "_OutlineLightingMix": 1.0,
        "_UvAnimScrollX": 0.0, "_UvAnimScrollY": 0.0, "_UvAnimRotation": 0.0, "_MToonVersion": 38,
        "_DebugMode": 0, "_BlendMode": mode, "_OutlineWidthMode": 1 if outline > 0 else 0,
        "_OutlineColorMode": 1, "_CullMode": cull, "_OutlineCullMode": 1,
        "_SrcBlend": 5 if mode == 2 else 1, "_DstBlend": 10 if mode == 2 else 0, "_ZWrite": 0 if mode == 2 else 1,
    }
    vectors = {
        "_Color": color, "_ShadeColor": shade, "_MainTex": [0, 0, 1, 1], "_ShadeTexture": [0, 0, 1, 1],
        "_BumpMap": [0, 0, 1, 1], "_ReceiveShadowTexture": [0, 0, 1, 1], "_ShadingGradeTexture": [0, 0, 1, 1],
        "_RimColor": [0, 0, 0, 1], "_RimTexture": [0, 0, 1, 1], "_SphereAdd": [0, 0, 1, 1],
        "_EmissionColor": [0, 0, 0, 1], "_EmissionMap": [0, 0, 1, 1], "_OutlineWidthTexture": [0, 0, 1, 1],
        "_OutlineColor": oc, "_UvAnimMaskTexture": [0, 0, 1, 1],
    }
    textures = {}
    if tex_index is not None:
        textures = {"_MainTex": tex_index, "_ShadeTexture": tex_index}
    keywords = {}
    if outline > 0:
        keywords["MTOON_OUTLINE_WIDTH_WORLD"] = True
        keywords["MTOON_OUTLINE_COLOR_MIXED"] = True
    if mode == 1:
        keywords["_ALPHATEST_ON"] = True
    if mode == 2:
        keywords["_ALPHABLEND_ON"] = True
    render_type = {0: "Opaque", 1: "TransparentCutout", 2: "Transparent"}[mode]
    queue = {0: 2000, 1: 2450, 2: 3000}[mode]
    return {
        "name": name, "shader": "VRM/MToon", "renderQueue": queue,
        "floatProperties": floats, "vectorProperties": vectors, "textureProperties": textures,
        "keywordMap": keywords, "tagMap": {"RenderType": render_type},
    }


# --------------------------------------------------------------------------
# glTF / GLB writer
# --------------------------------------------------------------------------


class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.views = []
        self.accessors = []

    def view(self, data: bytes, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bin.extend(data)
        self.views.append(v)
        return len(self.views) - 1

    def accessor(self, arr, ctype, atype, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        dtype = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[ctype]
        data = arr.astype(dtype)
        bv = self.view(data.tobytes(), target)
        acc = {"bufferView": bv, "componentType": ctype, "count": int(len(arr)), "type": atype}
        if minmax:
            acc["min"] = [float(x) for x in data.reshape(len(arr), -1).min(axis=0)]
            acc["max"] = [float(x) for x in data.reshape(len(arr), -1).max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


HEAD_SCALE = 1.10
HEAD_PRIMS = ("FaceSkin", "EyeWhite", "Iris", "Line", "Mouth", "Hair", "Goggle", "GoggleGrey", "Lens")


def scale_head(sk, prims):
    """Grow the whole head (face, hair, goggles) about its centre.

    The head is modelled at life-ish size; anime proportions want it bigger.
    Doing it as one final step keeps every number above easy to reason about.
    """
    for name in HEAD_PRIMS:
        pr = prims[name]
        pr.P = [C + (P - C) * HEAD_SCALE for P in pr.P]
        pr.morphs = {k: [(o, d * HEAD_SCALE) for o, d in v] for k, v in pr.morphs.items()}
    head = sk.id("J_Head")

    def under_head(i):
        while sk.parent[i] >= 0:
            i = sk.parent[i]
            if i == head:
                return True
        return False

    for i in range(len(sk.names)):
        if under_head(i):
            sk.pos[i] = C + (sk.pos[i] - C) * HEAD_SCALE


def build(out: Path, thumbnail: Path | None):
    sk = build_skeleton()
    prims = {name: Prim(name) for name in MATERIALS}
    build_body(sk, prims)
    tris = build_head(sk, prims)
    build_face(sk, prims, tris)
    hair = build_hair(sk, prims)
    build_clothes(sk, prims)
    scale_head(sk, prims)

    glb = GLB()
    # ---- textures --------------------------------------------------------
    tex_imgs = {
        "body": tex_body(), "face": tex_face(tris), "hair": tex_hair(), "iris": tex_iris(),
        "eyewhite": tex_eyewhite(), "mouth": tex_mouth(),
    }
    images, textures, tex_index = [], [], {}
    for key, im in tex_imgs.items():
        bv = glb.view(png_bytes(im))
        images.append({"name": key, "bufferView": bv, "mimeType": "image/png"})
        textures.append({"sampler": 0, "source": len(images) - 1})
        tex_index[key] = len(textures) - 1
    thumb_tex = None
    if thumbnail and thumbnail.exists():
        im = Image.open(thumbnail).convert("RGB")
        bv = glb.view(png_bytes(im))
        images.append({"name": "thumbnail", "bufferView": bv, "mimeType": "image/png"})
        textures.append({"sampler": 0, "source": len(images) - 1})
        thumb_tex = len(textures) - 1

    # ---- materials -------------------------------------------------------
    materials, mprops, mat_index = [], [], {}
    for name, spec in MATERIALS.items():
        ti = tex_index.get(spec.get("tex")) if spec.get("tex") else None
        col = list(to_linear(hex_rgb(spec["color"]))) + [spec.get("alpha", 1.0)]
        m = {
            "name": name,
            "pbrMetallicRoughness": {"baseColorFactor": col, "metallicFactor": 0.0, "roughnessFactor": 0.9},
            "doubleSided": spec.get("cull") == "off",
            "extensions": {"KHR_materials_unlit": {}},
        }
        if ti is not None:
            m["pbrMetallicRoughness"]["baseColorTexture"] = {"index": ti}
        blend = spec.get("blend", "opaque")
        if blend == "cutout":
            m["alphaMode"], m["alphaCutoff"] = "MASK", 0.5
        elif blend == "transparent":
            m["alphaMode"] = "BLEND"
        materials.append(m)
        mprops.append(mtoon_props(name, spec, ti))
        mat_index[name] = len(materials) - 1

    # ---- nodes -----------------------------------------------------------
    nodes = []
    for i, name in enumerate(sk.names):
        par = sk.parent[i]
        local = sk.pos[i] - (sk.pos[par] if par >= 0 else 0)
        nodes.append({"name": name, "translation": [float(x) for x in local]})
    for i, par in enumerate(sk.parent):
        if par >= 0:
            nodes[par].setdefault("children", []).append(i)
    ibm = np.zeros((len(sk.names), 16), dtype=np.float32)
    for i, p in enumerate(sk.pos):
        m = np.eye(4, dtype=np.float32)
        m[:3, 3] = -p
        ibm[i] = m.T.reshape(-1)  # column-major
    ibm_acc = glb.accessor(ibm, 5126, "MAT4")
    skins = [{"name": "skin", "joints": list(range(len(sk.names))), "inverseBindMatrices": ibm_acc, "skeleton": 0}]

    meshes, mesh_nodes, mesh_index = [], [], {}
    for mname, pnames in MESHES.items():
        mesh = {"name": mname, "primitives": []}
        use_morph = mname == "Face"
        for pn in pnames:
            a = prims[pn].arrays(MORPHS if use_morph else [])
            if len(a["P"]) == 0:
                continue
            attrs = {
                "POSITION": glb.accessor(a["P"], 5126, "VEC3", 34962, True),
                "NORMAL": glb.accessor(a["N"], 5126, "VEC3", 34962),
                "TEXCOORD_0": glb.accessor(a["UV"], 5126, "VEC2", 34962),
                "JOINTS_0": glb.accessor(a["J"], 5123, "VEC4", 34962),
                "WEIGHTS_0": glb.accessor(a["W"], 5126, "VEC4", 34962),
            }
            prim = {
                "attributes": attrs,
                "indices": glb.accessor(a["I"].reshape(-1), 5125, "SCALAR", 34963),
                "material": mat_index[pn],
                "mode": 4,
            }
            if use_morph:
                prim["targets"] = [{"POSITION": glb.accessor(d, 5126, "VEC3", 34962, True)} for d in a["morphs"]]
                prim["extras"] = {"targetNames": MORPHS}
            mesh["primitives"].append(prim)
        if use_morph:
            mesh["extras"] = {"targetNames": MORPHS}
            mesh["weights"] = [0.0] * len(MORPHS)
        meshes.append(mesh)
        mesh_index[mname] = len(meshes) - 1
        nodes.append({"name": mname, "mesh": len(meshes) - 1, "skin": 0})
        mesh_nodes.append(len(nodes) - 1)

    # ---- VRM extension ---------------------------------------------------
    face = mesh_index["Face"]
    M = {n: i for i, n in enumerate(MORPHS)}

    def group(name, preset, binds, binary=False):
        return {
            "name": name, "presetName": preset, "isBinary": binary, "materialValues": [],
            "binds": [{"mesh": face, "index": M[k], "weight": w} for k, w in binds],
        }

    groups = [
        group("Neutral", "neutral", []),
        group("A", "a", [("MouthA", 100)]),
        group("I", "i", [("MouthI", 100)]),
        group("U", "u", [("MouthU", 100)]),
        group("E", "e", [("MouthE", 100)]),
        group("O", "o", [("MouthO", 100)]),
        group("Blink", "blink", [("Blink_L", 100), ("Blink_R", 100)]),
        group("Blink_L", "blink_l", [("Blink_L", 100)]),
        group("Blink_R", "blink_r", [("Blink_R", 100)]),
        group("Joy", "joy", [("EyeJoy_L", 100), ("EyeJoy_R", 100), ("MouthFun", 100), ("BrowUp", 100)]),
        group("Angry", "angry", [("BrowAngry", 100), ("Blink_L", 25), ("Blink_R", 25), ("MouthAngry", 100)]),
        group("Sorrow", "sorrow", [("BrowSorrow", 100), ("Blink_L", 20), ("Blink_R", 20), ("MouthSorrow", 100)]),
        group("Fun", "fun", [("MouthFun", 100), ("BrowUp", 60)]),
        group("LookUp", "lookup", []),
        group("LookDown", "lookdown", []),
        group("LookLeft", "lookleft", []),
        group("LookRight", "lookright", []),
    ]

    human_bones = [{"bone": b, "node": n, "useDefaultValues": True} for b, n in sk.human.items()]

    # spring bones (VRM0 stores collider offsets in Unity space: z flipped)
    def col(node, *spheres):
        return {"node": sk.id(node), "colliders": [{"offset": {"x": o[0], "y": o[1], "z": -o[2]}, "radius": r} for o, r in spheres]}

    collider_groups = [
        col("J_Head", ((0, 0.11, 0.0), 0.10), ((0, 0.065, -0.038), 0.082)),
        col("J_Neck", ((0, 0.03, 0.0), 0.045)),
        col("J_UpperChest", ((0, 0.02, 0.0), 0.085), ((0.07, 0.06, 0.0), 0.05), ((-0.07, 0.06, 0.0), 0.05)),
        col("J_Chest", ((0, 0.02, -0.01), 0.09)),
        col("J_UpperArm_L", ((-0.02, 0, 0), 0.045)),
        col("J_UpperArm_R", ((0.02, 0, 0), 0.045)),
    ]
    all_cols = list(range(len(collider_groups)))
    settings = {
        "hair": dict(stiffiness=1.2, gravityPower=0.12, dragForce=0.45, hitRadius=0.018),
        "side": dict(stiffiness=1.0, gravityPower=0.15, dragForce=0.45, hitRadius=0.015),
        "bangs": dict(stiffiness=2.6, gravityPower=0.05, dragForce=0.55, hitRadius=0.010),
        "ahoge": dict(stiffiness=0.9, gravityPower=0.0, dragForce=0.3, hitRadius=0.006),
    }
    bone_groups = []
    for gname, s in settings.items():
        roots = [b for g, b in hair.chains if g == gname]
        bone_groups.append({
            "comment": gname, "stiffiness": s["stiffiness"], "gravityPower": s["gravityPower"],
            "gravityDir": {"x": 0, "y": -1, "z": 0}, "dragForce": s["dragForce"], "center": -1,
            "hitRadius": s["hitRadius"], "bones": roots, "colliderGroups": all_cols,
        })

    curve = [0, 0, 0, 1, 1, 1, 1, 0]
    vrm = {
        "exporterVersion": "nemuri-make_vrm-1.0",
        "specVersion": "0.0",
        "meta": {
            "title": "Hongou Nemuri",
            "version": "1.0",
            "author": "Hongou Nemuri",
            "contactInformation": "https://x.com/hongounemuri",
            "reference": "",
            "texture": thumb_tex if thumb_tex is not None else -1,
            "allowedUserName": "OnlyAuthor",
            "violentUssageName": "Disallow",
            "sexualUssageName": "Disallow",
            "commercialUssageName": "Allow",
            "otherPermissionUrl": "",
            "licenseName": "Redistribution_Prohibited",
            "otherLicenseUrl": "",
        },
        "humanoid": {
            "humanBones": human_bones,
            "armStretch": 0.05, "legStretch": 0.05, "upperArmTwist": 0.5, "lowerArmTwist": 0.5,
            "upperLegTwist": 0.5, "lowerLegTwist": 0.5, "feetSpacing": 0, "hasTranslationDoF": False,
        },
        "firstPerson": {
            "firstPersonBone": sk.id("J_Head"),
            "firstPersonBoneOffset": {"x": 0, "y": 0.07, "z": 0.02},
            "meshAnnotations": [{"mesh": i, "firstPersonFlag": "Auto"} for i in range(len(meshes))],
            "lookAtTypeName": "Bone",
            "lookAtHorizontalInner": {"curve": curve, "xRange": 90, "yRange": 9},
            "lookAtHorizontalOuter": {"curve": curve, "xRange": 90, "yRange": 9},
            "lookAtVerticalDown": {"curve": curve, "xRange": 90, "yRange": 5},
            "lookAtVerticalUp": {"curve": curve, "xRange": 90, "yRange": 5},
        },
        "blendShapeMaster": {"blendShapeGroups": groups},
        "secondaryAnimation": {"boneGroups": bone_groups, "colliderGroups": collider_groups},
        "materialProperties": mprops,
    }

    gltf = {
        "asset": {"version": "2.0", "generator": "nemuri make_vrm.py"},
        "extensionsUsed": ["VRM", "KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"nodes": [0] + mesh_nodes}],
        "nodes": nodes,
        "meshes": meshes,
        "skins": skins,
        "materials": materials,
        "textures": textures,
        "images": images,
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "accessors": glb.accessors,
        "bufferViews": glb.views,
        "buffers": [{"byteLength": len(glb.bin)}],
        "extensions": {"VRM": vrm},
    }
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    while len(glb.bin) % 4:
        glb.bin.append(0)
    total = 12 + 8 + len(js) + 8 + len(glb.bin)
    with open(out, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(glb.bin), 0x004E4942))
        f.write(glb.bin)
    verts = sum(len(np.concatenate(p.P)) for p in prims.values() if p.P)
    tris_n = sum(len(np.concatenate(p.I)) for p in prims.values() if p.I)
    print(f"wrote {out}  {out.stat().st_size / 1e6:.2f} MB  bones={len(sk.names)} verts={verts} tris={tris_n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "nemuri.vrm")
    ap.add_argument("--thumbnail", type=Path, default=HERE / "preview" / "thumbnail.png")
    args = ap.parse_args()
    build(args.out, args.thumbnail)


if __name__ == "__main__":
    main()
