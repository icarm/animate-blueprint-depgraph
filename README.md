# Animate Blueprint Depgraph

Given a [Lean Blueprint](https://github.com/PatrickMassot/leanblueprint) project, makes an animation of the dependency graph.


[<img src="http://img.youtube.com/vi/tLHuVh7-G_8/maxresdefault.jpg" height="300px">](https://youtu.be/tLHuVh7-G_8)


## Usage

```shell
uv run main.py --repo-url https://github.com/thefundamentaltheor3m/Sphere-Packing-Lean
```

It usually takes many minutes to run. When it is done, the output will be an html file
in the `output/` directory.


## Known Limitations

* The project repo must be on Github.
* Does not work if the dependency graph has been broken into chapters.

