"""Flatten stage: .docx bytes -> canonical normalized text."""

from redline_agent.pipeline.flatten import flatten_docx
from tests.fixtures.docx_builder import make_docx


def test_flatten_joins_paragraphs_with_newlines():
    data = make_docx(["First paragraph.", "Second paragraph."])
    assert flatten_docx(data) == "First paragraph.\nSecond paragraph."


def test_flatten_normalizes_internal_whitespace():
    data = make_docx(["Payment   is\tdue   on time."])
    assert flatten_docx(data) == "Payment is due on time."


def test_flatten_strips_and_drops_empty_paragraphs():
    data = make_docx(["  Leading and trailing  ", "", "   ", "Next"])
    assert flatten_docx(data) == "Leading and trailing\nNext"


def test_flatten_is_deterministic():
    data = make_docx(["Alpha", "Beta"])
    assert flatten_docx(data) == flatten_docx(data)
