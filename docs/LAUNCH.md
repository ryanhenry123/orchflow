# PyPI launch checklist

## One-time setup (trusted publishing)

No PyPI API tokens in GitHub secrets — uploads use OIDC.

### 1. GitHub environment

In [github.com/ryanhenry123/bedrockflow/settings/environments](https://github.com/ryanhenry123/bedrockflow/settings/environments):

1. Create environment **`pypi`**
2. (Optional) Add required reviewers for production deploys

### 2. PyPI trusted publisher

After the first manual upload *or* via **Pending publishers** before the project exists:

1. [pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/) (pending)
   **or** project → **Publishing** (existing project)
2. Add publisher → **GitHub**
3. Set:

| Field | Value |
|-------|-------|
| PyPI project name | `bedrockflow` |
| Owner | `ryanhenry123` |
| Repository | `bedrockflow` |
| Workflow name | `publish-pypi.yml` |
| Environment | `pypi` |

Save. The workflow filename must match exactly: `.github/workflows/publish-pypi.yml`.

Docs: [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/), [uv publish guide](https://docs.astral.sh/uv/guides/publish/).

---

## Pre-release

- [ ] `uv run pytest` and `uv run black --check .` pass
- [ ] CI green on `main`
- [ ] README, CHANGELOG, and `version` in `pyproject.toml` agree
- [ ] Tag will be `vX.Y.Z` matching `pyproject.toml` (e.g. `v0.3.0`)

Local wheel smoke test:

```bash
uv build
uv venv /tmp/bf-test && uv pip install --python /tmp/bf-test/bin/python dist/bedrockflow-*.whl
/tmp/bf-test/bin/bedrockflow eval tests/fixtures/simple/good.md \
  --panel bedrockflow.examples.simple_evals:SIMPLE_EVALS
```

---

## Release (automated)

Push a version tag — CI publishes to PyPI:

```bash
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

Watch **Actions → publish-pypi**. On success:

- [https://pypi.org/project/bedrockflow/](https://pypi.org/project/bedrockflow/)
- `pip install bedrockflow`

Create a GitHub Release from the tag and paste the matching [CHANGELOG](../CHANGELOG.md) section.

---

## Manual publish (fallback)

If you need to upload from your machine instead of CI:

```bash
export UV_PUBLISH_TOKEN=pypi-...
uv build
uv publish
```

Prefer the tag workflow once trusted publishing is configured.

---

## Post-release

- [ ] PyPI page renders README and license
- [ ] `pip install bedrockflow` in a fresh venv
- [ ] `pip install "bedrockflow[aws]"` for Bedrock extras
- [ ] GitHub Release notes link to CHANGELOG
