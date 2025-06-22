# main.py

import os
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from instagrapi import Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Instagram Reel Comment Toolbox")


def get_creds() -> Tuple[str, str]:
    user = (
        os.getenv("IG_LOGIN") or
        os.getenv("IG_USERNAME") or
        os.getenv("IG_EMAIL")
    )
    pwd = os.getenv("IG_PASSWORD")
    if not user or not pwd:
        raise HTTPException(500, "Please set IG_LOGIN (or IG_USERNAME/IG_EMAIL) and IG_PASSWORD in your env")
    return user, pwd


# ─── Request & Response Models ─────────────────────────────────────────

class ReelURL(BaseModel):
    reel_url: HttpUrl


class FetchCommentsReq(ReelURL):
    amount: int = 0           # 0 = all comments
    min_id: Optional[str]     # for chunked pagination


class CommentItem(BaseModel):
    pk: int
    username: str
    text: str
    created_at: str           # ISO8601
    like_count: int
    has_liked: Optional[bool]
    replied_to_comment_id: Optional[int]


class FetchCommentsRes(BaseModel):
    comments: List[CommentItem]
    next_min_id: Optional[str]


# ─── Model for Insights Endpoint ────────────────────────────────────────

class InsightsMediaReq(BaseModel):
    reel_url: HttpUrl


# ─── Helpers ────────────────────────────────────────────────────────────

def make_client() -> Client:
    user, pwd = get_creds()
    cl = Client()
    cl.login(user, pwd)
    return cl


def resolve_media_id(cl: Client, url: str) -> str:
    pk = cl.media_pk_from_url(url)
    return cl.media_id(pk)


# ─── Endpoints ─────────────────────────────────────────────────────────

@app.post("/comments", response_model=FetchCommentsRes)
def fetch_comments(req: FetchCommentsReq):
    cl = make_client()
    media_id = resolve_media_id(cl, str(req.reel_url))

    if req.min_id:
        comments, next_min = cl.media_comments_chunk(media_id, req.amount, req.min_id)
    else:
        comments = cl.media_comments(media_id, amount=req.amount)
        next_min = None

    out: List[CommentItem] = []
    for c in comments:
        out.append(CommentItem(
            pk=c.pk,
            username=c.user.username,
            text=c.text,
            created_at=c.created_at_utc.isoformat(),
            like_count=c.like_count or 0,
            has_liked=c.has_liked,
            replied_to_comment_id=c.replied_to_comment_id
        ))
    return FetchCommentsRes(comments=out, next_min_id=next_min)


@app.post("/insights/media", response_model=Dict[str, Any])
def insights_media(req: InsightsMediaReq):
    """
    Retrieve insights for a specific media item by URL.
    """
    cl = make_client()
    media_pk = cl.media_pk_from_url(str(req.reel_url))
    return cl.insights_media(media_pk)


@app.post("/summary", response_model=Dict[str, Any])
def summary(req: ReelURL):
    """
    Combined summary: media insights plus hierarchical comments structure.
    """
    cl = make_client()
    url = str(req.reel_url)
    # fetch insights
    media_pk = cl.media_pk_from_url(url)
    insights = cl.insights_media(media_pk)
    # fetch all comments
    media_id = resolve_media_id(cl, url)
    comments_raw = cl.media_comments(media_id, amount=0)
    # map comments by pk and prepare structure
    comment_map: Dict[int, Dict[str, Any]] = {}
    for c in comments_raw:
        comment_map[c.pk] = {
            "pk": c.pk,
            "username": c.user.username,
            "text": c.text,
            "created_at": c.created_at_utc.isoformat(),
            "like_count": c.like_count or 0,
            "has_liked": c.has_liked,
            "replied_to_comment_id": c.replied_to_comment_id,
            "replies": []  # will populate below
        }
    # nest replies under their parent comments
    root_comments: List[Dict[str, Any]] = []
    for comment in comment_map.values():
        parent_id = comment["replied_to_comment_id"]
        if parent_id and parent_id in comment_map:
            comment_map[parent_id]["replies"].append(comment)
        else:
            root_comments.append(comment)
    # return combined data
    return {
        "insights": insights,
        "comments": root_comments
    }
