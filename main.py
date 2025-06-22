from fastapi import FastAPI, HTTPException, Depends, Header
from apify_client import ApifyClient
from dotenv import load_dotenv
import os
from typing import List
from datetime import datetime
from models import (
    LinkedInFullRequest,
    LinkedInFullResult,
    LinkedInScrapeRequest,
    InstagramScrapeRequest,
    ApifyScrapeResult
)
from utils.transform import (
    transform_linkedin_post,
    transform_linkedin_comment,
    transform_instagram_post,
    transform_instagram_comment
)

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────

APIFY_TOKEN = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")
API_KEY = os.getenv("API_KEY", "ajay2025secret")

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

        structured_items = []
        for item in items:
            post = transform_instagram_post(item)
            comments = [transform_instagram_comment(c) for c in item.get("top_comments", [])]
            structured_items.append({
                "post": post,
                "comments": comments
            })

        return {"data": structured_items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify error: {str(e)}")


# ─── LinkedIn Full Info (Post + Comments) ────────────────────────────────

@app.post("/linkedin-full", response_model=LinkedInFullResult)
def scrape_linkedin_post_and_comments(
    req: LinkedInFullRequest,
    _: str = Depends(verify_api_key)
):
    try:
        # 1. Post info scrape
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

        # 2. Comment scrape
        comments_input = {
            "postIds": [str(req.url)],
            "page_number": 1,
            "sortOrder": "most recent",
            "limit": 100
        }
        comment_run = client.actor("2XnpwxfhSW1fAWElp").call(run_input=comments_input)
        comment_items = list(client.dataset(comment_run["defaultDatasetId"]).iterate_items())

        # 3. Transform post + comments
        post = transform_linkedin_post(post_info_items[0])
        comments = [
            transform_linkedin_comment(item)
            for item in comment_items if item.get("comment_id")
        ]

        return {
            "post": post,
            "comments": comments
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify full scrape failed: {str(e)}")
