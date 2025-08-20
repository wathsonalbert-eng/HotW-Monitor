import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# --- your Telegram secrets (already set in Replit → Secrets) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- the page to monitor (Hot Wheels listing) ---
URL = "https://www.firstcry.com/hot-wheels/0/0/113"

STATE_FILE = "last_hash.txt"
CHECK_EVERY_SECONDS = 30

# ---------------- keep-alive server ----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------------------------

def send_telegram(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=10,
        )
    except Exception as e:
        print("Telegram error:", e)

def get_page_signature(url: str) -> str:
    """Fetch page HTML, strip noisy parts (scripts/styles/extra spaces),
    and return a stable hash string."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # remove script/style/noscript to avoid ad/analytics noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # keep only the body content (less header/footer noise)
    body = soup.body.get_text(" ", strip=True) if soup.body else soup.get_text(" ", strip=True)

    # normalize whitespace
    normalized = " ".join(body.split())

    # hash the normalized text
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def load_last_hash() -> str | None:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return None

def save_last_hash(h: str):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(h)

def main():
    last_hash = load_last_hash()
    try:
        current_hash = get_page_signature(URL)
    except Exception as e:
        print("Initial fetch error:", e)
        send_telegram(f"⚠️ Initial fetch failed: {e}")
        return

    if last_hash is None:
        save_last_hash(current_hash)
        send_telegram("🟢 Monitor started for FirstCry Hot Wheels.\nI'll alert you when the page changes.")
        print("Monitor started; baseline hash saved.")
    else:
        print("Resumed with existing baseline.")

    while True:
        try:
            new_hash = get_page_signature(URL)
            if new_hash != load_last_hash():
                # change detected
                save_last_hash(new_hash)
                send_telegram(f"🚨 Hot Wheels page changed! Check now:\n{URL}")
                print("Change detected and alert sent.")
            else:
                print("No change.")
        except Exception as e:
            print("Loop error:", e)
            send_telegram(f"⚠️ Error while checking page: {e}")

        time.sleep(CHECK_EVERY_SECONDS)

if __name__ == "__main__":
    keep_alive()   # start Flask server
    main()         # start monitor
