"""Black-box, stdlib-only tests using real temporary repositories."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).with_name("check_requirements.py")
FIELDS = "id title priority origin status verification requirement acceptance code evidence gap".split()
DOCUMENT = """# Requirements
### RF-001 — Local operation
- **Prioridade:** P0.
- **Origem:** Decision.
- **Estado da implementação:** Implementado.
- **Requisito:** Operate locally.
- **Critérios de aceitação:**
  - Works offline.
- **Código/documentação:** `src/local.py`.
- **Evidência existente:** E01, E02.
- **Verificação:** Partial.
## Evidence
- **E01:** `tests/source.py::Checks.test_offline`.
- **E02:** `tests/source.py::main`.
"""


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("docs", "src", "tests"):
            (self.root / folder).mkdir()
        (self.root / "src/local.py").write_text("raise RuntimeError('never import product')\n")
        (self.root / "tests/source.py").write_text(
            "raise RuntimeError('never import evidence')\n"
            "class Checks:\n    async def test_offline(self):\n        pass\n"
            "def main():\n    pass\n"
        )
        self.document = DOCUMENT
        self.rows = [dict(zip(FIELDS, [
            "RF-001", "Local operation", "P0", "Decision", "Implementado",
            "Partial", "Operate locally.", "Works offline.", "src/local.py",
            "E01 | E02", "",
        ]))]

    def run_checker(self):
        (self.root / "docs/requisitos.md").write_text(self.document, encoding="utf-8")
        with (self.root / "docs/matriz-requisitos.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter=";")
            writer.writeheader()
            writer.writerows(self.rows)
        return subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.root)],
            capture_output=True, text=True, check=False,
        )

    def assert_invalid(self, diagnostic):
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(diagnostic, result.stderr)

    def test_duplicate_markdown_ids(self):
        self.document = self.document.replace("## Evidence", DOCUMENT.split("## Evidence")[0] + "\n## Evidence")
        self.assert_invalid("duplicate requirement RF-001")

    def test_duplicate_csv_ids(self):
        self.rows.append(dict(self.rows[0]))
        self.assert_invalid("duplicate CSV id RF-001")

    def test_missing_csv_entry(self):
        self.rows.clear()
        self.assert_invalid("RF-001: missing CSV entry")

    def test_unknown_source_path(self):
        self.document = self.document.replace("src/local.py", "src/missing.py")
        self.rows[0]["code"] = "src/missing.py"
        self.assert_invalid("src/missing.py: source path does not exist")

    def test_missing_ast_test_symbol(self):
        self.document = self.document.replace("Checks.test_offline", "Checks.test_missing")
        self.assert_invalid("E01: missing AST symbol Checks.test_missing")

    def test_mismatched_status(self):
        self.rows[0]["status"] = "Pendente"
        self.assert_invalid("RF-001: status differs")

    def test_missing_requirement_statement_in_both_documents(self):
        self.document = self.document.replace("- **Requisito:** Operate locally.\n", "")
        self.rows[0]["requirement"] = ""
        self.assert_invalid("RF-001: missing Markdown requirement")

    def test_missing_verification_status_in_both_documents(self):
        self.document = self.document.replace("- **Verificação:** Partial.\n", "")
        self.rows[0]["verification"] = ""
        self.assert_invalid("RF-001: missing Markdown verification")

    def test_missing_required_fields(self):
        self.rows[0]["acceptance"] = ""
        self.document = self.document.replace("- **Origem:** Decision.\n", "")
        self.assert_invalid("RF-001: missing Markdown origin")

    def test_unknown_evidence_reference(self):
        self.document = self.document.replace("E01, E02", "E01, E99")
        self.rows[0]["evidence"] = "E01 | E99"
        self.assert_invalid("RF-001: undeclared evidence E99")

    def test_mismatched_code_and_evidence_lists(self):
        self.rows[0]["code"] = "tests/source.py"
        self.rows[0]["evidence"] = "E01"
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("RF-001: code differs", result.stderr)
        self.assertIn("RF-001: evidence differs", result.stderr)

    def test_path_outside_repository(self):
        self.document = self.document.replace("src/local.py", "../outside.py")
        self.rows[0]["code"] = "../outside.py"
        self.assert_invalid("../outside.py: source path escapes repository")

    def test_duplicate_evidence_declaration(self):
        self.document += "\n- **E01:** `tests/source.py::main`.\n"
        self.assert_invalid("duplicate evidence E01")

    def test_malformed_heading_id_is_not_silently_ignored(self):
        self.document += "\n### RF-02 — Malformed requirement\n"
        self.assert_invalid("invalid requirement heading")

    def test_empty_markdown_code_list(self):
        self.document = self.document.replace("`src/local.py`", "No files")
        self.rows[0]["code"] = ""
        self.assert_invalid("RF-001: missing Markdown code paths")

    def test_explicit_no_evidence_is_valid_not_compliance(self):
        self.document = self.document.replace("E01, E02", "Nenhum teste dedicado identificado")
        self.rows[0]["evidence"] = ""
        self.rows[0]["status"] = "Pendente"
        self.document = self.document.replace("Implementado", "Pendente")
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not compliance", result.stdout)

    def test_symlink_outside_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "external.py"
            target.write_text("pass\n")
            (self.root / "src/local.py").unlink()
            (self.root / "src/local.py").symlink_to(target)
            self.assert_invalid("src/local.py: source path escapes repository")

    def test_valid_fixture_resolves_symbols_without_imports(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 requirements", result.stdout)
        self.assertIn("not compliance", result.stdout)


if __name__ == "__main__":
    unittest.main()
