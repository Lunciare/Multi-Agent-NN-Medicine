"""
Скрипт для конвертации PDF, HTML, DOCX в текстовые файлы
для проекта RAG-uni-medicine
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Импорты для обработки разных форматов (исправлены опечатки)
try:
    import pdfplumber  # БЫЛО: pdflumber, pdcflumber - опечатки!
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("ВНИМАНИЕ: pdfplumber не установлен. PDF файлы не будут обработаны.")

try:
    from bs4 import BeautifulSoup
    HTML_SUPPORT = True
except ImportError:
    HTML_SUPPORT = False
    print("ВНИМАНИЕ: beautifulsoup4 не установлен. HTML файлы не будут обработаны.")

try:
    import fitz  # PyMuPDF для альтернативной обработки PDF
    FITZ_SUPPORT = True
except ImportError:
    FITZ_SUPPORT = False
    print("ВНИМАНИЕ: PyMuPDF не установлен. Альтернативная обработка PDF недоступна.")

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("ВНИМАНИЕ: python-docx не установлен. DOCX файлы не будут обработаны.")


class DocumentConverter:
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'processed': 0, 
            'failed': 0,
            'by_format': {},
            'by_folder': {}
        }
    
    def extract_text_from_pdf(self, file_path):
        """Извлечение текста из PDF с использованием pdfplumber"""
        text_parts = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        # Добавляем номер страницы
                        text_parts.append(f"\n--- Страница {i} ---\n")
                        text_parts.append(page_text)
            
            return ''.join(text_parts)
        except Exception as e:
            # Пробуем альтернативный метод если pdfplumber не сработал
            if FITZ_SUPPORT:
                return self.extract_text_from_pdf_fitz(file_path)
            else:
                return f"[ОШИБКА при чтении PDF: {str(e)}]"
    
    def extract_text_from_pdf_fitz(self, file_path):
        """Альтернативный метод извлечения текста из PDF (PyMuPDF)"""
        text_parts = []
        try:
            doc = fitz.open(file_path)
            for i, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text:
                    text_parts.append(f"\n--- Страница {i} ---\n")
                    text_parts.append(page_text)
            doc.close()
            return ''.join(text_parts)
        except Exception as e:
            return f"[ОШИБКА при чтении PDF (fitz): {str(e)}]"
    
    def extract_text_from_html(self, file_path):
        """Извлечение текста из HTML"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Получаем текст
            text = soup.get_text()
            
            # Очищаем лишние переносы строк
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            return f"[ОШИБКА при чтении HTML: {str(e)}]"
    
    def extract_text_from_docx(self, file_path):
        """Извлечение текста из DOCX"""
        try:
            doc = Document(file_path)
            text_parts = []
            
            for i, paragraph in enumerate(doc.paragraphs, 1):
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            return '\n'.join(text_parts)
        except Exception as e:
            return f"[ОШИБКА при чтении DOCX: {str(e)}]"
    
    def extract_text_from_txt(self, file_path):
        """Чтение обычных текстовых файлов"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Пробуем другие кодировки
            try:
                with open(file_path, 'r', encoding='cp1251') as f:
                    return f.read()
            except:
                return f"[ОШИБКА: не удалось декодировать файл]"
        except Exception as e:
            return f"[ОШИБКА при чтении TXT: {str(e)}]"
    
    def create_metadata(self, file_path, doc_type, original_format):
        """Создание метаданных для документа"""
        file_stat = os.stat(file_path)
        
        metadata = {
            'original_filename': Path(file_path).name,
            'converted_date': datetime.now().isoformat(),
            'file_size_bytes': file_stat.st_size,
            'original_format': original_format,
            'document_type': doc_type,
            'source_folder': Path(file_path).parent.name,
            'full_path': str(file_path)
        }
        
        return metadata
    
    def save_document(self, text, metadata, output_path):
        """Сохранение документа с метаданными"""
        # Создаем папку если ее нет
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Формируем содержимое файла
        content = f"""=== МЕТАДАННЫЕ ===
{json.dumps(metadata, ensure_ascii=False, indent=2)}

=== СОДЕРЖАНИЕ ===
{text}
"""
        
        # Сохраняем файл
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def convert_file(self, input_path, output_path):
        """Основная функция конвертации одного файла"""
        file_ext = input_path.suffix.lower()
        doc_type = input_path.parent.name  # Название папки (Articles, Textbooks и т.д.)
        
        # Обновляем статистику
        self.stats['total_files'] += 1
        self.stats['by_format'][file_ext] = self.stats['by_format'].get(file_ext, 0) + 1
        self.stats['by_folder'][doc_type] = self.stats['by_folder'].get(doc_type, 0) + 1
        
        try:
            # Определяем метод извлечения текста по расширению файла
            if file_ext == '.pdf':
                if PDF_SUPPORT:
                    text = self.extract_text_from_pdf(input_path)
                    format_name = 'pdf'
                else:
                    print(f"  Пропуск: PDF поддержка отключена для файла {input_path.name}")
                    self.stats['failed'] += 1
                    return False
            elif file_ext in ['.html', '.htm']:
                if HTML_SUPPORT:
                    text = self.extract_text_from_html(input_path)
                    format_name = 'html'
                else:
                    print(f"  Пропуск: HTML поддержка отключена для файла {input_path.name}")
                    self.stats['failed'] += 1
                    return False
            elif file_ext == '.docx':
                if DOCX_SUPPORT:
                    text = self.extract_text_from_docx(input_path)
                    format_name = 'docx'
                else:
                    print(f"  Пропуск: DOCX поддержка отключена для файла {input_path.name}")
                    self.stats['failed'] += 1
                    return False
            elif file_ext == '.txt':
                text = self.extract_text_from_txt(input_path)
                format_name = 'txt'
            else:
                print(f"  Пропуск: неподдерживаемый формат {file_ext} для файла {input_path.name}")
                self.stats['failed'] += 1
                return False
            
            # Создаем метаданные
            metadata = self.create_metadata(input_path, doc_type, format_name)
            
            # Сохраняем документ
            self.save_document(text, metadata, output_path)
            
            print(f"  ✓ Успешно: {input_path.name} → {output_path.name}")
            self.stats['processed'] += 1
            return True
            
        except Exception as e:
            print(f"  ✗ ОШИБКА при обработке {input_path.name}: {str(e)}")
            self.stats['failed'] += 1
            return False
    
    def process_folder(self, input_folder, output_folder):
        """Обработка всех файлов в папке"""
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        
        # Находим все файлы
        all_files = []
        for ext in ['*.pdf', '*.html', '*.htm', '*.docx', '*.txt']:
            all_files.extend(input_path.rglob(ext))
        
        print(f"Найдено файлов для обработки: {len(all_files)}")
        print("-" * 50)
        
        # Обрабатываем файлы
        for file_path in all_files:
            # Определяем путь для сохранения
            relative_path = file_path.relative_to(input_path)
            output_file_path = output_path / relative_path.with_suffix('.txt')
            
            # Конвертируем файл
            self.convert_file(file_path, output_file_path)
    
    def print_statistics(self):
        """Вывод статистики обработки"""
        print("\n" + "="*50)
        print("СТАТИСТИКА ОБРАБОТКИ")
        print("="*50)
        print(f"Всего файлов: {self.stats['total_files']}")
        print(f"Успешно обработано: {self.stats['processed']}")
        print(f"Не удалось обработать: {self.stats['failed']}")
        
        if self.stats['by_format']:
            print("\nПо форматам:")
            for fmt, count in self.stats['by_format'].items():
                print(f"  {fmt}: {count}")
        
        if self.stats['by_folder']:
            print("\nПо категориям:")
            for folder, count in self.stats['by_folder'].items():
                print(f"  {folder}: {count}")
        
        # Сохраняем статистику в файл
        stats_path = Path("01_PROCESSED") / "conversion_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"\nСтатистика сохранена в: {stats_path}")


def main():
    """Основная функция"""
    print("="*50)
    print("КОНВЕРТАЦИЯ ДОКУМЕНТОВ ДЛЯ RAG-UNI-MEDICINE")
    print("="*50)
    
    # Проверяем существование папок
    raw_folder = Path("00_RAW_CARDIOLOGY")
    processed_folder = Path("01_PROCESSED")
    
    if not raw_folder.exists():
        print(f"ОШИБКА: Папка {raw_folder} не найдена!")
        return
    
    if not processed_folder.exists():
        print(f"ОШИБКА: Папка {processed_folder} не найдена!")
        return
    
    # Создаем конвертер и запускаем обработку
    converter = DocumentConverter()
    
    print(f"Исходная папка: {raw_folder}")
    print(f"Целевая папка: {processed_folder}")  # БЫЛО: fЦелевая - опечатка!
    print("-"*50)
    
    # Запрашиваем подтверждение
    response = input("Начать конвертацию? (y/n): ").lower()
    if response != 'y':
        print("Конвертация отменена.")
        return
    
    # Запускаем обработку
    converter.process_folder(raw_folder, processed_folder)
    
    # Выводим статистику
    converter.print_statistics()
    
    print("\n" + "="*50)
    print("КОНВЕРТАЦИЯ ЗАВЕРШЕНА!")
    print("="*50)


if __name__ == "__main__":
    main()