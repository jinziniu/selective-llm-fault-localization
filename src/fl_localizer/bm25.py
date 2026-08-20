from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

from fl_localizer.text import tokenize


@dataclass(frozen=True)
class RankedItem:
    rank: int
    file: str
    score: float


class BM25Index:
    def __init__(self, documents: list[tuple[str, str]], *, k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(text) for _, text in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_length = (
            sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        )
        self.term_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_freqs: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.doc_freqs.update(set(tokens))

    def rank(self, query: str, *, top_k: int = 10) -> list[RankedItem]:
        query_terms = tokenize(query)
        scores: list[tuple[str, float]] = []
        for index, (file_path, _) in enumerate(self.documents):
            score = self._score_document(index, query_terms)
            scores.append((file_path, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return [
            RankedItem(rank=rank, file=file_path, score=round(score, 6))
            for rank, (file_path, score) in enumerate(scores[:top_k], start=1)
        ]

    def _score_document(self, index: int, query_terms: list[str]) -> float:
        if not self.documents or self.avg_doc_length == 0:
            return 0.0

        doc_length = self.doc_lengths[index]
        term_freq = self.term_freqs[index]
        score = 0.0
        number_of_docs = len(self.documents)

        for term in query_terms:
            frequency = term_freq.get(term, 0)
            if frequency == 0:
                continue
            doc_frequency = self.doc_freqs[term]
            idf = math.log(1 + (number_of_docs - doc_frequency + 0.5) / (doc_frequency + 0.5))
            denominator = frequency + self.k1 * (
                1 - self.b + self.b * doc_length / self.avg_doc_length
            )
            score += idf * (frequency * (self.k1 + 1)) / denominator
        return score

