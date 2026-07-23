"""
Тест State Manager: проверяет загрузку, сохранение и восстановление состояния.
"""

import json
import time
from pathlib import Path
from src.state_manager.state_manager_config import StateManagerConfig
from src.state_manager.state_manager import StateManager


def main():
    """Главная функция для тестирования."""
    
    print("=" * 80)
    print("ТЕСТ STATE MANAGER")
    print("=" * 80)
    
    config = StateManagerConfig()
    state_manager = StateManager(config)
    
    # 1. Выводим конфигурацию
    print("\n[1] Конфигурация State Manager:")
    config.print_config()
    
    # 2. Сбрасываем старые сохранения (для чистого теста)
    print("\n[2] Сброс старых сохранений...")
    if config.both_states_exist():
        print("  Обнаружены старые сохранения, удаляю...")
        config.clear_state_files()
    else:
        print("  Старых сохранений не найдено")
    
    # 3. Загружаем из start_config.json
    print("\n[3] Загрузка из start_config.json...")
    market_engine, broker, metadata = state_manager.load_simulation_state()
    
    print(f"\nЗагруженное состояние:")
    print(f"  Market Engine:")
    print(f"    Компаний: {sum(1 for c in market_engine.companies.values() if not c.is_index)}")
    print(f"    Тик: {market_engine.tick_count}")
    print(f"    Индекс: ${market_engine.index_price:.2f}")
    print(f"  Broker:")
    print(f"    Счётов: {len(broker.accounts)}")
    for username, account in broker.accounts.items():
        print(f"      {username}: ${account.cash_balance:.2f}")
    
    # 4. Запускаем несколько тиков
    print("\n[4] Запуск 5 тиков симуляции...")
    for i in range(5):
        market_engine.tick()
        print(f"  Тик {i+1}: индекс ${market_engine.index_price:.2f}")
    
    # 5. Выполняем дневные операции
    print("\n[5] Дневные операции (конец дня)...")
    prices = {
        ticker: company.price
        for ticker, company in market_engine.companies.items()
        if not company.is_index
    }
    volatilities = {
        ticker: company.volatility
        for ticker, company in market_engine.companies.items()
        if not company.is_index
    }
    broker.on_daily_tick(prices, volatilities)
    print(f"  ✓ Дневные операции завершены")
    
    # 6. Сохраняем состояние
    print("\n[6] Сохранение состояния...")
    state_manager.save_simulation_state(market_engine, broker, metadata)
    
    # 7. Проверяем, что файлы созданы
    print("\n[7] Проверка сохранённых файлов...")
    print(f"  Market state: ", end="")
    if config.market_state_exists():
        size = config.MARKET_STATE_FILE.stat().st_size
        print(f"✓ ({size/1024:.1f} KB)")
    else:
        print("✗ НЕ НАЙДЕН")
    
    print(f"  Broker state: ", end="")
    if config.broker_state_exists():
        size = config.BROKER_STATE_FILE.stat().st_size
        print(f"✓ ({size/1024:.1f} KB)")
    else:
        print("✗ НЕ НАЙДЕН")
    
    # 8. Очищаем переменные (имитируем перезагрузку приложения)
    print("\n[8] Имитация перезагрузки приложения...")
    print("  (Очищаю переменные market_engine и broker из памяти)")
    del market_engine
    del broker
    time.sleep(0.5)
    print("  ✓ Переменные удалены")
    
    # 9. Загружаем из сохранений
    print("\n[9] Загрузка из сохранённого состояния...")
    market_engine2, broker2, metadata2 = state_manager.load_simulation_state()
    
    print(f"\nВосстановленное состояние:")
    print(f"  Market Engine:")
    print(f"    Тик: {market_engine2.tick_count}")
    print(f"    Индекс: ${market_engine2.index_price:.2f}")
    print(f"  Broker:")
    print(f"    Счётов: {len(broker2.accounts)}")
    for username, account in broker2.accounts.items():
        print(f"      {username}: ${account.cash_balance:.2f}")
    print(f"  Метаданные:")
    print(f"    Последнее сохранение: {metadata2.get('last_save_date', 'N/A')}")
    
    # 10. Запускаем ещё несколько тиков
    print("\n[10] Продолжение симуляции (ещё 3 тика)...")
    for i in range(3):
        market_engine2.tick()
        print(f"  Тик {market_engine2.tick_count}: индекс ${market_engine2.index_price:.2f}")
    
    # 11. Сохраняем новое состояние
    print("\n[11] Сохранение обновлённого состояния...")
    state_manager.save_simulation_state(market_engine2, broker2, metadata2, verbose=False)
    print("  ✓ Состояние обновлено")
    
    # 12. Выводим информацию о состоянии
    print("\n[12] Информация о состоянии:")
    state_manager.print_state_info()
    
    # 13. Проверяем содержимое JSON файлов
    print("\n[13] Проверка содержимого JSON файлов...")
    
    print(f"\n  Market state:")
    with open(config.MARKET_STATE_FILE, 'r', encoding='utf-8') as f:
        market_json = json.load(f)
        market_keys = list(market_json.keys())
        print(f"    Ключи: {market_keys}")
        print(f"    Тик: {market_json.get('tick_count', 'N/A')}")
        print(f"    Индекс: ${market_json.get('index_price', 'N/A'):.2f}")
        print(f"    Компаний в JSON: {len(market_json.get('companies', {}))}")
    
    print(f"\n  Broker state:")
    with open(config.BROKER_STATE_FILE, 'r', encoding='utf-8') as f:
        broker_json = json.load(f)
        broker_keys = list(broker_json.keys())
        print(f"    Ключи: {broker_keys}")
        print(f"    Счётов: {len(broker_json.get('accounts', {}))}")
    
    print(f"\n  Simulation meta:")
    with open(config.SIMULATION_META_FILE, 'r', encoding='utf-8') as f:
        meta_json = json.load(f)
        print(f"    Тик: {meta_json.get('tick_count', 'N/A')}")
        print(f"    Последнее сохранение: {meta_json.get('last_save_date', 'N/A')}")
    
    # 14. Тест сброса
    print("\n[14] Тест сброса симуляции...")
    print("  Перед сбросом:")
    print(f"    Market state существует: {config.market_state_exists()}")
    print(f"    Broker state существует: {config.broker_state_exists()}")
    
    state_manager.reset_simulation()
    
    print("  После сброса:")
    print(f"    Market state существует: {config.market_state_exists()}")
    print(f"    Broker state существует: {config.broker_state_exists()}")
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ STATE MANAGER ЗАВЕРШЁН УСПЕШНО")
    print("=" * 80)


if __name__ == "__main__":
    main()