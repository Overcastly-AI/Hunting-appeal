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
}
VIEW_LABEL = {"back": "back", "q34": "3/4 rear", "side": "side", "front": "front"}
STATE_LABEL = {"sixday": "6-day load 45 L (loaded)", "day": "day load 12 L, lid off (near empty)"}
CONCEPT_LABEL = {"base": "TODAY (rev 3 Krummholz)", "A": "Concept A: TONAL", "B": "Concept B: FLANKS",
                 "C": "Concept C: CROWN + PLINTH"}


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


CONCEPTS = {"base": None, "A": concept_A, "B": concept_B, "C": concept_C}


def install(concept):
    """Patch corrie_f so every scene it builds carries the concept's paint, in its own work folder."""
    fn = CONCEPTS[concept]
    CF.WORK = WORK / concept
    if fn is None:
        return
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
    for m in made:
        print(m, round(m.stat().st_size / 1e6, 2), "MB")
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--concept", choices=list(CONCEPTS))
    ap.add_argument("--states", default="sixday")
    ap.add_argument("--views", default="back,q34,side,front")
    ap.add_argument("--draft", action="store_true", help="600 x 450, 16 samples (check the paint)")
    ap.add_argument("--sheets", action="store_true")
    a = ap.parse_args(argv)
    if a.sheets:
        sheets()
    if a.concept:
        q = {"res": (600, 450), "samples": 16} if a.draft else None
        render(a.concept, a.states.split(","), a.views.split(","), q)


if __name__ == "__main__":
    main()
