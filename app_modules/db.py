import os
import sqlite3
from contextlib import closing
from datetime import datetime

DB_PATH = os.environ.get("INTERTEK_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "intertek.db"))
DB_PATH = os.path.abspath(DB_PATH)

def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS industries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    industry_id INTEGER,
    region_id INTEGER,
    contact_person TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (industry_id) REFERENCES industries(id) ON UPDATE CASCADE,
    FOREIGN KEY (region_id) REFERENCES regions(id) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    weight REAL DEFAULT 1.0,
    color TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    client_id INTEGER,
    owner TEXT,
    priority TEXT DEFAULT 'Medium',
    status TEXT DEFAULT 'Open',
    start_date TEXT,
    due_date TEXT,
    completed_date TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON UPDATE CASCADE ON DELETE SET NULL
);
"""

DEFAULT_INDUSTRIES = [
    "Oil & Gas / Petroleum Refining & Storage",
    "Power Generation",
    "Mining & Mineral Processing",
    "Steel & Metal Processing",
    "Cement & Building Materials",
    "Food & Beverage Manufacturing",
    "Cocoa & Agro-Processing",
    "Chemicals & Pharmaceuticals",
    "Textiles & Light Manufacturing",
    "LNG / LPG & Fuel Storage",
    "Water Treatment & Utilities",
    "Pulp & Paper / Printing",
    "Shipyards & Marine",
    "Other"
]

def init_db():
    with closing(get_conn()) as conn:
        conn.executescript(SCHEMA)
        cur = conn.execute("SELECT COUNT(*) as c FROM industries")
        if cur.fetchone()["c"] == 0:
            conn.executemany("INSERT INTO industries(name) VALUES (?)", [(x,) for x in DEFAULT_INDUSTRIES])
        conn.commit()

def now_iso():
    return datetime.utcnow().isoformat()

def list_table(table, where="", params=()):
    with closing(get_conn()) as conn:
        cur = conn.execute(f"SELECT * FROM {table} {where}", params)
        return [dict(row) for row in cur.fetchall()]

def insert(table, data: dict):
    ts = now_iso()
    data = dict(data)
    data.setdefault("created_at", ts)
    data.setdefault("updated_at", ts)
    keys = ",".join(data.keys())
    placeholders = ",".join(["?"]*len(data))
    with closing(get_conn()) as conn:
        cur = conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", tuple(data.values()))
        conn.commit()
        return cur.lastrowid

def update(table, id_, data: dict):
    data = dict(data)
    data["updated_at"] = now_iso()
    assignments = ",".join([f"{k}=?" for k in data.keys()])
    with closing(get_conn()) as conn:
        conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", tuple(data.values()) + (id_,))
        conn.commit()

def delete(table, id_):
    with closing(get_conn()) as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (id_,))
        conn.commit()
