-- 注文・取引データベーススキーマ定義
-- PostgreSQL用スキーマ（SQLiteとの互換性も考慮）

-- 注文テーブル
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ユーザー・戦略情報
    user_id UUID NOT NULL,
    strategy_id VARCHAR(100),
    strategy_name VARCHAR(200),
    
    -- 取引所・シンボル情報
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    
    -- 注文詳細
    order_type VARCHAR(20) NOT NULL, -- 'market', 'limit', 'stop_loss', 'take_profit', 'oco'
    side VARCHAR(10) NOT NULL,       -- 'buy', 'sell'
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8),            -- limit/stop注文の場合
    stop_price DECIMAL(20, 8),       -- stop注文の場合
    time_in_force VARCHAR(10) DEFAULT 'GTC', -- 'GTC', 'IOC', 'FOK', 'ALO'
    
    -- OCO注文用
    oco_take_profit_price DECIMAL(20, 8),
    oco_stop_loss_price DECIMAL(20, 8),
    
    -- 実行状況
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'submitted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired', 'failed'
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    remaining_quantity DECIMAL(20, 8),
    average_fill_price DECIMAL(20, 8),
    
    -- 取引所情報
    exchange_order_id VARCHAR(100),
    client_order_id VARCHAR(100),
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- エラー・手数料情報
    error_message TEXT,
    error_code VARCHAR(50),
    fee_amount DECIMAL(20, 8),
    fee_currency VARCHAR(10),
    
    -- メタデータ
    paper_trading BOOLEAN DEFAULT FALSE,
    risk_score DECIMAL(5, 4),        -- リスクスコア (0.0000-1.0000)
    metadata JSONB,                  -- 追加のメタデータ
    
    -- 制約
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_price_positive CHECK (price IS NULL OR price > 0),
    CONSTRAINT chk_filled_lte_quantity CHECK (filled_quantity <= quantity),
    CONSTRAINT chk_order_type CHECK (order_type IN ('market', 'limit', 'stop_loss', 'take_profit', 'oco')),
    CONSTRAINT chk_side CHECK (side IN ('buy', 'sell')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'submitted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired', 'failed'))
);

-- 取引（約定）テーブル
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 関連注文
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    
    -- ユーザー・戦略情報
    user_id UUID NOT NULL,
    strategy_id VARCHAR(100),
    strategy_name VARCHAR(200),
    
    -- 取引所・シンボル情報
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    
    -- 約定詳細
    side VARCHAR(10) NOT NULL,       -- 'buy', 'sell'
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    
    -- 手数料
    fee_amount DECIMAL(20, 8) DEFAULT 0,
    fee_currency VARCHAR(10),
    
    -- 取引所情報
    exchange_trade_id VARCHAR(100),
    exchange_order_id VARCHAR(100),
    
    -- タイムスタンプ
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- メタデータ
    is_maker BOOLEAN,                -- メイカー取引かどうか
    paper_trading BOOLEAN DEFAULT FALSE,
    liquidity_provider VARCHAR(50),  -- 流動性プロバイダー
    slippage DECIMAL(10, 6),         -- スリッページ（%）
    market_impact DECIMAL(10, 6),    -- マーケットインパクト（%）
    metadata JSONB,
    
    -- 制約
    CONSTRAINT chk_trade_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_trade_price_positive CHECK (price > 0),
    CONSTRAINT chk_trade_side CHECK (side IN ('buy', 'sell'))
);

-- ポジション集計ビュー（リアルタイム計算用）
CREATE OR REPLACE VIEW portfolio_positions AS
SELECT 
    user_id,
    strategy_id,
    strategy_name,
    exchange,
    symbol,
    SUM(CASE WHEN side = 'buy' THEN quantity ELSE -quantity END) as net_quantity,
    AVG(CASE WHEN side = 'buy' THEN price ELSE NULL END) as avg_buy_price,
    AVG(CASE WHEN side = 'sell' THEN price ELSE NULL END) as avg_sell_price,
    SUM(CASE WHEN side = 'buy' THEN quantity * price ELSE -quantity * price END) as net_value,
    COUNT(*) as trade_count,
    MIN(executed_at) as first_trade,
    MAX(executed_at) as last_trade,
    paper_trading
FROM trades 
GROUP BY user_id, strategy_id, strategy_name, exchange, symbol, paper_trading
HAVING SUM(CASE WHEN side = 'buy' THEN quantity ELSE -quantity END) != 0;

-- PnL計算ビュー
CREATE OR REPLACE VIEW trade_pnl AS
SELECT 
    t.id,
    t.order_id,
    t.user_id,
    t.strategy_id,
    t.exchange,
    t.symbol,
    t.side,
    t.quantity,
    t.price,
    t.executed_at,
    t.fee_amount,
    t.paper_trading,
    -- 実現損益計算（簡略化版）
    CASE 
        WHEN t.side = 'sell' THEN 
            (t.quantity * t.price) - t.fee_amount
        ELSE 
            -(t.quantity * t.price) - t.fee_amount
    END as realized_pnl,
    -- 取引コスト
    (t.quantity * t.price * 0.001) + COALESCE(t.fee_amount, 0) as trading_cost
FROM trades t;

-- インデックス作成（パフォーマンス最適化）

-- 注文テーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_strategy_id ON orders(strategy_id);
CREATE INDEX IF NOT EXISTS idx_orders_exchange_symbol ON orders(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_exchange_order_id ON orders(exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_paper_trading ON orders(paper_trading);

-- 取引テーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(order_id);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_exchange_symbol ON trades(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at);
CREATE INDEX IF NOT EXISTS idx_trades_exchange_trade_id ON trades(exchange_trade_id);
CREATE INDEX IF NOT EXISTS idx_trades_paper_trading ON trades(paper_trading);

-- 複合インデックス（よく使用されるクエリ用）
CREATE INDEX IF NOT EXISTS idx_orders_user_strategy_created ON orders(user_id, strategy_id, created_at);
CREATE INDEX IF NOT EXISTS idx_trades_user_symbol_executed ON trades(user_id, symbol, executed_at);
CREATE INDEX IF NOT EXISTS idx_portfolio_lookup ON trades(user_id, exchange, symbol, paper_trading);

-- パーティション（大量データ対応、オプション）
-- 日付別パーティショニングの例（PostgreSQLの場合）
-- CREATE TABLE orders_2024 PARTITION OF orders FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- トリガー関数（updated_atの自動更新）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガー設定
CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- サンプルデータ挿入用関数（テスト用）
CREATE OR REPLACE FUNCTION insert_sample_order(
    p_user_id UUID,
    p_strategy_id VARCHAR DEFAULT 'sample_strategy',
    p_exchange VARCHAR DEFAULT 'binance',
    p_symbol VARCHAR DEFAULT 'BTC/USDT',
    p_side VARCHAR DEFAULT 'buy',
    p_quantity DECIMAL DEFAULT 0.001,
    p_price DECIMAL DEFAULT 50000.0,
    p_paper_trading BOOLEAN DEFAULT TRUE
) RETURNS UUID AS $$
DECLARE
    order_id UUID;
BEGIN
    INSERT INTO orders (
        user_id, strategy_id, exchange, symbol, 
        order_type, side, quantity, price, paper_trading
    ) VALUES (
        p_user_id, p_strategy_id, p_exchange, p_symbol,
        'limit', p_side, p_quantity, p_price, p_paper_trading
    ) RETURNING id INTO order_id;
    
    RETURN order_id;
END;
$$ LANGUAGE plpgsql;

-- 統計・パフォーマンス分析用ビュー
CREATE OR REPLACE VIEW trading_statistics AS
SELECT 
    user_id,
    strategy_id,
    exchange,
    symbol,
    paper_trading,
    DATE_TRUNC('day', executed_at) as trade_date,
    COUNT(*) as trade_count,
    SUM(quantity * price) as total_volume,
    SUM(fee_amount) as total_fees,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(CASE WHEN side = 'buy' THEN 1 END) as buy_count,
    COUNT(CASE WHEN side = 'sell' THEN 1 END) as sell_count
FROM trades
GROUP BY user_id, strategy_id, exchange, symbol, paper_trading, DATE_TRUNC('day', executed_at)
ORDER BY trade_date DESC;