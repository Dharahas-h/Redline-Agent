"""Segmenter: canonical text -> ordered clauses via heading/numbering."""

from redline_agent.pipeline.segmenter import segment


def test_splits_numbered_sections_into_clauses():
    text = (
        "1. Payment\n"
        "Buyer shall pay within 30 days.\n"
        "2. Term\n"
        "This agreement lasts one year."
    )
    clauses = segment(text)
    assert [c.ordinal for c in clauses] == [0, 1]
    assert [c.number_label for c in clauses] == ["1", "2"]
    assert [c.heading for c in clauses] == ["Payment", "Term"]
    assert clauses[0].text == "1. Payment\nBuyer shall pay within 30 days."
    assert clauses[1].text == "2. Term\nThis agreement lasts one year."


def test_handles_multilevel_numbering():
    text = "1.1 Fees\nFees are due monthly.\n1.2 Taxes\nTaxes are extra."
    clauses = segment(text)
    assert [c.number_label for c in clauses] == ["1.1", "1.2"]


def test_inline_number_with_long_body_has_no_heading():
    text = "1. Buyer shall pay all invoices within thirty (30) days of receipt."
    clauses = segment(text)
    assert len(clauses) == 1
    assert clauses[0].number_label == "1"
    assert clauses[0].heading is None


def test_preamble_before_first_number_is_its_own_clause():
    text = "MASTER SERVICES AGREEMENT\n1. Scope\nProvider will do the work."
    clauses = segment(text)
    assert len(clauses) == 2
    assert clauses[0].number_label is None
    assert clauses[0].heading == "MASTER SERVICES AGREEMENT"
    assert clauses[1].number_label == "1"


def test_empty_text_yields_no_clauses():
    assert segment("") == []
