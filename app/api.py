# app.py
import sqlite3
from fastapi import FastAPI
from fastapi import Query


app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "ok!"}

@app.get("/feeds")
def feeds(since: str = Query(...)):
    con = sqlite3.connect("../data/feeds.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    rows = cur.execute(
        """
        SELECT title, link, published, created_at, source_id
        FROM feed_entries
        WHERE created_at >= ?
        ORDER BY created_at ASC
        """,
        (since,)
    ).fetchall()

    con.close()

    return [
        {
            "title": r["title"],
            "link": r["link"],
            "published": r["published"],
            "created_at": r["created_at"],
            "source_id": r["source_id"],
        }
        for r in rows
    ]

@app.get("/sources")
def sources(since: str = Query(...)):
    con = sqlite3.connect("../data/feeds.db")
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