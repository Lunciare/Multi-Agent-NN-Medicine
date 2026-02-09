import re
from pathlib import Path


def clean_text_from_pdf_noise(text: str) -> str:
    patterns = [
        # --- Страница 1 ---
        r'^---\s*Страница\s+\d+\s*---\s*$',

        # футеры NICE и права
        r'©\s*NICE.*?$',
        r'.*conditions#notice-of-rights.*?$',
        r'.*Page\s+\d+.*?$',

        # даты и время
        r'\b\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}\b',

        # заголовки сайтов
        r'.*-\s+wikidoc.*',

        # Contents / оглавление (многострочно)
        r'^Contents\s*\n(?:.*\n){1,40}?(\n|$)',

        #Ссылки
        r'https?://\S+'
    ]

    for p in patterns:
        text = re.sub(p, '', text, flags=re.I | re.M)

    # мусорные символы
    text = text.replace('\ufeff', '').replace('\xa0', ' ')

    # нормализация пустых строк
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def process_files(data_path="data/processed/cardiology"):
    processed = 0
    skipped = 0

    for txt_file in Path(data_path).rglob("*.txt"):

        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                raw = f.read()

            if "=== СОДЕРЖАНИЕ ===" not in raw:
                skipped += 1
                continue

            metadata, content = raw.split("=== СОДЕРЖАНИЕ ===", 1)

            cleaned_content = clean_text_from_pdf_noise(content)

            new_text = (
                metadata.strip()
                + "\n\n=== СОДЕРЖАНИЕ ===\n\n"
                + cleaned_content
                + "\n"
            )

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(new_text)

            processed += 1

        except Exception as e:
            print(f"Ошибка в {txt_file.name}: {e}")
            skipped += 1

    print(f"Обработано файлов: {processed}")
    print(f"Пропущено файлов: {skipped}")


if __name__ == "__main__":
    process_files()

