"""Blender cloth drape of the CACHE modules (team D). Each module is sewn from flat rectangles into a box (tube +
boxed floor), so the start shape is that box, subdivided to ~10 mm, and Blender's cloth solver inflates it with
internal pressure (stuffed soft goods) and a little shrink at the roll (the closure gathers it). Gravity off
(the contents, not gravity, set a stuffed bag's shape), so the flat panels bulge and the edges pucker.
Output: one npz per module (vertices mm, faces) read by cache_viz3d.py.

    $SCRATCH/bpyenv/bin/python designs/pack_5200/bag_comp/D/module_cloth_bpy.py OUTDIR
"""
import sys
from pathlib import Path

import bpy  # noqa: I001 (bpy first: it provides bmesh)
import bmesh
import numpy as np

# id: (W, D, H) mm of the sewn box below the roll (cache.py modules()); pressure (kPa-like solver units)
MODULES = {
    "MS": (330.0, 110.0, 560.0, 1.2),
    "MC": (250.0, 160.0, 430.0, 1.2),
    "MK": (260.0, 90.0, 280.0, 1.0),
    "MS_liner": (330.0, 150.0, 560.0, 0.4),   # meat mode: the SWAP slab open, half-filled, sagging
}


def run(out: Path, frames=36):
    out.mkdir(parents=True, exist_ok=True)
    for mid, (W, D, H, pr) in MODULES.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.frame_start, sc.frame_end = 1, frames
        sc.use_gravity = False      # stuffed by its contents: pressure, not gravity, sets the shape
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, H / 2000 + 0.002))
        ob = bpy.context.active_object
        ob.scale = (W / 1000, D / 1000, H / 1000)
        bpy.ops.object.transform_apply(scale=True)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=int(max(W, H) / 14), use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(ob.data)
        bm.free()
        cl = ob.modifiers.new("cloth", "CLOTH")
        s = cl.settings
        s.quality = 6
        s.mass = 0.08
        s.tension_stiffness = 60.0
        s.compression_stiffness = 12.0
        s.shear_stiffness = 6.0
        s.bending_stiffness = 0.6
        s.use_pressure = True
        s.uniform_pressure_force = pr
        s.shrink_min = 0.02
        cl.collision_settings.use_self_collision = False
        for f in range(1, frames + 1):
            sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        V = np.array([v.co[:] for v in me.vertices]) * 1000.0
        F = np.array([p.vertices[:] for p in me.polygons])
        ev.to_mesh_clear()
        np.savez(out / f"module_{mid}.npz", V=V, F=F, dims=np.array([W, D, H]))
        print(mid, V.shape, F.shape, V.min(0).round(1), V.max(0).round(1), flush=True)


if __name__ == "__main__":
    run(Path(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else sys.argv[1]))
