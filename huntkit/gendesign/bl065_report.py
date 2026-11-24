"""BL-065 record, figures and backlog note from the cached eigen runs (``bl065_h1_buckling``).

Writes ``designs/pack_5200/analysis/bl065.{json,md}``, the ``bl065_eigen`` block of ``bl058.json`` (no other key of
bl058.json is touched), ``docs/backlog/BL-065-h1-buckling.md`` and the screenshots
``outputs/screens/20261124_bl065_{1,2}.png``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from . import bl065_h1_buckling as B

BACKLOG = B.REPO / "docs" / "backlog" / "BL-065-h1-buckling.md"
MEMBERS = ("upper branch R", "upper branch L", "lower branch R", "lower branch L", "mid bar")
STATIC = ("fine_sm8", "fine", "beam")
CYC = ("fine_sm8.cyc",)
# dataviz reference palette, categorical slots 1-4 (light), validated order
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#d9d8d4", "#fcfcfb"


def load(tag: str = "h1") -> dict:
    out = {}
    for b in B.BASES:
        p = B.OUT / f"{tag}_{b}.json"
        if p.exists():
            out[b] = json.loads(p.read_text())
            for k in ("extra", "setdown", "sliver"):
                q = B.OUT / f"{tag}_{b}_{k}.json"
                if q.exists():
                    out[b][k] = json.loads(q.read_text())
    p = B.OUT / f"{tag}_squeeze.json"
    if p.exists():
        out["squeeze"] = json.loads(p.read_text())
    return out


def _r(x, n=3):
    return None if x is None else round(float(x), n)


def summary(res: dict) -> dict:
    """Minimum per reading, static-cinch (fine_sm8 / fine / beam) and cinch-cycled (fine_sm8.cyc)."""
    out = {}
    for nm, bs in (("static_cinch", STATIC), ("cinch_cycled", CYC)):
        bs = [b for b in bs if b in res]
        if not bs:
            continue
        row = {}
        rec = [(res[b]["record_rule"][k]["margin_record"], b, k) for b in bs for k in res[b]["record_rule"]]
        sec = [(res[b]["record_rule"][k]["margin_section"], b, k) for b in bs for k in res[b]["record_rule"]]
        row["record_rule"] = _r(min(rec)[0])
        row["section_rule"] = _r(min(sec)[0])
        for rd in ("unbraced", "braced"):
            v = [(res[b]["members"][m][rd]["margin"], b, m) for b in bs for m in res[b]["members"]]
            mn = min(v)
            row[f"member_eigen_{rd}"] = _r(mn[0])
            row[f"member_eigen_{rd}_where"] = f"{mn[2]} ({mn[1]}, {res[mn[1]]['members'][mn[2]]['set']})"
        fr = [frame_rows(res[b]) for b in bs]
        fr = [(r[0], b) for b, r in zip(bs, fr) if r is not None]
        if fr:
            mn = min(fr, key=lambda t: t[0]["margin"])
            row["frame_eigen_braced"] = _r(mn[0]["margin"])
            row["frame_eigen_braced_mode"] = {"basis": mn[1], **{k: mn[0][k] for k in
                                              ("set", "lead", "drives", "driver_peak_mm", "max_disp_at_mm", "reading")}}
            sd = [(res[b]["setdown"]["min_foot_held"], b) for b in bs if res[b].get("setdown", {}).get("sets")]
            row["setdown_foot_held_crown_free"] = _r(min(sd)[0]) if sd else None
            lp = [(v["with_sliver"], b, k) for b in bs for k, v in res[b].get("sliver", {}).get("sets", {}).items()]
            if lp:
                mn = min(lp)
                row["channel_lip_local"] = {"margin": _r(mn[0]), "basis": mn[1], "set": mn[2],
                                            "frame_with_lip_deleted": _r(res[mn[1]]["sliver"]["sets"][mn[2]]
                                                                         ["sliver_deleted"][0]["margin"])}
            fm = min((res[b]["free_min"]["margin"], b) for b in bs if "free_min" in res[b])
            fb = res[fm[1]]["free_min"]
            row["record_model_free"] = _r(fm[0])
            row["record_model_free_mode"] = {"basis": fm[1], "set": fb["set"], "lead": fb["lead"],
                                             "top_disp_share": _r(fb["top_disp_share"]),
                                             "max_disp_at_mm": fb["max_disp_at_mm"]}
        out[nm] = row
    return out


def frame_rows(rb: dict):
    """Lowest frame reading on one basis: braced full runs on every non-set-down set run (record-governing +
    screened + extra), and the set-down sets with the foot on the ground and the crown held. Returns (row, all)."""
    rows = []
    full = dict(rb.get("full", {}))
    full.update(rb.get("extra", {}).get("full", {}))
    sl = rb.get("sliver", {}).get("sets", {})
    for k, v in full.items():
        if "single_stay_setdown" in k:
            continue
        if k in sl:
            rows.append({"set": k, "reading": "crown held, channel lip deleted", **sl[k]["sliver_deleted"][0]})
        else:
            rows.append({"set": k, "reading": "crown held", **v["modes"][0]})
    for k, v in rb.get("setdown", {}).get("sets", {}).items():
        rows.append({"set": k, "reading": "set-down: foot on the ground, crown held", **v["foot_held_crown_held"][0]})
    if not rows:
        return None
    return min(rows, key=lambda r: r["margin"]), rows


def k_eff_table(res: dict) -> list:
    rows = []
    for b in B.BASES:
        if b not in res:
            continue
        for m in MEMBERS:
            v = res[b]["members"].get(m)
            if v is None:
                continue
            rows.append({"basis": b, "member": m, "set": v["set"], "P_factored_n": _r(v["P_n"], 1),
                         "I_min_mm4": round(v["I_min_mm4"]), "L_mm": v["L_mm"],
                         "margin_record": _r(v["margin_record"]), "margin_section": _r(v["margin_section"]),
                         "eigen_unbraced": _r(v["unbraced"]["margin"]), "Pcr_unbraced_n": _r(v["unbraced"]["Pcr_n"], 0),
                         "K_eff_unbraced": _r(v["unbraced"]["K_eff"]), "eigen_braced": _r(v["braced"]["margin"]),
                         "K_eff_braced": _r(v["braced"]["K_eff"])})
    return rows


# ================================================================================================ figures
def _mode_fig(path: Path, res: dict, tag: str = "h1"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b = B.body()
    g, solid = b["g"], b["solid"]
    idx = np.where(solid)[0]
    cen = g.elem_centers()[idx]
    st = summary(res)["static_cinch"]
    mb = st["frame_eigen_braced_mode"]["basis"]
    ub = res["fine"]["members"]["upper branch R"]
    panels = []
    gm = st["frame_eigen_braced_mode"]
    z = np.load(B.gov_mode(mb, gm["set"], "foot" in gm["reading"], tag))
    panels.append((z["mode"], f"Frame, crown held: margin {st['frame_eigen_braced']:.2f}, {gm['lead']}\n"
                              f"({mb}, {gm['set'].split(':')[1].split('|')[0]}, {gm['set'].split(':')[0]})"))
    zf = np.load(B.OUT / f"{tag}_fine_freemode.npz")
    panels.append((zf["mode"], f"Record model as is (hip clamp only): {res['fine']['free_min']['margin']:.2f}\n"
                               "whole frame pitches on the boss (support artefact)"))
    fig, axes = plt.subplots(2, 2, figsize=(9, 10.5), dpi=110)
    fig.patch.set_facecolor(SURF)
    for row, (mode, title) in enumerate(panels):
        u = mode.reshape(-1, 3)[g.enodes[idx]].mean(axis=1)
        a = np.linalg.norm(u, axis=1)
        sc = 40.0 / max(a.max(), 1e-12)
        d = cen + u * sc
        for col, (i, j, lab) in enumerate(((0, 2, "front view (x-z), mm"), (1, 2, "side view (y-z), mm"))):
            ax = axes[row, col]
            ax.set_facecolor(SURF)
            ax.scatter(cen[:, i], cen[:, j], s=0.3, c=GRID, linewidths=0)
            o = np.argsort(a)
            ax.scatter(d[o, i], d[o, j], s=0.6, c=a[o] / a.max(), cmap="Blues", vmin=-0.15, vmax=1, linewidths=0)
            ax.set_aspect("equal")
            ax.set_xlabel(lab, color=INK2, fontsize=8)
            ax.tick_params(colors=INK2, labelsize=7)
            for s_ in ax.spines.values():
                s_.set_color(GRID)
            if col == 0:
                ax.set_title(title, loc="left", fontsize=9.5, color=INK)
    fig.suptitle("BL-065 H1 print: lowest buckling modes (grey = undeformed, blue = mode, scaled)", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.text(0.01, 0.005, f"Upper branch R on its own (member mode, stay tops free): margin "
                          f"{ub['unbraced']['margin']:.2f}, K_eff {ub['unbraced']['K_eff']:.2f}. Margin = lam / 1.5 "
                          "(HA-LS-1), >= 1 required.", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)


def _bar_fig(path: Path, res: dict, fixres: dict | None = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [r for r in k_eff_table(res) if r["basis"] in ("fine", "fine_sm8.cyc")]
    labels, series = [], {"record rule (bl058.json)": [], "real section, K = 1 (BL-061)": [],
                          "eigen, member, stay tops free": [], "eigen, member, crown held": []}
    for r in rows:
        labels.append(f"{r['member']}\n{'static' if r['basis'] == 'fine' else 'cinch-cyc.'}")
        series["record rule (bl058.json)"].append(r["margin_record"])
        series["real section, K = 1 (BL-061)"].append(r["margin_section"])
        series["eigen, member, stay tops free"].append(r["eigen_unbraced"])
        series["eigen, member, crown held"].append(r["eigen_braced"])
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=110)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    n = len(labels)
    w = 0.2
    cap = 3.0
    for k, ((nm, vals), col) in enumerate(zip(series.items(), (C1, C2, C3, C4))):
        x = np.arange(n) + (k - 1.5) * w
        v = np.minimum(np.array(vals, float), cap)
        ax.bar(x, v, w * 0.9, color=col, label=nm, zorder=3)
        for xi, vi, raw in zip(x, v, vals):
            if raw < 1.6:
                ax.text(xi, vi + 0.03, f"{raw:.2f}", ha="center", va="bottom", fontsize=6.5, color=INK, rotation=90)
            elif raw > cap:
                ax.text(xi, cap + 0.03, f"{raw:.0f}", ha="center", va="bottom", fontsize=6.5, color=INK2, rotation=90)
    ax.axhline(1.0, color=INK, lw=1.2, zorder=4)
    ax.axhline(B.BONUS, color=INK2, lw=1, ls="--", zorder=4)
    ax.text(n - 0.5, 1.0, "required 1.0 ", ha="right", va="bottom", fontsize=8, color=INK)
    ax.text(n - 0.5, B.BONUS, "goal 1.15 ", ha="right", va="bottom", fontsize=8, color=INK2)
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(labels, fontsize=7.5, color=INK2)
    ax.set_ylim(0, cap + 0.45)
    ax.set_ylabel("buckling margin (P_cr / 1.5 P), capped at 3", color=INK2, fontsize=9)
    ax.tick_params(colors=INK2)
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    for s_ in ("left", "bottom"):
        ax.spines[s_].set_color(GRID)
    st = summary(res)
    ttl = (f"BL-065 H1 member buckling: record {st['static_cinch']['record_rule']:.2f}, BL-061 section "
           f"{st['static_cinch']['section_rule']:.2f}, eigen {st['static_cinch']['member_eigen_unbraced']:.2f} "
           f"(stay tops free) / frame {st['static_cinch']['frame_eigen_braced']:.2f} (crown held)")
    ax.set_title(ttl, loc="left", fontsize=10, color=INK)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)


def _shrink(path: Path, limit: int = 1_500_000):
    if path.stat().st_size <= limit:
        return
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.quantize(colors=128)
    im.save(path, optimize=True)


# ================================================================================================ record
def record(res: dict, fixres: dict | None = None) -> dict:
    st = summary(res)
    sq = res.get("squeeze")
    out = {
        "ticket": "BL-065",
        "date": "2026-11-24",
        "stl": str(B.FI.STL.relative_to(B.REPO)), "stl_md5": B.FI.STL_MD5,
        "method": ("linear eigenvalue buckling of the 2 mm voxel raster of the print (huntkit.fea.voxel_buckling, H8 "
                   "initial-stress stiffness, Lanczos), E 1621 MPa (E_xy x 0.6 hot x 0.7 creep, the record rule's), "
                   "prestress = the BL-058 whole-body solve of every rev C set; margin = lam / 1.5 / 1.02 (H8)"),
        "requirement": "HA-LS-1 4: eigenvalue >= 1.5 x case factor (margin >= 1); BL-061 goal >= 1.15",
        "summary": st,
        "members": k_eff_table(res),
        "squeeze": None if sq is None else {
            "Q_per_side_n": sq["Q_per_side_n"],
            "braced_margin": _r(sq["braced"][0]["margin"]), "braced_lead": sq["braced"][0]["lead"],
            "braced_bifurcation_n_per_side": _r(sq["braced_bifurcation_n_per_side"], 0),
            "free_margin": _r(sq["free"][0]["margin"]), "free_lead": sq["free"][0]["lead"],
            "free_bifurcation_n_per_side": _r(sq["free_bifurcation_n_per_side"], 0),
            "member_compression_n": {k: _r(v, 1) for k, v in sq["cuts"].items()}},
        "per_basis": {b: {"record_rule_min": _r(min(v["margin_record"] for v in res[b]["record_rule"].values())),
                          "frame_min": None if frame_rows(res[b]) is None else
                          {k: (_r(v) if k == "margin" else v) for k, v in frame_rows(res[b])[0].items()
                           if k in ("margin", "set", "lead", "drives", "reading")},
                          "setdown": None if not res[b].get("setdown", {}).get("sets") else
                          {k: {"foot": v["foot"], "foot_held_crown_free": _r(v["foot_held"][0]["margin"]),
                               "foot_held_crown_free_lead": v["foot_held"][0]["lead"],
                               "foot_held_crown_free_top_disp_share": _r(v["foot_held"][0]["top_disp_share"]),
                               "foot_and_crown_held": _r(v["foot_held_crown_held"][0]["margin"]),
                               "foot_and_crown_held_lead": v["foot_held_crown_held"][0]["lead"]}
                           for k, v in res[b]["setdown"]["sets"].items()},
                          "free_min": None if "free_min" not in res[b] else
                          {"margin": _r(res[b]["free_min"]["margin"]), "set": res[b]["free_min"]["set"],
                           "lead": res[b]["free_min"]["lead"],
                           "top_disp_share": _r(res[b]["free_min"]["top_disp_share"])},
                          "full_runs_crown_held": {k: [{"margin": _r(m["margin"]), "lead": m["lead"]}
                                                       for m in v["modes"]]
                                                   for k, v in {**res[b].get("full", {}),
                                                                **res[b].get("extra", {}).get("full", {})}.items()},
                          "screen_lowest": sorted(((k, _r(v)) for k, v in res[b].get("screen", {}).items()
                                                   if v is not None), key=lambda kv: kv[1])[:5]}
                      for b in B.BASES if b in res},
        "assumptions": {k: {"text": v[0], "settled_by": v[1]} for k, v in B.ASSUMPTIONS.items()},
        "fix": None,
        "screenshots": [f"outputs/screens/{B.SHOT}1.png", f"outputs/screens/{B.SHOT}2.png"],
    }
    from . import bl065_text as T
    out["fix"] = {**T.verdict(out), "mass_change_g": 0.0, "sized": fixres}
    return out


def update_bl058(rec: dict):
    d = json.loads(B.BL058.read_text())
    st = rec["summary"]
    d["bl065_eigen"] = {
        "source": "designs/pack_5200/analysis/bl065.json (huntkit.gendesign.bl065_h1_buckling)",
        "note": ("Member buckling of record (body.min.*.buckling) is the team A Euler rule (solid round, K 1). The "
                 "BL-065 eigenvalue run on the same print and sets replaces it as the buckling reading: the members "
                 "are end-restrained by the fused nodes (K_eff < 1), which more than covers the flat section."),
        "static_cinch": {k: st["static_cinch"][k] for k in ("record_rule", "section_rule", "member_eigen_unbraced",
                                                           "member_eigen_braced", "frame_eigen_braced",
                                                           "record_model_free")},
        "cinch_cycled": {k: st["cinch_cycled"][k] for k in ("record_rule", "section_rule", "member_eigen_unbraced",
                                                           "member_eigen_braced", "frame_eigen_braced",
                                                           "record_model_free")},
        "governing_frame_mode": st["static_cinch"]["frame_eigen_braced_mode"],
        "squeeze": rec["squeeze"],
        "buckling_of_record": {"static_cinch": min(st["static_cinch"]["member_eigen_unbraced"],
                                                   st["static_cinch"]["frame_eigen_braced"]),
                               "cinch_cycled": min(st["cinch_cycled"]["member_eigen_unbraced"],
                                                   st["cinch_cycled"]["frame_eigen_braced"]),
                               "rule": "min(member eigen with the stay tops free, frame eigen with the crown held)"},
        "fix": rec["fix"]["text"],
    }
    B.BL058.write_text(json.dumps(d, indent=1))


def report(tag: str = "h1"):
    res = load(tag)
    missing = [b for b in B.BASES if b not in res] + ([] if "squeeze" in res else ["squeeze"])
    if missing:
        raise RuntimeError(f"run first: python -m huntkit.gendesign.bl065_h1_buckling run {' '.join(missing)}")
    fx = B.OUT / "fix.json"
    fixres = json.loads(fx.read_text()) if fx.exists() else None
    rec = record(res, fixres)
    B.REC_JSON.write_text(json.dumps(rec, indent=1, default=B.FI._jd))
    update_bl058(rec)
    B.SCREENS.mkdir(parents=True, exist_ok=True)
    p1, p2 = B.SCREENS / f"{B.SHOT}1.png", B.SCREENS / f"{B.SHOT}2.png"
    _mode_fig(p1, res, tag)
    _bar_fig(p2, res, fixres)
    for p in (p1, p2):
        _shrink(p)
    from . import bl065_text as T
    B.REC_MD.write_text(T.analysis_md(rec))
    BACKLOG.write_text(T.backlog_md(rec))
    return rec


def fix(args):  # pragma: no cover
    from . import bl065_text as T
    T.fix(args)
