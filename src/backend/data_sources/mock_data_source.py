"""
モックデータソース実装
開発・テスト用のリアルなダミーデータを提供
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np

from src.backend.exchanges.base import (
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)

from .interfaces import DataSourceStrategy


class MockDataGenerator:
    """リアルなモックデータを生成するヘルパークラス"""

    def __init__(self):
        # 基準価格（実際の市場価格に近い値）
        self.base_prices = {
            "BTC": 45000.0,
            "ETH": 2500.0,
            "BNB": 320.0,
            "SOL": 100.0,
            "XRP": 0.65,
        }
        
        # ボラティリティ（年率換算）
        self.volatilities = {
            "BTC": 0.65,  # 65%
            "ETH": 0.75,  # 75%
            "BNB": 0.70,  # 70%
            "SOL": 0.90,  # 90%
            "XRP": 0.80,  # 80%
        }
        
        # 価格の履歴を保持（連続性のため）
        self.price_history: Dict[str, float] = {}

    def get_base_symbol(self, symbol: str) -> str:
        """シンボルからベース通貨を抽出"""
        if "/" in symbol:
            return symbol.split("/")[0]
        return symbol[:3]  # 最初の3文字を仮定

    def generate_price_movement(self, symbol: str, timeframe_minutes: int) -> float:
        """
        リアルな価格変動を生成（幾何ブラウン運動ベース）
        
        Args:
            symbol: シンボル
            timeframe_minutes: 時間枠（分）
        
        Returns:
            float: 価格変動率
        """
        base_symbol = self.get_base_symbol(symbol)
        volatility = self.volatilities.get(base_symbol, 0.7)
        
        # 時間スケーリング（年率ボラティリティを分単位に変換）
        minutes_in_year = 365 * 24 * 60
        time_factor = np.sqrt(timeframe_minutes / minutes_in_year)
        
        # ドリフト項（わずかな上昇トレンド）
        drift = 0.05 / minutes_in_year * timeframe_minutes
        
        # ランダムウォーク項
        random_shock = np.random.normal(0, 1)
        
        # 価格変動率
        return drift + volatility * time_factor * random_shock

    def generate_ohlcv(self, symbol: str, base_price: float, timeframe_minutes: int) -> OHLCV:
        """単一のOHLCVデータを生成"""
        # 価格変動を生成
        price_change = self.generate_price_movement(symbol, timeframe_minutes)
        
        # 始値（前回の終値または基準価格）
        open_price = self.price_history.get(symbol, base_price)
        
        # 高値・安値・終値を生成
        intra_volatility = abs(price_change) * 0.3
        high_price = open_price * (1 + abs(np.random.normal(0, intra_volatility)))
        low_price = open_price * (1 - abs(np.random.normal(0, intra_volatility)))
        close_price = open_price * (1 + price_change)
        
        # ボリューム（価格変動に応じて増加）
        base_volume = 1000 * (base_price / 1000)  # 価格に比例した基準ボリューム
        volume = base_volume * (1 + abs(price_change) * 10) * np.random.uniform(0.5, 1.5)
        
        # 次回のために終値を保存
        self.price_history[symbol] = close_price
        
        return OHLCV(
            timestamp=datetime.now(timezone.utc),
            open=round(open_price, 2),
            high=round(max(high_price, open_price, close_price), 2),
            low=round(min(low_price, open_price, close_price), 2),
            close=round(close_price, 2),
            volume=round(volume, 4),
        )


class MockDataSource(DataSourceStrategy):
    """モックデータソースの実装"""

    def __init__(self):
        self.generator = MockDataGenerator()
        self.is_running = True

    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """モックティッカーデータを生成"""
        base_symbol = self.generator.get_base_symbol(symbol)
        base_price = self.generator.base_prices.get(base_symbol, 100.0)
        
        # 現在の価格を生成（わずかな変動を加える）
        current_price = self.generator.price_history.get(
            symbol,
            base_price * np.random.uniform(0.99, 1.01)
        )
        
        # スプレッドを追加（0.01%〜0.05%）
        spread_percentage = np.random.uniform(0.0001, 0.0005)
        half_spread = current_price * spread_percentage / 2
        
        # 24時間のボリュームを生成
        daily_volume = base_price * 10000 * np.random.uniform(0.5, 2.0)
        
        return Ticker(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            bid=round(current_price - half_spread, 2),
            ask=round(current_price + half_spread, 2),
            last=round(current_price, 2),
            volume=round(daily_volume, 4),
        )

    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """モックOHLCVデータを生成"""
        # 時間枠を分に変換
        timeframe_minutes = {
            TimeFrame.MINUTE_1: 1,
            TimeFrame.MINUTE_5: 5,
            TimeFrame.MINUTE_15: 15,
            TimeFrame.MINUTE_30: 30,
            TimeFrame.HOUR_1: 60,
            TimeFrame.HOUR_2: 120,
            TimeFrame.HOUR_4: 240,
            TimeFrame.HOUR_8: 480,
            TimeFrame.DAY_1: 1440,
            TimeFrame.WEEK_1: 10080,
            TimeFrame.MONTH_1: 43200,
        }.get(timeframe, 60)
        
        # 基準価格を取得
        base_symbol = self.generator.get_base_symbol(symbol)
        base_price = self.generator.base_prices.get(base_symbol, 100.0)
        
        # 開始時刻を設定
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(minutes=timeframe_minutes * limit)
        
        # OHLCVデータを生成
        ohlcv_list = []
        current_time = since
        
        for i in range(limit):
            ohlcv = self.generator.generate_ohlcv(symbol, base_price, timeframe_minutes)
            ohlcv.timestamp = current_time
            ohlcv_list.append(ohlcv)
            current_time += timedelta(minutes=timeframe_minutes)
        
        return ohlcv_list

    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """モック資金調達率データを生成"""
        # -0.01% 〜 0.01% の範囲でランダムに生成（実際の市場に近い値）
        funding_rate = np.random.uniform(-0.0001, 0.0001)
        
        # 次回の資金調達時刻（8時間ごと）
        now = datetime.now(timezone.utc)
        hours_until_next = 8 - (now.hour % 8)
        next_funding_time = now.replace(
            hour=(now.hour + hours_until_next) % 24,
            minute=0,
            second=0,
            microsecond=0
        )
        if hours_until_next + now.hour >= 24:
            next_funding_time += timedelta(days=1)
        
        return FundingRate(
            timestamp=now,
            symbol=symbol,
            funding_rate=round(funding_rate, 6),
            next_funding_time=next_funding_time,
        )

    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """モック建玉データを生成"""
        base_symbol = self.generator.get_base_symbol(symbol)
        base_price = self.generator.base_prices.get(base_symbol, 100.0)
        
        # 建玉数量（実際の市場規模に近い値）
        base_oi = {
            "BTC": 50000,  # 50,000 BTC
            "ETH": 500000,  # 500,000 ETH
            "BNB": 1000000,  # 1,000,000 BNB
            "SOL": 5000000,  # 5,000,000 SOL
            "XRP": 100000000,  # 100,000,000 XRP
        }.get(base_symbol, 1000000)
        
        # ランダムな変動を加える（±20%）
        open_interest = base_oi * np.random.uniform(0.8, 1.2)
        open_interest_value = open_interest * base_price
        
        return OpenInterest(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            open_interest=round(open_interest, 2),
            open_interest_value=round(open_interest_value, 2),
        )

    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """モック残高データを生成"""
        # デモ用の残高
        return {
            "USDT": 10000.0,  # $10,000
            "BTC": 0.1,       # 0.1 BTC
            "ETH": 1.0,       # 1 ETH
            "BNB": 10.0,      # 10 BNB
        }

    async def is_available(self, exchange: str) -> bool:
        """モックデータソースは常に利用可能"""
        return self.is_running