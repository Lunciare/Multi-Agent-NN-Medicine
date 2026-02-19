from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer

BASE = Path("data/processed/cardiology")
CATS = ["Articles", "Cases", "Guidelines", "Handbooks", "Textbooks"]

# Settings
TOP_K_KEYWORDS = 15
SUMMARY_SENTENCES_TARGET = 6
SUMMARY_CHAR_LIMIT = 1200
MAX_TEXT_FOR_KEYWORDS_CHARS = 200_000

# IMPORTANT: these must NEVER include the literal word "keywords"
DEFAULT_KEYWORDS = [
    "cardiology",
    "cardiovascular",
    "ecg",
    "myocardial infarction",
    "acute coronary syndrome",
    "ischemia",
    "arrhythmia",
    "heart failure",
    "troponin",
    "reperfusion",
    "st elevation",
    "st depression",
    "posterior mi",
    "stemi",
    "nstemi",
]


# -------------------------
# Utils
# -------------------------

def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _list_chunk_files(doc_dir: Path) -> List[Path]:
    # only chunk .txt, excluding summary.txt
    chunks = [p for p in doc_dir.glob("*.txt") if p.name.lower() != "summary.txt"]

    def key_fn(x: Path) -> int:
        m = re.match(r"^(\d+)\.txt$", x.name)
        return int(m.group(1)) if m else 10**12

    return sorted(chunks, key=key_fn)


def _extract_title_from_chunk(chunk_path: Path) -> str:
    lines = _read_text(chunk_path).splitlines()
    if not lines:
        return "Untitled"
    return lines[0].strip() or "Untitled"


def _remove_leading_keyword_lines(body_lines: List[str], scan_lines: int = 30) -> List[str]:
    """
    Remove any leading KEYWORDS lines (and adjacent empty lines) from body_lines.
    This fixes the duplication you got: "KEYWORDS: ..." already existed in content,
    and your script inserted another one.
    """
    i = 0
    removed_any = False

    # allow a few empty lines before KEYWORDS
    while i < len(body_lines) and i < scan_lines and body_lines[i].strip() == "":
        i += 1

    # remove one or more KEYWORDS lines near the top
    while i < len(body_lines) and i < scan_lines and body_lines[i].strip().lower().startswith("keywords:"):
        removed_any = True
        i += 1
        # also drop empty lines right after keywords
        while i < len(body_lines) and i < scan_lines and body_lines[i].strip() == "":
            i += 1

    if removed_any:
        return body_lines[i:]
    return body_lines


def _strip_existing_keywords_header(lines: List[str]) -> List[str]:
    """
    Enforce chunk format:
    line1: title
    line2: KEYWORDS: ...
    line3: empty
    then body WITHOUT any extra KEYWORDS near the top.
    """
    if not lines:
        return lines

    title = lines[0]
    body = lines[1:]
    body = _remove_leading_keyword_lines(body, scan_lines=40)
    return [title] + body


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if len(p.strip()) >= 20]
    return parts


def _fallback_summary(text: str, max_sentences: int = 3, max_words: int = 90) -> str:
    sents = _split_sentences(text)
    if sents:
        out = []
        words = 0
        for s in sents:
            w = s.split()
            if not w:
                continue
            if words + len(w) > max_words and out:
                break
            out.append(s)
            words += len(w)
            if len(out) >= max_sentences:
                break
        if out:
            return " ".join(out)

    words = re.findall(r"\S+", (text or "").strip())
    return " ".join(words[: min(len(words), max_words)])


def _simple_keywords_fallback(text: str, top_k: int) -> List[str]:
    """
    Very simple fallback: frequent tokens (>=4 chars), with stoplist.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", (text or "").lower())
    stop = {
        "with","from","that","this","were","have","been","into","than","then","they","them","their",
        "also","such","most","more","less","only","over","under","between","during","after","before",
        "patient","patients","study","studies","result","results","using","used","use","may","might",
        "show","shows","shown","include","including","data","model","models","analysis","based",
        "clinical","medicine","medical",
        "keywords",  # crucial: never allow literal "keywords"
        "summary",
    }
    tokens = [t for t in tokens if t not in stop]
    if not tokens:
        return []
    return [w for w, _ in Counter(tokens).most_common(top_k)]


def _sanitize_keywords(kws: List[str], top_k: int) -> List[str]:
    """
    Guarantee: non-empty, no literal 'keywords', unique, trimmed.
    """
    out: List[str] = []
    seen = set()

    for k in (kws or []):
        k = (k or "").strip()
        if not k:
            continue
        if k.lower() == "keywords":
            continue
        if k.lower().startswith("keywords:"):
            continue
        if k not in seen:
            out.append(k)
            seen.add(k)
        if len(out) >= top_k:
            break

    if not out:
        out = DEFAULT_KEYWORDS[:top_k]
    return out


def _make_keywords(full_text: str, top_k: int) -> List[str]:
    cleaned = (full_text or "").strip()
    if not cleaned:
        return DEFAULT_KEYWORDS[:top_k]

    # limit for speed / memory
    if len(cleaned) > MAX_TEXT_FOR_KEYWORDS_CHARS:
        cleaned = cleaned[:MAX_TEXT_FOR_KEYWORDS_CHARS]

    # short texts: TF-IDF on 1 doc can be noisy → fallback
    if len(cleaned.split()) < 80:
        return _sanitize_keywords(_simple_keywords_fallback(cleaned, top_k), top_k)

    try:
        # SINGLE DOCUMENT TF-IDF: min_df=1, max_df=1.0
        vec = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=1.0,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b",
        )
        X = vec.fit_transform([cleaned])
        feats = vec.get_feature_names_out()
        scores = X.toarray()[0]

        idx = scores.argsort()[::-1]
        kws: List[str] = []
        for i in idx:
            if scores[i] <= 0:
                break
            kw = feats[i].strip()
            if not kw:
                continue
            if kw.lower() == "keywords":
                continue
            kws.append(kw)
            if len(kws) >= top_k:
                break

        if not kws:
            kws = _simple_keywords_fallback(cleaned, top_k)

        return _sanitize_keywords(kws, top_k)

    except Exception:
        return _sanitize_keywords(_simple_keywords_fallback(cleaned, top_k), top_k)


def _make_summary(title: str, full_text: str) -> str:
    text = (full_text or "").strip()
    title = (title or "").strip() or "Untitled"

    if not text:
        return f"{title}. Brief note: source text is empty."

    summary = _fallback_summary(text, max_sentences=SUMMARY_SENTENCES_TARGET, max_words=180)
    summary = (summary or "").strip()

    if not summary or len(summary.split()) < 12:
        summary = _fallback_summary(text, max_sentences=SUMMARY_SENTENCES_TARGET, max_words=180).strip()

    if not summary:
        summary = _fallback_summary(text).strip()

    if len(summary) > SUMMARY_CHAR_LIMIT:
        summary = summary[:SUMMARY_CHAR_LIMIT].rstrip() + "…"

    return summary


def _collect_doc_text_and_title(doc_dir: Path) -> Tuple[str, str]:
    chunks = _list_chunk_files(doc_dir)
    if not chunks:
        return ("", "Untitled")

    title = _extract_title_from_chunk(chunks[0])

    texts: List[str] = []
    for ch in chunks:
        lines = _read_text(ch).splitlines()
        if not lines:
            continue

        # IMPORTANT: drop title line AND drop any leading KEYWORDS line(s)
        body_lines = lines[1:]
        body_lines = _remove_leading_keyword_lines(body_lines, scan_lines=60)

        body = "\n".join(body_lines).strip()
        if body:
            texts.append(body)

    full_text = "\n\n".join(texts).strip()
    return full_text, title


def _write_summary_file(doc_dir: Path, title: str, summary: str, keywords: List[str]) -> None:
    # Ensure exactly ONE keywords line in summary.txt (we overwrite the file)
    kws = _sanitize_keywords(keywords, TOP_K_KEYWORDS)
    kw_line = "KEYWORDS: " + ", ".join(kws)
    content = f"{title}\n{kw_line}\n\n{summary}\n"
    (doc_dir / "summary.txt").write_text(content, encoding="utf-8")


def _rewrite_chunk_with_keywords(chunk_path: Path, keywords: List[str]) -> None:
    lines = _read_text(chunk_path).splitlines()
    if not lines:
        return

    # Remove any existing KEYWORDS line(s) near top, then re-add exactly one.
    cleaned = _strip_existing_keywords_header(lines)
    title = (cleaned[0] or "").strip() or "Untitled"
    body_lines = cleaned[1:]
    body_lines = _remove_leading_keyword_lines(body_lines, scan_lines=60)

    kws = _sanitize_keywords(keywords, TOP_K_KEYWORDS)
    kw_line = "KEYWORDS: " + ", ".join(kws)

    # Keep exactly one empty line after keywords
    new_lines = [title, kw_line, ""] + body_lines
    new_text = "\n".join(new_lines).rstrip() + "\n"
    chunk_path.write_text(new_text, encoding="utf-8")


# -------------------------
# Main
# -------------------------

def main() -> None:
    docs_total = 0
    summaries_written = 0
    chunks_rewritten = 0
    docs_no_chunks = 0

    for cat in CATS:
        cat_dir = BASE / cat
        if not cat_dir.exists():
            continue

        for doc_dir in [p for p in cat_dir.iterdir() if p.is_dir()]:
            docs_total += 1
            chunks = _list_chunk_files(doc_dir)
            if not chunks:
                docs_no_chunks += 1
                continue

            full_text, title = _collect_doc_text_and_title(doc_dir)

            keywords = _make_keywords(full_text, TOP_K_KEYWORDS)
            keywords = _sanitize_keywords(keywords, TOP_K_KEYWORDS)

            summary = _make_summary(title, full_text)

            _write_summary_file(doc_dir, title, summary, keywords)
            summaries_written += 1

            for ch in chunks:
                _rewrite_chunk_with_keywords(ch, keywords)
                chunks_rewritten += 1

    print("Done.")
    print(f"docs_total: {docs_total}")
    print(f"docs_no_chunks: {docs_no_chunks}")
    print(f"summaries_written: {summaries_written}")
    print(f"chunks_rewritten: {chunks_rewritten}")


if __name__ == "__main__":
    main()
