"""BL-039 task 2: structural confirmation of the two frame-release rules BL-038 wrote into the test kit.

    python designs/pack_5200/ca1_mt1c_confirm.py      # writes analysis/ca1_mt1c_confirm.md + .json

1. **CA-1 release rule** "governing flip + 0.02 on the BL-027 body" (TEST_PLAN, test kit: 0.276).
   flip = PAHT-CF record ratio (0.30, ASSUMPTION PAHT_FAT) / fatigue margin at 0.30, for every printed part whose
   fatigue rests on the ratio: the H1-G0.55-B1/2.5 body (h1_buckling.json ``chosen``), the 28 mm IM3 cheek at its
   design angle and at DIR_SCATTER (+10 deg aft, im3_body_simloads.json), and the z 234 joint (h1_buckling.json
   ``joint``). The margin of every part scales linearly with the ratio (fatigue = fat / (FI99 x 1.6 g / factor),
   fat = ratio x 0.8 x UTS: frame_comp_d / h1_sleeve), so at a measured ratio r the margin is m(0.30) x r / 0.30.

2. **MT-1c bound** "the cinch counts as static if its peak-to-peak swing <= 10 % of the mean tension".
   Result: margin >= 1.0 holds at 0.276 with a 10 % swing, but the flip + 0.02 rule does not (it needs 0.294), so
   the kit takes the R1 level from the measured swing (``graded``) instead of a pass/fail at 10 %.
   The body has two fatigue values on the same sim sets: cinch static (1.175, the loop left out of static carry) and
   cinch cycled (0.782, the whole loop in it). FI99 is a max over voxels of sums that are linear in the loads, so
   1 / margin is convex in the cycled fraction q of the cinch loop and the chord between the two runs is an upper
   bound on it (conservative): 1/m(q) <= 1/m_s + q (1/m_c - 1/m_s).
   A measured swing p (peak-to-peak / mean) maps to q = p / (0.9 k): the record ratio is a max-stress value at
   R 0.1 (range 0.9 x peak), and the cycled run represents the cinch at k times its preload. k is not stated by
   the run (``fixed_part`` is added unscaled to the static-carry set before the 1.6 g / factor scaling), so it is
   bracketed: k 0.8 (unscaled loop seen through 1.6 / 2.0) to 1.6 (loop scaled with the walking g). The smaller k
   is the worse case and governs.

Every input is read from the analysis JSON at run time; nothing is typed here except the bracketing constants.

3. **Structural countersign (2026-11-13, structural-fea-engineer)**: ``explicit_run`` re-solves the BL-027 body
   (H1-G0.55-B1/2.5 + 28 mm IM3 cheeks) on the cinch-static and cinch-cycled fine_sm8 sets and splits every
   static-carry set into its walking part W (1 g) and its cinch loop C (1.0 x the 150 N rev C preload). It reproduces
   both official margins (1.1751 / 0.7818) and shows the cycled run is exactly 1.6 W + 1.6 C, i.e. k = 1.6, not a
   bracket. It then sweeps the cinch as an explicit cyclic component, in the doc's convention (peak = 1.6 W + a C,
   preload mean ignored) and with a linear Goodman correction (ASSUMPTION GOODMAN) from the frame's cycle
   (walking 0 -> 1.6 g, cinch mean = preload, swing p peak-to-peak / mean, in phase) to the R 0.1 coupon. Results go
   to ``analysis/ca1_countersign.json`` (``python designs/pack_5200/ca1_mt1c_confirm.py --explicit``, ~5 min);
   ``countersign`` turns them into the R1 rule. The chord functions above are kept because
   ``physical_test_kit.swing_rule`` imports them; their table is superseded by the countersign.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AN = HERE / "analysis"
sys.path.insert(0, str(HERE))
import physical_test_kit as K  # noqa: E402  (release_levels: the levels the kit prints)

SWING_BOUND = 0.10        # the MT-1c bound BL-038 wrote (ASSUMPTION CINCH-SWING), checked here
K_BRACKET = (0.8, 1.0, 1.6)   # ASSUMPTION CINCH-K: the cycled run carries the cinch at k x its preload (see doc)
R_RANGE = 0.9             # R 0.1: range = 0.9 x peak (CA1_fatigue_rig.md section 3)
CUSHION = 0.02            # the "+ 0.02" of the release rule (BL-023 / BL-038)
FAT_GOAL = 1.15           # BL-021 / BL-024 / BL-027 fatigue goal "to cover scatter" (h1_buckling.json targets)


def _json(name: str) -> dict:
    return json.loads((AN / name).read_text())


def inputs() -> dict:
    hb = _json("h1_buckling.json")
    ch = hb["chosen"]
    ims = _json("im3_body_simloads.json")["eye"]["cands"]["14_8"]
    jt = hb["chosen"]["joint"]                    # basis -> [strength, fatigue]; worst static-cinch basis (beam)
    joint_fat = min(float(v[1]) for b, v in jt.items() if not b.endswith(".cyc"))
    return {"record_ratio": float(K.record("pa12_cf_fdm_paht")["properties"]["fatigue_1e5_ratio"]),
            "body": ch["name"], "m_body": float(ch["fatigue_min_sim"]), "m_body_beam": float(ch["fatigue_beam"]),
            "m_body_cyc": float(ch["fatigue_cinch_cycled"]),
            "m_cheek": float(ims["design"]["fatigue"]["value"]),
            "m_cheek_dir": float(ims["sensitivity"]["fatigue_dir_plus_scatter"]),
            "cheek_mesh_spread_pct": float(ims["sensitivity"]["mesh_spread_pct"]),
            "m_joint": joint_fat, "fat_goal": float(hb["targets"]["fatigue"])}


def up3(x: float) -> float:
    """Round a release level up to 0.001 (as physical_test_kit.release_levels)."""
    return math.ceil(round(x, 6) * 1000) / 1000


def body_flip(i: dict, p: float, k: float) -> float:
    """Body flip ratio with a measured cinch swing p (peak-to-peak / mean), chord bound, capped at the cycled run."""
    q = min(p / (R_RANGE * k), 1.0)
    d = 1.0 / i["m_body_cyc"] - 1.0 / i["m_body"]
    return i["record_ratio"] * (1.0 / i["m_body"] + q * d)


def p_at_flip(i: dict, flip: float, k: float) -> float:
    """Largest swing p whose body flip stays <= ``flip`` (0 if even p = 0 exceeds it)."""
    d = 1.0 / i["m_body_cyc"] - 1.0 / i["m_body"]
    q = (flip / i["record_ratio"] - 1.0 / i["m_body"]) / d
    return max(min(q, 1.0), 0.0) * R_RANGE * k


def confirm() -> dict:
    i = inputs()
    lv = K.release_levels()
    rec = i["record_ratio"]
    flips = {"body (cinch static)": rec / i["m_body"], "IM3 cheek 28 mm, design angle": rec / i["m_cheek"],
             "IM3 cheek 28 mm, DIR_SCATTER +10 deg": rec / i["m_cheek_dir"],
             "z 234 joint (bolt boss, worst basis)": rec / i["m_joint"]}
    floor = max(f for n, f in flips.items() if "body" not in n)        # flips that the cinch swing does not move
    gov_part = max(flips, key=flips.get)
    gov = flips[gov_part]
    release = up3(gov + CUSHION)
    margins_at_release = {n: round(rec / f * release / rec, 3) for n, f in flips.items()}
    goal_level = up3(gov * i["fat_goal"])           # the alternative rule: keep the 1.15 goal at the measured ratio
    sw = {}
    for k in K_BRACKET:
        f10 = body_flip(i, SWING_BOUND, k)
        sw[f"k{k:g}"] = {
            "m_at_0.30_10pct": round(rec / f10, 4), "body_flip_10pct": round(f10, 4),
            "margin_at_release_10pct": round(release / f10, 4),
            "cushion_left_10pct": round(release - max(f10, floor), 4),
            "release_for_10pct": up3(max(f10, floor) + CUSHION),
            # largest swing that keeps (a) the rule flip + 0.02 at today's level, (b) margin >= 1.0 at it,
            # (c) flip + 0.02 within the 0.40 coupon level CA-1 also runs
            "p_rule_at_release": round(p_at_flip(i, release - CUSHION, k), 4),
            "p_margin1_at_release": round(p_at_flip(i, release, k), 4),
            "p_rule_at_040": round(p_at_flip(i, 0.40 - CUSHION, k), 4)}
    kmin = min(K_BRACKET)
    worst = sw[f"k{kmin:g}"]
    graded = []
    for p in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.70, 1.0):
        fb = body_flip(i, p, kmin)
        graded.append({"swing_pct": round(100 * p), "body_flip": round(fb, 4), "release": up3(max(fb, floor) + CUSHION)})
    out = {"ticket": "BL-039", "inputs": i, "flips": {n: round(v, 4) for n, v in flips.items()},
            "governing_part": gov_part, "flip_gov": round(gov, 4), "release": release, "kit_levels": lv,
            "release_matches_kit": abs(release - lv["release"]) < 1e-9 and abs(gov - lv["flip_gov"]) < 1e-4,
            "margins_at_release": margins_at_release, "goal_level_1p15": goal_level,
            "swing_bound": SWING_BOUND, "swing": sw, "swing_worst": worst,
            "swing_bound_margin_ok": worst["margin_at_release_10pct"] >= 1.0,
            "swing_bound_rule_ok": worst["release_for_10pct"] <= release,
            "graded": graded, "cycled_release": lv["release_cycled"]}
    out["countersign"] = countersign(out)
    return out


# ======================================================================================= structural countersign
CS_JSON = AN / "ca1_countersign.json"
CS_SWINGS = (0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00, 1.15, 1.50, 2.00)   # peak-to-peak / mean (2.0 = slack)
CS_PEAK_A = (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.2, 1.6)                 # cinch share of the peak, x preload
CINCH_MEAN_N = 150.0      # rev C cinch per anchor (load_standard.md 4.1): the C field is at this tension
IM3_EC_MARGIN = 1.15      # BL-023 coupon factor (physical_test_kit.IM3_EC_MARGIN)
EC_R_MAX = 0.02           # countersign: IM3-EC at R <= 0.02 (F_min only to keep the rig taut), not R 0.1


def goodman_r01(peak_r0: float) -> float:
    """ASSUMPTION GOODMAN: the R 0.1 coupon max (ratio units of the knocked strength) with the same linear-Goodman
    equivalent as a 0 -> ``peak_r0`` cycle. sa / (1 - sm) equal; coupon sa = 0.45 S, sm = 0.55 S."""
    x = (peak_r0 / 2.0) / (1.0 - peak_r0 / 2.0)
    return x / (0.45 + 0.55 * x)


def explicit_run(write: bool = True) -> dict:
    """Body fatigue with the cinch loop as an explicit cyclic load component (see the module doc, item 3)."""
    import numpy as np
    sys.path.insert(0, str(HERE.parents[1]))
    from huntkit.gendesign import frame_comp_d as D
    from huntkit.gendesign import frame_h1 as H1
    from huntkit.gendesign import h1_buckling as HB
    from huntkit.gendesign import h1_sleeve as S
    i = inputs()
    solid = HB.final_solid(1.0, 2.5)                        # the release body (h1_buckling chosen d_mid / d_up)
    dom = H1.base()["dom"]
    fs = S.solve_fields_w(dom, solid, S.kit_sets("fine_sm8", cycled=False))
    fc = S.solve_fields_w(dom, solid, S.kit_sets("fine_sm8", cycled=True))
    M = D.MATERIALS[H1.MAT]
    fi = lambda s: D.fi_material(s, M)                      # noqa: E731
    p99 = lambda x, ex: float(np.percentile(x[~ex], 99))    # noqa: E731  (H1's FI99 rule)
    gx = lambda x: x / (0.45 + 0.55 * x)                    # noqa: E731  (fully reversed eq. -> R 0.1 max)

    def goodman(smax, smin, ex, signed=False):
        sa, sm = (smax - smin) / 2.0, (smax + smin) / 2.0
        fa, fm = fi(sa), fi(sm)
        if signed:              # lower bound: no mean penalty where the dominant in-plane mean stress is compressive
            ip = sm[:, [0, 2]]
            dom_ = ip[np.arange(len(ip)), np.abs(ip).argmax(1)]
            fm = np.where(dom_ < 0, 0.0, fm)
        return p99(gx(fa / np.clip(1.0 - fm, 1e-3, None)), ex)
    ic = {(m["scenario"], m["case"]): k for k, m in enumerate(fc["meta"])}
    rows = {}
    for ks, m in enumerate(fs["meta"]):
        if m["case"] != "static_carry":
            continue
        tc = m["scenario"].replace("_fine_sm8_", "_fine_sm8_cyc_")
        if (tc, m["case"]) not in ic:
            continue                                        # the .alt neighbour sets have no cycled twin
        kc = ic[(tc, m["case"])]
        w = fs["stress"][ks].astype(float) / m["factor"]    # walking part at 1 g (assemble_loads factors the set)
        cl = fc["stress"][kc].astype(float) / m["factor"] - w   # cinch loop at 1.0 x preload
        es, ec = fs["ex"][m["scenario"]], fc["ex"][tc]
        eu = es | ec
        rows[m["scenario"]] = {
            "m_static": i["record_ratio"] / p99(fi(1.6 * w), es), "m_cycled": i["record_ratio"] / p99(fi(1.6 * w + 1.6 * cl), ec),
            "flip_peak_a": {f"{a:g}": p99(fi(1.6 * w + a * cl), eu) for a in CS_PEAK_A},
            "flip_goodman_no_cinch": goodman(1.6 * w, 0.0 * w, es),
            "flip_goodman": {f"{p:g}": goodman(1.6 * w + (1 + p / 2) * cl, (1 - p / 2) * cl, eu) for p in CS_SWINGS},
            "flip_goodman_signed": {f"{p:g}": goodman(1.6 * w + (1 + p / 2) * cl, (1 - p / 2) * cl, eu, True)
                                    for p in CS_SWINGS},
            "flip_goodman_antiphase_10pct": goodman(1.6 * w + 0.95 * cl, 1.05 * cl, eu)}
    worst = lambda f: max(f(r) for r in rows.values())     # noqa: E731
    out = {"date": "2026-11-13", "body": i["body"], "raster_g": D.mass_g(solid, H1.H, 1060.0), "n_pairs": len(rows),
           "m_static": min(r["m_static"] for r in rows.values()), "m_cycled": min(r["m_cycled"] for r in rows.values()),
           "governing_set": min(rows, key=lambda k: rows[k]["m_static"]),
           "flip_peak_a": {a: worst(lambda r, a=a: r["flip_peak_a"][a]) for a in rows[next(iter(rows))]["flip_peak_a"]},
           "flip_goodman_no_cinch": worst(lambda r: r["flip_goodman_no_cinch"]),
           "flip_goodman": {p: worst(lambda r, p=p: r["flip_goodman"][p]) for p in rows[next(iter(rows))]["flip_goodman"]},
           "flip_goodman_signed": {p: worst(lambda r, p=p: r["flip_goodman_signed"][p])
                                   for p in rows[next(iter(rows))]["flip_goodman_signed"]},
           "flip_goodman_antiphase_10pct": worst(lambda r: r["flip_goodman_antiphase_10pct"])}
    if write:
        CS_JSON.write_text(json.dumps(out, indent=1))
    return out


def _interp_p(table: dict, level: float) -> float:
    """Largest swing p whose flip in ``table`` (p -> flip, rising) stays <= ``level`` (linear between grid points)."""
    pts = sorted((float(p), f) for p, f in table.items())
    if pts[0][1] > level:
        return 0.0
    for (p0, f0), (p1, f1) in zip(pts, pts[1:]):
        if f1 > level:
            return p0 + (p1 - p0) * (level - f0) / (f1 - f0)
    return pts[-1][0]


def countersign(c: dict) -> dict | None:
    """The structural-fea-engineer's answers to the four BL-039 questions, from ``ca1_countersign.json``."""
    if not CS_JSON.exists():
        return None
    x = json.loads(CS_JSON.read_text())
    i, rec = c["inputs"], c["inputs"]["record_ratio"]
    fa = {float(a): v for a, v in x["flip_peak_a"].items()}
    f0, f16 = fa[0.0], fa[1.6]
    chord_excess = max(f0 + a / 1.6 * (f16 - f0) - v for a, v in fa.items())
    # other parts on the Goodman basis (their checks cycle 0 -> peak; the cheek's strap share is cycled x 1.6, which
    # bounds its preload + swing, so only the R 0 -> R 0.1 step applies)
    other = {n: goodman_r01(f) for n, f in c["flips"].items() if "body" not in n}
    floor = max(other.values())
    gtab = []
    for p, f in sorted(((float(p), f) for p, f in x["flip_goodman"].items())):
        gtab.append({"swing_pct": round(100 * p), "body_flip": round(f, 4),
                     "body_flip_signed": round(x["flip_goodman_signed"][f"{p:g}"], 4),
                     "doc_flip": round(body_flip(i, p, min(K_BRACKET)), 4),
                     "level": up3(max(f, floor) + CUSHION)})
    gt = {float(p): max(f, floor) for p, f in x["flip_goodman"].items()}
    p040 = _interp_p(gt, 0.40 - CUSHION)
    p276 = _interp_p(gt, c["release"] - CUSHION)
    # IM3-EC: the coupon load and the angle the release flip is set at
    ims = _json("im3_body_simloads.json")["eye"]["cands"]["14_8"]
    sens = ims["sensitivity"]
    f1, th = float(sens["governing_combo_1g_n"]), float(sens["governing_combo_aft_deg"])
    peak = IM3_EC_MARGIN * 1.6 * f1
    dir_ratio = i["m_cheek"] / i["m_cheek_dir"]           # stress per N at +10 deg / at the computed angle
    p_cheek = rec / i["m_cheek_dir"]
    ec = {"combo_1g_n": round(f1, 1), "peak_n": round(peak), "aft_deg": round(th, 1),
          "aft_deg_dir": round(th + 10.0, 1),
          "proven_dir_margin_at_aft": round(IM3_EC_MARGIN / dir_ratio, 3),
          "peak_n_at_aft_for_dir": round(peak * dir_ratio),
          "r01_peak_n_at_dir": round(peak * goodman_r01(p_cheek) / p_cheek),
          "min_n_r002": round(EC_R_MAX * peak)}
    return {"explicit": x, "k_found": 1.6, "k_check": abs(f16 - rec / i["m_body_cyc"]) < 1e-6,
            "reproduces": abs(x["m_static"] - i["m_body"]) < 1e-6 and abs(x["m_cycled"] - i["m_body_cyc"]) < 1e-6,
            "chord_excess_max": round(chord_excess, 4), "chord_conservative": chord_excess >= 0.0,
            "r_gap_body": round(x["flip_goodman_no_cinch"] / (rec / i["m_body"]), 4),
            "other_goodman": {n: round(v, 4) for n, v in other.items()},
            "flip_static_goodman": round(x["flip_goodman"]["0"], 4),
            "flip_static_goodman_signed": round(x["flip_goodman_signed"]["0"], 4),
            "margin_at_276": round(c["release"] / x["flip_goodman"]["0"], 3),
            "margin_at_276_signed": round(c["release"] / x["flip_goodman_signed"]["0"], 3),
            "release_static": up3(max(x["flip_goodman"]["0"], floor) + CUSHION),
            "goal_level_1p15": up3(x["flip_goodman"]["0"] * FAT_GOAL),
            "table": gtab, "p_040_pct": round(100 * p040, 1), "p_276_pct": round(100 * p276, 1),
            "margin_040_static": round(0.40 / x["flip_goodman"]["0"], 3),
            "margin_040_p100": round(0.40 / x["flip_goodman"]["1"], 3),
            "antiphase_10pct": round(x["flip_goodman_antiphase_10pct"], 4), "ec": ec}


def countersign_md(c: dict, s: dict) -> list:
    x, ec = s["explicit"], s["ec"]
    t0 = next(r for r in s["table"] if r["swing_pct"] == 0)
    t10 = next(r for r in s["table"] if r["swing_pct"] == 10)
    t150 = next(r for r in s["table"] if r["swing_pct"] == 150)
    L = ["## Structural countersign (2026-11-13)", "",
         "structural-fea-engineer. **Verdict: not countersigned as written. Corrected: frame release R1 needs CA-1 to "
         f"pass 0.40 (3/3 run-outs), not {c['release']}.** The MT-1c swing then only has to be <= "
         f"{s['p_040_pct']:.0f} % with a mean cinch of <= {CINCH_MEAN_N:.0f} N per anchor. The flip arithmetic and the "
         f"IM3-EC load arithmetic are right. The basis under them is not, for two reasons. (a) The {c['release']} rule "
         "leaves out the mean stress from the cinch preload. (b) It compares the frame's 0 -> 1.6 g cycle (R 0) with "
         f"the R 0.1 coupon at equal max stress. The R gap alone takes the whole 0.02 cushion (+"
         f"{x['flip_goodman_no_cinch'] - c['flips']['body (cinch static)']:.4f}), and the preload adds "
         f"{x['flip_goodman']['0'] - x['flip_goodman_no_cinch']:.4f} more.", "",
         f"Method: `explicit_run` in this script (data `{CS_JSON.name}`). The H1-G0.55-B1/2.5 release body "
         f"(raster {x['raster_g']:.1f} g, same as `h1_buckling.json`) is re-solved on the BL-027 fine_sm8 sets, cinch "
         f"static and cinch cycled. Each of the {x['n_pairs']} static-carry sets (3 kits x settings, meat and fill) "
         "is split into a walking part W at 1 g and a cinch loop C at the 150 N rev C preload. The split is exact "
         f"because the solve is linear. It reproduces both official margins: {x['m_static']:.4f} / {x['m_cycled']:.4f}"
         f" ({'exact' if s['reproduces'] else 'MISMATCH'}). The solver chain's closed-form checks (cantilever, simply "
         "supported beam, Euler, thin-wall torsion, CLT) pass in `tests/test_fea.py`.", "",
         "### Q1. The k bracket", "",
         f"- **k is not a bracket. It is exactly 1.6, so k 0.8 is not a possible worst end.** "
         "`frame_topopt.assemble_loads` multiplies the *whole* set by the case factor (`F = factor x f`), the "
         "unscaled cinch loop included. `frame_comp_d.evaluate` then divides FI99 by the factor and multiplies by "
         "1.6. The cycled run is therefore peak = 1.6 W + 1.6 C. The explicit sweep at a = 1.6 gives "
         f"{x['flip_peak_a']['1.6']:.4f} = 0.30 / {c['inputs']['m_body_cyc']:.4f} "
         f"({'checked' if s['k_check'] else 'NOT matched'}). The \"seen through 1.6 / 2.0\" reading (k 0.8) does "
         "not match the code. Within the doc's own convention, k 0.8 overstates the swing's effect by 2x. That error "
         "is on the safe side.",
         "- **The explicit cyclic run (one set at a time, cinch scaled on its own)** is the table below. 'Doc' is the "
         "BL-039 chord at k 0.8. The line under the table is the doc's convention with the cinch explicit (preload "
         "mean ignored, swing range on top of 1.6 W). 'Goodman' is the frame's real cycle: walking 0 -> 1.6 g, cinch mean = preload, "
         "swing in phase, mapped to the R 0.1 coupon by linear Goodman on the knocked strength. The 'signed' column "
         "gives no mean penalty where the in-plane mean is compressive. It is a lower bound only, because it also "
         "drops interlayer-shear means. Antiphase at 10 % gives "
         f"{s['antiphase_10pct']:.4f} < {t10['body_flip']:.4f} in phase, so in phase governs.", "",
         "| swing p-p / mean | doc flip (k 0.8 chord) | Goodman flip | Goodman signed (lower bound) | R1 CA-1 level (flip + 0.02) |",
         "|---:|---:|---:|---:|---:|"]
    for r in s["table"]:
        L.append(f"| {r['swing_pct']} % | {r['doc_flip']:.4f} | {r['body_flip']:.4f} | {r['body_flip_signed']:.4f} | "
                 f"{r['level']} |")
    pa = x["flip_peak_a"]
    L += ["", f"Doc convention with the cinch explicit (peak = 1.6 W + a x C): a 0 {pa['0']:.4f}, 0.1 {pa['0.1']:.4f}, "
          f"0.5 {pa['0.5']:.4f}, 1.0 {pa['1']:.4f}, 1.6 {pa['1.6']:.4f}. On that basis the table would loosen, "
          "not tighten. The basis is the problem, not k.", "",
          "### Q2. The linear chord", "",
          f"- On this body the chord is above the explicit curve at every point of the sweep (largest excess "
          f"{s['chord_excess_max']:.4f} at full cycling). Within its convention it is conservative. That is a "
          "*result*, not true \"by construction\": FI99 is a 99th percentile (`np.percentile(..., 99)`), not a max, "
          "and a percentile of convex functions is not convex. Re-check it whenever the body changes.",
          f"- It is **non-conservative** in three places. (1) Both of its endpoints leave out the cinch preload's "
          f"mean stress and the R 0 / R 0.1 gap, so the doc's table is below the Goodman flip for every swing up to "
          f"about 35 % (0 %: {t0['doc_flip']:.4f} against {t0['body_flip']:.4f}; 10 %: {t10['doc_flip']:.4f} "
          f"against {t10['body_flip']:.4f}). (2) The cap at q = 1 is inconsistent with the doc's own k 0.8 mapping "
          "for swings above 72 %, where that mapping says the cinch passes the cycled run. (3) The table reads only "
          f"the relative swing. Every value in it assumes a mean cinch of <= {CINCH_MEAN_N:.0f} N per anchor, so "
          "MT-1c must record the mean too. If the mean is higher, re-run with C scaled by mean / 150.", "",
          "### Q3. The IM3-EC coupon load", "",
          f"- 1.15 x 1.6 x {ec['combo_1g_n']} N = {ec['peak_n']} N: **arithmetic correct** (hook 15fL + IM3 strap, "
          f"{ec['aft_deg']} deg aft of the stay axis, `im3_body_simloads.json` 14_8). The cheek check cycles the strap "
          "share x 1.6, which bounds its preload + swing, so the cinch does not move this number.",
          f"- **The angle is wrong for the release flip.** The governing flip (0.2556) is the cheek at DIR_SCATTER, "
          f"i.e. {ec['aft_deg_dir']} deg aft. A coupon pulled at {ec['aft_deg']} deg at {ec['peak_n']} N proves only "
          f"{ec['proven_dir_margin_at_aft']:.3f} at that angle, not 1.15. **Correction: lead the pull at "
          f"{ec['aft_deg_dir']:.0f} deg aft at {ec['peak_n']} N** (or keep {ec['aft_deg']:.0f} deg and raise the load "
          f"to {ec['peak_n_at_aft_for_dir']} N).",
          f"- **Run it at R <= {EC_R_MAX} (F_min about {ec['min_n_r002']} N, just enough to keep the rig taut), not "
          "R 0.1.** IM3-EC is a structural proof of the in-service cycle, which is 0 -> peak. At R 0.1 the same "
          f"Goodman step needs about {ec['r01_peak_n_at_dir']} N at {ec['aft_deg_dir']:.0f} deg. CA-1 itself stays at "
          "R 0.1, because it measures the material ratio as the record defines it.", "",
          "### Q4. The release rule and the swing table", "",
          f"- **{c['release']} (0.2556 + 0.02) is not countersigned.** On the Goodman basis the R 0 / R 0.1 gap alone "
          f"moves the body flip from {c['flips']['body (cinch static)']} to {x['flip_goodman_no_cinch']:.4f} (x {s['r_gap_body']:.3f}). "
          f"The 150 N preload's mean stress moves it on to **{s['flip_static_goodman']:.4f}** "
          f"(signed lower bound {s['flip_static_goodman_signed']:.4f}). At {c['release']} the body margin is "
          f"{s['margin_at_276']:.3f} ({s['margin_at_276_signed']:.3f} on the lower bound). That is below HA-LS-1's "
          "1.0, or above it with less than the 0.02 cushion. Cheek and joint on the same basis: "
          + "; ".join(f"{n} {v:.4f}" for n, v in s["other_goodman"].items())
          + ". The body governs. With a static cinch the flip + 0.02 rule gives "
          f"**{s['release_static']}**. The 1.15 scatter goal would need {s['goal_level_1p15']}.",
          f"- **The swing table is replaced by the 'R1 CA-1 level' column above.** In practice: **R1 = CA-1 passes "
          f"0.40** (3/3 run-outs), and MT-1c shows a swing of <= {s['p_040_pct']:.0f} % with a mean of <= "
          f"{CINCH_MEAN_N:.0f} N per anchor. Body margin at 0.40: {s['margin_040_static']:.3f} with the cinch static, "
          f"{s['margin_040_p100']:.3f} at a 100 % swing. The 0.40 bars are already in CA-1 step 3, so no new test "
          "is needed; R1 only waits for that run (3 x 27.8 h). If 0.40 fails, run 3 XY bars at the table level for "
          f"the measured swing (>= {s['release_static']}). {c['release']} on its own releases nothing (it covers "
          f"{s['p_276_pct']:.0f} % swing). The old rows '<= 0.4 % -> 0.276', '<= 70 % -> 0.40' and '> 70 % -> 0.404' "
          "are withdrawn. Above a "
          f"{s['p_040_pct']:.0f} % swing the level goes above 0.40 ({t150['level']} at 150 %), and the cinch needs a "
          "re-run or a firmer strap.",
          "- T5 (P2, 0.4 -> 1.6 g dead + crank, 1e5 cycles) stays the frame-level gate. Its 0.4 g dead load puts mean "
          "stress into the test, so it checks this correction on the real part.", "",
          "### Assumptions added by the countersign", "",
          "- ASSUMPTION GOODMAN: linear Goodman on the hot/wet-knocked strength (ratio units, U = 1) links the frame "
          "cycle to the R 0.1 coupon; mean taken as |FI(mean)| (conservative where the mean is compressive; the "
          "signed column bounds that). Standard design practice for short-fibre thermoplastics; Gerber would be less "
          "severe. Settled by: a CA-1 pair at R 0.4 or 0.5 if the owner wants credit for a milder mean-stress law.",
          f"- ASSUMPTION CINCH-MEAN: the cinch mean equals the rev C {CINCH_MEAN_N:.0f} N per anchor; the swing is in "
          "phase with the walking g (antiphase checked, less severe). Settled by: MT-1c (record mean and swing).",
          "- HA-LS-1's 0 -> 1.6 g walking cycle is kept; a real 0.4 -> 1.6 g stride cycle is milder on Goodman, so "
          "this is conservative.", "",
          "### Downstream to regenerate (not done here; another agent is editing nearby files)", "",
          "- `physical_test_kit.py`: `release_levels` / `swing_rule` (R1 level 0.40, swing <= "
          f"{s['p_040_pct']:.0f} %, mean <= {CINCH_MEAN_N:.0f} N; read `countersign()`), `im3_ec_load` (aft "
          f"{ec['aft_deg_dir']:.0f} deg, F_min {ec['min_n_r002']} N), the CA-1 / MT-1c / IM3-EC register rows, guide G4, "
          "and `outputs/release/test_kit/`.",
          "- `tests_physical/CA1_fatigue_rig.md` sections 1, 6 and 6a; the TEST_PLAN R1 row; the BL-038 line in "
          "`docs/DECISIONS.md`; `tests/test_ca1_mt1c_confirm.py::test_im3_ec_load_from_the_bl021_demand` (checks the "
          "rig doc still says 0.276) and `test_kit_uses_the_graded_rule`, when the kit switches.", ""]
    return L


def report(c: dict) -> str:
    i, sw, w = c["inputs"], c["swing"], c["swing_worst"]
    L = ["# BL-039 structural confirmation: CA-1 release level and the MT-1c cinch bound", "",
         "Generated by `python designs/pack_5200/ca1_mt1c_confirm.py` (data `ca1_mt1c_confirm.json`), 2026-11-13. "
         "Inputs read at run time: `h1_buckling.json` (BL-027 body " + i["body"] + ", chosen, and its z 234 joint), "
         "`im3_body_simloads.json` (28 mm IM3 cheek, cands 14_8), `pa12_cf_fdm_paht` record (fatigue_1e5_ratio "
         f"{i['record_ratio']}, ASSUMPTION PAHT_FAT); rules from `load_standard.md` (HA-LS-1 rev C: fatigue 1e5 "
         "cycles 0 -> 1.6 g x 68 kg) and the 1.15 scatter goal of BL-021 / BL-024 / BL-027. Ratio = 1e5-cycle max "
         "stress / (0.8 x UTS) at R 0.1. Structural owner's role taken by the pack-designer for this ticket; the "
         "structural-fea-engineer should countersign (see the report).", "",
         *([f"> **Superseded in part (2026-11-13): see \"Structural countersign\" at the end.** R1 needs CA-1 to "
             f"pass 0.40 (MT-1c swing <= {c['countersign']['p_040_pct']:.0f} %, mean <= {CINCH_MEAN_N:.0f} N per "
             f"anchor), not {c['release']}; IM3-EC is pulled {c['countersign']['ec']['aft_deg_dir']:.0f} deg aft at R "
             f"<= {EC_R_MAX}.", ""] if c.get("countersign") else []),
         "## Answer", "",
         f"- **CA-1 release rule \"flip + 0.02 on the BL-027 body\": confirmed, {c['release']}.** Governing flip "
         f"**{c['flip_gov']}** ({c['governing_part']}) + 0.02 = **{c['release']}** = the level the test kit prints "
         f"({'matches' if c['release_matches_kit'] else 'DOES NOT MATCH'}). Correction to the wording: BL-038 named "
         f"the cheek at its design angle (flip {c['flips']['IM3 cheek 28 mm, design angle']}); at the DIR_SCATTER "
         f"angle BL-021 sized it to, the cheek flips at {c['flips']['IM3 cheek 28 mm, DIR_SCATTER +10 deg']}, "
         f"0.0003 above the body ({c['flips']['body (cinch static)']}). Same rounded level; the kit now names both.",
         "- **What it buys:** fatigue margins at the release level "
         + "; ".join(f"{n} **{m:.3f}**" for n, m in c["margins_at_release"].items())
         + ". Every part >= 1.0 (HA-LS-1's fatigue rule), with a 0.02 coupon cushion (about 8 % of the flip). It "
         f"is **not** the 1.15 analysis-scatter goal: that would need CA-1 >= **{c['goal_level_1p15']}** (about the "
         "record value). 0.276 is a print release for the prototype frames; the 1e5-cycle T5 test on P2 "
         "(0.4 -> 1.6 g, `load_standard.md` 5.3) stays the frame fatigue gate before field use.",
         f"- **MT-1c bound \"static if peak-to-peak <= 10 % of the mean\": confirmed only for margin >= 1.0, not for "
         f"the release rule. Corrected.** With a 10 % swing the body margin at {c['release']} is "
         f"**{w['margin_at_release_10pct']:.3f}** (worst bracket k {min(K_BRACKET):g}; "
         f"{sw['k1']['margin_at_release_10pct']:.3f} at k 1, {sw['k1.6']['margin_at_release_10pct']:.3f} at k 1.6): "
         f"still >= 1.0 (1.0 is reached at a {100 * w['p_margin1_at_release']:.1f} % swing). But the swing moves the "
         f"body flip to {w['body_flip_10pct']}, so the rule the owner accepted (flip + 0.02) gives "
         f"**{w['release_for_10pct']}**, not {c['release']}: a 10 % swing leaves {1000 * w['cushion_left_10pct']:.1f} "
         f"of the 20 thousandths of cushion. Holding the rule, {c['release']} only covers a swing up to "
         f"**{100 * w['p_rule_at_release']:.1f} %**, i.e. a cinch that does not measurably move.",
         f"- **Correction applied (kit and register):** MT-1c records the swing; R1 takes the CA-1 level from the "
         f"table in section 2. Practically: swing <= {100 * w['p_rule_at_release']:.1f} %: {c['release']}; up to "
         f"**{100 * w['p_rule_at_040']:.0f} %**: CA-1 must also pass the **0.40** run it already makes (3 XY bars, no "
         f"new test); above that: {c['cycled_release']} (the cycled level). A swing up to "
         f"{100 * w['p_margin1_at_release']:.1f} % with only the {c['release']} pass keeps margin >= 1.0 but no "
         "cushion: an owner call, not the default (see OWNER DECISIONS in the BL-039 report).",
         f"- **Correction (wording):** the old guide line \"the 0.40 run covers it\" for a cycling cinch was wrong: "
         f"the cycled level is {c['cycled_release']} > 0.40. Fixed.", "",
         "## 1. Flip points (ratio at which each part's fatigue margin is 1.0)", "",
         "| part | fatigue margin at 0.30 | flip | margin at the release level |", "|---|---:|---:|---:|"]
    mm = {"body (cinch static)": i["m_body"], "IM3 cheek 28 mm, design angle": i["m_cheek"],
          "IM3 cheek 28 mm, DIR_SCATTER +10 deg": i["m_cheek_dir"],
          "z 234 joint (bolt boss, worst basis)": i["m_joint"]}
    for n, f in c["flips"].items():
        L.append(f"| {n} | {mm[n]:.3f} | {f:.4f} | {c['margins_at_release'][n]:.3f} |")
    L += ["", f"Body beam basis {i['m_body_beam']:.3f} (flip {i['record_ratio'] / i['m_body_beam']:.4f}) does not "
          f"govern. Cheek mesh spread {i['cheek_mesh_spread_pct']:.1f} % (h 1.0 / 0.8 / 0.7 mm): the design value is "
          "the worst grid. Margins scale exactly with the ratio for the rule used (fatigue = fat / (FI99 x 1.6 / "
          "factor), fat proportional to the ratio: frame_comp_d / h1_sleeve).", "",
          "## 2. MT-1c: cinch swing against the body margin", "",
          f"Body cinch static {i['m_body']:.4f}, cinch cycled {i['m_body_cyc']:.4f} (same sim sets). Chord bound "
          "1/m(q) <= 1/m_s + q (1/m_c - 1/m_s), q = p / (0.9 k), capped at the cycled run (q = 1).", "",
          "| k | margin at 0.30, 10 % swing | body flip, 10 % | margin at "
          f"{c['release']}, 10 % | swing for margin 1.0 at {c['release']} | swing that keeps flip + 0.02 <= "
          f"{c['release']} | swing that keeps flip + 0.02 <= 0.40 | level for a 10 % swing |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in K_BRACKET:
        d = sw[f"k{k:g}"]
        L.append(f"| {k:g} | {d['m_at_0.30_10pct']:.3f} | {d['body_flip_10pct']:.4f} | "
                 f"{d['margin_at_release_10pct']:.3f} | {100 * d['p_margin1_at_release']:.1f} % | "
                 f"{100 * d['p_rule_at_release']:.1f} % | {100 * d['p_rule_at_040']:.0f} % | {d['release_for_10pct']} |")
    L += ["", f"CA-1 release level for a measured swing (worst k {min(K_BRACKET):g}, + 0.02; the cheek and joint flips "
          "are the floor):", "", "| swing (peak-to-peak / mean) | body flip | CA-1 release level |", "|---:|---:|---:|"]
    for g in c["graded"]:
        L.append(f"| {g['swing_pct']} % | {g['body_flip']:.4f} | {g['release']} |")
    L += ["", "The IM3 cheek is not affected by the swing: its check already cycles the rev C IM3 strap force with "
          "the walking g (hook + strap combination x 1.6, `im3_body_simloads.py` eye rows).", "",
          "## 3. Assumptions", "",
          "- ASSUMPTION PAHT_FAT (record 0.30): settled by CA-1 itself.",
          "- ASSUMPTION CINCH-K: the cycled run carries the cinch loop at 0.8-1.6 x its preload (the loop is added "
          "unscaled to static carry; whether the 1.6 g / factor scaling reaches it is not recorded); the worst end "
          "(0.8) is used. Settled by re-running the body with the MT-1c measured swing as a cyclic load "
          "(structural-fea-engineer), if the owner wants credit above the table.",
          "- The chord bound (a max of linear terms is convex) is conservative by construction.",
          "- The 0.02 cushion is not a statistical allowable: 3/3 run-outs say the batch median is likely above the "
          "level, not a B-basis value. T5 (1e5 cycles on P2) remains the frame-level fatigue check.", ""]
    if c.get("countersign"):
        L += countersign_md(c, c["countersign"])
    return "\n".join(L)


SCREEN = HERE.parents[1] / "outputs" / "screens" / "20261113_BL039_1.png"


def plot(c: dict, path: Path = SCREEN) -> Path:
    """Phone-readable chart: CA-1 level R1 needs against the MT-1c cinch swing (worst k), with margin-1.0 line."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    i, k = c["inputs"], min(K_BRACKET)
    floor = max(f for n, f in c["flips"].items() if "body" not in n)
    ps = [x / 1000 for x in range(0, 1001, 2)]
    lev = [up3(max(body_flip(i, p, k), floor) + CUSHION) for p in ps]
    flip = [max(body_flip(i, p, k), floor) for p in ps]
    ink, muted, grid, blue = "#1f1f1e", "#6b6a66", "#e4e2dc", "#2a78d6"
    fig, ax = plt.subplots(figsize=(7.2, 5.4), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    ax.plot([100 * p for p in ps], lev, color=blue, lw=2, label="CA-1 level R1 needs (flip + 0.02)")
    ax.plot([100 * p for p in ps], flip, color=muted, lw=1.2, ls="--", label="governing flip (margin 1.0)")
    for y, t, dy in ((c["release"], f"{c['release']}: release level", 0.0), (0.40, "0.40: coupon run", -0.004),
                     (c["cycled_release"], f"{c['cycled_release']}: cinch fully cycling", 0.004)):
        ax.axhline(y, color=grid, lw=1, zorder=0)
        ax.text(101, y + dy, t, va="center", fontsize=8, color=ink)
    w = c["swing_worst"]
    ax.axvline(10, color=grid, lw=1, zorder=0)
    ax.annotate(f"BL-038 bound 10 %:\nneeds {w['release_for_10pct']},\nmargin at {c['release']} = "
                f"{w['margin_at_release_10pct']:.3f}", (10, w["release_for_10pct"]), (22, 0.29), fontsize=8,
                color=ink, arrowprops=dict(arrowstyle="-", color=muted, lw=0.8))
    ax.annotate(f"0.40 covers up to {100 * w['p_rule_at_040']:.0f} %", (100 * w["p_rule_at_040"], 0.40),
                (45, 0.375), fontsize=8, color=ink, arrowprops=dict(arrowstyle="-", color=muted, lw=0.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0.24, 0.42)
    ax.set_xlabel("MT-1c cinch swing, peak-to-peak / mean (%)", color=ink, fontsize=9)
    ax.set_ylabel("PAHT-CF fatigue ratio (1e5, R 0.1)", color=ink, fontsize=9)
    ax.set_title("BL-039: CA-1 level for frame release R1 vs. the measured cinch swing\n"
                 f"(H1 body + 28 mm IM3 cheek; worst bracket k {k:g})", fontsize=10, color=ink, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(muted)
    ax.tick_params(colors=muted, labelsize=8)
    ax.grid(axis="y", color=grid, lw=0.6)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


CS_SCREEN = HERE.parents[1] / "outputs" / "screens" / "20261113_ca1_countersign_1.png"


def plot_countersign(c: dict, path: Path = CS_SCREEN) -> Path:
    """Phone-readable chart: body flip against the MT-1c swing, BL-039 chord (k 0.8) vs the explicit runs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = c["countersign"]
    x = s["explicit"]
    ink, muted, grid = "#1f1f1e", "#6b6a66", "#e4e2dc"
    blue, orange, green = "#2a78d6", "#d9822b", "#3a9a5b"
    ps = sorted(float(p) for p in x["flip_goodman"])
    fig, ax = plt.subplots(figsize=(7.2, 5.6), dpi=150)
    pp = [p / 1000 for p in range(0, 2001, 5)]
    ax.plot([100 * p for p in pp], [body_flip(c["inputs"], p, min(K_BRACKET)) for p in pp], color=muted, lw=1.6,
            ls="--", label="BL-039 chord, k 0.8 (doc)")
    ax.plot([100 * p for p in ps], [x["flip_goodman"][f"{p:g}"] for p in ps], color=blue, lw=2.2, marker="o", ms=4,
            label="explicit run, Goodman (countersign basis)")
    ax.plot([100 * p for p in ps], [x["flip_goodman_signed"][f"{p:g}"] for p in ps], color=blue, lw=1, ls=":",
            label="explicit, Goodman signed (lower bound)")
    pa = sorted(float(a) for a in x["flip_peak_a"])
    ax.plot([100 * a for a in pa], [x["flip_peak_a"][f"{a:g}"] for a in pa], color=green, lw=1.4,
            label="explicit, doc convention (a = p)")
    for y, t in ((c["release"], f"{c['release']}: BL-039 release"), (0.40, "0.40: CA-1 run, R1 level (countersign)")):
        ax.axhline(y, color=orange if y == 0.40 else grid, lw=1.2 if y == 0.40 else 1, zorder=0)
        ax.text(2, y + 0.003, t, fontsize=8, color=ink)
    ax.axhline(0.38, color=orange, lw=0.8, ls=":", zorder=0)
    ax.axvline(s["p_040_pct"], color=orange, lw=0.8, ls=":")
    ax.text(s["p_040_pct"] - 2, 0.445, f"0.40 covers\n<= {s['p_040_pct']:.0f} % swing", fontsize=8, color=ink,
            ha="right", va="top")
    ax.set_xlim(0, 200)
    ax.set_ylim(0.24, 0.46)
    ax.set_xlabel("MT-1c cinch swing, peak-to-peak / mean (%), mean 150 N per anchor", color=ink, fontsize=9)
    ax.set_ylabel("body flip ratio (CA-1 R 0.1 level for margin 1.0)", color=ink, fontsize=9)
    ax.set_title("CA-1 countersign: body flip vs cinch swing (H1-G0.55-B1/2.5)\n"
                 f"static cinch: doc {c['flip_gov']}, explicit Goodman {s['flip_static_goodman']:.3f}; "
                 "R1 needs the 0.40 pass", fontsize=10, color=ink, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=muted, labelsize=8)
    ax.grid(axis="y", color=grid, lw=0.6)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> dict:
    if "--explicit" in sys.argv:
        explicit_run()
    c = confirm()
    print("screen:", plot(c))
    if c.get("countersign"):
        print("screen:", plot_countersign(c))
    (AN / "ca1_mt1c_confirm.json").write_text(json.dumps(c, indent=1, default=str))
    (AN / "ca1_mt1c_confirm.md").write_text(report(c), encoding="utf-8")
    print(json.dumps({k: c[k] for k in ("flip_gov", "release", "release_matches_kit", "goal_level_1p15",
                                        "swing_worst", "swing_bound_margin_ok", "swing_bound_rule_ok")}, indent=1))
    return c


if __name__ == "__main__":
    main()
