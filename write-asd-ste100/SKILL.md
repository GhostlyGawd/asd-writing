---
name: write-asd-ste100
description: Write, rewrite, and review technical content for full compliance with ASD-STE100 Simplified Technical English Issue 9. Use for STE authoring, ASD-STE100 rewriting, controlled technical English, vocabulary checks, compliance reviews, maintenance instructions, operating instructions, warnings, cautions, notes, and technical descriptions.
---

# Write ASD-STE100

Use the complete authorized Issue 9 PDF as the controlling language reference. Treat full
compliance as a release condition, not as a writing target. Never claim ASD or STEMG approval,
certification, or endorsement.

## Confirm inputs and mode

Require the authorized PDF, approved technical source information, approved company and project
terminology, company writing requirements, content type, intended reader, technical domain, and
protected terms/values/identifiers. If an input is absent, permit a draft only. Put
`DRAFT — FULL COMPLIANCE CHECK NOT COMPLETE` above the draft and use the final status
`NOT RELEASED — COMPLIANCE CHECK INCOMPLETE`.

Identify one mode:

- **Write:** Create text only from approved source facts.
- **Rewrite:** Preserve every fact, condition, sequence, quantity, unit, limit, tolerance,
  identifier, part name, safety level, and mandatory/optional meaning.
- **Compliance review:** Report each problem and a proposed correction without changing the text.
- **Rewrite with compliance report:** Return revised text, status, change report, evidence,
  unresolved items, and reviewer actions.
- **Clean output:** Return only released technical text. Refuse this mode until every gate passes.
- **Teaching:** For each important change, give source text, revised text, problem type, an exact
  verified rule or dictionary basis, and a short explanation.

Support procedural, descriptive, maintenance, operating, troubleshooting, safety, note, system,
component, inspection, test, and mixed technical content. Divide mixed content into procedural
and descriptive sections before checking it.

## Use controlling sources

Apply this hierarchy: safety requirements; approved technical source data; approved company
terminology; approved project terminology; Issue 9 writing rules; Issue 9 dictionary; general
English. Never change a technical fact to satisfy a language rule.

Open `references/asd-ste100-issue-9.pdf` and verify its Issue 9 identity before work. Use the PDF
for every exact rule, limit, meaning, part of speech, form, restriction, exception, and dictionary
decision. Use `references/compliance-checklist.yaml` only as an index into the PDF, never as a
substitute. Search the complete dictionary entry for each output word. Do not use memory, an older
issue, a summary, or a general grammar checker as authority. Do not invent citations.

Load `references/project-terminology.yaml`. Use only entries whose approval status is `APPROVED`.
Do not infer approval from frequency. Put a necessary absent or unapproved term in the unresolved
terminology list and block release.

If controlling sources conflict, stop the affected rewrite, identify both sources and the required
authorized decision, and set `NOT RELEASED — COMPLIANCE CHECK FAILED`. If source text is
ambiguous, quote it, list the possible meanings, state the technical decision needed, request
clarification, and block the affected content. Preserve and flag a possible source error.

## Follow the workflow

1. Confirm the controlling references and all required inputs.
2. Identify content type, reader, domain, terminology, and protected content.
3. Separate procedural and descriptive content and find ambiguity before rewriting.
4. Write or rewrite without adding facts.
5. Classify every output word as an Issue 9 dictionary word, approved technical noun, approved
   technical verb, permitted proper noun, permitted abbreviation/identifier, or non-approved word.
6. For each dictionary word, verify its approved meaning, part of speech, form, and restrictions.
7. Check every applicable Issue 9 rule for each sentence, paragraph, sequence, and safety item.
8. Compare the result with the technical source and protected content.
9. Run the terminology checker and all other available deterministic checks. Record only what each
   check actually implements.
10. Record evidence, correct each problem, and repeat all affected checks.
11. Obtain an actual trained ASD-STE100 language review and authorized technical review. Record
    reviewer identifier, role, date, result, corrections, and approval state. Never fabricate review.
12. Apply authorized corrections and repeat the complete final checks.
13. Run the compliance-report script. Release only if it permits the requested status and mode.

Do not skip checks because text appears simple. Do not use synonym variation. Use one term for one
meaning and one meaning for one term when the domain permits it.

## Run deterministic scripts

Run the terminology checker once for JSON and once for a readable report:

```text
python scripts/check_project_terms.py --terms references/project-terminology.yaml --text INPUT.txt --candidate TERM --format json
python scripts/check_project_terms.py --terms references/project-terminology.yaml --text INPUT.txt --candidate TERM --format human
```

Pass each suspected technical term with `--candidate`. The script checks only project terminology:
schema validity, known unapproved terms, absent candidates, prohibited synonyms, and inconsistent
approved terms. It does not check the Issue 9 dictionary or grammar.

Prepare a YAML or JSON evidence file and run:

```text
python scripts/create_compliance_report.py INPUT.yaml --format json
python scripts/create_compliance_report.py INPUT.yaml --format human
```

The report script validates result values, required release gates, change preservation decisions,
reviewer records, status, and clean-output eligibility. It does not perform linguistic or technical
review.

## Record evidence

Use this compliance record:

| Location | Check type | Result | Rule or dictionary basis | Correction | Reviewer | Evidence |
|---|---|---|---|---|---|---|

Use only `PASS`, `FAIL`, `NOT APPLICABLE`, or `REVIEW REQUIRED`. A `FAIL` or
`REVIEW REQUIRED` blocks release. Cite the exact rule, dictionary entry, approved terminology
entry, or technical source with concise checkable evidence.

For rewrites, also use:

| Location | Source text | Revised text | Reason | Rule or dictionary basis | Technical meaning preserved |
|---|---|---|---|---|---|

Use only `YES`, `NO`, or `REVIEW REQUIRED` in the last column. `NO` or
`REVIEW REQUIRED` blocks release.

## Enforce release gates

Require all of these to pass: authorized complete standard available; complete text checked; all
applicable rules checked; every word classified; each dictionary meaning and part of speech
verified; all technical terms approved; automated checks pass; no unresolved language,
terminology, or ambiguity item; all technical and safety facts preserved; trained language reviewer
approval; authorized technical reviewer approval; all corrections applied; and final checks pass.
One open gate blocks release.

Use only these final compliance statuses:

- `FULLY CHECKED — ASD-STE100 ISSUE 9 COMPLIANT`
- `NOT RELEASED — COMPLIANCE CHECK FAILED`
- `NOT RELEASED — COMPLIANCE CHECK INCOMPLETE`
- `NOT RELEASED — TECHNICAL REVIEW REQUIRED`
- `DRAFT — HUMAN ASD-STE100 REVIEW REQUIRED`

Use the fully checked status only after every gate passes. Otherwise, do not describe the text as
compliant, verified, or checked. If a word, rule, exception, term, fact, or meaning cannot be
verified, do not guess: identify what is unresolved, name the authority needed, block release, and
give only a clearly marked draft when useful.
