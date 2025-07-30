#!/usr/bin/env python3
"""
テストファイル内のbackend.importをsrc.backend.に一括修正するスクリプト
"""
import re
from pathlib import Path


def fix_imports_in_file(file_path):
    """ファイル内のbackend.importを修正"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # backend.をsrc.backend.に置換（コメント行も含む）
        original_content = content
        content = re.sub(r"\bbackend\.", "src.backend.", content)

        # 変更があった場合のみファイルを更新
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🔧 Fixing backend. imports to src.backend. in test files...")

    # testsディレクトリ内のすべての.pyファイルを処理
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("❌ tests/ directory not found")
        return False

    fixed_count = 0
    total_count = 0

    # 再帰的にすべての.pyファイルを処理
    for py_file in tests_dir.rglob("*.py"):
        total_count += 1
        if fix_imports_in_file(py_file):
            fixed_count += 1

    print("\n📊 Summary:")
    print(f"   Total files processed: {total_count}")
    print(f"   Files modified: {fixed_count}")
    print(f"   Files unchanged: {total_count - fixed_count}")

    if fixed_count > 0:
        print(f"\n🎉 Successfully fixed {fixed_count} files!")
        print("   All backend. imports have been updated to src.backend.")
    else:
        print("\n✅ All files are already up to date!")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
