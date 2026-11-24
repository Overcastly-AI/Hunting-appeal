"""BL-061 report: tables, rubric score, figures and renders for the iteration-1 frame concepts (frame_iter1).

``python -m huntkit.gendesign.frame_iter1_report`` (after ``frame_iter1 all``) writes
``designs/pack_5200/iter1/frame/frame_iter1.json`` and the screenshots; the Markdown record is written by
``write_md`` from the same JSON."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from . import frame_iter1 as F

WEIGHT_JSON = F.PACK / "iter1" / "system" / "iter1_weight.json"      # BL-062 roll-up (frame line after tests)
FRAME_LINE_FALLBACK = 1387.1
TOL = 0.01                    # "at least as strong": every margin >= H1's x (1 - TOL) (2 mm voxel noise)
KEYS_STATIC = ("strength", "fatigue", "creep", "buckling_record", "buckling_section", "joint_strength", "joint_fatigue")


def frame_line_g() -> tuple:
    """(g, source) of the whole frame line (print + crown + rack / pawl + pins + hardware), BL-062 roll-up."""
    if WEIGHT_JSON.exists():
        return float(json.loads(WEIGHT_JSON.read_text())["totals"]["frame_after_tests_g"]), \
            "designs/pack_5200/iter1/system/iter1_weight.json totals.frame_after_tests_g (BL-062)"
    return FRAME_LINE_FALLBACK, "ASSUMPTION: BL-062 roll-up value 1387.1 g (file missing)"


def load(name: str) -> dict | None:
    p = F.OUT / f"check_{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def gate(row: dict, base: dict) -> dict:
    """R1 gate (every static-cinch row >= 1, cinch-cycled fatigue kept on its R1 hold) and 'at least as strong as H1'
    (every margin >= H1's within TOL; carbon / bond rows only need R1 since H1 has none)."""
    s, c = row["static_cinch"], row["cinch_cycled"]
    bs, bc = base["static_cinch"], base["cinch_cycled"]
    r1 = []
    for k, v in s.items():
        if v is None or k == "buckling_section":
            continue
        if v < 1.0:
            r1.append(f"static {k} {v}")
    worse = []
    for k in KEYS_STATIC:
        if s.get(k) is None or bs.get(k) is None:
            continue
        if s[k] < bs[k] * (1 - TOL):
            worse.append(f"static {k} {s[k]} < H1 {bs[k]}")
    for k in ("fatigue", "buckling_record", "buckling_section"):
        if c.get(k) is not None and c[k] < bc[k] * (1 - TOL):
            worse.append(f"cinch-cycled {k} {c[k]} < H1 {bc[k]}")
    for k in ("tube_strength", "tube_fatigue", "gyroid_core"):
        if s.get(k) is not None and s[k] < 1.0:
            r1.append(f"static {k} {s[k]}")
    return {"R1_pass": not r1, "R1_fails": r1, "at_least_as_strong": not worse and not r1, "weaker_rows": worse}


def collect() -> dict:
    base = load("h1")
    bsum = F.summary(base)
    fl, fl_src = frame_line_g()
    out = {"frame_line_h1_g": fl, "frame_line_source": fl_src, "concepts": {}}
    for n in F.CONCEPTS:
        r = load(n)
        if r is None or F.summary(r) is None:
            continue
        sm = F.summary(r)
        con = F.build(n)
        mrow = F.mass(con)               # re-booked with the current mass rules (bond bands, full bond sleeves)
        if n.startswith("cf"):
            z = F._base()["cen"][:, 2]
            v = F.H ** 3 * F.RHO_PAHT
            mrow["parts_raster_g"] = {"P1 lower node (z < 193)": round(float((con["printed"] & (z < 193)).sum()) * v, 1),
                                      "P2 branch X (z 193-469)": round(float((con["printed"] & (z >= 193) & (z < 469)).sum()) * v, 1),
                                      "P3 top node (z > 469)": round(float((con["printed"] & (z >= 469)).sum()) * v, 1)}
        row = {"label": F.LABEL[n], "mass": mrow, "frame_line_g": round(fl + mrow["delta_g"], 1),
               "static_cinch": sm["static_cinch"], "cinch_cycled": sm["cinch_cycled"],
               "members_fine_sm8": r["fine_sm8"]["buckling"], "governing_tag": r["fine_sm8.cyc"]["governing_tag"],
               "top_regions_cyc": r["fine_sm8.cyc"]["top_regions"], "info": r.get("info", {})}
        if n.startswith("cf"):
            row["bonds"] = F.bonds(n)
            z = np.load(F.OUT / f"tube_{n}_fine_sm8.npz")
            row["bond_torque_in_model"] = bool(z["R_192"].shape[-1] > 5)
            bm = [v[k]["margin"] for v in row["bonds"].values() for k in ("avg", "peak", "fatigue", "bearing", "pin")
                  if v[k]["margin"] is not None]
            sm["static_cinch"]["bond_min"] = round(min(bm), 3)
            row["tube"] = {b: r[b]["tube"] for b in F.BASES}
        mins = [v for k, v in sm["static_cinch"].items() if v is not None and k != "buckling_section"]
        row["min_margin_static"] = round(min(mins), 3)
        # print time: h1_buckling print_h rule ((part + support) / 8 mm3/s x 1.08) on the printed raster, support
        # ASSUMPTION +10 % of the part (BL-053 tree supports were 49-55 g on 478-544 g parts)
        vol = mrow["raster_printed_g"] / F.RHO_PAHT
        row["print_h_est"] = round(vol * 1.10 / 8.0 * 1.08 / 3600.0, 1)
        row["gate"] = gate(sm, bsum)
        out["concepts"][n] = row
    return out


# ================================================================================================ figures
def _save(fig, path: Path) -> str:
    import matplotlib.pyplot as plt
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    from huntkit.viz3d.cycles_render import shrink_png
    shrink_png(path)
    return str(path)


def plot_compare(res: dict, path: Path) -> str:
    """Mass of the whole frame line and the margins per concept (bars), the R1 line and H1's values."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cs = res["concepts"]
    names = list(cs)
    fig, ax = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1, 2]})
    fl = [cs[n]["frame_line_g"] for n in names]
    cols = ["#7a7570" if n == "h1" else ("#2f6b4f" if cs[n]["gate"]["at_least_as_strong"] else
                                          ("#c08a2a" if cs[n]["gate"]["R1_pass"] else "#b03a2e")) for n in names]
    ax[0].barh(range(len(names)), fl, color=cols)
    for i, v in enumerate(fl):
        ax[0].text(v + 8, i, f"{v:.0f} g ({v / 453.6:.2f} lb)", va="center", fontsize=9)
    ax[0].set_yticks(range(len(names)))
    ax[0].set_yticklabels([n.upper() for n in names])
    ax[0].invert_yaxis()
    ax[0].set_xlim(0, max(fl) * 1.45)
    ax[0].axvline(900, color="k", ls=":", lw=1)
    ax[0].text(905, len(names) - 0.6, "900 g bold\ntarget", fontsize=8)
    ax[0].set_xlabel("whole frame line, g (print + crown + rack/pawl + pins + hardware)")
    ax[0].set_title("Frame line mass (green: at least as strong as H1;\namber: passes R1 but weaker; red: fails R1)",
                    fontsize=10)
    keys = [("strength", "static_cinch", "strength"), ("fatigue", "static_cinch", "fatigue"),
            ("creep", "static_cinch", "creep"), ("buckling (record rule)", "static_cinch", "buckling_record"),
            ("buckling (section rule)", "static_cinch", "buckling_section"),
            ("cinch-cycled fatigue", "cinch_cycled", "fatigue")]
    w = 0.8 / len(names)
    for i, n in enumerate(names):
        vals = [cs[n][b].get(k) or 0.0 for _, b, k in keys]
        ax[1].bar(np.arange(len(keys)) + (i - len(names) / 2 + 0.5) * w, vals, w, label=n.upper(), color=cols[i] if
                  n == "h1" else None)
    ax[1].axhline(1.0, color="k", lw=1)
    ax[1].text(len(keys) - 0.5, 1.02, "R1", fontsize=9, ha="right")
    ax[1].axhline(1.15, color="k", lw=0.8, ls="--")
    ax[1].text(len(keys) - 0.5, 1.17, "bonus 1.15", fontsize=8, ha="right")
    ax[1].set_xticks(range(len(keys)))
    ax[1].set_xticklabels([k[0] for k in keys], rotation=20, ha="right", fontsize=9)
    ax[1].set_ylim(0, 3.2)
    ax[1].set_ylabel("margin = SF / requirement")
    ax[1].legend(fontsize=8, ncol=5, loc="upper left")
    ax[1].set_title("HA-LS-1 rev C body margins (sanded stays, 42 sets x 4 bases)", fontsize=10)
    fig.suptitle("BL-061 iteration 1 frame concepts: mass and strength", fontsize=13)
    fig.tight_layout()
    return _save(fig, path)


def plot_util(name: str, path: Path, title: str) -> str:
    """Utilisation of one concept: static bases (max) and cinch-cycled, front (x-z) and side (y-z) projections,
    the voxel with the largest value in each projection column."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = F._base()
    cen = c["cen"]
    fig, ax = plt.subplots(1, 4, figsize=(15, 7.2), gridspec_kw={"width_ratios": [3, 1, 3, 1]})
    con = F.build(name)
    for j, (suf, lab) in enumerate((("", "static bases (max of strength / fatigue / creep FI / allowable)"),
                                    ("_cyc", "cinch-cycled basis fine_sm8.cyc"))):
        z = np.load(F.OUT / f"util_{name}{suf}.npz")
        P = cen[z["idx"]]
        u = z["util"].astype(float)
        cfm = con["cf"][z["idx"]]
        for k, (a, b) in enumerate(((0, 2), (1, 2))):
            axx = ax[2 * j + k]
            o = np.argsort(u)
            axx.scatter(P[cfm, a], P[cfm, b], s=3, c="#222222", marker="s")
            sc = axx.scatter(P[o, a][~cfm[o]], P[o, b][~cfm[o]], c=u[o][~cfm[o]], s=3, cmap="inferno_r",
                             vmin=0, vmax=1.0, marker="s")
            axx.set_aspect("equal")
            axx.set_xlabel("x (mm)" if a == 0 else "y (mm)")
            if k == 0:
                axx.set_title(lab, fontsize=9)
        fig.colorbar(sc, ax=ax[2 * j + 1], fraction=0.5, label="utilisation (1 = at the allowable)")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return _save(fig, path)


def plot_sections(name: str, path: Path, title: str) -> str:
    """Cross-sections of a concept against H1: z cuts through the stays / members, x cut through the mid bar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = F._base()
    cen = c["cen"]
    s0 = F.baseline_solid()
    con = F.build(name)
    cuts = ((2, 251.0, "z 250 (lower branches, stays)"), (2, 421.0, "z 420 (upper branches)"),
            (2, 121.0, "z 120 (lumbar struts, hip boss)"), (0, 1.0, "x 0 (mid bar, pawl housing)"))
    fig, ax = plt.subplots(2, 4, figsize=(15, 7.5))
    for j, (axn, v, lab) in enumerate(cuts):
        m = np.abs(cen[:, axn] - v) < 1.01
        o = [i for i in range(3) if i != axn]
        for i, (sol, nm) in enumerate(((s0, "H1"), (con["solid"], name.upper()))):
            a = ax[i, j]
            P = cen[m & sol]
            a.scatter(P[:, o[0]], P[:, o[1]], s=6, marker="s", c="#8c8377")
            if i == 1:
                Q = cen[m & con["cf"]]
                a.scatter(Q[:, o[0]], Q[:, o[1]], s=6, marker="s", c="#111111")
                Q = cen[m & con["core"]]
                a.scatter(Q[:, o[0]], Q[:, o[1]], s=6, marker="s", c="#d9b26f")
            a.set_aspect("equal")
            a.set_title(f"{nm}: {lab}", fontsize=8)
            a.tick_params(labelsize=7)
    fig.suptitle(title + "  (grey printed PAHT-CF, black carbon tube, tan gyroid core; white inside = cavity)", fontsize=11)
    fig.tight_layout()
    return _save(fig, path)


def _mesh_of(solid: np.ndarray, sigma: float = 0.8):
    """Smoothed marching-cubes surface of a voxel body (frame coordinates, mm)."""
    import trimesh
    from scipy import ndimage
    from skimage import measure
    c = F._base()
    g = c["dom"].grid
    a = g.to_array(solid).astype(float)
    a = np.pad(a, 2)
    a = ndimage.gaussian_filter(a, sigma)
    v, f, _, _ = measure.marching_cubes(a, 0.5)
    v = (v - 2) * g.h + np.asarray(g.x0) + g.h / 2
    m = trimesh.Trimesh(v, f[:, ::-1], process=True)
    trimesh.smoothing.filter_taubin(m, iterations=8)
    return m


def renders(res: dict) -> list:
    """Cycles: every concept side by side (front-quarter view from the wearer side, as frame_h1 renders)."""
    import trimesh
    from .frame_h1 import render
    from .frame_light2_render import _cyl
    work = F.OUT / "render"
    work.mkdir(parents=True, exist_ok=True)
    # GRADED and CF-BOX look like H1 and CF-LITE from outside: four bodies keep the frames large enough to read
    names = [n for n in ("h1", "box", "cfstay", "cflite") if n in res["concepts"]]
    dx = 390.0
    files = []
    for i, n in enumerate(names):
        off = -(i - (len(names) - 1) / 2) * dx           # seen from the wearer side (az 180): first on the left
        con = F.build(n)
        if n in ("h1", "graded"):
            m = trimesh.load(F.STL)
        else:
            # the voxel envelope stops at y 16 and |x| 152: the fairlead tops and the US2 clevises outside it are
            # unchanged in every concept, so they are taken from the released STL
            t0 = trimesh.load(F.STL)
            outside = [t0.slice_plane((0, 15.0, 0), (0, 1, 0)),
                       t0.slice_plane((151.0, 0, 0), (1, 0, 0)),
                       t0.slice_plane((-151.0, 0, 0), (-1, 0, 0))]
            m = trimesh.util.concatenate([_mesh_of(con["printed"])] + [o for o in outside if o is not None])
        m.apply_translation((off, 0, 0))
        m.export(work / f"{n}.stl")
        files.append({"path": str(work / f"{n}.stl"), "mat": "printed"})
        if n.startswith("cf"):
            t = trimesh.util.concatenate([_cyl((sx * F.TUBE["x"] + off, F.TUBE["y"], F.TUBE["z0"]),
                                               (sx * F.TUBE["x"] + off, F.TUBE["y"], F.TUBE["z1"]), F.TUBE["od"] / 2)
                                          for sx in (-1, 1)])
            t.export(work / f"{n}_tubes.stl")
            files.append({"path": str(work / f"{n}_tubes.stl"), "mat": "carbon"})
    cs = res["concepts"]
    cap = "Frame concepts (wearer side): " + "  |  ".join(n.upper() for n in names)
    sub = " | ".join(f"{n.upper()} {cs[n]['frame_line_g']:.0f} g, buckl. {cs[n]['static_cinch']['buckling_record']:.2f}"
                     + ("" if cs[n]["gate"]["at_least_as_strong"] else " (weaker)") for n in names)
    p = F.SCREENS / f"{F.SHOT}1.png"
    render(p, files, cap, sub, az=180.0, el=6.0, zoom=1.0, samples=32)
    return [str(p)]


# ================================================================================================ record
def report(do_renders: bool = True) -> dict:
    res = collect()
    shots = []
    if do_renders:
        try:
            shots += renders(res)
        except Exception as e:                   # Blender venv missing: the matplotlib figures still go out
            res["render_error"] = repr(e)[:400]
    shots.append(plot_compare(res, F.SCREENS / f"{F.SHOT}2.png"))
    rec = res.get("recommended") or pick(res)
    res["recommended"] = rec
    shots.append(plot_util(rec, F.SCREENS / f"{F.SHOT}3.png",
                           f"{F.LABEL[rec]}: utilisation (printed parts; carbon tubes black)"))
    shots.append(plot_sections(rec, F.SCREENS / f"{F.SHOT}4.png", f"{F.LABEL[rec]}: sections vs H1"))
    res["screenshots"] = shots
    F.DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    (F.DESIGN_DIR / "frame_iter1.json").write_text(json.dumps(res, indent=1, default=F._jd))
    write_md(res)
    return res


def _f(v, n=2):
    return "-" if v is None else f"{v:.{n}f}"


def write_md(res: dict) -> str:
    """The Markdown record, every number from ``res`` (frame_iter1.json)."""
    from .frame_iter1_text import narrative
    cs = res["concepts"]
    h = cs["h1"]
    L = []
    L.append("# Frame iteration 1 (BL-061): lighter and at least as strong")
    L.append("")
    L.append("structural-fea-engineer, 2026-11-24. Ticket `docs/backlog/BL-061-iter1-frame.md`. Research "
             "[frame_iter1.md](../../../../docs/research/frame_iter1.md). Rubric `docs/RUBRIC.md`. Code "
             "`huntkit/gendesign/frame_iter1.py` (concepts + check), `frame_iter1_report.py` (this record, figures), "
             "`frame_iter1_text.py` (prose); tests `tests/test_frame_iter1.py`; data `frame_iter1.json`. Units mm, N, "
             "MPa, g (imperial in brackets). Released print files untouched.")
    L.append("")
    L += narrative(res, "summary")
    L.append("")
    L.append("## 1. Concepts and results")
    L.append("")
    L.append(f"Frame line (print + crown + rack / pawl + pins + hardware) for H1: **{res['frame_line_h1_g']:.1f} g** "
             f"({res['frame_line_h1_g'] / 453.592:.2f} lb), {res['frame_line_source']}. Each concept changes it by its "
             "mass delta (section 3).")
    L.append("")
    L.append("| concept | frame line g (lb) | delta g | strength | fatigue | creep | buckling record / section | "
             "cinch-cycled fatigue / buckling | joint z 234 | tube str / fat | bonds min | R1 | as strong as H1 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for n, r in cs.items():
        s, c = r["static_cinch"], r["cinch_cycled"]
        L.append(f"| **{n.upper()}** {r['label'].split(':', 1)[-1].strip()} | {r['frame_line_g']:.1f} "
                 f"({r['frame_line_g'] / 453.592:.2f}) | {r['mass']['delta_g'] + 0.0:+.1f} | {_f(s['strength'])} | "
                 f"{_f(s['fatigue'])} | {_f(s['creep'])} | {_f(s['buckling_record'])} / {_f(s['buckling_section'])} | "
                 f"{_f(c['fatigue'])} / {_f(c['buckling_record'])} | "
                 f"{_f(s.get('joint_strength'))} / {_f(s.get('joint_fatigue'))} | "
                 f"{_f(s.get('tube_strength'))} / {_f(s.get('tube_fatigue'))} | {_f(s.get('bond_min'))} | "
                 f"{'pass' if r['gate']['R1_pass'] else 'FAIL'} | {'yes' if r['gate']['at_least_as_strong'] else 'no'} |")
    L.append("")
    L.append("Margins are SF / requirement (R1: >= 1). Static-cinch = minimum over fine_sm8, fine and beam; cinch-cycled "
             "= fine_sm8.cyc. All with the stays' sanding factor 1.0416 on printed stay voxels (BL-055). 'Section' "
             "buckling uses each cut's real weighted I_min (section 2.1).")
    L.append("")
    for n, r in cs.items():
        if r["gate"]["R1_fails"] or r["gate"]["weaker_rows"]:
            L.append(f"- **{n.upper()}**: " + "; ".join(r["gate"]["R1_fails"] + r["gate"]["weaker_rows"]))
    L.append("")
    L += narrative(res, "concepts")
    L.append("")
    L.append("## 2. Method")
    L += narrative(res, "method")
    L.append("")
    L.append("### 2.1 Member buckling per member (fine_sm8 basis)")
    L.append("")
    L.append("| concept | member | A_eff mm2 | I_min mm4 | P factored N | margin record | margin section |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for n, r in cs.items():
        for m, v in r["members_fine_sm8"].items():
            L.append(f"| {n.upper()} | {m} | {v['A_eff_mm2']:.0f} | {v['I_min_mm4']:.0f} | {v['P_factored_n']:.0f} | "
                     f"{_f(v['margin_record'])} | {_f(v['margin_section'])} |")
    L.append("")
    L += narrative(res, "buckling")
    L.append("")
    L.append("## 3. Mass (ledger style)")
    L.append("")
    for n, r in cs.items():
        L.append(f"**{n.upper()}**: " + "; ".join(f"{k} {v:+.1f}" if i else f"{k} {v:.1f}"
                                             for i, (k, v) in enumerate(r["mass"]["rows"].items()))
                 + f" = **{r['mass']['frame_print_g']:.1f} g** ({r['mass']['delta_g']:+.1f} g; frame line "
                 f"{r['frame_line_g']:.1f} g). Print about {r['print_h_est']:.0f} h.")
        L.append("")
    L += narrative(res, "mass")
    L.append("")
    if any("bonds" in r for r in cs.values()):
        L.append("## 4. Tube-to-node joints (carbon-stay concepts)")
        L.append("")
        L.append("| concept | sleeve | bonded L mm | Volkersen k | avg | peak (limit) | fatigue | bearing | fail-safe pin |")
        L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for n, r in cs.items():
            for sl, v in r.get("bonds", {}).items():
                L.append(f"| {n.upper()} | {sl} | {v['L_mm']:.0f} | {v['volkersen_k']:.1f} | {_f(v['avg']['margin'])} | "
                         f"{_f(v['peak']['margin'])} | {_f(v['fatigue']['margin'])} | {_f(v['bearing']['margin'])} | "
                         f"{_f(v['pin']['margin'])} |")
        L.append("")
        L += narrative(res, "joints")
        L.append("")
    L.append("## 5. Rubric score and recommendation")
    L += narrative(res, "recommendation")
    L.append("")
    L.append("## 6. Assumptions")
    L += narrative(res, "assumptions")
    L.append("")
    L.append("## 7. Side task: T1 US1 ROOT record only; second US1 gauge re-run")
    L.append("")
    import json as _j
    g2 = _j.loads((F.PACK / "tests_physical" / "us1_outer_gauge.json").read_text())
    L.append("- `physical_test_kit.py`: `T1_RECORD_ONLY = ('US1 ROOT',)`. Its T1 line (gauge_lines_bl060.json T1|us1) sits "
             "at a near-null point of the bag-on load and inside a PAHT-CF half-bridge's zero drift (BL-060), so the "
             "register's T1 pass / fail text lists it as RECORD ONLY with its model line, and its three results rows "
             "are `record` (no band). US2 ROOT and US1 OUTER CHEEK keep their pass lines.")
    L.append(f"- `us1_outer_gauge.py` re-run on the current STL (md5 `{g2['stl_md5']}`), locked like "
             "gauge_lines_bl060.json (`g2_locked`, `g2_src_txt`; another print falls back to ASSUMPTION GAUGE-GEOM). "
             "Lines now / before (microstrain): " + "; ".join(
                 f"{k} {[s_['pass_if_abs_microstrain_at_most'] for s_ in v['steps']]} / {g2['was']['lines'].get(k)}"
                 for k, v in g2["tests"].items()) + ". The outer cheek did not change since BL-055 (< 0.2 %).")
    L.append("- Kit regenerated: `test_register.csv`, `outputs/release/test_kit/` (results template, guide G6, PDF).")
    L.append("")
    L.append("## 8. Screenshots")
    L.append("")
    for sh in res.get("screenshots", []):
        L.append(f"- `{Path(sh).relative_to(F.REPO) if Path(sh).is_absolute() else sh}`")
    txt = "\n".join(L) + "\n"
    (F.DESIGN_DIR / "frame_iter1.md").write_text(txt)
    return txt


def pick(res: dict) -> str:
    """Rubric: strong is the gate (at least as strong as H1), then the lightest frame line; ties -> fewer parts."""
    ok = [n for n, r in res["concepts"].items() if n != "h1" and r["gate"]["at_least_as_strong"]]
    if not ok:
        ok = [n for n, r in res["concepts"].items() if r["gate"]["R1_pass"]]
    return min(ok, key=lambda n: res["concepts"][n]["frame_line_g"]) if ok else "h1"


if __name__ == "__main__":  # pragma: no cover
    r = report()
    print(json.dumps({n: (v["frame_line_g"], v["min_margin_static"], v["gate"]) for n, v in r["concepts"].items()},
                     indent=1))
