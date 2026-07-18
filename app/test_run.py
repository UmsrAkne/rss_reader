# test_run.py (使い捨ての動作確認用)
import sqlite3
import os
from pathlib import Path
# 既存のスクリプトから関数や変数をインポート（元のファイル名を rss_fetcher.py と仮定）
from rss_fetcher import insert_feed_entries, DB_PATH
from app.models import FeedEntry


def run_test():
    print(f"テスト用DBを作成します: {DB_PATH}")

    # 1. 完全にクリーンなテスト用DB、またはインメモリDBをセットアップ
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 元コードのテーブル定義をここにコピーして実行、または初期化SQLを流す
    # (省略: feed_entries, feed_sources, ng_words の CREATE TABLE)

    # 2. テスト用データの挿入
    cur.execute("INSERT INTO feed_sources (name, url, check_interval_minutes, last_fetched_at) VALUES (?, ?, ?, ?)",
                ("Test Source", "https://example.com/rss", 60, "1970-01-01 00:00:00"))
    cur.execute("INSERT INTO ng_words (word) VALUES (?)", ("NGワード",))
    conn.commit()

    # 3. 関数の単体テスト
    mock_entries = [
        FeedEntry(title="通常のタイトル", link="https://example.com/1", summary="これはテストです", published=None),
        FeedEntry(title="これはNGワードです", link="https://example.com/2", summary="テスト", published=None)
    ]

    print("insert_feed_entries をテスト中...")
    insert_feed_entries(conn, mock_entries, source_id=1, ng_words=["NGワード"], ng_checked_version=1)

    # 4. 結果の検証
    cur.execute("SELECT title, is_ng_word FROM feed_entries")
    rows = cur.fetchall()
    print("データベースの状態:")
    for row in rows:
        print(f"  タイトル: {row[0]}, NG判定: {row[1]}")

    conn.close()
    print("テスト完了！")


if __name__ == "__main__":
    # 本番DBを破壊しないよう、環境変数をテスト用に上書き
    os.environ["DATABASE_URL"] = "test_feeds.db"
    run_test()