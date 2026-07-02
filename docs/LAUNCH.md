# PyPI launch checklist

## Pre-publish

- [ ] `uv run pytest` and `uv run black --check .` pass
- [ ] CI `install-base` job passes (wheel install without `[aws]`)
- [ ] `uv build` and smoke-test the wheel in a clean venv
- [ ] README, CHANGELOG, and version in `pyproject.toml` agree
- [ ] Git tag `v0.3.0` matches `pyproject.toml` version

## Install smoke tests

```bash
# Offline core (no AWS)
pip install dist/orchflow-*.whl
python -c "from orchflow import markdown_sections, __version__; print(__version__)"
orchflow eval tests/fixtures/simple/good.md

# Live Bedrock
pip install "dist/orchflow-*.whl[aws]"
orchflow run --example simple
```

## Publish

```bash
uv build
uv publish
```

## Post-publish

- [ ] Verify PyPI page renders README and license
- [ ] `pip install orchflow` from PyPI in a fresh environment
- [ ] GitHub release notes link to CHANGELOG
