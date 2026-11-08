"""CORRIE bag for the 3D model (huntkit.viz3d), built on the CLOTH-SIM drape of its flat pieces.

The bag skin is the simulated shape (``huntkit.clothsim``, scenario ``corrie_PR19``, fine mesh h 25 mm): CORRIE's
actual flat pieces sewn together, hung on the frame by the hinge eyes, hooks, crown hood and guys, and loaded. The
render uses the ``packed`` case (0.5 kPa everyday load, 19 in) by default; ``CORRIE_CASE=fill`` shows the 68 kg
granular fill. Every detail part is placed ON that deformed surface through :class:`Skin` (projection onto the
smoothed sim mesh), so nothing floats or sinks. Same materials, camo texture, lighting, frame, harness, hood and
mannequin as the SPINE renders (``huntkit.viz3d.model``).

    from huntkit.viz3d.corrie import corrie_pack
    pack = corrie_pack(params)          # PackModel with SPINE's bag swapped for CORRIE

Render-only liberties (not in the sim, stated so nobody reads them as results):
* the skin is Taubin-smoothed and subdivided once (silhouette), the sim's node positions are otherwise kept;
* the wings, roll, pouch, straps and open door are placed geometry (the sim models the body pieces only);
* the chevron kick plate is cut round the door zip (SH-01a peak 140 mm would cross the zip at z 110: flagged in
  designs/pack_5200/analysis/corrie_body.md).

Variants used by the viewer toggles: ``rolled`` = door closed (hidden when "full" is on), ``full`` = door folded up +
lining + IM straps inside, ``lid`` = tripod under the right wing, ``nolid`` = the plain right wing.
Design record: designs/pack_5200/analysis/corrie_body.md.
"""
from __future__ import annotations

import os
import pickle
import sys
from collections import defaultdict
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
CASE = os.environ.get("CORRIE_CASE", "packed")
BE = (0.0, 260.0, 0.0)
SPINE_BAG_PARTS = ("bag_body", "bag_body_full", "bag_bottom", "bag_trim", "diagonal_band", "bag_shards", "zip_pulls",
                   "bag_boot_tabs", "side_pockets", "rolltop", "rolltop_straps", "rolltop_full", "rolltop_full_straps",
                   "lid", "lid_shard", "lid_trim", "compression_straps", "guy_tabs_b22", "guy_tabs_b22_full",
                   "bow_carry", "bow_carry_hook")
SPINE_PREFIX_DROP = ("top_guys", "haul_wraps_meat", "crown_wrap_meat", "crown_wrap")
# SPINE frame-interface parts on the B-01 outer face: same x / z on CORRIE (unchanged interface), snapped onto CORRIE's
# simulated B-01 face (they were drawn on SPINE's frame face, which lies inside CORRIE's box)
B01_PARTS = ("tab_b17", "doublers_b18_b23", "hook_tongues", "bag_hooks", "hinge_eyes", "hood_ladders")
WEB = 25.0          # webbing width, mm
ROLL_R = 29.0       # 3 turns of 330D + collar + hem band, ~58 mm closed roll (D_TOP 62)


def _concept():
    sys.path.insert(0, str(PACK / "concepts"))
    sys.path.insert(0, str(PACK))
    import bag_concepts as BC  # noqa: E402
    import corrie as CO  # noqa: E402
    return BC, CO


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


# ============================================================================ simulated skin
def sim_skin(sim_dir=SIM_DIR, case=None, fine=True) -> dict:
    """Deformed CORRIE mesh: nodes X (FCS mm), start nodes X0, triangles, piece name per triangle, per-node UV (mm on
    the flat pattern of one of its pieces). Cached next to the sim output."""
    case = case or CASE
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
    """(kept for callers of the first version) drafted point -> simulated shape by nearest-node displacement."""

    def __init__(self, sk):
        self.sk = sk
        self.tree = cKDTree(sk["X0"])

    def __call__(self, P, offset=0.0, k=6):
        P = np.atleast_2d(np.asarray(P, float))
        d, j = self.tree.query(P, k=k)
        w = 1.0 / np.maximum(d, 1e-3) ** 2
        w /= w.sum(1, keepdims=True)
        return P + np.einsum("ij,ijk->ik", w, self.sk["X"][j] - self.sk["X0"][j]), None


def _smooth(V, F, it=6):
    tm = trimesh.Trimesh(V.copy(), F.copy(), process=False)
    trimesh.smoothing.filter_taubin(tm, lamb=0.5, nu=-0.53, iterations=it)
    return np.asarray(tm.vertices)


class Skin:
    """The smoothed, once-subdivided sim mesh plus a projector: ``project`` snaps any point onto the skin (IDW of the
    nearest vertices and their normals), ``on`` maps a point of the DRAFTED box (concept coordinates) onto the
    deformed skin, ``push_out`` keeps points at least ``clear`` mm outside it."""

    def __init__(self, sk, smooth_it=10):
        T = sk["tris"]
        X = _smooth(sk["X"], T, smooth_it)
        V, F, att = trimesh.remesh.subdivide(X, T, vertex_attributes={"uv": sk["uv"] / G.TILE_MM, "x0": sk["X0"]})
        V = _smooth(V, F, 3)
        self.V, self.F, self.uv, self.x0 = V, F, att["uv"], att["x0"]
        self.piece = np.repeat(np.asarray(sk["piece"]), 4)
        tm = trimesh.Trimesh(V, F, process=False)
        vn = np.asarray(tm.vertex_normals)
        if np.mean(np.einsum("ij,ij->i", vn, V - V.mean(0))) < 0:
            vn = -vn
            self.F = F[:, ::-1]
        self.vn = vn
        self.tree = cKDTree(V)
        self.tree0 = cKDTree(self.x0)

    def project(self, P, lift=0.0, k=4):
        P = np.atleast_2d(np.asarray(P, float))
        d, j = self.tree.query(P, k=k)
        w = 1.0 / np.maximum(d, 0.5) ** 2
        w /= w.sum(1, keepdims=True)
        v = np.einsum("ij,ijk->ik", w, self.V[j])
        n = _unit(np.einsum("ij,ijk->ik", w, self.vn[j]))
        q = P - np.einsum("ij,ij->i", P - v, n)[:, None] * n
        return q + lift * n, n

    def on(self, P0, lift=0.0, k=6):
        P0 = np.atleast_2d(np.asarray(P0, float))
        d, j = self.tree0.query(P0, k=k)
        w = 1.0 / np.maximum(d, 0.5) ** 2
        w /= w.sum(1, keepdims=True)
        P = P0 + np.einsum("ij,ijk->ik", w, self.V[j] - self.x0[j])
        return self.project(P, lift)

    def push_out(self, P, clear=2.0, it=4):
        P = np.atleast_2d(np.asarray(P, float)).copy()
        for _ in range(it):
            q, n = self.project(P)
            s = np.einsum("ij,ij->i", P - q, n)
            m = s < clear
            if not m.any():
                break
            P[m] += (clear - s[m])[:, None] * n[m]
        return P

    def faces_of(self, mask):
        return self.F[mask]

    def submesh(self, mask, uv=None):
        Fm = self.F[mask]
        used = np.unique(Fm)
        remap = -np.ones(len(self.V), int)
        remap[used] = np.arange(len(used))
        return G._mesh(self.V[used], remap[Fm], (self.uv if uv is None else uv)[used], flip_if_negative=False)


def split_by_field(V, F, attrs: dict, f):
    """Cut triangles exactly along the zero line of a per-vertex field ``f`` (linear on each triangle). Returns new V,
    attrs, faces with f < 0, faces with f >= 0, and the indices of the cut vertices (on f = 0)."""
    V = [*np.asarray(V, float)]
    A = {k: [*np.asarray(a, float)] for k, a in attrs.items()}
    f = np.where(np.abs(f) < 1e-6, 1e-6, f)
    fl = list(f)
    cache, cut = {}, []

    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            t = fl[a] / (fl[a] - fl[b])
            V.append(V[a] + t * (V[b] - V[a]))
            for k in A:
                A[k].append(A[k][a] + t * (A[k][b] - A[k][a]))
            fl.append(0.0)
            cache[key] = len(V) - 1
            cut.append(cache[key])
        return cache[key]
    neg, pos = [], []
    for tri in F:
        s = [fl[i] < 0 for i in tri]
        if all(s):
            neg.append(tri)
            continue
        if not any(s):
            pos.append(tri)
            continue
        lone = [i for i in range(3) if s[i] != (sum(s) >= 2)][0]
        a, b, c = tri[lone], tri[(lone + 1) % 3], tri[(lone + 2) % 3]
        pab, pac = mid(a, b), mid(a, c)
        lone_side, other = (neg, pos) if s[lone] else (pos, neg)
        lone_side.append([a, pab, pac])
        other += [[pab, b, c], [pab, c, pac]]
    return (np.array(V), {k: np.array(v) for k, v in A.items()}, np.array(neg, int).reshape(-1, 3),
            np.array(pos, int).reshape(-1, 3), np.array(cut, int))


def _sub(V, F, uv):
    used = np.unique(F)
    remap = -np.ones(len(V), int)
    remap[used] = np.arange(len(used))
    return G._mesh(V[used], remap[F], uv[used], flip_if_negative=False)


# ============================================================================ polylines
def _chains_from_edges(E):
    """Chain undirected edges into polylines (break at junctions)."""
    adj = defaultdict(list)
    for u, v in E:
        adj[u].append(v)
        adj[v].append(u)
    seen, chains = set(), []
    for u, v in E:
        k = (min(u, v), max(u, v))
        if k in seen:
            continue
        seen.add(k)
        chain = [u, v]
        for end in (0, 1):
            while True:
                tip = chain[-1] if end == 0 else chain[0]
                prev = chain[-2] if end == 0 else chain[1]
                if len(adj[tip]) != 2:
                    break
                nxt = [w for w in adj[tip] if w != prev and (min(tip, w), max(tip, w)) not in seen]
                if not nxt:
                    break
                w = nxt[0]
                seen.add((min(tip, w), max(tip, w)))
                if end == 0:
                    chain.append(w)
                else:
                    chain.insert(0, w)
        chains.append(chain)
    return chains


def seam_chains(F, piece):
    """{frozenset(pieceA, pieceB): [chain, ...]} for every edge shared by two pieces."""
    ef = defaultdict(set)
    for t, tri in enumerate(F):
        for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            ef[(min(u, v), max(u, v))].add(piece[t])
    by = defaultdict(list)
    for e, ps in ef.items():
        if len(ps) == 2:
            by[frozenset(ps)].append(e)
    return {k: _chains_from_edges(E) for k, E in by.items()}


def join_chains(polys, tol=30.0):
    """Greedy end-to-end join of polylines into one (the longest first)."""
    polys = sorted([np.asarray(q, float) for q in polys], key=len, reverse=True)
    out = polys.pop(0)
    while polys:
        best = None
        for i, q in enumerate(polys):
            for qq in (q, q[::-1]):
                for at_end in (True, False):
                    d = np.linalg.norm((out[-1] if at_end else out[0]) - (qq[0] if at_end else qq[-1]))
                    if best is None or d < best[0]:
                        best = (d, i, qq, at_end)
        d, i, qq, at_end = best
        polys.pop(i)
        if d > tol:
            continue
        out = np.vstack([out, qq]) if at_end else np.vstack([qq, out])
    return out


def boundary_chains(F, keep=None):
    cnt = defaultdict(int)
    for tri in F:
        for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            cnt[(min(u, v), max(u, v))] += 1
    E = [e for e, n in cnt.items() if n == 1 and (keep is None or keep(e))]
    return _chains_from_edges(E)


def smooth_line(P, step=4.0, sigma=12.0, closed=False):
    """Resample a polyline at ``step`` and Gaussian-smooth it along its length (ends pinned)."""
    P = G.resample(np.asarray(P, float), step) if len(P) > 1 else np.asarray(P, float)
    n = len(P)
    if n < 5 or sigma <= 0:
        return P
    h = max(1, int(round(sigma / step)))
    k = np.exp(-0.5 * (np.arange(-3 * h, 3 * h + 1) / h) ** 2)
    k /= k.sum()
    if closed:
        Q = np.vstack([P[-3 * h:], P, P[:3 * h]])
        return np.stack([np.convolve(Q[:, i], k, "same")[3 * h:3 * h + n] for i in range(3)], -1)
    Q = np.vstack([np.repeat(P[:1], 3 * h, 0), P, np.repeat(P[-1:], 3 * h, 0)])
    S = np.stack([np.convolve(Q[:, i], k, "same")[3 * h:3 * h + n] for i in range(3)], -1)
    S[0], S[-1] = P[0], P[-1]
    return S


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
    m = G._mesh(V, np.array(F), uv, flip_if_negative=False)
    if G._signed_volume(m) < 0:
        m.faces = m.faces[:, ::-1]
    return m


def _block(c, size, e=0.3, R=None):
    return G.superellipsoid(c, np.asarray(size, float) / 2, e_ns=e, e_ew=e, nu=24, nv=12, R=R)


def _frame(n, t):
    """Rotation matrix with columns (t, n x t, n): local x along the strap, z out of the surface."""
    n, t = _unit(n), _unit(t)
    t = _unit(t - np.dot(t, n) * n)
    return np.column_stack([t, np.cross(n, t), n])


def strap(skin, pts, clear=2.0, width=WEB, thick=1.6, sigma=10.0, extra_push=None):
    """Webbing lying on the skin (and over anything ``extra_push`` pushes it off)."""
    P = smooth_line(np.asarray(pts, float), 4.0, sigma)
    for _ in range(2):
        P = skin.push_out(P, clear)
        if extra_push is not None:
            P = extra_push(P)
    P = smooth_line(P, 4.0, 4.0)
    _, n = skin.project(P)
    return G.ribbon(P, width, thick, n, step=4.0), P, n


def g_hook(p, n, t):
    """25 mm aluminium G-hook (HAUL family): a flat hook blade lying on the strap end."""
    return _block(p, (30, 11, 4.5), e=0.45, R=_frame(n, t))


def ladder_lock(p, n, t):
    return _block(p, (24, 31, 7), e=0.3, R=_frame(n, t))


def side_release(p, n, t):
    return _block(p, (48, 31, 10), e=0.35, R=_frame(n, t))


# ============================================================================ the CORRIE parts
def corrie_parts(p: dict, g: dict) -> tuple[list, dict]:
    BC, CO = _concept()
    c = CO.make()
    sk = sim_skin()
    S = Skin(sk)
    parts, metrics = [], {}
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    H = CO.DOOR
    Z0 = BC.Z0
    piece = S.piece
    door_m = piece == "B-02door"
    floor_m = piece == "B-05"
    body_m = ~(door_m | floor_m)

    # ---- skin: body split along the chevron kick-plate line (camo below), door, floor
    def door_bottom(x):
        hw = a_of(H["z_lo"]) - H["inset"]
        ax = abs(x)
        if ax >= hw:
            return np.inf
        if ax <= hw - H["r"]:
            return H["z_lo"]
        return H["z_lo"] + H["r"] - np.sqrt(max(H["r"] ** 2 - (ax - (hw - H["r"])) ** 2, 0.0))

    a0 = a_of(Z0)

    def kick_line(x0):
        x, y, z = x0
        a, yf, yb = a_of(z), yf_of(z), yb_of(z)
        if y < yf + 4:                                   # frame face: no kick plate
            return Z0 - 60.0
        if abs(y - yb) < 4 or y > yb:                    # aft face: chevron, kept 15 mm under the door zip
            chev = Z0 + 70 + 70 * (1 - min(abs(x) / a0, 1.0))
            return min(chev, door_bottom(x) - 15.0)
        return Z0 + 70.0                                 # side gussets
    fk = np.array([z - kick_line(x0) for x0, z in zip(S.x0, S.x0[:, 2])])
    Vk, Ak, Fneg, Fpos, cut = split_by_field(S.V, S.F[body_m], {"uv": S.uv}, fk)
    body = _sub(Vk, Fpos, Ak["uv"])
    kick = _sub(Vk, Fneg, Ak["uv"])
    door = S.submesh(door_m)
    floor = S.submesh(floor_m)
    parts.append(Part("corrie_body", body, "body", "bag", modes=BAGM, explode=BE, floats=True,
                      label=f"CORRIE main bag (cloth-sim drape of the flat pieces, {CASE} case, 19 in)"))
    parts.append(Part("corrie_kick", kick, "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Chevron kick plate SH-01 (camo, wear line)"))
    parts.append(Part("corrie_door", door, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                      label="Horseshoe door (closed)"))
    parts.append(Part("corrie_bottom", floor, "tpu", "bag", modes=BAGM, explode=(0, 260, -40), floats=True,
                      label="Bottom B-05 (500D)"))
    # kick-plate edge binding
    cutset = set(cut.tolist())
    kb = []
    for ch in boundary_chains(Fneg, keep=lambda e: e[0] in cutset and e[1] in cutset):
        if len(ch) > 3:
            P = smooth_line(Vk[ch], 4.0, 6.0)
            q, n = S.project(P, 1.0)
            kb.append(G.tube(q, 1.7, n=8))

    # ---- seams: the sim's own piece boundaries, smoothed, as bound-seam piping
    ch = seam_chains(S.F, piece)
    zip_key = frozenset(("B-02door", "B-02u"))
    tubes = []
    for key, chains in ch.items():
        if key == zip_key:
            continue
        for cc in chains:
            if len(cc) > 3:
                P = smooth_line(S.V[cc], 4.0, 10.0)
                q, _ = S.project(P, 1.2)
                tubes.append(G.tube(q, 2.1, n=8))
    parts.append(Part("corrie_seams", G.concat(tubes + kb), "trim", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Bound seams"))

    # ---- door zip: the door | U-surround seam itself, #10 coil, 2 sliders parked under 2 camo garages
    ZP = smooth_line(join_chains([S.V[cc] for cc in ch[zip_key] if len(cc) > 5]), 3.0, 18.0)
    if ZP[0, 0] > ZP[-1, 0]:
        ZP = ZP[::-1]
    zq, zn = S.project(ZP, 1.0)
    tape = G.ribbon(zq, 13.0, 1.0, zn, step=3.0)
    coil = G.tube(zq + zn * 1.0, 1.9, n=8)
    parts.append(Part("corrie_door_zip", G.concat([tape, coil]), "hardware", "bag", modes=BAGM, explode=BE,
                      floats=True, label="#10 coil door zip (1.26 m)"))
    sl, pulls, gar = [], [], []
    dz = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(zq, axis=0), axis=1))])
    for end in (0, -1):
        s_end = dz[end]
        s_sl = s_end + (70.0 if end == 0 else -70.0)
        i = int(np.argmin(np.abs(dz - s_sl)))
        t = zq[min(i + 1, len(zq) - 1)] - zq[max(i - 1, 0)]
        pnt, nn = zq[i], zn[i]
        sl.append(_block(pnt + nn * 3.5, (24, 13, 6), e=0.35, R=_frame(nn, t)))
        # cord pull: 3 mm Dyneema loop hanging from the slider + rubber sleeve
        down = _unit(np.array([0, 0, -1.0]) - np.dot([0, 0, -1.0], nn) * nn)
        side = np.cross(nn, down)
        base = pnt + nn * 6.0
        loop = np.array([base, base + down * 18 + side * 6 + nn * 3, base + down * 40 + nn * 5,
                         base + down * 18 - side * 6 + nn * 3])
        pulls.append(G.tube(G.catmull_rom(loop, 8, closed=True), 1.5, n=6))
        pulls.append(G.capsule_between(base + down * 34 + nn * 6, base + down * 60 + nn * 7, 4.2))
        # garage SH-07 40 x 60 over the zip end
        ge = zq[end] + (zq[end] - zq[end + (8 if end == 0 else -8)]) * 0.0
        gar.append(patch(S, ge + down * -8, 42, 62, lift=2.6, thick=1.4, up=t if abs(t[2]) > 0.5 else (0, 0, 1)))
    parts.append(Part("corrie_zip_sliders", G.concat(sl), "aluminium", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Door zip sliders (2)"))
    parts.append(Part("corrie_zip_pulls", G.concat(pulls), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      label="3 mm cord pulls in rubber sleeves"))
    parts.append(Part("corrie_zip_garages", G.concat(gar), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Zip garages SH-07 (camo)"))

    # ---- door open: folded up the hinge band, top third flopped back over itself (lining shows, as a sewn door)
    dopen, dlin, drim = _door_open(S, door_m, H, ch)
    parts.append(Part("corrie_door_open", dopen, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Horseshoe door open (unzipped, folded up over the hinge band)"))
    parts.append(Part("corrie_door_lining", dlin, "harness", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="full"))
    parts.append(Part("corrie_door_rim", drim, "hardware", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Door half of the #10 zip"))
    inside = S.submesh(~door_m)
    lin = G._mesh(inside.vertices - 1.8 * _vnormals(inside), inside.faces[:, ::-1], inside.metadata["uv"],
                  flip_if_negative=False)
    parts.append(Part("corrie_lining", lin, "harness", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Inside of the bag (seen through the open door)"))

    # ---- B-22 guy tabs on the hinge band
    tabs = [patch(S, S.on([sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z])[0][0], 34, 46, lift=1.4, thick=1.6)
            for sx in (1, -1)]
    parts.append(Part("corrie_b22", G.concat(tabs), "hypalon", "bag", modes=BAGM, explode=BE, floats=True,
                      label="B-22 guy tabs at z 695 on the hinge band"))

    # ---- roll-top: the collar's closure line rolled 3 turns, ends clipped down to the side gussets
    roll_line, roll, spiral, rstraps, rhw, clip_paths = _rolltop(S, c, a_of, yf_of, yb_of)
    parts.append(Part("corrie_roll", roll, "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Roll-top closed (3 turns), camo hem band SH-03 outermost"))
    parts.append(Part("corrie_roll_ends", spiral, "trim", "bag", modes=BAGM, explode=BE, floats=True))
    parts.append(Part("corrie_roll_straps", G.concat(rstraps), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Roll clips (ROLL family) down to the side gussets"))
    parts.append(Part("corrie_roll_buckles", G.concat(rhw), "hardware", "bag", modes=BAGM, explode=BE, floats=True))

    # ---- top pouch seated on the roll
    pe = (0, 200, 160)
    pm, pcamo, ptrim, pzip, pzhw, pstr, phw = _pouch(S, CO.POUCH, roll_line, clip_paths, yf_of)
    parts.append(Part("corrie_pouch", pm, "body", "bag", modes=BAGM, explode=pe, floats=True,
                      label="Top pouch 4.0 L (removable), seated on the roll"))
    parts.append(Part("corrie_pouch_top", pcamo, "camo", "bag", modes=BAGM, explode=pe, floats=True,
                      label="Pouch top L-21 (camo)"))
    parts.append(Part("corrie_pouch_seams", ptrim, "trim", "bag", modes=BAGM, explode=pe, floats=True))
    parts.append(Part("corrie_pouch_zip", pzip, "hardware", "bag", modes=BAGM, explode=pe, floats=True,
                      label="#8 coil zip, aft long edge"))
    parts.append(Part("corrie_pouch_pull", pzhw, "webbing", "bag", modes=BAGM, explode=pe, floats=True))
    parts.append(Part("corrie_pouch_straps", G.concat(pstr), "webbing", "bag", modes=BAGM, explode=pe, floats=True,
                      label="Pouch straps: 2 rear to the frame-side hem loops, 2 front to the roll clips"))
    parts.append(Part("corrie_pouch_hooks", G.concat(phw), "aluminium", "bag", modes=BAGM, explode=pe, floats=True))

    # ---- wings (taut over the gusset bulge, hemmed, camo leading-edge bar, 2 G-hook straps each) + tripod
    tri_geo = _tripod_axis(S, a_of, yf_of, yb_of)
    for sx, side in ((1, "R"), (-1, "L")):
        for trip in ((False, True) if sx == 1 else (False,)):
            w, hem, bar, st, hw = _wing(S, sx, a_of, yf_of, yb_of, tri_geo if trip else None)
            var = ("lid" if trip else "nolid") if sx == 1 else None
            tag = f"{side}{'_tripod' if trip else ''}"
            ex = (sx * 120, 200, 0)
            parts.append(Part(f"corrie_wing_{tag}", G.concat([w, hem]), "tpu", "bag", modes=BAGM, explode=ex,
                              floats=True, variant=var, label="Side compression wing M-01 200 x 450 (330D, hemmed)"))
            parts.append(Part(f"corrie_wing_bar_{tag}", bar, "camo", "bag", modes=BAGM, explode=ex,
                              floats=True, variant=var, label="Wing leading-edge bar SH-06 (camo)"))
            parts.append(Part(f"corrie_wing_straps_{tag}", G.concat(st), "webbing", "bag", modes=BAGM,
                              explode=ex, floats=True, variant=var))
            parts.append(Part(f"corrie_wing_hw_{tag}", G.concat(hw), "aluminium", "bag", modes=BAGM,
                              explode=ex, floats=True, variant=var, label="G-hooks + ladder locks (HAUL family)"))
    tri_m, tri_rub = _tripod(tri_geo)
    parts.append(Part("corrie_tripod", tri_m, "carbon", "bag", modes=BAGM, floats=True, variant="lid",
                      label="Tripod under the right wing"))
    parts.append(Part("corrie_tripod_parts", tri_rub, "hardware", "bag", modes=BAGM, floats=True, variant="lid"))

    # ---- inside, seen through the open door: IM1-IM3 (bone webbing) across the frame face, hooks
    ims, imh = [], []
    for zs in (190.0, 330.0, 520.0):
        pts0 = np.array([[x, yf_of(zs) + 2, zs] for x in np.linspace(-120, 120, 25)])
        q, nn = S.on(pts0, -7.0)
        q = smooth_line(q, 4.0, 8.0)
        _, nn = S.project(q)
        ims.append(G.ribbon(q, 38.0, 1.8, -nn, step=4.0))
        for k in (0, -1):
            t = q[1] - q[0] if k == 0 else q[-1] - q[-2]
            imh.append(g_hook(q[k] - nn[k] * 3, -nn[k], t))
    parts.append(Part("corrie_im_straps", G.concat(ims), "meat_strap", "bag", modes=BAGM, floats=True, variant="full",
                      label="IM1-IM3 internal meat straps (38 mm), reachable through the door"))
    parts.append(Part("corrie_im_hooks", G.concat(imh), "aluminium", "bag", modes=BAGM, floats=True, variant="full"))

    # ---- top guys (19 in): hood ears -> B-22
    gu = []
    for sx in (1, -1):
        A = np.array([sx * 95.0, 21.7, 702.6 + 6])
        Bp, nB = S.on([sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z], 3.0)
        side, _ = S.on([sx * a_of(700), 0.5 * (yf_of(700) + yb_of(700)), 705], 4.0)
        pts = np.array([A, A + [sx * 40, 4, 2], side[0], Bp[0] + [0, -14, 0], Bp[0]])
        rib, Pg, ng = strap(S, G.catmull_rom(pts, 10), clear=2.5, sigma=14.0)
        gu.append(rib)
    parts.append(Part("corrie_top_guys@t19", G.concat(gu), "webbing", "attach", torso=19.0, modes=("pack",),
                      label="Top guys: crown hood ears -> B-22 (fixed length)"))

    metrics.update(corrie_sim_volume_L=float(abs(G._signed_volume(trimesh.Trimesh(sk["X"], sk["tris"], process=False)))
                                             / 1e6), corrie_render_case=CASE)
    return parts, metrics


def _vnormals(m):
    return np.asarray(trimesh.Trimesh(m.vertices, m.faces, process=False).vertex_normals)


def patch(S, centre, w, h, lift=1.0, thick=1.2, up=(0, 0, 1), nu=8, nv=10):
    """Small conformal slab (tab, garage) on the skin centred at ``centre``, ``h`` along ``up``."""
    q, n = S.project(np.asarray(centre, float)[None])
    n = n[0]
    up = _unit(np.asarray(up, float))
    tu = _unit(np.cross(up, n))
    tv = np.cross(n, tu)
    us = np.linspace(-w / 2, w / 2, nu + 1)
    vs = np.linspace(-h / 2, h / 2, nv + 1)
    U, Vv = np.meshgrid(us, vs, indexing="ij")
    P0 = q[0] + U.reshape(-1, 1) * tu + Vv.reshape(-1, 1) * tv
    # round the corners (r 8)
    P, nn = S.project(P0, lift)
    P, nn = P.reshape(nu + 1, nv + 1, 3), nn.reshape(nu + 1, nv + 1, 3)
    return _slab(P, P + nn * thick, U / G.TILE_MM, Vv / G.TILE_MM)


# ---------------------------------------------------------------------------- door open
def _door_open(S, door_m, H, ch):
    """Door unzipped and folded UP onto the hinge band: rises up the aft face from the hinge seam, folds over (R 9) and
    its last ~40 % hangs back down on itself, so the lining shows on the up-run and the outer face on the flop."""
    F = S.F[door_m]
    used = np.unique(F)
    x0 = S.x0[used]
    Vc = S.V[used]
    remap = -np.ones(len(S.V), int)
    remap[used] = np.arange(len(used))
    Fd = remap[F]
    zh = H["z_hinge"]
    # door coordinates: x across, s = distance down from the hinge, measured on the drafted (flat) door
    s = np.clip(zh - x0[:, 2], 0, None)
    x = x0[:, 0]
    # hinge seam on the deformed skin
    hk = frozenset(("B-02door", "B-02h"))
    hinge = np.vstack([S.V[cc] for cc in ch.get(hk, [])]) if hk in ch else Vc[s < 8]
    # upper aft-face profile y(z) per x from the skin above the hinge (B-02h + collar)
    up_m = np.isin(S.piece, ["B-02h", "B-06"])
    UV_ = np.unique(S.F[up_m])
    Pu, Nu = S.V[UV_], S.vn[UV_]
    keep = Nu[:, 1] > 0.35
    Pu = Pu[keep]
    L_up = 0.58 * s.max()
    r_f = 9.0
    out = np.zeros_like(Vc)
    tree_h = cKDTree(hinge[:, [0]])
    for xs in np.unique(np.round(x, 0)):
        mk = np.abs(x - xs) < 0.6
        _, j = tree_h.query([[xs]])
        h0 = hinge[j[0]]
        col = Pu[np.abs(Pu[:, 0] - xs) < 22]
        zz = np.linspace(h0[2], h0[2] + L_up + 40, 40)
        if len(col) > 5:
            yy = np.array([col[np.abs(col[:, 2] - z) < 18][:, 1].max() if (np.abs(col[:, 2] - z) < 18).any() else np.nan
                           for z in zz])
            ok = ~np.isnan(yy)
            yy = np.interp(zz, zz[ok], yy[ok]) if ok.sum() > 1 else np.full_like(zz, h0[1])
        else:
            yy = np.full_like(zz, h0[1])
        yy = np.maximum.accumulate(yy[::-1])[::-1] * 0 + yy          # keep the measured profile
        prof = np.column_stack([np.full_like(zz, xs), yy + 4.0, zz])
        prof[0] = [xs, h0[1] + 3.0, h0[2]]
        prof = smooth_line(prof, 4.0, 12.0)
        dd = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
        sv = s[mk]
        res = np.zeros((mk.sum(), 3))
        a = sv <= L_up
        res[a] = np.stack([np.interp(sv[a], dd, prof[:, k]) for k in range(3)], -1)
        top = np.array([np.interp(L_up, dd, prof[:, k]) for k in range(3)])
        b = ~a
        ang = np.clip((sv[b] - L_up) / r_f, 0, np.pi)
        cen = top + np.array([0, r_f, 0])
        fold = np.column_stack([np.full(b.sum(), xs), cen[1] - r_f * np.cos(ang), cen[2] + r_f * np.sin(ang)])
        rest = np.clip(sv[b] - L_up - np.pi * r_f, 0, None)
        hang = _unit(np.array([0, 0.18, -1.0]))
        fold += rest[:, None] * hang
        fold[:, 0] = xs
        res[b] = fold
        out[mk] = res
    mid = G._mesh(out, Fd, S.uv[used], flip_if_negative=False)
    vn = _vnormals(mid)
    upm = s < 0.5 * L_up
    if np.mean(vn[upm, 1]) < 0:
        vn = -vn
        Fd = Fd[:, ::-1]
    lining = G._mesh(out + vn * 1.1, Fd, S.uv[used], flip_if_negative=False)
    outer = G._mesh(out - vn * 1.1, Fd[:, ::-1], S.uv[used], flip_if_negative=False)
    # zip half along the free rim (everything but the hinge edge)
    rim = []
    for cc in boundary_chains(Fd, keep=lambda e: s[e[0]] > 6 or s[e[1]] > 6):
        if len(cc) > 4:
            rim.append(G.tube(smooth_line(out[cc], 3.0, 6.0), 2.4, n=8))
    return outer, lining, G.concat(rim)


# ---------------------------------------------------------------------------- roll-top
def _rolltop(S, c, a_of, yf_of, yb_of):
    col_m = S.piece == "B-06"
    col = np.unique(S.F[col_m])
    P = S.V[col]
    zt = P[:, 2].max()
    top = P[P[:, 2] > zt - 40]
    xs = np.linspace(top[:, 0].min(), top[:, 0].max(), 40)
    ys, zs = [], []
    for x in xs:
        m = np.abs(top[:, 0] - x) < 14
        sel = top[m] if m.sum() else top[np.argsort(np.abs(top[:, 0] - x))[:3]]
        k = np.argmax(sel[:, 2])
        ys.append(sel[:, 1].mean())
        zs.append(sel[k, 2])
    line = np.column_stack([xs, ys, np.array(zs) - ROLL_R * 0.55])
    line = smooth_line(line, 6.0, 40.0)
    # extend past the corners so the flat closure's ears disappear into the roll
    d0, d1 = _unit(line[0] - line[3]), _unit(line[-1] - line[-4])
    line = np.vstack([line[0] + d0 * 10, line, line[-1] + d1 * 10])
    roll = G.tube(line, ROLL_R, n=36, tile=G.TILE_MM)
    # roll ends: the 3 visible turns of a rolled closure, as a spiral bead on each end cap
    spir = []
    for end, d in ((0, d0), (-1, d1)):
        cpt = line[end] + d * 0.6
        e1 = _unit(np.cross(d, [0, 0, 1.0]))
        e2 = np.cross(d, e1)
        th = np.linspace(0, 3 * 2 * np.pi, 160)
        rr = 4 + (ROLL_R - 5) * th / th[-1]
        sp = cpt + np.outer(rr * np.cos(th), e1) + np.outer(rr * np.sin(th), e2)
        spir.append(G.tube(sp, 1.1, n=6))
    # clips: from each roll end down the side to a side-release buckle on the gusset (z_c - 40)
    straps, hw, paths = [], [], []
    for end, sx in ((0, -1), (-1, 1)):
        e = line[end]
        zb = c.z_c - 30
        yb_mid = 0.5 * (yf_of(zb) + yb_of(zb))
        tgt, tn = S.on([sx * a_of(zb), yb_mid, zb], 4.0)
        tgt, tn = tgt[0], tn[0]
        start = e + np.array([sx * 4, 0, ROLL_R * 0.2])
        over = e + np.array([sx * (ROLL_R + 4), 0, -ROLL_R * 0.2])
        pts = np.array([start + [0, 0, 0], over, 0.6 * over + 0.4 * tgt + np.array([sx * 12, 0, 0]), tgt + [0, 0, 26]])
        pth = G.catmull_rom(pts, 10)

        def push_roll(Q, line=line):
            tr = cKDTree(line)
            d, j = tr.query(Q)
            m = d < ROLL_R + 2
            Q = Q.copy()
            Q[m] = line[j[m]] + _unit(Q[m] - line[j[m]]) * (ROLL_R + 2)
            return Q
        rib, Pp, nn = strap(S, pth, clear=2.5, extra_push=push_roll)
        straps.append(rib)
        paths.append(Pp)
        t = Pp[-1] - Pp[-4]
        hw.append(side_release(Pp[-1] + nn[-1] * 3 - _unit(t) * 18, nn[-1], t))
        # female half on a short tab sewn into the gusset
        tab = Pp[-1] + _unit(t) * np.linspace(0, 45, 8)[:, None]
        tq, tnn = S.project(tab, 1.2)
        straps.append(G.ribbon(tq, WEB, 1.4, tnn, step=4.0))
    return line, roll, G.concat(spir), straps, hw, paths


# ---------------------------------------------------------------------------- pouch
def _pouch(S, P, line, clip_paths, yf_of):
    """4.0 L pouch draped over the roll: the base hugs the roll top (3 mm into it) and droops ~25 mm to its front
    and rear edges; the 70 mm boxing keeps the thickness. Built in pouch-local coordinates, then mapped."""
    L, W, Hh = P["L"], P["W"], P["H"]
    xs_line = line[:, 0]
    yr = float(np.interp(0.0, xs_line, line[:, 1]))

    def roll_top(x):
        return np.interp(x, xs_line, line[:, 2]) + ROLL_R

    def pmap(Q):
        """pouch-local (x, y from the roll axis, h 0..Hh above the base) -> FCS."""
        Q = np.atleast_2d(np.asarray(Q, float))
        x, y, h = Q[:, 0], Q[:, 1], Q[:, 2]
        base = roll_top(x) - 3.0 - 26.0 * np.clip(np.abs(y) / (W / 2), 0, 1.2) ** 2
        sag_top = 6.0 * (1 - (x / (L / 2)) ** 2).clip(0) * (1 - (y / (W / 2)) ** 2).clip(0)
        z = base + h - sag_top * (h / Hh)
        return np.column_stack([x, yr + y, z])
    body = G.superellipsoid([0, 0, Hh / 2], [L / 2, W / 2, Hh / 2], e_ns=0.22, e_ew=0.16, nu=96, nv=30)
    Vl = body.vertices.copy()
    Vm = pmap(Vl)
    fn = trimesh.Trimesh(Vl, body.faces, process=False).face_normals
    topf = fn[:, 2] > 0.80
    uvp = np.column_stack([Vl[:, 0], Vl[:, 1]]) / G.TILE_MM
    side_uv = body.metadata["uv"]
    pm = _sub(Vm, body.faces[~topf], side_uv)
    pc = _sub(Vm + np.array([0, 0, 0.6]), body.faces[topf], uvp)
    # seam piping round the top panel and the base
    pip = []
    for cc in boundary_chains(body.faces[topf]):
        if len(cc) > 8:
            pip.append(G.tube(smooth_line(Vm[cc], 3.0, 3.0, closed=True), 1.9, n=8))
    botf = fn[:, 2] < -0.80
    for cc in boundary_chains(body.faces[botf]):
        if len(cc) > 8:
            pip.append(G.tube(smooth_line(Vm[cc], 3.0, 3.0, closed=True), 1.9, n=8))
    # zip on the aft long edge: just below the top seam on the boxing strip
    zl = np.column_stack([np.linspace(-150, 150, 60), np.full(60, W / 2 + 0.4), np.full(60, Hh - 9)])
    zp = pmap(zl)
    zipm = G.concat([G.ribbon(zp, 9.0, 1.0, np.tile([0, 1.0, 0], (60, 1)), step=4.0),
                     G.tube(zp + [0, 1.2, 0], 1.4, n=6)])
    sl = zp[-4] + [0, 3.5, 0]
    pull = G.concat([_block(sl, (20, 6, 11), e=0.35),
                     G.tube(G.catmull_rom(np.array([sl + [4, 3, 0], sl + [14, 6, -16], sl + [8, 7, -38],
                                                    sl + [0, 6, -16]]), 8, closed=True), 1.4, n=6),
                     G.capsule_between(sl + [6, 8, -30], sl + [9, 9, -52], 4.0)])
    # straps: 2 rear (frame side) down the collar to the hem loops, 2 front over the roll to the roll clips
    straps, hooks = [], []
    for sx in (-1, 1):
        x = sx * 118.0
        A = pmap([[x, -W / 2 + 4, 14]])[0]
        A_out = pmap([[x, -W / 2 - 3, 4]])[0]
        Bz = A[2] - 85
        Bp, _ = S.on([x, yf_of(1000) + 6, Bz])
        pts = np.array([pmap([[x, -W / 2 + 30, 2]])[0], A_out, 0.5 * (A_out + Bp[0]) + [0, -6, 0], Bp[0]])
        rib, Pp, nn = strap(S, G.catmull_rom(pts, 8), clear=2.0)
        straps.append(rib)
        hooks.append(g_hook(Pp[-1] + nn[-1] * 3, nn[-1], Pp[-1] - Pp[-4]))
        # front: from the aft-bottom edge of the pouch, over the roll, to the roll-clip strap below the roll end
        cp = clip_paths[0] if sx < 0 else clip_paths[1]
        tgt = cp[int(len(cp) * 0.42)]
        A2 = pmap([[sx * 140.0, W / 2 + 3, 6]])[0]
        mid = pmap([[sx * 150.0, W / 2 + 12, -14]])[0]
        pts2 = np.array([pmap([[sx * 140.0, W / 2 - 26, 2]])[0], A2, mid, 0.5 * (mid + tgt) + [0, 14, 0], tgt])
        rr = line

        def push_roll(Q, rr=rr):
            tr = cKDTree(rr)
            d, j = tr.query(Q)
            m = d < ROLL_R + 2
            Q = Q.copy()
            Q[m] = rr[j[m]] + _unit(Q[m] - rr[j[m]]) * (ROLL_R + 2)
            return Q
        rib2, Pq, nq = strap(S, G.catmull_rom(pts2, 8), clear=2.5, extra_push=push_roll)
        straps.append(rib2)
        hooks.append(g_hook(Pq[-1] + nq[-1] * 4.5, nq[-1], Pq[-1] - Pq[-4]))
    return pm, pc, G.concat(pip), zipm, pull, straps, hooks


# ---------------------------------------------------------------------------- wings + tripod
def _tripod_axis(S, a_of, yf_of, yb_of, sx=1, u=0.52, R=19.0):
    """Vertical tripod bundle (3 legs, R 19 envelope) on the right gusset, clear of the bulge everywhere."""
    zz = np.linspace(110, 700, 40)
    root = np.array([S.on([sx * a_of(z), yf_of(z) + 6, z])[0][0] for z in zz])
    edge = np.array([S.on([sx * a_of(z), yb_of(z) - 10, z])[0][0] for z in zz])
    mid = root + u * (edge - root)
    q, n = S.project(mid)
    yt = float(np.median(q[:, 1]))
    xreq = []
    for z in zz:
        ring = S.V[np.abs(S.V[:, 2] - z) < 10]
        ring = ring[np.abs(ring[:, 1] - yt) < R]
        if len(ring):
            xreq.append((ring[:, 0] * sx).max())
    xt = sx * (max(xreq) + R + 1.0)
    return {"x": xt, "y": yt, "R": R, "z0": 95.0, "z1": 700.0, "sx": sx}   # collapsed tripod ~600 mm (ASSUMPTION)


def _tripod(tg):
    legs, parts = [], []
    xt, yt, R = tg["x"], tg["y"], tg["R"]
    r = 9.0
    for k in range(3):
        ang = np.pi / 2 + k * 2 * np.pi / 3
        dx, dy = (R - r) * np.cos(ang), (R - r) * np.sin(ang)
        legs.append(G.capsule_between([xt + dx, yt + dy, tg["z0"] + 25], [xt + dx, yt + dy, tg["z1"] - 40], r))
        parts.append(G.capsule_between([xt + dx, yt + dy, tg["z0"]], [xt + dx, yt + dy, tg["z0"] + 28], r + 1.5))
        for zc in (300.0, 500.0):   # leg-lock collars
            parts.append(G.capsule_between([xt + dx, yt + dy, zc], [xt + dx, yt + dy, zc + 26], r + 1.8))
    parts.append(_block([xt, yt, tg["z1"] - 20], (2 * R + 10, 2 * R + 10, 46), e=0.45))
    parts.append(_block([xt, yt, tg["z1"] + 22], (56, 30, 26), e=0.4))
    return G.concat(legs), G.concat(parts)


def _wing(S, sx, a_of, yf_of, yb_of, tri=None):
    """M-01 wing 200 x 450, root in the frame-side seam, z 150-600: a taut panel from the root line to near the aft
    corner, laid over the bulge (and over the tripod), 2.2 mm thick, hem roll on the free edges, camo bar on the aft
    25 mm, straps at z 260 / 490 from G-hooks on the wing edge to loops in the aft corner seam."""
    z0, z1, W = 150.0, 600.0, 200.0
    nu, nv = 22, 40
    us = np.linspace(0, 1, nu + 1)
    zz = np.linspace(z0, z1, nv + 1)
    root = np.array([S.on([sx * a_of(z), yf_of(z) + 4, z])[0][0] for z in zz])
    edge0 = np.array([S.on([sx * a_of(z), min(yf_of(z) + W, yb_of(z) - 14), z])[0][0] for z in zz])
    P = root[None, :, :] + us[:, None, None] * (edge0 - root)[None, :, :]
    P = P + sx * np.array([1.0, 0, 0]) * (8.0 * np.sin(np.pi * us))[:, None, None]
    flat = P.reshape(-1, 3)
    clear = 3.0
    for _ in range(3):
        flat = S.push_out(flat, clear)
        if tri is not None:
            d = flat[:, :2] - [tri["x"], tri["y"]]
            r = np.linalg.norm(d, axis=1)
            m = (r < tri["R"] + 2.5) & (flat[:, 2] > tri["z0"]) & (flat[:, 2] < tri["z1"])
            flat[m, :2] = np.array([tri["x"], tri["y"]]) + d[m] / r[m, None] * (tri["R"] + 2.5)
    P = flat.reshape(nu + 1, nv + 1, 3)
    # light relaxation across the panel so the push-out reads as cloth over a bump, not a kink
    for _ in range(3):
        Q = P.copy()
        Q[1:-1] = 0.5 * P[1:-1] + 0.25 * (P[:-2] + P[2:])
        P = Q
        flat = S.push_out(P.reshape(-1, 3), clear)
        P = flat.reshape(nu + 1, nv + 1, 3)
    du = np.gradient(P, axis=0)
    dv = np.gradient(P, axis=1)
    n = _unit(np.cross(du, dv))
    if np.mean(n[..., 0]) * sx < 0:
        n = -n
    Uu = np.linspace(0, W, nu + 1)[:, None] * np.ones((1, nv + 1))
    Zz = np.ones((nu + 1, 1)) * zz[None, :]
    wing = _slab(P, P + n * 2.2, Uu / G.TILE_MM, Zz / G.TILE_MM)
    hem = []
    for path in (P[-1], P[:, 0], P[:, -1]):
        hem.append(G.tube(path, 2.3, n=8))
    hem.append(G.tube(P[0] - n[0] * 0.5, 2.6, n=8))
    sel = Uu[:, 0] >= W - 27
    i0 = int(np.argmax(sel))
    bar = _slab(P[i0:] + n[i0:] * 2.4, P[i0:] + n[i0:] * 3.2, Uu[i0:] / G.TILE_MM, Zz[i0:] / G.TILE_MM)
    straps, hw = [], []
    for zs in (260.0, 490.0):
        j = int(np.argmin(np.abs(zz - zs)))
        A = P[-1, j] + n[-1, j] * 3.5
        tdir = _unit(P[-1, j] - P[-3, j])
        hw.append(g_hook(A + tdir * 2, n[-1, j], tdir))
        corner, cn = S.on([sx * a_of(zs), yb_of(zs) + 2, zs], 2.0)
        loop, ln = S.on([sx * (a_of(zs) - 6), yb_of(zs) + 2, zs], 2.0)
        mid = 0.5 * (A + corner[0]) + n[-1, j] * 4
        pts = np.array([A - tdir * 18, A + tdir * 8, mid, corner[0], loop[0]])
        rib, Pp, nn = strap(S, G.catmull_rom(pts, 8), clear=2.5, sigma=5.0)
        straps.append(rib)
        t = Pp[-1] - Pp[-4]
        hw.append(ladder_lock(Pp[-1] + nn[-1] * 3.5, nn[-1], t))
        # tail hanging down the corner seam from the ladder lock
        tail0 = Pp[-1]
        tail = np.array([tail0 + [0, 0, -k] for k in np.linspace(0, 75, 12)])
        tq, tn = S.project(tail, 2.2)
        tq[:, 0] = tq[:, 0] + sx * 0.0
        straps.append(G.ribbon(tq, WEB, 1.4, tn, step=4.0))
    return wing, G.concat(hem), bar, straps, hw


# ============================================================================ swap SPINE -> CORRIE in a built pack
def corrie_pack(params: dict):
    from .model import build_pack
    pack = build_pack(params)
    keep = [p for p in pack.parts if p.name not in SPINE_BAG_PARTS and not p.name.startswith(SPINE_PREFIX_DROP)]
    cp, met = corrie_parts(params, None)
    skin = Skin(sim_skin())
    keep = [snap_b01(q, skin) if q.name in B01_PARTS else q for q in keep]
    pack.parts = keep + cp + float_wraps(cp)
    pack.metrics.update(met)
    pack.metrics["bag_type"] = "corrie_box_rolltop"
    return pack


def snap_b01(part, S):
    """Move each connected piece of a B-01 face part along y so its bag side sits on CORRIE's B-01 face."""
    import copy
    f_m = S.piece == "B-01"
    Vb = S.V[np.unique(S.F[f_m])]
    tr = cKDTree(Vb[:, [0, 2]])
    M = part.mesh
    uv = M.metadata.get("uv", np.zeros((len(M.vertices), 2)))
    lab = trimesh.graph.connected_component_labels(M.face_adjacency, node_count=len(M.faces))
    V = M.vertices.copy()
    for k in np.unique(lab):
        vid = np.unique(M.faces[lab == k])
        c = V[vid].mean(0)
        d, j = tr.query([[c[0], c[2]]], k=8)
        yface = float(Vb[j[0], 1].min())
        V[vid, 1] += yface - V[vid, 1].max() + 0.4
    out = [G._mesh(V, M.faces, uv, flip_if_negative=False)]
    q = copy.copy(part)
    q.mesh = G.concat(out)
    return q


def float_wraps(cp):
    """W1-W3 round meat and bag in float mode (170 mm gap): loops round the convex hull of the frame anchors and the
    bag section shifted aft by the gap. Webbing stands on edge against the load (normal radial, in plan)."""
    from shapely.geometry import MultiPoint
    body = next(p for p in cp if p.name == "corrie_body").mesh
    out = []
    for zs in (250.0, 420.0, 640.0):
        V = body.vertices
        sl = V[np.abs(V[:, 2] - zs) < 12][:, :2] + np.array([0, 170.0])
        anchors = np.array([[x, y] for x in (-125.0, 125.0) for y in (0.0, 30.0)])
        hull = MultiPoint(np.vstack([sl, anchors]).tolist()).convex_hull.buffer(4.0, quad_segs=12).exterior
        pts = np.array(hull.coords)
        P = np.column_stack([pts[:, 0], pts[:, 1], np.full(len(pts), zs)])
        P = smooth_line(G.resample(P, 6.0), 6.0, 10.0, closed=True)
        cen = P.mean(0)
        nrm = _unit(np.column_stack([P[:, 0] - cen[0], P[:, 1] - cen[1], np.zeros(len(P))]))
        out.append(G.ribbon(P, 25.0, 1.6, nrm, step=6.0))
    return [Part("corrie_float_wraps_g170", G.concat(out), "webbing", "haul", modes=("pack_haul",), gap=170.0,
                 label="W1-W3 round bag and meat (float, 170 mm)")]
