"""
Тест Broker: проверяет управление счётами, ордера, маржу, ликвидацию.
"""

import json
from src.broker_engine.broker import Broker
from src.market_engine.market import MarketEngine
from src.market_engine.company import Company


def main():
    """Главная функция для тестирования."""
    
    print("=" * 80)
    print("ТЕСТ BROKER")
    print("=" * 80)
    
    # 1. Инициализируем Market Engine (для цен)
    print("\n[1] Инициализация Market Engine...")
    engine = MarketEngine(seed=42)
    
    with open("config/start_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    for company_data in config["companies"]:
        company = Company(
            ticker=company_data["ticker"],
            name=company_data["name"],
            description=company_data["description"],
            sectors=company_data["sectors"],
            price=company_data["price_initial"],
            volatility=company_data["volatility"],
            profit_base=company_data["profit_base"],
            profit_current=company_data["profit_base"],
            profit_growth=company_data["profit_growth"],
            div_payout_ratio=company_data["div_payout_ratio"],
            div_period_ticks=company_data["div_period_ticks"],
        )
        engine.add_company(company)
    
    print(f"✓ Добавлено {len(engine.companies)} компаний")
    
    # 2. Инициализируем Broker
    print("\n[2] Инициализация Broker...")
    broker = Broker()
    print("✓ Broker инициализирован")
    
    # 3. Создаём счёты
    print("\n[3] Создание счётов...")
    
    for user_data in config["users"]:
        account = broker.create_account(
            username=user_data["username"],
            initial_balance=user_data["initial_balance"]
        )
        print(f"  ✓ {account.username}: ${account.cash_balance:.2f}")
    
    # 4. Получаем цены и волатильности
    print("\n[4] Получение цен из Market Engine...")
    
    prices = {
        ticker: company.price
        for ticker, company in engine.companies.items()
        if not company.is_index
    }
    
    volatilities = {
        ticker: company.volatility
        for ticker, company in engine.companies.items()
        if not company.is_index
    }
    
    print(f"✓ Получены цены {len(prices)} компаний:")
    for ticker, price in sorted(prices.items()):
        print(f"  {ticker}: ${price:.2f}")
    
    # 5. Выполняем ордера
    print("\n[5] Выполнение ордеров...")
    print("-" * 80)
    
    # BUY: Admin покупает 50 GIGA
    print("\nОрдер 1: Admin BUY 50 GIGA")
    order1 = broker.execute_order(
        username="Admin",
        ticker="GIGA",
        action="BUY",
        quantity=50,
        current_price=prices["GIGA"],
        volatilities=volatilities
    )
    print(f"  Статус: {order1.status}")
    print(f"  Комиссия: ${order1.commission:.2f}")
    
    if order1.status == "EXECUTED":
        account = broker.get_account("Admin")
        print(f"  Позиция GIGA: {account.positions.get('GIGA', 0)}")
        print(f"  Оставшийся баланс: ${account.cash_balance:.2f}")
    
    # BUY: Mint_AI покупает 100 PWR
    print("\nОрдер 2: Mint_AI BUY 100 PWR")
    order2 = broker.execute_order(
        username="Mint_AI",
        ticker="PWR",
        action="BUY",
        quantity=100,
        current_price=prices["PWR"],
        volatilities=volatilities
    )
    print(f"  Статус: {order2.status}")
    
    # SELL: Mint_AI шортит 10 BANK
    print("\nОрдер 3: Mint_AI SELL 10 BANK (шорт)")
    order3 = broker.execute_order(
        username="Mint_AI",
        ticker="BANK",
        action="SELL",
        quantity=10,
        current_price=prices["BANK"],
        volatilities=volatilities
    )
    print(f"  Статус: {order3.status}")
    
    if order3.status == "EXECUTED":
        account = broker.get_account("Mint_AI")
        print(f"  Позиция BANK (шорт): {account.positions.get('BANK', 0)}")
    
    # 6. Проверяем маржу
    print("\n[6] Проверка маржи и УДС...")
    print("-" * 80)
    
    for username in ["Admin", "Mint_AI"]:
        account = broker.get_account(username)
        
        portfolio_value = account.calc_portfolio_value(prices)
        initial_margin = account.calc_initial_margin(prices, volatilities)
        min_margin = account.calc_min_margin(prices, volatilities)
        uds = account.calc_uds(prices, volatilities)
        
        print(f"\n{username}:")
        print(f"  Cash balance: ${account.cash_balance:.2f}")
        print(f"  Portfolio value: ${portfolio_value:.2f}")
        print(f"  Initial margin: ${initial_margin:.2f}")
        print(f"  Min margin: ${min_margin:.2f}")
        print(f"  УДС: {uds:.2f} ({account.get_uds_status(uds)})")
        print(f"  Позиции: {account.positions}")
    
    # 7. Запускаем несколько тиков (цены меняются)
    print("\n[7] Запуск 5 тиков (цены меняются)...")
    
    for i in range(5):
        engine.tick()
    
    # Обновляем цены
    prices = {
        ticker: company.price
        for ticker, company in engine.companies.items()
        if not company.is_index
    }
    
    print("✓ После 5 тиков:")
    print(f"  Индекс: ${engine.index_price:.2f}")
    print(f"  GIGA: ${prices['GIGA']:.2f}")
    print(f"  PWR: ${prices['PWR']:.2f}")
    print(f"  BANK: ${prices['BANK']:.2f}")
    
    # 8. Проверяем УДС снова
    print("\n[8] УДС после изменения цен...")
    
    for username in ["Admin", "Mint_AI"]:
        account = broker.get_account(username)
        uds = account.calc_uds(prices, volatilities)
        
        print(f"\n{username}: УДС = {uds:.2f} ({account.get_uds_status(uds)})")
    
    # 9. Пытаемся сделать ордер, который нарушает маржу
    print("\n[9] Попытка ордера, нарушающего маржу...")
    
    account = broker.get_account("Viewer_1")
    print(f"  Баланс Viewer_1: ${account.cash_balance:.2f}")
    
    # Пытаемся купить слишком много (будет отклонено)
    print(f"  Пытаемся купить 1000 GIGA по ${prices['GIGA']:.2f}...")
    
    order_bad = broker.execute_order(
        username="Viewer_1",
        ticker="GIGA",
        action="BUY",
        quantity=1000,
        current_price=prices["GIGA"],
        volatilities=volatilities
    )
    
    print(f"  Статус: {order_bad.status}")
    if order_bad.status == "REJECTED":
        print(f"  Причина: {order_bad.rejection_reason}")
    
    # 10. Дневная операция (комиссия за плечо)
    print("\n[10] Дневная операция (вычет комиссии за плечо)...")
    
    account_before = broker.get_account("Mint_AI")
    balance_before = account_before.cash_balance
    
    broker.on_daily_tick(prices, volatilities)
    
    account_after = broker.get_account("Mint_AI")
    balance_after = account_after.cash_balance
    
    commission = balance_before - balance_after
    print(f"  Баланс до: ${balance_before:.2f}")
    print(f"  Баланс после: ${balance_after:.2f}")
    print(f"  Комиссия за плечо: ${commission:.2f}")
    print(f"  История портфеля: {len(account_after.portfolio_history)} записей")
    
    # 11. Сводка по счётам
    print("\n[11] Полная сводка по всем счётам...")
    print("-" * 80)
    
    for username in broker.accounts.keys():
        summary = broker.get_account_summary(username, prices, volatilities)
        
        print(f"\n{username}:")
        print(f"  UДС: {summary['uds']:.2f} ({summary['uds_status']})")
        print(f"  Cash: ${summary['balances']['cash']:.2f}")
        print(f"  Portfolio value: ${summary['balances']['portfolio_value_current']:.2f}")
        print(f"  Total return: {summary['pnl']['total_return_percent']:.2f}%")
        print(f"  Positions: {len(summary['positions'])}")
    
    # 12. История ордеров
    print("\n[12] История ордеров...")
    
    all_orders = broker.get_order_history(limit=10)
    print(f"  Всего ордеров: {len(all_orders)}")
    
    for order in all_orders:
        print(f"    {order.order_id[:20]}... | {order.username:10} | {order.action:4} " +
              f"{order.quantity:3} {order.ticker:6} | {order.status:8}")
    
    # 13. Статус брокера
    print("\n[13] Статус брокера...")
    
    print(f"  Всего счётов: {len(broker.accounts)}")
    print(f"  Ликвидировано: {sum(1 for a in broker.accounts.values() if a.is_liquidated)}")
    print(f"  Всего ордеров: {len(broker.order_history)}")
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ BROKER ЗАВЕРШЁН УСПЕШНО")
    print("=" * 80)


if __name__ == "__main__":
    main()