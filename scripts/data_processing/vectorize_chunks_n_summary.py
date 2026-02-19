import os
import json
from pathlib import Path
from typing import List, Dict

from sentence_transformers import SentenceTransformer
import numpy as np


# =============================
# CONFIG
# =============================

# Модель эмбеддингов
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Путь к данным (относительно корня проекта)
PROCESSED_ROOT = Path("./data/processed/cardiology")
VECTORIZED_ROOT = Path("./data/vectorized")


# =============================
# LOAD MODEL
# =============================

def load_model():
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


# =============================
# UTILS
# =============================

def read_text_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_json(data: Dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def embed_texts(model, texts: List[str]) -> np.ndarray:
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


# =============================
# VECTORIZE ONE DOCUMENT
# =============================

def vectorize_document(model, y_folder: Path):

    summary_path = y_folder / "summary.txt"

    chunk_files = sorted(
        [f for f in y_folder.glob("*.txt") if f.name != "summary.txt"]
    )

    if not summary_path.exists():
        print(f"Summary not found in {y_folder}")
        return

    summary_text = read_text_file(summary_path)
    summary_embedding = embed_texts(model, [summary_text])[0]

    if not chunk_files:
        print(f"No chunks found in {y_folder}")
        return

    chunk_texts = []
    chunk_ids = []

    for chunk_file in chunk_files:
        text = read_text_file(chunk_file)
        chunk_texts.append(text)
        chunk_ids.append(chunk_file.stem)

    chunk_embeddings = embed_texts(model, chunk_texts)

    # путь сохранения
    x_name = y_folder.parent.name
    y_name = y_folder.name

    output_base = VECTORIZED_ROOT / x_name / y_name / "E"
    output_base.mkdir(parents=True, exist_ok=True)

    # summary
    np.save(output_base / "summary_embedding.npy", summary_embedding)

    # chunks
    np.save(output_base / "chunk_embeddings.npy", chunk_embeddings)
    np.save(output_base / "chunk_ids.npy", np.array(chunk_ids))

    print(f"Vectorized: {x_name}/{y_name}")



# =============================
# MAIN LOOP
# =============================

def main():
    model = load_model()

    for x_folder in PROCESSED_ROOT.iterdir():
        if not x_folder.is_dir():
            continue

        for y_folder in x_folder.iterdir():
            if not y_folder.is_dir():
                continue

            vectorize_document(model, y_folder)



if __name__ == "__main__":
    main()
