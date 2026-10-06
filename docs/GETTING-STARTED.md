# Getting started with Learning Atlas

A local-first learning app with optional AI tutoring, theory questions, quizzes, walkthroughs, saved learning evidence, review scheduling, and an Obsidian-compatible knowledge vault. Study computing, mathematics, science, humanities, or your own subjects in one place.

**Working v1:** Python 3.11+, no third-party runtime dependencies, no account needed for offline practice. Cloud AI starts disabled.

## Run it

```powershell
git clone https://github.com/hammadshakeelai/all-of-computing.git
cd all-of-computing
python server.py --open
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). On Windows, you can also double-click `start.cmd`. Keep the terminal running while studying; press Ctrl+C to stop.

If `python` is not on PATH, try `py -3 server.py --open`. If the port is occupied, use `python server.py --port 8766 --open`.

## Your first session

1. Add a concept with your explanation or a permitted source excerpt, import a Markdown note, or load the example library.
2. Select **Study**, or **Discover what I know** for a recall-first diagnostic.
3. Choose a theory answer, short answer, or applied walkthrough. Cloud AI also generates multiple-choice quizzes.
4. Submit an answer. It is saved before evaluation, even if AI fails.
5. Inspect feedback, compare the reference, and record or dispute a judgment. Offline practice invites explicit self-assessment; it does not pretend to grade meaning.
6. Return to the saved session or scheduled review. Evidence distinguishes exposure, assisted success, independent success, and delayed retention.

## Included

| Area | Working behavior |
|---|---|
| Today | Continue sessions; find due reviews and active goals |
| Study | Saved text dialogue, explain/apply prompts, hints, drafts, optional read aloud |
| Assessment | Frozen rubrics, theory/short/quiz/walkthrough modes, retry-safe submissions |
| Feedback | Validated answer quotes, uncertainty, self-assessment and dispute revisions |
| Library | Add/edit/import Markdown, search, prerequisites, sources |
| AI lesson drafting | Start from a topic and level; review an unverified draft before saving |
| Courses and tools | Register resources, manual progress, and linked concepts |
| Learning paths | Outcomes, time budgets, ordered concepts, pause/activate/complete controls |
| Review | Transparent 1/3/7/14/30-day intervals and capped due queue |
| Knowledge map | Prerequisite arrows, subject filtering, evidence overlays, equivalent list |
| Learning evidence | Original answers, assistance, grading origin, assessment revisions |
| Data ownership | Markdown vault, SQLite records, JSON export/restore, checksums, snapshots |

The graph shows up to 24 concepts at a time. Filter by subject for a smaller map. Reading or course completion alone never establishes independent proficiency.

## Optional OpenAI tutoring

Configure the key in the terminal **before starting the app**:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
python server.py --open
```

On macOS/Linux:

```sh
export OPENAI_API_KEY="your-api-key"
python3 server.py --open
```

In **Settings & data**, enter a model available to your API account, choose a teaching language, and explicitly enable cloud AI. The app uses the [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) with [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), bounded output, a 60-second timeout, and `store: false`.

Selected notes, recent dialogue, questions, and submitted answers are sent to OpenAI when enabled. Local storage does not make those requests private. The key stays in the process environment, never in the browser, archive, or app logs. This app does not automatically read `.env` files.

Daily request limits include failed requests and reset at midnight UTC. They limit requests, not money; configure account spending controls separately. Learning dates display in Asia/Karachi.

**Live cloud behavior has not been verified with a paid API call in the initial build.** Provider payloads, output validation, and failure recovery have mocked tests. Model/account compatibility and educational grading quality need a configured pilot. AI-generated lessons are labeled unverified drafts.

## Obsidian and personal storage

```text
private/
  records.sqlite3       # answers, sessions, assessments, goals, resources, reviews
  vault/
    Concepts/           # authored Markdown with frontmatter and wiki links
    Sessions/           # generated readable learning summaries
    Conflicts/          # preserved proposed content after concurrent writes
  backups/              # snapshots made before restores
```

Open `private/vault` as an Obsidian vault. Edit notes outside the app and select **Refresh vault** to import text changes and update search. IDs survive renames. Missing notes do not erase assessment evidence. Use the app's prerequisite editor for cycle-checked relationships; external prerequisite edits are not automatically accepted. Unknown frontmatter is preserved.

Use a custom location with `python server.py --data-dir "D:\LearningData" --open`. Personal data and API keys are ignored by Git. Choose a private location if it is outside the default directory.

## Back up and restore

Use **Settings & data → Download backup**. The JSON archive contains Markdown, structured records, schema version, checksums, and non-secret preferences. Search is rebuildable. Non-Markdown attachments are excluded; back them up separately.

Restore merges records, rejects conflicts, validates paths and references before writing, and saves a pre-restore snapshot. Cloud AI is disabled afterward. For a full recovery, start with an empty directory and restore there:

```powershell
python server.py --data-dir "D:\RecoveredLearning" --port 8766 --open
```

Import/export request size is limited to 12 MB. Keep a filesystem backup of the entire private directory for larger collections. Markdown alone does not restore assessment history.

## Verification and development

```powershell
python -m unittest discover -s tests -v
python -m compileall -q learning server.py
node --check web/app.js
```

Node is only needed for the optional JavaScript check, not to run the app. CI tests Python 3.11 and 3.13 on Windows and Linux. Tests cover persistence, restart/resume, evidence rules, grading disputes, retries, AI failures, imports, concurrent edits, restore integrity, and request protections.

Architecture: standard-library Python HTTP server, SQLite/FTS5, and an unbundled browser UI. The API binds to loopback and validates Host/Origin and per-process request tokens. Imported content is escaped text. This release is for one trusted local user, not public hosting or shared accounts.

## Scope and project documents

The local text learning workflow is implemented. Voice input, isolated code execution, PDFs, semantic embeddings, automatic course-platform synchronization, multi-device sync, and packaged installers remain extensions. Read aloud depends on your browser's speech service. Learner code is never executed.

- [Project plan](PROJECT-PLAN.md)
- [Screen design plan](design-plans/learning-companion.md)
- [Proposed data contract](DATA-CONTRACT.md)
- [First build brief](FIRST-BUILD.md)
- [Release and validation](RELEASE.md)

Licensed under [MIT](../LICENSE).
