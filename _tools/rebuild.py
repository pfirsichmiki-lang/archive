# -*- coding: utf-8 -*-
"""events.py を唯一の原本として index.html / sitemap.xml / meta.csv / en.json /
thumbs/ を作り直す。使い方：  python3 _tools/rebuild.py
"""
import csv, html, json, re, sys
from pathlib import Path
from urllib.parse import quote, unquote, urljoin
from datetime import datetime

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build as B
from events import EVENTS, IMAGES
try:
    from events import VIDEOS
except ImportError:
    VIDEOS = []

ALL = EVENTS + IMAGES + VIDEOS

# ---- meta.csv / en.json -------------------------------------------
with (TOOLS/'meta.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['filename','title','note','date','group']); w.writeheader()
    for e in ALL:
        w.writerow({'filename': e['path'], 'title': e['title'], 'note': e['note'],
                    'date': e['date'], 'group': e['group']})
print('meta.csv:', len(ALL), '件')

en = {e['path'].split('/')[-1]: e['en'] for e in ALL}
(TOOLS/'en.json').write_text(json.dumps(en, ensure_ascii=False, indent=1), encoding='utf-8')
B.EN = en
print('en.json:', len(en), '件')

# ---- サムネイル + カード -------------------------------------------
B.THUMB_DIR.mkdir(exist_ok=True)
items = []
for kind, group in (('pdf', EVENTS), ('image', IMAGES), ('video', VIDEOS)):
    for e in group:
        p = B.FILES_DIR / e['path']
        if not p.exists():
            sys.exit(f'ファイルがありません: {p}')
        slug = B.slugify(p); tp = B.THUMB_DIR / f'{slug}.jpg'
        pages, dur = 0, 0.0
        if kind == 'pdf':
            _, pages = B.make_pdf_thumb(p, tp)
        elif kind == 'image':
            B.make_image_thumb(p, tp)
        else:
            _, dur = B.make_video_thumb(p, tp, at=e.get('thumb_at', 0))
        items.append(dict(file=e['path'], src=e['path'], title=e['title'], note=e['note'],
                          date=e['date'], group=e['group'], kind=kind, pages=pages, dur=dur,
                          size=B.human_size(p.stat().st_size),
                          thumb=f'thumbs/{slug}.jpg' if tp.exists() else '', no='000'))
print('サムネイル:', len(items), '点')

# ---- 並べ替え（日付降順 → パス昇順）と通し番号 -----------------------
items.sort(key=lambda it: it['src'].lower())
items.sort(key=lambda it: it['date'], reverse=True)
for i, it in enumerate(items, 1):
    it['no'] = f'{i:03d}'
cards = '\n'.join(B.render_cards([it]) for it in items)

# ---- index.html ----------------------------------------------------
idx = (ROOT/'index.html').read_text(encoding='utf-8')
idx = re.sub(r'(<main class="sheet" id="sheet">\n).*?(\n<p class="empty")',
             lambda m: m.group(1) + cards + m.group(2), idx, flags=re.S)

today = datetime.now().strftime('%Y-%m-%d')
n = len(items)
n_img = sum(1 for it in items if it['kind'] == 'image')
n_vid = sum(1 for it in items if it['kind'] == 'video')
idx = re.sub(r'(収録 <b>)\d+(</b>)', rf'\g<1>{n}\g<2>', idx)
idx = re.sub(r'(画像 <b>)\d+(</b>)', rf'\g<1>{n_img}\g<2>', idx)
idx = re.sub(r'(PDF <b>)\d+(</b>)', rf'\g<1>{n - n_img - n_vid}\g<2>', idx)
if '動画 <b>' in idx:
    idx = re.sub(r'(動画 <b>)\d+(</b>)', rf'\g<1>{n_vid}\g<2>', idx)
else:
    idx = idx.replace('<span>更新 <b>', f'<span>動画 <b>{n_vid}</b></span>\n    <span>更新 <b>', 1)
if 'data-filter="video"' not in idx:
    idx = idx.replace('<button class="chip" data-filter="pdf" aria-pressed="false">PDF</button>',
                      '<button class="chip" data-filter="pdf" aria-pressed="false">PDF</button>\n'
                      '    <button class="chip" data-filter="video" aria-pressed="false">動画</button>', 1)
idx = re.sub(r'(更新 <b>)[\d-]+(</b>)', rf'\g<1>{today}\g<2>', idx)
idx = re.sub(r'(<footer>.*?&nbsp;·&nbsp; )[\d-]+(</footer>)', rf'\g<1>{today}\g<2>', idx)

# og:image はポートレートとバスケットボール写真の2枚に固定する
B0 = 'https://mikemiki.com/'
OG = ((B0+'img/mike-shinkichi-miki-basketball-tokio-marine-big-blue.jpg',
       '三木晋吉 Mike Shinkichi Miki — 東京海上ビッグブルー 背番号13'),
      (B0+'files/%E6%8E%B2%E8%BC%89%E8%A8%98%E4%BA%8B/mike-shinkichi-miki-a-day-bulletin-504-cover-2017.jpg',
       '三木晋吉 Mike Shinkichi Miki'))
og_html = '\n'.join(f'<meta property="og:image" content="{u}">\n'
                    f'<meta property="og:image:alt" content="{a}">' for u, a in OG)
idx = re.sub(r'(<meta property="og:image" content="[^"]*">\n<meta property="og:image:alt" content="[^"]*">\n?)+',
             og_html + '\n', idx, count=1)
(ROOT/'index.html').write_text(idx, encoding='utf-8')
print('index.html:', n, '点')

# ---- sitemap.xml ---------------------------------------------------
IMG_NS = 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
def _img(loc, title, cap):
    return (f'<image:image><image:loc>{html.escape(loc)}</image:loc>'
            f'<image:title>{html.escape(title)}</image:title>'
            f'<image:caption>{html.escape(cap)}</image:caption></image:image>')
IMG_BLOCK = _img(B0+'img/mike-shinkichi-miki-basketball-tokio-marine-big-blue.jpg',
                 '三木晋吉 Mike Shinkichi Miki',
                 '三木晋吉（Mike Shinkichi Miki）日本リーグ（現Bリーグ） 東京海上ビッグブルー 背番号13')
for _i in IMAGES:
    IMG_BLOCK += _img(B0+quote('files/'+_i['path'], safe='/'), _i['title'], _i['note'][:180])
base = B.SITE_URL
urls = [f'  <url><loc>{html.escape(base)}</loc><lastmod>{today}</lastmod>' + IMG_BLOCK + '</url>']
for it in items:
    loc = urljoin(base, quote('files/' + it['src'], safe='/'))
    urls.append('  <url><loc>' + html.escape(loc) + '</loc><lastmod>'
                + html.escape(it['date']) + '</lastmod></url>')
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" ' + IMG_NS + '>\n'
  + '\n'.join(urls) + '\n</urlset>\n', encoding='utf-8')
print('sitemap.xml:', len(urls), 'URL')
