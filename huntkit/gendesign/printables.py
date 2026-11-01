"""Printable crown hardware (toothed rack, spring pawl, pulley webbing guides), two-tier, plus the
print README / settings sheet and cost model for everything under designs/pack_5200/print/.

Geometry source: designs/pack_5200/geometry.yaml frame.crown_retention (rack pitch 4 mm, 2 engaged
teeth, rack width 20 mm, travel 203.2 mm; 3:1 pulley with 25 mm webbing, guides A/C on the lumbar
plate and B on the spine bottom). Profiles are extruded (watertight by construction).
"""
from __future__ import annotations

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from huntkit.fea.materials_bridge import get_material

# ---------------------------------------------------------------- cost / time model (ASSUMPTIONS, cited)
COST = {
    # JLC3DP 2026 guide: Ti SLM $5-20 per cm3; Titanium TC4 price cut 47 % on 2026-07-24.
    "ti_usd_cm3": 8.0, "ti_hip_usd_part": 25.0, "ti_ream_usd_bore": 12.0, "ti_min_usd_part": 30.0,
    # AlSi10Mg: no published per-cm3 rate found; ASSUMPTION ~1/4 of Ti per cm3, min charge $15.
    "al_usd_cm3": 2.0, "al_min_usd_part": 15.0, "al_ream_usd_bore": 8.0,
    # FDM PAHT-CF: ~ $80/kg filament (Bambu store class), 12 cm3/h effective (0.6 mm nozzle, <=100 mm/s TDS)
    "fdm_usd_kg": 80.0, "fdm_cm3_h": 12.0, "fdm_support_factor": 1.15,
}
LEAD = {"ti": "JLC3DP lists 96 h production for Ti SLM; + HIP batch (vendor, 1-2 weeks) + reaming: plan 3-4 weeks door to door",
        "al": "SLM AlSi10Mg 2-5 business days (PCBWay lists 2-3 d build) + stress relief + reaming: 1-2 weeks",
        "fdm": "same day on the owner's printer (dry filament 8-12 h at 80 C first)"}


def slm_cost(vol_mm3: float, bores: int, metal="ti") -> float:
    v = vol_mm3 / 1000
    if metal == "ti":
        return max(COST["ti_min_usd_part"], v * COST["ti_usd_cm3"]) + COST["ti_hip_usd_part"] + bores * COST["ti_ream_usd_bore"]
    return max(COST["al_min_usd_part"], v * COST["al_usd_cm3"]) + bores * COST["al_ream_usd_bore"]


def fdm_time_cost(vol_mm3: float, infill_eff: float = 1.0):
    v = vol_mm3 / 1000 * infill_eff * COST["fdm_support_factor"]
    rho = float(get_material("pa12_cf_fdm_paht").require("density_kg_m3"))
    return v / COST["fdm_cm3_h"], v * rho * 1e-3 * COST["fdm_usd_kg"] / 1000


# ---------------------------------------------------------------- geometry helpers
def extrude(poly, h) -> trimesh.Trimesh:
    m = trimesh.creation.extrude_polygon(poly, h)
    m.merge_vertices()
    return m


def rack_profile(length=230.0, pitch=4.0, depth=2.0, base=4.0, flank_deg=20.0, end_land=12.0):
    """Two-way symmetric trapezoidal rack teeth (pawl locks in both directions), profile in XZ."""
    pts = [(0, 0), (length, 0), (length, base)]
    n = int((length - 2 * end_land) // pitch)
    x0 = (length - n * pitch) / 2
    top = pitch * 0.35
    run = depth * np.tan(np.radians(flank_deg))
    seq = []
    for i in range(n):
        a = x0 + i * pitch
        bot = (pitch - top - 2 * run)
        seq += [(a, base), (a + bot / 2, base), (a + bot / 2 + run, base + depth),
                (a + bot / 2 + run + top, base + depth), (a + bot / 2 + 2 * run + top, base), (a + pitch, base)]
    seq = [p for p in seq]
    poly = Polygon([(0, 0), (length, 0), (length, base)] + seq[::-1] + [(0, base)])
    return poly.buffer(0), n


def toothed_rack(width=20.0, length=230.0):
    prof, n = rack_profile(length)
    m = extrude(prof, width)                      # profile in XY, extruded along Z (= rack width)
    # M3 screw holes (into the spine-plate inserts) at both end lands, through the base (along Y)
    for x in (6.0, length - 6.0):
        hole = trimesh.creation.cylinder(radius=1.65, height=40, sections=32)
        hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        hole.apply_translation([x, 2.0, width / 2])
        m = m.difference(hole)
    return m, {"teeth": n, "pitch_mm": 4.0, "engaged": 2}


def spring_pawl(width=12.0):
    """Pawl with 2 teeth matching the rack, Ø4 pivot, release-cord eye, spring tang."""
    arm = box(0, 0, 32, 8)
    hub = Point(4, 4).buffer(5.0, 48)
    teeth = []
    pitch, depth, top, run = 4.0, 2.0, 1.4, 2.0 * np.tan(np.radians(20))
    for i in range(2):
        a = 20 + i * pitch
        bot = pitch - top - 2 * run
        teeth.append(Polygon([(a, 0), (a + bot / 2, 0), (a + bot / 2 + run, -depth + 0.15), (a + bot / 2 + run + top, -depth + 0.15),
                              (a + bot / 2 + 2 * run + top, 0), (a + pitch, 0)]).buffer(0.01))
    eye = Point(30, 10).buffer(3.5, 32).union(box(26.5, 6, 33.5, 10))
    tang = box(8, 8, 12, 14)
    body = unary_union([arm, hub, eye, tang] + teeth)
    body = body.difference(Point(4, 4).buffer(2.05, 32)).difference(Point(30, 10.5).buffer(1.3, 24))
    body = body.buffer(0.3, 8).buffer(-0.3, 8)
    if body.geom_type != "Polygon":
        body = max(body.geoms, key=lambda g: g.area)
    return extrude(body, width), {}


def webbing_guide(webbing=25.0, kind="fixed"):
    """Pulley webbing guide for 25 mm webbing: rounded bearing bar (R 3) + slot + bonded/screwed base tab."""
    slot_w, slot_h = webbing + 2.0, 4.0
    outer = box(-slot_w / 2 - 4, -3.0, slot_w / 2 + 4, slot_h + 6.0).buffer(2.0, 16)
    slot = box(-slot_w / 2, 0, slot_w / 2, slot_h).buffer(1.2, 16)
    frame = outer.difference(slot)
    base = box(-slot_w / 2 - 8, -6, slot_w / 2 + 8, -2).buffer(1.0, 8) if kind == "fixed" else box(-slot_w / 2 - 4, -6, slot_w / 2 + 4, -2)
    body = unary_union([frame, base])
    if kind == "fixed":
        for x in (-slot_w / 2 - 5, slot_w / 2 + 5):
            body = body.difference(Point(x, -4).buffer(1.6, 24))
    return extrude(body, 8.0), {"webbing_mm": webbing}


def part_mass_g(mesh, material):
    return abs(mesh.volume) * float(get_material(material).require("density_kg_m3")) * 1e-6


def rack_check(material: str, width=20.0, root=2.0, engaged=2, req_n=1334.0 * 1.5):
    """Tooth root shear capacity (geometry.yaml lock method): engaged x width x root x tau.
    FDM: printed flat (tooth profile in the layer plane), tau = 0.577 x 0.8 x XY strength."""
    m = get_material(material)
    if m.get("tensile_strength_xy_mpa"):
        tau = 0.577 * 0.8 * float(m.require("tensile_strength_xy_mpa"))
    else:
        tau = 0.577 * float(m.get("yield_strength_design_mpa") or m.require("yield_strength_mpa"))
    cap = engaged * width * root * tau
    return {"tau_mpa": tau, "capacity_n": cap, "required_n": req_n, "sf_over_req": cap / req_n}
