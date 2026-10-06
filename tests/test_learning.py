import copy
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from learning.app import LearningApp
from learning.providers import ProviderError
from learning.store import digest
from server import make_server


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = LearningApp(self.tmp.name)
        self.app.dispatch("examples", {})
        self.cid = "demo-recursion"

    def tearDown(self):
        self.app.store.close()
        self.tmp.cleanup()

    def question(self, hint=False):
        s = self.app.dispatch("start", {"concept_id": self.cid})
        s = self.app.dispatch("question", {"session_id": s["id"], "type": "theory"})
        if hint:
            self.app.dispatch("hint", {"session_id": s["id"]})
        return s

    def answer(self, s, request="answer-1"):
        return self.app.dispatch("submit", {"session_id": s["id"], "question_id": s["question"]["id"],
                                            "answer": "A recursive function calls itself on a smaller problem, and a base case stops the calls.\n", "request_id": request})

    def self_grade(self, s, verdict="correct"):
        return self.app.dispatch("revise", {"attempt_id": s["attempts"][-1]["id"], "verdict": verdict,
                                            "explanation": "Checked the explanation and example against the frozen rubric."})

    def test_reading_does_not_establish_independence(self):
        self.app.dispatch("start", {"concept_id": self.cid})
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Encountered")

    def test_offline_does_not_claim_to_grade_meaning(self):
        s = self.answer(self.question())
        self.assertEqual(s["assessments"][-1]["verdict"], "uncertain")
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Encountered")

    def test_independent_self_grade_has_auditable_evidence(self):
        s = self.answer(self.question())
        self.self_grade(s)
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Demonstrated independently")
        self.assertEqual(self.app.store.all("assessment")[-1]["provider"], "self")
        self.assertEqual(len(self.app.store.all("assessment")), 2)

    def test_hint_marks_assistance(self):
        s = self.answer(self.question(hint=True))
        self.self_grade(s)
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Demonstrated with help")

    def test_tutor_help_during_question_marks_assistance(self):
        s = self.question()
        self.app.dispatch("ask", {"session_id": s["id"], "message": "Explain the base case", "request_id": "msg-1"})
        s = self.answer(s)
        self.assertTrue(s["attempts"][0]["assisted"])

    def test_attempt_retry_is_idempotent(self):
        s = self.question()
        self.answer(s)
        self.answer(s)
        self.assertEqual(len(self.app.store.all("attempt")), 1)
        self.assertEqual(len(self.app.store.all("assessment")), 1)

    def test_request_key_rejects_different_answer(self):
        s = self.question()
        self.answer(s)
        with self.assertRaises(ValueError):
            self.app.dispatch("submit", {"session_id": s["id"], "question_id": s["question"]["id"], "answer": "Different answer", "request_id": "answer-1"})

    def test_question_is_frozen_and_reference_hidden(self):
        s = self.question()
        other = self.app.dispatch("question", {"session_id": s["id"], "type": "short"})
        self.assertEqual(other["question"]["id"], s["question"]["id"])
        self.assertNotIn("reference", s["question"])
        self.assertNotIn("correct_choice", s["question"])
        self.assertNotIn("source_snapshot", s["question"])

    def test_restart_preserves_draft_and_attempt(self):
        s = self.question()
        self.app.dispatch("draft", {"session_id": s["id"], "draft": "An unfinished explanation"})
        self.app.store.close()
        self.app = LearningApp(self.tmp.name)
        self.assertEqual(self.app.store.get("session", s["id"])["draft"], "An unfinished explanation")
        result = self.answer(s)
        self.assertTrue(result["attempts"][0]["answer"].endswith("\n"))

    def test_evaluator_timeout_preserves_answer_and_retry(self):
        s = self.question()
        with patch.object(self.app, "settings", return_value={"cloud_enabled": True}), patch.object(self.app, "cloud", side_effect=ProviderError("timeout")):
            with self.assertRaises(ProviderError):
                self.answer(s)
        self.assertEqual(self.app.store.all("attempt")[0]["status"], "pending")
        self.assertEqual(len(self.app.store.all("assessment")), 0)
        self.answer(s)
        self.assertEqual(len(self.app.store.all("attempt")), 1)

    def test_invented_quote_is_rejected(self):
        s = self.question()
        fake = {"correct": [], "missing": [], "quotes": ["made-up quote"], "verdict": "correct", "explanation": "ok", "next_action": "review"}
        with patch.object(self.app, "settings", return_value={"cloud_enabled": True}), patch.object(self.app, "cloud", return_value=fake):
            with self.assertRaises(ProviderError):
                self.answer(s)
        self.assertEqual(len(self.app.store.all("assessment")), 0)

    def test_message_retry_is_idempotent(self):
        s = self.question()
        data = {"session_id": s["id"], "message": "Explain recursion", "request_id": "msg-1"}
        self.app.dispatch("ask", data)
        self.app.dispatch("ask", data)
        messages = self.app.store.get("session", s["id"])["messages"]
        self.assertEqual(sum(m.get("request_id") == "msg-1" for m in messages), 1)

    def test_dispute_preserves_history_and_removes_evidence(self):
        s = self.answer(self.question())
        self.self_grade(s)
        self.self_grade(s, "disputed")
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Encountered")
        self.assertEqual(len(self.app.store.all("assessment")), 3)

    def test_retention_requires_delay_and_varied_question(self):
        s = self.answer(self.question())
        self.self_grade(s)
        attempt = self.app.store.all("attempt")[0]
        attempt["created_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.app.store.put("attempt", attempt)
        s2 = self.app.dispatch("question", {"session_id": s["id"], "type": "theory"})
        result = self.answer(s2, "answer-2")
        self.self_grade(result)
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Retained")

    def test_same_day_repeats_do_not_establish_retention(self):
        s = self.answer(self.question())
        self.self_grade(s)
        s2 = self.app.dispatch("question", {"session_id": s["id"], "type": "short"})
        self.self_grade(self.answer(s2, "answer-2"))
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Demonstrated independently")
        self.assertEqual(self.app.store.all("review")[0]["step"], 0)

    def test_external_note_edit_updates_search_not_evidence(self):
        c = self.app.store.get("concept", self.cid)
        p = self.app.store.safe_path(c["path"])
        p.write_text(p.read_text(encoding="utf-8") + "\nUnique quokka mnemonic", encoding="utf-8")
        self.app.state()
        self.assertEqual(self.app.store.search("quokka")[0]["id"], self.cid)
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Unknown")

    def test_stale_editor_refuses_overwrite(self):
        c = self.app.store.get("concept", self.cid)
        p = self.app.store.safe_path(c["path"])
        p.write_text(p.read_text(encoding="utf-8") + "\nExternal text", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.app.dispatch("concept", c)
        self.assertIn("External text", p.read_text(encoding="utf-8"))

    def test_unknown_frontmatter_survives_app_edit(self):
        c = self.app.store.get("concept", self.cid)
        p = self.app.store.safe_path(c["path"])
        p.write_text(p.read_text(encoding="utf-8").replace("---\n\n", "custom_tag: important\n---\n\n"), encoding="utf-8")
        self.app.state()
        c = self.app.store.get("concept", self.cid)
        c["body"] += "\nNew explanation"
        self.app.dispatch("concept", c)
        self.assertIn("custom_tag: important", p.read_text(encoding="utf-8"))

    def test_delete_and_restore_note_preserves_evidence(self):
        s = self.answer(self.question())
        self.self_grade(s)
        c = self.app.store.get("concept", self.cid)
        p = self.app.store.safe_path(c["path"])
        body = p.read_text(encoding="utf-8")
        p.unlink()
        self.app.state()
        self.assertTrue(self.app.store.get("concept", self.cid)["missing"])
        p.write_text(body, encoding="utf-8")
        self.app.state()
        self.assertFalse(self.app.store.get("concept", self.cid)["missing"])
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Demonstrated independently")

    def test_prerequisite_cycle_rejected(self):
        c = self.app.store.get("concept", "demo-functions")
        c["requires"] = [self.cid]
        with self.assertRaises(ValueError):
            self.app.dispatch("concept", c)

    def test_lossless_export_restore(self):
        s = self.answer(self.question(hint=True))
        self.self_grade(s)
        self.app.dispatch("goal", {"title": "Understand recursion", "concept_ids": ["demo-functions", self.cid]})
        archive = self.app.export()
        with tempfile.TemporaryDirectory() as target:
            restored = LearningApp(target)
            try:
                restored.dispatch("restore", archive)
                output = restored.export()
                self.assertEqual(output["records"], archive["records"])
                self.assertEqual(output["notes"], archive["notes"])
                self.assertFalse(output["settings"]["cloud_enabled"])
                self.assertEqual(restored.store.search("base case")[0]["id"], self.cid)
            finally:
                restored.store.close()

    def test_restore_rejects_path_traversal_before_writes(self):
        archive = self.app.export()
        archive["notes"]["../escape.md"] = "malicious"
        archive["checksums"]["../escape.md"] = digest("malicious")
        with self.assertRaises(ValueError):
            self.app.dispatch("restore", archive)
        self.assertFalse((Path(self.tmp.name) / "escape.md").exists())

    def test_restore_rejects_invalid_checksum(self):
        archive = self.app.export()
        path = next(iter(archive["notes"]))
        archive["notes"][path] += "tamper"
        with self.assertRaises(ValueError):
            self.app.dispatch("restore", archive)

    def test_restore_rejects_malformed_records(self):
        archive = self.app.export()
        archive["records"]["concept"][0]["body"] = 123
        with self.assertRaises(ValueError):
            self.app.dispatch("restore", archive)

    def test_cloud_off_never_calls_provider(self):
        s = self.question()
        with patch("learning.app.OpenAIProvider.run", side_effect=AssertionError("Network called")):
            self.answer(s)
            self.app.dispatch("ask", {"session_id": s["id"], "message": "Explain", "request_id": "msg-1"})

    def test_cloud_limit_is_enforced_before_provider(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-test-key"}):
            self.app.dispatch("settings", {"model": "test-model", "cloud_enabled": True, "request_limit": 1})
            fake = ({"reply": "Example", "source_ids": []}, {})
            with patch("learning.app.OpenAIProvider.run", return_value=fake) as provider:
                self.app.cloud("teach", {})
                with self.assertRaises(ProviderError):
                    self.app.cloud("teach", {})
                self.assertEqual(provider.call_count, 1)

    def test_export_never_contains_environment_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret-synthetic-key"}):
            self.assertNotIn("secret-synthetic-key", json.dumps(self.app.export()))

    def test_course_completion_does_not_create_proficiency(self):
        resource = self.app.dispatch("resource", {"title": "A course", "progress": 100, "concept_ids": [self.cid], "resource_type": "course"})
        self.assertEqual(resource["progress"], 100)
        self.assertEqual(self.app.proficiency(self.cid)["state"], "Unknown")
        archive = self.app.export()
        self.assertEqual(archive["records"]["resource"][0], resource)

    def test_ai_lesson_is_a_reviewable_draft_not_a_saved_note(self):
        fake = {"title": "Bayesian reasoning", "domain": "Mathematics", "body": "A draft explanation", "limitations": "Verify with a textbook"}
        with patch.object(self.app, "cloud", return_value=fake):
            draft = self.app.dispatch("lesson", {"topic": "Bayesian reasoning"})
        self.assertIn("AI-generated draft", draft["source"])
        self.assertEqual(len(self.app.store.all("concept")), 6)

    def test_new_question_reactivates_finished_session(self):
        s = self.answer(self.question())
        self.app.dispatch("finish", {"session_id": s["id"]})
        s = self.app.dispatch("question", {"session_id": s["id"], "type": "short"})
        self.assertEqual(s["status"], "active")

    def test_interrupted_projection_preserves_concurrent_external_edit(self):
        c = self.app.store.get("concept", self.cid)
        p = self.app.store.safe_path(c["path"])
        original = p.read_text(encoding="utf-8")
        self.app.store.queue_note(c["path"], original + "\nPending app write")
        self.app.store.db.commit()
        p.write_text(original + "\nExternal edit after commit", encoding="utf-8")
        self.app.store.flush()
        self.assertIn("External edit after commit", p.read_text(encoding="utf-8"))
        conflicts = list((self.app.store.vault / "Conflicts").glob("*.md"))
        self.assertEqual(len(conflicts), 1)
        self.assertIn("Pending app write", conflicts[0].read_text(encoding="utf-8"))


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = LearningApp(self.tmp.name)
        self.server = make_server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.app.store.close()
        self.tmp.cleanup()

    def test_state_and_static_assets(self):
        for path in ("/", "/app.js", "/styles.css", "/api/state"):
            with urllib.request.urlopen(self.url + path) as r:
                self.assertEqual(r.status, 200)
                self.assertIsNotNone(r.headers.get("Content-Security-Policy"))

    def test_csrf_and_origin_protection(self):
        with urllib.request.urlopen(self.url + "/api/state") as r:
            token = json.load(r)["csrf_token"]
        for headers in ({}, {"X-App-Token": token, "Origin": "https://evil.example"}):
            req = urllib.request.Request(self.url + "/api/examples", b"{}", {"Content-Type": "application/json"} | headers)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)
        req = urllib.request.Request(self.url + "/api/examples", b"{}", {"Content-Type": "application/json", "X-App-Token": token})
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 200)

    def test_dns_rebinding_host_rejected(self):
        req = urllib.request.Request(self.url + "/api/state", headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 403)

    def test_export_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.url + "/api/export")
        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
