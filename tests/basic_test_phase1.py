#!/usr/bin/env python3
"""
Phase 1 の基本的なテスト（依存関係を最小限に）
"""
import sys
import os
from pathlib import Path

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_project_structure():
    """プロジェクト構造のテスト"""
    print("Testing project structure...")

    # 基本ディレクトリの確認
    required_dirs = [
        "backend",
        "backend/api",
        "backend/core",
        "backend/models",
        "backend/strategies",
        "backend/backtesting",
        "backend/risk",
        "backend/fee_models",
        "backend/exchanges",
        "backend/data_pipeline",
        "config",
        "tests",
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path} exists")
        else:
            print(f"❌ {dir_path} missing")
            return False

    # 基本ファイルの確認
    required_files = [
        "requirements.txt",
        "docker-compose.yml",
        ".env.example",
        ".gitignore",
        "README.md",
        "backend/main.py",
        "backend/core/config.py",
        "backend/core/security.py",
        "backend/core/database.py",
        "backend/exchanges/base.py",
        "backend/exchanges/binance.py",
        "backend/exchanges/bybit.py",
        "backend/exchanges/factory.py",
        "backend/data_pipeline/collector.py",
        "backend/data_pipeline/onchain.py",
        "config/risk_management.yml",
    ]

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False

    print("✓ Project structure test passed")
    return True


def test_config_files():
    """設定ファイルのテスト"""
    print("Testing config files...")

    # .env.example の確認
    env_example = Path(".env.example")
    if env_example.exists():
        content = env_example.read_text()
        required_vars = [
            "BINANCE_API_KEY",
            "BINANCE_SECRET",
            "BYBIT_API_KEY",
            "BYBIT_SECRET",
            "GLASSNODE_KEY",
            "CRYPTOQUANT_KEY",
            "JWT_SECRET",
            "ADMIN_USERNAME",
            "ADMIN_PASSWORD",
        ]

        for var in required_vars:
            if var in content:
                print(f"✓ {var} found in .env.example")
            else:
                print(f"❌ {var} missing in .env.example")
                return False
    else:
        print("❌ .env.example missing")
        return False

    # risk_management.yml の確認
    risk_config = Path("config/risk_management.yml")
    if risk_config.exists():
        content = risk_config.read_text()
        required_sections = [
            "risk_management",
            "strategies",
            "emergency_stop",
            "trading_costs",
        ]

        for section in required_sections:
            if section in content:
                print(f"✓ {section} section found in risk_management.yml")
            else:
                print(f"❌ {section} section missing in risk_management.yml")
                return False
    else:
        print("❌ risk_management.yml missing")
        return False

    print("✓ Config files test passed")
    return True


def test_code_syntax():
    """コードの構文チェック"""
    print("Testing code syntax...")

    python_files = [
        "backend/main.py",
        "backend/core/config.py",
        "backend/core/security.py",
        "backend/core/database.py",
        "backend/core/logging.py",
        "backend/api/auth.py",
        "backend/api/strategies.py",
        "backend/api/config.py",
        "backend/api/backtest.py",
        "backend/api/trades.py",
        "backend/risk/position_sizing.py",
        "backend/fee_models/base.py",
        "backend/fee_models/exchanges.py",
    ]

    for file_path in python_files:
        path = Path(file_path)
        if path.exists():
            try:
                # 構文チェック
                with open(path, "r") as f:
                    content = f.read()
                    compile(content, file_path, "exec")
                print(f"✓ {file_path} syntax OK")
            except SyntaxError as e:
                print(f"❌ {file_path} syntax error: {e}")
                return False
            except Exception as e:
                print(f"⚠️ {file_path} could not be checked: {e}")
        else:
            print(f"❌ {file_path} missing")
            return False

    print("✓ Code syntax test passed")
    return True


def test_requirements():
    """requirements.txtの確認"""
    print("Testing requirements.txt...")

    req_file = Path("requirements.txt")
    if req_file.exists():
        content = req_file.read_text()
        required_packages = [
            "fastapi",
            "uvicorn",
            "python-jose",
            "passlib",
            "python-dotenv",
            "pydantic",
            "duckdb",
            "pandas",
            "numpy",
            "ccxt",
            "httpx",
            "tenacity",
            "PyYAML",
        ]

        for package in required_packages:
            if package in content:
                print(f"✓ {package} found in requirements.txt")
            else:
                print(f"❌ {package} missing in requirements.txt")
                return False
    else:
        print("❌ requirements.txt missing")
        return False

    print("✓ Requirements test passed")
    return True


def test_docker_config():
    """Docker設定のテスト"""
    print("Testing Docker configuration...")

    docker_compose = Path("docker-compose.yml")
    if docker_compose.exists():
        content = docker_compose.read_text()
        required_services = ["backend", "redis", "prometheus", "grafana"]

        for service in required_services:
            if service in content:
                print(f"✓ {service} service found in docker-compose.yml")
            else:
                print(f"❌ {service} service missing in docker-compose.yml")
                return False
    else:
        print("❌ docker-compose.yml missing")
        return False

    print("✓ Docker configuration test passed")
    return True


def run_all_tests():
    """全てのテストを実行"""
    print("=== Phase 1 Basic Tests ===")
    print()

    tests = [
        test_project_structure,
        test_config_files,
        test_code_syntax,
        test_requirements,
        test_docker_config,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()

    print("=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All Phase 1 basic tests passed!")
        return True
    else:
        print(f"\n❌ {failed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n✅ Phase 1 の基本構造とファイルが正常に作成されました！")
        print("🚀 Phase 2 - バックテスト基盤の実装に進みます...")
        exit(0)
    else:
        print("\n❌ Phase 1 の基本テストに失敗しました")
        exit(1)
