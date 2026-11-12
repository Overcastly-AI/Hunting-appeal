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
* the frame is the H1 body when ``outputs/pack3d_h1/genframe_assembled.stl`` exists (``frame_h1.py`` writes it).

Renders: ``render(shots)`` groups the shots by scene and by wearer pose and runs each group through
``huntkit.viz3d.studio`` (``studio.render_scene``); the hunter is BL-019's ``wearer.studio_wearer`` at the 19 in
setting, and outdoor shots add ``wearer._outdoor`` (CC0 HDRI and grass) in place of the studio sweep.

    python -m huntkit.viz3d.corrie_f --shots hero,side --quality quick      # repo Python; needs HUNTKIT_BPY
"""
from __future__ import annotations

import json
import os
import pickle
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
# ASSUMPTION POUCH-1 (picture choice): the top pouch as a limp, part-full bag: rounded heap of goods 16 mm high at
# the edge of a 60 mm box, the four strap points held. Settled by a photograph of the sewn pouch with 1 kg in it.
POUCH_SOFT = {"vertex_mass": 0.010, "bending": 0.12, "heap": 20.0, "round": 0.95, "pin": True, "pillow": 0.55,
              "relax": 10}
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
    if (H1_DIR / "genframe_assembled.stl").exists():
        p["generative_frame_dir"] = str(H1_DIR)
    return p


def frame_note() -> str:
    return ("H1 printed body (outputs/pack3d_h1); IM3 fairlead cheek still the released 18 mm, not the 27 mm of "
            "2026-11-11" if (H1_DIR / "genframe_assembled.stl").exists() else "released generative frame (H1 mesh missing)")


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
    # ---- top guys: a 25 mm loop round the crown top bar closed by a bright toggle
    crown = next((x for x in sc.parts if x.name == f"crown@t{TORSO}"), None)
    guys = byname.get(f"corrie_top_guys@t{TORSO}")
    if crown is not None and guys is not None:
        Vc = np.asarray(crown.mesh.vertices)
        topb = Vc[(Vc[:, 2] > Vc[:, 2].max() - 24.0) & (np.abs(Vc[:, 0]) < 60.0)]
        yb, zb = float(0.5 * (topb[:, 1].min() + topb[:, 1].max())), float(0.5 * (topb[:, 2].min() + topb[:, 2].max()))
        rb = float(0.5 * (topb[:, 2].max() - topb[:, 2].min()))
        Vg = np.asarray(guys.mesh.vertices)
        loops, togs = [], []
        for sx in (1, -1):
            side = Vg[Vg[:, 0] * sx > 0]
            x = float(sx * np.abs(side[:, 0]).min()) + sx * 12.5
            x = float(np.clip(x, -(np.abs(Vc[:, 0]).max() - 20.0), np.abs(Vc[:, 0]).max() - 20.0))
            a = np.linspace(0, 2 * np.pi, 40)
            ring = np.column_stack([np.full(40, x), yb + (rb + 1.6) * np.cos(a), zb + (rb + 1.6) * np.sin(a)])
            nr = np.column_stack([np.zeros(40), np.cos(a), np.sin(a)])
            loops.append(G.ribbon(ring, 25.0, 1.6, nr, step=3.0, caps=False))
            pt = np.array([x, yb + rb + 7.0, zb - 2.0])
            togs.append(G.capsule_between(pt - [TOGGLE["L"] / 2, 0, 0], pt + [TOGGLE["L"] / 2, 0, 0], TOGGLE["d"] / 2))
        sc.add_part(f"cf_guy_loops@t{TORSO}", G.concat(loops), "webbing", group="attach", torso=float(TORSO),
                    modes=("pack",), label="Top guys: 25 mm loop round the crown top bar (BL-004)")
        sc.add_part(f"cf_guy_toggles@t{TORSO}", G.concat(togs), "blaze", group="attach", torso=float(TORSO),
                    modes=("pack",), label="Guy toggles, bright ('guys on' is a carry rule)")
        guys.label = "Top guys: crown top bar -> B-22 (no crown hood)"
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
    sc.report["source"] = {"sim": "corrie_f_sim fine drape F_PR19 (seed) + viz3d.cloth_pass", "case": state,
                           "spec": "CORRIE F, door D2, wings deleted, no crown hood", "frame": frame_note()}
    return sc


def scene(state: str = "sixday", carry: bool = False, level: int = 2, name: str | None = None,
          with_pouch: bool | None = None, wraps: bool = True, force: bool = False):
    """CORRIE F at a load state ("day" 12 L, pouch off; "sixday" 45 L; "full"). ``carry`` adds the tripod (right,
    under W1-W3) and the scope pod (left gusset). Returns a ``studio.ConceptScene``."""
    from . import studio
    PV.ensure(TORSO)
    p = CP.ClothParams(level=level, clip_below_seam=CLIP_BELOW_SEAM_MM)
    old = getattr(studio, "LEGACY_WRAPS", None)
    PV.viz_door = True
    if old is not None:
        studio.LEGACY_WRAPS = bool(wraps)
    try:
        sc = CP.s15_scene(state, carry, p, name or f"corrie_f_{state}{'_carry' if carry else ''}", shell=SHELL,
                          torso=TORSO, force=force, with_pouch=with_pouch, skin_hook=d2_recut,
                          scene_params=viz_params(), pouch_soft=POUCH_SOFT)
    finally:
        PV.viz_door = False
        if old is not None:
            studio.LEGACY_WRAPS = old
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
SUB = "CORRIE F, door D2, on the H1 frame with belt B. "
PK = {"mannequin": True, "lid": True}


def _hunter(pose, state, az, el, caption, sub, scene_kind="studio", **view):
    v = {"az": az, "el": el, "fov": 24, "fstop": 11 if scene_kind == "studio" else 4.5, "frame": "pack", "fill": 0.9}
    if scene_kind == "outdoor":
        v["exposure"] = -0.9
    v.update(view)
    return {"scene": state, "pose": pose, "kind": scene_kind, "view": v, "state": {"lid": True},
            "caption": caption, "sub": sub + NOT_A_PHOTO}


HUNTER_BOX = [-300.0, -330.0, -1080.0, 300.0, 380.0, 1060.0]     # same camera for the three load states (FCS mm)

SHOTS = {
    # --- on the 6 ft hunter, 19 in setting
    "hero": _hunter("stand", "sixday", -36, 9, "CORRIE F on a 6 ft hunter: 3/4 rear, 6-day load (45 L)",
                    SUB + "1829 mm man, pack at the 19 in setting. ", box=HUNTER_BOX, zoom=1.3),
    "side": _hunter("side", "sixday", 90, 4, "Side profile, 6-day load (45 L)",
                    SUB + "How tall and how deep it rides. ", box=HUNTER_BOX, zoom=1.3),
    "day": _hunter("stand", "day", -36, 9, "Day load (12 L): rolled down and cinched, top pouch off",
                   SUB + "Same camera as the 6-day and full shots. ", box=HUNTER_BOX, zoom=1.3),
    "full": _hunter("stand", "full", -36, 9, "Full: 85 L class, collar standing, pouch on the roll",
                    SUB + "Same camera as the day and 6-day shots. ", box=HUNTER_BOX, zoom=1.3),
    "walk": _hunter("walk", "sixday", -58, 6, "Walking uphill with trekking poles, 6-day load",
                    "CORRIE F. HDRI and grass: Poly Haven, CC0. ", "outdoor"),
    "kneel": _hunter("kneel", "sixday", 118, 5, "Kneeling and glassing with the pack on, 6-day load",
                     "CORRIE F. HDRI and grass: Poly Haven, CC0. ", "outdoor"),
    "belt": _hunter("front", "sixday", 150, 8, "Hipbelt B and pockets from the front 3/4",
                    "Belt pocket left, bottle holster right, 50 mm buckle with 2:1 pulls, sternum strap. ",
                    box=[-330.0, -420.0, -120.0, 330.0, 140.0, 600.0]),
    # --- on the display form
    "door": {"scene": "full", "view": {"az": -22, "el": 8, "fov": 24, "fstop": 11, "box": [-270, 0, 20, 270, 400, 1010]},
             "state": {"mannequin": True, "lid": True, "full": True}, "caption": "Door D2 open (full load)",
             "sub": "Whole aft face between the camo blades hinges up at z 650; W1 and W2 unhooked; IM1-IM3 inside"},
    "meat": {"scene": "full", "view": {"az": -18, "el": 6, "fov": 24, "fstop": 11, "box": [-270, 0, 20, 270, 400, 1010]},
             "state": {"mannequin": True, "lid": True, "full": True, "haul": True},
             "caption": "Meat inside the bag on IM1-IM3, door D2 open",
             "sub": "Boned meat in a game bag strapped to the frame face by the three 25 mm internal meat straps"},
    "frame": {"scene": "full", "view": {"az": -72, "el": 6, "fov": 24, "fstop": 11, "frame": "pack", "zoom": 1.0},
              "state": {"mannequin": True, "mode": "frame", "haul": True},
              "caption": "Bag off: meat on the H1 frame",
              "sub": "Game bag in the under-strap cradle, held to the frame by the meat straps (drawn at the "
                     "legacy 38 mm; BL-003 makes them 25 mm)"},
    "frame_bare": {"scene": "full", "view": {"az": -38, "el": 10, "fov": 24, "fstop": 11, "frame": "pack"},
                   "state": {"mannequin": True, "mode": "frame"},
                   "caption": "Bag off: the H1 frame, crown, spreader and belt B",
                   "sub": "H1 printed body with the carbon crown at 19 in; IM3 fairlead cheek drawn at the released "
                          "18 mm (27 mm since 2026-11-11, not yet in the mesh)"},
    "addons_on": {"scene": "full_carry", "view": {"az": 38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                  "state": PK, "caption": "Add-ons on: tripod under W1-W3 (right), scope pod (left), top pouch",
                  "sub": "CORRIE F, full load"},
    "addons_on_left": {"scene": "full_carry", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                       "state": PK, "caption": "Add-ons on, from the left: scope pod on the left gusset",
                       "sub": "CORRIE F, full load"},
    "addons_off": {"scene": "full", "view": {"az": 38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                   "state": {"mannequin": True, "lid": False}, "caption": "Add-ons off: base pack",
                   "sub": "CORRIE F, full load, same camera"},
    "compare_f": {"scene": "full", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                  "state": PK, "caption": "CORRIE F, full load", "sub": "S15 shell, door D2, no wings, no hood"},
    "compare_b2": {"scene": "b2", "view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "box": BOX, "zoom": 1.4},
                   "state": PK, "caption": "CORRIE B.2, full load", "sub": "Same camera"},
    "roll": {"scene": "sixday", "view": {"az": -32, "el": 22, "fov": 18, "fstop": 8, "at": [-150.0, 110.0, 800.0],
                                         "span": 420}, "state": PK, "caption": "Rolled closure and top pouch, 6-day load",
             "sub": "Roll ends bent down to the clip tabs, now 150 mm below the collar seam; pouch as limp cloth"},
}
ORDER = ("hero", "side", "day", "full", "walk", "kneel", "door", "meat", "frame", "frame_bare", "addons_on",
         "addons_on_left", "addons_off", "belt", "roll", "compare_f", "compare_b2")


def build_scene(key: str, level: int = 2):
    from . import studio
    if key == "b2":
        return studio.corrie_b2_scene("corrie_b2_bl012")
    st, _, carry = key.partition("_")
    return scene(st, carry == "carry", level)


def render(names=ORDER, out_dir=None, prefix="20261111_BL012", quality="final", level: int = 2, numbers=None,
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
    ap.add_argument("--prefix", default="20261111_BL012")
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
