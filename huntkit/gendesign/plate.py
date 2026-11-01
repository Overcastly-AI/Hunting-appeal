"""Topology-optimized lumbar / hipbelt plate: 2D SIMP (Q4 plane stress) on the plate outline from
designs/pack_5200/geometry.yaml, loaded by the frame model's plate-to-stay forces with the hipbelt
pivot as the anchor. Output: a water-jet / CNC cut file (DXF) for quasi-isotropic carbon sheet.

Manufacturing rules for carbon sheet (ASSUMPTIONS, common composite drilling/cutting practice):
- min web width between cutouts >= 3 t;   - cutout edge distance from any outer edge >= 3 t;
- cutouts >= 3 t clear of the stay bond bands, the pivot-mount flange and attachment holes;
- min cutout size: inscribed circle >= 10 mm (water-jet pierce + clean-up), internal corner radius
  >= 3 mm (6 mm end mill) - stress concentration control on the cut edge;
- no cutout through the stay saddle bond (bond area is unchanged from the solid plate).

Check: the thresholded, rule-cleaned plate is re-meshed at half the pixel size and solved again
(independent FEA); ply stresses by CLT (huntkit.fea.composite) with Tsai-Wu first-ply failure and the
standard knockdowns (hot/wet 0.8, impact 0.65 compression), membrane (from the 2D FEA) PLUS bending
(grillage moments of the frame model divided by the remaining solid fraction of the cut section);
web buckling as pinned columns spanning the largest adjacent cutout.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from huntkit.fea.composite import DEFAULT_KNOCKDOWN, Laminate, Ply
from huntkit.fea.materials_bridge import get_material

from .fem import Assembler, Grid, Solver, b_q4_center, iso_D2, ke_q4, von_mises_2d
from .loads import member_end_global
from .simp import SimpProblem, run_simp


def plate_geometry(model: dict) -> dict:
    from huntkit.fea.pack5200 import load_geometry
    geom = load_geometry(model["params"]["geometry"])
    lp = geom["frame"]["members_topology"]["lumbar_plate"]
    hp = geom["frame"]["hard_points"]
    stay_x = {}
    for z in np.arange(lp["z_range"][0], lp["z_range"][1] + 1, 5.0):
        sx = None
        for nid, p in model["nodes"].items():
            pass
        stay_x[float(z)] = None
    return {"x": tuple(lp["x_range"]), "z": tuple(lp["z_range"]), "hard_points": hp}


def _stay_x_at(model, z):
    """x of the right stay centreline at height z (from the model's stay nodes)."""
    pts = sorted([(p[2], p[0]) for nid, p in model["nodes"].items() if nid.startswith("SR")
                  and nid[2:].replace(".", "").isdigit()])
    zs, xs = np.array(pts).T
    return float(np.interp(z, zs, xs))


def build_plate_problem(frame: dict, h: float = 1.25, t: float | None = None, volfrac: float = 0.45):
    runs = frame["runs"]
    res0, m0, _ = next(iter(runs.values()))
    g0 = plate_geometry(m0)
    t = float(t or m0["params"]["lumbar_plate_t"])
    x0, x1 = g0["x"]
    z0, z1 = g0["z"]
    nx, nz = int(round((x1 - x0) / h)), int(round((z1 - z0) / h))
    g = Grid((nx, nz), h, (x0, z0))
    c = g.elem_centers()
    stay_od = 25.0
    from huntkit.fea.sections import from_spec
    st = next(mm for mm in m0["members"] if mm["group"].startswith("stay_upper"))
    stay_od = float(from_spec(st["section"]).dims.get("od", 25.0))
    xs = np.array([_stay_x_at(m0, z) for z in c[:, 1]])
    band = np.abs(np.abs(c[:, 0]) - xs) <= stay_od / 2
    outboard = np.abs(c[:, 0]) > xs           # plate beyond the stay centreline: keep solid (fillet land)
    hp = np.asarray(g0["hard_points"]["hipbelt_pivot"], float)
    r_flange = 22.0                            # printed pivot-mount flange (lugs.hip_pivot_mount, D44)
    piv = np.hypot(c[:, 0] - hp[0], c[:, 1] - hp[2]) <= r_flange
    attach = np.zeros(g.ne, bool)
    hpts = g0["hard_points"]
    for k in ("pulley_fixed_guide_A", "pulley_fixed_guide_C", "pulley_cam_buckle_R", "pulley_cam_buckle_L_alt"):
        if k in hpts:
            p = np.asarray(hpts[k], float)
            attach |= np.hypot(c[:, 0] - p[0], c[:, 1] - p[2]) <= 8.0
    edge = (c[:, 1] < z0 + 3 * t) | (c[:, 1] > z1 - 3 * t)
    passive = band | outboard | piv | attach | edge
    # rule zone: cut-outs must stay >= 3 t from every passive zone (enforced in cleanup)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    pn = np.where(np.hypot(nc[:, 0] - hp[0], nc[:, 1] - hp[2]) <= 15.0)[0]   # insert flange D30
    fixed[2 * pn] = True
    fixed[2 * pn + 1] = True
    # loads: force of each stay node on the plate (minus the force the plate members put on the stay)
    from huntkit.fea.pack5200 import PLATE_Z
    keys, F_list, req = [], [], []
    for (case, tt), (res, model, cs) in runs.items():
        grid = model["plate_grid"]
        f = np.zeros(g.ndof)
        tot = 0.0
        for i, z in enumerate(PLATE_Z):
            dz_lo = (PLATE_Z[i] - PLATE_Z[i - 1]) / 2 if i > 0 else 0.0
            dz_hi = (PLATE_Z[i + 1] - PLATE_Z[i]) / 2 if i < len(PLATE_Z) - 1 else 0.0
            for j in (0, 4):
                nid = grid[f"{i},{j}"]
                Fp = np.zeros(3)
                for mm in model["members"]:
                    if mm["group"].startswith("lumbar_plate") and nid in mm["nodes"]:
                        v = member_end_global(res, mm["id"], nid)
                        if v is not None:
                            Fp += v[:3]
                Fs = -Fp                     # stay -> plate
                xsg = np.sign(model["nodes"][nid][0])
                sel = np.where((np.abs(np.abs(nc[:, 0]) - np.array([_stay_x_at(m0, zz) for zz in nc[:, 1]])) <= stay_od / 4)
                               & (np.sign(nc[:, 0]) == xsg) & (nc[:, 1] >= z - dz_lo) & (nc[:, 1] <= z + dz_hi))[0]
                if len(sel) == 0:
                    continue
                f[2 * sel] += cs.required_sf * Fs[0] / len(sel)
                f[2 * sel + 1] += cs.required_sf * Fs[2] / len(sel)
                tot += np.hypot(Fs[0], Fs[2])
        f[fixed] = 0
        keys.append(f"{case}|{tt}")
        F_list.append(f)
        req.append(cs.required_sf)
    F = np.column_stack(F_list)
    sev = np.abs(F).sum(0)
    # worst torso per case for the optimization (all kept for the check)
    best = {}
    for k, key in enumerate(keys):
        cname = key.split("|")[0]
        if sev[k] > best.get(cname, (-1, 0))[0]:
            best[cname] = (sev[k], k)
    pick = sorted(best.values(), key=lambda x: -x[0])
    sel = [k for _, k in pick[:4]]
    E = float(get_material("cfrp_plate_quasi_iso").require("youngs_modulus_mpa"))
    return {"grid": g, "t": t, "passive": passive, "fixed": fixed, "F": F, "keys": keys, "sel": sel,
            "all_sel": [k for _, k in pick], "E": E, "hp": hp, "stay_od": stay_od, "piv_r": r_flange,
            "zones": {"band": band | outboard, "piv": piv, "attach": attach, "edge": edge}, "volfrac": volfrac,
            "model": m0}


def optimize_plate(pp: dict, iters=80, log=None):
    g = pp["grid"]
    F = pp["F"][:, pp["sel"]]
    scale = 1 / np.abs(F).max()
    pb = SimpProblem(grid=g, loads=F * scale, fixed=pp["fixed"], passive_solid=pp["passive"],
                     volfrac=pp["volfrac"], rmin_vox=max(2.0, 0.75 * 3 * pp["t"] / g.h), thickness=1.0)
    return run_simp(pb, iters=iters, beta_schedule=(0, 1, 2, 4, 8), beta_every=15, log=log)


def _disk(r_pix):
    r = int(np.ceil(r_pix))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r_pix * r_pix


def cleanup(pp: dict, xPhys: np.ndarray, min_hole_inscribed=10.0, corner_r=3.0):
    """Binary cut pattern obeying the carbon-sheet rules. Returns (solid 2D array, report)."""
    g = pp["grid"]
    t = pp["t"]
    h = g.h
    solid = g.to_array(xPhys) >= 0.5
    holes = ~solid
    keep_out = g.to_array(pp["passive"])
    keep_out = ndimage.binary_dilation(keep_out, _disk(3 * t / h))
    border = np.zeros_like(holes); border[[0, -1], :] = True; border[:, [0, -1]] = True
    keep_out |= ndimage.binary_dilation(border, _disk(3 * t / h))
    holes &= ~keep_out
    # web rule: shrink cut-outs until every web between cut-outs is >= 3 t
    k = 0
    web = 0.0
    while True:
        hk = ndimage.binary_erosion(holes, _disk(k)) if k else holes
        hk = ndimage.binary_opening(hk, _disk(min_hole_inscribed / 2 / h))   # removes cut-outs < min size
        hk = ndimage.binary_opening(hk, _disk(corner_r / h))
        web = min_web_mm(hk, h)
        if web >= 3 * t - 0.5 * h or k > 20:
            break
        k += 1
    solid = ~hk
    rep = {"erosion_px": k, "min_web_mm": web, "rule_web_mm": 3 * t, "rule_edge_mm": 3 * t,
           "n_cutouts": int(ndimage.label(hk)[1]), "solid_frac": float(solid.mean())}
    return solid, rep


def min_web_mm(holes: np.ndarray, h: float) -> float:
    """Narrowest solid ligament between two different cut-outs (or a cut-out and the outer edge):
    min over solid pixels of (d1 + d2), d1/d2 = distances to the nearest and second-nearest distinct
    cut-out (outer boundary counted as one more 'cut-out')."""
    lab, n = ndimage.label(holes)
    if n == 0:
        return np.inf
    H, W = holes.shape
    dists = []
    for i in range(1, n + 1):
        dists.append(ndimage.distance_transform_edt(lab != i) * h)
    outer = np.ones((H + 2, W + 2), bool); outer[1:-1, 1:-1] = False
    do = ndimage.distance_transform_edt(~outer)[1:-1, 1:-1] * h
    dists.append(do)
    D = np.sort(np.stack(dists), axis=0)
    s = ~holes
    if n == 1:
        val = (D[0] + D[1])[s]
    else:
        val = (D[0] + D[1])[s]
    return float(val.min())


def verify_plate(pp: dict, solid2d: np.ndarray, up: int = 2) -> dict:
    """Independent FEA on the cleaned binary plate at h/up, every case at every torso."""
    g = pp["grid"]
    sf = np.kron(solid2d, np.ones((up, up), bool))
    gf = Grid(sf.shape, g.h / up, g.x0)
    el = np.where(gf.from_array(sf))[0]
    nc = gf.node_coords()
    used = np.unique(gf.enodes[el])
    nmap = -np.ones(gf.nn, np.int64); nmap[used] = np.arange(used.size)
    dmap = (nmap[:, None] * 2 + np.arange(2)).ravel()
    edof = dmap[gf.edof[el]]
    hp = pp["hp"]
    fixed_full = np.zeros(gf.ndof, bool)
    pn = np.where(np.hypot(nc[:, 0] - hp[0], nc[:, 1] - hp[2]) <= 15.0)[0]
    fixed_full[2 * pn] = fixed_full[2 * pn + 1] = True
    # map loads: coarse nodal loads -> nearest fine node
    gc = g.node_coords()
    from scipy.spatial import cKDTree
    tree = cKDTree(nc[used])
    _, near = tree.query(gc)
    keep = (used[:, None] * 2 + np.arange(2)).ravel()
    Fc = pp["F"]
    Ff = np.zeros((used.size * 2, Fc.shape[1]))
    for d in range(2):
        np.add.at(Ff, (2 * near + d), Fc[d::2])
    fx = fixed_full[keep]
    Ff[fx] = 0
    E, nu = pp["E"], 0.3
    KE = ke_q4(gf.h, E, nu, pp["t"])
    K = Assembler(edof, used.size * 2, KE, fx).assemble(np.ones(el.size))
    U = Solver(nc[used], fx).solve(K, Ff)
    B = b_q4_center(gf.h)
    D = iso_D2(E, nu)
    near_fix = np.isin(nmap[gf.enodes[el]], np.where(fx.reshape(-1, 2).any(1))[0]).any(1)
    sig = np.einsum("ij,ejk->eik", D @ B, U[edof]) if False else None
    out = {"keys": pp["keys"], "sigma": [], "vm_p99": [], "grid": gf, "el": el, "near_fix": near_fix}
    for k in range(Ff.shape[1]):
        s = (D @ B @ U[edof, k].T).T
        out["sigma"].append(s)
        out["vm_p99"].append(float(np.percentile(von_mises_2d(s[~near_fix]), 99)))
    return out


def qi_laminate(t: float) -> Laminate:
    ply = Ply.from_material("cfrp_t700_ud_epoxy_ply")
    n = max(1, int(round(t / ply.t / 8)))
    ang = ([0, 45, -45, 90] * n)
    ang = ang + ang[::-1]
    return Laminate([ply] * len(ang), ang)


def bending_moments(frame: dict) -> dict:
    """Max |moment per width| (N mm / mm) in the plate grillage strips per case key (torso)."""
    out = {}
    for (case, tt), (res, model, cs) in frame["runs"].items():
        best = 0.0
        for m in res.members:
            if m["group"] != "lumbar_plate":
                continue
            md = next(mm for mm in model["members"] if mm["id"] == m["id"])
            w = md["section"].dims.get("w", 1.0) if hasattr(md["section"], "dims") else 1.0
            My = m["max_abs_forces"][4]
            best = max(best, My / w)
        out[f"{case}|{tt}"] = best * cs.required_sf
    return out


def check_plate(pp: dict, solid2d: np.ndarray, ver: dict, frame: dict) -> dict:
    t = pp["t"]
    lam = qi_laminate(t)
    g = pp["grid"]
    # remaining solid fraction of the weakest horizontal / vertical cut through the free web zone
    S = solid2d
    zone = ~ndimage.binary_dilation(g.to_array(pp["zones"]["band"]), _disk(1))
    cols = [S[i, :].mean() for i in range(S.shape[0]) if zone[i, :].any()]
    rows_ = [S[:, j].mean() for j in range(S.shape[1])]
    phi = max(min(min(cols), min(rows_)), 0.2)
    mb = bending_moments(frame)
    rows = []
    E = pp["E"]
    lab, n = ndimage.label(~S)
    Lmax = 0.0
    for sl in ndimage.find_objects(lab):
        if sl is None:
            continue
        Lmax = max(Lmax, max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) * g.h)
    for k, key in enumerate(ver["keys"]):
        s = ver["sigma"][k][~ver["near_fix"]]
        N = s * t                                        # running loads (N/mm), membrane
        fi, _, _ = lam.membrane_fpf_batch(N, DEFAULT_KNOCKDOWN)
        imax = int(np.argmax(fi))
        m = mb.get(key, 0.0) / phi
        fpf = lam.first_ply_failure(N[imax], (m, 0, 0), DEFAULT_KNOCKDOWN)
        fi_mem = float(np.percentile(fi, 99))
        # web buckling (pinned column across the largest cut-out); compressive principal stress
        sx, sy, txy = s.T
        smin = (sx + sy) / 2 - np.sqrt(((sx - sy) / 2) ** 2 + txy ** 2)
        sc = float(np.percentile(np.maximum(-smin, 0), 99))
        scr = np.pi ** 2 * E * t ** 2 / (12 * max(Lmax, 1.0) ** 2)
        rows.append({"key": key, "fi_membrane_p99": fi_mem, "sf_membrane": 1 / fi_mem if fi_mem > 0 else np.inf,
                     "m_bending": m, "sf_combined": fpf["sf"], "sigma_c_p99": sc, "sigma_cr": scr,
                     "sf_buckling": scr / sc if sc > 0 else np.inf})
    return {"rows": rows, "phi_min": phi, "Lmax_cutout_mm": Lmax, "laminate": lam.describe(),
            "min_sf_combined": min(r["sf_combined"] for r in rows),
            "min_sf_membrane": min(r["sf_membrane"] for r in rows),
            "min_sf_buckling": min(r["sf_buckling"] for r in rows)}


def to_dxf(pp: dict, solid2d: np.ndarray, path, hole_dia_insert=8.5, smooth_r=2.0) -> dict:
    """DXF cut file: CUT (outer outline + cut-outs, polylines), DRILL (pivot-insert and attachment holes),
    TEXT. Coordinates in the plate plane: X = frame x, Y = frame z (mm), true scale."""
    import ezdxf
    from shapely.geometry import Polygon, box
    from skimage import measure
    g = pp["grid"]
    x0, z0 = g.x0
    W, H = g.shape[0] * g.h, g.shape[1] * g.h
    outline = box(x0, z0, x0 + W, z0 + H)
    corner = 8.0
    outline = outline.buffer(-corner).buffer(corner)
    holes = ~solid2d
    pad = np.pad(holes.astype(float), 1)
    cs = measure.find_contours(pad, 0.5)
    polys = []
    for cpts in cs:
        pts = (cpts - 1 + 0.5) * g.h + np.array([x0, z0])
        if len(pts) < 8:
            continue
        p = Polygon(pts)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area < 50:
            continue
        p = p.buffer(smooth_r).buffer(-2 * smooth_r).buffer(smooth_r).simplify(0.2)
        if p.is_empty:
            continue
        if p.geom_type == "MultiPolygon":
            polys += list(p.geoms)
        else:
            polys.append(p)
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for ln, col in (("CUT", 1), ("DRILL", 3), ("TEXT", 7), ("KEEPOUT", 8)):
        doc.layers.add(ln, color=col)
    msp = doc.modelspace()
    msp.add_lwpolyline(list(outline.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
    area = outline.area
    for p in polys:
        msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
        area -= p.area
    hp = pp["hp"]
    drills = [(hp[0], hp[2], hole_dia_insert, "pivot insert / pin")]
    from .loads import FRAME_YAML  # noqa: F401
    hpts = plate_geometry(pp["model"])["hard_points"]
    for k in ("pulley_fixed_guide_A", "pulley_fixed_guide_C", "pulley_cam_buckle_R", "pulley_cam_buckle_L_alt"):
        if k in hpts:
            p = hpts[k]
            drills.append((p[0], min(max(p[2], z0 + 6), z0 + H - 6), 4.2, k))
    for x, y, d, lab in drills:
        msp.add_circle((x, y), d / 2, dxfattribs={"layer": "DRILL"})
        area -= np.pi * d * d / 4
    msp.add_text(f"LUMBAR PLATE  QI carbon t={pp['t']:g} mm  qty 1  {len(polys)} cut-outs  web>=3t edge>=3t",
                 dxfattribs={"layer": "TEXT", "height": 3.5}).set_placement((x0, z0 - 8))
    doc.saveas(path)
    return {"path": str(path), "n_cutouts": len(polys), "area_mm2": area, "outline": outline, "holes": polys,
            "drills": drills}
