"""Pack 5200 v3.1: the sewn main bag from the release patterns, on the frame, under the load cases.

Source of the pieces: ``designs/pack_5200/patterns_v31.py`` (read-only import of ``build_body``;
the same code that wrote ``outputs/release/pack5200_v3.1_patterns``). Each developed piece keeps
its flat mesh (pattern) and the master-surface 3D position of every pattern point, which is the
"arrangement" the sim starts from. Frame and spreader: ``designs/pack_5200/print/frame/
genframe_assembled.stl`` and ``genframe_barrier.stl`` (BP-06 rev B), sampled to point clouds.

Modelled bag: B-01, B-01b, B-01u (frame side), B-02a..d (face, diagonal zip as a seam, two darts),
B-03 R/L (gores), B-05 (floor), B-06 (roll-top collar up to the fill line, closed flat at the fill
line = the rolled closure). Not modelled: swells, ports, sleeves, pockets, band, binding, hem, the
roll itself (see analysis/cloth_sim.md).
"""
from __future__ import annotations

import hashlib
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.spatial import cKDTree

from .assemble import PieceSpec, assemble, densify
from .fabric import fabric, webbing
from .model import (Bending, Cable, Cables, DeadLoad, FieldContact, GapField, Gravity, Membrane, Pressure,
                    GasFill, Pins, PressureProfile, Sim)

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
CACHE = REPO / "outputs" / "clothsim" / "cache"
SCENARIO = Path(__file__).parent / "scenarios" / "pack5200_v31.yaml"
FRAME_STL = PACK / "print" / "frame" / "genframe_assembled.stl"
SPREADER_STL = PACK / "print" / "frame" / "genframe_barrier.stl"
DEV_IDS = ["B-01", "B-01b", "B-01u", "B-02a", "B-02b", "B-02c", "B-02d", "B-03"]


# ============================================================================ pattern cache
def _src_hash() -> str:
    h = hashlib.sha1()
    for f in ("patterns_v31.py", "build_geometry.py", "geometry.yaml", "panels.yaml", "attachment.yaml"):
        p = PACK / f
        if p.exists():
            h.update(p.read_bytes())
    h.update(b"clothsim-cache-v1")
    return h.hexdigest()[:12]


def load_patterns(verbose=True) -> dict:
    """Body pieces of the v3.1 release (cached: building them takes ~30 s)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"pack5200_v31_body_{_src_hash()}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    if verbose:
        print("building v3.1 body pieces from designs/pack_5200/patterns_v31.py (once, ~30 s) ...")
    sys.path.insert(0, str(PACK))
    import patterns_v31 as P  # noqa: E402  (read-only use of the pattern-maker's code)
    S = P.MasterSurface()
    ps = P.PatternSet()
    ps.surface = S
    body = P.build_body(ps, S, spacing=12.0)
    out = {"pieces": {}, "constants": {}, "release": "outputs/release/pack5200_v3.1_patterns"}
    for pid in DEV_IDS:
        dp = ps.dev[pid]
        fm = dp.mesh
        edges = []
        for nm, uv in dp.edges_uv.items():
            uvd = densify(np.asarray(uv, float), 2.0)
            edges.append((nm, np.asarray(dp.to_flat(uvd)), np.asarray(S(uvd))))
        p = dp.piece
        out["pieces"][pid] = {"kind": "dev", "name": p.name, "material_id": p.material_id, "grain": float(p.grain),
                              "V2": np.asarray(fm.V2), "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris),
                              "edges": edges, "seam_area_mm2": float(p.area_mm2) if not callable(p.area_mm2) else float(p.area_mm2())}
    b05 = body["b05"]
    z0 = float(P.Z0)
    e05 = []
    for nm in b05.edge_names:
        fl = densify(np.asarray(b05.edge_points(nm), float), 2.0)
        e05.append((nm, fl, np.column_stack([-fl[:, 0], fl[:, 1], np.full(len(fl), z0)])))
    out["pieces"]["B-05"] = {"kind": "floor", "name": b05.name, "material_id": b05.material_id,
                             "grain": float(b05.grain), "edges": e05, "z0": z0}
    b06 = body["b06"]
    perim = float(b06.edge_length("bottom"))
    t = np.linspace(0, 2, 4001)
    q = np.mod(1.5 + t, 2.0)
    ring = np.asarray(S(np.column_stack([q * P.US, np.full(len(q), P.Z_COLLAR)])))
    s3 = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    out["pieces"]["B-06"] = {"kind": "collar", "name": b06.name, "material_id": b06.material_id,
                             "grain": float(b06.grain), "perimeter": perim, "ring": ring, "ring_s": s3 * perim / s3[-1],
                             "height_to_fill": float(P.Z_FILL - P.Z_COLLAR), "z_collar": float(P.Z_COLLAR)}
    # master-surface sampler for strap paths
    qg = np.linspace(0, 2, 401)
    zg = np.linspace(P.Z0, P.Z_COLLAR, 120)
    QQ, ZZ = np.meshgrid(qg, zg, indexing="ij")
    grid = np.asarray(S(np.column_stack([QQ.ravel() * P.US, ZZ.ravel()]))).reshape(len(qg), len(zg), 3)
    import build_geometry as BG  # noqa: E402
    out["surface"] = {"q": qg, "z": zg, "xyz": grid}
    out["constants"] = {"Z0": z0, "Z_COLLAR": float(P.Z_COLLAR), "Z_FILL": float(P.Z_FILL), "Z_SB": float(P.Z_SB),
                        "Z_SH": float(P.Z_SH), "design_volume_L": float(BG.bag_volume_mm3(P.HF)) / 1e6,
                        "pattern_volume_L_release": 85.02, "strain_p99": {k: v["p99_pct"] for k, v in ps.strain.items()}}
    f.write_bytes(pickle.dumps(out))
    return out


def surface_point(pat, q, z):
    """Bilinear lookup on the cached master-surface grid (q in [0, 2) wraps)."""
    s = pat["surface"]
    qg, zg, G = s["q"], s["z"], s["xyz"]
    q = np.mod(q, 2.0)
    i = np.clip(np.searchsorted(qg, q) - 1, 0, len(qg) - 2)
    j = np.clip(np.searchsorted(zg, z) - 1, 0, len(zg) - 2)
    u = (q - qg[i]) / (qg[i + 1] - qg[i])
    v = (z - zg[j]) / (zg[j + 1] - zg[j])
    u, v = np.asarray(u)[..., None], np.asarray(v)[..., None]
    return ((1 - u) * (1 - v) * G[i, j] + u * (1 - v) * G[i + 1, j] + (1 - u) * v * G[i, j + 1]
            + u * v * G[i + 1, j + 1])


# ============================================================================ pieces -> specs
def _tri_map(V2, V3, tris, k=16):
    """flat -> 3D by barycentric interpolation on the pattern's own fine flat mesh (V2 -> V3).
    Point location: the k triangles with the nearest centroids; best barycentric fit wins
    (tolerant of the few slivers a least-squares flattening leaves)."""
    cen = V2[tris].mean(1)
    tree = cKDTree(cen)
    A, B, C = V2[tris[:, 0]], V2[tris[:, 1]], V2[tris[:, 2]]
    den = (B[:, 1] - C[:, 1]) * (A[:, 0] - C[:, 0]) + (C[:, 0] - B[:, 0]) * (A[:, 1] - C[:, 1])
    den = np.where(np.abs(den) < 1e-12, 1e-12, den)

    def m(xy):
        xy = np.asarray(xy, float)
        _, cand = tree.query(xy, k=min(k, len(tris)))
        Pq = xy[:, None, :]
        Bc, Cc, Ac = B[cand], C[cand], A[cand]
        l1 = ((Bc[..., 1] - Cc[..., 1]) * (Pq[..., 0] - Cc[..., 0]) + (Cc[..., 0] - Bc[..., 0]) * (Pq[..., 1] - Cc[..., 1])) / den[cand]
        l2 = ((Cc[..., 1] - Ac[..., 1]) * (Pq[..., 0] - Cc[..., 0]) + (Ac[..., 0] - Cc[..., 0]) * (Pq[..., 1] - Cc[..., 1])) / den[cand]
        l3 = 1 - l1 - l2
        score = np.minimum(np.minimum(l1, l2), l3)
        j = np.argmax(score, axis=1)
        r = np.arange(len(xy))
        t = cand[r, j]
        L = np.clip(np.stack([l1[r, j], l2[r, j], l3[r, j]], 1), 0, None)
        L /= L.sum(1, keepdims=True)
        tri = tris[t]
        return L[:, :1] * V3[tri[:, 0]] + L[:, 1:2] * V3[tri[:, 1]] + L[:, 2:] * V3[tri[:, 2]]
    return m


def _rest_map(adj: dict, grain_deg: float, centre):
    """Panel adjustment: scale the flat piece along the warp / weft about its centre."""
    sw, sf = float(adj.get("scale_warp", 1.0)), float(adj.get("scale_weft", 1.0))
    if sw == 1.0 and sf == 1.0:
        return None
    th = math.radians(grain_deg)
    R = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])
    M = R.T @ np.diag([sw, sf]) @ R
    c = np.asarray(centre, float)
    return lambda xy: c + (np.asarray(xy) - c) @ M.T


def piece_specs(pat: dict, scen: dict) -> list[PieceSpec]:
    adj_all = scen.get("panels") or {}
    fov = scen.get("fabric_overrides") or {}

    def fab_for(mid, adj):
        mid = adj.get("material", mid)
        f = fabric(mid)
        kw = dict(fov.get(mid, {}))
        kw.update({k: v for k, v in adj.items() if k.endswith("_scale") or k in ("compression",)})
        return f.scaled(**kw) if kw else f

    specs = []
    for pid in pat.get("dev_ids", DEV_IDS):
        d = pat["pieces"][pid]
        m3 = _tri_map(d["V2"], d["V3"], d["tris"])
        sides = [("R", False), ("L", True)] if pid == "B-03" else [("", False)]
        for suf, mir in sides:
            name = pid + suf
            adj = {**adj_all.get(pid, {}), **adj_all.get(name, {})}
            if mir:
                edges = [(nm, fl * [-1, 1], x3 * [-1, 1, 1]) for nm, fl, x3 in d["edges"]]
                mm = (lambda f_: (lambda xy: f_(np.asarray(xy) * [-1, 1]) * [-1, 1, 1]))(m3)
                grain = 180.0 - d["grain"]
            else:
                edges, mm, grain = d["edges"], m3, d["grain"]
            cen = np.vstack([e[1] for e in edges]).mean(0)
            specs.append(PieceSpec(name, edges, mm, fab_for(d["material_id"], adj), grain,
                                   rest_map=_rest_map(adj, grain, cen), meta={"material_id": adj.get("material", d["material_id"]),
                                                                              "label": d["name"]}))
    d = pat["pieces"]["B-05"]
    z0 = d["z0"]
    adj = adj_all.get("B-05", {})
    cen = np.vstack([e[1] for e in d["edges"]]).mean(0)
    specs.append(PieceSpec("B-05", d["edges"], lambda xy: np.column_stack([-xy[:, 0], xy[:, 1], np.full(len(xy), z0)]),
                           fab_for(d["material_id"], adj), d["grain"], rest_map=_rest_map(adj, d["grain"], cen),
                           meta={"material_id": adj.get("material", d["material_id"]), "label": d["name"]}))
    specs.append(collar_spec(pat, adj_all.get("B-06", {}), fab_for))
    return specs


def collar_spec(pat, adj, fab_for) -> PieceSpec:
    """B-06 up to the fill line; the top edge is closed flat (front half on back half, ends at the
    sides) as the roll-top is when rolled: point s on the top edge meets point P/2 - s."""
    d = pat["pieces"]["B-06"]
    P, H = d["perimeter"], d["height_to_fill"]
    ring, rs, zc = d["ring"], d["ring_s"], d["z_collar"]

    def R(s):
        s = np.mod(s, P)
        return np.column_stack([np.interp(s, rs, ring[:, k]) for k in range(3)])
    yc = 0.5 * (ring[:, 1].max() + ring[:, 1].min())

    def m3(xy):
        xy = np.asarray(xy, float)
        s, y = np.mod(xy[:, 0], P), xy[:, 1]
        w = np.clip(y / H, 0, 1) ** 1.5
        front = (s >= P / 4) & (s <= 3 * P / 4)
        sf = np.where(front, s, np.mod(P / 2 - s, P))          # front member of the closure pair
        sig = -(sf - P / 2) / (P / 4) * (P / 4)                 # along the closure line, mm
        sgn = np.sign(R(np.array([P / 4]))[0, 0])
        top = np.column_stack([sgn * sig, np.full(len(s), yc), np.zeros(len(s))])
        base = R(s)
        out = (1 - w)[:, None] * base + w[:, None] * top
        out[:, 2] = zc + y
        return out

    def edge(a, b):
        fl = densify(np.array([a, b], float), 2.0)
        return fl, m3(fl)
    E = []
    # top split at the closure points so both halves get the same nodes (s <-> P/2 - s)
    for nm, a, b in (("bottom", (0, 0), (P, 0)), ("right", (P, 0), (P, H)),
                     ("top_a", (P, H), (0.75 * P, H)), ("top_b", (0.75 * P, H), (0.5 * P, H)),
                     ("top_c", (0.5 * P, H), (0.25 * P, H)), ("top_d", (0.25 * P, H), (0, H)),
                     ("left", (0, H), (0, 0))):
        fl, x3 = edge(a, b)
        E.append((nm, fl, x3))
    cen = np.array([P / 2, H / 2])
    return PieceSpec("B-06", E, m3, fab_for(d["material_id"], adj), d["grain"],
                     rest_map=_rest_map(adj, d["grain"], cen),
                     meta={"material_id": adj.get("material", d["material_id"]), "label": d["name"] + " (to fill line)",
                           "closure": "top edge s <-> P/2 - s"})


# ============================================================================ frame clouds
def frame_clouds(spacing=4.0) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"frame_cloud_{spacing:.1f}.npz"
    if f.exists():
        z = np.load(f)
        return {k: z[k] for k in z.files}
    import trimesh
    out = {}
    for key, path in (("frame", FRAME_STL), ("spreader", SPREADER_STL)):
        m = trimesh.load(path, force="mesh")
        n = int(m.area / spacing ** 2)
        pts, fi = trimesh.sample.sample_surface_even(m, n, seed=1)
        out[key + "_p"] = np.asarray(pts)
        out[key + "_n"] = np.asarray(m.face_normals[fi])
        # decimated display mesh
        tgt = max(2000, len(m.faces) // 20)
        try:
            dm = m.simplify_quadric_decimation(face_count=tgt)
        except Exception:  # noqa: BLE001
            dm = m
        out[key + "_V"] = np.asarray(dm.vertices)
        out[key + "_F"] = np.asarray(dm.faces)
    np.savez_compressed(f, **out)
    return out


def gap_fields(cl: dict, cs: dict) -> dict:
    """One-sided smooth gap fields: only the bag-facing surfaces push (the bag lives on the +y side
    of the frame face): spreader samples with n_y > 0.5 (its front skin), frame samples with
    n_y > -0.3 (anything not facing the wearer). Cached."""
    key = f"{cs.get('spacing', 4.0):.1f}_{cs.get('grid_mm', 2.0):.1f}_{cs.get('spreader_ny_min', 0.5)}_{cs.get('frame_ny_min', -0.3)}"
    f = CACHE / f"gap_fields_v2_{key}.npz"
    if f.exists():
        z = np.load(f)
        return {k: GapField(z[k + "_o"], float(z[k + "_h"]), z[k + "_v"]) for k in ("spreader", "frame")}
    out, save = {}, {}
    for k, ny in (("spreader", cs.get("spreader_ny_min", 0.5)), ("frame", cs.get("frame_ny_min", -0.3))):
        sel = cl[k + "_n"][:, 1] > ny
        gf = GapField.from_samples(cl[k + "_p"][sel], cl[k + "_n"][sel], spacing=float(cs.get("grid_mm", 2.0)))
        out[k] = gf
        save.update({k + "_o": gf.o, k + "_h": gf.h, k + "_v": gf.v.astype(np.float32)})
    np.savez_compressed(f, **save)
    return out


def crown_field(cc: dict, cs: dict) -> GapField:
    """Optional contact with the carbon crown, which is not in genframe_assembled.stl (the print ends at z 540):
    two legs (OD from ``leg_od``) on the frame axis from the stay tops, the top bar (``bar_od``) ``bar_aft_mm`` aft of
    the leg axis at ``top_z``, and the centre spine tube (``spine_od``) from the top bar down ``spine_len``.
    Dimensions: frame.yaml parts + geometry.yaml crown / crown_settings. Sampled as point clouds with outward
    normals; only faces not pointing at the wearer push (same rule as the frame field)."""
    key = "_".join(f"{cc.get(k)}" for k in ("top_z", "leg_od", "bar_od", "spine_od", "spine_len", "bar_aft_mm", "spine_y_mm"))
    f = CACHE / f"crown_field_{hashlib.sha1(key.encode()).hexdigest()[:10]}.npz"
    if f.exists():
        z = np.load(f)
        return GapField(z["o"], float(z["h"]), z["v"])
    ax = np.array([0.0, -0.0189, 0.9998])
    ax /= np.linalg.norm(ax)
    zt = float(cc["top_z"])
    sp = float(cs.get("spacing", 4.0))
    pts, nrm = [], []

    def cyl(a, b, r):
        a, b = np.asarray(a, float), np.asarray(b, float)
        L = np.linalg.norm(b - a)
        t = (b - a) / L
        u = np.cross(t, [1.0, 0, 0] if abs(t[0]) < 0.9 else [0, 1.0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(t, u)
        for s_ in np.arange(0, L + 1e-9, sp):
            for th in np.linspace(0, 2 * np.pi, max(8, int(2 * np.pi * r / sp)), endpoint=False):
                n = np.cos(th) * u + np.sin(th) * v
                pts.append(a + s_ * t + r * n)
                nrm.append(n)
    for sx in (1, -1):
        a = np.array([sx * 115.0, -10.0, 530.0])
        b = a + ax * (zt - 530.0) / ax[2]
        cyl(a, b, float(cc.get("leg_od", 22.0)) / 2)
    yb = -10.0 + (zt - 530.0) * ax[1] / ax[2] + float(cc.get("bar_aft_mm", 25.0))
    cyl([-115.0, yb, zt], [115.0, yb, zt], float(cc.get("bar_od", 18.0)) / 2)
    ys = float(cc.get("spine_y_mm", yb - 25.0))
    cyl([0.0, ys, zt], [0.0, ys, zt - float(cc.get("spine_len", 300.0))], float(cc.get("spine_od", 20.0)) / 2)
    P, N = np.asarray(pts), np.asarray(nrm)
    sel = N[:, 1] > float(cs.get("frame_ny_min", -0.3))
    gf = GapField.from_samples(P[sel], N[sel], spacing=float(cs.get("grid_mm", 2.0)))
    np.savez_compressed(f, o=gf.o, h=gf.h, v=gf.v.astype(np.float32))
    return gf


# ============================================================================ the model
def load_scenario(path=None, overrides=None) -> dict:
    scen = yaml.safe_load(Path(path or SCENARIO).read_text())
    base = scen.pop("extends", None)
    if base:
        b = load_scenario((Path(path).parent / base) if path else None)
        scen = _merge(b, scen)
    if overrides:
        scen = _merge(scen, overrides)
    return scen


def _merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class PackModel:
    """Sewn bag mesh + frame + attachments, ready for load cases."""

    def __init__(self, scen: dict, fine=False, verbose=True):
        self.scen = scen
        self.verbose = verbose
        ms = scen["mesh"]
        self.h = float(ms["fine_h"] if fine else ms["h"])
        bag = scen.get("bag", "spine")
        if bag == "spine":
            self.pat = load_patterns(verbose)
        elif bag == "corrie":       # concept body (designs/pack_5200/concepts/corrie.py), 2026-11-08
            from .corrie_bag import load_corrie_patterns
            self.pat = load_corrie_patterns(verbose)
        else:
            raise KeyError(f"unknown bag {bag!r}")
        self.c = self.pat["constants"]
        specs = piece_specs(self.pat, scen)
        ref = np.array([0.0, 150.0, 450.0])
        self.mesh, self.diag = assemble(specs, self.h, tol=float(ms.get("tol", 1.5)), outward_ref=ref)
        self.seams = self.diag["seams"]
        m = self.mesh
        self.piece_of_tri = np.array([m.pieces[i].name for i in m.tri_piece])
        self.node_pieces = {}
        for p in m.pieces:
            for g in np.unique(p.gid):
                self.node_pieces.setdefault(int(g), set()).add(p.name)
        self.clouds = frame_clouds(float(scen["contact"].get("spacing", 4.0)))
        self.fields = gap_fields(self.clouds, scen["contact"])
        if (scen["contact"].get("crown") or {}).get("enabled"):
            self.fields["crown"] = crown_field(scen["contact"]["crown"], scen["contact"])
        self._attachments()

    # ---- nodes helpers
    def nodes_of(self, *names):
        idx = set()
        for p in self.mesh.pieces:
            if p.name in names:
                idx.update(np.unique(p.gid).tolist())
        return np.array(sorted(idx))

    def nearest(self, pt, names=None):
        idx = self.nodes_of(*names) if names else np.arange(self.mesh.n)
        d = np.linalg.norm(self.mesh.X0[idx] - np.asarray(pt), axis=1)
        return int(idx[np.argmin(d)])

    def _attachments(self):
        sc = self.scen["attachments"]
        X = self.mesh.X0
        self.cables = {}
        geo = yaml.safe_load((PACK / "geometry.yaml").read_text())
        hp = _find_hardpoints(geo)

        def add(name, nodes, fixed, wid, pre, kind, mode="elastic", **meta):
            w = webbing(wid)
            cb = Cable(name, np.asarray(nodes), np.asarray(fixed, float), w["EA_n"], 1.0, kind, wid, meta)
            L = cb.length(X)
            cb.L0 = L / (1.0 + pre / w["EA_n"])
            cb.meta.update(L_init=L, pretension_n=pre, mode=mode, break_n=w["break_n"])
            if mode == "cinched":
                # hand-cinched strap: pretension at the drafted shape, soft "cinch compliance" (webbing
                # stretch + buckle/channel take-up) so a few mm of path change does not drop it slack
                eps = float(sc.get("cinch_strain", 0.03))
                cb.EA = min(w["EA_n"], pre / eps) if pre > 0 else w["EA_n"]
                cb.L0 = L / (1.0 + pre / cb.EA)
                cb.meta["EA_eff_n"] = cb.EA
            self.cables[name] = cb
        nan3 = [np.nan] * 3
        # hinge eyes at the floor / frame-panel seam, pinned at z 60 (bag_anchor_low)
        # optional hinge-eye doubler (``hinge.doubler_mm`` > 0): the eye is bartacked through a doubler sewn along
        # the B-01 | B-05 seam, so the pin holds every seam node within doubler_mm / 2 of the eye (stiffness split
        # equally), not one node. Default 0 = one node (phase-1 baseline).
        h = sc["hinge"]
        self.hinge_nodes, self.hinge_groups = [], {}
        seam_nodes = np.intersect1d(self.nodes_of("B-05"), self.nodes_of("B-01"))
        dbl = float(h.get("doubler_mm", 0.0) or 0.0)
        for side, sx in (("R", 1), ("L", -1)):
            pin = hp[f"bag_anchor_low_{side}"]
            dx = np.abs(X[seam_nodes, 0] - sx * abs(pin[0]))
            k = int(seam_nodes[np.argmin(dx)])
            add(f"hinge_{side}", [k, -1], [nan3, pin], h["webbing"], h.get("pretension_n", 0.0), "hinge",
                capacity_n=h.get("capacity_n"))
            self.hinge_groups[f"hinge_{side}"] = [len(self.hinge_nodes)]
            self.hinge_nodes.append(k)
            if dbl > 0:
                # the doubler is a stiff patch on the bag: tension legs from each seam node it covers into the eye
                # node. Only the eye node is pinned, so the bag still rotates freely about the pin (bulk mode)
                for j in seam_nodes[(dx <= 0.5 * dbl + 1e-6)].astype(int).tolist():
                    if j != k:
                        add(f"doubler_{side}.{j}", [j, k], [nan3, nan3], h.get("doubler_webbing", "poly_webbing_38mm"),
                            0.0, "doubler", group=f"doubler_{side}")
        self.hinge_doubler_mm = dbl
        # bag hooks at IM2 / IM3: hook strap bartacked on B-01 70 mm below the eye
        # optional bag-side hook tab (``hooks.tab: {stations, width_mm}``): the hook strap is bartacked to a tab sewn
        # across width_mm of B-01, modelled as a bridle of legs from every B-01 node on that line to the eye (one
        # elastic leg each, pretension split); reported as one attachment (sum) plus its legs
        hk = sc["hooks"]
        tab = hk.get("tab") or {}
        for st in hk["stations"]:
            for side, sx in (("R", 1), ("L", -1)):
                eye = hp[f"meat_anchor_z{int(st)}_{side}"]
                tgt = [sx * abs(eye[0]), 0.0, st - hk["bartack_below_mm"]]
                cand = self.nodes_of("B-01", "B-01b", "B-01u")
                d = np.hypot(X[cand, 0] - tgt[0], X[cand, 2] - tgt[2])
                k = int(cand[np.argmin(d)])
                name = f"hook_im{int(st)}_{side}"
                if tab and float(st) in [float(v) for v in tab.get("stations", [])]:
                    legs = self._line_nodes(cand, tgt[0], X[k, 2], float(tab["width_mm"]), k)
                    for i, kk in enumerate(legs):
                        add(f"{name}.{i + 1}", [kk, -1], [nan3, eye], hk["webbing"],
                            hk.get("pretension_n", 0.0) / len(legs), "hook", capacity_n=hk.get("capacity_n"),
                            group=name, tab_width_mm=float(tab["width_mm"]))
                else:
                    add(name, [k, -1], [nan3, eye], hk["webbing"], hk.get("pretension_n", 0.0),
                        "hook", capacity_n=hk.get("capacity_n"))
        # under-straps: frame pin L -> floor channel -> cam on pin R
        us = sc["under_straps"]
        floor = self.nodes_of("B-05")
        yf = X[floor, 1]
        for i, (zst, frac) in enumerate(zip(us["z"], us["channel_depth_frac"])):
            ych = yf.min() + frac * (yf.max() - yf.min())
            band = floor[np.abs(X[floor, 1] - ych) < 0.6 * self.h]
            band = band[np.argsort(X[band, 0])]
            yy = np.interp(zst, [60, 190], [hp["bag_anchor_low_R"][1], hp["meat_anchor_z190_R"][1]])
            aL, aR = [-abs(hp["bag_anchor_low_R"][0]), yy, zst], [abs(hp["bag_anchor_low_R"][0]), yy, zst]
            nodes = [-1] + band.tolist() + [-1]
            fixed = [aL] + [nan3] * len(band) + [aR]
            add(f"under_strap_US{i + 1}", nodes, fixed, us["webbing"], us["pretension_n"], "under_strap",
                mode=us.get("mode", "cinched"), capacity_n=us.get("capacity_n"))
        # haul wraps W1-W3 (carry-mode compression), around the outside
        wr = sc["wraps"]
        for w in wr["list"]:
            pR, pL = np.asarray(w["anchor_R"], float), np.asarray(w["anchor_L"], float)
            qs = np.linspace(1.88, 3.12, 60)
            zs = np.interp(qs, [1.88, 3.12], [pR[2], pL[2]])
            P = surface_point(self.pat, qs, zs)
            tr = cKDTree(X)
            _, j = tr.query(P)
            seq = []
            for k in j:
                if not seq or seq[-1] != k:
                    seq.append(int(k))
            nodes = [-1] + seq + [-1]
            fixed = [pR] + [nan3] * len(seq) + [pL]
            add(w["id"], nodes, fixed, wr["webbing"], wr["pretension_n"], "wrap", mode=wr.get("mode", "cinched"),
                capacity_n=wr.get("capacity_n"))
        # bag-top ties (``attachments.ties``, added 2026-11-05 for the crown tie / top guys): a strap from a bag point
        # (nearest node of ``pieces`` to ``at`` = [x, z], or a bridle across ``width_mm``) to a fixed frame anchor.
        # mode elastic = fixed-length (G-hook in a daisy loop, snug at the drafted shape); mode cinched = ladder lock,
        # re-cinched on the loaded bag like the wraps. ``via`` = optional list of [x, z] bag points the strap is
        # routed through (keepers; it slides freely there)
        tl = sc.get("ties") or {}
        for t in tl.get("list", []):
            cand = self.nodes_of(*t["pieces"])
            ax_, az_ = float(t["at"][0]), float(t["at"][1])
            d = np.hypot(X[cand, 0] - ax_, X[cand, 2] - az_)
            k = int(cand[np.argmin(d)])
            anchor = np.asarray(t["anchor"], float)
            via = []
            for v in t.get("via", []):
                cv = self.nodes_of(*v.get("pieces", t["pieces"]))
                dv = np.hypot(X[cv, 0] - float(v["at"][0]), X[cv, 2] - float(v["at"][1]))
                via.append(int(cv[np.argmin(dv)]))
            legs = self._line_nodes(cand, ax_, X[k, 2], float(t.get("width_mm", 0.0)), k)
            for i, kk in enumerate(legs):
                nm = t["id"] if len(legs) == 1 else f"{t['id']}.{i + 1}"
                nodes = [kk] + via[::-1] + [-1]
                fixed = [nan3] * (len(nodes) - 1) + [anchor]
                add(nm, nodes, fixed, t.get("webbing", tl.get("webbing", "poly_webbing_25mm")),
                    float(t.get("pretension_n", tl.get("pretension_n", 30.0))) / len(legs), "tie",
                    mode=t.get("mode", tl.get("mode", "elastic")), capacity_n=t.get("capacity_n", tl.get("capacity_n")),
                    **({"group": t["id"]} if len(legs) > 1 else {}), label=t.get("label", ""))
        # crown pocket (``attachments.pocket``, added 2026-11-05, attachment phase): an inverted Hypalon hood on the frame
        # face of B-01 that drops over the crown top bar. Every node of ``pieces`` in the band |z - bar_z| <= band_mm
        # and |x| <= half_width_mm gets a short tension-only leg to the bar's bag-facing surface at its own x
        # ([x, anchor_y, bar_z]); the legs are reported as one group ``pocket``. The hood holds B-01 against the bar
        # (no aft peel) and rests on it (no drop); it cannot pull the bag forward of the bar (crown contact does that).
        # ``hood_depth_mm``: free fabric between the bar face and B-01 when taut (rest length = max(drafted, depth)).
        pk = sc.get("pocket") or {}
        self.pocket_legs = []
        if pk.get("enabled"):
            cand = self.nodes_of(*pk.get("pieces", ["B-01u", "B-01b"]))
            zb = float(pk["bar_z"])
            band = float(pk.get("band_mm", 0.5 * self.h))
            hw_ = float(pk.get("half_width_mm", 90.0))
            sel = cand[(np.abs(X[cand, 2] - zb) <= band) & (np.abs(X[cand, 0]) <= hw_)]
            ay = float(pk["anchor_y"])
            depth = float(pk.get("hood_depth_mm", 0.0))
            pre = float(pk.get("pretension_n", 0.0)) / max(len(sel), 1)
            # ``slide: true`` (default): the hood rides on vertical rails on B-01, so it holds B-01 against aft peel only;
            # B-01 may slide past it in z (and x). Modelled with a leg reaching FAR forward (``slide_reach_mm``) whose
            # EA is scaled to keep the short leg's stiffness EA / max(drafted, depth): an aft move stretches it 1:1, a
            # z or x slide of d only by d^2 / (2 reach)
            slide = bool(pk.get("slide", True))
            reach = float(pk.get("slide_reach_mm", 2000.0)) if slide else 0.0
            for j in sel.astype(int).tolist():
                gap = max(float(X[j, 1]) - ay, 1.0)
                anchor = [float(X[j, 0]), ay - reach, zb if not slide else float(X[j, 2])]
                nm = f"pocket.{j}"
                add(nm, [j, -1], [nan3, anchor], pk.get("webbing", "poly_webbing_38mm"), pre, "pocket",
                    mode="elastic", capacity_n=pk.get("capacity_n"), group="pocket")
                cb = self.cables[nm]
                # slack hood: taut only once B-01 has moved aft to the depth; ``fixed_depth: true`` = the hood is a fixed
                # depth, so where the drafted gap is larger it pulls B-01 forward to it (negative slack)
                fixed = bool(pk.get("fixed_depth"))
                slack = (depth - gap) if fixed else max(depth - gap, 0.0)
                L_short = max(depth, 1.0) if fixed else max(gap, depth)
                k = cb.EA / L_short                     # hood stiffness (short leg)
                cb.L0 = cb.meta["L_init"] + slack - (pre / k if pre > 0 else 0.0)
                cb.EA = k * cb.L0
                cb.meta.update(hood_gap_mm=gap, hood_slack_mm=slack, slide=slide)
                self.pocket_legs.append(nm)
        # roll-top clips: the two ends of the closed roll pulled down onto the side gores
        rc = sc.get("roll_clips")
        if rc:
            top = self.nodes_of("B-06")
            zt = X[top, 2].max()
            ends = top[X[top, 2] > zt - 1.0]
            for side, sx in (("R", 1), ("L", -1)):
                e = int(ends[np.argmax(sx * X[ends, 0])])
                gore = self.nodes_of(f"B-03{side}")
                tgt = np.array([sx * 300.0, 120.0, self.c["Z_COLLAR"] - rc["below_collar_seam_mm"]])
                g = int(gore[np.argmin(np.linalg.norm(X[gore] - tgt, axis=1) + 1e3 * (np.abs(X[gore, 2] - tgt[2]) > 40))])
                add(f"roll_clip_{side}", [e, g], [nan3, nan3], rc["webbing"], rc["pretension_n"], "roll_clip",
                    mode="cinched", capacity_n=rc.get("capacity_n"))

    def _line_nodes(self, cand, x_c, z_c, width, k0):
        """Nodes of ``cand`` on a horizontal line of ``width`` (mm) centred on x_c at the height of node k0
        (within half an element); [k0] when width is 0."""
        if width <= 0:
            return [k0]
        X = self.mesh.X0
        s = cand[(np.abs(X[cand, 2] - z_c) <= 0.5 * self.h) & (np.abs(X[cand, 0] - x_c) <= 0.5 * width + 1e-6)]
        return sorted(set([k0] + s.astype(int).tolist()))

    # ---- one load case
    def build_sim(self, case: dict, cinched: bool = True) -> Sim:
        """Terms for one case. ``cinched=False`` leaves out the straps the owner cinches after
        loading (under-straps, wraps, roll clips): stage 1 of :func:`run_case`."""
        m = self.mesh
        terms = [Membrane(m), Bending(m), Gravity(m.mass)]
        cs = self.scen["contact"]
        terms.append(FieldContact(self.fields["spreader"], kc=cs["kc"], clearance=cs["clearance"],
                                  label="contact_spreader"))
        terms.append(FieldContact(self.fields["frame"], kc=cs["kc"], clearance=cs["clearance"],
                                  label="contact_frame"))
        if "crown" in self.fields:
            terms.append(FieldContact(self.fields["crown"], kc=cs["kc"], clearance=cs["clearance"],
                                      label="contact_crown"))
        # hinge eyes on the z 60 pins: the eye on the pin holds the floor corner in place (stiff pin,
        # ASSUMPTION k from scenario); reported as the hinge force
        hk = float(self.scen["attachments"]["hinge"].get("pin_stiffness_n_mm", 200.0))
        hn = np.array(self.hinge_nodes)
        terms.append(Pins(hn, m.X0[hn], k=hk))
        terms[-1].name = "hinge_pins"
        use = []
        for c in self.cables.values():
            if c.kind == "hinge":
                continue
            if c.kind in ("hook", "doubler") or (c.kind in ("tie", "pocket") and case.get("ties", True)):
                use.append(c)
            elif cinched and ((c.kind == "under_strap" and case.get("under_straps", True))
                              or (c.kind == "wrap" and case.get("wraps", False))
                              or (c.kind == "roll_clip" and case.get("roll_clips", self.scen["attachments"].get("roll_clips_enabled", False)))):
                use.append(c)
        terms.append(Cables(use))
        p0 = float(case.get("p0_kpa", 0.0)) * 1e-3
        fill = float(case.get("fill_kg", 0.0))
        model = case.get("fill_model", "janssen")
        Vc = case.get("contents_L")
        n = float(self.scen.get("contents", {}).get("polytropic_n", 3.0))
        terms.append(GasFill(m.tris, p0, None if Vc is None else float(Vc) * 1e6, n))
        self.fill_info = {"model": model, "fill_kg": fill, "p_pack_kpa": p0 * 1e3,
                          "contents_L": Vc, "polytropic_n": n if Vc is not None else None}
        if fill > 0 and model == "janssen":
            terms += self.janssen(case, fill, 0.0)
        elif fill > 0:
            vref = float(case.get("fill_volume_L", self.c["design_volume_L"]))
            rho = fill / vref
            terms.append(Pressure(m.tris, p0=0.0, rho_g=rho * 9.81e-6, z_ref=float(case.get("z_ref", self.c["Z_FILL"]))))
        if case.get("meat_kg"):
            terms += self.meat_loads(case)
        return Sim(m, terms)

    def janssen(self, case, fill_kg, p0) -> list:
        """Granular gear fill (Janssen 1895, arXiv cond-mat/0511618): vertical stress
        p_v(d) = rho g lam (1 - exp(-d / lam)), lam = D_h / (4 mu K), lateral p_h = K p_v.
        p_h(z) acts on the closed bag (its net vertical is part of the weight). The rest of the weight
        sits on the floor (ASSUMPTION: the gear column is carried by the floor; a share
        ``wall_friction_share`` can be moved into the walls below ``friction_below_z`` as friction).
        Total vertical = m g exactly."""
        m = self.mesh
        X = m.X0
        jp = self.scen["janssen"]
        mu, K = float(jp["mu_wall"]), float(jp["K"])
        V = float(case.get("fill_volume_L", self.c["design_volume_L"]))
        rho = fill_kg / V * 1e-6                     # kg/mm^3
        rg = rho * 9.81                              # N/mm^3
        zm = 0.5 * (self.c["Z0"] + self.c["Z_COLLAR"])
        qs = np.linspace(0, 2, 401)
        R = surface_point(self.pat, qs, np.full(len(qs), zm))
        A = 0.5 * abs(np.dot(R[:-1, 0], R[1:, 1]) - np.dot(R[:-1, 1], R[1:, 0]))
        Pm = np.linalg.norm(np.diff(R, axis=0), axis=1).sum()
        Dh = 4 * A / Pm
        lam = Dh / (4 * mu * K)
        zt = float(case.get("z_ref", self.c["Z_FILL"]))

        def pv(z):
            d = np.maximum(zt - np.asarray(z, float), 0.0)
            return rg * lam * (1 - np.exp(-d / lam))

        def ph(z):
            return p0 + K * pv(z)

        def Fz(z):
            z = np.asarray(z, float)
            d = np.maximum(zt - z, 0.0)
            return p0 * z - K * rg * lam * (d + lam * np.exp(-d / lam))
        pres = PressureProfile(m.tris, ph, Fz)
        pres.name = "pressure_janssen"
        # net vertical of the pressure field on the closed bag (downward, like buoyancy)
        _, gp, _ = pres(X, False)
        F_ph = float(gp[:, 2].sum())                  # = -(sum of nodal z forces) > 0 means downward
        W = fill_kg * 9.81
        floor = self.nodes_of("B-05")
        af = _vertex_area(m, floor)
        zf = float(X[floor, 2].mean())
        wall_frac = float(jp.get("wall_friction_share", 0.0))
        F_fric = wall_frac * max(W - F_ph, 0.0)
        F_floor = max(W - F_ph - F_fric, 0.0)
        Ffl = np.zeros((len(floor), 3))
        Ffl[:, 2] = -F_floor * af / af.sum()
        walls = np.setdiff1d(np.arange(m.n), floor)
        walls = walls[X[walls, 2] <= float(jp.get("friction_below_z", 520.0))]
        aw = _vertex_area(m, walls) * pv(X[walls, 2])
        Fw = np.zeros((len(walls), 3))
        Fw[:, 2] = -F_fric * aw / max(aw.sum(), 1e-9)
        self.fill_info.update({"D_h_mm": Dh, "lambda_mm": lam, "mu": mu, "K": K, "rho_kg_L": fill_kg / V,
                               "p_v_floor_kpa": float(pv(zf)) * 1e3, "p_h_floor_kpa": float(ph(zf)) * 1e3,
                               "W_n": W, "pressure_vertical_n": F_ph, "floor_n": F_floor, "wall_friction_n": F_fric})
        return [pres, DeadLoad(walls, Fw, label="fill_wall_friction"), DeadLoad(floor, Ffl, label="fill_floor")]

    def meat_loads(self, case) -> list:
        """HA-LS-1 rev B section 4.1 resolved onto the bag cloth (static carry, 1.0 g)."""
        m = self.mesh
        X = m.X0
        mk = float(case["meat_kg"])
        g = 9.81 * float(case.get("g", 1.0))
        P = mk * g
        mt = self.scen["meat"]
        # vertical share into the bag floor (70 %), on the frame half of the floor
        floor = self.nodes_of("B-05")
        ymid = 0.5 * (X[floor, 1].min() + X[floor, 1].max())
        fl = floor[X[floor, 1] < ymid]
        a = _vertex_area(m, fl)
        Ff = np.zeros((len(fl), 3))
        Ff[:, 2] = -mt["vertical_to_floor"] * P * a / a.sum()
        # face pressure on the frame panel over the spreader width, triangular z 60-330 (peak at bottom)
        z0, z1 = mt["face_z"]
        lev = np.array(mt["strap_z"]) - (z0 + (z1 - z0) / 3)
        H = P * mt["cg_aft_mm"] * lev / np.sum(lev ** 2)
        Fface = mt["cinch_per_anchor_n"] * 2 * len(mt["strap_z"]) + H.sum()
        fp = self.nodes_of("B-01")
        sel = fp[(np.abs(X[fp, 0]) <= mt["face_half_width_mm"]) & (X[fp, 2] >= z0) & (X[fp, 2] <= z1)]
        wgt = _vertex_area(m, sel) * (z1 - X[sel, 2]) / (z1 - z0)
        Fs = np.zeros((len(sel), 3))
        Fs[:, 1] = -Fface * wgt / wgt.sum()
        self.meat_info = {"P_n": P, "floor_n": float(-Ff[:, 2].sum()), "face_n": float(Fface),
                          "overturning_pull_n": H.round(1).tolist(), "to_strap_anchors_n": float((1 - mt["vertical_to_floor"]) * P),
                          "floor_nodes": len(fl), "face_nodes": len(sel)}
        return [DeadLoad(fl, Ff, label="meat_floor"), DeadLoad(sel, Fs, label="meat_face")]


def _vertex_area(m, idx):
    a, b, c = (m.X0[m.tris[:, j]] for j in range(3))
    ar = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    va = np.bincount(m.tris.ravel(), np.repeat(ar / 3, 3), minlength=m.n)
    return va[idx]


def _find_hardpoints(geo) -> dict:
    """geometry.yaml keeps the frame hardpoints in a nested block; find the dict holding them."""
    def walk(d):
        if isinstance(d, dict):
            if "bag_anchor_low_R" in d:
                return d
            for v in d.values():
                r = walk(v)
                if r is not None:
                    return r
        return None
    hp = walk(geo)
    if hp is None:
        raise KeyError("bag_anchor_low_R not found in geometry.yaml")
    return {k: [float(t) for t in v] for k, v in hp.items() if isinstance(v, list) and len(v) == 3}


LOADS = ("gas", "pressure", "pressure_janssen", "meat_floor", "meat_face", "fill_wall_friction", "fill_floor")


def run_case(pm: PackModel, case: dict, x0=None, verbose=False):
    """Solve one load case with a load ramp (contents pressure, fill and meat loads scaled up
    together). Hinge eyes and hook straps are fixed-length webbing (elastic, tension-only); the
    cammed / ladder-lock straps carry their cinch pretension at the drafted shape with a soft cinch
    compliance (``attachments.cinch_strain``)."""
    sv = pm.scen["solver"]
    x = pm.mesh.X0.copy() if x0 is None else x0.copy()
    infos = []
    t_left = float(sv.get("time_cap_s", 900))
    sim = pm.build_sim(case, cinched=True)
    for s in (sv.get("ramp", [1.0]) if x0 is None else [1.0]):
        for t in sim.terms:
            if t.name in LOADS:
                t.scale = s
        x, info = sim.solve(x, tol=float(sv["tol_n"]), max_iter=int(sv["max_iter"]), time_cap=max(t_left, 20.0),
                            verbose=False)
        t_left -= info.seconds
        info.reason = f"load x{s:g}: {info.reason}"
        infos.append(info)
        if verbose:
            print(f"   {info.reason} in {info.iterations} it, residual {info.residual_n:.3g} N, {info.seconds:.1f} s")
    # the owner cams / cinches the straps on the loaded bag: re-set each cinched strap so it carries
    # its pretension at the loaded shape, then re-equilibrate
    cins = [c for c in sim.term("cables").cables if c.meta.get("mode") == "cinched"]
    if cins and sv.get("recinch", True):
        for c in cins:
            c.L0 = c.length(x) / (1.0 + c.meta["pretension_n"] / c.EA)
        x, info = sim.solve(x, tol=float(sv["tol_n"]), max_iter=int(sv["max_iter"]), time_cap=max(t_left, 30.0))
        info.reason = f"re-cinched: {info.reason}"
        infos.append(info)
        if verbose:
            print(f"   {info.reason} in {info.iterations} it, residual {info.residual_n:.3g} N, {info.seconds:.1f} s")
    return x, sim, infos
