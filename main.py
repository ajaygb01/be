# main.py

import os
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from instagrapi import Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Instagram Reel Comment Toolbox")

# Path to cache your logged-in session
SESSION_FILE = os.getenv("IG_SESSION_FILE", "ig_session.json")


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

class PostCommentReq(ReelURL):
    text: str
    replied_to_comment_id: Optional[int]

class CommentActionReq(ReelURL):
    comment_pk: int

class BulkDeleteReq(ReelURL):
    comment_pks: List[int]


# ─── Models for Insights Endpoints ─────────────────────────────────────

class InsightsMediaReq(BaseModel):
    reel_url: HttpUrl


# ─── Helpers ────────────────────────────────────────────────────────────

def make_client() -> Client:
    user, pwd = get_creds()
    cl = Client()
    # try loading a saved session
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
    # only login if not already authenticated
    if not cl.user_id:
        cl.login(user, pwd)
        # save session for next time
        cl.dump_settings(SESSION_FILE)
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


# ─── Insights: Media Endpoint ───────────────────────────────────────────

@app.post("/insights/media", response_model=Dict[str, Any])
def insights_media(req: InsightsMediaReq):
    """
    Retrieve insights for a specific media item by URL.
    """
    cl = make_client()
    media_pk = cl.media_pk_from_url(str(req.reel_url))
    return cl.insights_media(media_pk)


# ─── Summary Endpoint ────────────────────────────────────────────────────

@app.post("/summary", response_model=Dict[str, Any])
def summary(req: InsightsMediaReq):
    cl = make_client()
    # get insights
    media_pk = cl.media_pk_from_url(str(req.reel_url))
    insights = cl.insights_media(media_pk)
    # fetch all comments
    comments = cl.media_comments(media_pk, amount=0)
    # nest replies under their parents
    reply_map: Dict[int, Dict[str, Any]] = {}
    top_comments: List[Dict[str, Any]] = []

    for c in comments:
        item = {
            "pk": c.pk,
            "username": c.user.username,
            "text": c.text,
            "created_at": c.created_at_utc.isoformat(),
            "like_count": c.like_count or 0,
            "has_liked": c.has_liked,
            "replies": []
        }
        reply_map[c.pk] = item
        if c.replied_to_comment_id:
            parent = reply_map.get(c.replied_to_comment_id)
            if parent:
                parent["replies"].append(item)
        else:
            top_comments.append(item)

    return {
        "insights": insights,
        "comments": top_comments
    }
