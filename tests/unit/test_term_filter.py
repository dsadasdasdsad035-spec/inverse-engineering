"""Unit tests for term_filter."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from skills.translate.term_filter import scan, is_clean


def test_detects_language_name():
    assert "Java" in scan("The Java service handles requests")


def test_clean_text_passes():
    assert is_clean("用户可以提交订单，系统记录操作结果。")


def test_detects_framework():
    assert len(scan("Use Spring Boot for the backend")) > 0


def test_annotation_detected():
    assert "@Transactional" in scan("Method has @Transactional annotation")
