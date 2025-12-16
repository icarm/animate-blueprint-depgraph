import requests
import os

# CONFIGURATION
OWNER = "jcreedcmu"  # Repository Owner
REPO = "Noperthedron"       # Repository Name
BRANCH = "main"       # Branch to analyze
# Ideally, store this in an environment variable: export GITHUB_TOKEN="your_token"
TOKEN = os.getenv("GITHUB_TOKEN")

def get_headers():
    """Construct headers with authentication to increase rate limits."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    else:
        print("WARNING: No GITHUB_TOKEN found. Rate limits will be very low (60 req/hr).")
    return headers

def fetch_all_commits(owner, repo, branch):
    """
    Fetches all commits from the repo using pagination.
    Returns a list of commit objects (metadata).
    """
    commits = []
    page = 1
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    print(f"Fetching commits for {owner}/{repo} on branch '{branch}'...")

    while True:
        params = {
            "sha": branch,
            "per_page": 100, # Max allowed per page
            "page": page
        }

        response = requests.get(url, headers=get_headers(), params=params)

        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

        batch = response.json()

        if not batch:
            break

        commits.extend(batch)
        print(f"Fetched {len(commits)} commits so far...")

        if len(batch) < 100:
            break # End of list

        page += 1

    return commits

def analyze_contributors_history(commits):
    """
    Iterates through commits chronologically to build cumulative contributor lists.
    """
    # The API returns commits in Reverse Chronological order (Newest first).
    # We flip it to start from the first commit ever.
    chronological_commits = commits[::-1]

    history_data = []

    # We use a dictionary to keep unique contributors based on their ID or Name
    seen_contributors = {}

    print("\nProcessing revision history...")

    for commit_obj in chronological_commits:
        sha = commit_obj['sha']
        author_info = commit_obj.get('author')
        commit_meta = commit_obj.get('commit', {}).get('author', {})

        contributor_entry = None
        contributor_id = None

        # Case 1: The user is linked to a valid GitHub account
        if author_info:
            contributor_id = author_info['id']
            contributor_entry = {
                "type": "github_user",
                "login": author_info['login'],
                "avatar_url": author_info['avatar_url'],
                "html_url": author_info['html_url']
            }

        # Case 2: No GitHub account linked (Git email doesn't match a GitHub user)
        # We fall back to the Git Name/Email
        else:
            contributor_id = commit_meta.get('email')
            contributor_entry = {
                "type": "git_user",
                "login": commit_meta.get('name'), # Use Git Name as login display
                "avatar_url": None, # Cannot get avatar without GitHub account
                "html_url": None
            }

        # Add to our unique set of contributors
        if contributor_id and contributor_id not in seen_contributors:
            seen_contributors[contributor_id] = contributor_entry

        # Store the state of contributors at this specific commit SHA
        history_data.append({
            "commit_sha": sha,
            "date": commit_meta.get('date'),
            "contributor_count": len(seen_contributors),
            "contributors": list(seen_contributors.values())
        })

    return history_data

# --- MAIN EXECUTION ---
try:
    # 1. Get raw data
    raw_commits = fetch_all_commits(OWNER, REPO, BRANCH)

    # 2. Process data
    revision_history = analyze_contributors_history(raw_commits)

    # 3. Output Example (Printing the last 3 revisions)
    print(f"\nAnalysis Complete. Total revisions processed: {len(revision_history)}")

    for revision in revision_history:
        print(f"Commit: {revision['commit_sha'][:7]} | Date: {revision['date']}")
        print(f"Total Contributors up to this point: {revision['contributor_count']}")
        display_contributors = [c['login'] for c in revision['contributors']]
        print(f"Contributors: {display_contributors}...")
        print("-" * 40)

except Exception as e:
    print(f"Error: {e}")
