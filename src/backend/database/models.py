"""
データベースモデル定義
SQLAlchemy ORM models for orders and trades
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index, JSON, 
    Numeric, String, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class OrderModel(Base):
    """注文テーブルのSQLAlchemyモデル"""
    
    __tablename__ = 'orders'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ユーザー・戦略情報
    user_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(String(100))
    strategy_name = Column(String(200))
    
    # 取引所・シンボル情報
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    
    # 注文詳細
    order_type = Column(
        Enum('market', 'limit', 'stop_loss', 'take_profit', 'oco', name='order_type_enum'),
        nullable=False
    )
    side = Column(Enum('buy', 'sell', name='order_side_enum'), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8))
    stop_price = Column(Numeric(20, 8))
    time_in_force = Column(String(10), default='GTC')
    
    # OCO注文用
    oco_take_profit_price = Column(Numeric(20, 8))
    oco_stop_loss_price = Column(Numeric(20, 8))
    
    # 実行状況
    status = Column(
        Enum('pending', 'submitted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired', 'failed', 
             name='order_status_enum'),
        nullable=False, default='pending'
    )
    filled_quantity = Column(Numeric(20, 8), default=0)
    remaining_quantity = Column(Numeric(20, 8))
    average_fill_price = Column(Numeric(20, 8))
    
    # 取引所情報
    exchange_order_id = Column(String(100))
    client_order_id = Column(String(100))
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    submitted_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # エラー・手数料情報
    error_message = Column(Text)
    error_code = Column(String(50))
    fee_amount = Column(Numeric(20, 8))
    fee_currency = Column(String(10))
    
    # メタデータ
    paper_trading = Column(Boolean, default=False)
    risk_score = Column(Numeric(5, 4))
    order_metadata = Column(JSON)
    
    # リレーションシップ
    trades = relationship("TradeModel", back_populates="order", cascade="all, delete-orphan")
    
    # 制約
    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_quantity_positive'),
        CheckConstraint('price IS NULL OR price > 0', name='chk_price_positive'),
        CheckConstraint('filled_quantity <= quantity', name='chk_filled_lte_quantity'),
        
        # インデックス
        Index('idx_orders_user_id', 'user_id'),
        Index('idx_orders_strategy_id', 'strategy_id'),
        Index('idx_orders_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
        Index('idx_orders_exchange_order_id', 'exchange_order_id'),
        Index('idx_orders_paper_trading', 'paper_trading'),
        Index('idx_orders_user_strategy_created', 'user_id', 'strategy_id', 'created_at'),
    )
    
    @validates('quantity', 'price')
    def validate_positive_numbers(self, key, value):
        """正数バリデーション"""
        if value is not None and value <= 0:
            raise ValueError(f"{key} must be positive")
        return value
    
    @validates('order_type')
    def validate_order_type(self, key, value):
        """注文タイプバリデーション"""
        valid_types = ['market', 'limit', 'stop_loss', 'take_profit', 'oco']
        if value not in valid_types:
            raise ValueError(f"Invalid order type: {value}")
        return value
    
    @validates('side')
    def validate_side(self, key, value):
        """売買方向バリデーション"""
        if value not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {value}")
        return value
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'quantity': float(self.quantity) if self.quantity else None,
            'price': float(self.price) if self.price else None,
            'stop_price': float(self.stop_price) if self.stop_price else None,
            'status': self.status,
            'filled_quantity': float(self.filled_quantity) if self.filled_quantity else 0,
            'remaining_quantity': float(self.remaining_quantity) if self.remaining_quantity else None,
            'average_fill_price': float(self.average_fill_price) if self.average_fill_price else None,
            'exchange_order_id': self.exchange_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'fee_amount': float(self.fee_amount) if self.fee_amount else None,
            'fee_currency': self.fee_currency,
            'paper_trading': self.paper_trading,
            'risk_score': float(self.risk_score) if self.risk_score else None,
            'metadata': self.order_metadata,
        }
    
    def is_active(self) -> bool:
        """アクティブな注文かどうか"""
        return self.status in ['submitted', 'partially_filled']
    
    def is_complete(self) -> bool:
        """完了した注文かどうか"""
        return self.status in ['filled', 'cancelled', 'rejected', 'expired', 'failed']
    
    def update_fill(self, fill_quantity: Decimal, fill_price: Decimal, fee: Optional[Decimal] = None):
        """約定情報を更新"""
        self.filled_quantity = (self.filled_quantity or 0) + fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # 平均約定価格を計算
        if self.average_fill_price is None:
            self.average_fill_price = fill_price
        else:
            previous_value = self.average_fill_price * (self.filled_quantity - fill_quantity)
            new_value = fill_price * fill_quantity
            self.average_fill_price = (previous_value + new_value) / self.filled_quantity
        
        # 手数料を加算
        if fee is not None:
            self.fee_amount = (self.fee_amount or 0) + fee
        
        # ステータスを更新
        if self.remaining_quantity <= 0:
            self.status = 'filled'
            self.filled_at = datetime.now(timezone.utc)
        else:
            self.status = 'partially_filled'
    
    def __repr__(self):
        return f"<OrderModel(id={self.id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity}, status={self.status})>"


class TradeModel(Base):
    """取引テーブルのSQLAlchemyモデル"""
    
    __tablename__ = 'trades'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 関連注文
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    
    # ユーザー・戦略情報
    user_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(String(100))
    strategy_name = Column(String(200))
    
    # 取引所・シンボル情報
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    
    # 約定詳細
    side = Column(Enum('buy', 'sell', name='trade_side_enum'), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    
    # 手数料
    fee_amount = Column(Numeric(20, 8), default=0)
    fee_currency = Column(String(10))
    
    # 取引所情報
    exchange_trade_id = Column(String(100))
    exchange_order_id = Column(String(100))
    
    # タイムスタンプ
    executed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # メタデータ
    is_maker = Column(Boolean)
    paper_trading = Column(Boolean, default=False)
    liquidity_provider = Column(String(50))
    slippage = Column(Numeric(10, 6))
    market_impact = Column(Numeric(10, 6))
    trade_metadata = Column(JSON)
    
    # リレーションシップ
    order = relationship("OrderModel", back_populates="trades")
    
    # 制約
    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_trade_quantity_positive'),
        CheckConstraint('price > 0', name='chk_trade_price_positive'),
        
        # インデックス
        Index('idx_trades_order_id', 'order_id'),
        Index('idx_trades_user_id', 'user_id'),
        Index('idx_trades_strategy_id', 'strategy_id'),
        Index('idx_trades_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_trades_executed_at', 'executed_at'),
        Index('idx_trades_exchange_trade_id', 'exchange_trade_id'),
        Index('idx_trades_paper_trading', 'paper_trading'),
        Index('idx_trades_user_symbol_executed', 'user_id', 'symbol', 'executed_at'),
        Index('idx_portfolio_lookup', 'user_id', 'exchange', 'symbol', 'paper_trading'),
    )
    
    @validates('quantity', 'price')
    def validate_positive_numbers(self, key, value):
        """正数バリデーション"""
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        return value
    
    @validates('side')
    def validate_side(self, key, value):
        """売買方向バリデーション"""
        if value not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {value}")
        return value
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'order_id': str(self.order_id),
            'user_id': str(self.user_id),
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'fee_amount': float(self.fee_amount) if self.fee_amount else 0,
            'fee_currency': self.fee_currency,
            'exchange_trade_id': self.exchange_trade_id,
            'exchange_order_id': self.exchange_order_id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_maker': self.is_maker,
            'paper_trading': self.paper_trading,
            'slippage': float(self.slippage) if self.slippage else None,
            'market_impact': float(self.market_impact) if self.market_impact else None,
            'metadata': self.trade_metadata,
        }
    
    def get_trade_value(self) -> Decimal:
        """取引金額を取得"""
        return self.quantity * self.price
    
    def get_net_value(self) -> Decimal:
        """手数料込みの純取引金額"""
        trade_value = self.get_trade_value()
        if self.side == 'buy':
            return -(trade_value + (self.fee_amount or 0))
        else:
            return trade_value - (self.fee_amount or 0)
    
    def __repr__(self):
        return f"<TradeModel(id={self.id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity}, price={self.price})>"


# データベース統計用のマテリアライズドビュー（オプション）
class TradingStatistics(Base):
    """取引統計テーブル（日次集計）"""
    
    __tablename__ = 'trading_statistics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(String(100))
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    paper_trading = Column(Boolean, default=False)
    trade_date = Column(DateTime(timezone=True), nullable=False)
    
    # 集計データ
    trade_count = Column(Numeric(10, 0), default=0)
    total_volume = Column(Numeric(20, 8), default=0)
    total_fees = Column(Numeric(20, 8), default=0)
    avg_price = Column(Numeric(20, 8))
    min_price = Column(Numeric(20, 8))
    max_price = Column(Numeric(20, 8))
    buy_count = Column(Numeric(10, 0), default=0)
    sell_count = Column(Numeric(10, 0), default=0)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_statistics_user_date', 'user_id', 'trade_date'),
        Index('idx_statistics_strategy_date', 'strategy_id', 'trade_date'),
        Index('idx_statistics_symbol_date', 'symbol', 'trade_date'),
    )
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'strategy_id': self.strategy_id,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'paper_trading': self.paper_trading,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'trade_count': int(self.trade_count) if self.trade_count else 0,
            'total_volume': float(self.total_volume) if self.total_volume else 0,
            'total_fees': float(self.total_fees) if self.total_fees else 0,
            'avg_price': float(self.avg_price) if self.avg_price else None,
            'min_price': float(self.min_price) if self.min_price else None,
            'max_price': float(self.max_price) if self.max_price else None,
            'buy_count': int(self.buy_count) if self.buy_count else 0,
            'sell_count': int(self.sell_count) if self.sell_count else 0,
        }


# Paper Trading用ウォレットモデル
class PaperWalletModel(Base):
    """Paper Trading用仮想ウォレットモデル"""
    
    __tablename__ = 'paper_wallets'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ユーザー情報
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # 資産情報
    asset = Column(String(20), nullable=False)
    balance = Column(Numeric(20, 8), nullable=False, default=0)
    locked_balance = Column(Numeric(20, 8), nullable=False, default=0)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    transactions = relationship("PaperWalletTransactionModel", back_populates="wallet", cascade="all, delete-orphan")
    
    # 制約
    __table_args__ = (
        CheckConstraint('balance >= 0', name='chk_balance_non_negative'),
        CheckConstraint('locked_balance >= 0', name='chk_locked_balance_non_negative'),
        CheckConstraint('locked_balance <= balance', name='chk_locked_lte_balance'),
        
        # インデックス
        Index('idx_paper_wallets_user_id', 'user_id'),
        Index('idx_paper_wallets_asset', 'asset'),
        Index('idx_paper_wallets_user_asset', 'user_id', 'asset'),
        
        # ユニーク制約
        {'extend_existing': True}
    )
    
    @validates('balance', 'locked_balance')
    def validate_non_negative(self, key, value):
        """非負数バリデーション"""
        if value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value
    
    def get_available_balance(self) -> Decimal:
        """利用可能残高を取得"""
        return self.balance - self.locked_balance
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'asset': self.asset,
            'balance': float(self.balance),
            'locked_balance': float(self.locked_balance),
            'available_balance': float(self.get_available_balance()),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<PaperWalletModel(user_id={self.user_id}, asset={self.asset}, balance={self.balance})>"


class PaperWalletTransactionModel(Base):
    """Paper Trading用ウォレット取引履歴モデル"""
    
    __tablename__ = 'paper_wallet_transactions'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 関連ウォレット
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('paper_wallets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    asset = Column(String(20), nullable=False)
    
    # 取引詳細
    transaction_type = Column(
        Enum('deposit', 'withdraw', 'trade_buy', 'trade_sell', 'fee', 'lock', 'unlock', 'reset', 
             name='paper_transaction_type_enum'),
        nullable=False
    )
    amount = Column(Numeric(20, 8), nullable=False)
    balance_before = Column(Numeric(20, 8), nullable=False)
    balance_after = Column(Numeric(20, 8), nullable=False)
    
    # 関連情報
    related_order_id = Column(String(100))
    related_trade_id = Column(String(100))
    description = Column(Text)
    transaction_metadata = Column(JSON)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # リレーションシップ
    wallet = relationship("PaperWalletModel", back_populates="transactions")
    
    # 制約
    __table_args__ = (
        CheckConstraint('amount != 0', name='chk_amount_not_zero'),
        
        # インデックス
        Index('idx_paper_wallet_transactions_wallet_id', 'wallet_id'),
        Index('idx_paper_wallet_transactions_user_id', 'user_id'),
        Index('idx_paper_wallet_transactions_asset', 'asset'),
        Index('idx_paper_wallet_transactions_type', 'transaction_type'),
        Index('idx_paper_wallet_transactions_created_at', 'created_at'),
        Index('idx_paper_wallet_transactions_order_id', 'related_order_id'),
        Index('idx_paper_wallet_transactions_user_asset_created', 'user_id', 'asset', 'created_at'),
    )
    
    @validates('transaction_type')
    def validate_transaction_type(self, key, value):
        """取引タイプバリデーション"""
        valid_types = ['deposit', 'withdraw', 'trade_buy', 'trade_sell', 'fee', 'lock', 'unlock', 'reset']
        if value not in valid_types:
            raise ValueError(f"Invalid transaction type: {value}")
        return value
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'wallet_id': str(self.wallet_id),
            'user_id': str(self.user_id),
            'asset': self.asset,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'balance_before': float(self.balance_before),
            'balance_after': float(self.balance_after),
            'related_order_id': self.related_order_id,
            'related_trade_id': self.related_trade_id,
            'description': self.description,
            'metadata': self.transaction_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<PaperWalletTransactionModel(user_id={self.user_id}, asset={self.asset}, type={self.transaction_type}, amount={self.amount})>"


class PaperWalletDefaultModel(Base):
    """Paper Trading用デフォルト設定モデル"""
    
    __tablename__ = 'paper_wallet_defaults'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 設定情報
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    default_balances = Column(JSON, nullable=False)
    
    # メタデータ
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'default_balances': self.default_balances,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<PaperWalletDefaultModel(name={self.name}, active={self.is_active})>"


# データベース接続・セッション管理用のユーティリティクラス
class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, database_url: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """テーブルを作成"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """テーブルを削除"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self):
        """セッションを取得"""
        return self.SessionLocal()
    
    def get_engine(self):
        """エンジンを取得"""
        return self.engine