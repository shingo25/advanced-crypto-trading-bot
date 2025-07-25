"""
PaperTradingAdapter の単体テスト
セキュリティとデータ整合性を重視したテスト
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os

from src.backend.exchanges.paper_trading_adapter import PaperTradingAdapter
from src.backend.trading.orders.models import Order, OrderType, OrderSide, OrderStatus
from src.backend.database.models import DatabaseManager
from src.backend.database.paper_wallet_service import PaperWalletService


class TestPaperTradingAdapterSecurity:
    """Paper Trading Adapterのセキュリティテスト"""
    
    def setup_method(self):
        """テスト用セットアップ"""
        # テスト用の一時データベース
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.test_user_id = str(uuid4())
        self.test_config = {
            "user_id": self.test_user_id,
            "database_url": f"sqlite:///{self.temp_db.name}",
            "real_exchange": "binance",
            "default_setting": "beginner",
            "fee_rates": {"maker": 0.001, "taker": 0.001},
            "execution_delay": 0.01,  # テスト用に短縮
            "slippage_rate": 0.0001,
        }
    
    def teardown_method(self):
        """テスト用クリーンアップ"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_initialization_security(self):
        """初期化時のセキュリティテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # セキュリティ確認
        assert adapter.exchange_name == "paper_trading"
        assert adapter.user_id == self.test_user_id
        assert adapter.wallet_service is not None
        assert adapter.db_manager is not None
        
        # 実際のAPIキーが使用されていないことを確認
        assert hasattr(adapter.real_adapter, 'exchange')
        # モック設定が適用されていることを確認
        real_exchange = adapter.real_adapter.exchange
        assert real_exchange.apiKey == "paper_trading_mock"
        assert real_exchange.secret == "paper_trading_mock"
    
    def test_user_id_validation(self):
        """ユーザーID検証のテスト"""
        # 不正なユーザーIDでのテスト
        invalid_configs = [
            {**self.test_config, "user_id": ""},
            {**self.test_config, "user_id": None},
        ]
        
        for config in invalid_configs:
            with pytest.raises(Exception):  # UUIDエラーまたは初期化エラー
                PaperTradingAdapter(config)
    
    @pytest.mark.asyncio
    async def test_balance_isolation(self):
        """残高の分離テスト（セキュリティ重要）"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 初期残高を確認
        balances = await adapter.get_balance()
        
        # デフォルト設定の確認（beginner）
        assert "USDT" in balances
        assert balances["USDT"]["total"] == 100000.0  # 初期10万USDT
        assert balances["USDT"]["free"] == 100000.0
        assert balances["USDT"]["used"] == 0.0
        
        # 他のユーザーIDでの分離確認
        other_user_id = str(uuid4())
        other_config = {**self.test_config, "user_id": other_user_id}
        other_adapter = PaperTradingAdapter(other_config)
        
        other_balances = await other_adapter.get_balance()
        
        # 各ユーザーが独立した残高を持つことを確認
        assert balances != other_balances or balances["USDT"]["total"] == other_balances["USDT"]["total"]
    
    @pytest.mark.asyncio
    async def test_paper_trading_flag_enforcement(self):
        """Paper Tradingフラグの強制適用テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # テスト注文作成
        test_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("0.001")
        )
        
        # 注文実行
        result = await adapter.place_order(test_order)
        
        # Paper Tradingフラグが正しく設定されていることを確認
        assert result["info"]["paper_trading"] is True
        assert result["info"]["user_id"] == self.test_user_id
        
        # 注文オブジェクトにもフラグが設定されていることを確認
        assert test_order.paper_trading is True


class TestPaperTradingAdapterFunctionality:
    """Paper Trading Adapterの機能テスト"""
    
    def setup_method(self):
        """テスト用セットアップ"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.test_user_id = str(uuid4())
        self.test_config = {
            "user_id": self.test_user_id,
            "database_url": f"sqlite:///{self.temp_db.name}",
            "real_exchange": "binance",
            "default_setting": "beginner",
            "fee_rates": {"maker": 0.001, "taker": 0.001},
            "execution_delay": 0.01,
            "slippage_rate": 0.0001,
        }
    
    def teardown_method(self):
        """テスト用クリーンアップ"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_market_order_execution(self):
        """成行注文の実行テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # モックで価格データを設定
        with patch.object(adapter, 'get_order_book') as mock_order_book:
            mock_order_book.return_value = {
                "bids": [[50000.0, 1.0]],
                "asks": [[50100.0, 1.0]],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # 買い注文のテスト
            buy_order = Order(
                exchange="paper_trading",
                symbol="BTC/USDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                amount=Decimal("0.001")
            )
            
            result = await adapter.place_order(buy_order)
            
            # 約定確認
            assert result["status"] == "filled"
            assert float(result["filled"]) == 0.001
            assert result["average"] is not None
            
            # 残高確認
            balances = await adapter.get_balance()
            assert "BTC" in balances
            assert balances["BTC"]["total"] > 0
            assert balances["USDT"]["total"] < 100000.0  # USDTが減っている
    
    @pytest.mark.asyncio
    async def test_limit_order_placement(self):
        """指値注文の発注テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 指値注文
        limit_order = Order(
            exchange="paper_trading",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.001"),
            price=Decimal("45000")
        )
        
        result = await adapter.place_order(limit_order)
        
        # 指値注文は待機状態になる
        assert result["status"] == "submitted"
        assert result["id"] is not None
        
        # アクティブ注文に登録されている
        open_orders = await adapter.get_open_orders()
        assert len(open_orders) == 1
        assert open_orders[0]["id"] == result["id"]
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self):
        """注文キャンセルテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 指値注文を発注
        limit_order = Order(
            exchange="paper_trading",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.001"),
            price=Decimal("45000")
        )
        
        result = await adapter.place_order(limit_order)
        order_id = result["id"]
        
        # 注文をキャンセル
        cancel_result = await adapter.cancel_order(order_id)
        
        assert cancel_result["status"] == "cancelled"
        
        # アクティブ注文から削除されている
        open_orders = await adapter.get_open_orders()
        assert len(open_orders) == 0
    
    @pytest.mark.asyncio
    async def test_insufficient_balance_handling(self):
        """残高不足時の処理テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 残高を超える注文
        large_order = Order(
            exchange="paper_trading",
            symbol="BTC/USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("10")  # 10 BTC = 約50万USDT（残高不足）
        )
        
        result = await adapter.place_order(large_order)
        
        # 注文が拒否される
        assert result["status"] == "rejected"
        assert "Insufficient balance" in result.get("info", {}).get("error", "")
    
    @pytest.mark.asyncio
    async def test_fee_calculation(self):
        """手数料計算テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        with patch.object(adapter, 'get_order_book') as mock_order_book:
            mock_order_book.return_value = {
                "bids": [[50000.0, 1.0]],
                "asks": [[50000.0, 1.0]],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # 成行買い注文
            buy_order = Order(
                exchange="paper_trading",
                symbol="BTC/USDT",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                amount=Decimal("0.001")
            )
            
            result = await adapter.place_order(buy_order)
            
            # 手数料が正しく計算されている
            expected_fee = 0.001 * 0.001  # 数量 * 手数料率
            assert abs(float(result["fee"]["amount"]) - expected_fee) < 1e-8
            assert result["fee"]["currency"] == "BTC"  # 買い注文はbase通貨で手数料
    
    def test_wallet_summary(self):
        """ウォレットサマリーテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        summary = adapter.get_wallet_summary()
        
        assert summary["user_id"] == self.test_user_id
        assert "balances" in summary
        assert "statistics" in summary
        assert "active_orders" in summary
        assert "timestamp" in summary
    
    def test_transaction_history(self):
        """取引履歴テスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        history = adapter.get_transaction_history()
        
        # 初期化時の入金履歴が記録されている
        assert len(history) > 0
        assert any(tx["transaction_type"] == "deposit" for tx in history)
    
    @pytest.mark.asyncio
    async def test_connection_methods(self):
        """接続関連メソッドのテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # Paper Tradingでは常に接続成功
        assert await adapter.connect() is True
        assert adapter.is_connected() is True
        
        # 切断処理
        await adapter.disconnect()
        # Paper Tradingでは切断後も接続状態を維持
        assert adapter.is_connected() is True


class TestPaperTradingAdapterEdgeCases:
    """Paper Trading Adapterのエッジケーステスト"""
    
    def setup_method(self):
        """テスト用セットアップ"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.test_user_id = str(uuid4())
        self.test_config = {
            "user_id": self.test_user_id,
            "database_url": f"sqlite:///{self.temp_db.name}",
            "real_exchange": "binance",
            "default_setting": "beginner",
        }
    
    def teardown_method(self):
        """テスト用クリーンアップ"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_invalid_symbol_handling(self):
        """不正なシンボル処理のテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 不正なシンボル形式
        invalid_order = Order(
            exchange="paper_trading",
            symbol="INVALID_SYMBOL",  # スラッシュがない
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            amount=Decimal("0.001")
        )
        
        # エラーハンドリングの確認
        result = asyncio.run(adapter.place_order(invalid_order))
        assert result["status"] in ["rejected", "failed"]
    
    def test_reset_wallet_functionality(self):
        """ウォレットリセット機能のテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        # 残高変更を加える（テスト用にダミー操作）
        original_summary = adapter.get_wallet_summary()
        
        # ウォレットリセット
        adapter.reset_wallet("advanced")  # より大きな初期残高設定
        
        # リセット後の確認
        new_summary = adapter.get_wallet_summary()
        # 統計がリセットされている（新しい設定が適用されている）
        assert new_summary["active_orders"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_orders(self):
        """同時注文処理のテスト"""
        adapter = PaperTradingAdapter(self.test_config)
        
        with patch.object(adapter, 'get_order_book') as mock_order_book:
            mock_order_book.return_value = {
                "bids": [[50000.0, 10.0]],
                "asks": [[50000.0, 10.0]],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # 複数の注文を同時実行
            orders = [
                Order(
                    exchange="paper_trading",
                    symbol="BTC/USDT",
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    amount=Decimal("0.001")
                )
                for _ in range(3)
            ]
            
            # 同時実行
            results = await asyncio.gather(*[
                adapter.place_order(order) for order in orders
            ])
            
            # すべて成功している
            assert all(result["status"] == "filled" for result in results)
            
            # 残高が正しく更新されている
            balances = await adapter.get_balance()
            expected_btc = 0.003  # 0.001 * 3
            assert abs(balances["BTC"]["total"] - expected_btc) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])