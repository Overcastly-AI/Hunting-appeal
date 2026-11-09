"""CORRIE rev B.2 for the viz3d / Cycles renders (2026-11-09): CORRIE B.1 (``corrie_b1``) with the owner-approved
weight cuts of ``designs/pack_5200/concepts/corrie.py`` spec B.2 and three render fixes.

B.2 content (from corrie.py, nothing typed here): roll-top hem body solid (SH-03 deleted, B-2), 2.7 L pouch 280 x 190
x 60 with a solid top and a camo pull tab (B-3/4/5), phone pocket sewn to the left strap (B-7, no G-hook wraps drawn
in B.1 either). The built-in viz3d CORRIE (``corrie.corrie_parts``) follows ``corrie.SPEC``.

Render fixes (visual only):
* wings: one smooth taut panel (2D relaxation, capsule obstacle) and the camo bar 0.6 mm proud (``corrie._wing``
  ``clean=True``); B.1's left wing over the scope sleeve showed a torn, z-fighting camo bar;
* mannequin: a clean retail display form (one lofted torso + neck + cap, no arms, on a stand) in place of the clay
  figure with capsule arms whose shoulder / elbow joints intersected crudely;
* belt B: pillow section (crowned outer face, thin bound edges, quilt channels that follow the crown), so it reads as a
  padded belt (``corrie_b1.belt_b_parts(padded=True)``).
"""
from __future__ import annotations

import numpy as np

from . import geom as G
from .corrie import BAGM, Part, Skin, _concept, _tripod, _tripod_axis, _wing, sim_skin
from .corrie_b1 import BELT_DROP, WING_L_DROP, bag_side_parts, belt_b_parts, belt_pocket_parts, pelvis

WING_R_NAMES = ("corrie_wing_R", "corrie_wing_bar_R", "corrie_wing_straps_R", "corrie_wing_hw_R",
                "corrie_wing_R_tripod", "corrie_wing_bar_R_tripod", "corrie_wing_straps_R_tripod",
                "corrie_wing_hw_R_tripod")


def mannequin_display(params: dict) -> list:
    """Retail display form: the viz3d mannequin's torso section (model.Body RINGS), lofted in one piece through the
    neck to a flat-domed neck cap (no seam, no intersecting primitives), hips closed with a rounded base, on a 25 mm
    satin pole and a 340 mm round base whose underside is the old figure's foot level (same floor, same framing)."""
    from .model import DEFAULT_PARAMS, IN, Body, deep_merge
    p = deep_merge(DEFAULT_PARAMS, params or {})
    pl = pelvis(params)
    out = []
    M = 96
    for tin in p["torsos_in"]:
        body = Body(tin * IN, pl["hz"], pl["BU"], pl["BH"])
        T, hz, c7 = body.T, body.hz, body.c7
        fs = np.array([r[0] for r in body.RINGS])
        zs = hz + T * np.linspace(-0.40, fs[-1], 72)              # cut at the upper hip (no tapered crotch)
        rings = []
        a0, b0 = (float(v) for v in body.ab(zs[0]))
        yb0 = float(body.yc(zs[0]))
        zb = zs[0] - 0.03 * T                                     # torso form cut flat just below the hips
        for z, k in ((zb - 7.0, 0.90), (zb - 4.5, 0.965), (zb - 2.0, 0.99)):   # small bevel onto the cap plate
            rings.append(G.superellipse_ring(a0 * k, b0 * k, 3.0, 2.4, M=M, cy=yb0, z=z))
        for z in np.linspace(zb, zs[0], 6)[:-1]:
            rings.append(G.superellipse_ring(a0, b0, 3.0, 2.4, M=M, cy=yb0, z=z))
        for z in zs:
            a, b = body.ab(z)
            rings.append(G.superellipse_ring(a, b, 3.0, 2.4, M=M, cy=float(body.yc(z)), z=z))
        # neck: from the torso's last ring (55 x 50) up to c7 + 80, blending the centre to the old neck axis
        z_top = zs[-1]
        y_top = float(body.yc(z_top))
        ycn = float(body.yc(c7)) + 10 - 8
        a1, b1 = (float(v) for v in body.ab(z_top))
        zn = np.linspace(z_top + 12, c7 + 80, 9)
        for i, z in enumerate(zn):
            w = (i + 1) / len(zn)
            s = 0.5 - 0.5 * np.cos(np.pi * w)
            rings.append(G.superellipse_ring(a1 + (47 - a1) * s, b1 + (45 - b1) * s, 2.4, 2.2, M=M,
                                             cy=y_top + (ycn - y_top) * s, z=z))
        for ph in np.linspace(0.25, np.pi / 2 * 0.9, 6):         # flat-domed cap (dress-form neck cap)
            k = np.cos(ph)
            rings.append(G.superellipse_ring(47 * k, 45 * k, 2.4, 2.2, M=M, cy=ycn, z=c7 + 80 + 14 * np.sin(ph)))
        form = G.loft(np.array(rings), pole_start=[0, yb0, zb - 7.5], pole_end=[0, ycn, c7 + 94.5])
        floor_z = hz - 0.30 * T - 360 - 66 + 8
        cap = G.superellipsoid([0, yb0, zb - 9.0], (a0 * 0.86, b0 * 0.86, 3.0), e_ns=0.2, e_ew=0.75, nu=96, nv=12)
        collar = G.capsule_between([0, yb0, zb - 10], [0, yb0, zb - 40], 19.0)
        pole = G.capsule_between([0, yb0, zb - 30], [0, yb0, floor_z + 10], 12.5)
        base = G.superellipsoid([0, yb0, floor_z + 6], (170, 170, 6), e_ns=0.15, e_ew=1.0, nu=96, nv=16)
        out.append(Part(f"mannequin@t{tin:g}", form, "clay", "mannequin", torso=tin,
                        label=f"Display form, {tin:g} in torso"))
        out.append(Part(f"mannequin_stand@t{tin:g}", G.concat([cap, collar, pole, base]), "hardware", "mannequin",
                        torso=tin, label="Display stand"))
    return out


def right_wing_parts() -> list:
    """The right wing (plain and over the tripod) rebuilt with the clean panel; same names / variants as corrie.py."""
    BC, CO = _concept()
    c = CO.make()
    S = Skin(sim_skin())
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    tri_geo = _tripod_axis(S, a_of, yf_of, yb_of)
    parts = []
    for trip in (False, True):
        w, hem, bar, st, hw = _wing(S, 1, a_of, yf_of, yb_of, tri_geo if trip else None, clean=True)
        var = "lid" if trip else "nolid"
        tag = f"R{'_tripod' if trip else ''}"
        ex = (120, 200, 0)
        parts += [Part(f"corrie_wing_{tag}", G.concat([w, hem]), "tpu", "bag", modes=BAGM, explode=ex, floats=True,
                       variant=var, label="Side compression wing M-01 200 x 450 (330D, hemmed)"),
                  Part(f"corrie_wing_bar_{tag}", bar, "camo", "bag", modes=BAGM, explode=ex, floats=True, variant=var,
                       label="Wing leading-edge bar SH-06 (camo)"),
                  Part(f"corrie_wing_straps_{tag}", G.concat(st), "webbing", "bag", modes=BAGM, explode=ex, floats=True,
                       variant=var),
                  Part(f"corrie_wing_hw_{tag}", G.concat(hw), "aluminium", "bag", modes=BAGM, explode=ex, floats=True,
                       variant=var, label="G-hooks + ladder locks (HAUL family)")]
    _ = _tripod
    return parts


def corrie_b2_pack(params: dict, size: str | None = None):
    from .corrie import corrie_pack
    BC, CO = _concept()
    assert CO.SPEC == "B.2", "render B.2 with corrie.SPEC = B.2 (unset CORRIE_SPEC)"
    pack = corrie_pack(params)
    drop = set(BELT_DROP) | set(WING_L_DROP) | set(WING_R_NAMES)
    keep = [p for p in pack.parts if p.name not in drop and not p.name.startswith("mannequin@")]
    bparts, info = belt_b_parts(params, size, padded=True)
    pack.parts = (keep + mannequin_display(params) + right_wing_parts() + bparts + belt_pocket_parts(info)
                  + bag_side_parts(pack, params, clean=True))
    pack.metrics["bag_type"] = "corrie_b2"
    pack.metrics["spec"] = CO.SPEC
    pack.metrics["belt_b"] = {k: v for k, v in info.items() if k in ("size", "wing_len", "beta_deg", "circ_in")}
    return pack
