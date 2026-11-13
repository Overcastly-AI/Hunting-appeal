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
import json
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
SHOT = "20261113_BL054"
IN = 25.4
OZ = 28.3495
MAT_PRINT = "pa12_cf_fdm_paht"
RATE_MM3_S = 8.0                 # print time basis of the H1 records: volume / 8 mm3/s + 8 % waste (README BL-049..051)
WASTE = 0.08
SUPPORT_EXTRA = (0.15, 0.25)     # review 5 B-1 fix 2: "add about 15-25 % on the filament line" (interim, BL-053 replaces)
MASS_BAND = (-0.03, 0.04)        # ASSUMPTION MASS-BAND: as-printed body within -3 / +4 % of the STL mass x density
PLACEHOLDER = "**[PLACEHOLDER BL-053]**"

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
    "HIP-INSERTS": ("The Ti hip mount fixes to the printed hip boss with M5 brass heat-set inserts. hipbelt_structural.md "
                    "books 2 (SF 0.995 with the load on the pin, flagged) and recommends 3-4; frame_light2 / frame_comp_C "
                    "use 4. This build uses 4 and buys 6.", "Insert pull-out coupon HB-6 (test kit) and the D-I1 coupon."),
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
             ("test_pieces/im3ec_cheek_R", "test piece IM3-EC", "PAHT-CF")]
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
PROFILE_TXT = ("PAHT-CF dried 80 C (176 F) 10-12 h, hardened 0.6 mm nozzle at 290 C, bed 100 C, chamber closed, 0.20 mm "
               "layers, 6 walls, 6 top / bottom layers, 100 % infill, 8 mm brim, loaded as the file is written (do not "
               "rotate)")
SUPPORT_TXT = ("tree supports FROM THE BUILD PLATE under the whole piece, in PAHT-CF, top Z distance 0.20-0.25 mm, 2-3 "
               "interface layers, 45 deg threshold, support blockers painted inside every bore, pin hole, bolt hole, "
               "counterbore and nut trap. After printing break the supports off, sand the scars flush ALONG the stay")


def piece_print_txt(piece: str, short: bool = False) -> str:
    """One sentence a beginner can follow for printing one test piece (kit HE-FIT / PT-3 / SEW-F / US ROUTE /
    CLEVIS-SHARE / IM3-EC). BL-053's per-piece plan is quoted when its JSON has an entry for the piece."""
    b = bl053()
    hit = None
    if b:
        flat = dict(_flat({k: v for k, v in b.items() if k != "_path"}))
        hit = {k: v for k, v in flat.items() if piece in k}
    on, ov = PIECE_CONTACT.get(piece, ("?", "?"))
    if piece.startswith("us2_clevis"):
        sup = (f"NO supports: it prints flat ({on} of its footprint on the plate, review 5 B-1), blockers in the bolt "
               "holes and counterbores")
    else:
        sup = (f"SUPPORTS REQUIRED (it touches the plate over only {on}, {ov} overhangs more than 45 deg, review 5 "
               f"B-1): {SUPPORT_TXT}")
    if hit:
        sup += ". BL-053 plan: " + ", ".join(f"{k.split('.')[-1]} {v}" for k, v in list(hit.items())[:8])
    else:
        sup += f" ({PLACEHOLDER.strip('*')} per-piece orientation and supports: check BUILD_H1 section 10 first)"
    if short:
        on_ = f"it touches the plate over only {on}"
        if piece.startswith("us2_clevis"):
            return ("frame profile of BUILD_H1.md section 3, NO supports (it prints flat), blockers in the holes, "
                    "annealed 90 C 6 h")
        return (f"frame profile of BUILD_H1.md section 3 with SUPPORTS REQUIRED ({on_}): tree supports from the build "
                "plate in PAHT-CF, blockers in every bore, pin hole, bolt hole and trap, scars sanded along the stay, "
                "annealed 90 C 6 h" + ("" if hit else f" ({PLACEHOLDER.strip('*')}: check BUILD_H1 section 10 first)"))
    return (f"{PROFILE_TXT}. {sup}. Anneal 90 C (194 F) 6 h with the part on a flat plate, cool in the oven, then ream "
            "every hole as the frame (BUILD_H1 sections 7-9)")   # no ';' in this text: the kit splits steps on it


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
    """Generic render of BL-053's print plan (schema not fixed when BL-054 was written): every key under a 'print' /
    'supports' / 'print_plan' block as a table, the rest named."""
    L = []
    keys = [k for k in b if any(t in k.lower() for t in ("print", "support", "orient"))]
    for k in keys or []:
        v = b[k]
        L += [f"**{k}**", "", "| item | value |", "|---|---|"]
        if isinstance(v, dict):
            L += [f"| {a} | {json.dumps(x) if isinstance(x, (list, dict)) else x} |" for a, x in _flat(v)]
        else:
            L.append(f"| {k} | {v} |")
        L.append("")
    if not keys:
        L += [f"{PLACEHOLDER} the BL-053 file has no print / support block yet: keys {', '.join(sorted(b)[:20])}.", ""]
    return L


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
def readme_md(stl: list[dict], b: dict) -> str:
    by = {r["file"]: r for r in stl}
    body = sum(by[f]["mass_g"] for f in ("h1_lower_flat", "h1_upper_flat") if f in by)
    cl = sum(by[f]["mass_g"] for f in ("us2_clevis_R", "us2_clevis_L") if f in by)
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
         "- **Engineering release candidate, not released.** Print the first article only after the coupons CA-1 and "
         "CA-5 pass (`designs/pack_5200/tests_physical/CA1_fatigue_rig.md`, the test kit) **and** after the BL-053 "
         "print plan (orientation, supports, filament, time) has replaced the placeholder in BUILD_H1 section 3.",
         "- Review 5 (`analysis/review_20261113_fifth.md`) found the body files cannot be printed with the old "
         "\"no supports\" text (B-1). BL-053 owns the supports, cradle direction, nut traps, US1 root and pin "
         "retention; BL-054 (this package) owns the build text.",
         f"- {('BL-053 data in use: `' + b['_path'] + '`.') if b else PLACEHOLDER + ' BL-053 data not yet published; marked placeholders in BUILD_H1.'}",
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
          ""]
    return "\n".join(L)


# ================================================================================ BUILD_H1
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
    nut_txt = b53_get(b, "nut_trap", "us2_nut_trap", default=None)
    ret = b53_get(b, "pin_retention", "retention", default=None)
    belly = b53_get(b, "belly_min_mm", "min_belly_mm", default=None)
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
         f"> {PLACEHOLDER} boxes mark what the structural-fea-engineer is still settling in BL-053 (supports, the US2 "
         "nut trap, the US1 root, pin retention). Where a box sits in a step, that step waits for it.", "",
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
    L += shopping_table(stl, cp, kits, pn, Z, C, pw, ret)
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
          "| soldering iron with a heat-set insert tip (M5) | hip inserts |",
          "| digital caliper, steel rule, feeler gauges 0.05-1.0 mm | checks |",
          "| hex keys 3 and 4 mm, small torque screwdriver (0.5-2 N m) | bolts |",
          "| MMA dispenser gun + mixing tips, IPA, nitrile gloves, PTFE tape | bonding |", ""]
    # ---- 2. gates
    L += ["## 2. Before you print anything (gates)", "",
          "1. **Coupons first.** CA-1 (fatigue bars) and CA-5 (z 234 joint stubs) must pass "
          "(`outputs/release/test_kit/guides/G1.md` prints them, G4 runs them). CHECK: the engineer has written "
          "PASS against both in the results sheet.",
          f"2. **BL-053 print plan in place.** Section 3 below must show the BL-053 table, not the {PLACEHOLDER} "
          "box. CHECK: no placeholder box in section 3.",
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
          "| bed | 100 C (212 F), chamber closed |",
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
          "Print order: (1) the CA coupons (G1); (2) the test pieces of section 10; (3) the clevises and the pawl; "
          "(4) the upper half; (5) the lower half (longest, fullest plate).", ""]
    # ---- 4. supports off
    L += ["## 4. Take the supports off and clean up", "",
          "1. Let the plate cool to room temperature before you lift the part (warm PAHT-CF bends).",
          "2. Break tree supports off from their tips toward the trunk with pliers; cut stubborn ones with flush "
          "cutters. Work from the middle of each stay outward.",
          "3. Sand support scars on the wearer face of the stays flush with 120 grit, then 240, sanding ALONG the "
          f"stay (never across it). Take off no more than the scar. {PLACEHOLDER} BL-053 says whether the wearer face "
          "of the stays is fatigue-critical and whether a sanding allowance is needed (review 5 B-1 fix 4).",
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
          f"2. Dry-fit an M5 nut (HW-M5-NUT) in each of the 4 side traps of the lower half: it slides in from the side "
          "and does not turn. Tight: file the slot lightly, never more than 0.2 mm.",
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
    L += ["## 8. US2 clevises", "",
          f"> {PLACEHOLDER} review 5 M-2: the clevis joint's nut traps in the current print (x +/-{C.trap_x0:.1f} to "
          f"{C.nut_face:.0f}) are square slots sized for the {C.washer_od:.0f} mm washer, so the {C.nut_af:.0f} mm nut "
          "spins in them. BL-053 re-cuts them as a hex pocket. "
          + (f"BL-053 data: {nut_txt}. " if nut_txt else "") + "Until the re-cut STL is in this folder, use the "
          "fallback in step 2.", "",
          f"1. Ream the two bolt holes in each clevis and in the lower half's US2 block (printed {C.hole_print_d:.1f}) "
          f"to **{C.hole_d:.1f} mm ({C.hole_d / IN:.3f} in)**.",
          f"2. Into each side trap, from the wearer face: a {C.washer_od:.0f} mm DIN 433 washer (**HW-US2-WSH**) then an "
          "M5 nut. If the nut turns in the trap (old print), hold it with a thin 8 mm open spanner slid in from the "
          "wearer face while you tighten.",
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
          f"2. Slide one UHMWPE sleeve (**HW-PIN-SLV**, OD {pn['hole_d_mm']:.1f} / ID 5.2) into each cheek, flush with "
          f"both faces: {pn['hinge_cheek_mm']:.0f} mm long at the hinge, {pn['im_cheek_mm']:.0f} mm at the other 10 "
          "stations (ASSUMPTION PIN-SLEEVE). 24 sleeves per frame.",
          f"3. Pins: hinge (z 60) = **Ti-6Al-4V, {pn['hinge_d_mm']:.0f} x {pn['hinge_len_mm']:.0f} mm** "
          f"(**HW-PIN-TI**, 2; not 7075: the 1019 N hinge row fails a 7075 pin). The other 10 = 7075-T6, 5 mm "
          "(**HW-PIN-AL**).",
          f"4. {PLACEHOLDER} pin retention (review 5 M-5): BL-053 designs one retention scheme for all 12 pins (head, "
          "retainer, tether, removal by hand for bag-off). " + (f"BL-053 data: {ret}. " if ret else "") +
          "The pins go in at bag fitting (bag op list), not at frame build; buy them when the BL-053 part list is in.",
          "5. CHECK: a 5 mm pin goes through cheek, sleeve, sleeve, cheek at every station by hand, without forcing.", ""]
    # ---- 10 test pieces (gate)
    L += ["## 10. Test pieces for the bag-cut gate (HE-FIT, PT-3, SEW-F, US ROUTE, CLEVIS-SHARE, IM3-EC)", "",
          "Print, anneal and ream them exactly like the frame (sections 3-5, 8, 9). Supports per piece: "
          + (PLACEHOLDER + " (BL-053 support plan per test piece)." if not b else "the BL-053 table in section 3."),
          "",
          "| piece | file | mass | prints for | count |", "|---|---|---:|---|---:|"]
    for f, use, n in (("test_pieces/hefit_hinge_fairlead_R", "HE-FIT, PT-3, SEW-F (one fresh print each)", 3),
                      ("test_pieces/us_route_stay_R", "HE-FIT step 0 (US ROUTE) and CLEVIS-SHARE (second print)", 2),
                      ("us2_clevis_R", "bolted onto each US route piece", 2),
                      ("test_pieces/im3ec_cheek_R", "IM3-EC (with the CA-1 bars)", 3)):
        L.append(f"| {by[f]['what']} | `{f}.stl` | {fg(by[f]['mass_g'])} | {use} | {n} |")
    L += ["", f"Interim support note (review 5 B-1 table, measured on these files): the US route piece touches the plate "
          "over about 10 mm2, the HE-FIT piece about 29 mm2 and the IM3-EC piece 23 % of its footprint; only the US2 "
          "clevis prints flat (94 % on the plate). **All three test pieces need tree supports from the plate; the "
          "clevis does not.** Same blockers as the frame: nothing inside a bore, pin hole, bolt hole or trap.", ""]
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
    L += ["## 12. Hip mount", "",
          "1. Heat-set 4 M5 brass inserts (**HW-HIP-INS**) into the printed hip boss, square to the face, flush "
          "(ASSUMPTION HIP-INSERTS). Practise on the HB-6 insert blocks first.",
          "2. Fit the SLM Ti pivot mount with its M5 screws, blue threadlocker, 2 N m.",
          "3. **OPEN (found by BL-054):** the H1 print's hip-boss pilot holes are not in the H1 records; check the boss on the "
          "print against the Ti mount's hole pattern before heat-setting; send a photo if the holes are not there.", ""]
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
          "| 8 | re-torque | after 24 h and after the first trip | z 234 bolts back to 1.0 N m |", "",
          f"Bag fitting that needs the frame: under-straps US (op {op_us}), US2 (op {op_us2}), cam anchors USA (op "
          f"{op_usa}), belly gauge tacks (op {op_bg}), B-25 (op {op_b25}).", ""]
    if belly:
        L += [f"Cradle belly: the frame is checked down to a {belly} mm belly (BL-053); the user card's belly is "
              "advice, not a safety rule.", ""]
    L += ["## Assumptions", "", "| ID | assumption | settled by |", "|---|---|---|"]
    L += [f"| {a} | {t} | {s} |" for a, (t, s) in ASSUMPTIONS.items()]
    L += ["| BED-ROT, CLEVIS-*, HEAD-*, CROWN-BRIDGE, ROOT-AIR | carried from `analysis/h1_bedfit.md` 7 and "
          "`h1_crown.md` 7 | as there |",
          "| CLAMP-TYPE, CLAMP-WALL, SOCKET-MIN, SPINE-AXIS, TRANSVERSE-SHEAR | carried from "
          "`huntkit/gendesign/crown_spine_clamp.py` | T6(c) coupon (13a), crown dry fit (13b.1) |", ""]
    return "\n".join(L)


def shopping_table(stl, cp, kits, pn, Z, C, pw, ret) -> list[str]:
    by = {r["file"]: r for r in stl}
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
         "US2 clevises only, heads in the counterbores", "Ti fastener vendor"),
        ("HW-US2-WSH", f"M5 washer {C.washer_od:.0f} mm OD x {C.washer_t:.1f} mm, A2, DIN 433", n_cl * C.n_washers,
         "US2 clevises only, nut side", "hardware store"),
        ("HW-M5-NUT", f"M5 hex nut A2, ISO 4032 ({C.nut_af:.0f} AF x {C.nut_t:.0f} mm)", 8,
         "4 for z 234 + 4 for the clevises; thin nuts do not fit", "hardware store"),
        ("HW-PIN-TI", f"Ti-6Al-4V pin, {pn['hinge_d_mm']:.0f} mm h8 ground, {pn['hinge_len_mm']:.0f} mm", 2,
         f"hinge z 60 ({pn['hinge_g']:.1f} g each; yield SF {pn['hinge_sf_yield']}, fatigue {pn['hinge_sf_fat']}, "
         "h1_lanes.hinge_pin); end form per BL-053 retention", "Ti pin / dowel vendor"),
        ("HW-PIN-AL", "7075-T6 pin, 5 mm", pn["n_al"],
         f"US1, US2, IM1-IM3, both sides; span cheek-to-cheek {pn['im_span_mm']:.0f} mm; length and end form per "
         "BL-053 retention", "machinist / bag kit"),
        ("HW-PIN-RET", f"{PLACEHOLDER} pin retention parts (review 5 M-5)" if not ret else f"pin retention: {ret}",
         pn["stations"], "one set per station", "BL-053"),
        ("HW-PIN-SLV", f"UHMWPE sleeve OD {pn['hole_d_mm']:.1f} / ID 5.2, {pn['hinge_cheek_mm']:.0f} mm (4) and "
         f"{pn['im_cheek_mm']:.0f} mm (20) long", 2 * pn["stations"],
         "one per cheek (ASSUMPTION PIN-SLEEVE); turned from UHMWPE rod (record uhmwpe_sheet)", "machinist"),
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
        ("HW-HIP-INS", "M5 brass heat-set insert (for plastics)", 6, "4 used + 2 spare (ASSUMPTION HIP-INSERTS)",
         "hardware"),
        ("HW-HIP-MNT", "SLM Ti-6Al-4V hip pivot mount + its M5 screws", 1, "as today's frame (frame.yaml 28.0 g)",
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
    lines += ["", f"Placeholders waiting for BL-053: {md.count(PLACEHOLDER)}"]
    fig = plt.figure(figsize=(8, 0.21 * len(lines) + 0.6))
    fig.text(0.02, 0.99, "\n".join(lines), va="top", family="monospace", fontsize=10)
    d = SCREENS / f"{SHOT}_3.png"
    fig.savefig(d, dpi=100)
    plt.close(fig)
    out.append(d)
    return out


def write(pk: dict) -> list[Path]:
    PRINT.mkdir(parents=True, exist_ok=True)
    (PRINT / "README.md").write_text(pk["readme_md"])
    (PRINT / "BUILD_H1.md").write_text(pk["build_md"])
    return [PRINT / "README.md", PRINT / "BUILD_H1.md"] + clamp_drawing(pk["clamp"])


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
