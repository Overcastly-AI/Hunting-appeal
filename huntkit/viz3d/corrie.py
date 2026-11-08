"""CORRIE bag for the 3D model (huntkit.viz3d), built from the CLOTH-SIM drape of its flat pieces.

The bag skin is the simulated fill shape (``huntkit.clothsim``, scenario ``corrie_PR19``, fine mesh): CORRIE's
actual flat pieces sewn together, hung on the frame by the hinge eyes, hooks, crown hood and guys, and filled
(68 kg granular fill, Janssen). Every detail part is placed on that deformed surface. Same materials, camo texture,
lighting, frame, harness and mannequin as the SPINE renders (``huntkit.viz3d.model``).

    from huntkit.viz3d.corrie import corrie_pack
    pack = corrie_pack(params)          # PackModel with SPINE's bag swapped for CORRIE

Variants used by the viewer toggles: ``rolled`` = door closed (hidden when "full" is on), ``full`` = door open +
lining + IM straps inside, ``lid`` = tripod under the right wing, ``nolid`` = the plain right wing.
Design record: designs/pack_5200/analysis/corrie_body.md.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from . import geom as G
from .model import BAGM, Part
from .params import REPO

PACK = REPO / "designs" / "pack_5200"
SCEN = REPO / "huntkit" / "clothsim" / "scenarios" / "corrie_PR19.yaml"
SIM_DIR = REPO / "outputs" / "clothsim" / "corrie_PR19_fine"
CACHE = REPO / "outputs" / "clothsim" / "cache"
BE = (0.0, 260.0, 0.0)
SPINE_BAG_PARTS = ("bag_body", "bag_body_full", "bag_bottom", "bag_trim", "diagonal_band", "bag_shards", "zip_pulls",
                   "bag_boot_tabs", "side_pockets", "rolltop", "rolltop_straps", "rolltop_full", "rolltop_full_straps",
                   "lid", "lid_shard", "lid_trim", "compression_straps", "guy_tabs_b22", "guy_tabs_b22_full",
                   "bow_carry", "bow_carry_hook")
SPINE_PREFIX_DROP = ("top_guys", "haul_wraps_meat", "crown_wrap_meat")


def _concept():
    sys.path.insert(0, str(PACK / "concepts"))
    sys.path.insert(0, str(PACK))
    import bag_concepts as BC  # noqa: E402
    import corrie as CO  # noqa: E402
    return BC, CO


# ============================================================================ simulated skin
def sim_skin(sim_dir=SIM_DIR, case="fill", fine=True) -> dict:
    """Deformed CORRIE mesh: nodes X (FCS mm), start nodes X0, triangles, piece name per triangle, per-node UV (mm on
    the flat pattern of one of its pieces). Cached next to the sim output."""
    xf = Path(sim_dir) / f"x_{case}.npy"
    key = CACHE / f"corrie_skin_{Path(sim_dir).name}_{case}_{int(xf.stat().st_mtime)}.pkl"
    if key.exists():
        return pickle.loads(key.read_bytes())
    from huntkit.clothsim.pack import PackModel, load_scenario
    pm = PackModel(load_scenario(str(SCEN)), fine=fine, verbose=False)
    m = pm.mesh
    x = np.load(xf)
    uv = np.zeros((m.n, 2))
    for p in m.pieces:
        uv[p.gid] = p.xy
    out = {"X": x, "X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    CACHE.mkdir(parents=True, exist_ok=True)
    key.write_bytes(pickle.dumps(out))
    return out


class Deform:
    """Maps any point of the undeformed (drafted) bag surface onto the simulated shape: displacement of the nearest
    start nodes, inverse-distance weighted, plus the local outward normal of the deformed skin."""

    def __init__(self, sk):
        self.sk = sk
        self.tree = cKDTree(sk["X0"])
        X, T = sk["X"], sk["tris"]
        fn = np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]])
        vn = np.zeros_like(X)
        for j in range(3):
            np.add.at(vn, T[:, j], fn)
        self.vn = vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)

    def __call__(self, P, offset=0.0, k=6):
        P = np.atleast_2d(np.asarray(P, float))
        d, j = self.tree.query(P, k=k)
        w = 1.0 / np.maximum(d, 1e-3) ** 2
        w /= w.sum(1, keepdims=True)
        disp = np.einsum("ij,ijk->ik", w, self.sk["X"][j] - self.sk["X0"][j])
        n = np.einsum("ij,ijk->ik", w, self.vn[j])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        return P + disp + offset * n, n


def _smooth(V, F, it=6):
    tm = trimesh.Trimesh(V.copy(), F.copy(), process=False)
    trimesh.smoothing.filter_taubin(tm, lamb=0.5, nu=-0.53, iterations=it)
    return np.asarray(tm.vertices)


def _subdivide(V, F, UV, n=1):
    for _ in range(n):
        V, F, att = trimesh.remesh.subdivide(V, F, vertex_attributes={"uv": UV})
        UV = att["uv"]
    return V, F, UV


# ============================================================================ helpers
def ribbon_on(D, pts0, width, thick=1.4, lift=2.0, step=6.0):
    """A strap lying on the bag: undeformed path -> deformed path + lift along the skin normal."""
    P, n = D(G.resample(np.asarray(pts0, float), step) if len(pts0) > 2 else np.asarray(pts0, float), lift)
    return G.ribbon(P, width, thick, n, step=step)


def plate_on(D, centre0, ex, ey, w, h, thick=1.2, lift=0.8, nu=8, nv=8):
    """A flat patch (tab, garage) on the bag at undeformed centre, axes ex (width) / ey (height)."""
    c0, ex, ey = (np.asarray(v, float) for v in (centre0, ex, ey))
    us = np.linspace(-w / 2, w / 2, nu + 1)
    vs = np.linspace(-h / 2, h / 2, nv + 1)
    U, Vv = np.meshgrid(us, vs, indexing="ij")
    P0 = c0 + U.reshape(-1, 1) * ex + Vv.reshape(-1, 1) * ey
    P, n = D(P0, lift)
    P = P.reshape(nu + 1, nv + 1, 3)
    n = n.reshape(nu + 1, nv + 1, 3)
    top = P + n * thick
    return _slab(P, top, U.reshape(nu + 1, nv + 1) / G.TILE_MM, Vv.reshape(nu + 1, nv + 1) / G.TILE_MM)


def _slab(Bot, Top, Uu, Vv):
    """Closed slab between two (nu+1, nv+1) grids."""
    nu, nv = Bot.shape[0] - 1, Bot.shape[1] - 1
    V = np.vstack([Top.reshape(-1, 3), Bot.reshape(-1, 3)])
    uv = np.vstack([np.column_stack([Uu.ravel(), Vv.ravel()])] * 2)
    off = (nu + 1) * (nv + 1)
    idx = lambda i, j: i * (nv + 1) + j  # noqa: E731
    F = []
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            F += [[a, b, c], [a, c, d], [off + a, off + c, off + b], [off + a, off + d, off + c]]
    ring = [idx(i, 0) for i in range(nu)] + [idx(nu, j) for j in range(nv)] + \
           [idx(i, nv) for i in range(nu, 0, -1)] + [idx(0, j) for j in range(nv, 0, -1)]
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        F += [[a, off + a, off + b], [a, off + b, b]]
    return G._mesh(V, np.array(F), uv)


def _block(c, size, e=0.3):
    return G.superellipsoid(c, np.asarray(size) / 2, e_ns=e, e_ew=e)


def g_hook(c, up=(0, 0, 1)):
    """25 mm aluminium G-hook (HAUL family) as a flat hook blade."""
    return _block(c, (8, 4, 30), e=0.5)


# ============================================================================ the CORRIE parts
def corrie_parts(p: dict, g: dict) -> tuple[list, dict]:
    BC, CO = _concept()
    c = CO.make()
    sk = sim_skin()
    D = Deform(sk)
    X, T, piece, UVn = sk["X"], sk["tris"], sk["piece"], sk["uv"]
    parts, metrics = [], {}
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([z])[0])                             # noqa: E731
    yb_of = lambda z: float(c.y_front([min(z, c.z_c)])[0])                  # noqa: E731
    H = CO.DOOR

    # ---- skin: smooth, split door / floor / rest, subdivide for silhouettes
    Xs = _smooth(X, T, 8)
    X0 = sk["X0"]
    cen0 = X0[T].mean(1)

    def in_door(p0):
        x, y, z = p0
        if not (H["z_lo"] - 2 < z < H["z_hinge"] + 2) or abs(y - yb_of(z)) > 8:
            return False
        a = a_of(z) - H["inset"]
        if abs(x) > a + 2:
            return False
        if z < H["z_lo"] + H["r"] and abs(x) > a - H["r"]:
            return (abs(x) - (a - H["r"])) ** 2 + (H["z_lo"] + H["r"] - z) ** 2 < (H["r"] + 2) ** 2
        return True
    door_t = np.array([pc == "B-02door" for pc in piece])
    floor_t = np.array([pc == "B-05" for pc in piece])
    rest_t = ~(door_t | floor_t)

    def skin_mesh(mask, sub=1):
        F = T[mask]
        used = np.unique(F)
        remap = -np.ones(len(Xs), int)
        remap[used] = np.arange(len(used))
        V, Fm, UV = _subdivide(Xs[used], remap[F], UVn[used] / G.TILE_MM, sub)
        return G._mesh(V, Fm, UV, flip_if_negative=False)
    body = skin_mesh(rest_t)
    door = skin_mesh(door_t)
    floor = skin_mesh(floor_t)
    parts.append(Part("corrie_body", body, "body", "bag", modes=BAGM, explode=BE, floats=True,
                      label="CORRIE main bag (cloth-sim drape of the flat pieces, 68 kg fill, 19 in)"))
    parts.append(Part("corrie_door", door, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                      label="Horseshoe door (closed)"))
    parts.append(Part("corrie_bottom", floor, "tpu", "bag", modes=BAGM, explode=(0, 260, -40), floats=True,
                      label="Bottom B-05 (500D)"))
    # door open: rotate the door about the hinge line (aft face, z 650) by 105 deg, upward
    zh = H["z_hinge"]
    hinge_pts = np.array([[x, yb_of(zh), zh] for x in (-100.0, 100.0)])
    hp, _ = D(hinge_pts)
    yh, zz = float(hp[:, 1].mean()), float(hp[:, 2].mean())
    th = np.radians(105)
    V = door.vertices - np.array([0, yh, zz])
    Vr = np.column_stack([V[:, 0], V[:, 1] * np.cos(th) - V[:, 2] * np.sin(th),
                          V[:, 1] * np.sin(th) + V[:, 2] * np.cos(th)]) + np.array([0, yh, zz])
    door_open = G._mesh(Vr, door.faces, door.metadata["uv"], flip_if_negative=False)
    parts.append(Part("corrie_door_open", door_open, "body", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="full", label="Horseshoe door open (hinged at z 650)"))
    lin = G._mesh(body.vertices - 1.5 * _vnormals(body), body.faces[:, ::-1], body.metadata["uv"], flip_if_negative=False)
    parts.append(Part("corrie_lining", lin, "harness", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Inside of the bag (seen through the open door)"))
    lin2 = G._mesh(door_open.vertices - 1.0 * _vnormals(door_open), door_open.faces[:, ::-1], door_open.metadata["uv"],
                   flip_if_negative=False)
    parts.append(Part("corrie_door_lining", lin2, "harness", "bag", modes=BAGM, explode=BE, floats=True, variant="full"))

    # ---- seam piping along every piece boundary (the binding the eye reads as seams)
    tubes = []
    for chain in _seam_chains(T, piece, Xs):
        if len(chain) > 2:
            P = Xs[chain]
            P = P + 1.2 * _node_normals(Xs, T)[chain]
            tubes.append(G.tube(G.catmull_rom(P, 3), 2.3, n=8))
    parts.append(Part("corrie_seams", G.concat(tubes), "trim", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Bound seams"))

    # ---- door zip: track + coil + 2 sliders + cord pulls + 2 camo garages
    du = _door_path(c, BC, CO)
    P, n = D(du, 1.6)
    zip_track = G.ribbon(P, 11.0, 1.2, n, step=4.0)
    coil = G.tube(P + n * 1.3, 1.9, n=6)
    parts.append(Part("corrie_door_zip", G.concat([zip_track, coil]), "hardware", "bag", modes=BAGM, explode=BE,
                      floats=True, variant="rolled", label="#10 coil door zip"))
    sl, pulls, gar = [], [], []
    for sx in (1, -1):
        z = zh - 30
        p0 = np.array([[sx * (a_of(z) - H["inset"]), yb_of(z), z]])
        q, nn = D(p0, 4.0)
        sl.append(_block(q[0], (15, 7, 26), e=0.4))
        loop = q[0] + nn[0] * 6 + np.array([[0, 0, 0], [sx * 4, 0, -18], [0, 0, -34], [-sx * 4, 0, -18]])
        pulls.append(G.tube(G.catmull_rom(loop, 6, closed=True), 1.6, n=6))
        gar.append(plate_on(D, [sx * (a_of(zh) - H["inset"]), yb_of(zh), zh - 22], [1, 0, 0], [0, 0, 1], 42, 62,
                            thick=1.0, lift=2.6))
    parts.append(Part("corrie_zip_sliders", G.concat(sl), "hardware", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Door zip sliders (2)"))
    parts.append(Part("corrie_zip_pulls", G.concat(pulls), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      label="3 mm cord pulls in rubber sleeves"))
    parts.append(Part("corrie_zip_garages", G.concat(gar), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Zip garages SH-07 (camo)"))

    # ---- camo: chevron kick plate (aft + sides), B-22 tabs, wing bars below
    kick = []
    a0 = a_of(60)
    for sgn, label in ((0, "aft"), (1, "R"), (-1, "L")):
        if sgn == 0:
            pts = [[x, yb_of(z0) + 0.0, z0] for x in np.linspace(-a0 + 4, a0 - 4, 24) for z0 in [0]]
            kick.append(_kick_aft(D, c, BC, yb_of, a_of))
        else:
            kick.append(_kick_side(D, c, BC, sgn, yf_of, yb_of, a_of))
    parts.append(Part("corrie_kick", G.concat(kick), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Chevron kick plate SH-01 (camo, wear line)"))
    tabs = [plate_on(D, [sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z], [1, 0, 0], [0, 0, 1], 50, 60, thick=1.2, lift=1.0)
            for sx in (1, -1)]
    parts.append(Part("corrie_b22", G.concat(tabs), "hypalon", "bag", modes=BAGM, explode=BE, floats=True,
                      label="B-22 guy tabs at z 695 on the hinge band"))

    # ---- roll-top: closed roll at the collar's top line, camo, with the two ROLL buckles to the gussets
    roll, rstraps, rbuck, top_line = _rolltop(Xs, T, piece, c)
    parts.append(Part("corrie_roll", roll, "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Roll-top closed (3 rolls), camo hem band"))
    parts.append(Part("corrie_roll_straps", G.concat(rstraps), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Roll clips (ROLL family) down to the side gussets"))
    parts.append(Part("corrie_roll_buckles", G.concat(rbuck), "hardware", "bag", modes=BAGM, explode=BE, floats=True))

    # ---- top pouch on the roll
    pouch, pcamo, pzip, pstr, phw = _pouch(top_line, CO, Xs, T, piece)
    parts.append(Part("corrie_pouch", pouch, "body", "bag", modes=BAGM, explode=(0, 200, 160), floats=True,
                      label="Top pouch 4.0 L (removable)"))
    parts.append(Part("corrie_pouch_top", pcamo, "camo", "bag", modes=BAGM, explode=(0, 200, 160), floats=True))
    parts.append(Part("corrie_pouch_zip", pzip, "hardware", "bag", modes=BAGM, explode=(0, 200, 160), floats=True))
    parts.append(Part("corrie_pouch_straps", G.concat(pstr), "webbing", "bag", modes=BAGM, explode=(0, 200, 160),
                      floats=True, label="Pouch straps: 2 rear to the frame-side hem, 2 front to the roll clips"))
    parts.append(Part("corrie_pouch_hooks", G.concat(phw), "aluminium", "bag", modes=BAGM, explode=(0, 200, 160),
                      floats=True))

    # ---- wings (fabric thickness, camo leading-edge bar, 2 G-hook straps each) + tripod variant
    for sx, side in ((1, "R"), (-1, "L")):
        for trip in ((False, True) if sx == 1 else (False,)):
            w, bar, st, hw = _wing(D, c, BC, sx, yf_of, yb_of, a_of, tripod=trip)
            var = ("lid" if trip else "nolid") if sx == 1 else None
            tag = f"{side}{'_tripod' if trip else ''}"
            parts.append(Part(f"corrie_wing_{tag}", w, "tpu", "bag", modes=BAGM, explode=(sx * 120, 200, 0), floats=True,
                              variant=var, label="Side compression wing 200 x 450 (330D, hemmed)"))
            parts.append(Part(f"corrie_wing_bar_{tag}", bar, "camo", "bag", modes=BAGM, explode=(sx * 120, 200, 0),
                              floats=True, variant=var, label="Wing leading-edge bar SH-06 (camo)"))
            parts.append(Part(f"corrie_wing_straps_{tag}", G.concat(st), "webbing", "bag", modes=BAGM,
                              explode=(sx * 120, 200, 0), floats=True, variant=var))
            parts.append(Part(f"corrie_wing_hw_{tag}", G.concat(hw), "aluminium", "bag", modes=BAGM,
                              explode=(sx * 120, 200, 0), floats=True, variant=var,
                              label="G-hooks + ladder locks (HAUL family)"))
    tri = _tripod(c, BC, yf_of, a_of)
    parts.append(Part("corrie_tripod", tri, "hardware", "bag", modes=BAGM, floats=True, variant="lid",
                      label="Tripod under the right wing"))

    # ---- inside, seen through the open door: IM1-IM3 (bone webbing) across the frame face, hooks
    ims, imh = [], []
    for zs in (190.0, 330.0, 520.0):
        pts0 = [[x, yf_of(zs) + 2, zs] for x in np.linspace(-118, 118, 20)]
        P, nn = D(pts0, -14.0)
        ims.append(G.ribbon(P, 38.0, 1.8, -nn, step=6.0))
        for sx in (1, -1):
            imh.append(_block(P[0 if sx < 0 else -1], (12, 8, 30), e=0.5))
    parts.append(Part("corrie_im_straps", G.concat(ims), "meat_strap", "bag", modes=BAGM, floats=True, variant="full",
                      label="IM1-IM3 internal meat straps (38 mm), reachable through the door"))
    parts.append(Part("corrie_im_hooks", G.concat(imh), "aluminium", "bag", modes=BAGM, floats=True, variant="full"))

    # ---- top guys (19 in): hood ears -> B-22
    gu = []
    for sx in (1, -1):
        A = np.array([sx * 95.0, 21.7, 702.6 + 6])
        Bp, nB = D([[sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z]], 3.0)
        mid = 0.5 * (A + Bp[0]) + np.array([sx * 18, 0, 6])
        path = G.catmull_rom(np.array([A, mid, Bp[0]]), 8)
        gu.append(G.ribbon(path, 25.0, 1.4, np.tile([0, 0, 1.0], (len(path), 1)), step=8.0))
    parts.append(Part("corrie_top_guys@t19", G.concat(gu), "webbing", "attach", torso=19.0, modes=("pack",),
                      label="Top guys: crown hood ears -> B-22 (fixed length)"))

    metrics.update(corrie_sim_volume_L=float(abs(G._signed_volume(trimesh.Trimesh(X, T, process=False))) / 1e6))
    return parts, metrics


def _vnormals(m):
    return np.asarray(trimesh.Trimesh(m.vertices, m.faces, process=False).vertex_normals)


def _node_normals(X, T):
    return np.asarray(trimesh.Trimesh(X, T, process=False).vertex_normals)


def _seam_chains(T, piece, X):
    """Edges shared by triangles of two different pieces, chained into polylines."""
    from collections import defaultdict
    ef = defaultdict(set)
    for t, (a, b, cc) in enumerate(T):
        for u, v in ((a, b), (b, cc), (cc, a)):
            ef[(min(u, v), max(u, v))].add(piece[t])
    E = [e for e, ps in ef.items() if len(ps) > 1]
    adj = defaultdict(list)
    for u, v in E:
        adj[u].append(v)
        adj[v].append(u)
    seen, chains = set(), []
    for u, v in E:
        if (u, v) in seen:
            continue
        chain = [u, v]
        seen.add((u, v))
        for end in (0, 1):
            while True:
                tip = chain[-1] if end == 0 else chain[0]
                prev = chain[-2] if end == 0 else chain[1]
                nxt = [w for w in adj[tip] if w != prev and (min(tip, w), max(tip, w)) not in seen]
                if len(adj[tip]) != 2 or not nxt:
                    break
                w = nxt[0]
                seen.add((min(tip, w), max(tip, w)))
                if end == 0:
                    chain.append(w)
                else:
                    chain.insert(0, w)
        chains.append(chain)
    return chains


def _door_path(c, BC, CO):
    H = CO.DOOR
    pts = []
    zz = np.linspace(H["z_hinge"] - 5, H["z_lo"] + H["r"], 40)
    yb = lambda z: float(c.y_front([z])[0])            # noqa: E731
    a_of = lambda z: float(c.a([z])[0])                # noqa: E731
    for z in zz:
        pts.append([-(a_of(z) - H["inset"]), yb(z), z])
    a_c = a_of(H["z_lo"] + H["r"]) - H["inset"]
    for t in np.linspace(0, np.pi / 2, 10):
        z = H["z_lo"] + H["r"] - H["r"] * np.sin(t)
        pts.append([-(a_c - H["r"] + H["r"] * np.cos(t)), yb(z), z])
    for t in np.linspace(np.pi / 2, 0, 10):
        z = H["z_lo"] + H["r"] - H["r"] * np.sin(t)
        pts.append([a_c - H["r"] + H["r"] * np.cos(t), yb(z), z])
    for z in zz[::-1]:
        pts.append([a_of(z) - H["inset"], yb(z), z])
    return G.resample(np.array(pts), 4.0)


def _kick_aft(D, c, BC, yb_of, a_of):
    """Chevron kick plate on the aft face: 70 mm at the corners, 140 mm at the centre, from the floor seam up."""
    nu, nv = 30, 8
    a0 = a_of(BC.Z0)
    U, Vv = np.meshgrid(np.linspace(-1, 1, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    hgt = 70 + 70 * (1 - np.abs(U))
    Z = BC.Z0 + 3 + Vv * hgt
    Xx = U * (np.array([[a_of(z) for z in row] for row in Z]) - 3)
    Y = np.array([[yb_of(z) for z in row] for row in Z])
    P0 = np.stack([Xx, Y, Z], -1).reshape(-1, 3)
    P, n = D(P0, 1.0)
    P, n = P.reshape(nu + 1, nv + 1, 3), n.reshape(nu + 1, nv + 1, 3)
    return _slab(P, P + n * 1.0, Xx / 380.0 * G.TILE_MM / G.TILE_MM, Z / 380.0)


def _kick_side(D, c, BC, sx, yf_of, yb_of, a_of):
    nu, nv = 10, 6
    U, Vv = np.meshgrid(np.linspace(0.04, 0.98, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    Z = BC.Z0 + 3 + Vv * 70
    Y = np.array([[yf_of(z) + u * (yb_of(z) - yf_of(z)) for u, z in zip(ur, zr)] for ur, zr in zip(U, Z)])
    Xx = sx * np.array([[a_of(z) for z in row] for row in Z])
    P0 = np.stack([Xx, Y, Z], -1).reshape(-1, 3)
    P, n = D(P0, 1.0)
    P, n = P.reshape(nu + 1, nv + 1, 3), n.reshape(nu + 1, nv + 1, 3)
    return _slab(P, P + n * 1.0, Y / 380.0, Z / 380.0)


def _rolltop(X, T, piece, c):
    """The sim closes the collar flat at the fill line; the roll (3 turns, ~56 mm) sits on that closure line."""
    col = np.unique(T[np.array([p == "B-06" for p in piece])])
    zt = X[col, 2].max()
    top = col[X[col, 2] > zt - 25]
    P = X[top]
    xs = np.linspace(P[:, 0].min() + 10, P[:, 0].max() - 10, 30)
    y = np.interp(xs, *zip(*sorted(zip(P[:, 0], P[:, 1]))))
    z = np.interp(xs, *zip(*sorted(zip(P[:, 0], P[:, 2]))))
    line = np.column_stack([xs, y, z + 14])
    line = G.catmull_rom(line[::3], 4)
    r = 27.0
    roll = G.tube(line, r, n=28, caps=True)
    roll.metadata["uv"] = roll.metadata["uv"] * 0.8
    straps, buck = [], []
    for end, sx in ((0, -1), (-1, 1)):
        e = line[end]
        side = col[np.abs(X[col, 0] - sx * np.abs(X[col, 0]).max()) < 25]
        zb = c.z_c - 60
        gs = side[np.argsort(np.abs(X[side, 2] - zb))[:6]] if len(side) else []
        tgt = X[gs].mean(0) if len(gs) else e + [0, 0, -200]
        tgt = tgt + np.array([sx * 4, 0, 0])
        path = np.array([e + [sx * 20, 0, 0], e + [sx * 30, 0, -40], tgt + [sx * 4, 0, 30], tgt])
        pth = G.catmull_rom(path, 8)
        straps.append(G.ribbon(pth, 25.0, 1.5, np.tile([sx * 1.0, 0, 0], (len(pth), 1)), step=6.0))
        buck.append(_block(tgt + [sx * 6, 0, 18], (8, 30, 46), e=0.35))
    return roll, straps, buck, line


def _pouch(line, CO, X, T, piece):
    P = CO.POUCH
    top_z = line[:, 2].max() + 27
    yc = float(line[:, 1].mean()) + 12
    zc = top_z + P["H"] / 2 - 10
    pouch = G.superellipsoid([0, yc, zc], [P["L"] / 2, P["W"] / 2, P["H"] / 2], e_ns=0.32, e_ew=0.28, nu=72, nv=28)
    # camo top: a thin cap over the upper surface of the pouch
    cap = G.superellipsoid([0, yc, zc + 2.0], [P["L"] / 2 - 6, P["W"] / 2 - 6, P["H"] / 2], e_ns=0.32, e_ew=0.28,
                           nu=72, nv=28)
    keep = cap.vertices[cap.faces].mean(1)[:, 2] > zc + P["H"] * 0.40
    capm = G._mesh(cap.vertices, cap.faces[keep], np.column_stack([cap.vertices[:, 0], cap.vertices[:, 1]]) / 380.0 *
                   1.0, flip_if_negative=False)
    xs = np.linspace(-150, 150, 40)
    ya = yc + P["W"] / 2 + 0.5
    zp = np.column_stack([xs, np.full(40, ya), np.full(40, zc + 14)])
    zipm = G.concat([G.ribbon(zp, 9.0, 1.2, np.tile([0, 1.0, 0], (40, 1)), step=8.0),
                     _block([152, ya + 3, zc + 4], (8, 5, 24), e=0.4)])
    straps, hooks = [], []
    for sx in (-1, 1):
        x = sx * 120
        A = np.array([x, yc - P["W"] / 2 + 6, zc - P["H"] / 2 + 6])
        Bp = np.array([x, line[:, 1].min() - 22, line[:, 2].min() - 50])
        straps.append(G.ribbon(G.catmull_rom(np.array([A, A + [0, -16, -10], Bp]), 6), 25.0, 1.4,
                               np.tile([0, -1.0, 0], (13, 1)), step=6.0))
        hooks.append(_block(Bp + [0, -2, -6], (8, 4, 28), e=0.5))
        A2 = np.array([x * 1.15, yc + P["W"] / 2 - 6, zc - P["H"] / 2 + 6])
        B2 = np.array([x * 1.35, yc + P["W"] / 2 + 10, line[:, 2].min() - 40])
        straps.append(G.ribbon(G.catmull_rom(np.array([A2, A2 + [0, 14, -12], B2]), 6), 25.0, 1.4,
                               np.tile([0, 1.0, 0], (13, 1)), step=6.0))
        hooks.append(_block(B2 + [0, 3, -6], (8, 4, 28), e=0.5))
    return pouch, capm, zipm, straps, hooks


def _wing(D, c, BC, sx, yf_of, yb_of, a_of, tripod=False):
    z0, z1, W = 150.0, 600.0, 200.0
    nu, nv = 12, 36
    U, Vv = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    Z = z0 + Vv * (z1 - z0)
    Y = np.array([[yf_of(z) + 12 + u * W for u, z in zip(ur, zr)] for ur, zr in zip(U, Z)])
    Xx = sx * np.array([[a_of(z) for z in row] for row in Z])
    P0 = np.stack([Xx, Y, Z], -1).reshape(-1, 3)
    P, n = D(P0, 3.0)
    P, n = P.reshape(nu + 1, nv + 1, 3), n.reshape(nu + 1, nv + 1, 3)
    if tripod:   # bulge over the tripod legs bundled at 115 mm from the frame-side corner
        ytri = U * W + 12
        bump = 34.0 * np.clip(1 - ((ytri - 115.0) / 75.0) ** 2, 0, None) ** 0.6
        P = P + n * bump[..., None]
    wing = _slab(P, P + n * 3.0, Y / G.TILE_MM, Z / G.TILE_MM)
    # camo bar: the last 25 mm of the wing (its aft, leading edge)
    sel = U >= 1 - 25.0 / W
    i0 = int(np.argmax(sel[:, 0]))
    Pb, nb = P[i0 - 1:], n[i0 - 1:]
    bar = _slab(Pb + nb * 3.2, Pb + nb * 4.2, Y[i0 - 1:] / 380.0, Z[i0 - 1:] / 380.0)
    straps, hw = [], []
    for zs in (260.0, 490.0):
        j = int(np.argmin(np.abs(Z[0] - zs)))
        A = P[-1, j] + n[-1, j] * 4.0
        corner0 = np.array([sx * a_of(zs), yb_of(zs), zs])
        Bc, nB = D([corner0 + [sx * 0.0, -4.0, 0]], 2.0)
        path = np.array([A - [0, 30, 0], A + [0, 5, 0], 0.5 * (A + Bc[0]) + nB[0] * 4, Bc[0]])
        pth = G.catmull_rom(path, 6)
        nrm = np.tile([sx * 1.0, 0, 0], (len(pth), 1))
        straps.append(G.ribbon(pth, 25.0, 1.5, nrm, step=5.0))
        hw.append(_block(A + n[-1, j] * 3 + [0, 2, 0], (5, 10, 30), e=0.5))          # G-hook on the wing
        hw.append(_block(Bc[0] + nB[0] * 4, (5, 12, 32), e=0.35))                  # ladder lock at the seam loop
    return wing, bar, straps, hw


def _tripod(c, BC, yf_of, a_of):
    legs = []
    a = a_of(400)
    for dy, dx in ((-13, 0), (13, 0), (0, 12)):
        y = yf_of(400) + 12 + 115 + dy
        x = a + 3 + 20 + dx
        legs.append(G.capsule_between([x, y, 95], [x, y, 860], 10.5))
    legs.append(_block([a + 23, yf_of(880) + 127, 890], (52, 52, 60), e=0.4))
    return G.concat(legs)


# ============================================================================ swap SPINE -> CORRIE in a built pack
def corrie_pack(params: dict):
    from .model import build_pack
    pack = build_pack(params)
    keep = [p for p in pack.parts if p.name not in SPINE_BAG_PARTS and not p.name.startswith(SPINE_PREFIX_DROP)]
    cp, met = corrie_parts(params, None)
    pack.parts = keep + cp + float_wraps(cp)
    pack.metrics.update(met)
    pack.metrics["bag_type"] = "corrie_box_rolltop"
    return pack


def float_wraps(cp):
    """W1-W3 round meat and bag in float mode (170 mm gap): loops round the convex hull of the frame anchors and the
    bag section shifted aft by the gap (the SPINE wraps were drawn round SPINE's shape)."""
    from shapely.geometry import MultiPoint
    body = next(p for p in cp if p.name == "corrie_body").mesh
    out = []
    for zs in (250.0, 420.0, 640.0):
        V = body.vertices
        sl = V[np.abs(V[:, 2] - zs) < 12][:, :2] + np.array([0, 170.0])
        anchors = np.array([[x, y] for x in (-125.0, 125.0) for y in (0.0, 30.0)])
        hull = MultiPoint(np.vstack([sl, anchors]).tolist()).convex_hull.buffer(6.0).exterior
        pts = np.array(hull.coords)
        P = np.column_stack([pts[:, 0], pts[:, 1], np.full(len(pts), zs)])
        P = G.resample(P, 10.0)
        out.append(G.ribbon(P, 25.0, 1.6, np.tile([0, 0, 1.0], (len(P), 1)), step=10.0))
    return [Part("corrie_float_wraps_g170", G.concat(out), "webbing", "haul", modes=("pack_haul",), gap=170.0,
                 label="W1-W3 round bag and meat (float, 170 mm)")]
