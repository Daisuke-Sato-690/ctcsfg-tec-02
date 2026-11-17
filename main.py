import feedparser
from datetime import datetime, timezone, timedelta, date

RSS_URL = "https://www.snowflake.com/feed/"

feed = feedparser.parse(RSS_URL)

# 日本時間（UTC+9）
JST = timezone(timedelta(hours=9))

# 動作確認用の日付
target_date = date(2026, 11, 12)

for entry in feed.entries:

    published = entry.get("published_parsed")

    if published is None:
        continue

    # 公開日時をUTCとして取得
    published_utc = datetime(
        *published[:6],
        tzinfo=timezone.utc
    )

    # 日本時間に変換
    published_jst = published_utc.astimezone(JST)

    # 指定日の記事だけ表示
    if published_jst.date() == target_date:
        print("タイトル:", entry.get("title"))
        print("公開日時:", published_jst)
        print("URL:", entry.get("link"))
        print("----------")