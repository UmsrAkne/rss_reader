from typing import TypedDict, List, Optional, Any, Tuple
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import time

class TitleDetail(TypedDict, total=False):
    type: str
    language: Optional[str]
    base: str
    value: str

class SummaryDetail(TypedDict, total=False):
    type: str
    language: Optional[str]
    base: str
    value: str

class LinkItem(TypedDict, total=False):
    rel: str
    type: str
    href: str

class RawFeedEntry(TypedDict, total=False):
    title: str
    title_detail: TitleDetail
    links: List[LinkItem]
    link: str
    published: str
    published_parsed: time.struct_time
    comments: str
    summary: str
    summary_detail: SummaryDetail

@dataclass
class FeedEntry:
    title: str
    link: str
    published: Optional[datetime]
    summary: str

def convert_entry(raw: RawFeedEntry) -> FeedEntry:
    published_dt: Optional[datetime] = None

    if "published_parsed" in raw and raw["published_parsed"]:
        published_dt = datetime(*raw["published_parsed"][:6])

    return FeedEntry(
        title=raw.get("title", ""),
        link=raw.get("link", ""),
        published=published_dt,
        summary=raw.get("summary", ""),
    )