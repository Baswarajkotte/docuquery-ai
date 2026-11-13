from types import SimpleNamespace

import pytest

from app.services import answer as answer_module
from app.services.answer import Passage, answer_question, extractive_answer
from app.services.chunker import chunk_pages
from app.services.retriever import BM25, tokenize


def test_tokenize_drops_stopwords_and_punctuation():
    assert tokenize("What is the Refund-Policy?") == ["refund", "policy"]


def test_chunker_overlaps_windows():
    words = " ".join(f"w{i}" for i in range(10))
    chunks = chunk_pages([words], size=4, overlap=2)
    assert [c.text for c in chunks] == [
        "w0 w1 w2 w3",
        "w2 w3 w4 w5",
        "w4 w5 w6 w7",
        "w6 w7 w8 w9",
    ]
    assert all(c.page == 1 for c in chunks)


def test_chunker_keeps_page_numbers_and_skips_blank_pages():
    chunks = chunk_pages(["alpha beta", "   ", "gamma"], size=5, overlap=1)
    assert [(c.page, c.text) for c in chunks] == [(1, "alpha beta"), (3, "gamma")]


def test_chunker_validates_arguments():
    with pytest.raises(ValueError):
        chunk_pages(["x"], size=3, overlap=3)


def test_bm25_ranks_relevant_document_first():
    index = BM25(
        [
            "python fastapi backend rest api",
            "cooking recipes with rice and dal",
            "deploying fastapi with docker on aws",
        ]
    )
    hits = index.top_k("fastapi docker deployment", k=3)
    assert hits[0].index == 2
    assert all(h.index != 1 for h in hits)


def test_extractive_answer_cites_passage():
    passages = [Passage("a.txt, page 1", "The office opens at 9 am. Parking is free.")]
    text = extractive_answer("When does the office open?", passages)
    assert text == "The office opens at 9 am. [1]"


def test_answer_uses_llm_when_available(monkeypatch):
    monkeypatch.setattr(answer_module, "llm_answer", lambda q, p: "From Claude [1]")
    text, mode = answer_question("q?", [Passage("x", "some text")])
    assert (text, mode) == ("From Claude [1]", "llm")


def test_answer_falls_back_when_llm_fails(monkeypatch):
    def boom(q, p):
        raise answer_module.LLMUnavailable("down")

    monkeypatch.setattr(answer_module, "llm_answer", boom)
    text, mode = answer_question("office open time", [Passage("x", "Office open time is 9.")])
    assert mode == "extractive"
    assert "Office open time is 9." in text


def test_llm_answer_handles_refusal(monkeypatch):
    fake_response = SimpleNamespace(stop_reason="refusal", content=[])

    class FakeClient:
        def __init__(self, **_):
            self.beta = SimpleNamespace(
                messages=SimpleNamespace(create=lambda **kwargs: fake_response)
            )

    monkeypatch.setattr(answer_module.anthropic, "Anthropic", FakeClient)
    monkeypatch.setattr(
        answer_module, "get_settings",
        lambda: SimpleNamespace(anthropic_api_key="k", llm_model="m", llm_max_tokens=10),
    )
    with pytest.raises(answer_module.LLMUnavailable):
        answer_module.llm_answer("q", [Passage("x", "y")])
