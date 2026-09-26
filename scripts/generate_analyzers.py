"""Generate only analyzer declarations and references from the pinned schema."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generated_files() -> dict[Path, str]:
    """Render the scoped outputs without changing runtime defaults or validators."""
    contract = json.loads((ROOT / "schemas/text-analyzers.json").read_text())
    schema = contract["schema"]
    names = schema["items"]["enum"]
    description = schema["description"]
    model_path = ROOT / "src/lambdadb/models/indexconfigs_union.py"
    model = model_path.read_text()
    enum = "class Analyzer(str, Enum):\n" + "\n".join(
        f'    {name.upper()} = "{name}"' for name in names
    )
    model, count = re.subn(
        r"class Analyzer\(str, Enum\):.*?(?=\n\n\nclass IndexConfigsTextTypedDict)",
        lambda _: enum,
        model,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Expected exactly one Analyzer declaration")
    model, count = re.subn(
        r'(    analyzers: [^\n]+\n)    r"""[^\n]*"""',
        lambda match: match[1] + f'    r"""{description}"""',
        model,
    )
    if count != 2:
        raise ValueError("Expected model and TypedDict analyzer descriptions")

    analyzer_doc = "# Analyzer\n\n## Values\n\n| Name | Value |\n| --- | --- |\n"
    analyzer_doc += "".join(f"| `{name.upper()}` | {name} |\n" for name in names)
    text_doc = (
        "# IndexConfigsText\n\n## Fields\n\n"
        "| Field | Type | Required | Description |\n"
        "| --- | --- | --- | --- |\n"
        "| `type` | [models.TypeText](typetext.md) | :heavy_check_mark: | N/A |\n"
        "| `analyzers` | List[[models.Analyzer](analyzer.md)] | :heavy_minus_sign: | "
        + description
        + " |\n"
    )
    return {
        model_path: model,
        ROOT / "docs/models/analyzer.md": analyzer_doc,
        ROOT / "docs/models/indexconfigstext.md": text_doc,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on stale outputs")
    args = parser.parse_args()
    stale = []
    for path, content in generated_files().items():
        if path.read_text() != content:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.write_text(content)
    if args.check and stale:
        parser.exit(1, "Stale analyzer outputs: " + ", ".join(stale) + "\n")


if __name__ == "__main__":
    main()
