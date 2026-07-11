"""Defined-term detection: which definitions changed, and their ripple count."""

from redline_agent.pipeline.defined_terms import (
    count_references,
    detect_definition_changes,
    extract_definitions,
)


def test_extracts_a_quoted_term_and_its_definition():
    defs = extract_definitions(['"Confidential Information" means any non-public data.'])
    assert "confidential information" in defs
    term, definition = defs["confidential information"]
    assert term == "Confidential Information"
    assert definition == "any non-public data."


def test_extracts_shall_mean_and_curly_quotes():
    defs = extract_definitions(["“Effective Date” shall mean January 1, 2026."])
    assert defs["effective date"][1] == "January 1, 2026."


def test_several_definitions_in_one_clause():
    text = '"Buyer" means Acme Corp. "Seller" means Globex Inc.'
    defs = extract_definitions([text])
    assert defs["buyer"][1] == "Acme Corp."
    assert defs["seller"][1] == "Globex Inc."


def test_a_changed_definition_is_detected():
    prev = ['"Term" means twelve (12) months.', "The Term auto-renews."]
    curr = ['"Term" means twenty-four (24) months.', "The Term auto-renews."]
    (change,) = detect_definition_changes(prev, curr)
    assert change.term == "Term"
    assert change.definition_before == "twelve (12) months."
    assert change.definition_after == "twenty-four (24) months."


def test_unchanged_definition_is_not_flagged():
    prev = ['"Term" means twelve (12) months.']
    curr = ['"Term" means twelve (12) months.', "An unrelated new clause."]
    assert detect_definition_changes(prev, curr) == []


def test_a_newly_added_definition_is_not_a_change():
    # A term that did not exist before is a new definition, not a redefinition.
    prev = ['"Buyer" means Acme.']
    curr = ['"Buyer" means Acme.', '"Seller" means Globex.']
    assert detect_definition_changes(prev, curr) == []


def test_reference_count_excludes_the_defining_clause():
    curr = [
        '"Confidential Information" means non-public data.',
        "Confidential Information must be protected.",
        "Return all Confidential Information on termination.",
        "This clause mentions nothing relevant.",
    ]
    # Two clauses reference the term; the defining clause is excluded.
    assert count_references("Confidential Information", curr) == 2


def test_definition_change_carries_the_affected_clause_count():
    prev = ['"Fee" means $100.']
    curr = [
        '"Fee" means $200.',
        "Buyer shall pay the Fee monthly.",
        "The Fee is non-refundable.",
    ]
    (change,) = detect_definition_changes(prev, curr)
    assert change.affected_clause_count == 2
