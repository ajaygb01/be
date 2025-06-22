# linkedin_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any

from scrape_linkedin_comments import scrape_comments

router = APIRouter(tags=["linkedin"])

class LinkedInRequest(BaseModel):
    post_url: HttpUrl

@router.post(
    "/linkedin/comments",
    response_model=List[Dict[str, Any]],
    summary="Scrape LinkedIn post comments",
    description="Provide a LinkedIn post URL and get JSON list of comments."
)
def linkedin_comments(req: LinkedInRequest):
    """
    Expects JSON: { "post_url": "<linkedin post URL>" }
    """
    try:
        # Just pass post_url; all other args use their defaults
        return scrape_comments(post_url=str(req.post_url))
    except Exception as e:
        raise HTTPException(502, f"LinkedIn scraper error: {e}")
