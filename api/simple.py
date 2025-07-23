"""
最小限のVercel Serverless Function
依存関係なしでテスト用
"""

def handler(request):
    """最も基本的なVercelハンドラー"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': '''
        {
            "status": "ok", 
            "message": "Basic Vercel function working",
            "timestamp": "2025-07-23T16:20:00Z"
        }
        '''
    }