"""BL-051: the H1 stay crown restored over the old US1 / US2 stub sites, and the checks re-run on the new print.

    python -m huntkit.gendesign.h1_crown --lug       # US1 / US2 lug FEA on the real stay section (cached, ~minutes)
    python -m huntkit.gendesign.h1_crown --body      # H1 body strength / fatigue / buckling on the restored body (heavy)
    python -m huntkit.gendesign.h1_crown             # crown profile, slice checks, joint, notch, md / json, figures

Ticket docs/backlog/BL-051-stay-crown.md. Defect: ``h1_lanes.strip_old_us`` (BL-049) removed every voxel outside the
stay CIRCLE inside the old US fairlead footprints, but the H1 stay is fuller than that circle on the bag face, so the
print's bag-face crown sat 2-4 mm low over z 86-104 (US1) and z 131-152 (US2). Fix at the source:
``h1_lanes.CROWN_RESTORE`` bridges the stay section across each strip zone (``h1_lanes._crown_bridge``).

Units mm, N, MPa, g. Frame coordinates: x lateral (R +), y towards the bag, z up from the stay feet.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_crown.json"
DOC = ANALYSIS / "h1_crown.md"
OUT = REPO / "outputs" / "h1_crown"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL051_"
PRINT = PACK / "print" / "frame_h1"

STAY_X = 115.0
# Crown continuity rule (test_h1_crown): over CROWN_Z the bag-face crown top on the stay axis (x +/-115) never drops
# more than CROWN_DROP_MAX below the plain stay's crown (median over REF_Z, a stretch with no fairlead), and no step
# between 1 mm slices exceeds CROWN_STEP_MAX. The BL-050 print fails both (7.7 against 9.8; 2.2 mm steps).
CROWN_Z = (92.0, 152.0)            # US1 cheek bottom (hinge throat ends at z 91) .. the US2 zone's top
REF_Z = (112.0, 126.0)             # plain stay between the US1 and US2 zones
CROWN_DROP_MAX = 0.5
CROWN_STEP_MAX = 1.0
# ASSUMPTION CROWN-SECTION: the lug FEA's stay stub takes the print's stay section at a plain height next to each
# station (US1: z 116, US2: z 122) in place of the r 9 circle; the restored stay over each zone is the intersection of
# the sections each side (h1_lanes._crown_bridge), so these are close to (not smaller than) it.
SECTION_Z = {"us1": 116.0, "us2": 122.0}
YC = {"us1": -1.78, "us2": -2.67}  # stay centre y at the stations (h1_fairleads.placed 'yc')
BEFORE = {"assembled_g": 995.1, "lower_g": 423.4, "upper_g": 543.5, "us_route_piece_g": 125.9,
          "us_route_piece_asm_g": 140.0, "hefit_g": 41.4}    # h1_bedfit.json / h1_bedfit.md (BL-050 export)


def _mesh(path=None):
    import trimesh
    return trimesh.load(path or PRINT / "h1_assembled.stl")


def crown_top(mesh, z: float, x: float) -> float | None:
    """Highest y where the line (x, z) cuts the print section at height z (None if it misses)."""
    s = mesh.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    if s is None:
        return None
    best = None
    for d in s.discrete:
        a, b = d[:-1], d[1:]
        cr = (a[:, 0] - x) * (b[:, 0] - x) <= 0.0
        for p, q in zip(a[cr], b[cr]):
            y = max(p[1], q[1]) if q[0] == p[0] else p[1] + (x - p[0]) * (q[1] - p[1]) / (q[0] - p[0])
            best = y if best is None else max(best, y)
    return None if best is None else float(best)


def crown_profile(mesh=None, z=(84.0, 166.0), dz: float = 1.0, xs=(STAY_X, -STAY_X)) -> dict:
    """{x: [(z, top_y)]} along the stay axes."""
    m = mesh if mesh is not None else _mesh()
    zz = np.arange(z[0], z[1] + 1e-6, dz)
    return {float(x): [(float(q), crown_top(m, float(q), float(x))) for q in zz] for x in xs}


def crown_continuity(mesh=None, offsets=(-3.0, 0.0, 3.0)) -> dict:
    """The continuity rule on lines along each stay (x = +/-(115 + offset), both sides): reference crown (median over
    REF_Z), lowest top over CROWN_Z, its drop below the reference, and the largest 1 mm step. pass = drop <=
    CROWN_DROP_MAX and step <= CROWN_STEP_MAX on every line. Per side, the worst line is reported."""
    m = mesh if mesh is not None else _mesh()
    out = {}
    for sgn, side in ((1.0, "R"), (-1.0, "L")):
        lines = []
        for off in offsets:
            x = sgn * (STAY_X + off)
            ref = float(np.median([crown_top(m, z, x) for z in np.arange(REF_Z[0], REF_Z[1] + 1e-6, 1.0)]))
            zz = np.arange(CROWN_Z[0], CROWN_Z[1] + 1e-6, 1.0)
            ys = np.array([crown_top(m, z, x) for z in zz], float)
            i = int(np.argmin(ys))
            steps = np.abs(np.diff(ys))
            j = int(np.argmax(steps))
            lines.append({"x": x, "ref_y": round(ref, 2), "min_y": round(float(ys[i]), 2), "min_z": float(zz[i]),
                          "drop_mm": round(ref - float(ys[i]), 2), "max_step_mm": round(float(steps[j]), 2),
                          "step_z": float(zz[j]),
                          "pass": bool(ref - ys[i] <= CROWN_DROP_MAX and steps[j] <= CROWN_STEP_MAX)})
        w = max(lines, key=lambda r: (not r["pass"], r["drop_mm"]))
        out[side] = dict(w, lines=lines, pass_all=all(r["pass"] for r in lines))
    out["pass"] = all(out[s_]["pass_all"] for s_ in ("R", "L"))
    return out


def stay_section(name: str, mesh=None, tol: float = 0.15) -> list:
    """The print's stay section at SECTION_Z[name] round the R stay (x 115, y YC), in the lug FEA's local frame
    (x - 115, y - yc), simplified to ``tol`` mm."""
    from shapely.geometry import Point, Polygon
    m = mesh if mesh is not None else _mesh()
    z = SECTION_Z[name]
    s = m.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    for d in s.discrete:
        pg = Polygon(d[:, :2]).buffer(0)
        if pg.contains(Point(STAY_X, YC[name])):
            pg = pg.simplify(tol)
            xy = np.asarray(pg.exterior.coords)[:-1] - np.array([STAY_X, YC[name]])
            return xy.round(3).tolist()
    raise ValueError(f"no stay section at z {z}")


def lug_crown(log=print) -> dict:
    """h1_lanes.lug_study with the real stay section (crown included) in place of the r 9 circle, next to the
    circle-stub record (BL-049 / BL-050)."""
    from . import h1_lanes as LN
    m = _mesh()
    polys = {n: stay_section(n, m) for n in LN.LANE_X}
    crown = LN.lug_study(log=log, stay_polys=polys)
    circ = LN.lug_study(log=None)
    from shapely.geometry import Polygon
    out = {}
    for n in LN.LANE_X:
        def reg(r):
            rows = r["rows"]
            regs = {}
            for rn in ("fairlead", "arm", "root"):
                v = [(rows[k]["regions"][rn]["fatigue"], rows[k]["regions"][rn]["sf"], k) for k in rows
                     if rn in rows[k]["regions"]]
                if v:
                    f, s_, k = min(v)
                    regs[rn] = {"fatigue": f, "sf_at": s_, "load": k,
                                "sf_min": min(rows[q]["regions"][rn]["sf"] for q in rows if rn in rows[q]["regions"])}
            return regs
        out[n] = {"section_z": SECTION_Z[n], "section_area_mm2": round(Polygon(polys[n]).area, 1),
                  "circle_area_mm2": round(float(np.pi * LN.lug_geom_inputs(n)["p"]["stay_r"] ** 2), 1),
                  "circle": {"worst_strength": circ[n]["worst_strength"], "worst_fatigue": circ[n]["worst_fatigue"],
                             "regions": reg(circ[n])},
                  "crown": {"worst_strength": crown[n]["worst_strength"], "worst_fatigue": crown[n]["worst_fatigue"],
                            "regions": reg(crown[n])}}
    return out


BODY_CHECK = "m1_u2.5_im3_bl051_crown"     # h1_buckling.full_check cache (the BL-049 lanes body, crown restored)
BODY_BEFORE = "m1_u2.5_im3_bl049_lanes"   # the record it replaces (h1_lanes.BODY_CHECK, the BL-049 / BL-050 body)
CRADLE_NAME = "cradle_lanes_bl051"         # h1_sleeve.body_eval cache in outputs/h1_lanes (BL-049: cradle_lanes)


def body(log=print) -> dict:
    """h1_lanes.body_check on the restored body under new cache names: h1_buckling.full_check (strength, fatigue,
    creep per kit and setting, member buckling, the z 234 joint; lane loads, real crown) and the bag-off cradle sets.
    ``h1_lanes.body_solid`` strips the old stubs with CROWN_RESTORE on."""
    from . import h1_buckling as B
    from . import h1_lanes as LN
    from . import h1_sleeve as S
    from . import h1_spine_channel as SC
    solid, info = LN.body_solid()
    orig = S.kit_sets
    with SC.real_crown_models(), SC._real_caches():
        S.kit_sets = LN.lane_kit_sets(orig)
        try:
            chk = B.full_check(BODY_CHECK, solid, log=log)
        finally:
            S.kit_sets = orig
    o_out = S.OUT
    S.OUT = LN.OUT
    try:
        cr = S.body_eval(CRADLE_NAME, solid, LN.cradle_sets(), log=log)
    finally:
        S.OUT = o_out
    return {"check": chk, "cradle": cr, "voxels": info}


def body_summary() -> dict | None:
    """Before (BL-049 / BL-050 body) and after (crown restored), per basis, from the caches; None if not run."""
    from . import h1_buckling as B
    from . import h1_lanes as LN
    p1, p0 = B.OUT / f"check_{BODY_CHECK}.json", B.OUT / f"check_{BODY_BEFORE}.json"
    c1, c0 = LN.OUT / f"body_{CRADLE_NAME}.json", LN.OUT / "body_cradle_lanes.json"
    if not (p1.exists() and c1.exists()):
        return None
    new, old = json.loads(p1.read_text()), json.loads(p0.read_text())
    keys = ("strength", "fatigue", "creep")

    def row(r):
        return {**{k: round(r["min"][k], 3) for k in keys}, "buckling": round(r["buckling_min"], 3),
                "joint_strength": round(r["joint_strength"], 3), "joint_fatigue": round(r["joint_fatigue"], 3)}
    out = {"bases": {b: {"before": row(old[b]), "after": row(new[b])} for b in B.BASES_CHECK if b in new and b in old},
           "raster_g": {"before": round(old["raster_g"], 1), "after": round(new["raster_g"], 1)},
           "governing_region": new.get("governing_region")}
    cn, co = json.loads(c1.read_text()), json.loads(c0.read_text())
    out["cradle"] = {"before": {**{k: round(co["min"][k], 3) for k in keys}, "buckling": round(co["buckling_min"], 3)},
                     "after": {**{k: round(cn["min"][k], 3) for k in keys}, "buckling": round(cn["buckling_min"], 3)},
                     "governing_tag": cn.get("governing_tag"), "top_regions": cn.get("top_regions")}
    return out


def mass_rows(ex: dict) -> dict:
    """Print masses against the BL-050 export (h1_bedfit.json export), from the export info of this print."""
    bf = json.loads((ANALYSIS / "h1_bedfit.json").read_text())["export"]
    a0 = bf["assembled"]["g"]
    return {"assembled_g": ex["assembled"]["g"], "assembled_bl050_g": a0,
            "print_delta_g": round(ex["assembled"]["g"] - a0, 1),
            "lower_g": ex["lower"]["g"], "lower_bl050_g": bf["lower"]["g"],
            "upper_g": ex["upper"]["g"], "upper_bl050_g": bf["upper"]["g"],
            "clevis_g": {k: ex[k]["g"] for k in ("us2_clevis_R", "us2_clevis_L") if k in ex},
            "lug_arms_g": round(ex["fairleads_bl042"]["lugs_bl049"]["arms_g"], 2)}


def us1_governs(lug: dict, bs: dict | None) -> dict:
    """Item 2: the US1 root on the stub model against the whole body, and which one governs."""
    u = lug["us1"]
    return {"stub_circle_fatigue": u["circle"]["regions"]["root"]["fatigue"],
            "stub_crown_fatigue": u["crown"]["regions"]["root"]["fatigue"],
            "stub_crown_strength": u["crown"]["regions"]["root"]["sf_min"],
            "body_cradle_fatigue": None if bs is None else bs["cradle"]["after"]["fatigue"],
            "body_cradle_fatigue_bl049": None if bs is None else bs["cradle"]["before"]["fatigue"],
            "governs": "stub_crown",
            "why": ("The whole-body model applies each US pin load at the stay node (force + the lane moment, "
                    "h1_lanes.lane_items): the arm carries no pin load there, so its root sees only the stay's global "
                    "stress. The stub model routes the pin load through the cheeks and the arm into the root, which "
                    "is what loads that root; its fixed stub ends leave out the lower branch (conservative) and the "
                    "global stay stress (unconservative). The stub number is the one to design to until the T1 / MT-1 "
                    "strain gauge at the US1 root settles it.")}


def compute(log=print, before_stl: Path | None = None) -> dict:
    from . import h1_bedfit as BF
    from . import h1_lanes as LN
    from . import spreader as SP
    m = _mesh()
    ex = json.loads((LN.OUT / "export_info.json").read_text())
    ur = json.loads((ANALYSIS / "us_route.json").read_text())
    pl = ur["layouts"]["print_lanes"]
    lug = json.loads((OUT / "lug_crown.json").read_text()) if (OUT / "lug_crown.json").exists() else lug_crown(log)
    bs = body_summary()
    old = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    before = None
    if before_stl is not None and Path(before_stl).exists():
        mb = _mesh(before_stl)
        before = {"continuity": crown_continuity(mb), "profile": crown_profile(mb)}
    elif old.get("before"):
        before = old["before"]
    res = {"date": "2026-11-13", "ticket": "BL-051",
           "cause": {"function": "huntkit.gendesign.h1_lanes.strip_old_us",
                     "rule": "voxels outside the stay circle (r + 1 mm) inside the old US fairlead footprint removed; "
                             "the H1 stay is fuller than the circle on the bag face, so its crown went too",
                     "fix": "h1_lanes.CROWN_RESTORE / _crown_bridge: the stay section bridged across each strip zone "
                            f"(reference planes {LN.CROWN_REF_VOX} voxels beyond each end, intersected)"},
           "rule": {"crown_z": list(CROWN_Z), "ref_z": list(REF_Z), "drop_max_mm": CROWN_DROP_MAX,
                    "step_max_mm": CROWN_STEP_MAX},
           "after": {"continuity": crown_continuity(m), "profile": crown_profile(m)},
           "before": before,
           "export": {k: {kk: ex[k].get(kk) for kk in ("g", "watertight", "shells", "footprint_mm", "bed_bl050")}
                      for k in ("assembled", "lower", "upper")},
           "slice_checks": LN.slice_checks(),
           "joint": {k: v for k, v in BF.joint_check().items() if k in ("worst_strength", "worst_fatigue",
                                                                         "capacities_n", "net_section")},
           "joint_share_1": {k: v for k, v in BF.joint_check(share=1.0).items() if k in ("worst_strength",
                                                                                          "worst_fatigue")},
           "joint_slices": BF.joint_slices(),
           "lug": lug,
           "us_route": {"print_lanes": {"worst_clear_mm": pl["worst_clear_mm"], "pass": pl["pass"]},
                        "test_piece": ur.get("test_piece")},
           "spreader_us2_notch": {k: v for k, v in SP.us2_notch_check().items() if k != "rows"},
           "body": bs,
           "mass": mass_rows(ex)}
    res["us1_root"] = us1_governs(lug, bs)
    RESULTS.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
    if log:
        log(f"  wrote {RESULTS.relative_to(REPO)}")
    return res


# ======================================================================================= figures
def _save(fig, path: Path) -> str:
    from .h1_bedfit import _save as s_
    return s_(fig, path)


def plot_profile(res: dict, path: Path) -> str:
    """Crown top along both stays, BL-050 print against BL-051, with the strip zones and the reference band."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, key in zip(axs, ("115.0", "-115.0")):
        for lab, src, st in (("BL-050 print (crown cut)", res.get("before"), dict(color="#c0392b", lw=1.6, ls="--")),
                             ("BL-051 print (restored)", res["after"], dict(color="#1f6f8b", lw=2.2))):
            if not src:
                continue
            pr = src["profile"][key] if key in src["profile"] else src["profile"][float(key)]
            z = [q[0] for q in pr if q[1] is not None]
            y = [q[1] for q in pr if q[1] is not None]
            ax.plot(z, y, label=lab, **st)
        for z0, z1, t in ((86, 104, "old US1 stub"), (131, 152, "old US2 stub")):
            ax.axvspan(z0, z1, color="#f2d7a6", alpha=0.45, lw=0)
            ax.text(0.5 * (z0 + z1), 6.15, t, ha="center", fontsize=9)
        ax.axvspan(*REF_Z, color="#d5e8d4", alpha=0.6, lw=0)
        ax.text(0.5 * sum(REF_Z), 6.15, "plain stay (reference)", ha="center", fontsize=9)
        ax.set_xlabel("height on the stay z, mm")
        ax.set_title(f"{'right' if key[0] != '-' else 'left'} stay (x {float(key):+.0f})", fontsize=11)
        ax.set_ylim(5.8, 12.6)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("bag-face crown top y, mm")
    axs[0].legend(loc="upper left", fontsize=9)
    fig.suptitle("BL-051: stay crown along the stay axis - the old US stub sites sat 2 mm low, now continuous",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    return _save(fig, path)


def plot_sections(path: Path, before_stl: Path | None) -> str:
    """Stay cross-sections at z 142 (US2 stub site) and z 96 (US1), before and after, with the plain stay at z 122."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import Point, Polygon, box
    m1 = _mesh()
    m0 = _mesh(before_stl) if before_stl is not None and Path(before_stl).exists() else None
    win = box(STAY_X - 16, -20, STAY_X + 16, 16)

    def sec(m, z):
        s = m.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
        out = []
        for d in s.discrete:
            pg = Polygon(d[:, :2]).buffer(0)
            if pg.intersects(win):
                out.append(pg.intersection(win))
        return out
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.9), sharey=True)
    for ax, (z, t) in zip(axs, ((96.0, "z 96 (old US1 site)"), (122.0, "z 122 (plain stay)"),
                                (142.0, "z 142 (old US2 site)"))):
        for mm, col, lab, fill in ((m1, "#1f6f8b", "BL-051", True), (m0, "#c0392b", "BL-050", False)):
            if mm is None:
                continue
            for pg in sec(mm, z):
                for g in getattr(pg, "geoms", [pg]):
                    if g.is_empty or not hasattr(g, "exterior") or g.area < 2.0:     # clip slivers
                        continue
                    x, y = g.exterior.xy
                    if fill:
                        ax.fill(x, y, color=col, alpha=0.35, lw=0)
                    ax.plot(x, y, color=col, lw=1.4 if fill else 1.6, ls="-" if fill else "--",
                            label=lab if g is getattr(pg, "geoms", [pg])[0] else None)
        ax.axhline(9.82, color="#555", lw=0.8, ls=":")
        ax.set_aspect("equal")
        ax.set_xlim(STAY_X - 16, STAY_X + 16)
        ax.set_title(t, fontsize=11)
        ax.set_xlabel("frame x, mm")
        ax.grid(alpha=0.25)
    axs[0].set_ylabel("frame y, mm (bag up)")
    h, l_ = axs[2].get_legend_handles_labels()
    seen = {}
    for hh, ll in zip(h, l_):
        seen.setdefault(ll, hh)
    axs[2].legend(seen.values(), seen.keys(), loc="lower right", fontsize=9)
    fig.suptitle("BL-051: right stay sections (dotted line: plain-stay crown y 9.8) - US arm roots blend under it",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    return _save(fig, path)


def plot_lug_field(path: Path) -> str:
    """US2 lug FEA (h1_lanes.lug_fea, governing row cradle|fleet_in), circle stub against the real stay section:
    fatigue utilization on the element layer at pin z + 4.5, displacement magnitude as the deformed outline."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import bag_attach as BA
    from . import h1_lanes as LN
    pa = BA._paht()
    gi = LN.lug_geom_inputs("us2")
    p = gi["p"]
    L = LN.lug_loads("us2")
    k = "cradle|fleet_in"
    loads = {k: L[k]["vec"]}
    gr = L[k]["g_times_req"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
    for ax, (lab, poly) in zip(axs, (("r 9 circle stub (BL-049 / BL-050)", None),
                                     ("real stay section, crown restored (BL-051)", stay_section("us2")))):
        f = LN.lug_fea(p["geom"], p["stay_r"], gi["xoff"], gi["arm"], loads, h=1.0, field=k, stay_poly=poly)
        fd = f["loads"]["_field"]
        c, fi, u = fd["cen"], fd["fi"], fd["u_elem"]
        sel = np.abs(c[:, 2] - 4.5) < 0.6
        util = fi[sel] * 1.6 / gr / pa["fat"]
        sc = ax.scatter(c[sel, 0] + LN.STAY_X, c[sel, 1], c=util, s=9, marker="s", cmap="inferno", vmin=0, vmax=1.2)
        ax.set_aspect("equal")
        ax.set_xlabel("frame x, mm")
        r = f["loads"][k]
        fr = r.get("root", {}).get("fi99", float("nan"))
        ax.set_title(f"{lab}\nroot fatigue SF {BA._fatigue_sf(fr, gr, pa['fat']):.2f}, max |u| {u.max():.2f} mm",
                     fontsize=10)
    axs[0].set_ylabel("frame y, mm")
    cb = fig.colorbar(sc, ax=axs, shrink=0.85)
    cb.set_label("fatigue utilization at 1.6 g (> 1 fails)")
    fig.suptitle("BL-051: US2 lug, bag-off cradle 720 N + 10 deg fleet, layer at pin z + 4.5",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    return _save(fig, path)


ASSUMPTIONS = [
    ("CROWN-BRIDGE", "The stay section over each old stub site is the intersection of the plain stay sections 4-8 mm "
     "beyond each end of the strip zone (h1_lanes._crown_bridge); what the topology body had under the old stub is "
     "unknown (the stub was a keep-in).", "Not needed for strength (the FEA uses this body); first-article slice / "
     "caliper of the crown at z 96 and z 142 against z 122 (within 0.5 mm)."),
    ("CROWN-SECTION", "The lug FEA's stay stub takes the print's plain stay section next to each station (US1 z 116, "
     "US2 z 122) in place of the r 9 circle; the stub still ends at +/-22-23 mm and leaves out the lower branch.",
     "Strain gauge at the US1 and US2 arm roots in T1 (and the MT-1 cradle pull) on the first article."),
    ("NOTCH-PROUD", "The z 142 spreader notch now sits over a plain stay crown: the rule is that nothing in the notch "
     "footprint stands proud of the sheet's support line (BL-050's 1.5 mm air rule was measured on the cut crown).",
     "Spreader dry fit on the first article: the sheet edge each side of the notch bears on the crown, no rocking."),
    ("US1-STUB-GOVERNS", "For the US1 arm root the stub model governs over the whole body (see section 4).",
     "Strain gauge at the US1 arm root, T1 (a) / (b) and the MT-1 cradle pull: measured root strain x E / the "
     "stub model's root stress at the same load <= 1.0."),
    ("Carried", "CLEVIS-SHARE, CLEVIS-DRY, CLEVIS-PRINT, SEAM-FLOOR, HEAD-PROUD, BED-ROT (h1_bedfit.md 7); STAY-STUB, "
     "LANE-MOMENT, HINGE-ROW, FI99-RULE (h1_lanes.md 6); US-FLEET, US-TOPO, DRAPE-US (us_route.json).", "as there"),
]

KIT_TEXT_FOR_BL050B = (
    "physical_test_kit.py, test T1 (and its TEST_PLAN / test_register rows): add 'strain gauges (1 mm foil, "
    "120 ohm, quarter bridge, cyanoacrylate on the sanded PAHT) on the US1 arm root (R side, bag face, 3 mm off the "
    "stay surface, gauge axis along the arm) and on the US2 arm root (same place); record at 0 / 150 / 300 lb in T1 "
    "(a)/(b) and at 240 / 480 / 720 N per pin in the MT-1 cradle pull; PASS: measured root stress (strain x 3.86 GPa, "
    "youngs_modulus_xy_mpa of data/materials pa12_cf_fdm_paht) <= the h1_crown lug model's root stress at that load (ASSUMPTION "
    "US1-STUB-GOVERNS / STAY-STUB / CROWN-SECTION)'. The CLEVIS-SHARE pull's 'optional strain gauge at the US2 arm "
    "root' becomes required, same gauge place.")


def write_md(res: dict, shots: list) -> str:
    a_ = []
    a = a_.append
    m = res["mass"]
    ca, cb = res["after"]["continuity"], (res.get("before") or {}).get("continuity")
    sc = res["slice_checks"]
    lug = res["lug"]
    bs = res["body"]
    sp = res["spreader_us2_notch"]
    u1 = res["us1_root"]
    a("# H1 stay crown restored at the old US stub sites (BL-051)\n")
    a("structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-051-stay-crown.md`. Code "
      "`huntkit/gendesign/h1_crown.py` (`python -m huntkit.gendesign.h1_crown --lug | --body`; the report with no "
      "flag); fix in `h1_lanes.strip_old_us` (`CROWN_RESTORE`, `_crown_bridge`); lug FEA option "
      "`h1_lanes.lug_fea(stay_poly=)`; spreader rule `spreader.us2_notch_check` (`proud_mm`); tests "
      "`tests/test_h1_crown.py`. Results `h1_crown.json`. Units mm, N, g (imperial in brackets). Supersedes the "
      "print, slice, notch and lug numbers of `h1_bedfit.md` and `h1_lanes.md` where they differ.\n")
    a("## Summary\n")
    if cb:
        a(f"- **Cause found:** `h1_lanes.strip_old_us` (BL-049) removed every voxel outside the stay *circle* "
          f"(r 9 + 1 mm) inside the old US1 / US2 fairlead footprints. The H1 stay is fuller than that circle on the "
          f"bag face (plain crown on the stay axis y {ca['R']['lines'][1]['ref_y']} R / {ca['L']['lines'][1]['ref_y']} "
          f"L), so its crown went with the stub: on the BL-050 print the axis crown sat at y "
          f"{cb['R']['lines'][1]['min_y']} (z {cb['R']['lines'][1]['min_z']:g}), {cb['R']['lines'][1]['drop_mm']} mm "
          f"low, and **{cb['R']['drop_mm']} mm** on the worst line (x {cb['R']['x']:+.0f}; L {cb['L']['drop_mm']} mm), "
          f"over z 131-152 and also over z 86-104 at the old US1 site.")
    a(f"- **Fixed at the source:** `CROWN_RESTORE` bridges the stay section across each strip zone (the plain stay "
      f"sections 4-8 mm beyond each end, intersected). Re-exported: crown continuity on x = +/-112, 115, 118 over z "
      f"{CROWN_Z[0]:g}-{CROWN_Z[1]:g}: worst drop **{max(ca['R']['drop_mm'], ca['L']['drop_mm'])} mm**, worst 1 mm "
      f"step {max(ca['R']['max_step_mm'], ca['L']['max_step_mm'])} mm (rule <= {CROWN_DROP_MAX} / "
      f"{CROWN_STEP_MAX}): **pass {ca['pass']}**. New test `test_crown_is_continuous`.")
    a(f"- **Print:** assembled {m['assembled_g']} g ({m['print_delta_g']:+.1f} g against BL-050 {m['assembled_bl050_g']}),"
      f" lower {m['lower_g']} g, upper {m['upper_g']} g, clevises {', '.join(f'{v} g' for v in m['clevis_g'].values())};"
      f" lower footprint {res['export']['lower']['bed_bl050']['extents_mm']} at "
      f"{res['export']['lower']['bed_bl050']['rot_deg']} deg, brim spare {res['export']['lower']['bed_bl050']['spare_mm']}"
      f" mm (unchanged). Every file one closed shell.")
    a(f"- **Slice checks** pass: fairleads {sc['fairleads_pass']} (12 / 12), spine channel {sc['channel']['pass']}, pawl "
      f"{sc['pawl']['pass']}, test pieces {sc['pieces_pass']}; US2 joint slices {res['joint_slices']['pass']}. "
      f"**us_route** print_lanes worst US1 {res['us_route']['print_lanes']['worst_clear_mm']['us1']} / US2 "
      f"{res['us_route']['print_lanes']['worst_clear_mm']['us2']} mm (>= 10): pass "
      f"{res['us_route']['print_lanes']['pass']}.")
    j, j1 = res["joint"], res["joint_share_1"]
    a(f"- **US2 clevis joint** (geometry unchanged, re-run): strength {j['worst_strength']['sf']} "
      f"({j['worst_strength']['check']}, {j['worst_strength']['load']}), fatigue "
      f"{j['worst_fatigue']['fatigue']} ({j['worst_fatigue']['check']}); share 1.0: {j1['worst_strength']['sf']} / {j1['worst_fatigue']['fatigue']}.")
    u2 = lug["us2"]
    a(f"- **US2 lug** on the real stay section (crown in): strength **{u2['crown']['worst_strength']['sf']}**, fatigue "
      f"**{u2['crown']['worst_fatigue']['fatigue']}** (root {u2['crown']['regions']['root']['fatigue']}, arm "
      f"{u2['crown']['regions']['arm']['fatigue']}); the r 9 circle stub of BL-049 / BL-050 gave "
      f"{u2['circle']['worst_strength']['sf']} / {u2['circle']['worst_fatigue']['fatigue']}.")
    if bs:
        fb = bs["bases"]
        worst = lambda k, w: min(v[w][k] for v in fb.values())
        a(f"- **Body** (h1_buckling.full_check, 4 bases, lane loads): strength {worst('strength', 'after'):.2f} "
          f"(was {worst('strength', 'before'):.2f}), fatigue {worst('fatigue', 'after'):.2f} (was "
          f"{worst('fatigue', 'before'):.2f}; fine_sm8.cyc, the BL-024 cinch-cycled set below 1 since BL-024, R1 hold "
          f"for MT-1, not this ticket; the other bases {min(v['after']['fatigue'] for b, v in fb.items() if not b.endswith('.cyc')):.2f}), buckling {worst('buckling', 'after'):.2f} (was "
          f"{worst('buckling', 'before'):.2f}), z 234 joint {worst('joint_strength', 'after'):.2f} / "
          f"{worst('joint_fatigue', 'after'):.2f}. Bag-off cradle: {bs['cradle']['after']['strength']:.2f} / "
          f"{bs['cradle']['after']['fatigue']:.2f} / buckling {bs['cradle']['after']['buckling']:.2f} (was "
          f"{bs['cradle']['before']['strength']:.2f} / {bs['cradle']['before']['fatigue']:.2f} / "
          f"{bs['cradle']['before']['buckling']:.2f}).")
    a(f"- **US1 root (item 2): the stub model governs, fatigue {u1['stub_crown_fatigue']}** on the real stay section "
      f"(0.80 on the circle stub); the whole body reads {u1['body_cradle_fatigue']} because it never puts the pin "
      f"load through the arm. **Below 1.0: target not met** (section 4). The T1 strain-gauge text is not in the kit; "
      f"the change is listed for BL-050B (section 4).")
    a(f"- **Spreader z 142 notch:** BL-050's '2.31 mm air' was the cut-away crown. With the crown back, the notch "
      f"footprint holds the plain crown, {sp['air_mm']} mm under the support line (old 1.5 mm air rule: "
      f"{sp['air_rule_pass']}). Rule now: nothing proud of the support line (proud {sp['proud_mm']} mm <= "
      f"{sp['proud_max_mm']}): pass {sp['pass']}. Closing the notch is now the natural option (owner).")
    a("- **Cleanup, n_pin (not done as written, on purpose):** of the 12 stations, `bag_attach._mass_budget` books 8 "
      "pins + sleeves and `meat_haul.cradle_parts_g` already books the US1 / US2 four ('under-straps US1/US2: 7075 "
      "pins (4)', 'UHMWPE sleeves (4)' = 10.8 g; CORRIE F books them in its 'US-anchor ... (frame side)' row). "
      "Setting n_pin to 12 would have booked them twice, and so did BL-050's '+10.80 g, 4 stations booked short' "
      "ledger row. Fixed at the source by making the count explicit (`bag_attach._pins_booked_here`, "
      "`CRADLE_PIN_STATIONS`) and retiring the BL050 row: **-10.8 g** on every config. `h1_lanes.md / .json` carry a "
      "superseded note; screws and washers have distinct BOM IDs and callouts (section 6).\n")

    a("## 1. Cause and fix\n")
    a("`strip_old_us` takes the old US1 / US2 fairlead stubs off the voxel body before the print mesh and the body "
      "FEA (BL-049). Its keep rule was 'inside the stay circle (r + 1 mm)'. On the H1 body the stay is not that "
      "circle: on the bag face it is a crown about 3 mm fuller (sections at z 116 / 122: "
      f"{lug['us1']['section_area_mm2']} / {lug['us2']['section_area_mm2']} mm2 against the circle's "
      f"{lug['us1']['circle_area_mm2']} / {lug['us2']['circle_area_mm2']} mm2). Over z 138-146 the release body had "
      "no crown either (the old stub's throat). `CROWN_RESTORE` now sets every voxel of each strip zone solid where "
      "the body is solid at the same (x, y) on all reference planes 2-4 voxels (4-8 mm) beyond both ends of the zone "
      "(1 voxel out still carries the old stub's edge blend: y 11 at z 103-107, which made a 1.5 mm hump in a first "
      "try). The restored stay is never fuller than the leaner side. The same function feeds the body FEA "
      "(`h1_lanes.body_solid`), so the FEA body and the print agree.\n")
    a("| line | rule | BL-050 print: min y (z) / drop / max step | BL-051 print: min y (z) / drop / max step | pass |")
    a("|---|---|---|---|---|")
    for side in ("R", "L"):
        for i, la in enumerate(ca[side]["lines"]):
            lb = cb[side]["lines"][i] if cb else None
            bb = f"{lb['min_y']} ({lb['min_z']:g}) / {lb['drop_mm']} / {lb['max_step_mm']}" if lb else "-"
            a(f"| x {la['x']:+.0f} | ref {la['ref_y']} | {bb} | {la['min_y']} ({la['min_z']:g}) / {la['drop_mm']} / "
              f"{la['max_step_mm']} | {la['pass']} |")
    a("")
    a("Residual: a 0.3-0.4 mm bump at z 104-108 (the old US1 stub's upper edge blend, outside the strip zone, in the "
      "print since BL-045) and the hinge throat's lead-out at z 88-91 (1 mm below the crown, part of the BL-049 hinge "
      "throat, not the crown).\n")

    a("## 2. Print files and slice checks\n")
    a("| file | g (BL-050) | g (BL-051) | watertight / shells | footprint mm |")
    a("|---|---:|---:|---|---|")
    ex = res["export"]
    a(f"| h1_assembled.stl | {m['assembled_bl050_g']} | {m['assembled_g']} | {ex['assembled']['watertight']} / "
      f"{ex['assembled']['shells']} | |")
    for nm in ("lower", "upper"):
        a(f"| h1_{nm}_flat.stl | {m[nm + '_bl050_g']} | {m[nm + '_g']} | {ex[nm]['watertight']} / {ex[nm]['shells']} | "
          f"{ex[nm]['footprint_mm']} (rot {ex[nm]['bed_bl050']['rot_deg']}, brim spare {ex[nm]['bed_bl050']['spare_mm']}) |")
    tp = res["us_route"]["test_piece"] or {}
    a(f"| test_pieces/us_route_stay_R.stl | 125.9 | {tp.get('g')} (as assembled {tp.get('g_as_assembled')}) | "
      f"{tp.get('watertight')} / {tp.get('shells')} | {tp.get('extents_mm')} |")
    a("")
    a(f"Slice checks on `h1_assembled.stl` (`h1_lanes.slice_checks`): fairleads {sc['fairleads_pass']}, every one "
      "with its eye stack:\n")
    a("| station | gap under pin | throat | cheek | cheek height | pass |")
    a("|---|---:|---:|---:|---:|---|")
    for k, v in sc["fairleads"].items():
        a(f"| {k} | {v['gap_under_pin']} | {v['throat']} | {v['cheek_mm']} | {v['cheek_height_mm']} | {v['pass']} |")
    a("")
    a(f"Spine channel clear {sc['channel']['min']['clear_mm']} mm: {sc['channel']['pass']}; pawl swing: "
      f"{sc['pawl']['pass']}; test pieces: {', '.join(f'{k} {v['pass']}' for k, v in sc['pieces'].items())}. "
      f"US2 joint slices (`h1_bedfit.joint_slices`): {res['joint_slices']['pass']}.\n")

    a("## 3. US2 lug, joint, strap route, spreader notch\n")
    a("Lug FEA (`h1_lanes.lug_fea`, 1 mm voxels, every US load: cradle 720 N at 2.4, bag-on at 3.0, +/-10 deg fleet). "
      "BL-049 / BL-050 modelled the stay as the r 9 circle; the crown that is now printed is in the second model "
      "(the print's plain stay section next to the station, ASSUMPTION CROWN-SECTION). Lowest per region over the "
      "loads, fatigue (strength):\n")
    a("| lug | stay model | fairlead | arm | root | worst strength | worst fatigue |")
    a("|---|---|---|---|---|---:|---:|")
    for n in ("us1", "us2"):
        for k, lab in (("circle", "r 9 circle (BL-049)"), ("crown", "real section (BL-051)")):
            r = lug[n][k]
            rg = r["regions"]
            a(f"| {n} | {lab} | " + " | ".join(f"{rg[q]['fatigue']} ({rg[q]['sf_min']})" for q in ("fairlead", "arm", "root"))
              + f" | {r['worst_strength']['sf']} | {r['worst_fatigue']['fatigue']} |")
    a("")
    a(f"US2 clevis joint (`h1_bedfit.joint_check`, geometry unchanged): share 0.6 strength {j['worst_strength']['sf']}, "
      f"fatigue {j['worst_fatigue']['fatigue']}; share 1.0 {j1['worst_strength']['sf']} / "
      f"{j1['worst_fatigue']['fatigue']}. Strap route (`us_route.py`, 'print_lanes', on the new STL): worst US1 "
      f"{res['us_route']['print_lanes']['worst_clear_mm']['us1']} / US2 {res['us_route']['print_lanes']['worst_clear_mm']['us2']}"
      f" mm, pass {res['us_route']['print_lanes']['pass']}.\n")
    a(f"Spreader z 142 notch (`spreader.us2_notch_check`): support line y {sp['support_bands']['below']['y']} (z "
      f"{sp['support_bands']['below']['z']:g}) to {sp['support_bands']['above']['y']} (z {sp['support_bands']['above']['z']:g});"
      f" the print inside the notch footprint is the stay crown, {sp['air_mm']} mm below that line at its closest. "
      "BL-050 measured 2.31 mm because the crown was cut away; the 1.5 mm 'root air' it passed was the defect. The "
      "arm root now blends into the stay under the crown and never reaches the sheet plane, and the crown is the "
      "sheet's support along the whole stay, so the rule is: nothing in the notch stands proud of the support line "
      f"(proud {sp['proud_mm']} mm, pass {sp['pass']}). The notch no longer clears anything (no cleat on the stay "
      "at z 142 since BL-049): closing it gives the sheet bearing there too (owner option, needs the spreader "
      "re-run).\n")

    a("## 4. Body, and the US1 root (item 2)\n")
    if bs:
        a("`h1_buckling.full_check` on the restored body (`h1_lanes.body_solid`, lane loads, real crown; cache "
          f"`check_{BODY_CHECK}`) against the BL-049 / BL-050 body (`check_{BODY_BEFORE}`; BL-050 changed only "
          "the print, not the voxel body):\n")
        a("| basis | strength | fatigue | creep | buckling | z 234 joint strength / fatigue |")
        a("|---|---|---|---|---|---|")
        for b, v in bs["bases"].items():
            o, n_ = v["before"], v["after"]
            a(f"| {b} | {o['strength']:.3f} -> **{n_['strength']:.3f}** | {o['fatigue']:.3f} -> **{n_['fatigue']:.3f}** | "
              f"{o['creep']:.3f} -> {n_['creep']:.3f} | {o['buckling']:.3f} -> **{n_['buckling']:.3f}** | "
              f"{n_['joint_strength']:.2f} / {n_['joint_fatigue']:.2f} |")
        c = bs["cradle"]
        a(f"| bag-off cradle (lanes) | {c['before']['strength']:.3f} -> **{c['after']['strength']:.3f}** | "
          f"{c['before']['fatigue']:.3f} -> **{c['after']['fatigue']:.3f}** | {c['before']['creep']:.3f} -> "
          f"{c['after']['creep']:.3f} | {c['before']['buckling']:.3f} -> **{c['after']['buckling']:.3f}** | |")
        a("")
        a(f"Raster {bs['raster_g']['before']} -> {bs['raster_g']['after']} g. Governing fatigue region (fine_sm8): "
          f"{(bs.get('governing_region') or {}).get('region')} / peak {(bs.get('governing_region') or {}).get('peak_region')}."
          " The fatigue minimum of the cycled basis (fine_sm8.cyc, the BL-024 cinch-cycled set) has been below 1 since "
          "BL-024 (R1 hold for MT-1, h1_lanes.md section 3); the crown does not change it.\n")
    a(f"**Which US1 number governs.** Stub model {u1['stub_circle_fatigue']} (circle) / **{u1['stub_crown_fatigue']}** "
      f"(real section, strength {u1['stub_crown_strength']}); whole body {u1['body_cradle_fatigue']} (BL-049: "
      f"{u1['body_cradle_fatigue_bl049']}). **The stub model governs.** {u1['why']} So the US1 arm root fails the "
      "fatigue requirement (>= 1.0 at the 1.6 g walking peak, 1e5 cycles) by about 14 % on the best model there is, "
      "and the body number does not clear it. The fix is a design change, not this ticket: BL-049 proposal 2 (run "
      "the US1 arm onto the lower branch it touches, which also unblocks the lighter arms), or a taller root (the "
      "US1 arm spans z 90-106: it cannot go down, the hinge cheek top is z 87; upward it has up to 6 mm to the "
      "spreader sheet's bottom edge, z 112; neither is sized here). Until then the first article's T1 "
      "and MT-1 carry a strain gauge at the US1 root.\n")
    a("**Kit text (for BL-050B; `physical_test_kit.py` is theirs and not edited here):** " + KIT_TEXT_FOR_BL050B + "\n")

    a("## 5. Mass\n")
    a("| item | g | oz |")
    a("|---|---:|---:|")
    a(f"| print: stay crown restored (assembled BL-051 {m['assembled_g']} - BL-050 {m['assembled_bl050_g']}) | "
      f"{m['print_delta_g']:+.1f} | {m['print_delta_g'] / 28.3495:+.2f} |")
    a("| attachment: BL-050's US1 / US2 pins + sleeves row retired (double count with the cradle rows) | -10.8 | -0.38 |")
    a("")
    a(f"Ledger row BL051 (`huntkit/mass/ledger.py`, from this json); the BL050 step drops by the retired 10.8 g "
      f"(`analysis/weight_rollup_v2.json`). Printed: lower {m['lower_g']} g, upper "
      f"{m['upper_g']} g, clevises {sum(m['clevis_g'].values()):.1f} g ({m['assembled_g']} g, "
      f"{m['assembled_g'] / 453.59237:.2f} lb). Lug arms as unioned {m['lug_arms_g']} g (the union adds a little "
      "less than before: the crown now holds part of their root).\n")
    a("**Mass reductions that keep the SF (not applied):** the restored crown is +2.6 g and holds no margin that "
      "governs anywhere else; the US2 lug now has fatigue margin (root 1.37, arm 1.32 on the real section) that the "
      "circle model hid, so the US2 arm could taper further (not sized here: a lug FEA sweep on the real section "
      "would set it). The US1 arm cannot lose anything (0.86).\n")

    a("## 6. BOM mix-up (washers 10 / 12 mm, screws M5 x 40 / x 45)\n")
    a("Both joints use M5 Ti DIN 7984 screws and A2 washers that differ only in length / OD. The print README's "
      "shopping list now gives each its own BOM line and ID: **HW-J234-SCR** M5 x 45 (z 234 joint, 4), **HW-J234-WSH** "
      "12 mm OD (z 234 joint, 8), **HW-US2-SCR** M5 x 40 (US2 clevis, 4), **HW-US2-WSH** 10 mm OD DIN 433 (US2 clevis, "
      "8), **HW-M5-NUT** (both, 8), with a callout to bag and label them apart and the IDs in the assembly steps. "
      "Consequence of a swap: an M5 x 40 at z 234 does not reach through the nut; an M5 x 45 in the clevis bottoms in "
      "the blind tail hole (|x| 142.5) before the head seats; a 10 mm washer at z 234 loses the washer-bearing area "
      "the joint is sized on; a 12 mm washer does not fit the clevis block. The ledger's BL050 hardware row named "
      "the clevis screws 'M5 x 35' (a typo against `h1_bedfit.hardware_g`'s M5 x 40); it now prints the names from "
      "`h1_bedfit.hardware_g` with the BOM ID.\n")

    a("## 7. Assumptions\n")
    for k, t, st in ASSUMPTIONS:
        a(f"- ASSUMPTION {k}: {t} Settled by: {st}")
    a("")
    a("## 8. Screenshots\n")
    for s_ in shots:
        a(f"- `{Path(s_).relative_to(REPO)}`")
    a("")
    DOC.write_text("\n".join(a_))
    return str(DOC)


def report(log=print, before_stl: Path | None = None) -> dict:
    res = compute(log=log, before_stl=before_stl)
    shots = [plot_profile(res, SCREENS / f"{SHOT}1.png"), plot_sections(SCREENS / f"{SHOT}2.png", before_stl),
             plot_lug_field(SCREENS / f"{SHOT}3.png")]
    write_md(res, shots)
    if log:
        log(f"  wrote {DOC.relative_to(REPO)}; screens {shots}")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lug", action="store_true")
    ap.add_argument("--body", action="store_true")
    ap.add_argument("--before", default=None, help="BL-050 h1_assembled.stl for the before columns and figures")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.body:
        r = body()
        print(json.dumps(body_summary(), indent=1, default=float))
    if a.lug:
        r = lug_crown()
        (OUT / "lug_crown.json").write_text(json.dumps(r, indent=1, default=float))
        print(json.dumps(r, indent=1, default=float))
    if not (a.lug or a.body):
        report(before_stl=Path(a.before) if a.before else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
