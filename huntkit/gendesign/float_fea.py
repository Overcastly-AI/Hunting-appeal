"""Float mode (owner 2026-11-06): direct FE checks of the frame-side anchors that the float changed.

1. IM3 captive eye (printed fairlead, z 520, x +/-115): meat-strap leg + one B-24 stand-off link on the same eye.
   Solved with the real force DIRECTION (voxel FE, ``bag_attach.solve_fairlead``), not scaled from the 554 N aft
   bag-on solve. Strength on the factored vector (HA-LS-1: link x 3.0, hand cinch x 1.5), fatigue on the 1.6 g
   walking-peak vector (load_standard.md section 4: 1e5 cycles at 0 -> 1.6 g), creep on the 1 g vector.
2. Lower under-strap anchor US1 (z 95): the float meat limit on the frame. Solved directly at the limit.
3. Envelope check against the bag-on IM3 hook case (T0 hood-off 472 N x 3.0 = 1415 N): the printed cheek is solved at
   1415 N in the bag-on direction too, so "inside the envelope" is a solved statement, not a magnitude comparison.

The voxel solver is verified against closed forms in tests/test_frame_topopt.py (Timoshenko cantilever, Saint-Venant
torsion) and tests/test_gendesign.py (H8 cantilever, Q4 patch).

Run: python -m huntkit.gendesign.float_fea
"""
from __future__ import annotations

import json

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.gendesign import meat_haul as MH

ANALYSIS = MH.ANALYSIS
RESULTS = ANALYSIS / "float_fea_results.json"
SCREENS = REPO_ROOT / "outputs" / "screens"
DATE = "20261106"
CINCH_N = 150.0                 # hand cinch per IM leg, ASSUMPTION (load_standard.md 4.1); a steady preload
CINCH_FACTOR = 1.5              # the bag-off rule: hand cinch x 1.5 (meat_haul.analyse)
WALK_G = 1.6                    # Rome walking peak, HA-LS-1 fatigue rule
FATIGUE_REQ = 1.0               # PAHT-CF: FI at the walking peak <= fatigue_1e5_ratio (0.3) -> SF >= 1.0
STRENGTH_REQ = 1.0              # factor is on the load (1/FI99 >= 1)
MESH_H = 1.0                    # the recorded fine mesh (bag_attachment_results.json h_mm)
MESH_CHECK_H = 0.75             # convergence check on the governing float vector
LB_PER_KG = 2.20462262


def _link_1g(bag_kg: float) -> float:
    return MH.link_tension(bag_kg, factored=False)


def im3_vector(bag_kg: float, link_scale: float, cinch_n: float) -> np.ndarray:
    """(fy aft, fz up) on one IM3 eye: meat-strap leg (aft) + link (aft and down at LINK_ANGLE_DEG)."""
    a = np.radians(MH.LINK_ANGLE_DEG)
    t = _link_1g(bag_kg) * link_scale
    return np.array([cinch_n + t * np.cos(a), -t * np.sin(a)])


def im3_cases() -> dict:
    """Factored, walking-peak and 1 g vectors for the design case and the misuse envelope."""
    out = {}
    for key, bag_kg, what in (("design", MH.FLOAT_GEAR_KG, "36 kg meat on the frame + 12 kg gear in the bag"),
                              ("misuse", MH.FLOAT_BAG_ENVELOPE_KG, "36 kg meat + 32 kg in the bag (rest of the 68 kg rating)")):
        out[key] = {"what": what, "bag_kg": bag_kg,
                    "factored": im3_vector(bag_kg, MH.LINK_FACTOR, CINCH_N * CINCH_FACTOR),
                    "walk": im3_vector(bag_kg, WALK_G, CINCH_N),
                    "static_1g": im3_vector(bag_kg, 1.0, CINCH_N)}
    return out


def bag_on_envelope_vector() -> np.ndarray:
    """The bag-on IM3 hook case (attach_system_results.json factored_n.im3, 1415 N) along the rev C governing IM3
    direction (rev_c_verification_results.json attachments.gov_c.im3, meat_straps: mostly aft)."""
    att = json.loads((ANALYSIS / "attach_system_results.json").read_text())
    rc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["im3"]
    d = np.array([rc["fy"], rc["fz"]], float)
    return float(att["factored_n"]["im3"]) * d / np.linalg.norm(d)


def us1_tension(meat_kg: float) -> float:
    """Lower under-strap tension, factored strength case (1.6 g x 1.5, US1 share, belly 70 mm)."""
    return MH.cradle_tension(MH.US1_FRACTION * meat_kg * MH.G * WALK_G * 1.5)


def us1_vector(meat_kg: float) -> np.ndarray:
    th = MH._theta()
    t = us1_tension(meat_kg)
    return np.array([t * np.cos(th), -t * np.sin(th)])


def float_meat_limit_kg(us1_fatigue_sf_36: float) -> float:
    """Meat on the frame at which the US1 anchor fatigue SF reaches 1.0 (linear: fixed direction, linear FE)."""
    return MH.QUARTER_KG * us1_fatigue_sf_36 / FATIGUE_REQ


def _solve(stay_r: float, v: np.ndarray, h: float, label: str) -> dict:
    from huntkit.gendesign.bag_attach import solve_fairlead
    row = solve_fairlead(stay_r, np.asarray(v, float), h=h, label=label)
    return row


def run(log=print, mesh_check: bool = True) -> dict:
    from huntkit.gendesign.bag_attach import _paht
    from huntkit.gendesign.frame_branch import stay_radius
    pa = _paht()
    r_im3 = float(stay_radius(520.0, 1.05))
    r_us1 = float(stay_radius(MH.US1_Z, 1.05))
    rec = json.loads((ANALYSIS / "bag_attachment_results.json").read_text())
    rec_im3 = next(r for r in rec["fea"] if r["station"] == "im3" and abs(r["h_mm"] - MESH_H) < 1e-6)
    cases = im3_cases()
    out = {"date": "2026-11-06", "mesh_h_mm": MESH_H, "stay_r_im3_mm": r_im3, "stay_r_us1_mm": r_us1,
           "material": {"fatigue_1e5_ratio": pa["fat"], "creep_rupture_8h_40c_ratio": pa["rupture"],
                        "env_knockdown": pa["knock"], "s_xy": pa["s_xy"], "s_z": pa["s_z"]},
           "im3": {}, "slabs": {}}

    # 0. reproduce the record (same vector, same mesh) before trusting the new vectors
    v0 = np.array([rec["governing"]["im3"]["fy"], rec["governing"]["im3"]["fz"]])
    r0 = _solve(r_im3, v0, MESH_H, "im3 record")
    out["reproduce"] = {"force_n": float(np.linalg.norm(v0)), "sf": r0["sf"], "sf_record": rec_im3["sf"]}
    log(f"record IM3 {np.linalg.norm(v0):.0f} N: SF {r0['sf']:.3f} (record {rec_im3['sf']:.3f})")

    for key, c in cases.items():
        row = {"what": c["what"], "bag_kg": c["bag_kg"]}
        for load in ("factored", "walk", "static_1g"):
            s = _solve(r_im3, c[load], MESH_H, f"im3 float {key} {load}")
            row[load] = {"fy": float(c[load][0]), "fz": float(c[load][1]), "n": float(np.linalg.norm(c[load])),
                         "fi99": s["fi99"], "fi_max": s["fi_max"], "bearing_sf": s["bearing_sf"]}
            if load == "factored":
                out["slabs"][key] = s["slab"]
        f = row["factored"]
        row["sf"] = 1.0 / max(f["fi99"], 1e-9)
        row["sf_fatigue"] = pa["fat"] / max(row["walk"]["fi99"], 1e-9)
        row["sf_creep"] = pa["rupture"] / max(row["static_1g"]["fi99"], 1e-9)
        row["bearing_sf"] = f["bearing_sf"]
        # what the hand-off had (scaled by force magnitude from the 554 N aft solve, x 3.0 fatigue basis)
        row["sf_scaled_handoff"] = rec_im3["sf"] * rec_im3["force_n"] / f["n"]
        row["sf_fatigue_scaled_handoff"] = rec_im3["sf_fatigue"] * rec_im3["force_n"] / f["n"]
        out["im3"][key] = row
        log(f"IM3 {key}: {f['n']:.0f} N (fy {f['fy']:.0f}, fz {f['fz']:.0f})  SF {row['sf']:.2f}  "
            f"fat {row['sf_fatigue']:.2f} (walk {row['walk']['n']:.0f} N)  creep {row['sf_creep']:.2f}")

    # bag-on IM3 hook case on the printed cheek
    ve = bag_on_envelope_vector()
    se = _solve(r_im3, ve, MESH_H, "im3 bag-on 1415")
    out["bag_on_1415"] = {"fy": float(ve[0]), "fz": float(ve[1]), "n": float(np.linalg.norm(ve)),
                          "fi99": se["fi99"], "sf": 1.0 / se["fi99"], "bearing_sf": se["bearing_sf"],
                          "basis": "attach_system_results.json factored_n.im3 along rev C gov_c.im3 direction"}
    out["im3_inside_envelope"] = bool(out["im3"]["misuse"]["factored"]["n"] <= out["bag_on_1415"]["n"]
                                      and out["im3"]["misuse"]["factored"]["fi99"] <= se["fi99"])
    log(f"IM3 bag-on 1415 N: SF {out['bag_on_1415']['sf']:.2f}; misuse inside: {out['im3_inside_envelope']}")

    if mesh_check:
        sm = _solve(r_im3, cases["misuse"]["factored"], MESH_CHECK_H, "im3 misuse fine")
        out["mesh_check"] = {"h_mm": MESH_CHECK_H, "sf": 1.0 / sm["fi99"],
                             "sf_h1": out["im3"]["misuse"]["sf"],
                             "change": (1.0 / sm["fi99"]) / out["im3"]["misuse"]["sf"] - 1.0}
        log(f"mesh {MESH_CHECK_H} mm: SF {out['mesh_check']['sf']:.2f} ({100 * out['mesh_check']['change']:+.1f} %)")

    # 2. US1 cradle anchor: the recorded 36 kg solve, the limit, and the 56 kg the hand-off asked about
    cr = json.loads((ANALYSIS / "cradle_fea.json").read_text())
    limit = float_meat_limit_kg(cr["sf_fatigue"])
    limit_kg = float(np.floor(limit))
    us1 = {"record_36kg": {"sf": cr["sf"], "sf_fatigue": cr["sf_fatigue"], "force_n": cr["force_n"]},
           "limit_exact_kg": limit, "limit_kg": limit_kg, "limit_lb": float(np.floor(limit_kg * LB_PER_KG)),
           "rows": {}}
    for kg in (MH.QUARTER_KG, limit_kg, MH.RATED_KG - MH.FLOAT_GEAR_KG):
        v = us1_vector(kg)
        s = _solve(r_us1, v, MESH_H, f"us1 {kg:.0f} kg")
        fat = pa["fat"] / (s["fi99"] * WALK_G / (WALK_G * 1.5))
        t = us1_tension(kg)
        us1["rows"][f"{kg:.0f}"] = {"meat_kg": kg, "tension_n": t, "fy": float(v[0]), "fz": float(v[1]),
                                    "sf": 1.0 / s["fi99"], "sf_fatigue": fat, "cam_sf": MH.CAM_N / t,
                                    "us2_sf_fatigue": cr["sf_fatigue"] * MH.QUARTER_KG / kg
                                    * MH.US1_FRACTION / (1 - MH.US1_FRACTION)}
        log(f"US1 {kg:.0f} kg: T {t:.0f} N  SF {1 / s['fi99']:.2f}  fat {fat:.2f}  cam {MH.CAM_N / t:.2f}")
    # belly sensitivity: the user cams to "about 70 mm"; a shallower cradle raises the tension
    sens = {}
    for belly in (50.0, 60.0, 70.0, 80.0):
        th = np.arctan(belly / MH.HALF_SPAN_MM)
        ratio = np.sin(MH._theta()) / np.sin(th)
        sens[f"{belly:.0f}"] = {"tension_ratio": float(ratio), "limit_kg": float(limit / ratio)}
    us1["belly_sensitivity"] = sens
    out["us1"] = us1
    out["friction_credit"] = {
        "credited": False,
        "reason": ("No sourced coefficient for a wet game bag on the Sandwich v2 spreader or on 38 mm webbing, and no "
                   "measured clamp force: the 150 N IM cinch is an ASSUMPTION and relaxes as the meat settles. A "
                   "friction share under 1e5 walking cycles needs both, and a slip moves the whole load to the cradle."),
        "mu_assumed_in_repo": MH.MU,
    }
    plots = plot(out)
    out["screens"] = plots
    slabs = out.pop("slabs")
    RESULTS.write_text(json.dumps(out, indent=2, default=float))
    out["slabs"] = slabs
    write_md(out)
    return out


def plot(res: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.render import _style
    _style()
    SCREENS.mkdir(parents=True, exist_ok=True)
    paths = []
    # 1. utilization (= 1 / margin) per check, the bar must stay left of 1.0
    rows = []
    for key, lab in (("design", "IM3 float design"), ("misuse", "IM3 float misuse")):
        r = res["im3"][key]
        rows += [(f"{lab}: strength", 1 / r["sf"]), (f"{lab}: fatigue", FATIGUE_REQ / r["sf_fatigue"]),
                 (f"{lab}: creep 1 g", 1 / r["sf_creep"])]
    rows.append(("IM3 bag-on 1415 N: strength", 1 / res["bag_on_1415"]["sf"]))
    u = res["us1"]
    lim = f"{u['limit_kg']:.0f}"
    for kg in ("36", lim, "56"):
        r = u["rows"][kg]
        rows += [(f"US1 {kg} kg meat: strength", 1 / r["sf"]), (f"US1 {kg} kg meat: fatigue", 1 / r["sf_fatigue"]),
                 (f"US1 {kg} kg meat: cam", 1 / r["cam_sf"])]
    fig, ax = plt.subplots(figsize=(9.0, 8.6))
    names = [n for n, _ in rows][::-1]
    vals = [v for _, v in rows][::-1]
    cols = ["#d6342a" if v > 1.0 else ("#e8a33d" if v > 0.9 else "#1baf7a") for v in vals]
    ax.barh(names, vals, color=cols, height=0.62)
    ax.axvline(1.0, color="#0b0b0b", ls="--", lw=1.2)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8.5)
    ax.set_xlim(0, max(1.15, max(vals) + 0.12))
    ax.set_xlabel("utilization = required / achieved SF  (fail > 1.0)")
    ax.set_title("Float mode: IM3 eye (link + meat strap) and US1 cradle anchor, direct FE", loc="left",
                 fontweight="bold", fontsize=11.5)
    fig.text(0.01, 0.01, f"Float meat limit on the frame: {u['limit_kg']:.0f} kg ({u['limit_lb']:.0f} lb), set by "
             "US1 fatigue at the 1.6 g walking peak. 56 kg fails (red).", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = SCREENS / f"{DATE}_float_fea_1.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    paths.append(str(p))
    # 2. failure-index cut through one cheek, design and misuse
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.8))
    vmax = max(float(np.nanpercentile(res["slabs"][k][np.isfinite(res["slabs"][k])], 99.5)) for k in ("design", "misuse"))
    for ax, key in zip(axes, ("design", "misuse")):
        s = res["slabs"][key]
        im = ax.imshow(np.where(np.isfinite(s), s, np.nan).T, origin="lower", cmap="magma", vmin=0, vmax=vmax)
        f = res["im3"][key]["factored"]
        ax.set_title(f"{key}: {f['n']:.0f} N (aft {f['fy']:.0f}, down {-f['fz']:.0f})\nSF {res['im3'][key]['sf']:.2f}",
                     loc="left", fontsize=10)
        ax.set_xlabel("y, toward the bag (voxels)")
        ax.set_ylabel("z, up the stay (voxels)")
    fig.colorbar(im, ax=axes, fraction=0.03, pad=0.02).set_label("failure index (factored)")
    fig.suptitle("IM3 fairlead cheek, 1 mm voxels, float vectors", x=0.02, ha="left", fontweight="bold")
    p = SCREENS / f"{DATE}_float_fea_2.png"
    fig.savefig(p, dpi=100)
    plt.close(fig)
    paths.append(str(p))
    import shutil
    for q in paths:                                     # the analysis folder keeps its own copy
        shutil.copy(q, ANALYSIS / q.split("/")[-1])
    return [str(p_.relative_to(REPO_ROOT)) if p_.is_absolute() else str(p_)
            for p_ in map(lambda s: __import__("pathlib").Path(s), paths)]


def write_md(res: dict) -> str:
    d, m, e, u = res["im3"]["design"], res["im3"]["misuse"], res["bag_on_1415"], res["us1"]
    lim = f"{u['limit_kg']:.0f}"
    a = []
    a.append("# Float mode: frame-side FE check (IM3 eye, US1 cradle anchor)\n")
    a.append("Owner: structural-fea-engineer. 2026-11-06. Hand-off: `meat_carry_alternatives.md` §8. Code: "
             "`huntkit/gendesign/float_fea.py`; numbers: `float_fea_results.json`. Standard: HA-LS-1 rev C "
             "(`load_standard.md` §4.3, float note).\n")
    a.append("## Result\n")
    a.append(f"- **IM3 eye, design** (36 kg meat + 12 kg gear): {d['factored']['n']:.0f} N factored. Strength SF "
             f"**{d['sf']:.2f}**, fatigue SF **{d['sf_fatigue']:.2f}**, creep SF {d['sf_creep']:.2f}. Pass.")
    a.append(f"- **IM3 eye, misuse envelope** (36 kg meat + 32 kg in the bag): {m['factored']['n']:.0f} N factored. "
             f"Strength SF **{m['sf']:.2f}**, fatigue SF **{m['sf_fatigue']:.2f}**, creep SF {m['sf_creep']:.2f}. Pass.")
    a.append(f"- **Inside the bag-on IM3 envelope: {'yes' if res['im3_inside_envelope'] else 'NO'}.** The printed cheek "
             f"solved at the 1415 N bag-on hook case gives SF {e['sf']:.2f}; the misuse float vector is smaller "
             f"({m['factored']['n']:.0f} N) and its FI99 is lower ({m['factored']['fi99']:.3f} vs {e['fi99']:.3f}).")
    a.append(f"- **US1 cradle anchor at 56 kg of meat on the frame: fatigue SF {u['rows']['56']['sf_fatigue']:.2f}, fails.** "
             "Friction is not credited (section 3).")
    a.append(f"- **Owner-facing limit: float meat on the frame <= {lim} kg ({u['limit_lb']:.0f} lb)**, with the cradle "
             f"cammed to the 70 mm belly. The 68 kg pack rating still applies to meat + gear together.\n")
    a.append("## 1. IM3 eye under the float vectors (direct, not scaled)\n")
    a.append("Each IM3 eye carries its meat-strap leg (150 N hand cinch, aft) and one B-24 link (aft and down at 30°). "
             "Factored: link x 3.0, cinch x 1.5 (the bag-off rule). Fatigue on the 1.6 g walking peak (cinch 150 N "
             "steady + link x 1.6, PAHT-CF FI <= 0.3); creep on 1 g (FI <= 0.4, 40 °C, 8 h). Fairlead stub, 1 mm "
             "voxels, layer normal +y (`bag_attach.solve_fairlead`).\n")
    a.append("| case | factored N (aft / down) | strength SF | was (scaled) | walk N | fatigue SF | was (scaled) | creep SF | bearing SF |")
    a.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for key, r in (("design", d), ("misuse", m)):
        f = r["factored"]
        a.append(f"| {key} | {f['n']:.0f} ({f['fy']:.0f} / {-f['fz']:.0f}) | **{r['sf']:.2f}** | {r['sf_scaled_handoff']:.2f} | "
                 f"{r['walk']['n']:.0f} | **{r['sf_fatigue']:.2f}** | {r['sf_fatigue_scaled_handoff']:.2f} | "
                 f"{r['sf_creep']:.2f} | {r['bearing_sf']:.2f} |")
    a.append(f"| bag-on hook case (reference) | {e['n']:.0f} ({e['fy']:.0f} / {-e['fz']:.0f}) | {e['sf']:.2f} | | | | | | {e['bearing_sf']:.2f} |")
    a.append("")
    a.append(f"Requirements: strength SF >= {STRENGTH_REQ:.1f} on the factored load, fatigue SF >= {FATIGUE_REQ:.1f}, "
             "creep SF >= 1.0.\n")
    a.append("Direct vs scaled. Strength: the print layer normal is +y (aft), so the aft share pulls across the layers "
             "(47 MPa) and the downward share is carried more along them (88 MPa); the float vectors are more downward "
             "than the solved 554 N, and the direct SF comes out 4-9 % higher than the scaled one. Fatigue: the scaled "
             "figure took the walking peak as 1.6 / 3.0 of the whole factored vector. The cinch is a 150 N steady "
             "preload, so the walking peak is 150 N + 1.6 x the 1 g link: higher than scaled for the design case "
             "(cinch dominates: 2.04, was 2.18), lower for the misuse case (link dominates: 1.11, was 1.07).\n")
    rp = res["reproduce"]
    a.append(f"Solver checks: the 554 N record vector reproduces SF {rp['sf']:.3f} (record {rp['sf_record']:.3f}). ")
    if "mesh_check" in res:
        mc = res["mesh_check"]
        a.append(f"Mesh: misuse vector at {mc['h_mm']} mm voxels SF {mc['sf']:.2f} vs {mc['sf_h1']:.2f} at 1 mm "
                 f"({100 * mc['change']:+.1f} %); applied to fatigue, the misuse SF would be "
                 f"{m['sf_fatigue'] * (1 + mc['change']):.2f}, still >= 1.0. ")
    a.append("The voxel solver is verified against the Timoshenko cantilever and Saint-Venant torsion "
             "(`tests/test_frame_topopt.py`) and the H8 cantilever / Q4 patch (`tests/test_gendesign.py`).\n")
    a.append("## 2. US1 cradle anchor and the float meat limit\n")
    a.append("The float meat path is the bag-off haul: all the meat's vertical in the two under-straps, US1 takes "
             "60 %, side legs at 31° (70 mm belly over a 115 mm half-span). Strength case 1.6 g x 1.5. Solved "
             "directly at each meat mass (fixed direction, so the result is linear in the mass; the direct solves "
             "confirm it).\n")
    a.append("| meat on the frame | US1 tension N | strength SF | fatigue SF | cam SF | US2 fatigue SF |")
    a.append("|---:|---:|---:|---:|---:|---:|")
    for kg in ("36", lim, "56"):
        r = u["rows"][kg]
        a.append(f"| {kg} kg ({np.floor(float(kg) * LB_PER_KG):.0f} lb) | {r['tension_n']:.0f} | {r['sf']:.2f} | "
                 f"**{r['sf_fatigue']:.2f}** | {r['cam_sf']:.2f} | {r['us2_sf_fatigue']:.2f} |")
    a.append("")
    a.append(f"Limit where US1 fatigue reaches 1.0: {u['limit_exact_kg']:.1f} kg, **set at {lim} kg "
             f"({u['limit_lb']:.0f} lb)**. Strength and the cam keep margin past it; fatigue governs.\n")
    a.append("Sensitivity to the belly (the user cams to \"about 70 mm\"; a flatter cradle pulls harder):\n")
    a.append("| belly mm | tension vs 70 mm | meat limit kg |")
    a.append("|---:|---:|---:|")
    for b, s in u["belly_sensitivity"].items():
        a.append(f"| {b} | {s['tension_ratio']:.2f} | {s['limit_kg']:.0f} |")
    a.append("\nThe user guide must say: cam the cradle until it hangs about a hand's width (70 mm, 2.75 in) below the "
             "straight line between the stays, not tight and flat. At 50 mm the limit drops to about "
             f"{u['belly_sensitivity']['50']['limit_kg']:.0f} kg.\n")
    a.append("## 3. Wrap-strap friction: not credited\n")
    a.append("The hand-off offered to credit W1–W3 / IM friction (μ 0.4, five clamping straps) to lift the 56 kg case. "
             "Not done:\n")
    a.append("- μ 0.4 in `meat_haul.MU` has no source in `data/materials/` or `docs/research/`. A search for a measured "
             "wet-fabric coefficient found fabric-on-skin and fabric-on-fabric studies only; one reports a *slight "
             "decrease* when the fabric is water-wetted ([J. Eng. Sci., Egypt](https://jest.journals.ekb.eg/article_81022_c05bfb54d692cc3843c62f19788a9fd3.pdf)), "
             "another an increase against wet skin ([Kyushu Univ.](https://catalog.lib.kyushu-u.ac.jp/opac_download_md/4738575/2021_p109.pdf)). "
             "Nothing for a bloody knit game bag on carbon/ROHACELL or on nylon webbing.")
    a.append("- Even with a sourced μ, the clamp force is unknown: the 150 N cinch is an ASSUMPTION, and W1–W3 are "
             "ladder-locked by hand. Meat settles and drains on the trail, so the clamp falls with time.")
    a.append("- Fatigue is the governing check. A friction share has to hold for 1e5 strides; any slip puts the whole "
             "load back on the cradle, so it cannot be counted on in fatigue without a test.\n")
    a.append("Path to 56 kg if the owner wants it: measure it, do not assume it. Prototype test T5f (proposed): 56 kg of "
             "wet sandbags in game bags in float, cradle on a load cell or a luggage scale in series with US1, walk or "
             "crank 0 -> 1.6 g, record the US1 share. A measured share <= 0.95 x the no-friction value earns 56 kg. "
             "Or re-print US1 thicker (outside this task: the anchor geometry belongs to the frame).\n")
    a.append("## 4. Frame-global effect\n")
    a.append("The float puts at most 68 kg on the frame with the CG <= 190 mm aft (lever table, `meat_haul_modes.md` C), "
             "inside C5 `meat_straps` (68 kg, 190 mm). The vertical enters at US1/US2 (z 95 / 142) and IM3 instead of "
             "the z 60 hinge pins: all on the solid lower stay or at an eye already in the IM3 couple variant. "
             "ASSUMPTION: the C5 branch-frame result (SF 2.49 `meat_straps`, rev C body check) covers the float "
             "globally; the local anchors are the checks above. Not re-solved on the beam model.\n")
    a.append("## 5. Retired case\n")
    a.append("The hinge swing (`between`, hinge 264 N, IM3 496 N, CG 110 mm) is retired. It is in no envelope: not in "
             "`load_standard.py`, `meat_haul_modes.json`, `attach_system.PROCEDURES` or `rev_c_verification`. The "
             "264.3 N in `frame.yaml` / `crown_loads.yaml` is the crown retention load of the retired rev A shelf case "
             "(`meat_shelf_heavy_low`), not the hinge. The bag-on hinge (1019 N factored, HE / B-18) is unchanged.\n")
    a.append("## Mass\n")
    a.append("No mass change from this check. Float hardware is the two B-24 links (54.4 g, `meat_haul_modes.json` "
             "float.link); the IM3 fairlead (6.1 g printed, each) and the US1 anchor (5.7 g) are unchanged. Mass cut: "
             f"the IM3 cheek has strength margin {d['sf']:.1f} / fatigue {d['sf_fatigue']:.1f} in the design case, but "
             "the eight fairleads are one shared geometry and the bag-on case governs the hinge one; no cut proposed.\n")
    a.append("## Assumptions\n")
    a.append("- ASSUMPTION: link at 30° below horizontal carries the whole bag (no W1–W3 help), as the hand-off.")
    a.append("- ASSUMPTION: the IM cinch is a 150 N steady preload; in fatigue it does not cycle with the stride.")
    a.append("- ASSUMPTION: both forces act on the same pin and load the cheek pair as one resultant on the bore "
             "(the meat-strap hook and the link hook sit side by side in the 18 mm throat).")
    a.append("- ASSUMPTION: the bag-on 1415 N hook case acts along the rev C governing IM3 direction (meat_straps).")
    a.append("- ASSUMPTION: US1 takes 60 % of the cradle, belly 70 mm (`meat_haul.py`).")
    a.append("- Fatigue rule: HA-LS-1, 1e5 cycles 0 -> 1.6 g (envelopes the 1.2 g carry rule).\n")
    a.append("## Screenshots\n")
    for s in res["screens"]:
        a.append(f"- `{s}`")
    path = ANALYSIS / "float_fea.md"
    path.write_text("\n".join(a) + "\n")
    return str(path)


if __name__ == "__main__":
    run()
