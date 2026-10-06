# Contributing

Learning Atlas focuses on local CS/AI learning, inspectable evidence, and a portable knowledge vault. Read [scope](docs/SCOPE.md), [roadmap](docs/ROADMAP.md), and [architecture](docs/ARCHITECTURE.md) before proposing a major integration.

## Setup and checks

Run `python server.py --data-dir .runtime/dev --port 8766 --open` for synthetic development records. Python 3.11+ requires no third-party packages. Node is only needed for the syntax check.

```sh
python -m unittest discover -s tests -v
python -m compileall -q learning server.py
node --check web/app.js
```

Describe the concrete problem, changed behavior, verification, and remaining limitations. Keep changes focused. For UI changes, check keyboard use, empty/error states, and a narrow viewport. Changes to persistence, restore, grading, retrieval, and privacy need meaningful tests for their affected invariants.

## Learning and research contributions

Link primary references near claims. Distinguish source findings from recommendations. Mark whether a feature is shipped, proposed, or validated. Do not claim grading accuracy without a reviewed benchmark. Include alternative valid answers and ambiguous cases in assessment work. Respect external course licenses and assignment-sharing policies.

## Protect personal records

Use synthetic data in tests, screenshots, and issues. Never commit API keys, real answers, grades, transcripts, private syllabus annotations, or database exports. `.gitignore` protects default paths; it cannot protect every custom data directory. Review the staged diff before committing. Follow [security guidance](SECURITY.md) for vulnerabilities.

Contributed code and original examples are provided under the repository's MIT license. Clearly identify any third-party material and its applicable license. Keep discussion respectful and specific to the work.
