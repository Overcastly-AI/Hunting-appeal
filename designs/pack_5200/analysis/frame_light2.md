# Lighter frame study 2: printed knuckles on carbon tubes (HA-LS-1 rev C)

Owner: structural-fea-engineer, 2026-11-09. Owner approval: DECISIONS 2026-11-09 "Owner: 'Yes' to the weight-pass recommendation" item 4. Research: [light_frame_architectures.md](../../../docs/research/light_frame_architectures.md). Code: `huntkit/gendesign/frame_light2.py` (+ `frame_light2_report.py`, `frame_light2_render.py`). Concepts: [`designs/pack_5200/frame_light2/concepts.yaml`](../frame_light2/concepts.yaml). Results: [`frame_light2_results.json`](../frame_light2/frame_light2_results.json). Tests: `tests/test_frame_light2.py`.

```
python -m huntkit.gendesign.frame_light2        # sizing + all rev C checks, about 10 min on 4 cores
```

## Summary

- **Recommendation: TENDON** (printed knuckles with carbon tendon wraps). Frame **802 g**, frame + spreader **964 g** (today 1063 / 1225 g: **-261 g**). Every rev C check passes: worst strength margin **1.04** (member: stays), worst fatigue margin **1.07** (fatigue: stays).
- **Achievable pack: about 3518 g (7.76 lb)** for CORRIE with every feature (weight pass A+B+C 3779 g with today's frame, minus the frame saving). **6.6 lb (2994 g) is not reachable** with these interfaces: frame + spreader would have to be 440 g, and the parts that no concept touches already weigh 437 g (carbon crown, rack and pawl, bushings, Ti pivot mount and inserts, Sandwich v2 spreader). With the stays, bars, pan and nodes on top, about 964 g is the floor of this architecture.
- **Tubes bonded straight into printed sockets (NODE) fail rev C**: the bond to printed polyamide is weak (published 3.7-5.0 MPa, interface failure) and the soft socket concentrates shear at the lip. Worst margin **0.16** (bond Volkersen peak: through, side_hill_torsion|23|bar upper_hub_R_through). Every load-carrying product found (Robot Bike Co, Bastion, Burton) uses metal lugs for this reason. The fix that keeps the printed look is TENDON: the print is the visible knuckle and the former, and a carbon wrap carries the joint load, as on the v2 frame.
- **Owner decisions:** pick a concept (NODE is not offered: it fails); accept a stiffer frame than today's; approve the T6 coupon programme for the printed-knuckle bonds before any frame is bonded; and choose whether the published 6.6 lb target moves (summary, second bullet).
- **BRANCH (the lattice look) fails frame buckling (0.88, side_hill_torsion|15|bar)** even with OD 18 branch tubes, and costs +89 g over TENDON: the branches push on the thin formed pan, and in-plane bracing does nothing for the out-of-plane bag loads (generative_design.md section 3 found the same). **SKIN** passes (it is TENDON underneath) and looks exactly like today's frame, for +191 g: frame 993 g, still 69 g under today.
- **Finding on today's frame (P-1):** the accessory extension-post socket at the crown corner has a Volkersen peak margin of **0.96** in C6p (posts fitted) with its 0.5 mm bondline, on today's frame too (`rev_c_verification_results.json` post_socket 0.957; the rev C summary table did not list this check). Giving it the crown corners' 0.8 mm bondline (glass beads) lifts it to 1.20 here. Applied in every concept; proposed for today's crown as well (no mass change).
- With the weight pass's accounting items T-2..T-4 as well (pouch as an accessory and the rest, about 217 g), the pack would be about **3302 g (7.28 lb)**.

## 1. Concepts

All four keep the v2 tube topology the beam model already knows: two straight OD 20 stays with the carbon crown legs telescoping inside, mid bar z 330, upper bar z 520 (pawl), formed CF lumbar pan (the lumbar-pad seat, hipbelt decision 2026-11-09), Ti pivot mount on 4 x M5 inserts in a printed hip node, the carbon crown with the rev C fix, and the Sandwich v2 spreader. Every interface keeps its place (section 6).

| concept | look | joints | stays / mid bar / upper bar / pan | frame g | frame + spreader g | worst strength | worst fatigue | pass |
|---|---|---|---|---:|---:|---:|---:|---|
| **NODE** | Organic printed knuckles at every junction with root fingers flowing along the tubes; tubes bonded straight into the prints. The simplest build. | tube in printed socket | OD 20 RW0 k3 / OD 18 RW45 k4 / OD 22 RW45 k6 / 1.5 mm | 857 | 1019 | 0.16 | 1.13 | **no** |
| **TENDON** | The NODE knuckles, with tapered carbon-twill 'tendons' laid from each knuckle onto its tubes: printed bone, carbon sinew. The wrap carries the joint load. | printed knuckle + carbon tendon wrap | OD 20 RW0 k2 / OD 16 RW45 k3 / OD 22 RW45 k5 / 1.5 mm | 802 | 964 | 1.04 | 1.07 | yes |
| **BRANCH** | TENDON plus a printed hip node at the pivot that branches into two OD 14 carbon tubes up to the z 330 knuckles: the Y-branch silhouette of today's body, as a lattice. | printed knuckle + carbon tendon wrap | OD 20 RW0 k3 / OD 18 RW45 k4 / OD 22 RW45 k6 / 1.5 mm + branch OD 18 RW45 k4 | 891 | 1054 | 0.88 | 1.16 | **no** |
| **SKIN** | The TENDON ladder hidden under a 0.8 mm printed shell shaped like today's branch body: reads exactly like today's frame. | printed knuckle + carbon tendon wrap | OD 20 RW0 k2 / OD 16 RW45 k3 / OD 22 RW45 k5 / 1.5 mm | 993 | 1156 | 1.04 | 1.07 | yes |
| today | printed PAHT-CF branch body + carbon crown | | | 1063 | 1225 | 1.12 (crown legs, IM3; rev_c_verification) | 1.04 (printed body) | yes (post socket 0.96, P-1) |

Layup codes: RW0 = twill 0/90 + UD 0 core x k + twill; RW45 = +-45 twill wraps (huntkit.fea.sizing). SKIN has the TENDON structure; its skin is not credited, so its margins are TENDON's.

## 2. Mass, by part group (g)

| group | NODE | TENDON | BRANCH | SKIN |
|---|---:|---:|---:|---:|
| tubes | 111.8 | 103.3 | 150.8 | 103.3 |
| printed nodes + clips | 308.3 | 237.8 | 262.9 | 237.8 |
| carbon tendon wraps | 0.0 | 40.5 | 54.8 | 40.5 |
| bonds (MMA) | 38.6 | 22.5 | 24.8 | 22.5 |
| lumbar pan + pad-up | 122.9 | 122.9 | 122.9 | 122.9 |
| crown + torso adjust (unchanged) | 250.0 | 250.0 | 250.0 | 250.0 |
| Ti pivot mount + inserts | 25.0 | 25.0 | 25.0 | 25.0 |
| printed skin (non-structural) | 0.0 | 0.0 | 0.0 | 191.1 |
| **frame** | **856.5** | **802.1** | **891.3** | **993.2** |
| spreader (Sandwich v2, unchanged) | 162.3 | 162.3 | 162.3 | 162.3 |
| **frame + spreader** | **1018.8** | **964.4** | **1053.6** | **1155.5** |

Nodes of TENDON (each):

| part | qty | printed g | carbon wrap g | bond g |
|---|---:|---:|---:|---:|
| foot node (boot + hinge-pin boss + stabiliser anchor + bumper) | 2 | 15.1 | 3.7 | 0.60 |
| mid knuckle z 330 (stay through-sleeve + mid-bar socket, IM2 seat) | 2 | 18.0 | 7.7 | 1.28 |
| upper knuckle z 520 (stay through-sleeve + upper-bar socket, IM3 + B-24 eye) | 2 | 20.7 | 8.9 | 1.46 |
| stay-top collar (bushing seat) | 2 | 13.8 | 0.0 | 1.40 |
| clip z80 wing lash | 2 | 7.0 | 0.0 | 0.88 |
| clip z110 shoulder-strap lower anchor | 2 | 8.0 | 0.0 | 0.88 |
| clip z190 IM1 fairlead seat | 2 | 8.0 | 0.0 | 0.88 |
| clip z250 wing lash | 2 | 7.0 | 0.0 | 0.88 |
| clip z420 wing lash | 2 | 7.0 | 0.0 | 0.88 |
| hip node (Ti-mount boss, 4 x M5, flange on the pan) | 1 | 28.8 | 0.0 | 2.47 |

Tubes: stays (2) 68.8 g, mid bar 12.3 g, upper bar 22.2 g. Crown and torso adjust (unchanged): crown legs (2, rev C +2 UD) 102.4, crown top bar (rev C +1 UD) 22.1, crown spine tube (rev C +1 UD) 32.6, crown corner wraps + 0.8 mm bondline 26.2, rack + pawl housing + pulley guides 44.0, UHMWPE bushings (4) 16.7, spine clamp 6.0.

## 3. Rev C strength, fatigue and joints

Method: `huntkit.fea` beam model of each concept (`frame_light2.build`), every rev C case set from `ls1_envelope('C')` (9 cases with the bag couple on the crown bar, C6p on the posts model, plus the 5 bag cases with the couple on the IM3 hooks) at torso 15 / 19 / 23 in. Margin = SF / requirement, pass >= 1.00. The solver's closed-form verification is in `tests/` (cantilever, Euler, thin-wall torsion, Volkersen) and `tests/test_frame_light2.py` adds the checks below.

Worst margin per check family:

| check | NODE | TENDON | BRANCH | where (TENDON) |
|---|---:|---:|---:|---|
| tube first-ply | 1.12 | 1.04 | 1.12 | member: stays @ hipbelt_off_abuse|15|IM3 SL520-SL530 |
| frame buckling | 1.86 | 1.72 | 0.88 | frame buckling @ hipbelt_off_abuse|23|bar |
| bond, average | 1.51 | 2.50 | 2.95 | bond avg: wrap mid hub @ side_hill_torsion|15|IM3 mid_hub_R |
| bond, Volkersen peak | 0.16 | 1.16 | 1.12 | bond Volkersen peak: wrap mid hub @ side_hill_torsion|15|IM3 mid_hub_R |
| crown (unchanged) | 1.12 | 1.12 | 1.12 | crown: crown_leg @ hipbelt_off_abuse|23|IM3 CLbot-CL530 |
| lumbar pan | 1.35 | 1.30 | 2.34 | lumbar pan: lumbar plate shear buckling @ drop_2p5g|23|IM3 |
| foot boot | 2.49 | 2.49 | 2.49 | foot boot (PAHT) @ single_stay_setdown|15|bar |
| stay-top collar | 3.04 | 2.44 | 3.04 | stay-top collar ring (PAHT, Z) @ hipbelt_off_abuse|15|IM3 |
| stay ring | 1.97 | 2.08 | 1.97 | stay ring under the collar @ hipbelt_off_abuse|15|IM3 |
| hip node | 3.00 | 3.00 | 3.00 | hip node 4 x M5 inserts @ meat_straps|23|bar |
| stay clips | 20.24 | 20.24 | 20.24 | stay clip bond (PAHT) @ meat_straps|15|bar |
| rack | 6.27 | 6.27 | 6.27 | torso adjust: rack (5328 N) @ hipbelt_off_abuse|15|IM3 |
| fatigue | 1.13 | 1.07 | 1.16 | fatigue: stays @ 23|IM3 SL290-SL330 |

TENDON by case (worst of torso, couple variant and every check):

| case | worst margin | torso |
|---|---:|---:|
| hipbelt_off_abuse (couple on IM3) | 1.04 | 15 |
| side_hill_torsion (couple on IM3) | 1.11 | 23 |
| hipbelt_off_abuse (couple on the crown bar) | 1.13 | 15 |
| meat_straps (couple on the crown bar) | 1.13 | 23 |
| drop_2p5g (couple on IM3) | 1.14 | 23 |
| side_hill_torsion (couple on the crown bar) | 1.16 | 15 |
| tall_load_posts (couple on the crown bar) | 1.20 | 15 |
| drop_2p5g (couple on the crown bar) | 1.21 | 15 |
| tall_load (couple on the crown bar) | 1.38 | 15 |
| overload_haul (couple on the crown bar) | 1.59 | 23 |
| static_carry (couple on IM3) | 1.72 | 23 |
| static_carry (couple on the crown bar) | 1.82 | 15 |
| single_stay_setdown (couple on the crown bar) | 1.92 | 19 |
| single_stay_setdown (couple on IM3) | 1.92 | 19 |

Every check of TENDON, sorted:

| check | margin | where |
|---|---:|---|
| member: stays | 1.04 | hipbelt_off_abuse|15|IM3 SL520-SL530 |
| fatigue: stays | 1.07 | 23|IM3 SL290-SL330 |
| member: crown legs | 1.12 | hipbelt_off_abuse|23|IM3 CLbot-CL530 |
| crown: crown_leg | 1.12 | hipbelt_off_abuse|23|IM3 CLbot-CL530 |
| member: upper_bar | 1.13 | hipbelt_off_abuse|15|bar UB0-UB1 |
| fatigue: lumbar_plate | 1.14 | 15|bar plv32 |
| bond Volkersen peak: wrap mid hub | 1.16 | side_hill_torsion|15|IM3 mid_hub_R |
| member: crown_spine | 1.18 | hipbelt_off_abuse|15|IM3 SP81-SP150 |
| crown: crown_spine | 1.18 | hipbelt_off_abuse|15|IM3 SP81-SP150 |
| crown: post_socket bond peak | 1.20 | tall_load_posts|15|bar |
| member: lumbar_plate | 1.21 | drop_2p5g|15|bar plv32 |
| member: crown_top_bar | 1.23 | hipbelt_off_abuse|15|IM3 TB0-TB1 |
| crown: crown_top_bar | 1.23 | hipbelt_off_abuse|15|IM3 TB0-TB1 |
| crown: crown_corner bond peak | 1.23 | tall_load_posts|15|bar |
| member: mid_bar | 1.26 | side_hill_torsion|15|bar MB2-SR330 |
| lumbar pan: lumbar plate shear buckling | 1.30 | drop_2p5g|23|IM3 |
| fatigue: crown legs | 1.36 | 23|IM3 CLbot-CL530 |
| lumbar pan: lumbar plate-to-stay bond Volkersen peak | 1.54 | side_hill_torsion|15|IM3 |
| bond Volkersen peak: wrap upper hub | 1.58 | side_hill_torsion|23|bar upper_hub_R |
| frame buckling | 1.72 | hipbelt_off_abuse|23|bar |
| stay ring under the collar | 2.08 | hipbelt_off_abuse|15|IM3 |
| fatigue: stay-top collar | 2.26 | 23|IM3 bush_top |
| crown: post_socket bond avg | 2.31 | tall_load_posts|15|bar |
| crown: leg_ring_crush | 2.31 | hipbelt_off_abuse|15|IM3 |
| lumbar pan: lumbar plate-to-stay bond avg | 2.32 | side_hill_torsion|15|IM3 |
| crown: crown_corner bond avg | 2.37 | tall_load_posts|15|bar |
| stay-top collar ring (PAHT, Z) | 2.44 | hipbelt_off_abuse|15|IM3 |
| foot boot (PAHT) | 2.49 | single_stay_setdown|15|bar |
| bond avg: wrap mid hub | 2.50 | side_hill_torsion|15|IM3 mid_hub_R |
| member: ext_post | 2.72 | tall_load_posts|15|bar post_L |
| crown: ext_post | 2.72 | tall_load_posts|15|bar post_L |
| fatigue: hip inserts | 2.86 | 15|bar HP |
| fatigue: upper_bar | 2.93 | 15|IM3 UB0-UB1 |
| hip node 4 x M5 inserts | 3.00 | meat_straps|23|bar |
| fatigue: hip flange bond | 3.04 | 15|bar HP |
| fatigue: crown_spine | 3.17 | 15|IM3 SP81-SP150 |
| fatigue: crown_top_bar | 3.43 | 23|IM3 TB0-TB1 |
| bond avg: wrap upper hub | 3.69 | side_hill_torsion|23|bar upper_hub_R |
| hip node flange bond | 4.25 | meat_straps|23|bar |
| fatigue: hip_pivot | 4.68 | 15|bar pivot_doubler_1 |
| member: hip_pivot | 5.00 | drop_2p5g|15|bar pivot_doubler_1 |
| fatigue: crown corner bond | 6.11 | 23|IM3 crown_corner |
| torso adjust: rack (5328 N) | 6.27 | hipbelt_off_abuse|15|IM3 |
| bond Volkersen peak: wrap foot | 7.03 | single_stay_setdown|19|bar foot_L |
| lumbar pan: lumbar plate in-plane shear | 8.73 | drop_2p5g|23|IM3 |
| lumbar pan: Ti pivot insert punching shear in lumbar plate | 12.35 | meat_straps|23|bar |
| member: ext_post_bar | 14.44 | tall_load_posts|15|bar XB0-XB1 |
| crown: ext_post_bar | 14.44 | tall_load_posts|15|bar XB0-XB1 |
| bond avg: wrap foot | 15.08 | single_stay_setdown|19|bar foot_L |
| crown: bushing_bearing | 17.44 | hipbelt_off_abuse|15|IM3 |
| stay clip bond (PAHT) | 20.24 | meat_straps|15|bar |
| fatigue: bond wrap mid hub | 26.36 | 19|IM3 mid_hub_L |
| fatigue: mid_bar | 45.50 | 19|IM3 SL330-MB0 |
| bond Volkersen peak: stay_top | 47.44 | hipbelt_off_abuse|15|IM3 stay_top_L |
| fatigue: bond wrap upper hub | > 100 | 15|IM3 upper_hub_R |
| bond avg: stay_top | > 100 | hipbelt_off_abuse|15|IM3 stay_top_L |
| fatigue: bond stay_top | > 100 | 23|IM3 stay_top_L |
| fatigue: bond wrap foot | > 100 | 15|IM3 foot_R |

Joint checks, how:

- **Printed sockets (NODE)**: `huntkit.fea.joints.bond_check` with the printed wall as the outer adherend (E t = 3860 MPa x 2.4 mm), MMA G 300 MPa, 0.5 mm bondline, double lap at bar ends (printed spigot: bond perimeter OD + ID). Allowable **4.0 MPa** (published 5.0 MPa dry PA12 x 0.8 hot/wet). The node itself is a PAHT 'neck' member in the beam model (socket annulus, tube not credited) checked at 0.8 x 88 MPa.
- **Carbon tendons (TENDON, BRANCH, SKIN)**: the v2 frame's carbon wrap joint (frame.yaml `joint`: 0.75 mm QI wrap, 30 mm on each tube, 40 mm through, MMA on CFRP 20 MPa x 0.8). The printed knuckle under it is the former; it is not credited.
- **Foot boot**: PAHT annulus at the boot mouth, ground lateral force x 40 mm + axial, 0.8 x 88 MPa.
- **Stay-top collar**: top bushing ring moment (120 deg land, `huntkit.fea.rings`) shared by the stay wall and a 3 mm printed collar by E t^3; the collar hoop at the Z allowable 0.8 x 47 MPa; the stay by first-ply failure.
- **Hip node**: Ti mount on 4 x M5 heat-set inserts (pull-out 1500 N ASSUMPTION, as hipbelt_structural.md; pull-out test pending), pivot reaction + its moment over a 22 mm stand-off; printed flange 70 x 60 mm bonded to the pan at 4.0 MPa (flatwise stress read against lap shear: conservative).
- **Stay clips** (z 80 / 110 / 190 / 250 / 420 hard points): external load at the node on a 22 mm wide printed collar bond at 4.0 MPa.
- **Fatigue** (1e5 cycles at 0 -> 1.6 g x 68 kg, from the C1 static-carry solve): CFRP FI <= 0.5; PAHT <= 0.3 x the knocked-down strength; bonds <= 0.3 x dry lap shear; inserts 0.5 x pull-out (ASSUMPTION).

## 4. Stiffness and load transfer

Same two tests as `frame_topopt.tube_frame_stiffness` (hip pivot clamped; rev B static-carry load set for the carry deflection; +-100 N fore-aft at the stay tops for torsion), torso 19 in.

| frame | stay-top aft deflection, static carry (mm) | torsion (N m/deg) | hip share, static carry |
|---|---:|---:|---:|
| today, printed branch body (production_frame_results.json, 4 mm voxels) | 29.7 | 0.44 | 0.80 (same spring model) |
| v2 wrapped tube ladder (rejected look) | 6.3 | 2.87 | |
| NODE | 6.3 | 2.82 | 0.80 |
| TENDON | 7.3 | 2.68 | 0.80 |
| BRANCH | 4.0 | 3.09 | 0.80 |
| SKIN | 7.3 | 2.68 | 0.80 |

Every tube concept is several times stiffer than today's printed body (torsion about 6x). Today's body was accepted at 0.15 of the tube frame's torsion (production_frame.md); the light frames go back to the tube frame's feel. The hip/shoulder split is set by the hipbelt and harness springs, not the frame (80 % hips in every model): a stiffer frame keeps the bag from swaying, it does not move load off the hips. The load lifters see less crown sag. ASSUMPTION: PAHT at 40 C is not a stiffness issue here, because the knuckles are short; the tubes carry the bending.

## 5. Centre of gravity

| frame | frame CG y (aft) mm | frame CG z mm | loaded-pack CG shift vs today (68 kg at 205 mm, z 550) |
|---|---:|---:|---|
| today (printed body centroid + crown) | -5 | 355 | |
| NODE | -12 | 340 | +0.5 mm aft, +0.4 mm up |
| TENDON | -12 | 338 | +0.7 mm aft, +0.5 mm up |
| BRANCH | -13 | 329 | +0.4 mm aft, +0.1 mm up |
| SKIN | -11 | 331 | +0.1 mm aft, -0.2 mm up |

The frame is about 1 % of the loaded mass, so its CG moves the loaded-pack CG by under 2 mm: no effect on the rev C load cases (bag 205 mm, meat 190 mm are content CGs). Empty, the lighter frame is less top-heavy than today's, because the printed body's mass was mostly in the stays and lumbar struts.

## 6. Interfaces kept

| interface | today | in the tube concepts |
|---|---|---|
| crown, top bar, lifters (US 10,952,523 guardrail) | carbon crown in printed sleeves | unchanged crown; legs telescope inside the carbon stays on the same UHMWPE bushings (v2); lifters stay on the crown top bar |
| torso adjust (rack + pawl + 3:1 pulley) | pawl housing on the printed upper bar | pawl housing printed on the upper carbon bar centre (as v2), rack on the spine unchanged |
| hipbelt B Ti pivot, 4 x M5 inserts | printed boss | printed hip node bonded to the pan; same 4 x M5 pattern |
| lumbar-pad seat | lumbar pan of the printed body | formed CF pan (v2), the pad bears on it |
| hinge pins z 60 (bag_anchor_low), under-strap pins US1/US2 | printed foot region | foot node bosses |
| IM1 z 190 / IM2 z 330 / IM3 z 520 fairleads, B-24 float-link eyes | printed body | IM1: stay clip; IM2, IM3 and B-24: knuckle seats (fairleads unchanged parts) |
| wing lash z 80 / 250 / 420, shoulder-strap lower anchor z 110, hip stabiliser z 60 | printed body | stay clips and foot node |
| hood, B-22 guys | crown | crown (unchanged) |
| spreader (Sandwich v2) | clips on the printed stays | clips on the carbon stays at the same x/z (ASSUMPTION: same support line, comfort result unchanged; re-run `spreader.evaluate` on the tube supports before release) |

## 7. Print time, cost, build, patents

| concept | printed parts | printed g | print h (H2S, 8 mm3/s) | material cost USD |
|---|---:|---:|---:|---:|
| NODE | 19 | 308 | 11.7 | 291 |
| TENDON | 19 | 238 | 9.2 | 284 |
| BRANCH | 21 | 263 | 10.4 | 303 |
| SKIN | 31 | 429 | 17.8 | 301 |
| today | 2 body halves + small parts | 823 | about 27 (generative_branch.md) | about 208 |

TENDON cost lines: tube: stays $41; tube: mid bar $6; tube: upper bar $8; crown tubes (legs, top bar, spine; unchanged) $44; PAHT-CF filament (nodes, clips, skin, rack/pawl) + 15 % failed prints $26; lumbar pan material (record, scaled) $6; MMA cartridges (2) + glass beads + mixing tips (ASSUMPTION) $80; SLM Ti hip mount (ASSUMPTION, mass_cut.md) $35; M5 heat-set inserts + UHMWPE bushings (ASSUMPTION) $12; printed bonding jig (PLA/PETG ~400 g) + plywood base (ASSUMPTION) $25.

Build steps (TENDON):

1. Order tubes cut to length (stays, bars; crown tubes as today). Sand every bond zone 120 grit, wipe with IPA.
2. Print the knuckles, foot nodes, collars, clips and hip node flat in PAHT-CF (dried 80 C 8-12 h), 6 walls, 40 % gyroid; anneal per the TDS. Sand the sockets; flame-treat (quick pass of a propane torch) just before bonding (ASSUMPTION for the 4.0 MPa design value; T6 coupons check it).
3. Make the T6 coupons from offcuts first (3 x each socket type), pull them to failure; do not bond the frame until the mean is >= 1.5 x the largest limit end force (load_standard.md T6).
4. Print the bonding jig: a flat plywood board with printed V-cradles at the stay feet, z 330, z 520 and the stay tops, holding the stays parallel at x +/-115 and the knuckle axes square (jig files to follow).
5. Dry-fit the whole ladder in the jig. Butter tube and socket with MMA (glass beads 0.5 mm), push in with a twist, wipe the fillet. No injection ports (patent design-around, research section 4). Cure 24 h.
6. Bond the formed CF lumbar pan to the stays (as the v2 frame) and the hip node flange to the pan; heat-set the 4 x M5 inserts in the hip node before bonding; fit the Ti mount.
7. Fit the crown (legs into the stays on the UHMWPE bushings), rack, pawl and pulley exactly as today.
8. TENDON wraps: 3 plies of 3k twill per joint (0/90, +-45, 0/90), cut as tapered fingers, wet out with laminating epoxy, laid from the knuckle 30 mm onto each tube (40 mm each side of the through-hubs), peel ply + shrink tape, cure, 65 C post-cure. The knuckle is the former: no foam, no mould.
9. Light scuff and a satin clear coat over the wraps; the printed knuckle body stays visible between the fingers.

Patents (research section 4, not legal advice): the knuckles have **no adhesive injection ports or internal channels** (Divergent US 10,668,965 design-around); TENDON has no inner spigot (Divergent node/tube engagement family); crown and lifters unchanged (Mystery Ranch US 10,952,523 guardrail); a multi-part tube frame is outside KUIU's one-piece frame patents. Freedom-to-operate opinion before tooling.

## 8. Mass reductions that keep the margins (not applied)

Greedy downsizing log (each step re-runs every rev C check at 15 / 19 / 23 in):

| step | worst strength | worst fatigue | kept |
|---|---:|---:|---|
| v2 sections | 1.12 (member: crown legs) | 1.13 | yes |
| stay OD 20 RW0 k2 | 1.03 (member: stays) | 1.07 | yes |
| stay OD 20 RW45 k2 | 0.68 (member: stays) | 0.65 | no |
| bar OD 16 RW45 k4 | 1.01 (bond Volkersen peak: wrap mid hub) | 1.07 | yes |
| bar OD 16 RW45 k3 | 1.03 (member: stays) | 1.07 | yes |
| ubar OD 22 RW45 k5 | 1.04 (member: stays) | 1.07 | yes |
| ubar OD 22 RW45 k4 | 0.94 (member: upper_bar) | 1.07 | no |
| pan_t 1.2 | 0.69 (lumbar pan: lumbar plate shear buckling) | 0.85 | no |

- The crown (legs, top bar, spine, corner wraps, rack, bushings) is now the biggest single block. A lighter crown needs a new torso-adjust concept: out of scope here, and the rev C crown margins (legs 1.12-1.14) leave nothing to cut.
- The spreader (162 g) is set by the 14 kPa comfort limit with the 190 mm meat CG (rev_c_verification.md: 13.83 kPa). It does not get thinner.
- Printed clips: folding the z 250 / 420 lash points into webbing loops around the stays saves about 15 g; the owner's pack-designer would need to accept it.

## 9. Assumptions

- ASSUMPTION: MMA on sanded, flame-treated PAHT-CF reaches 5.0 MPa dry (best published PA12 value), 4.0 MPa hot/wet. T6 coupons decide it.
- ASSUMPTION: the printed node neck is the socket annulus over 12 mm, tube not credited; real knuckles are filleted and thicker there (conservative).
- ASSUMPTION: generative root fingers and fillets add 30 % to each socket's printed volume; node features (fairlead seats, hinge-pin bosses, eyes) 2-6 g each.
- ASSUMPTION: TENDON wraps cover 60 % of the knuckle surface plus 30 / 40 mm on each tube with an 8 mm ply drop; the knuckle is not credited structurally.
- ASSUMPTION: M5 heat-set insert pull-out 1500 N in PAHT-CF (as hipbelt_structural.md); test pending.
- ASSUMPTION: the spreader keeps today's mass and comfort result on the tube supports.
- ASSUMPTION: tube price $30/m at 16 mm scaled with OD (cfrp_rollwrapped_tube record); print 8 mm3/s + 8 % waste + 0.15 h per part.
- ASSUMPTION: the CG comparison puts today's crown and hardware at z 560 and uses the printed body's STL centroid at uniform density.
- The PAHT fatigue ratio 0.3 and the creep values are the material record's study assumptions (no measured S-N curve for printed PAHT-CF).

## 10. Tests before release (HA-LS-1 section 5, added here)

- **T6p printed-knuckle coupons**: 3 x each knuckle (foot, mid, upper, stay-top collar, hip node flange) bonded to tube offcuts exactly as the frame; pull to failure. For TENDON, also 3 x a wrapped knuckle. Pass as T6.
- **T6f fatigue coupon**: one wrapped mid knuckle cycled 0 -> 1.6 g end force for 1e5 cycles on the T5 rig.
- Then the frame tests T1-T5, T9 as written.

## Screenshots

- `outputs/screens/20261109_framelight_1.png`
- `outputs/screens/20261109_framelight_2.png`
- `outputs/screens/20261109_framelight_3.png`

