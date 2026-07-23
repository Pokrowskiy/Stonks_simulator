"""
Простой тест Market Engine: инициализация, несколько тиков, вывод результатов.
Помогает проверить, что Market Engine работает корректно.
"""

import json
from src.market_engine.market import MarketEngine
from src.market_engine.company import Company
from src.api.market_api import create_market_router


def main():
    """Главная функция для тестирования."""
    
    print("=" * 80)
    print("ТЕСТ MARKET ENGINE")
    print("=" * 80)
    
    print("\n[1] Инициализация Market Engine...")
    engine = MarketEngine(seed=42)
    
    print("[2] Загрузка компаний из start_config.json...")
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
            profit_current=company_data["profit_base"],  # Начальная прибыль = базовая
            profit_growth=company_data["profit_growth"],
            div_payout_ratio=company_data["div_payout_ratio"],
            div_period_ticks=company_data["div_period_ticks"],
        )
        engine.add_company(company)
        print(f"  ✓ {company.ticker}: {company.name} (цена: ${company.price:.2f})")
    
    # 3. Добавляем индекс
    print("[3] Добавление индекса...")
    index = Company(
        ticker="INDEX",
        name="Market Index",
        description="Средняя цена всех компаний",
        is_index=True,
    )
    engine.add_company(index)
    print("  ✓ Индекс добавлен")
    
    # 4. Запускаем несколько тиков
    print("\n[4] Запуск 10 тиков симуляции...")
    print("-" * 80)
    
    for tick in range(1, 11):
        engine.tick()
        
        print(f"\nТик {tick}:")
        print(f"  Индекс: ${engine.index_price:.2f}")
        
        for ticker in ["GIGA", "PWR", "BANK"]:
            company = engine.get_company(ticker)
            if company:
                price_change = company.price_history[-1] - company.price_history[-2] if len(company.price_history) >= 2 else 0
                price_change_pct = (price_change / company.price_history[-2] * 100) if len(company.price_history) >= 2 else 0
                
                print(f"  {ticker}: ${company.price:.2f} " +
                      f"({price_change:+.2f}, {price_change_pct:+.2f}%) | " +
                      f"Прибыль: ${company.profit_current:.0f}")
    
    # 5. Проверяем дивиденды (устанавливаем счётчик на 1, чтобы выплатить в следующем тике)
    print("\n[5] Тест дивидендов...")
    print("-" * 80)
    company = engine.get_company("GIGA")
    company.ticks_to_next_dividend = 1  # Следующий тик - выплата
    print(f"Установили счётчик GIGA: ticks_to_next_dividend = 1")
    print(f"Цена перед дивидендом: ${company.price:.2f}")
    
    engine.tick()
    
    dividend = company.calc_dividend_amount()
    print(f"Ожидаемый дивиденд на акцию: ${dividend:.4f}")
    print(f"Цена после дивиденда: ${company.price:.2f} (упала на ~${dividend:.2f})")
    
    # 6. Добавляем событие и смотрим эффект
    print("\n[6] Тест события (новость)...")
    print("-" * 80)
    from src.market_engine.market import NewsEvent
    
    event = NewsEvent(
        event_id="test_news_1",
        name="Позитивная новость о GIGA",
        target_type="company",
        target_value="GIGA",
        impact_profit=100000.0,  # +100k прибыли
        impact_volatility=1.5,   # Волатильность x1.5
        duration_ticks=5,
        decay_type="linear"
    )
    engine.add_event(event)
    print(f"Добавлено событие: {event.name}")
    
    original_volatility = engine.get_company("GIGA").volatility
    print(f"Оригинальная волатильность GIGA: {original_volatility:.2f}")
    
    engine.tick()
    
    current_volatility = engine.get_company("GIGA").volatility
    print(f"Волатильность GIGA после события: {current_volatility:.2f}")
    print(f"Активные события: {len(engine.events)}")
    
    # 7. Выводим статистику
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    
    print(f"\nВсего тиков: {engine.tick_count}")
    print(f"Рыночный индекс: ${engine.index_price:.2f}")
    print(f"Активных событий: {len(engine.events)}")
    
    print("\nКомпании:")
    for ticker, company in sorted(engine.companies.items()):
        if not company.is_index:
            price_start = company.price_history[0] if company.price_history else company.price
            price_current = company.price
            change_pct = ((price_current - price_start) / price_start * 100) if price_start > 0 else 0
            
            print(f"  {ticker:8} | Цена: ${price_current:8.2f} | Изменение: {change_pct:+7.2f}% | " +
                  f"Прибыль: ${company.profit_current:10.0f} | " +
                  f"До дивиденда: {company.ticks_to_next_dividend:3} тиков")
    
    # 8. API тест (имитация)
    print("\n" + "=" * 80)
    print("ТЕСТ API ЭНДПОИНТОВ (имитация)")
    print("=" * 80)
    
    # Создаём router (но не запускаем сервер)
    # router = create_market_router(engine)
    
    # Имитируем GET /api/market/companies
    print("\nГЕТ /api/market/companies:")
    companies = []
    for ticker, company in engine.companies.items():
        if not company.is_index:
            price_start = company.price_history[0] if company.price_history else company.price
            change_pct = ((company.price - price_start) / price_start * 100) if price_start > 0 else 0
            companies.append({
                "ticker": ticker,
                "name": company.name,
                "price_current": round(company.price, 2),
                "price_change_percent": round(change_pct, 2),
                "volatility": company.volatility,
            })
    
    for c in sorted(companies, key=lambda x: x["ticker"]):
        print(f"  {c['ticker']:8} | {c['name']:15} | ${c['price_current']:8.2f} | " +
              f"{c['price_change_percent']:+7.2f}% | Vol: {c['volatility']:.2f}")
    
    # Имитируем GET /api/market/fundamentals/{ticker}
    print("\nГЕТ /api/market/fundamentals/GIGA:")
    company = engine.get_company("GIGA")
    fundamentals = {
        "ticker": company.ticker,
        "profit_current": round(company.profit_current, 2),
        "profit_base": round(company.profit_base, 2),
        "dividend_payout_ratio": company.div_payout_ratio,
        "ticks_to_next_payout": company.ticks_to_next_dividend,
        "dividend_per_share_next": round(company.calc_dividend_amount(), 4),
    }
    
    for key, value in fundamentals.items():
        print(f"  {key}: {value}")
    
    # Имитируем GET /api/market/index
    print("\nГЕТ /api/market/index:")
    if len(engine.index_history) >= 24:
        index_24h_ago = engine.index_history[-24]
    else:
        index_24h_ago = engine.index_history[0] if engine.index_history else engine.index_price
    
    index_change_pct = ((engine.index_price - index_24h_ago) / index_24h_ago * 100) if index_24h_ago > 0 else 0
    
    print(f"  index_price: {round(engine.index_price, 2)}")
    print(f"  index_change_percent: {round(index_change_pct, 2)}%")
    print(f"  total_companies: {sum(1 for c in engine.companies.values() if not c.is_index)}")
    
    print("\n" + "=" * 80)
    print("✓ ТЕСТ ЗАВЕРШЁН УСПЕШНО")
    print("=" * 80)


if __name__ == "__main__":
    main()