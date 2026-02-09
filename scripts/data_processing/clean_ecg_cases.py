# clean_ecg_cases.py
"""
Скрипт для очистки кейсов из Dr. Smith's ECG Blog.
Удаляет навигацию, даты, ссылки, рекламу, подписку и прочий мусор.
"""

import re
from pathlib import Path
import json
from typing import List, Tuple

def clean_ecg_case_content(content: str) -> str:
    """
    Очищает контент кейса ECG блога, оставляя только медицинскую информацию.
    """
    original_length = len(content)
    
    # 1. Удаляем заголовки страниц с датами и URL
    page_patterns = [
        # --- Страница X --- с датой и названием
        r'--- Страница \d+ ---\s*\n\d{2}/\d{2}/\d{4}, \d{2}:\d{2}.*?- Dr\. Smith’s ECG Blog\s*\n',
        # Просто --- Страница X ---
        r'--- Страница \d+ ---\s*\n',
        # Дата и название в начале строки
        r'\d{2}/\d{2}/\d{4}, \d{2}:\d{2}.*?- Dr\. Smith’s ECG Blog',
        # URL в конце строки
        r'https://drsmithsecgblog\.com/.*?/\d+/\d+\s*\n',
    ]
    
    for pattern in page_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # 2. Удаляем навигацию и заголовок блога
    navigation_patterns = [
        # Заголовок блога и редакторы
        r'Dr\. Smith\'s ECG Blog\s*\nInstructive ECGs in Emergency Medicine Clinical Content\s*\n'
        r'Associate Editors:.*?Home.*?\n',
        # Всё от "Home" до начала контента
        r'Home.*?\n(?:.*?\n){0,3}',
    ]
    
    for pattern in navigation_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. Удаляем блок "Write a Comment" и всё что после
    if 'Write a Comment' in content:
        comment_start = content.find('Write a Comment')
        if comment_start > 0:
            # Проверяем, есть ли медицинский контент до коммента
            before_comment = content[:comment_start]
            medical_keywords = ['ECG', 'chest pain', 'patient', 'diagnosis', 'treatment', 'STEMI', 'OMI']
            
            if any(keyword.lower() in before_comment.lower() for keyword in medical_keywords):
                content = before_comment.strip()
    
    # 4. Удаляем блок ABOUT и всё что в нём
    about_patterns = [
        r'ABOUT.*?FOLLOW US ON X \(TWITTER\).*?(?=\n\n|\Z)',
        r'FOLLOW US ON X \(TWITTER\).*?FEATURED POSTS.*?(?=\n\n|\Z)',
        r'FEATURED POSTS.*?BLOG ARCHIVE.*?(?=\n\n|\Z)',
        r'BLOG ARCHIVE.*?Select Month.*?(?=\n\n|\Z)',
        r'LABELS.*?Read Next.*?(?=\n\n|\Z)',
        r'Read Next.*?Never Miss a Beat.*?(?=\n\n|\Z)',
        r'Never Miss a Beat.*?Expert ECG Interpretation.*?(?=\n\n|\Z)',
        r'© \d{4} — Dr\. Smith\'s ECG Blog\..*?(?=\n\n|\Z)',
        # Лицензия
        r'This work is licensed under.*?International License\.',
        # Ссылки на соцсети
        r'Follow @\w+\s*',
    ]
    
    for pattern in about_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 5. Удаляем отдельные строки с рекламой/ссылками
    trash_lines = [
        'Trusted insights, no spam—only ECG brilliance.',
        'Expert ECG Interpretation and Emergency Cardiology Education',
        'Get the latest expert ECG cases, clinical pearls, and interpretation tips',
        'Email Address Subscribe',
        'Dr. Smith\'s Google Scholar Profile',
        'Dr. Smith Articles on PubMed',
        'FACULTY PHYSICIAN',
        r'Written by .*? on.*?\d{4}',
        r'This was written by .*?\..*?\n',
        r'This was sent by .*?\..*?\n',
    ]
    
    for line_pattern in trash_lines:
        content = re.sub(line_pattern + r'.*?\n', '', content, flags=re.IGNORECASE)
    
    # 6. Удаляем метки-теги (всё в кавычках через пробел)
    # Ищем строки, которые состоят в основном из тегов в кавычках
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Если строка содержит много тегов в кавычках - пропускаем
        if line.count('"') >= 4:  # Много кавычек = вероятно теги
            # Но проверяем, нет ли в строке медицинского контента
            medical_indicators = ['ECG', 'pain', 'patient', 'heart', 'chest', 'diagnos', 'treat']
            if not any(indicator.lower() in line.lower() for indicator in medical_indicators):
                continue  # Пропускаем эту строку
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # 7. Удаляем отдельные слова-теги
    tag_pattern = r'\"[^\"]+\"\(?\d*\)?\s*'
    content = re.sub(tag_pattern, '', content)
    
    # 8. Очищаем форматирование
    content = re.sub(r'\n{3,}', '\n\n', content)  # Множественные переносы
    content = re.sub(r'[ \t]{2,}', ' ', content)  # Множественные пробелы
    content = content.strip()
    
    # 9. Проверяем, не удалили ли весь медицинский контент
    medical_keywords = ['ECG', 'patient', 'chest', 'pain', 'heart', 'diagnosis', 
                       'treatment', 'history', 'symptoms', 'findings', 'case']
    
    has_medical_content = any(keyword.lower() in content.lower() for keyword in medical_keywords)
    
    if not has_medical_content or len(content) < 100:
        print(f"  ⚠️  Предупреждение: возможно удалён медицинский контент")
        print(f"     Длина: {len(content)} символов")
        return None  # Возвращаем None чтобы оставить оригинал
    
    cleaned_length = len(content)
    print(f"  Очищено: {original_length} → {cleaned_length} chars ({cleaned_length/original_length*100:.1f}%)")
    
    return content

def process_ecg_case_file(file_path: Path) -> Tuple[bool, int, int]:
    """
    Обрабатывает один файл кейса ECG.
    Возвращает (успех, оригинальная_длина, очищенная_длина)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_content = f.read()
        
        if '=== СОДЕРЖАНИЕ ===' not in full_content:
            return False, 0, 0
        
        # Разделяем метаданные и контент
        metadata_part, case_content = full_content.split('=== СОДЕРЖАНИЕ ===', 1)
        
        # Проверяем, это ли кейс ECG блога
        is_ecg_case = any(keyword in full_content for keyword in 
                         ['Dr. Smith', 'ECG Blog', 'chest pain', 'ECG'])
        
        if not is_ecg_case:
            return False, 0, 0
        
        print(f"\n📋 Обработка: {file_path.name}")
        
        # Очищаем контент
        cleaned_content = clean_ecg_case_content(case_content)
        
        if cleaned_content is None:
            print(f"  ❌ Файл не обработан: недостаточно медицинского контента")
            return False, len(case_content), 0
        
        # Обновляем файл
        new_content = metadata_part + '=== СОДЕРЖАНИЕ ===\n' + cleaned_content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, len(case_content), len(cleaned_content)
        
    except Exception as e:
        print(f"  ❌ Ошибка обработки {file_path.name}: {str(e)}")
        return False, 0, 0

def analyze_case_file(file_path: Path) -> dict:
    """
    Анализирует файл кейса для отладки.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '=== СОДЕРЖАНИЕ ===' in content:
        _, case_content = content.split('=== СОДЕРЖАНИЕ ===', 1)
        
        # Проверяем наличие мусора
        trash_patterns = {
            'страницы': r'--- Страница \d+ ---',
            'даты': r'\d{2}/\d{2}/\d{4}, \d{2}:\d{2}',
            'url': r'https://drsmithsecgblog\.com',
            'навигация': r'Dr\. Smith\'s ECG Blog',
            'теги': r'LABELS',
            'реклама': r'Never Miss a Beat',
            'комментарии': r'Write a Comment',
        }
        
        trash_counts = {}
        for name, pattern in trash_patterns.items():
            matches = len(re.findall(pattern, case_content, re.IGNORECASE))
            trash_counts[name] = matches
        
        # Медицинский контент
        medical_keywords = ['ECG', 'chest pain', 'patient', 'diagnosis', 'STEMI', 'OMI', 'angina']
        medical_count = sum(1 for kw in medical_keywords if kw.lower() in case_content.lower())
        
        return {
            'file': file_path.name,
            'total_length': len(case_content),
            'trash_patterns': trash_counts,
            'medical_keywords': medical_count,
            'has_ecg_blog': 'Dr. Smith' in case_content or 'ECG Blog' in case_content,
        }
    return {}

def main():
    """
    Основная функция очистки кейсов ECG.
    """
    cases_path = Path("data/processed/cardiology/Cases")
    
    if not cases_path.exists():
        print(f"❌ Папка Cases не найдена: {cases_path}")
        return
    
    # 1. Сначала проанализируем файлы
    print("🔍 Анализ файлов кейсов...")
    txt_files = list(cases_path.glob("*.txt"))
    print(f"Найдено файлов: {len(txt_files)}")
    
    ecg_cases = []
    other_cases = []
    
    for file_path in txt_files[:10]:  # Первые 10 для анализа
        analysis = analyze_case_file(file_path)
        if analysis:
            if analysis['has_ecg_blog']:
                ecg_cases.append(analysis)
            else:
                other_cases.append(analysis)
    
    print(f"\n📊 Результаты анализа (первые 10 файлов):")
    print(f"✅ Кейсы Dr. Smith's ECG Blog: {len(ecg_cases)}")
    print(f"📄 Другие кейсы: {len(other_cases)}")
    
    if ecg_cases:
        print("\nОбразец мусора в ECG кейсах:")
        for pattern, count in ecg_cases[0]['trash_patterns'].items():
            if count > 0:
                print(f"  - {pattern}: {count}")
    
    # 2. Подтверждение очистки
    print(f"\n{'='*60}")
    print("ОЧИСТКА КЕЙСОВ DR. SMITH'S ECG BLOG")
    print("="*60)
    print("Будет удалено:")
    print("  • Заголовки страниц (--- Страница X ---)")
    print("  • Даты и URL")
    print("  • Навигация блога")
    print("  • Блок ABOUT и реклама")
    print("  • Теги (LABELS)")
    print("  • Форма подписки")
    print("  • Футер с копирайтом")
    
    response = input("\nПродолжить очистку? (y/n): ").lower()
    if response != 'y':
        print("Очистка отменена.")
        return
    
    # 3. Обработка всех файлов
    print(f"\n🔄 Обработка {len(txt_files)} файлов...")
    
    total_original = 0
    total_cleaned = 0
    processed_count = 0
    
    for file_path in txt_files:
        success, orig_len, cleaned_len = process_ecg_case_file(file_path)
        if success:
            total_original += orig_len
            total_cleaned += cleaned_len
            processed_count += 1
    
    # 4. Статистика
    print(f"\n{'='*60}")
    print("📊 ИТОГИ ОЧИСТКИ")
    print("="*60)
    print(f"Обработано файлов: {processed_count}/{len(txt_files)}")
    print(f"Общий объём:")
    print(f"  До очистки: {total_original:,} символов")
    print(f"  После очистки: {total_cleaned:,} символов")
    if total_original > 0:
        reduction = (total_original - total_cleaned) / total_original * 100
        print(f"  Удалено: {reduction:.1f}% мусора")
    
    # 5. Создаём отчёт
    report = {
        'total_files': len(txt_files),
        'processed_files': processed_count,
        'total_original_chars': total_original,
        'total_cleaned_chars': total_cleaned,
        'reduction_percent': reduction if total_original > 0 else 0,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
    }
    
    report_path = cases_path / "cleaning_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Отчёт сохранён: {report_path}")
    
    # 6. Показываем пример очищенного файла
    if processed_count > 0:
        print(f"\n🔍 Пример очищенного файла:")
        sample_file = txt_files[0]
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '=== СОДЕРЖАНИЕ ===' in content:
            _, sample_content = content.split('=== СОДЕРЖАНИЕ ===', 1)
            print("\n" + "="*40)
            print("ПЕРВЫЕ 500 СИМВОЛОВ:")
            print("="*40)
            print(sample_content[:500] + "...")
            print("="*40)

def quick_clean_single_file(file_path: str):
    """
    Быстрая очистка одного файла для тестирования.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Файл не найден: {file_path}")
        return
    
    success, orig_len, cleaned_len = process_ecg_case_file(path)
    if success:
        print(f"\n✅ Файл очищен: {path.name}")
        print(f"   Было: {orig_len:,} символов")
        print(f"   Стало: {cleaned_len:,} символов")
        print(f"   Удалено: {(orig_len - cleaned_len)/orig_len*100:.1f}%")
    else:
        print(f"\n❌ Не удалось очистить файл")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Очистка одного файла
        quick_clean_single_file(sys.argv[1])
    else:
        # Очистка всей папки Cases
        main()