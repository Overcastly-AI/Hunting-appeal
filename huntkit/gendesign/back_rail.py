"""Back-rail skin pressure at the HA-LS-1 rev C meat case (pack-designer, 2026-11-06).

At the rev C meat CG (190 mm aft of the frame) the rail-and-tissue model of ``spreader.py`` gives 15.4 kPa under the
stay rails, over the 14 kPa comfort limit (Golriz et al. 2017, ``analysis/back_comfort.md``). This module finds the
smallest back-panel change that brings it back to <= 14 kPa, using the SAME model, unchanged:

- rail section: ``spreader.rail_backed`` / ``spreader.rail_section`` (rigid stay on a backer strip on aged foam on a
  25 mm, 60 kPa tissue column; Pasternak shear from the foam),
- along the stay: the Hetenyi beam-on-foundation spread of the bone reaction (``spreader._skin_pressure``),
- loads: ``frame_smooth.meat_normal_n(1.6, e_mm)`` (rev B couple, linear in e) less the bone (part of the meat),
  plus the worst bone side reaction of the production spreader at the named positions (``bone_sides``).

The only thing parametrised here is the rail build: rail (foam) width, backer strip width and thickness, foam grade
and thickness, rail length. ``spreader.py`` is not edited (owner: structural-fea-engineer); :func:`confirm` runs the
full ``spreader.evaluate`` with the chosen rail patched in for the duration of the call, and clears
``spreader._SKIN_CACHE`` before and after every evaluation.

    python -m huntkit.gendesign.back_rail            # study + confirm + screens + JSON + analysis/back_rail.md
    python -m huntkit.gendesign.back_rail --keep-confirm   # re-use the last full check if the chosen rail is the same
    python -m huntkit.gendesign.back_rail --docs-only
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULT = ANALYSIS / "back_rail_results.json"
DOC = ANALYSIS / "back_rail.md"
SCREENS = REPO / "outputs" / "screens"
DATE = "20261106"
E_REVC = 190.0                    # HA-LS-1 rev C meat case, mm aft of the frame (owner 2026-11-06)
E_SWEEP = (150.0, 165.0, 175.0, 181.0, 190.0, 205.0, 223.0)
PEAK_KPA = 14.0                   # Golriz et al., Work 58 (2017): prolonged-carriage limit (back_comfort.md)
MARGIN_KPA = 0.2                  # ASSUMPTION: model resolution (bone on named positions, 0.5 mm section grid)
GUTTER_MIN = 110.0                # ASSUMPTION: keep >= 85 % of the 130 mm air gutter (back_comfort.md ventilation)
BACKER_MAT = "cfrp_t300_3k_woven_epoxy_ply"     # stiffness (as spreader.RAIL_BACKERS)
BACKER_PRICE_MAT = "cfrp_plate_0_90_woven"      # bought 1 mm 2x2 twill plate, water-jet cut: price per m2
SLEEVE_MAT, MESH_MAT = "robic_210d_ripstop", "spacer_mesh_3d"


@dataclass(frozen=True)
class Rail:
    key: str
    name: str
    width: float = 100.0          # foam width, mm (centred on the stay line x +/-115)
    backer_w: float = 60.0        # stiff strip between the stay and the foam
    backer_t: float = 1.02        # 1 mm 2x2 twill (spreader 'tw10')
    foam: str = "xlpe_foam_l200"
    foam_t: float = 10.0          # new thickness; aged = (1 - compression set) x new
    length: float = 420.0         # stay contact length, z 50-470


CURRENT = Rail("r100_b60", "current: 100 mm L200 rail, 60 mm 1 mm twill backer")


def candidates() -> list[Rail]:
    """The levers the model has: backer stiffness and width, foundation (rail) width, foam grade and thickness."""
    out = [CURRENT, Rail("r100_nobacker", "as patterned in v3.1 and booked: 100 mm rail, NO backer strip", backer_t=0.0)]
    for bw in (70, 80, 90, 100):
        out.append(Rail(f"r100_b{bw}", f"100 mm rail, {bw} mm backer", backer_w=bw))
    for bt, lab in ((1.32, "1.3 mm"), (2.04, "2 mm")):
        for bw in (60, 90):
            out.append(Rail(f"r100_b{bw}_t{bt:g}", f"100 mm rail, {bw} mm {lab} backer", backer_w=bw, backer_t=bt))
    for ft in (12.0, 14.0, 16.0):
        out.append(Rail(f"r100_b60_f{ft:g}", f"100 mm rail, {ft:.0f} mm L200 foam", foam_t=ft))
    out.append(Rail("r100_b60_eva", "100 mm rail, 4 mm EVA 45C over 6 mm L200", foam="eva4_xlpe6"))
    out.append(Rail("r100_b60_eva30", "100 mm rail, 10 mm EVA 30C (softer grade)", foam="eva_foam_30c"))
    for w, bw in ((110, 70), (110, 80), (110, 90), (115, 75), (115, 80), (120, 70), (120, 80), (120, 100),
                  (130, 70), (130, 90)):
        out.append(Rail(f"r{w}_b{bw}", f"{w} mm rail, {bw} mm backer", width=float(w), backer_w=float(bw)))
    out.append(Rail("r100_b60_L460", "100 mm rail, 460 mm long (z 30-490)", length=460.0))
    return out


# ---------------------------------------------------------------- rail model (spreader.py functions, parametrised)
def _S():
    from huntkit.gendesign import spreader
    return spreader


def layers(rail: Rail) -> list[dict]:
    S = _S()
    xl = load("xlpe_foam_l200")
    G_x = float(xl.require("shear_modulus_kpa")) / 1000.0
    if rail.foam == "eva4_xlpe6":
        return S.rail_layers("eva4_xlpe6")
    m = load(rail.foam)
    set_ = float(m.require("compression_set_pct")) / 100.0
    if rail.foam == "xlpe_foam_l200":
        curve, G = S.foam_curve(), G_x
    else:   # ASSUMPTION (as spreader.eva_curve): the L200 curve shape scaled to the record's 25 % point; shear in step
        e, s = S.foam_curve()
        k = float(m.require("compression_25pct_kpa")) / 1000.0 / float(np.interp(0.25, e, s))
        curve, G = (e, s * k), G_x * k
    return [{"h": rail.foam_t * (1 - set_), "curve": curve, "G": G, "name": f"{rail.foam_t:g} mm {rail.foam} (aged)"}]


def backer_D(rail: Rail) -> float:
    if rail.backer_t <= 0:
        return 0.0
    m = load(BACKER_MAT)
    E = float(m.get("youngs_modulus_mpa") or m.require("E1_mpa"))
    nu = float(m.get("poisson")) if m.get("poisson") is not None else 0.1      # as spreader.backer_D
    return E * rail.backer_t ** 3 / (12 * (1 - nu ** 2))


def section(rail: Rail, q_line: float, tissue_kpa: float | None = None) -> dict:
    S = _S()
    tk = S.TISSUE_E_KPA if tissue_kpa is None else tissue_kpa
    D = backer_D(rail)
    if D > 0:
        return S.rail_backed(q_line, D, layers(rail), tk, half=rail.width / 2.0, strip_w=rail.backer_w)
    return S.rail_section(q_line, layers(rail), tk, half=rail.width / 2.0)


def meat_force_n(e_mm: float, g_level: float = 1.6) -> float:
    from huntkit.gendesign import frame_smooth as fs
    try:
        return float(fs.meat_normal_n(g_level, e_mm=e_mm))
    except TypeError:                     # older signature (rev B, fixed e = 150): linear in e
        return float(fs.meat_normal_n(g_level)) * e_mm / 150.0


def skin(rail: Rail, e_mm: float, bone_side_n: float, kind: str = "walk", tissue_kpa: float | None = None) -> dict:
    """Peak skin pressure under one rail (the ``spreader._skin_pressure`` method with the rail as a parameter)."""
    S = _S()
    g = {"walk": 1.6, "factored": 3.0, "static": 1.0}[kind]
    bone_total = S.bone_n(kind) if bone_side_n > 0 else 0.0
    H = max(meat_force_n(e_mm, g) - bone_total, 0.0)
    q0 = H / 2.0 / rail.length
    s0 = section(rail, q0, tissue_kpa)
    beta = (s0["k_line"] / (4.0 * S.stay_EI())) ** 0.25
    q = q0 + bone_side_n * beta / 2.0
    s = section(rail, q, tissue_kpa)
    return {"peak_kpa": float(s["peak_kpa"]), "meat_only_kpa": float(s0["peak_kpa"]), "indent_mm": float(s["indent_mm"]),
            "foam_mm": float(s["foam_mm"]), "q_line": float(q), "q_meat": float(q0), "beta_len_mm": 1.0 / beta,
            "x": np.asarray(s["x"]).tolist(), "p_kpa": np.asarray(s["p_kpa"]).tolist()}


# ---------------------------------------------------------------- bone reaction of the production spreader
def production_key() -> str:
    return getattr(_S(), "PRODUCTION_KEY", "sw110c6d")


def bone_sides(opt_key: str | None = None, h: float = 2.0) -> dict:
    """Bone-only stay side reaction (walking) at every named position of the production spreader, N. Independent of
    the meat CG and of the rail (the plate sits on the stays)."""
    S = _S()
    key = opt_key or production_key()
    opt = {o.key: o for o in S.options()}[key]
    pl, info = S.build_plate(opt, h, version="v2", tubes=None if opt.tubes is True else (opt.tubes or ()), lands=opt.pucks)
    out = {}
    for name, xy in S.named_positions("v2").items():
        bw = S.run_case(opt, pl, info, "walk", xy, bone_only=True)
        out[name] = float(max(bw["side_R"], bw["side_L"]))
    return {"spreader": key, "h": h, "sides_n": out}


# ---------------------------------------------------------------- mass and cost
def _areal(mid: str) -> float:
    return float(load(mid).require("areal_density_gsm"))


def mass_g(rail: Rail) -> dict:
    """Both rails: foam + backer + the extra sleeve fabric and mesh width the rail needs (beyond 100 mm)."""
    foam_rho = float(load("xlpe_foam_l200" if rail.foam == "eva4_xlpe6" else rail.foam).require("density_kg_m3"))
    if rail.foam == "eva4_xlpe6":
        foam = 2 * rail.width * rail.length * (4.0 * float(load("eva_foam_45c").require("density_kg_m3"))
                                                 + 6.0 * foam_rho) / 1e9 * 1000.0
    else:
        foam = 2 * rail.width * rail.length * rail.foam_t * foam_rho / 1e6
    backer = 2 * rail.backer_w * rail.length * rail.backer_t * float(load(BACKER_MAT).require("density_kg_m3")) / 1e6
    dw = rail.width - CURRENT.width
    dl = rail.length - CURRENT.length
    # sleeve BP-05 x2 is the rail + 20 mm wide, mesh BP-01 grows with the outer sleeve edges (x +/-(115 + w/2 + 10))
    sleeve = 2 * ((rail.width + 20) * (rail.length + 15) - 120.0 * 435.0) * _areal(SLEEVE_MAT) / 1e6
    mesh = 2 * max(dw, 0.0) / 2.0 * 460.0 * _areal(MESH_MAT) / 1e6 * 1.0 + (max(dl, 0.0) * 370.0 * _areal(MESH_MAT) / 1e6)
    return {"foam_g": foam, "backer_g": backer, "sleeve_extra_g": sleeve, "mesh_extra_g": mesh,
            "total_g": foam + backer + sleeve + mesh}


def cost_usd(rail: Rail) -> float:
    def per_m2(mid):
        c = load(mid).cost_usd
        if c["per"] == "m2":
            return float(c["value"])
        w = float(load(mid).get("usable_width_mm") or load(mid).get("roll_width_mm") or 1400.0) / 1000.0
        return float(c["value"]) / (0.9144 * w)          # per linear yard of the roll
    foam_id = "xlpe_foam_l200" if rail.foam == "eva4_xlpe6" else rail.foam
    a_foam = 2 * rail.width * rail.length / 1e6
    a_back = 2 * rail.backer_w * rail.length / 1e6 if rail.backer_t > 0 else 0.0
    a_sleeve = 2 * (rail.width + 20) * (rail.length + 15) / 1e6
    return a_foam * per_m2(foam_id) + a_back * per_m2(BACKER_PRICE_MAT) + a_sleeve * per_m2(SLEEVE_MAT)


# ---------------------------------------------------------------- full check with the chosen rail patched in
@contextlib.contextmanager
def patched(rail: Rail, e_mm: float):
    """spreader.evaluate with ``rail`` and the meat CG ``e_mm``. Restores everything and clears the skin cache."""
    S = _S()
    from huntkit.gendesign import frame_smooth as fs
    saved = {k: getattr(S, k) for k in ("rail_eval", "GUTTER_HALF", "RAIL_L", "RAIL_W", "RAIL_T") if hasattr(S, k)}
    had_cg = hasattr(S, "MEAT_CG_MM")
    cg0 = getattr(S, "MEAT_CG_MM", None)
    mn0 = fs.meat_normal_n
    S._SKIN_CACHE.clear()
    try:
        S.rail_eval = lambda q, rail_=None, tissue_kpa=S.TISSUE_E_KPA, _r=rail: section(_r, q, tissue_kpa)
        S.GUTTER_HALF = S.STAY_X - rail.width / 2.0
        S.RAIL_L, S.RAIL_W = rail.length, rail.width
        S.RAIL_T = rail.foam_t
        if had_cg:
            S.MEAT_CG_MM = float(e_mm)
        else:
            fs.meat_normal_n = lambda g_level=1.6, _o=mn0: _o(g_level) * float(e_mm) / 150.0
        yield S
    finally:
        for k, v in saved.items():
            setattr(S, k, v)
        if had_cg:
            S.MEAT_CG_MM = cg0
        fs.meat_normal_n = mn0
        S._SKIN_CACHE.clear()


def confirm(rail: Rail, e_mm: float = E_REVC, h: float = 2.0) -> dict:
    """Full spreader check (named positions, 2 mm grid) with this rail: skin, clearance, sheet checks."""
    S_ = _S()
    opt = {o.key: o for o in S_.options()}[production_key()]
    with patched(rail, e_mm) as S:
        r = S.evaluate(opt, h=h, step=None)
    keys = ("skin_peak_kpa", "skin_where", "skin_meat_only_kpa", "clear_walk_min", "clear_fact_min",
            "clear_fact_lean_min", "rail_indent_walk_mm", "sf_fpf", "sf_fatigue", "sandwich_sf_min", "checks", "passes")
    out = {k: r.get(k) for k in keys}
    out.update(rail=rail.key, e_mm=e_mm, spreader=opt.key)
    return out


# ---------------------------------------------------------------- study
def study(sides: dict, log=print) -> dict:
    side = max(sides["sides_n"].values())
    worst = max(sides["sides_n"], key=sides["sides_n"].get)
    rows = []
    base_m = mass_g(CURRENT)["total_g"]
    base_c = cost_usd(CURRENT)
    for r in candidates():
        s = skin(r, E_REVC, side)
        m = mass_g(r)
        rows.append({"rail": asdict(r), "peak_kpa": s["peak_kpa"], "meat_only_kpa": s["meat_only_kpa"],
                     "indent_mm": s["indent_mm"], "gutter_mm": 2 * (115.0 - r.width / 2.0),
                     "mass_g": m["total_g"], "delta_g": m["total_g"] - base_m, "cost_usd": cost_usd(r),
                     "delta_usd": cost_usd(r) - base_c, "pass": s["peak_kpa"] <= PEAK_KPA})
        log(f"  {r.key:16} {s['peak_kpa']:5.2f} kPa  {m['total_g'] - base_m:+6.1f} g")
    for x in rows:
        x["eligible"] = x["peak_kpa"] <= PEAK_KPA - MARGIN_KPA and x["gutter_mm"] >= GUTTER_MIN
    # minimum change: the lightest build that keeps the margin and the air gutter
    chosen = min((x for x in rows if x["eligible"]), key=lambda x: x["delta_g"])
    return {"bone_side_n": side, "bone_where": worst, "rows": rows, "chosen": chosen["rail"]["key"],
            "rule": f"lightest with peak <= {PEAK_KPA - MARGIN_KPA:.1f} kPa and gutter >= {GUTTER_MIN:.0f} mm"}


def rail_by_key(key: str) -> Rail:
    return next(r for r in candidates() if r.key == key)


RELEASED_KEY = "r120_b80"         # the build in panels.yaml (BP-02 / BP-05 / BP-08 / BP-01); test: = study()["chosen"]


def released() -> Rail:
    return rail_by_key(RELEASED_KEY)


def back_panel_pieces() -> dict:
    """Dimensions build_geometry.py uses for the back-panel rows (one source with this study)."""
    r = released()
    sleeve = r.width + 20.0
    return {"rail_w": r.width, "rail_l": r.length, "rail_t": r.foam_t, "backer_w": r.backer_w, "backer_l": r.length,
            "backer_t": r.backer_t, "backer_mat": BACKER_MAT, "sleeve_w": sleeve, "sleeve_l": r.length,
            "mesh_w": 2.0 * (115.0 + sleeve / 2.0), "mesh_h": 440.0}


def sweep(rail: Rail, side: float) -> list[dict]:
    return [{"e_mm": e, **{k: v for k, v in skin(rail, e, side).items() if k in ("peak_kpa", "meat_only_kpa", "indent_mm")}}
            for e in E_SWEEP]


def soft_tissue(rail: Rail, side: float) -> dict:
    S = _S()
    return {"tissue_kpa": S.TISSUE_E_SOFT_KPA, "peak_kpa": skin(rail, E_REVC, side, tissue_kpa=S.TISSUE_E_SOFT_KPA)["peak_kpa"]}


# ---------------------------------------------------------------- screens
def _save(fig, name: str) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    p = SCREENS / name
    fig.savefig(p, dpi=110)
    plt.close(fig)
    try:
        from huntkit.clothsim.report import shrink_png
        shrink_png(p)
    except Exception:  # noqa: BLE001
        pass
    return str(p.relative_to(REPO))


def plot_pressure(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cur, ch = rail_by_key(CURRENT.key), rail_by_key(res["chosen"])
    side = res["bone_side_n"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 6.2))
    for r, col, lab in ((cur, "#b03a2e", "current 100 / 60 mm"), (ch, "#1e6fb0", f"chosen {ch.width:.0f} / {ch.backer_w:.0f} mm")):
        s = skin(r, E_REVC, side)
        x = np.array(s["x"])
        a1.plot(x, s["p_kpa"], color=col, lw=3, label=f"{lab}: peak {s['peak_kpa']:.1f} kPa")
        a1.axvspan(-r.backer_w / 2, r.backer_w / 2, color=col, alpha=0.07)
        sw = res["sweep"][r.key]
        a2.plot([q["e_mm"] for q in sw], [q["peak_kpa"] for q in sw], "o-", color=col, lw=2.5, label=lab)
    a1.axhline(PEAK_KPA, color="k", ls="--", lw=1.2)
    a1.text(-58, PEAK_KPA + 0.3, "14 kPa comfort limit", fontsize=10)
    a1.set_xlabel("x across the rail from the stay line, mm")
    a1.set_ylabel("skin pressure, kPa (walking 1.6 g, worst bone)")
    a1.set_title(f"Across one rail at the rev C meat case (CG {E_REVC:.0f} mm)", fontsize=12)
    a1.legend(loc="upper right", fontsize=10)
    a1.set_ylim(0, 19)
    a2.axhline(PEAK_KPA, color="k", ls="--", lw=1.2)
    a2.axvline(E_REVC, color="#555", ls=":", lw=1.2)
    a2.text(E_REVC + 1, 9.3, "rev C\nmeat case", fontsize=9)
    a2.set_xlabel("meat CG aft of the frame, mm")
    a2.set_ylabel("peak skin pressure, kPa")
    a2.set_title("Peak vs meat CG", fontsize=12)
    a2.legend(fontsize=10, loc="upper left")
    a2.set_ylim(9, 19)
    fig.suptitle(f"Back rail: {ch.width:.0f} mm L200 rail on an {ch.backer_w:.0f} mm 1 mm-twill backer brings the "
                 f"rev C meat case to {res['confirm']['skin_peak_kpa']:.1f} kPa", fontweight="bold", fontsize=13)
    fig.tight_layout()
    return _save(fig, f"{DATE}_backpanel_1.png")


def plot_options(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 7))
    fam = {"backer width / stiffness": "#c27c0e", "foam grade / thickness": "#7a4fb0", "rail width": "#1e6fb0",
           "rail length": "#6b6252", "current": "#b03a2e"}
    off = [x for x in res["rows"] if x["peak_kpa"] > 20.0]
    for x in res["rows"]:
        if x["peak_kpa"] > 20.0:
            continue
        r = x["rail"]
        f = ("current" if r["key"] == CURRENT.key else "rail width" if r["width"] != 100 else
             "rail length" if r["length"] != 420 else "foam grade / thickness" if (r["foam"] != "xlpe_foam_l200" or r["foam_t"] != 10)
             else "backer width / stiffness")
        ax.scatter(x["delta_g"], x["peak_kpa"], s=90 if r["key"] != res["chosen"] else 260, color=fam[f],
                   edgecolor="k" if r["key"] == res["chosen"] else "none", zorder=3, label=f)
        if r["key"] in (res["chosen"], CURRENT.key) or x["delta_g"] > 90 or x["peak_kpa"] > 15.0:
            ax.annotate(r["key"], (x["delta_g"], x["peak_kpa"]), (6, 4), textcoords="offset points", fontsize=8.5)
    h, l_ = ax.get_legend_handles_labels()
    u = dict(zip(l_, h))
    ax.legend(u.values(), u.keys(), fontsize=10, loc="upper right")
    ax.axhline(PEAK_KPA, color="k", ls="--", lw=1.2)
    ax.text(ax.get_xlim()[0] + 2, PEAK_KPA - 0.25, "14 kPa", fontsize=10)
    for i, x in enumerate(off):
        ax.text(0.01, 0.03 + 0.04 * i, f"off the chart: {x['rail']['name']} = {x['peak_kpa']:.0f} kPa", transform=ax.transAxes,
                fontsize=10, color="#b03a2e", fontweight="bold")
    ax.set_xlabel("mass change for both rails vs the modelled 100 / 60 mm rail, g (foam + backer + sleeve/mesh growth)")
    ax.set_ylabel(f"peak skin pressure at meat CG {E_REVC:.0f} mm, kPa")
    ax.set_title("Every lever the rail model has. Foam grade and thickness barely move it (the 60 kPa tissue is the soft "
                 "spring);\nthe foundation width does. Circled: the chosen build", fontsize=11.5)
    fig.tight_layout()
    return _save(fig, f"{DATE}_backpanel_2.png")


def plot_section(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    ch = rail_by_key(res["chosen"])
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.8))
    for ax, r, ttl in ((axs[0], CURRENT, "current model: 100 / 60 mm (the released v3.1 patterns have the foam and sleeve, not the backer)"), (axs[1], ch, "rev C rail (this change)")):
        for sx in (-1, 1):
            cx = sx * 115.0
            ax.add_patch(mp.Rectangle((cx - r.width / 2, 0), r.width, r.foam_t, fc="#d9d2c0", ec="k"))
            ax.add_patch(mp.Rectangle((cx - r.backer_w / 2, r.foam_t), r.backer_w, 1.5, fc="#2b2e33", ec="k"))
            ax.add_patch(mp.Circle((cx, r.foam_t + 1.5 + 14.6), 14.6, fc="#5b6068", ec="k"))
            ax.add_patch(mp.Rectangle((cx - r.width / 2 - 10, -1.5), r.width + 20, r.foam_t + 4.5, fill=False, ec="#1e8a4c",
                                      ls="--", lw=1.2))
        g = 2 * (115.0 - r.width / 2.0)
        ax.annotate("", (-g / 2, 5), (g / 2, 5), arrowprops=dict(arrowstyle="<->", lw=1.3))
        ax.text(0, 7, f"air gutter {g:.0f} mm", ha="center", fontsize=10)
        ax.plot([-200, 200], [-3, -3], color="#e3a08a", lw=6)
        ax.text(-198, -11, "back (spacer mesh BP-01 over the rails)", fontsize=9, color="#a0533b")
        ax.text(115, -11, f"foam {r.width:.0f} x {r.foam_t:.0f} L200 | backer {r.backer_w:.0f} x {r.backer_t:g} twill | "
                f"sleeve {r.width + 20:.0f}", ha="center", fontsize=9)
        ax.set_xlim(-205, 205)
        ax.set_ylim(-16, 46)
        ax.set_aspect("equal")
        ax.set_title(ttl, fontsize=11)
        ax.set_yticks([])
    axs[1].set_xlabel("x mm from the spine (stays at x +/-115)")
    fig.suptitle("Back-rail section, wearer at the bottom: stay, backer strip, foam rail, sleeve", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_backpanel_3.png")


# ---------------------------------------------------------------- run, doc
def _json(o):
    if isinstance(o, dict):
        return {str(k): _json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def run(log=print, confirm_full: bool = True) -> dict:
    log("bone side reactions (production spreader)")
    sides = bone_sides()
    log(f"  {sides['spreader']}: worst {max(sides['sides_n'].values()):.1f} N")
    st = study(sides, log)
    ch = rail_by_key(st["chosen"])
    side = st["bone_side_n"]
    res = {"date": "2026-11-06", "e_rev_c_mm": E_REVC, "limit_kpa": PEAK_KPA, "bone": sides, **st,
           "sweep": {r.key: sweep(r, side) for r in (CURRENT, ch)},
           "soft_tissue": {r.key: soft_tissue(r, side) for r in (CURRENT, ch)},
           "mass": {r.key: mass_g(r) for r in (CURRENT, ch)}, "cost": {r.key: cost_usd(r) for r in (CURRENT, ch)}}
    res["delta_g"] = res["mass"][ch.key]["total_g"] - res["mass"][CURRENT.key]["total_g"]
    res["delta_usd"] = res["cost"][ch.key] - res["cost"][CURRENT.key]
    old = json.loads(RESULT.read_text()) if RESULT.exists() else {}
    if confirm_full or old.get("confirm", {}).get("rail") != ch.key:
        log("full spreader check with the chosen rail at the rev C meat case (and the current rail for reference)")
        res["confirm"] = confirm(ch)
        res["confirm_current"] = confirm(CURRENT)
        log(f"  chosen {res['confirm']['skin_peak_kpa']:.2f} kPa, current {res['confirm_current']['skin_peak_kpa']:.2f} kPa")
    else:                         # the full check (~8 min) is kept from the last run with the same chosen rail
        res["confirm"], res["confirm_current"] = old["confirm"], old["confirm_current"]
    res["screens"] = [plot_pressure(res), plot_options(res), plot_section(res)]
    RESULT.write_text(json.dumps(_json(res), indent=1))
    write_doc(res)
    return res


def write_doc(res: dict | None = None) -> str:
    res = res or json.loads(RESULT.read_text())
    ch = rail_by_key(res["chosen"])
    c, c0 = res["confirm"], res["confirm_current"]
    mc, m0 = res["mass"][ch.key], res["mass"][CURRENT.key]
    L = []
    a = L.append
    a("# Back-rail skin pressure at the rev C meat case")
    a("")
    a("Owner: pack-designer, 2026-11-06. Code: `huntkit/gendesign/back_rail.py` (`python -m huntkit.gendesign.back_rail`). "
      "Numbers: `analysis/back_rail_results.json`. Model: the rail-and-tissue model of `huntkit/gendesign/spreader.py` "
      "(`rail_backed`, Hetenyi spread along the stay), unchanged; only the rail build is a parameter here. Comfort limit "
      "14 kPa peak at the 1.6 g walking peak (Golriz et al. 2017, `back_comfort.md`). Load: HA-LS-1 rev C C5, meat CG "
      f"{res['e_rev_c_mm']:.0f} mm, worst bone end on the production spreader `{res['bone']['spreader']}` "
      f"({res['bone_side_n']:.0f} N side reaction, bone at position '{res['bone_where']}'). `spreader._SKIN_CACHE` is cleared before and "
      "after every full evaluation.")
    a("")
    a("## Decision")
    a("")
    a(f"- **Widen the stay rails 100 -> {ch.width:.0f} mm and the backer strips 60 -> {ch.backer_w:.0f} mm** (same 10 mm "
      "Minicel L200-class XLPE, same 1 mm 2x2 twill backer, same 420 mm length, still centred on the stay lines).")
    a(f"- Peak skin pressure at the rev C meat case: **{c0['skin_peak_kpa']:.1f} -> {c['skin_peak_kpa']:.1f} kPa** "
      f"(limit 14; full `spreader.evaluate`, worst bone position '{c['skin_where']}'). Meat only {c0['skin_meat_only_kpa']:.1f} -> "
      f"{c['skin_meat_only_kpa']:.1f} kPa.")
    a(f"- Mass **{res['delta_g']:+.1f} g** for the pair ({m0['total_g']:.1f} -> {mc['total_g']:.1f} g: foam, backer, the "
      f"wider sleeves and mesh). Cost **{res['delta_usd']:+.2f} USD** per pack (records' prices).")
    a(f"- Air gutter between the rails {2 * (115 - CURRENT.width / 2):.0f} -> {2 * (115 - ch.width / 2):.0f} mm. Air to "
      f"the skin, walking: {c0['clear_walk_min']:.1f} -> {c['clear_walk_min']:.1f} mm (limit 3); factored "
      f"{c0['clear_fact_min']:.1f} -> {c['clear_fact_min']:.1f} mm (limit 0). The sheet checks do not change "
      f"(FPF SF {c['sf_fpf']:.2f}, fatigue {c['sf_fatigue']:.2f}, sandwich {c['sandwich_sf_min']:.2f}).")
    nb = next(x for x in res["rows"] if x["rail"]["key"] == "r100_nobacker")
    a("- **Found on the way: the backer strip is in the model but not in the build.** Every skin number since 2026-11-04 "
      "(13.0 kPa at rev B) assumes a 1 mm twill strip between each stay and its foam rail (`spreader.RAIL_DESIGN`). "
      "The released v3.1 patterns, `panels.yaml` and the weight table have only the foam. As patterned the rail gives "
      f"**{nb['peak_kpa']:.0f} kPa** at the rev C meat case. The strips are now a cut part, BP-08 "
      f"({m0['backer_g']:.0f} g for the pair at 60 mm, {mc['backer_g']:.0f} g at {ch.backer_w:.0f} mm), and are in the weight table.")
    a("")
    a("## Options (same model, worst bone, CG 190 mm)")
    a("")
    a(f"Choice rule: {res['rule']} (margin and gutter are ASSUMPTIONs below).")
    a("")
    a("| key | build | peak kPa | meat share without the bone kPa | gutter mm | mass change g | cost change USD | <= 14 | meets the rule |")
    a("|---|---|---:|---:|---:|---:|---:|---|---|")
    for x in sorted(res["rows"], key=lambda x: x["delta_g"]):
        r = x["rail"]
        b = "**" if r["key"] == res["chosen"] else ""
        a(f"| {b}{r['key']}{b} | {r['name']} | {x['peak_kpa']:.2f} | {x['meat_only_kpa']:.2f} | {x['gutter_mm']:.0f} | "
          f"{x['delta_g']:+.1f} | {x['delta_usd']:+.2f} | {'yes' if x['pass'] else 'no'} | {'yes' if x['eligible'] else 'no'} |")
    a("")
    a("Reading the table:")
    a("")
    a("- **Foam grade and thickness hardly move the peak** (16 mm L200 still 15 kPa; EVA 45C over L200 15.1). The tissue "
      "column (60 kPa over 25 mm) is far softer than any closed-cell foam on file, so the pressure is set by how wide the "
      "stiff part spreads the stay load, not by the foam. PU memory foam (`pu_memory_foam`, 3 kPa at 25 %, open cell, "
      "500 % water uptake) would bottom and soak blood and sweat; not a candidate.")
    a("- **A wider backer alone saturates at about 14.7 kPa**: inside a 100 mm rail there is no foundation left to spread "
      "onto. A stiffer backer (2 mm twill) passes only at 90 mm width and costs about 150 g.")
    a("- **The foundation width is the lever.** A 120 mm rail with an 80 mm backer keeps the same 20 mm soft foam margin "
      "each side of the hard strip as today (no hard edge printing into the back) and passes with the most margin for its mass. "
      "115 / 80 is about 3 g lighter but leaves only 0.1 kPa. 130 / 70 is about 7 g lighter and passes, but narrows the "
      "air gutter to 100 mm and puts the rail edge at x +/-180, onto the rib curve.")
    a("- **A longer rail is not credited.** The model spreads the meat force uniformly over the rail length; in reality "
      "the overturning pressure peaks low (z 60-330) and the back curves away above the shoulder blades, so length above "
      "z 470 would not carry its share.")
    a("")
    a("## Peak vs meat CG")
    a("")
    a("| meat CG mm | " + " | ".join(r for r in res["sweep"]) + " |")
    a("|---:|" + "---:|" * len(res["sweep"]))
    for i, e in enumerate(E_SWEEP):
        a(f"| {e:.0f} | " + " | ".join(f"{res['sweep'][k][i]['peak_kpa']:.1f}" for k in res["sweep"]) + " |")
    a("")
    st = res["soft_tissue"]
    a(f"Soft-tissue sensitivity (20 kPa column): current {st[CURRENT.key]['peak_kpa']:.1f} kPa, chosen "
      f"{st[ch.key]['peak_kpa']:.1f} kPa. The 205 and 223 mm rows are bag-case CGs (C1); skin is a meat-case limit, shown "
      "for reference. The chosen rail keeps 14 kPa up to about "
      f"{np.interp(PEAK_KPA, [q['peak_kpa'] for q in res['sweep'][ch.key]], [q['e_mm'] for q in res['sweep'][ch.key]]):.0f} mm.")
    a("")
    a("## Mass and cost (both rails)")
    a("")
    a("| item | current g | chosen g |")
    a("|---|---:|---:|")
    for k in ("foam_g", "backer_g", "sleeve_extra_g", "mesh_extra_g", "total_g"):
        a(f"| {k.replace('_g', '').replace('_', ' ')} | {m0[k]:.1f} | {mc[k]:.1f} |")
    a("")
    a(f"Cost: current {res['cost'][CURRENT.key]:.2f} USD, chosen {res['cost'][ch.key]:.2f} USD (foam `xlpe_foam_l200` "
      f"15 USD/m2, backer `{BACKER_PRICE_MAT}` 250 USD/m2 bought 1 mm plate, sleeve `{SLEEVE_MAT}`).")
    a("")
    a("## Pattern-maker hand-off")
    a("")
    for k, v in HANDOFF(ch):
        a(f"- **{k}**: {v}")
    a("")
    a("## Assumptions")
    a("")
    for s_ in ASSUMPTIONS:
        a(f"- {s_}")
    a("")
    a("## Screenshots")
    a("")
    for s_ in res["screens"]:
        a(f"- `{s_}`")
    a("")
    DOC.write_text("\n".join(L))
    return str(DOC)


def HANDOFF(ch: Rail) -> list[tuple[str, str]]:
    sl = ch.width + 20
    mesh_w = 2 * (115 + sl / 2)
    return [
        ("BP-02 stay-rail foam x2", f"{CURRENT.width:.0f} x 420 -> **{ch.width:.0f} x 420 x 10 mm**, buy Minicel L200 class (the comfort model "
         "uses record `xlpe_foam_l200`; the `panels.yaml` row keeps the generic `xlpe_foam` id, the same L200 class, so the "
         "frame studies that read it do not move). Die-cut, 3 mm bevel on the long edges."),
        ("BP-08 rail backer x2 (new piece)", f"**{ch.backer_w:.0f} x 420 x 1.0 mm** 2x2 twill carbon plate, water-jet, "
         "R10 corners, edges sanded. Sits in the sleeve between the stay and the foam, centred on the stay line. Hot-melt "
         "two dots to the foam so it cannot shift in the sleeve."),
        ("BP-05 rail sleeve x2", f"120 x 420 -> **{sl:.0f} x 420** (rail + 20), top open, same seam allowances."),
        ("BP-01 back panel mesh", f"350 -> **{mesh_w:.0f} mm** wide x 440 (the sleeve outer edges at x +/-{115 + sl / 2:.0f} "
         f"stay on the panel); sleeve stitch lines move to stay CL +/-{sl / 2:.0f}. Stay-clip drill holes keep their 20 mm "
         "inset from the new edges."),
        ("check", "the hipbelt wing and shoulder-strap roots must clear the wider mesh edge (x +/-185); flag any overlap."),
    ]


ASSUMPTIONS = [
    "Rail model as spreader.py (structural-fea-engineer): stay hot/wet PAHT beam, aged L200 (12 % set), tissue 60 kPa "
    "over 25 mm (20 kPa sensitivity), 1-D lateral section, flat back under the rail. No new physics here.",
    "Foams without a compression curve (EVA 30C) use the L200 curve shape scaled to their 25 % point, as spreader.eva_curve.",
    "Wider rails stay centred on the stay line; the model puts the stay load at the strip centre.",
    f"Choice margin {MARGIN_KPA} kPa under the limit (model resolution) and an air gutter of at least {GUTTER_MIN:.0f} mm "
    "(85 % of today's 130 mm channel). A pressure-mat check on the first prototype (T9 day, meat case) replaces both.",
    "Sleeve = rail + 20 mm; mesh grows with the outer sleeve edge (2 x the width change x 460 mm of 380 gsm mesh).",
    "Backer price from cfrp_plate_0_90_woven (estimate, 250 USD/m2); stiffness from cfrp_t300_3k_woven_epoxy_ply, as the record.",
]


def docs_only() -> str:
    return write_doc()


if __name__ == "__main__":
    if "--docs-only" in sys.argv:
        docs_only()
    else:
        run(confirm_full="--keep-confirm" not in sys.argv)
