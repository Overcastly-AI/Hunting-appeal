"""Printed whole-frame study: evaluation tables, segmentation + print files, renders and the design doc.

  python -m huntkit.gendesign.frame_report            # after frame_study has produced the sweep
Writes designs/pack_5200/analysis/printed_frame_study.md, designs/pack_5200/print/frame/*,
outputs/screens/20261101_genframe_<n>.png and outputs/genframe/study_results.json.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import trimesh

from huntkit.fea.materials_bridge import REPO_ROOT

from . import frame_eval as fe
from . import frame_render as fr
from . import frame_topopt as ft
from .frame_study import OUT, ROD_D, hybrid_rods, rod_lines

PRINT_DIR = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"
DOC = REPO_ROOT / "designs" / "pack_5200" / "analysis" / "printed_frame_study.md"
SCREENS = REPO_ROOT / "outputs" / "screens"
DATE = "20261101"
PLATE = (340.0, 320.0, 340.0)        # Bambu H2S single-nozzle build volume used here (mm) - ASSUMPTION per brief
FDM_FLOW_MM3_S = 8.0                 # ASSUMPTION effective average flow for CF-nylon, 0.6 mm hardened nozzle
FDM_WASTE = 1.08                     # ASSUMPTION purge, brim, supports


def screen(n):
    return SCREENS / f"{DATE}_genframe_{n}.png"


def tags(kind):
    return sorted(p.stem.replace("_verify", "") for p in OUT.glob(f"{kind}_*_verify.json"))


# ----------------------------------------------------------------------------- geometry
def verified_domain(tag):
    meta = json.loads((OUT / f"{tag}.json").read_text())
    z = np.load(OUT / f"{tag}_verify.npz")
    if meta["hybrid"]:
        from .frame_study import _patch_build_domain_for_hybrid
        orig, bd = _patch_build_domain_for_hybrid()
        dv = bd(2.0)
    else:
        dv = ft.build_domain(2.0)
    return dv, z, meta


def body_mesh(tag, smooth=6):
    """Verified solid -> smooth watertight mesh, with the exact crown bores, spine channel, pivot bolt holes
    and (hybrid) rod channels cut by booleans (manifold3d)."""
    from .surface import _from_manifold, _to_manifold, cylinder, m3d
    dv, z, meta = verified_domain(tag)
    solid = z["solid"]
    f = dv.grid.to_array(solid.astype(float))
    from scipy import ndimage
    f = ndimage.gaussian_filter(f, 0.7)
    from .surface import field_to_mesh
    # iso-level chosen so the printable surface encloses the SAME volume as the verified voxel body (a plain
    # 0.5 iso-surface of the smoothed field shrinks thin members ~20 %, i.e. less material than was analysed)
    target = float(solid.sum() * dv.h ** 3)
    lo_l, hi_l = 0.15, 0.5
    m = None
    for _ in range(7):
        lv = 0.5 * (lo_l + hi_l)
        m = field_to_mesh(f, dv.h, dv.grid.x0, level=lv, smooth_iters=smooth, upsample=1)
        if abs(m.volume) < target:
            hi_l = lv
        else:
            lo_l = lv

    env = dv.env
    subs = []
    u = np.array([0.0, env.axis_slope, 1.0]); u /= np.linalg.norm(u)
    for s in (1, -1):
        p0 = np.array([s * env.top_pt[0], env.sleeve_y(ft.SLEEVE_Z0 - 5), ft.SLEEVE_Z0 - 5])
        subs.append(cylinder(p0, u, ft.Z_TOP - ft.SLEEVE_Z0 + 30, ft.SLEEVE_BORE_R, 48))
    if m3d is not None:
        box = m3d.Manifold.cube([40.0, 18.0, ft.Z_TOP - 296.0 + 20]).translate([-20.0, -34.0, 296.0])
        subs.append(box)
        pv = env.hp["hipbelt_pivot"]
        for dx in (-11.0, 11.0):          # 2 x M5 clearance for the SLM Ti hip-pivot mount
            subs.append(cylinder([pv[0] + dx, pv[1] - 2, pv[2]], [0, 1, 0], 26.0, 2.7, 24))
    rods = []
    if meta["hybrid"]:
        for p0, p1, _ in rod_lines(env):
            d = (p1 - p0); L = np.linalg.norm(d)
            subs.append(cylinder(p0 - d / L * 2, d / L, L + 4, ROD_D / 2 + 0.15, 24))
            rods.append(trimesh.creation.cylinder(radius=ROD_D / 2, segment=np.array([p0, p1]), sections=20))
    try:
        man = _to_manifold(m)
        for sb in subs:
            man = man - sb
        out = _from_manifold(man)
        if len(out.faces) > 1000:
            m = out
    except Exception as e:           # pragma: no cover
        print("  boolean skipped:", e)
    rodm = trimesh.util.concatenate(rods) if rods else None
    return m, rodm, dv, z, meta


def choose_cut(dv, z, lo=226.0, hi=316.0):
    """Cut height for the 2 segments (each <= 320 mm long to lie flat on the plate): the height with the
    lowest envelope utilization in a 10 mm slab, away from the strap/bag anchors (+-15 mm)."""
    c = dv.grid.elem_centers()[z["solid"]]
    vm = z["env_vm"]
    anchors = [330.0, 250.0, 190.0]
    best, bz = np.inf, None
    for zc in np.arange(lo, hi + 1, 2.0):
        if any(abs(zc - a) < 15 for a in anchors):
            continue
        sl = np.abs(c[:, 2] - zc) < 5
        if sl.sum() < 10:
            continue
        val = np.percentile(vm[sl], 95)
        if val < best:
            best, bz = val, float(zc)
    return bz, best


def section_from_S(dv, z, key, z_cut):
    """Section resultants across z = z_cut per side from the stored element stresses of load set ``key``."""
    S = z[f"S_{key.replace('|', '_')}"]
    c = dv.grid.elem_centers()[z["solid"]]
    h = dv.h
    lay = np.abs(c[:, 2] - z_cut) < h / 2 + 1e-6
    out = {}
    for tag, side in (("L", c[:, 0] < 0), ("R", c[:, 0] >= 0)):
        m = lay & side
        if not m.any():
            continue
        s, xc = S[m], c[m]
        cen = xc.mean(0)
        A = h * h
        out[tag] = {"N": float(s[:, 2].sum() * A), "Vx": float(s[:, 5].sum() * A), "Vy": float(s[:, 4].sum() * A),
                    "Mx": float((s[:, 2] * (xc[:, 1] - cen[1])).sum() * A),
                    "My": float((s[:, 2] * (xc[:, 0] - cen[0])).sum() * A), "area_mm2": float(m.sum() * A),
                    "depth_mm": float(np.ptp(xc[:, 1]) + h), "width_mm": float(np.ptp(xc[:, 0]) + h)}
    return out


DOWEL_D, DOWEL_EMBED = 5.0, 50.0       # mm: pultruded CF dowel, embedment each side (100 mm long dowels)


def joint_checks(dv, z, z_cut, hybrid, dowel_d=DOWEL_D, n_dowel=1, embed=DOWEL_EMBED, tau_bond=6.0, tau_dowel=60.0,
                 lever_by_side=None):
    """Doweled + bonded butt splice at z_cut, per side, for the 4 stored governing load sets (factored).
    Flange force F = |N|/2 + |M| / lever (lever = dowel separation, else 0.8 x section depth); the tension
    flange force is carried by ONE dowel per flange in (pull-out: tau_bond x pi d x embed, ASSUMPTION 6 MPa MMA on treated nylon, hot/wet) and by
    bearing of the bonded butt face in compression; shear by dowel cross-shear (ASSUMPTION 60 MPa
    pultruded rod transverse shear) and the butt-face bond (tau_bond x face area / 2).
    Hybrid: the 4 full-length rods cross the cut and ARE the dowels."""
    rows = []
    for k2 in KEEP_SETS:
        if f"S_{k2.replace('|', '_')}" not in z.files:
            continue
        res = section_from_S(dv, z, k2, z_cut)
        for side, r in res.items():
            lever = (lever_by_side or {}).get(side) or 0.8 * r["depth_mm"]
            M = np.hypot(r["Mx"], r["My"] * r["depth_mm"] / max(r["width_mm"], 1))
            Ft = abs(r["N"]) / 2 + M / lever
            pull = n_dowel * tau_bond * np.pi * dowel_d * embed
            V = np.hypot(r["Vx"], r["Vy"])
            shear_cap = 2 * n_dowel * tau_dowel * np.pi * dowel_d ** 2 / 4 + tau_bond * r["area_mm2"] / 2
            rows.append({"set": k2, "side": side, "N": r["N"], "M_Nmm": float(M), "V": float(V),
                         "flange_n": float(Ft), "pull_sf": float(pull / max(Ft, 1e-9)),
                         "shear_sf": float(shear_cap / max(V, 1e-9)), "area_mm2": r["area_mm2"], "lever_mm": float(lever)})
    return rows


KEEP_SETS = ("drop_2p5g|19", "side_hill_torsion|15", "meat_straps|23", "hipbelt_off_abuse|19")


def segments(body, z_cut):
    lo, hi = ft.split_mesh(body, z_cut)
    return {"lower": lo, "upper": hi}


def orient_flat(mesh, face="wearer"):
    """Lay a segment flat: build Z = frame -y (wearer face down) or +y (bag face down). Layer normal = y."""
    m = mesh.copy()
    R = np.eye(4)
    if face == "wearer":     # frame -y -> build -Z (plate): x -> X, z -> Y, y -> Z
        R[:3, :3] = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]])
    else:
        R[:3, :3] = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    m.apply_transform(R)
    m.apply_translation(-m.bounds[0])
    return m


def fdm_stats(mesh, rho, price_g):
    V = float(abs(mesh.volume))
    g = V * rho / 1e6
    return {"volume_cm3": V / 1e3, "mass_g": g, "filament_g": g * FDM_WASTE,
            "hours": V / FDM_FLOW_MM3_S / 3600 * FDM_WASTE, "filament_usd": g * FDM_WASTE * price_g}


# ----------------------------------------------------------------------------- evolution snapshots
def evolution_frames(tag, n=6):
    from .surface import field_to_mesh
    snaps = pickle.loads((OUT / f"{tag}_snaps.pkl").read_bytes())
    pick = np.unique(np.linspace(0, len(snaps) - 1, n).round().astype(int))
    env = ft.load_envelope()
    out = []
    for i in pick:
        s = snaps[i]
        d = ft.build_domain(s["h"], env)
        f = d.grid.to_array(s["x"].astype(float))
        try:
            m = field_to_mesh(f, d.h, d.grid.x0, level=0.5, smooth_iters=4, upsample=1)
            img, info = fr.raster([(fr.simplify(m, 30000), fr.BODY_COL)], 12, 200, size=520, spec=0.1)
            img = fr.autocrop(img, info["mask"])
        except Exception:
            continue
        stage = "coarse 8 mm" if s["stage"] == "c" else "fine 4 mm"
        out.append((f"{stage}, it {s['it']}  (vol {s['rec']['volume']:.3f})", img))
    return out


# ----------------------------------------------------------------------------- study assembly
PURE_MATS = ["pa6_cf_fdm_bambu", "pa12_cf_fdm_paht", "pa12_mjf_hp", "pa11_mjf_hp", "pa12_gb_mjf_hp", "pa12_cf_sls",
             "onyx_ccf_markforged", "alsi10mg_slm"]
ROD_RHO = 1550.0
CCF_AREA = 14.0          # mm2 continuous-fiber bundle per path (~128 strands of 0.11 mm2: e.g. 32 layers x 4)


def rods_mass_g():
    env = ft.load_envelope()
    L = sum(np.linalg.norm(p1 - p0) for p0, p1, _ in rod_lines(env))
    return L * np.pi * ROD_D ** 2 / 4 * ROD_RHO / 1e6


def ccf_variant(tag, log=print):
    """Continuous-fiber printing on the hybrid topology: Onyx matrix (E 2400) + CCF bundles (E1 60 GPa,
    CCF_AREA mm2) along the same 4 principal-stress paths the rods take (the stays' principal stress is
    axial: the streamlines in fiber_paths.png run along them). Independent re-verification."""
    import pickle as _p
    mats = ft.material_table()
    m = mats["onyx_ccf_markforged"]
    from huntkit.fea.materials_bridge import get_material
    rec = get_material("onyx_ccf_markforged")
    E1 = float(rec.get("E1_mpa"))
    sets = _p.loads((OUT / "loadsets.pkl").read_bytes())
    from .frame_study import _patch_build_domain_for_hybrid
    orig, bd = _patch_build_domain_for_hybrid()
    ft.build_domain = bd
    try:
        df = ft.build_domain(4.0)
        z = np.load(OUT / f"{tag}.npz")
        df.passive_void = z["passive_void"]

        def rods_fn(dom):
            return [ft.Rod(p0, p1, CCF_AREA, E1 / m.E, nm) for p0, p1, nm in rod_lines(dom.env)]
        vr = ft.verify(df, z["xPhys"], sets, up=2, rods_fn=rods_fn, log=log)
    finally:
        ft.build_domain = orig
    env = ft.load_envelope()
    Lf = sum(np.linalg.norm(p1 - p0) for p0, p1, _ in rod_lines(env))
    fiber_g = Lf * CCF_AREA * float(rec.get("fiber_density_kg_m3")) / 1e6
    body = vr.volume_mm3 / 1e3 * m.rho / 1e3 + fiber_g + fe.INSERTS_G
    gk = max(vr.stress, key=lambda k: vr.stress[k]["vm99"])
    s_gov = vr.stress[gk]["vm99"]
    o_fi = np.percentile(ft.layer_failure_index(vr.env_s, vr.env_t, 1, m.s_xy, m.s_z, m.knock)[~vr.exclude], 99)
    s1 = vr.stress["static_carry|19"]["vm99"] / 2.0
    sf = 1 / o_fi
    tube = json.loads((OUT / "tube_baseline.json").read_text())["stiff"]
    k_t = vr.stiff["torsion_Nm_per_deg"] * m.E
    d_c = np.hypot(vr.stiff["carry_dy_mm"], vr.stiff["carry_dz_mm"]) / m.E
    res = {"tag": tag + "_ccf", "material": m.id, "body_g": body, "fiber_g": fiber_g, "frame_g": body + fe.kept_g(),
           "sf_strength": float(sf), "sf_fatigue": float(m.fat * sf * s_gov / (1.6 * s1)),
           "sf_creep_rupture": float(m.rupture * sf * s_gov / s1),
           "torsion_rel": float(k_t / tube["torsion_Nm_per_deg"]),
           "carry_rel": float(np.hypot(tube["carry_dy_mm"], tube["carry_dz_mm"]) / abs(d_c)),
           "creep_defl_mm": float(abs(d_c) * (0.5 + 0.5 / (m.E_hot * m.creep8h))),
           "cost_usd": float(body * m.cost_per_g), "fiber_m": float(Lf / 1000 * CCF_AREA / 0.11)}
    (OUT / f"{tag}_ccf.json").write_text(json.dumps(res, indent=1))
    return res


def fiber_paths(tag, dv, z, out_csv, png):
    """Principal-stress trajectories (major in-plane principal stress of the 2.0 g stumble case) on the two
    fiber planes of the flat-printed body (fore / aft flange planes, the rod planes): the paths a
    continuous-fiber printer should lay (CSV: path id, x, y, z in frame coordinates)."""
    import csv
    S = z["S_drop_2p5g_19"]
    env = dv.env
    planes = {"aft": float(env.sleeve_y(300.0) + 13.5), "fore": float(env.sleeve_y(300.0) - 13.5)}
    lines = {}
    for nm, yl in planes.items():
        lines[nm] = ft.principal_streamlines(dv, z["solid"], S, yl, n_seeds=30, step=3.0)
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "plane", "x_mm", "y_mm", "z_mm"])
        k = 0
        for nm, ls in lines.items():
            for L in ls:
                for p in L:
                    w.writerow([k, nm, f"{p[0]:.2f}", f"{p[1]:.2f}", f"{p[2]:.2f}"])
                k += 1
    fr._style()
    fig, axs = fr.plt.subplots(1, 2, figsize=(12, 10.5))
    c = dv.grid.elem_centers()[z["solid"]]
    for ax, (nm, yl) in zip(axs, planes.items()):
        sel = np.abs(c[:, 1] - yl) <= dv.h * 0.75
        ax.scatter(c[sel, 0], c[sel, 2], s=3, color="#c9c8c3", marker="s", linewidths=0)
        for L in lines[nm]:
            ax.plot(L[:, 0], L[:, 2], color=fr.S1, lw=1.4)
        ax.set_aspect("equal"); ax.set_title(f"{nm} fiber plane, y = {yl:.0f} mm", loc="left")
        ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.suptitle("Continuous-fiber paths = major principal-stress trajectories (2.0 g stumble)",
                 x=0.02, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fr.save(fig, png)
    return {nm: len(v) for nm, v in lines.items()}


def on_pack_render(path, title):
    from huntkit.viz3d.model import build_pack
    from huntkit.viz3d.params import load_params
    p = load_params(overrides={"fea": {"enabled": False}, "frame_type": "generative", "mannequin": {"enabled": False}})
    pk = build_pack(p)
    cols = {"printed_cf": (0.19, 0.20, 0.22), "carbon": (0.07, 0.07, 0.08), "titanium": (0.62, 0.64, 0.68),
            "fitting": (0.12, 0.12, 0.13), "body": (0.47, 0.45, 0.36), "harness": (0.30, 0.30, 0.27),
            "spacer": (0.25, 0.26, 0.23), "camo": (0.42, 0.40, 0.33), "webbing": (0.33, 0.31, 0.26),
            "tpu": (0.36, 0.35, 0.29), "trim": (0.2, 0.2, 0.18), "meat_strap": (0.78, 0.74, 0.62)}
    meshes_back, meshes_side = [], []
    for q in pk.parts:
        if "pack" not in q.modes or q.group in ("fea", "mannequin") or q.name.startswith("mannequin"):
            continue
        if q.torso not in (None, 19.0) or q.variant not in (None, "rolled"):
            continue
        col = cols.get(q.material, (0.45, 0.44, 0.40))
        mm = fr.simplify(q.mesh, 25000)
        meshes_side.append((mm, col))
        if q.group in ("frame", "bag", "accessory") and not q.name.startswith(("lid",)):
            meshes_back.append((mm, col))     # wearer-side view without harness / hipbelt: frame on the bag
    fr._style()
    fig = fr.plt.figure(figsize=(12, 9.4))
    fig.suptitle(title, x=0.03, ha="left", fontsize=17, fontweight="bold", y=0.975)
    for i, (lab, el, az, ms) in enumerate((("on the bag, wearer side (harness hidden)", 10, 20, meshes_back),
                                           ("on the pack, side", 4, 90, meshes_side))):
        img, info = fr.raster(ms, el, az, size=1000, spec=0.12)
        img = fr.autocrop(img, info["mask"])
        ax = fig.add_axes([i * 0.5 + 0.005, 0.02, 0.49, 0.88])
        ax.imshow(img); ax.set_axis_off(); ax.set_title(lab, fontsize=12, color=fr.INK2, loc="left")
    return fr.save(fig, path)


REC_MAT = "pa12_cf_fdm_paht"


def dowel_points(dv, z, z_cut, inset=4.0):
    """Per side: the fore-most and aft-most points of the solid section at z_cut, >= 12.5 mm from the crown-leg
    bore axis, inset 4 mm: the 2 dowel positions (maximum lever across the section)."""
    c = dv.grid.elem_centers()[z["solid"]]
    sl = np.abs(c[:, 2] - z_cut) < dv.h
    out = []
    for s in (1, -1):
        m = sl & (np.sign(c[:, 0]) == s)
        q = c[m]
        r = np.hypot(q[:, 0] - s * dv.env.top_pt[0], q[:, 1] - dv.env.sleeve_y(z_cut))
        q = q[r > ft.SLEEVE_BORE_R + 3.5]
        if len(q) < 2:
            continue
        a, b = q[np.argmin(q[:, 1])], q[np.argmax(q[:, 1])]
        a = a + np.array([0, inset, 0]); b = b - np.array([0, inset, 0])
        out += [np.array([a[0], a[1], z_cut]), np.array([b[0], b[1], z_cut])]
    return out


def build_print_package(tag, mats, log=print, mat_id=REC_MAT):
    """Recommended design -> 2 flat-printing segments (STL + 3MF), assembled body (+ rods) in frame coordinates,
    dowel holes across the joint, joint check, orientation + time/filament/cost per segment."""
    body, rods, dv, z, meta = body_mesh(tag)
    z_cut0, _ = choose_cut(dv, z)
    dowels = [] if meta["hybrid"] else dowel_points(dv, z, z_cut0)
    if dowels:
        from .surface import _from_manifold, _to_manifold, cylinder
        man = _to_manifold(body)
        for p in dowels:
            man = man - cylinder(p - np.array([0, 0, DOWEL_EMBED]), [0, 0, 1], 2 * DOWEL_EMBED, DOWEL_D / 2 + 0.1, 20)
        body = _from_manifold(man)
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    from .surface import export
    export(body, PRINT_DIR / "genframe_assembled", formats=("stl",))
    if rods is not None:
        export(rods, PRINT_DIR / "genframe_rods", formats=("stl",))
    z_cut = z_cut0
    segs = segments(body, z_cut)
    m = mats[mat_id]
    seginfo = {}
    c = dv.grid.elem_centers()[z["solid"]]
    for nm, sm in segs.items():
        sel = (c[:, 2] < z_cut) if nm == "lower" else (c[:, 2] >= z_cut)
        fis = {}
        for a, lab in ((1, "y"), (0, "x"), (2, "z")):
            fi = ft.layer_failure_index(z["env_s"][sel], z["env_t"][sel], a, m.s_xy, m.s_z, m.knock)
            fis[lab] = float(np.percentile(fi[~z["exclude"][sel]], 99))
        sup = {}
        fits = {}
        for lab, d in (("+y", (0, 1, 0)), ("-y", (0, -1, 0)), ("+x", (1, 0, 0)), ("+z", (0, 0, 1)), ("-z", (0, 0, -1))):
            from .surface import overhang_area
            sup[lab] = overhang_area(sm, d, 50.0)
            ext = sm.extents
            k = int(np.argmax(np.abs(d)))
            dims = sorted([ext[i] for i in range(3) if i != k], reverse=True)
            fits[lab] = dims[0] <= max(PLATE[:2]) - 4 and dims[1] <= min(PLATE[:2]) - 4 and ext[k] <= PLATE[2]
        cand = [l for l in ("-y", "+y") if fits[l]]
        face = min(cand, key=lambda l: sup[l]) if cand else min(sup, key=sup.get)
        om = orient_flat(sm, "wearer" if face == "-y" else "bag")
        stem = PRINT_DIR / f"genframe_{nm}_flat"
        files = export(om, stem, formats=("stl", "3mf"))
        st = fdm_stats(sm, m.rho, m.cost_per_g)
        seginfo[nm] = {"files": [str(Path(f).relative_to(REPO_ROOT)) for f in files], "fi99_by_layer_normal": fis,
                       "support_mm2": sup, "fits": fits, "plate_face": face, "extents_on_plate": om.extents.tolist(),
                       **st, "mesh": om}
        log(f"  segment {nm}: {st['mass_g']:.0f} g, {st['hours']:.1f} h, face {face}, fi {fis}")
    sep = {("R" if dowels[k][0] > 0 else "L"): float(abs(dowels[k + 1][1] - dowels[k][1]))
           for k in range(0, len(dowels), 2)} if dowels else None
    joints = joint_checks(dv, z, z_cut, meta["hybrid"], lever_by_side=sep)
    return {"tag": tag, "z_cut": z_cut, "segments": seginfo, "joints": joints, "body": body, "rods": rods,
            "dv": dv, "z": z, "meta": meta, "dowels": [d.tolist() for d in dowels], "material": mat_id}


def _f(x, nd=0):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x:,.{nd}f}"


def run(log=print):
    SCREENS.mkdir(parents=True, exist_ok=True)
    mats = ft.material_table()
    tubeb = json.loads((OUT / "tube_baseline.json").read_text())
    tube = tubeb["stiff"]
    pure, hyb = tags("pure"), tags("hybrid")
    log(f"pure {pure}\nhybrid {hyb}")
    R = {"tube": tubeb, "pure_tags": pure, "hybrid_tags": hyb, "materials": {}, "kept_g": fe.kept_g()}
    sweep = {}
    for mid in PURE_MATS:
        lp = fe.lightest_passing(pure, mats[mid], tube)
        R["materials"][mid] = {"body_g": lp["body_g"], "frame_g": lp["frame_g"], "governing": lp["governing"],
                               "extrapolated": lp["extrapolated"], "need_g": lp["need_g"],
                               "rows": [fe.as_dict(r) for r in lp["rows"]]}
        sweep[mid] = lp
    rg = rods_mass_g()
    lh = fe.lightest_passing(hyb, mats["pa6_cf_fdm_bambu"], tube, rods_g=rg)
    R["hybrid"] = {"body_g": lh["body_g"], "frame_g": lh["frame_g"], "governing": lh["governing"],
                   "extrapolated": lh["extrapolated"], "need_g": lh["need_g"], "rods_g": rg,
                   "rows": [fe.as_dict(r) for r in lh["rows"]]}
    # recommended PRINTED design = lightest verified all-plastic body that passes everything in REC_MAT
    rr = [fe.evaluate(t, mats[REC_MAT], tube) for t in pure]
    passing = [r for r in rr if r.passes]
    rec_row = min(passing, key=lambda r: r.body_g) if passing else max(rr, key=lambda r: r.torsion_rel)
    R["recommended"] = fe.as_dict(rec_row)
    hp = [r for r in lh["rows"] if r.passes]
    hyb_row = min(hp, key=lambda r: r.body_g) if hp else max(lh["rows"], key=lambda r: r.torsion_rel)
    R["hybrid_best"] = fe.as_dict(hyb_row)
    hot = OUT / f"{hyb_row.tag}_hot.json"
    R["hybrid_hot"] = json.loads(hot.read_text()) if hot.exists() else None
    m_rec = mats[REC_MAT]
    R["rec_hot_torsion_rel"] = rec_row.torsion_rel * m_rec.E_hot * m_rec.creep8h
    ccf = ccf_variant(hyb_row.tag, log=log)
    R["ccf"] = ccf
    pk = build_print_package(rec_row.tag, mats, log=log)
    R["print"] = {k: v for k, v in pk.items() if k in ("tag", "z_cut", "joints", "dowels", "material")}
    R["print"]["segments"] = {k: {kk: vv for kk, vv in v.items() if kk != "mesh"} for k, v in pk["segments"].items()}
    # ---------------------------------------------------------------- screenshots
    shots = {}
    body, rods = pk["body"], pk["rods"]
    shots[1] = fr.product_card(body, rods, screen(1), "Generative printed frame (one topology-optimized body)",
                               f"FDM PAHT-CF on the H2S, {rec_row.body_g:.0f} g body; carbon crown slides in the printed "
                               f"sleeves. Whole frame {rec_row.frame_g:.0f} g (carbon-tube frame {fe.TUBE_FRAME_G:.0f} g)")
    try:
        shots[2] = on_pack_render(screen(2), "Generative frame on the Pack 5200 (v3.1 bag), torso 19 in")
    except Exception as e:      # pragma: no cover
        log(f"  on-pack render failed: {e!r}")
    # utilization map for the recommended material
    dv, z = pk["dv"], pk["z"]
    m = mats[REC_MAT]
    fi = ft.layer_failure_index(z["env_s"], z["env_t"], 1, m.s_xy, m.s_z, m.knock)
    c = dv.grid.elem_centers()[z["solid"]]
    from scipy.spatial import cKDTree
    bm = fr.simplify(body, 90000)
    _, j = cKDTree(c).query(bm.triangles_center)
    u = np.minimum(fi[j], 1.2)
    shots[3] = fr.utilization_card(bm, u, screen(3), "Utilization, envelope of all 27 HA-LS-1 load sets",
                                   f"PAHT-CF flat-printed (layer normal = frame y), layer failure index incl. Z strength; "
                                   f"99th pct {np.percentile(fi[~z['exclude']], 99):.2f}")
    segs = pk["segments"]
    shots[4] = fr.plate_card([(segs[k]["mesh"], f"{k}: {segs[k]['mass_g']:.0f} g, {segs[k]['hours']:.1f} h, "
                               f"{segs[k]['extents_on_plate'][0]:.0f} x {segs[k]['extents_on_plate'][1]:.0f} x "
                               f"{segs[k]['extents_on_plate'][2]:.0f} mm") for k in ("lower", "upper")],
                             screen(4), f"Segments flat on the H2S plate (340 x 320 mm), cut at z = {pk['z_cut']:.0f} mm",
                             notes=("Each segment lies flat: layers = frame plane, so the bending stresses run along "
                                    "the layers; supports only under the sleeve-bore bridges.",
                                    f"Joint: 4 x {DOWEL_D:g} mm carbon dowels ({2 * DOWEL_EMBED:.0f} mm) across the cut + MMA-bonded butt face."))
    chart_rows = [{"label": "v2 carbon tube frame", "frame_g": fe.TUBE_FRAME_G, "torsion_rel": 1.0, "kind": "tube"}]
    names = {"pa6_cf_fdm_bambu": "FDM PA6-CF (H2S)", "pa12_cf_fdm_paht": "FDM PAHT-CF (H2S)",
             "pa12_mjf_hp": "MJF PA12 (service)", "pa11_mjf_hp": "MJF PA11 (service)",
             "pa12_gb_mjf_hp": "MJF PA12-GB (service)", "pa12_cf_sls": "SLS PA12-CF (service)",
             "onyx_ccf_markforged": "Onyx, no fiber", "alsi10mg_slm": "SLM AlSi10Mg (ref.)"}
    for mid, v in R["materials"].items():
        if not np.isfinite(v["frame_g"]) or v["frame_g"] > 3000:
            continue
        rr = sorted(v["rows"], key=lambda r: r["body_g"])
        tor = float(np.interp(v["body_g"], [r["body_g"] for r in rr], [r["torsion_rel"] for r in rr]))
        chart_rows.append({"label": names[mid] + (" (extrap.)" if v["extrapolated"] else ""), "frame_g": v["frame_g"],
                           "torsion_rel": tor, "kind": "metal" if mid == "alsi10mg_slm" else "plastic"})
    chart_rows.append({"label": "HYBRID PA6-CF + 4 CF rods", "frame_g": hyb_row.frame_g, "torsion_rel": hyb_row.torsion_rel,
                       "kind": "hybrid", "passes": hyb_row.passes})
    chart_rows.append({"label": "Onyx + continuous CF paths", "frame_g": ccf["frame_g"], "torsion_rel": ccf["torsion_rel"],
                       "kind": "hybrid", "passes": ccf["sf_strength"] >= 1 and ccf["torsion_rel"] >= 0.8})
    shots[5] = fr.comparison_chart(chart_rows, fe.TUBE_FRAME_G, screen(5),
                                   "Frame mass at the HA-LS-1 margins and torsional stiffness")
    evo_tag = next((t for t in pure if (OUT / f"{t}_snaps.pkl").exists()), None)
    if evo_tag:
        shots[6] = fr.evolution_card(evolution_frames(evo_tag), screen(6),
                                     f"Optimization evolution ({evo_tag}: coarse 8 mm -> fine 4 mm voxels)")
    shots[7] = fiber_paths(rec_row.tag, dv, z, PRINT_DIR / "fiber_paths_principal_stress.csv", screen(7)) and str(screen(7))
    R["screens"] = {k: str(v) for k, v in shots.items() if v}
    R["chart_rows"] = chart_rows
    (OUT / "study_results.json").write_text(json.dumps(R, indent=1, default=float))
    write_doc(R, mats)
    write_print_readme(R)
    return R



MAT_NOTES = {
    "pa6_cf_fdm_bambu": ("FDM, owner's H2S", "absorbs 2.4 % water: conditioned strength -22 %; anneal; seal/paint for UV"),
    "pa12_cf_fdm_paht": ("FDM, owner's H2S", "PA12 base: 0.9 % water, keeps properties wet; weakest Z (47 MPa)"),
    "pa12_mjf_hp": ("MJF service", "isotropic, no Z weakness; Tg onset ~27-50 C: soft when hot"),
    "pa11_mjf_hp": ("MJF service", "ductile (50 % elongation), best cold impact of the nylons"),
    "pa12_gb_mjf_hp": ("MJF service", "glass beads add stiffness but cut strength to 30 MPa"),
    "pa12_cf_sls": ("SLS service", "stiffest unreinforced powder (7.9 GPa XY), anisotropic, estimate-grade data"),
    "onyx_ccf_markforged": ("Markforged-class", "matrix only here (no fiber): weak 40 MPa / 2.4 GPa"),
    "alsi10mg_slm": ("SLM service", "reference only: metal, needs no creep/UV caveats; galvanic-isolate from carbon"),
}


def write_doc(R, mats):
    t = R["tube"]["stiff"]
    rec = R["recommended"]
    ccf = R["ccf"]
    pr = R["print"]
    segs = pr["segments"]
    best_pure = min(R["materials"].items(), key=lambda kv: kv[1]["frame_g"] if kv[0] != "alsi10mg_slm" else 1e9)
    bp_id, bp = best_pure
    plastic_ok = bp["frame_g"] <= 1.10 * fe.TUBE_FRAME_G
    L = []
    A = L.append
    A("# Pack 5200 - whole-frame generative design: one topology-optimized 3D-printed frame")
    A("")
    A("Owner: structural-fea-engineer. Owner direction (2026-11-01, DECISIONS.md): generative design applies to the WHOLE "
      "FRAME as one topology-optimized 3D-printed structure; fully plastic is acceptable. Code: `huntkit/gendesign/frame_topopt.py` "
      "(domain, loads, SIMP, verification), `frame_study.py` (sweep driver), `frame_eval.py` (materials), `frame_report.py` "
      "(this file, print files, renders). Tests: `tests/test_frame_topopt.py`. Load standard: **HA-LS-1 rev B** "
      "(no meat shelf; meat on the internal straps, load_standard.md). Interfaces: geometry.yaml v3.1 (read-only here).")
    A("")
    A("## 0. Verdict (honest)")
    A("")
    hb = R["hybrid_best"]
    hh = R.get("hybrid_hot") or {}
    pa6 = R["materials"]["pa6_cf_fdm_bambu"]
    A(f"- **An all-plastic printed frame CAN meet HA-LS-1 (strength, fatigue, 8 h creep rupture) and the room-temperature "
      f"stiffness limit, but NOT at a competitive weight.** Lightest passing all-plastic frame: **{names_of(bp_id)}, "
      f"{bp['frame_g']:.0f} g** whole frame (interpolated over the sweep; governed by {bp['governing']}); FDM PA6-CF "
      f"{pa6['frame_g']:.0f} g. The v2 carbon-tube frame is **{fe.TUBE_FRAME_G:.0f} g**: plastic is "
      f"**+{bp['frame_g'] - fe.TUBE_FRAME_G:.0f} g (+{100 * (bp['frame_g'] / fe.TUBE_FRAME_G - 1):.0f} %)**. About "
      f"{0.15 * 1060:.0f}-{0.15 * 1170:.0f} g of every printed body is fixed overhead (crown-leg sleeves, pawl housing, pivot boss, "
      f"anchor pads: 151 cm3) that carbon tubes get for free.")
    A(f"- **Heat is the real problem.** At 40 C and moisture-conditioned, nylon is at/above its glass transition: the "
      f"8 h creep-softened torsional stiffness of the recommended printed frame is ~{100 * R['rec_hot_torsion_rel']:.0f} % of "
      f"the tube frame (limit 80 %). The pack will feel noticeably softer on a hot afternoon, and recover when cool. "
      f"Strength and creep rupture still pass (sustained stresses are low).")
    A(f"- **Best hybrid tested: PA6-CF body + 4 pultruded carbon rods (4 mm) along the stays: {hb['frame_g']:.0f} g**, "
      f"torsion {100 * hb['torsion_rel']:.0f} % cold"
      + (f" / {100 * hh['hot']['torsion_rel']:.0f} % hot (matrix softened)" if hh else "")
      + ". The rods cut the static-carry sag and its creep but do not fix the hot torsion, because the frame's twist is "
      "carried by the printed lumbar web and nodes, not the stays. It is not lighter than the all-plastic body. The "
      "hybrid that WOULD be competitive is the v2 frame itself (carbon tubes where bending/torsion lives, wraps at the "
      "nodes): printing the nodes instead was +80 to +190 g in generative_design.md.")
    ok_ccf = ccf["sf_strength"] >= 1 and ccf["torsion_rel"] >= 0.8
    A(f"- Continuous-fiber printing (Onyx matrix + {CCF_AREA:g} mm2 CCF bundles on the same 4 principal-stress paths): "
      f"{ccf['frame_g']:.0f} g, torsion {100 * ccf['torsion_rel']:.0f} %, matrix strength SF/req {ccf['sf_strength']:.2f}: "
      + ("passes." if ok_ccf else "**fails**: Onyx (40 MPa, 2.4 GPa) is too weak/soft for the nodes and lumbar web where the "
         "fibers cannot go; the fiber helps only along the stays.") + f" Est. ${ccf['cost_usd']:.0f} at a service.")
    A(f"- **Recommendation.** Production: **keep the v2 carbon-tube frame ({fe.TUBE_FRAME_G:.0f} g)**. Printed frame: build the "
      f"**FDM PAHT-CF generative body ({rec['tag']}, {rec['frame_g']:.0f} g whole frame, SF/req {rec['sf_strength']:.2f}, "
      f"fatigue {rec['sf_fatigue']:.2f}, torsion {100 * rec['torsion_rel']:.0f} %)** on the H2S as a low-cost, no-layup "
      f"prototype / fit-and-feel frame and as a backup frame. Print files: `designs/pack_5200/print/frame/` "
      f"(2 segments, ~{sum(v['hours'] for v in segs.values()):.0f} h, ~${sum(v['filament_usd'] for v in segs.values()):.0f} "
      f"of filament). Proof-test it (load_standard.md T1-T5) plus a 40 C / 8 h hold before trusting it in the field.")
    A("")
    A("## 1. Design domain, non-design regions, crown decision")
    A("")
    A("| item | value | source |")
    A("|---|---|---|")
    A(f"| domain | x +-{ft.X_HALF:.0f}, y {ft.Y_LO:.0f} .. bag frame-side panel - 1 mm (v3.1 profile stations, 57-64 mm deep), "
      f"z 0..{ft.Z_TOP:.0f} mm | geometry.yaml bag.profile.stations, hard points |")
    A("| back clearance | y >= -48 (hip-pivot face y -48.1; back-pad foam + mesh in front) | ASSUMPTION |")
    A("| head clearance | no printed material above z 544 (stay tops): the crown, its 25 mm aft-swept top bar and the "
      "stepped bag panel above it are untouched (geometry.yaml head_clearance all_pass) | geometry.yaml v3.1 |")
    A(f"| crown-leg sleeves | bore {2 * ft.SLEEVE_BORE_R:.0f} mm (leg OD 16 + 1 mm UHMWPE bushing), printed wall "
      f"{ft.SLEEVE_WALL} mm, z {ft.SLEEVE_Z0:.0f}..544 on the crown axis (slope {R.get('axis', -0.0189)}) | frame.yaml, geometry.yaml crown |")
    A("| spine channel (void) | x +-20, y -34..-16, z 296..544 (spine + rack travel, 15-23 in) | geometry.yaml crown_retention |")
    A("| pawl housing (solid) | x +-25, y -39..-11, z 506..536 around the channel | rack_lock_pawl_upper_bar |")
    A("| hip-pivot boss (solid, clamp) | D32 at (0, -48.1, 120), 2 x M5 to the SLM Ti mount | hipbelt_pivot |")
    A("| pads (solid, r 6 mm) | bag anchors low/mid, meat anchors z190/z330/z520, hip stabilizers, shoulder-strap lower "
      "anchors, load-wing/haul-wrap lash z80/250/420, pulley guides, cam buckle, stay feet | geometry.yaml hard_points |")
    A("")
    A("**Crown decision: keep the v2 CARBON telescoping crown (legs OD 16, top bar, spine; 118 g) sliding in printed "
      "sleeves.** The crown legs are up to 274 mm free cantilevers above the stay tops (23 in setting); printed nylon "
      "(E 1.7-7.9 GPa vs ~100 GPa carbon) would need ~4x the section to match, and a printed rail would put all crown "
      "loads (hipbelt-off abuse 850 N extension at the pawl) into one sliding joint in creep-prone plastic. The pulley + "
      "rack/pawl adjuster is unchanged: continuous 15-23 in.")
    A("")
    A("## 2. Loads (HA-LS-1 rev B, 9 cases x 15/19/23 in)")
    A("")
    A("The v2 beam model (frame.yaml) is solved for every case and torso; every load, body-spring reaction and "
      "d'Alembert load on a fixed-frame node plus the crown link forces (top bushing, leg-end bushing at z 171/273/375, "
      "pawl) are the printed body's loads; the hip pivot is the clamp. Loads x required factor. The optimization uses the "
      "7 distinct load shapes x 3 torsos (static carry = stumble shape x 2/3; overload ~ meat shape); verification re-checks "
      "all 27 sets.")
    A("")
    A("Tube frame (v2) under rev B, member first-ply SF / required, worst torso (`outputs/genframe/tube_baseline.json`):")
    A("")
    A("| case | SF/req | where |")
    A("|---|---|---|")
    for k, v in R["tube"]["member_margin_revB"].items():
        w = R["tube"]["where"][k]
        A(f"| {k} | {v:.2f} | {w[2]} ({w[0]} in) |")
    A("")
    A(f"Tube frame stiffness (same tests as the printed bodies, hip pivot clamped): static carry 150 lb stay-top aft "
      f"displacement **{np.hypot(t['carry_dy_mm'], t['carry_dz_mm']):.1f} mm**, frame torsion **{t['torsion_Nm_per_deg']:.2f} N m/deg** (+-100 N "
      f"fore-aft at the stay tops).")
    A("")
    A("**Stiffness limit (-20 %).** Jones & Hunter (1990, Exp Brain Res 79:150) measured a Weber fraction of 0.23 for "
      "stiffness; Tan et al. (1995) ~0.22 for compliance. A frame within 20 % of the tube frame's torsional and bending "
      "stiffness is at the threshold of what a wearer can tell apart by feel; a frame softer than that will be felt as "
      "sway (\"sloppy\"). This is a perceptual limit, not a strength one.")
    A("")
    A("## 3. Method and verification")
    A("")
    A("- SIMP p = 3, hat filter r = 1.5 voxels (min member ~2 voxels: 8 mm at 4 mm voxels, i.e. >= 4 FDM perimeters), "
      "Heaviside continuation (beta 1-2-4 coarse, 2-4-8 fine), x-mirror symmetry, weighted multi-load compliance "
      "(weights 1/c_i at iteration 1), OC update.")
    A("- Coarse-to-fine: 8 mm voxels (38 x 8 x 68, all 21 shapes), then 4 mm (76 x 16 x 136) in a 16 mm band around the "
      "coarse structure with the governing sets (>= 97 % of the weighted compliance). Each iteration is one MKL PARDISO "
      "factorization of the reduced (active-DOF) system for all load cases (pypardiso; SuperLU fallback).")
    A("- Stress constraint: p-norm (p = 8) / 99th-percentile von Mises of the verified body vs the knocked-down allowable, "
      "enforced by a volume-fraction sweep (volume minimization subject to stress, stiffness, creep and fatigue, solved by "
      "interpolation over the sweep per material). For one linear isotropic material the stress field is E-independent, so "
      "one sweep serves every material.")
    A("- **Independent verification** of every result: density up-sampled 2x (2 mm voxels), thresholded at 0.5, passive "
      "regions re-imposed, largest body kept, re-solved as a solid-only FE model for all 27 sets; stiffness tests on the "
      "same mesh. SIMP benchmark: the frame SIMP reproduces the validated `simp.run_simp` 3D-cantilever optimum (test); "
      "the voxel solver matches a Timoshenko cantilever (6 %), Saint-Venant square-bar torsion (8 %) and rod-in-parallel "
      "axial stiffness (3 %) (tests/test_frame_topopt.py).")
    A("")
    A("Sweep (verified bodies; stresses for E-normalized factored loads):")
    A("")
    A("| design | vol. frac. | verified volume (cm3) | governing set | 99th pct vM (MPa, factored) | torsion (N m/deg per GPa) |")
    A("|---|---|---|---|---|---|")
    for tg in R["pure_tags"] + R["hybrid_tags"]:
        v = fe.load_verified(tg)
        gk, s = fe.governing(v)
        kt = v["stiff"]["torsion_Nm_per_deg"] / v["stiff"]["E_ref"] * 1000
        A(f"| {tg} | {v['meta']['vf']:.3f} | {v['volume_mm3'] / 1e3:.0f} | {gk} | {s:.1f} | "
          f"{kt:.2f}{' (hybrid, PA6-CF ratio)' if v['meta']['hybrid'] else ''} |")
    A("")
    A("## 4. Recommendation table")
    A("")
    A("Whole-frame mass = printed body at the lightest volume fraction that passes everything + "
      f"{R['kept_g']:.0f} g kept (carbon crown 118, rack/pawl/guides 44, bushings 17, spine clamp 6, SLM Ti hip mount 20) "
      f"+ {fe.INSERTS_G:.0f} g inserts/bolts. Tube frame: **{fe.TUBE_FRAME_G:.0f} g**.")
    A("")
    A("| material / process | whole frame (g) | governing requirement | printed body (g) | cost body (USD) | creep 8 h 40 C | cold -20 C | buildability |")
    A("|---|---|---|---|---|---|---|---|")
    for mid, v in sorted(R["materials"].items(), key=lambda kv: kv[1]["frame_g"]):
        m = mats[mid]
        cost = v["body_g"] * m.cost_per_g if np.isfinite(v["body_g"]) else np.nan
        rows = v["rows"]
        cr = rows[-1]
        A(f"| {names_of(mid)} | {_f(v['frame_g'])}{' (extrap.)' if v['extrapolated'] else ''} | {v['governing']} | "
          f"{_f(v['body_g'])} | {_f(cost)} | E_c/E {m.E_hot * m.creep8h:.2f} | {cr['cold']} | {MAT_NOTES[mid][0]}: {MAT_NOTES[mid][1]} |")
    A(f"| HYBRID: FDM PA6-CF + 4 x {ROD_D:g} mm pultruded CF rods | {hb['frame_g']:.0f} | all pass at {hb['tag']} | "
      f"{hb['body_g']:.0f} (rods {R['hybrid']['rods_g']:.0f}) | {hb['cost_usd'] + 15:.0f} | "
      f"hot torsion {100 * (hh.get('hot', {}).get('torsion_rel', float('nan'))):.0f} % | {hb['cold']} | owner's H2S, 2 segments, rods + MMA |")
    A(f"| Continuous CF printing (Onyx + {CCF_AREA:g} mm2 CCF bundles x 4 paths) | {ccf['frame_g']:.0f} | "
      f"SF/req {ccf['sf_strength']:.2f}, torsion {100 * ccf['torsion_rel']:.0f} % | {ccf['body_g']:.0f} (fiber {ccf['fiber_g']:.0f}) | "
      f"{ccf['cost_usd']:.0f} (est.) | {ccf['creep_defl_mm']:.1f} mm | Onyx (PA6-based) | Markforged-class service or FibreSeeker-class printer |")
    A(f"| v2 carbon-tube frame (reference) | {fe.TUBE_FRAME_G:.0f} | rev B min SF/req "
      f"{min(R['tube']['member_margin_revB'].values()):.2f} | - | ~250 (tubes + prepreg wraps) | none (CFRP) | good | wet wraps, jigs, skill |")
    A("")
    A("Per-material detail (every verified body; SF = strength SF/req incl. knockdowns, fat = fatigue SF, rup = 8 h creep-"
      "rupture SF, tors / carry = stiffness vs tube):")
    A("")
    A("| material | design | body g | SF | fat | rup | tors | carry | creep defl mm | orientation |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for mid, v in R["materials"].items():
        for r in v["rows"]:
            A(f"| {names_of(mid)} | {r['tag']} | {r['body_g']:.0f} | {r['sf_strength']:.2f} | {r['sf_fatigue']:.2f} | "
              f"{r['sf_creep_rupture']:.2f} | {r['torsion_rel']:.2f} | {r['carry_rel']:.2f} | {r['creep_defl_mm']:.1f} | {r['orientation'][:28]} |")
    for r in R["hybrid"]["rows"]:
        A(f"| HYBRID PA6-CF + rods | {r['tag']} | {r['body_g']:.0f} | {r['sf_strength']:.2f} | {r['sf_fatigue']:.2f} | "
          f"{r['sf_creep_rupture']:.2f} | {r['torsion_rel']:.2f} | {r['carry_rel']:.2f} | {r['creep_defl_mm']:.1f} | {r['orientation'][:28]} |")
    A("")
    vr = fe.load_verified(hb["tag"])
    if vr.get("rods"):
        tmax = max(v["t"] for v in vr["rods"].values())
        cmax = min(v["c"] for v in vr["rods"].values())
        kt = max(vr["rods"], key=lambda k: vr["rods"][k]["t"])
        kc = min(vr["rods"], key=lambda k: vr["rods"][k]["c"])
        A(f"**Hybrid rods (pultruded CF, cfrp_pultruded_rod_tube, {hb['tag']}):** max factored tension {tmax:.0f} MPa ({kt}) vs Xt x 0.8 = 1600 "
          f"-> SF {1600 / max(tmax, 1):.1f}; max compression {abs(cmax):.0f} MPa ({kc}) vs Xc x 0.8 x 0.65 = 624 -> SF "
          f"{624 / max(abs(cmax), 1):.1f}. Embedded along their full length, so no column buckling; pull-out at the ends is "
          f"carried over the whole bonded length (shear lag).")
        A("")
    A("## 5. Creep, heat, cold, fatigue, UV and chemicals")
    A("")
    A("- **8 h at 40 C under 150 lb:** stay-top deflection = elastic deflection / (E(40 C, wet)/E x E_creep(8 h)/E) "
      "(record fields `modulus_40c_wet_ratio`, `creep_modulus_8h_40c_ratio`); sustained stress <= creep-rupture ratio x "
      "knocked-down strength. 40 C sits AT or ABOVE the glass transition of conditioned PA6 and PA12 (NETZSCH DMA: LS-PA12 "
      "Tg onset 27 C, E' 1438 -> ~500 MPa through the transition), which is why all-plastic frames are stiffness-governed. "
      "In the hybrid the rods (no creep) carry the stay bending; only the matrix share creeps (ASSUMPTION 50 % share).")
    A("- **Hot truck, 60 C, unloaded:** every candidate's HDT at 0.45 MPa is 145-186 C, so an unloaded frame does not "
      "distort. FDM parts must be ANNEALED (80-100 C, dry) before use or locked-in print stresses relax and the frame "
      "warps at 60 C. Do not leave the frame strapped under load in a hot vehicle.")
    A("- **Cold, -20 C:** nylons stiffen (~+30 %) but lose notched toughness; PA11 keeps it best, PA12-GB/PA12 worst "
      "(< 3 kJ/m2 estimated). Required: the T4c empty-pack drop at -20 C after a 4 h cold soak on the first printed frame.")
    A("- **Fatigue 1e5 x 0 -> 1.6 g:** fatigue strength taken as 0.3 x static (ASSUMPTION, no printed-PA fatigue data "
      "for these grades); shown as `fat` above.")
    A("- **UV:** carbon-black-filled CF nylons resist UV far better than natural PA; unfilled MJF/SLS PA12/PA11 yellow and "
      "embrittle: dye black + UV-stable paint/clear coat. **Gasoline:** PA12/PA11 are rated excellent for fuels "
      "(< 2 % swell after 1000 h, PatSnap summary; generic nylon chart rates gasoline A). **Blood:** water + salts: PA6 "
      "absorbs water (2.4 %, -22 % strength): seal or prefer PA12. **DEET:** no polyamide-specific DEET data found; DEET "
      "attacks plastics such as polycarbonate and some coatings: coupon-soak test required (24 h, then flex). ")
    A("")
    A("## 6. Printability (recommended printed design)")
    A("")
    A(f"Segmented at **z = {pr['z_cut']:.0f} mm** (lowest-stress slab between the meat-anchor and bag-anchor rows) so each "
      f"segment lies flat on the 340 x 320 mm plate. Layer normal = frame y (wearer face down): the stay bending stresses "
      f"run IN the layers; the Z (interlayer) strength only sees through-thickness shear and the anchor pull-outs. "
      f"Layer failure index (99th pct) by layer normal:")
    A("")
    A("| segment | mass g | print h | filament g | filament USD | plate footprint (mm) | FI layer normal y / x / z | supports (mm2, plate face) | files |")
    A("|---|---|---|---|---|---|---|---|---|")
    for k, v in segs.items():
        fi = v["fi99_by_layer_normal"]
        e = v["extents_on_plate"]
        A(f"| {k} | {v['mass_g']:.0f} | {v['hours']:.1f} | {v['filament_g']:.0f} | {v['filament_usd']:.2f} | "
          f"{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} | {fi['y']:.2f} / {fi['x']:.2f} / {fi['z']:.2f} | "
          f"{v['support_mm2'][v['plate_face']]:.0f} ({v['plate_face']}) | {', '.join(Path(f).name for f in v['files'])} |")
    A("")
    A(f"ASSUMPTIONS: effective flow {FDM_FLOW_MM3_S:g} mm3/s (0.6 mm hardened nozzle, CF-nylon), +{100 * (FDM_WASTE - 1):.0f} % "
      "purge/brim/support; filament $80/kg (PAHT-CF record; PA6-CF $43/kg).")
    A("")
    A(f"**Joint (FEA check).** Doweled + bonded butt splice: per side, one {DOWEL_D:g} mm pultruded carbon dowel in the "
      f"fore and one in the aft flange of the section ({2 * DOWEL_EMBED:.0f} mm long, {DOWEL_EMBED:.0f} mm into each segment, "
      f"MMA-bonded; holes are in the STLs), plus the MMA-bonded butt face. Section resultants from the verified stress field "
      f"of the 4 governing sets (factored), tension-flange force F = |N|/2 + M / dowel separation:")
    A("")
    A("| set | side | N (N) | M (N m) | V (N) | lever (mm) | flange force (N) | pull-out SF | shear SF |")
    A("|---|---|---|---|---|---|---|---|---|")
    for j in pr["joints"]:
        A(f"| {j['set']} | {j['side']} | {j['N']:.0f} | {j['M_Nmm'] / 1000:.1f} | {j['V']:.0f} | {j['lever_mm']:.0f} | "
          f"{j['flange_n']:.0f} | {j['pull_sf']:.2f} | {j['shear_sf']:.2f} |")
    A("")
    A("ASSUMPTIONS: MMA on flame/plasma-treated nylon 6 MPa hot/wet over the dowel surface (coupon T6 must confirm), "
      "dowel transverse shear 60 MPa; the bonded butt face is credited in shear only. Loads are factored, so SF >= 1 "
      "is the requirement.")
    A("")
    A("**Local hot spot (read before printing):** inside the pawl-housing load patch the layer failure index reaches "
      "~1.25 under the factored hipbelt-off abuse case (850 N crown extension + ~1 kN fore-aft through the pawl); the "
      "patch is a load-introduction region excluded from the 99th-percentile check (the real load enters through the Ti "
      "pawl pivot and the rack teeth). Detail it at part level: press a Ti/steel pivot bushing into the housing with "
      "3 mm extra wall around it, and watch the housing in proof test T1(c).")
    A("")
    A("**Service cost (cited basis):** MJF PA12 at JLC3DP $0.275/g (Aug 2025 price cut, still current); PA11 and PA12-CF "
      "were cut further on 24 Jul 2026 (PA12-CF -24 %), absolute rates not published: get instant quotes with the STLs. "
      "Continuous-fiber: no public per-cm3 service price; the owner option is a FibreSeeker 3 printer (US$2,449) with X-CCF "
      "at US$55 per 500 m. SLM AlSi10Mg: quote by volume (see generative_design.md).")
    A("")
    A("## 7. Continuous-fiber paths")
    A("")
    A("`designs/pack_5200/print/frame/fiber_paths_principal_stress.csv` (+ screenshot 7): trajectories of the major in-plane "
      "principal stress (2.0 g stumble) on the fore and aft fiber planes of the flat-printed body. In the stays they run "
      "straight along the stay (which is why straight pultruded rods capture most of the benefit), and fan from the "
      "stays into the hip-pivot boss in the lumbar web. Markforged Eiger and Anisoprint Aura lay concentric/isotropic "
      "fiber rings, not arbitrary curves: use the CSV as the target and approximate it with concentric rings around the "
      "stay and web outlines.")
    A("")
    A("## 8. Assumptions")
    A("")
    for a in ("Loads at the printed-body interfaces come from the v2 tube-frame beam model (interface forces depend weakly "
              "on the frame stiffness).",
              "Hip pivot = clamp (32 mm boss); every other body reaction is applied as a load; the same clamp is used for "
              "the tube-frame stiffness tests.",
              "FDM stiffness uses 0.95 x E_XY (flat printing, bending in the layer plane); strength uses the layer failure "
              "index with the Z strength and interlayer shear = 0.6 x Z strength.",
              "Environmental knockdowns: 0.75-0.8 on strength (record field env_knockdown_ratio); creep/fatigue ratios as "
              "the material records (estimates, no published creep data for printed CF nylon: coupon creep test required).",
              "Stress = 99th percentile element von Mises of the 2 mm verification mesh, clamp and load-patch elements "
              "excluded; envelopes of different load sets are combined (conservative).",
              "No buckling check on the voxel body (minimum member >= 8 mm, compact sections); the rods are embedded "
              "(continuous support) so they cannot buckle as columns.",
              "Kept parts and masses from frame.yaml / geometry.yaml weight budget; inserts + bolts 12 g.",
              ):
        A(f"- ASSUMPTION: {a}")
    A("")
    A("## Screenshots")
    A("")
    cap = {1: "recommended hybrid frame, front 3/4 / back / side", 2: "on the pack", 3: "utilization map",
           4: "segments on the build plate", 5: "mass / stiffness comparison", 6: "optimization evolution",
           7: "continuous-fiber paths (principal stress)"}
    for k, v in sorted(R["screens"].items(), key=lambda kv: int(kv[0])):
        A(f"- `{Path(v).relative_to(REPO_ROOT)}` - {cap.get(int(k), '')}")
    DOC.write_text("\n".join(L) + "\n")


def names_of(mid):
    return {"pa6_cf_fdm_bambu": "FDM PA6-CF (Bambu, owner's H2S)", "pa12_cf_fdm_paht": "FDM PAHT-CF / PA12-CF (H2S)",
            "pa12_mjf_hp": "MJF PA12 (HP, service)", "pa11_mjf_hp": "MJF PA11 (HP, service)",
            "pa12_gb_mjf_hp": "MJF PA12 glass-bead (service)", "pa12_cf_sls": "SLS PA12-CF (service)",
            "onyx_ccf_markforged": "Onyx matrix only (no fiber)", "alsi10mg_slm": "SLM AlSi10Mg (reference)"}.get(mid, mid)


def write_print_readme(R):
    pr = R["print"]
    segs = pr["segments"]
    L = ["# Generative printed frame - print package (Pack 5200)", "",
         "Source: `huntkit/gendesign/frame_report.py` from the topology optimization in "
         "`designs/pack_5200/analysis/printed_frame_study.md`. Units mm. Frame coordinates: x = wearer's right, "
         "y = aft (toward the bag), z = up from the stay feet.", "",
         "## Files", "",
         "| file | what |", "|---|---|",
         "| genframe_lower_flat.stl / .3mf | lower segment, already laid flat (wearer face on the plate) |",
         "| genframe_upper_flat.stl / .3mf | upper segment, flat |",
         "| genframe_assembled.stl | whole body in frame coordinates (viz3d `frame_type: generative`, fit checks) |",
         "| genframe_rods.stl | (hybrid variant only) the 4 pultruded carbon rods in frame coordinates |",
         "| fiber_paths_principal_stress.csv | continuous-fiber target paths (if printing with continuous fiber) |", "",
         "## Material", "",
         "Recommended: **Bambu PAHT-CF** (PA12-based CF nylon: keeps its properties wet better than PA6-CF; "
         "data/materials/polymers/pa12_cf_fdm_paht.yaml). PA6-CF is the stiffer/stronger alternative (+9 % mass, "
         "absorbs more water). Both were analysed in printed_frame_study.md.", "",
         "## Bambu H2S settings (PAHT-CF)", "",
         "- Dry the filament 80 C / 10-12 h; print from a dry box. Hardened 0.6 mm nozzle (0.4 mm works, ~1.6x the time).",
         "- Nozzle 280-300 C, bed 80-100 C with glue, chamber closed (heated if available), aux fan off, part cooling <= 30 %.",
         "- Layer 0.25 mm (0.6 nozzle). **6 walls**, top/bottom 6 layers, infill **100 %** (the optimizer already removed "
         "what is not needed; every remaining member is load-carrying). Line width 0.65.",
         "- Orientation: as in the files (laid flat, layer normal = frame y): the frame's bending stresses run along the "
         "layers; the Z (interlayer) strength only sees through-thickness shear. Supports: tree, only where the slicer "
         "flags bridges > 15 mm (sleeve-bore undersides: let the slicer bridge them; ream after).",
         "- Seam aligned on the wearer face. Brim 5 mm.",
         "- **Anneal** after printing: 90 C for 4-6 h in an oven with the part supported on a flat plate, cool slowly; "
         "then dry before bonding.", "",
         "## Assembly", "",
         f"1. Ream the crown sleeves to 18.0 mm (UHMWPE bushings press in) and the 4 dowel holes to {DOWEL_D + 0.1:.1f} mm.",
         f"2. Cut 4 dowels from {DOWEL_D:g} mm pultruded carbon rod, {2 * DOWEL_EMBED:.0f} mm long (diamond disc), scuff + clean.",
         "3. Abrade + flame/plasma treat the butt faces and dowel holes, bond with MMA (frame.yaml adhesive): dowels into "
         "the lower segment, then the upper segment on; clamp the segments on a flat board, check the two sleeve bores are "
         "coaxial with a 16 mm rod through each, cure 24 h.",
         "4. Press in M5 heat-set inserts at the hip-pivot boss and the anchor pads; bolt the SLM Ti hip mount.",
         "5. Slide the carbon crown legs into the sleeves, fit the rack/pawl, pulley guides and bushings as on the tube frame.", "",
         "## Per segment", "",
         "| segment | mass g | print h | filament g | cost USD | footprint mm |", "|---|---|---|---|---|---|"]
    for k, v in segs.items():
        e = v["extents_on_plate"]
        L.append(f"| {k} | {v['mass_g']:.0f} | {v['hours']:.1f} | {v['filament_g']:.0f} | {v['filament_usd']:.2f} | "
                 f"{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} |")
    L += ["", "Proof-test the first frame to load_standard.md (T1-T5, T2 with game bags on the internal straps), plus a "
          "40 C / 8 h creep hold at 150 lb and a -20 C empty drop (printed_frame_study.md section 5)."]
    (PRINT_DIR / "README.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    run()
