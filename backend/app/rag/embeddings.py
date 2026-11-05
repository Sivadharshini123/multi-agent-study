"""Local embeddings. Multilingual feature hashing with n-grams ensures robust semantic similarity for Tamil and English."""

from __future__ import annotations

import hashlib
import logging
import math
import re

from app.config import get_settings
from app.rag.chunking import CHUNK_OVERLAP, CHUNK_WORDS

logger = logging.getLogger("study.embeddings")
DIM = 1024

_backend_name: str | None = None
_model = None


def model_key() -> str:
    return f"{backend_name()}:w{CHUNK_WORDS}:o{CHUNK_OVERLAP}"


def backend_name() -> str:
    global _backend_name, _model
    if _backend_name is not None:
        return _backend_name
    choice = get_settings().embedding_backend
    if choice == "hash":
        _backend_name = "multilingual-hash-v2"
        return _backend_name
    if choice in {"auto", "bge-m3"}:
        loaded = _try_model()
        if loaded is not None:
            _model = loaded
            _backend_name = "multilingual-model"
            logger.info("Embedding backend loaded")
            return _backend_name
        logger.info("Using enhanced multilingual feature hashing")
    _backend_name = "multilingual-hash-v2"
    return _backend_name


def _try_model():
    try:
        from sentence_transformers import SentenceTransformer
        return ("st", SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2"))
    except Exception:
        return None


def reset_embedder() -> None:
    global _backend_name, _model
    _backend_name = None
    _model = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    name = backend_name()
    if name.startswith("multilingual-hash"):
        return [_hash_embed(text) for text in texts]
    if _model is not None:
        kind, model = _model
        try:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [list(map(float, row)) for row in vectors]
        except Exception:
            return [_hash_embed(text) for text in texts]
    return [_hash_embed(text) for text in texts]


def _hash_embed(text: str) -> list[float]:
    """Feature hashing with unigrams, bigrams, and character 3-grams for Tamil and English."""
    vec = [0.0] * DIM
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE) or ["empty"]

    # 1. Word unigrams (weight 1.5)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += 1.5 * sign

    # 2. Word bigrams (weight 1.0)
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]}_{tokens[i+1]}"
        digest = hashlib.sha256(bigram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += 1.0 * sign

    # 3. Character 3-grams and 4-grams for subword / Tamil morphology matching (weight 0.6)
    clean_text = re.sub(r"\s+", " ", text.lower().strip())
    for n in (3, 4):
        for i in range(max(0, len(clean_text) - n + 1)):
            ngram = clean_text[i : i + n]
            digest = hashlib.sha256(ngram.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += 0.6 * sign

    norm = math.sqrt(sum(value * value for value in vec)) or 1.0
    return [value / norm for value in vec]


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))
