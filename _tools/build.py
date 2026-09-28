# -*- coding: utf-8 -*-
"""三木晋吉 資料アーカイブ — 生成の土台。

rebuild.py から部品として読み込まれる。単体で実行すると files/ を総なめして
index.html を一から作り直す（通常は rebuild.py を使う）。
"""
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin

ROOT = Path(__file__).resolve().parent.parent   # _tools/ の一つ上＝サイトのルート
FILES_DIR = ROOT / "files"
THUMB_DIR = ROOT / "thumbs"
OUT_HTML = ROOT / "index.html"
META_CSV = Path(__file__).resolve().parent / "meta.csv"
EN_JSON = Path(__file__).resolve().parent / "en.json"
TEMPLATE_HTML = Path(__file__).resolve().parent / "_template.html"

SITE_URL = "https://mikemiki.com/"
THUMB_WIDTH = 720

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXT = {".pdf"}
VIDEO_EXT = {".mp4", ".m4v", ".webm", ".mov"}

try:
    import pymupdf
except ImportError:
    pymupdf = None
try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None

EN = json.loads(EN_JSON.read_text(encoding="utf-8")) if EN_JSON.exists() else {}
TEMPLATE = TEMPLATE_HTML.read_text(encoding="utf-8") if TEMPLATE_HTML.exists() else ""


# ---- 小道具 --------------------------------------------------------
def slugify(path: Path) -> str:
    """サムネイル名。ファイル名を48文字までのローマ字にし、相対パスのMD5先頭8桁を足す。"""
    rel = path.relative_to(FILES_DIR).as_posix()
    base = re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")[:48]
    return f"{base}-{hashlib.md5(rel.encode('utf-8')).hexdigest()[:8]}"


def human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0


def fmt_duration(sec: float) -> str:
    sec = int(round(sec or 0))
    if sec <= 0:
        return ""
    m, s = divmod(sec, 60)
    return f"{m}分{s:02d}秒" if m else f"{s}秒"


# ---- サムネイル ----------------------------------------------------
def make_image_thumb(src: Path, dest: Path):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        img.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 3), Image.LANCZOS)
        img.save(dest, "JPEG", quality=82, optimize=True)
    return None, w, h


def make_pdf_thumb(src: Path, dest: Path):
    if pymupdf is None:
        return None, 0
    doc = pymupdf.open(src)
    pages = doc.page_count
    page = doc.load_page(0)
    scale = THUMB_WIDTH / page.rect.width if page.rect.width else 1
    page.get_pixmap(matrix=pymupdf.Matrix(scale, scale)).save(dest)
    doc.close()
    return None, pages


def video_info(src: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(src)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def make_video_thumb(src: Path, dest: Path, at: float = 0.0):
    dur = video_info(src)
    ss = at if at else min(2.0, max(0.0, dur / 4))
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-i", str(src), "-frames:v", "1",
             "-vf", f"scale={THUMB_WIDTH}:-2", "-q:v", "3", str(dest), "-y"],
            capture_output=True, timeout=120)
    except Exception:
        pass
    return None, dur


# ---- カード --------------------------------------------------------
def render_cards(items: list[dict]) -> str:
    """カードを HTML として直接書き出す。
    JavaScript 待ちにしないことで検索エンジンに本文が読まれる。"""
    out = []
    for it in items:
        e = lambda k: html.escape(str(it.get(k, "")))
        href = quote(f"files/{it['src']}", safe="/") if it["file"] == it["src"] else quote(it["file"], safe="/.")
        meta_bits = [it["date"]]
        if it["kind"] == "pdf" and it["pages"]:
            meta_bits.append(f"{it['pages']}ページ")
        if it["kind"] == "video" and it.get("dur"):
            meta_bits.append(fmt_duration(it["dur"]))
        meta_bits += [it["size"], it["group"]]
        meta = "".join(f"<span>{html.escape(str(m))}</span>" for m in meta_bits if m)

        shot = (
            f'<img src="{html.escape(it["thumb"])}" alt="{e("title")}" loading="lazy" decoding="async">'
            if it["thumb"] else '<span class="missing">NO PREVIEW</span>'
        )
        note = f'<p class="note">{e("note")}</p>' if it["note"] else ""
        en_txt, en_kw = (EN.get(it["src"].split("/")[-1]) or ["", ""])
        haystack = html.escape(" ".join([
            str(it.get(k, "")) for k in ("title", "note", "src", "group", "date")
        ] + [en_txt, en_kw]).lower())
        en_block = (
            f'\n    <p class="en-note" lang="en"><span class="tag">EN</span>{en_txt}</p>'
            if en_txt else ""
        )
        out.append(f"""<a class="frame" href="{html.escape(href)}" data-kind="{e('kind')}"
   data-no="{e('no')}" data-title="{e('title')}" data-search="{haystack}"
   target="_blank" rel="noopener">
  <div class="sprocket"><span class="no">{e('no')}</span><span class="kind">{ {'pdf':'PDF','video':'VIDEO'}.get(it['kind'],'IMG') }</span></div>
  <div class="shot">{shot}</div>
  <div class="caption">
    <h2>{e('title')}</h2>
    {note}{en_block}
    <p class="meta">{meta}</p>
  </div>
</a>""")
    return "\n".join(out)
