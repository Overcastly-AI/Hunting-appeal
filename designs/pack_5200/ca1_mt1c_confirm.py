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
    return {"ticket": "BL-039", "inputs": i, "flips": {n: round(v, 4) for n, v in flips.items()},
            "governing_part": gov_part, "flip_gov": round(gov, 4), "release": release, "kit_levels": lv,
            "release_matches_kit": abs(release - lv["release"]) < 1e-9 and abs(gov - lv["flip_gov"]) < 1e-4,
            "margins_at_release": margins_at_release, "goal_level_1p15": goal_level,
            "swing_bound": SWING_BOUND, "swing": sw, "swing_worst": worst,
            "swing_bound_margin_ok": worst["margin_at_release_10pct"] >= 1.0,
            "swing_bound_rule_ok": worst["release_for_10pct"] <= release,
            "graded": graded, "cycled_release": lv["release_cycled"]}


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
    return "\n".join(L)


def main() -> dict:
    c = confirm()
    (AN / "ca1_mt1c_confirm.json").write_text(json.dumps(c, indent=1, default=str))
    (AN / "ca1_mt1c_confirm.md").write_text(report(c), encoding="utf-8")
    print(json.dumps({k: c[k] for k in ("flip_gov", "release", "release_matches_kit", "goal_level_1p15",
                                        "swing_worst", "swing_bound_margin_ok", "swing_bound_rule_ok")}, indent=1))
    return c


if __name__ == "__main__":
    main()
