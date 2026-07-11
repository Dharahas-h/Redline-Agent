"""FakeEmbedder: deterministic, offline, similarity reflects lexical overlap."""

import math

from redline_agent.infra.embedder import FakeEmbedder


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def test_is_deterministic():
    e = FakeEmbedder()
    first = await e.embed(["Buyer shall pay", "Governing law"])
    second = await e.embed(["Buyer shall pay", "Governing law"])
    assert first == second


async def test_similar_text_scores_higher_than_dissimilar():
    e = FakeEmbedder()
    vecs = await e.embed(
        [
            "Buyer shall pay within 30 days",
            "Buyer shall pay within 45 days",
            "Either party may terminate for convenience",
        ]
    )
    near = _cosine(vecs[0], vecs[1])
    far = _cosine(vecs[0], vecs[2])
    assert near > far
    assert near > 0.75  # heavy lexical overlap
    assert far == 0.0  # no shared tokens


async def test_identical_text_has_similarity_one():
    e = FakeEmbedder()
    v1, v2 = await e.embed(["Confidential Information", "confidential information"])
    assert math.isclose(_cosine(v1, v2), 1.0)


async def test_reports_a_model_name():
    assert FakeEmbedder().model_name == "fake-embedder"
