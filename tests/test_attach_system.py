"""Bag-to-frame attachment system (attachment phase 2026-11-05): the recorded numbers and their guardrails."""
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "designs" / "pack_5200" / "analysis" / "attach_system_results.json"


@pytest.fixture(scope="module")
def res():
    return json.loads(REC.read_text())


def test_chosen_top_anchor_meets_180_at_19_and_23_and_is_best_at_15(res):
    from huntkit.gendesign.attach_system import TARGET_CG
    S = res["sims"]
    assert res["chosen"] == "hood+guys"
    for t in (19, 23):
        assert S[f"PR{t}"]["fill"]["cg_y"] <= TARGET_CG
        assert S[f"PR{t}"]["meat"]["cg_y"] <= TARGET_CG
    # 15 in: the documented gap (no frame above z 601); still better than the no-anchor bag and the hood alone
    assert S["PR15"]["fill"]["cg_y"] < S["P15"]["fill"]["cg_y"] - 5.0
    assert S["PR15"]["fill"]["cg_y"] < S["baseline"]["fill"]["cg_y"] - 25.0
    assert S["PR15"]["fill"]["cg_y"] <= 195.0          # inside the 205 mm C1 envelope of the frame re-check
    # the hood alone beats the two-point crown tie at 19 in, and the guys are what reach 180
    assert S["P19"]["fill"]["cg_y"] < S["A"]["fill"]["cg_y"]
    assert S["PR19"]["fill"]["cg_y"] < S["P19"]["fill"]["cg_y"]


def test_relieved_hood_clears_the_corner_wraps_and_keeps_the_accepted_cg(res):
    """2026-11-06: lip, stiffener and lining on bare OD 18 bar only; the owner-accepted CG (189 / 177 / 168 mm at
    15 / 19 / 23 in, fill) holds within the +/-5 mm fill scatter; R-28 still passes."""
    from huntkit.gendesign.attach_system import HOOD, WRAP, drawing_pieces, wrap_clearance
    wc = wrap_clearance()
    assert wc["pass"]
    assert wc["lip_edge_worst_x_mm"] <= WRAP["x_start"] - 2.0          # hood floated to one leg
    assert wc["crown_over_wrap_clear_mm"] >= 2.0
    assert res["wrap_clearance"] == pytest.approx(wc)
    b19 = next(p for p in drawing_pieces() if p.piece_id == "B-19")
    o = np.asarray(b19.outline)
    top = o[o[:, 1] > o[:, 1].max() - 1.0]                              # the hem edge exists only over the lip width
    assert top[:, 0].min() >= HOOD["width"] / 2 - HOOD["lip_half"] - 1e-6
    assert top[:, 0].max() <= HOOD["width"] / 2 + HOOD["lip_half"] + 1e-6
    for p in drawing_pieces():
        if p.piece_id in ("B-19s", "B-19L"):
            assert np.ptp(np.asarray(p.outline)[:, 0]) <= 2 * HOOD["lip_half"]
    S = res["sims"]
    for t, accepted in ((15, 189.0), (19, 177.0), (23, 168.0)):
        assert abs(S[f"PR{t}"]["fill"]["cg_y"] - accepted) <= 5.0
        for case in ("fill", "meat"):
            assert S[f"PR{t}"][case]["r28"]["pass"]


def test_head_clearance_passes_with_the_simulated_wall_and_the_hood(res):
    for k, v in res["sims"].items():
        if v["family"] in ("hood+guys", "hood"):
            for case in ("fill", "meat"):
                assert v[case]["r28"]["pass"], (k, case)
                assert v[case]["r28"]["worst_contact_deg"] > 30.0
    ref = res["r28_reference"]
    assert ref["published"]["19"]["worst_contact_deg"] == pytest.approx(34.0)     # DESIGN 4.7 reproduced
    assert ref["with_hood"]["19"]["pass"]


def test_im3_hook_fix_covers_c5_with_margin(res):
    F = res["factored_n"]
    # the hook is designed for the hood-off case (T0 472 N at 1 g x 3.0)
    t0 = res["sims"]["T0"]["meat"]["im3_max_n"]
    assert F["im3"] >= 3.0 * t0 - 1.0
    assert res["hook_rated_n"] / F["im3"] >= 1.5
    pt1 = res["proof_tests"][0]
    assert pt1["id"] == "PT-1"
    assert pt1["load_n"] >= 1.5 * F["im3"] - 10.0
    assert 1500.0 / F["im3"] < 1.1                     # the old assumed hook really was short


def test_every_sewn_part_clears_the_qualification_margin(res):
    ids = {p["id"] for p in res["parts"]}
    assert {"HE", "B-18", "T2", "B-23", "T3", "B-17", "B-19", "HT", "B-20", "TG", "B-22"} <= ids
    for p in res["parts"]:
        assert p["sf"] >= 1.5, p["id"]
        assert p["thread"].startswith("bonded_nylon_tex")
        assert p["spi"] in (7, 8)
        assert p["proof_n"] == pytest.approx(1.5 * p["load_n"], abs=10.0)


def test_procedures_keep_the_120_s_bag_off(res):
    t = res["times_s"]
    assert t["bag_off"] <= 120
    assert t["bag_on"] <= 120
    from huntkit.gendesign.attach_system import procedure_times
    assert procedure_times() == t
    from huntkit.gendesign.meat_haul import DETACH_S
    assert DETACH_S == t["bag_off"]


def test_patent_guardrails(res):
    from huntkit.gendesign.attach_system import PATENTS, RUNS
    names = " ".join(p[0] for p in PATENTS)
    for pat in ("12,495,885", "10,952,523", "8,381,956"):
        assert pat in names
    # lifters are never the chosen anchor (US 10,952,523)
    assert res["chosen"] != "lifter"
    # no bag tie or pocket anchored between the spreader and the z 330 cross member (US 8,381,956): every top anchor of
    # the chosen runs sits at the crown, above the spreader top (z 430)
    import yaml
    from huntkit.clothsim.pack import load_scenario
    for k, (scen, torso, fam, _) in RUNS.items():
        if fam != res["chosen"]:
            continue
        sc = load_scenario(ROOT / "huntkit" / "clothsim" / "scenarios" / f"{scen}.yaml")
        assert sc["attachments"]["pocket"]["bar_z"] > 430.0
        for t in sc["attachments"]["ties"]["list"]:
            assert t["anchor"][2] > 430.0


def test_mass_delta_and_budget(res):
    m = res["mass"]
    assert 60.0 < m["delta_g"] < 160.0
    assert abs(sum(m["parts_g"].values()) - m["delta_g"]) < 0.5
    assert res["pack_after_g"] == pytest.approx(res["pack_before_g"] + m["delta_g"], abs=0.2)
    import yaml
    geo = yaml.safe_load((ROOT / "designs" / "pack_5200" / "geometry.yaml").read_text())
    assert geo["weight"]["groups_g"]["bag-to-frame attachment system"] == pytest.approx(m["delta_g"], abs=0.5)
    # Later owner changes booked after this record was written (docs/DECISIONS.md):
    later_g = {"2026-11-06 orange flag sleeve F-03 removed": -6.5,
               "2026-11-06 float mode: B-24 stand-off links (own weight group)": 54.4,
               "2026-11-06 float mode: IM1 meat strap cut +17 mm (220 mm float gap)": 0.5,
               "2026-11-09 materials records corrected (Robic 125 g/m2, ULTRA 200X, UltraGrid, shock cord)": 28.1}
    assert geo["weight"]["groups_g"]["float-mode stand-off links B-24"] == pytest.approx(54.4, abs=0.2)
    assert geo["weight"]["total_g"] == pytest.approx(res["pack_after_g"] + sum(later_g.values()), abs=1.0)


def test_drawings_and_screens_exist(res):
    for k in ("pdf", "dxf"):
        assert (ROOT / res["drawings"][k]).exists()
    dxf = (ROOT / res["drawings"]["dxf"]).read_text(errors="ignore")
    for pid in ("B-19", "B-20", "B-22", "B-23"):
        assert pid in dxf
    assert len(res["screens"]) >= 4
    for s in res["screens"]:
        p = ROOT / s
        assert p.exists() and p.stat().st_size <= 1.5e6


def test_attachment_doc_is_the_system_and_keeps_the_fairlead_record():
    md = (ROOT / "designs" / "pack_5200" / "analysis" / "bag_attachment.md").read_text()
    assert md.startswith("# Bag-to-frame attachment system")
    assert "## 2. Top anchor" in md and "crown hood" in md
    assert "## Frame side: branch fairleads" in md
    assert "notched 30 mm in height" in md


def test_pocket_model_slides_in_z_and_holds_aft():
    """The crown-hood legs: an aft move stretches them 1:1, a z slide of 10 mm only by ~d^2 / (2 reach)."""
    from huntkit.clothsim.pack import PackModel, load_scenario
    pm = PackModel(load_scenario(ROOT / "huntkit" / "clothsim" / "scenarios" / "pack5200_v31_att_P19.yaml"), verbose=False)
    assert pm.pocket_legs
    cb = pm.cables[pm.pocket_legs[0]]
    j = int(cb.nodes[0])
    x = pm.mesh.X0.copy()
    L0 = cb.length(x)
    x[j, 1] += 5.0
    aft = cb.length(x) - L0
    x = pm.mesh.X0.copy()
    x[j, 2] += 10.0
    slide = cb.length(x) - L0
    assert aft == pytest.approx(5.0, abs=0.05)
    assert slide < 0.05
    k_eff = cb.EA / cb.L0
    assert k_eff == pytest.approx(cb.EA / cb.L0)
    assert np.isfinite(k_eff) and k_eff > 1000.0
