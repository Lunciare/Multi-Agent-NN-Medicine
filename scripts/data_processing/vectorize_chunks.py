import os
from pathlib import Path
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# ====== ПУТИ ======
BASE_INPUT = Path("data/processed/cardiology")
BASE_OUTPUT = Path("data/vectorized")

# ====== СПИСОК МОДЕЛЕЙ ======
EMBEDDING_MODELS = [
    "all-MiniLM-L6-v2",
    "BAAI/bge-large-en-v1.5",
    "intfloat/e5-large-v2",
    "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb",
    "cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
]

# ====== ФУНКЦИИ ======
def read_txt_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")

def vectorize_texts(texts, model):
    vectors = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True
    )
    return vectors.astype(np.float32)


def process_document(doc_path: Path, output_base: Path, model):
    txt_files = sorted([f for f in doc_path.iterdir() if f.suffix == ".txt"])

    if not txt_files:
        print(f"[skip] No txt files in {doc_path}")
        return

    texts = [read_txt_file(f) for f in txt_files]
    vectors = vectorize_texts(texts, model)

    output_base.mkdir(parents=True, exist_ok=True)

    for txt_file, vec in zip(txt_files, vectors):
        vec_file = output_base / txt_file.name.replace(".txt", ".npy")
        np.save(vec_file, vec)

    print(f"[ok] Processed {doc_path}")


def main():
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"using {device}")
    assert device == "cuda"

    for model_name in EMBEDDING_MODELS:

        print(f"\n=== Processing with model: {model_name} ===")

        # Загружаем модель
        model = SentenceTransformer(model_name, device=device)

        # создаём корневую папку вида vectorized_{model_name}
        safe_model_name = model_name.replace("/", "-")
        model_output_root = BASE_OUTPUT / f"vectorized_{safe_model_name}"

        for x_dir in BASE_INPUT.iterdir():
            if not x_dir.is_dir():
                continue

            for y_dir in x_dir.iterdir():
                if not y_dir.is_dir():
                    continue

                rel_path = y_dir.relative_to(BASE_INPUT)
                out_dir = model_output_root / rel_path

                process_document(y_dir, out_dir, model)

if __name__ == "__main__":
    main()
