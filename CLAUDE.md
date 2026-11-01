# Hunting-Appeal — Claude-driven hunting gear design

This repo designs technical mountain-hunting apparel (original camo plus solid colorways,
in the performance class of brands like KUIU; mostly solid colors with camo used as edgy accent panels) and a 5200 cu in (≈85 L) framed hunting pack.
**Claude does most of the engineering. The human owner builds and sews the gear.**
That means every design must end with **mass-production-ready cut and sew packages**:
true-scale patterns, cutting markers, sewing operation sequences, BOMs and QC specs.

No GUI. Everything is Python scripts and CLI tools that write files into `outputs/`
(PDF, DXF, SVG, PNG, CSV, Markdown). The human opens those files and doesn't have to run anything.

## Hard rules
- **Original IP only.** Use other brands as performance benchmarks only. Never trace, copy or
  closely imitate their camo patterns (e.g. KUIU Verde/Vias/Valo), logos, names or trade dress.
- **Units:** mm, N, MPa, g, kg internally. Show imperial alongside metric in docs for the human
  (in, lb, oz, cu in).
- **Every design number traces to a source:** a material in `data/materials/`, a calculation in
  `huntkit/`, or a stated assumption marked `ASSUMPTION:` in the design doc.
- **Safety factors:** pack load-path parts SF ≥ 2.0 on yield at the 150 lb (68 kg) design load,
  under a 2.5 g dynamic factor (stumble or drop). Fatigue gets checked separately.
- Generated artifacts go in `outputs/` (git-tracked only when they're released deliverables in
  `outputs/release/`). Source of truth is code plus YAML in `designs/`.

## Layout
```
huntkit/            Python package (engineering library)
  materials/        material DB loader + property queries      (owner: materials-engineer)
  fea/              beam/shell FEA, load cases, frame checks    (owner: structural-fea-engineer)
  patterns/         2D pattern geometry, seam allowance, grading, markers, DXF/PDF export
                                                                (owner: pattern-maker)
  camo/             procedural camo + colorway generator        (owner: camo-designer)
  manufacturing/    BOM, sewing op sheets, tech packs, QC       (owner: manufacturing-engineer)
data/materials/     YAML material records (fabrics, foams, composites, metals, hardware, thread)
designs/pack_5200/  pack design spec + parameters (YAML) + design doc
designs/apparel/    garment specs per piece
docs/               conventions, interface contracts, decisions log
outputs/            generated files (scratch); outputs/release/ = shipped build packages
tests/              pytest, run `python -m pytest -q`
```

## Interface contracts (read docs/CONTRACTS.md before touching shared code)
The modules talk through the contracts in `docs/CONTRACTS.md`. Change a contract only if you
update every consumer in the same change.

## Working with agents (important — preserves main context)
The main session acts as **orchestrator**. It delegates substantive work to the specialist agents
in `.claude/agents/`, and keeps only their conclusions:

| Agent | Use for |
|---|---|
| `materials-engineer` | picking or adding fabrics, laminates, foams, composites, metals, hardware, thread; property sourcing |
| `structural-fea-engineer` | frame/stay/hipbelt/load-shelf FEA, load cases, safety factors, fatigue |
| `pattern-maker` | flat patterns, seam allowances, notches, grading, nesting markers, DXF/PDF cut sheets |
| `camo-designer` | original camo patterns, solid colorways, spectral/IR notes, print-repeat files |
| `pack-designer` | 5200 pack system architecture, volumes, suspension, features, integration |
| `apparel-designer` | garment system (layers, fits, features, size chart) |
| `manufacturing-engineer` | BOMs, sewing operation sequences, stitch specs, jigs, QC, costing, tech packs |
| `design-reviewer` | independent adversarial review of a design or analysis (give it files, not conclusions) |

Run independent agents in parallel. Each agent writes its findings into the repo (a design doc,
a YAML file or code) so they're durable, and returns a short summary.

## Commands
```
pip install -r requirements.txt
python -m pytest -q
python -m huntkit.<module>.cli --help     # each module exposes a CLI
```
