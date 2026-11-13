# BL-045 Crown tube with the B-25 mitre; spine clamp; IM/US fairlead clearance; loose island

**Agent:** structural-fea-engineer · **Size:** M · **Beside:** BL-044

1. **Crown tube:** BL-043 put B-25's 45° mitre and its 25 mm necked run under the 38 mm sleeve (`corrie_f.b25_topology`, sketch SK-12). Re-check `crown_tube_guy_loop` for the real bearing (sleeve plus mitre layers, pull direction), and confirm or correct SF 1.36 / 1.27.
2. **Spine clamp:** the frame files have no spine-clamp drawing. BL-043 assumed a 15 mm half-width and a 12 mm collar, plus a pawl housing 20 mm tall and ±18 mm wide. Produce the real dimensions from the frame model, publish them as constants, and say whether B-25's clearances hold.
3. **IM/US fairleads:** 10 of them still have 1.9 mm under the pin and an 18 mm throat. Find out what passes round each pin: carabiners, hooks or webbing (see `corrie_f.py`, the mfg BOM and `attach_system`). If anything wraps a pin, give it a clearance envelope like the hinge's, with strength re-checked.
4. **Lower-half export:** it drops a 571 mm³ loose island at frame (84, −0.4, 225). Find out what it is and fix it.
5. **Stale records:** `rev_c_verification` hinge cheek record (2.97 → re-run); "fairleads present 1.000" in `h1_buckling.md` and `frame_fixed.py:712`.

Don't edit `patterns_corrie_f_rev3*.py`, `mfg_corrie_f_rev3.py` or `concepts/corrie_f.py`; the pack-designer is in them. Publish constants for them to import, and run the full suite.
