"""
リアルタイム価格配信システム
Binance WebSocketから価格データを取得してクライアントに配信
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Set

import aiohttp
import websockets

from crypto_bot.websocket.manager import (
    ChannelType,
    MessageType,
    WebSocketMessage,
    websocket_manager,
)

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """価格データ構造"""

    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_24h": self.change_24h,
            "change_percent_24h": self.change_percent_24h,
            "volume_24h": self.volume_24h,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "timestamp": self.timestamp,
        }


@dataclass
class TradeData:
    """取引データ構造"""

    symbol: str
    price: float
    quantity: float
    is_buyer_maker: bool
    timestamp: str
    trade_id: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "side": "sell" if self.is_buyer_maker else "buy",
            "timestamp": self.timestamp,
            "trade_id": self.trade_id,
        }


class BinanceWebSocketStreamer:
    """BinanceのWebSocketストリーム管理"""

    def __init__(self):
        self.base_url = "wss://stream.binance.com:9443/ws"
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribed_symbols: Set[str] = set()
        self.price_cache: Dict[str, PriceData] = {}
        self.is_running = False

        # デフォルト監視シンボル
        self.default_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "DOTUSDT",
            "AVAXUSDT",
        ]

        logger.info("Binance WebSocket Streamer initialized")

    async def start(self):
        """ストリーミング開始"""
        if self.is_running:
            logger.warning("Streamer is already running")
            return

        self.is_running = True
        logger.info("Starting Binance WebSocket streamer...")

        # デフォルトシンボルで開始
        await self.subscribe_symbols(self.default_symbols)

        # 24時間統計データを定期取得
        asyncio.create_task(self._fetch_24h_stats_periodically())

        logger.info(f"Binance streamer started with {len(self.default_symbols)} symbols")

    async def stop(self):
        """ストリーミング停止"""
        self.is_running = False

        # 全ての接続を閉じる
        for connection in self.connections.values():
            await connection.close()

        self.connections.clear()
        self.subscribed_symbols.clear()

        logger.info("Binance WebSocket streamer stopped")

    async def subscribe_symbols(self, symbols: List[str]):
        """シンボルを購読"""
        new_symbols = [s.upper() for s in symbols if s.upper() not in self.subscribed_symbols]

        if not new_symbols:
            return

        for symbol in new_symbols:
            try:
                # 個別ティッカーストリーム
                await self._create_ticker_stream(symbol)
                # 個別トレードストリーム
                await self._create_trade_stream(symbol)

                self.subscribed_symbols.add(symbol)
                logger.info(f"Subscribed to {symbol}")

            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")

    async def unsubscribe_symbol(self, symbol: str):
        """シンボルの購読を解除"""
        symbol = symbol.upper()

        if symbol in self.subscribed_symbols:
            # 接続を閉じる
            ticker_key = f"{symbol}_ticker"
            trade_key = f"{symbol}_trade"

            if ticker_key in self.connections:
                await self.connections[ticker_key].close()
                del self.connections[ticker_key]

            if trade_key in self.connections:
                await self.connections[trade_key].close()
                del self.connections[trade_key]

            self.subscribed_symbols.remove(symbol)

            if symbol in self.price_cache:
                del self.price_cache[symbol]

            logger.info(f"Unsubscribed from {symbol}")

    async def _create_ticker_stream(self, symbol: str):
        """ティッカーストリームを作成"""
        stream_name = f"{symbol.lower()}@ticker"
        url = f"{self.base_url}/{stream_name}"

        async def ticker_handler():
            try:
                async with websockets.connect(url) as websocket:
                    self.connections[f"{symbol}_ticker"] = websocket

                    async for message in websocket:
                        if not self.is_running:
                            break

                        try:
                            data = json.loads(message)
                            await self._handle_ticker_data(data)
                        except Exception as e:
                            logger.error(f"Error processing ticker data for {symbol}: {e}")

            except Exception as e:
                logger.error(f"Ticker stream error for {symbol}: {e}")
                # 再接続を試行
                if self.is_running:
                    await asyncio.sleep(5)
                    await self._create_ticker_stream(symbol)

        asyncio.create_task(ticker_handler())

    async def _create_trade_stream(self, symbol: str):
        """トレードストリームを作成"""
        stream_name = f"{symbol.lower()}@trade"
        url = f"{self.base_url}/{stream_name}"

        async def trade_handler():
            try:
                async with websockets.connect(url) as websocket:
                    self.connections[f"{symbol}_trade"] = websocket

                    async for message in websocket:
                        if not self.is_running:
                            break

                        try:
                            data = json.loads(message)
                            await self._handle_trade_data(data)
                        except Exception as e:
                            logger.error(f"Error processing trade data for {symbol}: {e}")

            except Exception as e:
                logger.error(f"Trade stream error for {symbol}: {e}")
                # 再接続を試行
                if self.is_running:
                    await asyncio.sleep(5)
                    await self._create_trade_stream(symbol)

        asyncio.create_task(trade_handler())

    async def _handle_ticker_data(self, data: dict):
        """ティッカーデータを処理"""
        try:
            symbol = data["s"]

            price_data = PriceData(
                symbol=symbol,
                price=float(data["c"]),
                change_24h=float(data["P"]),
                change_percent_24h=float(data["p"]),
                volume_24h=float(data["v"]),
                high_24h=float(data["h"]),
                low_24h=float(data["l"]),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # キャッシュを更新
            self.price_cache[symbol] = price_data

            # WebSocketクライアントに配信
            await self._broadcast_price_update(price_data)

        except Exception as e:
            logger.error(f"Error handling ticker data: {e}")

    async def _handle_trade_data(self, data: dict):
        """トレードデータを処理"""
        try:
            trade_data = TradeData(
                symbol=data["s"],
                price=float(data["p"]),
                quantity=float(data["q"]),
                is_buyer_maker=data["m"],
                timestamp=datetime.fromtimestamp(data["T"] / 1000, timezone.utc).isoformat(),
                trade_id=str(data["t"]),
            )

            # WebSocketクライアントに配信
            await self._broadcast_trade_update(trade_data)

        except Exception as e:
            logger.error(f"Error handling trade data: {e}")

    async def _broadcast_price_update(self, price_data: PriceData):
        """価格更新をブロードキャスト"""
        message = WebSocketMessage(
            type=MessageType.PRICE_UPDATE,
            channel=ChannelType.PRICES,
            data=price_data.to_dict(),
        )

        # 全体配信
        await websocket_manager.broadcast_to_channel(ChannelType.PRICES.value, message)

        # シンボル固有チャンネル配信
        symbol_channel = f"{ChannelType.PRICES.value}:{price_data.symbol}"
        await websocket_manager.broadcast_to_channel(symbol_channel, message)

    async def _broadcast_trade_update(self, trade_data: TradeData):
        """取引更新をブロードキャスト"""
        message = WebSocketMessage(
            type=MessageType.TRADE_EXECUTION,
            channel=ChannelType.TRADES,
            data=trade_data.to_dict(),
        )

        # 全体配信
        await websocket_manager.broadcast_to_channel(ChannelType.TRADES.value, message)

        # シンボル固有チャンネル配信
        symbol_channel = f"{ChannelType.TRADES.value}:{trade_data.symbol}"
        await websocket_manager.broadcast_to_channel(symbol_channel, message)

    async def _fetch_24h_stats_periodically(self):
        """24時間統計を定期取得"""
        while self.is_running:
            try:
                await self._fetch_24h_stats()
                await asyncio.sleep(300)  # 5分間隔
            except Exception as e:
                logger.error(f"Error fetching 24h stats: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機

    async def _fetch_24h_stats(self):
        """24時間統計をREST APIから取得"""
        url = "https://api.binance.com/api/v3/ticker/24hr"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        for ticker in data:
                            symbol = ticker["symbol"]

                            if symbol in self.subscribed_symbols:
                                # キャッシュされた価格データがあれば更新
                                if symbol in self.price_cache:
                                    cached = self.price_cache[symbol]
                                    cached.volume_24h = float(ticker["volume"])
                                    cached.high_24h = float(ticker["highPrice"])
                                    cached.low_24h = float(ticker["lowPrice"])
                                    cached.change_24h = float(ticker["priceChange"])
                                    cached.change_percent_24h = float(ticker["priceChangePercent"])
                    else:
                        logger.warning(f"Failed to fetch 24h stats: {response.status}")

        except Exception as e:
            logger.error(f"Error in 24h stats fetch: {e}")

    def get_subscribed_symbols(self) -> List[str]:
        """購読中のシンボル一覧を取得"""
        return list(self.subscribed_symbols)

    def get_price_cache(self) -> Dict[str, dict]:
        """価格キャッシュを取得"""
        return {symbol: data.to_dict() for symbol, data in self.price_cache.items()}

    def get_connection_stats(self) -> dict:
        """接続統計を取得"""
        return {
            "is_running": self.is_running,
            "subscribed_symbols": len(self.subscribed_symbols),
            "active_connections": len(self.connections),
            "cached_prices": len(self.price_cache),
        }


class PriceStreamManager:
    """価格配信管理システム"""

    def __init__(self):
        self.binance_streamer = BinanceWebSocketStreamer()
        self.is_running = False

    async def start(self):
        """価格配信システム開始"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting price stream manager...")

        # Binanceストリーマー開始
        await self.binance_streamer.start()

        logger.info("Price stream manager started")

    async def stop(self):
        """価格配信システム停止"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping price stream manager...")

        # Binanceストリーマー停止
        await self.binance_streamer.stop()

        logger.info("Price stream manager stopped")

    async def subscribe_symbol(self, symbol: str):
        """シンボル購読"""
        await self.binance_streamer.subscribe_symbols([symbol])

    async def unsubscribe_symbol(self, symbol: str):
        """シンボル購読解除"""
        await self.binance_streamer.unsubscribe_symbol(symbol)

    def get_stats(self) -> dict:
        """統計情報取得"""
        binance_stats = self.binance_streamer.get_connection_stats()

        return {
            "manager_running": self.is_running,
            "binance": binance_stats,
            "total_symbols": binance_stats["subscribed_symbols"],
            "cached_prices": binance_stats["cached_prices"],
        }

    def get_all_prices(self) -> dict:
        """全価格データ取得"""
        return self.binance_streamer.get_price_cache()


# グローバル価格配信マネージャー
price_stream_manager = PriceStreamManager()
