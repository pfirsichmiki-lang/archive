# _tools — サイト生成の仕組み

このフォルダはサイトの表示には使われません（`_` で始まるフォルダは GitHub Pages が公開しない）。
資料を追加・修正するための作業ファイル一式です。

## ファイル

| ファイル | 役割 |
|---|---|
| `events.py` | **原本。** 収録項目の題名・説明文（和英）・日付・分類。ここを編集する |
| `rebuild.py` | `events.py` から `index.html` / `sitemap.xml` / `thumbs/` を作り直す |
| `build.py` | カードの書き出し・サムネイル生成などの部品。`rebuild.py` が読み込む |
| `_template.html` | ヘッダー・略歴・CSS・JavaScript の土台（カード部分が `__CARDS__`） |
| `meta.csv` / `en.json` | `rebuild.py` が書き出す控え。手で編集する必要はない |

## 追加のしかた

1. PDF・画像・動画を `files/<分類>/` に置く
2. `events.py` の `EVENTS`（PDF）/ `IMAGES`（画像）/ `VIDEOS`（動画）に項目を足す
3. `python3 _tools/rebuild.py`
4. `index.html` `sitemap.xml` `files/` `thumbs/` を GitHub にアップロード

必要なもの: Python 3、`pymupdf`、`pillow`、`ffmpeg`（動画を入れるときだけ）

## 運用ルール

- PDF は全ページ幅 595pt に統一。原本は圧縮しない
- フォルダ名に濁点つきの日本語を使わない（macOS の NFD 問題で URL が壊れる）
- GitHub のブラウザアップロードは 1 ファイル 25MB まで
- 写真に写る方々の実名は伏せる
- 確認はシークレットウインドウで（キャッシュ対策）
