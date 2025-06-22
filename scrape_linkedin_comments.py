import os
import re
from time import sleep
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# regex to pull emails from comment text
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def scrape_comments(
    post_url: str,
    headless: bool = True,
    pause: float = 0.5,
    load_replies: bool = False
) -> List[Dict[str, Any]]:
    # 1) Validate URL
    parsed = urlparse(post_url)
    if "linkedin.com" not in parsed.netloc:
        raise ValueError("Invalid LinkedIn URL")

    # 2) Credentials from environment
    USER = os.getenv("LINKEDIN_LOGIN")
    PWD  = os.getenv("LINKEDIN_PASSWORD")
    if not (USER and PWD):
        raise RuntimeError("Set LINKEDIN_LOGIN & LINKEDIN_PASSWORD in env")

    # 3) Launch headless Chrome
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )

    # 4) Log in
    driver.get("https://www.linkedin.com/login")
    driver.find_element(By.ID, "username").send_keys(USER)
    driver.find_element(By.ID, "password").send_keys(PWD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    sleep(1)

    # 5) Navigate to the post and scroll the comments container into view
    driver.get(post_url)
    # use the comments-list div as our scroll target
    comments_div = driver.find_element(
        By.CSS_SELECTOR,
        "div.comments-comments-list.comments-comments-list--cr"
    )
    ActionChains(driver).move_to_element(comments_div).perform()
    sleep(1)

    # 6) Click “load more comments” until it disappears
    while True:
        try:
            btn = driver.find_element(
                By.CSS_SELECTOR,
                "button.comments-comments-list__load-more-button"
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            sleep(pause)
        except:
            break

    # 7) Optionally load replies
    if load_replies:
        while True:
            try:
                rbtn = driver.find_element(
                    By.CSS_SELECTOR,
                    "button.comments-comments-list__show-replies-button"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", rbtn)
                rbtn.click()
                sleep(pause)
            except:
                break

    # 8) Grab exactly the comments-list HTML and quit
    html = comments_div.get_attribute("outerHTML")
    driver.quit()

    # 9) Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.comments-comment-entity")
    results: List[Dict[str, Any]] = []

    for art in articles:
        # — Actor & Avatar
        actor_link = art.select_one("a.comments-comment-meta__image-link")
        profile_url = actor_link["href"] if actor_link and actor_link.has_attr("href") else ""
        img = actor_link.select_one("img") if actor_link else None
        avatar_url = img["src"] if img and img.has_attr("src") else ""

        # — Username (from aria-label)
        aria = actor_link.get("aria-label","") if actor_link else ""
        username = aria.replace("View ", "").replace("’s  graphic link","").strip()

        # — Comment Text
        txt = art.select_one("span[dir='ltr'], span[dir='auto']")
        comment = txt.get_text(strip=True) if txt else ""

        # — Likes
        likes_el = art.select_one(
            "button.comments-comment-social-bar__reactions-count--cr span.v-align-middle"
        )
        likes_txt = likes_el.get_text(strip=True) if likes_el else "0"
        like_count = int(likes_txt) if likes_txt.isdigit() else 0

        # — Replies Count
        replies_el = art.select_one(
            "button.comments-comment-social-bar__action-group--cr + div button"
        )
        replies_txt = replies_el.get_text(strip=True) if replies_el else ""
        m = re.search(r"View\s+(\d+)\s+repli", replies_txt)
        replies_count = int(m.group(1)) if m else 0

        # — Email in comment (if any)
        m2 = EMAIL_RE.search(comment)
        email = m2.group(0) if m2 else ""

        results.append({
            "username":      username,
            "profile_url":   profile_url,
            "avatar_url":    avatar_url,
            "comment":       comment,
            "email":         email,
            "like_count":    like_count,
            "replies_count": replies_count
        })

    return results
