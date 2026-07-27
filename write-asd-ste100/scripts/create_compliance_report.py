"""Derive fail-closed release gates from content-bound compliance evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from check_project_terms import (
    InputError as TerminologyInputError,
    analyze_text,
    lexical_tokens,
    load_yaml,
    validate_entries,
)


SCHEMA_VERSION = 2
RESULT_VALUES = {"PASS", "FAIL", "NOT APPLICABLE", "REVIEW REQUIRED"}
MEANING_VALUES = {"YES", "NO", "REVIEW REQUIRED"}
STATUS_VALUES = {
    "FULLY CHECKED — ASD-STE100 ISSUE 9 COMPLIANT",
    "NOT RELEASED — COMPLIANCE CHECK FAILED",
    "NOT RELEASED — COMPLIANCE CHECK INCOMPLETE",
    "NOT RELEASED — TECHNICAL REVIEW REQUIRED",
    "DRAFT — HUMAN ASD-STE100 REVIEW REQUIRED",
}
FULL_STATUS = "FULLY CHECKED — ASD-STE100 ISSUE 9 COMPLIANT"
FAILED_STATUS = "NOT RELEASED — COMPLIANCE CHECK FAILED"
INCOMPLETE_STATUS = "NOT RELEASED — COMPLIANCE CHECK INCOMPLETE"
TECHNICAL_REVIEW_STATUS = "NOT RELEASED — TECHNICAL REVIEW REQUIRED"
LANGUAGE_REVIEW_STATUS = "DRAFT — HUMAN ASD-STE100 REVIEW REQUIRED"
TASK_MODES = {"write", "rewrite", "review"}
OUTPUT_MODES = {"report", "teaching", "clean"}
CONTENT_TYPES = {
    "procedural",
    "descriptive",
    "maintenance",
    "operating",
    "troubleshooting",
    "safety",
    "note",
    "system",
    "component",
    "inspection",
    "test",
    "mixed",
}
REQUIRED_GATES = (
    "authorized_standard_available",
    "complete_text_checked",
    "all_applicable_rules_checked",
    "every_word_classified",
    "dictionary_meaning_and_pos_verified",
    "technical_terms_approved",
    "automated_checks_pass",
    "no_language_problems",
    "no_terminology_problems",
    "no_technical_ambiguity",
    "technical_facts_preserved",
    "safety_requirements_preserved",
    "asd_reviewer_approved",
    "technical_reviewer_approved",
    "reviewer_corrections_applied",
    "final_checks_pass",
)
REQUIRED_REVIEWER_ROLES = {
    "ASD-STE100_LANGUAGE_REVIEWER",
    "AUTHORIZED_TECHNICAL_REVIEWER",
}
WORD_CLASSIFICATIONS = {
    "ASD_DICTIONARY_WORD",
    "APPROVED_TECHNICAL_NAME",
    "APPROVED_TECHNICAL_VERB",
    "PERMITTED_PROPER_NOUN",
    "PERMITTED_ABBREVIATION_OR_IDENTIFIER",
    "NON_APPROVED_WORD",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
UNRESOLVED_REGISTERS = (
    "language",
    "terminology",
    "ambiguities",
    "source_errors",
)


class InputError(ValueError):
    """Report malformed evidence separately from an open compliance gate."""


def load_data(path: Path) -> dict[str, Any]:
    """Load a duplicate-key-safe YAML or JSON evidence mapping."""
    try:
        return load_yaml(path)
    except TerminologyInputError as exc:
        raise InputError(str(exc)) from exc


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    """Hash exact UTF-8 text."""
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise InputError(f"Cannot read artifact {path}: {exc}") from exc
    return digest.hexdigest()


def require_text(record: dict[str, Any], field: str, context: str) -> str:
    """Return a required non-empty text field."""
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{context} requires non-empty field {field!r}.")
    return value.strip()


def require_sha256(record: dict[str, Any], field: str, context: str) -> str:
    """Return a required lowercase SHA-256 digest."""
    value = require_text(record, field, context)
    if not SHA256_PATTERN.fullmatch(value):
        raise InputError(f"{context} field {field!r} must be a lowercase SHA-256.")
    return value


def parse_date(value: Any, context: str) -> dt.date:
    """Parse a non-future ISO date."""
    if isinstance(value, dt.datetime):
        parsed = value.date()
    elif isinstance(value, dt.date):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = dt.date.fromisoformat(value)
        except ValueError as exc:
            raise InputError(f"{context} must use YYYY-MM-DD.") from exc
    else:
        raise InputError(f"{context} must use YYYY-MM-DD.")
    if parsed > dt.date.today():
        raise InputError(f"{context} cannot be in the future.")
    return parsed


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def review_digest(data: dict[str, Any]) -> str:
    """Bind review to exact source, output, references, checks, and decisions."""
    fields = (
        "schema_version",
        "task_mode",
        "content_types",
        "technical_domain",
        "authorization",
        "artifacts",
        "checks",
        "word_classifications",
        "change_report",
        "technical_integrity",
        "unresolved_items",
        "safety_trace",
    )
    payload = {field: data.get(field) for field in fields}
    canonical = json.dumps(
        _json_safe(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(canonical)


def _applies_to_values(item: dict[str, Any], context: str) -> set[str]:
    value = item.get("applies_to")
    if isinstance(value, str) and value:
        return {value}
    if isinstance(value, list) and value and all(
        isinstance(part, str) and part for part in value
    ):
        return set(value)
    raise InputError(f"{context} requires string or list field 'applies_to'.")


def expected_check_ids(
    checklist: dict[str, Any], content_types: list[str]
) -> set[str]:
    """Derive the complete applicable rule and dictionary check set."""
    if not isinstance(content_types, list) or not content_types:
        raise InputError("content_types must be a non-empty list.")
    selected = set(content_types)
    expected: set[str] = set()
    for section in ("rule_checks", "dictionary_checks"):
        items = checklist.get(section)
        if not isinstance(items, list) or not items:
            raise InputError(f"The checklist requires a non-empty {section!r} list.")
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise InputError(f"{section} item {index} must be a mapping.")
            check_id = require_text(item, "id", f"{section} item {index}")
            require_text(item, "check", f"{section} item {index}")
            require_text(item, "source", f"{section} item {index}")
            applies = _applies_to_values(item, f"{section} item {index}")
            if section == "dictionary_checks" or "all" in applies or selected & applies:
                if check_id in expected:
                    raise InputError(f"Duplicate checklist id {check_id!r}.")
                expected.add(check_id)
    return expected


def _resolve_artifact_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _validate_artifacts(
    data: dict[str, Any], base_dir: Path
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[str],
]:
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        raise InputError("The evidence requires an 'artifacts' mapping.")
    blockers: list[str] = []
    for name in ("source", "output", "standard", "checklist", "terminology"):
        if not isinstance(artifacts.get(name), dict):
            raise InputError(f"Artifact {name!r} must be a mapping.")

    source = artifacts["source"]
    require_text(source, "id", "Source artifact")
    require_text(source, "revision", "Source artifact")
    source_text = require_text(source, "text", "Source artifact")
    source_claim = require_sha256(source, "sha256", "Source artifact")
    if sha256_text(source_text) != source_claim:
        blockers.append("artifact:source:HASH MISMATCH")

    output = artifacts["output"]
    output_text = require_text(output, "text", "Output artifact")
    output_claim = require_sha256(output, "sha256", "Output artifact")
    if sha256_text(output_text) != output_claim:
        blockers.append("artifact:output:HASH MISMATCH")

    loaded: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for name in ("standard", "checklist", "terminology"):
        record = artifacts[name]
        path_value = require_text(record, "path", f"Artifact {name!r}")
        claim = require_sha256(record, "sha256", f"Artifact {name!r}")
        path = _resolve_artifact_path(path_value, base_dir)
        paths[name] = path
        if not path.is_file():
            blockers.append(f"artifact:{name}:MISSING")
            continue
        actual = sha256_file(path)
        if actual != claim:
            blockers.append(f"artifact:{name}:HASH MISMATCH")
        if name != "standard":
            try:
                loaded[name] = load_data(path)
            except InputError as exc:
                blockers.append(f"artifact:{name}:INVALID:{exc}")

    checklist = loaded.get("checklist", {})
    terminology_data = loaded.get("terminology", {})
    entries: list[dict[str, Any]] = []
    if checklist:
        standard = checklist.get("standard")
        if not isinstance(standard, dict):
            blockers.append("artifact:checklist:STANDARD MANIFEST MISSING")
        else:
            if standard.get("issue") != 9:
                blockers.append("artifact:checklist:WRONG STANDARD ISSUE")
            checklist_standard_sha = standard.get("sha256")
            if (
                isinstance(checklist_standard_sha, str)
                and paths.get("standard")
                and paths["standard"].is_file()
                and checklist_standard_sha != sha256_file(paths["standard"])
            ):
                blockers.append("artifact:standard:CHECKLIST HASH MISMATCH")
    if terminology_data:
        try:
            entries = validate_entries(terminology_data)
        except TerminologyInputError as exc:
            blockers.append(f"artifact:terminology:INVALID:{exc}")
    return artifacts, checklist, entries, blockers


def _validate_authorization(
    data: dict[str, Any], artifacts: dict[str, Any]
) -> tuple[bool, str]:
    authorization = data.get("authorization")
    if not isinstance(authorization, dict):
        return False, "No authorization record is present."
    try:
        authority = require_text(
            authorization, "authority_id", "Authorization record"
        )
        parse_date(
            authorization.get("confirmation_date"),
            "Authorization confirmation_date",
        )
        digest = require_sha256(
            authorization, "standard_sha256", "Authorization record"
        )
    except InputError as exc:
        return False, str(exc)
    if authorization.get("status") != "CONFIRMED":
        return False, "Authorization status is not CONFIRMED."
    if digest != artifacts["standard"].get("sha256"):
        return False, "Authorization is not bound to the standard artifact."
    return True, f"Confirmed by {authority} for standard {digest}."


def validate_checks(
    data: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str]]:
    """Validate compliance rows and return their unique IDs."""
    checks = data.get("checks")
    if not isinstance(checks, list):
        raise InputError("The evidence file must contain a 'checks' list.")
    ids: set[str] = set()
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            raise InputError(f"Check {index} must be a mapping.")
        context = f"Check {index}"
        for field in (
            "check_id",
            "location",
            "check_type",
            "result",
            "rule_or_dictionary_basis",
            "correction",
            "reviewer",
            "evidence",
        ):
            if field not in check:
                raise InputError(f"{context} is missing field {field!r}.")
        check_id = require_text(check, "check_id", context)
        if check_id in ids:
            raise InputError(f"Duplicate compliance check id {check_id!r}.")
        ids.add(check_id)
        result = check["result"]
        if not isinstance(result, str) or result not in RESULT_VALUES:
            raise InputError(
                f"{context} has invalid result {result!r}; "
                f"use one of {sorted(RESULT_VALUES)}."
            )
        require_text(check, "location", context)
        require_text(check, "check_type", context)
        require_text(check, "rule_or_dictionary_basis", context)
        require_text(check, "evidence", context)
        if not isinstance(check["correction"], str):
            raise InputError(f"{context} field 'correction' must be text.")
        if not isinstance(check["reviewer"], str):
            raise InputError(f"{context} field 'reviewer' must be text.")
    return checks, ids


def validate_changes(
    data: dict[str, Any], task_mode: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate substantive rewrite change evidence."""
    changes = data.get("change_report")
    if not isinstance(changes, list):
        raise InputError("'change_report' must be a list.")
    blockers: list[str] = []
    if task_mode == "rewrite" and not changes:
        blockers.append("coverage:change-report:INCOMPLETE")
    for index, change in enumerate(changes, start=1):
        if not isinstance(change, dict):
            raise InputError(f"Change row {index} must be a mapping.")
        context = f"Change row {index}"
        for field in (
            "location",
            "source_text",
            "revised_text",
            "reason",
            "rule_or_dictionary_basis",
            "technical_meaning_preserved",
        ):
            if field not in change:
                raise InputError(f"{context} is missing field {field!r}.")
        for field in (
            "location",
            "source_text",
            "revised_text",
            "reason",
            "rule_or_dictionary_basis",
        ):
            require_text(change, field, context)
        meaning = change["technical_meaning_preserved"]
        if isinstance(meaning, bool):
            meaning = "YES" if meaning else "NO"
            change["technical_meaning_preserved"] = meaning
        if not isinstance(meaning, str) or meaning not in MEANING_VALUES:
            raise InputError(
                f"{context} has invalid technical_meaning_preserved "
                f"value {meaning!r}."
            )
        if meaning != "YES":
            blockers.append(f"change:{index}:{meaning}")
    return changes, blockers


def _validate_word_classifications(
    data: dict[str, Any], output_text: str
) -> tuple[list[dict[str, Any]], bool, bool, list[str]]:
    rows = data.get("word_classifications")
    if not isinstance(rows, list):
        raise InputError("'word_classifications' must be a list.")
    tokens = lexical_tokens(output_text)
    blockers: list[str] = []
    coverage_complete = len(rows) == len(tokens) and bool(tokens)
    classifications_pass = coverage_complete
    dictionary_pass = coverage_complete
    if not coverage_complete:
        blockers.append("coverage:word-classifications:INCOMPLETE")
    for index, token in enumerate(tokens, start=1):
        if index > len(rows):
            break
        row = rows[index - 1]
        if not isinstance(row, dict):
            raise InputError(f"Word classification {index} must be a mapping.")
        context = f"Word classification {index}"
        for field in (
            "index",
            "token",
            "location",
            "classification",
            "basis",
            "result",
            "approved_meaning",
            "approved_part_of_speech",
            "term",
        ):
            if field not in row:
                raise InputError(f"{context} is missing field {field!r}.")
        if row["index"] != index:
            coverage_complete = False
            blockers.append(f"word:{index}:INDEX MISMATCH")
        if row["token"] != token["token"] or row["location"] != token["location"]:
            coverage_complete = False
            blockers.append(f"word:{index}:TOKEN OR LOCATION MISMATCH")
        classification = row["classification"]
        if not isinstance(classification, str) or classification not in WORD_CLASSIFICATIONS:
            raise InputError(
                f"{context} has invalid classification {classification!r}."
            )
        require_text(row, "basis", context)
        result = row["result"]
        if not isinstance(result, str) or result not in {
            "PASS",
            "FAIL",
            "REVIEW REQUIRED",
        }:
            raise InputError(f"{context} has invalid result {result!r}.")
        if result != "PASS" or classification == "NON_APPROVED_WORD":
            classifications_pass = False
            blockers.append(f"word:{index}:{result}")
        if classification == "ASD_DICTIONARY_WORD":
            if row["approved_meaning"] is not True:
                dictionary_pass = False
                blockers.append(f"word:{index}:MEANING NOT VERIFIED")
            if row["approved_part_of_speech"] is not True:
                dictionary_pass = False
                blockers.append(f"word:{index}:PART OF SPEECH NOT VERIFIED")
        elif classification not in {
            "NON_APPROVED_WORD",
        }:
            require_text(row, "term", context)
    if len(rows) > len(tokens):
        coverage_complete = False
        blockers.append("coverage:word-classifications:EXTRA ROWS")
    classifications_pass = classifications_pass and coverage_complete
    dictionary_pass = dictionary_pass and coverage_complete
    return rows, classifications_pass, dictionary_pass, blockers


def _validate_integrity(
    data: dict[str, Any]
) -> tuple[dict[str, Any], bool, bool]:
    integrity = data.get("technical_integrity")
    if not isinstance(integrity, dict):
        raise InputError("'technical_integrity' must be a mapping.")
    facts = integrity.get("facts_preserved")
    safety = integrity.get("safety_preserved")
    if facts not in {"PASS", "FAIL", "REVIEW REQUIRED"}:
        raise InputError("technical_integrity.facts_preserved has an invalid value.")
    if safety not in {"PASS", "FAIL", "REVIEW REQUIRED"}:
        raise InputError("technical_integrity.safety_preserved has an invalid value.")
    require_text(
        integrity,
        "source_comparison_evidence",
        "Technical integrity record",
    )
    return integrity, facts == "PASS", safety == "PASS"


def _validate_unresolved(
    data: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, bool]]:
    registers = data.get("unresolved_items")
    if not isinstance(registers, dict):
        raise InputError("'unresolved_items' must be a mapping.")
    extra = sorted(set(registers) - set(UNRESOLVED_REGISTERS))
    if extra:
        raise InputError(f"Unknown unresolved registers: {', '.join(extra)}.")
    open_by_register: dict[str, bool] = {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for name in UNRESOLVED_REGISTERS:
        items = registers.get(name)
        if not isinstance(items, list):
            raise InputError(f"Unresolved register {name!r} must be a list.")
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise InputError(
                    f"Unresolved register {name!r} item {index} must be a mapping."
                )
        normalized[name] = items
        open_by_register[name] = any(
            str(item.get("status", "OPEN")).upper()
            not in {"RESOLVED", "CLOSED", "APPROVED"}
            for item in items
        )
    return normalized, open_by_register


def _validate_safety_trace(
    data: dict[str, Any], content_types: list[str]
) -> tuple[list[dict[str, Any]], bool, list[str]]:
    trace = data.get("safety_trace")
    if not isinstance(trace, list):
        raise InputError("'safety_trace' must be a list.")
    blockers: list[str] = []
    if "safety" in content_types and not trace:
        blockers.append("coverage:safety-trace:INCOMPLETE")
    all_pass = "safety" not in content_types or bool(trace)
    for index, item in enumerate(trace, start=1):
        if not isinstance(item, dict):
            raise InputError(f"Safety trace {index} must be a mapping.")
        context = f"Safety trace {index}"
        for field in (
            "id",
            "source_requirement",
            "source_level",
            "revised_level",
            "condition",
            "command",
            "consequence",
            "technical_review_result",
        ):
            require_text(item, field, context)
        if item["source_level"] != item["revised_level"]:
            all_pass = False
            blockers.append(f"safety:{index}:LEVEL CHANGED")
        if item["technical_review_result"] != "APPROVED":
            all_pass = False
            blockers.append(f"safety:{index}:TECHNICAL REVIEW OPEN")
    return trace, all_pass, blockers


def validate_reviewers(
    data: dict[str, Any], artifact_digest: str
) -> tuple[list[dict[str, Any]], set[str], bool, list[str]]:
    """Validate distinct, current, revision-bound human reviewer records."""
    reviewers = data.get("reviewers")
    if not isinstance(reviewers, list):
        raise InputError("The evidence file must contain a 'reviewers' list.")
    approved_roles: set[str] = set()
    reviewer_ids: set[str] = set()
    corrections_applied = True
    blockers: list[str] = []
    for index, reviewer in enumerate(reviewers, start=1):
        if not isinstance(reviewer, dict):
            raise InputError(f"Reviewer {index} must be a mapping.")
        context = f"Reviewer {index}"
        for field in (
            "reviewer_id",
            "role",
            "review_date",
            "review_result",
            "required_corrections",
            "final_approval_state",
            "reviewed_artifact_sha256",
        ):
            if field not in reviewer:
                raise InputError(f"{context} is missing field {field!r}.")
        reviewer_id = require_text(reviewer, "reviewer_id", context)
        role = require_text(reviewer, "role", context)
        if reviewer_id in reviewer_ids:
            blockers.append(f"reviewer:{reviewer_id}:DUPLICATE ROLE OR RECORD")
        reviewer_ids.add(reviewer_id)
        if role not in REQUIRED_REVIEWER_ROLES:
            raise InputError(f"{context} has unsupported role {role!r}.")
        try:
            reviewer["review_date"] = parse_date(
                reviewer["review_date"], f"{context} review_date"
            ).isoformat()
        except InputError as exc:
            blockers.append(f"reviewer:{reviewer_id}:{exc}")
        digest = reviewer.get("reviewed_artifact_sha256")
        if digest != artifact_digest:
            blockers.append(f"reviewer:{reviewer_id}:ARTIFACT DIGEST MISMATCH")
        corrections = reviewer["required_corrections"]
        if not isinstance(corrections, list):
            raise InputError(f"{context} required_corrections must be a list.")
        reviewer_corrections_applied = True
        for correction_index, correction in enumerate(corrections, start=1):
            if not isinstance(correction, dict):
                raise InputError(
                    f"{context} correction {correction_index} must be a mapping."
                )
            correction_context = f"{context} correction {correction_index}"
            for field in ("id", "correction", "status", "evidence"):
                if field not in correction:
                    raise InputError(
                        f"{correction_context} is missing field {field!r}."
                    )
            require_text(correction, "id", correction_context)
            require_text(correction, "correction", correction_context)
            if correction["status"] != "APPLIED":
                reviewer_corrections_applied = False
            if correction["status"] == "APPLIED":
                require_text(correction, "evidence", correction_context)
        corrections_applied = corrections_applied and reviewer_corrections_applied
        approved = (
            reviewer["review_result"] == "APPROVED"
            and reviewer["final_approval_state"] == "APPROVED"
            and reviewer_corrections_applied
            and digest == artifact_digest
        )
        if approved:
            approved_roles.add(role)
        else:
            blockers.append(f"reviewer:{reviewer_id}:NOT APPROVED")
    missing = REQUIRED_REVIEWER_ROLES - approved_roles
    blockers.extend(f"reviewer:{role}:MISSING APPROVAL" for role in sorted(missing))
    return reviewers, approved_roles, corrections_applied, blockers


def _gate(result: bool, evidence: str, *, review: bool = False) -> dict[str, str]:
    return {
        "result": "PASS" if result else ("REVIEW REQUIRED" if review else "FAIL"),
        "evidence": evidence,
    }


def _invalid_report(message: str) -> tuple[dict[str, Any], int]:
    report = {
        "tool": "create_compliance_report",
        "scope": (
            "Evidence consistency and release-gate derivation only; this tool does "
            "not perform ASD-STE100 language review, prove reviewer identity, "
            "establish reference authorization, or perform technical review."
        ),
        "status": INCOMPLETE_STATUS,
        "released": False,
        "clean_output_permitted": False,
        "review_artifact_sha256": None,
        "input_errors": [message],
        "blockers": [f"input:{message}"],
        "checks": [],
        "word_classifications": [],
        "change_report": [],
        "unresolved_items": {name: [] for name in UNRESOLVED_REGISTERS},
        "safety_trace": [],
        "release_gates": {
            name: {
                "result": "REVIEW REQUIRED",
                "evidence": "Input validation did not complete.",
            }
            for name in REQUIRED_GATES
        },
        "reviewers": [],
        "final_text": None,
    }
    return report, 1


def _choose_blocked_status(
    gates: dict[str, dict[str, str]], checks: list[dict[str, Any]]
) -> str:
    if any(check["result"] == "FAIL" for check in checks):
        return FAILED_STATUS
    if any(
        gates[name]["result"] != "PASS"
        for name in (
            "no_technical_ambiguity",
            "technical_facts_preserved",
            "safety_requirements_preserved",
            "technical_reviewer_approved",
        )
    ):
        return TECHNICAL_REVIEW_STATUS
    if gates["asd_reviewer_approved"]["result"] != "PASS":
        return LANGUAGE_REVIEW_STATUS
    if any(gate["result"] == "FAIL" for gate in gates.values()):
        return FAILED_STATUS
    return INCOMPLETE_STATUS


def _build_report(
    data: dict[str, Any], base_dir: Path
) -> tuple[dict[str, Any], int]:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise InputError(f"schema_version must be {SCHEMA_VERSION}.")
    if "release_gates" in data:
        raise InputError(
            "Input field 'release_gates' is prohibited; gates are derived from "
            "content-bound evidence."
        )
    task_mode = data.get("task_mode")
    output_mode = data.get("output_mode")
    requested_status = data.get("requested_status", INCOMPLETE_STATUS)
    if task_mode not in TASK_MODES:
        raise InputError(f"task_mode must be one of {sorted(TASK_MODES)}.")
    if output_mode not in OUTPUT_MODES:
        raise InputError(f"output_mode must be one of {sorted(OUTPUT_MODES)}.")
    if requested_status not in STATUS_VALUES:
        raise InputError(
            f"requested_status must be one of {sorted(STATUS_VALUES)}."
        )
    content_types = data.get("content_types")
    if not isinstance(content_types, list) or not content_types:
        raise InputError("content_types must be a non-empty list.")
    if len(set(content_types)) != len(content_types):
        raise InputError("content_types cannot contain duplicates.")
    invalid_types = sorted(
        item
        for item in content_types
        if not isinstance(item, str) or item not in CONTENT_TYPES
    )
    if invalid_types:
        raise InputError(f"Unsupported content types: {invalid_types}.")
    if "mixed" in content_types and not {
        "procedural",
        "descriptive",
    }.issubset(content_types):
        raise InputError(
            "Mixed content must also identify procedural and descriptive sections."
        )
    technical_domain = require_text(
        data, "technical_domain", "Evidence record"
    )

    artifacts, checklist, entries, blockers = _validate_artifacts(data, base_dir)
    source_text = artifacts["source"]["text"]
    output_text = artifacts["output"]["text"]
    authorization_ok, authorization_evidence = _validate_authorization(
        data, artifacts
    )
    references_ok = (
        authorization_ok
        and not any(blocker.startswith("artifact:") for blocker in blockers)
        and bool(checklist)
    )

    checks, observed_check_ids = validate_checks(data)
    expected_ids = expected_check_ids(checklist, content_types) if checklist else set()
    missing_checks = sorted(expected_ids - observed_check_ids)
    extra_checks = sorted(observed_check_ids - expected_ids)
    if missing_checks:
        blockers.append("coverage:applicable-checks:INCOMPLETE")
    if extra_checks:
        blockers.append("coverage:applicable-checks:UNEXPECTED")
    check_coverage_complete = bool(expected_ids) and not missing_checks and not extra_checks
    all_checks_pass = check_coverage_complete and all(
        check["result"] == "PASS" for check in checks
    )
    blockers.extend(
        f"check:{check['check_id']}:{check['result']}"
        for check in checks
        if check["result"] != "PASS"
    )

    changes, change_blockers = validate_changes(data, task_mode)
    blockers.extend(change_blockers)
    changes_pass = not change_blockers
    word_rows, words_pass, dictionary_pass, word_blockers = (
        _validate_word_classifications(data, output_text)
    )
    blockers.extend(word_blockers)

    terminology_report = analyze_text(
        entries,
        output_text,
        word_rows,
        technical_domain,
    )
    terminology_pass = terminology_report["status"] == "PASS"
    blockers.extend(
        f"terminology:{item['code']}:{item.get('term', '')}"
        for item in terminology_report["findings"]
    )

    integrity, facts_pass, safety_integrity_pass = _validate_integrity(data)
    if not facts_pass:
        blockers.append(
            f"technical-integrity:facts:{integrity['facts_preserved']}"
        )
    if not safety_integrity_pass:
        blockers.append(
            f"technical-integrity:safety:{integrity['safety_preserved']}"
        )
    unresolved, open_registers = _validate_unresolved(data)
    for name, is_open in open_registers.items():
        if is_open:
            blockers.append(f"unresolved:{name}:OPEN")
    safety_trace, safety_trace_pass, safety_blockers = _validate_safety_trace(
        data, content_types
    )
    blockers.extend(safety_blockers)

    artifact_digest = review_digest(data)
    reviewers, approved_roles, corrections_applied, reviewer_blockers = (
        validate_reviewers(data, artifact_digest)
    )
    blockers.extend(reviewer_blockers)
    language_reviewer_pass = (
        "ASD-STE100_LANGUAGE_REVIEWER" in approved_roles
    )
    technical_reviewer_pass = (
        "AUTHORIZED_TECHNICAL_REVIEWER" in approved_roles
    )
    output_hash_pass = (
        sha256_text(output_text) == artifacts["output"]["sha256"]
    )
    source_hash_pass = (
        sha256_text(source_text) == artifacts["source"]["sha256"]
    )
    word_coverage_complete = (
        len(word_rows) == len(lexical_tokens(output_text))
        and bool(word_rows)
        and not any("TOKEN OR LOCATION MISMATCH" in item for item in blockers)
        and not any("INDEX MISMATCH" in item for item in blockers)
    )
    no_language_problems = (
        all_checks_pass
        and words_pass
        and not open_registers["language"]
    )
    no_terminology_problems = (
        terminology_pass and not open_registers["terminology"]
    )
    no_ambiguity = not open_registers["ambiguities"]
    facts_gate_pass = (
        facts_pass
        and changes_pass
        and not open_registers["source_errors"]
        and source_hash_pass
    )
    safety_gate_pass = (
        safety_integrity_pass and safety_trace_pass and technical_reviewer_pass
    )

    gates: dict[str, dict[str, str]] = {
        "authorized_standard_available": _gate(
            references_ok,
            authorization_evidence
            if references_ok
            else "Reference presence, digest, identity, or authorization is open.",
            review=not authorization_ok,
        ),
        "complete_text_checked": _gate(
            output_hash_pass and word_coverage_complete and check_coverage_complete,
            (
                f"Output digest {artifacts['output']['sha256']}; "
                f"{len(word_rows)} classified lexical tokens; "
                f"{len(observed_check_ids)} applicable check rows."
            ),
        ),
        "all_applicable_rules_checked": _gate(
            all_checks_pass,
            (
                f"Expected {len(expected_ids)} checklist IDs; "
                f"observed {len(observed_check_ids)}; "
                f"missing {missing_checks}; unexpected {extra_checks}."
            ),
        ),
        "every_word_classified": _gate(
            words_pass and word_coverage_complete,
            (
                f"Exact token coverage: {len(word_rows)} evidence rows for "
                f"{len(lexical_tokens(output_text))} lexical tokens."
            ),
        ),
        "dictionary_meaning_and_pos_verified": _gate(
            dictionary_pass,
            "Each dictionary-classified token requires approved meaning and part-of-speech flags.",
        ),
        "technical_terms_approved": _gate(
            terminology_pass,
            (
                f"Project terminology result {terminology_report['status']} "
                f"for domain {technical_domain!r}."
            ),
        ),
        "automated_checks_pass": _gate(
            references_ok and terminology_pass,
            "Reference-integrity and project-terminology checks completed.",
        ),
        "no_language_problems": _gate(
            no_language_problems,
            "Applicable rule rows, word rows, and language register are closed.",
        ),
        "no_terminology_problems": _gate(
            no_terminology_problems,
            "Terminology checker and unresolved terminology register are closed.",
        ),
        "no_technical_ambiguity": _gate(
            no_ambiguity,
            "Ambiguity register contains no open item.",
            review=not no_ambiguity,
        ),
        "technical_facts_preserved": _gate(
            facts_gate_pass,
            integrity["source_comparison_evidence"],
            review=not facts_gate_pass,
        ),
        "safety_requirements_preserved": _gate(
            safety_gate_pass,
            (
                f"Safety integrity {integrity['safety_preserved']}; "
                f"{len(safety_trace)} safety trace rows."
            ),
            review=not safety_gate_pass,
        ),
        "asd_reviewer_approved": _gate(
            language_reviewer_pass,
            "Revision-bound trained-language-reviewer record.",
            review=not language_reviewer_pass,
        ),
        "technical_reviewer_approved": _gate(
            technical_reviewer_pass,
            "Revision-bound authorized-technical-reviewer record.",
            review=not technical_reviewer_pass,
        ),
        "reviewer_corrections_applied": _gate(
            corrections_applied and language_reviewer_pass and technical_reviewer_pass,
            "All recorded reviewer corrections are APPLIED with evidence.",
            review=not corrections_applied,
        ),
        "final_checks_pass": {
            "result": "REVIEW REQUIRED",
            "evidence": "Computed after all other gates.",
        },
    }
    gates["final_checks_pass"] = _gate(
        all(gates[name]["result"] == "PASS" for name in REQUIRED_GATES[:-1]),
        (
            f"Final evidence bundle {artifact_digest} passed all preceding "
            "derived gates."
        ),
    )
    blockers.extend(
        f"gate:{name}:{gate['result']}"
        for name, gate in gates.items()
        if gate["result"] != "PASS"
    )
    blockers = list(dict.fromkeys(blockers))
    all_pass = all(gate["result"] == "PASS" for gate in gates.values())
    released = all_pass and requested_status == FULL_STATUS
    status = (
        FULL_STATUS
        if released
        else requested_status
        if all_pass
        else _choose_blocked_status(gates, checks)
    )
    clean_output_permitted = released and output_mode == "clean"
    if output_mode == "clean" and not clean_output_permitted:
        blockers.append("output_mode:clean:BLOCKED")

    report = {
        "tool": "create_compliance_report",
        "scope": (
            "Evidence consistency and release-gate derivation only; this tool does "
            "not perform ASD-STE100 language review, prove reviewer identity, "
            "establish reference authorization, or perform technical review."
        ),
        "status": status,
        "released": released,
        "clean_output_permitted": clean_output_permitted,
        "review_artifact_sha256": artifact_digest,
        "input_errors": [],
        "blockers": blockers,
        "task_mode": task_mode,
        "output_mode": output_mode,
        "content_types": content_types,
        "technical_domain": technical_domain,
        "checks": checks,
        "word_classifications": word_rows,
        "change_report": changes,
        "terminology_report": terminology_report,
        "unresolved_items": unresolved,
        "safety_trace": safety_trace,
        "release_gates": gates,
        "reviewers": reviewers,
        "final_text": output_text,
    }
    return report, 0 if released else 2


def build_report(
    data: dict[str, Any], base_dir: Path | None = None
) -> tuple[dict[str, Any], int]:
    """Return a serializable report for valid or malformed evidence."""
    try:
        if not isinstance(data, dict):
            raise InputError("The evidence must be a mapping.")
        return _build_report(data, (base_dir or Path.cwd()).resolve())
    except (
        InputError,
        TerminologyInputError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
        KeyError,
    ) as exc:
        return _invalid_report(str(exc))


def table_cell(value: Any) -> str:
    """Escape a value for a compact Markdown table cell."""
    return (
        str(value if value not in (None, "") else "—")
        .replace("|", r"\|")
        .replace("\n", " ")
    )


def _render_mapping_rows(
    lines: list[str], items: list[dict[str, Any]]
) -> None:
    for item in items:
        lines.append(f"- `{table_cell(json.dumps(_json_safe(item), ensure_ascii=False))}`")


def render_human(report: dict[str, Any]) -> str:
    """Render complete evidence and handoff records in Markdown."""
    lines = [
        "# ASD-STE100 Compliance Report",
        "",
        f"Status: {report['status']}",
        f"Released: {'YES' if report['released'] else 'NO'}",
        f"Clean output permitted: {'YES' if report['clean_output_permitted'] else 'NO'}",
        f"Review artifact SHA-256: {report.get('review_artifact_sha256') or '—'}",
        "",
        report["scope"],
        "",
        "## Compliance evidence",
        "",
        "| ID | Location | Check type | Result | Rule or dictionary basis | Correction | Reviewer | Evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(
            "| "
            + " | ".join(
                table_cell(check[field])
                for field in (
                    "check_id",
                    "location",
                    "check_type",
                    "result",
                    "rule_or_dictionary_basis",
                    "correction",
                    "reviewer",
                    "evidence",
                )
            )
            + " |"
        )
    if report["change_report"]:
        lines.extend(
            [
                "",
                "## Change report",
                "",
                "| Location | Source text | Revised text | Reason | Rule or dictionary basis | Technical meaning preserved |",
                "|---|---|---|---|---|---|",
            ]
        )
        for change in report["change_report"]:
            lines.append(
                "| "
                + " | ".join(
                    table_cell(change[field])
                    for field in (
                        "location",
                        "source_text",
                        "revised_text",
                        "reason",
                        "rule_or_dictionary_basis",
                        "technical_meaning_preserved",
                    )
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Unresolved items",
            "",
        ]
    )
    for name in UNRESOLVED_REGISTERS:
        lines.append(f"### {name.replace('_', ' ').title()}")
        lines.append("")
        items = report["unresolved_items"].get(name, [])
        if items:
            _render_mapping_rows(lines, items)
        else:
            lines.append("- None.")
        lines.append("")
    lines.extend(
        [
            "## Reviewer records",
            "",
            "| Reviewer | Role | Date | Result | Final approval | Artifact SHA-256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for reviewer in report["reviewers"]:
        lines.append(
            "| "
            + " | ".join(
                table_cell(reviewer[field])
                for field in (
                    "reviewer_id",
                    "role",
                    "review_date",
                    "review_result",
                    "final_approval_state",
                    "reviewed_artifact_sha256",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Release gates",
            "",
            "| Gate | Result | Evidence |",
            "|---|---|---|",
        ]
    )
    for gate_name in REQUIRED_GATES:
        gate = report["release_gates"][gate_name]
        lines.append(
            f"| {table_cell(gate_name)} | {table_cell(gate['result'])} | "
            f"{table_cell(gate['evidence'])} |"
        )
    if report.get("input_errors"):
        lines.extend(["", "## Input errors", ""])
        lines.extend(f"- {error}" for error in report["input_errors"])
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    return "\n".join(lines)


def evidence_template() -> dict[str, Any]:
    """Return a fail-closed starter contract without fabricated evidence."""
    return {
        "schema_version": SCHEMA_VERSION,
        "task_mode": "rewrite",
        "output_mode": "report",
        "requested_status": INCOMPLETE_STATUS,
        "content_types": ["procedural"],
        "technical_domain": "REQUIRED",
        "authorization": {
            "authority_id": "REQUIRED ACTUAL AUTHORITY",
            "confirmation_date": dt.date.today().isoformat(),
            "standard_sha256": "REQUIRED",
            "status": "REVIEW REQUIRED",
        },
        "artifacts": {
            "source": {
                "id": "REQUIRED",
                "revision": "REQUIRED",
                "text": "REQUIRED",
                "sha256": "REQUIRED",
            },
            "output": {"text": "REQUIRED", "sha256": "REQUIRED"},
            "standard": {
                "path": "references/asd-ste100-issue-9.pdf",
                "sha256": "REQUIRED",
            },
            "checklist": {
                "path": "references/compliance-checklist.yaml",
                "sha256": "REQUIRED",
            },
            "terminology": {
                "path": "PROJECT-CONTROLLED-TERMINOLOGY.yaml",
                "sha256": "REQUIRED",
            },
        },
        "checks": [],
        "word_classifications": [],
        "change_report": [],
        "technical_integrity": {
            "facts_preserved": "REVIEW REQUIRED",
            "safety_preserved": "REVIEW REQUIRED",
            "source_comparison_evidence": "REQUIRED",
        },
        "unresolved_items": {name: [] for name in UNRESOLVED_REGISTERS},
        "safety_trace": [],
        "reviewers": [],
    }


def verify_skill_root(
    root: Path, compare_root: Path | None = None
) -> tuple[dict[str, Any], int]:
    """Verify required structure, standard identity, and optional install parity."""
    required = (
        "SKILL.md",
        "agents/openai.yaml",
        "references/asd-ste100-issue-9.pdf",
        "references/project-terminology.yaml",
        "references/compliance-checklist.yaml",
        "scripts/check_project_terms.py",
        "scripts/create_compliance_report.py",
    )
    root = root.resolve()
    findings: list[str] = []
    for relative in required:
        if not (root / relative).is_file():
            findings.append(f"MISSING:{relative}")
    if not findings:
        try:
            checklist = load_data(root / "references/compliance-checklist.yaml")
            standard_sha = sha256_file(
                root / "references/asd-ste100-issue-9.pdf"
            )
            if checklist.get("standard", {}).get("sha256") != standard_sha:
                findings.append("STANDARD_DIGEST_MISMATCH")
            validate_entries(
                load_data(root / "references/project-terminology.yaml")
            )
        except (InputError, TerminologyInputError) as exc:
            findings.append(f"INVALID:{exc}")
    compared: list[str] = []
    if compare_root is not None:
        compare_root = compare_root.resolve()
        for relative in required:
            source = root / relative
            installed = compare_root / relative
            if source.is_file() and installed.is_file():
                compared.append(relative)
                if sha256_file(source) != sha256_file(installed):
                    findings.append(f"PARITY_MISMATCH:{relative}")
            elif source.is_file() != installed.is_file():
                findings.append(f"PARITY_MISSING:{relative}")
    result = {
        "tool": "create_compliance_report",
        "operation": "verify_skill_root",
        "root": str(root),
        "compare_root": str(compare_root) if compare_root else None,
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "compared_files": compared,
    }
    return result, 0 if not findings else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse report, template, and installation-verification arguments."""
    parser = argparse.ArgumentParser(
        description="Derive ASD-STE100 release gates from bound evidence."
    )
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument(
        "--format", choices=("json", "human", "both", "clean"), default="human"
    )
    parser.add_argument("--emit-template", action="store_true")
    parser.add_argument("--verify-skill-root", type=Path)
    parser.add_argument("--compare-skill-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run report validation or skill-root verification."""
    args = parse_args(argv)
    if args.emit_template:
        print(yaml.safe_dump(evidence_template(), sort_keys=False, allow_unicode=True))
        return 0
    if args.verify_skill_root:
        result, exit_code = verify_skill_root(
            args.verify_skill_root, args.compare_skill_root
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return exit_code
    if args.input is None:
        print("INPUT ERROR: an evidence file is required.", file=sys.stderr)
        return 1
    try:
        data = load_data(args.input)
    except InputError as exc:
        report, exit_code = _invalid_report(str(exc))
    else:
        report, exit_code = build_report(data, args.input.parent)

    if args.format == "clean":
        if report["clean_output_permitted"]:
            print(report["final_text"])
            return 0
        print(render_human(report), file=sys.stderr)
        return 2 if exit_code != 1 else 1
    if args.format in {"json", "both"}:
        print(json.dumps(_json_safe(report), indent=2, ensure_ascii=False))
    if args.format == "human":
        print(render_human(report))
    elif args.format == "both":
        print(render_human(report), file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
