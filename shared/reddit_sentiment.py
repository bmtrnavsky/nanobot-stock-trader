#!/usr/bin/env python3
"""
Reddit sentiment/discovery via PRAW (free tier, personal/research use,
100 QPM). Requires a Reddit app registered at reddit.com/prefs/apps.

Input (stdin): JSON {
  "query": "GSAT",             # ticker or search term
  "subreddits": ["stocks", "swingtrading", "smallcapstocks"],
  "limit": 15,
  "client_id": "...", "client_secret": "...", "user_agent": "..."
}
  Credentials can also come from env vars REDDIT_CLIENT_ID,
  REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT instead of the payload.

Output (stdout): JSON {"posts": [{...}], "status": "ok"}

Requires: uv run --with praw python3 reddit_sentiment.py
"""
import json
import os
import sys

import praw

DEFAULT_SUBREDDITS = ["stocks", "wallstreetbets", "swingtrading",
                       "smallcapstocks", "pennystocks"]


def get_client(payload: dict) -> praw.Reddit:
    client_id = payload.get("client_id") or os.environ.get("REDDIT_CLIENT_ID")
    client_secret = payload.get("client_secret") or os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = payload.get("user_agent") or os.environ.get(
        "REDDIT_USER_AGENT", "nanobot-stock-research/1.0"
    )
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing Reddit credentials. Register a free app at "
            "reddit.com/prefs/apps and provide client_id/client_secret "
            "via payload or REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET env vars."
        )
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def search_posts(reddit: praw.Reddit, query: str, subreddits: list, limit: int) -> list:
    results = []
    sub_str = "+".join(subreddits)
    subreddit = reddit.subreddit(sub_str)
    for post in subreddit.search(query, sort="new", time_filter="month", limit=limit):
        results.append({
            "title": post.title,
            "subreddit": str(post.subreddit),
            "score": post.score,
            "num_comments": post.num_comments,
            "created_utc": post.created_utc,
            "url": f"https://reddit.com{post.permalink}",
            "selftext_excerpt": (post.selftext or "")[:300],
        })
    return results


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    query = payload.get("query")
    if not query:
        print(json.dumps({"status": "error", "reason": "no query provided"}))
        sys.exit(1)

    subreddits = payload.get("subreddits", DEFAULT_SUBREDDITS)
    limit = payload.get("limit", 15)

    try:
        reddit = get_client(payload)
        posts = search_posts(reddit, query, subreddits, limit)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(1)

    print(json.dumps({"status": "ok", "posts": posts}, indent=2, default=str))


if __name__ == "__main__":
    main()
