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
        source_id: int
) -> None:
    sql = """
          INSERT OR IGNORE INTO feed_entries
    (title, link, published, summary, source_id)
    VALUES (?, ?, ?, ?, ?) \
          """

    data = [
        (
            e.title,
            e.link,
            e.published.isoformat() if e.published else datetime.now(timezone.utc).isoformat(),
            e.summary,
            source_id
        )
        for e in entry_list
    ]

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

# データベースのパス設定
DB_PATH = Path.home() / "rss_reader" / "data" / "feeds.db"

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

sources = get_feed_sources(conn)

logging.info("RSS fetch started.")

now = datetime.now(timezone.utc)

for source_id, url, interval_minutes, last_fetched_at in sources:
    try:
        # 経過時間チェック
        last_dt = datetime.fromisoformat(last_fetched_at).replace(tzinfo=timezone.utc)
        elapsed_minutes = (now - last_dt).total_seconds() / 60

        # -1 は誤差吸収用のバッファ
        if elapsed_minutes < (interval_minutes - 1):
            logging.info(f"Skipped {url} (interval not reached)")
            continue

        feed = feedparser.parse(url)

        if feed.get('bozo_exception'):
            logging.warning(f"Problem fetching {url}: {feed.bozo_exception}")

        entries = [convert_entry(e) for e in feed.entries]
        insert_feed_entries(conn, entries, source_id)

        update_last_fetched(conn, source_id)

        logging.info(f"Successfully fetched {len(entries)} entries from {url}")

    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")

logging.info("RSS fetch completed.")

conn.close()
