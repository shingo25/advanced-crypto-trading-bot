#!/usr/bin/env python3
"""
トレーディングエンジンのデバッグ
"""

# テスト用のパスを追加（pytest.iniで設定済みのため削除）
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def debug_position_management():
    """ポジション管理のデバッグ"""
    from src.backend.trading.engine import OrderSide, OrderType, TradingEngine

    # エンジンを作成
    engine = TradingEngine()

    # 価格を設定
    engine.update_price("BTCUSDT", 50000.0)
    print(f"Price data: {engine.price_data}")

    # 買い注文を作成
    buy_order = engine.create_order(symbol="BTCUSDT", side=OrderSide.BUY, order_type=OrderType.MARKET, amount=1.0)
    print(f"Buy order: {buy_order}")
    print(f"Buy order filled: {buy_order.is_filled()}")

    # ポジションを確認
    position = engine.get_position("BTCUSDT")
    print(f"Position after buy: {position}")

    if position:
        print(f"Position symbol: {position.symbol}")
        print(f"Position side: {position.side}")
        print(f"Position amount: {position.amount}")
        print(f"Position entry price: {position.entry_price}")

    # 価格を更新
    engine.update_price("BTCUSDT", 52000.0)
    print(f"Updated price: {engine.price_data['BTCUSDT']}")

    if position:
        print(f"Position unrealized PnL: {position.unrealized_pnl}")

    # ポジションを閉じる
    print("Closing position...")
    success = engine.close_position("BTCUSDT")
    print(f"Close position success: {success}")

    # ポジションが削除されたことを確認
    position_after_close = engine.get_position("BTCUSDT")
    print(f"Position after closing: {position_after_close}")

    print(f"All positions: {engine.get_all_positions()}")


if __name__ == "__main__":
    debug_position_management()
