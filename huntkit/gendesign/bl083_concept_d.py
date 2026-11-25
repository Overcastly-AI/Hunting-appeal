"""BL-083: concept D (tube stays + a formed sheet hip pan that carries the hip torque as a plate) with real joints,
and the B81 lever row (hose-band tees, .049 stays with a local doubler, locally bought metal).

What D is (the "D83" detail design)
-----------------------------------
* **Stays, bars, tees, foot, crown bushings: B81 unchanged** (``bl081_concept_b.build`` is called and its lumbar node is
  cut out: rungs, gussets, hip post, tie columns, saddle plugs and their links). D changes only the lumbar / hip node.
* **Hip pan (tray)**: one laser-cut and press-brake-formed 5052-H32 sheet (SendCutSend; they do NOT bend 6061-T6, see
  ``SCS`` below), four 90 deg bends: a face (x-z plane, x +/-101, z 50-190) whose body-side surface is the Ti mount
  seat at y -48.55 (= the BL-055 boss face, so the BL-056 Ti mount, the 21 mm pin stand-off, the hipbelt centre plate
  and belt B's pad seat (``concepts/corrie.pad_seat``: 190 x 150 backer, 25 mm top return) are all unchanged); two
  side walls (y-z plane) that run aft from the face along the inboard side of each stay (z 78-190, stepped down to
  z 170 beside the stay where the IM1 loop wraps it); 25 mm top and
  20 mm bottom return flanges on the face. The hip torque V x 67 mm reaches the stays as **in-plane bending of the
  side walls** (a 90 mm deep plate) and leaves each wall through two lateral M5 (along x) at z 85 / 155: the
  couple becomes fore-aft bolt shear, and the stay holes sit on the **neutral axis** of the stay's fore-aft bending.
* **Mount spine**: a second formed 5052-H32 part, a vertical channel (web 64 mm, legs 25 mm aft) behind the face from
  the bottom to the top return flange, clamped by the 8 Ti-mount screws and bolted to both flanges. The mount's own
  couple (V x 21 mm stand-off + pad offset) is too much for a 2 mm face in plate bending (first model: strip SF 0.99 at
  1 g); the spine carries it as beam bending to the two flanges, which take it in their plane to the walls.
* Every through-bolt in a tube has a crush sleeve (BL-082); nothing printed is in the pan's load path.

Hip pivot offset (the free variable of the brief)
-------------------------------------------------
The offset is set by the belt, not the frame: belt B's centre plate rides on the Ti pin and its lumbar pad seats on
the pan face (``hipbelt_fit.md`` 4.1, ``concepts/corrie.pad_seat``). Moving the pin aft by d moves the pad seat aft by
d, so the belt pad stack must grow by d (or the whole frame moves d toward the back). ``offset_sweep`` runs the global
model at d = 0 / 15 / 30 mm and books the pan mass saved against the EVA the pad needs.

Basis = BL-081 exactly: HA-LS-1 rev C envelope, torsos 15 / 19 / 23 in, Yahr / Goodman, Kf = Kt from the tube_solid
units (``bl081_local.hole_units``), no preload credit, wet mu 0.15, crush sleeves, printed parts in bearing /
compression on the PAHT hot/wet basis. The BL-081 global and local machinery is re-used by swapping the builder and the
station list into ``bl081_concept_b`` for the duration of a call (``_as_b81``); nothing in bl081 is edited.

Units mm, N, MPa, g, USD.
"""
from __future__ import annotations

import contextlib
import copy
import math

import numpy as np

from huntkit.gendesign import bl080_metal_frame as B80
from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL

REPO = BQ.REPO
OUTDIR = REPO / "designs" / "pack_5200" / "iter2" / "frame_d"
REC_JSON = OUTDIR / "bl083.json"
REC_MD = OUTDIR / "bl083.md"
CACHE = REPO / "outputs" / "bl083"
SHOT = "20261125_bl083_"
DATE = "2026-11-25"
IN = BQ.IN

_B81_BUILD = BQ.build
_B81_STATIONS = BQ.stations
_B81_ROLE = BQ._role

# ----------------------------------------------------------------------------- materials
# 5052-H32 (SendCutSend bends 5052, not 6061-T6). Design values: ASTM B209 sheet minimums as commonly quoted
# (UTS 31 ksi / yield 23 ksi; standard not purchased: ASSUMPTION AL5052-MIN), typical 33 / 28 ksi (SendCutSend
# 5052 page), fatigue 117 MPa at 5e8 R.R. Moore fully reversed (Protolabs 5052-H32 data sheet; makeitfrom 115).
AL5052 = {
    "fy": 159.0, "fu": 214.0, "fy_typ": 193.0, "fu_typ": 228.0, "se_5e8": 117.0, "E": 70300.0, "G": 25900.0,
    "rho": 2.68e-3, "brg_y": 1.5 * 159.0,
    "src": ["https://sendcutsend.com/materials/5052-aluminum/ (typical UTS ~33 ksi, yield ~28 ksi; thicknesses "
            ".040-.500 in, bending specs .040-.250 in; read 2026-11-25)",
            "https://Protolabs.com/media/iw0mfa0k/datasheet-sm-aluminum5052-h32.pdf (fatigue 117 MPa, R.R. Moore, "
            "5e8, completely reversed; search snippet 2026-11-25, secondary)",
            "ASSUMPTION AL5052-MIN: ASTM B209 H32 minimum UTS 31 ksi (214 MPa) / yield 23 ksi (159 MPa) as commonly "
            "quoted; settled by a mill cert with the SendCutSend order",
            "ASSUMPTION BRG-5052: bearing yield at e/D 2 = 1.5 x minimum yield (AA practice 1.5-1.9 x Fy)"],
}


def sn_5052_smax_r0(N: float = 1e5) -> float:
    """R 0 allowable max stress for 5052-H32 at N, on the BL-082 method: the Yahr 6061 curve SHAPE scaled to the
    5052 endurance (ASSUMPTION SN-5052-SCALE: Sa(N) = Se_5052 x (C/sqrt(N) + floor) / floor), Goodman on the minimum
    UTS 214. At 1e5: Sa = 117 x 1.474 = 172.5 MPa, S_max = 2 Sa Su / (Su + Sa) = 191.0 MPa (6061: 190.9)."""
    d = BQ.sn_6061()
    ratio = (d["C"] / math.sqrt(N) + d["floor"]) / d["floor"]
    sa = AL5052["se_5e8"] * ratio
    return 2 * sa * AL5052["fu"] / (AL5052["fu"] + sa)


def mat_5052() -> dict:
    return {"id": "alu_5052_h32_min", "youngs_modulus_mpa": AL5052["E"], "shear_modulus_mpa": AL5052["G"],
            "poisson": 0.33, "design_allowable_mpa": AL5052["fy"], "density_kg_m3": 0.0}


def pan_material(cfg) -> dict:
    if cfg["pan_mat"] == "5052":
        return {"fy": AL5052["fy"], "fu": AL5052["fu"], "fat": sn_5052_smax_r0(), "E": AL5052["E"], "G": AL5052["G"],
                "rho": AL5052["rho"], "brg": AL5052["brg_y"], "beam_mat": mat_5052(), "label": "5052-H32"}
    return {"fy": BQ.FY_6061, "fu": BQ.FU_6061, "fat": BQ.fat_allow_local(1.0), "E": BQ.E_AL, "G": 26000.0,
            "rho": BQ.RHO_AL, "brg": BQ.BRG_Y_ED2, "beam_mat": "alu_6061_t6", "label": "6061-T6"}


# ----------------------------------------------------------------------------- SendCutSend (cited method, price ASSUMPTION)
SCS = {
    "no_6061_bend": "SendCutSend does not bend 6061-T6 ('Because of this we don't offer bending for 6061'; recommends "
                    "5052): https://sendcutsend.com/blog/6061-t6-aluminum-laser-cutting-service/ (read 2026-11-25)",
    "bend_rules": "bend radius / K fixed per material and thickness (no custom radii), max 130 deg, flange >= the "
                  "material minimum over ~50-60 % of the bend length, cut features >= 1/2 die width from each bend "
                  "centreline (dies 0.472 / 0.630 / 0.984 / 1.575 in), holes >= 50 % of t, no minimum quantity, "
                  "bending +1-2 days: https://sendcutsend.com/bending/ (read 2026-11-25); general flange rule >= 0.500 in "
                  "or 4 t: https://sendcutsend.com/blog/the-ultimate-guide-to-sheet-metal-plastic-bending/",
    "pricing": "price drivers = part size, material / thickness, quantity (to 80 % off), complexity (every hole is a "
               "pierce), post-processing (bending); free US shipping on orders >= USD 39; example 5052 .100 in "
               "5.375 x 6.3 in part USD 19.51 cut-only vs USD 37.49 cut + bent (qty 1): "
               "https://sendcutsend.com/pricing/ (read 2026-11-25; 'examples ... general estimates')",
    "cut_part_usd": 19.51,       # cited example, cut-only, qty 1
    "bent_part_usd": 37.49,      # cited example, cut + bent, qty 1
    "free_ship_usd": 39.0,
}


def scs_price(area_in2: float, n_holes: int, n_bends: int) -> float:
    """ASSUMPTION SCS-PRICE (no live quote): the cited qty-1 example (5.375 x 6.3 = 33.9 in2, cut-only USD 19.51)
    scaled by part area to the power 0.5 (material is a small share at qty 1; machine time scales with perimeter) plus
    USD 0.25 per pierce beyond 8, and the cited bending premium (37.49 - 19.51 = USD 17.98) for the first bend plus
    half of it for each further bend (each bend is a press set-up at qty 1)."""
    base = SCS["cut_part_usd"] * math.sqrt(max(area_in2, 33.9) / 33.9) + 0.25 * max(n_holes - 8, 0)
    prem = SCS["bent_part_usd"] - SCS["cut_part_usd"]
    bend = 0.0 if n_bends == 0 else prem * (1 + 0.5 * (n_bends - 1))
    return round(base + bend, 2)


SHEET_T = {".063": 0.063 * IN, ".080": 0.080 * IN, ".090": 0.090 * IN, ".100": 0.100 * IN, ".125": 0.125 * IN}

# ----------------------------------------------------------------------------- design (D83)
CFG_D = {
    **BQ.CFG0,
    "pan_mat": "5052", "pan_t": ".080", "flange_top": 25.0, "flange_bot": 20.0,
    "face_z": (50.0, 190.0), "wall_z": (78.0, 190.0), "pan_bolt_z": (85.0, 155.0), "wall_aft": 12.0,
    "pin_aft": 0.0,              # hip-offset variable: pin (and mount seat, and the pad seat) moved aft by this, mm
    "strut_z": (155.0,),
    "spine_t": ".100", "spine_w": 64.0, "spine_leg": 25.0, "tees": "bolted", "band_n": 2,
    "band_T_upper": 1000.0,      # upper-tee bands set to 3.3 N m (1000 N each): 2000 N total as B81's upper preload
}
FACE_X = (-60.0, -25.0, 0.0, 25.0, 60.0)        # interior face columns (+/- x_w at the bends)
FACE_ZROWS = (50.0, 85.0, 95.0, 120.0, 145.0, 155.0, 170.0, 190.0)
WALL_ZROWS = (85.0, 95.0, 120.0, 145.0, 155.0, 170.0, 190.0)
WALL_STAY_TOP = 170.0                           # wall beside the stay stops here (IM1 loop round the stay above)
BAND = {"T_n": 4.0 / (0.55 * 0.006), "retention": 0.8, "mass_g": 12.0, "usd": 1.50, "width": 9.0,
        "src": "ASSUMPTION BAND: DIN 3017 9 mm W4 worm-drive band, install torque 4.0 N m (Evereon DIN 3017 data, "
               "https://www.directindustry.com/prod/evereon-industries-inc/product-161114-1651278.html, secondary); "
               "band tension T = torque / (K d), K 0.55 (worm on band slots), d 6 mm -> 1212 N; retention 0.8 "
               "(relaxation); 12 g, USD 1.50 each (shop-class price, not read). CL-1 with bands settles T and mu."}


def cfg_d(**kw) -> dict:
    c = {**CFG_D, **kw}
    return c


def t_of(cfg) -> float:
    return SHEET_T[cfg["pan_t"]]


def geom(cfg) -> dict:
    st = BQ.STOCK[cfg["stay"]]
    R = st["od"] / 2
    t = t_of(cfg)
    y_seat = BQ.Y_MOUNT + cfg["pin_aft"]
    return {"R": R, "t": t, "x_w": 115.0 - R - t / 2, "y_f": y_seat + t / 2, "y_seat": y_seat,
            "pin_y": BQ.PIN_Y + cfg["pin_aft"], "yline": lambda z: -10.0 * z / 530.0}


# ----------------------------------------------------------------------------- model
def _split_stay(m, tag, z):
    nodes = m["nodes"]
    nid = f"S{tag}{z:g}"
    if nid in nodes:
        return nid
    for mm in m["members"]:
        if mm["group"].startswith("stay") and mm["group"].endswith(tag):
            a_, b_ = mm["nodes"]
            za, zb = nodes[a_][2], nodes[b_][2]
            if min(za, zb) < z < max(za, zb):
                pa, pb = np.array(nodes[a_]), np.array(nodes[b_])
                nodes[nid] = list(map(float, pa + (z - za) / (zb - za) * (pb - pa)))
                m["members"].append({**mm, "id": f"{nid}-{b_}", "nodes": [nid, b_]})
                mm["nodes"], mm["id"] = [a_, nid], f"{a_}-{nid}"
                return nid
    raise KeyError(nid)


def _plate(m, prefix, P, us, vs, eu, ev, t, mat, group, G, E, edge_sec=None):
    """Grillage of a flat plate (pack5200 method: strips along u and v with J = w t^3 / 6, two truss diagonals per
    cell with A_d = G a t L_d / (2 E b c^2)). P(i, j) -> node id; nodes must exist. ``edge_sec(i_v)`` may return a
    special section for the u-strips of row j (flanged edge strips)."""
    from huntkit.fea.pack5200 import _strip
    from huntkit.fea.sections import generic
    nu, nv = len(us), len(vs)
    for j in range(nv):
        wv = ((vs[j] - vs[j - 1]) if j > 0 else 0) / 2 + ((vs[j + 1] - vs[j]) if j < nv - 1 else 0) / 2
        sec = (edge_sec(j, wv) if edge_sec else None) or _strip(wv, t)
        for i in range(nu - 1):
            m["members"].append({"id": f"{prefix}u{i}_{j}", "nodes": [P(i, j), P(i + 1, j)], "section": sec,
                                 "material": mat, "group": group, "ref": list(ev)})
    for i in range(nu):
        wu = ((us[i] - us[i - 1]) if i > 0 else 0) / 2 + ((us[i + 1] - us[i]) if i < nu - 1 else 0) / 2
        for j in range(nv - 1):
            m["members"].append({"id": f"{prefix}v{i}_{j}", "nodes": [P(i, j), P(i, j + 1)], "section": _strip(wu, t),
                                 "material": mat, "group": group, "ref": list(eu)})
    dm = {"youngs_modulus_mpa": E, "shear_modulus_mpa": G, "design_allowable_mpa": 1e9, "density_kg_m3": 0.0,
          "id": "plate_shear_equivalent"}
    nodes = m["nodes"]
    for i in range(nu - 1):
        for j in range(nv - 1):
            p00, p11 = np.array(nodes[P(i, j)]), np.array(nodes[P(i + 1, j + 1)])
            p10, p01 = np.array(nodes[P(i + 1, j)]), np.array(nodes[P(i, j + 1)])
            a = (np.linalg.norm(p10 - p00) + np.linalg.norm(p11 - p01)) / 2
            b = (np.linalg.norm(p01 - p00) + np.linalg.norm(p11 - p10)) / 2
            Ld = math.hypot(a, b)
            c = a / Ld
            Ad = G * a * t * Ld / (2 * E * b * c * c)
            for k, (n1, n2) in enumerate(((P(i, j), P(i + 1, j + 1)), (P(i + 1, j), P(i, j + 1)))):
                m["members"].append({"id": f"{prefix}d{i}_{j}_{k}", "nodes": [n1, n2],
                                     "section": generic(Ad, 1.0, 1.0, 1.0), "material": dm, "type": "truss",
                                     "group": group + "_shear", "no_kg": True})


def _flanged_edge(t, f):
    from huntkit.fea.pack5200 import _flanged_strip
    return lambda w: _flanged_strip(w, t, f)


def spine_sec(cfg):
    """Vertical channel (local y = x: web width; local z = y: legs aft). Iy carries M_x (the mount couple)."""
    from huntkit.fea.sections import generic
    t, w, f = SHEET_T[cfg["spine_t"]], cfg["spine_w"], cfg["spine_leg"]
    Aw, Af = w * t, f * t
    A = Aw + 2 * Af
    zc = 2 * Af * (f / 2) / A
    Iy = w * t ** 3 / 12 + Aw * zc ** 2 + 2 * (t * f ** 3 / 12 + Af * (f / 2 - zc) ** 2)
    Iz = t * w ** 3 / 12 + 2 * (f * t ** 3 / 12 + Af * (w / 2 - t / 2) ** 2)
    J = (w + 2 * f) * t ** 3 / 3
    s = generic(A, Iy, Iz, J, ymax=w / 2, zmax=max(f - zc, zc + t / 2), Wt=J / t)
    s.kind = "spine_channel"
    s.dims = {"w": w, "t": t, "f": f, "zc": zc}
    return s


def pan_bolt_link_k(cfg) -> list:
    """Lateral M5 (along x) through the stay, the wall on the inboard side only (single shear plane), bolt in both
    tube bores (crush sleeve): half the B81 two-plate stiffness for shear and the couples about y / z (ASSUMPTION
    GAP-K as BL-081); axial along x = the wall pressed on the stay by preload (3e4 N/mm)."""
    st = BQ.STOCK[cfg["stay"]]
    v = BQ.bolt_link_k(st["t"], t_of(cfg), st["od"] / 2 - st["t"] / 2, "x", "z", axial=True)
    return [v[0], v[1] * 0.5, v[2] * 0.5, v[3], v[4] * 0.5, v[5] * 0.5]


def build(cfg: dict | None = None, torso: float = 19.0, rigid: bool = False) -> dict:
    """D83 beam model: the B81 model with its lumbar node replaced by the hip pan."""
    from huntkit.fea.sections import generic, tube_round
    cfg = cfg_d(**(cfg or {}))
    m = copy.deepcopy(_B81_BUILD(cfg, torso, False))
    drop_groups = {"lumbar_cross_tube", "lumbar_gusset", "hip_bracket", "hip_ties"}
    m["members"] = [mm for mm in m["members"] if mm["group"] not in drop_groups and mm["id"] != "ti_mount"]
    m["links"] = [ln for ln in m["links"] if not ln["id"].startswith(("lb_", "lc_", "plug_", "tie_"))]
    g = geom(cfg)
    t, x_w, y_f, yl = g["t"], g["x_w"], g["y_f"], g["yline"]
    P = pan_material(cfg)
    mat = P["beam_mat"]
    nodes = m["nodes"]
    for n in [n for n in nodes if n.startswith(("HM", "PO", "TPL", "TPR", "TRL", "TRR", "GL", "GR")) or
              (n[0] == "R" and len(n) > 1 and n[1].isdigit())]:
        del nodes[n]
    # ---- face (x-z plane at y_f)
    xs = (-x_w,) + FACE_X + (x_w,)
    fz = FACE_ZROWS
    fid = {}
    for i, x in enumerate(xs):
        for j, z in enumerate(fz):
            nid = "HM" if (x == 0.0 and z == 120.0) else f"F{i}_{j}"
            nodes[nid] = [float(x), y_f, float(z)]
            fid[i, j] = nid

    def edge(j, w):
        if j == 0 and cfg["flange_bot"] > 0:
            return _flanged_edge(t, cfg["flange_bot"])(w)
        if j == len(fz) - 1 and cfg["flange_top"] > 0:
            return _flanged_edge(t, cfg["flange_top"])(w)
        return None
    _plate(m, "PF", lambda i, j: fid[i, j], xs, fz, (1, 0, 0), (0, 0, 1), t, mat, "pan_face", P["G"], P["E"], edge)
    # ---- walls (y-z plane at +/- x_w): columns y_f, mid, stay axis; rows WALL_ZROWS (corner nodes shared with the face)
    bolts = []
    for tag, sx in (("L", -1.0), ("R", 1.0)):
        i_edge = 0 if sx < 0 else len(xs) - 1
        wid = {}
        for j, z in enumerate(WALL_ZROWS):
            jf = fz.index(z)
            ys = (y_f, (y_f + yl(z)) / 2, yl(z))
            for i, y in enumerate(ys):
                if i == 0:
                    wid[i, j] = fid[i_edge, jf]
                    continue
                if i == 2 and z > WALL_STAY_TOP:
                    continue
                nid = f"W{tag}{i}_{j}"
                nodes[nid] = [sx * x_w, float(y), float(z)]
                wid[i, j] = nid
        ys120 = (y_f, (y_f + yl(120.0)) / 2, yl(120.0))
        jtop = WALL_ZROWS.index(WALL_STAY_TOP)
        # beside the stay the wall stops at z 170 (IM1 loop round the stay above); its front two thirds run to z 190
        _plate(m, f"PW{tag}", lambda i, j, w=wid: w[i, j], ys120, WALL_ZROWS[:jtop + 1], (0, 1, 0), (0, 0, 1),
               t, mat, "pan_wall", P["G"], P["E"])
        _plate(m, f"PX{tag}", lambda i, j, w=wid: w[i, j + jtop], ys120[:2], WALL_ZROWS[jtop:], (0, 1, 0), (0, 0, 1),
               t, mat, "pan_wall", P["G"], P["E"])
        # lateral bolts: stiff arm wall node -> node on the stay axis, link to the stay node
        for z in cfg["pan_bolt_z"]:
            j = WALL_ZROWS.index(z)
            sn = _split_stay(m, tag, z)
            pb = f"PB{tag}{z:g}"
            nodes[pb] = list(nodes[sn])
            m["members"].append({"id": f"arm_{tag}{z:g}", "nodes": [wid[2, j], pb],
                                 "section": generic(500.0, 1.0e5, 1.0e5, 1.0e5, 12.0, 12.0), "material": "ti_6al_4v",
                                 "group": "pan_bolt_arm", "ref": [0.0, 0.0, 1.0]})
            bolts.append({"id": f"pb_{tag}{z:g}", "nodes": [sn, pb], "k": pan_bolt_link_k(cfg), "kind": "pan_bolt",
                          "tube": cfg["stay"]})
    # ---- lumbar strut(s): 3/4 x .035 spacer tube between the walls on an M5 A2 threaded rod through both stays (the
    #      rod replaces the two pan bolts of that row). Without it the stays move in x / yaw against the pan only through
    #      the walls' out-of-plane bending: global buckling margin 0.99 (side-hill) vs 1.52 with one strut at z 155.
    for z in cfg["strut_z"]:
        j = WALL_ZROWS.index(z)
        m["members"].append({"id": f"strut_{z:g}", "nodes": [f"WL2_{j}", f"WR2_{j}"], "section": BQ.stock_sec("t750_035"),
                             "material": "alu_6061_t6", "group": "pan_strut", "ref": [0.0, 0.0, 1.0]})
    # ---- Ti mount + base spider (ASSUMPTION MOUNT-SPIDER: D50 Ti base + spine web rigid within r 25)
    nodes["HP"] = [0.0, g["pin_y"], 120.0]
    m["members"].append({"id": "ti_mount", "nodes": ["HM", "HP"], "section": tube_round(14.0, 6.9),
                         "material": "ti_6al_4v", "group": "hip_pivot", "ref": [1.0, 0.0, 0.0]})
    i0 = xs.index(0.0)
    for (di, dj) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        j0 = fz.index(120.0)
        m["members"].append({"id": f"spider_{di}{dj}", "nodes": ["HM", fid[i0 + di, j0 + dj]],
                             "section": generic(150.0, 2.0e4, 2.0e4, 2.0e4, 25.0, 25.0), "material": "ti_6al_4v",
                             "group": "mount_spider", "ref": [0.0, 1.0, 0.0] if di else [1.0, 0.0, 0.0]})
    # ---- spine channel behind the face at x 0, bottom to top flange (shares the face column nodes: composite)
    ss = spine_sec(cfg)
    for j in range(len(fz) - 1):
        m["members"].append({"id": f"spine_{j}", "nodes": [fid[i0, j], fid[i0, j + 1]], "section": ss, "material": mat,
                             "group": "pan_spine", "ref": [1.0, 0.0, 0.0]})
    # ---- lumbar pad seats on the face (belt B pad_seat rails at |x| 35-90): 6 face nodes
    m["groups"]["lumbar_pad"] = [fid[xs.index(sx_ * 60.0), fz.index(z)] for sx_ in (-1, 1) for z in (95.0, 120.0, 145.0)]
    if rigid:
        for b in bolts:
            b["k"] = [1e7] * 3 + [1e11] * 3
    m["links"] += bolts
    # prune orphans
    used = {n for mm in m["members"] for n in mm["nodes"]} | {n for ln in m["links"] for n in ln["nodes"]}
    for n in [n for n in nodes if n not in used]:
        del nodes[n]
    for k, v in list(m["groups"].items()):
        m["groups"][k] = [n for n in v if n in nodes]
    m["d83"] = {"cfg": cfg, "bolts": [b["id"] for b in bolts], "rigid": rigid, "face_ids": {f"{i},{j}": v for (i, j), v in fid.items()}}
    m.pop("b81", None)
    return m


def _role(group: str):
    if group == "pan_face":
        return "pan face (grillage strips)"
    if group == "pan_wall":
        return "pan side walls (grillage strips)"
    if group == "pan_spine":
        return "pan mount spine (channel)"
    if group == "pan_strut":
        return "lumbar strut (3/4 x .035 on M5 rod)"
    return _B81_ROLE(group)


def stations(cfg: dict) -> list[dict]:
    """Hole stations: the pan bolts (stay z 85 / 155 along x, on the neutral axis of fore-aft bending), the z 60 hinge
    pin and the pawl-housing holes (from BL-081)."""
    out = [s for s in _B81_STATIONS(cfg) if "z60" in s["name"] or "upper bar" in s["name"]]
    for tag in "LR":
        for z in cfg["pan_bolt_z"]:
            out.append({"name": f"stay z{z:g} pan bolt {tag} (along x)", "node": f"S{tag}{z:g}", "group": "stay",
                        "axis": "x", "tube": cfg.get("stay_hole_tube", cfg["stay"]), "link": f"pb_{tag}{z:g}",
                        "washer": True})
    return out


@contextlib.contextmanager
def _as_b81(builder=build, stations_fn=stations, role=_role):
    """Swap the D83 builder / stations / roles into bl081_concept_b for the duration of a call, so its global
    evaluation and bl081_local's rows run unchanged on D (no copy of the BL-081 machinery)."""
    saved = (BQ.build, BQ.stations, BQ._role)
    BQ.build, BQ.stations, BQ._role = builder, stations_fn, role
    try:
        yield
    finally:
        BQ.build, BQ.stations, BQ._role = saved


def evaluate_global(cfg=None, torsos=BQ.TORSOS, rigid=False, log=print) -> dict:
    cfg = cfg_d(**(cfg or {}))
    with _as_b81():
        g = BQ.evaluate_global(cfg, torsos=torsos, rigid=rigid, log=log)
    # pan members' end forces (hand checks): from the stored members? evaluate_global keeps only gusset / bracket
    return g


def evaluate_pan_forces(cfg, torsos=BQ.TORSOS) -> dict:
    """Pan wall / face strip end forces (factored and walk), the hip pin reactions, per case (for pan_rows)."""
    from huntkit.fea.load_standard import ls1_envelope
    cfg = cfg_d(**(cfg or {}))
    env = ls1_envelope()
    out = {"wall": [], "face": [], "spine": [], "hp": []}
    for t in torsos:
        m = build(cfg, t)
        for var, cases in env.items():
            for case in cases:
                if case.name == "tall_load_posts":
                    continue
                r = case.run(m)
                req = float(r.meta["required_sf"])
                key = f"{case.name}|{var}|{t:g}"
                walk = case.name == "static_carry"
                for mm in r.members:
                    if mm["group"] in ("pan_wall", "pan_face", "pan_spine"):
                        rec = {"id": mm["id"], "case": key, "sf": float(mm["sf"]), "req": req,
                               "maxf": (np.asarray(mm["max_abs_forces"]) * req).tolist()}
                        if walk:
                            rec["walk"] = (np.asarray(mm["max_abs_forces"]) * BQ.G_WALK).tolist()
                        out[{"pan_wall": "wall", "pan_face": "face", "pan_spine": "spine"}[mm["group"]]].append(rec)
    return out


# ----------------------------------------------------------------------------- local rows (pan)
def pan_rows(glob: dict, pf: dict, cfg: dict) -> list[dict]:
    """Hand checks of the pan that the grillage does not resolve: plate stress at the bolt holes (Kt), bolt bearing
    in the wall and the stay, bolt shear, the Ti mount screws (all 8 BL-055 positions now land on the face), the face
    + spine web under the mount tipping couple, the face under the lumbar push on the pin (H-PIN bound, belt pad seat
    absent), the bend radii, and the crush sleeves."""
    from huntkit.gendesign import h1_closeout as HC
    from huntkit.gendesign import hipbelt_structure as HS
    from huntkit.gendesign import hip_mount as HMNT
    cfg = cfg_d(**cfg)
    P = pan_material(cfg)
    g = geom(cfg)
    t = g["t"]
    rows = []
    fa = P["fat"]
    st = BQ.STOCK[cfg["stay"]]
    R_m = st["od"] / 2 - st["t"] / 2
    # 1 bolt forces (links, factored and walk)
    pb = [k for k in glob["links"] if k.startswith("pb_") and "|" not in k]
    worst = max(pb, key=lambda k: glob["links"][k]["F"])
    F = glob["links"][worst]["F"]
    vec = np.asarray(glob["links"][worst]["vec"], float)
    Fs = float(np.hypot(vec[1], vec[2]))        # shear in the wall plane (y, z)
    Mt = max(glob["links"][k + "|M"]["M"] for k in pb)
    Fw = max(float(np.hypot(*np.asarray(r["links"][k], float)[1:3])) for r in glob["walk"]["_links"] for k in pb)
    brg = Fs / (BQ.HOLE_D * t)
    e_d = cfg["wall_aft"] / BQ.HOLE_D
    brg_allow = P["brg"] * min(1.0, 0.5 + 0.25 * e_d)       # e/D 2 -> 1.0; shorter edge scaled (AA practice)
    rows.append({"item": "P", "row": f"pan wall: M5 bolt bearing in the {P['label']} {cfg['pan_t']} wall", "kind": "joint",
                 "value": brg, "allow": brg_allow, "margin": brg_allow / brg,
                 "basis": f"{worst} {Fs:.0f} N in the wall plane (factored, {glob['links'][worst]['case']}), e/D {e_d:.1f}"})
    tau = Fs / BQ.M5_MINOR_A
    rows.append({"item": "P", "row": "pan bolts M5 A2-70: single shear at the wall", "kind": "joint", "value": tau,
                 "allow": 0.6 * BQ.A2_PROOF, "margin": 0.6 * BQ.A2_PROOF / tau,
                 "basis": "wall-plane force on the minor-diameter area (one shear plane), 0.6 x 450 proof"})
    ax = abs(vec[0])
    cap = BQ.A2_PROOF * BQ.M5_AS - 2600.0
    rows.append({"item": "P", "row": "pan bolts: tension (wall pulled off the stay)", "kind": "joint", "value": ax,
                 "allow": cap, "margin": cap / max(ax, 1e-9), "basis": "proof x As - preload 2.6 kN"})
    # wall net section at the bolt holes (in-plane), Heywood Kt, fatigue on the walk forces
    W = 2 * cfg["wall_aft"]
    kt_pin = 3.0      # ASSUMPTION KT-PIN: pin-loaded hole, Kt on the net section P / ((W - d) t) (Peterson pin-joint charts, e/W 0.5)
    s_hole_w = Fw / ((W - BQ.HOLE_D) * t) * kt_pin
    rows.append({"item": "P", "row": "pan wall: fatigue at the bolt holes (pin-loaded, walk)", "kind": "fatigue",
                 "value": s_hole_w, "allow": fa, "margin": fa / s_hole_w,
                 "basis": f"walk {Fw:.0f} N on the net ligament (W {W:.0f} - d) t x Kt 3 (ASSUMPTION KT-PIN); "
                          f"{P['label']} R0 1e5 {fa:.0f} MPa"})
    # 2 grillage strips (beam): in-plane + out-of-plane, factored / walk, with Kt 2 at bends (no holes within 1/2 die)
    for grp, lab in (("wall", "side walls"), ("face", "face (with return flanges)"), ("spine", "mount spine channel")):
        recs = pf[grp]
        wm = min(recs, key=lambda r: r["sf"] / r["req"])
        rows.append({"item": "P", "row": f"pan {lab}: plate strength (grillage, all cases)", "kind": "strength",
                     "value": P["fy"] / wm["sf"], "allow": P["fy"], "margin": wm["sf"] / wm["req"],
                     "basis": f"{wm['id']} {wm['case']}, {P['label']} Fy {P['fy']:.0f}"})
        wk = [r for r in recs if "walk" in r]
        sm = max(P["fy"] / r["sf"] * BQ.G_WALK for r in wk) if wk else 0.0      # 1 g von Mises x 1.6 g
        kf = 2.0
        rows.append({"item": "P", "row": f"pan {lab}: fatigue (walk, Kt 2 at bends / cut edges)", "kind": "fatigue",
                     "value": sm * kf, "allow": fa, "margin": fa / max(sm * kf, 1e-9),
                     "basis": f"static carry x 1.6 g von Mises of the worst strip x Kt 2; R0 1e5 {fa:.0f}"})
    # 3 Ti mount screws (all 8 BL-055 positions on the face + spine), tipping
    ls = HS.load_sets()
    H_c2, H_walk = ls["C2"].H, ls["walk"].H
    hp = glob["hip_pin"]
    Vf = max(abs(r["F"][2]) for r in hp)
    Vw = max(abs(r["walk"][2]) for r in hp if r["walk"] is not None)
    pat = {"boss_d": 50.0, "positions_xz": [list(p) for p in HMNT.pattern()["positions_xz"]]}
    tip_s = HC.tip_tension(pat, Vf, H_c2)
    tip_w = HC.tip_tension(pat, Vw, H_walk)
    rows.append({"item": "P", "row": "Ti mount on the pan: 8 x M5 A2 tension (tipping)", "kind": "joint",
                 "value": tip_s["T_max_n"], "allow": cap, "margin": cap / tip_s["T_max_n"],
                 "basis": f"h1_closeout.tip_tension, 8 positions, V {Vf:.0f} + H {H_c2:.0f} N (H-PIN)"})
    # face + spine web under the mount couple: two plates (no composite action), M shared by t^3, strip b = 62 mm per
    # side of the D50 base (base D + 2 x 12 less 2 holes), M_net / 2 per side (as BL-081's angle-leg row)
    td = SHEET_T[cfg["spine_t"]]
    b = 50.0 + 24.0 - 2 * 5.8
    for lab, M_net, allow, kfm in (("strength", tip_s["M_net_nmm"], None, 1.0), ("fatigue", tip_w["M_net_nmm"], None, 2.0)):
        Mside = M_net / 2
        s_face = 6 * Mside * t / (b * (t ** 3 + td ** 3)) * kfm
        s_dbl = 6 * Mside * td / (b * (t ** 3 + td ** 3)) * kfm
        if lab == "strength":
            m_ = min(P["fy"] / s_face, P["fy"] / s_dbl)
            rows.append({"item": "P", "row": f"face {cfg['pan_t']} + spine web {cfg['spine_t']} under the mount tipping couple",
                         "kind": "strength", "value": max(s_face, s_dbl), "allow": P["fy"], "margin": m_,
                         "basis": f"M_net {M_net / 1e3:.1f} N m (tip_tension), half per side, strip {b:.0f} mm, plates share by t^3: "
                                  f"face {s_face:.0f} / spine web {s_dbl:.0f} MPa"})
        else:
            m_ = min(P["fat"] / s_face, P["fat"] / s_dbl)
            rows.append({"item": "P", "row": "face + spine web: fatigue at the mount holes (walk, Kt 2)", "kind": "fatigue",
                         "value": max(s_face, s_dbl), "allow": P["fat"], "margin": m_,
                         "basis": f"walk M_net {M_net / 1e3:.1f} N m, Kt 2 x: face {s_face:.0f} / spine web {s_dbl:.0f} MPa"})
    # face under the lumbar push on the pin (H-PIN: the pad not seated), channel section fixed at the walls (PL/8)
    hf, ft, fb = cfg["face_z"][1] - cfg["face_z"][0], cfg["flange_top"], cfg["flange_bot"]
    A_w, A_t, A_b = hf * t, ft * t, fb * t
    yc = (A_t * ft / 2 + A_b * fb / 2) / (A_w + A_t + A_b)
    I = hf * t ** 3 / 12 + A_w * yc ** 2 + t * ft ** 3 / 12 + A_t * (ft / 2 - yc) ** 2 + t * fb ** 3 / 12 + A_b * (fb / 2 - yc) ** 2
    c = max(max(ft, fb) - yc, yc + t / 2)
    L = 2 * g["x_w"]
    for lab, H, kfm, allow in (("strength", H_c2, 1.0, P["fy"]), ("fatigue", H_walk, 2.0, fa)):
        s = H * L / 8 * c / I * kfm
        rows.append({"item": "P", "row": f"face as a channel under the lumbar push on the pin (H-PIN): {lab}",
                     "kind": lab, "value": s, "allow": allow, "margin": allow / s,
                     "basis": f"H {H:.0f} N at mid-span, fixed at the walls (P L / 8), L {L:.0f}, channel I {I:.0f} mm4"
                              f" (flanges {ft:g} / {fb:g}){', Kt 2 at the mount holes' if kfm > 1 else ''}"})
    # bend radius (5052 formable at the SCS fixed radius; 6061 not offered)
    rows.append({"item": "P", "row": "pan bends: material can be formed at SendCutSend", "kind": "info",
                 "value": None, "allow": None, "margin": None,
                 "basis": SCS["no_6061_bend"] if cfg["pan_mat"] == "6061" else "5052-H32 is SendCutSend's bendable aluminium; "
                          "radius / K fixed by SCS per thickness (bending page)"})
    return rows


def lumbar_crush_rows(glob, cfg):
    rows = BL.crush_rows(glob, cfg)
    for r in rows:
        r["item"] = "P"
    return rows


# ----------------------------------------------------------------------------- hose-band tees (lever) on clamp_rows
def band_cfg(cfg: dict, n_upper: int | None = None) -> dict:
    """Clamp rows with hose bands: total normal force 2 pi n T (same form as 2 pi Fb of the bolted backers), so
    Fb_equiv = n x T; retention 0.8 (ASSUMPTION BAND)."""
    n = cfg.get("band_n", 2)
    nu = n if n_upper is None else n_upper
    Tu = cfg.get("band_T_upper", BAND["T_n"])
    return {**cfg, "clamp_preload_n": n * BAND["T_n"], "clamp_preload_upper_n": nu * Tu,
            "preload_retention": BAND["retention"]}


def clamp_rows(glob, cfg):
    """BL-081 clamp rows; with hose-band tees the backer / half-shell-line-load rows are replaced by a band row."""
    if cfg.get("tees") != "bands":
        return BL.clamp_rows(glob, cfg)
    c = band_cfg(cfg)
    rows = [r for r in BL.clamp_rows(glob, c) if "backer" not in r["row"] and "line load" not in r["row"]]
    T = BAND["T_n"]
    brk = 2.0 * T            # ASSUMPTION BAND-BREAK: worm-drive bands strip the screw before the band breaks at about 2 x install tension
    rows.append({"item": "5", "row": "hose band (9 mm W4): install tension vs band break", "kind": "joint", "value": T,
                 "allow": brk, "margin": brk / T, "basis": BAND["src"] + "; ASSUMPTION BAND-BREAK 2 x T"})
    for r in rows:
        r["basis"] = r["basis"].replace("2 x M5 A2", f"{cfg.get('band_n', 2)} hose bands")
    rows.append({"item": "5", "row": "upper-tee bands set to 3.3 N m (1000 N each, ASSUMPTION BAND torque-tension)", "kind": "info",
                 "value": None, "allow": None, "margin": None,
                 "basis": "keeps the stay wall under the upper tee at B81's 2000 N preload; full 4.0 N m (2424 N) drops the "
                          "wall fatigue row below 1 (quick check)"})
    return rows
