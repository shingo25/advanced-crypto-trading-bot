"""
注文システムのセキュリティ統合テスト
OrderValidator と SecurityManager の統合を検証
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from src.backend.trading.orders import (
    Order,
    OrderParams,
    OrderFactory,
    OrderCommandFactory,
    OrderValidator,
    SecurityManager,
    OrderType,
    OrderSide,
    OrderStatus,
)


@pytest.fixture
def security_config():
    """セキュリティ設定のテストフィクスチャ"""
    from cryptography.fernet import Fernet
    # 有効なFernet キーを生成
    key = Fernet.generate_key()
    
    return {
        'MASTER_ENCRYPTION_KEY': key,
        'IP_WHITELIST': ['127.0.0.1', '192.168.1.100'],
        'ENABLE_IP_FILTERING': True,
        'RATE_LIMITS': {
            'orders_per_minute': 5,
            'orders_per_hour': 30,
        },
        'ANOMALY_THRESHOLDS': {
            'max_order_value_ratio': 0.1,  # 10%
            'max_hourly_trades': 5,
            'max_price_deviation': 0.05,   # 5%
        }
    }


@pytest.fixture
def mock_exchange_adapter():
    """モック取引所アダプタ"""
    adapter = Mock()
    adapter.get_symbols = AsyncMock(return_value=['BTCUSDT', 'ETHUSDT'])  # 正規化済みシンボル
    adapter.normalize_symbol = Mock(side_effect=lambda x: x.replace('/', ''))
    adapter.fetch_ticker = AsyncMock(return_value=Mock(
        last=45000.0,
        bid=44990.0,
        ask=45010.0
    ))
    adapter.get_balance = AsyncMock(return_value={
        'BTC': 1.0,
        'USDT': 50000.0,
        'ETH': 10.0
    })
    return adapter


@pytest.fixture
def mock_account_service():
    """モックアカウントサービス"""
    service = Mock()
    service.get_balance = AsyncMock(return_value={
        'BTC': 1.0,
        'USDT': 50000.0,
        'ETH': 10.0
    })
    return service


@pytest.fixture
def test_order():
    """テスト用注文"""
    return Order(
        exchange="binance",
        symbol="BTC/USDT",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=Decimal("0.1"),
        price=Decimal("45000")
    )


@pytest.fixture
def test_request_context():
    """テスト用リクエストコンテキスト"""
    return {
        'user_id': 'test_user_123',
        'ip_address': '127.0.0.1',
        'session_id': 'session_abc'
    }


class TestSecurityManagerIntegration:
    """SecurityManagerの統合テスト"""
    
    def test_security_manager_initialization(self, security_config):
        """SecurityManagerの初期化テスト"""
        security_manager = SecurityManager(security_config)
        
        assert security_manager.enable_ip_filtering == True
        assert '127.0.0.1' in security_manager.ip_whitelist
        assert security_manager.rate_limits['orders_per_minute'] == 5
    
    def test_api_key_encryption_decryption(self, security_config):
        """APIキー暗号化・復号化テスト"""
        security_manager = SecurityManager(security_config)
        
        api_key = "test_api_key_12345"
        encrypted = security_manager.encrypt_api_key(api_key)
        decrypted = security_manager.decrypt_api_key(encrypted)
        
        assert decrypted == api_key
        assert encrypted != api_key.encode()  # 暗号化されていることを確認
    
    def test_ip_whitelist_check(self, security_config):
        """IPアドレスホワイトリストテスト"""
        security_manager = SecurityManager(security_config)
        
        # 許可されたIP
        assert security_manager.check_ip_address('127.0.0.1') == True
        assert security_manager.check_ip_address('192.168.1.100') == True
        
        # 許可されていないIP
        assert security_manager.check_ip_address('192.168.1.200') == False
        assert security_manager.check_ip_address('10.0.0.1') == False
    
    def test_rate_limiting(self, security_config):
        """レート制限テスト"""
        security_manager = SecurityManager(security_config)
        user_id = 'test_user'
        
        # 制限以内
        for i in range(5):
            assert security_manager.check_rate_limit(user_id) == True
        
        # 制限超過
        assert security_manager.check_rate_limit(user_id) == False
    
    def test_anomaly_detection_large_order(self, security_config, test_order):
        """異常検知：大額注文テスト"""
        security_manager = SecurityManager(security_config)
        
        # 大額注文（ポートフォリオの50%）
        large_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("10"),  # 10 BTC
            price=Decimal("45000")  # $450,000
        )
        
        portfolio_value = Decimal("500000")  # $500,000
        user_id = "test_user"
        
        is_anomalous = security_manager.check_for_anomalies(
            large_order, user_id, portfolio_value
        )
        
        assert is_anomalous == True  # 10%制限を超えているため異常


class TestOrderValidatorIntegration:
    """OrderValidatorの統合テスト"""
    
    @pytest.mark.asyncio
    async def test_validator_initialization(self, mock_exchange_adapter, mock_account_service):
        """OrderValidatorの初期化テスト"""
        validator = OrderValidator(mock_exchange_adapter, mock_account_service)
        
        assert validator.exchange_adapter == mock_exchange_adapter
        assert validator.account_service == mock_account_service
    
    @pytest.mark.asyncio
    async def test_basic_validation_success(self, mock_exchange_adapter, test_order):
        """基本バリデーション成功テスト"""
        validator = OrderValidator(mock_exchange_adapter)
        
        is_valid, error_msg = await validator.validate(test_order)
        
        assert is_valid == True
        assert error_msg is None
    
    @pytest.mark.asyncio
    async def test_symbol_validation(self, mock_exchange_adapter, test_order):
        """シンボルバリデーションテスト"""
        validator = OrderValidator(mock_exchange_adapter)
        
        # 無効なシンボル
        invalid_order = Order(
            exchange="binance",
            symbol="INVALID/SYMBOL",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000")
        )
        
        is_valid, error_msg = await validator.validate(invalid_order)
        
        assert is_valid == False
        assert "not available" in error_msg
    
    @pytest.mark.asyncio
    async def test_price_deviation_validation(self, mock_exchange_adapter, test_order):
        """価格乖離バリデーションテスト"""
        validator = OrderValidator(mock_exchange_adapter)
        
        # 極端に高い価格
        high_price_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("70000")  # 市場価格45000から55%高い
        )
        
        is_valid, error_msg = await validator.validate(high_price_order)
        
        assert is_valid == False
        assert "deviates" in error_msg


class TestOrderCommandFactoryIntegration:
    """OrderCommandFactoryの統合テスト"""
    
    def test_factory_initialization_with_security(self, security_config):
        """セキュリティ設定付きファクトリ初期化テスト"""
        factory = OrderCommandFactory(security_config)
        
        assert factory._security_manager is not None
        assert isinstance(factory._security_manager, SecurityManager)
    
    @pytest.mark.asyncio
    async def test_create_command_with_security(self, security_config, test_order, mock_exchange_adapter):
        """セキュリティ機能付きコマンド作成テスト"""
        # モックファクトリを作成（実際の取引所接続を避けるため）
        factory = OrderCommandFactory(security_config)
        factory._exchange_adapters['binance_False'] = mock_exchange_adapter
        
        # バリデータも手動で設定
        validator = OrderValidator(mock_exchange_adapter)
        factory._validators['binance_False'] = validator
        
        command = factory.create_order_command(test_order, "create")
        
        assert command.validator is not None
        assert command.security_manager is not None
        assert isinstance(command.validator, OrderValidator)
        assert isinstance(command.security_manager, SecurityManager)


class TestFullIntegrationScenarios:
    """完全統合シナリオテスト"""
    
    @pytest.mark.asyncio
    async def test_successful_order_creation_flow(
        self, 
        security_config, 
        test_order, 
        test_request_context,
        mock_exchange_adapter,
        mock_account_service
    ):
        """正常な注文作成フローテスト"""
        # ファクトリを設定
        factory = OrderCommandFactory(security_config)
        factory._exchange_adapters['binance_False'] = mock_exchange_adapter
        
        validator = OrderValidator(mock_exchange_adapter, mock_account_service)
        factory._validators['binance_False'] = validator
        
        # コマンドを作成
        command = factory.create_order_command(test_order, "create")
        
        # バリデーション実行
        is_valid, error_msg = await command.validate(
            test_request_context, 
            Decimal("100000")  # $100,000ポートフォリオ
        )
        
        assert is_valid == True
        assert error_msg is None
    
    @pytest.mark.asyncio
    async def test_security_rejection_flow(
        self, 
        security_config, 
        test_request_context,
        mock_exchange_adapter,
        mock_account_service
    ):
        """セキュリティ拒否フローテスト"""
        # 禁止IPアドレスに変更
        blocked_context = test_request_context.copy()
        blocked_context['ip_address'] = '10.0.0.1'  # ホワイトリストにない
        
        # 大額注文を作成
        large_order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("20"),  # 20 BTC
            price=Decimal("45000")  # $900,000
        )
        
        # ファクトリを設定
        factory = OrderCommandFactory(security_config)
        factory._exchange_adapters['binance_False'] = mock_exchange_adapter
        
        validator = OrderValidator(mock_exchange_adapter, mock_account_service)
        factory._validators['binance_False'] = validator
        
        # コマンドを作成
        command = factory.create_order_command(large_order, "create")
        
        # バリデーション実行
        is_valid, error_msg = await command.validate(
            blocked_context, 
            Decimal("100000")  # $100,000ポートフォリオ
        )
        
        assert is_valid == False
        assert ("not allowed" in error_msg or "anomaly" in error_msg.lower())
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(
        self, 
        security_config, 
        test_order,
        test_request_context,
        mock_exchange_adapter,
        mock_account_service
    ):
        """レート制限実施テスト"""
        # ファクトリを設定
        factory = OrderCommandFactory(security_config)
        factory._exchange_adapters['binance_False'] = mock_exchange_adapter
        
        validator = OrderValidator(mock_exchange_adapter, mock_account_service)
        factory._validators['binance_False'] = validator
        
        # コマンドを作成
        command = factory.create_order_command(test_order, "create")
        
        # 制限以内の注文
        for i in range(5):
            is_valid, error_msg = await command.validate(
                test_request_context, 
                Decimal("100000")
            )
            assert is_valid == True
        
        # 制限超過
        is_valid, error_msg = await command.validate(
            test_request_context, 
            Decimal("100000")
        )
        
        assert is_valid == False
        assert "rate limit" in error_msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])