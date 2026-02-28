#!/usr/bin/env python3
"""
Скрипт для исправления неправильных импортов domain в application слое
"""

import re
from pathlib import Path

def fix_imports_in_file(file_path: Path) -> bool:
    """Исправляет импорты в одном файле"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Замены для application слоя
        if 'src/application' in str(file_path):
            content = re.sub(r'^from domain\.', 'from ...domain.', content, flags=re.MULTILINE)
        # Замены для infrastructure слоя  
        elif 'src/infrastructure' in str(file_path):
            content = re.sub(r'^from domain\.', 'from ...domain.', content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Исправлен файл: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка при обработке {file_path}: {e}")
        return False

def main():
    """Основная функция"""
    
    # Файлы с проблемными импортами
    problem_files = [
        "src/application/sync_orchestrator/orchestrator.py",
        "src/application/change_detector/detector.py", 
        "src/application/data_validator/validator.py",
        "src/application/data_validator/excel_validator.py",
        "src/infrastructure/workers/read_model_builder.py",
        "src/infrastructure/workers/simple_position_sync.py",
        "src/infrastructure/database/repositories.py",
        "src/infrastructure/database/event_store.py",
    ]
    
    fixed_count = 0
    
    for file_str in problem_files:
        file_path = Path(file_str)
        if file_path.exists():
            if fix_imports_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  Файл не найден: {file_path}")
    
    print(f"\n📊 Исправлено файлов: {fixed_count}/{len(problem_files)}")

if __name__ == "__main__":
    main()



