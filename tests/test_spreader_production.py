"""Production spreader = Sandwich v2 (owner 2026-11-05) on the socket-free branch frame.

Checks that the shipped frame print file has no d6L stay sockets, that the viz3d barrier is the sandwich,
and that the sandwich build files and the beginner README exist and agree with the recorded result."""
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PRINT = ROOT / "designs" / "pack_5200" / "print" / "frame"
CUT = ROOT / "designs" / "pack_5200" / "cut" / "spreader"


def test_production_frame_has_no_stay_sockets():
    trimesh = pytest.importorskip("trimesh")
    from huntkit.gendesign import spreader_layout as L
    m = trimesh.load(PRINT / "genframe_assembled.stl", force="mesh")
    v = np.asarray(m.vertices)
    lay = L.layout_by_key("d6L_tubes")
    sock = np.min([L._socket_sdf(v, t) for t in lay.tubes], axis=0)
    base = L.frame_sdf_layout(v, None)
    # vertices on a socket surface that are not on the base body: the socketed print has ~2900, the base body 0
    assert int(((np.abs(sock) < 0.6) & (base > 1.0)).sum()) < 20


def test_barrier_mesh_is_the_sandwich():
    meta = json.loads((PRINT / "genframe_barrier.json").read_text())
    assert meta["material"] == "carbon" and "Sandwich" in meta["label"]


def test_sandwich_build_files_and_readme():
    for f in ("spreader_v2_cut.dxf", "spreader_v2_clip.dxf", "spreader_v2_drawing.pdf", "README.md"):
        assert (CUT / f).exists(), f
    ezdxf = pytest.importorskip("ezdxf")
    doc = ezdxf.readfile(CUT / "spreader_v2_cut.dxf")
    layers = {e.dxf.layer for e in doc.modelspace()}
    assert {"CUT", "MARK"} <= layers
    # outline extents match the drawing: 242 x 318 mm, z 112-430
    xs, zs = [], []
    for e in doc.modelspace().query('LWPOLYLINE[layer=="CUT"]'):
        for x, z, *_ in e.get_points():
            xs.append(x)
            zs.append(z)
    assert max(xs) - min(xs) == pytest.approx(242.0, abs=1.0)
    assert max(zs) - min(zs) == pytest.approx(318.0, abs=1.0)
    r = json.loads((ROOT / "designs/pack_5200/analysis/spreader_results.json").read_text())
    assert r["chosen_key"] == "sw110c6d" and abs(r["chosen"]["mass_g"] - 154.0) < 1.0
    readme = (CUT / "README.md").read_text()
    assert "154 g" in readme and "ASSUMPTION:" in readme


def test_sandwich_recheck_clears_lean_torso():
    r = json.loads((ROOT / "designs/pack_5200/analysis/spreader_layout_results.json").read_text())
    assert r["sandwich_recheck"]["clear_fact_lean_min"] >= 0.0
