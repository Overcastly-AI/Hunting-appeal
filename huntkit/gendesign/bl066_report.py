"""BL-066 record: designs/pack_5200/iter1/frame/bl066_cflite.{json,md} and the screenshots, from the cached runs of
``bl066_cflite`` (check, check_gj, eigen, lash_check). Run: ``python -m huntkit.gendesign.bl066_report``."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np

from . import bl066_cflite as B
from . import frame_iter1 as FI

BL065 = FI.REPO / "outputs" / "bl065"
H1_ROW = {"strength": 1.63, "fatigue": 1.249, "creep": 2.664, "buckling (eigen, BL-065)": 1.34,
          "cinch-cycled fatigue": 0.856, "joints (H1: z 234 joint strength / fatigue)": 1.158}


def _lb(g):
    return g / 453.592


# ------------------------------------------------------------------------------------------------ eigen summary
def eigen_summary(tag: str) -> dict | None:
    """BL-065's rule: buckling of record = min(member eigen with the stay tops free, frame eigen with the crown held,
    set-down foot held + crown held), per basis."""
    out = {}
    for b in ("fine_sm8", "fine", "fine_sm8.cyc"):
        p = BL065 / f"{tag}_{b}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        full = dict(r.get("full", {}))
        pe = BL065 / f"{tag}_{b}_extra.json"
        if pe.exists():
            full.update(json.loads(pe.read_text())["full"])
        # set-down sets are read with the loaded foot on the ground (run_setdown), as BL-065 does
        frame = min(((v["modes"][0]["margin"], k, v["modes"][0]["lead"]) for k, v in full.items()
                     if "single_stay_setdown" not in k), default=None)
        mem = {m: {"eig_free": round(v["unbraced"]["margin"], 3), "eig_crown": round(v["braced"]["margin"], 3),
                   "record": round(v["margin_record"], 3), "section": round(v["margin_section"], 3), "set": v["set"],
                   "K_eff": round(v["unbraced"]["K_eff"], 2)} for m, v in r["members"].items()}
        mm = min(mem.items(), key=lambda kv: kv[1]["eig_free"])
        sd = None
        ps = BL065 / f"{tag}_{b}_setdown.json"
        if ps.exists():
            s = json.loads(ps.read_text())
            sd = s.get("min_foot_held_crown_held")
        rec = min(x for x in (frame[0] if frame else None, mm[1]["eig_free"], sd) if x is not None)
        out[b] = {"frame_crown_held": round(frame[0], 3) if frame else None, "frame_set": frame[1] if frame else None,
                  "frame_lead": frame[2] if frame else None, "member_min": mm[0], "member_min_eig_free": mm[1]["eig_free"],
                  "setdown_foot_crown_held": round(sd, 3) if sd else None, "buckling_of_record": round(rec, 3),
                  "members": mem, "free_reading": round(r["free_min"]["margin"], 3) if "free_min" in r else None}
    return out or None


# ------------------------------------------------------------------------------------------------ figures
def fig_parts(con: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    cols = {"P1": "#3b6e8f", "P2": "#c9772f", "P3": "#5b8a3a"}
    off = {"P1": -60.0, "P2": 0.0, "P3": 60.0}
    fig = plt.figure(figsize=(9, 10), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    for nm, s in con["info"]["stl"].items():
        m = trimesh.load(FI.REPO / s["file"])
        m = m.simplify_quadric_decimation(face_count=9000)
        v = m.vertices.copy()
        v[:, 2] += off[nm]
        pc = Poly3DCollection(v[m.faces], facecolor=cols[nm], edgecolor="none", alpha=0.95)
        n = m.face_normals
        shade = 0.45 + 0.55 * np.clip(n @ np.array([0.3, -0.6, 0.75]), 0, 1)
        rgb = np.array(matplotlib.colors.to_rgb(cols[nm]))
        pc.set_facecolor(np.clip(shade[:, None] * rgb[None], 0, 1))
        ax.add_collection3d(pc)
        zc = float(v[:, 2].mean())
        ax.text(175, 0, zc, f"{nm}  {s['g']:.0f} g", fontsize=11, color=cols[nm], weight="bold")
    # tubes (grey lines), unshifted
    for sx in (1, -1):
        th = np.linspace(0, 2 * np.pi, 20)
        for z0 in (B.TUBE["z0"], B.TUBE["z1"]):
            ax.plot(sx * B.TUBE["x"] + 11 * np.cos(th), B.TUBE["y"] + 11 * np.sin(th), z0, color="0.3", lw=0.8)
        ax.plot([sx * B.TUBE["x"]] * 2, [B.TUBE["y"]] * 2, [B.TUBE["z0"], B.TUBE["z1"]], color="0.2", lw=4, alpha=0.6)
    ax.set_xlim(-180, 220)
    ax.set_ylim(-200, 200)
    ax.set_zlim(-70, 620)
    ax.set_box_aspect((400, 400, 690))
    ax.view_init(elev=14, azim=-62)
    ax.set_axis_off()
    sep = con["info"]["separation_rerastered"]
    ax.set_title("BL-066 CF-LITE on separated parts: P1 / P2 / P3 exploded 60 mm along the tubes (grey, unshifted)\n"
                 f"exported STLs re-rastered: {sep['n_components']} separate printed bodies, joined only by the tubes "
                 "+ bonds", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def fig_margins(rows: list, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=110)
    y = np.arange(len(rows))
    h1 = [r[1] if r[1] is not None else np.nan for r in rows]
    cf = [r[2] for r in rows]
    ax.barh(y + 0.2, h1, 0.38, color="#8a8a8a", label="H1 (released)")
    ax.barh(y - 0.2, cf, 0.38, color=["#c0392b" if c < 1.0 else "#2e7d32" for c in cf], label="CF-LITE, separated parts")
    xmax = max(3.0, np.nanmax(h1) + 0.4)
    for i, (lab, a, c) in enumerate(rows):
        ax.text(min(c, xmax - 0.25) + 0.03, i - 0.2, f"{c:.2f}", va="center", fontsize=8)
        if a is not None:
            ax.text(a + 0.03, i + 0.2, f"{a:.2f}", va="center", fontsize=8, color="0.35")
    ax.axvline(1.0, color="k", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("margin (SF / requirement); 1.0 = HA-LS-1 limit")
    ax.set_xlim(0, xmax)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title("BL-066: H1 vs CF-LITE per HA-LS-1 row (red = below 1.0)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def fig_util(con: dict, bonds: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = FI._base()
    cen = c["cen"]
    u = FI.util_of(con["name"])
    fig, axs = plt.subplots(1, 2, figsize=(11, 8.5), dpi=100, gridspec_kw={"width_ratios": [3, 2]})
    ax = axs[0]
    pr = con["printed"]
    order = np.argsort(cen[pr, 1])[::-1]
    sc = ax.scatter(cen[pr, 0][order], cen[pr, 2][order], c=np.clip(u[pr][order], 0, 1), s=1.2, cmap="viridis",
                    vmin=0, vmax=1)
    cf = con["cf"]
    ax.scatter(cen[cf, 0], cen[cf, 2], c="0.75", s=0.6)
    for zg in B.GAP_Z.values():
        ax.axhline(zg, color="r", lw=0.6, ls="--")
    fig.colorbar(sc, ax=ax, shrink=0.6, label="printed max utilisation (1/margin), static bases")
    ax.set_aspect("equal")
    ax.set_title("Printed parts: utilisation (front view); grey = carbon tubes;\nred dashes = part boundaries", fontsize=10)
    ax = axs[1]
    names = list(bonds)
    pk = [bonds[n]["peak"]["margin"] for n in names]
    ax.barh(range(len(names)), pk, color=["#c0392b" if p < 1 else "#2e7d32" for p in pk])
    for i, p in enumerate(pk):
        ax.text(p + 0.02, i, f"{p:.2f}", va="center", fontsize=8)
    ax.axvline(1, color="k")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([n.replace("P2 ", "P2\n") for n in names], fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Bond Volkersen peak margin per sleeve\n(2.96 MPa, axial E t + torque G t, C8 at limit)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


# ------------------------------------------------------------------------------------------------ record
def record() -> dict:
    v = B.variant_defaults()
    con = B.build(v)
    name = v["name"]
    res = json.loads((FI.OUT / f"check_{name}.json").read_text())
    summ = FI.summary(res)
    walls = B.sleeve_walls(con["label"], v)
    cover = B.bond_coverage(con["label"], v)
    alt = name + "_gj"
    bonds_model = B.bonds(name, v, walls=walls, cover=cover)
    bonds_bound = B.bonds(name, v, walls=walls, alt=alt, cover=cover)
    bonds_imposed = B.bonds(name, v, walls=walls, gw=con["info"]["tube"]["GJ_ratio_vox_over_tube"], cover=cover)
    beam = B.tube_beam_check(name)
    oh = B.tube_open_hole(name)
    eig = eigen_summary(name)
    mass = B.mass(con, v)
    sizing = B.size_bonds(name, alt, walls, v, cover=cover)
    pinned = {f"{n} x D{d:g}, boss {t:g} mm": B.pinned_option(bonds_bound, name, n=n, d=d, print_t=t)
              for n, d, t in ((2, 4.0, 6.0), (2, 5.0, 6.0), (2, 5.0, 8.0))}
    rd = lambda f: json.loads((B.OUT / f).read_text()) if (B.OUT / f).exists() else None   # noqa: E731
    return {"con": con, "v": v, "res": res, "summary": summ, "walls": walls, "cover": cover,
            "bonds_model": bonds_model, "bonds_bound": bonds_bound, "bonds_imposed": bonds_imposed, "tube_beam": beam,
            "open_hole": oh, "eigen": eig, "mass": mass, "sizing": sizing, "pinned": pinned,
            "lash": rd("lash_h1.json"), "lash_cflite": rd("lash_cflite.json"),
            "lash_bonds": B.lash_bonds(walls, cover, v)}


def tube_upsize(beam_margin: float, target: float) -> list:
    """Bending-governed tube (the governing tube row is the z 192 bending at the P1 | P2 gap): margin ~ I / ro at the
    same resultants; ID held at 18.0 (the crown-leg bore). Mass from the record density."""
    ro0, ri = B.TUBE["od"] / 2, B.TUBE["id"] / 2
    I0 = math.pi / 4 * (ro0 ** 4 - ri ** 4)
    out = []
    for od in (23.0, 24.0, 25.0):
        ro = od / 2
        I = math.pi / 4 * (ro ** 4 - ri ** 4)
        m = beam_margin * (I / ro) / (I0 / ro0)
        dg = 2 * math.pi * (ro ** 2 - ro0 ** 2) * (B.TUBE["z1"] - B.TUBE["z0"]) * B.TUBE["rho"]
        out.append({"od_mm": od, "margin": round(m, 2), "meets": m >= target, "tubes_delta_g": round(dg, 1)})
    return out


# m3: H1 box members (frame_iter1.grow_members on the released print, 2 mm raster x 1.06 g/cm3), recomputed BL-066:
# +57.5 g. The "+55 g" of DECISIONS 2026-11-24 had no source; BL-065 / BL-066 carry 57.5.
H1_BOX_G = 57.5


def voxsplit_members() -> dict | None:
    """Member eigen (stay tops free / crown held) on the PRE-EXPORT voxel split of the same parts: shows which
    readings the STL export moves (BL-066: lower branch L 1.52 on the voxel split, 0.46 on the exported STL)."""
    p = BL065 / "cflite_p_voxsplit_fine_sm8.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    return {m: {"eig_free": round(v["unbraced"]["margin"], 3), "eig_crown": round(v["braced"]["margin"], 3),
                "K_eff": round(v["unbraced"]["K_eff"], 2), "set": v["set"]} for m, v in r["members"].items()}


def fix_options(r: dict) -> dict:
    """Item 7: the smallest fix per failing row and the frame line it gives (g). Bonded sizing per sleeve
    (size_bonds); the pinned screen (pinned_option, 2 x D5, 8 mm bosses, the lightest that clears fatigue bearing);
    the lower-branch-L buckling fix as a first-order estimate (ASSUMPTION LB-FIX)."""
    fl = r["mass"]["frame_line_g"]
    sz = r["sizing"]
    bonded_feasible = all(x.get("g") is not None for x in sz.values())
    bonded_add = sum(x["g"] if x.get("g") is not None else x["g_at_limits"] for x in sz.values())
    pin = r["pinned"]["2 x D5, boss 8 mm"]
    pin_add = sum(x["delta_g_vs_bonded"] for x in pin.values())
    lb_fix = LB_FIX_G
    return {"as_drawn_frame_line_g": fl,
            "bonded": {"feasible": bonded_feasible, "add_g": round(bonded_add, 1),
                       "frame_line_g": round(fl + bonded_add + lb_fix, 1),
                       "note": "P3 bonded cannot pass at the search limits (10 mm wall, 1.5 mm line, 3 x D6): "
                               f"min {sz['P3 top node'].get('at_limits_min')}, needs "
                               f"{sz['P3 top node'].get('dry_bond_needed_mpa')} MPa dry bond (cited 3.7)"},
            "pinned_P1_P3": {"add_g": round(pin_add, 1), "lower_branch_fix_g": lb_fix,
                             "frame_line_g": round(fl + pin_add + lb_fix, 1), "rows": pin,
                             "note": "first-order screen only: no contact FE, backlash or PA creep under the pins"},
            "h1_frame_line_g": r["mass"]["frame_line_h1_g"]}


def t6p_spec(bb: dict, v: dict) -> list:
    """M3: T6p-T coupon pass lines per sleeve (load_standard.md T6 rule: mean failure >= 1.5 x the largest FE limit
    transfer, lowest >= 1.25 x; C7 / C8 transfers are limit = factored), the fatigue line (1e5 cycles 0 -> the 1.6 g
    static-carry transfer, no debond, stiffness change <= 10 %), and the dry bond strength the coupon must imply for
    the Volkersen peak to reach 1.0 (2.96 / 0.8 hot-wet / peak margin x 3.7 dry ... = 3.7 / peak margin)."""
    rows = []
    coupon = {"P1 lower node": "T6p-T1: P1 band (40 mm, 0.8 mm line)",
              "P2 lower-branch root": "T6p-T2a: P2 root (50 mm, 0.5 mm line)",
              "P2 mid-bar knuckle": "T6p-T2b: P2 knuckle (36 mm, 0.5 mm line)",
              "P2 z 420 lash collar": "T6p-T2c: P2 C-collar (18 mm, 0.5 mm line, 62 % arc)",
              "P2 upper-branch root": "T6p-T2d: P2 upper root (26 mm, 0.5 mm line)",
              "P3 top node": "T6p-T3: P3 node (71.5 mm, 0.8 mm line)"}
    for sl, r in bb.items():
        lt = r["limit_transfer"]
        rows.append({"coupon": coupon[sl], "sleeve": sl, "n": "3 pull + 3 torsion + 1 fatigue",
                     "pull_mean_n": round(1.5 * lt["dN_n"], 0), "pull_lowest_n": round(1.25 * lt["dN_n"], 0),
                     "torque_mean_nm": round(1.5 * lt["dT_nmm"] / 1000, 1),
                     "torque_lowest_nm": round(1.25 * lt["dT_nmm"] / 1000, 1),
                     "fatigue_1e5_pull_n": round(lt["fat_dN_n"], 0),
                     "fatigue_1e5_torque_nm": round(lt["fat_dT_nmm"] / 1000, 1),
                     "dry_bond_implied_needed_mpa": round(B.BOND_DRY_MPA / min(1.0, r["peak"]["margin"]) if
                                                          r["peak"]["margin"] < 1 else B.BOND_DRY_MPA, 2),
                     "governing_dN": lt["dN_set"], "governing_dT": lt["dT_set"]})
    return rows


# ASSUMPTION LB-FIX: lower branch L root (z 195-247, x 76-98, about 900 voxels = 7.6 g a side): the eigen margin
# 0.46 -> 1.0 needs P_cr x 2.2; by depth (I ~ h^3) about +30 % depth on that stub, about +2.3 g a side. Not run.
LB_FIX_G = 4.6


def write(log=print) -> dict:
    r = record()
    con, v, s = r["con"], r["v"], r["summary"]
    B.SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [fig_parts(con, B.SCREENS / f"{B.SHOT}1.png")]
    bb = r["bonds_bound"]
    eig = r["eigen"] or {}
    eig_rec = min((e["buckling_of_record"] for e in eig.values()), default=None)
    bmin = B.bond_min(bb)
    sc, cc = s["static_cinch"], s["cinch_cycled"]
    lh, lc = r["lash"], r["lash_cflite"]
    rows = [("printed strength (FI99, static-cinch)", 1.63, sc["strength"]),
            ("printed fatigue (static-cinch)", 1.249, sc["fatigue"]),
            ("printed creep", 2.664, sc["creep"]),
            ("cinch-cycled fatigue (R1)", 0.856, cc["fatigue"]),
            ("buckling of record (eigen, BL-065 rule)", 1.34, eig_rec if eig_rec is not None else float("nan")),
            ("tube strength, beam on resultants", None, float(r["tube_beam"]["margin"])),
            ("tube fatigue (voxel ring, 1.6 g)", None, sc.get("tube_fatigue")),
            ("tube open hole at P3 pins", None, float(r["open_hole"]["P3 pins (bound: cut z 468)"]["margin_open_hole"])),
            ("joints / bonds: strength (Volkersen peak, C8 at limit)", 1.158, bmin[0]),
            ("joints / bonds: fatigue", 1.158, min(x["fatigue"]["margin"] for x in bb.values())),
            ("fail-safe: printed-sleeve bearing", None, min(x.get("failsafe_print_bearing", {"margin": 9e9})["margin"]
                                                         for x in bb.values())),
            ("BL-068 lash (after), body p99", lh["states"]["after"]["margin_p99"] if lh else None,
             lc["states"]["after"]["margin_p99"] if lc else None),
            ("BL-068 lash bonds (peak at limit)", None, min(x["peak_margin_limit"] for x in r["lash_bonds"].values()))]
    rows = [(a, b_, float(c_)) for a, b_, c_ in rows if c_ is not None]
    shots.append(fig_margins(rows, B.SCREENS / f"{B.SHOT}2.png"))
    shots.append(fig_util(con, bb, B.SCREENS / f"{B.SHOT}3.png"))
    for p in shots:
        sz = Path(p).stat().st_size
        if sz > 1_500_000:
            raise RuntimeError(f"{p} is {sz} bytes")
    fails = [(a, round(c_, 3)) for a, b_, c_ in rows if c_ < 1.0]
    below_h1 = [(a, b_, round(c_, 3)) for a, b_, c_ in rows if b_ is not None and c_ < b_]
    out = {"ticket": "BL-066", "date": "2026-11-24", "code": "huntkit/gendesign/bl066_cflite.py, bl066_report.py",
           "model": "v3: STL bore over the tube length only (v2 drilled the stay foot); runs of 2026-11-24 22:47-23:40",
           "variant": v, "parts": {"split_voxel": con["info"]["split_voxel"],
                                   "separation_rerastered": con["info"]["separation_rerastered"],
                                   "raster_crumbs_deleted": con["info"]["raster_crumbs_deleted"],
                                   "stl": con["info"]["stl"], "voxels": con["info"]["voxels"],
                                   "bond_layer_voxels": con["info"]["bond_layer_voxels"]},
           "summary": s, "per_basis": {b: {k: r["res"][b][k] for k in ("min", "governing_tag", "buckling_record_min",
                                                                     "buckling_section_min", "tube")}
                                       for b in FI.BASES},
           "sleeve_walls": r["walls"], "bond_coverage": r["cover"], "bonds_model_torque": r["bonds_model"],
           "bonds_torque_bound": bb, "bonds_torque_imposed_twist_lower_bound": r["bonds_imposed"],
           "tube_beam": r["tube_beam"], "tube_open_hole": r["open_hole"],
           "tube_upsize": tube_upsize(float(r["tube_beam"]["margin"]), 1.63),
           "eigen": eig, "eigen_voxel_split_members_diagnostic": voxsplit_members(),
           "h1_box_members_g": H1_BOX_G, "mass": r["mass"], "sizing_bonded": r["sizing"], "pinned_screen": r["pinned"],
           "fix_options": fix_options(r), "t6p_t_spec": t6p_spec(bb, v), "lash_h1": lh, "lash_cflite": lc, "lash_bonds_cflite": r["lash_bonds"],
           "gate_rows": [{"row": a, "h1": b_, "cflite": round(c_, 3)} for a, b_, c_ in rows],
           "fails_hals1": fails, "below_h1": below_h1, "screenshots": shots}
    B.REC_JSON.write_text(json.dumps(out, indent=1, default=FI._jd))
    log(f"wrote {B.REC_JSON}")
    return out


if __name__ == "__main__":  # pragma: no cover
    write()
