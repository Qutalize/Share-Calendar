"""
friend_service.py - フレンド管理・検索
"""
from flask import Blueprint, request, jsonify
from data import get_db
from auth import login_required, get_current_user

friend_bp = Blueprint("friend", __name__)


@friend_bp.route("/api/friends")
@login_required
def get_friends():
    user = get_current_user()
    conn = get_db()
    friends = conn.execute(
        """SELECT u.id, u.username, u.display_name, f.status
           FROM friendships f
           JOIN users u ON f.friend_id = u.id
           WHERE f.user_id = ?
             AND f.friend_id != f.user_id""",
        (user["id"],)
    ).fetchall()
    conn.close()
    return jsonify({"friends": [dict(f) for f in friends]})


@friend_bp.route("/api/friends/search")
@login_required
def search_users():
    user = get_current_user()
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"users": []})

    conn = get_db()
    results = conn.execute(
        """SELECT id, username, display_name FROM users
           WHERE (username LIKE ? OR display_name LIKE ?)
             AND id != ?
           LIMIT 10""",
        (f"%{q}%", f"%{q}%", user["id"])
    ).fetchall()
    conn.close()
    return jsonify({"users": [dict(r) for r in results]})


@friend_bp.route("/api/friends/request", methods=["POST"])
@login_required
def send_friend_request():
    user = get_current_user()
    data = request.get_json()
    friend_id = data.get("friend_id")

    if not friend_id or friend_id == user["id"]:
        return jsonify({"error": "無効なリクエストです"}), 400

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM friendships WHERE user_id = ? AND friend_id = ?",
            (user["id"], friend_id)
        ).fetchone()
        if existing:
            return jsonify({"error": "既にフレンド申請済みです"}), 409

        conn.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (?,?,'pending')",
            (user["id"], friend_id)
        )
        conn.execute(
            """INSERT INTO notifications (user_id, type, message, related_id)
               VALUES (?,?,?,?)""",
            (friend_id, "friend_request",
             f"{user['display_name']}さんからフレンド申請が届いています", user["id"])
        )
        conn.commit()
        return jsonify({"message": "フレンド申請を送りました"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@friend_bp.route("/api/friends/respond", methods=["POST"])
@login_required
def respond_friend_request():
    user = get_current_user()
    data = request.get_json()
    requester_id = data.get("user_id")
    action = data.get("action")  # 'accept' or 'reject'

    if action not in ("accept", "reject"):
        return jsonify({"error": "actionは'accept'または'reject'を指定してください"}), 400

    conn = get_db()
    status = "accepted" if action == "accept" else "rejected"

    # 申請レコードは (user_id=申請者, friend_id=受信者=自分) で保存されている
    # ※旧コードは user_id と friend_id が逆だったため 0件更新になっていた
    cur = conn.execute(
        "UPDATE friendships SET status = ? WHERE user_id = ? AND friend_id = ?",
        (status, requester_id, user["id"])
    )

    if cur.rowcount == 0:
        conn.close()
        return jsonify({"error": "申請レコードが見つかりません"}), 404

    if action == "accept":
        # 相互フレンド登録（受信者→申請者 のレコードを追加/更新）
        conn.execute(
            """INSERT INTO friendships (user_id, friend_id, status)
               VALUES (?,?,'accepted')
               ON CONFLICT(user_id, friend_id) DO UPDATE SET status='accepted'""",
            (user["id"], requester_id)
        )
        conn.execute(
            """INSERT INTO notifications (user_id, type, message)
               VALUES (?,?,?)""",
            (requester_id, "friend_request",
             f"{user['display_name']}さんがフレンド申請を承認しました")
        )

    conn.commit()
    conn.close()
    return jsonify({"message": "フレンド申請に回答しました"})
