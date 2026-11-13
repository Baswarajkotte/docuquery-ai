"""BM25 ranking over document chunks.

BM25 is the ranking function used by search engines such as Elasticsearch.
It needs no external service or embedding model, so the API runs fully offline.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    """a an and are as at be by for from has have how i in is it its of on or that the
    this to was were what when where which who why will with you your do does did can
    about into than then there these those they them their our we us""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


@dataclass
class Ranked:
    index: int
    score: float


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(d) for d in documents]
        self.term_freqs = [Counter(d) for d in self.docs]
        self.doc_len = [len(d) for d in self.docs]
        self.avg_len = (sum(self.doc_len) / len(self.docs)) if self.docs else 0.0

        doc_freq: Counter[str] = Counter()
        for doc in self.docs:
            doc_freq.update(set(doc))
        n = len(self.docs)
        # Okapi BM25 idf, floored at a small positive value so very common
        # terms still count a little instead of going negative.
        self.idf = {
            term: max(math.log((n - df + 0.5) / (df + 0.5) + 1), 0.01)
            for term, df in doc_freq.items()
        }

    def score(self, query: str, index: int) -> float:
        tf = self.term_freqs[index]
        length = self.doc_len[index]
        total = 0.0
        for term in tokenize(query):
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
            total += self.idf[term] * freq * (self.k1 + 1) / denom
        return total

    def top_k(self, query: str, k: int) -> list[Ranked]:
        scored = [Ranked(i, self.score(query, i)) for i in range(len(self.docs))]
        scored = [r for r in scored if r.score > 0]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]
