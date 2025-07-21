"""
Portfolio API のテスト

Phase3で実装したPortfolio Management APIの動作確認
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.main import app
from backend.portfolio.strategy_portfolio_manager import AdvancedPortfolioManager


class TestPortfolioAPI:
    """Portfolio APIのテスト"""

    @pytest_asyncio.fixture
    async def client(self):
        """テスト用のHTTPクライアント"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_user(self):
        """モックユーザー"""
        return {"id": "test_user_123", "username": "testuser"}

    @pytest.fixture
    def mock_portfolio_manager(self):
        """独立したポートフォリオマネージャー（各テストで完全に新規作成）"""
        return AdvancedPortfolioManager(initial_capital=100000.0)

    @pytest.mark.asyncio
    async def test_get_portfolio_summary(self, client, mock_user, mock_portfolio_manager):
        """ポートフォリオサマリー取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
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
        assert overview["initial_capital"] == 100000.0
        assert overview["current_capital"] == 100000.0
        assert overview["total_strategies"] == 0
        assert overview["active_strategies"] == 0

    @pytest.mark.asyncio
    async def test_add_rsi_strategy(self, client, mock_user, mock_portfolio_manager):
        """RSI戦略追加テスト"""
        strategy_request = {
            "strategy_type": "rsi",
            "allocation_weight": 0.3,
            "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70},
            "symbol": "BTCUSDT",
            "timeframe": "1h",
        }

        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/strategies", json=strategy_request)

                assert response.status_code == 200
                data = response.json()

                assert data["strategy_type"] == "rsi"
                assert data["allocation_weight"] == 0.3
                assert data["allocated_capital"] == 30000.0  # 100000 * 0.3
                assert data["status"] == "active"
                assert data["symbol"] == "BTCUSDT"
                assert data["timeframe"] == "1h"
                assert "RSI_Strategy" in data["strategy_name"]

                # パラメータ確認
                assert data["parameters"]["rsi_period"] == 14
                assert data["parameters"]["oversold"] == 30
                assert data["parameters"]["overbought"] == 70

    @pytest.mark.asyncio
    async def test_add_macd_strategy(self, client, mock_user, mock_portfolio_manager):
        """MACD戦略追加テスト"""
        strategy_request = {
            "strategy_type": "macd",
            "allocation_weight": 0.4,
            "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "symbol": "ETHUSDT",
            "timeframe": "4h",
        }

        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/strategies", json=strategy_request)

                assert response.status_code == 200
                data = response.json()

                assert data["strategy_type"] == "macd"
                assert data["allocation_weight"] == 0.4
                assert data["allocated_capital"] == 40000.0
                assert data["symbol"] == "ETHUSDT"
                assert data["timeframe"] == "4h"
                assert "MACD_Strategy" in data["strategy_name"]

    @pytest.mark.asyncio
    async def test_add_bollinger_strategy(self, client, mock_user, mock_portfolio_manager):
        """Bollinger Bands戦略追加テスト"""
        strategy_request = {
            "strategy_type": "bollinger",
            "allocation_weight": 0.25,
            "parameters": {"bb_period": 20, "bb_std_dev": 2.0},
        }

        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/strategies", json=strategy_request)

                assert response.status_code == 200
                data = response.json()

                assert data["strategy_type"] == "bollinger"
                assert data["allocation_weight"] == 0.25
                assert data["allocated_capital"] == 25000.0
                assert "BOLLINGER_Strategy" in data["strategy_name"]

    @pytest.mark.asyncio
    async def test_invalid_strategy_type(self, client, mock_user, mock_portfolio_manager):
        """無効な戦略タイプのテスト"""
        strategy_request = {
            "strategy_type": "invalid_strategy",
            "allocation_weight": 0.3,
        }

        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/strategies", json=strategy_request)

                assert response.status_code == 400
                assert "Unsupported strategy type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_allocation_weight(self, client, mock_user, mock_portfolio_manager):
        """無効な配分重みのテスト"""
        strategy_request = {
            "strategy_type": "rsi",
            "allocation_weight": 1.5,  # 100%を超える
        }

        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/strategies", json=strategy_request)

                assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_strategy_status(self, client, mock_user, mock_portfolio_manager):
        """戦略ステータス更新テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                # まず戦略を追加
                strategy_request = {"strategy_type": "rsi", "allocation_weight": 0.3}

                # 戦略追加
                add_response = await client.post("/api/portfolio/strategies", json=strategy_request)
                assert add_response.status_code == 200
                strategy_name = add_response.json()["strategy_name"]

                # ステータス更新
                status_update = {"status": "paused"}
                update_response = await client.patch(
                    f"/api/portfolio/strategies/{strategy_name}/status", json=status_update
                )

                assert update_response.status_code == 200
                assert "paused" in update_response.json()["message"]

    @pytest.mark.asyncio
    async def test_remove_strategy(self, client, mock_user, mock_portfolio_manager):
        """戦略削除テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                # まず戦略を追加
                strategy_request = {"strategy_type": "rsi", "allocation_weight": 0.3}

                # 戦略追加
                add_response = await client.post("/api/portfolio/strategies", json=strategy_request)
                assert add_response.status_code == 200
                strategy_name = add_response.json()["strategy_name"]

                # 戦略削除
                delete_response = await client.delete(f"/api/portfolio/strategies/{strategy_name}")

                assert delete_response.status_code == 200
                assert "removed successfully" in delete_response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_strategy_performance(self, client, mock_user, mock_portfolio_manager):
        """戦略パフォーマンス取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                # まず戦略を追加
                strategy_request = {"strategy_type": "rsi", "allocation_weight": 0.3}

                # 戦略追加
                add_response = await client.post("/api/portfolio/strategies", json=strategy_request)
                assert add_response.status_code == 200
                strategy_name = add_response.json()["strategy_name"]

                # パフォーマンス取得
                perf_response = await client.get(f"/api/portfolio/strategies/{strategy_name}/performance")

                assert perf_response.status_code == 200
                perf_data = perf_response.json()

                # パフォーマンスメトリクスの確認
                assert "strategy_name" in perf_data
                assert "total_return" in perf_data
                assert "win_rate" in perf_data
                assert "trades_count" in perf_data
                assert "sharpe_ratio" in perf_data
                assert "max_drawdown" in perf_data

    @pytest.mark.asyncio
    async def test_get_correlation_matrix(self, client, mock_user, mock_portfolio_manager):
        """相関行列取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.get("/api/portfolio/correlation")

                assert response.status_code == 200
                data = response.json()

                # データが不足している場合のレスポンス確認
                assert "correlation_matrix" in data
                if "message" in data:
                    assert "Not enough data" in data["message"]

    @pytest.mark.asyncio
    async def test_get_rebalance_recommendations(self, client, mock_user, mock_portfolio_manager):
        """リバランシング提案取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/rebalance")

                assert response.status_code == 200
                data = response.json()

                assert "rebalancing_actions" in data
                assert "current_allocations" in data
                assert "recommended_allocations" in data
                assert "expected_improvement" in data

    @pytest.mark.asyncio
    async def test_get_risk_report(self, client, mock_user, mock_portfolio_manager):
        """リスクレポート取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.get("/api/portfolio/risk-report")

                assert response.status_code == 200
                data = response.json()

                # リスクレポートの基本構造確認
                assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_optimization(self, client, mock_user, mock_portfolio_manager):
        """ポートフォリオ最適化取得テスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                response = await client.post("/api/portfolio/optimize")

                assert response.status_code == 200
                data = response.json()

                # 最適化提案の基本構造確認
                assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """ヘルスチェックテスト"""
        response = await client.get("/api/portfolio/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "portfolio_initialized" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_multiple_strategies_workflow(self, client, mock_user, mock_portfolio_manager):
        """複数戦略のワークフローテスト"""
        with patch("backend.core.security.get_current_user", return_value=mock_user):
            with patch(
                "backend.api.portfolio.get_portfolio_manager",
                return_value=mock_portfolio_manager,
            ):
                strategies = [
                    {"strategy_type": "rsi", "allocation_weight": 0.3},
                    {"strategy_type": "macd", "allocation_weight": 0.4},
                    {"strategy_type": "bollinger", "allocation_weight": 0.2},
                ]

                strategy_names = []

                # 複数戦略を追加
                for strategy in strategies:
                    response = await client.post("/api/portfolio/strategies", json=strategy)
                    assert response.status_code == 200
                    strategy_names.append(response.json()["strategy_name"])

                # ポートフォリオサマリー確認
                summary_response = await client.get("/api/portfolio/")
                assert summary_response.status_code == 200
                summary = summary_response.json()

                assert summary["portfolio_overview"]["total_strategies"] == 3
                assert summary["portfolio_overview"]["active_strategies"] == 3
                assert len(summary["strategy_allocations"]) == 3

                # 各戦略のパフォーマンス確認
                for strategy_name in strategy_names:
                    perf_response = await client.get(f"/api/portfolio/strategies/{strategy_name}/performance")
                    assert perf_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
