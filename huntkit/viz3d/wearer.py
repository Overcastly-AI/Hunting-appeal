"""A clothed, posed 3D hunter wearing the pack (BL-019), for the Cycles renders.

The figure is a rendered 3D person, not a photograph. It is built on demand from CC0 MakeHuman assets by the
MPFB 2 Blender extension (GPL code, used as a tool; its output and the CC0 asset pack carry no licence burden for the
images) and sized from ANSUR II. Nothing downloaded is stored in the repo: ``assets/human_manifest.json`` lists every
URL, version, licence and SHA-256, and ``fetch_assets()`` rebuilds the cache (``HUNTKIT_HUMAN_ASSETS``, default
``~/.cache/huntkit/human_assets``).

Stages (bpy only runs in the CPython 3.11 venv of huntkit/viz3d/README.md, the pack model only in the repo Python)::

    python3 -m huntkit.viz3d.wearer model                  # pack GLB with the wearer's torso setting (repo Python)
    $BPY -m huntkit.viz3d.wearer fetch                     # download + verify the human assets (once)
    $BPY -m huntkit.viz3d.wearer render --shots hero,front --quick
    $BPY -m huntkit.viz3d.wearer render --shots all        # 1600 x 1200, 96 samples

API for other concepts (BL-018 hook)::

    from huntkit.viz3d.wearer import build_wearer
    w = build_wearer(torso_in=None, pose="stand", outfit="midlayer", glb="outputs/pack3d_wearer/corrie_b2_wearer.glb")
    # w.objects: every bpy object of the wearer + fitted pack; w.fit: the fit numbers; w.ground: floor plane (point,
    # normal); w.spec: the ANSUR-derived figure dimensions. Hand w.objects to huntkit.viz3d.studio.render.

Coordinates: the pack's FCS (x right, y aft, z up, mm) maps to Blender metres (x, -y, z); the wearer faces +Y.

Default wearer (owner requirement 2026-11-10): a 6 ft (1829 mm) man. ``figure_spec`` derives his other dimensions from
the ANSUR II regressions on stature (table below) and the pack is set to the torso length that results (18.5 in), not
to an assumed 19 in. 15 in and 23 in wearers are optional variants.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("assets") / "human_manifest.json"
IN = 25.4
OWNER_STATURE_MM = 1829.0          # owner requirement 2026-11-10: the hunter is 6 ft tall
TORSO_STEP_IN = 0.5                # geometry.yaml crown_settings: 15.0 ... 23.0 in 0.5 in steps
ILIAC_CREST_Z = 120.0              # geometry.yaml datums.iliac_crest_z (FCS mm)

# ------------------------------------------------------------------------------------------- ANSUR II regressions
# Linear regressions on stature, per sex: value_mm = a + b * stature_mm, with the standard error of estimate (SEE).
# Source: ANSUR II public release (US Army 2012; Gordon et al., NATICK/TR-15/007, 2014), ANSUR_II_MALE_Public.csv
# (n 4082) and ANSUR_II_FEMALE_Public.csv (n 1986), https://www.openlab.psu.edu/ansur2/ . Computed 2026-11-10 with
# numpy.polyfit on the raw rows (``derive_ansur`` below reproduces the table from the CSVs). "torso" is
# cervicaleheight - iliocristaleheight: the vertical C7 to iliac-crest distance, which is how geometry.yaml and the
# viz3d mannequin define the torso setting. weightkg is in units of 0.1 kg in the CSV; here it is kg.
ANSUR = {
    "male": {"n": 4082, "stature_mean": 1756.2, "stature_sd": 68.6, "stature_from_torso": (1014.4, 1.628), "reg": {
        "cervicaleheight": (-34.95, 0.88484, 11.2), "iliocristaleheight": (-107.18, 0.66651, 21.6),
        "torso": (72.23, 0.21833, 20.2), "waistheightomphalion": (-108.43, 0.66444, 21.8),
        "crotchheight": (-161.04, 0.57372, 23.9), "trochanterionheight": (-134.59, 0.59045, 25.9),
        "acromialheight": (-90.96, 0.87298, 16.2), "kneeheightmidpatella": (-65.08, 0.31625, 15.5),
        "biacromialbreadth": (160.27, 0.14557, 16.2), "bideltoidbreadth": (228.58, 0.15999, 30.9),
        "chestcircumference": (417.82, 0.36296, 84.7), "waistcircumference": (226.61, 0.40382, 109.3),
        "buttockcircumference": (301.18, 0.40787, 72.1), "hipbreadth": (86.22, 0.1473, 22.3),
        "waistbreadth": (85.2, 0.13578, 26.9), "waistdepth": (42.2, 0.11012, 34.3),
        "chestdepth": (89.58, 0.09319, 25.6), "buttockdepth": (77.27, 0.09549, 25.8),
        "headlength": (135.88, 0.03633, 6.5), "headbreadth": (131.76, 0.01262, 5.5),
        "footlength": (19.61, 0.14301, 9.1), "weightkg": (-76.52, 0.092467, 12.56),
        "sleevelengthspinewrist": (87.78, 0.45983, 25.6), "neckcircumference": (190.9, 0.11594, 25.3)}},
    "female": {"n": 1986, "stature_mean": 1628.5, "stature_sd": 64.2, "stature_from_torso": (953.5, 1.6877), "reg": {
        "cervicaleheight": (-46.6, 0.88629, 10.7), "iliocristaleheight": (-114.17, 0.68219, 19.1),
        "torso": (67.57, 0.2041, 18.1), "waistheightomphalion": (-78.72, 0.63973, 21.6),
        "crotchheight": (-137.29, 0.55729, 23.0), "trochanterionheight": (-128.76, 0.59117, 23.8),
        "acromialheight": (-88.02, 0.87152, 14.9), "kneeheightmidpatella": (-66.89, 0.31656, 14.3),
        "biacromialbreadth": (150.87, 0.13182, 14.2), "bideltoidbreadth": (232.36, 0.12915, 27.1),
        "chestcircumference": (613.99, 0.20337, 81.5), "waistcircumference": (518.2, 0.20621, 99.0),
        "buttockcircumference": (397.26, 0.38283, 69.9), "hipbreadth": (111.18, 0.14365, 23.3),
        "waistbreadth": (134.48, 0.09405, 24.9), "waistdepth": (106.69, 0.06386, 31.1),
        "chestdepth": (141.37, 0.05967, 26.0), "buttockdepth": (99.34, 0.08351, 25.8),
        "headlength": (139.28, 0.02953, 6.6), "headbreadth": (124.17, 0.01274, 5.5),
        "footlength": (27.57, 0.13455, 8.4), "weightkg": (-52.5, 0.073887, 9.93),
        "sleevelengthspinewrist": (80.17, 0.45135, 23.0), "neckcircumference": (239.28, 0.0548, 17.4)}},
}
# ANSUR II torso (cervicale - iliocristale) quantiles every 5 % from 0 to 100, and stature quantiles (mm), per sex.
ANSUR_Q = {
    "male": {"torso": [361.0, 413.0, 423.1, 430.0, 435.0, 439.0, 443.0, 446.0, 450.0, 453.0, 456.0, 459.0, 462.0,
                       465.0, 469.0, 472.0, 476.0, 480.0, 487.0, 496.0, 546.0],
             "stature": [1491.0, 1646.0, 1669.0, 1685.0, 1698.0, 1710.0, 1720.0, 1730.0, 1739.0, 1747.0, 1755.0,
                         1764.0, 1773.0, 1782.0, 1791.0, 1801.0, 1812.0, 1826.0, 1844.0, 1870.0, 1993.0]},
    "female": {"torso": [330.0, 363.0, 371.0, 377.0, 382.0, 385.0, 388.0, 391.0, 394.0, 397.0, 400.0, 403.0, 405.0,
                         408.0, 411.0, 415.0, 419.0, 423.0, 429.0, 437.0, 489.0],
               "stature": [1409.0, 1525.0, 1547.0, 1562.0, 1574.0, 1585.0, 1594.0, 1602.0, 1611.0, 1619.0, 1626.0,
                           1634.0, 1643.0, 1652.0, 1661.0, 1671.0, 1682.0, 1695.0, 1711.0, 1735.0, 1829.0]},
}


def derive_ansur(csv_dir: str | Path) -> dict:
    """Recompute ``ANSUR`` / ``ANSUR_Q`` from the two public CSVs (needs pandas; not used at run time)."""
    import pandas as pd  # noqa: PLC0415
    out = {}
    for sex in ("male", "female"):
        d = pd.read_csv(Path(csv_dir) / f"ANSUR_II_{sex.upper()}_Public.csv", encoding="latin-1")
        d["torso"] = d.cervicaleheight - d.iliocristaleheight
        d["weightkg"] = d.weightkg / 10.0
        reg = {}
        for c in ANSUR[sex]["reg"]:
            b, a = np.polyfit(d.stature, d[c], 1)
            reg[c] = (round(float(a), 2), round(float(b), 6), round(float((d[c] - (a + b * d.stature)).std()), 2))
        b, a = np.polyfit(d.torso, d.stature, 1)
        out[sex] = {"n": len(d), "stature_mean": round(float(d.stature.mean()), 1),
                    "stature_sd": round(float(d.stature.std()), 1), "stature_from_torso": (round(a, 1), round(b, 4)),
                    "reg": reg,
                    "q": {k: [round(float(np.percentile(d[k], p)), 1) for p in range(0, 101, 5)]
                          for k in ("torso", "stature")}}
    return out


def ansur_predict(sex: str, stature_mm: float) -> dict:
    """ANSUR II regression values (mm, kg) for a person of this sex and stature."""
    return {k: a + b * stature_mm for k, (a, b, _see) in ANSUR[sex]["reg"].items()}


def ansur_percentile(sex: str, key: str, value_mm: float) -> float:
    """Percentile of a stature or torso length in ANSUR II (interpolated on the 5 % quantile table)."""
    q = ANSUR_Q[sex][key]
    return float(np.interp(value_mm, q, np.arange(0, 101, 5)))


def torso_setting_in(torso_mm: float) -> float:
    """Nearest crown setting (0.5 in steps, 15 to 23 in) to a C7 to iliac-crest length."""
    return float(min(max(round(torso_mm / IN / TORSO_STEP_IN) * TORSO_STEP_IN, 15.0), 23.0))


def figure_spec(torso_in: float | None = None, stature_mm: float | None = None, sex: str | None = None) -> dict:
    """The wearer's target dimensions.

    * ``figure_spec()``: the default hunter, a 1829 mm (6 ft) man; every other dimension is the ANSUR II regression
      value at that stature and the torso setting follows from his torso length.
    * ``figure_spec(torso_in=15)`` / ``(23)``: optional variants. The stature is the ANSUR regression of stature on
      torso length (15 in: women, 23 in: men; 23 in is beyond the longest male torso in ANSUR II, an extrapolation).
    """
    if torso_in is None or stature_mm is not None:
        sex = sex or "male"
        stature = float(stature_mm or OWNER_STATURE_MM)
        dims = ansur_predict(sex, stature)
        if torso_in is not None:
            dims["torso"] = torso_in * IN
            dims["iliocristaleheight"] = dims["cervicaleheight"] - dims["torso"]
        source = "stature given; other dimensions from the ANSUR II regressions on stature"
    else:
        sex = sex or ("female" if torso_in < 16.5 else "male")
        a, b = ANSUR[sex]["stature_from_torso"]
        stature = a + b * torso_in * IN
        dims = ansur_predict(sex, stature)
        dims["torso"] = torso_in * IN                       # the requested torso, not the regression mean
        dims["iliocristaleheight"] = dims["cervicaleheight"] - dims["torso"]
        dims["waistheightomphalion"] = dims["iliocristaleheight"] - 5.0
        source = "torso given; stature from the ANSUR II regression of stature on torso, the rest from stature"
    setting = torso_setting_in(dims["torso"])
    return {"sex": sex, "stature": stature, "dims": dims, "torso_mm": dims["torso"], "torso_in": dims["torso"] / IN,
            "torso_setting_in": setting if torso_in is None else float(torso_in),
            "stature_pct": ansur_percentile(sex, "stature", stature),
            "torso_pct": ansur_percentile(sex, "torso", dims["torso"]), "source": source}


# ------------------------------------------------------------------------------------------------ asset cache
def asset_dir() -> Path:
    return Path(os.environ.get("HUNTKIT_HUMAN_ASSETS", Path.home() / ".cache" / "huntkit" / "human_assets"))


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def assets_ready(need=("mpfb", "mh_system_assets")) -> bool:
    d = asset_dir()
    m = {a["id"]: a for a in load_manifest()["assets"]}
    return all((d / m[k]["dir"] / m[k]["probe"]).exists() for k in need)


def fetch_assets(only=None) -> list:
    """Download every manifest asset into its own folder of the cache, verify SHA-256, unpack zips to ``x/``.
    Downloads are data: nothing in them is executed except the MPFB extension, which Blender loads as an add-on."""
    import subprocess  # noqa: PLC0415
    import zipfile  # noqa: PLC0415
    d = asset_dir()
    got = []
    for a in load_manifest()["assets"]:
        if only and a["id"] not in only:
            continue
        folder = d / a["dir"]
        folder.mkdir(parents=True, exist_ok=True)
        f = folder / a["file"]
        if not f.exists() or _sha256(f) != a["sha256"]:
            subprocess.run(["curl", "-sS", "-L", "--fail", "-m", "1800", "-A", "huntkit-asset-fetch", "-o", str(f),
                            a["url"]], check=True)
        sha = _sha256(f)
        if sha != a["sha256"]:
            raise RuntimeError(f"{a['id']}: sha256 {sha} != manifest {a['sha256']}")
        if f.suffix == ".zip" and not (folder / a["probe"]).exists():
            with zipfile.ZipFile(f) as z:
                z.extractall(folder / "x")
        got.append(str(f))
    return got
