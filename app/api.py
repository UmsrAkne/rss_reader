# app.py
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi import Query
from fastapi import HTTPException
from pydantic import BaseModel, HttpUrl


class FeedSourceCreate(BaseModel):
    name: str
    url: HttpUrl
    check_interval_minutes: int = 60

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
        SELECT id, title, summary, link, published, created_at, source_id
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
