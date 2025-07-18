from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.core.security import get_current_user
from backend.core.database import get_db
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class Trade(BaseModel):
    id: int
    strategy_id: int
    symbol: str
    side: str
    price: float
    amount: float
    fee: float
    realized_pnl: float
    timestamp: datetime


class Position(BaseModel):
    id: int
    strategy_id: int
    symbol: str
    side: str
    entry_price: float
    amount: float
    unrealized_pnl: float
    opened_at: datetime
    closed_at: Optional[datetime] = None


# WebSocket接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connection established. Total: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket connection closed. Total: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # 接続が切れた場合は削除
                self.active_connections.remove(connection)


manager = ConnectionManager()


@router.get("/", response_model=List[Trade])
async def get_trades(
    strategy_id: Optional[int] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """取引履歴を取得"""
    db = get_db()
    query = """
        SELECT id, strategy_id, symbol, side, price, amount, fee,
               realized_pnl, timestamp
        FROM trades
    """
    params = []

    if strategy_id:
        query += " WHERE strategy_id = ?"
        params.append(strategy_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    trades = db.fetchall(query, params)
    return [
        Trade(
            id=t[0],
            strategy_id=t[1],
            symbol=t[2],
            side=t[3],
            price=t[4],
            amount=t[5],
            fee=t[6],
            realized_pnl=t[7],
            timestamp=t[8],
        )
        for t in trades
    ]


@router.get("/positions", response_model=List[Position])
async def get_positions(
    strategy_id: Optional[int] = None, current_user: dict = Depends(get_current_user)
):
    """ポジション一覧を取得"""
    db = get_db()
    query = """
        SELECT id, strategy_id, symbol, side, entry_price, amount,
               unrealized_pnl, opened_at, closed_at
        FROM positions
    """
    params = []

    if strategy_id:
        query += " WHERE strategy_id = ?"
        params.append(strategy_id)

    query += " ORDER BY opened_at DESC"

    positions = db.fetchall(query, params)
    return [
        Position(
            id=p[0],
            strategy_id=p[1],
            symbol=p[2],
            side=p[3],
            entry_price=p[4],
            amount=p[5],
            unrealized_pnl=p[6],
            opened_at=p[7],
            closed_at=p[8],
        )
        for p in positions
    ]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """リアルタイム取引データのWebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # クライアントからのメッセージを受信（keepalive）
            await websocket.receive_text()

            # TODO: 実際のライブトレードデータを送信
            # 現在はダミーデータを送信
            dummy_trade = {
                "type": "trade",
                "strategy_id": 1,
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 43000.0,
                "amount": 0.01,
                "timestamp": datetime.now().isoformat(),
            }

            await manager.send_personal_message(json.dumps(dummy_trade), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
