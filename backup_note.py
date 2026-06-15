"""
note.com → GitHub バックアップスクリプト
使い方: python backup_note.py <noteのユーザー名>
"""

import sys
import os
import json
import re
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests が必要です: pip install requests")
    sys.exit(1)


# ---- 設定 ----
OUTPUT_DIR = Path("articles")
SLEEP_SEC = 1.0  # APIへの負荷軽減


def fetch_article_list(username: str) -> list[dict]:
    """ユーザーの記事一覧を全ページ取得"""
    articles = []
    page = 1
    while True:
        url = f"https://note.com/api/v2/creators/{username}/contents"
        resp = requests.get(url, params={"kind": "note", "page": page}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        contents = data.get("data", {}).get("contents", [])
        if not contents:
            break

        articles.extend(contents)
        print(f"  ページ {page}: {len(contents)} 件取得")

        total_count = data.get("data", {}).get("totalCount", 0)
        if len(articles) >= total_count:
            break

        page += 1
        time.sleep(SLEEP_SEC)

    return articles


def fetch_article_detail(key: str) -> dict | None:
    """記事の詳細（本文含む）を取得。v3 → v1 の順で試みる"""
    for url in [
        f"https://note.com/api/v3/notes/{key}",
        f"https://note.com/api/v1/notes/{key}",
    ]:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("data", {})
        except Exception:
            pass
    return None


def _strip_backup_at(content: str) -> str:
    return re.sub(r'  <meta name="backup-at"[^\n]*\n', "", content)


def sanitize_filename(title: str) -> str:
    """ファイル名として使えない文字を除去"""
    s = re.sub(r'[\\/:*?"<>|]', '_', title)
    return s.strip()[:80]


def article_to_html(detail: dict) -> str:
    """記事データをHTMLファイルとして出力"""
    title = detail.get("name", "無題")
    key = detail.get("key", "")
    publish_at = detail.get("publishAt", "")
    body_html = detail.get("body", "")
    hashtags = [t.get("hashtag", {}).get("name", "") for t in detail.get("noteHashtags", [])]
    like_count = detail.get("likeCount", 0)
    note_url = f"https://note.com/notes/{key}"
    backup_at = datetime.now().isoformat()
    tags_str = ", ".join(hashtags)

    body_content = body_html if body_html else f'<p><em>本文を取得できませんでした。<a href="{note_url}">元記事</a>を参照してください。</em></p>'

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <!-- backup metadata -->
  <meta name="note-key"          content="{key}">
  <meta name="note-published-at" content="{publish_at}">
  <meta name="note-tags"         content="{tags_str}">
  <meta name="note-like-count"   content="{like_count}">
  <meta name="note-url"          content="{note_url}">
  <meta name="backup-at"         content="{backup_at}">
</head>
<body>
  <h1>{title}</h1>
  <p><a href="{note_url}" target="_blank">元記事を開く</a> ／ 公開日: {publish_at[:10]} ／ いいね: {like_count}</p>
  <hr>
  {body_content}
</body>
</html>"""


def backup(username: str):
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\n📥  {username} の記事を取得中...")
    articles = fetch_article_list(username)
    print(f"✅  合計 {len(articles)} 件の記事が見つかりました\n")

    new_count = 0
    update_count = 0

    for i, article in enumerate(articles, 1):
        key = article.get("key", "")
        title = article.get("name", "無題")
        print(f"[{i}/{len(articles)}] {title[:40]}")

        try:
            detail = fetch_article_detail(key)
            if detail is None:
                print(f"  ⚠️  詳細API失敗。一覧データで保存します（本文なし）")
                detail = article

            content = article_to_html(detail)
            filename = f"{sanitize_filename(title)}__{key}.html"
            filepath = OUTPUT_DIR / filename

            if filepath.exists():
                existing = filepath.read_text(encoding="utf-8")
                if _strip_backup_at(existing) == _strip_backup_at(content):
                    print(f"  → 変更なし、スキップ")
                    time.sleep(SLEEP_SEC)
                    continue
                filepath.write_text(content, encoding="utf-8")
                print(f"  → 更新: {filename}")
                update_count += 1
            else:
                filepath.write_text(content, encoding="utf-8")
                print(f"  → 新規保存: {filename}")
                new_count += 1

        except Exception as e:
            print(f"  ⚠️  取得失敗: {e}")

        time.sleep(SLEEP_SEC)

    write_index(articles)
    print(f"\n🎉  完了！  新規: {new_count} 件 / 更新: {update_count} 件")


def write_index(articles: list[dict]):
    """記事一覧のインデックスMarkdownを生成"""
    rows = [
        "# note バックアップ 記事一覧\n",
        f"総記事数: {len(articles)} 件\n\n",
        "| タイトル | 公開日 | いいね |\n",
        "|---------|--------|-------|\n",
    ]
    for a in articles:
        title = a.get("name", "無題")
        key = a.get("key", "")
        published = a.get("publishAt", "")[:10]
        likes = a.get("likeCount", 0)
        filename = f"{sanitize_filename(title)}__{key}.html"
        rows.append(f"| [{title}](articles/{filename}) | {published} | {likes} |\n")

    index_path = Path(".") / "INDEX.md"
    body = "".join(rows)

    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8")
        if existing == body:
            print("\n📋  INDEX.md 変更なし、スキップ")
            return

    index_path.write_text(body, encoding="utf-8")
    print("\n📋  INDEX.md を更新しました")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        username = os.environ.get("NOTE_USERNAME", "")
        if not username:
            print("使い方: python backup_note.py <noteのユーザー名>")
            print("または環境変数 NOTE_USERNAME を設定してください")
            sys.exit(1)
    else:
        username = sys.argv[1]

    backup(username)