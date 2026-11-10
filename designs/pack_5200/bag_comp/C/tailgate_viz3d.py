"""TAILGATE (team C) render model: the CORRIE B.2 render pack (frame H1-era geometry, harness, belt B, display form,
hood) with CORRIE's bag parts swapped for TAILGATE's, built on TAILGATE's OWN cloth-sim drape
(outputs/clothsim/bagC_tg_PR19_fine, packed case; falls back to the coarse run while the fine one is missing).

    python designs/pack_5200/bag_comp/C/tailgate_viz3d.py --model          # GLB + viewer manifest + shots.json
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_bagC/tailgate.glb \\
        --shots outputs/pack3d_bagC/shots.json --views C_hero,C_side,C_open,C_zip,C_meat \\
        --samples 48 --prefix 20261110_bagC --out outputs/screens

Variants (viewer toggles): ``rolled`` = lid zipped (hidden when ``full``), ``full`` = lid down (tailgate), lining,
IM straps inside; ``lid`` = tripod under the right side straps + the meat quarter inside the bag (only visible with
the lid down). Render-only liberties: the lid, straps, flaps, roll and pouch are placed geometry on the simulated skin;
the open lid is the simulated lid rotated rigidly about the hinge seam (165 deg, it hangs 15 deg out of plumb).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from huntkit.viz3d import corrie as VC  # noqa: E402
from huntkit.viz3d import geom as G  # noqa: E402
from huntkit.viz3d.model import BAGM, Part  # noqa: E402

OUT = ROOT / "outputs" / "pack3d_bagC"
SIM = ROOT / "outputs" / "clothsim"
SCEN = HERE / "scenarios" / "tg_PR19.yaml"
BE = (0.0, 260.0, 0.0)
OPEN_DEG = 165.0

SHOTS = {
    "C_hero": {"view": {"az": -38, "el": 12, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
               "caption": "TAILGATE (team C): 3/4 rear on the display form",
               "sub": "Full-face lid zipped, 3 lid straps H1-H3 at the IM heights carry the hoop load; camo storm flaps"},
    "C_side": {"view": {"az": 90, "el": 4, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
               "caption": "TAILGATE: side, wearer's right",
               "sub": "Tripod under 2 side straps (cam cup at its foot); lid straps wrap to gusset loops"},
    "C_open": {"view": {"az": -14, "el": 16, "zoom": 1.0}, "state": {"mannequin": True, "full": True},
               "caption": "TAILGATE: lid down, the whole aft face open",
               "sub": "Hinged at the floor seam; floor to z 650 open full width (286-353 mm at IM1-IM3); kill kit on the lid"},
    "C_zip": {"view": {"az": -42, "el": 10, "zoom": 1.0, "box": [80, 120, 380, 330, 460, 760]},
              "state": {"lid": True},
              "caption": "TAILGATE: the zip never carries the bag",
              "sub": "Sliders parked in the top-right garage; H3 bridges the corner zip from gusset loop to lid; camo flap over the leg"},
    "C_meat": {"view": {"az": -30, "el": 18, "zoom": 1.0}, "state": {"mannequin": True, "full": True, "lid": True},
               "caption": "TAILGATE: meat in the bag, loaded through the open face",
               "sub": "Boned quarter cinched to the frame panel by IM1-IM3, nothing to lift over a sill; then H1-H3, then zip"},
}


# ------------------------------------------------------------------------------------------------ the skin
def sim_dir():
    if os.environ.get("TG_SIMDIR"):                    # dev override (same mesh: same pieces, same h)
        return SIM / os.environ["TG_SIMDIR"], "fine" in os.environ["TG_SIMDIR"]
    f = SIM / "bagC_tg_PR19_fine"
    return (f, True) if (f / "x_packed.npy").exists() else (SIM / "bagC_tg_PR19", False)


def skin():
    import tailgate_clothsim as TC
    TC.install()
    from huntkit.clothsim.pack import PackModel, load_scenario
    d, fine = sim_dir()
    pm = PackModel(load_scenario(str(SCEN)), fine=fine, verbose=False)
    m = pm.mesh
    x = np.load(d / "x_packed.npy")
    uv = np.zeros((m.n, 2))
    for p in m.pieces:
        uv[p.gid] = p.xy
    sk = {"X": x, "X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    return VC.Skin(sk), d.name


def _rot_open(P, hinge_y, hinge_z, deg=OPEN_DEG):
    """Rotate about the hinge line (x axis through (y, z)); +z swings to +y (aft) and on down."""
    th = np.radians(deg)
    P = np.atleast_2d(np.asarray(P, float)).copy()
    dy, dz = P[:, 1] - hinge_y, P[:, 2] - hinge_z
    P[:, 1] = hinge_y + dy * np.cos(th) + dz * np.sin(th)
    P[:, 2] = hinge_z - dy * np.sin(th) + dz * np.cos(th)
    return P


def _rot_vec(N, deg=OPEN_DEG):
    th = np.radians(deg)
    N = np.atleast_2d(np.asarray(N, float)).copy()
    y, z = N[:, 1].copy(), N[:, 2].copy()
    N[:, 1] = y * np.cos(th) + z * np.sin(th)
    N[:, 2] = -y * np.sin(th) + z * np.cos(th)
    return N


def _xform(mesh, f):
    m = mesh.copy()
    m.vertices = f(np.asarray(m.vertices))
    return m


# ------------------------------------------------------------------------------------------------ the parts
def tailgate_parts(params):
    import tailgate as TG
    BC, CO = VC._concept()
    c = CO.make()
    S, simname = skin()
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    Z0 = float(BC.Z0)
    piece = S.piece
    lid_m = piece == "B-02L"
    floor_m = piece == "B-05"
    body_m = ~(lid_m | floor_m)
    parts = []
    a0 = a_of(Z0)

    # ---- kick plate (camo) on the gussets (z0 + 70) and as a chevron on the lid bottom
    def kick_line(x0):
        x, y, z = x0
        if y < yf_of(z) + 4:
            return Z0 - 60.0
        if y > yb_of(z) - 4:
            return Z0 + 70 + 70 * (1 - min(abs(x) / a0, 1.0))
        return Z0 + 70.0
    fk_all = np.array([z - kick_line(x0) for x0, z in zip(S.x0, S.x0[:, 2])])
    Vk, Ak, Fneg, Fpos, cut = VC.split_by_field(S.V, S.F[body_m], {"uv": S.uv}, fk_all)
    parts.append(Part("tg_body", VC._sub(Vk, Fpos, Ak["uv"]), "body", "bag", modes=BAGM, explode=BE, floats=True,
                      label=f"TAILGATE main bag (cloth-sim drape of the flat pieces, packed, 19 in, {simname})"))
    parts.append(Part("tg_kick_sides", VC._sub(Vk, Fneg, Ak["uv"]), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Kick plate SH-01b (camo)"))
    VL, AL, FLn, FLp, _ = VC.split_by_field(S.V, S.F[lid_m], {"uv": S.uv}, fk_all)
    lid_body = VC._sub(VL, FLp, AL["uv"])
    lid_kick = VC._sub(VL, FLn, AL["uv"])
    floor = S.submesh(floor_m)
    parts.append(Part("tg_bottom", floor, "tpu", "bag", modes=BAGM, explode=(0, 260, -40), floats=True,
                      label="Bottom B-05 (500D)"))
    # ---- seams (piping) except the zip
    ch = VC.seam_chains(S.F, piece)
    zip_keys = {frozenset(("B-02L", "B-03R")), frozenset(("B-02L", "B-03L")), frozenset(("B-02L", "B-02h"))}
    hinge_key = frozenset(("B-02L", "B-05"))
    tubes = []
    for key, chains in ch.items():
        if key in zip_keys or key == hinge_key:
            continue
        for cc in chains:
            if len(cc) > 3:
                q, _ = S.project(VC.smooth_line(S.V[cc], 4.0, 10.0), 1.2)
                tubes.append(G.tube(q, 2.1, n=8))
    parts.append(Part("tg_seams", G.concat(tubes), "trim", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Seared body seams"))
    # ---- zip line (lid | gusset R, band, gusset L), ordered right foot -> left foot
    segs = []
    for key in (frozenset(("B-02L", "B-03R")), frozenset(("B-02L", "B-02h")), frozenset(("B-02L", "B-03L"))):
        for cc in ch.get(key, []):
            if len(cc) > 2:
                segs.append(S.V[cc])
    ZP = VC.join_chains(segs, tol=40.0)
    if ZP[0, 0] < ZP[-1, 0]:
        ZP = ZP[::-1]
    ZP = VC.smooth_line(ZP, 3.0, 8.0)
    zq, zn = S.project(ZP, 1.0)
    dz = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(zq, axis=0), axis=1))])
    tape = G.ribbon(zq, 15.0, 1.0, zn, step=3.0)
    coil = G.tube(zq + zn * 1.0, 2.1, n=8)
    parts.append(Part("tg_zip", G.concat([tape, coil]), "hardware", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="rolled", label=f"#10 coil zip, inverted U ({TG.LID['z_top']:.0f} top run), closed"))
    # gusset half of the zip (visible with the lid down)
    parts.append(Part("tg_zip_body_half", G.tube(zq + zn * 0.6, 2.3, n=8), "hardware", "bag", modes=BAGM, explode=BE,
                      floats=True, variant="full", label="Body half of the #10 zip"))
    # ---- storm flaps: camo strips on the gusset side of each leg (lie over the coil), 330D over the top run
    zt = TG.LID["z_top"] - TG.LID["r"]
    flaps = []
    for side in (1, -1):
        leg = zq[(np.sign(zq[:, 0]) == side) & (zq[:, 2] < zt - 4)]
        leg = leg[np.argsort(leg[:, 2])]
        if len(leg) < 5:
            continue
        leg = VC.smooth_line(leg, 4.0, 6.0)
        q, n = S.project(leg)
        # flap centre 12 mm onto the gusset (towards the frame), width 35, 2.4 mm proud
        tdir = VC._unit(np.gradient(q, axis=0))
        inward = VC._unit(np.cross(n, tdir) * side * -1)
        inward = np.where((inward[:, 1:2] < 0), inward, -inward)        # points forward (-y): onto the gusset
        Pq = q + inward * 9.0
        Pq, nn = S.project(Pq, 2.6)
        flaps.append(G.ribbon(Pq, TG.FLAP_W, 1.1, nn, step=4.0))
    parts.append(Part("tg_flaps", G.concat(flaps), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Corner storm flaps SH-09 (camo, 35 mm) over the zip legs"))
    # ---- sliders parked closed at the top-right arc + garage + cord pulls
    i_top = int(np.argmin(np.abs(zq[:, 0] - (a_of(650) - 75.0)) + 1e3 * (zq[:, 2] < zt)))
    sl, pulls = [], []
    for off in (-14, 14):
        i = int(np.clip(i_top + int(off / 3), 1, len(zq) - 2))
        t = zq[i + 1] - zq[i - 1]
        p, nn = zq[i], zn[i]
        sl.append(VC._block(p + nn * 3.5, (24, 13, 6), e=0.35, R=VC._frame(nn, t)))
        down = VC._unit(np.array([0, 0, -1.0]) - np.dot([0, 0, -1.0], nn) * nn)
        side = np.cross(nn, down)
        base = p + nn * 6.0
        loop = np.array([base, base + down * 18 + side * 6 + nn * 3, base + down * 40 + nn * 5,
                         base + down * 18 - side * 6 + nn * 3])
        pulls.append(G.tube(G.catmull_rom(loop, 8, closed=True), 1.5, n=6))
        pulls.append(G.capsule_between(base + down * 34 + nn * 6, base + down * 60 + nn * 7, 4.2))
    parts.append(Part("tg_sliders", G.concat(sl), "aluminium", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="rolled", label="2 sliders, parked closed at the top-right corner"))
    parts.append(Part("tg_pulls", G.concat(pulls), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="rolled", label="3 mm cord pulls in rubber sleeves"))
    gar = VC.patch(S, zq[i_top] + np.array([0, 0, 6.0]), 54, 72, lift=3.4, thick=1.4)
    parts.append(Part("tg_garage", gar, "camo", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                      label="Slider garage SH-07 (camo)"))

    # ---- lid (closed) and lid (open)
    parts.append(Part("tg_lid", lid_body, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                      label="Tailgate lid B-02L (closed)"))
    parts.append(Part("tg_lid_kick", lid_kick, "camo", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                      label="Kick plate SH-01a (camo chevron on the lid)"))
    hc = ch.get(hinge_key, [])
    H = np.vstack([S.V[cc] for cc in hc]) if hc else S.V[np.unique(S.F[lid_m])][S.V[np.unique(S.F[lid_m])][:, 2] < Z0 + 8]
    hy, hz = float(np.median(H[:, 1])) + 1.0, float(np.median(H[:, 2]))
    rot = lambda P: _rot_open(P, hy, hz)                                       # noqa: E731
    lidm = S.submesh(lid_m)
    vn = VC._vnormals(lidm)
    Vo = rot(np.asarray(lidm.vertices))
    No = _rot_vec(vn)
    uvl = lidm.metadata["uv"]
    outer = G._mesh(Vo - No * 0.0, lidm.faces, uvl, flip_if_negative=False)
    inner = G._mesh(Vo - No * 2.0, lidm.faces[:, ::-1], uvl, flip_if_negative=False)
    parts.append(Part("tg_lid_open", outer, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Tailgate lid down (rotated about the floor hinge seam)"))
    parts.append(Part("tg_lid_open_lining", inner, "tpu", "bag", modes=BAGM, explode=BE, floats=True,
                      variant="full", label="Lid inside face"))
    # zip half on the lid rim
    rim = rot(zq + zn * 0.2)
    parts.append(Part("tg_lid_open_rim", G.tube(rim, 2.4, n=8), "hardware", "bag", modes=BAGM, explode=BE,
                      floats=True, variant="full", label="Lid half of the #10 zip"))
    # IMP-4 kill-kit pocket on the lid inside (200 x 280, z 300-580 on the closed lid), with its #5 zip
    pc = np.array([0.0, yb_of(440.0), 440.0])
    pocket = VC.patch(S, pc, 200, 280, lift=-4.0, thick=16.0)
    pocket = _xform(pocket, rot)
    pz = np.array([[x, yb_of(570.0), 570.0] for x in np.linspace(-85, 85, 30)])
    pzq, pzn = S.project(pz, -21.0)
    pzip = G.tube(rot(pzq), 1.6, n=6)
    parts.append(Part("tg_imp4", pocket, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="IMP-4 kill-kit / first-aid pocket, inside the lid"))
    parts.append(Part("tg_imp4_zip", pzip, "hardware", "bag", modes=BAGM, explode=BE, floats=True, variant="full"))
    # inside of the bag
    inside = S.submesh(~lid_m)
    lin = G._mesh(inside.vertices - 1.8 * VC._vnormals(inside), inside.faces[:, ::-1], inside.metadata["uv"],
                  flip_if_negative=False)
    parts.append(Part("tg_lining", lin, "tpu", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="Inside of the bag"))

    # ---- lid straps H1-H3 (gusset loop R -> across the lid -> gusset loop L) and side straps
    hst, hhw, loops, hang = [], [], [], []
    for z in TG.HOOP_Z:
        a, yb = a_of(z), yb_of(z)
        P0 = np.array([[a, yb - TG.LOOP_IN_MM - 8, z], [a + 2, yb - 4, z], [a - 6, yb + 2, z]] +
                      [[x, yb + 2, z] for x in np.linspace(a - 30, -(a - 30), 24)] +
                      [[-(a - 6), yb + 2, z], [-(a + 2), yb - 4, z], [-a, yb - TG.LOOP_IN_MM - 8, z]])
        Pp = np.array([S.on(p)[0][0] for p in P0])
        rib, P, n = VC.strap(S, Pp, clear=3.0, sigma=8.0)
        hst.append(rib)
        t0, t1 = P[1] - P[0], P[-1] - P[-2]
        hhw.append(VC.g_hook(P[2] + n[2] * 3.0, n[2], -t0))
        hhw.append(VC.ladder_lock(P[-4] + n[-4] * 3.5, n[-4], t1))
        for sx in (1, -1):
            lp = S.on([sx * a, yb - TG.LOOP_IN_MM - 6, z])[0][0]
            loops.append(VC.patch(S, lp, 26, 30, lift=1.6, thick=2.2))
        # open state: unhooked at the right, hanging from the left loop
        L0 = S.on([-a, yb - TG.LOOP_IN_MM - 6, z])[0][0]
        hp = np.array([L0, L0 + [-6, 22, -10], L0 + [-10, 40, -80], L0 + [-12, 52, -220], L0 + [-12, 58, -380]])
        hp = G.catmull_rom(hp, 10)
        nh = np.tile([-1.0, 0, 0], (len(hp), 1))
        hang.append(G.ribbon(hp, 25.0, 1.6, nh, step=4.0))
        hang.append(VC.g_hook(hp[-3] + [-2.0, 0, 0], np.array([-1.0, 0, 0]), hp[-1] - hp[-6]))
    side_st, side_hw = [], []
    for sx in (1, -1):
        for z in TG.SIDE_Z:
            a, yf, yb = a_of(z), yf_of(z), yb_of(z)
            P0 = np.array([[sx * a, y, z + 0.0] for y in np.linspace(yf + 8, yb - TG.LOOP_IN_MM - 10, 18)])
            Pp = np.array([S.on(p)[0][0] for p in P0])
            push = None
            if sx == 1:
                tg = TRIPOD
                def push(P, tg=tg):                                           # noqa: E306
                    d = np.hypot(P[:, 0] - tg["x"], P[:, 1] - tg["y"])
                    m = d < tg["R"] + 2.5
                    if m.any():
                        v = np.column_stack([P[m, 0] - tg["x"], P[m, 1] - tg["y"]]) / d[m, None]
                        P[m, 0] = tg["x"] + v[:, 0] * (tg["R"] + 2.5)
                        P[m, 1] = tg["y"] + v[:, 1] * (tg["R"] + 2.5)
                    return P
            rib, P, n = VC.strap(S, Pp, clear=2.5, sigma=10.0, extra_push=push)
            side_st.append(rib)
            side_hw.append(VC.ladder_lock(P[-3] + n[-3] * 3.5, n[-3], P[-1] - P[-4]))
    parts += [Part("tg_lid_straps", G.concat(hst), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                   variant="rolled", label="Lid straps H1-H3 (25 mm) at z 190 / 330 / 520: carry the lid's hoop load"),
              Part("tg_lid_strap_hw", G.concat(hhw), "aluminium", "bag", modes=BAGM, explode=BE, floats=True,
                   variant="rolled", label="G-hook (right) + ladder lock (left)"),
              Part("tg_lid_straps_hanging", G.concat(hang), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                   variant="full", label="H1-H3 unhooked, hanging from the left loops"),
              Part("tg_loops", G.concat(loops), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                   label="Gusset loops (6), 15 mm forward of the zip"),
              Part("tg_side_straps", G.concat(side_st), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                   label="Side straps (2 a side), frame-corner seam to the gusset loops"),
              Part("tg_side_hw", G.concat(side_hw), "hardware", "bag", modes=BAGM, explode=BE, floats=True)]
    # ---- tripod under the right side straps
    tri_m, tri_rub = VC._tripod(TRIPOD)
    parts.append(Part("tg_tripod", tri_m, "carbon", "bag", modes=BAGM, floats=True, variant="lid",
                      label="Tripod under the right side straps"))
    parts.append(Part("tg_tripod_parts", tri_rub, "hardware", "bag", modes=BAGM, floats=True, variant="lid"))
    # ---- IMP-1 scope sleeve on the left gusset (a padded pillow over the 85 mm spotter)
    parts += scope_sleeve(S, a_of, yf_of, yb_of)
    # ---- B-22 tabs, roll-top, pouch, IM straps, top guys (as CORRIE, on this skin)
    tabs = [VC.patch(S, S.on([sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z])[0][0], 34, 46, lift=1.4, thick=1.6)
            for sx in (1, -1)]
    parts.append(Part("tg_b22", G.concat(tabs), "hypalon", "bag", modes=BAGM, explode=BE, floats=True,
                      label="B-22 guy tabs at z 695 on the hinge band"))
    roll_line, roll, spiral, rstraps, rhw, clip_paths = VC._rolltop(S, c, a_of, yf_of, yb_of)
    parts += [Part("tg_roll", roll, "body", "bag", modes=BAGM, explode=BE, floats=True, label="Roll-top closed"),
              Part("tg_roll_ends", spiral, "trim", "bag", modes=BAGM, explode=BE, floats=True),
              Part("tg_roll_straps", G.concat(rstraps), "webbing", "bag", modes=BAGM, explode=BE, floats=True),
              Part("tg_roll_buckles", G.concat(rhw), "hardware", "bag", modes=BAGM, explode=BE, floats=True)]
    pe = (0, 200, 160)
    pm, pcamo, ptrim, pzip2, pzhw, pstr, phw, ptab = VC._pouch(S, CO.POUCH, roll_line, clip_paths, yf_of, pull_tab=True)
    parts += [Part("tg_pouch", pm, "body", "bag", modes=BAGM, explode=pe, floats=True, label="Top pouch 2.7 L"),
              Part("tg_pouch_top", pcamo, "body", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_tab", ptab, "camo", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_seams", ptrim, "trim", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_zip", pzip2, "hardware", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_pull", pzhw, "webbing", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_straps", G.concat(pstr), "webbing", "bag", modes=BAGM, explode=pe, floats=True),
              Part("tg_pouch_hooks", G.concat(phw), "aluminium", "bag", modes=BAGM, explode=pe, floats=True)]
    ims, imh = [], []
    for zs in (190.0, 330.0, 520.0):
        pts0 = np.array([[x, yf_of(zs) + 2, zs] for x in np.linspace(-120, 120, 25)])
        q, nn = S.on(pts0, -7.0)
        q = VC.smooth_line(q, 4.0, 8.0)
        _, nn = S.project(q)
        ims.append(G.ribbon(q, 38.0, 1.8, -nn, step=4.0))
        for k in (0, -1):
            t = q[1] - q[0] if k == 0 else q[-1] - q[-2]
            imh.append(VC.g_hook(q[k] - nn[k] * 3, -nn[k], t))
    parts.append(Part("tg_im_straps", G.concat(ims), "meat_strap", "bag", modes=BAGM, floats=True, variant="full",
                      label="IM1-IM3 internal meat straps (38 mm)"))
    parts.append(Part("tg_im_hooks", G.concat(imh), "aluminium", "bag", modes=BAGM, floats=True, variant="full"))
    gu = []
    for sx in (1, -1):
        A = np.array([sx * 95.0, 21.7, 702.6 + 6])
        Bp, nB = S.on([sx * CO.B22_X, yb_of(CO.B22_Z), CO.B22_Z], 3.0)
        sd, _ = S.on([sx * a_of(700), 0.5 * (yf_of(700) + yb_of(700)), 705], 4.0)
        pts = np.array([A, A + [sx * 40, 4, 2], sd[0], Bp[0] + [0, -14, 0], Bp[0]])
        rib, Pg, ng = VC.strap(S, G.catmull_rom(pts, 10), clear=2.5, sigma=14.0)
        gu.append(rib)
    parts.append(Part("tg_top_guys@t19", G.concat(gu), "webbing", "attach", torso=19.0, modes=("pack",),
                      label="Top guys: crown hood ears -> B-22 (fixed length)"))
    return parts, S, {"sim": simname, "hinge_y": hy, "hinge_z": hz}


TRIPOD = {}


def scope_sleeve(S, a_of, yf_of, yb_of):
    """IMP-1 on the left gusset: 160 mm between its 2 sewn lines, z 165-595; the 85 mm spotter makes a ~95 mm pillow."""
    zz = np.linspace(165, 595, 44)
    us = np.linspace(-1, 1, 25)
    P = np.zeros((len(us), len(zz), 3))
    Nn = np.zeros_like(P)
    for j, z in enumerate(zz):
        yc = yf_of(z) + 0.48 * (yb_of(z) - yf_of(z))
        for i, u in enumerate(us):
            q, n = S.on([-a_of(z), yc + 80 * u, z])
            P[i, j], Nn[i, j] = q[0], n[0]
    ends = np.clip(np.minimum((zz - 165) / 70, (595 - zz) / 45), 0, 1) ** 0.6
    bulge = (1 - us[:, None] ** 2).clip(0) ** 0.55 * 92.0 * ends[None, :] + 1.5
    Top = P + Nn * bulge[..., None]
    Bot = P + Nn * 0.8
    U, Vv = np.meshgrid(us * 80 / G.TILE_MM, zz / G.TILE_MM, indexing="ij")
    sl = VC._slab(Bot, Top, U, Vv)
    # shock-cord mouth
    mouth = Top[:, -1] + Nn[:, -1] * 0.5
    cord = G.tube(VC.smooth_line(mouth, 3.0, 4.0), 2.0, n=6)
    cl = VC._block(mouth[len(mouth) // 2] + [0, 0, 8], (14, 10, 22), e=0.4)
    return [Part("tg_imp1_sleeve", sl, "body", "bag", modes=BAGM, explode=BE, floats=True,
                 label="IMP-1 padded scope sleeve on the left gusset (85 mm spotter inside)"),
            Part("tg_imp1_cord", G.concat([cord, cl]), "trim", "bag", modes=BAGM, explode=BE, floats=True)]


def meat_parts(pack, S):
    """Mode A (meat in bag): the frame_haul quarter proxy and its IM straps, moved onto B-01 inside the bag."""
    out = []
    f_m = S.piece == "B-01"
    yB = float(np.median(S.V[np.unique(S.F[f_m])][:, 1]))
    for nm, lab in (("quarter_proxy", "Boned quarter in a game bag, inside the bag on B-01"),
                    ("quarter_bone", None), ("meat_straps", "IM1-IM3 over the quarter (38 mm)"),
                    ("meat_hardware", None)):
        p = next((q for q in pack.parts if q.name == nm), None)
        if p is None:
            continue
        V = np.asarray(p.mesh.vertices)
        dy = (yB + 4.0) - V[:, 1].min() if nm.startswith("quarter") else None
        out.append((nm, p, lab))
    q0 = next(p for n, p, _ in out if n == "quarter_proxy")
    Vq = np.asarray(q0.mesh.vertices)
    lo, hi = Vq.min(0), Vq.max(0)
    print("quarter bbox FCS", lo.round(0), hi.round(0))
    d = np.array([-(lo[0] + hi[0]) / 2, (yB + 4.0) - lo[1], 72.0 - lo[2]])
    res = []
    for nm, p, lab in out:
        m = p.mesh.copy()
        m.vertices = np.asarray(m.vertices) + d
        res.append(Part(f"tg_meat_{nm}", m, p.material, "bag", modes=BAGM, floats=True, variant="lid",
                        label=lab or ""))
    return res


DROP_PREFIX = ("corrie_", "imp1_", "imp4_", "imp8_", "imp2_port")


def tailgate_pack(params):
    from huntkit.viz3d.corrie_b2 import corrie_b2_pack
    pack = corrie_b2_pack(params)
    keep = [p for p in pack.parts if not p.name.startswith(DROP_PREFIX) or p.name == "corrie_float_wraps_g170"]
    S0, _ = skin()
    BC, CO = VC._concept()
    c = CO.make()
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    TRIPOD.clear()
    TRIPOD.update(VC._tripod_axis(S0, a_of, yf_of, yb_of))
    tp, S, info = tailgate_parts(params)
    pack.parts = keep + tp + (meat_parts(pack, S) if os.environ.get("TG_MEAT") else [])
    pack.metrics["bag_type"] = "tailgate_bagC"
    pack.metrics.update(info)
    return pack


def model():
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = tailgate_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    stem = "tailgate_meat" if os.environ.get("TG_MEAT") else "tailgate"
    glb, _ = export_glb(pack, OUT / f"{stem}.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m.get("torsos", {}).items()}
    html = build_html(glb, manifest(pack), m, info, OUT / f"{stem}_viewer.html", title="Pack 5200 TAILGATE (team C)")
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    print("GLB", glb, "HTML", html, {k: pack.metrics.get(k) for k in ("sim", "hinge_y", "hinge_z")})


if __name__ == "__main__":
    if "--model" in sys.argv:
        model()
