"""Pack 5200: hipbelt redesign concepts for fit and load transfer (pack-designer, 2026-11-08).

Owner: "the hip belt needs improvement, to better fit the hips; it takes all the load."
Study only: the released geometry / YAML / patterns (``build_geometry.py``, ``geometry.yaml``, ``panels.yaml``,
``patterns_v31.py``) are only READ. Model: ``huntkit/gendesign/hipbelt.py``. Research: ``docs/research/hipbelt_fit.md``.
Write-up: ``designs/pack_5200/analysis/hipbelt_fit.md``.

Concepts (same Ti pivot at z 120, same centre-plate interface, same pockets / rifle tabs):

* ``C0``    current v3.1 belt: straight tapered wing 140 -> 95 mm, EVA 45C 6 + EVA 30C 5, 1.0 mm HDPE, 0/5/10 deg cant
            snap at the wing root (a straight strip tilted is still a cylinder: beta = 0), flat 2-stage lumbar.
* ``A``     CONE CUT: the same layup, wing cut as a developed cone per size (beta S 8 / M 6 / L 5 / XL 2 deg: a 5-10 mm
            bow in the flat pattern), cant snap deleted (fixed joint), removable terraced lumbar wedge (taper per size).
* ``B``     CONE CUT + DUAL DENSITY + 2:1 (recommended): A plus a taller crest zone (150 / 145 / 105 mm), perforated
            EVA crest-relief comfort layer, dual-density 150 x 150 lumbar, 2:1 forward pull, silicone-dot grip face
            (credited only after test HB-2), sizes re-centred on ANSUR II with 70 % padded length (ASIS clearance).
* ``C``     SWAP WING: B, but each wing swaps on the centre plate and comes in two cones per length
            ("T" straighter: S 5 / M 4 / L 3 / XL 0; "C" conical: S 11 / M 10 / L 8 / XL 5).

    python designs/pack_5200/concepts/hipbelt_concepts.py            # results JSON + PNG screens + DXF/PDF pieces
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from huntkit.gendesign import hipbelt as hb  # noqa: E402
from huntkit.gendesign.hipbelt import BeltDesign, FoamLayer as F  # noqa: E402
from huntkit.materials import load  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULT = HERE / "hipbelt_results.json"
SCREENS = ROOT / "outputs" / "screens"
OUTDIR = ROOT / "outputs" / "hipbelt"
DATE = "20261108"

# ------------------------------------------------------------------------------------------- concepts
C0 = BeltDesign("C0", "Current v3.1 (straight wing, cant snap, flat lumbar)")
BETA_A = {"S": 8.0, "M": 6.0, "L": 5.0, "XL": 2.0}
TAPER = {"S": 0.12, "M": 0.10, "L": 0.08, "XL": 0.0}          # XL: wedge out (big frames have no lumbar hollow)
A = replace(C0, key="A", name="CONE CUT (per-size cone, terraced lumbar wedge)", beta_deg=BETA_A,
            lumbar_taper_tan=TAPER)
SIZES_B = {"S": (26, 31), "M": (30, 35), "L": (34, 39), "XL": (38, 44)}
B = replace(A, key="B", name="CONE CUT + DUAL DENSITY + 2:1 (recommended)",
            wing_h=((0.0, 150.0), (0.45, 145.0), (1.0, 105.0)),
            crest_foam=(F("eva_foam_45c", 5.0), F("eva_foam_perforated", 6.0)),
            lumbar_w=150.0, lumbar_h=150.0,
            lumbar_foam=(F("eva_foam_45c", 6.0), F("eva_foam_30c", 6.0)),
            stiff_inset=10.0, sizes=SIZES_B, pad_fraction=0.70, pull_ma=2.0)
BETA_T = {"S": 5.0, "M": 4.0, "L": 3.0, "XL": 0.0}
BETA_C = {"S": 11.0, "M": 10.0, "L": 8.0, "XL": 5.0}
C_T = replace(B, key="C-T", name="SWAP WING, T (straighter) cone", beta_deg=BETA_T)
C_C = replace(B, key="C-C", name="SWAP WING, C (conical) cone", beta_deg=BETA_C)
CONCEPTS = {"C0": C0, "A": A, "B": B}

# display forms: S = female 30 in, M = female 34 / male 34, L = male 38 (ANSUR II medians in each band)
DISPLAY = [("female", 30, "S"), ("female", 34, "M"), ("male", 34, "M"), ("male", 38, "L")]


def all_forms(min_n: int = 60):
    out = []
    for sex in ("female", "male"):
        for k, f in hb.anthro()[sex]["forms"].items():
            if f["n"] >= min_n:
                out.append(hb.hip_form(sex, int(k[:-2])))
    return out


def concept_c(form):
    """SWAP WING: the user picks the cone. Women default C, men default T; report the better of the two."""
    rows = [hb.study(C_T, form), hb.study(C_C, form)]
    best = max(rows, key=lambda r: r["hold_margin_at_allow"])
    best = dict(best)
    best["design"] = "C"
    best["cone"] = "T" if best is rows[0] or rows[0]["hold_margin_at_allow"] >= rows[1]["hold_margin_at_allow"] else "C"
    return best


# ------------------------------------------------------------------------------------------- mass / cost / hours
def _poly_area(T, Bt):
    P = np.vstack([T, Bt[::-1]])
    x, y = P[:, 0], P[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _cost_per_m2(mid):
    m = load(mid)
    c = m.cost_usd or {}
    v, per = c.get("value", 0.0), c.get("per", "m2")
    if per == "m2":
        return v
    if per == "yd":
        w = m.get("roll_width_mm", 1450) / 1000.0
        return v / (0.9144 * w)
    if per == "kg":
        rho = m.get("density_kg_m3", 1000)
        return v * rho / 1000.0       # per m2 per mm thickness (scaled below)
    return v


def belt_bom(design: BeltDesign, size: str = "M") -> dict:
    """Soft-goods mass + material cost of the belt body (wings x2 + lumbar), same rules for every concept:
    fabric pieces at seam outline + 10 mm SA, foams inset (8 / 6 mm), stiffener inset, areas from the developed
    wing on the size-centre form (male median band nearest the size centre)."""
    lo, hi = design.sizes[size]
    band = int(round((lo + hi) / 2 / 2) * 2)
    form = hb.hip_form("male", band) if f"{band}in" in hb.anthro()["male"]["forms"] else hb.hip_form("female", band)
    T, Bt, _ = hb.wing_flat(design, form, size)
    A_seam = _poly_area(T, Bt)
    L = float(np.linalg.norm(0.5 * (T[-1] + Bt[-1]) - 0.5 * (T[0] + Bt[0])))
    perim = L * 2 + 150 + 100
    rows = []

    def add(name, mid, area, t=None, qty=2):
        g = hb.piece_mass_g(mid, area, t) * qty
        cu = load(mid).cost_usd or {}
        cpm = _cost_per_m2(mid) * ((t or 1.0) if cu.get("per") == "kg" else 1.0)
        rows.append({"piece": name, "material": mid, "area_mm2": round(area, 0), "qty": qty, "mass_g": round(g, 1),
                     "cost_usd": round(cpm * area / 1e6 * qty * 1.15, 2)})      # 15 % cutting waste ASSUMPTION

    add("wing shell", "cordura_330d_nylon66", A_seam + perim * 10)
    add("wing face", "spacer_mesh_3d", A_seam + perim * 10)
    shrink = lambda d: A_seam - perim * d    # noqa: E731
    lay = list(design.wing_foam)
    add("wing load foam", lay[0].material_id, shrink(8.0), lay[0].t)
    if design.crest_foam:
        crest_share = 90.0 / max(L, 1)       # 90 mm crest zone (hipbelt.evaluate: +/-45 mm)
        add("wing comfort foam", lay[1].material_id, shrink(6.0) * (1 - crest_share), lay[1].t)
        add("wing crest-relief foam", design.crest_foam[1].material_id, shrink(6.0) * crest_share, design.crest_foam[1].t)
    else:
        add("wing comfort foam", lay[1].material_id, shrink(6.0), lay[1].t)
    if design.stiff_mat:
        add("wing stiffener", design.stiff_mat, shrink(design.stiff_inset), design.stiff_t)
    lw, lh = design.lumbar_w + 20, design.lumbar_h
    add("lumbar shell", "cordura_330d_nylon66", (lw + 20) * (lh + 20), qty=1)
    add("lumbar face", "spacer_mesh_3d", (lw + 20) * (lh + 20), qty=1)
    for i, Lf in enumerate(design.lumbar_foam):
        add(f"lumbar foam {i + 1}", Lf.material_id, lw * lh, Lf.t, qty=1)
    tap = max(design.taper(s) for s in design.sizes)
    if tap > 0:                               # terraced wedge: 3 die-cut EVA 45C layers, 100 / 66 / 33 % height
        t_layer = round(tap * lh / 3, 1)
        add("lumbar terraced wedge (3 steps)", "eva_foam_45c", (lw - 20) * lh * (1 + 0.66 + 0.33), t_layer, qty=1)
    else:
        add("lumbar stage-2 wedge (flat)", "eva_foam_45c", 130 * 90, 8.0, qty=1)
    hw = []
    if design.pull_ma > 1:
        hw += [("2:1 pull: 25 mm poly webbing +0.6 m", 0.6 * load("poly_webbing_25mm").require("mass_g_m"), 0.6 * 1.0),
               ("2:1 pull: 2 x 25 mm Al D-ring (no record, ASSUMPTION 5 g, $1)", 10.0, 2.0)]
    if design.key in ("B", "C"):
        hw += [("silicone-dot grip print on lumbar + wing faces (ASSUMPTION 5 g, outsourced $3)", 5.0, 3.0)]
    if design.key in ("A", "B"):
        hw += [("cant snap deleted (2 POM 3-position detents, ASSUMPTION -6 g)", -6.0, -0.5)]
    if design.key == "C":
        hw += [("cant snap deleted (ASSUMPTION -6 g)", -6.0, -0.5),
               ("swap-wing connectors: 2 x PA66-GF30 tongue + POM latch (ASSUMPTION 12 g each, $4)", 24.0, 8.0)]
    soft = sum(r["mass_g"] for r in rows)
    hard = sum(h[1] for h in hw)
    return {"size": size, "form": form.name, "wing_seam_area_mm2": round(A_seam, 0), "wing_len_mm": round(L, 0),
            "pieces": rows, "hardware_delta": [{"item": h[0], "mass_g": round(h[1], 1), "cost_usd": h[2]} for h in hw],
            "soft_g": round(soft, 1), "hardware_delta_g": round(hard, 1), "total_g": round(soft + hard, 1),
            "material_cost_usd": round(sum(r["cost_usd"] for r in rows) + sum(h[2] for h in hw), 2)}


HOURS_DELTA = {   # ASSUMPTION: beginner, one walking-foot machine; deltas vs the current belt (~6 h)
    "C0": [],
    "A": [("curved wing binding (5-10 mm bow, eased; 2 wings)", 0.4), ("terraced lumbar wedge: glue 3 die-cut layers", 0.2),
          ("fixed wing joint instead of the cant snap (bolt + bartack)", -0.2)],
    "B": [("curved wing binding (2 wings)", 0.4), ("terraced lumbar wedge", 0.2), ("fixed wing joint", -0.2),
          ("crest-relief foam zone: 2 extra die-cut pieces, tack-glue", 0.3), ("2:1 pull: 4 bartacks + routing", 0.5),
          ("dual-density lumbar: one more layer", 0.1)],
    "C": [("curved wing binding (2 wings)", 0.4), ("terraced lumbar wedge", 0.2), ("crest-relief foam zone", 0.3),
          ("2:1 pull", 0.5), ("dual-density lumbar", 0.1),
          ("swap-wing connector tongues: 2 bolted + bartacked joints", 1.0), ("second cone variant to sew (per extra wing pair)", 0.0)],
}


# ------------------------------------------------------------------------------------------- run
def run(write: bool = True) -> dict:
    forms = all_forms()
    rows = []
    for f in forms:
        for d in CONCEPTS.values():
            rows.append(hb.study(d, f))
        rows.append(concept_c(f))
    # grip sensitivity (mu 0.5) and torso sensitivity on the display forms
    sens = []
    for sex, band, lab in DISPLAY:
        f = hb.hip_form(sex, band)
        for key, d in (("C0", C0), ("B", B)):
            for mu in (hb.MU, hb.MU_HIGH):
                for torso in (15, 19, 23):
                    if mu != hb.MU and torso != 19:
                        continue
                    r = hb.study(d, f, mu=mu, torso_in=torso)
                    sens.append({"form": f.name, "design": key, "mu": mu, "torso_in": torso,
                                 "T_req_n": r["T_req_n"], "peak_wing_kpa": r["peak_wing_kpa"],
                                 "peak_lumbar_kpa": r["peak_lumbar_kpa"], "mean_kpa": r["mean_kpa"],
                                 "hold_margin_at_allow": r["hold_margin_at_allow"]})
    sweeps = lever_sweeps()
    cov = {name: {sex: round(hb.coverage(sizes, sex), 3) for sex in ("male", "female")}
           for name, sizes in (("current", hb.SIZES_CURRENT), ("proposed", SIZES_B))}
    asis = asis_table()
    bom = {k: belt_bom(d) for k, d in {**CONCEPTS, "C": C_T}.items()}
    bom["C"] = belt_bom(replace(C_T, key="C"))
    flat = {}
    for size in SIZES_B:
        lo, hi = SIZES_B[size]
        band = int(round((lo + hi) / 2 / 2) * 2)
        form = hb.hip_form("male", band)
        T, Bt, st = hb.wing_flat(B, form, size)
        flat[size] = {"form": form.name, "beta_deg": B.beta(size), "bow_mm": round(hb.flat_sagitta(T, Bt), 1),
                      "wing_len_mm": round(B.wing_len(size), 0), "dev_strain": round(st, 4)}
    pockets = pocket_room()
    summary = summarise(rows)
    out = {"meta": {"generated_by": "designs/pack_5200/concepts/hipbelt_concepts.py", "date": "2026-11-08",
                    "model": "huntkit/gendesign/hipbelt.py", "mu": hb.MU, "hip_share": hb.HIP_SHARE,
                    "rated_kg": hb.RATED_KG, "walk_g": hb.WALK_G, "cg_aft_mm": hb.CG_AFT_MM,
                    "limits_kpa": {"hip_peak": hb.P_HIP_PEAK_KPA, "mean_occlusion": hb.P_OCCLUSION_KPA,
                                   "bony_crest_top": hb.P_BONY_KPA}},
           "summary": summary, "rows": rows, "sensitivity": sens, "sweeps": sweeps, "coverage": cov,
           "asis": asis, "bom": bom, "hours_delta": {k: {"items": v, "total_h": round(sum(x[1] for x in v), 1)}
                                                       for k, v in HOURS_DELTA.items()},
           "flat_wing": flat, "pockets": pockets,
           "lumbar_couple_n": {t: round(hb.RATED_KG * hb.G * hb.CG_AFT_MM / (hb.YOKE_Z[t] - hb.LUMBAR_Z), 0)
                               for t in (15, 19, 23)}}
    if write:
        RESULT.write_text(json.dumps(out, indent=1))
    return out


def summarise(rows):
    out = {}
    for key in ("C0", "A", "B", "C"):
        rr = [r for r in rows if r["design"] == key]
        out[key] = {
            "worst_peak_wing_kpa": max(r["peak_wing_kpa"] for r in rr),
            "median_peak_wing_kpa": float(np.median([r["peak_wing_kpa"] for r in rr])),
            "worst_peak_lumbar_kpa": max(r["peak_lumbar_kpa"] for r in rr),
            "median_mean_kpa": float(np.median([r["mean_kpa"] for r in rr])),
            "worst_crest_top_kpa": max(r["peak_crest_top_kpa"] for r in rr),
            "median_area_cm2": float(np.median([r["area_cm2"] for r in rr])),
            "worst_hold": min(r["hold_margin_at_allow"] for r in rr),
            "median_hold": float(np.median([r["hold_margin_at_allow"] for r in rr])),
            "median_T_req_n": float(np.median([r["T_req_n"] for r in rr])),
            "median_pull_n": float(np.median([r["pull_n"] for r in rr])),
            "min_asis_clear_mm": min(r["asis_clear_mm"] for r in rr),
        }
    return out


def lever_sweeps():
    """One lever at a time from the current belt, on F30 and M34."""
    res = {}
    forms = [hb.hip_form("female", 30), hb.hip_form("male", 34)]
    levers = {
        "beta_deg": [(b, replace(C0, beta_deg=b)) for b in (0, 2, 4, 6, 8, 10, 12, 14)],
        "foam_comfort": [(lab, replace(C0, wing_foam=(F("eva_foam_45c", 6.0), F(mid, t))))
                         for lab, mid, t in (("EVA30 3", "eva_foam_30c", 3.0), ("EVA30 5", "eva_foam_30c", 5.0),
                                             ("EVA30 8", "eva_foam_30c", 8.0), ("perf 6", "eva_foam_perforated", 6.0),
                                             ("EVA45 5 (firm)", "eva_foam_45c", 5.0))],
        "stiffener_inset_mm": [(i, replace(C0, stiff_inset=i)) for i in (4, 8, 12, 20, 30, 45)],
        "stiffener_t_mm": [(t, replace(C0, stiff_t=t)) for t in (0.5, 1.0, 1.5, 2.0)] + [("none", replace(C0, stiff_mat=None))],
        "lumbar_taper": [(t, replace(C0, lumbar_taper_tan=t)) for t in (0.0, 0.05, 0.10, 0.15, 0.20)],
        "wing_height_mm": [(h, replace(C0, wing_h=((0.0, h), (1.0, h - 45)))) for h in (120, 140, 160, 180)],
    }
    for name, lst in levers.items():
        res[name] = []
        for val, d in lst:
            row = {"value": val}
            for f in forms:
                r = hb.study(d, f)
                row[f.name] = {"peak_wing_kpa": r["peak_wing_kpa"], "peak_lumbar_kpa": r["peak_lumbar_kpa"],
                               "mean_kpa": r["mean_kpa"], "crest_top": r["peak_crest_top_kpa"],
                               "hold": r["hold_margin_at_allow"]}
            res[name].append(row)
    return res


def asis_table():
    """Wing tip to ASIS clearance (mm along the surface) at every band form inside each size range."""
    out = {}
    for key, d in (("C0", C0), ("B", B)):
        out[key] = {}
        for size, (lo, hi) in d.sizes.items():
            vals = []
            for f in all_forms(30):
                if lo <= f.circ_in <= hi:
                    r = hb.evaluate(d, f, 100.0, size=size)
                    vals.append((f.name, round(r.extra["asis_clear"], 0)))
            out[key][size] = vals
    return out


def pocket_room():
    """Room on each wing for a hipbelt pocket: from 25 mm forward of the crest-lateral point to 20 mm short of the
    tip (keeps pocket loads off the crest top), at the smallest form in each proposed size."""
    out = {}
    for size, (lo, hi) in SIZES_B.items():
        fs = [f for f in all_forms(30) if lo <= f.circ_in <= hi]
        f = min(fs, key=lambda x: x.circ)
        sec = hb.section(f)
        s_tip = B.lumbar_w / 2 + B.wing_len(size)
        out[size] = {"form": f.name, "pocket_max_len_mm": round(s_tip - 20 - (sec.s_crest + 25), 0),
                     "wing_h_at_pocket_mm": [145, 105]}
    return out


# ------------------------------------------------------------------------------------------- figures
def _cmap():
    import matplotlib
    return matplotlib.colormaps["magma_r"]


def fig_pressure_maps(path):
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.6), constrained_layout=True)
    norm = Normalize(0, 70)
    for j, (sex, band, lab) in enumerate(DISPLAY):
        f = hb.hip_form(sex, band)
        for i, d in enumerate((C0, B)):
            T = hb.tension_for_hold(d, f)
            r = hb.evaluate(d, f, T)
            m = hb.metrics(r)
            ax = axes[i, j]
            s_full = np.r_[-r.s[::-1], r.s[1:]]
            P = np.vstack([r.p[::-1], r.p[1:]])
            h = np.r_[r.h[::-1], r.h[1:]]
            zg = np.linspace(-95, 95, 191)
            grid = np.full((len(zg), len(s_full)), np.nan)
            for kk in range(len(s_full)):
                uu = np.linspace(-h[kk] / 2, h[kk] / 2, P.shape[1])
                inside = np.abs(zg) <= h[kk] / 2
                grid[inside, kk] = np.interp(zg[inside], uu, P[kk])
            ax.pcolormesh(s_full, zg, grid, cmap=_cmap(), norm=norm, shading="nearest")
            ax.axvline(0, color="#888", lw=0.6)
            for sgn in (-1, 1):
                ax.axvline(sgn * r.sec.s_crest, color="#3a7", lw=0.8, ls="--")
                ax.axvline(sgn * r.sec.s_asis, color="#c33", lw=0.8, ls=":")
            ax.set_xlim(-r.sec.half_perim * 0.8, r.sec.half_perim * 0.8)
            ax.set_ylim(-95, 95)
            ax.set_aspect("equal")
            ax.invert_yaxis()      # belt top (u -) at the top of the plot
            ttl = ("CURRENT" if i == 0 else "RECOMMENDED B") + f"  {lab} {f.name} ({f.circ_in:.0f} in, size {r.size})"
            ax.set_title(ttl, fontsize=9.5, loc="left")
            ax.text(0.01, 0.02, f"T {T:.0f} N  peak {m['peak_kpa']:.0f}  mean {m['mean_kpa']:.0f} kPa\n"
                                f"area {m['area_cm2']:.0f} cm2  crest-top {m['peak_crest_top_kpa']:.0f} kPa",
                    transform=ax.transAxes, fontsize=8, va="bottom", color="#222",
                    bbox=dict(fc="white", ec="none", alpha=0.8))
            ax.set_xlabel("along the belt from the spine (mm)   green -- crest side, red .. ASIS", fontsize=7.5)
            ax.set_ylabel("up  <-  belt height (mm)  ->  down", fontsize=7.5)
            ax.tick_params(labelsize=7)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=_cmap())
    fig.colorbar(sm, ax=axes, shrink=0.8, label="contact pressure, kPa (limits: mean 16, peak 48.6, bony 30)")
    fig.suptitle("Hipbelt contact pressure laid flat (seen from the body), 68 kg, belt tension to hold 80 % at the "
                 "1.6 g walking peak (mu 0.3), sustained 1 g lumbar couple", fontsize=11)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def fig_on_hip(path):
    """3D view of the hip form (ANSUR median) with the belt-contact pressure painted on the body, rear 3/4."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(14, 7.2))
    norm = Normalize(0, 70)
    cmap = _cmap()
    cases = [(hb.hip_form("female", 30), "S"), (hb.hip_form("male", 34), "M")]
    k = 1
    for f, lab in cases:
        for d in (C0, B):
            ax = fig.add_subplot(1, 4, k, projection="3d")
            k += 1
            T = hb.tension_for_hold(d, f)
            r = hb.evaluate(d, f, T)
            ex = r.sec.ex
            # body rings z -130 .. +110
            zs = np.linspace(-130, 110, 25)
            polys, cols = [], []
            for zi in range(len(zs) - 1):
                rings = []
                for z in (zs[zi], zs[zi + 1]):
                    a = f.a0 - f.tan_lat * z
                    bb = f.b0 - f.tan_post * z
                    t, P = hb._se_pts(a, f.b0, bb, ex, m=97)
                    rings.append(np.column_stack([P, np.full(len(P), z)]))
                zc = 0.5 * (zs[zi] + zs[zi + 1])
                for j in range(len(t) - 1):
                    quad = [rings[0][j], rings[0][j + 1], rings[1][j + 1], rings[1][j]]
                    # pressure lookup: arc position of this facet + height within the belt
                    xy = 0.25 * sum(q[:2] for q in quad)
                    i_s = int(np.argmin(np.linalg.norm(r.sec.xy - np.array([abs(xy[0]), xy[1]]), axis=1)))
                    s_here = r.sec.s[i_s]
                    pv = 0.0
                    if s_here <= r.s[-1]:
                        ii = int(np.argmin(np.abs(r.s - s_here)))
                        hh = r.h[ii]
                        if abs(zc) <= hh / 2:
                            uu = np.linspace(-hh / 2, hh / 2, r.p.shape[1])
                            pv = float(np.interp(-zc, uu, r.p[ii]))
                    polys.append(quad)
                    cols.append(cmap(norm(pv)) if pv > 0.5 else (0.78, 0.77, 0.74, 1.0))
            pc = Poly3DCollection(polys, facecolors=cols, edgecolors="none")
            ax.add_collection3d(pc)
            ax.set_xlim(-200, 200)
            ax.set_ylim(-200, 200)
            ax.set_zlim(-200, 200)
            ax.view_init(elev=12, azim=60)
            ax.set_axis_off()
            m = hb.metrics(r)
            ax.set_title(f"{'CURRENT' if d is C0 else 'RECOMMENDED B'}\n{lab}: {f.name} ({f.circ_in:.0f} in)\n"
                         f"peak {m['peak_kpa']:.0f} kPa, mean {m['mean_kpa']:.0f}, crest-top {m['peak_crest_top_kpa']:.0f}",
                         fontsize=9)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=fig.axes, shrink=0.55, orientation="horizontal", pad=0.02,
                 label="pressure on the hip, kPa (rear 3/4 view; grey = no belt contact)")
    fig.suptitle("Belt pressure on the hip (ANSUR II median forms), 68 kg, tension to hold 80 % at 1.6 g", fontsize=12)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_levers(out, path):
    import matplotlib.pyplot as plt
    sw = out["sweeps"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5), constrained_layout=True)
    specs = [("beta_deg", "wing cone angle beta (deg)"), ("lumbar_taper", "lumbar taper (thickness / height)"),
             ("wing_height_mm", "wing root height (mm), tip = root - 45"), ("stiffener_inset_mm", "HDPE inset (mm): less = wider stiffener"),
             ("stiffener_t_mm", "HDPE thickness (mm)"), ("foam_comfort", "comfort layer (EVA 45C 6 mm load layer kept)")]
    for ax, (key, lab) in zip(axes.flat, specs):
        rows = sw[key]
        xs = list(range(len(rows)))
        for fname, col in (("F30", "#b5523b"), ("M34", "#2f6f8f")):
            pk = [r[fname]["peak_lumbar_kpa"] if key == "lumbar_taper" else r[fname]["peak_wing_kpa"] for r in rows]
            ct = [r[fname]["crest_top"] for r in rows]
            hd = [r[fname]["hold"] for r in rows]
            ax.plot(xs, pk, "-o", color=col, lw=2, ms=4, label=f"{fname} {'lumbar' if key == 'lumbar_taper' else 'wing'} peak")
            ax.plot(xs, ct, "--", color=col, lw=1.2, label=f"{fname} crest-top")
            ax2 = ax.twinx() if fname == "F30" else ax2  # noqa: F821
            ax2.plot(xs, hd, ":", color=col, lw=1.6)
            ax2.set_ylim(0.2, 1.0)
            ax2.set_ylabel("hold at pressure limit (dotted)\n= share of the 1.6 g need", fontsize=7.5)
        ax.axhline(hb.P_HIP_PEAK_KPA, color="#999", lw=0.8)
        ax.axhline(hb.P_BONY_KPA, color="#999", lw=0.8, ls="--")
        ax.set_xticks(xs, [str(r["value"]) for r in rows], fontsize=7.5, rotation=20)
        ax.set_xlabel(lab, fontsize=8.5)
        ax.set_ylabel("kPa", fontsize=8)
        ax.set_ylim(0, 90)
        ax.legend(fontsize=6.5, loc="upper left")
    fig.suptitle("One lever at a time from the current belt (F30 = female 30 in, M34 = male 34 in). "
                 "Grey lines: 48.6 kPa hip peak, 30 kPa bony (ASSUMPTION)", fontsize=11)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def fig_sizing(out, path):
    import matplotlib.pyplot as plt
    a = hb.anthro()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True)
    ax = axes[0]
    bins = np.arange(24, 50, 0.5)
    for sex, col in (("male", "#2f6f8f"), ("female", "#b5523b")):
        ax.hist(a[sex]["_wc_in"], bins=bins, alpha=0.55, color=col, label=f"ANSUR II {sex} (n {a[sex]['n']})", density=True)
    for i, (k, (lo, hi)) in enumerate(hb.SIZES_CURRENT.items()):
        ax.plot([lo, hi], [0.205 - 0.006 * (i % 2)] * 2, color="#555", lw=4, solid_capstyle="butt")
        ax.text((lo + hi) / 2, 0.209, f"{k}", ha="center", fontsize=8, color="#555")
    for i, (k, (lo, hi)) in enumerate(SIZES_B.items()):
        ax.plot([lo, hi], [0.185 - 0.006 * (i % 2)] * 2, color="#1a8f4a", lw=4, solid_capstyle="butt")
        ax.text((lo + hi) / 2, 0.189 - 0.012, f"{k}", ha="center", fontsize=8, color="#1a8f4a")
    cov = out["coverage"]
    ax.text(0.99, 0.62, f"current S-XL 26-42 in covers men {cov['current']['male'] * 100:.0f} %, women "
                        f"{cov['current']['female'] * 100:.0f} %\nproposed 26-44 in covers men "
                        f"{cov['proposed']['male'] * 100:.0f} %, women {cov['proposed']['female'] * 100:.0f} %",
            transform=ax.transAxes, ha="right", fontsize=8.5)
    ax.set_xlabel("waist (iliac-crest level) circumference, in")
    ax.set_ylabel("density")
    ax.set_title("Size ranges vs ANSUR II (grey = current, green = proposed)", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    for sex, col, mk in (("male", "#2f6f8f", "o"), ("female", "#b5523b", "s")):
        xs, ys, ns = [], [], []
        for kk, f in a[sex]["forms"].items():
            xs.append(f["waistcircumference"] / hb.IN)
            ys.append(math.degrees(math.atan(f["tan_lat"])))
            ns.append(f["n"])
        ax.scatter(xs, ys, s=np.array(ns) / 6, color=col, marker=mk, label=f"{sex}: lateral hip cone (median per band)")
    for k, (lo, hi) in SIZES_B.items():
        ax.plot([lo, hi], [BETA_A[k]] * 2, color="#1a8f4a", lw=3)
        ax.plot([lo, hi], [BETA_C[k]] * 2, color="#1a8f4a", lw=1, ls="--")
        ax.plot([lo, hi], [BETA_T[k]] * 2, color="#1a8f4a", lw=1, ls=":")
    ax.text(0.02, 0.04, "green: B pattern cone per size; dashed / dotted = C swap-wing 'C' / 'T' cones\n"
                        "current wing: straight (0 deg) at every cant setting", transform=ax.transAxes, fontsize=8)
    ax.set_xlabel("waist circumference, in")
    ax.set_ylabel("cone half-angle, deg")
    ax.set_title("The hip cone is steeper for women and for smaller waists (ANSUR II)", fontsize=10)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=105)
    plt.close(fig)


def recommended_pieces(size: str = "M"):
    """Flat pieces (seam line) of the recommended belt B, one size, as huntkit.patterns Pieces."""
    from huntkit.patterns import Piece
    lo, hi = SIZES_B[size]
    band = int(round((lo + hi) / 2 / 2) * 2)
    form = hb.hip_form("male", band)
    T, Bt, _ = hb.wing_flat(B, form, size)
    outline = [tuple(map(float, p)) for p in Bt] + [tuple(map(float, p)) for p in T[::-1]]
    pieces = []
    common = dict(quantity=2, mirror=True, size=size)
    shell = Piece("hipbelt wing shell (cone cut)", outline, seam_allowance_mm=10.0, material_id="cordura_330d_nylon66",
                  piece_id="HB-W1", **common)
    pieces.append(shell)
    pieces.append(Piece("hipbelt wing face", outline, seam_allowance_mm=10.0, material_id="spacer_mesh_3d",
                        piece_id="HB-W2", **common))
    from shapely.geometry import Polygon
    poly = Polygon(outline)
    for pid, name, mid, inset in (("HB-W3", "wing load foam EVA 45C 5 mm", "eva_foam_45c", 8.0),
                                  ("HB-W4", "wing comfort foam EVA 30C 6 mm (crest zone cut out)", "eva_foam_30c", 6.0),
                                  ("HB-W6", "wing stiffener HDPE 1.0 mm", "hdpe_sheet", 10.0)):
        ip = poly.buffer(-inset, join_style=2)
        pieces.append(Piece(name, list(ip.exterior.coords)[:-1], seam_allowance_mm=0.0, material_id=mid,
                            piece_id=pid, **common))
    # crest-relief insert: 90 mm zone centred at the crest-lateral arc position
    sec = hb.section(form)
    x_c = sec.s_crest - B.lumbar_w / 2
    ip = poly.buffer(-6.0, join_style=2).intersection(Polygon([(x_c - 45, -200), (x_c + 45, -200), (x_c + 45, 200),
                                                               (x_c - 45, 200)]))
    pieces.append(Piece("crest-relief insert, perforated EVA 6 mm", list(ip.exterior.coords)[:-1], seam_allowance_mm=0.0,
                        material_id="eva_foam_perforated", piece_id="HB-W5", **common))
    lw, lh = B.lumbar_w + 20, B.lumbar_h
    one = dict(quantity=1, size="all")
    pieces.append(Piece("lumbar shell", [(0, 0), (lw + 20, 0), (lw + 20, lh + 20), (0, lh + 20)], seam_allowance_mm=10.0,
                        material_id="cordura_330d_nylon66", piece_id="HB-L1", **one))
    pieces.append(Piece("lumbar face (grip print)", [(0, 0), (lw + 20, 0), (lw + 20, lh + 20), (0, lh + 20)],
                        seam_allowance_mm=10.0, material_id="spacer_mesh_3d", piece_id="HB-L2", **one))
    pieces.append(Piece("lumbar load foam EVA 45C 6", [(0, 0), (lw, 0), (lw, lh), (0, lh)], seam_allowance_mm=0.0,
                        material_id="eva_foam_45c", piece_id="HB-L3", **one))
    pieces.append(Piece("lumbar comfort foam EVA 30C 6", [(0, 0), (lw, 0), (lw, lh), (0, lh)], seam_allowance_mm=0.0,
                        material_id="eva_foam_30c", piece_id="HB-L4", **one))
    for i, frac in enumerate((1.0, 0.66, 0.33)):
        hgt = round(lh * frac)
        pieces.append(Piece(f"lumbar wedge step {i + 1} EVA 45C 5 mm (top-aligned)", [(0, 0), (lw - 20, 0), (lw - 20, hgt), (0, hgt)],
                            seam_allowance_mm=0.0, material_id="eva_foam_45c", piece_id=f"HB-L5{'abc'[i]}", **one))
    return pieces, form


def fig_flat(path):
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(15, 9.6))
    ax = fig.add_axes([0.03, 0.30, 0.62, 0.62])
    cols = {"S": "#b5523b", "M": "#1a8f4a", "L": "#2f6f8f", "XL": "#6b4f9c"}
    for size in SIZES_B:
        lo, hi = SIZES_B[size]
        band = int(round((lo + hi) / 2 / 2) * 2)
        form = hb.hip_form("male", band)
        T, Bt, _ = hb.wing_flat(B, form, size)
        P = np.vstack([Bt, T[::-1], Bt[:1]])
        ax.plot(P[:, 0], P[:, 1], color=cols[size], lw=1.8,
                label=f"{size} ({lo}-{hi} in): beta {B.beta(size):.0f} deg, bow {hb.flat_sagitta(T, Bt):.1f} mm, "
                      f"length {B.wing_len(size):.0f} mm")
        Tc, Bc, _ = hb.wing_flat(C0, form, "M" if size in ("S", "M") else ("L" if size == "L" else "XL"))
    T0, B0, _ = hb.wing_flat(C0, hb.hip_form("male", 32), "M")
    P0 = np.vstack([B0, T0[::-1], B0[:1]])
    ax.plot(P0[:, 0], P0[:, 1], color="#888", lw=1.2, ls="--", label="current M wing (straight trapezoid 140 -> 95)")
    ax.set_aspect("equal")
    ax.grid(True, color="#ddd", lw=0.5)
    ax.set_xticks(np.arange(-20, 340, 20))
    ax.set_yticks(np.arange(-100, 101, 20))
    ax.tick_params(labelsize=7)
    ax.set_title("Recommended B wing, graded S-XL (seam line, right wing seen from outside; root at x 0, 20 mm grid)",
                 fontsize=10, loc="left")
    ax.legend(fontsize=8, loc="lower left")
    ax.plot([0, 100], [-118, -118], color="k", lw=3)
    ax.text(50, -126, "100 mm", ha="center", fontsize=8)
    ax.set_ylim(-135, 105)
    # M pieces
    pieces, form = recommended_pieces("M")
    ax2 = fig.add_axes([0.67, 0.30, 0.32, 0.62])
    y0 = 0
    for p in pieces:
        if not p.piece_id.startswith("HB-L"):
            continue
        cut = np.array(p.cut_line()) if p.seam_allowance_mm else np.array(p.outline)
        seam = np.array(p.outline + [p.outline[0]])
        ax2.plot(seam[:, 0], seam[:, 1] + y0, color="k", lw=1.0)
        if p.seam_allowance_mm:
            ax2.plot(np.r_[cut[:, 0], cut[0, 0]], np.r_[cut[:, 1], cut[0, 1]] + y0, color="#c33", lw=0.8, ls="--")
        ax2.text(-5, y0 + 5, f"{p.piece_id} {p.name}", fontsize=6.5, ha="right", rotation=0)
        y0 -= (max(seam[:, 1]) - min(seam[:, 1])) + 45
    ax2.set_aspect("equal")
    ax2.set_xlim(-260, 220)
    ax2.axis("off")
    ax2.set_title("Lumbar pieces (all sizes), black seam / red cut", fontsize=9)
    ax3 = fig.add_axes([0.03, 0.03, 0.62, 0.24])
    for p in pieces:
        if not p.piece_id.startswith("HB-W"):
            continue
        seam = np.array(p.outline + [p.outline[0]])
        ax3.plot(seam[:, 0], seam[:, 1], lw=1.0, label=f"{p.piece_id} {p.name}")
        if p.seam_allowance_mm:
            cut = np.array(p.cut_line())
            ax3.plot(np.r_[cut[:, 0], cut[0, 0]], np.r_[cut[:, 1], cut[0, 1]], color="#c33", lw=0.6, ls="--")
    ax3.set_aspect("equal")
    ax3.legend(fontsize=6.5, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax3.set_title("Size M wing stack: shell / face (cut line red), foams, crest insert, HDPE", fontsize=9, loc="left")
    ax3.tick_params(labelsize=6)
    fig.suptitle("Hipbelt B flat pattern pieces, to scale (DXF + 1:1 tiled PDF in outputs/hipbelt/)", fontsize=12)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def export_pieces():
    from huntkit.patterns.export_dxf import export_dxf
    from huntkit.patterns.export_pdf import export_pdf_tiled
    OUTDIR.mkdir(parents=True, exist_ok=True)
    allp = []
    for size in SIZES_B:
        pcs, _ = recommended_pieces(size)
        allp += [p for p in pcs if p.piece_id.startswith("HB-W") or size == "M"]
    export_dxf(allp, OUTDIR / "hipbelt_B_pieces.dxf")
    export_pdf_tiled([p for p in recommended_pieces("M")[0]], OUTDIR / "hipbelt_B_pieces_M_1to1.pdf")
    return [str(OUTDIR / "hipbelt_B_pieces.dxf"), str(OUTDIR / "hipbelt_B_pieces_M_1to1.pdf")]


def shrink(path: Path, limit=1_500_000):
    from PIL import Image
    im = Image.open(path)
    while path.stat().st_size > limit:
        im = im.resize((int(im.width * 0.85), int(im.height * 0.85)))
        im.save(path, optimize=True)


def screens(out):
    SCREENS.mkdir(parents=True, exist_ok=True)
    files = []
    for n, fn in ((1, lambda p: fig_pressure_maps(p)), (2, lambda p: fig_on_hip(p)), (3, lambda p: fig_flat(p)),
                  (4, lambda p: fig_levers(out, p)), (5, lambda p: fig_sizing(out, p))):
        p = SCREENS / f"{DATE}_hipbelt_{n}.png"
        fn(p)
        shrink(p)
        files.append(str(p))
    return files


if __name__ == "__main__":     # pragma: no cover
    res = run()
    print(json.dumps(res["summary"], indent=1))
    print(json.dumps({k: v["total_g"] for k, v in res["bom"].items()}))
    if "--no-figs" not in sys.argv:
        print(screens(res))
        print(export_pieces())
