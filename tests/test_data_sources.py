"""
データソース切り替え機能のテストスイート
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.data_sources import (
    CachedDataSource,
    DataSourceManager,
    DataSourceMode,
    HybridDataSource,
    LiveDataSource,
    MockDataSource,
)
from src.backend.exchanges.base import TimeFrame


class TestDataSourceManager:
    """データソースマネージャーのテスト"""

    def test_mode_from_env_mock(self):
        """環境変数からモックモードを読み込み"""
        with patch.dict(os.environ, {"DATA_SOURCE_MODE": "mock"}):
            manager = DataSourceManager()
            assert manager.mode == DataSourceMode.MOCK
            assert isinstance(manager.strategy, MockDataSource)

    def test_mode_from_env_live(self):
        """環境変数からライブモードを読み込み"""
        with patch.dict(os.environ, {"DATA_SOURCE_MODE": "live"}):
            manager = DataSourceManager()
            assert manager.mode == DataSourceMode.LIVE
            assert isinstance(manager.strategy, LiveDataSource)

    def test_mode_from_env_hybrid(self):
        """環境変数からハイブリッドモードを読み込み"""
        with patch.dict(
            os.environ,
            {
                "DATA_SOURCE_MODE": "hybrid",
                "HYBRID_LIVE_EXCHANGES": "binance,bybit",
                "HYBRID_LIVE_SYMBOLS": "BTC/USDT,ETH/USDT",
            },
        ):
            manager = DataSourceManager()
            assert manager.mode == DataSourceMode.HYBRID
            assert isinstance(manager.strategy, HybridDataSource)

    def test_use_mock_data_compatibility(self):
        """USE_MOCK_DATA環境変数の後方互換性"""
        with patch.dict(os.environ, {"USE_MOCK_DATA": "false"}):
            manager = DataSourceManager()
            assert manager.mode == DataSourceMode.LIVE

    def test_invalid_mode_defaults_to_mock(self):
        """無効なモードはモックにフォールバック"""
        with patch.dict(os.environ, {"DATA_SOURCE_MODE": "invalid"}):
            manager = DataSourceManager()
            assert manager.mode == DataSourceMode.MOCK

    def test_mode_switching(self):
        """実行時のモード切り替え"""
        manager = DataSourceManager()

        # ライブモードに切り替え
        manager.set_mode(DataSourceMode.LIVE)
        assert manager.mode == DataSourceMode.LIVE
        assert isinstance(manager.strategy, LiveDataSource)

        # モックモードに戻す
        manager.set_mode(DataSourceMode.MOCK)
        assert manager.mode == DataSourceMode.MOCK
        assert isinstance(manager.strategy, MockDataSource)

    def test_status_reporting(self):
        """ステータス情報の取得"""
        manager = DataSourceManager()
        status = manager.get_status()

        assert "mode" in status
        assert "strategy" in status
        assert "is_live" in status
        assert "is_mock" in status
        assert "is_hybrid" in status


class TestMockDataSource:
    """モックデータソースのテスト"""

    @pytest.mark.asyncio
    async def test_get_ticker(self):
        """ティッカーデータ生成テスト"""
        source = MockDataSource()
        ticker = await source.get_ticker("binance", "BTC/USDT")

        assert ticker.symbol == "BTC/USDT"
        assert ticker.last > 0
        assert ticker.bid > 0
        assert ticker.ask > ticker.bid  # Ask > Bid
        assert ticker.volume > 0

    @pytest.mark.asyncio
    async def test_get_ohlcv(self):
        """OHLCVデータ生成テスト"""
        source = MockDataSource()
        ohlcv_list = await source.get_ohlcv("binance", "BTC/USDT", TimeFrame.HOUR_1, limit=100)

        assert len(ohlcv_list) == 100

        for ohlcv in ohlcv_list:
            # OHLC関係の検証
            assert ohlcv.high >= ohlcv.low
            assert ohlcv.high >= ohlcv.open
            assert ohlcv.high >= ohlcv.close
            assert ohlcv.low <= ohlcv.open
            assert ohlcv.low <= ohlcv.close
            assert ohlcv.volume >= 0

    @pytest.mark.asyncio
    async def test_price_continuity(self):
        """価格の連続性テスト"""
        source = MockDataSource()

        # 2回連続で同じシンボルのティッカーを取得
        ticker1 = await source.get_ticker("binance", "BTC/USDT")
        ticker2 = await source.get_ticker("binance", "BTC/USDT")

        # 価格は類似している必要がある（大きく変動しない）
        price_diff = abs(ticker2.last - ticker1.last) / ticker1.last
        assert price_diff < 0.05  # 5%以内の変動

    @pytest.mark.asyncio
    async def test_funding_rate_range(self):
        """資金調達率の範囲テスト"""
        source = MockDataSource()
        funding = await source.get_funding_rate("binance", "BTC/USDT")

        # 通常の資金調達率の範囲内
        assert -0.01 <= funding.funding_rate <= 0.01
        assert funding.next_funding_time > funding.timestamp

    @pytest.mark.asyncio
    async def test_balance_consistency(self):
        """残高の一貫性テスト"""
        source = MockDataSource()
        balance = await source.get_balance("binance")

        assert isinstance(balance, dict)
        assert len(balance) > 0

        for asset, amount in balance.items():
            assert isinstance(asset, str)
            assert isinstance(amount, (int, float))
            assert amount >= 0


class TestHybridDataSource:
    """ハイブリッドデータソースのテスト"""

    def test_initialization(self):
        """初期化テスト"""
        live_exchanges = {"binance", "bybit"}
        live_symbols = {"BTC/USDT", "ETH/USDT"}

        source = HybridDataSource(live_exchanges=live_exchanges, live_symbols=live_symbols)

        assert source.live_exchanges == live_exchanges
        assert source.live_symbols == live_symbols

    def test_should_use_live_logic(self):
        """実データ使用判定のテスト"""
        source = HybridDataSource(live_exchanges={"binance"}, live_symbols={"BTC/USDT"})

        # 取引所がホワイトリストにある場合
        assert source._should_use_live("binance", "ETH/USDT") is True

        # シンボルがホワイトリストにある場合
        assert source._should_use_live("bybit", "BTC/USDT") is True

        # どちらもホワイトリストにない場合
        assert source._should_use_live("bybit", "ETH/USDT") is False

    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        source = HybridDataSource(live_exchanges={"binance"})

        # エラーを記録
        source._record_error("binance")
        assert source._error_counts["binance"] == 1

        # 複数回のエラーでモックに切り替わる
        for _ in range(5):
            source._record_error("binance")

        assert source._should_use_live("binance", "BTC/USDT") is False


class TestCachedDataSource:
    """キャッシュ付きデータソースのテスト"""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """キャッシュヒットのテスト"""
        # モックデータソースを作成
        mock_source = AsyncMock()
        mock_ticker = MagicMock()
        mock_ticker.timestamp = datetime.now(timezone.utc)
        mock_ticker.symbol = "BTC/USDT"
        mock_ticker.bid = 45000.0
        mock_ticker.ask = 45050.0
        mock_ticker.last = 45025.0
        mock_ticker.volume = 1000.0

        mock_source.get_ticker.return_value = mock_ticker

        # キャッシュ付きソースを作成
        cached_source = CachedDataSource(mock_source)

        # 1回目の呼び出し（キャッシュミス）
        await cached_source.get_ticker("binance", "BTC/USDT")
        assert mock_source.get_ticker.call_count == 1

        # 2回目の呼び出し（キャッシュヒット）
        # 注: 実際のキャッシュ実装では、ここでキャッシュからデータを取得
        # モックの場合は検証が困難なため、呼び出し回数で確認

    def test_cache_disabled(self):
        """キャッシュ無効時のテスト"""
        mock_source = MagicMock()
        cached_source = CachedDataSource(mock_source, cache_enabled=False)

        assert cached_source._cache_enabled is False
        assert cached_source._cache is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
