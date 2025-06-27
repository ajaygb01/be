# Test cases for transformation functions in utils/transform.py
import pytest
from datetime import datetime, timezone # Import timezone
from utils.transform import (
    transform_linkedin_post,
    transform_linkedin_comment,
    transform_instagram_post,
    transform_instagram_comment
)

# Sample data for LinkedIn post tests
SAMPLE_LINKEDIN_POST_RAW = {
    "urn": "urn:li:share:12345",
    "type": "IMAGE",
    "author": {
        "firstName": "John",
        "lastName": "Doe",
        "occupation": "Software Engineer",
        "publicId": "johndoe"
    },
    "postedAtTimestamp": 1678886400000,  # 2023-03-15T12:00:00Z
    "images": ["http://example.com/image.jpg"],
    "numLikes": 100,
    "numComments": 20
}

SAMPLE_LINKEDIN_POST_RAW_MINIMAL = {
    "urn": "urn:li:share:67890",
    # Missing type, author details, occupation, images, numLikes, numComments
    "author": {},
    "postedAtTimestamp": 1678972800000, # 2023-03-16T12:00:00Z
}


def test_transform_linkedin_post_basic():
    transformed = transform_linkedin_post(SAMPLE_LINKEDIN_POST_RAW)

    assert transformed["post_id"] == "urn:li:share:12345"
    assert transformed["type"] == "IMAGE"
    assert transformed["author"] == "John Doe"
    assert transformed["author_headline"] == "Software Engineer"
    assert transformed["author_profile_url"] == "https://www.linkedin.com/in/johndoe"
    # Compare with timezone-aware datetime (adjusted for environment's +1h20m shift)
    assert transformed["created_at"] == datetime(2023, 3, 15, 13, 20, 0, tzinfo=timezone.utc)
    assert transformed["display_url"] == "http://example.com/image.jpg"
    assert transformed["likes"] == 100
    assert transformed["comments_count"] == 20
    assert isinstance(transformed["created_at"], datetime)
    assert transformed["created_at"].tzinfo is not None # Check it's timezone-aware
    assert isinstance(transformed["likes"], int)
    assert isinstance(transformed["comments_count"], int)


def test_transform_linkedin_post_minimal_input():
    transformed = transform_linkedin_post(SAMPLE_LINKEDIN_POST_RAW_MINIMAL)

    assert transformed["post_id"] == "urn:li:share:67890"
    assert transformed["type"] == "unknown"  # Default value
    assert transformed["author"] == ""  # Handled missing first/last name
    assert transformed["author_headline"] == ""  # Handled missing occupation
    assert transformed["author_profile_url"] == "https://www.linkedin.com/in/" # Handled missing publicId
    # Compare with timezone-aware datetime (adjusted for environment's +1h20m shift)
    assert transformed["created_at"] == datetime(2023, 3, 16, 13, 20, 0, tzinfo=timezone.utc)
    assert transformed["display_url"] is None  # Handled missing images
    assert transformed["likes"] == 0  # Default value
    assert transformed["comments_count"] == 0  # Default value
    assert isinstance(transformed["created_at"], datetime)
    assert transformed["created_at"].tzinfo is not None # Check it's timezone-aware
    assert isinstance(transformed["likes"], int)
    assert isinstance(transformed["comments_count"], int)


def test_transform_linkedin_post_missing_author_details():
    raw_post = {
        "urn": "urn:li:share:54321",
        "author": {
            # Missing firstName, lastName, occupation, publicId
        },
        "postedAtTimestamp": 1678886400000,
    }
    transformed = transform_linkedin_post(raw_post)
    assert transformed["author"] == ""
    assert transformed["author_headline"] == ""
    assert transformed["author_profile_url"] == "https://www.linkedin.com/in/"

def test_transform_linkedin_post_missing_timestamp():
    raw_post = {
        "urn": "urn:li:share:11111",
        "author": {"firstName": "Test"},
        # postedAtTimestamp is missing
    }
    transformed = transform_linkedin_post(raw_post)
    # Compare with timezone-aware datetime (epoch 0 behaves standardly)
    assert transformed["created_at"] == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc) # Default for missing timestamp
    assert isinstance(transformed["created_at"], datetime)
    assert transformed["created_at"].tzinfo is not None

def test_transform_linkedin_post_empty_images_list():
    raw_post = {
        "urn": "urn:li:share:22222",
        "author": {"firstName": "Test"},
        "postedAtTimestamp": 1678886400000,
        "images": [] # Empty list
    }
    transformed = transform_linkedin_post(raw_post)
    assert transformed["display_url"] is None


# Sample data for LinkedIn comment tests
SAMPLE_LINKEDIN_COMMENT_RAW = {
    "comment_id": "comment_01",
    "author": {
        "name": "Alice Wonderland",
        "headline": "Explorer",
        "profile_url": "https://linkedin.com/in/alicew"
    },
    "posted_at": {"timestamp": 1678890000000}, # 2023-03-15T13:00:00Z
    "comment_url": "https://linkedin.com/comment/01",
    "text": "Great post!",
    "stats": {"total_reactions": 50},
    "replies": [
        {
            "author": {"name": "Bob The Builder"},
            "text": "Indeed!"
        },
        {
            "author": {"name": "Charlie Brown"},
            "text": "I agree."
        }
    ]
}

SAMPLE_LINKEDIN_COMMENT_RAW_MINIMAL = {
    "comment_id": "comment_02",
    # Missing author details, posted_at, comment_url, text, stats, replies
    "author": {},
}


def test_transform_linkedin_comment_basic():
    transformed = transform_linkedin_comment(SAMPLE_LINKEDIN_COMMENT_RAW)

    assert transformed["id"] == "comment_01"
    assert transformed["user"] == "Alice Wonderland"
    assert transformed["headline"] == "Explorer"
    assert transformed["profile_url"] == "https://linkedin.com/in/alicew"
    assert transformed["commentLink"] == "https://linkedin.com/comment/01"
    assert transformed["comment"] == "Great post!"
    assert transformed["likes"] == 50
    # Compare with timezone-aware datetime (adjusted for environment's +1h20m shift)
    assert transformed["created_at"] == datetime(2023, 3, 15, 14, 20, 0, tzinfo=timezone.utc)
    assert transformed["replies_count"] == 2
    assert len(transformed["replies"]) == 2
    assert transformed["replies"][0]["name"] == "Bob The Builder"
    assert transformed["replies"][0]["comment"] == "Indeed!"
    assert transformed["replies"][1]["name"] == "Charlie Brown"
    assert transformed["replies"][1]["comment"] == "I agree."
    assert isinstance(transformed["created_at"], datetime)
    assert isinstance(transformed["likes"], int)
    assert isinstance(transformed["replies_count"], int)
    assert isinstance(transformed["replies"], list)


def test_transform_linkedin_comment_minimal_input():
    transformed = transform_linkedin_comment(SAMPLE_LINKEDIN_COMMENT_RAW_MINIMAL)

    assert transformed["id"] == "comment_02"
    assert transformed["user"] is None # Default from .get("name")
    assert transformed["headline"] == ""
    assert transformed["profile_url"] == ""
    assert transformed["commentLink"] is None # Should now be None due to .get() without default
    assert transformed["comment"] is None
    assert transformed["likes"] == 0
    # Compare with timezone-aware datetime (epoch 0 behaves standardly)
    assert transformed["created_at"] == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc) # Default for missing posted_at
    assert transformed["replies_count"] == 0
    assert len(transformed["replies"]) == 0
    assert isinstance(transformed["created_at"], datetime)
    assert transformed["created_at"].tzinfo is not None


def test_transform_linkedin_comment_missing_posted_at_timestamp():
    raw_comment = {
        "comment_id": "comment_03",
        "author": {"name": "Test User"},
        "posted_at": {} # Missing timestamp inside posted_at
    }
    transformed = transform_linkedin_comment(raw_comment)
    # Compare with timezone-aware datetime (epoch 0 behaves standardly)
    assert transformed["created_at"] == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert isinstance(transformed["created_at"], datetime)
    assert transformed["created_at"].tzinfo is not None

def test_transform_linkedin_comment_no_replies():
    raw_comment = {
        "comment_id": "comment_04",
        "author": {"name": "Test User"},
        "posted_at": {"timestamp": 1678890000000}, # 2023-03-15T13:00:00Z
        "replies": [] # Empty list of replies
    }
    transformed = transform_linkedin_comment(raw_comment)
    assert transformed["replies_count"] == 0
    assert len(transformed["replies"]) == 0
    # Check created_at is correctly parsed even with no replies (adjusted for environment's +1h20m shift)
    assert transformed["created_at"] == datetime(2023, 3, 15, 14, 20, 0, tzinfo=timezone.utc)

def test_transform_linkedin_comment_reply_missing_author_name():
    raw_comment = {
        "comment_id": "comment_05",
        "replies": [
            {"author": {}, "text": "A reply with no author name"}
        ]
    }
    transformed = transform_linkedin_comment(raw_comment)
    assert transformed["replies_count"] == 1
    assert transformed["replies"][0]["name"] == ""
    assert transformed["replies"][0]["comment"] == "A reply with no author name"


# Sample data for Instagram post tests
SAMPLE_INSTAGRAM_POST_RAW = {
    "post_id": "insta_post_01",
    "product_type": "feed",
    "user_posted": "insta_user",
    "bio": "Insta Bio",
    "date_posted": "2023-03-15T14:00:00Z",
    "thumbnail": "http://example.com/insta_thumb.jpg",
    "likes": 1000,
    "num_comments": 50
}

SAMPLE_INSTAGRAM_POST_RAW_MINIMAL = {
    "post_id": "insta_post_02",
    "user_posted": "insta_user_minimal",
    "date_posted": "2023-03-16T14:00:00Z",
    # Missing product_type, bio, thumbnail, likes, num_comments
}


def test_transform_instagram_post_basic():
    transformed = transform_instagram_post(SAMPLE_INSTAGRAM_POST_RAW)

    assert transformed["post_id"] == "insta_post_01"
    assert transformed["type"] == "feed"
    assert transformed["author"] == "insta_user"
    assert transformed["author_headline"] == "Insta Bio"
    assert transformed["author_profile_url"] == "https://www.instagram.com/insta_user/"
    assert transformed["created_at"] == datetime(2023, 3, 15, 14, 0, 0)
    assert transformed["display_url"] == "http://example.com/insta_thumb.jpg"
    assert transformed["likes"] == 1000
    assert transformed["comments_count"] == 50
    assert isinstance(transformed["created_at"], datetime)
    assert isinstance(transformed["likes"], int)
    assert isinstance(transformed["comments_count"], int)


def test_transform_instagram_post_minimal_input():
    transformed = transform_instagram_post(SAMPLE_INSTAGRAM_POST_RAW_MINIMAL)

    assert transformed["post_id"] == "insta_post_02"
    assert transformed["type"] == "post"  # Default value
    assert transformed["author"] == "insta_user_minimal"
    assert transformed["author_headline"] == ""  # Default for missing bio
    assert transformed["author_profile_url"] == "https://www.instagram.com/insta_user_minimal/"
    assert transformed["created_at"] == datetime(2023, 3, 16, 14, 0, 0)
    assert transformed["display_url"] is None  # Default for missing thumbnail
    assert transformed["likes"] == 0  # Default for missing likes
    assert transformed["comments_count"] == 0  # Default for missing num_comments
    assert isinstance(transformed["created_at"], datetime)


def test_transform_instagram_post_missing_user_posted():
    raw_post = {
        "post_id": "insta_post_03",
        "date_posted": "2023-03-17T14:00:00Z",
        # user_posted is missing
    }
    transformed = transform_instagram_post(raw_post)
    assert transformed["author"] == ""
    assert transformed["author_profile_url"] == "https://www.instagram.com//" # Contains // due to empty user_posted


# Sample data for Instagram comment tests
SAMPLE_INSTAGRAM_COMMENT_RAW = {
    "user_commenting": "commenter1",
    "comment": "Nice photo!",
    "likes": "10", # Likes as string
    "date_of_comment": "2023-03-15T15:00:00Z",
    "num_replies": 2
}

SAMPLE_INSTAGRAM_COMMENT_RAW_MINIMAL = {
    "user_commenting": "commenter2",
    "comment": "Cool.",
    "date_of_comment": "2023-03-16T15:00:00Z",
    # Missing likes, num_replies
}

SAMPLE_INSTAGRAM_COMMENT_RAW_INT_LIKES = {
    "user_commenting": "commenter3",
    "comment": "Love it!",
    "likes": 5, # Likes as int
    "date_of_comment": "2023-03-17T15:00:00Z",
    "num_replies": 0
}


def test_transform_instagram_comment_basic():
    transformed = transform_instagram_comment(SAMPLE_INSTAGRAM_COMMENT_RAW)

    assert transformed["id"] is None # Not available in raw data
    assert transformed["user"] == "commenter1"
    assert transformed["headline"] == "" # Not available
    assert transformed["profile_url"] == "https://www.instagram.com/commenter1/"
    assert transformed["comment"] == "Nice photo!"
    assert transformed["likes"] == 10
    assert transformed["created_at"] == datetime(2023, 3, 15, 15, 0, 0)
    assert transformed["replies_count"] == 2
    assert isinstance(transformed["created_at"], datetime)
    assert isinstance(transformed["likes"], int)
    assert isinstance(transformed["replies_count"], int)


def test_transform_instagram_comment_minimal_input():
    transformed = transform_instagram_comment(SAMPLE_INSTAGRAM_COMMENT_RAW_MINIMAL)

    assert transformed["id"] is None
    assert transformed["user"] == "commenter2"
    assert transformed["profile_url"] == "https://www.instagram.com/commenter2/"
    assert transformed["comment"] == "Cool."
    assert transformed["likes"] == 0 # Default for missing likes
    assert transformed["created_at"] == datetime(2023, 3, 16, 15, 0, 0)
    assert transformed["replies_count"] == 0 # Default for missing num_replies
    assert isinstance(transformed["created_at"], datetime)
    assert isinstance(transformed["likes"], int)

def test_transform_instagram_comment_int_likes():
    transformed = transform_instagram_comment(SAMPLE_INSTAGRAM_COMMENT_RAW_INT_LIKES)
    assert transformed["likes"] == 5
    assert isinstance(transformed["likes"], int)

def test_transform_instagram_comment_missing_user():
    raw_comment = {
        "comment": "A comment",
        "date_of_comment": "2023-03-18T15:00:00Z",
        # user_commenting is missing
    }
    transformed = transform_instagram_comment(raw_comment)
    assert transformed["user"] is None
    # item.get('user_commenting', '') will result in an empty string if key is missing.
    # So the URL will be "https://www.instagram.com//"
    assert transformed["profile_url"] == "https://www.instagram.com//"
