# Initial scope research: CS, AI, and a BSAI learning companion

Research date: 2026-10-06. This is a preliminary desk review of primary sources and the current implementation. It is not a systematic literature review, learner assessment, market validation, or university accreditation analysis.

## Questions investigated

What should a broad CS/AI learner organize first? Which existing tools already solve parts of the problem? What deserves custom implementation? Which assumptions require real learning evidence rather than more features?

Confirmed user direction: computer science and AI, around a BSAI degree; local computer with optional cloud AI; help with learning, discovering existing knowledge, and keeping records. Precise university requirements, semester, available time, and proficiency have not been supplied.

## Finding 1: use a broad map, then a narrow active outcome

CS2023 includes programming, algorithms, systems, mathematics/statistics, AI, data, security, software engineering, HCI, and professional responsibility among its 17 knowledge areas. This provides a coverage checklist rather than a personalized timetable. [ACM/IEEE-CS/AAAI knowledge areas](https://csed.acm.org/knowledge-areas/).

The AI curriculum authors discuss integrating AI across CS, with mathematical and statistical preparation supporting deeper work. This argues for retaining foundations rather than equating AI study with prompting or a single framework. [CS2023 AI rationale and challenges](https://csed.acm.org/wp-content/uploads/2024/08/30352-Article-Text-34406-1-2-20240324.pdf).

**Our recommendation:** align the actual degree syllabus first, then organize supplementary CS and AI study by prerequisites and outcomes. Keep one main objective active, with a supporting math track where needed. The number of concurrent tracks is a management hypothesis to test, not a result established by the sources.

For a possible Pakistan degree context, HEC provides a revised 2025–26 computer science curriculum and an official revision announcement covering AI among specializations. This is a conditional reference only: we do not know the learner's university, country of study, cohort, or adopted curriculum. Do not substitute the national publication for the institution's official BSAI scheme. [HEC curriculum index](https://www.hec.gov.pk/english/services/universities/RevisedCurricula/Pages/default.aspx), [official revision announcement](https://www.hec.gov.pk/english/news/news/Pages/HEC-in-Collaboration-with-Academia.aspx).

## Finding 2: reuse instruction and storage; connect the evidence

| Primary source | What it establishes | Proposed role in Learning Atlas |
| --- | --- | --- |
| [Obsidian storage documentation](https://obsidian.md/help/data-storage) | Vaults are local plain-text Markdown files and can be edited externally | Keep portable notes; maintain learner attempts separately in local records |
| [Anki background](https://docs.ankiweb.net/background.html) | Supports active recall and spaced repetition across content types | Complementary factual recall; consider export later if duplicate review queues become burdensome |
| [Open WebUI RAG documentation](https://docs.openwebui.com/features/chat-conversations/rag/) | Retrieves source context to support conversations | Potential future document-chat/local-model complement; do not recreate every chat feature |
| [OSSU curriculum](https://github.com/ossu/computer-science) | A structured self-study CS curriculum with prerequisites, core study, electives, and a final project | Resource discovery and gap checking; align selected resources to the actual degree |
| [Boot.dev backend path](https://www.boot.dev/paths/backend?tech=python-golang) | A programming path combining courses and guided projects | Reference for task-based practice design; manual resource tracking remains sufficient for v1 |

These official descriptions establish capabilities, not comparative quality, affordability for this learner, or a guarantee of integration. Learning Atlas has no affiliation with these projects. Current prices, access, course availability, and assignment policies must be checked before enrolling. Store links and your own summaries; do not republish third-party course content without permission.

**Our product inference:** the useful focus is connecting goals, source notes, practice attempts, feedback revisions, and future review in one inspectable local workflow. This desk review does not prove that competing tools lack those capabilities or that this app is uniquely positioned.

## Finding 3: knowledge graphs need practice alongside them

Karpicke and Blunt's 2011 experiment found retrieval practice benefits for conceptual learning from science texts, including comprehension and inference questions, compared with the study conditions examined. It supports asking learners to reconstruct understanding, not merely accumulating or arranging notes. We reviewed the abstract, not the full paper or every replication. It does not validate this app's grading, review schedule, or every discipline. [Original study abstract](https://pubmed.ncbi.nlm.nih.gov/21252317/).

**Our design inference:** combine explanation, application, feedback, and delayed new questions. Record hints and source access so assisted success is distinguishable from independent performance. A colorful graph should help navigate topics, while actual answers remain the evidence.

Current implementation: frozen prompts and references, exact saved answers, assisted/independent labels, revisions and disputes. Retention requires accepted independent success at least 24 hours later on a differently worded prompt. That threshold and the 1/3/7/14/30-day review intervals are prototype rules, not calibrated scientific estimates of durable knowledge.

## Finding 4: source retrieval and learning retention are different problems

The original RAG paper studies a model combining parametric generation with retrieved external information for knowledge-intensive NLP tasks. Its task results do not establish whether a learner understands an answer or whether a retrieved citation supports every claim. [Lewis et al., 2020](https://arxiv.org/abs/2005.11401).

Learning Atlas currently uses SQLite FTS5 over concept notes and concept-ID citations. It has no semantic embeddings, paragraph-level citation matching, or trained RAG model. **Recommendation:** first measure whether retrieved notes support the questions and feedback being generated. Add semantic retrieval only if a reviewed query set shows lexical search missing necessary material.

## Priority decisions

| Decision | Reason | What could change it |
| --- | --- | --- |
| CS/AI centered on the BSAI degree | Explicit learner preference | Updated learner objective |
| Actual syllabus before a universal course list | Degree requirements are institution/cohort-specific | Syllabus and semester become available |
| Diagnose before assigning a level | Learner reports scattered existing knowledge | Reviewed independent work samples |
| Improve feedback trust before integrations | Present grading has no live educational calibration | A reviewed benchmark shows acceptable behavior |
| Keep local Markdown + structured records | Existing implementation supports portability and evidence | Measured recovery or usability problems |
| Reuse courses and tools | Existing instruction is available | A specific gap lacks a suitable resource |
| Defer embeddings/voice/sandboxed code | Their value for this learner is untested | Pilot evidence shows a blocking limitation |

## Next research: with the learner

1. Obtain the official university scheme and current module outlines privately; map outcome, prerequisite, assessment, source, and deadline.
2. Sample five to ten outcomes across programming, discrete math, linear algebra, probability, and introductory AI. Do not treat a small sample as a complete ability profile.
3. Ask for an explanation, a worked problem, and a changed application task. Save before instruction; note assistance and confidence.
4. Compare judgments with trusted references or instructor review. Mark ambiguity, alternative valid answers, and rubric defects.
5. Run the six-session pilot in [scope](../SCOPE.md), measure management friction, and choose the next outcome from observed gaps.

Public documentation contains framework-level guidance only. Actual answers, marks, deadlines, and personal syllabus annotations should stay in the private vault.

A separately checked [resource shortlist](../RESOURCES.md) includes official Harvard, MIT, Stanford, and Dive into Deep Learning pages. Its selection advice and proposed evidence tasks are our synthesis, not university course-equivalence claims.

## Confidence and limitations

High confidence: the user's CS/AI direction, official tool capabilities described above, and actual implemented storage/workflow behavior. Moderate confidence: the proposed curriculum grouping as a useful starting framework. Unvalidated: the learner's starting level, optimal workload, grading accuracy, product usefulness over existing tools, and the value of additional integrations.

Primary pages were checked on the research date. Course lists and software documentation can change. Recommendations are explicitly our synthesis; no source endorses Learning Atlas. See [scope](../SCOPE.md), [personal worksheet](../PERSONAL-SCOPE.md), and [roadmap](../ROADMAP.md) for the resulting plan.
