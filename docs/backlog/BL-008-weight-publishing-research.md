# BL-008 Research: what the leaders count in their published weights

**Wave:** 1 · **Agent:** pack-designer · **Size:** S · **Depends on:** none

## Why
Our weight target (about 6.6 lb) and every benchmark depend on what a published weight includes. The review assumed the leaders' bag weights include compression straps, meat-carry parts and frame attachment; that is unverified. Our pack books a top pouch, bottle holster, scope sleeve, phone pocket, rain fly and float links in its base weight.

## Goal
A cited table of what each leader's published weight includes, and a proposed definition of our "base" and "as hunted" configurations.

## Tasks
1. For Stone Glacier (Sky 5900, Krux frame), Exo (K4 5000, frame, lid), Mystery Ranch (Metcalf, Beartooth), Kifaru (ARK frame plus a bag), Seek Outside (Revolution plus a bag), KUIU (ICON/PRO) and Initial Ascent: record the published weight and whether it includes the lid, hipbelt pockets, bottle holder, rain cover, load shelf or meat straps, compression straps, frame attachment hardware, and which belt and frame size. Quote the source text and give the URL. Mark anything you could not verify.
2. Find independent measured weights where they exist (reviews that weigh the pack) and note differences from the published figure.
3. Propose our configurations: **base** (what is always on the pack) and **as hunted** (base plus the add-ons a typical hunt carries), item by item, using the systems in `huntkit/mass/ledger.py` if BL-001 has landed, else the groups in `weight_pass_corrie.json`.
4. Give the like-for-like comparison: our base against each leader on the same inclusions.

## Deliverables
- `docs/research/published_weight_definitions.md`
- `designs/pack_5200/analysis/weight_configs_proposal.md`

## Acceptance
- Every cell in the inclusion table has a URL or is marked "not stated".
- The proposal changes no design; it lists the owner decisions it needs.
