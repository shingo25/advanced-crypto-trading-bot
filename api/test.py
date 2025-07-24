"""
最もシンプルなPython関数 - 依存関係なし
"""

def handler(request):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"status": "ok", "message": "Pure Python working"}'
    }