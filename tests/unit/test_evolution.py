"""Unit tests for evolution.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills.shared.quality_report import QualityReport
from skills.shared.evolution import run_refine_loop


def test_refine_stops_on_pass():
    report = QualityReport("test", "r1",
                           tech_agnostic_score=1.0,
                           completeness_score=0.9,
                           uml_coverage_score=0.95)
    calls = []
    run_refine_loop("test", lambda: None, lambda d: calls.append(d), report)
    assert len(calls) == 0


def test_max_refine_reached():
    report = QualityReport("test", "r1",
                           tech_agnostic_score=0.0,
                           completeness_score=0.5,
                           uml_coverage_score=0.5)

    def fake_eval():
        pass  # scores stay bad

    def fake_refine(dims):
        pass

    run_refine_loop("test", fake_eval, fake_refine, report)
    assert report.max_refine_reached is True
    assert report.refine_count == 3


def test_passes_after_first_refine():
    report = QualityReport("test", "r1",
                           tech_agnostic_score=0.0,
                           completeness_score=0.9,
                           uml_coverage_score=0.95)

    def fake_eval():
        report.tech_agnostic_score = 1.0

    run_refine_loop("test", fake_eval, lambda d: None, report)
    assert report.max_refine_reached is False
    assert report.refine_count == 1
