"""BL-017: a lighter crown and torso-adjust block that keeps the adjustable torso (study, nothing adopted).

The H1 frame (``frame_h1``) carries a telescoping carbon crown: two 430 mm OD 16 legs sliding on 70 mm UHMWPE
bushings in the 18.0 mm sleeve bores of the printed stays, a top bar, a 300 mm spine with a PA66-GF30 rack, a
pawl in the printed upper bar, and a 3:1 webbing pulley + cam buckle to adjust the torso while worn. The owner kept
the adjustable torso (DECISIONS 2026-11-11, after BL-007). This module looks for the saving that keeps it.

Options (ticket BL-017):

- **(a) three crown kits on one printed body** ("S" 15-18, "M" 17.5-20.5, "L" 20-23 in, +-1.5 in = +-38 mm of
  travel each): legs, spine and rack are cut per size so that, at the top of each size, the leg sits in the stay
  exactly as H1's leg does at 23 in (overlap 155.8 mm, the governing leg geometry). The body is H1, unchanged.
  ``a_sleeve`` also tests opening the empty sleeve below the deepest leg (r 9 -> 10, z 160-290) on the body.
- **(b) pinned positions** instead of rack + pawl: an index plunger in a perforated strip (no holes in carbon),
  and, for information, a cross-pin through the carbon leg (allowed only where the leg moment is low).
- **(c) larger OD, thinner wall legs** at the same bending stiffness: OD 17 (bushing wall 0.5 mm, same 18.0 bore)
  and OD 18 (20.0 bore: the printed sleeve wall drops from 4.41 to 3.41 mm unless the stay grows).
- **(d) the 3:1 pulley replaced**: (d1) no pulley, pawl only; (d2) a 1:1 pull-down strap through one guide.
- **(e) shorter UHMWPE bushings** (70 -> 50 mm), found while breaking the block down.

Every structural variant is re-solved on the rev C beam model of frame.yaml (both bag-couple variants, every case
including C8 hipbelt-off and C6p posts) at the torso settings it affects; the printed body is re-checked on the
2 mm voxel model (H1 solid, D's solver, FI99 rule) wherever the leg-in-stay geometry changes.

Record: designs/pack_5200/analysis/crown_diet.md. Run (about 10 min on 2 cores):
    python -m huntkit.gendesign.crown_diet all
"""
from __future__ import annotations

import copy
import dataclasses
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "crown_diet"
DOC = REPO / "designs" / "pack_5200" / "analysis" / "crown_diet.md"
RESULT = REPO / "designs" / "pack_5200" / "analysis" / "crown_diet_results.json"
GEOM = REPO / "designs" / "pack_5200" / "geometry.yaml"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261111_BL017"

H1_LEG_MM = 430.0        # geometry.yaml frame.members_topology.crown.leg_length_along_axis
H1_SPINE_MM = 300.0      # pack5200 P5200 spine_len (frame.yaml stock: crown spine tube 300 mm)
H1_RACK_MM = 300.0       # pack5200 HW rack_g basis: PA66-GF30 toothed rack 300 x 12 x 4 mm
PAWL_Z = 520.0           # pack5200 pawl_z
SIZES = {"S": (15.0, 18.0), "M": (17.5, 20.5), "L": (20.0, 23.0)}   # +-1.5 in each, 0.5 in overlap
H1_TORSOS = (15.0, 19.0, 23.0)

# ---------------------------------------------------------------- mass sources (every number traced)
WEBBING_G_M = 18.0       # data/materials/webbing/poly_webbing_25mm.yaml mass_g_m
CORD_G_M = 2.5           # data/materials/hardware/dyneema_cord_2mm.yaml mass_g_m
CAM_G, TOGGLE_G = 12.0, 3.0           # geometry.yaml torso-adjust row: cam 12 g + toggle 3 g ASSUMPTION
PULLEY_WEB_M = 1.4                    # geometry.yaml torso-adjust row: webbing 25 mm x 1.4 m
TORSO_ADJUST_ROW_G = 41.7             # ledger row "torso adjust: ..." (checked against the ledger in tests)
PULLEY_GUIDES_G = 8.0                 # pack5200.HW pulley_guides_g (ASSUMPTION there)
RACK_G = 22.0                         # pack5200.HW rack_g (ASSUMPTION there)
PAWL_HOUSING_G = 14.0                 # pack5200.HW pawl_housing_g: POM housing + spring + Ti pawl (ASSUMPTION there)
PAWL_BUSH_G = 9.94                    # frame_branch.pack_numbers: 304 pawl bushings + pin
SPINE_CLAMP_G = 6.0                   # pack5200.HW spine_clamp_g
UHMW_RHO = 935.0                      # pack5200.HW uhmw_density
PA66_RHO = 1370.0                     # data/materials/polymers/pa66_gf30.yaml density
PA66_UTS_COND = 125.0                 # pa66_gf30.yaml ultimate_strength_conditioned_mpa
PA66_TAU = 67.0                       # geometry.yaml crown_retention lock basis (tau 67 MPa conditioned, ASSUMPTION)
RACK_STRIP_G_MM = 12.0 * 4.0 * PA66_RHO * 1e-6   # strip part of the rack (300 x 12 x 4); the rest is inserts
LADDER_G_PER_MM = 2.5 / 360.0         # BL-007 ASSUMPTION: 17 -> 3 rungs = -2.5 g (Hypalon 40 x 180 mm x 2)
LADDER_RUNG_MM = 250.0 / 16.0         # B-20: 17 rungs over 250 mm

# (b) index-plunger lock (ASSUMPTION masses: catalogue M10 plunger in Ti / Al)
PLUNGER_G = 6.0
PAWL_SPRING_G = 6.0                   # ASSUMPTION: the Ti pawl + spring share of the 14 g pawl row
PLUNGER_D, STRIP_T, PIN_PITCH = 5.0, 4.0, 12.7
CFRP_OPEN_HOLE = 0.55                 # frame_fixed OPEN_HOLE_KD (ASSUMPTION there)

# (d2) 1:1 pull-down strap (dead end on the spine bottom -> guide A at the lumbar top -> grab tab)
D2_WEB_M = 0.45                       # ASSUMPTION: spine bottom (z ~ 300-500) to guide A (z 190) and out to a tab
PULLEY_MU = 0.10                      # frame_cg_recheck.PULLEY_MU
TAIL_PULL_LIMIT_N = 200.0             # frame_cg_recheck.TAIL_PULL_LIMIT_N (ASSUMPTION there)


# ================================================================================================ geometry
_G: dict = {}


def geom() -> dict:
    if not _G:
        import yaml
        g = yaml.safe_load(GEOM.read_text())
        _G["g"] = g
        u = g["frame"]["members_topology"]["crown"]["axis_unit_vector_yz"]
        _G["uz"] = float(u[1]) / math.hypot(*u)
        _G["cs"] = {float(c["torso_in"]): c for c in g["frame"]["crown_settings"]}
    return _G


def crown_top_z(t: float) -> float:
    cs = geom()["cs"]
    return float(cs[min(cs, key=lambda k: abs(k - t))]["crown_top_z"])


def overlap_mm(t: float, leg_mm: float = H1_LEG_MM) -> float:
    """Leg length inside the stay (from the leg bottom to the stay top z 530), along the axis."""
    return leg_mm - (crown_top_z(t) - 530.0) / geom()["uz"]


def size_leg_mm(size: str) -> float:
    """Leg cut length so that at the top of the size the overlap equals H1's at 23 in (155.8 mm)."""
    top = SIZES[size][1]
    return H1_LEG_MM - (crown_top_z(23.0) - crown_top_z(top)) / geom()["uz"]


def s_pawl(t: float) -> float:
    return (crown_top_z(t) - PAWL_Z) / geom()["uz"]


def size_spine_mm(size: str) -> float:
    """Spine long enough to pass the pawl at the top of the size by H1's 16 mm tail (300 - s_pawl(23))."""
    return s_pawl(SIZES[size][1]) + (H1_SPINE_MM - s_pawl(23.0))


def size_travel_mm(size: str) -> float:
    lo, hi = SIZES[size]
    return (crown_top_z(hi) - crown_top_z(lo)) / geom()["uz"]


def size_rack_mm(size: str) -> float:
    """Rack = travel + H1's engagement / end allowance (300 - 203.2)."""
    h1_travel = (crown_top_z(23.0) - crown_top_z(15.0)) / geom()["uz"]
    return size_travel_mm(size) + (H1_RACK_MM - h1_travel)


def geometry_with_leg(leg_mm: float) -> Path:
    """geometry.yaml copy with another crown leg length (scratch, outputs/crown_diet/)."""
    import yaml
    p = OUT / f"geometry_leg{leg_mm:.1f}.yaml"
    if not p.exists():
        g = copy.deepcopy(geom()["g"])
        g["frame"]["members_topology"]["crown"]["leg_length_along_axis"] = float(leg_mm)
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(g, sort_keys=False))
    return p


def leg_section(od: float = 16.0, n_ud: int = 8):
    """Crown leg tube [twill +-45 / UD 0 x n / twill +-45] (frame.yaml leg_section family)."""
    from huntkit.fea.frames import _yaml_layup
    from huntkit.fea.pack5200 import _sec
    tw = {"angle": 45, "material": "cfrp_t300_3k_woven_epoxy_ply"}
    ud = {"angle": 0, "material": "cfrp_t700_ud_epoxy_ply"}
    return _sec(_yaml_layup({"type": "composite_tube", "od": float(od), "layup": [tw] + [ud] * n_ud + [tw]}))


def leg_g_per_mm(od: float = 16.0, n_ud: int = 8) -> float:
    s = leg_section(od, n_ud)
    return float(s.A * s.density_kg_m3 * 1e-6)


def spine_g_per_mm() -> float:
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_topopt as ft
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    return float(fm["hardware"]["items"]["tubes: crown_spine"]) / H1_SPINE_MM


def bushing_g(od: float, wall: float, length: float, n: int = 4) -> float:
    """pack5200.hardware_mass formula: n x pi (od + w) w L rho."""
    return n * math.pi * (od + wall) * wall * length * UHMW_RHO * 1e-6


# ================================================================================================ beam model
@dataclasses.dataclass(frozen=True)
class Spec:
    name: str
    torsos: tuple = H1_TORSOS
    leg_mm: float = H1_LEG_MM
    spine_mm: float = H1_SPINE_MM
    leg: tuple = (16.0, 8)            # (od, n UD plies)
    bushing_mm: float = 70.0
    bushing_wall: float = 1.0


def specs() -> dict:
    out = {"h1": Spec("h1")}
    for sz, (lo, hi) in SIZES.items():
        ts = tuple(sorted({lo, hi} | ({19.0} if lo < 19.0 < hi else set())))
        out[f"a_{sz}"] = Spec(f"a_{sz}", ts, round(size_leg_mm(sz), 1), round(size_spine_mm(sz), 1))
        out[f"ac_{sz}"] = Spec(f"ac_{sz}", ts, round(size_leg_mm(sz), 1), round(size_spine_mm(sz), 1),
                               leg=(17.0, 7), bushing_wall=0.5)
    out["e50"] = Spec("e50", bushing_mm=50.0)
    out["c17n7"] = Spec("c17n7", leg=(17.0, 7), bushing_wall=0.5)
    out["c17n6"] = Spec("c17n6", leg=(17.0, 6), bushing_wall=0.5)
    out["c18n6"] = Spec("c18n6", leg=(18.0, 6))
    out["c18n5"] = Spec("c18n5", leg=(18.0, 5))
    return out


def build(spec: Spec, t: float, posts: bool = False) -> dict:
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    over = {"spine_len": float(spec.spine_mm), "bushing_len_mm": float(spec.bushing_mm),
            "bushing_wall_mm": float(spec.bushing_wall)}
    if abs(spec.leg_mm - H1_LEG_MM) > 1e-6:
        over["geometry"] = str(geometry_with_leg(spec.leg_mm))
    if tuple(spec.leg) != (16.0, 8):
        over["leg_section"] = leg_section(*spec.leg)
    return R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=posts, **over),
                           95.0)


def _leg_overlap_forces(res, model) -> dict:
    """End forces of the leg member between the low bushing and the stay top (the H1-governing member)."""
    out = {}
    for tag in "LR":
        mid = f"C{tag}bot-C{tag}530"
        q = next((m for m in res.members if m["id"] == mid), None)
        if q is None:
            continue
        out[tag] = {"z0": float(model["nodes"][f"C{tag}bot"][2]), "z1": float(model["nodes"][f"C{tag}530"][2]),
                    "f0": [float(v) for v in q["end_forces"][0]], "f1": [float(v) for v in q["end_forces"][1]]}
    return out


def beam_runs(spec: Spec, buckling: bool = True, log=print, suffix: str = ""):
    """Every rev C case set (both couple variants: tag C = couple on the crown bar, C_im3 = on the IM3 hooks)
    x torso of ``spec``. Returns (LoadSets for the voxel body, crown rows as frame_cg_recheck._crown_rows +
    the leg overlap-member forces)."""
    from huntkit.fea.load_standard import TABLE, ls1_envelope
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    from .rev_c_verification import TAGS
    env = ls1_envelope("C")
    sets, rows = [], []
    for t in spec.torsos:
        fm, fmp = build(spec, t), None
        for vname, cases in env.items():
            tag = TAGS[vname]
            for c in cases:
                c = copy.copy(c)
                c.params = dict(c.params)
                c.buckling = buckling and vname == "crown_bar" and c.kind != "setdown"
                m = fm
                if c.name == "tall_load_posts":
                    fmp = fmp or build(spec, t, posts=True)
                    m = fmp
                res = c.run(m)
                ls = ft._extract(res, m, c, t, TABLE)
                ls.key = f"{tag}{suffix}:{ls.key}"
                sets.append(ls)
                rows.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": float(c.required_sf),
                             "g": float(c.g_factor), **R._crown_rows(res, m, c),
                             "leg_overlap": _leg_overlap_forces(res, m),
                             "z_legbot": float(m["nodes"]["CRbot"][2])})
        if log:
            log(f"  [{spec.name}] beam model torso {t:g} in")
    return sets, rows


def load_beam(spec: Spec, log=print):
    p = OUT / f"beam_{spec.name}.pkl"
    if p.exists():
        d = pickle.loads(p.read_bytes())
        if d.get("spec") == dataclasses.asdict(spec):
            return d["sets"], d["rows"]
    sets, rows = beam_runs(spec, log=log)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps({"spec": dataclasses.asdict(spec), "sets": sets, "rows": rows}))
    return sets, rows


def crown_margins(rows: list) -> dict:
    """Rev C crown checks (frame_cg_recheck.crown_summary, corner-bond fatigue, rack, pawl cheek) per couple
    variant, plus the flat minimum of each family over both."""
    from . import frame_cg_recheck as R
    from .rev_c_verification import corner_bond_fatigue
    out = {}
    tags = ("C", "C_im3")
    ta = R.torso_adjust(rows, tags=tags)
    for tg in tags:
        cs = R.crown_summary(rows, tg)
        cs["corner_bond_fatigue"] = corner_bond_fatigue(rows, tg)
        cs["rack"] = {"sf": ta[tg]["rack_worst"]["rack_sf"], "set": ta[tg]["rack_worst"]["set"]}
        ch = R.pawl_cheek(ta[tg]["pawl_cheek_force"]["factored_yz"])
        cs["pawl_cheek"] = {"sf": ch["sf_fi"], "set": ta[tg]["pawl_cheek_force"]["set"]}
        cs["_torso_adjust"] = ta[tg]
        out[tg] = cs
    flat = {}
    for k in ("crown_leg", "crown_top_bar", "crown_spine", "corner_bond_avg", "corner_bond_peak", "bushing_bearing",
              "leg_ring_crush", "fatigue", "buckling", "rack", "pawl_cheek"):
        vals = [(out[t][k]["sf"], f"{t}:{out[t][k]['set']}") for t in tags if k in out[t]]
        if vals:
            v = min(vals)
            flat[k] = {"sf": round(float(v[0]), 3), "set": v[1]}
    bf = []
    for t in tags:
        for case, d in out[t]["corner_bond_fatigue"].items():
            if case == "static_carry":
                bf.append((d["peak"]["sf_peak"], f"{t}:{d['peak']['set']}"))
    if bf:
        v = min(bf)
        flat["corner_bond_fatigue_peak"] = {"sf": round(float(v[0]), 3), "set": v[1]}
    out["min"] = flat
    out["min_all"] = round(min(v["sf"] for v in flat.values()), 3)
    return out


# ------------------------------------------------------------------------------------------------ (b) holes in the leg
def leg_hole_zone(rows: list, leg=(16.0, 8)) -> dict:
    """(b, information) a cross-pin through the carbon leg inside the stay. For every set, the leg FPF along the
    overlap member (linear internal forces, no load on the member) x the open-hole factor 0.55 against the case
    factor; returns the lowest z (over all sets and both legs) where a hole would fail, and the travel a pinned
    leg could have: holes may only sit below that z at every setting, and the pin must sit above the top of the
    low bushing (leg bottom + bushing) at the highest setting."""
    sec = leg_section(*leg)
    z_fail, where = 9e9, ""
    lb_top = -9e9
    for r in rows:
        for tag, d in r["leg_overlap"].items():
            f0, f1 = np.asarray(d["f0"]), np.asarray(d["f1"])
            for s in np.linspace(0.0, 1.0, 41):
                f = f0 + (f1 - f0) * s           # internal forces (end_forces convention as frame_fixed)
                # beam runs are at 1 x the case load (crown rows: margin = member sf / factor), so the hole
                # margin is FPF SF x 0.55 / factor
                sf = float(sec.failure(*[float(v) for v in f])["sf"]) * CFRP_OPEN_HOLE / r["factor"]
                z = d["z0"] + s * (d["z1"] - d["z0"])
                if sf < 1.0 and z < z_fail:
                    z_fail, where = z, f"{r['scenario']}:{r['case']}|{r['torso']:g} {tag}"
        lb_top = max(lb_top, r["z_legbot"] + 70.0)
    return {"z_hole_fails_above": round(z_fail, 1), "set": where, "low_bushing_top_at_highest_setting": round(lb_top, 1),
            "max_travel_mm": round(max(0.0, z_fail - lb_top), 1)}


def plunger_lock_check(rows: list) -> dict:
    """(b) index plunger (OD 5 tip, Ti) in a perforated PA66-GF30 strip (t 4, pitch 12.7) on the spine, at the
    factored pawl axial force (the plunger takes the pawl's load path: pawl link unchanged in the beam model)."""
    fz = max(abs(r["pawl_n"][2]) * r["factor"] for r in rows)
    bear = PLUNGER_D * STRIP_T * PA66_UTS_COND                       # tip bearing on the strip, ASSUMPTION allow = UTS
    lig = PIN_PITCH - PLUNGER_D
    shear = 2.0 * STRIP_T * lig * PA66_TAU                            # shear-out to the next hole, 2 planes
    M = fz * (STRIP_T / 2.0 + 1.0)                                    # tip cantilever, 1 mm clearance
    sig = 32.0 * M / (math.pi * PLUNGER_D ** 3)
    from huntkit.materials import load
    ti_y = float(load("ti_6al_4v").require("yield_strength_mpa"))
    return {"factored_axial_n": round(fz, 1), "strip_bearing_sf": round(bear / fz, 2),
            "strip_shear_out_sf": round(shear / fz, 2), "plunger_bending_sf": round(ti_y / sig, 2),
            "resolution_mm": PIN_PITCH, "rack_resolution_mm": 4.0}


# ------------------------------------------------------------------------------------------------ (d) pulley
def pull_strap_d2(rows: list) -> dict:
    """(d2) 1:1 pull-down strap through one 180 deg guide: tail pull to shorten while worn (hoist against the
    crown extension force and the guide friction), from the static-carry and walking crown forces."""
    F1 = max((abs(r["pawl_n"][2]) for r in rows if r["case"] == "static_carry"), default=0.0)
    k = math.exp(PULLEY_MU * math.pi)
    return {"crown_force_static_n": round(F1, 1), "tail_hoist_static_n": round(F1 * k, 1),
            "tail_hoist_walk_1p6g_n": round(1.6 * F1 * k, 1), "limit_n": TAIL_PULL_LIMIT_N,
            "ok": bool(1.6 * F1 * k <= TAIL_PULL_LIMIT_N)}


# ================================================================================================ masses
def block_items() -> dict:
    """The crown + torso-adjust block of the H1 frame, part by part (g, 19 in unit). Sources in ``block_sources``.
    The rev C crown tubes come from the beam model (frame.yaml sections, 430 / 214 / 300 mm)."""
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_topopt as ft
    hw = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)["hardware"]["items"]
    return {
        "crown legs 2 x 430 mm (OD 16, rev C)": hw["tubes: crown_leg"],
        "crown top bar 214 mm (rev C)": hw["tubes: crown_top_bar"],
        "crown spine 300 mm (rev C)": hw["tubes: crown_spine"],
        "crown-corner bondlines 0.8 mm (rev C line)": 2.21,
        "spine clamp": SPINE_CLAMP_G,
        "UHMWPE bushings 4 x 70 mm": hw["UHMWPE bushings (4)"],
        "rack PA66-GF30 300 mm": RACK_G,
        "pawl housing + spring + Ti pawl": PAWL_HOUSING_G,
        "pawl 304 bushings + pin": PAWL_BUSH_G,
        "pulley guides (3)": PULLEY_GUIDES_G,
        "pulley webbing 25 mm x 1.4 m": WEBBING_G_M * PULLEY_WEB_M,
        "cam buckle": CAM_G,
        "release cord + toggle": TORSO_ADJUST_ROW_G - WEBBING_G_M * PULLEY_WEB_M - CAM_G,
    }


BLOCK_SOURCES = {
    "crown legs": "beam model hardware (frame.yaml leg_section, 0.1025 g/mm x 860 mm) = frame_eval 73.8 + crown fix 14.27",
    "crown top bar": "beam model hardware = frame_eval 17.9 + crown fix 2.12",
    "crown spine": "beam model hardware = frame_eval 26.0 + crown fix 3.35",
    "crown-corner bondlines": "frame_mass_production.json crown_fix_lines_g.corner_bondline",
    "spine clamp": "pack5200.HW spine_clamp_g (ASSUMPTION there)",
    "UHMWPE bushings": "pack5200.hardware_mass formula, frame.yaml bushing_len_mm 70",
    "rack": "pack5200.HW rack_g (ASSUMPTION there)",
    "pawl housing": "pack5200.HW pawl_housing_g (ASSUMPTION there)",
    "pawl 304 bushings": "frame_branch.pack_numbers pawl 9.94",
    "pulley guides": "pack5200.HW pulley_guides_g (ASSUMPTION there)",
    "pulley webbing / cam / cord": "ledger torso-adjust row 41.7 = webbing 1.4 m x 18 g/m + cam 12 + toggle 3 + cord",
}


def ledger_basis() -> dict:
    from huntkit.mass import ledger as L
    rows = L.parts("corrie_b2_h1", "M")
    fr = [r for r in rows if r["system"] == "frame"]
    ta = sum(r["g"] for r in fr if r["name"].startswith("torso adjust"))
    lump = sum(r["g"] for r in fr if "carbon crown as built" in r["name"] or "crown inner plies" in r["name"])
    return {"pack_g": float(L.total("corrie_b2_h1", "M")), "torso_adjust_g": float(ta),
            "crown_lump_g": float(lump), "frame_g": float(sum(r["g"] for r in fr if not r["name"].startswith("torso adjust")))}


@dataclasses.dataclass(frozen=True)
class Option:
    """A buildable combination. ``kit``: per-size crown kits (a); ``lock``: 'pawl+pulley' (H1) | 'pawl' (d1) |
    'pawl+strap' (d2) | 'plunger' (b); ``leg``: (od, n UD); ``bushing``: (length, wall)."""
    name: str
    kit: bool = False
    lock: str = "pawl+pulley"
    leg: tuple = (16.0, 8)
    bushing: tuple = (70.0, 1.0)


def option_mass(o: Option, size: str = "M") -> dict:
    """Block mass change against H1 at the size's nominal unit (S 16.5, M 19, L 21.5 in), item by item."""
    d: dict = {}
    gpm0 = leg_g_per_mm()
    gpm = leg_g_per_mm(*o.leg)
    leg_mm = size_leg_mm(size) if o.kit else H1_LEG_MM
    d["crown legs"] = 2 * (gpm * leg_mm - gpm0 * H1_LEG_MM)
    if o.kit:
        d["spine cut per size"] = spine_g_per_mm() * (size_spine_mm(size) - H1_SPINE_MM)
        d["rack cut per size (strip part)"] = RACK_STRIP_G_MM * (size_rack_mm(size) - H1_RACK_MM)
    b0 = bushing_g(16.0, 1.0, 70.0)
    d["UHMWPE bushings"] = bushing_g(o.leg[0], o.bushing[1], o.bushing[0]) - b0
    web_cut = 0.0
    if o.kit and o.lock == "pawl+pulley":
        web_cut = 3.0 * (size_travel_mm(size) - (crown_top_z(23.0) - crown_top_z(15.0)) / geom()["uz"]) / 1000.0
        d["pulley webbing shorter (3 x travel cut)"] = WEBBING_G_M * web_cut
    if o.lock in ("pawl", "pawl+strap", "plunger"):
        d["pulley webbing 1.4 m"] = -WEBBING_G_M * PULLEY_WEB_M
        d["cam buckle"] = -CAM_G
        d["pulley guides"] = -PULLEY_GUIDES_G
    if o.lock == "pawl+strap":
        d["1:1 pull-down strap 0.45 m"] = WEBBING_G_M * D2_WEB_M
        d["one guide kept (guide A)"] = PULLEY_GUIDES_G / 3.0
    if o.lock == "plunger":
        holes = int(size_rack_mm(size) // PIN_PITCH) if o.kit else int(H1_RACK_MM // PIN_PITCH)
        d["rack -> perforated strip (holes)"] = -holes * math.pi / 4 * PLUNGER_D ** 2 * STRIP_T * PA66_RHO * 1e-6
        d["Ti pawl + spring -> index plunger"] = PLUNGER_G - PAWL_SPRING_G
        d["release cord + toggle (plunger pulled at the housing)"] = -(TORSO_ADJUST_ROW_G - WEBBING_G_M * PULLEY_WEB_M - CAM_G)
    if o.leg[0] >= 18.0:
        d["printed sleeve: none if the wall drops to 3.41 mm (see body check c18)"] = 0.0
    d = {k: round(v, 2) for k, v in d.items() if abs(v) > 1e-9 or "printed" in k}
    tot = round(sum(d.values()), 1)
    return {"items": d, "delta_g": tot}


def pack_mass(o: Option, size: str = "M") -> dict:
    lb = ledger_basis()
    dm = option_mass(o, size)["delta_g"]
    return {"frame_g": round(lb["frame_g"] + dm, 1), "pack_g": round(lb["pack_g"] + dm, 1), "delta_g": dm}


# ================================================================================================ voxel body
def _h1_solid():
    from . import frame_h1 as H1
    return np.load(H1.OUT / "h1_final.npz")["solid"]


def sleeve_open_solid(r_open: float = 10.0, z_top: float = 290.0) -> tuple:
    """H1 solid with the empty sleeve below ``z_top`` opened from r 9 to ``r_open`` (outside the z 234 joint
    zone and the spreader-clip sections, as BL-007 (c)). Returns (solid, removed g)."""
    from . import frame_fixed as FF
    from . import frame_h1 as H1
    from .frame_topopt import SLEEVE_Z0
    c = H1.base()
    s = _h1_solid().copy()
    z = c["cen"][:, 2]
    r = FF._stay_r(c["cen"])
    cut = (r < r_open) & (z >= SLEEVE_Z0) & (z < z_top) & ~FF._freeze_z(z) & s
    s &= ~cut
    return s, float(cut.sum() * H1.H ** 3 * 1.06e-3)


def bore20_solid() -> tuple:
    """(c18) bore 18 -> 20 over the whole sleeve (z 160-544): H1 solid with r < 10 removed (wall 4.41 -> 3.41)."""
    from . import frame_fixed as FF
    from . import frame_h1 as H1
    from .frame_topopt import SLEEVE_Z0
    c = H1.base()
    s = _h1_solid().copy()
    z = c["cen"][:, 2]
    r = FF._stay_r(c["cen"])
    cut = (r < 10.0) & (z >= SLEEVE_Z0) & s
    s &= ~cut
    return s, float(cut.sum() * H1.H ** 3 * 1.06e-3)


def body_check(name: str, solid: np.ndarray, sets: list, log=print) -> dict:
    """H1's rev C body checks (FI99 strength, fatigue at 1.6 g / PAHT 0.30, creep, A's branch buckling, z 234
    joint) of ``solid`` on H1's domain under ``sets``."""
    from . import frame_fixed as FF
    from . import frame_h1 as H1
    from . import frame_comp_d as D
    c = H1.base()
    f, ev = FF._eval(c["dom"], solid, sets)
    bk = H1.buckling(f)
    jc = H1.joint_check(f)
    out = {"name": name, "raster_g": D.mass_g(solid, H1.H, 1060.0), "min": ev["min"], "governing": ev["governing"],
           "by_torso": H1.by_torso(ev),
           "buckling_min": min(v["margin"] for v in bk.values() if v["margin"] is not None),
           "joint_strength": jc["min_strength"], "joint_fatigue": jc["min_fatigue"]}
    if log:
        log(json.dumps({k: out[k] for k in ("name", "raster_g", "min", "buckling_min", "joint_fatigue")}, default=float))
    return out


def _cached(name, fn):
    p = OUT / name
    if p.exists():
        return pickle.loads(p.read_bytes())
    v = fn()
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps(v))
    return v


def _retag(sets, size):
    out = []
    for s in sets:
        s2 = copy.copy(s)
        tg, rest = s.key.split(":", 1)
        s2.key = f"{tg}@{size}:{rest}"
        out.append(s2)
    return out


# ================================================================================================ driver
OPTIONS = (
    Option("H1 today"),
    Option("(a) 3 crown kits", kit=True),
    Option("(b) index plunger", lock="plunger"),
    Option("(c) OD 17 x 7 UD legs", leg=(17.0, 7), bushing=(70.0, 0.5)),
    Option("(c) OD 18 x 6 UD legs", leg=(18.0, 6)),
    Option("(d1) pawl only, no pulley", lock="pawl"),
    Option("(d2) pawl + 1:1 strap", lock="pawl+strap"),
    Option("(e) bushings 50 mm", bushing=(50.0, 1.0)),
    Option("(a)+(d2)", kit=True, lock="pawl+strap"),
    Option("(a)+(d1)", kit=True, lock="pawl"),
    Option("(a)+(d1)+(e)", kit=True, lock="pawl", bushing=(50.0, 1.0)),
    Option("(a)+(d1)+(c17)", kit=True, lock="pawl", leg=(17.0, 7), bushing=(70.0, 0.5)),
    Option("(a)+(d2)+(c17)", kit=True, lock="pawl+strap", leg=(17.0, 7), bushing=(70.0, 0.5)),
)
RECOMMENDED = "(a)+(d1)+(c17)"


def run_all(log=print) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    sp = specs()
    beams = {k: load_beam(s, log=log) for k, s in sp.items()}
    crown = {k: crown_margins(rows) for k, (_, rows) in beams.items()}
    from . import frame_comp_d as D
    h1_sets, _ = D.load_sets(log=None)
    # body: H1 reproduced on the cached rev C sets, then the crown-kit sets on the H1 body, the opened sleeve,
    # the 20 mm bore (c18) and the 50 mm bushings (e)
    body = {"h1": _cached("body_h1.pkl", lambda: body_check("h1", _h1_solid(), h1_sets, log=log))}
    kit_sets = sum((_retag(beams[f"a_{z}"][0], z) for z in SIZES), [])
    body["a"] = _cached("body_a.pkl", lambda: body_check("a", _h1_solid(), kit_sets, log=log))
    s_open, g_open = sleeve_open_solid()
    body["a_sleeve"] = _cached("body_a_sleeve.pkl", lambda: {**body_check("a_sleeve", s_open, kit_sets, log=log),
                                                               "removed_g": g_open})
    s20, g20 = bore20_solid()
    body["c18n6"] = _cached("body_c18n6.pkl", lambda: {**body_check("c18n6", s20, beams["c18n6"][0], log=log),
                                                         "removed_g": g20})
    body["c17n7"] = _cached("body_c17n7.pkl", lambda: body_check("c17n7", _h1_solid(), beams["c17n7"][0], log=log))
    ac_sets = sum((_retag(beams[f"ac_{z}"][0], z) for z in SIZES), [])
    body["ac"] = _cached("body_ac.pkl", lambda: body_check("ac", _h1_solid(), ac_sets, log=log))
    # (e) needs no body run: the voxel model spreads each bushing force over +-20 mm of sleeve whatever the
    # bushing length (frame_topopt.assemble_loads), and the beam forces of e50 equal H1's (checked in the tests)
    holes = leg_hole_zone(beams["h1"][1])
    plunger = plunger_lock_check(beams["h1"][1])
    strap = pull_strap_d2(beams["h1"][1])
    masses = {o.name: {sz: pack_mass(o, sz) | {"items": option_mass(o, sz)["items"]} for sz in SIZES} for o in OPTIONS}
    lb = ledger_basis()
    blk = block_items()
    out = {"date": "2026-11-11", "ticket": "BL-017", "ledger": lb,
           "block_g": {k: round(v, 2) for k, v in blk.items()}, "block_total_g": round(sum(blk.values()), 1),
           "sizes": {sz: {"torso_in": SIZES[sz], "leg_mm": round(size_leg_mm(sz), 1),
                          "spine_mm": round(size_spine_mm(sz), 1), "rack_mm": round(size_rack_mm(sz), 1),
                          "travel_mm": round(size_travel_mm(sz), 1),
                          "overlap_top_mm": round(overlap_mm(SIZES[sz][1], size_leg_mm(sz)), 1),
                          "overlap_bottom_mm": round(overlap_mm(SIZES[sz][0], size_leg_mm(sz)), 1),
                          "leg_bottom_z_lowest": round(crown_top_z(SIZES[sz][0]) - size_leg_mm(sz) * geom()["uz"], 1)}
                     for sz in SIZES},
           "specs": {k: dataclasses.asdict(s) for k, s in sp.items()},
           "crown": {k: {"min": v["min"], "min_all": v["min_all"]} for k, v in crown.items()},
           "body": body, "leg_holes": holes, "plunger": plunger, "strap_d2": strap, "masses": masses,
           "recommended": RECOMMENDED}
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    out["screens"] = [plot_summary(out, SCREENS / f"{SHOT}_1.png")]
    return out


# ================================================================================================ figure
def plot_summary(out: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = [o.name for o in OPTIONS if o.name != "H1 today"]
    cols = {"S": "#1baf7a", "M": "#2a78d6", "L": "#eb6834"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 6.6), gridspec_kw={"width_ratios": [1.25, 1]})
    fig.patch.set_facecolor("#fcfcfb")
    for ax in (ax1, ax2):
        ax.set_facecolor("#fcfcfb")
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    y = np.arange(len(names))
    w = 0.26
    for i, sz in enumerate(SIZES):
        v = [-out["masses"][n][sz]["delta_g"] for n in names]
        ax1.barh(y + (i - 1) * w, v, height=w, color=cols[sz], label=f"size {sz} ({SIZES[sz][0]:g}-{SIZES[sz][1]:g} in)")
        for yy, vv in zip(y + (i - 1) * w, v):
            ax1.text(max(vv, 0) + 0.8, yy, f"{vv:.0f}", va="center", fontsize=7)
    ax1.axvline(60.0, color="#0b0b0b", ls="--", lw=1.1)
    ax1.text(60.5, -0.9, "goal 60 g", fontsize=8)
    ax1.set_yticks(y, names, fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("saving on the crown + torso-adjust block, g (1 oz = 28.3 g)")
    ax1.set_title("Saving per option and size (H1 = 0)", loc="left", fontsize=11)
    ax1.legend(fontsize=8, frameon=False, loc="lower right")
    # margins
    fams = [("crown_leg", "legs FPF"), ("crown_top_bar", "top bar FPF"), ("crown_spine", "spine FPF"),
            ("corner_bond_peak", "corner bond peak"), ("leg_ring_crush", "leg ring crush"), ("buckling", "frame buckling")]
    keys = [("h1", "H1"), ("a_S", "(a) S"), ("a_M", "(a) M"), ("a_L", "(a) L"), ("e50", "(e) 50 mm"),
            ("c17n7", "(c) 17x7"), ("c17n6", "(c) 17x6"), ("c18n6", "(c) 18x6"), ("c18n5", "(c) 18x5"),
            ("ac_S", "(a)+(c17) S"), ("ac_M", "(a)+(c17) M"), ("ac_L", "(a)+(c17) L")]
    M = np.array([[out["crown"][k]["min"].get(f, {"sf": np.nan})["sf"] for f, _ in fams] for k, _ in keys])
    im = ax2.imshow(np.clip(M, 0.8, 2.0), cmap="RdYlGn", vmin=0.8, vmax=2.0, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax2.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8,
                     color="#0b0b0b" if M[i, j] >= 1.0 else "#ffffff", weight="bold" if M[i, j] < 1.0 else None)
    ax2.set_xticks(range(len(fams)), [f for _, f in fams], rotation=35, ha="right", fontsize=8)
    ax2.set_yticks(range(len(keys)), [k for _, k in keys], fontsize=8.5)
    b = out["body"]
    ax2.set_title("Crown margins, rev C (min of 2 couples, all cases)\n"
                  f"body fatigue: H1 {b['h1']['min']['fatigue']:.2f}, (a) kits {b['a']['min']['fatigue']:.2f}, "
                  f"(a)+sleeve cut {b['a_sleeve']['min']['fatigue']:.2f}", loc="left", fontsize=9.5)
    fig.colorbar(im, ax=ax2, fraction=0.04, pad=0.02, label="margin (SF / requirement)")
    rec = out["masses"][RECOMMENDED]
    fig.suptitle(f"BL-017 crown block diet: {RECOMMENDED} saves {-rec['S']['delta_g']:.0f} / {-rec['M']['delta_g']:.0f} / "
                 f"{-rec['L']['delta_g']:.0f} g (S / M / L) and keeps the adjustable torso", x=0.01, ha="left",
                 fontsize=12)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=105, facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(path)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "all"
    if cmd == "all":
        r = run_all()
        print(json.dumps({n: {s: v["delta_g"] for s, v in m.items()} for n, m in r["masses"].items()}, indent=1))
    elif cmd == "beam":
        for k, s in specs().items():
            _, rows = load_beam(s, log=None)
            print(k, json.dumps(crown_margins(rows)["min"]))
    else:
        print("usage: python -m huntkit.gendesign.crown_diet [all|beam]")


if __name__ == "__main__":
    main()
