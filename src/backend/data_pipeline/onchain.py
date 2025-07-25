import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from src.backend.core.config import settings
from src.backend.core.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class WhaleFlowData:
    """ホエールフローデータ"""

    timestamp: datetime
    symbol: str
    inflow: float
    outflow: float
    net_flow: float


@dataclass
class NVTData:
    """NVT（Network Value to Transactions）データ"""

    timestamp: datetime
    symbol: str
    nvt_ratio: float
    nvt_signal: float


@dataclass
class MinerOutflowData:
    """マイナーアウトフローデータ"""

    timestamp: datetime
    symbol: str
    outflow_amount: float
    outflow_value_usd: float


@dataclass
class NUPLData:
    """NUPL（Net Unrealized Profit/Loss）データ"""

    timestamp: datetime
    symbol: str
    nupl_value: float
    supply_in_profit: float


class GlassnodeClient:
    """Glassnodeクライアント"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.glassnode.com/v1/metrics"
        self.session = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """セッションを閉じる"""
        await self.session.aclose()

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """APIリクエストを実行"""
        params["api_key"] = self.api_key

        try:
            response = await self.session.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise

    async def get_whale_flow(
        self,
        symbol: str = "BTC",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WhaleFlowData]:
        """ホエールフローデータを取得"""
        params = {"a": symbol, "f": "JSON", "i": "1h"}

        if since:
            params["s"] = str(int(since.timestamp()))
        if until:
            params["u"] = str(int(until.timestamp()))

        try:
            # 実際のエンドポイントは複数の指標から合成
            inflow_data = await self._make_request("addresses/new_non_zero_count", params)

            outflow_data = await self._make_request("addresses/active_count", params)

            whale_flows = []
            for i, inflow in enumerate(inflow_data):
                if i < len(outflow_data):
                    outflow = outflow_data[i]

                    # 簡易的な計算（実際はより複雑）
                    inflow_val = float(inflow["v"]) if inflow["v"] is not None else 0
                    outflow_val = float(outflow["v"]) if outflow["v"] is not None else 0

                    whale_flow = WhaleFlowData(
                        timestamp=datetime.fromtimestamp(inflow["t"], tz=timezone.utc),
                        symbol=symbol,
                        inflow=inflow_val,
                        outflow=outflow_val,
                        net_flow=inflow_val - outflow_val,
                    )
                    whale_flows.append(whale_flow)

            logger.info(f"Fetched {len(whale_flows)} whale flow records for {symbol}")
            return whale_flows

        except Exception as e:
            logger.error(f"Error fetching whale flow for {symbol}: {e}")
            raise

    async def get_nvt_data(
        self,
        symbol: str = "BTC",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[NVTData]:
        """NVTデータを取得"""
        params = {"a": symbol, "f": "JSON", "i": "24h"}

        if since:
            params["s"] = str(int(since.timestamp()))
        if until:
            params["u"] = str(int(until.timestamp()))

        try:
            nvt_data = await self._make_request("indicators/nvt", params)

            nvt_signal_data = await self._make_request("indicators/nvts", params)

            nvt_list = []
            for i, nvt in enumerate(nvt_data):
                nvt_signal = nvt_signal_data[i] if i < len(nvt_signal_data) else None

                nvt_obj = NVTData(
                    timestamp=datetime.fromtimestamp(nvt["t"], tz=timezone.utc),
                    symbol=symbol,
                    nvt_ratio=float(nvt["v"]) if nvt["v"] is not None else 0,
                    nvt_signal=float(nvt_signal["v"]) if nvt_signal and nvt_signal["v"] else 0,
                )
                nvt_list.append(nvt_obj)

            logger.info(f"Fetched {len(nvt_list)} NVT records for {symbol}")
            return nvt_list

        except Exception as e:
            logger.error(f"Error fetching NVT data for {symbol}: {e}")
            raise

    async def get_nupl_data(
        self,
        symbol: str = "BTC",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[NUPLData]:
        """NUPLデータを取得"""
        params = {"a": symbol, "f": "JSON", "i": "24h"}

        if since:
            params["s"] = str(int(since.timestamp()))
        if until:
            params["u"] = str(int(until.timestamp()))

        try:
            nupl_data = await self._make_request("indicators/nupl", params)

            supply_profit_data = await self._make_request("indicators/supply_profit_relative", params)

            nupl_list = []
            for i, nupl in enumerate(nupl_data):
                supply_profit = supply_profit_data[i] if i < len(supply_profit_data) else None

                nupl_obj = NUPLData(
                    timestamp=datetime.fromtimestamp(nupl["t"], tz=timezone.utc),
                    symbol=symbol,
                    nupl_value=float(nupl["v"]) if nupl["v"] is not None else 0,
                    supply_in_profit=float(supply_profit["v"]) if supply_profit and supply_profit["v"] else 0,
                )
                nupl_list.append(nupl_obj)

            logger.info(f"Fetched {len(nupl_list)} NUPL records for {symbol}")
            return nupl_list

        except Exception as e:
            logger.error(f"Error fetching NUPL data for {symbol}: {e}")
            raise


class CryptoQuantClient:
    """CryptoQuantクライアント"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cryptoquant.com/v1"
        self.session = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """セッションを閉じる"""
        await self.session.aclose()

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """APIリクエストを実行"""
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = await self.session.get(f"{self.base_url}/{endpoint}", params=params, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise

    async def get_miner_outflow(
        self,
        symbol: str = "BTC",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[MinerOutflowData]:
        """マイナーアウトフローデータを取得"""
        params = {"symbol": symbol, "window": "1h"}

        if since:
            params["from"] = since.strftime("%Y-%m-%d")
        if until:
            params["to"] = until.strftime("%Y-%m-%d")

        try:
            # 実際のエンドポイントは異なる可能性があります
            data = await self._make_request("market-data/miner-outflow", params)

            outflow_list = []
            for item in data.get("data", []):
                outflow = MinerOutflowData(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    symbol=symbol,
                    outflow_amount=float(item.get("outflow_amount", 0)),
                    outflow_value_usd=float(item.get("outflow_value_usd", 0)),
                )
                outflow_list.append(outflow)

            logger.info(f"Fetched {len(outflow_list)} miner outflow records for {symbol}")
            return outflow_list

        except Exception as e:
            logger.error(f"Error fetching miner outflow for {symbol}: {e}")
            raise


class OnChainDataCollector:
    """オンチェーンデータ収集クラス"""

    def __init__(self):
        self.glassnode_client = None
        self.cryptoquant_client = None
        self.data_dir = Path("data/onchain")
        self.data_dir.mkdir(exist_ok=True, parents=True)

        # 収集対象のシンボル
        self.symbols = ["BTC", "ETH"]

    async def initialize(self):
        """初期化"""
        try:
            if settings.GLASSNODE_KEY:
                self.glassnode_client = GlassnodeClient(settings.GLASSNODE_KEY)
                logger.info("Glassnode client initialized")

            if settings.CRYPTOQUANT_KEY:
                self.cryptoquant_client = CryptoQuantClient(settings.CRYPTOQUANT_KEY)
                logger.info("CryptoQuant client initialized")

            # データベーステーブルを作成
            await self._create_tables()

        except Exception as e:
            logger.error(f"Failed to initialize OnChainDataCollector: {e}")
            raise

    async def _create_tables(self):
        """データベーステーブルを作成"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS whale_flows (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                inflow DECIMAL(20, 8),
                outflow DECIMAL(20, 8),
                net_flow DECIMAL(20, 8),
                PRIMARY KEY (timestamp, symbol)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS nvt_data (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                nvt_ratio DECIMAL(10, 4),
                nvt_signal DECIMAL(10, 4),
                PRIMARY KEY (timestamp, symbol)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS miner_outflows (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                outflow_amount DECIMAL(20, 8),
                outflow_value_usd DECIMAL(20, 8),
                PRIMARY KEY (timestamp, symbol)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS nupl_data (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                nupl_value DECIMAL(10, 4),
                supply_in_profit DECIMAL(10, 4),
                PRIMARY KEY (timestamp, symbol)
            )
            """,
        ]

        db = get_db()
        for table_sql in tables:
            db.execute(table_sql)

        logger.info("OnChain data tables created")

    async def collect_whale_flows(
        self, symbols: Optional[List[str]] = None, since: Optional[datetime] = None
    ) -> Dict[str, List[WhaleFlowData]]:
        """ホエールフローデータを収集"""
        if not self.glassnode_client:
            logger.warning("Glassnode client not initialized")
            return {}

        symbols = symbols or self.symbols
        results = {}

        for symbol in symbols:
            try:
                whale_flows = await self.glassnode_client.get_whale_flow(symbol=symbol, since=since)

                results[symbol] = whale_flows

                # データベースに保存
                await self._save_whale_flows_to_db(whale_flows)

            except Exception as e:
                logger.error(f"Error collecting whale flows for {symbol}: {e}")
                results[symbol] = []

        return results

    async def collect_nvt_data(
        self, symbols: Optional[List[str]] = None, since: Optional[datetime] = None
    ) -> Dict[str, List[NVTData]]:
        """NVTデータを収集"""
        if not self.glassnode_client:
            logger.warning("Glassnode client not initialized")
            return {}

        symbols = symbols or self.symbols
        results = {}

        for symbol in symbols:
            try:
                nvt_data = await self.glassnode_client.get_nvt_data(symbol=symbol, since=since)

                results[symbol] = nvt_data

                # データベースに保存
                await self._save_nvt_data_to_db(nvt_data)

            except Exception as e:
                logger.error(f"Error collecting NVT data for {symbol}: {e}")
                results[symbol] = []

        return results

    async def collect_miner_outflows(
        self, symbols: Optional[List[str]] = None, since: Optional[datetime] = None
    ) -> Dict[str, List[MinerOutflowData]]:
        """マイナーアウトフローデータを収集"""
        if not self.cryptoquant_client:
            logger.warning("CryptoQuant client not initialized")
            return {}

        symbols = symbols or self.symbols
        results = {}

        for symbol in symbols:
            try:
                outflow_data = await self.cryptoquant_client.get_miner_outflow(symbol=symbol, since=since)

                results[symbol] = outflow_data

                # データベースに保存
                await self._save_miner_outflows_to_db(outflow_data)

            except Exception as e:
                logger.error(f"Error collecting miner outflows for {symbol}: {e}")
                results[symbol] = []

        return results

    async def _save_whale_flows_to_db(self, whale_flows: List[WhaleFlowData]):
        """ホエールフローデータをデータベースに保存"""
        db = get_db()
        for flow in whale_flows:
            try:
                db.execute(
                    """
                    INSERT OR REPLACE INTO whale_flows
                    (timestamp, symbol, inflow, outflow, net_flow)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        flow.timestamp,
                        flow.symbol,
                        flow.inflow,
                        flow.outflow,
                        flow.net_flow,
                    ],
                )
            except Exception as e:
                logger.error(f"Error saving whale flow to DB: {e}")

    async def _save_nvt_data_to_db(self, nvt_data: List[NVTData]):
        """NVTデータをデータベースに保存"""
        db = get_db()
        for nvt in nvt_data:
            try:
                db.execute(
                    """
                    INSERT OR REPLACE INTO nvt_data
                    (timestamp, symbol, nvt_ratio, nvt_signal)
                    VALUES (?, ?, ?, ?)
                    """,
                    [nvt.timestamp, nvt.symbol, nvt.nvt_ratio, nvt.nvt_signal],
                )
            except Exception as e:
                logger.error(f"Error saving NVT data to DB: {e}")

    async def _save_miner_outflows_to_db(self, outflows: List[MinerOutflowData]):
        """マイナーアウトフローデータをデータベースに保存"""
        db = get_db()
        for outflow in outflows:
            try:
                db.execute(
                    """
                    INSERT OR REPLACE INTO miner_outflows
                    (timestamp, symbol, outflow_amount, outflow_value_usd)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        outflow.timestamp,
                        outflow.symbol,
                        outflow.outflow_amount,
                        outflow.outflow_value_usd,
                    ],
                )
            except Exception as e:
                logger.error(f"Error saving miner outflow to DB: {e}")

    async def run_scheduled_collection(self):
        """定期収集を実行"""
        logger.info("Starting scheduled onchain data collection...")

        try:
            # 過去1週間分のデータを収集
            since = datetime.now(timezone.utc) - timedelta(days=7)

            # 各データタイプを並列収集
            tasks = [
                self.collect_whale_flows(since=since),
                self.collect_nvt_data(since=since),
                self.collect_miner_outflows(since=since),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("Scheduled onchain data collection completed")

            return {
                "whale_flows": results[0] if len(results) > 0 else {},
                "nvt_data": results[1] if len(results) > 1 else {},
                "miner_outflows": results[2] if len(results) > 2 else {},
            }

        except Exception as e:
            logger.error(f"Error in scheduled onchain collection: {e}")
            raise

    async def close(self):
        """リソースをクリーンアップ"""
        if self.glassnode_client:
            await self.glassnode_client.close()
        if self.cryptoquant_client:
            await self.cryptoquant_client.close()
        logger.info("OnChainDataCollector closed")


# グローバルインスタンス
onchain_collector = OnChainDataCollector()
