"""Hipbelt concept B structural check (structural-fea-engineer, 2026-11-09).

Belt B was adopted 2026-11-09 (docs/DECISIONS.md). ``analysis/hipbelt_fit.md`` section 6 left four structural flags:
the fixed wing-to-centre-plate joint that replaces the cant snap, the never-analysed PA66-GF30 centre plate, the
fore-aft lumbar push through the Ti pivot, and the 2:1 pull path (D-ring tab, HDPE creep, ladder lock).
Write-up: ``designs/pack_5200/analysis/hipbelt_structural.md``.

Load path (B, as defined here)::

    frame -> Ti pivot pin (z 120, roll-free about y) -> PA66-GF30 centre plate (CP) -+-> lumbar pad -> body
                                                                                    +-> stitched ear joint (each side)
                                                                                         -> wing shell textile -> D-ring tab
                                                                                         -> 2:1 webbing -> buckle

Fixed wing joint "SE" (stitched ear): each CP side ends in a 3 mm ear, full root height, with two rows of 2.0 mm
stitch holes. The ear slides into the wing root between the outer shell and the inner face (with a 1000D doubler on
each side) and is hand saddle-stitched through the holes. The wing tension, the vertical shear and the cant moment all
go in over the full root height as small per-hole loads. The HDPE stiffener FLOATS (it butts against the ear, no
fastener, no stitch): the textile carries the hoop tension; HDPE does the spreading. A floating HDPE carries no net
tension, so nothing in it creeps (section ``hdpe_tab``).

Loads (HA-LS-1 rev C factors, ``huntkit.fea.load_standard``):
* wing tension T: the 1.6 g walking-peak need T_req from the fit model (``hipbelt_results.json``, worst B form
  483 N, XXL / male 42 in). Limit = stumble 2.0 g: T x 2.0 / 1.6. Factored x 1.5 -> 906 N; design value **1000 N**
  (ASSUMPTION: rounded up for users above the 42 in ANSUR band and for over-cinching).
* lumbar push H = 68 kg x g x CG aft / (yoke z - 120), CG 205 mm (rev C bag cases), 413 N at 1 g, 15 in torso.
* vertical V = 80 % x 68 kg x g (R-07). Wing share per side 0.40 (fit model: 0.39 worst).
* fatigue: 1e5 cycles of 0 -> 1.6 g (T 483, H 661, V 854 N). Creep: 1 g sustained.

    python -m huntkit.gendesign.hipbelt_structure        # results JSON + figures (+ pivot FE if cached)
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from huntkit.fea import load_standard as ls
from huntkit.fea.frame import solve
from huntkit.fea.sections import generic
from huntkit.gendesign import hipbelt as hb
from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
RESULTS_FIT = PACK / "concepts" / "hipbelt_results.json"
OUT_JSON = PACK / "analysis" / "hipbelt_structural_results.json"
PIVOT_FE_JSON = REPO / "outputs" / "gendesign" / "pivot_recheck.json"
SCREENS = REPO / "outputs" / "screens"
DATE = "20261109"

G = hb.G
# ---------------------------------------------------------------------------------------------- loads
T_DESIGN_F = 1000.0            # ASSUMPTION: factored wing tension per side (906 N computed, rounded up)
THETA_ROOT_DEG = 20.0          # wing direction at the CP edge, forward of lateral (fit model 9.8-19.4 deg)
WING_V_SHARE = 0.40            # vertical share per wing (fit model: wings 0.57-0.79 of the hip load, i.e. <= 0.395 each)
E_PAD_MM = 20.0                # ASSUMPTION: lumbar pressure centroid +/-20 mm about the pin (fit model -4..+16 mm)
TORSO_WORST = 15               # largest lumbar push (shortest lever)
WING_LEN_XXL_MM = 304.0        # B wing length XXL (hipbelt_fit.md section 3.3)

# ---------------------------------------------------------------------------------------------- PA66-GF30 allowables
HOT = 0.8                      # ASSUMPTION: sun-heated part (50-60 C), same 0.8 as the repo's polymer hot/wet knockdown
FAT_FRAC = 0.30                # ASSUMPTION (repo precedent, lugs.py FDM): 1e5-cycle max stress = 0.3 x static strength
CREEP_FRAC = 0.25              # ASSUMPTION: sustained stress <= 0.25 x conditioned UTS (GF-PA creep rupture ~0.5 UTS at 1e3 h)
KT_FAT = 2.0                   # ASSUMPTION: fatigue notch factor at radiused corners / hub fillet (r >= 3 mm)
KT_HOLE = 3.0                  # open-hole Kt (Peterson), used on the stitch-hole net section in fatigue

# ---------------------------------------------------------------------------------------------- HDPE (no creep data in the record)
HDPE_SUSTAINED_MPA = 5.0       # ASSUMPTION: long-term sustained stress for generic HDPE sheet: PE80 MRS 8 MPa
#                                (ISO 12162, 50 yr 20 C) / design coefficient 1.6. materials-engineer: add a cited creep curve
HDPE_FATIGUE_MPA = 10.0        # ASSUMPTION: HDPE stress range at 1e5 cycles (no record value)

THREAD_D_MM = 0.45             # ASSUMPTION: tex 135 bonded nylon finished diameter (bearing width per thread pass)


def pa66() -> dict:
    m = load("pa66_gf30")
    uts = float(m.require("ultimate_strength_conditioned_mpa"))
    return {"E": float(m.require("youngs_modulus_conditioned_mpa")), "nu": float(m.require("poisson")),
            "rho": float(m.require("density_kg_m3")), "uts_cond": uts, "static": uts * HOT,
            "fatigue": FAT_FRAC * uts, "creep": CREEP_FRAC * uts,
            "basis": "pa66_gf30 conditioned (50 % RH) values x hot 0.8; fatigue 0.3 UTS @1e5; creep 0.25 UTS"}


def cp_material(mid: str = "pa66_gf30") -> dict:
    """Allowables for the centre plate, same keys for the polymer and the metal options.
    Metals: static = S-basis yield; fatigue = max stress at R = 0 for 1e5 cycles from the repo Basquin curve
    (``huntkit.fea.fatigue.sn_from_material``) with Goodman; no creep at these temperatures (creep = static)."""
    if mid == "pa66_gf30":
        d = pa66()
        d["id"] = mid
        return d
    from huntkit.fea.fatigue import sn_from_material
    m = load(mid)
    su = float(m.require("ultimate_strength_mpa"))
    sy = float(m.get("yield_strength_sbasis_mpa") or m.require("yield_strength_mpa"))
    sa = float(sn_from_material(mid).stress_amplitude(1e5))
    smax = 2 * sa / (1 + sa / su)                 # R = 0: Sa = Sm = Smax / 2, Goodman Sa_eq = Sa / (1 - Sm / Su)
    return {"id": mid, "E": float(m.require("youngs_modulus_mpa")), "nu": float(m.get("poisson", 0.33)),
            "rho": float(m.require("density_kg_m3")), "uts_cond": su, "static": sy, "fatigue": min(smax, sy),
            "creep": sy, "basis": f"{mid}: S-basis yield; 1e5-cycle R=0 max stress {min(smax, sy):.0f} MPa (Basquin + Goodman)"}


def fit_rows() -> list[dict]:
    return [r for r in json.loads(RESULTS_FIT.read_text())["rows"] if r["design"] == "B"]


def lumbar_push(g: float = 1.0, torso: int = TORSO_WORST, cg: float = hb.CG_AFT_MM, mass: float = hb.RATED_KG) -> float:
    return mass * G * g * cg / (hb.YOKE_Z[torso] - hb.LUMBAR_Z)


@dataclass(frozen=True)
class LoadSet:
    name: str
    T: float          # wing tension per side, N
    H: float          # lumbar push into the CP (toward the frame, +y), N
    V: float          # hip vertical load (body pushes the belt up), N
    factor: float     # factor already included (1.0 = unfactored)
    kind: str         # "strength" | "fatigue" | "creep"


def load_sets() -> dict[str, LoadSet]:
    rows = fit_rows()
    t_walk = max(r["T_req_n"] for r in rows)                    # 1.6 g need, worst form
    t_1g = t_walk / hb.WALK_G
    v1 = hb.HIP_SHARE * hb.RATED_KG * G
    h1 = lumbar_push(1.0)
    f2 = ls.G_STUMBLE * ls.F_LIMIT                              # 3.0
    t_c2 = max(T_DESIGN_F, t_1g * f2)
    return {
        "C2": LoadSet("C2 stumble 2.0 g x 1.5", t_c2, h1 * f2, v1 * f2, f2, "strength"),
        "C1": LoadSet("C1 static 1.0 g x 2.0", t_1g * ls.F_STATIC, h1 * ls.F_STATIC, v1 * ls.F_STATIC, ls.F_STATIC,
                      "strength"),
        "walk": LoadSet("walking 0 -> 1.6 g, 1e5 cycles", t_walk, h1 * ls.G_WALK, v1 * ls.G_WALK, 1.0, "fatigue"),
        "carry": LoadSet("carry 1 g sustained", t_1g, h1, v1, 1.0, "creep"),
    }


# ---------------------------------------------------------------------------------------------- geometry
@dataclass(frozen=True)
class CentrePlate:
    """PA66-GF30 centre plate. x lateral (+ right), z up (0 = pivot, frame z 120), y fore-aft (+ toward the frame).
    A skin plate with ribs on the AFT face (toward the frame): one horizontal spine rib at z 0 (hub to the ears) and
    vertical ribs at |x| in ``vrib_x``, tapered from ``vrib_root`` at the spine to ``vrib_tip`` at the top/bottom edge."""
    half_w_body: float = 75.0       # body x -75..75 (= lumbar pad width 150)
    ear_w: float = 30.0             # ear x 75..105 (sits inside the wing root, no ribs)
    half_h: float = 70.0            # CP height 140 (wing root 150 less 5 mm binding each side)
    t: float = 1.5                  # skin thickness (recommended: 6061-T6 1.5 mm sheet, water-jet cut)
    rib_h: float = 0.0              # spine rib depth beyond the skin, along y (0 = none)
    rib_w: float = 3.0              # spine rib width along z
    vrib_x: tuple = ()              # |x| of vertical ribs (none in the recommended bow-tie)
    vrib_root: float = 14.0         # vertical rib depth at z 0
    vrib_tip: float = 4.0           # ... at |z| = half_h
    vrib_w: float = 2.5
    hub_d: float = 36.0             # hub boss (thrust face against the Ti mount via a POM washer)
    hub_len: float = 12.0           # along the pin
    bore_d: float = 10.2            # 10 mm Ti pin
    hub_mat: str = "pa66_gf30"      # hub bushing, riveted / bonded into the plate (a metal plate gets a PA66 hub)
    latch_g: float = 4.0            # POM latch (ASSUMPTION, part of the 45 g booked)
    material: str = "alu_6061_t6"
    kind: str = "bowtie"            # "plate": the lumbar pad bears on the CP (DESIGN.md 5.2, as drawn)
    #                                 "bowtie": the pad bears on the frame lumbar pan (as the frame FE assumes); the CP is
    #                                 a hub + spine band (|z| <= spine_half_h) flaring to full-height ears from flare_x
    spine_half_h: float = 30.0
    flare_x: float = 62.5
    curve_deg: float = 14.6         # end slope of the CP arc in plan (0 = flat). The wing leaves the ear at
    #                                 theta_root - curve_deg off the CP tangent (fit-model theta 9.8-19.4 deg)

    def inside(self, x: float, z: float) -> bool:
        if self.kind == "plate":
            return abs(x) <= self.half_w + 1e-6 and abs(z) <= self.half_h + 1e-6
        return abs(z) <= self.spine_half_h + 1e-6 or abs(x) >= self.flare_x - 1e-6

    def area_mm2(self) -> float:
        if self.kind == "plate":
            return 2 * self.half_w * 2 * self.half_h
        return 2 * self.flare_x * 2 * self.spine_half_h + 2 * (self.half_w - self.flare_x) * 2 * self.half_h

    @property
    def mat(self) -> dict:
        return cp_material(self.material)

    @property
    def half_w(self) -> float:
        return self.half_w_body + self.ear_w

    def vrib_depth(self, z: float) -> float:
        return self.vrib_root + (self.vrib_tip - self.vrib_root) * min(abs(z) / self.half_h, 1.0)

    def mass_g(self) -> dict:
        rho = self.mat["rho"] * 1e-6        # g/mm3
        plate = self.area_mm2() * self.t
        plate -= self.ear_holes() * math.pi * (StitchedEar().hole_d / 2) ** 2 * self.t * 2
        rib = 2 * self.half_w_body * self.rib_w * self.rib_h
        vrib = 0.0
        for x in self.vrib_x:
            hz = self.half_h if self.kind == "plate" or x >= self.flare_x - 1e-6 else self.spine_half_h
            d_end = self.vrib_depth(hz)
            vrib += (1 if x == 0 else 2) * self.vrib_w * 2 * hz * 0.5 * (self.vrib_root + d_end)
        rho_h = cp_material(self.hub_mat)["rho"] * 1e-6
        hub = math.pi / 4 * (self.hub_d ** 2 - self.bore_d ** 2) * (self.hub_len - self.t)
        bore = math.pi / 4 * self.bore_d ** 2 * self.t
        v = plate + rib + vrib - bore
        return {"plate_g": plate * rho, "ribs_g": (rib + vrib) * rho, "hub_g": hub * rho_h, "latch_g": self.latch_g,
                "total_g": v * rho + hub * rho_h + self.latch_g}

    def ear_holes(self) -> int:
        e = StitchedEar()
        return e.rows * e.n_per_row(self)


@dataclass(frozen=True)
class StitchedEar:
    """Wing root joint: the CP ear inside the wing root, hand saddle-stitched through drilled holes."""
    hole_d: float = 2.0
    pitch: float = 6.0
    rows: int = 2
    row_x: tuple = (87.0, 97.0)     # |x| of the rows; outer row 8 mm from the ear edge (105)
    end_dist: float = 6.0           # first / last hole from the ear top / bottom edge
    first_row_share: float = 0.6    # ASSUMPTION: outer (first-loaded) row carries 60 % (lap-joint load sharing)
    end_hole_factor: float = 1.5    # ASSUMPTION: end holes in a row carry 1.5 x the row mean
    thread: str = "bonded_nylon_tex135"
    doubler: str = "cordura_1000d_nylon66"     # one 1000D doubler each side of the ear, under the shell
    shell: str = "cordura_330d_nylon66"

    def n_per_row(self, cp: CentrePlate) -> int:
        return int((2 * cp.half_h - 2 * self.end_dist) // self.pitch) + 1


# Centre-plate variants compared in hipbelt_structural.md
CP_VARIANTS = {
    # DESIGN.md 5.2 as drawn: flat PA66-GF30 plate under the lumbar pad (45 g booked; 3 mm is the thinnest that
    # holds the 2 mm stitch holes and the pad) -> fails
    "as_drawn": CentrePlate(kind="plate", material="pa66_gf30", t=3.0, curve_deg=0.0, spine_half_h=70.0),
    # keep the pad on the CP: the lightest passing plate found, ribbed 7075-T6 (machined), flat
    "pad_on_cp_7075": CentrePlate(kind="plate", material="alu_7075_t6", t=0.8, rib_h=8.0, rib_w=2.0,
                                  vrib_x=(0.0, 25.0, 50.0, 75.0), vrib_root=8.0, vrib_tip=3.0, vrib_w=2.0,
                                  curve_deg=0.0),
    # recommended: pad bears on the frame lumbar pan (as the frame FE assumes), CP = curved 6061-T6 bow-tie
    "recommended": CentrePlate(),
}


# ---------------------------------------------------------------------------------------------- CP grillage FE
X_BODY = (0.0, 18.0, 25.0, 37.5, 50.0, 62.5, 75.0)      # grillage lines in the body (hub rim at 18)
X_EAR = (12.0, 22.0, 30.0)                               # ... in the ear, from its root (stitch rows at 12 and 22)
Z_NODES = (0.0, 12.5, 25.0, 47.5, 70.0)


def _strip(b: float, t: float, rib: tuple | None = None):
    """Plate strip of width b (in-plane) and thickness t, optional rib (w, h) on the +y face.
    Local y = out of plane (global y via ref), local z = in-plane width. Returns (Section, c_out) where c_out is the
    larger distance from the out-of-plane neutral axis to an extreme fibre."""
    A0, yc0, I0 = b * t, 0.0, b * t ** 3 / 12
    if rib:
        w, h = rib
        A1, yc1, I1 = w * h, t / 2 + h / 2, w * h ** 3 / 12
        A = A0 + A1
        yc = (A0 * yc0 + A1 * yc1) / A
        Iz = I0 + A0 * (yc0 - yc) ** 2 + I1 + A1 * (yc1 - yc) ** 2
        c = max(yc + t / 2, t / 2 + h - yc)
        Iy = t * b ** 3 / 12 + h * w ** 3 / 12
        a_, b_ = max(w, h), min(w, h)
        J = b * t ** 3 / 6 + a_ * b_ ** 3 / 3 * (1 - 0.63 * b_ / a_)   # skin (grillage) + rib (thin rectangle, Roark)
        tmax = max(t, b_)
    else:
        A, Iz, c, Iy = A0, I0, t / 2, t * b ** 3 / 12
        J = b * t ** 3 / 6                      # grillage torsion constant for an isotropic plate (half of b t^3 / 3)
        tmax = t
    sec = generic(A, Iy, Iz, J, ymax=c, zmax=b / 2, Wt=J / tmax)   # thin open section: tau = T t / J
    return sec, c


def _xs(cp: CentrePlate):
    half = [x for x in X_BODY if x <= cp.half_w_body] + [cp.half_w_body + e * cp.ear_w / 30.0 for e in X_EAR]
    return sorted({-x for x in half} | set(half))


def _zs(cp: CentrePlate):
    zs = sorted({-z for z in Z_NODES} | set(Z_NODES))
    return [z * cp.half_h / 70.0 for z in zs]


LUMBAR_FOAM_B = (hb.FoamLayer("eva_foam_45c", 6.0), hb.FoamLayer("eva_foam_30c", 6.0))   # hipbelt_concepts.B


THETA_RANGE_DEG = (9.8, 19.4)      # wing direction at the root over the 16 ANSUR forms (fit model, this module)


def theta_residual(cp: "CentrePlate", theta_deg: float = THETA_ROOT_DEG) -> float:
    """Angle between the wing and the CP end tangent. Flat CP: theta_deg (20, design). Curved CP: the worst
    mismatch over the forms, max(|19.4 - c|, |9.8 - c|), never below 3 deg (ASSUMPTION: fit scatter)."""
    if cp.curve_deg <= 0:
        return theta_deg
    lo, hi = THETA_RANGE_DEG
    return max(abs(hi - cp.curve_deg), abs(cp.curve_deg - lo), 3.0)


def foundation_k() -> float:
    """Winkler modulus (N/mm^3) of the B lumbar stack + soft tissue, as the fit model uses (hipbelt._k_stack)."""
    return hb._k_stack(LUMBAR_FOAM_B, hb.TISSUE_H_SOFT)


def cp_model(cp: CentrePlate, L: LoadSet, e_pad: float = 0.0, theta_deg: float = THETA_ROOT_DEG,
             wing_v_share: float = WING_V_SHARE, ear: StitchedEar = StitchedEar(), inplane: bool = False) -> dict:
    """Plate grillage of the CP (strips along x and z), clamped-in-roll pin support at the hub centre, rigid hub.
    Loads: lumbar pad pressure (+y, total H + 2 T sin theta, linear in z with centroid e_pad), wing pull at the two
    stitch rows (T (+/-cos, -sin) and the wing vertical share), pad vertical friction (the rest of V)."""
    m = cp.mat
    mat = {"id": m["id"] + "_cp", "name": m["id"], "youngs_modulus_mpa": m["E"], "poisson": m["nu"],
           "density_kg_m3": m["rho"], "design_allowable_mpa": m["static"]}
    xs, zs = _xs(cp), _zs(cp)
    theta_deg = theta_residual(cp, theta_deg)
    nid = lambda i, j: f"n{i}_{j}"  # noqa: E731
    nodes = {nid(i, j): [x, 0.0, z] for i, x in enumerate(xs) for j, z in enumerate(zs)}
    trib = lambda arr, k: (arr[min(k + 1, len(arr) - 1)] - arr[max(k - 1, 0)]) / 2  # noqa: E731
    members = []
    hub_r = cp.hub_d / 2
    for j, z in enumerate(zs):                     # strips along x
        b = trib(zs, j)
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            if not (cp.inside(x0, z) and cp.inside(x1, z)):
                continue
            rigid = abs(z) < 1e-9 and max(abs(x0), abs(x1)) <= hub_r + 1e-9
            in_body = max(abs(x0), abs(x1)) <= cp.half_w_body + 1e-9
            rib = (cp.rib_w, cp.rib_h) if abs(z) < 1e-9 and cp.rib_h > 0 and in_body else None
            sec, c = _strip(b, cp.t if not rigid else cp.hub_len, rib if not rigid else None)
            members.append({"id": f"x{j}_{i}", "nodes": [nid(i, j), nid(i + 1, j)], "section": sec, "material": mat,
                            "ref": [0, 1, 0], "group": "rigid" if rigid else ("spine" if rib else "strip_x"),
                            "c": c, "b": b, "t": cp.t, "dir": "x"})
    for i, x in enumerate(xs):                     # strips along z
        b = trib(xs, i)
        for j in range(len(zs) - 1):
            z0, z1 = zs[j], zs[j + 1]
            if not (cp.inside(x, z0) and cp.inside(x, z1)):
                continue
            rigid = abs(x) < 1e-9 and max(abs(z0), abs(z1)) <= hub_r + 1e-9
            has_rib = any(abs(abs(x) - xr) < 1e-6 for xr in cp.vrib_x) and cp.vrib_root > 0
            vr = (cp.vrib_w, cp.vrib_depth(0.5 * (z0 + z1))) if has_rib else None
            sec, c = _strip(b, cp.t if not rigid else cp.hub_len, vr if not rigid else None)
            members.append({"id": f"z{i}_{j}", "nodes": [nid(i, j), nid(i, j + 1)], "section": sec, "material": mat,
                            "ref": [0, 1, 0], "group": "rigid" if rigid else ("vrib" if vr else "strip_z"),
                            "c": c, "b": b, "t": cp.t, "dir": "z"})
    loads = {k: np.zeros(6) for k in nodes}
    th = math.radians(theta_deg)
    # lumbar pad: q(x, z) = 1 + k z over |x| <= half_w_body, centroid e_pad
    # Body = Winkler foundation under the whole CP footprint (ears included: they sit inside the padded wing roots):
    # pad foams (B lumbar: EVA 45C 6 + EVA 30C 6) + 25 mm tissue in series, the fit model's own k (hipbelt._k_stack).
    # Loads: the frame pushes the CP toward the body through the pin with H ("plate" mode only: in "bowtie" mode the
    # lumbar pad bears on the frame lumbar pan, as the frame FE assumes, and H never enters the CP); the wings pull the
    # ears (T cos, -T sin, + their vertical share). Vertical: the body holds the pad share by friction (+z on the pad
    # nodes, "plate" mode) and the wings hold theirs; the pin reacts the sum.
    used = {n for mem in members for n in mem["nodes"]}
    kf = foundation_k()
    w_pad, springs = {}, {}
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            if nid(i, j) not in used or not cp.inside(x, z):
                continue
            a_ = trib(xs, i) * trib(zs, j)
            springs[nid(i, j)] = kf * a_
            if abs(x) <= cp.half_w_body + 1e-9:
                w_pad[nid(i, j)] = a_
    s_pad = sum(w_pad.values())
    V_w = wing_v_share * L.V
    P_hoop = 2 * L.T * math.sin(th)
    if cp.kind == "plate":
        H_cp, V_pad = L.H, L.V - 2 * V_w
    else:
        H_cp, V_pad = 0.0, 0.0
    if inplane:
        for n, wv in w_pad.items():
            loads[n][2] += V_pad * wv / s_pad
    P_pad = H_cp + P_hoop
    # wing pull at the stitch rows: outer row first_row_share, inner the rest; uniform over the root height
    for side in (-1, 1):
        for xr, share in ((ear.row_x[1], ear.first_row_share), (ear.row_x[0], 1 - ear.first_row_share)):
            xr_s = cp.half_w_body + (xr - 75.0) * cp.ear_w / 30.0
            i = int(np.argmin([abs(x - side * xr_s) for x in xs]))
            ww = {nid(i, j): trib(zs, j) for j in range(len(zs)) if nid(i, j) in used}
            s_ = sum(ww.values())
            for n, wv in ww.items():
                f = share * wv / s_
                loads[n][1] += -L.T * math.sin(th) * f
                if inplane:            # in-plane loads: membrane check (cp_membrane); the grillage is a poor membrane
                    loads[n][0] += side * L.T * math.cos(th) * f
                    loads[n][2] += V_w * f
    ic = xs.index(0.0)
    jc = zs.index(0.0)
    used = {n for mem in members for n in mem["nodes"]}
    nodes = {n: v for n, v in nodes.items() if n in used}
    loads = {n: v for n, v in loads.items() if n in used}
    pin = nid(ic, jc)
    loads[pin][1] += -H_cp
    sup = {n: {"spring": [0.0, kk, 0.0, 0.0, 0.0, 0.0]} for n, kk in springs.items()}
    # pin: x, z and pitch (rx) held by the frame; roll about y free (elastomer bushing); y carried by the foundation
    sup[pin] = {"fix": "x z rx rz", "spring": [0.0, springs.get(pin, 0.0), 0.0, 0.0, 0.0, 0.0]}
    model = {"nodes": nodes, "members": members,
             "supports": sup,
             "loads": {n: list(v) for n, v in loads.items() if np.any(v)},
             "meta": {"P_body": P_pad, "H_cp": H_cp, "V_w": V_w, "V_pad": V_pad, "theta": theta_deg,
                      "k_found": kf, "pin": pin, "springs": springs, "load": L.name}}
    return model


def cp_solve(cp: CentrePlate, L: LoadSet, e_pad: float = 0.0, **kw) -> dict:
    model = cp_model(cp, L, e_pad=e_pad, **kw)
    res = solve(model, name=f"CP {L.name} e{e_pad:+.0f}")
    rows = []
    for mi, mem in enumerate(model["members"]):
        if mem["group"] == "rigid":
            continue
        sec = mem["section"]
        smax, tmax = 0.0, 0.0
        for e in res.members[mi]["elements"]:
            for end in (0, 1):
                N, Vy, Vz, T, My, Mz = res.elem_forces[e, end]
                s_out = abs(Mz) * mem["c"] / sec.Iz
                s_in = abs(My) * (mem["b"] / 2) / sec.Iy
                s = abs(N) / sec.A + s_out + s_in
                tau = abs(T) / sec.Wt
                s1 = s / 2 + math.sqrt((s / 2) ** 2 + tau ** 2)       # max principal (brittle-ish GF-PA)
                if s1 > smax:
                    smax, tmax = s1, tau
        x0 = np.array(model["nodes"][mem["nodes"][0]])
        x1 = np.array(model["nodes"][mem["nodes"][1]])
        rows.append({"id": mem["id"], "group": mem["group"], "x0": x0.tolist(), "x1": x1.tolist(),
                     "sigma1_mpa": smax, "tau_mpa": tmax})
    U = res.u.reshape(-1, 6)
    pin = model["meta"]["pin"]
    react = res.reactions[pin] - np.r_[0, res.reactions[pin][1], 0, 0, 0, 0]   # frame part (spring part removed)
    kf = model["meta"]["k_found"]
    disp = res.displacements
    p_kpa = {n: -kf * disp[n][1] * 1000.0 for n in model["meta"]["springs"]}
    hub_edge = [r for r in rows if r["group"] in ("spine", "strip_z", "strip_x")
                and min(np.hypot(r["x0"][0], r["x0"][2]), np.hypot(r["x1"][0], r["x1"][2])) <= cp.hub_d / 2 + 6]
    return {"model": model, "res": res, "rows": rows, "max": max(rows, key=lambda r: r["sigma1_mpa"]),
            "max_hub_edge": max(hub_edge, key=lambda r: r["sigma1_mpa"]) if hub_edge else None,
            "uy_max_mm": float(np.abs(U[: res.n_user_nodes, 1]).max()), "reaction": react.tolist(),
            "p_body_max_kpa": max(p_kpa.values()), "p_body_min_kpa": min(p_kpa.values()), "p_body": p_kpa}


def cp_membrane(cp: CentrePlate, L: LoadSet, theta_deg: float = THETA_ROOT_DEG,
                wing_v_share: float = WING_V_SHARE, ear: StitchedEar = StitchedEar()) -> dict:
    """In-plane (membrane) stress, closed form, at the two critical vertical sections of one half: the hub edge
    (x = hub_d / 2) and the body-to-ear junction (x = half_w_body; for the bow-tie, the narrow spine at flare_x).
    N = T cos(theta); shear = wing V share (+ the pad friction outboard of the section, plate mode); in-plane
    moment = those forces x their lever. sigma = N / A + 6 M / (t D^2), tau = 1.5 V / A (rectangle D x t)."""
    th = math.radians(theta_residual(cp, theta_deg))
    V_w = wing_v_share * L.V
    V_pad = (L.V - 2 * V_w) if cp.kind == "plate" else 0.0
    x_row = cp.half_w_body + (ear.row_x[1] - 75.0) * cp.ear_w / 30.0 * ear.first_row_share + \
        cp.half_w_body + (ear.row_x[0] - 75.0) * cp.ear_w / 30.0 * (1 - ear.first_row_share) - cp.half_w_body
    out = []
    secs = [cp.hub_d / 2, cp.half_w_body if cp.kind == "plate" else cp.flare_x - 1e-6]
    for xs_ in secs:
        D = 2 * cp.half_h if cp.kind == "plate" or xs_ >= cp.flare_x else 2 * cp.spine_half_h
        A = D * cp.t
        frac = max(cp.half_w_body - xs_, 0.0) / (2 * cp.half_w_body)          # pad share outboard of the section
        V = V_w + V_pad * frac
        M = V_w * (x_row - xs_) + V_pad * frac * (max(cp.half_w_body - xs_, 0.0) / 2)
        sig = L.T * math.cos(th) / A + 6 * M / (cp.t * D ** 2)
        tau = 1.5 * V / A
        s1 = sig / 2 + math.sqrt((sig / 2) ** 2 + tau ** 2)
        out.append({"x": xs_, "D": D, "N": L.T * math.cos(th), "V": V, "M": M, "sigma1_mpa": s1})
    return max(out, key=lambda r: r["sigma1_mpa"]) | {"all": out}


def annular_plate_mrb(q: float, a: float, b: float, nu: float) -> float:
    """Radial moment per unit length (N mm / mm) at the clamped inner edge of an annular plate, outer edge free,
    uniform pressure q over b..a (Roark Table 11.2 case 2L). Closed-form general solution
    w = C1 + C2 r^2 + C3 ln r + C4 r^2 ln r + q r^4 / (64 D), with D = 1 (moments do not depend on D).
    Used as a scale check of the as-drawn flat centre plate (hub-clamped, pad pressure over a ~ 82 mm disc)."""
    def dw(r):
        return np.array([0, 2 * r, 1 / r, 2 * r * math.log(r) + r]), q * r ** 3 / 16

    def d2w(r):
        return np.array([0, 2, -1 / r ** 2, 2 * math.log(r) + 3]), 3 * q * r ** 2 / 16

    def mr(r):
        a1, b1 = d2w(r)
        a2, b2 = dw(r)
        return -(a1 + nu * a2 / r), -(b1 + nu * b2 / r)
    rows = [np.array([1, b * b, math.log(b), b * b * math.log(b)]), dw(b)[0], mr(a)[0], np.array([0, 0, 0, -4 / a])]
    rhs = [-q * b ** 4 / 64, -dw(b)[1], -mr(a)[1], q * a / 2]
    C = np.linalg.solve(np.array(rows), np.array(rhs))
    m0, m1 = mr(b)
    return float(abs(m0 @ C + m1))


def cp_check(cp: CentrePlate = CentrePlate()) -> dict:
    """CP strength (C1, C2), fatigue (walk) and creep (carry), each at the worse pad centroid +/- e."""
    m = cp.mat
    out = {}
    for key, L in load_sets().items():
        worst = None
        for e in (0.0,):                    # foundation model: the pad centroid is an output, not an input
            r = cp_solve(cp, L, e_pad=e)
            if worst is None or r["max"]["sigma1_mpa"] > worst["max"]["sigma1_mpa"]:
                worst = r
                worst["e_pad"] = e
        mem = cp_membrane(cp, L)
        s_bend = worst["max"]["sigma1_mpa"]
        s = s_bend + mem["sigma1_mpa"]                  # superposed (conservative: peaks need not coincide)
        if L.kind == "strength":
            allow, kt = m["static"], 1.0
        elif L.kind == "fatigue":
            allow, kt = m["fatigue"], KT_FAT
        else:
            allow, kt = m["creep"], 1.0
        out[key] = {"load": L.name, "kind": L.kind, "sigma1_mpa": s, "sigma_bend_mpa": s_bend,
                    "sigma_membrane_mpa": mem["sigma1_mpa"], "membrane_at_x": mem["x"], "kt": kt, "allow_mpa": allow,
                    "sf_over_req": allow / (kt * s), "member": worst["max"]["id"], "group": worst["max"]["group"],
                    "at": [worst["max"]["x0"], worst["max"]["x1"]], "e_pad": worst["e_pad"],
                    "uy_max_mm": worst["uy_max_mm"], "reaction": worst["reaction"],
                    "p_body_max_kpa": worst["p_body_max_kpa"], "p_body_min_kpa": worst["p_body_min_kpa"],
                    "_solve": worst}
    return out


# ---------------------------------------------------------------------------------------------- stitched ear joint
def ear_check(cp: CentrePlate = CentrePlate(), ear: StitchedEar = StitchedEar(), theta_deg: float = THETA_ROOT_DEG) -> dict:
    """Per-hole loads and the PA66 / thread / textile checks of the stitched ear, every load set."""
    m = cp.mat
    thr = float(load(ear.thread).require("breaking_strength_n"))
    hole_cap = 1.5 * thr                     # repo seam rule (clothsim.fabric.stitch_strength_n_mm): 1.5 x thread / stitch
    n = ear.n_per_row(cp)
    span = (n - 1) * ear.pitch
    th = math.radians(theta_deg)
    d = ear.hole_d
    bearing_w = 2 * THREAD_D_MM              # saddle stitch: two thread passes per hole
    edge = cp.half_w - (cp.half_w_body + (ear.row_x[1] - 75.0) * cp.ear_w / 30.0)
    # textile: 1000D doubler + 330D shell on EACH face of the ear (double shear), strip strengths from clothsim
    import importlib
    fb = importlib.import_module("huntkit.clothsim.fabric")
    tex = {k: fb.fabric(k) for k in (ear.shell,)}
    s_shell = min(tex[ear.shell].strip_warp, tex[ear.shell].strip_weft)
    g2s = 31.25
    d1000 = load(ear.doubler)
    s_dbl = min(float(d1000.require("grab_warp_n")), float(d1000.require("grab_weft_n"))) / g2s
    seam_eff = 0.80
    out = {"n_per_row": n, "rows": ear.rows, "span_mm": span, "edge_mm": edge, "hole_cap_n": hole_cap, "cases": {}}
    for key, L in load_sets().items():
        V_w = WING_V_SHARE * L.V
        R = math.hypot(L.T, V_w)                       # in-plane resultant on the ear (the T sin theta part is
        #                                                 out-of-plane on the ear: carried by the fabric wrap, not holes)
        f_hole = ear.first_row_share * R / n * ear.end_hole_factor
        bearing = f_hole / (bearing_w * cp.t)
        shear_out = f_hole / (2 * (edge - d / 2) * cp.t)
        net = L.T / ((2 * cp.half_h - n * d) * cp.t)   # net tension across the outer row
        fab_line = R / (2 * cp.half_h)                  # N/mm into the fabric stack, both faces together
        fab_cap = seam_eff * 2 * (s_shell + s_dbl)      # two faces x (shell + doubler)
        if L.kind == "strength":
            allow, kt = m["static"], 1.0
        elif L.kind == "fatigue":
            allow, kt = m["fatigue"], KT_HOLE
        else:
            allow, kt = m["creep"], 1.0
        out["cases"][key] = {
            "load": L.name, "kind": L.kind, "R_n": R, "f_hole_n": f_hole,
            "thread_sf": hole_cap / f_hole / (1.0 if L.kind == "strength" else 1 / 0.3),   # textile fatigue: 0.3 x break
            "bearing_mpa": bearing, "bearing_sf": allow / bearing,
            "shear_out_mpa": shear_out, "shear_out_sf": 0.5 * allow / shear_out,
            "net_mpa": net, "net_sf": allow / (kt * net),
            "fabric_n_mm": fab_line, "fabric_sf": fab_cap / fab_line / (1.0 if L.kind == "strength" else 1 / 0.3),
        }
    c = out["cases"]
    out["min_sf"] = min(min(v for k, v in cc.items() if k.endswith("_sf")) for cc in c.values())
    return out


# ---------------------------------------------------------------------------------------------- wing textile + tip + 2:1
def wing_textile_check(shell: str = "cordura_330d_nylon66", tip_h: float = 105.0, root_h: float = 150.0) -> dict:
    """The floating-HDPE wing carries T in its shell textile. Strength at the tip height (smallest section),
    and the stretch at the walking peak (secant stiffness, +/- 50 %)."""
    import importlib
    fb = importlib.import_module("huntkit.clothsim.fabric")
    f = fb.fabric(shell)
    ls_ = load_sets()
    cap = 0.80 * min(f.strip_warp, f.strip_weft)          # seam efficiency 0.8 (clothsim fabrics.yaml)
    q_f = ls_["C2"].T / tip_h
    q_w = ls_["walk"].T / tip_h
    L_xxl = WING_LEN_XXL_MM
    strain = (ls_["walk"].T / (0.5 * (tip_h + root_h))) / f.k_warp
    return {"shell": shell, "strip_n_mm": min(f.strip_warp, f.strip_weft), "cap_n_mm": cap,
            "q_factored_n_mm": q_f, "sf_strength": cap / q_f, "q_walk_n_mm": q_w,
            "walk_frac_of_strip": q_w / min(f.strip_warp, f.strip_weft),
            "sf_fatigue": 0.3 * min(f.strip_warp, f.strip_weft) / q_w,
            "strain_walk": strain, "stretch_xxl_mm": strain * float(L_xxl),
            "basis": "clothsim strip = grab / 31.25 mm, secant k = strip / 25 % (warp); textile 1e5 limit 0.3 x strip "
                     "(ASSUMPTION)"}


def tab_check(box_l: float = 40.0, web_w: float = 25.0, stitch_mm: float = 3.5) -> dict:
    """Belt-side anchor of the 2:1 = the D-ring tab on the wing tip (carries the full wing tension T: both legs of
    T/2 turn round the D-ring). 25 mm poly webbing doubled round the ring, box-X stitched (tex 135) through the
    shell and a 1000D tip doubler. Also: D-ring, heavy ladder lock (lock leg), 50 mm buckle, webbing."""
    ls_ = load_sets()
    thr = float(load("bonded_nylon_tex135").require("breaking_strength_n"))
    per_mm = 1.5 * thr / stitch_mm                                  # repo seam rule, 301 lockstitch
    diag = math.hypot(web_w, box_l)
    total = 2 * web_w + 2 * box_l + 2 * diag
    eff = 0.5 * total                                               # ASSUMPTION: half the box-X length effective
    box_cap = per_mm * eff
    ring = load("d_ring_25mm_aluminium")
    lock = load("ladder_lock_25mm_heavy")
    lock_old = load("ladder_lock_25mm")
    buckle = load("buckle_side_release_50mm")
    web = load("poly_webbing_25mm")
    eta = 0.85                                                      # 2:1 efficiency ASSUMPTION (hipbelt_fit.md)
    lock_frac = 1 / (2 * eta)                                       # lock leg while pulling and after (materials rec)
    TF, TW, T2 = ls_["C2"].T, ls_["walk"].T, ls_["walk"].T * ls.G_STUMBLE / ls.G_WALK
    # 1000D + 330D under the box: load spreads from the 25 mm tab at 30 deg (ASSUMPTION)
    import importlib
    fb = importlib.import_module("huntkit.clothsim.fabric")
    s330 = min(fb.fabric("cordura_330d_nylon66").strip_warp, fb.fabric("cordura_330d_nylon66").strip_weft)
    d1000 = load("cordura_1000d_nylon66")
    s1000 = min(float(d1000.require("grab_warp_n")), float(d1000.require("grab_weft_n"))) / 31.25
    w_eff = web_w + 2 * box_l * math.tan(math.radians(30))
    fab_cap = 0.8 * (s330 + s1000) * w_eff
    return {
        "box_x": {"total_mm": total, "effective_mm": eff, "per_mm_n": per_mm, "cap_n": box_cap, "sf": box_cap / TF},
        "fabric_under_box": {"w_eff_mm": w_eff, "cap_n": fab_cap, "sf": fab_cap / TF},
        "d_ring": {"break_n": float(ring.require("breaking_strength_n")), "sf": float(ring.require("breaking_strength_n")) / TF},
        "lock_leg_frac": lock_frac,
        "ladder_lock_heavy": {"slip_n": float(lock.require("slip_load_n")), "break_n": float(lock.require("breaking_strength_n")),
                              "slip_sf_walk": float(lock.require("slip_load_n")) / (lock_frac * TW),
                              "slip_sf_stumble": float(lock.require("slip_load_n")) / (lock_frac * T2),
                              "break_sf": float(lock.require("breaking_strength_n")) / (lock_frac * TF)},
        "ladder_lock_classic_slip_sf_walk": float(lock_old.require("slip_load_n")) / (lock_frac * TW),
        "lock_if_routed_between_anchor_and_ring": {
            "lock_leg_frac": 1.0, "slip_sf_walk": float(lock.require("slip_load_n")) / TW,
            "note": "anchor on the wing, lock, then D-ring: once the hand lets go the D-ring legs go slack and the lock "
                    "holds the full T (1:1 hold)"},
        "buckle_50": {"break_n": float(buckle.require("breaking_strength_n")),
                      "sf": float(buckle.require("breaking_strength_n")) / TF},
        "webbing_25": {"break_n": float(web.require("breaking_strength_n")),
                       "sf": float(web.require("breaking_strength_n")) / (lock_frac * TF)},
        "T": {"factored": TF, "walk": TW, "stumble_limit": T2},
    }


def hdpe_tab(box_l: float = 40.0, web_w: float = 25.0, stitch_mm: float = 3.5, h_stiff: float = 85.0,
             tip_h: float = 105.0, e_end: float = 15.0) -> dict:
    """HDPE creep at the D-ring tab. Two cases:
    (a) B as defined here: HDPE floats (no fastener at the root): a free body, so whatever the tab stitches pierce,
        the net tension in it is zero (only friction drag; bounded by mu x pressure, small).
    (b) HDPE fixed at both ends (root fasteners, as the old cant snap): it carries its stiffness share of T into
        the tab stitch holes -> needle-hole bearing and shear-out to the HDPE end (soft tip, e_end mm)."""
    import importlib
    fb = importlib.import_module("huntkit.clothsim.fabric")
    ls_ = load_sets()
    k_shell = fb.fabric("cordura_330d_nylon66").k_warp
    Et = float(load("hdpe_sheet").require("youngs_modulus_mpa")) * 1.0      # 1.0 mm
    share = Et * h_stiff / (Et * h_stiff + k_shell * tip_h)
    diag = math.hypot(web_w, box_l)
    holes = int((2 * web_w + 2 * box_l + 2 * diag) / stitch_mm)
    holes_eff = 0.5 * holes                                                  # ASSUMPTION as tab_check
    t = 1.0
    out = {"share_if_fixed": share, "holes": holes}
    for key in ("carry", "walk", "C2"):
        T = ls_[key].T
        f = share * T / holes_eff
        sb = f / (2 * THREAD_D_MM * t)                                        # lockstitch: 2 thread passes per hole
        so = share * T / (2 * e_end * t + web_w * t)                          # block shear ahead of the box end
        out[key] = {"T": T, "f_hole_n": f, "bearing_mpa": sb, "shear_out_mpa": so}
    y = float(load("hdpe_sheet").require("yield_strength_mpa"))
    out["fixed_creep_sf"] = HDPE_SUSTAINED_MPA / out["carry"]["bearing_mpa"]
    out["fixed_fatigue_sf"] = HDPE_FATIGUE_MPA / out["walk"]["bearing_mpa"]
    out["fixed_static_sf"] = y / out["C2"]["bearing_mpa"]
    out["fixed_shearout_creep_sf"] = 0.5 * HDPE_SUSTAINED_MPA / out["carry"]["shear_out_mpa"]
    out["floating"] = "net HDPE tension 0 (free body): no creep path; stitches through it are allowed"
    return out


# ---------------------------------------------------------------------------------------------- pivot (hand checks)
def pivot_check(cp: CentrePlate = CentrePlate(), d_pin: float = 10.0, l_eng: float = 12.0, stand: float = 21.0,
                boss_r: float = 16.0, screw_arm: float = 16.0, e_pad: float = E_PAD_MM,
                h_on_pivot: bool | None = None) -> dict:
    """Hand checks on the pivot with the lumbar push H on it (FE of the SLM mount: hipbelt_pivot_fe).
    * The CP hub bears axially on the mount face through a POM thrust washer (D36): H is compressive (the pad pushes
      the CP toward the frame in every rev C case), so the POM latch carries none of it.
    * The pad-offset moment e H goes into the face contact; the part the face cannot hold (resultant beyond 0.8 x the
      face radius) goes into the pin as a couple over the engagement length.
    * The 2 x M5 that fix the SLM mount to the printed frame boss (x +/-11, z 0) see prying: tipping about the boss
      edge (r 16), V at the pin stand-off (21 mm) plus e H, less H x r (H presses the face)."""
    ti = load("ti_6al_4v")
    sy = float(ti.require("yield_strength_sbasis_mpa"))
    se = float(ti.require("fatigue_limit_mpa"))
    m = cp_material(cp.hub_mat)
    if h_on_pivot is None:
        h_on_pivot = cp.kind == "plate"
    out = {}
    face_r = 0.8 * cp.hub_d / 2
    A_face = math.pi / 4 * (cp.hub_d ** 2 - cp.bore_d ** 2)
    for key, L in load_sets().items():
        H = L.H if h_on_pivot else 0.0
        V = L.V
        m_res = H * max(abs(e_pad) - face_r, 0.0)               # moment the face cannot hold
        M_pin = V * l_eng / 2 + m_res
        s_pin = 32 * M_pin / (math.pi * d_pin ** 3)
        bear = V / (d_pin * l_eng) + 6 * m_res / (d_pin * l_eng ** 2)
        face_p = max(H, 1.0) / (0.25 * A_face)                  # crescent contact: 1/4 of the face (conservative)
        M_tip = stand * V + max(e_pad, 0.0) * H
        T_scr = max((M_tip - boss_r * H) / (2 * screw_arm), 0.0)
        T_scr_noH = stand * V / (2 * screw_arm)
        if L.kind == "strength":
            pin_sf = sy / s_pin
            pa_allow = m["static"]
        elif L.kind == "fatigue":
            pin_sf = se / (2.0 * s_pin / 2) * 1.0               # R=0: amplitude s/2 vs Se with Kt 2 (Goodman ignored: s << Su)
            pa_allow = m["fatigue"]
        else:
            pin_sf = sy / s_pin
            pa_allow = m["creep"]
        out[key] = {"load": L.name, "H_n": H, "V_n": V, "pin_sigma_mpa": s_pin, "pin_sf": pin_sf,
                    "hub_bearing_mpa": bear, "hub_bearing_sf": pa_allow / bear,
                    "face_p_mpa": face_p, "face_sf": pa_allow / face_p,
                    "m5_tension_n": T_scr, "m5_tension_noH_n": T_scr_noH}
    return out


M5_INSERT_PULLOUT_N = 1500.0    # ASSUMPTION: brass M5 heat-set insert pull-out in printed PA12-CF at 20 C (no record)


def m5_check(piv: dict) -> dict:
    cap = M5_INSERT_PULLOUT_N * HOT
    return {k: {"T_n": v["m5_tension_n"], "T_noH_n": v["m5_tension_noH_n"], "cap_n": cap,
                "sf": cap / max(v["m5_tension_n"], 1e-9) if v["m5_tension_n"] > 0 else float("inf"),
                "sf_noH": cap / v["m5_tension_noH_n"]}
            for k, v in piv.items() if k in ("C2", "C1")}


# ---------------------------------------------------------------------------------------------- run all
def summary_rows(res: dict) -> list[dict]:
    """One row per check: item, case, SF / required (>= 1 passes; the case factor is already in the load)."""
    R = []

    def add(group, item, case, sf, basis):
        R.append({"group": group, "item": item, "case": case, "sf_over_req": float(sf), "basis": basis})
    for k, v in res["cp"].items():
        add("Centre plate", f"CP rec.: curved 6061-T6 1.5 bow-tie ({res['cp_mass']['total_g']:.0f} g)", k, v["sf_over_req"],
            f"{v['sigma1_mpa']:.1f} MPa x Kt {v['kt']} vs {v['allow_mpa']:.1f}")
    for name, vv in res.get("cp_variants", {}).items():
        if name == "recommended":
            continue
        k = min(vv["sf"], key=vv["sf"].get)
        grp = "Rejected" if name == "as_drawn" else "Centre plate"
        add(grp, f"CP {name.replace('_', ' ')} ({vv['mass_g']:.0f} g, fallback)" if grp != "Rejected"
            else f"CP as drawn: flat PA66 3 mm under the pad ({vv['mass_g']:.0f} g)", k, vv["sf"][k],
            f"{vv['material']} {vv['kind']}")
    for k, v in res["ear"]["cases"].items():
        add("Wing joint", "ear: thread per hole", k, v["thread_sf"], f"{v['f_hole_n']:.1f} N/hole")
        add("Wing joint", "ear: plate bearing (thread)", k, v["bearing_sf"], f"{v['bearing_mpa']:.1f} MPa")
        add("Wing joint", "ear: plate shear-out", k, v["shear_out_sf"], f"{v['shear_out_mpa']:.1f} MPa")
        add("Wing joint", "ear: plate net section", k, v["net_sf"], f"{v['net_mpa']:.1f} MPa")
        add("Wing joint", "ear: textile (shell + 1000D)", k, v["fabric_sf"], f"{v['fabric_n_mm']:.1f} N/mm")
    w = res["wing"]
    add("Wing", "wing shell 330D at the tip", "C2", w["sf_strength"], f"{w['q_factored_n_mm']:.1f} N/mm")
    add("Wing", "wing shell 330D at the tip", "walk", w["sf_fatigue"], f"{w['q_walk_n_mm']:.1f} N/mm")
    t = res["tab"]
    add("2:1 pull", "D-ring tab box-X (tex 135)", "C2", t["box_x"]["sf"], f"{t['box_x']['cap_n']:.0f} N cap")
    add("2:1 pull", "textile under the tab", "C2", t["fabric_under_box"]["sf"], f"{t['fabric_under_box']['cap_n']:.0f} N cap")
    add("2:1 pull", "D-ring 25 mm Al", "C2", t["d_ring"]["sf"], f"break {t['d_ring']['break_n']:.0f} N")
    add("2:1 pull", "heavy ladder lock slip", "walk", t["ladder_lock_heavy"]["slip_sf_walk"] / 1.5,
        "slip / (1.5 x lock leg), test-qualified criterion")
    add("2:1 pull", "heavy ladder lock break", "C2", t["ladder_lock_heavy"]["break_sf"], "break / lock leg")
    add("2:1 pull", "50 mm buckle", "C2", t["buckle_50"]["sf"], f"break {t['buckle_50']['break_n']:.0f} N")
    h = res["hdpe"]
    add("Rejected", "HDPE at tab, if fixed both ends: creep", "carry", h["fixed_creep_sf"],
        f"{h['carry']['bearing_mpa']:.1f} MPa vs {HDPE_SUSTAINED_MPA}")
    for k, v in res["pivot"].items():
        add("Ti pivot", "Ti pin bending", k, v["pin_sf"], f"{v['pin_sigma_mpa']:.0f} MPa")
        add("Ti pivot", "CP hub bore bearing", k, v["hub_bearing_sf"], f"{v['hub_bearing_mpa']:.1f} MPa")
    for k, v in res["pivot_with_H"].items():
        add("Ti pivot", "Ti pin bending, H on the pin (bound)", k, v["pin_sf"], f"{v['pin_sigma_mpa']:.0f} MPa")
        add("Ti pivot", "PA66 hub bore bearing, H on the pin", k, v["hub_bearing_sf"], f"{v['hub_bearing_mpa']:.1f} MPa")
        add("Ti pivot", "PA66 hub thrust face, H on the pin", k, v["face_sf"], f"{v['face_p_mpa']:.1f} MPa")
    for k, v in res["m5_with_H"].items():
        add("Ti pivot", "2 x M5 inserts, mount to frame, H on the pin", k, v["sf"],
            f"{v['T_n']:.0f} N vs {v['cap_n']:.0f} (ASSUMPTION cap)")
    for k, v in res["m5"].items():
        add("Ti pivot", "2 x M5 inserts, mount to frame, H on frame", k, v["sf"],
            f"{v['T_n']:.0f} N vs {v['cap_n']:.0f} (ASSUMPTION cap)")
    fe = res.get("pivot_fe")
    if fe:
        add("Ti pivot", "SLM Ti mount FE (all cases + H)", "all", fe["min_sf_over_req_with_H"],
            f"governing {fe['governing_with_H']}")
        add("Ti pivot", "SLM Ti mount FE fatigue", "walk", fe["fatigue_with_H"]["sf"],
            f"{fe['fatigue_with_H']['smax_mpa']:.0f} MPa max")
    return R


def run(write: bool = True, cp: CentrePlate = CentrePlate()) -> dict:
    res = {"loads": {k: asdict(v) for k, v in load_sets().items()}, "cp_geometry": asdict(cp),
           "ear_geometry": asdict(StitchedEar()), "cp_mass": cp.mass_g(), "cp_material": cp.mat}
    cpc = cp_check(cp)
    res["cp"] = {k: {kk: vv for kk, vv in v.items() if kk != "_solve"} for k, v in cpc.items()}
    res["ear"] = ear_check(cp)
    res["wing"] = wing_textile_check()
    res["tab"] = tab_check()
    res["hdpe"] = hdpe_tab()
    res["pivot"] = pivot_check(cp)
    res["m5"] = m5_check(res["pivot"])
    res["pivot_with_H"] = pivot_check(cp, h_on_pivot=True)
    res["m5_with_H"] = m5_check(res["pivot_with_H"])
    res["cp_variants"] = {}
    for name, v in CP_VARIANTS.items():
        c = cpc if v == cp else cp_check(v)
        res["cp_variants"][name] = {"kind": v.kind, "material": v.material, "t": v.t, "curve_deg": v.curve_deg,
                                    "mass_g": v.mass_g()["total_g"],
                                    "sf": {k: float(x["sf_over_req"]) for k, x in c.items()},
                                    "sigma_bend": {k: float(x["sigma_bend_mpa"]) for k, x in c.items()},
                                    "sigma_membrane": {k: float(x["sigma_membrane_mpa"]) for k, x in c.items()},
                                    "p_body_walk_kpa": [float(c["walk"]["p_body_min_kpa"]), float(c["walk"]["p_body_max_kpa"])]}
    if PIVOT_FE_JSON.exists():
        fe = json.loads(PIVOT_FE_JSON.read_text())
        res["pivot_fe"] = {k: v for k, v in fe.items() if k != "rows"}
    res["summary"] = summary_rows(res)
    res["mass"] = mass_table(cp)
    if write:
        OUT_JSON.write_text(json.dumps(res, indent=1, default=float))
    res["_cp_solve"] = {k: v["_solve"] for k, v in cpc.items()}
    return res


def mass_table(cp: CentrePlate) -> dict:
    """Load-path members of the belt joint region, B as defined here vs the booked ASSUMPTION."""
    cm = cp.mass_g()
    d = load("cordura_1000d_nylon66")
    gsm = float(d.require("areal_density_gsm"))
    dbl = 2 * 2 * (cp.ear_w + 20) * (2 * cp.half_h + 10) * gsm * 1e-6      # 2 wings x 2 faces, ear + 20 mm
    tip = 2 * 60 * 100 * gsm * 1e-6                                         # 2 tip doublers 60 x 100
    thread = 2 * StitchedEar().rows * StitchedEar().n_per_row(cp) * 2 * (cp.t + 4) * 2 * 0.135e-3 * 2  # small
    return {"centre_plate_g": cm["total_g"], "cp_breakdown": cm, "root_doublers_1000d_g": dbl, "tip_doublers_1000d_g": tip,
            "ear_thread_g": thread, "thrust_washer_pom_g": 1.0,
            "joint_total_g": cm["total_g"] + dbl + tip + thread + 1.0,
            "booked_g": 45.0 + 6.0, "booked_basis": "centre plate + latch 45 g ASSUMPTION + cant snap 6 g (deleted in B)"}


# ---------------------------------------------------------------------------------------------- figures
def fig_utilisation(res: dict, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = res["summary"]
    # worst case per item
    best = {}
    for r in rows:
        k = (r["group"], r["item"])
        if k not in best or r["sf_over_req"] < best[k]["sf_over_req"]:
            best[k] = r
    order = ["Centre plate", "Wing joint", "Wing", "2:1 pull", "Ti pivot", "Rejected"]
    items = sorted(best.values(), key=lambda r: (order.index(r["group"]) if r["group"] in order else 9,
                                                 -1 / r["sf_over_req"]))
    util = [1 / r["sf_over_req"] for r in items]
    labels = [f"{r['item']}  [{r['case']}]" for r in items]
    fig, ax = plt.subplots(figsize=(9.5, 0.36 * len(items) + 1.8), dpi=110)
    cols = {"Centre plate": "#468faf", "Wing joint": "#2a6f97", "Wing": "#52796f", "2:1 pull": "#bc6c25",
            "Ti pivot": "#6a4c93", "Rejected": "#9e9e9e"}
    y = np.arange(len(items))[::-1]
    for yi, u, r in zip(y, util, items):
        c = cols.get(r["group"], "#777")
        ax.barh(yi, min(u, 1.6), color=c if (u <= 1.0 or r["group"] == "Rejected") else "#c1121f", height=0.66,
                hatch="//" if r["group"] == "Rejected" else None, edgecolor="#c1121f" if u > 1.0 else None)
        ax.text(min(u, 1.6) + 0.01, yi, f"SF/req {r['sf_over_req']:.2f}", va="center", fontsize=8)
    ax.axvline(1.0, color="#c1121f", lw=1.2, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 1.95)
    ax.set_xlabel("utilisation = 1 / (SF / required)   (bar past the red line = fails; factor already in the load)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols.values()]
    ax.legend(handles, cols.keys(), loc="upper right", fontsize=8, frameon=True, framealpha=0.9)
    ax.set_title("Hipbelt B structural check, HA-LS-1 rev C, worst case per item (pass = bar left of the red line)\n"
                 "grey hatched = rejected options: the centre plate as drawn, and HDPE fastened at both ends", fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    shrink(path)


def fig_cp(res: dict, cp: CentrePlate, path: Path):
    """CP grillage: plan view coloured by utilisation (C2) and the out-of-plane deflection (side view)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    s = res["_cp_solve"]["C2"]
    m = cp.mat
    model, rr = s["model"], s["res"]
    U = rr.u.reshape(-1, 6)
    disp = {nid: U[i] for i, nid in enumerate(rr.node_ids[: rr.n_user_nodes])}
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), dpi=110, gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axs[0]
    norm = colors.Normalize(0, 1.0)
    cmap = matplotlib.colormaps["viridis"]
    for r in s["rows"]:
        u = min(r["sigma1_mpa"] / m["static"], 1.0)
        ax.plot([r["x0"][0], r["x1"][0]], [r["x0"][2], r["x1"][2]], color=cmap(norm(u)), lw=2 + 6 * u,
                solid_capstyle="round")
    ax.add_patch(plt.Circle((0, 0), cp.hub_d / 2, color="#444", alpha=0.6))
    ax.add_patch(plt.Rectangle((-cp.half_w_body, -cp.half_h), 2 * cp.half_w_body, 2 * cp.half_h, fill=False, ls=":",
                               color="#999"))
    pad_txt = ("lumbar pad 150 x 150 (dotted) bears on the FRAME lumbar pan; the CP only carries the wings"
               if cp.kind == "bowtie" else "lumbar pad 150 x 150 (dotted) bears on this plate")
    e = StitchedEar()
    n = e.n_per_row(cp)
    zz = np.linspace(-(n - 1) * e.pitch / 2, (n - 1) * e.pitch / 2, n)
    for xr in e.row_x:
        for sd in (-1, 1):
            ax.plot(np.full(n, sd * (cp.half_w_body + (xr - 75.0) * cp.ear_w / 30.0)), zz, ".", color="#d00", ms=2.5)
    ax.text(0, -cp.half_h - 15, pad_txt, ha="center", fontsize=7.5)
    ax.text(cp.half_w - 2, cp.half_h + 5, "ear: 2 rows of 2 mm\nstitch holes", ha="right", fontsize=8, color="#d00")
    ax.set_aspect("equal")
    ax.set_xlim(-cp.half_w - 8, cp.half_w + 8)
    ax.set_ylim(-cp.half_h - 22, cp.half_h + 18)
    ax.set_xlabel("x lateral, mm (seen from the wearer)")
    ax.set_ylabel("z, mm (0 = pivot, frame z 120)")
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=ax, shrink=0.8, label=f"plate-bending utilisation, C2 (sigma1 / {m['static']:.0f} MPa)")
    v = res["cp"]["C2"]
    w = res["cp"]["walk"]
    ax.set_title(f"Centre plate (rec.): {m['id']} {cp.t:g} mm bow-tie, curved {cp.curve_deg:g} deg, {res['cp_mass']['total_g']:.0f} g\n"
                 f"C2 (T {res['loads']['C2']['T']:.0f} N/side x 1.5 incl.): bending {v['sigma_bend_mpa']:.0f} + membrane "
                 f"{v['sigma_membrane_mpa']:.0f} MPa, SF/req {v['sf_over_req']:.2f}; walk fatigue SF/req {w['sf_over_req']:.2f}",
                 fontsize=9)
    ax2 = axs[1]
    zs = _zs(cp)
    xs = _xs(cp)
    for j, z in enumerate(zs):
        px, py = [], []
        for i, x in enumerate(xs):
            if f"n{i}_{j}" not in disp:
                continue
            if px and x - px[-1] > 20.0:
                px.append(np.nan)
                py.append(np.nan)
            px.append(x)
            py.append(disp[f"n{i}_{j}"][1])
        if px:
            ax2.plot(px, py, "-o", ms=2, lw=1, label=f"z {z:+.0f}")
    ax2.axhline(0, color="#999", lw=0.6)
    ax2.set_xlabel("x, mm")
    ax2.set_ylabel("out-of-plane deflection uy, mm (+ toward the frame)")
    ax2.set_title(f"on the pad + tissue foundation: deflection C2 (max {v['uy_max_mm']:.1f} mm)\n"
                  f"walking pressure under the plate {w['p_body_min_kpa']:.0f}-{w['p_body_max_kpa']:.0f} kPa", fontsize=9)
    ax2.legend(fontsize=7, ncol=2)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    shrink(path)


def shrink(path: Path, limit: int = 1_500_000):
    if path.stat().st_size <= limit:
        return
    from PIL import Image
    im = Image.open(path)
    im = im.convert("P", palette=Image.ADAPTIVE, colors=128)
    im.save(path, optimize=True)


def figures(res: dict, cp: CentrePlate = CentrePlate()) -> list[Path]:
    SCREENS.mkdir(parents=True, exist_ok=True)
    p1 = SCREENS / f"{DATE}_hipbelt_fea_1.png"
    p2 = SCREENS / f"{DATE}_hipbelt_fea_2.png"
    fig_utilisation(res, p1)
    fig_cp(res, cp, p2)
    import shutil
    an = PACK / "analysis"
    shutil.copy(p1, an / "hipbelt_structural_1.png")
    shutil.copy(p2, an / "hipbelt_structural_2.png")
    return [p1, p2]


if __name__ == "__main__":
    r = run()
    paths = figures(r)
    worst = min(r["summary"], key=lambda x: x["sf_over_req"] if "fixed" not in x["item"] else 99)
    print(json.dumps({k: (round(v["sf_over_req"], 2), v["member"]) for k, v in r["cp"].items()}))
    print("ear min SF", round(r["ear"]["min_sf"], 2), "CP mass", round(r["cp_mass"]["total_g"], 1))
    print("worst (excluding the rejected fixed-HDPE case):", worst)
    print("\n".join(str(p) for p in paths))
