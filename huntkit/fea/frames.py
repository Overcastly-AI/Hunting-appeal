"""Parametric placeholder pack frame (the pack-designer refines the geometry later).

Layout (x lateral, y aft, z up; z = 0 at the stay feet):
- two stays, splayed (``width_bottom`` at the feet -> ``width_top`` at the top, centrelines) and
  curved toward the wearer at the lumbar (``lumbar_depth`` bulge to -y at ``lumbar_z``), with an
  optional aft ``top_sweep``. ``stay_style``: "curved" (bent tube, e.g. aluminium) or
  "segmented" (straight off-the-shelf tubes joined by bonded elbow fittings at the lumbar apex,
  the buildable route for roll-wrapped/pultruded carbon without a custom mould).
- top cross-bar between the stay tops (bonded corner fittings),
- lumbar / hipbelt cross-member at ``hip_z`` (bonded T fittings),
- load-shelf pivots at ``shelf_z``; shelf-strap anchors at ``shelf_strap_z``; lashing points at
  ``lash_z``; bag attachment points along both stays (unless ``haul_mode``).
- shoulder-harness yoke anchor at ``hip_z + torso_mm - yoke_drop`` (continuous torso adjust).

Every member is listed in ``model["members"]`` with a ``group``; bonded joints in
``model["joints"]`` for ``joints.check_frame_joints``.
"""
from __future__ import annotations

import copy

import numpy as np

from .sections import composite_tube, tube_round

IN = 25.4

DEFAULT_PARAMS = {
    "name": "placeholder_frame",
    "height": 560.0,
    "width_top": 180.0,
    "width_bottom": 260.0,
    "lumbar_z": 120.0,
    "lumbar_depth": 25.0,
    "lumbar_width": 110.0,       # gaussian width of the lumbar curve (mm)
    "top_sweep": 15.0,
    "stay_style": "curved",      # "curved" | "segmented"
    "n_stay": 18,                # nodes per stay (curved); segmented adds key nodes only
    "hip_z": 90.0,               # hipbelt / lumbar cross-member height
    "shelf_z": 30.0,
    "shelf_strap_z": 300.0,
    "lash_z": 480.0,
    "torso_in": 19.0,            # wearer torso length (C7 to iliac crest), inches
    "yoke_drop": 50.0,           # ASSUMPTION: yoke anchor sits 50 mm below C7 height
    "n_bag": 5,                  # bag attachment points per stay
    "haul_mode": False,          # frame-only haul: no bag; loads to shelf + lashing points
    "section": None,             # Section or spec dict for stays
    "material": "alu_7075_t6",
    "crossbar_section": None,    # default = stay section
    "crossbar_material": None,
    "joint": {},                 # overrides for joints.DEFAULT_JOINT
    "bonded": True,              # list bonded joints (False for a welded/one-piece metal frame)
}


def _stay_xy(z, side, p):
    H = p["height"]
    s = z / H
    x = side * (p["width_bottom"] / 2 + (p["width_top"] - p["width_bottom"]) / 2 * s)
    y = -p["lumbar_depth"] * np.exp(-((z - p["lumbar_z"]) / p["lumbar_width"]) ** 2) + p["top_sweep"] * s ** 2
    return x, y


def build_frame(params: dict | None = None) -> dict:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p.update(params or {})
    H = p["height"]
    sec = p["section"] or tube_round(12.7, 0.9)
    mat = p["material"]
    xsec = p["crossbar_section"] or sec
    xmat = p["crossbar_material"] or mat
    warnings = []

    torso_mm = p["torso_in"] * IN
    shoulder_z = p["hip_z"] + torso_mm - p["yoke_drop"]
    if shoulder_z > H - 10:
        warnings.append(f"torso {p['torso_in']:g} in needs the yoke at z={shoulder_z:.0f} mm but the "
                        f"frame is {H:.0f} mm tall: yoke modelled at z={H - 10:.0f} mm. Frame height "
                        f">= {shoulder_z + 10:.0f} mm needed for this torso setting.")
        shoulder_z = H - 10
    p["shoulder_z"] = shoulder_z

    zb = np.linspace(p["shelf_z"], H - 20, p["n_bag"])
    key = [0.0, p["shelf_z"], p["hip_z"], p["lumbar_z"], p["shelf_strap_z"], p["lash_z"],
           shoulder_z, H, *zb]
    if p["stay_style"] == "curved":
        key += list(np.linspace(0, H, p["n_stay"]))
    else:
        key += list(np.linspace(0, H, 8))
    zs = []
    for z in sorted(key):
        if not zs or z - zs[-1] > 3.0:
            zs.append(float(z))
        else:  # snap: keep the earlier node
            pass
    if zs[-1] != H:
        zs[-1] = H

    nodes, members, groups, joints = {}, [], {}, []

    def nearest(side_tag, z):
        return f"{side_tag}{int(np.argmin([abs(zz - z) for zz in zs]))}"

    for side, tag in ((-1, "SL"), (1, "SR")):
        for i, z in enumerate(zs):
            if p["stay_style"] == "segmented":
                # straight between foot, lumbar apex and top
                zk = [0.0, p["lumbar_z"], H]
                xk, yk = zip(*[_stay_xy(zz, side, p) for zz in zk])
                x = np.interp(z, zk, xk); y = np.interp(z, zk, yk)
            else:
                x, y = _stay_xy(z, side, p)
            nodes[f"{tag}{i}"] = [float(x), float(y), float(z)]
        grp = "stay_left" if side < 0 else "stay_right"
        for i in range(len(zs) - 1):
            members.append({"id": f"{tag}_{i}", "nodes": [f"{tag}{i}", f"{tag}{i + 1}"],
                            "section": sec, "material": mat, "group": grp})
        if p["stay_style"] == "segmented" and p["bonded"]:
            k = nearest(tag, p["lumbar_z"])
            ki = int(k[2:])
            joints.append({"id": f"elbow_{tag}", "node": k, "members": [f"{tag}_{ki - 1}", f"{tag}_{ki}"],
                           "params": p["joint"]})

    # top cross-bar (4 segments) between stay tops
    itop = len(zs) - 1
    L, R = np.array(nodes[f"SL{itop}"]), np.array(nodes[f"SR{itop}"])
    tb = [f"SL{itop}"]
    for k in range(1, 4):
        nid = f"TB{k}"
        nodes[nid] = list(map(float, L + (R - L) * k / 4))
        tb.append(nid)
    tb.append(f"SR{itop}")
    for k in range(4):
        members.append({"id": f"top_{k}", "nodes": [tb[k], tb[k + 1]], "section": xsec,
                        "material": xmat, "group": "top_bar"})
    # lumbar cross-member at hip_z
    ih = int(np.argmin([abs(z - p["hip_z"]) for z in zs]))
    L, R = np.array(nodes[f"SL{ih}"]), np.array(nodes[f"SR{ih}"])
    lb = [f"SL{ih}"]
    for k in range(1, 4):
        nid = f"LB{k}"
        nodes[nid] = list(map(float, L + (R - L) * k / 4))
        lb.append(nid)
    lb.append(f"SR{ih}")
    for k in range(4):
        members.append({"id": f"lumbar_{k}", "nodes": [lb[k], lb[k + 1]], "section": xsec,
                        "material": xmat, "group": "lumbar_bar"})

    if p["bonded"]:
        joints += [
            {"id": "corner_L", "node": f"SL{itop}", "members": ["top_0", f"SL_{itop - 1}"], "params": p["joint"]},
            {"id": "corner_R", "node": f"SR{itop}", "members": ["top_3", f"SR_{itop - 1}"], "params": p["joint"]},
            {"id": "tee_lumbar_L", "node": f"SL{ih}", "members": ["lumbar_0"], "params": p["joint"]},
            {"id": "tee_lumbar_R", "node": f"SR{ih}", "members": ["lumbar_3"], "params": p["joint"]},
        ]

    both = lambda z: [nearest("SL", z), nearest("SR", z)]  # noqa: E731
    groups["hipbelt"] = both(p["hip_z"]) + ["LB1", "LB3"]
    groups["shoulder"] = both(shoulder_z)
    groups["lifter"] = [f"SL{itop}", f"SR{itop}"]
    groups["shelf_pivot"] = both(p["shelf_z"])
    groups["shelf_strap"] = both(p["shelf_strap_z"])
    groups["lash"] = both(p["lash_z"])
    groups["foot_left"] = ["SL0"]
    groups["foot_right"] = ["SR0"]
    if not p["haul_mode"]:
        bag = []
        for z in zb:
            bag += both(z)
        bag.append("TB2")
        groups["bag"] = list(dict.fromkeys(bag))

    return {"name": p["name"], "nodes": nodes, "members": members, "groups": groups,
            "joints": joints, "params": p, "warnings": warnings,
            "settings": {"nseg": 2}}


# ----------------------------------------------------------------------------- demo variants
def aluminum_baseline(**kw) -> dict:
    p = {"name": "alu_7075_12.7x0.9", "section": tube_round(12.7, 0.9), "material": "alu_7075_t6",
         "stay_style": "curved", "bonded": True}
    p.update(kw)
    return build_frame(p)


def carbon_variant(**kw) -> dict:
    from .materials_bridge import CARBON_CANDIDATES, first_available
    ply_mat = first_available(CARBON_CANDIDATES)
    sec = composite_tube(12.7, "[0,±45,0,90]s", ply_mat, ply_t=0.10)
    p = {"name": "cfrp_12.7_[0,±45,0,90]s", "section": sec, "material": None,
         "stay_style": "segmented", "bonded": True}
    p.update(kw)
    return build_frame(p)
