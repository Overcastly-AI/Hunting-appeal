"""BL-038: the physical test kit generator (designs/pack_5200/physical_test_kit.py), built in memory (writes nothing)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import physical_test_kit as K  # noqa: E402
from huntkit.manufacturing import test_results as TR  # noqa: E402


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def test_register_has_every_gate_the_ticket_names(kit):
    reg = kit["register"]
    for t in ("HS-1", "CS-1", "AB-1", "SL-1", "ST-1", "BU-1", "T9-R3a", "T9-R3b", "T9-R3c", "T9-R3d", "US-BS",
              "PORT-1", "GT-1", "FRAY-1", "MT-1c"):
        assert reg[t]["status"] == "ACTIVE", t
        assert set(reg[t]) == set(K.COLS)
    assert reg["B-28 slip"]["status"] == "COVERED->LL-H"
    assert "B-28" in reg["LL-H"]["gates"]
    assert "28 mm cheek" in reg["IM3-EC"]["specimen"]


def test_ca1_release_level_from_the_adopted_results(kit):
    lv = kit["levels"]
    # BL-039: the cheek at its DIR_SCATTER angle joins the governing flip
    assert lv["flip_gov"] == pytest.approx(max(lv["flip_body"], lv["flip_cheek"], lv["flip_cheek_dir"]))
    assert lv["flip_body"] == pytest.approx(0.30 / lv["fatigue_static"], abs=2e-3)
    assert lv["release"] >= lv["flip_gov"] + 0.02 - 1e-9
    assert lv["release"] < 0.310                        # the BL-023 placeholder is replaced
    assert lv["release_cycled"] >= 0.30 / lv["fatigue_cycled"] + 0.02 - 1e-9
    assert str(lv["release"]) in kit["register"]["CA-1"]["pass_fail"]


def test_ca1_is_rescored_to_bl037(kit):
    rk = {d["test"]: d for d in kit["ranking"]}
    assert rk["CA-1"]["grams"] == pytest.approx(9.9)
    assert rk["CA-1"]["booked"] is False
    assert rk["CA-1"]["rank"] > 10
    s = [d["score"] for d in kit["ranking"]]
    assert s == sorted(s, reverse=True)
    assert float(kit["register"]["CA-1"]["grams_at_stake_g"]) == pytest.approx(9.9)


def test_order_releases_r1_then_bag_then_bl037(kit):
    ow = [o for o in kit["order"] if o["stage"] == "run"]
    first = {}
    for o in ow:
        first.setdefault(o["release"], o["seq"])
    assert first["R1"] < first["BAG-CUT"] < first["BAG-BATCH"] < first["BL037"]
    # inside every session R1 tests come before the bag's and the bag's before BL-037 (G6 follows load_standard 5.3)
    for g in ("G2", "G3", "G4", "G5", "G7"):
        ranks = [K.REL_ORDER[o["release"]] for o in ow if o["group"] == g]
        assert ranks == sorted(ranks), g
    active = {t for t, r in kit["register"].items() if r["status"].startswith(("ACTIVE", "PROPOSED"))}
    assert active <= {o["test"] for o in kit["order"]}
    seq = [o["test"] for o in ow if o["group"] == "G6"]
    assert seq.index("T9") < seq.index("T1") < seq.index("T2") < seq.index("MT-1c") and seq[-1] == "T2u"


def test_shopping_list_is_priced_and_flags_long_lead(kit):
    sh = kit["shopping"]
    for x in sh:
        assert x["total_usd"] == pytest.approx(x["qty"] * x["unit_usd"], abs=0.01)
        assert x["price_source"].startswith(("http", "record", "ASSUMPTION", "test_register", "frame_h1"))
    cam = next(x for x in sh if x["item"].startswith("cam buckle"))
    assert cam["unit_usd"] == pytest.approx(K.rec_price("cam_25mm_al")) and cam["long_lead"]
    assert next(x for x in sh if "#10 coil slider" in x["item"])["long_lead"]
    assert sum(x["total_usd"] for x in sh) > 2000


def test_results_template_reads_back(kit, tmp_path):
    res = kit["results"]
    p = tmp_path / "r.csv"
    K._csv(p, res, TR.COLUMNS)
    rows = TR.load_results(p)
    assert len(rows) == len(res)
    v = TR.verdicts(rows)
    assert all(t.status == "OPEN" for t in v.values())
    a = TR.assumption_status(rows, v)
    for key in ("US-BS", "NO-BIND", "CINCH_STATIC", "PAHT_FAT", "XLPE-SET", "SLIDER-CORD", "MU_WEB_FAB", "ROLL-PATH"):
        assert a[key]["status"] == "OPEN", key
    # fill every US-BS row with a pass: its assumption flips to VERIFIED
    for r in rows:
        if r.test_id == "US-BS":
            r.measured = "Y" if r.check == "yes" else "4"
    assert TR.assumption_status(rows)["US-BS"]["status"] == "VERIFIED"
    lid = next(r for r in rows if r.test_id == "T9-R3d" and r.check == "band")
    lo, hi = (float(x) for x in lid.limit.split(".."))
    assert hi - lo == pytest.approx(10.0) and lo < kit["lid_g"] < hi
