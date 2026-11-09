"""Lighter-frame study 2: printed PAHT-CF nodes on bought carbon tubes, checked to HA-LS-1 rev C.

Owner decision 2026-11-09 ("Yes" to the weight-pass recommendation, item 4): start a lighter-frame study that keeps
the generative-print look. Design doc: ``designs/pack_5200/analysis/frame_light2.md``; concept files:
``designs/pack_5200/frame_light2/``; research: ``docs/research/light_frame_architectures.md``.

Every concept keeps the v2 tube topology that the beam model already knows (``huntkit.fea.pack5200``): two straight
OD 20 stays that the carbon crown legs telescope inside, mid bar z 330, upper bar z 520 (pawl), formed CF lumbar pan
(the lumbar-pad seat), Ti hip-pivot mount, carbon crown with the rev C fix. What changes is the JOINT technology and
what is printed:

- every tube junction becomes a printed PAHT-CF node (owner's H2S), bonded with MMA. The printed node is modelled
  as a short PAHT "lug neck" member between the stay and the bar socket, so its compliance and its root stress come
  out of the beam solve; its bond is checked with ``huntkit.fea.joints`` at a PUBLISHED printed-polyamide lap shear
  (``TAU_PA_MPA``), not the carbon value;
- concept BRANCH adds a printed hip node with two branch tubes up to the z 330 nodes (the lattice look);
- concept SKIN is NODE plus a non-structural 0.8 mm printed skin shaped like today's branch body.

Checks per concept, at torso 15 / 19 / 23 in, every rev C case set (``ls1_envelope``: crown-bar couple incl. C6p
posts, and the IM3 couple): member first-ply (CFRP) / allowable (PAHT neck) SF / factor; frame buckling / (1.5 x
factor); printed-socket bonds (average >= factor, Volkersen peak >= 1); crown members, corner bonds, bushings
(``frame_cg_recheck._crown_rows``); lumbar pan (``pack5200.plate_checks``); hand checks for the foot boot, the
stay-top collar ring and the hip node (4 x M5 inserts, flange bond); fatigue at 1e5 x 1.6 g (CFRP FI <= 0.5,
PAHT <= 0.3 x knocked-down strength, bond <= 0.3 x dry lap shear).

Run: ``python -m huntkit.gendesign.frame_light2``   (about 5-10 min on 4 cores)
"""
from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT, get_material

ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
CONCEPT_DIR = REPO_ROOT / "designs" / "pack_5200" / "frame_light2"
RESULTS = CONCEPT_DIR / "frame_light2_results.json"
SCREENS = REPO_ROOT / "outputs" / "screens"
DOC_SCREENS = REPO_ROOT / "docs" / "screens"
SHOT = "20261109_framelight"
TORSOS = (15.0, 19.0, 23.0)

# ----------------------------------------------------------------------------- materials / allowables
PAHT = "pa12_cf_fdm_paht"
RHO_PAHT = 1.06e-3            # g/mm3 (record 1060 kg/m3)
RHO_CF = 1.55e-3              # g/mm3 (cfrp records)
RHO_ADH = 0.98e-3             # g/mm3 (adhesive_methacrylate_ma record)
G_WALK = 1.6                  # HA-LS-1 fatigue g
PAHT_FAT = 0.3                # pa12_cf_fdm_paht fatigue_1e5_ratio (record, ASSUMPTION there)
CFRP_FAT_FI = 0.5             # HA-LS-1: CFRP FI <= 0.5 at the 1.6 g peak
BOND_FAT = 0.3                # HA-LS-1: bond <= 0.3 x lap shear at 1.6 g

# Printed polyamide bond strength. Published: MJF PA12, media-blasted, 12.5 mm single lap, adhesive (interface)
# failure: PU 3M DP620NS 5.0 MPa, epoxy DP490 3.7, Loctite EA 9466 3.7, HY 4090 3.8 (Sedlacek et al., Polymers
# 17(22):3020, 2025, PMC12656205); FFF PA-CF to Al 1-6.6 MPa (Martins et al., Appl. Sci. 13:4429, 2023).
# ASSUMPTION: MMA on a sanded + flame-treated PAHT-CF print reaches at least the best published PA12 value, 5.0 MPa
# dry; hot/wet 0.8 -> 4.0 MPa design. The older printed-frame study assumed 6 MPa hot/wet with no source: not used.
TAU_PA_DRY = 5.0
TAU_PA_MPA = TAU_PA_DRY * 0.8

# PAHT-CF design allowables (record, env knockdown 0.8): XY 88, Z 47 MPa
PAHT_XY = 0.8 * 88.0
PAHT_Z = 0.8 * 47.0

LUG = {
    "t": 2.4,                 # printed socket wall (6 perimeters of a 0.4 mm line; record min_wall 2.0)
    "ta": 0.5,                # MMA bondline (glass-bead spacer), as frame.yaml
    "end_mm": 35.0,           # bar end socket depth
    "spigot_mm": 30.0,        # inner printed spigot (double lap, Robot Bike Co / Atherton practice)
    "spigot_t": 2.0,
    "through_mm": 60.0,       # stay through-sleeve at a hub
    "foot_mm": 40.0,          # stay foot boot socket
    "collar_mm": 35.0,        # stay-top collar (bushing seat) bonded length
    "collar_t": 3.0,
    "neck_mm": 12.0,          # node neck between the stay sleeve and the bar socket (ASSUMPTION: socket base)
    "flare": 0.30,            # generative root "fingers" + fillets, fraction of the sleeve volume (ASSUMPTION)
}

# Interface clips on the stays (hard points the printed body carries today; geometry.yaml frame.hard_points).
# Each is a printed split collar bonded to the stay, 22 mm wide, plus its eye / boss.
CLIPS = {
    "z80 wing lash": 2.0, "z110 shoulder-strap lower anchor": 3.0, "z190 IM1 fairlead seat": 3.0,
    "z250 wing lash": 2.0, "z420 wing lash": 2.0,
}                             # value = eye / boss extra g each (ASSUMPTION)
NODE_FEATURE_G = {            # hard points folded into the nodes (ASSUMPTION, g per node)
    "foot": 6.0,              # hinge-pin boss z 60 (bag_anchor_low, US pins) + hip-stabiliser anchor + bumper
    "mid_hub": 4.0,           # IM2 fairlead seat + bag_anchor_mid
    "upper_hub": 5.0,         # IM3 fairlead seat + B-24 float-link eye
    "stay_top": 2.0,          # bushing seat lip
}

# Unchanged parts (frame.yaml mass_g, rev C fix lines frame_mass_production.json crown_fix_lines_g)
CROWN = {
    "crown legs (2, rev C +2 UD)": 88.1 + 14.27,
    "crown top bar (rev C +1 UD)": 20.0 + 2.12,
    "crown spine tube (rev C +1 UD)": 29.3 + 3.35,
    "crown corner wraps + 0.8 mm bondline": 24.0 + 2.21,     # 2 corners: 0.75 mm wrap over 30 mm of each tube
    "rack + pawl housing + pulley guides": 44.0,
    "UHMWPE bushings (4)": 16.7,
    "spine clamp": 6.0,
}
PIVOT = {"Ti hip-pivot mount (SLM)": 20.2, "4 x M5 heat-set inserts (ASSUMPTION 1.2 g)": 4.8}
PAN_G_PER_MM = 110.4 / 1.5    # frame.yaml: lumbar pan 250 x 140 + 2 x 25 flanges at 1.5 mm
PADUP_G = 12.5

# Today's production frame (frame_mass_production.json, spreader_results.json)
TODAY = {"printed_body_g": 823.2, "non_body_g": 217.4, "crown_fix_g": 22.0, "frame_g": 1062.6,
         "spreader_g": 162.3, "frame_spreader_g": 1224.9,
         "carry_dy_mm": 29.7, "torsion_Nm_per_deg": 0.44}    # production_frame_results.json stiff (4 mm voxels)
V2_TUBE = {"frame_g": 599.0, "carry_dy_mm": 6.33, "torsion_Nm_per_deg": 2.87}   # frame.yaml, printed_frame_study
PACK_AFTER_ABC_G = 3779.0     # weight_pass_corrie.md: CORRIE on today's frame after packages A + B + C
TARGET_PACK_G = 2994.0        # 6.6 lb


# ----------------------------------------------------------------------------- concepts
def _spec(od, fam, k):
    from huntkit.fea.sizing import section_spec
    return section_spec(("round", float(od)), fam, int(k))


BASE = {"stay": (20, "RW0", 3), "bar": (18, "RW45", 4), "ubar": (22, "RW45", 6), "pan_t": 1.5,
        "branch": None, "skin_t": 0.0, "spigot": True, "joint_mode": "printed"}

# joint_mode "printed": the tube is bonded straight into the printed PAHT-CF socket (double lap with a printed
#   spigot at bar ends). Bond allowable = published printed-polyamide lap shear (TAU_PA_MPA).
# joint_mode "wrap": the printed knuckle is the visible node AND the bonding former; 3 plies of carbon twill
#   (0.75 mm, the v2 frame.yaml wrap) run from the knuckle onto each tube as tapered "tendons" (30 mm, through 40).
#   The load path is carbon to carbon as in the v2 frame, so the bond is checked with the v2 carbon wrap joint.
CONCEPTS = {
    "NODE": {"label": "NODE: printed sockets on a carbon ladder",
             "look": "Organic printed knuckles at every junction with root fingers flowing along the tubes; tubes "
                     "bonded straight into the prints. The simplest build.",
             "joint_mode": "printed"},
    "TENDON": {"label": "TENDON: printed knuckles with carbon tendon wraps",
               "look": "The NODE knuckles, with tapered carbon-twill 'tendons' laid from each knuckle onto its "
                       "tubes: printed bone, carbon sinew. The wrap carries the joint load.",
               "joint_mode": "wrap"},
    "BRANCH": {"label": "BRANCH: TENDON plus a printed hip node and branch tubes",
               "look": "TENDON plus a printed hip node at the pivot that branches into two OD 14 carbon tubes up "
                       "to the z 330 knuckles: the Y-branch silhouette of today's body, as a lattice.",
               "joint_mode": "wrap", "branch": {"sec": (14, "RW45", 4)}},
    "SKIN": {"label": "SKIN: TENDON structure under a printed skin",
             "look": "The TENDON ladder hidden under a 0.8 mm printed shell shaped like today's branch body: reads "
                     "exactly like today's frame.",
             "joint_mode": "wrap", "skin_t": 0.8},
}
WRAP_T = 0.75                  # frame.yaml joints.wrap
WRAP_END, WRAP_THROUGH = 30.0, 40.0


def wrap_joint() -> dict:
    """The v2 carbon wrap joint (frame.yaml frame.joint)."""
    import yaml
    fy = yaml.safe_load((REPO_ROOT / "designs" / "pack_5200" / "frame.yaml").read_text())["frame"]
    return {**fy["joint"], "wrap": True}


def candidate(name: str, **over) -> dict:
    c = {**copy.deepcopy(BASE), **{k: v for k, v in CONCEPTS[name].items() if k not in ("label", "look")}}
    c.update(over)
    c["name"] = name
    return c


def _crown_joint() -> dict:
    """The carbon crown corners stay wrapped carbon (frame.yaml joint + rev C 0.8 mm bondline)."""
    import yaml
    fy = yaml.safe_load((REPO_ROOT / "designs" / "pack_5200" / "frame.yaml").read_text())["frame"]
    return {**fy["joint"], **(fy.get("crown_joint") or {})}


def printed_joint(kind: str) -> dict:
    """bond_check params for a CF tube in a printed PAHT-CF socket. The allowable is applied afterwards
    (``TAU_PA_MPA``); the sleeve stiffness E t is the printed wall."""
    E = float(get_material(PAHT).require("youngs_modulus_xy_mpa"))
    G = E / 2.7
    t = LUG["collar_t"] if kind == "stay_top" else LUG["t"]
    L = {"end": LUG["end_mm"], "through": LUG["through_mm"], "foot": LUG["foot_mm"],
         "stay_top": LUG["collar_mm"], "branch": LUG["end_mm"]}[kind]
    return {"adhesive": "adhesive_methacrylate_ma", "adhesive_G_mpa": 300.0, "adhesive_t_mm": LUG["ta"],
            "overlap_mm": L, "through_overlap_mm": LUG["through_mm"], "sleeve_material": None,
            "sleeve_Et_n_mm": E * t, "sleeve_Gt_n_mm": G * t, "printed": True, "kind": kind}


def paht_neck_material() -> dict:
    return {"id": "paht_cf_node_neck", "youngs_modulus_mpa": float(get_material(PAHT).require("youngs_modulus_xy_mpa")),
            "shear_modulus_mpa": float(get_material(PAHT).require("youngs_modulus_xy_mpa")) / 2.7, "poisson": 0.35,
            "design_allowable_mpa": PAHT_XY, "density_kg_m3": 0.0}


def neck_section(od_tube: float):
    """Printed node neck: the socket sleeve annulus at the socket base, tube not credited (conservative)."""
    from huntkit.fea.sections import tube_round
    return tube_round(od_tube + 2 * LUG["ta"] + 2 * LUG["t"], LUG["t"])


def _split(m: dict, mem_id: str, from_node: str, s_mm: float, new: str, group: str, section, material) -> str:
    """Split member ``mem_id`` at ``s_mm`` from ``from_node``: the piece at ``from_node`` becomes the node neck."""
    md = next(q for q in m["members"] if q["id"] == mem_id)
    a, b = md["nodes"]
    other = b if a == from_node else a
    pa, pb = np.array(m["nodes"][from_node]), np.array(m["nodes"][other])
    L = float(np.linalg.norm(pb - pa))
    m["nodes"][new] = list(map(float, pa + (pb - pa) * s_mm / L))
    i = m["members"].index(md)
    neck = {"id": f"{from_node}-{new}", "nodes": [from_node, new], "section": section, "material": material,
            "group": group, "ref": md.get("ref", [0.0, 0.0, 1.0])}
    rest = {**md, "id": f"{new}-{other}", "nodes": [new, other]}
    m["members"][i:i + 1] = [neck, rest]
    return rest["id"]


def build(cand: dict, torso: float, posts: bool = False) -> dict:
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.sections import from_spec
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    over = {"stay_section": _spec(*cand["stay"]), "bar_section": _spec(*cand["bar"]),
            "upper_bar_section": _spec(*cand["ubar"]), "lumbar_plate_t": float(cand["pan_t"]),
            "crown_joint": _crown_joint()}
    m = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(torso), extension_posts=posts, **over),
                        95.0)
    m["name"] = f"light2_{cand['name']}"
    mat = paht_neck_material()
    joints = []
    for j in m["joints"]:
        jid = j["id"]
        if jid.startswith("crown_corner"):
            joints.append(j)
            continue
        if jid.startswith("post_socket"):
            # P-1 (this study): the accessory extension-post socket gets the crown corners' 0.8 mm bondline. With the
            # 0.5 mm line its Volkersen peak is 0.96 at C6p on TODAY's frame too (rev_c_verification_results.json
            # post_socket 0.957, a check the rev C summary table did not list).
            joints.append({**j, "params": {**(j.get("params") or {}), **_crown_joint()}})
            continue
        if cand.get("joint_mode") == "wrap" and not jid.startswith("stay_top"):
            joints.append({**j, "params": {**wrap_joint(), "kind": jid.rsplit("_", 1)[0]}})
            continue
        if jid.startswith(("mid_hub", "upper_hub")):
            tag = jid[-1]
            bar_id = j["members"][0]
            od = from_spec(next(q for q in m["members"] if q["id"] == bar_id)["section"]).dims["od"]
            nk = f"NK{'M' if jid.startswith('mid') else 'U'}{tag}"
            rest = _split(m, bar_id, j["node"], LUG["neck_mm"], nk, "lug_neck", neck_section(od), mat)
            joints.append({"id": f"{jid}_end", "node": nk, "members": [rest], "params": printed_joint("end"),
                           "spigot": bool(cand.get("spigot"))})
            joints.append({"id": f"{jid}_through", "node": j["node"], "members": [], "through": j["through"],
                           "params": printed_joint("through")})
        elif jid.startswith("foot"):
            joints.append({**j, "params": printed_joint("foot")})
        elif jid.startswith("stay_top"):
            joints.append({**j, "params": printed_joint("stay_top")})
        else:
            joints.append(j)
    m["joints"] = joints
    if cand.get("branch"):
        sec = _spec(*cand["branch"]["sec"])
        grid = m["plate_grid"]
        for tag, gj, stay_node in (("L", "2,1", "SL330"), ("R", "2,3", "SR330")):
            a = grid[gj]
            mid_ = f"BR{tag}"
            pa, pb = np.array(m["nodes"][a]), np.array(m["nodes"][stay_node])
            m["nodes"][mid_] = list(map(float, (pa + pb) / 2))
            for k, (n1, n2) in enumerate(((a, mid_), (mid_, stay_node))):
                m["members"].append({"id": f"branch_{tag}{k}", "nodes": [n1, n2], "section": sec, "material": None,
                                     "group": f"branch_{tag}", "ref": [0.0, 1.0, 0.0]})
            bp = ({**wrap_joint(), "kind": "branch"} if cand.get("joint_mode") == "wrap"
                  else printed_joint("branch"))
            m["joints"].append({"id": f"branch_hip_{tag}", "node": a, "members": [f"branch_{tag}0"],
                                "params": bp, "spigot": True})
            m["joints"].append({"id": f"branch_knuckle_{tag}", "node": stay_node, "members": [f"branch_{tag}1"],
                                "params": bp, "spigot": True})
    m["light2"] = cand
    return m


# ----------------------------------------------------------------------------- checks
def _spigot_factor(j: dict, sec) -> float:
    """Double-lap socket (outer sleeve + inner printed spigot): bond perimeter OD + ID instead of OD."""
    if not j.get("spigot"):
        return 1.0
    od, t = sec.dims["od"], sec.dims["t"]
    return (od + (od - 2 * t)) / od


def printed_bond_rows(res, model) -> list[dict]:
    from huntkit.fea.joints import check_frame_joints
    from huntkit.fea.sections import from_spec
    js = [j for j in model["joints"] if (j.get("params") or {}).get("printed")]
    out = []
    by = {j["id"]: j for j in js}
    secs = {md["id"]: md["section"] for md in model["members"]}
    for r in check_frame_joints(res, js):
        j = by[r["joint"]]
        k = _spigot_factor(j, from_spec(secs[r["member"]])) if r["kind"] == "end" else 1.0
        tau, peak = r["tau_avg"] / k, r["tau_peak"] / k
        out.append({"joint": r["joint"], "kind": j["params"]["kind"], "member": r["member"], "tau": tau,
                    "tau_peak": peak, "sf_avg": TAU_PA_MPA / tau if tau > 0 else np.inf,
                    "sf_peak": TAU_PA_MPA / peak if peak > 0 else np.inf})
    return out


def wrap_bond_rows(res, model) -> list[dict]:
    """Carbon tendon wraps: the v2 joint check (MMA on CFRP, record lap shear x 0.8 hot/wet)."""
    from huntkit.fea.joints import check_frame_joints
    js = [j for j in model["joints"] if (j.get("params") or {}).get("wrap")]
    by = {j["id"]: j for j in js}
    return [{"joint": r["joint"], "kind": "wrap " + by[r["joint"]]["params"]["kind"].replace("_hub", " hub"),
             "member": r["member"], "tau": r["tau_avg"], "tau_peak": r["tau_peak"], "sf_avg": r["sf_avg"],
             "sf_peak": r["sf_peak"], "allow": r["allow"]} for r in check_frame_joints(res, js)]


def clip_bonds(res, model) -> dict:
    """Printed split-collar clips bonded to the stays (22 mm wide): the external load at each stay node between
    z 60 and 450 that is not at a knuckle (IM1 strap at z 190, shoulder anchor, lash) in bond shear."""
    from huntkit.gendesign.loads import external_on_node
    worst = (np.inf, "")
    for n, p in model["nodes"].items():
        if not (n.startswith("SL") or n.startswith("SR")):
            continue
        z = p[2]
        if not (60.0 < z < 450.0) or abs(z - 330.0) < 1:
            continue
        F = external_on_node(res, model, n)[:3]
        f = float(np.linalg.norm(F))
        if f < 1e-6:
            continue
        tau = f / (math.pi * 20.0 * 22.0)
        sf = TAU_PA_MPA / tau
        if sf < worst[0]:
            worst = (sf, n)
    return {"sf": worst[0], "node": worst[1]}


def foot_boot(res, model) -> dict:
    """Foot boot at the socket mouth: the ground force acts at the boot floor; the boot annulus at the mouth
    carries the lateral force x socket depth (tube not credited). Bearing of the tube end on the floor."""
    from huntkit.fea.sections import from_spec, tube_round
    stay = from_spec(next(q for q in model["members"] if q["group"].startswith("stay_lower"))["section"])
    od = stay.dims["od"]
    boot = tube_round(od + 2 * LUG["ta"] + 2 * LUG["t"], LUG["t"])
    worst = (np.inf, None)
    for n in ("SL0", "SR0"):
        F = np.zeros(3)
        L_ = (res.model.get("loads") or {}).get(n)
        if L_ is not None:
            F += np.asarray(L_, float)[:3]
        if n in res.reactions:
            F += np.asarray(res.reactions[n])[:3]
        lat = float(np.hypot(F[0], F[1]))
        M = lat * LUG["foot_mm"]
        sig = abs(F[2]) / boot.A + M / (boot.Iy / (boot.dims["od"] / 2))
        sf = PAHT_XY / sig if sig > 0 else np.inf
        if sf < worst[0]:
            worst = (sf, n, float(F[2]), lat)
    return {"sf": worst[0], "node": worst[1], "Fz": worst[2] if worst[1] else 0.0, "lat": worst[3] if worst[1] else 0.0}


def stay_top_collar(res, model) -> dict:
    """Top bushing radial load on the stay top: ring moment (120 deg land, huntkit.fea.rings) shared by the CF stay
    wall and the printed collar by E t^3; the collar hoop is checked at the Z (layer-normal) allowable."""
    from huntkit.fea.rings import ring_moment_coeff
    from huntkit.fea.sections import from_spec
    p = model["params"]
    stay = from_spec(next(q for q in model["members"] if q["group"].startswith("stay_upper"))["section"])
    cm = ring_moment_coeff(float(p.get("bushing_contact_deg") or 0.0))
    Lb = float(p["bushing_len_mm"])
    lf = res.meta.get("link_forces", {})
    tc = LUG["collar_t"]
    Ec = float(get_material(PAHT).require("youngs_modulus_z_mpa"))
    best = {"sf_collar": np.inf, "sf_stay": np.inf}
    for name in ("bush_top_L", "bush_top_R"):
        f = lf.get(name)
        if f is None:
            continue
        Fr = float(np.hypot(f[0], f[1]))
        Dc, Ds = Ec * tc ** 3, stay.Ex * stay.dims["t"] ** 3
        share = Dc / (Dc + Ds)
        Rm = stay.dims["od"] / 2 + tc / 2
        m_c = cm * (Fr / Lb) * Rm
        sig = 6 * m_c * share / tc ** 2
        sfc = PAHT_Z / sig if sig > 0 else np.inf
        Rs = stay.dims["od"] / 2 - stay.dims["t"] / 2
        m_st = cm * (Fr / Lb) * Rs * (1 - share)
        fpf = stay.laminate.first_ply_failure((0, -Fr / (2 * Lb), 0), (0, m_st, 0))
        best["sf_collar"] = min(best["sf_collar"], sfc)
        best["sf_stay"] = min(best["sf_stay"], float(fpf["sf"]))
        best["Fr_max"] = max(best.get("Fr_max", 0.0), Fr)
    return best


INSERT_PULL_N = 1500.0        # M5 heat-set insert pull-out in PAHT-CF: ASSUMPTION as hipbelt_structural.md (test due)
HIP_FLANGE = (70.0, 60.0)     # printed hip node flange bonded to the pan face, x by z (ASSUMPTION)
PIVOT_STANDOFF = 22.0         # pin axis to the pan face (y): HP y -48.1 vs pan face y ~ -26 (geometry.yaml)
INSERT_PITCH = (36.0, 36.0)   # 4 x M5 on a 36 x 36 square around the pin boss (ASSUMPTION)


def hip_node(res, model) -> dict:
    """Printed hip node: Ti mount on 4 x M5 heat-set inserts (hipbelt decision 2026-11-09); node flange bonded to
    the CF pan face. Insert demand = tension share of the pivot force + its moment about the pan face."""
    R6 = np.asarray(res.reactions.get("HP", np.zeros(6)), float)
    F = R6[:3]
    Fx, Fy, Fz = F
    Mx, Mz = abs(Fz) * PIVOT_STANDOFF, abs(Fx) * PIVOT_STANDOFF      # about the pan face
    # inserts: pull-off (y) + moment couple over the bolt square; a pivot pull AWAY from the pan loads them
    px, pz = INSERT_PITCH
    t_ins = max(-Fy, 0.0) / 4 + Mx / (2 * pz) + Mz / (2 * px)
    a, b = HIP_FLANGE
    A = a * b
    tau = math.hypot(Fx, Fz) / A
    sig = abs(Fy) / A + 6 * Mx / (a * b * b) + 6 * Mz / (b * a * a)
    tau_eq = math.hypot(tau, sig)          # flatwise tension of a bond read against lap shear: conservative
    return {"F": [float(v) for v in F], "insert_n": float(t_ins),
            "sf_insert": INSERT_PULL_N / t_ins if t_ins > 0 else np.inf,
            "flange_tau": float(tau_eq), "sf_flange": TAU_PA_MPA / tau_eq if tau_eq > 0 else np.inf}


def _group_label(g: str) -> str:
    if g.startswith("stay"):
        return "stays"
    if g.startswith("branch"):
        return "branch tubes"
    if g.startswith("crown_leg"):
        return "crown legs"
    return g


def run_case(cand, torso, variant, case, posts=False):
    """One case on one torso. Returns a compact row (picklable)."""
    from huntkit.fea.pack5200 import plate_checks
    from . import frame_cg_recheck as R
    c = copy.copy(case)
    c.params = dict(c.params)
    c.buckling = variant == "crown_bar" and c.kind != "setdown"
    m = build(cand, torso, posts)
    res = c.run(m)
    req = float(c.required_sf)
    row = {"case": c.name, "torso": torso, "variant": variant, "req": req, "g": float(c.g_factor),
           "members": {}, "hip_fraction": res.meta.get("hip_fraction")}
    for mm in res.members:
        g = _group_label(mm["group"])
        if g == "lumbar_plate_shear":
            continue
        sf = float(mm["sf"]) / req
        if sf < row["members"].get(g, (np.inf,))[0]:
            row["members"][g] = (sf, mm["id"], float(mm["sf"]))
    row["buckling"] = float(res.buckling_sf) / (1.5 * req) if c.buckling and res.buckling_sf else None
    bonds = printed_bond_rows(res, m)
    wb = wrap_bond_rows(res, m)
    row["bonds"] = {}
    for b in bonds:
        key = b["kind"]
        cur = row["bonds"].get(key)
        if cur is None or b["sf_avg"] / req < cur[0]:
            row["bonds"][key] = (b["sf_avg"] / req, b["sf_peak"], b["joint"], b["tau"], b["tau_peak"])
    for b in wb:
        key = b["kind"]
        cur = row["bonds"].get(key)
        if cur is None or b["sf_avg"] / req < cur[0]:
            row["bonds"][key] = (b["sf_avg"] / req, b["sf_peak"], b["joint"], b["tau"], b["tau_peak"])
    cb = clip_bonds(res, m)
    row["clip"] = cb["sf"] / req
    cr = R._crown_rows(res, m, c)
    row["crown"] = {"members": cr["members"], "joints": cr["joints"], "bushings": cr["bushings"],
                    "pawl_n": cr["pawl_n"]}
    pc = plate_checks(res, m)
    row["plate"] = {}
    for p in pc:
        k = p["check"].split("(")[0].strip()
        div = 1.5 * req if p.get("buckling") else req
        row["plate"][k] = float(p["sf"]) / div
    fb = foot_boot(res, m)
    row["foot"] = fb["sf"] / req
    stc = stay_top_collar(res, m)
    row["collar"] = stc["sf_collar"] / req
    row["stay_ring"] = stc["sf_stay"] / req
    hn = hip_node(res, m)
    row["hip_insert"] = hn["sf_insert"] / req
    row["hip_flange"] = hn["sf_flange"] / req
    row["hip_insert_n"] = hn["insert_n"]
    if c.name == "static_carry":
        # fatigue at 1.6 g from the 1 g static-carry solve (R = 0 pulsating)
        fat = {}
        for mm in res.members:
            g = _group_label(mm["group"])
            if g == "lumbar_plate_shear":
                continue
            raw = float(mm["sf"])
            f = (PAHT_FAT * raw / G_WALK) if g == "lug_neck" else (CFRP_FAT_FI * raw / G_WALK)
            if f < fat.get(g, (np.inf,))[0]:
                fat[g] = (f, mm["id"])
        for b in bonds:
            f = BOND_FAT * TAU_PA_DRY / (b["tau"] * G_WALK) if b["tau"] > 0 else np.inf
            k = f"bond {b['kind']}"
            if f < fat.get(k, (np.inf,))[0]:
                fat[k] = (f, b["joint"])
        for b in wb:
            f = BOND_FAT * (b["allow"] / 0.8) / (b["tau"] * G_WALK) if b["tau"] > 0 else np.inf
            k = f"bond {b['kind']}"
            if f < fat.get(k, (np.inf,))[0]:
                fat[k] = (f, b["joint"])
        fat["clip bond"] = (BOND_FAT * TAU_PA_DRY / TAU_PA_MPA * cb["sf"] / G_WALK, cb["node"])
        fat["foot boot"] = (PAHT_FAT * fb["sf"] / G_WALK, fb["node"])
        fat["stay-top collar"] = (PAHT_FAT * stc["sf_collar"] / G_WALK, "bush_top")
        fat["hip inserts"] = (0.5 * hn["sf_insert"] / G_WALK, "HP")     # ASSUMPTION: insert fatigue 0.5 x pull-out
        fat["hip flange bond"] = (BOND_FAT * TAU_PA_DRY / (hn["flange_tau"] * G_WALK) if hn["flange_tau"] > 0
                                  else np.inf, "HP")
        row["fatigue"] = fat
        cj = cr["joints"].get("crown_corner")
        if cj:
            row["fatigue"]["crown corner bond"] = (cj[0] * req * BOND_FAT / G_WALK, "crown_corner")
    return row


def _task(args):
    cand, torso = args
    from huntkit.fea.load_standard import ls1_envelope
    rows = []
    for variant, cases in ls1_envelope("C").items():
        for c in cases:
            rows.append(run_case(cand, torso, variant, c, posts=(c.name == "tall_load_posts")))
    return rows


def evaluate(cand: dict, procs: int = 3, torsos=TORSOS) -> dict:
    t0 = time.time()
    args = [(cand, t) for t in torsos]
    if procs > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(procs, len(args))) as pool:
            parts = pool.map(_task, args)
    else:
        parts = [_task(a) for a in args]
    rows = [r for p in parts for r in p]
    return {"cand": cand, "rows": rows, "summary": summarize(rows), "seconds": time.time() - t0}


def summarize(rows: list) -> dict:
    """Worst margin per check family, per case (worst torso and couple variant)."""
    checks = {}

    def put(key, val, where):
        if val is None or not np.isfinite(val):
            return
        if key not in checks or val < checks[key][0]:
            checks[key] = (float(val), where)

    by_case = {}
    for r in rows:
        where = f"{r['case']}|{r['torso']:g}|{'IM3' if r['variant'] == 'strap_upper' else 'bar'}"
        vals = []
        for g, (sf, mid, _) in r["members"].items():
            put(f"member: {g}", sf, f"{where} {mid}")
            vals.append(sf)
        if r["buckling"] is not None:
            put("frame buckling", r["buckling"], where)
            vals.append(r["buckling"])
        for k, (a, pk, jid, *_ ) in r["bonds"].items():
            put(f"bond avg: {k}", a, f"{where} {jid}")
            put(f"bond Volkersen peak: {k}", pk, f"{where} {jid}")
            vals += [a, pk]
        for k, (sf, mid) in r["crown"]["members"].items():
            put(f"crown: {k}", sf, f"{where} {mid}")
            vals.append(sf)
        for k, (a, pk, mid) in r["crown"]["joints"].items():
            put(f"crown: {k} bond avg", a, where)
            put(f"crown: {k} bond peak", pk, where)
            vals += [a, pk]
        for k, v in r["crown"]["bushings"].items():
            put(f"crown: {k}", v, where)
            vals.append(v)
        for k, v in r["plate"].items():
            put(f"lumbar pan: {k}", v, where)
            vals.append(v)
        for k in ("foot", "collar", "stay_ring", "hip_insert", "hip_flange", "clip"):
            label = {"clip": "stay clip bond (PAHT)", "foot": "foot boot (PAHT)", "collar": "stay-top collar ring (PAHT, Z)",
                     "stay_ring": "stay ring under the collar", "hip_insert": "hip node 4 x M5 inserts",
                     "hip_flange": "hip node flange bond"}[k]
            put(label, r[k], where)
            vals.append(r[k])
        pawl = abs(r["crown"]["pawl_n"][2]) * r["req"]
        put("torso adjust: rack (5328 N)", 5328.0 / pawl if pawl > 0 else np.inf, where)
        key = (r["case"], r["variant"])
        mn = min(v for v in vals if np.isfinite(v))
        if key not in by_case or mn < by_case[key][0]:
            by_case[key] = (mn, r["torso"])
        if "fatigue" in r:
            for k, (f, mid) in r["fatigue"].items():
                put(f"fatigue: {k}", f, f"{r['torso']:g}|{'IM3' if r['variant'] == 'strap_upper' else 'bar'} {mid}")
    strength = {k: v for k, v in checks.items() if not k.startswith("fatigue")}
    fatigue = {k: v for k, v in checks.items() if k.startswith("fatigue")}
    smin = min(strength.items(), key=lambda kv: kv[1][0])
    fmin = min(fatigue.items(), key=lambda kv: kv[1][0])
    hip = [r["hip_fraction"] for r in rows if r["case"] == "static_carry" and r["variant"] == "crown_bar"]
    return {"checks": checks, "min_strength": (smin[1][0], smin[0], smin[1][1]),
            "min_fatigue": (fmin[1][0], fmin[0], fmin[1][1]),
            "by_case": {f"{k[0]}|{k[1]}": v for k, v in by_case.items()},
            "pass": smin[1][0] >= 1.0 and fmin[1][0] >= 1.0,
            "hip_fraction_static": float(np.mean([h for h in hip if h is not None])) if hip else None}


# ----------------------------------------------------------------------------- mass, print, cost
def _member_len(m, groups) -> float:
    L = 0.0
    for md in m["members"]:
        if any(md["group"].startswith(g) for g in groups):
            a, b = md["nodes"]
            L += float(np.linalg.norm(np.subtract(m["nodes"][b], m["nodes"][a])))
    return L


def _sleeve_vol(d, L, t, ta=LUG["ta"]):
    return math.pi * (d + 2 * ta + t) * t * (L + 3.0)


def _spigot_vol(od, wall, L, ts=LUG["spigot_t"], ta=LUG["ta"]):
    idd = od - 2 * wall - 2 * ta
    return math.pi * (idd - ts) * ts * L


def _adh(d, L, ta=LUG["ta"]):
    return math.pi * d * L * ta * RHO_ADH * 1.3          # +30 % fillet / squeeze-out (ASSUMPTION)


def _wrap_g(d_tubes, L_tubes, d_node, node_len):
    """Carbon tendon wrap (0.75 mm twill, laminate density): onto each tube over its wrap length + 8 mm ply-drop
    taper, plus the cover over the knuckle body (ASSUMPTION: wrap covers 60 % of the knuckle surface)."""
    v = sum(math.pi * (d + WRAP_T) * (L + 8.0) * WRAP_T for d, L in zip(d_tubes, L_tubes))
    v += 0.6 * math.pi * (d_node + 2 * WRAP_T) * node_len * WRAP_T
    return v * RHO_CF


def node_list(cand: dict) -> list[dict]:
    """Every printed node and clip of one frame: printed volume (mm3), bond mass (g), carbon wrap mass (g)."""
    from huntkit.fea.sections import from_spec
    st = from_spec(_spec(*cand["stay"]))
    bar = from_spec(_spec(*cand["bar"]))
    ub = from_spec(_spec(*cand["ubar"]))
    wrap = cand.get("joint_mode") == "wrap"
    ds = st.dims["od"]
    t = 2.0 if wrap else LUG["t"]                     # wrap mode: the print is a former (record min wall 2.0)
    Lend = WRAP_END if wrap else LUG["end_mm"]
    Lthr = WRAP_THROUGH if wrap else LUG["through_mm"]
    Lfoot = WRAP_END if wrap else LUG["foot_mm"]
    spig = cand.get("spigot") and not wrap
    neck = 0.0 if wrap else LUG["neck_mm"]
    out = []

    def add(name, qty, sleeves, spigots, bonds, feat_g, kind, wrap_g=0.0):
        v = sum(sleeves) * (1 + LUG["flare"]) + sum(spigots)
        out.append({"name": name, "qty": qty, "vol_mm3": v, "feature_g": feat_g, "bond_g": sum(bonds),
                    "wrap_g": wrap_g, "kind": kind})

    tack = 0.5 if wrap else 1.0                        # wrap mode: thin MMA tack in the former, wrap carries load
    add("foot node (boot + hinge-pin boss + stabiliser anchor + bumper)", 2,
        [_sleeve_vol(ds, Lfoot, t), math.pi / 4 * (ds + 2 * t) ** 2 * 4], [], [tack * _adh(ds, Lfoot)],
        NODE_FEATURE_G["foot"], "node", _wrap_g([ds], [Lfoot], ds + 2 * t, 15.0) if wrap else 0.0)
    for nm, b, feat in (("mid knuckle z 330 (stay through-sleeve + mid-bar socket, IM2 seat)", bar, "mid_hub"),
                        ("upper knuckle z 520 (stay through-sleeve + upper-bar socket, IM3 + B-24 eye)", ub,
                         "upper_hub")):
        db = b.dims["od"]
        sp = [_spigot_vol(db, b.dims["t"], LUG["spigot_mm"])] if spig else []
        bonds = [tack * _adh(ds, Lthr), tack * _adh(db, Lend)]
        if spig:
            bonds.append(_adh(db - 2 * b.dims["t"], LUG["spigot_mm"]))
        wg = _wrap_g([ds, ds, db], [Lthr / 2, Lthr / 2, Lend], ds + 2 * t, db + 2 * t) if wrap else 0.0
        add(nm, 2, [_sleeve_vol(ds, Lthr, t), _sleeve_vol(db, Lend + neck, t)], sp, bonds, NODE_FEATURE_G[feat],
            "node", wg)
    add("stay-top collar (bushing seat)", 2, [_sleeve_vol(ds, LUG["collar_mm"], LUG["collar_t"])], [],
        [_adh(ds, LUG["collar_mm"])], NODE_FEATURE_G["stay_top"], "node")
    for nm, eye in CLIPS.items():
        add(f"clip {nm}", 2, [_sleeve_vol(ds, 22.0, 2.0)], [], [_adh(ds, 22.0)], eye, "clip")
    a, b = HIP_FLANGE
    hip_v = a * b * 3.0 + math.pi / 4 * (30.0 ** 2 - 10.0 ** 2) * PIVOT_STANDOFF * 0.6   # flange + boss (ASSUMPTION)
    hip_bonds = [a * b * LUG["ta"] * RHO_ADH * 1.2]
    sleeves = [hip_v]
    if cand.get("branch"):
        br = from_spec(_spec(*cand["branch"]["sec"]))
        d = br.dims["od"]
        sleeves += [2 * _sleeve_vol(d, Lend, t)]
        hip_bonds += [2 * tack * _adh(d, Lend)]
        spv = [2 * _spigot_vol(d, br.dims["t"], LUG["spigot_mm"])] if spig else []
        add("hip node (Ti-mount boss, 4 x M5, flange on the pan, 2 branch sockets)", 1, sleeves, spv, hip_bonds,
            0.0, "node", 2 * _wrap_g([d], [Lend], d + 2 * t, 20.0) if wrap else 0.0)
        out.append({"name": "branch sockets on the mid knuckles", "qty": 2,
                    "vol_mm3": _sleeve_vol(d, Lend, t) * (1 + LUG["flare"]) + (spv[0] / 2 if spv else 0.0),
                    "feature_g": 0.0, "bond_g": tack * _adh(d, Lend),
                    "wrap_g": _wrap_g([d], [Lend], d + 2 * t, 10.0) if wrap else 0.0, "kind": "node"})
    else:
        add("hip node (Ti-mount boss, 4 x M5, flange on the pan)", 1, sleeves, [], hip_bonds, 0.0, "node")
    for n in out:
        n["g_each"] = n["vol_mm3"] * RHO_PAHT + n["feature_g"]
    return out


def skin_area_mm2() -> float:
    """Outer area of today's printed branch body (print/frame/genframe_assembled.stl, mm)."""
    import trimesh
    mesh = trimesh.load(REPO_ROOT / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    return float(mesh.area)


def mass_rollup(cand: dict, model19: dict) -> dict:
    from huntkit.fea.sections import from_spec
    tubes = {}
    for g, lab, spec in (("stay", "stays (2)", cand["stay"]), ("mid_bar", "mid bar", cand["bar"]),
                         ("upper_bar", "upper bar", cand["ubar"])):
        L = _member_len(model19, [g])
        if g != "stay":
            L -= 2 * (_stay_r(cand) + (0.0 if cand.get("joint_mode") == "wrap" else LUG["neck_mm"]))
        tubes[lab] = L * from_spec(_spec(*spec)).A * RHO_CF
    if cand.get("branch"):
        L = _member_len(model19, ["branch"]) - 2 * 2 * 15.0
        tubes["branch tubes (2)"] = L * from_spec(_spec(*cand["branch"]["sec"])).A * RHO_CF
    nodes = node_list(cand)
    node_g = sum(n["qty"] * n["g_each"] for n in nodes)
    wrap_g = sum(n["qty"] * n["wrap_g"] for n in nodes)
    bond_g = sum(n["qty"] * n["bond_g"] for n in nodes)
    pan = {"lumbar pan (formed CF)": PAN_G_PER_MM * cand["pan_t"], "pivot pad-up (CF)": PADUP_G,
           "pan-to-stay bond": 2 * 140.0 * 10.0 * 0.5 * RHO_ADH * 1.3}
    skin = 0.0
    if cand.get("skin_t"):
        skin = skin_area_mm2() * cand["skin_t"] * RHO_PAHT * 1.10     # +10 % snap ribs (ASSUMPTION)
    groups = {"tubes": sum(tubes.values()), "printed nodes + clips": node_g, "carbon tendon wraps": wrap_g, "bonds (MMA)": bond_g + pan["pan-to-stay bond"],
              "lumbar pan + pad-up": pan["lumbar pan (formed CF)"] + pan["pivot pad-up (CF)"],
              "crown + torso adjust (unchanged)": sum(CROWN.values()), "Ti pivot mount + inserts": sum(PIVOT.values()),
              "printed skin (non-structural)": skin}
    total = sum(groups.values())
    return {"tubes": tubes, "nodes": nodes, "pan": pan, "crown": CROWN, "pivot": PIVOT, "groups": groups,
            "frame_g": total, "frame_spreader_g": total + TODAY["spreader_g"],
            "printed_g": node_g + skin, "printed_vol_cm3": (sum(n["qty"] * n["vol_mm3"] for n in nodes)
                                                            + (skin / RHO_PAHT if skin else 0)) / 1e3}


def _stay_r(cand):
    from huntkit.fea.sections import from_spec
    return from_spec(_spec(*cand["stay"])).dims["od"] / 2 + LUG["ta"] + LUG["t"]


def print_hours(mr: dict, n_parts: int) -> float:
    """frame_production.print_hours (8 mm3/s, +8 %) + 0.15 h per part for heat-up / plate change (ASSUMPTION)."""
    from .frame_production import print_hours as ph
    return ph(mr["printed_vol_cm3"] * 1e3) + 0.15 * n_parts


TUBE_USD_PER_M_16 = 30.0      # cfrp_rollwrapped_tube record ($30/m at ~16 mm), scaled with OD (mass_cut.md)


def cost(cand: dict, mr: dict) -> dict:
    from huntkit.fea.sections import from_spec
    c = {}
    lens = {"stays": (2 * 545.0, cand["stay"]), "mid bar": (200.0, cand["bar"]), "upper bar": (200.0, cand["ubar"])}
    if cand.get("branch"):
        lens["branch tubes"] = (2 * 240.0, cand["branch"]["sec"])
    for k, (L, spec) in lens.items():
        c[f"tube: {k}"] = L / 1000 * TUBE_USD_PER_M_16 * spec[0] / 16.0
    c["crown tubes (legs, top bar, spine; unchanged)"] = (2 * 430 * 16 + 214 * 18 + 300 * 20) / 1000 / 16 * TUBE_USD_PER_M_16
    c["PAHT-CF filament (nodes, clips, skin, rack/pawl) + 15 % failed prints"] = (mr["printed_g"] + 44.0) * 1.15 * 0.08
    c["lumbar pan material (record, scaled)"] = 8.31 * cand["pan_t"] / 2.0
    c["MMA cartridges (2) + glass beads + mixing tips (ASSUMPTION)"] = 80.0
    c["SLM Ti hip mount (ASSUMPTION, mass_cut.md)"] = 35.0
    c["M5 heat-set inserts + UHMWPE bushings (ASSUMPTION)"] = 12.0
    c["printed bonding jig (PLA/PETG ~400 g) + plywood base (ASSUMPTION)"] = 25.0
    return {"lines": c, "total": sum(c.values())}


# ----------------------------------------------------------------------------- stiffness, CG
TORSION_F = 100.0


def stiffness(cand: dict, torso: float = 19.0) -> dict:
    """Same two tests as frame_topopt.tube_frame_stiffness (hip pivot clamped): rev B static-carry load set ->
    stay-top aft deflection; +-100 N fore-aft at the stay tops -> torsion."""
    from huntkit.fea.frame import solve
    from huntkit.fea.load_standard import ls1_cases
    fm = build(cand, torso)
    c = next(x for x in ls1_cases(rev="B") if x.name == "static_carry")
    c.buckling = False
    res = c.run(fm)
    loads = {}
    for nid in fm["nodes"]:
        if nid == "HP":
            continue
        v = np.zeros(6)
        L_ = (res.model.get("loads") or {}).get(nid)
        if L_ is not None:
            v[: len(L_)] += L_
        if nid in res.reactions:
            v += res.reactions[nid]
        if np.any(v):
            loads[nid] = list(v)
    m = dict(fm); m["loads"] = loads; m["supports"] = {"HP": "fixed"}; m["inertia_relief"] = False
    r = solve(m, buckling=False)
    i = {n: r.node_ids.index(n) for n in ("SL530", "SR530")}
    out = {"carry_dy_mm": float(np.mean([r.u[6 * i[n] + 1] for n in i]))}
    m2 = dict(fm); m2["loads"] = {"SR530": [0, TORSION_F, 0, 0, 0, 0], "SL530": [0, -TORSION_F, 0, 0, 0, 0]}
    m2["supports"] = {"HP": "fixed"}; m2["inertia_relief"] = False
    r2 = solve(m2, buckling=False)
    dy = r2.u[6 * i["SR530"] + 1] - r2.u[6 * i["SL530"] + 1]
    out["torsion_Nm_per_deg"] = float(TORSION_F * 0.230 / np.degrees(dy / 230.0))
    out["model"] = fm
    out["u_carry"] = r.u.reshape(-1, 6)[:, :3]
    out["node_ids"] = r.node_ids
    return out


def frame_cg(cand: dict, mr: dict, model19: dict) -> dict:
    """Mass centroid (y aft, z up) of the concept frame at 19 in vs today's printed body + the same crown."""
    import trimesh
    pts, ws = [], []
    for md in model19["members"]:
        a, b = md["nodes"]
        if md["group"] in ("lumbar_plate_shear",):
            continue
        p = (np.array(model19["nodes"][a]) + np.array(model19["nodes"][b])) / 2
        pts.append(p); ws.append(md.get("mass_g") or 0.0)
    # tubes by group mass, placed at member midpoints in proportion to length
    lens = []
    for md in model19["members"]:
        a, b = md["nodes"]
        lens.append(float(np.linalg.norm(np.subtract(model19["nodes"][b], model19["nodes"][a]))))
    groups_mass = {"stay": mr["tubes"]["stays (2)"], "mid_bar": mr["tubes"]["mid bar"],
                   "upper_bar": mr["tubes"]["upper bar"], "crown_leg": CROWN["crown legs (2, rev C +2 UD)"],
                   "crown_top_bar": CROWN["crown top bar (rev C +1 UD)"],
                   "crown_spine": CROWN["crown spine tube (rev C +1 UD)"],
                   "lumbar_plate": mr["groups"]["lumbar pan + pad-up"], "branch": mr["tubes"].get("branch tubes (2)", 0.0)}
    P, W = [], []
    for g, mass in groups_mass.items():
        sel = [(k, md) for k, md in enumerate(model19["members"]) if md["group"].startswith(g)]
        Lt = sum(lens[k] for k, _ in sel) or 1.0
        for k, md in sel:
            a, b = md["nodes"]
            P.append((np.array(model19["nodes"][a]) + np.array(model19["nodes"][b])) / 2)
            W.append(mass * lens[k] / Lt)
    n = model19["nodes"]
    lump = {"SL0": 0.5, "SR0": 0.5}
    for nd in mr["nodes"]:
        tot = nd["qty"] * (nd["g_each"] + nd["bond_g"] + nd.get("wrap_g", 0.0))
        if nd["name"].startswith("foot"):
            locs = ["SL0", "SR0"]
        elif nd["name"].startswith("mid"):
            locs = ["SL330", "SR330"]
        elif nd["name"].startswith("upper"):
            locs = ["SL520", "SR520"]
        elif nd["name"].startswith("stay-top"):
            locs = ["SL530", "SR530"]
        elif nd["name"].startswith("hip"):
            locs = ["HP"]
        elif nd["name"].startswith("branch"):
            locs = ["SL330", "SR330"]
        else:
            z = float(nd["name"].split("z")[1].split()[0])
            P += [np.array([-115.0, -5.0, z]), np.array([115.0, -5.0, z])]
            W += [tot / 2, tot / 2]
            continue
        for l in locs:
            P.append(np.array(n[l])); W.append(tot / len(locs))
    rest = mr["groups"]["crown + torso adjust (unchanged)"] - sum(groups_mass[k] for k in ("crown_leg", "crown_top_bar", "crown_spine"))
    P.append(np.array(n["UB1"])); W.append(rest)
    P.append(np.array(n["HP"])); W.append(mr["groups"]["Ti pivot mount + inserts"])
    if mr["groups"]["printed skin (non-structural)"]:
        P.append(np.array([0.0, -5.0, 300.0])); W.append(mr["groups"]["printed skin (non-structural)"])
    P, W = np.array(P), np.array(W)
    cg = (P * W[:, None]).sum(0) / W.sum()
    body = trimesh.load(REPO_ROOT / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    bc = body.center_mass if body.is_volume else body.centroid
    crown_g = sum(groups_mass[k] for k in ("crown_leg", "crown_top_bar", "crown_spine")) + rest
    ccg = np.array(n["UB1"]) * 0 + np.array([0.0, 0.0, 560.0])
    today = (np.asarray(bc) * TODAY["printed_body_g"] + ccg * crown_g + np.array(n["HP"]) * 25.0) / (
        TODAY["printed_body_g"] + crown_g + 25.0)
    return {"cg": [float(v) for v in cg], "mass_g": float(W.sum()), "today_cg": [float(v) for v in today],
            "today_body_centroid": [float(v) for v in bc]}


def system_cg_shift(frame_g: float, frame_cg, today_cg, load_kg: float = 68.0) -> dict:
    """Loaded-pack CG (68 kg in the bag at rev C 205 mm aft, z 550) with today's frame vs the concept."""
    load = np.array([0.0, 205.0, 550.0])
    W0, W1 = TODAY["frame_g"] / 1000, frame_g / 1000
    c0 = (load * load_kg + np.asarray(today_cg) * W0) / (load_kg + W0)
    c1 = (load * load_kg + np.asarray(frame_cg) * W1) / (load_kg + W1)
    return {"dy_mm": float(c1[1] - c0[1]), "dz_mm": float(c1[2] - c0[2]), "mass_saved_kg": W0 - W1}


# ----------------------------------------------------------------------------- sizing
def size(name: str, log=print, procs: int = 3) -> dict:
    """Greedy downsizing from the v2 sections: try each lighter stock option, keep it when every rev C check and
    fatigue still pass (>= 1.0) on 15 / 19 / 23 in."""
    base = candidate(name)
    best = evaluate(base, procs)
    # repair: rev C loads the upper bar harder than rev B (v2 sized at 1.05 on rev B with UD x4); if the base
    # fails, step the failing tube up before any downsizing
    ups = {"upper_bar": ("ubar", [(22, "RW45", 7), (25, "RW45", 6)]), "stays": ("stay", [(20, "RW0", 4)]),
           "frame buckling": (("branch", [{"sec": (16, "RW45", 4)}, {"sec": (18, "RW45", 4)}]) if base.get("branch")
                              else ("stay", [(20, "RW0", 4)]))}
    for _ in range(3):
        if best["summary"]["pass"]:
            break
        name_fail = best["summary"]["min_strength"][1]
        key = next((v for k, v in ups.items() if k in name_fail), None)
        if not key or not key[1]:
            break
        trial = evaluate({**best["cand"], key[0]: key[1].pop(0)}, procs)
        log(f"[{name}] repair {key[0]}: strength {trial['summary']['min_strength'][0]:.2f}")
        best = trial
    log(f"[{name}] base: strength {best['summary']['min_strength'][0]:.2f} fatigue "
        f"{best['summary']['min_fatigue'][0]:.2f} ({best['seconds']:.0f} s)")
    tried = [best]
    steps = [("stay", (20, "RW0", 2)), ("stay", (20, "RW45", 2)), ("bar", (16, "RW45", 4)), ("bar", (16, "RW45", 3)),
             ("ubar", (22, "RW45", 5)), ("ubar", (22, "RW45", 4)), ("pan_t", 1.2)]
    if base.get("branch"):
        steps.append(("pan_t", 1.0))
    for key, val in steps:
        cur = best["cand"]
        if cur.get(key) == val:
            continue
        trial = evaluate({**cur, key: val}, procs)
        tried.append(trial)
        ok = trial["summary"]["pass"]
        log(f"[{name}] {key} -> {val}: strength {trial['summary']['min_strength'][0]:.2f} "
            f"({trial['summary']['min_strength'][1]}), fatigue {trial['summary']['min_fatigue'][0]:.2f} "
            f"({trial['summary']['min_fatigue'][1]}) {'KEEP' if ok else 'reject'}")
        if ok:
            best = trial
    return {"best": best, "tried": [{"cand": t["cand"], "min_strength": t["summary"]["min_strength"],
                                     "min_fatigue": t["summary"]["min_fatigue"], "pass": t["summary"]["pass"]}
                                    for t in tried]}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items() if k not in ("model", "u_carry", "node_ids")}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def run(log=print, procs: int = 3) -> dict:
    t0 = time.time()
    out = {"date": "2026-11-09", "standard": "HA-LS-1 rev C", "tau_pa_design_mpa": TAU_PA_MPA, "lug": LUG,
           "today": TODAY, "v2_tube": V2_TUBE, "concepts": {}}
    sized = {}
    # NODE (printed sockets) fails the bond-peak rule at the v2 sections, so it is evaluated, not downsized
    node = evaluate(candidate("NODE"), procs)
    sized["NODE"] = {"best": node, "tried": []}
    log(f"[NODE] strength {node['summary']['min_strength'][0]:.2f} ({node['summary']['min_strength'][1]})")
    for name in ("TENDON", "BRANCH"):
        sized[name] = size(name, log, procs)
    # SKIN = the TENDON structure as sized (the skin carries nothing), so its checks are TENDON's
    skin_c = {**sized["TENDON"]["best"]["cand"], "name": "SKIN", "skin_t": CONCEPTS["SKIN"]["skin_t"]}
    sized["SKIN"] = {"best": {**sized["TENDON"]["best"], "cand": skin_c}, "tried": []}
    for name, sz in sized.items():
        best = sz["best"]
        cand = best["cand"]
        st = stiffness(cand)
        m19 = st["model"]
        mr = mass_rollup(cand, m19)
        n_parts = sum(n["qty"] for n in mr["nodes"]) + (12 if cand.get("skin_t") else 0)
        cg = frame_cg(cand, mr, m19)
        out["concepts"][name] = {
            "label": CONCEPTS[name]["label"], "look": CONCEPTS[name]["look"], "cand": cand,
            "summary": best["summary"], "tried": sz["tried"], "mass": mr, "print_h": print_hours(mr, n_parts),
            "n_printed_parts": n_parts, "cost": cost(cand, mr),
            "stiffness": {"carry_dy_mm": st["carry_dy_mm"], "torsion_Nm_per_deg": st["torsion_Nm_per_deg"]},
            "cg": cg, "system_cg": system_cg_shift(mr["frame_g"], cg["cg"], cg["today_cg"]),
            "pack_g": PACK_AFTER_ABC_G - TODAY["frame_g"] + mr["frame_g"],
        }
        log(f"{name}: frame {mr['frame_g']:.0f} g, +spreader {mr['frame_spreader_g']:.0f} g, "
            f"strength {best['summary']['min_strength'][0]:.2f}, fatigue {best['summary']['min_fatigue'][0]:.2f}")
        out["concepts"][name]["_model19"] = m19
        out["concepts"][name]["_u"] = st["u_carry"]
    out["seconds"] = time.time() - t0
    return out


def save(ctx: dict) -> Path:
    CONCEPT_DIR.mkdir(parents=True, exist_ok=True)
    clean = {**ctx, "concepts": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                                 for k, v in ctx["concepts"].items()}}
    RESULTS.write_text(json.dumps(_jsonable(clean), indent=1))
    return RESULTS


def main():
    ctx = run()
    save(ctx)
    from .frame_light2_report import write_all
    write_all(ctx)


if __name__ == "__main__":
    main()
