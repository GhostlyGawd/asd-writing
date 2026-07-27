"""Validate compliance evidence and release gates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import yaml


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


class InputError(ValueError):
    """Report malformed evidence separately from an open compliance gate."""


def load_data(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON evidence mapping."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"Cannot load evidence file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError("The evidence file must contain a mapping.")
    return data


def require_text(record: dict[str, Any], field: str, context: str) -> str:
    """Return a required non-empty text field."""
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{context} requires non-empty field {field!r}.")
    return value.strip()


def validate_checks(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate compliance-record rows and permitted result values."""
    checks = data.get("checks")
    if not isinstance(checks, list):
        raise InputError("The evidence file must contain a 'checks' list.")
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            raise InputError(f"Check {index} must be a mapping.")
        context = f"Check {index}"
        for field in (
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
        if check["result"] not in RESULT_VALUES:
            raise InputError(
                f"{context} has invalid result {check['result']!r}; "
                f"use one of {sorted(RESULT_VALUES)}."
            )
        require_text(check, "location", context)
        require_text(check, "check_type", context)
        require_text(check, "rule_or_dictionary_basis", context)
        require_text(check, "evidence", context)
    return checks


def validate_changes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate rewrite change-report rows."""
    changes = data.get("change_report", [])
    if not isinstance(changes, list):
        raise InputError("'change_report' must be a list.")
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
        meaning_value = change["technical_meaning_preserved"]
        if isinstance(meaning_value, bool):
            meaning_value = "YES" if meaning_value else "NO"
            change["technical_meaning_preserved"] = meaning_value
        if meaning_value not in MEANING_VALUES:
            raise InputError(
                f"{context} has invalid technical_meaning_preserved value "
                f"{meaning_value!r}."
            )
        require_text(change, "location", context)
        require_text(change, "rule_or_dictionary_basis", context)
    return changes


def validate_gates(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Validate the complete fixed release-gate set."""
    gates = data.get("release_gates")
    if not isinstance(gates, dict):
        raise InputError("The evidence file must contain a 'release_gates' mapping.")
    missing = [gate for gate in REQUIRED_GATES if gate not in gates]
    extra = sorted(set(gates) - set(REQUIRED_GATES))
    if missing:
        raise InputError(f"Missing release gates: {', '.join(missing)}.")
    if extra:
        raise InputError(f"Unknown release gates: {', '.join(extra)}.")
    for gate_name, gate in gates.items():
        if not isinstance(gate, dict):
            raise InputError(f"Release gate {gate_name!r} must be a mapping.")
        if gate.get("result") not in RESULT_VALUES:
            raise InputError(
                f"Release gate {gate_name!r} has invalid result "
                f"{gate.get('result')!r}."
            )
        require_text(gate, "evidence", f"Release gate {gate_name!r}")
    return gates


def validate_reviewers(data: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    """Validate actual reviewer records and return approved roles."""
    reviewers = data.get("reviewers")
    if not isinstance(reviewers, list):
        raise InputError("The evidence file must contain a 'reviewers' list.")
    approved_roles: set[str] = set()
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
        ):
            if field not in reviewer:
                raise InputError(f"{context} is missing field {field!r}.")
        require_text(reviewer, "reviewer_id", context)
        role = require_text(reviewer, "role", context)
        if role not in REQUIRED_REVIEWER_ROLES:
            raise InputError(f"{context} has unsupported role {role!r}.")
        review_date = reviewer["review_date"]
        if isinstance(review_date, dt.date):
            review_date = review_date.isoformat()
            reviewer["review_date"] = review_date
        try:
            dt.date.fromisoformat(str(review_date))
        except ValueError as exc:
            raise InputError(
                f"{context} review_date must use YYYY-MM-DD."
            ) from exc
        if not isinstance(reviewer["required_corrections"], list):
            raise InputError(f"{context} required_corrections must be a list.")
        if (
            reviewer["review_result"] == "APPROVED"
            and reviewer["final_approval_state"] == "APPROVED"
        ):
            approved_roles.add(role)
    return reviewers, approved_roles


def choose_blocked_status(
    checks: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    gates: dict[str, dict[str, str]],
    missing_reviewer_roles: set[str],
) -> str:
    """Choose one permitted non-release status from open evidence."""
    if any(check["result"] == "FAIL" for check in checks) or any(
        gate["result"] == "FAIL" for gate in gates.values()
    ) or any(
        change["technical_meaning_preserved"] == "NO" for change in changes
    ):
        return FAILED_STATUS
    technical_gate_names = {
        "no_technical_ambiguity",
        "technical_facts_preserved",
        "safety_requirements_preserved",
        "technical_reviewer_approved",
    }
    if (
        any(gates[name]["result"] != "PASS" for name in technical_gate_names)
        or "AUTHORIZED_TECHNICAL_REVIEWER" in missing_reviewer_roles
    ):
        return TECHNICAL_REVIEW_STATUS
    if (
        gates["asd_reviewer_approved"]["result"] != "PASS"
        or "ASD-STE100_LANGUAGE_REVIEWER" in missing_reviewer_roles
    ):
        return LANGUAGE_REVIEW_STATUS
    return INCOMPLETE_STATUS


def build_report(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Validate evidence, enforce all release gates, and compute status."""
    checks = validate_checks(data)
    changes = validate_changes(data)
    gates = validate_gates(data)
    reviewers, approved_roles = validate_reviewers(data)
    requested_status = data.get("requested_status", INCOMPLETE_STATUS)
    if requested_status not in STATUS_VALUES:
        raise InputError(
            f"Invalid requested_status {requested_status!r}; "
            f"use one of {sorted(STATUS_VALUES)}."
        )
    output_mode = data.get("output_mode", "report")
    if output_mode not in {"report", "clean", "teaching"}:
        raise InputError("output_mode must be report, clean, or teaching.")

    blockers: list[str] = []
    blockers.extend(
        f"check:{index}:{check['result']}"
        for index, check in enumerate(checks, start=1)
        if check["result"] in {"FAIL", "REVIEW REQUIRED"}
    )
    blockers.extend(
        f"change:{index}:{change['technical_meaning_preserved']}"
        for index, change in enumerate(changes, start=1)
        if change["technical_meaning_preserved"] in {"NO", "REVIEW REQUIRED"}
    )
    blockers.extend(
        f"gate:{name}:{gate['result']}"
        for name, gate in gates.items()
        if gate["result"] != "PASS"
    )
    missing_reviewer_roles = sorted(REQUIRED_REVIEWER_ROLES - approved_roles)
    blockers.extend(f"reviewer:{role}:NOT APPROVED" for role in missing_reviewer_roles)

    all_pass = not blockers
    if all_pass and requested_status == FULL_STATUS:
        status = FULL_STATUS
        released = True
    elif all_pass:
        status = requested_status
        released = False
    else:
        status = choose_blocked_status(
            checks, changes, gates, set(missing_reviewer_roles)
        )
        released = False

    clean_output_permitted = released and output_mode == "clean"
    if output_mode == "clean" and not clean_output_permitted:
        blockers.append("output_mode:clean:BLOCKED")

    report = {
        "tool": "create_compliance_report",
        "scope": (
            "Evidence and release-gate validation only; this tool does not perform "
            "ASD-STE100 language review or technical review."
        ),
        "status": status,
        "released": released,
        "clean_output_permitted": clean_output_permitted,
        "blockers": blockers,
        "checks": checks,
        "change_report": changes,
        "release_gates": gates,
        "reviewers": reviewers,
    }
    return report, 0 if released else 2


def table_cell(value: Any) -> str:
    """Escape a value for a compact Markdown table cell."""
    return str(value if value not in (None, "") else "—").replace("|", "\\|").replace(
        "\n", " "
    )


def render_human(report: dict[str, Any]) -> str:
    """Render the complete evidence in checkable Markdown tables."""
    lines = [
        "# ASD-STE100 Compliance Report",
        "",
        f"Status: {report['status']}",
        f"Released: {'YES' if report['released'] else 'NO'}",
        f"Clean output permitted: {'YES' if report['clean_output_permitted'] else 'NO'}",
        "",
        report["scope"],
        "",
        "## Compliance evidence",
        "",
        "| Location | Check type | Result | Rule or dictionary basis | Correction | Reviewer | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(
            "| "
            + " | ".join(
                table_cell(check[field])
                for field in (
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
    lines.extend(["", "## Release gates", "", "| Gate | Result | Evidence |", "|---|---|---|"])
    for gate_name in REQUIRED_GATES:
        gate = report["release_gates"][gate_name]
        lines.append(
            f"| {table_cell(gate_name)} | {table_cell(gate['result'])} | "
            f"{table_cell(gate['evidence'])} |"
        )
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate ASD-STE100 compliance evidence and release gates."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--format", choices=("json", "human", "both"), default="human"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run report validation and return zero only for released content."""
    try:
        args = parse_args(argv)
        report, exit_code = build_report(load_data(args.input))
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 1

    if args.format in {"json", "both"}:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.format == "human":
        print(render_human(report))
    elif args.format == "both":
        print(render_human(report), file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
