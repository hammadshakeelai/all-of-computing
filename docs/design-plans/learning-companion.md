# AI Learning Companion Design Plan — Local Learning Experience

This DesignPlan is a living document. Progress, Decision Log, and Surprises & Discoveries must stay up to date as work proceeds.

This applies the app-planner skill's user-goal and screen-milestone approach to a local browser app. Apple patterns are interaction references; this project has no SwiftUI or TCA code, and no iOS implementation dependency. Build-session prompts below replace platform-specific prompts.

## Purpose / Big Picture

Help the learner choose a useful next activity, learn interactively, understand assessment feedback, and inspect a durable history. Every progress claim should be explainable through evidence.

## User & Moments

- **Returning learner:** opens the app on their computer and wants to continue without re-explaining the past.
- **Exploring learner:** follows curiosity across subjects and wants to turn discoveries into manageable goals.

Frequency is a proposed relative ranking, not observed user behavior.

| Frequency | Moment | What they do |
|---|---|---|
| Many times per session | Study and dialogue | Explain, ask, attempt, get feedback |
| Several times per session | Review answer | Inspect feedback and correct reasoning |
| Once per visit | Choose next activity | Continue, review, or explore |
| Occasionally each day | Find knowledge | Search concepts and inspect sources |
| Weekly or when goals change | Plan and inspect progress | Adjust paths and review evidence |
| At setup and as needed | Manage local data | Configure AI, export, restore |

## Progress

- [x] Milestone 1: Study
- [x] Milestone 2: Answer and Feedback
- [x] Milestone 3: Today
- [x] Milestone 4: Library and Concept Detail
- [x] Milestone 5: Goals and Learning Path
- [x] Milestone 6: Knowledge Map
- [x] Milestone 7: Progress and Evidence
- [x] Milestone 8: Settings and Data

All screen areas are implemented at local v1 scope. Live AI quality and ordinary-browser download behavior remain validation items; see [RELEASE.md](../RELEASE.md).

## Design Milestones

### Milestone 1: Study

**User goal:** “Teach me, let me ask questions, and help me think it through.”
**Pattern:** Card vs Row Grammar (Fitness/Contacts).
**Priority:** Must-have.
**Frequency:** Highest; repeated interaction during sessions.
**Existing domain:** None; proposed sessions and learning workflows.

**Features:**
- Visible objective and current step — keep the session purposeful.
- Text dialogue with code and equations — support varied subjects.
- Distinct study and assessment modes — reveal whether help affects evidence.
- Optional source panel and expandable hints — make grounding inspectable.
- Pause and resume — preserve unfinished work.

**Acceptance criteria:**
1. After restart, the objective, pending task, and submitted answers reappear.
2. Hints are recorded and visibly affect independence classification.
3. An AI timeout leaves a recoverable state and preserves input.

**Build-session prompt:**
> Build the Study screen for a local browser learning app. Use Card vs Row Grammar to distinguish session context from chronological learning steps. Keep the objective visible and preserve answers and pending questions. Include loading, failed-provider, and resume states. Use the first-build contracts and mock provider.

### Milestone 2: Answer and Feedback

**User goal:** “Tell me what I understood, what I missed, and why.”
**Pattern:** Metric Detail Template (Health).
**Priority:** Must-have.
**Frequency:** After each assessment.
**Existing domain:** None; proposed attempts and assessments.

**Features:**
- Autosaved response editor and explicit submission — prevent accidental answer loss.
- Rubric dimensions and linked answer spans — explain judgments.
- Uncertainty, correction, and dispute controls — support ambiguous or unfair grades.
- Next exercise — turn feedback into learning.

**Acceptance criteria:**
1. Every quoted answer span exists in the submitted response.
2. The rubric is frozen before submission and revisions remain inspectable.
3. Writing style is graded only when the objective requires it.

**Build-session prompt:**
> Build the Answer and Feedback screen using a Metric Detail Template. Show the learner's exact answer, rubric judgments, supporting spans, uncertainty, and correction opportunities. Preserve original and revised grades. Do not reduce the screen to an overall percentage.

### Milestone 3: Today

**User goal:** “Give me one useful thing to do with the time I have.”
**Pattern:** Dashboard Cards (Fitness).
**Priority:** Must-have.
**Frequency:** Every visit.
**Existing domain:** None; proposed goals and reviews.

**Features:**
- Time budget and one primary suggestion — reduce decision burden.
- Continue session, due review, or explore — accommodate different intentions.
- Brief recommendation reason — preserve learner control.
- Honest empty state — offer a diagnostic without inventing progress.

**Acceptance criteria:**
1. A new learner sees no fabricated scores or achievements.
2. The learner starts or resumes an activity from one clear primary action.
3. Each recommendation gives an inspectable reason and can be overridden.

**Build-session prompt:**
> Build Today with Dashboard Cards for a returning learner with limited time. Show one primary activity, its reason, and clear continue/review/explore alternatives. Respect review caps and unknown proficiency. Use only saved evidence for progress.

### Milestone 4: Library and Concept Detail

**User goal:** “Find this idea, my explanation, and the sources behind it.”
**Pattern:** Card vs Row Grammar (Fitness/Contacts).
**Priority:** Must-have, initially minimal.
**Frequency:** Several times per learning day.
**Existing domain:** None; proposed concepts, resources, and vault projection.

**Features:**
- Searchable concepts and resources — retrieve across subjects.
- Authored explanation and linked prerequisites — organize usable knowledge.
- Source locations and evidence links — distinguish reference material from learner ability.
- Open note in external editor — preserve ownership.

**Acceptance criteria:**
1. Search results link to the correct concept and source location.
2. Editing a note outside the app preserves learner evidence.
3. Missing, malformed, and conflicting notes produce actionable states.

**Build-session prompt:**
> Build a Library and Concept Detail screen using Card vs Row Grammar. Keep authored knowledge, source provenance, and learner evidence clearly labeled. Follow field ownership and external-edit conflict rules in DATA-CONTRACT.md.

### Milestone 5: Goals and Learning Path

**User goal:** “Turn my curiosity into an achievable sequence.”
**Pattern:** Hierarchical Zoom (Calendar).
**Priority:** Next after the first learning loop.
**Frequency:** Weekly and when selecting new goals.
**Existing domain:** None; proposed goals, objectives, and path steps.

**Features:**
- Outcome-first goal editor — define what success looks like.
- Prerequisite-aware ordered steps — identify a workable starting point.
- Separate active goals and exploration backlog — support breadth without overload.
- Adjustable scope and time budget — fit real life.

**Acceptance criteria:**
1. Each path step names an observable objective and an activity.
2. Unknown prerequisites invite a diagnostic rather than assuming failure.
3. The learner can reorder or reject AI-proposed steps.

**Build-session prompt:**
> Build Goals and Learning Path with Hierarchical Zoom from outcomes to objectives to activities. Explain prerequisite suggestions, keep active goals manageable, and make AI proposals editable.

### Milestone 6: Knowledge Map

**User goal:** “Show how ideas connect and where I should explore next.”
**Pattern:** Hierarchical Zoom (Calendar).
**Priority:** Later, after concepts and evidence are reliable.
**Frequency:** Occasional exploration.
**Existing domain:** None; proposed typed relationships.

**Features:**
- Local concept neighborhood with relation filters — keep the graph readable.
- Prerequisite direction and proposal status — avoid misleading connections.
- Evidence overlays — show unknown, encountered, and demonstrated concepts.
- Equivalent list view — support keyboard and accessible navigation.

**Acceptance criteria:**
1. A displayed edge exposes its type and provenance.
2. Every graph action is possible in the list view.
3. A dense graph is filtered before rendering; note count is not shown as proficiency.

**Build-session prompt:**
> Build a filtered Knowledge Map with Hierarchical Zoom. Show small neighborhoods, typed edges, prerequisite direction, and evidence-backed states. Include a complete accessible list equivalent. Do not require a graph database.

### Milestone 7: Progress and Evidence

**User goal:** “What have I demonstrated, and what still needs checking?”
**Pattern:** Metric Detail Template (Health).
**Priority:** Minimal history first; richer view later.
**Frequency:** Weekly and when questioning a progress claim.
**Existing domain:** None; proposed evidence events and derived proficiency.

**Features:**
- Objective-level evidence states — distinguish exposure and performance.
- Assessment history with assistance and recency — make progress explainable.
- Review-needed and disputed evidence indicators — expose uncertainty.
- Activity metrics separated from proficiency — avoid misleading completion badges.

**Acceptance criteria:**
1. Every demonstrated/retained state links to actual attempts.
2. Unknown remains distinct from incorrect.
3. Grade revision updates the derived view while retaining history.

**Build-session prompt:**
> Build Progress and Evidence using Metric Detail Template. Present assessed objectives, assistance, recency, and uncertainty with drill-down to attempts. Keep activity and demonstrated proficiency separately labeled.

### Milestone 8: Settings and Data

**User goal:** “Control my AI, my spending, and my records.”
**Pattern:** Card vs Row Grammar (Contacts).
**Priority:** Minimal configuration/export in the first loop.
**Frequency:** Setup and occasional maintenance.
**Existing domain:** None; proposed configuration and export service.

**Features:**
- Provider and context permissions — make optional cloud use explicit.
- Budget caps — prevent unexpected paid requests.
- Vault location, export, backup, and restore — preserve data independence.
- Teaching language and timezone — support personal preferences.

**Acceptance criteria:**
1. Keys never appear in exported archives or app logs.
2. Cloud-off mode makes no provider requests.
3. Restore reports included/excluded data and preserves evidence IDs.

**Build-session prompt:**
> Build Settings and Data using structured rows. Include AI configuration, permitted context, budgets, local storage, export/restore, teaching language, and timezone. Show recoverable configuration failures and never render secrets in summaries.

## Deliberate Omissions

- Native mobile UI and live voice — validate the local text experience first.
- Social leaderboards and streak pressure — focus on understanding and retention.
- Universal knowledge map — expand from meaningful learner goals.
- Pixel layouts and visual themes — select during implementation after workflows are validated.

## Decision Log

- 2026-10-06: adapt the skill's screen-planning structure to the confirmed local browser direction.
- 2026-10-06: eight screen milestones define the eventual product; FIRST-BUILD.md implements only their minimum necessary subset.

## Surprises & Discoveries

- The repository has no application code or existing reducers/domains.
- Local operation and optional cloud AI require separate controls for stored data and transmitted context.
