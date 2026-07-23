from pathlib import Path


class StateManagerConfig:
    """Централизованная конфигурация путей для State Manager."""
    PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
    CONFIG_DIR = PROJECT_ROOT / "config"
    DATA_DIR = PROJECT_ROOT / "data"
    START_CONFIG_FILE = CONFIG_DIR / "start_config.json"
    MARKET_STATE_FILE = DATA_DIR / "market_state.json"
    BROKER_STATE_FILE = DATA_DIR / "broker_state.json"
    SIMULATION_META_FILE = DATA_DIR / "simulation_meta.json"
    LOG_DIR = PROJECT_ROOT / "logs"
    BACKUP_DIR = DATA_DIR / "backups"
    # ===== МЕТОДЫ КЛАССА =====
    
    @classmethod
    def ensure_directories(cls) -> None:
        """
        Создаёт необходимые директории, если их нет.
        Вызывается автоматически при импорте модуля.
        """
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def market_state_exists(cls) -> bool:
        """Проверяет, существует ли файл сохранённого состояния рынка."""
        return cls.MARKET_STATE_FILE.exists()
    
    @classmethod
    def broker_state_exists(cls) -> bool:
        """Проверяет, существует ли файл сохранённого состояния брокера."""
        return cls.BROKER_STATE_FILE.exists()
    
    @classmethod
    def start_config_exists(cls) -> bool:
        """Проверяет, существует ли файл стартовой конфигурации."""
        return cls.START_CONFIG_FILE.exists()
    
    @classmethod
    def both_states_exist(cls) -> bool:
        """Проверяет, что оба файла состояния существуют."""
        return cls.market_state_exists() and cls.broker_state_exists()
    
    @classmethod
    def clear_state_files(cls) -> None:
        """Удаляет все файлы сохранений (для перезагрузки симуляции с начала)."""
        files_to_remove = [
            cls.MARKET_STATE_FILE,
            cls.BROKER_STATE_FILE,
            cls.SIMULATION_META_FILE
        ]
        
        for file_path in files_to_remove:
            if file_path.exists():
                file_path.unlink()
                print(f"✓ Удалён: {file_path}")
    
    @classmethod
    def print_config(cls) -> None:
        """Выводит текущую конфигурацию путей в консоль."""
        print("=" * 80)
        print("STATE MANAGER CONFIGURATION")
        print("=" * 80)
        print(f"\nПроект: {cls.PROJECT_ROOT}")
        print(f"\nДиректории:")
        print(f"  CONFIG_DIR: {cls.CONFIG_DIR}")
        print(f"  DATA_DIR:   {cls.DATA_DIR}")
        print(f"  LOG_DIR:    {cls.LOG_DIR}")
        print(f"  BACKUP_DIR: {cls.BACKUP_DIR}")
        print(f"\nФайлы конфигурации:")
        print(f"  START_CONFIG:     {cls.START_CONFIG_FILE}")
        print(f"    ✓ Существует" if cls.start_config_exists() else "    ✗ НЕ НАЙДЕН")
        print(f"\nФайлы состояния:")
        print(f"  MARKET_STATE:     {cls.MARKET_STATE_FILE}")
        print(f"    ✓ Существует" if cls.market_state_exists() else "    ✗ НЕ НАЙДЕН")
        print(f"  BROKER_STATE:     {cls.BROKER_STATE_FILE}")
        print(f"    ✓ Существует" if cls.broker_state_exists() else "    ✗ НЕ НАЙДЕН")
        print(f"  SIMULATION_META:  {cls.SIMULATION_META_FILE}")
        print(f"    ✓ Существует" if cls.SIMULATION_META_FILE.exists() else "    ✗ НЕ НАЙДЕН")
        print(f"\nСтатус:")
        if cls.both_states_exist():
            print("  ✓ Полное состояние существует → загружаю сохранённое состояние")
        else:
            print("  ✗ Состояние не найдено → загружаю из start_config.json")
        print("\n" + "=" * 80)
    
    @classmethod
    def get_summary(cls) -> dict:
        """Возвращает словарь с информацией о конфигурации."""
        return {
            "project_root": str(cls.PROJECT_ROOT),
            "config_dir": str(cls.CONFIG_DIR),
            "data_dir": str(cls.DATA_DIR),
            "start_config_file": str(cls.START_CONFIG_FILE),
            "start_config_exists": cls.start_config_exists(),
            "market_state_file": str(cls.MARKET_STATE_FILE),
            "market_state_exists": cls.market_state_exists(),
            "broker_state_file": str(cls.BROKER_STATE_FILE),
            "broker_state_exists": cls.broker_state_exists(),
            "simulation_meta_file": str(cls.SIMULATION_META_FILE),
            "simulation_meta_exists": cls.SIMULATION_META_FILE.exists(),
            "both_states_exist": cls.both_states_exist(),
        }

StateManagerConfig.ensure_directories()

PROJECT_ROOT = StateManagerConfig.PROJECT_ROOT
CONFIG_DIR = StateManagerConfig.CONFIG_DIR
DATA_DIR = StateManagerConfig.DATA_DIR
START_CONFIG_FILE = StateManagerConfig.START_CONFIG_FILE
MARKET_STATE_FILE = StateManagerConfig.MARKET_STATE_FILE
BROKER_STATE_FILE = StateManagerConfig.BROKER_STATE_FILE
SIMULATION_META_FILE = StateManagerConfig.SIMULATION_META_FILE


if __name__ == "__main__":
    StateManagerConfig.print_config()
    print("\nСводка:")
    import json
    print(json.dumps(StateManagerConfig.get_summary(), indent=2, ensure_ascii=False))