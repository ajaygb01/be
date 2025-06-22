# main.py

import os
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, HttpUrl
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Instagram Reel Comment Toolbox")

# ─── Globals for authentication/session ────────────────────────────────
_client: Optional[Client] = None
_pending_challenge_url: Optional[str] = None


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

class InsightsMediaReq(BaseModel):
    reel_url: HttpUrl


# ─── Authentication Endpoints ──────────────────────────────────────────

@app.post("/login")
def login():
    """
    Start a login attempt.
    - If credentials succeed immediately, returns {"status": "logged_in"}.
    - If Instagram issues a challenge, returns {"status": "challenge_required", "api_path": "..."}.
    """
    global _client, _pending_challenge_url
    user, pwd = get_creds()
    cl = Client()
    try:
        cl.login(user, pwd)
        _client = cl
        return {"status": "logged_in"}
    except ChallengeRequired as e:
        _client = cl
        _pending_challenge_url = e.last_json.get("challenge", {}).get("api_path")
        return {
            "status": "challenge_required",
            "api_path": _pending_challenge_url
        }


@app.post("/login/challenge")
def login_challenge(code: str = Body(..., embed=True)):
    """
    Resolve a pending 2FA/challenge by passing the code.
    Call this after /login returns challenge_required.
    """
    global _client, _pending_challenge_url
    if not _client or not _pending_challenge_url:
        raise HTTPException(400, "No challenge pending. Call /login first.")
    _client.challenge_code_handler = lambda username, choice: code
    _client.challenge_resolve_simple(_pending_challenge_url)
    return {"status": "logged_in"}


def make_client() -> Client:
    """
    Retrieve the authenticated Client instance, or 401 if not logged in yet.
    """
    if _client and getattr(_client, "user_id", None):
        return _client
    raise HTTPException(401, "Not authenticated. Call /login and /login/challenge first.")


# ─── Helpers ────────────────────────────────────────────────────────────

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
def summary(req: InsightsMediaReq):
    """
    Returns a combined summary of insights + threaded comments.
    """
    cl = make_client()
    media_pk = cl.media_pk_from_url(str(req.reel_url))

    # insights
    insights = cl.insights_media(media_pk)

    # comments
    comments = cl.media_comments(media_pk, amount=0)
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
