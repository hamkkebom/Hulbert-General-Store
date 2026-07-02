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
]
NAV = [("about", "소개"), ("space", "공간"), ("makers", "작가들"),
       ("news", "소식"), ("policy", "운영정책"), ("contact", "문의")]

# ──────────────────────────── md → HTML 변환 ────────────────────────────
def render_md(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        text = f.read()
    # 상단 메타(제목 배지·페이지 노트)는 내부용 — 첫 '---' 전까지 제거, 제목만 유지
    m = re.match(r"# (.+)\n", text)
    page_h1 = re.sub(r"\s*\(/[a-z]+\)\s*$", "", m.group(1)).strip() if m else ""
    first_hr = text.find("\n---\n")
    body = text[first_hr + 5:] if first_hr != -1 else text
    # 운영자용 섹션 제거(게시 전 제거 지시 준수)
    body = re.split(r"\n## 🛠 .*", body)[0]
    body = re.split(r"\n## ④ 운영 가이드.*", body)[0]
    md = markdown.Markdown(extensions=["extra", "sane_lists"])
    html = md.convert(body)
    html = transform(html)
    return page_h1, html

def transform(html):
    # 📷 사진 자리 블록 → 스타일된 플레이스홀더
    def photo(m):
        inner = re.sub(r"</?p>", " ", m.group(1))
        inner = re.sub(r"\[사진 자리\s*[—-]?\s*", "", inner).replace("📷", "").replace("]", "")
        inner = re.sub(r"\*", "", inner).strip()
        return f'<figure class="photo-slot"><span class="ps-icon">📷</span><figcaption>{inner}</figcaption></figure>'
    html = re.sub(r"<blockquote>\s*<p>📷(.*?)</p>\s*</blockquote>", photo, html, flags=re.S)
    # 문서 간 .md 링크 → 사이트 경로
    link_map = {"합류하기": "../apply/", "문의": "../contact/", "소개": "../about/",
                "공간소개": "../space/", "운영정책": "../policy/", "작가들": "../makers/",
                "소식": "../news/", "작가-운영정책": "../policy/"}
    def relink(m):
        base = m.group(1).split("/")[-1].replace(".md", "")
        return f'href="{link_map.get(base, "#")}"'
    html = re.sub(r'href="([^"]+\.md)(?:#[^"]*)?"', relink, html)
    # TBD 값 → '준비 중' 정직 표기 (빈 대괄호 노출 금지 — 기술-사양 §4)
    html = re.sub(r"<code>@?\[\s*([^<]*?)(?:—|-)?\s*TBD\s*\]</code>",
                  r'<span class="tbd">준비 중</span>', html)
    html = re.sub(r"<code>@?\[\s*([^<]*?)\s*\]</code>", r'<span class="tbd">\1</span>', html)
    html = re.sub(r"@?\[(인스타 아이디|지원폼 링크|상세 위치|상세 주소|연락처|이메일 주소|운영 시간)\]",
                  r'<span class="tbd">\1</span>', html)
    # '예시' 배지 (디자인-가이드 §4 — 미확정 수치는 예시임이 보이게)
    html = html.replace("<code>예시</code>", '<span class="ex-badge">예시</span>')
    html = re.sub(r"\(예시\)", '<span class="ex-badge">예시</span>', html)
    return html

# ──────────────────────────── 공통 레이아웃 ────────────────────────────
FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"

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
<title>{htmllib.escape(title)}</title>
<meta name="description" content="{htmllib.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{htmllib.escape(title)}">
<meta property="og:description" content="{htmllib.escape(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{CFG['base_url']}/assets/img/og.svg">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="{FONT}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{FONT}"></noscript>
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
{MAKERS_JS if slug == 'makers' else ''}
<footer class="foot">
  <p class="f-brand">헐버트작가촌 <span class="sep">·</span> 경복궁 옆 서촌 한옥</p>
  <p class="f-line">잃을 걱정 없이, 하고 싶은 창작만 — 잘 팔리면 복지로 보답하고, 끝내 함께 주인이 된다.</p>
  <p class="f-note">이름 '헐버트'는 한글을 사랑하고 한국 독립을 도운 호머 헐버트 박사(1863~1949)를 기리는 뜻에서 따왔으며, 특정 단체와의 제휴를 뜻하지 않습니다.</p>
  <p class="f-legal">사업자 정보 · 개인정보처리방침 · 이용약관 — <span class="tbd">법률 검토 후 게시 예정</span></p>
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
    return f"""
<main class="home">

<section class="hero">
  <p class="eyebrow">경복궁 옆 서촌 한옥 · 함께할 작가를 찾습니다</p>
  <h1>잃을 걱정 없이,<br>하고 싶은 창작만.</h1>
  <p class="lede">입점비도, 자릿세도 없습니다. 안 팔린 달엔 한 푼도 내지 않습니다.<br>
  그리고 끝내 — <strong>함께 회사의 주인이 됩니다.</strong></p>
  <p class="hero-cta"><a class="cta-btn" href="{root}apply/">합류하기</a>
  <a class="ghost-btn" href="#why">3분 만에 이해하기 ↓</a></p>
</section>

<section class="empathy">
  <h2>위탁 매장에 한 번쯤 데여보셨죠?</h2>
  <ul class="pain">
    <li>💸 입점비 수십만 원</li>
    <li>📆 매달 빠져나가는 자릿세</li>
    <li>📦 안 팔리면 고스란히 내 손해</li>
  </ul>
  <p>그러다 <em>정말 하고 싶은 작품</em> 대신 <em>당장 돈이 되는 흔한 물건</em>만 만들게 되는 그 마음 —<br>
  우리는 그 마음을 알기에, <strong>규칙을 정반대로 짰습니다.</strong></p>
</section>

<section class="who">
  <h2>한글을 사랑한 '헐버트'처럼, 작가를 뒤에서 받칩니다</h2>
  <p>이름 <strong>헐버트</strong>는 한글을 사랑하고 한국을 도운 미국인 <strong>호머 헐버트 박사</strong>에서 왔습니다.<br>
  앞에 나서지 않고 뒤에서 받친 그 사람처럼 — 회사는 주인공이 아니라 <strong>작가를 받치는 조력자</strong>입니다.</p>
  <p class="values"><span>함께</span><span>공평</span><span>투명</span></p>
  <p class="more"><a href="{root}about/">우리 이야기 더 보기 →</a></p>
</section>

<section class="benefits" id="why">
  <h2>왜 합류하면 좋은가</h2>
  <div class="cards3">
    <div class="card"><div class="ic">💸</div><h3>입점비 0원</h3><p>가격은 처음부터 끝까지 <em>작가님이</em> 책정합니다. 우리는 손대지 않습니다.</p></div>
    <div class="card"><div class="ic">🏠</div><h3>경복궁 옆 서촌 한옥</h3><p>관광객이 흐르는 길목, 예술가의 동네. 작품이 '상품'이 아니라 '작품'이 됩니다.</p></div>
    <div class="card"><div class="ic">🤝</div><h3>복지수수료</h3><p>안 팔리면 0원. 수수료마저 회사 몫이 아니라 한옥 운영비로 전액 쓰입니다.</p></div>
  </div>
</section>

<section class="money">
  <h2>돈 이야기, 가장 쉽게</h2>
  <p class="money-head">수수료가 '회사 주머니'로 가지 않습니다</p>
  <div class="flow">
    <div class="flow-src">작가님이 판 금액</div>
    <div class="flow-arms">
      <div class="arm"><b class="pct">30%<span class="ex-badge">일반수수료</span></b><p>한옥 월세·관리비로 <strong>전액</strong><br><span class="muted">(회사 마진 0)</span></p></div>
      <div class="arm keep"><b>나머지</b><p><strong>작가님 지갑으로</strong></p></div>
    </div>
  </div>
  <ul class="money-notes">
    <li><strong>안 팔린 달엔?</strong> 낼 돈이 없습니다.</li>
    <li><strong>잘 팔리기 시작하면?</strong> '증명'한 작가에게 30%보다 <strong>더 깎아주는 '복지수수료'</strong>가 열립니다.</li>
  </ul>
  <p class="oneline">한 줄 요약 — <strong>떼이는 게 아니라, 한옥을 다 함께 공동구매하는 것.</strong></p>
</section>

<section class="journey">
  <h2>합류 여정 — 끝내 '함께 주인'</h2>
  <p>작가로 시작해, 동료로 일하고, 공동 주인으로. <strong>오를지 말지는 선택입니다.</strong></p>
  <ol class="timeline">
    <li><b>1 · 위탁</b><p>복지수수료 관계. 가격 자율, 판 만큼만.</p></li>
    <li><b>2 · 너투사</b><p>'너(회사·동료)에게 투자하는 사람들'. 마케팅·매장일 등으로 월급처럼 버는 동료 파트너(3.3% 프리랜서).</p></li>
    <li><b>3 · 나투사</b><p>'나에게 투자하는 사람들'. 회사의 진짜 주주. 한옥 고정비를 법인이 함께 집니다.</p></li>
  </ol>
</section>

<section class="what">
  <h2>장르도, 소재도 묻지 않습니다 — 한옥에 어울리면 뭐든</h2>
  <p>도자·유리·금속, 가죽·직물·주얼리, 캔들·디퓨저, 일러스트·지류까지.<br>
  기준은 하나 — <strong>"한옥 마루 위에 자연스럽게 어울리는가."</strong></p>
</section>

<section class="voices">
  <h2>동료 이야기 <span class="ex-badge">예시</span></h2>
  <p class="muted">아직 첫 동료를 기다리는 중입니다 — 아래는 톤을 보여드리는 예시이며, 실제 작가의 목소리로 바뀝니다.</p>
  <div class="cards2">
    <blockquote class="voice"><p>"입점비 걱정이 없으니, 팔릴 물건이 아니라 <em>만들고 싶은 걸</em> 만들게 됐어요."</p><cite>온새미로 · 도예 <span class="ex-badge">예시</span></cite></blockquote>
    <blockquote class="voice"><p>"안 팔린 달엔 정말 0원이더라고요. 그제야 마음 놓고 실험했어요."</p><cite>봄해 · 가죽 <span class="ex-badge">예시</span></cite></blockquote>
  </div>
</section>

<section class="honest">
  <h2>솔직하게 — 이런 단점·각오가 있어요</h2>
  <p>달콤한 혜택만 말하지 않겠습니다. 정직하게, <strong>단점과 각오</strong>도 먼저 보여드립니다.</p>
  <div class="cards3 sober">
    <div class="card"><h3>처음엔 일반수수료 30%</h3><p>깎아주는 '복지수수료'는 일정 매출을 <em>증명</em>한 뒤에 열려요 — 시작부터 싼 게 아닙니다.</p></div>
    <div class="card"><h3>냉정한 서바이벌</h3><p>매대는 한정적이라, 손님의 선택을 오래 받지 못한 작품은 다음 작가를 위해 <strong>자리를 양보(퇴점)</strong>해야 합니다.</p></div>
    <div class="card"><h3>오르면 커지는 책임</h3><p>너투사는 낮엔 회사 일·밤엔 작품, 나투사(주주)는 <strong>동료들의 꿈까지 책임지는 '왕관의 무게'</strong>를 집니다.</p></div>
  </div>
  <p class="oneline"><strong>이 각오를 기꺼이 질 분과 함께합니다.</strong> 단점까지 알고도 오신다면, 진짜 동료입니다.</p>
</section>

<section class="faq">
  <h2>자주 묻는 질문</h2>
  {faq_html}
  <p class="more"><a href="{root}contact/">더 많은 질문과 답 →</a></p>
</section>

<section class="join">
  <h2>거창한 서류는 없습니다. 세 가지만 보내주세요.</h2>
  <ol class="three">
    <li>① 작품 사진 3~5장</li><li>② "당신의 꿈" 한 문장</li><li>③ 불리고 싶은 한글 이름</li>
  </ol>
  <p class="ask">당신의 꿈은 무엇인가요?</p>
  <p><a class="cta-btn big" href="{root}apply/">합류 신청하기</a></p>
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
]
# 필터 칩 (docs/pages/작가들.md §4 — '장르 불문'이 원칙, 가르기 아니라 찾기 편하라고)
CHIPS = ["전체", "도자·유리·금속", "가죽·직물·주얼리", "캔들·디퓨저·리빙", "일러스트·지류·문구", "기타"]

def makers_body(root):
    chips = "".join(
        f'<button class="chip" data-cat="{c}" aria-pressed="{"true" if c=="전체" else "false"}">{c}</button>'
        for c in CHIPS)
    cards = "".join(f"""
    <article class="mk-card" data-cat="{cat}">
      <div class="photo-slot sq"><span class="ps-icon">📷</span><figcaption>작품 사진 자리</figcaption></div>
      <p class="mk-genre">[{g}] <span class="ex-badge">예시</span></p>
      <h3>{name}</h3>
      <p class="mk-dream">✦ 꿈: "{dream}"</p>
      <p class="mk-work">대표작 · {work}</p>
      <p class="mk-quote">💬 "{quote}"</p>
    </article>""" for g, cat, name, dream, work, quote in MAKERS)
    return f"""
<main class="page">
<header class="page-head">
  <p class="eyebrow">함께하는 작가들</p>
  <h1>여기, 같은 꿈을 가진 동료들이 있습니다.</h1>
</header>
<div class="prose">
  <p>헐버트작가촌은 나이도 학벌도 묻지 않습니다. 가장 먼저 묻는 건 하나예요 — <strong>"당신의 꿈은 무엇인가요?"</strong><br>
  그 꿈을 담은 한글 이름으로 서로를 부르고, 경복궁 옆 서촌 한옥 마루 위에 각자의 작품을 나란히 올립니다.</p>
  <div class="notice">📌 지금 보이는 카드는 <strong>분위기를 보여주기 위한 가상 예시</strong>입니다. 첫 작가들이 입점하면 진짜 얼굴로 바뀝니다. (장르 필터는 '가르기'가 아니라 <strong>찾기 편하라고</strong> 두는 장치예요 — 한옥에 어울리면 장르 불문입니다.)</div>
</div>
<div class="mk-filter" role="group" aria-label="장르 필터">{chips}</div>
<div class="mk-grid" id="mkGrid">{cards}
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
            h1, inner = render_md(src)
            banner = ""
            if slug == "apply":
                ig = cfg("instagram", default=None)
                form = cfg("apply_form_url", default=None)
                if not (ig or form):
                    banner = ('<div class="notice">📮 <strong>지원 접수는 곧 열립니다.</strong> '
                              '아래는 신청 시 여쭤볼 내용의 미리보기예요 — 채널이 열리는 대로 이 자리에서 바로 신청하실 수 있습니다.</div>')
            body = (f'<main class="page"><header class="page-head"><h1>{h1}</h1></header>'
                    f'<div class="prose">{banner}{inner}</div></main>')
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
