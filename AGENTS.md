# Create a Fully Compliant ASD-STE100 Writing Skill

## 1. Objective

Create and install a Codex skill named `write-asd-ste100`.

The skill must write, rewrite, and review technical content in full compliance with ASD-STE100 Simplified Technical English, Issue 9, January 2025.

Full compliance is a mandatory release condition. It is not an optional writing target.

The skill must not release content as compliant when it cannot complete all required checks.

## 2. Definition of success

The skill is successful when it can:

1. Write new technical content in ASD-STE100.
2. Rewrite existing technical content in ASD-STE100.
3. Check each word and sentence against the applicable standard.
4. Preserve the source technical meaning.
5. Apply approved project terminology.
6. Identify and stop on unresolved ambiguity.
7. Produce evidence for its compliance decision.
8. Prevent the release of content that does not pass all release gates.
9. Require trained human review before the final compliance statement.

## 3. Controlling reference

Use the complete, authorized copy of ASD-STE100 Issue 9 as the controlling language reference.

Do not use these sources as substitutes:

- model memory;
- unofficial summaries;
- general plain-language guidance;
- rules from an older issue;
- a general grammar checker;
- an unverified ASD-STE100 rule list.

Use exact requirements, limits, approved meanings, parts of speech, and exceptions from Issue 9.

Do not invent rule numbers or dictionary entries.

Do not create or install an operational version of the skill until the authorized reference is available.

## 4. Required inputs

Require these inputs for a full compliance check:

1. Authorized ASD-STE100 Issue 9 reference
2. Source technical information
3. Approved project terminology
4. Applicable company writing requirements
5. Content type
6. Intended reader
7. Technical domain
8. Terms and identifiers that must not change

If an input is missing, the skill can produce a draft. It must not release the draft as compliant.

Use this draft status:

`DRAFT — FULL COMPLIANCE CHECK NOT COMPLETE`

## 5. Activation requirements

Write the skill description so that the skill activates when the user asks to:

- write in ASD-STE100;
- write in Simplified Technical English;
- write in STE;
- convert technical text to ASD-STE100;
- rewrite technical instructions in ASD-STE100;
- review text for ASD-STE100 compliance;
- check STE vocabulary or grammar;
- create controlled technical English;
- edit maintenance, operation, safety, or system-description content in STE.

Do not activate the skill for a general request to make text short, simple, or informal unless the user also requests STE or ASD-STE100.

## 6. Supported content

Support these content types:

- procedural text;
- descriptive text;
- maintenance instructions;
- operating instructions;
- troubleshooting instructions;
- warnings;
- cautions;
- notes;
- system descriptions;
- component descriptions;
- inspection requirements;
- test requirements;
- mixed technical content.

Identify the content type before the rewrite. Apply the rules that are applicable to that content type.

## 7. Source hierarchy

Use sources in this order:

1. Safety requirements
2. Approved technical source data
3. Approved company terminology
4. Approved project terminology
5. ASD-STE100 Issue 9 writing rules
6. ASD-STE100 Issue 9 dictionary
7. General English usage

Do not change a technical fact to satisfy a language rule.

If two controlling sources conflict:

1. Stop the affected rewrite.
2. Identify the conflict.
3. Request an authorized decision.
4. Do not silently select one source.
5. Set the output status to `NOT RELEASED`.

## 8. Operating modes

Support these modes.

### 8.1 Write

Create new technical content from approved technical source data.

Do not add technical facts that are not in the source data.

### 8.2 Rewrite

Convert source text to ASD-STE100.

Preserve:

- meaning;
- conditions;
- sequence;
- quantities;
- units;
- limits;
- tolerances;
- identifiers;
- part names;
- safety level;
- mandatory or optional meaning.

### 8.3 Compliance review

Review text without automatically changing it.

Report each problem and give a proposed correction.

### 8.4 Rewrite with compliance report

Return:

1. Revised text
2. Compliance status
3. Change report
4. Compliance evidence
5. Unresolved items
6. Required reviewer actions

### 8.5 Clean output

Return only the final technical text.

Permit this mode only after all release gates pass. Do not use this mode for drafts or incomplete reviews.

### 8.6 Teaching mode

Explain the changes.

For each important change, give:

- the source text;
- the revised text;
- the problem type;
- the applicable rule number or dictionary entry;
- a short explanation.

Do not invent a citation when the controlling reference does not support it.

## 9. Required workflow

For each request, do these steps in this order:

1. Confirm that the controlling references are available.
2. Identify the content type.
3. Identify the intended reader.
4. Identify the technical domain.
5. Load the approved project terminology.
6. Identify protected terms, values, and identifiers.
7. Divide mixed content into procedural and descriptive sections.
8. Identify technical ambiguity before the rewrite.
9. Rewrite the content.
10. Check each word.
11. Check each sentence.
12. Check each paragraph or procedural sequence.
13. Compare the result with the technical source.
14. Run all available automated checks.
15. Record the compliance results.
16. Correct all detected language problems.
17. Repeat the checks after each correction.
18. Request technical and ASD-STE100 human review.
19. Apply authorized review corrections.
20. Run the final checks again.
21. Release the text only when all gates pass.

Do not skip a check because the text appears simple.

## 10. Vocabulary compliance

Check every word in the output.

Classify each word as one of these types:

1. An ASD-STE100 dictionary word
2. An approved technical name
3. An approved technical verb
4. A permitted proper noun
5. A permitted abbreviation or identifier
6. A non-approved word

For an ASD-STE100 dictionary word, verify:

- approved meaning;
- approved part of speech;
- approved grammatical form;
- applicable usage restrictions.

A dictionary word is not approved when the text uses it with a non-approved meaning or part of speech.

Do not use a synonym only to create variation.

Use one term for one meaning. Use one meaning for one term when the technical domain permits it.

A non-approved word blocks release unless the authorized standard permits its use as approved project terminology.

## 11. Project terminology

Support an approved project terminology file.

Each entry must contain:

- approved term;
- definition;
- term type;
- approved part of speech;
- permitted inflections;
- prohibited synonyms;
- domain;
- source authority;
- approval status;
- approval date;
- notes.

Use only terminology with an approved status.

Do not automatically approve a term because it occurs frequently in the source.

When a necessary term is not approved:

1. Keep it in the unresolved terminology list.
2. Request terminology approval.
3. Do not release the affected text as fully compliant.

## 12. Rule compliance

Check all applicable ASD-STE100 Issue 9 rules.

The checks must include, but are not limited to:

- approved vocabulary;
- approved meanings;
- approved parts of speech;
- technical names;
- technical verbs;
- spelling;
- sentence length;
- sentence structure;
- verb forms;
- verb tense;
- active and passive voice;
- imperative construction;
- articles;
- determiners;
- pronouns;
- pronoun references;
- omitted words;
- noun clusters;
- modifiers;
- conjunctions;
- punctuation;
- paragraph construction;
- procedural writing;
- descriptive writing;
- warnings;
- cautions;
- notes;
- units;
- quantities;
- limits;
- terminology consistency.

Get all exact limits, conditions, and exceptions from the authorized Issue 9 reference.

Do not put a remembered numerical limit into the skill unless it is verified against the reference.

## 13. Technical integrity

Do not change:

- technical meaning;
- equipment identity;
- part identity;
- material identity;
- step sequence;
- numerical value;
- unit;
- tolerance;
- condition;
- cause-and-effect relation;
- safety classification;
- mandatory requirement;
- prohibition;
- permission;
- expected result.

Do not change a warning into a caution or note.

Do not change a mandatory instruction into a recommendation.

Do not change an exact value into an approximate value.

Do not add a technical action that is not in the approved source.

If the source contains a possible technical error:

1. Preserve the source meaning in the draft.
2. Identify the possible error.
3. Request technical review.
4. Block final release.

## 14. Ambiguity controls

Do not guess the meaning of ambiguous source text.

For each ambiguity:

1. Quote the affected source text.
2. Identify the possible meanings.
3. Explain which technical decision is necessary.
4. Request clarification.
5. Block the affected content from release.

Do not use language simplification to hide a technical ambiguity.

## 15. Compliance evidence

Create a structured compliance record.

Use these columns:

| Location | Check type | Result | Rule or dictionary basis | Correction | Reviewer | Evidence |
|---|---|---|---|---|---|---|

Use these result values:

- `PASS`
- `FAIL`
- `NOT APPLICABLE`
- `REVIEW REQUIRED`

A `FAIL` or `REVIEW REQUIRED` result blocks final release.

Evidence must show the applicable rule number, dictionary entry, project terminology entry, or technical source.

Do not include hidden reasoning. Include only concise, checkable evidence.

## 16. Change report

For rewrite tasks, create this report:

| Location | Source text | Revised text | Reason | Rule or dictionary basis | Technical meaning preserved |
|---|---|---|---|---|---|

Use `YES`, `NO`, or `REVIEW REQUIRED` in the final column.

A `NO` or `REVIEW REQUIRED` result blocks release.

## 17. Release gates

Do not release text as fully compliant unless all these conditions are true:

- The complete authorized standard was available.
- The complete text was checked.
- All applicable rules were checked.
- Each word has an approved classification.
- Each dictionary word has an approved meaning and part of speech.
- Each technical term is approved.
- All automated checks pass.
- No unresolved language problem remains.
- No unresolved terminology problem remains.
- No unresolved technical ambiguity remains.
- The rewrite preserves all technical facts.
- The rewrite preserves all safety requirements.
- A trained ASD-STE100 reviewer approved the language.
- An authorized technical reviewer approved the technical content.
- All reviewer corrections were applied.
- The corrected text passed the final checks.

One failed gate blocks release.

## 18. Output status

Use only these status values:

- `FULLY CHECKED — ASD-STE100 ISSUE 9 COMPLIANT`
- `NOT RELEASED — COMPLIANCE CHECK FAILED`
- `NOT RELEASED — COMPLIANCE CHECK INCOMPLETE`
- `NOT RELEASED — TECHNICAL REVIEW REQUIRED`
- `DRAFT — HUMAN ASD-STE100 REVIEW REQUIRED`

Use the fully compliant status only after all release gates pass.

Do not use words such as `compliant`, `verified`, or `checked` in a final status when required checks are incomplete.

## 19. Human review

Automated checks and AI review do not replace human review.

Require:

1. A trained ASD-STE100 language reviewer
2. An authorized technical reviewer

Record:

- reviewer name or identifier;
- reviewer role;
- review date;
- review result;
- required corrections;
- final approval state.

The skill can prepare content and evidence for review. It cannot create a human approval record without an actual reviewer decision.

## 20. Prohibited claims

Do not state or imply that:

- ASD approved the skill;
- STEMG approved the skill;
- ASD certified the skill;
- STEMG certified the skill;
- an automated checker guarantees compliance;
- AI replaces a trained reviewer;
- language compliance guarantees technical accuracy.

Do not use ASD or STEMG logos unless the user supplies documented permission.

## 21. Failure behavior

If the skill cannot verify a word, rule, exception, term, or technical meaning:

1. Do not guess.
2. Do not release the affected text.
3. Identify the unresolved item.
4. Cite the decision or source that is necessary.
5. Set the status to `NOT RELEASED`.
6. Give a draft only when it is clearly marked as a draft.

## 22. Skill structure

Create only the files that the skill needs:

write-asd-ste100/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── asd-ste100-issue-9.pdf
│   ├── project-terminology.yaml
│   └── compliance-checklist.yaml
└── scripts/
    ├── check_project_terms.py
    └── create_compliance_report.py

Do not create a README, change log, installation guide, or other unnecessary file.

## 23. SKILL.md requirements

Use this frontmatter structure:

---
name: write-asd-ste100
description: Write, rewrite, and review technical content for full compliance with ASD-STE100 Simplified Technical English Issue 9. Use for STE authoring, ASD-STE100 rewriting, controlled technical English, vocabulary checks, compliance reviews, maintenance instructions, operating instructions, warnings, cautions, notes, and technical descriptions.
---

Keep the body concise.

Put these items in `SKILL.md`:

- required workflow;
- source hierarchy;
- release gates;
- failure behavior;
- instructions for using the references;
- instructions for using the scripts;
- output modes;
- compliance status rules.

Do not copy large parts of the standard into `SKILL.md`.

## 24. Reference requirements

Store the user-provided authorized copy of Issue 9 in the references directory.

Do not download, reproduce, or distribute an unauthorized copy.

Create the project terminology template and compliance checklist from verified requirements.

Every checklist item must cite its source in Issue 9.

Do not add a rule that cannot be verified.

## 25. Script requirements

Use scripts only for checks that can be reliable and repeatable.

The terminology checker must:

- load the approved project terminology;
- identify terms that are not approved;
- identify prohibited synonyms;
- detect inconsistent approved terms;
- produce machine-readable and human-readable results;
- return a failure status when blocking problems exist.

The compliance-report script must:

- collect check results;
- validate permitted result values;
- identify failed release gates;
- prevent a compliant status when a gate is open;
- produce a clear report.

Scripts must not claim to check rules that they do not implement.

Test all scripts with passing and failing inputs.

## 26. Acceptance tests

Test the completed skill with at least these cases:

1. A maintenance procedure
2. A descriptive system paragraph
3. A warning with related procedural steps
4. An approved dictionary word used with a non-approved meaning
5. An approved word used as the wrong part of speech
6. A necessary approved technical name
7. A technical term that is not approved
8. An inconsistent technical term
9. An ambiguous pronoun
10. An excessive noun cluster
11. A sentence that violates an applicable length rule
12. A passive construction that requires review
13. A missing unit
14. A changed numerical value
15. A changed mandatory requirement
16. A conflict between project terminology and technical source data
17. A task without the authorized Issue 9 reference
18. A task without human review
19. A task in which all gates pass
20. A request for clean output before the gates pass

Verify that the skill:

- preserves technical meaning;
- does not invent technical facts;
- does not invent rule citations;
- identifies non-approved vocabulary;
- identifies ambiguity;
- applies project terminology;
- blocks release when a gate fails;
- does not issue a compliant status without human approval;
- permits clean output only after all gates pass.

## 27. Skill validation

Initialize the skill with the standard skill-creation tools.

Validate:

- skill name;
- YAML frontmatter;
- skill description;
- required files;
- script operation;
- reference links;
- output statuses;
- release-gate behavior;
- test results.

Forward-test the skill on realistic technical content.

Do not expose the expected test results to the forward-test agent.

Correct all defects and repeat the tests.

## 28. Installation condition

Install and save the skill only when:

- the authorized Issue 9 reference is present;
- the skill structure is valid;
- all scripts pass their tests;
- all acceptance tests pass;
- no unverified ASD-STE100 rule is present;
- the release gates operate correctly.

If these conditions do not pass, preserve the work but report that the skill is not ready for installation.

## 29. Completion report

After successful installation, report:

1. Skill name
2. Purpose
3. Included files
4. Controlling standard issue
5. Tests completed
6. Test results
7. Known limitations
8. Human review requirement
9. Installation status

Do not describe the skill as ASD-approved, STEMG-approved, or certified.