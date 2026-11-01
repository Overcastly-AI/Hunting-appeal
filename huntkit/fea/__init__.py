"""huntkit.fea - structural analysis for pack frames (contract: docs/CONTRACTS.md §2).

    from huntkit.fea import solve, tube_round, composite_tube, load_cases, report
    from huntkit.fea.frames import build_frame
"""
from . import composite, fatigue, joints, load_cases, plate  # noqa: F401
from .analysis import run_study, summarize  # noqa: F401
from .frame import Result, solve  # noqa: F401
from .load_cases import pack_standard  # noqa: F401
from .report import report  # noqa: F401
from .sections import composite_tube, flat_bar, generic, tube_rect, tube_round  # noqa: F401

__all__ = ["solve", "Result", "tube_round", "tube_rect", "flat_bar", "composite_tube", "generic",
           "pack_standard", "load_cases", "report", "run_study", "summarize", "composite",
           "fatigue", "joints", "plate"]
