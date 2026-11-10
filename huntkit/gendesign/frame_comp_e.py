"""Team E (FIBRE) of the printed-frame competition (designs/pack_5200/frame_comp/RULES.md, owner 2026-11-10).

Concept **LOOM**: a planar ladder frame printed FLAT (layer normal = frame y, wearer face on the plate) with
continuous carbon fibre (CCF) laid in the layer plane. Fibre is placed where it can be continuous:

- out-of-plane bending (the dominant frame load, bag CG aft) is carried by **fibre flange layers** at the bag
  face and the wearer face of every member (I-beam action through the layer stack);
- in-plane bending and the stay / bar corners are carried by **concentric fibre rings** that run round each
  window of the ladder (stay -> corner -> bar -> corner -> stay) without a cut;
- matrix-only (chopped-CF nylon) regions carry the fixed interfaces: crown sleeve bores, pawl housing, hip
  inserts, fairlead cheeks.

Two segments (bed 300 x 300 mm): lower z 0..290 (lumbar panel, hip pivot), upper z 290..545 (mid bar, upper bar,
crown sleeves), joined on each stay by a bolted clamshell splice (4 x M5 Ti per stay, no adhesive).

Analysis (beam level, the same load source the production check uses): the frame.yaml v2 beam model of HA-LS-1
rev C, every case at torso 15 / 19 / 23 in, bag couple on the crown bar AND on IM3, with the stays, bars and
lumbar strips replaced by :class:`PrintedSection` (transformed section of fibre + matrix, discretised). Checks per
section: fibre tension / compression (hot/wet 0.8, impact 0.65 on compression), matrix normal stress,
interlayer shear (ILSS: transverse shear across the layer stack + torsion), in-plane shear, fatigue at 0 -> 1.6 g
(fibre FI <= 0.5, matrix / interlayer <= 0.3 of the knocked-down strength), creep-rupture at 1 g (matrix <= 0.4),
global buckling (beam eigenvalue >= 1.5 x factor), splice-joint bolt bearing / shear, and the released crown with
the new frame stiffness (crown legs, spine, bar, corner bonds, bushings) via ``frame_cg_recheck._crown_rows``.

Every material number comes from ``data/materials/composites/onyx_ccf_markforged.yaml`` or is an ASSUMPTION in
:data:`ALLOW` with the coupon test that must confirm it (docs/research/frame_comp_E.md).

Run: ``python -m huntkit.gendesign.frame_comp_e``   (about 2 min on 1 core)
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.fea.sections import Section

TEAM = "E"
OUT = REPO_ROOT / "designs" / "pack_5200" / "frame_comp" / "E"
DOC = REPO_ROOT / "designs" / "pack_5200" / "analysis" / "frame_comp_E.md"
SCREENS = REPO_ROOT / "outputs" / "screens"
SHOT = "20261110_compE"
TORSOS = (15.0, 19.0, 23.0)
TAGS = {"crown_bar": "C", "strap_upper": "C_im3"}
G_WALK = 1.6

# ============================================================================ material allowables
def _mat():
    from huntkit.materials import load
    return load("onyx_ccf_markforged")


M = _mat()
E_F = float(M.require("E1_mpa"))                    # 60 GPa fibre strand along the path (Mark Two datasheet)
E_M = float(M.require("youngs_modulus_xy_mpa"))     # 2.4 GPa Onyx
RHO_F = float(M.require("fiber_density_kg_m3"))     # 1400
RHO_M = float(M.require("density_kg_m3"))           # 1200
XT = float(M.require("Xt_mpa"))                     # 800
XC = float(M.require("Xc_mpa"))                     # 320 (older Markforged sheet, the lower of 320 / 420)
SM_T = float(M.require("tensile_strength_xy_mpa"))  # 40 Onyx in-plane
SM_Z = float(M.require("tensile_strength_z_mpa"))   # 30 Onyx across layers

ALLOW = {
    # fibre-dominated: HA-LS-1 composite knockdowns (load_standard.md section 4)
    "kd_fibre_hw": 0.8, "kd_impact_comp": 0.65,
    # ASSUMPTION (coupon E-1): fibre-region values from vendor UD coupons are de-rated 0.85 for the
    # thin fibre bands, turns and start/stop points of a real part (Pertuz 2020 measured 165 MPa on mixed
    # Onyx/CCF specimens, far below the 800 MPa all-fibre coupon)
    "kd_part": 0.85,
    # matrix-dominated: PA6 matrix, 40 C wet. ASSUMPTION 0.6 (record modulus_40c_wet_ratio 0.6; nylon
    # flexural modulus -60 % after immersion, PMC8587952). Coupon E-2 / E-3 conditioned.
    "kd_matrix_hw": 0.6,
    # ASSUMPTION (coupon E-2, ASTM D2344 short-beam shear, printed flat, 0.125 mm layers): dry ILSS 14 MPa,
    # half the 28 MPa published for printed continuous CF/PA6; published range 2.8-34 MPa.
    "ilss_mpa": 14.0,
    # ASSUMPTION (coupon E-3, Iosipescu / +-45 tension): in-plane shear of the layer, Onyx/CCF region 20 MPa
    "s_inplane_mpa": 20.0,
    # fatigue at 1e5 cycles (HA-LS-1: CFRP FI <= 0.5 at 1.6 g; matrix rule 0.3 as PAHT); creep-rupture 0.4
    "fat_fibre": 0.5, "fat_matrix": float(M.get("fatigue_1e5_ratio", 0.3)),
    "creep_matrix": float(M.get("creep_rupture_8h_40c_ratio", 0.4)),
    # ASSUMPTION (coupon E-4, pin bearing ASTM D5961 on a fibre-ringed M5 hole): bearing 60 MPa dry
    # (1.5 x Onyx tensile; fibre rings round the hole), x matrix hot/wet
    "bearing_mpa": 60.0,
}
FIBRE_W = 0.9      # strand width, mm (record: fiber_strand_area 0.11 mm2 = 0.125 x 0.9)
LAYER = 0.125      # CCF layer height, mm
WALL = 0.8         # 2 matrix walls of 0.4
SKIN = 0.5         # 4 matrix roof / floor layers of 0.125


def fibre_allow():
    xt = XT * ALLOW["kd_fibre_hw"] * ALLOW["kd_part"]
    xc = XC * ALLOW["kd_fibre_hw"] * ALLOW["kd_impact_comp"] * ALLOW["kd_part"]
    return xt, xc


def matrix_allow():
    k = ALLOW["kd_matrix_hw"]
    return {"ilss": ALLOW["ilss_mpa"] * k, "s_in": ALLOW["s_inplane_mpa"] * k, "sig": SM_T * k}


# ============================================================================ printed section
class _Lam:      # frame.py labels composite members by laminate.plies[0].name
    class _P:
        name = "onyx_ccf_markforged"
    plies = [_P()]


@dataclass
class PrintedSection(Section):
    """Rectangle b (local y) x h (local z), printed with the layer normal along local z (flat print: local z =
    frame y for every member of this frame). Optional central bore d (crown-leg sleeve). Fibre: flange bands of
    thickness ``tf`` under a ``SKIN`` matrix skin at both z faces (full layers of concentric fibre), plus ``nr``
    concentric rings at both y edges in every layer between the flanges. Matrix elsewhere (core density
    ``rho_c`` of solid, solid round a bore). Discretised on a 0.1 mm grid for the transformed section."""
    params: dict = field(default_factory=dict)
    EA: float = 0.0
    EIy: float = 0.0
    EIz: float = 0.0
    GJ: float = 0.0
    density_kg_m3: float = 0.0
    mass_g_per_mm: float = 0.0
    fibre_mm2: float = 0.0
    laminate: object = None
    _grid: tuple = None

    def stiffness(self, E=None, G=None) -> dict:
        Gs = self.GJ / max(self.J, 1e-9)
        return {"EA": self.EA, "EIy": self.EIy, "EIz": self.EIz, "GJ": self.GJ,
                "GAy": Gs * self.A * 5 / 6, "GAz": Gs * self.A * 5 / 6}

    # ---------------------------------------------------------------- stresses
    def components(self, N, Vy, Vz, T, My, Mz) -> dict:
        """Stress measures (MPa) at limit-load resultants (beam sign convention of sections.py)."""
        y, z, E, kind, dA, _ = self._grid
        eps = N / self.EA + My * z / self.EIy - Mz * y / self.EIz
        sf = np.where(kind == 2, E * eps, 0.0)
        sm = np.where(kind == 1, E * eps, 0.0)
        out = {"sig_f_t": float(max(sf.max(), 0.0)), "sig_f_c": float(max(-sf.min(), 0.0)),
               "sig_m": float(np.abs(sm).max())}
        # interlayer shear: Vz across planes z = z0 (layer interfaces); in-plane: Vy across y = y0
        out["tau_vz"] = abs(Vz) * self._qmax("z")
        out["tau_vy"] = abs(Vy) * self._qmax("y")
        tz, ty = self._torsion(abs(T))
        out["tau_il"] = out["tau_vz"] + tz          # side walls: torsion flow crosses the layer interfaces
        out["tau_in"] = out["tau_vy"] + ty
        return out

    def _qmax(self, ax: str) -> float:
        """max over the cut position of Q_E(c) / (EI * width(c)), per unit shear force (1/mm2)."""
        key = "_q" + ax
        if key not in self.params:
            y, z, E, kind, dA, rho = self._grid
            c = z if ax == "z" else y
            EI = self.EIy if ax == "z" else self.EIz
            d = self.params["dgrid"]
            cuts = np.linspace(c.min() + d, c.max() - d, 61)
            best = 0.0
            for c0 in cuts:
                above = (c > c0) & (kind > 0)
                Q = float((E[above] * c[above] * dA).sum())
                band = np.abs(c - c0) < d / 2 + 1e-9
                # shear-carrying width: sparse core counts by its relative density
                w = float(np.where(kind[band] == 2, 1.0, rho[band]).sum()) * d / max(
                    1, len(np.unique(np.round(c[band], 6))))
                if w > 0:
                    best = max(best, abs(Q) / (EI * w))
            self.params[key] = best
        return self.params[key]

    def _torsion(self, T):
        p = self.params
        b, h, d = p["b"], p["h"], p.get("bore", 0.0)
        if d > 0:            # thin-wall closed box round the bore (Bredt)
            ts, tt = (b - d) / 2, (h - d) / 2
            Am = (b - ts) * (h - tt)
            q = T / (2 * Am)
            return q / ts, q / tt
        a_, c_ = max(b, h), min(b, h)          # solid rectangle, Saint-Venant
        r = a_ / c_
        alpha = 1 / (3 + 1.8 / r)              # Roark: tau_max = T / (alpha a c^2)
        tau = T / (alpha * a_ * c_ ** 2)
        return tau, tau                        # conservative: max on both plane families

    def _hull(self, k: int):
        key = f"_hull{k}"
        if key not in self.params:
            y, z, E, kind, dA, _ = self._grid
            sel = kind == k
            if not sel.any():
                self.params[key] = (np.zeros((0, 2)), np.zeros(0))
            else:
                pts = np.c_[y[sel], z[sel]]
                try:
                    from scipy.spatial import ConvexHull
                    v = ConvexHull(pts).vertices
                except Exception:          # degenerate (one row of cells)
                    v = np.arange(len(pts))
                self.params[key] = (pts[v], E[sel][v])
        return self.params[key]

    def fi_batch(self, F: np.ndarray, factor) -> dict:
        """Vectorised :meth:`fi` over an (n, 6) array of resultants; ``factor`` scalar or (n,)."""
        F = np.atleast_2d(np.asarray(F, float))
        fac = np.broadcast_to(np.asarray(factor, float), (F.shape[0],))
        N, Vy, Vz, T, My, Mz = F.T
        xt, xc = fibre_allow()
        ma = matrix_allow()
        out = {}
        for k, nm in ((2, "fibre"), (1, "matrix")):
            pts, Ek = self._hull(k)
            if len(pts) == 0:
                st = np.zeros(F.shape[0]); sc = st
            else:
                eps = N[:, None] / self.EA + My[:, None] * pts[None, :, 1] / self.EIy \
                    - Mz[:, None] * pts[None, :, 0] / self.EIz
                sig = eps * Ek[None, :]
                st, sc = np.maximum(sig.max(1), 0), np.maximum(-sig.min(1), 0)
            if k == 2:
                out["fibre_t"], out["fibre_c"] = st / xt, sc / xc
            else:
                out["matrix"] = np.maximum(st, sc) / ma["sig"]
        tz, ty = self._torsion(np.abs(T))
        out["interlayer"] = (np.abs(Vz) * self._qmax("z") + tz) / ma["ilss"]
        out["inplane_shear"] = (np.abs(Vy) * self._qmax("y") + ty) / ma["s_in"]
        return {k: v * fac for k, v in out.items()}

    def fi(self, N, Vy, Vz, T, My, Mz, factor: float = 1.0) -> dict:
        """Failure indices at factor x the given resultants (knocked-down strengths)."""
        c = self.components(N, Vy, Vz, T, My, Mz)
        xt, xc = fibre_allow()
        ma = matrix_allow()
        f = {"fibre_t": c["sig_f_t"] / xt, "fibre_c": c["sig_f_c"] / xc,
             "matrix": c["sig_m"] / ma["sig"], "interlayer": c["tau_il"] / ma["ilss"],
             "inplane_shear": c["tau_in"] / ma["s_in"]}
        return {k: v * factor for k, v in f.items()}

    def failure(self, N, Vy, Vz, T, My, Mz, knockdown=None, criterion=None, n: int = 0) -> dict:
        f = self.fi(N, Vy, Vz, T, My, Mz)
        k = max(f, key=f.get)
        return {"fi": float(f[k]), "mode": k, "sf": 1 / f[k] if f[k] > 0 else np.inf, **f}


def printed_section(b: float, h: float, tf: float, nr: int = 0, bore: float = 0.0, rho_c: float = 1.0,
                    d: float = 0.1, name: str = "") -> PrintedSection:
    ys = np.arange(-b / 2 + d / 2, b / 2, d)
    zs = np.arange(-h / 2 + d / 2, h / 2, d)
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    kind = np.ones_like(Y, dtype=int)
    rho = np.full_like(Y, rho_c)
    if bore > 0:
        kind[np.hypot(Y, Z) < bore / 2] = 0
        near = np.hypot(Y, Z) < bore / 2 + 2.0          # solid matrix ring round the bore (2 mm)
        rho[near] = 1.0
    zf0, zf1 = h / 2 - SKIN - tf, h / 2 - SKIN
    flange = (np.abs(Z) >= zf0) & (np.abs(Z) <= zf1) & (np.abs(Y) <= b / 2 - WALL)
    rings = (np.abs(Y) >= b / 2 - WALL - nr * FIBRE_W) & (np.abs(Y) <= b / 2 - WALL) & (np.abs(Z) < zf0)
    for msk in (flange, rings):
        kind[msk & (kind > 0)] = 2
    skin = (np.abs(Z) > zf1) | (np.abs(Y) > b / 2 - WALL)
    rho[skin] = 1.0
    E = np.where(kind == 2, E_F, np.where(kind == 1, E_M * rho, 0.0))
    dA = d * d
    keep = kind.ravel() > 0
    y, z, Ee, kk = Y.ravel()[keep], Z.ravel()[keep], E.ravel()[keep], kind.ravel()[keep]
    rr = rho.ravel()[keep]
    A = float(keep.sum() * dA)
    EA = float(Ee.sum() * dA)
    EIy = float((Ee * z ** 2).sum() * dA)
    EIz = float((Ee * y ** 2).sum() * dA)
    Af = float((kk == 2).sum() * dA)
    mass_lin = float(((kk == 2) * RHO_F + (kk == 1) * RHO_M * rr).sum() * dA) * 1e-6   # g/mm
    Iy, Iz = b * h ** 3 / 12, h * b ** 3 / 12
    if bore > 0:
        Iy -= np.pi * bore ** 4 / 64
        Iz -= np.pi * bore ** 4 / 64
    # torsion stiffness: matrix shear modulus (fibre adds little to G); Bredt or Saint-Venant
    G = E_M / (2 * 1.35)
    if bore > 0:
        ts, tt = (b - bore) / 2, (h - bore) / 2
        Am = (b - ts) * (h - tt)
        J = 4 * Am ** 2 / (2 * (b - ts) / tt + 2 * (h - tt) / ts)
    else:
        a_, c_ = max(b, h), min(b, h)
        J = a_ * c_ ** 3 * (1 / 3 - 0.21 * c_ / a_ * (1 - c_ ** 4 / (12 * a_ ** 4)))
    s = PrintedSection("printed_ccf", {"b": b, "h": h, "tf": tf, "nr": nr, "bore": bore}, A, Iy, Iz, J,
                       Wt=J / min(b, h), ymax=b / 2, zmax=h / 2, Asy=5 * A / 6, Asz=5 * A / 6, composite=True,
                       params={"b": b, "h": h, "tf": tf, "nr": nr, "bore": bore, "rho_c": rho_c, "dgrid": d,
                               "name": name},
                       EA=EA, EIy=EIy, EIz=EIz, GJ=G * J, density_kg_m3=mass_lin / A * 1e6,
                       mass_g_per_mm=mass_lin, fibre_mm2=Af, laminate=_Lam(), _grid=(y, z, Ee, kk, dA, rr))
    return s


# ============================================================================ the design
# local y = in-plane width (frame x for stays, frame z for bars / lumbar strips); local z = frame y (depth).
DESIGN = {
    # lower stays z 0-130: solid, deep enough to hold the lumbar panel lands and the hip-belt loads
    "stay_lower": dict(b=18.0, h=26.0, tf=1.25, nr=2, rho_c=0.35),
    # upper stays z 130-530: the crown-leg sleeve (18 mm bore over the whole leg travel, z 171-374 at
    # torso 15-23 for the low bushing) with fibre flanges above / below the bore and rings in the side walls
    "stay_upper": dict(b=26.0, h=26.0, tf=1.25, nr=3, bore=18.0),
    "mid_bar": dict(b=16.0, h=16.0, tf=0.5, nr=1, rho_c=0.35),
    "upper_bar": dict(b=26.0, h=24.0, tf=1.5, nr=3, rho_c=0.35),
    # lumbar: an open lattice, not a panel. Three horizontal ribs (z 50 / 120 / 190) and a centre column carry
    # the hip-pivot load to the stays; light ties close the grid (fixed nodes for the meat face loads).
    "lumbar_rib": dict(b=14.0, h=14.0, tf=0.75, nr=2, rho_c=0.35),
    "lumbar_spine": dict(b=16.0, h=14.0, tf=0.75, nr=2, rho_c=0.35),
    "lumbar_tie": dict(b=6.0, h=6.0, tf=0.0, nr=1, rho_c=1.0),
    "lumbar_shear_scale": 0.02,      # the open lattice has no panel shear (diagonals kept, near zero)
}
LUMBAR_GROUPS = ("lumbar_rib", "lumbar_spine", "lumbar_tie")


def sections(design: dict = DESIGN) -> dict:
    out = {}
    for g in ("stay_lower", "stay_upper", "mid_bar", "upper_bar") + LUMBAR_GROUPS:
        out[g] = printed_section(name=g, **design[g])
    return out


def lumbar_group(mem_id: str) -> str:
    """plh{i}{j}: horizontal strip row i; plv{i}{j}: vertical strip column j (pack5200 grillage ids)."""
    if mem_id.startswith("plh"):
        return "lumbar_rib" if int(mem_id[3]) in (0, 2, 4) else "lumbar_tie"
    return "lumbar_spine" if int(mem_id[4]) == 2 else "lumbar_tie"


def model(torso: float, design: dict = DESIGN, posts: bool = False) -> dict:
    """frame.yaml v2 beam model (released crown with the rev C fix) with the printed members swapped in."""
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    m = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(torso), extension_posts=posts), 95.0)
    secs = sections(design)
    for mem in m["members"]:
        g = mem["group"]
        key = g[:-2] if g.endswith(("_L", "_R")) else g
        if key in secs:
            mem["section"] = secs[key]
            mem["material"] = None
        elif g == "lumbar_plate":
            lg = lumbar_group(mem["id"])
            mem["section"] = secs[lg]
            mem["material"] = None
            mem["group"] = lg
        elif g == "lumbar_plate_shear":
            mem["section"] = copy.copy(mem["section"])
            mem["section"].A = mem["section"].A * design["lumbar_shear_scale"]
    return m


# ============================================================================ runs
GROUPS = ("stay_lower", "stay_upper", "mid_bar", "upper_bar") + LUMBAR_GROUPS


def _key(g):
    return g[:-2] if g.endswith(("_L", "_R")) else g


def run_cases(design: dict = DESIGN, torsos=TORSOS, buckling: bool = True, log=print) -> dict:
    """Every rev C case set x torso: printed-member FI per mode, crown rows, splice forces, loads for fatigue."""
    from huntkit.fea.load_standard import ls1_envelope
    from . import frame_cg_recheck as R
    env = ls1_envelope("C")
    rows, crown = [], []
    t0 = time.time()
    for t in torsos:
        fm = model(t, design)
        fmp = None
        for variant, cases in env.items():
            tag = TAGS[variant]
            for c in cases:
                c = copy.copy(c)
                c.params = dict(c.params)
                c.buckling = buckling and variant == "crown_bar" and c.kind != "setdown"
                m = fm
                if c.name == "tall_load_posts":
                    fmp = fmp or model(t, design, posts=True)
                    m = fmp
                res = c.run(m)
                req = float(c.required_sf)
                secs = {mem["id"]: mem["section"] for mem in m["members"]}
                per = {}
                for mr in res.members:
                    g = _key(mr["group"])
                    if g not in GROUPS:
                        continue
                    sec = secs[mr["id"]]
                    for F in mr["end_forces"]:
                        f = sec.fi(*F, factor=req)
                        f1 = sec.fi(*F, factor=1.0)
                        cur = per.setdefault(g, {"fi": {}, "fi_limit": {}, "member": {}, "F": []})
                        cur["F"].append([float(v) for v in F])
                        for k, v in f.items():
                            if v > cur["fi"].get(k, -1):
                                cur["fi"][k] = float(v)
                                cur["member"][k] = mr["id"]
                                cur["fi_limit"][k] = float(f1[k])
                splice = _splice_forces(res, m)
                cr = R._crown_rows(res, _crown_view(m), c)
                rows.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": req,
                             "g": float(c.g_factor), "groups": per, "splice": splice,
                             "buckling": cr.get("buckling")})
                crown.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": req, **cr})
        if log:
            log(f"  [E] torso {t:g} in, {time.time() - t0:.0f} s")
    return {"rows": rows, "crown": crown}


# ============================================================================ sizing (fully-stressed, discrete)
CANDS = {
    "stay_upper": dict(b=(21, 22, 23, 24, 26), h=(21, 22, 23, 24, 26), tf=(0.5, 0.75, 1.0, 1.25, 1.5, 2.0),
                       nr=(1, 2, 3, 4), bore=(18.0,), rho_c=(1.0,)),
    "stay_lower": dict(b=(12, 14, 16, 18, 20), h=(16, 18, 20, 22, 26), tf=(0.5, 0.75, 1.0, 1.25, 1.5),
                       nr=(1, 2, 3), rho_c=(0.2, 0.35, 0.6, 1.0)),
    "mid_bar": dict(b=(8, 10, 12, 14, 16), h=(8, 10, 12, 14, 16), tf=(0.25, 0.5, 0.75, 1.0),
                    nr=(1, 2), rho_c=(0.2, 0.35, 1.0)),
    "upper_bar": dict(b=(14, 18, 22, 26, 30), h=(14, 18, 22, 26), tf=(0.5, 1.0, 1.5, 2.0, 2.5),
                      nr=(1, 2, 4), rho_c=(0.2, 0.35, 1.0)),
    "lumbar_rib": dict(b=(8, 10, 12, 14, 16, 20), h=(8, 10, 12, 14, 16, 18), tf=(0.25, 0.5, 0.75, 1.0, 1.5),
                       nr=(1, 2, 3), rho_c=(0.2, 0.35, 1.0)),
    "lumbar_spine": dict(b=(8, 10, 12, 14, 16, 20), h=(8, 10, 12, 14, 16, 18), tf=(0.25, 0.5, 0.75, 1.0, 1.5),
                         nr=(1, 2, 3), rho_c=(0.2, 0.35, 1.0)),
    "lumbar_tie": dict(b=(4, 6, 8, 10), h=(4, 6, 8, 10), tf=(0.0, 0.25, 0.5), nr=(0, 1, 2), rho_c=(1.0,)),
}
TARGET = 1.05      # sizing target margin (5 % reserve on every check)


def group_margins(sec: "PrintedSection", rows: list, g: str) -> dict:
    """Strength / fatigue / creep margins of one candidate section on the stored member end forces of group g."""
    FF, fac, sc = _stack(rows, g)
    if FF is None:
        return {"strength": np.inf, "fatigue": np.inf, "creep": np.inf}
    f = sec.fi_batch(FF, fac)
    st = 1 / max(max(v.max() for v in f.values()), 1e-12)
    f1 = sec.fi_batch(FF[sc], 1.0)
    fa, cr = np.inf, np.inf
    for k, v in f1.items():
        ratio = ALLOW["fat_fibre"] if k.startswith("fibre") else ALLOW["fat_matrix"]
        fa = min(fa, ratio / max(v.max() * G_WALK, 1e-12))
        if not k.startswith("fibre"):
            cr = min(cr, ALLOW["creep_matrix"] / max(v.max(), 1e-12))
    return {"strength": st, "fatigue": fa, "creep": cr}


_STACK = {}


def _stack(rows: list, g: str):
    key = (id(rows), g)
    if key not in _STACK:
        F, fac, sc = [], [], []
        for r in rows:
            d = r["groups"].get(g)
            if not d:
                continue
            F += d["F"]
            fac += [r["factor"]] * len(d["F"])
            sc += [r["case"] == "static_carry"] * len(d["F"])
        _STACK[key] = (np.asarray(F) if F else None, np.asarray(fac), np.asarray(sc, bool))
    return _STACK[key]


def size_group(g: str, rows: list, cands: dict | None = None, target: float = TARGET) -> tuple:
    """Lightest candidate of group g whose margins all reach ``target`` on the given force set."""
    import itertools
    cands = cands or CANDS[g]
    keys = list(cands)
    best = None
    opts = []
    for vals in itertools.product(*(cands[k] for k in keys)):
        kw = dict(zip(keys, vals))
        if kw.get("bore", 0) and (min(kw["b"], kw["h"]) - kw["bore"]) / 2 < 1.5:
            continue
        if kw["tf"] > kw["h"] / 2 - SKIN - 1.0:
            continue
        sec = printed_section(d=0.2, **kw)
        opts.append((sec.mass_g_per_mm, kw, sec))
    opts.sort(key=lambda o: o[0])
    for gpm, kw, sec in opts:
        m = group_margins(sec, rows, g)
        if min(m.values()) >= target:
            return kw, m, gpm
        best = best or (kw, m, gpm)
    # nothing passes: return the one with the best worst margin among the heaviest third
    top = max(opts[-max(1, len(opts) // 3):], key=lambda o: min(group_margins(o[2], rows, g).values()))
    return top[1], group_margins(top[2], rows, g), top[0]


def size(design: dict | None = None, iters: int = 3, log=print) -> tuple:
    """Fully-stressed resizing: solve, re-pick every group on the new forces, repeat."""
    design = copy.deepcopy(design or DESIGN)
    hist = []
    for it in range(iters):
        R_ = run_cases(design, buckling=False, log=None)
        for g in CANDS:
            kw, m, gpm = size_group(g, R_["rows"])
            design[g] = kw
            hist.append({"iter": it, "group": g, "design": kw, "margins": m, "g_per_mm": gpm})
            if log:
                log(f"  [E size {it}] {g}: {kw} margins {[round(v, 2) for v in m.values()]} {gpm:.3f} g/mm")
    return design, hist


def _crown_view(m: dict) -> dict:
    """The crown checks of pack5200 treat a composite stay as a carbon tube hosting the leg bushings (ring crush).
    The printed sleeve is checked here instead (:func:`sleeve_check`), so hide the printed sections from them."""
    from huntkit.fea.sections import from_spec
    dummy = from_spec(dict(m["params"]["stay_section"]) if isinstance(m["params"]["stay_section"], dict)
                      else m["params"]["stay_section"])
    m2 = dict(m)
    m2["members"] = [dict(x, section=dummy) if isinstance(x["section"], PrintedSection) else x for x in m["members"]]
    return m2


# ============================================================================ splice joint (z 290)
SPLICE_Z = 290.0
SPLICE = {"n_bolts": 4, "d": 5.0, "rows_pitch": 40.0, "t_bear": 13.0, "bolt_shear_n": 0.6 * 900 * 14.2 * 0.6}
# M5 grade-5 Ti (Ti-6Al-4V, UTS ~900 MPa): single-shear capacity 0.6 x UTS x 14.2 mm2 stress area, x 0.6
# design margin (ASSUMPTION; ISO 898 style 0.6 shear/tension). t_bear: each half-shell 13 mm of the 26 mm depth.


def _splice_forces(res, m) -> list:
    """Stay resultants at the splice station (the stay element that spans SPLICE_Z) on both sides."""
    out = []
    for mr in res.members:
        if not mr["group"].startswith("stay_upper"):
            continue
        a, b = (m["nodes"][n] for n in next(x for x in m["members"] if x["id"] == mr["id"])["nodes"])
        if min(a[2], b[2]) <= SPLICE_Z <= max(a[2], b[2]):
            s = (SPLICE_Z - a[2]) / (b[2] - a[2])
            F = (1 - s) * np.asarray(mr["end_forces"][0]) + s * np.asarray(mr["end_forces"][1])
            out.append([float(v) for v in F])
    return out


def splice_check(F, factor: float, design: dict = DESIGN) -> dict:
    """Clamshell splice (half-lap split through the bore plane, y-stacked half-shells, 4 x M5 through the side
    walls, two rows 40 mm apart along z). Flange force = |My| / lever + |N| / 2 is transferred by the bolt group
    in shear (composite-beam action of the half-shells); |Mz| by the bolt-group couple; |Vy|, |Vz| shared."""
    N, Vy, Vz, T, My, Mz = (abs(v) * factor for v in F)
    p = design["stay_upper"]
    lever = p["h"] - 2 * SKIN - p["tf"]
    s = SPLICE
    flange = My / lever + N / 2
    # bolt group: 2 rows x 2 bolts (x = +-11 mm side walls); Mz couple across x, T couple across x as y-force
    per_bolt = np.hypot(flange / s["n_bolts"] + Mz / (2 * 22.0) / 2, (Vy + Vz) / s["n_bolts"] + T / (22.0 * 2))
    bear = per_bolt / (s["d"] * s["t_bear"])
    ma = ALLOW["bearing_mpa"] * ALLOW["kd_matrix_hw"]
    return {"per_bolt_n": float(per_bolt), "bearing_mpa": float(bear), "fi_bearing": float(bear / ma),
            "fi_bolt": float(per_bolt / s["bolt_shear_n"]), "flange_n": float(flange)}


# ============================================================================ summary
def summarize(R_: dict, design: dict = DESIGN) -> dict:
    rows = R_["rows"]
    out = {"strength": {}, "fatigue": {}, "creep": {}, "splice": {}, "buckling": None, "crown": {}}
    # strength margin = 1 / max factored FI per group (worst over every set)
    for r in rows:
        for g, d in r["groups"].items():
            for k, v in d["fi"].items():
                cur = out["strength"].setdefault(g, {"fi": 0.0})
                if v > cur["fi"]:
                    out["strength"][g] = {"fi": v, "mode": k, "set": f"{r['scenario']}:{r['case']}|{r['torso']:g}",
                                          "member": d["member"][k]}
    for g, d in out["strength"].items():
        d["margin"] = 1 / d["fi"]
    # fatigue: C1 static carry (1 g) x 1.6, both couple variants; fibre / matrix ratios
    sc = [r for r in rows if r["case"] == "static_carry"]
    for r in sc:
        for g, d in r["groups"].items():
            for k, v in d["fi_limit"].items():
                ratio = ALLOW["fat_fibre"] if k.startswith("fibre") else ALLOW["fat_matrix"]
                m_ = ratio / max(v * G_WALK, 1e-9)
                cur = out["fatigue"].get(g)
                if cur is None or m_ < cur["margin"]:
                    out["fatigue"][g] = {"margin": m_, "mode": k, "set": f"{r['scenario']}:static_carry|{r['torso']:g}"}
                if not k.startswith("fibre"):
                    mc = ALLOW["creep_matrix"] / max(v, 1e-9)
                    cc = out["creep"].get(g)
                    if cc is None or mc < cc["margin"]:
                        out["creep"][g] = {"margin": mc, "mode": k,
                                           "set": f"{r['scenario']}:static_carry|{r['torso']:g}"}
    # splice: factored strength, and fatigue (C1 x 1.6 vs 0.3 bearing)
    worst, worst_f = None, None
    for r in rows:
        for F in r["splice"]:
            c = splice_check(F, r["factor"], design)
            m_ = 1 / max(c["fi_bearing"], c["fi_bolt"])
            if worst is None or m_ < worst["margin"]:
                worst = {"margin": m_, "set": f"{r['scenario']}:{r['case']}|{r['torso']:g}", **c}
            if r["case"] == "static_carry":
                cf = splice_check(F, G_WALK, design)
                mf = ALLOW["fat_matrix"] / cf["fi_bearing"]
                if worst_f is None or mf < worst_f["margin"]:
                    worst_f = {"margin": mf, "set": f"{r['scenario']}:static_carry|{r['torso']:g}", **cf}
    out["splice"] = {"strength": worst, "fatigue": worst_f}
    bk = [(r["buckling"], f"{r['scenario']}:{r['case']}|{r['torso']:g}") for r in rows if r.get("buckling")]
    if bk:
        b = min(bk)
        out["buckling"] = {"margin": b[0], "set": b[1]}
    # crown with the new frame stiffness (same rules as rev_c_verification)
    for c in R_["crown"]:
        tag = f"{c['scenario']}:{c['case']}|{c['torso']:g}"
        for k, (sf, mid) in c["members"].items():
            cur = out["crown"].get(k)
            if cur is None or sf < cur["margin"]:
                out["crown"][k] = {"margin": sf, "set": tag}
        for k, (a, p, _) in c["joints"].items():
            for nm, v in ((f"{k} avg", a), (f"{k} Volkersen peak", p)):
                cur = out["crown"].get(nm)
                if cur is None or v < cur["margin"]:
                    out["crown"][nm] = {"margin": v, "set": tag}
        for k, v in c["bushings"].items():
            cur = out["crown"].get(k)
            if cur is None or v < cur["margin"]:
                out["crown"][k] = {"margin": v, "set": tag}
    return out


# ============================================================================ mass
# Matrix-only features that carry the fixed interfaces. ASSUMPTION allowances (g), each to be weighed on the
# first article; volumes estimated from the released features at Onyx density 1.2.
FEATURES_G = {
    "pawl housing + rack guides on the upper bar (304 bushing cheeks)": 22.0,
    "hip pivot boss, 4 x M5 heat-set inserts, lumbar pad seat": 16.0,
    "8 fairlead cheeks + IM2/IM3 hook bosses + hinge-pin lugs + under-strap pins": 30.0,
    "spreader clip lands (z 166 / 260 / 400) + bottom-tab pads": 10.0,
    "stay feet (boot lands) + crown sleeve top cuffs": 14.0,
    "corner fillets (fibre turn radius >= 10 mm) + splice collars (2)": 24.0,
}
SPLICE_HW_G = 4 * 2 * 2.6       # 8 x M5 x 30 Ti-6Al-4V socket cap screws + nyloc (ASSUMPTION 2.6 g each)
BASELINE = {"body_g": 823.0, "frame_g": 1063.0, "frame_spreader_g": 1225.0, "spreader_g": 162.0,
            "corrie_b2_M_g": 3964.5}
# hardware outside the printed body that every entry keeps (crown, rack, pawl, bushings, Ti mount):
# 1063 - 823 = 240 g, minus the body-joint items the splice replaces: 8 carbon dowels 5 x 70 (8 x 1.37 cm3 x 1.6
# = 17.5 g) and their MMA (ASSUMPTION 4 g)
KEPT_HW_G = 240.0 - 17.5 - 4.0


def mass(design: dict = DESIGN, torso: float = 19.0) -> dict:
    m = model(torso, design)
    nodes = m["nodes"]
    by, fib = {}, {}
    for mem in m["members"]:
        g = _key(mem["group"])
        sec = mem["section"]
        if not isinstance(sec, PrintedSection):
            continue
        a, b = (np.asarray(nodes[n]) for n in mem["nodes"])
        L = float(np.linalg.norm(b - a))
        by[g] = by.get(g, 0.0) + sec.mass_g_per_mm * L
        fib[g] = fib.get(g, 0.0) + sec.fibre_mm2 * L
    feats = sum(FEATURES_G.values())
    body = sum(by.values()) + feats
    frame = body + SPLICE_HW_G + KEPT_HW_G
    fibre_cm3 = sum(fib.values()) / 1000
    return {"members_g": by, "features_g": FEATURES_G, "features_total_g": feats, "body_g": body,
            "splice_hw_g": SPLICE_HW_G, "kept_hw_g": KEPT_HW_G, "frame_g": frame,
            "frame_plus_spreader_g": frame + BASELINE["spreader_g"],
            "pack_corrie_b2_M_g": BASELINE["corrie_b2_M_g"] - (BASELINE["frame_spreader_g"]
                                                              - (frame + BASELINE["spreader_g"])),
            "fibre_cm3": fibre_cm3, "fibre_m": fibre_cm3 * 1000 / float(M.require("fiber_strand_area_mm2")) / 1000,
            "matrix_g": body - fibre_cm3 * RHO_F / 1000}


# ============================================================================ stiffness vs today
def torsion_stiffness(design: dict | None = DESIGN, torso: float = 19.0) -> float:
    """Frame twist stiffness, N m / deg: feet fixed (SL0 / SR0), equal and opposite y forces at the two stay
    tops (z 530). design=None -> the released frame.yaml beam model (carbon stays)."""
    from huntkit.fea.frame import solve
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    m = model(torso, design) if design is not None else R.split_top_bar(
        build_frame_from_yaml(ft.FRAME_YAML, torso_in=torso, extension_posts=False), 95.0)
    m = copy.deepcopy({k: v for k, v in m.items()})
    m["supports"] = {"SL0": [1] * 6, "SR0": [1] * 6}
    P = 50.0
    m["loads"] = {"SL530": [0, P, 0, 0, 0, 0], "SR530": [0, -P, 0, 0, 0, 0]}
    res = solve(m, buckling=False, name="torsion")
    d = res.displacements
    dy = d["SL530"][1] - d["SR530"][1]
    xL, xR = m["nodes"]["SL530"][0], m["nodes"]["SR530"][0]
    twist = np.degrees(dy / abs(xR - xL))
    T = P * abs(xR - xL) / 1000.0
    return float(T / twist)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def run(log=print) -> dict:
    t0 = time.time()
    R_ = run_cases(log=log)
    S = summarize(R_)
    ms = mass()
    ctx = {"design": DESIGN, "allow": ALLOW, "summary": S, "mass": ms,
           "sections": {g: {"EA": s.EA, "EIy": s.EIy, "EIz": s.EIz, "GJ": s.GJ, "g_per_mm": s.mass_g_per_mm,
                            "fibre_mm2": s.fibre_mm2} for g, s in sections().items()},
           "seconds": time.time() - t0}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis_results.json").write_text(json.dumps(_jsonable(ctx), indent=1))
    (OUT / "rows.json").write_text(json.dumps(_jsonable(R_), indent=0))
    return ctx


if __name__ == "__main__":       # pragma: no cover
    ctx = run()
    print(json.dumps(_jsonable({"summary": ctx["summary"], "mass": ctx["mass"]}), indent=1))
