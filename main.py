from fastapi import FastAPI, HTTPException, Depends, Header
from apify_client import ApifyClient
from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from datetime import datetime
from models import (
    LinkedInFullRequest,
    LinkedInFullResult,
    LinkedInScrapeRequest,
    InstagramScrapeRequest,
    ApifyScrapeResult
)

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────

APIFY_TOKEN = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")
API_KEY = os.getenv("API_KEY", "ajay2025secret")  # Default static key

if not APIFY_TOKEN:
    raise Exception("❌ Missing APIFY_TOKEN in environment.")

client = ApifyClient(APIFY_TOKEN)
app = FastAPI(title="Apify Comment Scraper API")


# ─── API Key Verification ────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ─── LinkedIn Comments ───────────────────────────────────────────────────

@app.post("/linkedin-comments", response_model=ApifyScrapeResult)
def scrape_linkedin_comments(
    req: LinkedInScrapeRequest,
    _: str = Depends(verify_api_key)
):
    try:
        run_input = {
            "postIds": req.postIds,
            "page_number": req.page_number,
            "sortOrder": req.sortOrder,
            "limit": req.limit,
        }

        run = client.actor("2XnpwxfhSW1fAWElp").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"])

        all_items = []
        offset = 0
        limit = 1000

        while True:
            response = dataset.list_items(limit=limit, offset=offset)
            all_items.extend(response.items)
            if offset + limit >= response.total:
                break
            offset += limit

        return {"data": all_items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify scrape failed: {str(e)}")


# ─── Instagram Comments ──────────────────────────────────────────────────

@app.post("/instagram-comments", response_model=ApifyScrapeResult)
def scrape_instagram_comments(
    req: InstagramScrapeRequest,
    _: str = Depends(verify_api_key)
):
    try:
        run_input = {"url": str(req.url)}
        run = client.actor("8yz4aO3qlqckRu3nu").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return {"data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify error: {str(e)}")


# ─── LinkedIn Full Info (Post + Comments) ────────────────────────────────

@app.post("/linkedin-full", response_model=LinkedInFullResult)
def scrape_linkedin_post_and_comments(
    req: LinkedInFullRequest,
    _: str = Depends(verify_api_key)
):
    try:
        # 1. Post scrape
        post_info_input = {
            "urls": [str(req.url)],
            "deepScrape": True,
            "rawData": False,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyCountry": "US"
            }
        }
        post_run = client.actor("kfiWbq3boy3dWKbiL").call(run_input=post_info_input)
        post_info_items = list(client.dataset(post_run["defaultDatasetId"]).iterate_items())

        # 2. Comments scrape
        comments_input = {
            "postIds": [str(req.url)],
            "page_number": 1,
            "sortOrder": "most recent",
            "limit": 100
        }
        comment_run = client.actor("2XnpwxfhSW1fAWElp").call(run_input=comments_input)
        comment_items = list(client.dataset(comment_run["defaultDatasetId"]).iterate_items())

        # 3. Flatten post
        raw_post = post_info_items[0]
        author_info = raw_post.get("author", {})
        post = {
            "post_id": raw_post.get("urn"),
            "type": raw_post.get("type", "unknown"),
            "author": f"{author_info.get('firstName', '')} {author_info.get('lastName', '')}".strip(),
            "author_headline": author_info.get("occupation", ""),
            "author_profile_url": f"https://www.linkedin.com/in/{author_info.get('publicId', '')}",
            "created_at": datetime.utcfromtimestamp(raw_post.get("postedAtTimestamp", 0) / 1000),
            "display_url": raw_post.get("images", [None])[0],
            "likes": raw_post.get("numLikes", 0),
            "comments_count": raw_post.get("numComments", 0)
        }

        # 4. Flatten comments
        comments = []
        for item in comment_items:
            if not item.get("comment_id"):
                continue  # skip blank summary row
            author = item.get("author", {})
            posted_at = item.get("posted_at", {}).get("timestamp", 0)

            comment = {
                "id": item.get("comment_id"),
                "user": author.get("name"),
                "headline": author.get("headline", ""),
                "profile_url": author.get("profile_url", ""),
                "comment": item.get("text"),
                "likes": item.get("stats", {}).get("reactions", {}).get("like", 0),
                "created_at": datetime.utcfromtimestamp(posted_at / 1000) if posted_at else datetime.utcfromtimestamp(0),
                "replies_count": len(item.get("replies", []))
            }
            comments.append(comment)

        return {
            "post": post,
            "comments": comments
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify full scrape failed: {str(e)}")
