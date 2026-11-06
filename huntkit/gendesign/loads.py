"""Frame-model load extraction for the generative-design studies.

Runs the Pack 5200 frame (designs/pack_5200/frame.yaml, built by huntkit.fea) through the current
load standard (HA-LS-1 from huntkit.fea.load_standard if present, else the v1 pack5200 cases) at
torso 15 / 19 / 23 in, and returns per-joint member END forces in global axes (the force each
tube exerts ON the joint node), per case, torso and side.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

# HUNTKIT_GENDESIGN_FRAME pins the study to a frame.yaml snapshot (the frame is re-sized by other runs)
FRAME_YAML = Path(os.environ.get("HUNTKIT_GENDESIGN_FRAME", REPO_ROOT / "designs" / "pack_5200" / "frame.yaml"))
TORSOS = (15, 19, 23)


def standard_cases():
    """(cases, standard name, fatigue g)."""
    try:
        from huntkit.fea.load_standard import FATIGUE, NAME, ls1_cases
        # the lug / gendesign studies are rev B records (bag 180 mm on C1-C4): pinned so they reproduce
        return ls1_cases(180.0, rev="B"), NAME + " rev B", float(FATIGUE["g"])
    except Exception:            # pragma: no cover - older trees
        from huntkit.fea.sizing5200 import cases
        return cases(), "v1 (pack5200_cases)", 1.2


def frame_model(torso_in: float, posts: bool = False, **over) -> dict:
    from huntkit.fea.frames import build_frame_from_yaml
    return build_frame_from_yaml(FRAME_YAML, torso_in=float(torso_in), extension_posts=posts, **over)


def member_end_global(res, member_id: str, node_id: str) -> np.ndarray | None:
    """6-vector [F, M] exerted BY the member ON the node, global axes (None if not attached)."""
    mi = next((i for i, m in enumerate(res.members) if m["id"] == member_id), None)
    if mi is None:
        return None
    ni = res.node_ids.index(node_id)
    for e in res.members[mi]["elements"]:
        el = res.elements[e]
        R = el.T[:3, :3]
        if el.n1 == ni:
            f = res.elem_forces[e, 0]
        elif el.n2 == ni:
            f = -res.elem_forces[e, 1]
        else:
            continue
        return np.r_[R.T @ f[:3], R.T @ f[3:]]
    return None


def external_on_node(res, model, node_id: str) -> np.ndarray:
    """Applied load + support/spring reaction on a user node (global, forces only + moments)."""
    out = np.zeros(6)
    f = (res.model.get("loads") or {}).get(node_id)
    if f is not None:
        out[: len(f)] += np.asarray(f, float)
    r = res.reactions.get(node_id)
    if r is not None:
        out += r
    fi = res.meta.get("inertia_forces")
    if fi is not None:
        i = res.node_ids.index(node_id)
        out += fi[6 * i: 6 * i + 6]
    return out


def run_all(torsos=TORSOS, log=print, **over) -> dict:
    """Solve every case at every torso. Returns {(case, torso): (result, model)} plus metadata."""
    cases, std, fat_g = standard_cases()
    out = {}
    for t in torsos:
        fm = frame_model(t, **over)
        fmp = None
        for c in cases:
            c = copy.copy(c)
            c.buckling = False
            m = fm
            if c.name == "tall_load_posts":
                fmp = fmp or frame_model(t, posts=True, **over)
                m = fmp
            out[(c.name, t)] = (c.run(m), m, c)
        if log:
            log(f"  frame cases solved at torso {t} in ({len(cases)} cases, standard {std})")
    return {"runs": out, "standard": std, "fatigue_g": fat_g, "cases": [c.name for c in cases]}


MIRROR = np.diag([-1.0, 1.0, 1.0])


def mirror6(v):
    """Reflect a [F, M] vector through the x = 0 plane (M is a pseudo-vector)."""
    v = np.asarray(v, float)
    return np.r_[MIRROR @ v[:3], -(MIRROR @ v[3:])]


def mirror_pt(p):
    return MIRROR @ np.asarray(p, float)
