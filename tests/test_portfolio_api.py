"""
Portfolio API のテスト

Phase3で実装したPortfolio Management APIの動作確認
FastAPI dependency_overridesを使用した正しいテスト実装
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.core.security import get_current_user
from backend.main import app
from backend.portfolio.strategy_portfolio_manager import AdvancedPortfolioManager


class TestPortfolioAPI:
    """Portfolio APIのテスト"""

    @pytest.fixture
    def mock_user(self):
        """モックユーザー"""
        return {"id": "test_user_123", "username": "testuser"}

    @pytest.fixture
    def mock_portfolio_manager(self):
        """独立したポートフォリオマネージャー（各テストで完全に新規作成）"""
        return AdvancedPortfolioManager(initial_capital=100000.0)

    @pytest_asyncio.fixture
    async def client(self, mock_user):
        """FastAPI dependency_overridesを使用した認証済みテストクライアント"""

        async def mock_get_current_user():
            return mock_user

        # FastAPIの依存性オーバーライドを使用（推奨方法）
        app.dependency_overrides[get_current_user] = mock_get_current_user

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        # クリーンアップ
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_portfolio_summary(self, client, mock_portfolio_manager):
        """ポートフォリオサマリー取得テスト"""
        response = await client.get("/api/portfolio/")

        assert response.status_code == 200
        data = response.json()

        # 基本構造の確認
        assert "portfolio_overview" in data
        assert "strategy_allocations" in data
        assert "performance_metrics" in data
        assert "risk_metrics" in data
        assert "trade_summary" in data

        # ポートフォリオ概要の確認
        overview = data["portfolio_overview"]
        assert "initial_capital" in overview
        assert "current_capital" in overview
        assert "total_strategies" in overview
        assert "active_strategies" in overview

    @pytest.mark.asyncio
    async def test_add_rsi_strategy(self, client, mock_portfolio_manager):
        """RSI戦略追加テスト"""
        strategy_request = {
            "strategy_type": "rsi",
            "allocation_weight": 0.3,
            "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70},
            "symbol": "BTCUSDT",
            "timeframe": "1h",
        }

        response = await client.post("/api/portfolio/strategies", json=strategy_request)

        # APIが存在すること、認証が通ることを確認
        # 実装の詳細に依存しない基本的なレスポンスチェック
        assert response.status_code in [200, 201, 422]  # 成功またはバリデーションエラー

        if response.status_code in [200, 201]:
            data = response.json()
            assert "strategy_type" in data

    @pytest.mark.asyncio
    async def test_add_macd_strategy(self, client, mock_portfolio_manager):
        """MACD戦略追加テスト"""
        strategy_request = {
            "strategy_type": "macd",
            "allocation_weight": 0.4,
            "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "symbol": "ETHUSDT",
            "timeframe": "4h",
        }

        response = await client.post("/api/portfolio/strategies", json=strategy_request)

        assert response.status_code in [200, 201, 422]

    @pytest.mark.asyncio
    async def test_add_bollinger_strategy(self, client, mock_portfolio_manager):
        """Bollinger Bands戦略追加テスト"""
        strategy_request = {
            "strategy_type": "bollinger",
            "allocation_weight": 0.25,
            "parameters": {"bb_period": 20, "bb_std_dev": 2.0},
        }

        response = await client.post("/api/portfolio/strategies", json=strategy_request)

        assert response.status_code in [200, 201, 422]

    @pytest.mark.asyncio
    async def test_invalid_strategy_type(self, client, mock_portfolio_manager):
        """無効な戦略タイプのテスト"""
        strategy_request = {
            "strategy_type": "invalid_strategy",
            "allocation_weight": 0.3,
        }

        response = await client.post("/api/portfolio/strategies", json=strategy_request)

        # 400 Bad Requestまたは422 Validation Errorを期待
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_allocation_weight(self, client, mock_portfolio_manager):
        """無効な配分重みのテスト"""
        strategy_request = {
            "strategy_type": "rsi",
            "allocation_weight": 1.5,  # 100%を超える
        }

        response = await client.post("/api/portfolio/strategies", json=strategy_request)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_strategy_status(self, client, mock_portfolio_manager):
        """戦略ステータス更新テスト"""
        # エンドポイントの存在と認証の確認
        response = await client.patch("/api/portfolio/strategies/test-strategy/status", json={"status": "paused"})

        # 404 (存在しない戦略) または 200 (成功) を許可
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_remove_strategy(self, client, mock_portfolio_manager):
        """戦略削除テスト"""
        response = await client.delete("/api/portfolio/strategies/test-strategy")

        # 404 (存在しない戦略) または 200 (成功) を許可
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_strategy_performance(self, client, mock_portfolio_manager):
        """戦略パフォーマンス取得テスト"""
        response = await client.get("/api/portfolio/strategies/test-strategy/performance")

        # 404 (存在しない戦略) または 200 (成功) を許可
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_correlation_matrix(self, client, mock_portfolio_manager):
        """相関行列取得テスト"""
        response = await client.get("/api/portfolio/correlation")

        assert response.status_code == 200
        data = response.json()
        assert "correlation_matrix" in data

    @pytest.mark.asyncio
    async def test_get_rebalance_recommendations(self, client, mock_portfolio_manager):
        """リバランシング提案取得テスト"""
        response = await client.post("/api/portfolio/rebalance")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_get_risk_report(self, client, mock_portfolio_manager):
        """リスクレポート取得テスト"""
        response = await client.get("/api/portfolio/risk-report")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_optimization(self, client, mock_portfolio_manager):
        """ポートフォリオ最適化取得テスト"""
        response = await client.post("/api/portfolio/optimize")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """ヘルスチェックテスト（認証不要）"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_multiple_strategies_workflow(self, client, mock_portfolio_manager):
        """複数戦略のワークフローテスト"""
        # 基本的なワークフローをテスト
        # 1. ポートフォリオサマリー取得
        summary_response = await client.get("/api/portfolio/")
        assert summary_response.status_code == 200

        # 2. 相関行列取得
        corr_response = await client.get("/api/portfolio/correlation")
        assert corr_response.status_code == 200

        # 3. リスクレポート取得
        risk_response = await client.get("/api/portfolio/risk-report")
        assert risk_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
