# BL-057 Wire the BL-056 results into the kit, register and frame build guide

**Agent:** manufacturing-engineer · **Size:** S · **Depends on:** BL-056

Goal: no document carries stale numbers after BL-056 (Ti hip mount redrawn; US2 joint blocks strengthened).
Sources: `designs/pack_5200/analysis/hip_mount_bl056.md` / `.json` (`tests`, `fe`), `clevis_bl056.json` (`kit`,
`gauges`, `joint`, `mass`), `huntkit/mass/ledger.py` (`bl056_update`), `docs/DECISIONS.md` 2026-11-21 rows.

1. **CLEVIS-SHARE A/B** in `designs/pack_5200/physical_test_kit.py` (and the generated `outputs/release/test_kit/`):
   loads, vectors, cycles and microstrain lines read from `clevis_bl056.json`, not BL-053's (proof 1103.9 / 642.9 N,
   cycle peak 735.9 / 428.6 N). The US2 lines of MT-1cr follow the same file.
2. **HB-6** (6 coupons, pull along build z at 60 C, pass >= 513 N each) and **HB-6b** (snug screws, gauge on the most
   loaded screw, 60 / 96 / 180 microstrain at 534 / 854 / 1601 N, then 1e5 cycles) from `hip_mount_bl056.json`.
   Add to HB-6b a second run with the lumbar pad offset 20 mm SIDEWAYS (orchestrator call 2026-11-21: reopen the
   mount legs if that run's gauge reads above its line). BL-056 published no line for it: derive it from the BL-056
   models and mark the derivation ASSUMPTION.
3. **Frame README and BUILD_H1** (`designs/pack_5200/frame_h1_build.py`): clevis 15.71 g, assembled 1069.4 g, nut
   trap 1 mm inboard (144.8-150), HOLD on ordering the Ti hip mount lifted (D50 x 3, 8 holes, 34.3 g).
   `designs/pack_5200/print/README.md`: Ti mount 20.2 -> 34.3 g. Numbers from the JSON / ledger, never typed.
4. **BL-055B leftovers:** the gauge-sign note (T1 at the US2 root reads tension) and the legend overlap in the kit
   order-of-work figure.
5. **Guard:** `huntkit/gendesign/lugs.py` must not let a gendesign re-run overwrite the redrawn mount STL; test.
6. Shopping list and test count.

Deliverables: `designs/pack_5200/physical_test_kit.py`, `designs/pack_5200/frame_h1_build.py`,
`huntkit/gendesign/lugs.py` (+ the call in `huntkit/gendesign/cli.py`), `tests/test_bl057_wiring.py` (+ the stale
assertions in `tests/test_physical_test_kit.py`, `tests/test_bl052_clevis_handoff.py`), regenerated
`tests_physical/test_register.csv`, `outputs/release/test_kit/`, `print/frame_h1/README.md`, `BUILD_H1.md`,
`print/README.md`. Screenshots `outputs/screens/20261121_BL057_<n>.png`. Do not commit.
