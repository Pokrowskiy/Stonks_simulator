import json
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.state_manager.state_manager_config import StateManagerConfig
from src.market_engine.market import MarketEngine
from src.market_engine.company import Company
from src.broker_engine.broker import Broker


class StateManager:
    """Управляет сохранением и загрузкой состояния симуляции."""
    
    def __init__(self, config: StateManagerConfig = StateManagerConfig):
        """
        Инициализирует State Manager.
        
        Args:
            config: StateManagerConfig с путями к файлам
        """
        self.config = config
        self.config.ensure_directories()
    
    # ===== ЗАГРУЗКА СОСТОЯНИЯ =====
    
    def load_simulation_state(self) -> Tuple[MarketEngine, Broker, Dict[str, Any]]:
        """
        Загружает полное состояние симуляции.
        
        Алгоритм:
        1. Если существуют сохранённые состояния → загружает их
        2. Иначе → загружает из start_config.json
        
        Returns:
            Кортеж (market_engine, broker, metadata)
            
        Raises:
            FileNotFoundError: Если не найден ни start_config, ни сохранённое состояние
        """
        print("\n" + "=" * 80)
        print("STATE MANAGER: ЗАГРУЗКА СОСТОЯНИЯ")
        print("=" * 80)
        
        # Проверяем, существуют ли сохранённые состояния
        if self.config.both_states_exist():
            print("\n[1] Обнаружено сохранённое состояние")
            return self._load_from_saved_state()
        
        # Если нет сохранений → загружаем из стартовой конфигурации
        print("\n[1] Сохранённое состояние не найдено")
        print("[2] Загружаю из start_config.json...")
        return self._load_from_start_config()
    
    def _load_from_saved_state(self) -> Tuple[MarketEngine, Broker, Dict[str, Any]]:
        """
        Загружает состояние из сохранённых файлов.
        
        Returns:
            Кортеж (market_engine, broker, metadata)
        """
        print(f"  Загружаю Market Engine из: {self.config.MARKET_STATE_FILE}")
        print(f"  Загружаю Broker из: {self.config.BROKER_STATE_FILE}")
        
        try:
            # Загружаем Market Engine
            with open(self.config.MARKET_STATE_FILE, 'r', encoding='utf-8') as f:
                market_state = json.load(f)
            market_engine = MarketEngine.from_dict(market_state)
            print(f"    ✓ Market Engine загружен (тик {market_engine.tick_count})")
            
            # Загружаем Broker
            with open(self.config.BROKER_STATE_FILE, 'r', encoding='utf-8') as f:
                broker_state = json.load(f)
            broker = Broker.from_dict(broker_state)
            print(f"    ✓ Broker загружен ({len(broker.accounts)} счётов)")
            
            # Загружаем метаданные (если есть)
            metadata = {}
            if self.config.SIMULATION_META_FILE.exists():
                with open(self.config.SIMULATION_META_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                print(f"    ✓ Метаданные загружены")
            
            print("\n✓ Симуляция восстановлена из сохранений!")
            return market_engine, broker, metadata
        
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            raise RuntimeError(
                f"Ошибка при загрузке сохранённого состояния: {str(e)}\n"
                f"Попробуйте удалить файлы сохранений и перезагрузить симуляцию"
            )
    
    def _load_from_start_config(self) -> Tuple[MarketEngine, Broker, Dict[str, Any]]:
        """
        Загружает состояние из стартовой конфигурации.
        
        Returns:
            Кортеж (market_engine, broker, metadata)
        """
        if not self.config.start_config_exists():
            raise FileNotFoundError(
                f"Файл start_config.json не найден: {self.config.START_CONFIG_FILE}"
            )
        
        print(f"  Загружаю конфиг из: {self.config.START_CONFIG_FILE}")
        
        # Загружаем конфиг
        with open(self.config.START_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Инициализируем Market Engine
        print("\n[3] Инициализация Market Engine...")
        market_engine = MarketEngine()
        
        for company_data in config.get("companies", []):
            company = Company(
                ticker=company_data["ticker"],
                name=company_data["name"],
                description=company_data.get("description", ""),
                sectors=company_data.get("sectors", []),
                price=company_data.get("price_initial", 100.0),
                volatility=company_data.get("volatility", 0.15),
                profit_base=company_data.get("profit_base", 500000.0),
                profit_current=company_data.get("profit_base", 500000.0),
                profit_growth=company_data.get("profit_growth", 1000.0),
                div_payout_ratio=company_data.get("div_payout_ratio", 0.5),
                div_period_ticks=company_data.get("div_period_ticks", 168),
            )
            market_engine.add_company(company)
        
        print(f"  ✓ Добавлено {len(market_engine.companies)} компаний")
        
        # Добавляем индекс
        index = Company(
            ticker="INDEX",
            name="Market Index",
            description="Средняя цена всех компаний",
            is_index=True,
        )
        market_engine.add_company(index)
        print("  ✓ Индекс добавлен")
        
        # Инициализируем Broker
        print("\n[4] Инициализация Broker...")
        broker = Broker()
        
        for user_data in config.get("users", []):
            broker.create_account(
                username=user_data["username"],
                initial_balance=user_data.get("initial_balance", 50000.0)
            )
        
        print(f"  ✓ Создано {len(broker.accounts)} счётов")
        
        # Создаём метаданные
        metadata = {
            "tick_count": 0,
            "creation_timestamp": datetime.now().isoformat(),
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "start_config.json"
        }
        
        print("\n✓ Симуляция инициализирована из start_config.json!")
        return market_engine, broker, metadata
    
    # ===== СОХРАНЕНИЕ СОСТОЯНИЯ =====
    
    def save_simulation_state(self, 
                             market_engine: MarketEngine,
                             broker: Broker,
                             metadata: Dict[str, Any] = None,
                             verbose: bool = True) -> None:
        """
        Сохраняет полное состояние симуляции в JSON файлы.
        
        Вызывается в конце каждого дня (tick % 24 == 0).
        
        Args:
            market_engine: MarketEngine для сохранения
            broker: Broker для сохранения
            metadata: Метаданные симуляции (опционально)
            verbose: Выводить ли логи сохранения
        """
        if verbose:
            print("\n" + "=" * 80)
            print(f"STATE MANAGER: СОХРАНЕНИЕ СОСТОЯНИЯ (тик {market_engine.tick_count})")
            print("=" * 80)
        
        # Обновляем метаданные
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "tick_count": market_engine.tick_count,
            "last_save_timestamp": datetime.now().isoformat(),
            "last_save_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        
        try:
            # Сохраняем Market Engine
            if verbose:
                print(f"\nСохраняю Market Engine...")
            market_state = market_engine.to_dict()
            self._save_json(self.config.MARKET_STATE_FILE, market_state)
            if verbose:
                print(f"  ✓ {self.config.MARKET_STATE_FILE}")
            
            # Сохраняем Broker
            if verbose:
                print(f"\nСохраняю Broker...")
            broker_state = broker.to_dict()
            self._save_json(self.config.BROKER_STATE_FILE, broker_state)
            if verbose:
                print(f"  ✓ {self.config.BROKER_STATE_FILE}")
            
            # Сохраняем метаданные
            if verbose:
                print(f"\nСохраняю метаданные...")
            self._save_json(self.config.SIMULATION_META_FILE, metadata)
            if verbose:
                print(f"  ✓ {self.config.SIMULATION_META_FILE}")
            
            if verbose:
                print("\n✓ Состояние успешно сохранено!")
                print("=" * 80)
        
        except (IOError, OSError) as e:
            raise RuntimeError(f"Ошибка при сохранении состояния: {str(e)}")
    
    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Сохраняет данные в JSON файл.
        
        Args:
            file_path: Путь к файлу
            data: Данные для сохранения
        """
        # Создаём директорию, если её нет
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем в JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # ===== УТИЛИТЫ =====
    
    def reset_simulation(self) -> None:
        """
        Удаляет все сохранённые состояния и готовит симуляцию к перезагрузке.
        При следующем запуске будет загружено из start_config.json.
        """
        print("\n⚠️  СБРОС СИМУЛЯЦИИ")
        print("Удаляю все сохранённые состояния...")
        self.config.clear_state_files()
        print("✓ Симуляция готова к перезагрузке")
    
    def get_state_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем состоянии файлов."""
        info = {
            "config_paths": self.config.get_summary(),
            "market_state_file": {
                "path": str(self.config.MARKET_STATE_FILE),
                "exists": self.config.market_state_exists(),
                "size_bytes": self.config.MARKET_STATE_FILE.stat().st_size if self.config.market_state_exists() else 0
            },
            "broker_state_file": {
                "path": str(self.config.BROKER_STATE_FILE),
                "exists": self.config.broker_state_exists(),
                "size_bytes": self.config.BROKER_STATE_FILE.stat().st_size if self.config.broker_state_exists() else 0
            },
            "can_load_from_save": self.config.both_states_exist(),
            "can_load_from_config": self.config.start_config_exists(),
        }
        return info
    
    def print_state_info(self) -> None:
        """Выводит информацию о состоянии файлов."""
        info = self.get_state_info()
        
        print("\n" + "=" * 80)
        print("STATE MANAGER: ИНФОРМАЦИЯ О СОСТОЯНИИ")
        print("=" * 80)
        
        print("\nФайлы:")
        for name, details in info.items():
            if name.startswith(("market", "broker")):
                exists_str = "✓" if details["exists"] else "✗"
                size_kb = details["size_bytes"] / 1024 if details["size_bytes"] > 0 else 0
                print(f"\n{name}:")
                print(f"  {exists_str} Путь: {details['path']}")
                if details["exists"]:
                    print(f"    Размер: {size_kb:.1f} KB")
        
        print(f"\nСтатус загрузки:")
        print(f"  Загружать из сохранений: {'✓ ДА' if info['can_load_from_save'] else '✗ НЕТ'}")
        print(f"  Загружать из конфига: {'✓ ДА' if info['can_load_from_config'] else '✗ НЕТ'}")
        
        print("\n" + "=" * 80)