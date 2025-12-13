import argparse
from datetime import datetime
import os
import re
import shlex
import subprocess
import time

from git import Repo
import pydot

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


OUTPUT_HEADER="""
<!DOCTYPE html>
<meta charset="utf-8">
<body>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://unpkg.com/@hpcc-js/wasm@2.20.0/dist/graphviz.umd.js"></script>
<script src="https://unpkg.com/d3-graphviz@5.6.0/build/d3-graphviz.js"></script>
<div id="graph" style="text-align: center;"></div>
<script>

var dotIndex = 0;
var graphviz = d3.select("#graph").graphviz()
    .transition(function () {
        return d3.transition("main")
            .ease(d3.easeLinear)
            .delay(500)
            .duration(1500);
    })
    .logEvents(true)
    .on("initEnd", render);

function render() {
    var dotLines = dots[dotIndex];
    var dot = dotLines.join('');
    graphviz
        .renderDot(dot)
        .on("end", function () {
            dotIndex = (dotIndex + 1) % dots.length;
            render();
        });
}

var dots = [
"""

def construct_html(dots, outfile):
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(OUTPUT_HEADER)
        for dot in dots:
            f.write("[`")
            f.write(dot)
            f.write("`],\n")
        f.write("];\n")
        f.write("</script>\n")

def fix_up_dot(dot):
    graphs = pydot.graph_from_dot_data(dot)
    original_g = graphs[0]

    # 2. Create a new graph with the same properties (type, name, strictness)
    # strict=True means duplicate edges are not allowed
    new_g = pydot.Dot(
        graph_name=original_g.get_name(),
        graph_type=original_g.get_type(),
        strict=original_g.get_strict()
    )

    # 3. Copy top-level graph attributes (e.g., rankdir, bgcolor)
    # original_g.get_attributes() returns a dictionary of attributes
    for key, value in original_g.get_attributes().items():
        new_g.set(key, value)

    # 4. Get all explicit nodes, sort them by name, and add them to the new graph
    # Note: get_nodes() returns a list of pydot.Node objects
    nodes = original_g.get_nodes()
    # We sort by the node's name. We strip quotes to ensure '"a"' sorts with 'a' correctly if needed.
    nodes.sort(key=lambda x: x.get_name().strip('"'))

    for node in nodes:
        # We allow pydot to handle the object copy/reference
        new_g.add_node(node)

    # 5. Copy over existing edges (order usually preserved from input)
    for edge in original_g.get_edges():
        new_g.add_edge(edge)

    # 6. Copy over subgraphs (optional, but good practice to preserve structure)
    for subgraph in original_g.get_subgraphs():
        new_g.add_subgraph(subgraph)

    print(new_g.to_string())
    return new_g.to_string()


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

    dots = []
    ii = 0
    for commit_id in commits:
        print("commit ID:", commit_id)
        dot = get_depgraph(args.repo_path, commit_id)
        if dot:
            dot = fix_up_dot(dot)
            if len(dots) > 0 and dots[-1] == dot:
                pass
            else:
                dots.append(dot)
        ii += 1

    construct_html(dots, "/Users/dwrensha/Desktop/out.html")

if __name__ == "__main__":
    main()
