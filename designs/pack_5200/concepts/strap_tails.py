"""BL-031: strap tails on the whole pack (pack-designer, 2026-11-12).

    python designs/pack_5200/concepts/strap_tails.py            # audit table (belt M, crown kit M) + mass changes

Owner 2026-11-12: "Different sizes. We don't want straps hanging everywhere." The rule (``corrie_f.TAIL_RULE_MM``,
``KEEPER_OVER_MM``): the free tail past every adjuster is <= 100 mm (4 in) at the most-used setting (6-day load, mid
torso of the crown kit / mid waist of the belt size), and any strap whose tail can pass 150 mm (6 in) at some setting
carries a keeper. This module audits every adjustable strap on the pack against it, before and after BL-031's fixes,
and books the fixes' mass:

* ``bag_rows()``  -> bag side, booked by ``corrie_f.parts`` (BL-008 cfg tags);
* ``suspension_rows(size)`` -> harness and belt, booked by ``huntkit.mass.ledger`` as correction ``BL031``.

A tail is measured from the adjuster's exit to the webbing end: tail = (cut - sewn ends - path) / adjusters. Paths come
from the design's own geometry where it exists (cloth-sim / cloth-pass paths for the crown straps, geometry.yaml for
W1-W3 and IM1-IM3, hipbelt_diet.closure for the belt, build_geometry crown settings for the lifters, meat_haul for the
under-straps); where it does not, the path is an ASSUMPTION named here with the T9 measurement that settles it.
Units mm, g.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACK = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(PACK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---- assumptions (each with the test that settles it; doc section 16.5)
LIFTER_END_MM = 60.0       # ASSUMPTION: lifter sewn round its lug on the crown corner wrap, folded 2 x 30 (B-25 tab rule)
LIFTER_LET_OUT_MM = 50.0   # ASSUMPTION: lifter let out to drop the strap tops off the collarbones (vent / on-off)
LIFTER_CINCH_MM = 30.0     # ASSUMPTION: lifter cinched hard on a heavy load, past the snug setting
#                            -> settled by T9 (BL-031 addition): lifter free length at snug, let-out and hard on 3 users
STERNUM_GAP_MM = (100.0, 150.0, 220.0)   # ASSUMPTION: gap between the J-strap inner edges at the sternum (min /
#                            most-used / max), 5th F to 95th M; settled by the R-06 fit trial (>= 3 men, >= 3 women)
STERNUM_BUCKLE_MM = 60.0   # ASSUMPTION: Fidlock 25 mm magnetic buckle, both halves closed, lock bar to lock bar
STERNUM_END_MM = 40.0      # ASSUMPTION: sewn loop round the POM rail slider
STAB_PATH_M_MM = 140.0     # ASSUMPTION: hip stabilizer, frame anchor z 60 to the wing's ladder lock, belt M
STAB_RANGE_MM = 30.0       # ASSUMPTION: +/- travel between loose and cinched; settled with the HB-D1 side-hill trial
STAB_END_MM = 60.0         # sewn round the frame anchor, 2 x 30
W_HOOK_END_MM = 60.0       # ASSUMPTION: W1-W3 G-hook end, folded and box-X'd (2 x 30, the B-25 tab rule)
W_DAY_SQUEEZE_MM = 100.0   # ASSUMPTION: a 12 L day load cinched flat takes ~100 mm of depth out of the bag at each W
#                            height, so the W path is 2 x 100 mm shorter than on a full bag; settled by T9 (W free
#                            length on the day load)
W_TRIPOD_MM = 70.0         # ASSUMPTION: a tripod (corrie_f.TRIPOD_D 70 mm bundle) under W1 / W2 adds about one
#                            bundle diameter to the path (taut strap over a cylinder on a flat face); settled by T9
#                            (W1 / W2 free length with the tripod on)
W_EXT_ENDS_MM = 120.0      # haul extender: G-hook fold 60 + sewn loop 60 that takes the W's own G-hook
ROLL_END_MM = 90.0         # ASSUMPTION: roll clip strap sewn to the roll end (60) + round the buckle bar (30)
# ROLL-CUT ASSUMPTION: today's 350 mm roll-clip cut leaves a gloved grip (TAIL_GRIP) with the collar standing (full);
#   the clip strap runs down the gusset, so its path changes 1:1 with the roll height (CROWN_ROLLED lid tops). Settled
#   by T9 (roll clip free length at day, 6-day and full).
PULL_TAB_MM = 60.0         # torso pull strap (crown_diet d2) grab tab, sewn


def _F():
    import corrie_f as F
    return F


def _geo() -> dict:
    import yaml
    return yaml.safe_load((PACK / "geometry.yaml").read_text())


def _panels() -> dict:
    import yaml
    return yaml.safe_load((PACK / "panels.yaml").read_text())


def _cut(use_prefix: str) -> float:
    for r in _panels()["webbing_cut_list"]:
        if r["use"].startswith(use_prefix):
            return float(r["length_mm"])
    raise KeyError(use_prefix)


def _web25() -> float:
    return _F().WEB25


def _floor5(x: float) -> float:
    return 5.0 * math.floor(x / 5.0 + 1e-9)


def _ceil5(x: float) -> float:
    """BL-048 m-2: a cut rounded DOWN leaves less than TAIL_GRIP at the longest path; cuts that size the grip round up."""
    return 5.0 * math.ceil(x / 5.0 - 1e-9)


def _row(sid, name, where, n, adjusters, cut_before, cut_after, ends, paths, keeper_before, keeper_after, src,
         settings=None, note=""):
    """One audit row. ``paths`` = {"max", "used", "min"} in mm (per strap); tails per adjuster."""
    def t(cut, L):
        return round((cut - ends - L) / adjusters, 1)
    F = _F()
    out = {"id": sid, "name": name, "where": where, "n": n, "adjusters": adjusters, "ends_mm": ends,
           "paths_mm": {k: round(v, 1) for k, v in paths.items()}, "settings": settings or {},
           "before": {"cut_mm": round(cut_before, 1), "tail_used_mm": t(cut_before, paths["used"]),
                      "tail_worst_mm": t(cut_before, paths["min"]), "keeper": keeper_before},
           "after": {"cut_mm": round(cut_after, 1), "tail_used_mm": t(cut_after, paths["used"]),
                     "tail_worst_mm": t(cut_after, paths["min"]),
                     "tail_longest_path_mm": t(cut_after, paths["max"]), "keeper": keeper_after},
           "source": src, "note": note}
    for k in ("before", "after"):
        s = out[k]
        s["rule_used"] = s["tail_used_mm"] <= F.TAIL_RULE_MM
        s["needs_keeper"] = s["tail_worst_mm"] > F.KEEPER_OVER_MM
        s["pass"] = (s["rule_used"] or bool(s["keeper"])) and (not s["needs_keeper"] or bool(s["keeper"]))
    return out


# =====================================================================================================================
# the audit, strap by strap
# =====================================================================================================================
def crown_row(kit: str = "M") -> dict:
    """B-28: before = BL-030's 20 mm single cut (one lock, rear toggle loop, no keeper); after = BL-031 per kit."""
    F = _F()
    a = F.crown_kit_straps(kit)
    d = F.crown_strap_diet()
    P = {"max": a["path_max_mm"], "used": a["path_used_mm"], "min": a["path_min_mm"]}
    r = _row("B-28", f"crown straps (kit {kit}, {a['torso_in'][0]:g}-{a['torso_in'][1]:g} in)", "bag (as hunted)", 2,
             2, 0.0, 0.0, 0.0, P, None, "25 mm elastic keeper at each lock", a["source"])
    # before: one adjuster, 20 mm, the 1138 mm cut with a 60 mm rear loop (BL-030)
    b_used = d["cut_mm"] - F.CROWN_LOOP - P["used"]
    b_worst = d["cut_mm"] - F.CROWN_LOOP - P["min"]
    r["adjusters"] = "1 -> 2"
    r["before"].update(cut_mm=d["cut_mm"], tail_used_mm=round(b_used, 1), tail_worst_mm=round(b_worst, 1),
                       rule_used=b_used <= F.TAIL_RULE_MM, needs_keeper=b_worst > F.KEEPER_OVER_MM, pass_=False)
    r["before"]["pass"] = False
    r["after"].update(cut_mm=a["cut_mm"], tail_used_mm=a["tail_used_mm"], tail_worst_mm=a["tail_worst_mm"],
                      tail_longest_path_mm=F.TAIL_GRIP_MM, rule_used=a["tail_rule_ok"],
                      needs_keeper=a["tail_worst_mm"] > F.KEEPER_OVER_MM)
    r["after"]["pass"] = (a["tail_rule_ok"] or a["keepers_per_strap"] > 0) and \
        (a["tail_worst_mm"] <= F.KEEPER_OVER_MM or a["keepers_per_strap"] > 0)
    r["note"] = "the slack is the lid's height range (day 414 -> full collar standing 830 mm at 19 in, CROWN_ROLLED)"
    return r


def lifter_row() -> dict:
    """Load lifters (2): lug on the crown corner wrap -> ladder lock on the shoulder strap top. The path is the same at
    every torso setting (the crown carries the yoke and the lugs: lifter angle 40.6 deg at every setting,
    build_geometry.crown_settings, 140 mm forward of the lug)."""
    from huntkit.gendesign import attach_system as AS
    rows = AS._bg().crown_settings()
    cs = min(rows, key=lambda q: abs(q["torso_in"] - 19.0))
    L = 140.0 / math.cos(math.radians(cs["lifter_angle_deg"]))
    P = {"max": L + LIFTER_LET_OUT_MM, "used": L, "min": L - LIFTER_CINCH_MM}
    F = _F()
    before = _cut("load lifters")
    after = _floor5(LIFTER_END_MM + P["max"] + F.TAIL_GRIP_MM)
    return _row("LL", "load lifters", "harness", 2, 1, before, after, LIFTER_END_MM, P,
                "tri-glide keeper (bag_attach)", "tri-glide keeper (bag_attach)",
                f"path 140 mm / cos({cs['lifter_angle_deg']} deg) (build_geometry.crown_settings) + LIFTER_LET_OUT / "
                "LIFTER_CINCH ASSUMPTIONS; cut panels.yaml webbing_cut_list")


def sternum_row() -> dict:
    """Sternum strap, each side (2): sewn to the POM rail slider -> ladder lock on its Fidlock half."""
    F = _F()
    side = [(g - STERNUM_BUCKLE_MM) / 2.0 for g in STERNUM_GAP_MM]
    P = {"max": side[2], "used": side[1], "min": side[0]}
    before = _cut("sternum")
    after = _floor5(STERNUM_END_MM + P["max"] + F.TAIL_GRIP_MM)
    return _row("ST", "sternum strap (each side)", "harness", 2, 1, before, after, STERNUM_END_MM, P, None, None,
                "STERNUM_GAP / BUCKLE / END ASSUMPTIONS; cut panels.yaml webbing_cut_list (2 x 400 mm)")


def stabilizer_row(size: str = "M") -> dict:
    """Hip stabilizers (2), per belt size: frame anchor z 60 -> ladder lock on the belt wing. The wing grades by
    length, so the path grows with the size (ASSUMPTION: by half the wing-length change, the lock sits mid-wing)."""
    import hipbelt_diet as HD
    F = _F()
    L = STAB_PATH_M_MM + 0.5 * (HD.B.wing_len(size) - HD.B.wing_len("M"))
    P = {"max": L + STAB_RANGE_MM, "used": L, "min": L - STAB_RANGE_MM}
    before = HD.STAB_25_M * 1000.0 / 2.0
    after = _floor5(STAB_END_MM + P["max"] + F.TAIL_GRIP_MM)
    return _row("HS", f"hip stabilizers (belt {size})", "belt", 2, 1, before, after, STAB_END_MM, P, None, None,
                "STAB_PATH_M / STAB_RANGE ASSUMPTIONS + hipbelt_diet.B.wing_len; cut hipbelt_diet.STAB_25_M",
                settings={"cut_by_size_mm": {s: _floor5(STAB_END_MM + STAB_PATH_M_MM + 0.5 * (HD.B.wing_len(s) -
                          HD.B.wing_len("M")) + STAB_RANGE_MM + F.TAIL_GRIP_MM) for s in HD.HC.SIZES_B}})


def belt_row(size: str = "M") -> dict:
    """Hipbelt B 2:1 pull (each side): the tail grows by 2 x the leg change (hipbelt_diet.closure). The tail at the
    size's largest waist was TAIL_MIN 150 mm; BL-031 takes it to the gloved grip and adds an elastic keeper."""
    import hipbelt_diet as HD
    F = _F()
    c = HD.closure(size)
    mx, mn = c["leg_max_mm"], c["leg_min_mm"]
    # express as a 1-adjuster strap whose 'path' is 2 x leg: tail = TAIL - 2 (leg - leg_max)
    P = {"max": 2 * mx, "used": mx + mn, "min": 2 * mn}
    ends = 0.0
    before = HD.TAIL_MIN_MM + 2 * mx
    after = F.TAIL_GRIP_MM + 2 * mx
    r = _row("HB", f"hipbelt 2:1 pull (belt {size}, each side)", "belt", 2, 1, before, after, ends, P, None,
             "25 mm elastic keeper on the wing tip", "hipbelt_diet.closure (BL-006 a2): tail = TAIL + 2 (leg_max - leg);"
             " mid waist = most used")
    r["note"] = (f"the 2:1 doubles the waist range: legs {mn:.0f}-{mx:.0f} mm, so the tail moves "
                 f"{2 * (mx - mn):.0f} mm across the size")
    return r


def wrap_rows(kit: str = "M") -> list:
    """W1-W3 (geometry.yaml haul_wraps, A-2 tails): one ladder lock each (R), G-hook (L). Before: one cut for carry and
    haul. After: cut for carry (W1 / W2 with the tripod under them, W3 at the kit's short torso); the meat haul and
    antler / cape lash use a haul extender each (meat-trip kit)."""
    F = _F()
    import corrie as CO
    g = _geo()["haul_wraps"]
    a2 = CO.SPECS["B.1"]["wrap_tail_mm"] - CO.SPECS["B.2"]["wrap_tail_mm"]
    lo, hi = F.crown_kits()[kit]
    out = []
    for w in g:
        carry, haul = float(w["carry_path_mm"]), float(w["haul_path_mm"])
        crown = w["id"] == "W3"
        if crown:     # W3 runs from the crown top bar: it moves with the torso like the crown straps (same bar)
            import numpy as np
            d_lo = float(np.mean(F._crown_delta_at(lo)))
            d_mid = float(np.mean(F._crown_delta_at(0.5 * (lo + hi))))
            d_hi = float(np.mean(F._crown_delta_at(hi)))
            c_max, c_used, c_min = carry + d_lo, carry + d_mid, carry + d_hi - 2 * W_DAY_SQUEEZE_MM
            h_max = haul + d_lo
        else:
            c_max = carry + W_TRIPOD_MM
            c_used = c_max                       # as hunted: the tripod rides under W1 / W2 (BL-010 S10)
            c_min = carry - 2 * W_DAY_SQUEEZE_MM
            h_max = haul + W_TRIPOD_MM
        before = float(w["cut_length_mm"]) - a2
        after = W_HOOK_END_MM + c_max + F.TAIL_GRIP_MM
        P = {"max": c_max, "used": c_used, "min": c_min}
        r = _row(w["id"], f"haul wrap {w['id']}" + (f" (kit {kit})" if crown else ""), "bag", 1, 1, before, after,
                 W_HOOK_END_MM, P, "2 keeper loops in the gore seams", "2 keeper loops in the gore seams",
                 "geometry.yaml haul_wraps (carry / haul paths) - A-2; W_DAY_SQUEEZE, W_TRIPOD ASSUMPTIONS"
                 + ("; torso change = crown strap's (TORSO-LIN)" if crown else ""))
        ext = h_max - c_max + W_EXT_ENDS_MM
        r["haul"] = {"path_mm": round(h_max, 1), "tail_before_mm": round(before - W_HOOK_END_MM - h_max, 1),
                     "extender_mm": round(ext, 1), "tail_after_mm": round(after - W_HOOK_END_MM - c_max, 1)}
        out.append(r)
    return out


def im_rows() -> list:
    """IM1-IM3 (25 mm, BL-003 a; owner-frozen feature, BL-010 load path): cuts unchanged. Most used: no meat, hooked
    across B-01 port to port and cammed flat (geometry.yaml meat_harness ``stow``), path 2 x PORT_X + 2 x 40 mm."""
    import build_geometry as BG
    stow = 2 * BG.PORT_X + 2 * 40.0
    out = []
    for s in _geo()["meat_harness"]["straps"]:
        P = {"max": float(max(s["path_bag_on_mm"], s["path_float_mm"])), "used": stow, "min": stow}
        cut = float(s["cut_length_mm"])
        out.append(_row(s["id"], f"internal meat strap {s['id']}", "bag (inside)", 1, 1, cut, cut, 120.0, P, None,
                        "25 mm elastic keeper at the cam", "geometry.yaml meat_harness (cut, paths; 2 x 60 mm end "
                        "loops, build_geometry.meat_harness); stowed path = 2 x PORT_X + 2 x 40"))
    return out


def us_rows() -> list:
    """US1 / US2 under-straps (pin to pin, owner-frozen). BL-050 B: each strap has its own cut (corrie_f.US_CUT_MM)
    and its own lane (h1_bedfit published half span US1 70 / US2 165). Paths: the bag-off cradle (meat_haul's two
    straight legs to the BELLY_MM belly, on the strap's own half span; us_route.cradle_span) is the SHORTEST path (the
    longest tail); the bag-on path under the floor channels (us_route.json strap_lengths 'now', the meat drapes) is
    the longest."""
    from huntkit.gendesign import meat_haul as MH
    F = _F()
    pub = json.loads(F.H1_PUBLISHED.read_text())["published"]
    ur = HERE.parent / "analysis" / "us_route.json"
    sl = json.loads(ur.read_text()).get("strap_lengths") if ur.exists() else None
    out = []
    import patterns_corrie_f_rev3 as PT
    reach = PT.USA_CUT / 2.0 - PT.USA_PIN_LOOP / 2.0    # the USA cam anchor spans this much of the pin-to-pin path
    for sid, n in (("US", "us1"), ("US2", "us2")):
        cradle = 2 * math.hypot(float(pub[n.upper() + "_X"]), MH.BELLY_MM) - reach      # the strap's own share
        cut = float(F.US_CUT_MM[n])
        bag_on = None
        if sl and "now" in sl.get("layouts", {}):
            bag_on = float(sl["layouts"]["now"][n]["need_mm"])        # pin-to-cam, as strap_lengths (USA reach off)
        P = {"max": max(cradle, bag_on or cradle), "used": bag_on or cradle, "min": cradle}
        r = _row(sid, f"under-strap {n.upper()}", "frame / bag floor", 1, 1, cut, cut, 2 * 50.0, P,
                 "tri-glide keeper (meat_haul)", "tri-glide keeper (meat_haul)",
                 f"corrie_f.US_CUT_MM (BL-050 B); cradle 2 x hypot(half span {pub[n.upper() + '_X']:.0f}, belly "
                 f"{MH.BELLY_MM:.0f}) less the USA reach; bag-on path us_route.json strap_lengths 'now'; 2 x 50 mm sewn eye")
        r["note"] = ("bag-on path modelled on the meat drapes (us_route); bag-off cradle on the lane span; the "
                     "stainless tri-glide holds the tail flat in every mode")
        out.append(r)
    return out


ROLL_CLIPS = HERE / "corrie_f_sim" / "corrie_f_roll_clips.json"   # huntkit.viz3d.corrie_f --roll-clips (BL-031)


def roll_row() -> dict:
    """Roll-top side clips (2): roll end -> 25 mm side-release on the gusset tab. Paths from the cloth-pass roll model
    at day / 6-day / full (``ROLL_CLIPS``; ASSUMPTION ROLL-CLIP-PATH: the render's roll (ends bent down towards the
    tabs, cloth_pass clip_run / clip_below_seam) stands in for the sewn roll; settled by T9, clip free length at the
    three loads). Without that file: ROLL-CUT (today's cut leaves the grip on a full bag, path 1:1 with the roll
    height). The cut is unchanged (350 mm, panels.yaml) unless the paths say otherwise."""
    F = _F()
    cut = _cut("roll-top clips")
    if ROLL_CLIPS.exists():
        st = json.loads(ROLL_CLIPS.read_text())["states"]
        L = {k: max(v["roll_clip_mm"].values()) for k, v in st.items() if v.get("roll_clip_mm")}
        Lmin = {k: min(v["roll_clip_mm"].values()) for k, v in st.items() if v.get("roll_clip_mm")}
        P = {"max": max(L.values()), "used": float(np.mean(list(st["sixday"]["roll_clip_mm"].values()))),
             "min": min(Lmin.values())}
        src = "corrie_f_roll_clips.json (cloth-pass roll model, ROLL-CLIP-PATH ASSUMPTION); cut panels.yaml"
        after = _ceil5(ROLL_END_MM + P["max"] + F.TAIL_GRIP_MM)     # BL-048 m-2: up, so the grip is >= TAIL_GRIP
    else:
        z = {k: v["lid_top_z"] for k, v in json.loads(F.CROWN_ROLLED.read_text())["states"].items()}
        L_full = cut - ROLL_END_MM - F.TAIL_GRIP_MM
        P = {"max": L_full, "used": L_full - (z["full"] - z["sixday"]), "min": L_full - (z["full"] - z["day"])}
        src = "panels.yaml cut 350 mm; roll heights CROWN_ROLLED lid_top_z (day / 6-day / full); ROLL-CUT ASSUMPTION"
        after = cut
    r = _row("RT", "roll-top side clips", "bag", 2, 1, cut, after, ROLL_END_MM, P, None, None, src)
    if r["after"]["needs_keeper"] or not r["after"]["rule_used"]:
        r = _row("RT", "roll-top side clips", "bag", 2, 1, cut, after, ROLL_END_MM, P, None,
                 "25 mm elastic keeper below the buckle", src)
    if not r["after"]["rule_used"]:
        # BL-048 m-2: DECISION RT-TAIL-EXC. The clip runs from the roll end, whose height spans day -> full, so one cut
        # cannot meet both the gloved grip at the longest path and the tail rule at the 6-day path. Grip wins (a clip
        # that cannot be closed on a full bag is a failure); the tail rule is waived for RT, mitigated by the K-RT
        # elastic keeper (tail rolled and held flat). Settled by T9-R3c (free length at day / 6-day / full).
        r["exception"] = {"rule": "TAIL RULE (<= %.0f mm at the most-used setting)" % F.TAIL_RULE_MM,
                          "decision": "RT-TAIL-EXC", "mitigation": "K-RT 25 mm elastic keeper below the buckle",
                          "tail_used_mm": r["after"]["tail_used_mm"], "grip_longest_mm": r["after"]["tail_longest_path_mm"],
                          "settled_by": "T9-R3c"}
        r["note"] = (r.get("note") or "") + " TAIL-RULE exception RT-TAIL-EXC (BL-048 m-2): grip at the full bag wins; K-RT keeper"
    return r


def other_rows() -> list:
    from huntkit.gendesign import meat_haul as MH
    F = _F()
    rows = [
        {"id": "B-24", "name": "float links B-24 (meat-trip kit)", "where": "frame", "adjust": "3 sewn loops (no buckle)",
         "tail_used_mm": MH.LINK["tail_mm"], "tail_worst_mm": MH.LINK["tail_mm"], "keeper": "heat-sealed end",
         "pass": True, "source": "meat_haul.LINK tail_mm"},
        {"id": "B-25", "name": "guy bridle B-25", "where": "crown bar", "adjust": "none (sewn sleeve and tabs)",
         "tail_used_mm": 0.0, "tail_worst_mm": 0.0, "keeper": None, "pass": True, "source": "corrie_f.guy_bridle"},
        {"id": "B-26", "name": "tripod keeper B-26", "where": "right gusset", "adjust": "none (shock cord, ends in seams)",
         "tail_used_mm": 0.0, "tail_worst_mm": 0.0, "keeper": None, "pass": True, "source": "corrie_f.tripod_keeper"},
        {"id": "PG", "name": "port guys (B-27 -> B-22, inside the bag)", "where": "bag (inside)",
         "adjust": "heavy ladder lock + tri-glide on B-22", "tail_used_mm": 100.0, "tail_worst_mm": 100.0,
         "keeper": "elastic keeper (attach_system)", "pass": True,
         "source": "attach_system: 'tail 100 mm in an elastic keeper'; rev 3 guy is fixed length (sims)"},
        {"id": "SH", "name": "shoulder straps (J / S)", "where": "harness",
         "adjust": "none: top quick-connect pin, lower end fixed to the z 110 anchor; fit by crown kit",
         "tail_used_mm": 0.0, "tail_worst_mm": 0.0, "keeper": None, "pass": True, "source": "DESIGN.md 5.3"},
        {"id": "TP", "name": "torso pull strap (crown_diet d2, 1:1)", "where": "frame (behind the lumbar pad)",
         "adjust": "pull-down through guide A; the pawl locks", "tail_used_mm": F.TAIL_GRIP_MM + 38.1,
         "tail_worst_mm": F.TAIL_GRIP_MM + 76.2, "keeper": None, "pass": True,
         "source": "cut rule BL-031: per kit, grip at the kit's longest setting; a kit spans +/-1.5 in = 76 mm on 1:1 "
                   "(crown_diet.SIZES); crown_diet.D2_WEB_M 0.45 m stays an ASSUMPTION (spine-bottom z per kit not "
                   "modelled)"},
        {"id": "BR", "name": "bow riser strap", "where": "bag right face", "adjust": "none (G-hook into a loop)",
         "tail_used_mm": 0.0, "tail_worst_mm": 0.0, "keeper": None, "pass": True, "source": "build_geometry.BOW_RISER"},
    ]
    return rows


def audit(size: str = "M", kit: str = "M") -> dict:
    rows = [crown_row(kit), lifter_row(), sternum_row(), stabilizer_row(size), belt_row(size)] + wrap_rows(kit) + \
        im_rows() + us_rows() + [roll_row()]
    F = _F()
    return {"size": size, "kit": kit, "rule_mm": F.TAIL_RULE_MM, "keeper_over_mm": F.KEEPER_OVER_MM,
            "grip_mm": F.TAIL_GRIP_MM, "rows": rows, "other": other_rows(),
            "all_pass": all(r["after"]["pass"] for r in rows) and all(o["pass"] for o in other_rows()),
            "not_audited": ["lumbar pad-seat bottom strap (hipbelt; path not modelled; BL-006 f1 replaces it with a "
                            "cord tie after HB-D3)", "D1 door lid straps H1-H3 (D1 is not the default door)",
                            "shock-cord tails at cord locks (FP-L / FP-R mouths, pole quiver): cords, not straps"]}


# =====================================================================================================================
# mass: what BL-031 books
# =====================================================================================================================
def bag_rows(kit: str = "M") -> list:
    """Bag-side rows for corrie_f.parts: ``(system, name, g, cfg, source)``. The crown straps are booked by
    ``corrie_f.rev3_addons`` (``crown_straps()``), not here."""
    F = _F()
    from huntkit.gendesign import loadpath_check as LP
    W25 = _web25()
    kg = F.tail_keeper_g()
    g25 = LP.hw()["g25"]["g"]
    out = []
    ws = wrap_rows(kit)
    d = sum(w["after"]["cut_mm"] - w["before"]["cut_mm"] for w in ws)
    cuts = ", ".join("%.0f->%.0f" % (w["before"]["cut_mm"], w["after"]["cut_mm"]) for w in ws)
    out.append(("straps_compression", f"BL-031: W1-W3 cut for carry ({cuts} mm)", d * W25 / 1000.0, "base",
                "strap_tails.wrap_rows x poly_webbing_25mm record"))
    ext = sum(w["haul"]["extender_mm"] for w in ws)
    out.append(("straps_compression", f"BL-031: W1-W3 haul extenders (3, {ext / 1000:.2f} m 25 mm + rated G-hook "
                "each; meat haul, float clamp, antler / cape lash)", ext * W25 / 1000.0 + 3 * g25, "meat_trip",
                "strap_tails.wrap_rows x poly_webbing_25mm + g_hook_25mm_aluminium record (loadpath_check.hw)"))
    out.append(("straps_meat", "BL-031: IM1-IM3 tail keepers (3, 25 mm elastic)", 3 * kg, "base",
                "TAIL_KEEPER_G ASSUMPTION (corrie_f)"))
    rr = roll_row()
    if rr["after"]["cut_mm"] != rr["before"]["cut_mm"]:
        out.append(("straps_compression", f"BL-031: roll-top clip straps cut {rr['before']['cut_mm']:.0f} -> "
                    f"{rr['after']['cut_mm']:.0f} mm (2)", 2 * (rr["after"]["cut_mm"] - rr["before"]["cut_mm"]) * W25
                    / 1000.0, "base", "strap_tails.roll_row x poly_webbing_25mm record"))
    if rr["after"]["keeper"]:
        out.append(("straps_compression", "BL-031: roll-top clip tail keepers (2, 25 mm elastic)", 2 * kg, "base",
                    "TAIL_KEEPER_G ASSUMPTION (corrie_f)"))
    return out


def suspension_rows(size: str = "M") -> list:
    """Harness and belt rows for the ledger (correction ``BL031``): ``(name, system, g, source, cfg)``."""
    F = _F()
    W25 = _web25()
    kg = F.tail_keeper_g()
    li, st, hs, hb = lifter_row(), sternum_row(), stabilizer_row(size), belt_row(size)
    return [
        (f"BL-031: load lifters cut {li['before']['cut_mm']:.0f} -> {li['after']['cut_mm']:.0f} mm (2)", "harness",
         2 * (li["after"]["cut_mm"] - li["before"]["cut_mm"]) * W25 / 1000.0,
         "strap_tails.lifter_row x poly_webbing_25mm record", "base"),
        (f"BL-031: sternum webbing cut {st['before']['cut_mm']:.0f} -> {st['after']['cut_mm']:.0f} mm a side (2)",
         "harness", 2 * (st["after"]["cut_mm"] - st["before"]["cut_mm"]) * W25 / 1000.0,
         "strap_tails.sternum_row x poly_webbing_25mm record", "base"),
        (f"BL-031: hip stabilizers cut {hs['before']['cut_mm']:.0f} -> {hs['after']['cut_mm']:.0f} mm (2, belt {size})",
         "belt", 2 * (hs["after"]["cut_mm"] - hs["before"]["cut_mm"]) * W25 / 1000.0,
         "strap_tails.stabilizer_row x poly_webbing_25mm record", "base"),
        (f"BL-031: hipbelt 2:1 tail at the largest waist {hb['before']['cut_mm'] - hb['paths_mm']['max']:.0f} -> "
         f"{hb['after']['cut_mm'] - hb['paths_mm']['max']:.0f} mm (2 sides)", "belt",
         2 * (hb["after"]["cut_mm"] - hb["before"]["cut_mm"]) * W25 / 1000.0,
         "strap_tails.belt_row x poly_webbing_25mm record", "base"),
        ("BL-031: hipbelt tail keepers (2, 25 mm elastic)", "belt", 2 * kg, "TAIL_KEEPER_G ASSUMPTION (corrie_f)",
         "base"),
    ]


def stabilizer_delta_g(size: str = "M") -> float:
    """The stabilizer share of ``suspension_rows`` (the roll-up's A_b step deletes the shortened strap)."""
    return sum(g for n, s, g, src, c in suspension_rows(size) if "stabilizers" in n)


def mass_summary(size: str = "M", kit: str = "M") -> dict:
    F = _F()
    b = bag_rows(kit)
    s = suspension_rows(size)
    cs = F.crown_straps(kit=kit)
    d = F.crown_strap_diet()
    out = {"bag": {n: round(g, 2) for _, n, g, _, _ in b}, "suspension": {n: round(g, 2) for n, _, g, _, _ in s},
           "crown_straps_g": cs["mass_g"], "crown_bl030_20mm_g": d["options"]["w20"]["mass_g"],
           "crown_bl029_g": F.crown_straps_bl029()["mass_g"]}
    for cfg in ("base", "as_hunted", "meat_trip"):
        inc = {"base": ("base",), "as_hunted": ("base", "as_hunted"), "meat_trip": ("base", "as_hunted", "meat_trip")}[cfg]
        bag = sum(g for _, _, g, c, _ in b if c in inc)
        sus = sum(g for _, _, g, _, c in s if c in inc)
        crown = cs["mass_g"] - d["options"]["w20"]["mass_g"] if cfg != "base" else 0.0
        out[cfg] = {"bag_g": round(bag, 2), "suspension_g": round(sus, 2), "crown_vs_bl030_g": round(crown, 2),
                    "total_g": round(bag + sus + crown, 2)}
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="M")
    ap.add_argument("--kit", default="M")
    a = ap.parse_args(argv)
    au = audit(a.size, a.kit)
    print(f"{'id':5} {'strap':42} {'cut b->a':>13} {'used b->a':>13} {'worst b->a':>13} keeper / pass")
    for r in au["rows"]:
        b, f = r["before"], r["after"]
        print(f"{r['id']:5} {r['name'][:42]:42} {b['cut_mm']:6.0f}>{f['cut_mm']:<6.0f} {b['tail_used_mm']:6.0f}>"
              f"{f['tail_used_mm']:<6.0f} {b['tail_worst_mm']:6.0f}>{f['tail_worst_mm']:<6.0f} "
              f"{f['keeper'] or '-'} / {f['pass']}")
    for o in au["other"]:
        print(f"{o['id']:5} {o['name'][:42]:42} {o['adjust'][:40]:40} tail {o['tail_used_mm']:.0f}/{o['tail_worst_mm']:.0f}")
    print("all pass:", au["all_pass"])
    print(json.dumps(mass_summary(a.size, a.kit), indent=1))


if __name__ == "__main__":
    main()
