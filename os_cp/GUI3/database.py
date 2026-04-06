# database.py
# ─────────────────────────────────────────────────────────────────────────────
# SQLite persistence layer for all simulation runs.
# Stores config, raw output, parsed metrics, and trace file metadata.
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

# DB lives next to the script, or in a user-writable app data dir
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_sim_history.db")


# ── Schema ────────────────────────────────────────────────────────────────────
_CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,           -- ISO-8601
    label           TEXT    NOT NULL,           -- auto-generated human label
    trace_file      TEXT    NOT NULL,           -- full path
    trace_filename  TEXT    NOT NULL,           -- basename only (display)
    trace_summary   TEXT    NOT NULL DEFAULT '',-- e.g. "27L traces, 2.3Cr traces"

    -- Config snapshot (stored flat for easy display + filtering)
    l1_size         INTEGER NOT NULL,
    l1_assoc        INTEGER NOT NULL,
    l2_size         INTEGER NOT NULL,
    l2_assoc        INTEGER NOT NULL,
    policy          TEXT    NOT NULL,
    prefetch        TEXT    NOT NULL,           -- "ON" / "OFF"

    -- Full command that was executed
    command         TEXT    NOT NULL,

    -- Raw simulator stdout (kept for debugging / re-parsing)
    raw_output      TEXT    NOT NULL DEFAULT '',

    -- Parsed metrics as JSON blob
    metrics_json    TEXT    NOT NULL DEFAULT '{}',

    -- Duration of execution in seconds
    duration_s      REAL    NOT NULL DEFAULT 0.0,

    -- Status: "success" | "error"
    status          TEXT    NOT NULL DEFAULT 'success'
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp DESC);
"""


# ── Connection helper ─────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # dict-like rows
    conn.execute("PRAGMA journal_mode=WAL") # safer concurrent writes
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Call once at app startup."""
    with _connect() as conn:
        conn.execute(_CREATE_RUNS_TABLE)
        conn.execute(_CREATE_INDEX)
        conn.commit()


# ── Trace summary helper ──────────────────────────────────────────────────────
def compute_trace_summary(trace_path: str) -> str:
    """
    Reads the trace file and returns a human-readable summary.
    Format: "27L traces · 2.3Cr traces" (load vs store-like breakdown).
    Falls back gracefully if file is unreadable.
    """
    try:
        load_count  = 0
        store_count = 0
        total       = 0

        with open(trace_path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                parts = line.split()
                if not parts:
                    continue
                op = parts[0].upper()
                if op in ("L", "R", "LOAD", "READ", "I"):
                    load_count += 1
                elif op in ("S", "W", "STORE", "WRITE", "M"):
                    store_count += 1

        def _fmt(n: int) -> str:
            if n >= 10_000_000:
                return f"{n/10_000_000:.1f}Cr"
            elif n >= 100_000:
                return f"{n/100_000:.1f}L"
            elif n >= 1_000:
                return f"{n/1_000:.1f}K"
            return str(n)

        parts = []
        if load_count:
            parts.append(f"{_fmt(load_count)} loads")
        if store_count:
            parts.append(f"{_fmt(store_count)} stores")
        other = total - load_count - store_count
        if other > 0:
            parts.append(f"{_fmt(other)} other")
        if not parts:
            parts.append(f"{_fmt(total)} traces")

        return " · ".join(parts) if parts else f"{total} lines"

    except Exception:
        return "trace summary unavailable"


# ── Auto-label generator ──────────────────────────────────────────────────────
def _make_label(config: dict, run_number: int) -> str:
    """
    e.g.  "Run #14 — L1:32K/8w  L2:2M/16w  LRU  Prefetch ON"
    """
    def _size(b: int) -> str:
        if b >= 1_048_576:
            return f"{b // 1_048_576}M"
        elif b >= 1_024:
            return f"{b // 1_024}K"
        return str(b)

    l1  = f"L1:{_size(config['l1_size'])}/{config['l1_assoc']}w"
    l2  = f"L2:{_size(config['l2_size'])}/{config['l2_assoc']}w"
    pol = config["policy"]
    pre = f"Prefetch {config['prefetch']}"
    return f"Run #{run_number}  —  {l1}  {l2}  {pol}  {pre}"


# ── Write ─────────────────────────────────────────────────────────────────────
def save_run(
    trace_path:  str,
    config:      dict,
    command:     str,
    raw_output:  str,
    metrics:     dict,
    duration_s:  float,
    status:      str = "success",
) -> int:
    """
    Persist a completed simulation run.
    Returns the new row id.

    config dict keys expected:
        l1_size (int), l1_assoc (int),
        l2_size (int), l2_assoc (int),
        policy (str),  prefetch (str)
    """
    ts       = datetime.now().isoformat(timespec="seconds")
    filename = os.path.basename(trace_path)
    summary  = compute_trace_summary(trace_path)

    with _connect() as conn:
        # Determine next run number
        row = conn.execute("SELECT COUNT(*) as cnt FROM runs").fetchone()
        run_number = (row["cnt"] or 0) + 1

        label = _make_label(config, run_number)

        cursor = conn.execute(
            """
            INSERT INTO runs
                (timestamp, label, trace_file, trace_filename, trace_summary,
                 l1_size, l1_assoc, l2_size, l2_assoc, policy, prefetch,
                 command, raw_output, metrics_json, duration_s, status)
            VALUES
                (?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?,?)
            """,
            (
                ts, label, trace_path, filename, summary,
                config["l1_size"], config["l1_assoc"],
                config["l2_size"], config["l2_assoc"],
                config["policy"],  config["prefetch"],
                command, raw_output,
                json.dumps(metrics), duration_s, status,
            ),
        )
        conn.commit()
        return cursor.lastrowid


# ── Read ──────────────────────────────────────────────────────────────────────
def get_all_runs(limit: int = 200) -> list[dict]:
    """
    Return all runs, newest first, as a list of plain dicts.
    metrics_json is decoded back to a dict.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["metrics"] = json.loads(d.pop("metrics_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            d["metrics"] = {}
        result.append(d)
    return result


def get_run_by_id(run_id: int) -> Optional[dict]:
    """Fetch a single run by primary key. Returns None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()

    if row is None:
        return None

    d = dict(row)
    try:
        d["metrics"] = json.loads(d.pop("metrics_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        d["metrics"] = {}
    return d


def get_recent_runs(n: int = 10) -> list[dict]:
    """Shorthand — returns the n most recent runs."""
    return get_all_runs(limit=n)


# ── Delete ────────────────────────────────────────────────────────────────────
def delete_run(run_id: int) -> bool:
    """Delete a run by id. Returns True if a row was deleted."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_all_runs() -> int:
    """Wipe the entire history. Returns number of rows deleted."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM runs")
        conn.commit()
        return cursor.rowcount


# ── Rename / tag ──────────────────────────────────────────────────────────────
def rename_run(run_id: int, new_label: str) -> bool:
    """Allow user to give a custom name to a run."""
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE runs SET label = ? WHERE id = ?", (new_label.strip(), run_id)
        )
        conn.commit()
        return cursor.rowcount > 0


# ── Stats helpers (used by history panel summaries) ───────────────────────────
def get_run_count() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM runs").fetchone()
        return row["cnt"] if row else 0


def get_runs_for_comparison(id_a: int, id_b: int) -> tuple[Optional[dict], Optional[dict]]:
    """Convenience: fetch two runs at once for side-by-side comparison."""
    return get_run_by_id(id_a), get_run_by_id(id_b)


# ── Migration guard (future-proof) ───────────────────────────────────────────
def _get_schema_version() -> int:
    with _connect() as conn:
        try:
            row = conn.execute("PRAGMA user_version").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0


def _set_schema_version(v: int) -> None:
    with _connect() as conn:
        conn.execute(f"PRAGMA user_version = {v}")
        conn.commit()


# ── Module-level init convenience ─────────────────────────────────────────────
if __name__ == "__main__":
    # Quick smoke-test
    init_db()
    print(f"DB initialised at: {DB_PATH}")
    print(f"Total runs stored: {get_run_count()}")