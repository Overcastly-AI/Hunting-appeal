"""BL-063 iteration 1, looks track: render CORRIE F rev 3 (today) and three colour-blocking concepts on the hunter.

Nothing here changes the design. Each concept is a *paint-over* of the rev 3 picture model
(``huntkit/viz3d/corrie_f.py``): the cloth-pass bag is re-split by its real pattern pieces (B-01, B-02u, B-03L/R,
B-06 ...) and the pieces are given other materials / colours. The one non-piece split (concept C: the B-02u kick strip
camo, the blades solid) is a print-file split inside one printed piece, not a seam. Geometry, straps, frame and belt are
exactly the rev 3 scene.

    export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python
    export HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets
    python designs/pack_5200/iter1/looks/looks_render.py --concept base --states sixday,day
    python designs/pack_5200/iter1/looks/looks_render.py --concept A           # sixday, 4 views
    python designs/pack_5200/iter1/looks/looks_render.py --sheets             # contact + comparison sheets

Concepts (rationale, masses and risks: ``design_language.md`` section 6 and ``concepts.md``):
    base  today's rev 3 Krummholz: camo blade U + garages + lid corner caps, Deadfall Shadow webbing / binding / thread
    A     TONAL: same pieces; webbing, binding, zip tape, cord and thread in Elk Wallow; camo only on the blade U
          (garages and lid caps to body colour); guy toggles from blaze to tonal
    B     FLANKS: A's tonal trim; both side gussets B-03L/R printed camo; the blade U printed solid body colour
    C     CROWN + PLINTH: A's tonal trim; roll collar B-06 (and the roll in the picture) and the crown lid shell camo,
          B-29g strap channels and B-07 hem stay solid 330D; the blade U printed camo only on
          its 75 mm kick strip (solid blades)
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huntkit.viz3d import corrie_f as CF  # noqa: E402

HERE = Path(__file__).resolve().parent
SCREENS = ROOT / "outputs" / "screens"
WORK = ROOT / "outputs" / "looks_iter1"
PREFIX = "20261124_iter1_looks"
QUALITY = {"res": (1600, 1200), "samples": 48}
# torso-up camera: the pack fills the frame on a phone (hero's HUNTER_BOX shows the whole 6 ft figure, pack small)
LOOK_BOX = [-330.0, -340.0, -420.0, 330.0, 380.0, 1000.0]

ELK_WALLOW = "#5E5A40"      # colorways.yaml elk_wallow (krummholz pairing harness)
KICK_TOP_Z = 152.0          # picture: top of the B-02u kick strip on the 6-day drape (75 mm strip on the U's floor run)

VIEWS = {   # name: (pose, az, el)  az 0 = straight behind the hunter (studio convention in corrie_f.SHOTS)
    "back": ("stand", 0, 6),
    "q34": ("stand", -36, 9),
    "side": ("side", 90, 4),
    "front": ("front", 180, 6),
    "bagoff": ("stand", -36, 9),        # BL-067 (review 7 m7): bag off, frame + harness + belt on the hunter
}
VIEW_LABEL = {"back": "back", "q34": "3/4 rear", "side": "side", "front": "front", "bagoff": "bag off, 3/4 rear"}
STATE_LABEL = {"sixday": "6-day load 45 L (loaded)", "day": "day load 12 L, lid off (near empty)"}
CONCEPT_LABEL = {"base": "TODAY (rev 3 Krummholz)", "A": "Concept A: TONAL", "B": "Concept B: FLANKS",
                 "C": "Concept C: CROWN + PLINTH", "Cp": "Concept C': CAMO LID CAP, LEVEL WRAPS, TAPERED ROLL"}


# ------------------------------------------------------------------------------------------------ concept paint
def _skin_pieces(sc):
    from huntkit.viz3d import corrie as VC
    S = VC.Skin(sc.cloth_skin)
    return S, S.piece.astype(str)


def _replace(sc, name, pieces):
    """Replace part ``name`` by [(new name, mesh, material), ...] keeping its flags."""
    i = next(k for k, p in enumerate(sc.parts) if p.name == name)
    old = sc.parts.pop(i)
    for nm, mesh, mat in pieces[::-1]:
        if mesh is not None and len(mesh.faces):
            sc.parts.insert(i, dataclasses.replace(old, name=nm, mesh=mesh, material=mat))


def _setmat(sc, prefix_or_names, mat):
    names = (prefix_or_names,) if isinstance(prefix_or_names, str) else tuple(prefix_or_names)
    for p in sc.parts:
        if p.name in names:
            p.material = mat


def _planar_uv(mesh):
    """Camo UV for picture parts built without a pattern UV (the roll, the lid): cylindrical about the bag's x axis
    (both are rounded along x), u = x, v = arc length round the axis, in the 500 mm texture-tile unit of the cloth
    skin (geom.TILE_MM). A flat (x, z) projection stretched the print on the lid top (checked on the first C render)."""
    from huntkit.viz3d import geom as G
    V = np.asarray(mesh.vertices)
    yc, zc = V[:, 1].mean(), V[:, 2].mean()
    r = np.hypot(V[:, 1] - yc, V[:, 2] - zc)
    th = np.arctan2(V[:, 2] - zc, V[:, 1] - yc)
    uv = np.c_[V[:, 0], th * max(float(np.median(r)), 1.0)] / G.TILE_MM
    mesh.metadata["uv"] = uv


def _needs_uv(mesh):
    uv = mesh.metadata.get("uv")
    return uv is None or len(uv) != len(mesh.vertices) or float(np.ptp(np.asarray(uv), axis=0).max()) < 1e-3


def tonal(sc):
    """A's trim rule (shared by B and C): webbing, binding, zip tape, cord, thread in Elk Wallow."""
    m = sc.materials
    for k in ("webbing", "trim", "zip_tape", "cord", "thread"):
        m[k] = dict(m[k], color="harness")
    m["tonal_toggle"] = {"shader": "plastic", "hex": "#3b3a2c", "rough": 0.5}
    for p in sc.parts:
        if p.material == "blaze" and "toggle" in p.name:
            p.material = "tonal_toggle"
    sc.materials["body_print"] = {"shader": "fabric", "record": "polyester_ht_630d_printable (solid ink fill)",
                                  "color": "body", "weave_mm": 0.55, "grid_mm": 0, "rough": 0.82, "sheen": 0.4}


def concept_A(sc, state):
    tonal(sc)
    _setmat(sc, ("corrie_zip_garages", "cf3_lid_caps"), "body_print")


def concept_B(sc, state):
    tonal(sc)
    S, pc = _skin_pieces(sc)
    gus = (pc == "B-03L") | (pc == "B-03R")
    um = pc == "B-02u"
    body = ~(um | (pc == "B-02door") | (pc == "B-05"))
    _replace(sc, "corrie_body", [("corrie_body", S.submesh(body & ~gus), "body"),
                                 ("corrie_gussets_camo", S.submesh(gus), "camo")])
    _setmat(sc, ("corrie_kick", "corrie_zip_garages"), "body_print")


def concept_C(sc, state):
    from huntkit.viz3d import corrie as VC
    from huntkit.viz3d import geom as G
    tonal(sc)
    S, pc = _skin_pieces(sc)
    um = pc == "B-02u"
    col = pc == "B-06"
    body = ~(um | (pc == "B-02door") | (pc == "B-05"))
    _replace(sc, "corrie_body", [("corrie_body", S.submesh(body & ~col), "body"),
                                 ("corrie_collar_camo", S.submesh(col), "camo")])
    # B-02u: one printed piece, camo on the kick strip only (print-file split, no seam)
    k = next(p for p in sc.parts if p.name == "corrie_kick")
    V, F = np.asarray(k.mesh.vertices), np.asarray(k.mesh.faces)
    V2, A, neg, pos, _ = VC.split_by_field(V, F, {"uv": np.asarray(k.mesh.metadata["uv"])}, V[:, 2] - KICK_TOP_Z)
    _replace(sc, "corrie_kick", [("corrie_kick_camo", VC._sub(V2, neg, A["uv"]), "camo"),
                                 ("corrie_blades_solid", VC._sub(V2, pos, A["uv"]), "body_print")])
    _setmat(sc, ("corrie_zip_garages",), "body_print")
    for p in sc.parts:
        if p.name in ("s15_roll", "cf3_lid", "cf3_lid_base"):      # B-29g strap channels stay 330D body colour
            if _needs_uv(p.mesh):
                _planar_uv(p.mesh)
            p.material = "camo"
    _ = G


# ------------------------------------------------------------------------------------------------ C' (BL-067)
# C' = camo on the lid crown B-29a only, A's Elk Wallow trim, no plinth (B-02u printed solid), the roll collar B-06
# solid on its own fabric, plus the geometry the rubric failed (looks 1, 2, 4). Unlike A-C this is NOT a paint-over:
# the cloth is re-solved (own cache folder) with the two geometry proposals below, which are specs for the pattern
# release (BL-067 follow-ups P1 / P2), drawn here so they can be judged. Rationale and numbers: design_language.md 10.
WRAP_LEVEL_Z = {"W1": 250.0, "W2": 420.0}   # PROPOSAL W-LEVEL: each wrap on the frame lash points at ONE height
#   (geometry.yaml hard_points load_wing_lash_z250_R/L and z420_R/L exist on both sides; today W1 runs z80 R -> z250 L
#   and W2 z250 R -> z420 L, a helix that crosses the door on a slant). Same lash points, same rated W rows.
ROLL_HALF_MM = 192.0        # PROPOSAL ROLL-TAPER: flattened mouth half-width (today 262.4 = (W + D) / 2); the collar
#   tapers from the seam to a mouth of 2 x 192 = 384 mm flattened, 10 mm under the 394 mm bag width cap (RULES 9)
OLIVE_MESH = "#4b4e36"      # ASSUMPTION MESH-COL: a dark olive nylon/spandex power mesh, same 170 g/m2 record
FOLIAGE = "#5a5947"         # ASSUMPTION HW-TONAL: ITW-type 'Foliage' acetal (sample card ordered, DECISIONS 2026-11-24)
HEM_MM = 34.0               # B-07 hem finished width (cut 92 mm: (92 - 2 x 12 SA) / 2), the roll's first turns
STOW_TAIL_MM = 100.0        # stowed tail drawn flat under its keeper, <= TAIL_RULE 100 mm visible


def _arch_scale():
    return ROLL_HALF_MM / 262.4495911544663


def geometry_patch():
    """Cloth-pass patches for C': level W1 / W2 anchors and the tapered mouth (the lip arch compressed in x so the
    flattened mouth is 2 x ROLL_HALF_MM). Own cache folder so the release scenes' cloth is untouched."""
    from huntkit.viz3d import cloth_pass as CP
    if getattr(CP, "_bl067", False):
        return CP
    CP.WORK = WORK / "Cp_cloth"
    w0, a0 = CP.wraps, CP.arch
    k = _arch_scale()

    def wraps(torso=19, shell="S15"):
        out = []
        for w in w0(torso, shell):
            if w["id"] in WRAP_LEVEL_Z:
                z = WRAP_LEVEL_Z[w["id"]]
                hp = {80.0: 10.5, 250.0: 7.3, 420.0: 4.1}[z]          # geometry.yaml lash points (y by height)
                w = dict(w, R=np.array([w["R"][0], hp, z]), L=np.array([w["L"][0], hp, z]))
            out.append(w)
        return out

    def arch(s, z_mid, p):
        return a0(np.asarray(s, float) * k, z_mid, p)
    CP.wraps, CP.arch, CP._bl067 = wraps, arch, True
    return CP


def _split_faces(mesh, keep):
    from huntkit.viz3d.assets import mesh as amesh
    V, F = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    uv = mesh.metadata.get("uv")
    out = []
    for m in (keep, ~keep):
        if not m.any():
            out.append(None)
            continue
        used = np.unique(F[m])
        remap = -np.ones(len(V), int)
        remap[used] = np.arange(len(used))
        u = None if uv is None or len(uv) != len(V) else np.asarray(uv)[used]
        out.append(amesh(V[used], remap[F[m]], u))
    return out


def concept_Cp(sc, state):
    tonal(sc)
    m = sc.materials
    m["mesh_olive"] = {"shader": "fabric", "record": "power_mesh_nylon_spandex (olive, ASSUMPTION MESH-COL)",
                       "hex": OLIVE_MESH, "weave_mm": 1.1, "grid_mm": 2.6, "rough": 0.86, "sheen": 0.55}
    m["hardware"] = dict(m["hardware"], hex=FOLIAGE)
    m["collar"] = dict(m["pocket"], color="body")                       # B-06 ripstop collar, body colour
    _setmat(sc, ("corrie_kick", "corrie_zip_garages"), "body_print")    # no plinth: B-02u printed solid
    for nm in ("beltB_holster_mesh", f"imp6_mesh@t{CF.TORSO}"):
        _setmat(sc, nm, "mesh_olive")
    # roll: B-06 collar ripstop in body colour, the B-07 hem (330D) as the first turns at the core (as built)
    r = next((p for p in sc.parts if p.name == "s15_roll"), None)
    if r is not None:
        uv = r.mesh.metadata.get("uv")
        F = np.asarray(r.mesh.faces)
        if uv is not None and len(uv) == len(r.mesh.vertices):
            al = np.asarray(uv)[:, 1] * 500.0
            hem = al[F].mean(1) < HEM_MM
            a, b = _split_faces(r.mesh, hem)
            _replace(sc, "s15_roll", [("s15_roll_hem", a, "body"), ("s15_roll", b, "collar")])
        else:
            r.material = "collar"
    # lid: crown B-29a camo (and its corner caps), walls / base / channels solid
    lid = next((p for p in sc.parts if p.name == "cf3_lid"), None)
    ridge = next((p for p in sc.parts if p.name == "cf3_lid_seam_top__ridge"), None)
    if lid is not None:
        if _needs_uv(lid.mesh):
            _planar_uv(lid.mesh)
        if ridge is not None:
            from scipy.spatial import cKDTree
            R = np.asarray(ridge.mesh.vertices)
            V, F = np.asarray(lid.mesh.vertices), np.asarray(lid.mesh.faces)
            c = V[F].mean(1)
            _, j = cKDTree(R[:, :2]).query(c[:, :2])
            crown = c[:, 2] > R[j, 2] - 1.0
            a, b = _split_faces(lid.mesh, crown)
            _replace(sc, "cf3_lid", [("cf3_lid_crown", a, "camo"), ("cf3_lid_walls", b, "body")])
        else:
            lid.material = "camo"
    _setmat(sc, ("cf3_lid_caps",), "camo")
    _setmat(sc, ("cf3_lid_base",), "collar")
    # lid locks: rear crown-strap locks deleted (PROPOSAL LID-LOCK: the strap's rear end becomes a sewn loop on the
    # same B-28t tab box, so the rated tab row stays); front locks tonal
    sc.parts = [p for p in sc.parts if not p.name.startswith(("cf3_crown_lock_rear_", "cf3_crown_tail_rear_"))]
    # roll-clip tails stowed: flat under the strap, pointing down the gusset, at most STOW_TAIL_MM visible
    from huntkit.viz3d.assets import webbing as WB
    vis = dict(group="bag", modes=("pack", "pack_haul"))
    for side, sx in (("R", 1.0), ("L", -1.0)):
        b = next((p for p in sc.parts if p.name == f"s15_roll_buckle_{side}"), None)
        if b is None:
            continue
        sc.parts = [p for p in sc.parts if not p.name.startswith(f"cf_roll_clip_tail_{side}")]
        V = np.asarray(b.mesh.vertices, float)
        p0 = np.array([V[:, 0].max() if sx > 0 else V[:, 0].min(), V[:, 1].mean(), V[:, 2].min() - 2.0])
        p0[0] += sx * 1.8
        tm = WB.tail(p0, np.array([0.0, 0.0, -1.0]), np.array([sx, 0.0, 0.0]), STOW_TAIL_MM, 25.0, stiffness=1.0,
                     fold=10.0)
        sc.add_part(f"cf_roll_clip_tail_{side}", tm, "webbing", label="roll-clip tail stowed flat under the K-RT keeper",
                    **vis)
        kp = WB.tail(p0 + np.array([sx * 1.6, 0.0, -30.0]), np.array([0.0, 0.0, -1.0]), np.array([sx, 0.0, 0.0]),
                     25.0, 27.0, stiffness=1.0, fold=0.0)
        sc.add_part(f"cf_roll_clip_tail_{side}__keeper", kp, "elastic", label="K-RT keeper", **vis)


CONCEPTS = {"base": None, "A": concept_A, "B": concept_B, "C": concept_C, "Cp": concept_Cp}


def install(concept):
    """Patch corrie_f so every scene it builds carries the concept's paint, in its own work folder."""
    fn = CONCEPTS[concept]
    CF.WORK = WORK / concept
    if fn is None:
        return
    if concept == "Cp":
        geometry_patch()
    orig = CF.finish

    def finish(sc, state, **kw):
        sc = orig(sc, state, **kw)
        fn(sc, state)
        sc.report["looks_concept"] = concept
        return sc
    CF.finish = finish


def shots(concept, states, views):
    out, numbers = [], {}
    for st in states:
        for v in views:
            pose, az, el = VIEWS[v]
            key = f"{concept}_{st}_{v}"
            cap = f"{CONCEPT_LABEL[concept]}, {VIEW_LABEL[v]}, {STATE_LABEL[st]}"
            CF.SHOTS[key] = CF._hunter(pose, st, az, el, cap,
                                       "CORRIE F rev 3 geometry, Krummholz Sage body, Owner Base camo. 6 ft hunter. ",
                                       box=LOOK_BOX, zoom=1.08)
            if v == "bagoff":
                CF.SHOTS[key]["state"] = {"lid": False, "mode": "frame"}
            out.append(key)
    return out


def file_for(concept, state, view):
    return SCREENS / f"{PREFIX}_{concept}_{state}_{view}.png"


def render(concept, states, views, quality=None):
    install(concept)
    names = shots(concept, states, views)
    numbers = {n: k + 1 for k, n in enumerate(names)}
    res = CF.render(names, SCREENS, f"{PREFIX}_tmp_{concept}", quality or QUALITY, numbers=numbers)
    for x in res:
        c, st, v = x["shot"].split("_", 2)
        dst = file_for(c, st, v)
        Path(x["file"]).replace(dst)
        x["file"] = str(dst)
        print(x["shot"], dst, x.get("seconds"), "s", flush=True)
    (WORK / f"{concept}_renders.json").write_text(json.dumps(res, indent=1, default=str))
    return res


# ------------------------------------------------------------------------------------------------ sheets
SHEET_BG = (236, 234, 228)
CROP = (430, 120, 1170, 980)        # the pack and torso in a 1600 x 1200 frame (caption band dropped)


def _font(size, bold=False):
    from PIL import ImageFont
    for f in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _tile(path, w):
    from PIL import Image
    im = Image.open(path).convert("RGB").crop(CROP)
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def _save(im, out, limit=1.5e6):
    from PIL import Image
    q = im
    while True:
        q.save(out, optimize=True)
        if out.stat().st_size <= limit or q.width < 600:
            return out
        q = im.resize((int(q.width * 0.9), int(q.height * 0.9)), Image.LANCZOS)


def sheet(grid, title, sub, out, w=600):
    """grid: rows of (concept, state, view, label) cells, cropped renders, one title band."""
    from PIL import Image, ImageDraw
    head, lab, foot = 96, 36, 8
    tiles = [[_tile(file_for(c, st, v), w) for c, st, v, _ in row] for row in grid]
    th = tiles[0][0].height
    W = w * max(len(r) for r in grid)
    H = head + len(grid) * (th + lab) + foot
    im = Image.new("RGB", (W, H), SHEET_BG)
    d = ImageDraw.Draw(im)
    d.text((14, 10), title, fill=(34, 33, 30), font=_font(32 if W > 1000 else 24, True))
    d.text((14, 56), sub, fill=(90, 88, 82), font=_font(20 if W > 1000 else 15))
    for i, row in enumerate(grid):
        y = head + i * (th + lab)
        for j, (_, _, _, text) in enumerate(row):
            im.paste(tiles[i][j], (j * w, y + lab))
            d.text((j * w + 12, y + 6), text, fill=(34, 33, 30), font=_font(24, True))
    return _save(im, out)


SHORT = {"base": "TODAY", "A": "A tonal", "B": "B flanks", "C": "C crown + plinth"}


def sheets():
    made = []
    V = ("back", "q34", "side", "front")
    lab = {"back": "back", "q34": "3/4 rear", "side": "side", "front": "front"}
    for c, states, n in (("base", ("sixday", "day"), 1), ("A", ("sixday",), 3), ("B", ("sixday",), 4),
                         ("C", ("sixday",), 5)):
        for st in states:
            if not all(file_for(c, st, v).exists() for v in V):
                continue
            k = n if st == "sixday" else 2
            grid = [[(c, st, v, lab[v]) for v in V[:2]], [(c, st, v, lab[v]) for v in V[2:]]]
            made.append(sheet(grid, f"{CONCEPT_LABEL[c]}", f"{STATE_LABEL[st]}. CORRIE F rev 3 on a 6 ft hunter. "
                              "Rendered 3D model, not a photograph.", SCREENS / f"{PREFIX}_{k}.png", w=600))
    cs = [c for c in ("base", "A", "B", "C") if all(file_for(c, "sixday", v).exists() for v in ("q34", "side", "back"))]
    if len(cs) > 1:
        grid = [[(c, "sixday", v, f"{SHORT[c]}, {lab[v]}") for v in ("back", "q34", "side")] for c in cs]
        made.append(sheet(grid, "Looks iter 1: today vs concepts", "6-day load, same cameras, same geometry; only "
                          "colour, print and trim change.", SCREENS / f"{PREFIX}_6.png", w=420))
    made += sheets_bl067()
    for m in made:
        print(m, round(m.stat().st_size / 1e6, 2), "MB")
    return made


BL067 = "20261124_bl067"


def sheets_bl067():
    """BL-067: 1 today vs C' (and C) comparison, 2 C' loaded 4 views, 3 C' day load 4 views, 4 bag off."""
    made = []
    V = ("back", "q34", "side", "front")
    lab = {"back": "back", "q34": "3/4 rear", "side": "side", "front": "front"}
    short = {"base": "TODAY", "C": "C (review 7)", "Cp": "C'"}
    rows = [c for c in ("base", "C", "Cp") if all(file_for(c, "sixday", v).exists() for v in ("back", "q34", "side"))]
    if "Cp" in rows:
        grid = [[(c, "sixday", v, f"{short[c]}, {lab[v]}") for v in ("back", "q34", "side")] for c in rows]
        made.append(sheet(grid, "BL-067: today vs C vs C'", "6-day load, same cameras. C': camo lid crown only, level W1/W2, "
                          "roll at bag width, olive mesh, tonal hw.",
                          SCREENS / f"{BL067}_1.png", w=420))
    for st, n in (("sixday", 2), ("day", 3)):
        if all(file_for("Cp", st, v).exists() for v in V):
            grid = [[("Cp", st, v, lab[v]) for v in V[:2]], [("Cp", st, v, lab[v]) for v in V[2:]]]
            made.append(sheet(grid, CONCEPT_LABEL["Cp"], f"{STATE_LABEL[st]}. Rendered 3D model. Proposals, not yet in the release.", SCREENS / f"{BL067}_{n}.png",
                              w=600))
    if file_for("Cp", "sixday", "bagoff").exists() and file_for("Cp", "sixday", "q34").exists():
        grid = [[("Cp", "sixday", "q34", "bag on, 3/4 rear"), ("Cp", "sixday", "bagoff", "bag off, 3/4 rear")]]
        made.append(sheet(grid, "C': bag on / bag off", "Bag off shows the H1 frame (looks criterion 5 is the frame "
                          "track's). Rendered 3D model.", SCREENS / f"{BL067}_4.png", w=600))
    return made


def _strap_len(meta_file, wid):
    m = json.loads(Path(meta_file).read_text())
    for st in m["straps"]:
        if st["id"] == wid:
            P = np.vstack([st["R"], np.asarray(st["P1"]), st["L"]])
            return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()), [float(st["R"][2]), float(st["L"][2])]
    return None, None


def cp_checks(states=("day", "sixday", "full"), write=True) -> dict:
    """BL-067: re-run the roll-clip path (the BL-043 check, ``corrie_f.roll_clip_paths``) on the tapered roll and the
    level wraps, size the RT cut as strap_tails.roll_row does, and compare the W1 / W2 strap paths with today's
    cached cloth. Writes ``cp_checks.json`` next to this file. Nothing in the release is written."""
    import importlib
    import math
    base = json.loads((ROOT / "designs" / "pack_5200" / "concepts" / "corrie_f_sim" / "corrie_f_roll_clips.json")
                      .read_text())
    CP = geometry_patch()
    new = CF.roll_clip_paths(states, write=False)
    sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
    STT = importlib.import_module("strap_tails")
    F = STT._F()

    def cut_of(st_rows):
        L = max(max(v["roll_clip_mm"].values()) for v in st_rows.values())
        used = float(np.mean(list(st_rows["sixday"]["roll_clip_mm"].values())))
        lmin = min(min(v["roll_clip_mm"].values()) for v in st_rows.values())
        cut = 5.0 * math.ceil((STT.ROLL_END_MM + L + F.TAIL_GRIP_MM) / 5.0)
        return {"path_max_mm": round(L, 1), "path_used_mm": round(used, 1), "path_min_mm": round(lmin, 1),
                "cut_mm": cut, "tail_used_mm": round(cut - STT.ROLL_END_MM - used, 1),
                "tail_longest_mm": round(cut - STT.ROLL_END_MM - lmin, 1),
                "tail_rule_met": bool(cut - STT.ROLL_END_MM - used <= F.TAIL_RULE_MM)}
    out = {"date": "2026-11-24", "ticket": "BL-067", "roll_half_mm": {"today": 262.45, "Cp": ROLL_HALF_MM},
           "roll_clip": {"today": {"states": base["states"], **cut_of(base["states"])},
                         "Cp": {"states": new["states"], **cut_of(new["states"])}},
           "w3_roll": {"today": base.get("w3_roll"), "Cp": new.get("w3_roll")},
           "tail_rule_mm": F.TAIL_RULE_MM, "tail_grip_mm": F.TAIL_GRIP_MM, "roll_end_mm": STT.ROLL_END_MM,
           "wraps": {}}
    for st in states:
        for wid in ("W1", "W2"):
            a, za = _strap_len(ROOT / "outputs" / "cloth_pass" / "CF_PR19" / f"{st}_L2.meta.json", wid)
            b, zb = _strap_len(CP.WORK / "CF_PR19" / f"{st}_L2.meta.json", wid)
            out["wraps"].setdefault(wid, {})[st] = {"today_mm": round(a, 1) if a else None, "today_z_RL": za,
                                                    "Cp_mm": round(b, 1) if b else None, "Cp_z_RL": zb}
    if write:
        (HERE / "cp_checks.json").write_text(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--concept", choices=list(CONCEPTS))
    ap.add_argument("--states", default="sixday")
    ap.add_argument("--views", default="back,q34,side,front")
    ap.add_argument("--draft", action="store_true", help="600 x 450, 16 samples (check the paint)")
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--cp-checks", action="store_true", help="BL-067: roll-clip path + W paths on C' geometry")
    a = ap.parse_args(argv)
    if a.cp_checks:
        print(json.dumps(cp_checks(), indent=1)[:3000])
    if a.sheets:
        sheets()
    if a.concept:
        q = {"res": (600, 450), "samples": 16} if a.draft else None
        render(a.concept, a.states.split(","), a.views.split(","), q)


if __name__ == "__main__":
    main()
