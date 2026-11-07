"""Pack 5200 v3.1: build-simplicity audit (manufacturing-engineer, 2026-11-07).

Counts the build (pieces, materials, hardware SKUs, stitch types, box-X / bar tacks, binding runs,
special operations) and estimates beginner build hours by subassembly, before and after the proposed
simplifications in ``analysis/build_simplicity.md``. Proposal only: nothing here changes geometry,
patterns or YAML.

    python designs/pack_5200/build_simplicity.py      # writes analysis/build_simplicity_results.json + 2 PNGs

Sources: outputs/release/pack5200_v3.1_patterns/cutlist.csv (pieces, perimeters, binding lengths),
cut/attachment/README.md + analysis/bag_attachment.md section 5 (attachment parts, box-X counts),
panels.yaml webbing_cut_list, geometry.yaml weight rows. Minutes per operation are ASSUMPTIONs
(beginner, first build, including marking and setup), listed in OP_MIN.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
CUTLIST = ROOT / "outputs/release/pack5200_v3.1_patterns/cutlist.csv"
OUT_JSON = HERE / "analysis" / "build_simplicity_results.json"
SCREENS = ROOT / "outputs" / "screens"

# ASSUMPTION: beginner minutes per operation unit (first build, incl. marking, clipping, setup, inspection).
# Calibrated so the base build lands in the 10-14 week evenings/weekends plan of BUILD_PLAN.md.
OP_MIN = {
    "cut_hand": 6.0,       # per fabric piece: trace paper template, rotary cut, notch, label L/R + face
    "cut_check": 1.5,      # per laser/die/waterjet part bought in: check against the DXF, label
    "web_cut": 3.0,        # per webbing part: measure, hot-knife, mark box-X lines, label
    "boxx": 8.0,           # per box-X load joint (mark from template, change to tex 135, sew, inspect)
    "bar": 4.0,            # per bar tack / small fray-stop tack
    "patch2": 12.0,        # per Hypalon patch, double-row perimeter
    "patch1": 8.0,         # per Hypalon patch or tab, single-row perimeter
    "seam_flat_m": 15.0,   # per metre of flat 301 seam
    "seam_curve_m": 35.0,  # per metre of 3D curved seam with notch matching every 50 mm
    "swell": 60.0,         # per fairlead swell: open window, set 2 cone caps, port, topstitch
    "zip_diag": 150.0,     # the 509 mm diagonal #10 zip on a 39 deg seam with storm strip B-08
    "zip_small": 45.0,     # per small pocket zip
    "bind_m": 30.0,        # per metre of 20 mm binding (fold, clip, 2 passes, corners)
    "hem_m": 20.0,         # per metre of folded hem / channel
    "overlay_m": 30.0,     # per metre of shard perimeter (turn edge, topstitch)
    "foam_assy": 45.0,     # per foam sandwich (strap, wing, pad): glue-stick, align, perimeter
    "hw": 2.0,             # per hardware item threaded or fitted
    "grommet": 5.0,
    "proof": 45.0,         # per proof-test type (rig setup, 5 samples, record)
    "thread_change": 5.0,  # per thread / needle / bobbin change
    "misc_min": 1.0,       # explicit minutes
}
REWORK = 0.20        # ASSUMPTION: unpicking + re-sewing on a first build (forum reports, see md)
REWORK_JIG = 0.12    # ASSUMPTION: with the jig + template kit (S-10) on jig-covered subassemblies
COMPOSITE_H = 8.0    # ASSUMPTION: owner time to lay up, vacuum-bag, cure, CNC-route and fit the BP-06 sandwich

ACCESSORY = {"R-01", "R-02", "L-01", "L-02", "L-03", "F-03"}
LASER_MATS = {"hypalon_coated_nylon", "hdpe_sheet", "eva_foam_30c", "eva_foam_45c", "eva_foam_perforated", "xlpe_foam"}
ATTACH_LASER = {"B-17": 2, "B-18": 2, "B-19": 1, "B-19s": 1, "B-19L": 1, "B-20": 2, "B-22": 2, "B-23": 2}
OTHER_BOUGHT = {"BP-08": 2, "BP-06": 1}   # waterjet carbon backers, composite spreader
# webbing parts: panels.yaml webbing_cut_list + patterns_v31 cut list + cut/attachment/README.md
WEBBING_PARTS = {"W1-W3": 3, "hipbelt strap": 1, "load lifters": 2, "IM1-IM3": 3, "roll-top clips": 2, "keeper loops": 6,
                 "hip stabilizers": 2, "sternum": 2, "crown pulley": 1, "fairlead eyes": 8, "T2/T3 tongues": 4,
                 "hinge eyes HE": 2, "under-straps US1/US2": 2, "lifter keeper tails": 2, "HT tongues": 2, "TG guys": 2,
                 "LLT tabs": 2, "GT grab tab": 1, "B-24 links": 2, "bow riser loops + strap": 3}
BINDING_M = {"hipbelt wings": 1.159, "lumbar pad": 0.420, "shoulder straps": 2.122, "back panel mesh": 1.628,
             "main-bag inside seams": 3.958}    # cutlist.md 'binding' rows


def pieces():
    rows = [r for r in csv.DictReader(CUTLIST.open()) if r["piece_id"] not in ACCESSORY and r["size"] in ("", "M", "J")]
    hand = sum(int(r["qty"]) for r in rows if r["material"] not in LASER_MATS)
    laser = sum(int(r["qty"]) for r in rows if r["material"] in LASER_MATS)
    ids = {r["piece_id"] for r in rows}
    mats = sorted({r["material"] for r in rows} | {"cfrp_t300_3k_woven_epoxy_ply", "rohacell_110_igf"})
    sas = sorted({v.split("=")[-1] for r in rows for v in r["seam_allowance_mm"].split("; ")}, key=float)
    return {"hand_cut": hand, "laser_die_cutlist": laser, "attach_laser": sum(ATTACH_LASER.values()),
            "bought_composite": sum(OTHER_BOUGHT.values()),
            "total": hand + laser + sum(ATTACH_LASER.values()) + sum(OTHER_BOUGHT.values()),
            "piece_types": len(ids) + len(ATTACH_LASER) + len(OTHER_BOUGHT),
            "webbing_parts": sum(WEBBING_PARTS.values()), "materials": mats, "seam_allowances_mm": sas}


def ops(after: bool):
    """Operation lines (subassembly, op, qty). after=True applies the recommended + owner-OK set."""
    P = pieces()
    hand_cut = P["hand_cut"] - (10 if after else 0)          # S-03: 10 body panels laser-cut (bought service)
    bought = P["laser_die_cutlist"] + P["attach_laser"] + 2 + (10 if after else 0)
    L = [
        ("Cutting + kitting", "cut_hand", hand_cut), ("Cutting + kitting", "cut_check", bought),
        ("Cutting + kitting", "web_cut", P["webbing_parts"]),
        # off-bag webbing parts: IM 6, US 2, B-24 8, fairlead eyes 8, wraps 6, roll clips 2, pulley 1, bow riser 3
        ("Webbing + load parts", "boxx", 36), ("Webbing + load parts", "hw", 6 + 3 + 2 + 2 + 2 + 6 + 2 + 1 + 1),
        ("Webbing + load parts", "thread_change", 2),
        # B-01 / face / gore flat-work (bag_attachment.md section 5, patterns_v31 drill marks)
        ("Bag flat-work", "swell", 8), ("Bag flat-work", "bar", 12 + 2 + 4 + 6 + 2 + 2),   # ports, HE necks, B-20 ends, keepers, roll clips, hose ports
        ("Bag flat-work", "patch1", 6 + 2 + 8), ("Bag flat-work", "patch2", 2 + 2 + 2 + 2),  # B-12, B-23, B-11 / B-17, B-18, B-20, B-22
        ("Bag flat-work", "boxx", 4 + 4 + 2 + 2), ("Bag flat-work", "seam_flat_m", 1.31 + 0.6 + 2 * 0.58),
        ("Bag flat-work", "bind_m", 0.0 if after else 1.162),                       # SH-02 bias binding (S-13: grosgrain)
        ("Bag flat-work", "hem_m", 1.162 if after else 0.0),
        ("Bag flat-work", "overlay_m", 0.618 + 2 * 0.582), ("Bag flat-work", "zip_diag", 1), ("Bag flat-work", "grommet", 2),
        ("Bag flat-work", "thread_change", 6 if not after else 3),
        ("Bag 3D assembly", "seam_curve_m", 0.9 + 0.8 + 4 * 0.765 + 0.873 + 1.2), ("Bag 3D assembly", "seam_flat_m", 0.5 + 0.3),
        ("Bag 3D assembly", "hem_m", 1.17), ("Bag 3D assembly", "overlay_m", 0.0 if after else 1.29),  # S-12 camo hem
        ("Bag 3D assembly", "bind_m", 0.0 if after else BINDING_M["main-bag inside seams"]),
        ("Bag 3D assembly", "seam_flat_m", BINDING_M["main-bag inside seams"] if after else 0.0),     # S-03 2nd row
        ("Bag 3D assembly", "thread_change", 4 if not after else 2),
        ("Side pockets", "hem_m", 2 * 0.17), ("Side pockets", "seam_curve_m", 2 * 0.75), ("Side pockets", "seam_flat_m", 2 * (0.75 + 0.55)),
        ("Side pockets", "grommet", 2),
        ("Rain fly + pocket", "seam_curve_m", 2.7), ("Rain fly + pocket", "hem_m", 3.0), ("Rain fly + pocket", "zip_small", 1),
        ("Rain fly + pocket", "seam_flat_m", 1.1), ("Rain fly + pocket", "boxx", 1), ("Rain fly + pocket", "thread_change", 2),
        ("Crown hood", "hem_m", 0.15), ("Crown hood", "misc_min", 30), ("Crown hood", "boxx", 7), ("Crown hood", "hw", 6),
        ("Hipbelt (M)", "foam_assy", 3), ("Hipbelt (M)", "overlay_m", 0.8), ("Hipbelt (M)", "zip_small", 2),
        ("Hipbelt (M)", "seam_curve_m", 1.66), ("Hipbelt (M)", "hw", 4 + 1 + 2), ("Hipbelt (M)", "boxx", 6),
        ("Hipbelt (M)", "seam_flat_m", 0.55), ("Hipbelt (M)", "bind_m", BINDING_M["hipbelt wings"] + BINDING_M["lumbar pad"]),
        ("Hipbelt (M)", "thread_change", 2),
        # S-04 (turned straps, no binding) is REJECTED in the md: the model gives no hour saving
        ("Harness (J)", "foam_assy", 2), ("Harness (J)", "bind_m", BINDING_M["shoulder straps"]),
        ("Harness (J)", "seam_flat_m", 0.24 + 0.77), ("Harness (J)", "boxx", 6),
        ("Harness (J)", "hw", 4 + 2 + 1 + 2), ("Harness (J)", "misc_min", 15), ("Harness (J)", "thread_change", 2),
        ("Back panel", "seam_flat_m", 2 * 0.96 + 0.79), ("Back panel", "bind_m", BINDING_M["back panel mesh"]),
        ("Back panel", "foam_assy", 1), ("Back panel", "bar", 4),
        ("Proof tests + fit", "proof", 8 if after else 9), ("Proof tests + fit", "misc_min", 240),
    ]
    return L


JIG_SUBS = {"Webbing + load parts", "Bag flat-work", "Crown hood", "Hipbelt (M)", "Harness (J)"}


def hours(after: bool):
    by = {}
    for sub, op, q in ops(after):
        by[sub] = by.get(sub, 0.0) + q * OP_MIN[op]
    for sub in by:
        if sub == "Proof tests + fit":
            if after:   # S-14: one fixture, one session: 25 min per test + 60 min setup instead of 45 min each
                n = 8
                by[sub] = by[sub] - n * OP_MIN["proof"] + n * 25 + 60
            continue
        r = REWORK_JIG if (after and sub in JIG_SUBS) else REWORK
        by[sub] *= 1 + r
    by["Composite parts (spreader)"] = 30.0 if after else COMPOSITE_H * 60   # S-05: outsource, owner inspects/fits
    if after:
        by["Jig + template kit (S-10)"] = 120.0
    return {k: round(v / 60, 2) for k, v in by.items()}


def counts():
    L = ops(False)
    s = lambda op: sum(q for _, o, q in L if o == op)
    return {"boxx_load_joints": s("boxx"), "bar_tacks_304": s("bar"), "binding_runs": len(BINDING_M) + 1,
            "binding_m": round(sum(BINDING_M.values()) + 1.162, 2), "swells": 8, "zips": 4,
            "curved_seam_m": round(s("seam_curve_m"), 2), "overlay_m": round(s("overlay_m"), 2),
            "hot_cut_webbing_ends": 2 * pieces()["webbing_parts"]}


# hardware SKUs (soft goods), before -> after
HW_BEFORE = {
    "buckles": ["50 mm side-release (HIP)", "25 mm side-release (ROLL)", "25 mm Fidlock (QUICK)"],
    "adjusters": ["25 mm ladder lock", "25 mm tri-glide", "38 mm tri-glide", "25 mm metal cam (pulley)", "38 mm metal cam (IM + US)"],
    "hooks": ["25 mm Al G-hook", "38 mm sliding-gate hook 1500 N (meat)", "38 mm rated hook >= 2200 N (bag + B-24)"],
    "toggles + small parts": ["POM toggle 30x8x5 (hood)", "pawl-release strap toggle", "POM sternum rail", "TPU hook sleeve",
                              "8 mm grommet", "elastic keeper", "Dyneema pull loop"],
    "zips": ["#10 coil + 2 sliders", "#8 coil + slider", "#5 coil + slider"],
    "elastic + cord": ["3 mm shock cord (pockets)", "flat elastic (fly hem)"],
    "webbing + binding": ["25 mm poly black", "25 mm poly coyote (HAUL)", "38 mm poly bone (MEAT)", "38 mm poly other parts",
                          "50 mm nylon", "20 mm grosgrain binding"],
    "thread": ["bonded nylon tex 90", "bonded nylon tex 135", "bonded poly tex 90"],
}
HW_REMOVED = {"38 mm sliding-gate hook 1500 N (meat)", "pawl-release strap toggle", "#5 coil + slider",
              "38 mm poly other parts", "bonded poly tex 90"}


def hw_counts():
    return {fam: {"before": len(v), "after": len([x for x in v if x not in HW_REMOVED])} for fam, v in HW_BEFORE.items()}


def charts(hb, ha, hw):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BEFORE, AFTER, INK, MUTED, SURF = "#8a8984", "#2a78d6", "#0b0b0b", "#52514e", "#fcfcfb"
    SCREENS.mkdir(parents=True, exist_ok=True)
    subs = sorted(set(hb) | set(ha), key=lambda s: -max(hb.get(s, 0), ha.get(s, 0)))
    fig, ax = plt.subplots(figsize=(7.2, 8.0), dpi=110, facecolor=SURF)
    ax.set_facecolor(SURF)
    y = range(len(subs))
    h = 0.38
    b1 = ax.barh([i - h / 2 for i in y], [hb.get(s, 0) for s in subs], h, color=BEFORE, label=f"now  {sum(hb.values()):.0f} h")
    b2 = ax.barh([i + h / 2 for i in y], [ha.get(s, 0) for s in subs], h, color=AFTER, label=f"after  {sum(ha.values()):.0f} h")
    for bars in (b1, b2):
        for r in bars:
            w = r.get_width()
            if w > 0:
                ax.text(w + 0.2, r.get_y() + r.get_height() / 2, f"{w:.1f}", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(list(y), subs, fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("beginner hours (ASSUMPTION model)", fontsize=9, color=MUTED)
    ax.set_title("Pack 5200 build hours by subassembly\nnow vs after the recommended simplifications", fontsize=11,
                 color=INK, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="x", color="#e4e3df", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.text(0.01, 0.01, "Excludes frame printing (27 h unattended). Source: designs/pack_5200/build_simplicity.py",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p1 = SCREENS / "20261107_buildsimp_1.png"
    fig.savefig(p1, facecolor=SURF)
    plt.close(fig)

    fams = list(hw)
    fig, ax = plt.subplots(figsize=(7.2, 6.0), dpi=110, facecolor=SURF)
    ax.set_facecolor(SURF)
    y = range(len(fams))
    b1 = ax.barh([i - h / 2 for i in y], [hw[f]["before"] for f in fams], h, color=BEFORE,
                 label=f"now  {sum(v['before'] for v in hw.values())} SKUs")
    b2 = ax.barh([i + h / 2 for i in y], [hw[f]["after"] for f in fams], h, color=AFTER,
                 label=f"after  {sum(v['after'] for v in hw.values())} SKUs")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_width() + 0.08, r.get_y() + r.get_height() / 2, f"{int(r.get_width())}", va="center",
                    fontsize=8, color=MUTED)
    ax.set_yticks(list(y), fams, fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("distinct SKUs to buy (soft goods; frame hardware excluded)", fontsize=9, color=MUTED)
    ax.set_title("Hardware / webbing / thread SKU consolidation\n(one hook part, #8 for every pocket zip, one 38 mm colour, 2 threads)",
                 fontsize=10.5, color=INK, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="x", color="#e4e3df", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    p2 = SCREENS / "20261107_buildsimp_2.png"
    fig.savefig(p2, facecolor=SURF)
    plt.close(fig)
    return [str(p1.relative_to(ROOT)), str(p2.relative_to(ROOT))]


def main():
    hb, ha = hours(False), hours(True)
    hw = hw_counts()
    res = {"pieces": pieces(), "counts": counts(), "hours_before": hb, "hours_after": ha,
           "total_before_h": round(sum(hb.values()), 1), "total_after_h": round(sum(ha.values()), 1),
           "hardware_skus": hw, "op_minutes_ASSUMPTION": OP_MIN, "rework": [REWORK, REWORK_JIG],
           "screens": charts(hb, ha, hw)}
    OUT_JSON.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "op_minutes_ASSUMPTION"}, indent=1))


if __name__ == "__main__":
    main()
