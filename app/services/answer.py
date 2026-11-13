"""Build an answer from retrieved passages.

Two modes:
* ``llm`` - Claude writes a grounded answer that cites passages as [1], [2] ...
* ``extractive`` - no API key (or the LLM call failed): return the passage
  sentences that best match the question. Works offline and costs nothing.
"""

import logging
import re
from dataclasses import dataclass

import anthropic

from app.config import get_settings
from app.services.retriever import tokenize

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You answer questions using only the numbered passages the user provides. "
    "Cite passages inline as [1], [2] after the sentences they support. "
    "If the passages do not contain the answer, say you could not find it in the "
    "uploaded documents instead of guessing. Keep answers under 200 words."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Passage:
    label: str
    text: str


def build_prompt(question: str, passages: list[Passage]) -> str:
    blocks = "\n\n".join(f"[{i}] ({p.label})\n{p.text}" for i, p in enumerate(passages, 1))
    return f"Passages:\n\n{blocks}\n\nQuestion: {question}"


def extractive_answer(question: str, passages: list[Passage], max_sentences: int = 3) -> str:
    if not passages:
        return "I could not find anything about that in your documents."
    query_terms = set(tokenize(question))
    candidates: list[tuple[float, int, str]] = []
    for idx, passage in enumerate(passages, 1):
        for sentence in _SENTENCE_SPLIT.split(passage.text):
            terms = set(tokenize(sentence))
            if not terms:
                continue
            overlap = len(query_terms & terms)
            if overlap:
                # Earlier (higher-ranked) passages win ties.
                candidates.append((overlap - idx * 0.01, idx, sentence.strip()))
    if not candidates:
        return "I could not find anything about that in your documents."
    candidates.sort(key=lambda c: c[0], reverse=True)
    best = candidates[:max_sentences]
    return " ".join(f"{sentence} [{idx}]" for _, idx, sentence in best)


class LLMUnavailable(RuntimeError):
    pass


def llm_answer(question: str, passages: list[Passage]) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.beta.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_prompt(question, passages)}],
            output_config={"effort": "low"},
            # If the model declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIConnectionError as exc:
        raise LLMUnavailable(f"Could not reach the Claude API: {exc}") from exc
    except anthropic.RateLimitError as exc:
        raise LLMUnavailable("Claude API rate limit reached") from exc
    except anthropic.APIStatusError as exc:
        raise LLMUnavailable(f"Claude API error {exc.status_code}") from exc

    if response.stop_reason == "refusal":
        raise LLMUnavailable("The model declined to answer")

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise LLMUnavailable("Empty response from the model")
    return text


def answer_question(question: str, passages: list[Passage]) -> tuple[str, str]:
    """Return ``(answer, mode)``. Falls back to extractive mode on any LLM problem."""
    if passages:
        try:
            return llm_answer(question, passages), "llm"
        except LLMUnavailable as exc:
            logger.info("Using extractive answer: %s", exc)
    return extractive_answer(question, passages), "extractive"
