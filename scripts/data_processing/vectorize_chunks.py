import os
from pathlib import Path
import pickle
from tqdm import tqdm

# Для embedding через sentence-transformers (можно заменить на OpenAI или другую модель)
from sentence_transformers import SentenceTransformer

# ====== ПУТИ ======
BASE_INPUT = Path("data/processed/cardiology")
BASE_OUTPUT = Path("data/vectorized")

# ====== НАСТРОЙКИ МОДЕЛИ ======
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  

# ====== ФУНКЦИИ ======
def read_txt_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")

def vectorize_texts(texts, model):
    """Возвращает список векторов для списка текстов"""
    return model.encode(texts, show_progress_bar=False)

def process_document(doc_path: Path, output_path: Path, model):
    txt_files = sorted([f for f in doc_path.iterdir() if f.suffix == '.txt'])
    if not txt_files:
        print(f"[skip] No txt files in {doc_path}")
        return

    texts = [read_txt_file(f) for f in txt_files]
    vectors = vectorize_texts(texts, model)

    output_path.mkdir(parents=True, exist_ok=True)

    for txt_file, vec in zip(txt_files, vectors):
        vec_file = output_path / txt_file.name.replace('.txt', '.pkl')
        with open(vec_file, 'wb') as f:
            pickle.dump(vec, f)

    print(f"[ok] Processed {doc_path} -> {output_path}")

def main():
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    for x_dir in BASE_INPUT.iterdir():
        if not x_dir.is_dir():
            continue
        for y_dir in x_dir.iterdir():
            if not y_dir.is_dir():
                continue
            rel_path = y_dir.relative_to(BASE_INPUT)
            out_dir = BASE_OUTPUT / rel_path
            process_document(y_dir, out_dir, model)

if __name__ == "__main__":
    main()
