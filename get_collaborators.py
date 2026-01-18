import requests
import os

# CONFIGURATION
OWNER = "jcreedcmu"
REPO = "Noperthedron"
BRANCH = "main"
TOKEN = os.getenv("GITHUB_TOKEN")

def run_graphql_query(query, variables):
    """Executes a GraphQL query against the GitHub API."""
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"bearer {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Query failed: {response.status_code} - {response.text}")

    json_data = response.json()
    if 'errors' in json_data:
        raise Exception(f"GraphQL Errors: {json_data['errors']}")

    return json_data

def fetch_history_graphql(owner, repo, branch):
    """
    Fetches commit history including pre-resolved co-authors using GraphQL.
    """
    print(f"Fetching commit history for {owner}/{repo} on '{branch}' via GraphQL...")

    query = """
    query($owner: String!, $name: String!, $branch: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        ref(qualifiedName: $branch) {
          target {
            ... on Commit {
              history(first: 100, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  oid
                  committedDate
                  # 'authors' includes the main author AND co-authors
                  authors(first: 10) {
                    nodes {
                      name
                      email
                      user {
                        login
                        avatarUrl
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    commits = []
    cursor = None
    has_next = True

    # Ensure branch name is fully qualified for the API
    qualified_branch = branch if branch.startswith("refs/") else f"refs/heads/{branch}"

    while has_next:
        variables = {
            "owner": owner,
            "name": repo,
            "branch": qualified_branch,
            "cursor": cursor
        }

        data = run_graphql_query(query, variables)

        repo_data = data.get('data', {}).get('repository')
        if not repo_data or not repo_data.get('ref'):
            print("Error: Repository or Branch not found.")
            break

        history = repo_data['ref']['target']['history']
        batch = history['nodes']
        commits.extend(batch)

        print(f"Fetched {len(commits)} commits so far...")

        page_info = history['pageInfo']
        has_next = page_info['hasNextPage']
        cursor = page_info['endCursor']

    return commits

def analyze_contributors_history(commits):
    """
    Iterates through commits chronologically.
    The GraphQL data is already structured with resolved users.
    """
    # GraphQL returns newest first, reverse for chronological order
    chronological_commits = commits[::-1]

    history_data = []
    seen_contributors = {}

    print("\nProcessing revision history...")

    for commit in chronological_commits:
        sha = commit['oid']
        date = commit['committedDate']

        # The 'authors' list from GraphQL contains both Main Author + Co-Authors
        author_nodes = commit['authors']['nodes']

        for actor in author_nodes:
            # Check if this Git actor is linked to a GitHub User
            gh_user = actor.get('user')

            if gh_user:
                # We have a valid GitHub account
                contributor_id = gh_user['login']
                contributor_entry = {
                    "type": "github_user",
                    "login": gh_user['login'],
                    "avatar_url": gh_user['avatarUrl'], # CamelCase from GraphQL
                    "html_url": gh_user['url']
                }
            else:
                # No GitHub account linked (or user not resolved)
                contributor_id = actor['email']
                contributor_entry = {
                    "type": "git_user",
                    "login": actor['name'],
                    "avatar_url": None,
                    "html_url": None
                }

            # Add to cumulative list
            if contributor_id not in seen_contributors:
                seen_contributors[contributor_id] = contributor_entry

        # Snapshot state
        history_data.append({
            "commit_sha": sha,
            "date": date,
            "contributor_count": len(seen_contributors),
            "contributors": list(seen_contributors.values())
        })

    return history_data

def get_revision_history(owner, repo, branch="main"):
    """
    Main entry point: fetches raw data via GraphQL and processes it.
    Returns a list of dicts (chronological order).
    """
    raw_commits = fetch_history_graphql(owner, repo, branch)
    return analyze_contributors_history(raw_commits)

def get_revision_history_by_hash(owner, repo, branch="main"):
    """
    Wrapper to return a dictionary keyed by commit SHA.
    """
    revision_history = get_revision_history(owner, repo, branch)
    result = {}
    for rev in revision_history:
        result[rev['commit_sha']] = rev
    return result

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN is required for GraphQL API calls.")
        exit(1)

    try:
        # Use the wrapper function to test
        revision_history = get_revision_history(OWNER, REPO, BRANCH)

        if revision_history:
            latest = revision_history[-1]
            print(f"\n--- Analysis Complete (SHA: {latest['commit_sha'][:7]}) ---")
            print(f"Total Contributors: {latest['contributor_count']}")
            print("Contributors:")
            for c in latest['contributors']:
                type_label = "[GitHub]" if c['type'] == 'github_user' else "[Git]"
                avatar = c['avatar_url'] if c['avatar_url'] else "(No Avatar)"
                print(f" {type_label:8} {c['login']:<20} {avatar}")

    except Exception as e:
        print(f"Error: {e}")
