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
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "profile.json")

with open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8") as source:
    CONFIG = json.load(source)
LOGIN = CONFIG["github_username"]
FEED = CONFIG.get("posts", {}).get("feed_url")
TARGETS = CONFIG.get("targets", [])

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
    activity = dict(commits=0, pull_requests=0, reviews=0, issues=0,
                    contributions=0, private_contributions=0)
    this_year = datetime.datetime.now(datetime.timezone.utc).year
    for year in range(int(u["createdAt"][:4]), this_year + 1):
        cc = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from,to:$to){
                   totalCommitContributions totalPullRequestContributions
                   totalPullRequestReviewContributions totalIssueContributions
                   restrictedContributionsCount
                   contributionCalendar{totalContributions}}}}""",
            {"login": LOGIN, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]
        for key, field in {
            "commits": "totalCommitContributions",
            "pull_requests": "totalPullRequestContributions",
            "reviews": "totalPullRequestReviewContributions",
            "issues": "totalIssueContributions",
            "private_contributions": "restrictedContributionsCount",
        }.items():
            activity[key] += cc[field]
        # Calendar totals already include shared private activity. Never add it twice.
        activity["contributions"] += cc["contributionCalendar"]["totalContributions"]
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": stars,
        **activity,
        "followers": u["followers"]["totalCount"],
    }


def fetch_repos():
    out = {}
    for target in TARGETS:
        name = target["repo"]
        r = gql(
            """query($o:String!,$n:String!){ repository(owner:$o,name:$n){
                 stargazerCount description url primaryLanguage{name} }}""",
            {"o": target.get("owner", LOGIN), "n": name},
        )["repository"]
        if r:
            out[name] = {
                "stars": r["stargazerCount"],
                "description": r["description"] or "",
                "url": r["url"],
                "language": (r["primaryLanguage"] or {}).get("name", ""),
            }
    return out


class BlogPage(HTMLParser):
    """Read public article links and JSON-LD without executing website scripts."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.documents = []
        self.json_parts = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            url = urljoin(self.base_url, attrs.get("href", ""))
            parsed = urlparse(url)
            if (parsed.netloc == urlparse(self.base_url).netloc
                    and parsed.path.startswith("/blog/") and url not in self.links):
                self.links.append(url)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.json_parts = []

    def handle_data(self, data):
        if self.json_parts is not None:
            self.json_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.json_parts is not None:
            self.documents.append(json.loads("".join(self.json_parts)))
            self.json_parts = None


def structured_articles(value):
    if isinstance(value, list):
        for item in value:
            yield from structured_articles(item)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if "BlogPosting" in types or "Article" in types:
            yield value
        if "@graph" in value:
            yield from structured_articles(value["@graph"])


def read_blog_page(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode("utf-8")
    page = BlogPage(url)
    page.feed(content)
    return page


def fetch_posts(limit=3):
    config = CONFIG.get("posts", {})
    count = min(3, limit, config.get("count", 3))
    if count <= 0:
        return []
    archive = config.get("archive_url")
    if archive:
        page = read_blog_page(archive)
        posts = []
        # The website archive is newest-first; featured links are deduplicated.
        for url in page.links[:count]:
            article_page = read_blog_page(url)
            articles = [article for doc in article_page.documents
                        for article in structured_articles(doc)]
            if not articles:
                raise ValueError(f"No article metadata at {url}")
            article = articles[0]
            date = datetime.date.fromisoformat(article["datePublished"][:10])
            posts.append({"title": article["headline"], "url": url, "date": date.isoformat()})
        if not posts:
            raise ValueError("Blog archive contains no article links")
        return sorted(posts, key=lambda post: post["date"], reverse=True)
    if not FEED:
        return []
    req = urllib.request.Request(FEED, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        root = ET.fromstring(response.read())
    posts = []
    for item in root.iter("item"):
        date = parsedate_to_datetime(item.findtext("pubDate")).date()
        posts.append({"title": item.findtext("title"), "url": item.findtext("link"), "date": date.isoformat()})
    return sorted(posts, key=lambda post: post["date"], reverse=True)[:count]


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

