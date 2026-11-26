"""BL-086 global pass: the B85 beam model (``bl081_concept_b.build`` + the BL-085 pinned mid saddle) with the BL-086
changes applied, on the full HA-LS-1 rev C envelope **including C6p**, in the BL-081 result format (stations, links,
member end forces, hip pin), but with the fatigue walk taken as the **walk envelope** (ASSUMPTION WALK-ENV, BL-085):
static carry x 1.6 (both couple tops) and meat_straps x 1.6 / 2.0. BL-081 / BL-085 fed the non-tee local rows from the
bag-carry walk only; BL-086 feeds every row from the envelope.

The BL-081 evaluator (``bl081_concept_b.evaluate_global``) is not edited; this is a copy with three differences:
C6p kept, walk envelope, and the BL-086 model changes (``build``).

Units mm, N, MPa. Cached in outputs/bl086/global_<tag>.json (about 15 s per run).
"""
from __future__ import annotations

import copy
import json
import time

import numpy as np

from huntkit.gendesign import bl080_metal_frame as B80
from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl085_global as G85

CACHE = BQ.REPO / "outputs" / "bl086"
WALK_CASES = dict(G85.WALK_CASES)          # {"static_carry": 1.0, "meat_straps": 2.0}


def sleeve_section(stay_key: str, sleeve: dict):
    """Composite section of a stay with a BONDED outer sleeve (equal E, perfect bond: section properties add)."""
    from huntkit.fea.sections import generic, tube_round
    a = tube_round(BQ.STOCK[stay_key]["od"], BQ.STOCK[stay_key]["t"])
    b = tube_round(sleeve["od"], sleeve["t"])
    s = generic(a.A + b.A, a.Iy + b.Iy, a.Iz + b.Iz, a.J + b.J, ymax=sleeve["od"] / 2, zmax=sleeve["od"] / 2,
                Wt=(a.J + b.J) / (sleeve["od"] / 2))
    s.kind = "tube_sleeved"
    s.dims = {"od": sleeve["od"], "t": sleeve["t"], "core_od": BQ.STOCK[stay_key]["od"], "core_t": BQ.STOCK[stay_key]["t"]}
    return s


def _split_stays(m: dict, zs) -> None:
    """Make sure the stays have nodes at each z in zs (so a sleeve starts / stops exactly there)."""
    nodes = m["nodes"]
    for z in zs:
        for tag in "LR":
            nid = f"S{tag}{z:g}"
            if nid in nodes:
                continue
            for mm in list(m["members"]):
                if mm["group"].startswith("stay") and mm["group"].endswith(tag):
                    a_, b_ = mm["nodes"]
                    za, zb = nodes[a_][2], nodes[b_][2]
                    if min(za, zb) < z < max(za, zb):
                        pa, pb = np.array(nodes[a_]), np.array(nodes[b_])
                        nodes[nid] = list(map(float, pa + (z - za) / (zb - za) * (pb - pa)))
                        m["members"].append({**mm, "id": f"{nid}-{b_}", "nodes": [nid, b_]})
                        mm["nodes"], mm["id"] = [a_, nid], f"{a_}-{nid}"
                        break


def build(cfg: dict | None = None, torso: float = 19.0, rigid: bool = False) -> dict:
    """B85 + BL-086 changes. cfg keys used beyond BL-081's: ``mid_tee`` ("saddle"), ``stay_sleeve`` (None or
    {"od", "t", "z0", "z1"}: bonded outer doubler on both stays over z0..z1, credited as a composite section),
    ``rung_sleeve`` (None or {"od", "t", "x0"}: bonded doubler on both rungs over |x| <= x0)."""
    cfg = {**BQ.CFG0, **(cfg or {})}
    m = copy.deepcopy(BQ.build(cfg, torso, rigid))
    if not rigid and cfg.get("mid_tee") == "saddle":
        for ln in m["links"]:
            if ln["id"] in ("tee_L330", "tee_R330"):
                ln["k"] = list(G85.SADDLE_K)
    if not rigid and cfg.get("upper_tie") == "saddle":
        # BL-086 upper hip tie: printed compression saddle between the post front leg and the upper rung (no bolt, no
        # hole in the rung): stiff along the tie (y, compression in every case but the 33 N set-down reversal, which
        # the positioning band holds) and across it in z (bearing on the saddle lip); along the rung (x) friction only
        # (ASSUMPTION TIE-SADDLE-K: 100 N/mm, so the lower ties and the gussets carry the lateral load)
        for ln in m["links"]:
            if ln["id"] in (f"tie_L{cfg['rung_z'][1]:g}", f"tie_R{cfg['rung_z'][1]:g}"):
                ln["k"] = [100.0, 3.0e4, 2.0e4, 0.0, 0.0, 0.0]
    nodes = m["nodes"]
    ld = cfg.get("leg_doubler")
    if ld:
        # BL-086 front-leg doubler strips sit between the Ti mount and the front leg: the mount face and the hip pin
        # move forward by the strip thickness (longer stand-off, so a slightly larger tipping couple on the post)
        nodes["HP"] = [nodes["HP"][0], nodes["HP"][1] - ld["t"], nodes["HP"][2]]
    sv = cfg.get("stay_sleeve")
    if sv:
        _split_stays(m, (sv["z0"], sv["z1"]))
        sec = sleeve_section(cfg["stay"], sv)
        for mm in m["members"]:
            if mm["group"].startswith("stay"):
                za, zb = (nodes[n][2] for n in mm["nodes"])
                if sv["z0"] - 1e-6 <= min(za, zb) and max(za, zb) <= sv["z1"] + 1e-6:
                    mm["section"] = sec
    rv = cfg.get("rung_sleeve")
    if rv:
        sec = sleeve_section(cfg["ctube"], rv)
        for mm in m["members"]:
            if mm["group"] == "lumbar_cross_tube":
                xa, xb = (nodes[n][0] for n in mm["nodes"])
                if max(abs(xa), abs(xb)) <= rv["x0"] + 1e-6:
                    mm["section"] = sec
    return m


ZONES = {"stay leg-end zone": (171.0, 420.0), "stay top zone": (470.0, 545.0)}


def zone_stations(m: dict, cfg: dict) -> list[dict]:
    """Extra stay stations (no hole, forces only): the rung-plug contact points and every stay node in the leg-end
    bushing travel (z 171-374, nearest nodes 171-380) and the stay-top bushing zone."""
    out = []
    for tag in "LR":
        for z in cfg["rung_z"]:
            out.append({"name": f"stay at plug z{z:g} {tag}", "node": f"S{tag}{z:g}", "group": "stay", "axis": "y",
                        "tube": cfg["stay"], "link": None})
        for nid, p in m["nodes"].items():
            if nid.startswith(f"S{tag}") and nid[2:].replace(".", "").isdigit():
                for zname, (z0, z1) in ZONES.items():
                    if z0 <= p[2] <= z1:
                        out.append({"name": f"{zname} {tag} {nid}", "node": nid, "group": "stay", "axis": "y",
                                    "tube": cfg["stay"], "link": None})
    return out


def evaluate(cfg: dict | None = None, torsos=BQ.TORSOS, log=print) -> dict:
    """BL-081-format global result on the BL-086 model, C6p included, walk = envelope (WALK_CASES)."""
    from huntkit.fea.load_standard import ls1_envelope
    cfg = {**BQ.CFG0, **(cfg or {})}
    env = ls1_envelope()
    out = {"strength": {}, "buckling": None, "links": {}, "stations": {}, "walk": {}, "deflection": {},
           "members_util": {}, "case_list": [], "walk_cases": WALK_CASES, "c6p": {}}
    for t in torsos:
        m = build(cfg, t)
        sts = BQ.stations(cfg) + zone_stations(m, cfg)
        for var, cases in env.items():
            for case in cases:
                r = case.run(m)
                req = float(r.meta["required_sf"])
                key = f"{case.name}|{var}|{t:g}"
                out["case_list"].append(key)
                wg = WALK_CASES.get(case.name)
                wf = BQ.G_WALK / wg if wg else None
                for mm in r.members:
                    role = BQ._role(mm["group"])
                    if role is None or B80._mid(mm["material"]) == B80.SOFT_MAT["id"]:
                        continue
                    marg = mm["sf"] / req
                    u = out["members_util"].get(mm["id"])
                    if u is None or 1 / marg > u:
                        out["members_util"][mm["id"]] = 1 / marg
                    cur = out["strength"].get(role)
                    if cur is None or marg < cur["margin"]:
                        out["strength"][role] = {"margin": float(marg), "case": key, "member": mm["id"],
                                                 "sf": float(mm["sf"]), "required": req}
                    if case.name == "tall_load_posts":
                        c = out["c6p"].get(role)
                        if c is None or marg < c["margin"]:
                            out["c6p"][role] = {"margin": float(marg), "case": key, "member": mm["id"]}
                bf = r.buckling_sf
                if np.isfinite(bf):
                    mg = bf / (1.5 * req)
                    if out["buckling"] is None or mg < out["buckling"]["margin"]:
                        out["buckling"] = {"margin": float(mg), "eigen": float(bf), "case": key}
                lf = r.meta["link_forces"]
                for lid, f in lf.items():
                    fv = np.asarray(f, float) * req
                    cur = out["links"].get(lid)
                    mag = float(np.linalg.norm(fv[:3]))
                    if cur is None or mag > cur["F"]:
                        out["links"][lid] = {"F": mag, "vec": fv.tolist(), "case": key}
                    cur = out["links"].get(lid + "|M")
                    mm_ = float(np.linalg.norm(fv[3:]))
                    if cur is None or mm_ > cur["M"]:
                        out["links"][lid + "|M"] = {"M": mm_, "vec": fv.tolist(), "case": key}
                for s in sts:
                    for mid in BQ._members_at(r, s["node"], s["group"]):
                        try:
                            f, R = BQ.station_forces(r, mid, s["node"])
                        except KeyError:
                            continue
                        rec = {"f": (f * req).tolist(), "R": R.tolist(), "case": key, "member": mid,
                               "link": (np.asarray(lf[s["link"]]) * req).tolist() if s.get("link") else None}
                        out["stations"].setdefault(s["name"], []).append(rec)
                        if wf:
                            rw = {"f": (f * wf).tolist(), "R": R.tolist(), "case": key, "member": mid,
                                  "link": (np.asarray(lf[s["link"]]) * wf).tolist() if s.get("link") else None}
                            out["walk"].setdefault(s["name"], []).append(rw)
                for mm in r.members:
                    if mm["group"] in ("lumbar_gusset", "hip_bracket", "hip_ties"):
                        rec = {"case": key, "req": req, "start": (np.asarray(mm["end_forces"][0]) * req).tolist(),
                               "end": (np.asarray(mm["end_forces"][1]) * req).tolist()}
                        out.setdefault("members_f", {}).setdefault(mm["id"], []).append(rec)
                        if wf:
                            rw = {"case": key, "start": (np.asarray(mm["end_forces"][0]) * wf).tolist(),
                                  "end": (np.asarray(mm["end_forces"][1]) * wf).tolist()}
                            out.setdefault("members_w", {}).setdefault(mm["id"], []).append(rw)
                hp = np.asarray(r.reactions.get("HP", np.zeros(6)), float)
                out.setdefault("hip_pin", []).append({"case": key, "req": req, "F": (hp[:3] * req).tolist(),
                                                      "walk": (hp[:3] * wf).tolist() if wf else None})
                if wf:
                    out["walk"].setdefault("_links", []).append(
                        {"case": key, "links": {k: (np.asarray(v) * wf).tolist() for k, v in lf.items()}})
                    if case.name == "static_carry" and var == "crown_bar":
                        out["deflection"][f"{t:g}"] = BQ.t1_deflection(r)
        log(f"  BL-086 global torso {t:g} done")
    return out


def cached(tag: str, cfg: dict | None = None, log=print, refresh: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"global_{tag}.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    t0 = time.time()
    g = evaluate(cfg, log=log)
    g["seconds"] = round(time.time() - t0, 1)
    p.write_text(json.dumps(g, default=float))
    return json.loads(p.read_text())
