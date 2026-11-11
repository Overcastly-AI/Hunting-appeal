"""huntkit.viz3d.cloth_pass - render-only cloth pass (BL-020).

PRESENTATION GEOMETRY ONLY. The huntkit cloth sim (``huntkit/clothsim``) stays the engineering source for every
number; this module makes the folds a photograph would show and that solver cannot reach: a part-full bag cinched
onto its contents, a rolled collar clipped down to the sides, a soft pouch sitting on the roll.

How it works (two stages, like ``studio``):

stage 1 (repo Python, numpy)   ``prepare(state)``: the huntkit drape is the seed. The flat-panel assembly X0 of the
    same mesh is the rest shape, the frame-face panel B-01 is pinned where the huntkit drape left it, a contents proxy
    of the state's volume is put inside (day 12 L, 6-day 45 L, full = the drape itself 5 mm in), W1-W3 are slabs that
    close from the seed's girth to the taut line round the contents, and the collar's closure line is carried to the
    line where the roll starts (an arch with its ends bent down to the side clips).
stage 2 (Blender's Python)     ``python -m huntkit.viz3d.cloth_pass --job <json>``: Blender's cloth solver with self
    collision runs the cinch and lets the cloth settle. Vertices come back in the seed's order, so pattern UVs, piece
    names and seams survive, and the result drops into the legacy builders as a ``sim_skin``.

The roll itself is not solved: it is the collar's own length (the 150 mm closure rule plus whatever collar the load
state leaves over) wound as a flat-folded spiral round the 20 mm hem stiffener and swept along the arch. The pouch
is a second small solve: its six flat panels draped over a contents block and the finished roll.

Entry points: ``studio.render(scene, shots, out, cloth_pass=True)`` (a scene carrying ``cloth_jobs``),
``s15_scene(state)`` (the merged bag's shell S15, wings deleted), ``run(state)`` (cached skin for one load state).
All coordinates FCS mm (x right, y aft, z up); Blender runs in metres.
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "outputs" / "cloth_pass"
PACK = REPO / "designs" / "pack_5200"


# ====================================================================================================== parameters
@dataclass
class ClothParams:
    """Every knob of the pass. Lengths mm, time in frames (24 per second), mass kg/m2.

    Values marked ASSUMPTION are picture choices, settled by a photograph of the first sewn prototype packed to the
    three loadouts; none of them feeds an engineering number."""
    level: int = 2                  # seed mesh subdivisions: h 25 -> 12.5 (1, quick) -> 6.3 mm (2, renders)
    frames_cinch: int = 50          # straps close and the lip travels over these frames
    frames_settle: int = 25         # then everything is held and the cloth settles
    quality: int = 8                # solver substeps per frame
    areal_mass: float = 0.21        # ASSUMPTION: 330D nylon + PU coat, kg/m2 (record nylon_330d_* areal mass class)
    tension: float = 40.0           # Blender cloth stiffnesses (dimensionless solver units): stiff in plane,
    compression: float = 40.0
    shear: float = 12.0
    bending: float = 0.9            # ASSUMPTION: coated 330D holds folds of 10-30 mm, not silk crumples
    damping: float = 4.0
    air_damping: float = 2.5
    self_dist: float = 1.6          # cloth-to-cloth clearance (must stay below half the mesh edge)
    coll_dist: float = 2.0          # cloth-to-collider clearance
    friction: float = 12.0
    proxy_inset: float = 5.0        # full load: the contents are the huntkit drape, this far inside it
    strap_w: float = 25.0           # W1-W3 webbing width (record poly_webbing_25mm)
    strap_bite: dict = field(default_factory=lambda: {"full": 3.0, "sixday": 4.0, "day": 12.0})
    #                                 clearance between the taut strap line and what it closes on: the cloth pile
    #                                 under the strap. ASSUMPTION (day: aft face + folded gusset = 4+ layers and air)
    roll_fold: float = 20.0         # flat of each fold = the hem stiffener width (bag_concepts.HDPE_W)
    roll_core: float = 1.0          # half thickness of the first fold (stiffener 0.8 + cloth)
    roll_pitch: float = 1.6         # ASSUMPTION: thickness added per turn per side (2 layers 330D laid loose)
    roll_closure: float = 150.0     # collar length the closed roll takes at the fill line (bag_concepts volume rule)
    roll_flat: float = 150.0        # half length of the roll's level middle before the ends bend down
    roll_bend_r: float = 60.0       # ASSUMPTION: bend radius of the roll ends
    roll_bend_deg: float = 75.0
    seed: int = 3


STATES = ("day", "sixday", "full")
STATE_LABEL = {"day": "day load, 12 L", "sixday": "6-day load, 45 L", "full": "full, 85 L class"}
# contents proxies: a rounded block against the frame face, from the floor up. w = width, z1 = top; the depth is
# solved so the block holds the state's volume (RENDER_STATES in concepts/shell_sweep.py: ASSUMPTION RS-1).
PROXY = {"day": {"w": 330.0, "z1": 470.0, "ex": 3.0, "ez": 2.6},
         "sixday": {"w": 372.0, "z1": 790.0, "ex": 5.0, "ez": 4.0}}


def _ss():
    """concepts/shell_sweep.py (BL-009) and its concept modules, imported without editing them."""
    for p in (PACK / "concepts", PACK):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import shell_sweep as SS  # noqa: E402
    return SS


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


# ============================================================================================ stage 1: the seed
def state_mesh(state: str, shell: str = "S15", torso: int = 19) -> dict:
    """Mesh of the shell for one load state (flat-panel assembly X0, triangles, piece per triangle, pattern UV) and,
    for the full state, the converged huntkit drape X. The part-full meshes only differ in collar height
    (``dome_h``: the rest of the collar is in the roll)."""
    SS = _ss()
    f = SS.RENDER_DIR / f"{shell}_PR{torso}_fine" / f"skin_{state}.pkl"
    if f.exists():
        sk = pickle.loads(f.read_bytes())
    elif state == "full":
        SS.run_render_state("full", shell, torso)                 # the engineering drape (about 2 min)
        sk = pickle.loads(f.read_bytes())
    else:                                                         # mesh only; the part-full huntkit drape diverges
        from huntkit.clothsim.pack import PackModel, load_scenario
        SS.install(SS.SHELLS[shell], SS.RENDER_STATES[state]["dome_h"])
        try:
            pm = PackModel(load_scenario(str(SS.scenario(torso))), fine=True, verbose=False)
        finally:
            SS.uninstall()
        m = pm.mesh
        uv = np.zeros((m.n, 2))
        for p in m.pieces:
            uv[p.gid] = p.xy
        sk = {"X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    out = {k: np.asarray(sk[k]) for k in ("X0", "tris", "piece", "uv")}
    if state == "full":
        out["X"] = np.asarray(sk["X"])
    return out


def subdivide(sk: dict, level: int) -> dict:
    import trimesh
    V, F = np.asarray(sk["X"], float), np.asarray(sk["tris"], int)
    att = {"x0": np.asarray(sk["X0"], float), "uv": np.asarray(sk["uv"], float)}
    piece = np.asarray(sk["piece"])
    for _ in range(level):
        V, F, att = trimesh.remesh.subdivide(V, F, vertex_attributes=att)
        piece = np.repeat(piece, 4)
    return {"X": V, "X0": att["x0"], "tris": F, "piece": piece, "uv": att["uv"]}


def seed(state: str, shell: str = "S15", torso: int = 19, level: int = 2) -> dict:
    """The cloth pass's start: the converged huntkit FULL drape, carried onto the state's mesh. Body nodes are the
    same nodes in every state (identical X0), so they start exactly on the huntkit drape; the shortened collar starts
    at its drafted shape moved with the collar seam."""
    from scipy.spatial import cKDTree
    full = state_mesh("full", shell, torso)
    sk = full if state == "full" else state_mesh(state, shell, torso)
    if state != "full":
        zc = float(full["X0"][np.unique(full["tris"][full["piece"] != "B-06"])][:, 2].max())
        body = np.where(full["X0"][:, 2] <= zc + 1e-6)[0]
        d, j = cKDTree(full["X0"][body]).query(sk["X0"], k=4)
        w = 1.0 / np.maximum(d, 1e-3) ** 2
        w /= w.sum(1, keepdims=True)
        disp = full["X"][body] - full["X0"][body]
        sk = dict(sk, X=sk["X0"] + np.einsum("ij,ijk->ik", w, disp[j]))
    out = subdivide(sk, level)
    out["state"], out["level"] = state, level
    return out


def _vnormals(V, F):
    n = np.zeros_like(V)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    for k in range(3):
        np.add.at(n, F[:, k], fn)
    n = _unit(n)
    if np.mean(np.einsum("ij,ij->i", n, V - V.mean(0))) < 0:
        n = -n
    return n


def _smooth(V, F, it=8):
    import trimesh
    tm = trimesh.Trimesh(V.copy(), F.copy(), process=False)
    trimesh.smoothing.filter_taubin(tm, lamb=0.5, nu=-0.53, iterations=it)
    return np.asarray(tm.vertices)


def signed_volume_L(V, F) -> float:
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6e6)


def volume_L(V, F) -> float:
    return abs(signed_volume_L(V, F))


def outward(V, F):
    """Faces wound so the normals point out of the closed mesh (Blender's cloth collision uses the face side)."""
    F = np.asarray(F, int)
    return F if signed_volume_L(np.asarray(V, float), F) > 0 else F[:, ::-1].copy()


# ---------------------------------------------------------------------------------------------- contents proxies
def face_y(sd: dict):
    """y of the pinned frame face B-01 as a function of (x, z): what the contents lie against."""
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
    v = np.unique(sd["tris"][np.char.startswith(sd["piece"].astype(str), "B-01")])
    P = sd["X"][v]
    lin, near = LinearNDInterpolator(P[:, [0, 2]], P[:, 1]), NearestNDInterpolator(P[:, [0, 2]], P[:, 1])

    def f(x, z):
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        y = lin(x, z)
        bad = np.isnan(y)
        if bad.any():
            y = np.where(bad, near(x, z), y)
        return y
    return f


def block_proxy(sd: dict, litres: float, w: float, z1: float, ex: float = 4.0, ez: float = 3.0, z0: float | None = None,
                gap: float = 4.0, nx: int = 44, nz: int = 64):
    """Packed-contents proxy: a rounded block lying on the frame face from the floor to ``z1``, ``w`` wide. Its depth
    profile is a superellipse in x and z; the peak depth is solved so the block's volume is ``litres``.
    Returns (V, F, info)."""
    fy = face_y(sd)
    floor = np.unique(sd["tris"][sd["piece"] == "B-05"])
    z0 = float(np.median(sd["X"][floor, 2])) + 6.0 if z0 is None else z0
    u = np.linspace(-1, 1, nx)
    v = np.linspace(-1, 1, nz)
    U, Vv = np.meshgrid(u, v, indexing="ij")
    x, z = U * w / 2, z0 + (Vv + 1) / 2 * (z1 - z0)
    prof = np.clip(1 - np.abs(U) ** ex, 0, 1) ** (1 / ex) * np.clip(1 - np.abs(Vv) ** ez, 0, 1) ** (1 / ez)
    yb = fy(x, z) + gap

    def build(depth):
        Pb = np.stack([x, yb, z], -1).reshape(-1, 3)
        Pa = np.stack([x, yb + depth * prof, z], -1).reshape(-1, 3)
        idx = np.arange(nx * nz).reshape(nx, nz)
        q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
        Fa = np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
        Fb = Fa[:, ::-1]
        rim = np.concatenate([idx[0, :], idx[-1, :], idx[:, 0], idx[:, -1]])
        Vv_ = np.vstack([Pb, Pa])
        Fa = Fa + nx * nz
        Vv_[nx * nz + rim] = Pb[rim]                              # sheets meet on the rim: closed
        Fo = np.vstack([Fb, Fa])
        return Vv_, outward(Vv_, Fo)
    lo, hi = 5.0, 400.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        Vp, Fp = build(mid)
        if volume_L(Vp, Fp) < litres:
            lo = mid
        else:
            hi = mid
    Vp, Fp = build(0.5 * (lo + hi))
    return Vp, Fp, {"litres": round(volume_L(Vp, Fp), 2), "depth_mm": round(0.5 * (lo + hi), 1), "w_mm": w,
                    "z0_mm": round(z0, 1), "z1_mm": z1}


def drape_proxy(sd: dict, inset: float, z_cap: float):
    """Full load: the contents are the huntkit drape itself, ``inset`` mm inside it, cut flat at ``z_cap`` (above
    that the collar is closure, not contents)."""
    V = _smooth(sd["X"], sd["tris"], 6)
    n = _vnormals(V, sd["tris"])
    P = V - inset * n
    P[:, 2] = np.minimum(P[:, 2], z_cap)
    return P, outward(P, sd["tris"]), {"litres": round(volume_L(P, sd["tris"]), 2), "inset_mm": inset,
                                           "z_cap_mm": round(z_cap, 1)}


# ------------------------------------------------------------------------------------------------- W1-W3 straps
def wraps(torso: int = 19) -> list:
    """W1-W3 frame anchors from the BL-009 scenario (attachments.wraps), FCS mm."""
    from huntkit.clothsim.pack import load_scenario
    sc = load_scenario(str(_ss().scenario(torso)))
    return [{"id": w["id"], "R": np.asarray(w["anchor_R"], float), "L": np.asarray(w["anchor_L"], float)}
            for w in sc["attachments"]["wraps"]["list"]]


def strap_z(w, x):
    """Height of the strap at lateral position x: it climbs evenly from the right anchor to the left one (a helix
    round the bag, not a plane: W1 runs from the z 80 lash point to the z 250 one)."""
    half = 205.0                                   # where the strap turns the bag's side (S15 half width + cloth)
    return np.interp(-np.asarray(x, float), [-half, half], [w["R"][2], w["L"][2]])


def band_pts(V, w, tol=14.0):
    """Vertices of a cloud that lie under the strap (within ``tol`` mm of its height at their x)."""
    V = np.asarray(V, float)
    return V[np.abs(V[:, 2] - strap_z(w, V[:, 0])) < tol]


def section_pts(V, F, origin, normal):
    import trimesh
    seg = trimesh.intersections.mesh_plane(trimesh.Trimesh(V, F, process=False), normal, origin)
    return np.zeros((0, 3)) if len(seg) == 0 else np.asarray(seg).reshape(-1, 3)


def taut_path(w, clouds, bite=0.0, step=6.0):
    """Taut strap line round ``clouds`` (vertex clouds; only what lies under the strap counts): convex hull in plan,
    taken from the right frame-side corner round the aft face to the left one, climbing evenly from the right
    anchor's height to the left one's. ``bite`` inflates the hull (the cloth pile under the strap).
    Returns points [n, 3] at ``step`` spacing, without the two frame anchors."""
    from scipy.spatial import ConvexHull
    P = np.vstack([band_pts(c, w) for c in clouds if len(c)])
    Q = P[:, :2]
    if bite > 0:
        a = np.linspace(0, 2 * np.pi, 9)[:-1]
        Q = (Q[:, None, :] + bite * np.column_stack([np.cos(a), np.sin(a)])[None]).reshape(-1, 2)
    y0 = float(max(w["R"][1], w["L"][1]))
    Q = Q[Q[:, 1] >= y0]
    H = Q[ConvexHull(Q).vertices]                                   # counter-clockwise in (x, y)
    low = H[:, 1] < y0 + 0.25 * (H[:, 1].max() - y0)
    i0 = np.where(low)[0][np.argmax(H[low, 0])]                     # right frame-side corner
    i1 = np.where(low)[0][np.argmin(H[low, 0])]                     # left one
    H2 = np.vstack([H, H])
    ch = H2[i0:(i1 if i1 > i0 else i1 + len(H)) + 1]                # ccw from the right corner = over the aft face
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ch, axis=0), axis=1))]
    k = max(int(s[-1] / step), 8)
    si = np.linspace(0, s[-1], k)
    xy = np.column_stack([np.interp(si, s, ch[:, 0]), np.interp(si, s, ch[:, 1])])
    lr = float(np.linalg.norm(xy[0] - w["R"][:2]))                  # anchor legs count in the even climb
    ll = float(np.linalg.norm(xy[-1] - w["L"][:2]))
    z = w["R"][2] + (w["L"][2] - w["R"][2]) * (lr + si) / (lr + s[-1] + ll)
    return np.column_stack([xy, z])


def resample(P, k):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    si = np.linspace(0, s[-1], k)
    return np.column_stack([np.interp(si, s, P[:, i]) for i in range(3)])


def strap_frames(P):
    """Along a strap line: unit tangent, outward direction (level, away from the bag) and the across-strap axis."""
    P = np.asarray(P, float)
    t = _unit(np.gradient(P, axis=0))
    o = np.column_stack([t[:, 1], -t[:, 0], np.zeros(len(P))])
    o = _unit(o)
    if np.mean(np.einsum("ij,ij->i", o[:, :2], P[:, :2] - P[:, :2].mean(0))) < 0:
        o = -o
    return t, o, _unit(np.cross(t, o))


def strap_slab(P, width=25.0, depth=45.0):
    """Collider for one strap: a slab whose inner face is the strap line ``P``, ``width`` across and ``depth`` thick
    outward. Returns V [4k, 3], F."""
    P = np.asarray(P, float)
    _, o, a = strap_frames(P)
    hw = 0.5 * width * a
    V = np.vstack([P + hw, P - hw, P + depth * o + hw, P + depth * o - hw])
    k = len(P)
    F = []
    for i0, i1 in ((0, 1), (1, 3), (3, 2), (2, 0)):
        for i in range(k - 1):
            q = [i0 * k + i, i0 * k + i + 1, i1 * k + i + 1, i1 * k + i]
            F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    for i in (0, k - 1):
        q = [i, k + i, 3 * k + i, 2 * k + i]
        F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    return V, outward(V, np.asarray(F, int))


# ------------------------------------------------------------------------------------------------------- the roll
def roll_turns(length: float, p: ClothParams) -> float:
    """Turns of the flat-folded roll that take ``length`` mm of collar. One turn at half-thickness r takes two flats
    (2 x fold) and one full circle (2 pi r); r grows by ``roll_pitch`` per turn from ``roll_core``."""
    a, b, c = np.pi * p.roll_pitch, 2 * p.roll_fold + 2 * np.pi * p.roll_core, -length
    return float((-b + np.sqrt(b * b - 4 * a * c)) / (2 * a))


def roll_section(length: float, p: ClothParams, per_turn: int = 28):
    """Cross-section of the roll as a polyline in (v, w): v along the flat (aft), w through the thickness (up).
    It starts at the lip (outer end, the collar arriving from below at the frame-side edge) and winds inward.
    Returns (Q [k, 2], turns, outer half-thickness)."""
    N = roll_turns(length, p)
    f = 0.5 * p.roll_fold
    r_out = p.roll_core + p.roll_pitch * N
    k = max(int(per_turn * N), 12)
    tau = np.linspace(0, N, k)                    # turns from the outside in
    r = r_out - p.roll_pitch * tau
    ph = (tau % 1.0) * 4.0                        # 0..1 bottom flat, 1..2 aft end, 2..3 top flat, 3..4 fore end
    Q = np.zeros((k, 2))
    for i, (h, ri) in enumerate(zip(ph, r)):
        if h < 1:
            Q[i] = (-f + 2 * f * h, -ri)
        elif h < 2:
            a = -np.pi / 2 + np.pi * (h - 1)
            Q[i] = (f + ri * np.cos(a), ri * np.sin(a))
        elif h < 3:
            Q[i] = (f - 2 * f * (h - 2), ri)
        else:
            a = np.pi / 2 + np.pi * (h - 3)
            Q[i] = (-f + ri * np.cos(a), ri * np.sin(a))
    return Q, N, r_out


def arch(s, z_mid: float, p: ClothParams):
    """The lip line as the roll carries it: level over ``roll_flat`` each side of the centre, then bent down through
    ``roll_bend_deg`` at ``roll_bend_r`` and straight on to the end. ``s`` = signed distance along the lip from the
    centre. Returns x, z, and the unit tangent (tx, tz)."""
    s = np.asarray(s, float)
    a = np.abs(s)
    th_max = np.radians(p.roll_bend_deg)
    arc = p.roll_bend_r * th_max
    th = np.clip((a - p.roll_flat) / p.roll_bend_r, 0.0, th_max)
    x = np.minimum(a, p.roll_flat) + p.roll_bend_r * np.sin(th)
    z = z_mid - p.roll_bend_r * (1 - np.cos(th))
    rest = np.maximum(a - p.roll_flat - arc, 0.0)
    x = x + rest * np.cos(th_max)
    z = z - rest * np.sin(th_max)
    sg = np.where(s < 0, -1.0, 1.0)
    return sg * x, z, np.cos(th), -sg * np.sin(th)


def roll_mesh(lip: dict, length: float, p: ClothParams, ds: float = 5.0):
    """The rolled collar: ``roll_section`` swept along the lip arch. ``lip`` = {half, y, z} (half width of the lip
    line, where its middle sits). Returns (trimesh with pattern UVs, info, centre line [m, 3], frames)."""
    from .assets import mesh as amesh
    Q, N, r_out = roll_section(length, p)
    m = max(int(2 * lip["half"] / ds), 8)
    s = np.linspace(-lip["half"], lip["half"], m)
    x, z, tx, tz = arch(s, lip["z"], p)
    T = np.column_stack([tx, np.zeros(m), tz])                      # along the roll
    Up = np.column_stack([-tz, np.zeros(m), tx])                    # out of the bag (through the roll's thickness)
    Aft = np.tile([0.0, 1.0, 0.0], (m, 1))
    L0 = np.column_stack([x, np.full(m, lip["y"]), z])              # the lip line (where the collar enters)
    f = 0.5 * p.roll_fold
    C = L0 + f * Aft + r_out * Up                                   # roll centre line
    k = len(Q)
    V = (C[:, None, :] + Q[None, :, 0:1] * Aft[:, None, :] + Q[None, :, 1:2] * Up[:, None, :]).reshape(-1, 3)
    idx = np.arange(m * k).reshape(m, k)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    F = np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    al = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    uv = np.stack(np.meshgrid(s, al, indexing="ij"), -1).reshape(-1, 2) / 500.0
    info = {"turns": round(N, 2), "collar_in_roll_mm": round(float(al[-1]), 1), "width_mm": round(2 * (f + r_out), 1),
            "thick_mm": round(2 * r_out, 1), "length_mm": round(2 * lip["half"], 1)}
    return amesh(V, F, uv), info, C, {"T": T, "Up": Up, "Aft": Aft, "L0": L0, "r_out": r_out, "f": f}


# =============================================================================================== stage 1: prepare
def prepare(state: str, params: ClothParams | None = None, shell: str = "S15", torso: int = 19, obstacles=(),
            work: Path | None = None, tag: str = "") -> dict:
    """Write the Blender job for one load state. ``obstacles`` = [(name, V, F)] things carried under W1-W3 (tripod,
    scope pod): the cloth collides with them and the straps close round them. Returns the job dict (with paths)."""
    p = params or ClothParams()
    SS = _ss()
    sd = seed(state, shell, torso, p.level)
    X, X0, T, piece = sd["X"], sd["X0"], sd["tris"], sd["piece"].astype(str)
    n = len(X)
    b01 = np.zeros(n, bool)
    b01[np.unique(T[np.char.startswith(piece, "B-01")])] = True
    ztop0 = X0[:, 2].max()
    lip = np.where(X0[:, 2] > ztop0 - 1e-3)[0]
    collar = np.zeros(n, bool)
    collar[np.unique(T[piece == "B-06"])] = True
    z_seam = float(X0[~collar | b01][:, 2].max())                   # collar seam height (drafted)
    dome_full = float(SS.BC.DOME_H)
    dome = float(ztop0 - z_seam)
    fy = face_y(sd)
    # ---- contents proxy and where the lip (roll start) ends up
    if state == "full":
        z_lip = float(X[lip, 2].mean()) - 8.0
        y_lip = float(np.median(X[lip, 1]))
        Vp, Fp, pinfo = drape_proxy(sd, p.proxy_inset, z_lip - 70.0)
    else:
        spec = SS.RENDER_STATES[state]
        pr = PROXY[state]
        Vp, Fp, pinfo = block_proxy(sd, spec["case"]["contents_L"], pr["w"], pr["z1"], pr["ex"], pr["ez"])
        if state == "day":            # contents end far below the collar: the roll lies on top of the frame face
            z_lip = z_seam + 22.0
            y_lip = float(fy(0.0, z_seam)) + 0.5 * p.strap_bite["day"] + 12.0
        else:
            z_lip = pr["z1"] + 14.0
            top = Vp[Vp[:, 2] > pr["z1"] - 60]
            y_lip = float(0.5 * (top[:, 1].min() + top[:, 1].max()))
    half = float(np.abs(X0[lip, 0]).max())
    lx, lz, _, _ = arch(X0[lip, 0], z_lip, p)
    tgt = X.copy()
    tgt[lip] = np.column_stack([lx, np.full(len(lip), y_lip), lz])
    # ---- straps: from the seed's girth to the taut line round the contents (+ anything carried)
    straps = []
    pin_cloud_all = X[b01]
    for w in wraps(torso):
        obs = [np.asarray(V, float) for _, V, F in obstacles]
        P0 = taut_path(w, [X, pin_cloud_all] + obs, bite=1.0)
        P1 = taut_path(w, [Vp, pin_cloud_all] + obs, bite=p.strap_bite[state])
        k = max(len(P0), len(P1))
        P0, P1 = resample(P0, k), resample(P1, k)
        V0, Fs = strap_slab(P0, p.strap_w)
        V1, _ = strap_slab(P1, p.strap_w)
        straps.append({"id": w["id"], "P0": P0, "P1": P1, "V0": V0, "V1": V1, "F": Fs, "R": w["R"], "L": w["L"]})
    work = Path(work or WORK / f"{shell}_PR{torso}")
    work.mkdir(parents=True, exist_ok=True)
    stem = f"{state}{tag}_L{p.level}"
    npz = work / f"{stem}.in.npz"
    arrays = {"X": X, "X0": X0, "T": T, "tgt": tgt, "pin": (b01 | np.isin(np.arange(n), lip)).astype(np.float32),
              "proxy_V": Vp, "proxy_F": Fp}
    for i, s in enumerate(straps):
        arrays[f"strap{i}_V0"], arrays[f"strap{i}_V1"], arrays[f"strap{i}_F"] = s["V0"], s["V1"], s["F"]
    for i, (_, V, F) in enumerate(obstacles):
        arrays[f"obs{i}_V"], arrays[f"obs{i}_F"] = np.asarray(V, float), np.asarray(F, int)
    np.savez_compressed(npz, **arrays)
    A = np.linalg.norm(np.cross(X0[T[:, 1]] - X0[T[:, 0]], X0[T[:, 2]] - X0[T[:, 0]]), axis=1).sum() / 2e6
    job = {"kind": "bag", "state": state, "in": str(npz), "out": str(work / f"{stem}.out.npy"),
           "preview": str(work / f"{stem}.preview.png"), "params": asdict(p), "n_straps": len(straps),
           "n_obs": len(obstacles), "area_m2": float(A), "stem": stem}
    meta = {"state": state, "shell": shell, "torso": torso, "level": p.level, "n": int(n), "proxy": pinfo,
            "lip": {"half": half, "y": y_lip, "z": z_lip}, "z_seam": z_seam, "dome_mm": dome,
            "collar_in_roll_mm": p.roll_closure + max(dome_full - dome, 0.0), "area_m2": float(A),
            "straps": [{k: (np.asarray(v).tolist() if not isinstance(v, str) else v) for k, v in s.items()
                        if k in ("id", "P0", "P1", "R", "L")} for s in straps]}
    (work / f"{stem}.job.json").write_text(json.dumps(job, indent=1))
    (work / f"{stem}.meta.json").write_text(json.dumps(meta))
    return {"job": job, "meta": meta, "seed": sd, "job_path": work / f"{stem}.job.json"}


def find_bpy_python(bpy_python=None):
    from . import studio
    return studio.find_bpy_python(bpy_python)


def solve(job_path: Path, bpy_python=None, threads: int = 2) -> None:
    """Run stage 2 for one job (in-process when bpy imports here, else through the Blender venv's Python)."""
    try:
        import bpy  # noqa: F401
        _blender_job(json.loads(Path(job_path).read_text()))
        return
    except ImportError:
        pass
    py = find_bpy_python(bpy_python)
    if py is None:
        raise RuntimeError("bpy is not importable: set HUNTKIT_BPY to the Blender venv's Python (viz3d/README.md)")
    env = dict(os.environ, OMP_NUM_THREADS=str(threads))
    subprocess.run([py, "-m", "huntkit.viz3d.cloth_pass", "--job", str(job_path)], cwd=REPO, check=True, env=env)


# ============================================================================================ stage 2: Blender
def _bl_mesh(name, V, F, scale=0.001):
    import bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata((np.asarray(V) * scale).tolist(), [], np.asarray(F).tolist())
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _bl_key(ob, name, V, scale=0.001):
    if ob.data.shape_keys is None:
        ob.shape_key_add(name="Basis")
    k = ob.shape_key_add(name=name)
    k.data.foreach_set("co", (np.asarray(V, float) * scale).ravel())
    return k


def _bl_collider(ob, p):
    ob.modifiers.new("Collision", "COLLISION")
    c = ob.collision
    c.thickness_outer = p["coll_dist"] * 0.001
    c.thickness_inner = 0.004
    c.cloth_friction = p["friction"]
    c.damping = 0.6


def _blender_job(job: dict) -> dict:
    import bpy
    t0 = time.time()
    p = job["params"]
    D = np.load(job["in"])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    n_c, n_s = int(job.get("frames_cinch", p["frames_cinch"])), int(job.get("frames_settle", p["frames_settle"]))
    f_end = 1 + n_c + n_s
    sc.frame_start, sc.frame_end = 1, f_end
    X, T = D["X"], D["T"]
    ob = _bl_mesh("cloth", X, T)
    ob.shape_key_add(name="Basis")
    rest = _bl_key(ob, "rest", D["X0"])
    rest.value = 0.0
    if "tgt" in D:
        tg = _bl_key(ob, "target", D["tgt"])
        tg.value = 0.0
        tg.keyframe_insert("value", frame=1)
        tg.value = 1.0
        tg.keyframe_insert("value", frame=1 + n_c)
    vg = ob.vertex_groups.new(name="pin")
    pin = D["pin"]
    for w in np.unique(pin[pin > 0]):
        vg.add(np.where(pin == w)[0].tolist(), float(w), "REPLACE")
    # colliders
    for key in [k[:-2] for k in D.files if k.endswith("_V") and not k.startswith("strap")]:
        _bl_collider(_bl_mesh(key, D[key + "_V"], D[key + "_F"]), p)
    for i in range(int(job.get("n_straps", 0))):
        so = _bl_mesh(f"strap{i}", D[f"strap{i}_V0"], D[f"strap{i}_F"])
        so.shape_key_add(name="Basis")
        k = _bl_key(so, "closed", D[f"strap{i}_V1"])
        k.value = 0.0
        k.keyframe_insert("value", frame=1)
        k.value = 1.0
        k.keyframe_insert("value", frame=1 + n_c)
        _bl_collider(so, p)
    for a in list(bpy.data.actions):                                 # ease in and out
        try:
            fcs = a.fcurves
        except AttributeError:
            fcs = [fc for layer in a.layers for st in layer.strips for cb in st.channelbags for fc in cb.fcurves]
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
    md = ob.modifiers.new("Cloth", "CLOTH")
    cs = md.settings
    cs.quality = int(p["quality"])
    cs.mass = float(job["area_m2"]) * p["areal_mass"] / len(X)
    cs.tension_stiffness = cs.compression_stiffness = p["tension"]
    cs.compression_stiffness = p["compression"]
    cs.shear_stiffness = p["shear"]
    cs.bending_stiffness = p["bending"]
    cs.tension_damping = cs.compression_damping = cs.shear_damping = p["damping"]
    cs.bending_damping = 0.5
    cs.air_damping = p["air_damping"]
    cs.vertex_group_mass = "pin"
    cs.pin_stiffness = 1.0
    cs.rest_shape_key = rest
    if job.get("pressure"):
        cs.use_pressure = True
        cs.uniform_pressure_force = float(job["pressure"])
    cc = md.collision_settings
    cc.use_collision = True
    cc.collision_quality = 3
    cc.distance_min = p["coll_dist"] * 0.001
    cc.use_self_collision = True
    cc.self_distance_min = min(p["self_dist"], job.get("self_dist_max", 99.0)) * 0.001
    cc.self_friction = 8.0
    cc.friction = p["friction"]
    md.point_cache.frame_start, md.point_cache.frame_end = 1, f_end
    V = None
    for f in range(1, f_end + 1):
        sc.frame_set(f)
        if f % 10 == 0 or f == f_end:
            dg = bpy.context.evaluated_depsgraph_get()
            me = ob.evaluated_get(dg).to_mesh()
            V = np.zeros(len(me.vertices) * 3)
            me.vertices.foreach_get("co", V)
            V = V.reshape(-1, 3) * 1000.0
            print(f"  cloth_pass {job.get('stem', '')}: frame {f}/{f_end}, moved max "
                  f"{np.linalg.norm(V - X, axis=1).max():.0f} mm, {time.time() - t0:.0f} s", flush=True)
    assert V is not None and len(V) == len(X) and np.isfinite(V).all(), "cloth solve failed"
    np.save(job["out"], V)
    res = {"seconds": round(time.time() - t0, 1), "frames": f_end, "verts": int(len(X))}
    Path(job["out"]).with_suffix(".result.json").write_text(json.dumps(res))
    if job.get("preview"):
        try:
            _clay_preview(ob, job["preview"])
        except Exception as e:                                      # a preview never fails the solve
            print("  preview failed:", e)
    return res


def _clay_preview(ob, png, res=(560, 700), samples=10):
    """Two quick clay views of the solved cloth (and its colliders hidden), side by side: a shape check."""
    import bpy
    from mathutils import Vector
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    for o in list(sc.collection.objects):
        o.hide_render = True
    co = bpy.data.objects.new("clay", me)
    sc.collection.objects.link(co)
    for poly in me.polygons:
        poly.use_smooth = True
    mat = bpy.data.materials.new("clay")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.55, 0.56, 0.5, 1)
    b.inputs["Roughness"].default_value = 0.7
    me.materials.append(mat)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.data.angle = 0.3
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 70
    sc.collection.objects.link(cam)
    sc.camera = cam
    bb = np.array([co.matrix_world @ Vector(c) for c in co.bound_box])
    c = Vector(bb.mean(0).tolist())
    r = float(np.linalg.norm(bb.max(0) - bb.min(0)))
    outs = []
    for i, (az, el) in enumerate(((-38, 12), (75, 8))):
        a, e = np.radians(az), np.radians(el)
        d = Vector((np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e) * -1.0, np.sin(e)))   # az 0 = looking at the aft face
        cam.location = c + d * r * 2.3
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        sun.rotation_euler = (cam.location - c + Vector((0.4, 0.2, 0.9)) * r).to_track_quat("Z", "Y").to_euler()
        sc.render.filepath = str(Path(png).with_suffix(f".{i}.png"))
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    from PIL import Image
    ims = [Image.open(o) for o in outs]
    sheet = Image.new("RGB", (sum(i.width for i in ims), ims[0].height), "white")
    x = 0
    for im in ims:
        sheet.paste(im.convert("RGB"), (x, 0))
        x += im.width
    sheet.save(png)
    for o in outs:
        Path(o).unlink()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="BL-020 render-only cloth pass (stage 2 runs in Blender's Python)")
    ap.add_argument("--job", help="stage 2: solve one prepared job (json)")
    ap.add_argument("--state", choices=STATES, help="stage 1 + 2: solve one load state of shell S15 and cache it")
    ap.add_argument("--level", type=int, default=2)
    a = ap.parse_args(argv)
    if a.job:
        print(json.dumps(_blender_job(json.loads(Path(a.job).read_text()))))
    elif a.state:
        r = prepare(a.state, ClothParams(level=a.level))
        solve(r["job_path"])
        print(r["job"]["out"])


if __name__ == "__main__":
    main()
