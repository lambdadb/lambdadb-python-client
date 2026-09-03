# Releasing the Python SDK

This document defines the required packaging and release process for the
`lambdadb` Python package.

PyPI is the distribution channel. Git tags and GitHub Releases initiate the
production publishing workflow, but a package is available to pip only after it
has been uploaded to PyPI.

## Version sources

Every build must use the same canonical PEP 440 version in both locations:

- `project.version` in `pyproject.toml`
- `SDK_VERSION` in `src/lambdadb/version.py`

The workflows reject mismatched versions. Release tags add a leading `v` to the
same package version.

| Channel | Package version | Git tag | Destination |
| :-- | :-- | :-- | :-- |
| Development | `X.Y.Z.devN` | None | GitHub Actions artifact |
| Release candidate | `X.Y.ZrcN` | `vX.Y.ZrcN` | Production PyPI |
| Stable | `X.Y.Z` | `vX.Y.Z` | Production PyPI |

Use the canonical Python spelling `0.9.0rc1`, not the Go-style
`0.9.0-rc.1`. Packaging tools may normalize the latter, but the workflows
require canonical input.

## Development packages

Development packages are for internal testing and must not be uploaded to
production PyPI.

1. Set both version sources to the next unused development version, such as
   `0.9.0.dev1`.
2. Push the reviewed commit to an appropriate branch.
3. Run the **Build development package** workflow with the exact branch, tag,
   or commit as its `ref` input.
4. Download the wheel artifact whose name includes both the package version and
   commit SHA.
5. Install that exact wheel in the target environment:

   ```bash
   python -m pip install ./lambdadb-0.9.0.dev1-py3-none-any.whl
   ```

6. Record the workflow run, commit SHA, package version, and test environment in
   the validation result.

Increment the development number for a new published artifact identity. Do not
reuse a version for different contents.

## Release candidates

Release candidates provide an explicit opt-in preview through production PyPI.
pip excludes prereleases from normal selection by default, so an existing
stable installation does not upgrade to an RC unless the consumer opts in.

1. Complete development and environment smoke tests.
2. Set both version sources to the next RC, such as `0.9.0rc1`.
3. Merge the reviewed release commit into `main`.
4. Create tag `v0.9.0rc1` from that exact `main` commit.
5. Create a GitHub Release for the tag and mark it as a prerelease.
6. Wait for the **Publish to PyPI** workflow to validate, test, build, and
   publish the package.
7. Verify the explicit RC installation in a clean environment:

   ```bash
   python -m pip install --no-cache-dir "lambdadb==0.9.0rc1"
   ```

8. Verify a normal installation still selects the current stable version:

   ```bash
   python -m pip index versions lambdadb
   ```

Consumers may opt in with an exact version or `--pre`:

```bash
python -m pip install "lambdadb==0.9.0rc1"
python -m pip install --pre --upgrade lambdadb
```

If an RC needs a fix, publish a new commit and increment the RC number. Never
move or replace an existing tag or PyPI version.

## Stable releases

Publish the matching stable version only after the release candidate is
accepted and all feedback is resolved.

1. Set both version sources to the stable version, such as `0.9.0`.
2. Update the release notes and user-facing documentation.
3. Run the complete validation checklist.
4. Merge the reviewed release commit into `main`.
5. Create tag `v0.9.0` from that exact commit.
6. Create a non-prerelease GitHub Release for the tag.
7. Verify the PyPI package and a clean installation.

## Validation checklist

Before publishing an RC or stable release:

- Pin and record the API contract revision used for the SDK.
- Confirm the target API is deployed in the intended test environment.
- Confirm the Git tag, `pyproject.toml`, and runtime SDK version agree.
- Confirm the version uses canonical PEP 440 syntax.
- Confirm the release commit belongs to `main`.
- Run non-integration tests on Python 3.9, 3.10, 3.11, 3.12, and 3.13.
- Build both the wheel and source distribution.
- Run `twine check` on all distributions.
- Install the built wheel and verify imports and the runtime version.
- Complete applicable live and third-party integration smoke tests.
- Review generated release notes before publishing the GitHub Release.

See [docs/TESTING.md](docs/TESTING.md) for local and integration test commands.

## Workflow boundaries

- `.github/workflows/dev-package.yaml` is the only workflow for development
  artifacts. It requires an `X.Y.Z.devN` version and never receives PyPI
  credentials.
- `.github/workflows/publish.yaml` runs only for a published GitHub Release. It
  rejects development versions, non-canonical versions, version mismatches,
  incorrect GitHub prerelease flags, and release commits outside `main`.
- The production publish job uses PyPI Trusted Publishing with a short-lived
  OIDC credential.

For additional administrative protection, configure a protected GitHub
Environment for production PyPI publishing and update the PyPI Trusted
Publisher configuration to require the same environment. Coordinate those two
external changes before adding `environment:` to the workflow; changing only
one side will break publishing.

## Failed releases

PyPI does not allow replacing files for an existing project version. If a
release is broken, publish the next RC or patch version. Yank a release only
when necessary, such as for an installation failure, a compatibility violation,
or a security issue. Yanking is an external, user-visible action and requires
explicit approval.

## References

- [Python version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)
- [pip prerelease behavior](https://pip.pypa.io/en/stable/cli/pip_install/#pre-release-versions)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI yanking](https://docs.pypi.org/project-management/yanking/)
