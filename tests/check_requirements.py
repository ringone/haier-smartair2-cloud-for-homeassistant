"""Check requirements traceability; never import or execute evidence/product code.

This checks document consistency and source-symbol existence, not acceptance,
coverage, passing tests, release approval, or physical hardware compliance.
"""
import argparse
import ast
import csv
from pathlib import Path
import re
import sys
import tokenize


REQUIREMENT_ID = r"(?:RF|RNF|RP)-\d{3}"
HEADING = re.compile(rf"^### ({REQUIREMENT_ID}) — (.+)$", re.MULTILINE)
FIELD = re.compile(r"^- \*\*([^*]+):\*\*[ \t]*(.*)$", re.MULTILINE)
LABELS = {
    "Prioridade": "priority", "Origem": "origin",
    "Estado da implementação": "status", "Requisito": "requirement",
    "Critérios de aceitação": "acceptance", "Código/documentação": "code",
    "Evidência existente": "evidence", "Verificação": "verification",
    "Lacuna/limitação": "gap",
}
REQUIRED = {"id", "title", "priority", "origin", "status", "verification", "requirement", "acceptance", "code", "evidence"}
EVIDENCE = re.compile(r"(?<!\w)E\d+(?!\w)")


def scalar(value):
    """Ignore layout whitespace and a field's final prose full stop only."""
    return " ".join(value.split()).removesuffix(".")


def items(value):
    return [part.strip() for part in value.split("|") if part.strip()]


def source_path(root, name, errors):
    """Reject traversal and symlink escapes before reading a source file."""
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root):
        errors.append(f"{name}: source path escapes repository")
        return None
    if not path.is_file():
        errors.append(f"{name}: source path does not exist or is not a file")
        return None
    return path


def symbols(path):
    """Only module functions and directly declared class methods qualify."""
    with tokenize.open(path) as handle:
        tree = ast.parse(handle.read(), filename=str(path))
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    names = set()
    for node in tree.body:
        if isinstance(node, functions):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.update(f"{node.name}.{method.name}" for method in node.body
                         if isinstance(method, functions))
    return names


def validate(root):
    """Return actionable errors and inventory counts; no runtime imports."""
    root = root.resolve()
    errors = []
    document = (root / "docs/requisitos.md").read_text(encoding="utf-8")
    requirements = {}
    for heading in re.finditer(r"^#{1,6} (?:RF|RNF|RP)-.*$", document, re.MULTILINE):
        if not HEADING.fullmatch(heading.group()):
            errors.append(f"invalid requirement heading: {heading.group()}")
    for match in HEADING.finditer(document):
        identifier, title = match.groups()
        end = re.search(r"^#{1,3} ", document[match.end():], re.MULTILINE)
        block = document[match.end():match.end() + end.start()] if end else document[match.end():]
        if identifier in requirements:
            errors.append(f"duplicate requirement {identifier} in docs/requisitos.md")
        fields = {"id": identifier, "title": title}
        matches = list(FIELD.finditer(block))
        for index, field in enumerate(matches):
            label, first = field.groups()
            key = LABELS.get(label)
            if not key:
                continue
            if key in fields:
                errors.append(f"{identifier}: duplicate Markdown field {key}")
            if key == "acceptance":
                stop = matches[index + 1].start() if index + 1 < len(matches) else len(block)
                bullets = re.findall(r"^[ \t]+- (.+)$", block[field.end():stop], re.MULTILINE)
                fields[key] = " | ".join(([first] if first.strip() else []) + bullets)
            else:
                fields[key] = first.strip()
        for key in REQUIRED - {"id", "title"}:
            if not fields.get(key):
                errors.append(f"{identifier}: missing Markdown {key}")
        fields["code"] = re.findall(r"`([^`]+)`", fields.get("code", ""))
        if not fields["code"]:
            errors.append(f"{identifier}: missing Markdown code paths (use backticks)")
        fields["evidence"] = EVIDENCE.findall(fields.get("evidence", ""))
        fields["references"] = set(EVIDENCE.findall(block))
        requirements[identifier] = fields
    if not requirements:
        errors.append("docs/requisitos.md: no requirement headings found (expected ### RF/RNF/RP-NNN — title)")

    declarations = {}
    for match in re.finditer(r"^- \*\*(E\d+):\*\*(.*)$", document, re.MULTILINE):
        identifier, declaration = match.groups()
        if identifier in declarations:
            errors.append(f"duplicate evidence {identifier}")
        target = re.fullmatch(r"\s*`([^`]+)::([^`]+)`\.?\s*", declaration)
        declarations[identifier] = target.groups() if target else None
        if not re.fullmatch(r"E\d{2}", identifier) or identifier == "E00" or not target:
            errors.append(f"{identifier}: invalid evidence mapping; expected `tests/path.py::Class.method` or `tests/path.py::function`")
    cache = {}
    for identifier, target in declarations.items():
        if not target:
            continue
        name, symbol = target
        path = source_path(root, name, errors)
        if path is None:
            continue
        try:
            if path not in cache:
                cache[path] = symbols(path)
            if symbol not in cache[path]:
                errors.append(f"{identifier}: missing AST symbol {symbol} in {name}")
        except (OSError, SyntaxError, UnicodeError) as exc:
            errors.append(f"{identifier}: cannot parse {name}: {exc}")

    rows = {}
    with (root / "docs/matriz-requisitos.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        header = reader.fieldnames or []
        for key in sorted(REQUIRED - set(header)):
            errors.append(f"docs/matriz-requisitos.csv: missing required column {key}")
        if len(header) != len(set(header)):
            errors.append("docs/matriz-requisitos.csv: duplicate column names")
        for number, row in enumerate(reader, 2):
            identifier = row.get("id") or f"CSV row {number}"
            if not re.fullmatch(REQUIREMENT_ID, identifier):
                errors.append(f"{identifier}: invalid CSV requirement id")
            if identifier in rows:
                errors.append(f"duplicate CSV id {identifier} at row {number}")
            for key in REQUIRED - {"evidence"}:
                if not (row.get(key) or "").strip():
                    errors.append(f"{identifier}: missing CSV {key}")
            if None in row or any(value is None for value in row.values()):
                errors.append(f"{identifier}: malformed CSV row {number}; check delimiter/quoting")
            rows[identifier] = row

    for identifier in sorted(requirements.keys() - rows.keys()):
        errors.append(f"{identifier}: missing CSV entry")
    for identifier in sorted(rows.keys() - requirements.keys()):
        errors.append(f"{identifier}: CSV entry has no Markdown requirement")
    for identifier, fields in requirements.items():
        row = rows.get(identifier)
        if row is None:
            continue
        for key in ("title", "priority", "origin", "status", "requirement", "acceptance", "verification", "gap"):
            if key in fields or key in row:
                if scalar(fields.get(key, "")) != scalar(row.get(key) or ""):
                    errors.append(f"{identifier}: {key} differs between Markdown and CSV")
        for key in ("code", "evidence"):
            expected = fields[key]
            actual = items(row.get(key) or "")
            if set(expected) != set(actual):
                errors.append(f"{identifier}: {key} differs between Markdown and CSV")
            if len(expected) != len(set(expected)) or len(actual) != len(set(actual)):
                errors.append(f"{identifier}: duplicate {key} reference")
        for name in set(fields["code"]) | set(items(row.get("code") or "")):
            source_path(root, name, errors)
        references = fields["references"] | set(items(row.get("evidence") or ""))
        for reference in sorted(references - declarations.keys()):
            errors.append(f"{identifier}: undeclared evidence {reference}")
    return errors, len(requirements), len(declarations)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        errors, count, evidence_count = validate(args.root)
    except (OSError, UnicodeError, csv.Error) as exc:
        errors, count, evidence_count = [f"cannot read requirements inputs: {exc}"], 0, 0
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Traceability OK: {count} requirements, {evidence_count} evidence mappings; "
          "structural consistency, not compliance or proof that tests pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
