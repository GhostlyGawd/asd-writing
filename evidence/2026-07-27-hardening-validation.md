# ASD-STE100 skill hardening validation — 2026-07-27

## Scope

This evidence applies to the `write-asd-ste100` skill on branch
`agent/harden-asd-ste100`. It records the remediation and validation of the
multi-lens review findings. It is dated evidence, not a permanent claim that
future skill versions have the same results.

## Completed task list

- [x] Convert the acceptance specification into executable regression tests.
- [x] Bind every compliance decision to the exact source, output, standard,
      checklist, terminology, and review artifact.
- [x] Derive release gates in the report generator and reject caller-supplied
      gate decisions.
- [x] Require complete word classification and strict terminology validation.
- [x] Enforce content applicability, technical-integrity, safety, ambiguity,
      and reviewer gates.
- [x] Separate task modes from output modes and prohibit premature clean output.
- [x] Provide fail-closed evidence and terminology templates.
- [x] Align the skill instructions, repository specification, operational
      guidance, and tests.
- [x] Forward-test maintenance, descriptive, and safety content with independent
      agents that did not receive expected results.
- [x] Run static, unit, CLI, structural, and source-to-install parity checks.

## Findings and resolution

| Review lens | Finding | Resolution | Verification |
|---|---|---|---|
| Release integrity | A caller could assert release gates or submit incomplete checks. | Gates are derived from validated evidence; supplied `release_gates`, missing checks, extra checks, and duplicate checks block release. | Unit and CLI regression tests. |
| Evidence integrity | Evidence was not bound to the exact artifacts under review. | SHA-256 digests bind the source, output, bundled standard, checklist, terminology, and reviewer artifact. | Hash-tampering and untrusted-reference tests. |
| Human review | Reviewer records could be weakly related to the reviewed content. | Distinct language and technical reviewers must approve the same artifact digest; dates cannot be in the future; all corrections require applied-state evidence. | Reviewer identity, date, digest, and correction tests. |
| Vocabulary | Partial vocabulary coverage could appear complete. | Every lexical token requires a classified ledger entry; dictionary words require approved meaning and part-of-speech evidence. | Missing-coverage, wrong-meaning, and wrong-part-of-speech tests. |
| Terminology | Terminology parsing and matching were permissive and inefficient. | Strict duplicate-safe schema validation, domain-aware Unicode matching, collision checks, prohibited-synonym checks, and combined patterns now fail closed. | Schema, domain, Unicode, collision, multiline, and performance tests. |
| Content rules | Safety and mixed-content applicability could be incomplete. | The checklist supports multiple content labels, and safety content receives procedural checks when applicable. | Safety applicability and Rule 5.1 lookup tests. |
| Technical integrity | Changes to facts, quantities, requirements, or safety meaning needed explicit gates. | Structured technical-integrity and safety-trace evidence is mandatory, with unresolved registers for ambiguity and possible source errors. | Numerical-value, unit, mandatory-requirement, ambiguity, conflict, and safety tests. |
| Operational workflow | Relative paths and mutable installed terminology reduced reliability. | Instructions resolve an absolute skill root and require a project-controlled terminology copy. | Skill contract tests and CLI smoke tests. |
| Output behavior | Clean output could be requested before release was ready. | Clean output is emitted only after every derived gate passes; otherwise the command exits with a blocking report. | Passing and premature-clean CLI tests. |
| Real-world usability | The workflow needed evidence that it stops safely on realistic inputs. | Three independent forward tests exercised maintenance, description, and safety requests. Each produced useful draft/review material and withheld release for concrete unresolved items. | Forward-test records below. |

## Contract alignment

| Contract item | Normative source | Implementation | Test or evidence | User guidance | Status |
|---|---|---|---|---|---|
| Exact Issue 9 control | `AGENTS.md`; checklist manifest | Trusted bundled-reference digest validation | Reference-tampering and skill-root verification tests | `SKILL.md`; `README.md` | Aligned |
| Complete word checks | `AGENTS.md`; Issue 9 checklist | Terminology checker and report word ledger | Vocabulary and coverage tests | `SKILL.md` | Aligned |
| Technical and safety preservation | `AGENTS.md` | Integrity records, safety trace, unresolved registers | Acceptance cases 3, 13–16 | `SKILL.md` | Aligned |
| Human approval | `AGENTS.md` | Digest-bound, distinct reviewer records | Acceptance cases 18–19 and reviewer tests | `SKILL.md`; `README.md` | Aligned |
| Fail-closed release | `AGENTS.md` | Derived gates and clean-output guard | Acceptance cases 17–20 and CLI tests | `SKILL.md`; `README.md` | Aligned |
| Terminology schema | `AGENTS.md` | Strict schema and matching engine | Terminology schema and performance tests | Template comments; `SKILL.md` | Aligned |
| Installation parity | `AGENTS.md` | Root verification and compare command | Source/install comparison | `README.md` | Aligned |

## Validation results

Repository validation completed on 2026-07-27:

- `python -m unittest discover -s tests -v`: 53 tests passed.
- `python -m ruff check write-asd-ste100\scripts tests`: passed.
- Standard skill validator on the repository skill root: passed.
- Skill-root structure, reference digest, and checklist validation: passed.
- Applicable-check lookup for safety content: passed and included the
  procedural sentence-length rule.
- Terminology and compliance-report CLI pass, fail, template, and clean-output
  scenarios: passed.
- Code-structure post-edit analysis: no introduced regressions, dependency
  cycles, duplicate implementations, or orphaned symbols.
- Installation validator on
  `C:\Users\rhenm\.codex\skills\write-asd-ste100`: passed.
- Exact repository-to-install comparison of all seven operational and reference
  files, including the authorized PDF: passed with no findings.

## Independent forward tests

The forward-test agents received realistic requests but did not receive the
expected outcomes.

| Lens | Scenario | Result |
|---|---|---|
| Maintenance | Ambiguous maintenance instruction with safety implications and a premature clean-output request. | Correctly refused clean output, identified the ambiguous pronoun, unspecified equipment, unresolved hazard level, missing controlled inputs, and required reviewers. |
| Description | System-description rewrite in teaching/report mode. | Produced a marked draft and checkable explanations, identified actor ambiguity and missing terminology/context, and did not fabricate compliance. |
| Safety | Warning plus passive procedural step with unclear reader roles. | Identified recommendation language, vague safety action, prohibited possibility usage, passive construction, role ambiguity, and unconfirmed risk control; blocked release. |

All three returned `NOT RELEASED — COMPLIANCE CHECK INCOMPLETE`. None changed
repository files or created temporary artifacts.

## Documentation alignment

Changed documentation:

- `AGENTS.md`: normative workflow, evidence, terminology, review, validation,
  and installation contracts.
- `write-asd-ste100/SKILL.md`: executable operating workflow and release rules.
- `README.md`: repository purpose, validation, installation, security,
  limitations, and workflow visualization.

Drift classifications resolved:

- Normative-to-implementation drift: release gates, evidence binding, reviewer
  records, and terminology coverage.
- Implementation-to-test drift: failure modes and command-line behavior now
  have regression coverage.
- Operations drift: commands now resolve the correct skill root and verify
  installation parity.
- Claim drift: documentation explicitly limits automated assurance and forbids
  certification or approval implications.

Reviewed but unaffected:

- No production service, deployment, external integration, repository setting,
  or cross-repository architecture is part of this change.
- No ASD or STEMG logo, endorsement, certification, or approval claim is used.

## Known limitations

- The scripts enforce structured evidence and deterministic release gates; they
  do not perform the complete language or technical review themselves.
- Automation cannot authenticate a reviewer's identity, training, authority, or
  the legal authorization of a supplied standard. Those facts require human and
  organizational controls.
- Passing deterministic gates does not by itself prove semantic correctness.
  The trained ASD-STE100 reviewer and authorized technical reviewer remain
  responsible for the final decisions.
- The authorized Issue 9 PDF is intentionally excluded from Git. Each lawful
  installation must receive its authorized local copy and match the pinned
  digest.

## Installation status

Installed on 2026-07-27 at
`C:\Users\rhenm\.codex\skills\write-asd-ste100`. The installed skill passed the
standard validator and exactly matched the verified repository source,
including the authorized local Issue 9 PDF.
