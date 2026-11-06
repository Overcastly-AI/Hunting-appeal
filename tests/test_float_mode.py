"""Float mode (owner 2026-11-06): the hinge swing is replaced by meat on the frame and the bag hung upright behind it on
two B-24 stand-off links at the IM3 eyes, at a 120 / 170 / 220 mm gap. analysis/meat_carry_alternatives.md."""
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "designs" / "pack_5200" / "analysis"


@pytest.fixture(scope="module")
def modes():
    from huntkit.gendesign.meat_haul import analyse
    return analyse(json.loads((ANALYSIS / "cradle_fea.json").read_text()))


def test_three_gaps_kept_and_the_link_reaches_them():
    from huntkit.gendesign import meat_haul as MH
    assert MH.FLOAT_GAPS_MM == (120.0, 170.0, 220.0)            # owner: boned and bone-in meat
    assert MH.FLOAT_VIEW_GAP_MM in MH.FLOAT_GAPS_MM
    L = MH.LINK
    raw = L["hook_fold_mm"] + max(MH.FLOAT_GAPS_MM) + L["tail_mm"] + 3 * L["loop_fold_mm"]
    assert raw <= MH.link_cut_mm() < raw + 5.0
    from huntkit.gendesign.attach_system import link_piece
    p = link_piece()
    assert p.piece_id == "B-24" and p.quantity == 2
    apex = [il for il in p.internal_lines if il.kind == "fold" and "apex" in il.label]
    assert len(apex) == 3
    # finished distance of each apex from the hook bed = the gap (each earlier loop uses loop_fold of webbing)
    for k, (il, gap) in enumerate(zip(apex, MH.FLOAT_GAPS_MM)):
        c = float(np.asarray(il.points)[0][1])
        assert c - L["hook_fold_mm"] - k * L["loop_fold_mm"] == pytest.approx(gap)


def test_link_load_and_im3_eye(modes):
    f = modes["float"]
    lk = f["link"]
    # 12 kg bag on two links at 30 deg, x 3.0 = the 353 N hand-off number
    assert lk["tension_factored_n"] == pytest.approx(353.0, abs=1.0)
    assert lk["tension_envelope_factored_n"] == pytest.approx(941.4, abs=1.0)    # 32 kg misuse envelope
    assert lk["hook_sf_envelope"] >= 1.5
    assert f["im3_eye_n"] == pytest.approx(559.3, abs=1.0)
    rec = json.loads((ANALYSIS / "attach_system_results.json").read_text())
    assert f["im3_eye_envelope_n"] < rec["factored_n"]["im3"]                    # inside the bag-on IM3 envelope
    assert f["nodes_envelope"]["im3"]["sf_fatigue"] >= 1.0
    assert "hinge" not in f["nodes"]                                             # the pins carry nothing in float


def test_meat_path_is_the_bag_off_haul(modes):
    f, o = modes["float"], modes["bag_off"]
    for k in ("us1", "us2", "im1", "im2"):
        assert f["nodes"][k]["n"] == pytest.approx(o["nodes"][k]["n"])
    assert f["viable"] and f["cleat_fatigue"] >= 1.0 and f["cradle_cam_sf"] >= 1.5


def test_lever_inside_rev_c_and_better_than_the_swing(modes):
    f = modes["float"]
    for r in f["lever"]:
        assert r["cg_mm"] <= f["cg_limit_mm"] + 1e-6
    by_gap = {r["gap_mm"]: r for r in f["lever"]}
    assert by_gap[170.0]["cg_mm"] < f["swing_cg_mm"]
    assert by_gap[170.0]["cg_mm"] == pytest.approx(158.0, abs=1.0)


def test_procedure_and_times():
    from huntkit.gendesign.attach_system import PROCEDURES, procedure_times
    assert "between" not in PROCEDURES and "float" in PROCEDURES
    t = procedure_times()
    assert t["float"] == t["bag_off"] + 12 + 24 + 8 + 14 + 18
    text = " ".join(s for s, _ in PROCEDURES["float"]["steps"]).lower()
    assert "b-24" in text and "swing" not in text
    rec = json.loads((ANALYSIS / "attach_system_results.json").read_text())
    assert rec["times_s"] == t
    assert any(p["id"] == "B-24" for p in rec["parts"])
    assert any(t_["id"] == "PT-6" for t_ in rec["proof_tests"])


def test_booked_once_and_drawn():
    import yaml
    from huntkit.gendesign.meat_haul import float_link_parts_g
    geo = yaml.safe_load((ROOT / "designs" / "pack_5200" / "geometry.yaml").read_text())
    assert geo["weight"]["groups_g"]["float-mode stand-off links B-24"] == pytest.approx(sum(float_link_parts_g().values()), abs=0.1)
    dxf = (ROOT / "designs" / "pack_5200" / "cut" / "attachment" / "attachment_parts.dxf").read_text(errors="ignore")
    assert "B-24" in dxf
    assert "meat_bay_L" not in geo["volumes"] and geo["volumes"]["meat_float_L"] > 30.0


def test_no_swing_left_in_the_docs():
    for f in ("designs/pack_5200/analysis/meat_haul_modes.md", "designs/pack_5200/analysis/bag_attachment.md"):
        md = (ROOT / f).read_text()
        assert "Between mode" not in md and "swings open" not in md, f
    j = json.loads((ANALYSIS / "meat_haul_modes.json").read_text())
    assert "between" not in j and "float" in j
