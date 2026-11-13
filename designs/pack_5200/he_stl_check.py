"""BL-044: the hinge eye checked against the REAL hinge fairlead, by slicing the HE-FIT test-piece STL.

    python designs/pack_5200/he_stl_check.py            # check, write analysis/he_stl_check.json + screenshots

Three review rounds found fixes that passed their own checks and failed on the real geometry. So the eye
(``patterns_corrie_f_rev3.he_geometry`` / ``he_loop`` on ``bag_attach.HINGE_EYE_ENVELOPE``, DECISION HE-ENV) is laid
into slices of the file the owner prints for HE-FIT, ``print/frame_h1/test_pieces/hefit_hinge_fairlead_R_frame_coords
.stl`` (BL-042, frame coordinates), at every bracket corner the pattern is solved over:

* the B-01 face at the box (PANEL_OFFSET 20, in line, the cheek-tip plane) x webbing ply 1.2 / 1.5 / 1.6 mm x 1 or 2
  fold plies under the main ply; each corner puts the loaded pin at its own height above the floor seam, so the bag
  (box, legs) sits at its own z against the frame;
* plane z through the pin axis: the eye's ply stack under the pin, across the neck, with the neck slid sideways
  against either cheek (it slides freely on the pin), against the printed floor and its corner fillets. The stack is
  3 plies over the 2 mm ridge where the two neck folds overlap and falls to 2 plies at the neck edge, where the main ply
  turns into its fold (ASSUMPTION HE-STACK: the taut main ply bridges from the ridge to the edge fold); the folded edge
  is round, radius one ply (ASSUMPTION HE-FOLD-R). Clearance = vertical gap from the stack to the floor at every x
  (sliding contact with a cheek FACE is allowed: the throat check covers it);
* planes x = station + dx across the neck: the whole loop (legs and wrap, section polygon) must not touch the
  printed material (root, saddle, stay) at any bracket corner;
* planes z through the cheeks: the clear throat against the widest neck (19 mm);
* planes x through the box (34 mm wide, so under the cheeks): the box stack must stay HE_CHEEK_MIN below the cheeks.

Units mm. Frame coordinates: y towards the bag, z up; the section model's z (above the floor seam line) maps to frame
z by putting the solved pin height on the printed pin (frame z 60).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import patterns_corrie_f_rev3 as P  # noqa: E402

PIECE = HERE / "print" / "frame_h1" / "test_pieces" / "hefit_hinge_fairlead_R_frame_coords.stl"
OUT_JSON = HERE / "analysis" / "he_stl_check.json"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261113_BL044"
RIDGE_HALF = 1.0 + 1.0           # 2 mm fold overlap (+/-1 mm) + HE-NECK-TOL: 3 plies within +/-2 mm of the neck CL
DX_STEP = 0.25
CORNER_BAND = 0.1               # the last 0.1 mm at each cheek face: the fold edge meets the throat-corner fillet; the
#                                 0.5 mm rule is reported there but only > 0 (no interference) is required (BL-044)


def _H():
    from huntkit.gendesign import h1_fairleads as H
    return H


def station(side: str = "R") -> dict:
    """The printed hinge fairlead's placement (h1_fairleads.placed: frame x, stay centre yc, pin y, floor y, tip y)."""
    return next(p for p in _H().placed() if p["id"] == f"hinge_{side}")


def load_piece(path: Path = PIECE):
    import trimesh
    m = trimesh.load(path)
    if not m.is_watertight:
        raise RuntimeError(f"{path.name}: not watertight")
    return m


def stack_t(dx_from_neck_cl: float, t: float, neck_w: float) -> float:
    """Ply-stack thickness of the eye at ``dx`` from the neck centre line (ASSUMPTION HE-STACK)."""
    a = abs(dx_from_neck_cl)
    if a <= RIDGE_HALF:
        return 3 * t
    half = neck_w / 2
    if a >= half:
        return 2 * t
    return 3 * t - t * (a - RIDGE_HALF) / (half - RIDGE_HALF)


def corners() -> list:
    """Every bracket corner the eye is solved over, with its loaded pin height (he_bracket) and the box."""
    g = P.he_geometry()
    out = []
    for r in P.he_bracket(P.HE_EYE):
        out.append({**r, "box": (P.HE_BOX_GAP, g["box_top"])})
    return out


def eye_polygon(c: dict, T: float, st: dict, dz_frame: float):
    """Section (frame y, z) of the eye's ply stack at one corner: the stack mid-line (legs from the box top, round the
    pin at radius PIN_D/2 + T/2) buffered by T/2."""
    from shapely.geometry import LineString
    g = P.he_geometry(c["face_y"], c["t"], c["nf"])
    yc = st["yc"]
    pin = (g["pin_y"], c["pin_z"])
    rm = g["pin_d"] / 2 + T / 2
    A = (c["face_y"] - c["t"] / 2, g["box_top"])
    B = (c["face_y"] - 1.5 * c["t"], g["box_top"])
    thA, tA = P._tangent(A, pin, rm, +1)
    thB, tB = P._tangent(B, pin, rm, -1)
    while thB < thA:
        thB += 2 * math.pi
    th = np.linspace(thA, thB, 90)
    pts = [A] + [(pin[0] + rm * math.cos(a), pin[1] + rm * math.sin(a)) for a in th] + [B]
    pts = [(yc + y, z + dz_frame) for y, z in pts]
    return LineString(pts).buffer(T / 2, cap_style=2, join_style=1)


def stack_bottom(u: float, t: float, neck_w: float) -> float:
    """Depth of the stack's underside below the pin's underside at ``u`` from the neck CL, with the round folded edge
    (radius one ply, ASSUMPTION HE-FOLD-R)."""
    T = stack_t(u, t, neck_w)
    half, r = neck_w / 2, t
    a = abs(u)
    if a > half:
        return 0.0
    if a > half - r:
        T -= r - math.sqrt(max(r * r - (a - (half - r)) ** 2, 0.0))
    return T


def under_pin(mesh, st: dict, t: float) -> dict:
    """Plane z through the pin axis: vertical clearance from the eye's stack to the printed floor under the pin, over
    every neck position (18 mm slid +/-1 mm, 19 mm slid +/-0.5 mm); min and where."""
    H = _H()
    E = P.he_envelope()
    S = H._zplane(mesh, st["z"])
    pu = st["y_pin"] - E["pin_d_mm"] / 2
    x0 = st["x"]
    half_th = E["throat_mm"] / 2
    xs = np.arange(-half_th + 0.01, half_th - 0.01 + 1e-9, 0.05)
    flo = {}
    for dx in xs:
        r = [b for a, b in H._runs(S, 1, x0 + dx, st["yc"] - 30, st["y_pin"] + 15) if a < pu]
        flo[round(float(dx), 3)] = (pu - max(r)) if r else 99.0          # floor depth below the pin's underside
    best = {"clear_mm": 1e9}
    for nw, sh in [(P.HE_NECK_W, v) for v in (-1.0, 0.0, 1.0)] + [(P.HE_NECK_W + P.HE_NECK_TOL, v) for v in (-0.5, 0.0, 0.5)]:
        for dx, fd in flo.items():
            u = dx - sh
            if abs(u) > nw / 2:
                continue
            c = fd - stack_bottom(u, t, nw)
            if c < best["clear_mm"]:
                best = {"clear_mm": round(c, 3), "x_from_throat_cl": dx, "neck_w": nw, "shift": sh,
                        "stack_mm": round(stack_bottom(u, t, nw), 3), "floor_depth_mm": round(fd, 3)}
    centred = min(fd - stack_bottom(dx, t, P.HE_NECK_W) for dx, fd in flo.items() if abs(dx) <= P.HE_NECK_W / 2)
    off = 1e9
    for nw, sh in [(P.HE_NECK_W, v) for v in (-1.0, 0.0, 1.0)] + [(P.HE_NECK_W + P.HE_NECK_TOL, v) for v in (-0.5, 0.0, 0.5)]:
        for dx, fd in flo.items():
            if abs(dx - sh) <= nw / 2 and abs(dx) <= half_th - CORNER_BAND:
                off = min(off, fd - stack_bottom(dx - sh, t, nw))
    return {"t": t, "worst": best, "centred_clear_mm": round(centred, 3), "clear_off_corner_mm": round(off, 3),
            "floor_depth_centre_mm": round(flo[min(flo, key=abs)], 3),
            "floor_profile": [[dx, round(fd, 3)] for dx, fd in sorted(flo.items())][::5]}


def check(mesh=None, side: str = "R") -> dict:
    """Slice the test piece and check the eye (see the module docstring)."""
    from shapely.geometry import box
    H = _H()
    mesh = mesh if mesh is not None else load_piece()
    st = station(side)
    E = P.he_envelope()
    x0, zp = st["x"], st["z"]
    ts = sorted({P.HE_T_RANGE[0], P.HE_T, P.HE_T_RANGE[1]})
    up = {f"{t}": under_pin(mesh, st, t) for t in ts}
    rows = []
    xsec = {dx: H._xplane(mesh, x0 + dx) for dx in range(-8, 9, 2)}
    bsec = [H._xplane(mesh, x0 + d) for d in np.arange(-P.HE_BOX[0] / 2, P.HE_BOX[0] / 2 + 1e-9, 1.0)]
    for c in corners():
        dz = zp - c["pin_z"] - P.BC.Z0               # section z (above the seam line) -> frame z: pin on the pin
        ov, dmin = 0.0, 1e9
        for dx, S in xsec.items():
            e = eye_polygon(c, stack_t(dx, c["t"], P.HE_NECK_W), st, dz + P.BC.Z0)
            a = float(e.intersection(S).area)
            ov = max(ov, a)
            dmin = min(dmin, float(e.distance(S)) if a < 1e-6 else 0.0)
        bx = box(st["yc"] + c["face_y"] - 2 * c["t"] - 1.6, c["box"][0] + dz + P.BC.Z0,
                 st["yc"] + c["face_y"], c["box"][1] + dz + P.BC.Z0)     # 2 HE plies + 1.6 mm B-01 / B-18 allowance
        box_d = min(float(bx.distance(S)) for S in bsec)
        rows.append({"face_y": c["face_y"], "t": c["t"], "nf": c["nf"], "pin_z": round(c["pin_z"], 2),
                     "loop_overlap_mm2": round(ov, 3), "loop_to_material_mm": round(dmin, 2),
                     "box_top_to_cheek_mm": round(zp - E["cheek_half_z_mm"] - (c["box"][1] + dz + P.BC.Z0), 2),
                     "box_to_material_mm": round(box_d, 2), "under_pin_clear_mm": up[f"{c['t']}"]["worst"]["clear_mm"]})
    ws = []
    pu = st["y_pin"] - E["pin_d_mm"] / 2
    for z in np.linspace(zp - E["cheek_half_z_mm"] + 1.0, zp + E["cheek_half_z_mm"] - 1.0, 9):
        S = H._zplane(mesh, z)
        for y in np.linspace(pu, st["y_tip"] - 0.3, 8):
            a, b = H._void_around(H._runs(S, 0, y, x0 - 40, x0 + 40), x0, x0 - 40, x0 + 40)
            ws.append(b - a)
    thr = min(ws)
    res = {"piece": str(PIECE.relative_to(ROOT)), "station": st["id"], "pin_y_frame": round(st["y_pin"], 3),
           "under_pin": up, "worst_under_pin_clear_mm": min(v["worst"]["clear_mm"] for v in up.values()),
           "throat_min_mm": round(thr, 2), "neck_max_mm": P.HE_NECK_W + P.HE_NECK_TOL,
           "throat_clear_side_mm": round((thr - P.HE_NECK_W - P.HE_NECK_TOL) / 2, 2),
           "throat_clear_side_at_print_tol_mm": round((thr - 2 * P.PRINT_TOL - P.HE_NECK_W - P.HE_NECK_TOL) / 2, 2),
           "corners": rows, "worst_loop_overlap_mm2": max(r["loop_overlap_mm2"] for r in rows),
           "min_loop_to_material_mm": min(r["loop_to_material_mm"] for r in rows),
           "min_box_top_to_cheek_mm": min(r["box_top_to_cheek_mm"] for r in rows),
           "min_box_to_material_mm": min(r["box_to_material_mm"] for r in rows),
           "req": {"under_pin_clear_mm": 0.5, "under_pin_clear_in_corner_mm": "> 0", "corner_band_mm": CORNER_BAND,
                   "throat_side_mm": 0.5, "box_cheek_mm": P.HE_CHEEK_MIN},
           "assumptions": ["HE-STACK: 3 plies over the +/-2 mm ridge, falling to 2 plies at the neck edge",
                           "HE-FOLD-R: the folded neck edge is round, radius one ply"]}
    res["min_clear_off_corner_mm"] = min(v["clear_off_corner_mm"] for v in up.values())
    res["pass"] = bool(res["worst_loop_overlap_mm2"] < 1e-3 and res["worst_under_pin_clear_mm"] > 0.0
                       and res["min_clear_off_corner_mm"] >= 0.5
                       and res["throat_clear_side_at_print_tol_mm"] >= 0.5 - 1e-9
                       and res["min_box_top_to_cheek_mm"] >= P.HE_CHEEK_MIN - 1e-9 and res["min_box_to_material_mm"] > 0.0)
    return res


def figures(res: dict, mesh=None, side: str = "R") -> list:
    """Screens: (1) section at the neck centre with the design corner and the worst corner over the STL slice;
    (2) the floor under the pin across the throat against the ply stack."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import MultiPolygon
    H = _H()
    mesh = mesh if mesh is not None else load_piece()
    st = station(side)
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    S = H._xplane(mesh, st["x"])
    cs = corners()
    g = P.he_geometry()
    design = min(cs, key=lambda c: abs(c["face_y"] - g["face_inline"]) + abs(c["t"] - P.HE_T) + abs(c["nf"] - 2))
    worst_row = min(res["corners"], key=lambda r: (r["box_top_to_cheek_mm"], r["under_pin_clear_mm"]))
    worst = next(c for c in cs if c["face_y"] == worst_row["face_y"] and c["t"] == worst_row["t"] and c["nf"] == worst_row["nf"])
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.8))
    for ax, c, ttl in ((axs[0], design, "design corner"), (axs[1], worst, "tightest corner (box to cheeks)")):
        for poly in (S.geoms if isinstance(S, MultiPolygon) else [S]):
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, fc="#8aa", ec="#344", lw=0.8)
            for hole in poly.interiors:
                hx, hy = hole.xy
                ax.fill(hx, hy, fc="white", ec="#344", lw=0.6)
        dz = st["z"] - c["pin_z"] - P.BC.Z0
        e = eye_polygon(c, 3 * c["t"], st, dz + P.BC.Z0)
        ex, ey = e.exterior.xy
        ax.fill(ex, ey, fc="#e2a64a", ec="#a5650a", alpha=0.85, lw=0.8)
        for hole in e.interiors:                         # the eye's opening (and the pin's seat) are holes
            hx, hy = hole.xy
            ax.fill(hx, hy, fc="white", ec="#a5650a", lw=0.6)
        ax.add_patch(plt.Circle((st["y_pin"], st["z"]), 2.5, fc="#222"))
        fy = st["yc"] + c["face_y"]
        zb0, zb1 = c["box"][0] + dz + P.BC.Z0, c["box"][1] + dz + P.BC.Z0
        ax.add_patch(plt.Rectangle((fy - 2 * c["t"], zb0), 2 * c["t"], zb1 - zb0, fc="#1a7f37", alpha=0.5))
        ax.plot([fy, fy], [P.BC.Z0 + dz - 12, zb1 + 2], color="#2b6cb0", lw=3)
        ax.axhline(P.BC.Z0 + dz, color="k", ls="--", lw=0.8)
        ax.text(st["yc"] - 14, P.BC.Z0 + dz + 0.8, "floor seam line", fontsize=8)
        r = next(q for q in res["corners"] if q["face_y"] == c["face_y"] and q["t"] == c["t"] and q["nf"] == c["nf"])
        ax.set_title(f"{ttl}: B-01 at {c['face_y']:.1f} mm, ply {c['t']} mm, {c['nf']} fold plies\n"
                     f"pin {c['pin_z']:.1f} above the seam; box top {r['box_top_to_cheek_mm']:.1f} mm under the cheeks;\n"
                     f"under the pin {r['under_pin_clear_mm']:.2f} mm clear (neck slid against a cheek)", fontsize=9.5, loc="left")
        ax.set_xlim(st["yc"] - 16, st["yc"] + 34)
        ax.set_ylim(st["z"] - 32, st["z"] + 16)
        ax.set_aspect("equal")
        ax.set_xlabel("frame y (mm, towards the bag)")
        ax.set_ylabel("frame z (mm)")
    fig.suptitle(f"BL-044 HE eye laid into the HE-FIT test piece STL, slice x = {st['x']:.0f} (neck centre). STL: grey; "
                 "eye ply stack: orange; box: green; B-01: blue", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    p1 = SCREENS / f"{SHOT}_1.png"
    fig.savefig(p1, dpi=110)
    plt.close(fig)
    out.append(p1)
    # under the pin, across the throat (plane z through the pin axis)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    up = res["under_pin"][f"{P.HE_T}"]
    fp = np.array(up["floor_profile"])
    ax.fill_between(fp[:, 0], fp[:, 1], 7.0, color="#8aa", label="printed floor + corner fillets (STL, plane z 60)")
    for nw, sh, col in ((P.HE_NECK_W, 0.0, "#a5650a"), (P.HE_NECK_W, 1.0, "#d08a2a"), (P.HE_NECK_W + 1.0, -0.5, "#c33")):
        for t in (P.HE_T, P.HE_T_RANGE[1]):
            u = np.linspace(-nw / 2, nw / 2, 300)
            ax.plot(u + sh, [stack_bottom(v, t, nw) for v in u], color=col, lw=1.4 if t == P.HE_T else 2.0,
                    ls="-" if t == P.HE_T else ":", label=f"eye stack: neck {nw:.0f} mm slid {sh:+.1f}, ply {t} mm")
    ax.axhline(0, color="#222", lw=2)
    ax.text(-9.5, -0.35, "pin underside", fontsize=8)
    ax.set_ylim(6.5, -0.8)
    ax.set_xlim(-10.5, 10.5)
    ax.set_xlabel("x across the throat from its centre (mm); the cheek faces are at +/-10")
    ax.set_ylabel("mm below the pin's underside")
    w = res["under_pin"][f"{P.HE_T_RANGE[1]}"]["worst"]
    ax.set_title(f"Under the pin: stack vs printed floor. Worst clear {res['worst_under_pin_clear_mm']:.2f} mm "
                 f"(ply {P.HE_T_RANGE[1]}, neck against a cheek at x {w['x_from_throat_cl']:+.1f}); throat "
                 f"{res['throat_min_mm']:.1f} mm vs the 19 mm neck", fontsize=9.5, loc="left")
    ax.legend(fontsize=7, loc="lower center", ncol=2)
    fig.tight_layout()
    p2 = SCREENS / f"{SHOT}_2.png"
    fig.savefig(p2, dpi=110)
    plt.close(fig)
    out.append(p2)
    return out


def main(argv=None) -> int:
    mesh = load_piece()
    res = check(mesh)
    OUT_JSON.write_text(json.dumps(res, indent=1))
    for r in res["corners"]:
        print(r)
    for t, v in res["under_pin"].items():
        print("under pin", t, v["worst"], "centred", v["centred_clear_mm"], "off corner", v["clear_off_corner_mm"])
    print({k: v for k, v in res.items() if k not in ("corners", "under_pin")})
    for p in figures(res, mesh):
        print("screen:", p)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
