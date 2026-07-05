#!/usr/bin/env python3
"""Record the animated blueprint depgraph HTML page as an MP4 video."""

import argparse
import os
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="Record animated depgraph HTML as MP4")
    parser.add_argument("html_file", help="Path to the generated HTML file")
    parser.add_argument("-o", "--output", default="output.mp4", help="Output MP4 file path")
    parser.add_argument("--width", type=int, default=1920, help="Video width in pixels")
    parser.add_argument("--height", type=int, default=1080, help="Video height in pixels")
    args = parser.parse_args()

    html_path = os.path.abspath(args.html_file)
    if not os.path.isfile(html_path):
        print(f"Error: {html_path} not found")
        sys.exit(1)

    file_url = f"file://{html_path}"

    with tempfile.TemporaryDirectory() as tmpdir:
        webm_path = os.path.join(tmpdir, "recording.webm")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": args.width, "height": args.height},
                record_video_dir=tmpdir,
                record_video_size={"width": args.width, "height": args.height},
            )
            page = context.new_page()

            print(f"Opening {file_url} at {args.width}x{args.height}")
            page.goto(file_url)

            # Chromium's screencast only delivers video frames when the page
            # repaints, and the recording can only ever end on the last frame
            # that was actually delivered. Once the animation stops, the page
            # goes static and no more frames flow, so if Chromium fails to
            # deliver the final repaint the video ends mid-transition and the
            # linger below is lost. Keep an imperceptible animation running so
            # frames keep flowing until the recording is closed.
            page.evaluate(
                """() => {
                    const beacon = document.createElement('div');
                    beacon.style.cssText =
                        'position:fixed;top:0;left:0;width:2px;height:2px;' +
                        'background:#888;opacity:0.02;pointer-events:none;' +
                        'z-index:99999';
                    document.body.appendChild(beacon);
                    (function spin(t) {
                        beacon.style.transform = 'rotate(' + (t / 16) % 360 + 'deg)';
                        requestAnimationFrame(spin);
                    })(0);
                }"""
            )

            # Poll animation progress and display a progress bar
            total = page.evaluate("dots.length")
            bar_width = 40
            poll_ms = 250
            while True:
                current = page.evaluate("dotIndex")
                frac = current / total if total > 0 else 0
                filled = int(bar_width * frac)
                bar = "#" * filled + "-" * (bar_width - filled)
                print(f"\rRecording: [{bar}] {current}/{total} frames", end="", flush=True)
                if current >= total:
                    break
                page.wait_for_timeout(poll_ms)
            print()  # newline after progress bar

            # Let the final frame linger for a moment
            page.wait_for_timeout(2000)

            video_path = page.video.path()
            context.close()
            browser.close()

            # Convert WebM to MP4 with ffmpeg
            output_path = os.path.abspath(args.output)
            print(f"Converting to MP4: {output_path}")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    output_path,
                ],
                check=True,
            )

    print(f"Done! Video saved to {output_path}")


if __name__ == "__main__":
    main()
