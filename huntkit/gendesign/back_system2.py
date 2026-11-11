"""BL-005 back system: can one structure do both jobs? (structural-fea-engineer, 2026-11-10)

The back system is two stiff parts on opposite sides of the stays:

- the Sandwich v2 spreader (BP-06 rev C, bag side) stops meat and bone ends pressing through the window and puts the
  meat into the stays;
- the two 1 mm twill backer strips (BP-08, wearer side) spread each stay's line load across its 120 mm XLPE rail so the
  skin stays <= 14 kPa.

This module asks whether one part can do both, or whether either job can be done lighter, using the SAME models:

- skin pressure: the rail-and-tissue section of ``spreader.rail_backed`` / ``back_rail.skin`` (Hetenyi spread of the
  bone along the stay, nonlinear Pasternak foam on a 60 kPa tissue column). ``section2`` below is that model, copied
  (``spreader.py`` and ``back_rail.py`` are not edited, ticket rule) and extended with (i) a shear-flexible
  (Timoshenko) strip, needed for sandwich backers, and (ii) the strip moment and shear for a strength check the
  released backer never had. With an infinitely shear-stiff strip it reproduces ``spreader.rail_backed`` exactly
  (tests/test_back_system2.py).
- spreader strength, fatigue and clearance: ``spreader.evaluate`` on the production part ``sw110c7d`` with the rail
  patched in (as ``back_rail.confirm``).
- the framesheet variant (a2), which the spreader model cannot represent, is a ``huntkit.fea.plate_grid.GridPlate`` on
  a secant Winkler foundation (the same foam + tissue column) with the stays as beams tied to the sheet.
- masses: ``huntkit.mass.ledger`` (back system rows), split by ``panels.yaml`` and ``spreader_results.json`` (both are
  the ledger's own sources; a test checks they add up to the ledger rows). Variants are booked as ledger total + the
  change computed by the ``back_rail.mass_g`` method.

    python -m huntkit.gendesign.back_system2              # study + doc + screens (re-uses the full checks if cached)
    python -m huntkit.gendesign.back_system2 --full       # also re-run the two full spreader checks (~10 min each)
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np
import yaml

from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
DOC = ANALYSIS / "back_system_integration.md"
OUT = REPO / "outputs" / "back_system2"
CACHE = OUT / "results.json"
SCREENS = REPO / "outputs" / "screens"
SHOT_PREFIX = "20261110_BL005_"   # orchestrator: today's prefix (ticket text says 20261111_)

E_REVC = 190.0                    # HA-LS-1 rev C C5 meat CG, covers every torso (load_standard.md, rev C table)
E_TORSO = {"15 in": 181.0, "19 in": 173.0, "23 in": 165.0}   # meat runs per torso (load_standard.md -> bag_attachment.md 2)
PEAK_KPA = 14.0                   # Golriz et al. 2017 (back_comfort.md)
MARGIN_KPA = 0.2                  # back_rail.MARGIN_KPA (model resolution)
GUTTER_MIN = 110.0                # back_rail.GUTTER_MIN
TARGET_G, STRETCH_G = 320.0, 290.0
FAT_FI = 0.5                      # HA-LS-1: CFRP FI <= 0.5 at the 1.6 g walking peak (spreader.FAT_FI)
B_STAY = 8.0                      # ASSUMPTION (as spreader.sandwich_checks b_crown): stay line load on >= 8 mm of strip
RESIN = 0.06                      # spreader.RESIN_SANDWICH_KG_M2: extra resin to wet the cut core, kg/m2
TW = "cfrp_t300_3k_woven_epoxy_ply"
PAD_SEAT_Y = -27.0                # corrie.PAD_SEAT zone_y top (pan face side of the pad seat stack), frame y
PAD_SEAT_X, PAD_SEAT_Z = 125.0, (50.0, 190.0)   # corrie.PAD_SEAT pan_x / pan_z


def _S():
    from huntkit.gendesign import spreader
    return spreader


def _BR():
    from huntkit.gendesign import back_rail
    return back_rail


# =====================================================================================================================
# backer strips
# =====================================================================================================================
@dataclass(frozen=True)
class Backer:
    key: str
    name: str
    kind: str = "twill"           # twill | sandwich | paht_rib | none
    width: float = 80.0
    t: float = 1.02               # twill plate thickness
    core: str = ""                # sandwich core id
    core_t: float = 0.0
    rib: tuple = ()               # PAHT ribbed print: (base t, rib width, rib height, pitch)

    # ---- laminate for strength (spreader conventions)
    def lam(self):
        S = _S()
        from huntkit.fea.composite import Laminate
        if self.kind == "twill":
            n = max(int(round(self.t / 0.255)), 1)
            ang = [0, 45, 45, 0] if n == 4 else ([0, 0] if n == 2 else [0] * n)
            return Laminate([S._twill(self.t / n)] * n, ang)
        if self.kind == "sandwich":
            return S.sandwich_lam(self.core, self.core_t)
        raise ValueError(self.kind)

    @property
    def thickness(self) -> float:
        if self.kind == "twill":
            return self.t
        if self.kind == "sandwich":
            return self.core_t + 2 * 0.22
        if self.kind == "paht_rib":
            return self.rib[0] + self.rib[2]
        return 0.0

    def D(self) -> float:
        """Lateral bending stiffness per mm of rail length, N mm. Twill: the released convention
        (back_rail.backer_D: E t^3 / 12(1 - 0.1^2), record E1). Sandwich: D11 of the CLT laminate."""
        if self.kind == "none":
            return 0.0
        if self.kind == "twill":
            m = load(TW)
            return float(m.require("E1_mpa")) * self.t ** 3 / (12 * (1 - 0.1 ** 2))
        if self.kind == "sandwich":
            return float(self.lam().D[0, 0])
        if self.kind == "paht_rib":
            E = float(load("pa12_cf_fdm_paht").require("youngs_modulus_xy_mpa")) * _S().PAHT_HOT_WET
            return E * self._rib_I()
        raise ValueError(self.kind)

    def _rib(self) -> tuple:
        """T-section per rib pitch: (I per mm of width, extreme-fibre distance)."""
        tb, b, hr, p = self.rib
        A1, A2 = p * tb, b * hr
        y1, y2 = tb / 2, tb + hr / 2
        yc = (A1 * y1 + A2 * y2) / (A1 + A2)
        I = p * tb ** 3 / 12 + A1 * (y1 - yc) ** 2 + b * hr ** 3 / 12 + A2 * (y2 - yc) ** 2
        return I / p, max(yc, tb + hr - yc)

    def _rib_I(self) -> float:
        return self._rib()[0]

    def S_shear(self) -> float:
        """Transverse shear stiffness per mm of rail length (N/mm per unit shear strain). Sandwich: G_c d^2 / t_c
        (Zenkert); solid strips: effectively rigid in shear here."""
        if self.kind == "sandwich":
            Gc = float(load(self.core).require("shear_modulus_mpa"))
            d = self.core_t + 0.22
            return Gc * d ** 2 / self.core_t
        return math.inf

    def areal_kg_m2(self) -> float:
        if self.kind == "none":
            return 0.0
        if self.kind == "twill":
            return self.t * float(load(TW).require("density_kg_m3")) / 1000.0
        if self.kind == "sandwich":
            return float(self.lam().areal_mass_kg_m2()) + RESIN
        tb, b, hr, p = self.rib
        return (tb + b * hr / p) * float(load("pa12_cf_fdm_paht").require("density_kg_m3")) / 1000.0

    def mass_pair_g(self, length: float = 420.0) -> float:
        m = 2 * self.width * length * self.areal_kg_m2() / 1000.0
        if self.kind == "sandwich":       # sealed core edge, as spreader.edge_seal_g
            S = _S()
            m += 2 * 2 * (self.width + length) * self.core_t * S.EDGE_COAT_T * S.EDGE_COAT_KG_M3 / 1e6
        return m

    def strength(self, M: float, Q: float, q_line: float, walk: bool) -> dict:
        """Strip checks at the moment M (N mm/mm), shear Q (N/mm) and stay line load q_line (N/mm).
        Factored (walk=False): first-ply FI (Tsai-Wu, hot/wet + impact knockdowns), core shear, core crush under the
        stay. Walking: the FI <= 0.5 fatigue rule. Returns SFs."""
        S = _S()
        KD = S.KD
        out = {}
        if self.kind in ("twill", "sandwich"):
            from huntkit.fea.plate_grid import laminate_bending_fi
            fi = float(laminate_bending_fi(self.lam(), np.array([[abs(M), 0.0, 0.0]]), KD)[0])
            out["fi"] = fi
            out["sf"] = (FAT_FI / fi) if walk else (1.0 / fi)
            if self.kind == "sandwich" and not walk:
                m = load(self.core)
                tau = abs(Q) / (self.core_t + 0.22)
                out["core_shear_sf"] = float(m.require("shear_strength_mpa")) * KD["hot_wet"] / max(tau, 1e-9)
                out["core_crush_sf"] = float(m.require("compressive_strength_mpa")) * KD["hot_wet"] / max(q_line / B_STAY, 1e-9)
                out["sf"] = min(out["sf"], out["core_shear_sf"], out["core_crush_sf"])
        elif self.kind == "paht_rib":
            m = load("pa12_cf_fdm_paht")
            I, c = self._rib()
            sig = abs(M) * c / I
            allow = float(m.require("tensile_strength_z_mpa")) * float(m.require("env_knockdown_ratio"))
            if walk:
                allow *= float(m.require("fatigue_1e5_ratio")) / 1.0
            out["sigma_mpa"] = sig
            out["sf"] = allow / max(sig, 1e-9)
        else:
            out["sf"] = math.inf
        return out


TODAY_BACKER = Backer("tw102_80", "1 mm 2x2 twill plate, 80 mm (BP-08, released)")


def backers() -> list[Backer]:
    out = [TODAY_BACKER, Backer("none", "no backer strip", "none", 0.0, 0.0)]
    for w in (80.0, 100.0):
        out.append(Backer(f"tw051_{w:.0f}", f"0.5 mm twill plate (2 plies), {w:.0f} mm", "twill", w, 0.51))
    for core, ct in (("rohacell_71_igf", 2.0), ("rohacell_71_igf", 3.0), ("rohacell_110_igf", 2.0),
                     ("rohacell_110_igf", 3.0)):
        for w in (60.0, 70.0, 80.0):
            c = "R71" if "71" in core else "R110"
            out.append(Backer(f"sw{c}c{ct:g}_{w:.0f}", f"sandwich strip: 200 g twill / {ct:g} mm {c} / twill, {w:.0f} mm",
                              "sandwich", w, 0.0, core, ct))
    out.append(Backer("paht_rib_80", "printed PAHT-CF ribbed strip (1.0 base + 1.2 x 4 ribs at 8 mm), 80 mm",
                      "paht_rib", 80.0, 0.0, rib=(1.0, 1.2, 4.0, 8.0)))
    return out


def backer_by_key(k: str) -> Backer:
    return next(b for b in backers() if b.key == k)


# =====================================================================================================================
# rail section: spreader.rail_backed with a Timoshenko strip and the strip moment
# =====================================================================================================================
def foam_layers(foam_t: float = 10.0) -> list[dict]:
    BR = _BR()
    return BR.layers(BR.Rail("tmp", "tmp", foam_t=foam_t))


def section2(q_line: float, D_b: float, S_b: float = math.inf, layers=None, tissue_kpa: float | None = None,
             half: float = 60.0, strip_w: float = 80.0, n: int = 101) -> dict:
    """Lateral section of one rail: a strip (bending D_b, shear S_b per mm of rail) between the stay and the foam,
    on the nonlinear Pasternak foam + Winkler tissue of ``spreader.rail_backed`` (same matrices, same secant loop).
    The stay line load lands at the strip centre. Timoshenko element with the interdependent interpolation
    (phi = 12 D / (S le^2)); phi = 0 gives the Hermite element of ``rail_backed``."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    S = _S()
    layers = layers or foam_layers()
    tk = S.TISSUE_E_KPA if tissue_kpa is None else tissue_kpa
    kt = tk / 1000.0 / S.TISSUE_H
    Gp = sum(L["G"] * L["h"] for L in layers)
    p_tab = np.concatenate([[0.0], np.geomspace(1e-5, 0.6, 400)])
    u_f = np.zeros_like(p_tab)
    for L in layers:
        e, s_ = L["curve"]
        u_f += L["h"] * np.interp(p_tab, s_, e)
    u_tab = u_f + p_tab / kt
    x = np.linspace(-half, half, n)
    le = x[1] - x[0]
    xm = (x[:-1] + x[1:]) / 2
    instrip = np.abs(xm) <= strip_w / 2
    Db = np.where(instrip, max(D_b, 1e-12), D_b * 1e-6 if D_b > 0 else 1e-9)
    phi = np.where(instrip & np.isfinite(S_b), 12 * Db / (S_b * le ** 2) if np.isfinite(S_b) else 0.0, 0.0)

    def kb(D, ph):
        c = D / (le ** 3 * (1 + ph))
        return c * np.array([[12, 6 * le, -12, 6 * le], [6 * le, (4 + ph) * le ** 2, -6 * le, (2 - ph) * le ** 2],
                             [-12, -6 * le, 12, -6 * le], [6 * le, (2 - ph) * le ** 2, -6 * le, (4 + ph) * le ** 2]])

    KB = np.stack([kb(D, ph) for D, ph in zip(Db, phi)])
    ks = Gp / (30 * le) * np.array([[36, 3 * le, -36, 3 * le], [3 * le, 4 * le ** 2, -3 * le, -le ** 2],
                                    [-36, -3 * le, 36, -3 * le], [3 * le, -le ** 2, -3 * le, 4 * le ** 2]])
    mw = le / 420 * np.array([[156, 22 * le, 54, -13 * le], [22 * le, 4 * le ** 2, 13 * le, -3 * le ** 2],
                              [54, 13 * le, 156, -22 * le], [-13 * le, -3 * le ** 2, -22 * le, 4 * le ** 2]])
    nd = 2 * n
    f = np.zeros(nd)
    f[2 * (n // 2)] = q_line
    ksec = np.full(n - 1, 0.01)
    ed = 2 * np.arange(n - 1)[:, None] + np.arange(4)[None, :]
    rr = np.repeat(ed, 4, axis=1).ravel()
    cc = np.tile(ed, (1, 4)).ravel()
    u = np.zeros(nd)
    for _ in range(80):
        ke = KB + ks[None] + ksec[:, None, None] * mw[None]
        K = sp.coo_matrix((ke.ravel(), (rr, cc)), shape=(nd, nd)).tocsr()
        un = spsolve(K, f)
        w = un[0::2]
        wm = np.maximum((w[:-1] + w[1:]) / 2, 1e-6)
        kn = np.interp(wm, u_tab, p_tab) / wm
        if np.allclose(kn, ksec, rtol=1e-4):
            u = un
            break
        ksec = 0.5 * ksec + 0.5 * kn
        u = un
    w = np.maximum(u[0::2], 0.0)
    p = np.interp(w, u_tab, p_tab)
    # strip end forces (bending part only): [V0, M0, V1, M1]
    fe = np.einsum("eab,eb->ea", KB, u[ed])
    Mn = np.abs(np.r_[fe[:, 1], fe[:, 3]])[np.r_[instrip, instrip]]
    Vn = np.abs(np.r_[fe[:, 0], fe[:, 2]])[np.r_[instrip, instrip]]
    pk = float(p.max())
    return {"peak_kpa": pk * 1000.0, "indent_mm": float(w.max()), "k_line": q_line / max(float(w.max()), 1e-6),
            "x": x, "p_kpa": p * 1000.0, "M_max": float(Mn.max()) if Mn.size else 0.0,
            "Q_max": float(Vn.max()) if Vn.size else 0.0,
            "foam_mm": float(sum(L["h"] * np.interp(pk, L["curve"][1], L["curve"][0]) for L in layers))}


# =====================================================================================================================
# rail variants
# =====================================================================================================================
@dataclass(frozen=True)
class RailV:
    key: str
    name: str
    family: str                   # today | a | b | c
    backer: Backer = TODAY_BACKER
    rail_w: float = 120.0
    rail_l: float = 420.0
    foam_t: float = 10.0
    sheet_half_w: float = 121.0   # spreader outline half width (a1 widens it)
    note: str = ""


TODAY = RailV("today", "today: 120 mm rail, 80 mm 1 mm twill backer, sw110c7d spreader", "today")


def bone_side_n() -> float:
    """Worst bone side reaction of the production spreader at the named positions (walking), N. From the cached
    reproduction run (``outputs/back_system2/repro_sides.json``) or ``back_rail_results.json`` (same call)."""
    p = OUT / "repro_sides.json"
    src = json.loads(p.read_text()) if p.exists() else json.loads((ANALYSIS / "back_rail_results.json").read_text())["bone"]
    return float(max(src["sides_n"].values()))


def section_of(v: RailV, q: float, tissue_kpa=None) -> dict:
    b = v.backer
    return section2(q, b.D(), b.S_shear(), foam_layers(v.foam_t), tissue_kpa, half=v.rail_w / 2,
                    strip_w=max(b.width, 1e-6))


def skin(v: RailV, e_mm: float, side_n: float, kind: str = "walk", tissue_kpa=None, length: float | None = None) -> dict:
    """``back_rail.skin`` with this rail (same loads, same Hetenyi spread), plus the strip forces."""
    S, BR = _S(), _BR()
    g = {"walk": 1.6, "factored": 3.0}[kind]
    side = side_n * (S.bone_n(kind) / S.bone_n("walk"))
    H = max(BR.meat_force_n(e_mm, g) - S.bone_n(kind), 0.0)
    L = length or v.rail_l
    q0 = H / 2.0 / L
    s0 = section_of(v, q0, tissue_kpa)
    beta = (s0["k_line"] / (4.0 * S.stay_EI())) ** 0.25
    q = q0 + side * beta / 2.0
    s = section_of(v, q, tissue_kpa)
    s.update(q_line=q, q_meat=q0, beta_len_mm=1.0 / beta, meat_only_kpa=s0["peak_kpa"])
    return s


def mass_delta_g(v: RailV) -> dict:
    """Change against today for the parts the variant touches (back_rail.mass_g method): foam, backer, sleeve, mesh,
    spreader outline. Positive = heavier."""
    BR = _BR()
    rho_f = float(load("xlpe_foam_l200").require("density_kg_m3"))

    def parts(r: RailV):
        foam = 2 * r.rail_w * r.rail_l * r.foam_t * rho_f / 1e6
        back = r.backer.mass_pair_g(r.rail_l)
        # sleeve = rail + 20 + 2 x (stack - 11) wide (a thicker stack needs more girth), rail_l + 15 long
        stack = r.foam_t + r.backer.thickness
        sleeve = 2 * (r.rail_w + 20 + 2 * max(stack - 11.02, 0.0)) * (r.rail_l + 15) * BR._areal(BR.SLEEVE_MAT) / 1e6
        mesh = 2 * (115.0 + (r.rail_w + 20) / 2) * 460.0 * BR._areal(BR.MESH_MAT) / 1e6
        sheet = 0.0
        if r.sheet_half_w > 121.0:      # a1: wider spreader outline, same 7.44 mm sandwich
            sheet = 2 * (r.sheet_half_w - 121.0) * 318.0 * 1.49 / 1000.0
        return {"foam": foam, "backer": back, "sleeve": sleeve, "mesh": mesh, "sheet": sheet}

    a, b = parts(v), parts(TODAY)
    d = {k: a[k] - b[k] for k in a}
    d["total"] = sum(d.values())
    return d


def rail_variants() -> list[RailV]:
    out = [TODAY]
    out.append(RailV("a1_wide_bagside", "(a1) spreader widened to x +/-155 on the bag side, backers deleted", "a",
                     backer_by_key("none"), sheet_half_w=155.0,
                     note="the sheet is on the bag face of the stays; the rail is on the wearer face. Nothing joins them"))
    for b in backers():
        if b.key in ("tw102_80", "none"):
            continue
        out.append(RailV(f"b_{b.key}", f"(b) {b.name}", "b", b))
    best = [backer_by_key(k) for k in ("swR71c3_80", "swR71c3_70", "swR110c2_80", "swR71c2_80")]
    for b in best:
        for w in (100.0, 110.0):
            out.append(RailV(f"c_{b.key}_r{w:.0f}", f"(c) {w:.0f} mm rail, {b.name}", "c", replace(b, width=min(b.width, w - 20)),
                             rail_w=w))
        for L in (380.0, 340.0):
            out.append(RailV(f"c_{b.key}_L{L:.0f}", f"(c) {L:.0f} mm long rail, {b.name}", "c", b, rail_l=L))
    return out


def clearance(v: RailV, today: dict, s_walk: dict, s_fact: dict, t0: dict) -> dict:
    """Air to the skin vs today's full spreader check (``today``: clear_walk_min etc.), shifted by the change in rail
    indentation, aged foam height, backer stack and the torso bulge at the worst point (x 24 in the gutter).
    ASSUMPTION: the sheet's own deflection field is unchanged by the rail (back_rail.md: it is)."""
    S = _S()
    set_ = float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0
    dh = (v.foam_t - TODAY.foam_t) * (1 - set_) + (v.backer.thickness - TODAY.backer.thickness)
    g0, g1 = S.STAY_X - TODAY.rail_w / 2, S.STAY_X - v.rail_w / 2
    out = {}
    for k, s, s_ref, R in (("walk", s_walk, t0["walk"], S.R_TORSO), ("fact", s_fact, t0["fact"], S.R_TORSO),
                           ("lean", s_fact, t0["fact"], S.R_TORSO_LO)):
        db = ((max(g1, 24) ** 2 - 24 ** 2) - (max(g0, 24) ** 2 - 24 ** 2)) / (2 * R)
        base = {"walk": today["clear_walk_min"], "fact": today["clear_fact_min"], "lean": today["clear_fact_lean_min"]}[k]
        out[k] = base + dh - (s["indent_mm"] - s_ref["indent_mm"]) - db
    return out


def evaluate_rail(v: RailV, side: float, today_full: dict, t0: dict | None = None) -> dict:
    sw = skin(v, E_REVC, side, "walk")
    sf = skin(v, E_REVC, side, "factored")
    t0 = t0 or {"walk": sw, "fact": sf}
    st_f = v.backer.strength(sf["M_max"], sf["Q_max"], sf["q_line"], walk=False)
    st_w = v.backer.strength(sw["M_max"], sw["Q_max"], sw["q_line"], walk=True)
    torso = {k: skin(v, e, side)["peak_kpa"] for k, e in E_TORSO.items()}
    c = clearance(v, today_full, sw, sf, t0)
    md = mass_delta_g(v)
    S = _S()
    set_ = float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0
    y_face = float(S.sleeve_y(119.0) - S.stay_r(119.0)) - v.backer.thickness - v.foam_t
    sides = {"gutter_mm": 2 * (S.STAY_X - v.rail_w / 2), "rail_outer_x": S.STAY_X + v.rail_w / 2,
             "backer_x": (S.STAY_X - v.backer.width / 2, S.STAY_X + v.backer.width / 2),
             "pad_seat_overlap_x": (S.STAY_X - v.rail_w / 2, min(S.STAY_X + v.rail_w / 2, PAD_SEAT_X)),
             "rail_face_y_z119": y_face, "pad_seat_proud_mm": y_face - PAD_SEAT_Y}
    r = {"key": v.key, "name": v.name, "family": v.family, "variant": asdict(v), "peak_kpa": sw["peak_kpa"],
         "meat_only_kpa": sw["meat_only_kpa"], "peak_fact_kpa": sf["peak_kpa"], "torso_kpa": torso,
         "indent_walk": sw["indent_mm"], "M_walk": sw["M_max"], "M_fact": sf["M_max"], "q_walk": sw["q_line"],
         "backer_sf_fpf": st_f["sf"], "backer_sf_fatigue": st_w["sf"], "backer_checks": {"fact": st_f, "walk": st_w},
         "clear": c, "geometry": sides, "mass_delta": md, "stack_mm": v.foam_t + v.backer.thickness,
         "aged_foam_mm": v.foam_t * (1 - set_)}
    r["checks"] = {"skin": r["peak_kpa"] <= PEAK_KPA - MARGIN_KPA, "gutter": sides["gutter_mm"] >= GUTTER_MIN,
                   "backer_fpf": r["backer_sf_fpf"] >= 1.0, "backer_fatigue": r["backer_sf_fatigue"] >= 1.0,
                   "no_bottoming": c["walk"] >= 3.0 and c["fact"] >= 0.0 and c["lean"] >= 0.0}
    r["passes"] = all(r["checks"].values())
    return r


# =====================================================================================================================
# (a2) framesheet: the spreader moved to the wearer face of the stays, backing the rails
# =====================================================================================================================
@dataclass(frozen=True)
class Framesheet:
    key: str
    core_t: float = 7.0
    half_w: float = 155.0         # backs the 120 mm rail out to the backer's outer edge today (x 155)
    z_lo: float = 195.0           # above the lumbar pan top flange (z 190) and the strut line (z 155)
    z_hi: float = 470.0           # rail top
    rail_w: float = 120.0
    h: float = 5.0
    core: str = "rohacell_110_igf"


def _foundation_tab(foam_aged: float, tissue_kpa: float | None = None):
    S = _S()
    layers = foam_layers(foam_aged / (1 - float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0))
    kt = (S.TISSUE_E_KPA if tissue_kpa is None else tissue_kpa) / 1000.0 / S.TISSUE_H
    p_tab = np.concatenate([[0.0], np.geomspace(1e-6, 0.6, 400)])
    u = p_tab / kt
    for L in layers:
        e, s_ = L["curve"]
        u = u + L["h"] * np.interp(p_tab, s_, e)
    return u, p_tab


def framesheet_solve(fs: Framesheet, kind: str, bone_xy=None, foam_aged: float = 8.8, n_sec: int = 8,
                     keep: bool = False) -> dict:
    """Sheet on the stays' wearer face, on the rail foam + tissue (secant Winkler, unilateral), stays tied to the
    sheet (bilateral) as free PAHT beams. Loads as spreader.meat_pressure (overturning share + cinch) less the bone,
    plus the bone patch; the cinch is self-equilibrated: its total is put back on the stays (the anchors).
    The overturning share is spread uniformly over the window, as the 1-D skin model spreads it along the rail."""
    from huntkit.fea.plate_grid import Beam, GridPlate, Spring
    S, BR = _S(), _BR()
    lam = S.sandwich_lam(fs.core, fs.core_t)
    h = fs.h
    nx = int(round(2 * fs.half_w / h))
    ny = int(round((fs.z_hi - fs.z_lo) / h))
    pl = GridPlate(-fs.half_w, fs.z_lo, nx, ny, h, lam.D)
    nxy = pl.node_xy()
    g, f_over, f_cinch = {"walk": (1.6, 1.0, 1.0), "factored": (2.0, 1.5, 1.5)}[kind]
    P = S.bone_n(kind) if bone_xy is not None else 0.0
    beams = {}
    for s in (1.0, -1.0):
        sel = np.nonzero(np.isclose(nxy[:, 0], s * S.STAY_X))[0]
        sel = sel[np.argsort(nxy[sel, 1])]
        bm = pl.add_beam(Beam(np.c_[nxy[sel, 0], nxy[sel, 1]], S.stay_EI(), clamp_start=False, clamp_end=False,
                              tag="stay"))
        beams[s] = (bm, sel)
        for k, n in enumerate(sel):
            pl.springs.append(Spring(int(n), 0.0, 0.0, other=bm.dof0 + 2 * k, unilateral=False, tag="tie"))
    # foundation nodes and tributary areas
    xa = np.abs(nxy[:, 0])
    fnd = np.abs(xa - S.STAY_X) <= fs.rail_w / 2 + 1e-6
    trib = np.full(pl.nn, h * h)
    edge_x = np.isclose(xa, fs.half_w) | np.isclose(xa, S.STAY_X - fs.rail_w / 2)
    edge_z = np.isclose(nxy[:, 1], fs.z_lo) | np.isclose(nxy[:, 1], fs.z_hi)
    trib = trib * np.where(edge_x, 0.5, 1.0) * np.where(edge_z, 0.5, 1.0)
    fnodes = np.nonzero(fnd)[0]
    u_tab, p_tab = _foundation_tab(foam_aged)
    k0 = 0.010 / np.interp(0.010, p_tab, u_tab)        # secant at 10 kPa
    sp0 = len(pl.springs)
    for n in fnodes:
        pl.springs.append(Spring(int(n), k0 * trib[n], 0.0, tag="fnd"))
    # loads
    exy = pl.elem_xy()
    win = np.abs(exy[..., 0]) <= S.STAY_X
    L_fs = fs.z_hi - fs.z_lo
    # this sheet's share of the meat force, spread uniformly as the 1-D model spreads it over the 420 mm rail; the
    # bone is part of that share (as spreader.meat_pressure less_n)
    H = max(BR.meat_force_n(E_REVC, g * f_over) * L_fs / 420.0 - P, 0.0)
    q_over = H / (2 * S.STAY_X * L_fs)
    q_cinch = 6.0 * S.CINCH_N_PER_ANCHOR * f_cinch / (500.0 * S.FACE_W)
    q = np.where(win, q_over + q_cinch, 0.0)
    if bone_xy is not None:
        q = q + pl.patch_pressure(bone_xy[0], bone_xy[1], S.BONE_D, P)
    f = pl.load_vector(q)
    cinch_tot = q_cinch * float(win.sum()) * h * h
    for s, (bm, sel) in beams.items():
        nb = len(sel)
        f[bm.dof0:bm.dof0 + 2 * nb:2] -= cinch_tot / 2 / nb
    for _ in range(n_sec):
        sol = pl.solve(f)
        w = sol["w"]
        wf = np.maximum(w[fnodes], 1e-6)
        ksec = np.interp(wf, u_tab, p_tab) / wf
        for i, n in enumerate(fnodes):
            pl.springs[sp0 + i].k = max(float(ksec[i]), 1e-7) * trib[n]
        pl._K0 = None
    sol = pl.solve(f)
    w = sol["w"]
    from huntkit.fea.plate_grid import laminate_bending_fi
    M = pl.moments(sol["u"])
    fi = laminate_bending_fi(lam, M, S.KD).max(axis=2)
    pf = np.zeros(pl.nn)
    ff = sol["spring_force"][sp0:]
    pf[fnodes] = ff / trib[fnodes] * 1000.0
    tie = np.abs(sol["spring_force"][:sp0])
    out = {"fi_max": float(fi.max()), "w": w, "p_kpa": pf, "skin_kpa": float(pf.max()),
           "reaction_n": float(ff.sum()), "tie_line_n_mm": float(tie.max() / h), "nxy": nxy, "gutter_half": S.STAY_X - fs.rail_w / 2}
    gut = xa < out["gutter_half"]
    for name, R in (("walk", S.R_TORSO), ("lean", S.R_TORSO_LO)):
        bulge = (out["gutter_half"] ** 2 - xa ** 2) / (2 * R)
        out[f"need_{name}"] = float(np.max((w + bulge)[gut]))
    out["w_fnd_max"] = float(w[fnodes].max())
    if keep:
        out["pl"] = pl
        out["fi"] = fi
    return out


def framesheet_eval(fs: Framesheet) -> dict:
    """All checks of one framesheet: FPF (factored), fatigue (walk FI <= 0.5), sandwich local at the bone patch and
    the stay ties, skin, and the aged rail foam the gutter clearance needs (walk >= 3 mm, factored >= 0, factored
    lean torso >= 0)."""
    S = _S()
    xs = (0.0, 52.0, 85.0)                       # gutter centre, gutter edge, between rail and stay
    zs = (fs.z_lo + 12.0, 330.0, fs.z_hi - 12.0)
    pos = [(x, z) for x in xs for z in zs]
    foam = 8.8
    rows = []
    for _it in range(2):
        rows = []
        for xy in pos:
            wk = framesheet_solve(fs, "walk", xy, foam_aged=foam)
            fc = framesheet_solve(fs, "factored", xy, foam_aged=foam)
            rows.append({"x": xy[0], "z": xy[1], "fi_walk": wk["fi_max"], "fi_fact": fc["fi_max"],
                         "skin_kpa": wk["skin_kpa"], "need_walk": wk["need_walk"] + 3.0,
                         "need_fact": fc["need_walk"], "need_lean": fc["need_lean"], "tie_fact": fc["tie_line_n_mm"]})
        need = max(max(r["need_walk"], r["need_fact"], r["need_lean"]) for r in rows)
        if abs(need - foam) < 0.5:
            foam = need
            break
        foam = need
    m = load(fs.core)
    d = fs.core_t + 0.22
    P = S.bone_n("factored")
    core_shear = float(m.require("shear_strength_mpa")) * S.KD["hot_wet"] / (P / (math.pi * S.BONE_D) / d)
    crush_patch = float(m.require("compressive_strength_mpa")) * S.KD["hot_wet"] / (P / (math.pi * S.BONE_D ** 2 / 4))
    tie = max(r["tie_fact"] for r in rows)
    crush_tie = float(m.require("compressive_strength_mpa")) * S.KD["hot_wet"] / (tie / B_STAY)
    fi_f = max(r["fi_fact"] for r in rows)
    fi_w = max(r["fi_walk"] for r in rows)
    set_ = float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0
    foam_new = foam / (1 - set_)
    lam = S.sandwich_lam(fs.core, fs.core_t)
    # mass: sheet + edge seal + 6 clips (spreader fittings without pucks), lower backers z 50-195 kept (80 mm twill),
    # thicker rail foam; removes today's spreader (ledger) and today's full-length backers
    area = 2 * fs.half_w * (fs.z_hi - fs.z_lo)
    sheet = area * (lam.areal_mass_kg_m2() + RESIN) / 1000.0
    seal = S.edge_seal_g(_box(fs), lam.thickness)
    clips = S.fittings_mass_g(lam.thickness, pucks=False)
    lower = 2 * 80.0 * (fs.z_lo - 50.0) * TODAY_BACKER.areal_kg_m2() / 1000.0
    rho_f = float(load("xlpe_foam_l200").require("density_kg_m3"))
    foam_d = 2 * fs.rail_w * 420.0 * (foam_new - 10.0) * rho_f / 1e6
    spreader_today = ledger_layers()["spreader_g"]
    delta = sheet + seal + clips + lower + foam_d - spreader_today - TODAY_BACKER.mass_pair_g()
    res = {"key": fs.key, "fs": asdict(fs), "rows": rows, "sf_fpf": 1 / fi_f, "sf_fatigue": FAT_FI / fi_w,
           "core_shear_sf": core_shear, "crush_patch_sf": crush_patch, "crush_tie_sf": crush_tie,
           "skin_kpa": max(r["skin_kpa"] for r in rows), "foam_aged_needed": foam, "foam_new_needed": foam_new,
           "mass": {"sheet": sheet, "seal": seal, "clips": clips, "lower_backers": lower, "foam_delta": foam_d,
                    "removed_spreader": -spreader_today, "removed_backers": -TODAY_BACKER.mass_pair_g(), "delta": delta}}
    res["checks"] = {"fpf": res["sf_fpf"] >= 1, "fatigue": res["sf_fatigue"] >= 1,
                     "sandwich_local": min(core_shear, crush_patch, crush_tie) >= 1,
                     "skin": res["skin_kpa"] <= PEAK_KPA - MARGIN_KPA}
    res["passes"] = all(res["checks"].values())
    return res


def _box(fs: Framesheet):
    from shapely.geometry import box
    return box(-fs.half_w, fs.z_lo, fs.half_w, fs.z_hi)


# =====================================================================================================================
# masses (ledger)
# =====================================================================================================================
def ledger_layers(config: str = "corrie_b2_h1", size: str = "M") -> dict:
    """Back-system rows of the mass ledger, split into layers by the ledger's own sources."""
    from huntkit.mass import ledger as L
    rows = [r for r in L.parts(config, size) if r["system"] == "back"]
    spr = next(r for r in rows if "spreader" in r["id"])
    pan = next(r for r in rows if "back_panel" in r["id"])
    panels = {p["id"]: p for p in yaml.safe_load((PACK / "panels.yaml").read_text())["panels"]}
    ids = ("BP-01", "BP-02", "BP-08", "BP-05", "BP-03", "BP-04", "BP-07")
    split = {i: {"name": panels[i]["name"], "g": float(panels[i]["mass_g_total"])} for i in ids}
    ch = json.loads((ANALYSIS / "spreader_results.json").read_text())["chosen"]
    return {"config": config, "size": size, "back_total_g": float(L.by_system(config, size)["back"]),
            "spreader_g": float(spr["g"]), "panel_g": float(pan["g"]), "panel_split": split,
            "panel_split_sum": sum(v["g"] for v in split.values()),
            "spreader_split": {"sheet (twill / 7 mm R110 / twill)": ch["sheet_g"], "edge tubes": ch["tubes_g"],
                               "clips, pucks, pads, doublers, seal": ch["fittings_g"]}}


# =====================================================================================================================
# full spreader check with a rail variant patched in (as back_rail.patched / confirm)
# =====================================================================================================================
@contextlib.contextmanager
def patched(v: RailV):
    S = _S()
    saved = {k: getattr(S, k) for k in ("rail_eval", "GUTTER_HALF", "RAIL_L", "RAIL_W", "RAIL_T")}
    S._SKIN_CACHE.clear()
    try:
        S.rail_eval = lambda q, rail_=None, tissue_kpa=S.TISSUE_E_KPA, _v=v: section_of(_v, q, tissue_kpa)
        S.GUTTER_HALF = S.STAY_X - v.rail_w / 2.0
        S.RAIL_L, S.RAIL_W, S.RAIL_T = v.rail_l, v.rail_w, v.foam_t
        yield S
    finally:
        for k, val in saved.items():
            setattr(S, k, val)
        S._SKIN_CACHE.clear()


def confirm(v: RailV, h: float = 2.0) -> dict:
    S = _S()
    opt = {o.key: o for o in S.options()}[S.PRODUCTION_KEY]
    with patched(v) as S_:
        r = S_.evaluate(opt, h=h, step=None)
    keys = ("skin_peak_kpa", "skin_where", "skin_meat_only_kpa", "clear_walk_min", "clear_fact_min",
            "clear_fact_lean_min", "rail_indent_walk_mm", "sf_fpf", "sf_fatigue", "sandwich_sf_min", "checks", "passes")
    out = {k: r.get(k) for k in keys}
    out.update(variant=v.key)
    return out


# =====================================================================================================================
# along-the-rail map (for the pressure-map screen) and the lumbar-shadow sensitivity
# =====================================================================================================================
def rail_map(v: RailV, side: float, z_bone: float = 255.0, nz: int = 22) -> dict:
    """Skin pressure over one rail (x across, z along): uniform meat share + the bone reaction spread along the stay
    as a Hetenyi beam on the rail foundation (peak P beta / 2, the 1-D model's peak), evaluated section by section."""
    S, BR = _S(), _BR()
    H = max(BR.meat_force_n(E_REVC, 1.6) - S.bone_n("walk"), 0.0)
    q0 = H / 2.0 / v.rail_l
    s0 = section_of(v, q0)
    beta = (s0["k_line"] / (4.0 * S.stay_EI())) ** 0.25
    z = np.linspace(50.0, 50.0 + v.rail_l, nz)
    zeta = np.abs(z - z_bone)
    qz = q0 + side * beta / 2.0 * np.exp(-beta * zeta) * (np.cos(beta * zeta) + np.sin(beta * zeta))
    prof = [section_of(v, float(q)) for q in qz]
    return {"z": z.tolist(), "x": np.asarray(prof[0]["x"]).tolist(), "p": [np.asarray(p["p_kpa"]).tolist() for p in prof]}


# =====================================================================================================================
# study
# =====================================================================================================================
def _json(o):
    if isinstance(o, dict):
        return {str(k): _json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not math.isfinite(o):
        return 1e9
    return o


def today_full() -> dict:
    p = OUT / "repro_confirm.json"
    if p.exists():
        return json.loads(p.read_text())
    return json.loads((ANALYSIS / "back_rail_results.json").read_text())["confirm"]


# Recommendation rule (ASSUMPTIONS, stated in the doc): passes every check with >= 0.2 kPa margin, a core sold as
# stock sheet (ROHACELL 71 IG-F starts at 3 mm), rail foam, sleeve and mesh unchanged (released v3.1 patterns, only
# BP-08 changes), full 420 mm rail (the uniform-along-rail model cannot credit a shorter rail; see the lumbar shadow).
RECOMMENDED = "b_swR71c3_70"


def choose(rows: list[dict]) -> dict:
    """The lightest passing row (for the record) and the recommended row."""
    ok = [r for r in rows if r["passes"] and r["family"] != "today"]
    return min(ok, key=lambda r: r["mass_delta"]["total"]) if ok else None


def study(log=print) -> dict:
    side = bone_side_n()
    tf = today_full()
    t_w = skin(TODAY, E_REVC, side, "walk")
    t_f = skin(TODAY, E_REVC, side, "factored")
    t0 = {"walk": t_w, "fact": t_f}
    rows = []
    for v in rail_variants():
        r = evaluate_rail(v, side, tf, t0)
        rows.append(r)
        log(f"  {v.key:28} {r['peak_kpa']:6.2f} kPa  {r['mass_delta']['total']:+7.1f} g  "
            f"SF {r['backer_sf_fpf']:.2f}/{r['backer_sf_fatigue']:.2f}  pass {r['passes']}")
    fsh = []
    for ct, hw in ((7.0, 155.0), (4.0, 155.0), (7.0, 175.0), (4.0, 175.0)):
        fr = framesheet_eval(Framesheet(f"a2_fs_c{ct:g}_w{2 * hw:.0f}", core_t=ct, half_w=hw))
        fsh.append(fr)
        log(f"  a2 framesheet core {ct:g} half-width {hw:.0f}: FPF {fr['sf_fpf']:.2f} fat {fr['sf_fatigue']:.2f} local "
            f"{min(fr['core_shear_sf'], fr['crush_patch_sf'], fr['crush_tie_sf']):.2f} skin {fr['skin_kpa']:.1f} "
            f"foam {fr['foam_new_needed']:.1f} mm  dm {fr['mass']['delta']:+.1f} g")
    light = choose(rows)
    ch = next(r for r in rows if r["key"] == RECOMMENDED)
    assert ch["passes"], "recommended row must pass"
    led = ledger_layers()
    shadow = {k: skin(v, E_REVC, side, length=280.0)["peak_kpa"] for k, v in
              (("today", TODAY), ("chosen", _variant(ch["key"])))}
    return {"date": "2026-11-10", "bone_side_n": side, "today_full": tf, "today_walk": _strip(t_w), "rows": rows,
            "framesheet": fsh, "chosen": ch["key"], "lightest_passing": light["key"] if light else None, "ledger": led, "shadow_280_kpa": shadow}


def _strip(s: dict) -> dict:
    return {k: v for k, v in s.items() if k not in ("x", "p_kpa")}


def _variant(key: str) -> RailV:
    return next(v for v in rail_variants() if v.key == key)


# =====================================================================================================================
# screens
# =====================================================================================================================
def _save(fig, name: str) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    p = SCREENS / name
    fig.savefig(p, dpi=100)
    plt.close(fig)
    try:
        from huntkit.clothsim.report import shrink_png
        shrink_png(p)
    except Exception:  # noqa: BLE001
        pass
    return str(p.relative_to(REPO))


def plot_maps(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    side = res["bone_side_n"]
    ch = _variant(res["chosen"])
    fig, axs = plt.subplots(1, 3, figsize=(15, 7.2), gridspec_kw={"width_ratios": [1, 1, 1.25]})
    vmax = 16.0
    for ax, v, ttl in ((axs[0], TODAY, "today: 1 mm twill backer"), (axs[1], ch, "recommended: sandwich strip")):
        m = rail_map(v, side)
        X, Z = np.meshgrid(np.array(m["x"]) + 115.0, m["z"])
        im = ax.pcolormesh(X, Z, np.array(m["p"]), cmap="magma_r", vmin=0, vmax=vmax, shading="auto")
        cs = ax.contour(X, Z, np.array(m["p"]), levels=[10, 12, 14], colors=["#888", "#555", "k"], linewidths=1)
        ax.clabel(cs, fmt="%g kPa", fontsize=8)
        ax.axvspan(115 - v.backer.width / 2, 115 + v.backer.width / 2, color="#1e6fb0", alpha=0.08)
        pk = max(max(r) for r in m["p"])
        ax.set_title(f"{ttl}\npeak {pk:.1f} kPa (bone at a clip, z 255)", fontsize=11)
        ax.set_xlabel("x from the spine, mm (stay at 115)")
        ax.set_aspect("equal")
    axs[0].set_ylabel("z up the rail, mm")
    fig.colorbar(im, ax=axs[:2], shrink=0.8, label="skin pressure, kPa (walking 1.6 g, rev C meat, CG 190 mm)")
    ax = axs[2]
    for v, col, lab in ((TODAY, "#b03a2e", "today"), (ch, "#1e6fb0", "recommended")):
        s = skin(v, E_REVC, side)
        ax.plot(np.array(s["x"]) + 115, s["p_kpa"], color=col, lw=3, label=f"{lab}: {s['peak_kpa']:.1f} kPa")
    ax.axhline(PEAK_KPA, color="k", ls="--")
    ax.text(57, PEAK_KPA + 0.3, "14 kPa limit")
    ax.set_xlabel("x from the spine, mm")
    ax.set_ylabel("skin pressure across the rail at the worst z, kPa")
    ax.set_ylim(0, 17)
    ax.legend(loc="lower center")
    ax.set_title("Section at the bone (worst point)", fontsize=11)
    fig.suptitle("BL-005 rail skin pressure: today vs recommended (same model, same loads)", fontweight="bold")
    return _save(fig, f"{SHOT_PREFIX}1.png")


def plot_sections(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    ch = _variant(res["chosen"])
    rows = {r["key"]: r for r in res["rows"]}
    led = res["ledger"]
    fig = plt.figure(figsize=(15, 8.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1])
    for k, (v, ttl) in enumerate(((TODAY, "today"), (ch, "recommended"))):
        ax = fig.add_subplot(gs[k, 0])
        cx = 115.0
        y = 0.0
        ax.add_patch(mp.Rectangle((cx - v.rail_w / 2, y), v.rail_w, v.foam_t, fc="#d9d2c0", ec="k"))
        y += v.foam_t
        b = v.backer
        if b.kind == "sandwich":
            ax.add_patch(mp.Rectangle((cx - b.width / 2, y), b.width, 0.6, fc="#2b2e33", ec="k"))
            ax.add_patch(mp.Rectangle((cx - b.width / 2, y + 0.6), b.width, b.core_t, fc="#f2e6a0", ec="k"))
            ax.add_patch(mp.Rectangle((cx - b.width / 2, y + 0.6 + b.core_t), b.width, 0.6, fc="#2b2e33", ec="k"))
        else:
            ax.add_patch(mp.Rectangle((cx - b.width / 2, y), b.width, max(b.thickness, 0.8), fc="#2b2e33", ec="k"))
        y += max(b.thickness, 0.8)
        ax.add_patch(mp.Circle((cx, y + 14.07), 14.07, fc="#5b6068", ec="k"))
        ys = y + 28.1
        ax.add_patch(mp.Rectangle((0, ys), 121, 7.44, fc="#f2e6a0", ec="k", alpha=0.6))
        ax.text(10, ys + 9, "spreader sw110c7d (bag side, unchanged)", fontsize=9)
        ax.plot([0, 200], [-3, -3], color="#e3a08a", lw=6)
        ax.text(2, -10, "back", color="#a0533b", fontsize=9)
        ax.text(cx + v.rail_w / 2 + 3, 2, f"rail {v.rail_w:.0f} x {v.foam_t:.0f} L200", fontsize=9)
        ax.text(cx + b.width / 2 + 3, v.foam_t + 0.5, b.name, fontsize=8.5)
        r = rows[v.key]
        ax.set_title(f"{ttl}: half section at the stay (x 0 = spine). Skin {r['peak_kpa']:.1f} kPa, backer SF "
                     f"{min(r['backer_sf_fpf'], 99):.2f} / fatigue {min(r['backer_sf_fatigue'], 99):.2f}", fontsize=10.5)
        ax.set_xlim(-2, 200)
        ax.set_ylim(-14, 52)
        ax.set_aspect("equal")
        ax.set_yticks([])
    ax = fig.add_subplot(gs[:, 1])
    split = led["panel_split"]
    labels = [f"{k} {v['name']}" for k, v in split.items()] + [f"spreader: {k}" for k in led["spreader_split"]]
    vals_t = [v["g"] for v in split.values()] + list(led["spreader_split"].values())
    md = rows[ch.key]["mass_delta"]
    vals_r = list(vals_t)
    idx = {k: i for i, k in enumerate(split)}
    vals_r[idx["BP-08"]] += md["backer"]
    vals_r[idx["BP-02"]] += md["foam"]
    vals_r[idx["BP-05"]] += md["sleeve"]
    vals_r[idx["BP-01"]] += md["mesh"]
    yy = np.arange(len(labels))
    ax.barh(yy + 0.2, vals_t, 0.4, color="#b03a2e", label=f"today {led['back_total_g']:.0f} g")
    ax.barh(yy - 0.2, vals_r, 0.4, color="#1e6fb0", label=f"recommended {led['back_total_g'] + md['total']:.0f} g")
    for i, (a, b2) in enumerate(zip(vals_t, vals_r)):
        ax.text(max(a, b2) + 2, i, f"{a:.0f} -> {b2:.0f}", va="center", fontsize=8.5)
    ax.set_yticks(yy)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("g (ledger rows split by panels.yaml / spreader_results.json)")
    ax.set_xlim(0, 150)
    ax.legend(loc="lower right")
    ax.set_title(f"Back-system mass. Target 320 g: {'met' if led['back_total_g'] + md['total'] <= TARGET_G else 'NOT met'}",
                 fontsize=11)
    fig.suptitle("BL-005 sections and mass: the backer strip can be a sandwich; the spreader cannot also be the backer",
                 fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{SHOT_PREFIX}2.png")


# =====================================================================================================================
# run, doc
# =====================================================================================================================
def run(full: bool = False, log=print) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    res = study(log)
    ch = _variant(res["chosen"])
    old = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if full or old.get("confirm_chosen", {}).get("variant") != ch.key:
        log("full spreader check with the recommended rail (named positions, 2 mm)")
        res["confirm_chosen"] = confirm(ch)
    else:
        res["confirm_chosen"] = old["confirm_chosen"]
    res["screens"] = [plot_maps(res), plot_sections(res)]
    CACHE.write_text(json.dumps(_json(res), indent=1))
    return res


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    run(full="--full" in argv)


if __name__ == "__main__":
    main()
