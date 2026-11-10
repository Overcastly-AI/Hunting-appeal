"""Cloth-sim runs for CACHE (team D). The CACHE shell is CORRIE rev B's shell (same B-01, gussets, aft face with the
horseshoe door, floor and collar to the same fill line; the drawcord channel replaces the roll hem, which the sim does
not model for CORRIE either: the collar closes flat at the fill line). So the pattern loader is CORRIE's,
re-labelled; what changes are the external loads (lid module on the cinched closure, optics pod on the 4 loops).

    python designs/pack_5200/bag_comp/D/clothsim_cache.py 15 [19 23]     # coarse h 40 mm, cases packed, fill, meat
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from huntkit.clothsim import cli, corrie_bag  # noqa: E402

_orig = corrie_bag.load_corrie_patterns


def load_cache_patterns(verbose=True) -> dict:
    out = _orig(verbose)
    out["release"] = "concept: designs/pack_5200/bag_comp/D/cache.py (shell = CORRIE rev B shell pieces)"
    return out


corrie_bag.load_corrie_patterns = load_cache_patterns


def run(torso: int):
    a = argparse.Namespace(scenario=str(HERE / "scenarios" / f"cache_PR{torso}.yaml"), time_cap=None,
                           out=str(ROOT / "outputs" / "clothsim" / f"bagD_cache_PR{torso}"), fine=False,
                           cases="packed,fill,meat", verbose=False, no_sweep=True, no_render=True,
                           screens=str(ROOT / "outputs" / "screens"), date="20261110")
    return cli.cmd_run(a)


if __name__ == "__main__":
    for t in sys.argv[1:] or ["15", "19", "23"]:
        run(int(t))
