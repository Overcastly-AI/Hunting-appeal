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
    "adhesive_t_mm": 0.15,       # ASSUMPTION: glass-bead controlled bondline
    "adhesive": "epoxy_adhesive_toughened",
    "hot_wet": 0.8,
    "sleeve_Et_n_mm": None,      # adherend 2 axial stiffness per width; None -> equal to tube
    "sleeve_Gt_n_mm": None,
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
               params: dict | None = None) -> BondResult:
    p = {**DEFAULT_JOINT, **(params or {})}
    adh = get_material(p["adhesive"])
    Ga = float(adh.get("shear_modulus_mpa") or adh.require("youngs_modulus_mpa") / (2 * (1 + adh.get("poisson", 0.4))))
    tau_s = float(adh.get("lap_shear_strength_mpa") or adh.require("shear_strength_mpa"))
    L, ta = p["overlap_mm"], p["adhesive_t_mm"]
    E2t = p["sleeve_Et_n_mm"] or tube_Et
    G2t = p["sleeve_Gt_n_mm"] or tube_Gt

    def factor(a1, a2):
        om = np.sqrt(Ga / ta * (1 / a1 + 1 / a2))
        return volkersen_factor(om * L, min(a1, a2) / max(a1, a2)), om

    k_ax, om = factor(tube_Et, E2t)
    k_t, _ = factor(tube_Gt, G2t)
    n_max = abs(N) / (2 * np.pi * r) + abs(M) / (np.pi * r * r)
    q_t = abs(T) / (2 * np.pi * r * r)
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


def check_frame_joints(result, joints: list[dict]) -> list[dict]:
    """Check every bonded tube end listed in ``joints`` against the solved ``result``.

    joints: [{"id": "J_top_L", "node": "SL_top", "members": ["top_0", "SL_17"], "params": {...}}]
    """
    mem_by_id = {m["id"]: (i, m) for i, m in enumerate(result.members)}
    mdefs = {str(md.get("id", i)): md for i, md in enumerate(result.model["members"])}
    out = []
    from .sections import from_spec
    for j in joints:
        for mid in j["members"]:
            i, summ = mem_by_id[mid]
            md = mdefs[mid]
            sec = from_spec(md["section"])
            f = summ["end_forces"][0] if md["nodes"][0] == j["node"] else summ["end_forces"][1]
            N, Vy, Vz, T, My, Mz = f
            Et, Gt = tube_wall_stiffness(sec, md.get("material"))
            r = sec.dims["od"] / 2
            br = bond_check(N, T, float(np.hypot(My, Mz)), r, Et, Gt, j.get("params"))
            out.append({"joint": j["id"], "member": mid, "N": N, "T": T, "M": float(np.hypot(My, Mz)),
                        **br.as_dict()})
    return out
