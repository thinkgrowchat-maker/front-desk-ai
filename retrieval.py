"""
retrieval.py — dependency-free semantic retrieval over the knowledge base.

This is the "R" in RAG (Retrieval-Augmented Generation). It ranks knowledge-base
entries against a guest's question using TF-IDF vectors and cosine similarity —
real vector-space retrieval that runs offline with zero API calls and zero
dependencies.

For a small, curated knowledge base this is fast, accurate, and — importantly —
explainable: we can show the exact similarity score for every entry, which is
what powers the "Retrieval Inspector" panel in the UI. For a very large corpus
you would swap this module for an embeddings model (e.g. Voyage); the rest of
the app would not change.
"""

import math
import re
from collections import Counter

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "could", "do",
    "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "is", "it",
    "its", "me", "my", "of", "on", "or", "our", "so", "that", "the", "their", "them",
    "there", "they", "this", "to", "was", "we", "what", "when", "where", "which",
    "who", "will", "with", "would", "you", "your", "yours", "get", "got", "any",
}


def tokenize(text):
    """Lowercase, split into words, drop stopwords, and lightly de-pluralize."""
    tokens = []
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) < 2 or word in _STOPWORDS:
            continue
        # light stemming: collapse simple plurals ("dogs" -> "dog")
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        tokens.append(word)
    return tokens


def _tfidf_vector(tokens, idf):
    """Build an L2-normalized sparse TF-IDF vector (dict term -> weight)."""
    counts = Counter(tokens)
    vec = {}
    for term, count in counts.items():
        weight = count * idf.get(term, 0.0)
        if weight:
            vec[term] = weight
    norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
    return {term: w / norm for term, w in vec.items()}


def build_index(docs):
    """Pre-compute IDF weights and a TF-IDF vector for every document."""
    n = len(docs)
    doc_tokens = [
        tokenize(" ".join([d["title"], d["text"], " ".join(d.get("keywords", []))]))
        for d in docs
    ]

    doc_freq = Counter()
    for tokens in doc_tokens:
        for term in set(tokens):
            doc_freq[term] += 1

    # smoothed inverse-document-frequency
    idf = {term: math.log((n + 1) / (freq + 1)) + 1 for term, freq in doc_freq.items()}

    vectors = [_tfidf_vector(tokens, idf) for tokens in doc_tokens]
    return {"docs": docs, "idf": idf, "vectors": vectors}


def _cosine(a, b):
    """Dot product of two L2-normalized sparse vectors == cosine similarity."""
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(term, 0.0) for term, w in a.items())


def search(index, query, top_k=3, min_score=0.05):
    """Return the top_k most relevant documents with their similarity scores."""
    query_vec = _tfidf_vector(tokenize(query), index["idf"])
    scored = [
        {"doc": index["docs"][i], "score": _cosine(query_vec, vec)}
        for i, vec in enumerate(index["vectors"])
    ]
    scored.sort(key=lambda s: s["score"], reverse=True)
    return [s for s in scored if s["score"] >= min_score][:top_k]
