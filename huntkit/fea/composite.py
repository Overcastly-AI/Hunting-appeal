"""Classical lamination theory (CLT), ply stresses and first-ply failure.

Conventions: ply angle in degrees measured from the laminate x axis (for a tube: the tube axis).
Units: MPa, mm, N/mm (running loads), N (moments per width: N*mm/mm).
Engineering shear strain gamma_xy is used throughout.

Failure indices are *inverse strength ratios*: FI = 1/R where R is the load multiplier to
first-ply failure. FI < 1 is safe, SF = 1/FI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from .materials_bridge import Mat, get_material

# ASSUMPTION (agent role spec): environmental knockdown 0.8 on all strengths (hot/wet), and
# barely-visible impact damage knockdown 0.65 on compressive strengths.
DEFAULT_KNOCKDOWN = {"hot_wet": 0.80, "impact_comp": 0.65}


@dataclass
class Ply:
    E1: float
    E2: float
    G12: float
    nu12: float
    Xt: float
    Xc: float
    Yt: float
    Yc: float
    S: float
    t: float = 0.125
    density_kg_m3: float = 1550.0
    name: str = "ply"

    @property
    def nu21(self):
        return self.nu12 * self.E2 / self.E1

    @classmethod
    def from_material(cls, ref, ply_t: float | None = None) -> "Ply":
        m: Mat = get_material(ref)
        r = m.require
        return cls(E1=r("E1_mpa"), E2=r("E2_mpa"), G12=r("G12_mpa"), nu12=r("nu12"),
                   Xt=r("Xt_mpa"), Xc=abs(r("Xc_mpa")), Yt=r("Yt_mpa"), Yc=abs(r("Yc_mpa")),
                   S=r("S_mpa"), t=float(ply_t or m.get("ply_thickness_mm", 0.125)),
                   density_kg_m3=float(m.get("density_kg_m3", 1550.0)), name=m.id)

    def knocked_down(self, kd: dict | None) -> "Ply":
        if not kd:
            return self
        hw = kd.get("hot_wet", 1.0)
        ic = kd.get("impact_comp", 1.0)
        return Ply(self.E1, self.E2, self.G12, self.nu12, self.Xt * hw, self.Xc * hw * ic,
                   self.Yt * hw, self.Yc * hw * ic, self.S * hw, self.t, self.density_kg_m3,
                   self.name + "(kd)")


# ----------------------------------------------------------------------------- layups
def parse_layup(layup) -> list[float]:
    """Expand a layup to a full list of ply angles (bottom to top).

    Accepts a list of numbers, or a string like ``"[0,±45,0,90]s"``, ``"[0/±45/90]2s"``,
    ``"[0_2,45,-45]"`` (``_n`` repeats a ply), ``"+-45"``, ``"∓45"``.
    """
    if isinstance(layup, (list, tuple, np.ndarray)):
        out = []
        for a in layup:
            if isinstance(a, str):
                out += parse_layup("[" + a + "]")
            else:
                out.append(float(a))
        return out
    s = str(layup).strip().replace(" ", "").replace("/", ",")
    mt = re.fullmatch(r"\[(.*)\](\d*)(s?)", s, flags=re.I)
    if not mt:
        raise ValueError(f"cannot parse layup {layup!r}")
    body, nrep, sym = mt.group(1), mt.group(2), mt.group(3)
    base: list[float] = []
    for tok in body.split(","):
        if not tok:
            continue
        rep = 1
        if "_" in tok:
            tok, r = tok.split("_")
            rep = int(r)
        if tok.startswith(("±", "+-")):
            a = float(tok.lstrip("±+-"))
            seq = [a, -a]
        elif tok.startswith(("∓", "-+")):
            a = float(tok.lstrip("∓-+"))
            seq = [-a, a]
        else:
            seq = [float(tok)]
        base += seq * rep
    if sym:
        base = base * (int(nrep) if nrep else 1)
        base = base + base[::-1]
    elif nrep:
        base = base * int(nrep)
    return base


# ----------------------------------------------------------------------------- CLT core
def Q_matrix(p: Ply) -> np.ndarray:
    d = 1 - p.nu12 * p.nu21
    return np.array([[p.E1 / d, p.nu12 * p.E2 / d, 0],
                     [p.nu12 * p.E2 / d, p.E2 / d, 0],
                     [0, 0, p.G12]])


def T_sigma(theta_deg: float) -> np.ndarray:
    """Stress transformation global (x,y,xy) -> ply (1,2,12)."""
    c, s = np.cos(np.radians(theta_deg)), np.sin(np.radians(theta_deg))
    return np.array([[c * c, s * s, 2 * c * s], [s * s, c * c, -2 * c * s], [-c * s, c * s, c * c - s * s]])


def T_eps(theta_deg: float) -> np.ndarray:
    """Engineering-strain transformation global -> ply."""
    c, s = np.cos(np.radians(theta_deg)), np.sin(np.radians(theta_deg))
    return np.array([[c * c, s * s, c * s], [s * s, c * c, -c * s], [-2 * c * s, 2 * c * s, c * c - s * s]])


def Qbar(p: Ply, theta_deg: float) -> np.ndarray:
    Ts, Te = T_sigma(theta_deg), T_eps(theta_deg)
    return np.linalg.inv(Ts) @ Q_matrix(p) @ Te


@dataclass
class Laminate:
    plies: list            # list[Ply] (bottom to top)
    angles: list           # degrees
    A: np.ndarray = field(init=False)
    B: np.ndarray = field(init=False)
    D: np.ndarray = field(init=False)
    z: np.ndarray = field(init=False)

    def __post_init__(self):
        t = np.array([p.t for p in self.plies])
        self.z = np.concatenate([[0.0], np.cumsum(t)]) - t.sum() / 2
        A = np.zeros((3, 3)); B = np.zeros((3, 3)); D = np.zeros((3, 3))
        for k, (p, a) in enumerate(zip(self.plies, self.angles)):
            Qb = Qbar(p, a)
            z0, z1 = self.z[k], self.z[k + 1]
            A += Qb * (z1 - z0)
            B += Qb * (z1 ** 2 - z0 ** 2) / 2
            D += Qb * (z1 ** 3 - z0 ** 3) / 3
        self.A, self.B, self.D = A, B, D

    @classmethod
    def from_layup(cls, layup, ply: Ply | None = None) -> "Laminate":
        """Single-material layup (string / angle list) with ``ply``, or a mixed layup: a list of
        tuples ``(angle, material_ref[, t])`` or dicts ``{"angle", "material", "t", "n"}``
        (inner -> outer). Plain numbers in a mixed list use ``ply``."""
        if isinstance(layup, (list, tuple)) and any(isinstance(x, (tuple, list, dict)) for x in layup):
            plies, ang = [], []
            cache = {}
            for item in layup:
                if isinstance(item, dict):
                    a, mref, t, n = item["angle"], item.get("material"), item.get("t"), int(item.get("n", 1))
                elif isinstance(item, (tuple, list)):
                    a, mref = item[0], item[1]
                    t = item[2] if len(item) > 2 else None
                    n = 1
                else:
                    a, mref, t, n = item, None, None, 1
                if mref is None:
                    p = ply
                else:
                    key = (str(mref), t)
                    if key not in cache:
                        cache[key] = mref if isinstance(mref, Ply) else Ply.from_material(mref, t)
                    p = cache[key]
                for aa in parse_layup([a] if not isinstance(a, str) else a):
                    plies += [p] * n
                    ang += [aa] * n
            return cls(plies, ang)
        angs = parse_layup(layup)
        return cls([ply] * len(angs), angs)

    @property
    def density_kg_m3(self) -> float:
        return sum(p.t * p.density_kg_m3 for p in self.plies) / self.thickness

    def describe(self) -> str:
        out, prev, n = [], None, 0
        for p, a in zip(self.plies, self.angles):
            key = (p.name, a)
            if key == prev:
                n += 1
                continue
            if prev:
                out.append(f"{prev[1]:g}{'_' + str(n) if n > 1 else ''}({prev[0]})")
            prev, n = key, 1
        out.append(f"{prev[1]:g}{'_' + str(n) if n > 1 else ''}({prev[0]})")
        return "[" + " / ".join(out) + "]  (inner -> outer)"

    @property
    def thickness(self) -> float:
        return float(self.z[-1] - self.z[0])

    @property
    def ABD(self) -> np.ndarray:
        return np.block([[self.A, self.B], [self.B, self.D]])

    @property
    def abd(self) -> np.ndarray:
        return np.linalg.inv(self.ABD)

    # Effective in-plane engineering constants (membrane, from a = A^-1)
    def engineering(self) -> dict:
        a = np.linalg.inv(self.A)
        h = self.thickness
        return {"Ex": 1 / (a[0, 0] * h), "Ey": 1 / (a[1, 1] * h), "Gxy": 1 / (a[2, 2] * h),
                "nuxy": -a[0, 1] / a[0, 0], "thickness": h}

    def areal_mass_kg_m2(self) -> float:
        return sum(p.t * 1e-3 * p.density_kg_m3 for p in self.plies)

    def response(self, N=(0, 0, 0), M=(0, 0, 0)):
        """Mid-plane strains eps0 (3,) and curvatures kappa (3,) for running loads N, M."""
        sol = self.abd @ np.concatenate([np.asarray(N, float), np.asarray(M, float)])
        return sol[:3], sol[3:]

    def ply_stresses(self, N=(0, 0, 0), M=(0, 0, 0)) -> list[dict]:
        """Ply stresses in material axes at the bottom/top of each ply."""
        e0, k = self.response(N, M)
        out = []
        for i, (p, a) in enumerate(zip(self.plies, self.angles)):
            for pos, zz in (("bot", self.z[i]), ("top", self.z[i + 1])):
                eps_g = e0 + zz * k
                eps_12 = T_eps(a) @ eps_g
                sig_12 = Q_matrix(p) @ eps_12
                out.append({"ply": i, "angle": a, "pos": pos, "z": zz,
                            "eps12": eps_12, "sig12": sig_12})
        return out

    def first_ply_failure(self, N=(0, 0, 0), M=(0, 0, 0), knockdown: dict | None = DEFAULT_KNOCKDOWN,
                          criterion: str = "tsai_wu") -> dict:
        """Max failure index over plies. criterion in {'tsai_wu', 'max_stress', 'both'}."""
        best = {"fi": 0.0}
        for r in self.ply_stresses(N, M):
            p = self.plies[r["ply"]].knocked_down(knockdown)
            fis = {}
            if criterion in ("tsai_wu", "both"):
                fis["tsai_wu"] = tsai_wu_fi(r["sig12"], p)
            if criterion in ("max_stress", "both"):
                fis["max_stress"] = max_stress_fi(r["sig12"], p)
            for crit, fi in fis.items():
                if fi > best["fi"]:
                    best = {"fi": fi, "criterion": crit, "ply": r["ply"], "angle": r["angle"],
                            "pos": r["pos"], "sig12": r["sig12"]}
        best["sf"] = 1.0 / best["fi"] if best["fi"] > 0 else np.inf
        return best


    def membrane_fpf_batch(self, N: np.ndarray, knockdown: dict | None = DEFAULT_KNOCKDOWN,
                           criterion: str = "tsai_wu"):
        """Vectorised first-ply failure for membrane running loads N (n, 3) [Nx, Ny, Nxy], M = 0.

        Requires a symmetric laminate (B = 0). Returns (fi (n,), ply index (n,), sig12 (n, 3)).
        """
        N = np.atleast_2d(np.asarray(N, float))
        eps0 = np.linalg.solve(self.A, N.T)              # (3, n)
        best_fi = np.zeros(N.shape[0])
        best_ply = np.zeros(N.shape[0], int)
        best_sig = np.zeros((N.shape[0], 3))
        for i, (p, a) in enumerate(zip(self.plies, self.angles)):
            sig = (Q_matrix(p) @ T_eps(a) @ eps0).T      # (n, 3)
            pk = p.knocked_down(knockdown)
            fis = []
            if criterion in ("tsai_wu", "both"):
                fis.append(tsai_wu_fi_vec(sig, pk))
            if criterion in ("max_stress", "both"):
                fis.append(max_stress_fi_vec(sig, pk))
            fi = np.max(fis, axis=0)
            upd = fi > best_fi
            best_fi[upd], best_ply[upd], best_sig[upd] = fi[upd], i, sig[upd]
        return best_fi, best_ply, best_sig


# ----------------------------------------------------------------------------- failure
def tsai_wu_fi_vec(sig, p: Ply, F12_star: float = -0.5) -> np.ndarray:
    s1, s2, t12 = sig[:, 0], sig[:, 1], sig[:, 2]
    F1 = 1 / p.Xt - 1 / p.Xc
    F2 = 1 / p.Yt - 1 / p.Yc
    F11, F22, F66 = 1 / (p.Xt * p.Xc), 1 / (p.Yt * p.Yc), 1 / p.S ** 2
    F12 = F12_star * np.sqrt(F11 * F22)
    a = F11 * s1 ** 2 + F22 * s2 ** 2 + F66 * t12 ** 2 + 2 * F12 * s1 * s2
    b = F1 * s1 + F2 * s2
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where(a > 1e-30, (-b + np.sqrt(b * b + 4 * a)) / (2 * a), np.where(b > 0, 1 / b, np.inf))
        return np.where(np.isfinite(R) & (R > 0), 1 / R, 0.0)


def max_stress_fi_vec(sig, p: Ply) -> np.ndarray:
    s1, s2, t12 = sig[:, 0], sig[:, 1], sig[:, 2]
    f1 = np.where(s1 >= 0, s1 / p.Xt, -s1 / p.Xc)
    f2 = np.where(s2 >= 0, s2 / p.Yt, -s2 / p.Yc)
    return np.maximum.reduce([f1, f2, np.abs(t12) / p.S])


def tsai_wu_fi(sig12, p: Ply, F12_star: float = -0.5) -> float:
    """Tsai-Wu inverse strength ratio. F12 = F12* sqrt(F11 F22) (F12* = -0.5 by default)."""
    s1, s2, t12 = sig12
    F1 = 1 / p.Xt - 1 / p.Xc
    F2 = 1 / p.Yt - 1 / p.Yc
    F11 = 1 / (p.Xt * p.Xc)
    F22 = 1 / (p.Yt * p.Yc)
    F66 = 1 / p.S ** 2
    F12 = F12_star * np.sqrt(F11 * F22)
    a = F11 * s1 ** 2 + F22 * s2 ** 2 + F66 * t12 ** 2 + 2 * F12 * s1 * s2
    b = F1 * s1 + F2 * s2
    if a <= 0 and b <= 0:
        return 0.0
    if a <= 1e-30:
        return max(b, 0.0)
    R = (-b + np.sqrt(b * b + 4 * a)) / (2 * a)
    return float(1 / R)


def max_stress_fi(sig12, p: Ply) -> float:
    s1, s2, t12 = sig12
    f1 = s1 / p.Xt if s1 >= 0 else -s1 / p.Xc
    f2 = s2 / p.Yt if s2 >= 0 else -s2 / p.Yc
    return float(max(f1, f2, abs(t12) / p.S))


def quasi_isotropic_modulus(p: Ply) -> float:
    """Closed-form in-plane modulus of a quasi-isotropic laminate (Tsai-Pagano invariants)."""
    Q = Q_matrix(p)
    U1 = (3 * Q[0, 0] + 3 * Q[1, 1] + 2 * Q[0, 1] + 4 * Q[2, 2]) / 8
    U4 = (Q[0, 0] + Q[1, 1] + 6 * Q[0, 1] - 4 * Q[2, 2]) / 8
    return (U1 ** 2 - U4 ** 2) / U1
