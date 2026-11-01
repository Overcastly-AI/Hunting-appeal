"""Seams between named piece edges and automated seam-length checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import curves as C
from .piece import EdgeRef

SEAM_TOL_MM = 1.0  # default matching tolerance (~1/32"); sewing error is larger than this


def _as_list(x) -> list[EdgeRef]:
    if isinstance(x, EdgeRef):
        return [x]
    lst = list(x)
    if not all(isinstance(e, EdgeRef) for e in lst):
        raise TypeError("seam sides must be EdgeRef (piece.edge(name)) or lists of them")
    return lst


@dataclass
class Seam:
    """A seam joining side A to side B. Each side is an edge or a list of consecutive edges
    (e.g. a bottom panel perimeter against three gusset edges).

    ``ease_mm`` is the intended excess of A over B: ``len(A) - len(B) == ease_mm``
    (A is eased onto B). ``stitch`` is the ISO 4915 stitch class (301 lockstitch, 401 chain,
    504/514 overlock, 516 safety, 607 cover)."""
    a: EdgeRef | Sequence[EdgeRef]
    b: EdgeRef | Sequence[EdgeRef]
    ease_mm: float = 0.0
    stitch: str = "301"
    name: str = ""
    spi: float | None = None
    notes: str = ""

    def __post_init__(self):
        self.a = _as_list(self.a)
        self.b = _as_list(self.b)
        if not self.name:
            self.name = f"{self.side_label(self.a)} <> {self.side_label(self.b)}"

    @staticmethod
    def side_label(side: list[EdgeRef]) -> str:
        return "+".join(e.label for e in side)

    @property
    def length_a(self) -> float:
        return sum(e.length for e in self.a)

    @property
    def length_b(self) -> float:
        return sum(e.length for e in self.b)

    @property
    def error_mm(self) -> float:
        """Deviation from the intended ease (0 = perfect)."""
        return self.length_a - self.length_b - self.ease_mm

    def add_match_notches(self, fractions: Iterable[float] = (0.5,), kind: str = "slit",
                          distances_mm: Iterable[float] = ()) -> None:
        """Add matching notches on both sides at the same fractions of each side's length
        (or at absolute distances from the start of side A / side B). Sides are walked
        in the order given; use ``edge.reversed()`` to walk an edge end-to-start."""
        for side in (self.a, self.b):
            pts: list = []
            for e in side:
                p = e.points
                pts.extend(p if not pts else p[1:])
            L = C.polyline_length(pts)
            targets = [f * L for f in fractions] + list(distances_mm)
            for s in targets:
                (x, y), _ = C.point_at_length(pts, s)
                # attach to the piece owning that stretch
                acc = 0.0
                for e in side:
                    if s <= acc + e.length + 1e-9:
                        e.piece.add_notch(x, y, kind, label=self.name)
                        break
                    acc += e.length

    def __repr__(self) -> str:
        return (f"Seam({self.name}: A={self.length_a:.1f} B={self.length_b:.1f} "
                f"ease={self.ease_mm} err={self.error_mm:+.2f} mm, {self.stitch})")


@dataclass
class SeamResult:
    seam: Seam
    length_a: float
    length_b: float
    error_mm: float
    ok: bool

    def line(self) -> str:
        flag = "OK " if self.ok else "MISMATCH"
        return (f"[{flag}] {self.seam.name}: A={self.length_a:.2f} mm, B={self.length_b:.2f} mm, "
                f"ease={self.seam.ease_mm:.2f}, error={self.error_mm:+.2f} mm "
                f"(stitch {self.seam.stitch})")


@dataclass
class SeamReport:
    results: list[SeamResult] = field(default_factory=list)
    tol_mm: float = SEAM_TOL_MM

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def mismatches(self) -> list[SeamResult]:
        return [r for r in self.results if not r.ok]

    def __bool__(self) -> bool:
        return self.ok

    def __str__(self) -> str:
        head = (f"Seam check: {len(self.results)} seams, {len(self.mismatches)} mismatches "
                f"(tolerance {self.tol_mm} mm)")
        return "\n".join([head] + [r.line() for r in self.results])

    def markdown(self) -> str:
        rows = ["| Seam | Stitch | A mm | B mm | Ease mm | Error mm | Status |",
                "|---|---|---:|---:|---:|---:|---|"]
        for r in self.results:
            rows.append(f"| {r.seam.name} | {r.seam.stitch} | {r.length_a:.1f} | {r.length_b:.1f} | "
                        f"{r.seam.ease_mm:.1f} | {r.error_mm:+.2f} | "
                        f"{'OK' if r.ok else '**MISMATCH**'} |")
        return "\n".join(rows)

    def assert_ok(self) -> None:
        if not self.ok:
            raise SeamMismatchError(str(self))


class SeamMismatchError(AssertionError):
    pass


def check_seams(seams: Iterable[Seam], tol_mm: float = SEAM_TOL_MM,
                raise_on_error: bool = False) -> SeamReport:
    """Check that every seam's sides match in length (within ``tol_mm``, after ease).

    Returns a :class:`SeamReport` (truthy when all seams match; ``.mismatches`` lists the
    failures). With ``raise_on_error=True`` raises :class:`SeamMismatchError` on any mismatch."""
    rep = SeamReport(tol_mm=tol_mm)
    for s in seams:
        la, lb = s.length_a, s.length_b
        err = la - lb - s.ease_mm
        rep.results.append(SeamResult(s, la, lb, err, abs(err) <= tol_mm))
    if raise_on_error:
        rep.assert_ok()
    return rep
