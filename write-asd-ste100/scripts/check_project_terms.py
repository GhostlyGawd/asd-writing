"""Validate complete word coverage against approved project terminology."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = 2
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
APPROVAL_STATUS_VALUES = {"APPROVED", "PENDING", "REJECTED"}
TERM_TYPE_VALUES = {
    "technical_noun",
    "technical_verb",
    "proper_noun",
    "abbreviation",
    "identifier",
}
PART_OF_SPEECH_VALUES = {
    "noun",
    "verb",
    "proper_noun",
    "abbreviation",
    "identifier",
}
TERM_TYPE_POS = {
    "technical_noun": "noun",
    "technical_verb": "verb",
    "proper_noun": "proper_noun",
    "abbreviation": "abbreviation",
    "identifier": "identifier",
}
APPROVED_STATUS = "APPROVED"
WORD_CLASSIFICATIONS = {
    "ASD_DICTIONARY_WORD",
    "APPROVED_TECHNICAL_NAME",
    "APPROVED_TECHNICAL_VERB",
    "PERMITTED_PROPER_NOUN",
    "PERMITTED_ABBREVIATION_OR_IDENTIFIER",
    "NON_APPROVED_WORD",
}
PROJECT_TERM_CLASSIFICATIONS = WORD_CLASSIFICATIONS - {
    "ASD_DICTIONARY_WORD",
    "NON_APPROVED_WORD",
}
CASE_SENSITIVE_TYPES = {"abbreviation", "identifier"}
TOKEN_PATTERN = re.compile(r"\w+(?:[-'’]\w+)*", re.UNICODE)


class InputError(ValueError):
    """Report invalid input without presenting it as a terminology finding."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def normalize_text(value: str) -> str:
    """Return canonical Unicode text."""
    return unicodedata.normalize("NFC", value)


def normalize_key(value: str, *, case_sensitive: bool = False) -> str:
    """Normalize a term for deterministic lookup."""
    normalized = " ".join(normalize_text(value).strip().split())
    return normalized if case_sensitive else normalized.casefold()


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping and reject duplicate keys."""
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"Cannot load YAML file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"The YAML file {path} must contain a mapping.")
    return data


def lexical_tokens(text: str) -> list[dict[str, Any]]:
    """Return normalized lexical tokens with stable locations."""
    normalized = normalize_text(text)
    tokens: list[dict[str, Any]] = []
    for match in TOKEN_PATTERN.finditer(normalized):
        start = match.start()
        line = normalized.count("\n", 0, start) + 1
        previous_break = normalized.rfind("\n", 0, start)
        column = start - previous_break
        tokens.append(
            {
                "token": match.group(0),
                "location": f"line {line}, column {column}",
                "line": line,
                "column": column,
            }
        )
    return tokens


def phrase_pattern(phrase: str, *, case_sensitive: bool = False) -> re.Pattern[str]:
    """Compile a normalized whole-phrase pattern that can cross line breaks."""
    words = normalize_text(phrase).strip().split()
    if not words:
        raise InputError("A terminology value cannot be empty.")
    body = r"\s+".join(re.escape(word) for word in words)
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(rf"(?<![\w-]){body}(?![\w-])", flags)


def occurrences(
    text: str, phrase: str, *, case_sensitive: bool = False
) -> list[int]:
    """Return unique one-based starting lines for whole-phrase occurrences."""
    normalized = normalize_text(text)
    pattern = phrase_pattern(phrase, case_sensitive=case_sensitive)
    return sorted(
        {
            normalized.count("\n", 0, match.start()) + 1
            for match in pattern.finditer(normalized)
        }
    )


def _require_declared_values(
    data: dict[str, Any], field: str, expected: set[str]
) -> None:
    value = data.get(field)
    if not isinstance(value, list) or set(value) != expected:
        raise InputError(
            f"{field!r} must contain exactly these values: {sorted(expected)}."
        )


def _parse_approval_date(value: Any, *, term: str, approved: bool) -> str | None:
    if value in (None, ""):
        if approved:
            raise InputError(
                f"Approved terminology entry {term!r} requires approval_date."
            )
        return None
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = dt.date.fromisoformat(value)
        except ValueError as exc:
            raise InputError(
                f"Terminology entry {term!r} approval_date must use YYYY-MM-DD."
            ) from exc
    else:
        raise InputError(
            f"Terminology entry {term!r} approval_date must use YYYY-MM-DD or null."
        )
    if parsed > dt.date.today():
        raise InputError(
            f"Terminology entry {term!r} approval_date cannot be in the future."
        )
    return parsed.isoformat()


def _domains_overlap(left: str, right: str) -> bool:
    return left == "all" or right == "all" or left == right


def validate_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the complete terminology schema and reject ambiguous forms."""
    if data.get("schema_version") != SCHEMA_VERSION:
        raise InputError(f"schema_version must be {SCHEMA_VERSION}.")
    _require_declared_values(
        data, "approval_status_values", APPROVAL_STATUS_VALUES
    )
    _require_declared_values(data, "term_type_values", TERM_TYPE_VALUES)
    _require_declared_values(
        data, "approved_part_of_speech_values", PART_OF_SPEECH_VALUES
    )
    entries = data.get("terms")
    if not isinstance(entries, list):
        raise InputError("The terminology file must contain a 'terms' list.")

    validated: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(entries, start=1):
        if not isinstance(raw_entry, dict):
            raise InputError(f"Terminology entry {index} must be a mapping.")
        missing = sorted(REQUIRED_FIELDS - set(raw_entry))
        extra = sorted(set(raw_entry) - REQUIRED_FIELDS)
        if missing:
            raise InputError(
                f"Terminology entry {index} is missing fields: {', '.join(missing)}."
            )
        if extra:
            raise InputError(
                f"Terminology entry {index} has unknown fields: {', '.join(extra)}."
            )
        entry = dict(raw_entry)
        term = entry["approved_term"]
        if not isinstance(term, str) or not term.strip():
            raise InputError(f"Terminology entry {index} has an empty approved_term.")
        entry["approved_term"] = " ".join(normalize_text(term).strip().split())
        term = entry["approved_term"]
        for field in (
            "definition",
            "term_type",
            "approved_part_of_speech",
            "domain",
            "source_authority",
            "approval_status",
        ):
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise InputError(
                    f"Terminology entry {term!r} field {field} cannot be empty."
                )
            if entry[field] != entry[field].strip():
                raise InputError(
                    f"Terminology entry {term!r} field {field} cannot have "
                    "leading or trailing whitespace."
                )
        if not isinstance(entry["notes"], str):
            raise InputError(
                f"Terminology entry {term!r} field notes must be text."
            )
        if entry["approval_status"] not in APPROVAL_STATUS_VALUES:
            raise InputError(
                f"Terminology entry {term!r} has invalid approval_status "
                f"{entry['approval_status']!r}."
            )
        if entry["term_type"] not in TERM_TYPE_VALUES:
            raise InputError(
                f"Terminology entry {term!r} has invalid term_type "
                f"{entry['term_type']!r}."
            )
        if entry["approved_part_of_speech"] not in PART_OF_SPEECH_VALUES:
            raise InputError(
                f"Terminology entry {term!r} has invalid approved_part_of_speech "
                f"{entry['approved_part_of_speech']!r}."
            )
        expected_pos = TERM_TYPE_POS[entry["term_type"]]
        if entry["approved_part_of_speech"] != expected_pos:
            raise InputError(
                f"Terminology entry {term!r} type {entry['term_type']!r} "
                f"requires approved_part_of_speech {expected_pos!r}."
            )
        entry["domain"] = normalize_key(entry["domain"])
        for list_field in ("permitted_inflections", "prohibited_synonyms"):
            values = entry[list_field]
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise InputError(
                    f"Terminology entry {term!r} field {list_field} must be a list "
                    "of non-empty strings."
                )
            entry[list_field] = [
                " ".join(normalize_text(value).strip().split()) for value in values
            ]
        entry["approval_date"] = _parse_approval_date(
            entry["approval_date"],
            term=term,
            approved=entry["approval_status"] == APPROVED_STATUS,
        )
        validated.append(entry)

    forms: list[tuple[str, str, str, str]] = []
    synonyms: list[tuple[str, str, str, str]] = []
    for entry in validated:
        domain = entry["domain"]
        sensitive = entry["term_type"] in CASE_SENSITIVE_TYPES
        for form in [entry["approved_term"], *entry["permitted_inflections"]]:
            key = normalize_key(form, case_sensitive=sensitive)
            forms.append((key, domain, entry["approved_term"], entry["term_type"]))
        for synonym in entry["prohibited_synonyms"]:
            key = normalize_key(synonym, case_sensitive=sensitive)
            synonyms.append((key, domain, entry["approved_term"], entry["term_type"]))

    for index, left in enumerate(forms):
        for right in forms[index + 1 :]:
            if left[0] == right[0] and _domains_overlap(left[1], right[1]):
                raise InputError(
                    f"Terminology form collision between {left[2]!r} and "
                    f"{right[2]!r} in overlapping domains."
                )
    for synonym in synonyms:
        for form in forms:
            if synonym[0] == form[0] and _domains_overlap(synonym[1], form[1]):
                raise InputError(
                    f"Prohibited synonym for {synonym[2]!r} collides with "
                    f"terminology form for {form[2]!r}."
                )
    for index, left in enumerate(synonyms):
        for right in synonyms[index + 1 :]:
            if left[0] == right[0] and _domains_overlap(left[1], right[1]):
                raise InputError(
                    f"Prohibited synonym collision between {left[2]!r} and "
                    f"{right[2]!r} in overlapping domains."
                )
    return validated


def _active_entries(
    entries: list[dict[str, Any]], domain: str
) -> list[dict[str, Any]]:
    normalized_domain = normalize_key(domain)
    return [
        entry
        for entry in entries
        if entry["domain"] in {"all", normalized_domain}
    ]


def _validate_coverage(
    text: str, coverage: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    expected = lexical_tokens(text)
    errors: list[str] = []
    candidates: list[str] = []
    findings: list[dict[str, Any]] = []
    if len(coverage) != len(expected):
        errors.append(
            f"word classification count {len(coverage)} does not match "
            f"lexical token count {len(expected)}"
        )
    for index, token in enumerate(expected, start=1):
        if index > len(coverage):
            break
        row = coverage[index - 1]
        if not isinstance(row, dict):
            errors.append(f"word classification {index} is not a mapping")
            continue
        if row.get("index") != index:
            errors.append(f"word classification {index} has the wrong index")
        if normalize_text(str(row.get("token", ""))) != token["token"]:
            errors.append(f"word classification {index} does not match output token")
        if row.get("location") != token["location"]:
            errors.append(f"word classification {index} has the wrong location")
        classification = row.get("classification")
        if classification not in WORD_CLASSIFICATIONS:
            errors.append(
                f"word classification {index} has invalid classification "
                f"{classification!r}"
            )
            continue
        if row.get("result") not in {"PASS", "FAIL", "REVIEW REQUIRED"}:
            errors.append(f"word classification {index} has invalid result")
        basis = row.get("basis")
        if not isinstance(basis, str) or not basis.strip():
            errors.append(f"word classification {index} requires a basis")
        if classification in PROJECT_TERM_CLASSIFICATIONS:
            term = row.get("term")
            if not isinstance(term, str) or not term.strip():
                errors.append(
                    f"word classification {index} requires its complete project term"
                )
            else:
                candidates.append(term)
        if classification == "NON_APPROVED_WORD" or row.get("result") != "PASS":
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "WORD_CLASSIFICATION_FAILED",
                    "term": token["token"],
                    "lines": [token["line"]],
                    "message": (
                        f"Word {token['token']!r} is not approved by its complete "
                        "classification record."
                    ),
                    "basis": str(basis or "word classification coverage"),
                }
            )
    return expected, sorted(set(candidates), key=str.casefold), findings + [
        {
            "severity": "BLOCKING",
            "code": "CANDIDATE_COVERAGE_INCOMPLETE",
            "term": "",
            "lines": [],
            "message": error,
            "basis": "complete word classification coverage",
        }
        for error in errors
    ]


def _compiled_inventory(
    entries: list[dict[str, Any]],
) -> tuple[
    dict[tuple[str, bool], tuple[dict[str, Any], str]],
    dict[tuple[str, bool], tuple[dict[str, Any], str]],
    list[tuple[re.Pattern[str], bool]],
]:
    forms: dict[tuple[str, bool], tuple[dict[str, Any], str]] = {}
    synonyms: dict[tuple[str, bool], tuple[dict[str, Any], str]] = {}
    alternatives: dict[bool, list[str]] = {False: [], True: []}
    for entry in entries:
        sensitive = entry["term_type"] in CASE_SENSITIVE_TYPES
        for form in [entry["approved_term"], *entry["permitted_inflections"]]:
            key = normalize_key(form, case_sensitive=sensitive)
            forms[(key, sensitive)] = (entry, form)
            alternatives[sensitive].append(form)
        for synonym in entry["prohibited_synonyms"]:
            key = normalize_key(synonym, case_sensitive=sensitive)
            synonyms[(key, sensitive)] = (entry, synonym)
            alternatives[sensitive].append(synonym)
    patterns: list[tuple[re.Pattern[str], bool]] = []
    for sensitive, values in alternatives.items():
        if not values:
            continue
        bodies = []
        for value in sorted(set(values), key=lambda item: (-len(item), item)):
            normalized_value = (
                normalize_key(value, case_sensitive=True)
                if sensitive
                else normalize_key(value)
            )
            words = normalized_value.split()
            bodies.append(r"\s+".join(re.escape(word) for word in words))
        flags = 0 if sensitive else re.IGNORECASE
        patterns.append(
            (
                re.compile(
                    rf"(?<![\w-])(?:{'|'.join(bodies)})(?![\w-])",
                    flags,
                ),
                sensitive,
            )
        )
    return forms, synonyms, patterns


def analyze_text(
    entries: list[dict[str, Any]],
    text: str,
    coverage: list[dict[str, Any]],
    domain: str,
    additional_candidates: list[str] | None = None,
) -> dict[str, Any]:
    """Find deterministic terminology and complete-coverage problems."""
    if not isinstance(domain, str) or not domain.strip():
        raise InputError("An active technical domain is required.")
    if not isinstance(coverage, list):
        raise InputError("Word classification coverage must be a list.")
    normalized_text = normalize_text(text)
    active = _active_entries(entries, domain)
    expected_tokens, candidates, findings = _validate_coverage(
        normalized_text, coverage
    )
    for candidate in additional_candidates or []:
        if not isinstance(candidate, str) or not candidate.strip():
            raise InputError("Candidate terms cannot be empty.")
        candidates.append(candidate)
    candidates = sorted(set(candidates), key=str.casefold)

    forms, synonyms, patterns = _compiled_inventory(active)
    used_approved_terms: dict[str, set[int]] = {}
    finding_keys: set[tuple[str, str]] = set()
    for pattern, sensitive in patterns:
        scan_text = normalized_text if sensitive else normalized_text.casefold()
        scan_pattern = pattern
        if not sensitive:
            bodies = pattern.pattern
            scan_pattern = re.compile(bodies)
        for match in scan_pattern.finditer(scan_text):
            matched = " ".join(match.group(0).split())
            key = normalize_key(matched, case_sensitive=sensitive)
            line = scan_text.count("\n", 0, match.start()) + 1
            form_record = forms.get((key, sensitive))
            synonym_record = synonyms.get((key, sensitive))
            if form_record:
                entry, _ = form_record
                term = entry["approved_term"]
                if entry["approval_status"] == APPROVED_STATUS:
                    used_approved_terms.setdefault(term, set()).add(line)
                else:
                    dedupe = ("TERM_NOT_APPROVED", term)
                    if dedupe not in finding_keys:
                        findings.append(
                            {
                                "severity": "BLOCKING",
                                "code": "TERM_NOT_APPROVED",
                                "term": term,
                                "lines": [line],
                                "message": (
                                    f"The text uses {term!r}, but its approval "
                                    f"status is {entry['approval_status']}."
                                ),
                                "basis": f"project terminology entry: {term}",
                            }
                        )
                        finding_keys.add(dedupe)
            if synonym_record:
                entry, synonym = synonym_record
                if entry["approval_status"] == APPROVED_STATUS:
                    dedupe = ("PROHIBITED_SYNONYM", synonym)
                    if dedupe not in finding_keys:
                        findings.append(
                            {
                                "severity": "BLOCKING",
                                "code": "PROHIBITED_SYNONYM",
                                "term": synonym,
                                "approved_term": entry["approved_term"],
                                "lines": [line],
                                "message": (
                                    f"Use approved term {entry['approved_term']!r} "
                                    f"instead of prohibited synonym {synonym!r}."
                                ),
                                "basis": (
                                    "project terminology entry: "
                                    f"{entry['approved_term']}"
                                ),
                            }
                        )
                        finding_keys.add(dedupe)

    candidate_results: list[dict[str, str]] = []
    for candidate in candidates:
        candidate_match: tuple[dict[str, Any], str] | None = None
        for sensitive in (True, False):
            key = normalize_key(candidate, case_sensitive=sensitive)
            record = forms.get((key, sensitive))
            if record:
                candidate_match = record
                break
        if candidate_match and candidate_match[0]["approval_status"] == APPROVED_STATUS:
            entry = candidate_match[0]
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "PASS",
                    "basis": (
                        "approved project terminology entry: "
                        f"{entry['approved_term']} ({entry['domain']})"
                    ),
                }
            )
        elif candidate_match:
            entry = candidate_match[0]
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "FAIL",
                    "basis": (
                        f"project terminology entry {entry['approved_term']} "
                        f"has status {entry['approval_status']}"
                    ),
                }
            )
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "CANDIDATE_NOT_APPROVED",
                    "term": candidate,
                    "lines": occurrences(
                        normalized_text,
                        candidate,
                        case_sensitive=entry["term_type"] in CASE_SENSITIVE_TYPES,
                    ),
                    "message": (
                        f"Candidate term {candidate!r} does not have APPROVED status."
                    ),
                    "basis": (
                        f"project terminology entry: {entry['approved_term']}"
                    ),
                }
            )
        else:
            candidate_results.append(
                {
                    "candidate": candidate,
                    "result": "FAIL",
                    "basis": (
                        f"no approved project terminology entry in domain "
                        f"{normalize_key(domain)}"
                    ),
                }
            )
            findings.append(
                {
                    "severity": "BLOCKING",
                    "code": "UNKNOWN_TERM",
                    "term": candidate,
                    "lines": occurrences(normalized_text, candidate),
                    "message": (
                        f"Candidate term {candidate!r} is absent from approved "
                        f"project terminology for domain {normalize_key(domain)!r}."
                    ),
                    "basis": "project terminology file and active domain",
                }
            )

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in active:
        if entry["approval_status"] != APPROVED_STATUS:
            continue
        group_key = (
            normalize_key(entry["definition"]),
            entry["domain"],
        )
        groups.setdefault(group_key, []).append(entry)
    for group in groups.values():
        used = [
            entry["approved_term"]
            for entry in group
            if entry["approved_term"] in used_approved_terms
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
                        for line in used_approved_terms[term]
                    ),
                    "message": (
                        "The text uses multiple approved terms for the same "
                        f"definition and domain: {', '.join(used)}."
                    ),
                    "basis": "project terminology consistency",
                }
            )

    blocking_count = sum(
        finding["severity"] == "BLOCKING" for finding in findings
    )
    coverage_complete = not any(
        finding["code"] == "CANDIDATE_COVERAGE_INCOMPLETE"
        for finding in findings
    )
    status = (
        "INCOMPLETE"
        if not coverage_complete
        else "FAIL" if blocking_count else "PASS"
    )
    return {
        "tool": "check_project_terms",
        "scope": (
            "Project terminology and complete word-classification coverage only; "
            "this tool does not decide ASD-STE100 dictionary meanings, grammar, "
            "or technical accuracy."
        ),
        "status": status,
        "blocking_count": blocking_count,
        "coverage_complete": coverage_complete,
        "token_count": len(expected_tokens),
        "active_domain": normalize_key(domain),
        "findings": findings,
        "candidate_results": candidate_results,
    }


def table_cell(value: Any) -> str:
    """Escape a value for a compact Markdown table cell."""
    return (
        str(value if value not in (None, "") else "—")
        .replace("|", r"\|")
        .replace("\n", " ")
    )


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
        lines.extend(
            [
                "",
                "## Candidate terms",
                "",
                "| Candidate | Result | Basis |",
                "|---|---|---|",
            ]
        )
        for item in report["candidate_results"]:
            lines.append(
                f"| {table_cell(item['candidate'])} | "
                f"{table_cell(item['result'])} | {table_cell(item['basis'])} |"
            )
    if report["findings"]:
        lines.extend(["", "## Findings", ""])
        for finding in report["findings"]:
            line_text = ", ".join(
                str(line) for line in finding.get("lines", [])
            )
            lines.append(
                f"- {table_cell(finding['code'])}: "
                f"{table_cell(finding['message'])} "
                f"(lines: {line_text or 'not present'})"
            )
    return "\n".join(lines)


def _load_coverage(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    data = load_yaml(path)
    coverage = data.get("word_classifications")
    if not isinstance(coverage, list):
        raise InputError(
            "The coverage file must contain a 'word_classifications' list."
        )
    return coverage


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate complete word coverage against approved project terminology."
        )
    )
    parser.add_argument("--terms", required=True, type=Path)
    parser.add_argument("--text", required=True, type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help=(
            "An additional technical term to require; this does not replace the "
            "complete --coverage file."
        ),
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
        report = analyze_text(
            entries,
            text,
            _load_coverage(args.coverage),
            args.domain,
            args.candidate,
        )
    except (InputError, OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 1

    if args.format in {"json", "both"}:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.format == "human":
        print(render_human(report))
    elif args.format == "both":
        print(render_human(report), file=sys.stderr)
    return 2 if report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
