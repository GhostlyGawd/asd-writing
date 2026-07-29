from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "write-asd-ste100" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


terms = load_module("check_project_terms", SCRIPTS / "check_project_terms.py")
reporter = load_module(
    "create_compliance_report", SCRIPTS / "create_compliance_report.py"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def term_entry(
    approved_term: str = "fuel pump",
    *,
    term_type: str = "technical_noun",
    part_of_speech: str = "noun",
    domain: str = "fuel",
    status: str = "APPROVED",
    inflections: list[str] | None = None,
    synonyms: list[str] | None = None,
) -> dict:
    return {
        "approved_term": approved_term,
        "definition": f"Definition of {approved_term}",
        "term_type": term_type,
        "approved_part_of_speech": part_of_speech,
        "permitted_inflections": inflections or [],
        "prohibited_synonyms": synonyms or [],
        "domain": domain,
        "source_authority": "TEST-AUTHORITY",
        "approval_status": status,
        "approval_date": "2025-01-01" if status == "APPROVED" else None,
        "notes": "",
    }


def word_rows(text: str, technical_terms: dict[str, str] | None = None) -> list[dict]:
    technical_terms = technical_terms or {}
    rows = []
    for index, token in enumerate(terms.lexical_tokens(text), start=1):
        term = technical_terms.get(token["token"])
        classification = (
            "APPROVED_TECHNICAL_NAME" if term else "ASD_DICTIONARY_WORD"
        )
        rows.append(
            {
                "index": index,
                "token": token["token"],
                "location": token["location"],
                "classification": classification,
                "basis": (
                    f"project terminology entry: {term}"
                    if term
                    else f"Issue 9 dictionary entry: {token['token']}"
                ),
                "result": "PASS",
                "approved_meaning": True if not term else None,
                "approved_part_of_speech": True if not term else None,
                "term": term,
            }
        )
    return rows


class EvidenceFactory:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.references = self.root / "references"
        self.references.mkdir()
        self.standard = self.references / "asd-ste100-issue-9.pdf"
        self.standard.write_bytes(b"authorized-test-standard")
        standard_sha = sha256_bytes(self.standard.read_bytes())
        self.checklist = self.references / "compliance-checklist.yaml"
        self.checklist.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "standard": {
                        "issue": 9,
                        "sha256": standard_sha,
                    },
                    "rule_checks": [
                        {
                            "id": "rule-all",
                            "applies_to": ["all"],
                            "check": "All-content check.",
                            "source": "ASD-STE100 Issue 9, test rule",
                        },
                        {
                            "id": "rule-procedure",
                            "applies_to": ["procedural", "safety"],
                            "check": "Procedure and safety check.",
                            "source": "ASD-STE100 Issue 9, test procedure rule",
                        },
                        {
                            "id": "rule-description",
                            "applies_to": ["descriptive"],
                            "check": "Description check.",
                            "source": "ASD-STE100 Issue 9, test description rule",
                        },
                    ],
                    "dictionary_checks": [
                        {
                            "id": "dictionary-approval",
                            "applies_to": ["each_word"],
                            "check": "Dictionary approval.",
                            "source": "ASD-STE100 Issue 9, test dictionary",
                        }
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        self.terminology = self.root / "project-terminology.yaml"
        self.write_terms([])
        reporter.TRUSTED_SKILL_ROOT = self.root

    def cleanup(self) -> None:
        self.temp.cleanup()

    def write_terms(self, entries: list[dict]) -> None:
        self.terminology.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 2,
                    "approval_status_values": ["APPROVED", "PENDING", "REJECTED"],
                    "term_type_values": [
                        "technical_noun",
                        "technical_verb",
                        "proper_noun",
                        "abbreviation",
                        "identifier",
                    ],
                    "approved_part_of_speech_values": [
                        "noun",
                        "verb",
                        "proper_noun",
                        "abbreviation",
                        "identifier",
                    ],
                    "terms": entries,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    def evidence(
        self,
        *,
        source_text: str = "Disconnect the fuel pump.",
        final_text: str = "Disconnect the fuel pump.",
        task_mode: str = "rewrite",
        output_mode: str = "report",
        content_types: list[str] | None = None,
        technical_terms: dict[str, str] | None = None,
    ) -> dict:
        content_types = content_types or ["procedural"]
        checklist_data = yaml.safe_load(self.checklist.read_text(encoding="utf-8"))
        expected_ids = reporter.expected_check_ids(checklist_data, content_types)
        evidence = {
            "schema_version": 2,
            "task_mode": task_mode,
            "output_mode": output_mode,
            "requested_status": reporter.FULL_STATUS,
            "content_types": content_types,
            "technical_domain": "fuel",
            "authorization": {
                "authority_id": "TEST-AUTHORITY",
                "confirmation_date": dt.date.today().isoformat(),
                "standard_sha256": sha256_bytes(self.standard.read_bytes()),
                "status": "CONFIRMED",
            },
            "artifacts": {
                "source": {
                    "id": "SRC-1",
                    "revision": "A",
                    "text": source_text,
                    "sha256": sha256_text(source_text),
                },
                "output": {
                    "text": final_text,
                    "sha256": sha256_text(final_text),
                },
                "standard": {
                    "path": str(self.standard),
                    "sha256": sha256_bytes(self.standard.read_bytes()),
                },
                "checklist": {
                    "path": str(self.checklist),
                    "sha256": sha256_bytes(self.checklist.read_bytes()),
                },
                "terminology": {
                    "path": str(self.terminology),
                    "sha256": sha256_bytes(self.terminology.read_bytes()),
                },
            },
            "checks": [
                {
                    "check_id": check_id,
                    "location": "complete output",
                    "check_type": "rule" if check_id.startswith("rule-") else "dictionary",
                    "result": "PASS",
                    "rule_or_dictionary_basis": check_id,
                    "correction": "",
                    "reviewer": "LANG-1",
                    "evidence": "Complete output reviewed against controlling entry.",
                }
                for check_id in sorted(expected_ids)
            ],
            "word_classifications": word_rows(final_text, technical_terms),
            "change_report": [
                {
                    "location": "sentence 1",
                    "source_text": source_text,
                    "revised_text": final_text,
                    "reason": "ASD-STE100 rewrite or confirmed no change.",
                    "rule_or_dictionary_basis": "technical source SRC-1",
                    "technical_meaning_preserved": "YES",
                }
            ]
            if task_mode == "rewrite"
            else [],
            "technical_integrity": {
                "facts_preserved": "PASS",
                "safety_preserved": "PASS",
                "source_comparison_evidence": "Compared SRC-1 revision A with final output.",
            },
            "unresolved_items": {
                "language": [],
                "terminology": [],
                "ambiguities": [],
                "source_errors": [],
            },
            "safety_trace": [],
            "reviewers": [],
        }
        if "safety" in content_types:
            evidence["safety_trace"] = [
                {
                    "id": "SAF-1",
                    "source_requirement": "SRC-1",
                    "source_level": "WARNING",
                    "revised_level": "WARNING",
                    "condition": "Fuel is present.",
                    "command": "Disconnect the fuel pump.",
                    "consequence": "Fuel can ignite.",
                    "technical_review_result": "APPROVED",
                }
            ]
        digest = reporter.review_digest(evidence)
        today = dt.date.today().isoformat()
        evidence["reviewers"] = [
            {
                "reviewer_id": "LANG-1",
                "role": "ASD-STE100_LANGUAGE_REVIEWER",
                "review_date": today,
                "review_result": "APPROVED",
                "required_corrections": [],
                "final_approval_state": "APPROVED",
                "reviewed_artifact_sha256": digest,
            },
            {
                "reviewer_id": "TECH-1",
                "role": "AUTHORIZED_TECHNICAL_REVIEWER",
                "review_date": today,
                "review_result": "APPROVED",
                "required_corrections": [],
                "final_approval_state": "APPROVED",
                "reviewed_artifact_sha256": digest,
            },
        ]
        return evidence


class TerminologyHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = EvidenceFactory()

    def tearDown(self) -> None:
        self.factory.cleanup()

    def test_duplicate_yaml_keys_are_rejected(self) -> None:
        path = self.factory.root / "duplicate.yaml"
        path.write_text("schema_version: 2\nschema_version: 1\nterms: []\n", encoding="utf-8")
        with self.assertRaises(terms.InputError):
            terms.load_yaml(path)

    def test_schema_enums_and_dates_are_enforced(self) -> None:
        invalid = term_entry(term_type="invalid", part_of_speech="banana")
        with self.assertRaises(terms.InputError):
            terms.validate_entries(
                {
                    "schema_version": 2,
                    "approval_status_values": ["APPROVED", "PENDING", "REJECTED"],
                    "term_type_values": [
                        "technical_noun",
                        "technical_verb",
                        "proper_noun",
                        "abbreviation",
                        "identifier",
                    ],
                    "approved_part_of_speech_values": [
                        "noun",
                        "verb",
                        "proper_noun",
                        "abbreviation",
                        "identifier",
                    ],
                    "terms": [invalid],
                }
            )

    def test_missing_complete_candidate_coverage_blocks(self) -> None:
        entries = terms.validate_entries(
            yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        )
        result = terms.analyze_text(entries, "Inspect the flux capacitor.", [], "fuel")
        self.assertEqual("INCOMPLETE", result["status"])
        self.assertTrue(
            any(
                item["code"] == "CANDIDATE_COVERAGE_INCOMPLETE"
                for item in result["findings"]
            )
        )

    def test_unknown_technical_term_from_complete_coverage_blocks(self) -> None:
        text = "Inspect the flux capacitor."
        coverage = word_rows(
            text, {"flux": "flux capacitor", "capacitor": "flux capacitor"}
        )
        entries = terms.validate_entries(
            yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        )
        result = terms.analyze_text(entries, text, coverage, "fuel")
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any(item["code"] == "UNKNOWN_TERM" for item in result["findings"]))

    def test_domain_and_identifier_case_are_enforced(self) -> None:
        entry = term_entry(
            "AC-ID",
            term_type="identifier",
            part_of_speech="identifier",
            domain="avionics",
        )
        self.factory.write_terms([entry])
        entries = terms.validate_entries(
            yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        )
        text = "Record ac-id."
        coverage = word_rows(text, {"ac-id": "ac-id"})
        result = terms.analyze_text(entries, text, coverage, "hydraulics")
        self.assertEqual("FAIL", result["status"])
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("UNKNOWN_TERM", codes)

    def test_unicode_is_normalized(self) -> None:
        entry = term_entry("café")
        self.factory.write_terms([entry])
        entries = terms.validate_entries(
            yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        )
        text = "Inspect the cafe\u0301."
        coverage = word_rows(text, {"café": "café"})
        result = terms.analyze_text(entries, text, coverage, "fuel")
        self.assertEqual("PASS", result["status"])

    def test_form_and_synonym_collisions_are_rejected(self) -> None:
        entries = [
            term_entry("controller", inflections=["controllers"]),
            term_entry("controllers", status="PENDING"),
        ]
        data = yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        data["terms"] = entries
        with self.assertRaises(terms.InputError):
            terms.validate_entries(data)

        data["terms"] = [
            term_entry("engine"),
            term_entry("motor", synonyms=["engine"]),
        ]
        with self.assertRaises(terms.InputError):
            terms.validate_entries(data)

    def test_multi_line_phrase_and_unique_lines(self) -> None:
        self.assertEqual([1, 2], terms.occurrences("fuel\npump fuel pump", "fuel pump"))

    def test_human_markdown_is_escaped(self) -> None:
        rendered = terms.render_human(
            {
                "status": "FAIL",
                "blocking_count": 1,
                "scope": "scope",
                "candidate_results": [
                    {"candidate": "bad|term", "result": "FAIL", "basis": "a|b"}
                ],
                "findings": [],
            }
        )
        self.assertIn(r"bad\|term", rendered)
        self.assertIn(r"a\|b", rendered)

    def test_coverage_template_is_complete_and_fail_closed(self) -> None:
        template = terms.coverage_template("Inspect pump 1.")
        self.assertEqual(3, len(template["word_classifications"]))
        self.assertTrue(
            all(
                row["result"] == "REVIEW REQUIRED"
                and row["classification"] == "NON_APPROVED_WORD"
                for row in template["word_classifications"]
            )
        )

    def test_large_inventory_uses_bounded_scan_time(self) -> None:
        entries = [term_entry(f"component {index}") for index in range(500)]
        data = yaml.safe_load(self.factory.terminology.read_text(encoding="utf-8"))
        data["terms"] = entries
        validated = terms.validate_entries(data)
        text = ("unrelated technical text " * 20_000).strip()
        coverage = word_rows(text)
        start = time.perf_counter()
        result = terms.analyze_text(validated, text, coverage, "fuel")
        elapsed = time.perf_counter() - start
        self.assertEqual("PASS", result["status"])
        self.assertLess(elapsed, 5.0)


class ComplianceHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = EvidenceFactory()

    def tearDown(self) -> None:
        self.factory.cleanup()

    def test_empty_checks_cannot_release(self) -> None:
        evidence = self.factory.evidence()
        evidence["checks"] = []
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(2, code)
        self.assertIn("coverage:applicable-checks:INCOMPLETE", result["blockers"])

    def test_release_gates_are_derived_not_accepted_from_input(self) -> None:
        evidence = self.factory.evidence()
        evidence["release_gates"] = {
            name: {"result": "PASS", "evidence": "self-attested"}
            for name in reporter.REQUIRED_GATES
        }
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(1, code)
        self.assertTrue(any("release_gates" in item for item in result["input_errors"]))

    def test_reviewers_are_distinct_current_and_revision_bound(self) -> None:
        evidence = self.factory.evidence()
        evidence["reviewers"][1]["reviewer_id"] = evidence["reviewers"][0]["reviewer_id"]
        evidence["reviewers"][0]["review_date"] = "2999-01-01"
        evidence["reviewers"][1]["reviewed_artifact_sha256"] = "0" * 64
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertNotEqual(0, code)
        self.assertTrue(any(item.startswith("reviewer:") for item in result["blockers"]))

    def test_future_review_date_alone_blocks_release(self) -> None:
        evidence = self.factory.evidence()
        evidence["reviewers"][0]["review_date"] = "2999-01-01"
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(2, code)

    def test_same_reviewer_cannot_fill_both_roles(self) -> None:
        evidence = self.factory.evidence()
        evidence["reviewers"][1]["reviewer_id"] = evidence["reviewers"][0]["reviewer_id"]
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(2, code)

    def test_open_reviewer_corrections_block(self) -> None:
        evidence = self.factory.evidence()
        evidence["reviewers"][0]["required_corrections"] = [
            {
                "id": "C-1",
                "correction": "Change text.",
                "status": "OPEN",
                "evidence": "",
            }
        ]
        result, _ = reporter.build_report(evidence)
        self.assertFalse(result["released"])

    def test_artifact_hash_mismatch_blocks(self) -> None:
        evidence = self.factory.evidence()
        evidence["artifacts"]["output"]["text"] += " Changed."
        result, _ = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertIn("artifact:output:HASH MISMATCH", result["blockers"])

    def test_mutually_consistent_untrusted_standard_and_checklist_block(self) -> None:
        evidence = self.factory.evidence()
        alternate_standard = self.factory.root / "alternate.pdf"
        alternate_standard.write_bytes(b"alternate-standard")
        alternate_checklist = self.factory.root / "alternate-checklist.yaml"
        checklist = yaml.safe_load(
            self.factory.checklist.read_text(encoding="utf-8")
        )
        checklist["standard"]["sha256"] = sha256_bytes(
            alternate_standard.read_bytes()
        )
        alternate_checklist.write_text(
            yaml.safe_dump(checklist, sort_keys=False), encoding="utf-8"
        )
        evidence["artifacts"]["standard"] = {
            "path": str(alternate_standard),
            "sha256": sha256_bytes(alternate_standard.read_bytes()),
        }
        evidence["artifacts"]["checklist"] = {
            "path": str(alternate_checklist),
            "sha256": sha256_bytes(alternate_checklist.read_bytes()),
        }
        evidence["authorization"]["standard_sha256"] = evidence["artifacts"][
            "standard"
        ]["sha256"]
        digest = reporter.review_digest(evidence)
        for reviewer in evidence["reviewers"]:
            reviewer["reviewed_artifact_sha256"] = digest
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(2, code)
        self.assertTrue(
            any("NOT TRUSTED" in blocker for blocker in result["blockers"])
        )

    def test_rewrite_requires_substantive_change_evidence(self) -> None:
        evidence = self.factory.evidence()
        evidence["change_report"] = []
        result, _ = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertIn("coverage:change-report:INCOMPLETE", result["blockers"])

    def test_safety_content_requires_procedural_rule_and_trace(self) -> None:
        evidence = self.factory.evidence(content_types=["safety"])
        check_ids = {item["check_id"] for item in evidence["checks"]}
        self.assertIn("rule-procedure", check_ids)
        evidence["safety_trace"] = []
        result, _ = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertIn("coverage:safety-trace:INCOMPLETE", result["blockers"])

    def test_human_report_includes_reviewers_and_unresolved_registers(self) -> None:
        evidence = self.factory.evidence()
        result, _ = reporter.build_report(evidence)
        rendered = reporter.render_human(result)
        self.assertIn("## Reviewer records", rendered)
        self.assertIn("## Unresolved items", rendered)

    def test_applicable_check_index_includes_safety_procedure_rule(self) -> None:
        checklist = yaml.safe_load(
            self.factory.checklist.read_text(encoding="utf-8")
        )
        rows = reporter.applicable_check_index(checklist, ["safety"])
        self.assertIn("rule-procedure", {row["id"] for row in rows})

    def test_clean_output_is_only_emitted_after_release(self) -> None:
        evidence = self.factory.evidence(output_mode="clean")
        result, code = reporter.build_report(evidence)
        self.assertTrue(result["clean_output_permitted"])
        self.assertEqual(0, code)
        evidence["checks"][0]["result"] = "FAIL"
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["clean_output_permitted"])
        self.assertEqual(2, code)

    def test_malformed_values_return_input_error_not_traceback(self) -> None:
        evidence = self.factory.evidence()
        evidence["checks"][0]["result"] = []
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertEqual(1, code)
        json.dumps(result)


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_activation_is_explicit_and_minimal(self) -> None:
        skill = (ROOT / "write-asd-ste100" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        _, frontmatter, _ = skill.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("write-asd-ste100", metadata["name"])
        self.assertIn("Use only when the user explicitly requests", metadata["description"])
        self.assertIn("ASD-STE100", metadata["description"])

    def test_skill_documents_fail_closed_helpers_and_mode_axes(self) -> None:
        skill = (ROOT / "write-asd-ste100" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Select one task mode",
            "Select one independent output mode",
            "--emit-template",
            "--emit-coverage-template",
            "--list-applicable-checks",
            "--verify-skill-root",
            "--format clean",
            "actual trained ASD-STE100 reviewer",
            "authorized technical reviewer",
            "do not assemble an operational-looking procedure",
            "use the exact status derived by the report script",
            "write-verifiable-requirements",
            "analyze-competing-hypotheses",
        ):
            self.assertIn(phrase, skill)

    def test_evidence_template_is_incomplete_by_construction(self) -> None:
        template = reporter.evidence_template()
        self.assertNotEqual(reporter.FULL_STATUS, template["requested_status"])
        self.assertEqual([], template["checks"])
        self.assertEqual([], template["word_classifications"])
        self.assertEqual([], template["reviewers"])

    def test_local_skill_root_verifier_passes(self) -> None:
        result, code = reporter.verify_skill_root(ROOT / "write-asd-ste100")
        self.assertEqual(0, code)
        self.assertEqual("PASS", result["status"])


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = EvidenceFactory()

    def tearDown(self) -> None:
        self.factory.cleanup()

    def run_cli(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_report_cli_pass_and_clean_output(self) -> None:
        self.factory.standard = (
            ROOT
            / "write-asd-ste100"
            / "references"
            / "asd-ste100-issue-9.pdf"
        )
        self.factory.checklist = (
            ROOT
            / "write-asd-ste100"
            / "references"
            / "compliance-checklist.yaml"
        )
        reporter.TRUSTED_SKILL_ROOT = ROOT / "write-asd-ste100"
        evidence = self.factory.evidence(output_mode="clean")
        path = self.factory.root / "evidence.yaml"
        path.write_text(
            yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        result = self.run_cli(
            "create_compliance_report.py", str(path), "--format", "clean"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(evidence["artifacts"]["output"]["text"], result.stdout.strip())

    def test_report_cli_rejects_duplicate_keys_without_traceback(self) -> None:
        path = self.factory.root / "duplicate-evidence.yaml"
        path.write_text(
            "schema_version: 2\nschema_version: 1\n", encoding="utf-8"
        )
        result = self.run_cli(
            "create_compliance_report.py", str(path), "--format", "json"
        )
        self.assertEqual(1, result.returncode)
        self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_terminology_cli_blocks_missing_coverage(self) -> None:
        text_path = self.factory.root / "text.txt"
        text_path.write_text("Inspect the flux capacitor.", encoding="utf-8")
        result = self.run_cli(
            "check_project_terms.py",
            "--terms",
            str(self.factory.terminology),
            "--text",
            str(text_path),
            "--domain",
            "fuel",
            "--format",
            "json",
        )
        self.assertEqual(2, result.returncode)
        self.assertIn('"status": "INCOMPLETE"', result.stdout)

    def test_coverage_template_cli_is_fail_closed(self) -> None:
        text_path = self.factory.root / "text.txt"
        text_path.write_text("Inspect the pump.", encoding="utf-8")
        result = self.run_cli(
            "check_project_terms.py",
            "--text",
            str(text_path),
            "--emit-coverage-template",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("REVIEW REQUIRED", result.stdout)


class AcceptanceMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = EvidenceFactory()

    def tearDown(self) -> None:
        self.factory.cleanup()

    def assert_blocked(self, evidence: dict) -> dict:
        result, code = reporter.build_report(evidence)
        self.assertFalse(result["released"])
        self.assertNotEqual(0, code)
        return result

    def test_01_maintenance_procedure(self) -> None:
        evidence = self.factory.evidence(final_text="Disconnect the pump.")
        result, code = reporter.build_report(evidence)
        self.assertTrue(result["released"])
        self.assertEqual(0, code)

    def test_02_descriptive_system_paragraph(self) -> None:
        evidence = self.factory.evidence(
            source_text="The pump supplies fuel.",
            final_text="The pump supplies fuel.",
            content_types=["descriptive"],
        )
        self.assertTrue(reporter.build_report(evidence)[0]["released"])

    def test_03_warning_with_steps(self) -> None:
        evidence = self.factory.evidence(
            source_text="WARNING: Disconnect the pump. Fuel can ignite.",
            final_text="WARNING: Disconnect the pump. Fuel can ignite.",
            content_types=["safety", "procedural"],
        )
        self.assertTrue(reporter.build_report(evidence)[0]["released"])

    def test_04_dictionary_word_nonapproved_meaning(self) -> None:
        evidence = self.factory.evidence()
        evidence["word_classifications"][0]["approved_meaning"] = False
        self.assert_blocked(evidence)

    def test_05_wrong_part_of_speech(self) -> None:
        evidence = self.factory.evidence()
        evidence["word_classifications"][0]["approved_part_of_speech"] = False
        self.assert_blocked(evidence)

    def test_06_necessary_approved_technical_name(self) -> None:
        self.factory.write_terms([term_entry()])
        evidence = self.factory.evidence(
            technical_terms={"fuel": "fuel pump", "pump": "fuel pump"}
        )
        self.assertTrue(reporter.build_report(evidence)[0]["released"])

    def test_07_unapproved_technical_term(self) -> None:
        evidence = self.factory.evidence(
            final_text="Inspect the flux capacitor.",
            technical_terms={"flux": "flux capacitor", "capacitor": "flux capacitor"},
        )
        self.assert_blocked(evidence)

    def test_08_inconsistent_technical_term(self) -> None:
        self.factory.write_terms(
            [
                term_entry("fuel pump"),
                {
                    **term_entry("fuel supply pump"),
                    "definition": "Definition of fuel pump",
                },
            ]
        )
        evidence = self.factory.evidence(
            final_text="Inspect the fuel pump and the fuel supply pump.",
            technical_terms={
                "fuel": "fuel pump",
                "pump": "fuel pump",
                "supply": "fuel supply pump",
            },
        )
        self.assert_blocked(evidence)

    def test_09_ambiguous_pronoun(self) -> None:
        evidence = self.factory.evidence()
        evidence["unresolved_items"]["ambiguities"] = [
            {
                "id": "A-1",
                "source_quote": "Install it.",
                "possible_meanings": ["Install the pump.", "Install the valve."],
                "required_decision": "Identify the component.",
                "authority": "technical reviewer",
                "status": "OPEN",
            }
        ]
        self.assert_blocked(evidence)

    def test_10_excessive_noun_cluster(self) -> None:
        evidence = self.factory.evidence()
        evidence["checks"][0]["result"] = "FAIL"
        evidence["checks"][0]["evidence"] = "Excessive noun cluster found."
        self.assert_blocked(evidence)

    def test_11_sentence_length_violation(self) -> None:
        evidence = self.factory.evidence()
        evidence["checks"][0]["result"] = "FAIL"
        evidence["checks"][0]["evidence"] = "Applicable length rule failed."
        self.assert_blocked(evidence)

    def test_12_passive_construction_review(self) -> None:
        evidence = self.factory.evidence()
        evidence["checks"][0]["result"] = "REVIEW REQUIRED"
        self.assert_blocked(evidence)

    def test_13_missing_unit(self) -> None:
        evidence = self.factory.evidence()
        evidence["technical_integrity"]["facts_preserved"] = "FAIL"
        self.assert_blocked(evidence)

    def test_14_changed_numerical_value(self) -> None:
        evidence = self.factory.evidence(source_text="Set 10 mm.", final_text="Set 12 mm.")
        evidence["change_report"][0]["technical_meaning_preserved"] = "NO"
        self.assert_blocked(evidence)

    def test_15_changed_mandatory_requirement(self) -> None:
        evidence = self.factory.evidence(
            source_text="You must disconnect the pump.",
            final_text="You can disconnect the pump.",
        )
        evidence["change_report"][0]["technical_meaning_preserved"] = "NO"
        self.assert_blocked(evidence)

    def test_16_terminology_source_conflict(self) -> None:
        evidence = self.factory.evidence()
        evidence["unresolved_items"]["terminology"] = [
            {
                "id": "T-1",
                "term": "pump",
                "conflict": "Source and project terminology differ.",
                "authority": "terminology authority",
                "status": "OPEN",
            }
        ]
        self.assert_blocked(evidence)

    def test_17_missing_authorized_reference(self) -> None:
        evidence = self.factory.evidence()
        evidence["artifacts"]["standard"]["path"] = str(
            self.factory.root / "missing.pdf"
        )
        self.assert_blocked(evidence)

    def test_18_missing_human_review(self) -> None:
        evidence = self.factory.evidence()
        evidence["reviewers"] = []
        self.assert_blocked(evidence)

    def test_19_all_gates_pass(self) -> None:
        evidence = self.factory.evidence()
        result, code = reporter.build_report(evidence)
        self.assertTrue(result["released"])
        self.assertEqual(reporter.FULL_STATUS, result["status"])
        self.assertEqual(0, code)

    def test_20_clean_output_before_gates_pass(self) -> None:
        evidence = self.factory.evidence(output_mode="clean")
        evidence["reviewers"] = []
        result = self.assert_blocked(evidence)
        self.assertFalse(result["clean_output_permitted"])


if __name__ == "__main__":
    unittest.main()
