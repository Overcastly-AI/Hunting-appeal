"""Beam cross-sections.

Local axes: x along the member, y and z in the section plane (see ``frame.py`` for how y/z are
oriented from the reference vector). ``Iy`` is the second moment about local y (bending in the
x-z plane, resisted by ``My``), ``Iz`` about local z.

Isotropic sections carry geometry only; stiffness comes from the member material.
``composite_tube`` carries its own CLT-derived effective stiffness and checks first-ply failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .composite import DEFAULT_KNOCKDOWN, Laminate, Ply, parse_layup


@dataclass
class Section:
    kind: str
    dims: dict
    A: float
    Iy: float
    Iz: float
    J: float
    Wt: float                 # torsion modulus: tau_max = T / Wt
    ymax: float
    zmax: float
    Asy: float = 0.0          # shear areas (only used with Timoshenko elements)
    Asz: float = 0.0
    composite: bool = False

    @property
    def Ip(self) -> float:
        return self.Iy + self.Iz

    def label(self) -> str:
        d = ", ".join(f"{k}={v:g}" for k, v in self.dims.items() if isinstance(v, (int, float)))
        return f"{self.kind}({d})"

    # stiffness from an isotropic material
    def stiffness(self, E: float, G: float) -> dict:
        return {"EA": E * self.A, "EIy": E * self.Iy, "EIz": E * self.Iz, "GJ": G * self.J,
                "GAy": G * (self.Asy or self.A), "GAz": G * (self.Asz or self.A)}

    def stress_points(self, n: int = 24):
        """(y, z) points on the section where normal stress is evaluated."""
        if self.kind == "tube_round":
            r = self.ymax
            th = np.linspace(0, 2 * np.pi, n, endpoint=False)
            return np.c_[r * np.cos(th), r * np.sin(th)]
        y, z = self.ymax, self.zmax
        return np.array([[y, z], [-y, z], [y, -z], [-y, -z]])

    def stresses(self, N, Vy, Vz, T, My, Mz) -> dict:
        """Extreme-fibre axial/bending/torsion stresses and von Mises (conservative combination:
        peak normal stress combined with peak torsion + transverse shear)."""
        pts = self.stress_points()
        sig = N / self.A + My * pts[:, 1] / self.Iy - Mz * pts[:, 0] / self.Iz
        i = int(np.argmax(np.abs(sig)))
        if self.kind == "tube_round":
            tau_v = 2.0 * np.hypot(Vy, Vz) / self.A
        elif self.kind == "flat_bar":
            tau_v = 1.5 * np.hypot(Vy, Vz) / self.A
        elif self.kind == "tube_rect":
            tau_v = max(abs(Vy) / (self.Asy or self.A), abs(Vz) / (self.Asz or self.A))
        else:
            tau_v = 2.0 * np.hypot(Vy, Vz) / self.A
        tau_t = abs(T) / self.Wt
        tau = tau_t + tau_v
        s = sig[i]
        return {"axial": N / self.A, "bending": abs(s - N / self.A), "sigma": s,
                "torsion": tau_t, "tau": tau, "von_mises": float(np.sqrt(s * s + 3 * tau * tau))}


def tube_round(od: float, t: float) -> Section:
    di = od - 2 * t
    if di < 0:
        raise ValueError("wall thicker than radius")
    A = np.pi * (od ** 2 - di ** 2) / 4
    I = np.pi * (od ** 4 - di ** 4) / 64
    J = 2 * I
    return Section("tube_round", {"od": od, "t": t}, A, I, I, J, Wt=J / (od / 2),
                   ymax=od / 2, zmax=od / 2, Asy=A / 2, Asz=A / 2)


def tube_rect(w: float, h: float, t: float) -> Section:
    """Rectangular tube, width ``w`` along local y, height ``h`` along local z."""
    wi, hi = w - 2 * t, h - 2 * t
    A = w * h - wi * hi
    Iy = (w * h ** 3 - wi * hi ** 3) / 12
    Iz = (h * w ** 3 - hi * wi ** 3) / 12
    Am = (w - t) * (h - t)
    J = 4 * Am ** 2 * t / (2 * ((w - t) + (h - t)))     # Bredt-Batho, thin wall
    return Section("tube_rect", {"w": w, "h": h, "t": t}, A, Iy, Iz, J, Wt=2 * Am * t,
                   ymax=w / 2, zmax=h / 2, Asy=2 * t * w, Asz=2 * t * h)


def flat_bar(w: float, t: float) -> Section:
    """Flat bar, width ``w`` along local y, thickness ``t`` along local z."""
    a, b = max(w, t), min(w, t)
    A = w * t
    beta = (1 / 3) * (1 - 0.630 * b / a + 0.052 * (b / a) ** 5)   # Roark, rectangle torsion
    J = beta * a * b ** 3
    Wt = J / b      # tau_max ~ T*b/J (thin rectangle)
    return Section("flat_bar", {"w": w, "t": t}, A, w * t ** 3 / 12, t * w ** 3 / 12, J, Wt=Wt,
                   ymax=w / 2, zmax=t / 2, Asy=5 * A / 6, Asz=5 * A / 6)


def generic(A: float, Iy: float, Iz: float, J: float, ymax: float = 1.0, zmax: float = 1.0,
            Wt: float | None = None) -> Section:
    return Section("generic", {"A": A, "Iy": Iy, "Iz": Iz, "J": J}, A, Iy, Iz, J,
                   Wt=Wt or J / max(ymax, zmax), ymax=ymax, zmax=zmax, Asy=A / 2, Asz=A / 2)


# ----------------------------------------------------------------------------- composite tube
@dataclass
class CompositeTube(Section):
    laminate: Laminate = None
    layup_str: str = ""
    Ex: float = 0.0
    Gxy: float = 0.0
    density_kg_m3: float = 0.0
    knockdown: dict = field(default_factory=lambda: dict(DEFAULT_KNOCKDOWN))
    criterion: str = "tsai_wu"

    def stiffness(self, E=None, G=None) -> dict:
        """CLT-derived effective stiffness (membrane homogenisation of the wall laminate)."""
        return {"EA": self.Ex * self.A, "EIy": self.Ex * self.Iy, "EIz": self.Ex * self.Iz,
                "GJ": self.Gxy * self.J, "GAy": self.Gxy * self.A / 2, "GAz": self.Gxy * self.A / 2}

    def failure(self, N, Vy, Vz, T, My, Mz, knockdown=None, criterion=None, n: int = 24) -> dict:
        """First-ply failure of the tube wall at ``n`` points around the circumference.

        Wall running loads at mean radius Rm (thin-wall, statically determinate within the section):
          Nx  = t * (N/A + (My z - Mz y)/I)  evaluated at the mean radius
          Nxy = T / (2 pi Rm^2)  +  transverse-shear flow V sin(phi)/(pi Rm)
          Ny  = 0 (no hoop load; local crushing at clamps/joints is NOT covered here)
        """
        kd = self.knockdown if knockdown is None else knockdown
        crit = criterion or self.criterion
        Rm = self.dims["od"] / 2 - self.laminate.thickness / 2
        t = self.laminate.thickness
        q_t = T / (2 * np.pi * Rm ** 2)
        best = {"fi": 0.0}
        for th in np.linspace(0, 2 * np.pi, n, endpoint=False):
            y, z = Rm * np.cos(th), Rm * np.sin(th)
            sx = N / self.A + My * z / self.Iy - Mz * y / self.Iz
            # shear flow from Vy peaks at y=0 (sin), from Vz at z=0
            q_v = (Vy * np.sin(th) - Vz * np.cos(th)) / (np.pi * Rm)
            Nx, Nxy = sx * t, q_t + q_v
            r = self.laminate.first_ply_failure((Nx, 0.0, Nxy), (0, 0, 0), kd, crit)
            if r["fi"] > best["fi"]:
                best = dict(r, theta_deg=float(np.degrees(th)), Nx=Nx, Nxy=Nxy)
        best["sf"] = 1 / best["fi"] if best["fi"] > 0 else np.inf
        return best


def composite_tube(od: float, layup, material_id, ply_t: float | None = None,
                   knockdown: dict | None = None, criterion: str = "tsai_wu") -> CompositeTube:
    """Composite tube from a layup (angles from the tube axis) and a UD ply material.

    ``material_id`` may be a DB id, a :class:`Ply`, or an inline property dict with the contract
    composite keys (E1_mpa, E2_mpa, G12_mpa, nu12, Xt_mpa, Xc_mpa, Yt_mpa, Yc_mpa, S_mpa,
    ply_thickness_mm, density_kg_m3).
    """
    ply = material_id if isinstance(material_id, Ply) else Ply.from_material(material_id, ply_t)
    if ply_t is not None:
        ply.t = ply_t
    lam = Laminate.from_layup(layup, ply)
    t = lam.thickness
    di = od - 2 * t
    if di <= 0:
        raise ValueError("laminate thicker than tube radius")
    A = np.pi * (od ** 2 - di ** 2) / 4
    I = np.pi * (od ** 4 - di ** 4) / 64
    J = 2 * I
    eng = lam.engineering()
    return CompositeTube("composite_tube", {"od": od, "t": t, "n_plies": len(lam.angles)}, A, I, I, J,
                         Wt=J / (od / 2), ymax=od / 2, zmax=od / 2, Asy=A / 2, Asz=A / 2,
                         composite=True, laminate=lam,
                         layup_str=str(layup) if isinstance(layup, str) else str(parse_layup(layup)),
                         Ex=eng["Ex"], Gxy=eng["Gxy"], density_kg_m3=ply.density_kg_m3,
                         knockdown=dict(DEFAULT_KNOCKDOWN) if knockdown is None else knockdown,
                         criterion=criterion)


def from_spec(spec) -> Section:
    """Build a section from a dict like {"type": "tube_round", "od": 12.7, "t": 0.9}."""
    if isinstance(spec, Section):
        return spec
    s = dict(spec)
    typ = s.pop("type")
    fn = {"tube_round": tube_round, "tube_rect": tube_rect, "flat_bar": flat_bar,
          "composite_tube": composite_tube, "generic": generic}[typ]
    return fn(**s)
