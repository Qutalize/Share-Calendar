"""
auth.py - ログイン・セッション管理
"""
from flask import Blueprint, request, session, jsonify
from data import get_db, hash_password

auth_bp = Blueprint("auth", __name__)


def get_current_user():
    """セッションから現在のユーザー情報を取得"""
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT id, username, display_name, group_id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def login_required(f):
    """ログイン必須デコレータ"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return jsonify({"error": "ログインが必要です"}), 401
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "ユーザー名とパスワードを入力してください"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "ユーザー名またはパスワードが正しくありません"}), 401

    session["user_id"] = user["id"]
    return jsonify({
        "message": "ログイン成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "group_id": user["group_id"],
        }
    })


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "ログアウトしました"})


@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "").strip() or username

    if not username or not password:
        return jsonify({"error": "ユーザー名とパスワードを入力してください"}), 400
    if len(username) < 3:
        return jsonify({"error": "ユーザー名は3文字以上にしてください"}), 400
    if len(password) < 6:
        return jsonify({"error": "パスワードは6文字以上にしてください"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?,?,?)",
            (username, hash_password(password), display_name)
        )
        conn.commit()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        session["user_id"] = user["id"]
        return jsonify({
            "message": "登録成功",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "display_name": user["display_name"],
            }
        }), 201
    except Exception as e:
        return jsonify({"error": "このユーザー名は既に使用されています"}), 409
    finally:
        conn.close()


@auth_bp.route("/api/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "未ログイン"}), 401
    return jsonify({"user": user})
