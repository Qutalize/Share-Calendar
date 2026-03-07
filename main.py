"""
main.py
-------
アプリ全体の統合・エントリポイント。
各サービスを組み合わせて、CLI から主要機能を一通り確認できる。

実際の Web アプリ化には FastAPI / Flask などのフレームワークと
このモジュールを組み合わせる。

モジュール構成:
    models.py               … データクラス定義
    data.py                 … デモデータ・ユーティリティ
    auth.py                 … ログイン・セッション管理
    calendar_service.py     … カレンダー表示ロジック
    event_service.py        … 予定管理・ダブルブッキング判定
    friend_service.py       … フレンド管理・検索
    notification_service.py … 通知生成・既読管理
    main.py                 … 統合・エントリポイント（本ファイル）
"""

from auth import AuthService
from calendar_service import CalendarService
from event_service import EventService
from friend_service import FriendService
from notification_service import NotificationService
from data import DEMO_EVENTS, FRIENDS_DATA


# ----------------------------------------------------------------
# アプリ本体
# ----------------------------------------------------------------

class SyncedApp:
    """
    Synced アプリの全サービスを束ねるファサードクラス。
    UI レイヤー（Web フレームワーク等）はこのクラスを通じて
    各機能を呼び出す。
    """

    def __init__(self) -> None:
        self.auth          = AuthService()
        self.calendar      = CalendarService()
        self.events        = EventService(DEMO_EVENTS)
        self.friends       = FriendService(FRIENDS_DATA)
        self.notifications = NotificationService()

    # ----------------------------------------------------------------
    # ログイン
    # ----------------------------------------------------------------

    def login(self, user_id: str) -> None:
        user = self.auth.login_by_id(user_id)
        print(f"✅ ログイン: {user.name} ({user.id})")

    def logout(self) -> None:
        self.auth.logout()
        print("👋 ログアウトしました")

    # ----------------------------------------------------------------
    # カレンダー表示
    # ----------------------------------------------------------------

    def show_calendar(self, year: int, month: int) -> None:
        user = self.auth.require_login()
        friend_ids = self.friends.get_friend_ids(user.id)

        print(f"\n📅 {self.calendar.format_month_label(year, month)}")
        print("日 月 火 水 木 金 土")
        for week in self.calendar.get_month_grid(year, month):
            row = [str(d).rjust(2) if d else "  " for d in week]
            # イベントがある日に ● を付ける
            marked = []
            for i, d in enumerate(week):
                if d is None:
                    marked.append("  ")
                else:
                    date_str = f"{year}-{month:02d}-{d:02d}"
                    has = self.calendar.has_event_on_date(
                        self.events.events, date_str, user, friend_ids
                    )
                    marked.append(f"{d:2d}" + ("●" if has else " "))
            print(" ".join(marked))

    # ----------------------------------------------------------------
    # 予定表示
    # ----------------------------------------------------------------

    def show_events_on_date(self, date_str: str) -> None:
        user = self.auth.require_login()
        friend_ids = self.friends.get_friend_ids(user.id)
        evts = self.calendar.get_events_on_date(
            self.events.events, date_str, user, friend_ids
        )
        print(f"\n📆 {date_str} の予定 ({len(evts)}件)")
        for e in evts:
            travel = f" 🚃{e.travel_minutes}分" if e.travel_minutes else ""
            counts = self.events.count_responses(e)
            print(
                f"  {e.start_time}-{e.end_time} 【{e.title}】 "
                f"📍{e.location}{travel}"
                f"  ✓{counts['yes']} ✗{counts['no']} ?{counts['pending']}"
            )

    def show_upcoming(self) -> None:
        user = self.auth.require_login()
        friend_ids = self.friends.get_friend_ids(user.id)
        evts = self.calendar.get_upcoming_events(
            self.events.events, user, friend_ids
        )
        print(f"\n🔮 今後の予定 ({len(evts)}件)")
        for e in evts:
            print(f"  {e.date} {e.start_time}-{e.end_time} {e.title}")

    # ----------------------------------------------------------------
    # 予定追加
    # ----------------------------------------------------------------

    def add_event(
        self,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        location: str = "",
        description: str = "",
        travel_minutes: int | None = None,
        invite_ids: list[str] | None = None,
        force: bool = False,
    ) -> None:
        user = self.auth.require_login()
        evt, conflicts = self.events.add_event(
            title=title,
            date=date,
            start_time=start_time,
            end_time=end_time,
            creator=user,
            location=location,
            description=description,
            travel_minutes=travel_minutes,
            invite_user_ids=invite_ids,
            force=force,
        )

        if conflicts and not force:
            print("⚠️  ダブルブッキングの可能性があります:")
            for c in conflicts:
                print(f"   「{c.title}」({c.start_time}-{c.end_time}) と重複")
            print("   force=True で強制追加できます")
        else:
            print(f"✅ 予定を追加しました: {evt.title} ({evt.date} {evt.start_time}-{evt.end_time})")
            if conflicts:
                print(f"   ⚠️  {len(conflicts)}件の重複がありますが強制追加しました")

    # ----------------------------------------------------------------
    # 参加可否回答
    # ----------------------------------------------------------------

    def respond(self, event_id: str, response: str) -> None:
        user = self.auth.require_login()
        evt = self.events.respond_to_event(event_id, user, response)
        label = {"yes": "✓ 参加", "no": "✗ 不参加", "pending": "? 未回答"}[response]
        print(f"{label} と回答しました: 「{evt.title}」")
        counts = self.events.count_responses(evt)
        print(f"  現在: ✓{counts['yes']} ✗{counts['no']} ?{counts['pending']}")

    # ----------------------------------------------------------------
    # フレンド管理
    # ----------------------------------------------------------------

    def show_friends(self) -> None:
        user = self.auth.require_login()
        friends = self.friends.get_friends(user.id)
        print(f"\n👥 {user.name} のフレンド ({len(friends)}人)")
        for f in friends:
            print(f"  {f.id}: {f.name}")

    def add_friend(self, query: str) -> None:
        user = self.auth.require_login()
        target = self.friends.search_user(query)
        if target is None:
            print(f"❌ ユーザーが見つかりません: {query!r}")
            return
        try:
            added = self.friends.add_friend(user.id, target.id)
            print(f"✅ フレンドに追加しました: {added.name}")
        except ValueError as e:
            print(f"❌ {e}")

    # ----------------------------------------------------------------
    # 通知
    # ----------------------------------------------------------------

    def show_notifications(self) -> None:
        user = self.auth.require_login()
        notifs = self.notifications.build_notifications(
            self.events.events, user
        )
        unread = self.notifications.unread_count(notifs)
        print(f"\n🔔 通知 ({len(notifs)}件, 未読:{unread}件)")
        for n in notifs:
            read_mark = "  " if self.notifications.is_read(n.id) else "🆕"
            print(f"  {read_mark} [{n.date} {n.time}] {n.message}")


# ----------------------------------------------------------------
# CLI デモ
# ----------------------------------------------------------------

def main() -> None:
    app = SyncedApp()

    print("=" * 60)
    print("  Synced — 予定調整アプリ デモ")
    print("=" * 60)

    # 1. ログイン
    app.login("USR001")

    # 2. カレンダー表示
    app.show_calendar(2026, 3)

    # 3. 特定日の予定
    app.show_events_on_date("2026-03-10")

    # 4. 今後の予定
    app.show_upcoming()

    # 5. ダブルブッキングのある予定を追加（警告）
    print("\n--- ダブルブッキングテスト ---")
    app.add_event(
        title="別件MTG",
        date="2026-03-10",
        start_time="10:30",
        end_time="11:30",
        location="オンライン",
    )

    # 6. 強制追加
    app.add_event(
        title="別件MTG（強制）",
        date="2026-03-10",
        start_time="10:30",
        end_time="11:30",
        location="オンライン",
        force=True,
    )

    # 7. 参加可否回答
    print("\n--- 参加回答テスト ---")
    app.respond("EVT001", "yes")
    app.respond("EVT002", "no")

    # 8. フレンド管理
    print("\n--- フレンド管理テスト ---")
    app.show_friends()
    app.add_friend("USR002")       # すでにフレンド
    app.login("USR002")
    app.add_friend("USR004")       # 新規追加

    # 9. 通知
    app.login("USR001")
    app.show_notifications()


if __name__ == "__main__":
    main()
