"""Table-change detection: detect-and-flag only, never a cell-level diff."""

from redline_agent.pipeline.tables import (
    detect_table_changes,
    extract_table_signatures,
)
from tests.fixtures.docx_builder import make_docx


def test_extracts_a_signature_per_table():
    data = make_docx(
        ["1. Pricing"],
        tables=[[["Item", "Price"], ["Widget", "$10"]]],
    )
    (sig,) = extract_table_signatures(data)
    assert "Item" in sig and "Widget" in sig and "$10" in sig


def test_document_without_tables_has_no_signatures():
    assert extract_table_signatures(make_docx(["1. Payment", "No tables here."])) == []


def test_identical_tables_produce_no_change():
    prev = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"], ["Widget", "$10"]]])
    )
    curr = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"], ["Widget", "$10"]]])
    )
    assert detect_table_changes(prev, curr) == []


def test_a_modified_cell_flags_the_table():
    prev = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"], ["Widget", "$10"]]])
    )
    curr = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"], ["Widget", "$15"]]])
    )
    (change,) = detect_table_changes(prev, curr)
    assert change.position == 1
    assert change.kind == "modified"


def test_an_added_table_is_flagged():
    prev = extract_table_signatures(make_docx(["1. Pricing"]))
    curr = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"]]])
    )
    (change,) = detect_table_changes(prev, curr)
    assert change.position == 1
    assert change.kind == "added"


def test_a_removed_table_is_flagged():
    prev = extract_table_signatures(
        make_docx(["1. Pricing"], tables=[[["Item", "Price"]]])
    )
    curr = extract_table_signatures(make_docx(["1. Pricing"]))
    (change,) = detect_table_changes(prev, curr)
    assert change.kind == "removed"
