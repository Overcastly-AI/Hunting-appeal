"""Placed (engineered) camo print layouts for cut pattern pieces.

A *placed* print renders the camo inside each pattern piece in the piece's own on-product
frame, instead of printing one uniform repeat down the roll and cutting pieces out of it.
That gives three things a uniform print can't:

1. **Orientation is free of the cloth.** The art reads upright on the product whatever way the
   piece lies on the cloth, so a one-way print no longer forbids 180 deg (or, for a piece whose
   grain runs across it, 90 deg) on the marker. Grain stays where the pattern-maker put it.
2. **Phase is engineered.** Each piece gets a chosen offset into the repeat (``choose_phase``):
   all inks present, dark share near the repeat mean, and dark *and* light along the outer edge
   band (an even edge reads as a straight line at range). Every set prints the same phases, so
   every bag looks the same and QC can compare against one master.
3. **Only the piece areas carry ink.** The waste is left unprinted, with piece IDs, a 100 mm test
   square and an ink QC strip in it, so hand cutting is unambiguous.

Coordinates: piece outlines are in mm, piece frame +y = up on the product (ASSUMPTION carried by
the caller). Sheets are images with x across the fabric width and y down the roll (warp), so a
piece with its grain on piece-y is placed at rotation 0/180.

Main API
--------
- ``read_dxf_pieces(path) -> list[PieceGeom]``   (release DXF blocks: CUT/SEW/GRAIN/TEXT layers)
- ``pack_into(region, items, spacing_mm, step_mm)``  first-fit bottom-left packing into any polygon
- ``set_tile(pieces, spacing_mm)``  the largest piece with the others packed into its holes/bbox
- ``layout_sheet(width_mm, length_mm, tiles, n_sets, extras, ...)``  sets in a grid + extras
- ``choose_phase(labels, ppmm_tile, repeat_mm, piece, ...)``  engineered offset per piece
- ``render_sheet(layout, base_labels, repeat_mm, hexes, dpi, ...) -> PIL.Image``
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely import affinity
import shapely
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

WHITE = (255, 255, 255)
CUT_RGB = (90, 90, 90)          # printed cut-guide line (sits on the cut edge, inside the seam)
TEXT_RGB = (40, 40, 40)
UNPRINTED = 255                  # label value for "no ink"
CUTLINE = 254                    # label value for the cut-guide line


# ============================================================================ pieces
@dataclass
class PieceGeom:
    """One pattern piece read from a release DXF block (mm, piece frame)."""
    piece_id: str
    name: str
    cut: Polygon
    sew: Polygon | None
    grain_deg: float               # grain direction in the piece frame (90 = along piece y)
    quantity: int = 1
    material_id: str = ""
    up_deg: float = 90.0           # product "up" in the piece frame (ASSUMPTION: +y)

    @property
    def visible(self) -> Polygon:
        """Area seen on the product (inside the sew line)."""
        return self.sew if self.sew is not None and not self.sew.is_empty else self.cut


def _font(px: int):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, max(6, int(px)))
        except OSError:
            continue
    return ImageFont.load_default()


def read_dxf_pieces(path: str | Path) -> list[PieceGeom]:
    """Pieces from a release DXF (one block per piece; layers CUT, SEW, GRAIN, TEXT).

    Block TEXT carries ``ID: <id>``, ``PIECE: <name>``, ``MATERIAL: <id>`` and ``CUT <n>``. The grain
    angle is taken from the longest GRAIN polyline (the shaft)."""
    import ezdxf
    doc = ezdxf.readfile(str(path))
    out = []
    for blk in doc.blocks:
        if blk.name.startswith(("*", "_")):
            continue
        cut = sew = None
        grain = 90.0
        shaft = 0.0
        meta = {"ID": blk.name.rsplit("_", 1)[0], "PIECE": blk.name, "MATERIAL": "", "CUT": "1"}
        for e in blk:
            t = e.dxftype()
            if t == "LWPOLYLINE":
                pts = np.array([q[:2] for q in e.get_points()], float)
                if e.dxf.layer == "CUT" and e.closed:
                    cut = Polygon(pts)
                elif e.dxf.layer == "SEW" and e.closed:
                    sew = Polygon(pts)
                elif e.dxf.layer == "GRAIN" and len(pts) == 2:
                    d = pts[1] - pts[0]
                    L = float(np.hypot(*d))
                    if L > shaft:
                        shaft = L
                        grain = math.degrees(math.atan2(d[1], d[0])) % 180.0
            elif t == "TEXT":
                s = e.dxf.text.strip()
                m = re.match(r"^(ID|PIECE|MATERIAL):\s*(.+)$", s)
                if m:
                    meta[m.group(1)] = m.group(2)
                m = re.match(r"^CUT\s+(\d+)", s)
                if m:
                    meta["CUT"] = m.group(1)
        if cut is None:
            continue
        if not cut.is_valid:
            cut = cut.buffer(0)
        out.append(PieceGeom(meta["ID"], meta["PIECE"], cut, sew, grain, int(meta["CUT"]),
                             meta["MATERIAL"]))
    return out


def grain_rotations(grain_deg: float, warp_axis_deg: float = 90.0) -> tuple[float, float]:
    """The two rotations (deg, CCW) that lay a piece's grain on the warp (sheet y)."""
    r = (warp_axis_deg - grain_deg) % 360.0
    return (r, (r + 180.0) % 360.0)


def clean_hairlines(labels: np.ndarray, passes: int = 2) -> np.ndarray:
    """Remove 1-px-thick lines/specks (rasteriser seams between abutting SVG shapes, where the
    field ink shows through): a pixel whose two opposite neighbours agree with each other but not
    with it takes their value, along rows then columns. Periodic (wraps). Only valid where the
    finest real feature is >= 3 px (owner base: 3.0 mm at the accent scale, so >= 1 px/mm)."""
    L = labels.copy()
    for _ in range(passes):
        changed = 0
        for ax in (0, 1):
            a = np.roll(L, 1, ax)
            b = np.roll(L, -1, ax)
            m = (a == b) & (L != a)
            changed += int(m.sum())
            L[m] = a[m]
        if not changed:
            break
    return L


# ============================================================================ packing
@dataclass
class Item:
    key: str                        # unique instance key, e.g. "SH-01b#2"
    polygon: Polygon                # cut polygon in its own frame
    rotations: tuple = (0.0,)
    ref: object = None              # PieceGeom or a dict for extras


@dataclass
class Placed:
    key: str
    ref: object
    rotation: float                 # applied CCW about the frame origin, then translated
    dx: float
    dy: float
    polygon: Polygon                # placed cut polygon (sheet/tile frame)


def _place(poly: Polygon, rot: float, x: float, y: float) -> tuple[Polygon, float, float]:
    p = affinity.rotate(poly, rot, origin=(0, 0))
    bx, by = p.bounds[0], p.bounds[1]
    return affinity.translate(p, x - bx, y - by), x - bx, y - by


def pack_into(region: Polygon, items: list[Item], spacing_mm: float = 6.0, step_mm: float = 3.0,
              occupied: list[Polygon] | None = None) -> tuple[list[Placed], list[Item]]:
    """First-fit-decreasing, bottom-left packing of ``items`` into ``region`` (any polygon, holes
    allowed). Each piece keeps ``spacing_mm`` from other pieces and from the region boundary is
    not required beyond containment. Returns (placed, not_placed). Deterministic."""
    placed: list[Placed] = []
    left: list[Item] = []
    obst = [o.buffer(spacing_mm, join_style="mitre") for o in (occupied or [])]
    for it in sorted(items, key=lambda i: -i.polygon.area):
        best = None
        for rot in it.rotations:
            p0 = affinity.rotate(it.polygon, rot, origin=(0, 0))
            w = p0.bounds[2] - p0.bounds[0]
            h = p0.bounds[3] - p0.bounds[1]
            rx0, ry0, rx1, ry1 = region.bounds
            free = region
            if obst:
                free = region.difference(unary_union(obst))
            if free.is_empty:
                continue
            shapely.prepare(free)
            ys = np.arange(ry0, ry1 - h + 1e-6, step_mm)
            xs = np.arange(rx0, rx1 - w + 1e-6, step_mm)
            found = None
            for y in ys:                      # bottom-left: smallest y (top of sheet), then x
                if best is not None and y > best[0] + 1e-9:
                    break
                for x in xs:
                    cand = affinity.translate(p0, x - p0.bounds[0], y - p0.bounds[1])
                    if free.contains(cand):
                        found = (float(y), float(x))
                        break
                if found:
                    break
            if found and (best is None or found < best[:2]):
                best = (found[0], found[1], rot)
        if best is None:
            left.append(it)
            continue
        y, x, rot = best
        poly, dx, dy = _place(it.polygon, rot, x, y)
        placed.append(Placed(it.key, it.ref, rot, dx, dy, poly))
        obst.append(poly.buffer(spacing_mm, join_style="mitre"))
    return placed, left


@dataclass
class SetTile:
    """One product set: every piece instance, laid out in a tile frame (origin top-left, y down)."""
    placed: list[Placed]
    width_mm: float
    length_mm: float
    unplaced: list[str] = field(default_factory=list)

    @property
    def piece_area_mm2(self) -> float:
        return sum(p.polygon.area for p in self.placed)

    @property
    def utilisation(self) -> float:
        return self.piece_area_mm2 / (self.width_mm * self.length_mm)


def _flip_y(poly: Polygon) -> Polygon:
    """Piece frame (y up) -> sheet frame (y down)."""
    return affinity.scale(poly, 1.0, -1.0, origin=(0, 0))


def instances(pieces: list[PieceGeom], warp_axis_deg: float = 90.0) -> list[Item]:
    """Every cut instance as a packing item, in sheet orientation (y down), grain on the warp.
    In the sheet frame (y flipped) the warp is the image vertical as well."""
    items = []
    for pg in pieces:
        rots = grain_rotations(pg.grain_deg, warp_axis_deg)
        for k in range(pg.quantity):
            items.append(Item(f"{pg.piece_id}#{k + 1}", _flip_y(pg.cut), rots, pg))
    return items


def set_tile(pieces: list[PieceGeom], spacing_mm: float = 6.0, step_mm: float = 2.0) -> SetTile:
    """Lay the largest piece at rotation 0 (upright), then pack the others into the rest of its
    bounding box (its holes, e.g. the inside of a U). Anything that does not fit goes in a strip
    under it (the tile grows)."""
    items = instances(pieces)
    big = max(items, key=lambda i: i.polygon.area)
    rest = [i for i in items if i is not big]
    rot0 = big.rotations[0]
    poly, dx, dy = _place(big.polygon, rot0, 0.0, 0.0)
    first = Placed(big.key, big.ref, rot0, dx, dy, poly)
    W, H = poly.bounds[2], poly.bounds[3]
    region = box(0, 0, W, H)
    placed, left = pack_into(region, rest, spacing_mm, step_mm, occupied=[poly])
    unplaced = []
    if left:
        extra_h = sum(max(i.polygon.bounds[3] - i.polygon.bounds[1],
                          i.polygon.bounds[2] - i.polygon.bounds[0]) for i in left) + spacing_mm * (len(left) + 1)
        region2 = box(0, 0, W, H + extra_h)
        more, still = pack_into(region2, left, spacing_mm, step_mm,
                                occupied=[poly] + [p.polygon for p in placed])
        placed += more
        unplaced = [i.key for i in still]
        H = max([H] + [p.polygon.bounds[3] for p in more])
    return SetTile([first] + placed, W, H, unplaced)


# ============================================================================ sheets
@dataclass
class Sheet:
    name: str
    width_mm: float                 # image width = fabric (print) width
    length_mm: float                # image height = print length along the roll
    margin_mm: float                # unprinted selvedge band each side (non-guaranteed width)
    placed: list[Placed]
    notes: list[str] = field(default_factory=list)
    n_sets: int = 0

    @property
    def piece_area_mm2(self) -> float:
        return sum(p.polygon.area for p in self.placed if isinstance(p.ref, PieceGeom))

    @property
    def utilisation(self) -> float:
        usable = (self.width_mm - 2 * self.margin_mm) * self.length_mm
        return self.piece_area_mm2 / usable


def _shift(p: Placed, ox: float, oy: float, suffix: str) -> Placed:
    return Placed(p.key + suffix, p.ref, p.rotation, p.dx + ox, p.dy + oy,
                  affinity.translate(p.polygon, ox, oy))


def layout_sheet(name: str, width_mm: float, length_mm: float, tile: SetTile, n_sets: int,
                 margin_mm: float, gap_mm: float = 6.0, top_mm: float = 18.0,
                 extras: list[Item] | None = None, step_mm: float = 4.0) -> Sheet:
    """``n_sets`` tiles in rows across the usable width (left to right, then down), then the
    ``extras`` (test specimens, QC strip ...) packed into what is left. ``top_mm`` keeps a header
    band for the title and test square. Raises if the sets do not fit."""
    usable_w = width_mm - 2 * margin_mm
    per_row = int((usable_w + gap_mm) // (tile.width_mm + gap_mm))
    if per_row < 1:
        raise ValueError(f"{name}: set tile {tile.width_mm:.0f} mm wider than usable {usable_w:.0f} mm")
    placed: list[Placed] = []
    for s in range(n_sets):
        r, c = divmod(s, per_row)
        ox = margin_mm + c * (tile.width_mm + gap_mm)
        oy = top_mm + r * (tile.length_mm + gap_mm)
        if oy + tile.length_mm > length_mm + 1e-6:
            raise ValueError(f"{name}: set {s + 1} does not fit in {length_mm:.0f} mm")
        placed += [_shift(p, ox, oy, f"@S{s + 1}") for p in tile.placed]
    notes = []
    if extras:
        region = box(margin_mm, top_mm, width_mm - margin_mm, length_mm - 4.0)
        more, left = pack_into(region, extras, gap_mm, step_mm, occupied=[p.polygon for p in placed])
        placed += more
        if left:
            notes.append("did not fit: " + ", ".join(i.key for i in left))
    return Sheet(name, width_mm, length_mm, margin_mm, placed, notes, n_sets)


# ============================================================================ phase engineering
def _poly_mask(poly: Polygon, shape: tuple[int, int], ppmm: float, origin=(0.0, 0.0)) -> np.ndarray:
    im = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(im)
    polys = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for g in polys:
        pts = [((x - origin[0]) * ppmm, (y - origin[1]) * ppmm) for x, y in g.exterior.coords]
        d.polygon(pts, fill=1)
        for hole in g.interiors:
            d.polygon([((x - origin[0]) * ppmm, (y - origin[1]) * ppmm) for x, y in hole.coords], fill=0)
    return np.asarray(im, bool)


def sample_piece(labels: np.ndarray, repeat_mm: float, poly_up: Polygon, phase_mm: tuple[float, float],
                 ppmm: float) -> tuple[np.ndarray, np.ndarray]:
    """Labels seen inside ``poly_up`` (piece frame, y up) at ``ppmm``, art upright.
    Returns (label crop, mask)."""
    x0, y0, x1, y1 = poly_up.bounds
    w = max(1, int(math.ceil((x1 - x0) * ppmm)))
    h = max(1, int(math.ceil((y1 - y0) * ppmm)))
    flipped = affinity.scale(poly_up, 1.0, -1.0, origin=(0, 0))   # image rows go down = -y
    mask = _poly_mask(flipped, (h, w), ppmm, origin=(x0, -y1))
    n = labels.shape[0]
    xs = x0 + (np.arange(w) + 0.5) / ppmm
    ys = y1 - (np.arange(h) + 0.5) / ppmm                          # piece y, top row first
    u = ((xs + phase_mm[0]) / repeat_mm * n).astype(np.int64) % n
    v = ((-ys + phase_mm[1]) / repeat_mm * n).astype(np.int64) % n
    return labels[np.ix_(v, u)], mask


def phase_score(crop: np.ndarray, mask: np.ndarray, edge: np.ndarray, dark: int, lights: tuple,
                target_dark: float) -> float:
    """Higher is better. Dark share near the repeat mean, every ink present, and the outer edge
    band carrying both dark and light so the panel edge does not read as one straight line."""
    vals = crop[mask]
    if vals.size == 0:
        return -1e9
    n_ink = int(max(dark, *lights)) + 1
    cov = np.bincount(vals, minlength=n_ink)[:n_ink] / vals.size
    s = -2.0 * abs(cov[dark] - target_dark)
    s += 0.15 * float(np.sum(cov > 0.02))
    ev = crop[edge & mask]
    if ev.size:
        ec = np.bincount(ev, minlength=n_ink)[:n_ink] / ev.size
        s += min(ec[dark], 0.30) + min(sum(ec[i] for i in lights), 0.30)
    return float(s)


def choose_phase(labels: np.ndarray, repeat_mm: float, piece: PieceGeom, *, ppmm: float = 1.0,
                 dark: int = 3, lights: tuple = (0, 2), target_dark: float | None = None,
                 edge_mm: float = 15.0, n_candidates: int = 96, seed: int = 0,
                 avoid: list[tuple[float, float]] | None = None, avoid_mm: float = 60.0
                 ) -> tuple[tuple[float, float], float]:
    """Best (phase_x, phase_y) in mm for a piece's visible area, from a seeded candidate set
    (deterministic). ``avoid`` lists phases already used by a matching piece (L/R pairs) so the
    pair does not print identical."""
    vis = piece.visible
    if target_dark is None:
        target_dark = float(np.mean(labels == dark))
    rng = np.random.default_rng(seed)
    cands = rng.uniform(0, repeat_mm, size=(n_candidates, 2))
    inner = vis.buffer(-edge_mm)
    best, best_s = (0.0, 0.0), -1e18
    for px, py in cands:
        if avoid and any(math.hypot((px - ax + repeat_mm / 2) % repeat_mm - repeat_mm / 2,
                                    (py - ay + repeat_mm / 2) % repeat_mm - repeat_mm / 2) < avoid_mm
                         for ax, ay in avoid):
            continue
        crop, mask = sample_piece(labels, repeat_mm, vis, (px, py), ppmm)
        if inner.is_empty:
            edge = mask
        else:
            _, inner_mask = sample_piece(labels, repeat_mm, inner, (0, 0), ppmm)
            # align inner mask into the outer crop
            x0, y0, x1, y1 = vis.bounds
            ix0, iy0, ix1, iy1 = inner.bounds
            ox = int(round((ix0 - x0) * ppmm))
            oy = int(round((y1 - iy1) * ppmm))
            full = np.zeros_like(mask)
            hh = min(inner_mask.shape[0], mask.shape[0] - oy)
            ww = min(inner_mask.shape[1], mask.shape[1] - ox)
            full[oy:oy + hh, ox:ox + ww] = inner_mask[:hh, :ww]
            edge = mask & ~full
        s = phase_score(crop, mask, edge, dark, lights, target_dark)
        if s > best_s:
            best, best_s = (float(px), float(py)), s
    return best, best_s


def engineer_phases(pieces: list[PieceGeom], labels: np.ndarray, repeat_mm: float, seed: int = 20261113,
                    **kw) -> dict[str, tuple[float, float]]:
    """Phase per instance key ``<id>#<k>``; instances of the same piece avoid each other's phase."""
    out: dict[str, tuple[float, float]] = {}
    for j, pg in enumerate(pieces):
        used: list[tuple[float, float]] = []
        for k in range(pg.quantity):
            ph, _ = choose_phase(labels, repeat_mm, pg, seed=seed + 101 * j + k, avoid=used, **kw)
            used.append(ph)
            out[f"{pg.piece_id}#{k + 1}"] = ph
    return out


# ============================================================================ rendering
def _instance_key(key: str) -> str:
    return key.split("@", 1)[0]


def render_sheet(sheet: Sheet, labels: np.ndarray, repeat_mm: float, hexes: list[str], dpi: float,
                 phases: dict[str, tuple[float, float]], *, bleed_mm: float = 3.0, cutline_mm: float = 0.4,
                 title: str = "", extras_render=None, qc_strip: bool = True) -> Image.Image:
    """Full-resolution RGB image of a sheet. Pieces carry the camo (art upright in the piece
    frame, phase from ``phases``) to ``bleed_mm`` beyond the cut line, with a ``cutline_mm`` grey
    cut guide on the cut line and a small ID inside the seam allowance. Waste is unprinted.
    ``extras_render(draw, placed, ppmm)`` may draw extras (specimens); by default specimens with
    ``ref['camo']`` get camo, others an outline."""
    ppmm = dpi / 25.4
    W = int(round(sheet.width_mm * ppmm))
    H = int(round(sheet.length_mm * ppmm))
    lab = np.full((H, W), UNPRINTED, np.uint8)
    n = labels.shape[0]
    for p in sheet.placed:
        is_piece = isinstance(p.ref, PieceGeom)
        if not is_piece and not (isinstance(p.ref, dict) and p.ref.get("camo")):
            continue
        area = p.polygon.buffer(bleed_mm, join_style="mitre")
        x0, y0, x1, y1 = area.bounds
        cx0, cy0 = max(0, int(math.floor(x0 * ppmm))), max(0, int(math.floor(y0 * ppmm)))
        cx1, cy1 = min(W, int(math.ceil(x1 * ppmm))), min(H, int(math.ceil(y1 * ppmm)))
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        mask_all = _poly_mask(area, (cy1 - cy0, cx1 - cx0), ppmm, origin=(cx0 / ppmm, cy0 / ppmm))
        # sheet mm of each pixel centre -> piece frame (undo translate, then rotate); the sheet frame
        # is the piece frame with y flipped, so art rows follow +y here (upright on the product)
        ph = phases.get(_instance_key(p.key), (0.0, 0.0)) if is_piece else p.ref.get("phase", (0.0, 0.0))
        a = math.radians(-p.rotation)
        ca, sa = math.cos(a), math.sin(a)
        xs = (np.arange(cx0, cx1) + 0.5) / ppmm - p.dx
        for r0 in range(cy0, cy1, 512):                     # row strips: bounded memory at 300 dpi
            r1 = min(cy1, r0 + 512)
            mask = mask_all[r0 - cy0:r1 - cy0]
            if not mask.any():
                continue
            ys = (np.arange(r0, r1) + 0.5) / ppmm - p.dy
            X, Y = np.meshgrid(xs, ys)
            xr = X * ca - Y * sa
            yr = X * sa + Y * ca
            u = (np.floor((xr + ph[0]) / repeat_mm * n).astype(np.int64)) % n
            v = (np.floor((yr + ph[1]) / repeat_mm * n).astype(np.int64)) % n
            sub = lab[r0:r1, cx0:cx1]
            sub[mask] = labels[v[mask], u[mask]]
    # cut-guide lines
    im_lines = Image.new("L", (W, H), 0)
    dl = ImageDraw.Draw(im_lines)
    lw = max(1, int(round(cutline_mm * ppmm)))
    for p in sheet.placed:
        geoms = [p.polygon] if p.polygon.geom_type == "Polygon" else list(p.polygon.geoms)
        for g in geoms:
            pts = [(x * ppmm, y * ppmm) for x, y in g.exterior.coords]
            dl.line(pts, fill=1, width=lw, joint="curve")
    lab[np.asarray(im_lines, bool)] = CUTLINE
    # palette image -> RGB
    lut = np.zeros((256, 3), np.uint8)
    lut[:] = WHITE
    for i, h in enumerate(hexes):
        h = h.lstrip("#")
        lut[i] = [int(h[k:k + 2], 16) for k in (0, 2, 4)]
    lut[CUTLINE] = CUT_RGB
    img = Image.fromarray(lut[lab], "RGB")
    del lab
    d = ImageDraw.Draw(img)
    # IDs in the seam allowance: at the mid-point of the longest cut edge, just inside it
    f_id = _font(3.2 * ppmm)
    for p in sheet.placed:
        if not isinstance(p.ref, PieceGeom):
            continue
        txt = _instance_key(p.key).split("#")[0]
        poly = p.polygon
        sa_band = poly.difference(poly.buffer(-4.5, join_style="mitre"))
        cs = list(poly.exterior.coords)
        segs = sorted(((math.dist(cs[i], cs[i + 1]), i) for i in range(len(cs) - 1)), reverse=True)
        done = False
        for _, i in segs[:6]:
            (ax, ay), (bx, by) = cs[i], cs[i + 1]
            mx, my = (ax + bx) / 2, (ay + by) / 2
            L = math.dist((ax, ay), (bx, by))
            nx, ny = -(by - ay) / L, (bx - ax) / L
            for sgn in (1, -1):
                qx, qy = mx + sgn * nx * 2.4, my + sgn * ny * 2.4
                if sa_band.contains(Point(qx, qy)):
                    tw = d.textlength(txt, font=f_id)
                    d.text((qx * ppmm - tw / 2, qy * ppmm - 1.6 * ppmm), txt, fill=WHITE, font=f_id,
                           stroke_width=max(1, int(0.25 * ppmm)), stroke_fill=TEXT_RGB)
                    done = True
                    break
            if done:
                break
    # extras
    f_small = _font(4.0 * ppmm)
    for p in sheet.placed:
        if isinstance(p.ref, dict):
            x0, y0, x1, y1 = p.polygon.bounds
            label = p.ref.get("label", p.key)
            if p.ref.get("kind") == "qc_strip":
                k = len(hexes)
                cw = (x1 - x0 - 2) / k
                for i, h in enumerate(hexes):
                    rgb = tuple(int(h.lstrip("#")[j:j + 2], 16) for j in (0, 2, 4))
                    d.rectangle([((x0 + 1 + i * cw) * ppmm, (y0 + 1) * ppmm),
                                 ((x0 + 1 + (i + 1) * cw - 1) * ppmm, (y1 - 9) * ppmm)], fill=rgb)
                d.text((x0 * ppmm, (y1 - 7.5) * ppmm), label, fill=TEXT_RGB, font=_font(3.5 * ppmm))
            elif p.ref.get("kind") == "test_square":
                d.rectangle([x0 * ppmm, y0 * ppmm, x1 * ppmm, y1 * ppmm], outline=TEXT_RGB,
                            width=max(1, int(0.3 * ppmm)))
                d.text(((x0 + 4) * ppmm, (y0 + 4) * ppmm), "100 mm", fill=TEXT_RGB, font=_font(6 * ppmm))
                d.text(((x0 + 4) * ppmm, (y0 + 13) * ppmm), "(3.94 in)", fill=TEXT_RGB, font=_font(5 * ppmm))
                d.text(((x0 + 4) * ppmm, (y0 + 22) * ppmm), "measure before", fill=TEXT_RGB, font=_font(4 * ppmm))
                d.text(((x0 + 4) * ppmm, (y0 + 28) * ppmm), "cutting", fill=TEXT_RGB, font=_font(4 * ppmm))
                ax = x0 + 80
                d.line([(ax * ppmm, (y0 + 40) * ppmm), (ax * ppmm, (y0 + 88) * ppmm)], fill=TEXT_RGB,
                       width=max(1, int(0.6 * ppmm)))
                d.polygon([((ax - 4) * ppmm, (y0 + 82) * ppmm), ((ax + 4) * ppmm, (y0 + 82) * ppmm),
                           (ax * ppmm, (y0 + 92) * ppmm)], fill=TEXT_RGB)
                d.text(((x0 + 4) * ppmm, (y0 + 60) * ppmm), "roll / warp", fill=TEXT_RGB, font=_font(4 * ppmm))
            elif not p.ref.get("camo"):
                d.rectangle([x0 * ppmm, y0 * ppmm, x1 * ppmm, y1 * ppmm], outline=CUT_RGB, width=lw)
            if p.ref.get("kind") not in ("qc_strip", "test_square"):
                tw = d.textlength(label, font=f_small)
                if (x1 - x0) * ppmm > tw + 4 * ppmm and p.ref.get("camo"):
                    d.text(((x0 + x1) / 2 * ppmm - tw / 2, (y1 + 0.8) * ppmm), label, fill=TEXT_RGB,
                           font=f_small)
                elif not p.ref.get("camo"):
                    d.text(((x0 + 2) * ppmm, (y0 + 2) * ppmm), label, fill=TEXT_RGB, font=f_small)
    # header: title + note (the 100 mm test square is an extra item, kind "test_square")
    hx = sheet.margin_mm + 2
    d.text((hx * ppmm, 2 * ppmm), title or sheet.name, fill=TEXT_RGB, font=_font(4.2 * ppmm))
    d.text((hx * ppmm, 7.5 * ppmm), "PRINT AT 100 %, face up, top edge first off the roll (warp = image "
           "vertical). Grey line = cut line; camo bleeds 3 mm past it. Unprinted = waste.",
           fill=TEXT_RGB, font=_font(3.0 * ppmm))
    if extras_render:
        extras_render(d, sheet, ppmm)
    return img


def sheet_map(sheet: Sheet, px_per_mm: float = 0.6, labels: np.ndarray | None = None,
              repeat_mm: float = 380.0, hexes: list[str] | None = None,
              phases: dict | None = None) -> Image.Image:
    """Low-res preview of a sheet (optionally with camo) for screenshots."""
    if labels is not None and hexes is not None:
        small_dpi = px_per_mm * 25.4
        return render_sheet(sheet, labels, repeat_mm, hexes, small_dpi, phases or {}, cutline_mm=1.2 / px_per_mm * 0.6)
    W = int(sheet.width_mm * px_per_mm)
    H = int(sheet.length_mm * px_per_mm)
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    for p in sheet.placed:
        d.polygon([(x * px_per_mm, y * px_per_mm) for x, y in p.polygon.exterior.coords],
                  outline=CUT_RGB, fill=(200, 190, 160))
    return im
