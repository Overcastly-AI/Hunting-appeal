"""BL-068: C' pattern work on CORRIE F rev 3 (pattern-maker, 2026-11-24): P1 level wraps, P2 roll taper, P3 lid locks.

    python designs/pack_5200/bl068_cprime.py              # ledger deltas, lash loads, volume / loadout, screenshots
    python designs/pack_5200/bl068_cprime.py --state 101  # one state (P1 P2 P3 on/off) as JSON (used by the above)
    python designs/pack_5200/bl068_cprime.py --no-screens

The geometry lives in its sources (this module only switches them and measures):

* P1 W-LEVEL: ``build_geometry.W_LEVEL`` -> ``geometry.yaml haul_wraps`` (W1 z 250 / 250, W2 z 420 / 420); consumers
  ``strap_tails.wrap_rows`` (W cuts), ``patterns_corrie_f_rev3.kw_heights`` (K-W notches), ``w_level_checks``,
  ``tripod_fit``.
* P2 ROLL-TAPER: ``corrie_f.ROLL_TAPER`` / ``ROLL_MOUTH_FLAT_MM`` (collar, hem, HDPE strips; RT marks on B-07 follow);
  RT cut from ``strap_tails.roll_row`` on the tapered-roll clip paths (BL-067 ``cp_checks.json``);
  ``patterns_corrie_f_rev3.rtm_raise_check`` (the 60-70 mm tab raise, refused by W3-OVER).
* P3 LID-LOCK: ``corrie_f.CROWN_REAR`` "box" (``crown_kit_straps``: one front lock, rear end box-X'd on B-28t).

Writes ``analysis/bl068_cprime.json`` (all numbers), ``analysis/bl068_lash_loads.json`` (for the frame agent: the lash
points W now loads) and ``outputs/screens/20261124_bl068_<n>.png``. Units mm, N, g, L.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(ROOT), str(HERE), str(HERE / "concepts"), str(HERE / "iter1" / "system"), str(HERE / "iter1" / "looks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

AN = HERE / "analysis"
OUT_JSON = AN / "bl068_cprime.json"
LASH_JSON = AN / "bl068_lash_loads.json"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261124_bl068"
W_DESIGN_N = 225.0          # loadpath_verification.md S9: W1-W3 float clamp, the W G-hook end row of the load-point table
W_PROOF_N = 1.5 * W_DESIGN_N  # W-PULL / LL-H: 338 N (proof rule 1.5 x)
W_CINCH_N = 80.0            # corrie_f.CROWN_PRE_N note: hand-cinched 25 mm ladder lock, the W1-W3 value (pack5200_v31 wraps)
STATES = {"before": (0, 0, 0), "P1": (1, 0, 0), "P2": (0, 1, 0), "P3": (0, 0, 1),
          "P1+P2": (1, 1, 0), "after": (1, 1, 1)}
MEAT_KG_L = 1.05            # ASSUMPTION MEAT-DENS: boned meat about 1.05 kg/L (lean muscle); only used to say how much
#                             meat one round game-bag bundle through the tapered mouth holds; settled by the T9 load-up


# =====================================================================================================================
# the switches
# =====================================================================================================================
def _BG():
    import build_geometry as BG
    return BG


@contextlib.contextmanager
def state(p1: bool = True, p2: bool = True, p3: bool = True):
    """C' geometry with each of P1-P3 on or off. P1 off: geometry.yaml's W1 / W2 swapped for the helix rows
    (build_geometry.haul_wraps(level=False)) in every reader this process uses (strap_tails._geo, bag_concepts.GEOM)."""
    import bag_concepts as BC
    import corrie_f as F
    import strap_tails as ST
    import weight_pass_corrie as WPC
    old_geo, old_bc = ST._geo, BC.GEOM["haul_wraps"]
    wrow = next(r for r in WPC.GEO["weight"]["rows"] if r["item"].startswith("3 frame-anchored wraps"))
    old_w = (wrow["item"], wrow["mass_g"])
    if not p1:
        helix = helix_wraps()
        g0 = ST._geo()

        def _geo():
            g = copy.deepcopy(g0)
            g["haul_wraps"] = helix
            return g
        ST._geo = _geo
        BC.GEOM["haul_wraps"] = helix
        # the ledger's B.2 basis books the W webbing from geometry.yaml's weight row (weight_pass_corrie.GEO): the
        # helix cut lengths, as build_geometry.weight_budget writes that row
        L_m = sum(w["cut_length_mm"] for w in helix) / 1000.0
        wrow["mass_g"] = round(_BG().hw("poly_webbing_25mm", length_m=L_m), 1)
        wrow["item"] = f"3 frame-anchored wraps, 25 mm coyote poly webbing {L_m:.2f} m"
    try:
        with F.cprime(roll_taper=bool(p2), crown_rear="box" if p3 else "lock"):
            yield
    finally:
        ST._geo = old_geo
        BC.GEOM["haul_wraps"] = old_bc
        wrow["item"], wrow["mass_g"] = old_w


def yaml_geo() -> dict:
    import yaml
    return yaml.safe_load((HERE / "geometry.yaml").read_text())


def helix_wraps() -> list:
    """The W1-W3 rows as build_geometry wrote them before BL-068 (W_LEVEL False), from the same generator."""
    BG = _BG()
    with contextlib.chdir(ROOT):
        _, _, c = BG.build()
    return BG.haul_wraps(c["Hf"], c["topo"], level=False)


# =====================================================================================================================
# ledger
# =====================================================================================================================
def measure_state(p1: bool, p2: bool, p3: bool) -> dict:
    """Ledger numbers in one state: the adopted bag rows (huntkit.mass.ledger.adopted_bag_rows = corrie_f.parts at rev
    3, D2, belt M) by configuration, and the iteration-1 ledger scenarios (iter1_weight: P proven now, A after tests)."""
    import corrie_f as F
    import strap_tails as ST
    with state(p1, p2, p3), contextlib.chdir(ROOT):
        import iter1_weight as IW
        with F.revision(3):
            rows = F.parts("M", door="D2")
        inc = {"base": ("base",), "as_hunted": ("base", "as_hunted"), "meat_trip": ("base", "as_hunted", "meat_trip")}
        bag = {k: round(sum(r["g"] for r in rows if r["cfg"] in v), 2) for k, v in inc.items()}
        iw = {f"{sc}_{cfg}": IW.total(sc, cfg) for sc in ("P", "A") for cfg in ("base", "as_hunted")}
        if not p1:
            # the roll-up reads geometry.yaml's W webbing row through its own cached sources (strap_arch / ledger), which
            # the in-process switch does not reach: book the helix row there by hand (build_geometry.weight_budget rule)
            BG = _BG()
            lev = [w for w in yaml_geo()["haul_wraps"]]
            d_row = round(BG.hw("poly_webbing_25mm", length_m=sum(w["cut_length_mm"] for w in lev) / 1000.0), 1) - \
                round(BG.hw("poly_webbing_25mm", length_m=sum(w["cut_length_mm"] for w in helix_wraps()) / 1000.0), 1)
            iw = {k: round(v - d_row, 1) for k, v in iw.items()}
        cs = F.crown_kit_straps("M")
        wr = {w["id"]: w["after"]["cut_mm"] for w in ST.wrap_rows("M")}
        rr = ST.roll_row()
        key = [r for r in rows if r["name"].split(" ")[0] in ("B-06", "B-06f", "B-07", "B-07s")]
    return {"state": [int(p1), int(p2), int(p3)], "adopted_bag_g": bag, "iter1_g": iw,
            "rows": {r["name"]: r["g"] for r in key},
            "w_cuts_mm": wr, "rt_cut_mm": rr["after"]["cut_mm"],
            "b28": {k: cs[k] for k in ("adjusters", "rear", "cut_mm", "tail_used_mm", "tail_worst_mm", "keepers_per_strap",
                                      "mass_g")}}


def _run_state(bits) -> dict:
    s = "".join(str(int(b)) for b in bits)
    r = subprocess.run([sys.executable, str(Path(__file__)), "--state", s], cwd=ROOT, capture_output=True, text=True,
                       check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def ledger_deltas() -> dict:
    """Each state in its own process (the roll-up caches), then the delta of each P alone and in sequence."""
    st = {k: _run_state(v) for k, v in STATES.items()}

    def d(a, b):
        out = {}
        for grp in ("adopted_bag_g", "iter1_g"):
            out[grp] = {k: round(st[b][grp][k] - st[a][grp][k], 1) for k in st[a][grp]}
        return out
    return {"states": st,
            "alone": {p: d("before", p) for p in ("P1", "P2", "P3")},
            "in_sequence": {"P1": d("before", "P1"), "P2": d("P1", "P1+P2"), "P3": d("P1+P2", "after")},
            "total": d("before", "after"),
            "basis": "adopted_bag_g: corrie_f.parts (rev 3, D2, belt M) summed per configuration = the ledger's adopted "
                     "bag rows (huntkit.mass.ledger.adopted_bag_rows); iter1_g: iter1_weight.total (roll-up scenarios "
                     "P proven now / A after tests, belt M, crown kit M), the BL-062 / BL-067 basis"}


# =====================================================================================================================
# structural hand-off: the lash points W loads
# =====================================================================================================================
def lash_loads(wraps_after: list | None = None, wraps_before: list | None = None) -> dict:
    """Per W1 / W2 end: the frame lash point, the hardware, and the strap force on the point (design S9 225 N, proof
    338 N, service cinch 80 N) along the strap's first run from the point to the bag's frame-face corner, with the
    helix rise of the wrap (KW-PATH: z linear in the developed path). Frame FCS (x + wearer's right, y + aft, z up)."""
    import bag_concepts as BC
    import corrie_f as F
    import patterns_corrie_f_rev3 as PR
    hp = BC.GEOM["frame"]["hard_points"]
    after = wraps_after or [w for w in BC.GEOM["haul_wraps"] if w["id"] in ("W1", "W2")]
    before = wraps_before or [w for w in helix_wraps() if w["id"] in ("W1", "W2")]
    c = F.make()

    def rows(ws):
        out = {}
        for w in ws:
            zR, zL = float(w["z_R_at_19in"]), float(w["z_L_at_19in"])
            zm = 0.5 * (zR + zL)
            with F.frame_face(c):
                a, d = float(c.a([zm])[0]), float(c.depth([zm])[0])
            xa = abs(float(hp[w["anchor_R"]][0]))
            run = max(a - xa, 0.0)
            T = 2 * run + 2 * d + 2 * a                    # developed path (kw_heights, KW-PATH)
            slope = (zL - zR) / T                          # dz per mm of path, R -> L
            for side, name, hw in (("R", w["anchor_R"], "heavy ladder lock (ladder_lock_25mm_heavy)"),
                                   ("L", w["anchor_L"], "rated 25 mm G-hook (g_hook_25mm_aluminium)")):
                P = [float(v) for v in hp[name]]
                sx = 1.0 if side == "R" else -1.0
                with F.frame_face(c):
                    yf = float(c.frame_y([P[2]])[0])
                dx, dy = sx * (a - abs(P[0])), yf - P[1]
                h = math.hypot(dx, dy)
                dz = (slope if side == "R" else -slope) * h     # the strap leaves R climbing toward L (and vice versa)
                n = math.sqrt(h * h + dz * dz)
                u = [dx / n, dy / n, dz / n]
                out[name] = {"wrap": w["id"], "end": side, "hardware": hw, "point_xyz_mm": [round(v, 1) for v in P],
                             "strap_dir_unit": [round(v, 3) for v in u],
                             "force_design_n": [round(W_DESIGN_N * v, 1) for v in u],
                             "force_proof_n": [round(W_PROOF_N * v, 1) for v in u],
                             "force_cinch_n": [round(W_CINCH_N * v, 1) for v in u],
                             "rise_deg": round(math.degrees(math.atan2(dz, h)), 1)}
        return out
    A, B = rows(after), rows(before)
    allp = sorted(set(A) | set(B), key=lambda k: (k[-1], float(k.split("_z")[1].split("_")[0])))
    status = {}
    for k in allp:
        if k in A and k not in B:
            status[k] = "NEW: loaded by W after BL-068, not before"
        elif k in B and k not in A:
            status[k] = "UNLOADED after BL-068 (was loaded)"
        elif A[k]["wrap"] != B[k]["wrap"] or A[k]["end"] != B[k]["end"] or A[k]["hardware"] != B[k]["hardware"]:
            status[k] = f"CHANGED: {B[k]['wrap']} {B[k]['end']} -> {A[k]['wrap']} {A[k]['end']}"
        else:
            status[k] = "same wrap / end; direction changes (level instead of a helix)" if \
                A[k]["strap_dir_unit"] != B[k]["strap_dir_unit"] else "unchanged"
    mirror = {}
    for k, v in A.items():
        m = k[:-1] + ("L" if k.endswith("R") else "R")
        if m in B:
            u, w_ = v["strap_dir_unit"], B[m]["strap_dir_unit"]
            mirror[k] = {"mirror_point_loaded_before": m, "this_dir": u, "mirror_dir_before": w_,
                         "is_mirror_image": abs(u[0] + w_[0]) < 0.02 and abs(u[1] - w_[1]) < 0.02}
    return {"ticket": "BL-068 P1 (DECISION W-LEVEL)", "for": "structural-fea-engineer (BL-066 frame rework)",
            "frame_coords": "FCS: x + wearer's right, y + aft, z up, mm (geometry.yaml frame.hard_points)",
            "load_basis": {"design_n": W_DESIGN_N, "design_src": "loadpath_verification.md S9 (W1-W3 float clamp), the "
                           "W G-hook end row of mfg load_points", "proof_n": W_PROOF_N, "proof_src": "W-PULL / LL-H "
                           "(1.5 x)", "cinch_n": W_CINCH_N, "cinch_src": "corrie_f.CROWN_PRE_N note (W1-W3 hand cinch)",
                           "direction": "strap's first run from the lash point to the bag's frame-face corner at the "
                           "point's height, with the wrap's rise (ASSUMPTION KW-PATH); force ON the point = T x unit"},
            "after": A, "before": B, "status": status, "mirror_check": mirror,
            "new_points": [k for k, s in status.items() if s.startswith("NEW")],
            "changed_points": [k for k, s in status.items() if s.startswith(("CHANGED", "same wrap"))],
            "note": "do not run frame FE here (BL-068 scope); the frame agent checks these points"}


# =====================================================================================================================
# volume and loadout
# =====================================================================================================================
def volume_loadout(rs=None) -> dict:
    """85 L +/- 3 with the tapered collar, and what passes the tapered mouth."""
    import yaml
    import concepts_mass as CM
    import corrie_f as F
    import patterns_corrie_f_rev3 as PR
    rs = rs or PR.build("today", addons=False)
    o = rs.geo["rt_origin"]
    flat_today = 2.0 * CM.ROLL_HALF_TODAY          # flattened mouth before BL-068 (W + D)
    mouth_today = 2.0 * flat_today                 # its perimeter
    mouth = o["mouth_mm"]
    # ASSUMPTION COLLAR-RULED (concepts_mass): loss = h D (Lm_today - Lm_new) / 6, Lm = flattened mouth; same function,
    # scaled to the mouth as cut (ROLL_HALF_CP = 192 = ROLL_MOUTH_FLAT_MM / 2 gives the factor 1)
    loss = CM.collar_volume_loss_L() * (flat_today - 0.5 * mouth) / (flat_today - 2.0 * CM.ROLL_HALF_CP)
    st = F.sim_table()
    fill = {t: st[t]["fill"]["closed_L"] for t in st if "fill" in st[t]}
    head = sum(fill.values()) / len(fill)
    rev3_fine = {"15": 82.7, "19": 83.5, "23": 83.4}     # corrie_f_body.md 14.x table (rev 3 crown straps, fine mesh)
    items = yaml.safe_load((HERE / "loadouts.yaml").read_text())["items"]
    bag_zone = ("bag_A_low", "bag_A_mid", "bag_A_high", "bag_F_low", "bag_F_mid", "bag_F_high")
    rows = []
    for k, v in items.items():
        if not any(z in bag_zone for z in v.get("pref", [])):
            continue
        d = sorted(float(x) for x in v.get("dims_mm", [0, 0, 0]))
        girth = 2 * (d[0] + d[1])
        rows.append({"item": k, "rigid": bool(v.get("rigid")), "girth_mm": girth, "passes_mouth": girth <= mouth})
    fails = [r["item"] for r in rows if not r["passes_mouth"]]
    rigid_max = max((r["girth_mm"] for r in rows if r["rigid"]), default=0.0)
    soft_max = max((r["girth_mm"] for r in rows if not r["rigid"]), default=0.0)
    dia = mouth / math.pi
    l_per_100 = math.pi * dia ** 2 / 4 * 100 / 1e6
    return {"mouth_perimeter_mm": {"before": round(mouth_today, 1), "after": mouth},
            "mouth_flat_mm": o["mouth_flat_mm"], "perimeter_change_pct": round(100 * (mouth / mouth_today - 1), 1),
            "collar_loss_L": round(loss, 2), "collar_loss_basis": "concepts_mass.collar_volume_loss_L (ASSUMPTION "
                                                                 "COLLAR-RULED), scaled to the mouth as cut",
            "volume_headline_L": {"before": round(head, 2), "after": round(head - loss, 2),
                                  "basis": "corrie_f.sim_table fill closed volume, mean 15 / 19 / 23 in (coarse)"},
            "volume_rev3_fine_L": {t: {"before": v, "after": round(v - loss, 2)} for t, v in rev3_fine.items()},
            "band_L": [82.0, 88.0],
            "headline_in_band": 82.0 <= head - loss <= 88.0,
            "fine_min_after_L": round(min(rev3_fine.values()) - loss, 2),
            "fine_in_band": min(rev3_fine.values()) - loss >= 82.0,
            "loadout_items_checked": len(rows), "loadout_fails": fails,
            "largest_rigid_girth_mm": rigid_max, "largest_soft_girth_mm": soft_max,
            "round_bundle_through_mouth": {"diameter_mm": round(dia, 1), "litres_per_100mm": round(l_per_100, 2),
                                           "meat_kg_per_100mm": round(l_per_100 * MEAT_KG_L, 2),
                                           "basis": "a soft game bag of boned meat as a round bundle of the mouth's "
                                                    "perimeter; ASSUMPTION MEAT-DENS"},
            "meat_route": "boned meat in game bags goes in through the D2 door (z 110-650, the main access since "
                          "BL-011) and is cinched by IM1-IM3; the top is the secondary route"}


# =====================================================================================================================
# screenshots
# =====================================================================================================================
def _draw(ax, p, dx=0.0, dy=0.0, rot=False, title=None, col="#222"):
    import numpy as np

    def T(pts):
        a = np.asarray(pts, float)
        if rot:
            a = a[:, ::-1] * [1, -1]
        return a + [dx, dy]
    cp = p.cut_polygon()
    ext = T(list(cp.exterior.coords))
    ax.fill(ext[:, 0], ext[:, 1], color="#f3efe4", zorder=1)
    ax.plot(ext[:, 0], ext[:, 1], color=col, lw=1.2, zorder=3)
    so = T(p.outline + [p.outline[0]])
    ax.plot(so[:, 0], so[:, 1], color="#888", lw=0.8, ls="--", zorder=3)
    kc = {"fold": "#2a6fdb", "placement": "#2e8b57", "stitch": "#2e8b57", "dart": "#2e8b57", "cut_inside": "#111"}
    for ln in p.internal_lines:
        q = T(ln.points + ([ln.points[0]] if ln.closed else []))
        ax.plot(q[:, 0], q[:, 1], color=kc.get(ln.kind, "#2e8b57"), lw=0.8,
                ls="--" if ln.kind == "fold" else "-", zorder=4)
    for n in p.notches:
        q = T([(n.x, n.y)])
        ax.plot(q[:, 0], q[:, 1], marker="v" if n.kind == "v" else "|", color="#c0392b", ms=5, zorder=5)
    for h in p.drill_holes:
        q = T([(h.x, h.y)])
        ax.plot(q[:, 0], q[:, 1], marker="o", mfc="none", color="#333", ms=3, zorder=5)
    try:
        g0, g1 = p.grain_arrow()
        q = T([g0, g1])
        ax.annotate("", q[1], q[0], arrowprops=dict(arrowstyle="<->", color="#2a6fdb", lw=1.0), zorder=6)
    except Exception:          # noqa: BLE001  (a piece without a grain arrow still draws)
        pass
    if title:
        b = cp.bounds
        bb = T([(b[0], b[3]), (b[2], b[3])]) if not rot else T([(b[0], b[1]), (b[0], b[3])])
        ax.text(float(min(bb[:, 0])), float(max(bb[:, 1])) + 12, title, fontsize=8, va="bottom")


def _save(fig, path: Path) -> Path:
    from PIL import Image
    fig.savefig(path, dpi=110)
    import matplotlib.pyplot as plt
    plt.close(fig)
    if path.stat().st_size > 1.5e6:
        im = Image.open(path)
        im = im.resize((int(im.width * 0.75), int(im.height * 0.75)))
        im.save(path, optimize=True)
    return path


def screens(before, after, lv: dict, out_dir: Path = SCREENS) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    # 1: collar B-06f / B-06 / B-07 / B-07s before vs after
    fig, axs = plt.subplots(2, 1, figsize=(12, 11))
    for ax, rs, tag in ((axs[0], before, "BEFORE (rev 3 as released)"), (axs[1], after, "AFTER BL-068 P2 ROLL-TAPER")):
        x = 0.0
        for pid in ("B-06f", "B-06", "B-07", "B-07s"):
            p = rs.pieces[pid]
            b = p.cut_polygon().bounds
            yoff = 0.0 if pid in ("B-06f", "B-06") else (-150.0 if pid == "B-07" else -250.0)
            xo = x - b[0] if pid in ("B-06f", "B-06") else -b[0]
            _draw(ax, p, dx=xo, dy=yoff - b[1],
                  title=f"{pid} x{p.quantity} ({p.material_id}): top {p.edge_length('top'):.1f} / bottom "
                        f"{p.edge_length('bottom'):.1f}" + (f" / sides {p.edge_length('left'):.1f}"
                                                            if pid in ("B-06f", "B-06") else "") + " mm")
            if pid in ("B-06f", "B-06"):
                x += (b[2] - b[0]) + 330.0
        o = rs.geo["rt_origin"]
        ax.set_title(f"{tag}: mouth {o['hem_mm']:.1f} mm ({0.5 * o['hem_mm']:.0f} mm flat), side cut "
                     f"{o.get('collar_side_cut_mm', 0.0):.1f} mm per edge at the mouth; B-07s {rs.pieces['B-07s'].edge_length('bottom'):.0f} mm",
                     fontsize=10)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("BL-068 P2: roll collar B-06f / B-06 tapered at the side seams; hem B-07 and HDPE strips B-07s "
                 "shortened\n(cut line solid, seam line dashed, notches red, grain blue, RT box-X and roll-end marks "
                 "on B-07)", fontsize=10)
    fig.tight_layout()
    shots.append(_save(fig, out_dir / f"{SHOT}_1.png"))
    # 2: B-07 hem close-up with the RT marks, before vs after
    fig, axs = plt.subplots(2, 1, figsize=(13, 4.8))
    for ax, rs, tag in ((axs[0], before, "BEFORE"), (axs[1], after, "AFTER")):
        p = rs.pieces["B-07"]
        _draw(ax, p)
        for side, v in rs.geo["rt_on_b07"].items():
            ax.text(v["x_centre"], 75, f"roll end {side}\nx {v['x_centre']:.1f}", ha="center", fontsize=7, color="#c0392b")
        ax.set_title(f"{tag}: B-07 hem {p.edge_length('bottom'):.1f} mm, layers at the roll ends "
                     f"{rs.geo['rt_origin'].get('layers_at_roll_ends_mm', ['-', '-'])} mm", fontsize=9)
        ax.set_aspect("equal")
        ax.set_xlim(-30, 1080)
        ax.axis("off")
    fig.suptitle("BL-068 P2: RT strap placements, box-X and roll-end / strip-end marks move with the hem ends", fontsize=10)
    fig.tight_layout()
    shots.append(_save(fig, out_dir / f"{SHOT}_2.png"))
    # 3: B-28 + B-28t before vs after
    fig, axs = plt.subplots(2, 1, figsize=(13, 4.2))
    for ax, rs, tag in ((axs[0], before, "BEFORE (BL-031: heavy ladder lock each end)"),
                        (axs[1], after, "AFTER BL-068 P3: front lock only, rear end box-X'd on B-28t")):
        p = rs.pieces["B-28"]
        _draw(ax, p, rot=True, title=f"B-28 crown strap kit M x2: cut {p.edge_length('left'):.0f} mm")
        t = rs.pieces["B-28t"]
        _draw(ax, t, rot=True, dx=p.edge_length("left") + 60.0, title=f"B-28t x{t.quantity}")
        k = rs.pieces.get("K-28")
        if k is not None:
            _draw(ax, k, rot=True, dx=p.edge_length("left") + 160.0, title=f"K-28 x{k.quantity}")
        ax.set_title(tag, fontsize=9)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("BL-068 P3 LID-LOCK: B-28 rear end folded 30 mm (blue) and box-X'd 21 x 20 (green) on the rear B-28t",
                 fontsize=10)
    fig.tight_layout()
    shots.append(_save(fig, out_dir / f"{SHOT}_3.png"))
    # 4: marker (the regenerated release marker preview of the collar fabric, if exported)
    mk = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "patterns" / "markers" / "markers.json"
    if mk.exists():
        d = json.loads(mk.read_text())["primary_1bag"]
        pdfs = sorted((mk.parent / "primary").glob("*robic*_1bag.pdf")) or sorted((mk.parent / "primary").glob("*.pdf"))
        if pdfs:
            tmp = out_dir / f"{SHOT}_marker_tmp"
            subprocess.run(["pdftoppm", "-png", "-r", "60", "-f", "1", "-l", "1", str(pdfs[0]), str(tmp)], check=True)
            png = sorted(out_dir.glob(f"{SHOT}_marker_tmp*.png"))[0]
            from PIL import Image, ImageChops
            im = Image.open(png).convert("RGB")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bb = ImageChops.difference(im, bg).getbbox()
            im = im.crop(bb) if bb else im
            fig = plt.figure(figsize=(13, 7.5))
            ax = fig.add_axes([0.0, 0.0, 0.42, 0.93])
            ax.imshow(im)
            ax.axis("off")
            key = next((k for k in d if k in pdfs[0].stem), None)
            eff = d.get(key, {}).get("efficiency") if key else None
            ax.set_title(f"{pdfs[0].name}" + (f": {100 * eff:.1f} % used" if eff else ""), fontsize=9)
            prev = marker_before()
            ax2 = fig.add_axes([0.44, 0.02, 0.55, 0.9])
            ax2.axis("off")
            rows_ = []
            for sc in ("primary_1bag", "primary_10bag"):
                for k, v in json.loads(mk.read_text())[sc].items():
                    if not isinstance(v, dict) or "efficiency" not in v:
                        continue
                    p_ = (prev or {}).get(sc, {}).get(k, {})
                    yd = v["length_mm"] / 914.4 / (10 if "10bag" in sc else 1)
                    yd0 = p_.get("length_mm", float("nan")) / 914.4 / (10 if "10bag" in sc else 1)
                    rows_.append([sc.replace("primary_", ""), k[:26], f"{100 * p_.get('efficiency', float('nan')):.1f}",
                                  f"{100 * v['efficiency']:.1f}", f"{yd0:.2f}", f"{yd:.2f}"])
            t = ax2.table(cellText=rows_, colLabels=["marker", "material", "eff % before", "eff % after",
                                                     "yd/bag before", "yd/bag after"], loc="upper left",
                          cellLoc="left", colWidths=[0.1, 0.36, 0.13, 0.13, 0.14, 0.14])
            t.auto_set_font_size(False)
            t.set_fontsize(7)
            t.scale(1, 1.15)
            fig.suptitle("BL-068: markers regenerated at the roll width (primary fabrics). The tapered collar shortens "
                         "the 10-bag 330D / ULTRA 200 markers; 1-bag markers keep their length (longest piece governs)",
                         fontsize=10)
            shots.append(_save(fig, out_dir / f"{SHOT}_4.png"))
            png.unlink()
    # 5: W level + tripod + RTM raise summary
    g = after.geo["bl068"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.5))
    ax = axs[0]
    import patterns_corrie_f_rev3 as PR
    for tag, col in (("helix", "#999"), ("level", "#2e8b57")):
        r = g["w_level"][tag]["R"]
        for wid in ("W1", "W2"):
            z = r[f"{wid}_z"]
            ax.axhspan(z - 12.5, z + 12.5, xmin=0.05 if tag == "helix" else 0.5, xmax=0.45 if tag == "helix" else 0.95,
                       color=col, alpha=0.6)
            ax.text(0.25 if tag == "helix" else 0.72, z, f"{wid} {tag} z {z:.0f}", fontsize=8, ha="center",
                    va="center", transform=ax.get_yaxis_transform())
    for lab, (z0, z1), col in (("IMP-8 cup", PR.IMP8_Z, "#c9b37e"), ("FP pocket", PR.FP_Z, "#d8e3f0"),
                               ("B-11 bow tabs", (PR.B11_BOW_Z[0] - 25, PR.B11_BOW_Z[1] + 25), "#f0d0d0")):
        ax.axhspan(z0, z1, xmin=0.0, xmax=0.04, color=col)
        ax.text(0.0, z1, lab, fontsize=7, transform=ax.get_yaxis_transform(), va="bottom")
    ax.axhline(600, color="#7a5", ls=":")
    ax.text(0.5, 604, "B-26 cord z 600", fontsize=7, transform=ax.get_yaxis_transform())
    ax.set_ylim(0, 760)
    ax.set_xticks([])
    ax.set_ylabel("z on the R gusset, mm (mid-gusset)")
    ax.set_title(f"P1: W1 / W2 on the R gusset, helix (before) vs level (after); bow tab gap "
                 f"{g['w_level']['level']['min_bow_gap_mm']:.1f} mm", fontsize=9)
    ax = axs[1]
    ax.axis("off")
    tl = ["Tripod fit (TRIPOD-HOLD: lower end held = cup or a hold in the lower third):"]
    for k, v in g["tripod"]["rows"].items():
        tl.append(f"  {k}: holds {', '.join(n for n, _ in v['holds'])}; lower end "
                  f"{'HELD' if v['lower_end_held'] else 'NOT held'}; top free {v['top_free_mm']:.0f} mm")
    rr = g["rtm_raise"]
    tl += ["", "RTM buckle tab raise (keep the 565 mm RT cut?):"]
    for k, v in rr["raised"].items():
        tl.append(f"  +{k} mm: W3 buckle gap {v['w3_buckle_gap_min_mm']} mm (need 10), RT cut {v['rt_cut_mm']:.0f}, "
                  f"{'OK' if v['ok'] else 'FAIL: ' + ', '.join(v['w3_corners_failing'])}")
    tl += [f"  -> {rr['decision']}", "", f"Volume: headline {lv['volume_headline_L']['before']} -> "
           f"{lv['volume_headline_L']['after']} L; fine rev 3 min {lv['fine_min_after_L']} L (band 82-88)",
           f"Mouth {lv['mouth_perimeter_mm']['before']} -> {lv['mouth_perimeter_mm']['after']} mm; loadout fails: "
           f"{lv['loadout_fails'] or 'none'}"]
    ax.text(0.0, 1.0, "\n".join(tl), fontsize=7.2, va="top", family="monospace", wrap=True)
    fig.suptitle("BL-068 checks: P1 level wraps and the tripod, P2 RTM tab raise, volume", fontsize=10)
    fig.tight_layout()
    shots.append(_save(fig, out_dir / f"{SHOT}_5.png"))
    return shots


def marker_before() -> dict | None:
    """markers.json as committed before this regeneration (git HEAD), for the before / after table."""
    try:
        r = subprocess.run(["git", "show", "HEAD:outputs/release/pack5200_corrie_f_rev3/patterns/markers/markers.json"],
                           cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(r.stdout)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


# =====================================================================================================================
def build_pair():
    import patterns_corrie_f_rev3 as PR
    with state(False, False, False):
        before = PR.build("today", addons=False)
    after = PR.build("today", addons=False)
    return before, after


def run(write: bool = True, shots: bool = True) -> dict:
    import patterns_corrie_f_rev3 as PR
    before, after = build_pair()
    rep = PR.seam_report(after)
    led = ledger_deltas()
    lv = volume_loadout(after)
    lash = lash_loads()
    g = after.geo["bl068"]
    out = {"ticket": "BL-068", "date": "2026-11-24",
           "seams": {"n": len(rep.results), "mismatches_1mm": len(rep.mismatches)},
           "grain_missing": [pid for pid, p in after.pieces.items() if p.grain is None],
           "P1": {"kw_z": after.geo["kw_z"], "w_level": g["w_level"], "tripod": g["tripod"],
                  "w_cuts_mm": {"before": led["states"]["before"]["w_cuts_mm"],
                                "after": led["states"]["after"]["w_cuts_mm"]}},
           "P2": {"rt_origin": after.geo["rt_origin"], "rt_on_b07": after.geo["rt_on_b07"],
                  "rtm_raise": g["rtm_raise"], "rt_cut_mm": {"before": led["states"]["before"]["rt_cut_mm"],
                                                             "after": led["states"]["after"]["rt_cut_mm"]},
                  "rifle": {k: after.geo["rt_rifle"][k] for k in ("min_flat_mm", "standoff_min_mm",
                                                                    "standoff_below_barrel_od", "ok")},
                  "rifle_before": {k: before.geo["rt_rifle"][k] for k in ("min_flat_mm", "standoff_min_mm")},
                  "volume_loadout": lv},
           "P3": {"b28": {"before": led["states"]["before"]["b28"], "after": led["states"]["after"]["b28"]}},
           "ledger": led, "lash_loads_json": str(LASH_JSON.relative_to(ROOT))}
    if shots:
        out["screens"] = [str(p.relative_to(ROOT)) for p in screens(before, after, lv)]
    if write:
        OUT_JSON.write_text(json.dumps(out, indent=1, default=float))
        LASH_JSON.write_text(json.dumps(lash, indent=1, default=float))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", help="three bits P1 P2 P3, e.g. 101: print that state's ledger numbers as JSON")
    ap.add_argument("--no-screens", action="store_true")
    a = ap.parse_args(argv)
    if a.state:
        b = [c == "1" for c in a.state]
        print(json.dumps(measure_state(*b), default=float))
        return
    r = run(shots=not a.no_screens)
    led = r["ledger"]
    print("seams", r["seams"], "grain missing", r["grain_missing"])
    for p in ("P1", "P2", "P3"):
        print(p, "alone", led["alone"][p], "| in sequence", led["in_sequence"][p])
    print("total", led["total"])
    print("screens", r.get("screens"))


if __name__ == "__main__":
    main()
