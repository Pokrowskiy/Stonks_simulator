# Временные параметры
TICKS_PER_DAY = 24
TICKS_PER_WEEK = 168
TICK_DURATION_SECONDS = 2

MIN_MARGIN_RATIO = 0.5
UDS_CLIP_MIN = -9.99
UDS_CLIP_MAX = 9.99

COMMISSION_LEVERAGE_DAILY = 0.0001
COMMISSION_TRADE = 0.001

LIQUIDATION_DISCOUNT = 0.95

DEFAULT_RISK_RATE = 0.25  # Базовая ставка (потом модифицируется по волатильности)
VOLATILITY_RISK_MULTIPLIER = 1.0  # Risk_Rate = DEFAULT_RISK_RATE + volatility * multiplier

SAVE_INTERVAL_TICKS = TICKS_PER_DAY  # Сохранять в конце каждого дня
MARKET_STATE_FILE = "data/market_state.json"
BROKER_STATE_FILE = "data/broker_state.json"