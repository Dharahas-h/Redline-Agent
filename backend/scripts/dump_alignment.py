"""Diagnostic: show exactly what the paragraph aligner sees for two .docx files.

Usage (from the backend/ directory):

    python scripts/dump_alignment.py PRIOR.docx CURRENT.docx

Prints, for the two documents:
  1. The extracted + normalized paragraph text the aligner compares
     (with an <EMPTY> marker so blank paragraphs are visible).
  2. The ordered ops produced by align_paragraphs.
  3. For every replace region, the positional pairing and the char-level
     similarity ratio, so you can see why each pair became `modified`
     (ratio >= threshold) or degraded to `delete` + `insert`.
"""

from __future__ import annotations

import sys
from difflib import SequenceMatcher

# Make `src/` importable when run straight from backend/.
sys.path.insert(0, "src")

from redline_agent.redline.ooxml_writer import (  # noqa: E402
    W,
    _paragraph_text,
    _parse_document,
)
from redline_agent.redline.paragraph_align import (  # noqa: E402
    _MODIFIED_THRESHOLD,
    align_paragraphs,
    normalize,
)


def _show(text: str) -> str:
    norm = normalize(text)
    return "<EMPTY>" if norm == "" else norm


def main(prev_path: str, curr_path: str, threshold: float) -> None:
    prev_root = _parse_document(open(prev_path, "rb").read())
    curr_root = _parse_document(open(curr_path, "rb").read())

    prev_paras = prev_root.find(W + "body").findall(W + "p")
    curr_paras = curr_root.find(W + "body").findall(W + "p")

    prev_texts = [_paragraph_text(p) for p in prev_paras]
    curr_texts = [_paragraph_text(p) for p in curr_paras]

    print(f"\n=== PRIOR: {len(prev_texts)} body paragraphs ===")
    for i, t in enumerate(prev_texts):
        print(f"  [{i:3}] {_show(t)!r}")

    print(f"\n=== CURRENT: {len(curr_texts)} body paragraphs ===")
    for j, t in enumerate(curr_texts):
        print(f"  [{j:3}] {_show(t)!r}")

    # Raw opcodes over the paragraph lists (Layer 1).
    prev_norm = [normalize(t) for t in prev_texts]
    curr_norm = [normalize(t) for t in curr_texts]
    matcher = SequenceMatcher(a=prev_norm, b=curr_norm, autojunk=False)
    print("\n=== RAW SequenceMatcher opcodes (Layer 1) ===")
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        print(f"  {tag:8} prev[{i1}:{i2}] curr[{j1}:{j2}]")

    # Pairwise ratios inside each replace region (Layer 2).
    print(f"\n=== Replace-region pairing (threshold={threshold}) ===")
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "replace":
            continue
        paired = min(i2 - i1, j2 - j1)
        print(f"  replace prev[{i1}:{i2}] curr[{j1}:{j2}]:")
        for off in range(paired):
            i, j = i1 + off, j1 + off
            ratio = SequenceMatcher(a=prev_norm[i], b=curr_norm[j]).ratio()
            verdict = "modified" if ratio >= threshold else "DELETE+INSERT"
            print(f"    prev[{i}] vs curr[{j}]  ratio={ratio:.3f}  -> {verdict}")
        for i in range(i1 + paired, i2):
            print(f"    prev[{i}] unpaired          -> delete")
        for j in range(j1 + paired, j2):
            print(f"    curr[{j}] unpaired          -> insert")

    print("\n=== Final ops (align_paragraphs) ===")
    for op in align_paragraphs(prev_texts, curr_texts, threshold):
        print(f"  {op.kind:9} prev={op.prev_index} curr={op.curr_index}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else _MODIFIED_THRESHOLD
    main(sys.argv[1], sys.argv[2], thr)
