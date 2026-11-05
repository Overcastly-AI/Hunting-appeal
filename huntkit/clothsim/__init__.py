"""huntkit.clothsim: batch cloth and pack simulator (phase 1).

Flat pattern pieces -> sewn 3D mesh -> static equilibrium under gravity, fill pressure, straps and
rigid frame/spreader contact. Contract: docs/CONTRACTS.md section 7. Method and validation:
docs/research/cloth_sim_methods.md, designs/pack_5200/analysis/cloth_sim.md.
"""
from .assemble import PieceSpec, assemble
from .fabric import FabricModel, fabric, seam_strength_n_mm, stitch_strength_n_mm
from .mesh import ClothMesh, MeshPiece, build_mesh, triangulate_loop
from .model import (Anchor, Bending, Cable, Cables, Contact, DeadLoad, Gravity, Membrane, Pins, Pressure,
                    Sim, SolveInfo)

__all__ = ["PieceSpec", "assemble", "FabricModel", "fabric", "seam_strength_n_mm", "stitch_strength_n_mm",
           "ClothMesh", "MeshPiece", "build_mesh", "triangulate_loop", "Anchor", "Bending", "Cable", "Cables",
           "Contact", "DeadLoad", "Gravity", "Membrane", "Pins", "Pressure", "Sim", "SolveInfo"]
