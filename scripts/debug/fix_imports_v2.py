#!/usr/bin/env python3
"""
Скрипт для исправления всех неправильных импортов
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
            content = re.sub(r'^from infrastructure\.', 'from ...infrastructure.', content, flags=re.MULTILINE)
            content = re.sub(r'^from application\.', 'from ..', content, flags=re.MULTILINE)
        # Замены для infrastructure слоя  
        elif 'src/infrastructure' in str(file_path):
            content = re.sub(r'^from domain\.', 'from ...domain.', content, flags=re.MULTILINE)
            content = re.sub(r'^from application\.', 'from ...application.', content, flags=re.MULTILINE)
        
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
    
    # Ищем все Python файлы в application и infrastructure
    dirs = ["src/application", "src/infrastructure"]
    problem_files = []
    
    for dir_path in dirs:
        for py_file in Path(dir_path).rglob("*.py"):
            problem_files.append(str(py_file))
    
    fixed_count = 0
    
    for file_str in problem_files:
        file_path = Path(file_str)
        if file_path.exists():
            if fix_imports_in_file(file_path):
                fixed_count += 1
    
    print(f"\n📊 Исправлено файлов: {fixed_count}/{len(problem_files)}")

if __name__ == "__main__":
    main()



