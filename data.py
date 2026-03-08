"""
data.py - デモデータ・データベース初期化・ユーティリティ
"""
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "calendar.db")



def get_db():
    """データベース接続を返す"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    """データベースとテーブルを初期化する"""
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            group_id INTEGER REFERENCES groups(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT,
            description TEXT,
            is_public INTEGER DEFAULT 0,
            group_id INTEGER REFERENCES groups(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            friend_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, friend_id)
        );

        CREATE TABLE IF NOT EXISTS event_participations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            response TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            related_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # デモデータ挿入（初回のみ）
    existing = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        _insert_demo_data(c)

    conn.commit()
    conn.close()


def _insert_demo_data(c):
    """デモ用初期データを挿入"""
    now = datetime.now()

    # グループ
    c.execute("INSERT INTO groups (name, owner_id) VALUES (?, ?)", ("サッカーサークル", 1))
    group_id = c.lastrowid

    # ユーザー
    users = [
        ("alice", hash_password("password"), "アリス", group_id),
        ("bob", hash_password("password"), "ボブ", group_id),
        ("carol", hash_password("password"), "キャロル", group_id),
    ]
    c.executemany(
        "INSERT INTO users (username, password_hash, display_name, group_id) VALUES (?,?,?,?)",
        users
    )

    # イベント（aliceのID=1）
    base = now.replace(hour=10, minute=0, second=0, microsecond=0)
    events = [
        (1, "チームミーティング", (base + timedelta(days=1)).isoformat(),
         (base + timedelta(days=1, hours=1)).isoformat(), "会議室A", "週次ミーティング", 1, group_id),
        (1, "ランチ会", (base + timedelta(days=1, hours=0, minutes=30)).isoformat(),
         (base + timedelta(days=1, hours=2)).isoformat(), "レストランB", "ランチ！", 0, None),
        (1, "勉強会", (base + timedelta(days=3)).isoformat(),
         (base + timedelta(days=3, hours=2)).isoformat(), "図書館", "Python勉強会", 1, group_id),
        (2, "サッカー練習", (base + timedelta(days=5)).isoformat(),
         (base + timedelta(days=5, hours=2)).isoformat(), "グラウンド", "練習試合", 1, group_id),
    ]
    c.executemany(
        """INSERT INTO events
           (user_id, title, start_time, end_time, location, description, is_public, group_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        events
    )

    # フレンド関係（相互登録: alice-bob, alice-carol, bob-carol）
    friendships = [
        (1, 2), (2, 1),  # alice ↔ bob
        (1, 3), (3, 1),  # alice ↔ carol
        (2, 3), (3, 2),  # bob  ↔ carol  ← 追加（これがないとbobのフレンド一覧が不完全）
    ]
    for uid, fid in friendships:
        c.execute(
            "INSERT OR IGNORE INTO friendships (user_id, friend_id, status) VALUES (?,?,'accepted')",
            (uid, fid)
        )

    # 参加登録
    c.execute("INSERT INTO event_participations (event_id, user_id, response) VALUES (3, 2, 'accepted')")
    c.execute("INSERT INTO event_participations (event_id, user_id, response) VALUES (4, 1, 'pending')")

    # 通知
    c.execute("""INSERT INTO notifications (user_id, type, message, related_id)
                 VALUES (1, 'double_booking', 'チームミーティングとランチ会が重複しています！', 1)""")
    c.execute("""INSERT INTO notifications (user_id, type, message, related_id)
                 VALUES (1, 'event_invite', 'ボブさんからサッカー練習への招待が届いています', 4)""")


if __name__ == "__main__":
    init_db()
    print("Database initialized.")