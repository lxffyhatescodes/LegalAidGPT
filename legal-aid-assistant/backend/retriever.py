"""Retrieval: question -> top-k legal passages.

Two interchangeable backends behind ONE function, `retrieve(question)`:
  * dense   : sentence-transformers + FAISS (needs `python -m backend.build_index` once)
  * keyword : TF-IDF cosine, pure Python, works with zero extra installs (fallback)

Each hit has the shape assistant/llm.py already expects:
  {"text", "metadata": {"source", "section", "chunk_id", "doc_id"}, "score", "distance"}
"""
import json
import math
import re
from collections import Counter, defaultdict

from . import settings as config

_STOP = set("""a an and are as at be by for from has have he her his i in is it its me my of on or
our she that the their them they this to was we were what when where which who will with you your
can do does did how if so than then there these those am been being not no but about into out up
any all some may shall also i'm""".split())
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    toks = [t for t in _WORD.findall(text.lower()) if t not in _STOP and len(t) > 1]
    return [_stem(t) for t in toks]


def _stem(t: str) -> str:   # tiny suffix stripper: arrested/arrests/arresting -> arrest
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def load_chunks() -> list[dict]:
    if not config.CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"{config.CHUNKS_FILE.name} not found. Run: python -m backend.chunker")
    with open(config.CHUNKS_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _hit(chunk: dict, score: float) -> dict:
    return {
        "text": chunk["text"],
        "metadata": {
            "source": chunk["doc_title"],
            "section": chunk["section"],
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
        },
        "score": round(float(score), 4),
        "distance": round(1.0 - float(score), 4),
    }


class KeywordRetriever:
    name = "keyword"
    min_score = config.FALLBACK_MIN_SCORE

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        df = Counter()
        tfs = []
        for c in chunks:
            # the title + section number help short queries ("section 35 constitution")
            tf = Counter(_tokens(c["doc_title"] + " " + c["text"]))
            tfs.append(tf)
            df.update(tf.keys())
        n = len(chunks)
        self.idf = {t: math.log((n + 1) / (d + 0.5)) + 1 for t, d in df.items()}
        self.inv = defaultdict(list)
        self.norms = []
        for i, tf in enumerate(tfs):
            norm = 0.0
            for t, f in tf.items():
                w = (1 + math.log(f)) * self.idf[t]
                self.inv[t].append((i, w))
                norm += w * w
            self.norms.append(math.sqrt(norm) or 1.0)

    def search(self, question: str, k: int) -> list[dict]:
        q = Counter(_tokens(question))
        if not q:
            return []
        qw = {t: (1 + math.log(f)) * self.idf[t] for t, f in q.items() if t in self.idf}
        qnorm = math.sqrt(sum(w * w for w in qw.values())) or 1.0
        if len(q) >= 2 and len(qw) < 2:     # off-topic: only one query word exists in the law texts
            return []
        scores = defaultdict(float)
        for t, wq in qw.items():
            for i, wd in self.inv[t]:
                scores[i] += wq * wd
        ranked = sorted(((s / (qnorm * self.norms[i]), i) for i, s in scores.items()), reverse=True)
        return [_hit(self.chunks[i], s) for s, i in ranked[:k]]


class DenseRetriever:
    name = "dense"
    min_score = config.MIN_SIMILARITY

    def __init__(self, chunks: list[dict]):
        import faiss  # noqa: F401  (imported lazily so the keyword fallback needs neither package)
        from sentence_transformers import SentenceTransformer
        self._faiss = faiss
        self.index = faiss.read_index(str(config.INDEX_FILE))
        ids = json.loads(config.INDEX_IDS_FILE.read_text(encoding="utf-8"))
        by_id = {c["chunk_id"]: c for c in chunks}
        self.chunks = [by_id[i] for i in ids]
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)

    def search(self, question: str, k: int) -> list[dict]:
        v = self.model.encode([question], normalize_embeddings=True).astype("float32")
        scores, idx = self.index.search(v, k)      # inner product == cosine (vectors are normalised)
        return [_hit(self.chunks[i], s) for s, i in zip(scores[0], idx[0]) if i >= 0]


_retriever = None


def get_retriever():
    """Build once, reuse for every question (important for Streamlit reruns)."""
    global _retriever
    if _retriever is not None:
        return _retriever
    chunks = load_chunks()
    mode = config.RETRIEVAL_BACKEND
    if mode in ("auto", "dense") and config.INDEX_FILE.exists() and config.INDEX_IDS_FILE.exists():
        try:
            _retriever = DenseRetriever(chunks)
            return _retriever
        except Exception:
            if mode == "dense":
                raise
    _retriever = KeywordRetriever(chunks)
    return _retriever


# Lay words -> the vocabulary the statutes actually use. Only the SEARCH text is expanded; the LLM
# still sees the user's original question. Extend this table when a test scenario retrieves badly.
EXPANSIONS = [
    (r"\b(arrest\w*|detain\w*|police|custody|locked up|hold me|held|kept me)\b",
     "arrested or detained person right to personal liberty brought before a court within a "
     "reasonable time informed of the grounds of arrest release on bail"),
    (r"\b(landlord|tenant\w*|evict\w*|rent|quit notice)\b",
     "tenancy notice to quit recovery of premises possession of premises rent tenant rights"),
    (r"\b(salary|salaries|wages?|unpaid|not paid|owed|pay(ment)?)\b",
     "payment of wages payment in legal tender deductions from wages worker entitled to wages"),
    (r"\b(employer|sacked|fired|dismiss\w*|terminat\w*|boss|worker|employee|job)\b",
     "employment contract of employment termination of employment notice worker rights"),
    (r"\b(loan|lender|loan app|borrow\w*|debt|harass\w*)\b",
     "consumer lending digital lending borrower protection debt recovery harassment"),
    (r"\b(marriage|married|divorce|husband|wife|spouse)\b",
     "marriage dissolution of marriage divorce matrimonial causes spouse"),
    (r"\b(land|plot|certificate of occupancy|c of o|title)\b",
     "land use act right of occupancy certificate of occupancy land title"),
    (r"\b(child|children|minor|baby)\b", "child rights act rights of the child welfare"),
    (r"\b(legal aid|free lawyer|cannot afford)\b", "legal aid council free legal assistance"),
]
_EXP = [(re.compile(p, re.I), extra) for p, extra in EXPANSIONS]


def expand_query(question: str) -> str:
    extras = [extra for pat, extra in _EXP if pat.search(question)]
    return question if not extras else question + ". " + " ".join(extras)


CANDIDATES = 25        # fetch many, then trim
MAX_PER_SECTION = 2    # at most 2 chunks of one section, so one long section cannot fill every slot


EXPAND_TOP = 3          # the best N hits also get the NEXT chunk of their section (e.g. s.35(4) + s.35(5))
MAX_MERGED_CHARS = 2000
_next_chunk = None


def _next_map() -> dict:
    """chunk_id -> the following chunk of the same document section (built once)."""
    global _next_chunk
    if _next_chunk is None:
        chunks = load_chunks()
        _next_chunk = {}
        for a, b in zip(chunks, chunks[1:]):
            if a["doc_id"] == b["doc_id"] and a["section"] == b["section"]:
                _next_chunk[a["chunk_id"]] = b
    return _next_chunk


def _with_next(hit: dict, taken: set) -> dict:
    nxt = _next_map().get(hit["metadata"]["chunk_id"])
    if nxt and nxt["chunk_id"] not in taken and len(hit["text"]) + len(nxt["text"]) <= MAX_MERGED_CHARS:
        first, _, rest = nxt["text"].partition("\n")
        body = rest if "(continued)" in first else nxt["text"]   # drop the repeated heading line
        hit = {**hit, "text": hit["text"] + "\n" + body}
    return hit


def retrieve(question: str, k: int = config.TOP_K) -> list[dict]:
    """Top-k passages (max 2 per document section) above the relevance threshold ([] = 'not covered')."""
    r = get_retriever()
    per_section, out = {}, []
    for h in r.search(expand_query(question), max(CANDIDATES, k)):
        if h["score"] < r.min_score:
            continue
        key = (h["metadata"]["doc_id"], h["metadata"]["section"])
        if per_section.get(key, 0) >= MAX_PER_SECTION:
            continue
        per_section[key] = per_section.get(key, 0) + 1
        out.append(h)
        if len(out) == k:
            break
    taken = {h["metadata"]["chunk_id"] for h in out}
    return [_with_next(h, taken) if i < EXPAND_TOP else h for i, h in enumerate(out)]
