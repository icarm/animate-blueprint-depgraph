# Animate Blueprint Depgraph

Given a [Lean Blueprint](https://github.com/PatrickMassot/leanblueprint) project, makes an animation of the dependency graph.


[<img src="http://img.youtube.com/vi/tLHuVh7-G_8/maxresdefault.jpg" height="300px">](https://youtu.be/tLHuVh7-G_8)


## Usage

```shell
uv run main.py --repo-url https://github.com/thefundamentaltheor3m/Sphere-Packing-Lean
```

It usually takes many minutes to run. When it is done, the output will be an html file
in the `output/` directory.


## Recording as MP4

To turn the generated HTML animation into an MP4 video, use `record_video.py`.
This requires [Playwright](https://playwright.dev/python/) and `ffmpeg`.

```shell
# One-time setup: install the Chromium browser for Playwright
uv run playwright install chromium

# Record the animation at 1920x1080
uv run python record_video.py output/Sphere-Packing-Lean.html -o output/Sphere-Packing-Lean.mp4 --width 1920 --height 1080
```

Options:
- `--width` / `--height` — video resolution (default: 1920x1080)

## Known Limitations

* The project repo must be on Github.
* Does not work if the dependency graph has been broken into chapters.

