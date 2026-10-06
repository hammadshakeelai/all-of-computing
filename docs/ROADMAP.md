# Roadmap and validation gates

Updated 2026-10-06. Ordered by proposed value for a CS/AI learner around a BSAI degree. These are plans, not shipped features or promised dates.

| Stage | Outcome | Work | Gate before expanding |
| --- | --- | --- | --- |
| Shipped v1 | A usable local text learning loop | Study, frozen questions, evidence, review, Markdown, graph, paths, resources, backups | Existing automated tests and browser walkthrough; see release notes |
| 1 · Personal scope | A degree-aligned starting point | Map real syllabus; collect diagnostics and one small outcome; run the pilot | Learner confirms map; next activity is clear; management friction is recorded |
| 2 · Teaching trust | Feedback worth using | Reviewed CS/math/AI answer set; alternative answers; ambiguous rubrics; live provider pilot when configured | No known fabricated answer quotes; review false positives/negatives; publish measured results and remaining errors |
| 3 · Curriculum support | Less planning overhead | Syllabus/outcome import, local private profile, inspectable prerequisite mapping, optional reviewed study packs | Mapping never silently assigns proficiency; learner can revise and trace each recommendation |
| 4 · Better retrieval | Sources that support generated work | Query benchmark, note chunks, paragraph citations; compare lexical and optional hybrid search | Show measured retrieval improvement and citation support on the reviewed set |
| 5 · Practical CS/AI work | Assess implementation as well as explanation | Artifact links first; then isolated code tasks and result capture | Demonstrate isolation, time/resource limits, reproducibility, and assistance tracking |
| 6 · Optional conveniences | Reduce demonstrated friction | Local model adapter, voice, PDF ingestion, Anki export, connectors, packaging | A pilot shows the need; privacy, portability, and recovery still hold |

## Immediate research backlog

Gather the official degree outline and current modules privately. Diagnose selected outcomes without assuming the learner is a beginner. Complete a small project and a changed delayed task. Keep missed reviews, grading disputes, and time spent managing records visible.

## Evaluation work to design

Use synthetic or explicitly permissioned answers. Include correct alternative explanations, partially correct work, confidently wrong work, source conflicts, missing prerequisites, and failed provider requests. Separate grading correctness from answer persistence and citation format. Agree acceptance thresholds before running a benchmark; do not choose them after seeing results.

Semantic search should face an actual query set containing paraphrases and near-miss concepts. A citation ID passing validation is not enough: verify that the cited material supports the claim. Code tasks need a separate execution threat model before implementation.

## Constraints that carry forward

Personal data stays private by default. Record exact answers before evaluation. Preserve assistance, revisions, and uncertainty. Let the learner override planning choices and dispute judgments. Course completion does not imply independent competence. External content retains its license. New integrations must remain optional.

See [scope](SCOPE.md), [research](research/2026-10-06-scope-discovery.md), [release](RELEASE.md), and the [original detailed plan](PROJECT-PLAN.md).
