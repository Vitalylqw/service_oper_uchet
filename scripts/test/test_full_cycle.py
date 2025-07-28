#!/usr/bin/env python3
"""
Simple Full Cycle Testing Script.

Простой скрипт для запуска тестов полного цикла с реальными данными.

Использование:
    python scripts/test_full_cycle.py
    python scripts/test_full_cycle.py --quick
    python scripts/test_full_cycle.py --check-only
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check_prerequisites():
    """Проверка предварительных требований."""
    logger.info("🔍 Проверка предварительных требований...")
    
    results = {
        "excel_file": False,
        "api_server": False,
        "ui_server": False,
        "database": False
    }
    
    # Проверка Excel файла
    excel_files = [
        Path("Data_source_excel.xlsx"),
        Path("data/excel/Data_source_excel.xlsx")
    ]
    
    for excel_file in excel_files:
        if excel_file.exists():
            logger.info(f"✅ Excel файл найден: {excel_file}")
            results["excel_file"] = str(excel_file)  # Convert to string for JSON serialization
            break
    else:
        logger.error("❌ Excel файл не найден")
    
    # Проверка API сервера
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            logger.info("✅ API сервер работает")
            results["api_server"] = True
        else:
            logger.error(f"❌ API сервер вернул {response.status_code}")
    except:
        logger.error("❌ API сервер недоступен (запустите start_api_server.bat)")
    
    # Проверка UI сервера
    try:
        response = requests.get("http://localhost:3000", timeout=3)
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            logger.info("✅ React UI сервер работает")
            results["ui_server"] = True
        else:
            logger.error("❌ React UI сервер недоступен")
    except:
        logger.error("❌ React UI сервер недоступен (запустите start_react_ui.bat)")
    
    # Проверка базы данных
    db_path = Path("data/service_oper_uchet.sqlite")
    if db_path.exists():
        logger.info(f"✅ База данных найдена: {db_path}")
        results["database"] = True
    else:
        logger.warning("⚠️ База данных не найдена (будет создана автоматически)")
        results["database"] = True  # It's OK if DB doesn't exist yet
    
    return results


def get_auth_token(role: str = "analyst"):
    """Получение токена аутентификации."""
    try:
        from src.presentation.api.auth.security import create_access_token
        
        token_data = {
            "sub": role,
            "user_id": 2 if role == "analyst" else 3,
            "role": role
        }
        
        return create_access_token(token_data)
    except Exception as e:
        logger.error(f"Ошибка создания токена: {e}")
        return None


def test_excel_processing(excel_file: Path) -> dict:
    """Тест обработки Excel файла."""
    logger.info("📊 Тестирование обработки Excel файла...")
    
    # Получение токена
    token = get_auth_token("analyst")
    if not token:
        return {"status": "error", "error": "Не удалось получить токен"}
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Создание sync session
    payload = {
        "file_path": str(excel_file),
        "session_type": "full"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/sessions/",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        processing_time = time.time() - start_time
        
        if response.status_code in [200, 201]:
            session_data = response.json()
            logger.info(f"✅ Sync session создана: {session_data.get('id')}")
            logger.info(f"⏱️ Время обработки: {processing_time:.2f} секунд")
            
            return {
                "status": "success",
                "session_id": session_data.get("id"),
                "processing_time": processing_time
            }
        else:
            logger.error(f"❌ Ошибка создания session: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Исключение при обработке: {e}")
        
        return {
            "status": "error",
            "error": str(e),
            "processing_time": processing_time
        }


def test_api_endpoints() -> dict:
    """Тест API endpoints."""
    logger.info("🌐 Тестирование API endpoints...")
    
    # Получение токена viewer для чтения данных
    token = get_auth_token("viewer")
    if not token:
        return {"status": "error", "error": "Не удалось получить токен"}
    
    headers = {"Authorization": f"Bearer {token}"}
    results = {}
    
    # Тест deals endpoint
    try:
        start_time = time.time()
        response = requests.get("http://localhost:8000/api/v1/deals", headers=headers)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            deals_data = response.json()
            results["deals"] = {
                "status": "success",
                "count": deals_data.get("total", 0),
                "response_time": response_time
            }
            logger.info(f"✅ Deals endpoint: {deals_data.get('total', 0)} сделок, {response_time:.3f}с")
        else:
            results["deals"] = {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "response_time": response_time
            }
            logger.error(f"❌ Deals endpoint: HTTP {response.status_code}")
            
    except Exception as e:
        results["deals"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ Deals endpoint: {e}")
    
    # Тест sessions endpoint
    try:
        start_time = time.time()
        response = requests.get("http://localhost:8000/api/v1/sessions/", headers=headers)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            sessions_data = response.json()
            results["sessions"] = {
                "status": "success",
                "count": sessions_data.get("total", 0),
                "response_time": response_time
            }
            logger.info(f"✅ Sessions endpoint: {sessions_data.get('total', 0)} сессий, {response_time:.3f}с")
        else:
            results["sessions"] = {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "response_time": response_time
            }
            logger.error(f"❌ Sessions endpoint: HTTP {response.status_code}")
            
    except Exception as e:
        results["sessions"] = {"status": "error", "error": str(e)}
        logger.error(f"❌ Sessions endpoint: {e}")
    
    return results


def test_database_data() -> dict:
    """Тест данных в базе данных."""
    logger.info("🗄️ Проверка данных в базе данных...")
    
    db_path = Path("data/service_oper_uchet.sqlite")
    if not db_path.exists():
        logger.warning("⚠️ База данных не существует")
        return {"status": "warning", "message": "Database doesn't exist"}
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        results = {}
        
        # Проверка таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        results["tables"] = tables
        logger.info(f"📋 Таблицы в БД: {', '.join(tables)}")
        
        # Подсчет записей в основных таблицах
        main_tables = ["deal_read_model", "sync_sessions", "event_store"]
        
        for table in main_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results[table] = count
                logger.info(f"📊 {table}: {count} записей")
            else:
                results[table] = 0
                logger.warning(f"⚠️ Таблица {table} не найдена")
        
        conn.close()
        
        return {
            "status": "success",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка работы с БД: {e}")
        return {"status": "error", "error": str(e)}


def test_ui_accessibility() -> dict:
    """Тест доступности UI."""
    logger.info("🖥️ Тестирование доступности UI...")
    
    try:
        # Проверка главной страницы
        start_time = time.time()
        response = requests.get("http://localhost:3000", timeout=5)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            html_content = response.text
            
            # Проверка что это React приложение
            is_react = "root" in html_content and "script" in html_content
            
            results = {
                "status": "success",
                "load_time": load_time,
                "is_react_app": is_react,
                "content_length": len(html_content)
            }
            
            logger.info(f"✅ UI доступен: {load_time:.3f}с, React: {is_react}")
            
            return results
            
        else:
            logger.error(f"❌ UI недоступен: HTTP {response.status_code}")
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "load_time": load_time
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка UI: {e}")
        return {"status": "error", "error": str(e)}


def run_full_cycle_test(quick_mode: bool = False):
    """Запуск полного цикла тестирования."""
    logger.info("🚀 ЗАПУСК ТЕСТИРОВАНИЯ ПОЛНОГО ЦИКЛА")
    logger.info("=" * 50)
    
    start_time = datetime.now()
    results = {
        "start_time": start_time.isoformat(),
        "mode": "quick" if quick_mode else "full"
    }
    
    # 1. Проверка предварительных требований
    prerequisites = check_prerequisites()
    results["prerequisites"] = prerequisites
    
    if not all([prerequisites["excel_file"], prerequisites["api_server"]]):
        logger.error("❌ Не выполнены предварительные требования")
        logger.info("💡 Запустите серверы:")
        logger.info("   - API: start_api_server.bat")
        logger.info("   - UI: start_react_ui.bat")
        return results
    
    # 2. Тестирование обработки Excel
    excel_result = test_excel_processing(prerequisites["excel_file"])
    results["excel_processing"] = excel_result
    
    if quick_mode and excel_result["status"] != "success":
        logger.warning("⚠️ Быстрый режим: пропускаем остальные тесты из-за ошибки Excel")
        return results
    
    # 3. Тестирование API endpoints
    api_result = test_api_endpoints()
    results["api_endpoints"] = api_result
    
    # 4. Проверка данных в БД
    db_result = test_database_data()
    results["database"] = db_result
    
    # 5. Тестирование UI (если не быстрый режим)
    if not quick_mode and prerequisites["ui_server"]:
        ui_result = test_ui_accessibility()
        results["ui"] = ui_result
    
    # 6. Подведение итогов
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    results["end_time"] = end_time.isoformat()
    results["total_duration"] = total_duration
    
    # Определение общего статуса
    success_count = 0
    total_tests = 0
    
    for test_name, test_result in results.items():
        if isinstance(test_result, dict) and "status" in test_result:
            total_tests += 1
            if test_result["status"] == "success":
                success_count += 1
    
    overall_success = success_count == total_tests and success_count > 0
    results["overall_status"] = "SUCCESS" if overall_success else "PARTIAL" if success_count > 0 else "FAILED"
    
    # Вывод итогов
    logger.info("=" * 50)
    logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info(f"⏱️ Общее время: {total_duration:.2f} секунд")
    logger.info(f"✅ Успешных тестов: {success_count}/{total_tests}")
    
    status_emoji = "🎉" if overall_success else "⚠️" if success_count > 0 else "❌"
    logger.info(f"{status_emoji} Общий статус: {results['overall_status']}")
    
    # Сохранение отчета
    report_file = Path("full_cycle_test_report.json")
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 Отчет сохранен: {report_file}")
    
    return results


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Тестирование полного цикла")
    parser.add_argument("--quick", action="store_true", help="Быстрый режим тестирования")
    parser.add_argument("--check-only", action="store_true", help="Только проверка предварительных требований")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    
    args = parser.parse_args()
    
    # Настройка логирования
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<level>{time:HH:mm:ss}</level> | <level>{message}</level>"
    )
    
    if args.check_only:
        # Только проверка требований
        logger.info("🔍 Проверка предварительных требований...")
        prerequisites = check_prerequisites()
        
        all_good = all([prerequisites["excel_file"], prerequisites["api_server"], prerequisites["ui_server"]])
        
        if all_good:
            logger.info("🎉 Все требования выполнены! Можно запускать тесты.")
            sys.exit(0)
        else:
            logger.error("❌ Не все требования выполнены")
            sys.exit(1)
    
    else:
        # Полное тестирование
        results = run_full_cycle_test(quick_mode=args.quick)
        
        # Выход с соответствующим кодом
        if results.get("overall_status") == "SUCCESS":
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
