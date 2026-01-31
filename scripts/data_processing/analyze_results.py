# analyze_results.py
import json
from pathlib import Path
from collections import Counter

def analyze_processed_files():
    processed_path = Path("01_PROCESSED")
    
    print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ КОНВЕРТАЦИИ")
    print("="*50)
    
    # Читаем статистику
    stats_files = list(processed_path.glob("*stats*.json"))
    if stats_files:
        with open(stats_files[0], 'r') as f:
            stats = json.load(f)
        print(f"Всего файлов: {stats.get('total_files', 0)}")
        print(f"Успешно: {stats.get('processed', 0)}")
        print(f"Ошибок: {stats.get('failed', 0)}")
    
    # Анализируем файлы
    txt_files = list(processed_path.rglob("*.txt"))
    print(f"\n📁 Конвертированных .txt файлов: {len(txt_files)}")
    
    # По категориям
    categories = Counter()
    sizes = []
    
    for file_path in txt_files:
        # Категория из имени папки
        category = file_path.parent.name
        categories[category] += 1
        
        # Размер файла
        size_kb = file_path.stat().st_size / 1024
        sizes.append(size_kb)
    
    print("\n📂 Распределение по категориям:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} файлов")
    
    print(f"\n📏 Размеры файлов:")
    print(f"  Средний: {sum(sizes)/len(sizes):.1f} KB")
    print(f"  Минимальный: {min(sizes):.1f} KB")
    print(f"  Максимальный: {max(sizes):.1f} KB")
    
    # Проверяем содержание файлов
    print("\n🔍 Проверка нескольких файлов:")
    for i, file_path in enumerate(txt_files[:3]):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(500)
        print(f"\n{i+1}. {file_path.name}")
        print(f"   Размер: {file_path.stat().st_size/1024:.1f} KB")
        print(f"   Начало: {content[:100]}...")

if __name__ == "__main__":
    analyze_processed_files()