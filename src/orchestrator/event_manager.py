import json
import uuid
from typing import Dict, List, Any, Optional
from src.market_engine.market import NewsEvent, TrendEvent


class EventManager:
    """    
    События хранятся в events_config.json в следующем формате:
    {
        "events": [
            {
                "trigger_tick": 48,
                "name": "Tech Boom",
                "type": "news",  # или "trend"
                "target_type": "sector",
                "target": "Tech",
                "impact_profit": 100000,
                "impact_volatility": 1.3,
                "duration_ticks": 48,
                "decay_type": "linear"
            }
        ]
    }
    """
    
    def __init__(self, config_path: str = "config/events_config.json"):
        self.config_path = config_path
        self.events_config: List[Dict[str, Any]] = []
        self.triggered_events: set = set()
        self.load_config()
    
    def load_config(self) -> None:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.events_config = data.get("events", [])
            print(f"✓ EventManager: загружено {len(self.events_config)} событий из {self.config_path}")
        except FileNotFoundError:
            print(f"⚠️  EventManager: файл {self.config_path} не найден. События не будут загружены.")
            self.events_config = []
        except json.JSONDecodeError:
            print(f"❌ EventManager: ошибка парсинга JSON в {self.config_path}")
            self.events_config = []
    
    def check_and_trigger(self, current_tick: int, market_engine: Any) -> None:
        for event_config in self.events_config:
            trigger_tick = event_config.get("trigger_tick")
            if trigger_tick == current_tick:
                event_id = f"{trigger_tick}_{event_config.get('name', 'unknown')}"
                
                if event_id not in self.triggered_events:
                    self._trigger_event(event_config, market_engine)
                    self.triggered_events.add(event_id)
    
    def _trigger_event(self, event_config: Dict[str, Any], market_engine: Any) -> None:
        event_type = event_config.get("type", "news")
        name = event_config.get("name", "Unknown Event")
        
        try:
            if event_type == "news":
                self._inject_news_event(event_config, market_engine)
            elif event_type == "trend":
                self._inject_trend_event(event_config, market_engine)
            else:
                print(f"❌ EventManager: неизвестный тип события '{event_type}'")
        except Exception as e:
            print(f"❌ EventManager: ошибка при инжекте события '{name}': {e}")
    
    def _inject_news_event(self, event_config: Dict[str, Any], market_engine: Any) -> None:
        event_id = str(uuid.uuid4())
        name = event_config.get("name", "News Event")
        target_type = event_config.get("target_type", "market")
        target = event_config.get("target", "MARKET")
        description = event_config.get("description", "No description provided.")
        impact_profit = event_config.get("impact_profit", 0.0)
        impact_volatility = event_config.get("impact_volatility", 1.0)
        duration_ticks = event_config.get("duration_ticks", 24)
        decay_type = event_config.get("decay_type", "linear")
        
        event = NewsEvent(
            event_id=event_id,
            name=description,
            target_type=target_type,
            target_value=target,
            impact_profit=impact_profit,
            impact_volatility=impact_volatility,
            duration_ticks=duration_ticks,
            decay_type=decay_type
        )
        
        market_engine.add_event(event)
        print(f"📰 EventManager [Тик {market_engine.tick_count}]: инжекнуто событие '{name}'")
    
    def _inject_trend_event(self, event_config: Dict[str, Any], market_engine: Any) -> None:
        event_id = str(uuid.uuid4())
        name = event_config.get("name", "Trend Event")
        target = event_config.get("target", "MARKET")
        description = event_config.get("description", "No description provided.")
        trend_direction = event_config.get("trend_direction", "UP")
        strength = event_config.get("strength", 0.5)
        duration_ticks = event_config.get("duration_ticks", 24)
        
        event = TrendEvent(
            event_id=event_id,
            name=description,
            target_value=target,
            trend_direction=trend_direction,
            strength=strength,
            duration_ticks=duration_ticks
        )
        
        market_engine.add_trend_event(event)
        print(f"📈 EventManager [Тик {market_engine.tick_count}]: инжекнуто событие '{name}' ({trend_direction})")
    
    def get_upcoming_events(self, current_tick: int, next_n_ticks: int = 100) -> List[Dict[str, Any]]:
        upcoming = []
        for event_config in self.events_config:
            trigger_tick = event_config.get("trigger_tick", 0)
            if current_tick < trigger_tick <= current_tick + next_n_ticks:
                upcoming.append({
                    "tick": trigger_tick,
                    "name": event_config.get("name", "Unknown"),
                    "type": event_config.get("type", "unknown"),
                    "time_until": trigger_tick - current_tick
                })
        return sorted(upcoming, key=lambda x: x["tick"])
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        return self.events_config
    
    def get_event_timeline(self) -> str:
        timeline = "\n📅 РАСПИСАНИЕ СОБЫТИЙ:\n"
        timeline += "=" * 80 + "\n"
        
        sorted_events = sorted(self.events_config, key=lambda x: x.get("trigger_tick", 0))
        
        for event in sorted_events:
            tick = event.get("trigger_tick", 0)
            name = event.get("name", "Unknown")
            event_type = event.get("type", "unknown")
            days = tick // 24
            hours = tick % 24
            emoji = "📰" if event_type == "news" else "📈"
            timeline += f"{emoji} Тик {tick:4d} (День {days:2d}, {hours:2d}:00) - {name}\n"
        
        timeline += "=" * 80 + "\n"
        return timeline