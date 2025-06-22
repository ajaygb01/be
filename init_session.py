# init_session.py
import os
from instagrapi import Client
from dotenv import load_dotenv

load_dotenv()  # needs IG_LOGIN & IG_PASSWORD in your .env

cl = Client()
cl.login(os.getenv("IG_LOGIN"), os.getenv("IG_PASSWORD"))
cl.dump_settings("ig_session.json")
print("✅ Session file written to ig_session.json")
