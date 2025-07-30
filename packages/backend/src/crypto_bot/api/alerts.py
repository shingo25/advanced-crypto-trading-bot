"""
Alert System API

Phase3で実装したAlert/Notification機能をAPI化
アラート作成、管理、配信状況確認などの機能を提供
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from crypto_bot.core.messaging import AlertPublisher
from crypto_bot.core.redis import RedisManager
from crypto_bot.core.security import get_current_user
from crypto_bot.models.alerts import AlertCategory, AlertLevel, AlertType, UnifiedAlert
from crypto_bot.monitoring.alert_manager import IntegratedAlertManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global alert manager instance (in production, this would be per-user)
_alert_manager: Optional[IntegratedAlertManager] = None
_alert_publisher: Optional[AlertPublisher] = None


def get_alert_manager() -> IntegratedAlertManager:
    """アラートマネージャーインスタンスを取得"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = IntegratedAlertManager()
    return _alert_manager


def get_alert_publisher() -> AlertPublisher:
    """アラートパブリッシャーインスタンスを取得"""
    global _alert_publisher
    if _alert_publisher is None:
        redis_manager = RedisManager()
        _alert_publisher = AlertPublisher(redis_manager)
    return _alert_publisher


# Pydantic models
class AlertCreateRequest(BaseModel):
    """アラート作成リクエスト"""

    name: str = Field(..., min_length=1, max_length=100, description="アラート名")
    target: str = Field(..., description="監視対象 (price, volume, rsi, var など)")
    symbol: Optional[str] = Field(None, description="取引シンボル")
    condition: Literal["GREATER_THAN", "LESS_THAN", "EQUALS", "NOT_EQUALS"] = Field(..., description="条件")
    value: float = Field(..., description="閾値")
    notification_channels: List[str] = Field(default=["websocket"], description="通知チャンネル")
    level: Literal["info", "warning", "critical"] = Field(default="info", description="アラートレベル")
    enabled: bool = Field(default=True, description="有効状態")


class AlertUpdateRequest(BaseModel):
    """アラート更新リクエスト"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="アラート名")
    condition: Optional[Literal["GREATER_THAN", "LESS_THAN", "EQUALS", "NOT_EQUALS"]] = Field(None, description="条件")
    value: Optional[float] = Field(None, description="閾値")
    notification_channels: Optional[List[str]] = Field(None, description="通知チャンネル")
    level: Optional[Literal["info", "warning", "critical"]] = Field(None, description="アラートレベル")
    enabled: Optional[bool] = Field(None, description="有効状態")


class AlertResponse(BaseModel):
    """アラートレスポンス"""

    id: str
    name: str
    target: str
    symbol: Optional[str]
    condition: str
    value: float
    notification_channels: List[str]
    level: str
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_triggered: Optional[datetime]
    trigger_count: int


class AlertHistoryResponse(BaseModel):
    """アラート履歴レスポンス"""

    id: str
    alert_id: str
    alert_name: str
    triggered_at: datetime
    value: float
    threshold: float
    condition: str
    message: str
    level: str
    acknowledged: bool


class AlertStatsResponse(BaseModel):
    """アラート統計レスポンス"""

    total_alerts: int
    active_alerts: int
    triggered_today: int
    triggered_this_week: int
    most_triggered_alert: Optional[str]
    recent_triggers: List[AlertHistoryResponse]


# In-memory storage for demo (in production, use database)
_alerts_storage: Dict[str, Dict[str, Any]] = {}
_alert_history_storage: List[Dict[str, Any]] = []


@router.post("/", response_model=AlertResponse)
async def create_alert(request: AlertCreateRequest, current_user: dict = Depends(get_current_user)):
    """新しいアラートを作成"""
    try:
        alert_id = str(uuid.uuid4())
        user_id = current_user["id"]

        # アラートデータを作成
        alert_data = {
            "id": alert_id,
            "user_id": user_id,
            "name": request.name,
            "target": request.target,
            "symbol": request.symbol,
            "condition": request.condition,
            "value": request.value,
            "notification_channels": request.notification_channels,
            "level": request.level,
            "enabled": request.enabled,
            "created_at": datetime.now(),
            "updated_at": None,
            "last_triggered": None,
            "trigger_count": 0,
        }

        # ストレージに保存
        if user_id not in _alerts_storage:
            _alerts_storage[user_id] = {}
        _alerts_storage[user_id][alert_id] = alert_data

        logger.info(f"Alert '{request.name}' created by user {user_id}")

        return AlertResponse(**alert_data)

    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    enabled_only: bool = Query(default=False, description="有効なアラートのみ取得"),
    current_user: dict = Depends(get_current_user),
):
    """アラート一覧を取得"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage:
            return []

        alerts = list(_alerts_storage[user_id].values())

        if enabled_only:
            alerts = [alert for alert in alerts if alert["enabled"]]

        return [AlertResponse(**alert) for alert in alerts]

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """特定のアラートを取得"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage or alert_id not in _alerts_storage[user_id]:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = _alerts_storage[user_id][alert_id]
        return AlertResponse(**alert_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert")


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """アラートを更新"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage or alert_id not in _alerts_storage[user_id]:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = _alerts_storage[user_id][alert_id]

        # 更新データを適用
        update_data = request.dict(exclude_unset=True)
        for key, value in update_data.items():
            alert_data[key] = value

        alert_data["updated_at"] = datetime.now()

        logger.info(f"Alert {alert_id} updated by user {user_id}")

        return AlertResponse(**alert_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """アラートを削除"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage or alert_id not in _alerts_storage[user_id]:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_name = _alerts_storage[user_id][alert_id]["name"]
        del _alerts_storage[user_id][alert_id]

        logger.info(f"Alert '{alert_name}' ({alert_id}) deleted by user {user_id}")

        return {"message": f"Alert '{alert_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert")


@router.patch("/{alert_id}/toggle", response_model=AlertResponse)
async def toggle_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """アラートの有効/無効を切り替え"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage or alert_id not in _alerts_storage[user_id]:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = _alerts_storage[user_id][alert_id]
        alert_data["enabled"] = not alert_data["enabled"]
        alert_data["updated_at"] = datetime.now()

        status = "enabled" if alert_data["enabled"] else "disabled"
        logger.info(f"Alert {alert_id} {status} by user {user_id}")

        return AlertResponse(**alert_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle alert")


@router.post("/{alert_id}/test")
async def test_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """アラートのテスト配信"""
    try:
        user_id = current_user["id"]

        if user_id not in _alerts_storage or alert_id not in _alerts_storage[user_id]:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = _alerts_storage[user_id][alert_id]

        # テストアラートを作成
        test_alert = UnifiedAlert(
            id=str(uuid.uuid4()),
            level=AlertLevel(alert_data["level"]),
            category=AlertCategory.SYSTEM,
            type=AlertType.TEST,
            title=f"Test Alert: {alert_data['name']}",
            message=f"This is a test notification for alert '{alert_data['name']}'",
            metadata={
                "original_alert_id": alert_id,
                "test_trigger": True,
                "user_id": user_id,
            },
        )

        # アラートパブリッシャーで配信
        alert_publisher = get_alert_publisher()
        await alert_publisher.publish_alert(test_alert, channels=alert_data["notification_channels"])

        logger.info(f"Test alert sent for {alert_id} by user {user_id}")

        return {
            "message": "Test alert sent successfully",
            "alert_id": alert_id,
            "test_alert_id": test_alert.id,
            "channels": alert_data["notification_channels"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test alert")


@router.get("/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    limit: int = Query(default=50, ge=1, le=500, description="取得件数"),
    alert_id: Optional[str] = Query(None, description="特定のアラートIDでフィルタ"),
    current_user: dict = Depends(get_current_user),
):
    """アラート履歴を取得"""
    try:
        user_id = current_user["id"]

        # ユーザーのアラート履歴をフィルタ
        user_history = [history for history in _alert_history_storage if history.get("user_id") == user_id]

        # 特定のアラートIDでフィルタ
        if alert_id:
            user_history = [history for history in user_history if history.get("alert_id") == alert_id]

        # 最新順にソートして制限
        user_history.sort(key=lambda x: x.get("triggered_at", datetime.min), reverse=True)
        user_history = user_history[:limit]

        return [AlertHistoryResponse(**history) for history in user_history]

    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert history")


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_statistics(current_user: dict = Depends(get_current_user)):
    """アラート統計を取得"""
    try:
        user_id = current_user["id"]

        # ユーザーのアラート情報を取得
        user_alerts = _alerts_storage.get(user_id, {})
        user_history = [history for history in _alert_history_storage if history.get("user_id") == user_id]

        # 統計を計算
        total_alerts = len(user_alerts)
        active_alerts = sum(1 for alert in user_alerts.values() if alert["enabled"])

        # 今日と今週のトリガー数を計算
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        triggered_today = sum(1 for history in user_history if history.get("triggered_at", datetime.min) >= today_start)

        triggered_this_week = sum(
            1 for history in user_history if history.get("triggered_at", datetime.min) >= week_start
        )

        # 最もトリガーされたアラートを計算
        trigger_counts = {}
        for history in user_history:
            alert_name = history.get("alert_name", "Unknown")
            trigger_counts[alert_name] = trigger_counts.get(alert_name, 0) + 1

        most_triggered_alert = None
        if trigger_counts:
            most_triggered_alert = max(trigger_counts, key=trigger_counts.get)

        # 最近のトリガー履歴
        recent_triggers = sorted(
            user_history,
            key=lambda x: x.get("triggered_at", datetime.min),
            reverse=True,
        )[:10]

        return AlertStatsResponse(
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            triggered_today=triggered_today,
            triggered_this_week=triggered_this_week,
            most_triggered_alert=most_triggered_alert,
            recent_triggers=[AlertHistoryResponse(**trigger) for trigger in recent_triggers],
        )

    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert statistics")


@router.get("/health")
async def alerts_health_check():
    """アラートシステムのヘルスチェック"""
    try:
        alert_manager = get_alert_manager()

        # Redis接続確認
        redis_status = "unknown"
        try:
            redis_manager = RedisManager()
            redis_status = "connected" if redis_manager.ping() else "disconnected"
        except Exception:
            redis_status = "error"

        health_data = {
            "status": "healthy",
            "alert_manager_initialized": alert_manager is not None,
            "redis_status": redis_status,
            "total_alerts_in_memory": sum(len(alerts) for alerts in _alerts_storage.values()),
            "total_history_records": len(_alert_history_storage),
            "supported_channels": ["websocket", "email", "slack", "webhook"],
            "timestamp": datetime.now().isoformat(),
        }

        return health_data

    except Exception as e:
        logger.error(f"Alerts health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
