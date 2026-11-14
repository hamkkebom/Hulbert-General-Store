#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""헐버트작가촌 모집 사이트 빌더 (docs/기술-사양.md 정본 구현).

원천: docs/ 카피 문서 → 정적 HTML(_site/). 홈은 홈-랜딩-카피.md 11블록의
구조화 템플릿(카피 수정은 정본 md에 먼저 → 여기 반영), 내부 페이지는 md 렌더.
실데이터는 site/config.json 단일 소스 — 미확정(null)은 '준비 중'으로 정직하게 표기.
뷰어(viewer/)는 /viewer/ 하위에 내부 도구로 동봉된다.
"""
import json, os, re, shutil, html as htmllib
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT  = os.path.join(ROOT, "_site")

with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

def cfg(key, fallback_key=None, default="준비 중"):
    v = CFG.get(key)
    if v: return v
    if fallback_key and CFG.get(fallback_key): return CFG[fallback_key]
    return default

# ──────────────────────────── 페이지 정의 ────────────────────────────
# (경로, 제목, 설명, 원천 md — None이면 커스텀 빌드)
PAGES = [
    ("",        "헐버트작가촌 — 잃을 걱정 없이, 하고 싶은 창작만", "경복궁 옆 서촌 한옥. 입점비 0원, 가격은 작가가, 안 팔린 달엔 0원. 함께할 작가를 찾습니다.", None),
    ("about",   "우리는 누구인가 — 헐버트작가촌", "한글을 사랑한 헐버트처럼, 작가를 뒤에서 받칩니다. 함께·공평·투명.", "docs/pages/소개.md"),
    ("space",   "당신의 작품이 놓일 곳 — 헐버트작가촌", "경복궁 옆 서촌 한옥. 100평대 마루와 마당, 한지에 스민 햇살 위에 작품이 놓입니다.", "docs/pages/공간소개.md"),
    ("policy",  "함께 일하는 규칙 — 헐버트작가촌", "입점비 0원, 가격은 작가가, 수수료는 한옥 고정비로 전액. 운영 규칙을 정직하게 공개합니다.", "docs/pages/운영정책.md"),
    ("apply",   "합류하기 — 헐버트작가촌", "거창한 서류 없이 세 가지만 — 작품 사진, 꿈 한 문장, 한글 이름. 당신의 꿈은 무엇인가요?", "docs/pages/합류하기.md"),
    ("makers",  "함께하는 작가들 — 헐버트작가촌", "같은 꿈을 가진 동료들. 다음 빈자리의 주인공은 당신일 수 있어요.", None),
    ("news",    "소식 · 공지 — 헐버트작가촌", "작가 모집·행사·로테이션 소식을 숨김 없이 투명하게 전합니다.", "docs/pages/소식.md"),
    ("contact", "문의 · FAQ — 헐버트작가촌", "궁금한 건 무엇이든. 수수료·퇴점·정산까지 FAQ에 정직하게 담았습니다.", "docs/pages/문의.md"),
    ("guide",   "작가 가이드 — 헐버트작가촌", "지원부터 정산·성장까지, 어떻게 하는지 단계별로 안내합니다.", "docs/작가-가이드.md"),
    ("academy", "헐버트 아카데미 — 헐버트작가촌", "작품 사진·가격 책정·SNS·세무·성장까지 — 작가로 더 잘 살아남는 법.", "docs/작가촌-아카데미.md"),
    ("magazine", "작가 이야기 — 헐버트작가촌", "작품 너머의 사람. 헐버트·서촌 이야기와 작가 인터뷰를 기록합니다.", "docs/작가촌-매거진.md"),
]
NAV = [("about", "소개"), ("space", "공간"), ("makers", "작가들"),
       ("guide", "가이드"), ("academy", "아카데미"), ("magazine", "이야기"),
       ("news", "소식"), ("contact", "문의")]

# ──────────────────────────── md → HTML 변환 ────────────────────────────
def gh_slug(text, sep="-"):
    # 뷰어(viewer/build.py)와 동일한 슬러그 규칙 — 제목 앵커 ID 생성(한글 유지)
    s = htmllib.unescape(text).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s", sep, s.strip())
    return s

def flatten_toc(tokens):
    # markdown toc 확장의 중첩 토큰을 (레벨, id, 이름) 평면 목록으로
    out = []
    for t in tokens:
        out.append((t["level"], t["id"], t["name"]))
        out.extend(flatten_toc(t.get("children", [])))
    return out

# ──────────────────────────── 공개용 정리 (문서 원본은 그대로 두고 렌더 단계에서만) ────────────────────────────
# 문서에는 운영자·디자이너용 표기(〔버튼〕, `[ 텍스트 입력 ]`, 꼭지 번호 ①②③, 이모지)가 섞여 있다.
# 뷰어에서는 유효한 작업 메모지만, 공개 페이지에선 내부 메모로 보이므로 여기서 걷어낸다.
PAGE_H1 = {
    "docs/작가-가이드.md": "작가 가이드",
    "docs/작가촌-아카데미.md": "헐버트 아카데미",
    "docs/작가촌-매거진.md": "작가 이야기",
}
PAGE_TWEAKS = {
    "docs/pages/소식.md": [
        (r"^## ① 인트로\n", ""),
        (r"^## ② 게시물 유형\n", "## 소식의 종류\n"),
        (r"^> 글머리에.*\n", ""),
        (r"^\| 유형 배지 \| 무엇을 올리나 \| 주요 독자 \|", "| 종류 | 무엇을 올리나 | 누구에게 |"),
        (r"^## ③ 예시 게시물 2개\n", "## 최근 소식 `예시`\n"),
        (r"^### 게시물 \d+ — 〔([^〕]+)〕 \(예시\)\n", r"### \1 `예시`\n"),
        (r"^> 톤은 작가 모집 키트.*\n", ""),
        (r"^`〔[^〕]+〕` · 예시 날짜: .*\n", ""),
        (r"^👉 지원: .*\n", "지원 채널과 위치는 준비 중입니다 — 열리는 대로 합류하기 페이지에서 안내합니다.\n"),
        (r"^📍 위치: .*\n", ""),
    ],
    "docs/작가-가이드.md": [
        # 글자로 그린 흐름도 → 단계 목록
        (r"^```\n지원 → 큐레이션[^`]*```\n",
         '<ol class="flow"><li>지원</li><li>큐레이션</li><li>입점 확정</li><li>작품 등록·표시</li>'
         '<li>진열·로테이션</li><li>판매·정산</li><li class="opt">퇴점·재입점</li></ol>\n'
         '<p class="flow-opt">원하면 <strong>2단계 너투사</strong> → <strong>3단계 나투사</strong>로 이어집니다.</p>\n'),
    ],
    "docs/작가촌-매거진.md": [
        (r"^> 📌 인터뷰 한 줄 인용은.*\n", ""),
        (r"^> 코너:.*\n", ""),
    ],
}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐️‍]+[ \t]?")

def public_clean(path, body):
    for pat, rep in PAGE_TWEAKS.get(path, []):
        body = re.sub(pat, rep, body, flags=re.M)
    # UI 설계 표기만 있는 줄, 입력란 표기
    body = re.sub(r"^〔(?:라벨|필터 칩|버튼)〕.*\n", "", body, flags=re.M)
    body = re.sub(r"[ \t]*`\[[^\]`\n]*(?:입력|첨부)[^\]`\n]*\]`", "", body)
    body = re.sub(r"[〔〕]", "", body)
    # 필수 표시: 별 이모지 → '필수' 배지
    body = body.replace("별표(⭐)는 필수 항목입니다", "'필수' 표시가 붙은 항목만 꼭 채워주세요")
    body = re.sub(r"[ \t]*⭐", " `필수`", body)
    # 제목 앞 꼭지 번호·대괄호 꼬리표
    body = re.sub(r"^(#{2,3}) [①-⑳]\s*", r"\1 ", body, flags=re.M)
    body = re.sub(r"^(#{2,3}) \[([^\]\n]+)\]\s*", r"\1 \2 — ", body, flags=re.M)
    # 문단 바로 아래 붙은 목록이 한 줄로 뭉치지 않게 빈 줄 삽입
    body = re.sub(r"^(?![-*] |\d+\. |>|\||#|\s|`{3})([^\n]+)\n(?=[-*] |\d+\. )", r"\1\n\n", body, flags=re.M)
    return body

def render_md(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        text = f.read()
    # 상단 메타(제목 배지·페이지 노트)는 내부용 — 첫 '---' 전까지 제거, 제목만 유지
    m = re.match(r"# (.+)\n", text)
    page_h1 = re.sub(r"\s*\(/[a-z]+\)\s*$", "", m.group(1)).strip() if m else ""
    page_h1 = PAGE_H1.get(path, page_h1)
    first_hr = text.find("\n---\n")
    body = text[first_hr + 5:] if first_hr != -1 else text
    # 운영자용·내부 섹션 제거(공개 페이지엔 노출 금지) — 가장 먼저 나오는 지점에서 자름
    body = re.split(r"\n#{2,3} [^\n]*🛠", body)[0]
    body = re.split(r"\n#{2,3} [^\n]*운영자", body)[0]
    body = re.split(r"\n#{2,3} [^\n]*게시 가이드", body)[0]
    body = re.split(r"\n## ④ 운영 가이드.*", body)[0]
    body = public_clean(path, body)
    md = markdown.Markdown(
        extensions=["extra", "toc", "sane_lists", "attr_list"],
        extension_configs={"toc": {"slugify": gh_slug, "separator": "-"}},
    )
    html = md.convert(body)
    # 제목 앵커(h2·h3) 목록 — 좌측 목차(TOC)용. 뷰어와 동일하게 2개 이상일 때만.
    headings = [(lvl, hid, name) for lvl, hid, name in flatten_toc(md.toc_tokens) if lvl in (2, 3)]
    html = transform(html, SLOT_IMG.get(path, ()))
    html = EMOJI_RE.sub("", html).replace("<code>필수</code>", '<span class="req">필수</span>')
    headings = [(lvl, hid, EMOJI_RE.sub("", name).strip()) for lvl, hid, name in headings]
    return page_h1, html, headings

def _toc_links(headings):
    return "".join(
        f'<a class="{"lvl3" if lvl == 3 else "lvl2"}" href="#{hid}">{htmllib.escape(name)}</a>'
        for lvl, hid, name in headings)

def pagetoc_aside(headings):
    # 좌측 sticky 목차(데스크톱) — 표제가 2개 미만이면 생략(뷰어 규칙과 동일)
    if len(headings) < 2:
        return ""
    return ('<aside class="pagetoc" aria-label="목차">'
            '<div class="pagetoc-inner"><p class="pagetoc-head">목차</p>'
            f'<nav>{_toc_links(headings)}</nav></div></aside>')

def pagetoc_mobile(headings):
    # 좁은 화면용 접이식 목차(상단) — 모바일에도 '모든 페이지 목차' 제공
    if len(headings) < 2:
        return ""
    return ('<details class="pagetoc-m"><summary>목차</summary>'
            f'<nav>{_toc_links(headings)}</nav></details>')

NOLINK = "#__nolink__"

# 문서의 📷 사진 자리(등장 순서)에 넣을 사진 — None이면 "사진 준비 중" 자리 유지.
# 실제 사진을 받으면 site/assets/img/의 같은 파일명으로 덮어쓴다(출처: CREDITS.md).
SLOT_IMG = {
    "docs/pages/공간소개.md": ["courtyard.jpg", "hall.jpg", "on-chest.jpg", "price-tags.jpg", "alley.jpg"],
}
# 실제 촬영 사진 — 어디 사진인지 캡션에 밝힌다(출처: CREDITS.md).
REAL = {"courtyard.jpg": "서촌 한옥 '함께봄'", "hall.jpg": "서촌 한옥 '함께봄'"}
# AI로 생성한 연출 이미지 — 실제 촬영본으로 덮어쓴 파일은 여기서 빼면 표기가 사라진다.
GENERATED = {"on-chest.jpg", "price-tags.jpg", "maker-pottery.jpg"}

def photo_ref(fn):
    if fn in REAL:
        return f"{REAL[fn]} 실제 사진"
    return ("AI로 만든 연출 이미지" if fn in GENERATED else "참고 이미지") + " · 실제 공간 사진으로 바뀝니다"

# 공개 페이지가 없는 내부 문서 이름(코드 표기) → 해당 공개 페이지 링크
DOC_LINK = {"작가-운영정책": ("policy", "운영 규칙"), "작가-소개": ("about", "소개"),
            "작가촌-아카데미": ("academy", "아카데미"), "작가-가이드": ("guide", "작가 가이드"),
            "작가촌-매거진": ("magazine", "작가 이야기")}

def transform(html, slot_imgs=()):
    html = re.sub(r"<li>\s*[◻☐□]\s*", '<li class="chk">', html)
    # 📷 사진 자리 블록 → 스타일된 플레이스홀더
    def photo(m):
        inner = re.sub(r"</?p>", " ", m.group(1))
        inner = re.sub(r"\[사진 자리\s*[—-]?\s*", "", inner).replace("📷", "").replace("]", "")
        inner = re.sub(r"\*", "", inner).strip()
        # '캡션 예시:'는 내부 작업 라벨 — 공개 화면엔 라벨 없이 캡션 문장만 보여 준다
        desc, _, cap = inner.partition("캡션 예시:")
        desc, cap = desc.strip(), cap.strip().strip('"“”').strip()
        desc_txt = re.sub(r"<[^>]+>", "", desc)
        i = photo.n; photo.n += 1
        fn = slot_imgs[i] if i < len(slot_imgs) else None
        if fn:
            cap_html = f"{cap} " if cap else ""
            return (f'<figure class="photo-fig"><img src="../assets/img/{fn}" alt="{htmllib.escape(desc_txt)}" loading="lazy">'
                    f'<figcaption>{cap_html}<span class="ps-ref">{photo_ref(fn)}</span></figcaption></figure>')
        cap_html = f'<span class="ps-cap">{cap}</span>' if cap else ""
        return ('<figure class="photo-slot">'
                f'<figcaption><span class="ps-wait">사진 준비 중 — {desc_txt}</span>{cap_html}</figcaption></figure>')
    photo.n = 0
    # 다른 문단 뒤에 붙어 한 인용구로 합쳐진 📷 문단은 따로 떼어 낸다
    html = re.sub(r"\n<p>📷((?:(?!</p>).)*)</p>\s*</blockquote>",
                  r"\n</blockquote>\n<blockquote>\n<p>📷\1</p>\n</blockquote>", html, flags=re.S)
    html = re.sub(r"<blockquote>\s*</blockquote>\s*", "", html)  # 떼어 내고 남은 빈 인용구 제거
    html = re.sub(r"<blockquote>\s*<p>📷(.*?)</p>\s*</blockquote>", photo, html, flags=re.S)
    # 문서 간 .md 링크 → 사이트 경로
    link_map = {"합류하기": "../apply/", "문의": "../contact/", "소개": "../about/",
                "공간소개": "../space/", "운영정책": "../policy/", "작가들": "../makers/",
                "소식": "../news/", "작가-운영정책": "../policy/", "작가-소개": "../about/",
                "작가-가이드": "../guide/", "작가촌-아카데미": "../academy/",
                "작가촌-매거진": "../magazine/"}
    def relink(m):
        base = m.group(1).split("/")[-1].replace(".md", "")
        return f'href="{link_map.get(base, NOLINK)}"'
    html = re.sub(r'href="([^"]+\.md)(?:#[^"]*)?"', relink, html)
    # 공개 페이지가 없는 내부 문서로의 링크는 죽은 '#' 링크 대신 글자만 남긴다
    html = re.sub(r'<a href="%s"[^>]*>(?:<code>)?(.*?)(?:</code>)?</a>' % NOLINK, r"\1", html, flags=re.S)
    # 문서 표기 CTA '**[라벨 → /slug]** *(…CTA)*' → 실제 버튼
    html = re.sub(r'<p><strong>\[\s*([^\]<]+?)\s*→\s*/([a-z]+)\s*\]</strong>(?:\s*<em>\([^)]*\)</em>)?</p>',
                  r'<p class="cta-row"><a class="cta-btn" href="../\2/">\1</a></p>', html)
    # 머리글이 전부 빈 표의 thead 제거(빈 줄로 보임)
    html = re.sub(r"<thead>\s*<tr>\s*(?:<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>\s*", "", html)
    # TBD 값 → '준비 중' 정직 표기 (빈 대괄호 노출 금지 — 기술-사양 §4)
    html = re.sub(r"<code>@?\[\s*([^<]*?)(?:—|-)?\s*TBD\s*\]</code>",
                  r'<span class="tbd"></span>', html)
    html = re.sub(r"<code>@?\[\s*([^<]*?)\s*\]</code>", r'<span class="tbd">\1</span>', html)
    html = re.sub(r"@?\[(인스타 아이디|지원폼 링크|상세 위치|상세 주소|연락처|이메일 주소|운영 시간)\]",
                  r'<span class="tbd">\1</span>', html)
    # 본문에 남은 맨 'TBD' — 공개 화면엔 내부 약어 대신 우리말로
    html = re.sub(r"\s*\(TBD\)", "", html)
    html = html.replace("<strong>TBD</strong>", '<span class="tbd"></span>')
    html = re.sub(r"(?<![A-Za-z])TBD(?![A-Za-z])", "준비 중", html)
    # '예시' 배지 (디자인-가이드 §4 — 미확정 수치는 예시임이 보이게)
    html = html.replace("<code>예시</code>", '<span class="ex-badge">예시</span>')
    html = re.sub(r"\(예시\)", '<span class="ex-badge">예시</span>', html)
    html = re.sub("<li>(<p>)?[①-⑳] ?", lambda m: "<li>" + (m.group(1) or ""), html)  # 목록 점과 겹치는 원문자 번호
    for name, (slug, label) in DOC_LINK.items():
        html = html.replace(f"<code>{name}</code>", f'<a href="../{slug}/">{label}</a>')
    return html

# ──────────────────────────── 공통 레이아웃 ────────────────────────────
# 제목용 명조(홈 매거진형) — 본문은 Pretendard 유지
SERIF = "https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&display=swap"
FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"

# 전역 인터랙션: 헤더 그림자(스크롤) + 스크롤 리빌(reduced-motion 존중, JS 없으면 전체 표시)
GLOBAL_JS = """<script>
(function(){
  var top=document.querySelector('.top');
  var onScroll=function(){ if(top) top.classList.toggle('scrolled', window.scrollY>4); };
  window.addEventListener('scroll',onScroll,{passive:true}); onScroll();
  // 좌측 목차 스크롤 스파이 — 현재 보고 있는 섹션을 강조
  var toc=document.querySelector('.pagetoc');
  if(toc){
    var links=[].slice.call(toc.querySelectorAll('a'));
    var targets=links.map(function(a){return document.getElementById(a.getAttribute('href').slice(1));});
    var spy=function(){
      var idx=0;
      for(var k=0;k<targets.length;k++){
        if(targets[k]&&targets[k].getBoundingClientRect().top<=120)idx=k;else break;
      }
      links.forEach(function(a,k){a.classList.toggle('active',k===idx);});
    };
    window.addEventListener('scroll',spy,{passive:true});spy();
  }
  // 모바일 접이식 목차: 링크 누르면 접기
  var mtoc=document.querySelector('.pagetoc-m');
  if(mtoc){[].slice.call(mtoc.querySelectorAll('a')).forEach(function(a){
    a.addEventListener('click',function(){mtoc.open=false;});});}
  var els=[].slice.call(document.querySelectorAll('.reveal'));
  var rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(rm||!('IntersectionObserver' in window)){els.forEach(function(e){e.classList.add('in');});return;}
  var io=new IntersectionObserver(function(en){en.forEach(function(x){
    if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target);}});},{rootMargin:'0px 0px -8% 0px'});
  els.forEach(function(e){io.observe(e);});
})();
</script>"""

# 작가들 장르 필터 (JS 없이도 전체 표시 — 프로그레시브 인핸스먼트)
MAKERS_JS = """<script>
(function(){
  var chips=[].slice.call(document.querySelectorAll('.mk-filter .chip'));
  var cards=[].slice.call(document.querySelectorAll('.mk-card'));
  var empty=document.querySelector('.mk-empty');
  chips.forEach(function(c){c.addEventListener('click',function(){
    var cat=c.dataset.cat;
    chips.forEach(function(x){x.setAttribute('aria-pressed', x===c?'true':'false');});
    var shown=0;
    cards.forEach(function(card){
      var ok=(cat==='전체')||card.dataset.cat===cat;
      card.hidden=!ok; if(ok)shown++;
    });
    if(empty)empty.hidden=shown>0;
  });});
})();
</script>"""

# 내부 페이지 제목 위 작은 표지
KICKER = dict(NAV, policy="운영 규칙", apply="합류")

# 내부 페이지를 읽어 나가는 순서 — 글 끝의 '다음 읽을거리'에 쓴다.
READ_ORDER = ["about", "space", "policy", "guide", "academy", "magazine", "makers", "news", "contact"]

def page_next(slug, root):
    if slug not in READ_ORDER:
        return ""
    i = READ_ORDER.index(slug)
    nxt = READ_ORDER[i + 1] if i + 1 < len(READ_ORDER) else None
    a = (f'<a class="pn-item" href="{root}{nxt}/"><span class="pn-label">다음 읽을거리</span>'
         f'<strong>{KICKER[nxt]}</strong><span class="pn-arrow" aria-hidden="true">→</span></a>') if nxt else ""
    b = (f'<a class="pn-item pn-join" href="{root}apply/"><span class="pn-label">마음이 닿았다면</span>'
         f'<strong>합류 신청하기</strong><span class="pn-arrow" aria-hidden="true">→</span></a>')
    return f'<nav class="page-next" aria-label="다음으로">{a}{b}</nav>'

def layout(slug, title, desc, body, root):
    active = lambda s: ' class="on"' if s == slug else ""
    nav = "".join(f'<a href="{root}{s}/"{active(s)}>{label}</a>' for s, label in NAV)
    sticky = "" if slug == "apply" else f'<a class="sticky-cta" href="{root}apply/">합류하기 — 당신의 꿈은 무엇인가요?</a>'
    canonical = CFG["base_url"] + "/" + (slug + "/" if slug else "")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<script>document.documentElement.className+=' js';</script>
<title>{htmllib.escape(title)}</title>
<meta name="description" content="{htmllib.escape(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23161513'/%3E%3Ccircle cx='16' cy='16' r='6' fill='%23C2452D'/%3E%3C/svg%3E">
<meta property="og:type" content="website">
<meta property="og:title" content="{htmllib.escape(title)}">
<meta property="og:description" content="{htmllib.escape(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{CFG['base_url']}/assets/img/og.svg">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="{FONT}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{FONT}"></noscript>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{SERIF}">
<link rel="stylesheet" href="{root}assets/style.css">
</head>
<body class="p-{slug or 'home'}">
<header class="top">
  <a class="brand" href="{root}">헐버트<span>작가촌</span></a>
  <nav class="gnav">{nav}</nav>
  <a class="cta-btn small" href="{root}apply/">합류하기</a>
  <button class="menu-btn" aria-label="메뉴" onclick="document.body.classList.toggle('nav-open')">☰</button>
</header>
<div class="mnav"><nav>{nav}<a href="{root}apply/">합류하기</a></nav></div>
{body}
{GLOBAL_JS}
{MAKERS_JS if slug == 'makers' else ''}
<footer class="foot">
  <div class="foot-in">
    <div>
      <p class="f-brand">헐버트작가촌</p>
      <p class="f-line">경복궁 옆 서촌 한옥<br>잃을 걱정 없이, 하고 싶은 창작만 — 잘 팔리면 복지로 보답하고, 끝내 함께 주인이 된다.</p>
    </div>
    <nav class="foot-nav" aria-label="바닥 메뉴">{nav}<a href="{root}apply/">합류하기</a></nav>
    <div>
      <p class="f-note">이름 '헐버트'는 한글을 사랑하고 한국 독립을 도운 호머 헐버트 박사(1863~1949)를 기리는 뜻에서 따왔으며, 특정 단체와의 제휴를 뜻하지 않습니다.</p>
      <p class="f-legal">사업자 정보 · 개인정보처리방침 · 이용약관 — <span class="tbd">법률 검토 후 게시 예정</span></p>
    </div>
  </div>
  <div class="foot-base"><span>© 헐버트작가촌</span><a href="{root}apply/">합류 신청하기 →</a></div>
</footer>
{sticky}
</body>
</html>"""

# ──────────────────────────── 홈 (정본: docs/홈-랜딩-카피.md 11블록) ────────────────────────────
def home_body(root):
    faq = [
        ("또 입점비·자릿세 뜯기나요?", "입점비 0, 고정 월세 0. 판 만큼만 복지수수료."),
        ("가격을 후려치나요?", "100% 작가님이 정합니다."),
        ("어떤 작품이어야 하나요?", "한옥에 어울리면 장르 불문."),
        ("안 팔리면 어떻게 되나요?", "로테이션으로 자리가 돌고, 다듬어 재입점할 수 있습니다."),
        ("단계는 꼭 올라가야 하나요?", "아니요. 1단계 작가로 머물러도 좋습니다. 사다리는 선택이에요."),
        ("정산은 어떻게 받나요?", "판매분에서 수수료를 뺀 금액을 정기 정산합니다. 안 팔린 달엔 청구가 없습니다."),
    ]
    faq_html = "".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
    img = root + "assets/img/"
    return f"""
<main class="home">

<section class="mz-hero hx">
  <div class="hx-grid">
    <div class="hx-text">
      <p class="mz-kicker"><span class="dot-ac"></span>작가 모집 · 경복궁 옆 서촌 한옥</p>
      <h1>잃을 걱정 없이,<br>하고 싶은 창작만.</h1>
      <p class="lede">입점비도, 자릿세도 없습니다. 안 팔린 달엔 한 푼도 내지 않습니다. 그리고 끝내 — <strong>함께 회사의 주인이 됩니다.</strong></p>
      <p class="hero-cta"><a class="cta-btn big" href="{root}apply/">합류하기</a>
      <a class="mz-link" href="#why">3분 만에 이해하기 ↓</a></p>
    </div>
    <figure class="hx-photo">
      <img src="{img}courtyard.jpg" alt="소나무가 선 한옥 마당과 본채" width="900" height="502" fetchpriority="high">
      <figcaption>서촌 한옥 '함께봄'의 마당 — 실제 사진</figcaption>
    </figure>
  </div>
  <div class="mz-wrap">
    <dl class="mz-facts">
      <div><dt>입점비</dt><dd>0<span>원</span></dd></div>
      <div><dt>매달 자릿세</dt><dd>0<span>원</span></dd></div>
      <div><dt>안 팔린 달</dt><dd>0<span>원</span></dd></div>
      <div class="accent"><dt>끝내 함께 주인</dt><dd>3<span>단계</span></dd></div>
    </dl>
  </div>
</section>

<section class="mz-sec reveal">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>01</b>이야기의 시작</p>
    <div class="mz-body wide">
      <h2>위탁 매장에 한 번쯤 데여보셨죠?</h2>
      <div class="mz-duo">
      <ul class="mz-lines flip">
        <li><s>입점비 수십만 원</s><b>0원</b></li>
        <li><s>매달 빠져나가는 자릿세</s><b>0원</b></li>
        <li><s>안 팔리면 고스란히 내 손해</s><b>안 팔린 달 0원</b></li>
      </ul><div>
      <p>그러다 <em>정말 하고 싶은 작품</em> 대신 <em>당장 돈이 되는 흔한 물건</em>만 만들게 되는 그 마음 —</p>
      <p class="mz-pull">우리는 그 마음을 알기에,<br>규칙을 정반대로 짰습니다.</p></div></div>
    </div>
  </div>
</section>

<section class="mz-sec mz-tint reveal">
  <div class="mz-wrap mz-split">
    <figure class="mz-fig"><img src="{img}hall-table.jpg" alt="서까래가 보이는 한옥 대청과 긴 나무 테이블" width="900" height="675" loading="lazy"></figure>
    <div>
      <p class="mz-label inline"><b>02</b>이름에 담은 뜻</p>
      <h2>한글을 사랑한 '헐버트'처럼,<br>작가를 뒤에서 받칩니다</h2>
      <p>이름 <strong>헐버트</strong>는 한글을 사랑하고 한국을 도운 미국인 <strong>호머 헐버트 박사</strong>에서 왔습니다. 앞에 나서지 않고 뒤에서 받친 그 사람처럼 — 회사는 주인공이 아니라 <strong>작가를 받치는 조력자</strong>입니다.</p>
      <p class="mz-values"><span>함께</span><span>공평</span><span>투명</span></p>
      <p class="more"><a class="mz-link" href="{root}about/">우리 이야기 더 보기 →</a></p>
    </div>
  </div>
</section>

<section class="mz-sec reveal" id="why">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>03</b>합류하면 좋은 이유</p>
    <div class="mz-body wide">
      <h2>왜 합류하면 좋은가</h2>
      <div class="mz-three">
        <div><span class="mz-num">하나</span><h3>입점비 0원</h3><p>가격은 처음부터 끝까지 <em>작가님이</em> 책정합니다. 우리는 손대지 않습니다.</p></div>
        <div><span class="mz-num">둘</span><h3>경복궁 옆 서촌 한옥</h3><p>관광객이 흐르는 길목, 예술가의 동네. 작품이 '상품'이 아니라 '작품'이 됩니다.</p></div>
        <div><span class="mz-num">셋</span><h3>복지수수료</h3><p>안 팔리면 0원. 수수료마저 회사 몫이 아니라 한옥 운영비로 전액 쓰입니다.</p></div>
      </div>
    </div>
  </div>
</section>

<section class="mz-sec mz-ink reveal">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>04</b>돈 이야기</p>
    <div class="mz-body wide">
      <h2>돈 이야기, 가장 쉽게</h2>
      <p class="mz-sub">수수료가 '회사 주머니'로 가지 않습니다</p>
      <p class="mz-flow-cap">작가님이 판 금액</p>
      <div class="mz-figs">
        <div><b>30<i>%</i></b><span class="ex-badge">일반수수료</span><p>한옥 월세·관리비로 <strong>전액</strong> <span class="muted">(회사 마진 0)</span></p></div>
        <div class="keep"><b>나머지</b><p><strong>작가님 지갑으로</strong></p></div>
      </div>
      <ul class="mz-lines on-ink">
        <li><strong>안 팔린 달엔?</strong> 낼 돈이 없습니다.</li>
        <li><strong>잘 팔리기 시작하면?</strong> '증명'한 작가에게 30%보다 <strong>더 깎아주는 '복지수수료'</strong>가 열립니다.</li>
      </ul>
      <p class="mz-pull">떼이는 게 아니라,<br>한옥을 다 함께 공동구매하는 것.</p>
    </div>
  </div>
</section>

<section class="mz-sec reveal">
  <div class="mz-wrap mz-split rev">
    <div>
      <p class="mz-label inline"><b>05</b>합류 여정</p>
      <h2>끝내 '함께 주인'</h2>
      <p>작가로 시작해, 동료로 일하고, 공동 주인으로. <strong>오를지 말지는 선택입니다.</strong></p>
      <ol class="mz-steps">
        <li><b>위탁</b><p>복지수수료 관계. 가격 자율, 판 만큼만.</p></li>
        <li><b>너투사</b><p>'너(회사·동료)에게 투자하는 사람들'. 마케팅·매장일 등으로 월급처럼 버는 동료 파트너(3.3% 프리랜서).</p></li>
        <li><b>나투사</b><p>'나에게 투자하는 사람들'. 회사의 진짜 주주. 한옥 고정비를 법인이 함께 집니다.</p></li>
      </ol>
    </div>
    <figure class="mz-fig tall"><img src="{img}cafe-yard.jpg" alt="자갈 마당에 나무 의자가 놓인 한옥" width="1080" height="1350" loading="lazy"></figure>
  </div>
</section>

<section class="mz-sec mz-tint reveal">
  <div class="mz-wrap">
    <figure class="mz-fig banner"><img src="{img}yard-house.jpg" alt="마당에서 바라본 한옥 본채" width="900" height="502" loading="lazy"></figure>
    <div class="mz-cols">
      <p class="mz-label"><b>06</b>어떤 작품이든</p>
      <div class="mz-body wide">
        <h2>장르도, 소재도 묻지 않습니다 — 한옥에 어울리면 뭐든</h2>
        <ul class="mz-genres">
          <li>도자·유리·금속</li><li>가죽·직물·주얼리</li><li>캔들·디퓨저·리빙</li>
          <li>일러스트·지류·문구</li><li>음악·공연</li><li>그리고 무엇이든</li>
        </ul>
        <p class="mz-pull small">기준은 하나 — "한옥 마루 위에 자연스럽게 어울리는가."</p>
        <p class="mz-note"><strong>'소리'를 파는 예술가도 함께합니다</strong> — 음악가·싱어·연주자가 한옥에서 공연하고, 마음이 닿은 손님과 평생의 팬으로 이어집니다. <span class="muted">(한옥 무대 준비 중)</span></p>
      </div>
    </div>
  </div>
</section>

<section class="mz-sec reveal">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>07</b>동료 이야기 <span class="ex-badge">예시</span></p>
    <div class="mz-body wide">
      <p class="muted">아직 첫 동료를 기다리는 중입니다 — 아래는 톤을 보여드리는 예시이며, 실제 작가의 목소리로 바뀝니다.</p>
      <div class="mz-quotes">
        <blockquote><p>"입점비 걱정이 없으니, 팔릴 물건이 아니라 <em>만들고 싶은 걸</em> 만들게 됐어요."</p><cite>온새미로 · 도예 <span class="ex-badge">예시</span></cite></blockquote>
        <blockquote><p>"안 팔린 달엔 정말 0원이더라고요. 그제야 마음 놓고 실험했어요."</p><cite>봄해 · 가죽 <span class="ex-badge">예시</span></cite></blockquote>
      </div>
    </div>
  </div>
</section>

<section class="mz-sec mz-tint reveal">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>08</b>솔직하게</p>
    <div class="mz-body wide">
      <h2>이런 단점·각오가 있어요</h2>
      <p>달콤한 혜택만 말하지 않겠습니다. 정직하게, <strong>단점과 각오</strong>도 먼저 보여드립니다.</p>
      <div class="mz-three plain">
        <div><h3>처음엔 일반수수료 30%</h3><p>깎아주는 '복지수수료'는 일정 매출을 <em>증명</em>한 뒤에 열려요 — 시작부터 싼 게 아닙니다.</p></div>
        <div><h3>냉정한 서바이벌</h3><p>매대는 한정적이라, 손님의 선택을 오래 받지 못한 작품은 다음 작가를 위해 <strong>자리를 양보(퇴점)</strong>해야 합니다.</p></div>
        <div><h3>오르면 커지는 책임</h3><p>너투사는 낮엔 회사 일·밤엔 작품, 나투사(주주)는 <strong>동료들의 꿈까지 책임지는 '왕관의 무게'</strong>를 집니다.</p></div>
      </div>
      <p class="mz-pull small"><strong>이 각오를 기꺼이 질 분과 함께합니다.</strong> 단점까지 알고도 오신다면, 진짜 동료입니다.</p>
    </div>
  </div>
</section>

<section class="mz-sec reveal">
  <div class="mz-wrap mz-cols">
    <p class="mz-label"><b>09</b>자주 묻는 질문</p>
    <div class="mz-body wide mz-faq">
      {faq_html}
      <p class="more"><a class="mz-link" href="{root}contact/">더 많은 질문과 답 →</a></p>
    </div>
  </div>
</section>

<section class="mz-join reveal">
  <div class="mz-wrap">
    <img class="mz-jar" src="{img}room-window.jpg" alt="마당이 내다보이는 황토벽 방의 창" width="604" height="604" loading="lazy">
    <p class="mz-kicker center">거창한 서류는 없습니다. 세 가지만 보내주세요.</p>
    <ol class="mz-three-ask">
      <li>작품 사진 3~5장</li><li>"당신의 꿈" 한 문장</li><li>불리고 싶은 한글 이름</li>
    </ol>
    <h2 class="mz-ask">당신의 꿈은 무엇인가요?</h2>
    <p><a class="cta-btn big" href="{root}apply/">합류 신청하기</a></p>
  </div>
</section>

</main>"""

# ──────────────────────────── 작가들 (정본: docs/pages/작가들.md — 카드 4개는 가상 예시) ────────────────────────────
MAKERS = [
    ("도예", "도자·유리·금속", "온새미로", "가르지 않고, 있는 그대로 — 흙의 온기를 식탁마다 올려놓는 것.",
     "민무늬 백자 찻잔 — 손에 쥐면 따뜻한, 군더더기 없는 일상 그릇.",
     "입점비 걱정이 없으니, 팔릴 물건이 아니라 만들고 싶은 걸 만들게 됐어요."),
    ("가죽", "가죽·직물·주얼리", "봄해", "봄볕처럼 오래 곁에 머무는, 길들일수록 예뻐지는 물건을 만드는 것.",
     "한 장 가죽 카드지갑 — 바느질 한 땀까지 손으로, 쓸수록 윤이 나는.",
     "안 팔린 달엔 정말 0원이더라고요. 그제야 마음 놓고 실험했어요."),
    ("향·리빙", "캔들·디퓨저·리빙", "달보드레", "달처럼 은은한 향으로, 누군가의 저녁을 한 뼘 더 포근하게.",
     "서촌 골목 소이캔들 — 한옥 마당 냄새를 닮은, 과하지 않은 향.",
     "한옥에 어울리는 향이 뭘까 고민하다 보니, 제 작업이 더 단단해졌어요."),
    ("일러스트·지류", "일러스트·지류·문구", "그린나래", "그린 듯한 날개로 — 서촌의 풍경을 종이 위에 오래 남기는 것.",
     "인왕산 사계 엽서 세트 — 계절마다 다른 동네를 손으로 그린 네 장.",
     "가격을 제가 정한다는 게 처음엔 낯설었는데, 이제 제 작품값을 제가 책임져요."),
    ("음악·공연", "음악·공연", "소리별", "한옥 마루에 어쿠스틱 한 곡 — 지나던 발걸음이 멈추는 순간을 만드는 것.",
     "서촌 야상곡 — 해질녘 한옥에서 부르는 자작 어쿠스틱.",
     "공연은 무료지만, 그날 만난 분이 제 노래의 평생 팬이 되더라고요."),
]
# 필터 칩 (docs/pages/작가들.md §4 — '장르 불문'이 원칙, 가르기 아니라 찾기 편하라고)
# 예시 카드의 임시 사진(장르별) — 실제 작가가 입점하면 작품 사진으로 교체
MAKER_IMG = {"도예": "maker-pottery.jpg", "가죽": "maker-leather.jpg", "향·리빙": "maker-candle.jpg",
             "일러스트·지류": "maker-illust.jpg", "음악·공연": "maker-music.jpg"}
CHIPS = ["전체", "도자·유리·금속", "가죽·직물·주얼리", "캔들·디퓨저·리빙", "일러스트·지류·문구", "음악·공연", "기타"]

def makers_body(root):
    chips = "".join(
        f'<button class="chip" data-cat="{c}" aria-pressed="{"true" if c=="전체" else "false"}">{c}</button>'
        for c in CHIPS)
    cards = "".join(f"""
    <article class="mk-card" data-cat="{cat}">
      <figure class="mk-photo"><img src="{root}assets/img/{MAKER_IMG[g]}" alt="{g} 작업 참고 사진" width="800" height="800" loading="lazy"></figure>
      <p class="mk-genre">{g} <span class="ex-badge">예시</span></p>
      <h3>{name}</h3>
      <p class="mk-dream">"{dream}"</p>
      <p class="mk-work">대표작 · {work}</p>
      <p class="mk-quote">"{quote}"</p>
    </article>""" for g, cat, name, dream, work, quote in MAKERS)
    return f"""
<header class="page-band wide"><div class="page-band-in">
  <p class="mz-kicker"><span class="dot-ac"></span>함께하는 작가들</p>
  <h1>여기, 같은 꿈을 가진 동료들이 있습니다.</h1>
</div></header>
<main class="page">
<div class="prose">
  <p>헐버트작가촌은 나이도 학벌도 묻지 않습니다. 가장 먼저 묻는 건 하나예요 — <strong>"당신의 꿈은 무엇인가요?"</strong><br>
  그 꿈을 담은 한글 이름으로 서로를 부르고, 경복궁 옆 서촌 한옥 마루 위에 각자의 작품을 나란히 올립니다.</p>
  <div class="notice">지금 보이는 카드와 사진은 <strong>분위기를 보여주기 위한 가상 예시</strong>입니다(사진은 무료 사진과 AI 연출 이미지). 첫 작가들이 입점하면 진짜 얼굴로 바뀝니다. (장르 필터는 '가르기'가 아니라 <strong>찾기 편하라고</strong> 두는 장치예요 — 한옥에 어울리면 장르 불문입니다.)</div>
</div>
<div class="mk-filter" role="group" aria-label="장르 필터">{chips}</div>
<div class="mk-grid" id="mkGrid">{cards}
    <a class="mk-next" href="{root}apply/">
      <span class="mk-next-box"><span class="mk-plus" aria-hidden="true">+</span></span>
      <span class="mk-genre">다음 동료</span>
      <strong>여기는 당신의 자리</strong>
      <span class="mk-next-line">작품 사진 몇 장과 꿈 한 문장이면 됩니다. 합류 신청하기 →</span>
    </a>
  <p class="mk-empty" hidden>해당 장르의 동료는 아직 준비 중이에요. 다음 주인공이 당신일 수 있어요.</p>
</div>
<section class="join">
  <h2>다음 빈 카드의 주인공은, 당신입니다.</h2>
  <p>여기 있는 동료들도 처음엔 작품 사진 몇 장과 "꿈" 한 문장으로 시작했어요.<br>
  입점비도, 자릿세도 없습니다. 가격은 당신이 정하고, 안 팔린 달엔 한 푼도 내지 않습니다.</p>
  <p class="ask">당신의 꿈은 무엇인가요?</p>
  <p><a class="cta-btn big" href="{root}apply/">나도 합류하기</a> <a class="ghost-btn" href="{root}about/">헐버트작가촌 더 알아보기</a></p>
</section>
</main>"""

# ──────────────────────────── 빌드 ────────────────────────────
def build():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets", "img"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "assets", "style.css"), os.path.join(OUT, "assets", "style.css"))
    # 사진(임시 무료 사진 포함 — 출처는 site/assets/img/CREDITS.md)
    img_src = os.path.join(HERE, "assets", "img")
    if os.path.isdir(img_src):
        for f in os.listdir(img_src):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg")):
                shutil.copy(os.path.join(img_src, f), os.path.join(OUT, "assets", "img", f))
    # OG 대표 이미지: 기존 브랜드 일러스트 재사용
    og_src = os.path.join(ROOT, "viewer", "assets", "홈-랜딩-카피.svg")
    if os.path.exists(og_src): shutil.copy(og_src, os.path.join(OUT, "assets", "img", "og.svg"))

    urls = []
    for slug, title, desc, src in PAGES:
        root = "../" if slug else ""
        if slug == "":
            body = home_body(root)
        elif slug == "makers":
            body = makers_body(root)
        else:
            h1, inner, headings = render_md(src)
            banner = ""
            if slug == "apply":
                ig = cfg("instagram", default=None)
                form = cfg("apply_form_url", default=None)
                if not (ig or form):
                    banner = ('<div class="notice"><strong>지원 접수는 곧 열립니다.</strong> '
                              '아래는 신청 시 여쭤볼 내용의 미리보기예요 — 채널이 열리는 대로 이 자리에서 바로 신청하실 수 있습니다.</div>')
            mtoc = pagetoc_mobile(headings)
            band = (f'<header class="page-band{"" if pagetoc_aside(headings) else " solo"}"><div class="page-band-in">'
                    f'<p class="mz-kicker"><span class="dot-ac"></span>{KICKER.get(slug, "헐버트작가촌")}</p>'
                    f'<h1>{h1}</h1><p class="page-lead">{htmllib.escape(desc)}</p></div></header>')
            main_html = (f'<main class="page">{mtoc}<div class="prose">{banner}{inner}</div>{page_next(slug, root)}</main>')
            toc = pagetoc_aside(headings)
            body = band + (f'<div class="doc-layout">{toc}{main_html}</div>' if toc else main_html)
        page_dir = os.path.join(OUT, slug) if slug else OUT
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(layout(slug, title, desc, body, root))
        urls.append(CFG["base_url"] + "/" + (slug + "/" if slug else ""))

    # sitemap.xml · robots.txt (뷰어는 내부 도구 — 검색 제외, 기술-사양 §6)
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nDisallow: /Hulbert-General-Store/viewer/\nSitemap: {CFG['base_url']}/sitemap.xml\n")

    # 문서 뷰어 동봉 (내부 도구, /viewer/)
    vdst = os.path.join(OUT, "viewer")
    os.makedirs(os.path.join(vdst, "assets"), exist_ok=True)
    for name in ("index.html", "sources.json"):
        shutil.copy(os.path.join(ROOT, "viewer", name), os.path.join(vdst, name))
    for fn in os.listdir(os.path.join(ROOT, "viewer", "assets")):
        shutil.copy(os.path.join(ROOT, "viewer", "assets", fn), os.path.join(vdst, "assets", fn))

    total = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(OUT) for fn in fns)
    print("WROTE", OUT, "| pages:", len(PAGES), "| total:", round(total/1024), "KB (뷰어 포함)")

if __name__ == "__main__":
    build()
