"""BL-013: whole-pack weight roll-up, version 2 (pack-designer, 2026-11-11; brought up to date 2026-11-12).

    python designs/pack_5200/weight_rollup_v2.py            # print the scenario table, belt M
    python designs/pack_5200/weight_rollup_v2.py --write    # also write analysis/weight_rollup_v2.{md,json} + 2 PNGs

One answer to "what does the pack weigh now, and what can it reach?", built only from the mass ledger
(``huntkit.mass.ledger``, config ``corrie_b2_h1``) and the other tickets' modules, imported and called. No total is
typed here. Every change is a STEP: a list of ledger-schema rows ``{system, name, g, cfg, source, step}`` added to
the CORRIE B.2-on-H1 rows. A removed part is a negative copy of its ledger row. ``cfg`` is BL-008's rule (base /
as_hunted / meat_trip; owner-adopted 2026-11-10, the 6.6 lb target applies to base).

Steps are in two booked classes, kept apart everywhere (ticket acceptance), plus a list of retired steps:

* ``P`` proven now: a PASS verdict and no open decision gate. Booking corrections (resolved against their sources)
  and safety additions (BL-010, BL-021 / BL-024 / BL-027 H1 body) are in P.
* ``A`` after tests: a change whose own named test decides whether it stays (the test is listed with the step).
* ``R`` retired: not adopted, in no scenario (BL-017 OD 17 legs and BL-007 fixed torso, both below 1.0 on the cloth-sim
  loads, BL-021). Kept only so the report can say what they would have been. The BL-013 "owner options" class held
  only the fixed torso and is gone with it.

2026-11-12 update: CORRIE F is booked at rev 1 (BL-022, door D2); the H1 body is the ledger's H1B correction (800.7 g
raster, BL-024 + BL-027 + the 28 mm IM3 cheeks, which are inside that raster, so there is no separate cheek step).

Rule used to sort a gate (DECISION, analysis/weight_rollup_v2.md section 1): a test that, if failed, sends the change
back to a known heavier part is a decision gate (class A). A first-article check of the whole prototype with no mass
fallback (S15 elbow swing, the IM3 cheek re-run, R-28 protractor) is listed but does not move the change out of P.

Configs added to the ledger basis (task 1): ``configs()`` returns ledger-schema row sets for CORRIE F base and as
hunted, the BL-005 back system, the BL-006 belt package, and BL-007 frame variants (a) and (c). ``huntkit/mass``
itself is not edited (RULES.md rule 2); ``huntkit.mass.ledger.total / by_system / like_for_like`` take these rows.
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ANALYSIS = HERE / "analysis"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from huntkit.mass import ledger as L  # noqa: E402

LB, OZ = 453.592, 28.3495
CONFIG = "corrie_b2_h1"
SIZES = L.SIZES
CFGS = ("base", "as_hunted", "meat_trip")
_INCL = {"base": ("base",), "as_hunted": ("base", "as_hunted"), "meat_trip": CFGS}
TARGET_G = 6.6 * LB                       # 2993.7 g, owner target, applies to base (DECISIONS 2026-11-10)
SCEN = ("P", "A")
SCEN_NAME = {"P": "proven now", "A": "after tests", "R": "retired (not booked)"}
SCREENS = ROOT / "outputs" / "screens"
PREFIX = "20261112_rollup_"
DOC_SCREEN = ROOT / "docs" / "screens" / "20261112_rollup_1.png"   # waterfall, git-tracked copy
DOC = ANALYSIS / "weight_rollup_v2.md"
RESULT = ANALYSIS / "weight_rollup_v2.json"
KIT = "M"                                 # crown kit at the pack's headline size (torso 17.5-20.5 in); torso, not belt


# =====================================================================================================================
# ticket modules (imported lazily: some build cloth geometry)
# =====================================================================================================================
def _F():
    import corrie_f as F
    return F


CORRIE_F_REV = 1   # BL-022 rev 1 adopted (DECISIONS 2026-11-12): B-25 guy bridle + B-26 tripod keeper, guys at x +/-52.


def rev():
    """Context: corrie_f at CORRIE_F_REV (``corrie_f.revision``, BL-022); a no-op on a corrie_f without revisions."""
    import contextlib
    F = _F()
    return F.revision(CORRIE_F_REV) if hasattr(F, "revision") else contextlib.nullcontext()


def _HD():
    import hipbelt_diet as HD
    return HD


def _SA():
    import strap_arch as SA
    return SA


def _CD():
    from huntkit.gendesign import crown_diet as CD
    return CD


def _r(system, name, g, cfg, source, step=""):
    return {"system": system, "name": name, "g": round(float(g), 2), "cfg": cfg, "source": source, "step": step}


def _neg(row: dict, step: str, why: str) -> dict:
    return _r(row["system"], f"REMOVED: {row['name']}", -row["g"], row.get("cfg", "base"), f"{why}; ledger row", step)


def _ledger_row(prefix: str, size: str = "M", system: str | None = None) -> dict:
    hit = [r for r in L.parts(CONFIG, size) if r["name"].startswith(prefix) and (system is None or r["system"] == system)]
    if len(hit) != 1:
        raise KeyError(f"{len(hit)} ledger rows start with {prefix!r}")
    return hit[0]


# =====================================================================================================================
# start: CORRIE B.2 on H1 with BL-008 cfg tags
# =====================================================================================================================
@functools.lru_cache(maxsize=None)
def _b2(size: str) -> tuple:
    """Ledger rows (corrie_b2_h1, belt ``size``) with BL-008 tags: suspension + misc base, IMP-3 holster as hunted,
    bag side by ``corrie_f.corrie_b2_rows`` (same rule BL-011 used; F-02 split out of the fly row)."""
    F = _F()
    out = [_r(r["system"], r["name"], r["g"], "base", "ledger " + r["source"], "start")
           for r in L.parts(CONFIG, size) if r["system"] not in F.BAG_SIDE and not r["name"].startswith("IMP-3")]
    with rev():
        out += [_r(r["system"], r["name"], r["g"], r["cfg"], r["source"], "start") for r in F.corrie_b2_rows(size)]
    return tuple(out)


def b2_rows(size: str = "M") -> list:
    return [dict(r) for r in _b2(size)]


# =====================================================================================================================
# booking corrections (each resolved against its source; class P, kind "correction")
# =====================================================================================================================
def corner_wraps() -> dict:
    """C3 source numbers; the computation lives in the ledger since BL-023 (``ledger.corner_wraps``)."""
    return dict(L.corner_wraps())


def non_body_sources() -> dict:
    """C5 source numbers; the computation lives in the ledger since BL-023 (``ledger.non_body_sources``)."""
    return dict(L.non_body_sources())


def corrections(size: str = "M") -> dict:
    """{step_id: rows}. The C1-C8 booking corrections, read from the ledger (``ledger.corrections``, folded in by
    BL-023), so the roll-up and ``ledger.total('corrie_b2_h1_v2')`` cannot drift apart."""
    return {k: [_r(r["system"], r["name"], r["g"], r["cfg"], "ledger correction " + k + ": " + r["source"], k)
                for r in rows]
            for k, rows in L.corrections(CONFIG, size).items()}


# =====================================================================================================================
# design steps
# =====================================================================================================================
def wing_parts() -> list:
    """The parts BL-003 deletes with the side wings, from strap_arch (each a ledger row or a record)."""
    SA = _SA()
    a = SA._lighten_im_us(SA.today_parts())
    keep = {p.id for p in SA._delete_wings(a)}
    return [p for p in a if p.id not in keep]


def corrie_f_step(size: str, fabrics: str, step: str) -> list:
    """B.2 bag side out, CORRIE F (door D2) in (BL-011; carries BL-003 REC straps, BL-004 REC attachment, BL-010
    hardware). The fairlead and swell rows CORRIE F inherits from the ledger stay in both, so C1/C2 apply once."""
    F = _F()
    out = [_r(r["system"], f"REMOVED (B.2): {r['name']}", -r["g"], r["cfg"], "corrie_f.corrie_b2_rows", step)
           for r in F.corrie_b2_rows(size) if r["system"] in F.BAG_SIDE]
    out += [_r(r["system"], f"CORRIE F: {r['name']}", r["g"], r["cfg"], r["source"], step)
            for r in F.parts(size, "D2", fabrics)]
    return out


def fabric_step(size: str) -> list:
    """BL-011 fabric swaps: CORRIE F team-B fabrics minus CORRIE F today's fabrics (same pieces)."""
    F = _F()
    return ([_r(r["system"], f"CORRIE F: {r['name']}", r["g"], r["cfg"], r["source"], "A_fab")
             for r in F.parts(size, "D2", "B")]
            + [_r(r["system"], f"CORRIE F: {r['name']}", -r["g"], r["cfg"], r["source"], "A_fab")
               for r in F.parts(size, "D2", "today")])


def crown(option_name: str, size: str = KIT) -> float:
    """Pack-mass change of a crown_diet option against H1 (crown_diet.option_mass, the BL-017 code)."""
    CD = _CD()
    o = next(o for o in CD.OPTIONS if o.name == option_name)
    return CD.option_mass(o, size)["delta_g"]


def fixed_torso(variant: str, torso: float = 19.0) -> dict:
    """BL-007 frame variant at a torso (frame_fixed.frame_mass, the BL-007 code; body rasters from its FEA result)."""
    from huntkit.gendesign import frame_fixed as FF
    res = json.loads(FF.RESULT.read_text())
    h1 = res["h1_reproduced"]["raster_g"]
    m = FF.frame_mass(variant, torso, res["variants"][variant]["body"]["raster_g"], h1)
    return {"pack_delta_g": m["pack_g"] - L.total(CONFIG, "M"), "frame_g": m["frame_g"], "items": m["items"],
            "fatigue_old_basis": res["variants"][variant]["body"]["min"]["fatigue"]}


def package_c(size: str = "M") -> list:
    """Package C as the ledger books it on H1 (config corrie_b2_h1_c minus corrie_b2_h1): the adopted 7075 plate
    C-1+C-2+C-3 and the two rev C corrections C-4 (pad backer) and C-7 (yoke plate); C-9 is 0 g on H1 (ledger note).
    BL-011's pack (corrie_f.pack_with_adopted) left package C out; BL-006 used corrie_b2_h1_c as its baseline."""
    plain = {r["id"] for r in L.parts(CONFIG, size)}
    return [_r(r["system"], r["name"], r["g"], "base", "ledger corrie_b2_h1_c: " + r["source"], "P_pkgC")
            for r in L.parts("corrie_b2_h1_c", size) if r["id"] not in plain]


def h1_fatigue() -> dict:
    """H1 body fatigue on the recorded and the per-torso basis (BL-017 crown_diet results)."""
    b = json.loads(_CD().RESULT.read_text())["body"]
    old, new = b["h1_recorded_basis"]["min"]["fatigue"], b["h1"]["min"]["fatigue"]
    return {"old": old, "per_torso": new, "ratio": new / old}


CHEEK_HALF_Z = 14.0      # adopted IM3 cheek 28 x 8 mm (DECISIONS 2026-11-12, BL-021; supersedes 27 mm)


def cheek_g(half_z: float = CHEEK_HALF_Z) -> float:
    """Cross-check only (not booked since 2026-11-12): IM3 printed fairlead cheek 18 mm -> ``half_z`` x 2, both sides,
    as stand-alone fairlead volume (loadpath_check.FROZEN fine-mesh runs). The booked cheek is in the ledger's H1B body
    raster (``ledger.h1_body_update()['im3_cheek_28_g']``), which counts only the cheek volume outside the body it
    overlaps; the difference is listed under estimates (ASSUMPTION, settled by weighing the printed halves)."""
    from huntkit.gendesign import loadpath_check as LP
    f = LP.FROZEN["fairlead_im3"]
    return 2 * (f[half_z]["added_g"] - f[9.0]["added_g"])


def imus_a_rows(step: str, sign: float = 1.0, prefix: str = "BL-003 (a) IM/US") -> list:
    """BL-003 (a) on IM1-IM3 and US1/US2 (38 -> 25 mm webbing, 25 mm cams, rated G-hooks), part by part:
    strap_arch._lighten_im_us(today) - today (the REC strap set CORRIE F carries). ``sign`` -1 undoes it."""
    SA = _SA()
    t = {p.id: p for p in SA.today_parts()}
    out = []
    for p in SA._lighten_im_us(SA.today_parts()):
        d = p.g - t[p.id].g
        if abs(d) > 1e-9:
            out.append(_r(p.system, f"{prefix}: {p.id} {p.name}", sign * d, p.cfg,
                          "strap_arch._lighten_im_us(today_parts) - today_parts: " + p.source, step))
    return out


def attach_rec_rows(step: str, sign: float = 1.0, prefix: str = "BL-004 REC") -> list:
    """BL-004 REC (hood B-19/B-20 and IM2 bag hooks deleted, guy bar loops, B-17 trimmed), change by change:
    attach_diet.mass_changes('REC') against the ledger attachment system. ``sign`` -1 undoes it."""
    import attach_diet as AD
    return [_r("attachment", f"{prefix}: {n}", sign * g, "base", "attach_diet.mass_changes('REC'): " + b, step)
            for n, g, b in AD.mass_changes("REC")]


STEP_META = {   # id: (class, ticket, short label, kind, gate)
    "C1": ("P", "BL-004 flag", "fairleads booked twice", "correction", "-"),
    "C2": ("P", "BL-004 flag", "swell patches booked twice", "correction", "-"),
    "C3": ("P", "BL-017 flag", "crown-corner wraps unbooked", "correction", "-"),
    "C4": ("P", "BL-017 flag", "POM pawl housing booked twice", "correction", "weigh pawl + spring"),
    "C5": ("P", "BL-017 flag", "non-body lump short", "correction", "-"),
    "C6": ("P", "BL-004 flag", "lifter keepers -> harness", "correction", "-"),
    "C7": ("P", "BL-006 e", "holster tabs stay on belt", "correction", "-"),
    "C8": ("P", "BL-006 a2", "belt webbing re-booked", "correction", "HB-7 (planned lock-slip test)"),
    "H1B": ("P", "BL-024/027/021", "H1 body (sleeve growth, buckling members, 28 mm IM3 cheeks)",
            "safety", "MT-1 cinch, CA-1 PAHT ratio >= 0.255, T1/T2 gauges (release R1; failing adds mass, never removes)"),
    "P_pkgC": ("P", "package C (2026-11-09)", "7075 belt plate; C-4 / C-7 rev C fixes", "safety",
               "HB-5 plate, pad-seat sag test, T1(c) yoke dial (verification; the 6061 fallback fails rev C too)"),
    "P_F": ("P", "BL-011/010/022", "CORRIE F rev 1, D2, today's fabrics; wings, 38 mm IM/US and hood kept", "design",
            "first-article: S15 elbow-swing / sling check (BL-009)"),
    "P_d2": ("P", "BL-017 d2", "1:1 pull strap (no 3:1 pulley)", "design", "-"),
    "P_kits": ("P", "BL-017 a (owner)", "three crown kits, size M", "design", "-"),
    "A_imus": ("A", "BL-003 (a)", "IM/US straps 38 -> 25 mm, 25 mm cams + rated hooks", "design",
               "MT-1 / MT-2 / MT-3 at the BL-010 per-row loads; fallback 38 mm webbing, cams and hooks"),
    "A_att": ("A", "BL-004 REC", "hood + IM2 bag hooks deleted, guy toggle loops", "design",
              "PT-1 / PT-2 at 2553 N, TL-1 toggle loop 366 N, LL-H heavy lock 366 N; fallback hood + IM2 hooks "
              "(owner kept them removed 2026-11-12)"),
    "A_back": ("A", "BL-005", "sandwich backer strip", "design",
               "BP-1 3-point bend coupon + BP-2 stay contact width; BP-3 back pressure below z 190"),
    "A_b": ("A", "BL-006 b", "no belt stabilizers", "design", "HB-D1 side-hill stability"),
    "A_c2": ("A", "BL-006 c2", "0.75 mm wing stiffener", "design", "HB-D2 wing roll-over (+ HB-1 front-strap sensor)"),
    "A_f": ("A", "BL-006 f1+f2", "pad-seat cord tie + 1000D sleeve", "design", "HB-D3 pad-seat retention"),
    "A_fab": ("A", "BL-011 swaps", "ULTRAGrid / 70D / ULTRA 200X fabrics", "design",
              "owner swatch look (ULTRAGrid) + PT-3 and 50 mm strip test (ULTRA 200X)"),
    "A_wings": ("A", "BL-003 (owner)", "side wings deleted", "design",
                "FT-S2 5 km side-hill + door open/close x 5, pod shift <= 20 mm"),
    "A_c17": ("R", "BL-017 c17", "OD 17 legs, 19 mm bore", "design",
              "retired: body fatigue 0.97-0.99 on the cloth-sim loads (BL-021 (4)); not booked"),
    "O_fixed": ("R", "BL-007 (a)", "fixed torso instead of the kits", "design",
                "retired: body fatigue below 1.0 on the cloth-sim loads (BL-021 (4)); adjustable torso kept; not booked"),
}
ORDER = list(STEP_META)


@functools.lru_cache(maxsize=None)
def _steps(size: str) -> tuple:
    with rev():
        return _steps_at(size)


def _steps_at(size: str) -> tuple:
    F, HD, CD = _F(), _HD(), _CD()
    s = dict(corrections(size))
    wings = wing_parts()
    s["P_pkgC"] = package_c(size)
    s["P_F"] = (corrie_f_step(size, "today", "P_F") + [
        _r(p.system, f"wing part kept until FT-S2: {p.id} {p.name}", p.g, p.cfg, "strap_arch: " + p.source, "P_F")
        for p in wings]
        + imus_a_rows("P_F", -1.0, "38 mm IM/US kept until MT-1/MT-2/MT-3 (BL-003 (a) undone)")
        + attach_rec_rows("P_F", -1.0, "hood + IM2 hooks kept until PT-1/TL-1/LL-H (BL-004 REC undone)"))
    s["A_imus"] = imus_a_rows("A_imus")
    s["A_att"] = attach_rec_rows("A_att")
    d2 = crown("(d2) pawl + 1:1 strap")
    s["P_d2"] = [_r("frame", "BL-017 (d2): 3:1 pulley -> pawl + 1:1 pull strap", d2, "base",
                    "crown_diet.option_mass('(d2) pawl + 1:1 strap')", "P_d2")]
    ad2 = crown("(a)+(d2)")
    s["P_kits"] = [_r("frame", f"BL-017 (a): three crown kits, kit {KIT}", ad2 - d2, "base",
                      "crown_diet.option_mass('(a)+(d2)') - option_mass('(d2) ...')", "P_kits")]
    from huntkit.gendesign import back_system2 as BS2
    md = BS2.mass_delta_g(BS2._variant(BS2.RECOMMENDED))
    s["A_back"] = [_r("back", f"BL-005 BP-08 backer -> sandwich strip ({k})", g, "base",
                      "back_system2.mass_delta_g(RECOMMENDED)", "A_back") for k, g in md.items() if k != "total" and g]
    s["A_b"] = [_r("belt", "BL-006 b: stabilizer straps deleted", HD._mass_delta("b", size), "base",
                   "hipbelt_diet._mass_delta('b')", "A_b")]
    s["A_c2"] = [_r("belt", "BL-006 c2: HDPE wing stiffener 1.0 -> 0.75 mm", HD._mass_delta("c2", size), "base",
                    "hipbelt_diet._mass_delta('c2')", "A_c2")]
    s["A_f"] = [_r("belt", f"BL-006 {k}", HD._mass_delta(k, size), "base", f"hipbelt_diet._mass_delta('{k}')", "A_f")
                for k in ("f1", "f2")]
    s["A_fab"] = fabric_step(size)
    s["A_wings"] = [_r(p.system, f"BL-003 wings off: {p.id} {p.name}", -p.g, p.cfg, "strap_arch._delete_wings", "A_wings")
                    for p in wings]
    s["A_c17"] = [_r("frame", "BL-017 (c17): OD 17 x 7 UD legs, sleeve bore reamed 18 -> 19 mm",
                     crown("(a)+(d2)+(c17 bore 19)") - ad2, "base",
                     "crown_diet.option_mass('(a)+(d2)+(c17 bore 19)') - option_mass('(a)+(d2)')", "A_c17")]
    fx = fixed_torso("a")
    s["O_fixed"] = [
        _r("frame", "BL-007 (a) fixed torso at 19 in (frame_fixed.frame_mass, vs H1)", fx["pack_delta_g"], "base",
           "frame_fixed.frame_mass('a', 19)", "O_fixed"),
        _r("frame", "crown kits (a)+(d2)+(c17 bore 19) undone (fixed torso replaces them)",
           -crown("(a)+(d2)+(c17 bore 19)"), "base", "crown_diet.option_mass", "O_fixed"),
        _r("frame", "BL-007 removes the full 14 g pawl row; its 8 g POM share is already out (C4)",
           CD.PAWL_HOUSING_G - CD.PAWL_SPRING_G, "base", "crown_diet.PAWL_HOUSING_G - PAWL_SPRING_G", "O_fixed")]
    return tuple((k, tuple(v)) for k, v in s.items())


def steps(size: str = "M") -> dict:
    return {k: [dict(r) for r in v] for k, v in _steps(size)}


# =====================================================================================================================
# scenarios and totals
# =====================================================================================================================
def scenario_rows(scen: str, size: str = "M") -> list:
    """B.2 rows + every step of this scenario's class and the classes before it (P < A < O)."""
    upto = SCEN[: SCEN.index(scen) + 1]
    st = steps(size)
    out = b2_rows(size)
    for k in ORDER:
        if STEP_META[k][0] in upto:
            out += st[k]
    return out


def cfg_total(rows: list, cfg: str) -> float:
    return round(sum(r["g"] for r in rows if r["cfg"] in _INCL[cfg]), 1)


def cfg_rows(rows: list, cfg: str) -> list:
    """Rows of one weight configuration, in the ledger schema (L.total / by_system / like_for_like take them)."""
    return [r for r in rows if r["cfg"] in _INCL[cfg]]


def scenario_table(size: str = "M") -> dict:
    out = {"B.2": {c: cfg_total(b2_rows(size), c) for c in CFGS}}
    for s in SCEN:
        rows = scenario_rows(s, size)
        out[s] = {c: cfg_total(rows, c) for c in CFGS}
        out[s]["by_system_base"] = L.by_system(cfg_rows(rows, "base"))
        out[s]["like_for_like_base"] = L.like_for_like(cfg_rows(rows, "base"))
    return out


def by_size() -> dict:
    return {sz: {k: {c: v[c] for c in CFGS} for k, v in scenario_table(sz).items()} for sz in SIZES}


def step_deltas(size: str = "M") -> dict:
    st = steps(size)
    return {k: {c: cfg_total(st[k], c) for c in CFGS} for k in ORDER}


# =====================================================================================================================
# configs added to the ledger basis (task 1)
# =====================================================================================================================
def configs(size: str = "M") -> dict:
    """Ledger-schema row sets (``system, name, g, cfg, source``), each a whole pack at belt ``size``:
    corrie_f_base / corrie_f_as_hunted: CORRIE F (D2, team-B fabrics) on H1 with the P corrections, today's suspension;
    bl005_back / bl006_belt / bl007_a / bl007_c: CORRIE B.2 on H1 (base) with that one ticket's package."""
    st = steps(size)
    b2 = b2_rows(size)
    corr = [r for k in ORDER if k in L.CORRECTIONS for r in st[k]]
    with rev():
        f_rows = b2 + corr + corrie_f_step(size, "B", "corrie_f")
    HD = _HD()
    belt = [_r("belt", f"BL-006 {k}", HD._mass_delta(k, size), "base", f"hipbelt_diet._mass_delta('{k}')", "bl006")
            for k in HD.PACKAGE if k != "e"]                 # e = the holster cfg move, already in the BL-008 tags
    out = {"corrie_f_base": cfg_rows(f_rows, "base"), "corrie_f_as_hunted": cfg_rows(f_rows, "as_hunted"),
           "bl005_back": cfg_rows(b2 + st["A_back"], "base"), "bl006_belt": cfg_rows(b2 + belt, "base")}
    for v in ("a", "c"):
        fx = fixed_torso(v)
        out[f"bl007_{v}"] = cfg_rows(b2 + [_r("frame", f"BL-007 ({v}) fixed torso, 19 in", fx["pack_delta_g"], "base",
                                              f"frame_fixed.frame_mass('{v}', 19)", "bl007")], "base")
    return out


# =====================================================================================================================
# leaders, like for like (BL-008 basis)
# =====================================================================================================================
# Published figures and inclusions: docs/research/published_weight_definitions.md section 2.1 (URL per figure there);
# the basis rule per leader is weight_configs_proposal.md section 4. External data, not design numbers.
LEADERS = [   # name, published g, (+ add-on items, - base items), note
    ("Stone Glacier Sky 5900 + Krux, M belt", 2308.0, (), ("hip_pocket", "hydration"), "no lid; SG sells hip pockets and sleeve"),
    ("Stone Glacier Sky 5900 + Xcurve, M belt", 2396.0, (), ("hip_pocket", "hydration"), "same basis"),
    ("Exo K4 5000 (bag + frame + lid)", 2637.0, ("pouch",), ("hip_pocket",), "lid in"),
    ("KUIU ICON 6 6000 full kit", 2790.0, (), (), "hip pockets supplied"),
    ("KUIU PRO 6000 full kit (secondary)", 2639.0, (), (), "incl. hip pouches"),
    ("Mystery Ranch Beartooth 85", 2812.0, ("pouch",), (), "inclusions not stated"),
    ("Mystery Ranch Metcalf 100 (secondary)", 2708.0, ("pouch",), (), "workbook 'full'"),
    ("Kifaru ARK + Absaroka", 2835.0, ("holster",), (), "sewn Nalgene pockets"),
    ("Seek Outside Unaweep 6300 (shipped)", 1673.0, ("pouch",), ("hip_pocket",), "24 in frame, lid, shelf"),
    ("Initial Ascent IA5K", 2722.0, ("pouch",), (), "frame, belt, straps, bag, lid"),
]


def _item(rows: list, key: str) -> float:
    """Mass of a like-for-like item in a row set (signed sums, so a REMOVED row nets out)."""
    def pick(r):
        n = r["name"]
        if key == "hip_pocket":
            return r["system"] == "belt" and "IMP-5L" in n
        if key == "hydration":
            return r["system"] == "bag_pockets" and "IMP-2" in n
        if key == "pouch":
            return r["cfg"] == "as_hunted" and (r["system"] == "pouch" or "pouch" in n and r["system"] == "straps_compression")
        if key == "holster":
            return r["cfg"] == "as_hunted" and "IMP-3" in n
        raise KeyError(key)
    return sum(r["g"] for r in rows if pick(r))


def like_for_like_leaders(size: str = "M") -> list:
    out = []
    sets = {"B.2": b2_rows(size), **{s: scenario_rows(s, size) for s in SCEN}}
    for name, g, add, sub, note in LEADERS:
        row = {"leader": name, "published_g": g, "add": list(add), "remove": list(sub), "note": note}
        for k, rows in sets.items():
            ours = cfg_total(rows, "base") + sum(_item(rows, a) for a in add) - sum(_item(rows, b) for b in sub)
            row[k] = {"ours_g": round(ours, 1), "delta_g": round(ours - g, 1), "pct": round(100 * (ours / g - 1), 0)}
        out.append(row)
    return out


# =====================================================================================================================
# 6.6 lb: what it would cost in features; estimates and their uncertainty
# =====================================================================================================================
FEATURE_CANDIDATES = [   # (row-name needle, system, what the hunter loses, frozen?) - only base rows of CORRIE F
    ("IMP-2", "bag_pockets", "hydration sleeve (SG sells it separately)", False),
    ("FP-L/R", "bag_pockets", "hip-reach pockets (the BL-002 access fix for the sheep-load 2nd bottle)", False),
    ("IMP-5L", "belt", "hipbelt pocket (SG, Exo, Seek sell them separately)", False),
    ("IMP-4", "bag_pockets", "kill-kit / first-aid door pocket", False),
    ("IMP-6", "harness", "shoulder-strap phone pocket", False),
    ("B-11 lash", "bag_shell", "lash tabs + muzzle keepers (rifle carry)", False),
    ("E-5", "bag_pockets", "pole quiver (trekking pole / tripod leg carry)", False),
    ("IMP-8", "bag_pockets", "bow cam / limb cup (bow carry: owner-frozen)", True),
    ("US-", "straps_meat", "under-straps (owner-frozen)", True),
]


def feature_costs(size: str = "M") -> dict:
    rows = cfg_rows(scenario_rows(SCEN[-1], size), "base")
    base = cfg_total(rows, "base")
    need = base - TARGET_G
    items = []
    for needle, system, what, frozen in FEATURE_CANDIDATES:
        g = sum(r["g"] for r in rows if r["system"] == system and needle in r["name"])
        items.append({"item": needle, "what": what, "g": round(g, 1), "frozen": frozen})
    free = sorted([i for i in items if not i["frozen"]], key=lambda i: -i["g"])
    acc, take = 0.0, []
    for i in free:
        if acc >= need:
            break
        acc += i["g"]
        take.append(i["item"])
    HD = _HD()
    reserve = sum(HD._mass_delta(k, size) for k in HD.NEXT_LEVER)
    return {"after_tests_base_g": base, "gap_g": round(need, 1), "candidates": items,
            "all_unfrozen_g": round(sum(i["g"] for i in free), 1), "greedy_take": take, "greedy_g": round(acc, 1),
            "reaches": acc >= need, "belt_foam_reserve_g": round(reserve, 1),
            "with_reserve_g": round(sum(i["g"] for i in free) - reserve, 1),
            "reaches_with_reserve": sum(i["g"] for i in free) - reserve >= need}


UNC_CLASSES = [   # (class, test on name+source, +- fraction) - ASSUMPTION bands, each settled by weighing the part
    ("typed ASSUMPTION (no record, no drawing)", lambda t: "assumption" in t, 0.30),
    ("printed PAHT-CF body (2 mm raster x density)", lambda t: "printed body" in t or "raster" in t or "cheek" in t
     or "h1 body" in t, 0.05),
    ("frame lumps and carbon (beam model, frame_mass json)", lambda t: "frame_mass" in t or "crown" in t or "carbon" in t
     or "pack5200" in t or "frame_fixed" in t or "pawl" in t, 0.10),
    ("cut area x record gsm, length x record g/m", lambda t: True, 0.08),
]


def estimates(scen: str = "A", size: str = "M", cfg: str = "base") -> dict:
    """Every row of a scenario is computed, none weighed: band each row by its source class (ASSUMPTION bands) and add
    the bands two ways (worst case and root-sum-square). Also the single estimates >= 5 g that are typed ASSUMPTIONs."""
    net: dict = {}
    for r in cfg_rows(scenario_rows(scen, size), cfg):      # net out removed / re-added copies of the same part
        n = r["name"]
        for pre in ("REMOVED (B.2): ", "REMOVED: ", "CORRIE F: "):
            n = n.replace(pre, "")
        k = (r["system"], n)
        if k in net:
            net[k]["g"] += r["g"]
        else:
            net[k] = dict(r, name=n)
    rows = [r for r in net.values() if abs(r["g"]) > 0.05]
    cls = {c[0]: {"g": 0.0, "band_g": 0.0, "rss2": 0.0, "n": 0, "frac": c[2]} for c in UNC_CLASSES}
    named = []
    for r in rows:
        t = (r["name"] + " " + r["source"]).lower()
        c = next(c for c in UNC_CLASSES if c[1](t))
        b = abs(r["g"]) * c[2]
        d = cls[c[0]]
        d["g"] += r["g"]
        d["band_g"] += b
        d["rss2"] += b * b
        d["n"] += 1
        if c[0].startswith("typed") and abs(r["g"]) >= 5.0:
            named.append({"name": r["name"][:90], "g": r["g"], "band_g": round(b, 1)})
    worst = sum(d["band_g"] for d in cls.values())
    rss = sum(d["rss2"] for d in cls.values()) ** 0.5
    return {"scenario": scen, "cfg": cfg, "total_g": cfg_total(rows, cfg),
            "classes": {k: {"g": round(v["g"], 1), "band_g": round(v["band_g"], 1), "n": v["n"], "frac": v["frac"]}
                        for k, v in cls.items()},
            "worst_g": round(worst, 1), "rss_g": round(rss, 1), "named": sorted(named, key=lambda x: -abs(x["g"]))}


RISKS = [   # mass that is not in any scenario but may arrive, each from code
    ("BL-010 front-strap pad pair, booked only if HB-1 fails", lambda: __import__(
        "huntkit.gendesign.loadpath_check", fromlist=["x"]).front_pad()["g_pair"]),
]


def risks() -> list:
    return [{"what": w, "g": round(f(), 1)} for w, f in RISKS]


# =====================================================================================================================
# charts
# =====================================================================================================================
COL = {"P": "#4f6b4a", "A": "#b0793a", "O": "#5b6f8f", "correction": "#9a9a9a", "rule": "#c9c9c9"}


def plot_waterfall(path: Path, size: str = "M") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    st = step_deltas(size)
    b2 = scenario_table(size)["B.2"]
    lab, val, kind, bottoms = [], [], [], []
    run = b2["meat_trip"]
    bars = [("CORRIE B.2 on H1\n(ledger, all items)", run, "total", 0.0)]
    rule = b2["base"] - b2["meat_trip"]
    bars.append(("BL-008 rule: add-ons\nout of base (no saving)", rule, "rule", run))
    run += rule
    for sc in SCEN:
        for k in ORDER:
            m = STEP_META[k]
            if m[0] != sc:
                continue
            d = st[k]["base"]
            kd = "correction" if m[3] == "correction" else sc
            bars.append((f"{m[1]}: {m[2]}", d, kd, run))
            run += d
        bars.append((f"= {SCEN_NAME[sc].upper()}", run, "total_" + sc, 0.0))
    fig, ax = plt.subplots(figsize=(8.6, 13.0), dpi=100)
    n = len(bars)
    for i, (t, d, k, b) in enumerate(bars):
        y = n - 1 - i
        if k.startswith("total"):
            c = COL.get(k.split("_")[-1], "#333333") if "_" in k else "#333333"
            ax.barh(y, d, color=c, height=0.72)
            ax.text(d + 15, y, f"{d:.0f} g  {d / LB:.2f} lb", va="center", fontsize=9, fontweight="bold")
        else:
            lo, w = (b + d, -d) if d < 0 else (b, d)
            ax.barh(y, w, left=lo, color=COL[k], height=0.62)
            ax.text(max(b, b + d) + 12, y, f"{d:+.1f}", va="center", fontsize=8)
        ax.text(1985, y, t, va="center", ha="right", fontsize=7.6)
    ax.axvline(TARGET_G, color="#b22222", lw=1.6, ls="--")
    ax.text(TARGET_G + 6, -1.9, "6.6 lb target (base) 2994 g", color="#b22222", fontsize=8, va="bottom")
    lead = [g for _, g, *_ in LEADERS]
    ax.axvspan(min(g for g in lead if g > 2000), max(lead), color="#7a7a7a", alpha=0.12)
    ax.text(min(g for g in lead if g > 2000) + 6, n - 3.5, "leaders' published\nsystems 2308-2835 g\n(Seek 1673 g "
            "off-chart)", fontsize=7.4, ha="left", va="top", color="#555")
    ax.set_xlim(2000, 4650)
    ax.set_ylim(-2.0, n)
    ax.set_yticks([])
    ax.set_xlabel("pack mass, base configuration, belt M (g)")
    fig.suptitle("Weight roll-up v2, 2026-11-12: B.2 on H1 to proven now and after tests\n(base, belt M; CORRIE F rev 1, "
                 "H1 body 800.7 g)", x=0.02, ha="left", fontsize=11, fontweight="bold")
    ax.legend(handles=[Patch(color=COL["correction"], label="booking correction (no design change)"),
                       Patch(color=COL["P"], label="proven now"), Patch(color=COL["A"], label="after tests")],
              loc="upper center", fontsize=8, frameon=False,
              bbox_to_anchor=(0.45, -0.045), ncol=2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def plot_leaders(path: Path, size: str = "M") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = like_for_like_leaders(size)
    fig, ax = plt.subplots(figsize=(8.6, 11.0), dpi=100)
    keys = [("published", "#7a7a7a", "leader, published"), ("B.2", "#3b3b3b", "ours: CORRIE B.2 on H1"),
            ("P", COL["P"], "ours: proven now"), ("A", COL["A"], "ours: after tests")]
    h = 0.16
    for i, r in enumerate(rows):
        y0 = len(rows) - 1 - i
        for j, (k, c, _) in enumerate(keys):
            g = r["published_g"] if k == "published" else r[k]["ours_g"]
            y = y0 + (1.5 - j) * h
            ax.barh(y, g, height=h * 0.92, color=c)
            if k in ("published", "A"):
                ax.text(g + 15, y, f"{g:.0f}" + ("" if k == "published" else f"  ({r[k]['delta_g']:+.0f}, {r[k]['pct']:+.0f} %)"),
                        va="center", fontsize=7)
        basis = "base" + "".join(f" + {a}" for a in r["add"]) + "".join(f" - {b}" for b in r["remove"])
        ax.text(20, y0 + 3 * h + 0.02, f"{r['leader']}   [ours = {basis}]", fontsize=7.6, va="bottom")
    ax.axvline(TARGET_G, color="#b22222", lw=1.4, ls="--")
    ax.text(TARGET_G + 8, len(rows) - 0.35, "6.6 lb (target applies to base)", color="#b22222", fontsize=7.5)
    ax.set_yticks([])
    ax.set_xlim(0, 4500)
    ax.set_ylim(-0.6, len(rows) + 0.1)
    ax.set_xlabel("g, each pair on the leader's inclusions (BL-008 like-for-like basis), belt M")
    ax.set_title("Like for like against the leaders", loc="left", fontsize=11, fontweight="bold")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=l) for _, c, l in keys], loc="upper center", fontsize=8, frameon=False,
              bbox_to_anchor=(0.5, -0.05), ncol=3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


# =====================================================================================================================
# report
# =====================================================================================================================
def _lb(g):
    return f"{g / LB:.2f} lb"


def _lboz(g):
    lb = int(abs(g) // LB)
    return f"{'-' if g < 0 else ''}{lb} lb {(abs(g) - lb * LB) / OZ:.1f} oz"


def _bl011_headline(size: str) -> float:
    with rev():
        return _F().pack_with_adopted(size)["base"]["with_adopted_g"]


def compute(size: str = "M") -> dict:
    t = scenario_table(size)
    st = step_deltas(size)
    fx = {v: fixed_torso(v) for v in ("a", "c")}
    cfgs = configs(size)
    return {
        "date": "2026-11-12", "ticket": "BL-013, revised by BL-023, brought up to date 2026-11-12", "size": size, "corrie_f_rev": CORRIE_F_REV, "kit": KIT, "target_g": round(TARGET_G, 1),
        "scenarios": t, "by_size": by_size(),
        "steps": {k: {"class": STEP_META[k][0], "ticket": STEP_META[k][1], "label": STEP_META[k][2],
                      "kind": STEP_META[k][3], "gate": STEP_META[k][4], "delta_g": st[k],
                      "rows": [{kk: r[kk] for kk in ("system", "name", "g", "cfg", "source")} for r in steps(size)[k]]}
                  for k in ORDER},
        "configs": {k: {"total_g": L.total(v), "by_system": L.by_system(v), "like_for_like": L.like_for_like(v)}
                    for k, v in cfgs.items()},
        "corner_wraps": corner_wraps(), "non_body": non_body_sources(),
        "crown_kits_by_torso_size": {z: {"(a)+(d2)": crown("(a)+(d2)", z), "(a)+(d2)+(c17 bore 19)":
                                         crown("(a)+(d2)+(c17 bore 19)", z)} for z in ("S", "M", "L")},
        "fixed_torso": {v: {"pack_delta_g": round(d["pack_delta_g"], 1), "frame_g": d["frame_g"],
                            "fatigue_old_basis": round(d["fatigue_old_basis"], 3)} for v, d in fx.items()},
        "leaders": like_for_like_leaders(size), "features": feature_costs(size),
        "bl011_headline_base_g": _bl011_headline(size),
        "h1_fatigue": h1_fatigue(), "h1_body": L.h1_body_update(),
        "cheek_cross_check": {"frozen_pair_28_g": round(cheek_g(), 2),
                              "raster_g": round(L.h1_body_update()["im3_cheek_28_g"], 2)},
        "estimates": {s: estimates(s, size) for s in SCEN}, "risks": risks(),
    }


def report(res: dict, shots: list) -> str:
    t, st, sz = res["scenarios"], res["steps"], res["size"]
    P, A, B2 = t["P"], t["A"], t["B.2"]
    tg = res["target_g"]
    fc = res["features"]
    hb = res["h1_body"]
    L_ = []
    w = L_.append
    w("# Whole-pack weight roll-up, version 2 (BL-013, revised by BL-023, brought up to date 2026-11-12)\n")
    w("Owner: pack-designer (BL-013, 2026-11-12 update); revision: manufacturing-engineer (BL-023). Date: 2026-11-12. "
      "Code: `designs/pack_5200/weight_rollup_v2.py` (tests `tests/test_weight_rollup_v2.py`); numbers: "
      "`analysis/weight_rollup_v2.json`. Every mass below is a ledger row (`huntkit.mass.ledger`, config "
      "`corrie_b2_h1`, plus the C1-C8 and H1B corrections that the ledger holds as config `corrie_b2_h1_v2`) or a row "
      f"produced by the named ticket's own code, called live. CORRIE F is booked at rev {CORRIE_F_REV} (BL-022), door "
      "D2. **Do not quote the numbers from this file after the code changes: re-run it.**\n")
    w("**2026-11-12 changes (everything adopted since BL-013 / BL-023, DECISIONS rows of 2026-11-12):** "
      f"(1) **H1 body {hb['booked_g']} -> {hb['body_g']:.1f} g** ({hb['name']}), booked in the ledger as correction H1B "
      f"from `analysis/h1_buckling.json`: BL-024 grow-only offset {hb['bl024_g']:+.1f} g, BL-027 buckling members "
      f"{hb['bl027_members_g']:+.1f} g, BL-021 28 mm IM3 cheeks {hb['im3_cheek_28_g']:+.1f} g (as rastered into the "
      "body). (2) The separate cheek step (27 mm, +6.80 g) is gone: the 28 mm cheek is inside the H1B raster. "
      "(3) **CORRIE F rev 1** (BL-022: B-25 guy bridle, B-26 tripod keeper), door D2. (4) **Retired, booked in no "
      "scenario:** BL-017 OD 17 legs and BL-007 fixed torso (both below 1.0 on the cloth-sim loads, BL-021); the "
      "'owner options' scenario held only the fixed torso and is dropped. Wings, hood and IM2 hooks stay deleted in "
      "after tests (owner decisions 2026-11-11 / 2026-11-12); proven now still books them, because each deletion "
      "passes only after a named test with the part as its fallback (BL-014 S1). (5) The fabric swaps stay in after "
      "tests.\n")
    w("## 0. Answer\n")
    w(f"| Belt {sz}, crown kit {res['kit']} | base | as hunted | meat trip |")
    w("|---|---:|---:|---:|")
    w(f"| CORRIE B.2 on H1 (ledger start) | {B2['base']:.1f} ({_lb(B2['base'])}) | {B2['as_hunted']:.1f} | {B2['meat_trip']:.1f} |")
    for k in SCEN:
        v = t[k]
        w(f"| **{SCEN_NAME[k]}** | **{v['base']:.1f} ({_lb(v['base'])}, {_lboz(v['base'])})** | {v['as_hunted']:.1f} "
          f"({_lb(v['as_hunted'])}) | {v['meat_trip']:.1f} ({_lb(v['meat_trip'])}) |")
    w(f"| target (base) | {tg:.1f} (6.60 lb) | | |\n")
    w(f"- **6.6 lb is not reachable with what is adopted or under test.** Proven now misses it by "
      f"**{P['base'] - tg:.0f} g**, after tests by **{A['base'] - tg:.0f} g**.")
    w(f"- Closing the last {fc['gap_g']:.0f} g would take deleting or moving to add-ons: "
      + ", ".join(f"{c['item']} ({c['g']:.0f} g)" for c in fc["candidates"] if c["item"] in fc["greedy_take"])
      + f" = {fc['greedy_g']:.0f} g. " + ("That reaches it" if fc["reaches"] else
      f"Even every unfrozen candidate ({fc['all_unfrozen_g']:.0f} g) does not reach it")
      + (f"; only with the belt-foam reserve on top ({fc['with_reserve_g']:.0f} g in all) does it, i.e. a pack with "
         "no pockets, no hip-reach access, no hydration sleeve and a softer belt" if fc["reaches_with_reserve"] else
         f"; with the belt-foam reserve on top ({fc['with_reserve_g']:.0f} g in all) it is still short")
      + "; see section 5.")
    h = res["bl011_headline_base_g"]
    w(f"- The BL-011 headline (`corrie_f.pack_with_adopted`, rev {CORRIE_F_REV}: base {h:.0f} g) is {h - P['base']:+.0f} g "
      f"against proven now and {h - A['base']:+.0f} g against after tests: it takes the gated BL-005/006 items and the "
      "fabric swaps as done, leaves package C out, books the H1 body at 757.7 g and has the ledger's booking errors in "
      "it (section 2).\n")
    w("## 1. Rules\n")
    w("- **Start:** ledger `corrie_b2_h1`, belt M, every item booked: "
      f"{B2['meat_trip']:.1f} g. BL-008 tags (owner-adopted 2026-11-10): add-ons (top pouch, scope pod, IMP-3 holster, "
      "rain fly) are as hunted; float links B-24 and the meat liner are meat trip. Taking the add-ons out of base is a "
      "reporting rule, not a saving; it is its own grey bar in the waterfall.")
    w("- **Proven now (P):** PASS verdicts with no open decision gate, plus every booking correction and safety "
      "addition. **After tests (A):** BL-014's rule: a change gated by a named test, where failing the test sends the "
      "part back to a known heavier part, is in A even when its fallback is known (BL-014 S1); its safety hardware "
      "(BL-010) stays in P (ASSUMPTION: conservative, settled when the gate passes). A scenario includes the one "
      "before it (P, then P + A). **Retired (R):** not adopted; in no scenario.")
    w("- DECISION: a named test that can only add mass (the H1 release tests MT-1 / CA-1 / T1 / T2, the IM3 eye pull and "
      "coupon, the lifter protractor check, HB-7 lock slip) does not move a change out of P: there is no lighter "
      "outcome to wait for. BL-014 notes that the S15 elbow-swing check does have a fallback shell (S16 / CORRIE); "
      "CORRIE F's shell is kept in P here because P_F also carries today's fabrics and every part a failed gate would "
      f"restore (P_F is {st['P_F']['delta_g']['base']:+.1f} g on base: moving the whole of it to A would make proven "
      f"now {P['base'] - st['P_F']['delta_g']['base']:.1f} g). The owner's wing removal has its own field test FT-S2 "
      f"with a known fallback (the wing parts), so the wing saving ({-st['A_wings']['delta_g']['base']:.1f} g) is in "
      f"A, and P carries the wing parts. If FT-S2, PT-1 / TL-1 / LL-H were treated as first-article verification of "
      f"owner decisions, proven now would be "
      f"{P['base'] + st['A_wings']['delta_g']['base'] + st['A_att']['delta_g']['base']:.1f} g.")
    w("- CORRIE F is door D2 (orchestrator call 2026-11-11), rev 1 (BL-022). P uses today's fabrics on CORRIE F's "
      "pieces; A adds the swaps (owner swatch + strip test). P books the B-25 bridle even with the hood fallback "
      f"(conservative, {_F().guy_bridle()['mass_g']:.1f} g).\n")
    w("## 2. Steps (belt M; base / as hunted / meat trip deltas, g)\n")
    w("| # | class | ticket | change | base | as hunted | meat trip | gate (test or check) |")
    w("|---|---|---|---|---:|---:|---:|---|")
    for k in ORDER:
        s = st[k]
        d = s["delta_g"]
        w(f"| {k} | {SCEN_NAME[s['class']]} | {s['ticket']} | {s['label']} ({s['kind']}) | {d['base']:+.1f} | "
          f"{d['as_hunted']:+.1f} | {d['meat_trip']:+.1f} | {s['gate']} |")
    w("")
    w("### 2.1 Ledger clean-ups, each resolved against the source files (now ledger rows, BL-023)\n")
    cw, nb = res["corner_wraps"], res["non_body"]
    w(f"- **C1 fairleads (49.4 g): double-booked, removed.** `frame_branch.frame_sdf` adds "
      "`bag_attach.attachment_field` (the 8 fairleads) to the body SDF, so the 823.2 g production raster and the 757.7 g "
      "H1 raster (`frame_comp_d.restore_hardpoints`, `frame_h1.md` section 4: 'bag fairleads (8) 100 % present') "
      "already hold them; 823.2 - 774.3 (study body without fairleads) = 48.9 g matches. The ledger's attachment row "
      "came from `bag_attach._mass_budget`, the added mass of the same features.")
    w("- **C2 swell patches (12.3 g): booked twice, removed.** `bag_attach` booked the 8 swells as 2-ply 200 gsm "
      "patches (ASSUMPTION there); CORRIE books the same 8 swells as cut piece B-13x (14.4 g, 'replaces the cone "
      "caps'). B-13x stays.")
    w(f"- **C3 crown-corner wraps: {cw['wraps_g']:.1f} g wraps + gussets and {cw['adhesive_g'] - cw['booked_line_g']:.1f} g "
      f"bond, unbooked, added ({cw['unbooked_g']:.1f} g).** `frame_eval.REPLACED_G` drops all of frame.yaml's "
      "'carbon wraps + gussets' (64.6 g) and 'adhesive' as replaced by the printed body, but the two crown corners "
      "stay carbon. Their share comes from `pack5200.hardware_mass` run with and without the crown_corner joints; the "
      f"rev C 0.8 mm line already booked ({cw['booked_line_g']} g) is taken off. Cross-check: `frame_light2.py` "
      "books 'crown corner wraps + 0.8 mm bondline' at 24.0 + 2.21 g.")
    w("- **C4 POM pawl housing (8.0 g): double-booked, removed.** The printed body forms the pawl housing and cheeks "
      "(`frame_branch.frame_sdf` 'pawl housing bulge'; `print/frame/PRODUCTION.md` step 2: pin through the printed "
      "cheeks in 304 sleeves, booked separately at 9.94 g). The 14 g 'pawl housing + spring + Ti pawl' row is "
      "8 g housing + 6 g pawl and spring (`crown_diet` ASSUMPTIONs); BUILD_PLAN's 'POM housing' is from the tube frame. "
      "ASSUMPTION settled by weighing the pawl + spring.")
    w(f"- **C5 non-body lump: {nb['short_g']:.1f} g short, added.** `frame_mass_production.non_body_g` = generative "
      "frame_g - body_g - 202.6 g (`spreader_results.old_part_g`: QI sheet + M4 sets). frame_g held the sheet but not "
      f"the M4 sets, so the lump is below its own sources: KEPT_G + pawl bushings + inserts = {nb['sources_g']:.1f} g "
      f"against {nb['lump_g']} g. Open: the 12 g inserts ASSUMPTION also names 'rod/dowel bond, joint bolts', which H1 "
      "books separately (Ti M5 set); up to a few grams may still be double (estimate list).")
    w("- **C6 lifter keepers (6.0 g): moved attachment -> harness** (bag_attach: 'lifter backup'); no total change; "
      "the bag side gets 6 g lighter on the like-for-like split.")
    w("- **C7 IMP-3 holster tabs (2.2 g): base.** The two wing tabs stay sewn to the belt (`hipbelt_diet.holster_split`); "
      "BL-011 had the whole 38.8 g holster in as hunted.")
    w("- **C8 old 50 mm belt strap and the under-booked 25 mm 2:1 webbing: re-booked** (`hipbelt_diet.closure`, BL-006 "
      "a2): 0.9 m 50 mm strap -> two 140 mm buckle tabs; 25 mm webbing 0.6 -> 1.20 m. Net -12.7 g at M.")
    cc = res["cheek_cross_check"]
    w(f"- **H1B H1 body ({hb['steps_sum_g']:+.1f} g), a ledger correction since 2026-11-12.** `frame_mass_h1.json` still "
      f"books BL-007's {hb['booked_g']} g H1 raster; `ledger.h1_body_update()` reads `h1_buckling.json` `chosen` and "
      f"adds three signed rows: BL-024 {hb['bl024_g']:+.2f}, BL-027 members {hb['bl027_members_g']:+.2f}, 28 mm IM3 "
      f"cheeks {hb['im3_cheek_28_g']:+.2f} g (sum {hb['steps_sum_g']:.2f} g on the {hb['booked_g']} g base; the json's "
      f"own raster total is {hb['body_g']:.2f} g). The cheek is the 28 mm cheek mask minus the body it overlaps; the "
      f"stand-alone fairlead volume (`loadpath_check.FROZEN`, 18 -> 28 mm, both sides) is {cc['frozen_pair_28_g']:.1f} "
      "g, so up to the difference may be printed mass the 2 mm raster does not see (estimate list).")
    w("- **Package C was missing from BL-011's pack.** The ledger books it as config `corrie_b2_h1_c` (7075 plate "
      "-25.0 g; C-4 pad backer +8.1 g and C-7 yoke +8.5 g, both fixes for parts that fail rev C as released). It is "
      "adopted (DECISIONS 2026-11-09) and in P here.\n")
    w("## 3. Scenarios by belt size (crown kit M; base / as hunted / meat trip, g)\n")
    w("| belt | B.2 | proven now | after tests |")
    w("|---|---|---|---|")
    for z, v in res["by_size"].items():
        f = lambda k: f"{v[k]['base']:.0f} / {v[k]['as_hunted']:.0f} / {v[k]['meat_trip']:.0f}"  # noqa: E731
        w(f"| {z} | {f('B.2')} | {f('P')} | {f('A')} |")
    w("")
    ck = res["crown_kits_by_torso_size"]
    w("Crown kit by torso size (change against H1, g): " + "; ".join(
        f"{z}: kits {v['(a)+(d2)']:+.1f}" for z, v in ck.items())
      + ". Kit S is lighter and kit L heavier than the M figures used above (today's 16 x 8 legs; the OD 17 legs are "
      "retired).\n")
    w("### 3.1 Base by system (belt M)\n")
    w("| system | B.2 base | proven now | after tests |")
    w("|---|---:|---:|---:|")
    b2s = L.by_system(cfg_rows(b2_rows(sz), "base"))
    for s in L.SYSTEMS:
        w(f"| {s} | {b2s[s]:.1f} | {P['by_system_base'][s]:.1f} | {A['by_system_base'][s]:.1f} |")
    w("")
    w("Like-for-like split (BL-001 groups, base): " + "; ".join(
        f"{SCEN_NAME[k]} bag side {t[k]['like_for_like_base']['bag_side']:.0f} g, suspension "
        f"{t[k]['like_for_like_base']['suspension']:.0f} g" for k in SCEN) + ".\n")
    w("## 4. Against the leaders (BL-008 like-for-like basis)\n")
    w("Leader figures and inclusions: `docs/research/published_weight_definitions.md` section 2.1 (a URL on every "
      "figure there); the basis rule per leader: `weight_configs_proposal.md` section 4.\n")
    w("| leader | published g | our basis | B.2 | proven now | after tests |")
    w("|---|---:|---|---:|---:|---:|")
    for r in res["leaders"]:
        basis = "base" + "".join(f" + {a}" for a in r["add"]) + "".join(f" - {b}" for b in r["remove"])
        cell = lambda k: f"{r[k]['ours_g']:.0f} ({r[k]['delta_g']:+.0f}, {r[k]['pct']:+.0f} %)"  # noqa: E731
        w(f"| {r['leader']} | {r['published_g']:.0f} | {basis} | {cell('B.2')} | {cell('P')} | {cell('A')} |")
    lo = min(r["A"]["delta_g"] for r in res["leaders"] if r["published_g"] > 2000)
    hi = max(r["A"]["delta_g"] for r in res["leaders"] if r["published_g"] > 2000)
    w(f"\nAfter tests, we are {lo:+.0f} to {hi:+.0f} g against the framed leaders (Seek Outside excluded: a 1.7 kg "
      "system is another class).\n")
    w("## 5. Is 6.6 lb (2994 g, base) reachable?\n")
    w(f"**No.** The lightest scenario is {min(P['base'], A['base']):.0f} g. Gap after tests: "
      f"**{fc['gap_g']:.0f} g ({fc['gap_g'] / OZ:.1f} oz)**.\n")
    w("What closing it would cost in features (CORRIE F base rows; frozen features cannot be traded, RULES.md rule 9):\n")
    w("| item | g | what the hunter loses | owner-frozen |")
    w("|---|---:|---|---|")
    for c in sorted(fc["candidates"], key=lambda c: -c["g"]):
        w(f"| {c['item']} | {c['g']:.1f} | {c['what']} | {'yes' if c['frozen'] else 'no'} |")
    w(f"\n- Taking the largest unfrozen items first: {', '.join(fc['greedy_take'])} = {fc['greedy_g']:.0f} g "
      + ("reaches 6.6 lb only by stripping the pack of its pockets and hip-reach access." if fc["reaches"] else
         f"does not reach it; all unfrozen candidates together are {fc['all_unfrozen_g']:.0f} g.")
      + (f" With the belt-foam reserve as well, {fc['with_reserve_g']:.0f} g against the {fc['gap_g']:.0f} g gap: "
         + ("6.6 lb is reached only by deleting every one of these features and softening the belt." if
            fc["reaches_with_reserve"] else "still short.")))
    w(f"- Not in any scenario: the belt-foam reserve (BL-006 d2 + d4, {fc['belt_foam_reserve_g']:+.1f} g, gated by HB-1 "
      "and a compression-set check). On its own it does not close the gap.")
    fxa, fxc = res["fixed_torso"]["a"], res["fixed_torso"]["c"]
    w(f"- Retired, not booked: BL-007 fixed torso ((a) {fxa['pack_delta_g']:+.1f} g against H1 on its own, "
      f"{st['O_fixed']['delta_g']['base']:+.1f} g once the kits it replaces are undone) and the BL-017 OD 17 legs "
      f"({st['A_c17']['delta_g']['base']:+.1f} g). Both fall below fatigue 1.0 on the cloth-sim loads (BL-021 (4), "
      "0.97-0.99), so neither is a lever.")
    w("- The lever the 6.6 lb target needs is on the frame side (BL-008: frame side about double the leaders'), "
      f"which no open ticket reaches: after tests the suspension is {A['like_for_like_base']['suspension']:.0f} g.\n")
    w("## 6. Estimates and uncertainty\n")
    w("Nothing in the roll-up has been weighed. Each row is banded by its source class. The bands are ASSUMPTIONs, "
      "settled by weighing every part of prototype 1 on a 0.1 g scale against its ledger row.\n")
    w("| scenario (base) | total g | typed ASSUMPTION | printed body | frame lumps / carbon | area x gsm, records | worst case | RSS |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in SCEN:
        e = res["estimates"][k]
        c = list(e["classes"].values())
        w(f"| {SCEN_NAME[k]} | {e['total_g']:.0f} | " + " | ".join(
            f"{x['g']:.0f} +- {x['band_g']:.0f} ({x['frac']:.0%})" for x in c) + f" | +- {e['worst_g']:.0f} | +- {e['rss_g']:.0f} |")
    w("\nSingle typed ASSUMPTION masses >= 5 g in after tests (base):\n")
    w("| row | g | band g |")
    w("|---|---:|---:|")
    for n in res["estimates"]["A"]["named"]:
        w(f"| {n['name']} | {n['g']:.1f} | {n['band_g']:.1f} |")
    w("\nOther open estimates:\n")
    w(f"- IM3 fairlead cheek 28 mm: booked inside the H1B raster at {cc['raster_g']:.1f} g; the stand-alone "
      f"fairlead volume is {cc['frozen_pair_28_g']:.1f} g a pair, so up to {cc['frozen_pair_28_g'] - cc['raster_g']:+.1f} g "
      "may be unbooked (ASSUMPTION: the raster overlap is right; settled by weighing the two printed halves against "
      "the slicer).")
    pr = json.loads((ANALYSIS / "h1_buckling.json").read_text())["print"]
    pm = pr["lower"]["g"] + pr["upper"]["g"]
    w(f"- H1 body on the 2 mm raster ({hb['body_g']:.1f} g); BL-027's print halves (lower {pr['lower']['g']} g, upper "
      f"{pr['upper']['g']} g, `h1_buckling.json` print) are {pm - hb['body_g']:+.1f} g against the raster, as BL-007's "
      "H1 mesh was heavier than its raster; the ledger keeps the raster basis for every body (ASSUMPTION MESH, "
      "h1_buckling.md; settled by weighing the printed halves).")
    for r in res["risks"]:
        w(f"- Risk not in any scenario: {r['what']}: +{r['g']:.1f} g.")
    w("- Misc (thread ~3 % of soft goods, ASSUMPTION in geometry.yaml) is kept at the B.2 figure; the lighter bag "
      "would trim it by a few grams.")
    w("- Crown kit masses are for kit M (torso 17.5-20.5 in); belt sizes S-XXL keep kit M (torso and belt are separate).\n")
    w("## 7. Configs added to the ledger basis (task 1)\n")
    w("`weight_rollup_v2.configs(size)` returns ledger-schema rows; `ledger.total / by_system / like_for_like` take them. "
      "BL-023 folded the C1-C8 corrections into `huntkit/mass/ledger.py`, and the H1 configs carry H1B since "
      "2026-11-12 (configs `corrie_b2_today_v2`, `corrie_b2_h1_v2`, `corrie_b2_h1_c_v2`; `DEFAULT_CONFIG` = "
      "`corrie_b2_h1_v2`; the BL-001 names stay unchanged). The design configs below are still roll-up row sets; "
      "bl007_a / bl007_c are retired designs, kept for reference.\n")
    w("| config | total g (belt M) | bag side | suspension |")
    w("|---|---:|---:|---:|")
    for k, v in res["configs"].items():
        w(f"| {k} | {v['total_g']:.1f} | {v['like_for_like']['bag_side']:.1f} | {v['like_for_like']['suspension']:.1f} |")
    w("\n## 8. Screenshots\n")
    for s in shots:
        w(f"- `{s}`")
    w("")
    return "\n".join(L_)


def _j(o):
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(type(o))


def write() -> dict:
    res = compute("M")
    s1 = plot_waterfall(SCREENS / f"{PREFIX}1.png")
    s2 = plot_leaders(SCREENS / f"{PREFIX}2.png")
    DOC_SCREEN.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copyfile(s1, DOC_SCREEN)
    shots = [str(DOC_SCREEN.relative_to(ROOT)), str(s1.relative_to(ROOT)), str(s2.relative_to(ROOT))]
    res["screenshots"] = shots
    RESULT.write_text(json.dumps(res, indent=1, default=_j))
    DOC.write_text(report(res, shots))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    t = scenario_table("M")
    for k in ("B.2",) + SCEN:
        print(f"{k:5s}", {c: t[k][c] for c in CFGS})
    if a.write:
        res = write()
        print(DOC, RESULT, *res["screenshots"])


if __name__ == "__main__":
    main()
