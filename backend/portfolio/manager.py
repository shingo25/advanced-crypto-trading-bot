"""
ポートフォリオ管理システム
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """資産の種類"""

    CRYPTO = "crypto"
    FIAT = "fiat"
    STABLE = "stable"


@dataclass
class Asset:
    """資産"""

    symbol: str
    asset_type: AssetType
    current_price: float = 0.0
    balance: float = 0.0
    target_weight: float = 0.0
    actual_weight: float = 0.0
    last_update: Optional[datetime] = None

    @property
    def market_value(self) -> float:
        """市場価値を計算"""
        return self.balance * self.current_price

    def update_price(self, price: float):
        """価格を更新"""
        self.current_price = price
        self.last_update = datetime.now()


@dataclass
class Portfolio:
    """ポートフォリオ"""

    name: str
    assets: Dict[str, Asset] = field(default_factory=dict)
    total_value: float = 0.0
    target_allocation: Dict[str, float] = field(default_factory=dict)
    rebalance_threshold: float = 0.05  # 5%のずれでリバランス
    min_trade_amount: float = 10.0  # 最小取引額
    created_at: datetime = field(default_factory=datetime.now)
    last_rebalance: Optional[datetime] = None

    def add_asset(self, asset: Asset):
        """資産を追加"""
        self.assets[asset.symbol] = asset
        if asset.target_weight > 0:
            self.target_allocation[asset.symbol] = asset.target_weight
        self._calculate_weights()
        logger.info(f"Added asset {asset.symbol} to portfolio {self.name}")

    def remove_asset(self, symbol: str):
        """資産を削除"""
        if symbol in self.assets:
            del self.assets[symbol]
        if symbol in self.target_allocation:
            del self.target_allocation[symbol]
        logger.info(f"Removed asset {symbol} from portfolio {self.name}")

    def update_asset_balance(self, symbol: str, balance: float):
        """資産残高を更新"""
        if symbol in self.assets:
            self.assets[symbol].balance = balance
            self._calculate_weights()
            logger.info(f"Updated balance for {symbol}: {balance}")

    def update_asset_price(self, symbol: str, price: float):
        """資産価格を更新"""
        if symbol in self.assets:
            self.assets[symbol].update_price(price)
            self._calculate_weights()
            logger.info(f"Updated price for {symbol}: {price}")

    def _calculate_weights(self):
        """実際の重みを計算"""
        total_value = sum(asset.market_value for asset in self.assets.values())
        self.total_value = total_value

        if total_value > 0:
            for asset in self.assets.values():
                asset.actual_weight = asset.market_value / total_value
        else:
            for asset in self.assets.values():
                asset.actual_weight = 0.0

    def get_rebalance_suggestions(self) -> List[Dict[str, Any]]:
        """リバランス提案を取得"""
        suggestions = []

        if self.total_value < self.min_trade_amount:
            return suggestions

        for symbol, asset in self.assets.items():
            if symbol not in self.target_allocation:
                continue

            target_weight = self.target_allocation[symbol]
            actual_weight = asset.actual_weight
            weight_diff = abs(target_weight - actual_weight)

            if weight_diff > self.rebalance_threshold:
                target_value = self.total_value * target_weight
                current_value = asset.market_value
                trade_value = target_value - current_value

                if abs(trade_value) >= self.min_trade_amount:
                    suggestions.append(
                        {
                            "symbol": symbol,
                            "current_weight": actual_weight,
                            "target_weight": target_weight,
                            "weight_diff": weight_diff,
                            "trade_value": trade_value,
                            "action": "buy" if trade_value > 0 else "sell",
                            "amount": abs(trade_value) / asset.current_price
                            if asset.current_price > 0
                            else 0,
                        }
                    )

        return suggestions

    def execute_rebalance(self, suggestions: List[Dict[str, Any]]):
        """リバランスを実行"""
        for suggestion in suggestions:
            symbol = suggestion["symbol"]
            action = suggestion["action"]
            amount = suggestion["amount"]

            if symbol in self.assets:
                asset = self.assets[symbol]

                if action == "buy":
                    # 買い注文をシミュレート
                    asset.balance += amount
                    logger.info(f"Bought {amount} {symbol}")
                elif action == "sell":
                    # 売り注文をシミュレート
                    asset.balance = max(0, asset.balance - amount)
                    logger.info(f"Sold {amount} {symbol}")

        self.last_rebalance = datetime.now()
        self._calculate_weights()
        logger.info(f"Rebalanced portfolio {self.name}")

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """ポートフォリオ概要を取得"""
        return {
            "name": self.name,
            "total_value": self.total_value,
            "asset_count": len(self.assets),
            "created_at": self.created_at.isoformat(),
            "last_rebalance": self.last_rebalance.isoformat()
            if self.last_rebalance
            else None,
            "assets": {
                symbol: {
                    "balance": asset.balance,
                    "current_price": asset.current_price,
                    "market_value": asset.market_value,
                    "target_weight": asset.target_weight,
                    "actual_weight": asset.actual_weight,
                    "asset_type": asset.asset_type.value,
                }
                for symbol, asset in self.assets.items()
            },
        }


class PortfolioManager:
    """ポートフォリオマネージャー"""

    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.risk_settings = {
            "max_concentration": 0.4,  # 単一資産の最大割合
            "max_volatility": 0.3,  # 最大ボラティリティ
            "min_diversification": 3,  # 最小分散数
        }
        logger.info("PortfolioManager initialized")

    def create_portfolio(
        self, name: str, initial_allocation: Dict[str, float] = None
    ) -> Portfolio:
        """ポートフォリオを作成"""
        portfolio = Portfolio(name=name)

        if initial_allocation:
            # 割合の合計が1.0になるよう正規化
            total_weight = sum(initial_allocation.values())
            if total_weight > 0:
                for symbol, weight in initial_allocation.items():
                    normalized_weight = weight / total_weight
                    asset = Asset(
                        symbol=symbol,
                        asset_type=self._get_asset_type(symbol),
                        target_weight=normalized_weight,
                    )
                    portfolio.add_asset(asset)

        self.portfolios[name] = portfolio
        logger.info(f"Created portfolio: {name}")
        return portfolio

    def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """ポートフォリオを取得"""
        return self.portfolios.get(name)

    def delete_portfolio(self, name: str):
        """ポートフォリオを削除"""
        if name in self.portfolios:
            del self.portfolios[name]
            logger.info(f"Deleted portfolio: {name}")

    def _get_asset_type(self, symbol: str) -> AssetType:
        """シンボルから資産タイプを推定"""
        stable_coins = ["USDT", "USDC", "BUSD", "DAI", "TUSD"]

        if symbol in stable_coins:
            return AssetType.STABLE
        elif symbol in ["USD", "EUR", "JPY", "GBP"]:
            return AssetType.FIAT
        else:
            return AssetType.CRYPTO

    def update_portfolio_prices(self, name: str, price_data: Dict[str, float]):
        """ポートフォリオの価格を更新"""
        if name in self.portfolios:
            portfolio = self.portfolios[name]
            for symbol, price in price_data.items():
                portfolio.update_asset_price(symbol, price)

    def get_risk_assessment(self, name: str) -> Dict[str, Any]:
        """リスク評価を取得"""
        if name not in self.portfolios:
            return {"error": "Portfolio not found"}

        portfolio = self.portfolios[name]
        assessment = {
            "concentration_risk": self._assess_concentration_risk(portfolio),
            "diversification_score": self._assess_diversification(portfolio),
            "volatility_risk": self._assess_volatility_risk(portfolio),
            "overall_risk_score": 0.0,
        }

        # 総合リスクスコアを計算
        assessment["overall_risk_score"] = (
            assessment["concentration_risk"] * 0.4
            + assessment["diversification_score"] * 0.3
            + assessment["volatility_risk"] * 0.3
        )

        return assessment

    def _assess_concentration_risk(self, portfolio: Portfolio) -> float:
        """集中リスクを評価"""
        if not portfolio.assets:
            return 1.0

        max_weight = max(asset.actual_weight for asset in portfolio.assets.values())

        if max_weight > self.risk_settings["max_concentration"]:
            return 1.0  # 高リスク
        elif max_weight > self.risk_settings["max_concentration"] * 0.75:
            return 0.5  # 中リスク
        else:
            return 0.0  # 低リスク

    def _assess_diversification(self, portfolio: Portfolio) -> float:
        """分散度を評価"""
        asset_count = len(portfolio.assets)

        if asset_count < self.risk_settings["min_diversification"]:
            return 1.0  # 低分散（高リスク）
        elif asset_count < self.risk_settings["min_diversification"] * 2:
            return 0.5  # 中分散
        else:
            return 0.0  # 高分散（低リスク）

    def _assess_volatility_risk(self, portfolio: Portfolio) -> float:
        """ボラティリティリスクを評価"""
        # 簡単なボラティリティ評価（実際の実装では価格履歴を使用）
        crypto_weight = sum(
            asset.actual_weight
            for asset in portfolio.assets.values()
            if asset.asset_type == AssetType.CRYPTO
        )

        if crypto_weight > 0.8:
            return 1.0  # 高ボラティリティ
        elif crypto_weight > 0.5:
            return 0.5  # 中ボラティリティ
        else:
            return 0.0  # 低ボラティリティ

    def get_optimization_suggestions(self, name: str) -> List[Dict[str, Any]]:
        """最適化提案を取得"""
        if name not in self.portfolios:
            return []

        portfolio = self.portfolios[name]
        suggestions = []

        # リバランス提案
        rebalance_suggestions = portfolio.get_rebalance_suggestions()
        if rebalance_suggestions:
            suggestions.append(
                {
                    "type": "rebalance",
                    "priority": "high",
                    "description": "Portfolio needs rebalancing",
                    "actions": rebalance_suggestions,
                }
            )

        # リスク軽減提案
        risk_assessment = self.get_risk_assessment(name)
        if risk_assessment["overall_risk_score"] > 0.6:
            suggestions.append(
                {
                    "type": "risk_reduction",
                    "priority": "medium",
                    "description": "Portfolio has high risk, consider diversification",
                    "actions": self._get_risk_reduction_actions(
                        portfolio, risk_assessment
                    ),
                }
            )

        return suggestions

    def _get_risk_reduction_actions(
        self, portfolio: Portfolio, risk_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """リスク軽減アクションを取得"""
        actions = []

        if risk_assessment["concentration_risk"] > 0.5:
            # 集中リスクを軽減
            max_asset = max(portfolio.assets.values(), key=lambda x: x.actual_weight)
            actions.append(
                {
                    "action": "reduce_concentration",
                    "symbol": max_asset.symbol,
                    "current_weight": max_asset.actual_weight,
                    "suggested_weight": self.risk_settings["max_concentration"] * 0.8,
                }
            )

        if risk_assessment["diversification_score"] > 0.5:
            # 分散を増やす
            actions.append(
                {
                    "action": "increase_diversification",
                    "current_assets": len(portfolio.assets),
                    "suggested_assets": self.risk_settings["min_diversification"] + 2,
                }
            )

        return actions

    def get_all_portfolios_summary(self) -> Dict[str, Any]:
        """すべてのポートフォリオの概要を取得"""
        return {
            "total_portfolios": len(self.portfolios),
            "portfolios": {
                name: portfolio.get_portfolio_summary()
                for name, portfolio in self.portfolios.items()
            },
        }

    def save_portfolio_state(self, name: str, filepath: str):
        """ポートフォリオ状態を保存"""
        if name not in self.portfolios:
            raise ValueError(f"Portfolio {name} not found")

        portfolio = self.portfolios[name]
        state = {
            "name": portfolio.name,
            "assets": {
                symbol: {
                    "symbol": asset.symbol,
                    "asset_type": asset.asset_type.value,
                    "current_price": asset.current_price,
                    "balance": asset.balance,
                    "target_weight": asset.target_weight,
                    "last_update": asset.last_update.isoformat()
                    if asset.last_update
                    else None,
                }
                for symbol, asset in portfolio.assets.items()
            },
            "target_allocation": portfolio.target_allocation,
            "rebalance_threshold": portfolio.rebalance_threshold,
            "min_trade_amount": portfolio.min_trade_amount,
            "created_at": portfolio.created_at.isoformat(),
            "last_rebalance": portfolio.last_rebalance.isoformat()
            if portfolio.last_rebalance
            else None,
        }

        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Portfolio {name} state saved to {filepath}")

    def load_portfolio_state(self, filepath: str) -> Portfolio:
        """ポートフォリオ状態を読み込み"""
        with open(filepath, "r") as f:
            state = json.load(f)

        portfolio = Portfolio(name=state["name"])
        portfolio.target_allocation = state["target_allocation"]
        portfolio.rebalance_threshold = state["rebalance_threshold"]
        portfolio.min_trade_amount = state["min_trade_amount"]
        portfolio.created_at = datetime.fromisoformat(state["created_at"])

        if state["last_rebalance"]:
            portfolio.last_rebalance = datetime.fromisoformat(state["last_rebalance"])

        for symbol, asset_data in state["assets"].items():
            asset = Asset(
                symbol=asset_data["symbol"],
                asset_type=AssetType(asset_data["asset_type"]),
                current_price=asset_data["current_price"],
                balance=asset_data["balance"],
                target_weight=asset_data["target_weight"],
            )

            if asset_data["last_update"]:
                asset.last_update = datetime.fromisoformat(asset_data["last_update"])

            portfolio.add_asset(asset)

        self.portfolios[portfolio.name] = portfolio
        logger.info(f"Portfolio {portfolio.name} loaded from {filepath}")
        return portfolio
