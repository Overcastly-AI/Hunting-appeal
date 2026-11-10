"""CHERT renders: the CORRIE B.2 render stack (huntkit/viz3d corrie / corrie_b1 / corrie_b2: frame, harness, belt B,
display form, roll-top, pouch, wings, tripod, scope sleeve, door) rebuilt ON CHERT's own cloth-sim drape, then CHERT's
colour blocking cut exactly along its seam lines.

No shared module is edited. For this process only, the viz3d CORRIE modules are pointed at CHERT: their ``sim_skin``
returns CHERT's fine packed drape (outputs/clothsim/chert_PR19_fine) and their ``_concept`` returns a proxy of
concepts/corrie.py whose ``make()`` is CHERT's envelope (form.make). Every placed part then sits on CHERT's skin.

    python designs/pack_5200/bag_comp/form/form_viz.py              # GLB + manifest + shots.json -> outputs/pack3d_chert
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_chert/chert.glb \\
        --manifest outputs/pack3d_chert/manifest.json --shots outputs/pack3d_chert/shots.json \\
        --views e_hero,e_side,e_access,e_feature,e_haul --samples 64 --prefix 20261110_bagE --out outputs/screens
"""
from __future__ import annotations

import json
import pickle
import sys
import types
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import form as F  # noqa: E402
import form_sim as FS  # noqa: E402

ROOT = F.ROOT
OUT = ROOT / "outputs" / "pack3d_chert"
import os  # noqa: E402
FINE = os.environ.get("CHERT_SKIN", "fine") == "fine"      # CHERT_SKIN=coarse: look-dev on the h 40 run
SIM = ROOT / "outputs" / "clothsim" / ("chert_PR19_fine" if FINE else "chert_PR19c")
CACHE = ROOT / "outputs" / "clothsim" / "cache"


def chert_skin(case="packed") -> dict:
    xf = SIM / f"x_{case}.npy"
    key = CACHE / f"chert_skin_{SIM.name}_{case}_{int(xf.stat().st_mtime)}.pkl"
    if key.exists():
        return pickle.loads(key.read_bytes())
    pm = FS.model(19, fine=FINE)
    m = pm.mesh
    uv = np.zeros((m.n, 2))
    for p in m.pieces:
        uv[p.gid] = p.xy
    out = {"X": np.load(xf), "X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    CACHE.mkdir(parents=True, exist_ok=True)
    key.write_bytes(pickle.dumps(out))
    return out


def _proxy():
    CO = F.CO
    px = types.ModuleType("corrie_chert_proxy")
    px.__dict__.update({k: v for k, v in vars(CO).items() if not k.startswith("__")})
    px.make = lambda rev=None: F.make()
    px.DOOR = dict(F.DOOR)
    return px


def install():
    import huntkit.viz3d.corrie as VC
    import huntkit.viz3d.corrie_b1 as V1
    import huntkit.viz3d.corrie_b2 as V2
    px = _proxy()
    sk = chert_skin()
    conc = lambda: (F.BC, px)       # noqa: E731
    skin = lambda *a, **k: sk       # noqa: E731
    for mod in (VC, V1, V2):
        mod._concept = conc
        mod.sim_skin = skin
    return sk


# ----------------------------------------------------------------------------- CHERT colour blocking
def fang_field(x0, c):
    """< 0 below the fang line on the gussets (camo), > 0 elsewhere. Line: frame edge z 60 -> blade edge z 260."""
    z = x0[:, 2]
    zc = np.clip(z, F.BC.Z0, c.z_c)
    yf = F.BC.y_frame(zc)
    d = c.depth(zc)
    cy = c.ch(zc)[1]
    t = np.clip((x0[:, 1] - yf) / np.maximum(d - cy, 1.0), 0, 1)
    return z - (F.FANG["z_frame"] + (F.FANG["z_aft"] - F.FANG["z_frame"]) * t)


def recolour(pack, params):
    import huntkit.viz3d.geom as G
    from huntkit.viz3d.corrie import (BAGM, BE, Part, Skin, boundary_chains, seam_chains, smooth_line, split_by_field,
                                      _sub)
    c = F.make()
    S = Skin(chert_skin())
    piece = S.piece
    gus = np.isin(piece, ["B-03R", "B-03L"])
    blade = piece == "B-02u"
    door = piece == "B-02door"
    floor = piece == "B-05"
    cap = np.isin(piece, ["B-06", "B-02h"])      # dark solid cap: collar + hinge band (two-tone solid blocking)
    solid = ~(gus | blade | door | floor | cap)
    parts = []
    # gussets cut along the fang line
    f = fang_field(S.x0, c)
    Vk, Ak, Fneg, Fpos, cut = split_by_field(S.V, S.F[gus], {"uv": S.uv}, f)
    parts.append(Part("chert_gusset", _sub(Vk, Fpos, Ak["uv"]), "body", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Side gussets B-03 (330D solid)"))
    parts.append(Part("chert_fang", _sub(Vk, Fneg, Ak["uv"]), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Fang inset SH-F (owner camo, 630D)"))
    parts.append(Part("chert_body", S.submesh(solid), "body", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Frame panel, hinge band, collar (solid)"))
    parts.append(Part("chert_cap", S.submesh(cap), "harness", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Collar B-06 + hinge band B-02h in the dark solid (same fabrics, second solid colour)"))
    parts.append(Part("chert_blades", S.submesh(blade), "camo", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Chamfer blade U B-02u (owner camo, 630D): blades + kick strip, door zip on its inner edge"))
    # seam piping: every sim seam except the zip, plus the fang seam, plus the blade creases are SEAMS here
    ch = seam_chains(S.F, piece)
    zip_key = frozenset(("B-02door", "B-02u"))
    tubes = []
    for key, chains in ch.items():
        if key == zip_key:
            continue
        for cc in chains:
            if len(cc) > 3:
                P = smooth_line(S.V[cc], 4.0, 10.0)
                q, _ = S.project(P, 1.2)
                tubes.append(G.tube(q, 2.0, n=8))
    cutset = set(cut.tolist())
    for cc in boundary_chains(Fneg, keep=lambda e: e[0] in cutset and e[1] in cutset):
        if len(cc) > 3:
            P = smooth_line(Vk[cc], 4.0, 6.0)
            q, _ = S.project(P, 1.2)
            tubes.append(G.tube(q, 2.0, n=8))
    parts.append(Part("chert_seams", G.concat(tubes), "trim", "bag", modes=BAGM, explode=BE, floats=True,
                      label="Seams: 301 + 2nd row, seared (B.2 rule)"))
    drop = {"corrie_body", "corrie_kick", "corrie_seams"}
    keep = []
    for p in pack.parts:
        if p.name in drop:
            continue
        if p.name == "corrie_zip_garages":      # garages on a camo blade: solid hypalon so they read
            p.material = "hypalon"
        if p.name == "corrie_roll":             # the rolled collar shows the dark cap colour
            p.material = "harness"
        keep.append(p)
    pack.parts = keep + parts
    pack.metrics["bag_type"] = "chert"
    return pack


SHOTS = {
    "e_hero": {"view": {"az": -34, "el": 12, "zoom": 1.22}, "state": {"mannequin": True, "lid": True},
               "caption": "CHERT (Team E FORM): 3/4 rear on the display form",
               "sub": "Camo chamfer blades on the aft corners carry the door zip; solid faces; fang insets low on the gussets"},
    "e_side": {"view": {"az": 90, "el": 4, "zoom": 1.15}, "state": {"mannequin": True, "lid": True},
               "caption": "CHERT: side profile, wearer's right",
               "sub": "Blade tapers 60 -> 32 mm floor to collar; tripod under the right wing; fang below the wing"},
    "e_access": {"view": {"az": -22, "el": 18, "zoom": 1.3}, "state": {"mannequin": True, "full": True},
                 "caption": "CHERT: door open (blade zips undone, door folded up over the hinge band)",
                 "sub": "Door = the whole aft face z 110-650; IM1-IM3 meat straps and the door pocket inside"},
    "e_feature": {"view": {"az": -30, "el": 6, "zoom": 1.0, "box": [-240, 150, 40, -40, 390, 700]},
                  "state": {"mannequin": True},
                  "caption": "CHERT: the blade line = camo break = door zip",
                  "sub": "#10 coil in the blade | door seam, fang inset meeting the blade, wing strap loop in the blade | gusset seam"},
    "e_haul": {"view": {"az": 68, "el": 8, "zoom": 1.1}, "state": {"mannequin": True, "haul": True, "gap": 170},
               "caption": "CHERT: meat haul, bag floated 170 mm on the B-24 links",
               "sub": "Boned quarter on the load shelf against the frame, bag hung behind it; W1-W3 wraps round meat and bag (GLB chert_haul)"},
}


def model():
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    install()
    from huntkit.viz3d.corrie_b2 import corrie_b2_pack
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = recolour(corrie_b2_pack(p), p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "chert.glb", mats=mats)
    (OUT / "manifest.json").write_text(json.dumps(manifest(pack), indent=1, default=float))
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    print("GLB", glb, len(pack.parts), "parts")
    haul_export(pack, mats)
    return pack


def haul_export(pack, mats, gap=170.0):
    """Float-mode GLB for Cycles: the viewer slides every ``floats`` part aft by the B-24 gap at draw time, the Cycles
    port does not, so the shift is baked here (bag parts + 170 mm in y; meat, frame, wraps stay)."""
    import copy

    from huntkit.viz3d.export import export_glb, manifest
    hp = copy.copy(pack)
    hp.parts = []
    for p in pack.parts:
        if getattr(p, "floats", False) and "pack_haul" in p.modes:
            q = copy.copy(p)
            m = p.mesh.copy()
            m.vertices = m.vertices + np.array([0.0, gap, 0.0])
            if "uv" in p.mesh.metadata:
                m.metadata["uv"] = p.mesh.metadata["uv"]
            q.mesh = m
            hp.parts.append(q)
        else:
            hp.parts.append(p)
    glb, _ = export_glb(hp, OUT / "chert_haul.glb", mats=mats)
    (OUT / "manifest_haul.json").write_text(json.dumps(manifest(hp), indent=1, default=float))
    print("GLB", glb)


if __name__ == "__main__":
    model()
