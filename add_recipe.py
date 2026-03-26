#!/usr/bin/env python3
"""
add_recipe.py — add a recipe to recipes.json and push to GitHub.

Usage:
  python3 add_recipe.py \
    --name "Keto Butter Chicken" \
    --url "https://youtube.com/watch?v=..." \
    --tags "keto,chicken,dinner" \
    --notes "Optional short note"
"""

import sys, json, re, argparse, base64, os
from datetime import date
from urllib.request import urlopen, Request
from urllib.parse import urlparse

REPO = "notOccupanther/recipe-vault"
FILE = "recipes.json"

def get_gh_token():
    import subprocess
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    return r.stdout.strip()

def gh_get(token, path):
    req = Request(f"https://api.github.com/repos/{REPO}/contents/{path}",
                  headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urlopen(req) as r:
        return json.load(r)

def gh_put(token, path, content_str, sha, message):
    body = json.dumps({
        "message": message,
        "content": base64.b64encode(content_str.encode()).decode(),
        "sha": sha
    }).encode()
    req = Request(f"https://api.github.com/repos/{REPO}/contents/{path}",
                  data=body, method="PUT",
                  headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                           "Content-Type": "application/json"})
    with urlopen(req) as r:
        d = json.load(r)
    return d["commit"]["sha"][:7]

def detect_platform(url):
    h = urlparse(url).netloc.lower()
    if "youtube" in h or "youtu.be" in h: return "youtube"
    if "tiktok" in h: return "tiktok"
    if "instagram" in h: return "instagram"
    if "twitter" in h or "x.com" in h: return "twitter"
    if "reddit" in h: return "reddit"
    return "web"

def get_yt_id(url):
    m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else None

def get_thumbnail(url, platform):
    if platform == "youtube":
        vid = get_yt_id(url)
        if vid:
            return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
    # Try og:image scrape for other platforms
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=8) as r:
            html = r.read(30000).decode("utf-8", errors="ignore")
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\'](https?://[^"\']+)', html)
        if not m:
            m = re.search(r'content=["\'](https?://[^"\']+)["\'][^>]*property=["\']og:image["\']', html)
        if m: return m.group(1)
    except Exception as e:
        print(f"  (thumbnail scrape failed: {e})")
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--url",  required=True)
    parser.add_argument("--tags", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    token = get_gh_token()
    platform = detect_platform(args.url)
    print(f"Platform: {platform}")

    print("Fetching thumbnail...")
    thumb = get_thumbnail(args.url, platform)
    print(f"Thumbnail: {thumb or '(none)'}")

    print("Fetching current recipes.json from GitHub...")
    remote = gh_get(token, FILE)
    sha = remote["sha"]
    current = json.loads(base64.b64decode(remote["content"]).decode())

    import uuid
    entry = {
        "id":        str(uuid.uuid4())[:8],
        "name":      args.name,
        "url":       args.url,
        "platform":  platform,
        "thumbnail": thumb,
        "tags":      [t.strip() for t in args.tags.split(",") if t.strip()],
        "notes":     args.notes,
        "added":     date.today().isoformat()
    }

    current["recipes"].append(entry)
    new_content = json.dumps(current, indent=2, ensure_ascii=False)

    print("Pushing update...")
    commit = gh_put(token, FILE, new_content, sha, f"Add recipe: {args.name}")
    print(f"✓ {args.name} → {commit}")
    print(f"  https://notoccupanther.github.io/recipe-vault/")

if __name__ == "__main__":
    main()
