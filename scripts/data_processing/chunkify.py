import re
from pathlib import Path

# ====== ПУТИ ======
RAW_ROOT = Path("data/raw")
OUT_ROOT = Path("data/processed/cardiology")

CATEGORIES = ["Articles", "Cases", "Guidelines", "Handbooks", "Textbooks"]
EXTENSIONS = {".txt"}

# ====== ЧАНКИНГ ======
CHUNK_WORDS = 200
OVERLAP_WORDS = 30

def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\/\\:\*\?\"<>\|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:120] if len(name) > 120 else name

def normalize_text_keep_paragraphs(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # чистим хвостовые пробелы в строках, абзацы сохраняем
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()

def split_words(text: str):
    return re.findall(r"\S+", text)

def make_chunks(words, chunk_words: int, overlap_words: int):
    if chunk_words <= 0:
        raise ValueError("CHUNK_WORDS must be > 0")
    if overlap_words < 0:
        raise ValueError("OVERLAP_WORDS must be >= 0")
    if overlap_words >= chunk_words:
        raise ValueError("OVERLAP_WORDS must be < CHUNK_WORDS")

    chunks = []
    start = 0
    n = len(words)
    step = chunk_words - overlap_words

    while start < n:
        end = min(start + chunk_words, n)
        chunks.append(words[start:end])
        if end == n:
            break
        start += step

    return chunks

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def process_one_file(cat: str, src_path: Path):
    raw = normalize_text_keep_paragraphs(read_text(src_path))
    if not raw:
        return

    lines = raw.split("\n")
    title = (lines[0] or "").strip()
    if not title:
        title = src_path.stem

    body = "\n".join(lines[1:]).strip()
    words = split_words(body) if body else []

    if len(words) <= CHUNK_WORDS:
        chunks = [words]
    else:
        chunks = make_chunks(words, CHUNK_WORDS, OVERLAP_WORDS)

    out_dir = OUT_ROOT / cat / sanitize_name(src_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, chunk_words in enumerate(chunks, start=1):
        chunk_text = " ".join(chunk_words).strip()
        out_path = out_dir / f"{i:04d}.txt"
        out_path.write_text(f"{title}\n\n{chunk_text}\n", encoding="utf-8")

def main():
    for cat in CATEGORIES:
        in_dir = RAW_ROOT / cat
        if not in_dir.exists():
            print(f"[skip] no input folder: {in_dir}")
            continue

        # Только файлы верхнего уровня в каждой категории
        txt_files = [p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
        if not txt_files:
            print(f"[skip] no .txt files in {in_dir}")
            continue

        for p in sorted(txt_files):
            try:
                process_one_file(cat, p)
                print(f"[ok] {cat}: {p.name}")
            except Exception as e:
                print(f"[err] {cat}: {p.name}: {e}")

if __name__ == "__main__":
    main()
