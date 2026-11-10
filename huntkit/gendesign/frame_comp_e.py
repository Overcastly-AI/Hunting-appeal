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
    # sized by :func:`size` (4 fully-stressed passes, target 1.05 on strength, fatigue, creep, sleeve ring)
    # lower stays z 0-130: sparse (20 percent) core between fibre flanges
    "stay_lower": dict(b=16.0, h=22.0, tf=1.0, nr=1, rho_c=0.2),
    # upper stays z 130-520: the crown-leg sleeve (18 mm bore over the whole leg travel, low bushing z 171-374
    # at torso 15-23), fibre flanges above / below the bore, rings in the side walls
    "stay_upper": dict(b=26.0, h=23.0, tf=1.25, nr=2, bore=18.0, rho_c=1.0),
    # stay top z 520-530 (upper bar to the top crown bushing): the top-bushing cuff
    "stay_top": dict(b=30.0, h=22.0, tf=0.5, nr=1, bore=18.0, rho_c=1.0),
    "mid_bar": dict(b=16.0, h=10.0, tf=0.25, nr=2, rho_c=0.2),
    "upper_bar": dict(b=26.0, h=26.0, tf=2.5, nr=1, rho_c=0.2),
    # lumbar: an open lattice, not a panel. Three horizontal ribs (z 50 / 120 / 190) and a centre column carry
    # the hip-pivot load to the stays; light ties close the grid (fixed nodes for the lumbar-pad / meat loads).
    "lumbar_rib": dict(b=20.0, h=16.0, tf=1.5, nr=1, rho_c=0.35),
    "lumbar_spine": dict(b=20.0, h=16.0, tf=0.25, nr=1, rho_c=0.35),
    "lumbar_tie": dict(b=6.0, h=5.0, tf=0.25, nr=1, rho_c=1.0),
    "lumbar_shear_scale": 0.02,      # the open lattice has no panel shear (diagonals kept, near zero)
}
LUMBAR_GROUPS = ("lumbar_rib", "lumbar_spine", "lumbar_tie")


def sections(design: dict = DESIGN) -> dict:
    out = {}
    for g in ("stay_lower", "stay_upper", "stay_top", "mid_bar", "upper_bar") + LUMBAR_GROUPS:
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
    # P-1 (fixed interface, frame_light2.md): the extension-post socket gets the crown corners' 0.8 mm bondline
    cj = m["params"].get("crown_joint") or {}
    m["joints"] = [({**j, "params": {**(j.get("params") or {}), **cj}} if j["id"].startswith("post_socket") else j)
                   for j in m["joints"]]
    secs = sections(design)
    for mem in m["members"]:
        g = mem["group"]
        key = g[:-2] if g.endswith(("_L", "_R")) else g
        if key == "stay_upper" and min(m["nodes"][n][2] for n in mem["nodes"]) >= 519.0:
            key = "stay_top"
            mem["group"] = f"stay_top_{g[-1]}"
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
GROUPS = ("stay_lower", "stay_upper", "stay_top", "mid_bar", "upper_bar") + LUMBAR_GROUPS


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
                lf = res.meta.get("link_forces", {})
                bush = {k: float(np.hypot(*np.asarray(v)[:2])) for k, v in lf.items() if k.startswith("bush")}
                pawl = [float(v) for v in np.asarray(lf.get("pawl", np.zeros(6)))[:3]]
                cr = R._crown_rows(res, _crown_view(m), c)
                rows.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": req,
                             "g": float(c.g_factor), "groups": per, "splice": splice, "bush": bush, "pawl": pawl,
                             "buckling": cr.get("buckling")})
                crown.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": req, **cr})
        if log:
            log(f"  [E] torso {t:g} in, {time.time() - t0:.0f} s")
    return {"rows": rows, "crown": crown}


# ============================================================================ sizing (fully-stressed, discrete)
CANDS = {
    "stay_upper": dict(b=(22, 23, 24, 25, 26, 27, 28, 30), h=(21, 22, 23, 24, 26), tf=(0.5, 0.75, 1.0, 1.25, 1.5, 2.0),
                       nr=(1, 2, 3, 4), bore=(18.0,), rho_c=(1.0,)),
    "stay_top": dict(b=(22, 24, 26, 28, 30, 34), h=(22, 24, 26, 28, 30, 34), tf=(0.5, 1.0, 1.5, 2.0),
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
    "lumbar_tie": dict(b=(4, 6, 8, 10), h=(4, 5, 6, 8, 10), tf=(0.0, 0.25, 0.5), nr=(0, 1, 2), rho_c=(1.0,)),
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


def sleeve_margins(kw: dict, rows: list, which: str) -> dict:
    """Sleeve ring under the crown-leg bushing for a candidate sleeve section (see :func:`sleeve_check`)."""
    des = {"stay_upper": kw, "stay_top": kw}
    st, fa, cr = np.inf, np.inf, np.inf
    for r in rows:
        for k, F in r.get("bush", {}).items():
            if ("top" in k) != (which == "top"):
                continue
            st = min(st, 1 / sleeve_check(F * r["factor"], which, des)["fi"])
            if r["case"] == "static_carry":
                fa = min(fa, ALLOW["fat_matrix"] / sleeve_check(F * G_WALK, which, des)["fi"])
                cr = min(cr, ALLOW["creep_matrix"] / sleeve_check(F, which, des)["fi"])
    return {"sleeve": st, "sleeve_fatigue": fa, "sleeve_creep": cr}


def bore_fits(kw: dict) -> bool:
    """Printability round a sleeve bore: >= 0.6 mm matrix liner between the reamed 18 mm bore and the fibre
    (the ream must not cut fibre; ASSUMPTION) and the bore roof printed as a 45 deg teardrop."""
    yb = (kw["h"] - kw["bore"]) / 2 - SKIN - kw["tf"]
    xb = (kw["b"] - kw["bore"]) / 2 - WALL - kw["nr"] * FIBRE_W
    return yb >= 0.6 and xb >= 0.6


def size_group(g: str, rows: list, cands: dict | None = None, target: float = TARGET) -> tuple:
    """Lightest candidate of group g whose margins all reach ``target`` on the given force set."""
    import itertools
    cands = cands or CANDS[g]
    keys = list(cands)
    best = None
    opts = []
    for vals in itertools.product(*(cands[k] for k in keys)):
        kw = dict(zip(keys, vals))
        if kw.get("bore", 0) and not bore_fits(kw):
            continue
        if kw["tf"] > kw["h"] / 2 - SKIN - 1.0:
            continue
        sec = printed_section(d=0.2, **kw)
        opts.append((sec.mass_g_per_mm, kw, sec))
    opts.sort(key=lambda o: o[0])
    for gpm, kw, sec in opts:
        m = group_margins(sec, rows, g)
        if g in ("stay_upper", "stay_top"):
            m.update(sleeve_margins(kw, rows, "low" if g == "stay_upper" else "top"))
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


# ============================================================================ local interface checks
BUSH_LEN = 70.0          # frame.yaml bushing_len_mm (crown-leg bushings)
PAWL = {"pin_bore": 8.0, "cheek_t": 6.0, "rings": 3, "fibre_layers": 16}
# ASSUMPTION: each pawl cheek is 6 mm thick with 3 concentric fibre rings round the 8 mm 304 bushing in 16 of its
# layers (2 mm of CCF), the rest Onyx. Same pawl geometry and 304 bushing as released (frame_cg_recheck.pawl_cheek).


def sleeve_check(F_radial: float, which: str, design: dict = DESIGN) -> dict:
    """Printed sleeve ring under a crown-leg bushing: diametral line load F over the bushing length, point-load
    ring moment 0.318 F R / L (no T7 contact-land credit). The side-wall hoop stress acts ACROSS the layers
    (flat print, bore axis in the layer plane), so it is checked against the matrix Z strength (hot/wet)."""
    p = design["stay_top" if which == "top" else "stay_upper"]
    d = p["bore"]
    t = (p["b"] - d) / 2                      # side wall (x), hoop across layers there
    R = d / 2 + t / 2
    m = 0.318 * F_radial * R / BUSH_LEN
    sig = 6 * m / t ** 2
    allow = SM_Z * ALLOW["kd_matrix_hw"]
    return {"sigma_mpa": float(sig), "allow_mpa": float(allow), "fi": float(sig / allow)}


def pawl_check(F_yz) -> dict:
    """Pawl cheek pair: pin load shared by 2 cheeks; fibre loop tension (2 legs) and bushing bearing on the cheek."""
    F = float(np.hypot(*F_yz)) / 2
    xt, _ = fibre_allow()
    strands = 2 * PAWL["rings"] * PAWL["fibre_layers"]
    loop = strands * float(M.require("fiber_strand_area_mm2")) * xt
    bear = F / (PAWL["pin_bore"] * PAWL["cheek_t"])
    ba = ALLOW["bearing_mpa"] * ALLOW["kd_matrix_hw"]
    return {"per_cheek_n": F, "fi_loop": F / loop, "fi_bearing": bear / ba, "bearing_mpa": bear}


def local_checks(rows: list, design: dict = DESIGN) -> dict:
    out = {}
    for r in rows:
        tag = f"{r['scenario']}:{r['case']}|{r['torso']:g}"
        for k, F in r.get("bush", {}).items():
            which = "top" if "top" in k else "low"
            c = sleeve_check(F * r["factor"], which, design)
            key = f"sleeve ring ({which} bushing)"
            if key not in out or 1 / c["fi"] < out[key]["margin"]:
                out[key] = {"margin": 1 / c["fi"], "set": tag, **c}
            if r["case"] == "static_carry":
                cf = sleeve_check(F * G_WALK, which, design)
                mf = ALLOW["fat_matrix"] / cf["fi"]
                kf = f"sleeve ring fatigue ({which} bushing)"
                if kf not in out or mf < out[kf]["margin"]:
                    out[kf] = {"margin": mf, "set": tag}
                mc = ALLOW["creep_matrix"] / sleeve_check(F, which, design)["fi"]
                kc = f"sleeve ring creep ({which} bushing)"
                if kc not in out or mc < out[kc]["margin"]:
                    out[kc] = {"margin": mc, "set": tag}
        pw = r.get("pawl")
        if pw:
            c = pawl_check(np.asarray(pw[1:3]) * r["factor"])
            m_ = 1 / max(c["fi_loop"], c["fi_bearing"])
            if "pawl cheek" not in out or m_ < out["pawl cheek"]["margin"]:
                out["pawl cheek"] = {"margin": m_, "set": tag, **c}
            if r["case"] == "static_carry":
                cf = pawl_check(np.asarray(pw[1:3]) * G_WALK)
                mf = min(ALLOW["fat_fibre"] / cf["fi_loop"], ALLOW["fat_matrix"] / cf["fi_bearing"])
                if "pawl cheek fatigue" not in out or mf < out["pawl cheek fatigue"]["margin"]:
                    out["pawl cheek fatigue"] = {"margin": mf, "set": tag}
    return out


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
    out["local"] = local_checks(rows, design)
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
TODAY_TORSION_VS_TUBE = 1.51     # spreader_layout.md section 3: released printed body = 1.51 x the v2 tube frame


def torsion_stiffness(design: dict | None = DESIGN, torso: float = 19.0) -> float:
    """Twist stiffness, N m / deg, by the record's test (frame_topopt.tube_frame_stiffness): hip pivot clamped,
    +-TORSION_F (y) at the two stay tops. design=None -> the released frame.yaml beam model (carbon tubes)."""
    from huntkit.fea.frame import solve
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_topopt as ft
    m = model(torso, design) if design is not None else build_frame_from_yaml(
        ft.FRAME_YAML, torso_in=torso, extension_posts=False)
    m = dict(m)
    m["loads"] = {"SR530": [0, ft.TORSION_F, 0, 0, 0, 0], "SL530": [0, -ft.TORSION_F, 0, 0, 0, 0]}
    m["supports"] = {"HP": "fixed"}
    m["inertia_relief"] = False
    r = solve(m, buckling=False)
    i = {n: r.node_ids.index(n) for n in ("SL530", "SR530")}
    dy = r.u[6 * i["SR530"] + 1] - r.u[6 * i["SL530"] + 1]
    w = abs(m["nodes"]["SR530"][0] - m["nodes"]["SL530"][0])
    return float(ft.TORSION_F * w / 1000.0 / np.degrees(dy / w))


def torsion_vs_today(design: dict = DESIGN) -> dict:
    k = torsion_stiffness(design)
    k_tube = torsion_stiffness(None)
    return {"Nm_per_deg": k, "tube_Nm_per_deg": k_tube, "vs_tube": k / k_tube,
            "vs_today": k / k_tube / TODAY_TORSION_VS_TUBE}


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
    ctx = {"design": DESIGN, "allow": ALLOW, "summary": S, "mass": ms, "torsion": torsion_vs_today(),
           "sections": {g: {"EA": s.EA, "EIy": s.EIy, "EIz": s.EIz, "GJ": s.GJ, "g_per_mm": s.mass_g_per_mm,
                            "fibre_mm2": s.fibre_mm2} for g, s in sections().items()},
           "seconds": time.time() - t0}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis_results.json").write_text(json.dumps(_jsonable(ctx), indent=1))
    (OUT / "rows.json").write_text(json.dumps(_jsonable(R_), indent=0))
    return ctx




# ============================================================================ figures (phone-readable PNG)
def member_utilization(design: dict = DESIGN, torso: float = 15.0) -> dict:
    """Max factored FI per printed member over every rev C set at one torso (both couple variants)."""
    from huntkit.fea.load_standard import ls1_envelope
    m = model(torso, design)
    fi = {}
    for variant, cases in ls1_envelope("C").items():
        for c in cases:
            if c.name == "tall_load_posts":
                continue
            c = copy.copy(c)
            c.buckling = False
            res = c.run(m)
            for mr in res.members:
                if _key(mr["group"]) in GROUPS:
                    fi[mr["id"]] = max(fi.get(mr["id"], 0.0), float(mr["check"]["fi"]) * float(c.required_sf))
    return {"model": m, "fi": fi}


def _draw_frame(ax, m, color_of, design=DESIGN, fibre=True):
    from matplotlib.patches import Polygon
    N = m["nodes"]
    for mem in m["members"]:
        sec = mem["section"]
        if not isinstance(sec, PrintedSection):
            continue
        a, b = (np.asarray(N[n])[[0, 2]] for n in mem["nodes"])
        u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        n = np.array([-u[1], u[0]])
        w = sec.params["b"] / 2
        ax.add_patch(Polygon([a + n * w, b + n * w, b - n * w, a - n * w], closed=True,
                             fc=color_of(mem), ec="none", zorder=2))
        if fibre:
            off = w - WALL - 0.6
            for sgn in (1, -1):
                p, q = a + sgn * n * off, b + sgn * n * off
                ax.plot([p[0], q[0]], [p[1], q[1]], color="#111111", lw=0.6, zorder=3)


def plot_concept(path=None, design: dict = DESIGN) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    path = Path(path or SCREENS / f"{SHOT}_1.png")
    fig, axs = plt.subplots(1, 2, figsize=(9, 7.2), dpi=120)
    # today: released PAHT-CF branch body, front view (x-z)
    mesh = trimesh.load(REPO_ROOT / "designs/pack_5200/print/frame/genframe_assembled.stl")
    tri = mesh.vertices[mesh.faces][:, :, [0, 2]]
    from matplotlib.collections import PolyCollection
    axs[0].add_collection(PolyCollection(tri, fc="#7a7f87", ec="none"))
    axs[0].set_title(f"TODAY: PAHT-CF branch body\nbody {BASELINE['body_g']:.0f} g, frame {BASELINE['frame_g']:.0f} g",
                     fontsize=11)
    # LOOM
    m = model(19.0, design)
    colors = {"stay_lower": "#c9a96e", "stay_upper": "#b8925a", "stay_top": "#8c6a3c", "mid_bar": "#c9a96e",
              "upper_bar": "#b8925a", "lumbar_rib": "#d8bd8a", "lumbar_spine": "#d8bd8a", "lumbar_tie": "#e9dcc0"}
    _draw_frame(axs[1], m, lambda mem: colors.get(_key(mem["group"]), "#ccc"), design)
    ax = axs[1]
    ax.axhline(SPLICE_Z, color="#c0392b", lw=1.2, ls="--")
    ax.text(0, SPLICE_Z + 6, "bolted splice z 290 (bed 300 mm)", color="#c0392b", ha="center", fontsize=8)
    for x in (-115, 115):
        ax.plot([x, x], [136, 530], color="white", lw=1.0, ls=(0, (3, 2)), zorder=4)
    ms = mass(design)
    ax.set_title(f"TEAM E LOOM: flat-printed CCF ladder\nbody {ms['body_g']:.0f} g, frame {ms['frame_g']:.0f} g",
                 fontsize=11)
    ax.text(0, -40, "black lines = continuous-fibre rings / flanges\ndashed white = 18 mm crown-leg sleeve bore",
            ha="center", fontsize=8)
    for a in axs:
        a.set_aspect("equal")
        a.set_xlim(-160, 160)
        a.set_ylim(-60, 570)
        a.set_xlabel("x mm")
        a.grid(alpha=0.25)
    axs[0].set_ylabel("z mm")
    fig.suptitle("Printed-frame competition: today vs Team E (front view, wearer side)", fontsize=12)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_utilization(ctx: dict, path=None, design: dict = DESIGN) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors as mcolors
    path = Path(path or SCREENS / f"{SHOT}_2.png")
    U = member_utilization(design, 15.0)
    fig = plt.figure(figsize=(10, 7.2), dpi=120)
    ax = fig.add_axes([0.02, 0.08, 0.36, 0.82])
    norm = mcolors.Normalize(0, 1.0)
    cmap = matplotlib.colormaps["viridis"]
    _draw_frame(ax, U["model"], lambda mem: cmap(norm(min(U["fi"].get(mem["id"], 0), 1.0))), design, fibre=False)
    ax.set_aspect("equal"); ax.set_xlim(-150, 150); ax.set_ylim(-20, 560)
    ax.set_title("max factored FI per member\n(torso 15 in, every rev C set)", fontsize=10)
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, fraction=0.05, label="utilization (1.0 = limit)")
    # margins bar chart
    S = ctx["summary"]
    items = []
    for g, v in S["strength"].items():
        items.append((f"{g} strength ({v['mode']})", v["margin"]))
    for g, v in S["fatigue"].items():
        if v["margin"] < 3:
            items.append((f"{g} fatigue ({v['mode']})", v["margin"]))
    for k, v in S["local"].items():
        if v["margin"] < 3:
            items.append((k, v["margin"]))
    items.append(("splice bolts bearing", S["splice"]["strength"]["margin"]))
    items.append(("splice fatigue", S["splice"]["fatigue"]["margin"]))
    items.append(("buckling", S["buckling"]["margin"]))
    for k in ("crown_leg", "crown_top_bar", "crown_spine", "post_socket Volkersen peak"):
        items.append((f"crown {k}", S["crown"][k]["margin"]))
    items.sort(key=lambda t: t[1])
    ax2 = fig.add_axes([0.70, 0.08, 0.28, 0.82])
    ys = np.arange(len(items))
    ax2.barh(ys, [t[1] for t in items], color=["#c0392b" if t[1] < 1 else "#2c7fb8" for t in items])
    ax2.axvline(1.0, color="k", lw=1)
    ax2.set_yticks(ys, [t[0] for t in items], fontsize=7)
    ax2.set_xlim(0, 2.6)
    ax2.set_xlabel("margin = SF / requirement (pass >= 1.0)")
    ax2.set_title("HA-LS-1 rev C, worst torso and couple variant", fontsize=10)
    fig.suptitle(f"Team E LOOM utilization: passes at beam level on ASSUMED allowables (coupons E-1..E-7)",
                 fontsize=11)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


# ============================================================================ cost, hours, result.json
PRINTER_USD = 3199.0        # FibreSeeker 3 US pre-sale price (3dnatives 2026-09-11); Kickstarter $2,699 (3DPrint.com)
FIBRE_USD_PER_M = 55.0 / 500.0       # X-CCF $55 / 500 m (record onyx_ccf_markforged, Fabbaloo)
MATRIX_USD_PER_KG = 80.0             # ASSUMPTION: PA-CF matrix filament at the PAHT-CF record price
FIBRE_LAY_MM_S = 10.0                # ASSUMPTION: continuous-fibre lay rate (no published FibreSeeker rate)
MATRIX_MM3_S = 8.0                   # as the released H2S plan
KEPT_HW_USD = 50.3 + 8.0 + 35.0 + 5.0 + 3.0     # crown tubes, 304 bushings, Ti hip mount, UHMWPE, XLPE (PRODUCTION.md)
SPREADER_USD = 207.2


def cost_and_hours(ms: dict) -> dict:
    fibre_m = ms["fibre_m"] * 1.10                    # 10 % purge / cut waste (ASSUMPTION)
    matrix_kg = ms["matrix_g"] * 1.08 / 1000
    hrs = ms["fibre_m"] * 1000 / FIBRE_LAY_MM_S / 3600 + ms["matrix_g"] / (RHO_M / 1e6) * 1.08 / MATRIX_MM3_S / 3600
    mat = fibre_m * FIBRE_USD_PER_M + matrix_kg * MATRIX_USD_PER_KG
    unit = {"fibre": fibre_m * FIBRE_USD_PER_M, "matrix": matrix_kg * MATRIX_USD_PER_KG,
            "reprint allowance 20 %": 0.20 * mat, "machine at $1/h": hrs * 1.0, "Ti splice bolts + nyloc": 20.0,
            "inserts": 3.0, "kept hardware (crown, bushings, Ti mount, UHMWPE, XLPE)": KEPT_HW_USD,
            "Sandwich v2 spreader": SPREADER_USD}
    u = sum(unit.values())
    return {"print_hours": hrs, "unit_items": unit, "unit_usd": u,
            "cost_usd": {"1": u + PRINTER_USD, "10": u + PRINTER_USD / 10, "100": u + PRINTER_USD / 100}}


def write_result(ctx: dict) -> dict:
    S, ms = ctx["summary"], ctx["mass"]
    ch = cost_and_hours(ms)
    strength = [(v["margin"], f"{g} {v['mode']} {v['set']}") for g, v in S["strength"].items()]
    strength += [(v["margin"], f"crown {k} {v['set']}") for k, v in S["crown"].items()
                 if "Volkersen" not in k and "avg" not in k]
    strength += [(v["margin"], f"{k} {v['set']}") for k, v in S["local"].items()
                 if "fatigue" not in k and "creep" not in k and "sleeve" not in k and "pawl" not in k]
    strength.append((S["buckling"]["margin"], f"buckling {S['buckling']['set']}"))
    fatigue = [(v["margin"], f"{g} {v['mode']} {v['set']}") for g, v in S["fatigue"].items()]
    fatigue += [(v["margin"], f"{k} {v['set']}") for k, v in S["local"].items() if "fatigue" in k]
    fatigue.append((S["splice"]["fatigue"]["margin"], f"splice bearing fatigue {S['splice']['fatigue']['set']}"))
    joint = [(S["splice"]["strength"]["margin"], "splice"), (S["splice"]["fatigue"]["margin"], "splice fatigue")]
    joint += [(v["margin"], k) for k, v in S["local"].items() if "sleeve" in k or "pawl" in k]
    joint += [(v["margin"], f"crown {k}") for k, v in S["crown"].items() if "Volkersen" in k or "avg" in k]
    ws, wf, wj = min(strength), min(fatigue), min(joint)
    passes = min(ws[0], wf[0], wj[0]) >= 1.0
    res = {
        "team": "E",
        "concept_name": "LOOM",
        "one_line": ("Flat-printed continuous-carbon ladder (fibre flanges + concentric rings round each window) on a "
                     "home FibreSeeker 3, two segments bolted at z 290; passes rev C at beam level on assumed "
                     "allowables but is HEAVIER than today (+61 g)"),
        "frame_g": round(ms["frame_g"], 1),
        "frame_plus_spreader_g": round(ms["frame_plus_spreader_g"], 1),
        "pack_mass_corrie_b2_M_g": round(ms["pack_corrie_b2_M_g"], 1),
        "passes_rev_c": bool(passes),
        "worst_strength_margin": round(ws[0], 3),
        "worst_fatigue_margin": round(wf[0], 3),
        "worst_joint_margin": round(wj[0], 3),
        "governing_case": f"fatigue: {wf[1]}; strength: {ws[1]}; joint: {wj[1]}",
        "torsion_stiffness_vs_today": round(ctx["torsion"]["vs_today"], 2),
        "print_hours": round(ch["print_hours"], 1),
        "printer": "FibreSeeker 3 home (CFC continuous carbon, dual nozzle; pre-sale 2026)",
        "cost_usd": {k: round(v) for k, v in ch["cost_usd"].items()},
        "build_hours": 8.0,
        "skill_level": "intermediate",
        "looks_generative": False,
        "patents_checked": [
            "US 10,952,523 (Mystery Ranch, load lifters): crown, top bar and lifters unchanged; posts stay lash points",
            "US 9,126,365 / US 9,579,851 / US 10,040,252 / US 9,156,205 (Markforged continuous-fibre printing "
            "process family): process claims on the machine; owner uses a commercial machine, no claim on the frame",
            "docs/DECISIONS.md 2026-11-01 IP guardrail (extension posts lash/flag only)",
        ],
        "governing_assumptions": [
            "ASSUMPTION ILSS 14 MPa dry (half the 28 MPa published for printed CF/PA6; published range 2.8-34) x 0.6 "
            "hot/wet -> coupon E-2",
            "ASSUMPTION fibre-region strength = Markforged UD coupon (800 / 320 MPa, 60 GPa) x 0.85 part factor, "
            "x 0.8 hot/wet, x 0.65 impact on compression -> coupon E-1 (FibreSeek X-CCF has no datasheet)",
            "ASSUMPTION fatigue: fibre FI <= 0.5, matrix / interlayer <= 0.3 at 1e5 x 1.6 g (no published endurance "
            "data for printed CCF; Pertuz 2020 short-life Basquin b = -0.039) -> coupon E-5 (1e5 cycles)",
            "ASSUMPTION matrix (Onyx-class PA6-CF) 40 / 30 MPa XY / Z x 0.6 hot/wet; in-plane shear 20 MPa -> E-3",
            "ASSUMPTION bolt bearing 60 MPa dry on a fibre-ringed M5 hole, no clamp-friction credit -> coupon E-4",
            "ASSUMPTION sleeve ring: point-load ring moment, side-wall hoop across layers vs Z strength -> coupon E-6",
            "ASSUMPTION beam model of frame.yaml is the load path (members re-sectioned, straight planar stays, "
            "lumbar grid kept as an open lattice); no voxel FE of junctions -> T1/T5 first article",
            "ASSUMPTION interface features (pawl housing, hip boss, fairlead cheeks, clip lands, feet, corners, "
            "splice collars) 116 g Onyx allowance -> weigh first article",
            "ASSUMPTION fibre lay rate 10 mm/s and matrix 8 mm3/s for print hours; FibreSeeker 3 ships as announced",
        ],
        "coupon_tests": [
            "E-1 tension + compression (ASTM D3039 / D6641) of flat-printed X-CCF/PA-CF flange coupons, dry and "
            "conditioned 40 C / 85 % RH to saturation; >= 6 each; B-basis vs 544 / 166 MPa design",
            "E-2 short-beam shear ASTM D2344, 0.125 mm layers, dry + conditioned; pass >= 14 MPa dry, >= 8.4 wet",
            "E-3 in-plane shear (Iosipescu ASTM D5379) and matrix Z tension of the PA-CF matrix; >= 20 / 30 MPa",
            "E-4 pin bearing ASTM D5961 on an M5 hole with 3 fibre rings, plus 1e5-cycle bearing fatigue at "
            "0.3 x static",
            "E-5 4-point-bend fatigue of a 400 mm stay section (flanges + bore) at the 1.6 g C1 moment x 1.0, "
            "R = 0.1, 1e5 cycles, then residual strength >= factored C2 moment",
            "E-6 sleeve ring crush: 70 mm sleeve section, 18 mm UHMWPE bushing, diametral load to failure + 1e5 cycles "
            "at 1.6 g bushing force",
            "E-7 fibre corner coupon: ring round a 10 mm radius stay-bar corner, T-pull to failure",
            "First article: HA-LS-1 T1-T5 + T9 (load_standard.md) with the splice pencil-mark check",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(res, indent=2))
    ctx["cost"] = ch
    return res


def main(log=print):
    ctx = run(log=log)
    res = write_result(ctx)
    shots = [plot_concept(), plot_utilization(ctx)]
    (OUT / "analysis_results.json").write_text(json.dumps(_jsonable({**ctx, "result": res, "screens": shots}),
                                                          indent=1))
    return ctx, res, shots


if __name__ == "__main__":       # pragma: no cover
    _ctx, _res, _shots = main()
    print(json.dumps(_res, indent=1))
