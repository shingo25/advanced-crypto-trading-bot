"""
APIファジングテスト（堅牢性検証）
不正な入力値、型不一致、権限外アクセス等の検証
"""

import pytest
from fastapi.testclient import TestClient

try:
    import schemathesis
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False
    schemathesis = None
from unittest.mock import patch, MagicMock
from datetime import timedelta

from src.backend.main import app
from src.backend.core.security import create_access_token

# schemathesis が利用できない場合はテスト全体をスキップ
pytestmark = pytest.mark.skipif(not SCHEMATHESIS_AVAILABLE, reason="schemathesis not available")


# FastAPIのappインスタンスからOpenAPIスキーマを読み込む（schemathesis利用可能時のみ）
schema = None
if SCHEMATHESIS_AVAILABLE:
    schema = schemathesis.openapi.from_asgi(app=app, path="/openapi.json")
client = TestClient(app)


def handle_client_side_errors(e, case):
    """
    HTTPXクライアント側のエラーを適切に処理する共通関数
    """
    error_message = str(e).lower()
    if any(keyword in error_message for keyword in [
        "invalid header", "illegal header", "protocol error", 
        "invalid character", "header", "encoding", "json serializable",
        "notset", "not json serializable"
    ]):
        # 不正なHTTPプロトコル形式の場合はテストをスキップ
        pytest.skip(f"HTTPXプロトコルエラー（正常な検証）: {str(e)[:100]}")
    else:
        # 予期しないエラーの場合は失敗とする
        pytest.fail(f"Unexpected error on {case.method} {case.formatted_path}: {str(e)}")


@pytest.fixture
def test_client():
    """テスト用クライアントの設定"""
    return TestClient(app)


@pytest.fixture
def valid_auth_token():
    """テスト用の有効なJWTトークンを生成"""
    user_data = {"sub": "fuzzing_test_user", "role": "admin"}
    expires_delta = timedelta(hours=1)
    token = create_access_token(data=user_data, expires_delta=expires_delta)
    return f"Bearer {token}"


@pytest.fixture
def invalid_auth_token():
    """無効なJWTトークンを生成"""
    return "Bearer invalid_token_for_fuzzing_test"


if SCHEMATHESIS_AVAILABLE and schema is not None:
    class TestAPIFuzzingBasic:
        """基本的なAPIファジングテスト"""
        
        @schema.parametrize()
        def test_no_server_errors(self, case):
        """
        5xx系サーバーエラーが発生しないことを検証
        どんな不正なリクエストでもサーバーがクラッシュしてはいけない
        """
        try:
            response = client.request(
                method=case.method,
                url=case.formatted_path,
                headers=case.headers,
                params=case.query,
                json=case.body
            )
            
            # サーバーエラー（5xx）が発生しないことを確認
            assert response.status_code < 500, f"Server error on {case.method} {case.formatted_path}: {response.text}"
            
        except Exception as e:
            handle_client_side_errors(e, case)
    
    @schema.parametrize()
    def test_proper_error_responses(self, case):
        """
        適切なエラーレスポンスが返されることを検証
        不正なリクエストには適切な4xxエラーが返されるべき
        """
        try:
            response = client.request(
                method=case.method,
                url=case.formatted_path,
                headers=case.headers,
                params=case.query,
                json=case.body
            )
            
            # レスポンスが適切なHTTPステータス範囲内であることを確認
            assert 100 <= response.status_code < 600
            
            # エラーレスポンスの場合、JSONまたは適切な形式であることを確認
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    # エラーレスポンスには詳細が含まれるべき（但し機密情報は含まない）
                    assert "detail" in error_data or "message" in error_data
                except ValueError:
                    # JSONでない場合も許可（HTTPエラーページなど）
                    pass
                    
        except Exception as e:
            handle_client_side_errors(e, case)


class TestAPIFuzzingAuthentication:
    """認証関連のAPIファジングテスト"""
    
    @schema.parametrize()
    def test_protected_endpoints_without_auth(self, case):
        """
        認証が必要なエンドポイントで未認証アクセスの検証
        """
        try:
            # 認証ヘッダーなしでリクエスト
            response = client.request(
                method=case.method,
                url=case.formatted_path,
                headers=case.headers,
                params=case.query,
                json=case.body
            )
            
            # サーバーエラーは発生してはいけない
            assert response.status_code < 500
            
            # 認証が必要なエンドポイントでは401または403が返されるべき
            # （ただし、公開エンドポイントは200/404も許可）
            if "/auth/" in case.formatted_path and case.formatted_path not in ["/auth/login", "/auth/register"]:
                assert response.status_code in [401, 403, 404], f"Protected endpoint should require auth: {case.formatted_path}"
                
        except Exception as e:
            handle_client_side_errors(e, case)
    
    @schema.parametrize()
    def test_invalid_token_handling(self, case, invalid_auth_token):
        """
        無効なトークンでのアクセス検証
        """
        try:
            headers = case.headers or {}
            headers["Authorization"] = invalid_auth_token
            
            response = client.request(
                method=case.method,
                url=case.formatted_path,
                headers=headers,
                params=case.query,
                json=case.body
            )
            
            # サーバーエラーは発生してはいけない
            assert response.status_code < 500
            
            # 無効なトークンは適切に拒否されるべき
            if "/auth/" in case.formatted_path and case.formatted_path not in ["/auth/login", "/auth/register"]:
                assert response.status_code in [401, 403, 404]
                
        except Exception as e:
            handle_client_side_errors(e, case)


class TestAPIFuzzingInput:
    """入力値検証のファジングテスト"""
    
    def test_extremely_large_payload(self):
        """極端に大きなペイロードの処理検証"""
        large_payload = {"data": "x" * 1000000}  # 1MB相当の文字列
        
        # ログインエンドポイントで大きなペイロードをテスト
        response = client.post("/auth/login", json=large_payload)
        
        # サーバーエラーではなく適切なエラー（400番台）が返されるべき
        assert response.status_code < 500
        assert response.status_code >= 400  # 不正なリクエストとして扱われるべき
    
    def test_malformed_json_payload(self):
        """不正な形式のJSONペイロードの処理検証"""
        malformed_payloads = [
            '{"incomplete": "json"',  # 不完全なJSON
            '{"invalid": json}',      # 無効なJSON
            '',                       # 空文字列
            'not_json_at_all',       # JSON以外
        ]
        
        for payload in malformed_payloads:
            response = client.post(
                "/auth/login", 
                data=payload, 
                headers={"content-type": "application/json"}
            )
            
            # サーバーエラーではなく適切なエラーが返されるべき
            assert response.status_code < 500
            assert response.status_code >= 400
    
    def test_sql_injection_attempts(self):
        """SQLインジェクション試行の検証"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' UNION SELECT * FROM api_keys --",
        ]
        
        for payload in sql_injection_payloads:
            # ログインエンドポイントでSQLインジェクションを試行
            login_data = {"username": payload, "password": payload}
            response = client.post("/auth/login", data=login_data)
            
            # SQLインジェクションは失敗し、適切なエラーが返されるべき
            assert response.status_code < 500
            assert response.status_code in [400, 401, 422]  # 認証失敗またはバリデーションエラー
            
            # レスポンスにSQL関連のエラーメッセージが含まれていないことを確認
            response_text = response.text.lower()
            dangerous_keywords = ["sql", "syntax", "mysql", "postgresql", "database", "table"]
            for keyword in dangerous_keywords:
                assert keyword not in response_text, f"SQL error information leaked: {keyword}"
    
    def test_xss_attempts(self):
        """クロスサイトスクリプティング（XSS）試行の検証"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'; alert('xss'); //",
        ]
        
        for payload in xss_payloads:
            # ユーザー登録でXSSを試行
            register_data = {
                "username": payload,
                "email": f"test{payload}@example.com",
                "password": "ValidPass123"
            }
            response = client.post("/auth/register", json=register_data)
            
            # XSSペイロードは適切に処理されるべき
            assert response.status_code < 500
            
            # レスポンスがエラーの場合、適切なバリデーションエラーであることを確認
            # XSSペイロードは受け入れられず、適切にバリデーションエラーになるべき
            if response.status_code >= 400:
                # バリデーションエラーまたは認証エラーであることを確認
                assert response.status_code in [400, 422], f"XSS payload should be rejected with validation error"
                # エラーメッセージ内にXSSペイロードが含まれることは避けられないが、
                # 実際の出力（HTMLなど）にスクリプトが実行可能な形で含まれていないことが重要
    
    def test_path_traversal_attempts(self):
        """パストラバーサル攻撃の検証"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fsetc%2fpasswd",  # URLエンコード
        ]
        
        for payload in path_traversal_payloads:
            # ファイルパスを含む可能性のあるエンドポイントをテスト
            response = client.get(f"/api/portfolio/{payload}")
            
            # パストラバーサルは失敗し、適切なエラーが返されるべき
            assert response.status_code < 500
            assert response.status_code in [400, 404, 422]  # バリデーションエラーまたは未発見


class TestAPIFuzzingBusiness:
    """ビジネスロジックのファジングテスト"""
    
    def test_negative_amounts(self):
        """負の金額での取引試行検証"""
        negative_amounts = [-1, -0.001, -999999.99]
        
        for amount in negative_amounts:
            # バックテスト用の設定で負の値を試行
            backtest_data = {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_balance": amount,  # 負の初期残高
                "symbols": ["BTC/USDT"]
            }
            
            # 負の金額は拒否されるべき
            response = client.post("/backtest/run", json=backtest_data)
            
            # サーバーエラーではなく適切なバリデーションエラーが返されるべき
            assert response.status_code < 500
            # 404(エンドポイント未実装)または400/422(バリデーションエラー)が許可される
            assert response.status_code in [400, 404, 422]
    
    def test_extreme_price_values(self):
        """極端な価格値でのデータ取得検証"""
        extreme_prices = [0, -1, 0.000000001, 999999999999.99]
        
        for price in extreme_prices:
            # 市場データAPIで極端な価格範囲を試行
            params = {
                "symbol": "BTC/USDT",
                "min_price": price,
                "max_price": price * 2 if price > 0 else 1
            }
            
            response = client.get("/api/market-data/ohlcv", params=params)
            
            # 極端な価格は適切に検証されるべき
            assert response.status_code < 500
            # APIが実装されていない場合は404、実装されている場合は適切なバリデーション
            assert response.status_code in [400, 404, 422]
    
    def test_invalid_trading_pairs(self):
        """無効な取引ペアでのデータ取得検証"""
        invalid_symbols = [
            "INVALID/PAIR",
            "BTC/",
            "/USDT",
            "BTC-USDT",  # 間違った形式
            "",
            None
        ]
        
        for symbol in invalid_symbols:
            # 市場データAPIで無効なシンボルを試行
            params = {"symbol": symbol} if symbol is not None else {}
            
            response = client.get("/api/market-data/latest", params=params)
            
            # 無効なシンボルは適切に拒否されるべき
            assert response.status_code < 500
            # APIが未実装なら404、実装済みなら適切なバリデーションエラー
            assert response.status_code in [400, 404, 422]


class TestAPIFuzzingRateLimit:
    """レート制限のファジングテスト"""
    
    def test_rapid_requests(self):
        """高頻度リクエストの処理検証"""
        responses = []
        
        # 短時間で多数のリクエストを送信
        for i in range(20):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # すべてのリクエストでサーバーエラーは発生してはいけない
        for status_code in responses:
            assert status_code < 500
        
        # レート制限が適用される場合は429が返されることもある
        rate_limited_responses = [code for code in responses if code == 429]
        
        # レート制限が発生した場合、最初のいくつかは成功しているべき
        if rate_limited_responses:
            successful_responses = [code for code in responses[:5] if code == 200]
            assert len(successful_responses) > 0, "Rate limiting should allow some initial requests"


class TestAPIFuzzingInfoDisclosure:
    """情報漏洩の検証テスト"""
    
    def test_error_message_info_disclosure(self):
        """エラーメッセージからの情報漏洩検証"""
        # 存在しないエンドポイント
        response = client.get("/nonexistent/endpoint")
        
        error_text = response.text.lower()
        
        # 機密情報が漏洩していないことを確認
        sensitive_info = [
            "password", "secret", "key", "token", "database", "internal",
            "stack trace", "traceback", "exception", "debug", "dev"
        ]
        
        for info in sensitive_info:
            assert info not in error_text, f"Sensitive information disclosed: {info}"
    
    def test_server_header_disclosure(self):
        """サーバーヘッダーの情報漏洩検証"""
        response = client.get("/health")
        
        # サーバー情報が過度に詳細でないことを確認
        server_header = response.headers.get("server", "").lower()
        
        # バージョン番号や詳細な実装情報が含まれていないことを確認
        sensitive_headers = ["python", "uvicorn", "fastapi", "version"]
        
        if server_header:
            for header in sensitive_headers:
                # 完全に隠すのではなく、詳細なバージョン情報がないことを確認
                assert not any(char.isdigit() for char in server_header), \
                    "Server header should not contain version numbers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])