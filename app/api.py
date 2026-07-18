# app.py
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi import Query
from fastapi import HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List


class FeedSourceCreate(BaseModel):
    name: str
    url: HttpUrl
    check_interval_minutes: int = 60


class NGWordCreate(BaseModel):
    word: str


class FeedReadUpdate(BaseModel):
    ids: List[int]


app = FastAPI()

DB_PATH = Path.home() / "rss_reader" / "data" / "feeds.db"

@app.get("/ping")
def ping():
    return {"status": "ok!"}

@app.get("/feeds")
def feeds(since: str = Query(...)):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        """
        SELECT id, title, summary, link, published, created_at, source_id, is_read, is_ng_word, ng_checked_version
        FROM feed_entries
        WHERE created_at >= ?
        ORDER BY created_at ASC
        """,
        (since,)
    ).fetchall()

    con.close()

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "summary": r["summary"],
            "link": r["link"],
            "published": r["published"],
            "created_at": r["created_at"],
            "source_id": r["source_id"],
            "is_read": r["is_read"],
            "is_ng_word": bool(r["is_ng_word"]),
            "ng_checked_version": r["ng_checked_version"],
        }
        for r in rows
    ]

@app.get("/sources")
def sources(since: str = Query(...)):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        """
        SELECT
            id,
            name,
            url,
            enabled,
            check_interval_minutes,
            updated_at,
            created_at
        FROM feed_sources
        WHERE updated_at >= ?
        ORDER BY updated_at ASC
        """,
        (since,)
    ).fetchall()

    con.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "url": r["url"],
            "enabled": bool(r["enabled"]),
            "check_interval_minutes": r["check_interval_minutes"],
            "updated_at": r["updated_at"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

@app.post("/sources")
def create_source(source: FeedSourceCreate):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    try:
        cur.execute(
            """
            INSERT INTO feed_sources (name, url, check_interval_minutes)
            VALUES (?, ?, ?)
            """,
            (source.name, str(source.url), source.check_interval_minutes)
        )
        con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Source with this URL already exists"
        )
    finally:
        con.close()

    return {"status": "ok"}


@app.get("/ng_words")
def get_ng_words():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        """
        SELECT id, word, created_at
        FROM ng_words
        ORDER BY created_at DESC
        """
    ).fetchall()

    con.close()

    return [
        {
            "id": r["id"],
            "word": r["word"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.post("/ng_words")
def create_ng_word(ng_word: NGWordCreate):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    try:
        cur.execute(
            """
            INSERT INTO ng_words (word)
            VALUES (?)
            """,
            (ng_word.word,)
        )
        con.commit()
    finally:
        con.close()

    return {"status": "ok"}


@app.post("/feeds/read")
def mark_feeds_as_read(update: FeedReadUpdate):
    if not update.ids:
        return {"status": "ok", "message": "No IDs provided"}

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    try:
        placeholders = ",".join("?" for _ in update.ids)
        cur.execute(
            f"UPDATE feed_entries SET is_read = 1 WHERE id IN ({placeholders})",
            update.ids
        )
        con.commit()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        con.close()

    return {"status": "ok"}
