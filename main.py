import argparse
from datetime import datetime
import os
import re
import shlex
import subprocess
import time

from git import Repo

def get_depgraph(repo_path, commit_id):
    target_dir = os.path.expanduser(repo_path)

    # hack to get `uv run` to work in a subprocess in a different directory
    subprocess_env = os.environ.copy()
    subprocess_env.pop("VIRTUAL_ENV", None)
    subprocess_env.pop("UV_PROJECT_ENVIRONMENT", None)

    subprocess_env["PYTHONUNBUFFERED"] = "1"

    sequential_commands = [
        "git checkout {}".format(commit_id),
 #       "lake exe cache get",
 #       "lake build",
        "uv run leanblueprint web",
#        "uv run leanblueprint pdf",
    ]

    print("--- Starting Sequential Phase ---")
    for cmd in sequential_commands:
        try:
            print(f"Running: {cmd}")
            args = shlex.split(cmd)
            subprocess.run(args, check=True, cwd=target_dir, env=subprocess_env, stdin=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"Error running command '{cmd}': {e}")
            return None

    dg_filename = os.path.join(target_dir, "blueprint", "web", "dep_graph_document.html")

    with open(dg_filename, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"\.renderDot\(`(.*?)`"
    matches = re.findall(pattern, content, re.DOTALL)
    if len(matches) == 0:
        print("no match!")
        return None
    elif len(matches) > 1:
        print("too many matches!")

    dot = matches[0]
    print(dot)
    return dot

def list_commits_chronologically(repo_path, rev, start_date_str):
    try:
        # Initialize the repository object
        repo = Repo(repo_path)

        # check if the repo is empty
        if repo.bare:
            print(f"The repository at {repo_path} is bare.")
            return None

        # repo.iter_commits() defaults to 'master' (or current HEAD)
        # and iterates backwards (newest -> oldest).
        # We wrap it in list() and use reversed() to go Oldest -> Newest.
        commits = list(repo.iter_commits(rev=rev, paths="blueprint", since=start_date_str))
        commits.reverse() # In-place reversal is slightly more memory efficient than reversed()

        print(f"Iterating {len(commits)} commits chronologically:\n")

        result = []
        for commit in commits:
            result.append(commit.hexsha[:10])
            # Convert unix timestamp to a readable date
            commit_date = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')

            print(f"Commit: {commit.hexsha[:7]}")
            print(f"Author: {commit.author.name} <{commit.author.email}>")
            print(f"Date:   {commit_date}")
            print(f"Message: {commit.message.strip()}")
            print("-" * 40)

        return result

    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Serve blueprint and save SVG")
    parser.add_argument("--url", type=str, default="http://localhost:8000/dep_graph_document.html", help="URL to fetch the SVG from")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--repo-path", type=str, default="~/src/NegativeRupert", help="Path to the git repository to list commits from")
    parser.add_argument("--rev", type=str, default="main", help="Git revision to list commits from")
    parser.add_argument("--start-date", type=str, default="1970-01-01", help="Start date for listing commits (YYYY-MM-DD)")
    args = parser.parse_args()

    output_directory = os.path.expanduser(args.output)
    os.makedirs(output_directory, exist_ok=True)

    commits = list_commits_chronologically(args.repo_path, args.rev, args.start_date)

    ii = 0
    for commit_id in commits:
        print("commit ID:", commit_id)
        dot = get_depgraph(args.repo_path, commit_id)

        #output_filename = os.path.join(output_directory, "downloaded_image{:05}.svg".format(ii))
        #save_svg_from_url("{}/dep_graph_document.html".format(url_prefix), args.element_id, output_filename)
        ii += 1


if __name__ == "__main__":
    main()
