"""
通知チャネルパッケージ

様々な通知チャネルの実装を提供
"""

from .base import NotificationChannel, NotificationError, NotificationResult
from .email import EmailChannel
from .slack import SlackChannel
from .webhook import WebhookChannel

__all__ = [
    "NotificationChannel",
    "NotificationResult",
    "NotificationError",
    "EmailChannel",
    "SlackChannel",
    "WebhookChannel",
]
