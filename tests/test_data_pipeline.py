"""データパイプライン機能の単体テスト"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from backend.data_pipeline.collector import DataCollector
from backend.exchanges.base import OHLCV, TimeFrame
from backend.models.price_data import PriceData, PriceDataSchema


class TestDataCollector:
    """DataCollectorクラスのテスト"""

    @pytest.fixture
    def collector(self):
        """テスト用のDataCollectorインスタンス"""
        collector = DataCollector("binance")

        # モックアダプターを設定
        mock_adapter = AsyncMock()
        collector.adapter = mock_adapter

        return collector

    @pytest.fixture
    def sample_ohlcv_data(self):
        """サンプルOHLCVデータ"""
        return [
            OHLCV(
                timestamp=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
                open=45000.0,
                high=45500.0,
                low=44800.0,
                close=45200.0,
                volume=123.456,
            ),
            OHLCV(
                timestamp=datetime(2025, 1, 19, 13, 0, 0, tzinfo=timezone.utc),
                open=45200.0,
                high=45800.0,
                low=45100.0,
                close=45600.0,
                volume=98.765,
            ),
        ]

    @pytest.mark.asyncio
    async def test_collect_ohlcv_success(self, collector, sample_ohlcv_data):
        """OHLCVデータ収集の成功テスト"""
        # モックの設定
        collector.adapter.fetch_ohlcv.return_value = sample_ohlcv_data

        # テスト実行
        result = await collector.collect_ohlcv(
            symbol="BTC/USDT", timeframe=TimeFrame.HOUR_1, limit=1000
        )

        # 検証
        assert len(result) == 2
        assert result[0].close == 45200.0
        assert result[1].close == 45600.0

        # アダプターが正しく呼ばれたか確認
        collector.adapter.fetch_ohlcv.assert_called_once_with(
            symbol="BTC/USDT", timeframe=TimeFrame.HOUR_1, since=None, limit=1000
        )

    @pytest.mark.asyncio
    async def test_collect_ohlcv_failure(self, collector):
        """OHLCVデータ収集の失敗テスト"""
        # モックでエラーを発生させる
        collector.adapter.fetch_ohlcv.side_effect = Exception("API Error")

        # テスト実行とエラー検証
        with pytest.raises(Exception, match="API Error"):
            await collector.collect_ohlcv(symbol="BTC/USDT", timeframe=TimeFrame.HOUR_1)

    @pytest.mark.asyncio
    async def test_collect_ohlcv_without_adapter(self):
        """アダプター未初期化時のエラーテスト"""
        collector = DataCollector("binance")
        # adapterを初期化しない

        with pytest.raises(RuntimeError, match="DataCollector not initialized"):
            await collector.collect_ohlcv("BTC/USDT", TimeFrame.HOUR_1)

    @pytest.mark.asyncio
    @patch("backend.data_pipeline.collector.get_supabase_client")
    async def test_save_ohlcv_to_supabase_success(
        self, mock_supabase, collector, sample_ohlcv_data
    ):
        """Supabaseへのデータ保存成功テスト"""
        # Supabaseクライアントのモック
        mock_client = Mock()
        mock_table = Mock()
        mock_upsert = Mock()

        mock_supabase.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = Mock()

        # テスト実行
        await collector._save_ohlcv_to_supabase(
            symbol="BTC/USDT", timeframe=TimeFrame.HOUR_1, ohlcv_data=sample_ohlcv_data
        )

        # 検証
        mock_client.table.assert_called_once_with("price_data")
        mock_table.upsert.assert_called_once()

        # upsertに渡されたデータを確認
        call_args = mock_table.upsert.call_args[0]
        records = call_args[0]

        assert len(records) == 2
        assert records[0]["symbol"] == "BTCUSDT"  # / が削除されている
        assert records[0]["exchange"] == "binance"
        assert records[0]["timeframe"] == "1h"
        assert records[0]["close_price"] == 45200.0

    @pytest.mark.asyncio
    @patch("backend.data_pipeline.collector.get_supabase_client")
    async def test_save_ohlcv_to_supabase_failure(
        self, mock_supabase, collector, sample_ohlcv_data
    ):
        """Supabaseへのデータ保存失敗テスト"""
        # Supabaseクライアントでエラーを発生させる
        mock_supabase.side_effect = Exception("Supabase connection error")

        # テスト実行（エラーが発生しても例外は投げられない設計）
        await collector._save_ohlcv_to_supabase(
            symbol="BTC/USDT", timeframe=TimeFrame.HOUR_1, ohlcv_data=sample_ohlcv_data
        )

        # エラーログが出力されるが、メソッド自体は正常終了する


class TestPriceDataModel:
    """PriceDataモデルのテスト"""

    def test_price_data_schema_creation(self):
        """PriceDataSchemaの作成テスト"""
        schema = PriceDataSchema(
            exchange="binance",
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
            open_price=Decimal("45000.00"),
            high_price=Decimal("45500.00"),
            low_price=Decimal("44800.00"),
            close_price=Decimal("45200.00"),
            volume=Decimal("123.456"),
        )

        assert schema.exchange == "binance"
        assert schema.symbol == "BTCUSDT"
        assert schema.close_price == Decimal("45200.00")

    def test_price_data_from_ohlcv(self):
        """OHLCVからPriceDataインスタンス作成テスト"""
        ohlcv = OHLCV(
            timestamp=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
            open=45000.0,
            high=45500.0,
            low=44800.0,
            close=45200.0,
            volume=123.456,
        )

        price_data = PriceData.from_ohlcv(
            exchange="binance", symbol="BTCUSDT", timeframe="1h", ohlcv_data=ohlcv
        )

        assert price_data.exchange == "binance"
        assert price_data.symbol == "BTCUSDT"
        assert price_data.timeframe == "1h"
        assert price_data.close_price == Decimal("45200.0")
        assert price_data.volume == Decimal("123.456")

    def test_price_data_to_dict(self):
        """PriceDataの辞書変換テスト"""
        price_data = PriceData(
            exchange="binance",
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
            open_price=Decimal("45000.00"),
            high_price=Decimal("45500.00"),
            low_price=Decimal("44800.00"),
            close_price=Decimal("45200.00"),
            volume=Decimal("123.456"),
        )

        result = price_data.to_dict()

        assert result["exchange"] == "binance"
        assert result["symbol"] == "BTCUSDT"
        assert result["close_price"] == 45200.0
        assert result["volume"] == 123.456
        assert "timestamp" in result


@pytest.mark.asyncio
async def test_integration_data_flow():
    """統合テスト：データフロー全体のテスト"""
    collector = DataCollector("binance")

    # モックアダプターを設定
    mock_adapter = AsyncMock()
    sample_data = [
        OHLCV(
            timestamp=datetime(2025, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
            open=45000.0,
            high=45500.0,
            low=44800.0,
            close=45200.0,
            volume=123.456,
        )
    ]
    mock_adapter.fetch_ohlcv.return_value = sample_data
    collector.adapter = mock_adapter

    # Supabaseクライアントをモック
    with patch("backend.data_pipeline.collector.get_supabase_client") as mock_supabase:
        mock_client = Mock()
        mock_table = Mock()
        mock_upsert = Mock()

        mock_supabase.return_value = mock_client
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = Mock()

        # テスト実行
        result = await collector.collect_ohlcv("BTC/USDT", TimeFrame.HOUR_1)

        # データ収集確認
        assert len(result) == 1
        assert result[0].close == 45200.0

        # Supabase保存のテスト（実際の保存は別メソッドで実行されるため、手動実行）
        await collector._save_ohlcv_to_supabase("BTC/USDT", TimeFrame.HOUR_1, result)

        # Supabaseが呼ばれたか確認
        mock_client.table.assert_called_with("price_data")
        mock_table.upsert.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
