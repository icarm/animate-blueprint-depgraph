from playwright.sync_api import sync_playwright

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
    TARGET_URL = "http://localhost:8000/dep_graph_document.html"
    SVG_ID = "graph"
    OUTPUT_FILE = "downloaded_image.svg"

    save_svg_from_url(TARGET_URL, SVG_ID, OUTPUT_FILE)


if __name__ == "__main__":
    main()
