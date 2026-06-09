"""Integration test: full 4-stage pipeline on fixture (stages 0 and 3 pending implementation)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills.ingest.main import run as ingest_run
from skills.translate.main import run as translate_run
from skills.translate.term_filter import scan


FIXTURE = str(Path(__file__).parent / "../fixtures/java-vue-sample")
OUTPUT = str(Path(__file__).parent / "../../output-test")


def test_pipeline_no_tech_leak():
    """SC-001: srs.md must contain zero tech terms."""
    ingest_run(FIXTURE)
    report = translate_run(FIXTURE, OUTPUT)
    srs_path = Path(OUTPUT) / "srs.md"
    if srs_path.exists():
        violations = scan(srs_path.read_text())
        assert violations == [], f"Tech terms leaked: {violations}"


def test_pipeline_srs_generated():
    """SC-002: SRS generation must succeed for mixed stacks."""
    ingest_run(FIXTURE)
    report = translate_run(FIXTURE, OUTPUT)
    assert (Path(OUTPUT) / "srs.md").exists()
    assert (Path(OUTPUT) / "hla.md").exists()


def test_pipeline_uml_coverage():
    """SC-003: UML coverage report must be present."""
    translate_run(FIXTURE, OUTPUT)
    assert (Path(OUTPUT) / "quality.json").exists()
