#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""헐버트 프로젝트 문서 → HTML 뷰어+WYSIWYG 편집기 빌드.
읽기=외부 의존성 없음(미리 렌더된 HTML, index.html 단독으로 즉시 표시).
편집=원문(sources.json)과 marked(렌더)+turndown(역변환) CDN을 편집 시점에만 지연 로드.
로드 실패 시 소스 모드/안내 토스트로 폴백 — 읽기는 어떤 경우에도 막히지 않는다."""
import re, os, json, html as htmllib
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "viewer", "index.html")

DOCS = [
    ("docs/문서-지도.md",        "idx", "인덱스"),
    ("README.md",                "idx", "인덱스"),
    ("docs/작가-소개.md",        "A", "개념·브랜드"),
    ("docs/브랜드-정의서.md",     "A", "개념·브랜드"),
    ("docs/홈페이지-사이트맵.md", "B", "작가촌 사이트"),
    ("docs/홈-랜딩-카피.md",      "B", "작가촌 사이트"),
    ("docs/pages/소개.md",       "B", "작가촌 사이트"),
    ("docs/pages/공간소개.md",    "B", "작가촌 사이트"),
    ("docs/pages/운영정책.md",    "B", "작가촌 사이트"),
    ("docs/pages/작가들.md",      "B", "작가촌 사이트"),
    ("docs/pages/소식.md",       "B", "작가촌 사이트"),
    ("docs/pages/합류하기.md",    "B", "작가촌 사이트"),
    ("docs/pages/문의.md",       "B", "작가촌 사이트"),
    ("docs/기술-사양.md",         "B", "작가촌 사이트"),
    ("docs/디자인-가이드.md",      "B", "작가촌 사이트"),
    ("docs/작가-운영정책.md",     "C", "운영·계약"),
    ("docs/입점-동의서.md",       "C", "운영·계약"),
    ("docs/운영-매뉴얼.md",       "C", "운영·계약"),
    ("docs/작가-모집-키트.md",    "D", "모집"),
    ("docs/로드맵.md",           "E", "경영·관리"),
    ("docs/사업계획서.md",        "E", "경영·관리"),
    ("docs/시장-벤치마크-개관-전략.md", "E", "경영·관리"),
    ("docs/성과지표-KPI.md",      "E", "경영·관리"),
    ("docs/정관-거버넌스.md",     "E", "경영·관리"),
    ("docs/상표-IP-보호-메모.md", "E", "경영·관리"),
    ("docs/헐버트작가촌-기획.md", "F", "전략"),
    ("docs/손님-매장안내.md",     "G", "범위 밖"),
    ("docs/en/hulbert-en.md",    "G", "범위 밖"),
    ("docs/legal/개인정보처리방침.md", "H", "법적 고지"),
    ("docs/legal/이용약관.md",        "H", "법적 고지"),
    ("docs/legal/사업자정보.md",       "H", "법적 고지"),
]
GROUP_ORDER = [
    ("idx", "인덱스"), ("A", "개념·브랜드"), ("B", "작가촌 사이트"),
    ("C", "운영·계약"), ("D", "모집"), ("E", "경영·관리"), ("F", "전략"),
    ("G", "범위 밖"), ("H", "법적 고지"),
]
STATUS_ORDER = [
    ("all", "전체"), ("confirmed", "✅ 확정"), ("draft", "📝 초안"),
    ("review", "⚠️ 검토"), ("later", "🕒 다음"), ("out", "🗂 범위 밖"),
]

def gh_slug(text, sep="-"):
    s = htmllib.unescape(text).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s", sep, s.strip())
    return s

def status_key(label):
    if "✅" in label: return "confirmed"
    if "📝" in label: return "draft"
    if "⚠️" in label: return "review"
    if "🕒" in label: return "later"
    if "🗂" in label: return "out"
    return "info"

def parse_meta(md_text):
    title, badge, role = "(제목 없음)", "", ""
    for line in md_text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip(); break
    m = re.search(r"🏷️\s*\*\*(.+?)\*\*(.*)", md_text)
    if m:
        badge = m.group(1).strip()
        parts = [p.strip() for p in m.group(2).split("·") if p.strip()]
        role = parts[-1] if parts else ""
    title = re.sub(r"[*`]", "", title)
    role  = re.sub(r"[*`]", "", role)
    return title, badge, role

basemap = {}
for i, (rel, _g, _gl) in enumerate(DOCS):
    base = os.path.basename(rel)
    if base.endswith(".md"): base = base[:-3]
    basemap[base] = i

def rewrite_md_links(s):
    def repl(m):
        href = m.group(1)
        path = href.split("#", 1)[0]
        base = path.rsplit("/", 1)[-1]
        if base.endswith(".md"): base = base[:-3]
        if base in basemap:
            return f'href="#" data-goto="{basemap[base]}"'
        return m.group(0)
    return re.sub(r'href="([^"]+\.md(?:#[^"]*)?)"', repl, s)

def prefix_anchors(s, n):
    s = re.sub(r'id="([^"]+)"',     lambda m: f'id="d{n}-{m.group(1)}"', s)
    s = re.sub(r'href="#([^"]+)"',  lambda m: f'href="#d{n}-{m.group(1)}"', s)
    return s

articles, navmeta, raw_sources = [], [], []
for i, (rel, gkey, glabel) in enumerate(DOCS):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        md_text = f.read()
    raw_sources.append(md_text)
    title, badge, role = parse_meta(md_text)
    skey = status_key(badge) if badge else "info"
    md = markdown.Markdown(
        extensions=["extra", "toc", "sane_lists", "attr_list"],
        extension_configs={"toc": {"slugify": gh_slug, "separator": "-"}},
    )
    body = prefix_anchors(rewrite_md_links(md.convert(md_text)), i)
    # 생성된 이해용 일러스트가 있으면 문서 상단에 주입(원본 .md는 건드리지 않음)
    # PNG(AI 생성) 우선, 없으면 SVG(기본 일러스트)
    slug = os.path.basename(rel)[:-3] if rel.endswith(".md") else os.path.basename(rel)
    for ext in ("png", "svg"):
        if os.path.exists(os.path.join(ROOT, "viewer", "assets", slug + "." + ext)):
            # 첫 문서 히어로는 첫 화면(LCP)이므로 즉시·우선 로드, 나머지는 지연 로드
            img_attr = 'fetchpriority="high"' if i == 0 else 'loading="lazy"'
            body = f'<img class="doc-hero" src="assets/{slug}.{ext}" alt="" {img_attr}>\n' + body
            break
    # 첫 문서는 JS 실행 전에도 보이도록 hidden 없이 출력(빈 화면 방지)
    hidden_attr = "" if i == 0 else " hidden"
    articles.append(
        f'<article class="doc" id="doc-{i}" data-group="{gkey}" data-status="{skey}"{hidden_attr}>\n{body}\n</article>'
    )
    navmeta.append({"i": i, "title": title, "badge": badge or "—", "role": role,
                    "group": gkey, "glabel": glabel, "status": skey})

glabel_map = dict(GROUP_ORDER)
nav_html = []
for gkey, _ in GROUP_ORDER:
    members = [m for m in navmeta if m["group"] == gkey]
    if not members: continue
    nav_html.append(f'<div class="nav-group" data-group="{gkey}">')
    nav_html.append(f'<div class="nav-grouphead">{htmllib.escape(glabel_map[gkey])}</div>')
    for m in members:
        sub = m["role"] or (m["badge"] if m["badge"] != "—" else "")
        nav_html.append(
            f'<button class="navitem s-{m["status"]}" data-i="{m["i"]}" '
            f'data-group="{m["group"]}" data-status="{m["status"]}" '
            f'data-title="{htmllib.escape(m["title"], quote=True)}" '
            f'data-role="{htmllib.escape(m["role"], quote=True)}">'
            f'<span class="dot" title="{htmllib.escape(m["badge"])}"></span>'
            f'<span class="navitem-main">'
            f'<span class="navitem-title">{htmllib.escape(m["title"])}</span>'
            f'<span class="navitem-sub">{htmllib.escape(sub)}</span>'
            f'</span></button>'
        )
    nav_html.append("</div>")
nav = "".join(nav_html)

status_pills = "".join(
    f'<button class="pill st s-{k}{" active" if k=="all" else ""}" data-st="{k}">{lbl}</button>'
    for k, lbl in STATUS_ORDER
)

# 원문 마크다운은 index.html에 내장하지 않고 별도 파일(sources.json)로 분리 —
# 초기 전송량을 절반 수준으로 줄이고, 편집·복사·저장 시점에만 fetch 한다.
raw_json  = json.dumps({str(i): s for i, s in enumerate(raw_sources)}, ensure_ascii=False)
relp_json = json.dumps({str(i): rel for i, (rel, _g, _gl) in enumerate(DOCS)}, ensure_ascii=False)
base_json = json.dumps(basemap, ensure_ascii=False)

TOOLBAR = (
    '<button data-cmd="undo" title="실행취소">↶</button>'
    '<button data-cmd="redo" title="다시실행">↷</button>'
    '<span class="div"></span>'
    '<button data-cmd="bold" title="굵게"><b>B</b></button>'
    '<button data-cmd="italic" title="기울임"><i>I</i></button>'
    '<button data-cmd="strikeThrough" title="취소선"><s>S</s></button>'
    '<span class="div"></span>'
    '<button data-cmd="h2" title="제목">제목</button>'
    '<button data-cmd="h3" title="소제목">소제목</button>'
    '<button data-cmd="p" title="본문">본문</button>'
    '<span class="div"></span>'
    '<button data-cmd="ul" title="글머리 목록">• 목록</button>'
    '<button data-cmd="ol" title="번호 목록">1. 목록</button>'
    '<button data-cmd="quote" title="인용">❝ 인용</button>'
    '<button data-cmd="link" title="링크">🔗 링크</button>'
)

FONT_CSS = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"

CSS = """
:root{
  --paper:#ece4d5; --sidebar:#f6f1e7; --card:#fffdf9; --ink:#262220; --muted:#7c7264;
  --line:#e3dac9; --line-soft:#efe7d8; --accent:#9c5b34; --accent-soft:#f3e6dc; --accent2:#2f6b63;
  --sidebar-w:298px; --reader-w:744px; --toc-w:208px;
  --c-confirmed:#2f7d4f; --c-draft:#2f6db0; --c-review:#b5791f;
  --c-later:#6b4ea8; --c-out:#9a9082; --c-info:#9a9082;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"Pretendard Variable","Pretendard","Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.layout{display:flex;align-items:flex-start;min-height:100vh}

.sidebar{width:var(--sidebar-w);flex:0 0 var(--sidebar-w);background:var(--sidebar);
  border-right:1px solid var(--line);height:100vh;position:sticky;top:0;
  display:flex;flex-direction:column;z-index:40}
.side-head{padding:18px 18px 14px;border-bottom:1px solid var(--line)}
.brand{font-size:1.18rem;font-weight:800;margin:0;letter-spacing:-.02em}
.brand .sep{color:var(--accent)}
.subtitle{font-size:.71rem;color:var(--muted);margin:.45rem 0 0;line-height:1.55}
.subtitle b{color:var(--ink)}
.side-tools{padding:13px 16px 9px;border-bottom:1px solid var(--line)}
.searchbox{width:100%;border:1px solid var(--line);border-radius:9px;padding:8px 12px;
  font-size:.85rem;font-family:inherit;background:#fff;color:var(--ink)}
.searchbox:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.pillrow{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}
.pill{border:1px solid var(--line);background:#fff;color:var(--muted);border-radius:999px;
  padding:3px 9px;font-size:.73rem;cursor:pointer;transition:.12s;font-family:inherit}
.pill:hover{border-color:var(--accent);color:var(--accent)}
.pill.st.active{background:var(--ink);color:#fff;border-color:var(--ink)}
.pill.st.s-confirmed.active{background:var(--c-confirmed);border-color:var(--c-confirmed);color:#fff}
.pill.st.s-draft.active{background:var(--c-draft);border-color:var(--c-draft);color:#fff}
.pill.st.s-review.active{background:var(--c-review);border-color:var(--c-review);color:#fff}
.pill.st.s-later.active{background:var(--c-later);border-color:var(--c-later);color:#fff}
.pill.st.s-out.active{background:var(--c-out);border-color:var(--c-out);color:#fff}
.count{font-size:.7rem;color:var(--muted);margin:9px 2px 2px}
.side-nav{flex:1;overflow-y:auto;padding:10px 10px 40px}
.nav-group{margin:2px 0 10px}
.nav-grouphead{font-size:.66rem;font-weight:800;letter-spacing:.09em;color:var(--muted);
  padding:8px 10px 4px;text-transform:uppercase}
.navitem{display:flex;align-items:center;gap:9px;width:100%;text-align:left;cursor:pointer;
  border:none;background:none;border-radius:9px;padding:7px 10px;font-family:inherit;color:var(--ink);
  transition:background .1s,color .1s}
.navitem:hover{background:rgba(156,91,52,.09)}
.navitem.active{background:var(--accent);color:#fff}
.navitem.active .navitem-sub{color:rgba(255,255,255,.82)}
.navitem.active .dot{box-shadow:0 0 0 2px rgba(255,255,255,.85)}
.navitem.edited .navitem-title::after{content:" ✏️";font-size:.82em}
.dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto}
.s-confirmed .dot{background:var(--c-confirmed)} .s-draft .dot{background:var(--c-draft)}
.s-review .dot{background:var(--c-review)} .s-later .dot{background:var(--c-later)}
.s-out .dot{background:var(--c-out)} .s-info .dot{background:var(--c-info)}
.navitem-main{display:flex;flex-direction:column;min-width:0;line-height:1.3}
.navitem-title{font-weight:600;font-size:.855rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.navitem-sub{font-size:.67rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.empty{color:var(--muted);font-size:.8rem;padding:20px 12px;text-align:center}

.content{flex:1;min-width:0;display:flex;justify-content:center;gap:46px;padding:0 36px}
.reader{flex:1 1 var(--reader-w);max-width:var(--reader-w);padding:22px 0 140px;font-size:17px;line-height:1.78}
.reader-bar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;position:sticky;top:0;z-index:8;
  background:linear-gradient(var(--paper) 78%,transparent);margin:0 0 16px;padding:12px 0 12px;
  border-bottom:1px solid var(--line-soft)}
.bar-path{font-size:.72rem;color:var(--muted);font-family:"SFMono-Regular",Consolas,monospace}
.tag-edited{font-size:.7rem;color:var(--c-review);font-weight:700}
.reader-bar .sp{flex:1}
.tbtn{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:8px;
  padding:6px 12px;font-size:.8rem;cursor:pointer;font-family:inherit;transition:.12s;white-space:nowrap}
.tbtn:hover{border-color:var(--accent);color:var(--accent)}
.tbtn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.tbtn.primary:hover{color:#fff;filter:brightness(1.06)}
.tbtn.hot{color:var(--c-review);border-color:#e6cfa3}
.doc{animation:fade .22s ease}
@keyframes fade{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.doc :where(h1,h2,h3,h4){scroll-margin-top:64px}
.doc h1{font-size:1.92rem;line-height:1.25;margin:.1em 0 .55em;letter-spacing:-.022em;font-weight:800}
.doc h2{font-size:1.36rem;margin:2.05em 0 .65em;padding-bottom:.32em;
  border-bottom:1.5px solid var(--line);font-weight:700;letter-spacing:-.01em}
.doc h3{font-size:1.13rem;margin:1.7em 0 .5em;font-weight:700;color:#39332b}
.doc h4{font-size:1.0rem;margin:1.35em 0 .35em;color:var(--accent);font-weight:700}
.doc p{margin:.9em 0}
.doc a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(156,91,52,.32)}
.doc a:hover{border-bottom-color:var(--accent)}
.doc a[data-goto]{color:var(--accent2);border-bottom-color:rgba(47,107,99,.4);font-weight:600}
.doc strong{font-weight:700}
.doc blockquote{margin:1.05em 0;padding:.8em 1.15em;background:#faf5ec;
  border-left:4px solid var(--accent);border-radius:0 9px 9px 0;color:#4a4239}
.doc blockquote p{margin:.3em 0}
.doc ul,.doc ol{padding-left:1.45em;margin:.7em 0}
.doc li{margin:.34em 0}
.doc li::marker{color:var(--accent)}
.doc code{background:#f0e8d8;padding:.12em .42em;border-radius:5px;font-size:.86em;
  font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace}
.doc pre{background:#272220;color:#f3ede1;padding:16px 18px;border-radius:11px;overflow:auto;font-size:.85rem;line-height:1.6}
.doc pre code{background:none;padding:0;color:inherit}
.doc table{border-collapse:collapse;width:100%;margin:1.2em 0;font-size:.92rem;display:block;overflow-x:auto}
.doc th,.doc td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top}
.doc th{background:#f1e9da;font-weight:700;white-space:nowrap}
.doc tr:nth-child(even) td{background:#fbf7ef}
.doc hr{border:none;border-top:1px solid var(--line-soft);margin:2em 0}
.doc img{max-width:100%}
.doc-hero{width:100%;aspect-ratio:16/7;object-fit:cover;border-radius:14px;display:block;
  margin:0 0 26px;box-shadow:0 6px 22px rgba(60,40,20,.10);background:var(--line-soft)}
.toc{flex:0 0 var(--toc-w);width:var(--toc-w);position:sticky;top:0;align-self:flex-start;
  max-height:100vh;overflow-y:auto;padding:28px 0 60px;font-size:.78rem}
.toc-head{font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.09em;
  font-size:.64rem;margin:0 0 9px 12px}
.toc a{display:block;color:var(--muted);text-decoration:none;padding:4px 12px;
  border-left:2px solid var(--line);line-height:1.4;transition:.1s}
.toc a:hover{color:var(--accent)}
.toc a.lvl3{padding-left:24px;font-size:.74rem}
.toc a.active{color:var(--accent);border-left-color:var(--accent);font-weight:700}

/* 편집 모드 (WYSIWYG + 소스 토글) */
.editor{display:none;flex-direction:column;gap:12px}
body.editing .editor{display:flex}
body.editing article.doc{display:none}
body.editing .reader{max-width:920px}
body.editing .toc{display:none}
.edtoolbar{position:sticky;top:54px;z-index:6;display:none;flex-wrap:wrap;gap:3px;align-items:center;
  background:var(--card);border:1px solid var(--line);border-radius:11px;padding:7px 9px;
  box-shadow:0 3px 12px rgba(60,40,20,.06)}
body.editing.wys .edtoolbar{display:flex}
.edtoolbar button{border:1px solid transparent;background:none;border-radius:7px;padding:5px 10px;
  font-size:.85rem;cursor:pointer;color:var(--ink);font-family:inherit;min-width:32px;line-height:1.1}
.edtoolbar button:hover{background:var(--accent-soft);color:var(--accent)}
.edtoolbar .div{width:1px;height:18px;background:var(--line);margin:0 4px}
.ed-wys{display:none;min-height:72vh;border:1px solid var(--line);border-radius:12px;
  padding:30px 36px;background:var(--card);outline:none;font-size:17px;line-height:1.78}
body.editing.wys .ed-wys{display:block}
.ed-wys:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.ed-src{display:none;width:100%;min-height:74vh;border:1px solid var(--line);border-radius:12px;
  padding:18px;font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace;
  font-size:13.5px;line-height:1.65;background:#fffdf9;color:var(--ink);resize:vertical;tab-size:2}
body.editing.src .ed-src{display:block}
.ed-src:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.edhint{font-size:.69rem;color:var(--muted);margin:0 2px}

.menu-toggle{display:none;position:fixed;top:12px;left:12px;z-index:60;
  background:var(--ink);color:#fff;border:none;border-radius:9px;padding:9px 13px;
  font-size:.85rem;font-family:inherit;cursor:pointer;box-shadow:0 3px 12px rgba(0,0,0,.22)}
.scrim{display:none;position:fixed;inset:0;background:rgba(30,24,18,.42);z-index:35}
.scrim.show{display:block}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(10px);
  background:var(--ink);color:#fff;padding:9px 16px;border-radius:9px;font-size:.82rem;
  opacity:0;pointer-events:none;transition:.2s;z-index:80}
.toast.show{opacity:.96;transform:translateX(-50%)}
@media(max-width:1140px){ .toc{display:none} }
@media(max-width:860px){
  .menu-toggle{display:block}
  .sidebar{position:fixed;left:0;top:0;transform:translateX(-100%);
    transition:transform .25s ease;box-shadow:6px 0 24px rgba(40,28,18,.18)}
  .sidebar.open{transform:none}
  .content{padding:0 18px}
  .reader{padding:56px 0 90px;font-size:16.5px}
  .doc h1{font-size:1.62rem}.doc h2{font-size:1.24rem}
  .edtoolbar{top:50px}
  .ed-wys{padding:22px 18px}
}
"""

JS = """
const RELP=JSON.parse(document.getElementById('relpaths').textContent);
const BASE=JSON.parse(document.getElementById('basemap').textContent);
const articles=Array.from(document.querySelectorAll('article.doc'));
const ORIG=articles.map(a=>a.innerHTML);
const items=Array.from(document.querySelectorAll('.navitem'));
const groups=Array.from(document.querySelectorAll('.nav-group'));
const stPills=Array.from(document.querySelectorAll('.pill.st'));
const search=document.getElementById('search');
const countEl=document.getElementById('count');
const emptyEl=document.getElementById('empty');
const tocEl=document.getElementById('toc');
const sidebar=document.getElementById('sidebar');
const scrim=document.getElementById('scrim');
const bar=document.getElementById('readerbar');
const edwys=document.getElementById('edwys');
const edsrc=document.getElementById('edsrc');
const edtoolbar=document.getElementById('edtoolbar');
const total=items.length;
let curStatus='all',curQuery='',curHeads=[],tocLinks=[],curDoc=0,editing=false,mode='wysiwyg',dt;
const touched=new Set();

/* 지연 로딩 — 원문(sources.json)·편집 모듈(CDN)은 편집/복사/저장 시점에만 가져온다.
   초기 화면은 미리 렌더된 HTML만으로 그려져 네트워크 상태와 무관하게 즉시 뜬다. */
let RAW=null,rawP=null;
function ensureRAW(){
  if(RAW)return Promise.resolve(RAW);
  if(!rawP)rawP=fetch('sources.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();})
    .then(j=>(RAW=j)).catch(err=>{rawP=null;throw err;});
  return rawP;
}
let TD=null,libsP=null;
function loadScript(src){return new Promise((res,rej)=>{const s=document.createElement('script');
  s.src=src;s.onload=res;s.onerror=()=>rej(new Error(src));document.head.appendChild(s);});}
function ensureLibs(){
  if(!libsP)libsP=Promise.all([
    loadScript('https://cdn.jsdelivr.net/npm/marked@12/marked.min.js').catch(()=>{}),
    loadScript('https://cdn.jsdelivr.net/npm/turndown@7/dist/turndown.js')
      .then(()=>loadScript('https://cdn.jsdelivr.net/npm/turndown-plugin-gfm@1/dist/turndown-plugin-gfm.js'))
      .catch(()=>{})
  ]).then(()=>{try{ if(window.TurndownService){
    TD=new window.TurndownService({headingStyle:'atx',hr:'---',bulletListMarker:'-',
      codeBlockStyle:'fenced',emDelimiter:'*',strongDelimiter:'**',linkStyle:'inlined'});
    if(window.turndownPluginGfm) TD.use(window.turndownPluginGfm.gfm);
  }}catch(e){}});
  return libsP;
}
const canWys=()=>!!(TD&&window.marked);

const EKEY=i=>'hbedit:'+RELP[i];
const getSrc=i=>{const v=localStorage.getItem(EKEY(i));return v!==null?v:(RAW?RAW[i]:'');};
const isEdited=i=>localStorage.getItem(EKEY(i))!==null;
function editedList(){const r=[];for(let k=0;k<total;k++)if(isEdited(k))r.push(k);return r;}
function slug(t){return t.trim().toLowerCase().replace(/[^\\w\\s-]/g,'').replace(/\\s+/g,'-');}
function norm(s){return s.replace(/\\r\\n?/g,'\\n').replace(/[ \\t]+$/gm,'').replace(/\\n{3,}/g,'\\n\\n').trim()+'\\n';}

function renderMD(src,i){
  if(!window.marked) return '<div class="edhint" style="padding:30px;text-align:center">미리보기 모듈을 불러오지 못했습니다.</div>';
  const div=document.createElement('div');
  div.innerHTML=window.marked.parse(src);
  div.querySelectorAll('h1,h2,h3,h4').forEach(h=>{if(!h.id)h.id='d'+i+'-'+slug(h.textContent);});
  div.querySelectorAll('a[href]').forEach(a=>{
    const base=(a.getAttribute('href')||'').split('#')[0].split('/').pop().replace(/\\.md$/,'');
    if(Object.prototype.hasOwnProperty.call(BASE,base)){a.setAttribute('href','#');a.setAttribute('data-goto',BASE[base]);}
  });
  return div.innerHTML;
}
function renderReadDoc(i){
  const art=document.getElementById('doc-'+i);
  if(isEdited(i)){
    if(window.marked){art.innerHTML=renderMD(getSrc(i),i);return;}
    ensureLibs().then(()=>{ if(window.marked&&isEdited(i)&&!editing){
      art.innerHTML=renderMD(getSrc(i),i);
      if(i===curDoc){buildTOC(art);spy();}
    }});
  }
  art.innerHTML=ORIG[i];
}

const _base={};
function baseMD(i){
  if(!RAW)return null;
  if(_base[i]===undefined) _base[i]= canWys()? norm(TD.turndown(window.marked.parse(RAW[i]))) : RAW[i];
  return _base[i];
}
function currentMarkdown(){
  if(editing&&mode==='wysiwyg'&&TD) return norm(TD.turndown(edwys.innerHTML));
  return edsrc.value;
}
function persist(){
  if(!touched.has(curDoc))return;
  const md=currentMarkdown();
  const baseline=(mode==='wysiwyg')?baseMD(curDoc):(RAW?RAW[curDoc]:null);
  if(baseline!==null&&md===baseline) localStorage.removeItem(EKEY(curDoc)); else localStorage.setItem(EKEY(curDoc),md);
  markSidebar();
}
function flush(){ clearTimeout(dt); persist(); }
function schedule(){ clearTimeout(dt); dt=setTimeout(()=>{persist();updateBar();},300); }
function loadIntoEditor(i){
  if(mode==='wysiwyg'&&canWys()) edwys.innerHTML=window.marked.parse(getSrc(i));
  else edsrc.value=getSrc(i);
}

function applyFilter(){
  let shown=0;
  groups.forEach(g=>{
    let gv=0;
    g.querySelectorAll('.navitem').forEach(c=>{
      const okS=curStatus==='all'||c.dataset.status===curStatus;
      const okQ=!curQuery||(c.dataset.title+' '+c.dataset.role).toLowerCase().includes(curQuery);
      const vis=okS&&okQ;c.style.display=vis?'':'none';if(vis){gv++;shown++;}
    });
    g.style.display=gv?'':'none';
  });
  countEl.textContent=shown+' / '+total+' 문서';
  emptyEl.style.display=shown?'none':'block';
}
function buildTOC(art){
  curHeads=Array.from(art.querySelectorAll('h2, h3'));
  if(curHeads.length<2){tocEl.innerHTML='';tocLinks=[];return;}
  let h='<div class="toc-head">목차</div>';
  curHeads.forEach(x=>{h+='<a class="'+(x.tagName==='H3'?'lvl3':'lvl2')+'" href="#'+x.id+'">'+x.textContent+'</a>';});
  tocEl.innerHTML=h;tocLinks=Array.from(tocEl.querySelectorAll('a'));
}
function spy(){
  if(!tocLinks.length)return;let idx=0;
  for(let k=0;k<curHeads.length;k++){if(curHeads[k].getBoundingClientRect().top<=150)idx=k;else break;}
  tocLinks.forEach((a,k)=>a.classList.toggle('active',k===idx));
}
function markSidebar(){items.forEach(c=>c.classList.toggle('edited',isEdited(+c.dataset.i)));}
function setModeClass(){document.body.classList.toggle('wys',mode==='wysiwyg');document.body.classList.toggle('src',mode==='source');}

function updateBar(){
  const i=curDoc,ed=isEdited(i),nE=editedList().length;
  let h='<span class="bar-path">'+RELP[i]+'</span>';
  if(ed)h+=' <span class="tag-edited">● 편집됨</span>';
  h+='<span class="sp"></span>';
  if(!editing){
    h+='<button class="tbtn primary" data-act="edit">✏️ 편집</button>';
  }else{
    h+='<button class="tbtn primary" data-act="read">✓ 완료</button>';
    if(canWys())h+='<button class="tbtn" data-act="mode">'+(mode==='wysiwyg'?'&lt;/&gt; 소스':'👁 비주얼')+'</button>';
    h+='<button class="tbtn" data-act="save">💾 저장</button>';
    h+='<button class="tbtn" data-act="copy">📋 복사</button>';
    if(ed)h+='<button class="tbtn hot" data-act="revert">↩︎ 원본</button>';
  }
  if(nE>0)h+='<button class="tbtn" data-act="saveall">📦 변경분 '+nE+'개</button>';
  bar.innerHTML=h;
}

let entering=false;
function enterEdit(){
  if(editing||entering)return;
  entering=true;
  Promise.allSettled([ensureLibs(),ensureRAW()]).then(rs=>{
    entering=false;
    if(rs[1].status==='rejected'&&!isEdited(curDoc)){
      toast('원본 문서를 불러오지 못했어요 — 네트워크 확인 후 다시 시도해 주세요');return;
    }
    editing=true; mode=canWys()?'wysiwyg':'source';
    document.body.classList.add('editing'); setModeClass();
    loadIntoEditor(curDoc); updateBar(); window.scrollTo({top:0});
    if(!canWys()) toast('편집 모듈을 불러오지 못했어요 — 소스 모드로 편집합니다');
    (mode==='wysiwyg'?edwys:edsrc).focus();
  });
}
function exitEdit(){
  flush(); editing=false;
  document.body.classList.remove('editing','wys','src');
  renderReadDoc(curDoc); markSidebar();
  buildTOC(document.getElementById('doc-'+curDoc)); updateBar();
  window.scrollTo({top:0}); requestAnimationFrame(spy);
}
function toggleMode(){
  if(mode==='wysiwyg'){ edsrc.value=currentMarkdown(); mode='source'; }
  else { if(!canWys()){toast('비주얼 편집은 인터넷 연결이 필요해요');return;} edwys.innerHTML=window.marked.parse(edsrc.value); mode='wysiwyg'; }
  setModeClass(); updateBar(); (mode==='wysiwyg'?edwys:edsrc).focus();
}

function withSrc(i,fn){
  if(RAW||isEdited(i)){fn();return;}
  ensureRAW().then(fn).catch(()=>toast('원본 문서를 불러오지 못했어요 — 네트워크를 확인해 주세요'));
}
function downloadDoc(i){
  withSrc(i,()=>{
    if(i===curDoc&&editing)flush();
    const blob=new Blob([getSrc(i)],{type:'text/markdown;charset=utf-8'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download=RELP[i].split('/').pop();document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href),1500);
  });
}
function copyDoc(i){
  withSrc(i,()=>{
    if(i===curDoc&&editing)flush();
    const t=getSrc(i);
    if(navigator.clipboard&&navigator.clipboard.writeText)
      navigator.clipboard.writeText(t).then(()=>toast('마크다운을 클립보드에 복사했어요')).catch(()=>toast('복사 실패 — 소스 모드에서 직접 선택해 주세요'));
    else toast('이 브라우저에선 자동 복사가 안 돼요 — 소스 모드에서 직접 선택');
  });
}
function revertDoc(i){
  if(!confirm('이 문서의 편집을 모두 버리고 원본으로 되돌릴까요?'))return;
  localStorage.removeItem(EKEY(i)); touched.delete(i);
  if(editing&&i===curDoc) loadIntoEditor(i);
  renderReadDoc(i); markSidebar(); updateBar(); toast('원본으로 되돌렸어요');
}

function selectDoc(i){
  i=+i;
  if(editing){
    flush(); curDoc=i;
    articles.forEach(d=>d.hidden=(d.id!=='doc-'+i));
    items.forEach(c=>c.classList.toggle('active',c.dataset.i===String(i)));
    loadIntoEditor(i); updateBar(); closeSidebar(); window.scrollTo({top:0});
    (mode==='wysiwyg'?edwys:edsrc).focus(); return;
  }
  curDoc=i;
  articles.forEach(d=>d.hidden=(d.id!=='doc-'+i));
  items.forEach(c=>c.classList.toggle('active',c.dataset.i===String(i)));
  closeSidebar(); renderReadDoc(i);
  buildTOC(document.getElementById('doc-'+i));
  updateBar(); window.scrollTo({top:0,behavior:'auto'}); requestAnimationFrame(spy);
}

function openSidebar(){sidebar.classList.add('open');scrim.classList.add('show');}
function closeSidebar(){sidebar.classList.remove('open');scrim.classList.remove('show');}
let tt;function toast(m){const el=document.getElementById('toast');el.textContent=m;el.classList.add('show');clearTimeout(tt);tt=setTimeout(()=>el.classList.remove('show'),1900);}

edwys.addEventListener('input',()=>{touched.add(curDoc);schedule();});
edsrc.addEventListener('input',()=>{touched.add(curDoc);schedule();});
edsrc.addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();
  const s=edsrc.selectionStart,en=edsrc.selectionEnd;edsrc.value=edsrc.value.slice(0,s)+'  '+edsrc.value.slice(en);
  edsrc.selectionStart=edsrc.selectionEnd=s+2;touched.add(curDoc);schedule();}});
edtoolbar.addEventListener('mousedown',e=>{
  const b=e.target.closest('button[data-cmd]');if(!b)return;e.preventDefault();
  edwys.focus();const c=b.dataset.cmd;
  try{
    if(c==='h2')document.execCommand('formatBlock',false,'H2');
    else if(c==='h3')document.execCommand('formatBlock',false,'H3');
    else if(c==='p')document.execCommand('formatBlock',false,'P');
    else if(c==='quote')document.execCommand('formatBlock',false,'BLOCKQUOTE');
    else if(c==='ul')document.execCommand('insertUnorderedList');
    else if(c==='ol')document.execCommand('insertOrderedList');
    else if(c==='link'){const u=prompt('링크 주소 (URL 또는 파일명.md):');if(u)document.execCommand('createLink',false,u);}
    else document.execCommand(c,false,null);
  }catch(_){}
  touched.add(curDoc);schedule();
});

items.forEach(c=>c.addEventListener('click',()=>selectDoc(c.dataset.i)));
stPills.forEach(p=>p.addEventListener('click',()=>{curStatus=p.dataset.st;stPills.forEach(x=>x.classList.toggle('active',x===p));applyFilter();}));
search.addEventListener('input',()=>{curQuery=search.value.trim().toLowerCase();applyFilter();});
bar.addEventListener('click',e=>{const b=e.target.closest('button[data-act]');if(!b)return;const a=b.dataset.act;
  if(a==='edit')enterEdit();else if(a==='read')exitEdit();else if(a==='mode')toggleMode();
  else if(a==='save')downloadDoc(curDoc);else if(a==='copy')copyDoc(curDoc);else if(a==='revert')revertDoc(curDoc);
  else if(a==='saveall'){const L=editedList();if(!L.length){toast('변경된 문서가 없어요');return;}L.forEach((x,k)=>setTimeout(()=>downloadDoc(x),k*250));toast(L.length+'개 문서를 내려받아요');}});
bar.addEventListener('pointerover',e=>{if(e.target.closest('button[data-act="edit"]')){ensureLibs();ensureRAW().catch(()=>{});}});
document.addEventListener('click',e=>{const a=e.target.closest('a[data-goto]');if(a&&!editing){e.preventDefault();selectDoc(a.dataset.goto);}});
document.getElementById('menu').addEventListener('click',openSidebar);
scrim.addEventListener('click',closeSidebar);
let spyQ=false;
window.addEventListener('scroll',()=>{if(spyQ)return;spyQ=true;requestAnimationFrame(()=>{spyQ=false;spy();});},{passive:true});
window.addEventListener('beforeunload',e=>{if(editing){flush();}});

markSidebar();applyFilter();selectDoc(0);
"""

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>헐버트 프로젝트 · 문서</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="{FONT_CSS}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{FONT_CSS}"></noscript>
<style>{CSS}</style>
</head>
<body>
<button class="menu-toggle" id="menu" aria-label="문서 목록 열기">☰ 문서</button>
<div class="scrim" id="scrim"></div>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="side-head">
      <h1 class="brand">헐버트 <span class="sep">·</span> 문서</h1>
      <p class="subtitle"><b>헐버트잡화점</b> = 손님용 매장 · <b>헐버트작가촌</b> = 작가용 사이트(모집 단계)</p>
    </div>
    <div class="side-tools">
      <input id="search" class="searchbox" type="search" placeholder="문서 이름·역할 검색…" autocomplete="off">
      <div class="pillrow">{status_pills}</div>
      <p class="count" id="count"></p>
    </div>
    <nav class="side-nav">
      {nav}
      <p class="empty" id="empty" style="display:none">조건에 맞는 문서가 없어요.</p>
    </nav>
  </aside>

  <div class="content">
    <main class="reader" id="reader">
      <div class="reader-bar" id="readerbar"></div>
      <div class="editor" id="editor">
        <div class="edtoolbar" id="edtoolbar">{TOOLBAR}</div>
        <div class="ed-wys doc" id="edwys" contenteditable="true" spellcheck="false"></div>
        <textarea class="ed-src" id="edsrc" spellcheck="false"></textarea>
        <p class="edhint">✏️ 본문을 클릭해 바로 고치세요. 자동 저장(브라우저)됩니다. <b>💾 저장</b>으로 .md를 받거나 <b>📋 복사</b>해서 채팅에 붙여주시면 제가 커밋합니다.</p>
      </div>
      {"".join(articles)}
    </main>
    <aside class="toc" id="toc"></aside>
  </div>
</div>
<div class="toast" id="toast"></div>

<script type="application/json" id="relpaths">{relp_json}</script>
<script type="application/json" id="basemap">{base_json}</script>
<script>{JS}</script>
</body>
</html>
"""

SRC_OUT = os.path.join(ROOT, "viewer", "sources.json")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
with open(SRC_OUT, "w", encoding="utf-8") as f:
    f.write(raw_json)

print("WROTE", OUT)
print("WROTE", SRC_OUT)
print("docs:", len(DOCS),
      "| index.html:", round(len(HTML)/1024, 1), "KB",
      "| sources.json:", round(len(raw_json)/1024, 1), "KB")
