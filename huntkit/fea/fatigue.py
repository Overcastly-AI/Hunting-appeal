"""Metal fatigue: Basquin S-N, Goodman mean-stress correction, rainflow counting, Miner sum.

Simple S-N (when no fitted curve is available), stress *amplitude* basis, fully reversed:
  S(1e3 cycles) = 0.9 Su
  S(N_e)        = Se  (material ``fatigue_limit_mpa``; else 0.5 Su capped at 0.4 Su for Al)
Basquin through those points: Sa = A * N^b. For aluminium there is no true endurance limit; the
curve keeps falling past N_e (ASSUMPTION: same slope extrapolated), for steel/Ti it is flat
beyond N_e.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .materials_bridge import get_material


@dataclass
class SNCurve:
    A: float          # Sa = A * N**b
    b: float
    Se: float
    Ne: float
    endurance: bool   # flat beyond Ne?
    Su: float

    def stress_amplitude(self, N):
        N = np.asarray(N, float)
        Sa = self.A * N ** self.b
        if self.endurance:
            Sa = np.where(N >= self.Ne, self.Se, Sa)
        return Sa

    def life(self, Sa: float) -> float:
        """Cycles to failure at fully reversed amplitude Sa."""
        if Sa <= 0:
            return np.inf
        if self.endurance and Sa <= self.Se:
            return np.inf
        if Sa >= self.Su:
            return 1.0
        return float(max((Sa / self.A) ** (1 / self.b), 1.0))


def basquin(Su: float, Se: float, Ne: float = 5e8, endurance: bool = False) -> SNCurve:
    S1, N1 = 0.9 * Su, 1e3
    b = np.log(Se / S1) / np.log(Ne / N1)
    A = S1 / N1 ** b
    return SNCurve(A, b, Se, Ne, endurance, Su)


def sn_from_material(ref) -> SNCurve:
    m = get_material(ref)
    Su = float(m.require("ultimate_strength_mpa"))
    Se = m.get("fatigue_limit_mpa")
    name = (m.id + " " + m.name).lower()
    is_al = "alu" in name or "aluminum" in name or "aluminium" in name
    if Se is None:
        Se = min(0.4 * Su, 130.0) if is_al else 0.5 * Su
    # ASSUMPTION: Al fatigue_limit quoted at 5e8 cycles (MMPDS/rotating-beam basis), no knee;
    # steel/Ti knee at 1e6 with a true endurance limit.
    return basquin(Su, float(Se), Ne=5e8 if is_al else 1e6, endurance=not is_al)


def goodman_equivalent(Sa: float, Sm: float, Su: float) -> float:
    """Fully reversed amplitude equivalent to (Sa, Sm) via Goodman. Compressive mean -> no credit."""
    Sm = max(Sm, 0.0)
    if Sm >= Su:
        return np.inf
    return Sa / (1 - Sm / Su)


def life(Smax: float, Smin: float, curve: SNCurve) -> float:
    Sa, Sm = (Smax - Smin) / 2, (Smax + Smin) / 2
    return curve.life(goodman_equivalent(abs(Sa), Sm, curve.Su))


def rainflow(series) -> list[tuple[float, float, float]]:
    """ASTM E1049-85 rainflow count. Returns [(range, mean, count)] with count 1.0 or 0.5."""
    x = np.asarray(series, float)
    if x.size < 2:
        return []
    # reduce to turning points
    tp = [x[0]]
    for v in x[1:]:
        if v == tp[-1]:
            continue
        if len(tp) >= 2 and (tp[-1] - tp[-2]) * (v - tp[-1]) > 0:
            tp[-1] = v
        else:
            tp.append(v)
    out, stack = [], []
    for p in tp:
        stack.append(p)
        while len(stack) >= 3:
            X = abs(stack[-1] - stack[-2])
            Y = abs(stack[-2] - stack[-3])
            if X < Y:
                break
            if len(stack) == 3:
                out.append((Y, (stack[-2] + stack[-3]) / 2, 0.5))
                stack.pop(0)
            else:
                out.append((Y, (stack[-2] + stack[-3]) / 2, 1.0))
                last = stack.pop()
                stack.pop(); stack.pop()
                stack.append(last)
    for i in range(len(stack) - 1):
        out.append((abs(stack[i + 1] - stack[i]), (stack[i + 1] + stack[i]) / 2, 0.5))
    return out


def miner(cycles, curve: SNCurve) -> float:
    """Damage sum for [(range, mean, count)] cycles."""
    D = 0.0
    for rng, mean, n in cycles:
        Nf = curve.life(goodman_equivalent(rng / 2, mean, curve.Su))
        D += n / Nf if np.isfinite(Nf) else 0.0
    return D
