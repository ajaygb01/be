# utils.py

import os
import re
from time import sleep
from selenium.webdriver.common.by import By
import requests
from urllib.parse import urlparse


def check_post_url(url: str) -> str:
    """
    Ensure the URL is a LinkedIn post or reel link.
    """
    parsed = urlparse(url)
    if "linkedin.com" not in parsed.netloc:
        raise ValueError(f"Not a linkedin.com URL: {url}")
    return url


def login_details() -> tuple[str, str]:
    """
    Read LinkedIn credentials from env vars LINKEDIN_LOGIN and LINKEDIN_PASSWORD.
    """
    user = os.getenv("LINKEDIN_LOGIN")
    pwd  = os.getenv("LINKEDIN_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("Set LINKEDIN_LOGIN and LINKEDIN_PASSWORD in your environment")
    return user, pwd


def load_more(kind: str, button_class: str, driver, pause: float = 0.5):
    """
    Click “load more” buttons until they disappear.
    kind = "comments" or "replies" (just for logging)
    button_class = CSS class name of the “see more” button
    """
    while True:
        try:
            btn = driver.find_element(By.CLASS_NAME, button_class)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            btn.click()
            sleep(pause)
        except Exception:
            break


def extract_emails(texts: list[str]) -> list[str]:
    """
    Return the first email found in each string, or empty string.
    """
    out = []
    email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    for t in texts:
        m = email_re.search(t)
        out.append(m.group(0) if m else "")
    return out


def write_data2csv(
    writer,
    names: list[str],
    profiles: list[str],
    avatars: list[str],
    headlines: list[str],
    emails: list[str],
    comments: list[str],
):
    """
    Write one row per comment to the given CSV writer.
    """
    for i in range(len(names)):
        writer.writerow([
            names[i],
            headlines[i] if i < len(headlines) else "",
            avatars[i]   if i < len(avatars)  else "",
            emails[i]    if i < len(emails)   else "",
            comments[i]  if i < len(comments) else "",
        ])


def download_avatars(urls: list[str], names: list[str], dirname: str):
    """
    Download each URL into dirname/{name}.jpg
    """
    os.makedirs(dirname, exist_ok=True)
    for url, name in zip(urls, names):
        if not url:
            continue
        ext = os.path.splitext(url)[1].split("?")[0] or ".jpg"
        fn = os.path.join(dirname, f"{name}{ext}")
        try:
            r = requests.get(url, timeout=10)
            with open(fn, "wb") as f:
                f.write(r.content)
        except Exception:
            pass
