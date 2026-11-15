#!/usr/bin/env python3
"""Fetch everything the profile cards needs and write assets/profile.json.

- GitHub stats + stars/description/language of the repos listed in profile.config.json (GraphQL, needs a token)
- Latest posts from the blog RSS feed

Standard library only, so CI needs no extra deps.
Token: $STATS_TOKEN (PAT, private-inclusive commits) or $GH_TOKEN / $GITHUB_TOKEN.

    STATS_TOKEN=$(gh auth token) python3 scripts/fetch_profile_data.py
"""
import datetime
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "profile.json")

with open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8") as source:
    CONFIG = json.load(source)
LOGIN = CONFIG["github_username"]
FEED = CONFIG.get("posts", {}).get("feed_url")
REPOS = [t["repo"] for t in CONFIG.get("targets", [])]

TOKEN = os.environ.get("STATS_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
UA = "profile-board-generator"


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, method="POST")
    req.add_header("Authorization", f"bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


def fetch_stats():
    u = gql(
        """query($login:String!){ user(login:$login){
             createdAt followers{totalCount}
             repositories(privacy:PUBLIC, ownerAffiliations:OWNER){totalCount}
           }}""",
        {"login": LOGIN},
    )["user"]
    stars, cursor = 0, None
    while True:
        page = gql(
            """query($login:String!,$cursor:String){ user(login:$login){
                 repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER, after:$cursor){
                   nodes{stargazerCount} pageInfo{hasNextPage endCursor}}}}""",
            {"login": LOGIN, "cursor": cursor},
        )["user"]["repositories"]
        stars += sum(n["stargazerCount"] for n in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    commits = 0
    this_year = datetime.datetime.now(datetime.timezone.utc).year
    for year in range(int(u["createdAt"][:4]), this_year + 1):
        cc = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from,to:$to){
                   totalCommitContributions}}}""",
            {"login": LOGIN, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"]
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": stars,
        "commits": commits,
        "followers": u["followers"]["totalCount"],
    }


def fetch_repos():
    out = {}
    for name in REPOS:
        r = gql(
            """query($o:String!,$n:String!){ repository(owner:$o,name:$n){
                 stargazerCount description url primaryLanguage{name} }}""",
            {"o": LOGIN, "n": name},
        )["repository"]
        if r:
            out[name] = {
                "stars": r["stargazerCount"],
                "description": r["description"] or "",
                "url": r["url"],
                "language": (r["primaryLanguage"] or {}).get("name", ""),
            }
    return out


def fetch_posts(limit=20):
    if not FEED or CONFIG.get("posts", {}).get("count", 3) <= 0:
        return []
    req = urllib.request.Request(FEED, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    posts = []
    for item in root.iter("item"):
        pub = datetime.datetime.strptime(item.findtext("pubDate")[:16], "%a, %d %b %Y")
        posts.append({"title": item.findtext("title"), "url": item.findtext("link"), "date": pub.strftime("%Y-%m-%d")})
        if len(posts) >= limit:
            break
    return posts


def main():
    if not TOKEN:
        sys.exit("No token in STATS_TOKEN / GH_TOKEN / GITHUB_TOKEN")
    previous = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            previous = json.load(f)
    data = {"stats": fetch_stats(), "repos": fetch_repos()}
    try:
        data["posts"] = fetch_posts()
    except Exception as e:  # blog down? keep yesterday's posts rather than failing
        print("feed fetch failed, keeping previous posts:", e, file=sys.stderr)
        data["posts"] = previous.get("posts", [])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

