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
    "male": {"n": 4082, "stature_mean": 1756.2, "stature_sd": 68.6,
            "stature_from_torso": (1014.4, 1.628), "reg": {
        "cervicaleheight": (-78.12, 0.90844, 11.2), "iliocristaleheight": (-150.35, 0.69011, 21.6), "torso":
        (72.23, 0.21833, 20.2), "waistheightomphalion": (-157.37, 0.69117, 21.8), "crotchheight": (-176.32,
        0.58208, 23.9), "trochanterionheight": (-169.93, 0.60976, 25.9), "acromialheight": (-126.89, 0.89261,
        16.2), "kneeheightmidpatella": (-112.13, 0.34194, 15.5), "biacromialbreadth": (154.64, 0.14864, 16.2),
        "bideltoidbreadth": (249.82, 0.14839, 30.9), "chestcircumference": (504.54, 0.31554, 84.7),
        "waistcircumference": (345.64, 0.33876, 109.3), "buttockcircumference": (352.33, 0.3799, 72.1),
        "hipbreadth": (108.34, 0.13517, 22.3), "waistbreadth": (104.74, 0.12624, 33.6), "waistdepth": (98.33,
        0.0794, 34.3), "chestdepth": (105.82, 0.08429, 25.6), "buttockdepth": (100.38, 0.08283, 25.8),
        "headlength": (133.08, 0.03782, 6.5), "headbreadth": (143.69, 0.00606, 5.5), "footlength": (30.13,
        0.13725, 9.1), "weightkg": (-85.309, 0.097273, 12.56), "sleevelengthspinewrist": (101.93, 0.45206,
        25.6), "neckcircumference": (268.79, 0.07337, 25.3)}},
    "female": {"n": 1986, "stature_mean": 1628.5, "stature_sd": 64.2,
              "stature_from_torso": (953.5, 1.6877), "reg": {
        "cervicaleheight": (-90.41, 0.91256, 10.5), "iliocristaleheight": (-157.98, 0.70846, 20.0), "torso":
        (67.57, 0.2041, 18.1), "waistheightomphalion": (-173.09, 0.70817, 20.9), "crotchheight": (-179.1,
        0.59038, 23.6), "trochanterionheight": (-126.9, 0.59703, 23.0), "acromialheight": (-96.85, 0.87932,
        13.7), "kneeheightmidpatella": (-106.94, 0.34142, 14.0), "biacromialbreadth": (102.82, 0.16121, 15.1),
        "bideltoidbreadth": (189.14, 0.16038, 26.8), "chestcircumference": (402.37, 0.33436, 79.9),
        "waistcircumference": (280.02, 0.35671, 97.3), "buttockcircumference": (291.94, 0.44785, 70.2),
        "hipbreadth": (91.92, 0.16083, 24.6), "waistbreadth": (69.95, 0.1412, 31.7), "waistdepth": (89.34,
        0.07596, 31.0), "chestdepth": (87.95, 0.09792, 26.6), "buttockdepth": (83.94, 0.09149, 23.6),
        "headlength": (122.19, 0.04153, 7.0), "headbreadth": (127.19, 0.01264, 5.1), "footlength": (18.5,
        0.13988, 8.6), "weightkg": (-80.886, 0.091278, 9.29), "sleevelengthspinewrist": (34.18, 0.47438, 22.6),
        "neckcircumference": (186.11, 0.08823, 18.4)}},
}
# ANSUR II torso (cervicale - iliocristale) and stature quantiles every 5 % from 0 to 100 (mm), per sex.
ANSUR_Q = {
    "male": {"torso": [361.0, 413.0, 423.1, 430.0, 435.0, 439.0, 443.0, 446.0, 450.0, 453.0, 456.0, 459.0, 462.0, 465.0,
        469.0, 472.0, 476.0, 480.0, 487.0, 496.0, 546.0],
        "stature": [1491.0, 1648.0, 1669.0, 1685.0, 1699.0, 1710.0, 1720.0, 1729.0, 1738.0, 1745.0, 1755.0, 1764.0, 1773.0,
        1782.0, 1791.0, 1802.0, 1813.0, 1827.0, 1844.0, 1870.0, 1993.0]},
    "female": {"torso": [330.0, 363.0, 371.0, 377.0, 382.0, 385.0, 388.0, 391.0, 394.0, 397.0, 400.0, 403.0, 405.0, 408.0,
        411.0, 415.0, 419.0, 423.0, 429.0, 437.0, 489.0],
        "stature": [1409.0, 1525.0, 1547.0, 1563.0, 1575.0, 1586.2, 1595.0, 1603.0, 1611.0, 1617.2, 1626.0, 1634.0, 1643.0,
        1653.0, 1661.0, 1672.0, 1681.0, 1696.0, 1713.0, 1740.0, 1829.0]},
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


# ======================================================================================================= bpy side
def _bpy():
    import bpy  # noqa: PLC0415
    return bpy


_MPFB = {}


def enable_mpfb():
    """Register the cached MPFB extension with this bpy session (a custom extension repo in the asset cache) and
    return its service classes. Raises FileNotFoundError when the cache is empty (run ``fetch``)."""
    if _MPFB:
        return _MPFB
    bpy = _bpy()
    m = {a["id"]: a for a in load_manifest()["assets"]}["mpfb"]
    src = asset_dir() / m["dir"] / "x"
    if not (src / "blender_manifest.toml").exists():
        raise FileNotFoundError(f"MPFB not in {src}: run `python -m huntkit.viz3d.wearer fetch`")
    repo_dir = asset_dir() / "bl_ext_repo"
    (repo_dir).mkdir(parents=True, exist_ok=True)
    link = repo_dir / "mpfb"
    if not link.exists():
        link.symlink_to(src, target_is_directory=True)
    repos = bpy.context.preferences.extensions.repos
    if "huntkit_human" not in [r.module for r in repos]:
        repos.new(name="huntkit_human", module="huntkit_human", custom_directory=str(repo_dir))
    mod = "bl_ext.huntkit_human.mpfb"
    import addon_utils  # noqa: PLC0415
    addon_utils.modules_refresh()
    if mod not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module=mod)
    import importlib  # noqa: PLC0415
    _MPFB["human"] = importlib.import_module(mod + ".services.humanservice").HumanService
    _MPFB["target"] = importlib.import_module(mod + ".services.targetservice").TargetService
    _MPFB["data"] = src / "data"
    return _MPFB


def _mh(*parts) -> str:
    m = {a["id"]: a for a in load_manifest()["assets"]}["mh_system_assets"]
    return str(asset_dir().joinpath(m["dir"], "x", *parts))


# MakeHuman hm08 base-mesh landmark vertices (topology is fixed, so indices are stable across every morph).
V_NAVEL = 4121            # centre of the navel dimple, front midline: omphalion
V_CROTCH = 6431           # lowest midline point of the trunk: crotch
V_C7 = (858, 857)         # back midline, where the neck leaves the thoracic curve; their midpoint = cervicale
V_VERTEX = 881            # top of the head
CREST_ABOVE_NAVEL = 5.0   # mm. ANSUR II men: iliocristale height - omphalion height, regression values at 1829 mm
#                           (1111.9 - 1106.8). ASSUMPTION: the crest is not a surface feature of the mesh, so it is
#                           placed from the navel. Settles with: palpated crest on a 3D body scan of the same person.
TUNE_TARGETS = ("torso/measure-napetowaist-dist", "hip/hip-waist", "legs/measure-upperleg-height",
                "legs/measure-lowerleg-height", "torso/measure-waist-circ")


def _body_coords(bm):
    """Rest coordinates (object space, m) of the base mesh with its shape keys applied, no armature / masks."""
    bpy = _bpy()
    shown = [(m, m.show_viewport) for m in bm.modifiers]
    for m in bm.modifiers:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = bm.evaluated_get(dg)
    V = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get("co", V)
    for m, s in shown:
        m.show_viewport = s
    return V.reshape(-1, 3)


def _group_mask(ob, name):
    gi = ob.vertex_groups[name].index
    return np.array([any(g.group == gi for g in v.groups) for v in ob.data.vertices])


def _hull_perimeter(P):
    """Perimeter of the 2D convex hull (Andrew monotone chain): a taut tape around a body section."""
    P = np.unique(np.round(np.asarray(P, float), 6), axis=0)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def half(pts):
        h = []
        for q in pts:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (q[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(q)
        return h
    H = np.array(half(P)[:-1] + half(P[::-1])[:-1])
    return float(np.linalg.norm(H - np.roll(H, 1, axis=0), axis=1).sum())


def _slice(V, E, z, xmax):
    """Points where mesh edges cross the horizontal plane z, within |x| < xmax (taut-tape section of the trunk)."""
    a, b = V[E[:, 0]], V[E[:, 1]]
    m = (a[:, 2] - z) * (b[:, 2] - z) < 0
    a, b = a[m], b[m]
    t = (z - a[:, 2]) / (b[:, 2] - a[:, 2])
    P = a + (b - a) * t[:, None]
    return P[np.abs(P[:, 0]) < xmax][:, :2]


def measure_figure(bm, scale_to_mm=1000.0) -> dict:
    """ANSUR-style dimensions (mm) of an MPFB base mesh in its rest pose, feet on z = 0."""
    V = _body_coords(bm) * scale_to_mm
    body = _group_mask(bm, "body")
    z0 = V[body][:, 2].min()
    V = V - [0, 0, z0]
    E = np.array([e.vertices[:] for e in bm.data.edges])
    E = E[body[E[:, 0]] & body[E[:, 1]]]
    stature = float(V[V_VERTEX, 2])
    c7 = 0.5 * (V[V_C7[0]] + V[V_C7[1]])
    navel = V[V_NAVEL]
    crest = float(navel[2] + CREST_ABOVE_NAVEL)
    out = {"stature": stature, "cervicaleheight": float(c7[2]), "waistheightomphalion": float(navel[2]),
           "iliocristaleheight": crest, "torso": float(c7[2] - crest), "crotchheight": float(V[V_CROTCH, 2])}
    xw = 0.14 * stature
    W = _slice(V, E, navel[2], xw)
    out["waistcircumference"] = _hull_perimeter(W)
    out["waistbreadth"] = float(np.ptp(W[:, 0]))
    out["waistdepth"] = float(np.ptp(W[:, 1]))
    zs = np.linspace(0.47, 0.56, 19) * stature          # buttock: the largest hull girth between crotch and waist
    girths = [_hull_perimeter(_slice(V, E, z, 0.16 * stature)) for z in zs]
    k = int(np.argmax(girths))
    B = _slice(V, E, zs[k], 0.16 * stature)
    out["buttockcircumference"] = girths[k]
    out["hipbreadth"] = float(np.ptp(B[:, 0]))
    out["buttockdepth"] = float(np.ptp(B[:, 1]))
    return out


def _new_human(macro, details, scale=0.1):
    S = enable_mpfb()
    bm = S["human"].create_human(scale=scale, macro_detail_dict=macro)
    for name, w in details.items():
        if abs(w) < 1e-4:
            continue
        f = S["data"] / "targets" / f"{name}-{'incr' if w > 0 else 'decr'}.target.gz"
        if name == "hip/hip-waist":
            f = S["data"] / "targets" / f"{name}-{'down' if w > 0 else 'up'}.target.gz"
        nm = f.name.split(".")[0]
        S["target"].load_target(bm, str(f), weight=min(abs(w), 1.0), name=nm)
        kb = bm.data.shape_keys.key_blocks.get(nm)
        if kb is not None and abs(w) > 1.0:              # beyond the slider end: extrapolate the morph linearly
            kb.slider_max = 2.0
            kb.value = min(abs(w), 2.0)
    return bm


def _delete(ob):
    bpy = _bpy()
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0:
        bpy.data.meshes.remove(me)


FIGURE_LOOK = {   # MakeHuman macro sliders that are a styling choice, not anthropometry (0..1)
    "male": {"gender": 1.0, "age": 0.58, "muscle": 0.62, "weight": 0.8, "proportions": 0.55, "cupsize": 0.5, "firmness": 0.5,
             "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}},
    "female": {"gender": 0.0, "age": 0.52, "muscle": 0.58, "weight": 0.7, "proportions": 0.55, "cupsize": 0.4, "firmness": 0.6,
               "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}},
}
WAIST_MORPH_MAX = 0.35
_TUNE_KEYS = ("cervicaleheight", "waistheightomphalion", "crotchheight", "waistcircumference")


def tune_figure(spec: dict, iters: int = 4, verbose=False) -> dict:
    """Solve the MakeHuman sliders so the mesh matches the ANSUR targets as ratios of stature: nape-to-waist and
    waist height (torso length), leg length (crotch height) and the waist-girth morph (girth at the navel).
    Returns {"macro", "details", "scale", "measured" (mm at the final scale), "target"}. Damped Gauss-Newton on finite
    differences; each evaluation builds a throw-away base mesh (0.3 s)."""
    sex, st = spec["sex"], spec["stature"]
    tgt = dict(spec["dims"])
    tgt["waistheightomphalion"] = tgt["iliocristaleheight"] - CREST_ABOVE_NAVEL
    want = np.array([tgt[k] / st for k in _TUNE_KEYS])
    wts = np.array([1.0, 1.0, 1.0, 0.25])

    def build(p):
        macro = dict(FIGURE_LOOK[sex], height=0.6)
        details = {TUNE_TARGETS[0]: p[0], TUNE_TARGETS[1]: p[1], TUNE_TARGETS[2]: p[2], TUNE_TARGETS[3]: p[2],
                   TUNE_TARGETS[4]: p[3]}
        return macro, details

    def res(p):
        macro, details = build(p)
        bm = _new_human(macro, details)
        m = measure_figure(bm)
        _delete(bm)
        return (np.array([m[k] / m["stature"] for k in _TUNE_KEYS]) - want) * wts, m

    p = np.zeros(4)
    # The waist-girth morph grows the waist radially and fills the lumbar hollow the belt's lumbar pad sits in, so it
    # is capped at WAIST_MORPH_MAX; the girth that is then missing against ANSUR is reported, not hidden.
    lo, hi = np.array([-2.0, -2.0, -2.0, -WAIST_MORPH_MAX]), np.array([2.0, 2.0, 2.0, WAIST_MORPH_MAX])
    r, m = res(p)
    for it in range(iters):
        J = np.empty((4, 4))
        for j in range(4):
            dp = np.zeros(4)
            dp[j] = 0.15
            if p[j] + dp[j] > hi[j]:
                dp[j] = -dp[j]
            J[:, j] = (res(p + dp)[0] - r) / dp[j]
        step = np.linalg.lstsq(J, -r, rcond=1e-4)[0]
        p = np.clip(p + np.clip(step, -0.8, 0.8), lo, hi)
        r, m = res(p)
        if verbose:
            print(f"tune {it}: p {p.round(3)} |r| {np.abs(r / wts).max() * st:.1f} mm", flush=True)
        if np.abs((r / wts)[:3]).max() * st < 1.5 and (it > 0):
            break
    macro, details = build(p)
    scale = st / m["stature"]
    return {"macro": macro, "details": details, "scale": float(scale), "target": tgt,
            "measured": {k: v * scale for k, v in m.items()}}


# ------------------------------------------------------------------------------------------------- the figure
@dataclass
class Wearer:
    """What ``build_wearer`` returns. ``objects`` is everything to render (bpy objects, world space, pose baked)."""
    objects: list = field(default_factory=list)
    figure: list = field(default_factory=list)       # body, eyes, clothes, cap ...
    pack: list = field(default_factory=list)         # visible pack parts (fitted harness and belt included)
    props: list = field(default_factory=list)        # trekking poles, binoculars
    rig: object = None
    spec: dict = field(default_factory=dict)         # figure_spec() + the tuned sliders and measured dimensions
    fit: dict = field(default_factory=dict)          # pack-on-body fit numbers (mm, deg)
    ground: tuple = ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0))   # a point on the ground and its normal (m)
    pose: str = "stand"
    outfit: str = "midlayer"
    look_at: tuple = (0.0, 0.0, 1.0)                 # a good camera target (m)


PALETTE_FILE = REPO / "designs" / "apparel" / "colorways.yaml"
# Outfits: generic technical clothing in solid colours from designs/apparel/colorways.yaml (names below). The apparel
# line is not designed yet, so the cut is the CC0 MakeHuman garment mesh, recoloured: no logos, no camo.
OUTFITS = {
    "midlayer": {"suit": "male_casualsuit02", "top": "Lichen Stone", "pants": "Spruce Shadow", "cap": "Elk Wallow",
                 "boots": "#3a2c20"},
    "jacket": {"suit": "male_casualsuit05", "top": "Krummholz Sage", "pants": "Spruce Shadow", "cap": "Elk Wallow",
               "boots": "#3a2c20", "shirt": "Lichen Stone"},
}


def palette() -> dict:
    """{colour name: hex} from the apparel colourways file (every ``name:`` / ``hex:`` pair)."""
    import re  # noqa: PLC0415
    txt = PALETTE_FILE.read_text()
    return {m.group(1): m.group(2) for m in re.finditer(r'name:\s*"([^"]+)"[^#]*?hex:\s*"(#[0-9A-Fa-f]{6})"', txt, re.S)}


def _hex(c: str):
    from .cycles_render import hexlin  # noqa: PLC0415
    if not c.startswith("#"):
        c = palette()[c]
    return hexlin(c)


def _cloth_material(name, base, normal_png=None, ao_png=None, rough=0.86, sheen=0.5, weave_mm=1.1, bump=0.35):
    """Solid-colour technical fabric: the garment's own normal map (sewn folds, seams) plus a fine weave bump."""
    bpy = _bpy()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial")
    bsdf = N("ShaderNodeBsdfPrincipled")
    L(bsdf.outputs[0], out.inputs["Surface"])
    col = N("ShaderNodeRGB")
    col.outputs[0].default_value = (*base[:3], 1.0)
    src = col.outputs[0]
    tc = N("ShaderNodeTexCoord")
    noise = N("ShaderNodeTexNoise")                         # dye / wear mottling
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 5.0
    L(tc.outputs["Object"], noise.inputs["Vector"])
    mot = N("ShaderNodeMixRGB")
    mot.blend_type = "MULTIPLY"
    ramp = N("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.3, 0.7
    ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = 0.86, 1.06
    L(noise.outputs["Fac"], ramp.inputs["Value"])
    mot.inputs["Fac"].default_value = 1.0
    L(src, mot.inputs["Color1"])
    L(ramp.outputs[0], mot.inputs["Color2"])
    src = mot.outputs[0]
    if ao_png and Path(ao_png).exists():
        ao = N("ShaderNodeTexImage")
        ao.image = bpy.data.images.load(str(ao_png), check_existing=True)
        ao.image.colorspace_settings.name = "Non-Color"
        mul = N("ShaderNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        mul.inputs["Fac"].default_value = 0.55
        L(src, mul.inputs["Color1"])
        L(ao.outputs["Color"], mul.inputs["Color2"])
        src = mul.outputs[0]
    L(src, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    for k, v in (("Sheen Weight", sheen), ("Sheen Roughness", 0.5), ("Specular IOR Level", 0.3)):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = v
    normal = None
    if normal_png and Path(normal_png).exists():
        ni = N("ShaderNodeTexImage")
        ni.image = bpy.data.images.load(str(normal_png), check_existing=True)
        ni.image.colorspace_settings.name = "Non-Color"
        nm = N("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 1.0
        L(ni.outputs["Color"], nm.inputs["Color"])
        normal = nm.outputs[0]
    wv = N("ShaderNodeTexWave")                              # weave: two crossed fine wave bands in object space
    wv.inputs["Scale"].default_value = 1000.0 / weave_mm / 6.283
    wv.bands_direction = "DIAGONAL"
    L(tc.outputs["Object"], wv.inputs["Vector"])
    bp = N("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.0004
    L(wv.outputs["Fac"], bp.inputs["Height"])
    if normal is not None:
        L(normal, bp.inputs["Normal"])
    L(bp.outputs[0], bsdf.inputs["Normal"])
    return mat


def _leather_material(name, base, normal_png=None, rough=0.55):
    mat = _cloth_material(name, base, normal_png, None, rough=rough, sheen=0.05, weave_mm=3.0, bump=0.08)
    return mat


def _split_suit(ob, z_split):
    """Split a one-piece MakeHuman suit into top / pants (/ shirt) by loose part: a part whose centroid is above
    ``z_split`` (object z, m) is top. Returns {"top": faces mask, "pants": ...} as per-polygon material indices."""
    import bmesh  # noqa: PLC0415
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen, parts = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            comp.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        parts.append(comp)
    cls = {}
    for comp in parts:
        z = np.array([q.co.z for q in comp])
        top = z.mean() > z_split
        for q in comp:
            cls[q.index] = 0 if top else 1
    bm.free()
    return cls


def build_figure(spec: dict | None = None, outfit: str = "midlayer", tuned: dict | None = None, subdiv: int = 1,
                 verbose=False) -> dict:
    """The dressed, rigged figure in its rest (A) pose, standing on z = 0 at the origin, facing -Y (MakeHuman
    convention). Returns {"rig", "body", "clothes": {...}, "extras": [...], "tuned"}."""
    bpy = _bpy()
    S = enable_mpfb()
    spec = spec or figure_spec()
    tuned = tuned or tune_figure(spec, verbose=verbose)
    bm = _new_human(tuned["macro"], tuned["details"], scale=0.1 * tuned["scale"])
    S["target"].bake_targets(bm)
    bm.name = "wearer_body"
    rig = S["human"].add_builtin_rig(bm, "game_engine")
    rig.name = "wearer_rig"
    sex = spec["sex"]
    skin = "middleage_caucasian_male" if sex == "male" else "young_caucasian_female"
    S["human"].set_character_skin(_mh("skins", skin, skin + ".mhmat"), bm, skin_type="ENHANCED_SSS")
    out = {"rig": rig, "body": bm, "clothes": {}, "extras": [], "tuned": tuned, "spec": spec}
    for typ, rel in (("Eyes", "eyes/high-poly/high-poly.mhclo"), ("Eyebrows", "eyebrows/eyebrow001/eyebrow001.mhclo"),
                     ("Eyelashes", "eyelashes/eyelashes01/eyelashes01.mhclo")):
        o = S["human"].add_mhclo_asset(_mh(*rel.split("/")), bm, asset_type=typ, subdiv_levels=0,
                                       material_type="MAKESKIN")
        o.name = "wearer_" + typ.lower()
        out["extras"].append(o)
    of = OUTFITS[outfit]
    suit_dir = Path(_mh("clothes", of["suit"]))
    suit = S["human"].add_mhclo_asset(str(suit_dir / (of["suit"] + ".mhclo")), bm, asset_type="Clothes",
                                      subdiv_levels=0, material_type="MAKESKIN")
    suit.name = "wearer_suit"
    boots_dir = Path(_mh("clothes", "shoes03"))
    boots = S["human"].add_mhclo_asset(str(boots_dir / "shoes03.mhclo"), bm, asset_type="Clothes", subdiv_levels=0,
                                       material_type="MAKESKIN")
    boots.name = "wearer_boots"
    # materials: solid palette colours over the garment's own normal map
    nrm, ao = suit_dir / (of["suit"] + "_normal.png"), suit_dir / (of["suit"] + "_ao.png")
    mats = [_cloth_material("wearer_top", _hex(of["top"]), nrm, ao, weave_mm=1.6, bump=0.3),
            _cloth_material("wearer_pants", _hex(of["pants"]), nrm, ao, weave_mm=1.0, bump=0.25, rough=0.8,
                            sheen=0.3)]
    suit.data.materials.clear()
    for m in mats:
        suit.data.materials.append(m)
    navel_z = float((_body_coords(bm)[V_NAVEL])[2])
    cls = _split_suit(suit, navel_z - 0.02 * spec["stature"] / 1000.0)
    for poly in suit.data.polygons:
        poly.material_index = cls[poly.vertices[0]]
    boots.data.materials.clear()
    boots.data.materials.append(_leather_material("wearer_boots", _hex(of["boots"]),
                                                  boots_dir / "shoes03_normal.png"))
    out["clothes"] = {"suit": suit, "boots": boots}
    for o in [bm, suit, boots] + out["extras"]:
        for p in o.data.polygons:
            p.use_smooth = True
    if subdiv:
        for o in (bm, suit, boots):
            if not any(m.type == "SUBSURF" for m in o.modifiers):
                m = o.modifiers.new("subdiv", "SUBSURF")
                m.levels = m.render_levels = subdiv
    return out


# ------------------------------------------------------------------- pack model stage (repo Python, no bpy needed)
PACK_OUT = REPO / "outputs" / "pack3d_wearer"
PACK_GLB = PACK_OUT / "corrie_b2_wearer.glb"
_T19_ONLY = ("imp2_", "imp6_", "corrie_top_guys")     # viz3d parts that exist for the 19 in setting only


def build_pack_glb(torsos_in=None, out_dir: Path = PACK_OUT) -> Path:
    """CORRIE B.2 (huntkit.viz3d.corrie_b2, unchanged) exported with the wearer's torso setting among its crown
    variants, plus ``pack_fit.json`` (the design numbers the fit is checked against, read from geometry.yaml).

    corrie_b1 draws the hose, bite valve, strap phone pocket and top guys for the 19 in setting only. For any other
    setting they are copied and moved rigidly with the shoulder-strap top / crown (a visual placement, not a design
    change)."""
    import copy  # noqa: PLC0415

    from .corrie_b2 import corrie_b2_pack  # noqa: PLC0415
    from .export import build_materials, export_glb, manifest  # noqa: PLC0415
    from .params import load_geometry, load_params  # noqa: PLC0415
    from .viewer import build_html  # noqa: PLC0415
    want = sorted(set([float(t) for t in (torsos_in or [figure_spec()["torso_setting_in"]])] + [19.0]))
    p = load_params(str(REPO / "designs" / "pack_5200" / "spec.yaml"), {"torsos_in": want})
    pack = corrie_b2_pack(p)
    by = {q.name: q for q in pack.parts}
    for t in want:
        if abs(t - 19.0) < 1e-6:
            continue
        s19, st = by["shoulder_straps@t19"].mesh.vertices, by[f"shoulder_straps@t{t:g}"].mesh.vertices
        top = lambda V: V[V[:, 2] > V[:, 2].max() - 40.0].mean(0)      # noqa: E731
        d_strap = top(st) - top(s19)
        d_crown = by[f"crown@t{t:g}"].mesh.vertices.mean(0) - by["crown@t19"].mesh.vertices.mean(0)
        for q in list(pack.parts):
            if q.torso is not None and abs(q.torso - 19.0) < 1e-6 and q.name.startswith(_T19_ONLY):
                c = copy.copy(q)
                c.mesh = q.mesh.copy()
                c.mesh.vertices = c.mesh.vertices + (d_crown if q.name.startswith("corrie_top_guys") else d_strap)
                c.name = q.name.replace("@t19", f"@t{t:g}")
                c.torso = t
                pack.parts.append(c)
    out_dir.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, out_dir / PACK_GLB.name, mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()} if isinstance(m.get("torsos"), dict) else m.get("torsos")
    build_html(glb, manifest(pack), m, info, out_dir / (PACK_GLB.stem + "_viewer.html"),
               title="Pack 5200 CORRIE B.2 (wearer torso settings)")
    g = load_geometry(p)
    hp = g["frame"]["hard_points"]
    crowns = {}
    for v in g["frame"].get("crown_settings", []) if isinstance(g["frame"].get("crown_settings"), list) else []:
        crowns[f"{v['torso_in']:g}"] = v
    if not crowns:                                           # crown settings live elsewhere in the YAML: search
        def walk(o):
            if isinstance(o, dict):
                if "torso_in" in o and "lifter_angle_deg" in o:
                    crowns[f"{o['torso_in']:g}"] = o
                for x in o.values():
                    walk(x)
            elif isinstance(o, list):
                for x in o:
                    walk(x)
        walk(g)
    hc = [r for r in g.get("head_clearance", {}).get("rows", []) if r.get("state") == "rolled"]
    fit = {"source": "designs/pack_5200/geometry.yaml", "iliac_crest_z": g["frame"]["datums"]["iliac_crest_z"],
           "hipbelt_pivot": hp["hipbelt_pivot"], "yoke_drop_below_C7_mm": g["frame"]["datums"]["yoke_drop_below_C7_mm"],
           "torsos_in": want,
           "crown": {k: {kk: v[kk] for kk in ("torso_mm", "yoke_anchor", "lifter_anchor_R", "lifter_angle_deg")
                         if kk in v} for k, v in crowns.items() if float(k) in want},
           "head_gap_neutral_mm": {f"{r['torso_in']:g}/{r['head']}": r["gap_neutral_mm"] for r in hc},
           "belt_b": {k: v for k, v in pack.metrics.get("belt_b", {}).items()}}
    (out_dir / "pack_fit.json").write_text(json.dumps(fit, indent=1, default=float))
    return glb


# ------------------------------------------------------------------------------------------------------ posing
# Directions are in the figure's own frame: F forward, R to the wearer's right, U up. The MakeHuman rest figure faces
# -Y with its left side at +X, so F = -Y, R = -X.
def _fru(f=0.0, r=0.0, u=0.0):
    from mathutils import Vector  # noqa: PLC0415
    return Vector((-r, -f, u))


def _aim_bone(rig, name, direction, twist_deg=0.0):
    """Rotate pose bone ``name`` (about its head) so its axis points along ``direction`` (rig space)."""
    bpy = _bpy()
    from mathutils import Matrix, Vector  # noqa: PLC0415
    bpy.context.view_layer.update()
    pb = rig.pose.bones[name]
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(direction).normalized())
    R = q.to_matrix() @ M.to_3x3()
    if twist_deg:
        R = Matrix.Rotation(math.radians(twist_deg), 3, Vector(direction).normalized()) @ R
    N = R.to_4x4()
    N.translation = M.translation
    pb.matrix = N
    bpy.context.view_layer.update()


def _two_bone(rig, upper, lower, target, pole, end=None):
    """Analytic two-bone IK in rig space: the tail of ``lower`` reaches ``target``; the joint bends toward ``pole``.
    Returns the reach error (m) when the target is farther than the limb."""
    bpy = _bpy()
    from mathutils import Vector  # noqa: PLC0415
    bpy.context.view_layer.update()
    a, b = rig.pose.bones[upper], rig.pose.bones[lower]
    S = a.head.copy()
    l1, l2 = a.length, (b.length if end is None else (rig.pose.bones[end].bone.head_local - b.bone.head_local).length)
    l1 = (b.bone.head_local - a.bone.head_local).length
    T = Vector(target)
    d = T - S
    dist = min(d.length, (l1 + l2) * 0.999)
    err = d.length - dist
    dn = d.normalized()
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = Vector(pole) - dn * Vector(pole).dot(dn)
    p = p.normalized() if p.length > 1e-6 else Vector((0, -1, 0))
    E = S + dn * x + p * h
    _aim_bone(rig, upper, E - S)
    bpy.context.view_layer.update()
    _aim_bone(rig, lower, (S + dn * dist) - rig.pose.bones[lower].head)
    return err


def _curl_fingers(rig, side, curl, thumb=None, spread=0.0):
    """Curl the four fingers by ``curl`` (0 flat .. 1 fist): each phalanx turns toward the palm about its own X."""
    for f in ("index", "middle", "ring", "pinky"):
        for k, gain in ((1, 0.9), (2, 1.0), (3, 0.7)):
            pb = rig.pose.bones[f"{f}_0{k}_{side}"]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (math.radians(85.0 * curl * gain) * FINGER_SIGN, 0.0, 0.0)
    t = curl * 0.5 if thumb is None else thumb
    for k, gain in ((2, 0.8), (3, 0.8)):
        pb = rig.pose.bones[f"thumb_0{k}_{side}"]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(60.0 * t * gain) * FINGER_SIGN, 0.0, 0.0)


FINGER_SIGN = 1.0     # sign of the local-X rotation that closes a game_engine-rig finger (checked by test render)

POSES = ("stand", "walk", "side", "kneel", "front")


def _leg_len(rig, s):
    b = rig.data.bones
    return ((b[f"calf_{s}"].head_local - b[f"thigh_{s}"].head_local).length
            + (b[f"foot_{s}"].head_local - b[f"calf_{s}"].head_local).length)


def apply_pose(rig, pose: str, eye_rest=None) -> dict:
    """Pose the game_engine rig. The trunk (pelvis + spine) stays one rigid piece so the pack rides on it unchanged;
    only the pelvis leans. Returns {"slope_deg", "ground_z" (rig space, under the feet), "props": {...}}."""
    bpy = _bpy()
    from mathutils import Matrix, Vector  # noqa: PLC0415
    pb = rig.pose.bones
    for b in pb:
        b.rotation_mode = "QUATERNION"
        b.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    info = {"slope_deg": 0.0, "props": {}, "lean_deg": 0.0}
    ankle_h = min(pb["foot_l"].head.z, pb["foot_r"].head.z)        # ankle joint above the sole plane (rest)
    hip = {s: pb[f"thigh_{s}"].head.copy() for s in "lr"}
    foot_rest = {s: (pb[f"foot_{s}"].tail - pb[f"foot_{s}"].head).normalized() for s in "lr"}
    sgn = {"l": -1.0, "r": 1.0}                                     # R component of each side

    def lean_pelvis(deg, drop=0.0, fwd=0.0, yaw=0.0):
        """Lean the whole trunk forward about the hip axis, lower / advance the pelvis."""
        p = pb["pelvis"]
        piv = 0.5 * (hip["l"] + hip["r"])
        Rm = (Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(deg), 4, Vector((1, 0, 0))))
        M = Matrix.Translation(piv + _fru(fwd, 0, -drop)) @ Rm @ Matrix.Translation(-piv) @ p.matrix
        p.matrix = M
        bpy.context.view_layer.update()
        info["lean_deg"] = deg

    def leg(s, f, r, u, knee_out=0.05, foot_pitch=0.0, foot_yaw=0.0):
        """Ankle joint to (f, r, u) relative to the rest hip position projected on the floor (u above z = 0)."""
        tgt = Vector((hip[s].x, hip[s].y, 0.0)) + _fru(f, r, u)
        err = _two_bone(rig, f"thigh_{s}", f"calf_{s}", tgt, _fru(1.0, sgn[s] * knee_out, 0.15))
        d = (Matrix.Rotation(math.radians(foot_yaw * -sgn[s]), 3, "Z")
             @ Matrix.Rotation(math.radians(foot_pitch), 3, "X") @ foot_rest[s])
        _aim_bone(rig, f"foot_{s}", d)
        return err

    def arm(s, upper, lower, hand=None, twist_u=0.0, twist_l=0.0):
        _aim_bone(rig, f"upperarm_{s}", upper, twist_u)
        _aim_bone(rig, f"lowerarm_{s}", lower, twist_l)
        _aim_bone(rig, f"hand_{s}", hand if hand is not None else lower)

    if pose == "front":
        lean_pelvis(3.0)
        leg("l", 0.05, -0.04, ankle_h, foot_yaw=10)
        leg("r", -0.03, 0.04, ankle_h, foot_yaw=12)
        arm("l", _fru(0.10, -0.34, -1), _fru(1.0, -0.10, -0.12))     # both poles planted ahead, elbows clear of the belt
        arm("r", _fru(0.06, 0.36, -1), _fru(1.0, 0.16, -0.22))
        _curl_fingers(rig, "l", 0.92, thumb=0.7)
        _curl_fingers(rig, "r", 0.92, thumb=0.7)
        _aim_bone(rig, "neck_01", _fru(0.10, 0.0, 1))
        _aim_bone(rig, "head", _fru(0.03, -0.12, 1), twist_deg=12.0)
        info["props"]["poles"] = True
    elif pose in ("stand", "side"):
        lean_pelvis(4.0)                                             # a loaded pack is carried with a slight lean
        leg("l", 0.03, -0.035, ankle_h, foot_yaw=8)
        leg("r", -0.02, 0.035, ankle_h, foot_yaw=10)
        arm("l", _fru(0.10, -0.10, -1), _fru(0.32, -0.02, -1), _fru(0.30, 0.0, -1))
        arm("r", _fru(0.02, 0.10, -1), _fru(0.22, 0.02, -1), _fru(0.25, 0.0, -1))
        _curl_fingers(rig, "l", 0.35)
        _curl_fingers(rig, "r", 0.42)
        _aim_bone(rig, "neck_01", _fru(0.10, 0.0, 1))
        hd = {"stand": _fru(0.02, 0.30, 1), "side": _fru(0.04, 0.0, 1)}[pose]
        _aim_bone(rig, "head", hd, twist_deg={"stand": -32.0, "side": 0.0}[pose])
    elif pose == "walk":
        a = 14.0                                                     # uphill slope, deg
        t = math.tan(math.radians(a))
        info["slope_deg"] = a
        lean_pelvis(13.0, drop=0.075, fwd=0.02)
        # ground rises toward F: height(f) = t * f, measured from the point under the rest hips
        fl, fr = 0.40, -0.30
        leg("l", fl, -0.02, t * fl + ankle_h + 0.004, foot_pitch=-a, foot_yaw=4)
        leg("r", fr, 0.03, t * fr + ankle_h + 0.055, foot_pitch=-a + 24.0, foot_yaw=6)   # rear heel lifting
        arm("r", _fru(0.42, 0.16, -1), _fru(1.0, -0.02, 0.10))       # right pole planted ahead (opposite the lead leg)
        arm("l", _fru(-0.22, -0.16, -1), _fru(0.75, 0.04, -0.55))    # left pole trailing
        _curl_fingers(rig, "l", 0.92, thumb=0.7)
        _curl_fingers(rig, "r", 0.92, thumb=0.7)
        _aim_bone(rig, "neck_01", _fru(0.02, 0.0, 1))
        _aim_bone(rig, "head", _fru(0.0, 0.0, 1))
        info["props"]["poles"] = True
    elif pose == "kneel":
        thigh = (rig.data.bones["calf_r"].head_local - rig.data.bones["thigh_r"].head_local).length
        drop = hip["r"].z - (thigh + 0.085)                           # right knee on the ground
        lean_pelvis(7.0, drop=drop, fwd=0.0)
        hz_ = pb["thigh_r"].head.z
        _ = hz_
        # right: thigh straight down, shin back along the ground, toes tucked
        tgt = Vector((hip["r"].x, hip["r"].y, 0.0)) + _fru(-0.43, 0.02, 0.075)
        _two_bone(rig, "thigh_r", "calf_r", tgt, _fru(0.6, 0.05, -1.0))
        _aim_bone(rig, "foot_r", _fru(-1.0, 0.0, -0.42))              # instep on the ground, toes back
        # left: thigh forward, shin vertical, foot flat
        tgt = Vector((hip["l"].x, hip["l"].y, 0.0)) + _fru(0.36, -0.10, ankle_h)
        _two_bone(rig, "thigh_l", "calf_l", tgt, _fru(1.0, -0.25, 0.6))
        _aim_bone(rig, "foot_l", Matrix.Rotation(math.radians(10.0), 3, "Z") @ foot_rest["l"])
        # glassing: both hands at the binoculars in front of the eyes
        _aim_bone(rig, "neck_01", _fru(0.16, 0.0, 1))
        head_rest = pb["head"].bone.matrix_local.copy()
        _aim_bone(rig, "head", _fru(0.0, 0.0, 1))
        Hd = pb["head"].matrix @ head_rest.inverted()                # head: rest -> posed
        fwd = (Hd.to_3x3() @ _fru(1, 0, 0)).normalized()
        info["head_fwd"] = tuple(fwd)
        if eye_rest is not None:                                     # wrists beside the binocular barrels
            eye = Hd @ Vector(eye_rest)
            lat = (Hd.to_3x3() @ _fru(0, 1, 0)).normalized()
            for s in "lr":
                wrist = eye + fwd * 0.085 + lat * (sgn[s] * 0.085) + Vector((0, 0, -0.075))
                _two_bone(rig, f"upperarm_{s}", f"lowerarm_{s}", wrist, _fru(0.2, sgn[s] * 0.7, -1.0))
                _aim_bone(rig, f"hand_{s}", _fru(0.25, -sgn[s] * 0.75, 0.9))
        _curl_fingers(rig, "l", 0.55, thumb=0.1)
        _curl_fingers(rig, "r", 0.55, thumb=0.1)
        info["props"]["binoculars"] = True
    else:
        raise ValueError(f"pose {pose!r}: choose from {POSES}")
    bpy.context.view_layer.update()
    return info


def _bake(ob, keep_subdiv=False, levels=None):
    """Replace the object's mesh by its evaluated (posed, masked, optionally subdivided) mesh and drop the modifiers."""
    bpy = _bpy()
    sub = [(m.levels, m.render_levels) for m in ob.modifiers if m.type == "SUBSURF"]
    for m in ob.modifiers:
        if m.type == "SUBSURF":
            m.show_viewport = not keep_subdiv
            if levels is not None:
                m.levels = levels
        else:
            m.show_viewport = True
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = ob.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world = mw
    if keep_subdiv and sub:
        m = ob.modifiers.new("subdiv", "SUBSURF")
        m.levels, m.render_levels = sub[0]
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _co(ob):
    V = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", V)
    return V.reshape(-1, 3)


def _set_co(ob, V):
    ob.data.vertices.foreach_set("co", np.ascontiguousarray(V, dtype=np.float64).ravel())
    ob.data.update()


def _xf(M, V):
    A = np.array(M)
    return V @ A[:3, :3].T + A[:3, 3]


# ------------------------------------------------------------------------------------------- pack on the body
HARNESS_REF = ("shoulder_straps", "yoke_pad")
HARNESS_FOLLOW = ("harness_webbing", "harness_hardware", "load_lifters", "imp2_hose", "imp2_valve", "imp6_")
BELT_REF = ("beltB_shell", "beltB_face", "beltB_binding", "beltB_quilt")
BELT_PREFIX = "beltB_"
SINK_STRAP, SINK_BELT = 0.005, 0.007       # m the pads press into the clothed surface. ASSUMPTION (visual): no
#                                            pressure / compliance model; settle with a pressure-mat fit on the mule.


def load_pack(glb: Path, torso_setting: float, state: dict | None = None) -> dict:
    """Import the pack GLB (Cycles materials from cycles_render), keep the parts visible for this torso setting and
    state, and keep the display form as a hidden reference. Returns {"parts": {name: object}, "form": object}."""
    bpy = _bpy()
    from . import cycles_render as CR  # noqa: PLC0415
    man = CR.load_manifest(glb)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    new = [o for o in bpy.data.objects if o not in before]
    CR.build_materials(CR.owner_camo_png(REPO / "outputs" / "cycles_work"))
    st = {"mannequin": False, "lid": True, **(state or {}), "torso": torso_setting}
    parts, form = {}, None
    for o in new:
        if o.type != "MESH":
            continue
        if o.name == f"mannequin@t{torso_setting:g}":
            form = o
            o.hide_render = True
            continue
        if CR.visible_for(man.get(o.name), o.name, st):
            parts[o.name] = o
    for o in new:
        if o is not form and o.name not in parts:
            bpy.data.objects.remove(o, do_unlink=True)
    for o in list(parts.values()) + [form]:                 # bake the glTF node transforms: mesh data in pack space
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world.identity()
        for p in o.data.polygons:
            p.use_smooth = True
    return {"parts": parts, "form": form, "manifest": man}


def _profile_min_y(V, z_lo, z_hi, half_w, dz=0.02):
    """Most aft point (min y; the wearer faces +Y) per height bin over |x| < half_w: the back profile."""
    zs = np.arange(z_lo, z_hi, dz)
    out = np.full(len(zs), np.nan)
    m = np.abs(V[:, 0]) < half_w
    P = V[m]
    k = np.floor((P[:, 2] - z_lo) / dz).astype(int)
    ok = (k >= 0) & (k < len(zs))
    for i in np.unique(k[ok]):
        out[i] = P[ok & (k == i), 1].min()
    return zs + dz / 2, out


def _nanfill(G, iters=200):
    """Fill NaN cells by repeated neighbour averaging (numpy only: the bpy venv has no scipy)."""
    G = G.copy()
    known = ~np.isnan(G)
    if not known.any():
        return np.zeros_like(G)
    G[~known] = 0.0
    w = known.astype(float)
    for _ in range(iters):
        if w.min() > 0:
            break
        s = np.zeros_like(G)
        c = np.zeros_like(G)
        for ax in (0, 1):
            for sh in (-1, 1):
                s += np.roll(G * w, sh, axis=ax)
                c += np.roll(w, sh, axis=ax)
        new = (w == 0) & (c > 0)
        G[new] = (s[new] / c[new])
        w[new] = 1.0
    return G


def _blur(G, n=2):
    for _ in range(n):
        G = (G + np.roll(G, 1, 0) + np.roll(G, -1, 0) + np.roll(G, 1, 1) + np.roll(G, -1, 1)) / 5.0
    return G


class _Wrap:
    """Radial re-fit of a pad system onto the clothed body, in pack space (m, wearer faces +Y).

    Each point is described about a centre line c(z) = (0, yc, min(z, z_top)): below ``z_top`` the direction is
    horizontal (cylindrical), above it the direction fans out from (0, yc, z_top) (spherical), so the rays leave
    the top of the shoulders roughly normal to them. On a (azimuth, u) grid the class ray-casts the inner face of the
    reference pads and the clothed body, and moves every point along its ray by
    ``body radius - sink - pad inner radius``: the pad keeps its thickness and its place on the body (height, angle)
    and ends up pressed ``sink`` into the cloth."""

    def __init__(self, yc, z_top, z_lo, z_hi, daz=1.0, du=0.004, r0=0.16):
        self.yc, self.z_top, self.r0 = yc, z_top, r0
        self.az = np.radians(np.arange(-180.0, 180.0, daz))
        u_hi = z_top + (math.pi / 2) * r0 if z_hi > z_top else z_hi
        self.u = np.arange(z_lo, u_hi + du, du)

    def to_grid(self, P):
        """(azimuth, u, r, unit direction, centre) of points P."""
        zc = np.minimum(P[:, 2], self.z_top)
        d = P - np.c_[np.zeros(len(P)), np.full(len(P), self.yc), zc]
        r = np.linalg.norm(d, axis=1)
        dirs = d / np.maximum(r, 1e-9)[:, None]
        az = np.arctan2(d[:, 0], d[:, 1])
        el = np.arcsin(np.clip(dirs[:, 2], -1, 1))
        u = np.where(P[:, 2] < self.z_top, P[:, 2], self.z_top + el * self.r0)
        return az, u, r, dirs

    def rays(self):
        A, U = np.meshgrid(self.az, self.u, indexing="ij")
        el = np.clip((U - self.z_top) / self.r0, 0.0, math.pi / 2 - 1e-3)
        zc = np.minimum(U, self.z_top)
        C = np.stack([np.zeros_like(A), np.full_like(A, self.yc), zc], -1)
        D = np.stack([np.sin(A) * np.cos(el), np.cos(A) * np.cos(el), np.sin(el)], -1)
        return C, D

    def cast(self, bvh, first=True, rmax=0.6, need=None, layers=0.0):
        """Radius of the first (or last) hit of every grid ray on a BVH; NaN where there is none."""
        from mathutils import Vector  # noqa: PLC0415
        C, D = self.rays()
        R = np.full(C.shape[:2], np.nan)
        idx = np.argwhere(need) if need is not None else np.argwhere(np.ones(C.shape[:2], bool))
        for i, j in idx:
            o, d = Vector(C[i, j]), Vector(D[i, j])
            if first:
                hit = bvh.ray_cast(o, d, rmax)
                if hit[0] is not None:
                    r = hit[3]
                    while layers:                     # an outer garment layer just beyond (shirt hem over trousers)
                        h2 = bvh.ray_cast(o + d * (r + 0.0008), d, layers)
                        if h2[0] is None:
                            break
                        r += 0.0008 + h2[3]
                    R[i, j] = r
            else:                                    # outermost surface: cast back in from outside
                hit = bvh.ray_cast(o + d * rmax, -d, rmax)
                if hit[0] is not None:
                    R[i, j] = rmax - hit[3]
        return R

    def sample(self, G, az, u):
        """Bilinear sample of grid G at (az, u); azimuth wraps."""
        na, nu = G.shape
        fa = (az - self.az[0]) / (self.az[1] - self.az[0])
        fu = np.clip((u - self.u[0]) / (self.u[1] - self.u[0]), 0, nu - 1.001)
        i0 = np.floor(fa).astype(int)
        j0 = np.floor(fu).astype(int)
        ta, tu = fa - i0, fu - j0
        i0 %= na
        i1 = (i0 + 1) % na
        j1 = np.minimum(j0 + 1, nu - 1)
        return ((1 - ta) * (1 - tu) * G[i0, j0] + ta * (1 - tu) * G[i1, j0]
                + (1 - ta) * tu * G[i0, j1] + ta * tu * G[i1, j1])


def _bvh(objs_V_F):
    from mathutils.bvhtree import BVHTree  # noqa: PLC0415
    V, F, off = [], [], 0
    for v, f in objs_V_F:
        V.append(v)
        F += [tuple(int(i) + off for i in p) for p in f]
        off += len(v)
    V = np.vstack(V)
    return BVHTree.FromPolygons([tuple(p) for p in V], F, all_triangles=False)


def _polys(ob):
    return [tuple(p.vertices) for p in ob.data.polygons]


def _refine(ob, max_edge=0.012, passes=4):
    """Split edges longer than ``max_edge`` (m) so a mesh can follow a curved surface when its vertices are moved."""
    import bmesh  # noqa: PLC0415
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for _ in range(passes):
        long = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def fit_pack(pack: dict, cloth_objs: list, M_pack, torso_setting: float, z_crest: float, z_c7: float,
             verbose=False) -> dict:
    """Fit the harness and hipbelt to the clothed body and press them into the cloth.

    ``pack``: load_pack() result, mesh data in pack space. ``cloth_objs``: baked world-space figure meshes the pads
    bear on (suit; body for the neck). ``M_pack``: pack space -> world. Works in pack space; edits the pad meshes and
    dents the cloth meshes in place. Returns the fit numbers."""
    from mathutils import Matrix  # noqa: PLC0415
    Mi = np.array(Matrix(M_pack).inverted())
    Mf = np.array(Matrix(M_pack))
    parts = pack["parts"]
    cloth = [(o, _xf(Mi @ np.array(o.matrix_world), _co(o))) for o in cloth_objs]
    body_bvh = _bvh([(v, _polys(o)) for o, v in cloth])
    allc = np.vstack([v for _, v in cloth])
    trunk = allc[(np.abs(allc[:, 0]) < 0.12)]
    yc_of = lambda z0, z1: float(np.mean([trunk[(trunk[:, 2] > z0) & (trunk[:, 2] < z1), 1].min(),       # noqa: E731
                                           trunk[(trunk[:, 2] > z0) & (trunk[:, 2] < z1), 1].max()]))
    out = {}
    tag = f"@t{torso_setting:g}"

    def run(ref_names, follow, yc, z_top, z_lo, z_hi, sink, back_fixed, close_front=False):
        refs = [o for n, o in parts.items() if n.split("@")[0].startswith(ref_names)]
        fol = [o for n, o in parts.items() if follow(n) and o not in refs]
        W = _Wrap(yc, z_top, z_lo, z_hi)
        for o in refs + fol:                                  # long straight runs must be able to bend round the body
            _refine(o, 0.012)
        solo = ("load_lifters", "imp2_hose", "corrie_top_guys")       # run free of the body: never pulled onto it
        union = refs + [o for o in fol if not o.name.startswith(solo)]
        r_pad = W.cast(_bvh([(_co(o), _polys(o)) for o in refs]), first=True)
        r_in = W.cast(_bvh([(_co(o), _polys(o)) for o in union]), first=True)
        foot = ~np.isnan(r_in)
        pad = ~np.isnan(r_pad)
        need = foot.copy()
        for _ in range(10):                                   # body radius on the footprint and a margin around it
            need = need | np.roll(need, 1, 0) | np.roll(need, -1, 0) | np.roll(need, 1, 1) | np.roll(need, -1, 1)
        r_body = W.cast(body_bvh, first=True, need=need, layers=0.022)
        # a ray that leaves through an armhole or misses: use the neighbours
        med = _blur(_nanfill(r_body), 2)
        bad = np.isnan(r_body) | (np.abs(r_body - med) > 0.03)
        r_body = np.where(bad, np.nan, r_body)
        pad_soft = np.clip(_blur(pad.astype(float), 2), 0.0, 1.0)
        # pads press ``sink`` into the cloth; webbing and hardware beyond the pads lie on it
        delta = np.where(foot, r_body - sink * pad_soft + 0.0012 * (1.0 - pad_soft) - r_in, np.nan)
        delta = np.where(np.abs(delta) > 0.12, np.nan, delta)
        D = _blur(_nanfill(delta), 3)
        D = np.where(foot & ~np.isnan(delta), 0.5 * D + 0.5 * np.nan_to_num(delta, nan=0.0), D)
        moved = []
        for o in refs + fol:
            P = _co(o)
            az, u, r, dirs = W.to_grid(P)
            d = W.sample(D, az, u)
            w = np.ones(len(P))
            if o in fol and back_fixed is not None:           # webbing that runs back to the frame stays put there
                w = np.clip((P[:, 1] - (back_fixed - 0.03)) / 0.05, 0.0, 1.0)
                w = w * w * (3 - 2 * w)
            _set_co(o, P + dirs * (d * w)[:, None])
            moved.append(float(np.abs(d * w).max()))
        # inner face of the fitted pads, then press the cloth under it
        r_in2 = W.cast(_bvh([(_co(o), _polys(o)) for o in union]), first=True, need=need)
        depth = np.where(~np.isnan(r_in2) & ~np.isnan(r_body), np.maximum(r_body - (r_in2 - 0.0012), 0.0), 0.0)
        soft = np.maximum(depth, _blur(depth, 3))
        for o, Vp in cloth:
            az, u, r, dirs = W.to_grid(Vp)
            rb = W.sample(_nanfill(r_body), az, u)
            dd = W.sample(soft, az, u)
            sel = (dd > 1e-5) & (np.abs(r - rb) < 0.02) & (u > W.u[0]) & (u < W.u[-1])
            if sel.any():
                Vp[sel] -= dirs[sel] * dd[sel, None]
        if close_front:
            # The viz3d belt B is drawn open at the front (buckle on one tip, D-ring on the other, no webbing between).
            # Close it with a 38 mm webbing band on the cloth between the wing tips, at the buckle height.
            j = int(np.argmin(np.abs(W.u - z_crest)))
            az_deg = np.degrees(W.az)
            padded = pad[:, max(j - 3, 0):j + 4].any(axis=1)
            free = np.where(~padded & (np.abs(az_deg) < 120))[0]
            if len(free) > 4:
                a0, a1 = az_deg[free].min() - 6.0, az_deg[free].max() + 6.0
                azs = np.radians(np.arange(a0, a1 + 0.5, 2.0))
                rb = _blur(_nanfill(r_body), 1)
                hw = parts.get("beltB_hardware")
                zb = z_crest
                if hw is not None:
                    Vh = _co(hw)
                    fr = Vh[Vh[:, 1] > np.percentile(Vh[:, 1], 80)]
                    zb = float(fr[:, 2].mean())
                Vr, Fr = [], []
                for a in azs:
                    for dz in (-0.019, 0.019):
                        for lift in (0.0006, 0.0026):
                            r = float(W.sample(rb, np.array([a]), np.array([zb + dz]))[0]) + lift
                            Vr.append((r * math.sin(a), W.yc + r * math.cos(a), zb + dz))
                for i in range(len(azs) - 1):
                    b0, b1 = 4 * i, 4 * (i + 1)
                    Fr += [(b0 + 1, b0 + 3, b1 + 3, b1 + 1), (b0, b1, b1 + 2, b0 + 2), (b0, b0 + 1, b1 + 1, b1),
                           (b0 + 2, b1 + 2, b1 + 3, b0 + 3)]
                wb = parts.get("beltB_webbing")
                band = _mesh_obj("beltB_front_webbing", np.array(Vr), Fr,
                                 wb.data.materials[0] if wb is not None and wb.data.materials else None)
                parts["beltB_front_webbing"] = band
        gap = r_in2 - r_body                                  # > 0: daylight between pad and cloth before the press
        if os.environ.get("WEARER_DBG"):
            np.savez(os.environ["WEARER_DBG"] + f"_{ref_names[0]}.npz", r_in=r_in, r_pad=r_pad, r_body=r_body, D=D,
                     delta=delta, r_in2=r_in2, az=W.az, u=W.u)
        return {"cells": int(foot.sum()), "max_move_mm": round(1000 * max(moved), 1),
                "press_mm_mean": round(1000 * float(depth[depth > 0].mean()) if (depth > 0).any() else 0.0, 1),
                "gap_mm_max_after": round(1000 * float(np.nanmax(np.where(foot, gap, np.nan))), 1),
                "contact_fraction": round(float(((gap < 0.0005) & foot).sum() / max(foot.sum(), 1)), 3)}

    z_arm = z_c7 - 0.19
    yb = float(np.nanmin(trunk[(trunk[:, 2] > z_crest + 0.1) & (trunk[:, 2] < z_c7 - 0.1), 1]))
    out["harness"] = run(HARNESS_REF, lambda n: n.split("@")[0].startswith(HARNESS_FOLLOW) and n.endswith(tag),
                         yc_of(z_arm - 0.05, z_arm + 0.05), z_arm, z_crest + 0.02, z_c7 + 0.2, SINK_STRAP, yb)
    out["belt"] = run(BELT_REF, lambda n: n.startswith(BELT_PREFIX), yc_of(z_crest - 0.06, z_crest + 0.06),
                      z_crest + 0.4, z_crest - 0.16, z_crest + 0.16, SINK_BELT, None, close_front=True)
    for o, Vp in cloth:
        _set_co(o, _xf(np.array(Matrix(o.matrix_world).inverted()) @ Mf, Vp))
    if verbose:
        print("fit", out, flush=True)
    return out


# ------------------------------------------------------------------------------------------------ cap and props
def _mesh_obj(name, V, F, mat=None, smooth=True):
    bpy = _bpy()
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(int(i) for i in f) for f in F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def _plain_material(name, base, rough=0.5, metallic=0.0, coat=0.0, transmission=0.0):
    bpy = _bpy()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base[:3], 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    for k, v in (("Coat Weight", coat), ("Transmission Weight", transmission)):
        if k in b.inputs:
            b.inputs[k].default_value = v
    return mat


def _bind_to_bone(ob, rig, bone):
    """Rigid skinning to one bone (so the object is posed and baked with the figure)."""
    g = ob.vertex_groups.new(name=bone)
    g.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
    m = ob.modifiers.new("Armature", "ARMATURE")
    m.object = rig
    ob.parent = rig


def add_cap(fig: dict, colour) -> object:
    """A plain six-panel-style field cap built on the figure's own skull (rest pose): crown = the scalp above a
    tilted rim plane, offset 4 mm and thickened; curved brim from the front of the rim. Original, no logo."""
    import bmesh  # noqa: PLC0415
    bpy = _bpy()
    body, rig = fig["body"], fig["rig"]
    V = _body_coords(body)
    eyes = next(o for o in fig["extras"] if o.name == "wearer_eyes")
    ze = float(_co(eyes)[:, 2].mean())
    zt = float(V[V_VERTEX, 2])
    hd = body.vertex_groups["head"].index
    head = np.array([any(g.group == hd and g.weight > 0.5 for g in v.groups) for v in body.data.vertices])
    head &= _group_mask(body, "body")
    H = V[head]
    yf, yb = H[:, 1].min(), H[H[:, 2] > ze][:, 1].max()             # figure faces -Y: front = min y
    zf, zb = ze + 0.40 * (zt - ze), ze + 0.02 * (zt - ze)
    slope = (zb - zf) / (yb - yf)
    above = head & (V[:, 2] > zf + slope * (V[:, 1] - yf))
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    for i, v in enumerate(bm.verts):
        v.co = V[i]
    drop = [f for f in bm.faces if not all(above[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.normal_update()
    cx, cy = 0.0, 0.5 * (yf + yb)
    for v in bm.verts:                                              # stand the cloth 4 mm off the scalp, 9 at the rim
        k = 1.0 - min(max((v.co.z - (zf + slope * (v.co.y - yf))) / 0.05, 0.0), 1.0)
        v.co += v.normal * (0.004 + 0.003 * k)
    bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    rim = [v for v in bm.verts if v.is_boundary]
    for v in rim:                                                   # a clean, planar rim
        v.co.z = zf + slope * (v.co.y - yf) - 0.004
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5, use_axis_x=True,
                              use_axis_y=True, use_axis_z=True)
    me = bpy.data.meshes.new("wearer_cap")
    rim_pts = np.array([v.co[:] for v in rim])
    bm.to_mesh(me)
    bm.free()
    mat = _cloth_material("wearer_cap", colour, weave_mm=0.9, bump=0.3, rough=0.82, sheen=0.4)
    cap = bpy.data.objects.new("wearer_cap", me)
    bpy.context.scene.collection.objects.link(cap)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    sol = cap.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.0022
    sol.offset = 1.0
    sub = cap.modifiers.new("subdiv", "SUBSURF")
    sub.levels = sub.render_levels = 1
    # brim: inner edge on the rim's front arc, 72 mm long at the centre, edges swept back, slight droop
    ang = np.arctan2(rim_pts[:, 0] - cx, -(rim_pts[:, 1] - cy))     # 0 = straight ahead
    front = np.abs(ang) < math.radians(62)
    order = np.argsort(ang[front])
    A, P = ang[front][order], rim_pts[front][order]
    phis = np.linspace(-math.radians(58), math.radians(58), 33)
    inner = np.stack([np.interp(phis, A, P[:, k]) for k in range(3)], 1)
    nv = 9
    rows = []
    for j in range(nv):
        t = j / (nv - 1)
        c = np.cos(phis / math.radians(58) * math.pi / 2) ** 0.55
        L = 0.074 * c * t
        row = inner + np.c_[np.sin(phis) * L * 0.25, -L, -0.16 * L - 0.010 * (1 - c) * t]
        row[:, 2] += 0.004 * np.sin(math.pi * t) * c                 # a little crown along the bill
        rows.append(row)
    G = np.array(rows)
    Vb = G.reshape(-1, 3)
    nu = len(phis)
    Fb = [(j * nu + i, j * nu + i + 1, (j + 1) * nu + i + 1, (j + 1) * nu + i) for j in range(nv - 1)
          for i in range(nu - 1)]
    brim = _mesh_obj("wearer_cap_brim", Vb, Fb, mat)
    s2 = brim.modifiers.new("thick", "SOLIDIFY")
    s2.thickness = 0.0035
    s2.offset = 0.0
    sb = brim.modifiers.new("subdiv", "SUBSURF")
    sb.levels = sb.render_levels = 2
    top = V[V_VERTEX] + np.array([0, 0.012, 0.004])
    for o in (cap, brim):
        _bind_to_bone(o, rig, "head")
        o.modifiers.move(len(o.modifiers) - 1, 0)
    _ = top
    return [cap, brim]


def _tube(name, a, b, r, mat, n=16, r2=None):
    """Capped cylinder / cone from a to b (world m)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ax = b - a
    ln = np.linalg.norm(ax)
    ax /= ln
    t = np.cross(ax, [0, 0, 1.0])
    if np.linalg.norm(t) < 1e-6:
        t = np.array([1.0, 0, 0])
    t /= np.linalg.norm(t)
    s = np.cross(ax, t)
    r2 = r if r2 is None else r2
    V, F = [], []
    for k, (p, rr) in enumerate(((a, r), (b, r2))):
        for i in range(n):
            ph = 2 * math.pi * i / n
            V.append(p + rr * (math.cos(ph) * t + math.sin(ph) * s))
    V += [a, b]
    for i in range(n):
        j = (i + 1) % n
        F += [(i, j, n + j, n + i), (2 * n, j, i), (2 * n + 1, n + i, n + j)]
    return _mesh_obj(name, np.array(V), F, mat)


def _pack_measures(parts: dict, tag: str) -> dict:
    """Fit numbers read off the fitted pack meshes (pack space, m): belt mid-height at the sides and lifter angle."""
    out = {}
    sh = parts.get("beltB_shell")
    if sh is not None:
        V = _co(sh)
        side = V[np.abs(V[:, 0]) > 0.8 * np.abs(V[:, 0]).max()]
        back = V[np.abs(V[:, 0]) < 0.05]
        out["belt_mid_z_side_mm"] = round(500.0 * float(side[:, 2].min() + side[:, 2].max()), 1)
        out["belt_mid_z_back_mm"] = round(500.0 * float(back[:, 2].min() + back[:, 2].max()), 1)
        out["belt_top_z_back_mm"] = round(1000.0 * float(back[:, 2].max()), 1)
    ll = parts.get("load_lifters" + tag)
    if ll is not None:
        V = _co(ll)
        angs = []
        for sx in (-1, 1):
            P = V[V[:, 0] * sx > 0]
            if len(P) < 8:
                continue
            lo_, hi_ = np.percentile(P[:, 1], [8, 92])      # aft end (frame lug) and forward end (strap), by y
            a, b = P[P[:, 1] <= lo_].mean(0), P[P[:, 1] >= hi_].mean(0)
            angs.append(abs(math.degrees(math.atan2(a[2] - b[2], math.hypot(a[0] - b[0], a[1] - b[1])))))
        out["lifter_angle_deg"] = [round(a, 1) for a in angs]
    return out


def build_wearer(torso_in: float | None = None, pose: str = "stand", outfit: str = "midlayer", glb=None,
                 pack_parts: dict | None = None, form=None, stature_mm: float | None = None, sex: str | None = None,
                 with_pack: bool = True, verbose: bool = False) -> Wearer:
    """Build the posed, dressed hunter in the current Blender scene and put the pack on him.

    torso_in    None = the default hunter (1829 mm man; the torso setting follows from ANSUR II). 15 / 23 = variants.
    pose        "stand" (hero), "walk" (uphill, trekking poles), "side", "kneel" (glassing), "front".
    outfit      key of OUTFITS.
    glb         pack GLB to import (default outputs/pack3d_wearer/corrie_b2_wearer.glb, see build_pack_glb), or
    pack_parts  {name: object} of pack meshes already in the scene, mesh data in pack space (FCS x, -y, z metres,
                identity object transforms), with ``form`` = the display-form mesh they were built on (optional).
    Result: a ``Wearer``; ``fit["pack_on_torso"]`` is the 4x4 that carries pack space onto the posed torso (already
    applied to ``pack_parts`` unless they are parented, see ``studio_wearer``)."""
    bpy = _bpy()
    from mathutils import Matrix  # noqa: PLC0415
    spec = figure_spec(torso_in, stature_mm, sex)
    pk = None
    if with_pack:          # first: cycles_render.build_materials repaints every material that exists when it runs
        if pack_parts is None:
            pk = load_pack(Path(glb or PACK_GLB), spec["torso_setting_in"])
        else:
            pk = {"parts": dict(pack_parts), "form": form}
    fig = build_figure(spec, outfit, verbose=verbose)
    rig, body, suit, boots = fig["rig"], fig["body"], fig["clothes"]["suit"], fig["clothes"]["boots"]
    cap = add_cap(fig, _hex(OUTFITS[outfit]["cap"]))
    Vr = _body_coords(body)
    zr_crest = float(Vr[V_NAVEL, 2]) + CREST_ABOVE_NAVEL / 1000.0
    zr_c7 = float(0.5 * (Vr[V_C7[0], 2] + Vr[V_C7[1], 2]))
    rest_pelvis = rig.pose.bones["pelvis"].matrix.copy()
    eyes_ob = next(o for o in fig["extras"] if o.name == "wearer_eyes")
    info = apply_pose(rig, pose, eye_rest=tuple(_co(eyes_ob).mean(0)))
    P = rig.pose.bones["pelvis"].matrix @ rest_pelvis.inverted()           # trunk: rest -> posed (rig space)
    figure = [body, suit, boots] + fig["extras"] + cap
    _bake(body, levels=1)
    _bake(suit, levels=2)
    _bake(boots, levels=1)
    for o in fig["extras"] + cap:
        _bake(o, levels=1)
    w = Wearer(figure=figure, rig=rig, pose=pose, outfit=outfit)
    w.spec = {**spec, "tuned": fig["tuned"]}
    setting = spec["torso_setting_in"]
    tag = f"@t{setting:g}"
    A = Matrix.Identity(4)
    if with_pack:
        # trunk surface in the rest frame (posed cloth carried back by P^-1): the back profile for the alignment
        Pi = np.array(P.inverted())
        Vs = _xf(Pi, _co(suit))
        tz = zr_crest - ILIAC_CREST_Z / 1000.0
        if pk["form"] is not None:
            Vf = _co(pk["form"])
            zs, yf = _profile_min_y(Vf, 0.08, 0.12 + spec["torso_mm"] / 1000.0 - 0.09, 0.09)
        else:                                                    # no form: the viz3d mannequin back plane
            zs = np.arange(0.08, 0.5, 0.01)
            yf = np.full(len(zs), 0.065)
        Vh = np.c_[-Vs[:, 0], -Vs[:, 1], Vs[:, 2] - tz]           # rest figure seen in pack axes, before ty
        _, yh = _profile_min_y(Vh, zs[0] - 0.005, zs[-1] + 0.005, 0.09)
        n = min(len(yf), len(yh))
        ty = float(np.nanmax(yf[:n] - yh[:n])) - 0.004            # touch at the tightest height, 4 mm compression
        if verbose:
            print("back profile z, form y, figure y (mm):",
                  [(round(1000 * a), round(1000 * b), round(1000 * c)) for a, b, c in zip(zs[:n], yf[:n], yh[:n])])
        A = Matrix.Translation((0.0, ty, tz)) @ Matrix.Rotation(math.pi, 4, "Z")   # pack space -> rig rest space
        M = P @ A
        fit = fit_pack(pk, [suit, body], M, setting, ILIAC_CREST_Z / 1000.0,
                       ILIAC_CREST_Z / 1000.0 + spec["torso_mm"] / 1000.0, verbose=verbose)
        fit.update(_pack_measures(pk["parts"], tag))
        # head clearance: the smallest distance from the head to any pack part that is not harness
        Mi = np.array(M.inverted())
        Vb = _xf(Mi, _co(body))
        zc7p = ILIAC_CREST_Z / 1000.0 + spec["torso_mm"] / 1000.0
        head = Vb[Vb[:, 2] > zc7p + 0.06]
        gap = 9.0
        for nme, o in pk["parts"].items():
            if nme.split("@")[0].startswith(HARNESS_REF + HARNESS_FOLLOW + (BELT_PREFIX,)):
                continue
            Vp = _co(o)
            Vp = Vp[Vp[:, 2] > zc7p]
            if not len(Vp):
                continue
            hs = head[:: max(1, len(head) // 600)]
            ps = Vp[:: max(1, len(Vp) // 4000)]
            d = np.sqrt(((hs[:, None, :] - ps[None, :, :]) ** 2).sum(-1)).min()
            gap = min(gap, float(d))
        fit["head_gap_mm"] = round(1000.0 * gap, 1)
        fit["torso_figure_mm"] = round(spec["torso_mm"], 1)
        fit["torso_setting_in"] = setting
        fit["torso_setting_mm"] = round(setting * IN, 1)
        fit["iliac_crest_z_design_mm"] = ILIAC_CREST_Z
        fit["back_offset_ty_mm"] = round(1000 * ty, 1)
        w.fit = fit
        w.pack = list(pk["parts"].values())
        if pk["form"] is not None and pack_parts is None:
            bpy.data.objects.remove(pk["form"], do_unlink=True)
    # world: the wearer faces +Y (the pack's own axes when he stands erect), ground under the soles at z = 0
    Vb_ = _co(boots)
    slope = math.radians(info["slope_deg"])
    # ground plane in rig space: z = z0 + tan(slope) * f, f = -y; z0 from the lowest sole point against that plane
    z0 = float((Vb_[:, 2] - math.tan(slope) * (-Vb_[:, 1])).min())
    piv = np.array(rig.pose.bones["pelvis"].head)
    X = Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation((-piv[0], -piv[1], -z0))
    for o in figure:
        o.matrix_world = X @ o.matrix_world
    M_world = X @ P @ A
    for o in w.pack:
        if o.parent is None and pack_parts is None:
            o.matrix_world = M_world
    w.fit["pack_on_torso"] = [list(r) for r in M_world]
    w.ground = ((0.0, 0.0, 0.0), (0.0, -math.sin(slope), math.cos(slope)))
    w.fit["lean_deg"] = info["lean_deg"]
    w.fit["slope_deg"] = info["slope_deg"]
    w.props = add_props(w, info, X)
    bpy.data.objects.remove(rig, do_unlink=True)
    w.rig = None
    w.objects = w.figure + w.pack + w.props
    hb = _xf(np.array(X), _co(body)) if False else np.array([o.matrix_world.translation[:] for o in figure[:1]])
    _ = hb
    return w


def add_props(w: Wearer, info: dict, X) -> list:
    """Pose props: trekking poles through the fists down to the slope, binoculars in front of the eyes."""
    props = []
    body = w.figure[0]
    V = _xf(np.array(body.matrix_world), _co(body))
    gi = {g.name: g.index for g in body.vertex_groups}
    wts = {}

    def group_pts(name, thr=0.5):
        if name not in gi:
            return np.zeros((0, 3))
        if name not in wts:
            k = gi[name]
            wts[name] = np.array([any(g.group == k and g.weight > thr for g in v.groups) for v in body.data.vertices])
        return V[wts[name]]
    n = np.array(w.ground[1])
    if info["props"].get("poles"):
        alu = _plain_material("pole_shaft", (0.02, 0.02, 0.022), 0.35, metallic=0.9)
        grip = _plain_material("pole_grip", (0.035, 0.03, 0.025), 0.9)
        for s, fwd in (("l", 0.02), ("r", 0.20)):
            pts = np.vstack([group_pts(f"{f}_0{k}_{s}") for f in ("index", "middle", "ring", "pinky") for k in (1, 2)])
            if not len(pts):
                continue
            hand = pts.mean(0)
            palm = group_pts(f"hand_{s}").mean(0)
            c = 0.5 * (hand + palm)
            tip = np.array([c[0] + (0.05 if s == "r" else -0.05), c[1] + fwd, 0.0])
            tip[2] = -(n[0] * tip[0] + n[1] * tip[1]) / n[2]          # on the slope
            ax = (c - tip) / np.linalg.norm(c - tip)
            top = c + ax * 0.075
            props += [_tube(f"pole_{s}_shaft", tip + ax * 0.03, c - ax * 0.07, 0.0065, alu, r2=0.008),
                      _tube(f"pole_{s}_tip", tip - ax * 0.005, tip + ax * 0.03, 0.002, alu, r2=0.0065),
                      _tube(f"pole_{s}_basket", tip + ax * 0.045, tip + ax * 0.05, 0.022, grip),
                      _tube(f"pole_{s}_grip", c - ax * 0.07, top, 0.0145, grip, r2=0.016),
                      _tube(f"pole_{s}_knob", top, top + ax * 0.012, 0.016, grip, r2=0.011)]
    if info["props"].get("binoculars"):
        eyes = next(o for o in w.figure if o.name == "wearer_eyes")
        E = _xf(np.array(eyes.matrix_world), _co(eyes))
        ec = E.mean(0)
        el, er = E[E[:, 0] < ec[0]].mean(0), E[E[:, 0] > ec[0]].mean(0)
        Xr = np.array(X)[:3, :3]
        fw = Xr @ np.array(info.get("head_fwd", (0.0, -1.0, 0.0)))
        lat = (er - el) / np.linalg.norm(er - el)
        fw = fw - lat * fw.dot(lat)
        fw /= np.linalg.norm(fw)
        arm = _plain_material("bino_armour", (0.03, 0.035, 0.03), 0.75)
        glass = _plain_material("bino_glass", (0.01, 0.012, 0.02), 0.08, coat=1.0)
        for k, e in enumerate((el, er)):
            a = e + fw * 0.034
            props += [_tube(f"bino_{k}_eyecup", a, a + fw * 0.022, 0.019, arm, r2=0.02),
                      _tube(f"bino_{k}_body", a + fw * 0.022, a + fw * 0.12, 0.021, arm, r2=0.026, n=24),
                      _tube(f"bino_{k}_obj", a + fw * 0.12, a + fw * 0.15, 0.027, arm, n=24),
                      _tube(f"bino_{k}_lens", a + fw * 0.146, a + fw * 0.151, 0.0235, glass, n=24)]
        m = 0.5 * (el + er) + fw * 0.09
        props.append(_tube("bino_bridge", m - lat * 0.02, m + lat * 0.02, 0.012, arm))
    return props


def studio_wearer(torso_in=None, pose="stand", outfit="midlayer", **kw) -> dict:
    """Hook for ``huntkit.viz3d.studio.render(..., wearer="huntkit.viz3d.wearer:studio_wearer", wearer_kwargs={...})``.
    studio has already imported the concept's GLB into the scene: the harness and belt meshes found there by name are
    fitted to the body in place, and the rigid pack-to-torso transform is returned for studio to apply to the pack.
    The concept's scene must be rendered with ``state.torso`` = ``figure_spec(torso_in)["torso_setting_in"]``."""
    bpy = _bpy()
    setting = figure_spec(torso_in, kw.get("stature_mm"), kw.get("sex"))["torso_setting_in"]
    tag = f"@t{setting:g}"
    parts, form = {}, None
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if o.name.startswith("mannequin@") or "display_form" in o.name:
            form = o if (o.name.endswith(tag) or form is None) else form
            continue
        if "@t" in o.name and not o.name.endswith(tag):
            continue
        mw = o.matrix_world.copy()
        if o.parent is None:
            o.data.transform(mw)
            o.matrix_world.identity()
        parts[o.name] = o
    w = build_wearer(torso_in, pose, outfit, pack_parts=parts, form=form, **kw)
    return {"objects": w.figure + w.props, "pack_on_torso": w.fit["pack_on_torso"], "wearer": w}


# ------------------------------------------------------------------------------------------------ render stage
# Shots: pose, scene ("studio" = BL-018's studio rig from huntkit.viz3d.studio; "outdoor" = CC0 HDRI + grass ground),
# camera azimuth / elevation in the viewer convention (0 = looking at the bag's aft face, 90 = from the wearer's
# right, 180 = from the front), optional close-up box in metres (wearer frame: x right, y forward, z up from ground).
NOT_A_PHOTO = "Rendered 3D figure (Blender Cycles), not a photograph"
SHOTS = {
    "hero": {"pose": "stand", "scene": "studio", "az": -36, "el": 9,
             "caption": "CORRIE B.2 on a 6 ft hunter: 3/4 rear", "sub": "{fit}. " + NOT_A_PHOTO},
    "front": {"pose": "front", "scene": "studio", "az": 152, "el": 8,
              "caption": "Front 3/4: belt, pocket, bottle, sternum strap",
              "sub": "Belt B size {belt} on the iliac crest; poles in hand. " + NOT_A_PHOTO},
    "side": {"pose": "side", "scene": "studio", "az": 90, "el": 4,
             "caption": "Side profile: how tall and how deep it rides",
             "sub": "Head gap {head} mm; lifters {lifter} deg (design 40.6). " + NOT_A_PHOTO},
    "walk": {"pose": "walk", "scene": "outdoor", "az": -58, "el": 6,
             "caption": "Walking uphill with trekking poles (14 deg slope)", "sub": NOT_A_PHOTO + ". HDRI: Poly Haven, CC0"},
    "kneel": {"pose": "kneel", "scene": "outdoor", "az": 118, "el": 5,
              "caption": "Kneeling and glassing with the pack on", "sub": NOT_A_PHOTO + ". HDRI: Poly Haven, CC0"},
    "field": {"pose": "stand", "scene": "outdoor", "az": -40, "el": 7,
              "caption": "In the field: 3/4 rear, sun from the side", "sub": NOT_A_PHOTO + ". HDRI: Poly Haven, CC0"},
    "fit_back": {"pose": "stand", "scene": "studio", "az": 62, "el": 10, "box": (-0.30, -0.42, 0.85, 0.34, 0.25, 1.80),
                 "caption": "Fit detail: straps on the shoulders, belt on the hips",
                 "sub": "Pads pressed {press} mm into the cloth; no daylight under the straps. " + NOT_A_PHOTO},
    "fit_front": {"pose": "front", "scene": "studio", "az": 205, "el": 12, "box": (-0.36, -0.30, 0.85, 0.36, 0.30, 1.62),
                  "caption": "Fit detail: belt, bottle holster, sternum strap",
                  "sub": "Front webbing between the wing tips is drawn by wearer.py (the viz3d belt is open). "
                         + NOT_A_PHOTO},
}
DEFAULT_SHOTS = ("hero", "front", "side", "walk", "kneel", "field", "fit_back", "fit_front")


def _ph(asset_id) -> Path:
    m = {a["id"]: a for a in load_manifest()["assets"]}[asset_id]
    return asset_dir() / m["dir"] / m["file"]


def _outdoor(w: Wearer, cam_az: float, sun_off_deg: float = -70.0, exposure: float = -0.6):
    """Mountain setting: Poly Haven HDRI as light and backdrop, a grass ground on the wearer's slope, dry-grass tufts
    round the feet. The HDRI is turned so the sun stands ``sun_off_deg`` round from the camera (side light)."""
    bpy = _bpy()
    from . import cycles_render as CR  # noqa: PLC0415
    sc = bpy.context.scene
    wd = bpy.data.worlds.new("mountain")
    sc.world = wd
    wd.use_nodes = True
    nt = wd.node_tree
    nt.nodes.clear()
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(_ph("ph_hdri")), check_existing=True)
    bg, out = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    d = CR.view_dir(cam_az + sun_off_deg, 0.0)                        # where the sun should stand (from the subject)
    want = math.atan2(d[1], d[0])
    have = math.atan2(math.sin(math.radians(HDRI_SUN_AZ_DEG)), math.cos(math.radians(HDRI_SUN_AZ_DEG)))
    mp.inputs["Rotation"].default_value = (0.0, 0.0, have - want + math.pi)   # sign / half-turn set by test render
    bg.inputs["Strength"].default_value = 1.0
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False
    # ground
    n = np.array(w.ground[1])
    size = 120.0
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2, size=size)
    g = bpy.context.active_object
    g.name = "ground"
    from mathutils import Vector  # noqa: PLC0415
    g.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector(n)).to_euler()
    g.location = (0, 0, -0.004)
    m = bpy.data.materials.new("grass_ground")
    m.use_nodes = True
    t = m.node_tree
    b = t.nodes["Principled BSDF"]
    tcn, mpn = t.nodes.new("ShaderNodeTexCoord"), t.nodes.new("ShaderNodeMapping")
    mpn.inputs["Scale"].default_value = (size / 2.2, size / 2.2, 1.0)
    t.links.new(tcn.outputs["UV"], mpn.inputs["Vector"])
    base = asset_dir() / {a["id"]: a for a in load_manifest()["assets"]}["ph_grass_diff"]["dir"]

    def tex(fn, noncolor):
        ti = t.nodes.new("ShaderNodeTexImage")
        ti.image = bpy.data.images.load(str(base / fn), check_existing=True)
        if noncolor:
            ti.image.colorspace_settings.name = "Non-Color"
        t.links.new(mpn.outputs["Vector"], ti.inputs["Vector"])
        return ti
    t.links.new(tex("grass_ground_diff_2k.jpg", False).outputs["Color"], b.inputs["Base Color"])
    t.links.new(tex("grass_ground_rough_2k.jpg", True).outputs["Color"], b.inputs["Roughness"])
    nm = t.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 1.5
    t.links.new(tex("grass_ground_nor_gl_2k.jpg", True).outputs["Color"], nm.inputs["Color"])
    t.links.new(nm.outputs[0], b.inputs["Normal"])
    g.data.materials.append(m)
    extra = [g]
    # dry-grass tufts round the feet: a patch of thin curved blades (mesh, so it needs no particle system)
    rng = np.random.default_rng(7)
    V, F = [], []
    nb = 70000
    r = 11.0 * rng.random(nb) ** 1.15                               # dense at the feet, thinning with distance
    a = rng.random(nb) * 2 * math.pi
    px, py = r * np.cos(a), r * np.sin(a)
    pz = -(n[0] * px + n[1] * py) / n[2]
    hgt = 0.05 + 0.11 * rng.random(nb) ** 1.6
    lean = rng.normal(0, 0.35, (nb, 2))
    yaw = rng.random(nb) * math.pi
    wdt = 0.0022 + 0.002 * rng.random(nb)
    for i in range(nb):
        c, s = math.cos(yaw[i]), math.sin(yaw[i])
        k = len(V)
        for j, f in enumerate((0.0, 0.5, 1.0)):
            ww = wdt[i] * (1 - 0.85 * f)
            ox, oy = lean[i, 0] * hgt[i] * f * f, lean[i, 1] * hgt[i] * f * f
            V += [(px[i] + ox - c * ww, py[i] + oy - s * ww, pz[i] + hgt[i] * f),
                  (px[i] + ox + c * ww, py[i] + oy + s * ww, pz[i] + hgt[i] * f)]
        F += [(k, k + 1, k + 3, k + 2), (k + 2, k + 3, k + 5, k + 4)]
    gm = bpy.data.materials.new("dry_grass")
    gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    oi, rp = gm.node_tree.nodes.new("ShaderNodeObjectInfo"), gm.node_tree.nodes.new("ShaderNodeValToRGB")
    geo = gm.node_tree.nodes.new("ShaderNodeNewGeometry")
    _ = oi
    rp.color_ramp.elements[0].color = (0.16, 0.115, 0.05, 1)
    rp.color_ramp.elements[1].color = (0.42, 0.33, 0.16, 1)
    gm.node_tree.links.new(geo.outputs["Random Per Island"], rp.inputs["Fac"])
    gm.node_tree.links.new(rp.outputs["Color"], gb.inputs["Base Color"])
    gb.inputs["Roughness"].default_value = 0.7
    tuft = _mesh_obj("grass_tufts", np.array(V), F, gm, smooth=False)
    extra.append(tuft)
    return extra


HDRI_SUN_AZ_DEG = 0.0      # set by calibration below: azimuth (deg, atan2(y, x)) of the sun in the unrotated HDRI


def _hdri_sun_az() -> float:
    """Sun azimuth in Blender world axes of the unrotated HDRI: the brightest pixel. Blender's equirectangular
    lookup is u = atan2(y, -x) / 2 pi + 0.5."""
    bpy = _bpy()
    im = bpy.data.images.load(str(_ph("ph_hdri")), check_existing=True)
    wpx, hpx = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(hpx, wpx, 4)[:, :, :3].sum(2)
    j, i = np.unravel_index(int(np.argmax(a)), a.shape)
    ang = ((i + 0.5) / wpx - 0.5) * 2 * math.pi            # = atan2(y, -x)
    x, y = -math.cos(ang), math.sin(ang)
    return math.degrees(math.atan2(y, x)), (j / hpx - 0.5) * 180.0


def clear_scene():
    """Empty the current file without a factory reset (a reset would unregister the MPFB extension)."""
    bpy = _bpy()
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras,
                 bpy.data.lights, bpy.data.worlds, bpy.data.node_groups, bpy.data.curves):
        for b in list(coll):
            coll.remove(b)


def render_wearer(shots=DEFAULT_SHOTS, out_dir=None, prefix="20261110_BL019", quality="final", start=1,
                  torso_in=None, outfit="midlayer", glb=None, samples=None, captions=True, verbose=True) -> list:
    """Standalone render path (Blender Cycles): one build per pose, studio shots with BL-018's studio rig
    (huntkit.viz3d.studio: setup_render, make_backdrop, make_lights, place_lights, finish), outdoor shots with the
    HDRI scene. PNGs <= 1.5 MB to ``out_dir`` (default outputs/screens) as ``<prefix>_<n>.png``."""
    global HDRI_SUN_AZ_DEG
    bpy = _bpy()
    from . import cycles_render as CR  # noqa: PLC0415
    from . import studio as ST  # noqa: PLC0415
    out_dir = Path(out_dir or REPO / "outputs" / "screens")
    out_dir.mkdir(parents=True, exist_ok=True)
    work = REPO / "outputs" / "cycles_work"
    work.mkdir(parents=True, exist_ok=True)
    q = dict(ST.QUALITY[quality])
    if quality == "final":
        q["samples"] = 96
    if samples:
        q["samples"] = samples
    res = tuple(q["res"])
    order = list(shots)
    results = {}
    for pose in dict.fromkeys(SHOTS[s]["pose"] for s in order):
        t0 = time.time()
        clear_scene()
        w = build_wearer(torso_in, pose, outfit, glb=glb, verbose=False)
        if verbose:
            print(f"[{pose}] built in {time.time() - t0:.0f} s; fit "
                  + json.dumps({k: v for k, v in w.fit.items() if k != 'pack_on_torso'}), flush=True)
        sc = ST.setup_render(q["samples"], res, None)
        studio_world = sc.world
        cd = bpy.data.cameras.new("cam")
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 24.0
        cam = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(cam)
        sc.camera = cam
        backdrop, lights, outdoor = None, None, None
        meshes = [o for o in w.objects if o.type == "MESH"]
        for name in [s for s in order if SHOTS[s]["pose"] == pose]:
            sh = SHOTS[name]
            if sh["scene"] == "studio":
                if outdoor:
                    for o in outdoor:
                        o.hide_render = True
                if backdrop is None:
                    backdrop, lights = ST.make_backdrop(), ST.make_lights()
                backdrop.hide_render = False
                for o in lights:
                    o.hide_render = False
                sc.world = studio_world
                sc.view_settings.exposure = 0.0
            else:
                if backdrop is not None:
                    backdrop.hide_render = True
                    for o in lights:
                        o.hide_render = True
                if not HDRI_SUN_AZ_DEG:
                    HDRI_SUN_AZ_DEG = _hdri_sun_az()[0]
                if outdoor:
                    for o in outdoor:
                        bpy.data.objects.remove(o, do_unlink=True)
                outdoor = _outdoor(w, sh["az"])
            lo, hi = CR.visible_bounds(meshes)
            if "box" in sh:
                bmin, bmax = tuple(sh["box"][:3]), tuple(sh["box"][3:])
            else:
                bmin, bmax = lo, hi
            fov = 24.0
            cd.angle_y = math.radians(fov)
            pos, tgt = CR.fit_camera(bmin, bmax, sh["az"], sh["el"], fov, res[0] / res[1], 1.0, fill=0.93)
            cam.location = pos
            CR._aim(cam, tgt)
            dist = math.dist(pos, tgt)
            cd.dof.use_dof = True
            cd.dof.focus_distance = dist
            cd.dof.aperture_fstop = 11.0 if sh["scene"] == "studio" else 4.0
            cd.clip_start, cd.clip_end = 0.01, 300.0
            if sh["scene"] == "studio":
                backdrop.location = (tgt[0], tgt[1], -0.0005)
                d = CR.view_dir(sh["az"], 0.0)
                backdrop.rotation_euler = (0.0, 0.0, math.atan2(-d[1], -d[0]) - math.pi / 2)
                ST.place_lights(lights, sh["az"], tgt, max(1.6, 0.8 * dist) if "box" not in sh else max(1.2, dist))
            raw = work / f"_raw_{prefix}_{name}.png"
            sc.render.filepath = str(raw)
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            n = start + order.index(name)
            out = out_dir / f"{prefix}_{n}.png"
            f = w.fit
            sub = sh["sub"].format(
                fit=f"1829 mm man, torso {f.get('torso_figure_mm', 0):.0f} mm, pack set to {f.get('torso_setting_in', 0):g} in",
                belt="L", head=f"{f.get('head_gap_mm', 0):.0f}",
                lifter="/".join(f"{a:.0f}" for a in f.get("lifter_angle_deg", [])),
                press=f"{f.get('harness', {}).get('press_mm_mean', 0):.0f} to {f.get('belt', {}).get('press_mm_mean', 0):.0f}")
            ST.finish(raw, out, sh["caption"] if captions else "", sub if captions else "")
            CR.shrink_png(out)
            results[name] = {"shot": name, "file": str(out), "seconds": round(time.time() - t1, 1),
                             "mb": round(out.stat().st_size / 1e6, 2), "fit": {k: v for k, v in f.items()
                                                                              if k != "pack_on_torso"}}
            if verbose:
                print(f"[{name}] {out} {time.time() - t1:.0f} s", flush=True)
    res_list = [results[s] for s in order]
    (work / f"{prefix}_wearer.json").write_text(json.dumps(res_list, indent=1))
    return res_list


def main(argv=None):
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("model", help="export the pack GLB with the wearer torso settings (repo Python)")
    m.add_argument("--torsos", default="", help="extra settings, e.g. 15,23")
    sub.add_parser("fetch", help="download and verify the human assets")
    sub.add_parser("spec", help="print the default wearer's ANSUR-derived dimensions")
    r = sub.add_parser("render", help="render shots (bpy venv)")
    r.add_argument("--shots", default="all")
    r.add_argument("--quick", action="store_true")
    r.add_argument("--torso", type=float, default=None)
    r.add_argument("--outfit", default="midlayer")
    r.add_argument("--prefix", default="20261110_BL019")
    r.add_argument("--out", default=None)
    r.add_argument("--start", type=int, default=1)
    a = ap.parse_args(argv)
    if a.cmd == "model":
        extra = [float(x) for x in a.torsos.split(",") if x]
        print(build_pack_glb([figure_spec()["torso_setting_in"]] + extra))
    elif a.cmd == "fetch":
        print("\n".join(fetch_assets()))
    elif a.cmd == "spec":
        s = figure_spec()
        print(json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items() if k != "dims"}))
        print(json.dumps({k: round(v, 1) for k, v in s["dims"].items()}, indent=1))
    else:
        names = DEFAULT_SHOTS if a.shots == "all" else tuple(a.shots.split(","))
        for x in render_wearer(names, a.out, a.prefix, "quick" if a.quick else "final", a.start, a.torso, a.outfit):
            print(x["file"], x["seconds"], "s", x["mb"], "MB")


if __name__ == "__main__":
    main()
