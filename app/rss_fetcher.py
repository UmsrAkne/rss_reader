import feedparser
import sqlite3
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

from typing import Iterable
from app.models import FeedEntry, convert_entry

# ログの設定
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "rss_fetcher.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

def insert_feed_entries(
        con: sqlite3.Connection,
        entry_list: Iterable[FeedEntry],
        source_id: int,
        ng_words: list[str],
        ng_checked_version: int
) -> None:
    sql = """
          INSERT OR IGNORE INTO feed_entries
    (title, link, published, summary, source_id, is_ng_word, ng_checked_version)
    VALUES (?, ?, ?, ?, ?, ?, ?) \
          """

    data = []
    for e in entry_list:
        is_ng_word = 0
        # タイトルとサマリーに対してNGワードチェックを行う
        title = e.title if e.title else ""
        summary = e.summary if e.summary else ""
        for word in ng_words:
            if word in title or word in summary:
                is_ng_word = 1
                break

        data.append((
            e.title,
            e.link,
            e.published.isoformat() if e.published else datetime.now(timezone.utc).isoformat(),
            e.summary,
            source_id,
            is_ng_word,
            ng_checked_version
        ))

    con.executemany(sql, data)
    con.commit()

def get_feed_sources(con: sqlite3.Connection) -> list[tuple[int, str, int, str]]:
    cr = con.cursor()
    cr.execute("""
        SELECT id, url, check_interval_minutes, last_fetched_at
        FROM feed_sources
        WHERE enabled = 1
    """)
    return cr.fetchall()

def update_last_fetched(con: sqlite3.Connection, source_id: int) -> None:
    con.execute(
        "UPDATE feed_sources SET last_fetched_at = datetime('now') WHERE id = ?",
        (source_id,)
    )
    con.commit()

def get_latest_ng_words_and_version(con: sqlite3.Connection) -> tuple[list[str], int]:
    """
    NGワードのリストと、その中での最新の更新日時（バージョンとして使用）を返す。
    """
    cr = con.cursor()
    # ワード一覧を取得
    cr.execute("SELECT word FROM ng_words")
    words = [row[0] for row in cr.fetchall()]

    # 最新の created_at をバージョンとして取得
    cr.execute("SELECT MAX(created_at) FROM ng_words")
    row = cr.fetchone()
    version = row[0] if row and row[0] is not None else 0

    return words, version

# データベースのパス設定
# 環境変数 "DATABASE_URL" があればそれを使い、無ければ今までのローカルパスを使う
DB_PATH_STR = os.getenv("DATABASE_URL")

if DB_PATH_STR:
    DB_PATH = Path(DB_PATH_STR)
else:
    # 今までのローカルでのパスをフォールバックにしとく
    DB_PATH = Path.home() / "rss_reader" / "data" / "feeds.db"

# フォルダが存在しない場合に作る
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS feed_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    published TEXT,
    summary TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_ng_word INTEGER NOT NULL DEFAULT 0,
    ng_checked_version INTEGER,
    is_read INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_id, link),
    FOREIGN KEY(source_id) REFERENCES feed_sources(id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS feed_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    check_interval_minutes INTEGER NOT NULL DEFAULT 60,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS ng_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))) -- ('%s', 'now') でユニックスエポック秒になる。
""")

sources = get_feed_sources(conn)
ng_words, ng_version = get_latest_ng_words_and_version(conn)

logging.info("RSS fetch started.")

now = datetime.now(timezone.utc)

for source_id, url, interval_minutes, last_fetched_at in sources:
    try:
        # last_fetched_at が空であるケース（新しく追加したソースなど）に対応
        if last_fetched_at:
            # SQLiteの "YYYY-MM-DD HH:MM:SS" 形式を fromisoformat で読めるように T を入れる
            last_dt = datetime.fromisoformat(last_fetched_at.replace(" ", "T")).replace(tzinfo=timezone.utc)
        else:
            # 1970年とか、とりあえず「絶対に更新が必要なほど古い日時」にする
            last_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)

        # 経過時間チェック
        elapsed_minutes = (now - last_dt).total_seconds() / 60

        # -1 は誤差吸収用のバッファ
        if elapsed_minutes < (interval_minutes - 1):
            logging.info(f"Skipped {url} (interval not reached)")
            continue

        feed = feedparser.parse(url)

        if feed.get('bozo_exception'):
            logging.warning(f"Problem fetching {url}: {feed.bozo_exception}")

        entries = [convert_entry(e) for e in feed.entries]
        insert_feed_entries(conn, entries, source_id, ng_words, ng_version)

        update_last_fetched(conn, source_id)

        logging.info(f"Successfully fetched {len(entries)} entries from {url}")

    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")

logging.info("RSS fetch completed.")

conn.close()
