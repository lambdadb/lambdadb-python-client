# Contributing to This Repository

Thank you for your interest in contributing to this repository. This SDK is
maintained manually. Issues and focused pull requests are welcome.

## How to Report Issues

If you encounter any bugs or have suggestions for improvements, please open an issue on GitHub. When reporting an issue, please provide as much detail as possible to help us reproduce the problem. This includes:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected and actual behavior
- Any relevant logs, screenshots, or error messages
- Information about your environment (e.g., operating system, software versions)
    - For example can be collected using the `npx envinfo` command from your terminal if you have Node.js installed

## Issue Triage

We will review and triage issues as quickly as possible. Fixes are included in
the next release.

## Preparing a pull request

Branch from `main` and open the pull request against `main`; maintainers merge
it with **Squash and merge**. There is no `develop` branch. Run the checks in
[docs/TESTING.md](docs/TESTING.md) before requesting review.

## Maintaining text analyzer models

For the scoped analyzer contract, maintain the pinned schema and regenerate its
model and documentation with the [analyzer maintenance procedure](schemas/README.md).
The original Speakeasy configuration is no longer present in this repository.

## Releasing

Maintainers must follow [RELEASING.md](RELEASING.md). `main` carries the next
version as `X.Y.Z.dev0` between releases. Development packages are
artifact-only, release candidates use canonical `X.Y.ZrcN` versions, and stable
packages are published only after release-candidate validation. Creating or
merging a pull request does not publish a package.

## Contact

If you have any questions or need further assistance, please feel free to reach out by opening an issue.

Thank you for your understanding and cooperation!

The Maintainers
