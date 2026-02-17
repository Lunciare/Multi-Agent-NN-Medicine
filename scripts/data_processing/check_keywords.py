from pathlib import Path

BASE = Path("data/processed/cardiology")
cats = ["Articles", "Cases", "Guidelines", "Handbooks", "Textbooks"]

no_summary = []
no_kw = []

def chunk_has_kw(p: Path) -> bool:
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return False
    return len(lines) >= 2 and lines[1].strip().lower().startswith("keywords:")

for cat in cats:
    cat_dir = BASE / cat
    if not cat_dir.exists():
        continue
    for doc in [p for p in cat_dir.iterdir() if p.is_dir()]:
        if not (doc / "summary.txt").exists():
            no_summary.append(doc)

        chunks = sorted([p for p in doc.glob("*.txt") if p.name != "summary.txt"])
        if chunks:
            # если хотя бы 1 чанк без keywords — считаем документ проблемным
            if any(not chunk_has_kw(ch) for ch in chunks[:10]):  # достаточно первых 10
                no_kw.append(doc)

print("No summary:", len(no_summary))
for p in no_summary[:20]:
    print("  ", p)

print("\nDocs with missing keywords in first chunks:", len(no_kw))
for p in no_kw[:20]:
    print("  ", p)
