"""
Local support corpus indexing and retrieval for Support Triage Agent.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).parent.parent / "data"

COMPANY_TO_DIR = {
    "HackerRank": DATA_DIR / "hackerrank",
    "Claude": DATA_DIR / "claude",
    "Visa": DATA_DIR / "visa",
}

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
TOP_K = 6


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_words(words: List[str]) -> List[str]:
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for start in range(0, max(1, len(words) - CHUNK_OVERLAP), step):
        chunk = words[start : start + CHUNK_SIZE]
        if len(chunk) >= 20:
            chunks.append(" ".join(chunk))
    return chunks


def _load_file(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return _clean_text(raw)


class Corpus:
    """
    Loads documents from the local data directories and exposes TF-IDF retrieval.
    """

    def __init__(self):
        self.chunks: List[str] = []
        self.metadata: List[Dict[str, str]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._build()

    def _build(self) -> None:
        print("[Retriever] Loading corpus...", flush=True)
        for company, directory in COMPANY_TO_DIR.items():
            if not directory.exists():
                print(f"  [warn] {directory} not found - skipping {company}", flush=True)
                continue

            files = [
                path
                for path in directory.rglob("*")
                if path.is_file()
                and path.suffix.lower() in {".txt", ".md", ".html", ".htm", ".json", ".csv"}
            ]

            for filepath in files:
                text = _load_file(filepath)
                if not text:
                    continue
                for chunk in _chunk_words(text.split()):
                    self.chunks.append(chunk)
                    self.metadata.append({"company": company, "filepath": str(filepath)})

        if not self.chunks:
            raise RuntimeError("Corpus is empty - make sure data/ contains the support files.")

        print(
            f"[Retriever] {len(self.chunks)} chunks across {len(COMPANY_TO_DIR)} companies",
            flush=True,
        )

        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=60_000,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(self.chunks)

    def retrieve(
        self,
        query: str,
        company: str = None,
        top_k: int = TOP_K,
    ) -> List[Tuple[str, str, float]]:
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix).flatten()

        if company and company in COMPANY_TO_DIR:
            mask = np.array([meta["company"] == company for meta in self.metadata])
            scores = scores * mask

        ranked = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in ranked:
            if scores[idx] < 1e-6:
                break
            results.append(
                (
                    self.chunks[idx],
                    self.metadata[idx]["company"],
                    float(scores[idx]),
                )
            )
        return results


_corpus: Corpus | None = None


def get_corpus() -> Corpus:
    global _corpus
    if _corpus is None:
        _corpus = Corpus()
    return _corpus
