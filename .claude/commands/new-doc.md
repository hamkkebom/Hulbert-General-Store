---
description: 새 문서를 스캐폴드하고 3곳 등록·재빌드·하네스 검사까지 실행
---

새 문서를 추가한다. 반복 실수(등록 누락)를 막기 위해 **반드시 스캐폴더를 먼저 실행**한다.

1. 스캐폴더 실행 (문서 생성 + viewer 등록 + 재빌드 + 하네스 검사):
   ```
   python3 tools/new_doc.py docs/<파일명>.md --title "<제목>" --group <그룹> --badge <이모지> --role "<역할>"
   ```
   그룹 코드: `idx A B C D E F G H` (경영·관리=E, 전략=F, 개념·브랜드=A …). 배지: `✅ 📝 ⚠️ 🕒 🗂`.

2. 스캐폴더가 안내한 **수동 등록**을 맥락에 맞는 자리에 마무리:
   - `docs/문서-지도.md` 표에 행 추가
   - `README.md` 관련 절에 링크
   - 공개 페이지면 `site/build_site.py`의 `PAGES`/`NAV`에 등록

3. 본문을 작성하고 `docs/작가-운영정책.md`의 운영 수치는 **재서술하지 말고 참조**한다.

4. 마무리 검증:
   ```
   python3 viewer/build.py && python3 site/build_site.py && python3 tools/harness_check.py
   ```
   하네스가 통과하면 완료. 규칙은 `CLAUDE.md` 참고.

사용자 입력(있으면): $ARGUMENTS
