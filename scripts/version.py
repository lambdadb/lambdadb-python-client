#!/usr/bin/env python3
"""Read and set the package version in every version source at once.

Usage:
    python scripts/version.py get
    python scripts/version.py set <version>
    python scripts/version.py next-dev <released-version>
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = "pyproject.toml"
RUNTIME = "src/lambdadb/version.py"

_CORE = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
# Versions that may be committed: the dev placeholder between releases, or an
# RC/stable release.
COMMITTED_VERSION = re.compile(rf"{_CORE}(?:\.dev0|rc[1-9][0-9]*)?")
_RELEASED_VERSION = re.compile(rf"{_CORE}(rc[1-9][0-9]*)?")
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


def set_version(version: str, root: Path = ROOT) -> str:
    """Set every version source to a committed version, preserving formatting."""
    if COMMITTED_VERSION.fullmatch(version) is None:
        raise ValueError(
            f"Unsupported version {version}; commit X.Y.Z.dev0, X.Y.ZrcN, or X.Y.Z"
        )
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


def next_dev_version(released: str) -> str:
    """Return the placeholder that follows a published RC or stable release.

    An RC keeps its version (X.Y.ZrcN -> X.Y.Z.dev0); a stable release moves to
    the next patch (X.Y.Z -> X.Y.(Z+1).dev0).
    """
    match = _RELEASED_VERSION.fullmatch(released)
    if match is None:
        raise ValueError(f"Expected an RC or stable version, got {released}")
    major, minor, patch = (int(part) for part in match.group(1, 2, 3))
    if match.group(4) is None:
        patch += 1
    return f"{major}.{minor}.{patch}.dev0"


def main(argv: list[str]) -> int:
    """Run the command-line interface."""
    try:
        if argv == ["get"]:
            print(read_version())
        elif len(argv) == 2 and argv[0] == "set":
            print(set_version(argv[1]))
        elif len(argv) == 2 and argv[0] == "next-dev":
            print(next_dev_version(argv[1]))
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
