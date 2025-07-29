"""
Paper Trading用ウォレットサービス
仮想残高の管理と取引履歴の記録
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy import and_, desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import DatabaseManager, PaperWalletDefaultModel, PaperWalletModel, PaperWalletTransactionModel

logger = logging.getLogger(__name__)


class PaperWalletService:
    """
    Paper Trading用ウォレットサービス
    仮想残高の管理、取引実行、履歴記録を担当
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def initialize_user_wallet(
        self, user_id: UUID, default_setting: str = "beginner", force_reset: bool = False
    ) -> bool:
        """
        ユーザーのPaper Tradingウォレットを初期化

        Args:
            user_id: ユーザーID
            default_setting: デフォルト設定名
            force_reset: 既存ウォレットを強制リセット

        Returns:
            bool: 初期化成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            # 既存ウォレットの確認
            existing_wallets = session.query(PaperWalletModel).filter(PaperWalletModel.user_id == user_id).all()

            if existing_wallets and not force_reset:
                logger.info(f"User {user_id} already has paper wallets, skipping initialization")
                return True

            # デフォルト設定を取得
            default_config = (
                session.query(PaperWalletDefaultModel)
                .filter(
                    and_(PaperWalletDefaultModel.name == default_setting, PaperWalletDefaultModel.is_active.is_(True))
                )
                .first()
            )

            if not default_config:
                # デフォルト設定が存在しない場合は作成
                logger.info(f"Creating default setting: {default_setting}")
                default_balances = {
                    "beginner": {"USDT": 100000.0},  # 初心者: 10万USDT
                    "intermediate": {"USDT": 500000.0, "BTC": 1.0},  # 中級者: 50万USDT + 1 BTC
                    "advanced": {"USDT": 1000000.0, "BTC": 5.0, "ETH": 10.0},  # 上級者: 100万USDT + 5 BTC + 10 ETH
                }

                if default_setting in default_balances:
                    default_config = PaperWalletDefaultModel(
                        name=default_setting, default_balances=default_balances[default_setting], is_active=True
                    )
                    session.add(default_config)
                    session.flush()  # IDを取得するためにflush
                else:
                    logger.error(f"Unknown default setting: {default_setting}")
                    return False

            # 既存ウォレットを削除（force_resetの場合）
            if force_reset and existing_wallets:
                for wallet in existing_wallets:
                    session.delete(wallet)
                logger.info(f"Reset existing wallets for user {user_id}")

            # デフォルト残高を設定
            wallets_to_create = []
            for asset, balance in default_config.default_balances.items():
                wallet = PaperWalletModel(
                    user_id=user_id, asset=asset, balance=Decimal(str(balance)), locked_balance=Decimal("0")
                )
                session.add(wallet)
                wallets_to_create.append((wallet, asset, balance))

            # まずウォレットをコミットしてIDを取得
            session.flush()

            # その後で取引ログを作成（金額が0でない場合のみ）
            for wallet, asset, balance in wallets_to_create:
                if balance > 0:  # 金額が0より大きい場合のみ取引ログを作成
                    transaction = PaperWalletTransactionModel(
                        wallet_id=wallet.id,
                        user_id=user_id,
                        asset=asset,
                        transaction_type="deposit",
                        amount=Decimal(str(balance)),
                        balance_before=Decimal("0"),
                        balance_after=Decimal(str(balance)),
                        description=f"Initial deposit from {default_setting} setting",
                    )
                    session.add(transaction)

            session.commit()
            logger.info(f"Paper wallet initialized for user {user_id} with setting {default_setting}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to initialize paper wallet for user {user_id}: {e}")
            return False
        finally:
            session.close()

    def get_user_balances(self, user_id: UUID) -> Dict[str, Dict[str, float]]:
        """
        ユーザーの全残高を取得

        Args:
            user_id: ユーザーID

        Returns:
            Dict: 資産別残高情報
        """
        session = self.db_manager.get_session()
        try:
            wallets = session.query(PaperWalletModel).filter(PaperWalletModel.user_id == user_id).all()

            result = {}
            for wallet in wallets:
                result[wallet.asset] = {
                    "total": float(wallet.balance),
                    "locked": float(wallet.locked_balance),
                    "available": float(wallet.get_available_balance()),
                }

            return result

        except SQLAlchemyError as e:
            logger.error(f"Failed to get balances for user {user_id}: {e}")
            return {}
        finally:
            session.close()

    def get_asset_balance(self, user_id: UUID, asset: str) -> Dict[str, float]:
        """
        特定資産の残高を取得

        Args:
            user_id: ユーザーID
            asset: 資産名

        Returns:
            Dict: 残高情報
        """
        session = self.db_manager.get_session()
        try:
            wallet = (
                session.query(PaperWalletModel)
                .filter(and_(PaperWalletModel.user_id == user_id, PaperWalletModel.asset == asset))
                .first()
            )

            if not wallet:
                return {"total": 0.0, "locked": 0.0, "available": 0.0}

            return {
                "total": float(wallet.balance),
                "locked": float(wallet.locked_balance),
                "available": float(wallet.get_available_balance()),
            }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get balance for user {user_id}, asset {asset}: {e}")
            return {"total": 0.0, "locked": 0.0, "available": 0.0}
        finally:
            session.close()

    def update_balance(
        self,
        user_id: UUID,
        asset: str,
        amount: Decimal,
        transaction_type: str,
        related_order_id: str = None,
        description: str = None,
    ) -> bool:
        """
        残高を更新（アトミック操作）

        Args:
            user_id: ユーザーID
            asset: 資産名
            amount: 変動量（正負両方可）
            transaction_type: 取引タイプ
            related_order_id: 関連注文ID
            description: 説明

        Returns:
            bool: 更新成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            # ウォレットを取得（行ロック）
            wallet = (
                session.query(PaperWalletModel)
                .filter(and_(PaperWalletModel.user_id == user_id, PaperWalletModel.asset == asset))
                .with_for_update()
                .first()
            )

            # ウォレットが存在しない場合は作成
            if not wallet:
                wallet = PaperWalletModel(
                    user_id=user_id, asset=asset, balance=Decimal("0"), locked_balance=Decimal("0")
                )
                session.add(wallet)
                session.flush()  # IDを取得するため

            # 新しい残高を計算
            old_balance = wallet.balance
            new_balance = old_balance + amount

            # 残高が負になる場合はエラー
            if new_balance < 0:
                logger.warning(
                    f"Insufficient balance: user={user_id}, asset={asset}, current={old_balance}, requested={amount}"
                )
                return False

            # 残高を更新
            wallet.balance = new_balance
            wallet.updated_at = datetime.now(timezone.utc)

            # 取引ログを作成
            transaction = PaperWalletTransactionModel(
                wallet_id=wallet.id,
                user_id=user_id,
                asset=asset,
                transaction_type=transaction_type,
                amount=amount,
                balance_before=old_balance,
                balance_after=new_balance,
                related_order_id=related_order_id,
                description=description,
            )
            session.add(transaction)

            session.commit()
            logger.debug(f"Balance updated: user={user_id}, asset={asset}, amount={amount}, new_balance={new_balance}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update balance: user={user_id}, asset={asset}, amount={amount}, error={e}")
            return False
        finally:
            session.close()

    def lock_balance(self, user_id: UUID, asset: str, amount: Decimal, related_order_id: str = None) -> bool:
        """
        残高をロック（注文時）

        Args:
            user_id: ユーザーID
            asset: 資産名
            amount: ロック量
            related_order_id: 関連注文ID

        Returns:
            bool: ロック成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            # ウォレットを取得（行ロック）
            wallet = (
                session.query(PaperWalletModel)
                .filter(and_(PaperWalletModel.user_id == user_id, PaperWalletModel.asset == asset))
                .with_for_update()
                .first()
            )

            if not wallet:
                logger.warning(f"Wallet not found: user={user_id}, asset={asset}")
                return False

            # 利用可能残高をチェック
            available = wallet.get_available_balance()
            if available < amount:
                logger.warning(
                    f"Insufficient available balance: user={user_id}, asset={asset}, available={available}, requested={amount}"
                )
                return False

            # ロック残高を更新
            old_locked = wallet.locked_balance
            new_locked = old_locked + amount
            wallet.locked_balance = new_locked
            wallet.updated_at = datetime.now(timezone.utc)

            # ロック取引ログを作成
            transaction = PaperWalletTransactionModel(
                wallet_id=wallet.id,
                user_id=user_id,
                asset=asset,
                transaction_type="lock",
                amount=amount,
                balance_before=old_locked,
                balance_after=new_locked,
                related_order_id=related_order_id,
                description=f"Balance locked for order {related_order_id}",
            )
            session.add(transaction)

            session.commit()
            logger.debug(f"Balance locked: user={user_id}, asset={asset}, amount={amount}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to lock balance: user={user_id}, asset={asset}, amount={amount}, error={e}")
            return False
        finally:
            session.close()

    def unlock_balance(self, user_id: UUID, asset: str, amount: Decimal, related_order_id: str = None) -> bool:
        """
        残高のロックを解除

        Args:
            user_id: ユーザーID
            asset: 資産名
            amount: ロック解除量
            related_order_id: 関連注文ID

        Returns:
            bool: ロック解除成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            # ウォレットを取得（行ロック）
            wallet = (
                session.query(PaperWalletModel)
                .filter(and_(PaperWalletModel.user_id == user_id, PaperWalletModel.asset == asset))
                .with_for_update()
                .first()
            )

            if not wallet:
                logger.warning(f"Wallet not found: user={user_id}, asset={asset}")
                return False

            # ロック残高をチェック
            if wallet.locked_balance < amount:
                logger.warning(
                    f"Insufficient locked balance: user={user_id}, asset={asset}, locked={wallet.locked_balance}, requested={amount}"
                )
                return False

            # ロック残高を更新
            old_locked = wallet.locked_balance
            new_locked = old_locked - amount
            wallet.locked_balance = new_locked
            wallet.updated_at = datetime.now(timezone.utc)

            # ロック解除取引ログを作成
            transaction = PaperWalletTransactionModel(
                wallet_id=wallet.id,
                user_id=user_id,
                asset=asset,
                transaction_type="unlock",
                amount=-amount,  # 負の値でロック解除を表現
                balance_before=old_locked,
                balance_after=new_locked,
                related_order_id=related_order_id,
                description=f"Balance unlocked after order {related_order_id}",
            )
            session.add(transaction)

            session.commit()
            logger.debug(f"Balance unlocked: user={user_id}, asset={asset}, amount={amount}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to unlock balance: user={user_id}, asset={asset}, amount={amount}, error={e}")
            return False
        finally:
            session.close()

    def execute_trade(
        self,
        user_id: UUID,
        buy_asset: str,
        sell_asset: str,
        buy_amount: Decimal,
        sell_amount: Decimal,
        fee_asset: str,
        fee_amount: Decimal,
        related_order_id: str = None,
        description: str = None,
    ) -> bool:
        """
        取引を実行（複数資産の残高更新）

        Args:
            user_id: ユーザーID
            buy_asset: 購入資産
            sell_asset: 売却資産
            buy_amount: 購入量
            sell_amount: 売却量
            fee_asset: 手数料資産
            fee_amount: 手数料
            related_order_id: 関連注文ID
            description: 説明

        Returns:
            bool: 取引実行成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            # トランザクション内でまとめて処理
            success = True

            # 1. 売却資産を減らす
            if not self._update_balance_in_session(
                session, user_id, sell_asset, -sell_amount, "trade_sell", related_order_id, description
            ):
                success = False

            # 2. 購入資産を増やす
            if success and not self._update_balance_in_session(
                session, user_id, buy_asset, buy_amount, "trade_buy", related_order_id, description
            ):
                success = False

            # 3. 手数料を差し引く
            if (
                success
                and fee_amount > 0
                and not self._update_balance_in_session(
                    session, user_id, fee_asset, -fee_amount, "fee", related_order_id, f"Trading fee for {description}"
                )
            ):
                success = False

            if success:
                session.commit()
                logger.info(
                    f"Trade executed: user={user_id}, -{sell_amount} {sell_asset}, +{buy_amount} {buy_asset}, -{fee_amount} {fee_asset}"
                )
                return True
            else:
                session.rollback()
                logger.error(f"Trade execution failed: user={user_id}")
                return False

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error executing trade: user={user_id}, error={e}")
            return False
        finally:
            session.close()

    def _update_balance_in_session(
        self,
        session: Session,
        user_id: UUID,
        asset: str,
        amount: Decimal,
        transaction_type: str,
        related_order_id: str = None,
        description: str = None,
    ) -> bool:
        """セッション内での残高更新（内部メソッド）"""
        try:
            # ウォレットを取得（行ロック）
            wallet = (
                session.query(PaperWalletModel)
                .filter(and_(PaperWalletModel.user_id == user_id, PaperWalletModel.asset == asset))
                .with_for_update()
                .first()
            )

            # ウォレットが存在しない場合は作成
            if not wallet:
                wallet = PaperWalletModel(
                    user_id=user_id, asset=asset, balance=Decimal("0"), locked_balance=Decimal("0")
                )
                session.add(wallet)
                session.flush()  # IDを取得

            # 新しい残高を計算
            old_balance = wallet.balance
            new_balance = old_balance + amount

            # 残高が負になる場合はエラー
            if new_balance < 0:
                logger.warning(
                    f"Insufficient balance in trade: user={user_id}, asset={asset}, current={old_balance}, requested={amount}"
                )
                return False

            # 残高を更新
            wallet.balance = new_balance
            wallet.updated_at = datetime.now(timezone.utc)

            # 取引ログを作成
            transaction = PaperWalletTransactionModel(
                wallet_id=wallet.id,
                user_id=user_id,
                asset=asset,
                transaction_type=transaction_type,
                amount=amount,
                balance_before=old_balance,
                balance_after=new_balance,
                related_order_id=related_order_id,
                description=description,
            )
            session.add(transaction)

            return True

        except Exception as e:
            logger.error(f"Error updating balance in session: {e}")
            return False

    def get_transaction_history(
        self, user_id: UUID, asset: str = None, transaction_type: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        """
        取引履歴を取得

        Args:
            user_id: ユーザーID
            asset: 資産フィルター
            transaction_type: 取引タイプフィルター
            limit: 取得件数制限
            offset: オフセット

        Returns:
            List[Dict]: 取引履歴リスト
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(PaperWalletTransactionModel).filter(PaperWalletTransactionModel.user_id == user_id)

            if asset:
                query = query.filter(PaperWalletTransactionModel.asset == asset)

            if transaction_type:
                query = query.filter(PaperWalletTransactionModel.transaction_type == transaction_type)

            transactions = (
                query.order_by(desc(PaperWalletTransactionModel.created_at)).offset(offset).limit(limit).all()
            )

            return [tx.to_dict() for tx in transactions]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get transaction history: user={user_id}, error={e}")
            return []
        finally:
            session.close()

    def get_portfolio_summary(self, user_id: UUID) -> Dict:
        """
        ポートフォリオサマリーを取得

        Args:
            user_id: ユーザーID

        Returns:
            Dict: ポートフォリオサマリー
        """
        session = self.db_manager.get_session()
        try:
            # 残高情報
            balances = self.get_user_balances(user_id)

            # 取引統計
            stats = (
                session.query(
                    func.count(PaperWalletTransactionModel.id).label("total_transactions"),
                    func.count(func.distinct(PaperWalletTransactionModel.asset)).label("assets_count"),
                    func.min(PaperWalletTransactionModel.created_at).label("first_transaction"),
                    func.max(PaperWalletTransactionModel.created_at).label("last_transaction"),
                )
                .filter(PaperWalletTransactionModel.user_id == user_id)
                .first()
            )

            return {
                "user_id": str(user_id),
                "balances": balances,
                "statistics": {
                    "total_transactions": int(stats.total_transactions) if stats.total_transactions else 0,
                    "assets_count": int(stats.assets_count) if stats.assets_count else 0,
                    "first_transaction": stats.first_transaction.isoformat() if stats.first_transaction else None,
                    "last_transaction": stats.last_transaction.isoformat() if stats.last_transaction else None,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get portfolio summary: user={user_id}, error={e}")
            return {}
        finally:
            session.close()

    def get_default_settings(self) -> List[Dict]:
        """
        利用可能なデフォルト設定を取得

        Returns:
            List[Dict]: デフォルト設定リスト
        """
        session = self.db_manager.get_session()
        try:
            defaults = session.query(PaperWalletDefaultModel).filter(PaperWalletDefaultModel.is_active.is_(True)).all()

            return [default.to_dict() for default in defaults]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get default settings: {e}")
            return []
        finally:
            session.close()

    def reset_user_wallet(self, user_id: UUID, default_setting: str = "beginner") -> bool:
        """
        ユーザーウォレットをリセット

        Args:
            user_id: ユーザーID
            default_setting: デフォルト設定名

        Returns:
            bool: リセット成功フラグ
        """
        return self.initialize_user_wallet(user_id, default_setting, force_reset=True)
