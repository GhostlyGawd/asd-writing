"""Validate approved project terminology against technical text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = {
    "approved_term",
    "definition",
    "term_type",
    "approved_part_of_speech",
    "permitted_inflections",
    "prohibited_synonyms",
    "domain",
    "source_authority",
    "approval_status",
    "approval_date",
    "notes",
}
APPROVED_STATUS = "APPROVED"


class InputError(ValueError):
    """Report invalid input without presenting it as a terminology finding."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from a file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"Cannot load terminology file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError("The terminology file must contain a YAML mapping.")
    return data


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Compile a case-insensitive whole-phrase pattern."""
    words = phrase.strip().split()
    if not words:
        raise InputError("A terminology value cannot be empty.")
    body = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<![\w-]){body}(?![\w-])", re.IGNORECASE)


def occurrences(text: str, phrase: str) -> list[int]:
    """Return one-based line numbers that contain a whole phrase."""
    pattern = phrase_pattern(phrase)
    found: list[int] = []
    for line_number, line in enumerate(text.splitlines() or [text], start=1):
        found.extend([line_number] * len(list(pattern.finditer(line))))
    return found


def validate_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate terminology entry structure and approval metadata."""
    entries = data.get("terms")
    if not isinstance(entries, list):
        raise InputError("The terminology file must contain a 'terms' list.")

    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise InputError(f"Terminology entry {index} must be a mapping.")
        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            raise InputError(
                f"Terminology entry {index} is missing fields: {', '.join(missing)}."
            )
        term = entry["approved_term"]
        if not isinstance(term, str) or not term.strip():
            raise InputError(f"Terminology entry {index} has an empty approved_term.")
        key = term.casefold().strip()
        if key in seen:
            raise InputError(f"Duplicate terminology entry: {term}.")
        seen.add(key)
        for list_field in ("permitted_inflections", "prohibited_synonyms"):
            if not isinstance(entry[list_field], list) or not all(
                isinstance(value, str) and value.strip()
                for value in entry[list_field]
            ):
                raise InputError(
                    f"Terminology entry {term!r} field {list_field} must be a list "
                    "of non-empty strings."
                )
        for text_field in (
            "definition",
            "term_type",
            "approved_part_of_speech",
            "domain",
            "source_authority",
            "approval_status",
        ):
            if not isinstance(entry[text_field], str) or not entry[text_field].strip():
                raise InputError(
                    f"Terminology entry {term!r} field {text_field} cannot be empty."
                )
        if entry["approval_status"].upper() == APPROVED_STATUS:
            if not entry["approval_date"]:
                raise InputError(
                    f"Approved terminology entry {term!r} requires approval_date."
                )
    return entries


def analyze_text(
    entries: list[dict[str, Any]], text: str, candidates: list[str]
) -> dict[str, Any]:
    """Find only deterministic project-terminology problems."""
    findings: list[dict[str, Any]] = []
    candidate_results: list[dict[str, str]] = []
    approved_forms: dict[str, dict[str, Any]] = {}
    known_forms: dict[str, dict[str, Any]] = {}
    used_approved_terms: dict[str, list[int]] = {}

    for entry in entries:
        term = entry["approved_term"].strip()
        forms = [term, *entry["permitted_inflections"]]
        for form in forms:
            known_forms[form.casefold()] = entry
            if entry["approval_status"].upper() == APPROVED_STATUS:
                approved_forms[form.casefold()] = entry

        term_lines: list[int] = []
        for form in forms:
            term_lines.extend(occurrences(text, form))
        if entry["approval_status"].upper() == APPROVED_STATUS and term_lines:
            used_approved_terms[term.casefold()] = sorted(term_lines)
        elif entry["approval_status"].upper() != APPROVED_STATUS and term_lines:
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "TERM_NOT_APPROVED",
                    "term": term,
                    "lines": sorted(term_lines),
                    "message": (
                        f"The text uses {term!r}, but its approval status is "
                        f"{entry['approval_status']}."
                    ),
                    "basis": f"project terminology entry: {term}",
                }
            )

        if entry["approval_status"].upper() == APPROVED_STATUS:
            for synonym in entry["prohibited_synonyms"]:
                synonym_lines = occurrences(text, synonym)
                if synonym_lines:
                    findings.append(
                        {
                            "severity": "BLOCKING",
                            "code": "PROHIBITED_SYNONYM",
                            "term": synonym,
                            "approved_term": term,
                            "lines": synonym_lines,
                            "message": (
                                f"Use approved term {term!r} instead of prohibited "
                                f"synonym {synonym!r}."
                            ),
                            "basis": f"project terminology entry: {term}",
                        }
                    )

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry["approval_status"].upper() != APPROVED_STATUS:
            continue
        group_key = (
            entry["definition"].strip().casefold(),
            entry["domain"].strip().casefold(),
        )
        groups.setdefault(group_key, []).append(entry)
    for group in groups.values():
        used = [
            entry["approved_term"]
            for entry in group
            if entry["approved_term"].casefold() in used_approved_terms
        ]
        if len(used) > 1:
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "INCONSISTENT_APPROVED_TERMS",
                    "terms": used,
                    "lines": sorted(
                        line
                        for term in used
                        for line in used_approved_terms[term.casefold()]
                    ),
                    "message": (
                        "The text uses multiple approved terms for the same definition "
                        f"and domain: {', '.join(used)}."
                    ),
                    "basis": "project terminology consistency",
                }
            )

    for candidate in candidates:
        normalized = candidate.strip().casefold()
        if not normalized:
            raise InputError("Candidate terms cannot be empty.")
        if normalized in approved_forms:
            entry = approved_forms[normalized]
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "PASS",
                    "basis": f"approved project terminology entry: {entry['approved_term']}",
                }
            )
        elif normalized in known_forms:
            entry = known_forms[normalized]
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "FAIL",
                    "basis": (
                        f"project terminology entry {entry['approved_term']} has status "
                        f"{entry['approval_status']}"
                    ),
                }
            )
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "CANDIDATE_NOT_APPROVED",
                    "term": candidate,
                    "lines": occurrences(text, candidate),
                    "message": (
                        f"Candidate term {candidate!r} does not have APPROVED status."
                    ),
                    "basis": f"project terminology entry: {entry['approved_term']}",
                }
            )
        else:
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "FAIL",
                    "basis": "no project terminology entry",
                }
            )
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "UNKNOWN_TERM",
                    "term": candidate,
                    "lines": occurrences(text, candidate),
                    "message": (
                        f"Candidate term {candidate!r} is absent from project terminology."
                    ),
                    "basis": "project terminology file",
                }
            )

    blocking_count = sum(
        finding["severity"] == "BLOCKING" for finding in findings
    )
    return {
        "tool": "check_project_terms",
        "scope": (
            "Project terminology only; this tool does not check the ASD-STE100 "
            "dictionary, grammar, technical accuracy, or complete vocabulary."
        ),
        "status": "FAIL" if blocking_count else "PASS",
        "blocking_count": blocking_count,
        "findings": findings,
        "candidate_results": candidate_results,
    }


def render_human(report: dict[str, Any]) -> str:
    """Render a concise human-readable terminology report."""
    lines = [
        "# Project Terminology Report",
        "",
        f"Status: {report['status']}",
        f"Blocking findings: {report['blocking_count']}",
        "",
        report["scope"],
    ]
    if report["candidate_results"]:
        lines.extend(["", "## Candidate terms", "", "| Candidate | Result | Basis |", "|---|---|---|"])
        for item in report["candidate_results"]:
            lines.append(
                f"| {item['candidate']} | {item['result']} | {item['basis']} |"
            )
    if report["findings"]:
        lines.extend(["", "## Findings", ""])
        for finding in report["findings"]:
            line_text = ", ".join(str(line) for line in finding.get("lines", []))
            lines.append(
                f"- {finding['code']}: {finding['message']} "
                f"(lines: {line_text or 'not present'})"
            )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate text against approved project terminology."
    )
    parser.add_argument("--terms", required=True, type=Path)
    parser.add_argument("--text", required=True, type=Path)
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="A suspected technical term to require in the terminology file; repeatable.",
    )
    parser.add_argument(
        "--format", choices=("json", "human", "both"), default="human"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the terminology check and return a blocking exit status."""
    try:
        args = parse_args(argv)
        entries = validate_entries(load_yaml(args.terms))
        text = args.text.read_text(encoding="utf-8")
        report = analyze_text(entries, text, args.candidate)
    except (InputError, OSError, UnicodeError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 1

    if args.format in {"json", "both"}:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.format == "human":
        print(render_human(report))
    elif args.format == "both":
        print(render_human(report), file=sys.stderr)
    return 2 if report["blocking_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
