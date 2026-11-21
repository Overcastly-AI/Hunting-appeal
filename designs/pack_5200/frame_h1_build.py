"""BL-054: the H1 frame build package for a beginner (manufacturing-engineer, 2026-11-13).

    python designs/pack_5200/frame_h1_build.py            # write print/frame_h1/README.md, BUILD_H1.md, drawings
    python designs/pack_5200/frame_h1_build.py --check    # build in memory, print the checks, write nothing

Writes, into ``designs/pack_5200/print/frame_h1/``:

* ``README.md``  : what is in the folder, the status and what to read (regenerated; replaces the hand-written one, which
  pointed at ``../frame/PRODUCTION.md``, DO NOT PRINT, and carried stale masses, footprints and cheek sizes: review 5
  M-7);
* ``BUILD_H1.md``: the one ordered build path: gates, print (supports, BL-053), clean-up, anneal, weigh, ream, joints,
  fairlead pins, pawl, hip inserts, crown with the spine clamp and the B-25 sleeves, first-article checks;
* ``drawings/spine_clamp_7075.pdf|.png|.dxf``: the machined spine clamp (``crown_spine_clamp`` constants).

Every number is read at run time: STL masses and footprints from the meshes (density from the material record), joint
hardware from ``frame_h1.JOINT`` / ``h1_bedfit.JOINT``, pins from ``h1_lanes`` / ``bag_attach``, the clamp from
``crown_spine_clamp.size_clamp``, crown kits from ``crown_diet``, op numbers from the bag release op list, and the
print plan from the BL-053 JSON when it exists (clearly marked placeholders until then). Units mm, g, N internally;
inches / oz / lb shown next to them.
"""
from __future__ import annotations

import argparse
import csv
import functools
import json
import re
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRINT = HERE / "print" / "frame_h1"
TP_DIR = PRINT / "test_pieces"
DRAW = PRINT / "drawings"
AN = HERE / "analysis"
OPS_CSV = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "manufacturing" / "op_sequence.csv"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261121_BL059build"     # BL-059: named for the ticket that regenerates the package (was 20261121_BL057build)
IN = 25.4
OZ = 28.3495
MAT_PRINT = "pa12_cf_fdm_paht"
RATE_MM3_S = 8.0                 # print time basis of the H1 records: volume / 8 mm3/s + 8 % waste (README BL-049..051)
WASTE = 0.08
SUPPORT_EXTRA = (0.15, 0.25)     # review 5 B-1 fix 2: "add about 15-25 % on the filament line" (interim, BL-053 replaces)
MASS_BAND = (-0.03, 0.04)        # ASSUMPTION MASS-BAND: as-printed body within -3 / +4 % of the STL mass x density
PLACEHOLDER = "**[PLACEHOLDER BL-053]**"
MOUNT_SEAT_N = 20.0              # ASSUMPTION MOUNT-SEAT: hand push on the mount's pin end (seating check only)


def _hip_c2_pin_n() -> float:
    """BL-060: the C2 pin load the MOUNT-SEAT text compares against, read from the BL-056 part FE
    (analysis/hip_mount_bl056.json fe.rows['C2|H_pin'].V_n), never typed."""
    return float(json.loads((AN / "hip_mount_bl056.json").read_text())["fe"]["rows"]["C2|H_pin"]["V_n"])


_C2_PIN_N = _hip_c2_pin_n()

ASSUMPTIONS = {
    "MASS-BAND": ("The printed, cleaned, annealed and unreamed body weighs the STL volume x 1.06 g/cm3 within -3 / +4 % "
                  "(100 % infill; the band covers flow calibration and support scars). Over +4 % = over-extrusion; under "
                  "-3 % = gaps or wet filament.", "Weigh P1 and P2 (BUILD_H1 step 6); the engineer resets the band."),
    "SLEEVE-BOND": ("The 304 pawl sleeves (OD 8.0) go into the bore reamed to 8.0 with a thin film of the frame's MMA "
                    "(adhesive_methacrylate_ma), not a press fit: an 8.0 reamer gives no interference (review 5 M-7).",
                    "Pawl dry fit + 100 release cycles; the sleeve does not turn under a 4 mm pin twisted by hand."),
    "PIN-SLEEVE": ("One UHMWPE sleeve per cheek (2 per station, 24 per frame), as long as the cheek is thick (hinge 10, "
                   "the rest 8 mm), slip fit in the 7.2 mm reamed eye hole and held by the pin; the webbing eye rides on "
                   "the bare pin between the cheeks. This is what bag_attach.pin_check books (bearing over 2 x the cheek, "
                   "sleeve volume over 2 x the cheek); the bag BOM's '12 sleeves' counted pairs.",
                   "Pack-designer confirms (OWNER / pack-designer decision); HE-FIT step 3 slides the eye on the pin."),
    "FRAME-AS-JIG": ("The crown is bonded on the printed frame itself (legs in their bushings at the 15 in setting, the "
                     "spine in its channel), so the spine axis lands where the channel puts it (crown_spine_clamp "
                     "SPINE-AXIS) without a separate jig; PTFE tape keeps MMA off the print.",
                     "Dry fit of the crown on P1 before any bond: the spine slides the full channel with the clamp on."),
    "PAWL-PIN": ("The pawl pin is a 4 mm stainless pin, length = the cheek bosses' outer faces (2 x the measured x +/-"
                 "24.8) rounded up to 50 mm, retained by one E-clip (DIN 6799, for a 4 mm shaft) in a groove at each end "
                 "outside the sleeves. Sleeves 8 x 4.2 x 8 (h1_pawl BORE_REAM_D, PRODUCTION op 2).",
                 "Pawl dry fit: the pin turns freely in both sleeves; no end play over 0.5 mm."),
    "HIP-INSERTS": ("The Ti hip mount fixes to the printed hip boss with M5 brass heat-set inserts in the pattern BL-055 "
                    "Part A sized (h1_closeout.json: count, positions, printed pilot holes; insert pull-out 1200 N "
                    "(record ASSUMPTION) x the PAHT-CF hot knock-down x the layer-normal ratio). Buy 2 spares.",
                    "Insert pull-out coupon HB-6 (test kit) and the D-I1 coupon."),
    "MOUNT-SEAT": (f"A {MOUNT_SEAT_N:.0f} N hand push on the mount's pin end (about {100 * MOUNT_SEAT_N / _C2_PIN_N:.0f} % of "
                   f"the {_C2_PIN_N:.0f} N C2 pin load, hip_mount_bl056.json part FE, C2 row with H on the pin) is a seating check "
                   "only: it finds a mount resting on a burr or an insert standing proud, not strength.",
                   "HB-6b hip-mount proof on the frame (hip_mount_bl056.md 6, FLANGE-RIGID; test kit) carries the "
                   "strength."),
    "HIP-HEAT": ("Inserts go in with the iron at 290 C (the PAHT-CF nozzle temperature): hot enough to melt the wall "
                 "round the knurl without a blob; the insert record gives no install temperature.",
                 "HB-6 practice blocks: each insert flush within 0.2 mm, square (an M5 screw stands upright), no bulge "
                 "on the far face; pull-out per HB-6."),
    "SLM-MASS": ("The SLM Ti hip mount as delivered (HIPed, supports off, base faced, pin bore reamed) weighs the "
                 "redrawn STL volume x 4430 kg/m3 (ledger BL056) within +/- 5 %: more = support left on, less = "
                 "porosity or a short build.", "Weigh the first mount on arrival; the engineer resets the band."),
    "RACK-CUT": ("The printed rack (print/crown_rack_fdm_pacf, 230 mm) is cut to the kit's spine length minus the clamp "
                 "socket (15 mm) and bonded to the spine tube's fore face with MMA, teeth fore, as frame.yaml 'crown spine "
                 "tube (rack bonded on)'. Kit S's spine (173 mm) needs a cut rack.",
                 "Crown dry fit: the pawl engages the rack over the kit's whole torso range."),
}


# ================================================================================ sources
def material(rid: str):
    from huntkit.materials import load
    return load(rid)


def rho_print() -> float:
    """g/mm3 of the print material (record density)."""
    return float(material(MAT_PRINT).require("density_kg_m3")) * 1e-6


def _ops_index() -> dict:
    """op id key (title before ':') -> seq, from the bag release op list (m-2: op numbers read, never typed)."""
    if not OPS_CSV.exists():
        return {}
    out = {}
    with open(OPS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["operation"].split(":")[0].strip(), r["seq"])
    return out


def op_no(key: str) -> str:
    return _ops_index().get(key, f"[op {key}: not in the op list]")


def stl_table() -> list[dict]:
    """Every print file: mass at the record density, as-written extents (x, y, z on the plate), watertight, shells."""
    import trimesh
    rho = rho_print()
    files = [("h1_lower_flat", "lower half", "PAHT-CF"), ("h1_upper_flat", "upper half", "PAHT-CF"),
             ("us2_clevis_R", "US2 clevis, right", "PAHT-CF"), ("us2_clevis_L", "US2 clevis, left", "PAHT-CF"),
             ("crown_pawl_lp_fdm_pacf", "low-profile pawl (P1 prototype)", "PAHT-CF"),
             ("h1_assembled", "whole frame as assembled (checks only, do not print)", "-"),
             ("test_pieces/hefit_hinge_fairlead_R", "test piece HE-FIT / PT-3 / SEW-F", "PAHT-CF"),
             ("test_pieces/us_route_stay_R", "test piece US ROUTE / CLEVIS-SHARE", "PAHT-CF"),
             ("test_pieces/im3ec_cheek_R", "test piece IM3-EC", "PAHT-CF"),
             ("test_pieces/hip_insert_guide", "hip insert-setting guide (BL-058; a tool, print it)", "PAHT-CF")]
    out = []
    for f, what, mat in files:
        p = PRINT / f"{f}.stl"
        if not p.exists():
            continue
        m = trimesh.load(p)
        e = [float(v) for v in m.extents]
        out.append({"file": f, "what": what, "material": mat, "volume_mm3": float(m.volume),
                    "mass_g": round(float(m.volume) * rho, 1), "extents_mm": [round(v, 1) for v in e],
                    "watertight": bool(m.is_watertight),
                    "hours_no_support": round(float(m.volume) * (1 + WASTE) / RATE_MM3_S / 3600.0, 1)})
    return out


_MASS: dict = {}


def piece_mass_g(f: str) -> float:
    """Mass of one print file (``f`` relative to print/frame_h1, no extension) at the record density, cached."""
    if f not in _MASS:
        import trimesh
        _MASS[f] = round(float(trimesh.load(PRINT / f"{f}.stl").volume) * rho_print(), 1)
    return _MASS[f]


def bl053_paths() -> list[Path]:
    """BL-053's data (structural-fea-engineer, ``huntkit/gendesign/h1_rev5.py``): the print settings JSON and the
    review-5 results JSON, when they land. Searched in the print folder and the analysis folder."""
    out = []
    for d in (PRINT, AN):
        for pat in ("print_settings*.json", "h1_rev5*.json", "*bl053*.json"):
            out += [p for p in sorted(d.glob(pat)) if p not in out]
    return out


def bl053() -> dict:
    """Merged BL-053 data: {'print_settings': {...}, 'h1_rev5': {...}, '_path': 'a, b'} or {} before it lands."""
    d = {}
    for p in bl053_paths():
        try:
            v = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        d[p.stem] = v
    if d:
        d["_path"] = ", ".join(str(p.relative_to(ROOT)) for p in bl053_paths())
    return d


def clamp() -> dict:
    """The spine clamp as sized (crown_spine_clamp.size_clamp) + limit loads for the T6(c) coupon pass line."""
    from huntkit.gendesign import crown_spine_clamp as C
    rows = C.joint_loads()
    s = C.size_clamp(rows)
    lim_n = max(abs(r["spine"][0]) for r in rows)                      # limit axial force on the socket
    lim_t = max(abs(r["jump"][3]) for r in rows) / 1000.0               # limit torque jump on the saddle (N m)
    from huntkit.gendesign.h1_spine_channel import CLAMP_WEB_GAP, CLAMP_WEB_H
    s.update({"limit_spine_axial_n": round(lim_n, 0), "limit_bar_torque_nm": round(lim_t, 1),
              "web_h_mm": CLAMP_WEB_H, "web_gap_mm": CLAMP_WEB_GAP, "web_t_mm": C.WEB_T_MM,
              "saddle_id_mm": C.BAR_OD + 2 * C.BONDLINE_MM, "socket_id_mm": C.SPINE_OD + 2 * C.BONDLINE_MM,
              "bar_od_mm": C.BAR_OD, "spine_od_mm": C.SPINE_OD})
    return s


def crown_kits() -> dict:
    from huntkit.gendesign import crown_diet as CD
    sp = CD.specs()
    return {k[-1]: {"torsos": sp[k].torsos, "leg_mm": sp[k].leg_mm, "spine_mm": sp[k].spine_mm,
                    "bushing_mm": sp[k].bushing_mm} for k in ("a_S", "a_M", "a_L")}


def pins() -> dict:
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign import h1_lanes as LN
    hp = LN.hinge_pin()
    hc = hp[hp["chosen"]]
    n = len(BA.stations())
    g = BA.HINGE_GEOM
    gi = BA.eye_geom("us1")                       # BL-045: every IM / US fairlead has the 20 mm throat, 8 mm cheeks
    span_im = gi.throat + 2 * gi.cheek
    return {"stations": n, "hinge_len_mm": hc["length_mm"], "hinge_d_mm": hc["pin_d_mm"], "hinge_g": hc["mass_g"],
            "hinge_sf_yield": hc["sf_yield"], "hinge_sf_fat": hc["sf_fatigue"], "hinge_cheek_mm": g.cheek,
            "hinge_span_mm": g.throat + 2 * g.cheek, "im_cheek_mm": gi.cheek, "im_span_mm": span_im,
            "hole_d_mm": BA.HOLE_D, "pin_d_mm": BA.PIN_D, "n_al": n - 2}


# ================================================================================ BL-055 Part A data (close-out)
CLOSEOUT_JSON = AN / "h1_closeout.json"   # structural-fea-engineer, huntkit/gendesign/h1_closeout.py (BL-055 Part A)
PENDING = "**[PENDING BL-055 Part A]**"
TI = "ti_6al_4v"
MAT_NAME = {"ti_6al_4v": "Ti-6Al-4V", "alu_7075_t6": "7075-T6"}


def _find(d, pred):
    """First dict in a nested JSON (depth first) for which ``pred`` is true."""
    if isinstance(d, dict):
        if pred(d):
            return d
        for v in d.values():
            r = _find(v, pred)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _find(v, pred)
            if r is not None:
                return r
    return None


def closeout() -> dict:
    """BL-055 Part A results (``analysis/h1_closeout.json``), {} before they land. Returned keys: ``pins`` (the 12 pin
    rows with the US1 pins in Ti: h1_closeout.pins), ``hip`` (the chosen insert pattern with its check:
    h1_closeout.hip_check), ``hip_screw`` (the mount screw), ``raw`` and ``_path``. The JSON is searched by shape, not
    by a fixed key path, so a re-arranged report still reads."""
    if not CLOSEOUT_JSON.exists():
        return {}
    try:
        d = json.loads(CLOSEOUT_JSON.read_text())
    except (OSError, ValueError):
        return {}
    pins_ = _find(d, lambda x: isinstance(x.get("stations"), dict) and isinstance(x.get("bom"), list))
    hip = _find(d, lambda x: isinstance(x.get("pattern"), dict) and "positions_xz" in x["pattern"] and "min_sf" in x)
    scr = _find(d, lambda x: isinstance(x.get("hip_screw"), str))
    return {"pins": pins_ or {}, "hip": hip or {}, "hip_screw": (scr or {}).get("hip_screw"),
            "insert": _find(d, lambda x: "pullout_n" in x and "hole_d" in x) or {},
            "flange": _find(d, lambda x: "t_mm" in x and "holes" in x and "hole_d_mm" in x) or {},
            "raw": d,
            "_path": str(CLOSEOUT_JSON.relative_to(ROOT)) if CLOSEOUT_JSON.is_relative_to(ROOT) else str(CLOSEOUT_JSON)}


def pin_rows(co: dict | None = None) -> dict:
    """The pin rows the build uses: BL-055's (US1 in Ti) when published, else BL-053's (h1_rev5.json pins)."""
    co = closeout() if co is None else co
    if co.get("pins"):
        return co["pins"]
    return rev5().get("pins", {})


def pin_groups(pr: dict) -> dict:
    """{'Ti-6Al-4V': [(station, qty, row), ...], '7075-T6': [...]} from the pin rows."""
    out: dict = {}
    for name, r in pr.get("stations", {}).items():
        out.setdefault(MAT_NAME.get(r["material"], r["material"]), []).append((name, r["qty"], r))
    return out


def hip_rel(pat: dict) -> list[tuple]:
    """Insert positions relative to the boss centre: (x mm, + = R; z mm, + = up) as a beginner marks them."""
    from huntkit.gendesign.h1_closeout import HIP_C        # the boss axis (frame x, z)
    cx, cz = pat.get("centre_xz") or HIP_C
    return [(round(x - cx, 1), round(z - cz, 1)) for x, z in pat["positions_xz"]]


def joints() -> tuple:
    from huntkit.gendesign.frame_h1 import JOINT as Z
    from huntkit.gendesign.h1_bedfit import JOINT as C
    return Z, C


def pawl() -> dict:
    from huntkit.gendesign import h1_pawl as HP
    return {"bore_print": HP.BORE_PRINT_D, "bore_ream": HP.BORE_REAM_D, "pivot_hole": HP.PIVOT_D_PIN,
            "boss_x": 24.8, "pin_len": 50.0}   # boss |x| 11-24.8 (crown_gnl.md 5 table, measured); ASSUMPTION PAWL-PIN


def fmm(v: float, nd: int = 1) -> str:
    return f"{v:.{nd}f} mm ({v / IN:.2f} in)"


def fg(v: float) -> str:
    return f"{v:.1f} g ({v / OZ:.2f} oz)"


# ================================================================================ test-piece print text (kit)
# review 5 B-1 table, measured on the STLs by the reviewer (plate contact, share of the footprint overhanging > 45 deg);
# replaced by the BL-053 per-piece plan when it lands
PIECE_CONTACT = {"hefit_hinge_fairlead_R": ("about 29 mm2", "77 %"), "us_route_stay_R": ("about 10 mm2", "79 %"),
                 "im3ec_cheek_R": ("23 % of its footprint", "most of the rest"), "us2_clevis_R": ("94 %", "little")}
PROFILE_TXT = ("PAHT-CF dried 80 C (176 F) 10-12 h, hardened 0.6 mm nozzle at 290 C, bed 100 C, chamber heater 50-60 C, 0.20 mm "
               "layers, 6 walls, 6 top / bottom layers, 100 % infill, 8 mm brim, loaded as the file is written (do not "
               "rotate)")
SUPPORT_TXT = ("tree supports FROM THE BUILD PLATE under the whole piece, in PAHT-CF, top Z distance 0.20-0.25 mm, 2-3 "
               "interface layers, 45 deg threshold, support blockers painted inside every bore, pin hole, bolt hole, "
               "counterbore and nut trap. After printing break the supports off, sand the scars flush ALONG the stay")


NUT_STD = "DIN 934"           # review 6 M-1 (orchestrator call): m = 4.0 mm; ISO 4032 M5 is 4.4-4.7 mm and does not fit
NUT_T_TOL = 0.1               # caliper limit = trap nut length + 0.1 mm (inside the trap's 0.2 mm nut play, h1_bedfit)


def nut_txt(C) -> str:
    """HW-M5-NUT spec (review 6 M-1): read the nut size from the joint code, the standard from NUT_STD."""
    return (f"M5 hex nut A2, {NUT_STD}, m = {C.nut_t:.1f} mm, {C.nut_af:.0f} AF (NOT ISO 4032, which is 4.4-4.7 mm "
            "thick and does not fit the trap)")


def nut_check_txt(C) -> str:
    return (f"CHECK each nut with the caliper before it goes in: thickness <= {C.nut_t + NUT_T_TOL:.1f} mm "
            f"({(C.nut_t + NUT_T_TOL) / IN:.3f} in); a thicker nut is the wrong standard, set it aside")


def bolt_window(C) -> tuple[float, float] | None:
    """BL-058 BOLT-LEN: the caliper window for the screw of joint ``C``. US2 (M5 x 35): read from bl058.json
    kit.nut.bolt_caliper (34.7-35.3 mm: a long one bottoms in the 0.5 mm tail room, a short one ends < 0.6 pitch past
    the nut). z 234: the ISO 4759-1 length tolerance of BOLT-LEN (nut_check.bolt_len_tol_mm), which nut_check shows is
    safe at both ends there (tail room and tip past the nut both > 0). None before BL-058."""
    b8 = bl058()
    if not b8:
        return None
    nc = b8["nut_check"]
    rows = [r for r in nc["rows"] if r["bolt"].startswith(f"M5 x {C.bolt_len:.0f} ")]
    m = re.search(rf"M5 x {C.bolt_len:.0f}\b.*?(\d+\.\d+)-(\d+\.\d+) mm", b8["kit"]["nut"]["bolt_caliper"])
    if m:
        return float(m.group(1)), float(m.group(2))
    assert rows and all(r["tail_clear_long_bolt_mm"] > 0 and r["seat"]["DIN 934"]["tip_past_nut_short_bolt_mm"] > 0
                        for r in rows), C.bolt_len
    t = nc["bolt_len_tol_mm"]
    return C.bolt_len - t, C.bolt_len + t


def bolt_check_txt(C) -> str:
    """BUILD_H1 7.2 / 8.2 (BL-058 BOLT-LEN): caliper every screw of this joint under the head before it goes in."""
    w = bolt_window(C)
    if not w:
        return ""
    rows = [r for r in bl058()["nut_check"]["rows"] if r["bolt"].startswith(f"M5 x {C.bolt_len:.0f} ")]
    tail = min(r["tail_clear_nominal_mm"] for r in rows)
    tip = min(r["seat"]["DIN 934"]["tip_past_nut_nominal_mm"] for r in rows)
    return (f" CHECK each M5 x {C.bolt_len:.0f} screw with the caliper too, under the head to the tip: **{w[0]:.1f}-"
            f"{w[1]:.1f} mm** ({w[0] / IN:.3f}-{w[1] / IN:.3f} in; ASSUMPTION BOLT-LEN). The nominal screw leaves "
            f"{tail:.1f} mm to the end of the tail hole and ends {tip:.1f} mm past the nut (bl058.json nut_check); "
            "outside the window set it aside")


def chamber_txt() -> str:
    """Chamber temperature for the long PAHT-CF prints (review 6 m-5): the material record's chamber_temp_c as the
    low end, the record note's 60 C as the top."""
    lo = float(material(MAT_PRINT).require("chamber_temp_c"))
    hi = 60.0                 # pa12_cf_fdm_paht note: 'enclosure (chamber 45-60 C)'
    return (f"chamber closed with the chamber heater on, {lo:.0f}-{hi:.0f} C ({lo * 1.8 + 32:.0f}-{hi * 1.8 + 32:.0f} F) "
            f"for the 18-21 h halves (record {MAT_PRINT} chamber_temp_c {lo:.0f}, note 45-60 C)")


def ps() -> dict:
    """BL-053's print settings (``print/frame_h1/print_settings_bl053.json``), {} before it lands."""
    return bl053().get("print_settings_bl053", {})


def rev5() -> dict:
    """BL-053's results (``analysis/h1_rev5.json``), {} before it lands."""
    return bl053().get("h1_rev5", {})


CLEVIS56_JSON = AN / "clevis_bl056.json"     # BL-056 (structural-fea-engineer): US2 joint blocks re-printed
HIP56_JSON = AN / "hip_mount_bl056.json"     # BL-056: the Ti hip mount redrawn on the 8-insert boss
SLM_MASS_TOL = 0.05                          # ASSUMPTION SLM-MASS (see ASSUMPTIONS)
MASS_TOL_G = 0.06                            # STL mass here vs the BL-056 JSON: same mesh, same density, rounding only


def bl056() -> dict:
    """BL-056 results: {'clevis': clevis_bl056.json, 'hip': hip_mount_bl056.json, 'mount_g': ledger} or {} before."""
    if not (CLEVIS56_JSON.exists() and HIP56_JSON.exists()):
        return {}
    from huntkit.mass import ledger
    return {"clevis": json.loads(CLEVIS56_JSON.read_text()), "hip": json.loads(HIP56_JSON.read_text()),
            "mount_g": ledger.bl056_update()["mount_g"],
            "_path": f"{CLEVIS56_JSON.relative_to(ROOT)}, {HIP56_JSON.relative_to(ROOT)}"}


BL058_JSON = AN / "bl058.json"               # BL-058 (structural-fea-engineer): review 6 frame / hardware fixes


@functools.lru_cache(maxsize=None)
def bl058() -> dict:
    """BL-058 results (``analysis/bl058.json``: kit.nut / hip_screw / pins_bom / PIN-RET_d / FIT-US_marks / hip_guide,
    hip_mount, stl, mass, head_check, sleeve_bearing, assumptions), {} before it lands."""
    if not BL058_JSON.exists():
        return {}
    return json.loads(BL058_JSON.read_text())


def mount_g() -> float:
    """The SLM Ti hip mount mass the build books: ledger BL056 mount_g + ledger BL058 mount_delta_g (the D5.8 holes),
    checked against the STL mass BL-058 published (bl058.json hip_mount.mass_g)."""
    from huntkit.mass import ledger
    g = ledger.bl056_update()["mount_g"]
    if bl058():
        g = round(g + ledger.bl058_update()["mount_delta_g"], 2)
        assert abs(g - bl058()["hip_mount"]["mass_g"]) <= MASS_TOL_G, (g, bl058()["hip_mount"]["mass_g"])
    return g


def mass_check(stl: list[dict]) -> dict:
    """The STL-measured masses of this folder against the latest published ones: BL-058's (bl058.json stl) when on
    file, else BL-056's (clevis_bl056.json mass; BL-057). {file: (stl g, json g, ok)}."""
    by = {r["file"]: r for r in stl}
    out = {}
    b8 = bl058()
    if b8:
        for f, v in b8["stl"].items():
            k = f if f in by else f"test_pieces/{f}"
            if isinstance(v, dict) and "g" in v and k in by:
                out[k] = (by[k]["mass_g"], v["g"], abs(by[k]["mass_g"] - v["g"]) <= MASS_TOL_G)
        return out
    b = bl056()
    if not b:
        return {}
    for f, v in b["clevis"]["mass"].items():
        if isinstance(v, dict) and f in by:
            out[f] = (by[f]["mass_g"], v["g"], abs(by[f]["mass_g"] - v["g"]) <= MASS_TOL_G)
    return out


def ps_file(piece: str) -> dict:
    """BL-053 per-file print row for one file stem (keys there are 'test_pieces/x.stl' or 'a.stl / b.stl')."""
    for k, v in ps().get("files", {}).items():
        if any(Path(n.strip()).stem == Path(piece).stem for n in k.split("/ ") + k.split(" / ")):
            return v
    return {}


def piece_print_txt(piece: str, short: bool = False) -> str:
    """One sentence a beginner can follow for printing one test piece (kit HE-FIT / PT-3 / SEW-F / US ROUTE /
    CLEVIS-SHARE / IM3-EC), from BL-053's per-file support plan (print_settings_bl053.json) when it is on file,
    else the review 5 B-1 interim rule (marked). No ';' in the text: the kit splits steps on it."""
    f = ps_file(piece)
    if f:
        on = f"{f['plate_contact_mm2']:.0f} mm2"
        ov = f"{f['supported_down_area_mm2']:.0f} mm2 needs support"
        src = "BL-053 print_settings_bl053.json"
        fil = f", filament about {f['filament_g_est']:.0f} g, about {f['print_h_est']:.1f} h"
    else:
        on, ov = PIECE_CONTACT.get(piece, ("?", "?"))
        ov = f"{ov} overhangs more than 45 deg"
        src = "review 5 B-1 interim"
        fil = ""
    flat_piece = piece.startswith("us2_clevis") or (f and str(f.get("supports", "")).startswith("none"))
    if short:
        if flat_piece:
            return ("frame profile of BUILD_H1.md section 3, NO supports (it prints flat), blockers in the holes, "
                    f"annealed 90 C 6 h{fil}")
        return (f"frame profile of BUILD_H1.md section 3 with SUPPORTS REQUIRED (it touches the plate over only {on}, "
                f"{src}): tree supports from the build plate in PAHT-CF, blockers in every bore, pin hole, bolt hole and "
                f"trap, scars sanded flat (BUILD_H1 section 4){fil}"
                + ("" if f else f" ({PLACEHOLDER.strip('*')}: check BUILD_H1 section 10 first)"))
    if flat_piece:
        sup = (f"NO supports: it prints flat (plate contact {on}, {src}), blockers in the bolt holes and "
               "counterbores")
    else:
        sup = f"SUPPORTS REQUIRED (it touches the plate over only {on}, {ov}, {src}): {SUPPORT_TXT}"
        if not f:
            sup += f" ({PLACEHOLDER.strip('*')} per-piece orientation and supports: check BUILD_H1 section 10 first)"
    return (f"{PROFILE_TXT}. {sup}{fil}. Anneal 90 C (194 F) 6 h with the part on a flat plate, cool in the oven, "
            "then ream every hole as the frame (BUILD_H1 sections 7-9)")


# ================================================================================ text blocks
def _b53_print_section(b: dict, stl: list[dict]) -> list[str]:
    """Print settings + supports: from the BL-053 JSON when it exists, else the interim review B-1 rule, marked."""
    L = []
    if b:
        L += [f"Source: `{b['_path']}` (BL-053, structural-fea-engineer). The tables below are generated from it.", ""]
        L += _render_bl053(b)
        return L
    body = [r for r in stl if r["file"] in ("h1_lower_flat", "h1_upper_flat")]
    g_body = sum(r["mass_g"] for r in body)
    lo, hi = (round(g_body * (1 + WASTE) * (1 + x)) for x in SUPPORT_EXTRA)
    L += [f"> {PLACEHOLDER} The structural-fea-engineer is re-planning the orientation and supports (ticket BL-053, "
          "item 1: orientation per half and per test piece, support plan, filament and time, and whether support "
          "scars land on fatigue-critical faces). **Do not start a body print until this box is replaced by the "
          "BL-053 table.** Until then the rule below is the review's interim fix (review 5 B-1, fix 1), so you can "
          "set up the slicer profile and run the plate preview (step 3), nothing more.", "",
          "Interim support rule (review 5 B-1 fix 1; replaced by BL-053):", "",
          "| setting | value |", "|---|---|",
          "| support type | **tree supports from the build plate, under the whole body** (the stays start 16-30 mm "
          "(0.6-1.2 in) above the plate; only the lumbar hub / pawl housing touches it) |",
          "| support material | PAHT-CF itself (single nozzle) |",
          "| top Z distance | 0.20-0.25 mm (0.008-0.010 in) |",
          "| interface layers | 2-3 |",
          "| overhang threshold | 45 deg |",
          "| support blockers | inside every bore, pin hole, bolt hole, counterbore and nut trap (paint them in the "
          "slicer) |", "",
          f"Filament with supports (interim): body {g_body:.0f} g + 8 % waste + 15-25 % support = **{lo}-{hi} g "
          f"({lo / 453.6:.2f}-{hi / 453.6:.2f} lb)** for the two halves. {PLACEHOLDER} print time with supports.", ""]
    return L


def _flat(d, pre=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _flat(v, f"{pre}{k}.")
        else:
            yield f"{pre}{k}", v


def _render_bl053(b: dict) -> list[str]:
    """BL-053's print settings as beginner tables (print_settings_bl053.json schema)."""
    p = b.get("print_settings_bl053", {})
    if not p:
        return [f"{PLACEHOLDER} BL-053 results are on file but no print_settings_bl053.json yet.", ""]
    o, su = p["orientation"], p["supports"]
    tz = su["top_z_distance_mm"]
    L = ["Supports (BL-053, from `print/frame_h1/print_settings_bl053.json`):", "",
         "| setting | value |", "|---|---|",
         f"| orientation | {o['all_files']} |",
         f"| support type | **{su['type']}** |",
         f"| support material | {su['material']} |",
         f"| top Z distance | {tz[0]:.2f}-{tz[1]:.2f} mm ({tz[0] / IN:.3f}-{tz[1] / IN:.3f} in) |",
         f"| interface layers / spacing | {su['interface_layers']} / {su['interface_spacing_mm']} mm |",
         f"| support XY distance | {su['xy_distance_mm']} mm |",
         f"| brim | {su['brim_mm']:.0f} mm |",
         "| **support blockers (paint them BEFORE slicing)** | " + "; ".join(su["blockers"]) + " |", "",
         f"Why not flipped: {o['why_not_flipped']}.", "",
         f"Slicer warning: {su['note']}.", "",
         "Per file (support mass estimate and its high bound; time rule: " + p.get("time_rule", "") + "):", "",
         "| file | touches the plate | needs support under | part | support (high) | filament (high) | time | "
         "tallest support |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    live = {k: live_print_row(k, f) for k, f in p["files"].items()}
    for k, f in p["files"].items():
        v = live[k]
        L.append(f"| `{k}` | {f['plate_contact_mm2']:.0f} mm2 (flat face now {v['flat_mm2']:.0f}) | "
                 f"{f['supported_down_area_mm2']:.0f} mm2 | "
                 f"{v['part_g']:.1f} g | {f['support_g_est']:.1f} ({f['support_g_high']:.1f}) g | "
                 f"{v['fil_est']:.0f} ({v['fil_high']:.0f}) g | {v['h_est']:.1f} h | "
                 f"{f['max_support_column_mm']:.0f} mm ({f['max_support_column_mm'] / IN:.1f} in) |")
    tot = sum(live[k]["fil_high"] for k in p["files"] if "flat" in k)
    L += ["", "BL-057 (review 6 m-11): the part mass, filament and time columns are measured from the STL files in this "
          "folder now (part + BL-053's support estimate; time by BL-053's rule); 'flat face now' is the area of the "
          "part's flat underside on the plate, measured on the current mesh (the lower half now starts on the D50 "
          "hip boss face). The support columns are BL-053's voxel estimates for the BL-053 meshes.", "",
          f"The two halves together need up to **{tot:.0f} g ({tot / 453.6:.2f} lb)** of filament with supports "
          "(high bound).", ""]
    return L


def live_print_row(key: str, f: dict) -> dict:
    """One BL-053 print row re-measured on today's STL (review 6 m-11): part mass (record density), the flat
    underside on the plate (faces at the lowest z facing down), filament = part + BL-053 support estimate, time by the
    BL-053 rule (part + support) / 8 mm3/s x 1.08."""
    import trimesh
    stem = key.split(" / ")[0].strip().removesuffix(".stl")
    m = trimesh.load(PRINT / f"{stem}.stl")
    z0 = float(m.bounds[0][2])
    sel = (m.triangles_center[:, 2] < z0 + 0.05) & (m.face_normals[:, 2] < -0.99)
    part = float(m.volume) * rho_print()
    t = (part + f["support_g_est"]) / rho_print() / RATE_MM3_S * (1 + WASTE) / 3600.0
    return {"part_g": round(part, 1), "flat_mm2": round(float(m.area_faces[sel].sum()), 0),
            "fil_est": round(part + f["support_g_est"], 0), "fil_high": round(part + f["support_g_high"], 0),
            "h_est": round(t, 1)}


def b53_get(b: dict, *names, default=None):
    """First value found under any of ``names`` anywhere in the BL-053 JSON (flattened, key suffix match)."""
    if not b:
        return default
    flat = dict(_flat(b))
    for n in names:
        for k, v in flat.items():
            if k.split(".")[-1] == n or k.endswith(n):
                return v
    return default


# ================================================================================ README
def body_status_txt(co: dict) -> str:
    """README status line: the whole-body margins BL-055 Part A published (sanded body, every R1 basis; >= 1 passes)."""
    b8 = bl058().get("body", {}).get("bases", {})
    bs, tag, who = ((b8, "bl058_sanded", "BL-058, on the exported STL") if b8 else
                    ((co.get("raw") or {}).get("body", {}).get("bases", {}), "bl053_sanded", "BL-055 Part A"))
    if not bs:
        return f"- {PENDING} whole-body margins on the BL-053 print (Part A)."
    keys = ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")
    worst = {k: min((v.get(tag) or v.get(tag.removesuffix("_sanded")))[k] for v in bs.values()) for k in keys}
    low = {b_: v_[tag]["fatigue"] for b_, v_ in bs.items() if v_.get(tag, {}).get("fatigue", 9) < 1.0}
    return (f"- Whole body on this print, stays sanded 0.2 mm ({who}, lowest over the R1 bases, pass >= 1.00): "
            + ", ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in worst.items())
            + (". **Below 1.00:** " + ", ".join(f"fatigue {v:.2f} on basis {b_}" for b_, v in low.items())
               + " (the R1 rule holds the print for MT-1c / CA-1; see `analysis/"
               + ("bl058.json` body)." if b8 else "h1_closeout.md` 1).") if low else "."))


def readme_md(stl: list[dict], b: dict) -> str:
    by = {r["file"]: r for r in stl}
    rho = rho_print()                                   # sums from the volumes, rounded once (BL-059)
    body = sum(by[f]["volume_mm3"] * rho for f in ("h1_lower_flat", "h1_upper_flat") if f in by)
    cl = sum(by[f]["volume_mm3"] * rho for f in ("us2_clevis_R", "us2_clevis_L") if f in by)
    asm = by.get("h1_assembled", {}).get("mass_g", float("nan"))
    L = ["# H1 printed frame body: files (Pack 5200)", "",
         "Generated by `designs/pack_5200/frame_h1_build.py` (BL-054). **Do not edit by hand: re-run the script.** "
         "Every mass and size below is measured from the STL files in this folder at run time.", "",
         "**How to build it: [`BUILD_H1.md`](BUILD_H1.md)** (one ordered list, from the shopping list to the first-"
         "article checks). It replaces every older pointer to `../frame/PRODUCTION.md`: that folder is the "
         "superseded frame and says DO NOT PRINT FROM THIS FOLDER.", "",
         "H1 is the frame the owner adopted on 2026-11-10 (`docs/DECISIONS.md`): a branching PAHT-CF body split at "
         "z = 234 mm into two halves that are **bolted, not glued**, plus two bolt-on US2 clevises. Engineering "
         "records: `analysis/frame_h1.md`, `h1_lanes.md`, `h1_bedfit.md`, `h1_crown.md`, `crown_gnl.md`, "
         "`h1_spine_channel.md`. Code: `huntkit/gendesign/frame_h1.py`.", "",
         "## Status", "",
         "- **Engineering release candidate, not released.** Print the first article only after the coupons CA-1 "
         "(with the scar bars) and CA-5 pass, and the lower half only after HB-6 passes (its hip insert pilots are "
         "printed in; review 6 m-9) (`designs/pack_5200/tests_physical/CA1_fatigue_rig.md`, the test kit)"
         + (" and after the BL-053 print plan has replaced the placeholder in BUILD_H1 section 3." if not b else
            "; the print plan (orientation, supports, filament, time) is BL-053's, in BUILD_H1 section 3."),
         "- Review 5 (`analysis/review_20261113_fifth.md`) found the body files cannot be printed with the old "
         "\"no supports\" text (B-1). BL-053 owns the supports, cradle direction, nut traps, US1 root and pin "
         "retention; BL-055 Part A the whole-body re-run, the hip insert pattern and the Ti US1 pins; the "
         "manufacturing-engineer (BL-054 / BL-055 Part B) owns the build text.",
         f"- {('BL-053 data in use: `' + b['_path'] + '`.') if b else PLACEHOLDER + ' BL-053 data not yet published; marked placeholders in BUILD_H1.'}",
         body_status_txt(closeout()),
         f"- {('BL-055 Part A data in use: `' + closeout()['_path'] + '` (hip inserts, Ti US1 pins).') if closeout() else PENDING + ' BL-055 Part A (hip insert pattern, Ti US1 pins) not yet published; BUILD_H1 sections 9 and 12 carry pending boxes.'}",
         bl056_status_txt(stl),
         bl058_status_txt(stl),
         "",
         "## Files", "",
         "| file | what | mass | size as written on the plate (x, y, z) | watertight |", "|---|---|---:|---|---|"]
    for r in stl:
        e = r["extents_mm"]
        tmf = " / `.3mf`" if (PRINT / f"{r['file']}.3mf").exists() else ""
        L.append(f"| `{r['file']}.stl`{tmf} | {r['what']} | {fg(r['mass_g'])} | {e[0]:.1f} x {e[1]:.1f} x "
                 f"{e[2]:.1f} mm ({e[0] / IN:.1f} x {e[1] / IN:.1f} x {e[2] / IN:.1f} in) | {r['watertight']} |")
    L += ["| `crown_pawl_lp_slm.stl` / `.3mf` | low-profile pawl, Ti-6Al-4V SLM + HIP (production), 12 mm wide | "
          "bought SLM part | | |",
          "| `test_pieces/*_frame_coords.stl` | the test pieces in frame coordinates, for the slice checks (do not "
          "print) | | | |",
          "| `drawings/spine_clamp_7075.pdf` / `.png` / `.dxf` | machined 7075 spine clamp drawing (BL-054) | | | |", "",
          f"- Printed body (two halves): **{fg(body)}**, {body / 453.6:.2f} lb; with the two clevises "
          f"{fg(body + cl)}; `h1_assembled.stl` {fg(asm)} (the same parts, as assembled).",
          f"- Masses are the mesh volume x {rho_print() * 1e3:.2f} g/cm3 (`data/materials` `{MAT_PRINT}`), before "
          "support, brim and waste.",
          "- The lower half is written **already turned on the plate** (163.5 deg, BL-050): do not rotate it in the "
          "slicer unless BL-053 says so.",
          "- Superseded files one folder up (`../crown_pawl_fdm_pacf.*`, `../crown_pawl_slm.*`): the old pawl does "
          "**not** fit H1. The rack `../crown_rack_fdm_pacf.stl` is still the rack (BUILD_H1 step 13).", "",
          "## History (one line per revision; current numbers are in the table above)", "",
          "- BL-027: body H1-G0.55-B1/2.5 (thicker mid bar and upper branches, 28 mm IM3 cheeks).",
          "- BL-042 / BL-045: all 12 fairleads added whole, 20 mm throat, saddle with 45 deg underside.",
          "- BL-047: pawl pivot bore, cheek bosses, fore-wall window; low-profile pawl.",
          "- BL-049: hinge fairleads 10 mm cheeks x 36 mm tall, Ti-6Al-4V 5 x 44 hinge pin; US1 / US2 on their own "
          "lanes (x +/-70 and +/-165).",
          "- BL-050: US2 outer cheek is a bolt-on clevis; lower half turned on the plate.",
          "- BL-051: stay crown restored; clevis screw heads counterbored (M5 x 35).",
          "- BL-054: print README regenerated from the meshes; build path moved to BUILD_H1.md; spine clamp drawing.",
          "- BL-053: tree supports from the plate, hex nut traps, US1 / US2 lugs for a 40 mm cradle belly, headed pins "
          "with clips and tethers (the clips are BL-058's).",
          "- BL-055: " + ("hip boss with printed insert pilot holes (Part A pattern); US1 pins in Ti-6Al-4V; "
                          if closeout() else "") + "README / BUILD_H1 regenerated (Part B).",
          ("- BL-056: US2 joint blocks grown upward and the clevis nut face moved 1 mm inboard (CLEVIS-SHARE B now "
           "passes); the SLM Ti hip mount redrawn on the 8-insert boss. BL-057: README / BUILD_H1 regenerated."
           if bl056() else ""),
          ("- BL-058: DIN 934 nuts, a retainer per pin station (hairpin clips; US2 groove + E-clip + tether), US2 pin "
           "head counterbored into the clevises, hip screws shortened, mount holes opened, insert-setting guide. "
           "BL-059: README / BUILD_H1 regenerated from bl058.json." if bl058() else ""),
          ""]
    return "\n".join(L)


def bl056_status_txt(stl: list[dict]) -> str:
    """README status line for BL-056: the clevis / assembled masses from the STL, checked against clevis_bl056.json."""
    b = bl056()
    if not b:
        return ""
    blk = b["clevis"]["joint"]["block"]
    txt = (f"- BL-056 data in use: `{b['_path']}`. US2 joint blocks grown to z pin +{blk['upper_half_z_mm']:g} mm (was "
           f"+{blk['was_upper_mm']:g}), clevis nut face at x +/-{blk['nut_face_x_mm']:g} (was {blk['was_nut_face_x_mm']:g}; "
           f"nut trap {blk['trap_x0_mm']:g}-{blk['nut_face_x_mm']:g}).")
    if bl058():
        return txt
    mc = mass_check(stl)
    ok = all(v[2] for v in mc.values())
    parts = ", ".join(f"`{f}` {fg(v[0])} (JSON {v[1]:.2f} g, was {b['clevis']['mass'][f]['bl055_g']:.2f})"
                      for f, v in mc.items() if f in ("us2_clevis_R", "h1_assembled"))
    return (txt + f" Masses: {parts}; "
            + ("every STL mass here matches the JSON." if ok else "**STL MASS DIFFERS FROM THE JSON: ask the engineer.**"))


def bl058_status_txt(stl: list[dict]) -> str:
    """README status line for BL-058: what changed on the print and the hardware, the masses from the STL checked
    against bl058.json stl (BL-059 wiring)."""
    b8 = bl058()
    if not b8:
        return ""
    mc = mass_check(stl)
    ok = all(v[2] for v in mc.values())
    parts = ", ".join(f"`{f}` {fg(v[0])} (bl058.json {v[1]:.2f} g)" for f, v in mc.items()
                      if f in ("us2_clevis_R", "h1_assembled"))
    cb, bd = b8["cbore"], b8["body"]
    return (f"- BL-058 data in use: `{BL058_JSON.relative_to(ROOT)}`. US2 pin head D{cb['head_mm'][0]:g} x "
            f"{cb['head_mm'][1]:g} in a D{cb['d_mm']:g} x {cb['depth_mm']:g} counterbore cut into both clevises (head "
            f"{cb['recess_mm']:g} mm below the face); DIN 934 nuts; hairpin clips / US2 E-clip; hip screws "
            f"{b8['kit']['hip_screw']['spec']}; mount holes D{b8['hip_mount']['hole_d_mm']:g} with the printed insert "
            f"guide. Whole body re-run on this print: {body_line(bd)}. Masses: {parts}; "
            + ("every STL mass here matches bl058.json." if ok else "**STL MASS DIFFERS FROM bl058.json: ask the engineer.**"))


def body_line(bd: dict) -> str:
    """The whole-body margins BL-058 ran on the exported STL (bl058.json body, sanded), lowest over the static bases."""
    bs = bd.get("bases", {})
    keys = ("strength", "fatigue", "creep", "buckling")
    st = [v["bl058_sanded"] for k, v in bs.items() if "bl058_sanded" in v and not k.endswith(".cyc")]
    if not st:
        return "see `analysis/bl058.json` body"
    return ", ".join(f"{k} {min(r[k] for r in st):.2f}" for k in keys)


# ================================================================================ BUILD_H1
def pins_step3(pn: dict, pr: dict, co: dict) -> str:
    """BUILD_H1 9.3: which pin goes where, from the pin rows (BL-055 Part A: US1 in Ti, orchestrator call)."""
    gr = pin_groups(pr)
    if not gr:
        return (f"3. Pins: hinge (z 60) = **Ti-6Al-4V, {pn['hinge_d_mm']:.0f} x {pn['hinge_len_mm']:.0f} mm** "
                f"(**HW-PIN-TI**, 2). The other 10 = 7075-T6, 5 mm (**HW-PIN-AL**).")
    parts = []
    for mat, rows in sorted(gr.items(), key=lambda kv: kv[0] != "Ti-6Al-4V"):
        hid = "HW-PIN-TI" if mat == "Ti-6Al-4V" else "HW-PIN-AL"
        n = sum(q for _, q, _ in rows)
        each = ", ".join(f"{nm} (shank {r['shank_mm']} mm, {r['pin_g']:.2f} g)" for nm, _, r in rows)
        parts.append(f"**{mat}** (**{hid}**, {n}): {each}")
    why = []
    for nm, _, r in gr.get("Ti-6Al-4V", []):
        b = r.get("bending")
        if b:
            load = b.get("design_yz_n", b.get("row_n"))
            t = f"{nm}: bending SF {b['sf_yield']} yield / {b['sf_fatigue']} fatigue" + (f" on {load:.0f} N" if load else "")
            if "dy95_sf_fatigue" in b:
                t += f", {b['dy95_sf_yield']} / {b['dy95_sf_fatigue']} with the contact line 95 mm aft ({b['dy95_yz_n']:.0f} N)"
            if r.get("was"):
                wb = r["was"].get("bending") or {}
                t += (f" (in {MAT_NAME.get(r['was']['material'], r['was']['material'])}: "
                      f"{wb.get('sf_fatigue')} / {wb.get('dy95_sf_fatigue')} fatigue)")
            why.append(t)
    src = co.get("_path") or "analysis/h1_rev5.json pins (BL-053)"
    rt, ra = (float(material(m).require("density_kg_m3")) / 1000.0 for m in (TI, "alu_7075_t6"))
    txt = (f"3. Pins, all {pn['pin_d_mm']:.0f} mm, headed: " + "; ".join(parts) + f" (source `{src}`). "
           f"Keep the two kinds apart: a Ti pin weighs {rt / ra:.2f} x a 7075 pin of the same size ({rt:.2f} vs "
           f"{ra:.2f} g/cm3, material records), so CHECK each pin on a 0.01 g scale against its weight above "
           "(within 0.1 g) before it goes in.")
    if why:
        txt += " Why Ti: " + "; ".join(why) + "."
    if not co:
        txt += f" {PENDING} the US1 pins move to Ti-6Al-4V (orchestrator call); this list follows when Part A publishes."
    return txt


def us2_sleeve_mm() -> float | None:
    """BL-058 follow-up: the US2 outer cheek's sleeve length under the pin-head counterbore (bl058.json
    sleeve_bearing.bearing_now_mm = cbore.outer_cheek_bearing_mm), None before BL-058."""
    b8 = bl058()
    if not b8:
        return None
    L = float(b8["sleeve_bearing"]["bearing_now_mm"])
    assert abs(L - b8["cbore"]["outer_cheek_bearing_mm"]) < 1e-6
    return L


def sleeve_counts(pn: dict) -> list[tuple[float, int, str]]:
    """(length mm, count, where) of the UHMWPE pin sleeves: one per cheek (PIN-SLEEVE); BL-058 cuts the two US2 outer
    (clevis) sleeves to the counterbore floor."""
    n = pn["stations"]                        # 12 stations, 2 cheeks each
    L2 = us2_sleeve_mm()
    hinge = (pn["hinge_cheek_mm"], 4, "hinge cheeks")
    if L2 is None:
        return [hinge, (pn["im_cheek_mm"], 2 * n - 4, "every other cheek")]
    return [hinge, (pn["im_cheek_mm"], 2 * n - 6, "US1, IM1-IM3 and the US2 inner cheeks"),
            (L2, 2, "US2 OUTER (clevis) cheeks: the pin head's counterbore takes the rest")]


def sleeve_step_txt(pn: dict) -> str:
    sc = sleeve_counts(pn)
    return (f"2. Slide one UHMWPE sleeve (**HW-PIN-SLV**, OD {pn['hole_d_mm']:.1f} / ID 5.2) into each cheek, flush with "
            "the faces (ASSUMPTION PIN-SLEEVE): " + "; ".join(f"{L:g} mm long x {k} ({w})" for L, k, w in sc)
            + f". {sum(k for _, k, _ in sc)} sleeves per frame."
            + (" The US2 outer sleeve ends flush with the counterbore floor, under the pin head (BL-058: bearing "
               f"SF {bl058()['sleeve_bearing']['min_now']:.2f} at the bounding corner, goal "
               f"{bl058()['sleeve_bearing']['goal']:.1f}). CHECK: caliper each US2 outer sleeve "
               f"{us2_sleeve_mm():g} mm before it goes in." if us2_sleeve_mm() else ""))


def retention_txt(pr: dict) -> str:
    """BUILD_H1 9.4 (BL-058, review 6 M-2 / M-3): the retainer per station from h1_closeout.json pins (BL-058
    overlay: retainers_bl058, stations) and the PIN-RET steps incl. (d) from bl058.json kit."""
    rb = pr["retainers_bl058"]
    hp, ec = rb["hairpin"], rb["eclip"]
    st = pr["stations"]
    hs = [k for k, v in st.items() if v["retainer"] == "hairpin"]
    es = [k for k, v in st.items() if v["retainer"] == "eclip"]
    h0, e0 = st[hs[0]], st[es[0]]
    ch = h0["cross_hole"]
    gr = e0["groove"]
    th = e0["tether"]
    cb = bl058()["cbore"]
    pd = bl058()["kit"]["PIN-RET_d"]
    names = lambda ks: "/".join(k.upper() for k in ks)
    return (f"4. Pin retention (BL-058, review 6 M-2): head on the outboard side at every station. "
            f"**{names(hs)}:** a hairpin clip (**HW-PIN-RET-H**: {hp['part']}) through the D{ch['d_mm']:g} mm cross "
            f"hole {ch['from_far_cheek_face_mm']:g} mm past the far (inboard) cheek face, the clip's straight leg "
            "through the hole and its BODY POINTING FORE (towards the wearer, -y), never aft into the bag: "
            + "; ".join(f"{k.upper()} {rb['stations'][k]['points']}" for k in hs)
            + f". Fallback clip: {hp['fallback']} (ASSUMPTION CLIP-FIT). "
            f"Tether at these stations: {pr['retainer']['tether'].split(';')[0]}. "
            f"**{names(es)}:** the 7075 pin's head (D{cb['head_mm'][0]:g} x {cb['head_mm'][1]:g}) sits in the clevis "
            f"counterbore D{cb['d_mm']:g} x {cb['depth_mm']:g}, {cb['recess_mm']:g} mm below the face; on the far side a "
            f"DIN 6799 E-clip (**HW-PIN-RET-E**: {ec['part']}) snaps into the groove D{gr['d_mm']:g} x {gr['w_mm']:g} "
            f"mm ({gr['from_far_cheek_face_mm'][0]:g}-{gr['from_far_cheek_face_mm'][1]:g} mm past the inner cheek face; "
            f"{ec['tool']}). Tether (**HW-PIN-TETH**, {th['cord_mm']:.0f} mm of 1.5 mm Dyneema): "
            + "; ".join(th["route"]) + f"; it never goes {th['never']}. The pins go in at bag fitting; the two hinge "
            "pins come out at bag-off (the US2 pins only at the bench, bag off). CHECK (test PIN-RET): "
            + "; ".join(pr["test"]["steps"]) + f"; (d) {pd['what']}: PASS {pd['pass']}.")


def clevis56_txt(C) -> str:
    """BL-056 note for section 8: the blocks grew and the nut face moved inboard (clevis_bl056.json joint.block, checked
    against the joint code h1_bedfit.JOINT)."""
    b = bl056()
    if not b:
        return ""
    blk = b["clevis"]["joint"]["block"]
    assert abs(blk["nut_face_x_mm"] - C.nut_face) < 1e-6 and abs(blk["trap_x0_mm"] - C.trap_x0) < 1e-6
    d = blk["was_nut_face_x_mm"] - blk["nut_face_x_mm"]
    return (f" BL-056 (CLEVIS-SHARE B at share 1.0): the joint blocks grew upward to z pin +{blk['upper_half_z_mm']:g} mm "
            f"(was +{blk['was_upper_mm']:g}) and the nut face moved {d:g} mm ({d / IN:.2f} in) INBOARD: each nut trap now "
            f"runs x +/-{C.trap_x0:.1f} to {C.nut_face:.0f} (was to {blk['was_nut_face_x_mm']:g}), so the nut sits "
            f"{d:g} mm deeper; the {C.bolt_len:.0f} mm screw still reaches through it (hip_mount_bl056.md 7). Use only "
            "the clevises and lower half printed from the files in this folder (dated 2026-11-21 or later): a clevis "
            "from an older print does not mate with the grown block.")


def hip_n(co: dict) -> int | None:
    h = co.get("hip", {})
    return len(h["pattern"]["positions_xz"]) if h else None


HIP_TORQUE_N_M = 2.0        # fallback only: BL-055 Part B's build-text value, which traces to no record (BL-059)


def hip_torque_n_m(co: dict) -> float:
    """Service torque of the hip mount screws. BL-059 (HB-6b torque mismatch): the sourced value is the insert record's
    ``tightening_torque_max_n_m`` (data/materials/hardware/insert_heatset_brass_m5.yaml, 2.5 N m, read through
    h1_closeout.json hip.insert.torque_max_n_m), which hip_mount_bl056.json HB-6b also quotes; BL-055's 2.0 N m was typed
    in this script with no source. HIP_TORQUE_N_M is used only when the record value is not on file."""
    t = (co or {}).get("insert", {}).get("torque_max_n_m")
    return float(t) if t else HIP_TORQUE_N_M


def hip_screw_spec(co: dict) -> str:
    """The hip mount screw: BL-058's (bl058.json kit.hip_screw: M5 x 12, review 6 m-2) when on file, else the one
    h1_closeout.json carries (BL-055's booking, M5 x 14)."""
    b8 = bl058()
    if b8:
        return re.sub(r"\s*\(\d+\)$", "", b8["kit"]["hip_screw"]["spec"])
    return co.get("hip_screw") or "M5 screw"


def guide_bore_max() -> float:
    """ASSUMPTION GUIDE-HEAT's replace-the-guide line (bl058.json assumptions: 'Bore <= 7.4 mm after use')."""
    a = {x["id"]: x for x in bl058()["assumptions"]}["GUIDE-HEAT"]
    m = re.search(r"<=\s*(\d+(?:\.\d+)?)\s*mm", a["settled_by"])
    assert m, a
    return float(m.group(1))


def guide_steps(n: int) -> list[str]:
    """BUILD_H1 12 steps 2-3 with BL-058's printed insert-setting guide (bl058.json insert_guide / kit.hip_guide):
    print it, start every insert through it, finish flush, INSERT-SET check."""
    b8 = bl058()
    ig, pro = b8["insert_guide"], b8["kit"]["hip_guide"]["procedure"]
    f = Path(b8["kit"]["hip_guide"]["file"]).relative_to(PRINT.relative_to(ROOT))
    gp = ig["params"]
    bmax = guide_bore_max()
    body = lambda t: t.split(". ", 1)[1]
    return [
        f"2. **Insert-setting guide (BL-058, review 6 m-3).** Print `{f}` (+ `.3mf`; {fg(piece_mass_g(str(f.with_suffix(''))))}, "
        f"{ig['extents_mm'][0]:.1f} x {ig['extents_mm'][1]:.1f} x {ig['extents_mm'][2]:.1f} mm) with the frame profile "
        f"of section 3: {ig['print']}; anneal as section 5. CHECK: caliper each of its {ig['bores']} bores "
        f"{gp['bore_d']:.2f} mm (record <= {bmax:.1f} mm, ASSUMPTION GUIDE-HEAT). The guide is what lets the D"
        f"{b8['hip_mount']['hole_d_mm']:g} mount holes line up: freehand inserts scatter too far "
        f"({b8['hip_holes']['choice']['why']}). Practise the whole sequence on the HB-6 insert blocks first (test kit).",
        f"3. START, then FINISH, each insert (ASSUMPTION HIP-HEAT: the insert record gives no install temperature, "
        "so 'the vendor temperature' below is 290 C (554 F), the PAHT-CF nozzle temperature of section 3): (a) " + body(pro[0]) + " (b) " + body(pro[1]) + " (c) " + body(pro[2]) + " (d) " + body(pro[3])
        + f" (e) CHECK (ASSUMPTION INSERT-SET): " + body(pro[4]) + f" (f) CHECK the guide after use: every bore still "
        f"<= {bmax:.1f} mm on the caliper, else print a new guide before the next frame (GUIDE-HEAT).",
    ]


def hip_section(co: dict) -> list[str]:
    """BUILD_H1 12: the hip insert pattern from BL-055 Part A (h1_closeout.hip_check), else a marked pending box."""
    h = co.get("hip", {})
    if not h:
        return ["## 12. Hip mount", "",
                f"> {PENDING} the structural-fea-engineer is sizing the hip insert pattern (count, pilot holes, "
                "positions, wall) for SF >= 1.5 / fatigue >= 1.15 and cutting the pilot holes into the print "
                "(BL-055 Part A). **Do not heat-set any hip insert until this box is replaced.**", "",
                "1. Practise heat-setting on the HB-6 insert blocks meanwhile (test kit).", ""]
    pat = h["pattern"]
    n = len(pat["positions_xz"])
    rel = hip_rel(pat)
    ir = co.get("insert", {})
    ms = h.get("min_sf", {})
    cap = h.get("capacity", {})
    torque = ir.get("torque_max_n_m")
    scr = hip_screw_spec(co)
    b8 = bl058()
    L = ["## 12. Hip mount", "",
         f"Source: `{co['_path']}` (BL-055 Part A, `huntkit/gendesign/h1_closeout.py`). {n} M5 brass heat-set inserts "
         f"(**HW-HIP-INS**) on a boss {pat['boss_d']:.0f} mm ({pat['boss_d'] / IN:.2f} in) across; the pilot holes are "
         f"PRINTED into the boss (D {pat['hole_d']:.1f} x {pat['hole_depth']:.1f} mm deep, open on the wearer face, "
         "which is the face on the plate).", "",
         "| insert | towards the R stay from the boss centre (mm; minus = towards the L stay) | above the boss centre (mm) |", "|---:|---:|---:|"]
    L += [f"| {i} | {x:+.1f} | {z:+.1f} |" for i, (x, z) in enumerate(rel, 1)]
    w = pat.get("walls", {})
    L += ["",
          f"Walls (record minimum {pat.get('wall_rule_mm', float('nan')):.1f} mm): hole to boss edge "
          f"{w.get('edge_mm', float('nan')):.1f} mm, between holes {w.get('between_mm', float('nan')):.1f} mm, hole to the "
          f"mount's pin bore {w.get('to_pin_bore_mm', float('nan')):.1f} mm"
          + (f", hole floor {w['floor_mm']:.1f} mm" if "floor_mm" in w else "") + ". Checked: strength SF "
          f"{ms.get('strength', float('nan'))} (goal 1.5), fatigue {ms.get('fatigue', float('nan'))} (goal 1.15), creep "
          f"{ms.get('creep', float('nan'))}; insert capacity {cap.get('static_n', float('nan')):.0f} N each "
          f"({cap.get('basis', '')}). Pattern {'PASSES' if h.get('pass') else 'DOES NOT PASS: do not fit the mount, ask the engineer'}.", "",
          f"0. CHECK the boss: caliper across it reads {pat['boss_d']:.0f} mm (+/- 0.5) ({pat['boss_d'] / IN:.2f} in).",
          f"1. CHECK the print: count {n} pilot holes on the boss; a {pat['hole_d']:.1f} mm drill shank slides into each "
          f"by hand; the caliper depth rod reads >= {pat['hole_depth']:.1f} mm in each. Clear any support or stringing "
          "with the drill held in your fingers (do not drill deeper).",
          ] + (guide_steps(n) if b8 else [
          "2. Practise on the HB-6 insert blocks first (test kit). Then heat-set each insert with the soldering iron's M5 insert tip at 290 C (554 F, the PAHT-CF nozzle temperature of section 3; ASSUMPTION HIP-HEAT), square to the face, until it sits 0.0-0.2 mm below the face (caliper depth rod).",
          "3. CHECK: lay a steel rule across the boss: no insert stands proud; an M5 screw starts by hand in each."]) + [
          f"4. Fit the SLM Ti pivot mount (**HW-HIP-MNT**) with {n} **{scr}** (**HW-HIP-SCR**), blue threadlocker, "
          + (f"{hip_torque_n_m(co):.1f} N m (the insert record's maximum, tightening_torque_max_n_m; do not exceed it)"
             if torque else f"{HIP_TORQUE_N_M:.1f} N m")
          + ", in a star order"
          + ((f"; neighbouring heads sit only {b8['hip_holes']['head_to_head_worst_mm']:.2f} mm apart at the worst "
              f"insert scatter, so use the {b8['hip_screws']['key']['tool'].split(';')[0]} (DIN 7984 M5 socket "
              f"s {b8['hip_screws']['key']['socket_s_mm']:g}; ASSUMPTION KEY-D)") if b8 else
             (f"; neighbouring heads sit only {w['head_to_head_mm']:.1f} mm apart, so use a ball-end 3 mm key (DIN 7984 M5 socket)"
              if "head_to_head_mm" in w else "")) + "."
          + (" FIRST ARTICLE (ASSUMPTION INSERT-SCATTER): " + b8["kit"]["hip_guide"]["procedure"][-1].split(". ", 1)[1]
             + " If one will not start, stop: do not force it or open the hole; send a photo." if b8 else ""),
          f"5. CHECK: push the mount's pin end with the spring scale to {MOUNT_SEAT_N:.0f} N ({MOUNT_SEAT_N / 9.80665:.1f} kg, {MOUNT_SEAT_N / 4.44822:.1f} lb; ASSUMPTION MOUNT-SEAT) up, down, left and right: "
          "a 0.05 mm (0.002 in) feeler does not enter under the base edge at any point, and no screw head turns "
          "(a paint mark across each head and the base).", ""]
    fl = co.get("flange", {})
    rd = mount_redraw(co)
    if fl and rd:
        L += [f"> **HOLD LIFTED (BL-056): order HW-HIP-MNT.** The SLM file `../{rd['stl']}` (+ `.3mf`) is now the "
              f"redraw: a {rd['d']:.0f} mm ({rd['d'] / IN:.2f} in) x {rd['t']:.1f} mm Ti base with {rd['holes']} holes "
              f"of {rd['hole_d']:.1f} mm on the insert positions above (position error {rd['pos_err']:.2f} mm), "
              f"{fg(rd['mass_g'])} ({rd['mass_src']})"
              + (f"; BL-058 opened the holes to D{rd['hole_d']:.1f} for the guided inserts (FE min SF / goal "
                 f"{bl058()['hip_mount']['fe_min_sf_over_goal']}, was {bl058()['hip_mount']['bl056_fe_min_sf_over_goal']})"
                 if bl058() else "")
              + ". Send the print service `analysis/hip_mount_bl056.md` section 4 "
              "(build direction base down on the plate, supports, HIP, ream the D10 pin bore). The drawn D44 x 1.2 mm "
              "part is kept only in `../legacy/` for the record: never order it. CHECK on arrival: caliper the base "
              f"{rd['t']:.1f} mm thick (+/- 0.1) and {rd['d']:.0f} mm across; count {rd['holes']} holes; weigh it: "
              f"{fg(rd['mass_g'])} +/- {100 * SLM_MASS_TOL:.0f} % (ASSUMPTION SLM-MASS); lay the mount on the boss: every hole shows its insert.", "",
              "> The orchestrator kept the drawn legs for P1 (DECISIONS 2026-11-21): HB-6b run 2 (test kit, pad 20 mm "
              "sideways) decides whether they stay. Order ONE mount for P1; order P2's after HB-6b passes.", ""]
    elif fl:
        L += [f"> **HOLD before ordering HW-HIP-MNT:** the mount's base must be the BL-055 redraw, a {fl['d_mm']:.0f} mm "
              f"({fl['d_mm'] / IN:.2f} in) x {fl['t_mm']:.1f} mm Ti disc with {fl['holes']} holes of {fl['hole_d_mm']:.1f} mm "
              f"on the insert positions above (the file on record is {fl.get('drawn', 'not yet redrawn')}). CHECK on "
              f"arrival: caliper the base {fl['t_mm']:.1f} mm thick (+/- 0.1) and {fl['d_mm']:.0f} mm across; count "
              f"{fl['holes']} holes; lay the mount on the boss: every hole shows its insert.", ""]
    return L


def mount_redraw(co: dict) -> dict:
    """BL-056's redrawn mount, {} until hip_mount_bl056.json says the print file is the redraw (D, t and the 8 holes
    match BL-055's flange and the file passes its fit check)."""
    b = bl056()
    fl = co.get("flange", {}) if co else {}
    if not b or not fl:
        return {}
    b8 = bl058()
    h = b8["hip_mount"] if b8 else b["hip"]               # BL-058 re-exported the mount with D5.8 holes
    hole_d = float(h["hole_d_mm"]) if b8 else fl["hole_d_mm"]
    g = h["geometry"]["base"]
    n = sum(1 for d in g["hole_d_eq_mm"] if abs(d - hole_d) < 0.05)
    ok = (abs(g["d_eq_mm"] - fl["d_mm"]) < 0.1 and n == fl["holes"] and bool(h["frame_fit"].get("pass"))
          and abs(g["top_z_mm"] - fl["t_mm"]) < 0.1 and h["geometry"].get("watertight", False))
    if not ok:
        return {}
    return {"stl": Path(h["stl"]).name, "d": fl["d_mm"], "t": fl["t_mm"], "holes": n, "hole_d": hole_d,
            "pos_err": g["hole_pos_err_mm"], "mass_g": mount_g(),
            "mass_src": "ledger BL056 + BL058" if b8 else "ledger BL056"}


def mount_txt(co: dict) -> str:
    fl = co.get("flange", {})
    if not fl:
        return "SLM Ti-6Al-4V hip pivot mount"
    rd = mount_redraw(co)
    if rd:
        return (f"SLM Ti-6Al-4V hip pivot mount `print/{rd['stl']}` ({'BL-056 redraw, BL-058 holes' if bl058() else 'BL-056 redraw'}): {rd['d']:.0f} x {rd['t']:.1f} mm "
                f"base, {rd['holes']} x D{rd['hole_d']:.1f} holes on the insert positions, {fg(rd['mass_g'])}")
    return (f"SLM Ti-6Al-4V hip pivot mount, base REDRAWN (BL-055): {fl['d_mm']:.0f} x {fl['t_mm']:.1f} mm disc, "
            f"{fl['holes']} x D{fl['hole_d_mm']:.1f} holes on the insert positions")


def build_md(stl: list[dict], b: dict, cp: dict, kits: dict, pn: dict) -> str:
    Z, C = joints()
    pw = pawl()
    by = {r["file"]: r for r in stl}
    lower, upper = by["h1_lower_flat"], by["h1_upper_flat"]
    body = lower["mass_g"] + upper["mass_g"]
    cl = by["us2_clevis_R"]["mass_g"]
    lo_b, hi_b = (body * (1 + x) for x in MASS_BAND)
    fil_body = body * (1 + WASTE)
    n_tp = sum(by[f]["mass_g"] for f in ("test_pieces/hefit_hinge_fairlead_R", "test_pieces/us_route_stay_R",
                                         "test_pieces/im3ec_cheek_R") if f in by)
    hrs = lower["hours_no_support"] + upper["hours_no_support"]
    r5, p5 = rev5(), ps()
    tw = (bl056().get("clevis", {}).get("joint", {}).get("trap_walls") or r5.get("trap_walls", {}))   # BL-056 first
    co = closeout()
    pr = pin_rows(co)
    ret = pr.get("retainer", {}).get("part") if pr else None
    belly = (r5.get("cradle_3d", {}).get("bellies_mm") or [None])[0]
    scar = p5.get("scars", {})
    op_b25, op_us, op_us2, op_usa, op_bg = (op_no(k) for k in ("B-25", "US", "US2", "USA",
                                                               "US / US2 belly gauge tacks (BL-052, DECISION BELLY-GAUGE)"))
    k = kits
    L = ["# BUILD_H1: how to build the H1 frame (Pack 5200)", "",
         "Generated by `designs/pack_5200/frame_h1_build.py` (BL-054, manufacturing-engineer). **Do not edit by hand: "
         "re-run the script.** Every number is read from the STL files, the material records and the frame code when "
         "the script runs; lines marked ASSUMPTION are listed at the end with the test that settles each.", "",
         "Read this file top to bottom, once, before you buy anything. Do the steps in order. Each step says what you "
         "need, what to do, and how you know it worked (CHECK). Metric first, inches in brackets. If a CHECK fails, "
         "stop and send a photo; do not work round it.", "",
         (f"> {PLACEHOLDER} boxes mark what the structural-fea-engineer is still settling in BL-053 (supports, the "
          "US2 nut trap, the US1 root, pin retention). Where a box sits in a step, that step waits for it." if not r5
          else f"> BL-053 data is in use (`{b['_path']}`): supports, the US2 hex nut traps, the stronger US1 / US2 "
          "lugs and the pin retention below come from it."
          + (f" BL-055 Part A data is in use (`{closeout()['_path']}`): the Ti US1 pins (section 9) and the hip "
             "insert pattern with its printed pilot holes (section 12)." if closeout() else
             f" {PENDING} boxes mark the hip insert pattern and the Ti US1 pins (BL-055 Part A).")), "",
         "## 0. What you end up with", "",
         "| part | how it is made | mass |", "|---|---|---:|",
         f"| frame body, lower half (feet to z 234) | printed, PAHT-CF | {fg(lower['mass_g'])} |",
         f"| frame body, upper half (z 234 to the top) | printed, PAHT-CF | {fg(upper['mass_g'])} |",
         f"| US2 clevis x 2 | printed, PAHT-CF | {fg(cl)} each |",
         f"| crown: 2 legs, top bar, spine tube + rack, spine clamp | bought carbon tube, printed rack, machined 7075 "
         f"clamp ({fg(cp['mass_g'])}), bonded | see the crown records |",
         "| pins, sleeves, bolts, pawl, bushings, hip mount | bought or machined | shopping list, section 1 |", "",
         "Frame coordinates used below: x to the wearer's right, y aft (toward the bag), z up from the stay feet. "
         "\"Wearer face\" is the side against your back.", "",
         "## 1. Shopping list (frame only; every line has an ID: label each bag with it)", ""]
    L += shopping_table(stl, cp, kits, pn, Z, C, pw, pr, co)
    L += ["", "> **Two screw lengths and two washer sizes look alike.** HW-J234-SCR (M5 x "
          f"{Z.bolt_len:.0f}) and HW-US2-SCR (M5 x {C.bolt_len:.0f}); HW-J234-WSH ({Z.washer_od:.0f} mm OD) and "
          f"HW-US2-WSH ({C.washer_od:.0f} mm OD). Keep each in its own bag with its ID. Check before fitting: screw "
          f"against a ruler ({Z.bolt_len:.0f} or {C.bolt_len:.0f} mm under the head), washer against the caliper "
          f"({Z.washer_od:.0f} or {C.washer_od:.0f} mm).", ""]
    L += ["### Tools", "",
          "| tool | for |", "|---|---|",
          "| hardened 0.6 mm nozzle, dry box, filament dryer (80 C) | printing PAHT-CF |",
          "| kitchen or postal scale, 1 g (0.04 oz), up to 1 kg | weighing the halves (step 6) |",
          "| oven that holds 90 C +/- 5 C, oven thermometer | annealing (step 5) |",
          "| two 16 mm (5/8 in) straight steel rods, 600 mm (24 in) | keep the crown bores straight in the oven and at "
          "the joint |",
          "| hand reamers: 5.1, 7.2, 8.0, 18.0 mm (adjustable or fixed) + tap wrench | bolt holes, eye holes, pawl bore, "
          "crown-leg bores |",
          "| flush cutters, needle-nose pliers, deburring tool, 120 / 240 grit paper, flat board | support removal "
          "and clean-up |",
          ("| soldering iron with a heat-set insert tip (M5) and a flat-faced tip (to finish the inserts flush) | "
           "hip inserts (section 12) |" if bl058() else "| soldering iron with a heat-set insert tip (M5) | hip inserts |"),
          "| digital caliper, steel rule, feeler gauges 0.05-1.0 mm | checks |",
          ("| " + (f"{bl058()['hip_screws']['key']['tool'].split(';')[0]} (DIN 7984 M5 socket s {bl058()['hip_screws']['key']['socket_s_mm']:g}, "
                   f"every M5 screw on the frame), small torque screwdriver (0.5-{hip_torque_n_m(closeout()):.1f} N m)" if bl058() else
                   "hex keys 3 and 4 mm, small torque screwdriver (0.5-2 N m)") + " | bolts, hip mount |"),
          "| MMA dispenser gun + mixing tips, IPA, nitrile gloves, PTFE tape | bonding |", ""]
    # ---- 2. gates
    L += ["## 2. Before you print anything (gates)", "",
          "1. **Coupons first.** CA-1 (fatigue bars, with the scar bars) and CA-5 (z 234 joint stubs) must pass "
          "before either half; HB-6 (insert pull-out along the build z, hot) must pass before the LOWER half, because "
          "the hip insert pilots are printed into it (review 6 m-9) "
          "(`outputs/release/test_kit/guides/G1.md` prints them, G4 runs them). CHECK: the engineer has written "
          "PASS against all three in the results sheet.",
          "2. **BL-053 print plan in place.** Section 3 below must show the BL-053 support table, not a "
          "'PLACEHOLDER BL-053' box. CHECK: no placeholder box in section 3.",
          "3. **Plate preview with supports on** (review 5 m-10). Load each half into Bambu Studio with the profile of "
          "section 3, supports on, brim on. Slice. CHECK, for each half: (a) nothing is red or outside the plate, "
          "including the support base, the brim and the purge / skirt keep-out; (b) the preview's filament and time "
          "are within 10 % of section 3; (c) no support is drawn inside a bore, pin hole, bolt hole or nut trap. "
          f"Screenshot each preview and send it. The lower half as written is {lower['extents_mm'][0]:.1f} x "
          f"{lower['extents_mm'][1]:.1f} mm ({lower['extents_mm'][0] / IN:.2f} x {lower['extents_mm'][1] / IN:.2f} "
          "in) on a plate the retailer gives as 340 x 320 mm (`docs/research/frame_comp_A.md`, ASSUMPTION BED-ROT in "
          "`analysis/h1_bedfit.md`): only the preview settles it.", ""]
    # ---- 3. print
    L += ["## 3. Print settings and supports", "",
          "Same profile for both halves, the clevises and every test piece (fixtures included).", "",
          "| setting | value |", "|---|---|",
          "| filament | Bambu PAHT-CF, dried 80 C (176 F) for 10-12 h, printed from a dry box |",
          "| nozzle | hardened 0.6 mm, 290 C (554 F) |",
          f"| bed / chamber | 100 C (212 F) / {chamber_txt()} |",
          "| cooling | part fan <= 30 %, aux fan off |",
          "| layer / walls / top-bottom | 0.20 mm / 6 walls / 6 layers |",
          "| infill | 100 % (never a gyroid in place of the limbs) |",
          "| orientation | as in the files: wearer face toward the plate, layers stacked along frame y (the FEA's layer "
          "direction; keep it) |",
          "| seam | on the wearer face side |",
          "| brim | 8 mm (0.31 in) |", ""]
    L += _b53_print_section(b, stl)
    L += ["Filament and time (from the meshes; supports not included in this table):", "",
          "| file | part mass | filament + 8 % waste | time without supports |", "|---|---:|---:|---:|"]
    for f in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_R", "us2_clevis_L", "crown_pawl_lp_fdm_pacf"):
        r = by[f]
        L.append(f"| `{f}` | {fg(r['mass_g'])} | {fg(r['mass_g'] * (1 + WASTE))} | {r['hours_no_support']:.1f} h |")
    L += ["", f"Body without supports: {fg(fil_body)} of filament, about {hrs:.0f} h. Buy one 1 kg spool per half "
          "plus one for the clevises, test pieces and reprints (section 1).", "",
          "Print order: (1) the CA coupons (G1); (2) the test pieces of section 10"
          + (" and the hip insert-setting guide (section 12 step 2: it is needed before HB-6b and before the lower "
             "half's inserts)" if bl058() else "")
          + "; (3) the clevises and the pawl; (4) the upper half; (5) the lower half (longest, fullest plate).", ""]
    # ---- 4. supports off
    L += ["## 4. Take the supports off and clean up", "",
          "1. Let the plate cool to room temperature before you lift the part (warm PAHT-CF bends).",
          "2. Break tree supports off from their tips toward the trunk with pliers; cut stubborn ones with flush "
          "cutters. Work from the middle of each stay outward.",
          ("3. Support scars: " + scar["where"] + ". **These faces are fatigue-critical.** " + scar["finish"]
           + f" Measure with the caliper before and after on one stay: at most {scar['allowance']['max_removed_mm']} "
           f"mm ({scar['allowance']['max_removed_mm'] / IN:.3f} in) off. Sand ALONG the stay, never across it "
           "(BL-053, ASSUMPTION SAND-ALLOW)." if scar else
           "3. Sand support scars on the wearer face of the stays flush with 120 grit, then 240, sanding ALONG the "
           f"stay (never across it). Take off no more than the scar. {PLACEHOLDER} BL-053 says whether the wearer "
           "face of the stays is fatigue-critical and whether a sanding allowance is needed (review 5 B-1 fix 4)."),
          "4. Pick every bore, pin hole and nut trap clean with a pick and a 3 mm drill bit turned by hand.",
          "5. CHECK: no white (stress-whitened) patch on a stay; no layer split you can catch with a fingernail; "
          "every hole open end to end (hold it to a light).", ""]
    # ---- 5. anneal
    L += ["## 5. Anneal", "",
          "1. Put each half on a flat plate in the oven, a 16 mm rod through each crown bore so the bores stay straight.",
          "2. 90 C (194 F) for 6 h. Turn the oven off and let the parts cool inside it, door shut.",
          "3. If the parts sit out for more than a day afterwards, dry them again: 80 C, 4 h.", ""]
    # ---- 6. weigh
    L += ["## 6. Weigh (before reaming)", "",
          f"Weigh each half after support removal and annealing. Expected (STL x density): lower "
          f"{fg(lower['mass_g'])}, upper {fg(upper['mass_g'])}, together {fg(body)} ({body / 453.6:.2f} lb).", "",
          f"CHECK: the two halves together read **{lo_b:.0f} to {hi_b:.0f} g** ({lo_b / OZ:.1f}-{hi_b / OZ:.1f} oz; "
          "ASSUMPTION MASS-BAND). Heavier: over-extrusion, check the flow ratio before the next print. Lighter: gaps "
          "or wet filament; look at a broken support stub for voids. Write both weights on the build sheet.", ""]
    # ---- 7. z234
    L += ["## 7. Bolt the halves together (the z 234 joint)", "",
          f"1. Ream the 4 bolt holes in each half to **{Z.hole_d:.1f} mm ({Z.hole_d / IN:.3f} in)**, from the split face outward, slowly, square "
          "to the face (a drill guide helps).",
          f"2. {nut_check_txt(Z)}.{bolt_check_txt(Z)}{'.' if bolt_window(Z) else ''} Dry-fit an M5 nut (HW-M5-NUT, {NUT_STD}) in each of the 4 side traps of the "
          "lower half: it slides in from the side and does not turn. Tight: file the slot lightly, never more than 0.2 mm.",
          "3. Sand both split faces flat on 120 grit taped to the flat board, about 10 strokes, until they touch over "
          "the whole stay section with no rocking.",
          f"4. Into each side trap: a {Z.washer_od:.0f} mm washer (**HW-J234-WSH**) then a nut; the washer goes on the "
          "split-face side, under the ledge.",
          "5. Stand the halves on the board with a 16 mm rod through both crown bores.",
          f"6. A {Z.washer_od:.0f} mm washer (HW-J234-WSH) under each head; drop the **M5 x {Z.bolt_len:.0f}** screws "
          "(**HW-J234-SCR**) into the upper half's counterbores, through the split, into the nuts; one drop of blue "
          "threadlocker on the threads.",
          f"7. Tighten to **{Z.torque_nm:.1f} N m** (9 in lbf: snug, two fingers on a short key), cross pattern, twice. "
          "Do not over-torque: the joint takes no credit for clamping, and the nylon creeps.",
          "8. CHECK: no step you can feel with a fingernail across the split on any face.",
          "9. Ream each crown bore to **18.0 mm (0.709 in) in one pass** from the top, through the split. Scribe a line across "
          "the split on each stay: these two halves are now a matched pair. Press the two stay-top UHMWPE bushings "
          "(HW-BUSH) into the tops of the bores. CHECK: a crown leg with its 70 mm bushing slides the full travel and "
          "does not catch at z 234.", ""]
    # ---- 8. clevis
    nut_ok = bool(tw.get("nut_held_by_flats"))
    L += ["## 8. US2 clevises", "",
          (f"BL-053 re-cut the nut traps (review 5 M-2): a {C.washer_od:.0f} mm washer slot at the nut face, then a hex "
           f"pocket that holds the nut by its flats; thinnest wall {tw.get('min_wall_mm')} mm (>= 2 mm). Bolt axes at "
           f"z +/-{r5.get('fixes', {}).get('joint', {}).get('dz', C.dz):.0f} mm about the pin." + clevis56_txt(C)
           if nut_ok else
           f"> {PLACEHOLDER} review 5 M-2: the clevis joint's nut traps in the current print (x +/-{C.trap_x0:.1f} to "
           f"{C.nut_face:.0f}) are square slots sized for the {C.washer_od:.0f} mm washer, so the {C.nut_af:.0f} mm "
           "nut spins in them. BL-053 re-cuts them as a hex pocket. Until the re-cut STL is in this folder, use the "
           "fallback in step 2."), "",
          f"1. Ream the two bolt holes in each clevis and in the lower half's US2 block (printed {C.hole_print_d:.1f}) "
          f"to **{C.hole_d:.1f} mm ({C.hole_d / IN:.3f} in)**.",
          f"2. {nut_check_txt(C)}.{bolt_check_txt(C)}{'.' if bolt_window(C) else ''} Into each side trap, from the wearer face: a {C.washer_od:.0f} mm DIN 433 washer "
          f"(**HW-US2-WSH**) then an M5 nut ({NUT_STD}). CHECK: the nut slides into its hex pocket and does not turn with a finger"
          + ("." if nut_ok else "; if it turns (old print), hold it with a thin 8 mm open spanner slid in from the "
             "wearer face while you tighten."),
          f"3. Put the clevis on its block, flat face to flat face at x +/-163, throat floors flush. Push the **M5 x "
          f"{C.bolt_len:.0f}** screws (**HW-US2-SCR**, not the z 234 M5 x {Z.bolt_len:.0f}) into the counterbores in "
          "the clevis's outer face, **no washer under the head**. Blue threadlocker, snug (about 1 N m).",
          f"4. CHECK: a steel rule laid across the clevis outer face does not touch the heads (design "
          f"{C.head_recess - C.head_h:.1f} mm below the face); no step in the throat floor across the joint line "
          "(break the edges 0.3 mm if the eye catches).",
          "5. Ream the US2 eye through both cheeks, assembled, to 7.2 mm so they line up (step 9).", ""]
    # ---- 9. fairleads
    L += ["## 9. Fairlead eyes, sleeves and pins (12 stations)", "",
          "Stations, both stays: hinge z 60, US1 z 95 (lane x +/-70), US2 z 142 (lane x +/-165), IM1 z 190, IM2 z 330, "
          "IM3 z 520.", "",
          f"1. Ream every eye hole to **{pn['hole_d_mm']:.1f} mm ({pn['hole_d_mm'] / IN:.3f} in)** from both sides (24 cheeks).",
          sleeve_step_txt(pn),
          pins_step3(pn, pr, co),
          (retention_txt(pr) if pr.get("retainers_bl058") else
           f"4. Pin retention (BL-053, review 5 M-5): {pr['scheme']}. Head on the outboard side, the clip "
           f"(**HW-PIN-RET**: {ret}) through the {pr['stations']['hinge']['cross_hole']['d_mm']} mm cross hole "
           f"{pr['stations']['hinge']['cross_hole']['from_far_cheek_face_mm']} mm past the far (inboard) cheek face; "
           f"tether: {pr['retainer']['tether']}. The pins go in at bag fitting; the two hinge pins come out at "
           "bag-off. CHECK (BL-053 test PIN-RET): " + "; ".join(pr["test"]["steps"]) + "." if pr else
           f"4. {PLACEHOLDER} pin retention (review 5 M-5): BL-053 designs one retention scheme for all 12 pins "
           "(head, retainer, tether, removal by hand for bag-off). The pins go in at bag fitting (bag op list), not at "
           "frame build; buy them when the BL-053 part list is in."),
          "5. CHECK: a 5 mm pin goes through cheek, sleeve, sleeve, cheek at every station by hand, without forcing.", ""]
    # ---- 10 test pieces (gate)
    L += ["## 10. Test pieces for the bag-cut gate (HE-FIT, PT-3, SEW-F, US ROUTE, CLEVIS-SHARE, IM3-EC)", "",
          "Print, anneal and ream them exactly like the frame (sections 3-5, 8, 9). Supports per piece: "
          + (PLACEHOLDER + " (BL-053 support plan per test piece)." if not p5 else "the BL-053 per-file table in "
             "section 3 (same orientation and supports as the frame, so the pieces carry the frame's scars)."),
          "",
          "| piece | file | mass | prints for | count |", "|---|---|---:|---|---:|"]
    for f, use, n in (("test_pieces/hefit_hinge_fairlead_R", "HE-FIT, PT-3, SEW-F (one fresh print each)", 3),
                      ("test_pieces/us_route_stay_R", "HE-FIT step 0 (US ROUTE) and CLEVIS-SHARE (second print)", 2),
                      ("us2_clevis_R", "bolted onto each US route piece", 2),
                      ("test_pieces/im3ec_cheek_R", "IM3-EC (with the CA-1 bars)", 3)):
        L.append(f"| {by[f]['what']} | `{f}.stl` | {fg(by[f]['mass_g'])} | {use} | {n} |")
    L += (["", "Per piece (BL-053): " + " ".join(f"`{p_}` {piece_print_txt(Path(p_).stem, short=True)}." for p_ in ("test_pieces/hefit_hinge_fairlead_R", "test_pieces/us_route_stay_R", "test_pieces/im3ec_cheek_R", "us2_clevis_R")), ""] if p5 else ["", f"Interim support note (review 5 B-1 table, measured on these files): the US route piece touches the plate "
          "over about 10 mm2, the HE-FIT piece about 29 mm2 and the IM3-EC piece 23 % of its footprint; only the US2 "
          "clevis prints flat (94 % on the plate). **All three test pieces need tree supports from the plate; the "
          "clevis does not.** Same blockers as the frame: nothing inside a bore, pin hole, bolt hole or trap.", ""])
    # ---- 11. pawl
    L += ["## 11. Pawl", "",
          f"1. Ream the pivot bore (printed {pw['bore_print']:.1f}, at z 500 through both cheeks of the pawl housing) "
          f"to **{pw['bore_ream']:.1f} mm ({pw['bore_ream'] / IN:.3f} in)** from each side.",
          "2. Bond one 304 sleeve (**HW-PAWL-SLV**, OD 8.0, ID 4.2, 8 mm long) into each cheek with a thin film of MMA, "
          "flush with the cheek's outer face (ASSUMPTION SLEEVE-BOND: a reamed 8.0 bore gives no press fit). Wipe the "
          "bore of the sleeve clean. Cure 24 h.",
          "3. Fit the **low-profile** pawl (`crown_pawl_lp_fdm_pacf` for P1; the SLM Ti one for production; never "
          "`../crown_pawl_*`) on the 4 x 50 mm pin (**HW-PAWL-PIN**) with the 0.5 mm music-wire torsion spring "
          "(**HW-PAWL-SPR**) on the pin beside it: one leg on the pawl's tang, the other on the window's lower edge. "
          "E-clip each pin end (**HW-PAWL-CLIP**, ASSUMPTION PAWL-PIN).",
          "4. Tie the release cord through the pawl's arm-end hole; lead it out through the fore-wall window.",
          "5. CHECK (after the crown is in, step 13): pull the cord to the stop, the rack slides both ways; let go, the "
          "pawl snaps back into the teeth. Do it 100 times.", ""]
    # ---- 12. hip
    L += hip_section(co)
    # ---- 13. crown
    L += ["## 13. Crown: spine clamp, B-25 sleeves, corners", "",
          "The crown is bought carbon tube, bonded with MMA. Kits (owner 2026-11-11, `crown_diet`):", "",
          "| kit | torso range | leg cut (2) | spine cut | bushing |", "|---|---|---:|---:|---:|"]
    for kk, v in k.items():
        L.append(f"| {kk} | {v['torsos'][0]:g}-{v['torsos'][-1]:g} in | {fmm(v['leg_mm'])} | {fmm(v['spine_mm'])} | "
                 f"{v['bushing_mm']:.0f} mm |")
    L += ["", "Top bar: OD 18.0, 214 mm cut (frame.yaml). Bondline at the corners and the clamp: **0.8 mm** set with "
          "0.8 mm glass beads mixed into the MMA (about 1 % by volume, ASSUMPTION in PRODUCTION rev C).", "",
          "### 13a. Spine clamp coupon first (T6(c))", "",
          f"Make 3 coupons exactly as the frame: the clamp (drawing `drawings/spine_clamp_7075.pdf`) on a 100 mm top-bar "
          f"offcut and a 100 mm spine offcut, same prep, same beads, same MMA. Pull the spine out of the socket along "
          f"its axis to failure. PASS: mean >= 1.5 x {cp['limit_spine_axial_n']:.0f} N = "
          f"{1.5 * cp['limit_spine_axial_n']:.0f} N ({1.5 * cp['limit_spine_axial_n'] / 9.81:.0f} kg), lowest >= "
          f"1.25 x = {1.25 * cp['limit_spine_axial_n']:.0f} N, failure cohesive or in the laminate (not a clean "
          "peel). The limit axial force is the largest spine end force over every rev C case on kits S / M / L "
          "(`crown_spine_clamp.joint_loads`). Make 3 more and TWIST them: clamp the bar offcut in V-blocks, lever on "
          f"the spine offcut, torque the saddle about the bar to failure: PASS mean >= 1.5 x "
          f"{cp['limit_bar_torque_nm']:.1f} N m = {1.5 * cp['limit_bar_torque_nm']:.1f} N m "
          f"({1.5 * cp['limit_bar_torque_nm'] * 8.851:.0f} in lbf), lowest >= 1.25 x (the largest limit torque jump in "
          "the bar across the clamp, same source). The saddle's bond peak is "
          f"{cp['margins']['saddle_with_shear']['peak']['sf']:.2f} with the transverse shear added "
          "(sensitivity), so this coupon is the evidence for the clamp (load_standard.md T6 rule).", "",
          "### 13b. Order (do not change it)", "",
          "1. **Dry fit** the whole crown on the frame with tape, no glue: legs with bushings in the bores at the kit's "
          "shortest setting, the clamp's saddle on the bar centre, the spine (rack on) in its channel, socket over the spine "
          "top. CHECK: the spine slides its channel over the kit's whole range; the pawl engages the rack.",
          f"2. **B-25 gate (bag op {op_b25}, B25-FIT):** with the crown dry-fitted at kit S's shortest setting, the "
          "sewer dry-fits the B-25 scrap strip. The bag op says what passes.",
          "3. Take the crown apart. Cut the rack to the spine length minus 15 mm and bond it to the spine's fore face "
          "(ASSUMPTION RACK-CUT). Bond one 70 mm UHMWPE bushing (HW-BUSH) on the bottom end of each leg (frame.yaml "
          "'low bushing'). Cure 24 h.",
          "4. Slide the clamp's saddle onto the top bar to the bar centre (it is a closed ring: it cannot go on later).",
          f"5. **Slide both B-25 bar sleeves onto the top bar now**, one from each free end, outboard of the clamp (bag "
          f"op {op_b25}: the sleeves are sewn closed off the bar, round an 18 mm dowel). They sit 26.5-64.5 mm (1.04-2.54 in) "
          "each side of the bar centre. **Once the corners are bonded they cannot go on.** Thread the spine through the B-25 "
          "spine-wrap loop.",
          "6. Bond the two corners (leg top to bar end): cope, sand 120 grit, IPA wipe, MMA with 0.8 mm beads, carbon "
          "wrap 3 plies 30 mm onto each tube, ply-drop 8 mm, peel ply, shrink tape, RT cure + 65 C post-cure "
          "(`../frame/PRODUCTION.md` 'Corner wrap' is the source of this recipe; it is the only part of that file you "
          "use). Keep the B-25 sleeves and the clamp away from the wrap with PTFE tape.",
          f"7. Bond the clamp (ASSUMPTION FRAME-AS-JIG): crown seated in the frame at the kit's shortest setting, PTFE tape over the print "
          f"round the channel. Saddle ID {cp['saddle_id_mm']:.1f} on the {cp['bar_od_mm']:.0f} mm bar, socket ID "
          f"{cp['socket_id_mm']:.1f} on the {cp['spine_od_mm']:.0f} mm spine: both 0.8 mm bondlines set by the beads. "
          "Sand both tubes and the fitting bores 120 grit, IPA. Butter, assemble, spine fully home in the socket, "
          "24 h.",
          "8. CHECK: crown slides through the kit's range with the pawl clicking; release cord frees it; the B-25 "
          "sleeves turn on the bar by hand.", ""]
    # ---- 14. spreader
    L += ["## 14. Spreader and rails", "",
          "Sandwich v2 (BP-06 rev C, 7 mm core), from `designs/pack_5200/cut/spreader/`. Clips at z 166 / 260 / 400 "
          "snap over the stays. **One change on H1:** the stay is 4 mm fuller on the bag side at z 119, so the bonded "
          "stand-off pad under the bottom tab is **0.5 mm** (was 4.5 mm). XLPE rails 100 x 420 x 10 mm on the wearer "
          "face.", ""]
    # ---- 15. first article
    L += ["## 15. First-article checks", "",
          "| # | check | how | pass |", "|---:|---|---|---|",
          f"| 1 | body mass | step 6 | {lo_b:.0f}-{hi_b:.0f} g |",
          "| 2 | z 234 joint | fingernail across the split; pencil marks | no step; marks within 0.5 mm after "
          "every load test |",
          "| 3 | crown travel | section 13b check 8 at every kit | full range, pawl clicks, cord releases |",
          "| 4 | clevis heads | steel rule over the clevis face | does not touch the heads |",
          "| 5 | stay crown | caliper the stay crown at z 96 and z 142 against z 122 | within 0.5 mm (ASSUMPTION "
          "CROWN-BRIDGE, h1_crown.md) |",
          "| 6 | spreader seat | 1.5 mm feeler between sheet and the US2 arm root | passes (ASSUMPTION ROOT-AIR) |",
          "| 7 | proof loads | HA-LS-1 T9, T1-T5, T4b dial on the branch, T4c at -20 C "
          "(`analysis/load_standard.md`); MT-1cr on P1 first (test kit G6) | as written there |",
          "| 8 | re-torque | after 24 h and after the first trip | z 234 bolts back to 1.0 N m |"]
    if bl058():
        Wz, Wc = bolt_window(Z), bolt_window(C)
        L += [f"| 9 | screw lengths (BOLT-LEN) | caliper every M5 x {Z.bolt_len:.0f} and M5 x {C.bolt_len:.0f} "
              f"(sections 7.2, 8.2) | {Wz[0]:.1f}-{Wz[1]:.1f} / {Wc[0]:.1f}-{Wc[1]:.1f} mm |",
              "| 10 | hip inserts (INSERT-SET, INSERT-SCATTER) | straight-edge + 0.2 mm feeler; the mount's screws "
              "(section 12) | none proud, none > 0.2 mm low; all "
              f"{hip_n(co)} start by hand through the D{bl058()['hip_mount']['hole_d_mm']:g} holes |",
              "| 11 | retainers (PIN-RET (d), FIT-US marks) | test kit PIN-RET (d) and FIT-US | no colour from a "
              "clip, E-clip, tether or pin head on the bag |"]
    L += ["",
          f"Bag fitting that needs the frame: under-straps US (op {op_us}), US2 (op {op_us2}), cam anchors USA (op "
          f"{op_usa}), belly gauge tacks (op {op_bg}), B-25 (op {op_b25}).", ""]
    if belly:
        L += [f"Cradle belly: the frame is checked down to a {belly} mm belly (BL-053); the user card's belly is "
              "advice, not a safety rule.", ""]
    L += ["## Assumptions", "", "| ID | assumption | settled by |", "|---|---|---|"]
    L += [f"| {a} | {t} | {s} |" for a, (t, s) in ASSUMPTIONS.items()]
    if bl058():
        L += [f"| {a['id']} | {a['text']} | {a['settled_by']} (BL-058, `analysis/bl058.json` assumptions) |"
              for a in bl058()["assumptions"]]
    L += ["| BED-ROT, CLEVIS-*, HEAD-*, CROWN-BRIDGE, ROOT-AIR | carried from `analysis/h1_bedfit.md` 7 and "
          "`h1_crown.md` 7 | as there |",
          "| CLAMP-TYPE, CLAMP-WALL, SOCKET-MIN, SPINE-AXIS, TRANSVERSE-SHEAR | carried from "
          "`huntkit/gendesign/crown_spine_clamp.py` | T6(c) coupon (13a), crown dry fit (13b.1) |", ""]
    return "\n".join(L)


def pin_shop_rows(pn: dict, pr: dict) -> list[tuple]:
    """HW-PIN-TI / HW-PIN-AL from the pin rows: one line per material, every station's shank, head and cross hole
    (BL-055: US1 joins the hinge in Ti). Before any pin rows exist: the BL-049 hinge pin and 10 x 7075."""
    gr = pin_groups(pr)
    if not gr:
        return [("HW-PIN-TI", f"Ti-6Al-4V pin, {pn['hinge_d_mm']:.0f} mm h8 ground, {pn['hinge_len_mm']:.0f} mm", 2,
                 f"hinge z 60 (yield SF {pn['hinge_sf_yield']}, fatigue {pn['hinge_sf_fat']}, h1_lanes.hinge_pin)",
                 "machinist (Ti rod)"),
                ("HW-PIN-AL", "7075-T6 pin, 5 mm", pn["n_al"], "US1, US2, IM1-IM3, both sides", "machinist / bag kit")]
    out = []
    for mat, rows in sorted(gr.items(), key=lambda kv: kv[0] != "Ti-6Al-4V"):
        hid = "HW-PIN-TI" if mat == "Ti-6Al-4V" else "HW-PIN-AL"
        same: dict = {}                                   # stations with the same drawing share a line
        for nm, q, r in rows:
            g = r.get("groove")
            k = (r["shank_mm"], tuple(r["head_mm"]), r["cross_hole"]["d_mm"], r["cross_hole"]["from_far_cheek_face_mm"],
                 (g["d_mm"], g["w_mm"], tuple(g["from_far_cheek_face_mm"])) if g else None)
            same.setdefault(k, []).append((nm, q))

        def feat(k):
            if k[4]:                                      # BL-058 US2: plain head in the counterbore, groove, tail hole
                gd, gw, gx = k[4]
                return (f"plain head {k[1][0]:.0f} x {k[1][1]:g} mm (no head hole), E-clip groove D{gd:g} x {gw:g} mm "
                        f"{gx[0]:g}-{gx[1]:g} mm past the far cheek, D{k[2]:g} tether hole {k[3]:g} mm past it")
            return (f"head {k[1][0]:.0f} x {k[1][1]:g} mm with the 1.6 mm tether hole, D{k[2]:g} clip cross hole "
                    f"{k[3]:g} mm past the far cheek")
        desc = f"{mat} pin, {pn['pin_d_mm']:.0f} mm h8 ground, headed: " + "; ".join(
            f"{' + '.join(nm for nm, _ in v)} ({sum(q for _, q in v)}): shank {k[0]} mm, {feat(k)}" for k, v in same.items())
        why = "; ".join(f"{nm} bending SF {r['bending']['sf_yield']} / fatigue {r['bending']['sf_fatigue']}"
                        for nm, _, r in rows if r.get("bending"))
        out.append((hid, desc, sum(q for _, q, _ in rows),
                    ", ".join(nm for nm, _, _ in rows) + ", both sides" + (f" ({why})" if why else ""),
                    "machinist (Ti rod)" if hid == "HW-PIN-TI" else "machinist / bag kit"))
    return out


def _tally(pairs) -> dict:
    out: dict = {}
    for k, n in pairs:
        out[k] = out.get(k, 0) + n
    return out


def retainer_shop_rows(pn: dict, pr: dict) -> list[tuple]:
    """BL-058 (review 6 M-2): the retainer line split in two, HW-PIN-RET-H (hairpin clips) and HW-PIN-RET-E (US2
    E-clips), plus the tether cord, from h1_closeout.json pins (BL-058 overlay). Before BL-058: one HW-PIN-RET line."""
    if not pr:
        return [("HW-PIN-RET", f"{PLACEHOLDER} pin retention parts (review 5 M-5)", pn["stations"],
                 "one set per station", "hardware / BL-053")]
    rb = pr.get("retainers_bl058")
    if not rb:
        return [("HW-PIN-RET", f"{pr['retainer']['part']} + {pr['retainer']['tether']}", pn["stations"],
                 f"one set per station (BL-053; source {pr['retainer']['source']})", "hardware / BL-053")]
    st = pr["stations"]
    nh = sum(v["qty"] for v in st.values() if v["retainer"] == "hairpin")
    ne = sum(v["qty"] for v in st.values() if v["retainer"] == "eclip")
    hs = "/".join(k.upper() for k, v in st.items() if v["retainer"] == "hairpin")
    es = "/".join(k.upper() for k, v in st.items() if v["retainer"] == "eclip")
    cord = sum(v["qty"] * v["tether"]["cord_mm"] for v in st.values() if v.get("tether"))
    return [
        ("HW-PIN-RET-H", rb["hairpin"]["part"], nh,
         f"{hs}, both sides: through the D{rb['cross_hole_d_mm']:g} cross hole, body fore (BUILD_H1 9.4); fallback "
         f"{rb['hairpin']['fallback']}; source {rb['hairpin']['source'].split(' (')[0]}", "McMaster-Carr"),
        ("HW-PIN-RET-E", rb["eclip"]["part"], ne,
         f"{es}, both sides, in the pin's groove; source {rb['eclip']['source'].split(' (')[0]}", "McMaster-Carr"),
        ("HW-PIN-TETH", "1.5 mm Dyneema (UHMWPE) cord", 1,
         f"{cord / 1000:.2f} m for the {sum(v['qty'] for v in st.values())} tethers ("
         + ", ".join(f"{L:.0f} mm x {n}" for L, n in sorted(_tally((v["tether"]["cord_mm"], v["qty"]) for v in st.values()
                                                                   if v.get("tether")).items()))
         + ": BUILD_H1 9.4); buy 2 m", "bag kit"),
    ]


def shopping_table(stl, cp, kits, pn, Z, C, pw, pr, co=None) -> list[str]:
    co = co or {}
    by = {r["file"]: r for r in stl}
    hs = pr.get("stations", {}).get("hinge", {}) if pr else {}
    ia = pr.get("stations", {}).get("us1", {}) if pr else {}
    fil = sum(by[f]["mass_g"] for f in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_R", "us2_clevis_L"))
    n_cl = 4
    rows = [
        ("HW-FIL", "Bambu PAHT-CF filament, 1 kg spool", 3,
         f"frame parts {fil:.0f} g + 8 % waste + supports (section 3) + test pieces + a reprint; buy 3 spools", "Bambu Lab"),
        ("HW-J234-SCR", f"Ti gr5 low-head socket cap screw M5 x {Z.bolt_len:.0f}, DIN 7984 ({Z.head_h:.1f} mm head)", 4,
         "z 234 joint only (ISO 7380 button head M5 x 45 also fits); not M5 x 40", "Ti fastener vendor"),
        ("HW-J234-WSH", f"M5 washer {Z.washer_od:.0f} mm OD x {Z.washer_t:.1f} mm, A2", 8,
         "z 234 joint only; the 12 mm OD is load-bearing", "hardware store"),
        ("HW-US2-SCR", f"Ti gr5 low-head socket cap screw M5 x {C.bolt_len:.0f}, DIN 7984", n_cl,
         "US2 clevises only, heads in the counterbores" + (
             f"; caliper each {bolt_window(C)[0]:.1f}-{bolt_window(C)[1]:.1f} mm on arrival (BOLT-LEN, BL-058)"
             if bolt_window(C) else ""), "Ti fastener vendor"),
        ("HW-US2-WSH", f"M5 washer {C.washer_od:.0f} mm OD x {C.washer_t:.1f} mm, A2, DIN 433", n_cl * C.n_washers,
         "US2 clevises only, nut side", "hardware store"),
        ("HW-M5-NUT", nut_txt(C), 8,
         f"4 for z 234 + 4 for the clevises; caliper each <= {C.nut_t + NUT_T_TOL:.1f} mm on arrival (review 6 M-1)",
         "hardware store"),
    ] + pin_shop_rows(pn, pr) + retainer_shop_rows(pn, pr) + [
        ("HW-PIN-SLV", f"UHMWPE sleeve OD {pn['hole_d_mm']:.1f} / ID 5.2, "
         + ", ".join(f"{L:g} mm ({k})" for L, k, _ in sleeve_counts(pn)) + " long", 2 * pn["stations"],
         "one per cheek (ASSUMPTION PIN-SLEEVE); turned from UHMWPE rod (record uhmwpe_sheet)"
         + ("; the 2 short ones are the US2 outer cheeks (BL-058 counterbore)" if us2_sleeve_mm() else ""), "machinist"),
        ("HW-PAWL-PIN", "stainless pin 4 mm x 50 mm with an E-clip groove at each end", 1,
         f"pawl pivot; cheek bosses out to x +/-{pw['boss_x']:.1f} (ASSUMPTION PAWL-PIN)", "machinist / McMaster-type"),
        ("HW-PAWL-CLIP", "E-clip DIN 6799 for a 4 mm shaft (size 3.2), stainless", 2, "pawl pin ends", "hardware"),
        ("HW-PAWL-SLV", "304 sleeve OD 8.0 x ID 4.2 x 8 mm", 2, "pawl bore, bonded (ASSUMPTION SLEEVE-BOND)",
         "machinist"),
        ("HW-PAWL-SPR", "music-wire torsion spring, 0.5 mm wire, on a 4 mm pin, 2 legs about 10 mm", 1,
         "h1_pawl PAWL-SPRING; no drawing: bend from 0.5 mm music wire round a 4 mm rod, 2 turns", "hobby shop"),
        ("HW-PAWL", "low-profile pawl: P1 `crown_pawl_lp_fdm_pacf` (printed), production `crown_pawl_lp_slm` (SLM Ti)",
         1, "never the old `../crown_pawl_*`", "print / SLM bureau"),
        ("HW-CORD", "2 mm Dyneema release cord 0.6 m + POM toggle", 1, "crown_diet torso-adjust row", "bag kit"),
        ("HW-HIP-INS", "M5 brass heat-set insert, 9.5 mm long (record insert_heatset_brass_m5)",
         (hip_n(co) + 2) if hip_n(co) else 6,
         (f"{hip_n(co)} used (BL-055 pattern, section 12) + 2 spare" if hip_n(co) else f"{PENDING} count") +
         " (ASSUMPTION HIP-INSERTS)", "hardware"),
    ] + ([("HW-HIP-GUIDE", f"insert-setting guide, printed `{Path(bl058()['kit']['hip_guide']['file']).relative_to(PRINT.relative_to(ROOT))}` "
           "(PAHT-CF, the frame spool)", 1,
           f"section 12 step 2 (BL-058); print a new one when a bore reads > {guide_bore_max():.1f} mm (GUIDE-HEAT)",
           "print")] if bl058() else []) + [
        ("HW-HIP-SCR", (hip_screw_spec(co) if (bl058() or co.get("hip_screw")) else f"{PENDING} M5 mount screw"),
         hip_n(co) or 0,
         "hip mount to the inserts (section 12)" + (
             f"; {bl058()['kit']['hip_screw']['key']}; was {bl058()['kit']['hip_screw']['was']} (BL-058, review 6 m-2 / "
             f"m-3: {bl058()['hip_screws']['rows']['x12']['engagement_mm']['insert_0.2_low']:g}-"
             f"{bl058()['hip_screws']['rows']['x12']['engagement_mm']['insert_flush']:g} mm of thread in the insert, tip "
             f"{bl058()['hip_screws']['rows']['x12']['tip_to_pilot_floor_mm']:g} mm above the pilot floor)"
             if bl058() else ""), "Ti fastener vendor"),
        ("HW-HIP-MNT", mount_txt(co), 1,
         (("BL-056 redraw on file: order now (section 12; HOLD lifted). One for P1; P2's after HB-6b (test kit)")
          if mount_redraw(co) else
          ("+" + f"{co['flange']['delta_g']:.1f} g on today's 28.0 g (frame.yaml); the SLM file must be redrawn before "
           "ordering (section 12 HOLD)")) if co.get("flange") else "as today's frame (frame.yaml 28.0 g)",
         "SLM bureau"),
        ("HW-BUSH", "UHMWPE bushing, 70 mm, for the 16 mm crown legs / 18.0 mm bores", 4,
         "frame.yaml: 2 bonded on the leg bottoms + 2 stay-top bushings", "machinist"),
        ("HW-CLAMP", f"spine clamp, machined 7075-T6 ({fg(cp['mass_g'])})", 1,
         "+ 6 more for the T6(c) coupons (3 pulled, 3 twisted): order 7", "CNC shop"),
        ("HW-LEG", "carbon crown leg, OD 16.0, twill +-45 / UD 0 x 8 / twill +-45 (wall 1.44)", 2,
         "cut per kit (section 13): " + ", ".join(f"{k} {v['leg_mm']:.1f} mm" for k, v in kits.items()), "tube vendor"),
        ("HW-BAR", "carbon crown top bar, OD 18.0 +/- 0.3, twill / UD 0 x 5 / twill (wall 1.065), 214 mm", 1,
         "+ 6 offcuts of 100 mm for the T6(c) coupons (buy 1 m)", "tube vendor"),
        ("HW-SPINE", "carbon crown spine tube, OD 20.0, twill / UD 0 x 5 / twill (wall 1.065)", 1,
         "cut per kit: " + ", ".join(f"{k} {v['spine_mm']:.1f} mm" for k, v in kits.items()) + "; + offcuts for "
         "T6(c)", "tube vendor"),
        ("HW-RACK", "rack, printed `../crown_rack_fdm_pacf.stl` (230 x 6 x 20 mm)", 1,
         "cut to length (ASSUMPTION RACK-CUT)", "print"),
        ("HW-MMA", "methacrylate adhesive (MA300-class), 50 ml cartridge + mixing tips", 2,
         "record adhesive_methacrylate_ma: corners, clamp, rack, pawl sleeves", "adhesive vendor"),
        ("HW-BEADS", "0.8 mm glass beads (bondline spacer)", 1, "small pot; about 1 % by volume in the MMA",
         "abrasives vendor"),
        ("HW-WRAP", "3k carbon twill, 0/90 and +-45, peel ply, shrink tape, laminating epoxy", 1,
         "crown corner wraps", "composites vendor"),
        ("HW-LOC", "medium threadlocker (blue)", 1, "every bolt", "hardware"),
    ]
    L = ["| ID | part | qty | note | where |", "|---|---|---:|---|---|"]
    L += [f"| **{a}** | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
    return L


# ================================================================================ drawing
def clamp_drawing(cp: dict, out: Path = DRAW) -> list[Path]:
    """Three-view drawing of the machined spine clamp (crown_spine_clamp constants), PDF + PNG + DXF outlines."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    out.mkdir(parents=True, exist_ok=True)
    Lb, Ls = cp["saddle_len_mm"], cp["socket_len_mm"]
    rbo, rbi = cp["saddle_od_mm"] / 2, cp["saddle_id_mm"] / 2
    rso, rsi = cp["socket_od_mm"] / 2, cp["socket_id_mm"] / 2
    dy = cp["spine_axis_offset_fore_mm"]
    wt, wh, wg = cp["web_t_mm"], cp["web_h_mm"], cp["web_gap_mm"]
    fig, axs = plt.subplots(1, 3, figsize=(16.5, 6.6), gridspec_kw={"width_ratios": [1.1, 1.1, 1.0]})
    kw = dict(fill=False, lw=1.6, color="k")
    # (a) side view, looking along the bar (x): y horizontal (fore = left), z up
    a = axs[0]
    a.add_patch(Circle((0, 0), rbo, **kw))
    a.add_patch(Circle((0, 0), rbi, ls="--", fill=False, lw=1.0, color="0.4"))
    a.add_patch(Rectangle((-dy - rso, -Ls), 2 * rso, Ls, **kw))
    a.add_patch(Rectangle((-dy - rsi, -Ls), 2 * rsi, Ls, ls="--", fill=False, lw=1.0, color="0.4"))
    a.add_patch(Rectangle((-dy, -wh / 2), dy, wh, fill=True, color="0.85", lw=0))
    a.plot([-dy, -dy], [-Ls - 6, rbo + 6], "-.", color="b", lw=0.8)
    a.plot([0, 0], [-rbo - 4, rbo + 4], "-.", color="b", lw=0.8)
    a.annotate("", xy=(-dy, rbo + 6), xytext=(0, rbo + 6), arrowprops=dict(arrowstyle="<->"))
    a.text(-dy / 2, rbo + 7.5, f"spine axis {dy:.2f} fore of bar axis", ha="center", fontsize=9)
    a.annotate("", xy=(-dy - rso - 4, -Ls), xytext=(-dy - rso - 4, 0), arrowprops=dict(arrowstyle="<->"))
    a.text(-dy - rso - 6, -Ls / 2, f"socket {Ls:.0f}", rotation=90, va="center", ha="right", fontsize=9)
    a.text(rbo + 1, -rbo - 3, f"saddle\nOD {2 * rbo:.1f}\nID {2 * rbi:.1f}", ha="left", va="top", fontsize=9)
    a.text(-dy, -Ls - 3, f"socket OD {2 * rso:.1f} / ID {2 * rsi:.1f}", ha="center", va="top", fontsize=9)
    a.text(-dy / 2, 0, f"webs\n{wt:.1f} thk\n{wh:.1f} tall", ha="center", va="center", fontsize=8)
    a.set_xlim(-dy - rso - 14, rbo + 14)
    a.set_ylim(-Ls - 12, rbo + 14)
    a.set_title("(a) side view along the bar (wearer / fore to the left)", fontsize=10, pad=8)
    # (b) front view, looking aft (-y): x horizontal, z up
    b = axs[1]
    b.add_patch(Rectangle((-Lb / 2, -rbo), Lb, 2 * rbo, **kw))
    b.add_patch(Rectangle((-rso, -Ls), 2 * rso, Ls, **kw))
    for s in (-1, 1):
        b.add_patch(Rectangle((s * (wg / 2) - (wt if s > 0 else 0), -wh / 2), wt, wh, fill=True, color="0.6", lw=0))
    b.annotate("", xy=(-Lb / 2, rbo + 4), xytext=(Lb / 2, rbo + 4), arrowprops=dict(arrowstyle="<->"))
    b.text(0, rbo + 5.5, f"saddle {Lb:.0f} along the bar", ha="center", fontsize=9)
    b.plot([-40, 40], [0, 0], "-.", color="b", lw=0.8)
    b.text(30, 1.5, "bar axis", fontsize=8, color="b")
    b.text(0, -Ls - 3, f"socket bottom: collar {cp['collar_below_bar_underside_mm']:.1f}\nbelow the bar's underside",
           ha="center", va="top", fontsize=9)
    b.set_xlim(-42, 42)
    b.set_ylim(-Ls - 14, rbo + 12)
    b.set_title("(b) front view (from the wearer side)", fontsize=10, pad=8)
    # (c) notes
    c = axs[2]
    c.axis("off")
    notes = [f"SPINE CLAMP, 7075-T6, 1 per frame ({cp['mass_g']:.1f} g)", "",
             f"Saddle: tube OD {2 * rbo:.1f}, ID {2 * rbi:.1f}, {Lb:.0f} long",
             f"   on the {cp['bar_od_mm']:.0f} mm top bar, 0.8 bondline",
             f"Socket: tube OD {2 * rso:.1f}, ID {2 * rsi:.1f}, {Ls:.0f} deep",
             f"   on the {cp['spine_od_mm']:.0f} mm spine, 0.8 bondline,",
             "   top of socket level with the bar axis",
             f"Spine axis {dy:.2f} fore of the bar axis,",
             "   parallel to the crown legs",
             f"Webs: 2 plates {wt:.1f} thick x {wh:.1f} tall,",
             f"   outer faces {wg:.1f} apart, saddle to socket",
             "Wall 0.8 everywhere; break edges 0.2",
             "Finish: hard anodise (no bare Al on carbon)",
             "Bond: MMA + 0.8 mm glass beads (BUILD_H1 13)", "",
             "Margins (crown_spine_clamp.size_clamp):",
             f"  socket avg {cp['margins']['socket']['avg']['sf']}, peak {cp['margins']['socket']['peak']['sf']}",
             f"  saddle avg {cp['margins']['saddle']['avg']['sf']}, peak {cp['margins']['saddle']['peak']['sf']}",
             f"  saddle peak + shear {cp['margins']['saddle_with_shear']['peak']['sf']} -> T6(c) coupon",
             f"  webs yield {cp['margins']['webs']['sf_yield']}", "",
             "Units mm. Design intent from code constants;",
             "machinist confirms tolerances (bores +0.1/-0)."]
    c.text(0, 1, "\n".join(notes), va="top", family="monospace", fontsize=9.5)
    for ax in axs[:2]:
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
        ax.set_xlabel("mm")
    fig.suptitle("H1 crown spine clamp (BL-054, from huntkit/gendesign/crown_spine_clamp.py)", fontsize=12)
    fig.tight_layout()
    pdf, png = out / "spine_clamp_7075.pdf", out / "spine_clamp_7075.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=110)
    plt.close(fig)
    paths = [pdf, png]
    try:
        import ezdxf
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_circle((0, 0), rbo)
        msp.add_circle((0, 0), rbi)
        for r_ in (rso, rsi):
            msp.add_lwpolyline([(-dy - r_, 0), (-dy + r_, 0), (-dy + r_, -Ls), (-dy - r_, -Ls)], close=True)
        msp.add_lwpolyline([(-dy, -wh / 2), (0, -wh / 2), (0, wh / 2), (-dy, wh / 2)], close=True)
        ox = 80.0
        msp.add_lwpolyline([(ox - Lb / 2, -rbo), (ox + Lb / 2, -rbo), (ox + Lb / 2, rbo), (ox - Lb / 2, rbo)], close=True)
        msp.add_lwpolyline([(ox - rso, 0), (ox + rso, 0), (ox + rso, -Ls), (ox - rso, -Ls)], close=True)
        msp.add_text("SPINE CLAMP 7075-T6, mm; side view at 0,0, front view at x 80", dxfattribs={"height": 2.5}
                     ).set_placement((-40, 25))
        d = out / "spine_clamp_7075.dxf"
        doc.saveas(d)
        paths.append(d)
    except ImportError:
        pass
    return paths


# ================================================================================ build
def checks(pk: dict) -> dict:
    stl = pk["stl"]
    by = {r["file"]: r for r in stl}
    md = pk["build_md"] + pk["readme_md"]
    return {"all_watertight": all(r["watertight"] for r in stl),
            "body_g": round(by["h1_lower_flat"]["mass_g"] + by["h1_upper_flat"]["mass_g"], 1),
            "no_production_md_pointer": "as in `../frame/PRODUCTION.md`" not in md,
            "bl053_data": bool(pk["bl053"]), "placeholders": md.count(PLACEHOLDER),
            "bl055_data": bool(closeout()), "pending_bl055": md.count(PENDING),
            "b25_before_corners": "Slide both B-25 bar sleeves onto the top bar now" in pk["build_md"],
            "clamp_mass_g": pk["clamp"]["mass_g"]}


def package() -> dict:
    stl = stl_table()
    b = bl053()
    cp = clamp()
    kits = crown_kits()
    pn = pins()
    pk = {"stl": stl, "bl053": b, "clamp": cp, "kits": kits, "pins": pn,
          "readme_md": readme_md(stl, b), "build_md": build_md(stl, b, cp, kits, pn)}
    pk["checks"] = checks(pk)
    return pk


def screenshots(pk: dict, draw: list[Path]) -> list[Path]:
    """Phone-readable PNGs: the clamp drawing, and the first page of BUILD_H1 rendered as text."""
    import shutil
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    png = [p for p in draw if p.suffix == ".png"]
    if png:
        d = SCREENS / f"{SHOT}_1.png"
        shutil.copyfile(png[0], d)
        out.append(d)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import textwrap
    lines = []
    for ln in pk["build_md"].splitlines():
        if ln.startswith("## 1. Shopping"):
            break
        lines += textwrap.wrap(ln, 95) or [""]
    sec = pk["build_md"].split("## 1. Shopping list")[1].split("### Tools")[0].splitlines()
    rows = [r for r in sec if r.startswith("| **")]
    lines += ["", "SHOPPING LIST (ID / part / qty):"] + [
        textwrap.shorten(" ".join(c.strip(" *") for c in r.split("|")[1:4]), 95) for r in rows]
    fig = plt.figure(figsize=(9, 0.19 * len(lines) + 0.8))
    fig.text(0.02, 0.99, "\n".join(lines), va="top", family="monospace", fontsize=9)
    d = SCREENS / f"{SHOT}_2.png"
    fig.savefig(d, dpi=100)
    plt.close(fig)
    out.append(d)
    # 3: the build order on one phone page (section headings + the crown order, the step a beginner gets wrong)
    md = pk["build_md"]
    heads = [ln[3:] for ln in md.splitlines() if ln.startswith("## ") and ln[3:4].isdigit()]
    crown = md.split("### 13b.")[1].split("## 14.")[0].splitlines()[2:]
    lines = ["H1 BUILD ORDER (BUILD_H1.md)", ""] + [f"  {h}" for h in heads] + ["", "CROWN ORDER (section 13b):"]
    for ln in crown:
        if ln[:2].rstrip(".").isdigit():
            lines += textwrap.wrap(ln.replace("**", ""), 80, subsequent_indent="     ")[:3]
    lines += ["", f"Placeholders waiting for BL-053: {md.count(PLACEHOLDER)}; for BL-055 Part A: {md.count(PENDING)}"]
    fig = plt.figure(figsize=(8, 0.21 * len(lines) + 0.6))
    fig.text(0.02, 0.99, "\n".join(lines), va="top", family="monospace", fontsize=10)
    d = SCREENS / f"{SHOT}_3.png"
    fig.savefig(d, dpi=100)
    plt.close(fig)
    out.append(d)
    h = hip_figure(SCREENS / f"{SHOT}_4.png")
    if h:
        out.append(h)
    return out


def hip_figure(path: Path) -> Path | None:
    """BUILD_H1 section 12 as a picture: the boss seen from the wearer face, the 8 pilot holes numbered as the table,
    the mount's pin bore, dimensions in mm (BL-055 Part A pattern)."""
    co = closeout()
    h = co.get("hip", {})
    if not h:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.h1_closeout import HIP_PIN_HOLE_D
    pat = h["pattern"]
    rel = hip_rel(pat)
    R = pat["boss_d"] / 2
    fig, ax = plt.subplots(figsize=(7, 7.6))
    ax.add_patch(plt.Circle((0, 0), R, fc="#d9d9d9", ec="k", lw=1.5))
    ax.add_patch(plt.Circle((0, 0), HIP_PIN_HOLE_D / 2, fc="white", ec="k", ls="--"))
    ax.text(0, -HIP_PIN_HOLE_D / 2 - 2.5, f"mount pin bore D{HIP_PIN_HOLE_D:g}\n(in the Ti mount)", ha="center",
            va="top", fontsize=9)
    for i, (x, z) in enumerate(rel, 1):
        ax.add_patch(plt.Circle((x, z), pat["hole_d"] / 2, fc="white", ec="#b00", lw=1.5))
        ax.text(x, z, str(i), ha="center", va="center", fontsize=10, color="#b00", weight="bold")
        ax.text(R + 2 if x > 0 else -R - 2, z, f"{i}: {x:+.1f}, {z:+.1f}", ha="left" if x > 0 else "right",
                va="center", fontsize=9)
    ax.annotate("", (-R, -R - 4), (R, -R - 4), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, -R - 5.5, f"boss D{pat['boss_d']:.0f} mm ({pat['boss_d'] / IN:.2f} in)", ha="center", va="top", fontsize=10)
    ax.set_xlim(-R - 24, R + 24)
    ax.set_ylim(-R - 12, R + 8)
    ax.set_aspect("equal")
    ax.axhline(0, color="#888", lw=0.5)
    ax.axvline(0, color="#888", lw=0.5)
    ax.set_xlabel("mm towards the R stay (+) / L stay (-) from the boss centre\n(the pattern is mirror-symmetric: "
                  "it reads the same from either face)")
    ax.set_ylabel("mm above the boss centre")
    ms = h["min_sf"]
    ax.set_title(f"BUILD_H1 12: hip boss, {len(rel)} x M5 insert pilots D{pat['hole_d']:.1f} x "
                 f"{pat['hole_depth']:.1f} deep\nSF strength {ms['strength']:.2f} (goal 1.5), fatigue {ms['fatigue']:.2f} "
                 "(goal 1.15)  BL-055 Part A", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


PRINT_README = PRINT.parent / "README.md"      # designs/pack_5200/print/README.md (huntkit.gendesign.docs writes it)
HIP_ROW = "| lug hip pivot mount |"


def print_readme_hip_row(co: dict | None = None) -> str | None:
    """BL-057: the SLM Ti hip mount row of ``print/README.md`` for the BL-056 redraw (BL-059: with BL-058's D5.8
    holes). The mass is the ledger's (mount_g(): BL056 mount_g + BL058 mount_delta_g); the cost is
    huntkit.gendesign.printables.slm_cost on the redrawn STL's volume with the lug's one reamed bore (lugs.build_specs:
    plate flange + pivot pin), the same rule the gendesign run used for its own (superseded) lug. The time cell: "96 h"
    is the JLC3DP Ti SLM service time of the README's cost source (docs.SRC jlc_ti); the door-to-door weeks are an
    ASSUMPTION a vendor quote settles. huntkit.gendesign.docs.write_print_readme writes this same row. None until the
    redraw is on file."""
    rd = mount_redraw(closeout() if co is None else co)
    if not rd:
        return None
    import trimesh
    from huntkit.gendesign.printables import slm_cost
    vol = float(trimesh.load(PRINT.parent / rd["stl"]).volume)
    tag = "BL-056 redraw, BL-058 holes" if bl058() else "BL-056 redraw"
    return (f"{HIP_ROW} `{Path(rd['stl']).stem}.stl`, `{Path(rd['stl']).stem}.3mf` ({tag}: D{rd['d']:.0f} x "
            f"{rd['t']:.0f} mm base, {rd['holes']} x D{rd['hole_d']:.1f} holes; SLM notes in "
            f"`analysis/hip_mount_bl056.md` 4) | Ti-6Al-4V (ti_6al_4v_slm) | 1 | SLM + HIP + ream the pin bore | "
            f"{rd['mass_g']:.1f} g | 96 h SLM service (JLC3DP, the cost source below) + HIP (3-4 wk door to door: "
            f"ASSUMPTION, a vendor quote settles it) | ${slm_cost(vol, 1, 'ti'):.0f} (AlSi10Mg "
            f"${slm_cost(vol, 1, 'al'):.0f}) |")


HIP_PROTO_ROW = "| lug hip pivot mount (proto)"


def proto_superseded_txt() -> str | None:
    """Review 6 m-4: the FDM prototype hip mount file is still the drawn D44 base with no screw holes. Measured on the
    STL: its base width against the redraw's D. None if it has been redrawn (wide enough)."""
    import trimesh
    rd = mount_redraw(closeout())
    if not rd:
        return None
    m = trimesh.load(PRINT.parent / "lug_hip_pivot_mount_fdm_pacf.stl")
    w = float(sorted(m.extents)[1])                       # the base disc's width (the two larger extents)
    if w >= rd["d"] - 1.0:
        return None
    return (f"base {w:.0f} mm wide with no screw holes, the drawn D44 part; H1 needs the D{rd['d']:.0f} x {rd['holes']} "
            "hole mount: no FDM version is drawn (review 6 m-4)")


def patch_print_readme(write: bool = True) -> str | None:
    """Replace the hip mount row of print/README.md (generated by the BL-022 gendesign run, which BL-057 guards from
    overwriting the redrawn STL; see huntkit.gendesign.lugs.PROTECTED) with print_readme_hip_row(). Idempotent."""
    row = print_readme_hip_row()
    if row is None or not PRINT_README.exists():
        return None
    lines = PRINT_README.read_text().split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(HIP_ROW)]
    assert len(hits) == 1, hits
    lines[hits[0]] = row
    proto = [i for i, ln in enumerate(lines) if ln.startswith(HIP_PROTO_ROW)]
    assert len(proto) == 1, proto
    why = proto_superseded_txt()
    cells = lines[proto[0]].split(" | ")
    first = cells[0].split(", **SUPERSEDED")[0]
    cells[0] = first + (f", **SUPERSEDED, not for H1** ({why})" if why else "")
    lines[proto[0]] = " | ".join(cells)
    txt = "\n".join(lines)
    if write:
        PRINT_README.write_text(txt)
    return txt


def write(pk: dict) -> list[Path]:
    PRINT.mkdir(parents=True, exist_ok=True)
    (PRINT / "README.md").write_text(pk["readme_md"])
    (PRINT / "BUILD_H1.md").write_text(pk["build_md"])
    out = [PRINT / "README.md", PRINT / "BUILD_H1.md"]
    if patch_print_readme():
        out.append(PRINT_README)
    return out + clamp_drawing(pk["clamp"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-screens", action="store_true")
    a = ap.parse_args(argv)
    pk = package()
    print(json.dumps(pk["checks"], indent=1))
    if a.check:
        return pk
    files = write(pk)
    for f in files:
        print("wrote", f.relative_to(ROOT))
    if not a.no_screens:
        for s in screenshots(pk, files):
            print("SCREEN", s)
    return pk


if __name__ == "__main__":
    main()
