import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import asdict
import pandas as pd
from pathlib import Path

from backend.exchanges.factory import ExchangeFactory
from backend.exchanges.base import AbstractExchangeAdapter, TimeFrame, OHLCV
from backend.core.database import get_db
from backend.core.supabase_db import get_supabase_client

logger = logging.getLogger(__name__)


class DataCollector:
    """データ収集クラス"""

    def __init__(self, exchange_name: str = "binance"):
        self.exchange_name = exchange_name
        self.adapter: Optional[AbstractExchangeAdapter] = None
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        # Parquet ファイルの保存先
        self.parquet_dir = self.data_dir / "parquet"
        self.parquet_dir.mkdir(exist_ok=True)

        # 収集対象のシンボル
        self.symbols = [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "ADA/USDT",
            "SOL/USDT",
            "XRP/USDT",
            "DOT/USDT",
            "AVAX/USDT",
        ]

        # 収集対象の時間枠
        self.timeframes = [
            TimeFrame.MINUTE_15,
            TimeFrame.HOUR_1,
            TimeFrame.HOUR_4,
            TimeFrame.DAY_1,
        ]

    async def initialize(self):
        """初期化"""
        try:
            self.adapter = ExchangeFactory.create_adapter(self.exchange_name)
            logger.info(f"DataCollector initialized with {self.exchange_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DataCollector: {e}")
            raise

    async def collect_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """OHLCV データを収集"""
        if not self.adapter:
            raise RuntimeError("DataCollector not initialized")

        try:
            ohlcv_data = await self.adapter.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, since=since, limit=limit
            )

            logger.info(
                f"Collected {len(ohlcv_data)} OHLCV records for {symbol} {timeframe.value}"
            )
            return ohlcv_data

        except Exception as e:
            logger.error(f"Error collecting OHLCV for {symbol}: {e}")
            raise

    async def collect_funding_rates(self, symbols: List[str]) -> Dict[str, Any]:
        """資金調達率を収集"""
        if not self.adapter:
            raise RuntimeError("DataCollector not initialized")

        funding_rates = {}

        for symbol in symbols:
            try:
                funding_rate = await self.adapter.fetch_funding_rate(symbol)
                funding_rates[symbol] = asdict(funding_rate)

                # データベースに保存
                await self._save_funding_rate_to_db(funding_rate)

            except Exception as e:
                logger.error(f"Error collecting funding rate for {symbol}: {e}")
                funding_rates[symbol] = {"error": str(e)}

        return funding_rates

    async def collect_open_interest(self, symbols: List[str]) -> Dict[str, Any]:
        """建玉データを収集"""
        if not self.adapter:
            raise RuntimeError("DataCollector not initialized")

        open_interests = {}

        for symbol in symbols:
            try:
                open_interest = await self.adapter.fetch_open_interest(symbol)
                open_interests[symbol] = asdict(open_interest)

                # データベースに保存
                await self._save_open_interest_to_db(open_interest)

            except Exception as e:
                logger.error(f"Error collecting open interest for {symbol}: {e}")
                open_interests[symbol] = {"error": str(e)}

        return open_interests

    async def collect_batch_ohlcv(
        self,
        symbols: List[str],
        timeframes: List[TimeFrame],
        since: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, List[OHLCV]]]:
        """複数シンボル・時間枠のOHLCVデータを並列収集"""
        results: Dict[str, Dict[str, List[OHLCV]]] = {}

        # 並列実行用のタスクを作成
        tasks = []
        for symbol in symbols:
            results[symbol] = {}
            for timeframe in timeframes:
                task = asyncio.create_task(self.collect_ohlcv(symbol, timeframe, since))
                tasks.append((symbol, timeframe, task))

        # 並列実行
        for symbol, timeframe, task in tasks:
            try:
                ohlcv_data = await task
                results[symbol][timeframe.value] = ohlcv_data

                # Parquet ファイルに保存
                await self._save_ohlcv_to_parquet(symbol, timeframe, ohlcv_data)

                # Supabaseに保存
                await self._save_ohlcv_to_supabase(symbol, timeframe, ohlcv_data)

            except Exception as e:
                logger.error(
                    f"Error in batch collection for {symbol} {timeframe.value}: {e}"
                )
                results[symbol][timeframe.value] = []

        return results

    async def _save_ohlcv_to_parquet(
        self, symbol: str, timeframe: TimeFrame, ohlcv_data: List[OHLCV]
    ):
        """OHLCV データを Parquet ファイルに保存"""
        if not ohlcv_data:
            return

        # DataFrame に変換
        df = pd.DataFrame([asdict(ohlcv) for ohlcv in ohlcv_data])
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # ファイルパスを作成
        normalized_symbol = symbol.replace("/", "_")
        filename = f"{normalized_symbol}_{timeframe.value}.parquet"
        filepath = self.parquet_dir / filename

        # 既存のファイルがあれば読み込んで結合
        if filepath.exists():
            existing_df = pd.read_parquet(filepath)
            df = pd.concat([existing_df, df]).drop_duplicates(subset=["timestamp"])
            df = df.sort_values("timestamp")

        # Parquet ファイルに保存
        df.to_parquet(filepath, index=False)
        logger.info(f"Saved {len(df)} records to {filepath}")

    async def _save_ohlcv_to_supabase(
        self, symbol: str, timeframe: TimeFrame, ohlcv_data: List[OHLCV]
    ):
        """OHLCV データを Supabase に保存"""
        if not ohlcv_data:
            return

        try:
            supabase = get_supabase_client()

            # データを変換
            records = []
            for ohlcv in ohlcv_data:
                record = {
                    "exchange": self.exchange_name,
                    "symbol": symbol.replace("/", ""),  # BTC/USDT -> BTCUSDT
                    "timeframe": timeframe.value,
                    "timestamp": ohlcv.timestamp.isoformat(),
                    "open_price": float(ohlcv.open),
                    "high_price": float(ohlcv.high),
                    "low_price": float(ohlcv.low),
                    "close_price": float(ohlcv.close),
                    "volume": float(ohlcv.volume),
                }
                records.append(record)

            # バッチサイズを制限してバッチ挿入（upsert使用で重複回避）
            batch_size = 1000  # Supabaseの推奨バッチサイズ
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                (
                    supabase.table("price_data")
                    .upsert(batch, on_conflict="exchange,symbol,timeframe,timestamp")
                    .execute()
                )

                logger.info(
                    f"Saved batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1} "
                    f"({len(batch)} records) to Supabase for {symbol} {timeframe.value}"
                )

        except Exception as e:
            logger.error(f"Error saving OHLCV data to Supabase: {e}")
            # Supabaseエラーでもメイン処理は継続

    async def _save_funding_rate_to_db(self, funding_rate):
        """資金調達率をデータベースに保存"""
        try:
            # 簡易的な保存（実際はテーブル定義が必要）
            query = """
            INSERT OR REPLACE INTO funding_rates
            (timestamp, symbol, funding_rate, next_funding_time)
            VALUES (?, ?, ?, ?)
            """

            # テーブルが存在しない場合は作成
            create_table_query = """
            CREATE TABLE IF NOT EXISTS funding_rates (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                funding_rate DECIMAL(10, 6),
                next_funding_time TIMESTAMP,
                PRIMARY KEY (timestamp, symbol)
            )
            """

            db = get_db()
            db.execute(create_table_query)
            db.execute(
                query,
                [
                    funding_rate.timestamp,
                    funding_rate.symbol,
                    funding_rate.funding_rate,
                    funding_rate.next_funding_time,
                ],
            )

        except Exception as e:
            logger.error(f"Error saving funding rate to DB: {e}")

    async def _save_open_interest_to_db(self, open_interest):
        """建玉データをデータベースに保存"""
        try:
            # 簡易的な保存（実際はテーブル定義が必要）
            query = """
            INSERT OR REPLACE INTO open_interests
            (timestamp, symbol, open_interest, open_interest_value)
            VALUES (?, ?, ?, ?)
            """

            # テーブルが存在しない場合は作成
            create_table_query = """
            CREATE TABLE IF NOT EXISTS open_interests (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                open_interest DECIMAL(20, 8),
                open_interest_value DECIMAL(20, 8),
                PRIMARY KEY (timestamp, symbol)
            )
            """

            db = get_db()
            db.execute(create_table_query)
            db.execute(
                query,
                [
                    open_interest.timestamp,
                    open_interest.symbol,
                    open_interest.open_interest,
                    open_interest.open_interest_value,
                ],
            )

        except Exception as e:
            logger.error(f"Error saving open interest to DB: {e}")

    async def run_scheduled_collection(self):
        """定期収集を実行"""
        logger.info("Starting scheduled data collection...")

        try:
            # 過去1日分のデータを収集
            since = datetime.now(timezone.utc) - timedelta(days=1)

            # OHLCV データを並列収集
            ohlcv_results = await self.collect_batch_ohlcv(
                symbols=self.symbols, timeframes=self.timeframes, since=since
            )

            # 資金調達率を収集
            funding_results = await self.collect_funding_rates(self.symbols)

            # 建玉データを収集
            oi_results = await self.collect_open_interest(self.symbols)

            logger.info("Scheduled data collection completed successfully")

            return {
                "ohlcv": ohlcv_results,
                "funding_rates": funding_results,
                "open_interests": oi_results,
            }

        except Exception as e:
            logger.error(f"Error in scheduled collection: {e}")
            raise

    async def close(self):
        """リソースをクリーンアップ"""
        if self.adapter:
            await self.adapter.close()
            logger.info("DataCollector closed")


class DataCollectorManager:
    """データ収集管理クラス"""

    def __init__(self):
        self.collectors: Dict[str, DataCollector] = {}
        self.is_running = False
        self.collection_interval = 300  # 5分間隔

    async def add_collector(self, exchange_name: str):
        """データ収集器を追加"""
        if exchange_name not in self.collectors:
            collector = DataCollector(exchange_name)
            await collector.initialize()
            self.collectors[exchange_name] = collector
            logger.info(f"Added data collector for {exchange_name}")

    async def start_collection(self):
        """データ収集を開始"""
        if self.is_running:
            logger.warning("Data collection is already running")
            return

        self.is_running = True
        logger.info("Starting data collection manager...")

        while self.is_running:
            try:
                # 各取引所のデータを収集
                collection_tasks = []
                for exchange_name, collector in self.collectors.items():
                    task = asyncio.create_task(collector.run_scheduled_collection())
                    collection_tasks.append(task)

                # 並列実行
                await asyncio.gather(*collection_tasks, return_exceptions=True)

                # 指定間隔で待機
                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機

    async def stop_collection(self):
        """データ収集を停止"""
        self.is_running = False

        # 全てのコレクターを閉じる
        for collector in self.collectors.values():
            await collector.close()

        logger.info("Data collection manager stopped")


# グローバルインスタンス
data_collector_manager = DataCollectorManager()
