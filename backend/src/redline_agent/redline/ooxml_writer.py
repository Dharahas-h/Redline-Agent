"""OOXML tracked-changes writer.

Injects ``w:ins``/``w:del`` markup into a *copy of the prior document's* OOXML
so all of the prior document's formatting, styles, and numbering are preserved
verbatim (decision #4). Only the ``word/document.xml`` part is rewritten; every
other zip entry is passed through untouched.

Kept paragraphs are copied element-for-element from the prior document.
Modified paragraphs keep the prior paragraph's properties (``w:pPr`` — style
and numbering) and rebuild their runs from a word-level diff. Deleted and
inserted paragraphs are wrapped whole in ``w:del``/``w:ins``.
"""

from __future__ import annotations

import io
import zipfile
from copy import deepcopy

from lxml import etree

from redline_agent.redline.paragraph_align import align_paragraphs
from redline_agent.redline.word_diff import diff_words

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"
_DOCUMENT_PART = "word/document.xml"


def build_redline(
    prev_docx: bytes,
    curr_docx: bytes,
    author: str,
    date: str,
) -> bytes:
    """Return tracked-changes ``.docx`` bytes redlining ``curr`` over ``prev``."""
    prev_root = _parse_document(prev_docx)
    curr_root = _parse_document(curr_docx)

    prev_body = prev_root.find(W + "body")
    curr_body = curr_root.find(W + "body")
    prev_paras = prev_body.findall(W + "p")
    curr_paras = curr_body.findall(W + "p")

    ops = align_paragraphs(
        [_paragraph_text(p) for p in prev_paras],
        [_paragraph_text(p) for p in curr_paras],
    )

    counter = _IdCounter()
    built = [
        _build_paragraph(op, prev_paras, curr_paras, author, date, counter)
        for op in ops
    ]

    _replace_paragraphs(prev_body, built)
    new_document = etree.tostring(
        prev_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    return _rewrite_zip(prev_docx, new_document)


class _IdCounter:
    def __init__(self) -> None:
        self._value = 0

    def next(self) -> str:
        self._value += 1
        return str(self._value)


def _parse_document(docx_bytes: bytes) -> etree._Element:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        return etree.fromstring(zf.read(_DOCUMENT_PART))


def _paragraph_text(paragraph: etree._Element) -> str:
    return "".join(t.text or "" for t in paragraph.iter(W + "t"))


def _replace_paragraphs(
    body: etree._Element, paragraphs: list[etree._Element]
) -> None:
    """Swap the body's paragraphs for the built ones, keeping trailing parts.

    Non-paragraph children (notably the body-level ``w:sectPr``) are preserved
    in their original order after the paragraphs.
    """
    trailing = [child for child in body if child.tag != W + "p"]
    for child in list(body):
        body.remove(child)
    for paragraph in paragraphs:
        body.append(paragraph)
    for child in trailing:
        body.append(child)


def _build_paragraph(
    op,
    prev_paras: list[etree._Element],
    curr_paras: list[etree._Element],
    author: str,
    date: str,
    counter: _IdCounter,
) -> etree._Element:
    if op.kind == "equal":
        return deepcopy(prev_paras[op.prev_index])

    if op.kind == "delete":
        source = prev_paras[op.prev_index]
        return _paragraph_from_segments(
            source, [("delete", _paragraph_text(source))], author, date, counter
        )

    if op.kind == "insert":
        source = curr_paras[op.curr_index]
        return _paragraph_from_segments(
            source, [("insert", _paragraph_text(source))], author, date, counter
        )

    # modified: keep prior paragraph properties, word-diff the runs.
    prev_p = prev_paras[op.prev_index]
    curr_p = curr_paras[op.curr_index]
    segments = [
        (seg.op, seg.text)
        for seg in diff_words(_paragraph_text(prev_p), _paragraph_text(curr_p))
    ]
    return _paragraph_from_segments(prev_p, segments, author, date, counter)


def _paragraph_from_segments(
    source_paragraph: etree._Element,
    segments: list[tuple[str, str]],
    author: str,
    date: str,
    counter: _IdCounter,
) -> etree._Element:
    """Build a ``w:p`` reusing the source's ``w:pPr`` and marking each segment."""
    paragraph = etree.Element(W + "p")
    p_pr = source_paragraph.find(W + "pPr")
    if p_pr is not None:
        paragraph.append(deepcopy(p_pr))

    for index, (op, text) in enumerate(segments):
        spaced = text if index == len(segments) - 1 else text + " "
        if op == "equal":
            paragraph.append(_run(spaced))
        elif op == "insert":
            paragraph.append(
                _revision(W + "ins", _run(spaced), author, date, counter)
            )
        elif op == "delete":
            paragraph.append(
                _revision(
                    W + "del", _run(spaced, deleted=True), author, date, counter
                )
            )
    return paragraph


def _run(text: str, deleted: bool = False) -> etree._Element:
    run = etree.Element(W + "r")
    tag = W + "delText" if deleted else W + "t"
    text_el = etree.SubElement(run, tag)
    text_el.set(f"{{{XML_NS}}}space", "preserve")
    text_el.text = text
    return run


def _revision(
    tag: str,
    run: etree._Element,
    author: str,
    date: str,
    counter: _IdCounter,
) -> etree._Element:
    revision = etree.Element(tag)
    revision.set(W + "id", counter.next())
    revision.set(W + "author", author)
    revision.set(W + "date", date)
    revision.append(run)
    return revision


def _rewrite_zip(prev_docx: bytes, new_document: bytes) -> bytes:
    """Copy the prior ``.docx`` zip, replacing only ``word/document.xml``."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(prev_docx)) as source:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dest:
            for item in source.infolist():
                data = (
                    new_document
                    if item.filename == _DOCUMENT_PART
                    else source.read(item.filename)
                )
                dest.writestr(item, data)
    return out.getvalue()
