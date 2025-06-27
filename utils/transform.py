from datetime import datetime, timezone # Added timezone
from typing import List


def transform_linkedin_post(raw_post: dict) -> dict:
    author_info = raw_post.get("author", {})
    images = raw_post.get("images")
    display_url = images[0] if images else None # Fix for IndexError

    return {
        "post_id": raw_post.get("urn"),
        "type": raw_post.get("type", "unknown"),
        "author": f"{author_info.get('firstName', '')} {author_info.get('lastName', '')}".strip(),
        "author_headline": author_info.get("occupation", ""),
        "author_profile_url": f"https://www.linkedin.com/in/{author_info.get('publicId', '')}",
        # Use datetime.fromtimestamp with timezone.utc
        "created_at": datetime.fromtimestamp(raw_post.get("postedAtTimestamp", 0) / 1000, timezone.utc),
        "display_url": display_url,
        "likes": raw_post.get("numLikes", 0),
        "comments_count": raw_post.get("numComments", 0)
    }


def transform_linkedin_comment(item: dict) -> dict:
    author = item.get("author", {})
    posted_at_ts = item.get("posted_at", {}).get("timestamp", 0)

    # Convert nested replies to RepliesSimple format
    replies_raw = item.get("replies", [])
    replies: List[dict] = []
    for reply in replies_raw:
        reply_author = reply.get("author", {})
        replies.append({
            "name": reply_author.get("name", ""),
            "comment": reply.get("text", "")
        })

    created_at_dt = datetime.fromtimestamp(posted_at_ts / 1000, timezone.utc) if posted_at_ts \
        else datetime.fromtimestamp(0, timezone.utc)

    return {
        "id": item.get("comment_id"),
        "user": author.get("name"),
        "headline": author.get("headline", ""),
        "profile_url": author.get("profile_url", ""),
        "commentLink": item.get("comment_url"), # Changed default from "" to None (by removing default)
        "comment": item.get("text"),
        "likes": item.get("stats", {}).get("total_reactions", 0),
        "created_at": created_at_dt,
        "replies_count": len(item.get("replies", [])),
        "replies": replies
    }


def transform_instagram_post(raw_post: dict) -> dict:
    return {
        "post_id": raw_post.get("post_id"),
        "type": raw_post.get("product_type", "post"),
        "author": raw_post.get("user_posted", ""),
        "author_headline": raw_post.get("bio", ""),
        "author_profile_url": f"https://www.instagram.com/{raw_post.get('user_posted', '')}/",
        "created_at": datetime.fromisoformat(raw_post["date_posted"].replace("Z", "")),
        "display_url": raw_post.get("thumbnail"),
        "likes": raw_post.get("likes", 0),
        "comments_count": raw_post.get("num_comments", 0)
    }


def transform_instagram_comment(item: dict) -> dict:
    return {
        "id": None,
        "user": item.get("user_commenting"),
        "headline": "",
        "profile_url": f"https://www.instagram.com/{item.get('user_commenting', '')}/",
        "comment": item.get("comment"),
        "likes": int(item.get("likes", 0)) if isinstance(item.get("likes"), str) else item.get("likes", 0),
        "created_at": datetime.fromisoformat(item["date_of_comment"].replace("Z", "")),
        "replies_count": item.get("num_replies", 0)
    }
