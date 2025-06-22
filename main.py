from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Any
from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")

if not APIFY_TOKEN:
    raise Exception("❌ Missing APIFY_TOKEN in environment.")

client = ApifyClient(APIFY_TOKEN)

app = FastAPI(title="Apify Comment Scraper API")


# ─── LinkedIn Comments Endpoint with postIds ─────────────────────────────

class LinkedInScrapeRequest(BaseModel):
    postIds: List[str]
    page_number: int = 1
    sortOrder: str = "most recent"
    limit: int = 100

class ApifyScrapeResult(BaseModel):
    data: List[Any]


@app.post("/linkedin-comments", response_model=ApifyScrapeResult)
def scrape_linkedin_comments(req: LinkedInScrapeRequest):
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
            items = response.items  # ✅ use attribute
            all_items.extend(items)
            if offset + limit >= response.total:  # ✅ use attribute
                break
            offset += limit

        return {"data": all_items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify scrape failed: {str(e)}")


# ─── Instagram Comments Endpoint ─────────────────────────────────────────

class InstagramScrapeRequest(BaseModel):
    url: HttpUrl


@app.post("/instagram-comments", response_model=ApifyScrapeResult)
def scrape_instagram_comments(req: InstagramScrapeRequest):
    try:
        run_input = {"url": str(req.url)}
        run = client.actor("8yz4aO3qlqckRu3nu").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return {"data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apify error: {str(e)}")
