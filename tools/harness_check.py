#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""헐버트 저장소 — 콘텐츠 일관성 하네스 (문서 회귀 테스트).

Playwright(렌더된 HTML 검사)를 넘어, **문서 자체의 규칙**을 검사한다.
'harness engineering'의 Verification 계층 — 이 저장소를 AI가 드리프트 없이
유지하게 하는 게이트. CI(pull_request/push)와 SessionStart 훅에서 실행.

검사:
  1) 등록 정합성   — docs/**/*.md ↔ viewer/build.py DOCS 일치 + 문서-지도 색인 링크
  2) 상태 배지      — 모든 문서 상단에 🏷️ + 배지값이 유효 집합(✅📝⚠️🕒🗂)
  3) 내부 링크      — 문서 간 .md 링크의 대상 파일 존재
  4) 수수료 축 드리프트 — 폐기된 '낸 제품 수 (예시)' 표 사용 금지(운영정책='칸' 단일)
  5) 금지 보이스    — '모시겠습니다/모십니다' + 과장어(업계 최저·압도적·놓치면 후회)
                     실사용 금지(브랜드-정의서 §6·§9 금지어 정의는 예외)
  6) 빌드 신선도    — viewer/sources.json이 현재 docs와 일치(재빌드/커밋 누락 감지)
  7) 공개 플레이스홀더 누출 — (_site 존재 시) 공개 HTML에 원시 [TBD]·[@인스타] 대괄호 0개

통과=exit 0, 위반=exit 1(+상세). 경고(INFO)는 실패시키지 않는다.
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors, infos = [], []
def err(msg): errors.append(msg)
def info(msg): infos.append(msg)

# ── 0. 대상 문서 수집 ───────────────────────────────────────────────
disk_docs = sorted(
    os.path.relpath(p, ROOT).replace("\\", "/")
    for p in glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True)
)

# viewer/build.py DOCS 목록 파싱
with open(os.path.join(ROOT, "viewer", "build.py"), encoding="utf-8") as f:
    build_src = f.read()
registered = re.findall(r'\(\s*"((?:docs/[^"]+|README\.md))"', build_src)
registered_docs = sorted(d for d in registered if d.startswith("docs/"))

# ── 1. 등록 정합성 (뷰어 + 문서-지도) ─────────────────────────────
missing = sorted(set(disk_docs) - set(registered_docs))   # 디스크에 있으나 뷰어 미등록
orphan  = sorted(set(registered_docs) - set(disk_docs))    # 뷰어에 등록됐으나 파일 없음
for m in missing: err(f"[등록] 뷰어(viewer/build.py DOCS)에 미등록된 문서: {m}")
for o in orphan:  err(f"[등록] 뷰어에 등록됐으나 파일이 없음: {o}")

# 모든 문서는 문서-지도(색인)에도 링크되어야 한다.
DOCMAP = "docs/문서-지도.md"
with open(os.path.join(ROOT, DOCMAP), encoding="utf-8") as f:
    docmap_text = f.read()
for d in disk_docs:
    if d == DOCMAP:
        continue
    base = os.path.basename(d)[:-3]  # 파일명(확장자 제거)
    if f"{base}.md)" not in docmap_text and f"({base})" not in docmap_text:
        err(f"[색인] 문서-지도(docs/문서-지도.md)에 링크되지 않은 문서: {d}")

# ── 2. 상태 배지 ───────────────────────────────────────────────────
for d in disk_docs:
    with open(os.path.join(ROOT, d), encoding="utf-8") as f:
        head = "".join([next(f, "") for _ in range(6)])
    if "🏷️" not in head:
        err(f"[배지] 상단 6줄에 상태 배지(🏷️) 없음: {d}")

# ── 3. 내부 .md 링크 대상 존재 ─────────────────────────────────────
link_re = re.compile(r'\]\(([^)]+?\.md)(#[^)]*)?\)')
for d in disk_docs:
    ddir = os.path.dirname(os.path.join(ROOT, d))
    with open(os.path.join(ROOT, d), encoding="utf-8") as f:
        text = f.read()
    for m in link_re.finditer(text):
        href = m.group(1)
        if href.startswith(("http://", "https://")):
            continue
        target = os.path.normpath(os.path.join(ddir, href))
        if not os.path.exists(target):
            err(f"[링크] {d} → 존재하지 않는 대상: {href}")

# ── 4. 수수료 축 드리프트 (폐기된 '낸 제품 수' 표) ────────────────
#   운영정책·계약서·개념 정본은 '칸'으로 통일됨. 폐기된 표 헤더 사용 금지.
#   (로드맵의 '칸 vs 낸 제품 수?' 결정 질문은 정상 — 아래 정확 패턴만 검사)
RETIRED = ["낸 제품 수 (예시)", "| 적음 (1~3개)", "| 보통 (4~10개)", "| 많음 (11개~)"]
for d in disk_docs:
    with open(os.path.join(ROOT, d), encoding="utf-8") as f:
        text = f.read()
    for pat in RETIRED:
        if pat in text:
            err(f"[수수료축] 폐기된 '제품 수' 표 잔존({pat!r}) — '점유 칸' 축으로 통일 필요: {d}")

# ── 5. 금지 보이스 실사용 (존대어 + 과장 광고 상투어) ──────────────
#   브랜드-정의서 §6·§9가 금지어로 정의하는 표현들. 브랜드-정의서 자신은 예외.
#   '무조건'은 "무조건 좋은 게 아니다"처럼 정상 용법이 흔해 제외(오탐 방지).
BANNED = re.compile(r'모시겠습니다|모십니다|업계 최저|압도적|놓치면 후회')
for d in disk_docs:
    if d == "docs/브랜드-정의서.md":
        continue
    with open(os.path.join(ROOT, d), encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            m = BANNED.search(line)
            if m:
                err(f"[보이스] 금지 표현 사용({m.group(0)!r}) {d}:{i} — 브랜드-정의서 §6·§9 위반")

# ── 5b. 상태 배지 값 유효성 (✅ 📝 ⚠️ 🕒 🗂 중 하나) ───────────────
BADGES = ("✅", "📝", "⚠️", "🕒", "🗂")
for d in disk_docs:
    with open(os.path.join(ROOT, d), encoding="utf-8") as f:
        head = "".join([next(f, "") for _ in range(6)])
    mb = re.search(r"🏷️\s*\*\*\s*(\S+)", head)
    if mb and not any(b in mb.group(1) for b in BADGES):
        err(f"[배지] 알 수 없는 상태 배지값({mb.group(1)!r}) — {BADGES} 중 하나여야: {d}")

# ── 5c. 빌드 신선도 (viewer/sources.json ↔ 현재 docs 일치) ─────────
#   문서를 고치고 재빌드/커밋을 잊으면 산출물이 낡는다 → 드리프트. 이를 잡는다.
try:
    import json
    with open(os.path.join(ROOT, "viewer", "sources.json"), encoding="utf-8") as f:
        src = json.load(f)
    for i, rel in enumerate(registered):   # registered = viewer DOCS 순서(README 포함)
        cur = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        if src.get(str(i)) != cur:
            err(f"[신선도] viewer/sources.json이 현재 문서와 다름 — 재빌드 필요: {rel} "
                f"(python3 viewer/build.py)")
            break
except FileNotFoundError:
    info("viewer/sources.json 없음 — 빌드 신선도 검사 건너뜀.")

# ── 6. 공개 플레이스홀더 누출 (_site 빌드 산출물이 있을 때만) ──────
site_dir = os.path.join(ROOT, "_site")
if os.path.isdir(site_dir):
    leak_re = re.compile(r'@?\[\s*[^\]]*(?:TBD|인스타|지원폼|상세 주소|운영 시간|이메일 주소|연락처)[^\]]*\]')
    for p in glob.glob(os.path.join(site_dir, "**", "*.html"), recursive=True):
        if "/viewer/" in p.replace("\\", "/"):
            continue  # 내부 뷰어는 원문 편집기라 예외
        with open(p, encoding="utf-8") as f:
            html = f.read()
        for m in leak_re.finditer(html):
            err(f"[누출] 공개 HTML에 원시 플레이스홀더 노출: {os.path.relpath(p, ROOT)} → {m.group(0)}")
else:
    info("_site 미빌드 — 공개 플레이스홀더 검사 건너뜀(CI는 빌드 후 실행).")

# ── 참고(비실패) 정보 ──────────────────────────────────────────────
info(f"문서 {len(disk_docs)}개 · 뷰어 등록 {len(registered_docs)}개 검사.")

# ── 결과 ───────────────────────────────────────────────────────────
print("── 헐버트 콘텐츠 하네스 검사 ─────────────────────")
for m in infos:  print("  · " + m)
if errors:
    print(f"\n❌ 위반 {len(errors)}건:")
    for e in errors: print("  ✗ " + e)
    print("\n실패 — 위 항목을 고친 뒤 다시 실행하세요.")
    sys.exit(1)
print(f"\n✅ 통과 — 문서 규칙 위반 없음.")
sys.exit(0)
