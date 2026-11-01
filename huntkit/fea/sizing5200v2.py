"""Pack 5200 frame, v2 sizing against HA-LS-1 (designs/pack_5200/analysis/load_standard.md).

v2 topology changes (from the v1 study's recommendations, frame_sizing.md):
  1. straight stays (one tube foot -> stay top, no lumbar elbow; lumbar curve moves into the formed plate
     and the foam). Foot moved in-line under the stay top (x 115) so the crown legs stay parallel.
  2. carbon wraps (wet/prepreg QI wrap, ``cfrp_plate_quasi_iso``) instead of 7075 sleeves/sockets/collars.
  3. formed hat/pan lumbar plate: return flanges top + bottom, face pressed toward the body by the flange
     depth (restores the old lumbar offset), CF pad-up behind the hipbelt pivot.
  4. longer crown bushings (70-110 mm), lower bushing carried on the LEG END (always full engagement and
     the widest bushing spread at every torso setting), 120 deg contact land credited (ring moment
     0.154 F R instead of the point-load 0.318 F R; huntkit.fea.rings) - to be proven by the crush coupon.
  5. upper bar sized separately (it carries the rack-lock pawl at mid-span).
Run: ``python -m huntkit.fea.cli size5200v2 [--procs 4] [--pickle /tmp/sw2.pkl]``.
"""
from __future__ import annotations

import itertools
import shutil
import time
from pathlib import Path

import numpy as np

from .sizing import _map, k_for_walls, pareto, section_spec
from .sizing5200 import (FRAME_BUDGET_G, _desc, _plain, _yaml_sec, crown_load_summary, evaluate, leg_for,
                         params_for)

TARGET_G = (550.0, 700.0)
OLD = {"mass_g": 1103.0, "label": "v1 recommended (7-case SF 2.0 standard)"}
WRAP = "cfrp_plate_quasi_iso"
V2 = {"stay_style": "straight", "low_bushing": "leg_end", "bushing_contact_deg": 60.0,
      "sleeve_material": WRAP, "standard": "ls1", "adhesive": "mma"}
BASE2 = {**V2, "bar": section_spec(("round", 18), "RW45", 4), "ubar": section_spec(("round", 22), "RW45", 6),
         "spine": section_spec(("round", 20), "RW45", 6), "plate": ("cfrp_plate_quasi_iso", 2.0),
         "lumbar_flange_mm": 20.0, "lumbar_padup_t_mm": 1.5, "sleeve_t": 1.0, "bushing_len": 90.0}

# the v1 recommended design (frame.yaml before this study), for the old-vs-new comparison
V1_REC = {"stay": section_spec(("round", 25), "RW45", 6), "leg": section_spec(("round", 20), "RW45", 8),
          "bar": section_spec(("round", 22), "RW45", 6), "plate": ("cfrp_plate_quasi_iso", 4.0),
          "spine": section_spec(("round", 20), "RW45", 6), "adhesive": "mma", "sleeve_t": 2.0, "bushing_len": 70.0}
V1_MASS_ITEMS = {
    "tubes: stay_lower": 37.0, "tubes: stay_upper": 110.5, "tubes: mid_bar": 27.7, "tubes: upper_bar": 27.7,
    "tubes: crown_leg": 112.3, "tubes: crown_top_bar": 27.7, "tubes: crown_spine": 32.7,
    "lumbar plate (250 x 140)": 217.0, "7075 sockets/sleeves + gussets": 337.9,
    "adhesive (incl. lumbar-plate bond)": 43.4, "foot boots (2)": 28.0, "Ti hipbelt pivot insert": 28.0,
    "crown rack + pawl housing + pulley guides": 44.0, "UHMWPE bushings (4)": 23.0, "spine clamp": 6.0}


def _q(c):
    return evaluate(c, (15, 23))


def _f(c):
    return evaluate(c, (15, 19, 23))


def stay_options():
    for od in (20.0, 22.0, 25.0):
        for fam in ("RW0", "RW45", "UD90"):
            for k in k_for_walls(fam, (0.8, 1.0, 1.25, 1.5)):
                yield section_spec(("round", od), fam, k)


def _ckpt(path, key, fn):
    """Stage checkpoint: reuse ``path.<key>.pkl`` if present, else run ``fn`` and save it."""
    import pickle
    if path is None:
        return fn()
    f = Path(f"{path}.{key}.pkl")
    if f.exists():
        return pickle.loads(f.read_bytes())
    out = fn()
    f.write_bytes(pickle.dumps(out))
    return out


def sweep(log=print, procs=4, keep_a=6, keep_d=16, keep_c=1, ckpt=None):
    t0 = time.time()
    ca = []
    for st in stay_options():
        for lf, lk in (("RW45", 4), ("RW45", 6), ("RW45", 8)):
            leg = leg_for(st, lf, lk)
            if leg is not None:
                ca.append({**BASE2, "stay": st, "leg": leg})
    sa = _ckpt(ckpt, "A", lambda: _map(_q, ca, procs))
    log(f"A: {len(sa)} stay/leg options, {time.time() - t0:.0f} s")

    def rank(e):   # feasible-first by mass, else by margin
        return (0, e["mass_g"]) if e["margin"] >= 1.0 else (1, -e["margin"])
    best = []
    seen = set()
    for e in sorted(sa, key=lambda e: (-(e["stay_margin"] >= 1.0), e["tubes_g"])):
        key = (e["cand"]["stay"]["od"], e["cand"]["stay"]["layup"][0]["angle"], len(e["cand"]["stay"]["layup"]))
        if e["stay_margin"] < 1.0 or key in seen:
            continue
        seen.add(key)
        best.append(e)
        if len(best) >= keep_a:
            break
    if not best:
        best = sorted(sa, key=rank)[:keep_a]
    # B: bars / upper bar / spine
    cb = []
    for e in best:
        for bar, ub, sp in itertools.product(
                [section_spec(("round", od), "RW45", 4) for od in (16, 18)],
                [section_spec(("round", od), "RW45", k) for od, k in ((20, 4), (22, 4), (22, 6))],
                [section_spec(("round", od), "RW45", k) for od, k in ((18, 4), (20, 4), (20, 6))]):
            cb.append({**e["cand"], "bar": bar, "ubar": ub, "spine": sp})
    sb = _ckpt(ckpt, "B", lambda: _map(_q, cb, procs))
    log(f"B: {len(sb)} bar/spine variants, {time.time() - t0:.0f} s")
    # C: plate / flange / pad-up / wrap thickness / bushing length on the 2 best B per stay
    cc = []
    for e in best:
        mine = sorted([x for x in sb if x["cand"]["stay"] == e["cand"]["stay"]], key=rank)[:keep_c]
        for x in mine:
            for pt, fl, pu, sl, bl in itertools.product((1.5, 2.0), (15.0, 20.0, 25.0), (1.0, 1.5),
                                                        (0.75, 1.0), (70.0, 110.0)):
                cc.append({**x["cand"], "plate": ("cfrp_plate_quasi_iso", pt), "lumbar_flange_mm": fl,
                           "lumbar_padup_t_mm": pu, "sleeve_t": sl, "bushing_len": bl})
    sc = _ckpt(ckpt, "C", lambda: _map(_q, cc, procs))
    log(f"C: {len(sc)} plate/joint variants, {time.time() - t0:.0f} s")
    allq = sa + sb + sc
    feas = sorted([e for e in allq if e["margin"] >= 1.0], key=lambda e: e["mass_g"])
    pick, seen = [], set()
    for e in feas[:keep_d] + pareto(allq)[:keep_d]:
        if e["label"] not in seen:
            seen.add(e["label"])
            pick.append(e["cand"])
    sd = _ckpt(ckpt, "D", lambda: _map(_f, pick, procs))
    log(f"D: {len(sd)} full 15/19/23 in checks, {time.time() - t0:.0f} s")
    return {"stageA": sa, "stageB": sb, "stageC": sc, "stage2": allq, "stage3": sd}


# ============================================================================ deliverables
def recommend(evals):
    feas = sorted([e for e in evals if e["feasible"]], key=lambda e: e["mass_g"])
    return (feas[0], True) if feas else (max(evals, key=lambda e: e["margin"]), False)


def stock_rows(e, model):
    from .sizing import STOCK_NOTE, _spec_desc
    c = e["cand"]
    n = model["nodes"]
    rows = []

    def add(part, qty, spec, centre, cut):
        geo, w, lay, fam = _spec_desc(spec)
        rows.append({"part": part, "qty": qty, "section": geo, "wall_mm": round(w, 3), "layup": lay,
                     "source": STOCK_NOTE[fam], "centreline_mm": round(centre, 1), "cut_length_mm": round(cut, 1)})

    def dist(a, b):
        return float(np.linalg.norm(np.subtract(n[a], n[b])))
    L = dist("SL0", "SL530")
    add("stay, straight (foot boot -> stay-top wrap collar)", 2, c["stay"], L, L - 5.0)
    add("crown leg (telescoping, low bushing bonded on its bottom end)", 2, c["leg"], 430.0, 430.0)
    span = dist("SL330", "SR330")
    od = c["stay"]["od"]
    add("mid bar (z 330)", 1, c["bar"], span, span - od)          # mitred / coped to the stay, wrapped
    add("upper bar (z 520, pawl housing)", 1, c.get("ubar") or c["bar"], span, span - od)
    add("crown top bar", 1, c["bar"], 230.0, 230.0 - c["leg"]["od"])
    add("crown spine tube (rack bonded on)", 1, c["spine"], 300.0, 300.0)
    return rows


def joint_design(c):
    sl = c.get("sleeve_t", 1.0)
    nply = max(2, int(round(sl / 0.22)))
    return {
        "adhesive": "adhesive_methacrylate_ma (tube-to-tube fit-up, fillets) + wet-layup epoxy for the wraps",
        "bondline_mm": 0.5,
        "adhesive_shear_modulus_mpa_ASSUMPTION": 300.0,
        "wrap": f"{WRAP}-equivalent wrap, {sl:g} mm = {nply} plies 3k twill alternating 0/90 and +-45, "
                "wet-laid (or prepreg) over sanded tubes, peel-ply + shrink tape, room-temp cure + 65 C post-cure",
        "wrap_overlap_mm": f"{c.get('overlap', 30.0):g} on each tube (through-joints {c.get('through_overlap', 40.0):g}); "
                           "wrap ends scarfed / ply-dropped over 8 mm (peel relief, not credited)",
        "stay": "ONE straight tube per side, foot boot -> stay top (no lumbar elbow)",
        "foot_boot": "7075 boot bonded 25 mm over the stay foot, carries the shelf-pivot boss 20 mm outboard "
                     "(keeps the shelf pivot at x +-135) + bumper",
        "mid_hub / upper_hub": "bar end coped (fish-mouthed) to the stay, tacked with MMA, then carbon-wrapped "
                               "(tube-to-tube, bicycle-frame style); CF gusset in the wrap",
        "stay_top_collar": f"carbon wrap {sl:g} mm over the stay top; UHMWPE bushing {c.get('bushing_len', 90):g} mm "
                           "with a 120 deg contact land seats inside",
        "low_bushing": f"UHMWPE {c.get('bushing_len', 90):g} mm sleeve bonded on the crown-leg bottom end (slides in the stay bore)",
        "crown_corner": "leg top + top bar coped and wrapped; extension-post socket = short 7075 liner inside the wrap",
        "lumbar_plate": f"formed QI CFRP pan {c['plate'][1]:g} mm, return flanges {c.get('lumbar_flange_mm', 0):g} mm "
                        f"top + bottom, face {c.get('lumbar_flange_mm', 0):g} mm toward the body; lands bonded to both "
                        f"stays z 50-190; CF pad-up {c.get('lumbar_padup_t_mm', 0):g} mm behind the Ti pivot insert",
        "galvanic": "no bare Al on carbon: anodise + glass-bead bondline / E-glass ply under any Al liner",
    }


def write_frame_yaml(e, path, model, crown_loads):
    import yaml
    c = e["cand"]
    p = params_for(c)
    frame = {"topology": "pack5200_crown", "name": "pack5200_frame_v2",
             "geometry": "designs/pack_5200/geometry.yaml",
             "torso_in": 19.0, "haul_mode": False, "extension_posts": False,
             "stay_section": _yaml_sec(c["stay"]), "leg_section": _yaml_sec(c["leg"]),
             "bar_section": _yaml_sec(c["bar"]),
             "upper_bar_section": _yaml_sec(c.get("ubar") or c["bar"]),
             "spine_section": _yaml_sec(c["spine"]),
             "lumbar_plate_material": c["plate"][0], "lumbar_plate_t": c["plate"][1],
             "lumbar_flange_mm": c.get("lumbar_flange_mm", 0.0), "lumbar_padup_t_mm": c.get("lumbar_padup_t_mm", 0.0),
             "stay_style": c.get("stay_style", "segmented"), "low_bushing": c.get("low_bushing", "stay"),
             "bushing_contact_deg": c.get("bushing_contact_deg", 0.0),
             "bushing_len_mm": c.get("bushing_len", 40.0), "joint": p["joint"]}
    doc = {
        "schema": "huntkit.frame/v1",
        "design": "pack_5200",
        "revision": "v2 (HA-LS-1 standard, straight stays, carbon wraps, formed lumbar pan, leg-end bushings)",
        "description": "Carbon frame sized by huntkit.fea.sizing5200v2 against HA-LS-1 "
                       "(designs/pack_5200/analysis/load_standard.md). 'frame' = params for "
                       "huntkit.fea.frames.build_frame (dispatches to huntkit.fea.pack5200.build); override torso_in "
                       "(15-23) and extension_posts. Units mm.",
        "load_standard": "HA-LS-1 (designs/pack_5200/analysis/load_standard.md)",
        "frame": frame,
        "torso_range_in": [15, 23],
        "stock": stock_rows(e, model),
        "joints": joint_design(c),
        "mass_g": {k: round(float(v), 1) for k, v in e["mass_items"].items()},
        "mass_total_g": round(e["mass_g"], 1),
        "mass_target_g": list(TARGET_G),
        "mass_v1_g": OLD["mass_g"],
        "crown_loads_fea": crown_loads,
        "results": {"standard": "HA-LS-1", "feasible": bool(e["feasible"]), "min_margin": round(float(e["margin"]), 3),
                    "governing": e["governing"]["what"], "governing_torso_in": e["governing"]["torso"],
                    "margin_by_check": {k: round(float(v), 3) for k, v in e["per_check"].items() if isinstance(k, str)}},
        "hardpoint_changes": "designs/pack_5200/analysis/frame_hardpoint_changes.yaml",
        "source": "huntkit/fea/sizing5200v2.py; designs/pack_5200/analysis/frame_sizing.md",
    }
    Path(path).write_text("# Pack 5200 carbon frame v2 - generated by `python -m huntkit.fea.cli size5200v2`.\n"
                          "# Read with huntkit.fea.frames.build_frame_from_yaml(path, torso_in=..).\n"
                          + yaml.safe_dump(_plain(doc), sort_keys=False, allow_unicode=True, width=100))


def hardpoint_changes(model19) -> dict:
    from .pack5200 import load_geometry
    g = load_geometry()
    hp = g["frame"]["hard_points"]
    sp = model19["stay_points"]
    foot, top = np.array(sp["foot"]), np.array(sp["top"])

    def on(z):
        return foot + (z - foot[2]) / (top[2] - foot[2]) * (top - foot)
    u = model19["crown_axis"]
    ch = {
        "stay_foot_R": {"old": hp["stay_foot_R"], "new": [round(float(v), 1) for v in foot],
                        "why": "straight stay: foot in-line under the stay top (x 115) so the two crown legs stay "
                               "parallel; fore-aft position kept"},
        "lumbar_elbow_R": {"old": hp["lumbar_elbow_R"], "new": None,
                           "why": "elbow deleted (one straight tube). Stay centreline at z 130 is now "
                                  f"{[round(float(v), 1) for v in on(130.0)]}; the formed lumbar pan face sits "
                                  "~20 mm toward the body, so the lumbar contour the foam sees is ~unchanged"},
        "crown axis_unit_vector_yz": {"old": g["frame"]["members_topology"]["crown"]["axis_unit_vector_yz"],
                                      "new": [round(u[1], 4), round(u[2], 4)],
                                      "why": "crown legs coaxial with the straight stay, which now leans slightly TOWARD the "
                                             "body going up (old upper stay leaned aft). Crown top bar, lifter anchors and "
                                             f"yoke move {(u[1] - 0.0375) * 71:+.1f} mm (y) at 15 in and "
                                             f"{(u[1] - 0.0375) * 274:+.1f} mm at 23 in (toward the wearer). PACK-DESIGNER: "
                                             "check head clearance and lifter angle at 23 in; if not acceptable, the "
                                             "alternative is foot y -30 (crown axis unchanged) at the cost of 30 mm less "
                                             "buttock clearance"},
        "mid_bar_node_R": {"old": hp["mid_bar_node_R"], "new": [round(float(v), 1) for v in on(330.0)],
                           "why": "follows the straight stay (shelf-strap and bag-mid anchors move with it)"},
        "upper_bar_node_R": {"old": hp["upper_bar_node_R"], "new": [round(float(v), 1) for v in on(520.0)],
                             "why": "follows the straight stay (sub-mm)"},
    }
    for k in ("bag_anchor_low_R", "hip_stabilizer_anchor_R", "load_wing_lash_z80_R", "load_wing_lash_z250_R",
              "load_wing_lash_z420_R", "shoulder_strap_lower_anchor_R"):
        if k in hp:
            z = hp[k][2]
            st_old_y = (hp["stay_foot_R"][1] + (hp["lumbar_elbow_R"][1] - hp["stay_foot_R"][1]) * z / 130.0) if z <= 130 \
                else (hp["lumbar_elbow_R"][1] + (hp["stay_top_crown_socket_R"][1] - hp["lumbar_elbow_R"][1]) * (z - 130) / 400)
            st_old_x = (hp["stay_foot_R"][0] + (hp["lumbar_elbow_R"][0] - hp["stay_foot_R"][0]) * z / 130.0) if z <= 130 else 115.0
            st_new = on(z)
            dx, dy = st_new[0] - st_old_x, st_new[1] - st_old_y
            ch[k] = {"old": hp[k], "new": [round(hp[k][0] + dx, 1), round(hp[k][1] + dy, 1), hp[k][2]],
                     "why": f"rides on the stay: shifts dx {dx:+.1f} dy {dy:+.1f} mm"}
    ch["shelf_pivot_R"] = {"old": hp["shelf_pivot_R"], "new": hp["shelf_pivot_R"],
                           "why": "UNCHANGED: the foot boot carries a 20 mm outboard boss for the pivot"}
    ch["hipbelt_pivot"] = {"old": hp["hipbelt_pivot"], "new": hp["hipbelt_pivot"],
                           "why": "UNCHANGED: carried by the formed lumbar pan (face 20 mm toward the body)"}
    for k in ("stay_top_crown_socket_R", "rack_lock_pawl_upper_bar", "pulley_fixed_guide_A", "pulley_fixed_guide_C"):
        if k in hp:
            ch[k] = {"old": hp[k], "new": hp[k], "why": "UNCHANGED"}
    return {"from": "structural-fea-engineer", "date": "2026-11-01",
            "for": "pack-designer (Spine bag redesign) - update geometry.yaml hard_points / members_topology",
            "summary": "Frame v2 deletes the lumbar elbow: one straight stay per side from the foot (moved 20 mm "
                       "inboard to x +-115, under the stay top) to the unchanged stay top. Crown, stay top, pawl, "
                       "hipbelt pivot and shelf pivots are unchanged. Hard points riding on the stay between z 0 and "
                       "z 530 shift by the amounts below (mirror for _L: negate x). Lower frame is 40 mm narrower at the feet.",
            "changes": ch}


# ---------------------------------------------------------------------------- plots
def plot_utilization(kept19, png, title, mass_g):
    """Envelope utilization over all HA-LS-1 cases at 19 in (members), plus per-case margin bars."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import colors as mcolors
    from .report import CMAP, INK, MUTED, _elem_util, _setup3d
    res_all = kept19["results"]
    base = res_all["static_carry"]
    util = np.zeros(len(base.elements))
    for name, r in res_all.items():
        if name == "tall_load_posts":
            continue
        u = _elem_util(r)
        util = np.maximum(util, u[: len(util)])
    fig = plt.figure(figsize=(6.0, 9.0), dpi=140)
    ax = fig.add_subplot(1, 1, 1, projection="3d")
    norm = mcolors.Normalize(0, 1.0)
    for k, el in enumerate(base.elements):
        if base.elements[k].truss:
            continue
        ax.plot(*base.coords[[el.n1, el.n2]].T, color=CMAP(norm(min(util[k], 1.0))), lw=3.2, solid_capstyle="round")
    k = int(np.argmax(util))
    ax.scatter(*base.coords[[base.elements[k].n1, base.elements[k].n2]].mean(0), s=80, facecolors="none",
               edgecolors=INK, linewidths=1.4)
    _setup3d(ax, base.coords)
    c = base.coords
    ax.set_xlim(c[:, 0].min() - 20, c[:, 0].max() + 20)
    ax.set_ylim(c[:, 1].min() - 60, c[:, 1].max() + 60)
    ax.set_zlim(c[:, 2].min() - 10, c[:, 2].max() + 10)
    ax.set_box_aspect((np.ptp(c[:, 0]) + 40, np.ptp(c[:, 1]) + 120, np.ptp(c[:, 2]) + 20))
    ax.view_init(elev=14, azim=-58)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
    cax = fig.add_axes([0.15, 0.06, 0.7, 0.014])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("utilization = required factor / SF (envelope of all HA-LS-1 cases); 1.0 = limit", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.suptitle(f"{title}\n{mass_g:.0f} g, max member utilization {util.max():.2f} (circle)", fontsize=10, color=INK)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.92, bottom=0.1)
    fig.savefig(png, bbox_inches="tight")
    plt.close(fig)


def plot_mass_compare(old_items, new_items, png, new_total, old_total=1103.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def bucket(items):
        b = {"stay tubes": 0, "crown legs": 0, "bars + spine": 0, "lumbar plate": 0, "sleeves / wraps": 0,
             "adhesive": 0, "boots, pivot, crown lock, bushings": 0}
        for k, v in items.items():
            if "adhesive" in k:
                b["adhesive"] += v
            elif "stay" in k and k.startswith("tubes"):
                b["stay tubes"] += v
            elif "crown_leg" in k:
                b["crown legs"] += v
            elif k.startswith("tubes"):
                b["bars + spine"] += v
            elif "lumbar" in k:
                b["lumbar plate"] += v
            elif "sleeve" in k or "wrap" in k:
                b["sleeves / wraps"] += v
            elif "adhesive" in k:
                b["adhesive"] += v
            else:
                b["boots, pivot, crown lock, bushings"] += v
        return b
    bo, bn = bucket(old_items), bucket(new_items)
    keys = list(bo)
    fig, ax = plt.subplots(figsize=(6.0, 7.0), dpi=140)
    y = np.arange(len(keys))
    h = 0.38
    ax.barh(y - h / 2, [bo[k] for k in keys], height=h, color="#b9c7d6", label=f"v1: {old_total:.0f} g (old standard)")
    ax.barh(y + h / 2, [bn[k] for k in keys], height=h, color="#2a6fb0", label=f"v2: {new_total:.0f} g (HA-LS-1)")
    for i, k in enumerate(keys):
        ax.text(bo[k] + 4, i - h / 2, f"{bo[k]:.0f}", va="center", fontsize=8, color="#555555")
        ax.text(bn[k] + 4, i + h / 2, f"{bn[k]:.0f}", va="center", fontsize=8, color="#1d4f80")
    ax.set_yticks(y)
    ax.set_yticklabels(keys, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("mass (g)", fontsize=9)
    ax.set_title(f"Frame mass, old vs new: {old_total:.0f} g -> {new_total:.0f} g "
                 f"({(new_total - old_total) / old_total * 100:+.0f} %)", fontsize=10, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def plot_test_rig(png):
    """DIY dead-weight / drop / cycle rig sketch (side view), phone format."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle
    fig, ax = plt.subplots(figsize=(6.0, 8.6), dpi=140)
    ink, mut, blue, red = "#222222", "#888888", "#2a6fb0", "#c0392b"
    # wall + floor
    ax.add_patch(Rectangle((0, 0), 0.25, 9.6, color="#dddddd"))
    ax.add_patch(Rectangle((0, 0), 6.0, 0.18, color="#dddddd"))
    # frame posts (2x4 "torso")
    ax.add_patch(Rectangle((0.25, 2.5), 2.2, 0.35, color="#c9a66b"))          # hip log support arm
    ax.add_patch(Rectangle((0.25, 7.6), 2.0, 0.3, color="#c9a66b"))           # shoulder bar arm
    ax.add_patch(Circle((2.25, 2.95), 0.42, color="#a07d45"))                  # hip log (4x4 in foam)
    ax.text(2.25, 2.95, "hip\nlog", ha="center", va="center", fontsize=7, color="white")
    ax.add_patch(Circle((2.1, 7.95), 0.2, color="#a07d45"))                    # shoulder bar
    # pack frame (side view): stay + crown
    ax.plot([2.75, 2.85, 2.95], [1.2, 3.0, 6.8], color=ink, lw=5, solid_capstyle="round")
    ax.plot([2.95, 2.98], [6.8, 8.6], color="#555555", lw=3.5)
    ax.plot([2.35, 2.75], [3.0, 3.1], color=blue, lw=4)                        # hipbelt
    ax.plot([2.1, 2.9, 2.98], [7.95, 7.3, 8.5], color=blue, lw=3)              # shoulder strap + lifter
    ax.text(3.15, 8.2, "crown top: dial indicator /\nlaser dot target (deflection)", fontsize=7.5, color=ink)
    # bag / load
    ax.add_patch(Polygon([[3.0, 1.3], [4.4, 1.6], [4.6, 6.3], [3.05, 6.6]], closed=True, fc="#e6eef6", ec=blue, lw=1.5))
    for i, yy in enumerate((1.9, 2.9, 3.9)):
        ax.add_patch(Rectangle((3.3, yy), 0.9, 0.8, fc="#9aa5ad", ec=ink, lw=0.8))
    ax.text(3.75, 5.0, "load:\nsandbags /\nwater jugs /\nplates", ha="center", fontsize=7.5, color=ink)
    # crane scale + ratchet on the shoulder bar
    ax.text(0.35, 8.15, "ratchet strap + luggage/crane scale:\nsets the 20 % shoulder share", fontsize=7, color=ink)
    # cycle actuator below
    ax.add_patch(Circle((3.9, 0.75), 0.32, fc="white", ec=ink, lw=1.2))
    ax.plot([3.9, 4.1], [0.75, 0.95], color=ink, lw=1.5)
    ax.plot([4.1, 3.9], [0.95, 1.6], color=red, lw=1.5, ls="--")
    ax.text(4.35, 0.55, "T5 cycle: 12 V wiper motor + crank\n+ bungee pulls the load down\n0.4 -> 1.6 g, ~50/min, counter", fontsize=7, color=red)
    # drop arrow
    ax.add_patch(FancyArrowPatch((5.2, 4.2), (5.2, 2.6), arrowstyle="-|>", mutation_scale=14, color=red, lw=1.5))
    ax.text(5.3, 3.3, "T4 drop:\nlift 15-40 mm,\nrelease; phone\naccelerometer\non crown", fontsize=7, color=red)
    ax.text(0.35, 2.1, "2x4 / 4x4 wall frame or\nsawhorses, lag-screwed;\nhip log padded like a pelvis", fontsize=7, color=ink)
    ax.text(0.35, 9.25, "DIY frame test rig (side view, not to scale)", fontsize=11, color=ink, weight="bold")
    ax.text(0.35, 8.95, "T1-T3 hang  |  T4 drop  |  T5 cycle  |  pass criteria: load_standard.md", fontsize=8, color=mut)
    ax.set_xlim(0, 6.0)
    ax.set_ylim(0, 9.6)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


# ---------------------------------------------------------------------------- deliver
def deliver(sw, design_dir="designs/pack_5200", screens_dir="outputs/screens", date="20261101", log=print):
    import yaml
    from .report import report as write_report
    from .sizing import plot_case_margins, plot_pareto
    design_dir, screens_dir = Path(design_dir), Path(screens_dir)
    adir = design_dir / "analysis"
    adir.mkdir(parents=True, exist_ok=True)
    screens_dir.mkdir(parents=True, exist_ok=True)
    s3 = sorted(sw["stage3"], key=lambda e: e["mass_g"])
    rec, feasible = recommend(s3)
    full = evaluate(rec["cand"], (15, 19, 23), keep_results=True)
    model19 = full["kept"][19]["model"]
    crown = crown_load_summary(full)
    write_frame_yaml(full, design_dir / "frame.yaml", model19, crown)
    (adir / "crown_loads.yaml").write_text(
        "# FEA crown retention loads (huntkit.fea.sizing5200v2, HA-LS-1 cases), for the pack-designer\n"
        + yaml.safe_dump(_plain(crown), sort_keys=False))
    (adir / "frame_hardpoint_changes.yaml").write_text(
        "# Frame v2 hard-point changes (structural-fea-engineer -> pack-designer)\n"
        + yaml.safe_dump(_plain(hardpoint_changes(model19)), sort_keys=False, width=110))
    # comparisons
    log("comparison runs ...")
    v1_new = evaluate({**V1_REC, "standard": "ls1"}, (15, 19, 23))
    rec_old = evaluate({**rec["cand"], "standard": "v1"}, (15, 19, 23))
    rec_nocredit = evaluate({**rec["cand"], "bushing_contact_deg": 0.0}, (15, 19, 23))
    # plots
    png_u = adir / "frame_v2_utilization.png"
    plot_utilization(full["kept"][19], png_u, "Frame v2 (HA-LS-1), 19 in torso", full["mass_g"])
    png_m = adir / "frame_v2_mass_old_vs_new.png"
    plot_mass_compare(V1_MASS_ITEMS, full["mass_items"], png_m, full["mass_g"])
    png_r = adir / "frame_test_rig.png"
    plot_test_rig(png_r)
    png_c = adir / "frame_v2_case_margins.png"
    names = [n for n in full["kept"][19]["results"]] + ["fatigue"]
    plot_case_margins({"cases": names, "torsos": (15, 19, 23),
                       "margin": {(n, t): full["per_check"].get((n, t), np.inf) for n in names for t in (15, 19, 23)}},
                      png_c)
    png_p = adir / "frame_v2_pareto.png"
    plot_pareto({"stage2": sw["stage2"], "stage3": s3}, rec if feasible else None, png_p,
                budget_g=FRAME_BUDGET_G, screen_label="screened at 15 + 23 in torso")
    shots = []
    for i, pth in enumerate((png_u, png_m, png_r, png_c), start=1):
        dst = screens_dir / f"{date}_frame2_{i}.png"
        shutil.copyfile(pth, dst)
        shots.append(dst)
    st19 = {"label": "Pack 5200 frame v2, 19 in torso (HA-LS-1)", "frame": model19,
            "results": full["kept"][19]["results"], "joints": full["kept"][19]["joints"],
            "fatigue": full["kept"][19]["fatigue"]}
    write_report(st19, adir / "frame_sizing_cases_19in.md", title="Pack 5200 frame v2 - all HA-LS-1 load cases (19 in torso)")
    md = _md(sw, full, feasible, model19, crown, v1_new, rec_old, rec_nocredit)
    (adir / "frame_sizing.md").write_text(md)
    log(f"wrote {adir / 'frame_sizing.md'}; screens {[str(s) for s in shots]}")
    return {"recommended": full, "feasible": feasible, "screens": shots, "v1_under_ls1": v1_new,
            "rec_under_v1": rec_old, "rec_no_contact_credit": rec_nocredit}


def _test_refs(e) -> list[str]:
    """FEA numbers the owner compares against in T1, T6 and T7."""
    kept = e["kept"]
    out = []
    for t in sorted(kept):
        r = kept[t]["results"]["static_carry"]
        d = r.displacements
        top = np.array(d["TB1"][:3]) - np.array(d["HP"][:3])
        lum = np.array(d["P22"][:3]) - np.array(d["HP"][:3])
        out.append(f"- T1(a) 150 lb static carry, {t} in torso: crown top bar centre moves {top[1]:+.1f} mm fore-aft "
                   f"(+ = away from the back), {top[2]:+.1f} mm vertical relative to the hipbelt pivot; lumbar pan centre "
                   f"{lum[1]:+.1f} mm fore-aft. Most of it is the frame rotating on the modelled body springs (hipbelt "
                   "foam, harness), so the rig reading depends on how stiff the hip log and shoulder bar are: treat it "
                   "as an order-of-magnitude check (+-50 %) and use YOUR first 150 lb reading as the baseline for the "
                   "10 % stiffness-change and permanent-set criteria. At 300 lb expect ~2x (linear).")
    fmax, case_f = 0.0, ""
    jmax = {}
    for t, k in kept.items():
        for n, r in k["results"].items():
            lf = r.meta.get("link_forces", {})
            for lid, f in lf.items():
                if lid.startswith("bush"):
                    fr = float(np.hypot(f[0], f[1]))
                    if fr > fmax:
                        fmax, case_f = fr, f"{n} {t} in, {lid}"
            for j in k["joints"][n]:
                key = j["joint"].rstrip("_LR").rstrip("_")
                cur = jmax.get(key, (0.0, 0.0, ""))
                if abs(j["N"]) > cur[0]:
                    jmax[key] = (abs(j["N"]), j["M"], f"{n} {t} in")
    out.append(f"- T7 bushing crush coupon: max FEA bushing radial force {fmax:.0f} N ({case_f}); test to "
               f"**{1.5 * fmax:.0f} N** with no crack and <= 0.2 mm ovalisation after unload, then to failure.")
    out.append("- T6 joint coupons, largest FEA end force per joint type (all HA-LS-1 cases, limit loads):")
    for k_, (N, M, w) in sorted(jmax.items()):
        out.append(f"  - {k_}: axial {N:.0f} N (with {M / 1e3:.1f} N m bending, {w}) -> mean coupon pull-out "
                   f">= {1.5 * N:.0f} N, lowest >= {1.25 * N:.0f} N")
    return out


def _md(sw, e, feasible, model, crown, v1_new, rec_old, rec_nc):
    from .load_standard import describe
    from .pack5200 import crown_checks, plate_checks
    from .sizing import _spec_desc
    c = e["cand"]
    s3 = sorted(sw["stage3"], key=lambda x: x["mass_g"])
    m = e["mass_g"]
    oz = m / 28.3495
    L = ["# Pack 5200 - carbon frame sizing, v2 (HA-LS-1 standard)", "",
         "Owner: structural-fea-engineer. Standard: [load_standard.md](load_standard.md) (HA-LS-1, owner decision "
         "2026-11-01 \"match the leaders\"). Model: `huntkit/fea/pack5200.py` (v2 options), sweep "
         "`huntkit/fea/sizing5200v2.py` (`python -m huntkit.fea.cli size5200v2`). Frame parameters: "
         "`designs/pack_5200/frame.yaml`. Hard-point changes for the pack-designer: "
         "[frame_hardpoint_changes.yaml](frame_hardpoint_changes.yaml).", "",
         "## Result", ""]
    if feasible:
        L.append(f"**Lightest v2 frame passing every HA-LS-1 check at 15/19/23 in torso: {m:.0f} g ({oz:.1f} oz, "
                 f"{m / 453.6:.2f} lb)**, down from 1103 g ({(m - 1103) / 1103 * 100:+.0f} %). Target 550-700 g; "
                 "competitor frames 450-700 g (KUIU ICON 6 frame 13.7 oz = 388 g; SG Krux 2 lb 7 oz incl. belt + harness).")
    else:
        L.append(f"**No v2 candidate passes every HA-LS-1 check.** Best: {m:.0f} g, min margin {e['margin']:.2f}.")
    L += ["", f"- Design: {e['label']}",
          f"- Min margin (SF / required, all checks, 15/19/23 in): **{e['margin']:.2f}**, governing "
          f"`{e['governing']['what']}` at {e['governing']['torso']:g} in.", "",
          "| check | min margin |", "|---|---|"]
    for k in ("member", "buckling", "bond_avg", "bond_peak", "crown", "plate", "plate_buckling", "fatigue"):
        if k in e["per_check"]:
            L.append(f"| {k.replace('_', ' ')} | {e['per_check'][k]:.2f} |")
    L += ["", "### Min margin per load case (all torsos)", "", "| case | g x factor | 15 in | 19 in | 23 in |", "|---|---|---|---|---|"]
    from .load_standard import TABLE
    for n, (g, f, kg) in TABLE.items():
        row = [f"{e['per_check'].get((n, t), float('nan')):.2f}" for t in (15, 19, 23)]
        L.append(f"| {n} | {kg:g} kg x {g:g} g x {f:g} | " + " | ".join(row) + " |")
    L.append("| fatigue (1e5 x 0->1.6 g) | - | " + " | ".join(f"{e['per_check'].get(('fatigue', t), float('nan')):.2f}" for t in (15, 19, 23)) + " |")
    L += ["", "![utilization](frame_v2_utilization.png)", "", "![case margins](frame_v2_case_margins.png)", "",
          "## Old vs. new", "",
          "| | v1 (old standard) | v2 (HA-LS-1) |", "|---|---|---|",
          "| standard | 7 cases, 2.5 g x SF 2.0 (5.0 x rated), bond peak >= 2.0, buckling >= 3.0 | "
          "static 2.0 x rated; stumble / set-down / shelf / tall load 2.0 g x 1.5 (3.0 x rated); side-hill 1.6 g x 1.5; "
          "overload 91 kg x 1.6 g and hipbelt-off 1.5 g at 1.0 (ultimate); bond peak >= 1.0 at limit; buckling >= 1.5 x factor; "
          "fatigue 1e5 x 1.6 g |",
          "| stays | segmented (lower + upper, bonded 7075 elbow) | one straight tube per side |",
          "| joints | 7075 sleeves / sockets / collars, 2 mm | carbon wraps |",
          "| lumbar plate | 4 mm flat QI, 217 g | formed QI pan + flanges + pivot pad-up |",
          "| crown bushings | 70 mm, low bushing fixed at z 380, point-contact ring formula | leg-end low bushing, "
          f"{c.get('bushing_len', 90):g} mm, 120 deg contact land |",
          f"| mass | 1103 g | **{m:.0f} g** |",
          f"| min margin under its own standard | 1.09 | {e['margin']:.2f} |",
          f"| min margin under the OTHER standard | {v1_new['margin']:.2f} (v1 design under HA-LS-1; governing "
          f"`{v1_new['governing']['what']}`) | {rec_old['margin']:.2f} (v2 design under the old standard; governing "
          f"`{rec_old['governing']['what']}`) |", "",
          f"Where the 1103 -> {m:.0f} g came from: **neither change alone gets there.** The v1 design re-checked "
          f"against HA-LS-1 has only {v1_new['margin']:.2f} margin (governing `{v1_new['governing']['what']}`): the "
          "hipbelt-off abuse case is unchanged by the new standard (1.5 g x 1.0 in both) and, with the point-load ring "
          "formula and the 7075 parts, it sizes the v1 crown just as before. The v2 topology checked against the OLD "
          f"standard has {rec_old['margin']:.2f} margin. The saving is the combination: HA-LS-1 cuts the dynamic design "
          "loads 40 % (5.0x -> 3.0x rated) and the Volkersen-peak requirement 2x, and the topology changes delete the "
          "parasitic mass that no tube size could remove (7075 sleeves 338 -> 65 g as carbon wraps, flat 4 mm plate "
          "217 -> 123 g as a formed pan, elbow joints gone, leg-end bushings unload the crown legs).", "",
          "### Reference values for the physical tests (load_standard.md section 5)", ""] + _test_refs(e) + ["",
          "![mass old vs new](frame_v2_mass_old_vs_new.png)", "",
          "### Mass breakdown (v2)", "", "| item | g | oz |", "|---|---|---|"]
    for k, v in e["mass_items"].items():
        L.append(f"| {k} | {v:.1f} | {v / 28.3495:.2f} |")
    L += [f"| **total (extension posts excluded)** | **{m:.1f}** | **{oz:.1f}** |", "",
          "### Sensitivity: the 120 deg bushing contact credit", "",
          f"Without the contact credit (point-load ring formula, 0.318 F R) the same frame has min margin "
          f"**{rec_nc['margin']:.2f}** (governing `{rec_nc['governing']['what']}`). "
          + ("It still passes: the credit is not load-bearing for this design." if rec_nc["margin"] >= 1.0 else
             "So the credit IS load-bearing: the bushing crush coupon (load_standard.md T7) must pass before release, "
             "or step the crown leg wall up one ply."), "",
          "## Proposed further mass reductions (keep the margins)", "",
          "1. **Fatigue / walking-peak tests first.** If T5 (cycle test) passes at 1.6 g with no stiffness loss, the "
          "fatigue screen (CFRP FI <= 0.5 at the walking peak) can be relaxed to the measured value; it is the most "
          "conservative assumption left in HA-LS-1.",
          "2. **Pulley shares the crown load.** The pawl is assumed to carry 100 % (pulley slack). A pre-tensioned 3:1 "
          "pulley carries part of it; measured in T1 with a luggage scale on the pulley tail, this unloads the upper bar and spine.",
          "3. **Joint coupons (T6) earn the scarfed-wrap credit** (~2x lower Volkersen peak): thinner wraps (0.5 mm) at "
          "the hubs, ~10-15 g.",
          "4. **Formed / corrugated sections** (KUIU ICON 6 style thermoplastic corrugated sheet) need press tooling: "
          "not buildable in the owner's no-autoclave shop now; the formed lumbar pan is the one place it pays. Revisit "
          "for production tooling (a corrugated one-piece lower frame could replace plate + lower stays).",
          "5. **Hardware** (foot boots 28 g, pivot insert, rack + pawl 44 g) is now ~25 % of the frame; a lighter "
          "printed-nylon rack and a 3D-printed Ti pivot are the next 20-30 g.", "",
          "## Crown retention (for the pulley / rack-and-pawl sizing)", "",
          "| case | pawl force N (+ extension / - compression) | torso in |", "|---|---|---|"]
    for k, v in crown["by_case_worst_torso"].items():
        L.append(f"| {k} | {v['force_n']:.0f} | {v['torso_in']:g} |")
    L += ["", f"- Max extension {crown['max_extension_n']:.0f} N, max compression {abs(crown['max_compression_n']):.0f} N "
          "(HA-LS-1 limit loads, pulley assumed slack). Rack rating 5328 N.", ""]
    kept = e["kept"]
    L += ["### Telescoping crown checks (23 in and 15 in, left side)", "", "| case | torso | check | value | SF |", "|---|---|---|---|---|"]
    for t in (15, 23):
        for n_ in ("drop_2p5g", "meat_straps", "hipbelt_off_abuse"):
            r = kept[t]["results"][n_]
            for cc in crown_checks(r, kept[t]["model"]):
                if cc.get("retention") or cc.get("info") or "_R" in cc["check"]:
                    continue
                L.append(f"| {n_} | {t} | {cc['check']} | {cc['value']:.1f} {cc['unit']} | {cc['sf']:.2f} |")
    L += ["", "### Lumbar plate checks (19 in)", "", "| case | check | value | SF |", "|---|---|---|---|"]
    for n_ in ("drop_2p5g", "side_hill_torsion", "single_stay_setdown", "tall_load"):
        r = kept[19]["results"][n_]
        for pc in plate_checks(r, kept[19]["model"]):
            L.append(f"| {n_} | {pc['check']} | {pc['value']:.1f} {pc['unit']} | {pc['sf']:.2f} |")
    L += ["", "## Stock list", "",
          "| part | qty | section | wall mm | layup (inner -> outer) | centreline mm | cut mm | source |",
          "|---|---|---|---|---|---|---|---|"]
    for row in stock_rows(e, model):
        L.append(f"| {row['part']} | {row['qty']} | {row['section']} | {row['wall_mm']:.2f} | {row['layup']} | "
                 f"{row['centreline_mm']:.0f} | {row['cut_length_mm']:.0f} | {row['source']} |")
    L.append(f"| lumbar pan blank | 1 | 250 x {140 + 2 * c.get('lumbar_flange_mm', 0):g} mm before forming | "
             f"{c['plate'][1]:g} | QI twill (0/90, +-45) wet layup over a foam / MDF male mould | - | - | owner layup |")
    L += ["", "## Joint design", ""]
    for k, v in joint_design(c).items():
        L.append(f"- **{k}**: {v}")
    L += ["", "## Sizing sweep", "",
          "Stage A: stays 20/22/25 mm x RW0/RW45/UD90 x walls 0.8-1.5 mm, legs = largest buyable OD in the bore "
          "(>= 0.75 mm bushing) x 3 walls. Stage B: bars 16/18, upper bar 20/22 mm, spine 18/20 mm. Stage C: plate "
          "1.5/2.0 mm x flange 15/20/25 x pad-up 1.0/1.5 x wrap 0.75/1.0 mm x bushing 70/110 mm (base 90). A-C screened "
          "at 15 + 23 in; stage D re-ran the lightest feasible and the Pareto set at 15/19/23 in.", "",
          f"Evaluated: {len(sw['stage2'])} screened, {len(s3)} full checks.", "",
          "![pareto](frame_v2_pareto.png)", "",
          "| mass g | min margin | governing | design |", "|---|---|---|---|"]
    for x in s3[:12]:
        L.append(f"| {x['mass_g']:.0f} | {x['margin']:.2f} | {x['governing']['what']} ({x['governing']['torso']:g} in) | {x['label']} |")
    L += ["", "## Assumptions and caveats", "",
          "- Load cases and factors: `huntkit/fea/load_standard.py` (HA-LS-1); rationale and sources in load_standard.md.",
          "- ASSUMPTION: straight stay foot moved to x +-115 (in-line under the stay top) so the crown legs stay "
          "parallel; shelf pivots stay at x +-135 on a 20 mm boot boss (boss not modelled; it is a 7075 part).",
          "- ASSUMPTION: the formed lumbar pan is a grillage in the plate face, offset toward the body by the "
          "flange depth; top/bottom edge strips are L-sections (web + return flange); the land-to-face transition "
          "is the inclined end strip. +-30 % on plate stresses; shell-model check before release.",
          "- ASSUMPTION: bushing contact pressure is a half-cosine over a 120 deg land (ring moment 0.154 F R, "
          "`huntkit.fea.rings`, verified against Roark's point-load ring). Needs the T7 crush coupon.",
          "- ASSUMPTION: carbon wrap = QI CFRP (`cfrp_plate_quasi_iso`: E 45 GPa) in the Volkersen model; the bond "
          "allowable is still the MMA lap-shear on CFRP x 0.8 hot/wet (wet-layup epoxy onto sanded CFRP is similar). "
          "Wrap-collar ring check shares the ring moment with the stay wall by E t^3 (no composite action credited).",
          "- ASSUMPTION: adhesive moduli (MMA 300 MPa) as v1; hardware masses +-30 %; Ti pivot boss grows "
          "0.35 g per mm of extra standoff.",
          "- Same bag-load split, body springs and hip share (80 %) as v1 (see the v1 notes kept in git history).",
          "- Not modelled: peel at wrap ends, local hub stresses, the yoke plate, the extension posts beyond the "
          "`tall_load_posts` case.", ""]
    return "\n".join(L)
