# First Build Brief

Status: implemented as local v1 on 2026-10-06. The offline completion scenario and mocked-provider failure paths pass automated checks; live AI needs a configured key/model. See [RELEASE.md](RELEASE.md) and the repository README for setup and actual scope. This brief preserves the original build requirements below.

## Outcome

The learner opens a local GUI, studies one concept from a small approved source fixture, answers a question, receives grounded feedback, saves the learning record, closes the app, and resumes. Notes can be read in Obsidian. A lossless export can be restored.

Use a user-selected objective. Until selected, a synthetic recursion example can exercise the workflow without claiming the user studied it.

## Included

- One learner, one configurable private data directory, loopback-only API.
- Today screen, basic Study screen, minimal concept detail and history.
- A Markdown source/concept fixture with stable IDs and full-text retrieval.
- One question with a frozen rubric; short-answer or theory response.
- Persist the answer before evaluating it, with retry-safe submission IDs.
- Structured feedback: correct points, missing points, supporting answer spans, uncertainty, source references, next action.
- Evidence states separating encountered, assisted, and independent demonstration.
- A simple review item and resumable session state.
- Generated Markdown session summary plus original structured records.
- Mock provider and one optional real adapter after configuration is chosen.
- Minimal complete export/restore; keys and private content ignored by Git.

## Implementation sequence

1. Freeze minimal record contracts and field ownership. Select supported runtime versions and lock dependencies.
2. Set up local application startup and persistent storage with a migration baseline.
3. Load a small clearly labeled demo fixture and implement source lookup.
4. Implement question/attempt persistence and deterministic evidence policy.
5. Implement mock tutoring/evaluation and failure states.
6. Build the local UI for completing and resuming the session.
7. Add safe Markdown projection, then lossless export and restore.
8. Run persistence and end-to-end checks. Connect a real provider only after secret/context configuration is explicit.

## Completion scenario

1. Start from empty private storage and a synthetic demo source.
2. Open a concept and study an explanation with a resolvable citation.
3. Answer a frozen question independently and receive feedback.
4. Verify the stored attempt matches the submitted answer exactly.
5. Verify feedback links to rubric dimensions and actual answer spans.
6. Confirm that reading alone did not generate independent proficiency.
7. Restart and inspect the attempt, note, source, and suggested review.
8. Submit the same request again; only one attempt exists.
9. Simulate provider timeout; the saved answer remains and evaluation can resume.
10. Export, restore to empty storage, and find the same IDs, answer, assessment, and session.

Mock mode verifies workflow and durability. A working real AI adapter is separately labeled unverified until a live run and the reviewed grading fixtures pass.

## Deferred from this build

Live voice, code execution, complex course ingestion, PDF extraction, embeddings, a full interactive graph, multi-device sync, automatic course-platform connections, public hosting, and multiple autonomous agents.

## Decisions needed for a live pilot

First objective, teaching language, provider, permitted cloud context, and spending cap. The architecture and mock implementation can proceed without paid calls or invented learner history.
