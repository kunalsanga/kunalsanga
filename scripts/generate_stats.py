#!/usr/bin/env python3
"""
GitHub Profile Stats Generator
------------------------------
Collects verified data from GitHub REST & GraphQL APIs and generates
dark-themed, responsive SVGs and normalized JSON for kunalsanga's profile.

Features:
- Zero external dependencies (uses standard library urllib, json, etc.)
- Multi-page repository pagination
- Verified byte-level language calculation
- GraphQL contribution collection & streak analysis (with token)
- Graceful rate-limit fallback & last-known-good preservation
- Validated SVG output matching the profile's radical/dark theme
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Standard language colors matching GitHub's color palette
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "Solidity": "#AA6746",
    "Dart": "#00B4AB",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Vue": "#41b883",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Other": "#8b949e"
}

DEFAULT_COLOR = "#8b949e"


def format_bytes(byte_count: int) -> str:
    """Format bytes into readable units (B, KB, MB, GB)."""
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    elif byte_count < 1024 * 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.1f} MB"
    else:
        return f"{byte_count / (1024 * 1024 * 1024):.2f} GB"


def format_number(val: int) -> str:
    """Format large numbers with k notation or commas."""
    if val >= 1000:
        return f"{val:,}"
    return str(val)


def make_request(url: str, token: str = None, post_data: bytes = None) -> dict:
    """Make an HTTP request with proper headers and error handling."""
    headers = {
        "User-Agent": "kunalsanga-ProfileStats/1.0",
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers, data=post_data)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} for {url}: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Failed request to {url}: {str(e)}")


def fetch_github_data(username: str, token: str = None) -> dict:
    """Fetch complete verified metrics for user."""
    stats = {
        "username": username,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub REST & GraphQL API",
        "is_authenticated": bool(token),
        "user": {},
        "repos": {
            "total_public": 0,
            "total_forks_owned": 0,
            "total_sources_owned": 0,
            "total_stars": 0,
            "total_forks_count": 0,
            "total_open_issues": 0
        },
        "languages": {
            "breakdown": {},
            "total_bytes": 0,
            "percentages": {}
        },
        "contributions": {
            "total_year": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "total_commits": 0,
            "total_prs": 0,
            "total_issues": 0,
            "total_reviews": 0,
            "has_graphql_data": False
        }
    }

    # 1. User details
    user_url = f"https://api.github.com/users/{username}"
    user_data = make_request(user_url, token)
    stats["user"] = {
        "name": user_data.get("name") or username,
        "login": user_data.get("login"),
        "public_repos": user_data.get("public_repos", 0),
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "created_at": user_data.get("created_at")
    }

    # 2. Paginate public repos
    all_repos = []
    page = 1
    while True:
        repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        page_repos = make_request(repos_url, token)
        if not page_repos:
            break
        all_repos.extend(page_repos)
        if len(page_repos) < 100:
            break
        page += 1

    stats["repos"]["total_public"] = len(all_repos)

    lang_bytes = {}
    total_stars = 0
    total_forks_count = 0
    total_open_issues = 0
    source_repos = []

    for r in all_repos:
        if r.get("fork"):
            stats["repos"]["total_forks_owned"] += 1
            continue
        stats["repos"]["total_sources_owned"] += 1
        total_stars += r.get("stargazers_count", 0)
        total_forks_count += r.get("forks_count", 0)
        total_open_issues += r.get("open_issues_count", 0)
        source_repos.append(r)

    stats["repos"]["total_stars"] = total_stars
    stats["repos"]["total_forks_count"] = total_forks_count
    stats["repos"]["total_open_issues"] = total_open_issues

    # 3. Calculate Languages (detailed bytes if token or within rate limit)
    # If token present, fetch repo language bytes for top repositories
    # If unauthenticated, query language endpoints or aggregate repo primary languages safely
    query_detailed_languages = bool(token) or len(source_repos) <= 30
    languages_queried = False

    if query_detailed_languages:
        try:
            for repo in source_repos:
                lang_url = repo.get("languages_url")
                if lang_url:
                    repo_langs = make_request(lang_url, token)
                    for lang, b in repo_langs.items():
                        lang_bytes[lang] = lang_bytes.get(lang, 0) + b
            languages_queried = True
        except Exception as e:
            print(f"Notice: Detailed language query stopped ({e}), using primary fallback.", file=sys.stderr)

    if not languages_queried or not lang_bytes:
        # Fallback to repo primary language * size in KB (approximate bytes)
        for repo in source_repos:
            primary_lang = repo.get("language")
            size_kb = repo.get("size", 1)
            if primary_lang:
                lang_bytes[primary_lang] = lang_bytes.get(primary_lang, 0) + (size_kb * 1024)

    total_code_bytes = sum(lang_bytes.values())
    stats["languages"]["total_bytes"] = total_code_bytes
    stats["languages"]["breakdown"] = lang_bytes

    if total_code_bytes > 0:
        sorted_langs = sorted(lang_bytes.items(), key=lambda item: item[1], reverse=True)
        stats["languages"]["percentages"] = {
            lang: round((b / total_code_bytes) * 100, 2)
            for lang, b in sorted_langs
        }

    # 4. GraphQL Contributions Collection (if token is available)
    if token:
        graphql_query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              totalCommitContributions
              totalIssueContributions
              totalPullRequestContributions
              totalPullRequestReviewContributions
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                  }
                }
              }
            }
          }
        }
        """
        payload = json.dumps({"query": graphql_query, "variables": {"login": username}}).encode("utf-8")
        try:
            graphql_res = make_request("https://api.github.com/graphql", token, post_data=payload)
            user_data = graphql_res.get("data", {}).get("user", {})
            cc = user_data.get("contributionsCollection", {})
            cal = cc.get("contributionCalendar", {})

            stats["contributions"]["total_commits"] = cc.get("totalCommitContributions", 0)
            stats["contributions"]["total_issues"] = cc.get("totalIssueContributions", 0)
            stats["contributions"]["total_prs"] = cc.get("totalPullRequestContributions", 0)
            stats["contributions"]["total_reviews"] = cc.get("totalPullRequestReviewContributions", 0)
            stats["contributions"]["total_year"] = cal.get("totalContributions", 0)

            # Streak calculation
            all_days = []
            for week in cal.get("weeks", []):
                for day in week.get("contributionDays", []):
                    all_days.append(day)

            # Calculate current streak and longest streak
            current_streak = 0
            longest_streak = 0
            temp_streak = 0

            # Today's date check for current streak
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Longest streak scan
            for d in all_days:
                if d.get("contributionCount", 0) > 0:
                    temp_streak += 1
                    if temp_streak > longest_streak:
                        longest_streak = temp_streak
                else:
                    temp_streak = 0

            # Current streak scan (working backwards)
            active_streak = 0
            for d in reversed(all_days):
                count = d.get("contributionCount", 0)
                date_str = d.get("date", "")
                if count > 0:
                    active_streak += 1
                else:
                    # If today has 0 contributions, streak might still be active from yesterday
                    if date_str == today_str and active_streak == 0:
                        continue
                    break
            current_streak = active_streak

            stats["contributions"]["current_streak"] = current_streak
            stats["contributions"]["longest_streak"] = longest_streak
            stats["contributions"]["has_graphql_data"] = True
        except Exception as e:
            print(f"Notice: GraphQL contributions skipped ({e})", file=sys.stderr)

    return stats


def generate_overview_svg(stats: dict) -> str:
    """Generate SVG card for GitHub Overview Stats."""
    username = stats.get("username", "kunalsanga")
    user_name = stats.get("user", {}).get("name", username)
    repos = stats.get("repos", {})
    contribs = stats.get("contributions", {})
    updated = stats.get("fetched_at", "")[:10]

    stars = repos.get("total_stars", 0)
    public_repos = repos.get("total_public", 0)
    forks_count = repos.get("total_forks_count", 0)
    sources = repos.get("total_sources_owned", 0)
    
    total_contribs = contribs.get("total_year", 0)
    current_streak = contribs.get("current_streak", 0)
    longest_streak = contribs.get("longest_streak", 0)

    # If GraphQL contributions weren't fetched, provide verified repos & stars cleanly
    has_contrib = contribs.get("has_graphql_data", False)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="230" viewBox="0 0 480 230" fill="none" role="img" aria-label="{user_name} GitHub Overview Statistics">
  <title>{user_name} - GitHub Statistics</title>
  <style>
    .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
    .title {{ font: 600 18px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #58a6ff; }}
    .subtitle {{ font: 400 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .stat-label {{ font: 500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .stat-value {{ font: 700 20px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .stat-accent {{ fill: #fe428e; font-weight: 700; }}
    .stat-green {{ fill: #3fb950; font-weight: 700; }}
    .stat-blue {{ fill: #58a6ff; font-weight: 700; }}
    .stat-yellow {{ fill: #d29922; font-weight: 700; }}
    .divider {{ stroke: #21262d; stroke-width: 1px; }}
    .footer {{ font: 400 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #6e7681; }}
  </style>

  <!-- Card Background -->
  <rect width="480" height="230" class="bg"/>

  <!-- Header -->
  <g transform="translate(25, 32)">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" fill="#58a6ff"/>
    <text x="24" y="13" class="title">{username}</text>
    <text x="430" y="13" class="subtitle" text-anchor="end">GitHub Verified Data</text>
  </g>

  <line x1="25" y1="52" x2="455" y2="52" class="divider"/>

  <!-- Row 1: Repositories & Stars -->
  <g transform="translate(35, 82)">
    <text x="0" y="0" class="stat-label">Public Repositories</text>
    <text x="0" y="24" class="stat-value stat-blue">{public_repos} <tspan class="subtitle">({sources} original)</tspan></text>
  </g>

  <g transform="translate(255, 82)">
    <text x="0" y="0" class="stat-label">Total Stars Earned</text>
    <text x="0" y="24" class="stat-value stat-yellow">★ {format_number(stars)}</text>
  </g>

  <!-- Row 2: Contributions / Forks -->
  <g transform="translate(35, 142)">
    <text x="0" y="0" class="stat-label">{"Past Year Contributions" if has_contrib else "Repository Forks"}</text>
    <text x="0" y="24" class="stat-value stat-green">{"⚡ " + format_number(total_contribs) if has_contrib else "⑂ " + format_number(forks_count)}</text>
  </g>

  <g transform="translate(255, 142)">
    <text x="0" y="0" class="stat-label">{"Contribution Streaks" if has_contrib else "Open Issues"}</text>
    <text x="0" y="24" class="stat-value stat-accent">{"Current: " + str(current_streak) + "d | Max: " + str(longest_streak) + "d" if has_contrib else format_number(repos.get("total_open_issues", 0))}</text>
  </g>

  <line x1="25" y1="188" x2="455" y2="188" class="divider"/>

  <!-- Footer -->
  <text x="25" y="208" class="footer">✓ Automated GitHub Actions pipeline</text>
  <text x="455" y="208" class="footer" text-anchor="end">Refreshed: {updated} UTC</text>
</svg>"""
    return svg


def generate_language_svg(stats: dict) -> str:
    """Generate SVG card for verified language breakdown."""
    percentages = stats.get("languages", {}).get("percentages", {})
    breakdown = stats.get("languages", {}).get("breakdown", {})
    total_bytes = stats.get("languages", {}).get("total_bytes", 0)
    updated = stats.get("fetched_at", "")[:10]

    # Select top 6 languages
    top_langs = list(percentages.items())[:6]

    # Calculate bar segments
    bar_width = 430
    bar_segments = []
    current_x = 25
    for lang, pct in top_langs:
        seg_w = (pct / 100.0) * bar_width
        color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)
        bar_segments.append(
            f'<rect x="{current_x:.1f}" y="70" width="{seg_w:.1f}" height="10" rx="3" fill="{color}"/>'
        )
        current_x += seg_w

    # Render language list items (2 columns of 3)
    list_items = []
    for idx, (lang, pct) in enumerate(top_langs):
        color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR)
        col = idx % 2
        row = idx // 2
        x = 35 + (col * 220)
        y = 115 + (row * 28)
        bytes_str = format_bytes(breakdown.get(lang, 0))
        item = f"""
    <g transform="translate({x}, {y})">
      <circle cx="5" cy="5" r="5" fill="{color}"/>
      <text x="18" y="9" class="lang-name">{lang}</text>
      <text x="200" y="9" class="lang-pct" text-anchor="end">{pct}% <tspan class="lang-bytes">({bytes_str})</tspan></text>
    </g>"""
        list_items.append(item)

    items_markup = "\n".join(list_items)
    bars_markup = "\n  ".join(bar_segments)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="230" viewBox="0 0 480 230" fill="none" role="img" aria-label="Top Languages by Code Volume">
  <title>Top Languages - kunalsanga</title>
  <style>
    .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
    .title {{ font: 600 18px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #fe428e; }}
    .subtitle {{ font: 400 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .lang-name {{ font: 500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .lang-pct {{ font: 700 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #58a6ff; }}
    .lang-bytes {{ font: 400 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .divider {{ stroke: #21262d; stroke-width: 1px; }}
    .footer {{ font: 400 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #6e7681; }}
  </style>

  <!-- Card Background -->
  <rect width="480" height="230" class="bg"/>

  <!-- Header -->
  <g transform="translate(25, 32)">
    <text x="0" y="13" class="title">Top Languages</text>
    <text x="430" y="13" class="subtitle" text-anchor="end">By Byte Volume ({format_bytes(total_bytes)})</text>
  </g>

  <!-- Segmented Progress Bar -->
  <rect x="25" y="70" width="430" height="10" rx="4" fill="#21262d"/>
  {bars_markup}

  <!-- Language Grid -->
  {items_markup}

  <line x1="25" y1="188" x2="455" y2="188" class="divider"/>

  <!-- Footer -->
  <text x="25" y="208" class="footer">✓ Calculated from public source repositories</text>
  <text x="455" y="208" class="footer" text-anchor="end">Refreshed: {updated} UTC</text>
</svg>"""
    return svg


def validate_svg(svg_content: str) -> bool:
    """Validate that SVG markup is well-formed and closed."""
    s = svg_content.strip()
    if not s.startswith("<svg"):
        return False
    if not s.endswith("</svg>"):
        return False
    if not re.search(r'xmlns=["\']', s):
        return False
    if not re.search(r'viewBox=["\']', s, re.IGNORECASE):
        return False
    return True


def main():
    username = os.environ.get("GITHUB_ACTOR") or os.environ.get("GITHUB_USERNAME") or "kunalsanga"
    token = os.environ.get("GITHUB_TOKEN") or None

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "stats")
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "github_stats.json")
    overview_svg_path = os.path.join(output_dir, "overview_stats.svg")
    language_svg_path = os.path.join(output_dir, "language_stats.svg")
    timestamp_path = os.path.join(output_dir, "last_updated.txt")

    print(f"Collecting verified GitHub statistics for: {username} (Authenticated: {bool(token)})")

    stats = None
    try:
        stats = fetch_github_data(username, token)
        print(f"Data retrieved successfully: {stats['repos']['total_public']} public repos, {stats['repos']['total_stars']} stars.")
    except Exception as e:
        print(f"Warning during data fetch: {e}", file=sys.stderr)
        # Attempt fallback to existing JSON to avoid breaking assets
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                print(f"Preserving existing validated dataset from: {stats.get('fetched_at')}")
            except Exception as read_err:
                print(f"Could not read previous dataset: {read_err}", file=sys.stderr)

    if not stats or not stats.get("repos", {}).get("total_public", 0):
        print("Error: Could not retrieve valid statistics and no valid fallback exists.", file=sys.stderr)
        sys.exit(1)

    # Save normalized JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote validated statistics to: {json_path}")

    # Generate SVGs
    overview_svg = generate_overview_svg(stats)
    if validate_svg(overview_svg):
        with open(overview_svg_path, "w", encoding="utf-8") as f:
            f.write(overview_svg)
        print(f"Generated valid Overview SVG: {overview_svg_path}")
    else:
        print("Error: Generated Overview SVG failed validation", file=sys.stderr)
        sys.exit(1)

    language_svg = generate_language_svg(stats)
    if validate_svg(language_svg):
        with open(language_svg_path, "w", encoding="utf-8") as f:
            f.write(language_svg)
        print(f"Generated valid Language SVG: {language_svg_path}")
    else:
        print("Error: Generated Language SVG failed validation", file=sys.stderr)
        sys.exit(1)

    with open(timestamp_path, "w", encoding="utf-8") as f:
        f.write(stats.get("fetched_at", datetime.now(timezone.utc).isoformat()) + "\n")

    print("All statistics generated and validated successfully.")


if __name__ == "__main__":
    main()
