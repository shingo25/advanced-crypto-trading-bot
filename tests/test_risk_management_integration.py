"""
リスク管理統合テスト
CircuitBreaker、EnhancedRiskManager、PositionManagerの統合テスト
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.backend.risk.circuit_breaker import CircuitBreaker, BreakerState, TripReason
from src.backend.trading.enhanced_risk_manager import EnhancedRiskManager, PositionManager
from src.backend.trading.orders.models import Order, OrderType, OrderSide


# テスト用のPositionクラス
class Position:
    """テスト用ポジションクラス"""
    def __init__(self, symbol: str, side: str, quantity: float, entry_price: float, current_price: float, unrealized_pnl: float):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price
        self.unrealized_pnl = unrealized_pnl
    
    def get_market_value(self) -> float:
        return self.quantity * self.current_price


@pytest.fixture
def circuit_breaker_config():
    """サーキットブレーカー設定"""
    return {
        "failure_threshold": 3,
        "recovery_timeout_seconds": 60,
        "volatility_threshold": 0.15,
        "drawdown_threshold": 0.20,
        "var_threshold": 0.10,
        "half_open_test_trades": 2,
    }


@pytest.fixture
def enhanced_risk_config(circuit_breaker_config):
    """EnhancedRiskManager設定"""
    return {
        "circuit_breaker": circuit_breaker_config,
        "advanced_risk": {
            "max_portfolio_var_95": 0.05,
            "max_portfolio_var_99": 0.08,
            "max_daily_loss": 0.02,
            "var_window": 30,
        },
        "basic_risk": {
            "risk_limits": {
                "max_position_size": 50000.0,
                "max_daily_loss": 1000.0,
                "max_drawdown": 0.15,
            }
        },
        "position_manager": {
            "max_position_count": 5,
            "auto_rebalance_threshold": 0.30,
        },
        "realtime_monitoring": False,  # テスト用に無効化
    }


@pytest.fixture
def sample_position():
    """サンプルポジション"""
    return Position(
        symbol="BTC/USDT",
        side="long",
        quantity=1.0,
        entry_price=45000.0,
        current_price=46000.0,
        unrealized_pnl=1000.0
    )


@pytest.fixture
def sample_order():
    """サンプル注文"""
    return Order(
        exchange="binance",
        symbol="BTC/USDT",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=Decimal("0.1"),
        price=Decimal("45000")
    )


class TestCircuitBreaker:
    """CircuitBreakerの単体テスト"""
    
    def test_initialization(self, circuit_breaker_config):
        """初期化テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        assert cb.state == BreakerState.CLOSED
        assert cb.failure_threshold == 3
        assert cb.consecutive_losses == 0
        assert not cb.manual_override
    
    def test_trip_from_consecutive_losses(self, circuit_breaker_config):
        """連続損失による作動テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # 閾値以下では作動しない
        for i in range(2):
            cb.on_trade_result(False)
            assert cb.state == BreakerState.CLOSED
        
        # 閾値到達で作動
        cb.on_trade_result(False)
        assert cb.state == BreakerState.OPEN
        assert cb.consecutive_losses == 3
    
    def test_trip_from_volatility(self, circuit_breaker_config):
        """ボラティリティによる作動テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # 正常範囲
        cb.check_volatility(0.10)
        assert cb.state == BreakerState.CLOSED
        
        # 閾値超過で作動
        cb.check_volatility(0.20)
        assert cb.state == BreakerState.OPEN
    
    def test_trip_from_drawdown(self, circuit_breaker_config):
        """ドローダウンによる作動テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # 正常範囲
        cb.check_drawdown(0.15)
        assert cb.state == BreakerState.CLOSED
        
        # 閾値超過で作動
        cb.check_drawdown(0.25)
        assert cb.state == BreakerState.OPEN
    
    def test_manual_trip_and_release(self, circuit_breaker_config):
        """手動作動・解除テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # 手動作動
        cb.manual_trip("Test emergency")
        assert cb.state == BreakerState.OPEN
        assert cb.manual_override == True
        
        # 手動解除
        cb.manual_release()
        assert cb.state == BreakerState.CLOSED
        assert cb.manual_override == False
    
    def test_half_open_transition(self, circuit_breaker_config):
        """ハーフオープン遷移テスト"""
        # タイムアウトを短く設定
        config = circuit_breaker_config.copy()
        config["recovery_timeout_seconds"] = 1
        
        cb = CircuitBreaker(config)
        
        # 作動
        cb.trip(TripReason.CONSECUTIVE_LOSSES)
        assert cb.state == BreakerState.OPEN
        
        # タイムアウト前は遷移しない
        assert not cb.attempt_reset()
        assert cb.state == BreakerState.OPEN
        
        # タイムアウト後に遷移
        import time
        time.sleep(1.1)
        assert cb.attempt_reset()
        assert cb.state == BreakerState.HALF_OPEN
    
    def test_half_open_success_path(self, circuit_breaker_config):
        """ハーフオープンでの成功パステスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # ハーフオープン状態に設定
        cb.state = BreakerState.HALF_OPEN
        cb.test_trades_executed = 0
        
        # テスト取引成功
        cb.on_trade_result(True)
        assert cb.test_trades_executed == 1
        assert cb.state == BreakerState.HALF_OPEN
        
        # 2回目成功でリセット（リセット後はカウンターも0に戻る）
        cb.on_trade_result(True)
        assert cb.state == BreakerState.CLOSED
        assert cb.test_trades_executed == 0  # リセット後は0
    
    def test_half_open_failure_path(self, circuit_breaker_config):
        """ハーフオープンでの失敗パステスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # ハーフオープン状態に設定
        cb.state = BreakerState.HALF_OPEN
        
        # テスト取引失敗でオープンに戻る
        cb.on_trade_result(False)
        assert cb.state == BreakerState.OPEN
    
    def test_is_trading_allowed(self, circuit_breaker_config):
        """取引許可判定テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        # CLOSED状態では許可
        assert cb.is_trading_allowed == True
        
        # OPEN状態では拒否
        cb.state = BreakerState.OPEN
        assert cb.is_trading_allowed == False
        
        # HALF_OPEN状態では制限付き許可
        cb.state = BreakerState.HALF_OPEN
        cb.test_trades_executed = 0
        assert cb.is_trading_allowed == True
        
        cb.test_trades_executed = 2  # 制限到達
        assert cb.is_trading_allowed == False
    
    def test_callback_execution(self, circuit_breaker_config):
        """コールバック実行テスト"""
        cb = CircuitBreaker(circuit_breaker_config)
        
        trip_callback = Mock()
        reset_callback = Mock()
        notification_callback = Mock()
        
        cb.set_callbacks(
            on_trip=trip_callback,
            on_reset=reset_callback,
            notification=notification_callback
        )
        
        # 作動時のコールバック
        cb.trip(TripReason.MANUAL_OVERRIDE, {"test": "data"})
        trip_callback.assert_called_once_with(TripReason.MANUAL_OVERRIDE, {"test": "data"})
        notification_callback.assert_called_once()
        
        # リセット時のコールバック
        cb.reset()
        reset_callback.assert_called_once()


class TestPositionManager:
    """PositionManagerのテスト"""
    
    def test_initialization(self):
        """初期化テスト"""
        pm = PositionManager()
        
        assert len(pm.get_all_positions()) == 0
        assert pm.get_total_value() == 0
        assert pm.get_total_pnl() == 0
    
    def test_position_management(self, sample_position):
        """ポジション管理テスト"""
        pm = PositionManager()
        
        # ポジション追加
        pm.update_position(sample_position)
        assert len(pm.get_all_positions()) == 1
        assert pm.get_position("BTC/USDT") == sample_position
        
        # ポジション削除
        pm.remove_position("BTC/USDT")
        assert len(pm.get_all_positions()) == 0
        assert pm.get_position("BTC/USDT") is None
    
    def test_portfolio_calculations(self, sample_position):
        """ポートフォリオ計算テスト"""
        pm = PositionManager()
        pm.update_position(sample_position)
        
        # 総額計算
        expected_value = sample_position.get_market_value()
        assert pm.get_total_value() == expected_value
        
        # PnL計算
        assert pm.get_total_pnl() == sample_position.unrealized_pnl
    
    def test_concentration_calculation(self, sample_position):
        """集中度計算テスト"""
        pm = PositionManager()
        pm.update_position(sample_position)
        
        concentrations = pm.get_position_concentrations()
        assert concentrations["BTC/USDT"] == 1.0  # 100%集中
    
    def test_drawdown_calculation(self):
        """ドローダウン計算テスト"""
        pm = PositionManager()
        
        # ピーク設定
        pm.update_equity_history(100000.0)
        assert pm._peak_equity == 100000.0
        assert pm.get_current_drawdown() == 0.0
        
        # ドローダウン発生
        pm.update_equity_history(80000.0)
        assert pm.get_current_drawdown() == 0.2  # 20%ドローダウン


class TestEnhancedRiskManager:
    """EnhancedRiskManagerの統合テスト"""
    
    def test_initialization(self, enhanced_risk_config):
        """初期化テスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        assert erm.circuit_breaker is not None
        assert erm.advanced_manager is not None
        assert erm.basic_risk_manager is not None
        assert erm.position_manager is not None
    
    @pytest.mark.asyncio
    async def test_order_risk_check_normal(self, enhanced_risk_config, sample_order):
        """正常な注文リスクチェック"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        is_allowed, error_msg = await erm.check_order_risk(
            sample_order, 
            portfolio_value=Decimal("100000")
        )
        
        assert is_allowed == True
        assert error_msg is None
    
    @pytest.mark.asyncio
    async def test_order_risk_check_circuit_breaker_open(self, enhanced_risk_config, sample_order):
        """サーキットブレーカー作動時の注文拒否"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        # サーキットブレーカー作動
        erm.circuit_breaker.manual_trip("Test")
        
        is_allowed, error_msg = await erm.check_order_risk(sample_order)
        
        assert is_allowed == False
        assert "Circuit breaker" in error_msg
    
    @pytest.mark.asyncio
    async def test_realtime_risk_update(self, enhanced_risk_config, sample_position):
        """リアルタイムリスク更新テスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        # ポジション追加
        erm.position_manager.update_position(sample_position)
        
        # リスク更新実行（エラーが発生しないことを確認）
        await erm.update_realtime_risk()
        
        # 最終チェック時間が更新されていることを確認
        assert erm._last_risk_check is not None
    
    @pytest.mark.asyncio
    async def test_emergency_stop_trigger(self, enhanced_risk_config):
        """緊急停止トリガーテスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        with patch.object(erm, '_execute_emergency_actions', new_callable=AsyncMock) as mock_emergency:
            # 高リスク状態を模擬
            with patch.object(erm, '_should_emergency_stop', return_value=True):
                await erm.update_realtime_risk()
                
                mock_emergency.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manual_emergency_stop(self, enhanced_risk_config):
        """手動緊急停止テスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        with patch.object(erm, '_execute_emergency_actions', new_callable=AsyncMock) as mock_emergency:
            await erm.manual_emergency_stop("Manual test")
            
            assert erm.circuit_breaker.state == BreakerState.OPEN
            assert erm.circuit_breaker.manual_override == True
            mock_emergency.assert_called_once()
    
    def test_trade_result_processing(self, enhanced_risk_config):
        """取引結果処理テスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        sample_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("0.1")
        )
        
        # 成功時
        erm.on_trade_result(True, sample_order, {"profit": 100})
        assert erm.circuit_breaker.consecutive_gains >= 1
        assert erm.circuit_breaker.consecutive_losses == 0
        
        # 失敗時
        erm.on_trade_result(False, sample_order, {"loss": -50})
        assert erm.circuit_breaker.consecutive_losses >= 1
        assert erm.circuit_breaker.consecutive_gains == 0
    
    def test_comprehensive_status(self, enhanced_risk_config):
        """包括的ステータス取得テスト"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        status = erm.get_comprehensive_status()
        
        required_keys = [
            "timestamp", "circuit_breaker", "position_manager", 
            "basic_risk", "monitoring"
        ]
        
        for key in required_keys:
            assert key in status
        
        assert "state" in status["circuit_breaker"]
        assert "total_positions" in status["position_manager"]
        assert "enabled" in status["monitoring"]


class TestIntegrationScenarios:
    """統合シナリオテスト"""
    
    @pytest.mark.asyncio
    async def test_high_volatility_scenario(self, enhanced_risk_config):
        """高ボラティリティシナリオ"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        # 高ボラティリティ状況を模擬
        erm.circuit_breaker.check_volatility(0.25)  # 25%ボラティリティ
        
        # サーキットブレーカーが作動するはず
        assert erm.circuit_breaker.state == BreakerState.OPEN
        
        # 注文が拒否されるはず
        sample_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000")
        )
        
        is_allowed, error_msg = await erm.check_order_risk(sample_order)
        assert is_allowed == False
        assert "Circuit breaker" in error_msg
    
    @pytest.mark.asyncio
    async def test_large_drawdown_scenario(self, enhanced_risk_config):
        """大きなドローダウンシナリオ"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        
        # 大きなドローダウンを模擬
        erm.circuit_breaker.check_drawdown(0.30)  # 30%ドローダウン
        
        # サーキットブレーカーが作動するはず
        assert erm.circuit_breaker.state == BreakerState.OPEN
        
        # 緊急アクションが必要な状態
        with patch.object(erm, '_execute_emergency_actions', new_callable=AsyncMock) as mock_emergency:
            await erm.update_realtime_risk()
            # 必要に応じて緊急アクションが実行される
    
    @pytest.mark.asyncio
    async def test_consecutive_losses_scenario(self, enhanced_risk_config):
        """連続損失シナリオ"""
        erm = EnhancedRiskManager(enhanced_risk_config)
        sample_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("0.1")
        )
        
        # 連続3回の損失
        for i in range(3):
            erm.on_trade_result(False, sample_order, {"loss": -100})
        
        # サーキットブレーカーが作動するはず
        assert erm.circuit_breaker.state == BreakerState.OPEN
        
        # 取引が拒否されるはず
        is_allowed, error_msg = await erm.check_order_risk(sample_order)
        assert is_allowed == False
    
    @pytest.mark.asyncio
    async def test_recovery_scenario(self, enhanced_risk_config):
        """回復シナリオ"""
        # タイムアウトを短く設定
        config = enhanced_risk_config.copy()
        config["circuit_breaker"]["recovery_timeout_seconds"] = 1
        config["circuit_breaker"]["half_open_test_trades"] = 1
        
        erm = EnhancedRiskManager(config)
        sample_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("0.1")
        )
        
        # サーキットブレーカー作動
        erm.circuit_breaker.trip(TripReason.VOLATILITY_SPIKE)
        assert erm.circuit_breaker.state == BreakerState.OPEN
        
        # タイムアウト待機
        import time
        time.sleep(1.1)
        
        # ハーフオープンに遷移
        assert erm.circuit_breaker.attempt_reset()
        assert erm.circuit_breaker.state == BreakerState.HALF_OPEN
        
        # テスト取引成功でリセット
        erm.on_trade_result(True, sample_order)
        assert erm.circuit_breaker.state == BreakerState.CLOSED
        
        # 取引が再開されるはず
        is_allowed, error_msg = await erm.check_order_risk(sample_order)
        assert is_allowed == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])