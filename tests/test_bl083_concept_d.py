"""BL-083 concept D83: model surgery on the B81 model, pan grillage and joints, 5052 basis, SendCutSend price rule,
flat patterns / DXF, bills, and the stored record."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl083_concept_d as D
from huntkit.gendesign import bl083_parts as DP


def test_5052_basis_and_scs_rule():
    # Yahr shape scaled to the 5052 endurance (117 MPa at 5e8), Goodman on 214 -> about the 6061 value at 1e5
    assert D.sn_5052_smax_r0(1e5) == pytest.approx(191.0, abs=0.3)
    assert D.sn_5052_smax_r0(1e6) < D.sn_5052_smax_r0(1e5)
    # the price rule reproduces the cited examples at the cited size
    assert D.scs_price(33.9, 4, 0) == pytest.approx(19.51, abs=0.01)
    assert D.scs_price(33.9, 4, 1) == pytest.approx(37.49, abs=0.01)
    assert D.scs_price(100.0, 20, 4) > D.scs_price(100.0, 20, 2) > D.scs_price(100.0, 20, 0)
    assert "don't offer bending for 6061" in D.SCS["no_6061_bend"]


def test_model_surgery_and_wiring():
    cfg = D.cfg_d()
    m = D.build(cfg, 19.0)
    groups = {mm["group"] for mm in m["members"]}
    assert not {"lumbar_cross_tube", "lumbar_gusset", "hip_bracket", "hip_ties"} & groups
    assert {"pan_face", "pan_wall", "pan_spine", "pan_strut", "hip_pivot"} <= groups
    links = {ln["id"] for ln in m["links"]}
    assert not any(l.startswith(("lb_", "lc_", "plug_", "tie_")) for l in links)
    for tag in "LR":
        for z in cfg["pan_bolt_z"]:
            assert f"pb_{tag}{z:g}" in links
        assert f"tee_{tag}520" in links
    # Ti mount seat on the face's body side at the BL-055 boss face; pin 21 mm in front
    g = D.geom(cfg)
    assert m["nodes"]["HM"][1] - g["t"] / 2 == pytest.approx(BQ.Y_MOUNT)
    assert m["nodes"]["HP"][1] == pytest.approx(BQ.PIN_Y)
    # every node is used by a member or a link (no singular orphans)
    used = {n for mm in m["members"] for n in mm["nodes"]} | {n for ln in m["links"] for n in ln["nodes"]}
    assert set(m["nodes"]) <= used
    # stay holes: lateral (x) and below the crown-leg travel
    for s in D.stations(cfg):
        if s["group"] == "stay":
            assert m["nodes"][s["node"]][2] <= 160.0
            if "pan bolt" in s["name"]:
                assert s["axis"] == "x"


def test_static_carry_load_path():
    from huntkit.fea.load_standard import ls1_cases
    cfg = D.cfg_d()
    m = D.build(cfg, 19.0)
    case = [c for c in ls1_cases() if c.name == "static_carry"][0]
    r = case.run(m)
    assert all(math.isfinite(mm["sf"]) for mm in r.members)
    lf = r.meta["link_forces"]
    # the hip torque leaves each wall as a fore-aft couple: the z 85 and z 155 bolts push in opposite y
    for tag in "LR":
        assert np.sign(lf[f"pb_{tag}85"][1]) != np.sign(lf[f"pb_{tag}155"][1])
        # couple ~ (V/2) x lever / dz within the stiffness-share band
        V = r.reactions["HP"][2]
        lever = D.geom(cfg)["yline"](120.0) - D.geom(cfg)["pin_y"]
        est = V / 2 * lever / 70.0
        assert 0.4 * est < abs(lf[f"pb_{tag}155"][1]) < 1.6 * est
    # the vertical hip load reaches the stays through the pan (sum of pan-bolt z forces ~ hip V)
    Fz = sum(lf[k][2] for k in lf if k.startswith("pb_"))
    assert abs(Fz) == pytest.approx(r.reactions["HP"][2], rel=0.35)


def test_strut_lifts_buckling():
    from huntkit.fea.load_standard import ls1_envelope
    case = [c for c in ls1_envelope()["crown_bar"] if c.name == "side_hill_torsion"][0]
    with_s = case.run(D.build(D.cfg_d(), 15.0)).buckling_sf
    without = case.run(D.build(D.cfg_d(strut_z=()), 15.0)).buckling_sf
    assert with_s > 1.3 * without
    assert with_s / (1.5 * case.required_sf) >= 1.0


def test_flat_patterns_and_dxf(tmp_path):
    import ezdxf
    cfg = D.cfg_d()
    ft, fs = DP.flat_tray(cfg), DP.flat_spine(cfg)
    # SendCutSend: features >= 1/2 die width (0.472 in die -> 6.0 mm) from each bend centre line
    assert ft["hole_to_bend_min_mm"] >= 6.0 and fs["hole_to_bend_min_mm"] >= 6.0
    assert ft["n_bends"] == 4 and fs["n_bends"] == 2
    # flat area is less than the OML surface (bends deduct) but within 10 %
    d = ft["dims"]
    oml = d["W"] * d["H"] + d["W"] * (d["ft"] + d["fb"]) + 2 * (d["D_full"] * (D.WALL_STAY_TOP - d["wz"][0]) +
                                                              d["D_front"] * (d["H"] - (D.WALL_STAY_TOP - d["wz"][0])))
    assert 0.85 * oml < ft["area_mm2"] < 1.02 * oml
    p = tmp_path / "t.dxf"
    DP.write_dxf(ft, p, "test")
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    assert len([e for e in msp if e.dxf.layer == "BEND"]) == 4
    assert len([e for e in msp if e.dxftype() == "CIRCLE"]) == len(ft["holes"])


def test_bills():
    cfg = D.cfg_d()
    printed = {"foot_cup": {"count": 2, "mass_g_each": 67.1}}
    mass = DP.mass_table(cfg, printed)
    assert mass["body_g"] == pytest.approx(sum(mass["rows"].values()), abs=1.0)
    cost = DP.cost_table(cfg, mass)
    assert cost["per_frame_usd"] == pytest.approx(sum(l["usd"] for l in cost["lines"]), abs=0.05)
    assert not cost["within_cap"]
    # pan order clears the free-shipping threshold
    assert cost["pan_usd"] >= D.SCS["free_ship_usd"]
    bands = DP.mass_table(D.cfg_d(tees="bands"), printed)
    assert bands["body_g"] < mass["body_g"] - 100
    rec = json.loads(BQ.REC_JSON.read_text())
    lev = DP.b81_lever_bill({**BQ.CFG0}, rec["mass"], rec["cost"])
    assert lev["d_mass_g"] < -150
    assert lev["body_g"] == pytest.approx(rec["mass"]["body_g"] + lev["d_mass_g"], abs=0.2)


def test_record_consistent():
    if not D.REC_JSON.exists():
        pytest.skip("run python -m huntkit.gendesign.bl083_report run first")
    rec = json.loads(D.REC_JSON.read_text())
    for name, v in rec["variants"].items():
        ms = [r["margin"] for r in v["rows"] if r.get("margin") is not None and r["kind"] != "info"]
        assert v["min_margin"] == pytest.approx(min(ms), abs=1e-3)
        assert v["strong_pass"] == (min(ms) >= 1.0)
    ranks = rec["ranking"]
    assert [c["rank"] for c in ranks] == list(range(1, len(ranks) + 1))
    # rubric order: no failing option ranks above a passing one
    first_fail = min((c["rank"] for c in ranks if not c["strong_pass"]), default=99)
    assert all(c["rank"] < first_fail for c in ranks if c["strong_pass"])
