#!/usr/bin/env python3
"""Validate immutable release metadata before the publish job can run."""

from __future__ import annotations

import os
from pathlib import Path
import re
import runpy

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def validate_release_metadata(
    *, release_tag: str, release_name: str, release_is_prerelease: bool
) -> str:
    """Validate tag, package/runtime versions, changelog, and release flags."""
    match = re.fullmatch(r"v(?P<version>.+)", release_tag)
    if not match:
        raise ValueError(f"Release tag must look like v<version>, got: {release_tag}")

    version_text = match.group("version")
    version = Version(version_text)
    if str(version) != version_text:
        raise ValueError(
            "Release tag must use canonical PEP 440 syntax: "
            f"{version_text!r} normalizes to {str(version)!r}"
        )

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_section = re.search(
        r"(?ms)^\[project\]\s*$\n(?P<body>.*?)(?=^\[|\Z)", pyproject
    )
    version_match = (
        None
        if project_section is None
        else re.search(
            r'^version\s*=\s*["\'](?P<version>[^"\']+)["\']\s*$',
            project_section.group("body"),
            re.MULTILINE,
        )
    )
    if version_match is None:
        raise ValueError("pyproject.toml must define project.version")
    project_version = version_match.group("version")
    runtime_version = runpy.run_path(str(ROOT / "src/lambdadb/version.py"))[
        "SDK_VERSION"
    ]

    if version_text != project_version or version_text != runtime_version:
        raise ValueError(
            "Tag, project, and runtime versions must match: "
            f"tag={version_text!r}, project={project_version!r}, "
            f"runtime={runtime_version!r}"
        )
    if release_name != release_tag:
        raise ValueError(
            f"GitHub Release name must exactly match tag {release_tag!r}, got {release_name!r}"
        )
    if version.is_devrelease:
        raise ValueError(
            "Development releases must not be published to production PyPI"
        )
    if version.is_prerelease and (version.pre is None or version.pre[0] != "rc"):
        raise ValueError("Only X.Y.ZrcN prereleases may be published")
    if version.is_prerelease != release_is_prerelease:
        raise ValueError(
            "GitHub prerelease flag does not match package version: "
            f"version={version}, prerelease={release_is_prerelease}"
        )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = re.findall(
        r"^## (?:\[)?([^\]\s]+)(?:\])?(?:\s+-.*)?$", changelog, re.MULTILINE
    )
    if version_text not in headings:
        raise ValueError(
            f"CHANGELOG.md must contain a level-2 heading for {version_text}"
        )
    return version_text


def main() -> None:
    version = validate_release_metadata(
        release_tag=os.environ["RELEASE_TAG"],
        release_name=os.environ["RELEASE_NAME"],
        release_is_prerelease=os.environ["RELEASE_IS_PRERELEASE"].lower() == "true",
    )
    print(f"Validated immutable release metadata for v{version}")


if __name__ == "__main__":
    main()
