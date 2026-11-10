"""Team A EVOLVE (bag design competition, 2026-11-10): CORRIE E, the evolution of CORRIE B.2.

    python designs/pack_5200/bag_comp/A/evolve.py            # geometry, ledger, mass, hours -> print + evolve_numbers.json

CORRIE B.2 (designs/pack_5200/concepts/corrie.py) is IMPORTED, never copied or edited. CORRIE E is CORRIE's build
on a re-shaped envelope plus a change ledger. Every ledger row is cut area x record gsm (data/materials) or a record
hardware mass, and hours come from the same beginner model (bag_concepts.HOURS, ASSUMPTION: rank, not plan).

What changes (write-up: designs/pack_5200/analysis/bag_comp_A.md; research: docs/research/bag_comp_A.md):

* E-1  ROUNDED AFT CORNERS, R 40 mm. The aft panels (U-surround, door, hinge band) wrap round the two vertical aft
       corners; the gusset | aft seam moves to the side tangent, so the gusset stays a flat straight-seamed panel and
       the wing-strap loops stay in that seam. Kills the hard box edge seen from behind (the owner's "boxy" complaint).
* E-2  SHOULDER TAPER: half-width 197 mm at the shoulder crease (z 631) to 185 mm at the collar seam. The silhouette
       narrows into the roll instead of a slab; it moves no load-zone width (IM1-IM3 are below z 631).
* E-3  CAMO TUB BASE: a 60 mm tub wall in camo-printed 500D runs round the three outer sides (floor up to z 95). It
       replaces CORRIE's two-layer camo chevron kick plate (SH-01a/b) with ONE layer, puts the camo where the wear
       is, and lifts the gusset | floor seam 60 mm off the bulging floor corner (the B-03 | B-05 hot seam of the
       CORRIE sims). Door sill raised from z 110 to z 130 to keep a 35 mm surround strip above the tub.
* E-4  HIP-REACH POCKETS (FP-L, FP-R): power-mesh pockets on the lower front corner of each wing, mouth angled
       forward. Left: snacks + GPS on EVERY belt size (fixes the S-L snacks miss and the sheep GPS miss without
       touching the graded belt pockets). Right: the 2nd 1 L bottle (sheep), with a pole boot along its front edge.
* E-5  POLE QUIVER: the right pocket's front pleat is a boot for the pole tips and a shock-cord loop with a cord lock
       at the wing's top front corner holds the grips; poles stow and draw pack-on, so the 8-day sheep load no
       longer pushes them into the bag (the B.2 glassing miss).
* E-7  WIDER BASE: floor half-width 136 -> 160 mm (base 320 mm, 12.6 in), linear to 197 at the shoulder crease as
       CORRIE. Puts back the volume E-1/E-2/E-3 removed, low and on the frame line, so the collar stays at z 736.3.
* E-6  Pouch, door construction, wings, IMP-1/2/4/8, frame interface, fly logic: as CORRIE B.2.
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit import materials as MAT  # noqa: E402

TEAM = "A"
NAME = "CORRIE E (EVOLVE)"

# ---------------------------------------------------------------------------------------------- design parameters
R_AFT = 40.0            # DECISION E-1: aft vertical corner radius (mm); 1.6 in
A_TOP = 185.0           # DECISION E-2: half-width at the collar seam (CORRIE 196.8); width 370 mm = 14.6 in
TUB_H = 60.0            # DECISION E-3: tub wall height above the floor (z 35 -> 95)
TUB_MAT = "cordura_500d_nylon66"   # ASSUMPTION: camo-printed 500D = the record gsm (print adds < 3 %, research doc)
DOOR = dict(CO.DOOR, z_lo=130.0)   # E-3: sill z 110 -> 130 (35 mm surround strip over the tub wall)
Z_C = 736.3             # collar seam as CORRIE rev B. Iteration log: a first run at z 736.3 with CORRIE's base gave
                        # 81.7 L fill (E-1/E-2/E-3 took ~6.7 L out); raising the collar to 776 restored 85.5 L but
                        # moved the 15 in fill / meat CG aft to 198.2 / 188.8 mm (taller bag peels more on a short
                        # torso). So the volume comes back LOW and WIDE instead (E-7), the collar stays.
A_BOT = 160.0           # DECISION E-7: half-width at the floor 136 -> 160 (base 272 -> 320 mm, 12.6 in); the volume
                        # goes in low, on the frame line, where it costs no CG lever

# hip-reach pockets (E-4) and pole quiver (E-5)
FP = {"w": 180.0, "h": 230.0, "z": (95.0, 325.0), "pleat": 2 * 40.0,  # finished face; 2 x 40 mm bottom box pleats
      "cap_L": 2.0, "env_mm": (230.0, 150.0, 90.0)}                    # ASSUMPTION: usable stretch volume / envelope
POLE = {"cord_m": 0.30, "tab_m": 0.06, "env_mm": (420.0, 70.0, 50.0), "cap_L": 1.0}

GSM = {m: MAT.load(m).require("areal_density_gsm") for m in
       ("cordura_330d_nylon66", "cordura_500d_nylon66", "polyester_ht_630d_printable", "power_mesh_nylon_spandex",
        "robic_100d_ripstop", "challenge_ultra_200")}
SHOCK_GM = MAT.load("shock_cord_3mm").require("mass_g_m")
CORDLOCK_G = MAT.load("cord_lock_spring").require("mass_g")
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")
ZIP10_GM = MAT.load("coil_zipper_10").require("mass_g_m")
SA = 8.0
H = BC.HOURS


# ---------------------------------------------------------------------------------------------- envelope
class EvoConcept(BC.Concept):
    """CORRIE rev B envelope (kind box, d_bot 170, d_nom 270) with the shoulder taper (E-2) and rounded aft corners
    (E-1). The rounded corners enter the rule volume as the section factor k(z) = 1 - 2 (1 - pi/4) r^2 / (2 a d)."""

    r_aft: float = R_AFT
    a_top: float = A_TOP

    def a(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        base = np.interp(z, [BC.Z0, BC.Z_SH], [self.a_bot, BC.A_MAX])
        zc = self.z_c if self.z_c else Z_C
        top = BC.A_MAX + (self.a_top - BC.A_MAX) * np.clip((z - BC.Z_SH) / (zc - BC.Z_SH), 0, 1)
        return np.where(z <= BC.Z_SH, base, top)

    def k_at(self, a, d):
        return 1.0 - 2 * (1 - math.pi / 4) * self.r_aft ** 2 / (2 * a * d)

    def profile(self, z_c=None, n_body=240, n_dome=80):
        z_c = self.z_c if z_c is None else z_c
        zb = np.unique(np.r_[np.linspace(BC.Z0, z_c, n_body), BC.Z_SB, BC.Z_SH])
        zb = zb[zb <= z_c]
        a, d = self.a(zb), self.depth(zb)
        k = np.array([self.k_at(ai, di) for ai, di in zip(a, d)])
        rows = [np.column_stack([zb, a, BC.y_frame(zb), d, k])]
        a_c, d_c = float(self.a([z_c])[0]), float(self.depth([z_c])[0])
        k_c = self.k_at(a_c, d_c)
        zd = np.linspace(z_c, z_c + self.dome_h, n_dome)[1:]
        u = (zd - z_c) / self.dome_h
        ad, dd, _ = BC.dome_section(u, a_c, d_c, k_c)
        kd = (k_c + (BC.K_SPINE - k_c) * u) * BC.DOME_CAL
        rows.append(np.column_stack([zd, ad, BC.y_frame(zd), dd, kd]))
        return np.vstack(rows)

    def ring(self, z, M=240, state=None):
        st = self.profile()
        a, yf, d = (float(np.interp(z, st[:, 0], st[:, i])) for i in (1, 2, 3))
        P = rounded_section(a, d, yf, min(self.r_aft, 0.45 * d), M)
        return np.column_stack([P, np.full(len(P), z)]), M // 4

    def cg(self, n=161, M=360):
        st = self.profile()
        zs = np.linspace(st[0, 0], st[-1, 0], n)
        V = Sy = Sz = 0.0
        for z in zs:
            a, yf, d, kk = (float(np.interp(z, st[:, 0], st[:, i])) for i in (1, 2, 3, 4))
            P = rounded_section(a, d, yf, min(self.r_aft, 0.45 * d), M)
            A, cy = BC.poly_area_centroid(P)
            A *= kk / self.k_at(a, d) if z <= self.z_c else kk / BC.DOME_CAL / max(self.k_at(a, d), 1e-6) * BC.DOME_CAL
            V += A
            Sy += A * cy
            Sz += A * z
        return Sy / V, Sz / V


def rounded_section(a, d, yf, r, M=240):
    """Frame face (-x -> +x) then the outer path: right side, R r aft corner, aft face, left corner, left side."""
    nf = M // 4
    fr = np.column_stack([np.linspace(-a, a, nf, endpoint=False), np.full(nf, yf)])
    th = np.linspace(0, np.pi / 2, 24)
    right = np.column_stack([np.full(2, a), [yf, yf + d - r]])
    arcR = np.column_stack([a - r + r * np.cos(th), yf + d - r + r * np.sin(th)])
    arcL = np.column_stack([-(a - r) - r * np.sin(th), yf + d - r + r * np.cos(th)])
    left = np.column_stack([np.full(2, -a), [yf + d - r, yf]])
    out = np.vstack([right, arcR, arcL, left])
    return np.vstack([fr, BC._resample_open(out, M - nf)[:-1]])


_CORRIE_MAKE = CO.make     # captured: renders re-point corrie.make at this module's make()


def make() -> EvoConcept:
    CO_c = _CORRIE_MAKE()
    c = EvoConcept(key="corrie_e", name=NAME, kind="box", d_bot=CO_c.d_bot, d_nom=CO_c.d_nom, a_bot=A_BOT,
                   tagline="CORRIE evolved: rounded aft corners, shoulder taper, camo tub base, hip-reach pockets",
                   access="roll-top + horseshoe #10 door z 130-650 + 2.7 L pouch + hip-reach pockets")
    c.z_c = Z_C
    return c


@contextlib.contextmanager
def corrie_door(door=None):
    """CORRIE's build reads corrie.DOOR at call time: swap in CORRIE E's door for the duration of a build."""
    old = CO.DOOR
    CO.DOOR = door or DOOR
    try:
        yield
    finally:
        CO.DOOR = old


# ---------------------------------------------------------------------------------------------- mass ledger
def _cut(w, h, gsm, qty=1, sa=SA):
    return (w + 2 * sa) * (h + 2 * sa) * 1e-6 * gsm * qty


def outer_perimeter(c, z, r=R_AFT):
    """Outer three sides (right gusset, aft, left gusset) at z, with the rounded aft corners."""
    a, d = float(c.a([z])[0]), float(c.depth([z])[0])
    return 2 * (d - r) + 2 * (a - r) + math.pi * r


def ledger(c: EvoConcept, b: BC.Build) -> list:
    """Rows on top of corrie.build(c) (CORRIE's own build on the CORRIE E envelope and door)."""
    rows = []

    def row(id_, what, g, hours=0.0, pieces=0, seam_m=0.0, curved=0, applique_m=0.0, src=""):
        rows.append({"id": id_, "what": what, "g": round(g, 1), "hours": round(hours, 2), "pieces": pieces,
                     "seam_m": round(seam_m, 2), "curved_seams": curved, "applique_m": round(applique_m, 2), "src": src})

    # E-1 rounded aft corners: each corner trades 2 r of flat face for pi r / 2 of arc
    dp = (2 - math.pi / 2) * R_AFT * 2
    h_shell = c.z_c - BC.Z0 - TUB_H
    floor_cut = 2 * (1 - math.pi / 4) * R_AFT ** 2
    row("E-1", f"rounded aft corners R {R_AFT:.0f}: aft panels {dp:.1f} mm narrower over {h_shell:.0f} mm; floor "
        f"corners rounded", -dp * h_shell * 1e-6 * GSM["cordura_330d_nylon66"] - floor_cut * 1e-6 * GSM["cordura_500d_nylon66"],
        hours=0.15, src="cordura_330d / 500d records; +0.15 h clipping the 2 floor arcs (ASSUMPTION); the door zip bottom run is the same 34 mm shorter (coil_zipper_10)")
    # E-3 camo tub: tub wall strip in 500D printed; the gusset / surround lose their bottom 60 mm; kick plates go
    per0 = outer_perimeter(c, BC.Z0)
    per1 = outer_perimeter(c, BC.Z0 + TUB_H)
    strip = _cut(0.5 * (per0 + per1), TUB_H, GSM[TUB_MAT])
    shell_cut = 0.5 * (per0 + per1) * TUB_H * 1e-6 * GSM["cordura_330d_nylon66"]
    kicks = [p for p, _ in b.pieces if p.piece_id in ("SH-01a", "SH-01b")]
    kick_g = sum(BC.piece_mass_g(p) for p in kicks)
    kick_edge = sum(BC._perim(p) * p.quantity for p in kicks) / 1000
    seam_new = per0 + per1 + 2 * TUB_H          # floor | tub (curved), tub | body (straight ring), 2 ends at B-01
    seam_old = per0                              # floor | gusset R/aft/gusset L (3 straight seams) disappear
    row("E-3", f"camo tub wall {TUB_H:.0f} mm (500D printed, {per0:.0f}/{per1:.0f} mm long) replaces the bottom "
        f"{TUB_H:.0f} mm of gussets + surround and the two-layer chevron kick plates SH-01a/b ({kick_g:.1f} g)",
        strip - shell_cut - kick_g,
        hours=(1 * H["cut_piece"] - sum(p.quantity for p in kicks) * H["cut_piece"]
               + (per1 + 2 * TUB_H - 0) / 1000 * H["straight_m"] + per0 / 1000 * (H["curved_m"] - H["straight_m"])
               + H["ring"] - kick_edge * H["applique_m"]),
        pieces=1 - sum(p.quantity for p in kicks), seam_m=(seam_new - seam_old) / 1000, curved=1,
        applique_m=-kick_edge, src=f"{TUB_MAT} record (ASSUMPTION print), cordura_330d record, corrie.build kick plates")
    # E-7: corrie.build sizes the floor B-05 from bag_concepts.A_BOT (136); the CORRIE E floor is 2 x A_BOT wide
    d0 = float(c.depth([BC.Z0])[0])
    row("E-7", f"wider base: floor B-05 {2 * BC.A_BOT:.0f} -> {2 * A_BOT:.0f} mm wide (B-01, gussets, aft panels follow "
        "c.a(z) in corrie.build already)", 2 * (A_BOT - BC.A_BOT) * d0 * 1e-6 * GSM["cordura_500d_nylon66"],
        src="cordura_500d_nylon66 record")
    # E-4 hip-reach pockets (2): power-mesh face, 2 x 40 mm box pleats, 3 mm shock-cord top channel
    mesh = _cut(FP["w"] + FP["pleat"], FP["h"], GSM["power_mesh_nylon_spandex"], qty=2)
    cord = 2 * (FP["w"] + FP["pleat"] + 60) / 1000 * SHOCK_GM
    band = _cut(FP["w"] + FP["pleat"], 25.0, GSM["polyester_ht_630d_printable"], qty=2)   # camo mouth band
    row("E-4", "hip-reach pockets FP-L / FP-R on the wings' lower front corners: power mesh "
        f"{FP['w'] + FP['pleat']:.0f} x {FP['h']:.0f} with 2 box pleats, shock-cord top in a 25 mm camo mouth band (630D printable), sewn to the wing before its hem",
        mesh + cord + band, hours=2 * H["cut_piece"] + 2 * (2 * FP["h"] + FP["w"]) / 1000 * H["straight_m"]
        + 2 * 0.25 * H["straight_m"] + 4 * H["bartack"] + 0.3, pieces=2, seam_m=2 * (2 * FP["h"] + FP["w"] + 250) / 1000,
        src="power_mesh_nylon_spandex, shock_cord_3mm records; +0.3 h pleats (ASSUMPTION)")
    # E-5 pole quiver: boot = the right pocket's front pleat (stitched 40 mm channel); grip loop on the wing top
    row("E-5", "pole quiver: 40 mm boot channel stitched in FP-R's front pleat; 3 mm shock-cord grip loop 0.30 m with "
        "a cord lock on a 25 mm webbing tab caught in the wing top hem", POLE["cord_m"] * SHOCK_GM + CORDLOCK_G
        + POLE["tab_m"] * WEB25, hours=0.25 * H["straight_m"] + 2 * H["bartack"] + 0.1, seam_m=0.25,
        src="shock_cord_3mm, cord_lock_spring, poly_webbing_25mm records")
    return rows


def bag_pockets_g() -> dict:
    """The CORRIE B.2 bag-mounted pockets (unchanged in CORRIE E). IMP-6 / IMP-3 / IMP-5 are harness / belt parts."""
    out = {}
    for d in CO.bag_pockets():
        if d["id"] in ("IMP-1", "IMP-2", "IMP-4", "IMP-8"):
            out[d["id"]] = round(float(d["mass_g"]), 1)
    return out


def fly_g(b: BC.Build, extra_area_m2=0.0) -> float:
    fly = sum(r["mass_g_total"] for k, r in CO._panels().items() if k.startswith("F-01"))
    a = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in CO.OUTER_IDS) / 1e6 + extra_area_m2
    return fly * a / CO.SPINE_OUTER_M2


def system(c=None) -> dict:
    """CORRIE E bag system and the same metric on CORRIE B.2 (same code, so the delta is like for like)."""
    c = c or make()
    with corrie_door():
        b = CO.build(c)
    m = BC.metrics(b)
    led = ledger(c, b)
    # fly: E-1 and E-3 change the outer shell; scale the fly with it (as corrie G-2)
    d_outer = -(2 - math.pi / 2) * R_AFT * 2 * (c.z_c - BC.Z0) * 1e-6
    bc = _CORRIE_MAKE()
    bco = CO.build(bc)
    mc = BC.metrics(bco)
    pk = bag_pockets_g()
    sys_c = mc["mass_g"]["total"] + sum(pk.values()) + fly_g(bco)
    sys_e = m["mass_g"]["total"] + sum(r["g"] for r in led) + sum(pk.values()) + fly_g(b, d_outer)
    zip_e = sum(z["length_mm"] for z in b.zips) - (2 - math.pi / 2) * R_AFT * 2   # E-1: the U bottom run is shorter
    zip_c = sum(z["length_mm"] for z in bco.zips)
    hours_e = m["hours_total"] + sum(r["hours"] for r in led) + POCKET_HOURS
    hours_c = mc["hours_total"] + POCKET_HOURS
    v = volumes(c)
    return {
        "corrie_b2": {"body_g": mc["mass_g"]["total"], "pockets_g": pk, "fly_g": round(fly_g(bco), 1),
                      "bag_system_g": round(sys_c, 1), "pieces": mc["cut_pieces"] + POCKET_PIECES, "curved_seams": mc["curved_seams"],
                      "zip_mm": round(zip_c, 0), "hours": round(hours_c, 1), "seam_m": mc["seam_length_m"]},
        "corrie_e": {"body_g_corrie_build": m["mass_g"]["total"], "ledger": led, "pockets_g": pk,
                     "fly_g": round(fly_g(b, d_outer), 1), "bag_system_g": round(sys_e, 1),
                     "pieces": m["cut_pieces"] + sum(r["pieces"] for r in led) + POCKET_PIECES,
                     "curved_seams": m["curved_seams"] + sum(r["curved_seams"] for r in led),
                     "zip_mm": round(zip_e, 0), "hours": round(hours_e, 1),
                     "seam_m": round(m["seam_length_m"] + sum(r["seam_m"] for r in led), 2)},
        "delta_g": round(sys_e - sys_c, 1), "volume": v, "door": DOOR, "zips_e": b.zips,
    }


# IMP-1/2/4/8 pieces and hours (corrie.bag_pockets), counted the same on both bags
POCKET_PIECES = sum(d.get("pieces_n", 0) for d in [])   # filled below
POCKET_HOURS = 0.0


def _pocket_counts():
    global POCKET_PIECES, POCKET_HOURS
    n = h = 0.0
    for d in CO.bag_pockets():
        if d["id"] in ("IMP-1", "IMP-2", "IMP-4", "IMP-8"):
            pc = d.get("pieces", 0)
            n += sum(int(getattr(p, "quantity", 1)) for p in pc) if isinstance(pc, list) else int(pc)
            h += float(d.get("hours", 0.0))
    POCKET_PIECES, POCKET_HOURS = int(n), round(h, 2)


_pocket_counts()


def volumes(c=None) -> dict:
    c = c or make()
    cc = _CORRIE_MAKE()
    cy, cz = c.cg()
    return {"rule_L": round(c.volume_L(), 2), "corrie_rule_L": round(cc.volume_L(), 2),
            "z_collar": c.z_c, "z_fill": round(c.z_fill, 1), "fill_height_in": round((c.z_fill - BC.Z0) / 25.4, 1),
            "width_max_mm": round(2 * float(np.max(c.a(np.linspace(BC.Z0, c.z_c, 200)))), 0),
            "width_collar_mm": round(2 * float(c.a([c.z_c])[0]), 0),
            "depth_max_mm": round(float(np.max(c.depth(np.linspace(BC.Z0, c.z_c, 200)))), 0),
            "uniform_cg_y": round(cy, 1), "uniform_cg_z": round(cz, 1),
            "corrie_uniform_cg": [round(float(v), 1) for v in cc.cg()]}


def door_reach(c=None) -> dict:
    """Clear width of the door opening (chord). CORRIE: zip 45 mm in from a square corner, chord 2 (a - 45).
    CORRIE E: the zip is 45 mm along the surface from the side tangent, i.e. on the R 40 arc at phi = 45 / 40 rad,
    so the chord is 2 (a - r + r cos phi): the door opens round the corners and is wider in plan."""
    c = c or make()
    cc = _CORRIE_MAKE()
    out = {}
    phi = DOOR["inset"] / R_AFT
    for nm, z in BC.STATIONS.items():
        a = float(c.a([z])[0])
        inside = DOOR["z_lo"] <= z <= DOOR["z_hinge"]
        w = 2 * (a - R_AFT + R_AFT * math.cos(min(phi, math.pi / 2))) if phi < math.pi / 2 else 2 * (a - R_AFT - (DOOR["inset"] - R_AFT * math.pi / 2))
        out[nm] = {"z": z, "clear_width_mm": round(w, 0) if inside else 0.0,
                   "corrie_mm": round(2 * (float(cc.a([z])[0]) - CO.DOOR["inset"]), 0) if CO.DOOR["z_lo"] <= z else 0.0}
    out["sill_above_floor_mm"] = DOOR["z_lo"] - BC.Z0
    return out


if __name__ == "__main__":
    s = system()
    print(json.dumps({k: v for k, v in s.items() if k != "zips_e"}, indent=1, default=float))
    print(json.dumps(door_reach(), default=float))
    (HERE / "evolve_numbers.json").write_text(json.dumps(s, indent=1, default=float))
