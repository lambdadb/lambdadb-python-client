# Repository agent instructions

These instructions apply to the entire repository.

<!-- CLONE:ARTIFACT-REVIEW-CONTRACT:START -->
## Artifact review contract

When a response creates, changes, or relies on an artifact that needs human
review, the final response must list every such artifact with a directly
reviewable URI. Use an absolute local path for a local artifact and a direct URL
or deep link for a remote artifact. Include enough context to identify what
should be reviewed, and do not claim that an artifact was reviewed unless it
was actually opened and checked.
<!-- CLONE:ARTIFACT-REVIEW-CONTRACT:END -->

## Packaging and release policy

For any task that changes the SDK implementation, public API, API contract,
package metadata, version, Git tag, GitHub Release, or publishing workflow, read
and follow [RELEASING.md](RELEASING.md) in full before making changes.
`RELEASING.md` is the source of truth for packaging and releases.

The following rules are mandatory:

- Pin the exact API contract revision used for implementation. A source branch
  or documentation revision is not evidence that the API is deployed.
- Keep the versions in `pyproject.toml` and `src/lambdadb/version.py` identical.
- Use canonical PEP 440 versions: `X.Y.Z.devN` for development artifacts,
  `X.Y.ZrcN` for release candidates, and `X.Y.Z` for stable releases.
- Development builds must use the artifact-only development workflow. Do not
  publish routine development releases to production PyPI.
- Release candidates may reach production PyPI only through a GitHub Release
  marked as a prerelease. Stable releases must not be marked as prereleases.
- Never replace an existing PyPI version or move a published Git tag. Publish
  the next development, RC, or patch version instead.
- Never create or push a tag, publish a GitHub Release, upload to PyPI, yank a
  PyPI release, or promote an RC without explicit user approval.
- Run the release checks in `RELEASING.md` and the applicable environment smoke
  tests before any RC or stable publication.
