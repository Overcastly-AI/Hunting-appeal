"""huntkit.manufacturing: contract records (SewingOp, BOMLine) and the tech pack builder (BL-034 part C)."""
import json

import pytest

from huntkit import manufacturing as MF
from huntkit.manufacturing import cli


def _op(seq, length, thread="bonded_nylon_tex90", per_bag=True):
    return MF.SewingOp(seq=seq, operation="op " + seq, machine="WF1", stitch_type="301", spi=8, thread_id=thread,
                       needle="Nm 110/18 DPx17, round point R", attachment="-", notes="", time_s=60.0,
                       length_mm=length, per_bag=per_bag)


def test_contract_fields_in_order():
    assert MF.SEWING_OP_FIELDS[:10] == ("seq", "operation", "machine", "stitch_type", "spi", "thread_id", "needle",
                                        "attachment", "notes", "time_s")
    assert MF.BOM_LINE_FIELDS[:8] == ("section", "item", "material_id", "qty", "unit", "waste_pct", "unit_cost_usd",
                                      "cost_usd")


def test_imperial_and_cost_helpers():
    a = MF.BOMLine("fabric", "x", "m1", 0.9144, "m", 5.0, 10.0, 9.14)
    b = MF.BOMLine("fabric", "y", "m2", 1.0, "m2", 5.0, None, None)
    c = MF.BOMLine("hardware", "z", "h", 2, "unit", 0.0, 1.5, 3.0)
    assert MF.imperial(a) == "1.00 yd" and MF.imperial(b) == "10.76 ft2" and MF.imperial(c) == ""
    assert MF.bom_cost([a, b, c]) == pytest.approx(12.14)
    assert MF.bom_cost([a, b, c], {"hardware"}) == pytest.approx(3.0)
    assert MF.missing_cost([a, b, c]) == ["y"]
    assert MF.bom_rows([a])[0]["imperial"] == "1.00 yd"


def test_thread_metres_without_waste():
    ops = [_op("1.01", 1000.0), _op("1.02", 500.0, "bonded_nylon_tex135"), _op("1.03", 300.0, "-")]
    t = MF.thread_metres(ops, 2.75)
    assert t == {"bonded_nylon_tex90": pytest.approx(2.75), "bonded_nylon_tex135": pytest.approx(1.375)}


def _design(tmp_path, with_all=True):
    from PIL import Image
    png = tmp_path / "flat.png"
    Image.new("RGB", (200, 100), "white").save(png)
    secs = [MF.Section("Flats", [MF.image(png, 100, 50)]),
            MF.Section("Bill of materials", [MF.bom_table([MF.BOMLine("fabric", "x", "m1", 1.0, "m", 5, 2.0, 2.0)])]),
            MF.Section("Cutting plan", [MF.table([["a", "b"], [1, None]], [20, 20])]),
            MF.Section("Sewing operation sequence", [MF.ops_table([_op("1.01", 100.0)]), MF.page_break(),
                                                     MF.h2("more"), MF.para("a < b & c"), MF.space(2)]),
            MF.Section("QC checkpoints", [MF.para("QC-01")])]
    if with_all:
        secs.append(MF.Section("Packaging", [MF.para("poly bag")]))
    return MF.TechPack(title="Test item", date="20261113", cover=[["Pieces", "3"]], sections=secs)


def test_missing_sections_and_strict(tmp_path):
    assert MF.missing_sections(_design(tmp_path)) == []
    d = _design(tmp_path, with_all=False)
    assert MF.missing_sections(d) == ["packaging"]
    with pytest.raises(ValueError):
        MF.tech_pack(d, tmp_path / "x.pdf", strict=True)


def test_tech_pack_pdf_has_cover_sections_and_tables(tmp_path):
    import pypdf
    p = MF.tech_pack(_design(tmp_path), tmp_path / "tp.pdf", strict=True)
    r = pypdf.PdfReader(str(p))
    assert len(r.pages) == 8                     # cover + 6 sections, one with a page break
    text = " ".join(pg.extract_text() or "" for pg in r.pages)
    for want in ("Tech pack: Test item", "Bill of materials", "Packaging", "a < b & c", "op 1.01", "page 8"):
        assert want in text, want


def test_cli_renders_a_json_spec(tmp_path, capsys):
    spec = {"title": "CLI item", "cover": [["k", "v"]],
            "sections": [{"title": t, "blocks": [{"kind": "p", "text": t}]} for t in
                         ("Flats", "BOM", "Pattern list", "Operation sequence", "QC", "Packaging")]}
    f = tmp_path / "spec.json"
    f.write_text(json.dumps(spec))
    assert cli.main(["check", str(f)]) == 0
    assert cli.main(["techpack", str(f), str(tmp_path / "o.pdf"), "--strict"]) == 0
    assert (tmp_path / "o.pdf").stat().st_size > 1000
    assert cli.main(["fields"]) == 0
    assert '"SewingOp"' in capsys.readouterr().out
