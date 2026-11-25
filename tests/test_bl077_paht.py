"""BL-077: PAHT-CF H1 under the cost cap (huntkit/gendesign/bl077_paht.py).

Checks results, not only that the code runs: the hot/wet B-basis numbers against hand calculations from the cited
data, the record fix, the routing of the bl070 machinery onto PAHT (reproduces the H1 record rows on the record
basis), the hip options, the cost cap and, when the generated record is present, every row of the adopted design."""
from __future__ import annotations

import json
import math

import pytest

from huntkit.gendesign import bl077_paht as X


def test_b_basis_k_and_allowables_match_hand_calcs():
    b = X.basis()
    assert b["k"] == pytest.approx(3.4066, abs=1e-3)                 # one-sided 90/95, n 5 (CMH-17 table)
    assert b["xy_b"] == pytest.approx(88.0 - 3.4066 * 7.0, abs=0.02)   # lower published XY mean (TDS V2.0)
    assert b["z_b"] == pytest.approx(47.0 - 3.4066 * 5.0, abs=0.02)    # lower published Z mean (TDS V3.0)
    assert b["wet"]["xy"] == 0.82 and b["wet"]["z"] == 0.80
    assert b["hot"]["direct_40_23_dry"] == pytest.approx(40.31 / 49.07, abs=1e-4)   # Ciganas 2026 Table 3
    assert b["hot"]["chosen"] == 0.82
    assert b["hw"]["xy"] == pytest.approx(64.15 * 0.82 * 0.82, abs=0.05)
    assert b["hw"]["z"] == pytest.approx(29.97 * 0.80 * 0.82, abs=0.05)
    assert b["hw"]["tau"] == pytest.approx(b["hw"]["z"] / math.sqrt(3.0), abs=0.02)
    # the honest basis is harsher than the record on every allowable
    assert all(v < 0.62 for v in b["scale"].values())


def test_hot_ratio_tg_shift_readings_bracket_the_direct_one():
    h = X.hot_ratio()
    reads = [v["ratio"] for v in h.values() if isinstance(v, dict)]
    assert len(reads) == 2
    assert min(reads + [h["direct_40_23_dry"]]) >= h["chosen"]
    for v in h.values():
        if isinstance(v, dict):
            assert 40.0 < v["tg_wet_c"] < 70.0                     # wet Tg below the dry DSC 70 C


def test_record_tg_fixed_and_hot_wet_fields_present():
    from huntkit.materials import load
    r = load("pa12_cf_fdm_paht")
    assert float(r.require("glass_transition_c")) == 70.0           # TDS V3.0 DSC (was 45, ASSUMPTION)
    b = X.basis()
    assert float(r.require("tensile_strength_z_hw_mpa")) == pytest.approx(b["hw"]["z"], abs=0.01)
    assert float(r.require("tensile_strength_xy_hw_mpa")) == pytest.approx(b["hw"]["xy"], abs=0.01)
    assert float(r.require("interlayer_shear_hw_mpa")) == pytest.approx(b["hw"]["tau"], abs=0.01)


def test_paht_routing_reproduces_the_record_rows_on_the_record_basis():
    """With the record basis the routed machinery must give the H1 record's clevis and hip-insert rows (bl070
    PAHT_H1), so the hot/wet rows differ only by the allowables."""
    c = X.clevis_rows("paht_rec")
    assert c["clevis_strength"] == pytest.approx(X.BEFORE["clevis_strength"], abs=0.01)
    assert c["clevis_fatigue"] == pytest.approx(X.BEFORE["clevis_fatigue"], abs=0.01)
    from huntkit.gendesign import bl070_h1p as P
    with X.paht("paht_rec"):
        h = P.hip_inserts("paht_rec")
    assert h["abs_z"]["min_sf"]["fatigue"] == pytest.approx(X.BEFORE["hip_fatigue"], abs=0.005)
    # the patch is undone on exit
    assert "paht_hw" not in P.materials()


def test_hot_wet_clevis_and_inserts_scale_with_the_allowables():
    b = X.basis()
    c = X.clevis_rows("paht_hw")
    # the clevis rows mix in-plane and interlayer terms: their scale lies between the tau and the XY scales
    sc = c["clevis_fatigue"] / X.BEFORE["clevis_fatigue"]
    assert min(b["scale"].values()) - 0.02 <= sc <= max(b["scale"].values()) + 0.02
    hip = X.hip_options()
    assert hip["inserts"]["min_sf"]["fatigue"] < 1.15                 # the H1 inserts fail on the honest basis
    assert not hip["plates_window"]["window"]                       # plates alone: no torque window on PAHT
    sl = hip["sleeves"]
    assert sl["pass_rows"] and sl["min_sf"]["fatigue"] >= 1.15 and sl["min_sf"]["creep"] >= 1.5
    assert sl["sleeve_yield_sf"] > 1.0
    assert sl["web_between_holes_mm"] == pytest.approx(9.19 - 6.5, abs=0.02)


def test_cost_table_hand_check():
    cost = X.cost_table(1038.0, 1300.0, 200.0)
    fil = X.filament(1038.0)
    # BUILD_H1 section 3: halves 494.6 + 543.4 g + BL-053 supports 49.0 + 55.3 g (high bound 1235 g)
    assert fil["filament_g"] == pytest.approx(494.6 + 543.4 + 49.0 + 55.3 + 31.4 * 1.08 + 4.5, abs=0.2)
    assert X.filament(1038.0, high=True)["filament_g"] == pytest.approx(1235.0 + 31.4 * 1.08 + 4.5, abs=0.2)
    assert fil["usd"] == pytest.approx(fil["filament_g"] * 0.08, abs=0.01)
    h1 = cost["H1"]
    assert h1["hardware_usd"] == pytest.approx(16 * 2.5 + 8 * 0.08 + 8 * 0.10 + 4 * 0.05 + 8 * 0.19, abs=0.01)
    assert cost["first_frame"]["spools_1kg"] == math.ceil((X.filament(1300.0)["filament_g"] + 200.0) / 1000.0)
    assert all(t[1] <= X.CAP_TOOL_USD for t in X.TOOLS_NEW)


def test_tornado_moves_only_the_rows_it_names():
    M = {k: 1.2 for k, _n, _g in X.ROWS}
    tor = X.tornado(M, 0.5)
    fat = tor[0]["rows"]
    assert fat["R1"] == pytest.approx(1.0, abs=1e-3) and fat["strength"] == 1.2
    tau = tor[1]["rows"]
    f = 0.5 / X.TAU_RATIO
    assert tau["R1"] == pytest.approx(1.2 / (0.5 / f + 0.5), abs=1e-3) and tau["lug_fatigue"] == 1.2


@pytest.fixture(scope="module")
def rec():
    if not X.REC_JSON.exists():
        pytest.skip("bl077.json not generated")
    return json.loads(X.REC_JSON.read_text())


def test_record_body_rows_pass_and_every_shortfall_is_listed(rec):
    rows = {r["key"]: r for r in rec["rows"]}
    for k in ("strength", "static_fatigue", "R1", "creep", "joint_strength", "buckling", "buckling_record",
              "hip_strength", "hip_fatigue", "hip_creep", "lash", "lug_strength"):
        assert rows[k]["pass_after"], k
    assert rows["R1"]["after"] >= 1.0
    # the honest basis really did break the H1 of record
    assert rows["R1"]["h1_hw"] < 0.6 and rows["strength"]["h1_hw"] < 1.0
    # every row still below goal is either gated by a named test or listed with its closing options
    open_names = {o["row"] for o in rec["open_rows"]}
    for r in rec["rows"]:
        if not r["pass_after"]:
            assert r.get("gated_by") or r["name"] in open_names, r["name"]
    for o in rec["open_rows"]:
        assert o["options"]


def test_record_states_the_cap_plainly(rec):
    c = rec["cost"]
    f = rec["final"]
    halves = rec["mass"][f]["h1_lower_flat"] + rec["mass"][f]["h1_upper_flat"]
    # the cap leaves less filament than the design that closes R1 needs, and the record says it is over the cap
    assert c["cap_body_halves_max_g"] < halves
    assert not c[c["cheapest"]]["within_cap"] and c[c["cheapest"]]["per_frame_usd"] > 150.0
    assert c["H1c_a2"]["per_frame_usd"] < c["H1c_ti"]["per_frame_usd"]
    # the re-tune step that would fit the cap does not reach R1 1.0
    fits = [s for s, v in rec["steps"].items() if v["body_g"] - 2 * 15.7 <= c["cap_body_halves_max_g"] + 1e-6]
    assert all(rec["steps"][s]["R1"] < 1.0 for s in fits)
    assert rec["coupon_cost"]["usd"] <= 150.0
    assert "does NOT close within the USD 150 cap" in X.REC_MD.read_text()


def test_record_stls_are_the_checked_export(rec):
    import hashlib
    d = X.REPO / rec["stl_dir"]
    for name, h in rec["stl_md5"].items():
        assert hashlib.md5((d / name).read_bytes()).hexdigest() == h
    import trimesh
    m = trimesh.load(d / "h1_assembled.stl", force="mesh")
    assert m.is_watertight
    assert m.volume * X.RHO == pytest.approx(rec["mass"][rec["final"]]["body"], abs=0.2)
