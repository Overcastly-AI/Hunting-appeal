"""Hipbelt fit and load-transfer model (pack-designer, 2026-11-08).

Owner: "the hip belt needs improvement, to better fit the hips; it takes all the load."
Research: ``docs/research/hipbelt_fit.md``. Write-up: ``designs/pack_5200/analysis/hipbelt_fit.md``.

What it models (simple, transparent, every input cited or tagged ASSUMPTION):

1. **Hip forms from ANSUR II.** For each belt size band and sex, the median subject's waist breadth/depth/circumference
   (omphalion level = iliac-crest level: ANSUR II medians 1055 vs 1061 mm, men) and hip breadth / buttock depth at
   buttock height. The belt-height section is a superellipse whose exponent is SOLVED so its perimeter equals the
   measured circumference. Below the waist the section widens laterally by the lateral cone slope
   ((hip breadth - waist breadth)/2 over the height drop) and posteriorly by the posterior slope (buttock depth -
   waist depth, ASSUMPTION: all of it behind, the abdomen plane vertical). This is the cone the belt sits on.
2. **Belt as a developable band** (``BeltDesign``): lumbar pad on the rigid centre plate, two wings with a height
   profile, a foam stack, an optional HDPE stiffener and a pattern cone angle ``beta`` (0 = straight/cylindrical
   wing; a pre-curved wing pattern gives beta > 0). The stiffened band is in-plane stiff (hoop stiffness
   E t / r^2), so it cannot tilt its generators to match the body cone; only the share k/(k + k_hoop) of the
   mismatch is taken up by rotation, the rest by foam + tissue compression across the belt height.
3. **Loads** (HA-LS-1 rev C, ``analysis/load_standard.md``): 68 kg, hips 80 % of the vertical load (R-07), bag CG
   205 mm aft at z 550; the overturning moment is reacted by the shoulder straps at the yoke and the lumbar pad
   (couple). Belt hoop tension T gives a line load q = T kappa on the wings (membrane), lumbar = couple + T kappa.
4. **Pressure across the belt height** per station: Winkler foundation (foam layers + tissue column in series),
   closed-form full / partial (triangular) contact under the remaining generator mismatch.
5. **Slip** (wedge + Coulomb): each element pressed horizontally by N on a surface sloping alpha outward-down holds
   N (tan a + mu) / (1 - mu tan a) vertically. mu = 0.30 (ASSUMPTION, low end of cited skin-textile 0.27-0.71).

It reports peak / mean pressure, contact area, belt tension needed to hold the hip share without slip at the
1.6 g walking peak, the pressure-limited hold, and tip-to-ASIS clearance. It is a comparison model for belt
shapes, not a replacement for a pressure-mat test (prototype test HB-1 in the write-up).

    python -m huntkit.gendesign.hipbelt --anthro <ANSUR male csv> <ANSUR female csv>   # rebuild the hip forms YAML
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import yaml

from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANTHRO_YAML = PACK / "analysis" / "hipbelt_anthro.yaml"
IN = 25.4
G = 9.81

# ----------------------------------------------------------------------------------------- loads (rev C)
RATED_KG = 68.0                 # R-02, load_standard.md
HIP_SHARE = 0.80                # R-07 (REI / AMC fit guidance 80 %; measured military framed packs ~30 %, research §1)
WALK_G = 1.6                    # load_standard.md fatigue: Rome walking peak 1.6 g
CG_AFT_MM = 205.0               # rev C bag cases C1-C4, C8 (load_standard.md §4.2)
CG_Z = 550.0
Z_IC = 120.0                    # iliac crest = hipbelt pivot height (build_geometry.Z_IC)
YOKE_Z = {15: 451.0, 17: 502.0, 19: 553.0, 21: 603.0, 23: 654.0}   # DESIGN.md §5.1 crown settings
LUMBAR_Z = 120.0                # lumbar pad load centroid at the crest datum (ASSUMPTION)
MU = 0.30                       # ASSUMPTION: skin/clothing-textile friction, low end of 0.27-0.71 (research §2.4)
MU_HIGH = 0.50                  # sensitivity

# ----------------------------------------------------------------------------------------- thresholds (research §2)
P_OCCLUSION_KPA = 16.0          # Holloway et al. 1976 (via Wettenschwiler 2015): blood occlusion, sustained -> mean
P_SHOULDER_KPA = 14.0           # Golriz et al. 2017 (back_comfort.md): prolonged-carriage limit, shoulder/back
P_HIP_PEAK_KPA = round(2.135 * P_SHOULDER_KPA + 18.75, 1)   # Wettenschwiler 2015 eq. 1, equal discomfort: 48.6 kPa
P_BONY_KPA = 30.0               # ASSUMPTION: crest top / ASIS (no site-specific PPT found): ~0.6 x hip peak limit
T_TESTED_MAX_N = 120.0          # Mackie/Wettenschwiler 2015 tested belt tensions 30-120 N (20 kg load)
ASIS_HALF_MM = 113.5            # inter-ASIS distance 227 +/- 16 mm, CT of 200 adults (research §1.2)
ASIS_CLEAR_MM = 15.0            # ASSUMPTION: wing tip (and its webbing bartack) ends >= 15 mm behind the ASIS

# ----------------------------------------------------------------------------------------- tissue (as spreader.py)
TISSUE_E_KPA = 60.0             # spreader.py TISSUE_E_KPA (design), 20 kPa soft sensitivity
TISSUE_H_SOFT = 25.0            # spreader.py TISSUE_H: lumbar / lateral hip soft tissue column
TISSUE_H_CREST = 12.0           # ASSUMPTION: thinner column over the iliac crest (bony): stiffer, higher peak

SIZES_CURRENT = {"S": (26, 30), "M": (30, 34), "L": (34, 38), "XL": (38, 42)}   # build_geometry.HIPBELT_SIZES (in)


# ======================================================================================= anthropometry
ANSUR_KEYS = ("waistcircumference", "waistbreadth", "waistdepth", "hipbreadth", "buttockdepth",
              "buttockcircumference", "waistheightomphalion", "buttockheight", "iliocristaleheight",
              "bicristalbreadth")


def _read_ansur(path: Path) -> list[dict]:
    with open(path, encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        try:
            out.append({k: float(r[k]) for k in ANSUR_KEYS})
        except (KeyError, ValueError):
            continue
    return out


def _slopes(r: dict) -> dict:
    dz = r["waistheightomphalion"] - r["buttockheight"]
    lat = (r["hipbreadth"] - r["waistbreadth"]) / 2.0 / dz
    post = (r["buttockdepth"] - r["waistdepth"]) / dz
    circ = (r["buttockcircumference"] - r["waistcircumference"]) / (2 * math.pi) / dz
    return {"tan_lat": lat, "tan_post": post, "cone_circ_deg": math.degrees(math.atan(circ)), "dz": dz}


def derive_anthro(male_csv: Path, female_csv: Path, out: Path = ANTHRO_YAML,
                  band_centres_in=(28, 30, 32, 34, 36, 38, 40, 42), half_band_in: float = 1.0) -> dict:
    """Hip forms (median subject per size band and sex) + population stats from the ANSUR II public CSVs."""
    data = {}
    for sex, path in (("male", male_csv), ("female", female_csv)):
        rows = _read_ansur(Path(path))
        for r in rows:
            r.update(_slopes(r))
        wc = np.array([r["waistcircumference"] for r in rows]) / IN
        cone = np.array([r["cone_circ_deg"] for r in rows])
        lat = np.degrees(np.arctan([r["tan_lat"] for r in rows]))
        post = np.degrees(np.arctan([r["tan_post"] for r in rows]))
        pct = lambda a: {f"p{q}": round(float(np.percentile(a, q)), 2) for q in (5, 25, 50, 75, 95)}  # noqa: E731
        forms = {}
        for c in band_centres_in:
            sel = [r for r in rows if abs(r["waistcircumference"] / IN - c) <= half_band_in]
            if len(sel) < 30:
                continue
            med = {k: round(float(np.median([r[k] for r in sel])), 1) for k in ANSUR_KEYS}
            med["tan_lat"] = round(float(np.median([r["tan_lat"] for r in sel])), 4)
            med["tan_post"] = round(float(np.median([r["tan_post"] for r in sel])), 4)
            med["n"] = len(sel)
            forms[f"{c}in"] = med
        data[sex] = {
            "n": len(rows),
            "waist_circ_in": pct(wc),
            "cone_circ_deg": pct(cone),
            "cone_lateral_deg": pct(lat),
            "cone_posterior_deg": pct(post),
            "forms": forms,
            "_wc_in": [round(float(x), 2) for x in np.sort(wc)],     # for coverage checks (sorted, anonymous)
        }
    doc = {
        "source": ("ANSUR II public release (US Army 2012 survey; Gordon et al. NATICK/TR-15/007, 2014), "
                   "ANSUR_II_MALE_Public.csv n 4082 and ANSUR_II_FEMALE_Public.csv n 1986 from "
                   "https://www.openlab.psu.edu/ansur2/ (tools.openlab.psu.edu/publicData/), downloaded 2026-11-08"),
        "method": ("forms = median of subjects with waist circumference (omphalion) within +/-1 in of the band centre; "
                   "slopes over waistheightomphalion - buttockheight; tan_post assumes all buttock-depth gain is "
                   "posterior (ASSUMPTION). Percentiles per sex, never pooled."),
        "generated_by": "huntkit/gendesign/hipbelt.py derive_anthro()",
        "male": data["male"], "female": data["female"],
    }
    out.write_text(yaml.safe_dump(doc, sort_keys=False, width=118))
    return doc


_ANTHRO = None


def anthro() -> dict:
    global _ANTHRO
    if _ANTHRO is None:
        _ANTHRO = yaml.safe_load(ANTHRO_YAML.read_text())
    return _ANTHRO


def coverage(ranges: dict, sex: str) -> float:
    """Share of the ANSUR II sex population whose waist circumference falls inside ANY size range (in)."""
    wc = np.array(anthro()[sex]["_wc_in"])
    ok = np.zeros(len(wc), bool)
    for lo, hi in ranges.values():
        ok |= (wc >= lo) & (wc <= hi)
    return float(ok.mean())


# ======================================================================================= hip form geometry
@dataclass(frozen=True)
class HipForm:
    name: str
    sex: str
    circ: float           # waist (crest-level) circumference, mm
    a0: float             # half waist breadth
    b0: float             # half waist depth (front and back halves equal at the waist, ASSUMPTION)
    tan_lat: float        # lateral widening per mm of drop
    tan_post: float       # posterior widening per mm of drop
    n: int = 0            # subjects in the band

    @property
    def circ_in(self) -> float:
        return self.circ / IN


def hip_form(sex: str, band_in: int, name: str | None = None) -> HipForm:
    f = anthro()[sex]["forms"][f"{band_in}in"]
    return HipForm(name or f"{sex[0].upper()}{band_in}", sex, f["waistcircumference"], f["waistbreadth"] / 2,
                   f["waistdepth"] / 2, f["tan_lat"], f["tan_post"], f["n"])


def _se_pts(a, bf, bb, ex, m=2001):
    """Superellipse section, t=0 at the back centre (+y = posterior), CCW seen from above."""
    t = np.linspace(-math.pi, math.pi, m)
    s, c = np.sin(t), np.cos(t)
    x = a * np.sign(s) * np.abs(s) ** (2 / ex)
    b = np.where(c >= 0, bb, bf)
    y = b * np.sign(c) * np.abs(c) ** (2 / ex)
    return t, np.column_stack([x, y])


def _perim(P):
    return float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))


def section_exponent(form: HipForm) -> float:
    """Superellipse exponent n whose perimeter equals the measured circumference (bisection, n in [1.6, 6])."""
    lo, hi = 1.6, 6.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if _perim(_se_pts(form.a0, form.b0, form.b0, mid)[1]) < form.circ:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass
class Section:
    """Half section (back centre -> front centre), resampled by arc length s from the back centre."""
    s: np.ndarray         # mm
    xy: np.ndarray        # points (x lateral +, y posterior +)
    nrm: np.ndarray       # outward unit normal
    kappa: np.ndarray     # curvature 1/mm (>= 0)
    tan_a: np.ndarray     # outward widening per mm of drop (cone slope) along the normal
    half_perim: float
    s_asis: float         # arc position of the ASIS (front face, x = ASIS_HALF_MM)
    s_crest: float        # arc position of the lateral extreme (x max): iliac crest region
    ex: float


def section(form: HipForm, z: float = 0.0, ds: float = 2.0) -> Section:
    """Body section at height z (mm, + up, 0 = crest/waist level) with local cone slope along the normal."""
    ex = section_exponent(form)

    def ring(zz):
        a = form.a0 - form.tan_lat * zz
        bb = form.b0 - form.tan_post * zz
        return _se_pts(a, form.b0, bb, ex)

    t, P = ring(z)
    _, P2 = ring(z - 10.0)
    half = t >= 0                                  # back centre (t=0) -> front centre (t=pi), x >= 0
    P, P2 = P[half], P2[half]
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    s = np.arange(0, seg[-1] + 1e-9, ds)
    xy = np.column_stack([np.interp(s, seg, P[:, 0]), np.interp(s, seg, P[:, 1])])
    xy2 = np.column_stack([np.interp(s, seg, P2[:, 0]), np.interp(s, seg, P2[:, 1])])
    d = np.gradient(xy, s, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.column_stack([-d[:, 1], d[:, 0]])     # CCW from back (+y) toward +x: outward is (-dy, dx)
    if np.dot(nrm[len(s) // 2], xy[len(s) // 2]) < 0:
        nrm = -nrm
    dd = np.gradient(d, s, axis=0)
    kappa = np.abs(d[:, 0] * dd[:, 1] - d[:, 1] * dd[:, 0])
    kappa = np.convolve(np.pad(kappa, 3, mode="edge"), np.ones(7) / 7, mode="valid")
    tan_a = np.einsum("ij,ij->i", xy2 - xy, nrm) / 10.0
    front = xy[:, 1] < 0
    idx = np.where(front & (xy[:, 0] <= ASIS_HALF_MM))[0]
    s_asis = float(s[idx[0]]) if len(idx) else float(s[-1])
    s_crest = float(s[int(np.argmax(xy[:, 0]))])
    return Section(s, xy, nrm, kappa, tan_a, float(s[-1]), s_asis, s_crest, ex)


# ======================================================================================= belt design
@dataclass(frozen=True)
class FoamLayer:
    material_id: str
    t: float              # mm

    @property
    def E_kpa(self) -> float:
        """Secant compression modulus to 25 % (record compression_25pct_kpa / 0.25)."""
        return load(self.material_id).require("compression_25pct_kpa") / 0.25


@dataclass(frozen=True)
class BeltDesign:
    key: str
    name: str
    lumbar_w: float = 140.0                 # lumbar pad / centre width on the body (build_geometry LUMBAR_CENTRE)
    lumbar_h: float = 140.0
    lumbar_foam: tuple = (FoamLayer("eva_foam_45c", 8.0), FoamLayer("eva_foam_45c", 8.0))
    lumbar_taper_tan: float | dict = 0.0    # pad thickness gradient (thicker at the top) fills the lumbar hollow; dict = per size
    wing_h: tuple = ((0.0, 140.0), (1.0, 95.0))       # (fraction root->tip, height mm)
    wing_foam: tuple = (FoamLayer("eva_foam_45c", 6.0), FoamLayer("eva_foam_30c", 5.0))
    crest_foam: tuple | None = None         # optional softer stack over the crest zone (dual density)
    stiff_mat: str | None = "hdpe_sheet"
    stiff_t: float = 1.0
    stiff_inset: float = 12.0               # stiffener inset from the wing edges (height and tip)
    stiff_to_tip: float = 1.0               # stiffener length as a fraction of the wing
    beta_deg: float | dict = 0.0            # pattern cone angle (0 = straight wing); dict = per size
    pad_fraction: float = 0.72              # padded length / hip circumference at the size centre
    sizes: dict = field(default_factory=lambda: dict(SIZES_CURRENT))
    top_tension_share: float = 0.5          # share of the wing tension in the top edge (0.5 = centred strap)
    pull_ma: float = 1.0                    # mechanical advantage of the tightening pull
    notes: str = ""

    def wing_len(self, size: str) -> float:
        lo, hi = self.sizes[size]
        return (self.pad_fraction * (lo + hi) / 2 * IN - self.lumbar_w) / 2

    def taper(self, size: str) -> float:
        t = self.lumbar_taper_tan
        return float(t[size]) if isinstance(t, dict) else float(t)

    def beta(self, size: str) -> float:
        return float(self.beta_deg[size]) if isinstance(self.beta_deg, dict) else float(self.beta_deg)

    def size_for(self, circ_in: float) -> str:
        best = None
        for k, (lo, hi) in self.sizes.items():
            if lo <= circ_in <= hi:
                d = abs(circ_in - (lo + hi) / 2)
                if best is None or d < best[0]:
                    best = (d, k)
        if best is None:
            return min(self.sizes, key=lambda k: abs(circ_in - sum(self.sizes[k]) / 2))
        return best[1]


def _k_stack(layers, tissue_h, tissue_e=TISSUE_E_KPA) -> float:
    """Winkler modulus (MPa/mm = N/mm^3) of foam layers + tissue column in series."""
    c = sum(L.t / (L.E_kpa / 1000.0) for L in layers) + tissue_h / (tissue_e / 1000.0)
    return 1.0 / c


def _across_height(q, h, k, delta):
    """Pressure across the height (u: -h/2 top ... +h/2 bottom) for line load q (N/mm), Winkler k and a linear
    interference gradient delta (+ = bottom presses harder). Returns (u, p MPa)."""
    u = np.linspace(-h / 2, h / 2, 41)
    if q <= 0:
        return u, np.zeros_like(u)
    d0 = q / (k * h)
    if abs(delta) * h / 2 <= d0:                       # full contact
        p = k * (d0 + delta * u)
    else:                                              # partial contact: triangle from the loaded edge
        c = math.sqrt(2 * q / (k * abs(delta)))
        edge = h / 2 if delta > 0 else -h / 2
        dist = np.abs(edge - u)
        p = np.where(dist <= c, k * abs(delta) * (c - dist), 0.0)
    return u, np.clip(p, 0, None)


@dataclass
class BeltResult:
    design: str
    form: str
    size: str
    T: float
    s: np.ndarray                 # half-belt stations (arc from back centre)
    u: np.ndarray
    p: np.ndarray                 # kPa, shape (len(s), len(u))
    h: np.ndarray
    zone: np.ndarray              # 0 lumbar, 1 wing, 2 crest zone
    V_cap: float                  # N (whole belt)
    s_tip: float
    sec: Section
    extra: dict


def evaluate(design: BeltDesign, form: HipForm, T: float, size: str | None = None, torso_in: int = 19,
             g: float = 1.0, mu: float = MU, tissue_e: float = TISSUE_E_KPA, cg_aft: float = CG_AFT_MM) -> BeltResult:
    """Pressure field and vertical holding capacity of one belt on one hip form at wing tension T (N)."""
    sec = section(form)
    size = size or design.size_for(form.circ_in)
    s_root = design.lumbar_w / 2
    s_tip = s_root + design.wing_len(size)
    sel = sec.s <= s_tip
    s = sec.s[sel]
    kap, tan_a = sec.kappa[sel], sec.tan_a[sel]
    r = 1.0 / np.maximum(kap, 1e-4)
    frac = np.clip((s - s_root) / max(s_tip - s_root, 1e-6), 0, 1)
    fh, hh = zip(*design.wing_h)
    h_w = np.interp(frac, fh, hh)
    lumbar = s <= s_root
    crest = (np.abs(s - sec.s_crest) <= 45.0) & ~lumbar
    zone = np.where(lumbar, 0, np.where(crest, 2, 1))
    h = np.where(lumbar, design.lumbar_h, h_w)
    # pack overturning couple -> lumbar push (whole belt), spread over the lumbar width
    W = RATED_KG * G * g
    lever = YOKE_Z[torso_in] - LUMBAR_Z
    H = W * cg_aft / lever
    q = T * kap + np.where(lumbar, H / design.lumbar_w, 0.0)
    # stiffness and generator mismatch
    k = np.empty_like(s)
    keff_h = np.empty_like(s)
    dlt = np.empty_like(s)
    tb = math.tan(math.radians(design.beta(size)))
    if design.stiff_mat:
        Es = load(design.stiff_mat).require("youngs_modulus_mpa")
    for i in range(len(s)):
        if lumbar[i]:
            k[i] = _k_stack(design.lumbar_foam, TISSUE_H_SOFT, tissue_e)
            # rigid centre plate: no pitch freedom (the pivot only rolls); a tapered pad removes mismatch
            dlt[i] = tan_a[i] - design.taper(size)
            keff_h[i] = design.lumbar_h
            continue
        layers = design.crest_foam if (crest[i] and design.crest_foam) else design.wing_foam
        k[i] = _k_stack(layers, TISSUE_H_CREST if crest[i] else TISSUE_H_SOFT, tissue_e)
        t_f = sum(L.t for L in layers)
        stiff_here = design.stiff_mat and frac[i] <= design.stiff_to_tip - design.stiff_inset / max(s_tip - s_root, 1)
        if stiff_here:
            hs = max(h[i] - 2 * design.stiff_inset, 0.0)
            kh = Es * design.stiff_t * (hs / h[i]) / r[i] ** 2
            keff_h[i] = min(h[i], hs + 2 * t_f)
        else:
            kh = 30.0 / r[i] ** 2               # ASSUMPTION: shell + binding hoop stiffness E t ~ 30 N/mm
            keff_h[i] = min(h[i], 0.6 * h[i] + 2 * t_f)
        rem = kh / (k[i] + kh)                   # share of the cone mismatch the band cannot rotate away
        d = (tan_a[i] - tb) * rem
        # top/bottom tension split: moment per length (T_top - T_bot) kappa * (0.35 h) -> equivalent gradient
        m = (2 * design.top_tension_share - 1) * T * kap[i] * 0.35 * h[i]
        d -= m / ((k[i] + kh) * h[i] ** 3 / 12.0)
        dlt[i] = d
    P = np.zeros((len(s), 41))
    u = None
    for i in range(len(s)):
        uu, pp = _across_height(q[i], keff_h[i], k[i], dlt[i])
        # map the effective band back onto the full height grid (centred)
        u_full = np.linspace(-h[i] / 2, h[i] / 2, 41)
        P[i] = np.interp(u_full, uu, pp, left=0.0, right=0.0)
        if u is None:
            u = np.linspace(-0.5, 0.5, 41)
    # vertical capacity (whole belt = 2 x half), wedge + friction per element
    ta = np.clip(tan_a, -0.2, 0.8)
    wedge = (ta + mu) / (1 - mu * ta)
    ds = np.gradient(s)
    du = h / 40.0
    N_line = P.sum(axis=1) * du                  # N/mm along s
    V_cap = 2.0 * float(np.sum(N_line * wedge * ds))
    return BeltResult(design.key, form.name, size, T, s, u, P * 1000.0, h, zone, V_cap, s_tip, sec,
                      {"H_lumbar": H, "lever": lever, "k": k, "delta": dlt, "keff_h": keff_h,
                       "asis_clear": sec.s_asis - s_tip, "pad_len_mm": 2 * s_tip,
                       "pad_frac": 2 * s_tip / form.circ})


def metrics(res: BeltResult) -> dict:
    p = res.p
    ds = np.gradient(res.s)
    dA = (res.h / 40.0)[:, None] * ds[:, None] * np.ones_like(p)
    on = p > 0.5
    area = 2.0 * float(dA[on].sum())                           # mm^2, whole belt
    mean = float((p * dA)[on].sum() / max(dA[on].sum(), 1e-9))
    wing = res.zone > 0
    crest = res.zone == 2
    top = res.u[None, :] < -0.25                                # top quarter of the belt height
    crest_top = float(p[crest][:, top[0]].max()) if crest.any() else 0.0
    def _pk(mask):
        return float(p[mask].max()) if mask.any() else 0.0
    return {"peak_kpa": round(float(p.max()), 1), "mean_kpa": round(mean, 1), "area_cm2": round(area / 100, 0),
            "peak_wing_kpa": round(_pk(wing), 1), "peak_lumbar_kpa": round(_pk(res.zone == 0), 1),
            "peak_crest_top_kpa": round(crest_top, 1), "V_cap_n": round(res.V_cap, 0),
            "asis_clear_mm": round(res.extra["asis_clear"], 0), "pad_frac": round(res.extra["pad_frac"], 3)}


def tension_for_hold(design: BeltDesign, form: HipForm, g_hold: float = WALK_G, margin: float = 1.0,
                     **kw) -> float:
    """Wing tension (N) at which the belt holds HIP_SHARE x 68 kg x g_hold without slip (V_cap is linear in T;
    the lumbar couple is evaluated at 1 g: the pack moment and the vertical load rise together in a step,
    so holding the ratio at 1 g x margin is the same check)."""
    need = margin * HIP_SHARE * RATED_KG * G * g_hold
    kw1 = {k: v for k, v in kw.items() if k != "g"}
    v0 = evaluate(design, form, 0.0, g=g_hold, **kw1).V_cap
    v1 = evaluate(design, form, 100.0, g=g_hold, **kw1).V_cap
    slope = (v1 - v0) / 100.0
    return max((need - v0) / slope, 0.0) if slope > 0 else float("inf")


def tension_allow(design: BeltDesign, form: HipForm, **kw) -> float:
    """Highest wing tension at which wing peak <= P_HIP_PEAK, crest-top <= P_BONY and mean <= P_OCCLUSION."""
    lo, hi = 0.0, 600.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        m = metrics(evaluate(design, form, mid, **kw))
        ok = (m["peak_wing_kpa"] <= P_HIP_PEAK_KPA and m["peak_crest_top_kpa"] <= P_BONY_KPA
              and m["mean_kpa"] <= P_OCCLUSION_KPA)
        lo, hi = (mid, hi) if ok else (lo, mid)
    return lo


def study(design: BeltDesign, form: HipForm, **kw) -> dict:
    """Full comparison row: tension to hold at the walking peak, pressures there (1 g sustained), and the
    pressure-limited hold."""
    T_req = tension_for_hold(design, form, **kw)
    res = evaluate(design, form, T_req, **kw)
    m = metrics(res)
    T_ok = tension_allow(design, form, **kw)
    v_ok = evaluate(design, form, T_ok, g=WALK_G, **{k: v for k, v in kw.items() if k != "g"}).V_cap
    need = HIP_SHARE * RATED_KG * G * WALK_G
    return {"design": design.key, "form": form.name, "sex": form.sex, "circ_in": round(form.circ_in, 1),
            "size": res.size, "T_req_n": round(T_req, 0), "pull_n": round(T_req / design.pull_ma / (0.85 if design.pull_ma > 1 else 1.0), 0),
            **m, "T_allow_n": round(T_ok, 0), "hold_margin_at_allow": round(v_ok / need, 2)}


# ======================================================================================= 3D band + flat pattern
def wing_edges(design: BeltDesign, form: HipForm, size: str, offset: float | None = None, n: int = 80):
    """3D top and bottom edge curves of the RIGHT wing (x >= 0) from the wing root to the tip, on a cone of the
    pattern angle beta laid over the body section at crest level, offset outward by ``offset`` (default: half the
    wing foam stack). Generators lean inward going up by beta. Returns (centre, top, bottom, s) in body coordinates
    (x lateral, y posterior, z up; z = 0 at the crest)."""
    sec = section(form)
    t_f = sum(L.t for L in design.wing_foam)
    off = t_f / 2 if offset is None else offset
    s_root = design.lumbar_w / 2
    s_tip = s_root + design.wing_len(size)
    s = np.linspace(s_root, min(s_tip, sec.s[-1]), n)
    cx = np.interp(s, sec.s, sec.xy[:, 0])
    cy = np.interp(s, sec.s, sec.xy[:, 1])
    nx = np.interp(s, sec.s, sec.nrm[:, 0])
    ny = np.interp(s, sec.s, sec.nrm[:, 1])
    nn = np.hypot(nx, ny)
    nx, ny = nx / nn, ny / nn
    C = np.column_stack([cx + off * nx, cy + off * ny, np.zeros(n)])
    b = math.radians(design.beta(size))
    gen = np.column_stack([-math.sin(b) * nx, -math.sin(b) * ny, np.full(n, math.cos(b))])
    frac = (s - s_root) / max(s_tip - s_root, 1e-6)
    fh, hh = zip(*design.wing_h)
    h = np.interp(frac, fh, hh)
    top = C + gen * (h / 2)[:, None]
    bot = C - gen * (h / 2)[:, None]
    return C, top, bot, s


def wing_flat(design: BeltDesign, form: HipForm, size: str, n: int = 80):
    """Developed (flat) seam outline of the right wing: top edge, bottom edge (2D, mm) + max developability strain.
    Root at x = 0, the wing runs toward +x; the top edge is ABOVE (y +)."""
    from huntkit.patterns.geometry import develop_ruled_surface
    _, top, bot, _ = wing_edges(design, form, size, n=n)
    dev = develop_ruled_surface(bot, top, n=n, resample=False)
    B, T = dev.edge_a.copy(), dev.edge_b.copy()
    if T[:, 1].mean() < B[:, 1].mean():
        B[:, 1] *= -1
        T[:, 1] *= -1
    o = 0.5 * (B[0] + T[0])
    B -= o
    T -= o
    c_end = 0.5 * (B[-1] + T[-1])
    ang = -math.atan2(c_end[1], c_end[0])            # centreline chord along +x
    R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
    B, T = B @ R.T, T @ R.T
    if T[:, 1].mean() < B[:, 1].mean():
        B[:, 1] *= -1
        T[:, 1] *= -1
    return T, B, dev.max_strain


def flat_sagitta(top: np.ndarray, bot: np.ndarray) -> float:
    """Bow of the developed wing centreline off its chord (mm): ~0 for a straight wing, > 0 for a cone cut."""
    c = 0.5 * (top + bot)
    d = c[-1] - c[0]
    L = np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]]) / L
    return float(np.max(np.abs((c - c[0]) @ nrm)))


# ======================================================================================= mass helpers
def piece_mass_g(material_id: str, area_mm2: float, t_mm: float | None = None) -> float:
    m = load(material_id)
    gsm = m.get("areal_density_gsm")
    if gsm:
        return gsm * area_mm2 / 1e6
    rho = m.require("density_kg_m3")
    return rho * area_mm2 * 1e-9 * t_mm * 1000.0


if __name__ == "__main__":     # pragma: no cover
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "--anthro":
        d = derive_anthro(Path(sys.argv[2]), Path(sys.argv[3]))
        print({s: list(d[s]["forms"]) for s in ("male", "female")})
