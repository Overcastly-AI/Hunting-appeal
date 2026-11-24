"""BL-066: CF-LITE rework on a buildable model (review 7 B1, B2, M1-M4, m3, m4, m5, m8, m10).

CF-LITE (BL-061, ``frame_iter1.build('cflite')``) was checked as one printed body: the part gaps cut only the stay
column, so the printed P1 / P2 / P3 touched each other outside the tubes and the load skipped the bonds (B1). Here:

1. **Parts.** Real part-boundary surfaces: the planes z 193 (P1 | P2) and z 469 (P2 | P3) through EVERY printed voxel
   (a 2 mm voxel layer, ``GAP_Z``), so only the carbon tubes (and the bonds) join the parts. P1's bore is a closed
   sleeve over the whole tube length it holds (z 30-190; it is one printed part, slip fit between the bond bands), so
   the z 110 shoulder-strap anchor pads stay on P1. The z 420 wing-lash pads (which BL-068 now loads with W2) sat on
   the bare tube; they become a bonded collar of P2 (z 411-429, joined to the upper branch, which runs beside the tube
   there). Any printed voxel not 26-connected to its part is deleted and reported (crumbs). ``parts_report`` / ``tests/test_bl066_cflite.py`` prove the printed parts are
   separate components (26-connectivity, i.e. no shared FE node).
2. **Exported geometry.** Each part is exported as an STL (smooth surface of the part's voxels, exact tube bore with
   the bondline, flat part ends) and the check runs on the STLs RE-RASTERED on the H1 2 mm grid (RUBRIC 1).
3. **Bonds (B2, M1, M2, M3).** Transfer per sleeve from the tube resultants at the model's real ring forces (the FE
   ring's own physical stress x area, not strain x 75 GPa, which read 0.939 x); axial and torque parts kept apart:
   Volkersen with E t adherends for the axial shear, G t for the torque shear; combined at the peak as the vector sum
   (the two shears are orthogonal on the bond surface). Allowable 3.7 x 0.8 = 2.96 MPa (cited epoxy-on-PA floor, x hot
   / wet) until T6p-T reads. C8 (hipbelt-off, ultimate) needs peak >= 1.0 too (adhesive failure on PA: no
   redistribution credit). Fail-safe bolt: printed-sleeve bearing (37.6 MPa) and the tube's open hole. dN / dT per
   sleeve and the governing sets are written to the json for the T6p-T pass lines.
4. **Buckling (M4).** ``voxel_buckling`` eigen run with BL-065's supports and assumptions (crown held, member
   isolation), with the carbon ring at its own stiffness weight.

Run: ``python -m huntkit.gendesign.bl066_cflite [parts | check <variant> | eigen <variant> | report]``.
Record: ``designs/pack_5200/iter1/frame/bl066_cflite.{md,json}``; STLs ``designs/pack_5200/iter1/frame/print_cflite/``.
Units N, mm, MPa, g.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from . import frame_iter1 as FI

REPO = FI.REPO
PACK = FI.PACK
DESIGN = PACK / "iter1" / "frame"
STL_DIR = DESIGN / "print_cflite"
OUT = REPO / "outputs" / "iter1_frame" / "bl066"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261124_bl066_"
REC_JSON = DESIGN / "bl066_cflite.json"
REC_MD = DESIGN / "bl066_cflite.md"
H = FI.H
TUBE = FI.TUBE

# ------------------------------------------------------------------------------------------------ part geometry
GAP_Z = {"P1|P2": 193.0, "P2|P3": 469.0}           # voxel-layer centres of the part-boundary planes (2 mm gaps)
PARTS = ("P1", "P2", "P3")
P1_SLEEVE_Z = (30.0, 190.0)                        # P1 closed sleeve over the tube it holds
CLIPS: dict = {}                                   # separate bonded clips (none: the z 420 lash pads are a P2 collar)
MIN_KEEP_VOX = 1                                   # orphans (not 26-connected to their part, not a clip) are deleted

# ------------------------------------------------------------------------------------------------ bond inputs
# B2(c): cited epoxies on PA12 3.7 MPa (light_frame_architectures section 2; the 5.0 MPa top was a PU on MJF PA12), no
# MMA-on-PAHT-CF value: design 3.7 x 0.8 hot / wet = 2.96 MPa until T6p-T reads (ASSUMPTION BOND-PA-3.7).
BOND_DRY_MPA = 3.7
BOND_HOT_WET = 0.8
MMA_G = FI.MMA_G_MPA                               # 300 MPa (ASSUMPTION MMA-G)
G_PAHT = FI.E_PAHT / (2 * (1 + 0.35))              # 1430 MPa, isotropic with nu 0.35 (the FE's nu)
SLEEVE_T = FI.SLEEVE_R_OUT - TUBE["od"] / 2        # 3.0 mm printed sleeve wall over the tube
BEARING_PRINT = 47.0 * 0.8                         # 37.6 MPa: printed sleeve bearing floor (Z tensile x 0.8)
OPEN_HOLE_KD = 0.55                                # ASSUMPTION OHT: open-hole strength / unnotched, quasi-iso CFRP
FAILSAFE_BOLT_D = 4.0


def variant_defaults() -> dict:
    """The as-reviewed CF-LITE bond layout (frame_iter1 SLEEVES / BONDLINE / BOND_L), sleeve wall 3 mm."""
    return {"name": "cflite_p", "sleeve_t": SLEEVE_T,
            "sleeves": {"P1 lower node": {"bands": ((40.0, 80.0), (150.0, 190.0)), "bondline": 0.8},
                        "P2 lower-branch root": {"bands": ((196.0, 246.0),), "bondline": 0.5},
                        "P2 mid-bar knuckle": {"bands": ((312.0, 348.0),), "bondline": 0.5},
                        "P2 z 420 lash collar": {"bands": ((411.0, 429.0),), "bondline": 0.5, "sleeve_t": 4.0},
                        "P2 upper-branch root": {"bands": ((440.0, 466.0),), "bondline": 0.5},
                        "P3 top node": {"bands": ((472.0, 543.5),), "bondline": 0.8}},
            # fail-safe: P1 one Ti M4 cross bolt at z 60 across x (below every crown-leg position: leg bottom z 171 at
            # torso 15); P3: no cross bolt is possible (the crown leg slides through the tube bore at every torso
            # setting, z 171-601), so P3's fail-safe is two steel D4 dowel pins per side, each through the printed
            # sleeve and ONE tube wall (opposite walls), flush with the bore, the 18.0 bore reamed through after
            "failsafe": {"P1 lower node": {"kind": "bolt", "z": 60.0},
                         "P3 top node": {"kind": "pins"}}}


# sleeve -> (cut below, cut above) on bare tube; None = the tube's free end
def sleeve_cuts(v: dict) -> dict:
    return {"P1 lower node": (None, 192.0), "P2 lower-branch root": (192.0, 250.0),
            "P2 mid-bar knuckle": (306.0, 354.0), "P2 z 420 lash collar": (400.0, 434.0),
            "P2 upper-branch root": (434.0, 468.0), "P3 top node": (468.0, None)}


TUBE_CUTS = (192.0, 250.0, 306.0, 354.0, 400.0, 434.0, 468.0)


# ================================================================================================ parts
def part_of(cen: np.ndarray) -> np.ndarray:
    """0 = gap layer, 1 / 2 / 3 = P1 / P2 / P3 by the boundary planes."""
    z = cen[:, 2]
    lab = np.zeros(len(cen), np.int8)
    g1, g2 = GAP_Z["P1|P2"], GAP_Z["P2|P3"]
    lab[z < g1 - H / 2] = 1
    lab[(z > g1 + H / 2) & (z < g2 - H / 2)] = 2
    lab[z > g2 + H / 2] = 3
    return lab


def _label26(mask: np.ndarray):
    from scipy import ndimage
    g = FI._base()["dom"].grid
    lab, n = ndimage.label(g.to_array(mask), structure=np.ones((3, 3, 3), bool))
    return g.from_array(lab), n


def ring_mask(cen: np.ndarray, z0: float, z1: float, r_out: float) -> np.ndarray:
    r = FI.tube_axis_r(cen)
    return (r >= TUBE["od"] / 2 - 1e-6) & (r < r_out) & (np.abs(cen[:, 0]) > 95.0) & (cen[:, 2] >= z0) & \
        (cen[:, 2] <= z1)


def split(solid: np.ndarray, cf: np.ndarray, v: dict | None = None) -> dict:
    """Cut every printed voxel at the part boundaries; P1 closed sleeve; clips; orphans deleted.
    Returns {solid, printed, label (0 none, 1-3 parts, 10+k clip k), info}."""
    v = v or variant_defaults()
    c = FI._base()
    cen, dom = c["cen"], c["dom"]
    ok = dom.design() & ~dom.passive_void
    pr = solid & ~cf
    r_out = TUBE["od"] / 2 + v["sleeve_t"]
    # P1 is one closed sleeve (slip fit between the bands), every bonded length a full ring
    pr |= ring_mask(cen, *P1_SLEEVE_Z, r_out) & ok
    for sl, d in v["sleeves"].items():
        for z0, z1 in d["bands"]:
            pr |= ring_mask(cen, z0, z1, TUBE["od"] / 2 + d.get("sleeve_t", v["sleeve_t"])) & ok
    lab_part = part_of(cen)
    cut = pr & (lab_part == 0)
    pr &= lab_part > 0
    label = np.zeros(len(cen), np.int16)
    info = {"gap_voxels_cut": int(cut.sum()), "gap_g": round(float(cut.sum()) * H ** 3 * FI.RHO_PAHT, 1),
            "orphans": [], "clips": {}}
    clip_zone = np.zeros(len(cen), np.int16)
    for k, (nm, (z0, z1)) in enumerate(CLIPS.items()):
        clip_zone[(cen[:, 2] >= z0 - 1e-6) & (cen[:, 2] <= z1 + 1e-6) & (np.abs(cen[:, 0]) > 95.0)] = 10 + k
    for p in (1, 2, 3):
        m = pr & (lab_part == p)
        L, n = _label26(m)
        if n == 0:
            continue
        sizes = np.bincount(L[m])
        main = int(np.argmax(sizes))
        label[m & (L == main)] = p
        for k in range(1, n + 1):
            if k == main:
                continue
            mk = m & (L == k)
            cz = np.unique(clip_zone[mk])
            if cz.size == 1 and cz[0] >= 10:
                label[mk] = cz[0]
            else:
                info["orphans"].append({"part": f"P{p}", "voxels": int(mk.sum()),
                                        "g": round(float(mk.sum()) * H ** 3 * FI.RHO_PAHT, 2),
                                        "at_mm": [round(float(q), 1) for q in cen[mk].mean(axis=0)]})
    # clip rings: the clip pads + a full ring over the clip length, per side
    for k, (nm, (z0, z1)) in enumerate(CLIPS.items()):
        rr = ring_mask(cen, z0, z1, r_out) & ok
        label[rr & (label == 0)] = 10 + k
        for sd, sg in (("R", 1), ("L", -1)):
            mk = (label == 10 + k) & (np.sign(cen[:, 0]) == sg)
            info["clips"][f"{nm} {sd}"] = {"voxels": int(mk.sum()), "z": [z0, z1]}
    printed = label > 0
    out_solid = printed | cf
    return {"solid": out_solid, "printed": printed, "label": label, "info": info}


def separation(label: np.ndarray, cf: np.ndarray | None = None) -> dict:
    """Printed parts as FE bodies: 26-connected components of the printed voxels (tube left out). Each declared part
    must be exactly one component and no component may hold two parts."""
    pr = label > 0
    L, n = _label26(pr)
    rows = {}
    ok = True
    names = {1: "P1", 2: "P2", 3: "P3"}
    for k, nm in enumerate(CLIPS):
        names[10 + k] = nm
    for lab_v in np.unique(label[pr]):
        comps = np.unique(L[label == lab_v])
        nm = names.get(int(lab_v), str(lab_v))
        sides = {}
        for cc in comps:
            mixed = np.unique(label[L == cc])
            sides[int(cc)] = [names.get(int(x), str(x)) for x in mixed]
            if mixed.size != 1:
                ok = False
        rows[nm] = {"components": int(comps.size), "voxels": int((label == lab_v).sum()), "comp_parts": sides}
        # P1-P3 are one body each; a clip is one body per side
        if int(lab_v) < 10 and comps.size != 1:
            ok = False
        if int(lab_v) >= 10 and comps.size != 2:
            ok = False
    return {"n_components": int(n), "parts": rows, "separate": bool(ok)}


# ================================================================================================ export / re-raster
def part_meshes(label: np.ndarray, v: dict | None = None) -> dict:
    """STL per printed part: smooth surface of the part's voxels (2x up-sampled field, Taubin, as H1's export), then
    with manifold3d the exact tube bore (OD 22 + 2 x bondline where bonded, + 2 x 0.2 slip in P1 between the bands)
    and flat part ends at the boundary planes. Clips are exported per side."""
    import manifold3d as m3d
    from scipy import ndimage
    from .surface import _from_manifold, _to_manifold, field_to_mesh
    v = v or variant_defaults()
    c = FI._base()
    dom = c["dom"]
    out = {}
    names = {1: "P1", 2: "P2", 3: "P3"}
    for k, nm in enumerate(CLIPS):
        names[10 + k] = nm
    cen = c["cen"]
    for lab_v, nm in names.items():
        sides = [("", label == lab_v)] if lab_v < 10 else [(" R", (label == lab_v) & (cen[:, 0] > 0)),
                                                          (" L", (label == lab_v) & (cen[:, 0] < 0))]
        for sfx, m in sides:
            if not m.any():
                continue
            field = ndimage.zoom(dom.grid.to_array(m.astype(float)), 2, order=1)
            field = ndimage.gaussian_filter(field, 0.7)
            mesh = field_to_mesh(field, dom.h / 2, dom.grid.x0 - dom.h / 4, level=0.5, smooth_iters=10, upsample=1)
            man = _to_manifold(mesh)
            z0, z1 = float(cen[m, 2].min()) - H / 2, float(cen[m, 2].max()) + H / 2
            for sx in (1.0, -1.0):
                base = m3d.Manifold.cylinder(800.0, TUBE["od"] / 2 + 0.2, TUBE["od"] / 2 + 0.2, 96)
                man = man - base.translate((sx * TUBE["x"], TUBE["y"], -100.0))
                for sl, d in v["sleeves"].items():
                    for b0, b1 in d["bands"]:
                        if b1 < z0 - 1 or b0 > z1 + 1:
                            continue
                        rb = TUBE["od"] / 2 + d["bondline"]
                        cyl = m3d.Manifold.cylinder(b1 - b0, rb, rb, 96)
                        man = man - cyl.translate((sx * TUBE["x"], TUBE["y"], b0))
            # flat ends exactly on the boundary planes (gap 2 mm: the voxel layer)
            for zg in GAP_Z.values():
                slab = m3d.Manifold.cube((800.0, 800.0, H), center=True).translate((0.0, 0.0, zg))
                man = man - slab
            mm = _from_manifold(man)
            # keep the largest shell (the cuts can leave crumbs)
            parts = mm.split(only_watertight=False)
            if len(parts) > 1:
                vols = [abs(p.volume) for p in parts]
                mm = parts[int(np.argmax(vols))]
            out[nm + sfx] = mm
    return out


def raster(mesh) -> np.ndarray:
    """Element centres inside the mesh's section loops (even-odd), every voxel layer: bl058_frame.body_stl's rule."""
    from matplotlib.path import Path as MPath
    c = FI._base()
    cen = c["cen"]
    solid = np.zeros(len(cen), bool)
    lo, hi = mesh.bounds[0][2], mesh.bounds[1][2]
    zs = np.unique(np.round(cen[:, 2], 4))
    zs = zs[(zs >= lo - H) & (zs <= hi + H)]
    for z in zs:
        sel = np.where(np.isclose(cen[:, 2], z))[0]
        s = mesh.section(plane_origin=[0.0, 0.0, float(z) + 1e-4], plane_normal=[0.0, 0.0, 1.0])
        if s is None:
            continue
        k = np.zeros(sel.size, int)
        P = cen[sel, :2]
        for d in s.discrete:
            k += MPath(np.asarray(d)[:, :2]).contains_points(P)
        solid[sel] = (k % 2) == 1
    return solid


def rerastered(meshes: dict, cf: np.ndarray, v: dict | None = None) -> dict:
    """The exported parts re-rastered, plus the bond layer: element centres between the tube OD and the bore over each
    bonded band (the 0.5 / 0.8 mm bondline is below the 2 mm grid; the adhesive is carried in the first voxel layer
    as print: ASSUMPTION BONDLINE-VOXEL)."""
    v = v or variant_defaults()
    c = FI._base()
    cen = c["cen"]
    names = {"P1": 1, "P2": 2, "P3": 3}
    for k, nm in enumerate(CLIPS):
        names[nm] = 10 + k
    label = np.zeros(len(cen), np.int16)
    clash = 0
    for nm, mesh in meshes.items():
        lv = names[nm.split(" ")[0]]
        m = raster(mesh) & ~cf
        clash += int((m & (label > 0)).sum())
        label[m & (label == 0)] = lv
    r = FI.tube_axis_r(cen)
    first = (r >= TUBE["od"] / 2 - 1e-6) & (r < TUBE["od"] / 2 + H) & (np.abs(cen[:, 0]) > 95.0) & ~cf
    lab_part = part_of(cen)
    added = 0
    for sl, d in v["sleeves"].items():
        for b0, b1 in d["bands"]:
            m = first & (cen[:, 2] >= b0) & (cen[:, 2] <= b1) & (label == 0)
            lv = {"P1": 1, "P2": 2, "P3": 3}[sl[:2]]
            m &= lab_part == lv
            label[m] = lv
            added += int(m.sum())
    # raster crumbs: keep each part's largest FACE-connected (6) body. A voxel hanging on by an edge or a corner shares
    # 2 or 1 nodes: a hinge in the FE (BL-066 first eigen run: an 8-voxel toe of the L stay foot gave lam ~ 0)
    from scipy import ndimage
    g = FI._base()["dom"].grid
    crumbs = []
    for lv in np.unique(label[label > 0]):
        m = label == lv
        lab6, n = ndimage.label(g.to_array(m))
        L = g.from_array(lab6)
        if n > 1:
            sizes = np.bincount(L[m])
            main = int(np.argmax(sizes))
            for k in range(1, n + 1):
                if k != main:
                    mk = m & (L == k)
                    crumbs.append({"part": int(lv), "voxels": int(mk.sum()),
                                   "at_mm": [round(float(q), 1) for q in cen[mk].mean(axis=0)]})
                    label[mk] = 0
    return {"crumbs_deleted": crumbs, "label": label, "solid": (label > 0) | cf, "printed": label > 0, "raster_clash_voxels": clash,
            "bond_layer_voxels": added}


# ================================================================================================ concept
def build(v: dict | None = None, log=print, rebuild: bool = False) -> dict:
    """CF-LITE parts on the exported geometry: voxel split -> STLs -> re-raster -> FE body. Cached per variant."""
    import trimesh
    v = v or variant_defaults()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"body_{v['name']}.npz"
    if p.exists() and not rebuild:
        z = np.load(p, allow_pickle=True)
        con = {k: z[k] for k in ("solid", "weight", "cf", "printed", "core", "label", "label_vox")}
        con.update({"name": v["name"], "joint": False, "info": json.loads(str(z["info"]))})
        return con
    t0 = time.time()
    base = FI.build("cflite")
    cf = base["cf"]
    sp = split(base["solid"], cf, v)
    sep_vox = separation(sp["label"])
    log(f"  split: {sep_vox} ({time.time() - t0:.0f} s)")
    meshes = part_meshes(sp["label"], v)
    sd = STL_DIR / v["name"]
    sd.mkdir(parents=True, exist_ok=True)
    stl = {}
    for nm, m in meshes.items():
        fn = sd / f"cflite_{nm.replace(' ', '_')}.stl"
        m.export(fn)
        stl[nm] = {"file": str(fn.relative_to(REPO)), "watertight": bool(m.is_watertight),
                   "volume_mm3": round(float(m.volume), 0), "g": round(float(m.volume) * FI.RHO_PAHT, 1),
                   "faces": int(len(m.faces))}
    log(f"  exported {len(meshes)} STLs ({time.time() - t0:.0f} s)")
    # re-read from disk (the check runs on the files)
    meshes2 = {nm: trimesh.load(REPO / s["file"]) for nm, s in stl.items()}
    rr = rerastered(meshes2, cf, v)
    sep = separation(rr["label"])
    log(f"  re-rastered: {sep} ({time.time() - t0:.0f} s)")
    w = np.ones(len(cf), np.float32)
    w[cf] = base["weight"][cf]
    solid = rr["solid"]
    w[~solid] = 1.0
    info = {"split_voxel": sp["info"], "separation_voxel_model": sep_vox, "separation_rerastered": sep,
            "raster_crumbs_deleted": rr["crumbs_deleted"],
            "stl": stl, "raster_clash_voxels": rr["raster_clash_voxels"],
            "bond_layer_voxels": rr["bond_layer_voxels"],
            "voxels": {"voxel_model_printed": int(sp["printed"].sum()), "rerastered_printed": int(rr["printed"].sum()),
                       "in_both": int((sp["printed"] & rr["printed"]).sum())},
            "tube": base["info"]["tube"], "variant": v}
    con = {"name": v["name"], "solid": solid, "weight": w, "cf": cf.copy(), "printed": rr["printed"],
           "core": np.zeros(len(cf), bool), "label": rr["label"], "label_vox": sp["label"], "joint": False,
           "info": info}
    np.savez_compressed(p, solid=solid, weight=w, cf=con["cf"], printed=con["printed"], core=con["core"],
                        label=con["label"], label_vox=con["label_vox"], info=json.dumps(info, default=FI._jd))
    return con


# ================================================================================================ resultants (B2 b)
RES_CUTS = (60.0,) + TUBE_CUTS                     # z 60: the P1 fail-safe bolt station (open hole)


def make_resultants(weight: np.ndarray):
    """A ``frame_iter1.tube_resultants`` replacement that reads the tube resultants from the FE ring's OWN physical
    stress (strain x the ring's stiffness weight x E_PAHT) x voxel area: the forces the model's ring really carries.
    (frame_iter1 multiplied the strain by 75 GPa instead, which reads 75000 / (20.7 x 3860) = 0.939 x of them.)
    Rows per set: N, Mx (about x, from y lever), My, Vx, Vy, T (N, N mm)."""
    def tube_resultants(f: dict, cf_loc: np.ndarray, meta: list) -> dict:
        cen = f["cen"]
        wl = np.asarray(weight, float)[f["idx"]]
        out = {}
        a = H * H
        for sd, sg in (("R", 1.0), ("L", -1.0)):
            for zc in RES_CUTS:
                m = cf_loc & (np.sign(cen[:, 0]) == sg) & (np.abs(cen[:, 2] - (zc + 1.0)) < H / 2 + 1e-6)
                if m.sum() == 0:
                    continue
                dx = cen[m, 0] - sg * TUBE["x"]
                dy = cen[m, 1] - TUBE["y"]
                ww = wl[m][:, None]
                rows = []
                for S in f["stress"]:
                    s = S[m].astype(float) * ww           # f["stress"] here = phys / w (check's convention)
                    rows.append([float(s[:, 2].sum() * a), float((s[:, 2] * dy).sum() * a),
                                 float((s[:, 2] * dx).sum() * a), float(s[:, 5].sum() * a), float(s[:, 4].sum() * a),
                                 float((dx * s[:, 4] - dy * s[:, 5]).sum() * a)])
                out[f"{sd}|{zc:g}"] = np.array(rows)
        return out
    return tube_resultants


def tube_section_real() -> dict:
    ro, ri = TUBE["od"] / 2, TUBE["id"] / 2
    A = math.pi * (ro ** 2 - ri ** 2)
    I = math.pi / 4 * (ro ** 4 - ri ** 4)
    return {"A": A, "I": I, "J": 2 * I, "ro": ro, "t": ro - ri}


def tube_fi(N: float, M: float, T: float, V: float, holes: int = 0, d_hole: float = FAILSAFE_BOLT_D) -> float:
    """Max-stress FI of the real 22 x 18 tube from its resultants (beam theory): axial N / A + M ro / I, shear
    T ro / J + 2 V / A, knock-downs kept (Xt x 0.8, Xc x 0.8 x 0.65, S x 0.8). With ``holes`` (open holes of d_hole
    through the wall at the station): net section (A, I scaled by the lost wall) and the open-hole strength
    OPEN_HOLE_KD instead of the impact knock-down in compression (ASSUMPTION OHT)."""
    ts = tube_section_real()
    A, I, J, ro, t = ts["A"], ts["I"], ts["J"], ts["ro"], ts["t"]
    Xt = TUBE["Xt"] * TUBE["hot_wet"]
    Xc = TUBE["Xc"] * TUBE["hot_wet"] * TUBE["impact_c"]
    S = TUBE["S"] * TUBE["hot_wet"]
    if holes:
        f = 1 - holes * d_hole * t / A
        A, I, J = A * f, I * f, J * f
        Xt = TUBE["Xt"] * TUBE["hot_wet"] * OPEN_HOLE_KD
        Xc = TUBE["Xc"] * TUBE["hot_wet"] * min(OPEN_HOLE_KD, TUBE["impact_c"])
    st = N / A + abs(M) * ro / I
    sc = N / A - abs(M) * ro / I
    tau = abs(T) * ro / J + 2 * abs(V) / A
    return max(max(st, 0) / Xt, max(-sc, 0) / Xc) + (tau / S) ** 2


# ================================================================================================ bonds (B2, M1, M2, M3)
def volkersen_k(L: float, bondline: float, kind: str, sleeve_t: float = SLEEVE_T) -> float:
    """Peak / average shear of a tubular lap (Volkersen). kind 'axial': adherend stiffness E t (tube 75 GPa x 2 mm,
    sleeve E_PAHT x sleeve_t); 'torque': G t (tube 12 GPa x 2 mm, sleeve G_PAHT x sleeve_t)."""
    from huntkit.fea.joints import volkersen_factor
    t = (TUBE["od"] - TUBE["id"]) / 2
    if kind == "axial":
        a1, a2 = TUBE["E"] * t, FI.E_PAHT * sleeve_t
    elif kind == "torque":
        a1, a2 = TUBE["G"] * t, G_PAHT * sleeve_t
    else:
        raise ValueError(kind)
    om = math.sqrt(MMA_G / bondline * (1 / a1 + 1 / a2))
    return float(volkersen_factor(om * L, min(a1, a2) / max(a1, a2)))


def bond_stresses(dN: float, dT: float, L: float, k_ax: float, k_T: float) -> dict:
    """Average and peak bond shear (MPa) of a transfer dN (N) and dT (N mm) over a tubular bond of length L at the tube
    OD. Axial shear dN / (pi d L) and torque shear dT / (2 pi r^2 L) are orthogonal on the bond surface: combined as a
    vector, the peaks (both at the sleeve ends) likewise."""
    r = TUBE["od"] / 2
    ta = dN / (2 * math.pi * r * L)
    tt = dT / (2 * math.pi * r * r * L)
    return {"tau_ax": ta, "tau_T": tt, "avg": math.hypot(ta, tt), "peak": math.hypot(k_ax * ta, k_T * tt)}


ULTIMATE_CASES = ("hipbelt_off_abuse", "overload")


def bonds(name: str, v: dict | None = None, bases=FI.BASES, gw: float = 1.0, alt: str | None = None,
          walls: dict | None = None) -> dict:
    """Per sleeve, from the stored tube resultants (``make_resultants``): transfer dN / dT / dM per set; checks
    - avg: allowable / average >= 1 at the factored load (HA-LS-1);
    - peak: allowable / Volkersen peak >= 1 at LIMIT (factored / case factor) for limit cases, and at the factored load
      (= limit) for the ultimate cases C7 / C8 (M1: no redistribution credit on an adhesive-failure substrate);
    - fatigue: 1.6 g static-carry average <= 0.3 x dry;
    - bearing: bending into the sleeve, p = 6 dM / (d L_b^2) <= 37.6 MPa;
    - fail-safe (bond gone, at limit, factor 1.0): Ti M4 in P1 / 2 radial pins in P3: tube-wall bearing (250 MPa)
      and printed-sleeve bearing (37.6 MPa, M2), each wall / pin taking half the axial force plus the torque couple;
    - tube open hole at the fail-safe stations (M2).
    ``gw``: divide every model torque by gw (sensitivity: the voxel ring over-attracts torsion by GJ x 2.3).
    ``alt``: a second run of the same sets (``check_gj``): the torque per set is the lower of the two upper bounds;
    bases without an alt run keep the main torque.
    ``walls``: measured printed adherend per sleeve (``sleeve_walls``): the Volkersen adherend is
    max(design sleeve wall, measured mean).
    Returns per sleeve: margins with their governing set, and the largest limit transfers dN / dT (T6p-T)."""
    v = v or variant_defaults()
    allow = BOND_DRY_MPA * BOND_HOT_WET
    t_tube = (TUBE["od"] - TUBE["id"]) / 2
    out = {}
    cuts = sleeve_cuts(v)
    for sl, d in v["sleeves"].items():
        lo, hi = cuts[sl]
        bands = d["bands"]
        L = min(b1 - b0 for b0, b1 in bands)          # P1: one band takes all (ASSUMPTION P1-BANDS)
        Lb = max(b1 for _, b1 in bands) - min(b0 for b0, _ in bands)
        t_s = d.get("sleeve_t", v["sleeve_t"])
        if walls and sl in walls:
            t_s = max(t_s, walls[sl]["t_mean_mm"])
        k_ax = volkersen_k(L, d["bondline"], "axial", t_s)
        k_T = volkersen_k(L, d["bondline"], "torque", t_s)
        W = {}

        def keep(key, val, tag, extra=None):
            if key not in W or val < W[key]["margin"]:
                W[key] = {"margin": val, "where": tag, **(extra or {})}
        lim = {"dN_n": 0.0, "dT_nmm": 0.0, "dN_set": "", "dT_set": "", "dN_with_dT": 0.0, "dT_with_dN": 0.0,
               "fat_dN_n": 0.0, "fat_dT_nmm": 0.0, "c8_dN_n": 0.0, "c8_dT_nmm": 0.0,
               "factored_dN_n": 0.0, "factored_dT_nmm": 0.0, "factored_dN_set": "", "factored_dT_set": ""}
        fs = v["failsafe"].get(sl)
        for b in bases:
            p = FI.OUT / f"tube_{name}_{b}.npz"
            if not p.exists():
                continue
            z = np.load(p)
            meta = [json.loads(m) for m in z["meta"]]
            pa = FI.OUT / f"tube_{alt}_{b}.npz" if alt else None
            za = np.load(pa) if (pa is not None and pa.exists()) else None
            if za is not None and [json.loads(m)["set"] for m in za["meta"]] != [m["set"] for m in meta]:
                raise RuntimeError("alt run sets differ")
            for sd in ("R", "L"):
                A = z[f"{sd}_{lo:g}"] if lo is not None else np.zeros((len(meta), 6))
                B = z[f"{sd}_{hi:g}"] if hi is not None else np.zeros((len(meta), 6))
                dd = np.asarray(B) - np.asarray(A)
                if za is not None:
                    Aa = za[f"{sd}_{lo:g}"] if lo is not None else np.zeros((len(meta), 6))
                    Ba = za[f"{sd}_{hi:g}"] if hi is not None else np.zeros((len(meta), 6))
                    dT_alt = np.abs(np.asarray(Ba) - np.asarray(Aa))[:, 5]
                for i, mt in enumerate(meta):
                    fac = float(mt["factor"])
                    dN = abs(float(dd[i, 0]))
                    dT = abs(float(dd[i, 5])) / gw
                    if za is not None:
                        dT = min(dT, float(dT_alt[i]))
                    dM = float(np.hypot(dd[i, 1], dd[i, 2]))
                    tag = f"{b}|{sd}|{mt['set']}"
                    ultimate = fac <= 1.0
                    st = bond_stresses(dN, dT, L, k_ax, k_T)
                    keep("avg", allow / max(st["avg"], 1e-9), tag)
                    pk_load = 1.0 if ultimate else fac            # peak judged at limit
                    keep("peak", allow / max(st["peak"] / pk_load, 1e-9), tag,
                         {"rule": "ultimate: peak at factored = limit (M1)" if ultimate else "limit"})
                    if mt["case"] == "hipbelt_off_abuse":
                        keep("peak_c8", allow / max(st["peak"], 1e-9), tag)
                        if dN > lim["c8_dN_n"]:
                            lim["c8_dN_n"] = dN
                        if dT > lim["c8_dT_nmm"]:
                            lim["c8_dT_nmm"] = dT
                    keep("bearing", BEARING_PRINT / max(6 * dM / (TUBE["od"] * Lb ** 2), 1e-9), tag)
                    if mt["case"] == "static_carry":
                        f16 = 1.6 / fac
                        keep("fatigue", 0.3 * BOND_DRY_MPA / max(st["avg"] * f16, 1e-9), tag)
                        lim["fat_dN_n"] = max(lim["fat_dN_n"], dN * f16)
                        lim["fat_dT_nmm"] = max(lim["fat_dT_nmm"], dT * f16)
                    if dN > lim["factored_dN_n"]:
                        lim.update(factored_dN_n=dN, factored_dN_set=tag)
                    if dT > lim["factored_dT_nmm"]:
                        lim.update(factored_dT_nmm=dT, factored_dT_set=tag)
                    # transfers at limit (the T6p-T pass lines; C7 / C8 are limit = factored)
                    dNl, dTl = dN / (1.0 if ultimate else fac), dT / (1.0 if ultimate else fac)
                    if dNl > lim["dN_n"]:
                        lim.update(dN_n=dNl, dN_set=tag, dT_with_dN=dTl)
                    if dTl > lim["dT_nmm"]:
                        lim.update(dT_nmm=dTl, dT_set=tag, dN_with_dT=dNl)
                    if fs:
                        Fw = math.hypot(dNl / 2, dTl / TUBE["od"])
                        fd = fs.get("d", FAILSAFE_BOLT_D)
                        n_fs = fs.get("n", 1)          # fail-safe elements in parallel per side (pairs of walls)
                        Fw = Fw / n_fs
                        keep("failsafe_tube_bearing", FI.TUBE_BEARING_MPA / max(Fw / (fd * t_tube), 1e-9), tag)
                        keep("failsafe_print_bearing", BEARING_PRINT / max(Fw / (fd * fs.get("print_t", t_s)), 1e-9),
                             tag)
        out[sl] = {"L_bond_mm": L, "L_bearing_mm": Lb, "bondline_mm": d["bondline"], "adherend_t_mm": round(t_s, 2),
                   "k_axial": round(k_ax, 2),
                   "k_torque": round(k_T, 2),
                   **{kk: {**vv, "margin": round(float(vv["margin"]), 3)} for kk, vv in W.items()},
                   "limit_transfer": {k: (round(v_, 1) if isinstance(v_, float) else v_) for k, v_ in lim.items()},
                   "failsafe": fs}
    return out


def tube_open_hole(name: str, v: dict | None = None, bases=FI.BASES) -> dict:
    """Tube with the fail-safe holes: P1 at z 60 (cut z 60), P3 pins at about z 508 (the tube resultant at z 468, the
    most it carries into P3, used as the bound). Requirement: FI x factor ... margin = 1 / FI at the factored load."""
    out = {}
    for st, cut in (("P1 bolt z 60", 60.0), ("P3 pins (bound: cut z 468)", 468.0)):
        best = (9e9, "")
        plain = (9e9, "")
        for b in bases:
            p = FI.OUT / f"tube_{name}_{b}.npz"
            if not p.exists():
                continue
            z = np.load(p)
            meta = [json.loads(m) for m in z["meta"]]
            for sd in ("R", "L"):
                key = f"{sd}_{cut:g}"
                if key not in z:
                    continue
                R = z[key]
                for i, mt in enumerate(meta):
                    N, M, V, T = R[i, 0], math.hypot(R[i, 1], R[i, 2]), math.hypot(R[i, 3], R[i, 4]), R[i, 5]
                    fi = tube_fi(N, M, T, V, holes=2)
                    fp = tube_fi(N, M, T, V, holes=0)
                    if 1 / fi < best[0]:
                        best = (1 / fi, f"{b}|{sd}|{mt['set']}")
                    if 1 / fp < plain[0]:
                        plain = (1 / fp, f"{b}|{sd}|{mt['set']}")
        out[st] = {"margin_open_hole": round(best[0], 3), "where": best[1], "margin_plain": round(plain[0], 3),
                   "where_plain": plain[1]}
    return out


def tube_beam_check(name: str, bases=FI.BASES) -> dict:
    """Tube strength from its resultants at every bare cut (beam theory on the real 22 x 18 section)."""
    best = (9e9, "")
    for b in bases:
        p = FI.OUT / f"tube_{name}_{b}.npz"
        if not p.exists():
            continue
        z = np.load(p)
        meta = [json.loads(m) for m in z["meta"]]
        for sd in ("R", "L"):
            for zc in TUBE_CUTS:
                R = z[f"{sd}_{zc:g}"]
                for i, mt in enumerate(meta):
                    fi = tube_fi(R[i, 0], math.hypot(R[i, 1], R[i, 2]), R[i, 5], math.hypot(R[i, 3], R[i, 4]))
                    if 1 / fi < best[0]:
                        best = (1 / fi, f"{b}|{sd}|z{zc:g}|{mt['set']}")
    return {"margin": round(best[0], 3), "where": best[1]}


# ================================================================================================ check
def check(v: dict | None = None, bases=FI.BASES, log=print, refresh: bool = False) -> dict:
    """frame_iter1.check (BL-058 whole-body rules) on the re-rastered parts, with the corrected tube resultants."""
    v = v or variant_defaults()
    con = build(v, log=log)
    old_tr, old_cuts = FI.tube_resultants, FI.TUBE_CUTS
    FI.tube_resultants = make_resultants(con["weight"])
    try:
        res = FI.check(v["name"], bases=bases, log=log, refresh=refresh, con=con)
    finally:
        FI.tube_resultants, FI.TUBE_CUTS = old_tr, old_cuts
    return res


# ================================================================================================ buckling (M4)
def eigen(v: dict | None = None, bases=("fine_sm8", "fine_sm8.cyc", "fine"), log=print, tube_real_E: bool = True,
          setdown: bool = True) -> dict:
    """BL-065's eigen readings (bl065_h1_buckling.run_basis / run_extra / run_setdown: same supports, crown brace, member
    isolation, H8 correction, screen) on the re-rastered CF-LITE parts. The carbon ring keeps its EI-matched weight;
    with ``tube_real_E`` it is divided by the PAHT buckling knock-down (0.6 hot x 0.7 creep: CFRP keeps its modulus),
    otherwise the knock-down is applied to the carbon too (conservative sensitivity)."""
    from . import bl065_h1_buckling as BK
    v = v or variant_defaults()
    con = build(v, log=log)
    w = con["weight"].astype(float).copy()
    if tube_real_E:
        w[con["cf"]] /= (0.6 * 0.7)
    tag = f"{v['name']}{'' if tube_real_E else '_kdtube'}"
    b = BK.body()
    out = {}
    for bs in bases:
        out[bs] = BK.run_basis(bs, b, con["solid"], tag=tag, log=log, weights=w)
        out[bs + "_extra"] = BK.run_extra(bs, b, con["solid"], tag=tag, log=log, weights=w)
        if setdown:
            out[bs + "_setdown"] = BK.run_setdown(bs, b, con["solid"], tag=tag, log=log, weights=w)
    return out


# ================================================================================================ BL-068 lash loads
LASH_JSON = PACK / "analysis" / "bl068_lash_loads.json"
LASH_FACTOR = 2.0          # ASSUMPTION W-FACTOR: the W wrap pull is a static strap load: HA-LS-1 C1 factor 2.0


def lash_check(solid: np.ndarray | None = None, weight: np.ndarray | None = None, tag: str = "h1",
               log=print) -> dict:
    """BL-068 levelled W straps: the wrap pulls (bl068_lash_loads.json, design 225 N per end, proof 337.5 N) applied
    to the lash pads of the body (nodes of the body within 8 mm of each lash point), hip boss clamped as the record
    solve, alone (the wraps' own pulls are near self-equilibrated). Load-patch and clamp elements are left out of the
    FI population, as the record check does. After (levelled) and before (helix) states.
    Margin = 1 / (FI of the 99th percentile printed voxel outside the load patches at LASH_FACTOR x design), FI
    by the record material rule (frame_comp_d.fi_material, PAHT-CF 88 / 47 MPa x 0.8); the max-voxel FI is reported
    too."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    d = json.loads(LASH_JSON.read_text())
    c = FI._base()
    dom, g = c["dom"], c["dom"].grid
    solid = FI.baseline_solid() if solid is None else solid
    with FI._ctx():
        from . import h1_sleeve as S
        sets = S.kit_sets("fine")
        _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    nc = g.node_coords()
    act = np.zeros(g.nn, bool)
    act[np.unique(g.enodes[solid])] = True
    vb = VoxelBuckler(g, solid, fixed, ft.NU, weights=weight)
    cen_a = g.elem_centers()[vb.ae]
    printed_a = np.ones(vb.ae.size, bool) if weight is None else (np.asarray(weight)[vb.ae] == 1.0)
    out = {"source": str(LASH_JSON.relative_to(REPO)), "factor": LASH_FACTOR, "states": {}}
    for state in ("after", "before"):
        F = np.zeros(g.ndof)
        patch = np.zeros(g.nn, bool)
        pts = {}
        for k, row in d[state].items():
            p = np.asarray(row["point_xyz_mm"], float)
            f = np.asarray(row["force_design_n"], float) * LASH_FACTOR
            n = np.where(act & (np.linalg.norm(nc - p, axis=1) <= 8.0))[0]
            if n.size == 0:
                raise RuntimeError(f"no body nodes at {k}")
            for i in range(3):
                F[3 * n + i] += f[i] / n.size
            patch[n] = True
            pts[k] = {"nodes": int(n.size), "F_factored_n": [round(float(q), 1) for q in f]}
        Sx = vb.prestress(F)[0]
        clamp = np.zeros(g.nn, bool)
        clamp[np.where(fixed[0::3])[0]] = True
        ex = (patch | clamp)[g.enodes[vb.ae]].any(axis=1) | (np.linalg.norm(
            cen_a[:, None, :] - np.array([r["point_xyz_mm"] for r in d[state].values()])[None], axis=2).min(axis=1)
            < 10.0)
        fi = D.fi_material(Sx[printed_a & ~ex].astype(float), D.MATERIALS[H1.MAT])
        k99 = float(np.percentile(fi, 99))
        kmax = float(fi.max())
        wi = int(np.argmax(fi))
        out["states"][state] = {"points": pts, "fi_p99": round(k99, 4), "fi_max": round(kmax, 4),
                                "margin_p99": round(1 / k99, 2), "margin_max": round(1 / kmax, 2),
                                "max_at_mm": [round(float(q), 1) for q in cen_a[printed_a & ~ex][wi]]}
        log(f"  lash {tag} {state}: margin p99 {1 / k99:.2f}, max {1 / kmax:.2f} at {out['states'][state]['max_at_mm']}")
    vb.free()
    return out


# ================================================================================================ sleeve wall (measured)
T_EFF_CAP = 10.0           # ASSUMPTION SHEAR-LAG: printed material beyond 10 mm off the bore is not counted as adherend


def sleeve_walls(label: np.ndarray, v: dict | None = None, sectors: int = 16) -> dict:
    """Printed adherend thickness over each bonded band, measured on the re-rastered body: per voxel layer and per
    angular sector about each tube axis, the contiguous printed depth from the tube OD outward (2 mm steps), capped at
    T_EFF_CAP; reported as the circumferential mean (used for the Volkersen adherend E t / G t) and the thinnest
    sector."""
    v = v or variant_defaults()
    c = FI._base()
    cen = c["cen"]
    pr = label > 0
    out = {}
    for sl, d in v["sleeves"].items():
        lv = {"P1": 1, "P2": 2, "P3": 3}[sl[:2]]
        rows = []
        for sd, sg in (("R", 1.0), ("L", -1.0)):
            dx = cen[:, 0] - sg * TUBE["x"]
            dy = cen[:, 1] - TUBE["y"]
            r = np.hypot(dx, dy)
            th = np.arctan2(dy, dx)
            near = (np.sign(cen[:, 0]) == sg) & (r < TUBE["od"] / 2 + T_EFF_CAP + H) & (r >= TUBE["od"] / 2 - 1e-6)
            for b0, b1 in d["bands"]:
                for z in np.unique(cen[near & (cen[:, 2] >= b0) & (cen[:, 2] <= b1), 2]):
                    lay = near & np.isclose(cen[:, 2], z)
                    for k in range(sectors):
                        a0 = -np.pi + 2 * np.pi * k / sectors
                        s = lay & (th >= a0) & (th < a0 + 2 * np.pi / sectors)
                        if not s.any():
                            continue
                        rr = np.sort(np.unique(np.round(r[s & pr & (label == lv)] / H)))
                        # contiguous from the first ring
                        t = 0.0
                        r0 = round((TUBE["od"] / 2 + 1.0) / H)
                        for q in rr:
                            if q <= r0 + t / H + 0.5:
                                t = (q - r0 + 1) * H
                            else:
                                break
                        rows.append(min(t, T_EFF_CAP))
        a = np.asarray(rows)
        out[sl] = {"t_mean_mm": round(float(a.mean()), 2), "t_p10_mm": round(float(np.percentile(a, 10)), 2),
                   "t_min_mm": round(float(a.min()), 2), "samples": int(a.size)}
    return out


# ================================================================================================ mass
RHO_MMA = 0.98e-3
RHO_STEEL = 7.85e-3


def h1_stl_in_grid_g() -> float:
    """The released H1 STL clipped to the FE grid's box (manifold3d intersection), g: the part of the print the voxel
    model (and the CF-LITE parts) covers; outside it (fairlead tops, US2 clevises, about 92 g) nothing changes."""
    import manifold3d as m3d
    import trimesh
    from .surface import _to_manifold
    g = FI._base()["dom"].grid
    nc = g.node_coords()
    lo, hi = nc.min(axis=0), nc.max(axis=0)
    box = m3d.Manifold.cube(tuple((hi - lo).tolist())).translate(tuple(lo.tolist()))
    return float((_to_manifold(trimesh.load(FI.STL)) ^ box).volume()) * FI.RHO_PAHT


def mass(con: dict, v: dict | None = None, extra_rows: dict | None = None) -> dict:
    """Frame-line mass on the EXPORTED parts: printed delta = the part STLs' exact volume - the H1 STL's exact volume
    inside the same grid box (both x 1.06 g/cm3), applied to the 1069.32 g released STL; plus tubes, bond (every band,
    both sides), fail-safe hardware (P1: Ti M4 x 30 cross bolt + nut per side; P3: 2 steel D4 x 6 flush dowel pins
    per side), less the z 234 joint hardware. The 2 mm raster delta (frame_iter1.mass's rule) is reported as a
    cross-check: the raster over-reads 3 mm walls and counts the bond layer voxels as print. ``extra_rows``: sizing
    changes (g)."""
    v = v or variant_defaults()
    s0 = FI.baseline_solid()
    vv = H ** 3
    g_raster = float(con["printed"].sum()) * vv * FI.RHO_PAHT
    g0 = float(s0.sum()) * vv * FI.RHO_PAHT
    g_stl = sum(r["g"] for r in con["info"]["stl"].values())
    g_h1box = h1_stl_in_grid_g()
    stl_g = json.loads((PACK / "analysis" / "bl058.json").read_text())["stl"]["h1_assembled"]["g"]
    ts = FI.tube_section()
    L = TUBE["z1"] - TUBE["z0"]
    bond_v = 2 * sum(math.pi * TUBE["od"] * (b1 - b0) * d["bondline"] for d in v["sleeves"].values()
                     for b0, b1 in d["bands"])
    bolt = math.pi / 4 * FAILSAFE_BOLT_D ** 2 * 30.0 * 4.43e-3 + 0.8
    pin = math.pi / 4 * FAILSAFE_BOLT_D ** 2 * 6.0 * RHO_STEEL
    j = json.loads((PACK / "analysis" / "frame_mass_h1.json").read_text())["h1"]["joint_hardware_g"]
    rows = {"print (released STL, bl058.json stl)": stl_g,
            "printed delta: P1 + P2 + P3 STLs - H1 STL inside the FE box (exact volumes)": round(g_stl - g_h1box, 1),
            f"2 carbon tubes 22 x 18 x {L:.0f} mm (record density)": round(2 * ts["g_per_mm"] * L, 1),
            "MMA bond, every band both sides (0.98 g/cm3)": round(bond_v * RHO_MMA, 1),
            "P1 fail-safe: 2 Ti M4 x 30 cross bolts + nuts (ASSUMPTION BOLT-G)": round(2 * bolt, 1),
            "P3 fail-safe: 4 steel D4 x 6 flush dowel pins": round(4 * pin, 1),
            "z 234 joint hardware deleted (frame_mass_h1.json)": -round(sum(j.values()), 1)}
    rows.update(extra_rows or {})
    total = round(sum(rows.values()), 1)
    fl0 = json.loads((PACK / "iter1" / "frame" / "frame_iter1.json").read_text())["frame_line_h1_g"]
    return {"rows": rows, "frame_print_g": total, "delta_g": round(total - stl_g, 1),
            "frame_line_g": round(fl0 + total - stl_g, 1), "frame_line_h1_g": fl0,
            "parts_stl_g": {k: r["g"] for k, r in con["info"]["stl"].items()},
            "h1_stl_in_box_g": round(g_h1box, 1),
            "cross_check_raster_delta_g": round(g_raster - g0, 1),
            "cross_check_bond_layer_voxels_g": round(con["info"]["bond_layer_voxels"] * vv * FI.RHO_PAHT, 1)}


def check_gj(v: dict | None = None, bases=("fine_sm8", "fine"), log=print) -> dict:
    """B2 torque submodel: the same body with the carbon ring's weight divided by its GJ over-stiffness (so the ring's
    GJ is the real tube's and its EI is 2.3 x low). With EI low the stays' bending path is softer than real and the
    tube attracts MORE torsion than the real tube would; with EI matched (the main run) GJ is 2.3 x high and it also
    attracts more. Both are upper bounds on the real tube torque; the bond check takes the lower of the two per
    sleeve and set (``torque_bound``)."""
    v = v or variant_defaults()
    con = dict(build(v, log=log))
    gj = con["info"]["tube"]["GJ_ratio_vox_over_tube"]
    w = con["weight"].copy()
    w[con["cf"]] = w[con["cf"]] / gj
    con.update(weight=w, name=v["name"] + "_gj")
    old_tr = FI.tube_resultants
    FI.tube_resultants = make_resultants(w)
    try:
        return FI.check(con["name"], bases=bases, log=log, con=con)
    finally:
        FI.tube_resultants = old_tr


# ================================================================================================ sizing (item 7)
BOND_KEYS = ("avg", "peak", "peak_c8", "fatigue", "bearing", "failsafe_tube_bearing", "failsafe_print_bearing")
MAX_BONDLINE = 1.5          # ASSUMPTION GAP-FILL: MMA bondline up to 1.5 mm (glass beads), coupons at that line
MAX_SLEEVE_T = 10.0


def bond_min(b: dict) -> tuple:
    best = (9e9, "")
    for sl, r in b.items():
        for k in BOND_KEYS:
            if k in r and r[k]["margin"] < best[0]:
                best = (r[k]["margin"], f"{sl} {k}")
    return best


def sleeve_ring_g(sl: str, d: dict, t_new: float, t_have: float) -> float:
    """Printed mass to thicken a bonded band's sleeve from t_have (measured mean) to t_new, both sides."""
    if t_new <= t_have:
        return 0.0
    r0 = TUBE["od"] / 2
    L = sum(b1 - b0 for b0, b1 in d["bands"])
    return 2 * math.pi * ((r0 + t_new) ** 2 - (r0 + t_have) ** 2) * L * FI.RHO_PAHT


def failsafe_g(fs: dict) -> float:
    """Fail-safe hardware, both sides: P1 Ti cross bolts (length 30 mm) + nut / washer (0.8 g x (d / 4)^2 each);
    P3 flush steel dowel pins, two per element (opposite walls), length = printed wall + tube wall."""
    n, d = fs.get("n", 1), fs.get("d", FAILSAFE_BOLT_D)
    if fs["kind"] == "bolt":
        return 2 * n * (math.pi / 4 * d ** 2 * 30.0 * 4.43e-3 + 0.8 * (d / 4) ** 2)
    L = fs.get("print_t", SLEEVE_T) + 2.0
    return 2 * 2 * n * math.pi / 4 * d ** 2 * L * RHO_STEEL


def size_bonds(name: str, alt: str | None, walls: dict, v: dict | None = None, bases=FI.BASES) -> dict:
    """Smallest per-sleeve change (sleeve wall t from the measured mean up to 10 mm in 1 mm steps, bondline 0.5 / 0.8 /
    1.0 / 1.25 / 1.5 mm, fail-safe: elements 1-3 per side, d 4 / 5 / 6 mm, printed wall at the fail-safe up to 10 mm)
    that brings every bond row of the sleeve to >= 1 on the stored transfers, cheapest in grams first. Transfers are
    held at the run's values (a thicker sleeve stiffens the node a little: the sized variant is re-run to confirm)."""
    import copy
    v = v or variant_defaults()
    out = {}
    for sl, d in v["sleeves"].items():
        t_have = max(d.get("sleeve_t", v["sleeve_t"]), walls[sl]["t_mean_mm"])
        best = None
        for t in [t_have] + [float(x) for x in range(int(math.ceil(t_have)), int(MAX_SLEEVE_T) + 1)]:
            for bl in sorted({d["bondline"], 0.8, 1.0, 1.25, MAX_BONDLINE}):
                if bl < d["bondline"]:
                    continue
                fsl = [None] if sl not in v["failsafe"] else [
                    {**v["failsafe"][sl], "n": n, "d": dd, "print_t": pt}
                    for n in (1, 2, 3) for dd in (4.0, 5.0, 6.0) for pt in (t, MAX_SLEEVE_T)]
                for fs in fsl:
                    vv = copy.deepcopy(v)
                    vv["sleeves"] = {sl: {**d, "bondline": bl, "sleeve_t": t}}
                    if fs is not None:
                        vv["failsafe"] = {sl: fs}
                    b = bonds(name, vv, bases=bases, alt=alt)
                    m = bond_min(b)
                    g = sleeve_ring_g(sl, d, t, t_have) + 2 * math.pi * TUBE["od"] * sum(
                        b1 - b0 for b0, b1 in d["bands"]) * (bl - d["bondline"]) * RHO_MMA
                    if fs is not None:
                        g += failsafe_g(fs) - failsafe_g(v["failsafe"][sl])
                        if fs["print_t"] > t:
                            g += 2 * fs["n"] * math.pi * ((fs["print_t"] + 11) ** 2 - (t + 11) ** 2) * 0.25 * \
                                (3 * fs["d"]) * FI.RHO_PAHT
                    if m[0] >= 1.0 and (best is None or g < best["g"]):
                        best = {"g": round(g, 1), "sleeve_t": t, "bondline": bl, "failsafe": fs, "min": round(m[0], 3),
                                "gov": m[1]}
        if best is None:
            vv = copy.deepcopy(v)
            vv["sleeves"] = {sl: {**d, "bondline": MAX_BONDLINE, "sleeve_t": MAX_SLEEVE_T}}
            if sl in v["failsafe"]:
                vv["failsafe"] = {sl: {**v["failsafe"][sl], "n": 3, "d": 6.0, "print_t": MAX_SLEEVE_T}}
            m = bond_min(bonds(name, vv, bases=bases, alt=alt))
            gl = sleeve_ring_g(sl, d, MAX_SLEEVE_T, t_have) + 2 * math.pi * TUBE["od"] * sum(
                b1 - b0 for b0, b1 in d["bands"]) * (MAX_BONDLINE - d["bondline"]) * RHO_MMA
            if sl in v["failsafe"]:
                gl += failsafe_g(vv["failsafe"][sl]) - failsafe_g(v["failsafe"][sl])
            # bond strength a T6p-T coupon would have to show (dry, MPa) for the sleeve at the limits to pass
            best = {"g": None, "feasible": False, "at_limits_min": round(m[0], 3), "gov": m[1],
                    "g_at_limits": round(gl, 1), "dry_bond_needed_mpa": round(BOND_DRY_MPA / m[0], 2)}
        out[sl] = best
    return out
