"""BL-085 global pass on the B81 aluminium ladder: the BL-081 beam model (``bl081_concept_b.build``, unchanged), run on
the FULL HA-LS-1 rev C envelope **including C6p** (``tall_load_posts``; BL-081 / BL-083 skipped it, review 9 M2), with
the stay section forces recorded at both tee stations (z 330 and z 520, the stay member above and below each tee
node) so the tee checks use the real stay stress at the tee, not the worst stay stress anywhere in the frame.

Walking (fatigue) set, ASSUMPTION WALK-ENV: the HA-LS-1 fatigue load is 0 -> 1.6 g x 68 kg. BL-081 took it from the
bag-carry case only (static carry x 1.6). A meat pack-out walks too, so BL-085 takes the envelope of
static carry (both couple tops) x 1.6 / 1.0 and meat_straps x 1.6 / 2.0 (its case g is 2.0; the 150 N cinch is
scaled with it, a small conservatism).

Units mm, N, MPa. Results are cached in outputs/bl085/global_<tag>.json (about 4 min per torso on 4 cores).
"""
from __future__ import annotations

import json
import time

import numpy as np

from huntkit.gendesign import bl080_metal_frame as B80
from huntkit.gendesign import bl081_concept_b as BQ

CACHE = BQ.REPO / "outputs" / "bl085"
TEE_Z = (330.0, 520.0)
WALK_CASES = {"static_carry": 1.0, "meat_straps": 2.0}      # case name -> its g level (walk = case x 1.6 / g)


def tee_stations(cfg: dict) -> list[dict]:
    out = []
    for z in TEE_Z:
        for tag in "LR":
            out.append({"name": f"stay at tee z{z:g} {tag}", "node": f"S{tag}{z:g}", "group": "stay", "z": z, "tag": tag})
    return out


# BL-085 mid tee: a pinned saddle (printed PAHT-CF saddle socket on the mid-bar end, bearing on the stay, held on by a
# hose band at positioning tension, no metal clamp on the stay). Link: bearing across the stay (x, y) as stiff as the
# B81 clamp link; along the stay only the band friction (ASSUMPTION SADDLE-KZ 200 N/mm, a positioning spring whose
# force is checked against the band's minimum friction); rotations free (1e3 N mm / rad keeps the bar's torsion mode
# non-singular).
SADDLE_K = [BQ.CLAMP_KT, BQ.CLAMP_KT, 200.0, 1.0e3, 1.0e3, 1.0e3]


def build(cfg: dict, torso: float) -> dict:
    m = BQ.build(cfg, torso)
    if cfg.get("mid_tee") == "saddle":
        for ln in m["links"]:
            if ln["id"] in ("tee_L330", "tee_R330"):
                ln["k"] = list(SADDLE_K)
    return m


def evaluate(cfg: dict | None = None, torsos=BQ.TORSOS, include_c6p: bool = True, log=print) -> dict:
    """Member margins by role, buckling, tee link forces (factored), stay section forces at the tees (factored and
    walk), for every case of ``ls1_envelope`` (with C6p when ``include_c6p``)."""
    from huntkit.fea.load_standard import ls1_envelope
    cfg = {**BQ.CFG0, **(cfg or {})}
    env = ls1_envelope()
    out = {"strength": {}, "buckling": None, "links": {}, "tee_stay": {}, "tee_stay_walk": {}, "cases": [],
           "c6p": {"included": include_c6p}}
    sts = tee_stations(cfg)
    for t in torsos:
        m = build(cfg, t)
        for var, cases in env.items():
            for case in cases:
                if case.name == "tall_load_posts" and not include_c6p:
                    continue
                r = case.run(m)
                req = float(r.meta["required_sf"])
                key = f"{case.name}|{var}|{t:g}"
                out["cases"].append(key)
                for mm in r.members:
                    role = BQ._role(mm["group"])
                    if role is None or B80._mid(mm["material"]) == B80.SOFT_MAT["id"]:
                        continue
                    marg = mm["sf"] / req
                    cur = out["strength"].get(role)
                    if cur is None or marg < cur["margin"]:
                        out["strength"][role] = {"margin": float(marg), "case": key, "member": mm["id"],
                                                 "sf": float(mm["sf"]), "required": req}
                    if case.name == "tall_load_posts":
                        c = out["c6p"].setdefault(role, {"margin": np.inf})
                        if marg < c["margin"]:
                            out["c6p"][role] = {"margin": float(marg), "case": key, "member": mm["id"]}
                bf = r.buckling_sf
                if np.isfinite(bf):
                    mg = bf / (1.5 * req)
                    if out["buckling"] is None or mg < out["buckling"]["margin"]:
                        out["buckling"] = {"margin": float(mg), "eigen": float(bf), "case": key}
                lf = r.meta["link_forces"]
                for lid, f in lf.items():
                    if not lid.startswith(("tee_", "pawl", "bush_top")):
                        continue
                    fv = np.asarray(f, float) * req
                    out["links"].setdefault(lid, []).append({"case": key, "vec": fv.tolist()})
                for s in sts:
                    for mid in BQ._members_at(r, s["node"], s["group"]):
                        try:
                            f, R = BQ.station_forces(r, mid, s["node"])
                        except KeyError:
                            continue
                        side = "above" if r.model["nodes"][[n for n in mid.split("-") if n != s["node"]][0]][2] > \
                            r.model["nodes"][s["node"]][2] else "below"
                        rec = {"f": (f * req).tolist(), "case": key, "member": mid, "side": side}
                        out["tee_stay"].setdefault(s["name"], []).append(rec)
                        if case.name in WALK_CASES:
                            g = WALK_CASES[case.name]
                            rw = {"f": (f * BQ.G_WALK / g).tolist(), "case": key, "member": mid, "side": side}
                            out["tee_stay_walk"].setdefault(s["name"], []).append(rw)
                if case.name in WALK_CASES:
                    g = WALK_CASES[case.name]
                    for lid, f in lf.items():
                        if lid.startswith("tee_"):
                            out["links"].setdefault(lid + "|walk", []).append(
                                {"case": key, "vec": (np.asarray(f, float) * BQ.G_WALK / g).tolist()})
        log(f"  global torso {t:g} done")
    return out


def cached(tag: str = "b81", cfg: dict | None = None, log=print) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"global_{tag}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    g = evaluate(cfg, log=log)
    g["seconds"] = round(time.time() - t0, 1)
    p.write_text(json.dumps(g, default=float))
    return g


def section_stress(f6, od: float, t: float) -> dict:
    """Beam stresses of a round tube from section forces (N, Vy, Vz, T, My, Mz): extreme-fibre axial and torsion
    shear."""
    ro, ri = od / 2, od / 2 - t
    A = np.pi * (ro ** 2 - ri ** 2)
    I = np.pi * (ro ** 4 - ri ** 4) / 4
    N, Vy, Vz, T, My, Mz = f6
    s = abs(N) / A + np.hypot(My, Mz) * ro / I
    tau = abs(T) * ro / (2 * I)
    return {"sigma": float(s), "tau": float(tau), "M": float(np.hypot(My, Mz)), "N": float(N)}


if __name__ == "__main__":     # pragma: no cover
    import sys
    tag = sys.argv[1] if len(sys.argv) > 1 else "b81"
    g = cached(tag, {"mid_tee": "saddle"} if tag == "b85" else None)
    print(json.dumps({"strength": g["strength"], "buckling": g["buckling"], "c6p": g["c6p"]}, indent=1, default=str))
