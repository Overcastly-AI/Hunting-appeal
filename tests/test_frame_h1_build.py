"""BL-054: H1 frame build package, gate print text and the review-5 minors (m-1..m-10)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "designs" / "pack_5200"
sys.path.insert(0, str(PACK))

import frame_h1_build as B  # noqa: E402


@pytest.fixture(scope="module")
def pk():
    return B.package()


def test_masses_and_footprints_from_the_stl(pk):
    import trimesh
    by = {r["file"]: r for r in pk["stl"]}
    rho = B.rho_print()
    for f in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_R"):
        m = trimesh.load(B.PRINT / f"{f}.stl")
        assert by[f]["mass_g"] == pytest.approx(m.volume * rho, abs=0.06)
        assert by[f]["extents_mm"] == pytest.approx([round(float(v), 1) for v in m.extents], abs=0.06)
        assert by[f]["watertight"]
    body = by["h1_lower_flat"]["mass_g"] + by["h1_upper_flat"]["mass_g"]
    assert pk["checks"]["body_g"] == pytest.approx(body, abs=0.1)
    # the README's stale numbers (review 5 M-7) are gone: the expected weight is the STL body, not 846 g
    assert "846 g" not in pk["build_md"] and "880 g" not in pk["build_md"]
    lo, hi = (body * (1 + x) for x in B.MASS_BAND)
    assert f"**{lo:.0f} to {hi:.0f} g**" in pk["build_md"]
    e = by["h1_lower_flat"]["extents_mm"]
    assert f"{e[0]:.1f} x {e[1]:.1f} mm" in pk["build_md"]


def test_no_superseded_pointer_and_one_build_path(pk):
    md = pk["build_md"] + pk["readme_md"]
    assert "as in `../frame/PRODUCTION.md`" not in md
    assert "BUILD_H1.md" in pk["readme_md"]
    assert "Supports: none" not in md and "no supports" not in pk["build_md"].split("## 10.")[0]


def test_b25_sleeves_go_on_before_the_corners_are_bonded(pk):
    s = pk["build_md"].split("### 13b.")[1]
    i_sleeve = s.index("Slide both B-25 bar sleeves onto the top bar now")
    i_saddle = s.index("Slide the clamp's saddle onto the top bar")
    i_corner = s.index("Bond the two corners")
    i_clamp = s.index("Bond the clamp")
    assert i_saddle < i_sleeve < i_corner < i_clamp
    # the op number is the release op list's, not a literal
    assert f"bag op {B.op_no('B-25')}" in s


def test_hardware_ids_match_the_joint_code(pk):
    from huntkit.gendesign.frame_h1 import JOINT as Z
    from huntkit.gendesign.h1_bedfit import JOINT as C
    md = pk["build_md"]
    rows = {m.group(1): m.group(0) for m in re.finditer(r"\| \*\*(HW-[A-Z0-9-]+)\*\* \|[^\n]*", md)}
    assert len(rows) == len(set(rows)) >= 25
    assert f"M5 x {Z.bolt_len:.0f}" in rows["HW-J234-SCR"] and f"M5 x {C.bolt_len:.0f}" in rows["HW-US2-SCR"]
    assert f"{Z.washer_od:.0f} mm OD" in rows["HW-J234-WSH"] and f"{C.washer_od:.0f} mm OD" in rows["HW-US2-WSH"]
    # M-7's missing items are on the list
    for hid in ("HW-PIN-TI", "HW-PIN-AL", "HW-PIN-SLV", "HW-PAWL-PIN", "HW-PAWL-SLV", "HW-PAWL-SPR", "HW-HIP-INS",
                "HW-BUSH", "HW-SPINE", "HW-RACK", "HW-MMA", "HW-BEADS", "HW-CLAMP", "HW-PIN-RET"):
        # BL-059: BL-058 split HW-PIN-RET into HW-PIN-RET-H (hairpin clips) and HW-PIN-RET-E (US2 E-clips)
        assert hid in rows or any(k.startswith(hid + "-") for k in rows), hid
    pn = B.pins()
    n_ti = sum(q for _, q, _ in B.pin_groups(B.pin_rows()).get("Ti-6Al-4V", []))
    assert f"| {2 * pn['stations']} |" in rows["HW-PIN-SLV"] and f"| {pn['stations'] - n_ti} |" in rows["HW-PIN-AL"]
    assert pn["im_span_mm"] == 36.0 and pn["hinge_span_mm"] == 40.0


def test_bl053_placeholders_until_its_data_lands(pk):
    sec3 = pk["build_md"].split("## 3.")[1].split("## 4.")[0]
    if pk["bl053"]:
        assert B.PLACEHOLDER not in sec3
    else:
        assert B.PLACEHOLDER in sec3 and "Do not start a body print" in sec3
        assert "tree supports from the build plate" in sec3


def test_spine_clamp_drawing(tmp_path, pk):
    from huntkit.gendesign import crown_spine_clamp as C
    cp = pk["clamp"]
    assert cp["saddle_len_mm"] == 2 * C.SPINE_CLAMP_HALF_X and cp["mass_g"] == C.SPINE_CLAMP_MASS_G
    assert cp["spine_axis_offset_fore_mm"] == pytest.approx(C.SPINE_AXIS_FORE_MM, abs=0.01)
    assert cp["collar_below_bar_underside_mm"] == C.SPINE_CLAMP_COLLAR
    files = B.clamp_drawing(cp, tmp_path)
    assert {p.suffix for p in files} >= {".pdf", ".png"}
    assert all(p.stat().st_size > 1000 for p in files)
    # the T6(c) pass line is 1.5 x the largest limit spine force on the clamp
    assert f"1.5 x {cp['limit_spine_axial_n']:.0f} N" in pk["build_md"]


def test_piece_print_text_has_supports_and_no_semicolons():
    for p in ("hefit_hinge_fairlead_R", "us_route_stay_R", "im3ec_cheek_R"):
        t = B.piece_print_txt(p)
        assert "SUPPORTS REQUIRED" in t and "FROM THE BUILD PLATE" in t and ";" not in t
    t = B.piece_print_txt("us2_clevis_R")
    assert t.count("NO supports") == 1 and ";" not in t


# ------------------------------------------------------------------ test kit (item 2, m-1, m-3, m-4, m-5, m-7, m-8)
@pytest.fixture(scope="module")
def K():
    import physical_test_kit as K
    return K


def test_step_splitter_keeps_marked_steps_whole(K):
    he = K.he_fit_row()
    st = K.split_steps(he["steps"])
    labels = [re.match(r"\*\*Step (\w+)\.\*\*", s).group(1) for s in st if s.startswith("**Step ")]
    assert labels == [str(i) for i in range(9)]                       # (0)..(8), not 29 fragments
    assert not any(s.startswith(("Pass criterion", "Shopping list", ")")) for s in st)
    mt = K.split_steps(K.mt1cr_row()["steps"])
    assert [s[:12] for s in mt] == ["**Step A.** ", "**Step B.** "]
    assert K.split_steps("a (b; c); d") == ["a (b; c)", "d"]


def test_gate_print_text_and_stale_numbers(K):
    he = K.he_fit_row()
    assert "H1 settings" not in he["steps"] and "SUPPORTS REQUIRED" in he["steps"]
    assert f"as op {K.op_no('USA')}" in he["steps"] and "as op 7.16" not in he["steps"]
    assert "0.3 mm clear" not in he["steps"] and "< 0.7 mm" not in he["steps"]
    assert "31.9 g" not in he["cost_basis"] and "BL-042 z 60" not in he["title"]
    assert "the the" not in he["specimen"] + he["steps"] + K.pt3_steps()
    assert "SUPPORTS REQUIRED" in K.pt3_steps() and "SUPPORTS REQUIRED" in K.clevis_row()["specimen"]
    assert "x 50 dowel" in K.FIX_PIN and K.FIX_PIN_LEN == 50
    assert "HALF bridge" in K.gauge_txt() and "temperature" in K.gauge_txt()
    fu = K.fit_us_row()
    assert "(8) US STRAP CLEARANCE ON THE REAL BAG" in fu["steps"] and "lower aft edge" in fu["steps"]


# ------------------------------------------------------------------ mfg (m-2, m-6) and meat haul (item 4)
def test_mfg_op_refs_and_bts_spec():
    import mfg_corrie_f_rev3 as M
    assert "BT-S 10 x 2 mm zigzag, 28 st" in M.step_spec("bt", "304", bt="BT-S")
    assert "BT-M 16 x 2 mm zigzag" in M.step_spec("bt", "304")
    M._OPIDX.clear()
    M._OPIDX.update({"B-25": "7.19"})
    assert M.opref(f"op {M.OP('B-25')} gate") == "op 7.19 gate"
    flat = " ".join(" ".join(r[1:]) for r in M.FOURTH_STATUS + M.THIRD_STATUS) + " ".join(
        " ".join(a) for a in M.ASSUMPTIONS)
    assert "op 7.18" not in flat


def test_meat_haul_step6_is_advice():
    from huntkit.gendesign import meat_haul as MH
    t = MH.belly_advice()
    assert f"{MH.BELLY_FRAME_SAFE_MM:.0f} mm" in t
    if (MH.ANALYSIS / "h1_rev5.json").exists():
        assert "advice, not a safety rule" in t
    else:
        assert "Never under 60 mm" in t


# ---------------------------------------------------------------------------- BL-055 Part B (item 2)
def _fake_closeout(tmp_path):
    """A close-out JSON in Part A's shapes (h1_closeout.pins / hip_check / mass_rows), US1 moved to Ti."""
    import copy
    import json
    pins = copy.deepcopy(B.rev5()["pins"])
    u = pins["stations"]["us1"]
    u.update({"material": "ti_6al_4v", "pin_g": round(u["pin_g"] * 4430 / 2810, 2),
              "was": {"material": "alu_7075_t6", "pin_g": u["pin_g"], "bending": dict(u["bending"])}})
    pins["bom"] = [{"id": f"PIN-{k.upper()}"} for k in pins["stations"]]
    pat = {"boss_d": 44.0, "hole_d": 6.4, "hole_depth": 11.5, "wall_rule_mm": 2.6,
           "positions_xz": [[16.0, 120.0], [0.0, 136.0], [-16.0, 120.0], [0.0, 104.0]],
           "walls": {"edge_mm": 2.8, "between_mm": 16.2, "to_pin_bore_mm": 7.8, "floor_mm": 4.5}}
    d = {"hip": {"chosen": {"pattern": pat, "min_sf": {"strength": 1.6, "fatigue": 1.2, "creep": 2.0},
                            "capacity": {"static_n": 900.0, "basis": "test"}, "pass": True},
                 "insert": {"pullout_n": 1200.0, "hole_d": 6.4, "torque_max_n_m": 2.5}},
         "pins": pins, "mass": {"hip_screw": "Ti gr5 M5 x 14 DIN 7984"}}
    p = tmp_path / "h1_closeout.json"
    p.write_text(json.dumps(d))
    return p


def test_build_reads_the_part_a_pins_and_hip_pattern(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "CLOSEOUT_JSON", _fake_closeout(tmp_path))
    co = B.closeout()
    assert co["pins"]["stations"]["us1"]["material"] == "ti_6al_4v" and co["hip_screw"].startswith("Ti gr5 M5")
    pk = B.package()
    md = pk["build_md"]
    assert B.PENDING not in md and pk["checks"]["bl055_data"]
    shop = {r.split("|")[1].strip(" *"): r for r in md.splitlines() if r.startswith("| **HW-")}
    assert shop["HW-PIN-TI"].split("|")[3].strip() == "4"          # hinge 2 + US1 2
    assert shop["HW-PIN-AL"].split("|")[3].strip() == "8"
    assert "us1" in shop["HW-PIN-TI"] and "us1" not in shop["HW-PIN-AL"]
    assert shop["HW-HIP-INS"].split("|")[3].strip() == "6"         # 4 + 2 spare
    # BL-059: the screw is BL-058's when bl058.json is on file (M5 x 12), else the close-out's booking
    scr = "M5 x 12" if B.bl058() else "M5 x 14"
    assert shop["HW-HIP-SCR"].split("|")[3].strip() == "4" and scr in shop["HW-HIP-SCR"]
    s12 = md.split("## 12. Hip mount")[1].split("## 13.")[0]
    for x, z in ((+16.0, 0.0), (0.0, +16.0), (-16.0, 0.0), (0.0, -16.0)):   # positions relative to the boss centre
        assert f"| {x:+.1f} | {z:+.1f} |" in s12
    # BL-059: service torque = the insert record's maximum (2.5 N m in the fake close-out), not BL-055's untraced 2.0
    assert "count 4 pilot holes" in s12 and ">= 11.5 mm" in s12 and "2.5 N m" in s12 and "PASSES" in s12
    s9 = md.split("## 9.")[1].split("## 10.")[0]
    assert "**Ti-6Al-4V** (**HW-PIN-TI**, 4)" in s9 and "us1 (shank" in s9
    assert "1.58 x a 7075 pin" in s9


def test_build_marks_part_a_pending_when_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "CLOSEOUT_JSON", tmp_path / "missing.json")
    pk = B.package()
    md = pk["build_md"]
    assert pk["checks"]["pending_bl055"] >= 2 and not pk["checks"]["bl055_data"]
    assert "Do not heat-set any hip insert" in md


def test_published_closeout_leaves_no_pending_box(pk):
    if not B.CLOSEOUT_JSON.exists():
        pytest.skip("BL-055 Part A has not published h1_closeout.json")
    co = B.closeout()
    assert co["pins"] and co["hip"], "h1_closeout.json lacks the pin rows or the hip check in the expected shape"
    assert B.PENDING not in pk["build_md"] and B.PENDING not in pk["readme_md"]
    n = len(co["hip"]["pattern"]["positions_xz"])
    assert f"count {n} pilot holes" in pk["build_md"]
    assert co["pins"]["stations"]["us1"]["material"] == "ti_6al_4v"
