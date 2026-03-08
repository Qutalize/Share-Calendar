"""
main.py - 統合エントリポイント
ダブルブッキング防止カレンダーアプリ
"""
import os
from flask import Flask, send_from_directory
from data import init_db
from auth import auth_bp
from event_service import event_bp
from friend_service import friend_bp
from notification_service import notification_bp

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"]   = True  

# Blueprint登録
app.register_blueprint(auth_bp)
app.register_blueprint(event_bp)
app.register_blueprint(friend_bp)
app.register_blueprint(notification_bp)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    """SPAのルーティング"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.template_folder, "index.html")


if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("📅 ダブルブッキング防止カレンダー 起動中...")
    print("   http://localhost:5000")
    print("   デモアカウント: alice / password")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
