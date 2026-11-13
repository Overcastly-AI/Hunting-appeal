"""BL-032 part B / BL-034 part C: CORRIE F rev 3 manufacturing package (designs/pack_5200/mfg_corrie_f_rev3.py)."""
import csv
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import mfg_corrie_f_rev3 as M  # noqa: E402


@pytest.fixture(scope="module")
def pk():
    return M.package()


def test_every_piece_and_webbing_line_is_sequenced(pk):
    assert M.unsequenced(pk["ctx"].rs, pk["ops"]) == []


def test_ledger_reconciles_one_to_one_and_mass_within_3pct(pk):
    ck = M.checks(pk)
    assert ck["recon_unmatched"] == 0 and ck["recon_pieces_without_row"] == 0
    assert abs(pk["mass"]["mass_delta_pct"]) <= 3.0 and pk["mass"]["mass_ok"]


def test_fabric_bom_covers_every_cut_piece_with_non_negative_waste(pk):
    rs = pk["ctx"].rs
    lines = {b.material_id: b for b in pk["bom"] if b.section == "fabric"}
    mats = {p.material_id for p in M._fabric_pieces(rs)}
    assert set(lines) == mats
    for mid, b in lines.items():
        net = sum(p.area_mm2 * p.quantity for p in M._fabric_pieces(rs) if p.material_id == mid) / 1e6
        gross = b.qty if b.unit == "m2" else b.qty * M._roll_w(mid) / 1000.0
        assert gross >= net * 0.999, mid
        assert b.waste_pct >= 0.0
        assert f"net {net:.3f} m2" in b.source
        assert b.alt_material_id                      # alternate column filled


def test_alternate_set_lines_match_the_alternate_pieces(pk):
    alt = {b.material_id for b in pk["bom"] if b.section == "fabric_alternate"}
    assert alt == {p.material_id for p in M._fabric_pieces(pk["ctx"].rsA)}
    assert "ultragrid_210d_uhmwpe_ripstop" in alt and "nylon_ripstop_70d" in alt


def test_hardware_traces_to_ledger_and_bl010_choices(pk):
    hw = [b for b in pk["bom"] if b.section == "hardware"]
    assert not [b for b in hw if b.item.startswith("UNMAPPED")]
    cara = sum(b.qty for b in hw if b.material_id == "carabiner_wiregate_22kn")
    ghook = sum(b.qty for b in hw if b.material_id == "g_hook_25mm_aluminium")
    assert cara == 5          # IM3 bag hooks 2 + IM3 free end 1 (base) + B-24 2 (meat trip), loadpath S2 / A1 / S12
    assert ghook == 9         # IM1, IM2, W1-W3, bow riser + 3 extenders
    ll = sum(h["qty"] for h in pk["ctx"].rs.hardware if h["material_id"] == "ladder_lock_25mm_heavy")
    assert sum(b.qty for b in hw if b.material_id == "ladder_lock_25mm_heavy") == ll
    for b in hw:
        assert b.cost_usd is not None and b.source


def test_load_points_cover_the_ticket_and_pass(pk):
    lp = pk["load_points"]
    parts = {r["part"] for r in lp}
    for need in ("TG", "B-28t", "T3", "W1", "W2", "W3"):          # port guys, crown straps, IM3, W1-W3
        assert need in parts, need
    assert any(r["part"].startswith("LLT") for r in lp)
    gates = {t["id"] for t in pk["tests"]}
    st = 25.4 / M.SPI["box"]
    for r in lp:
        if r["sf"] is not None:
            assert r["sf"] >= 1.0, r["point"]
        if r["pattern"].startswith("box-X"):
            w, h = (float(v) for v in r["pattern"].split("box-X ")[1].split(" mm")[0].split(" x "))
            assert r["stitches"] == math.ceil(M.AS.box_x(w, h)["path_mm"] / st) + 4
            assert r["thread"] == "bonded_nylon_tex135"
        # BL-040: an UNRATED row (no load case, e.g. the roll-top clip, a hand cinch) is checked by a QC hand pull
        ok = gates | {"port mock-up"} | ({"QC-11"} if r["load_n"] is None else set())
        assert any(g in r["proof"] for g in ok), r["point"]


def test_every_sewing_op_names_machine_needle_thread_spi_and_seam(pk):
    for o in pk["ops"]:
        if o.stitch_type in ("-",):
            continue
        assert o.machine and o.needle.startswith("Nm") and o.thread_id.startswith("bonded_nylon"), o.seq
        assert o.spi or o.stitch_type == "304", o.seq
        assert o.seam, o.seq


def test_seam_lengths_and_placements_come_from_the_pattern(pk):
    ctx, ops = pk["ctx"], {o.operation: o for o in pk["ops"]}
    zd = ctx.seams["door | blade U (#10 zip, R 55 corners)"]
    assert ops["Door #10 zip"].length_mm == pytest.approx(4 * zd, abs=0.2)
    b22 = next(o for o in pk["ops"] if o.operation.startswith("B-22 guy anchors"))
    assert f"{ctx.rs.geo['b22']['placed_x']:.1f}" in b22.notes and b22.volatile == "pattern: B-22 x"
    sw = next(o for o in pk["ops"] if o.operation.startswith("Set the") and "swells" in o.operation)
    n = sum(p.quantity for pid, p in ctx.rs.pieces.items() if pid.startswith("B-13"))
    assert sw.operation.startswith(f"Set the {n} swells")
    fp = next(o for o in pk["ops"] if o.operation.startswith("Gusset flat work: FP"))
    assert f"{pk['geo']['fp_finished_w']:.0f} mm face" in fp.notes


def test_fly_ops_follow_the_pattern(pk):
    fly = [o for o in pk["ops"] if o.step.startswith("9")]
    if pk["geo"]["fly_drafted"]:
        assert all("HOLD" not in o.operation for o in fly)
        assert all(o.volatile == "pattern: F-01" for o in fly)
    else:
        assert fly and "HOLD" in fly[0].operation


def test_thread_bom_covers_box_paths(pk):
    t135 = next(b for b in pk["bom"] if b.material_id == "bonded_nylon_tex135")
    box_mm = sum(o.length_mm for o in pk["ops"] if o.thread_id == "bonded_nylon_tex135")
    assert box_mm > 0
    assert t135.qty == pytest.approx(box_mm / 1000 * M.THREAD_FACTOR * (1 + M.THREAD_WASTE), rel=0.01)


def test_costing_and_hours_are_consistent(pk):
    c = pk["costing"]
    assert c["missing_cost"] == []
    assert c["proto_hours"] == pytest.approx(sum(o.proto_h for o in pk["ops"]), abs=0.1)
    assert c["sam_min"] == pytest.approx(sum(o.time_s for o in pk["ops"] if o.per_bag) / 60, abs=0.1)
    assert all(o.time_s == 0 for o in pk["ops"] if not o.per_bag)
    lid = sum(o.proto_h for o in pk["ops"] if o.step.startswith("6"))
    cut = next(r["hours"] for r in pk["ctx"].lid["rows"] if r["op"].startswith("cut"))
    assert lid == pytest.approx(pk["ctx"].lid["hours"] - cut, abs=0.05)   # lid cut is booked in step 0


def test_delta_register_closeout_rows(pk):
    ids = {d["id"]: d for d in pk["delta"]}
    for rd in ("RD-16", "RD-23", "RD-24", "RD-12", "RD-18"):
        assert rd in ids
    assert ids["RD-01"]["status_after_rev3_package"] == "closed"


def test_package_writes_and_tech_pack_builds(pk, tmp_path):
    files = M.write_files(pk, tmp_path)
    for f in files:
        assert f.exists() and f.stat().st_size > 0
    with (tmp_path / "op_sequence.csv").open() as fh:
        assert sum(1 for _ in csv.DictReader(fh)) == len(pk["ops"])
    sk = M.sketches(pk, tmp_path)
    design = M.techpack_design(pk, sk)
    assert M.MF.missing_sections(design) == []
    pdf = M.MF.tech_pack(design, tmp_path / "tp.pdf", strict=True)
    import pypdf
    r = pypdf.PdfReader(str(pdf))
    assert len(r.pages) >= 20
    text = " ".join((p.extract_text() or "") for p in r.pages[:3])
    assert "Tech pack" in text and "Ledger reconciliation" in text


# ---------------------------------------------------------------------------- BL-034 part C
def test_contract_records_come_from_huntkit_manufacturing(pk):
    from huntkit.manufacturing import BOMLine, SewingOp
    assert M.SewingOp is SewingOp and M.BOMLine is BOMLine
    assert all(isinstance(o, SewingOp) for o in pk["ops"]) and all(isinstance(b, BOMLine) for b in pk["bom"])


def test_record_prices_win_over_assumptions(pk):
    for k in ("slider_10", "slider_5", "cam_25mm_al", "triglide_25mm", "pom_toggle", "elastic_25mm", "elastic_6mm"):
        assert k not in M.PRICE_ASSUMED, k
    for b in pk["bom"]:
        if b.material_id in ("slider_10", "slider_5", "cam_25mm_al", "pom_toggle") and b.section == "hardware":
            assert b.unit_cost_usd == pytest.approx(M.MAT.load(b.material_id).cost_usd["value"]), b.item
        if b.material_id.startswith("elastic") and b.section == "webbing":
            assert b.unit_cost_usd == pytest.approx(M.MAT.load(b.material_id).cost_usd["value"]), b.item


def test_us_backstop_is_the_stainless_triglide(pk):
    ss = [b for b in pk["bom"] if b.section == "hardware" and "STAINLESS" in b.item]
    assert len(ss) == 1 and ss[0].material_id == "triglide_25mm" and ss[0].qty == 2
    assert ss[0].unit_cost_usd == M.TG_SS_USD and ss[0].unit_cost_usd > 5 * M.MAT.load("triglide_25mm").cost_usd["value"]
    assert "US-tg" in ss[0].source and "US1/US2 backstop" in ss[0].source
    assert "US-BS" in {t["id"] for t in pk["tests"]}


def test_ledger_hardware_rows_all_mapped(pk):
    ck = M.checks(pk)
    assert ck["unmapped_hardware"] == []
    rows = [t for t, (_k, how, _l) in M.ledger_map(pk["ctx"]).items()]
    assert any(t.startswith("BL-034 records:") for t in rows) and any(t.startswith("BL-034 thread:") for t in rows)


def test_op_407_released_and_b11_from_the_pattern(pk):
    ck = M.checks(pk)
    assert ck["holds"] == []
    o = next(o for o in pk["ops"] if o.seq == "4.07")
    assert "B-11" in o.operation and "HOLD" not in o.operation + o.notes
    b11 = pk["ctx"].rs.geo["b11"]
    assert o.pieces.startswith(f"B-11 x{2 * b11['per_gusset']}")
    w, h = M._b11_box(pk["ctx"].rs)
    assert o.length_mm == pytest.approx(2 * b11["per_gusset"] * M.AS.box_x(w, h)["path_mm"], abs=0.2)


def test_no_webbing_part_is_box_sewn_twice(pk):
    seen: dict = {}
    for o in pk["ops"]:
        if "box" in o.stitch_type and o.length_mm:
            for x in o.pieces.split(","):
                t, _, n = x.strip().partition(" x")
                seen[t] = seen.get(t, 0) + (int(n) if n.isdigit() else 1)
    qty = {}
    for w in pk["ctx"].rs.webbing:
        if not ("kit S" in w["kit"] or "kit L" in w["kit"]):
            qty[w["id"]] = qty.get(w["id"], 0) + w["qty"]
    for pid, n in seen.items():
        if pid in qty:
            assert n <= qty[pid], (pid, n, qty[pid])
    titles = [o.operation for o in pk["ops"]]
    for pid in ("IME", "T3", "LLT", "HE"):                     # the old 7.15 / 7.19 / 7.22 (+ HE 7.18) are gone
        assert not any(t.startswith(f"{pid}: ") for t in titles), pid


def test_thread_in_the_bag_excludes_cone_waste(pk):
    for b in (b for b in pk["bom"] if b.section == "thread"):
        m_sewn = M.MF.thread_metres(pk["ops"], M.THREAD_FACTOR)[b.material_id]
        assert b.qty == pytest.approx(m_sewn * (1 + M.THREAD_WASTE), abs=0.06)
        g = m_sewn * M.MAT.load(b.material_id).require("mass_g_m")
        assert f"= {g:.1f} g in the bag (no cone waste)" in b.notes
    ck = M.checks(pk)
    assert ck["thread_bag_g"] == pytest.approx(sum(
        M.MF.thread_metres(pk["ops"], M.THREAD_FACTOR)[t] * M.MAT.load(t).require("mass_g_m")
        for t in M.MF.thread_metres(pk["ops"], M.THREAD_FACTOR) if t.startswith("bonded")), abs=0.01)


def test_load_points_use_the_pattern_boxes(pk):
    rs = pk["ctx"].rs
    lp = pk["load_points"]

    def sizes(part):
        return {tuple(float(v) for v in r["pattern"].split("box-X ")[1].split(" mm")[0].split(" x "))
                for r in lp if r["part"] == part and r["pattern"].startswith("box-X")}
    for pid in ("B-24", "B-25", "US", "IM1", "W3", "TG", "IMC"):         # BL-041: GBL deleted, IMC added
        drawn = {(w, h) for w, h, _ in M.boxes_of(rs.pieces[pid])}
        assert drawn and sizes(pid) == drawn, pid
    hook = next(r for r in lp if r["point"] == "B-24 float link: hook end")
    hw, hh, _ = next(b for b in M.boxes_of(rs.pieces["B-24"]) if "hook" in b[2])
    assert hook["pattern"].startswith(f"box-X {hw:.0f} x {hh:.0f} mm")
    band = {(w, h) for w, h, lab in M.boxes_of(rs.pieces["B-02h"]) if "B-28" in lab}
    assert sizes("B-02h") == band
    assert not [r for r in lp if "ASSUMPTION" in (r["note"] or "")]


def test_ops_quote_the_pattern_placements(pk):
    g = pk["geo"]
    kw = next(o for o in pk["ops"] if o.operation.startswith("Aft corner seams"))
    for zz in g["kw_z"].values():
        assert f"{zz['R']:.0f}" in kw.notes and f"{zz['L']:.0f}" in kw.notes
    assert "KW-PLACE" not in kw.notes
    fp = next(o for o in pk["ops"] if o.operation.startswith("Gusset flat work: FP"))
    assert "clamp" not in fp.notes and f"{g['fp_margin']}" in fp.notes
    f02 = next(o for o in pk["ops"] if o.operation.startswith("F-02 fly base pocket"))
    assert "F02-PLACE" not in f02.notes and "drawn" in f02.notes
    b28 = next(o for o in pk["ops"] if o.operation.startswith("B-28 front tabs"))
    bw, bh = next((w, h) for w, h, lab in M.boxes_of(pk["ctx"].rs.pieces["B-02h"]) if "B-28" in lab)
    assert f"{bw:.0f} x {bh:.0f} mm" in b28.notes and b28.length_mm == pytest.approx(2 * M.AS.box_x(bw, bh)["path_mm"], abs=0.2)
