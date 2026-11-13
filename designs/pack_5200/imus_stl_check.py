"""BL-044 (orchestrator item 1): the necked IME and US eyes checked against the PRINTED IM / US fairleads, by slicing.

    python designs/pack_5200/imus_stl_check.py      # check, write analysis/imus_stl_check.json + screenshots

BL-045 gave all ten IM / US fairleads the hinge's clearance (``bag_attach.imus_eye_envelope``: 5.5 mm under the pin,
20 mm throat). BL-044 necks the eyes that pass a throat to 18 mm (pattern pieces IME, US, USA; ``_neck``). This lays
each eye into slices of the STL the owner prints, the way ``he_stl_check`` does for the HE:

* **IM3 R on the IM3-EC test piece** (``print/frame_h1/test_pieces/im3ec_cheek_R_frame_coords.stl``, BL-042), and
  **every IM / US station, both sides, on the full print** (``print/frame_h1/h1_assembled.stl``; no US test piece is
  cut, so US1 / US2 are checked on the print the frame is made from);
* plane z through the pin axis: the eye's ply stack under the pin, across the neck, with the neck slid against either
  cheek (18 mm slid +/-1, 19 mm slid +/-0.5), ply 1.2 / 1.5 / 1.6 mm. IME (38 mm, 10 mm folds) is the HE's stack:
  3 plies over the 2 mm fold ridge, 2 at the neck edge (ASSUMPTION HE-STACK). US / USA (25 mm, 3.5 mm folds) are booked
  at 2 plies right across (the envelope's step; the real eye is 1 ply in the middle 11 mm). Round folded edge
  (ASSUMPTION HE-FOLD-R). Rule as HE: >= 0.5 mm clear off the throat-corner fillet band, > 0 inside it;
* plane z through the cheeks: clear throat against the widest neck (19 mm), 0.5 mm a side (print tol 0.05);
* planes x across the neck (and across the full webbing width where it is full width): the whole eye (wrap, both legs
  as a taut teardrop to its box), its box and the strap beyond it must not touch printed material, for every pull
  direction theta in the stay's y-z plane from -90 deg (straight down the stay) to +45 deg (theta 0 = straight into
  the bag, +y). This covers every kit and torso end: the fairleads are on the fixed stays (the crown legs slide in
  the bore behind them), so a torso or crown-kit change moves only the PULL DIRECTION on the eye. The sim directions
  per simulated torso (15 / 19 / 23 in; kit ends map to the nearest, h1_sleeve ASSUMPTION SIM_TORSO) and the rev C
  governing vectors are listed against the swept range.

Units mm. Frame coordinates: x lateral (pin axis), y towards the bag, z up.
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

import he_stl_check as HC  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402

PIECES = HERE / "print" / "frame_h1" / "test_pieces"
IM3EC = PIECES / "im3ec_cheek_R_frame_coords.stl"
PRINT = HERE / "print" / "frame_h1" / "h1_assembled.stl"
OUT_JSON = HERE / "analysis" / "imus_stl_check.json"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261113_BL044imus"
SIMFORCES = ROOT / "outputs" / "im3_body_simloads" / "sim_frame_forces_rev1.json"
THETAS = tuple(range(-90, 46, 15))                  # pull direction sweep, deg from +y towards +z
BEYOND = 60.0                                       # strap / tail carried on past the box (US strap, USA second loop)
STATIONS = ("us1", "us2", "im1", "im2", "im3")


def _H():
    from huntkit.gendesign import h1_fairleads as H
    return H


def _BA():
    from huntkit.gendesign import bag_attach as BA
    return BA


def eye_spec(name: str, side: str) -> dict:
    """The eye that wraps this pin (pattern pieces): webbing width, neck fold, leg (fold to box edge), box."""
    if name.startswith("im"):
        return {"piece": "IME", "web_w": 38.0, "fold": P.IME_NECK_EDGE, "leg": P.IME_NECK[1] - 100.0,
                "box_len": 30.0, "box_w": 34.0, "plies_ridge": 3, "beyond": 0.0}
    if side == "R":                       # the US cam's anchor: the USA dog-bone's pin loop (DECISION USA-LOOP)
        return {"piece": "USA", "web_w": 25.0, "fold": P.US_NECK_EDGE, "leg": P.USA_PIN_LOOP,
                "box_len": 25.0, "box_w": 21.0, "plies_ridge": 2, "beyond": BEYOND}
    return {"piece": "US", "web_w": 25.0, "fold": P.US_NECK_EDGE, "leg": P.US_EYE - P.BOX_TIP_GAP - 25.0,
            "box_len": 25.0, "box_w": 21.0, "plies_ridge": 2, "beyond": BEYOND}


def stack_t(spec: dict, u: float, t: float, neck_w: float) -> float:
    """Ply stack at ``u`` from the neck centre (IME: HE-STACK; US / USA: 2 plies across, the envelope's step)."""
    if spec["plies_ridge"] == 3:
        return HC.stack_t(u, t, neck_w)
    return 2 * t


def stack_bottom(spec: dict, u: float, t: float, neck_w: float) -> float:
    T = stack_t(spec, u, t, neck_w)
    half, r = neck_w / 2, t
    a = abs(u)
    if a > half:
        return 0.0
    if a > half - r:
        T -= r - math.sqrt(max(r * r - (a - (half - r)) ** 2, 0.0))
    return T


def box_distance(spec: dict, t: float) -> float:
    """Pin centre to the box edge for a taut eye: the main ply's centreline (radius PIN_D/2 + plies under it + t/2,
    the fold plies inside) laps the pin and runs to the box as a teardrop; its length is 2 x leg."""
    rc = 2.5 + (spec["plies_ridge"] - 1) * t + t / 2
    L = 2 * spec["leg"]
    lo, hi = rc + 1e-3, L
    for _ in range(60):
        d = (lo + hi) / 2
        per = 2 * math.sqrt(d * d - rc * rc) + rc * (math.pi + 2 * math.asin(rc / d))
        lo, hi = (d, hi) if per < L else (lo, d)
    return (lo + hi) / 2


def eye_shapes(spec: dict, p: dict, t: float, T: float, theta: float):
    """(y, z) section shapes at one pull direction: the eye (taut teardrop round the pin, ply stack T, the pin hole
    left open) and the box + strap beyond it (2 plies of webbing)."""
    from shapely.geometry import LineString, Point
    pin = np.array([p["y_pin"], p["z"]])
    u = np.array([math.cos(math.radians(theta)), math.sin(math.radians(theta))])
    d0 = box_distance(spec, t)
    tip = pin + d0 * u
    eye = Point(*pin).buffer(2.5 + T, 64).union(Point(*tip).buffer(T, 16)).convex_hull
    eye = eye.difference(Point(*pin).buffer(2.5, 64))
    box = LineString([tuple(tip), tuple(tip + (spec["box_len"] + spec["beyond"]) * u)]).buffer(t, cap_style=2)
    return eye, box, d0


def under_pin(mesh, p: dict, spec: dict, t: float) -> dict:
    """Plane z through the pin axis: vertical clearance from the stack to the printed floor, over every neck position
    (he_stl_check.under_pin with this eye's stack)."""
    H = _H()
    E = _BA().imus_eye_envelope(p["name"])
    S = H._zplane(mesh, p["z"])
    pu = p["y_pin"] - E["pin_d_mm"] / 2
    x0 = p["x"]
    half_th = E["throat_mm"] / 2
    nw0 = E["neck_w_mm"]
    flo = {}
    for dx in np.arange(-half_th + 0.01, half_th - 0.01 + 1e-9, 0.05):
        r = [b for a, b in H._runs(S, 1, x0 + dx, p["yc"] - 30, p["y_pin"] + 15) if a < pu]
        flo[round(float(dx), 3)] = (pu - max(r)) if r else 99.0
    cases = [(nw0, v) for v in (-1.0, 0.0, 1.0)] + [(nw0 + P.HE_NECK_TOL, v) for v in (-0.5, 0.0, 0.5)]
    worst, off = {"clear_mm": 1e9}, 1e9
    for nw, sh in cases:
        for dx, fd in flo.items():
            u = dx - sh
            if abs(u) > nw / 2:
                continue
            c = fd - stack_bottom(spec, u, t, nw)
            if c < worst["clear_mm"]:
                worst = {"clear_mm": round(c, 3), "x_from_throat_cl": dx, "neck_w": nw, "shift": sh}
            if abs(dx) <= half_th - HC.CORNER_BAND:
                off = min(off, c)
    return {"t": t, "worst": worst, "clear_off_corner_mm": round(off, 3),
            "floor_depth_centre_mm": round(flo[min(flo, key=abs)], 3)}


def throat(mesh, p: dict) -> float:
    H = _H()
    E = _BA().imus_eye_envelope(p["name"])
    pu = p["y_pin"] - E["pin_d_mm"] / 2
    ws = []
    for z in np.linspace(p["z"] - E["cheek_half_z_mm"] + 1.0, p["z"] + E["cheek_half_z_mm"] - 1.0, 9):
        S = H._zplane(mesh, z)
        for y in np.linspace(pu, p["y_tip"] - 0.3, 8):
            a, b = H._void_around(H._runs(S, 0, y, p["x"] - 40, p["x"] + 40), p["x"], p["x"] - 40, p["x"] + 40)
            ws.append(b - a)
    return float(min(ws))


def sweep(mesh, p: dict, spec: dict) -> dict:
    """Eye, box and strap against x-plane slices at every pull direction and ply (the worst of 1.2 / 1.5 / 1.6)."""
    H = _H()
    nw = _BA().imus_eye_envelope(p["name"])["neck_w_mm"] + P.HE_NECK_TOL
    neck = {dx: H._xplane(mesh, p["x"] + dx) for dx in np.arange(-nw / 2 + 0.25, nw / 2 - 0.25 + 1e-9, 1.0)}
    wide = {dx: H._xplane(mesh, p["x"] + dx) for dx in np.arange(-spec["web_w"] / 2, spec["web_w"] / 2 + 1e-9, 1.5)}
    rows = []
    for th in THETAS:
        r = {"theta": th, "eye_overlap_mm2": 0.0, "eye_clear_mm": 1e9, "box_overlap_mm2": 0.0, "box_clear_mm": 1e9}
        for t in sorted({P.HE_T_RANGE[0], P.HE_T, P.HE_T_RANGE[1]}):
            for dx, S in neck.items():
                eye, _, d0 = eye_shapes(spec, p, t, stack_t(spec, dx, t, nw - P.HE_NECK_TOL), th)
                a = float(eye.intersection(S).area)
                r["eye_overlap_mm2"] = max(r["eye_overlap_mm2"], round(a, 3))
                r["eye_clear_mm"] = min(r["eye_clear_mm"], 0.0 if a > 1e-6 else float(eye.distance(S)))
            for dx, S in wide.items():
                _, box, d0 = eye_shapes(spec, p, t, 2 * t, th)
                a = float(box.intersection(S).area)
                r["box_overlap_mm2"] = max(r["box_overlap_mm2"], round(a, 3))
                r["box_clear_mm"] = min(r["box_clear_mm"], 0.0 if a > 1e-6 else float(box.distance(S)))
        r["box_from_pin_mm"] = round(d0, 1)
        r["eye_clear_mm"] = round(r["eye_clear_mm"], 2)
        r["box_clear_mm"] = round(r["box_clear_mm"], 2)
        r["pass"] = r["eye_overlap_mm2"] < 1e-3 and r["box_overlap_mm2"] < 1e-3
        rows.append(r)
    ok = [r["theta"] for r in rows if r["pass"]]
    return {"rows": rows, "clear_thetas": ok, "eye_ok_all": all(r["eye_overlap_mm2"] < 1e-3 for r in rows)}


def pull_directions() -> dict:
    """Where the eyes are actually pulled: rev C governing vectors (rev_c_verification_results gov_c) and the CORRIE F
    rev 1 sim IM3 hook forces per simulated torso (15 / 19 / 23 in; outputs/im3_body_simloads, regenerated by
    im3_body_simloads if missing). theta = atan2(fz, fy) of the force ON the frame (the eye pulls the pin that way)."""
    rc = json.loads((HERE / "analysis" / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]
    out = {"revC": {k: round(math.degrees(math.atan2(v["fz"], v["fy"])), 1) for k, v in rc.items() if k != "hinge"},
           "sim_im3": {}}
    if SIMFORCES.exists():
        d = json.loads(SIMFORCES.read_text())
        for run, v in d.items():
            for side in "RL":
                f = v["forces"].get(f"hook_im520_{side}", {}).get("f")
                if f:
                    out["sim_im3"][f"{run}|{side}"] = {
                        "theta": round(math.degrees(math.atan2(f[2], f[1])), 1),
                        "lateral_deg": round(math.degrees(math.atan2(abs(f[0]), math.hypot(f[1], f[2]))), 1)}
    # kit ends -> simulated torso (h1_sleeve ASSUMPTION SIM_TORSO)
    from huntkit.gendesign import h1_sleeve as HS
    out["kit_ends"] = {f"{k} {t:g} in": HS.sim_torso(t) for k, ts in HS.KITS.items() if k != "h1" for t in (ts[0], ts[-1])}
    return out


def us_cradle_theta(name: str) -> float:
    """ASSUMPTION US-ROUTE: in bag-on carry the under-strap leaves its pin on the straight line to its floor channel
    (corrie_f.us_channels: US1 -> the aft channel, US2 -> the fore channel, at the floor seam line). The other reading,
    the strap hugging B-01 straight down to the floor corner (theta about -88), is reported as found-not-fixed: it
    runs into the fairlead below (US1: the hinge; see ``check`` rows at -75 / -90)."""
    import corrie_f as F
    H = _H()
    u = F.us_channels()
    p = next(q for q in H.placed() if q["id"] == f"{name}_R")
    y = p["yc"] + _BA().PANEL_OFFSET + u["stations_mm"][0 if name == "us1" else 1]
    return round(math.degrees(math.atan2(F.BC.Z0 - p["z"], y - p["y_pin"])), 1)


def required_pulls(pulls: dict) -> dict:
    """The pull directions each station must clear: IM3 every sim torso (both sides) and rev C; IM1 / IM2 rev C (IM2's
    side-hill case is straight down); US1 / US2 the cradle line (ASSUMPTION US-ROUTE)."""
    sims = [v["theta"] for v in pulls["sim_im3"].values()]
    rc = pulls["revC"]
    out = {"im1": [rc["im1"]], "im2": [rc["im2"]], "im3": sorted({rc["im3"], *(([min(sims), max(sims)]) if sims else [])}),
           "us1": [us_cradle_theta("us1")], "us2": [us_cradle_theta("us2")]}
    return out


def check(meshes: dict | None = None) -> dict:
    import trimesh
    H = _H()
    meshes = meshes or {"im3ec": trimesh.load(IM3EC), "print": trimesh.load(PRINT)}
    res = {"pieces": {"im3ec": str(IM3EC.relative_to(ROOT)), "print": str(PRINT.relative_to(ROOT))}, "stations": {}}
    for p in H.placed():
        if p["name"] not in STATIONS:
            continue
        for src, mesh in meshes.items():
            if src == "im3ec" and p["id"] != "im3_R":
                continue
            spec = eye_spec(p["name"], p["side"])
            ts = sorted({P.HE_T_RANGE[0], P.HE_T, P.HE_T_RANGE[1]})
            up = {f"{t}": under_pin(mesh, p, spec, t) for t in ts}
            thr = throat(mesh, p)
            sw = sweep(mesh, p, spec)
            r = {"station": p["id"], "piece": spec["piece"], "src": src,
                 "worst_under_pin_clear_mm": min(v["worst"]["clear_mm"] for v in up.values()),
                 "min_clear_off_corner_mm": min(v["clear_off_corner_mm"] for v in up.values()),
                 "floor_depth_centre_mm": up[f"{P.HE_T}"]["floor_depth_centre_mm"],
                 "throat_min_mm": round(thr, 2),
                 "throat_clear_side_mm": round((thr - P.HE_NECK_W - P.HE_NECK_TOL) / 2, 2),
                 "under_pin": up, "sweep": sw}
            r["eye_pass"] = bool(r["worst_under_pin_clear_mm"] > 0.0 and r["min_clear_off_corner_mm"] >= 0.5
                                 and r["throat_clear_side_mm"] >= 0.5 - 0.05)
            res["stations"][f"{p['id']}@{src}"] = r
    res["pulls"] = pull_directions()
    st = res["stations"]
    req = required_pulls(res["pulls"])
    res["required_pulls"] = req
    for k, v in st.items():
        name = k.split("_")[0]
        ok = [r["theta"] for r in v["sweep"]["rows"] if r["pass"]]
        v["required_thetas"] = req[name]
        # a required direction is covered when both swept directions that bracket it pass (eye, box and strap)
        v["route_ok"] = all(math.floor(t / 15) * 15 in ok and math.ceil(t / 15) * 15 in ok for t in req[name])
        v["eye_pass"] = bool(v["eye_pass"] and v["route_ok"])
    res["eye_pass_all"] = all(v["eye_pass"] for v in st.values())
    res["box_clear_thetas"] = {k: v["sweep"]["clear_thetas"] for k, v in st.items()}
    res["assumptions"] = ["HE-STACK / HE-FOLD-R as he_stl_check (IME); US / USA booked at 2 plies across",
                          "SIM_TORSO (h1_sleeve): a kit end takes the pull direction of the nearest simulated torso",
                          "IMUS-TAUT: the eye is a taut teardrop from the pin to its box; a slack eye lies inside it"]
    return res


def figures(res: dict, meshes: dict) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import MultiPolygon
    H = _H()
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    picks = [("im3_R", "im3ec", -90), ("im2_R", "print", -90), ("us1_L", "print", -45), ("us1_R", "print", -90)]
    fig, axs = plt.subplots(1, 4, figsize=(16, 5.6))
    pl = {p["id"]: p for p in H.placed()}
    for ax, (sid, src, th) in zip(axs, picks):
        p = pl[sid]
        spec = eye_spec(p["name"], p["side"])
        S = H._xplane(meshes[src], p["x"])
        for poly in (S.geoms if isinstance(S, MultiPolygon) else [S]):
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, fc="#8aa", ec="#344", lw=0.7)
            for hole in poly.interiors:
                hx, hy = hole.xy
                ax.fill(hx, hy, fc="white", ec="#344", lw=0.5)
        for tt, col in ((0, "#1a7f37"), (th, "#c0392b")):
            eye, box, _ = eye_shapes(spec, p, P.HE_T_RANGE[1], spec["plies_ridge"] * P.HE_T_RANGE[1], tt)
            for g, a in ((eye, 0.8), (box, 0.5)):
                for q in (g.geoms if hasattr(g, "geoms") else [g]):
                    ex, ey = q.exterior.xy
                    ax.fill(ex, ey, fc=col, alpha=a * 0.6, ec=col, lw=0.6)
        ax.add_patch(plt.Circle((p["y_pin"], p["z"]), 2.5, fc="#222"))
        r = res["stations"][f"{sid}@{src}"]
        ax.set_title(f"{sid} {spec['piece']} on {src}\nunder pin {r['worst_under_pin_clear_mm']:.2f} mm (off corner "
                     f"{r['min_clear_off_corner_mm']:.2f}), throat {r['throat_min_mm']:.1f}\npull 0 deg green, "
                     f"{th} deg red; box clear at {min(r['sweep']['clear_thetas'], default='none')}..{max(r['sweep']['clear_thetas'], default='')} deg",
                     fontsize=8.5, loc="left")
        ax.set_xlim(p["yc"] - 22, p["yc"] + 70)
        ax.set_ylim(p["z"] - 75, p["z"] + 30)
        ax.set_aspect("equal")
        ax.set_xlabel("frame y (mm, to the bag)")
    axs[0].set_ylabel("frame z (mm)")
    fig.suptitle("BL-044 necked IME / US eyes laid into the printed IM / US fairleads (x slice at the neck centre). "
                 "STL grey; eye (1.6 mm ply) + box/strap", fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout()
    p1 = SCREENS / f"{SHOT}_1.png"
    fig.savefig(p1, dpi=95)
    plt.close(fig)
    out.append(p1)
    return out


def main(argv=None) -> int:
    import trimesh
    meshes = {"im3ec": trimesh.load(IM3EC), "print": trimesh.load(PRINT)}
    res = check(meshes)
    OUT_JSON.write_text(json.dumps(res, indent=1))
    for k, v in res["stations"].items():
        print(k, v["piece"], "under", v["worst_under_pin_clear_mm"], "off", v["min_clear_off_corner_mm"], "throat",
              v["throat_min_mm"], "eye_ok", v["sweep"]["eye_ok_all"], "box thetas", v["sweep"]["clear_thetas"],
              "req", v["required_thetas"], "route_ok", v["route_ok"], "PASS", v["eye_pass"])
    print("pulls", res["pulls"])
    for p in figures(res, meshes):
        print("screen:", p)
    return 0 if res["eye_pass_all"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
