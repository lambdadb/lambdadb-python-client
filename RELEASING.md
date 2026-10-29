# Releasing the Python SDK

This document defines the required packaging and release process for the
`lambdadb` Python package.

PyPI is the distribution channel. Releases are trunk-based: `main` is the only
long-lived branch. A push to `main` whose RC or stable version is not tagged yet
is verified without publication, and a published GitHub Release for that version
publishes it to PyPI. Development builds are GitHub Actions artifacts only;
nothing publishes development versions to PyPI automatically.

Every `main` push and Release also runs the deployed
[live smoke gate](#deployed-live-smoke-gate): development pushes against the dev
environment, release verification and Releases against production.

## Branches

- Branch from `main`, open a pull request into `main`, and merge it with
  **Squash and merge**. The organization ruleset `protect-main` requires a pull
  request with one approval (the `dev` team may bypass the approval) and blocks
  deletion and force pushes.
- There are no `develop`, release, or hotfix branches. Maintenance releases are
  cut from `main`; anything merged into `main` ships in the next release.

## Version sources

Every build must use the same canonical PEP 440 version in both locations:

- `project.version` in `pyproject.toml`
- `SDK_VERSION` in `src/lambdadb/version.py`

The workflows reject mismatched versions. Release tags add a leading `v` to the
same package version.

The committed version is always an RC or stable version: the most recently
released one, whose tag `v<version>` exists, or the next one set by a merged
release pull request that is not tagged yet. Only a release pull request changes
it, and that exact merge commit is tagged with a leading `v`. A development
version is never committed; CI derives it from tags (see
[Development packages](#development-packages)).

| Channel | Committed version | Package version | Git tag | Destination |
| :-- | :-- | :-- | :-- | :-- |
| Development | Last release (`X.Y.ZrcN` or `X.Y.Z`, tagged) | `X.Y.Z.devN` or `X.Y.(Z+1).devN`, derived in CI | None | GitHub Actions artifact |
| Release candidate | `X.Y.ZrcN` | `X.Y.ZrcN` | `vX.Y.ZrcN` | Production PyPI |
| Stable | `X.Y.Z` | `X.Y.Z` | `vX.Y.Z` | Production PyPI |

Use the canonical Python spelling `0.9.0rc1`, not the Go-style
`0.9.0-rc.1`. Packaging tools may normalize the latter, but the workflows
require canonical input.

## Preparing a version

Change both version sources at once with the version script, which keeps each
file's formatting and fails unless both sources agree afterwards:

```bash
python scripts/version.py get                 # print the committed version
python scripts/version.py set 0.15.0rc1       # release pull request
```

`set` accepts only the committed forms `X.Y.ZrcN` and `X.Y.Z` and rejects
development versions. `python scripts/version.py set-dev` writes the derived
development version and is only for disposable CI checkouts; never commit its
result.

## Development packages

Development packages are for internal testing and must not be uploaded to
production PyPI. They are built manually; merging into `main` does not publish
or upload one. A `main` push whose committed version is already tagged runs only
the dev-environment live smoke gate in the **Publish to PyPI** workflow.

The **Build development package** workflow derives the development version in
its disposable checkout and never commits it:

- After an RC `X.Y.ZrcN`, the version is `X.Y.Z.devN`, which sorts below the RC.
- After a stable `X.Y.Z`, the version is the next patch `X.Y.(Z+1).devN`.
- `N` is the number of first-parent commits since the newest stable tag
  `vA.B.C` reachable from the built commit, and must be at least 1. RC tags do
  not reset it. For example, with `0.14.0` committed and tagged, the third
  first-parent commit after `v0.14.0` builds `0.14.1.dev3`.

1. Run the **Build development package** workflow with the exact branch, tag,
   or commit as its `ref` input (default `main`). A ref that is exactly a stable
   release tag has no development version and fails.
2. Download the wheel artifact whose name includes both the package version and
   commit SHA.
3. Install that exact wheel in the target environment:

   ```bash
   python -m pip install ./lambdadb-0.14.1.dev3-py3-none-any.whl
   ```

4. Record the workflow run, commit SHA, package version, and test environment in
   the validation result.

Builds of different branches can derive the same development version, so the
commit SHA in the artifact name, not the package version, identifies its
contents.

## Release candidates

Release candidates provide an explicit opt-in preview through production PyPI.
pip excludes prereleases from normal selection by default, so an existing
stable installation does not upgrade to an RC unless the consumer opts in.

1. Complete development and environment smoke tests.
2. Open a release pull request into `main` that sets the RC with
   `python scripts/version.py set 0.9.0rc1` and changes the `CHANGELOG.md`
   Unreleased heading to that exact package version.
3. Merge it and record the exact merge commit. Because `v0.9.0rc1` does not
   exist on `origin` yet, that `main` push runs the
   **Publish to PyPI** workflow in verification mode: metadata validation,
   tests on every supported Python version, distribution checks, and the
   production live smoke gate, with no publication. Do not merge other pull requests until the release is tagged,
   or tag the release pull request's merge commit explicitly.
4. After verification passes and with explicit publication approval, create tag
   `v0.9.0rc1` from that exact `main` commit. Never move an existing tag.
5. Create a GitHub Release whose name exactly matches the tag. Mark an RC as a
   prerelease and explicitly leave it out of the `latest` designation.
6. Wait for the **Publish to PyPI** workflow to validate, test, build, run the
   production live smoke gate again, and publish the package.
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

If an RC needs a fix, merge it into `main` through a new pull request and
increment the RC number. Never move or replace an existing tag or PyPI version.

## Stable releases

Publish the matching stable version only after the release candidate is
accepted and all feedback is resolved.

1. Open a release pull request into `main` that sets the stable version with
   `python scripts/version.py set 0.9.0`.
2. Update the release notes and user-facing documentation.
3. Run the complete validation checklist.
4. Merge the reviewed release pull request and wait for the `main` push
   verification run to pass.
5. Create tag `v0.9.0` from that exact merge commit.
6. Create a non-prerelease GitHub Release for the tag.
7. Verify the PyPI package and a clean installation.

## After a release

After the tag exists, `main` keeps the released version until the next release
pull request; there is no follow-up version pull request. Later `main` pushes
run in development mode, and development packages derive their versions from the
tags.

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
- Confirm the production live smoke gate passed for the release commit, and
  complete applicable third-party integration smoke tests.
- Review generated release notes before publishing the GitHub Release.

See [docs/TESTING.md](docs/TESTING.md) for local and integration test commands.

## Workflow boundaries

- `.github/workflows/dev-package.yaml` is the only workflow for development
  artifacts. It is manually dispatched, tests the committed tree, writes the
  derived `X.Y.Z.devN` version into its disposable checkout, and never receives
  PyPI credentials.
- `.github/workflows/publish.yaml` runs for `main` pushes and published GitHub
  Releases. A `main` push must carry an RC or stable version; a committed
  development version fails. It queries the tags on `origin` (not the local
  checkout): when `v<version>` exists, the push is a development commit and runs
  only the dev-environment live smoke gate. When it does not exist, the push is
  a release commit and runs the validation, test, build, and production live
  smoke jobs without publishing. A Release runs the
  same jobs and publishes its RC or stable version only after all of them pass. The workflow rejects development
  versions, non-canonical versions, version mismatches, versions outside exact
  `X.Y.ZrcN` / `X.Y.Z` channels, mismatched release names or changelog headings,
  incorrect GitHub prerelease flags, and release commits outside `main`.
- The production publish job uses PyPI Trusted Publishing with a short-lived
  OIDC credential.
- `scripts/publish.sh` intentionally refuses direct token-based publishing.
- Ordinary pull request CI has no credentials and runs no live tests.

## Deployed live smoke gate

The `live-smoke` job in `.github/workflows/publish.yaml` runs
`python scripts/run_live_smoke.py`, which runs every
`tests/integration/test_*_live.py` file in one sequential pytest process with
every suite flag enabled (`LAMBDADB_RUN_LIVE_TESTS`,
`LAMBDADB_RUN_VERSIONING_SMOKE`, `LAMBDADB_RUN_QUERY_SCORE_SMOKE`, and
`LAMBDADB_RUN_BAYESIAN_SMOKE`). A skipped live test fails the gate, as does
missing configuration. Each suite creates uniquely named temporary collections
and verifies their deletion. The run takes about three minutes.

| Run mode | Event | Live target |
| :-- | :-- | :-- |
| development | `main` push whose version is already tagged on `origin` | Dev environment; nothing is published |
| verify | `main` push whose `X.Y.ZrcN` or `X.Y.Z` has no `v<version>` tag on `origin` yet | Production; nothing is published |
| release | Published GitHub Release | Production, before the PyPI publish job |

The job authenticates to AWS with a dedicated GitHub OIDC role, then reads the
smoke project API key from Secrets Manager. The key is masked in the workflow
log and passed only in the pytest child process environment, never in command
arguments, files, artifacts, or GitHub Secrets.

The following repository Variables configure the gate. The `LAMBDADB_DEV_`
Variables serve development pushes; the `LAMBDADB_PROD_` Variables serve release
verification and Releases. A missing Variable fails the run; it never falls back
to the other environment.

| Variable | Value |
| :-- | :-- |
| `LAMBDADB_DEV_BASE_URL` | `https://internal-dev-aws-apne2-v3-c05a2b5d492a.lambdadb.ai` |
| `LAMBDADB_DEV_PROJECT_NAME` | Dedicated SDK smoke project in `dev-aws-apne2-v3` (`python-sdk-ci`) |
| `LAMBDADB_DEV_SMOKE_AWS_ROLE_ARN` | Dev OIDC role (`lambdadb-python-sdk-smoke`) |
| `LAMBDADB_DEV_SMOKE_SECRET_ARN` | Exact ARN of the dev project's API key secret |
| `LAMBDADB_PROD_BASE_URL` | `https://aws-ap-northeast-2-v3.lambdadb.ai` |
| `LAMBDADB_PROD_PROJECT_NAME` | Dedicated SDK smoke project in `prod-aws-apne2-v3` (`python-sdk-ci`) |
| `LAMBDADB_PROD_SMOKE_AWS_ROLE_ARN` | Production OIDC role (`lambdadb-python-sdk-prod-smoke`) |
| `LAMBDADB_PROD_SMOKE_SECRET_ARN` | Exact ARN of the production project's API key secret |

Store each project key as a plain SecretString in `ap-northeast-2`. Use a
dedicated project where test collections may be created and deleted, with a
`rateLimit` of at least 100 requests per second. Do not grant the workflow the
stack admin key, project creation, deployment, or secret write permissions. Key
rotation updates the AWS secret without changing this workflow.

Each role trusts audience `sts.amazonaws.com` and only these subjects. The dev
role:

```text
repo:lambdadb/lambdadb-python-client:ref:refs/heads/main
```

The production role (release verification on `main`, Releases on tags):

```text
repo:lambdadb/lambdadb-python-client:ref:refs/heads/main
repo:lambdadb/lambdadb-python-client:ref:refs/tags/v*
```

Each role's permission policy allows only `secretsmanager:GetSecretValue` on its
own environment's smoke secret ARN (plus `kms:Decrypt` on the exact key only if
the secret uses a customer-managed KMS key).

Run the same gate locally with AWS credentials that can read the secret, for
example an SSO profile. Outside GitHub Actions the runner prints no mask
command, so the key never reaches the terminal:

```bash
AWS_PROFILE=dev \
LAMBDADB_BASE_URL=https://internal-dev-aws-apne2-v3-c05a2b5d492a.lambdadb.ai \
LAMBDADB_PROJECT_NAME=python-sdk-ci \
LAMBDADB_SMOKE_SECRET_ARN=<dev smoke secret ARN> \
poetry run python scripts/run_live_smoke.py
```

Production can lag dev. A live failure caused by an undeployed or changed
server contract blocks the gate; report the exact error rather than skipping
the test. Missing credentials or an untested endpoint are never a successful
live validation.

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
