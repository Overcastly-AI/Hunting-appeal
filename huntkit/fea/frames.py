"""Parametric pack frame builder (shared by huntkit.fea and huntkit.viz3d).

Public API (stable; huntkit.viz3d imports it):
  DEFAULT_PARAMS, build_frame(params) -> model dict, aluminum_baseline(**kw), carbon_variant(**kw),
  load_frame_params(path) -> params dict, build_frame_from_yaml(path, **overrides) -> model dict,
  hardware_mass(model) -> dict.

Coordinates: x lateral (+ wearer's right), y fore-aft (+ AFT, toward the bag), z up; z = 0 at the
stay feet. Model dict keys: nodes {id: [x,y,z]}, members [{id, nodes, section, material, group,
ref}], groups {hipbelt, shoulder, lifter, shelf_pivot, shelf_strap, lash, foot_left, foot_right,
[bag]}, joints [...], hubs [...], params, warnings, settings.

Layout:
- two stays, splayed (``width_bottom`` -> ``width_top``). ``stay_style``:
  "curved"    bent tube following the lumbar curve (aluminium),
  "segmented" straight tubes joined by bonded elbows at the lumbar apex,
  "straight"  one straight tube per stay foot->top (off-the-shelf carbon; the lumbar curve is
              built into the lumbar pad foam). No elbow joints.
- top cross-bar (corner hubs), lumbar/hipbelt cross-bar at ``hip_z`` (through-sleeve hubs),
  optional mid cross-bar at ``mid_bar_z`` (through-sleeve hubs) and X-brace(s).
- ``anchors_at_nodes``: shelf-strap anchors on the mid-bar hubs, lashing on the top hubs,
  shelf pivots in the bonded foot inserts.
- shoulder-harness yoke at ``hip_z + torso_mm - yoke_drop`` (continuous torso adjust).
Rect/oval tubes: ``w`` is along the member's local y = ``ref`` (stays: lateral; cross-bars:
vertical), ``h`` along local z (fore-aft depth for both).
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

from .sections import Section, composite_tube, from_spec, tube_round

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
    "stay_style": "curved",      # "curved" | "segmented" | "straight"
    "n_stay": 18,                # nodes per stay (curved); others add key nodes + 8 uniform
    "hip_z": 90.0,               # hipbelt / lumbar cross-member height
    "shelf_z": 30.0,
    "shelf_strap_z": 300.0,
    "lash_z": 480.0,
    "mid_bar_z": None,           # optional mid cross-bar height
    "xbrace": None,              # None | "lower" (lumbar->mid) | "upper" (mid->top) | "both" | "full"
    "anchors_at_nodes": False,   # shelf straps -> mid hubs, lashing -> top hubs, pivots -> feet
    "torso_in": 19.0,            # wearer torso length (C7 to iliac crest), inches
    "yoke_drop": 50.0,           # ASSUMPTION: yoke anchor sits 50 mm below C7 height
    "n_bag": 5,                  # bag attachment points per stay
    "haul_mode": False,          # frame-only haul: no bag; loads to shelf + lashing points
    "section": None,             # Section or spec dict for stays
    "material": "alu_7075_t6",
    "crossbar_section": None,    # default = stay section
    "crossbar_material": None,
    "brace_section": None,       # default = crossbar section
    "brace_material": None,
    "stay_ref": [1.0, 0.0, 0.0],
    "crossbar_ref": [0.0, 0.0, 1.0],
    "joint": {},                 # overrides for joints.DEFAULT_JOINT
    "bonded": True,              # list bonded joints (False for a welded/one-piece metal frame)
    "hardware": {},              # overrides for HARDWARE_DEFAULTS (mass estimate)
}

# ASSUMPTIONS for the hub / fitting / adhesive mass estimate (see hardware_mass()).
HARDWARE_DEFAULTS = {
    "sleeve_density_kg_m3": 2810,     # 7075-T6 sockets / through-sleeves
    "sleeve_t_mm": 1.0,
    "socket_extra_mm": 5.0,           # socket length beyond the bond overlap (shoulder / chamfer)
    "web_plate_t_mm": 2.0,            # CF 0/90 plate web joining the sockets of a hub (2 plies of it)
    "web_plate_density_kg_m3": 1500,
    "web_plate_len_mm": 30.0,         # web length per connected tube, x (tube size + 10 mm) wide
    "web_plates_per_hub": 2,          # sandwich: one each side
    "foot_insert_len_mm": 25.0,
    "foot_insert_fill": 0.45,         # fraction of the bore volume that is metal (hollow plug)
    "foot_boss_g": 3.0,               # shelf-pivot boss
    "adhesive_density_kg_m3": 1150,
    "adhesive_fillet_factor": 1.5,    # squeeze-out / fillets
}


def _stay_xy(z, side, p):
    H = p["height"]
    s = z / H
    x = side * (p["width_bottom"] / 2 + (p["width_top"] - p["width_bottom"]) / 2 * s)
    y = -p["lumbar_depth"] * np.exp(-((z - p["lumbar_z"]) / p["lumbar_width"]) ** 2) + p["top_sweep"] * s ** 2
    return x, y


def _stay_point(z, side, p):
    H = p["height"]
    style = p["stay_style"]
    if style == "segmented":
        zk = [0.0, p["lumbar_z"], H]
    elif style == "straight":
        zk = [0.0, H]
    else:
        return _stay_xy(z, side, p)
    xk, yk = zip(*[_stay_xy(zz, side, p) for zz in zk])
    return float(np.interp(z, zk, xk)), float(np.interp(z, zk, yk))


def _sec(spec, default=None):
    if spec is None:
        return default
    return spec if isinstance(spec, Section) else from_spec(spec)


def build_frame(params: dict | None = None) -> dict:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p.update(params or {})
    H = p["height"]
    sec = _sec(p["section"], tube_round(12.7, 0.9))
    mat = p["material"]
    xsec = _sec(p["crossbar_section"], sec)
    xmat = p["crossbar_material"] or mat
    bsec = _sec(p["brace_section"], xsec)
    bmat = p["brace_material"] or xmat
    sref, xref = p["stay_ref"], p["crossbar_ref"]
    warnings = []

    if p["anchors_at_nodes"]:
        p["shelf_z"] = 0.0
        p["lash_z"] = H
        if p["mid_bar_z"] is not None:
            p["shelf_strap_z"] = p["mid_bar_z"]
        else:
            warnings.append("anchors_at_nodes without mid_bar_z: shelf straps stay at shelf_strap_z")

    torso_mm = p["torso_in"] * IN
    shoulder_z = p["hip_z"] + torso_mm - p["yoke_drop"]
    if shoulder_z > H - 10:
        warnings.append(f"torso {p['torso_in']:g} in needs the yoke at z={shoulder_z:.0f} mm but the "
                        f"frame is {H:.0f} mm tall: yoke modelled at z={H - 10:.0f} mm. Frame height "
                        f">= {shoulder_z + 10:.0f} mm needed for this torso setting.")
        shoulder_z = H - 10
    p["shoulder_z"] = shoulder_z

    zb = np.linspace(max(p["shelf_z"], 30.0), H - 20, p["n_bag"])
    key = [0.0, p["shelf_z"], p["hip_z"], p["lumbar_z"], p["shelf_strap_z"], p["lash_z"],
           shoulder_z, H, *zb]
    if p["mid_bar_z"] is not None:
        key.append(p["mid_bar_z"])
    key += list(np.linspace(0, H, p["n_stay"] if p["stay_style"] == "curved" else 8))
    must = {0.0, H, p["hip_z"], p["mid_bar_z"]}
    zs = []
    for z in sorted(key):
        if not zs or z - zs[-1] > 3.0:
            zs.append(float(z))
        elif z in must:      # keep hub heights exact
            zs[-1] = float(z)
    zs[-1] = H

    nodes, members, groups, joints, hubs = {}, [], {}, [], []

    def iz(z):
        return int(np.argmin([abs(zz - z) for zz in zs]))

    def nearest(tag, z):
        return f"{tag}{iz(z)}"

    for side, tag in ((-1, "SL"), (1, "SR")):
        for i, z in enumerate(zs):
            x, y = _stay_point(z, side, p)
            nodes[f"{tag}{i}"] = [float(x), float(y), float(z)]
        grp = "stay_left" if side < 0 else "stay_right"
        for i in range(len(zs) - 1):
            members.append({"id": f"{tag}_{i}", "nodes": [f"{tag}{i}", f"{tag}{i + 1}"],
                            "section": sec, "material": mat, "group": grp, "ref": sref})
        if p["stay_style"] == "segmented" and p["bonded"]:
            ki = iz(p["lumbar_z"])
            joints.append({"id": f"elbow_{tag}", "node": f"{tag}{ki}",
                           "members": [f"{tag}_{ki - 1}", f"{tag}_{ki}"], "params": p["joint"]})
            hubs.append({"id": f"elbow_{tag}", "node": f"{tag}{ki}", "ends": 2, "through": 0})
        if p["bonded"]:
            joints.append({"id": f"foot_{tag}", "node": f"{tag}0", "members": [f"{tag}_0"],
                           "params": p["joint"]})
            hubs.append({"id": f"foot_{tag}", "node": f"{tag}0", "ends": 0, "through": 0, "foot": True})

    def crossbar(prefix, z_idx, group, s, m):
        L, R = np.array(nodes[f"SL{z_idx}"]), np.array(nodes[f"SR{z_idx}"])
        chain = [f"SL{z_idx}"]
        for k in range(1, 4):
            nid = f"{prefix}{k}"
            nodes[nid] = list(map(float, L + (R - L) * k / 4))
            chain.append(nid)
        chain.append(f"SR{z_idx}")
        for k in range(4):
            members.append({"id": f"{group}_{k}", "nodes": [chain[k], chain[k + 1]], "section": s,
                            "material": m, "group": group, "ref": xref})

    itop = len(zs) - 1
    ih = iz(p["hip_z"])
    crossbar("TB", itop, "top_bar", xsec, xmat)
    crossbar("LB", ih, "lumbar_bar", xsec, xmat)
    # keep the original member ids used by older code ("top_k", "lumbar_k")
    for m in members:
        if m["group"] == "top_bar":
            m["id"] = m["id"].replace("top_bar_", "top_")
        elif m["group"] == "lumbar_bar":
            m["id"] = m["id"].replace("lumbar_bar_", "lumbar_")
    im = None
    if p["mid_bar_z"] is not None:
        im = iz(p["mid_bar_z"])
        crossbar("MB", im, "mid_bar", xsec, xmat)

    # X-braces between hub levels (diagonals pass each other, not connected at the crossing)
    levels = {"lumbar": ih, "mid": im, "top": itop}
    spans = {"lower": [("lumbar", "mid")], "upper": [("mid", "top")],
             "both": [("lumbar", "mid"), ("mid", "top")], "full": [("lumbar", "top")]}.get(p["xbrace"], [])
    brace_at = {}
    for lo, hi in spans:
        a, b = levels[lo], levels[hi]
        if a is None or b is None:
            warnings.append(f"xbrace {lo}->{hi} needs mid_bar_z; skipped")
            continue
        for k, (n1, n2) in enumerate(((f"SL{a}", f"SR{b}"), (f"SR{a}", f"SL{b}"))):
            bid = f"brace_{lo}_{hi}_{k}"
            members.append({"id": bid, "nodes": [n1, n2], "section": bsec, "material": bmat,
                            "group": "brace", "ref": [0.0, 1.0, 0.0], "nseg": 4})
            brace_at.setdefault(n1, []).append(bid)
            brace_at.setdefault(n2, []).append(bid)

    if p["bonded"]:
        for side, tag in ((-1, "SL"), (1, "SR")):
            tb = "top_0" if tag == "SL" else "top_3"
            lb = "lumbar_0" if tag == "SL" else "lumbar_3"
            n = f"{tag}{itop}"
            joints.append({"id": f"corner_{tag[1]}", "node": n,
                           "members": [tb, f"{tag}_{itop - 1}"] + brace_at.get(n, []), "params": p["joint"]})
            hubs.append({"id": f"corner_{tag[1]}", "node": n, "ends": 2 + len(brace_at.get(n, [])), "through": 0})
            n = f"{tag}{ih}"
            joints.append({"id": f"lumbar_hub_{tag[1]}", "node": n, "members": [lb] + brace_at.get(n, []),
                           "through": [[f"{tag}_{ih - 1}", f"{tag}_{ih}"]] if ih > 0 else [],
                           "params": p["joint"]})
            hubs.append({"id": f"lumbar_hub_{tag[1]}", "node": n, "ends": 1 + len(brace_at.get(n, [])),
                         "through": 1})
            if im is not None:
                mb = "mid_bar_0" if tag == "SL" else "mid_bar_3"
                n = f"{tag}{im}"
                joints.append({"id": f"mid_hub_{tag[1]}", "node": n, "members": [mb] + brace_at.get(n, []),
                               "through": [[f"{tag}_{im - 1}", f"{tag}_{im}"]], "params": p["joint"]})
                hubs.append({"id": f"mid_hub_{tag[1]}", "node": n, "ends": 1 + len(brace_at.get(n, [])),
                             "through": 1})

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

    model = {"name": p["name"], "nodes": nodes, "members": members, "groups": groups,
             "joints": joints, "hubs": hubs, "params": p, "warnings": warnings,
             "settings": {"nseg": 2}}
    model["hardware"] = hardware_mass(model)
    return model


def _member_len(model, m):
    a, b = (np.asarray(model["nodes"][n]) for n in m["nodes"])
    return float(np.linalg.norm(b - a))


def _tube_size(sec):
    return sec.dims["od"] if "od" in sec.dims else max(sec.dims["w"], sec.dims["h"])


def _tube_perim(sec):
    return np.pi * sec.dims["od"] if "od" in sec.dims else 2 * (sec.dims["w"] + sec.dims["h"])


def hardware_mass(model: dict) -> dict:
    """ASSUMPTION-based mass of hubs, sockets, sleeves, foot inserts and adhesive (grams).

    Every bonded tube end gets a 7075 socket (wall ``sleeve_t_mm``, length overlap + 5 mm); each
    through-hub a 7075 through-sleeve; each hub two CF 0/90 web plates; each foot a hollow 7075
    insert with a shelf-pivot boss; adhesive = bond area x bondline x 1.15 g/cc x fillet factor.
    """
    from .joints import DEFAULT_JOINT
    p = model["params"]
    h = {**HARDWARE_DEFAULTS, **(p.get("hardware") or {})}
    jp = {**DEFAULT_JOINT, **(p.get("joint") or {})}
    ta = jp.get("adhesive_t_mm") or 0.2
    ov = jp["overlap_mm"]
    ov_t = jp.get("through_overlap_mm") or ov
    mem = {m["id"]: m for m in model["members"]}
    items = []
    stay_sec = _sec(mem["SL_0"]["section"])
    for hub in model.get("hubs", []):
        joint = next((j for j in model["joints"] if j["id"] == hub["id"]), None)
        secs = [_sec(mem[mid]["section"]) for mid in (joint or {}).get("members", [])]
        g = 0.0
        for s in secs:   # sockets
            per = _tube_perim(s) + np.pi * (2 * ta + h["sleeve_t_mm"])
            g += per * h["sleeve_t_mm"] * (ov + h["socket_extra_mm"]) * h["sleeve_density_kg_m3"] * 1e-6
        for _ in range(hub.get("through", 0)):
            per = _tube_perim(stay_sec) + np.pi * (2 * ta + h["sleeve_t_mm"])
            g += per * h["sleeve_t_mm"] * (ov_t + h["socket_extra_mm"]) * h["sleeve_density_kg_m3"] * 1e-6
        n_conn = len(secs) + 2 * hub.get("through", 0)
        if n_conn >= 2:
            web_area = sum((_tube_size(s) + 10) * h["web_plate_len_mm"] for s in secs) \
                + hub.get("through", 0) * (_tube_size(stay_sec) + 10) * 2 * h["web_plate_len_mm"]
            g += h["web_plates_per_hub"] * web_area * h["web_plate_t_mm"] * h["web_plate_density_kg_m3"] * 1e-6
        if hub.get("foot"):
            s = stay_sec
            bore = (s.dims["od"] - 2 * s.dims["t"]) if "od" in s.dims else min(s.dims["w"], s.dims["h"]) - 2 * s.dims["t"]
            g += (np.pi * bore ** 2 / 4 * h["foot_insert_len_mm"] * h["foot_insert_fill"]
                  * h["sleeve_density_kg_m3"] * 1e-6 + h["foot_boss_g"])
            area = np.pi * bore * h["foot_insert_len_mm"]
        else:
            area = sum(_tube_perim(s) * ov for s in secs) + hub.get("through", 0) * _tube_perim(stay_sec) * ov_t
        adh = area * ta * h["adhesive_density_kg_m3"] * h["adhesive_fillet_factor"] * 1e-6
        items.append({"hub": hub["id"], "metal_and_plate_g": g, "adhesive_g": adh, "total_g": g + adh})
    tubes_g = 0.0
    for m in model["members"]:
        s = _sec(m["section"])
        if getattr(s, "composite", False):
            rho = s.density_kg_m3
        else:
            from .materials_bridge import get_material, rho_of
            rho = rho_of(get_material(m["material"]))
        tubes_g += rho * s.A * 1e-9 * _member_len(model, m) * 1e3
    hw = sum(i["total_g"] for i in items)
    return {"items": items, "hubs_g": hw, "tubes_g": tubes_g, "total_g": tubes_g + hw}


# ----------------------------------------------------------------------------- YAML
def load_frame_params(path) -> dict:
    """Read ``designs/<design>/frame.yaml`` -> params dict for :func:`build_frame`.

    The YAML holds a ``frame:`` mapping with the DEFAULT_PARAMS keys; sections are spec dicts
    ({type: composite_tube, od, layup, material, ply_t} / {type: tube_round, od, t} ...).
    Unknown top-level keys (stock list, joint design notes, results) are ignored here.
    """
    import yaml
    doc = yaml.safe_load(Path(path).read_text())
    fr = dict(doc.get("frame", doc))
    for k in ("section", "crossbar_section", "brace_section"):
        if isinstance(fr.get(k), dict):
            fr[k] = _sec(_yaml_layup(fr[k]))
    return {k: v for k, v in fr.items() if k in DEFAULT_PARAMS}


def _yaml_layup(spec: dict) -> dict:
    s = dict(spec)
    lay = s.get("layup")
    if isinstance(lay, list) and lay and isinstance(lay[0], dict):
        s["layup"] = [dict(x) for x in lay]
    return s


def build_frame_from_yaml(path, **overrides) -> dict:
    p = load_frame_params(path)
    p.update(overrides)
    return build_frame(p)


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
