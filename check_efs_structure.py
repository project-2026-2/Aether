#!/usr/bin/env python3
"""
로컬 저장 구조 테스트 스크립트
사용자별 EFS 디렉토리 구조를 확인합니다.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 설정값
EFS_ROOT = Path(os.getenv("EFS_ROOT", "efs_data"))
USER_DATA_ISOLATION = os.getenv("USER_DATA_ISOLATION", "true").lower() == "true"

print("=" * 70)
print("🔍 Aether 로컬 저장 구조 분석")
print("=" * 70)

print(f"\n📍 EFS_ROOT: {EFS_ROOT.resolve()}")
print(f"🔐 USER_DATA_ISOLATION: {USER_DATA_ISOLATION}")

print("\n" + "=" * 70)
print("📂 디렉토리 구조 트리")
print("=" * 70)

def print_tree(directory, prefix="", is_last=True, max_depth=5, current_depth=0):
    """디렉토리 구조를 트리 형태로 출력"""
    if current_depth >= max_depth:
        return

    if not directory.exists():
        return

    try:
        entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        print(f"{prefix}❌ 접근 권한 없음")
        return

    for i, entry in enumerate(entries):
        is_last_entry = i == len(entries) - 1
        current = "└── " if is_last_entry else "├── "
        next_prefix = prefix + ("    " if is_last_entry else "│   ")

        if entry.is_dir():
            print(f"{prefix}{current}📁 {entry.name}/")
            print_tree(entry, next_prefix, is_last_entry, max_depth, current_depth + 1)
        else:
            # 파일 크기 표시
            size = entry.stat().st_size
            size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB"
            print(f"{prefix}{current}📄 {entry.name} ({size_str})")

if EFS_ROOT.exists():
    print_tree(EFS_ROOT)
else:
    print(f"\n⚠️  {EFS_ROOT} 디렉토리가 아직 생성되지 않았습니다.")
    print("   (첫 파일 업로드 시 자동으로 생성됩니다)\n")

print("\n" + "=" * 70)
print("📊 사용자별 저장 위치")
print("=" * 70)

# 사용자별 정보 표시
users_dir = EFS_ROOT / "users"
if users_dir.exists():
    user_dirs = [d for d in users_dir.iterdir() if d.is_dir()]
    if user_dirs:
        print(f"\n🔍 발견된 사용자: {len(user_dirs)}명\n")
        for user_dir in sorted(user_dirs):
            username = user_dir.name
            meta_file = user_dir / "meta.json"
            files_dir = user_dir / "files"

            print(f"👤 {username}")
            print(f"   📁 경로: {user_dir.resolve()}")
            print(f"   📄 메타: {meta_file.resolve()}")
            print(f"   📂 파일: {files_dir.resolve()}")

            # meta.json 분석
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    file_count = len(meta)
                    total_size = sum(int(f.get('size', 0)) for f in meta.values())
                    print(f"   ✅ 파일 개수: {file_count}개")
                    print(f"   💾 총 용량: {total_size:,}B ({total_size/1024/1024:.2f}MB)")

                    # 파일 목록
                    if file_count > 0:
                        print(f"   📋 파일 목록:")
                        for fid, finfo in meta.items():
                            fname = finfo.get('name', 'Unknown')
                            fsize = int(finfo.get('size', 0))
                            ftrashed = finfo.get('trashed', False)
                            status = "🗑️ (휴지통)" if ftrashed else "✅"
                            print(f"      {status} {fname} ({fsize:,}B)")
                except json.JSONDecodeError:
                    print(f"   ⚠️  meta.json 파일이 손상되었습니다")
            else:
                print(f"   ℹ️  아직 파일이 없습니다")

            print()
    else:
        print("\n   ℹ️  아직 사용자가 생성되지 않았습니다.")
        print("   (첫 회원가입 후 자동으로 디렉토리가 생성됩니다)\n")
else:
    print("\n   ℹ️  users 디렉토리가 아직 생성되지 않았습니다.\n")

print("=" * 70)
print("💡 사용 방법")
print("=" * 70)
print("""
1. 서버 시작:
   cd /Users/chies/PycharmProjects/Aether
   python src/app.py

2. 브라우저에서:
   http://localhost:5050

3. 회원가입/로그인 후 파일 업로드

4. 저장 위치 확인:
   python check_efs_structure.py

5. 사용자별 격리 확인:
   # userA와 userB의 파일이 각각 다른 디렉토리에 저장되어 있는지 확인
""")

print("\n" + "=" * 70)
print("✅ 분석 완료!")
print("=" * 70)

