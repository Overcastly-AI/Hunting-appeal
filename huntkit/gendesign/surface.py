"""Density field -> smooth watertight mesh -> STL / 3MF, plus print-orientation (overhang) analysis.

marching cubes (scikit-image) on the padded density field at iso 0.5 -> Taubin smoothing (no
shrink) -> exact boolean union with analytic socket sleeves and subtraction of the tube bores
(manifold3d), so the bond surfaces are true cylinders (they still get reamed: see the print notes).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

try:
    import manifold3d as m3d
except ImportError:      # pragma: no cover
    m3d = None


def field_to_mesh(field3: np.ndarray, h: float, x0, level: float = 0.5, smooth_iters: int = 12,
                  upsample: int = 2) -> trimesh.Trimesh:
    from scipy import ndimage
    from skimage.measure import marching_cubes
    f = np.pad(field3, 1, constant_values=0.0)
    if upsample > 1:
        f = ndimage.zoom(f, upsample, order=1)
        f = ndimage.gaussian_filter(f, 0.6)
    hh = h / upsample
    v, faces, _, _ = marching_cubes(f, level=level, spacing=(hh, hh, hh))
    off = np.asarray(x0, float) - h + 0.5 * h     # pad (one voxel) + element-centre sampling
    v = v + off
    mesh = trimesh.Trimesh(v, faces, process=True)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.merge_vertices()
    if smooth_iters:
        trimesh.smoothing.filter_taubin(mesh, lamb=0.5, nu=-0.53, iterations=smooth_iters)
    trimesh.repair.fix_normals(mesh)
    return mesh


def _to_manifold(mesh: trimesh.Trimesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                                 tri_verts=np.asarray(mesh.faces, np.uint32)))


def _from_manifold(man) -> trimesh.Trimesh:
    mm = man.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)


def _frame(axis):
    a = np.asarray(axis, float); a /= np.linalg.norm(a)
    ref = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    b = np.cross(a, ref); b /= np.linalg.norm(b)
    c = np.cross(a, b)
    return np.column_stack([b, c, a])     # local z -> axis


def cylinder(p0, axis, length, r, segments=64):
    """Solid cylinder from p0 along axis (manifold)."""
    cyl = m3d.Manifold.cylinder(float(length), float(r), float(r), segments)
    R = _frame(axis)
    M = np.zeros((3, 4)); M[:, :3] = R; M[:, 3] = np.asarray(p0, float)
    return cyl.transform(M)


def boolean_body(body: trimesh.Trimesh, adds=(), subs=()) -> trimesh.Trimesh:
    """body U adds - subs. adds/subs: list of manifold solids (see ``cylinder``)."""
    if m3d is None:
        return body
    try:
        man = _to_manifold(body)
        if man.status() != m3d.Error.NoError if hasattr(man, "status") else False:
            raise ValueError("non-manifold body")
    except Exception:
        man = None
    for a in adds:
        man = a if man is None else man + a
    for s in subs:
        man = man - s
    return _from_manifold(man)


def export(mesh: trimesh.Trimesh, path_stem: Path, formats=("stl", "3mf")) -> list[str]:
    out = []
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    for f in formats:
        p = path_stem.with_suffix("." + f)
        try:
            mesh.export(p)
            out.append(str(p))
        except Exception as e:      # 3MF needs lxml/networkx; skip quietly if absent
            if f == "stl":
                raise
            print(f"  ({f} export skipped: {e})")
    return out


# ----------------------------------------------------------------------------- orientation
CANDIDATE_DIRS = {"+z": (0, 0, 1), "-z": (0, 0, -1), "+x": (1, 0, 0), "-x": (-1, 0, 0),
                  "+y": (0, 1, 0), "-y": (0, -1, 0)}


def overhang_area(mesh: trimesh.Trimesh, build_dir, max_overhang_deg: float = 45.0) -> float:
    """Down-facing area (mm^2) steeper than the allowed overhang (angle measured from horizontal:
    a face needs support when its normal points down within (90 - limit) deg of -build_dir).
    Faces touching the build plate (lowest 0.5 mm) are excluded."""
    d = np.asarray(build_dir, float); d /= np.linalg.norm(d)
    n = mesh.face_normals
    cosang = n @ (-d)
    need = cosang > np.cos(np.radians(90 - max_overhang_deg))
    zc = mesh.triangles_center @ d
    need &= zc > zc.min() + 0.5
    return float(mesh.area_faces[need].sum())


def best_orientation(mesh: trimesh.Trimesh, max_overhang_deg=45.0, prefer=None) -> dict:
    rows = {k: overhang_area(mesh, v, max_overhang_deg) for k, v in CANDIDATE_DIRS.items()}
    best = min(rows, key=rows.get) if prefer is None else prefer
    return {"by_dir": rows, "best": best, "support_area_mm2": rows[best],
            "support_frac": rows[best] / mesh.area}


def orient_to(mesh: trimesh.Trimesh, build_dir) -> trimesh.Trimesh:
    """Copy rotated so ``build_dir`` becomes +Z and the part sits on z = 0."""
    m = mesh.copy()
    d = np.asarray(build_dir, float)
    # axis-aligned rotation (permutation with signs) so the part stays square to the plate
    k = int(np.argmax(np.abs(d)))
    sgn = np.sign(d[k])
    R = np.eye(4)
    if k == 2:
        R[:3, :3] = np.diag([1, sgn, sgn])
    elif k == 0:
        R[:3, :3] = np.array([[0, 0, -sgn], [0, 1, 0], [sgn, 0, 0]])
    else:
        R[:3, :3] = np.array([[1, 0, 0], [0, 0, -sgn], [0, sgn, 0]])
    m.apply_transform(R)
    m.apply_translation(-m.bounds[0])
    return m
