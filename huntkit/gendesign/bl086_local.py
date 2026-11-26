"""BL-086 local checks on B86 (B85 with the non-tee details reworked), every metal fatigue row on the Yahr DESIGN
S-N curve (orchestrator call 2026-11-26), fretting allowances as in BL-085 (metal clamp / contact edge 0.6, polymer
contact 0.85 with Kt 1.15), walk = the envelope of bag carry x 1.6 and meat_straps x 1.6 / 2.0 (``bl086_global``),
C6p in every envelope.

What B86 changes against B85 (and why, from the BL-086 baseline run on the design curve):

* **Stay gusset bolts z 105 / 135 -> z 78 / 95.** The stays bend fore-aft (the bolt axis y is the bending plane), so
  a y-bolt hole sits on the extreme fibre. Walk stress at the hole fibre: z 135 54 MPa, z 95 26 MPa, z 78 15 MPa
  (z 155-380 is a 70 MPa plateau). The gusset spine runs z 68-170; the printed foot-cup sleeve is cut to z 66
  (new part ``foot_cup_86``).
* **Upper hip tie (z 155): no bolt, no hole in the rung.** The tie force is compression in every case (the post
  pushes the upper rung aft: 783 N factored, 417 N walk; the only reversal is 33 N in single-stay set-down). A printed
  PAHT-CF saddle (``tie_saddle_86``) bears on the post front leg and on the rung front half; printed snap arms round
  the rung hold it in place (positioning only). Rung contact is polymer (Kt 1.15, fretting 0.85).
* **Lower hip tie (z 85): bolt kept, printed saddle washer behind the rung.** The tie pulls the lower rung forward in
  every case; the nut-side bearing patch (the 14 mm washer of B81) was half the bore peak. A 25 mm PAHT-CF saddle
  (+/-80 deg) under an M5 x 15 fender washer spreads it; the bolt is snug (0.5 N m, nylon-insert locknut, no preload
  credited, ASSUMPTION SNUG-LT), so the saddle carries the tie pull in bearing only. A 6061 saddle washer was tried
  first: its edge is a metal contact at the rung's back crown (Kt 2, fretting 0.6) and fails at 0.94.
* **Upper rung saddle plug: flared head** (40 mm along the stay, 140 deg) because the plug bears on the stay at the
  top of the lumbar node where the stay walk stress is 69 MPa (a row B81 / B85 did not check on the stay side).
* **Front angle leg: 1 x 1/8 6061 doubler strip on each leg** (90 mm, on the front face under the Ti mount, bolted by
  the 3 mount bolts of that side + 2 end bolts), credited by bending-stiffness share only (no composite action). The
  mount face and the hip pin move 3.2 mm forward (modelled in ``bl086_global.build``).
* **Leg-end bushings 70 -> L mm** (``CFG86['bush_len']``) to lower the bushing hoop at the 73 MPa stay section.

Bonded sleeve doublers were studied and rejected (``bond_check``): the bond peak at a doubler end on the stay
(Volkersen shear lag, toughened epoxy) is far above any cited adhesive fatigue strength.

Units mm, N, MPa, g.
"""
from __future__ import annotations

import contextlib
import math
from functools import lru_cache

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl085_tee as T

CFG86 = {
    "mid_tee": "saddle", "stay_bolt_z": (78.0, 95.0), "upper_tie": "saddle",
    "tie_saddle_len": 26.0, "tie_saddle_deg": 60.0,        # printed upper-tie saddle on the rung: 26 mm along x, +/-60 deg
    "lt_washer_len": 25.0, "lt_washer_deg": 80.0,          # lower-tie 6061 saddle washer (half-shell of p-4573)
    "plug_len_upper": 50.0, "plug_deg": 65.0,              # flared upper rung plug head on the stay
    "plug_len_lower": 20.0,
    "bush_len": 110.0, "bush_contact_deg": 30.0,
    "leg_doubler": {"w": BQ.IN, "t": 0.125 * BQ.IN, "n": 2, "len": 90.0},
}
KT_POLY = T.CFG85["kt_saddle"]          # 1.15 (ASSUMPTION SADDLE-KT, BL-085)
KT_EDGE = T.CFG85["kt_clamp_edge"]      # 2.0 at a metal contact edge


def cfg86(**over) -> dict:
    return {**BQ.CFG0, **CFG86, **over}


# ----------------------------------------------------------------------------- design-curve allowables
def smax_r0(contact: str | None = None, cfg: dict | None = None) -> float:
    """R 0 (0 -> S_max) allowable at 1e5 on the Yahr design curve, Goodman on Su 290, with the BL-085 fretting
    factor for the contact type (None: open hole / smooth, 'metal' 0.6, 'poly' 0.85)."""
    sa = T.allowable_sa(contact, {**T.CFG85, **(cfg or {})})
    su = T.sn_basis()["Su"]
    return 2 * sa * su / (su + sa)


@contextlib.contextmanager
def design_curve():
    """Route every BL-081 local fatigue row through the design curve: ``bl081_concept_b.fat_allow_local`` is the one
    allowable function the BL-081 rows call (hole, gusset, hip, fairlead, bushing)."""
    old = BQ.fat_allow_local
    smax = smax_r0(None)
    BQ.fat_allow_local = lambda kt=1.0, N=1e5: smax / kt
    try:
        yield smax
    finally:
        BQ.fat_allow_local = old


# ----------------------------------------------------------------------------- solid-FE unit fields (cached)
def _cache():
    p = BQ.REPO / "outputs" / "bl086"
    p.mkdir(parents=True, exist_ok=True)
    return p


@lru_cache(maxsize=None)
def saddle_hole_units(tube_key: str = "t1000_065", Ls: float = 25.0, half_deg: float = 80.0) -> dict:
    """Bore stress tensors (hole 0 / hole 1, same layout as ``bl081_local.hole_units``) for a saddle washer pushing the
    wall inward round each bore (1 N resultant over Ls x +/-half_deg, cosine), on the BL-081 hole submodel mesh."""
    from huntkit.fea.tube_solid import Hole, TubeFE, TubeModel
    path = _cache() / f"saddle_units_{tube_key}_{Ls:g}_{half_deg:g}.npz"
    if path.exists():
        d = np.load(path)
        return {"S0": d["S0"], "S1": d["S1"]}
    st = BQ.STOCK[tube_key]
    L = BL.SUB_L
    m = TubeModel(L=L, od=st["od"], t=st["t"], holes=[Hole(L / 2, 0.0, BQ.HOLE_D)], h=2.0, h_hole=0.25)
    fe = TubeFE(m)
    S0, S1 = [], []
    for th in (0.0, math.pi):
        u = fe.solve(fe.patch_pressure(L / 2 - Ls / 2, L / 2 + Ls / 2, th, math.radians(half_deg), 1.0, "outer"))
        t0 = fe.bore_stress_tensors(u, 0)
        t1 = fe.bore_stress_tensors(u, 1)
        S0.append(np.array([t0[v] for v in sorted(t0)]))
        S1.append(np.array([t1[v] for v in sorted(t1)]))
    S0, S1 = np.array(S0), np.array(S1)
    np.savez(path, S0=S0, S1=S1)
    return {"S0": S0, "S1": S1}


@lru_cache(maxsize=None)
def ring_unit(tube_key: str, Ls: float, half_deg: float) -> float:
    """Peak |hoop| (MPa per kN) of a cosine contact patch Ls x +/-half_deg on a plain tube (130 mm, mid-length): the
    ring part of a saddle / plug / pad bearing load. Cached to disk."""
    import json
    path = _cache() / "ring_units.json"
    db = json.loads(path.read_text()) if path.exists() else {}
    key = f"{tube_key}|{Ls:g}|{half_deg:g}"
    if key in db:
        return db[key]
    from huntkit.fea.tube_solid import TubeFE, TubeModel
    st = BQ.STOCK[tube_key]
    L = 130.0
    x0, x1 = L / 2 - Ls / 2, L / 2 + Ls / 2
    m = TubeModel(L=L, od=st["od"], t=st["t"], h=2.0, refine_x=((x0 - 4, x1 + 4, 1.4),))
    fe = TubeFE(m)
    u = fe.solve(fe.patch_pressure(x0, x1, 0.0, math.radians(half_deg), 1000.0, "outer"))
    v = fe.surface_hoop(u, x0 - 6, x1 + 6)
    db[key] = v
    path.write_text(json.dumps(db, indent=1))
    return v


def bush_units(tube_key: str, bush_len: float, contact_deg: float) -> dict:
    """``bl081_local.bushing_units`` with a disk cache (the solid FE takes several minutes per length)."""
    import json
    path = _cache() / "bush_units.json"
    db = json.loads(path.read_text()) if path.exists() else {}
    key = f"{tube_key}|{bush_len:g}|{contact_deg:g}"
    if key not in db:
        U = BL.bushing_units(tube_key, bush_len, contact_deg)
        db[key] = {w: {k: float(v) for k, v in d.items() if np.isscalar(v)} for w, d in U.items()}
        path.write_text(json.dumps(db, indent=1))
    return db[key]


def hole_peak_saddle(tube_key, sec6, wall0, wall1, sad, Ls, half_deg):
    """``bl081_local.hole_peak`` with the 14 mm washer units replaced by the saddle-washer units."""
    U = BL.hole_units(tube_key)
    Us = saddle_hole_units(tube_key, Ls, half_deg)
    c = np.r_[sec6, wall0[0], wall0[1], wall1[0], wall1[1]]
    S0 = np.tensordot(c, U["S0"][:10], axes=1) + sad[0] * Us["S0"][0] + sad[1] * Us["S0"][1]
    S1 = np.tensordot(c, U["S1"][:10], axes=1) + sad[0] * Us["S1"][0] + sad[1] * Us["S1"][1]
    pk = max(np.abs(np.linalg.eigvalsh(S0)).max(), np.abs(np.linalg.eigvalsh(S1)).max())
    h = BL.hole_peak(tube_key, sec6, wall0, wall1)
    h["peak"] = float(pk)
    return h


# ----------------------------------------------------------------------------- rows
def _nominal(rec_f, tube_key) -> float:
    st = BQ.STOCK[tube_key]
    ro, ri = st["od"] / 2, st["od"] / 2 - st["t"]
    A = math.pi * (ro ** 2 - ri ** 2)
    I = math.pi * (ro ** 4 - ri ** 4) / 4
    N, Vy, Vz, Tq, My, Mz = rec_f
    return abs(N) / A + math.hypot(My, Mz) * ro / I


def hole_rows_86(g: dict, cfg: dict) -> list[dict]:
    """BL-081 hole rows (design curve) for every station that still has a hole; the upper hip-tie stations are gone
    (no hole); the lower hip-tie stations use the saddle-washer units."""
    zu, zl = cfg["rung_z"][1], cfg["rung_z"][0]
    keep_g = {**g}
    keep_g["stations"] = {k: v for k, v in g["stations"].items() if f"rung z{zu:g}" not in k or "hip tie" not in k}
    keep_g["walk"] = {k: v for k, v in g["walk"].items() if f"rung z{zu:g}" not in k or "hip tie" not in k}
    lower = {k for k in g["stations"] if f"rung z{zl:g}" in k and "hip tie" in k}
    plain_g = {**keep_g, "stations": {k: v for k, v in keep_g["stations"].items() if k not in lower},
               "walk": {k: v for k, v in keep_g["walk"].items() if k not in lower}}
    with design_curve() as fa:
        rows = BL.hole_rows(plain_g, cfg)
        sts = {s["name"]: s for s in BQ.stations(cfg)}
        Ls, hd = cfg["lt_washer_len"], cfg["lt_washer_deg"]
        for name in sorted(lower):
            s = sts[name]
            st = BQ.STOCK[s["tube"]]
            R_m = st["od"] / 2 - st["t"] / 2
            worst_s = worst_f = None
            for kind, recs in (("static", g["stations"][name]), ("fatigue", g["walk"][name])):
                for rec in recs:
                    sec, frame = BL.sub_forces(rec["f"], rec["R"], s["axis"])
                    w0, w1 = BL._walls(rec["link"], frame, R_m)
                    FY = float(np.asarray(rec["link"][:3]) @ frame[1])
                    sad = (max(-FY, 0.0), max(FY, 0.0))
                    h = hole_peak_saddle(s["tube"], sec, w0, w1, sad, Ls, hd)
                    if kind == "static":
                        sig_net = math.sqrt(h["s_max_nom"] ** 2 + 3 * h["tau"] ** 2) * h["A"] / (h["A"] - BQ.HOLE_D * st["t"] * 2)
                        m = min(BQ.BRG_Y_ED2 / max(h["brg"], 1e-9), BQ.FY_6061 / sig_net)
                        if worst_s is None or m < worst_s["margin"]:
                            worst_s = {"margin": m, "brg": h["brg"], "sig_net": sig_net, "case": rec["case"]}
                    else:
                        ref = max(h["s_hole_nom"], h["tau"] * math.sqrt(3))
                        sf = max(h["peak"], ref)
                        m = fa / sf
                        if worst_f is None or m < worst_f["margin"]:
                            worst_f = {"margin": m, "peak": h["peak"], "ref": ref, "case": rec["case"],
                                       "nom": h["s_max_nom"], "sad": max(sad)}
            rows.append({"item": "2", "row": f"{name} (saddle washer): static (bearing / net section)", "kind": "strength",
                         "value": worst_s["brg"], "allow": BQ.BRG_Y_ED2, "margin": worst_s["margin"],
                         "basis": f"bearing {worst_s['brg']:.0f} MPa vs 386, net-section VM {worst_s['sig_net']:.0f} vs 241; "
                                  f"{worst_s['case']}"})
            rows.append({"item": "2", "row": f"{name} (saddle washer): fatigue 1e5 walk, design curve", "kind": "fatigue",
                         "value": worst_f["peak"], "allow": fa, "margin": worst_f["margin"],
                         "basis": f"solid FE bore peak {worst_f['peak']:.0f} MPa with the {Ls:g} mm x +/-{hd:g} deg saddle "
                                  f"washer ({worst_f['sad']:.0f} N) vs design R0 {fa:.0f}; {worst_f['case']}"})
            # printed saddle washer: polymer contact on the rung's back half (snug bolt, no preload credited)
            Ff = max(max(-float(np.asarray(r["link"][:3]) @ BL.sub_forces(r["f"], r["R"], s["axis"])[1][1]),
                         float(np.asarray(r["link"][:3]) @ BL.sub_forces(r["f"], r["R"], s["axis"])[1][1]))
                     for r in g["stations"][name])
            sf_nom = max(_nominal(r["f"], s["tube"]) for r in g["stations"][name])
            area = 2 * math.radians(hd) * 12.7 * Ls * 0.6
            for r_ in _poly_rows(f"{name}: printed saddle washer on the rung", "2", Ff, worst_f["sad"], sf_nom,
                                 worst_f["nom"], s["tube"], Ls, hd, area):
                rows.append(r_)
            P_ = BQ.paht()
            a_w = math.pi / 4 * (15.0 ** 2 - 5.3 ** 2)
            rows.append({"item": "2", "row": f"{name}: M5 x 15 fender washer on the printed saddle: PAHT bearing fatigue",
                         "kind": "fatigue", "value": worst_f["sad"] / a_w, "allow": P_["fat"] * P_["z_hw"],
                         "margin": P_["fat"] * P_["z_hw"] / (worst_f["sad"] / a_w),
                         "basis": f"walk tie pull {worst_f['sad']:.0f} N on the D15 washer annulus {a_w:.0f} mm2 vs 0.30 x z_hw"})
    return rows


def _poly_rows(label, item, F_fact, F_walk, s_fact, s_walk, tube_key, Ls, half_deg, paht_area) -> list[dict]:
    """A printed PAHT pad / saddle / plug bearing on a bare 6061 tube: tube static (VM beam + ring, opposite signs),
    tube fatigue (Kt 1.15 x beam walk + ring walk, design curve x 0.85), PAHT bearing (hot/wet Z) and creep (1 g)."""
    P = BQ.paht()
    ru = ring_unit(tube_key, Ls, half_deg)
    rf, rw = ru * F_fact / 1000.0, ru * F_walk / 1000.0
    vm = math.sqrt(s_fact ** 2 + rf ** 2 + s_fact * rf)
    smax = KT_POLY * s_walk + rw
    Sa = T.allowable_sa("poly", T.CFG85)
    mg = T.goodman_margin(smax / 2, smax / 2, Sa)
    b_f = F_fact / paht_area
    b_1g = F_walk / BQ.G_WALK / paht_area
    return [
        {"item": item, "row": f"{label}: tube wall at limit (beam + ring)", "kind": "strength", "value": vm,
         "allow": BQ.FY_6061, "margin": BQ.FY_6061 / vm,
         "basis": f"beam {s_fact:.0f} MPa factored + ring {rf:.0f} MPa ({F_fact:.0f} N on {Ls:g} mm x +/-{half_deg:g} deg, FE "
                  f"{ru:.0f} MPa/kN), VM opposite signs"},
        {"item": item, "row": f"{label}: tube fatigue, design curve + polymer contact", "kind": "fatigue", "value": smax,
         "allow": smax_r0("poly"), "margin": mg,
         "basis": f"R 0 walk Kt {KT_POLY} x beam {s_walk:.0f} + ring {rw:.0f} MPa ({F_walk:.0f} N); Sa {Sa:.1f} (design x 0.85)"},
        {"item": item, "row": f"{label}: PAHT bearing (hot/wet, compression across the layers)", "kind": "strength",
         "value": b_f, "allow": P["z_hw"], "margin": P["z_hw"] / b_f,
         "basis": f"{F_fact:.0f} N on {paht_area:.0f} mm2 effective (60 % of the projected saddle)"},
        {"item": item, "row": f"{label}: PAHT sustained bearing (creep, 1 g)", "kind": "creep", "value": b_1g,
         "allow": P["z_hw"] * P["creep"], "margin": P["z_hw"] * P["creep"] / b_1g,
         "basis": "1 g share of the walk force vs z_hw x creep_rupture_8h_40c_ratio"},
    ]


def _stay_station_stress(g, name_prefix):
    """Max factored and walk extreme-fibre stress over the records of the stay stations whose name starts with the
    prefix (both sides)."""
    tube = BQ.CFG0["stay"]
    sf = max(_nominal(r["f"], tube) for k, v in g["stations"].items() if k.startswith(name_prefix) for r in v)
    sw = max(_nominal(r["f"], tube) for k, v in g["walk"].items() if k.startswith(name_prefix) for r in v)
    return sf, sw


def plug_rows(g: dict, cfg: dict) -> list[dict]:
    """Rung-end saddle plugs bearing on the stays (z 85 and z 155): the stay side of the plug contact (B81 / B85
    checked only the PAHT)."""
    rows = []
    for z, Ls in ((cfg["rung_z"][0], cfg["plug_len_lower"]), (cfg["rung_z"][1], cfg["plug_len_upper"])):
        keys = [f"plug_L{z:g}", f"plug_R{z:g}"]
        Ff = max(g["links"][k]["F"] for k in keys)
        Fw = max(float(np.linalg.norm(np.asarray(r["links"][k][:3]))) for r in g["walk"]["_links"] for k in keys)
        sf, sw = _stay_station_stress(g, f"stay at plug z{z:g}")
        area = 2 * math.radians(cfg["plug_deg"]) * 12.7 * Ls * 0.6
        rows += _poly_rows(f"stay at the z {z:g} rung plug ({Ls:g} mm head)", "1", Ff, Fw, sf, sw, cfg["stay"], Ls,
                           cfg["plug_deg"], area)
    return rows


def tie_saddle_rows(g: dict, cfg: dict) -> list[dict]:
    """Upper hip tie = printed compression saddle on the rung (no hole)."""
    zu = cfg["rung_z"][1]
    keys = [f"tie_L{zu:g}", f"tie_R{zu:g}"]
    Ff = max(g["links"][k]["F"] for k in keys)
    Fw = max(float(np.linalg.norm(np.asarray(r["links"][k][:3]))) for r in g["walk"]["_links"] for k in keys)
    ymin = min(min(float(np.asarray(r["links"][k])[1]) for r in g["walk"]["_links"] for k in keys),
               min(float(np.asarray(g["links"][k]["vec"])[1]) for k in keys))
    names = [k for k in g["stations"] if k.startswith(f"rung z{zu:g}") and "hip tie" in k]
    tube = cfg["ctube"]
    sf = max(_nominal(r["f"], tube) for k in names for r in g["stations"][k])
    sw = max(_nominal(r["f"], tube) for k in names for r in g["walk"][k])
    Ls, hd = cfg["tie_saddle_len"], cfg["tie_saddle_deg"]
    area = 2 * math.radians(hd) * 12.7 * Ls * 0.6
    rows = _poly_rows(f"upper rung under the printed tie saddle (x +/-{cfg['tie_x']:g})", "6", Ff, Fw, sf, sw, tube, Ls, hd,
                      area)
    P_ = BQ.paht()
    hz = 12.7 * math.sin(math.radians(hd))
    a_w = 2 * 3.0 * (2 * hz + 5.0)              # the two 3 mm side walls of the open saddle frame (bl086_parts.tie_saddle)
    rows.append({"item": "6", "row": "upper tie saddle: side walls in compression (PAHT hot/wet)", "kind": "strength",
                 "value": Ff / a_w, "allow": P_["z_hw"], "margin": P_["z_hw"] / (Ff / a_w),
                 "basis": f"{Ff:.0f} N factored on 2 walls 3 x {2 * hz + 5:.0f} mm = {a_w:.0f} mm2 (Z value, the lower one)"})
    rows.append({"item": "6", "row": "upper tie saddle: side walls, compression fatigue", "kind": "fatigue",
                 "value": Fw / a_w, "allow": P_["fat"] * P_["z_hw"], "margin": P_["fat"] * P_["z_hw"] / (Fw / a_w),
                 "basis": f"walk {Fw:.0f} N, 0.30 x z_hw"})
    rows.append({"item": "6", "row": "upper tie saddle: compression in every walk / limit case (info)", "kind": "info",
                 "value": ymin, "allow": 0.0, "margin": None,
                 "basis": f"min tie force along y {ymin:.0f} N (>= 0 = compression); the 33 N set-down reversal (unfactored "
                          "x 1.5) is held by the saddle's snap arms"})
    return rows


def bushing_rows_86(g: dict, cfg: dict) -> list[dict]:
    """Leg-end and stay-top bushings on the design curve + polymer contact (UHMWPE on bare 6061), with the corrected
    stay beam stress (BL-085 F1): stations at the bushing zones from this global."""
    U = {"mid": bush_units(cfg["stay"], float(cfg["bush_len"]), float(cfg["bush_contact_deg"]))["mid"],
         "end": bush_units(cfg["stay"], 70.0, float(cfg["bush_contact_deg"]))["end"]}      # stay-top bushing stays 70 mm
    walk = {}
    for rec in g["walk"]["_links"]:
        for k in ("bush_low_L", "bush_low_R", "bush_top_L", "bush_top_R"):
            walk[k] = max(walk.get(k, 0.0), float(np.linalg.norm(np.asarray(rec["links"][k])[:2])))
    rows = []
    Sa = T.allowable_sa("poly", T.CFG85)
    for where, keys, pref, lab in (("mid", ("bush_low_L", "bush_low_R"), "stay leg-end zone", "leg-end bushing (z 171-374)"),
                                   ("end", ("bush_top_L", "bush_top_R"), "stay top zone", "stay-top bushing (z 475-545)")):
        F = max(g["links"][k]["F"] for k in keys)
        Fw = max(walk[k] for k in keys)
        sbf, sbw = _stay_station_stress(g, pref)
        sh, shw = U[where]["hoop_peak"] * F / 1000.0, U[where]["hoop_peak"] * Fw / 1000.0
        vm = math.sqrt(sbf ** 2 + sh ** 2 + sbf * sh)
        rows.append({"item": "3", "row": f"stay at the {lab}: static (ring + beam)", "kind": "strength", "value": vm,
                     "allow": BQ.FY_6061, "margin": BQ.FY_6061 / vm,
                     "basis": f"{cfg['bush_len'] if where == 'mid' else 70:g} mm bushing, {F:.0f} N factored -> hoop {sh:.0f} MPa; beam {sbf:.0f} MPa"})
        smax = KT_POLY * sbw + shw
        mg = T.goodman_margin(smax / 2, smax / 2, Sa)
        rows.append({"item": "3", "row": f"stay at the {lab}: fatigue, design curve + polymer contact", "kind": "fatigue",
                     "value": smax, "allow": smax_r0("poly"), "margin": mg,
                     "basis": f"R 0 walk Kt {KT_POLY} x beam {sbw:.0f} + hoop {shw:.0f} MPa ({Fw:.0f} N, {cfg['bush_len'] if where == 'mid' else 70:g} mm "
                              f"bushing); Sa {Sa:.1f}"})
        ov = U[where]["oval_diam_mm"] * F / 1000.0
        rows.append({"item": "3", "row": f"{lab}: bore ovalisation at limit vs leg clearance", "kind": "joint", "value": ov,
                     "allow": 2 * cfg["leg_clear_mm"], "margin": 2 * cfg["leg_clear_mm"] / max(ov, 1e-9),
                     "basis": "n = 2 diametral change (BL-081 method)"})
    return rows


def hip_rows_86(g: dict, cfg: dict) -> list[dict]:
    """BL-081 hip rows on the design curve with the B86 changes: the front-leg mount-hole rows with the doubler strips
    (stiffness share), the tie rows for the lower (bolted) ties only, the upper tie as a saddle (``tie_saddle_rows``)."""
    zu = cfg["rung_z"][1]
    g2 = {**g, "links": {k: v for k, v in g["links"].items() if not (k.startswith("tie_") and f"{zu:g}" in k)},
          "walk": {**g["walk"], "_links": [{"case": r["case"], "links": {k: v for k, v in r["links"].items()
                                                                          if not (k.startswith("tie_") and f"{zu:g}" in k)}}
                                           for r in g["walk"]["_links"]]},
          "members_w": {k: v for k, v in g.get("members_w", {}).items() if not k.startswith(f"tie_L{zu:g}")
                        and not k.startswith(f"tie_R{zu:g}")}}
    with design_curve():
        rows = BL.hip_rows(g2, cfg)
    d = cfg["leg_doubler"]
    t = 0.125 * BQ.IN
    b_leg = 2 * 1.5 * BQ.IN - 2 * BQ.HOLE_D
    b_d = d["n"] * (d["w"] - BQ.HOLE_D)
    share_leg = b_leg * t ** 3 / (b_leg * t ** 3 + b_d * d["t"] ** 3)
    k_st = (BQ.HIP_STAND + d["t"]) / BQ.HIP_STAND      # stand-off grows by the strip: whole tipping couple scaled (conservative)
    out = []
    for r in rows:
        if r["row"].startswith(("Ti mount on the front angle", "front angle leg:")):
            r = {**r, "value": r["value"] * k_st, "margin": r["margin"] / k_st,
                 "basis": r["basis"] + f"; x {k_st:.3f} for the 3.2 mm longer pin stand-off (doubler under the mount)"}
        if r["row"].startswith("front angle leg:"):
            r = {**r, "value": r["value"] * share_leg, "margin": r["margin"] / share_leg,
                 "basis": r["basis"] + f"; x {share_leg:.3f} leg share of the bending stiffness with {d['n']} x 1 x 1/8 doubler "
                                       "strips (net widths, no composite action, ASSUMPTION DOUBLER-SHARE)"}
        out.append(r)
    # doubler strip itself: same curvature -> stress in proportion (same t): check at its holes
    for r in list(out):
        if r["row"] == "front angle leg: fatigue at the mount holes":
            sd = r["value"] * (d["t"] / t)
            out.append({**r, "row": "front-leg doubler strips: fatigue at the mount holes", "value": sd,
                        "margin": r["allow"] / sd, "basis": "same curvature as the leg (stacked, bolted), Kt 2 at the holes"})
    return out


def bond_check(cfg: dict | None = None) -> dict:
    """Why no bonded sleeve doubler: Volkersen shear lag at the end of a 1-1/4 x .120 sleeve bonded on the stay at the
    top of the lumbar node (walk 69 MPa on the stay). ASSUMPTION BOND: toughened two-part epoxy, G 700 MPa, bondline
    0.13 mm (the p-4573 bore gap)."""
    st = BQ.STOCK["t1000_065"]
    E = BQ.E_AL
    t1, t2 = st["t"], 0.120 * BQ.IN
    G, eta = 700.0, 0.13
    lam = math.sqrt(G / eta * (1 / (E * t1) + 1 / (E * t2)))
    q = 69.1 * t1
    frac = E * t2 / (E * t1 + E * t2)
    tau_w = q * lam * frac
    return {"lambda_per_mm": lam, "line_force_walk_n_mm": q, "tau_peak_walk_mpa": tau_w, "tau_peak_factored_mpa": tau_w / 1.6 * 3,
            "verdict": "rejected: walk peak above typical toughened-epoxy fatigue strength on aluminium (order 5-10 MPa at 1e5-1e6)"}
