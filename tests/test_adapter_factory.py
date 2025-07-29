"""
AdapterFactory Paper Trading切り替えテスト
セキュリティを重視したファクトリークラステスト
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from src.backend.exchanges.binance import BinanceAdapter
from src.backend.exchanges.factory import ExchangeFactory, create_paper_trading_adapter
from src.backend.exchanges.paper_trading_adapter import PaperTradingAdapter


class TestExchangeFactoryPaperTrading:
    """ExchangeFactoryのPaper Trading対応テスト"""

    def test_paper_trading_mode_validation(self):
        """Paper Tradingモードの検証テスト"""
        factory = ExchangeFactory()
        # user_id無しでPaper Tradingを試行（自動的にUUIDが生成される）
        adapter = factory.create_adapter(exchange_name="binance", trading_mode="paper")
        # PaperTradingAdapterが作成されることを確認
        assert isinstance(adapter, PaperTradingAdapter)

    def test_invalid_trading_mode(self):
        """不正な取引モードのテスト"""
        factory = ExchangeFactory()
        with pytest.raises(ValueError, match="Invalid trading mode"):
            factory.create_adapter(exchange_name="binance", trading_mode="invalid_mode")

    def test_paper_trading_adapter_creation(self):
        """Paper Tradingアダプター作成テスト"""
        test_user_id = str(uuid4())
        factory = ExchangeFactory()

        # Paper Tradingアダプター作成
        adapter = factory.create_adapter(
            exchange_name="binance",
            trading_mode="paper",
            user_id=test_user_id,
            paper_config={"database_url": "sqlite:///:memory:", "default_setting": "beginner"},
        )

        # Paper Tradingアダプターが作成されることを確認
        assert isinstance(adapter, PaperTradingAdapter)
        assert adapter.user_id == test_user_id
        assert adapter.exchange_name == "paper_trading"

    @patch("src.backend.exchanges.factory.config.settings")
    @patch("src.backend.exchanges.factory.settings")
    def test_live_trading_adapter_creation(self, mock_main_settings, mock_config_settings):
        """Live Tradingアダプター作成テスト"""
        # モック設定
        mock_config_settings.BINANCE_API_KEY = "test_api_key"
        mock_config_settings.BINANCE_SECRET = "test_secret"
        mock_main_settings.ENVIRONMENT = "production"  # 本番環境に設定
        factory = ExchangeFactory()

        # Live Tradingアダプター作成
        adapter = factory.create_adapter(exchange_name="binance", trading_mode="live", sandbox=True)

        # Binanceアダプターが作成されることを確認
        assert isinstance(adapter, BinanceAdapter)
        assert adapter.exchange.sandbox is True

    def test_unsupported_exchange_for_paper_trading(self):
        """サポートされていない取引所でのPaper Tradingテスト"""
        test_user_id = str(uuid4())
        factory = ExchangeFactory()

        # 存在しない取引所名でPaper Trading（例外が発生する）
        with pytest.raises(ValueError, match="Unsupported exchange: nonexistent_exchange"):
            factory.create_adapter(
                exchange_name="nonexistent_exchange",
                trading_mode="paper",
                user_id=test_user_id,
                paper_config={
                    "database_url": "sqlite:///:memory:",
                },
            )

    def test_get_supported_exchanges(self):
        """サポートされている取引所一覧テスト"""
        factory = ExchangeFactory()
        # Paper Trading無し
        exchanges = factory.get_supported_exchanges(include_paper_trading=False)
        assert "paper_trading" not in exchanges
        assert "binance" in exchanges
        assert "bybit" in exchanges

        # Paper Trading含む
        exchanges_with_paper = factory.get_supported_exchanges(include_paper_trading=True)
        assert "paper_trading" in exchanges_with_paper
        assert "binance" in exchanges_with_paper

    def test_paper_trading_config_security(self):
        """Paper Trading設定のセキュリティテスト"""
        test_user_id = str(uuid4())
        factory = ExchangeFactory()

        # 安全でない設定を含むconfig
        unsafe_config = {
            "database_url": "sqlite:///:memory:",
            "real_api_key": "SHOULD_NOT_BE_USED",  # 実際のAPIキーは無視される
            "real_secret": "SHOULD_NOT_BE_USED",
        }

        adapter = factory.create_adapter(
            exchange_name="binance", trading_mode="paper", user_id=test_user_id, paper_config=unsafe_config
        )

        # Paper Tradingアダプターが作成され、実際のAPIキーは使用されない
        assert isinstance(adapter, PaperTradingAdapter)
        # 内部のreal_adapterも安全なモック設定
        assert adapter.real_adapter.exchange.apiKey == "paper_trading_mock"
        assert adapter.real_adapter.exchange.secret == "paper_trading_mock"


class TestPaperTradingHelperFunction:
    """Paper Trading ヘルパー関数テスト"""

    def test_create_paper_trading_adapter_helper(self):
        """create_paper_trading_adapter ヘルパー関数テスト"""
        test_user_id = str(uuid4())

        adapter = create_paper_trading_adapter(
            user_id=test_user_id,
            real_exchange="binance",
            paper_config={"database_url": "sqlite:///:memory:", "default_setting": "beginner"},
        )

        assert isinstance(adapter, PaperTradingAdapter)
        assert adapter.user_id == test_user_id

    def test_create_paper_trading_adapter_default_config(self):
        """デフォルト設定でのPaper Tradingアダプター作成テスト"""
        test_user_id = str(uuid4())

        adapter = create_paper_trading_adapter(user_id=test_user_id)

        assert isinstance(adapter, PaperTradingAdapter)
        assert adapter.user_id == test_user_id
        # デフォルト設定が適用される


class TestExchangeFactoryEdgeCases:
    """ExchangeFactory エッジケーステスト"""

    def test_case_insensitive_exchange_names(self):
        """大文字小文字を区別しない取引所名テスト"""
        test_user_id = str(uuid4())
        factory = ExchangeFactory()

        # 大文字での指定
        adapter1 = factory.create_adapter(
            exchange_name="BINANCE",
            trading_mode="paper",
            user_id=test_user_id,
            paper_config={"database_url": "sqlite:///:memory:"},
        )

        # 小文字での指定
        adapter2 = factory.create_adapter(
            exchange_name="binance",
            trading_mode="paper",
            user_id=test_user_id,
            paper_config={"database_url": "sqlite:///:memory:"},
        )

        # 両方ともPaper Tradingアダプターが作成される
        assert isinstance(adapter1, PaperTradingAdapter)
        assert isinstance(adapter2, PaperTradingAdapter)

    def test_case_insensitive_trading_modes(self):
        """大文字小文字を区別しない取引モードテスト"""
        test_user_id = str(uuid4())
        factory = ExchangeFactory()

        # 大文字でのPaper Trading指定
        adapter = factory.create_adapter(
            exchange_name="binance",
            trading_mode="PAPER",
            user_id=test_user_id,
            paper_config={"database_url": "sqlite:///:memory:"},
        )

        assert isinstance(adapter, PaperTradingAdapter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
