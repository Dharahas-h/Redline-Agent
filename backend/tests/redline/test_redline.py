"""Golden-file tests for the standalone ``redline()`` export.

Each case builds a hand-crafted prev/curr ``.docx`` pair, runs ``redline()``,
and asserts the emitted OOXML carries the correct ``w:ins``/``w:del`` markup and
re-opens cleanly as a document. The moved-paragraph case documents the accepted
tradeoff that a move renders as delete + insert (decision #4).
"""

from __future__ import annotations

import io
import zipfile

from docx import Document
from lxml import etree

from redline_agent.redline import redline
from tests.fixtures.docx_builder import make_docx

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _document_root(docx_bytes: bytes) -> etree._Element:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        xml = zf.read("word/document.xml")
    return etree.fromstring(xml)


def _ins_texts(root: etree._Element) -> list[str]:
    return [
        (t.text or "")
        for ins in root.iter(W + "ins")
        for t in ins.iter(W + "t")
    ]


def _del_texts(root: etree._Element) -> list[str]:
    return [
        (t.text or "")
        for delel in root.iter(W + "del")
        for t in delel.iter(W + "delText")
    ]


def _joined(texts: list[str]) -> str:
    return " ".join(t.strip() for t in texts).strip()


def test_output_reopens_as_valid_docx():
    prev = make_docx(["Alpha", "Bravo"])
    curr = make_docx(["Alpha", "Bravo", "Charlie"])

    out = redline(prev, curr)

    # Re-opening with python-docx proves the package is structurally valid.
    Document(io.BytesIO(out))


def test_insertion_marked_with_w_ins():
    prev = make_docx(["Alpha", "Bravo"])
    curr = make_docx(["Alpha", "Bravo", "Charlie inserted"])

    root = _document_root(redline(prev, curr))

    assert "Charlie inserted" in _joined(_ins_texts(root))
    assert _del_texts(root) == []


def test_deletion_marked_with_w_del():
    prev = make_docx(["Alpha", "Bravo deleted", "Charlie"])
    curr = make_docx(["Alpha", "Charlie"])

    root = _document_root(redline(prev, curr))

    assert "Bravo deleted" in _joined(_del_texts(root))
    assert _ins_texts(root) == []


def test_modified_paragraph_word_diffs_inline():
    prev = make_docx(["Alpha", "Buyer pays in 30 days."])
    curr = make_docx(["Alpha", "Buyer pays in 45 days."])

    root = _document_root(redline(prev, curr))

    # Only the changed words are marked; the unchanged words survive as plain
    # runs (not re-inserted/re-deleted).
    assert "30" in _joined(_del_texts(root))
    assert "45" in _joined(_ins_texts(root))
    assert "Buyer" not in _joined(_del_texts(root))
    assert "Buyer" not in _joined(_ins_texts(root))


def test_moved_paragraph_renders_as_delete_plus_insert():
    # Accepted tradeoff (decision #4): a moved paragraph is delete + insert.
    prev = make_docx(["First", "Second", "Third"])
    curr = make_docx(["Second", "Third", "First"])

    root = _document_root(redline(prev, curr))

    assert "First" in _joined(_del_texts(root))
    assert "First" in _joined(_ins_texts(root))


def test_original_formatting_and_numbering_preserved():
    # Markup is injected into a copy of the prior document's OOXML, so the
    # prior document's styled/numbered paragraphs survive unchanged.
    prev = make_docx([("Heading 1", "Agreement"), "Body one.", "Body two."])
    curr = make_docx([("Heading 1", "Agreement"), "Body one.", "Body two changed."])

    out = redline(prev, curr)
    root = _document_root(out)

    # The heading paragraph's style reference from prev is still present.
    styles = [
        s.get(W + "val")
        for s in root.iter(W + "pStyle")
    ]
    assert any(s and "Heading" in s for s in styles)


def test_changes_attributed_to_submitting_party():
    prev = make_docx(["Alpha"])
    curr = make_docx(["Alpha", "Beta"])

    root = _document_root(redline(prev, curr, author="Seller"))

    authors = {
        el.get(W + "author")
        for el in root.iter(W + "ins", W + "del")
    }
    assert authors == {"Seller"}


def test_redline_package_does_not_import_pipeline_or_domain():
    # Decision #4: the export is standalone. No import path may reach the
    # pipeline or domain packages.
    import redline_agent.redline as pkg
    import importlib
    import pkgutil

    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        module = importlib.import_module(mod.name)
        source = getattr(module, "__file__", "")
        assert source
    # Static check: no submodule may reference the forbidden packages.
    import pathlib

    root = pathlib.Path(pkg.__path__[0])
    for path in root.glob("*.py"):
        text = path.read_text()
        assert "redline_agent.pipeline" not in text
        assert "redline_agent.domain" not in text
