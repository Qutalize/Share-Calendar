"""
notification_service.py - 通知生成・既読管理
"""
from flask import Blueprint, jsonify
from data import get_db
from auth import login_required, get_current_user

notification_bp = Blueprint("notification", __name__)


@notification_bp.route("/api/notifications")
@login_required
def get_notifications():
    user = get_current_user()
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM notifications
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT 50""",
        (user["id"],)
    ).fetchall()
    unread_count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
        (user["id"],)
    ).fetchone()[0]
    conn.close()
    return jsonify({
        "notifications": [dict(r) for r in rows],
        "unread_count": unread_count,
    })


@notification_bp.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    user = get_current_user()
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notif_id, user["id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "既読にしました"})


@notification_bp.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    user = get_current_user()
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (user["id"],)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "全て既読にしました"})
