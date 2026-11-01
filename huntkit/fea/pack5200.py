"""FEA model of the Pack 5200 frame as defined by the pack-designer
(designs/pack_5200/geometry.yaml + DESIGN.md), for sizing. Same FCS as huntkit.fea.frames
(x lateral +right, y aft, z up, origin between the stay feet).

Topology
- segmented stays: lower foot (+-135, 0, 0) -> lumbar elbow (+-115, -25, 130); upper elbow ->
  stay top (+-115, -10, 530). Bonded elbow sleeves, bonded foot boots (shelf pivots z 25).
- lumbar plate (cfrp_plate_pm45, z 50-190) bonded across both stays: modelled as a grillage of
  flat-bar strips (bending/twisting) plus equivalent X-diagonals per cell for in-plane shear.
  The Ti hipbelt pivot (0, -48.1, 120) is a boss on the plate centre.
- mid bar z 330 (shelf-strap + bag-mid anchors at its nodes), upper bar z 520.
- telescoping crown: two 430 mm legs coaxial inside the upper stays, on UHMWPE bushings at the
  stay top (z 530) and z 380 (radial springs, free to slide), held vertically by a clamp collar /
  webbing lock at the stay top (axial spring). Crown top bar with lifter + bag-top anchors at
  x = +-70, centre spine (cfrp_plate_quasi_iso) hanging 300 mm from the top bar carrying the yoke.
  No pin holes (owner decision). Optional extension posts (+220 mm) and post bar.
Crown settings (crown top z, yoke z) come from geometry.yaml ``frame.crown_settings``.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

from .composite import DEFAULT_KNOCKDOWN
from .materials_bridge import REPO_ROOT, get_material, yield_of
from .sections import Section, flat_bar, from_spec, generic, tube_round

GEOMETRY = REPO_ROOT / "designs" / "pack_5200" / "geometry.yaml"

P5200_DEFAULTS = {
    "topology": "pack5200_crown",
    "name": "pack5200_frame",
    "geometry": str(GEOMETRY),
    "torso_in": 19.0,
    "haul_mode": False,
    "extension_posts": False,
    "stay_section": None,          # lower and upper stays
    "leg_section": None,           # crown legs (must fit inside the upper stay bore)
    "bar_section": None,           # mid bar, upper bar, crown top bar
    "post_section": None,          # extension posts + post bar (default: leg section)
    "lumbar_plate_t": 2.0,
    "lumbar_plate_material": "cfrp_plate_pm45",
    "spine_w": 30.0,               # ASSUMPTION: spine plate width
    "spine_t": 3.0,
    "spine_len": 300.0,
    "spine_material": "cfrp_plate_quasi_iso",
    "bushing_k_n_mm": 2.0e4,       # ASSUMPTION: UHMWPE bushing radial stiffness
    "bushing_len_mm": 20.0,
    "bushing_wall_mm": 1.0,
    "bushing_low_z": 380.0,
    "pawl_z": 520.0,               # rack/pawl lock on the upper bar centre (geometry.yaml crown_retention)
    "pawl_k_n_mm": 5.0e4,          # ASSUMPTION: pawl + rack tooth axial stiffness (carries all; pulley ignored)
    "collar_len_mm": 20.0,
    "collar_mu": 0.20,             # ASSUMPTION: carbon/carbon with carbon assembly (grip) paste
    "collar_slip_sf": 2.0,
    "post_len": 220.0,
    "shelf_depth_mm": 260.0,       # geometry.yaml load_shelf.floor_d_y
    "bag_weights": {"shelf": 0.35, "low": 0.25, "mid": 0.25, "top": 0.15},   # ASSUMPTION
    "springs": {"hipbelt": (20.0, 0.0, 40.0), "lumbar_pad": (0.0, 30.0, 0.0),
                "shoulder": (4.0, 8.0, 10.0), "lifter": (0.0, 6.0, 3.0)},
    "joint": {},
    "hardware": {},
}

PLATE_Z = [50.0, 90.0, 120.0, 155.0, 190.0]
FRACS = [0.0, 0.25, 0.5, 0.75, 1.0]


def _sec(spec, default=None):
    if spec is None:
        return default
    return spec if isinstance(spec, Section) else from_spec(spec)


def load_geometry(path=None) -> dict:
    import yaml
    return yaml.safe_load(Path(path or GEOMETRY).read_text())


def crown_setting(geom: dict, torso_in: float) -> dict:
    cs = geom["frame"]["crown_settings"]
    return min(cs, key=lambda c: abs(c["torso_in"] - torso_in))


def _stay_pts(geom):
    t = geom["frame"]["members_topology"]
    lo, up = t["stay_lower_R"], t["stay_upper_R"]
    return np.array(lo["from"], float), np.array(lo["to"], float), np.array(up["to"], float)


def _on_segment(a, b, z):
    s = (z - a[2]) / (b[2] - a[2])
    return a + s * (b - a)


def build(params: dict | None = None) -> dict:
    p = copy.deepcopy(P5200_DEFAULTS)
    p.update(params or {})
    geom = load_geometry(p["geometry"])
    fr = geom["frame"]
    cs = crown_setting(geom, p["torso_in"])
    foot, elbow, top = _stay_pts(geom)
    stay = _sec(p["stay_section"], tube_round(22.0, 1.2))
    leg = _sec(p["leg_section"], tube_round(18.0, 1.2))
    bar = _sec(p["bar_section"], stay)
    post = _sec(p["post_section"], leg)
    warnings = []
    if "od" in stay.dims and "od" in leg.dims:
        bore = stay.dims["od"] - 2 * stay.dims["t"]
        gap = (bore - leg.dims["od"]) / 2
        if gap < 0.5:
            warnings.append(f"crown leg OD {leg.dims['od']:g} does not fit the stay bore {bore:.2f} with a "
                            f"bushing (radial gap {gap:.2f} mm < 0.5)")
        p["bushing_wall_mm"] = gap
    pl_mat = get_material(p["lumbar_plate_material"])
    sp_mat = get_material(p["spine_material"])

    def plate_mat(m):
        a, _ = yield_of(m)
        return {"id": m.id, "youngs_modulus_mpa": m.require("youngs_modulus_mpa"),
                "shear_modulus_mpa": m.get("shear_modulus_mpa"), "poisson": m.get("poisson", 0.3),
                "design_allowable_mpa": a, "density_kg_m3": 0.0}     # mass counted in hardware_mass

    nodes, members, groups, joints, links = {}, [], {}, [], []
    stay_ref, bar_ref = [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]

    # ------------------------------------------------------------- stays
    z_lo = sorted({0.0, 25.0, 50.0, 60.0, 80.0, 90.0, 120.0, elbow[2]})
    z_up = sorted({elbow[2], 155.0, 190.0, 250.0, 290.0, 330.0, p["bushing_low_z"], 420.0, 470.0, 520.0, top[2]})
    for side, tag in ((-1, "L"), (1, "R")):
        mir = np.array([side, 1.0, 1.0])
        chain = []
        for z in z_lo:
            nodes[f"S{tag}{z:g}"] = list(map(float, _on_segment(foot, elbow, z) * mir))
            chain.append(f"S{tag}{z:g}")
        for z in z_up[1:]:
            nodes[f"S{tag}{z:g}"] = list(map(float, _on_segment(elbow, top, z) * mir))
            chain.append(f"S{tag}{z:g}")
        for a, b in zip(chain[:-1], chain[1:]):
            grp = "stay_lower" if nodes[b][2] <= elbow[2] + 1e-6 else "stay_upper"
            members.append({"id": f"{a}-{b}", "nodes": [a, b], "section": stay, "material": None,
                            "group": f"{grp}_{tag}", "ref": stay_ref})

    def sid(tag, z):
        return f"S{tag}{z:g}"

    def mid(tag, z):   # stay member id that ends at z (below) / starts at z (above)
        zs = z_lo + z_up[1:]
        i = zs.index(z)
        return f"{sid(tag, zs[i - 1])}-{sid(tag, z)}", (f"{sid(tag, z)}-{sid(tag, zs[i + 1])}" if i + 1 < len(zs) else None)

    # ------------------------------------------------------------- lumbar plate (grillage)
    t = p["lumbar_plate_t"]
    pm = plate_mat(pl_mat)
    grid = {}
    for i, z in enumerate(PLATE_Z):
        L, R = np.array(nodes[sid("L", z)]), np.array(nodes[sid("R", z)])
        for j, f in enumerate(FRACS):
            if j == 0:
                grid[i, j] = sid("L", z)
            elif j == len(FRACS) - 1:
                grid[i, j] = sid("R", z)
            else:
                nid = f"P{i}{j}"
                nodes[nid] = list(map(float, L + f * (R - L)))
                grid[i, j] = nid
    nz, nx = len(PLATE_Z), len(FRACS)
    dz = np.diff(PLATE_Z)
    for i in range(nz):
        wz = ((dz[i - 1] if i > 0 else 0) + (dz[i] if i < nz - 1 else 0)) / 2
        for j in range(nx - 1):
            members.append({"id": f"plh{i}{j}", "nodes": [grid[i, j], grid[i, j + 1]],
                            "section": flat_bar(wz, t), "material": pm, "group": "lumbar_plate",
                            "ref": [0.0, 0.0, 1.0]})
    for j in range(nx):
        a_ = np.linalg.norm(np.subtract(nodes[grid[2, 1]], nodes[grid[2, 0]]))
        wx = a_ / 2 if j in (0, nx - 1) else a_
        for i in range(nz - 1):
            members.append({"id": f"plv{i}{j}", "nodes": [grid[i, j], grid[i + 1, j]],
                            "section": flat_bar(wx, t), "material": pm, "group": "lumbar_plate",
                            "ref": [1.0, 0.0, 0.0]})
    G_pl = float(pl_mat.get("shear_modulus_mpa"))
    E_pl = float(pl_mat.require("youngs_modulus_mpa"))
    cells = []
    for i in range(nz - 1):
        for j in range(nx - 1):
            p00, p01 = np.array(nodes[grid[i, j]]), np.array(nodes[grid[i, j + 1]])
            p10, p11 = np.array(nodes[grid[i + 1, j]]), np.array(nodes[grid[i + 1, j + 1]])
            a_ = (np.linalg.norm(p01 - p00) + np.linalg.norm(p11 - p10)) / 2
            b_ = PLATE_Z[i + 1] - PLATE_Z[i]
            Ld = np.hypot(a_, b_)
            c = a_ / Ld
            Ad = G_pl * a_ * t * Ld / (2 * E_pl * b_ * c * c)
            dm = {"youngs_modulus_mpa": E_pl, "shear_modulus_mpa": G_pl, "design_allowable_mpa": 1e9,
                  "density_kg_m3": 0.0, "id": "plate_shear_equivalent"}
            ids = []
            for k, (n1, n2) in enumerate(((grid[i, j], grid[i + 1, j + 1]), (grid[i, j + 1], grid[i + 1, j]))):
                did = f"pld{i}{j}{k}"
                members.append({"id": did, "nodes": [n1, n2], "section": generic(Ad, 1.0, 1.0, 1.0),
                                "material": dm, "type": "truss", "group": "lumbar_plate_shear"})
                ids.append(did)
            cells.append({"cell": (i, j), "a": a_, "b": b_, "cos": c, "diags": ids})

    # Ti hipbelt pivot boss
    hp = fr["hard_points"]["hipbelt_pivot"]
    nodes["HP"] = list(map(float, hp))
    members.append({"id": "pivot_boss", "nodes": [grid[2, 2], "HP"], "section": tube_round(12.0, 3.0),
                    "material": "ti_6al_4v", "group": "hip_pivot", "ref": [1.0, 0.0, 0.0]})

    # ------------------------------------------------------------- bars
    def crossbar(prefix, nl, nr, xs, group, sec, ref=bar_ref):
        L, R = np.array(nodes[nl]), np.array(nodes[nr])
        chain = [nl]
        for k, x in enumerate(xs):
            f = (x - L[0]) / (R[0] - L[0])
            nid = f"{prefix}{k}"
            nodes[nid] = list(map(float, L + f * (R - L)))
            chain.append(nid)
        chain.append(nr)
        ids = []
        for a, b in zip(chain[:-1], chain[1:]):
            members.append({"id": f"{a}-{b}", "nodes": [a, b], "section": sec, "material": None,
                            "group": group, "ref": ref})
            ids.append(f"{a}-{b}")
        return chain, ids

    _, mb_ids = crossbar("MB", sid("L", 330.0), sid("R", 330.0), [-57.5, 0.0, 57.5], "mid_bar", bar)
    _, ub_ids = crossbar("UB", sid("L", 520.0), sid("R", 520.0), [-57.5, 0.0, 57.5], "upper_bar", bar)

    # ------------------------------------------------------------- crown
    crown = fr.get("crown") or fr["members_topology"]["crown"]
    u = np.array(crown["axis_unit_vector_yz"], float)
    u = np.array([0.0, u[0], u[1]])
    zt = float(cs["crown_top_z"])
    leg_len = float(crown["leg_length_along_axis"])
    for side, tag in ((-1, "L"), (1, "R")):
        topL = np.array(nodes[sid(tag, top[2])])
        s_top = (zt - top[2]) / u[2]
        ptop = topL + s_top * u
        pbot = ptop - leg_len * u
        if pbot[2] > p["bushing_low_z"] - 1:
            warnings.append(f"crown leg bottom z={pbot[2]:.0f} is above the lower bushing z={p['bushing_low_z']:g}")
        names = [f"C{tag}bot"]
        nodes[f"C{tag}bot"] = list(map(float, pbot))
        nodes[f"C{tag}380"] = list(map(float, nodes[sid(tag, p["bushing_low_z"])]))
        nodes[f"C{tag}530"] = list(map(float, nodes[sid(tag, top[2])]))
        nodes[f"C{tag}mid"] = list(map(float, (topL + ptop) / 2))
        nodes[f"C{tag}top"] = list(map(float, ptop))
        names = [f"C{tag}bot", f"C{tag}380", f"C{tag}530", f"C{tag}mid", f"C{tag}top"]
        if pbot[2] > p["bushing_low_z"] - 3:      # leg ends at the bushing: drop the separate bottom node
            names.remove(f"C{tag}bot")
        for a, b in zip(names[:-1], names[1:]):
            members.append({"id": f"{a}-{b}", "nodes": [a, b], "section": leg, "material": None,
                            "group": f"crown_leg_{tag}", "ref": stay_ref})
        links.append({"id": f"bush_low_{tag}", "nodes": [sid(tag, p["bushing_low_z"]), f"C{tag}380"],
                      "k": [p["bushing_k_n_mm"], p["bushing_k_n_mm"], 0, 0, 0, 0]})
        links.append({"id": f"bush_top_{tag}", "nodes": [sid(tag, top[2]), f"C{tag}530"],
                      "k": [p["bushing_k_n_mm"], p["bushing_k_n_mm"], 0, 0, 0, 0]})
    tb_chain, tb_ids = crossbar("TB", "CLtop", "CRtop", [-70.0, 0.0, 70.0], "crown_top_bar", bar)
    # spine (hangs from the top-bar centre), yoke at 150 mm
    spine_sec = flat_bar(p["spine_w"], p["spine_t"])
    spm = plate_mat(sp_mat)
    s_nodes = ["TB1"]
    s_pawl = (nodes["TB1"][2] - p["pawl_z"]) / u[2]
    if not 0 < s_pawl <= p["spine_len"]:
        warnings.append(f"spine does not reach the pawl at z={p['pawl_z']:g} (s={s_pawl:.0f})")
    svals = [75.0, 150.0, 225.0, float(p["spine_len"])]
    sp = round(float(s_pawl), 1)
    svals = sorted([v for v in svals if abs(v - sp) >= 3.0 or v == 150.0] + ([sp] if all(abs(sp - v) >= 3.0 for v in (150.0,)) else []))
    pawl_node = None
    for sv in svals:
        nid = "SP150" if sv == 150.0 else f"SP{sv:g}".replace(".", "p")
        nodes[nid] = list(map(float, np.array(nodes["TB1"]) - sv * u))
        s_nodes.append(nid)
        if abs(sv - sp) < 3.0:
            pawl_node = nid
    if pawl_node:
        links.append({"id": "pawl", "nodes": ["UB1", pawl_node], "k": [0, 0, p["pawl_k_n_mm"], 0, 0, 0]})
    for a, b in zip(s_nodes[:-1], s_nodes[1:]):
        members.append({"id": f"{a}-{b}", "nodes": [a, b], "section": spine_sec, "material": spm,
                        "group": "crown_spine", "ref": [1.0, 0.0, 0.0]})
    # extension posts
    if p["extension_posts"]:
        for tag in ("L", "R"):
            nodes[f"X{tag}"] = list(map(float, np.array(nodes[f"C{tag}top"]) + p["post_len"] * u))
            members.append({"id": f"post_{tag}", "nodes": [f"C{tag}top", f"X{tag}"], "section": post,
                            "material": None, "group": "ext_post", "ref": stay_ref, "nseg": 3})
        _, xb_ids = crossbar("XB", "XL", "XR", [-70.0, 70.0], "ext_post_bar", post)
        groups["lash_posts"] = ["XB0", "XB1"]
        groups["lifter_posts"] = ["XB0", "XB1"]

    # ------------------------------------------------------------- groups
    groups["hipbelt"] = ["HP"]
    groups["lumbar_pad"] = [grid[i, j] for i in (1, 2, 3) for j in (1, 2, 3)]
    groups["shoulder"] = ["SP150"]
    groups["lifter"] = ["TB0", "TB2"]
    groups["shelf_pivot"] = [sid("L", 25.0), sid("R", 25.0)]
    groups["shelf_strap"] = [sid("L", 330.0), sid("R", 330.0)]
    groups["lash"] = ["TB0", "TB2"]
    groups["foot_left"] = [sid("L", 0.0)]
    groups["foot_right"] = [sid("R", 0.0)]
    bag_w = []
    if not p["haul_mode"]:
        bw = p["bag_weights"]
        bag = ([sid("L", 25.0), sid("R", 25.0)], [sid("L", 60.0), sid("R", 60.0)],
               [sid("L", 330.0), sid("R", 330.0)], ["TB0", "TB2"])
        groups["bag"] = [n for pair in bag for n in pair]
        for key in ("shelf", "low", "mid", "top"):
            bag_w += [bw[key] / 2] * 2

    # ------------------------------------------------------------- bonded joints
    jp = p["joint"]
    for tag in ("L", "R"):
        lo_last, up_first = mid(tag, elbow[2])
        joints += [
            {"id": f"foot_{tag}", "node": sid(tag, 0.0), "members": [mid(tag, 0.0)[1]], "params": jp},
            {"id": f"elbow_{tag}", "node": sid(tag, elbow[2]), "members": [lo_last, up_first], "params": jp},
            {"id": f"mid_hub_{tag}", "node": sid(tag, 330.0), "members": [mb_ids[0] if tag == "L" else mb_ids[-1]],
             "through": [list(mid(tag, 330.0))], "params": jp},
            {"id": f"upper_hub_{tag}", "node": sid(tag, 520.0), "members": [ub_ids[0] if tag == "L" else ub_ids[-1]],
             "through": [list(mid(tag, 520.0))], "params": jp},
            {"id": f"stay_top_{tag}", "node": sid(tag, top[2]), "members": [mid(tag, top[2])[0]], "params": jp},
            {"id": f"crown_corner_{tag}", "node": f"C{tag}top",
             "members": [f"C{tag}mid-C{tag}top", tb_ids[0] if tag == "L" else tb_ids[-1]], "params": jp},
        ]
        if p["extension_posts"]:
            joints.append({"id": f"post_socket_{tag}", "node": f"C{tag}top", "members": [f"post_{tag}"],
                           "params": jp})

    model = {"name": p["name"], "nodes": nodes, "members": members, "groups": groups, "links": links,
             "joints": joints, "params": p, "warnings": warnings, "settings": {"nseg": 2},
             "springs": p["springs"], "shelf_depth_mm": p["shelf_depth_mm"],
             "plate_cells": cells, "plate_grid": {f"{i},{j}": v for (i, j), v in grid.items()},
             "crown_setting": cs, "topology": "pack5200_crown"}
    if bag_w:
        model["bag_weights"] = bag_w
    model["hardware"] = hardware_mass(model)
    return model


# ============================================================================ mass
HW = {
    "al_density": 2810.0, "ti_density": 4430.0, "cf_density": 1550.0, "uhmw_density": 935.0,
    "pom_density": 1410.0, "adhesive_density": 1150.0, "fillet": 1.5, "socket_extra_mm": 5.0,
    "foot_boot_g": 14.0,          # ASSUMPTION: 7075 boot + shelf-pivot boss + bumper seat (each)
    "pivot_insert_g": 18.0,       # ASSUMPTION: Ti flanged insert + pin, bonded with a glass ply
    "collar_g": 9.0,              # ASSUMPTION: 7075 seatpost-style collar + Ti bolt (each)
    "lock_pulley_g": 12.0,        # ASSUMPTION: webbing pulley + friction lock hardware (total)
    "spine_clamp_g": 6.0,         # ASSUMPTION: spine-to-top-bar clamp
    "web_plate_g": 4.0,           # ASSUMPTION: CF gusset per T / corner hub
}


def _perim(s):
    return np.pi * s.dims["od"] if "od" in s.dims else 2 * (s.dims["w"] + s.dims["h"])


def hardware_mass(model: dict) -> dict:
    from .joints import DEFAULT_JOINT
    p = model["params"]
    h = {**HW, **(p.get("hardware") or {})}
    jp = {**DEFAULT_JOINT, **(p.get("joint") or {})}
    ta = jp.get("adhesive_t_mm") or 0.3
    ov = jp["overlap_mm"]
    ov_t = jp.get("through_overlap_mm") or ov
    ts = jp.get("sleeve_t_mm") or 1.0
    mem = {m["id"]: m for m in model["members"]}
    nodes = model["nodes"]
    items = {}

    def L(m):
        return float(np.linalg.norm(np.subtract(nodes[m["nodes"][1]], nodes[m["nodes"][0]])))

    tubes = {}
    for m in model["members"]:
        s = _sec(m["section"])
        if getattr(s, "composite", False):
            g = s.density_kg_m3 * s.A * 1e-9 * L(m) * 1e3
            key = m["group"].rstrip("_LR").replace("crown_leg", "crown_leg")
            tubes[key] = tubes.get(key, 0.0) + g
    # crown legs: full 430 mm length regardless of the setting
    stay = _sec(mem[next(k for k in mem if mem[k]["group"].startswith("stay_upper"))]["section"])
    legm = [m for m in model["members"] if m["group"].startswith("crown_leg")]
    if legm:
        leg = _sec(legm[0]["section"])
        tubes["crown_leg"] = 2 * leg.density_kg_m3 * leg.A * 1e-9 * 430.0 * 1e3
    for k, v in tubes.items():
        items[f"tubes: {k}"] = v
    # plates
    pl = get_material(p["lumbar_plate_material"])
    items["lumbar plate (250 x 140)"] = 250 * 140 * p["lumbar_plate_t"] * float(pl.get("density_kg_m3", 1550)) * 1e-6
    sp = get_material(p["spine_material"])
    items["crown spine plate"] = p["spine_w"] * p["spine_len"] * p["spine_t"] * float(sp.get("density_kg_m3", 1550)) * 1e-6

    def sleeve_g(sec, length):
        per = _perim(sec) + np.pi * (2 * ta + ts)
        return per * ts * (length + h["socket_extra_mm"]) * h["al_density"] * 1e-6

    def adh_g(sec, length):
        return _perim(sec) * length * ta * h["adhesive_density"] * h["fillet"] * 1e-6

    g_sock, g_adh = 0.0, 0.0
    for j in model["joints"]:
        if j["id"].startswith("foot"):
            g_adh += adh_g(stay, 25.0)
            continue
        for mid_ in j.get("members", []):
            s = _sec(mem[mid_]["section"])
            g_sock += sleeve_g(s, ov)
            g_adh += adh_g(s, ov)
        for _ in j.get("through", []):
            g_sock += sleeve_g(stay, ov_t)
            g_adh += adh_g(stay, ov_t)
        if j["id"].startswith(("mid_hub", "upper_hub", "crown_corner")):
            g_sock += h["web_plate_g"]
    items["7075 sockets/sleeves + gussets"] = g_sock
    items["adhesive (incl. lumbar-plate bond)"] = g_adh + 2 * 140 * 0.5 * stay.dims.get("od", 20) * ta * h["adhesive_density"] * h["fillet"] * 1e-6
    items["foot boots (2)"] = 2 * h["foot_boot_g"]
    items["Ti hipbelt pivot insert"] = h["pivot_insert_g"]
    items["crown collars (2) + lock/pulley"] = 2 * h["collar_g"] + h["lock_pulley_g"]
    if legm:
        leg = _sec(legm[0]["section"])
        bw = p.get("bushing_wall_mm", 1.0)
        items["UHMWPE bushings (4)"] = 4 * np.pi * (leg.dims["od"] + bw) * bw * p["bushing_len_mm"] * h["uhmw_density"] * 1e-6
    items["spine clamp"] = h["spine_clamp_g"]
    total = sum(items.values())
    tubes_g = sum(v for k, v in items.items() if k.startswith("tubes"))
    return {"items": items, "tubes_g": tubes_g, "hubs_g": total - tubes_g, "total_g": total}


# ============================================================================ custom checks
def _member_node_force_global(res, member_id, node_id):
    """Force (3,) exerted BY the member ON the node, global axes."""
    mi = next(i for i, m in enumerate(res.members) if m["id"] == member_id)
    ni = res.node_ids.index(node_id)
    for e in res.members[mi]["elements"]:
        el = res.elements[e]
        R = el.T[:3, :3]
        if el.n1 == ni:
            return R.T @ res.elem_forces[e, 0, :3]
        if el.n2 == ni:
            return R.T @ (-res.elem_forces[e, 1, :3])
    return np.zeros(3)


def crown_checks(res, model: dict, required_sf: float = 2.0) -> list[dict]:
    """Telescoping crown: retention force, bushing bearing, ring crush of stay and leg at the
    bushings, clamp-collar pressure vs. crush limit of the leg."""
    p = model["params"]
    lf = res.meta.get("link_forces", {})
    mem = {m["id"]: m for m in model["members"]}
    leg = _sec(next(m for m in model["members"] if m["group"].startswith("crown_leg"))["section"])
    stay = _sec(next(m for m in model["members"] if m["group"].startswith("stay_upper"))["section"])
    out = []
    ret = float(lf.get("pawl", np.zeros(6))[2])     # + : crown pushed DOWN (compression)? sign below
    out.append({"check": "crown vertical retention force at the pawl", "value": ret, "unit": "N",
                "sf": np.inf, "retention": True})
    uh = get_material("uhmwpe_sheet")
    p_allow = float(uh.require("yield_strength_mpa"))
    Lb = p["bushing_len_mm"]
    for name in ("bush_low_L", "bush_low_R", "bush_top_L", "bush_top_R"):
        f = lf.get(name)
        if f is None:
            continue
        Fr = float(np.hypot(f[0], f[1]))
        pb = Fr / (leg.dims["od"] * Lb)
        out.append({"check": f"{name}: UHMWPE bushing bearing", "value": pb, "unit": "MPa",
                    "allow": p_allow, "sf": p_allow / pb if pb > 0 else np.inf})
        for who, sec in (("stay", stay), ("leg", leg)):
            if not getattr(sec, "composite", False):
                continue
            Rm = sec.dims["od"] / 2 - sec.dims["t"] / 2
            m_hoop = 0.318 * (Fr / Lb) * Rm      # ring under diametral load (conservative: point load)
            fpf = sec.laminate.first_ply_failure((0, -Fr / (2 * Lb), 0), (0, m_hoop, 0))
            out.append({"check": f"{name}: {who} ring crush at bushing", "value": m_hoop, "unit": "N*mm/mm",
                        "sf": fpf["sf"]})
    # clamp collar
    if getattr(leg, "composite", False):
        Rm = leg.dims["od"] / 2 - leg.dims["t"] / 2
        unit = leg.laminate.first_ply_failure((0, -Rm, 0), (0, 0, 0))   # FI per 1 MPa external pressure
        p_crush = 1 / unit["fi"]
        Fz = abs(ret) / 2      # IF seatpost-style collars on both stay tops held the crown instead
        Nc = p["collar_slip_sf"] * Fz / p["collar_mu"]
        pc = Nc / (np.pi * leg.dims["od"] * p["collar_len_mm"])
        out.append({"check": f"seatpost-style collar option: clamp pressure on leg (slip SF "
                             f"{p['collar_slip_sf']:g}, mu {p['collar_mu']:g}, {p['collar_len_mm']:g} mm)",
                    "value": pc, "unit": "MPa", "allow": p_crush, "sf": p_crush / pc if pc > 0 else np.inf,
                    "clamp_force_n": Nc, "info": True})
    return out


def plate_checks(res, model: dict) -> list[dict]:
    """Lumbar plate in-plane shear (from the equivalent diagonals), plate-to-stay bond, and the
    pivot-insert punching shear."""
    from .joints import DEFAULT_JOINT, volkersen_factor
    p = model["params"]
    t = p["lumbar_plate_t"]
    pl = get_material(p["lumbar_plate_material"])
    tau_a = float(pl.get("shear_strength_mpa")) * DEFAULT_KNOCKDOWN["hot_wet"] * DEFAULT_KNOCKDOWN["impact_comp"]
    mf = {m["id"]: m for m in res.members}
    out = []
    worst = 0.0
    for c in model["plate_cells"]:
        F1 = mf[c["diags"][0]]["end_forces"][1][0]
        F2 = mf[c["diags"][1]]["end_forces"][1][0]
        tau = abs(F1 - F2) * c["cos"] / (c["a"] * t)
        worst = max(worst, tau)
    out.append({"check": "lumbar plate in-plane shear", "value": worst, "unit": "MPa", "allow": tau_a,
                "sf": tau_a / worst if worst > 0 else np.inf})
    # plate -> stay bond (per attach node, tributary length)
    stay = _sec(next(m for m in model["members"] if m["group"].startswith("stay_upper"))["section"])
    jp = {**DEFAULT_JOINT, **(p.get("joint") or {})}
    adh = get_material(jp["adhesive"])
    Ga = float(adh.get("shear_modulus_mpa") or jp.get("adhesive_G_mpa", 800.0))
    ta = jp.get("adhesive_t_mm") or adh.get("bondline_thickness_mm") or 0.3
    tau_s = float(adh.get("lap_shear_strength_cfrp_mpa") or adh.require("lap_shear_strength_mpa")) * 0.8
    b = 0.5 * stay.dims.get("od", 20.0)       # ASSUMPTION: saddle/fillet bond width = half the stay OD
    Et1 = E_t = stay.Ex * stay.dims["t"] if getattr(stay, "composite", False) else 7e4
    Et2 = float(pl.require("youngs_modulus_mpa")) * t
    om = np.sqrt(Ga / ta * (1 / Et1 + 1 / Et2))
    grid = model["plate_grid"]
    worst = (0, 0, 0)
    for i, z in enumerate(PLATE_Z):
        trib = ((PLATE_Z[i] - PLATE_Z[i - 1]) if i > 0 else 0) / 2 + ((PLATE_Z[i + 1] - PLATE_Z[i]) if i < len(PLATE_Z) - 1 else 0) / 2
        for j in (0, len(FRACS) - 1):
            nid = grid[f"{i},{j}"]
            F = np.zeros(3)
            for m in model["members"]:
                if m["group"].startswith("lumbar_plate") and nid in m["nodes"]:
                    F += _member_node_force_global(res, m["id"], nid)
            n = np.linalg.norm(F) / trib
            tau = n / b
            k = volkersen_factor(om * trib, min(Et1, Et2) / max(Et1, Et2))
            if tau * k > worst[1]:
                worst = (tau, tau * k, nid)
    out.append({"check": f"lumbar plate-to-stay bond avg ({worst[2]})", "value": worst[0], "unit": "MPa",
                "allow": tau_s, "sf": tau_s / worst[0] if worst[0] else np.inf})
    out.append({"check": f"lumbar plate-to-stay bond Volkersen peak ({worst[2]})", "value": worst[1],
                "unit": "MPa", "allow": tau_s, "sf": tau_s / worst[1] if worst[1] else np.inf})
    # pivot insert punching (flange D 30 mm, ASSUMPTION)
    F = np.linalg.norm(res.reactions.get("HP", np.zeros(6))[:3])
    tau_p = F / (np.pi * 30.0 * t)
    out.append({"check": "Ti pivot insert punching shear in lumbar plate (D30 flange)", "value": tau_p,
                "unit": "MPa", "allow": tau_a, "sf": tau_a / tau_p if tau_p else np.inf})
    return out
