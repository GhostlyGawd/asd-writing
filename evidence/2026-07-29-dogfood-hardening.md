# ASD-STE100 skill dogfood hardening — 2026-07-29

## Scope

This record applies to the `write-asd-ste100` skill on branch
`agent/dogfood-hardening-20260729`. It records the deterministic report and
agent-operability changes from the three-skill dogfood campaign. It does not
supersede the 2026-07-27 validation record or claim that later revisions have
the same results.

## Findings and resolutions

| Finding | Resolution | Verification |
|---|---|---|
| Agents could infer release from a process exit code or a successful report operation. | Reports now give `state_code`, `operation_succeeded`, and `release_permitted`. Only `release_permitted` authorizes release. | Passing, blocked, malformed-input, human-render, and CLI tests. |
| Console-only reports were difficult to retain safely, and a fixed output name could overwrite prior evidence. | `--output-dir` writes digest-qualified JSON and Markdown files through destination-local atomic writes. Existing files block the command unless `--overwrite` is explicit. | CLI creation, name, content, temporary-file cleanup, overwrite-refusal, and explicit-overwrite tests. |
| Repeated dictionary lookups could waste effort on long text. | The workflow batches unique dictionary-entry reads but still checks and records every occurrence in context. The instructions explicitly deny automated semantic approval. | Skill contract test and instruction review. |
| Invocation policy was implicit. | Agent metadata now sets `policy.allow_implicit_invocation: true`; the skill description still limits formal activation to explicit STE requests. | Agent-metadata contract test. |

## Validation

Validation completed on 2026-07-29:

- `python3 -m unittest discover -s tests -v`: 56 tests passed.
- `git diff --check`: passed.
- Standard Codex skill validator: passed.
- Local skill-root structure and trusted-reference verification: passed.
- Digest-qualified JSON and Markdown output: passed.
- Default overwrite refusal and explicit overwrite: passed.
- Codeweb structural comparison: passed with no new cycle, duplicate
  implementation, orphaned symbol, or other structural regression.

The repository runtime did not provide Ruff, so this task did not repeat the
optional Ruff check. The complete unit suite and repository verifier did run.

## Documentation alignment

Changed documentation:

- `write-asd-ste100/SKILL.md`: batched dictionary lookup, durable report output,
  machine-readable state, and release-decision instructions.
- `README.md`: durable output and orchestration behavior.
- `write-asd-ste100/agents/openai.yaml`: explicit implicit-invocation policy.

Drift classifications resolved:

- Agent-interface drift: release state is now explicit and machine-readable.
- Operations drift: report retention and overwrite behavior are documented.
- Efficiency drift: repeated dictionary reference reads are batched without
  weakening per-occurrence checks.

Reviewed but unaffected:

- The controlling Issue 9 reference, checklist requirements, terminology
  schema, reviewer roles, release gates, security and privacy boundaries,
  installation process, and workflow visual did not require a semantic change.
- No production service, external integration, repository setting, logo,
  endorsement, approval, or certification claim is part of this change.

## Remaining limitations

- The scripts still validate only their documented deterministic scope.
- Dictionary meaning, grammar, technical accuracy, reference authorization, and
  reviewer identity still require the controlling reference and authorized
  human decisions.
- Atomicity applies to each destination file. No filesystem operation can make
  the JSON and Markdown pair one indivisible multi-file transaction.
