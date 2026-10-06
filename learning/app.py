"""Learning workflows; AI proposes, application policy records evidence."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .providers import OpenAIProvider, ProviderError
from .store import Store, digest, now, uid

KINDS = ("concept", "resource", "goal", "session", "question", "attempt", "assessment", "review", "run")
DEFAULT_SETTINGS = {"cloud_enabled": False, "model": "", "language": "English",
                    "request_limit": 30, "review_cap": 10, "timezone": "Asia/Karachi"}


def text(value, maximum=10000, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f"Expected text between {1 if required else 0} and {maximum} characters.")
    return value.strip() if required else value


class LearningApp:
    def __init__(self, root):
        self.store = Store(root)

    def need(self, kind, record_id):
        result = self.store.get(kind, record_id)
        if result is None:
            raise ValueError("This record no longer exists. Refresh the app.")
        return result

    def settings(self):
        return DEFAULT_SETTINGS | self.store.setting("preferences", {})

    def cloud(self, role, context):
        settings = self.settings()
        if not settings["cloud_enabled"]:
            raise ProviderError("Cloud AI is disabled.")
        today = now()[:10]
        count = sum(1 for r in self.store.all("run") if r["created_at"].startswith(today))
        if count >= settings["request_limit"]:
            raise ProviderError("Daily AI request limit reached. Switch to offline practice or adjust Settings.")
        record = {"id": uid(), "created_at": now(), "role": role, "model": settings["model"],
                  "prompt_version": 1, "status": "pending", "source_ids": context.get("source_ids", [])}
        self.store.put("run", record)
        self.store.commit()  # Reserve the bounded request before network I/O, including failed calls.
        try:
            result, usage = OpenAIProvider(settings["model"]).run(role, context | {"language": settings["language"]})
            record.update(status="completed", usage=usage)
            return result
        except ProviderError:
            record["status"] = "failed"
            raise
        finally:
            self.store.put("run", record)
            self.store.commit()

    def proficiency(self, concept_id):
        sessions = [s for s in self.store.all("session") if s["concept_id"] == concept_id]
        attempts = [a for a in self.store.all("attempt") if a["concept_id"] == concept_id]
        latest = {}
        for a in self.store.all("assessment"):
            latest[a["attempt_id"]] = a
        independent = []
        assisted = False
        for attempt in attempts:
            assessment = latest.get(attempt["id"])
            if not assessment or assessment.get("status") == "disputed" or assessment["verdict"] != "correct":
                continue
            if attempt["assisted"]:
                assisted = True
            else:
                independent.append(attempt)
        state = "Unknown"
        if sessions:
            state = "Encountered"
        if assisted:
            state = "Demonstrated with help"
        if independent:
            state = "Demonstrated independently"
        # Retention requires delayed independent success on different question prompts.
        for first in independent:
            for later in independent:
                q1 = self.need("question", first["question_id"])
                q2 = self.need("question", later["question_id"])
                delay = datetime.fromisoformat(later["created_at"]) - datetime.fromisoformat(first["created_at"])
                if delay >= timedelta(days=1) and q1["prompt"] != q2["prompt"]:
                    state = "Retained"
        return {"state": state, "attempts": len(attempts), "evidence_ids": [a["id"] for a in independent]}

    def public_question(self, q):
        return {k: v for k, v in q.items() if k not in ("reference", "correct_choice", "hint", "source_snapshot")}

    def public_session(self, session):
        session = dict(session)
        question = self.store.get("question", session.get("question_id", ""))
        session["question"] = self.public_question(question) if question else None
        session["attempts"] = [a for a in self.store.all("attempt") if a["session_id"] == session["id"]]
        session["assessments"] = [a for a in self.store.all("assessment")
                                  if a["attempt_id"] in {x["id"] for x in session["attempts"]}]
        if question and session.get("hint_used"):
            session["shown_hint"] = question["hint"]
        return session

    def state(self):
        warnings = self.store.sync()
        concepts = [dict(c, proficiency=self.proficiency(c["id"])) for c in self.store.all("concept")]
        reviews = self.store.all("review")
        due = [r for r in reviews if r["due_at"] <= now() and r["status"] == "due"]
        return {"concepts": concepts, "resources": self.store.all("resource"), "goals": self.store.all("goal"),
                "sessions": [self.public_session(s) for s in self.store.all("session")],
                "reviews": reviews, "due": due[:self.settings()["review_cap"]],
                "settings": self.settings(), "warnings": warnings,
                "ai_key_available": bool(os.environ.get("OPENAI_API_KEY")),
                "vault_path": str(self.store.vault),
                "ai_requests_today": sum(r["created_at"].startswith(now()[:10]) for r in self.store.all("run"))}

    def save_session(self, s):
        s["updated_at"] = now()
        self.store.put("session", s)
        concept = self.need("concept", s["concept_id"])
        lines = [f"# {concept['title']} — study session", "", f"Session ID: {s['id']}",
                 f"Started: {s['created_at']}", "", f"[[{concept['path'][:-3]}|{concept['title']}]]", ""]
        for m in s["messages"]:
            lines.extend(["## " + m["role"].capitalize(), "", m["text"], ""])
        for attempt in self.store.all("attempt"):
            if attempt["session_id"] == s["id"]:
                q = self.need("question", attempt["question_id"])
                lines.extend(["## Assessment", "", q["prompt"], "", attempt["answer"], "",
                              "Assisted: " + str(attempt["assisted"]), ""])
                for grade in self.store.all("assessment"):
                    if grade["attempt_id"] == attempt["id"]:
                        lines.extend([f"### {grade['verdict']} ({grade['provider']})", "", grade["explanation"],
                                      "", grade["next_action"], ""])
        self.store.queue_note("Sessions/" + s["id"] + ".md", "\n".join(lines))
        self.store.commit()

    def validate_links(self, record_id, links):
        if not isinstance(links, list) or len(links) > 30 or any(not isinstance(i, str) for i in links):
            raise ValueError("Invalid prerequisites.")
        adjacency = {c["id"]: c.get("requires", []) for c in self.store.all("concept")}
        adjacency[record_id] = links
        for link in links:
            self.need("concept", link)
        def visit(node, trail):
            if node in trail:
                raise ValueError("This prerequisite would create a cycle.")
            for parent in adjacency.get(node, []):
                visit(parent, trail | {node})
        visit(record_id, set())

    def create_concept(self, data):
        record_id = data.get("id") or uid()
        existing = self.store.get("concept", record_id)
        if data.get("id") and not existing:
            raise ValueError("Concept not found.")
        self.validate_links(record_id, data.get("requires", []))
        c = dict(existing or {"id": record_id, "created_at": now(), "origin": "learner"})
        c.update(title=text(data.get("title"), 160), domain=text(data.get("domain"), 80),
                 body=text(data.get("body"), 100000), source=text(data.get("source", ""), 2000, False),
                 requires=data.get("requires", []), missing=False)
        self.store.save_concept(c, data.get("hash"))
        self.store.commit()
        return c

    def start(self, data):
        c = self.need("concept", data.get("concept_id"))
        if c.get("missing"):
            raise ValueError("This note is missing. Restore it before starting a session.")
        mode = data.get("mode", "learn")
        if mode not in ("learn", "diagnostic", "review", "walkthrough"):
            raise ValueError("Invalid study mode.")
        s = {"id": uid(), "concept_id": c["id"], "goal_id": data.get("goal_id"), "mode": mode,
             "created_at": now(), "updated_at": now(), "status": "active", "draft": "",
             "hint_used": False, "question_id": None, "messages": []}
        greeting = ("Start with what you remember. Close your notes before answering; a hint will mark the attempt as assisted."
                    if mode in ("review", "diagnostic") else
                    "Read the explanation, then try explaining it in your own words. Ask the AI tutor for another example when cloud AI is enabled.")
        s["messages"].append({"id": uid(), "role": "tutor", "text": greeting, "source_ids": [c["id"]]})
        self.save_session(s)
        return self.public_session(s)

    def ask(self, data):
        s = self.need("session", data.get("session_id"))
        message = text(data.get("message"), 6000)
        request_id = text(data.get("request_id"), 100)
        existing = next((m for m in s["messages"] if m.get("request_id") == request_id), None)
        if existing:
            if existing["text"] != message:
                raise ValueError("Request ID already belongs to a different message.")
            if any(m.get("reply_to") == request_id for m in s["messages"]):
                return self.public_session(s)
        else:
            s["messages"].append({"id": uid(), "request_id": request_id, "role": "you", "text": message})
            self.save_session(s)
        c = self.need("concept", s["concept_id"])
        hits = self.store.search(message)
        sources = [c] + [h for h in hits if h and h["id"] != c["id"]][:3]
        if self.settings()["cloud_enabled"]:
            reply = self.cloud("teach", {"message": message, "history": s["messages"][-10:],
                                        "source_ids": [x["id"] for x in sources],
                                        "sources": [{"id": x["id"], "title": x["title"], "text": x["body"][:10000]} for x in sources],
                                        "assessment_active": bool(s.get("question_id"))})
            if any(i not in {x["id"] for x in sources} for i in reply["source_ids"]):
                raise ProviderError("AI returned an invalid citation. The message is saved; retry.")
            body, citations = reply["reply"], reply["source_ids"]
        else:
            body = ("Offline practice uses your notes; it does not generate an AI conversation.\n\n"
                    + c["body"][:5000] + "\n\nTry this: explain the main idea without looking, give your own example, and check it against this source. Enable cloud AI in Settings for adaptive explanations.")
            citations = [c["id"]]
        if s.get("question_id"):
            s["hint_used"] = True  # Tutor assistance during assessment cannot count as independent.
        s["messages"].append({"id": uid(), "reply_to": request_id, "role": "tutor", "text": body,
                              "source_ids": citations})
        self.save_session(s)
        return self.public_session(s)

    def make_question(self, data):
        s = self.need("session", data.get("session_id"))
        if s.get("question_id") and not any(a["question_id"] == s["question_id"] for a in self.store.all("attempt")):
            return self.public_session(s)
        c = self.need("concept", s["concept_id"])
        kind = data.get("type", "theory")
        if kind not in ("theory", "short", "quiz", "walkthrough"):
            raise ValueError("Invalid question type.")
        prior = [q["prompt"] for q in self.store.all("question") if q["concept_id"] == c["id"]][-8:]
        if self.settings()["cloud_enabled"]:
            q = self.cloud("question", {"type": kind, "title": c["title"], "source": c["body"][:15000],
                                        "source_ids": [c["id"]], "previous_questions": prior})
            if not q["prompt"].strip() or not q["criteria"] or not q["reference"].strip():
                raise ProviderError("AI returned an incomplete question. Please retry.")
            if kind == "quiz" and (len(q["choices"]) != 4 or len(set(q["choices"])) != 4 or not 0 <= q["correct_choice"] < 4):
                raise ProviderError("AI returned invalid quiz choices. Please retry.")
            provider = "openai"
        else:
            if kind == "quiz":
                raise ValueError("Adaptive multiple-choice quizzes need cloud AI. Use short answer or theory in offline practice.")
            variants = {
                "theory": [f"Explain {c['title']} in your own words. Include a concrete example and a common mistake.",
                           f"Apply {c['title']} to a new example. Explain your reasoning and the conditions where it works."],
                "short": [f"What is the central idea of {c['title']}? Explain it in two or three sentences.",
                          f"Give a new example of {c['title']} and explain why it fits."],
                "walkthrough": [f"Choose a small task involving {c['title']}. Describe your first step, carry it out, and explain how you checked it.",
                                f"Create a worked example of {c['title']}. Explain each step and identify a possible error."]}
            q = {"prompt": variants[kind][len(prior) % 2], "reference": c["body"],
                 "criteria": ["The central idea is explained accurately.", "A concrete example supports the explanation.",
                              "Conditions or limitations are identified."],
                 "hint": "Start with the main idea. Give a small example, then say why it works.",
                 "choices": [], "correct_choice": -1}
            provider = "offline"
        q.update(id=uid(), concept_id=c["id"], session_id=s["id"], type=kind, created_at=now(),
                 provider=provider, source_snapshot=c["body"], source_ids=[c["id"]], rubric_version=1)
        self.store.put("question", q)
        s.update(question_id=q["id"], draft="", hint_used=False, status="active")
        self.save_session(s)
        return self.public_session(s)

    def submit(self, data):
        s = self.need("session", data.get("session_id"))
        q = self.need("question", data.get("question_id"))
        if q["session_id"] != s["id"]:
            raise ValueError("Question belongs to a different session.")
        answer = text(data.get("answer"), 20000, False)
        if not answer.strip():
            raise ValueError("Write an answer before submitting.")
        request_id = text(data.get("request_id"), 100)
        attempt = next((a for a in self.store.all("attempt") if a["request_id"] == request_id), None)
        if attempt and (attempt["answer"] != answer or attempt["question_id"] != q["id"]):
            raise ValueError("Request ID already belongs to a different answer.")
        if not attempt:
            if s.get("question_id") != q["id"]:
                raise ValueError("This question is no longer active.")
            if q["type"] == "quiz" and answer not in q["choices"]:
                raise ValueError("Choose one of the available quiz answers.")
            attempt = {"id": uid(), "request_id": request_id, "session_id": s["id"], "concept_id": q["concept_id"],
                       "question_id": q["id"], "answer": answer, "assisted": bool(s["hint_used"] or data.get("assisted")),
                       "created_at": now(), "status": "pending"}
            self.store.put("attempt", attempt)
            self.store.commit()  # An answer is durable even if the evaluator fails.
        elif attempt["status"] == "assessed":
            return self.public_session(s)
        if self.settings()["cloud_enabled"]:
            feedback = self.cloud("evaluate", {"question": q["prompt"], "criteria": q["criteria"],
                                               "reference": q["reference"], "source": q["source_snapshot"][:15000],
                                               "answer": answer, "source_ids": q["source_ids"]})
            if any(not quote or quote not in answer for quote in feedback["quotes"]):
                raise ProviderError("AI feedback contained a quote that is not in your answer. Your answer is saved; retry evaluation.")
            provider = "openai"
        else:
            feedback = {"correct": [], "missing": [], "quotes": [], "verdict": "uncertain",
                        "explanation": "Your answer is saved. Offline practice cannot judge the meaning of a theory answer. Compare it with the frozen criteria and source, then record your own honest judgment below.",
                        "next_action": "Check the criteria and source; revise your explanation or mark your self-assessment."}
            provider = "offline"
        assessment = feedback | {"id": uid(), "attempt_id": attempt["id"], "created_at": now(), "provider": provider,
                                 "status": "accepted", "rubric": q["criteria"], "reference": q["reference"], "version": 1}
        self.store.put("assessment", assessment)
        attempt["status"] = "assessed"
        self.store.put("attempt", attempt)
        self.schedule(attempt, assessment)
        s["draft"] = ""
        self.save_session(s)
        return self.public_session(s)

    def schedule(self, attempt, assessment):
        concept_id = attempt["concept_id"]
        prior = next((r for r in self.store.all("review") if r["concept_id"] == concept_id), None)
        intervals = [1, 3, 7, 14, 30]
        independent_success = assessment["verdict"] == "correct" and not attempt["assisted"]
        # Only advance when actually doing a due review; repeated same-day successes do not inflate intervals.
        step = prior.get("step", 0) if prior else 0
        if not independent_success:
            step = 0
        elif prior and prior["due_at"] <= now():
            step = min(step + 1, len(intervals) - 1)
        r = {"id": prior["id"] if prior else uid(), "concept_id": concept_id, "status": "due", "step": step,
             "due_at": (datetime.now(timezone.utc) + timedelta(days=intervals[step])).isoformat(),
             "attempt_id": attempt["id"], "policy_version": 1}
        self.store.put("review", r)

    def revise_grade(self, data):
        attempt = self.need("attempt", data.get("attempt_id"))
        grades = [g for g in self.store.all("assessment") if g["attempt_id"] == attempt["id"]]
        if not grades:
            raise ValueError("Wait for an assessment before revising it.")
        old = grades[-1]
        verdict = data.get("verdict")
        if verdict not in ("correct", "partial", "incorrect", "uncertain", "disputed"):
            raise ValueError("Invalid assessment judgment.")
        explanation = text(data.get("explanation"), 3000)
        grade = dict(old, id=uid(), created_at=now(), provider="self", explanation=explanation,
                     verdict="uncertain" if verdict == "disputed" else verdict,
                     status="disputed" if verdict == "disputed" else "accepted", supersedes=old["id"],
                     version=old["version"] + 1, quotes=[], correct=[], missing=[],
                     next_action="Try a varied question later without help to check retention.")
        self.store.put("assessment", grade)
        self.schedule(attempt, grade)
        self.save_session(self.need("session", attempt["session_id"]))
        return {"saved": True}

    def export(self):
        self.store.flush()
        self.store.sync()
        notes = {}
        for p in self.store.vault.rglob("*.md"):
            relative = p.relative_to(self.store.vault).as_posix()
            self.store.safe_path(relative)
            notes[relative] = p.read_text(encoding="utf-8")
        return {"schema_version": 1, "exported_at": now(), "settings": self.settings(),
                "records": {k: self.store.all(k) for k in KINDS}, "notes": notes,
                "checksums": {p: digest(t) for p, t in notes.items()},
                "exclusions": ["API keys", "search index (rebuildable)", "non-Markdown attachments"]}

    def restore(self, archive):
        if not isinstance(archive, dict) or archive.get("schema_version") != 1:
            raise ValueError("Unsupported archive version.")
        records, notes = archive.get("records"), archive.get("notes")
        if not isinstance(records, dict) or set(records) != set(KINDS) or not isinstance(notes, dict):
            raise ValueError("Invalid archive structure.")
        if not all(isinstance(records[k], list) for k in KINDS):
            raise ValueError("Invalid record lists.")
        if sum(len(v) for v in records.values()) > 50000 or len(notes) > 5000:
            raise ValueError("Archive exceeds the restore limit.")
        incoming = {}
        for kind, rows in records.items():
            for r in rows:
                if not isinstance(r, dict) or not isinstance(r.get("id"), str) or not re.fullmatch(r"[\w-]{1,100}", r["id"]):
                    raise ValueError("Invalid record ID.")
                if r["id"] in incoming:
                    raise ValueError("Duplicate record ID in archive.")
                incoming[r["id"]] = (kind, r)
                existing = self.store.db.execute("SELECT kind,data FROM records WHERE id=?", (r["id"],)).fetchone()
                if existing and (existing[0] != kind or json.loads(existing[1]) != r):
                    raise ValueError("Archive conflicts with existing records. Restore into an empty data directory to preserve both versions.")
        fields = {
            "resource": ("title", "url", "notes", "progress", "concept_ids", "resource_type", "created_at"),
            "concept": ("title", "domain", "body", "path", "hash", "requires"),
            "goal": ("title", "concept_ids", "budget", "status"),
            "session": ("concept_id", "messages", "status", "created_at", "updated_at", "draft", "hint_used", "question_id", "mode"),
            "question": ("concept_id", "session_id", "prompt", "reference", "criteria", "hint", "choices", "correct_choice", "type", "provider", "source_ids", "source_snapshot", "rubric_version", "created_at"),
            "attempt": ("session_id", "concept_id", "question_id", "answer", "assisted", "created_at", "request_id", "status"),
            "assessment": ("attempt_id", "verdict", "explanation", "next_action", "provider", "version", "status", "rubric", "quotes", "correct", "missing", "reference", "created_at"),
            "review": ("concept_id", "due_at", "status", "step", "attempt_id"),
            "run": ("role", "created_at", "status"),
        }
        refs = {"session": {"concept_id": "concept"}, "question": {"concept_id": "concept", "session_id": "session"},
                "attempt": {"concept_id": "concept", "session_id": "session", "question_id": "question"},
                "assessment": {"attempt_id": "attempt"}, "review": {"concept_id": "concept"}}
        def ref(value, kind):
            return (value in incoming and incoming[value][0] == kind) or self.store.get(kind, value) is not None
        for kind, rows in records.items():
            for r in rows:
                if any(f not in r for f in fields[kind]):
                    raise ValueError("Incomplete " + kind + " record.")
                # Reject malformed archives before writing any record or file.
                string_fields = {
                    "resource": ("title", "url", "notes", "resource_type"),
                    "concept": ("title", "domain", "body", "path", "hash"),
                    "goal": ("title", "budget", "status"),
                    "session": ("concept_id", "status", "draft"),
                    "question": ("prompt", "reference", "hint", "type"),
                    "attempt": ("answer", "request_id", "status"),
                    "assessment": ("verdict", "explanation", "next_action", "provider", "status"),
                    "review": ("status",), "run": ("role", "status"),
                }
                if any(not isinstance(r[f], str) for f in string_fields[kind]):
                    raise ValueError("Invalid " + kind + " text fields.")
                if kind == "session" and (not isinstance(r["messages"], list) or type(r["hint_used"]) is not bool):
                    raise ValueError("Invalid session.")
                if kind == "session":
                    for m in r["messages"]:
                        if not isinstance(m, dict) or m.get("role") not in ("you", "tutor") or not isinstance(m.get("text"), str):
                            raise ValueError("Invalid session message.")
                    if r.get("question_id") and not ref(r["question_id"], "question"):
                        raise ValueError("Missing session question.")
                if kind == "question":
                    if r["type"] not in ("theory", "short", "quiz", "walkthrough"):
                        raise ValueError("Invalid question type.")
                    if any(not isinstance(r[f], list) or any(not isinstance(x, str) for x in r[f]) for f in ("criteria", "choices")):
                        raise ValueError("Invalid question rubric.")
                    if type(r["correct_choice"]) is not int or "source_snapshot" not in r or not isinstance(r["source_snapshot"], str):
                        raise ValueError("Invalid question reference.")
                    if r["type"] == "quiz" and (len(r["choices"]) != 4 or not 0 <= r["correct_choice"] < 4):
                        raise ValueError("Invalid quiz.")
                if kind == "attempt" and type(r["assisted"]) is not bool:
                    raise ValueError("Invalid assistance flag.")
                if kind == "assessment":
                    if r["verdict"] not in ("correct", "partial", "incorrect", "uncertain") or type(r["version"]) is not int:
                        raise ValueError("Invalid assessment verdict.")
                    if any(not isinstance(r[f], list) or any(not isinstance(x, str) for x in r[f]) for f in ("rubric", "quotes", "correct", "missing")):
                        raise ValueError("Invalid feedback.")
                if kind == "review" and (type(r["step"]) is not int or not 0 <= r["step"] <= 4):
                    raise ValueError("Invalid review interval.")
                if kind == "resource":
                    if type(r["progress"]) is not int or not 0 <= r["progress"] <= 100:
                        raise ValueError("Invalid resource progress.")
                    if not isinstance(r["concept_ids"], list) or any(not isinstance(i, str) or not ref(i, "concept") for i in r["concept_ids"]):
                        raise ValueError("Invalid resource concept links.")
                for f, expected in refs.get(kind, {}).items():
                    if not isinstance(r[f], str) or not ref(r[f], expected):
                        raise ValueError("Archive contains a dangling " + f + ".")
                if kind in ("concept", "goal"):
                    links = r.get("requires", []) if kind == "concept" else r["concept_ids"]
                    if not isinstance(links, list) or any(not isinstance(i, str) or not ref(i, "concept") for i in links):
                        raise ValueError("Archive contains dangling concept links.")
                if kind == "concept":
                    self.store.safe_path(r["path"])
                    if r["path"] not in notes and not r.get("missing"):
                        raise ValueError("Concept note missing from archive.")
                if kind in ("session", "attempt", "review", "run"):
                    for key in ("created_at", "updated_at", "due_at"):
                        if key in r:
                            try:
                                d = datetime.fromisoformat(r[key])
                                if d.tzinfo is None:
                                    raise ValueError()
                            except (ValueError, TypeError):
                                raise ValueError("Invalid archive timestamp.") from None
        for relative, note in notes.items():
            p = self.store.safe_path(relative)
            if not isinstance(note, str) or len(note) > 300000 or archive.get("checksums", {}).get(relative) != digest(note):
                raise ValueError("Archive checksum failed.")
            if p.exists() and p.read_text(encoding="utf-8") != note:
                raise ValueError("Archive conflicts with a note. Restore into an empty data directory.")
        adjacency = {c["id"]: c.get("requires", []) for c in self.store.all("concept")}
        adjacency.update({c["id"]: c["requires"] for c in records["concept"]})
        visited, visiting = set(), set()
        def visit(node):
            if node in visiting:
                raise ValueError("Archive prerequisite cycle.")
            if node in visited:
                return
            visiting.add(node)
            for parent in adjacency.get(node, []):
                visit(parent)
            visiting.remove(node)
            visited.add(node)
        for node in adjacency:
            visit(node)
        # Save a complete pre-restore snapshot. Merge only: existing data is never removed.
        backup_dir = self.store.root / "backups"
        backup_dir.mkdir(exist_ok=True)
        (backup_dir / (uid() + ".json")).write_text(json.dumps(self.export(), ensure_ascii=False), encoding="utf-8")
        try:
            for kind, rows in records.items():
                for r in rows:
                    self.store.put(kind, r)
                    if kind == "concept" and not r.get("missing"):
                        self.store.index(r)
            for relative, note in notes.items():
                self.store.queue_note(relative, note)
            # Restore non-secret preferences, but never enable cloud automatically.
            imported = archive.get("settings", {})
            self.update_settings(dict(imported, cloud_enabled=False), commit=False)
            self.store.commit()
        except Exception:
            self.store.db.rollback()
            raise
        return {"saved": True, "records": len(incoming), "notes": len(notes)}

    def update_settings(self, data, commit=True):
        p = self.settings()
        for k in ("model", "language"):
            if k in data:
                p[k] = text(data[k], 100, k != "model")
        for k, maximum in (("request_limit", 1000), ("review_cap", 100)):
            if k in data:
                if type(data[k]) is not int or not 1 <= data[k] <= maximum:
                    raise ValueError("Invalid " + k + ".")
                p[k] = data[k]
        if "cloud_enabled" in data:
            if type(data["cloud_enabled"]) is not bool:
                raise ValueError("Invalid cloud setting.")
            p["cloud_enabled"] = data["cloud_enabled"]
        if p["cloud_enabled"] and (not p["model"] or not os.environ.get("OPENAI_API_KEY")):
            raise ValueError("Set OPENAI_API_KEY and choose a model before enabling cloud AI.")
        self.store.set_setting("preferences", p)
        if commit:
            self.store.commit()
        return {"saved": True}

    def dispatch(self, action, data):
        with self.store.lock:
            self.store.flush()
            self.store.sync()
            if action == "concept":
                return self.create_concept(data)
            if action == "lesson":
                topic = text(data.get("topic"), 200)
                lesson = self.cloud("lesson", {"topic": topic, "level": text(data.get("level", "Introductory"), 200),
                                                "source_ids": [], "existing_concepts": [c["title"] for c in self.store.all("concept")][:50]})
                if not lesson["body"].strip():
                    raise ProviderError("AI returned an empty lesson. Please retry.")
                return {"id": "", "hash": "", "title": lesson["title"][:160], "domain": lesson["domain"][:80],
                        "body": lesson["body"] + "\n\nAI draft limitations: " + lesson["limitations"],
                        "source": "AI-generated draft; verify against independent sources before relying on it.", "requires": []}
            if action == "resource":
                record_id = data.get("id") or uid()
                old = self.store.get("resource", record_id)
                if data.get("id") and not old:
                    raise ValueError("Resource not found.")
                progress = data.get("progress", 0)
                if type(progress) is not int or not 0 <= progress <= 100:
                    raise ValueError("Progress must be between 0 and 100.")
                resource_type = data.get("resource_type", "course")
                if resource_type not in ("course", "book", "video", "tool", "article"):
                    raise ValueError("Invalid resource type.")
                links = data.get("concept_ids", [])
                if not isinstance(links, list) or len(links) > 100:
                    raise ValueError("Invalid concept links.")
                for i in links:
                    self.need("concept", i)
                resource = {"id": record_id, "title": text(data.get("title"), 200), "url": text(data.get("url", ""), 2000, False),
                            "notes": text(data.get("notes", ""), 10000, False), "progress": progress,
                            "resource_type": resource_type, "concept_ids": links, "created_at": old["created_at"] if old else now()}
                self.store.put("resource", resource)
                self.store.commit()
                return resource
            if action == "examples":
                bundled = json.loads((Path(__file__).parent.parent / "content/examples.json").read_text(encoding="utf-8"))
                for c in bundled:
                    if not self.store.get("concept", c["id"]):
                        c.update(origin="demo", created_at=now())
                        self.store.save_concept(c)
                self.store.commit()
                return {"saved": True}
            if action == "goal":
                ids = data.get("concept_ids", [])
                if not isinstance(ids, list) or len(ids) > 100:
                    raise ValueError("Invalid learning path.")
                for i in ids:
                    self.need("concept", i)
                g = {"id": uid(), "title": text(data.get("title"), 200), "concept_ids": ids,
                     "budget": text(data.get("budget", "25 minutes a day"), 100), "status": "active", "created_at": now()}
                self.store.put("goal", g)
                self.store.commit()
                return g
            if action == "goal-status":
                g = self.need("goal", data.get("id"))
                if data.get("status") not in ("active", "paused", "complete"):
                    raise ValueError("Invalid goal status.")
                g["status"] = data["status"]
                self.store.put("goal", g)
                self.store.commit()
                return {"saved": True}
            if action == "start":
                return self.start(data)
            if action == "ask":
                return self.ask(data)
            if action == "question":
                return self.make_question(data)
            if action == "submit":
                return self.submit(data)
            if action == "revise":
                return self.revise_grade(data)
            if action == "draft":
                s = self.need("session", data.get("session_id"))
                s["draft"] = text(data.get("draft", ""), 20000, False)
                self.store.put("session", s)
                self.store.commit()
                return {"saved": True}
            if action == "hint":
                s = self.need("session", data.get("session_id"))
                q = self.need("question", s.get("question_id"))
                s["hint_used"] = True
                self.save_session(s)
                return {"hint": q["hint"]}
            if action == "finish":
                s = self.need("session", data.get("session_id"))
                s["status"] = "complete"
                self.save_session(s)
                return {"saved": True}
            if action == "settings":
                return self.update_settings(data)
            if action == "restore":
                return self.restore(data)
            raise ValueError("Unknown action.")
