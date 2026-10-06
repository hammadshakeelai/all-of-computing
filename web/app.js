const $ = (s, root = document) => root.querySelector(s);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const id = () => crypto.randomUUID();
const views = [
  ["today", "⌂", "Today"],
  ["study", "▤", "Study"],
  ["library", "▥", "Knowledge library"],
  ["goals", "◎", "Learning paths"],
  ["review", "↻", "Review"],
  ["graph", "◇", "Knowledge map"],
  ["progress", "▧", "Learning evidence"],
  ["settings", "⚙", "Settings & data"],
];
let state,
  view = location.hash.slice(1) || "today",
  activeSession,
  filter = "",
  domain = "",
  busy = false,
  saveTimer;
const draftKeys = new Set();
let toastTimer;
function toast(message, duration = 6000) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("visible"), duration);
}
function fmt(date) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "Asia/Karachi",
  }).format(new Date(date));
}
function badge(p) {
  return `<span class="badge ${p.state === "Unknown" ? "unknown" : p.state.includes("help") ? "assisted" : ""}">${esc(p.state)}</span>`;
}
function button(label, action, value = "", primary = false) {
  return `<button type="button" class="btn ${primary ? "primary" : ""}" data-action="${action}" data-id="${esc(value)}">${label}</button>`;
}
function prose(value) {
  return String(value || "")
    .split(/(```[\s\S]*?```)/g)
    .map((part) =>
      part.startsWith("```")
        ? `<pre>${esc(part.replace(/^```[^\n]*\n?/, "").replace(/```$/, ""))}</pre>`
        : part
            .split(/\n\s*\n/)
            .filter(Boolean)
            .map((p) => `<p>${esc(p)}</p>`)
            .join(""),
    )
    .join("");
}
function heading(title, subtitle, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">Your learning workspace</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
function empty(title, description, action = "") {
  return `<div class="empty"><div class="empty-icon">◇</div><h3>${title}</h3><p>${description}</p>${action}</div>`;
}
function concept(cid) {
  return state.concepts.find((c) => c.id === cid);
}
function session() {
  return state.sessions.find((s) => s.id === activeSession);
}
function available() {
  return state.concepts.filter((c) => !c.missing);
}
async function api(path, data) {
  const options = { headers: { "X-App-Token": state?.csrf_token || "" } };
  if (data !== undefined)
    Object.assign(options, {
      method: "POST",
      headers: { ...options.headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  const response = await fetch("/api/" + path, options);
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.error || "The operation failed. Please retry.");
  return body;
}
async function reload() {
  state = await api("state");
  if (!activeSession)
    activeSession = [...state.sessions]
      .reverse()
      .find((s) => s.status === "active")?.id;
}
function render() {
  if (!views.some((v) => v[0] === view)) view = "today";
  const label = views.find((v) => v[0] === view)[2];
  $("#app").innerHTML =
    `<div class="shell"><aside class="sidebar"><div class="brand"><img src="/favicon.svg" alt=""><div>Learning Atlas<small>ALL OF COMPUTING</small></div></div><nav class="nav" aria-label="Main navigation">${views.map(([key, icon, name]) => `<button data-action="nav" data-id="${key}" class="${view === key ? "active" : ""}" ${view === key ? 'aria-current="page"' : ""}><span class="nav-icon" aria-hidden="true">${icon}</span>${name}</button>`).join("")}</nav><div class="sidebar-footer"><span class="status-dot"></span>Records saved locally<br>${state.settings.cloud_enabled ? "Optional cloud AI enabled" : "Offline practice mode"}<br>Notes you can keep. Evidence you can inspect.</div></aside><div class="workspace"><header class="topbar"><div class="breadcrumb">Learning Atlas <span aria-hidden="true"> / </span><b>${label}</b></div><div class="date">${new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric", timeZone: "Asia/Karachi" }).format(new Date())}</div></header><main id="main" tabindex="-1">${state.warnings.length ? `<div class="note warning">Vault notices: ${state.warnings.map(esc).join(" · ")}</div>` : ""}${pages[view]()}</main></div></div>`;
  if (busy) showBusy(true);
}
function navigate(v) {
  view = v;
  location.hash = v;
  filter = "";
  domain = "";
  render();
  $("#main").focus({ preventScroll: true });
}
function showBusy(on) {
  document.querySelectorAll(".busy-bar,.busy-label").forEach((e) => e.remove());
  if (on) {
    const div = document.createElement("div");
    div.className = "busy-bar";
    document.body.append(div);
    const label = document.createElement("div");
    label.className = "busy-label";
    label.textContent = "Saving your work…";
    document.body.append(label);
  }
}
async function run(work, success) {
  if (busy) return;
  busy = true;
  showBusy(true);
  try {
    await work();
    await reload();
    render();
    if (success) toast(success);
  } catch (error) {
    toast(error.message, 12000);
    try {
      await reload();
    } catch {} /* Keep editors intact after failure. */
  } finally {
    busy = false;
    showBusy(false);
  }
}
function card(c) {
  return `<article class="panel concept-card"><div class="tag">${esc(c.domain)}${c.origin === "demo" ? " · Example material" : ""}</div><h3>${esc(c.title)}</h3><p>${esc(c.body.replace(/^#+\s*/, "").slice(0, 150))}${c.body.length > 150 ? "…" : ""}</p><div>${badge(c.proficiency)}</div><div class="actions">${button("Study →", "start", c.id, true)}${button("Open note", "open-concept", c.id)}</div></article>`;
}
const pages = {
  today() {
    const active = [...state.sessions]
      .reverse()
      .find((s) => s.status === "active");
    const demonstrated = state.concepts.filter((c) =>
      ["Demonstrated independently", "Retained"].includes(c.proficiency.state),
    ).length;
    const next =
      available().find((c) => c.proficiency.state === "Unknown") ||
      available()[0];
    return (
      heading(
        "What would you like to understand?",
        "A place to explore ideas, practice what matters, and remember what you learn.",
        button("Add a concept", "new-concept"),
      ) +
      `<div class="stats"><div class="stat"><strong>${state.concepts.length}</strong><span>Concepts in your library</span></div><div class="stat"><strong>${demonstrated}</strong><span>Independently demonstrated</span></div><div class="stat"><strong>${state.due.length}</strong><span>Reviews ready today</span></div></div>` +
      `<section class="panel hero"><div class="eyebrow">Your next step</div><h2>${active ? "Pick up where you left off" : state.due.length ? "Bring an idea back to mind" : next ? `Explore ${esc(next.title)}` : "Start with one idea"}</h2><p>${active ? `Your session on ${esc(concept(active.concept_id)?.title)} is saved, including your questions and answers.` : state.due.length ? "A short recall exercise can show what stayed with you. Choose a due review below." : next ? "This concept has no independent evidence yet. Read, explain, and try an example to discover what you understand." : "Add something you want to learn, paste a note you already have, or load the small example library. Nothing here assumes what you already know."}</p><div class="actions">${active ? button("Continue session →", "resume", active.id, true) : state.due.length ? button("Review an idea →", "review-start", state.due[0].concept_id, true) : next ? button("Start learning →", "start", next.id, true) : button("Add your first concept →", "new-concept", "", true)}${!state.concepts.length ? button("Explore example library", "examples") : button("Browse library", "nav", "library")}</div><div class="flow"><span>Choose an objective</span><i>→</i><span>Explain & apply</span><i>→</i><span>Save evidence</span><i>→</i><span>Recall later</span></div></section>` +
      `<div class="grid"><section class="panel"><div class="panel-heading"><h2>Ready for review</h2>${button("See reviews", "nav", "review")}</div>${
        state.due.length
          ? state.due
              .slice(0, 3)
              .map((r) => reviewRow(r))
              .join("")
          : empty(
              "Nothing due yet",
              "Reviews appear after you submit an assessment. You can practice any concept whenever you want.",
            )
      }</section><section class="panel"><div class="panel-heading"><h2>Your learning paths</h2>${button("Plan a goal", "new-goal")}</div>${
        state.goals
          .filter((g) => g.status === "active")
          .slice(0, 3)
          .map(
            (g) =>
              `<div class="row"><div><div class="row-title">${esc(g.title)}</div><small>${g.concept_ids.length} concepts · ${esc(g.budget)}</small></div>${button("Open", "nav", "goals")}</div>`,
          )
          .join("") ||
        empty(
          "Make room for your curiosity",
          "Choose a goal and an ordered set of ideas to study. Keep the rest in your library for later.",
        )
      }</section></div>`
    );
  },
  library() {
    const list = available().filter(
      (c) =>
        (!domain || c.domain === domain) &&
        (!filter ||
          `${c.title} ${c.body} ${c.domain}`
            .toLowerCase()
            .includes(filter.toLowerCase())),
    );
    return (
      heading(
        "Your knowledge, connected.",
        "Keep explanations, sources, and prerequisites together. Open the vault in Obsidian at any time.",
        `<div class="actions">${button("Import Markdown", "import-note")}${button("Add a concept", "new-concept", "", true)}</div>`,
      ) +
      `<div class="toolbar"><label class="sr-only" for="search">Search concepts</label><input id="search" class="search" placeholder="Find an idea, example, or source…" value="${esc(filter)}"><label class="sr-only" for="domain">Filter by subject</label><select id="domain" class="filter"><option value="">All subjects</option>${[
        ...new Set(available().map((c) => c.domain)),
      ]
        .sort()
        .map(
          (d) => `<option ${d === domain ? "selected" : ""}>${esc(d)}</option>`,
        )
        .join(
          "",
        )}</select></div><div id="library-results" class="grid three">${list.map(card).join("") || `<section class="panel">${empty("Your library starts here", "Add a concept or import a Markdown note. You can also explore the bundled example material.", button("Load examples", "examples"))}</section>`}</div><p class="technical">Obsidian vault: ${esc(state.vault_path)}</p>`
    );
  },
  study() {
    const s = session();
    if (!s)
      return (
        heading(
          "A conversation with an objective.",
          "Pick a concept to start, or resume a previous session.",
        ) +
        `<section class="panel">${
          available().length
            ? available()
                .map(
                  (c) =>
                    `<div class="row"><div><div class="row-title">${esc(c.title)}</div>${badge(c.proficiency)}</div><div class="actions">${button("Study", "start", c.id, true)}${button("Diagnose", "diagnostic-start", c.id)}</div></div>`,
                )
                .join("")
            : empty(
                "Add an idea first",
                "Your tutor needs something to teach from. Start with a concept and a source.",
                button("Open library", "nav", "library"),
              )
        }</section>`
      );
    const c = concept(s.concept_id),
      q = s.question;
    const attempts = s.attempts.filter((a) => a.question_id === q?.id),
      attempt = attempts.at(-1);
    const grades = s.assessments.filter((g) => g.attempt_id === attempt?.id);
    const grade = grades.at(-1);
    return (
      heading(
        esc(c?.title || "Study session"),
        `${s.mode === "diagnostic" ? "Discover what you already know" : s.mode === "review" ? "Recall before reopening your notes" : "Understand, explain, then apply"} · ${state.settings.cloud_enabled ? "AI tutor" : "Offline practice"}`,
        `<div class="actions"><label class="sr-only" for="session-switch">Choose a session</label><select id="session-switch" class="filter session-select">${[
          ...state.sessions,
        ]
          .reverse()
          .map(
            (x) =>
              `<option value="${esc(x.id)}" ${x.id === s.id ? "selected" : ""}>${esc(concept(x.concept_id)?.title)} · ${fmt(x.created_at)}${x.status === "complete" ? " · finished" : ""}</option>`,
          )
          .join("")}</select>${button("Finish session", "finish", s.id)}</div>`,
      ) +
      `<div class="split"><div><section class="panel flush"><div class="chat" id="chat">${s.messages.map((m) => `<div class="message ${m.role === "you" ? "you" : ""}"><div class="label">${m.role === "you" ? "You" : state.settings.cloud_enabled ? "Tutor" : "Practice guide"}</div><div class="prose">${prose(m.text)}</div>${m.source_ids?.length ? `<div class="source">Notes: ${m.source_ids.map((cid) => `<button class="link-button" data-action="open-concept" data-id="${esc(cid)}">${esc(concept(cid)?.title || cid)}</button>`).join(" · ")}</div>` : ""}</div>`).join("")}</div><form id="chat-form" class="chat-form"><label class="field">Ask a question<textarea name="message" placeholder="Explain it another way, give me an example, or help me find a gap…" required maxlength="6000"></textarea></label><div class="actions"><button class="btn primary">${state.settings.cloud_enabled ? "Ask tutor" : "Use practice guide"}</button>${button("Read aloud", "speak", s.id)}</div><p class="privacy">${state.settings.cloud_enabled ? "This question, recent dialogue, and selected notes will be sent to OpenAI." : "Your notes and answers stay on this computer. Enable cloud AI in Settings for adaptive teaching."}${q && !grade ? " Help during an assessment marks your answer as assisted." : ""}</p></form></section>${q ? questionPanel(s, q, attempt, grade) : `<section class="panel"><h2>Make your understanding visible</h2><p class="muted">Choose a question, answer from memory, then inspect your feedback.</p>${questionButtons(s)}</section>`}</div><aside><section class="panel"><div class="eyebrow">Your source</div><h2>${esc(c?.title)}</h2>${(!q || grade || s.hint_used) && (s.mode === "learn" || s.mode === "walkthrough") ? `<div class="prose">${prose(c?.body)}</div>` : `<p class="muted">Try recalling first. Opening this source during an active question marks the attempt as assisted.</p>${button("Show explanation", "show-source", c?.id)}`}<div class="source">${sourceLink(c?.source)}${c?.origin === "demo" ? "<p>Illustrative example material. No prior learning history is implied.</p>" : ""}</div></section><section class="panel"><h3>Evidence so far</h3>${badge(c?.proficiency || { state: "Unknown" })}<p class="privacy">${c?.proficiency.attempts || 0} saved attempts. Reading records exposure; independent answers provide evidence. Self-assessments remain labeled in history.</p>${button("Inspect evidence", "nav", "progress")}</section></aside></div>`
    );
  },
  goals() {
    return (
      heading(
        "Give your curiosity a direction.",
        "Define an outcome, choose an ordered path, and study at a pace you can keep.",
        button("Create a learning path", "new-goal", "", true),
      ) +
      (!state.goals.length
        ? `<section class="panel">${empty("What would you like to be able to do?", "Try a concrete outcome such as “explain recursion and trace a small program.” Add concepts to your library, then choose them in order.", button("Create a path", "new-goal", "", true))}</section>`
        : state.goals
            .map(
              (g) =>
                `<section class="panel"><div class="panel-heading"><div><div class="tag">${esc(g.status)} · ${esc(g.budget)}</div><h2>${esc(g.title)}</h2></div><div class="actions">${button(g.status === "active" ? "Pause" : "Activate", g.status === "active" ? "pause-goal" : "activate-goal", g.id)}${button("Mark complete", "complete-goal", g.id)}</div></div>${
                  g.concept_ids
                    .map((cid, i) => {
                      const c = concept(cid);
                      return `<div class="path-step"><span class="step-number">${i + 1}</span><div><strong>${esc(c?.title || "Missing concept")}</strong><p>${esc(c?.domain)} · ${esc(c?.proficiency.state || "Unknown")}</p>${c?.requires.length ? `<p>Prerequisites: ${c.requires.map((r) => esc(concept(r)?.title || r)).join(", ")}</p>` : ""}</div><div class="actions">${button("Study →", "start", cid, true)}</div></div>`;
                    })
                    .join("") ||
                  '<p class="muted">This goal has no concepts yet. Create a new path with selected concepts.</p>'
                }<p class="privacy">Path completion is your decision. It does not automatically establish proficiency.</p></section>`,
            )
            .join(""))
    );
  },
  review() {
    const reviews = [...state.reviews].sort((a, b) =>
      a.due_at.localeCompare(b.due_at),
    );
    return (
      heading(
        "Remember, then move forward.",
        "Explain an idea before reopening your notes. Review dates use simple intervals, not a predicted memory score.",
      ) +
      `<section class="panel"><h2>Due now</h2>${state.due.length ? state.due.map(reviewRow).join("") : empty("You’re up to date", "Submit an assessment to schedule a review, or revisit any concept in your library.", button("Browse concepts", "nav", "library"))}</section><section class="panel"><h2>Coming up</h2>${
        reviews
          .filter((r) => r.due_at > new Date().toISOString())
          .map(reviewRow)
          .join("") || '<p class="muted">Future reviews will appear here.</p>'
      }</section>`
    );
  },
  graph() {
    const list = available()
      .filter((c) => !domain || c.domain === domain)
      .slice(0, 24);
    const positions = new Map(
      list.map((c, i) => [
        c.id,
        { x: 35 + (i % 3) * 255, y: 35 + Math.floor(i / 3) * 110 },
      ]),
    );
    return (
      heading(
        "An atlas of ideas.",
        "Explore prerequisites and connections. The map shows your notes; evidence shows your understanding.",
      ) +
      `<div class="toolbar"><label class="sr-only" for="domain">Filter map by subject</label><select id="domain" class="filter"><option value="">All subjects</option>${[...new Set(available().map((c) => c.domain))].map((d) => `<option ${domain === d ? "selected" : ""}>${esc(d)}</option>`).join("")}</select>${button("Add a connection", "new-concept")}</div><section class="panel">${
        list.length
          ? `<svg class="graph" viewBox="0 0 805 ${Math.max(220, Math.ceil(list.length / 3) * 110 + 55)}" role="img" aria-label="Concept map. Arrows point from prerequisites to concepts. An equivalent list follows."><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#94b3bd"/></marker></defs>${list
              .flatMap((c) =>
                c.requires
                  .filter((r) => positions.has(r))
                  .map((r) => {
                    const a = positions.get(r),
                      b = positions.get(c.id);
                    return `<line x1="${a.x + 110}" y1="${a.y + 62}" x2="${b.x + 110}" y2="${b.y}" marker-end="url(#arrow)"/>`;
                  }),
              )
              .join("")}${list
              .map((c) => {
                const p = positions.get(c.id);
                return `<g class="node ${c.proficiency.state.includes("Demonstrated") || c.proficiency.state === "Retained" ? "known" : ""}" tabindex="0" role="button" aria-label="Open ${esc(c.title)}" data-action="open-concept" data-id="${esc(c.id)}"><rect x="${p.x}" y="${p.y}" width="220" height="65" rx="11"/><text x="${p.x + 14}" y="${p.y + 26}">${esc(c.title.slice(0, 29))}</text><text class="domain-text" x="${p.x + 14}" y="${p.y + 47}">${esc(c.domain)} · ${esc(c.proficiency.state === "Unknown" ? "Unassessed" : c.proficiency.state)}</text></g>`;
              })
              .join(
                "",
              )}</svg><p class="graph-caption">Arrows point from a prerequisite to the concept that requires it. Green nodes have demonstrated evidence. Showing up to 24 concepts; filter by subject for a smaller map.</p>`
          : empty(
              "Connections grow as you learn",
              "Add concepts and select prerequisites in their note editor.",
              button("Open library", "nav", "library"),
            )
      }</section><section class="panel"><h2>Connections in a list</h2>${list.map((c) => `<div class="row"><div><button class="link-button row-title" data-action="open-concept" data-id="${esc(c.id)}">${esc(c.title)}</button><div><small>${c.requires.length ? "Requires " + c.requires.map((r) => esc(concept(r)?.title || r)).join(", ") : "No accepted prerequisites"}</small></div></div>${badge(c.proficiency)}</div>`).join("")}</section>`
    );
  },
  progress() {
    const attempts = state.sessions
      .flatMap((s) => s.attempts.map((a) => ({ ...a, session_id: s.id })))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
    return (
      heading(
        "What your evidence says.",
        "Inspect actual answers and their conditions. Unknown means unassessed, not incorrect.",
      ) +
      `<section class="panel"><h2>Concept evidence</h2><div class="table-wrap"><table><thead><tr><th>CONCEPT</th><th>OBSERVED STATE</th><th>ATTEMPTS</th><th>DETAIL</th></tr></thead><tbody>${state.concepts.map((c) => `<tr><td>${esc(c.title)}<br><small>${esc(c.domain)}</small></td><td>${badge(c.proficiency)}</td><td>${c.proficiency.attempts}</td><td>${button("Open note", "open-concept", c.id)}</td></tr>`).join("")}</tbody></table></div>${!state.concepts.length ? empty("No evidence yet", "Start a study session and submit an answer.", button("Start studying", "nav", "study")) : ""}</section><section class="panel"><h2>Assessment history</h2>${
        attempts
          .map((a) => {
            const s = state.sessions.find((x) => x.id === a.session_id),
              g = s.assessments.filter((x) => x.attempt_id === a.id).at(-1);
            return `<div class="row"><div><div class="row-title">${esc(concept(a.concept_id)?.title)}</div><small>${fmt(a.created_at)} · ${a.assisted ? "Assisted" : "Independent"} · ${g ? `${esc(g.verdict)} · ${g.provider === "self" ? "Self-assessed" : esc(g.provider)}` : "Awaiting evaluation"}</small><p class="privacy">${esc(a.answer.slice(0, 160))}${a.answer.length > 160 ? "…" : ""}</p></div>${button("Inspect", "resume", s.id)}</div>`;
          })
          .join("") ||
        '<p class="muted">Your submitted answers will appear here. Conversation alone does not generate assessment evidence.</p>'
      }</section>`
    );
  },
  settings() {
    const p = state.settings;
    return (
      heading(
        "Your tools. Your records.",
        "Control optional AI use, study preferences, and a portable backup of your learning.",
      ) +
      `<div class="split"><section class="panel"><h2>Teaching preferences</h2><form id="settings-form"><label class="field">Teaching language<input name="language" value="${esc(p.language)}" required maxlength="100"></label><label class="field">OpenAI model<input name="model" value="${esc(p.model)}" placeholder="Enter a model available to your API account" maxlength="100"><small>Uses the OpenAI Responses API. Your API key stays in the server environment.</small></label><label class="check"><input type="checkbox" name="cloud_enabled" ${p.cloud_enabled ? "checked" : ""}>Enable cloud AI. I allow my selected notes, questions, recent dialogue, and submitted answers to be sent to OpenAI.</label><div class="note ${state.ai_key_available ? "" : "warning"}">${state.ai_key_available ? "An API key is available to this server." : "No API key is configured. Set OPENAI_API_KEY in the terminal before starting the server. Offline practice remains available."}</div><div class="grid"><label class="field">Daily AI request limit<input type="number" name="request_limit" min="1" max="1000" value="${p.request_limit}" required></label><label class="field">Daily review queue cap<input type="number" name="review_cap" min="1" max="100" value="${p.review_cap}" required></label></div><p class="privacy">${state.ai_requests_today} AI requests today. Request limits reset at midnight UTC and include failed calls. They limit requests, not money; set a separate spending limit in your API account.</p><button class="btn primary">Save preferences</button></form></section><div><section class="panel"><h2>Your Obsidian vault</h2><p class="muted">Open this folder as a vault in Obsidian. Markdown edits are picked up when you refresh the app.</p><p class="technical">${esc(state.vault_path)}</p>${button("Refresh vault", "refresh")}<p class="privacy">Notes store knowledge. The database stores your answers, assessments, goals, and review history. Back up both using the export below.</p></section><section class="panel"><h2>Export & restore</h2><p class="muted">Download a complete JSON archive with Markdown notes and structured records. API keys and non-Markdown attachments are excluded.</p>${button("Download backup", "export", "", true)}<hr><label class="field">Restore a backup<input class="file-input" id="restore-file" type="file" accept=".json,application/json"><small>Restore merges records. Conflicting versions are refused. Use an empty data directory for a full recovery.</small></label>${button("Review selected backup", "restore-preview")}<p class="privacy">A snapshot is saved before restoring. Cloud AI is always disabled after restore.</p></section><section class="panel"><h3>About this release</h3><p class="privacy">Local single-learner app · Python & SQLite · Asia/Karachi display dates. Adaptive teaching needs a configured AI model. Voice playback uses your browser’s speech service; code execution and course-platform synchronization are future integrations.</p></section></div></div>`
    );
  },
};
const baseLibrary = pages.library;
pages.library = () =>
  baseLibrary() +
  `<section class="panel"><div class="panel-heading"><div><div class="eyebrow">Start from a question</div><h2>Turn an interest into a lesson</h2></div>${button("Draft a lesson with AI", "new-lesson")}</div><p class="muted">Choose any topic and a starting level. Review the AI draft, add independent references, then save it to your library.</p></section>` +
  resourcePanel();
function resourcePanel() {
  return `<section class="panel"><div class="panel-heading"><div><div class="eyebrow">Beyond your notes</div><h2>Courses, books & tools</h2></div>${button("Add a resource", "new-resource")}</div><p class="privacy">Keep external learning in one place. Progress is recorded by you and stays separate from demonstrated understanding.</p>${(state.resources || []).map((r) => `<div class="row"><div><div class="tag">${esc(r.resource_type)} · ${r.progress}% complete</div><div class="row-title">${esc(r.title)}</div><p class="privacy">${esc(r.notes.slice(0, 180))}</p><div class="source">${sourceLink(r.url)}</div><p class="privacy">${r.concept_ids.map((cid) => `<button class="link-button" data-action="open-concept" data-id="${esc(cid)}">${esc(concept(cid)?.title || cid)}</button>`).join(" · ")}</p></div>${button("Update progress", "edit-resource", r.id)}</div>`).join("") || empty("Bring your courses along", "Add a course, book, video, article, or practice tool. Link it to the concepts you want to learn.")}</section>`;
}
function resourceDialog(r) {
  const v = r || {
    id: "",
    title: "",
    url: "",
    notes: "",
    progress: 0,
    resource_type: "course",
    concept_ids: [],
  };
  dialog(
    r ? "Update your resource" : "Add a learning resource",
    `<form id="resource-form" data-id="${esc(v.id)}"><label class="field">Title<input name="title" value="${esc(v.title)}" required maxlength="200" placeholder="Course, book, or tool name"></label><div class="grid"><label class="field">Type<select name="resource_type">${["course", "book", "video", "article", "tool"].map((t) => `<option ${v.resource_type === t ? "selected" : ""}>${t}</option>`).join("")}</select></label><label class="field">Completion percentage<input name="progress" type="number" min="0" max="100" value="${v.progress}" required></label></div><label class="field">Reference URL<input name="url" type="url" value="${esc(v.url)}" maxlength="2000" placeholder="https://…"></label><label class="field">Progress notes or syllabus<textarea name="notes" maxlength="10000">${esc(v.notes)}</textarea></label><div class="field">Related concepts<div class="path-picker">${
      available()
        .map(
          (c) =>
            `<label class="check"><input type="checkbox" name="links" value="${esc(c.id)}" ${v.concept_ids.includes(c.id) ? "checked" : ""}>${esc(c.title)}</label>`,
        )
        .join("") ||
      '<p class="muted">Add concepts first to link them here.</p>'
    }</div></div><button class="btn primary">Save resource</button></form>`,
  );
}
function lessonDialog() {
  dialog(
    "Draft a lesson",
    `<form id="lesson-form"><label class="field">What do you want to understand?<input name="topic" required maxlength="200" placeholder="e.g. Bayesian reasoning, ancient civilizations, or Python"></label><label class="field">Your starting point<input name="level" required maxlength="200" value="Introductory — explain from first principles"></label><div class="note ${state.settings.cloud_enabled ? "" : "warning"}">${state.settings.cloud_enabled ? "The topic and level will be sent to OpenAI. The draft is unverified until you review it and add independent references." : "Enable cloud AI in Settings to generate a lesson. You can always write or import your own notes."}</div><button class="btn primary">Create a draft</button></form>`,
  );
}
function sourceLink(value) {
  if (!value) return "No reference added yet. Add a source in the note editor.";
  try {
    const url = new URL(value);
    if (["https:", "http:"].includes(url.protocol))
      return `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">Open reference ↗</a>`;
  } catch {}
  return esc(value);
}
function reviewRow(r) {
  const c = concept(r.concept_id);
  return `<div class="row"><div><div class="row-title">${esc(c?.title || "Missing concept")}</div><small>${r.due_at <= new Date().toISOString() ? "Due now" : "Due " + fmt(r.due_at)} · ${[1, 3, 7, 14, 30][r.step]} day interval</small></div>${button("Recall →", "review-start", r.concept_id, true)}</div>`;
}
function questionButtons(s) {
  return `<div class="actions">${["theory", "short", "quiz", "walkthrough"].map((type) => `<button class="btn ${type === "theory" ? "primary" : ""}" data-action="question" data-id="${type}">${{ theory: "Theory answer", short: "Short answer", quiz: "Multiple choice", walkthrough: "Walkthrough" }[type]}</button>`).join("")}</div><p class="privacy">${state.settings.cloud_enabled ? "AI creates a fresh question from this note and freezes its rubric." : "Offline prompts use transparent templates. Multiple-choice generation requires cloud AI."}</p>`;
}
function questionPanel(s, q, a, g) {
  const localKey = "draft:" + q.id;
  let draft = localStorage.getItem(localKey) ?? s.draft ?? "";
  if (a) draft = a.answer;
  return `<section class="panel question"><div class="tag">${esc(q.type)} · ${q.provider === "offline" ? "Offline practice" : "AI generated"} · Frozen rubric</div><p class="question-prompt">${esc(q.prompt)}</p><details class="details"><summary>What this question checks</summary><ul class="criteria">${q.criteria.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>${s.shown_hint ? `<div class="hint">Hint: ${esc(s.shown_hint)}</div>` : ""}${
    !g
      ? `<form id="answer-form" data-question="${esc(q.id)}">${q.choices.length ? `<fieldset><legend class="sr-only">Choose an answer</legend>${q.choices.map((choice, i) => `<label class="choice"><input type="radio" name="choice" value="${esc(choice)}" ${draft === choice ? "checked" : ""} required> ${esc(choice)}</label>`).join("")}</fieldset>` : `<label class="field">Your answer<textarea id="answer" name="answer" maxlength="20000" required placeholder="Explain your reasoning. It’s fine to say what you are unsure about.">${esc(draft)}</textarea><small id="draft-status">${a ? "Your answer is saved. Retry evaluation below." : "Draft saves automatically on this computer."}</small></label>`}<label class="check"><input type="checkbox" name="assisted" ${s.hint_used || a?.assisted ? "checked" : ""}>I used notes, hints, or other help for this answer.</label><div class="actions"><button class="btn primary">${a ? "Retry evaluation" : "Save answer & get feedback"}</button>${button("Show a hint", "hint")}${button("I don’t know yet", "dont-know")}</div></form>`
      : `<div class="feedback"><div class="row"><div class="verdict">${esc(g.verdict)}</div><span class="badge unknown">${g.provider === "self" ? "Self-assessed" : g.provider === "offline" ? "Needs your judgment" : "AI assessment"} · ${a.assisted ? "Assisted" : "Independent"}</span></div><details class="details"><summary>Your submitted answer</summary><div class="prose">${prose(a.answer)}</div></details><div class="prose">${prose(g.explanation)}</div>${g.correct.length ? `<h3>What you got right</h3><ul>${g.correct.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}${g.missing.length ? `<h3>What needs another look</h3><ul>${g.missing.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}${g.quotes.map((x) => `<blockquote>${esc(x)}</blockquote>`).join("")}<div class="note">Next: ${esc(g.next_action)}</div><details class="details"><summary>Compare with the reference</summary><div class="prose">${prose(g.reference)}</div></details><div class="actions">${button("Record your judgment", "revise", a.id)}${button("Question this grade", "dispute", a.id)}</div><details class="details"><summary>Earlier assessment revisions</summary>${
          s.assessments
            .filter((x) => x.attempt_id === a.id && x.id !== g.id)
            .map(
              (x) =>
                `<div class="note"><strong>Revision ${x.version}: ${esc(x.verdict)} · ${esc(x.provider)}</strong><p>${esc(x.explanation)}</p></div>`,
            )
            .join("") || '<p class="privacy">No earlier revisions.</p>'
        }</details><p class="privacy">Assessment revision ${g.version}. All earlier judgments are kept. ${g.status === "disputed" ? "This judgment is disputed and does not establish proficiency." : ""}</p><hr><h3>Try another question</h3>${questionButtons(s)}</div>`
  }</section>`;
}
function dialog(title, body) {
  $("#dialog-content").innerHTML =
    `<div class="dialog-head"><h2>${title}</h2><button type="button" data-action="close-dialog" aria-label="Close dialog">×</button></div>${body}<div id="dialog-error" class="dialog-error" role="alert"></div>`;
  $("#editor").showModal();
}
function closeDialog() {
  if ($("#editor").open) $("#editor").close();
}
function editor(c) {
  const defaults = c || {
    id: "",
    title: "",
    domain: "",
    body: "",
    source: "",
    requires: [],
    hash: "",
  };
  dialog(
    c ? "Edit your concept" : "Add a concept",
    `<form id="concept-form" data-id="${esc(defaults.id)}" data-hash="${esc(defaults.hash)}"><div class="grid"><label class="field">Concept title<input name="title" value="${esc(defaults.title)}" required maxlength="160" placeholder="e.g. Conditional probability"></label><label class="field">Subject<input name="domain" value="${esc(defaults.domain)}" required maxlength="80" placeholder="e.g. Mathematics" list="subjects"><datalist id="subjects">${[...new Set(state.concepts.map((c) => c.domain))].map((d) => `<option>${esc(d)}</option>`).join("")}</datalist></label></div><label class="field">Your explanation or source excerpt<textarea name="body" class="code" maxlength="100000" required placeholder="Paste permitted study material, write your own explanation, or add a worked example…">${esc(defaults.body)}</textarea></label><label class="field">Reference URL or source description<input name="source" value="${esc(defaults.source)}" maxlength="2000" placeholder="Where did this explanation come from?"></label>${
      available().filter((x) => x.id !== defaults.id).length
        ? `<div class="field">Prerequisites <small>Select concepts needed before this one. Cycles are checked when saving.</small><div class="path-picker">${available()
            .filter((x) => x.id !== defaults.id)
            .map(
              (x) =>
                `<label class="check"><input name="requires" type="checkbox" value="${esc(x.id)}" ${defaults.requires.includes(x.id) ? "checked" : ""}>${esc(x.title)}</label>`,
            )
            .join("")}</div></div>`
        : ""
    }<div class="actions"><button class="btn primary">Save concept</button>${button("Cancel", "close-dialog")}</div></form>`,
  );
}
async function openConcept(cid) {
  const c = concept(cid);
  if (!c) return toast("Concept no longer exists. Refresh the library.");
  const s = session();
  if (
    view === "study" &&
    s?.question &&
    !s.hint_used &&
    !s.attempts.some(
      (a) => a.question_id === s.question.id && a.status === "assessed",
    )
  ) {
    try {
      await api("hint", { session_id: s.id });
      await reload();
      toast(
        "Viewing notes during an assessment marks the attempt as assisted.",
      );
    } catch (e) {
      return toast(e.message);
    }
  }
  dialog(
    esc(c.title),
    `<div class="tag">${esc(c.domain)} · ${esc(c.origin || "learner")}</div>${badge(c.proficiency)}<div class="prose details">${prose(c.body)}</div><div class="source">${sourceLink(c.source)}</div>${c.requires.length ? `<p class="privacy">Requires: ${c.requires.map((x) => esc(concept(x)?.title || x)).join(", ")}</p>` : ""}<p class="technical">${esc(c.path)}</p><div class="actions">${button("Start studying →", "start", c.id, true)}${button("Edit note", "edit-concept", c.id)}${button("Discover what I know", "diagnostic-start", c.id)}</div>`,
  );
}
function goalDialog() {
  dialog(
    "Create a learning path",
    `<form id="goal-form"><label class="field">What would you like to be able to do?<input name="title" required maxlength="200" placeholder="Explain and apply the fundamentals of…"></label><label class="field">Time budget<input name="budget" value="25 minutes a day" required maxlength="100"></label><div class="field">Choose concepts in learning order<small>Selection order sets the path. Use prerequisites to guide your choices.</small><div class="path-picker">${
      available()
        .map(
          (c) =>
            `<label class="check"><input type="checkbox" name="concept_ids" value="${esc(c.id)}">${esc(c.title)} <small>${esc(c.domain)}</small></label>`,
        )
        .join("") || "<p>Add concepts in your library first.</p>"
    }</div></div><p id="selected-order" class="privacy"></p><div class="actions"><button class="btn primary">Save learning path</button>${button("Cancel", "close-dialog")}</div></form>`,
  );
  $("#goal-form").selectionOrder = [];
}
async function start(cid, mode = "learn") {
  await run(async () => {
    const result = await api("start", { concept_id: cid, mode });
    activeSession = result.id;
    view = "study";
    location.hash = "study";
    closeDialog();
    if (["review", "diagnostic", "walkthrough"].includes(mode))
      await api("question", {
        session_id: activeSession,
        type: mode === "walkthrough" ? "walkthrough" : "theory",
      });
  });
}
const actions = {
  nav: (v) => navigate(v),
  "new-concept": () => editor(),
  "open-concept": openConcept,
  "edit-concept": (cid) => editor(concept(cid)),
  "close-dialog": closeDialog,
  examples: () =>
    run(
      () => api("examples", {}),
      "Example library loaded. These notes do not imply any previous learning.",
    ),
  start: (cid) => start(cid),
  "diagnostic-start": (cid) => start(cid, "diagnostic"),
  "review-start": (cid) => start(cid, "review"),
  resume: (sid) => {
    activeSession = sid;
    navigate("study");
  },
  "new-goal": goalDialog,
  "new-resource": () => resourceDialog(),
  "edit-resource": (rid) =>
    resourceDialog(state.resources.find((r) => r.id === rid)),
  "new-lesson": lessonDialog,
  "pause-goal": (gid) =>
    run(() => api("goal-status", { id: gid, status: "paused" }), "Goal paused"),
  "activate-goal": (gid) =>
    run(
      () => api("goal-status", { id: gid, status: "active" }),
      "Goal activated",
    ),
  "complete-goal": (gid) =>
    run(
      () => api("goal-status", { id: gid, status: "complete" }),
      "Goal marked complete; proficiency is unchanged.",
    ),
  question: (type) =>
    run(
      () => api("question", { session_id: activeSession, type }),
      "Question ready",
    ),
  hint: () =>
    run(
      () => api("hint", { session_id: activeSession }),
      "Hint shown. This attempt is marked as assisted.",
    ),
  "show-source": async (cid) => {
    if (session()?.question)
      await run(() => api("hint", { session_id: activeSession }));
    openConcept(cid);
  },
  "dont-know": () => {
    const input = $("#answer");
    if (input) {
      input.value = "I don’t know yet.";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
    } else
      toast(
        "Choose the option you think fits, or use a hint before answering.",
      );
  },
  finish: (sid) =>
    run(
      () => api("finish", { session_id: sid }),
      "Session saved and marked complete",
    ),
  refresh: () => run(async () => {}, "Vault refreshed"),
  revise: (aid) => gradeDialog(aid, false),
  dispute: (aid) => gradeDialog(aid, true),
  export: async () => {
    try {
      const r = await fetch("/api/export", {
        headers: { "X-App-Token": state.csrf_token },
      });
      if (!r.ok) throw new Error("Export failed. Refresh and retry.");
      const blob = await r.blob(),
        url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download =
        "learning-backup-" + new Date().toISOString().slice(0, 10) + ".json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast("Backup downloaded");
    } catch (e) {
      toast(e.message);
    }
  },
  "restore-preview": async () => {
    const file = $("#restore-file").files[0];
    if (!file) return toast("Choose a backup file first.");
    if (file.size > 12 * 1024 * 1024)
      return toast("Backup exceeds the 12 MB restore limit.");
    try {
      const archive = JSON.parse(await file.text());
      if (archive.schema_version !== 1 || !archive.records || !archive.notes)
        throw new Error("Unsupported backup format.");
      const count = Object.values(archive.records).reduce(
        (n, r) => n + (Array.isArray(r) ? r.length : 0),
        0,
      );
      dialog(
        "Review your backup",
        `<p>This archive contains <strong>${count} records</strong> and <strong>${Object.keys(archive.notes).length} Markdown notes</strong>.</p><p class="muted">Existing records are kept. Conflicting versions are refused. A snapshot is saved before merging. Cloud AI will be disabled.</p><div class="actions">${button("Restore these records", "confirm-restore", "", true)}${button("Cancel", "close-dialog")}</div>`,
      );
      $("#editor").archive = archive;
    } catch (e) {
      toast(e.message);
    }
  },
  "confirm-restore": () =>
    run(async () => {
      await api("restore", $("#editor").archive);
      closeDialog();
    }, "Backup restored"),
  "import-note": () =>
    dialog(
      "Import Markdown",
      `<form id="import-form"><label class="field">Markdown file<input name="file" type="file" accept=".md,text/markdown,text/plain" required></label><label class="field">Subject<input name="domain" value="Unsorted" required maxlength="80"></label><p class="privacy">Imports the text as a concept. Original frontmatter stays in the note body for inspection. Add source details and prerequisites after import.</p><button class="btn primary">Import note</button></form>`,
    ),
  speak: () => {
    if (!("speechSynthesis" in window))
      return toast("This browser does not support read aloud.");
    speechSynthesis.cancel();
    const last = session()
      ?.messages.filter((m) => m.role === "tutor")
      .at(-1);
    if (last) speechSynthesis.speak(new SpeechSynthesisUtterance(last.text));
    toast("Reading aloud using your browser’s speech service.");
  },
};
function gradeDialog(aid, dispute) {
  dialog(
    dispute ? "Question this assessment" : "Record your judgment",
    `<form id="grade-form" data-attempt="${esc(aid)}"><label class="field">Judgment<select name="verdict">${(dispute ? ["disputed"] : ["correct", "partial", "incorrect", "uncertain"]).map((v) => `<option value="${v}">${v === "disputed" ? "Disputed — exclude from proficiency" : v[0].toUpperCase() + v.slice(1)}</option>`).join("")}</select></label><label class="field">Why?<textarea name="explanation" required maxlength="3000" placeholder="Compare the answer with the criteria and explain your judgment."></textarea></label><p class="privacy">This creates a labeled self-assessment revision. The original grade and answer remain in your history.</p><button class="btn primary">Save judgment</button></form>`,
  );
}
document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-action]");
  if (!target || busy) return;
  const fn = actions[target.dataset.action];
  if (fn) fn(target.dataset.id);
});
document.addEventListener("keydown", (e) => {
  if (
    (e.key === "Enter" || e.key === " ") &&
    e.target.matches("g[data-action]")
  ) {
    e.preventDefault();
    actions[e.target.dataset.action]?.(e.target.dataset.id);
  }
});
document.addEventListener("input", (e) => {
  if (e.target.id === "search") {
    filter = e.target.value;
    const list = available().filter(
      (c) =>
        (!domain || c.domain === domain) &&
        `${c.title} ${c.body} ${c.domain}`
          .toLowerCase()
          .includes(filter.toLowerCase()),
    );
    $("#library-results").innerHTML =
      list.map(card).join("") ||
      '<p class="muted">No matching concepts. Try a broader term.</p>';
  }
  if (e.target.id === "answer") {
    const q = session()?.question;
    if (!q) return;
    const value = e.target.value;
    localStorage.setItem("draft:" + q.id, value);
    draftKeys.add(q.id);
    clearTimeout(saveTimer);
    const sid = activeSession;
    saveTimer = setTimeout(async () => {
      try {
        await api("draft", { session_id: sid, draft: value });
        if ($("#draft-status"))
          $("#draft-status").textContent = "Draft saved locally.";
      } catch {
        if ($("#draft-status"))
          $("#draft-status").textContent =
            "Server unavailable. Draft is kept in this browser; retry when connected.";
      }
    }, 500);
  }
});
document.addEventListener("change", (e) => {
  if (e.target.id === "domain") {
    domain = e.target.value;
    render();
  }
  if (e.target.id === "session-switch") {
    activeSession = e.target.value;
    render();
  }
  if (e.target.name === "concept_ids") {
    const form = $("#goal-form");
    const val = e.target.value;
    form.selectionOrder = form.selectionOrder.filter((x) => x !== val);
    if (e.target.checked) form.selectionOrder.push(val);
    $("#selected-order").textContent =
      "Path: " +
      form.selectionOrder.map((cid) => concept(cid)?.title).join(" → ");
  }
});
document.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (busy) return;
  const form = e.target,
    values = new FormData(form);
  async function saveDialog(path, data, message) {
    const submit = form.querySelector(
      'button[type="submit"],button.btn.primary',
    );
    if (submit) submit.disabled = true;
    try {
      await api(path, data);
      closeDialog();
      await reload();
      render();
      toast(message);
    } catch (err) {
      $("#dialog-error").textContent = err.message;
    } finally {
      if (submit) submit.disabled = false;
    }
  }
  if (form.id === "concept-form")
    await saveDialog(
      "concept",
      {
        id: form.dataset.id || undefined,
        hash: form.dataset.hash || undefined,
        title: values.get("title"),
        domain: values.get("domain"),
        body: values.get("body"),
        source: values.get("source"),
        requires: values.getAll("requires"),
      },
      "Concept saved",
    );
  if (form.id === "goal-form")
    await saveDialog(
      "goal",
      {
        title: values.get("title"),
        budget: values.get("budget"),
        concept_ids: form.selectionOrder,
      },
      "Learning path saved",
    );
  if (form.id === "resource-form")
    await saveDialog(
      "resource",
      {
        id: form.dataset.id || undefined,
        title: values.get("title"),
        url: values.get("url"),
        notes: values.get("notes"),
        progress: Number(values.get("progress")),
        resource_type: values.get("resource_type"),
        concept_ids: values.getAll("links"),
      },
      "Resource saved",
    );
  if (form.id === "lesson-form") {
    const submit = form.querySelector("button");
    submit.disabled = true;
    submit.textContent = "Drafting your lesson…";
    try {
      const draft = await api("lesson", {
        topic: values.get("topic"),
        level: values.get("level"),
      });
      closeDialog();
      editor(draft);
      toast("Review the draft and add references before saving.");
    } catch (err) {
      $("#dialog-error").textContent = err.message;
    } finally {
      submit.disabled = false;
      submit.textContent = "Create a draft";
    }
  }
  if (form.id === "grade-form")
    await saveDialog(
      "revise",
      {
        attempt_id: form.dataset.attempt,
        verdict: values.get("verdict"),
        explanation: values.get("explanation"),
      },
      "Assessment revision saved",
    );
  if (form.id === "import-form") {
    const file = values.get("file");
    if (file.size > 100000)
      return ($("#dialog-error").textContent =
        "Use a Markdown file smaller than 100 KB.");
    await saveDialog(
      "concept",
      {
        title: file.name.replace(/\.md$/i, ""),
        domain: values.get("domain"),
        body: await file.text(),
        source: "Imported Markdown: " + file.name,
        requires: [],
      },
      "Markdown imported",
    );
  }
  if (form.id === "settings-form")
    await run(
      () =>
        api("settings", {
          language: values.get("language"),
          model: values.get("model"),
          cloud_enabled: values.has("cloud_enabled"),
          request_limit: Number(values.get("request_limit")),
          review_cap: Number(values.get("review_cap")),
        }),
      "Preferences saved",
    );
  if (form.id === "chat-form") {
    const message = values.get("message");
    const key = "message:" + activeSession + ":" + message;
    let rid = localStorage.getItem(key);
    if (!rid) {
      rid = id();
      localStorage.setItem(key, rid);
    }
    await run(async () => {
      await api("ask", { session_id: activeSession, message, request_id: rid });
      localStorage.removeItem(key);
    });
  }
  if (form.id === "answer-form") {
    clearTimeout(saveTimer);
    const q = session().question;
    const answer = values.get("answer") || values.get("choice");
    const existing = session().attempts.find(
      (a) => a.question_id === q.id && a.status === "pending",
    );
    const key = "submission:" + q.id;
    let rid = existing?.request_id || localStorage.getItem(key);
    if (!rid) {
      rid = id();
      localStorage.setItem(key, rid);
    }
    await run(async () => {
      await api("submit", {
        session_id: activeSession,
        question_id: q.id,
        answer,
        assisted: values.has("assisted"),
        request_id: rid,
      });
      localStorage.removeItem("draft:" + q.id);
      localStorage.removeItem(key);
    }, "Answer and feedback saved");
  }
});
window.addEventListener("hashchange", () => {
  const next = location.hash.slice(1) || "today";
  if (next !== view) {
    view = next;
    render();
  }
});
window.addEventListener("beforeunload", () => {
  window.speechSynthesis?.cancel?.();
});
try {
  await reload();
  render();
} catch (e) {
  $("#app").innerHTML =
    `<main><h1>Could not open your learning workspace.</h1><p>${esc(e.message)}</p><p>Start the local server with <code>python server.py</code>, then reload this page.</p></main>`;
}
