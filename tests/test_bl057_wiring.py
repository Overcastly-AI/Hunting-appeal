"""BL-057: BL-056 results wired into the test kit, the register and the frame build package; the lugs.py guard."""
import csv
import inspect
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1_build as B  # noqa: E402
import physical_test_kit as K  # noqa: E402

AN = ROOT / "designs" / "pack_5200" / "analysis"
C56 = json.loads((AN / "clevis_bl056.json").read_text())
H56 = json.loads((AN / "hip_mount_bl056.json").read_text())
REV5 = json.loads((AN / "h1_rev5.json").read_text())
REG = ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv"


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


@pytest.fixture(scope="module")
def pk():
    return B.package()


# ------------------------------------------------------------------ 1. CLEVIS-SHARE from clevis_bl056.json
def test_clevis_share_loads_and_lines_are_bl056(kit):
    r = kit["register"]["CLEVIS-SHARE"]
    cl = K.clevis_loadings()
    for lab, k in C56["kit"].items():
        assert cl[lab]["proof_n"] == k["proof_n"] and cl[lab]["peak_n"] == k["cycle_peak_n"]
        assert cl[lab]["valley_n"] == round(k["R"] * k["cycle_peak_n"])
        for g in k["gauge_lines"]:
            assert f"PASS if size <= {g['pass_if_abs_microstrain_at_most']:.0f}" in r["pass_fail"]
    assert (cl["A"]["proof_n"], cl["B"]["proof_n"]) == (1103.9, 642.9)
    assert (cl["A"]["peak_n"], cl["B"]["peak_n"]) == (735.9, 428.6)
    # BL-053 lines that BL-056 moved are gone (A proof 4159 -> 4156, B proof 2681 -> 2679)
    old = REV5["gauges"]["tests"]
    for key in ("CLEVIS-SHARE|us2_inboard", "CLEVIS-SHARE|us2_yz"):
        for s_old, s_new in zip(old[key]["steps"], C56["gauges"]["tests"][key]["steps"]):
            if s_old["pass_if_abs_microstrain_at_most"] != s_new["pass_if_abs_microstrain_at_most"]:
                assert f"PASS if size <= {s_old['pass_if_abs_microstrain_at_most']:.0f};" not in r["pass_fail"]
    assert "clevis_bl056.json" in r["defined_in"] and "h1_rev5.json joint" not in r["what_it_proves"]
    s1 = C56["joint"]["share_1"]
    assert f"fatigue {s1['worst_fatigue']['fatigue']}" in r["what_it_proves"]          # 1.36, was 0.86
    # the results sheet carries the same bands
    rows = [x for x in kit["results"] if x["test_id"] == "CLEVIS-SHARE" and x["unit"] == "microstrain"]
    assert any(x["limit"] == "-4156..4156" for x in rows) and not any(x["limit"] == "-4159..4159" for x in rows)


def test_written_register_and_kit_match_the_build(kit):
    reg = {r["id"]: r for r in csv.DictReader(open(REG, encoding="utf-8"))}
    for tid in ("CLEVIS-SHARE", "HB-6", "HB-6b"):
        assert reg[tid]["pass_fail"] == kit["register"][tid]["pass_fail"], tid
    man = json.loads((ROOT / "outputs/release/test_kit/manifest.json").read_text())
    assert man["totals"]["usd"] == round(sum(x["total_usd"] for x in kit["shopping"]), 2)
    assert f"{len({o['test'] for o in kit['order'] if o['stage'] == 'run'})} tests" in man["checks"][-1]


# ------------------------------------------------------------------ 2. HB-6 / HB-6b
def test_hb6_row_is_the_bl056_test(kit):
    h = H56["tests"]["HB-6"]
    r = kit["register"]["HB-6"]
    assert f"{h['n_coupons']} printed PAHT-CF coupons" in r["title"] and "BUILD Z" in r["title"] and "60 C" in r["title"]
    assert f">= {h['pass_line_n_each']:.0f} N" in r["title"] and "1.5 kN" not in r["pass_fail"]
    assert f"{h['minimum_for_8_inserts_n']:.0f} N" in r["pass_fail"]
    assert "hip_mount_bl056.json" in r["defined_in"]
    assert K.TEST_RELEASE["HB-6"] == "R1"
    res = [x for x in kit["results"] if x["test_id"] == "HB-6" and x["unit"] == "N"]
    assert len(res) == h["n_coupons"] and all(x["limit"] == f"{h['pass_line_n_each']:.0f}" for x in res)


def test_hb6b_run1_lines_are_the_published_ones(kit):
    hb = H56["tests"]["HB-6b"]
    r = kit["register"]["HB-6b"]
    assert r["status"] == "ACTIVE" and set(r) == set(K.COLS)
    for st in hb["steps"]:
        assert f"V {st['pin_load_v_n']:.0f} N" in r["pass_fail"]
        assert f"PASS if <= {st['pass_if_microstrain_at_most']:.0f}" in r["pass_fail"]
    assert [s["screw_line"] for s in K.hb6b_runs()["run1"]] == [60.0, 96.0, 180.0]
    assert [s["V_n"] for s in K.hb6b_runs()["run1"]] == [534.0, 854.0, 1601.0]
    assert f"{hb['cycles']['n']:,}".replace(",", "") == "100000" and "1e5 cycles 0 -> 854 N" in r["steps"]
    # the gauged screw is the model's most-loaded insert and sits where BL-056 put the gauge
    gx, gz = K.hb6b_gauged_screw()
    assert (abs(gx), gz) == (14.12, 107.29)
    assert "HB-6b" in [o["test"] for o in kit["order"] if o["group"] == "G6"]


def test_hb6b_sideways_run_lines_derived_from_bl056_models(kit):
    """Run 2 (orchestrator call): leg line = part-FE lateral leg-root p99.5 / E x 1.15; screw line = tip_tension x 1.15."""
    from huntkit.gendesign import h1_closeout as C
    rr = K.hb6b_runs()
    lat = H56["fe"]["lateral_offset_sensitivity"]["rows"]
    ch = json.loads((AN / "h1_closeout.json").read_text())["hip"]["chosen"]
    E = 110000.0
    As = math.pi / 4 * 4.2 ** 2
    for s, k in zip(rr["run2"], ("carry", "walk", "C2")):
        sig = lat[f"{k}|H_pin"]["sigma_p995_mpa"]
        assert s["leg_line"] == round(1.15 * sig / E * 1e6)
        T = C.tip_tension(ch["pattern"], ch["rows"][f"{k}|H_pin"]["V_n"], ch["rows"][f"{k}|H_pin"]["H_n"])["T_max_n"]
        assert s["screw_line"] == round(1.15 * T / As / E * 1e6)
        assert s["screw_ue"] < s["screw_line"]                     # the vector value sits under the scalar bound
    assert rr["run2"][-1]["leg_line"] == 5424 and rr["pad_offset_mm"] == 20.0
    r = kit["register"]["HB-6b"]
    assert "SIDEWAYS" in r["steps"] and "STOP there" in r["pass_fail"] and "reopened" in r["pass_fail"]
    for s in rr["run2"]:
        assert f"PASS if <= {s['leg_line']:.0f}" in r["pass_fail"]
    assert "LEG-GAUGE-LINE" in r["defined_in"] and "SIDE-SCREW-LINE" in r["defined_in"]


def test_tip_vector_equals_the_published_model_when_the_lifts_line_up():
    from huntkit.gendesign import h1_closeout as C
    ch = json.loads((AN / "h1_closeout.json").read_text())["hip"]["chosen"]
    pat = ch["pattern"]
    g = K.hb6b_gauged_screw()
    for k in ("carry", "walk", "C2"):
        V = ch["rows"][f"{k}|H_frame"]["V_n"]
        ref = C.tip_tension(pat, V, 0.0)["T_max_n"]
        assert K.tip_vector(pat, V, 0.0, 0.0, g, n_dir=72) == pytest.approx(ref, abs=0.1)
        # a vertical pad offset (lifts parallel) adds e H arithmetically, as tip_tension does
        H = ch["rows"][f"{k}|H_pin"]["H_n"]
        assert K.tip_vector(pat, V, H, 20.0, g, lift_h=(0.0, -1.0), n_dir=72) == pytest.approx(
            C.tip_tension(pat, V, H, e=20.0)["T_max_n"], abs=0.1)


# ------------------------------------------------------------------ 4. BL-055B leftovers
def test_gauge_sign_note_follows_the_data(kit):
    sg = K.gauge_signs()
    assert "T1 at the US2 root" in sg["plus"]                       # h1_rev5 T1|us2 reads tension
    assert "CLEVIS-SHARE at the US2 root" in sg["minus"]
    r = kit["register"]["CLEVIS-SHARE"]
    assert "TENSION (plus) for T1 at the US2 root" in r["specimen"]
    assert "the model reads compression (minus) at every US1 and cradle site" not in r["specimen"]


def test_order_of_work_legend_sits_below_the_bars(kit, tmp_path, monkeypatch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figs = []
    real_close = plt.close
    monkeypatch.setattr(plt, "close", lambda f=None: figs.append(f))
    K.charts(kit["order"], kit["shopping"], kit["levels"], kit["ranking"], tmp_path)
    fig = figs[0]
    ax = fig.axes[0]
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    leg = ax.get_legend().get_window_extent(r)
    bars = [p.get_window_extent(r) for p in ax.patches]
    assert all(leg.y1 <= b.y0 + 0.5 for b in bars)                  # no bar under the legend
    for f in figs:
        real_close(f)


# ------------------------------------------------------------------ 3. frame README / BUILD_H1 / print README
def test_frame_package_reads_bl056(pk):
    md, rd = pk["build_md"], pk["readme_md"]
    mc = B.mass_check(pk["stl"])
    assert mc and all(v[2] for v in mc.values())
    assert mc["us2_clevis_R"][1] == C56["mass"]["us2_clevis_R"]["g"] == 15.71
    assert mc["h1_assembled"][1] == C56["mass"]["h1_assembled"]["g"] == 1069.4
    assert "15.7 g" in rd and "1069.4 g" in rd and "1061.1 g" not in rd and "13.7 g" not in rd
    blk = C56["joint"]["block"]
    assert f"x +/-{blk['trap_x0_mm']:.1f} to {blk['nut_face_x_mm']:.0f}" in md and "INBOARD" in md
    from huntkit.mass import ledger
    g = ledger.bl056_update()["mount_g"]
    assert f"{g:.1f} g" in md and "HOLD LIFTED" in md and "HOLD before ordering" not in md
    row = [ln for ln in md.splitlines() if ln.startswith("| **HW-HIP-MNT**")][0]
    assert f"{g:.1f} g" in row and "must be redrawn" not in row
    assert "SLM-MASS" in md


def test_print_readme_hip_row_from_the_ledger_and_cost_rule():
    from huntkit.gendesign.printables import slm_cost
    from huntkit.mass import ledger
    import trimesh
    row = B.print_readme_hip_row()
    g = ledger.bl056_update()["mount_g"]
    assert f"| {g:.1f} g |" in row
    vol = float(trimesh.load(ROOT / "designs/pack_5200/print/lug_hip_pivot_mount_slm_ti.stl").volume)
    assert f"${slm_cost(vol, 1, 'ti'):.0f}" in row
    # the same rule gives the old README's $73 on the drawn part
    old = trimesh.load(ROOT / "designs/pack_5200/print/legacy/lug_hip_pivot_mount_slm_ti_D44_drawn.stl").volume
    assert round(slm_cost(float(old), 1, "ti")) == 73
    txt = (ROOT / "designs/pack_5200/print/README.md").read_text()
    assert row in txt and "| 20.2 g |" not in txt


# ------------------------------------------------------------------ 5. lugs.py guard
def test_lug_export_never_targets_the_redrawn_mount(tmp_path):
    from huntkit.gendesign import lugs as L
    pr = ROOT / "designs/pack_5200/print"
    with pytest.raises(L.ProtectedFileError):
        L.output_stem("hip_pivot_mount", "slm_ti", pr)
    with pytest.raises(L.ProtectedFileError):
        L.output_stem("hip_pivot_mount", "slm_ti", pr, redirect_dir=pr)
    st = L.output_stem("hip_pivot_mount", "slm_ti", pr, redirect_dir=tmp_path)
    assert st.parent == tmp_path and st.name == "lug_hip_pivot_mount_slm_ti_gendesign"
    assert L.output_stem("stay_hub", "slm_ti", pr) == pr / "lug_stay_hub_slm_ti"
    assert L.output_stem("hip_pivot_mount", "fdm_pacf", pr) == pr / "lug_hip_pivot_mount_fdm_pacf"
    # the gendesign export goes through the guard
    from huntkit.gendesign import cli
    src = inspect.getsource(cli.lug_task)
    assert "output_stem(spec.name, variant, PRINT, redirect_dir=WORK)" in src and 'PRINT / ("lug_"' not in src
    # and the protected file is the BL-056 redraw (D50, 8 + 1 holes)
    assert H56["stl"].endswith("lug_hip_pivot_mount_slm_ti.stl") and H56["geometry"]["base"]["holes"] == 9


# ------------------------------------------------------------------ 6. shopping / count
def test_shopping_and_count(kit):
    sh = kit["shopping"]
    assert any("HB-6b" in x["tests"] and "Ti / steel-matched" in x["item"] for x in sh)
    assert any("HB-6b" in x["tests"] and "M5 x 14" in x["item"] for x in sh)
    runs = {o["test"] for o in kit["order"] if o["stage"] == "run"}
    assert "HB-6b" in runs and len(runs) == 87
