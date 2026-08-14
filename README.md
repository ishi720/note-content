# note-content

note.com の記事を HTML ファイルとして GitHub にバックアップするスクリプト

## バッチ

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/3f09e64626d34c57a9f64eccd9b6de05)](https://app.codacy.com/gh/ishi720/note-content/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

## 機能

- note.com の公開 API を使い、指定ユーザーの全記事を取得
- 記事をメタデータ付き HTML ファイルとして `articles/` に保存
- 既存ファイルと差分がない場合はスキップ（差分がある場合のみ上書き）
- 記事一覧を `INDEX.md` として自動生成

## 必要環境

- Python 3.10 以上
- `requests` ライブラリ

```bash
pip install requests
```

## 使い方

```bash
python backup_note.py <note_username>
```

環境変数で指定することも可能

```bash
NOTE_USERNAME=note_username python backup_note.py
```

## 出力ファイル

| ファイル | 説明 |
|---------|------|
| `articles/<タイトル>__<key>.html` | 記事本文（メタデータ付き HTML） |
| `INDEX.md` | 全記事の一覧表（タイトル・公開日・いいね数） |

## ディレクトリ構成

```
note-content/
├── backup_note.py   # バックアップスクリプト
├── INDEX.md         # 記事一覧（自動生成）
└── articles/        # バックアップ記事（自動生成）
```
