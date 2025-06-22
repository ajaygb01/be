# main.py

import os
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from instagrapi import Client
from dotenv import load_dotenv
from linkedin_routes import router as linkedin_router

load_dotenv()

app = FastAPI(title="Instagram Reel Comment Toolbox")

# ─── Path to your pre-auth’d session ────────────────────────────────────
SESSION_FILE = os.getenv("IG_SESSION_FILE", "ig_session.json")

def get_creds() -> Tuple[str, str]:
    user = os.getenv("IG_LOGIN") or os.getenv("IG_USERNAME") or os.getenv("IG_EMAIL")
    pwd  = os.getenv("IG_PASSWORD")
    if not user or not pwd:
        raise HTTPException(500, "Set IG_LOGIN and IG_PASSWORD in your env")
    return user, pwd

def make_client() -> Client:
    user, pwd = get_creds()
    cl = Client()
    # 1) Load saved session (cookies, tokens, 2FA, etc.)
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
    # 2) If the session file wasn't valid or expired, fallback to login & re-dump
    if not getattr(cl, "user_id", None):
        cl.login(user, pwd)
        cl.dump_settings(SESSION_FILE)
    return cl

def resolve_media_id(cl: Client, url: str) -> str:
    pk = cl.media_pk_from_url(url)
    return cl.media_id(pk)


# ─── Request & Response Models ─────────────────────────────────────────

class ReelURL(BaseModel):
    reel_url: HttpUrl

class FetchCommentsReq(ReelURL):
    amount: int = 0
    min_id: Optional[str]

class CommentItem(BaseModel):
    pk: int
    username: str
    text: str
    created_at: str
    like_count: int
    has_liked: Optional[bool]
    replied_to_comment_id: Optional[int]

class FetchCommentsRes(BaseModel):
    comments: List[CommentItem]
    next_min_id: Optional[str]

class InsightsMediaReq(BaseModel):
    reel_url: HttpUrl


# ─── Endpoints ─────────────────────────────────────────────────────────

app.include_router(linkedin_router)
@app.post("/comments", response_model=FetchCommentsRes)
def fetch_comments(req: FetchCommentsReq):
    cl = make_client()
    media_id = resolve_media_id(cl, str(req.reel_url))
    if req.min_id:
        comments, next_min = cl.media_comments_chunk(media_id, req.amount, req.min_id)
    else:
        comments = cl.media_comments(media_id, amount=req.amount)
        next_min = None

    out = []
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
    return out

@app.post("/insights/media", response_model=Dict[str, Any])
def insights_media(req: InsightsMediaReq):
    cl = make_client()
    media_pk = cl.media_pk_from_url(str(req.reel_url))
    return cl.insights_media(media_pk)

@app.post("/summary", response_model=list)
def summary(req: InsightsMediaReq):
    cl = make_client()
    media_pk = cl.media_pk_from_url(str(req.reel_url))

    # 1) Get insights
    insights = cl.insights_media(media_pk)

    # 2) Get all comments
    comments = cl.media_comments(media_pk, amount=0)
    reply_map: Dict[int, Dict[str, Any]] = {}
    top_comments: List[Dict[str, Any]] = []

    for c in comments:
        item = {
            "pk": c.pk,
            "username": c.user.username,
            "comment": c.text,
            "created_at": c.created_at_utc.isoformat(),
            "likes": c.like_count or 0,
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

    return top_comments
