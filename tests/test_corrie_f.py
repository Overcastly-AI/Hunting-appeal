"""BL-011 CORRIE F (merged bag): geometry, ledger booking, door options, sims, access, and the R-28 method fix.

    python -m pytest -q tests/test_corrie_f.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(CONCEPTS / "corrie_f_sim")):
    if p not in sys.path:
        sys.path.insert(0, p)

import corrie_f as F  # noqa: E402


@pytest.fixture(scope="module")
def summ():
    return F.summary("M")


# ------------------------------------------------------------------------------------------- R-28 method fix
def test_r28_design_face_default_is_unchanged_and_own_face_is_used():
    """attach_system.r28_loaded(design_face=...) is additive: SPINE's own face given explicitly reproduces the default,
    and a face set back 40 mm above the crown reads a later (or equal) first contact for the same move."""
    from huntkit.gendesign import attach_system as AS
    bg = AS._bg()
    zz = np.arange(560.0, 1150.0, 25.0)
    move = [(float(z), 70.0) for z in zz]           # a wall bulging 70 mm toward the head fails at 23 in
    spine = [(float(z), float(bg.y_frame(z)[0])) for z in zz]
    a = AS.r28_loaded(23, move, hood=False)
    b = AS.r28_loaded(23, move, hood=False, design_face=spine)
    assert a["worst_contact_deg"] == b["worst_contact_deg"]
    assert a["worst_gap_30_mm"] == pytest.approx(b["worst_gap_30_mm"], abs=0.05)
    back = [(z, y + 40.0) for z, y in spine]
    c = AS.r28_loaded(23, move, hood=False, design_face=back)
    assert c["worst_contact_deg"] > a["worst_contact_deg"]


# ------------------------------------------------------------------------------------------- shell
def test_shell_is_s15_with_a_top_setback():
    g = F.geometry()
    assert g["width_max_mm"] <= 394.0                        # owner freeze 15.5 in
    assert g["width_collar_mm"] == pytest.approx(360.0, abs=0.5)
    assert g["z_c"] == pytest.approx(745.0)
    assert g["depth_collar_mm"] == pytest.approx(195.0 - F.TOP_SETBACK_MM, abs=0.5)
    c0, c = F.make(0.0), F.make()
    zs = np.linspace(40.0, 620.0, 30)                        # below the shoulder crease nothing moves
    assert np.allclose(c.frame_y(zs), c0.frame_y(zs))
    assert np.allclose(c.y_front(np.linspace(40, 745, 40)), c0.y_front(np.linspace(40, 745, 40)))
    assert float(c.frame_y([745.0])[0] - c0.frame_y([745.0])[0]) == pytest.approx(F.TOP_SETBACK_MM)


# ------------------------------------------------------------------------------------------- ledger booking
def test_corrie_b2_rows_reconcile_to_the_ledger():
    from huntkit.mass import ledger as L
    rows = F.corrie_b2_rows("M")
    tot = sum(r["g"] for r in rows if r["system"] in F.BAG_SIDE)
    assert tot == pytest.approx(L.like_for_like("corrie_b2_h1", "M")["bag_side"], abs=0.2)
    # BL-008 configs of CORRIE B.2: as hunted moves pouch + its straps + the fly (not F-02); meat trip = B-24
    mt = sum(r["g"] for r in rows if r["cfg"] == "meat_trip")
    assert mt == pytest.approx(24.4 + 28.0 + 2.0, abs=0.1)


def test_corrie_f_rows_are_booked_once_on_ledger_systems():
    rows = F.parts("M", "D2")
    assert {r["system"] for r in rows} <= set(F.BAG_SIDE)
    assert {r["cfg"] for r in rows} <= set(F.CFGS)
    # the crown hood family leaves completely (ledger rows + the BL-004 removal net to zero)
    hood = sum(r["g"] for r in rows if any(k in r["name"] for k in ("crown hood B-19", "lip stiffener B-19s", "hood lining",
                                                                       "hood ladder strips", "hood tongues", "hood grab tab",
                                                                       "BL-004 REC: hood B-19")))
    assert hood == pytest.approx(0.0, abs=0.05)
    # IM2 bag hooks: 2 of the 4 rated hooks removed, IM3 pair upgraded to carabiners (+8 g each)
    assert any("IM3 bag hooks -> wiregate" in r["name"] and r["g"] == pytest.approx(16.0) for r in rows)
    # no wings, no wing straps, no tripod straps (W1-W3 are the only external set)
    assert not any(k in r["name"] for r in rows for k in ("M-01", "SH-06", "wing strap", "tripod_straps"))
    # the shell is CORRIE F's own build, not CORRIE B.2's door / U-surround
    assert not any(r["name"].startswith(("horseshoe door zip", "B-02u U-surround")) for r in rows)


def test_strap_rows_are_bl003_rec_plus_bl010_fixes():
    import strap_arch as SA
    rec = sum(p.g for p in SA.architectures()["rec"] if p.id != "pouch-straps")
    rows = F.strap_rows()
    fixes = sum(g for s, n, g, c, src in rows if n.startswith("BL-010"))
    assert fixes == pytest.approx(14.0 + 21.0 + 16.0, abs=0.01)        # loadpath_verification S2 + S9 + S12
    assert sum(g for s, n, g, c, src in rows) == pytest.approx(rec + fixes, abs=0.05)


def test_goal_is_reported_honestly(summ):
    for d in F.DOORS:
        g = summ["doors"][d]["goal"]
        assert g["met"] == (g["saving_g"] >= 350.0)
        mt = summ["doors"][d]["configs"]["meat_trip"]
        assert g["corrie_b2_g"] == mt["corrie_b2_bag_side_g"]
        # every configuration is lighter than CORRIE B.2 on the same rule
        for cfg in F.CFGS:
            assert summ["doors"][d]["configs"][cfg]["delta_g"] < 0
    # D2 is the lighter door; B fabrics save against today's fabrics
    assert summ["doors"]["D2"]["goal"]["saving_g"] > summ["doors"]["D1"]["goal"]["saving_g"]
    for d in F.DOORS:
        assert summ["doors"][d]["configs"]["base"]["bag_side_g"] < summ["doors"][d]["today_fabrics"]["base"]["bag_side_g"]


def test_weight_configs_nest(summ):
    for d in F.DOORS:
        c = summ["doors"][d]["configs"]
        assert c["base"]["bag_side_g"] < c["as_hunted"]["bag_side_g"] < c["meat_trip"]["bag_side_g"]
        assert c["base"]["by_system"]["pouch"] == 0.0           # the top pouch is an add-on


# ------------------------------------------------------------------------------------------- doors and build
def test_both_doors_complete_and_wider_than_corrie(summ):
    b2 = summ["corrie_b2_metrics"]["clear_width_mm"]
    for d in F.DOORS:
        m = summ["doors"][d]["metrics"]
        assert m["curved_seams"] <= 1                           # ticket: zero or one curved seam
        assert m["door_zip_mm"] > 1000
        for k in ("IM1", "IM2", "IM3"):
            assert m["clear_width_mm"][k] > b2[k] + 35
    assert all(v == pytest.approx(376.0, abs=1) for v in summ["doors"]["D1"]["metrics"]["clear_width_mm"].values())
    assert min(summ["doors"]["D2"]["metrics"]["clear_width_mm"].values()) >= 294.0   # team A's narrowest door width


# ------------------------------------------------------------------------------------------- sims (stored rows)
def _rows():
    """Current-rev rows; a stalled coarse case is replaced by its 8 mm-rounding retry (F_PR{t}_sm8, BL-022)."""
    import copy
    import corrie_f_sim as S
    st = S.load_results()["rows"]
    out = {}
    for t in S.TORSOS:
        r = copy.deepcopy(st.get(f"F_PR{t}"))
        alt = st.get(f"F_PR{t}_sm8")
        if r and alt:
            for cn, c in alt["cases"].items():
                if cn in r["cases"] and not r["cases"][cn]["converged"] and c["converged"]:
                    r["cases"][cn] = c
        out[t] = r
    return out


def test_sims_converged_in_band_and_under_rev_c():
    rows = _rows()
    if any(r is None for r in rows.values()):
        pytest.skip("CORRIE F sims not run in this checkout (outputs/ is untracked; corrie_f_sim.py run F --torso N)")
    for t, r in rows.items():
        for cn, lim in (("fill", 205.0), ("meat", 190.0)):
            c = r["cases"][cn]
            assert c["converged"]
            assert c["cg_y_biased"] <= lim
        assert 82.0 <= r["cases"]["fill"]["closed_L"] <= 88.0          # 85 L +/- 3
    assert rows[15]["cases"]["meat"]["cg_y"] <= 180.0                    # ticket acceptance: 15 in meat <= 180 simulated


def test_r28_passes_at_15_19_23_with_the_setback():
    rows = _rows()
    if any(r is None for r in rows.values()):
        pytest.skip("CORRIE F sims not run")
    for t, r in rows.items():
        for cn in ("fill", "meat"):
            assert r["r28"][cn]["pass"], (t, cn, r["r28"][cn]["worst_contact_deg"])


# ------------------------------------------------------------------------------------------- access
def test_access_hourly_items_on_every_belt():
    import corrie_f_loadout as CFL
    for door in F.DOORS:
        res = CFL.run(door, sizes=("S", "M", "XXL"))
        for sz, m in res["misses"].items():
            assert m["day"]["hourly"] == [] and m["elk6"]["hourly"] == []
            assert len(m["sheep8"]["hourly"]) <= 1
            assert "bottle_1L#2" not in m["sheep8"]["all"]               # the 2nd bottle is reachable (FP-R)


# ------------------------------------------------------------------------------------------- BL-022 (rev 1)
def test_rev0_is_reproducible_and_rev1_adds_only_its_parts():
    with F.revision(0):
        assert F.TOP_SETBACK_MM == 30.0 and F.GUY_X == 100.0
        r0 = F.parts("M", "D2")
        assert not any(r["name"].startswith("BL-022") for r in r0)
    r1 = F.parts("M", "D2")
    assert F.REVISION == 1 and F.GUY_X == F.REVS[1]["guy_x"]
    new = [r for r in r1 if r["name"].startswith("BL-022")]
    assert {r["system"] for r in new} == {"attachment", "straps_compression"}
    added = sum(r["g"] for r in r1) - sum(r["g"] for r in r0)
    if F.REVS[1]["setback"] == F.REVS[0]["setback"]:          # same shell: the difference is the two new parts only
        assert added == pytest.approx(F.guy_bridle()["mass_g"] + F.tripod_keeper(door="D2")["mass_g"], abs=0.05)
    assert added < 15.0                                          # far lighter than team B's tripod straps (32.2 g)


def test_guys_clash_with_lifters_at_rev0_and_clear_at_rev1_on_every_crown_kit():
    g = F.guy_lifter_check()
    # all three BL-017 kits share H1's bar: legs at x +/-115, straight bar, at both ends of every kit's range
    assert set(g["kits"]) == {"S", "M", "L"}
    assert all(r["leg_x"] == pytest.approx(115.0) and r["bar_straight"] for rr in g["kits"].values() for r in rr)
    assert g["rev0_clash"]                                       # x +/-(92-100) loops overlap the lifter webbing band
    assert all(v["overlap_lifter_mm"] > 10 for v in g["rev0"].values())
    r1 = g["rev1"]
    assert g["rev1_ok"] and r1["overlap_lifter_mm"] == 0
    assert r1["clear_to_lifter_mm"] >= F.MIN_CLEAR_MM
    assert r1["clear_to_wrap_mm"] >= 0 and r1["clear_to_clamp_mm"] >= 0   # on bare bar, clear of the spine clamp
    assert F.LIFTER_X == 105.0                                   # the lifters did not move (patent guardrail)


def test_inboard_guys_need_the_bridle():
    geo = F.guy_geometry()
    for t, r in geo.items():
        assert not r["rev0"]["slides_without_bridle"]           # at the bar end the leg stops it anyway
        assert r["rev1"]["slides_without_bridle"]               # inboard: outboard pull > friction -> bridle B-25
        assert r["rev1"]["dist_to_lifter_mm"] > r["rev0"]["dist_to_lifter_mm"]
    b = F.guy_bridle()
    assert 4.0 < b["mass_g"] < 10.0


def test_tripod_keeper_is_light_and_needs_no_handling_at_the_door():
    k2, k1 = F.tripod_keeper(door="D2"), F.tripod_keeper(door="D1")
    assert k2["mass_g"] == pytest.approx(k2["cut_mm"] * F.SHOCK_GM / 1000.0, abs=0.01)
    assert k2["mass_g"] < 3.0 and k1["mass_g"] > k2["mass_g"]  # D1 needs a tab (zip in the corner seam)
    assert k2["glove_s_per_door_cycle"] == 0.0
    assert 0.2 < k2["strain_with_tripod"] < 1.0                  # snug when empty, inside shock-cord stretch with a tripod


def test_bl022_sims_fine_r28_and_guys_off():
    t = F.bl022_table()
    if t["guys_off"] is None or any(t["r28"][x]["worst"]["rev1_fine"] is None for x in (15, 19, 23)):
        pytest.skip("BL-022 sims not run in this checkout (corrie_f_sim.py finerun F --torso N; run F --torso 15 "
                    "--cases meat --guys off --tag _goff)")
    acc = t["acceptance"]
    assert acc["met"] == all(v >= 31.0 for v in acc["rev1_fine_deg"])
    assert acc["met"] or acc["shortfall_deg"]                    # either met or the shortfall is stated
    for tor in (15, 19, 23):
        for cn in ("fill", "meat"):
            c = t["fine"][f"F_{tor}"][cn]
            assert c["converged"] and c["mesh_h"] == 25.0
    go = t["guys_off"]
    assert go["guys_off"]["converged"]
    assert go["guys_off"]["guy_1g_n"] == 0.0                     # no guys in the misuse case
    assert go["exceeds_rev_c"] == (go["guys_off"]["cg_y_biased"] > 190.0)
    assert go["guys_off"]["cg_y"] > go["guys_on"]["cg_y"]        # the guys pull the CG in


def test_bl022_r28_fine_mesh_margin_against_wall_allowance():
    t = F.bl022_table()
    sw = t["r28_allow_sweep"]
    if sw is None:
        pytest.skip("corrie_f_sim.py r28sweep not run in this checkout")
    worst = {k: {a: min(v["fill"]["deg"], v["meat"]["deg"]) for a, v in row.items()} for k, row in sw["rows"].items()}
    for tor in (15, 19, 23):                                     # rev 1 fine: >= 31 deg even at 4x the coded allowance
        assert all(worst[f"F_PR{tor}_fineFM"][a] >= 31.0 for a in ("3", "6", "9", "12"))
    assert worst["Fr0_PR23"]["9"] <= 30.0                        # the coarse rev 0 margin the review flagged was real
    assert worst["F_PR23_fineFM"]["3"] == 34.0                   # = the frame-only ceiling (bag wall not in contact)


def test_r28_frame_only_ceiling_is_34_deg():
    from huntkit.gendesign.attach_system import r28_loaded
    zs = list(range(300, 1200, 50))
    for tor in (15, 19, 23):                                     # bag wall placed far aft: bar + back pad only
        r = r28_loaded(tor, [(z, 0.0) for z in zs], hood=False, design_face=[(z, 3000.0) for z in zs])
        assert r["worst_contact_deg"] == 34.0


def test_bl022_guys_off_misuse_exceeds_rev_c_and_is_a_carry_rule():
    t = F.bl022_table()
    go = t["guys_off"]
    if go is None or go["runs"]["fine_sm8"] is None:
        pytest.skip("guys-off fine run not in this checkout (finerun F --torso 15 --cases meat --guys off --smooth 8 --tag _goff_sm8)")
    assert go["guys_off"] is go["runs"]["fine_sm8"] or go["guys_off"] == go["runs"]["fine_sm8"]
    assert go["exceeds_rev_c"] and go["over_limit_mm"] > 0       # misuse: over the 190 mm meat limit
    assert go["im3_worst_factored_n"] >= go["guys_off"]["im3_factored_n"]
    doc = (F.ROOT / "designs" / "pack_5200" / "analysis" / "corrie_f_body.md").read_text()
    assert "GUYS ON" in doc                                      # hang-tag wording is in the doc
