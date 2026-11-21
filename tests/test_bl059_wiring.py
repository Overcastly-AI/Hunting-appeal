"""BL-059: bl058.json wired into BUILD_H1 / the frame README, the test kit and register, print/README.md and the bag
release frame-kit line. Every check reads the number from bl058.json / the ledger / the records, never a typed value."""
import csv
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1_build as B  # noqa: E402
import physical_test_kit as K  # noqa: E402

AN = ROOT / "designs" / "pack_5200" / "analysis"
B58 = json.loads((AN / "bl058.json").read_text())
CO = json.loads((AN / "h1_closeout.json").read_text())
REG = ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv"
MFG = ROOT / "outputs/release/pack5200_corrie_f_rev3/manufacturing"
FRAME = ROOT / "designs/pack_5200/print/frame_h1"
STALE = ("R-clip", "699 N")


@pytest.fixture(scope="module")
def pk():
    return B.package()


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def sec(md, n):
    return md.split(f"## {n}.")[1].split("\n## ")[0]


# ------------------------------------------------------------------ hip screws, key, holes, guide
def test_hip_screws_key_and_holes_from_bl058(pk):
    md = pk["build_md"]
    spec = re.sub(r"\s*\(\d+\)$", "", B58["kit"]["hip_screw"]["spec"])
    assert spec.endswith("M5 x 12 DIN 7984")
    row = [ln for ln in md.splitlines() if ln.startswith("| **HW-HIP-SCR**")][0]
    assert spec in row and B58["kit"]["hip_screw"]["key"] in row
    s12 = sec(md, 12)
    assert f"**{spec}**" in s12 and "M5 x 14 DIN" not in s12 and "4 mm key" not in s12
    assert B58["hip_screws"]["key"]["tool"].split(";")[0] in s12
    hole = B58["hip_mount"]["hole_d_mm"]
    assert f"8 holes of {hole:.1f} mm" in s12 and f"8 x D{hole:.1f} holes" in md
    tools = md.split("### Tools")[1].split("## 2.")[0]
    assert "3 and 4 mm" not in tools and "3 mm hex screwdriver" in tools


def test_insert_guide_procedure_and_checks(pk):
    s12 = sec(pk["build_md"], 12)
    g = B58["kit"]["hip_guide"]
    assert Path(g["file"]).name in s12 and (FRAME / "test_pieces/hip_insert_guide.stl").exists()
    for step in g["procedure"][:5]:                       # start-then-finish, INSERT-SET check
        assert step.split(". ", 1)[1] in s12
    assert "START, then FINISH" in s12 and "INSERT-SET" in s12
    bmax = float(re.search(r"<= (\d+\.\d+) mm", {a["id"]: a for a in B58["assumptions"]}["GUIDE-HEAT"]["settled_by"])[1])
    assert B.guide_bore_max() == bmax == 7.4 and f"<= {bmax:.1f} mm" in s12
    assert g["procedure"][-1].split(". ", 1)[1] in s12 and "start by hand" in s12   # all 8 by hand, first article
    assert "HW-HIP-GUIDE" in pk["build_md"]
    # the guide is in the file table with its STL mass, checked against bl058.json stl
    mc = B.mass_check(pk["stl"])
    assert mc["test_pieces/hip_insert_guide"][2]


def test_torque_is_the_sourced_record_value(pk, kit):
    """HB-6b mismatch: the JSON's 2.5 N m is the insert record's tightening_torque_max_n_m; BL-055's 2.0 was untraced."""
    import yaml
    rec = yaml.safe_load((ROOT / "data/materials/hardware/insert_heatset_brass_m5.yaml").read_text())
    t = float(rec["properties"]["tightening_torque_max_n_m"])
    assert B.hip_torque_n_m(B.closeout()) == t == CO["hip"]["insert"]["torque_max_n_m"]
    assert f"{t:.1f} N m (the insert record's maximum" in sec(pk["build_md"], 12)
    hb = kit["register"]["HB-6b"]
    assert f"({t:.1f} N m" in hb["steps"] and "2.0 N m" not in hb["steps"] + hb["notes"]


def test_mount_mass_from_the_ledger(pk):
    from huntkit.mass import ledger
    g = ledger.bl056_update()["mount_g"] + ledger.bl058_update()["mount_delta_g"]
    assert B.mount_g() == pytest.approx(B58["hip_mount"]["mass_g"], abs=0.01) == pytest.approx(g, abs=0.01)
    row = [ln for ln in pk["build_md"].splitlines() if ln.startswith("| **HW-HIP-MNT**")][0]
    assert f"{g:.1f} g" in row and "D5.8" in row


# ------------------------------------------------------------------ nut and bolt windows
def test_bolt_len_window_next_to_the_nut_check(pk):
    md = pk["build_md"]
    m = re.search(r"(\d+\.\d+)-(\d+\.\d+) mm", B58["kit"]["nut"]["bolt_caliper"])
    w = f"**{m[1]}-{m[2]} mm**"
    s7, s8 = sec(md, 7), sec(md, 8)
    s82 = [ln for ln in s8.splitlines() if ln.startswith("2.")][0]
    assert w in s82 and "thickness <= 4.1 mm" in s82 and "BOLT-LEN" in s82
    s72 = [ln for ln in s7.splitlines() if ln.startswith("2.")][0]
    tol = B58["nut_check"]["bolt_len_tol_mm"]
    assert f"**{45 - tol:.1f}-{45 + tol:.1f} mm**" in s72 and "thickness <= 4.1 mm" in s72
    assert all(r["tail_clear_long_bolt_mm"] > 0 for r in B58["nut_check"]["rows"] if r["bolt"].startswith("M5 x 45"))


# ------------------------------------------------------------------ retainers, US2 pin, sleeves
def test_retainers_in_build_h1(pk):
    md = pk["build_md"]
    for s in STALE:
        assert s not in md
    s9 = sec(md, 9)
    rb = CO["pins"]["retainers_bl058"]
    assert "90153A214" in s9 and "90153A216" in s9 and "BODY POINTING FORE" in s9
    assert f"D{rb['cross_hole_d_mm']:g} mm cross hole" in s9 and rb["cross_hole_d_mm"] == 1.5
    tr = CO["pins"]["stations"]["us2"]["tether"]
    assert f"{tr['cord_mm']:.0f} mm" in s9 and "|x| 132" in s9 and "DIN 6799" in s9
    pd = B58["kit"]["PIN-RET_d"]
    assert f"(d) {pd['what']}: PASS {pd['pass']}" in s9
    shop = {m.group(1): m.group(0) for m in re.finditer(r"\| \*\*(HW-[A-Z0-9-]+)\*\* \|[^\n]*", md)}
    assert "HW-PIN-RET" not in shop and {"HW-PIN-RET-H", "HW-PIN-RET-E", "HW-PIN-TETH"} <= set(shop)
    nh = sum(v["qty"] for v in CO["pins"]["stations"].values() if v["retainer"] == "hairpin")
    assert f"| {nh} |" in shop["HW-PIN-RET-H"] and "| 2 |" in shop["HW-PIN-RET-E"]


def test_us2_pin_and_sleeve(pk):
    md = pk["build_md"]
    us2 = CO["pins"]["stations"]["us2"]
    assert us2["material"] == "alu_7075_t6" and us2["shank_mm"] == 39.6 and us2["head_mm"] == [8.0, 1.0]
    al = [ln for ln in md.splitlines() if ln.startswith("| **HW-PIN-AL**")][0]
    assert "us2 (2): shank 39.6 mm, plain head 8 x 1 mm" in al and "E-clip groove D4 x 0.74" in al
    L = B58["sleeve_bearing"]["bearing_now_mm"]
    assert L == B58["cbore"]["outer_cheek_bearing_mm"] == 6.5
    slv = [ln for ln in md.splitlines() if ln.startswith("| **HW-PIN-SLV**")][0]
    assert f"{L:g} mm (2)" in slv and "| 24 |" in slv
    assert sum(k for _, k, _ in B.sleeve_counts(B.pins())) == 24
    assert f"caliper each US2 outer sleeve {L:g} mm" in sec(md, 9)


# ------------------------------------------------------------------ masses and the README
def test_readme_masses_and_mass_band(pk):
    rd, md = pk["readme_md"], pk["build_md"]
    st = B58["stl"]
    assert f"`h1_assembled` {B.fg(round(st['h1_assembled']['g'], 1))}" in rd
    assert f"bl058.json {st['us2_clevis_R']['g']:.2f} g" in rd and "every STL mass here matches bl058.json" in rd
    by = {r["file"]: r for r in pk["stl"]}
    body = by["h1_lower_flat"]["mass_g"] + by["h1_upper_flat"]["mass_g"]          # the STL masses, as BUILD_H1 6
    assert body == pytest.approx(st["h1_lower_flat"]["g"] + st["h1_upper_flat"]["g"], abs=0.1)
    lo, hi = (body * (1 + x) for x in B.MASS_BAND)
    assert f"**{lo:.0f} to {hi:.0f} g**" in md
    # whole-body line is BL-058's on the exported STL, not BL-055's
    assert "BL-058, on the exported STL" in rd and "buckling 1.05" in rd


# ------------------------------------------------------------------ kit
def test_kit_pin_ret_has_d_and_the_new_wire(kit):
    r = kit["register"]["PIN-RET"]
    txt = " ".join(r.values())
    for s in STALE:
        assert s not in txt
    from huntkit.gendesign.bl058_frame import HAIRPIN
    assert f"new wire {HAIRPIN['wire_d']:.2f} mm" in r["steps"] and f">= {HAIRPIN['wire_d'] - 0.1:.2f} mm" in r["pass_fail"]
    pd = B58["kit"]["PIN-RET_d"]
    assert pd["what"] in r["steps"] and f"(d) {pd['pass']}" in r["pass_fail"]
    assert f"double shear {CO['pins']['clip_double_shear_n']:.0f} N" in r["safety_at_stake"] == r["safety_at_stake"]
    res = [x for x in kit["results"] if x["test_id"] == "PIN-RET"]
    assert sum(1 for x in res if x["sample"].startswith("(d)")) == 4
    assert not any("new 1.2" in x["quantity"] for x in res)


def test_kit_fit_us_marks(kit):
    r = kit["register"]["FIT-US"]
    for m in B58["kit"]["FIT-US_marks"]:
        assert m in r["steps"]
    assert B58["kit"]["FIT-US_pass"] in r["pass_fail"]
    res = [x for x in kit["results"] if x["test_id"] == "FIT-US"]
    assert sum(1 for x in res if "E-clip" in x["quantity"]) == 3      # one per crown kit end


def test_kit_hb6b_and_shopping_use_bl058(kit):
    hb = kit["register"]["HB-6b"]
    assert "M5 x 14" not in hb["steps"] + hb["specimen"] + hb["cost_basis"]
    assert "M5 x 12" in hb["specimen"] and f"{B.mount_g():.2f} g" in hb["specimen"]
    sh = kit["shopping"]
    us2 = [x for x in sh if x["item"].startswith("US2 pin set")][0]
    assert "E-clip" in us2["item"] and "R-clip" not in us2["item"]
    for s in STALE:
        assert not any(s in x["item"] for x in sh)


def test_t1_us2_lines_from_the_current_print(kit):
    rec = K.t1_us2_record()
    assert rec and rec["stl_md5"] == K.stl_md5() and rec["source"].startswith("huntkit.gendesign.h1_rev5.gauge_values")
    steps = rec["tests"]["T1|us2"]["steps"]
    assert K.gauge_tests()["T1|us2"]["steps"] == steps
    gl = K.t1_gauge_lines()["US2 ROOT"]
    top = max(steps, key=lambda s: s["pin_load_n"])
    assert gl["(b)"][1] == round(top["pass_if_abs_microstrain_at_most"])
    assert "t1_us2_gauge_bl059.json" in kit["register"]["T1"]["defined_in"]


def test_t1_us2_falls_back_to_assumption_on_another_print(monkeypatch):
    monkeypatch.setattr(K, "stl_md5", lambda path=None: "0" * 32)
    assert K.t1_us2_record() == {}
    assert K.gauge_tests()["T1|us2"] == K.rev5()["gauges"]["tests"]["T1|us2"]
    assert "ASSUMPTION T1-US2-GEOM" in K.t1_patch()["defined_in"]


def test_test_plan_row_18_and_hipbelt_doc():
    tp = (ROOT / "designs/pack_5200/tests_physical/TEST_PLAN.md").read_text()
    h = K.hip56()["tests"]["HB-6"]
    row = [ln for ln in tp.splitlines() if ln.startswith(K.HB6_PLAN_ROW)][0]
    assert f">= {h['pass_line_n_each']:.0f} N" in row and f"{h['n_coupons']} printed" in row and "60 C" in row
    assert "1.5" not in row.split("|")[3]
    hs = (AN / "hipbelt_structural.md").read_text()
    b = [ln for ln in hs.splitlines() if ln.startswith(K.HB6_STRUCT_BULLET)][0]
    assert b == K.hb6_struct_bullet() and "Pass ≥ 1.5 kN" not in hs and "****" not in b


def test_written_files_match_the_build(kit, pk):
    reg = {r["id"]: r for r in csv.DictReader(open(REG, encoding="utf-8"))}
    for tid in ("PIN-RET", "FIT-US", "HB-6b", "T1"):
        assert reg[tid]["pass_fail"] == kit["register"][tid]["pass_fail"], tid
    assert (FRAME / "BUILD_H1.md").read_text() == pk["build_md"]
    assert (FRAME / "README.md").read_text() == pk["readme_md"]
    guides = "".join(p.read_text() for p in (ROOT / "outputs/release/test_kit/guides").glob("G*.md"))
    for s in STALE:
        assert s not in guides


# ------------------------------------------------------------------ print README and gendesign docs
def test_print_readme_hip_row_and_gendesign_writer():
    from huntkit.gendesign import docs
    row = B.print_readme_hip_row()
    assert docs.protected_row("hip_pivot_mount", "slm_ti") == row
    assert docs.protected_row("stay_hub", "slm_ti") is None
    assert f"| {B.mount_g():.1f} g |" in row and "D5.8 holes" in row and "| 20.2 g |" not in row
    assert "96 h SLM service (JLC3DP" in row and "96 h service" in docs.SRC["jlc_ti"]
    txt = (ROOT / "designs/pack_5200/print/README.md").read_text()
    assert row in txt and "| 34.3 g |" not in txt


# ------------------------------------------------------------------ bag release
def test_bag_release_frame_kit_and_review6_table():
    import mfg_corrie_f_rev3 as M
    bom = list(csv.DictReader(open(MFG / "bom.csv", encoding="utf-8")))
    fk = [r for r in bom if r.get("item", "").startswith("printed fairleads")][0]["item"]
    assert "90153A214" in fk and "DIN 6799" in fk and "toward the wearer" in fk and "R-clip" not in fk
    assert "E-clip groove D4 x 0.74" in fk and "6.5 mm" in fk
    st = {i: (s, h) for i, _, s, h in M.REVIEW6_STATUS}
    for i in ("M-1", "M-2", "M-3", "M-5", "m-2", "m-3", "m-8"):
        assert st[i][0].startswith("closed (BL-058"), i
    assert f"{B58['sleeve_bearing']['min_now']:.2f}" in st["M-3"][1] and "M5 x 12" in st["m-2"][1]
    rd = (MFG / "README.md").read_text()
    for i in ("M-1", "M-2", "M-3", "M-5", "m-2", "m-3", "m-8"):
        assert f"| {i} | {'major' if i[0] == 'M' else 'minor'} | closed (BL-058" in rd, i
    assert "still open (BL-058)" not in rd
