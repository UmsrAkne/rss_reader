import feedparser
import sqlite3

from typing import Iterable
from app.models import FeedEntry, convert_entry

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
            e.published.isoformat() if e.published else None,
            e.summary,
            source_id
        )
        for e in entry_list
    ]

    con.executemany(sql, data)
    con.commit()

def get_feed_sources(con: sqlite3.Connection) -> list[tuple[int, str]]:
    cr = con.cursor()
    cr.execute("""
        SELECT id, url
        FROM feed_sources
        WHERE enabled = 1
    """)
    return cr.fetchall()

conn = sqlite3.connect("../data/feeds.db")
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
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
""")

cur.execute("""
INSERT OR IGNORE INTO feed_sources (name, url)
VALUES
    ('Yahoo Business', 'https://news.yahoo.co.jp/rss/categories/business.xml'),
    ('Yahoo World',    'https://news.yahoo.co.jp/rss/categories/world.xml');
""")

sources = get_feed_sources(conn)

for source_id, url in sources:
    feed = feedparser.parse(url)
    entries = [convert_entry(e) for e in feed.entries]
    insert_feed_entries(conn, entries, source_id)

conn.close()
