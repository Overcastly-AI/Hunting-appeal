"""BL-032 part B: CORRIE F rev 3 manufacturing package (designs/pack_5200/mfg_corrie_f_rev3.py)."""
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
        assert any(g in r["proof"] for g in gates | {"port mock-up"}), r["point"]


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
    assert f"{ctx.rs.geo['b22']['placed_x']:.1f}" in b22.notes and b22.volatile == "BL-033 B-22 x"
    sw = next(o for o in pk["ops"] if o.operation.startswith("Set the") and "swells" in o.operation)
    n = sum(p.quantity for pid, p in ctx.rs.pieces.items() if pid.startswith("B-13"))
    assert sw.operation.startswith(f"Set the {n} swells")
    fp = next(o for o in pk["ops"] if o.operation.startswith("Gusset flat work: FP"))
    assert f"{pk['geo']['fp_finished_w']:.0f} mm face" in fp.notes


def test_fly_ops_follow_the_pattern(pk):
    fly = [o for o in pk["ops"] if o.step.startswith("9")]
    if pk["geo"]["fly_drafted"]:
        assert all("HOLD" not in o.operation for o in fly)
        assert all(o.volatile == "BL-033 F-01" for o in fly)
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
    pdf = M.tech_pack(pk, sk, tmp_path / "tp.pdf")
    import pypdf
    r = pypdf.PdfReader(str(pdf))
    assert len(r.pages) >= 20
    text = " ".join((p.extract_text() or "") for p in r.pages[:3])
    assert "Tech pack" in text and "Ledger reconciliation" in text
