import logging
from pathlib import Path
from typing import Any, Dict, List, Type

import yaml

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyLoader:
    """戦略ローダークラス"""

    def __init__(self, config_dir: str = "config/strategies"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 登録済み戦略クラス
        self.strategy_classes: Dict[str, Type[BaseStrategy]] = {}

        # 設定ファイルから読み込んだ戦略設定
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}

        logger.info(f"StrategyLoader initialized with config directory: {config_dir}")

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]):
        """戦略クラスを登録"""
        self.strategy_classes[name] = strategy_class
        logger.info(f"Strategy class registered: {name}")

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """YAML設定ファイルを読み込み"""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Strategy config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            logger.info(f"Strategy config loaded: {config_file}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config {config_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config {config_file}: {e}")
            raise

    def load_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """すべての戦略設定を読み込み"""
        configs = {}

        for config_file in self.config_dir.glob("*.yml"):
            try:
                config = self.load_config(config_file.name)
                strategy_name = config.get("name", config_file.stem)
                configs[strategy_name] = config

            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")
                continue

        self.strategy_configs = configs
        logger.info(f"Loaded {len(configs)} strategy configurations")
        return configs

    def create_strategy(self, config: Dict[str, Any]) -> BaseStrategy:
        """設定から戦略インスタンスを作成"""

        strategy_name = config.get("name")
        if not strategy_name:
            raise ValueError("Strategy name is required in config")

        strategy_type = config.get("type", strategy_name)

        # 戦略クラスを取得
        if strategy_type not in self.strategy_classes:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        strategy_class = self.strategy_classes[strategy_type]

        # パラメータを抽出
        parameters = config.get("parameters", {})
        symbol = config.get("symbol", "BTCUSDT")
        timeframe = config.get("timeframe", "1h")

        # 戦略インスタンスを作成
        strategy = strategy_class(
            name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            parameters=parameters,
        )

        # 追加の設定を適用
        if "enabled" in config:
            strategy.enabled = config["enabled"]

        if "description" in config:
            strategy.description = config["description"]

        logger.info(f"Strategy created: {strategy_name} ({strategy_type})")
        return strategy

    def create_strategy_from_file(self, config_file: str) -> BaseStrategy:
        """設定ファイルから戦略を作成"""
        config = self.load_config(config_file)
        return self.create_strategy(config)

    def create_all_strategies(self) -> Dict[str, BaseStrategy]:
        """すべての戦略を作成"""
        strategies = {}

        for strategy_name, config in self.strategy_configs.items():
            try:
                if config.get("enabled", True):
                    strategy = self.create_strategy(config)
                    strategies[strategy_name] = strategy
                else:
                    logger.info(f"Strategy {strategy_name} is disabled, skipping")

            except Exception as e:
                logger.error(f"Failed to create strategy {strategy_name}: {e}")
                continue

        logger.info(f"Created {len(strategies)} strategies")
        return strategies

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """設定の妥当性を検証"""

        # 必須フィールドの確認
        required_fields = ["name"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field: {field}")
                return False

        # 戦略タイプの確認
        strategy_type = config.get("type", config["name"])
        if strategy_type not in self.strategy_classes:
            logger.error(f"Unknown strategy type: {strategy_type}")
            return False

        # パラメータの確認
        parameters = config.get("parameters", {})
        if not isinstance(parameters, dict):
            logger.error("Parameters must be a dictionary")
            return False

        # 時間枠の確認
        timeframe = config.get("timeframe", "1h")
        valid_timeframes = [
            "1m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "8h",
            "1d",
            "1w",
        ]
        if timeframe not in valid_timeframes:
            logger.error(f"Invalid timeframe: {timeframe}")
            return False

        return True

    def get_strategy_list(self) -> List[Dict[str, Any]]:
        """戦略一覧を取得"""
        strategies = []

        for name, config in self.strategy_configs.items():
            strategies.append(
                {
                    "name": name,
                    "type": config.get("type", name),
                    "symbol": config.get("symbol", "BTCUSDT"),
                    "timeframe": config.get("timeframe", "1h"),
                    "enabled": config.get("enabled", True),
                    "description": config.get("description", ""),
                }
            )

        return strategies

    def save_config(self, strategy_name: str, config: Dict[str, Any]):
        """戦略設定を保存"""
        config_file = self.config_dir / f"{strategy_name}.yml"

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Strategy config saved: {config_file}")

        except Exception as e:
            logger.error(f"Failed to save config {config_file}: {e}")
            raise

    def delete_config(self, strategy_name: str):
        """戦略設定を削除"""
        config_file = self.config_dir / f"{strategy_name}.yml"

        if config_file.exists():
            config_file.unlink()
            logger.info(f"Strategy config deleted: {config_file}")
        else:
            logger.warning(f"Config file not found: {config_file}")

    def reload_configs(self):
        """設定を再読み込み"""
        logger.info("Reloading strategy configurations...")
        self.strategy_configs = {}
        self.load_all_configs()


class StrategyFactory:
    """戦略ファクトリークラス"""

    def __init__(self):
        self.loader = StrategyLoader()
        self._register_builtin_strategies()

    def _register_builtin_strategies(self):
        """組み込み戦略を登録"""
        try:
            # EMA戦略を登録
            from .implementations.ema_strategy import EMAStrategy

            self.loader.register_strategy("ema", EMAStrategy)

            # RSI戦略を登録
            from .implementations.rsi_strategy import RSIStrategy

            self.loader.register_strategy("rsi", RSIStrategy)

            # MACD戦略を登録
            from .implementations.macd_strategy import MACDStrategy

            self.loader.register_strategy("macd", MACDStrategy)

            # ボリンジャーバンド戦略を登録
            from .implementations.bollinger_strategy import BollingerStrategy

            self.loader.register_strategy("bollinger", BollingerStrategy)

            logger.info("Built-in strategies registered")

        except ImportError as e:
            logger.warning(f"Some built-in strategies could not be imported: {e}")

    def create_strategy(self, name: str, **kwargs) -> BaseStrategy:
        """戦略を作成"""

        # 設定ファイルから作成を試行
        try:
            config_file = f"{name}.yml"
            strategy = self.loader.create_strategy_from_file(config_file)

            # 追加パラメータがあれば適用
            if kwargs:
                for key, value in kwargs.items():
                    if hasattr(strategy, key):
                        setattr(strategy, key, value)
                    else:
                        strategy.parameters[key] = value

            return strategy

        except FileNotFoundError:
            logger.warning(f"Config file not found for strategy: {name}")

        # デフォルト設定で作成
        if name in self.loader.strategy_classes:
            strategy_class = self.loader.strategy_classes[name]
            return strategy_class(name=name, **kwargs)

        raise ValueError(f"Unknown strategy: {name}")

    def get_available_strategies(self) -> List[str]:
        """利用可能な戦略一覧を取得"""
        return list(self.loader.strategy_classes.keys())

    def get_strategy_info(self, name: str) -> Dict[str, Any]:
        """戦略情報を取得"""
        if name in self.loader.strategy_configs:
            return self.loader.strategy_configs[name]

        if name in self.loader.strategy_classes:
            return {
                "name": name,
                "type": name,
                "description": f"Built-in {name} strategy",
                "enabled": True,
            }

        raise ValueError(f"Unknown strategy: {name}")


# グローバルファクトリーインスタンス
strategy_factory = StrategyFactory()
