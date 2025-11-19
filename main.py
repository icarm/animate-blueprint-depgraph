import os
import shlex
import subprocess
from playwright.sync_api import sync_playwright


def serve_blueprint():
    target_dir = os.path.join(os.path.expanduser("~"), "src", "NegativeRupert")

    # hack to get `uv run` to work in a subprocess in a different directory
    subprocess_env = os.environ.copy()
    subprocess_env.pop("VIRTUAL_ENV", None)
    subprocess_env.pop("UV_PROJECT_ENVIRONMENT", None)

    sequential_commands = [
        "lake exe cache get",
        "lake build",
        "uv run leanblueprint all"
    ]

    background_cmd_str = 'uv run leanblueprint serve'

    print("--- Starting Sequential Phase ---")
    for cmd in sequential_commands:
        try:
            print(f"Running: {cmd}")
            args = shlex.split(cmd)
            subprocess.run(args, check=True, cwd=target_dir, env=subprocess_env)
        except subprocess.CalledProcessError as e:
            print(f"Error running command '{cmd}': {e}")
            return

    # --- PHASE 2: Background Command ---
    print("\n--- Starting Background Phase ---")

    # shlex.split parses the string into a list safe for subprocess (better than shell=True)
    # e.g. "ls -l" becomes ["ls", "-l"]
    bg_args = shlex.split(background_cmd_str)

    # Popen starts the process but does NOT wait for it to finish
    proc_handle = subprocess.Popen(bg_args, cwd=target_dir, env=subprocess_env)

    return proc_handle

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

def main():

    child = serve_blueprint()
    if child is None:
        return

    TARGET_URL = "http://localhost:8000/dep_graph_document.html"
    SVG_ID = "graph"
    OUTPUT_FILE = "downloaded_image.svg"

    save_svg_from_url(TARGET_URL, SVG_ID, OUTPUT_FILE)

    child.terminate()
    child.wait()
    print("child exited")


if __name__ == "__main__":
    main()
