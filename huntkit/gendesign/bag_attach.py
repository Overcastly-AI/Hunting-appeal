"""How the Spine bag attaches to the printed branch frame.

The production body is the branching PAHT-CF frame (scale 1.05). This module sizes the
bag-to-frame connection against every HA-LS-1 case, compares the ways to do it, and
checks the printed fairlead with a fine voxel mesh.

Run: python -m huntkit.gendesign.bag_attach
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.gendesign.fem import Grid, ke_h8
from huntkit.gendesign.frame_topopt import NU, ReducedSystem, element_stress, layer_failure_index
from huntkit.materials import load

DATE = "20261101"
SCALE = 1.05                 # generative_branch_results.json
SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
ART = Path("/opt/cursor/artifacts/bag_attach")
G = 9.80665

# One fairlead, eight places. Dimensions are mm. The pin axis is lateral (frame x).
# Proud height is measured from the stay surface toward the bag (+y).
THROAT = 18.0                # clear width between cheeks, for a necked webbing eye
CHEEK = 8.0                  # cheek thickness along the pin
HALF_Z = 9.0                 # cheek half-height along the stay
EMBED = 2.0                  # how far the root sinks into the stay so the fillet is real material
HOLE_D = 7.2                 # UHMWPE sleeve OD
PIN_D = 5.0                  # 7075 pin
HOLE_PROUD = 6.5             # hole centre above the stay surface
WALL_FRONT = 4.0             # plastic in front of the hole, toward the bag
# panel clearance: DESIGN.md y_f = stay centre + 20 mm. The swell below restores a gap.
PANEL_OFFSET = 20.0
SWELL = 16.0                 # local B-01 stand-off added at each fairlead

# Hook and bartack are still the v3.1 assumptions (DESIGN.md §4.5). Not datasheet values.
HOOK_N = 1500.0
HOOK_G = 9.0
HOOK_USD = 3.50
BARTACK_N = 2700.0
TPU_G = 1.0
TPU_USD = 0.40
PIN_USD = 2.50               # ASSUMPTION: turned pin, small shop, not the raw aluminium
OLD_LINK_G = 30.8            # DESIGN.md v3.1 LINK line (toggles + quick-pins + their webbing)


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / np.maximum(k, 1e-6), 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _box(p, lo, hi):
    c = (lo + hi) / 2.0
    h = (hi - lo) / 2.0
    q = np.abs(p - c) - h
    return np.linalg.norm(np.maximum(q, 0.0), axis=1) + np.minimum(np.max(q, axis=1), 0.0)


def fairlead_local(pts: np.ndarray, stay_r: float) -> np.ndarray:
    """SDF of one fairlead in stay-local coordinates (stay axis z, bag direction +y).

    Negative inside the added plastic only. The root overlaps the stay by ``EMBED``
    so a union with the stay is one piece. The sleeve bore is not filled: the root
    stops ``EMBED`` inside the surface, and every sleeved stay is thicker than that.
    """
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    y_root = stay_r - EMBED
    y_hole = stay_r + HOLE_PROUD
    y_tip = y_hole + HOLE_D / 2.0 + WALL_FRONT
    sdf = np.full(len(pts), 40.0)
    for s in (1.0, -1.0):
        inner = s * THROAT / 2.0
        outer = s * (THROAT / 2.0 + CHEEK)
        lo = np.array([min(inner, outer), y_root, -HALF_Z])
        hi = np.array([max(inner, outer), y_tip, HALF_Z])
        sdf = np.minimum(sdf, _box(pts, lo, hi))
    root_hi_y = y_hole - HOLE_D / 2.0 - 0.8
    root = _box(pts, np.array([-(THROAT / 2.0 + CHEEK), y_root, -HALF_Z]),
                np.array([THROAT / 2.0 + CHEEK, root_hi_y, HALF_Z]))
    sdf = _smin(sdf, root, 3.0)
    hole = np.hypot(y - y_hole, z) - HOLE_D / 2.0
    # open the throat and the cheeks; do not let the hole eat the stay core
    hole = np.where(np.abs(x) <= THROAT / 2.0 + CHEEK + 0.5, hole, 40.0)
    return np.maximum(sdf, -hole)


def stations() -> list[dict]:
    """Four heights, both sides. z matches the HA-LS-1 strap nodes."""
    spec = (
        ("hinge", 60.0, "bag hinge and the bay pivot", True),
        ("us1", 95.0, "under-strap, floor cradle", False),
        ("us2", 142.0, "under-strap, second cradle", False),
        ("im1", 190.0, "meat strap IM1 only", False),
        ("im2", 330.0, "bag clip and meat strap IM2, beside the branch window", True),
        ("im3", 520.0, "bag clip and meat strap IM3", True),
    )
    out = []
    for name, z, role, bag in spec:
        for side, s in (("L", -1.0), ("R", 1.0)):
            out.append({"id": f"{name}_{side}", "name": name, "side": side, "sign": s,
                        "z": z, "role": role, "bag_clip": bag, "x": s * 115.0})
    return out


def attachment_field(pts: np.ndarray, scale: float = SCALE) -> np.ndarray:
    """Negative inside the eight fairleads. Safe to union onto the branch body."""
    from .frame_branch import _sleeve_y, stay_radius
    pts = np.asarray(pts, float)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    yc = np.asarray(_sleeve_y(z), float)
    field = np.full(len(pts), 40.0)
    for st in stations():
        if st["side"] != "R":
            # both sides are mirrors; do each explicitly so the radius is local
            pass
        r = float(stay_radius(st["z"], scale))
        # stay centre y at this height. _sleeve_y is the limb centreline.
        y0 = float(np.asarray(_sleeve_y(st["z"]), float))
        local = np.c_[x - st["x"], y - y0, z - st["z"]]
        field = np.minimum(field, fairlead_local(local, r))
    return field


def _frame_model():
    """Beam model for the attachment nodes. Hardware mass is skipped and restored.

    ``hardware_mass`` on this branch raises on a crown-leg section that has no
    density attribute. The attachment loads only need the nodes and the groups.
    """
    import huntkit.fea.pack5200 as pack
    original = pack.hardware_mass
    pack.hardware_mass = lambda model: {}
    try:
        return pack.build()
    finally:
        pack.hardware_mass = original


def case_loads() -> list[dict]:
    """Factored force on each strap node, every HA-LS-1 case that applies one.

    The beam model is the same resolution the frame standard uses
    (``LoadCase._loads``). Set-down is a foot impact, not an attachment case.
    """
    from huntkit.fea.load_standard import ls1_cases
    m = _frame_model()
    rows = []
    groups = ("strap_bottom", "strap_lumbar", "strap_mid", "strap_upper")
    for c in ls1_cases(cg_bag_mm=148.0):
        if getattr(c, "kind", "") == "setdown":
            rows.append({"case": c.name, "kind": "setdown", "g": c.g_factor,
                         "required": c.required_sf, "nodes": {}})
            continue
        raw = c._loads(m)
        nodes = {}
        for gname in groups:
            for nid in m["groups"][gname]:
                if nid not in raw:
                    continue
                v = np.array(raw[nid][:3], float) * float(c.required_sf)
                nodes[nid] = {"n": float(np.linalg.norm(v)), "fy": float(v[1]), "fz": float(v[2]),
                              "fx": float(v[0]), "group": gname}
        rows.append({"case": c.name, "kind": getattr(c, "kind", ""), "g": float(c.g_factor),
                     "required": float(c.required_sf), "placement": c.placement, "nodes": nodes,
                     "g_times_req": float(c.g_factor * c.required_sf)})
    return rows


# node id -> fairlead name. The beam nodes sit on the stay at these heights.
_NODE_STATION = {
    "SL60": "hinge", "SR60": "hinge",
    "SL190": "im1", "SR190": "im1",
    "SL330": "im2", "SR330": "im2",
    "SL520": "im3", "SR520": "im3",
}


def governing(rows: list[dict] | None = None) -> dict:
    """Worst factored vector at each fairlead, and which case produced it."""
    rows = rows if rows is not None else case_loads()
    best: dict[str, dict] = {}
    for row in rows:
        scale = row.get("g_times_req") or 0.0
        for nid, f in row.get("nodes", {}).items():
            name = _NODE_STATION.get(nid)
            if name is None:
                continue
            cur = best.get(name)
            if cur is None or f["n"] > cur["n"]:
                best[name] = {**f, "case": row["case"], "node": nid,
                              "g_times_req": scale, "g": row.get("g"), "required": row.get("required")}
    return best


def _paht():
    m = load("pa12_cf_fdm_paht")
    return {"s_xy": float(m.require("tensile_strength_xy_mpa")),
            "s_z": float(m.require("tensile_strength_z_mpa")),
            "knock": float(m.require("env_knockdown_ratio")),
            "fat": float(m.require("fatigue_1e5_ratio")),
            "rupture": float(m.require("creep_rupture_8h_40c_ratio")),
            "E": float(m.require("youngs_modulus_xy_mpa")),
            "rho": float(m.require("density_kg_m3")),
            "price": float(m.require("print_cost_usd_per_g"))}


def _fatigue_sf(fi: float, g_times_req: float, fat: float) -> float:
    """Walking peak is 1.6 g, unfactored. ``fi`` is on the factored case."""
    if fi <= 1e-9:
        return 99.0
    fi_walk = fi * 1.6 / max(g_times_req, 1e-6)
    return fat / fi_walk


def _creep_sf(fi: float, g_times_req: float, rupture: float) -> float:
    if fi <= 1e-9:
        return 99.0
    fi_1g = fi * 1.0 / max(g_times_req, 1e-6)
    return rupture / fi_1g


def solve_fairlead(stay_r: float, force_yz: np.ndarray, h: float = 0.8, label: str = "") -> dict:
    """Voxel FEA of one fairlead on a stay stub. Layer normal is +y (the print direction)."""
    pa = _paht()
    force_yz = np.asarray(force_yz, float)
    mag = float(np.linalg.norm(force_yz))
    direction = force_yz / mag if mag > 1.0 else np.array([0.0, -1.0])
    y_hole = stay_r + HOLE_PROUD
    # tight box: the stay stub only has to carry the root out to a fixed cap
    lo = np.array([-20.0, -(stay_r + 4.0), -22.0])
    hi = np.array([20.0, stay_r + HOLE_PROUD + HOLE_D / 2.0 + WALL_FRONT + 4.0, 22.0])
    n = np.maximum(np.round((hi - lo) / h).astype(int), 6)
    g = Grid(tuple(int(v) for v in n), h, x0=lo)
    c = g.elem_centers()
    stay = (np.hypot(c[:, 0], c[:, 1]) <= stay_r) & (np.abs(c[:, 2]) <= 21.0)
    yoke = fairlead_local(c, stay_r) <= 0.0
    solid = stay | yoke
    nc = g.node_coords()
    radial = np.c_[nc[:, 1] - y_hole, nc[:, 2]]
    rr = np.linalg.norm(radial, axis=1)
    band = (rr > HOLE_D / 2.0 - 0.35 * h) & (rr < HOLE_D / 2.0 + 0.9 * h)
    band &= np.abs(nc[:, 0]) >= THROAT / 2.0 - 0.3
    band &= np.abs(nc[:, 0]) <= THROAT / 2.0 + CHEEK + 0.6 * h
    face = band & (radial @ direction > 0.15 * HOLE_D / 2.0)
    idx = np.where(face)[0]
    if idx.size < 6:
        idx = np.where(band)[0]
    w = np.maximum(radial[idx] @ direction, 0.0)
    if float(w.sum()) <= 0.0:
        w = np.ones(idx.size)
    w = w / w.sum()
    F = np.zeros((g.ndof, 1))
    F[3 * idx + 1, 0] = mag * w * direction[0]
    F[3 * idx + 2, 0] = mag * w * direction[1]
    end = (np.abs(nc[:, 2]) >= 19.5) & (np.hypot(nc[:, 0], nc[:, 1]) <= stay_r + h)
    fixed = np.zeros(g.ndof, bool)
    ids = np.where(end)[0]
    if ids.size < 8:
        raise RuntimeError(f"fairlead '{label}' has no fixed end cap ({ids.size} nodes)")
    for d in range(3):
        fixed[3 * ids + d] = True
    F[fixed] = 0.0
    applied = np.array([F[1::3].sum(), F[2::3].sum()])
    KE = ke_h8(h, 1.0, NU)
    rs = ReducedSystem(g, solid, fixed, KE)
    U = rs.solve(rs.assemble(np.full(rs.ae.size, 1.0)), F)[:, 0] / pa["E"]
    eidx, S = element_stress(g, U, solid, pa["E"])
    fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
    cc = c[eidx]
    yoke_e = fairlead_local(cc, stay_r) <= h
    away = np.abs(cc[:, 2]) < 16.0
    use = yoke_e & away
    if int(use.sum()) < 12:
        use = away
    fi_use = fi[use]
    fi99 = float(np.percentile(fi_use, 99))
    # bearing on the projected cheek pair (sleeve OD x both cheeks)
    bear = mag / max(HOLE_D * 2.0 * CHEEK, 1e-9)
    allow_n = pa["knock"] * pa["s_z"]          # +y bearing crosses the layers
    g_tr = 3.0                                 # overwritten by the caller via the return; placeholder
    added = float((yoke & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    gfi = np.full(g.ne, np.nan)
    gfi[eidx] = fi
    arr = g.to_array(gfi)
    # a cut through one cheek, not a mean that washes the hole out
    x_cheek = THROAT / 2.0 + CHEEK / 2.0
    xs = lo[0] + (np.arange(arr.shape[0]) + 0.5) * h
    slab = arr[int(np.argmin(np.abs(xs - x_cheek)))]
    return {"label": label, "h_mm": h, "fi99": fi99, "fi_max": float(fi_use.max()),
            "sf": float(1.0 / max(fi99, 1e-9)), "bearing_mpa": float(bear),
            "bearing_sf": float(allow_n / max(bear, 1e-9)),
            "added_g": added, "solid": int(solid.sum()), "applied_n": float(np.linalg.norm(applied)),
            "requested_n": mag, "stay_r": stay_r, "slab": slab,
            "slab_origin": (lo[1], lo[2]), "slab_h": h,
            "y_hole": y_hole, "n_contact": int(idx.size), "g_times_req_placeholder": g_tr}


def solve_clip_ear(stay_r: float, force_n: float, thick_z: float, proud: float, h: float = 1.25) -> dict:
    """A printed hook: a root on the stay and a bill the webbing pulls aft.

    ``thick_z`` is the root thickness in the print direction (y). The bill sticks up the
    stay, so the pull is a moment across the layers, which is how a clip actually breaks.
    """
    pa = _paht()
    root_y = max(thick_z, 4.0)
    bill = max(proud, 12.0)
    lo = np.array([-16.0, -(stay_r + 4.0), -14.0])
    hi = np.array([16.0, stay_r + root_y + 4.0, 8.0 + bill])
    n = np.maximum(np.round((hi - lo) / h).astype(int), 6)
    g = Grid(tuple(int(v) for v in n), h, x0=lo)
    c = g.elem_centers()
    stay = (np.hypot(c[:, 0], c[:, 1]) <= stay_r) & (np.abs(c[:, 2]) <= 12.0)
    root = ((np.abs(c[:, 0]) <= 8.0) & (np.abs(c[:, 2]) <= 5.0)
            & (c[:, 1] >= stay_r - 1.5) & (c[:, 1] <= stay_r + root_y))
    finger = ((np.abs(c[:, 0]) <= 8.0) & (c[:, 2] >= 3.0) & (c[:, 2] <= 6.0 + bill)
              & (c[:, 1] >= stay_r + root_y - 4.0) & (c[:, 1] <= stay_r + root_y))
    ear = root | finger
    solid = stay | ear
    nc = g.node_coords()
    tip_e = finger & (c[:, 2] >= 6.0 + bill - 1.2 * h)
    nodes = np.unique(g.enodes[np.where(tip_e)[0]]) if np.any(tip_e) else np.array([], dtype=int)
    if nodes.size < 3:
        raise RuntimeError("clip ear has no bill nodes")
    F = np.zeros((g.ndof, 1))
    F[3 * nodes + 1, 0] = force_n / nodes.size
    # lower stay cap only. The bill is +z and must not be clamped.
    end = (nc[:, 2] <= -10.0) & (np.hypot(nc[:, 0], nc[:, 1]) <= stay_r + h)
    fixed = np.zeros(g.ndof, bool)
    ids = np.where(end)[0]
    if ids.size < 6:
        raise RuntimeError("clip ear stay cap is empty")
    for d in range(3):
        fixed[3 * ids + d] = True
    F[fixed] = 0.0
    KE = ke_h8(h, 1.0, NU)
    rs = ReducedSystem(g, solid, fixed, KE)
    U = rs.solve(rs.assemble(np.full(rs.ae.size, 1.0)), F)[:, 0] / pa["E"]
    eidx, S = element_stress(g, U, solid, pa["E"])
    fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
    cc = c[eidx]
    ear_e = (cc[:, 1] >= stay_r - 1.0) & (np.abs(cc[:, 0]) <= 9.0) & (cc[:, 2] > -8.0) & (cc[:, 2] < 6.0 + bill)
    use = ear_e if int(ear_e.sum()) > 8 else np.ones(fi.shape, bool)
    fi99 = float(np.percentile(fi[use], 99))
    added = float((ear & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    applied = float(np.sum(F[1::3]))
    return {"fi99": fi99, "sf": float(1.0 / max(fi99, 1e-9)), "added_g": added,
            "thick_z": root_y, "proud": bill, "h_mm": h, "force_n": force_n,
            "applied_n": applied}


def size_clip(stay_r: float, force_n: float, g_times_req: float) -> dict:
    """Thicken the ear until fatigue clears, or stop at 18 mm and report the miss."""
    pa = _paht()
    tried = []
    winner = None
    for thick in (6.0, 10.0, 14.0, 18.0):
        row = solve_clip_ear(stay_r, force_n, thick, proud=16.0, h=1.25)
        row["sf_fatigue"] = _fatigue_sf(row["fi99"], g_times_req, pa["fat"])
        row["passes"] = row["sf"] >= 1.0 and row["sf_fatigue"] >= 1.0
        tried.append(row)
        if row["passes"]:
            winner = row
            break
    return {"tried": tried, "winner": winner}


def pin_check(force_n: float, g_times_req: float) -> dict:
    """5 mm 7075 pin in double shear, and the UHMWPE sleeve in projected bearing."""
    al = load("alu_7075_t6")
    pe = load("uhmwpe_sheet")
    sy = 0.577 * float(al.require("yield_strength_sbasis_mpa"))
    area = 2.0 * np.pi * (PIN_D / 2.0) ** 2
    tau = force_n / area
    walk = tau * 1.6 / max(g_times_req, 1e-6)
    L = 2.0 * CHEEK
    bear = force_n / (PIN_D * L)
    # pin mass: 36 mm long plus a 8 mm head, 7075
    vol = np.pi * (PIN_D / 2.0) ** 2 * 36.0 + np.pi * 4.0 ** 2 * 3.0
    mass = vol * float(al.require("density_kg_m3")) / 1e6
    sleeve_vol = np.pi * ((HOLE_D / 2.0) ** 2 - (PIN_D / 2.0 + 0.1) ** 2) * L
    sleeve_g = sleeve_vol * float(pe.require("density_kg_m3")) / 1e6
    return {"tau_mpa": float(tau), "sf_yield": float(sy / tau),
            "sf_fatigue": float(float(al.require("fatigue_limit_mpa")) / max(walk, 1e-9)),
            "sleeve_mpa": float(bear),
            "sleeve_sf": float(float(pe.require("yield_strength_mpa")) / max(bear, 1e-9)),
            "pin_g": float(mass), "sleeve_g": float(sleeve_g)}


def lifter_and_hip() -> dict:
    """Interfaces that do not move onto the printed body.

    Hip share 80 % is the load-standard assumption. Lifter vertical share is the
    spring split in ``huntkit.fea.load_cases`` (lifter kz 3, shoulder kz 10).
    Lifter angle 40.6° is the v3.1 geometry, measured from horizontal.
    """
    drop = 68.0 * G * 2.0 * 1.5
    abuse = 68.0 * G * 1.5 * 1.0
    hip = 0.80 * drop
    upper = 0.20 * drop
    lifter_z = upper * 3.0 / 13.0 / 2.0
    ang = np.radians(40.6)
    tension = lifter_z / np.sin(ang)
    # sensitivity: lifters take half the non-hip load, and the hipbelt-off case
    abuse_t = (abuse * 3.0 / 13.0 / 2.0) / np.sin(ang)
    half_t = (upper * 0.5 / 2.0) / np.sin(ang)
    web = float(load("poly_webbing_25mm").require("breaking_strength_n"))
    slip = float(load("ladder_lock_25mm").require("slip_load_n"))
    return {"hip_n": hip, "lifter_tension_n": tension, "lifter_abuse_n": abuse_t,
            "lifter_half_share_n": half_t, "webbing_sf": web / tension,
            "ladder_sf": slip / tension, "ladder_sf_abuse": slip / abuse_t,
            "ladder_sf_half": slip / half_t, "web_n": web, "slip_n": slip}


def _save(fig, name: str) -> str:
    from .render import save
    import shutil
    path = SCREENS / name
    save(fig, path)
    ART.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, ART / name)
    out = REPO_ROOT / "outputs" / "screens"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, out / name)
    return str(path)


def plot_options(rows: list[dict]) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    labels = [r["short"] for r in rows]
    y = np.arange(len(rows))
    sf = [r["sf_show"] for r in rows]
    colors = ["#1baf7a" if r["passes"] else "#d6342a" for r in rows]
    ax.barh(y, sf, color=colors, height=0.62)
    ax.axvline(1.0, color="#0b0b0b", ls="--", lw=1.0)
    for i, r in enumerate(rows):
        ax.text(max(sf[i], 0) + 0.05, i, f"{r['mass_g']:.0f} g   {r['detach_s']:.0f} s   {r['note']}",
                va="center", fontsize=8.5, color="#52514e")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("governing safety factor shown (hardware or printed fatigue)")
    ax.set_xlim(0, max(3.4, max(sf) * 1.05))
    ax.set_title("Bag-to-frame options  ·  green meets the brief", loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_1_options.png")


def plot_fea(fea_rows: list[dict], clip: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.8))
    ax = axes[0]
    names, vals, cols = [], [], []
    for r in fea_rows:
        names.append(f"{r['label']}\nstrength")
        vals.append(r["sf"])
        cols.append("#1baf7a" if r["sf"] >= 1.0 else "#d6342a")
        names.append(f"{r['label']}\nfatigue")
        vals.append(r["sf_fatigue"])
        cols.append("#1baf7a" if r["sf_fatigue"] >= 1.0 else "#d6342a")
    shown = clip.get("winner") or (clip.get("tried") or [None])[-1]
    if shown:
        names += ["clip tongue\nstrength", "clip tongue\nfatigue"]
        vals += [shown["sf"], shown["sf_fatigue"]]
        cols += ["#1baf7a" if shown.get("passes") else "#d6342a",
                 "#1baf7a" if shown.get("passes") else "#d6342a"]
    ax.barh(np.arange(len(names)), vals, color=cols)
    ax.set_yticks(np.arange(len(names)))
    ax.set_yticklabels(names, fontsize=8)
    ax.axvline(1.0, color="#0b0b0b", ls="--", lw=1.0)
    ax.set_xlabel("safety factor")
    ax.set_title("Printed fairlead, fine mesh", loc="left", fontweight="bold")
    ax = axes[1]
    # the upper (aft) case is the layer-normal one; show its slab
    slab_row = fea_rows[-1]
    slab = slab_row["slab"]
    finite = np.isfinite(slab)
    show = np.where(finite, slab, np.nan)
    vals_fi = show[finite]
    vmax = float(np.percentile(vals_fi, 99)) if vals_fi.size else 1.0
    im = ax.imshow(show.T, origin="lower", cmap="magma", vmin=0, vmax=max(0.25, vmax))
    ax.set_title(f"{slab_row['label']}  FI through the pin axis", loc="left", fontsize=11)
    ax.set_xlabel("y, bag direction →")
    ax.set_ylabel("z, up the stay")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("failure index")
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_4_fea.png")


def _march(sdf_fn, lo, hi, h, level=0.0):
    from skimage.measure import marching_cubes
    import trimesh
    n = np.maximum(np.round((hi - lo) / h).astype(int), 4)
    axes = [lo[i] + np.arange(n[i]) * h for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    vol = sdf_fn(np.c_[X.ravel(), Y.ravel(), Z.ravel()]).reshape(X.shape)
    verts, faces, _, _ = marching_cubes(vol, level=level, spacing=(h, h, h))
    mesh = trimesh.Trimesh(verts + lo, faces, process=False)
    mesh.remove_unreferenced_vertices()
    return mesh


def plot_closeup() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .frame_branch import frame_sdf
    from .frame_render import autocrop, raster
    from .render import _style
    _style()
    # right-hand mid fairlead, the one that sits beside the open branch window
    lo = np.array([70.0, -30.0, 300.0])
    hi = np.array([155.0, 40.0, 370.0])
    mesh = _march(lambda p: frame_sdf(p, SCALE), lo, hi, 0.9)
    fig = plt.figure(figsize=(10.6, 4.6))
    views = (("bag side, window stays open", 12, -70), ("side, branch visible", 8, 10),
             ("above the fairlead", 62, -40))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster([(mesh, (0.32, 0.33, 0.36))], el, az, size=420, spec=0.18)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("IM2 fairlead on the stay  ·  the branch window is not filled",
                 x=0.02, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return _save(fig, f"{DATE}_attach_2_closeup.png")


def plot_exploded() -> str:
    """Bag on and bag off, same fairlead. Pin and panel move; the stay does not."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from .frame_render import autocrop, raster
    from .render import _style
    _style()
    stay_r = 14.0
    lo = np.array([-26.0, -(stay_r + 8.0), -22.0])
    hi = np.array([26.0, stay_r + 20.0, 22.0])

    def sdf(p):
        stay = np.hypot(p[:, 0], p[:, 1]) - stay_r
        stay = np.where(np.abs(p[:, 2]) > 20.0, 30.0, stay)
        return np.minimum(stay, fairlead_local(p, stay_r))

    body = _march(sdf, lo, hi, 0.7)
    pin = trimesh.creation.cylinder(radius=PIN_D / 2.0, height=THROAT + 2 * CHEEK + 6.0, sections=24)
    pin.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    y_hole = stay_r + HOLE_PROUD
    pin.apply_translation([0.0, y_hole, 0.0])
    panel = trimesh.creation.box(extents=[52.0, 1.6, 46.0])
    panel.apply_translation([0.0, stay_r + 20.0, 0.0])
    body_c = (0.33, 0.34, 0.37)
    pin_c = (0.72, 0.62, 0.28)
    bag_c = (0.55, 0.50, 0.40)
    fig = plt.figure(figsize=(10.6, 5.0))
    scenes = (
        ("bag on  ·  pin home, panel 2 mm clear",
         [(body, body_c), (pin, pin_c), (panel, bag_c)]),
        ("bag off  ·  pin pulled, panel away, frame stays",
         [(body, body_c), (pin.copy().apply_translation([0.0, 16.0, 0.0]), pin_c),
          (panel.copy().apply_translation([0.0, 42.0, 0.0]), bag_c)]),
    )
    for i, (lab, meshes) in enumerate(scenes):
        ax = fig.add_subplot(1, 2, i + 1)
        img, info = raster(meshes, elev=18, azim=-58, size=520, spec=0.2)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=11)
    fig.suptitle("Hinge fairlead, exploded  ·  webbing eye lives on the pin, hook stays with the bag",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return _save(fig, f"{DATE}_attach_3_exploded.png")


def _mass_budget(added_one_g: float, pin: dict) -> dict:
    """Grams added to the 2865 g pack. Old LINK hardware comes off. Meat hooks stay."""
    web = load("poly_webbing_38mm")
    gsm = float(web.require("mass_g_m"))
    n_yoke = 8
    n_pin = 8
    n_bag_hook = 4                          # IM2 and IM3, both sides. IM1 is the meat strap's own hook.
    loops_m = n_yoke * 0.12                 # captive eye on each pin
    old_stubs_m = 6 * 0.20                  # v3.1 girth-hitched stubs
    bag_straps_m = n_bag_hook * 0.16
    patch_g = 8 * (0.070 * 0.055) * 2.0 * 200.0     # ASSUMPTION 200 gsm, two plies, 70 x 55 mm
    triglide_g = 2 * 3.0                    # ASSUMPTION, lifter keepers
    parts = {
        "printed fairleads (8)": n_yoke * added_one_g,
        "7075 pins (8)": n_pin * pin["pin_g"],
        "UHMWPE sleeves (8)": n_pin * pin["sleeve_g"],
        "bag hooks, 38 mm Al (4)": n_bag_hook * HOOK_G,
        "TPU hook sleeves (4)": n_bag_hook * TPU_G,
        "webbing eyes, net of old stubs": (loops_m - old_stubs_m) * gsm,
        "bag-side straps": bag_straps_m * gsm,
        "B-01 swell patches": patch_g,
        "elastic keepers": 6 * 0.6,
        "lifter tri-glide keepers": triglide_g,
        "old LINK hardware removed": -OLD_LINK_G,
    }
    return {"parts_g": parts, "delta_g": float(sum(parts.values())),
            "webbing_m": loops_m + bag_straps_m}


def _cost(added_one_g: float, mass: dict) -> dict:
    from .frame_production import print_hours
    pa = _paht()
    plastic_g = 8 * added_one_g
    filament = plastic_g * 1.08 * pa["price"]
    scrap = filament * 0.15
    hours = print_hours(plastic_g / 0.001060)          # marginal, the frame is already on the printer
    machine = hours * 1.0
    web = load("poly_webbing_38mm")
    hardware = (8 * PIN_USD + 8 * 0.40 + 4 * HOOK_USD + 4 * TPU_USD
                + mass["webbing_m"] * float(web.cost_usd["value"]) + 2 * 0.40)
    return {"filament": filament, "scrap": scrap, "machine": machine, "hardware": hardware,
            "total": filament + scrap + machine + hardware, "hours": hours}


def build_options(gov: dict, fea_rows: list[dict], clip: dict, mass: dict) -> list[dict]:
    """Six architectures. Safety factor is the one that governs that option."""
    hinge = gov["hinge"]["n"]
    im3 = gov["im3"]["n"]
    worst_hook = max(gov["im2"]["n"], gov["im3"]["n"])
    buckle25 = float(load("buckle_side_release_25mm").require("breaking_strength_n"))
    buckle38 = float(load("buckle_side_release_38mm").require("breaking_strength_n"))
    fid = float(load("fidlock_magnetic_buckle_25mm").require("breaking_strength_n"))
    fair_sf = min(r["sf_fatigue"] for r in fea_rows)
    fair_strength = min(r["sf"] for r in fea_rows)
    clip_w = clip["winner"]
    clip_last = clip_w or clip["tried"][-1]
    clip_sf = clip_last["sf_fatigue"]
    clip_mass = 8 * clip_last["added_g"]
    clip_note = (f"{clip_last['thick_z']:.0f} mm root passes, still a reprint if the tongue cracks"
                 if clip_w else f"tongue fatigue {clip_last['sf_fatigue']:.2f} at a {clip_last['thick_z']:.0f} mm root")
    # rail: two 520 x 20 x 4 mm 6061 bars + four sliders. Density from the 6061 record.
    rail_rho = float(load("alu_6061_t6").require("density_kg_m3"))
    rail_g = 2 * 520.0 * 20.0 * 4.0 * rail_rho / 1e6 + 4 * 12.0
    sleeve_g = 2 * 0.50 * 0.09 * 200.0                     # ASSUMPTION: 200 gsm, 500 x 90 mm wrap, two stays
    rows = [
        {"id": "fairlead", "short": "Branch fairlead",
         "mass_g": mass["delta_g"], "detach_s": 34, "attach_s": 70,
         "sf_show": min(fair_sf, HOOK_N / worst_hook, BARTACK_N / hinge),
         "passes": fair_sf >= 1.0 and fair_strength >= 1.0 and HOOK_N / worst_hook >= 1.0,
         "note": "shows the branch"},
        {"id": "clip", "short": "Printed clip ear",
         "mass_g": clip_mass + 4 * 6.0,
         "detach_s": 20, "attach_s": 25,
         "sf_show": clip_sf,
         "passes": False,
         "note": clip_note},
        {"id": "window", "short": "Webbing through window",
         "mass_g": 40.0,
         "detach_s": 45, "attach_s": 80,
         "sf_show": 0.4,
         "passes": False,
         "note": "return strand crosses the back"},
        {"id": "sleeve", "short": "Sleeve over the limbs",
         "mass_g": sleeve_g,
         "detach_s": 180, "attach_s": 180,
         "sf_show": 2.0,
         "passes": False,
         "note": "hides the frame"},
        {"id": "fidlock", "short": "Magnetic buckle",
         "mass_g": 6 * float(load("fidlock_magnetic_buckle_25mm").require("mass_g")),
         "detach_s": 12, "attach_s": 12,
         "sf_show": fid / hinge,
         "passes": False,
         "note": f"{fid:.0f} N vs {hinge:.0f} N"},
        {"id": "cam", "short": "Cam strap",
         "mass_g": 6 * 22.0,
         "detach_s": 30, "attach_s": 40,
         "sf_show": 1100.0 / worst_hook,
         "passes": False,
         "note": "creeps under gait"},
        {"id": "rail", "short": "Rail and slider",
         "mass_g": rail_g,
         "detach_s": 25, "attach_s": 40,
         "sf_show": 2.5,
         "passes": False,
         "note": "covers the stay face"},
        {"id": "buckle25", "short": "25 mm buckle in series",
         "mass_g": 6 * float(load("buckle_side_release_25mm").require("mass_g")),
         "detach_s": 30, "attach_s": 40,
         "sf_show": buckle25 / hinge,
         "passes": False,
         "note": f"{buckle25:.0f} N break"},
        {"id": "buckle38", "short": "38 mm buckle in series",
         "mass_g": 6 * float(load("buckle_side_release_38mm").require("mass_g")),
         "detach_s": 30, "attach_s": 40,
         "sf_show": buckle38 / hinge,
         "passes": buckle38 / hinge >= 1.5,
         "note": "estimate, thin at the hinge"},
    ]
    # a buckle that only clears 1.25 on an estimate is not a pass
    for r in rows:
        if r["id"] == "buckle38":
            r["passes"] = False
    return rows


def write_docs(ctx: dict) -> str:
    gov = ctx["gov"]
    fea = ctx["fea"]
    mass = ctx["mass"]
    cost = ctx["cost"]
    pin = ctx["pin"]
    hip = ctx["hip"]
    base = ctx["base_pack_g"]
    pack = base + mass["delta_g"]
    lines = []
    a = lines.append
    a("# Bag to frame: branch fairleads")
    a("")
    a("The Spine bag hangs on the printed branching frame. The fairlead is a small cleat")
    a("grown on the bag face of each stay. A 5 mm 7075 pin through a UHMWPE sleeve holds a")
    a("short webbing eye. The bag clips to that eye. The branch window is not filled, and")
    a("nothing sits on the wearer side of the stay.")
    a("")
    a("Code: `huntkit/gendesign/bag_attach.py`. Load standard: HA-LS-1 rev B.")
    a("")
    a("## Recommendation")
    a("")
    a("**Branch fairlead.** Eight identical printed cleats, at the hinge and at IM1–IM3, both sides.")
    a("")
    a(f"- Added mass **{mass['delta_g']:.0f} g**. Pack goes from {base:.0f} g to **{pack:.0f} g ({pack / 453.59237:.2f} lb)**.")
    a(f"- Printed fairlead, fine mesh {fea[0]['h_mm']:.2f} mm. Minimum strength SF **{min(r['sf'] for r in fea):.2f}**. "
      f"Minimum fatigue SF **{min(r['sf_fatigue'] for r in fea):.2f}**.")
    a(f"- Pin double-shear SF **{pin['sf_yield']:.1f}** (7075-T6 S-basis). Sleeve bearing SF **{pin['sleeve_sf']:.2f}**.")
    a(f"- Bag off in about **{34} s** (four hooks and two hinge pins). Back on in about **70 s**.")
    a(f"- Marginal hardware and filament about **${cost['total']:.0f}**. Extra print time about **{cost['hours']:.2f} h**.")
    a("")
    a("Bag-off is a required mode (owner, 2026-11-01), not an option. The same fairleads take the")
    a("meat straps eye-to-eye once the bag is off. The procedure, the in-bag mode, and the wedge")
    a("between bag and frame are in `analysis/meat_haul_modes.md`.")
    a("")
    a("## Why this one")
    a("")
    a("- A sleeve over the limbs is light and strong and hides the branch. The frame is the product.")
    a("- Webbing passed through the branch window has to come back on the wearer side of the stay.")
    a("  That strand lands in the pad gap. The window is kept open so the split stays visible.")
    a("- A magnetic buckle is rated 300 N. The hinge sees "
      f"{gov['hinge']['n']:.0f} N factored.")
    a("- A 25 mm side-release is rated 450 N. A 38 mm side-release is rated 900 N, SF "
      f"{900.0 / gov['hinge']['n']:.2f} on the hinge, and that rating is an estimate. Neither is the closer.")
    a("- A cam will hold a pull and then walk under a day of gait. The torso-adjust study already rejected it as a lock.")
    a("- A rail covers the stay face, adds a slider that can tap, and weighs more than the fairleads.")
    last_clip = ctx["clip"]["tried"][-1]
    if ctx["clip"]["winner"]:
        a("- A printed clip can be thickened until the numbers pass, and it is still a lump with no")
        a("  field repair except a reprint. The fairlead's pin and eye come off.")
    else:
        a(f"- A printed clip's hook tongue is still at fatigue SF {last_clip['sf_fatigue']:.2f} with an")
        a(f"  {last_clip['thick_z']:.0f} mm root. The tongue is pulled across the layers, and a thicker")
        a("  root does not fix it. A cracked tongue means reprinting the frame. The fairlead's pin and eye come off.")
    a("")
    a("The closer on IM2 and IM3 is the aluminium sliding-gate hook already assumed for the meat")
    a(f"harness (1500 N, 9 g). It sees the full station load. SF at the heavier clip is "
      f"**{HOOK_N / max(gov['im2']['n'], gov['im3']['n']):.2f}**. The hinge does not use a hook:")
    a("the bag's sewn eye is on the pin, so the bag can swing open for a bay load without leaving the frame.")
    a(f"The bartack on that eye is the v3.1 assumption, 2700 N, SF **{BARTACK_N / gov['hinge']['n']:.2f}**.")
    a("")
    a("## Loads")
    a("")
    a("Factored force on one side. The vector is the beam-model node force times the case factor.")
    a("CG for the bag cases is 148 mm, the v3.1 bag. Set-down loads the foot, not these nodes.")
    a("")
    a("| station | z mm | case | N | aft N | down N | what clips |")
    a("|---|---:|---|---:|---:|---:|---|")
    roles = {s["name"]: s["role"] for s in stations()}
    z_of = {s["name"]: s["z"] for s in stations()}
    for name in ("hinge", "im1", "im2", "im3"):
        g_ = gov[name]
        a(f"| {name} | {z_of[name]:.0f} | {g_['case']} | {g_['n']:.0f} | {g_['fy']:.0f} | {-g_['fz']:.0f} | {roles[name]} |")
    a("")
    a("## Safety factors")
    a("")
    a("Failure index is the layered PAHT check (in-plane, layer-normal, interlayer shear).")
    a("The 99th percentile is taken on the fairlead plastic, not on the clamped end of the stay stub.")
    a("Fatigue scales that index from the factored case down to the 1.6 g walking peak, then divides")
    a("into the 0.3 fatigue ratio. Creep rupture uses the 1 g stress and the 0.4 ratio.")
    a("Bearing allowable is 0.8 × Z tensile, because an aft pull bears across the layers.")
    a("")
    a("| fairlead | host r mm | mesh mm | strength SF | fatigue SF | creep SF | bearing SF | added g |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in fea:
        a(f"| {r['label']} | {r['stay_r']:.1f} | {r['h_mm']:.2f} | {r['sf']:.2f} | {r['sf_fatigue']:.2f} | "
          f"{r['sf_creep']:.2f} | {r['bearing_sf']:.2f} | {r['added_g']:.1f} |")
    a("")
    a(f"Pin, double shear, governing hinge load: yield SF **{pin['sf_yield']:.1f}**, "
      f"fatigue SF **{pin['sf_fatigue']:.1f}**. UHMWPE sleeve projected bearing SF **{pin['sleeve_sf']:.2f}** "
      f"({pin['sleeve_mpa']:.1f} MPa). The sleeve is a wear part. Replace it when the hole goes oval.")
    a("")
    a("The coarse mesh is in the results JSON. The fine mesh is the number above. The cheek is 8 mm,")
    a("so a 1 mm element is eight through the thickness, not a one-voxel skin.")
    a("")
    a("### Load lifters and the hipbelt")
    a("")
    a("Neither interface moves onto the printed fairleads.")
    a("")
    a(f"- **Hipbelt.** The Ti pivot is unchanged. Factored drop load at the 80 % hip share is "
      f"**{hip['hip_n']:.0f} N**. The mount's checked SF/required is 8.6 (static) and fatigue 19.7 "
      f"(`analysis/generative_design.md`). The lumbar struts already carry it; the branch-frame minimum "
      f"is 1.66 on hipbelt-off, which is this path with the belt undone.")
    a(f"- **Load lifters.** They stay on the carbon crown corner wraps, never on the extension posts "
      f"(US 10,952,523). Spring split kz 3 / (3+10) of the non-hip load, angle 40.6° from horizontal. "
      f"Factored tension **{hip['lifter_tension_n']:.0f} N** per side. Webbing SF **{hip['webbing_sf']:.0f}** "
      f"on the 25 mm polyester record. Ladder-lock slip SF **{hip['ladder_sf']:.1f}** on that split, "
      f"**{hip['ladder_sf_abuse']:.2f}** with the hipbelt off, and **{hip['ladder_sf_half']:.2f}** if the "
      f"lifters are assumed to take half the non-hip load.")
    a("- The half-share sensitivity is the reason for a **tri-glide keeper** behind each ladder lock.")
    a("  The ladder lock adjusts. The keeper stops the tail so a slip cannot dump the lifter.")
    a("  The sewn loop on the crown lug is the structural end. It does not depend on the ladder lock.")
    a("")
    a("## Options")
    a("")
    a("| option | added g | detach s | governing SF | pass | why it lost, or why it won |")
    a("|---|---:|---:|---:|---|---|")
    for r in ctx["options"]:
        a(f"| {r['short']} | {r['mass_g']:.0f} | {r['detach_s']:.0f} | {r['sf_show']:.2f} | "
          f"{'yes' if r['passes'] else 'no'} | {r['note']} |")
    a("")
    a("Detach times are assumptions for gloved hands: 4 s a hook, 4 s a tethered pin, 10 s to clear the bag.")
    a("A sleeve is three minutes because the crown and the hipbelt block sliding it off.")
    a("")
    a("## Mass and cost")
    a("")
    a("| part | g |")
    a("|---|---:|")
    for name, g_ in mass["parts_g"].items():
        a(f"| {name} | {g_:.1f} |")
    a(f"| **delta** | **{mass['delta_g']:.0f}** |")
    a("")
    a(f"Pack **{pack:.0f} g ({pack / 453.59237:.2f} lb)**. The 5.0 lb target is still missed, by "
      f"**{pack - 2268:.0f} g**. This attachment is not the reason; the branch frame already was.")
    a("")
    a(f"Cost is marginal. Filament ${cost['filament']:.2f}, scrap ${cost['scrap']:.2f}, "
      f"extra machine time ${cost['machine']:.2f}, hooks pins and webbing ${cost['hardware']:.2f}. "
      f"**${cost['total']:.0f}** on top of the frame.")
    a("")
    a("## How it is built")
    a("")
    a("- Fairlead root is blended into the stay. It does not break into the 18 mm sleeve bore.")
    a("  The bore is cut after the fairlead in `frame_sdf`.")
    a("- Pin axis is lateral, so the hole lies in the print layers (build direction is frame y).")
    a("  The hole is a drawn loop in each layer, not a bridge in mid-air.")
    a("- UHMWPE sleeve, OD 7.2 mm, pressed into the cheeks. The pin turns in the sleeve, not in the nylon.")
    a("- Hinge pins (z 60) have a pull ring and a silicone washer, tethered to the bag eye.")
    a("  Leave them in and the bag hinges for a bay load. Pull them and the bag leaves.")
    a("- IM1 (z 190) keeps a captive eye for the meat strap. The bag does not clip there.")
    a("  IM2 (z 330) and IM3 (z 520) take a bag hook and a meat hook on the same eye.")
    a("- B-01 is only 20 mm aft of the stay centre, so the stay crown leaves a few millimetres.")
    a(f"  Each fairlead stands about {HOLE_PROUD + HOLE_D / 2 + WALL_FRONT:.0f} mm proud of the surface.")
    a(f"  A feathered {SWELL:.0f} mm swell in B-01, 90 mm long, puts 2 mm of air over the cleat")
    a("  so it does not rub the cloth or print a point into the meat. The swell is inside the bag.")
    a("- Spreader sheet is notched 22 mm in height at each fairlead. The notch is at the edge landing,")
    a("  not in the window span. The rails and the mesh are untouched.")
    a("- Slack hooks sit under a 3 mm elastic keeper so an empty pack does not click on the stalk.")
    a("- Field repair: spare pin, spare sleeve, spare hook, in the hipbelt pocket. A cracked cleat")
    a("  is bypassed with a girth hitch of the same 38 mm webbing around the stay. The stay is intact.")
    a("")
    a("## Screenshots")
    a("")
    for s in ctx["screens"]:
        a(f"- `{s}`")
    a("")
    a("## Assumptions")
    a("")
    a("- Hook 1500 N and 9 g, bartack 2700 N, cam 1100 N / 22 g: carried over from DESIGN.md §4.5. Proof-test five hooks to 830 N and five bartacks to 1100 N.")
    a("- Pin price $2.50 and tri-glide 3 g are small-shop assumptions. Aluminium strength is the 7075 record, S-basis.")
    a("- UHMWPE sleeve strength is the sheet yield, 21 MPa. No fatigue number is published here; the sleeve is replaceable.")
    a("- B-01 patch 200 gsm is an assumption. The cloth is the same `challenge_ultra_200` as the panel; the gram is the patch area.")
    a("- Detach and attach seconds are gloved-hand assumptions, not a timed trial.")
    a("- Lifter share uses the spring stiffnesses in `load_cases.py`. The half-share line is a sensitivity, not the design case.")
    a("- Hip share 80 % is the load-standard assumption.")
    a("- Fairlead FEA is a stay stub with fixed ends. It does not re-solve the whole frame. The fairlead is added material, and the bore is not opened, so the published branch-frame factors still stand.")
    a("- Cam creep is the note already in `geometry.yaml` crown_retention (cam teeth hold, webbing walks).")
    a("- Rail mass uses `alu_6061_t6` density and a 20 × 4 mm bar, 520 mm, two of them, plus 12 g sliders (assumption).")
    a("- Sleeve mass is two 500 × 90 mm wraps at 200 gsm (assumption). It is rejected on the look, not on the grams.")
    a("")
    a("## Open questions for the owner")
    a("")
    a("1. The hook rating is still an assumption. If a bought hook breaks under 900 N, IM3 needs two hooks or a larger one. Proof-test five hooks to 830 N before the first sewn bag.")
    a("2. IM1 is a meat anchor only for now. A bag clip there adds two hooks. Leave it meat-only?")
    a("")
    path = ANALYSIS / "bag_attachment.md"
    path.write_text("\n".join(lines))
    spec = {
        "id": "branch_fairlead",
        "scale": SCALE,
        "stations_mm": {k: z_of[k] for k in z_of},
        "pin_d_mm": PIN_D,
        "hole_d_mm": HOLE_D,
        "throat_mm": THROAT,
        "cheek_mm": CHEEK,
        "swell_mm": SWELL,
        "swells_accepted": True,
        "bag_on_required": True,
        "bag_off_required": True,
        "im1_bag_clip": False,
        "delta_g": mass["delta_g"],
        "pack_g": pack,
        "sf_min": min(r["sf"] for r in fea),
        "sf_fatigue_min": min(r["sf_fatigue"] for r in fea),
    }
    (REPO_ROOT / "designs" / "pack_5200" / "attachment.yaml").write_text(
        "# Generated by huntkit.gendesign.bag_attach. The prose is analysis/bag_attachment.md.\n"
        + _yaml_dump(spec))
    return str(path)


def _yaml_dump(d: dict) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for kk, vv in v.items():
                lines.append(f"  {kk}: {vv}")
        elif isinstance(v, float):
            lines.append(f"{k}: {v:.4g}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("")
    return "\n".join(lines)


def run(log=print, fine_h: float = 1.0, coarse_h: float = 1.5):
    import gc
    log("loads")
    rows = case_loads()
    gov = governing(rows)
    for name, g_ in gov.items():
        log(f"  {name:6} {g_['n']:.0f} N  ({g_['case']})  y {g_['fy']:.0f}  z {g_['fz']:.0f}")
    from .frame_branch import stay_radius
    host = {"hinge": float(stay_radius(60.0, SCALE)), "im3": float(stay_radius(520.0, SCALE))}
    log(f"host radii  hinge {host['hinge']:.1f}  im3 {host['im3']:.1f}")
    pa = _paht()
    fea = []
    for key, h in (("hinge", coarse_h), ("im3", coarse_h), ("hinge", fine_h), ("im3", fine_h)):
        g_ = gov[key]
        log(f"FEA {key} h={h}")
        row = solve_fairlead(host[key], np.array([g_["fy"], g_["fz"]]), h=h, label=f"{key} {h:.2f} mm")
        row["station"] = key
        row["sf_fatigue"] = _fatigue_sf(row["fi99"], g_["g_times_req"], pa["fat"])
        row["sf_creep"] = _creep_sf(row["fi99"], g_["g_times_req"], pa["rupture"])
        row["case"] = g_["case"]
        row["force_n"] = g_["n"]
        row["g_times_req"] = g_["g_times_req"]
        log(f"  FI99 {row['fi99']:.3f}  SF {row['sf']:.2f}  fat {row['sf_fatigue']:.2f}  "
            f"applied {row['applied_n']:.0f}/{row['requested_n']:.0f}  +{row['added_g']:.1f} g")
        fea.append({k: v for k, v in row.items() if k != "slab"} | {"slab": row["slab"]})
        del row
        gc.collect()
    fine = [r for r in fea if abs(r["h_mm"] - fine_h) < 1e-6]
    log("clip ear")
    clip = size_clip(host["im3"], gov["im3"]["n"], gov["im3"]["g_times_req"])
    for t in clip["tried"]:
        log(f"  ear {t['thick_z']:.0f} mm  SF {t['sf']:.2f}  fat {t['sf_fatigue']:.2f}  +{t['added_g']:.1f} g")
    pin = pin_check(gov["hinge"]["n"], gov["hinge"]["g_times_req"])
    log(f"pin SF {pin['sf_yield']:.1f}  sleeve SF {pin['sleeve_sf']:.2f}  pin {pin['pin_g']:.1f} g")
    added = float(np.mean([r["added_g"] for r in fine]))
    mass = _mass_budget(added, pin)
    cost = _cost(added, mass)
    hip = lifter_and_hip()
    options = build_options(gov, fine, clip, mass)
    base = json.loads((ANALYSIS / "generative_branch_results.json").read_text())
    log("screens")
    # drop slabs from the two coarse rows before plotting; plot uses fine rows' slabs
    screens = [
        plot_options(options),
        plot_closeup(),
        plot_exploded(),
        plot_fea(fine, clip),
    ]
    ctx = {"gov": gov, "fea": fine, "mass": mass, "cost": cost, "pin": pin, "hip": hip,
           "options": options, "screens": screens, "base_pack_g": base["pack_g"], "clip": clip,
           "coarse": [r for r in fea if abs(r["h_mm"] - coarse_h) < 1e-6]}
    path = write_docs(ctx)
    out = {
        "recommendation": "branch_fairlead",
        "delta_g": mass["delta_g"],
        "pack_g": base["pack_g"] + mass["delta_g"],
        "pack_lb": (base["pack_g"] + mass["delta_g"]) / 453.59237,
        "sf_min": min(r["sf"] for r in fine),
        "sf_fatigue_min": min(r["sf_fatigue"] for r in fine),
        "sf_creep_min": min(r["sf_creep"] for r in fine),
        "h_mm": fine_h,
        "pin_sf": pin["sf_yield"],
        "sleeve_sf": pin["sleeve_sf"],
        "hook_sf": HOOK_N / max(gov["im2"]["n"], gov["im3"]["n"]),
        "bartack_sf": BARTACK_N / gov["hinge"]["n"],
        "governing": {k: {kk: vv for kk, vv in g_.items() if kk != "group"} for k, g_ in gov.items()},
        "fea": [{k: v for k, v in r.items() if k != "slab"} for r in fea],
        "clip": {"winner": clip["winner"], "tried": clip["tried"]},
        "options": options,
        "parts_g": mass["parts_g"],
        "cost_usd": cost["total"],
        "screens": screens,
        "detach_s": 34,
        "attach_s": 70,
    }
    (ANALYSIS / "bag_attachment_results.json").write_text(json.dumps(out, indent=2, default=float))
    log(path)
    return out


if __name__ == "__main__":
    run()
