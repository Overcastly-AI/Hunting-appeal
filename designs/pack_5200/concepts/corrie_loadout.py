"""CORRIE loadout / packing study (2026-11-08). Study code: CORRIE geometry is only READ (no change to corrie.py).

    python designs/pack_5200/concepts/corrie_loadout.py            # numbers -> outputs/loadout/loadout_results.json
    python designs/pack_5200/concepts/corrie_loadout.py --render   # + PNG screens

Inputs: designs/pack_5200/loadouts.yaml (three canonical loadouts, every number cited or ASSUMPTION),
research docs/research/hunting_loadouts.md, CORRIE (concepts/corrie.py, rev B).
Write-up: designs/pack_5200/analysis/loadout_study.md.

Model (a zone + layer mass model, deliberately simple):
* The main bag is split into two half-depth COLUMNS along z: F (frame half) and A (aft half). Each column's
  capacity at height z is half of CORRIE's rev B section area, scaled by the cloth-sim bulge factor so that the
  full bag holds the simulated 88.4 L (rev B sim, fill cases 88.9 / 89.0 / 87.2 L; the flat-panel rule gives
  ~75.9 L, corrie.py REVS note). Items assigned to a column are stacked bottom-up in band order (low, mid, high);
  each item occupies its effective volume (packed volume / fill efficiency) and gets the z-slot and the half-section
  centroid at that height. Light loads therefore settle low and the roll-top rolls down (no fake height).
* External zones (wings, top pouch, hipbelt pockets, chest harness, hands, new proposed pockets) have a capacity,
  an interior envelope (item dims must fit) and a fixed position.
* Bag-load CG = everything carried by the bag (columns, pouch, wings, door pocket, sleeves). Hipbelt, chest and hands
  are carried by the hips / body and are excluded, as in HA-LS-1 (load_standard.md rev C, bag CG).
  Rev C check: geometric CG + the cloth-sim peel (sim fill CG - geometric uniform-fill CG, same rev B body).
* Access class (0 on body ... 5 roll-top) from the zone; requirement from the item's access frequency.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit import materials as MAT  # noqa: E402

LOADOUT_YAML = ROOT / "designs" / "pack_5200" / "loadouts.yaml"
OUT = ROOT / "outputs" / "loadout"

# ----------------------------------------------------------------------------- constants (each traced)
# Rev B.1 (2026-11-09): CONVERGED cloth sims corrie_PR{15,19,23}c (corrie_body.md section 5b; pouch 1 kg + 85 mm scope
# in the left wing sleeve, 6 mm contact rounding). Contents (volume) CG y of the deformed bag; the pouch / scope masses
# are added by this model itself, so the volume centroid (not the mass-weighted sim CG) is the peel basis.
SIM_FILL_L = (88.1, 88.4, 87.0)            # outputs/clothsim/corrie_PR{15,19,23}c/results.json fill closed_L
SIM_FILL_CG = {15: 190.9, 19: 172.0, 23: 130.8}   # same, fill contents_cg_mm[1]
SIM_MEAT_CG = {15: 184.0, 19: 166.8, 23: 133.9}   # same, meat contents_cg_mm[1]
REV_B_SIM = {"fill_L": (88.9, 89.0, 87.2), "fill_cg": {15: 190.4, 19: 172.3, 23: 136.4},   # rev B (2026-11-08,
             "meat_cg": {15: 185.6, 19: 168.5, 23: 139.2}}                                 # 7 of 9 not converged)
REV_C = {"bag_y": 205.0, "meat_y": 190.0, "z_max": 590.0}  # load_standard.md §4.2 and T9 (z <= 590)
RATED_KG = 68.0                             # DECISIONS 2026-11-01 (150 lb)
FLOAT_MEAT_MAX_KG = 53.0                    # DECISIONS 2026-11-06 float FEA (US1 fatigue)
FLOAT_GAP_MM = 170.0                        # B-24 middle loop (DECISIONS 2026-11-06)
PACK_BASE_G = 3725.0                        # corrie_body.md §4 (CORRIE pack total)
EFF_SOFT, EFF_RIGID, EFF_POCKET = 0.90, 0.75, 0.85   # ASSUMPTION: fill efficiency (packed volume / space used)
MEAT_KG_PER_L = 1.0                         # ASSUMPTION: boned meat in game bags incl. voids (~1.05 kg/L tissue)
MIN_TOP_Z = CO.DOOR["z_hinge"]              # ASSUMPTION: the roll cannot close below the door hinge band (z 650)
POUCH_ABOVE_TOP = 75.0                      # roll 22 + clip 18 + half pouch 35 (corrie.pouch_cg_shift)
ACCESS_NAMES = {0: "on body", 1: "pack on", 2: "pack on, behind", 3: "pack off, outside",
                4: "pack off, door", 5: "pack off, roll-top / unpack"}
REQUIRED = {"constant": 1, "hourly": 1, "glassing": 4, "weather": 4, "kill": 4, "emergency": 4,
            "daily": 5, "camp": 5}   # DECISION (this study): constant/hourly must be reachable with the pack on
FREQ_ORDER = ["constant", "hourly", "glassing", "weather", "kill", "emergency", "daily", "camp"]


@dataclass
class Zone:
    id: str
    name: str
    kind: str                     # body | hip | strap | bagcol | wing | pouch | fixed
    access: int
    cap_L: float | None = None    # None = unlimited
    env_mm: tuple | None = None   # interior envelope (sorted large -> small); item dims must fit
    in_bag: bool = True           # counts in the bag-load CG
    pos: tuple | None = None      # fixed (x, y, z) for fixed zones
    pool: str | None = None       # shares capacity with another zone
    col: str | None = None        # 'F' or 'A' for bag columns
    band: int = 0
    note: str = ""


def corrie_geom():
    c = CO.make()
    st = c.profile()
    z = st[:, 0]
    area = 2 * st[:, 1] * st[:, 3] * st[:, 4]          # [mm2] section area (box k = 1, dome blended)
    v_geo = float(np.trapezoid(area, z)) / 1e6
    kb = float(np.mean(SIM_FILL_L)) / v_geo             # bulge factor flat-panel rule -> sewn (sim) volume
    half = 0.5 * area * kb
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (half[1:] + half[:-1]) * np.diff(z))]) / 1e6   # L per column
    return {"c": c, "z": z, "a": st[:, 1], "yf": st[:, 2], "d": st[:, 3], "half_area": half, "cum_L": cum,
            "kb": kb, "v_geo": v_geo, "v_sewn": float(np.mean(SIM_FILL_L)), "zc": c.z_c, "zfill": c.z_fill}


G = corrie_geom()


def col_z(v_L):
    """Height in a column at cumulative volume v_L (from the floor)."""
    return float(np.interp(v_L, G["cum_L"], G["z"]))


def col_y(col, z):
    yf = float(np.interp(z, G["z"], G["yf"]))
    d = float(np.interp(z, G["z"], G["d"]))
    return yf + (0.25 if col == "F" else 0.75) * d


def a_at(z):
    return float(np.interp(z, G["z"], G["a"]))


def y_front(z):
    return float(np.interp(z, G["z"], G["yf"] + G["d"]))


# ----------------------------------------------------------------------------- zones
HIP_TODAY_ENV = (145, 92, 50)     # ASSUMPTION: HP-01 face 180/140 x 110 less 8 mm SA and the #8 zip; gusset 55 less SA
HIP_AFTER_ENV = (175, 112, 55)    # IMP-5: face 200/160 x 130, gusset 60


ROLL_MIN_Z_BLADDER = 990.0   # ASSUMPTION (corrie.HYDRO): with a bladder in the IMP-2 sleeve (top z 975) the roll closes >= z 990


def zones_integrated(size="M"):
    """CORRIE rev B.1 (DECISIONS 2026-11-09): the adopted pockets as built in corrie.py, belt B of ``size``."""
    hl = CO.hip_layout(size)
    hy, dp, sp = CO.HYDRO, CO.DOOR_POCKET, CO.STRAP_POCKET
    zw = 375.0
    Z = [
        Zone("chest", "chest harness (not ours)", "body", 0, None, None, False),
        Zone("hands", "hands / sling", "body", 0, None, None, False),
        Zone("strap_clip", "shoulder-strap webbing clip", "strap", 1, 0.20, (110, 60, 30), False),
        Zone("strap_pocket", "IMP-6 shoulder-strap phone pocket", "strap", 1,
             round(sp["h"] * sp["w"] * sp["stretch_depth"] / 1e6, 3), CO.bag_pockets()[3]["interior_mm"], False),
        Zone("hip_L", f"IMP-5 hipbelt pocket L ({size})", "hip", 1, hl["L"]["volume_L"], hl["L"]["interior_mm"], False,
             (-150, -60, 40)),
        Zone("bottle_hip", "IMP-3 bottle holster, belt B right wing", "hip", 1, 2.0, CO.holster()["interior_mm"], False,
             (150, -40, 70)),
        Zone("wing_L", "under left wing", "wing", 3, 6.0, (600, 200, 150), True, (-1, None, zw)),
        Zone("wing_R", "under right wing", "wing", 3, 6.0, (600, 200, 150), True, (1, None, zw)),
        Zone("top_pouch", "top pouch 4.0 L", "pouch", 3, 4.0, (300, 195, 65), True),
        Zone("scope_sleeve_L", "IMP-1 padded scope sleeve, left wing", "wing", 3, 5.0, (430, 160, 150), True, (-1, None, zw),
             pool="wing_L"),
        Zone("hydro_sleeve", "IMP-2 hydration sleeve (hung, z 545-975)", "fixed", 1, 3.0, (430, 240, 60), True,
             (0, None, CO.bag_pockets()[1]["bladder_centre_z"])),
        Zone("door_pocket", "IMP-4 zipped pocket inside the door", "fixed", 4,
             round(sum([0]) + (dp["w"] - 8) * (dp["h"] - 8) * (dp["bellows"] - 2) / 1e6, 2), CO.bag_pockets()[2]["interior_mm"],
             True, (0, "door", 0.5 * sum(dp["z"]))),
    ]
    if hl["R"]:
        Z.append(Zone("hip_R", f"IMP-5 hipbelt pocket R ({size})", "hip", 1, hl["R"]["volume_L"], hl["R"]["interior_mm"],
                      False, (150, -60, 40)))
    for col in ("F", "A"):
        for b, nm in enumerate(("low", "mid", "high")):
            Z.append(Zone(f"bag_{col}_{nm}", f"main bag {'frame' if col == 'F' else 'aft'} half, {nm}", "bagcol",
                          5, None, (900, 380, 260), True, col=col, band=b))
    return {z.id: z for z in Z}


def zones(config="today"):
    if str(config).startswith("integrated"):
        return zones_integrated(config.split(":")[1] if ":" in config else "M")
    after = config == "after"
    zw = 375.0                    # wing centre (M-01 z 150-600, corrie_body.md §4)
    Z = [
        Zone("chest", "chest harness (not ours)", "body", 0, None, None, False),
        Zone("hands", "hands / sling", "body", 0, None, None, False),
        Zone("strap_clip", "shoulder-strap webbing clip", "strap", 1, 0.20, (110, 60, 30), False,
             note="device with its own carabiner (INREACH lists one)"),
        Zone("hip_L", "hipbelt pocket L", "hip", 1, 1.30 if after else 0.97, HIP_AFTER_ENV if after else HIP_TODAY_ENV,
             False, (-150, -60, 40)),
        Zone("hip_R", "hipbelt pocket R", "hip", 1, 1.30 if after else 0.97, HIP_AFTER_ENV if after else HIP_TODAY_ENV,
             False, (150, -60, 40)),
        Zone("wing_L", "under left wing", "wing", 3, 6.0, (600, 200, 150), True, (-1, None, zw),
             note="ASSUMPTION 6 L usable under a 200 x 450 wing, items up to 150 mm thick, 150 mm overhang"),
        Zone("wing_R", "under right wing", "wing", 3, 6.0, (600, 200, 150), True, (1, None, zw)),
        Zone("top_pouch", "top pouch 4.0 L", "pouch", 3, 4.0, (300, 195, 65), True),
    ]
    for col in ("F", "A"):
        for b, nm in enumerate(("low", "mid", "high")):
            Z.append(Zone(f"bag_{col}_{nm}", f"main bag {'frame' if col == 'F' else 'aft'} half, {nm}", "bagcol",
                          5, None, (900, 380, 260), True, col=col, band=b))
    if after:
        Z += [
            Zone("scope_sleeve_L", "IMP-1 padded scope sleeve, left wing", "wing", 3, 5.0, (430, 160, 150), True,
                 (-1, None, zw), pool="wing_L", note="quiet: spotter cannot touch hardware"),
            Zone("hydro_sleeve", "IMP-2 hydration sleeve B-09 (hung above IM3)", "fixed", 1, 3.0, (430, 240, 60), True,
                 (0, None, 640)),
            Zone("bottle_hip", "IMP-3 hipbelt bottle holster R", "hip", 1, 2.0, (230, 95, 95), False, (170, -40, 70)),
            Zone("door_pocket", "IMP-4 zipped kill-kit pocket inside the door", "fixed", 4, 4.0, (300, 240, 60), True,
                 (0, "door", 450)),
        ]
    return {z.id: z for z in Z}


# ----------------------------------------------------------------------------- loadouts
def load_yaml(path=LOADOUT_YAML):
    return yaml.safe_load(Path(path).read_text())


def expand(data, key, archery=False, meat_day=False):
    """Item rows of one loadout: list of dicts with qty applied (qty may be fractional for food)."""
    lo = data["loadouts"][key]
    items = dict(lo["items"])
    if archery and lo.get("archery_swap"):
        for k in lo["archery_swap"]["remove"]:
            items.pop(k, None)
        items.update(lo["archery_swap"]["add"])
    rows = []
    for iid, q in items.items():
        it = copy.deepcopy(data["items"][iid])
        it["id"] = iid
        if meat_day and it["cat"] == "food" and iid.startswith("food_day"):
            q = 0.5                 # ASSUMPTION: last day, half a day of food left on the pack-out
        if meat_day and iid == "game_bags_elk" or meat_day and iid == "game_bags_small":
            continue                # the game bags now hold the meat
        it["qty"] = q
        it["mass_tot"] = it["mass_g"] * q
        it["vol_tot"] = it["vol_L"] * q
        rows.append(it)
    return rows


def split_units(rows, ids=("bottle_1L",)):
    """Rev B.1: carry each unit of a multi-unit item separately (two 1 L bottles go to two places)."""
    out = []
    for r in rows:
        q = r["qty"]
        if r["id"] in ids and q > 1 and float(q).is_integer():
            for i in range(int(q)):
                u = dict(r)
                u.update(qty=1, mass_tot=r["mass_g"], vol_tot=r["vol_L"], id=r["id"] if i == 0 else f"{r['id']}#{i + 1}")
                out.append(u)
        else:
            out.append(r)
    return out


def fits_env(dims, env):
    if env is None:
        return True
    d = sorted(dims, reverse=True)
    e = sorted(env, reverse=True)
    return all(a <= b + 1e-6 for a, b in zip(d, e))


def eff(it):
    return EFF_RIGID if it.get("rigid") else EFF_SOFT


# ----------------------------------------------------------------------------- packer
@dataclass
class Packed:
    rows: list
    zones: dict
    used: dict
    cols: dict = field(default_factory=dict)
    unplaced: list = field(default_factory=list)
    meat: dict | None = None
    float_mode: bool = False


def pack(rows, config="today", force=None, meat_kg=0.0):
    """Assign items to zones, stack the bag columns, give every item a position and an access class.
    ``force``: {item_id: [zone prefs]} override (spotter options). ``meat_kg`` > 0: pack-out case."""
    Z = zones(config)
    used = {k: 0.0 for k in Z}
    col_items = {"F": [], "A": []}
    out = []
    meat = None
    col_cap = G["cum_L"][-1]
    reserve = {"F": 0.0, "A": 0.0}
    fixedF = 0.0
    if meat_kg > 0:
        mv = meat_kg / MEAT_KG_PER_L / EFF_SOFT
        meat = {"kg": meat_kg, "vol_eff_L": mv}
        reserve = {"F": min(mv, col_cap), "A": max(0.0, mv - col_cap)}
    for it in rows:
        it = dict(it)
        prefs = (force or {}).get(it["id"], it["pref"])
        if meat_kg > 0:   # meat rides against B-01 (IM1-IM3): frame-half gear moves aft
            prefs = [p.replace("bag_F_", "bag_A_") if p.startswith("bag_F_") else p for p in prefs]
        placed = None
        for p in prefs:
            if p not in Z:
                continue
            z = Z[p]
            if z.kind == "body":
                placed = p
                break
            if not fits_env(it["dims_mm"], z.env_mm):
                continue
            ev = it["vol_tot"] / (EFF_POCKET if z.kind in ("hip", "strap", "pouch", "fixed", "wing") else eff(it))
            pool = z.pool or p
            if z.kind == "bagcol":
                used_col = sum(r["vol_eff"] for r in col_items[z.col]) + reserve[z.col]
                if used_col + ev <= col_cap + 1e-9:
                    placed = p
                    it["vol_eff"] = ev
                    col_items[z.col].append(it)
                    break
                continue
            if z.cap_L is None or used[pool] + ev <= Z[pool].cap_L + 1e-9:
                if z.kind == "fixed":   # sleeve / door pocket sit INSIDE the main bag: they take column volume
                    colk = "A" if z.pos[1] == "door" else "F"
                    hung = meat is not None and colk == "F" and str(config).startswith("integrated")
                    if hung:
                        # rev B.1: the bladder stays in its hung sleeve on the pack-out; the meat packs round it and its
                        # overflow from the frame half moves aft (the total-volume check below still applies)
                        fixedF += ev
                        reserve["F"] += ev
                        over = reserve["F"] - col_cap
                        if over > 0:
                            reserve["F"] -= over
                            reserve["A"] += over
                    elif sum(r["vol_eff"] for r in col_items[colk]) + reserve[colk] + ev > col_cap + 1e-9:
                        continue
                    else:
                        reserve[colk] += ev
                used[pool] += ev
                placed = p
                it["vol_eff"] = ev
                break
        if placed is None:   # spill into whichever bag column has room (soft or rigid alike)
            for colk in ("A", "F"):
                ev = it["vol_tot"] / eff(it)
                if sum(r["vol_eff"] for r in col_items[colk]) + reserve[colk] + ev <= col_cap:
                    placed = f"bag_{colk}_high"
                    it["vol_eff"] = ev
                    it["spilled"] = True
                    col_items[colk].append(it)
                    break
        it["zone"] = placed
        out.append(it)
    # ---- meat: first in column F, overflow on top of column A gear is not allowed -> float mode
    float_mode = False
    if meat:
        gear = sum(r["vol_eff"] for r in col_items["F"] + col_items["A"])
        unplaced_v = sum(r["vol_tot"] / eff(r) for r in out if r["zone"] is None)
        free = 2 * col_cap - gear - reserve["F"] - reserve["A"]     # reserve = meat + in-bag pockets
        meat["bag_free_L"] = round(free, 1)
        if unplaced_v == 0 and free >= -1e-9:
            meat["mode"] = "in bag (IM1-IM3 against B-01)"
        else:
            float_mode = True
            meat["mode"] = f"float ({FLOAT_GAP_MM:.0f} mm gap, meat on US1/US2 between frame and bag)"
    # ---- stack the columns
    cols = {}
    for colk in ("F", "A"):
        lst = sorted(col_items[colk], key=lambda r: Z[r["zone"]].band if r["zone"] in Z else 2)
        v = 0.0
        if meat and not float_mode and colk == "F":
            v1 = meat["vol_eff_L"]
            capF = col_cap - fixedF
            if v1 > capF:   # meat overflows F: the rest sits low in A (ASSUMPTION: cinched against the F stack)
                meat["vol_F_L"], meat["vol_A_L"] = capF, v1 - capF
                v1 = capF
            else:
                meat["vol_F_L"], meat["vol_A_L"] = v1, 0.0
            meat["z_F"] = (col_z(0.0), col_z(v1))
            v = v1
        if meat and not float_mode and colk == "A" and meat.get("vol_A_L", 0) > 0:
            meat["z_A"] = (col_z(0.0), col_z(meat["vol_A_L"]))
            v = meat["vol_A_L"]
        for r in lst:
            v0, v = v, v + r["vol_eff"]
            z0, z1 = col_z(min(v0, col_cap)), col_z(min(v, col_cap))
            r["slot"] = (colk, z0, z1)
            zm = 0.5 * (z0 + z1)
            r["pos"] = (0.0, col_y(colk, zm), zm)
        cols[colk] = {"vol_eff_L": v, "z_top": col_z(min(v, col_cap)), "over_L": max(0.0, v - col_cap)}
    top = max(MIN_TOP_Z, cols["F"]["z_top"], cols["A"]["z_top"])
    if any(r["zone"] == "hydro_sleeve" for r in out) and str(config).startswith("integrated"):
        top = max(top, ROLL_MIN_Z_BLADDER)
    # ---- positions of external zones
    for r in out:
        z = Z.get(r["zone"])
        if z is None or z.kind == "bagcol":
            continue
        if z.kind in ("body", "hip", "strap"):
            r["pos"] = z.pos if z.pos else None
        elif z.kind == "wing":
            # ASSUMPTION: every item under a wing rides at the wing centre height (z 375), outboard of the gusset
            side = -1 if r["zone"].endswith("_L") else 1
            zm = 375.0
            t = sorted(r["dims_mm"])[1]
            r["pos"] = (side * (a_at(zm) + t / 2), float(np.interp(zm, G["z"], G["yf"])) + 100.0, zm)
        elif z.kind == "pouch":
            r["pos"] = (0.0, CO.pouch_cg_shift(G["c"])["yc"], top + POUCH_ABOVE_TOP)
        elif z.kind == "fixed":
            x, y, zz = z.pos
            if y == "door":
                y = y_front(zz) - 30.0
            elif y is None:
                y = float(np.interp(zz, G["z"], G["yf"])) + 25.0
            r["pos"] = (x, y, zz)
    # ---- access class
    for r in out:
        z = Z.get(r["zone"])
        if z is None:
            r["access_cls"] = 9
        elif z.kind == "bagcol":
            col, z0, z1 = r["slot"]
            # reachable through the open door: aft half, the item reaches above the sill and starts below the hinge
            # (D3: sill 75 mm above the floor, "low gear comes out without unpacking")
            inside_door = col == "A" and z1 > CO.DOOR["z_lo"] and z0 < CO.DOOR["z_hinge"] - 30
            r["access_cls"] = 4 if inside_door else 5
        else:
            r["access_cls"] = z.access
        r["required"] = REQUIRED[r["access"]]
        r["ok"] = r["access_cls"] <= r["required"]
    unplaced = [r["id"] for r in out if r["zone"] is None]
    return Packed(out, Z, used, cols, unplaced, meat, float_mode)


# ----------------------------------------------------------------------------- CG + summaries
def bag_cg(P: Packed):
    m = s = None
    M = 0.0
    S = np.zeros(3)
    for r in P.rows:
        z = P.zones.get(r["zone"])
        if z is None or not z.in_bag or r.get("pos") is None:
            continue
        M += r["mass_tot"]
        S += r["mass_tot"] * np.asarray(r["pos"], float)
    if P.meat:
        mk = P.meat["kg"] * 1000.0
        if P.float_mode:
            zm = BC.STATIONS["im2"]
            pos = np.array([0.0, float(np.interp(zm, G["z"], G["yf"])) - 20.0 + FLOAT_GAP_MM / 2, zm])
            # bag contents shift aft by the gap (parallel float, no rotation)
            S += np.array([0.0, FLOAT_GAP_MM, 0.0]) * M
        else:
            vF, vA = P.meat["vol_F_L"], P.meat["vol_A_L"]
            zF = 0.5 * sum(P.meat["z_F"])
            pF = np.array([0.0, col_y("F", zF), zF])
            if vA > 0:
                zA = 0.5 * sum(P.meat["z_A"])
                pA = np.array([0.0, col_y("A", zA), zA])
                pos = (vF * pF + vA * pA) / (vF + vA)
            else:
                pos = pF
        M += mk
        S += mk * pos
    m = M
    s = S / M if M > 0 else np.zeros(3)
    return m, s


def peel(torso):
    """Cloth-sim peel for CORRIE rev B: sim fill CG minus the geometric uniform-fill CG (concept integrator)."""
    geo = G["c"].cg()[0]
    return SIM_FILL_CG[torso] - geo


_MEAT_PEEL = {}


def peel_meat(torso):
    """Meat-case peel: the sim meat case (38 kg on IM1-IM3, corrie_body.md §5a) minus this model's geometric CG of
    38 kg of meat in column F. Calibrated separately because the fill peel under-reads the meat case."""
    if torso not in _MEAT_PEEL:
        # the sim meat case = 30 kg meat on IM1-IM3 + 38 kg fill (huntkit/clothsim scenarios pack5200_v31.yaml)
        cap = G["cum_L"][-1]
        mv = 30.0 / MEAT_KG_PER_L / EFF_SOFT
        vF, vA = cap - mv, cap
        fill = lambda col, v: {"id": f"fill_{col}", "name": "uniform fill", "cat": "fill", "pref": [f"bag_{col}_low"],  # noqa: E731
                               "dims_mm": [10, 10, 10], "access": "camp", "qty": 1, "vol_L": v * EFF_SOFT,
                               "vol_tot": v * EFF_SOFT, "mass_g": 38000 * v / (vF + vA), "mass_tot": 38000 * v / (vF + vA)}
        P = pack([fill("A", vA), fill("F", vF)], "today", meat_kg=30.0)
        _MEAT_PEEL[torso] = SIM_MEAT_CG[torso] - float(bag_cg(P)[1][1])
    return _MEAT_PEEL[torso]


def summary(P: Packed, label=""):
    m_bag, cg = bag_cg(P)
    tot = sum(r["mass_tot"] for r in P.rows if r["zone"] not in ("hands",))
    hand = sum(r["mass_tot"] for r in P.rows if r["zone"] == "hands")
    bodyish = sum(r["mass_tot"] for r in P.rows if r["zone"] in ("chest", "hip_L", "hip_R", "strap_clip", "bottle_hip",
                                                                    "strap_pocket"))
    vol_bag = sum(r["vol_eff"] for r in P.rows if r.get("slot") or P.zones.get(r["zone"], Zone("", "", "", 0)).kind == "fixed")
    cap = 2 * G["cum_L"][-1]
    by_cat = {}
    for r in P.rows:
        if r["zone"] == "hands":
            continue
        c = by_cat.setdefault(r["cat"], {"mass_g": 0.0, "vol_L": 0.0})
        c["mass_g"] += r["mass_tot"]
        c["vol_L"] += r["vol_tot"]
    acc = {}
    for f in FREQ_ORDER:
        rs = [r for r in P.rows if r["access"] == f and r["zone"] != "hands"]
        acc[f] = {"n": len(rs), "ok": sum(r["ok"] for r in rs), "fail": [r["id"] for r in rs if not r["ok"]]}
    load_kg = (tot - sum(r["mass_tot"] for r in P.rows if r["zone"] in ("chest",))) / 1000.0
    meat_kg = P.meat["kg"] if P.meat else 0.0
    shoulder = sum(r["mass_tot"] for r in P.rows if r.get("slot") and r["slot"][0] == "F"
                   and 330 <= r["pos"][2] <= 650)
    out = {
        "label": label,
        "carried_g": round(tot, 0), "in_hands_g": round(hand, 0), "body_hip_chest_g": round(bodyish, 0),
        "bag_load_g": round(m_bag - meat_kg * 1000, 0), "pack_total_g": round(tot + PACK_BASE_G + meat_kg * 1000, 0),
        "load_kg_incl_meat": round(load_kg + meat_kg, 1),
        "main_bag_used_L": round(vol_bag, 1), "main_bag_cap_L": round(cap, 1),
        "main_bag_free_L": round(cap - vol_bag - (P.meat["vol_eff_L"] if P.meat and not P.float_mode else 0), 1),
        "top_z": round(max(P.cols["F"]["z_top"], P.cols["A"]["z_top"]), 0),
        "pouch_used_L": round(P.used.get("top_pouch", 0.0), 2),
        "wing_used_L": {k: round(P.used.get(k, 0.0), 2) for k in ("wing_L", "wing_R")},
        "hip_used_L": {k: round(P.used.get(k, 0.0), 2) for k in ("hip_L", "hip_R")},
        "cg_geo_mm": [round(float(v), 1) for v in cg],
        "cg_y_rev_c_15in": round(float(cg[1]) + (peel_meat(15) if P.meat else peel(15)), 1),
        "cg_y_rev_c_19in": round(float(cg[1]) + (peel_meat(19) if P.meat else peel(19)), 1),
        "frame_half_shoulder_g": round(shoulder, 0),
        "by_cat": {k: {"mass_g": round(v["mass_g"], 0), "vol_L": round(v["vol_L"], 2)} for k, v in by_cat.items()},
        "access": acc, "unplaced": P.unplaced, "spilled": [r["id"] for r in P.rows if r.get("spilled")],
        "float_mode": P.float_mode, "meat": P.meat,
    }
    # meat headroom: what still fits in the bag on top of this gear (volume), and what the rating allows (mass)
    free_now = cap - vol_bag
    out["meat_in_bag_max_kg"] = round(max(0.0, free_now) * EFF_SOFT * MEAT_KG_PER_L, 1) if not P.meat else None
    out["meat_rating_max_kg"] = round(RATED_KG - load_kg, 1) if not P.meat else None
    lim = REV_C["meat_y"] if P.meat else REV_C["bag_y"]
    out["rev_c_limit_y"] = lim
    out["rev_c_ok_15in"] = out["cg_y_rev_c_15in"] <= lim and out["cg_geo_mm"][2] <= REV_C["z_max"]
    return out


# ----------------------------------------------------------------------------- spotter options
SPOTTER_OPTIONS = {
    "a_wing_sleeve": {"label": "(a) padded sleeve in the left wing (IMP-1)", "config": "after",
                      "prefs": ["scope_sleeve_L"], "extra_g": 0.0},
    "b_case_plain_wing": {"label": "(b) bought padded case under the plain left wing", "config": "today",
                          "prefs": ["wing_L"], "extra_g": 150.0},
    "c_inside_door": {"label": "(c) inside the bag, aft half, via the door", "config": "today",
                      "prefs": ["bag_A_mid"], "extra_g": 0.0},
}
CASE_G = 150.0   # ASSUMPTION: neoprene stay-on / padded case for a 65-85 mm scope


def spotter_study(data):
    res = {}
    for key, spot in (("elk6", "spotter_65"), ("sheep8", "spotter_85")):
        rows = expand(data, key)
        res[key] = {}
        for ok, o in SPOTTER_OPTIONS.items():
            rr = copy.deepcopy(rows)
            for r in rr:
                if r["id"] == spot and o["extra_g"]:
                    r["mass_tot"] += o["extra_g"]
                    r["dims_mm"] = [d + 12 for d in r["dims_mm"]]   # ASSUMPTION 6 mm case wall
            P = pack(rr, o["config"], force={spot: o["prefs"]})
            s = summary(P, o["label"])
            r = next(x for x in P.rows if x["id"] == spot)
            res[key][ok] = {"label": o["label"], "zone": r["zone"], "access_cls": r["access_cls"],
                            "cg_geo_mm": s["cg_geo_mm"], "cg_y_rev_c_15in": s["cg_y_rev_c_15in"],
                            "spotter_pos": [round(float(v), 0) for v in r["pos"]], "mass_delta_g": o["extra_g"]}
    return res


# ----------------------------------------------------------------------------- improvements (proposals only)
def _gsm(mid):
    return MAT.load(mid).require("areal_density_gsm")


def _part(mid, w, h, qty=1, sa=8.0):
    return (w + 2 * sa) * (h + 2 * sa) * 1e-6 * _gsm(mid) * qty


H = BC.HOURS
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")
ZIP5 = MAT.load("coil_zipper_5").require("mass_g_m")
ZIP8 = MAT.load("coil_zipper_8").require("mass_g_m")
CORD2 = MAT.load("dyneema_cord_2mm").require("mass_g_m")
CORDLOCK = MAT.load("cord_lock_spring").require("mass_g")
XLPE = MAT.load("xlpe_foam").require("density_kg_m3")
SLIDER5_G = 3.0       # ASSUMPTION
G_HOOK = 4.0          # ASSUMPTION (HAUL family, corrie.py)


def improvements():
    """Each: mass (cut area x record gsm + hardware), beginner hours (bag_concepts.HOURS model, ASSUMPTION),
    problem (research refs), IP read. Proposals only: CORRIE geometry is not changed."""
    I = []

    def add(id_, name, mass, pieces, seam_m, zips=0, zip_m=0.0, tacks=0, extra_h=0.0, **kw):
        h = pieces * H["cut_piece"] + seam_m * H["straight_m"] + zips * H["zip_fixed"] + zip_m * H["zip_m"] \
            + tacks * H["bartack"] + extra_h
        I.append(dict(id=id_, name=name, mass_g=round(mass, 1), hours=round(h, 2), **kw))

    xlpe3 = 0.30 * 0.42 * 0.003 * XLPE * 1000
    add("IMP-1", "Padded scope sleeve on the inside of the left wing (330D tube, 3 mm XLPE liner on the bag side, "
        "shock-cord top)", _part("cordura_330d_nylon66", 340, 430) + xlpe3 + 0.5 * CORD2 + CORDLOCK,
        pieces=2, seam_m=1.6, tacks=2, extra_h=0.3,
        problem="Spotter has no home on CORRIE (side pockets dropped). Leaders give the spotter a dedicated side "
                "pocket/sleeve [HL §3.2]; rattle and damage when set down [HL §4.3].",
        ip="US 8,960,513 (optic + tripod pack) lapsed for fees 2019 and claims a hinged front optics compartment with "
           "tripod-leg holders, not a wing sleeve. Wing pockets for scopes are prior art (Eberlestock X2, ALPS "
           "Traverse). Frame guardrails H1-H4 untouched.", rank=2)
    add("IMP-2", "Hydration sleeve B-09 restored on B-01, hung from the B-06f collar strip above IM3 (z >= 545), "
        "2 bound hose ports at the collar seam", _part("robic_100d_ripstop", 250, 430, sa=10) + 0.1 * WEB25
        + 2 * _part("hypalon_coated_nylon", 40, 60, sa=0),
        pieces=3, seam_m=1.5, tacks=1, extra_h=0.5,
        problem="R-19 (frozen) asks for a sleeve + ports; CORRIE's body build has none, so water has no pack-on "
                "access. Hunters drink more from a bladder; many carry both [HL §2.4].",
        ip="Same part as the released SPINE B-09 (generic). Above IM3, off the frame interface: H1-H4 untouched.",
        rank=1)
    add("IMP-3", "Hipbelt bottle holster, right wing, for a 1 L bottle (power mesh + 330D base and back, shock cord, "
        "2 webbing loops onto the belt)", _part("power_mesh_nylon_spandex", 290, 240) + _part("cordura_330d_nylon66", 95, 95)
        + _part("cordura_330d_nylon66", 120, 200) + 0.3 * WEB25 + 0.4 * CORD2 + CORDLOCK,
        pieces=3, seam_m=1.4, tacks=4, extra_h=0.3,
        problem="A bottle is the hunters' backup or main water [HL §2.4]; CORRIE has no pack-on bottle spot. Exo sells "
                "a hipbelt bottle holder for this [HL §2.4].",
        ip="US 5,114,059 (side bottle holsters, granted 1992) is expired by term. Holsters are common (Stone Glacier "
           "Hydro Holster). Hipbelt only: frame guardrails untouched.", rank=3)
    add("IMP-4", "Zipped flat pocket inside the horseshoe door (100D ripstop, 50 mm bellows, #5 coil zip 280 mm, "
        "sewn flat before the door zip) for the kill kit, game bags and first aid",
        _part("robic_100d_ripstop", 300, 340) + _part("robic_100d_ripstop", 50, 1000) + ZIP5 * 0.32 + SLIDER5_G
        + 1.5, pieces=2, seam_m=1.4, zips=1, zip_m=0.28, extra_h=0.2,
        problem="Things you need now end up at the bottom [HL §4.1]; leaders keep the kill kit in a separate reachable "
                "compartment (Exo: in the hydration compartment) [HL §2.8]. The door opens upward, so the pocket must "
                "close (an open pocket would spill).",
        ip="Generic internal pocket; no hook-and-loop. Door / H1-H4 untouched (pocket is on the aft door, not the frame "
           "side).", rank=4)
    old = 2 * (0.5 * (180 + 140) * 110 + 2 * 55 * 160) * 1e-6 * _gsm("cordura_330d_nylon66")
    new = 2 * (0.5 * (200 + 160) * 130 + 2 * 60 * 180) * 1e-6 * _gsm("cordura_330d_nylon66")
    add("IMP-5", "Taller hipbelt pockets: HP-01 face 180/140 x 110 -> 200/160 x 130 mm, gusset 55 -> 60 mm "
        "(0.97 -> ~1.3 L), #8 zip +20 mm", new - old + 2 * 0.02 * ZIP8, pieces=0, seam_m=0.12, extra_h=0.2,
        problem="Hipbelt pockets that will not take a large phone are a recurring complaint [HL §4.2]; today's 145 x 92 "
                "interior (ASSUMPTION) does not take a 160 mm phone.",
        ip="Size change of an existing part.", rank=5)
    add("IMP-6", "Stretch phone / inReach pocket on the left shoulder strap (power mesh face, 330D back, 2 loops)",
        _part("power_mesh_nylon_spandex", 90, 170) + _part("cordura_330d_nylon66", 90, 170) + 0.2 * WEB25,
        pieces=2, seam_m=0.6, tacks=2, extra_h=0.1,
        problem="Hourly items (phone, messenger) need a pack-on home [HL §4.2]; optional once IMP-5 fits the phone.",
        ip="Common accessory class (strap phone pockets sold separately). Harness part, not the bag.", rank=7)
    add("IMP-7", "Silpoly wet-gear sack (400 x 500) for a wet shelter, carried outside the dry bag under the top pouch",
        _part("silicone_coated_poly_ripstop_40d", 400, 500) + 0.8 * CORD2 + CORDLOCK, pieces=1, seam_m=1.0,
        extra_h=0.2,
        problem="Keep a wet shelter away from the sleep system; outside or in its own bag [HL §4.4].",
        ip="Stuff sack; no IP issue.", rank=6)
    add("IMP-8", "Bow limb / cam cup at the foot of the right wing (330D cup, Hypalon base)",
        _part("cordura_330d_nylon66", 130, 160) + _part("hypalon_coated_nylon", 60, 100, sa=0), pieces=2,
        seam_m=0.5, tacks=2, extra_h=0.1,
        problem="CORRIE kept the riser loops (B-11) but lost SPINE's band cam cup (SH-04): the bow's lower cam has no "
                "seat on the box (archery loadout).", ip="Restores a released SPINE function; generic.", rank=8)
    return sorted(I, key=lambda d: d["rank"])


RECOMMENDED = ("IMP-1", "IMP-2", "IMP-3", "IMP-4", "IMP-5")


# ----------------------------------------------------------------------------- run
def run(data=None):
    data = data or load_yaml()
    res = {"geometry": {"v_geo_L": round(G["v_geo"], 2), "v_sewn_L": G["v_sewn"], "bulge_factor": round(G["kb"], 3),
                        "geo_uniform_cg": [round(float(v), 1) for v in G["c"].cg()],
                        "peel_mm": {t: round(peel(t), 1) for t in (15, 19, 23)},
                        "peel_meat_mm": {t: round(peel_meat(t), 1) for t in (15, 19, 23)}, "z_collar": G["zc"],
                        "z_fill": round(G["zfill"], 1)},
           "loadouts": {}, "packs": {}}
    for key, lo in data["loadouts"].items():
        variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
        for vname, arch in variants:
            rows = expand(data, key, archery=arch)
            for cfg in ("today", "after"):
                P = pack(rows, cfg)
                tag = f"{key}_{vname}_{cfg}"
                res["loadouts"][tag] = summary(P, f"{lo['name']} [{vname}, {cfg}]")
                res["packs"][tag] = [{k: r.get(k) for k in ("id", "name", "cat", "qty", "mass_tot", "vol_tot", "access",
                                                            "zone", "access_cls", "required", "ok", "pos", "slot")}
                                     for r in P.rows]
            # pack-out with meat (after config; the meat case is about volume and CG, not access)
            mk = lo["meat_case"]["meat_kg"]
            for cfg in ("today", "after"):
                P = pack(expand(data, key, archery=arch, meat_day=True), cfg, meat_kg=mk)
                res["loadouts"][f"{key}_{vname}_{cfg}_meat"] = summary(P, f"{lo['name']} pack-out {mk} kg [{cfg}]")
    # rev B.1 (2026-11-09): the adopted pockets + belt B, every belt size (hip pocket room grades with the wing)
    res["integrated"] = {}
    for size in CO.BELT_SIZES:
        cfg = f"integrated:{size}"
        for key, lo in data["loadouts"].items():
            variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
            for vname, arch in variants:
                P = pack(split_units(expand(data, key, archery=arch)), cfg)
                tag = f"{key}_{vname}_{size}"
                res["integrated"][tag] = summary(P, f"{lo['name']} [{vname}, CORRIE B.1, belt {size}]")
                res["integrated"][tag]["zones"] = {r["id"]: r["zone"] for r in P.rows}
                mk = lo["meat_case"]["meat_kg"]
                Pm = pack(split_units(expand(data, key, archery=arch, meat_day=True)), cfg, meat_kg=mk)
                res["integrated"][tag + "_meat"] = summary(Pm, f"{lo['name']} pack-out {mk} kg [B.1, {size}]")
    res["spotter"] = spotter_study(data)
    res["improvements"] = improvements()
    rec = [i for i in res["improvements"] if i["id"] in RECOMMENDED]
    res["recommended"] = {"ids": list(RECOMMENDED), "mass_g": round(sum(i["mass_g"] for i in rec), 1),
                          "hours": round(sum(i["hours"] for i in rec), 2)}
    return res


def _json(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    res = run()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "loadout_results.json").write_text(json.dumps(res, indent=1, default=_json))
    for k, s in res["loadouts"].items():
        a = s["access"]
        bad = {f: v["fail"] for f, v in a.items() if v["fail"]}
        print(f"{k:28s} carried {s['carried_g']/1000:5.1f} kg  bag {s['bag_load_g']/1000:5.1f} kg  "
              f"main {s['main_bag_used_L']:5.1f}/{s['main_bag_cap_L']:.0f} L free {s['main_bag_free_L']:5.1f} "
              f"top z {s['top_z']:.0f}  CG {s['cg_geo_mm']}  15in {s['cg_y_rev_c_15in']} "
              f"(lim {s['rev_c_limit_y']}) float {s['float_mode']}  pouch {s['pouch_used_L']} wings {s['wing_used_L']} "
              f"hip {s['hip_used_L']} unplaced {s['unplaced']} spilled {s['spilled']}")
        print("     fails:", bad)
    print(json.dumps(res["spotter"], indent=0, default=_json))
    for i in res["improvements"]:
        print(i["id"], i["mass_g"], i["hours"])
    print(res["recommended"], res["geometry"])
    if "--render" in sys.argv:
        import corrie_loadout_render as R
        print(R.render_all(res))
