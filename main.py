from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, HttpUrl
from typing import List, Any
from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────

APIFY_TOKEN = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")
API_KEY = os.getenv("API_KEY", "ajay2025secret")  # Set default or use .env

if not APIFY_TOKEN:
    raise Exception("❌ Missing APIFY_TOKEN in environment.")

client = ApifyClient(APIFY_TOKEN)

app = FastAPI(title="Apify Comment Scraper API")


# ─── API Key Dependency ──────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ─── Models ──────────────────────────────────────────────────────────────

class LinkedInScrapeRequest(BaseModel):
    postIds: List[str]
    page_number: int = 1
    sortOrder: str = "most recent"
    limit: int = 100


class InstagramScrapeRequest(BaseModel):
    url: HttpUrl


class ApifyScrapeResult(BaseModel):
    data: List[Any]


# ─── LinkedIn Endpoint ───────────────────────────────────────────────────

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
            items = response.items
            all_items.extend(items)
            if offset + limit >= response.total:
                break
            offset += limit

        return {"data": all_items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify scrape failed: {str(e)}")


# ─── Instagram Endpoint ──────────────────────────────────────────────────

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
