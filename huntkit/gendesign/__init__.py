"""huntkit.gendesign - generative design for the Pack 5200 carbon frame (owner: structural-fea-engineer).

    simp      3D (H8 voxel) / 2D (Q4) SIMP with density filter, Heaviside projection, passive regions,
              multi-load-case compliance, AMG-preconditioned CG (fem.py)
    lugs      topology-optimized printed node lugs (SLM Ti-6Al-4V / FDM PAHT-CF) from frame member end forces
    plate     2D SIMP lumbar plate -> carbon-sheet cut pattern (DXF) with CLT / Tsai-Wu + web buckling checks
    layout    frame ground-structure LP (axial + bending + torsion) and discrete brace check on buyable tubes
    printables  crown rack, pawl, pulley guides; cost / print-time model
    surface   marching cubes -> smooth watertight STL/3MF, exact socket booleans, print orientation
    cli       python -m huntkit.gendesign.cli stage lugs|plate|plate_v2|layout|printables|report
"""
from .simp import SimpProblem, SimpResult, run_simp  # noqa: F401
