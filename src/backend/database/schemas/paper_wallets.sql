-- Paper Trading用仮想ウォレットテーブル
-- ユーザー毎の仮想残高を管理

-- 仮想ウォレットテーブル
CREATE TABLE IF NOT EXISTS paper_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ユーザー情報
    user_id UUID NOT NULL,
    
    -- 資産情報
    asset VARCHAR(20) NOT NULL,        -- BTC, ETH, USDT, BNB, etc.
    balance DECIMAL(20, 8) NOT NULL DEFAULT 0,    -- 総残高
    locked_balance DECIMAL(20, 8) NOT NULL DEFAULT 0,  -- ロック残高（注文中）
    
    -- メタデータ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 制約
    CONSTRAINT chk_balance_non_negative CHECK (balance >= 0),
    CONSTRAINT chk_locked_balance_non_negative CHECK (locked_balance >= 0),
    CONSTRAINT chk_locked_lte_balance CHECK (locked_balance <= balance),
    CONSTRAINT unique_user_asset UNIQUE (user_id, asset)
);

-- ウォレット取引履歴テーブル（監査ログ用）
CREATE TABLE IF NOT EXISTS paper_wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 関連ウォレット
    wallet_id UUID REFERENCES paper_wallets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    asset VARCHAR(20) NOT NULL,
    
    -- 取引詳細
    transaction_type VARCHAR(20) NOT NULL, -- 'deposit', 'withdraw', 'trade_buy', 'trade_sell', 'fee', 'lock', 'unlock'
    amount DECIMAL(20, 8) NOT NULL,        -- 変動量（正負両方）
    balance_before DECIMAL(20, 8) NOT NULL, -- 取引前残高
    balance_after DECIMAL(20, 8) NOT NULL,  -- 取引後残高
    
    -- 関連情報
    related_order_id VARCHAR(100),         -- 関連注文ID
    related_trade_id VARCHAR(100),         -- 関連取引ID
    description TEXT,                      -- 説明
    metadata JSONB,                        -- 追加データ
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 制約
    CONSTRAINT chk_amount_not_zero CHECK (amount != 0),
    CONSTRAINT chk_transaction_type CHECK (
        transaction_type IN ('deposit', 'withdraw', 'trade_buy', 'trade_sell', 'fee', 'lock', 'unlock', 'reset')
    )
);

-- デフォルト残高設定テーブル
CREATE TABLE IF NOT EXISTS paper_wallet_defaults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 設定名
    name VARCHAR(100) NOT NULL UNIQUE,     -- 'beginner', 'advanced', 'whale', etc.
    description TEXT,
    
    -- デフォルト残高設定（JSON）
    default_balances JSONB NOT NULL,       -- {"USDT": 100000, "BTC": 0, "ETH": 0}
    
    -- メタデータ
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_paper_wallets_user_id ON paper_wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_wallets_asset ON paper_wallets(asset);
CREATE INDEX IF NOT EXISTS idx_paper_wallets_user_asset ON paper_wallets(user_id, asset);

CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_wallet_id ON paper_wallet_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_user_id ON paper_wallet_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_asset ON paper_wallet_transactions(asset);
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_type ON paper_wallet_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_created_at ON paper_wallet_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_order_id ON paper_wallet_transactions(related_order_id);

-- 複合インデックス
CREATE INDEX IF NOT EXISTS idx_paper_wallet_transactions_user_asset_created ON paper_wallet_transactions(user_id, asset, created_at);

-- トリガー（updated_atの自動更新）
CREATE TRIGGER update_paper_wallets_updated_at 
    BEFORE UPDATE ON paper_wallets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_wallet_defaults_updated_at 
    BEFORE UPDATE ON paper_wallet_defaults 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- デフォルト設定データの挿入
INSERT INTO paper_wallet_defaults (name, description, default_balances) VALUES
('beginner', '初心者向け設定（10万USDT）', '{"USDT": 100000, "BTC": 0, "ETH": 0, "BNB": 0}'),
('intermediate', '中級者向け設定（50万USDT）', '{"USDT": 500000, "BTC": 0, "ETH": 0, "BNB": 0}'),
('advanced', '上級者向け設定（100万USDT）', '{"USDT": 1000000, "BTC": 0, "ETH": 0, "BNB": 0}'),
('crypto_heavy', '暗号通貨重視設定', '{"USDT": 50000, "BTC": 2, "ETH": 20, "BNB": 100}'),
('minimal', 'ミニマル設定（1万USDT）', '{"USDT": 10000, "BTC": 0, "ETH": 0}')
ON CONFLICT (name) DO NOTHING;

-- ユーザーウォレット初期化関数
CREATE OR REPLACE FUNCTION initialize_paper_wallet(
    p_user_id UUID,
    p_default_setting VARCHAR DEFAULT 'beginner'
) RETURNS BOOLEAN AS $$
DECLARE
    default_config RECORD;
    asset_key TEXT;
    asset_balance NUMERIC;
BEGIN
    -- デフォルト設定を取得
    SELECT * INTO default_config 
    FROM paper_wallet_defaults 
    WHERE name = p_default_setting AND is_active = TRUE;
    
    IF default_config IS NULL THEN
        RAISE EXCEPTION 'Default setting not found: %', p_default_setting;
    END IF;
    
    -- 既存ウォレットをクリア
    DELETE FROM paper_wallets WHERE user_id = p_user_id;
    
    -- デフォルト残高を設定
    FOR asset_key, asset_balance IN SELECT * FROM jsonb_each_text(default_config.default_balances)
    LOOP
        INSERT INTO paper_wallets (user_id, asset, balance, locked_balance)
        VALUES (p_user_id, asset_key, asset_balance::NUMERIC, 0);
        
        -- 初期化取引ログを作成
        INSERT INTO paper_wallet_transactions (
            wallet_id, user_id, asset, transaction_type, amount, 
            balance_before, balance_after, description
        ) SELECT 
            pw.id, p_user_id, asset_key, 'deposit', asset_balance::NUMERIC,
            0, asset_balance::NUMERIC, 
            'Initial deposit from ' || p_default_setting || ' setting'
        FROM paper_wallets pw 
        WHERE pw.user_id = p_user_id AND pw.asset = asset_key;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 残高更新関数（アトミックな残高操作）
CREATE OR REPLACE FUNCTION update_paper_wallet_balance(
    p_user_id UUID,
    p_asset VARCHAR,
    p_amount DECIMAL,
    p_transaction_type VARCHAR,
    p_related_order_id VARCHAR DEFAULT NULL,
    p_description TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    wallet_record RECORD;
    new_balance DECIMAL;
    transaction_id UUID;
BEGIN
    -- ウォレットを取得（行ロック）
    SELECT * INTO wallet_record
    FROM paper_wallets 
    WHERE user_id = p_user_id AND asset = p_asset
    FOR UPDATE;
    
    -- ウォレットが存在しない場合は作成
    IF wallet_record IS NULL THEN
        INSERT INTO paper_wallets (user_id, asset, balance, locked_balance)
        VALUES (p_user_id, p_asset, 0, 0);
        
        SELECT * INTO wallet_record
        FROM paper_wallets 
        WHERE user_id = p_user_id AND asset = p_asset;
    END IF;
    
    -- 新しい残高を計算
    new_balance := wallet_record.balance + p_amount;
    
    -- 残高が負になる場合はエラー
    IF new_balance < 0 THEN
        RAISE EXCEPTION 'Insufficient balance: current=%, requested=%', wallet_record.balance, p_amount;
    END IF;
    
    -- 残高を更新
    UPDATE paper_wallets 
    SET balance = new_balance, updated_at = NOW()
    WHERE id = wallet_record.id;
    
    -- 取引ログを作成
    INSERT INTO paper_wallet_transactions (
        wallet_id, user_id, asset, transaction_type, amount,
        balance_before, balance_after, related_order_id, description
    ) VALUES (
        wallet_record.id, p_user_id, p_asset, p_transaction_type, p_amount,
        wallet_record.balance, new_balance, p_related_order_id, p_description
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ロック残高更新関数
CREATE OR REPLACE FUNCTION update_paper_wallet_locked_balance(
    p_user_id UUID,
    p_asset VARCHAR,
    p_lock_amount DECIMAL,
    p_related_order_id VARCHAR DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    wallet_record RECORD;
    new_locked_balance DECIMAL;
BEGIN
    -- ウォレットを取得（行ロック）
    SELECT * INTO wallet_record
    FROM paper_wallets 
    WHERE user_id = p_user_id AND asset = p_asset
    FOR UPDATE;
    
    IF wallet_record IS NULL THEN
        RAISE EXCEPTION 'Wallet not found for user % and asset %', p_user_id, p_asset;
    END IF;
    
    -- 新しいロック残高を計算
    new_locked_balance := wallet_record.locked_balance + p_lock_amount;
    
    -- ロック残高が利用可能残高を超える場合はエラー
    IF new_locked_balance > wallet_record.balance THEN
        RAISE EXCEPTION 'Insufficient available balance: total=%, locked=%, requested=%', 
            wallet_record.balance, wallet_record.locked_balance, p_lock_amount;
    END IF;
    
    -- ロック残高が負になる場合はエラー
    IF new_locked_balance < 0 THEN
        RAISE EXCEPTION 'Invalid locked balance: current=%, requested=%', 
            wallet_record.locked_balance, p_lock_amount;
    END IF;
    
    -- ロック残高を更新
    UPDATE paper_wallets 
    SET locked_balance = new_locked_balance, updated_at = NOW()
    WHERE id = wallet_record.id;
    
    -- 取引ログを作成
    INSERT INTO paper_wallet_transactions (
        wallet_id, user_id, asset, transaction_type, amount,
        balance_before, balance_after, related_order_id, description
    ) VALUES (
        wallet_record.id, p_user_id, p_asset, 
        CASE WHEN p_lock_amount > 0 THEN 'lock' ELSE 'unlock' END,
        p_lock_amount, wallet_record.locked_balance, new_locked_balance, 
        p_related_order_id, 
        CASE WHEN p_lock_amount > 0 THEN 'Balance locked for order' ELSE 'Balance unlocked after order' END
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 利用可能残高取得ビュー
CREATE OR REPLACE VIEW paper_wallet_balances AS
SELECT 
    user_id,
    asset,
    balance as total_balance,
    locked_balance,
    (balance - locked_balance) as available_balance,
    updated_at
FROM paper_wallets
WHERE balance > 0 OR locked_balance > 0;

-- ユーザー別ポートフォリオビュー（価格情報は別途結合が必要）
CREATE OR REPLACE VIEW paper_portfolio_summary AS
SELECT 
    user_id,
    COUNT(*) as asset_count,
    SUM(CASE WHEN asset = 'USDT' THEN balance ELSE 0 END) as usdt_balance,
    SUM(CASE WHEN asset = 'BTC' THEN balance ELSE 0 END) as btc_balance,
    SUM(CASE WHEN asset = 'ETH' THEN balance ELSE 0 END) as eth_balance,
    MAX(updated_at) as last_updated
FROM paper_wallets
WHERE balance > 0
GROUP BY user_id;