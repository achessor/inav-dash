import csv
import datetime as dt
import hashlib
import io
import os
import re
import sqlite3
from contextlib import closing

from decoder import decode

TELEMETRY = {"timestamp_utc", "command", "measurement", "value"}
RAW = {"timestamp_utc", "command", "command_id", "payload_hex"}


def connect():
    db = sqlite3.connect(os.getenv("INAV_DB", "telemetry.sqlite3"))
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS uploads (
            digest TEXT PRIMARY KEY, session TEXT NOT NULL,
            filename TEXT NOT NULL, kind TEXT NOT NULL, csv BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS samples (
            digest TEXT REFERENCES uploads(digest),
            ts TEXT NOT NULL, command TEXT NOT NULL, metric TEXT NOT NULL, value TEXT NOT NULL,
            PRIMARY KEY (digest, ts, command, metric)
        );
        CREATE INDEX IF NOT EXISTS uploads_session ON uploads(session);
    """)
    return closing(db)


def import_csv(filename, content):
    digest = hashlib.sha256(content).hexdigest()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
    headers = set(reader.fieldnames or [])
    if RAW <= headers:
        kind = "raw"
    elif TELEMETRY <= headers:
        kind = "telemetry"
    else:
        raise ValueError("Expected an INAV raw or telemetry CSV header.")
    match = re.fullmatch(r"(?:raw|telemetry)_(\d{8}_\d{6})\.csv", filename, re.I)
    session = match[1] if match else f"{filename} ({digest[:8]})"
    samples = []
    row_count = 0
    for row in reader:
        row_count += 1
        try:
            timestamp = dt.datetime.fromisoformat(row["timestamp_utc"])
            if timestamp.tzinfo is None:
                raise ValueError("Timestamp needs a UTC offset.")
            timestamp = timestamp.astimezone(dt.timezone.utc).isoformat(timespec="microseconds")
            command = row["command"]
            if not command:
                raise ValueError("Missing command.")
            if kind == "raw":
                values = decode(command, bytes.fromhex(row["payload_hex"]))
            else:
                if not row["measurement"] or row["value"] is None:
                    raise ValueError("Missing measurement or value.")
                values = {row["measurement"]: row["value"]}
            samples.extend((digest, timestamp, command, key, str(value)) for key, value in values.items())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc
    if not row_count:
        raise ValueError("The CSV contains no data rows.")
    with connect() as db, db:
        inserted = db.execute("INSERT OR IGNORE INTO uploads VALUES (?, ?, ?, ?, ?)",
                              (digest, session, filename, kind, content)).rowcount
        if inserted:
            db.executemany("INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?, ?)", samples)
    return bool(inserted)


def session_names():
    with connect() as db:
        return [row[0] for row in db.execute("SELECT DISTINCT session FROM uploads ORDER BY session DESC")]


def read_samples(sessions):
    placeholders = ",".join("?" for _ in sessions)
    with connect() as db:
        return db.execute(f"""
            SELECT u.session, s.ts, s.command, s.metric, s.value, u.kind
            FROM samples s JOIN uploads u USING (digest)
            WHERE u.session IN ({placeholders})
            ORDER BY s.ts, CASE u.kind WHEN 'raw' THEN 0 ELSE 1 END, u.digest
        """, sessions).fetchall()


def uploaded_files():
    with connect() as db:
        return db.execute("""
            SELECT digest, session, filename, kind
            FROM uploads ORDER BY session DESC, kind, filename, digest
        """).fetchall()


def original_csv(digest):
    with connect() as db:
        return db.execute("SELECT csv FROM uploads WHERE digest = ?", (digest,)).fetchone()[0]
