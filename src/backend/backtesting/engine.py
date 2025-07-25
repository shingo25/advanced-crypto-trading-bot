import asyncio
import logging
import multiprocessing as mp
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.backend.core.supabase_db import get_supabase_client
from src.backend.fee_models.base import TradeType
from src.backend.fee_models.exchanges import FeeModelFactory
from src.backend.risk.position_sizing import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """データ品質レポート"""

    symbol: str
    timeframe: str
    total_records: int
    missing_records: int
    duplicate_records: int
    data_coverage: float
    quality_score: float
    issues: List[str]

    def is_valid(self, min_quality_score: float = 0.95) -> bool:
        """データ品質が有効かチェック"""
        return self.quality_score >= min_quality_score


class DataValidator:
    """データ品質チェッククラス"""

    @staticmethod
    def validate_ohlcv_data(df: pd.DataFrame, symbol: str, timeframe: str) -> DataQualityReport:
        """OHLCVデータの品質をチェック"""
        issues = []

        # 基本統計
        total_records = len(df)
        duplicate_records = df.duplicated(subset=["timestamp"]).sum()

        # データの連続性チェック
        if len(df) > 1:
            df_sorted = df.sort_values("timestamp")
            time_diffs = df_sorted["timestamp"].diff()
            expected_interval = DataValidator._get_expected_interval(timeframe)

            # 欠損データの検出
            missing_count = (time_diffs > expected_interval * 1.5).sum()
        else:
            missing_count = 0

        # 価格データの妥当性チェック
        price_columns = ["open_price", "high_price", "low_price", "close_price"]
        for col in price_columns:
            if col in df.columns:
                # 負の価格
                if (df[col] <= 0).any():
                    issues.append(f"{col}に負の値または0が含まれています")

                # 異常な価格変動
                if len(df) > 1:
                    pct_change = df[col].pct_change().abs()
                    extreme_changes = (pct_change > 0.5).sum()  # 50%以上の変動
                    if extreme_changes > 0:
                        issues.append(f"{col}に異常な価格変動({extreme_changes}件)が検出されました")

        # High >= Low の確認
        if "high_price" in df.columns and "low_price" in df.columns:
            invalid_ohlc = (df["high_price"] < df["low_price"]).sum()
            if invalid_ohlc > 0:
                issues.append(f"High < Lowの無効なOHLCデータが{invalid_ohlc}件あります")

        # ボリュームチェック
        if "volume" in df.columns:
            zero_volume = (df["volume"] == 0).sum()
            if zero_volume > len(df) * 0.1:  # 10%以上がゼロボリューム
                issues.append(f"ゼロボリュームの割合が高すぎます({zero_volume}/{len(df)})")

        # データカバレッジ計算
        data_coverage = max(0, 1 - (missing_count / max(total_records, 1)))

        # 品質スコア計算
        quality_score = DataValidator._calculate_quality_score(
            total_records, missing_count, duplicate_records, len(issues)
        )

        return DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_records=total_records,
            missing_records=missing_count,
            duplicate_records=duplicate_records,
            data_coverage=data_coverage,
            quality_score=quality_score,
            issues=issues,
        )

    @staticmethod
    def _get_expected_interval(timeframe: str) -> timedelta:
        """時間枠に応じた期待される間隔を取得"""
        intervals = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1),
        }
        return intervals.get(timeframe, timedelta(hours=1))

    @staticmethod
    def _calculate_quality_score(total: int, missing: int, duplicates: int, issues: int) -> float:
        """品質スコアを計算"""
        if total == 0:
            return 0.0

        # 基本スコア（データの完全性）
        completeness_score = max(0, 1 - (missing / total))

        # 重複ペナルティ
        duplicate_penalty = min(0.2, duplicates / total)

        # 問題ペナルティ
        issue_penalty = min(0.3, issues * 0.1)

        return max(0, completeness_score - duplicate_penalty - issue_penalty)


class RealDataLoader:
    """実データローダークラス"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def load_ohlcv_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        exchange: str = "binance",
    ) -> pd.DataFrame:
        """Supabaseから実データを読み込み"""
        try:
            # シンボル形式を正規化 (BTC/USDT -> BTCUSDT)
            normalized_symbol = symbol.replace("/", "")

            response = (
                self.supabase.table("price_data")
                .select("*")
                .eq("exchange", exchange)
                .eq("symbol", normalized_symbol)
                .eq("timeframe", timeframe)
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .order("timestamp")
                .execute()
            )

            if not response.data:
                logger.warning(f"No data found for {symbol} {timeframe} from {start_date} to {end_date}")
                return pd.DataFrame()

            # DataFrameに変換
            df = pd.DataFrame(response.data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            logger.info(f"Loaded {len(df)} records for {symbol} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"Error loading real data for {symbol}: {e}")
            return pd.DataFrame()

    async def get_available_data_range(
        self, symbol: str, timeframe: str, exchange: str = "binance"
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """利用可能なデータの範囲を取得"""
        try:
            normalized_symbol = symbol.replace("/", "")

            # 最古のデータ
            oldest_response = (
                self.supabase.table("price_data")
                .select("timestamp")
                .eq("exchange", exchange)
                .eq("symbol", normalized_symbol)
                .eq("timeframe", timeframe)
                .order("timestamp")
                .limit(1)
                .execute()
            )

            # 最新のデータ
            latest_response = (
                self.supabase.table("price_data")
                .select("timestamp")
                .eq("exchange", exchange)
                .eq("symbol", normalized_symbol)
                .eq("timeframe", timeframe)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )

            oldest = None
            latest = None

            if oldest_response.data:
                oldest = datetime.fromisoformat(oldest_response.data[0]["timestamp"])

            if latest_response.data:
                latest = datetime.fromisoformat(latest_response.data[0]["timestamp"])

            return oldest, latest

        except Exception as e:
            logger.error(f"Error getting data range for {symbol}: {e}")
            return None, None


class BacktestOptimizer:
    """バックテスト最適化クラス"""

    @staticmethod
    def optimize_dataframe_processing(df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameの処理を最適化"""
        # データ型を最適化
        df = df.copy()

        # 数値列のデータ型を最適化
        numeric_columns = [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], downcast="float")

        # インデックスを最適化
        df = df.reset_index(drop=True)

        # メモリ使用量を削減
        df = df.sort_values("timestamp")

        return df

    @staticmethod
    def split_data_for_parallel_processing(df: pd.DataFrame, num_chunks: int = None) -> List[pd.DataFrame]:
        """並列処理用にデータを分割"""
        if num_chunks is None:
            num_chunks = min(mp.cpu_count(), len(df) // 1000)  # 最小1000行/チャンク

        num_chunks = max(1, num_chunks)
        chunk_size = len(df) // num_chunks

        chunks = []
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < num_chunks - 1 else len(df)
            chunk = df.iloc[start_idx:end_idx].copy()
            chunks.append(chunk)

        return chunks

    @staticmethod
    def estimate_processing_time(data_size: int, complexity_factor: float = 1.0) -> float:
        """処理時間を推定"""
        # 基本的な推定式（実際の環境に応じて調整）
        base_time_per_row = 0.0001  # 100マイクロ秒/行
        return data_size * base_time_per_row * complexity_factor


class PerformanceMonitor:
    """パフォーマンス監視クラス"""

    def __init__(self):
        self.start_time = None
        self.metrics = {}

    def start(self):
        """監視開始"""
        self.start_time = time.time()
        self.metrics = {
            "start_time": self.start_time,
            "memory_usage": self._get_memory_usage(),
        }

    def checkpoint(self, name: str):
        """チェックポイント記録"""
        current_time = time.time()
        self.metrics[f"{name}_time"] = current_time
        self.metrics[f"{name}_duration"] = current_time - self.start_time
        self.metrics[f"{name}_memory"] = self._get_memory_usage()

    def finish(self) -> Dict[str, Any]:
        """監視終了"""
        end_time = time.time()
        total_duration = end_time - self.start_time if self.start_time else 0

        self.metrics["end_time"] = end_time
        self.metrics["total_duration"] = total_duration
        self.metrics["final_memory"] = self._get_memory_usage()

        return self.metrics

    def _get_memory_usage(self) -> float:
        """メモリ使用量を取得（MB）"""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """注文データ"""

    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    amount: float
    filled_price: Optional[float] = None
    filled_amount: Optional[float] = None
    fee: Optional[float] = None
    trade_id: Optional[str] = None


@dataclass
class Trade:
    """取引データ"""

    timestamp: datetime
    symbol: str
    side: OrderSide
    price: float
    amount: float
    fee: float
    realized_pnl: float
    strategy_name: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Position:
    """ポジションデータ"""

    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: datetime

    def update_pnl(self, current_price: float):
        """未実現損益を更新"""
        self.current_price = current_price
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size


@dataclass
class Portfolio:
    """ポートフォリオデータ"""

    equity: float
    cash: float
    positions: Dict[str, Position]
    trades: List[Trade]

    def get_total_value(self) -> float:
        """総資産価値を計算"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.cash + total_unrealized


@dataclass
class BacktestResult:
    """バックテスト結果"""

    strategy_name: str
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: pd.DataFrame
    metrics: Dict[str, Any]

    def to_dict(self):
        return asdict(self)


class BacktestEngine:
    """バックテストエンジン"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        exchange: str = "binance",
        use_real_data: bool = True,
        data_quality_threshold: float = 0.95,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.exchange = exchange
        self.use_real_data = use_real_data
        self.data_quality_threshold = data_quality_threshold

        # 手数料モデル
        self.fee_model = FeeModelFactory.create(exchange)

        # ポートフォリオ
        self.portfolio = Portfolio(equity=initial_capital, cash=initial_capital, positions={}, trades=[])

        # 取引記録
        self.orders: List[Order] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # リスク管理
        self.risk_manager = None

        # データ関連
        self.data_loader = RealDataLoader() if use_real_data else None
        self.data_validator = DataValidator()
        self.data_quality_reports: Dict[str, DataQualityReport] = {}

        # 最適化関連
        self.optimizer = BacktestOptimizer()
        self.performance_monitor = PerformanceMonitor()
        self.enable_optimization = True

        # 統計情報
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "max_equity": initial_capital,
            "max_drawdown": 0.0,
            "peak_equity": initial_capital,
        }

        logger.info(f"BacktestEngine initialized with capital: ${initial_capital:,.2f}")

    def set_risk_manager(self, risk_config: Dict[str, Any]):
        """リスク管理を設定"""
        self.risk_manager = RiskManager(risk_config)

    async def run_backtest_with_real_data(
        self,
        strategy,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        strategy_name: str,
    ) -> BacktestResult:
        """実データを使用してバックテストを実行"""

        if not self.data_loader:
            raise ValueError("Real data loader not initialized")

        # データ範囲の確認
        (
            available_start,
            available_end,
        ) = await self.data_loader.get_available_data_range(symbol, timeframe, self.exchange)

        if not available_start or not available_end:
            raise ValueError(f"No data available for {symbol} {timeframe}")

        # 実際のデータ範囲を調整
        actual_start = max(start_date, available_start)
        actual_end = min(end_date, available_end)

        if actual_start >= actual_end:
            raise ValueError(f"Invalid date range: {actual_start} to {actual_end}")

        logger.info(f"Running backtest for {symbol} from {actual_start} to {actual_end}")

        # データを読み込み
        df = await self.data_loader.load_ohlcv_data(symbol, timeframe, actual_start, actual_end, self.exchange)

        if df.empty:
            raise ValueError(f"No data loaded for {symbol} {timeframe}")

        # データ品質チェック
        quality_report = self.data_validator.validate_ohlcv_data(df, symbol, timeframe)
        self.data_quality_reports[f"{symbol}_{timeframe}"] = quality_report

        logger.info(f"Data quality score: {quality_report.quality_score:.3f}")

        if not quality_report.is_valid(self.data_quality_threshold):
            warning_msg = (
                f"Data quality below threshold ({quality_report.quality_score:.3f} < {self.data_quality_threshold})"
            )
            logger.warning(warning_msg)
            if quality_report.issues:
                logger.warning(f"Issues found: {', '.join(quality_report.issues)}")

        # バックテストを実行
        return await self._run_backtest_on_dataframe(df, strategy, symbol, strategy_name)

    async def _run_backtest_on_dataframe(
        self,
        df: pd.DataFrame,
        strategy,
        symbol: str,
        strategy_name: str,
    ) -> BacktestResult:
        """DataFrameを使用してバックテストを実行（最適化版）"""

        # パフォーマンス監視開始
        self.performance_monitor.start()

        # データフレーム最適化
        if self.enable_optimization:
            df = self.optimizer.optimize_dataframe_processing(df)
            self.performance_monitor.checkpoint("dataframe_optimization")

        # 処理時間推定
        estimated_time = self.optimizer.estimate_processing_time(len(df))
        logger.info(f"Estimated processing time: {estimated_time:.2f} seconds for {len(df)} records")

        # エンジンをリセット
        self.reset()

        # ストラテジーを初期化
        strategy.reset()
        self.performance_monitor.checkpoint("initialization")

        # 大きなデータセットの場合は進行状況を表示
        show_progress = len(df) > 10000
        progress_interval = len(df) // 20 if show_progress else float("inf")

        # 各行でストラテジーを実行
        for idx, row in df.iterrows():
            timestamp = row["timestamp"]

            # OHLCVデータを作成（最適化されたアクセス）
            ohlcv = {
                "open": row["open_price"],
                "high": row["high_price"],
                "low": row["low_price"],
                "close": row["close_price"],
                "volume": row["volume"],
            }

            # ストラテジーにデータを渡してシグナルを取得
            signals = strategy.generate_signals(timestamp, ohlcv, symbol)

            # シグナルを処理
            self.process_bar(timestamp, ohlcv, signals, strategy_name)

            # 進行状況表示
            if show_progress and idx % progress_interval == 0:
                progress = (idx / len(df)) * 100
                logger.info(f"Backtest progress: {progress:.1f}% ({idx}/{len(df)})")

        self.performance_monitor.checkpoint("main_processing")

        # 結果を取得
        result = self.get_results(strategy_name)

        # データ品質情報を結果に追加
        key = f"{symbol}_{strategy_name}"
        if key in self.data_quality_reports:
            result.metrics["data_quality"] = asdict(self.data_quality_reports[key])

        # パフォーマンス指標を結果に追加
        performance_metrics = self.performance_monitor.finish()
        result.metrics["performance"] = performance_metrics

        logger.info(f"Backtest completed in {performance_metrics['total_duration']:.2f} seconds")

        return result

    async def run_batch_backtests(
        self,
        backtest_configs: List[Dict[str, Any]],
        max_workers: int = None,
    ) -> List[BacktestResult]:
        """複数のバックテストを並列実行"""

        if max_workers is None:
            max_workers = min(mp.cpu_count(), len(backtest_configs))

        logger.info(f"Running {len(backtest_configs)} backtests with {max_workers} workers")

        # 実行時間を推定
        total_estimated_time = sum(
            self.optimizer.estimate_processing_time(config.get("data_size", 1000), config.get("complexity_factor", 1.0))
            for config in backtest_configs
        )

        logger.info(f"Estimated total time: {total_estimated_time:.2f} seconds")

        # 並列実行
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_config = {}

            for config in backtest_configs:
                future = executor.submit(self._run_single_backtest_from_config, config)
                future_to_config[future] = config

            for future in asyncio.as_completed(future_to_config):
                try:
                    result = await future
                    results.append(result)
                except Exception as e:
                    config = future_to_config[future]
                    logger.error(f"Backtest failed for config {config}: {e}")

        return results

    async def _run_single_backtest_from_config(self, config: Dict[str, Any]) -> BacktestResult:
        """設定から単一のバックテストを実行"""
        # エンジンの新しいインスタンスを作成（並列実行のため）
        engine = BacktestEngine(
            initial_capital=config.get("initial_capital", self.initial_capital),
            commission=config.get("commission", self.commission),
            slippage=config.get("slippage", self.slippage),
            exchange=config.get("exchange", self.exchange),
        )

        # 設定からバックテストを実行
        return await engine.run_backtest_with_real_data(
            strategy=config["strategy"],
            symbol=config["symbol"],
            timeframe=config["timeframe"],
            start_date=config["start_date"],
            end_date=config["end_date"],
            strategy_name=config["strategy_name"],
        )

    async def validate_backtest_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> DataQualityReport:
        """バックテスト用データの品質を事前確認"""

        if not self.data_loader:
            raise ValueError("Real data loader not initialized")

        df = await self.data_loader.load_ohlcv_data(symbol, timeframe, start_date, end_date, self.exchange)

        if df.empty:
            # 空のデータの場合のレポート
            return DataQualityReport(
                symbol=symbol,
                timeframe=timeframe,
                total_records=0,
                missing_records=0,
                duplicate_records=0,
                data_coverage=0.0,
                quality_score=0.0,
                issues=["データが見つかりません"],
            )

        return self.data_validator.validate_ohlcv_data(df, symbol, timeframe)

    def process_bar(
        self,
        timestamp: datetime,
        ohlcv: Dict[str, float],
        signals: Dict[str, Any],
        strategy_name: str,
    ):
        """バーデータを処理"""

        # 現在価格でポジションの未実現損益を更新
        current_price = ohlcv["close"]
        symbol = signals.get("symbol", "BTCUSDT")

        # 既存ポジションの更新
        if symbol in self.portfolio.positions:
            self.portfolio.positions[symbol].update_pnl(current_price)

        # シグナルの処理
        if signals.get("enter_long"):
            self._process_long_entry(timestamp, symbol, current_price, strategy_name)
        elif signals.get("enter_short"):
            self._process_short_entry(timestamp, symbol, current_price, strategy_name)
        elif signals.get("exit_long"):
            self._process_long_exit(timestamp, symbol, current_price, strategy_name)
        elif signals.get("exit_short"):
            self._process_short_exit(timestamp, symbol, current_price, strategy_name)

        # 資産価値の更新
        self.portfolio.equity = self.portfolio.get_total_value()

        # 統計情報の更新
        self._update_stats(timestamp)

        # 資産曲線の記録
        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "equity": self.portfolio.equity,
                "cash": self.portfolio.cash,
                "unrealized_pnl": sum(pos.unrealized_pnl for pos in self.portfolio.positions.values()),
            }
        )

    def _process_long_entry(self, timestamp: datetime, symbol: str, price: float, strategy_name: str):
        """ロングエントリーを処理"""

        # 既にポジションがある場合はスキップ
        if symbol in self.portfolio.positions:
            return

        # ポジションサイズの計算
        position_size = self._calculate_position_size(symbol, price, strategy_name)

        if position_size <= 0:
            return

        # 必要な資金を計算
        required_capital = price * position_size

        # 現金が不足している場合はスキップ
        if self.portfolio.cash < required_capital:
            logger.warning(
                f"Insufficient cash for long entry: required ${required_capital:.2f}, available ${self.portfolio.cash:.2f}"
            )
            return

        # スリッページを考慮した約定価格
        execution_price = price * (1 + self.slippage)

        # 手数料を計算
        fee = self.fee_model.calculate_fee(TradeType.TAKER, execution_price, position_size, symbol)

        # ポジションを作成
        position = Position(
            symbol=symbol,
            side=OrderSide.BUY,
            size=position_size,
            entry_price=execution_price,
            current_price=execution_price,
            unrealized_pnl=0.0,
            entry_time=timestamp,
        )

        self.portfolio.positions[symbol] = position
        self.portfolio.cash -= required_capital + fee

        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.BUY,
            price=execution_price,
            amount=position_size,
            fee=fee,
            realized_pnl=0.0,
            strategy_name=strategy_name,
        )

        self.portfolio.trades.append(trade)
        self.stats["total_trades"] += 1

        logger.info(f"Long entry: {symbol} @ ${execution_price:.2f}, size: {position_size:.6f}")

    def _process_long_exit(self, timestamp: datetime, symbol: str, price: float, strategy_name: str):
        """ロングイグジットを処理"""

        if symbol not in self.portfolio.positions:
            return

        position = self.portfolio.positions[symbol]

        if position.side != OrderSide.BUY:
            return

        # スリッページを考慮した約定価格
        execution_price = price * (1 - self.slippage)

        # 手数料を計算
        fee = self.fee_model.calculate_fee(TradeType.TAKER, execution_price, position.size, symbol)

        # 損益を計算
        realized_pnl = (execution_price - position.entry_price) * position.size - fee

        # 現金を更新
        self.portfolio.cash += execution_price * position.size - fee

        # ポジションを削除
        del self.portfolio.positions[symbol]

        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.SELL,
            price=execution_price,
            amount=position.size,
            fee=fee,
            realized_pnl=realized_pnl,
            strategy_name=strategy_name,
        )

        self.portfolio.trades.append(trade)

        # 統計情報の更新
        if realized_pnl > 0:
            self.stats["winning_trades"] += 1
        else:
            self.stats["losing_trades"] += 1

        logger.info(f"Long exit: {symbol} @ ${execution_price:.2f}, PnL: ${realized_pnl:.2f}")

    def _process_short_entry(self, timestamp: datetime, symbol: str, price: float, strategy_name: str):
        """ショートエントリーを処理"""

        # 既にポジションがある場合はスキップ
        if symbol in self.portfolio.positions:
            return

        # ポジションサイズの計算
        position_size = self._calculate_position_size(symbol, price, strategy_name)

        if position_size <= 0:
            return

        # 証拠金の計算（簡略化）
        required_margin = price * position_size * 0.1  # 10倍レバレッジ想定

        # 証拠金が不足している場合はスキップ
        if self.portfolio.cash < required_margin:
            logger.warning(
                f"Insufficient margin for short entry: required ${required_margin:.2f}, available ${self.portfolio.cash:.2f}"
            )
            return

        # スリッページを考慮した約定価格
        execution_price = price * (1 - self.slippage)

        # 手数料を計算
        fee = self.fee_model.calculate_fee(TradeType.TAKER, execution_price, position_size, symbol)

        # ポジションを作成
        position = Position(
            symbol=symbol,
            side=OrderSide.SELL,
            size=position_size,
            entry_price=execution_price,
            current_price=execution_price,
            unrealized_pnl=0.0,
            entry_time=timestamp,
        )

        self.portfolio.positions[symbol] = position
        self.portfolio.cash -= fee

        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.SELL,
            price=execution_price,
            amount=position_size,
            fee=fee,
            realized_pnl=0.0,
            strategy_name=strategy_name,
        )

        self.portfolio.trades.append(trade)
        self.stats["total_trades"] += 1

        logger.info(f"Short entry: {symbol} @ ${execution_price:.2f}, size: {position_size:.6f}")

    def _process_short_exit(self, timestamp: datetime, symbol: str, price: float, strategy_name: str):
        """ショートイグジットを処理"""

        if symbol not in self.portfolio.positions:
            return

        position = self.portfolio.positions[symbol]

        if position.side != OrderSide.SELL:
            return

        # スリッページを考慮した約定価格
        execution_price = price * (1 + self.slippage)

        # 手数料を計算
        fee = self.fee_model.calculate_fee(TradeType.TAKER, execution_price, position.size, symbol)

        # 損益を計算
        realized_pnl = (position.entry_price - execution_price) * position.size - fee

        # 現金を更新
        self.portfolio.cash += realized_pnl

        # ポジションを削除
        del self.portfolio.positions[symbol]

        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.BUY,
            price=execution_price,
            amount=position.size,
            fee=fee,
            realized_pnl=realized_pnl,
            strategy_name=strategy_name,
        )

        self.portfolio.trades.append(trade)

        # 統計情報の更新
        if realized_pnl > 0:
            self.stats["winning_trades"] += 1
        else:
            self.stats["losing_trades"] += 1

        logger.info(f"Short exit: {symbol} @ ${execution_price:.2f}, PnL: ${realized_pnl:.2f}")

    def _calculate_position_size(self, symbol: str, price: float, strategy_name: str) -> float:
        """ポジションサイズを計算"""

        if self.risk_manager:
            # リスク管理を使用
            return self.risk_manager.calculate_position_size(
                strategy_name=strategy_name,
                capital=self.portfolio.equity,
                signal_strength=1.0,
                volatility=0.02,  # 簡略化
                win_rate=0.5,
                avg_win=0.01,
                avg_loss=0.01,
            )
        else:
            # 固定サイズ（総資産の5%）
            return (self.portfolio.equity * 0.05) / price

    def _update_stats(self, timestamp: datetime):
        """統計情報を更新"""

        current_equity = self.portfolio.equity

        # 最大資産を更新
        if current_equity > self.stats["max_equity"]:
            self.stats["max_equity"] = current_equity
            self.stats["peak_equity"] = current_equity

        # ドローダウンを計算
        if self.stats["peak_equity"] > 0:
            drawdown = (self.stats["peak_equity"] - current_equity) / self.stats["peak_equity"]
            if drawdown > self.stats["max_drawdown"]:
                self.stats["max_drawdown"] = drawdown

    def get_results(self, strategy_name: str) -> BacktestResult:
        """バックテスト結果を取得"""

        final_capital = self.portfolio.equity
        total_trades = len(self.portfolio.trades)
        winning_trades = self.stats["winning_trades"]
        losing_trades = self.stats["losing_trades"]

        # 基本統計
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_return = (final_capital - self.initial_capital) / self.initial_capital

        # 資産曲線を DataFrame に変換
        equity_df = pd.DataFrame(self.equity_curve)

        # パフォーマンス指標を計算
        metrics = self._calculate_performance_metrics(equity_df)

        result = BacktestResult(
            strategy_name=strategy_name,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            annualized_return=metrics.get("annualized_return", 0.0),
            max_drawdown=self.stats["max_drawdown"],
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            sortino_ratio=metrics.get("sortino_ratio", 0.0),
            calmar_ratio=metrics.get("calmar_ratio", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            trades=self.portfolio.trades,
            equity_curve=equity_df,
            metrics=metrics,
        )

        return result

    def _calculate_performance_metrics(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """パフォーマンス指標を計算（精度向上版）"""

        if len(equity_df) < 2:
            return {}

        # リターン計算
        equity_df["returns"] = equity_df["equity"].pct_change()
        returns = equity_df["returns"].dropna()

        if len(returns) == 0:
            return {}

        # 時間枠に基づく年間化係数の動的計算
        time_diff = equity_df["timestamp"].diff().median()
        if pd.isna(time_diff):
            periods_per_year = 365 * 24  # デフォルト（1時間足想定）
        else:
            minutes_per_period = time_diff.total_seconds() / 60
            periods_per_year = (365 * 24 * 60) / minutes_per_period

        # 基本統計
        mean_return = returns.mean()
        std_return = returns.std()

        # 年間化リターンの改良計算
        total_return = (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1
        periods_count = len(returns)
        annualized_return = ((1 + total_return) ** (periods_per_year / periods_count)) - 1

        # リスクフリーレート（3%想定）
        risk_free_rate = 0.03
        excess_return = mean_return - (risk_free_rate / periods_per_year)

        # シャープレシオ（リスクフリーレート考慮）
        sharpe_ratio = (excess_return / std_return * np.sqrt(periods_per_year)) if std_return > 0 else 0

        # ソルティノレシオ（改良版）
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
        sortino_ratio = (excess_return / downside_std * np.sqrt(periods_per_year)) if downside_std > 0 else 0

        # カルマーレシオ（改良版）
        calmar_ratio = annualized_return / self.stats["max_drawdown"] if self.stats["max_drawdown"] > 0 else 0

        # プロフィットファクターとその他の取引統計
        winning_trades = [t for t in self.portfolio.trades if t.realized_pnl > 0]
        losing_trades = [t for t in self.portfolio.trades if t.realized_pnl < 0]

        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # 追加の取引統計
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # 最大連続勝ち・負け数
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades()

        # ドローダウン詳細分析
        dd_analysis = self._analyze_drawdowns(equity_df)

        # VaRとCVaR（精度向上版）
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else 0

        # ベータ計算（市場リターンとの相関 - BTC基準）
        beta = self._calculate_beta(returns) if len(returns) > 30 else 0

        # 情報比率（Information Ratio）
        tracking_error = std_return * np.sqrt(periods_per_year)
        information_ratio = annualized_return / tracking_error if tracking_error > 0 else 0

        return {
            # 基本リターン指標
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": std_return * np.sqrt(periods_per_year),
            # リスク調整リターン
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "information_ratio": information_ratio,
            # 取引統計
            "profit_factor": profit_factor,
            "win_loss_ratio": win_loss_ratio,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "consecutive_wins": consecutive_wins,
            "consecutive_losses": consecutive_losses,
            # リスク指標
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95,
            "cvar_99": cvar_99,
            "beta": beta,
            # 分布統計
            "skewness": returns.skew(),
            "kurtosis": returns.kurtosis(),
            # ドローダウン分析
            "max_drawdown_duration": dd_analysis.get("max_duration", 0),
            "avg_drawdown": dd_analysis.get("avg_drawdown", 0),
            "recovery_factor": total_return / self.stats["max_drawdown"] if self.stats["max_drawdown"] > 0 else 0,
            # その他
            "periods_per_year": periods_per_year,
            "total_periods": periods_count,
        }

    def _calculate_consecutive_trades(self) -> tuple[int, int]:
        """最大連続勝ち・負け数を計算"""
        if not self.portfolio.trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.portfolio.trades:
            if trade.realized_pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.realized_pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _analyze_drawdowns(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """ドローダウンの詳細分析"""
        if len(equity_df) < 2:
            return {"max_duration": 0, "avg_drawdown": 0}

        equity = equity_df["equity"].values
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak

        # ドローダウン期間の計算
        in_drawdown = drawdown > 0.001  # 0.1%以上のドローダウン

        if not in_drawdown.any():
            return {"max_duration": 0, "avg_drawdown": 0}

        # 連続するドローダウン期間を特定
        drawdown_periods = []
        start_idx = None

        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                drawdown_periods.append(i - start_idx)
                start_idx = None

        # 最後がドローダウンで終わる場合
        if start_idx is not None:
            drawdown_periods.append(len(in_drawdown) - start_idx)

        max_duration = max(drawdown_periods) if drawdown_periods else 0
        avg_drawdown = np.mean(drawdown[drawdown > 0.001]) if drawdown_periods else 0

        return {
            "max_duration": max_duration,
            "avg_drawdown": avg_drawdown,
        }

    def _calculate_beta(self, returns: pd.Series) -> float:
        """ベータ値を計算（簡易版）"""
        # 実装では市場リターンデータが必要だが、ここでは簡易計算
        # 実際にはBTCなどの基準リターンとの相関を使用
        try:
            # ボラティリティベースの疑似ベータ
            volatility = returns.std()
            market_volatility = 0.04  # 仮想通貨市場の平均日次ボラティリティ
            return volatility / market_volatility if market_volatility > 0 else 1.0
        except Exception:
            return 1.0

    def reset(self):
        """エンジンをリセット"""
        self.portfolio = Portfolio(
            equity=self.initial_capital,
            cash=self.initial_capital,
            positions={},
            trades=[],
        )

        self.orders = []
        self.equity_curve = []

        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "max_equity": self.initial_capital,
            "max_drawdown": 0.0,
            "peak_equity": self.initial_capital,
        }

        logger.info("BacktestEngine reset")

    async def save_results_to_database(self, result: BacktestResult) -> str:
        """バックテスト結果をSupabaseに保存"""
        try:
            supabase = get_supabase_client()

            # メイン結果レコード
            result_record = {
                "strategy_name": result.strategy_name,
                "initial_capital": float(result.initial_capital),
                "final_capital": float(result.final_capital),
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": float(result.win_rate),
                "total_return": float(result.total_return),
                "annualized_return": float(result.annualized_return),
                "max_drawdown": float(result.max_drawdown),
                "sharpe_ratio": float(result.sharpe_ratio),
                "sortino_ratio": float(result.sortino_ratio),
                "calmar_ratio": float(result.calmar_ratio),
                "profit_factor": float(result.profit_factor),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metrics": result.metrics,  # JSON形式で詳細指標を保存
                "exchange": self.exchange,
            }

            # バックテスト結果をメインテーブルに保存
            backtest_response = supabase.table("backtest_results").insert(result_record).execute()

            if not backtest_response.data:
                raise Exception("Failed to save backtest result")

            backtest_id = backtest_response.data[0]["id"]

            # 取引履歴を保存
            if result.trades:
                trade_records = []
                for trade in result.trades:
                    trade_record = {
                        "backtest_id": backtest_id,
                        "timestamp": trade.timestamp.isoformat(),
                        "symbol": trade.symbol,
                        "side": trade.side.value,
                        "price": float(trade.price),
                        "amount": float(trade.amount),
                        "fee": float(trade.fee),
                        "realized_pnl": float(trade.realized_pnl),
                        "strategy_name": trade.strategy_name,
                    }
                    trade_records.append(trade_record)

                # バッチサイズで分割して保存
                batch_size = 1000
                for i in range(0, len(trade_records), batch_size):
                    batch = trade_records[i : i + batch_size]
                    supabase.table("backtest_trades").insert(batch).execute()

            # 資産曲線を保存
            if not result.equity_curve.empty:
                equity_records = []
                for _, row in result.equity_curve.iterrows():
                    equity_record = {
                        "backtest_id": backtest_id,
                        "timestamp": row["timestamp"].isoformat(),
                        "equity": float(row["equity"]),
                        "cash": float(row.get("cash", 0)),
                        "unrealized_pnl": float(row.get("unrealized_pnl", 0)),
                    }
                    equity_records.append(equity_record)

                # バッチサイズで分割して保存
                for i in range(0, len(equity_records), batch_size):
                    batch = equity_records[i : i + batch_size]
                    supabase.table("backtest_equity_curve").insert(batch).execute()

            logger.info(f"Backtest results saved to database with ID: {backtest_id}")
            return str(backtest_id)

        except Exception as e:
            logger.error(f"Error saving backtest results to database: {e}")
            raise

    async def load_backtest_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """データベースからバックテスト結果を読み込み"""
        try:
            supabase = get_supabase_client()

            # メイン結果を取得
            result_response = supabase.table("backtest_results").select("*").eq("id", backtest_id).single().execute()

            if not result_response.data:
                return None

            result_data = result_response.data

            # 取引履歴を取得
            trades_response = (
                supabase.table("backtest_trades")
                .select("*")
                .eq("backtest_id", backtest_id)
                .order("timestamp")
                .execute()
            )

            trades = []
            for trade_data in trades_response.data:
                trade = Trade(
                    timestamp=datetime.fromisoformat(trade_data["timestamp"]),
                    symbol=trade_data["symbol"],
                    side=OrderSide(trade_data["side"]),
                    price=trade_data["price"],
                    amount=trade_data["amount"],
                    fee=trade_data["fee"],
                    realized_pnl=trade_data["realized_pnl"],
                    strategy_name=trade_data["strategy_name"],
                )
                trades.append(trade)

            # 資産曲線を取得
            equity_response = (
                supabase.table("backtest_equity_curve")
                .select("*")
                .eq("backtest_id", backtest_id)
                .order("timestamp")
                .execute()
            )

            equity_data = []
            for equity_row in equity_response.data:
                equity_data.append(
                    {
                        "timestamp": datetime.fromisoformat(equity_row["timestamp"]),
                        "equity": equity_row["equity"],
                        "cash": equity_row["cash"],
                        "unrealized_pnl": equity_row["unrealized_pnl"],
                    }
                )

            equity_df = pd.DataFrame(equity_data)

            # BacktestResultオブジェクトを再構築
            result = BacktestResult(
                strategy_name=result_data["strategy_name"],
                initial_capital=result_data["initial_capital"],
                final_capital=result_data["final_capital"],
                total_trades=result_data["total_trades"],
                winning_trades=result_data["winning_trades"],
                losing_trades=result_data["losing_trades"],
                win_rate=result_data["win_rate"],
                total_return=result_data["total_return"],
                annualized_return=result_data["annualized_return"],
                max_drawdown=result_data["max_drawdown"],
                sharpe_ratio=result_data["sharpe_ratio"],
                sortino_ratio=result_data["sortino_ratio"],
                calmar_ratio=result_data["calmar_ratio"],
                profit_factor=result_data["profit_factor"],
                trades=trades,
                equity_curve=equity_df,
                metrics=result_data.get("metrics", {}),
            )

            return result

        except Exception as e:
            logger.error(f"Error loading backtest result {backtest_id}: {e}")
            return None

    async def list_backtest_results(
        self,
        strategy_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """バックテスト結果の一覧を取得"""
        try:
            supabase = get_supabase_client()

            query = supabase.table("backtest_results").select(
                "id, strategy_name, initial_capital, final_capital, total_return, "
                "sharpe_ratio, max_drawdown, total_trades, win_rate, created_at"
            )

            if strategy_name:
                query = query.eq("strategy_name", strategy_name)

            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return response.data

        except Exception as e:
            logger.error(f"Error listing backtest results: {e}")
            return []

    def save_results(self, result: BacktestResult, output_dir: str = "results"):
        """結果を保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 取引履歴を保存
        trades_df = pd.DataFrame([trade.to_dict() for trade in result.trades])
        trades_file = output_path / f"{result.strategy_name}_trades.csv"
        trades_df.to_csv(trades_file, index=False)

        # 資産曲線を保存
        equity_file = output_path / f"{result.strategy_name}_equity.csv"
        result.equity_curve.to_csv(equity_file, index=False)

        # 結果サマリーを保存
        summary = {
            "strategy_name": result.strategy_name,
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_return": result.total_return,
            "annualized_return": result.annualized_return,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
        }

        summary_file = output_path / f"{result.strategy_name}_summary.json"
        import json

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to {output_path}")
