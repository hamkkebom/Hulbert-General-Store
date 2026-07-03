#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""새 문서 스캐폴더 — 반복 등록 작업을 자동화하는 Tooling 하네스.

`새 문서 → 상태 배지 → viewer 등록 → 문서-지도 안내 → 재빌드 → 하네스 검사`를
한 명령으로. 등록 누락(하네스가 잡는 대표 실수)을 애초에 방지한다.

사용:
  python3 tools/new_doc.py docs/새문서.md --title "제목" --group E --badge 📝 --role "역할 설명"

그룹 코드: idx A B C D E F G H  (viewer/build.py GROUP_ORDER 참고)
실행 후 문서-지도·README 링크는 안내에 따라 손으로 추가(맥락에 맞는 자리 필요).
"""
import argparse, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUP_LABELS = {"idx": "인덱스", "A": "개념·브랜드", "B": "작가촌 사이트",
                "C": "운영·계약", "D": "모집", "E": "경영·관리", "F": "전략",
                "G": "범위 밖", "H": "법적 고지"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="새 문서 경로 (예: docs/새문서.md)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--group", required=True, choices=list(GROUP_LABELS))
    ap.add_argument("--badge", default="📝", help="상태 이모지(✅ 📝 ⚠️ 🕒 🗂)")
    ap.add_argument("--role", default="", help="배지 옆 역할 설명")
    a = ap.parse_args()

    rel = os.path.relpath(a.path, ROOT).replace("\\", "/") if os.path.isabs(a.path) else a.path
    if not rel.startswith("docs/") or not rel.endswith(".md"):
        sys.exit("경로는 docs/ 아래 .md 여야 합니다.")
    abspath = os.path.join(ROOT, rel)
    if os.path.exists(abspath):
        sys.exit(f"이미 존재: {rel}")

    # 1) 문서 생성(상태 배지 포함)
    role = f" · {a.role}" if a.role else ""
    body = (f"# {a.title}\n\n"
            f"> 🏷️ **{a.badge} 초안** · 갱신 2026-07{role}\n\n"
            f"> (여기에 내용을 작성하세요.)\n\n---\n\n## 1. \n\n")
    os.makedirs(os.path.dirname(abspath), exist_ok=True)
    with open(abspath, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"✔ 생성: {rel}")

    # 2) viewer/build.py DOCS 목록에 등록(그룹의 마지막 항목 뒤에 삽입)
    bp = os.path.join(ROOT, "viewer", "build.py")
    with open(bp, encoding="utf-8") as f:
        src = f.read()
    label = GROUP_LABELS[a.group]
    entry = f'    ("{rel}", {" " * max(1, 22 - len(rel))}"{a.group}", "{label}"),\n'
    # 같은 그룹의 마지막 DOCS 라인 뒤에 삽입
    lines = src.splitlines(keepends=True)
    last_idx = None
    for i, ln in enumerate(lines):
        if re.match(r'\s*\("docs/.+",\s*"' + re.escape(a.group) + r'"\s*,', ln):
            last_idx = i
    if last_idx is not None:
        lines.insert(last_idx + 1, entry)
        with open(bp, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✔ viewer/build.py DOCS 등록(그룹 {a.group})")
    else:
        print(f"⚠ viewer/build.py에서 그룹 {a.group} 위치를 못 찾음 — 수동 등록 필요")

    # 3) 재빌드 + 하네스 검사
    print("· 재빌드…")
    for cmd in (["python3", "viewer/build.py"], ["python3", "site/build_site.py"]):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    print("· 하네스 검사…")
    r = subprocess.run(["python3", "tools/harness_check.py"], cwd=ROOT)

    # 4) 남은 수동 작업 안내(맥락 자리 필요)
    print("\n── 남은 수동 등록(맥락에 맞는 자리에) ─────────────")
    print(f"  1) docs/문서-지도.md 표에 행 추가:  | [`{os.path.basename(rel)[:-3]}`]({os.path.basename(rel)}) | {a.badge} | … |")
    print(f"  2) README.md 관련 절에 링크 추가")
    print(f"  3) 공개 페이지면 site/build_site.py PAGES/NAV 등록")
    print("  → 이후 python3 tools/harness_check.py 로 색인 검사까지 통과 확인")
    sys.exit(r.returncode)

if __name__ == "__main__":
    main()
