# Cloth and pack simulation methods (research note for `huntkit.clothsim`)

Owner: structural-fea-engineer, 2026-11-05. Short survey before building the phase-1 batch cloth simulator.
The question: which method gives the **static** shape, strain and seam line force of a sewn, loaded pack bag
from the real flat pattern, in numpy/scipy, with no GUI?

## 1. Methods

| Method | What it is | Good for | Weak for us |
|---|---|---|---|
| **PBD / XPBD** | Positions are projected onto constraints each step. XPBD (Macklin, Müller & Chentanez, MIG 2016) adds a compliance per constraint, so stiffness is tied to an energy potential and no longer depends on the time step or iteration count [xpbd][xpbd-rr]. Houdini Vellum is built on it [diffxpbd]. | Fast, robust, games and previs, collisions | Converged forces need many iterations at high stiffness. A seam force in N/mm is what we want out, and with stiff pack cloth (100 to 1500 N/mm) XPBD stalls before the force converges. |
| **Implicit mass-spring / FEM (Baraff & Witkin, SIGGRAPH 1998)** | Backward-Euler step on stretch, shear and bend "conditions", one sparse linear solve per step, so large steps are stable [bw98][bw98-cmu]. | Stiff cloth, large steps, physical forces | Dynamic: we only need the end state. |
| **Static energy minimisation** | One implicit-Euler step with dt to infinity is a Newton step on the total potential energy. This gives the equilibrium directly. | Batch static load cases, exact force balance (so a seam force can be checked against p r) | Needs a damped (Levenberg-Marquardt) Newton step and a line search because cloth has near-zero-stiffness modes (slack and wrinkles) |
| **Quadratic bending (Bergou, Wardetzky et al., SGP 2006; CAGD 2007)** | For isometric (near-inextensible) deformation, a cotangent-Laplacian bending energy is quadratic in the positions, so its Hessian is constant [bergou][wardetzky] | Cheap bending for cloth with a flat rest state (a flat pattern is exactly that) | Exact only for isometric deformation; fine at fabric strains of a few percent |
| **Anisotropic woven membrane** | Woven cloth is orthotropic: stiff along warp and weft, soft in shear (trellising), and it carries almost no compression (it wrinkles). Orthotropic hyperelastic membranes with separate warp and fill terms (Motevalli & Balzani) and piecewise-linear data-driven anisotropic models fitted to measured cloth (Wang, O'Brien & Ramamoorthi, SIGGRAPH 2011) are the standard references [motevalli][wang11]. | Strain by yarn direction, shear and wrinkles | Real fabrics are non-linear (crimp), and we only have break strength and break elongation, not stress-strain curves |

Measured fabric ranges (Kawabata KES-F, 15 plain wovens): bending rigidity B = 0.018 to 0.119 gf cm²/cm,
shear rigidity G = 0.31 to 4.15 gf/(cm deg) [kes]. In SI, 1 gf cm²/cm = 0.098 N mm and 1 gf/(cm deg) = 0.056 N/mm per radian.
Coated pack cloth is much stiffer than those apparel wovens, so our bending and shear values are ASSUMPTIONS, but the
**ratios are clear**: shear and bending are 2 to 4 orders of magnitude below warp/weft tension.

Seam strength rule of thumb for a 301 lockstitch: **seam strength = SPI x single-end thread strength x 1.5**
(1.7 for 401 chainstitch), valid as long as the fabric does not tear first [seam-f2f][seam-tl].

## 2. Choice for phase 1

- **Static equilibrium by damped Newton on the total potential energy.** This is the infinite-dt limit of
  Baraff-Witkin. The Hessian is a Gauss-Newton membrane term plus the positive part of the geometric stiffness,
  which keeps it positive definite. The step is Levenberg-Marquardt damped, with a backtracking line search.
- **Membrane:** constant-strain triangles in the flat-pattern rest state. Green strain is split by yarn direction:
  warp `k1`, weft `k2`, shear `g`. A compression factor `c << 1` stands in for tension-field theory, so compressed
  cloth goes slack and shows up as a wrinkle.
- **Bending:** quadratic cotangent-Laplacian energy (Bergou/Wardetzky) per piece. Seams act as hinges.
- **Seams:** nodes are welded by notch position. Both sides of a seam take the same 3D points on the master
  surface, as the pattern's 50 mm notches do. The seam line force is the membrane force one panel passes to
  the other at each welded node, divided by the tributary seam length.
- **Loads:** gravity; gas or fluid-equivalent fill written as the exact pressure potential −∫p dV, with
  p = p0 + ρ g (z_ref − z); dead loads; tension-only cables (straps, hook straps, eyes); penalty contact against
  the decimated frame and spreader meshes.
- XPBD was not chosen. It would suit an interactive drape, but this is a batch check of forces.

## Sources

[xpbd]: https://matthias-research.github.io/pages/publications/XPBD.pdf
[xpbd-rr]: https://researchr.org/publication/MacklinMC16
[diffxpbd]: https://arxiv.org/pdf/2301.01396
[bw98]: https://www.cs.cornell.edu/courses/cs667/2005sp/readings/baraff98.pdf
[bw98-cmu]: https://www.ri.cmu.edu/publications/large-steps-in-cloth-simulation
[bergou]: https://cs.columbia.edu/cg/pdfs/9_QuadBend.pdf
[wardetzky]: https://ddg.math.uni-goettingen.de/pub/bendingCAGD.pdf
[motevalli]: https://www.scipedia.com/wd/images/5/5c/Motevalli_Balzani_2021a_5590_718_paper.pdf
[wang11]: https://wanghmin.github.io/publication/wang-2011-dde/Wang-2011-DDE.pdf
[kes]: https://matsc.ktu.lt/index.php/MatSc/article/view/26098
[seam-f2f]: https://fibre2fashion.com/industry-article/110/seam-engineering
[seam-tl]: https://textilelearner.net/?p=1522

- XPBD: Macklin, Müller, Chentanez, "XPBD: Position-Based Simulation of Compliant Constrained Dynamics", MIG 2016 ([pdf][xpbd], [record][xpbd-rr]); Vellum note in [DiffXPBD][diffxpbd].
- Baraff & Witkin, "Large Steps in Cloth Simulation", SIGGRAPH 1998 ([pdf][bw98], [CMU][bw98-cmu]).
- Bergou, Wardetzky, Harmon, Zorin, Grinspun, "A Quadratic Bending Model for Inextensible Surfaces", SGP 2006 ([pdf][bergou]); Wardetzky et al., "Discrete Quadratic Curvature Energies", CAGD 2007 ([pdf][wardetzky]).
- Motevalli & Balzani, orthotropic hyperelastic woven-membrane model ([pdf][motevalli]).
- Wang, O'Brien, Ramamoorthi, "Data-Driven Elastic Models for Cloth", ACM TOG 30(4) 2011 ([pdf][wang11]).
- KES-F bending and shear ranges for plain wovens ([KTU Materials Science][kes]).
- Seam strength rule (SPI x thread strength x 1.5 for 301): [Fibre2Fashion seam engineering][seam-f2f], [Textile Learner SPI][seam-tl].
