import argparse
from datetime import datetime
import os
import re
import shlex
import subprocess
import time

from git import Repo
from playwright.sync_api import sync_playwright


def serve_blueprint(repo_path, commit_id):
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

    background_cmd_str = 'uv run leanblueprint serve'

    print("--- Starting Sequential Phase ---")
    for cmd in sequential_commands:
        try:
            print(f"Running: {cmd}")
            args = shlex.split(cmd)
            subprocess.run(args, check=True, cwd=target_dir, env=subprocess_env, stdin=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"Error running command '{cmd}': {e}")
            return None, ""

    # --- PHASE 2: Background Command ---
    print("\n--- Starting Background Phase ---")

    # shlex.split parses the string into a list safe for subprocess (better than shell=True)
    # e.g. "ls -l" becomes ["ls", "-l"]
    bg_args = shlex.split(background_cmd_str)

    # Popen starts the process but does NOT wait for it to finish
    proc_handle = subprocess.Popen(bg_args, cwd=target_dir, env=subprocess_env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   bufsize=1 )

    detected_url = None
    # Loop to read stdout line by line until we find the URL
    while True:
        # Check if process exited unexpectedly
        if proc_handle.poll() is not None:
            print("Background process exited prematurely.")
            return None, ""

        # Read a line
        print("reading line...")
        line = proc_handle.stdout.readline()
        if not line:
            break
        print("line read!")

        if line.strip() == "Could not find an available port.":
            print('failed to get port. sleeping and trying again...')
            time.sleep(20)
            print("trying again...")
            # Popen starts the process but does NOT wait for it to finish
            proc_handle = subprocess.Popen(bg_args, cwd=target_dir, env=subprocess_env, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           text=True,
                                           bufsize=1 )

            continue

        # Print the line to your console so you can still see what's happening
        print(f"[SERVER] {line.strip()}")

        # Regex to look for "Serving http://..."
        # Matches "Serving http://0.0.0.0:8001/" or similar
        match = re.search(r"Serving\s+(http://[\w\d\.:]+)", line)
        if match:
            detected_url = match.group(1)

            # Fix 0.0.0.0 -> localhost for Playwright compatibility
            if "0.0.0.0" in detected_url:
                detected_url = detected_url.replace("0.0.0.0", "localhost")

            print(f"--- Detected Server URL: {detected_url} ---")
            break

    if not detected_url:
        raise Exception("failed to detect server url")
    return proc_handle, detected_url


# element_id is the ID of the enclosing div.
def save_svg_from_url(url, element_id, output_filename):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"Visiting {url}...")
        page.goto(url)

        # 3. Wait for the SVG to be present in the DOM
        # (This ensures JS has finished rendering the element)
        selector = f"#{element_id} svg"
        try:
            page.wait_for_selector(selector, state="attached", timeout=10000)
        except Exception as e:
            print(f"Error: Could not find element with ID '{element_id}'")
            browser.close()
            return

        # 4. Get the SVG element.
        svg_locator = page.locator(selector).first

        # 5. Extract the outerHTML (the full <svg>...</svg> string)
        # We use evaluate to run a tiny JS snippet inside the browser
        svg_content = svg_locator.evaluate("el => el.outerHTML")

        # 6. Clean/Validate the SVG for standalone use
        # Standalone SVGs require the xmlns namespace, usually present,
        # but we check to be safe.
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg_content:
            svg_content = svg_content.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)

        # 7. Save to file
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print(f"Successfully saved SVG to {output_filename}")
        browser.close()

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
    parser.add_argument("--element-id", type=str, default="graph", help="ID of the enclosing div containing the SVG")
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
        child, url_prefix = serve_blueprint(args.repo_path, commit_id)
        if child is None:
            print("ignoring this one")
            continue

        output_filename = os.path.join(output_directory, "downloaded_image{:05}.svg".format(ii))
        save_svg_from_url("{}/dep_graph_document.html".format(url_prefix), args.element_id, output_filename)
        ii += 1

        child.terminate()
        child.wait()


if __name__ == "__main__":
    main()
