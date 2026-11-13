"""Pack 5200: bag-side weight-cut plan (pack-designer, 2026-11-05).

HISTORICAL (BL-036, 2026-11-13): the 2026-11-05 plan on the CORRIE B.2 / v3.1 bag, kept as the record of that day.
Its MISSING hardware masses are that day's ASSUMPTIONs (e.g. the 25 mm cam 12.0 g; the cam_25mm_al record is now
12.2 g, strap_arch.CAM25_G 13.2 g with the pull tab). Current masses come from huntkit/mass/ledger.py and
weight_rollup_v2. weight_pass_corrie still imports MISSING / usd_m2 from here (fabric prices only, not the cam).

Every gram below is computed from the design bill of panels (build_geometry.build()), the material records in
data/materials/, the analysis records, or a line tagged ASSUMPTION (missing material records are listed).

    python designs/pack_5200/bag_weight_plan.py

Writes designs/pack_5200/analysis/bag_weight_plan.md, analysis/bag_weight_plan.json and
outputs/screens/20261105_bag_3.png (weight budget), outputs/screens/20261105_bag_4.png (ranked savings).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import build_geometry as BG  # noqa: E402
from huntkit import materials as MAT  # noqa: E402

HISTORICAL_NOTE = '**HISTORICAL (BL-036, 2026-11-13).** This is the 2026-11-05 plan on the CORRIE B.2 / v3.1 bag. Its hardware masses are the ASSUMPTIONs of that day (25 mm cam 12.0 g: the `cam_25mm_al` record is now 12.2 g, 13.2 g with the glove pull tab in `strap_arch.CAM25_G`). Current masses: `huntkit/mass/ledger.py`, `designs/pack_5200/analysis/weight_rollup_v2.md` and `corrie_f_body.md`. Not re-run since; do not cite its numbers as current.'
ANALYSIS = HERE / "analysis"
SCREENS = ROOT / "outputs" / "screens"
CUTLIST = ROOT / "outputs" / "release" / "pack5200_v3.1_patterns" / "cutlist.csv"
THREAD = 0.03                      # build_geometry misc row: thread = 3 % of soft goods (ASSUMPTION there)
YD = 0.9144

# ASSUMPTION: fabrics that have no record in data/materials/ yet (materials-engineer to add them). Values are
# typical supplier-listing figures, not sourced records, and are used only to size an owner choice.
MISSING = {
    "nylon_ripstop_70d": {"gsm": 70, "tear_n": 35, "usd_m2": 13.0,
                          "why": "70D nylon ripstop (PU), collar option. ASSUMPTION ~2.0 oz/yd2 class"},
    "silpoly_20d": {"gsm": 37, "tear_n": 15, "usd_m2": 9.0,
                    "why": "20D silpoly (1.1 oz/yd2 class), lighter fly. ASSUMPTION"},
    "polyester_300d_printable": {"gsm": 170, "tear_n": 70, "usd_m2": 12.0,
                                 "why": "300D printable polyester for the camo shards. ASSUMPTION"},
    # HISTORICAL (BL-036): 12.0 g was the 2026-11-05 ASSUMPTION; the cam_25mm_al record (BL-034) is 12.2 g. Kept so
    # the historical plan reproduces; not used by the current ledger (strap_arch.CAM25_G reads the record).
    "cam_buckle_25mm_al": {"mass_g": 12.0, "why": "25 mm metal cam (same as the torso-adjust cam ASSUMPTION)"},
    "hook_sliding_gate_25mm_al": {"mass_g": 5.0, "why": "25 mm sliding-gate hook. ASSUMPTION"},
    "slider_coil_8": {"mass_g": 4.0, "why": "#8 coil slider. ASSUMPTION (the #10 slider is a 6 g ASSUMPTION)"},
    "ultragrid abrasion": {"why": "ultragrid_210d_uhmwpe_ripstop has no abrasion property; needed before O-4"},
}


def usd_m2(mid: str) -> float:
    m = MAT.load(mid)
    c = m.cost_usd or {}
    if c.get("per") == "m2":
        return float(c["value"])
    if c.get("per") == "yd":
        w = float(m.props.get("roll_width_mm", 1500.0)) / 1000.0     # ASSUMPTION 1.5 m when no roll width
        return float(c["value"]) / (YD * w)
    return float("nan")


def gsm(mid: str) -> float:
    return float(MISSING[mid]["gsm"]) if mid in MISSING else float(MAT.load(mid).require("areal_density_gsm"))


def cost_m2(mid: str) -> float:
    return float(MISSING[mid]["usd_m2"]) if mid in MISSING else usd_m2(mid)


def tear(mid: str):
    return MISSING[mid]["tear_n"] if mid in MISSING else MAT.load(mid).props.get("tear_warp_n")


def build():
    geom, pan, ctx = BG.build()
    P = {r["piece"].piece_id: r for r in ctx["P"]}
    return geom, pan, ctx, P


def area(P, pid):
    r = P[pid]
    return r["piece"].area_mm2 / 1e6 * r["piece"].quantity      # cut-line area, all copies


def swap(P, pids, new):
    """(grams saved incl. thread, $ per pack, area) for re-cutting pieces in another fabric."""
    g = c = a_tot = 0.0
    for pid in pids:
        a = area(P, pid)
        old = P[pid]["piece"].material_id
        g += a * (gsm(old) - gsm(new))
        c += a * (cost_m2(new) - cost_m2(old))
        a_tot += a
    return g * (1 + THREAD), c, a_tot


def items(geom, ctx, P):
    w = {r["item"]: r["mass_g"] for r in geom["weight"]["rows"]}
    mh = geom["meat_harness"]
    straps = {s["id"]: s for s in mh["straps"]}
    web38 = MAT.load("poly_webbing_38mm").require("mass_g_m")
    web25 = MAT.load("poly_webbing_25mm").require("mass_g_m")
    port_g = BG.piece_mass(P["B-12"]) / 6
    out = []

    def add(**k):
        k.setdefault("pattern_regen", "none")
        out.append(k)

    # ---------------------------------------------------------------- applied (no owner choice)
    b10 = BG.rect_panel("frame-link tab", 50.0, 70.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon",
                        piece_id="B-10", quantity=6)
    b10_g = b10.area_mm2 / 1e6 * 6 * gsm("hypalon_coated_nylon")
    add(id="W-01", zone="reinforcement", title="Retire the B-10 frame-link tabs (6 Hypalon 50 x 70)",
        g=b10_g * (1 + THREAD), usd=-b10.area_mm2 / 1e6 * 6 * usd_m2("hypalon_coated_nylon"),
        durability="none: the bag hangs on the eight fairleads; the toggles these tabs took were removed in PR #3",
        source="analysis/bag_attachment.md (LINK hardware removed); patterns_v31.py note 'B-10 tabs retired'",
        status="applied", rec="applied in build_geometry.py", pattern_regen="none (the v3.1 patterns already omit B-10)")
    # ---------------------------------------------------------------- owner choices
    im1 = straps["IM1"]
    g_im1 = im1["cut_length_mm"] / 1000 * web38 + 2 * BG.MEAT_HOOK_G + BG.MEAT_CAM_G + 2 * port_g
    add(id="O-1", zone="feature count", title="Meat straps 3 -> 2 (drop IM1, keep its fairlead eyes)",
        g=g_im1 + 2 * port_g * THREAD, usd=-(im1["cut_length_mm"] / 1000 * 1.0 + 2 * 3 + 6),
        durability=("bag-off quarter loses its lowest clamp: friction hold drops from 5 to 4 straps and the hock can no "
                    "longer hook over IM1; bag-on loads move to IM2/IM3 (IM3 hook already the heaviest, SF 2.71)"),
        source="geometry.yaml meat_harness (IM1 cut length, hook 9 g / cam 22 g ASSUMPTION; hook $3, cam $6 ASSUMPTION); meat_haul_modes.md; DESIGN Q2",
        status="owner", rec="NO. Packing meat out is the primary mission; IM1 is the low clamp in bag-off. Keep 3.",
        pattern_regen="B-01: delete the 2 IM1 ports (B-12 x2)")
    L = sum(s["cut_length_mm"] for s in mh["straps"]) / 1000
    g_25 = L * (web38 - web25) + 3 * (BG.MEAT_CAM_G - MISSING["cam_buckle_25mm_al"]["mass_g"]) \
        + 6 * (BG.MEAT_HOOK_G - MISSING["hook_sliding_gate_25mm_al"]["mass_g"])
    add(id="O-2", zone="hardware", title="Meat straps 38 mm -> 25 mm (webbing, cams, hooks)",
        g=g_25, usd=-L * 0.3,
        durability=("25 mm bites game bags and the 25 mm cam/buckle ratings were already too low for the cradle "
                    "(meat_haul_modes.md); breaks the one-width MEAT family (R-25)"),
        source="poly_webbing_25/38mm records; 25 mm cam 12 g and hook 5 g ASSUMPTION (no records)",
        status="owner", rec="NO. Load rating and glove use beat 80 g.")
    g, c, a = swap(P, ["B-06"], "nylon_ripstop_70d")
    g40, c40, _ = swap(P, ["B-06"], "silicone_coated_poly_ripstop_40d")
    add(id="O-3", zone="fabric: collar", title="Roll-top collar B-06 100D Robic -> 70D ripstop (40D silpoly shown for scale)",
        g=g, usd=c, alt=f"40D silpoly: -{g40:.1f} g",
        durability=(f"tear {tear('robic_100d_ripstop')} -> {tear('nylon_ripstop_70d')} N (40D: {tear('silicone_coated_poly_ripstop_40d')} N). "
                    "The collar carries an over-stuffed load and the roll; silpoly is too slick to hold a roll"),
        source="robic_100d_ripstop record; 70D ripstop ASSUMPTION (no record); B-06 cut area from panels.yaml",
        status="owner", rec="YES to 70D once the materials-engineer adds a record with a real tear value; NO to 40D silpoly.",
        pattern_regen="B-06 material id only (marker re-nest at the 70D roll width)")
    g, c, a = swap(P, ["B-02a", "B-02b", "B-03", "B-07", "B-08"], "ultragrid_210d_uhmwpe_ripstop")
    add(id="O-4", zone="fabric: body", title="Body face, side gores, hem, storm strip 330D Cordura -> 210D UHMWPE grid",
        g=g, usd=c,
        durability=(f"tear {tear('cordura_330d_nylon66')} -> {tear('ultragrid_210d_uhmwpe_ripstop')} N (2x); abrasion of "
                    "the grid fabric is not in its record; visible grid lines change the solid-colour look; same quietness (3)"),
        source="cordura_330d_nylon66 and ultragrid_210d_uhmwpe_ripstop records; Exo users report thin pocket fabric "
               "tearing on rock (docs/research/pack_market_2026.md 3.2)",
        status="owner", rec="YES if a supplier abrasion figure is >= the 330D (800 Taber cycles) and the owner likes the swatch.",
        pattern_regen="B-02a/b/c/d, B-03, B-07, B-08 material id; re-nest markers")
    g, c, a = swap(P, ["B-05"], "challenge_ultra_200")
    add(id="O-5", zone="fabric: bottom", title="Bag bottom B-05 500D Cordura -> Challenge ULTRA 200 (B-01 fabric)",
        g=g, usd=c,
        durability=(f"better: Taber 1500 -> 2000, tear {tear('cordura_500d_nylon66')} -> {tear('challenge_ultra_200')} N, "
                    "waterproof floor (blood/wet ground); louder (quietness 2) but the floor is not brushed; stock colours only"),
        source="cordura_500d_nylon66, challenge_ultra_200 records; Seek Outside Unaweep in ULTRA 200X (research 3.6)",
        status="owner", rec="YES. A durability gain that also saves grams; pick the closest stock ULTRA colour (black/coyote).",
        pattern_regen="B-05 material id (and B-16 floor channels stay 500D)")
    shards = ["SH-02", "SH-03", "SH-04"]
    g, c, a = swap(P, shards, "polyester_300d_printable")
    add(id="O-6", zone="reinforcement / accents", title="Camo shards SH-02..04 on a 300D printable base (SH-01 corner stays 630D)",
        g=g, usd=c,
        durability=("SH-02/03/04 are trim on low-wear spots; SH-01 wraps the bottom corner and stays the abrasion "
                    "doubler (DECISIONS: accents as functional reinforcement)"),
        source="polyester_ht_630d_printable record; 300D printable ASSUMPTION (no record)",
        status="owner", rec="YES, after a print test on the 300D base (camo-designer colour match).",
        pattern_regen="SH-02, SH-03, SH-04 material id")
    g, c, a = swap(P, ["F-01"], "silpoly_20d")
    add(id="O-7", zone="rain fly", title="Rain fly F-01 40D -> 20D silpoly",
        g=g, usd=c,
        durability=f"tear {tear('silicone_coated_poly_ripstop_40d')} -> {tear('silpoly_20d')} N; the fly is also the brush cover in rain",
        source="silicone_coated_poly_ripstop_40d record; 20D silpoly ASSUMPTION (no record)",
        status="owner", rec="NO. 10 g does not pay for a fly that snags open on the first deadfall.",
        pattern_regen="F-01a/b/c material id")
    fly_pocket = BG.piece_mass(P["F-02"]) + MAT.load("coil_zipper_5").require("mass_g_m") * 0.18 + 3
    add(id="O-8", zone="rain fly", title="Fly integration: stow the fly in the SPINE band, delete fly pocket F-02 + #5 zip",
        g=fly_pocket * (1 + THREAD), usd=-(area(P, "F-02") * cost_m2("cordura_330d_nylon66") + 0.18 * 2.0 + 0.5),
        durability="the fly no longer deploys from the bottom without unpacking; the band then holds fly + bow/poles",
        source="F-02 piece, coil_zipper_5 record; research P7 (stowable fly in a base pocket is the users' wish)",
        status="owner", rec="NO. The base-pocket fly is a researched answer to P7.",
        pattern_regen="delete F-02; D-01 unchanged")
    fly_g = sum(v for k, v in w.items() if k.startswith("fly"))
    face_g, face_c, _ = swap(P, ["B-02a", "B-02b", "B-03"], "challenge_ultra_200")
    tape = 6.0 * 3.0                       # ASSUMPTION: 6 m of seam tape at 3 g/m (no record)
    add(id="O-9", zone="rain fly", title="Delete the fly: waterproof body (ULTRA 200 face + gores, taped seams)",
        g=fly_g + face_g - tape, usd=face_c + 8.0,
        durability=("ULTRA's film backing is louder (quietness 2, R-13 quiet requirement), UHMWPE takes camo print poorly "
                    "(record ir_notes), taped seams in a 3D teardrop are hard for a first-time builder"),
        source="fly rows in geometry.yaml weight; challenge_ultra_200 record; seam tape 3 g/m ASSUMPTION; owner: fly counts in base",
        status="owner", rec="NO. Quiet hunting and the owner's camo direction win; keep the fly.",
        pattern_regen="all face/gore pieces and the fly set")
    g, c, a = swap(P, ["P-02"], "robic_100d_ripstop")
    add(id="O-10", zone="pockets", title="Side-pocket gussets P-02 210D grid -> 100D Robic",
        g=g, usd=c,
        durability=f"tear {tear('ultragrid_210d_uhmwpe_ripstop')} -> {tear('robic_100d_ripstop')} N on the brush-facing gusset",
        source="records; research 3.2 'thin pocket fabric tears on rock' (Exo)",
        status="owner", rec="NO. This is the pain point we were built to fix.", pattern_regen="P-02 material id")
    add(id="O-11", zone="pockets / feature count", title="Delete both floating side pockets",
        g=w["floating side pockets x2"] * (1 + THREAD), usd=-sum(area(P, k) * cost_m2(P[k]["piece"].material_id) for k in ("P-01", "P-02", "P-03")),
        durability="loses tripod / rifle-stock / bottle carry and 5.8 L; wraps alone carry long items",
        source="geometry.yaml weight row; volumes.side_pocket_each_L", status="owner",
        rec="NO. Tripod and stock carry are requirements R-18..22.", pattern_regen="delete P-01..P-03")
    sleeve = BG.piece_mass(P["B-09"]) - 2 * 0.10 * web25
    add(id="O-12", zone="feature count", title="Hydration: replace the sleeve B-09 with 2 hanger loops",
        g=sleeve * (1 + THREAD), usd=-area(P, "B-09") * cost_m2("robic_100d_ripstop"),
        durability="the bladder then sits against the meat stack: blood on the bladder and no separation",
        source="B-09 piece, poly_webbing_25mm record", status="owner",
        rec="NO. Meat rides in this bag; keep the sleeve.", pattern_regen="delete B-09")
    zip_L = (ctx["diag"]["zip_len"] + 60) / 1000
    g_zip = zip_L * (MAT.load("coil_zipper_10").require("mass_g_m") - MAT.load("coil_zipper_8").require("mass_g_m")) \
        + 2 * (6.0 - MISSING["slider_coil_8"]["mass_g"])
    add(id="O-13", zone="zip", title="Diagonal zip #10 -> #8 coil (2 sliders kept)",
        g=g_zip, usd=-zip_L * 1.0,
        durability="#8 under a meat load and gloved hands; the leaders use #10 on the main zip (SG, research 3.1)",
        source="coil_zipper_10/8 records; slider masses ASSUMPTION", status="owner",
        rec="NO. The main zip is the last place to save 7 g.", pattern_regen="none (tape width differs 1 mm: B-08 notes)")
    add(id="O-14", zone="zip", title="Diagonal zip: one slider instead of two",
        g=6.0, usd=-1.0, durability="lose the open-from-either-end access that makes one zip ambidextrous",
        source="slider 6 g ASSUMPTION (build_geometry zip row)", status="owner", rec="NO. Ambidextrous access is a decision.")
    lash = swap(P, ["B-11"], "tpu_coated_nylon_840d")
    add(id="O-15", zone="reinforcement", title="Lash tabs B-11 Hypalon -> laser-cut TPU-coated 840D",
        g=lash[0], usd=lash[1],
        durability="lighter and stiffer; laser fuses the cut edge; pull-test the 25 x 5 slot to the 450 N buckle class first",
        source="hypalon_coated_nylon, tpu_coated_nylon_840d records", status="owner",
        rec="YES, pending a 5-sample slot pull test.", pattern_regen="B-11 material id")
    w3 = next(x for x in geom["haul_wraps"] if x["id"] == "W3")
    add(id="O-16", zone="feature count", title="Delete haul wrap W3 (crown wrap)",
        g=(w3["cut_length_mm"] / 1000 * web25 + 4 + MAT.load("ladder_lock_25mm").require("mass_g")), usd=-2.0,
        durability="the roll-top clips still compress the top; frame-only loses the top lash to the crown and antler carry",
        source="geometry.yaml haul_wraps W3; G-hook 4 g ASSUMPTION", status="owner",
        rec="NO. Antler/cape lash is a field use case; keep W3.")
    for it in out:
        it["g"] = round(float(it["g"]), 1)
        it["usd"] = round(float(it["usd"]), 2)
    return out


def truth_up(pan):
    """Bag-side fabric: design bill of panels vs the released v3.1 cut list (what is actually cut)."""
    if not CUTLIST.exists():
        return None
    groups = {"main bag": ("B-", "D-"), "fly": ("F-",), "pockets": ("P-",), "accents": ("SH-01", "SH-02", "SH-03", "SH-04")}
    rows = list(csv.DictReader(CUTLIST.open()))
    out = {}
    for name, pref in groups.items():
        skip = ("B-12", "B-13", "B-14", "B-15", "B-16")   # ports, swell caps (attachment line), floor channels (cradle)
        cut = sum(float(r["mass_g"] or 0) for r in rows if r["piece_id"].startswith(pref) and r["size"] == ""
                  and not r["piece_id"].startswith(skip))
        des = sum(p["mass_g_total"] for p in pan["panels"] if p["id"].startswith(pref) and p["id"] != "B-12")
        out[name] = {"design_g": round(des, 1), "cut_list_g": round(cut, 1), "delta_g": round(cut - des, 1)}
    return out


def chart_budget(geom, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BAG = {"main bag", "accents", "rain fly", "pockets", "bag-to-frame attachment (fairleads)",
           "under-straps US1/US2 (cradle)", "internal meat harness", "haul wraps (= compression)"}
    g = geom["weight"]["groups_g"]
    items = sorted(g.items(), key=lambda kv: kv[1])
    names = [k.split(" (")[0] if not k.startswith("frame") else "frame (printed branch)" for k, _ in items]
    vals = [v for _, v in items]
    cols = ["#eb6834" if k in BAG else "#2a78d6" for k, _ in items]
    fig, ax = plt.subplots(figsize=(8.0, 9.0), dpi=110)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    ax.barh(range(len(vals)), vals, color=cols, height=0.72, edgecolor="#fcfcfb", linewidth=2)
    for i, v in enumerate(vals):
        ax.text(v + 12, i, f"{v:.0f} g", va="center", fontsize=10, color="#0b0b0b")
    ax.set_yticks(range(len(vals)), names, fontsize=10, color="#0b0b0b")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(axis="x", colors="#52514e")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xlabel("grams", color="#52514e")
    tot = geom["weight"]["total_g"]
    bag = sum(v for k, v in g.items() if k in BAG)
    fig.suptitle(f"Pack 5200 base weight: {tot:.0f} g ({tot / 453.592:.2f} lb) vs 2268 g (5.0 lb) target",
                 fontsize=13, fontweight="bold", color="#0b0b0b", x=0.02, ha="left")
    ax.set_title(f"orange = bag side, {bag:.0f} g   |   blue = frame, back system, belt, harness, "
                 f"{tot - bag:.0f} g   |   gap {tot - 2268:.0f} g", fontsize=9.5, color="#52514e", loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)


def chart_savings(its, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"applied": "#2a78d6", "yes": "#1baf7a", "no": "#eb6834"}
    rows = sorted(its, key=lambda x: x["g"])
    fig, ax = plt.subplots(figsize=(8.0, 9.5), dpi=110)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    kinds = []
    for i, it in enumerate(rows):
        k = "applied" if it["status"] == "applied" else ("yes" if it["rec"].startswith("YES") else "no")
        kinds.append(k)
        ax.barh(i, it["g"], color=col[k], height=0.72, edgecolor="#fcfcfb", linewidth=2)
        ax.text(it["g"] + 1.5, i, f"{it['g']:.0f} g", va="center", fontsize=9.5, color="#0b0b0b")
    lab = [f"{it['id']}  {it['title'][:46]}" + ("..." if len(it["title"]) > 46 else "") for it in rows]
    ax.set_yticks(range(len(rows)), lab, fontsize=8.8, color="#0b0b0b")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors="#52514e")
    ax.grid(axis="x", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(r["g"] for r in rows) * 1.2)
    ax.set_xlabel("grams saved", color="#52514e")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=col["applied"], label="applied (no owner choice)"),
                       Patch(color=col["yes"], label="owner choice, recommend YES"),
                       Patch(color=col["no"], label="owner choice, recommend NO")],
              loc="lower right", frameon=False, fontsize=9)
    ap = sum(r["g"] for r, k in zip(rows, kinds) if k == "applied")
    ys = sum(r["g"] for r, k in zip(rows, kinds) if k == "yes")
    fig.suptitle("Bag-side weight cuts, ranked", fontsize=13, fontweight="bold", color="#0b0b0b", x=0.02, ha="left")
    ax.set_title(f"applied {ap:.0f} g  +  recommended {ys:.0f} g  =  {ap + ys:.0f} g of a 762 g gap",
                 fontsize=9.5, color="#52514e", loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_md(geom, its, tu, screens):
    w = geom["weight"]
    tot, gap = w["total_g"], w["gap_g"]
    BAGK = ("main bag", "accents", "rain fly", "pockets", "bag-to-frame", "under-straps", "internal meat", "haul wraps")
    bag = sum(v for k, v in w["groups_g"].items() if k.startswith(BAGK))
    applied = [i for i in its if i["status"] == "applied"]
    owner = sorted([i for i in its if i["status"] == "owner"], key=lambda i: -i["g"])
    yes = [i for i in owner if i["rec"].startswith("YES")]
    pre = tot + sum(i["g"] for i in applied)
    L = []
    a = L.append
    a("# Pack 5200: bag weight-cut plan")
    a("")
    a("Owner: pack-designer. Date 2026-11-05. Generated by `designs/pack_5200/bag_weight_plan.py` from "
      "`build_geometry.build()` (the design bill of panels), the material records in `data/materials/`, and the "
      "analysis records. Re-run it after any change; do not hand-edit the numbers.")
    a("")
    a(HISTORICAL_NOTE)
    a("")
    a("## Summary")
    a("")
    a(f"- Production pack before this plan: **{pre:.0f} g ({pre / 453.592:.2f} lb)**. After the applied item: "
      f"**{tot:.0f} g ({tot / 453.592:.2f} lb)**. Target 2268 g (5.0 lb). Gap **{gap:.0f} g**.")
    a(f"- The bag side (bag body, fly, pockets, attachment, under-straps, meat harness, wraps) is **{bag:.0f} g**. "
      f"The other {tot - bag:.0f} g is the printed frame, spreader, back panel, hipbelt and harness.")
    a(f"- Applied (no owner choice): {', '.join(i['id'] for i in applied)}, **-{sum(i['g'] for i in applied):.0f} g**.")
    a(f"- Owner choices I recommend: {', '.join(i['id'] for i in yes)}, **-{sum(i['g'] for i in yes):.0f} g** more. "
      f"With them the pack is about **{tot - sum(i['g'] for i in yes):.0f} g "
      f"({(tot - sum(i['g'] for i in yes)) / 453.592:.2f} lb)**.")
    a(f"- Every bag-side item on the list together, recommended or not, is "
      f"**-{sum(i['g'] for i in its):.0f} g**. **The bag cannot close the gap.** The 5.0 lb target was set on the "
      f"569 g tube frame; the printed branch frame plus spreader is {w['groups_g'][next(k for k in w['groups_g'] if k.startswith('frame'))] + w['groups_g'][next(k for k in w['groups_g'] if k.startswith('back-system'))]:.0f} g. "
      "Closing it needs a frame-side decision or a new target (owner choice OC-0 below).")
    a("")
    a("Cost is the material delta per pack (record cost per yard over the record roll width; ASSUMPTION 1.5 m "
      "roll when a record has none). Thread follows the 3 % rule of the budget.")
    a("")
    a("## Ranked list (bag side)")
    a("")
    a("| Rank | ID | Zone | Change | g saved | $ / pack | Durability / function trade | Source | Status |")
    a("|---:|---|---|---|---:|---:|---|---|---|")
    for n, i in enumerate(sorted(its, key=lambda i: -i["g"]), 1):
        st = "applied" if i["status"] == "applied" else ("owner: rec YES" if i["rec"].startswith("YES") else "owner: rec NO")
        alt = f" ({i['alt']})" if i.get("alt") else ""
        a(f"| {n} | {i['id']} | {i['zone']} | {i['title']}{alt} | {i['g']:.1f} | {i['usd']:+.2f} | {i['durability']} | "
          f"{i['source']} | {st} |")
    a("")
    a("## Applied in this pass")
    a("")
    for i in applied:
        a(f"- **{i['id']}** {i['title']}: -{i['g']:.1f} g. {i['durability']}. Patterns: {i['pattern_regen']}.")
    a("- Accounting, no grams: the v3.1 LINK row (4 toggles, 0.6 m webbing, 2 quick-pins, 30.8 g) is out of the "
      "budget and the fairlead parts are listed one by one instead of a net delta (same total).")
    a("")
    if tu:
        a("## Cross-check: design bill of panels vs the released cut list")
        a("")
        a("The weight budget uses `panels.yaml` (gore-method design pieces). The cut set is the v3.1 production "
          "pattern set (`outputs/release/pack5200_v3.1_patterns/cutlist.csv`). Fabric only; ports B-12, swell caps "
          "B-13..15 (in the attachment line) and floor channels B-16 (in the cradle line) excluded:")
        a("")
        a("| Group | design g | cut list g | cut - design |")
        a("|---|---:|---:|---:|")
        for k, v in tu.items():
            a(f"| {k} | {v['design_g']:.1f} | {v['cut_list_g']:.1f} | {v['delta_g']:+.1f} |")
        a("")
        a(f"Net {sum(v['delta_g'] for v in tu.values()):+.1f} g. Not taken into the budget: the manufacturing-engineer "
          "rebuilds the BOM from the cut list (RESUME next step 8). The fly is the big one: the drafted fly is smaller "
          "than the 0.80 x surface x 1.12 estimate in `build_geometry.info_fly_area`.")
        a("")
    a("## Owner choices")
    a("")
    after = tot - sum(i["g"] for i in yes)
    a("**OC-0. The target.** Bag-side cuts are worth about "
      f"{sum(i['g'] for i in yes) + sum(i['g'] for i in applied):.0f} g with no loss of function. The rest of the "
      f"gap (~{after - 2268:.0f} g) is in the printed frame and back system, which the owner chose over the lighter tube "
      "frame (DECISIONS 2026-11-01). **Recommendation:** stop chasing 5.0 lb in the bag. Publish the honest number for "
      f"the printed frame (about {after:.0f} g, {after / 453.592:.2f} lb with the recommended cuts), keep 5.0 lb as the "
      "target of a later lighter-frame variant, and if 5.0 lb must hold now, order a frame-side mass study from the "
      "structural-fea-engineer. More bag cuts would cost meat-haul function, quiet or durability.")
    a("")
    for i in owner:
        a(f"**{i['id']}. {i['title']}** (-{i['g']:.1f} g, {i['usd']:+.2f} $/pack{', ' + i['alt'] if i.get('alt') else ''}). "
          f"Trade: {i['durability']}. **Recommendation: {i['rec']}** Patterns if accepted: {i['pattern_regen']}.")
        a("")
    a("## Missing material records (ASSUMPTION, for the materials-engineer)")
    a("")
    for k, v in MISSING.items():
        a(f"- `{k}`: {v['why']}" + (f" ({v['gsm']} gsm)" if "gsm" in v else "") + (f" ({v['mass_g']} g)" if "mass_g" in v else ""))
    a("- Seam tape for taped seams (O-9): 3 g/m ASSUMPTION.")
    a("")
    a("## Screenshots")
    a("")
    for s in screens:
        a(f"- `{s}`")
    a("")
    return "\n".join(L)


def main():
    geom, pan, ctx, P = build()
    its = items(geom, ctx, P)
    tu = truth_up(pan)
    SCREENS.mkdir(parents=True, exist_ok=True)
    s3 = SCREENS / "20261105_bag_3.png"
    s4 = SCREENS / "20261105_bag_4.png"
    chart_budget(geom, s3)
    chart_savings(its, s4)
    screens = [str(p.relative_to(ROOT)) for p in (s3, s4)]
    (ANALYSIS / "bag_weight_plan.md").write_text(write_md(geom, its, tu, screens))
    (ANALYSIS / "bag_weight_plan.json").write_text(json.dumps(
        {"date": "2026-11-05", "total_g": geom["weight"]["total_g"], "gap_g": geom["weight"]["gap_g"],
         "items": its, "cut_list_cross_check": tu, "missing_records": MISSING, "screens": screens}, indent=2))
    for i in sorted(its, key=lambda i: -i["g"]):
        print(f"{i['id']:5s} {i['g']:6.1f} g {i['usd']:+7.2f} $  {i['status']:7s} {i['rec'][:40]}  {i['title']}")
    print(tu)


if __name__ == "__main__":
    main()
