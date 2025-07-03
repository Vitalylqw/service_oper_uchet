#!/usr/bin/env python3
"""
Скрипт для проверки готовности окружения разработки
"""

import sys
from pathlib import Path

import pkg_resources


def check_python_version():
    """Проверка версии Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 9:
        print("   ✅ Версия Python подходит для проекта")
        return True
    else:
        print("   ❌ Требуется Python 3.9+")
        return False


def check_packages():
    """Проверка установленных пакетов"""
    required_packages = [
        "pandas",
        "numpy",
        "openpyxl",
        "fastapi",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "pyodbc",
        "ruff",
        "black",
        "mypy",
        "pytest",
    ]

    print("\n📦 Проверка пакетов:")
    all_installed = True

    for package in required_packages:
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"   ✅ {package} ({version})")
        except pkg_resources.DistributionNotFound:
            print(f"   ❌ {package} НЕ УСТАНОВЛЕН")
            all_installed = False

    return all_installed


def check_files():
    """Проверка файлов конфигурации"""
    required_files = [
        "pyproject.toml",
        "requirements.txt",
        ".gitignore",
        "README.md",
        "excel_parser.py",
    ]

    print("\n📁 Проверка файлов:")
    all_exist = True

    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"   ✅ {file_name} ({size} байт)")
        else:
            print(f"   ❌ {file_name} НЕ НАЙДЕН")
            all_exist = False

    return all_exist


def check_parser():
    """Проверка работы парсера"""
    print("\n🔧 Проверка парсера:")
    try:
        from excel_parser import ExcelParser  # noqa: F401

        print("   ✅ Импорт парсера успешен")

        # Проверяем существование тестового файла
        test_file = Path("Data_source_excel.xlsx")
        if test_file.exists():
            print("   ✅ Тестовый Excel файл найден")
            return True
        else:
            print("   ⚠️ Тестовый Excel файл не найден")
            return False

    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        return False


def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА ОКРУЖЕНИЯ РАЗРАБОТКИ")
    print("=" * 50)

    checks = [
        ("Python", check_python_version),
        ("Пакеты", check_packages),
        ("Файлы", check_files),
        ("Парсер", check_parser),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))

    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 50)

    all_good = True
    for name, result in results:
        status = "✅ ГОТОВО" if result else "❌ ПРОБЛЕМЫ"
        print(f"{name:.<20} {status}")
        if not result:
            all_good = False

    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ОКРУЖЕНИЕ ПОЛНОСТЬЮ ГОТОВО К РАЗРАБОТКЕ!")
        print("Можно приступать к работе:")
        print("  • python excel_parser.py  - тест парсера")
        print("  • ruff check .            - проверка кода")
        print("  • pytest                  - запуск тестов")
    else:
        print("⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print("Необходимо устранить ошибки перед началом разработки.")

    print("=" * 50)


if __name__ == "__main__":
    main()
