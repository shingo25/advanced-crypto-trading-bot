"""
Vercel Functions最小テスト - シンプルなHTTPレスポンス
"""

def handler(request, context):
    """最小限のVercel Functionハンドラー"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": '{"status": "ok", "message": "simple test working", "timestamp": "2025-01-01T00:00:00"}'
    }