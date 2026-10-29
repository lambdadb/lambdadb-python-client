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

## Branches and merges

`main` is the default branch and the only source of published releases.
`develop` is the integration branch.

1. Feature and fix work: branch from the current `develop`, open a pull request
   that targets `develop`, and merge it with **Squash and merge**. Select the
   base branch explicitly; GitHub defaults new pull requests to `main`.
2. Release branch: cut `release/X.Y.Z` from the reviewed `develop` commit.
   Commit release preparation (version sources, changelog, and release notes)
   and any RC fixes through pull requests into the release branch. `develop`
   keeps receiving feature work meanwhile; nothing merged into `develop` after
   the cut ships in this release. When there is nothing to stabilize, the
   release branch may be skipped and `develop` promoted directly.
3. Promotion: open a `release/X.Y.Z` -> `main` pull request (or `develop` ->
   `main` when the release branch is skipped) and merge it with **Create a
   merge commit**. Tag and publish only from the resulting reviewed `main` merge
   commit. Each RC repeats this: fix on the release branch, promote, and tag the
   next RC.
4. Back-merge: after every promotion and tag, open a `main` -> `develop` pull
   request and merge it with **Create a merge commit**. Back-merge `main`, not
   the release branch: only `main` carries the promotion merge commit and its
   tag, plus any hotfix or Dependabot change merged directly into `main`. Never
   squash or rebase a back-merge pull request: that makes the trees equal
   without shared ancestry, so later comparisons repeat merged commits and
   release tags become unreachable from `develop`. Resolve conflicts in the
   back-merge pull request, typically keeping `develop`'s newer content.
   Afterwards, this check must succeed:

   ```bash
   git merge-base --is-ancestor origin/main origin/develop
   ```

5. Hotfixes: cut `hotfix/X.Y.Z` from `main`, open a pull request into `main`,
   merge it with **Create a merge commit**, tag and publish from `main`, and
   then back-merge `main` into `develop` as in step 4.
6. Keep `release/X.Y.Z` through its RCs and delete it after the final stable
   promotion; delete `hotfix/*` after its merge. The CI workflow runs only for
   pull requests into `main` and `develop`, so run the repository checks in
   [docs/TESTING.md](docs/TESTING.md) locally for pull requests into
   `release/*` and `hotfix/*`.

Once lambdadb/lambdadb-iac#22 is applied, organization rulesets enforce part of
this flow: deletion and force pushes are blocked on `develop` and `main`, both
require pull requests, `develop` allows squash merges and merge commits but
blocks rebase merges, and `main` allows only merge commits. The rulesets have no
bypass actors and do not cover tags or `release/*` and `hotfix/*` branches.

## Development packages

Development packages are for internal testing and must not be uploaded to
production PyPI.

1. Set both version sources to the next unused development version, such as
   `0.10.0.dev1`.
2. Push the reviewed commit to an appropriate branch.
3. Run the **Build development package** workflow with the exact branch, tag,
   or commit as its `ref` input.
4. Download the wheel artifact whose name includes both the package version and
   commit SHA.
5. Install that exact wheel in the target environment:

   ```bash
   python -m pip install ./lambdadb-0.10.0.dev1-py3-none-any.whl
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
2. Cut `release/0.9.0` from the exact reviewed `develop` commit. Through a
   reviewed pull request into the release branch, set both version sources to
   the next RC, such as `0.9.0rc1`, and change the `CHANGELOG.md` Unreleased
   heading to that exact package version.
3. Merge a reviewed `release/0.9.0` -> `main` promotion pull request with
   **Create a merge commit** and record the exact merge commit.
4. After explicit publication approval, create tag `v0.9.0rc1` from that exact
   `main` commit. Never move an existing tag.
5. Create a GitHub Release whose name exactly matches the tag. Mark an RC as a
   prerelease and explicitly leave it out of the `latest` designation.
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

Because pip's `--pre` flag also enables prerelease dependency candidates, keep
the runtime dependency upper bounds in `pyproject.toml` aligned with the major
versions supported by the SDK. Validate both opt-in forms in clean
environments before publishing.

If an RC needs a fix, merge it into the release branch, increment the RC
number, and promote and tag again from `main`. Never move or replace an
existing tag or PyPI version.

After every promotion and tag, back-merge `main` (not the release branch) into
`develop` without rewriting the reviewed main ancestry, as described in
[Branches and merges](#branches-and-merges). Merge the `main` -> `develop` pull
request with **Create a merge commit**; do not squash or rebase the back-merge
PR. Verify:

```bash
git merge-base --is-ancestor origin/main origin/develop
```

## Stable releases

Publish the matching stable version only after the release candidate is
accepted and all feedback is resolved.

1. On the release branch, set both version sources to the stable version, such
   as `0.9.0`.
2. Update the release notes and user-facing documentation on the release
   branch.
3. Run the complete validation checklist.
4. Merge a reviewed `release/0.9.0` -> `main` promotion pull request with
   **Create a merge commit**.
5. Create tag `v0.9.0` from that exact `main` merge commit.
6. Create a non-prerelease GitHub Release for the tag.
7. Verify the PyPI package and a clean installation.
8. Back-merge `main` into `develop` as described in
   [Branches and merges](#branches-and-merges), and delete the release branch.

## Validation checklist

Before publishing an RC or stable release:

- Pin and record the API contract revision used for the SDK.
- Confirm the target API is deployed in the intended test environment.
- Confirm the Git tag, GitHub Release name, `CHANGELOG.md` heading,
  `pyproject.toml`, and runtime SDK version agree.
- Confirm the version uses canonical `X.Y.ZrcN` or `X.Y.Z` syntax. Epoch,
  abbreviated, alpha/beta, post, and local versions are not release channels.
- Confirm an exact RC install and a `--pre` RC install both import successfully,
  while an install without either opt-in still selects the stable release.
- Confirm the release commit belongs to `main`.
- Run non-integration tests on Python 3.10, 3.11, 3.12, and 3.13.
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
  versions outside exact `X.Y.ZrcN` / `X.Y.Z` channels, mismatched release
  names or changelog headings, incorrect GitHub prerelease flags, and release
  commits outside `main`.
- The production publish job uses PyPI Trusted Publishing with a short-lived
  OIDC credential.
- `scripts/publish.sh` intentionally refuses direct token-based publishing.

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
