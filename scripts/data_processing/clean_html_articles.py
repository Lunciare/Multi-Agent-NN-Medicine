# clean_html_articles.py
import re
from pathlib import Path
import json

def clean_html_content(html_content):
    """Очищает HTML контент, оставляя только медицинскую статью"""
    
    # 1. Удаляем всю навигацию, меню, рекламу
    patterns_to_remove = [
        r'Skip to main content.*?Sign in',
        r'Advertisement.*?Journal Information',
        r'Shopping cart.*?Cart',
        r'Search.*?Advanced Search',
        r'Sign in.*?REGISTER',
        r'Quick Search.*?anywhere',
        r'Publications.*?Stroke: Vascular',
        r'Information For Authors.*?International Users',
        r'Submit & Publish.*?Trend Watch',
        r'Current Issue.*?Awards',
        r'Track Citations.*?Get Access',
        r'Login options.*?Keep me logged in',
        r'Purchase Options.*?Add to Cart',
        r'Advertisement.*?Recommended',
        r'This page is managed.*?Confirm My Choices',
        r'National Center.*?Our Sites',
        r'Copyright.*?registered trademark',
        r'Privacy Preference Center.*?Vendors List',
    ]
    
    for pattern in patterns_to_remove:
        html_content = re.sub(pattern, '', html_content, flags=re.DOTALL)
    
    # 2. Оставляем только ключевые секции статьи
    sections_to_keep = [
        r'Abstract.*?Graphical Abstract',
        r'Abstract.*?Introduction',
        r'Introduction.*?Methods',
        r'Methods.*?Results',
        r'Results.*?Discussion',
        r'Discussion.*?Conclusion',
        r'Conclusion.*?References',
        r'References.*?$',
    ]
    
    cleaned_text = ""
    for pattern in sections_to_keep:
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned_text += match.group(0) + "\n\n"
    
    # 3. Если не нашли структурированные секции, пытаемся вытащить основной контент
    if not cleaned_text:
        # Удаляем все HTML теги
        cleaned_text = re.sub(r'<[^>]+>', '', html_content)
        # Удаляем лишние пробелы и переносы
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        # Оставляем только текст между Abstract и References
        abstract_match = re.search(r'Abstract(.*?)References', cleaned_text, re.DOTALL | re.IGNORECASE)
        if abstract_match:
            cleaned_text = "ABSTRACT: " + abstract_match.group(1).strip()
    
    return cleaned_text.strip()

def reprocess_html_files():
    """Переобрабатывает HTML файлы, оставляя только медицинский контент"""
    processed_path = Path("data/processed/cardiology")
    
    html_files = list(processed_path.rglob("*.txt"))
    
    print(f"Найдено файлов для очистки: {len(html_files)}")
    
    cleaned_count = 0
    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, это ли HTML-конвертация
        if 'original_format": "html"' in content and '=== СОДЕРЖАНИЕ ===' in content:
            # Разделяем метаданные и контент
            metadata_part, html_part = content.split('=== СОДЕРЖАНИЕ ===', 1)
            
            # Очищаем HTML
            cleaned_content = clean_html_content(html_part)
            
            # Проверяем, осталось ли что-то полезное
            if len(cleaned_content) > 500:  # Минимум 500 символов медицинского текста
                # Обновляем файл
                new_content = metadata_part + '=== СОДЕРЖАНИЕ ===\n' + cleaned_content
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                cleaned_count += 1
                print(f"✓ Очищен: {file_path.name}")
            else:
                print(f"✗ Мало контента, пропуск: {file_path.name}")
                # Можно пометить файл как проблемный
                error_path = file_path.with_suffix('.low_quality.txt')
                with open(error_path, 'w', encoding='utf-8') as f:
                    f.write(f"Файл содержит недостаточно медицинского контента\nОригинальный размер: {len(html_part)} символов\nОчищенный размер: {len(cleaned_content)} символов")
    
    print(f"\n✅ Очищено файлов: {cleaned_count}")

if __name__ == "__main__":
    reprocess_html_files()