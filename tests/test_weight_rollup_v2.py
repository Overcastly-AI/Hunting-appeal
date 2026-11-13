"""BL-013 whole-pack weight roll-up v2: start reconciles to the ledger, scenarios stay separate, every bar traces to
a ticket's code, the clean-ups are resolved against their sources.

    python -m pytest -q tests/test_weight_rollup_v2.py
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "designs" / "pack_5200"
for p in (str(ROOT), str(PACK), str(PACK / "concepts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import weight_rollup_v2 as W  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402


@pytest.mark.parametrize("size", L.SIZES)
def test_start_reconciles_to_the_ledger_at_every_belt_size(size):
    rows = W.b2_rows(size)
    assert W.cfg_total(rows, "meat_trip") == pytest.approx(L.total("corrie_b2_h1", size), abs=0.15)
    # base < as hunted < meat trip, and the holster is the only suspension add-on
    assert W.cfg_total(rows, "base") < W.cfg_total(rows, "as_hunted") < W.cfg_total(rows, "meat_trip")
    sus_addons = [r for r in rows if r["system"] in L.SUSPENSION and r["cfg"] != "base"]
    assert [r["name"][:5] for r in sus_addons] == ["IMP-3"]


def test_scenarios_are_kept_separate():
    for scen in W.SCEN:
        allowed = W.SCEN[: W.SCEN.index(scen) + 1]
        steps = {r["step"] for r in W.scenario_rows(scen)} - {"start"}
        assert steps, scen
        for s in steps:
            assert W.STEP_META[s][0] in allowed, (scen, s)
    p_steps = {r["step"] for r in W.scenario_rows("P")}
    assert not any(W.STEP_META[s][0] == "A" for s in p_steps if s != "start")   # no after-tests saving in proven now
    t = W.scenario_table()
    assert t["B.2"]["base"] > t["P"]["base"] > t["A"]["base"]


def test_waterfall_closes_and_every_bar_is_a_step():
    st = W.step_deltas("M")
    t = W.scenario_table("M")
    run = t["B.2"]["base"]
    for sc in W.SCEN:
        run += sum(st[k]["base"] for k in W.ORDER if W.STEP_META[k][0] == sc)
        assert run == pytest.approx(t[sc]["base"], abs=0.3), sc
    for k, rows in W.steps("M").items():
        assert rows, k
        assert all(r["source"] and r["system"] in L.SYSTEMS and r["cfg"] in W.CFGS for r in rows), k


def test_cleanups_resolved_against_sources():
    led = {r["name"]: r["g"] for r in L.parts("corrie_b2_h1", "M")}
    st = W.step_deltas("M")
    assert st["C1"]["base"] == pytest.approx(-led["attachment: printed fairleads (8)"])
    assert st["C2"]["base"] == pytest.approx(-led["attachment: B-01 swell patches"])
    cw = W.corner_wraps()
    assert 15.0 < cw["wraps_g"] < 20.0                    # the "about 18 g" flag of BL-017
    assert cw["unbooked_g"] == pytest.approx(cw["wraps_g"] + cw["adhesive_g"] - 2.21)
    nb = W.non_body_sources()
    assert nb["short_g"] == pytest.approx(9.1, abs=0.1)   # BL-017's 9.1 g
    assert st["C4"]["base"] == pytest.approx(-8.0)
    assert st["C6"]["base"] == pytest.approx(0.0)         # a move, not a saving
    c6 = W.steps("M")["C6"]
    assert {r["system"] for r in c6} == {"attachment", "harness"}
    assert st["C7"]["as_hunted"] == pytest.approx(0.0) and st["C7"]["base"] > 0
    assert st["C8"]["base"] == pytest.approx(W._HD().closure("M")["delta_g"], abs=0.05)


def test_ticket_steps_match_the_ticket_modules():
    F = W._F()
    st = W.step_deltas("M")
    wings = sum(p.g for p in W.wing_parts())
    # P: CORRIE F, today's fabrics, with the wing parts, the 38 mm IM/US set and the hood + IM2 hooks kept (BL-023);
    # A: BL-003 (a) IM/US, BL-004 REC, wings off and the fabric swaps
    with W.rev():
        wt, wb = F.weight_table("M", "base", "D2", "today"), F.weight_table("M", "base", "D2", "B")
    imus, att = st["A_imus"]["base"], st["A_att"]["base"]
    assert imus == pytest.approx(-116.96, abs=0.05)                            # BL-014 S1 / DECISIONS BL-014 row
    assert att == pytest.approx(-103.0, abs=0.05)                              # attachment_diet.md REC
    patch = L.parts(L.CONFIGS[0], "M")                 # BL-033: C2 took the B.2 swell-patch row; P_F leaves it alone
    patch = next(r["g"] for r in patch if r["name"] == "attachment: B-01 swell patches")
    assert st["P_F"]["base"] == pytest.approx(wt["bag_side_g"] - wt["corrie_b2_bag_side_g"] + patch + wings - imus - att,
                                              abs=0.3)
    assert st["A_wings"]["base"] == pytest.approx(-wings, abs=0.05)
    assert st["A_fab"]["base"] == pytest.approx(wb["bag_side_g"] - wt["bag_side_g"], abs=0.3)
    assert st["A_back"]["base"] == pytest.approx(-44.6, abs=0.1)              # BL-005 record
    assert st["P_pkgC"]["base"] == pytest.approx(L.total("corrie_b2_h1_c", "M") - L.total("corrie_b2_h1", "M"), abs=0.05)
    assert st["P_d2"]["base"] + st["P_kits"]["base"] == pytest.approx(W.crown("(a)+(d2)"), abs=0.05)
    assert st["A_c17"]["base"] < 0
    # 28 mm cheek (BL-021): booked inside the H1B raster, not as its own step; FROZEN is the cross-check only
    assert "P_cheek" not in W.STEP_META
    assert W.cheek_g() == pytest.approx(2 * (9.78 - 6.13104), abs=0.01)         # 28 mm, loadpath_check.FROZEN
    assert W.cheek_g() - W.cheek_g(13.5) == pytest.approx(0.5, abs=0.01)       # DECISIONS BL-021: +0.5 g over 27 mm
    assert st["H1B"]["base"] == pytest.approx(L.h1_body_update()["steps_sum_g"], abs=0.05)
    fx = W.fixed_torso("a")
    assert fx["pack_delta_g"] == pytest.approx(3839.3 - 3927.0, abs=0.15)    # BL-007's own result at 19 in
    # CORRIE F rev 3 (BL-030, the ledger's adopted bag): rev 1's +8.6 g on rev 0 (DECISIONS 2026-11-12, "Rev 1 adds
    # +8.6 g (D2)") + rev 2's B-27 ports in base; the rev 3 lid and crown straps are as hunted, not base
    assert W.CORRIE_F_REV == L.ADOPTED_BAG["revision"] == 3
    with F.revision(0):
        r0 = F.weight_table("M", "base", "D2", "today")["bag_side_g"]
    import strap_tails as ST                       # BL-031 base strap changes ride on rev 3 (strap_tails.bag_rows)
    bl031 = sum(g for s, n, g, c, src in ST.bag_rows() if c == "base")
    assert wt["bag_side_g"] - r0 == pytest.approx(8.6 + F.guy_port()["mass_g"] + bl031, abs=0.1)


def test_six_point_six_pounds_is_not_reached_and_the_gap_is_reported():
    t = W.scenario_table("M")
    for s in W.SCEN:
        assert t[s]["base"] > W.TARGET_G
    fc = W.feature_costs("M")
    assert fc["gap_g"] == pytest.approx(t["A"]["base"] - W.TARGET_G, abs=0.2)
    assert all(not c["frozen"] for c in fc["candidates"] if c["item"] in fc["greedy_take"])


def test_leaders_basis_and_configs():
    lf = {r["leader"]: r for r in W.like_for_like_leaders("M")}
    t = W.scenario_table("M")
    kuiu = lf["KUIU ICON 6 6000 full kit"]
    assert kuiu["A"]["ours_g"] == pytest.approx(t["A"]["base"])
    sg = lf["Stone Glacier Sky 5900 + Krux, M belt"]
    assert sg["A"]["ours_g"] < t["A"]["base"]                                  # hip pocket and sleeve removed
    cf = W.configs("M")
    assert L.total(cf["corrie_f_as_hunted"]) > L.total(cf["corrie_f_base"])
    assert L.total(cf["bl005_back"]) == pytest.approx(t["B.2"]["base"] - 44.6, abs=0.2)
    assert L.total(cf["bl007_c"]) < L.total(cf["bl007_a"])


def test_estimates_cover_every_row():
    e = W.estimates("A", "M")
    assert sum(c["g"] for c in e["classes"].values()) == pytest.approx(e["total_g"], abs=0.5)
    assert 0 < e["rss_g"] < e["worst_g"]


def test_screenshots_are_phone_sized_if_written():
    for n in (1, 2):
        p = W.SCREENS / f"{W.PREFIX}{n}.png"
        if p.exists():
            assert p.stat().st_size <= 1.5 * 1024 * 1024


# =====================================================================================================================
# BL-023: the ledger holds the corrections; re-classification per BL-014
# =====================================================================================================================
@pytest.mark.parametrize("size", L.SIZES)
def test_ledger_and_rollup_agree(size):
    """B.2 start + the roll-up's C1-C8 steps == ledger corrie_b2_h1_v2, to 0.5 g, in total and system by system."""
    st = W.steps(size)
    rows = W.b2_rows(size) + [r for k in W.ORDER if k in L.CORRECTIONS for r in st[k]]
    assert W.cfg_total(rows, "meat_trip") == pytest.approx(L.total("corrie_b2_h1_v2", size), abs=0.5)
    a, b = L.by_system(W.cfg_rows(rows, "meat_trip")), L.by_system("corrie_b2_h1_v2", size)
    for s in L.SYSTEMS:
        assert a[s] == pytest.approx(b[s], abs=0.5), s
    # the roll-up reads its corrections from the ledger, not its own copy
    led = L.corrections("corrie_b2_h1", size)
    for k in L.CORRECTIONS:
        assert sum(r["g"] for r in st[k]) == pytest.approx(sum(r["g"] for r in led[k]), abs=0.01), k


def test_gated_savings_are_not_proven_now():
    """BL-014 S1: changes that pass only after a named test are in A, with the heavier part booked in P."""
    assert W.STEP_META["A_imus"][0] == "A" and W.STEP_META["A_att"][0] == "A"
    p_rows = W.scenario_rows("P")
    assert not any(r["step"] in ("A_imus", "A_att") for r in p_rows)
    t = W.scenario_table("M")
    st = W.step_deltas("M")
    # proven now = BL-013's 3414.4 g + the two gated savings + the 27 mm cheek (+1.46 g), i.e. BL-023's 3635.9 g
    # (BL-014 S1), then 2026-11-12: + H1B body (+42.9 g, h1_buckling.json) - the 27 mm cheek step (6.80 g, now inside
    # the H1B raster) + CORRIE F rev 1 (+8.6 g, BL-022) + rev 3's B-27 ports in base (BL-030; lid and straps as hunted)
    bl023_p = 3414.4 - st["A_imus"]["base"] - st["A_att"]["base"] + 1.46
    assert bl023_p == pytest.approx(3635.9, abs=0.3)                             # weight_rollup_v2.md of BL-023
    import strap_tails as ST                       # + BL-031 (2026-11-12): bag-side base rows + the BL031 correction
    bl031 = sum(g for s, n, g, c, src in ST.bag_rows() if c == "base") + st["BL031"]["base"]
    upd = st["H1B"]["base"] - 2 * (9.53 - 6.13104) + 8.6 + W._F().guy_port()["mass_g"] + bl031
    assert t["P"]["base"] == pytest.approx(bl023_p + upd, abs=0.3)
    assert 3610 < t["P"]["base"] < 3660                                        # BL-031: 3634.8 g (was 3683.4)
    # after tests: BL-023's 3143.5 g + the same update + the retired OD 17 legs taken back out (they were -20.6 g); the
    # A_b step also deletes BL-031's shortened stabilizers (its compensating row)
    assert t["A"]["base"] == pytest.approx(3143.5 + upd - st["A_c17"]["base"] - ST.stabilizer_delta_g("M"), abs=0.3)
    assert st["A_c17"]["base"] == pytest.approx(-20.6, abs=0.1)


def test_retired_items_stay_out():
    """2026-11-12: OD 17 legs and the fixed torso are retired (BL-021 (4)); wings, hood and IM2 hooks are deleted in
    after tests and booked in proven now (named tests with the part as fallback, BL-014 S1); fabric swaps are A."""
    assert W.SCEN == ("P", "A")
    assert W.STEP_META["A_c17"][0] == "R" and W.STEP_META["O_fixed"][0] == "R"
    for scen in W.SCEN:
        assert not {r["step"] for r in W.scenario_rows(scen)} & {"A_c17", "O_fixed"}
    for k in ("A_wings", "A_att", "A_imus", "A_fab"):
        assert W.STEP_META[k][0] == "A", k
    a = W.scenario_rows("A")
    net = lambda rows, needle: sum(r["g"] for r in rows if needle in r["name"])  # noqa: E731
    assert all(abs(net(a, p.id)) < 0.05 for p in W.wing_parts() if p.id.startswith("M-01"))   # wing panels net out
