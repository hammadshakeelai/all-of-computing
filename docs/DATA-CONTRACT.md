# Data and Knowledge Contract

Status: proposed version 1, for review before implementation. These schemas describe intended records; no runtime database exists yet.

## Ownership

| Data | Canonical home | Other representations |
|---|---|---|
| Authored concept explanation and examples | Markdown | Search chunks and UI rendering |
| Source notes and bibliographic metadata | Markdown/source manifest | Search and resource database projection |
| Accepted typed relationships and stable identity | SQLite | Flat frontmatter lists, graph export, readable links |
| Goals, paths, sessions, attempts, assessments, reviews | SQLite | Structured JSON export and Markdown summaries |
| Proficiency | Derived from versioned evidence policy | Cached database view and generated note fields |
| Search chunks and embeddings | Rebuildable index | Source checksum and configuration manifest |
| Personal configuration | Local configuration/credential store | Redacted export only |

Ownership must be field-specific. A note edit may change authored text and propose relationships; it must not overwrite an assessment. Generated note fields carry a revision marker. Restoring Markdown alone restores the library, not the full learner history.

## Minimal record shapes

All persistent entities have a stable ID, schema version, creation time, and revision. Store timestamps in UTC with the learner timezone available for display and scheduling. Initially use Asia/Karachi for the user's day boundaries. Display actual historical dates; never infer them from chat text.

| Entity | Important fields |
|---|---|
| Concept | id, title, aliases, domain_ids, learning_objectives, note_path, content_hash |
| Relationship | id, from_id, to_id, relation_type, status, origin, supporting_source_ids |
| Resource | id, title, URL/path, author, source_type, access_date, checksum, permission/provenance metadata |
| Goal | id, desired_outcome, active_status, priority, time_budget, target_date_optional |
| Path step | id, goal_id, objective_ids, required_concept_ids, activity_type, order, completion_policy |
| Session | id, mode, goal_id_optional, objective_ids, current_step, pending_question_id, status |
| Question | id, version, prompt, type, objective_ids, rubric_version, difficulty_label, source_refs, hidden_reference_answer |
| Attempt | id, question_id_and_version, session_id, answer, answer_format, self_confidence_optional, assistance_events, submitted_at |
| Assessment | id, attempt_id, rubric_snapshot, dimension_judgments, supporting_answer_spans, feedback, uncertainty, evaluator_version, status |
| Evidence event | id, concept_id, objective_id, attempt_id, assessment_id, evidence_type, assistance_class, policy_version |
| Review item | id, objective_id, due_at, scheduling_policy_version, interval_step, last_evidence_id, status |
| AI run | id, role, prompt_version, provider, model_identifier, source_chunk_ids, usage_optional, error_optional |

Events use persistent unique submission keys for idempotency. Store assessment revisions as new records linked to the superseded judgment. Deletion/export policies must cover transcripts and raw answers, not only notes. Support learner corrections without erasing audit history; explicit personal-data deletion is a separate operation.

## Markdown representation

Example only, with synthetic IDs and no learner proficiency:

```markdown
---
id: concept-demo-recursion
schema_version: 1
title: Recursion
type: concept
domains:
  - computing
aliases:
  - recursive functions
requires:
  - "[[Functions]]"
related:
  - "[[Induction]]"
origin: demo
---

# Recursion

## Learning objectives

- Explain a base case and a recursive step.
- Trace a small recursive computation.

## My explanation

Authored content belongs here.

## Connections

Requires [[Functions]]. Relates to [[Induction]].

## Sources

Source records and precise locations belong here.
```

Use flat properties and quoted wikilinks because Obsidian supports YAML properties and has limitations on nested property editing. Keep rich assessment structures in structured exports rather than nesting them into note properties. [Obsidian properties](https://obsidian.md/help/properties)

Link paths are a presentation layer; IDs identify records. When a file is renamed, resolve by its frontmatter ID. Duplicate IDs trigger a visible conflict rather than silent merging. Wiki links must resolve unambiguously with directory-qualified paths where necessary. Ordinary Markdown links remain usable outside Obsidian where possible.

## Synchronization rules

1. The app watches selected vault paths; it ignores temporary files and its own writes by checksum/revision.
2. Parse external edits into candidate changes. Preserve unknown frontmatter keys and user sections.
3. Validate IDs and schemas; malformed notes stay readable but are excluded from automated updates with an actionable error.
4. For authored content, compare last-seen hash and current hash before writing. If both sides changed, retain both versions and show a conflict.
5. App-generated proficiency fields can be regenerated. Do not silently replace user-authored explanations with AI summaries.
6. Relationship edits are imported as proposals; accepted prerequisites receive validation, including cycle checks.
7. Use a database transaction and durable file-write outbox. Retry pending file writes after restart. Do not pretend a database transaction makes filesystem writes atomic.
8. Source changes invalidate affected chunks. Source deletion removes them from retrieval while historical assessments retain provenance snapshots and a missing-source marker.
9. Deleting a note archives or detaches its concept; it must not cascade-delete attempts.

## Portable export

An export archive contains:

- `manifest.json`: export/schema versions, generation timestamp, timezone, file checksums, and included data categories.
- `vault/`: authored Markdown and generated readable summaries.
- `records/*.jsonl`: concepts, relationships, goals, paths, sessions, questions, attempts, assessments, evidence events, and review items.
- `sources/`: permitted attachment content and source metadata; reference-only entries for excluded content.
- `configuration.json`: non-secret policy settings and versions necessary to interpret evidence.

Never include API keys. Keep raw answer and rubric snapshots sufficient to inspect a grade after a provider disappears. Search and embeddings can be omitted because they are rebuildable. Record exclusions explicitly. A schema migration may transform old exports; unsupported versions must fail visibly.

A graph export uses explicit nodes and typed edges in JSON. RDF or JSON-LD can be added later through an adapter once ontology needs are concrete; do not require them for the first version.

## Restore acceptance

Export a fixture with one edited concept, one source, one session, an assisted attempt, an independent attempt, a disputed assessment, and a due review. Restore into an empty installation. IDs, authored content, assessment revisions, assistance, pending session state, and due dates must match. Citation locations and source exclusions remain inspectable. Rebuild search afterward. This verifies evidence durability rather than merely that notes can be reopened.
