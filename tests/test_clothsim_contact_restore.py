"""BL-025 regression: a stopped contact-rounding continuation must report on the KEPT stage.

Before the fix, run_case restored x to the last converged stage but left every contact_* term on the
gap field of the failed (sharper) stage, so contact forces were computed on the wrong field. These
tests drive run_case with a cheap fake model (real FieldContact terms on analytic plane fields) so the
check runs in milliseconds and the reported force can be compared with a hand value.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from huntkit.clothsim.model import FieldContact, SolveInfo
from huntkit.clothsim.pack import run_case


class Plane:
    """Gap to the plane z = z0 (gap = z - z0, normal +z). ``z0`` stands in for the rounding: a
    rounded field sits a little off the raw surface, so each stage gives a different contact force."""

    def __init__(self, z0, tag):
        self.z0, self.tag = float(z0), tag

    def __call__(self, q):
        q = np.atleast_2d(q)
        return q[:, 2] - self.z0, np.tile([0.0, 0.0, 1.0], (len(q), 1))


class FakeSim:
    """Terms: two contact fields plus an empty cable set. ``solve`` leaves x alone and converges
    unless any contact term sits on a field tagged in ``fail_tags``."""

    def __init__(self, fields, fail_tags):
        self.terms = [FieldContact(fields["spreader"], kc=10.0, clearance=0.0, label="contact_spreader"),
                      FieldContact(fields["frame"], kc=10.0, clearance=0.0, label="contact_frame"),
                      SimpleNamespace(name="cables", cables=[])]
        self.fail = set(fail_tags)
        self.solved_on = []

    def term(self, name):
        return next((t for t in self.terms if getattr(t, "name", "") == name), None)

    def solve(self, x, tol, max_iter, time_cap, verbose=False):
        tags = tuple(t.f.tag for t in self.terms if isinstance(t, FieldContact))
        self.solved_on.append(tags)
        ok = not (set(tags) & self.fail)
        return x.copy(), SolveInfo(converged=ok, iterations=3, residual_n=0.0 if ok else 9.0, energy=0.0, seconds=0.01)


def _fake_pm(cont, fail_tags):
    # rounded fields sit 2, 1 mm above the raw surface at z = 0; nodes at z = -5 penetrate all of them
    smooth = {"spreader": Plane(3.0, "s6"), "frame": Plane(3.0, "s6")}
    raw = {"spreader": Plane(0.0, "s0"), "frame": Plane(0.0, "s0")}
    cache = {(k, 3.0): Plane(2.0, "s3") for k in raw}
    cache.update({(k, 1.5): Plane(1.0, "s1.5") for k in raw})
    sim = FakeSim(smooth, fail_tags)
    pm = SimpleNamespace(
        scen={"solver": {"ramp": [1.0], "tol_n": 1.0, "max_iter": 5, "time_cap_s": 60, "recinch": False},
              "contact": {"smooth_mm": 6.0, "smooth_continuation": cont}},
        mesh=SimpleNamespace(X0=np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0]])),
        fields_raw=raw, _fcache=cache, build_sim=lambda case, cinched=True: sim)
    return pm, sim


def _force(sim, x, name):
    idx, f = sim.term(name).forces(x)
    return float(np.linalg.norm(f.sum(0)))


def test_stopped_continuation_reports_on_the_kept_stage_fields():
    # 6 -> 3 converges, 1.5 converges, 0 (raw) fails: the kept stage is 1.5 mm
    pm, sim = _fake_pm([3.0, 1.5, 0.0], fail_tags={"s0"})
    x, sim2, infos = run_case(pm, {})
    assert sim2.contact_rounding_mm == 1.5
    assert "kept the last converged stage" in infos[-1].reason
    for nm in ("contact_spreader", "contact_frame"):
        assert sim2.term(nm).f.tag == "s1.5"           # field of the kept stage, not "s0"
        # hand value: 2 nodes, gap -5 - 1 = -6 mm, kc 10 N/mm -> 2 * 60 = 120 N (raw field would give 100 N)
        assert _force(sim2, x, nm) == pytest.approx(120.0)


def test_failure_on_first_continuation_stage_restores_the_smoothed_field():
    pm, sim = _fake_pm([3.0, 0.0], fail_tags={"s3"})
    x, sim2, infos = run_case(pm, {})
    assert sim2.contact_rounding_mm == 6.0
    assert all(sim2.term(n).f.tag == "s6" for n in ("contact_spreader", "contact_frame"))
    assert _force(sim2, x, "contact_spreader") == pytest.approx(2 * 10.0 * 8.0)


def test_full_continuation_ends_on_the_raw_field():
    pm, sim = _fake_pm([3.0, 0.0], fail_tags=set())
    x, sim2, infos = run_case(pm, {})
    assert sim2.contact_rounding_mm == 0.0
    assert sim2.term("contact_spreader").f.tag == "s0"
    assert _force(sim2, x, "contact_frame") == pytest.approx(100.0)
