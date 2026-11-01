"""Topology-optimized 3D-printed node lugs for the Pack 5200 carbon frame.

Each lug = bonded socket sleeves (non-design, solid skin at the bond surface, tube bore void) plus
a SIMP-optimized body in a voxel box around the frame node. Loads are the frame-model member end
forces (huntkit.gendesign.loads) for every case of the current load standard at torso 15/19/23 in,
left joints mirrored onto the right-hand lug (the left lug is printed mirrored).

Load application: each loaded tube's [F, M] (at the frame node) is moved to the centroid of its
bond-surface nodes and spread over them as f_i = F/n + omega x r_i with omega = I^-1 M
(I = sum |r|^2 1 - r r^T): exact resultant force and moment. The anchor tube's bond nodes are
clamped (it reacts the remainder, including any external load at the node).

Load factors: every case's load is multiplied by its required factor (HA-LS-1: 1.5 limit / 2.0 static
/ 1.0 ultimate), so the stress check is "factored stress <= design allowable".

Variants
- "slm_ti":  Ti-6Al-4V SLM + HIP (data/materials/metals/ti_6al_4v_slm.yaml), 1.0 mm bond skin,
             filter radius >= 1.0 mm wall, 45 deg overhang rule for orientation.
- "fdm_pacf": PAHT-CF (data/materials/polymers/pa12_cf_fdm_paht.yaml), 2.0 mm walls, layer
             orientation chosen so the stress normal to the layers is smallest (Z strength 47 MPa).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import get_material

from .fem import Assembler, Grid, Solver, b_h8_center, iso_D3, ke_h8, von_mises_3d
from .loads import external_on_node, member_end_global, mirror6, mirror_pt
from .simp import SimpProblem, run_simp

BOND_T = 0.5            # mm adhesive bondline (frame.yaml joints.bondline_mm)

VARIANTS = {
    "slm_ti": {"material": "ti_6al_4v_slm", "skin": 1.0, "min_wall": 1.0, "overhang_deg": 45.0,
               "voxels": 24000, "volfrac": 0.06, "process": "SLM (L-PBF) Ti-6Al-4V + HIP"},
    "fdm_pacf": {"material": "pa12_cf_fdm_paht", "skin": 2.0, "min_wall": 2.0, "overhang_deg": 20.0,
                 "voxels": 18000, "volfrac": 0.25, "process": "desktop FDM, PAHT-CF (PA12-CF)"},
}


@dataclass
class Socket:
    name: str
    axis: np.ndarray            # unit, from the node outward along the tube
    od: float                   # tube OD
    kind: str = "end"           # "end" | "through" | "pin" | "pad" | "flange"
    s0: float = 0.0             # start of the bond (end sockets)
    length: float = 30.0
    role: str = "load"          # "anchor" | "load" | "passive"
    center: np.ndarray = field(default_factory=lambda: np.zeros(3))   # socket origin (pins/pads)
    loads: dict = field(default_factory=dict)     # load key -> 6-vector at the frame node (or centre)

    @property
    def rb(self):
        return self.od / 2 + (BOND_T if self.kind in ("end", "through") else 0.0)


@dataclass
class LugSpec:
    name: str
    title: str
    sockets: list
    qty: int = 2
    joints: list = field(default_factory=list)
    baseline_7075_g: float = 0.0
    note: str = ""
    case_req: dict = field(default_factory=dict)     # load key -> required factor
    static_keys: list = field(default_factory=list)  # keys used for the fatigue check


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _sec_od(model, member_id):
    from huntkit.fea.sections import from_spec
    m = next(mm for mm in model["members"] if mm["id"] == member_id)
    return float(from_spec(m["section"]).dims.get("od", 20.0))


def _other_end(model, member_id, node):
    m = next(mm for mm in model["members"] if mm["id"] == member_id)
    o = m["nodes"][1] if m["nodes"][0] == node else m["nodes"][0]
    return np.asarray(model["nodes"][o], float)


def sleeve_7075_g(od, length, ts=2.0, ta=0.5, extra=5.0):
    """Mass of one 7075 socket sleeve as costed in huntkit.fea.pack5200.hardware_mass."""
    per = np.pi * od + np.pi * (2 * ta + ts)
    return per * ts * (length + extra) * 2810e-6


# ----------------------------------------------------------------------------- lug specs
def build_specs(frame: dict) -> list[LugSpec]:
    """Lug specs (right-hand geometry) with every case/torso/side load set attached.

    frame: output of loads.run_all()."""
    runs = frame["runs"]
    (r0, m0, _) = next(iter(runs.values()))
    joints = {j["id"]: j for j in m0["joints"]}
    jp = (m0["params"].get("joint") or {})
    ov, ov_t = jp.get("overlap_mm", 30.0), jp.get("through_overlap_mm", 40.0)
    ts_al = jp.get("sleeve_t_mm", 2.0)
    specs = []

    def per_side(jid_base):
        return [(f"{jid_base}_R", False), (f"{jid_base}_L", True)]

    def add_loads(spec, sock_members, through=None, ext_node_sock=None):
        """sock_members: {socket name: member id pattern resolver(side_joint)}"""
        for (case, t), (res, model, c) in runs.items():
            for base in spec.joints:
                for jid, mir in per_side(base):
                    j = next((jj for jj in model["joints"] if jj["id"] == jid), None)
                    if j is None:
                        continue
                    key = f"{case}|{t}|{jid}"
                    spec.case_req[key] = c.required_sf
                    if case == "static_carry":
                        spec.static_keys.append(key)
                    for s in spec.sockets:
                        v = sock_members(s, j, res, model)
                        if v is None:
                            continue
                        s.loads[key] = mirror6(v) if mir else np.asarray(v, float)

    # --- crown corner -------------------------------------------------------
    if "crown_corner_R" in joints:
        j = joints["crown_corner_R"]
        node = np.asarray(m0["nodes"][j["node"]], float)
        leg_id, bar_id = j["members"]
        a_leg = _unit(_other_end(m0, leg_id, j["node"]) - node)
        a_bar = _unit(_other_end(m0, bar_id, j["node"]) - node)
        od_leg, od_bar = _sec_od(m0, leg_id), _sec_od(m0, bar_id)
        r_leg = od_leg / 2 + BOND_T + 2.0
        r_bar = od_bar / 2 + BOND_T + 2.0
        socks = [Socket("leg", a_leg, od_leg, "end", s0=r_bar + 2, length=ov, role="anchor"),
                 Socket("top_bar", a_bar, od_bar, "end", s0=r_leg + 2, length=ov, role="load"),
                 Socket("post", -a_leg, od_leg, "end", s0=r_bar + 2, length=25.0, role="load")]
        sp = LugSpec("crown_corner", "Crown corner (leg top + top bar + extension-post socket)", socks, qty=2,
                     joints=["crown_corner"],
                     baseline_7075_g=sleeve_7075_g(od_leg, ov, ts_al) + sleeve_7075_g(od_bar, ov, ts_al) + 4.0,
                     note="7075 baseline costs 2 sockets + gusset (the post socket was not costed in the 338 g).")

        def f_corner(s, jj, res, model):
            if s.name == "leg":
                return None
            if s.name == "top_bar":
                return member_end_global(res, jj["members"][1], jj["node"])
            if s.name == "post":
                pid = "post_" + jj["id"][-1]
                return member_end_global(res, pid, jj["node"]) if any(m["id"] == pid for m in model["members"]) else None
        add_loads(sp, f_corner)
        specs.append(sp)

    # --- stay hub (mid bar z 330 and upper bar z 520 share one lug) ---------
    if "mid_hub_R" in joints:
        j = joints["mid_hub_R"]
        node = np.asarray(m0["nodes"][j["node"]], float)
        bar_id = j["members"][0]
        below, above = j["through"][0]
        a_st = _unit(_other_end(m0, above, j["node"]) - _other_end(m0, below, j["node"]))
        a_bar = _unit(_other_end(m0, bar_id, j["node"]) - node)
        od_st, od_bar = _sec_od(m0, above), _sec_od(m0, bar_id)
        Lt = max(ov_t, od_bar + 24.0)
        socks = [Socket("stay", a_st, od_st, "through", length=Lt, role="anchor"),
                 Socket("bar", a_bar, od_bar, "end", s0=od_st / 2 + BOND_T + 3.0, length=ov, role="load")]
        n_hubs = sum(1 for k in ("mid_hub_R", "upper_hub_R") if k in joints)
        sp = LugSpec("stay_hub", "Stay T-hub (through-sleeve on the stay + cross-bar socket; mid bar AND upper bar)",
                     socks, qty=2 * n_hubs, joints=[k[:-2] for k in ("mid_hub_R", "upper_hub_R") if k in joints],
                     baseline_7075_g=sleeve_7075_g(od_st, ov_t, ts_al) + sleeve_7075_g(od_bar, ov, ts_al) + 4.0)

        def f_hub(s, jj, res, model):
            if s.name == "stay":     # through: load = upper stay half
                b, a = jj["through"][0]
                return ("through_above", member_end_global(res, a, jj["node"]))
            return member_end_global(res, jj["members"][0], jj["node"])

        def f_hub2(s, jj, res, model):
            v = f_hub(s, jj, res, model)
            if isinstance(v, tuple):
                return v[1]
            return v
        add_loads(sp, f_hub2)
        specs.append(sp)

    # --- lumbar elbow (segmented stays only) -----------------------------------
    if "elbow_R" in joints:
        j = joints["elbow_R"]
        node = np.asarray(m0["nodes"][j["node"]], float)
        lo, up = j["members"]
        a_lo = _unit(_other_end(m0, lo, j["node"]) - node)
        a_up = _unit(_other_end(m0, up, j["node"]) - node)
        od = _sec_od(m0, up)
        socks = [Socket("lower", a_lo, od, "end", s0=4.0, length=ov, role="anchor"),
                 Socket("upper", a_up, od, "end", s0=4.0, length=ov, role="load")]
        sp = LugSpec("lumbar_elbow", "Lumbar elbow (lower stay -> upper stay, lumbar-plate corner)", socks, qty=2,
                     joints=["elbow"], baseline_7075_g=2 * sleeve_7075_g(od, ov, ts_al),
                     note="Deleted if the v2 straight-stay topology is adopted (frame_sizing.md v2).")
        add_loads(sp, lambda s, jj, res, model: None if s.name == "lower"
                  else member_end_global(res, jj["members"][1], jj["node"]))
        specs.append(sp)

    # --- stay foot boot + shelf pivot ------------------------------------------
    if "foot_R" in joints:
        j = joints["foot_R"]
        node = np.asarray(m0["nodes"][j["node"]], float)
        st = j["members"][0]
        a_st = _unit(_other_end(m0, st, j["node"]) - node)
        od = _sec_od(m0, st)
        sock_len = 25.0
        rb = od / 2 + BOND_T
        piv = np.array([0.0, rb + 1.0 + 7.0, 25.0])       # ASSUMPTION: boss moved aft to clear the tube
        socks = [Socket("stay", a_st, od, "end", s0=3.0, length=sock_len, role="anchor"),
                 Socket("shelf_pivot", np.array([1.0, 0, 0]), 8.0, "pin", length=14.0, role="load", center=piv),
                 Socket("ground_pad", -a_st, 2 * rb + 2.0, "pad", length=3.0, role="load", center=np.zeros(3))]
        sp = LugSpec("stay_foot", "Stay foot boot (stay socket + shelf-pivot clevis + ground bumper pad)", socks,
                     qty=2, joints=["foot"], baseline_7075_g=14.0,
                     note="Baseline = foot_boot_g 14 g each (huntkit.fea.pack5200 HW, ASSUMPTION). Shelf pivot "
                          "boss sits 8 mm aft of the sleeve OD (ASSUMPTION; hard point shelf_pivot is inside the tube).")
        piv_node = {"R": "SR25", "L": "SL25"}

        def f_foot(s, jj, res, model):
            side = jj["id"][-1]
            if s.name == "shelf_pivot":
                f = (res.model.get("loads") or {}).get(piv_node[side])
                return None if f is None else np.r_[np.asarray(f, float)[:3], 0, 0, 0]
            if s.name == "ground_pad":
                f = (res.model.get("loads") or {}).get(jj["node"])
                return None if f is None else np.r_[np.asarray(f, float)[:3], 0, 0, 0]
            return None
        add_loads(sp, f_foot)
        specs.append(sp)

    # --- hipbelt Ti pivot mount ------------------------------------------------
    if "HP" in m0["nodes"]:
        hp = np.asarray(m0["nodes"]["HP"], float)
        # plate surface: stay y at the pivot height, minus half the plate (wearer side)
        y_plate = -25.0 + 2.0 - float(m0["params"].get("lumbar_plate_t", 4.0)) / 2 - 2.0
        stand = hp[1] - y_plate                 # negative: toward the wearer
        socks = [Socket("plate_flange", np.array([0, -1.0, 0]), 44.0, "flange", length=1.2, role="anchor",
                     center=np.array([0.0, 0.0, 0.0])),
                 Socket("pivot_pin", np.array([0, -1.0, 0]), 10.0, "pin", length=14.0, role="load",
                        center=np.array([0.0, stand, 0.0]))]
        sp = LugSpec("hip_pivot_mount", "Hipbelt pivot mount (bonded flange on the lumbar plate + 10 mm roll-pin boss)",
                     socks, qty=1, joints=["HP"], baseline_7075_g=28.0,
                     note=f"Baseline = Ti pivot insert 28 g (pack5200 HW ASSUMPTION). D44 bonded flange (1.2 mm Ti / 2 mm FDM). Pin axis fore-aft (free roll); "
                          f"boss {abs(stand):.0f} mm proud of the plate face.")
        for (case, t), (res, model, c) in runs.items():
            key = f"{case}|{t}|HP"
            sp.case_req[key] = c.required_sf
            if case == "static_carry":
                sp.static_keys.append(key)
            r = res.reactions.get("HP")
            if r is not None and np.linalg.norm(r[:3]) > 1e-6:
                socks[1].loads[key] = np.r_[r[:3], 0, 0, 0]
        specs.append(sp)
    return specs


# ----------------------------------------------------------------------------- voxel model
def _local(s: Socket, c):
    """axial coordinate s and radius r of points c relative to socket s."""
    d = c - s.center
    ax = d @ s.axis
    r = np.linalg.norm(d - ax[:, None] * s.axis, axis=1)
    return ax, r


def socket_ranges(s: Socket, skin: float = 0.0):
    if s.kind == "through":
        return -s.length / 2, s.length / 2
    if s.kind in ("pin",):
        return -s.length / 2, s.length / 2
    if s.kind in ("pad", "flange"):
        return 0.0, max(s.length, skin)
    return s.s0, s.s0 + s.length


def build_domain(spec: LugSpec, var: dict, voxels: int | None = None, h: float | None = None):
    skin = var["skin"]
    pts = []
    for s in spec.sockets:
        a0, a1 = socket_ranges(s)
        R = s.rb + skin + (2.0 if s.kind in ("end", "through") else 3.0)
        if s.kind in ("pad", "flange"):
            R = s.od / 2
        for a in (a0, a1):
            p = s.center + a * s.axis
            for e in np.eye(3):
                for sg in (-1, 1):
                    q = e * sg * R
                    q = q - (q @ s.axis) * s.axis
                    pts.append(p + q)
    pts = np.array(pts)
    lo, hi = pts.min(0) - 1.0, pts.max(0) + 1.0
    if h is None:
        h = (np.prod(hi - lo) / (voxels or var["voxels"])) ** (1 / 3)
        h = max(h, 0.6)
    shape = np.maximum(np.ceil((hi - lo) / h).astype(int), 4)
    g = Grid(shape, h, lo)
    return g


def classify(spec: LugSpec, var: dict, g: Grid):
    """passive solid / void element masks and bond node sets."""
    skin = max(var["skin"], g.h * 0.999)
    c = g.elem_centers()
    nc = g.node_coords()
    ps = np.zeros(g.ne, bool)
    pv = np.zeros(g.ne, bool)
    bond = {}
    for s in spec.sockets:
        a0, a1 = socket_ranges(s, var["skin"])
        ax, r = _local(s, c)
        axn, rn = _local(s, nc)
        tol = 0.75 * g.h
        if s.kind in ("end", "through"):
            ins = (ax >= a0) & (ax <= a1)
            ps |= ins & (r >= s.rb) & (r < s.rb + skin)
            if s.kind == "end":
                pv |= (ax >= a0 - 0.5 * g.h) & (r < s.rb)
                pv |= (ax > a1) & (r < s.rb + skin + g.h)
            else:
                pv |= r < s.rb
                pv |= ((ax > a1) | (ax < a0)) & (r < s.rb + skin + g.h)
            nb = (axn >= a0) & (axn <= a1) & (np.abs(rn - s.rb) <= tol)
            if s.kind == "through":
                bond[s.name + ":below"] = np.where(nb & (axn < 0))[0]
                bond[s.name + ":above"] = np.where(nb & (axn >= 0))[0]
            bond[s.name] = np.where(nb)[0]
        elif s.kind == "pin":
            ins = (ax >= a0) & (ax <= a1)
            ps |= ins & (r >= s.rb) & (r < s.rb + max(skin, 2.5))
            pv |= r < s.rb
            bond[s.name] = np.where((axn >= a0) & (axn <= a1) & (np.abs(rn - s.rb) <= tol))[0]
        elif s.kind in ("pad", "flange"):
            # disc of thickness `length` from the centre along axis (pad: bottom bumper; flange: bonded face)
            ins = (ax >= a0) & (ax <= a1) & (r <= s.od / 2)
            ps |= ins
            if s.kind == "flange":     # bonded face at ax = a0, plate behind it (ax < a0)
                pv |= ax < a0
                face = (np.abs(axn - a0) <= 0.51 * g.h) & (rn <= s.od / 2)
            else:                      # ground pad: contact face at ax = a1, ground beyond it
                pv |= ax > a1
                face = (np.abs(axn - a1) <= 0.51 * g.h) & (rn <= s.od / 2)
            bond[s.name] = np.where(face)[0]
    ps &= ~pv | ps
    pv &= ~ps
    return ps, pv, bond


def distribute(nc, nodes, F6, origin=np.zeros(3)):
    """Nodal forces (n, 3) on ``nodes`` with resultant F at the node set centroid and moment M about
    ``origin`` transferred to the centroid."""
    P = nc[nodes]
    cen = P.mean(0)
    F, M = np.asarray(F6[:3], float), np.asarray(F6[3:], float)
    Mc = M + np.cross(origin - cen, F)
    r = P - cen
    n = len(nodes)
    I = np.eye(3) * (r * r).sum() - r.T @ r
    try:
        om = np.linalg.solve(I + 1e-9 * np.trace(I) * np.eye(3), Mc)
    except np.linalg.LinAlgError:
        om = np.zeros(3)
    return F / n + np.cross(om, r)


def assemble_loads(spec: LugSpec, g: Grid, bond: dict, keys: list):
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    F = np.zeros((g.ndof, len(keys)))
    for s in spec.sockets:
        if s.role == "anchor":
            nodes = bond[s.name + ":below"] if s.kind == "through" else bond[s.name]
            for d in range(3):
                fixed[3 * nodes + d] = True
    for k, key in enumerate(keys):
        for s in spec.sockets:
            if s.role != "load" and not (s.role == "anchor" and s.kind == "through"):
                continue
            v = s.loads.get(key)
            if v is None:
                continue
            req = spec.case_req.get(key, 1.0)
            nodes = bond[s.name + ":above"] if s.kind == "through" else bond[s.name]
            if len(nodes) == 0:
                continue
            origin = s.center if s.kind in ("pin", "pad", "flange") else np.zeros(3)
            f = distribute(nc, nodes, req * np.asarray(v), origin)
            for d in range(3):
                F[3 * nodes + d, k] += f[:, d]
    F[fixed] = 0.0
    return F, fixed


def severity(spec: LugSpec, key: str) -> float:
    tot = 0.0
    for s in spec.sockets:
        v = s.loads.get(key)
        if v is None:
            continue
        rr = max(s.rb, 5.0)
        tot += np.linalg.norm(v[:3]) + np.linalg.norm(v[3:]) / rr
    return tot * spec.case_req.get(key, 1.0)


def pick_cases(spec: LugSpec, n=3) -> list[str]:
    """Worst load set per case name (over torsos and sides), top n by severity."""
    best = {}
    for key in spec.case_req:
        case = key.split("|")[0]
        sv = severity(spec, key)
        if sv > best.get(case, (0, None))[0]:
            best[case] = (sv, key)
    ranked = sorted(best.values(), key=lambda x: -x[0])
    return [k for sv, k in ranked if sv > 0][:n], [k for sv, k in ranked if sv > 0]


# ----------------------------------------------------------------------------- run + verify
def optimize_lug(spec: LugSpec, variant: str, volfrac: float | None = None, iters=45, log=None):
    var = VARIANTS[variant]
    g = build_domain(spec, var)
    ps, pv, bond = classify(spec, var, g)
    keys, all_keys = pick_cases(spec, 3)
    F, fixed = assemble_loads(spec, g, bond, keys)
    scale = 1.0 / max(np.abs(F).max(), 1e-9)
    rmin = max(1.5, var["min_wall"] / g.h * 1.2)
    pb = SimpProblem(grid=g, loads=F * scale, fixed=fixed, passive_solid=ps, passive_void=pv,
                     volfrac=volfrac or var["volfrac"], rmin_vox=rmin)
    res = run_simp(pb, iters=iters, beta_schedule=(0, 1, 2, 4, 8), beta_every=8, log=log, solver_tol=1e-4)
    return {"grid": g, "ps": ps, "pv": pv, "bond": bond, "keys": keys, "all_keys": all_keys, "simp": res,
            "rmin_vox": rmin, "volfrac": pb.volfrac, "variant": variant}


def fine_solid(spec: LugSpec, var: dict, opt: dict, up: int = 2):
    """Independent re-mesh: density field trilinearly upsampled x``up``, thresholded at 0.5, with the
    exact socket geometry re-imposed at the fine resolution."""
    from scipy import ndimage
    g = opt["grid"]
    xa = g.to_array(opt["simp"].xPhys)
    xf = ndimage.zoom(np.pad(xa, 1, mode="edge"), up, order=1)[up:-up, up:-up, up:-up]
    gf = Grid(xf.shape, g.h / up, g.x0)
    ps, pv, bond = classify(spec, var, gf)
    solid = gf.from_array(xf) >= 0.5
    solid = (solid | ps) & ~pv
    # keep the largest connected component that touches the anchor
    lab, n = ndimage.label(gf.to_array(solid))
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = np.argmax(sizes) + 1
        solid = gf.from_array(lab == keep)
    return gf, solid, bond


def verify_lug(spec: LugSpec, variant: str, opt: dict, up: int = 2, log=None) -> dict:
    """Independent FEA of the thresholded, re-meshed lug under EVERY case (worst load set per case)
    plus the walking-fatigue load set; stresses vs the variant material allowables."""
    var = VARIANTS[variant]
    mat = get_material(var["material"])
    gf, solid, bond = fine_solid(spec, var, opt, up)
    keys = list(opt["all_keys"])
    stat_keys = [k for k in spec.static_keys if k in spec.case_req]
    stat = max(stat_keys, key=lambda k: severity(spec, k)) if stat_keys else None
    keys_run = keys + ([stat] if stat and stat not in keys else [])
    F, fixed = assemble_loads(spec, gf, bond, keys_run)
    # solid-only sub-model
    el = np.where(solid)[0]
    edof = gf.edof[el]
    used = np.unique(gf.enodes[el])
    nmap = -np.ones(gf.nn, np.int64)
    nmap[used] = np.arange(used.size)
    dmap = (nmap[:, None] * 3 + np.arange(3)).ravel()
    edof_s = dmap[edof]
    ndof = used.size * 3
    keepdof = (used[:, None] * 3 + np.arange(3)).ravel()
    Fs = F[keepdof]
    fx = fixed[keepdof]
    E = float(mat.require("youngs_modulus_mpa"))
    nu = float(mat.get("poisson", 0.3))
    KE = ke_h8(gf.h, E, nu)
    asm = Assembler(edof_s, ndof, KE, fx)
    K = asm.assemble(np.ones(el.size))
    coords = gf.node_coords()[used]
    solver = Solver(coords, fx, tol=1e-8, maxiter=800)
    Fs[fx] = 0.0
    U = solver.solve(K, Fs)
    B = b_h8_center(gf.h)
    D = iso_D3(E, nu)
    # exclude elements touching clamped nodes (singular clamp corners stand in for the bonded tube)
    fixed_nodes = np.where(fx.reshape(-1, 3).any(1))[0]
    near = np.isin(nmap[gf.enodes[el]], fixed_nodes).any(1)
    out = {"keys": keys_run, "per_key": {}, "n_solid_fine": int(el.size), "h_fine": gf.h,
           "volume_mm3": float(el.size * gf.h ** 3)}
    for k, key in enumerate(keys_run):
        Ue = U[edof_s, k]
        sig = (D @ B @ Ue.T).T                    # (ne, 6)
        vm = von_mises_3d(sig)
        vmx = vm[~near]
        out["per_key"][key] = {"vm_p99": float(np.percentile(vmx, 99)), "vm_max": float(vmx.max()),
                               "sig": sig, "vm": vm, "req": spec.case_req.get(key, 1.0)}
    out["solid_mask"] = solid
    out["grid"] = gf
    out["near"] = near
    out["el"] = el
    out["static_key"] = stat
    out["U_max"] = float(np.abs(U).max())
    return out


def strength_check(spec: LugSpec, variant: str, ver: dict, fatigue_g: float) -> dict:
    var = VARIANTS[variant]
    mat = get_material(var["material"])
    rows = []
    if variant == "slm_ti":
        allow = float(mat.require("yield_strength_design_mpa"))
        Su = float(mat.require("ultimate_strength_design_mpa"))
        for key, d in ver["per_key"].items():
            rows.append({"key": key, "factor": d["req"], "vm_p99": d["vm_p99"], "vm_max": d["vm_max"],
                         "sf_over_req": allow / d["vm_p99"] if d["vm_p99"] > 0 else np.inf})
        best_dir = None
    else:
        xy = float(mat.require("tensile_strength_xy_mpa")) * 0.8     # ASSUMPTION hot/wet 0.8
        z = float(mat.require("tensile_strength_z_mpa")) * 0.8
        el = ver["el"]
        dirs = {"x": 0, "y": 1, "z": 2}
        res_dir = {}
        for dname, di in dirs.items():
            worst = np.inf
            rr = []
            for key, d in ver["per_key"].items():
                sig = d["sig"][~ver["near"]]
                snn = sig[:, di]
                vm = d["vm"][~ver["near"]]
                s1 = np.percentile(vm, 99) / xy
                s2 = np.percentile(np.maximum(snn, 0), 99) / z
                fi = max(s1, s2)
                rr.append({"key": key, "factor": d["req"], "vm_p99": float(np.percentile(vm, 99)),
                           "snn_p99": float(np.percentile(np.maximum(snn, 0), 99)),
                           "vm_max": float(vm.max()), "sf_over_req": 1 / fi if fi > 0 else np.inf})
                worst = min(worst, rr[-1]["sf_over_req"])
            res_dir[dname] = (worst, rr)
        best_dir = max(res_dir, key=lambda k: res_dir[k][0])
        rows = res_dir[best_dir][1]
        allow, Su = xy, xy
    min_row = min(rows, key=lambda r: r["sf_over_req"])
    out = {"rows": rows, "min_sf_over_req": min_row["sf_over_req"], "governing": min_row["key"],
           "layer_normal": best_dir, "allow": allow}
    # fatigue: 0 -> fatigue_g x static carry (static load set had factor req: remove it), R = 0
    sk = ver.get("static_key")
    if sk:
        d = ver["per_key"][sk]
        smax = d["vm_p99"] / d["req"] * fatigue_g
        sa = sm = smax / 2
        if variant == "slm_ti":
            Se = float(mat.require("fatigue_limit_asbuilt_hip_mpa"))
            sar = sa / max(1 - sm / Su, 1e-3)
            out["fatigue"] = {"smax": smax, "sa_equiv_R-1": sar, "limit": Se, "sf": Se / sar if sar > 0 else np.inf,
                              "basis": "Goodman, as-built surface + HIP, 1e7 limit (conservative for 1e5)"}
        else:
            xy0 = float(mat.require("tensile_strength_xy_mpa"))
            z0 = float(mat.require("tensile_strength_z_mpa"))
            snn = np.percentile(np.maximum(d["sig"][~ver["near"]][:, "xyz".index(best_dir)], 0), 99) / d["req"] * fatigue_g
            fi = max(smax / (0.3 * xy0), snn / (0.3 * z0))
            out["fatigue"] = {"smax": smax, "snn": float(snn), "limit": 0.3 * z0, "sf": 1 / fi if fi > 0 else np.inf,
                              "basis": "ASSUMPTION: 1e5-cycle limit = 0.3 x static strength (XY for von Mises, Z for layer-normal)"}
    return out


# ----------------------------------------------------------------------------- printable mesh
def lug_mesh(spec: LugSpec, variant: str, opt: dict):
    from . import surface
    var = VARIANTS[variant]
    from scipy import ndimage
    g = opt["grid"]
    ps, pv, _ = classify(spec, var, g)
    x = opt["simp"].xPhys.copy()
    # socket skins: the voxel skin (1 voxel >= the real skin) is replaced by the exact analytic sleeve;
    # keep only the attachment pads where the optimized body meets the skin (3x3x3 max of the body)
    skin_kind = np.zeros(g.ne, bool)
    c = g.elem_centers()
    for s in spec.sockets:
        if s.kind in ("end", "through"):
            a0, a1 = socket_ranges(s)
            ax, r = _local(s, c)
            skin_kind |= (ax >= a0) & (ax <= a1) & (r >= s.rb) & (r < s.rb + max(var["skin"], g.h))
    xb = np.where(skin_kind, 0.0, x)
    bridge = g.from_array(ndimage.maximum_filter(g.to_array(xb), size=3))
    x = np.where(skin_kind, np.minimum(bridge, 1.0), x)
    field = g.to_array(x)
    body = surface.field_to_mesh(field, g.h, g.x0)
    adds, subs = [], []
    skin = var["skin"]
    big = 400.0
    for s in spec.sockets:
        a0, a1 = socket_ranges(s, var["skin"])
        if s.kind in ("end", "through"):
            p0 = s.center + a0 * s.axis
            adds.append(surface.cylinder(p0, s.axis, a1 - a0, s.rb + skin))
            if s.kind == "end":
                subs.append(surface.cylinder(s.center + (a0) * s.axis, s.axis, big, s.rb))
            else:
                subs.append(surface.cylinder(s.center - big / 2 * s.axis, s.axis, big, s.rb))
        elif s.kind == "pin":
            adds.append(surface.cylinder(s.center + a0 * s.axis, s.axis, a1 - a0, s.rb + max(skin, 2.5)))
            subs.append(surface.cylinder(s.center - big / 2 * s.axis, s.axis, big, s.rb))
        elif s.kind in ("pad", "flange"):
            adds.append(surface.cylinder(s.center + a0 * s.axis, s.axis, a1 - a0, s.od / 2))
    # trim anything behind the bonded flange / below the pad
    for s in spec.sockets:
        if s.kind == "flange":
            subs.append(surface.cylinder(s.center - big * s.axis, s.axis, big, big / 2))
        elif s.kind == "pad":
            a0, a1 = socket_ranges(s, var["skin"])
            subs.append(surface.cylinder(s.center + a1 * s.axis, s.axis, big, big / 2))
    mesh = surface.boolean_body(body, adds, subs)
    return mesh


def mass_g(mesh, variant):
    rho = float(get_material(VARIANTS[variant]["material"]).require("density_kg_m3"))
    return float(abs(mesh.volume) * rho * 1e-6)
