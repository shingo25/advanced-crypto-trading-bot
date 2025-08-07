"""
Vercel Functions最小テスト - 依存関係なし
"""

def handler(request, context):
    """最小限のVercel Functionハンドラー - 依存関係なし"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": '{"status": "ok", "message": "minimal test working", "source": "minimal_test.py"}'
    }