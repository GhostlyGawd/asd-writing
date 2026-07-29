---
name: write-asd-ste100
description: Write, rewrite, and review technical content for full compliance with ASD-STE100 Simplified Technical English Issue 9. Use only when the user explicitly requests ASD-STE100, Simplified Technical English, STE, controlled technical English, or an STE vocabulary, grammar, or compliance check; then support maintenance and operating instructions, warnings, cautions, notes, and technical descriptions.
---

# Write ASD-STE100

Use the complete authorized Issue 9 PDF as the controlling language reference. Treat full
compliance as a release condition. Never claim ASD or STEMG approval, certification, or
endorsement. Never treat automated checks or AI review as a substitute for the two required human
reviewers.

Resolve the directory containing this file as `<SKILL_ROOT>`. Use absolute paths based on that
directory when running bundled scripts or opening references.

## Confirm inputs and select modes

Require the authorized PDF, approved source information, company requirements, a project-controlled
terminology file, content type, intended reader, technical domain, and protected terms, values, and
identifiers. If an input is absent, put `DRAFT — FULL COMPLIANCE CHECK NOT COMPLETE` above any
draft and use `NOT RELEASED — COMPLIANCE CHECK INCOMPLETE` as its final status.

Select one task mode:

- `write`: Create text only from approved source facts.
- `rewrite`: Preserve every fact, condition, sequence, quantity, unit, limit, tolerance, identifier,
  part name, safety level, and mandatory or optional meaning.
- `review`: Report each problem and a proposed correction without silently changing the text.

Select one independent output mode:

- `report`: Return technical text, status, changes, evidence, unresolved items, and reviewer actions.
- `teaching`: Add source text, revised text, problem type, exact verified basis, and explanation.
- `clean`: Return only final technical text. Refuse it until the report script permits release.

Identify all applicable content labels. For mixed content, label both procedural and descriptive
sections. Add `safety` when a warning, caution, or other safety instruction occurs.

## Apply controlling sources

Use this hierarchy: safety requirements; approved technical source data; approved company
terminology; approved project terminology; Issue 9 writing rules; Issue 9 dictionary; general
English. Never change a technical fact to satisfy a language rule.

Open `<SKILL_ROOT>/references/asd-ste100-issue-9.pdf`. Verify its Issue 9 identity and digest before
work. Use `<SKILL_ROOT>/references/compliance-checklist.yaml` only as an index into that PDF. Read
each complete cited rule and exception. Search the complete dictionary entry for every output word.
Do not use memory, an older issue, a summary, or a general grammar checker as authority. Do not
invent citations.

Treat `<SKILL_ROOT>/references/project-terminology.yaml` as a template only. Copy it to a
project-controlled location, obtain actual approvals, and pass that copy to the scripts. Do not
modify the installed template. Use only `APPROVED` entries for the active domain. Preserve absent
or unapproved necessary terms in the unresolved terminology register and block release.

If controlling sources conflict, stop the affected rewrite, identify both sources and the
authorized decision needed, and set a `NOT RELEASED` status. For ambiguity, quote the source, list
possible meanings, identify the required authority, and keep the item open. Preserve and flag
possible source errors.

If ambiguity changes an action, object, condition, endpoint, sequence, safety control, or mandatory
meaning, do not assemble an operational-looking procedure with guessed ordering or bracketed
substitutions. Return the unchanged source segment and isolated, non-executable authoring fragments
with targeted resolution questions. Do not convert “wait until it cools” to “wait until it is
cool” unless the technical source confirms that endpoint.

Handle proprietary, personal, export-controlled, or safety-sensitive source material only in
locations and tools approved by the organization. Do not upload, disclose, or retain it beyond the
authorized workflow.

## Follow the workflow

1. Confirm references, inputs, task mode, output mode, reader, domain, content labels, and protected
   content.
2. Separate mixed content and identify ambiguity, source errors, and controlling-source conflicts.
3. Write or rewrite without adding facts.
4. Generate a complete fail-closed word ledger. For each token, verify its classification, basis,
   result, and location. For each dictionary word, verify meaning, part of speech, form, and
   restrictions. For each project term, record the complete term and approval entry. Deduplicate
   the token list to batch dictionary lookups, and open each applicable dictionary entry once per
   batch. Then apply the verified entry to every occurrence and check each occurrence in context.
   Batching reduces repeated reference reads only. It does not automate semantic approval, permit
   skipped occurrences, or replace the complete word ledger.
5. Get the hash-verified applicable-check index. Check every applicable rule for every sentence,
   paragraph, sequence, and safety item against the complete PDF.
6. Compare source and output. Record substantive rewrite changes, technical integrity, protected
   content, and one safety trace per safety item.
7. Run the terminology checker. Resolve every finding and rerun all affected checks.
8. Generate the report. Its first blocked run supplies the review-artifact digest.
9. Give that exact source/output/evidence bundle and digest to an actual trained ASD-STE100 reviewer
   and an authorized technical reviewer. Use different reviewer identifiers.
10. Record corrections as structured items. Apply them, update all affected evidence, regenerate
    the digest, obtain approval for that exact revision, and rerun final checks.
11. Release only when every derived gate is `PASS`. Use `clean` only when the script emits the final
    text successfully.

Use this status precedence when more than one gate is open: a failed language check; required
technical decision or review; required ASD-STE100 human review; otherwise incomplete evidence or
inputs. Before a report exists, use the incomplete status for missing required inputs. After report
generation, use the exact status derived by the report script.

For long content, process stable source sections in manageable batches, but merge them into one
ordered final output, one complete token ledger, and one applicable-check ledger. Reconcile
cross-section terminology, references, sequence, and protected values. Never release a partial
batch as the complete document.

## Route related work

- Use `write-verifiable-requirements` first when ambiguity concerns requirement intent, allocation,
  precedence, traceability, or acceptance criteria.
- Use `analyze-competing-hypotheses` when ambiguity concerns competing factual or causal
  explanations. Treat its judgments as assumptions or unknowns until the decision owner accepts
  them.
- Establish requirement intent before an ASD-STE100 rewrite. Protect normative keywords, values,
  and conditions during the rewrite.
- Rerun the requirements checker after an ASD-STE100 wording change. If both release claims are
  required, bind each review to the same final text and revalidate both digests after every change.

## Run deterministic tools

Generate a fail-closed evidence starter:

```text
python "<SKILL_ROOT>/scripts/create_compliance_report.py" --emit-template
```

Generate a complete token ledger for the exact final text:

```text
python "<SKILL_ROOT>/scripts/check_project_terms.py" --text "FINAL.txt" --emit-coverage-template
```

Get the hash-verified applicable rule index:

```text
python "<SKILL_ROOT>/scripts/create_compliance_report.py" --list-applicable-checks --checklist "<SKILL_ROOT>/references/compliance-checklist.yaml" --standard "<SKILL_ROOT>/references/asd-ste100-issue-9.pdf" --content-type procedural
```

After qualified review fills every word row, run the terminology check once for machine and human
output:

```text
python "<SKILL_ROOT>/scripts/check_project_terms.py" --terms "PROJECT-TERMINOLOGY.yaml" --text "FINAL.txt" --coverage "EVIDENCE.yaml" --domain "DOMAIN" --format both
```

Run the release report:

```text
python "<SKILL_ROOT>/scripts/create_compliance_report.py" "EVIDENCE.yaml" --format both --output-dir "REPORTS"
```

The report rejects caller-supplied release gates and derives all gates from exact checklist
coverage, token coverage, file and text digests, terminology results, technical-integrity evidence,
unresolved registers, safety traces, corrections, and revision-bound reviewers. Its digest binds
review to the source, output, references, and evidence. Any evidence change invalidates prior
reviewer records. The output directory receives digest-qualified JSON and Markdown files. The
script refuses to replace either file unless the user supplies `--overwrite`. It stages each file
in the destination directory before the atomic write.

Read `state_code`, `operation_succeeded`, and `release_permitted` from the JSON report. A completed
report operation can still block release. Do not infer release permission from the process exit
code, from `operation_succeeded`, or from the presence of report files.

For clean output, run:

```text
python "<SKILL_ROOT>/scripts/create_compliance_report.py" "EVIDENCE.yaml" --format clean
```

Verify source, local standard, and installation parity when installing or updating:

```text
python "<SKILL_ROOT>/scripts/create_compliance_report.py" --verify-skill-root "<SKILL_ROOT>" --compare-skill-root "INSTALLED-SKILL-ROOT"
```

These scripts validate only the deterministic scope they report. They do not decide dictionary
meaning, grammar, technical accuracy, lawful reference authorization, or actual reviewer identity.

## Record evidence and release status

Use only `PASS`, `FAIL`, `NOT APPLICABLE`, or `REVIEW REQUIRED` for check results. Give every
applicable checklist row its exact ID. Use only `YES`, `NO`, or `REVIEW REQUIRED` for technical
meaning preservation. An applicable non-`PASS`, a missing or extra row, incomplete token coverage,
an open register, a digest mismatch, or an invalid reviewer record blocks release.

For ambiguity, source discrepancies, terminology decisions, safety traces, reviewers, and
corrections, record stable IDs, source location or quotation, required authority, status,
disposition evidence, date where applicable, and the bound artifact digest.

Use only these final statuses:

- `FULLY CHECKED — ASD-STE100 ISSUE 9 COMPLIANT`
- `NOT RELEASED — COMPLIANCE CHECK FAILED`
- `NOT RELEASED — COMPLIANCE CHECK INCOMPLETE`
- `NOT RELEASED — TECHNICAL REVIEW REQUIRED`
- `DRAFT — HUMAN ASD-STE100 REVIEW REQUIRED`

Use the fully checked status only when the report derives every gate as `PASS` and both actual human
reviewers approved the exact final digest. If a word, rule, exception, term, fact, meaning,
authorization, or review cannot be verified, do not guess. Identify the unresolved item, name the
authority needed, block release, and provide only a clearly marked draft when useful.
