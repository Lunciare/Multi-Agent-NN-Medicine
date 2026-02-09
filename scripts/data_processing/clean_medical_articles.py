import re
from pathlib import Path
import json

def clean_medical_article(content):
    """
    Безопасная очистка медицинской статьи.
    Оставляет максимум медицинского контента, удаляет только явный мусор.
    """
    
    original_length = len(content)
    print(f"  Начальная длина: {original_length} chars")
    
    # 1. Удаляем ОЧЕНЬ ОСТОРОЖНО - только явный мусор ПОСЛЕ References
    # Разделяем на части ДО и ПОСЛЕ References
    if 'References' in content:
        # Находим последнее вхождение References
        ref_matches = list(re.finditer(r'References\d*\.', content))
        if ref_matches:
            last_ref = ref_matches[-1]
            # Всё ДО последних References - оставляем
            main_content = content[:last_ref.end()]
            
            # Всё ПОСЛЕ References - очищаем от мусора
            after_refs = content[last_ref.end():]
            
            # Удаляем только ОЧЕНЬ явный мусор после References
            trash_patterns = [
                r'Show all references.*',
                r'eLetters.*?Sign In to Submit',
                r'Information & Authors.*?Metrics & Citations',
                r'Get Access.*?Get Access',
                r'Login options.*?Login',
                r'Purchase Options.*?Checkout',
                r'Restore your content access.*',
                r'Advertisement.*?Advertisement',
                r'Submit a Response.*?CancelSubmit',
                r'Browse.*?Annals of Internal Medicine',
                r'Now Reading.*?Next__',
                r'This page is managed.*?Confirm My Choices',
                r'Shopping cart.*?Cart',
                r'Sign in.*?REGISTER',
            ]
            
            for pattern in trash_patterns:
                after_refs = re.sub(pattern, '', after_refs, flags=re.DOTALL | re.IGNORECASE)
            
            # Собираем обратно
            content = main_content + after_refs
    
    # 2. Убираем технические пометки в ссылках, но оставляем сами ссылки
    # Вместо удаления "CrossrefPubMedGoogle Scholar", просто делаем их менее заметными
    content = re.sub(r'(Crossref|PubMed|Google Scholar)', '', content)
    
    # 3. Удаляем "doi: 10.xxx" но оставляем ссылку
    content = re.sub(r'doi: \d+\.\d+/\S+\s*', '', content)
    
    # 4. Удаляем HTML/XML теги если остались
    content = re.sub(r'<[^>]+>', '', content)
    
    # 5. Очищаем форматирование
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[ \t]{2,}', ' ', content)
    
    cleaned_length = len(content)
    print(f"  После очистки: {cleaned_length} chars")
    print(f"  Сохранено: {cleaned_length/original_length*100:.1f}%")
    
    return content.strip()

def extract_medical_content_safely(content):
    """
    Альтернативный метод: извлекаем медицинские части по шаблонам
    """
    medical_parts = []
    
    # Ищем Abstract
    abstract_match = re.search(r'Abstract(.*?)(?=Graphical Abstract|Introduction|Methods|References|$)', 
                               content, re.DOTALL | re.IGNORECASE)
    if abstract_match:
        medical_parts.append("ABSTRACT:\n" + abstract_match.group(1).strip())
    
    # Ищем Introduction
    intro_match = re.search(r'Introduction(.*?)(?=Methods|Results|Discussion|References|$)', 
                            content, re.DOTALL | re.IGNORECASE)
    if intro_match:
        medical_parts.append("\nINTRODUCTION:\n" + intro_match.group(1).strip())
    
    # Ищем Methods
    methods_match = re.search(r'Methods(.*?)(?=Results|Discussion|Conclusion|References|$)', 
                              content, re.DOTALL | re.IGNORECASE)
    if methods_match:
        medical_parts.append("\nMETHODS:\n" + methods_match.group(1).strip())
    
    # Ищем Results
    results_match = re.search(r'Results(.*?)(?=Discussion|Conclusion|References|$)', 
                              content, re.DOTALL | re.IGNORECASE)
    if results_match:
        medical_parts.append("\nRESULTS:\n" + results_match.group(1).strip())
    
    # Ищем Discussion/Conclusion
    discussion_match = re.search(r'(Discussion|Conclusion)(.*?)(?=References|$)', 
                                 content, re.DOTALL | re.IGNORECASE)
    if discussion_match:
        medical_parts.append(f"\n{discussion_match.group(1).upper()}:\n" + discussion_match.group(2).strip())
    
    # Ищем References
    refs_match = re.search(r'References\d*\.(.*)', content, re.DOTALL)
    if refs_match:
        medical_parts.append("\nREFERENCES:\n" + refs_match.group(1).strip())
    
    # Если нашли хоть что-то
    if medical_parts:
        return '\n\n'.join(medical_parts)
    
    # Если ничего не нашли - возвращаем оригинал (лучше мусор, чем ничего)
    return content

def process_article_file_safely(file_path):
    """Безопасная обработка файла с сохранением бэкапа"""
    with open(file_path, 'r', encoding='utf-8') as f:
        full_content = f.read()
    
    if '=== СОДЕРЖАНИЕ ===' not in full_content:
        return False
    
    # Создаём бэкап оригинального файла
    backup_path = file_path.with_suffix('.original.txt')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"  Создан бэкап: {backup_path.name}")
    
    # Разделяем метаданные и контент
    metadata_part, article_content = full_content.split('=== СОДЕРЖАНИЕ ===', 1)
    
    print(f"\n📄 Обработка: {file_path.name}")
    
    # Метод 1: Безопасная очистка
    cleaned_content = clean_medical_article(article_content)
    
    # Метод 2: Если очистка удалила слишком много (>80%), используем извлечение
    if len(cleaned_content) < len(article_content) * 0.2:  # Осталось меньше 20%
        print(f"  ⚠️  Слишком много удалено, пробуем извлечь контент...")
        cleaned_content = extract_medical_content_safely(article_content)
    
    # Если ВСЁ РАВНО мало контента (<10%), оставляем оригинал с предупреждением
    if len(cleaned_content) < len(article_content) * 0.1:
        print(f"  ❗ Очень мало контента, оставляю оригинал с предупреждением")
        cleaned_content = "⚠️ ВНИМАНИЕ: файл содержит много не-медицинского контента\n" + article_content
    
    # Обновляем файл
    new_content = metadata_part + '=== СОДЕРЖАНИЕ ===\n' + cleaned_content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    """Основная функция - обрабатывает только проблемные файлы"""
    articles_path = Path("data/processed/cardiology/Articles")
    
    if not articles_path.exists():
        print("Папка Articles не найдена!")
        return
    
    # Сначала найдём все файлы с warning
    warning_files = list(articles_path.glob("*.warning.txt"))
    print(f"Найдено файлов с предупреждениями: {len(warning_files)}")
    
    # Обрабатываем файлы, у которых есть warning
    for warning_file in warning_files:
        original_file = warning_file.with_suffix('.txt')  # Убираем .warning
        if original_file.exists():
            print(f"\n{'='*50}")
            print(f"ИСПРАВЛЕНИЕ: {original_file.name}")
            print('='*50)
            
            process_article_file_safely(original_file)
            
            # Удаляем warning файл после исправления
            warning_file.unlink()
            print(f"  Удалён warning файл")

if __name__ == "__main__":
    main()