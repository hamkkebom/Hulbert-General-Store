#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""헐버트 저장소 — 상태 스냅샷 (Observability 하네스).

문서 저장소의 건강도를 한눈에 보여주는 대시보드. 검사(harness_check)가
'통과/실패'를 판정한다면, 이 리포트는 '지금 어떤 상태인가'를 보여준다.
비파괴·비실패(항상 exit 0) — 언제든 실행해 현황을 본다.

  python3 tools/harness_report.py
"""
import os, re, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BADGE_NAME = {"✅": "확정", "📝": "초안", "⚠️": "검토필요", "🕒": "다음시점", "🗂": "범위밖"}

docs = sorted(glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True))
status = collections.Counter()
decisions, tbd_docs = 0, 0
drift_watch = collections.Counter()

for p in docs:
    with open(p, encoding="utf-8") as f:
        text = f.read()
    head = "\n".join(text.splitlines()[:6])
    mb = re.search(r"🏷️\s*\*\*\s*(\S+)", head)
    if mb:
        for b in BADGE_NAME:
            if b in mb.group(1):
                status[b] += 1
                break
    # 결정 필요·TBD 인벤토리
    decisions += len(re.findall(r"결정 필요|결정 현황|🕒 \*\*", text))
    if "TBD" in text:
        tbd_docs += 1
    # 드리프트 워치(예시 수치 산재 정도 — 정보용)
    for pat in ("30%", "4주", "8주", "월 1회"):
        if pat in text:
            drift_watch[pat] += 1

# 공개 사이트 페이지 수
try:
    with open(os.path.join(ROOT, "site", "build_site.py"), encoding="utf-8") as f:
        site_pages = len(re.findall(r'^\s*\("[a-z]*",\s+"[^"]+ — 헐버트', f.read(), re.M))
except FileNotFoundError:
    site_pages = "?"

print("═══ 헐버트 저장소 상태 스냅샷 ═══════════════════════")
print(f"\n문서 총 {len(docs)}개")
for b, n in BADGE_NAME.items():
    print(f"  {b} {n:<6} {status.get(b, 0)}개")
print(f"\n공개 사이트 페이지: {site_pages}개")
print(f"결정 대기 항목(결정 필요/현황 표기): 약 {decisions}건")
print(f"TBD 포함 문서: {tbd_docs}개")
print("\n드리프트 워치(예시 수치가 등장하는 문서 수 — 운영정책 단일 출처 유지 대상):")
for pat, n in drift_watch.items():
    print(f"  '{pat}' → {n}개 문서")
print("\n(규칙 위반 판정은 python3 tools/harness_check.py)")
