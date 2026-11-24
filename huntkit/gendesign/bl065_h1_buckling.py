"""BL-065: linear eigenvalue buckling of the released H1 print (and a side-squeeze case), against the record rule.

Body: ``print/frame_h1/h1_assembled.stl`` (md5-locked, ``frame_iter1.baseline_solid``) on the H1 2 mm grid, PAHT-CF at
the buckling modulus of the record rule (E_xy 3860 x 0.6 hot x 0.7 creep = 1621 MPa, ``frame_iter1.E_BUCKLE``).
Loads: the BL-058 whole-body sets (HA-LS-1 rev C, lane kit sets, real crown models: ``frame_iter1._ctx``) on the four
bases fine_sm8 / fine / beam / fine_sm8.cyc, each set already carrying its case factor. Requirement (HA-LS-1 4):
buckling eigenvalue >= 1.5 x case factor, i.e. **margin = lam / 1.5 >= 1** with lam the multiplier on the factored set
(the record rule's margin P_cr / (1.5 P) on the same footing).

Solver: ``huntkit.fea.voxel_buckling`` (H8 initial-stress stiffness, Lanczos; verified against Euler in
``tests/test_voxel_buckling.py``). Prestress = the record's own solve (hip-boss clamp, every other support a dead load).

Three readings per set (ASSUMPTION BRACE-TOP / DEAD-LOAD below):
- ``free``: the record's support as is. Its lowest modes are rigid-ish pitch / sway / yaw of the whole frame on the
  32 mm boss clamp, because the load sets fold the wearer (shoulder harness, back, crown bar) into dead loads.
- ``braced``: the stay tops (z >= 526, the crown bushing band) held in x and y in the eigen problem only: the crown bar
  ties both stays and the shoulder harness / lifters hold it to the wearer (the T1 rig does the same). This is the
  frame reading.
- ``member``: K_sigma kept only in one member (branch, mid bar), the rest of the frame acting as its stress-free elastic
  end restraint; unbraced (stay tops free: conservative) and braced. Gives the member's real P_cr and its effective
  length factor K_eff = sqrt(pi^2 E I_min / P_cr) / L against the record rule's L.

Run: ``python -m huntkit.gendesign.bl065_h1_buckling [run | fix | report]``. Record:
``designs/pack_5200/analysis/bl065.{json,md}``; bl058.json gets a ``bl065_eigen`` block (code only).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from . import frame_iter1 as FI

REPO = FI.REPO
PACK = FI.PACK
ANA = PACK / "analysis"
OUT = REPO / "outputs" / "bl065"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261124_bl065_"
REC_JSON = ANA / "bl065.json"
REC_MD = ANA / "bl065.md"
BL058 = ANA / "bl058.json"
H = FI.H
E_B = FI.E_BUCKLE                                    # 1621.2 MPa
REQ = 1.5                                            # HA-LS-1: eigenvalue >= 1.5 x case factor
BONUS = 1.15                                         # BL-061 rubric bonus on buckling
BASES = FI.BASES
BRACE_Z = 526.0                                      # stay-top band held in the braced reading (crown bushing band)
HINGE = (115.0, 10.9, 60.0)                          # geometry.yaml bag_anchor_low_R (hinge pin axis along x)
SQUEEZE_1G = 208.0                                   # N per side, h1_buckling.md 2.1 (largest converged meat run, 1 g)
SQUEEZE_FACTOR = 2.0                                 # HA-LS-1 static factor (largest case factor)
H8_STIFF = 1.02                                      # tests/test_voxel_buckling: 2 mm H8 reads +2 % on a 12 mm depth
K_TOP = 6                                            # modes per braced run
N_SCREEN = 3                                         # extra sets per basis picked by the Rayleigh screen

ASSUMPTIONS = {
    "DEAD-LOAD": ("The load sets' forces are dead loads (fixed direction) and the hip boss is the only support, as in "
                  "the record solve. Body, harness and crown reactions do not follow the deformed frame.",
                  "Conservative for members; makes the 'free' reading's global modes artefacts (see BRACE-TOP)."),
    "BRACE-TOP": ("The crown bar and the shoulder harness hold the stay tops (z >= 526) in x and y against buckling "
                  "motion, carrying no load in the reference state (eigen problem only).",
                  "T1 rig (shoulder straps ratcheted, hipbelt on the log) and the side-squeeze test: no sway at the "
                  "crown before the member readings are reached."),
    "H8-STIFF": ("Full-integration H8 voxels are 2 % stiff in bending at 2 mm on a 12 mm depth (verified on a 16 x 12 x "
                 "180 column: cantilever 1.020, pinned 1.002, 1 mm 1.006); every eigen margin here is divided by "
                 "1.02.", "tests/test_voxel_buckling.py"),
    "CENTROID-STRESS": ("K_sigma uses each voxel's centroid stress (constant per element), the stress the record "
                        "check uses.", "Standard for linear bricks; converges with the grid."),
    "SQUEEZE": ("Side-squeeze case: the hinge pins pull each stay foot inboard by 208 N at 1 g (largest converged "
                "meat run, h1_buckling.md 2.1) x 2.0 (static factor, the largest HA-LS-1 case factor) = 416 N a side, "
                "spread over the eye nodes within 7 mm of the pin axis, alone (every other load off).",
                "T1 side-squeeze test: 1.5 x 416 = 624 N a side with no buckle."),
    "SCREEN": ("Sets not run in full are ranked by the Rayleigh quotient of the braced modes from the governing "
               "sets; the 3 lowest per basis are run in full. A set with a lower first eigenvalue whose mode is "
               "unlike every trial mode could be missed.", "Optional: all-set run (about 6 h)."),
    "FOOT-GROUND": ("In single-stay set-down the loaded foot stands on the ground: its sole nodes (z <= 4) are held in "
                    "x and y in the eigen problem (friction 0.2 x the impact load is far above any buckling "
                    "perturbation); the record's inertia-relief hip clamp stays.",
                    "T4b set-down drop test."),
    "SLIVER": ("The bridge lip under the spine-channel opening (upper bar underside z 496-498, 3.7 x ~2 mm in the STL, "
               "one voxel layer) is a local, non-load-path detail: its buckle is reported on its own and the frame "
               "reading is taken with it deleted (which removes material, so it is conservative for the rest).",
               "Look at the printed lip after the T1 hipbelt-off variant; trim it in the next CAD revision."),
    "SAND": ("The stays' sanding factor (k 1.0416, a strength rule) is not applied: it changes no member stiffness.",
             "-"),
}


# ================================================================================================ body / masks
def body() -> dict:
    c = FI._base()
    solid = FI.baseline_solid()
    return {"c": c, "dom": c["dom"], "g": c["dom"].grid, "cen": c["cen"], "grp": c["grp"], "solid": solid}


def member_masks(b: dict, solid: np.ndarray | None = None) -> dict:
    from . import frame_comp_A as A
    s = b["solid"] if solid is None else solid
    cen, grp = b["cen"], b["grp"]
    br = s & (grp == A.GROUPS.index("branch"))
    up = br & (cen[:, 2] > 330.0)
    lo = br & (cen[:, 2] <= 330.0) & (cen[:, 2] > 165.0)
    return {"upper branch R": up & (cen[:, 0] > 0), "upper branch L": up & (cen[:, 0] < 0),
            "lower branch R": lo & (cen[:, 0] > 0), "lower branch L": lo & (cen[:, 0] < 0),
            "mid bar": s & (grp == A.GROUPS.index("mid"))}


CUT_OF = {"upper branch R": ("branch upper (z 330-495)", "R"), "upper branch L": ("branch upper (z 330-495)", "L"),
          "lower branch R": ("branch lower (z 165-330)", "R"), "lower branch L": ("branch lower (z 165-330)", "L"),
          "mid bar": ("mid bar (x -115..115)", "all")}


def region_of(cen: np.ndarray, grp: np.ndarray) -> np.ndarray:
    """Short region name per element (for mode shares)."""
    from . import frame_comp_A as A
    out = np.empty(len(cen), object)
    side = np.where(cen[:, 0] > 0, "R", "L")
    for i, gname in enumerate(A.GROUPS):
        m = grp == i
        if gname == "branch":
            up = cen[:, 2] > 330.0
            out[m & up] = np.char.add("upper branch ", side[m & up].astype(str))
            out[m & ~up] = np.char.add("lower branch ", side[m & ~up].astype(str))
        elif gname == "mid":
            out[m] = "mid bar"
        elif gname == "strut":
            out[m] = np.char.add("lumbar strut ", side[m].astype(str))
        else:
            nm = {"foot": "stay foot", "low": "stay lower", "sleeve": "stay sleeve", "top": "stay top"}[gname]
            out[m] = np.char.add(nm + " ", side[m].astype(str))
    out[out == None] = "other"  # noqa: E711
    return out


def brace_dofs(b: dict, solid: np.ndarray | None = None) -> np.ndarray:
    s = b["solid"] if solid is None else solid
    g = b["g"]
    nc = g.node_coords()
    act = np.zeros(g.nn, bool)
    act[np.unique(g.enodes[s])] = True
    n = np.where(act & (np.abs(nc[:, 0]) > 90.0) & (nc[:, 2] >= BRACE_Z))[0]
    out = np.zeros(g.ndof, bool)
    for d in (0, 1):
        out[3 * n + d] = True
    return out


def squeeze_F(b: dict, Q: float, solid: np.ndarray | None = None) -> np.ndarray:
    """Inboard x force Q per side spread over the hinge-eye nodes (pin axis along x at y 10.9, z 60, |x| 95..135)."""
    s = b["solid"] if solid is None else solid
    g = b["g"]
    nc = g.node_coords()
    act = np.zeros(g.nn, bool)
    act[np.unique(g.enodes[s])] = True
    F = np.zeros(g.ndof)
    for sg in (1, -1):
        m = act & (np.hypot(nc[:, 1] - HINGE[1], nc[:, 2] - HINGE[2]) <= 7.0) & (sg * nc[:, 0] >= 95.0) \
            & (sg * nc[:, 0] <= 135.0)
        n = np.where(m)[0]
        if n.size == 0:
            raise RuntimeError("no hinge-eye nodes found")
        F[3 * n] = -sg * Q / n.size
    return F


# ================================================================================================ record rule
def cut_rows(b: dict, ae: np.ndarray, S: np.ndarray) -> dict:
    """Record rule (team A) and section rule per member cut, from one prestress (active order)."""
    from . import frame_comp_A as A
    cen = b["g"].elem_centers()[ae]
    grp = b["grp"][ae]
    out = {}
    for name, (gname, ax, cc, L) in A.BUCKLE_CUTS.items():
        lay = (grp == A.GROUPS.index(gname)) & (np.abs(cen[:, ax] - (cc + H / 2)) <= H / 2 + 1e-6)
        sides = {"all": lay} if ax == 0 else {"L": lay & (cen[:, 0] < 0), "R": lay & (cen[:, 0] > 0)}
        for sd, m in sides.items():
            o = [i for i in range(3) if i != ax]
            sp = FI.section_props(cen[m][:, o[0]], cen[m][:, o[1]], np.ones(int(m.sum())))
            P = -float(S[m, ax].sum() * H * H)
            pr = FI.euler_pcr(E_B, sp["A"] ** 2 / (4 * math.pi), L)
            ps = FI.euler_pcr(E_B, sp["Imin"], L)
            out[f"{name} {sd}"] = {"P": P, "A": sp["A"], "I_min": sp["Imin"], "L": L, "Pcr_record": pr,
                                   "Pcr_section": ps}
    return out


# ================================================================================================ mode description
def describe(vb, S: np.ndarray, modes: np.ndarray, lam: np.ndarray, regions: np.ndarray, kg_weight=None) -> list:
    from huntkit.fea.voxel_buckling import geometric_energy
    g = vb.g
    cen = g.elem_centers()[vb.ae]
    Sk = S if kg_weight is None else S * np.asarray(kg_weight, float)[vb.ae][:, None]
    nc = g.node_coords()
    out = []
    for j in range(len(lam)):
        if not np.isfinite(lam[j]):
            continue
        en = geometric_energy(vb.rs, Sk, modes[:, j], g.h)
        tot = en.sum()
        en = en / tot if tot != 0 else en
        sh = {}
        for r in np.unique(regions):
            v = float(en[regions == r].sum())
            if v > 0.05:
                sh[str(r)] = round(v, 2)
        ph = modes[:, j].reshape(-1, 3)
        a = np.linalg.norm(ph, axis=1)
        k = int(np.argmax(a))
        top = (nc[:, 2] > 480.0) & (np.abs(nc[:, 0]) > 90.0) & (a > 0)
        lead = max(sh, key=sh.get) if sh else "?"
        out.append({"lam": float(lam[j]), "margin": float(lam[j] / REQ / H8_STIFF),
                    "drives": dict(sorted(sh.items(), key=lambda kv: -kv[1])), "lead": lead,
                    "driver_peak_mm": [float(v) for v in cen[int(np.argmax(en))]],
                    "max_disp_at_mm": [float(v) for v in nc[k]],
                    "top_disp_share": float((a[top] ** 2).sum() / (a ** 2).sum())})
    return out


def rayleigh(trials: list, S: np.ndarray) -> float:
    """Lowest Rayleigh estimate of lam over trial modes: trials = [(q (n, 6) from mode_q, phi^T K phi)]."""
    best = np.inf
    for q, kk in trials:
        d = -float((q * S).sum())
        if d > 0:
            best = min(best, E_B * kk / d)
    return best


# ================================================================================================ one basis
def _sets(basis: str):
    from . import h1_sleeve as S
    b, cyc = basis.split(".")[0], basis.endswith(".cyc")
    return S.kit_sets(b, cycled=cyc)


def run_basis(basis: str, b: dict | None = None, solid: np.ndarray | None = None, tag: str = "h1", log=print,
              refresh: bool = False, members_only: bool = False) -> dict:
    """All readings on one basis, cached OUT/<tag>_<basis>.json."""
    from huntkit.fea.voxel_buckling import VoxelBuckler, mode_q, sym_full
    from . import frame_topopt as ft
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{tag}_{basis}.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    b = b or body()
    solid = b["solid"] if solid is None else solid
    dom, g = b["dom"], b["g"]
    t0 = time.time()
    with FI._ctx():
        sets = _sets(basis)
        _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
        vb = VoxelBuckler(g, solid, fixed, ft.NU, extra_fixed=brace_dofs(b, solid))
        log(f"[{time.strftime('%H:%M:%S')}] {tag} {basis}: {len(sets)} sets, system {vb.rs.n} dof "
            f"({time.time() - t0:.0f} s)")
        stress, keys = [], []
        tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
        for tg in tags:
            ts = [s for s in sets if s.key.split(":")[0] == tg]
            F, _ = ft.assemble_loads(dom, ts, solid_mask=solid)
            for s_, S in zip(ts, vb.prestress(F)):
                stress.append(S.astype(np.float32))
                keys.append(s_.key)
            del F
    regions = region_of(g.elem_centers()[vb.ae], b["grp"][vb.ae])
    log(f"   prestress {len(keys)} sets ({time.time() - t0:.0f} s)")
    # record rule on every set: governing set per member
    rec = {}
    for k, S in zip(keys, stress):
        for nm, r in cut_rows(b, vb.ae, S).items():
            if r["P"] <= 0:
                continue
            m = r["Pcr_record"] / (REQ * r["P"])
            if nm not in rec or m < rec[nm]["margin_record"]:
                rec[nm] = {**r, "set": k, "margin_record": m, "margin_section": r["Pcr_section"] / (REQ * r["P"])}
    res = {"basis": basis, "tag": tag, "n_sets": len(keys), "record_rule": rec, "full": {}, "members": {}}
    idx = {k: i for i, k in enumerate(keys)}
    mm = member_masks(b, solid)
    # member-isolated, unbraced and braced, on each member's governing set
    for mem, (cut, sd) in CUT_OF.items():
        row = rec.get(f"{cut} {sd}")
        if row is None:
            continue
        S = stress[idx[row["set"]]].astype(float)
        kw = mm[mem].astype(float)
        out = {"set": row["set"], "P_n": row["P"], "I_min_mm4": row["I_min"], "L_mm": row["L"],
               "margin_record": row["margin_record"], "margin_section": row["margin_section"]}
        for rd, br in (("unbraced", False), ("braced", True)):
            lam, modes = vb.eig(S, E_B, 2, kw, braced=br)
            d = describe(vb if br else vb.unbraced(), S, modes, lam, regions, kw)[0]
            pcr = d["lam"] / H8_STIFF * row["P"]
            out[rd] = {"lam": d["lam"], "margin": d["margin"], "Pcr_n": pcr,
                       "K_eff": math.sqrt(math.pi ** 2 * E_B * row["I_min"] / pcr) / row["L"],
                       "K_eff_round": math.sqrt(math.pi ** 2 * E_B * (row["A"] ** 2 / (4 * math.pi)) / pcr) / row["L"],
                       "max_disp_at_mm": d["max_disp_at_mm"]}
        res["members"][mem] = out
        log(f"   member {mem}: rec {out['margin_record']:.3f} sec {out['margin_section']:.3f} eig unbraced "
            f"{out['unbraced']['margin']:.3f} (K {out['unbraced']['K_eff']:.2f}) braced {out['braced']['margin']:.3f} "
            f"({time.time() - t0:.0f} s)")
    if not members_only:
        gov = list(dict.fromkeys(r["set"] for r in rec.values()))
        trials = []
        Kf = sym_full(vb.K)
        for k in gov:
            lam, modes = vb.eig(stress[idx[k]].astype(float), E_B, K_TOP)
            res["full"][k] = {"why": "record-governing", "modes": describe(vb, stress[idx[k]].astype(float), modes, lam,
                                                                            regions)}
            for j in range(modes.shape[1]):
                ph = modes[vb.rs.free, j]
                trials.append((mode_q(vb.rs, modes[:, j], H).astype(np.float32), float(ph @ (Kf @ ph))))
            log(f"   full braced {k}: {res['full'][k]['modes'][0]['margin']:.3f} "
                f"{res['full'][k]['modes'][0]['lead']} ({time.time() - t0:.0f} s)")
        scr = {k: rayleigh(trials, stress[idx[k]]) for k in keys if k not in res["full"]}
        res["screen"] = {k: (v / REQ / H8_STIFF if np.isfinite(v) else None) for k, v in scr.items()}
        for k in sorted(scr, key=scr.get)[:N_SCREEN]:
            lam, modes = vb.eig(stress[idx[k]].astype(float), E_B, K_TOP)
            res["full"][k] = {"why": "screened", "rayleigh_margin": scr[k] / REQ / H8_STIFF,
                              "modes": describe(vb, stress[idx[k]].astype(float), modes, lam, regions)}
            log(f"   full braced {k} (screen {scr[k] / REQ / H8_STIFF:.3f}): "
                f"{res['full'][k]['modes'][0]['margin']:.3f} {res['full'][k]['modes'][0]['lead']} "
                f"({time.time() - t0:.0f} s)")
        # the record model as is (free) on the set that governs the record rule
        gk = min(rec.values(), key=lambda r: r["margin_record"])["set"]
        lam, modes = vb.eig(stress[idx[gk]].astype(float), E_B, 4, braced=False)
        res["free"] = {"set": gk, "modes": describe(vb.unbraced(), stress[idx[gk]].astype(float), modes, lam, regions)}
        np.savez_compressed(OUT / f"{tag}_{basis}_freemode.npz", mode=modes[:, 0].astype(np.float32))
        # braced governing mode shape for the figure
        fk = min(res["full"], key=lambda k: res["full"][k]["modes"][0]["margin"])
        lam, modes = vb.eig(stress[idx[fk]].astype(float), E_B, 1)
        np.savez_compressed(OUT / f"{tag}_{basis}_mode.npz", mode=modes[:, 0].astype(np.float32), set=fk)
        res["braced_min"] = {"set": fk, **res["full"][fk]["modes"][0]}
        res["free_min"] = {"set": gk, **res["free"]["modes"][0]}
    res["seconds"] = round(time.time() - t0)
    vb.free()
    p.write_text(json.dumps(res, default=FI._jd))
    return res


def run_squeeze(b: dict | None = None, solid: np.ndarray | None = None, tag: str = "h1", log=print,
                refresh: bool = False) -> dict:
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    p = OUT / f"{tag}_squeeze.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    b = b or body()
    solid = b["solid"] if solid is None else solid
    dom, g = b["dom"], b["g"]
    with FI._ctx():
        sets = _sets("fine")
        _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    Q = SQUEEZE_1G * SQUEEZE_FACTOR
    vb = VoxelBuckler(g, solid, fixed, ft.NU, extra_fixed=brace_dofs(b, solid))
    S = vb.prestress(squeeze_F(b, Q, solid))[0]
    regions = region_of(g.elem_centers()[vb.ae], b["grp"][vb.ae])
    res = {"Q_per_side_n": Q, "cuts": {k: v["P"] for k, v in cut_rows(b, vb.ae, S).items()}}
    for rd, br in (("braced", True), ("free", False)):
        lam, modes = vb.eig(S, E_B, 4, braced=br)
        res[rd] = describe(vb if br else vb.unbraced(), S, modes, lam, regions)
        res[rd + "_bifurcation_n_per_side"] = res[rd][0]["lam"] / H8_STIFF * Q
        if br:
            np.savez_compressed(OUT / f"{tag}_squeeze_mode.npz", mode=modes[:, 0].astype(np.float32))
    vb.free()
    log(f"   squeeze {Q:.0f} N/side: braced {res['braced'][0]['margin']:.2f} ({res['braced'][0]['lead']}), free "
        f"{res['free'][0]['margin']:.2f} ({res['free'][0]['lead']})")
    p.write_text(json.dumps(res, default=FI._jd))
    return res


def foot_dofs(b: dict, side: str, solid: np.ndarray | None = None) -> np.ndarray:
    """x, y of the stay-foot sole nodes (z <= 4) on one side: the ground under a set-down foot (ASSUMPTION
    FOOT-GROUND)."""
    s = b["solid"] if solid is None else solid
    g = b["g"]
    nc = g.node_coords()
    act = np.zeros(g.nn, bool)
    act[np.unique(g.enodes[s])] = True
    sg = 1.0 if side == "R" else -1.0
    n = np.where(act & (nc[:, 2] <= 4.0 + 1e-6) & (sg * nc[:, 0] > 60.0))[0]
    out = np.zeros(g.ndof, bool)
    for d in (0, 1):
        out[3 * n + d] = True
    return out


def setdown_side(F: np.ndarray, g) -> str:
    nc = g.node_coords()
    Fz = F[2::3]
    m = nc[:, 2] < 20.0
    return "R" if Fz[m & (nc[:, 0] > 0)].sum() > Fz[m & (nc[:, 0] < 0)].sum() else "L"


def run_setdown(basis: str, b: dict | None = None, solid: np.ndarray | None = None, tag: str = "h1", log=print,
                refresh: bool = False, n: int = 1) -> dict:
    """Single-stay set-down with the loaded foot on the ground (held in x, y in the eigen problem), with and
    without the crown brace, on the record-governing set-down set and the n lowest screened set-down sets."""
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    p = OUT / f"{tag}_{basis}_setdown.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    base = json.loads((OUT / f"{tag}_{basis}.json").read_text())
    b = b or body()
    solid = b["solid"] if solid is None else solid
    dom, g = b["dom"], b["g"]
    cand = [k for k in base["full"] if "single_stay_setdown" in k]
    scr = sorted(((v, k) for k, v in base.get("screen", {}).items() if v is not None and "single_stay_setdown" in k))
    cand += [k for _, k in scr if k not in cand][:n]
    cand = cand[: n + 1]
    res = {"basis": basis, "sets": {}}
    if not cand:
        p.write_text(json.dumps(res))
        return res
    t0 = time.time()
    with FI._ctx():
        sets = {s_.key: s_ for s_ in _sets(basis)}
        _, fixed = ft.assemble_loads(dom, [sets[cand[0]]], solid_mask=solid)
        vb = VoxelBuckler(g, solid, fixed, ft.NU)
        regions = region_of(g.elem_centers()[vb.ae], b["grp"][vb.ae])
        top = brace_dofs(b, solid)
        for k in cand:
            F, _ = ft.assemble_loads(dom, [sets[k]], solid_mask=solid)
            side = setdown_side(F[:, 0], g)
            S = vb.prestress(F[:, 0])[0]
            row = {"foot": side}
            for nm, extra in ((f"foot{side}", foot_dofs(b, side, solid)),
                              (f"foot{side}+top", foot_dofs(b, side, solid) | top)):
                if nm not in vb.variants:
                    vb.add_variant(nm, extra)
                lam, modes = vb.eig(S, E_B, 3, variant=nm)
                row["foot_held" if "+" not in nm else "foot_held_crown_held"] = describe(
                    vb.view(nm), S, modes, lam, regions)
                if "+" not in nm:
                    np.savez_compressed(OUT / f"{tag}_{basis}_setdown_{k.split(':')[0].replace('@', '_')}.npz",
                                        mode=modes[:, 0].astype(np.float32))
            res["sets"][k] = row
            log(f"   set-down {k}: foot held {row['foot_held'][0]['margin']:.3f} ({row['foot_held'][0]['lead']}), "
                f"+crown {row['foot_held_crown_held'][0]['margin']:.3f} ({time.time() - t0:.0f} s)")
    vb.free()
    res["min_foot_held"] = min(r["foot_held"][0]["margin"] for r in res["sets"].values())
    res["min_foot_held_crown_held"] = min(r["foot_held_crown_held"][0]["margin"] for r in res["sets"].values())
    p.write_text(json.dumps(res, default=FI._jd))
    return res


def run_extra(basis: str, b: dict | None = None, solid: np.ndarray | None = None, tag: str = "h1", log=print,
              refresh: bool = False, n: int = N_SCREEN) -> dict:
    """Braced full runs on the n lowest screened sets that are NOT set-down (the set-down sets fill the first screen
    slots with their foot mode, which run_setdown treats on its own)."""
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    p = OUT / f"{tag}_{basis}_extra.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    base = json.loads((OUT / f"{tag}_{basis}.json").read_text())
    scr = sorted(((v, k) for k, v in base.get("screen", {}).items()
                  if v is not None and "single_stay_setdown" not in k and k not in base["full"]))
    cand = [k for _, k in scr[:n]]
    res = {"basis": basis, "full": {}}
    b = b or body()
    solid = b["solid"] if solid is None else solid
    dom, g = b["dom"], b["g"]
    t0 = time.time()
    with FI._ctx():
        sets = {s_.key: s_ for s_ in _sets(basis)}
        _, fixed = ft.assemble_loads(dom, [sets[next(iter(sets))]], solid_mask=solid)
        vb = VoxelBuckler(g, solid, fixed, ft.NU, extra_fixed=brace_dofs(b, solid))
        regions = region_of(g.elem_centers()[vb.ae], b["grp"][vb.ae])
        for k in cand:
            F, _ = ft.assemble_loads(dom, [sets[k]], solid_mask=solid)
            S = vb.prestress(F[:, 0])[0]
            lam, modes = vb.eig(S, E_B, K_TOP)
            res["full"][k] = {"why": "screened (not set-down)", "rayleigh_margin": base["screen"][k],
                              "modes": describe(vb, S, modes, lam, regions)}
            log(f"   extra braced {k} (screen {base['screen'][k]:.3f}): {res['full'][k]['modes'][0]['margin']:.3f} "
                f"{res['full'][k]['modes'][0]['lead']} ({time.time() - t0:.0f} s)")
    vb.free()
    p.write_text(json.dumps(res, default=FI._jd))
    return res


def gov_mode(basis: str, key: str, setdown: bool, tag: str = "h1") -> Path:
    """First mode of one set on the frame reading (crown held; + foot on the ground for set-down), cached."""
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    p = OUT / f"{tag}_gov_{basis}_{key.split(':')[0].replace('@', '_')}_{key.split(':')[1].split('|')[0]}.npz"
    if p.exists():
        return p
    b = body()
    solid, dom, g = b["solid"], b["dom"], b["g"]
    with FI._ctx():
        s_ = {x.key: x for x in _sets(basis)}[key]
        F, fixed = ft.assemble_loads(dom, [s_], solid_mask=solid)
    extra = brace_dofs(b, solid)
    if setdown:
        extra = extra | foot_dofs(b, setdown_side(F[:, 0], g), solid)
    vb = VoxelBuckler(g, solid, fixed, ft.NU, extra_fixed=extra)
    lam, modes = vb.eig(vb.prestress(F[:, 0])[0], E_B, 1)
    vb.free()
    np.savez_compressed(p, mode=modes[:, 0].astype(np.float32), lam=lam[0], set=key)
    return p


def sliver_mask(b: dict, solid: np.ndarray | None = None) -> np.ndarray:
    """The bridge lip under the spine-channel opening at the upper bar's underside: one voxel layer (z 497), y <= -33,
    |x| <= 12. STL: 3.7 mm deep (y -38.4..-34.7) and about 2 mm tall (z 496..498), spanning the opening; above it the
    channel is open on the body side (STL slices, bl065.md 3)."""
    s = b["solid"] if solid is None else solid
    cen = b["cen"]
    return s & (np.abs(cen[:, 2] - 497.0) < 1.0 + 1e-6) & (cen[:, 1] <= -33.0) & (np.abs(cen[:, 0]) <= 12.0)


def in_sliver(p) -> bool:
    return abs(p[2] - 497.0) <= 1.0 + 1e-6 and p[1] <= -33.0 and abs(p[0]) <= 12.0


def run_sliver(basis: str, b: dict | None = None, tag: str = "h1", log=print, refresh: bool = False) -> dict:
    """Every crown-held run whose first mode is driven from the sliver, rerun with the sliver deleted (crown held)."""
    from huntkit.fea.voxel_buckling import VoxelBuckler
    from . import frame_topopt as ft
    p = OUT / f"{tag}_{basis}_sliver.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    base = json.loads((OUT / f"{tag}_{basis}.json").read_text())
    ex = OUT / f"{tag}_{basis}_extra.json"
    full = dict(base["full"])
    if ex.exists():
        full.update(json.loads(ex.read_text())["full"])
    cand = {k: v["modes"][0] for k, v in full.items() if in_sliver(v["modes"][0]["driver_peak_mm"])}
    res = {"basis": basis, "sets": {}}
    if cand:
        b = b or body()
        dom, g = b["dom"], b["g"]
        sl = sliver_mask(b)
        s2 = b["solid"] & ~sl
        res["sliver_voxels"] = int(sl.sum())
        t0 = time.time()
        with FI._ctx():
            sets = {s_.key: s_ for s_ in _sets(basis)}
            _, fixed = ft.assemble_loads(dom, [sets[next(iter(cand))]], solid_mask=s2)
            vb = VoxelBuckler(g, s2, fixed, ft.NU, extra_fixed=brace_dofs(b, s2))
            regions = region_of(g.elem_centers()[vb.ae], b["grp"][vb.ae])
            for k, m0 in cand.items():
                F, _ = ft.assemble_loads(dom, [sets[k]], solid_mask=s2)
                S = vb.prestress(F[:, 0])[0]
                lam, modes = vb.eig(S, E_B, 3)
                d = describe(vb, S, modes, lam, regions)
                res["sets"][k] = {"with_sliver": m0["margin"], "sliver_deleted": d}
                log(f"   sliver {k}: with {m0['margin']:.3f} -> deleted {d[0]['margin']:.3f} {d[0]['lead']} "
                    f"({time.time() - t0:.0f} s)")
        vb.free()
    p.write_text(json.dumps(res, default=FI._jd))
    return res


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else "report"
    if cmd == "run":
        b = body()
        for bs in (a[1:] or BASES):
            if bs == "squeeze":
                run_squeeze(b)
            elif bs.startswith("sliver:"):
                run_sliver(bs.split(":", 1)[1], b)
            elif bs.startswith("extra:"):
                run_extra(bs.split(":", 1)[1], b)
            elif bs.startswith("setdown:"):
                run_setdown(bs.split(":", 1)[1], b)
            else:
                run_basis(bs, b)
        return 0
    from . import bl065_report as R
    if cmd == "fix":
        R.fix(a[1:])
        return 0
    R.report()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
