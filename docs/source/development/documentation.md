# Documentation

Install docs depends:

```bash
uv sync --dev
```

Auto build and serve:

```bash
cd docs
uv run sphinx-autobuild source/ build/
```

Or build manually:

```bash
cd docs
uv run sphinx-build source/ build/
```

And serve manually:

```bash
uv run python -m http.server 8000 -d build
```

Open <http://localhost:8000> in your browser.
