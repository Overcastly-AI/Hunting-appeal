"""Driver for the printed whole-frame study (designs/pack_5200/analysis/printed_frame_study.md).

Stages (cached in outputs/genframe/):
  loads     beam-model interface loads, HA-LS-1 rev B, 9 cases x torso 15/19/23  -> loadsets.pkl
  simp      SIMP sweep over the volume fraction (pure printed) + hybrid (printed + pultruded CF rods)
  verify    up-sampled, thresholded, independent solid-voxel FE re-check of every result, all 27 sets
  report    materials evaluation, segmentation, print files, renders, Markdown

  python -m huntkit.gendesign.frame_study simp --vf 0.05 [--hybrid]
  python -m huntkit.gendesign.frame_study verify --tag pure_0.050
"""
from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

from . import frame_topopt as ft

OUT = REPO_ROOT / "outputs" / "genframe"

ROD_D = 4.0                  # mm pultruded CF rod (data/materials/composites/cfrp_pultruded_rod_tube.yaml)
ROD_E = 125000.0
MATRIX_FOR_HYBRID_E = 4430.0     # PA6-CF FDM (pa6_cf_fdm_bambu, XY)
ROD_OFFSET = 13.5            # rod axis offset fore / aft of the sleeve axis (y): rod touches the sleeve OD


def log(msg):
    print(msg, flush=True)


def loadsets(force=False):
    p = OUT / "loadsets.pkl"
    if p.exists() and not force:
        return pickle.loads(p.read_bytes())
    OUT.mkdir(parents=True, exist_ok=True)
    sets = ft.beam_loadsets(log=log)
    p.write_bytes(pickle.dumps(sets))
    return sets


def rod_lines(env: ft.Envelope) -> list:
    """Hybrid H1: 4 straight pultruded rods per frame, 2 per side, fore + aft of the crown sleeve axis,
    from the foot (z 8) to the stay top (z 538): they become the flanges of each printed stay."""
    out = []
    for s in (1, -1):
        for off, nm in ((ROD_OFFSET, "aft"), (-ROD_OFFSET, "fore")):
            p0 = np.array([s * 115.0, env.sleeve_y(8.0) + off, 8.0])
            p1 = np.array([s * 115.0, env.sleeve_y(538.0) + off, 538.0])
            out.append((p0, p1, f"rod_{'R' if s > 0 else 'L'}_{nm}"))
    return out


def hybrid_rods(matrix_E=MATRIX_FOR_HYBRID_E, d=ROD_D, E=ROD_E):
    A = np.pi * d * d / 4

    def fn(dom: ft.Domain):
        return [ft.Rod(p0, p1, A, E / matrix_E, nm) for p0, p1, nm in rod_lines(dom.env)]
    return fn


def rod_sheath(dom: ft.Domain, r=3.5):
    """Solid printed sheath around each rod channel (passive solid in the hybrid run)."""
    c = dom.grid.elem_centers()
    m = np.zeros(dom.grid.ne, bool)
    for p0, p1, _ in rod_lines(dom.env):
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        v = c - p0
        t = np.clip(v @ d, 0, np.linalg.norm(p1 - p0))
        dist = np.linalg.norm(v - t[:, None] * d, axis=1)
        m |= dist < max(r, 0.75 * dom.h)
    return m & ~dom.passive_void


def _patch_build_domain_for_hybrid():
    orig = ft.build_domain

    def bd(h=4.0, env=None, sleeve_wall=ft.SLEEVE_WALL):
        d = orig(h, env, sleeve_wall)
        sh = rod_sheath(d)
        d.passive_solid = d.passive_solid | sh
        d.masks["rod_sheath"] = sh
        return d
    return orig, bd


def run_simp(vf: float, hybrid=False, it_coarse=40, it_fine=24, snaps=False):
    sets = loadsets()
    tag = f"{'hybrid' if hybrid else 'pure'}_{vf:.3f}"
    snapl = [] if snaps else None
    t0 = time.time()
    orig = None
    if hybrid:
        orig, bd = _patch_build_domain_for_hybrid()
        ft.build_domain = bd
    try:
        r = ft.run_optimization(sets, vf, it_coarse=it_coarse, it_fine=it_fine, log=log,
                                rods_fn=hybrid_rods() if hybrid else None, snap_every=4 if snaps else None,
                                snaps=snapl)
    finally:
        if orig is not None:
            ft.build_domain = orig
    of, oc = r["fine"], r["coarse"]
    ft.save_npz(OUT / f"{tag}.npz", xPhys=of.xPhys.astype(np.float32), x=of.x.astype(np.float32),
                xc=oc.xPhys.astype(np.float32), passive_void=r["domain_f"].passive_void)
    meta = {"tag": tag, "vf": vf, "hybrid": hybrid, "fine_keys": r["fine_keys"], "seconds": time.time() - t0,
            "design_volume_mm3": r["design_volume_mm3"], "passive_volume_mm3": r["passive_volume_mm3"],
            "rel_compliance": r["rel_compliance"],
            "history": [{k: v for k, v in h.items() if k != "comps"} for h in oc.history + of.history]}
    (OUT / f"{tag}.json").write_text(json.dumps(meta, indent=1))
    if snaps:
        (OUT / f"{tag}_snaps.pkl").write_bytes(pickle.dumps(snapl))
    log(f"{tag}: done in {meta['seconds']:.0f} s")
    return tag


def run_verify(tag: str, E_mat=1.0):
    sets = loadsets()
    meta = json.loads((OUT / f"{tag}.json").read_text())
    hybrid = meta["hybrid"]
    orig = None
    if hybrid:
        orig, bd = _patch_build_domain_for_hybrid()
        ft.build_domain = bd
    try:
        df = ft.build_domain(4.0)
        z = np.load(OUT / f"{tag}.npz")
        df.passive_void = z["passive_void"]
        t0 = time.time()
        vr = ft.verify(df, z["xPhys"], sets, up=2, rods_fn=hybrid_rods() if hybrid else None, log=log)
    finally:
        if orig is not None:
            ft.build_domain = orig
    rods_info = None
    if hybrid:
        rods_info = rod_stresses(vr, sets)
    res = {"tag": tag, "h": vr.h, "volume_mm3": vr.volume_mm3, "stress": vr.stress, "stiff": vr.stiff,
           "seconds": time.time() - t0, "rods": rods_info,
           "env_pct": {"vm99": float(np.percentile(vr.env_vm[~vr.exclude], 99)),
                       "sn99": [float(np.percentile(vr.env_s[~vr.exclude, d], 99)) for d in range(3)],
                       "tau99": [float(np.percentile(vr.env_t[~vr.exclude, d], 99)) for d in range(3)]}}
    (OUT / f"{tag}_verify.json").write_text(json.dumps(res, indent=1))
    np.savez_compressed(OUT / f"{tag}_verify.npz", solid=vr.solid, env_vm=vr.env_vm.astype(np.float32),
                        env_s=vr.env_s.astype(np.float32), env_t=vr.env_t.astype(np.float32), exclude=vr.exclude,
                        **{f"S_{k.replace('|', '_')}": v for k, v in vr.S.items()},
                        **{k: v for k, v in vr.disp.items()})
    log(f"{tag}: verified in {res['seconds']:.0f} s, volume {vr.volume_mm3 / 1e3:.0f} cm3, "
        f"vm99 env {res['env_pct']['vm99']:.1f} (E-normalized), torsion {vr.stiff.get('torsion_Nm_per_deg'):.4g}")
    return res


def rod_stresses(vr: ft.Verified, sets) -> dict:
    """Axial stress in every rod segment for every set (E_rod x strain), max tension / compression."""
    dv = vr.dom
    F, fixed = ft.assemble_loads(dv, sets, solid_mask=vr.solid)
    rods = hybrid_rods()(dv)
    U, _ = ft.solve_solid(dv, vr.solid, F, fixed, E=MATRIX_FOR_HYBRID_E, rods=rods)
    _, info = ft.rod_matrix(dv.grid, rods)
    nc = dv.grid.node_coords()
    out = {}
    for k, ls in enumerate(sets):
        u = U[:, k].reshape(-1, 3)
        smax, smin = 0.0, 0.0
        for inf in info:
            for a, b, l in inf["segs"]:
                e = (nc[b] - nc[a]) / l
                st = ROD_E * (u[b] - u[a]) @ e / l
                smax, smin = max(smax, st), min(smin, st)
        out[ls.key] = {"t": float(smax), "c": float(smin)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["loads", "simp", "verify"])
    ap.add_argument("--vf", type=float, default=0.05)
    ap.add_argument("--hybrid", action="store_true")
    ap.add_argument("--snaps", action="store_true")
    ap.add_argument("--tag")
    ap.add_argument("--it-coarse", type=int, default=40)
    ap.add_argument("--it-fine", type=int, default=24)
    a = ap.parse_args(argv)
    if a.stage == "loads":
        loadsets(force=True)
    elif a.stage == "simp":
        t = run_simp(a.vf, a.hybrid, a.it_coarse, a.it_fine, a.snaps)
        run_verify(t)
    elif a.stage == "verify":
        run_verify(a.tag)


if __name__ == "__main__":
    main()
