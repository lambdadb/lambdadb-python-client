#!/usr/bin/env python3
"""Read and set the package version in every version source at once.

Usage:
    python scripts/version.py get
    python scripts/version.py set <version>
    python scripts/version.py set-dev
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = "pyproject.toml"
RUNTIME = "src/lambdadb/version.py"

_CORE = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
# Versions that may be committed: an RC or stable release. Development versions
# are derived from tags in disposable CI checkouts and never committed.
COMMITTED_VERSION = re.compile(rf"{_CORE}(rc[1-9][0-9]*)?")
_STABLE_TAG = re.compile(rf"v{_CORE}")
_PROJECT_SECTION = re.compile(r"(?ms)^\[project\][ \t]*$\n(?P<body>.*?)(?=^\[|\Z)")
_PROJECT_VERSION = re.compile(r'(?m)^(version\s*=\s*")([^"]+)("[ \t]*)$')
_RUNTIME_VERSION = re.compile(r'(?m)^(SDK_VERSION: str = ")([^"]+)(")$')


def _read(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def _project_version(text: str) -> tuple[re.Match[str], re.Match[str]]:
    section = _PROJECT_SECTION.search(text)
    match = None if section is None else _PROJECT_VERSION.search(section.group("body"))
    if section is None or match is None:
        raise ValueError(f"{PYPROJECT} must define project.version")
    return section, match


def _runtime_version(text: str) -> re.Match[str]:
    matches = list(_RUNTIME_VERSION.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"{RUNTIME} must define SDK_VERSION exactly once")
    return matches[0]


def read_version(root: Path = ROOT) -> str:
    """Return the version; raise unless every version source agrees."""
    _section, project = _project_version(_read(root, PYPROJECT))
    runtime = _runtime_version(_read(root, RUNTIME))
    if project.group(2) != runtime.group(2):
        raise ValueError(
            f"Version sources must agree: {PYPROJECT} project.version="
            f"{project.group(2)!r}, {RUNTIME} SDK_VERSION={runtime.group(2)!r}"
        )
    return project.group(2)


def _write_version(version: str, root: Path) -> str:
    """Write a version to every source, preserving formatting."""
    read_version(root)
    pyproject = _read(root, PYPROJECT)
    section, project = _project_version(pyproject)
    start = section.start("body") + project.start(2)
    end = section.start("body") + project.end(2)
    runtime = _read(root, RUNTIME)
    match = _runtime_version(runtime)
    updates = {
        PYPROJECT: pyproject[:start] + version + pyproject[end:],
        RUNTIME: runtime[: match.start(2)] + version + runtime[match.end(2) :],
    }
    for path, text in updates.items():
        (root / path).write_text(text, encoding="utf-8")
    if read_version(root) != version:
        raise ValueError("Version update did not reach every source")
    return version


def set_version(version: str, root: Path = ROOT) -> str:
    """Set every version source to a committed RC or stable version."""
    if COMMITTED_VERSION.fullmatch(version) is None:
        raise ValueError(f"Unsupported version {version}; commit X.Y.ZrcN or X.Y.Z")
    return _write_version(version, root)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def development_version(root: Path = ROOT) -> str:
    """Return the development version of the checked-out commit.

    An RC X.Y.ZrcN builds X.Y.Z.devN, below the RC; a stable X.Y.Z builds the
    next patch X.Y.(Z+1).devN. N counts first-parent commits since the newest
    stable tag vA.B.C reachable from HEAD and must be at least 1.
    """
    committed = read_version(root)
    match = COMMITTED_VERSION.fullmatch(committed)
    if match is None:
        raise ValueError(
            f"Committed version {committed} must be an RC or stable version"
        )
    major, minor, patch = (int(part) for part in match.group(1, 2, 3))
    if match.group(4) is None:
        patch += 1
    stable_tags = [
        (tuple(int(part) for part in tag_match.groups()), tag)
        for tag in _git(root, "tag", "--merged", "HEAD", "--list", "v*").splitlines()
        if (tag_match := _STABLE_TAG.fullmatch(tag)) is not None
    ]
    newest = max(stable_tags, default=None)
    revisions = "HEAD" if newest is None else f"{newest[1]}..HEAD"
    count = int(_git(root, "rev-list", "--count", "--first-parent", revisions))
    if count < 1:
        raise ValueError(f"Expected at least one first-parent commit in {revisions}")
    return f"{major}.{minor}.{patch}.dev{count}"


def set_development_version(root: Path = ROOT) -> str:
    """Write the development version; only for disposable CI checkouts."""
    return _write_version(development_version(root), root)


def main(argv: list[str]) -> int:
    """Run the command-line interface."""
    try:
        if argv == ["get"]:
            print(read_version())
        elif len(argv) == 2 and argv[0] == "set":
            print(set_version(argv[1]))
        elif argv == ["set-dev"]:
            print(set_development_version())
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
