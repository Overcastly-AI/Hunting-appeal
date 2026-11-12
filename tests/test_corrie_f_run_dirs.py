"""BL-025: CORRIE F rev 0 and rev 1 cloth-sim runs live in separate folders, and each reader takes its own one."""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SIM = REPO / "designs" / "pack_5200" / "concepts" / "corrie_f_sim" / "corrie_f_sim.py"


def _cfs():
    spec = importlib.util.spec_from_file_location("corrie_f_sim_bl025", SIM)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_run_dir_names_carry_the_revision():
    m = _cfs()
    assert m.F.REVISION == 3 and m.F.sim_rev() == 1        # BL-030: revs 1-3 share the rev 1 simulated shell
    assert m.run_dir("Fr0", 15).name == "F_r0_PR15"
    assert m.run_dir("F", 23, "_fineFM").name == "F_r1_PR23_fineFM"
    assert m.run_dir("F", 15, "_fineFM_goff").name == "F_r1_PR15_fineFM_goff"
    assert m.run_dir("F", 19, "_fine").name == "F_PR19_fine"        # packed render drape keeps the viz3d name
    assert m.run_dir("F0", 23).name == "F0_PR23" and m.run_dir("S40", 15).name == "S40_PR15"


def test_loadpath_reads_rev0_runs():
    from huntkit.gendesign import loadpath_check as L
    out = L.corrie_f_loads()
    for t, fr in L.FROZEN["corrie_f_im3_1g"].items():
        r = out[t]
        if r["source"] == "live":
            # rev 0 folder, and the live value is the frozen rev 0 value (rev 1 F_r1_PR15 meat gives 547.7 N)
            assert r["run"] == f"F_r0_PR{t}"
            assert r["n_1g"] == pytest.approx(max(fr.values()), abs=0.1)
