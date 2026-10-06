"""SQLite records, full-text lookup, and safe Markdown projection."""
import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid4())


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "records.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS kind_index ON records(kind);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS projections (path TEXT PRIMARY KEY, text TEXT NOT NULL, expected_hash TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED, title, body, domain);
            PRAGMA user_version=1;
        """)
        if "expected_hash" not in {r[1] for r in self.db.execute("PRAGMA table_info(projections)")}:
            self.db.execute("ALTER TABLE projections ADD COLUMN expected_hash TEXT")
        self.db.commit()
        self.flush()

    def close(self):
        self.db.close()

    def put(self, kind, record):
        self.db.execute("INSERT INTO records VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                        (kind, record["id"], json.dumps(record, ensure_ascii=False)))

    def get(self, kind, record_id):
        row = self.db.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, record_id)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        return [json.loads(r[0]) for r in self.db.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid", (kind,))]

    def setting(self, key, default=None):
        row = self.db.execute("SELECT data FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key, data):
        self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(data)))

    def safe_path(self, relative):
        if not isinstance(relative, str) or not relative.endswith(".md") or "\\" in relative:
            raise ValueError("Invalid Markdown path")
        p = (self.vault / relative).resolve()
        if not p.is_relative_to(self.vault) or p == self.vault:
            raise ValueError("Path must stay inside the vault")
        return p

    def queue_note(self, relative, text):
        p = self.safe_path(relative)
        current_hash = digest(p.read_text(encoding="utf-8")) if p.exists() else None
        self.db.execute("INSERT OR REPLACE INTO projections(path,text,expected_hash) VALUES (?,?,?)", (relative, text, current_hash))

    def flush(self):
        """Durable outbox: interrupted file writes are retried on the next request/start."""
        for relative, text, expected_hash in list(self.db.execute("SELECT path,text,expected_hash FROM projections")):
            p = self.safe_path(relative)
            current_hash = digest(p.read_text(encoding="utf-8")) if p.exists() else None
            if current_hash not in (expected_hash, digest(text)):
                # Another editor changed the destination after the database commit.
                # Preserve both versions instead of replaying an old write over new work.
                conflict_path = self.safe_path("Conflicts/" + uid() + ".md")
                conflict_path.parent.mkdir(exist_ok=True)
                conflict_path.write_text("# Pending write conflict\n\nOriginal note: " + relative +
                                         "\n\nThe original file was preserved. Proposed content follows.\n\n```markdown\n" + text + "\n```\n", encoding="utf-8")
                notices = self.setting("notices", [])
                notices.append("A concurrent edit was preserved. Review " + conflict_path.relative_to(self.vault).as_posix())
                self.set_setting("notices", notices[-10:])
                self.db.execute("DELETE FROM projections WHERE path=?", (relative,))
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            temporary = p.with_suffix(".md.pending")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(p)
            self.db.execute("DELETE FROM projections WHERE path=?", (relative,))
        self.db.commit()

    def index(self, concept):
        self.db.execute("DELETE FROM search WHERE id=?", (concept["id"],))
        self.db.execute("INSERT INTO search VALUES (?,?,?,?)", (concept["id"], concept["title"],
                                                              concept["body"], concept["domain"]))

    def note(self, concept):
        related = []
        for i in concept.get("requires", []):
            parent = self.get("concept", i)
            if parent:
                related.append(f"[[Concepts/{i}|{parent['title']}]]")
        properties = {"id": concept["id"], "title": concept["title"], "domain": concept["domain"],
                      "type": "concept", "requires": related, "origin": concept.get("origin", "learner"),
                      "source": concept.get("source", "")}
        front = "\n".join(k + ": " + json.dumps(v, ensure_ascii=False) for k, v in properties.items())
        preserved = concept.get("extra_frontmatter", "")
        if preserved:
            front += "\n" + preserved
        return "---\n" + front + "\n---\n\n" + concept["body"]

    def save_concept(self, concept, expected_hash=None):
        existing = self.get("concept", concept["id"])
        if existing and expected_hash != existing.get("hash"):
            raise ValueError("This note changed since you opened it. Reload before saving; your editor text is kept.")
        concept["path"] = existing["path"] if existing else "Concepts/" + concept["id"] + ".md"
        current_file = self.safe_path(concept["path"])
        if existing and current_file.exists() and digest(current_file.read_text(encoding="utf-8")) != existing.get("hash"):
            raise ValueError("The file changed during saving. Refresh and try again; the original file is preserved.")
        text = self.note(concept)
        concept["hash"] = digest(text)
        self.put("concept", concept)
        self.index(concept)
        self.queue_note(concept["path"], text)

    def sync(self):
        """Import external text edits and notes; evidence is never derived from them."""
        warnings = list(self.setting("notices", []))
        concepts = self.all("concept")
        by_id = {c["id"]: c for c in concepts}
        found = set()
        for p in self.vault.rglob("*.md"):
            relative = p.relative_to(self.vault).as_posix()
            if relative.startswith("Sessions/"):
                continue
            try:
                self.safe_path(relative)
                if p.stat().st_size > 300_000:
                    warnings.append(f"Skipped large note: {relative}")
                    continue
                text = p.read_text(encoding="utf-8-sig")
                match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n)?", text, re.S)
                props = {}
                if match:
                    for line in match[1].splitlines():
                        if ":" in line and not line.startswith(" "):
                            key, value = line.split(":", 1)
                            try:
                                props[key.strip()] = json.loads(value.strip())
                            except ValueError:
                                props[key.strip()] = value.strip().strip("'\"")
                record_id = props.get("id")
                if record_id and (not isinstance(record_id, str) or not re.fullmatch(r"[\w-]{1,100}", record_id)):
                    warnings.append(f"Invalid note ID: {relative}")
                    continue
                if not record_id:
                    record_id = "note-" + digest(relative)[:20]
                if record_id in found:
                    warnings.append(f"Duplicate note ID: {relative}")
                    continue
                found.add(record_id)
                old = by_id.get(record_id)
                if old and old.get("hash") == digest(text):
                    old.update(path=relative, missing=False)
                    self.put("concept", old)
                    self.index(old)
                    continue
                if self.db.execute("SELECT kind FROM records WHERE id=? AND kind!='concept'", (record_id,)).fetchone():
                    warnings.append(f"ID belongs to another record: {relative}")
                    continue
                body = text[match.end():].lstrip("\r\n") if match else text
                concept = dict(old or {"id": record_id, "requires": [], "origin": "import", "created_at": now()})
                extras = []
                skip = False
                if match:
                    for line in match[1].splitlines():
                        if line and not line.startswith(" ") and ":" in line:
                            skip = line.split(":", 1)[0].strip() in {"id", "title", "domain", "type", "requires", "origin", "source"}
                        if not skip:
                            extras.append(line)
                concept.update(title=str(props.get("title", p.stem))[:160],
                               domain=str(props.get("domain", "Unsorted"))[:80], body=body,
                               source=str(props.get("source", concept.get("source", "")))[:2000],
                               extra_frontmatter="\n".join(extras), path=relative, hash=digest(text), missing=False)
                # External frontmatter links are proposals; accepted prerequisite IDs remain unchanged.
                self.put("concept", concept)
                self.index(concept)
            except (OSError, UnicodeError, ValueError):
                warnings.append(f"Could not read note: {relative}")
        for c in concepts:
            if c["id"] not in found:
                c["missing"] = True
                self.put("concept", c)
                self.db.execute("DELETE FROM search WHERE id=?", (c["id"],))
        self.db.commit()
        return warnings

    def search(self, query):
        tokens = re.findall(r"\w+", query, re.UNICODE)[:12]
        if not tokens:
            return []
        expr = " OR ".join('"' + t + '"' for t in tokens)
        return [self.get("concept", r[0]) for r in self.db.execute(
            "SELECT id FROM search WHERE search MATCH ? ORDER BY rank LIMIT 8", (expr,))]

    def commit(self):
        self.db.commit()
        self.flush()
