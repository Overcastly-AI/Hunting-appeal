"""Cycles render of printed frame bodies side by side (runs inside the bpy venv; no scipy / gendesign imports).
Called by huntkit.gendesign.frame_h1.render with a JSON manifest of STL files and materials."""
import json
import math
from pathlib import Path


def main(argv):
    """Inside the bpy venv: <manifest.json> <out_png> <samples> <caption> <sub> <az> <el> <zoom>."""
    import bpy
    from huntkit.viz3d import cycles_render as CR
    man = json.loads(Path(argv[0]).read_text())
    out_png, samples, cap, sub = Path(argv[1]), int(argv[2]), argv[3], argv[4]
    az, el, zoom = float(argv[5]), float(argv[6]), float(argv[7])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    res = (1200, 900)
    sc = CR.setup_scene(samples, res, 2)
    mats = {}
    for key, base_, rough, metal, coat, bump in (("carbon", "#101112", 0.28, 0.0, 0.9, 0.0),
                                                ("printed", "#4b4945", 0.72, 0.0, 0.0, 0.35),
                                                ("today", "#2e2d2b", 0.6, 0.0, 0.0, 0.2),
                                                ("ti", "#9a9a9e", 0.32, 1.0, 0.0, 0.0)):
        mt = bpy.data.materials.new(key)
        mt.use_nodes = True
        CR.solid(mt, CR.hexlin(base_), rough, metallic=metal, coat=coat, noise_bump=bump)
        mats[key] = mt
    objs = []
    for item in man["files"]:
        bpy.ops.wm.stl_import(filepath=item["path"])
        ob = bpy.context.selected_objects[0]
        ob.scale = (0.001, 0.001, 0.001)
        ob.data.materials.clear()
        ob.data.materials.append(mats[item["mat"]])
        for p in ob.data.polygons:
            p.use_smooth = True
        objs.append(ob)
    bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    lo, hi = CR.visible_bounds(objs)
    floor.location = (0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), (man.get("floor_z", lo[2] * 1000)) / 1000 - 0.001)
    cd.angle_y = math.radians(28.0)
    pos, tgt = CR.fit_camera(lo, hi, az, el, 28.0, res[0] / res[1], zoom)
    cam.location = pos
    CR._aim(cam, tgt)
    rig = (CR._area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2), CR._area("fill", 22.0, 2.4, (0.88, 0.93, 1.0), 1.6),
           CR._area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0))
    CR.place_rig(rig, az, tgt, max(1.0, 0.75 * math.dist(pos, tgt)))
    raw = out_png.with_name("_raw_" + out_png.name)
    sc.render.filepath = str(raw)
    bpy.ops.render.render(write_still=True)
    CR.composite(raw, out_png, cap, sub)
    CR.shrink_png(out_png)
    raw.unlink(missing_ok=True)
    print("RENDERED", out_png, flush=True)


