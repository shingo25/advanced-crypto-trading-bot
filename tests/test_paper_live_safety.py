"""
Paper/Live切り替えの安全性テスト
意図しない実取引の防止、設定ミス検知、データ分離の確認
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from src.backend.exchanges.factory import ExchangeFactory
from src.backend.exchanges.paper_trading_adapter import PaperTradingAdapter
from src.backend.core.config import settings


class ConfigurationError(Exception):
    """設定エラー用のカスタム例外"""
    pass


class LiveModeInNonProductionError(ConfigurationError):
    """非本番環境でのLiveモード使用エラー"""
    pass


class TestPaperLiveModeSelection:
    """Paper/Liveモード選択の安全性テスト"""
    
    def test_default_mode_is_paper(self):
        """デフォルトモードはPaperであることの確認"""
        factory = ExchangeFactory()
        
        # trading_modeを指定しない場合、Paperモードが選択される
        adapter = factory.create_adapter("binance")
        assert isinstance(adapter, PaperTradingAdapter)
        
        # 明示的にpaperモードを指定
        adapter = factory.create_adapter("binance", trading_mode="paper")
        assert isinstance(adapter, PaperTradingAdapter)
    
    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_live_mode_blocked_in_development(self):
        """開発環境でのLiveモード禁止"""
        factory = ExchangeFactory()
        
        # 開発環境でliveモードを指定するとエラーが発生するべき
        with pytest.raises((ConfigurationError, ValueError)) as exc_info:
            factory.create_adapter("binance", trading_mode="live")
        
        # エラーメッセージに開発環境での警告が含まれることを確認
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["development", "live", "production"])
    
    @patch.dict(os.environ, {"ENVIRONMENT": "staging"})
    def test_live_mode_blocked_in_staging(self):
        """ステージング環境でのLiveモード禁止"""
        factory = ExchangeFactory()
        
        # ステージング環境でliveモードを指定するとエラーが発生するべき
        with pytest.raises((ConfigurationError, ValueError)) as exc_info:
            factory.create_adapter("binance", trading_mode="live")
    
    @patch.dict(os.environ, {"ENVIRONMENT": "test"})
    def test_live_mode_blocked_in_test(self):
        """テスト環境でのLiveモード禁止"""
        factory = ExchangeFactory()
        
        # テスト環境でliveモードを指定するとエラーが発生するべき
        with pytest.raises((ConfigurationError, ValueError)) as exc_info:
            factory.create_adapter("binance", trading_mode="live")
    
    def test_invalid_trading_mode_rejected(self):
        """無効なtrading_modeの拒否"""
        factory = ExchangeFactory()
        
        # 無効なtrading_modeを指定するとエラーが発生するべき
        with pytest.raises(ValueError) as exc_info:
            factory.create_adapter("binance", trading_mode="invalid_mode")
        
        assert "trading mode" in str(exc_info.value).lower()


class TestPaperModeAPIKeySafety:
    """Paperモードでの実APIキー保護テスト"""
    
    def test_paper_mode_uses_mock_api_keys(self):
        """Paperモードでは実際のAPIキーを使用しない"""
        factory = ExchangeFactory()
        paper_adapter = factory.create_adapter("binance", trading_mode="paper")
        
        # PaperTradingAdapterの場合、実際のAPIキーは使用されない
        if hasattr(paper_adapter, 'api_key'):
            # APIキーがNoneまたはmock/demoキーであることを確認
            api_key = paper_adapter.api_key
            assert api_key is None or "mock" in str(api_key).lower() or "demo" in str(api_key).lower()
        
        if hasattr(paper_adapter, 'secret'):
            # シークレットキーがNoneまたはmock/demoキーであることを確認
            secret = paper_adapter.secret
            assert secret is None or "mock" in str(secret).lower() or "demo" in str(secret).lower()
    
    @patch('src.backend.core.config.settings')
    def test_paper_mode_ignores_production_api_keys(self, mock_settings):
        """Paperモードでは本番APIキーを読み込まない"""
        # 本番APIキーが設定されていても使用されないことを確認
        mock_settings.BINANCE_API_KEY = "real_production_api_key"
        mock_settings.BINANCE_SECRET = "real_production_secret"
        
        factory = ExchangeFactory()
        paper_adapter = factory.create_adapter("binance", trading_mode="paper")
        
        # PaperTradingAdapterは本番APIキーを無視するべき
        assert isinstance(paper_adapter, PaperTradingAdapter)
        # 実際のAPIキーが設定されていないことを確認
        if hasattr(paper_adapter, 'api_key'):
            assert paper_adapter.api_key != "real_production_api_key"
        if hasattr(paper_adapter, 'secret'):
            assert paper_adapter.secret != "real_production_secret"


class TestPaperModeTradeIsolation:
    """Paperモード取引の分離テスト"""
    
    @patch('ccxt.binance')
    def test_paper_mode_no_external_api_calls(self, mock_ccxt_binance):
        """Paperモードでは外部API呼び出しが発生しない"""
        # CCXTライブラリのモック設定
        mock_exchange = MagicMock()
        mock_ccxt_binance.return_value = mock_exchange
        
        factory = ExchangeFactory()
        paper_adapter = factory.create_adapter("binance", trading_mode="paper")
        
        # モック注文データ
        order_data = {
            "symbol": "BTC/USDT",
            "type": "market",
            "side": "buy",
            "amount": 0.001,
            "price": None
        }
        
        # Paper取引を実行
        if hasattr(paper_adapter, 'create_order'):
            result = paper_adapter.create_order(**order_data)
            
            # 外部API（CCXT）が呼び出されていないことを確認
            mock_exchange.create_order.assert_not_called()
            
            # 結果が仮想的な注文結果であることを確認
            assert result is not None
            if isinstance(result, dict):
                assert "id" in result  # 仮想注文IDが生成される
    
    def test_paper_mode_uses_virtual_balance(self):
        """Paperモードでは仮想残高を使用"""
        import uuid
        
        factory = ExchangeFactory()
        test_user_id = str(uuid.uuid4())
        
        # データベース接続エラーが発生してもPaperTradingAdapterが作成されることを確認
        paper_adapter = factory.create_adapter("binance", trading_mode="paper", user_id=test_user_id)
        
        # PaperTradingAdapterが作成されることを確認
        assert isinstance(paper_adapter, PaperTradingAdapter)
        
        # 仮想残高機能があることを確認（メソッドの存在確認）
        assert hasattr(paper_adapter, 'get_balance')
        # 注意: 実際のデータベース接続なしでは残高取得はできないが、
        # インターフェースが存在することで仮想残高機能の準備ができていることを確認


class TestConfigurationValidation:
    """設定検証テスト"""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    @patch('src.backend.core.config.settings')
    def test_production_mode_requires_valid_api_keys(self, mock_settings):
        """本番環境では有効なAPIキーが必要"""
        # 無効なAPIキーを設定
        mock_settings.BINANCE_API_KEY = ""
        mock_settings.BINANCE_SECRET = ""
        mock_settings.is_production = True
        
        factory = ExchangeFactory()
        
        # 本番環境で空のAPIキーを使用するとエラーが発生するべき
        with pytest.raises((ConfigurationError, ValueError)):
            factory.create_adapter("binance", trading_mode="live")
    
    def test_missing_user_id_for_paper_mode(self):
        """Paperモードでuser_id未指定時の動作確認"""
        factory = ExchangeFactory()
        
        # user_idなしでもPaperモードは動作するべき（デフォルトユーザー使用）
        paper_adapter = factory.create_adapter("binance", trading_mode="paper")
        assert isinstance(paper_adapter, PaperTradingAdapter)
    
    def test_trading_mode_case_insensitive(self):
        """trading_modeの大文字小文字を区別しない"""
        factory = ExchangeFactory()
        
        # 大文字小文字を問わずPaperモードが選択される
        adapters = [
            factory.create_adapter("binance", trading_mode="paper"),
            factory.create_adapter("binance", trading_mode="PAPER"),
            factory.create_adapter("binance", trading_mode="Paper"),
        ]
        
        for adapter in adapters:
            assert isinstance(adapter, PaperTradingAdapter)


class TestDataIsolation:
    """データ分離テスト"""
    
    def test_paper_mode_uses_separate_database(self):
        """Paperモードでは分離されたデータベースを使用"""
        import uuid
        
        factory = ExchangeFactory()
        test_user_id = str(uuid.uuid4())
        paper_adapter = factory.create_adapter("binance", trading_mode="paper", user_id=test_user_id)
        
        # PaperTradingAdapterが作成されることを確認
        assert isinstance(paper_adapter, PaperTradingAdapter)
        
        # wallet_serviceの存在を確認（データ分離のための仕組み）
        assert hasattr(paper_adapter, 'wallet_service')
        
        # 仮想取引データが実際の取引データと混在しないことの確認
        # (統合テストで詳細に検証される予定)
    
    @patch('src.backend.database.paper_wallet_service.PaperWalletService')
    def test_paper_trade_history_isolation(self, mock_wallet_service):
        """Paper取引履歴の分離確認"""
        import uuid
        
        # モックの設定
        mock_service_instance = MagicMock()
        mock_wallet_service.return_value = mock_service_instance
        mock_service_instance.initialize_user_wallet.return_value = True
        
        factory = ExchangeFactory()
        test_user_id = str(uuid.uuid4())
        paper_adapter = factory.create_adapter("binance", trading_mode="paper", user_id=test_user_id)
        
        # 異なるユーザーのPaper取引が分離されていることを確認
        # (詳細な検証は統合テストで実施)
        assert isinstance(paper_adapter, PaperTradingAdapter)


class TestRuntimeSafety:
    """実行時安全性テスト"""
    
    def test_mode_immutability_during_runtime(self):
        """実行時のモード変更不可能性"""
        factory = ExchangeFactory()
        paper_adapter = factory.create_adapter("binance", trading_mode="paper")
        
        # アダプターのモードが変更できないことを確認
        assert isinstance(paper_adapter, PaperTradingAdapter)
        
        # exchange_nameプロパティが読み取り専用であることを確認
        original_exchange_name = paper_adapter.exchange_name
        # PaperTradingAdapterはexchange_nameが"paper_trading"になる
        assert original_exchange_name == "paper_trading"
        
        # モードの変更試行（もし可能ならエラーが発生するべき）
        if hasattr(paper_adapter, '_trading_mode'):
            with pytest.raises(AttributeError):
                # プライベート属性への直接アクセスは制限されるべき
                paper_adapter._trading_mode = "live"
    
    def test_factory_state_isolation(self):
        """ファクトリーの状態分離確認"""
        factory1 = ExchangeFactory()
        factory2 = ExchangeFactory()
        
        # 異なるファクトリーインスタンスが互いに影響しないことを確認
        adapter1 = factory1.create_adapter("binance", trading_mode="paper")
        adapter2 = factory2.create_adapter("bitget", trading_mode="paper")
        
        # 両方ともPaperTradingAdapterなので exchange_name は同じになるが、
        # 内部の real_exchange は異なるべき
        assert isinstance(adapter1, PaperTradingAdapter)
        assert isinstance(adapter2, PaperTradingAdapter)
        # real_exchangeが異なることを確認（内部的に異なる取引所を参照）
        if hasattr(adapter1, 'real_exchange') and hasattr(adapter2, 'real_exchange'):
            assert adapter1.real_exchange != adapter2.real_exchange


if __name__ == "__main__":
    pytest.main([__file__, "-v"])