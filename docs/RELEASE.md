# Learning Atlas v1 — implementation and validation

Release date: 2026-10-06. This is a usable local text learning app; optional integrations in the long-term plan remain extensions.

## Implemented

All eight planned screen areas are present: Today, Study, Answer/Feedback (inside Study), Library, Goals, Knowledge Map, Progress/Evidence, and Settings/Data. Review has its own navigation entry. Course/resource tracking and reviewable AI lesson drafting extend the initial learning loop.

Persistent records include concepts, prerequisites, resources, goals, resumable sessions, frozen questions, original answers, assessment revisions, reviews, and bounded AI run metadata. Offline practice works without configuration. Adaptive teaching, quiz generation, and theory grading use the optional OpenAI adapter.

## Implementation decisions

- Python's standard library, SQLite, and browser JavaScript replace the proposed React/FastAPI stack to remove runtime installation overhead. HTTP, workflow, storage, and provider modules remain separate.
- Workflow records are JSON payloads in SQLite; FTS5 is a rebuildable concept index. The plan's separate relational tables and additional entity types remain expansion proposals.
- Retrieval uses concept-note granularity, lexical search, and concept-ID citations. Paragraph/page chunks, hybrid retrieval, and citation-entailment evaluation remain extensions. A valid ID establishes provenance, not correctness.
- The first graph accepts `requires` edges. Other relation types and a full ontology remain future adapters.
- A bounded coordinator handles teaching, questions, evaluation, and drafting. There are no unrestricted autonomous tools or deployed agent swarm.
- Offline grades stay uncertain until an explicit labeled self-assessment. Keyword matching never creates proficiency.
- Retention requires accepted independent success at least 24 hours later on a differently worded question. This is a transparent prototype rule, not a validated memory model.
- Notes start hidden during assessment; hints/tutor help and learner-disclosed assistance are recorded.
- Durable file projections preserve concurrent external edits and save conflicting proposed content separately.
- MIT licenses the application and original example material. External resources keep their own licenses.

## Verified locally

Automated tests cover evidence states, exact answers, retries, restart/resume, frozen references, AI failure recovery, invented quote rejection, structured provider contracts, cloud limits, secret exclusion, external edits, stale editor conflicts, frontmatter preservation, prerequisite cycles, interrupted writes, lossless restoration, checksum/shape/reference validation, path traversal, Host/Origin checks, request tokens, and static assets.

A browser walkthrough in a separate synthetic directory verified examples, study, theory questions, answer submission, self-assessment revision, restart/resume, drafts, hints without submission, a course linked to concepts, an ordered path, and the knowledge graph. Desktop (1280px) and narrow-screen (390px) checks found no document-level horizontal overflow.

The export API returned all concepts, a resource, the session note, and the original attempt from the browser walkthrough. The in-app browser's download-event inspection timed out; ordinary-browser download behavior remains a manual check. Archive integrity and restore are covered by tests.

The local environment used Python 3.11.15 and Node 24.14.1. The initial release's [CI run](https://github.com/hammadshakeelai/all-of-computing/actions/runs/37512106151) passed all four Windows/Linux and Python 3.11/3.13 jobs. CI verifies the automated suite, not educational effectiveness.

## Remaining validation and extensions

- No live paid AI call was made because OPENAI_API_KEY was not configured. Transport is tested with mocks; model access and grading quality need a configured pilot.
- Cross-discipline grading calibration needs reviewed real answers. Exact quote validation does not establish that a judgment is correct.
- Voice input, isolated code execution, PDFs, embeddings, course connectors, sync, and desktop packaging are not implemented.
- Sources remain under learner control. AI drafts and historical feedback are not automatically authoritative.
- Archives exclude non-Markdown attachments and have a 12 MB HTTP request limit. Larger installations should back up the private directory directly.

## Release checklist

- [x] Functional local learning loop.
- [x] Automated persistence/provider/security checks.
- [x] Browser walkthrough with synthetic history separate from personal data.
- [x] Setup, privacy, and recovery documentation.
- [ ] Live AI pilot and reviewed grading benchmark.
- [ ] Manual backup download check in an ordinary browser.

Public code and personal data remain separate. Browser-test history is not the user's learning record.
