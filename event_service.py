"""
event_service.py - 予定管理・ダブルブッキング判定
"""
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup


    
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from data import get_db
from auth import login_required, get_current_user

event_bp = Blueprint("event", __name__)


def parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"日時フォーマットエラー: {s}")


def check_double_booking(user_id: int, start: datetime, end: datetime,
                          exclude_event_id: int = None) -> list:
    """指定ユーザーのイベントとの重複を検出"""
    conn = get_db()
    query = """
        SELECT id, title, start_time, end_time FROM events
        WHERE user_id = ?
          AND start_time < ?
          AND end_time > ?
    """
    params = [user_id, end.isoformat(), start.isoformat()]
    if exclude_event_id:
        query += " AND id != ?"
        params.append(exclude_event_id)

    conflicts = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in conflicts]


@event_bp.route("/api/events")
@login_required
def get_events():
    user = get_current_user()
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    conn = get_db()

    # 自分のイベント
    query = "SELECT * FROM events WHERE user_id = ?"
    params = [user["id"]]

    if year and month:
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = f"{year:04d}-{month:02d}-01"
        end = f"{year:04d}-{month:02d}-{last_day:02d}T23:59:59"
        query += " AND start_time >= ? AND start_time <= ?"
        params += [start, end]

    my_events = [dict(r) for r in conn.execute(query, params).fetchall()]

    # フレンドの公開イベント
    friend_query = """
        SELECT e.*, u.display_name as owner_name FROM events e
        JOIN users u ON e.user_id = u.id
        WHERE e.is_public = 1
          AND e.user_id IN (
              SELECT friend_id FROM friendships
              WHERE user_id = ? AND status = 'accepted'
          )
    """
    friend_params = [user["id"]]
    if year and month:
        friend_query += " AND e.start_time >= ? AND e.start_time <= ?"
        friend_params += [start, end]

    friend_events = [dict(r) for r in conn.execute(friend_query, friend_params).fetchall()]
    conn.close()

    # ダブルブッキング検出
    conflicts = set()
    for i, ev1 in enumerate(my_events):
        s1 = parse_dt(ev1["start_time"])
        e1 = parse_dt(ev1["end_time"])
        for j, ev2 in enumerate(my_events):
            if i >= j:
                continue
            s2 = parse_dt(ev2["start_time"])
            e2 = parse_dt(ev2["end_time"])
            if s1 < e2 and e1 > s2:
                conflicts.add(ev1["id"])
                conflicts.add(ev2["id"])

    for ev in my_events:
        ev["is_conflict"] = ev["id"] in conflicts
        ev["is_mine"] = True

    for ev in friend_events:
        ev["is_conflict"] = False
        ev["is_mine"] = False

    return jsonify({"events": my_events + friend_events})


@event_bp.route("/api/events", methods=["POST"])
@login_required
def create_event():
    user = get_current_user()
    data = request.get_json()

    title = data.get("title", "").strip()
    start_str = data.get("start_time", "")
    end_str = data.get("end_time", "")
    location = data.get("location", "")
    train=data.get("train","")
    

    """
    Yahoo路線情報から所要時間と料金を取得する関数
    """

    "https://transit.yahoo.co.jp/?from=%7B%E5%87%BA%E7%99%BA%E5%9C%B0%7D&to=%7B%E5%88%B0%E7%9D%80%E5%9C%B0%7D&fromgid=&togid=&flatlon=&tlatlon=&via=&viacode=&y=2026&m=03&d=08&hh=13&m1=5&m2=3&type=5&ticket=ic&expkind=1&userpass=1&ws=3&s=0&al=1&shin=1&ex=1&hb=1&lb=1&sr=1&cmd=4014"
    route_url = (
        "https://transit.yahoo.co.jp/search/print?from="
        + location
        + "&to="
        + train
        +"&fromgid=&togid=&flatlon=&tlatlon=&via=&viacode=&y=2026&m=03&d=08&hh=13&m1=5&m2=3&type=5&ticket=ic&expkind=1&userpass=1&ws=3&s=0&al=1&shin=1&ex=1&hb=1&lb=1&sr=1&cmd=4014"
    )

    route_response = requests.get(route_url)
    route_soup = BeautifulSoup(route_response.text, "html.parser")

    route_summary = route_soup.find("div", class_="routeSummary")

    required_time = route_summary.find("li", class_="time").get_text()
    fare = route_summary.find("li", class_="fare").get_text()




    #print("所要時間：" + required_time)
    #print("料金：" + fare)
    print("URL：" + route_url)

    location=train
    train=required_time+fare
    
    
    description = data.get("description", "")
    is_public = data.get("is_public", False)

    if not title:
        return jsonify({"error": "タイトルを入力してください"}), 400
    if not start_str or not end_str:
        return jsonify({"error": "開始時刻と終了時刻を入力してください"}), 400

    try:
        start = parse_dt(start_str)
        end = parse_dt(end_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if start >= end:
        return jsonify({"error": "終了時刻は開始時刻より後にしてください"}), 400

    # ダブルブッキング検出
    conflicts = check_double_booking(user["id"], start, end)
    conflict_warning = None
    if conflicts:
        names = "、".join(c["title"] for c in conflicts)
        conflict_warning = f"⚠️ ダブルブッキング警告: 「{names}」と時間が重複しています"

    conn = get_db()
    try:
        c = conn.execute(
            """INSERT INTO events
               (user_id, title, start_time, end_time, location,train,description, is_public)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user["id"], title, start.isoformat(), end.isoformat(),
             location,train, description, 1 if is_public else 0)
        )
        event_id = c.lastrowid

        # ダブルブッキング通知を保存
        if conflicts:
            conn.execute(
                """INSERT INTO notifications (user_id, type, message, related_id)
                   VALUES (?,?,?,?)""",
                (user["id"], "double_booking", conflict_warning, event_id)
            )

        conn.commit()

        event = dict(conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone())
        event["is_conflict"] = bool(conflicts)
        event["is_mine"] = True

        return jsonify({
            "event": event,
            "warning": conflict_warning,
            "conflicts": conflicts
        }), 201
    finally:
        conn.close()


@event_bp.route("/api/events/<int:event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id):
    user = get_current_user()
    conn = get_db()
    event = conn.execute(
        "SELECT * FROM events WHERE id = ? AND user_id = ?", (event_id, user["id"])
    ).fetchone()

    if not event:
        conn.close()
        return jsonify({"error": "イベントが見つかりません"}), 404

    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.execute("DELETE FROM event_participations WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "削除しました"})


@event_bp.route("/api/events/<int:event_id>/participate", methods=["POST"])
@login_required
def participate(event_id):
    user = get_current_user()
    data = request.get_json()
    response = data.get("response")  # 'accepted' or 'declined'

    if response not in ("accepted", "declined"):
        return jsonify({"error": "responseは'accepted'または'declined'を指定してください"}), 400

    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "イベントが見つかりません"}), 404

    conn.execute(
        """INSERT INTO event_participations (event_id, user_id, response)
           VALUES (?,?,?)
           ON CONFLICT(event_id, user_id) DO UPDATE SET response = excluded.response""",
        (event_id, user["id"], response)
    )

    # 主催者に通知
    status_text = "参加" if response == "accepted" else "不参加"
    conn.execute(
        """INSERT INTO notifications (user_id, type, message, related_id)
           VALUES (?,?,?,?)""",
        (event["user_id"], "participation_update",
         f"{user['display_name']}さんが「{event['title']}」に{status_text}を回答しました", event_id)
    )

    conn.commit()
    conn.close()
    return jsonify({"message": f"{status_text}で回答しました"})


@event_bp.route("/api/events/<int:event_id>/participants")
@login_required
def get_participants(event_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT u.display_name, ep.response, ep.created_at
           FROM event_participations ep
           JOIN users u ON ep.user_id = u.id
           WHERE ep.event_id = ?""",
        (event_id,)
    ).fetchall()
    conn.close()
    return jsonify({"participants": [dict(r) for r in rows]})
