"""
注文システムのデータモデル
取引所間で統一されたOrderとTradeの表現
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class OrderType(Enum):
    """注文タイプ"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    OCO = "oco"  # One-Cancels-Other


class OrderSide(Enum):
    """注文方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """注文状態"""
    PENDING = "pending"        # 作成中
    SUBMITTED = "submitted"    # 取引所に送信済み
    PARTIALLY_FILLED = "partially_filled"  # 部分約定
    FILLED = "filled"          # 完全約定
    CANCELLED = "cancelled"    # キャンセル
    REJECTED = "rejected"      # 拒否
    EXPIRED = "expired"        # 期限切れ
    FAILED = "failed"          # システムエラー


class TimeInForce(Enum):
    """注文有効期限"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    ALO = "alo"  # Add Liquidity Only


class OrderParams(BaseModel):
    """注文パラメータ"""
    exchange: str = Field(..., description="取引所名")
    symbol: str = Field(..., description="取引ペア（例: BTC/USDT）")
    order_type: OrderType = Field(..., description="注文タイプ")
    side: OrderSide = Field(..., description="売買方向")
    amount: Decimal = Field(..., gt=0, description="注文数量")
    price: Optional[Decimal] = Field(None, gt=0, description="価格（成行の場合はNone）")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="ストップ価格")
    time_in_force: TimeInForce = Field(TimeInForce.GTC, description="注文有効期限")
    
    # OCO注文用
    oco_take_profit_price: Optional[Decimal] = Field(None, description="利確価格")
    oco_stop_loss_price: Optional[Decimal] = Field(None, description="損切価格")
    
    # メタデータ
    strategy_name: Optional[str] = Field(None, description="戦略名")
    client_order_id: Optional[str] = Field(None, description="クライアント注文ID")
    
    @field_validator('price')
    @classmethod
    def validate_price_for_limit_orders(cls, v, info):
        """指値注文では価格が必須"""
        if info.data.get('order_type') == OrderType.LIMIT and v is None:
            raise ValueError("Limit orders require a price")
        return v
    
    @field_validator('stop_price')
    @classmethod
    def validate_stop_price(cls, v, info):
        """ストップ注文では停止価格が必須"""
        order_type = info.data.get('order_type')
        if order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT] and v is None:
            raise ValueError(f"{order_type.value} orders require a stop_price")
        return v


class Order(BaseModel):
    """注文の完全な表現"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="内部注文ID")
    exchange_order_id: Optional[str] = Field(None, description="取引所の注文ID")
    
    # 注文パラメータ
    exchange: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    amount: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # OCO注文用
    oco_take_profit_price: Optional[Decimal] = None
    oco_stop_loss_price: Optional[Decimal] = None
    
    # 実行状況
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: Decimal = Field(default=Decimal("0"), description="約定済み数量")
    remaining_amount: Optional[Decimal] = Field(default=None, description="残り数量")
    average_fill_price: Optional[Decimal] = Field(None, description="平均約定価格")
    
    # メタデータ
    strategy_name: Optional[str] = None
    client_order_id: Optional[str] = None
    
    # タイムスタンプ
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # エラー情報
    error_message: Optional[str] = None
    
    # 手数料情報
    fee_amount: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.remaining_amount is None:
            self.remaining_amount = self.amount
    
    @classmethod
    def from_params(cls, params: OrderParams) -> "Order":
        """OrderParamsから注文を作成"""
        return cls(
            exchange=params.exchange,
            symbol=params.symbol,
            order_type=params.order_type,
            side=params.side,
            amount=params.amount,
            price=params.price,
            stop_price=params.stop_price,
            time_in_force=params.time_in_force,
            oco_take_profit_price=params.oco_take_profit_price,
            oco_stop_loss_price=params.oco_stop_loss_price,
            strategy_name=params.strategy_name,
            client_order_id=params.client_order_id,
        )
    
    def is_complete(self) -> bool:
        """注文が完了状態かチェック"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED
        ]
    
    def is_active(self) -> bool:
        """注文がアクティブ状態かチェック"""
        return self.status in [
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    def update_fill(self, fill_amount: Decimal, fill_price: Decimal, fee: Optional[Decimal] = None):
        """約定情報を更新"""
        self.filled_amount += fill_amount
        self.remaining_amount = self.amount - self.filled_amount
        
        # 平均約定価格を計算
        if self.average_fill_price is None:
            self.average_fill_price = fill_price
        else:
            total_value = (self.average_fill_price * (self.filled_amount - fill_amount) + 
                          fill_price * fill_amount)
            self.average_fill_price = total_value / self.filled_amount
        
        # 手数料を加算
        if fee is not None:
            if self.fee_amount is None:
                self.fee_amount = fee
            else:
                self.fee_amount += fee
        
        # ステータスを更新
        if self.remaining_amount <= Decimal("0"):
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.now(timezone.utc)
        else:
            self.status = OrderStatus.PARTIALLY_FILLED


class Trade(BaseModel):
    """個別の約定情報"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="約定ID")
    order_id: str = Field(..., description="関連する注文ID")
    exchange_trade_id: Optional[str] = Field(None, description="取引所の約定ID")
    
    # 約定詳細
    exchange: str
    symbol: str
    side: OrderSide
    amount: Decimal = Field(..., gt=0, description="約定数量")
    price: Decimal = Field(..., gt=0, description="約定価格")
    
    # 手数料
    fee_amount: Optional[Decimal] = Field(None, description="手数料")
    fee_currency: Optional[str] = Field(None, description="手数料通貨")
    
    # タイムスタンプ
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # メタデータ
    strategy_name: Optional[str] = None
    is_maker: Optional[bool] = Field(None, description="メイカー約定かどうか")


class OrderResult(BaseModel):
    """注文実行結果"""
    success: bool
    order: Optional[Order] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def success_result(cls, order: Order) -> "OrderResult":
        return cls(success=True, order=order)
    
    @classmethod
    def error_result(cls, error_message: str, error_code: Optional[str] = None) -> "OrderResult":
        return cls(success=False, error_message=error_message, error_code=error_code)