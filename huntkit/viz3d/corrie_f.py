"""BL-012: CORRIE F (shell S15 + 30 mm top setback, door D2) as a studio scene on the BL-020 cloth pass.

Nothing here is an engineering number: this module builds presentation geometry. The design comes from
``designs/pack_5200/concepts/corrie_f.py`` (BL-011) and the 2026-11-11 rows of ``docs/DECISIONS.md``:

* shell: CORRIE F's own fine huntkit drape (``corrie_f_sim.py fine --torso 19``) is the cloth-pass seed, through a
  ``cloth_pass.SHELL_PROVIDERS`` entry (key ``"CF"``); the BL-020 code is reused through its parameters;
* door D2: the aft face of the solved cloth is re-cut to D2's lines (``d2_recut``): camo blade U (both blades and
  the 75 mm kick strip), the door (whole aft face between the blades, z 110 to 650, R 55 corners), the hinge band;
* wings deleted, W1-W3 the only outside straps (BL-003, owner);
* no crown hood, no hood ladders; each top guy ends in a 25 mm loop round the crown top bar closed by a bright
  toggle (BL-004); no IM2 bag hooks; the IM3 bag hooks are wiregate carabiners (BL-010);
* the roll-clip tabs sit ``CLIP_BELOW_SEAM_MM`` below the collar seam (BL-020 call: lower, so the closed roll's ends
  do not stick out on part-full loads);
* the frame is the BL-027 H1 body (``designs/pack_5200/print/frame_h1/h1_assembled.stl``: H1-G0.55-B1/2.5 with the
  28 mm IM3 cheeks), copied to ``outputs/pack3d_h1_final`` under the name ``model.py`` reads.

BL-026 brings the picture to **rev 1** (section "rev 1" below): guys at x +/-52 on the B-25 bridle, the B-26 tripod
keeper cord, 25 mm meat and under-straps, the back-panel edge bound in body colour, the scope pod as a sewn part with
W1 over its wall, and the opened door as cloth lying over the top of the bag.

Renders: ``render(shots)`` groups the shots by scene and by wearer pose and runs each group through
``huntkit.viz3d.studio`` (``studio.render_scene``); the hunter is BL-019's ``wearer.studio_wearer`` at the 19 in
setting, and outdoor shots add ``wearer._outdoor`` (CC0 HDRI and grass) in place of the studio sweep.

    python -m huntkit.viz3d.corrie_f --shots hero,side --quality quick      # repo Python; needs HUNTKIT_BPY
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import cloth_pass as CP

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
SHELL = "CF"
TORSO = 19
H1_DIR = REPO / "outputs" / "pack3d_h1"
WORK = REPO / "outputs" / "corrie_f_viz"

# ASSUMPTION CLIP-1 (picture choice, proposed for the pattern release): the roll-clip tab sits 150 mm below the collar
# seam (CORRIE B.2: 60 mm). Settled by rolling the first prototype at the day and 6-day loads and marking where the
# roll ends land.
CLIP_BELOW_SEAM_MM = 150.0
# ASSUMPTION POUCH-1 (picture choice): the top pouch as a limp, part-full bag: rounded heap of goods (half height 26 mm) in
# a 60 mm box whose top seam slumps 75 % at the rim, the four strap points held. Settled by a photograph of the sewn pouch with 1 kg in it.
POUCH_SOFT = {"vertex_mass": 0.010, "bending": 0.12, "heap": 26.0, "round": 0.95, "pin": True, "pillow": 0.75,
              "relax": 16}
TOGGLE = {"d": 9.0, "L": 34.0}      # ASSUMPTION: POM toggle 9 x 34 mm (no record yet; BL-004 names the part only)
BINER = {"L": 58.0, "W": 36.0, "rod": 4.6, "gate": 1.9}   # ASSUMPTION: 22 g wiregate envelope (BL-010 names the rating)
NOT_A_PHOTO = "Rendered 3D figure, not a photograph"


def _mods():
    for p in (PACK / "concepts" / "corrie_f_sim", PACK / "concepts", PACK):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import bag_concepts as BC  # noqa: E402
    import corrie as CO  # noqa: E402
    import corrie_f as F  # noqa: E402
    import corrie_f_sim as CS  # noqa: E402
    return BC, CO, F, CS


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


# =================================================================================================== the shell
class Provider:
    """``cloth_pass`` shell provider for CORRIE F: its loader swap is ``corrie_f_sim.install`` (S15 + the top
    setback on its own frame face), its seed the fine drape of ``corrie_f_sim.py fine``."""

    viz_door = False        # True only while the fittings are built: corrie.DOOR reads as D2 for the viz builders

    def install(self, dome_h=None):
        BC, CO, F, CS = _mods()
        c = CS.install()
        self._dome = getattr(c, "dome_h", None)
        if dome_h is not None:
            c.dome_h = float(dome_h)
        self._c = c
        if self.viz_door:
            self._door = dict(CO.DOOR)
            zl = F.D2["z_lo"]
            CO.DOOR.update(z_lo=zl, z_hinge=F.D2["z_hinge"], r=F.D2["r"], inset=float(F.blade_w(c, zl)))

    def uninstall(self):
        BC, CO, F, CS = _mods()
        if getattr(self, "_door", None) is not None:
            CO.DOOR.clear()
            CO.DOOR.update(self._door)
            self._door = None
        CS.uninstall()

    def scenario(self, torso):
        return _mods()[3].scenario_path(torso)

    def skin_file(self, state, torso):
        return _mods()[3].OUT / f"F_PR{torso}_fine" / f"skin_{state}.pkl"

    def _model(self, torso, dome_h=None):
        from huntkit.clothsim.pack import PackModel, load_scenario
        door, self.viz_door = self.viz_door, False
        self.install(dome_h)
        try:
            pm = PackModel(load_scenario(str(self.scenario(torso))), fine=True, verbose=False)
        finally:
            self.uninstall()
            self.viz_door = door
        m = pm.mesh
        uv = np.zeros((m.n, 2))
        for p in m.pieces:
            uv[p.gid] = p.xy
        return {"X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}

    def ensure_full(self, torso):
        CS = _mods()[3]
        d = CS.run_dir("F", torso, "_fine")
        if not (d / "x_packed.npy").exists():
            os.environ.setdefault("OMP_NUM_THREADS", "2")
            CS.run("F", torso, "packed", fine=True, tag="_fine")
        sk = self._model(torso)
        sk["X"] = np.load(d / "x_packed.npy")
        assert len(sk["X"]) == len(sk["X0"]), "fine drape and fine mesh differ"
        self.skin_file("full", torso).write_bytes(pickle.dumps(sk))

    def ensure(self, torso=TORSO):
        """All three state meshes on disk (the part-full ones are mesh only), so later loads never rebuild them."""
        SS = CP._ss()
        if not self.skin_file("full", torso).exists():
            self.ensure_full(torso)
        for st in ("day", "sixday"):
            f = self.skin_file(st, torso)
            if not f.exists():
                f.write_bytes(pickle.dumps(self._model(torso, SS.RENDER_STATES[st]["dome_h"])))


PV = Provider()
CP.SHELL_PROVIDERS[SHELL] = PV


# ================================================================================================== door D2
def _snap(f, X, X0, uv, E, free):
    """Move the nearer end of every edge that crosses f = 0 onto the crossing (only ``free`` vertices move)."""
    a, b = E[:, 0], E[:, 1]
    cross = (f[a] * f[b] < 0)
    a, b = a[cross], b[cross]
    t = f[a] / (f[a] - f[b])                       # crossing at a + t (b - a)
    mv = np.where(t <= 0.5, a, b)
    ot = np.where(t <= 0.5, b, a)
    tt = np.where(t <= 0.5, t, 1 - t)
    ok = free[mv]
    mv, ot, tt = mv[ok], ot[ok], tt[ok]
    order = np.argsort(-tt)                        # the shortest move wins where a vertex has several
    mv, ot, tt = mv[order], ot[order], tt[order]
    for A in (X, X0, uv):
        d = (A[ot] - A[mv]) * tt[:, None]
        A[mv] = A[mv] + d
    f = f.copy()
    f[mv] = 0.0
    return f


def d2_fields(c, x, z):
    """Signed fields on the drafted aft face: ``g`` > 0 between the blades, ``d`` > 0 inside the D2 door."""
    BC, CO, F, CS = _mods()
    zl, zh, r = F.D2["z_lo"], F.D2["z_hinge"], F.D2["r"]
    zc = np.clip(z, BC.Z0, c.z_c)
    inner = np.asarray(c.a(zc), float) - np.asarray(F.blade_w(c, zc), float)
    g = inner - np.abs(x)
    xc = float(c.a([zl + r])[0] - F.blade_w(c, zl + r)) - r        # corner centre
    low = np.where(np.abs(x) <= xc, z - zl, r - np.hypot(np.abs(x) - xc, z - (zl + r)))
    low = np.where(z >= zl + r, 1e3, low)
    d = np.minimum(np.minimum(g, zh - z), low)
    return g, d


def d2_recut(sk: dict) -> dict:
    """Re-cut the aft face of a skin (cloth-pass or huntkit, any subdivision) to door D2. The sim carries CORRIE's
    piece layout for both doors (ASSUMPTION DOOR-SIM, corrie_f_sim.py); here mesh vertices beside D2's lines are
    moved onto them (at most half an edge) and the aft-face triangles renamed: B-02door (door), B-02h (hinge band),
    B-02u (camo blade U with the kick strip). Vertex count and order are unchanged."""
    BC, CO, F, CS = _mods()
    c = F.make()
    X, X0, uv = (np.array(sk[k], float) for k in ("X", "X0", "uv"))
    T = np.asarray(sk["tris"], int)
    piece = np.asarray(sk["piece"]).astype("<U10")
    aft = np.char.startswith(piece, "B-02")
    va = np.zeros(len(X), bool)
    va[np.unique(T[aft])] = True
    free = va.copy()
    free[np.unique(T[~aft])] = False               # vertices on the aft face's own boundary seams stay
    Ta = T[aft]
    E = np.unique(np.sort(np.vstack([Ta[:, [0, 1]], Ta[:, [1, 2]], Ta[:, [2, 0]]]), axis=1), axis=0)
    uv[free] = np.column_stack([X0[free, 0] + 1000.0, X0[free, 2]])     # one flat, true-scale map for the face
    for which in (0, 1):
        g, d = d2_fields(c, X0[:, 0], X0[:, 2])
        f = (g, d)[which]
        f = np.where(va, f, 1.0)
        _snap(f, X, X0, uv, E, free)
    g, d = d2_fields(c, X0[:, 0], X0[:, 2])
    gc, dc, zc = g[Ta].mean(1), d[Ta].mean(1), X0[Ta][:, :, 2].mean(1)
    new = np.where(dc > 1e-6, "B-02door", np.where((gc > 1e-6) & (zc > F.D2["z_hinge"]), "B-02h", "B-02u"))
    piece[aft] = new
    return {**sk, "X": X, "X0": X0, "uv": uv, "piece": piece}


# ================================================================================================= the scene
def viz_params() -> dict:
    from .params import load_params
    p = load_params(str(PACK / "spec.yaml"))
    d = h1_dir()
    if (d / "genframe_assembled.stl").exists():
        p["generative_frame_dir"] = str(d)
    return p


def frame_note() -> str:
    if H1_FINAL_STL.exists():
        return "H1 body H1-G0.55-B1/2.5 (print/frame_h1/h1_assembled.stl, BL-027), IM3 cheeks 28 mm"
    if (H1_DIR / "genframe_assembled.stl").exists():
        return "H1 body of 2026-11-10 (outputs/pack3d_h1): IM3 cheek 18 mm, not the adopted 28 mm"
    return "released generative frame (H1 mesh missing)"


def carabiner(c, long, nrm):
    """Wiregate carabiner: a D of round rod in the plane (long, side), wire gate on the open side."""
    from . import geom as G
    c, long, nrm = np.asarray(c, float), _unit(long), _unit(nrm)
    side = _unit(np.cross(nrm, long))
    r = BINER["rod"] / 2
    L, W = BINER["L"] / 2 - r - 0.8, BINER["W"] / 2 - r - 0.8        # path inside the envelope by the rod
    spine = [(W - 4, -L + 9), (-W + 7, -L), (-W, -L + 12), (-W, L - 12), (-W + 8, L), (W - 9, L), (W, L - 9)]
    P = np.array([c + side * x + long * y for x, y in spine])
    body = G.tube(G.catmull_rom(P, 8), r, n=10)
    gate = np.array([c + side * x + long * y for x, y in [(W - 1.5, L - 11), (W - 2.5, 0), (W - 5.5, -L + 10)]])
    g1 = G.tube(G.catmull_rom(gate + nrm * 2.2, 6), BINER["gate"] / 2, n=6)
    g2 = G.tube(G.catmull_rom(gate - nrm * 2.2, 6), BINER["gate"] / 2, n=6)
    return G.concat([body, g1, g2])


def _components(mesh):
    import trimesh
    tm = trimesh.Trimesh(np.asarray(mesh.vertices), np.asarray(mesh.faces), process=False)
    lab = trimesh.graph.connected_component_labels(tm.face_adjacency, node_count=len(tm.faces))
    return tm, lab


def _keep_faces(part, keep_fn):
    """Keep the connected components of a part's mesh for which keep_fn(centroid, lo, hi) is true."""
    from .assets import mesh as amesh
    tm, lab = _components(part.mesh)
    keep = np.zeros(len(tm.faces), bool)
    gone = []
    for k in np.unique(lab):
        fm = lab == k
        Q = tm.vertices[np.unique(tm.faces[fm])]
        if keep_fn(Q.mean(0), Q.min(0), Q.max(0)):
            keep[fm] = True
        else:
            gone.append((Q.mean(0), Q.min(0), Q.max(0)))
    md = dict(getattr(part.mesh, "metadata", {}) or {})
    part.mesh = amesh(tm.vertices, tm.faces[keep], md.get("uv"))
    for k in ("extras", "straps"):
        if k in md:
            part.mesh.metadata[k] = md[k]
    return gone


# ============================================================================================== rev 1 (BL-026)
# Picture geometry for the adopted design: CORRIE F rev 1 (BL-022) on the BL-027 H1 body. Design numbers are read
# from the concept (guy x, keeper height, webbing widths); what is declared here are picture choices.
STRAP_W = 25.0            # IM1-IM3 meat straps and US1 / US2 under-straps (BL-003; poly_webbing_25mm record)
# ASSUMPTION BIND-1 (picture choice): the back-panel edge binding shows 12 mm on each face. DECISIONS 2026-11-12 names
# the colour only. Settled by the binding tape picked for the back-panel pattern.
BIND_W = 12.0
# ASSUMPTION POD-1 (picture choice): the scope pod is a 405 mm sleeve with a flat sewn base (corner radius 18 mm), a
# bound mouth and a 90 mm No. 5 throat zip; its base hangs 75 mm lower than the BL-020 obstacle so that W1 crosses
# the sleeve wall, not the base. Settled by the IMP-1 pod pattern and a fit check with the owner's spotter.
POD = {"drop": 75.0, "corner": 18.0, "mouth_z": 520.0, "r_mouth": 44.0, "zip": 5, "zip_len": 90.0, "scope_top": 620.0}
# ASSUMPTION DOOR-OPEN-1 (picture choice): the opened door is thrown up over the top of the bag and lies on what is
# there (hinge band, collar, roll, top pouch), with 14 mm of slack bellying out of the rise. Settled by a photograph
# of the first sewn bag with the door open.
DOOR_CLOTH = {"clear": 5.0, "sag": 14.0, "col": 10.0, "win": 30.0, "ds": 5.0}
DOOR_LIES_ON = ("corrie_body", "s15_roll", "s15_pouch", "s15_W3", "corrie_b22", "cf_guy_", "corrie_zip_garages")
H1_FINAL_STL = PACK / "print" / "frame_h1" / "h1_assembled.stl"       # BL-027 body H1-G0.55-B1/2.5, 28 mm cheeks
H1_FINAL_DIR = REPO / "outputs" / "pack3d_h1_final"


def h1_dir() -> Path:
    """Folder that holds the frame body under the name ``model.py`` reads (``genframe_assembled.stl``): a copy of the
    tracked BL-027 print file when it exists, else the 2026-11-10 H1 folder."""
    if not H1_FINAL_STL.exists():
        return H1_DIR
    dst = H1_FINAL_DIR / "genframe_assembled.stl"
    st = H1_FINAL_STL.stat()
    if not dst.exists() or dst.stat().st_size != st.st_size or dst.stat().st_mtime < st.st_mtime:
        H1_FINAL_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(H1_FINAL_STL, dst)
    return H1_FINAL_DIR


def _part(sc, name):
    return next((x for x in sc.parts if x.name == name), None)


def _vis(part) -> dict:
    return dict(group=part.group, modes=tuple(part.modes), torso=part.torso, variant=part.variant)


def _surf(V, F):
    """``cloth_pass.Surf`` with its normals turned outward (away from the centroid)."""
    S = CP.Surf(V, F)
    if np.mean(np.einsum("ij,ij->i", S.n, S.V - S.V.mean(0))) < 0:
        S.n = -S.n
    return S


def restrap(sc, name, width=STRAP_W, surf=None, clear=3.0) -> list:
    """Redraw a legacy strap part at ``width`` along the paths it recorded (``mesh.metadata['straps']``); with
    ``surf`` the paths are first pushed ``clear`` mm clear of that surface. Returns the new strap records."""
    from .assets import concat as aconcat
    from .assets import webbing as WB
    part = _part(sc, name)
    recs = list((getattr(part.mesh, "metadata", None) or {}).get("straps", [])) if part is not None else []
    out, ms = [], []
    for r in recs:
        P, N = np.asarray(r["P"], float), np.asarray(r["N"], float)
        if surf is not None:
            P = surf.push_out(P, clear + WB.thickness(width) / 2)
        m = WB.strap(P, N, width)
        out.append(m.metadata["strap"])
        ms.append(m)
    if ms:
        part.mesh = aconcat(ms)
        part.mesh.metadata["straps"] = out
    return out


def _cam(sc, name, rec, frac, vis):
    """A 25 mm cam buckle on a strap record, at ``frac`` of its length."""
    P, N = np.asarray(rec["P"], float), np.asarray(rec["N"], float)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    i = int(np.clip(np.searchsorted(s, frac * s[-1]), 2, len(P) - 3))
    sc.add_hardware(name, "cam_buckle_25", P[i], N[i], _unit(P[i + 1] - P[i - 1]), **vis)


def straps_25(sc) -> dict:
    """BL-003: under-straps, cradle and meat straps at 25 mm (the legacy builders draw 38 mm)."""
    n = {}
    q = _part(sc, "quarter_proxy")
    qs = _surf(np.asarray(q.mesh.vertices), np.asarray(q.mesh.faces)) if q is not None else None
    for name, surf in (("under_straps", None), ("under_straps_slack", None), ("corrie_im_straps", None),
                       ("meat_straps", qs), ("cradle_straps", qs)):
        part = _part(sc, name)
        recs = restrap(sc, name, STRAP_W, surf)
        n[name] = len(recs)
        if not recs:
            continue
        part.label = (part.label or name).replace("38 mm", "25 mm")
        if name in ("under_straps", "meat_straps"):                 # their cams were blocks sized for 38 mm webbing
            for k, r in enumerate(recs):
                _cam(sc, f"cf_{name}_cam{k + 1}", r, 0.90 if name == "under_straps" else 0.25, _vis(part))
    mh = _part(sc, "meat_hardware")
    if mh is not None and n.get("meat_straps"):
        tm, lab = _components(mh.mesh)
        keep = np.ones(len(tm.faces), bool)
        for k in np.unique(lab):
            fm = lab == k
            sub = tm.submesh([np.where(fm)[0]], append=True, repair=False)
            if abs(float(sub.volume)) > 5000.0:                     # the 12 x 18 x 46 cam blocks; the hooks stay
                keep[fm] = False
        from .assets import mesh as amesh
        mh.mesh = amesh(tm.vertices, tm.faces[keep])
        mh.label = "MEAT sliding-gate hooks"
    return n


def _outboard_hull(cloud2, a, b, lift, toward):
    """Taut 2D line from a to b round the points of ``cloud2`` that lie on the same side of the line a-b as the
    point ``toward`` (each inflated by ``lift``). Returns the chain a .. b."""
    from scipy.spatial import ConvexHull
    a, b, cloud2 = np.asarray(a, float), np.asarray(b, float), np.asarray(cloud2, float).reshape(-1, 2)
    d = b - a

    def cross(Q):
        return d[0] * (Q[:, 1] - a[1]) - d[1] * (Q[:, 0] - a[0])
    sgn = np.sign(cross(np.asarray(toward, float)[None])[0])
    Q = cloud2[cross(cloud2) * sgn > 1e-6]
    if len(Q):
        ang = np.linspace(0, 2 * np.pi, 9)[:-1]
        Q = (Q[:, None, :] + lift * np.column_stack([np.cos(ang), np.sin(ang)])[None]).reshape(-1, 2)
        Q = Q[cross(Q) * sgn > 1e-6]
    if len(Q) < 1:
        return np.array([a, b])
    P = np.vstack([Q, a, b])
    H = list(ConvexHull(P).vertices)
    ia, ib = len(P) - 2, len(P) - 1
    if ia not in H or ib not in H:
        return np.array([a, b])
    i0 = H.index(ia)
    H = H[i0:] + H[:i0]
    fwd = H[:H.index(ib) + 1]
    back = [ia] + H[H.index(ib):][::-1]
    return P[fwd if len(fwd) >= len(back) else back]             # the chain that carries the cloud's points


def guys_rev1(sc, sk) -> dict:
    """BL-022 rev 1: the two top guys start at x +/-52 on the B-25 bridle (a 25 mm sleeve round the crown top bar each
    side, joined under the bar), each closed by a bright toggle, and run round the bag's top corner to B-22."""
    from . import geom as G
    from .assets import seams as SM
    BC, CO, F, CS = _mods()
    crown = _part(sc, f"crown@t{TORSO}")
    guys = _part(sc, f"corrie_top_guys@t{TORSO}")
    if crown is None or guys is None:
        return {}
    gx = float(F.REVS[1]["guy_x"])
    Vc = np.asarray(crown.mesh.vertices)
    ztop = Vc[:, 2].max()

    def bar(x):                                    # bar centre (y, z) and radius at x, from the crown mesh
        t = Vc[(Vc[:, 2] > ztop - 22.0) & (np.abs(Vc[:, 0] - x) < 6.0)]
        r = 0.5 * float(t[:, 1].max() - t[:, 1].min())
        return float(0.5 * (t[:, 1].min() + t[:, 1].max())), float(t[:, 2].max()) - r, r
    yb, zb, rb = bar(gx)
    recs = list(guys.mesh.metadata.get("straps", []))
    X = np.asarray(sk["X"], float)
    S = CP.Surf(X, sk["tris"])
    sleeves, tabs, togs, info = [], [], [], {"guy_x": gx, "bar": [yb, zb, rb]}
    a = np.linspace(0, 2 * np.pi, 40)
    for sx in (1, -1):
        x = sx * gx
        ring = np.column_stack([np.full(40, x), yb + (rb + 1.0) * np.cos(a), zb + (rb + 1.0) * np.sin(a)])
        nr = np.column_stack([np.zeros(40), np.cos(a), np.sin(a)])
        sleeves.append(G.ribbon(ring, F.GUY_W, 1.6, nr, step=3.0, caps=False))
        # the folded tab hangs down the wearer's side of the bar (shown bag off; with the bag on the toggle holds it)
        y0 = yb - rb - 1.9
        tp = np.array([[x, y0, zb], [x, y0 - 0.6, zb - rb - 0.5 * F.BRIDLE_TAB_MM], [x, y0 - 3.4, zb - rb - 0.5 * F.BRIDLE_TAB_MM],
                       [x, y0 - 2.6, zb + 2.0]])
        tabs.append(G.ribbon(G.catmull_rom(tp, 6), F.GUY_W, 1.4, np.tile([0.0, -1.0, 0.0], (len(G.catmull_rom(tp, 6)), 1)),
                             step=3.0))
        pt = np.array([x, yb - rb - 1.6 - TOGGLE["d"] / 2 - 1.5, zb])
        togs.append(G.capsule_between(pt - [TOGGLE["L"] / 2, 0, 0], pt + [TOGGLE["L"] / 2, 0, 0], TOGGLE["d"] / 2))
        # the guy: from its sleeve along the top of the bar to the crown corner, then round the bag's top corner to
        # the legacy B-22 end (a straight line from x 52 to B-22 would pass through the bag)
        rec = next((r for r in recs if np.asarray(r["P"])[0, 0] * sx > 0), None)
        if rec is None:
            continue
        B = np.asarray(rec["P"], float)[-1]
        zt = zb + rb + 3.2                                           # over the lifter wraps on the bar
        xe = sx * (float(np.abs(Vc[:, 0]).max()) + 1.0)
        A = np.array([xe, yb + 2.0, zt])
        cl = X[(np.abs(X[:, 2] - 0.5 * (A[2] + B[2])) < 16.0) & (X[:, 0] * sx > 0)][:, :2]
        ch = _outboard_hull(cl, A[:2], B[:2], 2.5, [sx * 600.0, 0.5 * (A[1] + B[1])])
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ch, axis=0), axis=1))]
        si = np.linspace(0, s[-1], max(int(s[-1] / 3.0), 8))
        Pw = np.column_stack([np.interp(si, s, ch[:, 0]), np.interp(si, s, ch[:, 1]), A[2] + (B[2] - A[2]) * si / s[-1]])
        Pw[3:] = S.push_out(Pw[3:], 2.2)
        nb = max(int(abs(xe - x) / 3.0), 4)
        Pb = np.column_stack([np.linspace(x, xe, nb, endpoint=False), np.full(nb, yb + 2.0), np.full(nb, zt)])
        P = SM.smooth_path(np.vstack([Pb, Pw]), 3.0, 4.0)
        t = _unit(np.gradient(P, axis=0))
        Nh = _unit(np.cross(t, [0.0, 0.0, 1.0]))
        cen = np.array([0.0, float(np.median(cl[:, 1])) if len(cl) else 150.0, 0.0])
        Nh *= np.sign(np.einsum("ij,ij->i", Nh, P - cen))[:, None]
        w = np.clip((np.abs(P[:, 0]) - abs(xe)) / 40.0, 0.0, 1.0)[:, None]      # flat on the bar, then on edge
        w = np.maximum(w, np.clip((P[:, 1:2] - (yb + 2.0)) / 40.0, 0.0, 1.0))
        N = _unit(_gauss_rows(w * Nh + (1 - w) * np.array([0.0, 0.0, 1.0]), 4.0))
        sc.add_strap(f"cf_guy_{'R' if sx > 0 else 'L'}@t{TORSO}", P, N, F.GUY_W, group="attach", torso=float(TORSO),
                     modes=("pack",), label="Top guy: B-25 bridle at x 52 -> B-22 (rev 1, BL-022)")
        info[f"len_{'R' if sx > 0 else 'L'}"] = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    # the bridle's run under the bar between the sleeves (it passes under the spine clamp)
    xs = np.linspace(-(gx - F.GUY_W / 2), gx - F.GUY_W / 2, 41)
    run = []
    for x in xs:
        t = Vc[(Vc[:, 2] > ztop - 34.0) & (np.abs(Vc[:, 0] - x) < 5.0)]
        run.append([x, yb, float(t[:, 2].min()) - 1.2])
    run = SM.smooth_path(np.array(run), 3.0, 5.0)
    sleeves.append(G.ribbon(run, F.GUY_W, 1.4, np.tile([0.0, 0.0, -1.0], (len(run), 1)), step=3.0))
    allm = ("pack", "pack_haul", "frame", "frame_haul")
    sc.parts = [x for x in sc.parts if x is not guys]
    sc.add_part(f"cf_guy_loops@t{TORSO}", G.concat(sleeves), "webbing", group="attach", torso=float(TORSO), modes=allm,
                label="B-25 guy bridle: 25 mm sleeves round the top bar at x +/-52, joined under the bar (rev 1)")
    sc.add_part(f"cf_bridle_tabs@t{TORSO}", G.concat(tabs), "webbing", group="attach", torso=float(TORSO),
                modes=("frame", "frame_haul"), label="B-25 bridle tabs (60 mm folded), hanging with the bag off")
    sc.add_part(f"cf_guy_toggles@t{TORSO}", G.concat(togs), "blaze", group="attach", torso=float(TORSO),
                modes=("pack",), label="Guy toggles through the bridle tabs, bright ('guys on' is a carry rule)")
    return info


def _gauss_rows(A, sigma):
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(np.asarray(A, float), sigma, axis=0, mode="nearest")


def keeper_cord(sc, sk, obstacles=()) -> dict:
    """B-26 tripod keeper (rev 1): one 3 mm shock cord across the right gusset at pattern height TRIPOD_KEEPER_Z,
    seam to seam, taut over the gusset and over whatever is carried there (``obstacles`` = (V, F) meshes)."""
    from .assets import seams as SM
    from .assets import tube as atube
    BC, CO, F, CS = _mods()
    X, X0, T = np.asarray(sk["X"], float), np.asarray(sk["X0"], float), np.asarray(sk["tris"], int)
    g = np.unique(T[np.asarray(sk["piece"]).astype(str) == "B-03R"])
    if not len(g):
        return {}
    edge = float(np.median(np.linalg.norm(X0[T[:, 0]] - X0[T[:, 1]], axis=1)))
    row = g[np.abs(X0[g, 2] - F.TRIPOD_KEEPER_Z) < 0.75 * edge]
    if len(row) < 4:
        return {}
    row = row[np.argsort(X0[row, 1])]
    E0, E1 = X[row[0]], X[row[-1]]
    L = float(np.linalg.norm(E1 - E0))
    e = (E1 - E0) / L
    o = _unit(np.array([1.0, 0.0, 0.0]) - e[0] * e)
    pts = [X[row]]
    for V, Fc in obstacles:
        sec = CP.section_pts(np.asarray(V, float), np.asarray(Fc, int), E0, np.cross(e, o))
        if len(sec):
            pts.append(sec)
    Pn = np.vstack(pts) - E0
    uv = np.column_stack([Pn @ e, Pn @ o])
    uv = uv[(uv[:, 0] > 0.0) & (uv[:, 0] < L) & (uv[:, 1] > -5.0)]
    r = 0.5 * 3.0
    ch = _outboard_hull(uv, np.array([0.0, 0.0]), np.array([L, 0.0]), r + 1.0, [0.5 * L, 100.0])
    P = E0 + ch[:, :1] * e + ch[:, 1:2] * o
    P = SM.smooth_path(P, 2.0, 3.0)
    sc.add_part("cf_keeper_B26", atube(P, r, n=8), "cord", group="bag", modes=("pack", "pack_haul"),
                label="B-26 tripod keeper: 3 mm shock cord across the right gusset, seam to seam (rev 1, BL-022)")
    s = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    return {"span_mm": L, "path_mm": s, "z": float(0.5 * (E0[2] + E1[2])), "stand_off_mm": float(ch[:, 1].max())}


def panel_binding(sc) -> dict:
    """DECISIONS 2026-11-12: the back-panel edge is bound in body colour (no pattern change). A band BIND_W wide on
    each face round the whole edge of the legacy ``back_panel`` mesh."""
    from scipy.spatial import ConvexHull, cKDTree
    from .assets import mesh as amesh
    from .assets import seams as SM
    bp = _part(sc, "back_panel")
    if bp is None:
        return {}
    V = np.asarray(bp.mesh.vertices, float)
    H = V[ConvexHull(V[:, [0, 2]]).vertices][:, [0, 2]]             # counter-clockwise outline in (x, z)
    k = len(H)
    en = []                                                          # inward normal of each edge
    for i in range(k):
        d = _unit(H[(i + 1) % k] - H[i])
        en.append([-d[1], d[0]])
    en = np.array(en)
    L, inw, si, acc = [], [], [], 0.0
    for i in range(k):
        n1, n2 = en[i - 1], en[i]
        L.append(H[i])
        inw.append((n1 + n2) / max(1.0 + float(n1 @ n2), 0.2))      # mitre: the band keeps its width round a corner
        si.append(acc)
        ln = float(np.linalg.norm(H[(i + 1) % k] - H[i]))
        # inner points of samples closer to a corner than the mitre reaches would cross it: leave them out
        sk0 = BIND_W * np.tan(0.5 * np.arccos(np.clip(float(n1 @ n2), -1.0, 1.0))) + 0.5
        sk1 = BIND_W * np.tan(0.5 * np.arccos(np.clip(float(n2 @ en[(i + 1) % k]), -1.0, 1.0))) + 0.5
        for u in np.arange(max(sk0, 4.0), ln - max(sk1, 2.0), 4.0):
            L.append(H[i] + (H[(i + 1) % k] - H[i]) * u / ln)
            inw.append(n2)
            si.append(acc + u)
        acc += ln
    L, inw, si, s = np.array(L), np.array(inw), np.array(si), np.array([0.0, acc])
    n = len(L)
    tree = cKDTree(V[:, [0, 2]])
    ylo, yhi = np.zeros(n), np.zeros(n)
    for i, p in enumerate(L):
        j = tree.query_ball_point(p, 10.0)
        if not j:
            j = tree.query(p, k=8)[1]
        ylo[i], yhi[i] = V[j, 1].min(), V[j, 1].max()
    from scipy.ndimage import gaussian_filter1d
    ylo, yhi = (gaussian_filter1d(a, 3.0, mode="wrap") for a in (ylo, yhi))
    t = 1.0
    # closed profile round the edge: (distance into the panel, 0 = fore face .. 1 = aft face, skin offset)
    prof = [(BIND_W, 1, t), (BIND_W * 0.5, 1, t * 1.15), (0.0, 1, t), (-t, 1, 0.0), (-t * 1.15, 0.5, 0.0), (-t, 0, 0.0),
            (0.0, 0, -t), (BIND_W * 0.5, 0, -t * 1.15), (BIND_W, 0, -t)]
    m = len(prof)
    W, K = [], []
    for a_in, k, off in prof:
        y = ylo + k * (yhi - ylo) + off
        W.append(np.column_stack([L[:, 0] + inw[:, 0] * a_in, y, L[:, 1] + inw[:, 1] * a_in]))
        K.append(a_in)
    W = np.stack(W, 1)                                               # [n, m, 3]
    Fq = []
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(m - 1):
            a, b, c, d = i * m + j, i * m + j + 1, i2 * m + j + 1, i2 * m + j
            Fq += [[a, b, c], [a, c, d]]
    u = np.cumsum([0.0] + [float(np.hypot(prof[j + 1][0] - prof[j][0], (prof[j + 1][1] - prof[j][1]) * 12.0)) for j in range(m - 1)])
    uvm = np.stack([np.broadcast_to(u[None, :], (n, m)), np.broadcast_to(si[:, None], (n, m))], -1).reshape(-1, 2) / 500.0
    Fq = np.array(Fq)
    Wf = W.reshape(-1, 3)
    band = Fq[(Fq % m).max(1) <= 1]                                 # the two profile strips on the aft face
    if np.cross(Wf[band[:, 1]] - Wf[band[:, 0]], Wf[band[:, 2]] - Wf[band[:, 0]])[:, 1].sum() < 0:
        Fq = Fq[:, ::-1]                                             # the aft face must look aft
    mesh = amesh(Wf, Fq, uvm)
    vis = _vis(bp)
    sc.add_part("back_panel_binding", mesh, "body", label="Back-panel edge binding, body colour (DECISIONS 2026-11-12)",
                **vis)
    line = np.vstack([W[:, 0], W[:1, 0]]) + np.array([0.0, 0.25, 0.0])
    line = line - np.vstack([np.column_stack([inw[:, 0], np.zeros(n), inw[:, 1]]), [[inw[0, 0], 0.0, inw[0, 1]]]]) * 2.5
    thr = SM.stitch_row(line, np.tile([0.0, 1.0, 0.0], (len(line), 1)))
    sc.add_part("back_panel_binding__thread", thr, "thread", **vis)
    return {"loop_mm": float(s[-1]), "width_mm": BIND_W, "x_half": float(np.abs(L[:, 0]).max()),
            "edge_thick_mm": [float((yhi - ylo).min()), float((yhi - ylo).max())]}


def pod_rev1(sc, sk) -> dict:
    """Scope pod as a sewn part: a sleeve with a flat base, a base seam, a bound mouth and a throat zip (POD-1), hung
    75 mm lower so that W1 crosses its wall. W1 is then re-run taut over the new pod."""
    from . import geom as G
    from .assets import fabric as FB
    from .assets import mesh as amesh
    from .assets import seams as SM
    old, eye = _part(sc, "s15_pod"), _part(sc, "s15_pod_scope")
    if old is None:
        return {}
    Vo = np.asarray(old.mesh.vertices, float)
    lo, hi = Vo.min(0), Vo.max(0)
    R = 0.5 * float(hi[0] - lo[0])
    cx, cy = 0.5 * float(lo[0] + hi[0]), 0.5 * float(lo[1] + hi[1])
    sx = 1.0 if cx > 0 else -1.0
    zb, zm, c = float(lo[2]) - POD["drop"], POD["mouth_z"], POD["corner"]
    vis = _vis(old)
    # profile (r, z): flat base, rounded corner, wall tapering to the mouth, a turned-in lip
    prof = [(r, zb) for r in np.linspace(0.0, R - c, 5)]
    prof += [(R - c + c * np.sin(q), zb + c * (1 - np.cos(q))) for q in np.linspace(0, np.pi / 2, 7)[1:]]
    zw = np.linspace(zb + c, zm, int((zm - zb - c) / 7.0) + 1)[1:]
    prof += [(R + (POD["r_mouth"] - R) * ((z - zb - c) / (zm - zb - c)) ** 2.2, z) for z in zw]
    prof += [(POD["r_mouth"] - 2.0, zm + 1.5), (POD["r_mouth"] - 4.5, zm - 1.0)]
    prof = np.array(prof)
    nth = 56
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    ring = np.column_stack([np.cos(th), np.sin(th)])
    V = np.concatenate([np.column_stack([cx + r * ring[:, 0], cy + r * ring[:, 1], np.full(nth, z)]) for r, z in prof])
    sp = np.r_[0, np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))]
    uv = np.concatenate([np.column_stack([th * R, np.full(nth, s)]) for s in sp]) / 500.0
    Fq = []
    for i in range(len(prof) - 1):
        for j in range(nth):
            j2 = (j + 1) % nth
            a, b, d, e = i * nth + j, i * nth + j2, (i + 1) * nth + j2, (i + 1) * nth + j
            Fq += [[a, b, d], [a, d, e]]
    Fq = np.array(Fq)
    k = len(prof) // 2
    nq = np.cross(V[Fq[k * nth * 2, 1]] - V[Fq[k * nth * 2, 0]], V[Fq[k * nth * 2, 2]] - V[Fq[k * nth * 2, 0]])
    if np.dot(nq, V[Fq[k * nth * 2, 0]] - np.array([cx, cy, V[Fq[k * nth * 2, 0], 2]])) < 0:
        Fq = Fq[:, ::-1]
    sc.parts = [x for x in sc.parts if x is not old and x is not eye]
    sc.add_fabric("s15_pod", amesh(V, Fq, uv), "body", look=FB.Look(slack=0.35, fold=2.0), max_edge=4.0,
                  uv_is_pattern=False, label="IMP-1 scope pod on the left gusset: sleeve, sewn base, bound mouth, zip",
                  **vis)
    scope = G.capsule_between([cx, cy, zm - 70.0], [cx, cy, POD["scope_top"]], POD["r_mouth"] - 5.0, POD["r_mouth"] - 8.0)
    sc.add_part("s15_pod_scope", scope, "fitting", label="85 mm spotter", **vis)

    def ring_at(z, r, lift=0.0):
        a = np.linspace(0, 2 * np.pi, 73)
        N = np.column_stack([np.cos(a), np.sin(a), np.zeros(73)])
        return np.array([cx, cy, z]) + (r + lift) * N, N
    Pb, Nb = ring_at(zb + c, R, 0.3)
    sc.add_seam("cf_pod_seam_base", Pb, Nb, **vis)
    Pm, Nm = ring_at(zm + 1.0, POD["r_mouth"] - 1.0)
    bd = SM.binding(Pm, Nm, width=10.0, edge_out=np.tile([0.0, 0.0, 1.0], (len(Pm), 1)))
    sc.add_part("cf_pod_binding", bd["binding"], "trim", **vis)
    sc.add_part("cf_pod_binding__thread", bd["thread"], "thread", **vis)
    d = _unit(np.array([sx * 0.60, 0.80, 0.0]))                     # outboard and aft: the side the camera sees
    zz = np.linspace(zm - 14.0, zm - 14.0 - POD["zip_len"], 40)
    wall = prof[10:11 + len(zw)]
    rr = np.interp(zz, wall[:, 1], wall[:, 0])
    Pz = np.column_stack([cx + (rr + 0.4) * d[0], cy + (rr + 0.4) * d[1], zz])
    sc.add_zip("cf_pod_zip", Pz, np.tile(d, (len(Pz), 1)), size=POD["zip"], sliders=(0.08,), **vis)
    # W1 again, taut over the new pod and the tripod
    piece = np.asarray(sk["piece"]).astype(str)
    b01 = np.unique(np.asarray(sk["tris"])[np.char.startswith(piece, "B-01")])
    clouds = [sk["X"], sk["X"][b01], V, np.asarray(scope.vertices)]
    clouds += [np.asarray(x.mesh.vertices) for x in sc.parts if x.name in ("s15_tripod", "s15_tripod_parts")]
    out = {"R": R, "base_z": zb, "mouth_z": zm, "W": {}}
    for w in CP.wraps(TORSO, SHELL):
        zl = float(CP.strap_z(w, cx))
        out["W"][w["id"]] = {"z_at_pod": zl, "on_wall": bool(zb + c < zl - 12.5 and zl + 12.5 < POD["scope_top"])}
        if w["id"] != "W1":
            continue
        ref = _part(sc, "s15_W1")
        wv = _vis(ref) if ref is not None else dict(vis, variant="rolled")
        sc.parts = [x for x in sc.parts if not x.name.startswith("s15_W1")]
        sc.strap_lines = [(P, wd) for P, wd in sc.strap_lines
                          if not (np.asarray(P)[:, 0].min() < cx and abs(float(np.asarray(P)[:, 2].mean()) - 0.5 * (w["R"][2] + w["L"][2])) < 40.0)]
        P = CP.taut_path(w, clouds, bite=1.6, step=3.0)
        P = CP._smooth_path(P, 3.0, 5.0)
        t, o, _ = CP.strap_frames(P)
        sc.add_strap("s15_W1", P, o, 25.0, label="W1 haul / compression wrap (25 mm), over the scope pod", **wv)
        right = np.where(P[:, 0] > 0.6 * P[:, 0].max())[0]
        i = int(right[np.argmin(np.abs(P[right, 1] - np.median(P[right, 1])))])
        sc.add_hardware("s15_W1_lock", "ladder_lock_25", P[i], o[i], -t[i], **wv)
        on = P[np.abs(P[:, 0] - cx) < R]
        out["W1_z_on_pod"] = [float(on[:, 2].min()), float(on[:, 2].max())] if len(on) else None
    return out


def door_cloth(S, door_m, H, ch, clouds, cfg=None):
    """The opened door as cloth (DOOR-OPEN-1): each 10 mm column of the door is laid, from the hinge seam, along the
    taut line over what stands above the hinge (``clouds``: vertex arrays), with slack bellying out of the rise, then
    smoothed across the door. Same return as ``corrie._door_open``: (outer, lining, rim) meshes on the door's own
    vertices, so the door pocket follows through ``corrie_b1.door_pocket_parts``."""
    from scipy.interpolate import RegularGridInterpolator
    from scipy.ndimage import gaussian_filter1d
    from scipy.spatial import ConvexHull
    from . import corrie as VC
    from . import geom as G
    cfg = dict(DOOR_CLOTH, **(cfg or {}))
    Fd0 = S.F[door_m]
    used = np.unique(Fd0)
    x0 = S.x0[used]
    remap = -np.ones(len(S.V), int)
    remap[used] = np.arange(len(used))
    Fd = remap[Fd0]
    zh = float(H["z_hinge"])
    s = np.clip(zh - x0[:, 2], 0, None)
    x = x0[:, 0]
    hk = frozenset(("B-02door", "B-02h"))
    hinge = np.vstack([S.V[cc] for cc in ch.get(hk, [])]) if ch and hk in ch else S.V[used][s < 8]
    O = np.vstack([np.asarray(c, float).reshape(-1, 3) for c in clouds])
    O = O[O[:, 2] > hinge[:, 2].min() - 10.0]
    xs = np.linspace(x.min(), x.max(), max(int(np.ptp(x) / cfg["col"]) + 1, 3))
    sg = np.arange(0.0, s.max() + 2 * cfg["ds"], cfg["ds"])
    ang = np.linspace(0, 2 * np.pi, 13)[:-1]
    circ = cfg["clear"] * np.column_stack([np.cos(ang), np.sin(ang)])
    GY, GZ = np.zeros((len(xs), len(sg))), np.zeros((len(xs), len(sg)))
    for i, xc in enumerate(xs):
        h0 = hinge[np.argmin(np.abs(hinge[:, 0] - xc))]
        col = O[np.abs(O[:, 0] - xc) < cfg["win"]][:, 1:]
        col = col[col[:, 1] > h0[2] + cfg["clear"] + 1.0]
        a = np.array([h0[1] + 1.0, h0[2]])
        if len(col) < 3:
            ch2 = np.array([a, a + [0.0, 1.0]])
        else:
            Q = (col[:, None, :] + circ[None]).reshape(-1, 2)
            b = np.array([Q[:, 0].min() - 1.0, h0[2]])               # front foot of the hull, level with the hinge
            P2 = np.vstack([Q, a, b])
            Hv = list(ConvexHull(P2).vertices)                       # counter-clockwise in (y, z)
            i0 = Hv.index(len(P2) - 2)
            Hv = Hv[i0:] + Hv[:i0]
            ch2 = P2[Hv[:Hv.index(len(P2) - 1) + 1]]                 # hinge -> up the aft side -> over the top -> front
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ch2, axis=0), axis=1))]
        if d[-1] < sg[-1]:                                           # door longer than the line: it hangs on down
            ch2 = np.vstack([ch2, ch2[-1] + [0.0, -(sg[-1] - d[-1]) - 1.0]])
            d = np.r_[d, sg[-1] + 1.0]
        y, z = np.interp(sg, d, ch2[:, 0]), np.interp(sg, d, ch2[:, 1])
        ty, tz = np.gradient(y, sg), np.gradient(z, sg)
        up = np.where((tz < 0.3) & (sg > 60.0))[0]
        s1 = sg[up[0]] if len(up) else sg[-1]
        uu = np.clip(sg / max(s1, 1.0), 0.0, 1.0)
        bel = cfg["sag"] * (0.8 + 0.2 * np.cos(2 * np.pi * xc / 190.0)) * np.sin(np.pi * uu ** 0.75) ** 2
        nrm = np.hypot(ty, tz) + 1e-9
        GY[i], GZ[i] = y + bel * tz / nrm, z - bel * ty / nrm
    GY, GZ = (gaussian_filter1d(A, 6.0 / cfg["ds"], axis=1, mode="nearest") for A in (GY, GZ))
    GY, GZ = (gaussian_filter1d(A, 18.0 / cfg["col"], axis=0, mode="nearest") for A in (GY, GZ))
    q = np.column_stack([np.clip(x, xs[0], xs[-1]), np.clip(s, sg[0], sg[-1])])
    out = np.column_stack([x, RegularGridInterpolator((xs, sg), GY)(q), RegularGridInterpolator((xs, sg), GZ)(q)])
    # the first 20 mm blend onto the hinge seam of the solved cloth
    from scipy.spatial import cKDTree
    hj = cKDTree(hinge[:, [0]]).query(x[:, None])[1]
    wgt = np.clip(1.0 - s / 20.0, 0.0, 1.0)[:, None]
    out = out * (1 - wgt) + (hinge[hj] + [0.0, 1.0, 0.0]) * wgt
    mid = G._mesh(out, Fd, S.uv[used], flip_if_negative=False)
    vn = VC._vnormals(mid)
    rise = (s > 20.0) & (s < 120.0)
    if np.mean(vn[rise, 1]) < 0:
        vn = -vn
        Fd = Fd[:, ::-1]
    lining = G._mesh(out + vn * 1.1, Fd, S.uv[used], flip_if_negative=False)
    outer = G._mesh(out - vn * 1.1, Fd[:, ::-1], S.uv[used], flip_if_negative=False)
    rim = []
    for cc in VC.boundary_chains(Fd, keep=lambda e: s[e[0]] > 6 or s[e[1]] > 6):
        if len(cc) > 4:
            rim.append(G.tube(VC.smooth_line(out[cc], 3.0, 6.0), 2.4, n=8))
    return outer, lining, G.concat(rim)


def door_rev1(sc) -> dict:
    """Swap the hinged rigid door copy for ``door_cloth`` and rebuild the door pocket on it."""
    from . import corrie as VC
    from . import corrie_b1 as VB1
    cap = getattr(sc, "_door_cap", None)
    dp = _part(sc, "corrie_door_open")
    if not cap or dp is None or "S" not in cap:
        return {}
    clouds = [np.asarray(x.mesh.vertices) for x in sc.parts
              if x.name.startswith(DOOR_LIES_ON) and x.variant in (None, "lid", "full") and len(x.mesh.vertices)]
    outer, lining, rim = door_cloth(cap["S"], cap["door_m"], cap["H"], cap["ch"], clouds)
    dp.mesh = outer
    dp.label = "Door D2 open: thrown up over the top, lying on the roll and pouch (cloth, DOOR-OPEN-1)"
    from .assets import fabric as FB
    dp.look = FB.Look(slack=0.45, fold=2.6, fold_mm=(30.0, 70.0), hand=0.8)
    r = _part(sc, "corrie_door_rim")
    if r is not None:
        r.mesh = rim
    if "pocket" in cap:
        orig = VC._door_open
        VC._door_open = lambda *a, **k: (outer, lining, rim)
        try:
            for q in VB1.door_pocket_parts(cap["S"], cap["pocket"]):
                tgt = _part(sc, q.name)
                if tgt is not None:
                    tgt.mesh = q.mesh
        finally:
            VC._door_open = orig
    V = np.asarray(outer.vertices)
    return {"z_top": float(V[:, 2].max()), "y_min": float(V[:, 1].min()), "y_max": float(V[:, 1].max()),
            "lies_on": len(clouds)}


def finish(sc, state: str, meat: bool = True):
    """Turn the BL-020 S15 scene (already built on CORRIE F's cloth with the aft face re-cut) into CORRIE F."""
    from . import corrie as VC
    from . import geom as G
    from .assets import mesh as amesh
    BC, CO, F, CS = _mods()
    sk = sc.cloth_skin
    byname = {x.name: x for x in sc.parts}
    # ---- deleted: crown hood, its lining and ladders (BL-004); the chevron kick edge (D2 has the blade U instead);
    #      float-mode meat (not a shot here)
    DROP = ("crown_hood", "hood_lining", "hood_ladders", "corrie_kick_edge", "quarter_float", "quarter_bone_float",
            "meat_straps_float", "meat_hardware_float", "cradle_straps_float", "float_link")
    sc.parts = [x for x in sc.parts if not x.name.startswith(DROP)]
    # ---- body and camo by D2's pieces: blade U = camo, everything else of the shell = body fabric
    S = VC.Skin(sk)
    pc = S.piece.astype(str)
    um = pc == "B-02u"
    body_m = ~(um | (pc == "B-02door") | (pc == "B-05"))
    byname["corrie_body"].mesh = S.submesh(body_m)
    byname["corrie_body"].label = "CORRIE F main bag (cloth pass on the fine huntkit drape, 19 in)"
    byname["corrie_kick"].mesh = S.submesh(um)
    byname["corrie_kick"].label = "D2 camo blade U: both blades and the 75 mm kick strip, one piece"
    if "corrie_door" in byname:
        byname["corrie_door"].label = "D2 door (whole aft face between the blades, z 110-650), closed"
    vis = dict(group="bag", modes=VC.BAGM)
    # ---- IM2 bag hooks and tongues deleted; IM3 bag hooks become wiregate carabiners
    hk, cache = byname.get("bag_hooks"), getattr(sc, "_hook_cache", [])
    if hk is not None and cache:
        hk.mesh = G.concat([carabiner(cen, [0, 0, 1.0], [0, -1.0, 0]) for cen, lo, hi in cache if cen[2] > sc._hook_zmid])
        hk.label = "IM3 bag hooks: certified wiregate carabiners (21 kN major axis), BL-010"
    tg = byname.get("hook_tongues")
    if tg is not None and getattr(sc, "_hook_zmid", None):
        _keep_faces(tg, lambda c, lo, hi: hi[2] > sc._hook_zmid)
        tg.label = "T3 bag-hook tongues at IM3 (38 mm); the IM2 tongues are deleted (BL-004)"
    # ---- rev 1 (BL-026): 25 mm straps, guys on the B-25 bridle, scope pod and W1, B-26 keeper, panel binding
    rev = {"straps_25": straps_25(sc), "guys": guys_rev1(sc, sk)}
    if _part(sc, "s15_pod") is not None:
        rev["pod"] = pod_rev1(sc, sk)
    rev["keeper"] = keeper_cord(sc, sk, [(np.asarray(x.mesh.vertices), np.asarray(x.mesh.faces)) for x in sc.parts
                                         if x.name in ("s15_tripod", "s15_tripod_parts")])
    rev["binding"] = panel_binding(sc)
    # ---- meat inside the bag on IM1-IM3 (door-open shot, haul state): a game bag against the frame face
    if meat and state == "full" and "quarter_proxy" in byname:
        qp = byname["quarter_proxy"]
        Vq = np.asarray(qp.mesh.vertices, float).copy()
        b01 = np.unique(sk["tris"][np.char.startswith(sk["piece"].astype(str), "B-01")])
        aftv = np.unique(sk["tris"][np.char.startswith(sk["piece"].astype(str), "B-02")])
        yf = float(np.percentile(sk["X"][b01][:, 1], 90)) + 14.0
        ya = float(np.percentile(sk["X"][aftv][:, 1], 20)) - 22.0
        zfl = float(np.percentile(sk["X"][np.unique(sk["tris"][sk["piece"].astype(str) == "B-05"])][:, 2], 80)) + 10.0
        lo, hi = Vq.min(0), Vq.max(0)
        Vq[:, 0] = (Vq[:, 0] - 0.5 * (lo[0] + hi[0])) * (150.0 / (0.5 * (hi[0] - lo[0])))
        Vq[:, 1] = yf + (Vq[:, 1] - lo[1]) / (hi[1] - lo[1]) * (ya - yf)
        Vq[:, 2] = zfl + (Vq[:, 2] - lo[2]) * min(1.0, 560.0 / (hi[2] - lo[2]))
        mv = dict(group="bag", modes=("pack_haul",), variant="full")
        sc.add_fabric("cf_meat", amesh(Vq, np.asarray(qp.mesh.faces), qp.mesh.metadata.get("uv")), "game_bag",
                      max_edge=5.0, uv_is_pattern=False, label="Boned meat in a game bag, inside the bag on IM1-IM3",
                      **mv)
        for k, zs in enumerate((190.0, 330.0, 520.0)):
            w = {"id": f"IM{k + 1}", "R": np.array([125.0, yf - 10.0, zs]), "L": np.array([-125.0, yf - 10.0, zs])}
            P = CP.taut_path(w, [Vq, np.array([[125.0, yf - 9.0, zs], [-125.0, yf - 9.0, zs]])], bite=2.0, step=3.0)
            P = CP._smooth_path(P, 3.0, 6.0)
            _, o, _ = CP.strap_frames(P)
            sc.add_strap(f"cf_meat_IM{k + 1}", P, o, 25.0, material="meat_strap", dent=False,
                         label=f"IM{k + 1} over the meat (25 mm, BL-003)", **mv)
            t = _unit(np.gradient(P, axis=0))
            i = int(np.argmin(np.abs(P[:, 0] - 60.0) + 1e3 * (P[:, 1] < P[:, 1].max() - 12.0)))
            sc.add_hardware(f"cf_meat_IM{k + 1}_cam", "cam_buckle_25", P[i], o[i], -t[i], **mv)
        for x in sc.parts:                              # the bare IM straps and hooks show only without meat
            if x.name.startswith("corrie_im_"):
                x.modes = ("pack",)
    rev["door"] = door_rev1(sc)              # last: the door lies on everything built above
    sc.report["rev1"] = rev
    sc.report["source"] = {"sim": "corrie_f_sim fine drape F_PR19 (seed) + viz3d.cloth_pass", "case": state,
                           "spec": "CORRIE F rev 1, door D2, wings deleted, no crown hood", "frame": frame_note()}
    return sc


def scene(state: str = "sixday", carry: bool = False, level: int = 2, name: str | None = None,
          with_pouch: bool | None = None, wraps: bool = True, force: bool = False):
    """CORRIE F at a load state ("day" 12 L, pouch off; "sixday" 45 L; "full"). ``carry`` adds the tripod (right,
    under W1-W3) and the scope pod (left gusset). Returns a ``studio.ConceptScene``."""
    from types import SimpleNamespace
    from . import corrie as VC
    from . import corrie_b1 as VB1
    from . import studio
    PV.ensure(TORSO)
    p = CP.ClothParams(level=level, clip_below_seam=CLIP_BELOW_SEAM_MM)
    old = getattr(studio, "LEGACY_WRAPS", None)
    PV.viz_door = True
    if old is not None:
        studio.LEGACY_WRAPS = bool(wraps)
    cap, o_open, o_pocket = {}, VC._door_open, VB1.door_pocket_parts

    def see_door(S, door_m, H, ch):                    # what the legacy door builders were given (door_rev1 reuses it)
        cap.update(S=S, door_m=door_m, H=dict(H), ch=ch)
        return o_open(S, door_m, H, ch)

    def see_pocket(S, CO2):
        cap["pocket"] = SimpleNamespace(DOOR=dict(CO2.DOOR), DOOR_POCKET=dict(CO2.DOOR_POCKET))
        return o_pocket(S, CO2)
    VC._door_open, VB1.door_pocket_parts = see_door, see_pocket
    try:
        sc = CP.s15_scene(state, carry, p, name or f"corrie_f_{state}{'_carry' if carry else ''}", shell=SHELL,
                          torso=TORSO, force=force, with_pouch=with_pouch, skin_hook=d2_recut,
                          scene_params=viz_params(), pouch_soft=POUCH_SOFT)
    finally:
        VC._door_open, VB1.door_pocket_parts = o_open, o_pocket
        PV.viz_door = False
        if old is not None:
            studio.LEGACY_WRAPS = old
    sc._door_cap = cap
    hk = next((x for x in sc.parts if x.name == "bag_hooks"), None)
    if hk is not None:                                  # component centres of the four legacy hooks
        tm, lab = _components(hk.mesh)
        cs = []
        for k in np.unique(lab):
            Q = tm.vertices[np.unique(tm.faces[lab == k])]
            cs.append((Q.mean(0), Q.min(0), Q.max(0)))
        sc._hook_cache = cs
        zz = [c[0][2] for c in cs]
        sc._hook_zmid = 0.5 * (min(zz) + max(zz))
    return finish(sc, state)


# ================================================================================================== the shots
BOX = [-290.0, -120.0, -100.0, 290.0, 360.0, 1140.0]
STATE_LABEL = {"day": "day load, 12 L, top pouch off", "sixday": "6-day load, 45 L", "full": "full, 85 L class"}
SUB = "CORRIE F rev 1 (D2), H1 frame, belt B. "
MODEL = "Rendered 3D model, not a photograph"
PK = {"mannequin": True, "lid": True}


def _hunter(pose, state, az, el, caption, sub, scene_kind="studio", **view):
    v = {"az": az, "el": el, "fov": 24, "fstop": 11 if scene_kind == "studio" else 4.5, "frame": "pack", "fill": 0.9}
    if scene_kind == "outdoor":
        v["exposure"] = -0.9
    v.update(view)
    return {"scene": state, "pose": pose, "kind": scene_kind, "view": v, "state": {"lid": True},
            "caption": caption, "sub": sub + NOT_A_PHOTO}


HUNTER_BOX = [-300.0, -330.0, -1080.0, 300.0, 380.0, 1060.0]     # same camera for the three load states (FCS mm)
HUNTER_ZOOM = 1.16       # 1.3 cut the full load's collar and pouch off at the top of the frame (defect D-2)

SHOTS = {
    # --- on the 6 ft hunter, 19 in setting
    "hero": _hunter("stand", "sixday", -36, 9, "CORRIE F on a 6 ft hunter: 3/4 rear, 6-day load (45 L)",
                    SUB + "1829 mm (6 ft) man, 19 in setting. ", box=HUNTER_BOX, zoom=HUNTER_ZOOM),
    "side": _hunter("side", "sixday", 90, 4, "Side profile, 6-day load (45 L)",
                    SUB + "How tall and how deep it rides. ", box=HUNTER_BOX, zoom=HUNTER_ZOOM),
    "day": _hunter("stand", "day", -36, 9, "Day load (12 L): rolled down and cinched, top pouch off",
                   SUB + "Same camera as 6-day and full. ", box=HUNTER_BOX, zoom=HUNTER_ZOOM),
    "full": _hunter("stand", "full", -36, 9, "Full: 85 L class, collar standing, pouch on the roll",
                    SUB + "Same camera as day and 6-day. ", box=HUNTER_BOX, zoom=HUNTER_ZOOM),
    "walk": _hunter("walk", "sixday", -58, 6, "Walking uphill with trekking poles, 6-day load",
                    "CORRIE F. HDRI and grass: Poly Haven, CC0. ", "outdoor"),
    "kneel": _hunter("kneel", "sixday", 118, 5, "Kneeling and glassing with the pack on, 6-day load",
                     "CORRIE F. HDRI and grass: Poly Haven, CC0. ", "outdoor"),
    "belt": _hunter("front", "sixday", 150, 8, "Hipbelt B and pockets from the front 3/4",
                    "Belt pocket left, bottle holster right, 50 mm buckle, sternum strap. ",
                    box=[-330.0, -420.0, -120.0, 330.0, 140.0, 600.0]),
    # --- on the display form
    "door": {"scene": "full", "view": {"az": -22, "el": 8, "fov": 24, "fstop": 11, "box": [-270, 0, 20, 270, 400, 1010]},
             "state": {"mannequin": True, "lid": True, "full": True}, "caption": "Door D2 open (full load)",
             "sub": "Door laid up over the top pouch (cloth); W1, W2 unhooked; IM1-IM3 inside"},
    "meat": {"scene": "full", "view": {"az": -18, "el": 6, "fov": 24, "fstop": 11, "box": [-270, 0, 20, 270, 400, 1010]},
             "state": {"mannequin": True, "lid": True, "full": True, "haul": True},
             "caption": "Meat inside the bag on IM1-IM3, door D2 open",
             "sub": "Game bag on the frame face under the three 25 mm internal meat straps"},
    "frame": {"scene": "full", "view": {"az": -72, "el": 6, "fov": 24, "fstop": 11, "frame": "pack", "zoom": 1.0},
              "state": {"mannequin": True, "mode": "frame", "haul": True},
              "caption": "Bag off: meat on the H1 frame",
              "sub": "Game bag in the under-strap cradle; meat and under-straps 25 mm (BL-003)"},
    "frame_bare": {"scene": "full", "view": {"az": -38, "el": 10, "fov": 24, "fstop": 11, "frame": "pack"},
                   "state": {"mannequin": True, "mode": "frame"},
                   "caption": "Bag off: the H1 frame, crown, spreader and belt B",
                   "sub": "BL-027 body, 28 mm IM3 cheeks; B-25 guy bridle on the top bar; crown at 19 in"},
    "addons_on": {"scene": "full_carry", "view": {"az": 38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                  "state": PK, "caption": "Add-ons on: tripod under W1-W3 (right), scope pod (left), top pouch",
                  "sub": "CORRIE F rev 1, full load; B-26 keeper cord over the tripod"},
    "addons_on_left": {"scene": "full_carry", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                       "state": PK, "caption": "Add-ons on, from the left: scope pod on the left gusset",
                       "sub": "Rev 1, full load; W1, W2 over the pod's wall; W3 runs above the scope"},
    "addons_off": {"scene": "full", "view": {"az": 38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                   "state": {"mannequin": True, "lid": False}, "caption": "Add-ons off: base pack",
                   "sub": "CORRIE F rev 1, full load, same camera; B-26 cord on the gusset"},
    "compare_f": {"scene": "full", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                  "state": PK, "caption": "CORRIE F, full load", "sub": "S15 shell, door D2, no wings, no hood"},
    "compare_b2": {"scene": "b2", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                   "state": PK, "caption": "CORRIE B.2, full load", "sub": "Same camera"},
    "roll": {"scene": "sixday", "view": {"az": -32, "el": 22, "fov": 18, "fstop": 8, "at": [0.0, 150.0, 610.0],
                                         "span": 560}, "state": PK, "caption": "Rolled closure and top pouch, 6-day load",
             "sub": "Roll ends bent down to clip tabs 150 mm below the collar seam; soft pouch"},
}
for _k, _s in SHOTS.items():                       # every caption says what the picture is (owner, 2026-11-12)
    if not _s.get("pose"):
        _s["sub"] = _s["sub"].rstrip(". ") + ". " + MODEL
SUB_MAX = 116                                      # characters that fit the 1600 px caption band
ORDER = ("hero", "side", "day", "full", "walk", "kneel", "door", "meat", "frame", "frame_bare", "addons_on",
         "addons_on_left", "addons_off", "belt", "roll", "compare_f", "compare_b2")


def build_scene(key: str, level: int = 2):
    from . import studio
    if key == "b2":
        return studio.corrie_b2_scene("corrie_b2_bl012")
    st, _, carry = key.partition("_")
    return scene(st, carry == "carry", level)


def render(names=ORDER, out_dir=None, prefix="20261112_BL026", quality="final", level: int = 2, numbers=None,
           bpy_python=None, threads=None) -> list:
    """Render the named shots. Stage 1 (this interpreter) builds each scene once; stage 2 runs one Blender process
    per (scene, pose, studio / outdoor) group. ``numbers`` = {shot: n} fixes the file numbers (default: position in
    ORDER + 1). Returns one dict per frame."""
    from . import studio
    out_dir = Path(out_dir or REPO / "outputs" / "screens")
    numbers = numbers or {n: ORDER.index(n) + 1 for n in names}
    py = studio.find_bpy_python(bpy_python)
    if py is None:
        raise RuntimeError("set HUNTKIT_BPY to the Blender venv's Python (huntkit/viz3d/README.md)")
    q = quality if isinstance(quality, dict) else (
        {"res": (1600, 1200), "samples": 64} if quality == "final" else dict(studio.QUALITY[quality]))
    results = []
    by_scene = {}
    for n in names:
        by_scene.setdefault(SHOTS[n]["scene"], []).append(n)
    WORK.mkdir(parents=True, exist_ok=True)
    for skey, ns in by_scene.items():
        sj = build_scene(skey, level).build(WORK / skey)
        groups = {}
        for n in ns:
            groups.setdefault((SHOTS[n].get("pose"), SHOTS[n].get("kind", "studio")), []).append(n)
        for (pose, kind), gs in groups.items():
            for n in gs:                                  # one job per shot keeps the file numbers free
                job = {"scene": str(sj), "shots": {n: {k: SHOTS[n][k] for k in ("view", "state", "caption", "sub")}},
                       "out": str(out_dir), "prefix": prefix, "quality": q, "start": numbers[n], "pose": pose,
                       "kind": kind, "threads": threads, "torso": float(TORSO)}
                jf = WORK / f"{prefix}_{n}.job.json"
                jf.write_text(json.dumps(job))
                env = dict(os.environ, HUNTKIT_PY=os.environ.get("HUNTKIT_PY", sys.executable))
                subprocess.run([py, "-m", "huntkit.viz3d.corrie_f", "--job", str(jf)], cwd=REPO, check=True, env=env)
                r = json.loads(jf.with_suffix(".result.json").read_text())
                for x in r:
                    x["shot"] = n
                results += r
                print(f"[{n}] {r[0]['file']} {r[0]['seconds']} s", flush=True)
    return results


# ------------------------------------------------------------------------------------------- stage 2 (bpy)
def _stage2(job: dict) -> list:
    from . import studio as ST
    kw = dict(quality=job["quality"], start=job["start"], threads=job.get("threads"), torso=job["torso"])
    if job.get("pose") is None:
        return ST.render_scene(job["scene"], job["shots"], job["out"], job["prefix"], **kw)
    from . import wearer as WR
    wk = {"torso_in": float(TORSO), "stature_mm": float(WR.OWNER_STATURE_MM), "pose": job["pose"]}
    import bpy
    from mathutils import Matrix
    outdoor = job["kind"] == "outdoor"
    az = next(iter(job["shots"].values()))["view"]["az"]

    def hook(**k):
        pre = {o.name for o in bpy.data.objects}
        res = WR.studio_wearer(**k)
        # wearer.py builds the front belt webbing in pack space and returns it with neither the figure nor the
        # pack, so studio never moves it onto the torso (it lay on the floor at the feet): move it here
        mine = {o.name for o in res["objects"]}
        M = Matrix([list(r) for r in res["pack_on_torso"]])
        for o in bpy.data.objects:
            if o.type == "MESH" and o.name not in pre and o.name not in mine and o.parent is None:
                o.matrix_world = M @ o.matrix_world
        if outdoor:
            if not WR.HDRI_SUN_AZ_DEG:
                WR.HDRI_SUN_AZ_DEG = WR._hdri_sun_az()[0]
            WR._outdoor(res["wearer"], az)
        return res

    if outdoor:
        def no_backdrop():
            ob = bpy.data.objects.new("no_backdrop", None)
            bpy.context.scene.collection.objects.link(ob)
            return ob
        ST.make_backdrop, ST.make_lights, ST.place_lights = no_backdrop, (lambda: ()), (lambda *a, **k: None)
    return ST.render_scene(job["scene"], job["shots"], job["out"], job["prefix"], wearer=hook, wearer_kwargs=wk, **kw)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--job")
    ap.add_argument("--shots", default="all")
    ap.add_argument("--quality", default="final")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--prefix", default="20261112_BL026")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.job:
        job = json.loads(Path(a.job).read_text())
        res = _stage2(job)
        Path(a.job).with_suffix(".result.json").write_text(json.dumps(res))
        return
    names = ORDER if a.shots == "all" else tuple(a.shots.split(","))
    for r in render(names, a.out, a.prefix, a.quality, a.level):
        print(r["shot"], r["file"], r["seconds"], "s", r["mb"], "MB")


if __name__ == "__main__":
    main()
