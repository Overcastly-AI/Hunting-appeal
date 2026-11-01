"""Standard pack-frame load cases (docs/CONTRACTS.md §2) plus meat-hauling cases.

Coordinate system used by ``frames.py`` and here:
  x = lateral (+ wearer's right), y = fore-aft (+ AFT, away from the wearer's back, toward the bag),
  z = up. The frame plane is roughly y = 0; the wearer is on the -y side.

A frame model handed to these cases must carry ``model["groups"]`` with node-id lists:
  hipbelt, shoulder, lifter, shelf_pivot, shelf_strap, lash, foot_left, foot_right, and
  optionally bag (absent in frame-only haul mode).

ASSUMPTIONS (all overridable through ``pack_standard(**overrides)``):
- g = 9.80665 m/s^2. Design load 68 kg (150 lb).
- Pack load reaches the frame as nodal forces at the attachment nodes, with the load's CG offset
  aft of the frame plane carried by rigid-link equivalent nodal moments (bag) or by an explicit
  shelf/strap/lashing force resolution (shelf cases). Frame self-weight (<0.5% of load) ignored.
- Body interface = linear springs in global axes. Hipbelt (wrap + lumbar pad): kx 20, ky 30,
  kz 40 N/mm total; shoulder harness at the yoke: kx 4, ky 8, kz 10 N/mm; load lifters at the
  stay tops: ky 6, kz 3 N/mm. The shoulder+lifter vertical stiffness is then rescaled
  iteratively so the hipbelt carries 80 % (shoulders 20 %) of the vertical load.
- Dynamic factor 2.5 g for drop, side-hill, set-down, meat-shelf and tall-load cases (CLAUDE.md
  rule), 1.0 g static carry (also basis for the 1.2 g fatigue check), overload haul 91 kg x 1.5 g
  with required SF 1.5.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .frame import G_ACC, Result, solve

DEFAULT_SPRINGS = {
    "hipbelt": (20.0, 30.0, 40.0),
    "shoulder": (4.0, 8.0, 10.0),
    "lifter": (0.0, 6.0, 3.0),
}


@dataclass
class LoadCase:
    name: str
    description: str
    load_kg: float
    g_factor: float
    required_sf: float = 2.0
    kind: str = "worn"              # "worn" (spring supports) | "setdown" (inertia relief)
    placement: str = "bag"          # "bag" | "meat_shelf" | "tall_load"
    cg_aft_mm: float = 150.0        # CG offset aft of the frame plane
    lateral_tilt_deg: float = 0.0   # gravity tilt about y (side-hill)
    slack_shoulder: str | None = None   # "left"/"right": that strap/lifter at 25 % stiffness
    hip_share: float = 0.80
    springs: dict = field(default_factory=lambda: dict(DEFAULT_SPRINGS))
    params: dict = field(default_factory=dict)
    buckling: bool = True

    @property
    def W(self) -> float:
        """Weight x dynamic factor (N)."""
        return self.load_kg * G_ACC * self.g_factor

    # ------------------------------------------------------------------ loads
    def _loads(self, model) -> dict:
        g = model["groups"]
        nodes = model["nodes"]
        W = self.W
        tilt = np.radians(self.lateral_tilt_deg)
        Fdir = np.array([np.sin(tilt), 0.0, -np.cos(tilt)])
        loads: dict = {}

        def add(nid, f):
            loads.setdefault(nid, np.zeros(6))
            loads[nid][: len(f)] += f

        placement = self.placement
        if placement == "bag" and not g.get("bag"):
            placement = "meat_shelf"   # frame-only haul mode: no bag
        if placement == "bag":
            bag = g["bag"]
            w = np.array(model.get("bag_weights", [1.0] * len(bag)), float)
            if self.params.get("downhill_bias"):   # load slumps to the downhill (+x) side
                xs = np.array([nodes[n][0] for n in bag])
                w = w * (1 + self.params["downhill_bias"] * np.sign(xs))
            w /= w.sum()
            couple = model.get("bag_couple")
            for nid, wi in zip(bag, w):
                F = W * wi * Fdir
                if couple:      # forces only; the CG-offset moment is resolved as a couple below
                    add(nid, F)
                else:
                    r = np.array([0.0, self.cg_aft_mm, 0.0])
                    add(nid, np.r_[F, np.cross(r, F)])
            if couple:
                # bag CG aft of the frame: top tabs pull aft (+y), bottom bears forward (-y)
                top, bot = couple["top"], couple["bottom"]
                zt = np.mean([nodes[n][2] for n in top])
                zb = np.mean([nodes[n][2] for n in bot])
                H = W * np.cos(tilt) * self.cg_aft_mm / (zt - zb)
                for nid in top:
                    add(nid, np.array([0.0, H / len(top), 0.0]))
                for nid in bot:
                    add(nid, np.array([0.0, -H / len(bot), 0.0]))
        elif placement == "meat_straps":
            self._meat_straps(model, W, tilt, add)
        elif placement in ("meat_shelf", "tall_load"):
            piv, P = g["shelf_pivot"], W * np.cos(tilt)
            e = self.cg_aft_mm
            if placement == "meat_shelf":
                # Rigid shelf of depth d hinged at the pivots, tip held by straps running up to the
                # shelf_strap anchors. Load P at e aft: strap vertical Tv = P e / d.
                anc = g["shelf_strap"]
                d = self.params.get("shelf_depth_mm", model.get("shelf_depth_mm", 2.0 * e))
                z_p = np.mean([nodes[n][2] for n in piv])
                z_a = np.mean([nodes[n][2] for n in anc])
                h = z_a - z_p
                Tv = P * e / d
                for nid in anc:
                    add(nid, np.array([0.0, Tv * d / h, -Tv]) / len(anc))
                for nid in piv:
                    add(nid, np.array([0.0, -Tv * d / h, -(P - Tv)]) / len(piv))
            else:
                # Tall load: weight sits on the shelf pivots; overturning moment P*e is reacted by
                # near-horizontal lashing at the upper 'lash' nodes (pulled aft) and the pivots
                # bearing forward (toward the wearer).
                anc = g[self.params.get("lash_group", "lash")]
                z_p = np.mean([nodes[n][2] for n in piv])
                z_a = np.mean([nodes[n][2] for n in anc])
                H = P * e / (z_a - z_p)
                for nid in anc:
                    add(nid, np.array([0.0, H, 0.0]) / len(anc))
                for nid in piv:
                    add(nid, np.array([0.0, -H, -P]) / len(piv))
            if tilt:
                for nid in piv:
                    add(nid, np.array([W * np.sin(tilt), 0, 0]) / len(piv))
        return loads

    def _meat_straps(self, model, W, tilt, add):
        """HA-LS-1 rev B meat load (owner 2026-11-01: NO meat shelf). Meat (boned in game bags or a
        bone-in quarter) rides INSIDE the bag, cinched against the frame face by internal straps.

        Load path on the frame (statically determinate resolution, ASSUMPTIONS in load_standard.md):
        - vertical P = W cos(tilt): ``floor_share`` into the bottom strap pair (the bag floor is sewn to
          it and slings the meat), the rest by strap/face friction into the strap anchors (equal split);
        - overturning P*e (CG ``cg_aft_mm`` aft of the frame axis): a couple of aft (+y) strap pull H at
          the ``upper_groups`` anchors and forward (-y) contact pressure on the frame face, triangular
          over ``face_z`` (peak at the bottom); strap pulls in proportion to their lever above the
          discrete pressure centroid z_p (sum H_i (z_i - z_p) = P e);
        - strap cinch pretension ``pretension_n`` per anchor (aft), balanced by uniform face pressure.
        Groups: strap_bottom, strap_lumbar, strap_mid, strap_upper, meat_face.
        """
        g, nodes = model["groups"], model["nodes"]
        pr = self.params
        P = W * np.cos(tilt)
        e = self.cg_aft_mm
        bottom = g["strap_bottom"]
        levels = [n for k in ("strap_lumbar", "strap_mid", "strap_upper") for n in g.get(k, [])]
        upper = [n for k in pr.get("upper_groups", ("strap_mid", "strap_upper")) for n in g.get(k, [])]
        face = list(g["meat_face"])
        fs = float(pr.get("floor_share", 0.5))
        for nid in bottom:
            add(nid, np.array([0.0, 0.0, -fs * P / len(bottom)]))
        for nid in levels:
            add(nid, np.array([0.0, 0.0, -(1 - fs) * P / len(levels)]))
        z0, z1 = pr.get("face_z", (50.0, 330.0))
        zf = np.array([nodes[n][2] for n in face])
        wf = np.clip((z1 - zf) / (z1 - z0), 0.0, None) + 1e-9
        wf = np.where((zf >= z0 - 1e-6) & (zf <= z1 + 1e-6), wf, 0.0)
        wf /= wf.sum()
        zp = float(wf @ zf)
        zu = np.array([nodes[n][2] for n in upper])
        if pr.get("proportional", True):
            # straps share the overturning couple in proportion to their lever above the pressure centroid
            lev = np.clip(zu - zp, 1.0, None)
            Hn = P * e * lev / np.sum(lev ** 2)
        else:
            Hn = np.full(len(upper), P * e / (zu.mean() - zp) / len(upper))
        H = float(Hn.sum())
        for nid, h_ in zip(upper, Hn):
            add(nid, np.array([0.0, h_, 0.0]))
        T0 = float(pr.get("pretension_n", 150.0))
        anchors = levels + list(bottom)
        for nid in anchors:
            add(nid, np.array([0.0, T0, 0.0]))
        inface = (zf >= z0 - 1e-6) & (zf <= z1 + 1e-6)
        for nid, w, ok in zip(face, wf, inface):
            f = -H * w - (T0 * len(anchors) / inface.sum() if ok else 0.0)
            if f:
                add(nid, np.array([0.0, f, 0.0]))
        if tilt:
            for nid in anchors:
                add(nid, np.array([W * np.sin(tilt) / len(anchors), 0.0, 0.0]))

    # ------------------------------------------------------------------ supports
    def _supports(self, model, sh_scale: float = 1.0) -> dict:
        g = model["groups"]
        nodes = model["nodes"]
        sup = {}
        springs = model.get("springs") or self.springs     # a frame may define its own body springs
        for grp, kk in springs.items():
            if self.params.get("no_hipbelt") and grp in ("hipbelt", "lumbar_pad"):
                continue
            src = grp
            if grp == "lifter" and self.params.get("lifter_group"):
                src = self.params["lifter_group"]
            ids = g.get(src, [])
            if not ids:
                continue
            kx, ky, kz = kk
            if grp in ("shoulder", "lifter"):
                kz *= sh_scale
            for nid in ids:
                f = 1.0
                if self.slack_shoulder and grp != "hipbelt":
                    side = "left" if nodes[nid][0] < 0 else "right"
                    f = 0.25 if side == self.slack_shoulder else 1.0
                k = np.array([kx, ky, kz, 0, 0, 0]) * f / len(ids)
                if nid in sup:
                    sup[nid]["spring"] = list(np.add(sup[nid]["spring"], k))
                else:
                    sup[nid] = {"spring": list(k)}
        return sup

    def build_model(self, frame_model: dict, sh_scale: float = 1.0) -> dict:
        m = copy.copy(frame_model)
        m["loads"] = {k: list(v) for k, v in self._loads(frame_model).items()}
        if self.kind == "setdown":
            m["supports"] = {}
            m["inertia_relief"] = True
            # load mass lumped at the nodes that carry it in the carry configuration
            carry = LoadCase("tmp", "", self.load_kg, 1.0, placement=self.placement,
                             cg_aft_mm=self.cg_aft_mm)
            base = carry._loads(frame_model)
            fz = {k: -v[2] for k, v in base.items()}
            tot = sum(fz.values())
            m["masses"] = {k: self.load_kg * v / tot for k, v in fz.items() if v > 0}
            foot = frame_model["groups"]["foot_left"][0]
            F = self.W
            mu = self.params.get("friction", 0.2)
            m["loads"] = {foot: [mu * F, 0.0, F, 0, 0, 0]}
        else:
            m["supports"] = self._supports(frame_model, sh_scale)
            m["inertia_relief"] = False
        return m

    def hip_fraction(self, res: Result, model: dict) -> float:
        hip = set(model["groups"]["hipbelt"])
        rz = {k: v[2] for k, v in res.reactions.items()}
        tot = sum(rz.values())
        return sum(v for k, v in rz.items() if k in hip) / tot if tot else np.nan

    def run(self, frame_model: dict, name_suffix: str = "") -> Result:
        sh = 1.0
        name = self.name + name_suffix
        if self.kind == "setdown":
            m = self.build_model(frame_model)
            res = solve(m, buckling=False, name=name)
        elif self.params.get("no_hipbelt"):
            m = self.build_model(frame_model, sh)
            res = solve(m, buckling=self.buckling, name=name)
            res.meta["hip_fraction"] = 0.0
        else:
            for _ in range(8):
                m = self.build_model(frame_model, sh)
                res = solve(m, buckling=False, name=name)
                hf = self.hip_fraction(res, frame_model)
                if abs(hf - self.hip_share) < 0.005:
                    break
                ratio = (hf / max(1 - hf, 1e-6)) / (self.hip_share / (1 - self.hip_share))
                sh = float(np.clip(sh * np.clip(ratio, 0.1, 10.0), 1e-3, 1e3))
            if self.buckling:
                res = solve(m, buckling=True, name=name)
            res.meta["hip_fraction"] = self.hip_fraction(res, frame_model)
            res.meta["shoulder_kz_scale"] = sh
        res.meta.update({"case": self, "required_sf": self.required_sf, "W_N": self.W})
        return res


def pack_standard(design_load_kg: float = 68.0, overload_kg: float = 91.0, **overrides) -> list[LoadCase]:
    """Standard pack cases. ``overrides`` = {case_name: {field: value}} to tweak any case."""
    W = design_load_kg
    cases = [
        LoadCase("static_carry", f"{W:g} kg carried at 1.0 g in the bag, CG 150 mm aft; "
                 "hipbelt 80 % / shoulders 20 %.", W, 1.0),
        LoadCase("drop_2p5g", f"{W:g} kg x 2.5 g (stumble / drop-step), bag load, CG 150 mm aft.", W, 2.5),
        LoadCase("side_hill_torsion", f"{W:g} kg x 2.5 g with gravity tilted 25 deg laterally, load "
                 "biased 30 % to the downhill side, downhill shoulder strap + lifter slack (25 % "
                 "stiffness) -> frame torsion.", W, 2.5, lateral_tilt_deg=25.0,
                 slack_shoulder="right", params={"downhill_bias": 0.3}),
        LoadCase("single_stay_setdown", f"Pack dropped onto the left stay foot: impact {W:g} kg x "
                 "2.5 g vertical + 0.2 friction lateral at the foot, balanced by the load's "
                 "d'Alembert inertia (inertia relief, free-free).", W, 2.5, kind="setdown"),
        LoadCase("meat_shelf_heavy_low", f"{W:g} kg x 2.5 g of meat on the load shelf between "
                 "frame and bag, CG 120 mm aft, shelf tip strapped to mid-frame anchors. CRITICAL "
                 "(primary mission).", W, 2.5, placement="meat_shelf", cg_aft_mm=120.0,
                 params={"shelf_depth_mm": 240.0}),
        LoadCase("tall_load", f"{W:g} kg x 2.5 g bone-in quarter standing on the shelf, CG high and "
                 "250 mm aft, top lashed to the upper frame; large bending at the hipbelt junction "
                 "and load-lifter tension. CRITICAL.", W, 2.5, placement="tall_load", cg_aft_mm=250.0),
        LoadCase("overload_haul", f"{overload_kg:g} kg (200 lb) meat haul on the shelf, 1.5 g "
                 "walking factor, CG 120 mm aft; required SF 1.5.", overload_kg, 1.5,
                 required_sf=1.5, placement="meat_shelf", cg_aft_mm=120.0,
                 params={"shelf_depth_mm": 240.0}),
    ]
    for c in cases:
        for k, v in overrides.get(c.name, {}).items():
            setattr(c, k, v)
    return cases


def pack5200_cases(design_load_kg: float = 68.0, overload_kg: float = 91.0, **overrides) -> list[LoadCase]:
    """pack_standard + ``tall_load_posts`` (extension posts fitted: lashing and lifters on the post
    bar, the R-10 tall-load mode of designs/pack_5200/DESIGN.md). Needs groups lash_posts/lifter_posts."""
    cases = pack_standard(design_load_kg, overload_kg, **overrides)
    W = design_load_kg
    cases.append(LoadCase("tall_load_posts", f"{W:g} kg x 2.5 g tall load (antlers / quarter) lashed to the "
                          "extension-post bar 220 mm above the crown, CG 250 mm aft; lifters moved to the post bar.",
                          W, 2.5, placement="tall_load", cg_aft_mm=250.0,
                          params={"lash_group": "lash_posts", "lifter_group": "lifter_posts"}))
    cases.append(LoadCase("hipbelt_off_abuse", f"{W:g} kg x 1.5 g with the hipbelt unbuckled (creek crossing): "
                          "100 % on the shoulders + lifters; abuse case, required SF 1.0 (no damage, no slip). "
                          "Source: geometry.yaml crown_retention.", W, 1.5, required_sf=1.0,
                          cg_aft_mm=180.0, params={"no_hipbelt": True}))
    for c in cases[-2:]:
        for k, v in overrides.get(c.name, {}).items():
            setattr(c, k, v)
    return cases


def run_cases(frame_model: dict, cases: list[LoadCase] | None = None) -> dict[str, Result]:
    cases = cases or pack_standard()
    return {c.name: c.run(frame_model) for c in cases}
