"""Bonded tube-to-node (sleeve / socket / lap) joint checks.

Model: a tube of radius ``r`` (bond surface radius) bonded over overlap length ``L`` into a socket
(or over a spigot) with an adhesive layer of thickness ``ta`` and shear modulus ``Ga``.

Average bond shear (thin tube, load carried as axial line load around the circumference):
  axial line load   n(theta) = N/(2 pi r) + M cos(theta)/(pi r^2)   -> n_max = |N|/(2 pi r) + |M|/(pi r^2)
  torsion shear flow q_t     = T/(2 pi r^2)
  tau_avg = sqrt((n_max/L)^2 + (q_t/L)^2)

Volkersen shear-lag peak factor (linear-elastic adhesive, no peel):
  omega^2 = (Ga/ta) * (1/(E1 t1) + 1/(E2 t2))          (E t = adherend axial stiffness per unit width)
  psi = (E t)_min / (E t)_max
  tau_max / tau_avg = (omega L / (1+psi)) * (psi + cosh(omega L)) / sinh(omega L)
which reduces to (omega L/2) coth(omega L/2) for balanced adherends. The torsional factor uses
G t of the adherends in the same expression.

ASSUMPTIONS (state in reports):
- Transverse shear at the socket goes into bearing at the socket lip, not bond shear; peel from
  bending is not modelled (keep socket lips tapered / chamfered).
- Design allowable on *average* shear = adhesive lap-shear strength x hot/wet 0.8 (SF >= 2 req'd).
- The Volkersen peak vs the same lap-shear strength is reported as an information check
  (SF_peak >= 1 means the elastic peak stays below the strength); toughened epoxies yield and
  redistribute, so the average-shear SF governs.
- Effective load-transfer length ~ 3/omega from each end; overlap beyond ~ 6/omega adds little.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .materials_bridge import get_material

DEFAULT_JOINT = {
    "overlap_mm": 25.0,          # ASSUMPTION: 2x tube OD socket depth
    "adhesive_t_mm": None,       # None -> record bondline_thickness_mm, else 0.15 (ASSUMPTION)
    "adhesive": "adhesive_epoxy_toughened_2part",
    "adhesive_G_mpa": 800.0,     # ASSUMPTION if the record has no shear/Young's modulus
    "cfrp_adherend": False,      # True -> use lap_shear_strength_cfrp_mpa when available
    "hot_wet": 0.8,
    "sleeve_Et_n_mm": None,      # adherend 2 axial stiffness per width; None -> from sleeve material
    "sleeve_Gt_n_mm": None,
    "sleeve_material": "alu_7075_t6",   # hub socket / through-sleeve (hard-anodised, glass-bead bondline)
    "sleeve_t_mm": 1.0,
}


@dataclass
class BondResult:
    tau_avg: float
    tau_peak: float
    k_axial: float
    k_torsion: float
    allow: float
    sf_avg: float
    sf_peak: float
    omega: float
    effective_length_mm: float

    def as_dict(self):
        return self.__dict__.copy()


def volkersen_factor(omega_L: float, psi: float = 1.0) -> float:
    x = float(omega_L)
    if x < 1e-6:
        return 1.0
    if x > 50:   # avoid overflow: cosh/sinh -> 1
        return x / (1 + psi)
    return x / (1 + psi) * (psi + np.cosh(x)) / np.sinh(x)


def bond_check(N: float, T: float, M: float, r: float, tube_Et: float, tube_Gt: float,
               params: dict | None = None, geom: dict | None = None) -> BondResult:
    """``geom`` (optional, for non-round tubes): {"perim", "Am", "ky", "kz"} with the axial line
    load n_max = |N|/perim + ky|My| + kz|Mz| and torsion flow T/(2 Am); then ``M`` must be a
    (My, Mz) tuple."""
    p = {**DEFAULT_JOINT, **(params or {})}
    try:
        adh = get_material(p["adhesive"])
    except KeyError:
        adh = get_material("epoxy_adhesive_toughened")
    if adh.get("shear_modulus_mpa"):
        Ga = float(adh.get("shear_modulus_mpa"))
    elif adh.get("youngs_modulus_mpa"):
        Ga = float(adh.get("youngs_modulus_mpa")) / (2 * (1 + adh.get("poisson", 0.4)))
    else:
        Ga = float(p["adhesive_G_mpa"])
    tau_s = None
    if p["cfrp_adherend"]:
        tau_s = adh.get("lap_shear_strength_cfrp_mpa")
    tau_s = float(tau_s or adh.get("lap_shear_strength_mpa") or adh.require("shear_strength_mpa"))
    L = p["overlap_mm"]
    ta = p["adhesive_t_mm"] or adh.get("bondline_thickness_mm") or 0.15
    E2t, G2t = p["sleeve_Et_n_mm"], p["sleeve_Gt_n_mm"]
    if (E2t is None or G2t is None) and p.get("sleeve_material"):
        from .materials_bridge import E_of, G_of
        sm = get_material(p["sleeve_material"])
        E2t = E2t or E_of(sm) * p["sleeve_t_mm"]
        G2t = G2t or G_of(sm) * p["sleeve_t_mm"]
    E2t = E2t or tube_Et
    G2t = G2t or tube_Gt

    def factor(a1, a2):
        om = np.sqrt(Ga / ta * (1 / a1 + 1 / a2))
        return volkersen_factor(om * L, min(a1, a2) / max(a1, a2)), om

    k_ax, om = factor(tube_Et, E2t)
    k_t, _ = factor(tube_Gt, G2t)
    if geom is None:
        n_max = abs(N) / (2 * np.pi * r) + abs(float(np.hypot(*M)) if np.ndim(M) else M) / (np.pi * r * r)
        q_t = abs(T) / (2 * np.pi * r * r)
    else:
        My, Mz = M
        n_max = abs(N) / geom["perim"] + geom["ky"] * abs(My) + geom["kz"] * abs(Mz)
        q_t = abs(T) / (2 * geom["Am"])
    tau_avg = float(np.hypot(n_max / L, q_t / L))
    tau_peak = float(np.hypot(k_ax * n_max / L, k_t * q_t / L))
    allow = tau_s * p["hot_wet"]
    return BondResult(tau_avg, tau_peak, k_ax, k_t, allow,
                      allow / tau_avg if tau_avg > 0 else np.inf,
                      allow / tau_peak if tau_peak > 0 else np.inf,
                      float(om), float(3 / om))


def tube_wall_stiffness(section, material=None) -> tuple[float, float]:
    """(E t, G t) per unit circumference of a tube wall."""
    t = section.dims["t"]
    if getattr(section, "composite", False):
        return section.Ex * t, section.Gxy * t
    from .materials_bridge import E_of, G_of
    m = get_material(material)
    return E_of(m) * t, G_of(m) * t


def bond_geometry(section) -> dict | None:
    """Bond-line geometry for a tube section (None -> round formula with r = od/2)."""
    if "od" in section.dims:
        return None
    w, h, t = section.dims["w"], section.dims["h"], section.dims["t"]
    return {"perim": 2 * (w + h), "Am": w * h, "ky": (h / 2) * t / section.Iy,
            "kz": (w / 2) * t / section.Iz}


def bond_area(section, overlap):
    if "od" in section.dims:
        return np.pi * section.dims["od"] * overlap
    return 2 * (section.dims["w"] + section.dims["h"]) * overlap


def check_frame_joints(result, joints: list[dict]) -> list[dict]:
    """Check every bonded tube end / through-sleeve listed in ``joints`` against ``result``.

    joints: [{"id": "corner_L", "node": "SL9", "members": ["top_0", "SL_8"],      # bonded ends
              "through": [["SL_2", "SL_3"]],                                    # optional sleeves
              "params": {...}}]
    A through-sleeve transfers the jump in stay internal forces across the hub
    (member above at its start minus member below at its end).
    """
    mem_by_id = {m["id"]: (i, m) for i, m in enumerate(result.members)}
    mdefs = {str(md.get("id", i)): md for i, md in enumerate(result.model["members"])}
    out = []
    from .sections import from_spec

    def _end(mid, node):
        _, summ = mem_by_id[mid]
        md = mdefs[mid]
        return summ["end_forces"][0] if md["nodes"][0] == node else summ["end_forces"][1]

    def _check(kind, mid, f, prm_j):
        md = mdefs[mid]
        sec = from_spec(md["section"])
        N, Vy, Vz, T, My, Mz = f
        Et, Gt = tube_wall_stiffness(sec, md.get("material"))
        prm = {"cfrp_adherend": bool(getattr(sec, "composite", False)), **(prm_j or {})}
        if kind == "through" and prm.get("through_overlap_mm"):
            prm["overlap_mm"] = prm["through_overlap_mm"]
        g = bond_geometry(sec)
        r = sec.dims.get("od", 0) / 2
        br = bond_check(N, T, (My, Mz), r, Et, Gt, prm, g)
        return {"kind": kind, "member": mid, "N": float(N), "T": float(T),
                "M": float(np.hypot(My, Mz)), **br.as_dict()}

    for j in joints:
        for mid in j.get("members", []):
            out.append({"joint": j["id"], **_check("end", mid, _end(mid, j["node"]), j.get("params"))})
        for below, above in j.get("through", []):
            f = np.asarray(_end(above, j["node"])) - np.asarray(_end(below, j["node"]))
            out.append({"joint": j["id"], **_check("through", above, f, j.get("params"))})
    return out
