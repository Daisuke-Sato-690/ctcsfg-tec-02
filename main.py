import argparse
from datetime import datetime, timezone, timedelta

import feedparser

RSS_URL = "https://www.snowflake.com/feed/"

# 日本時間（UTC+9）
JST = timezone(timedelta(hours=9))


def parse_date(value):
    """YYYY-MM-DD 形式の文字列を date に変換する。"""
    try:
        # date.fromisoformat は Python 3.11 以降 20261112 も受け付けるため strptime を使う
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"日付は YYYY-MM-DD 形式で指定してください: {value}"
        )


def resolve_range(date_from, date_to, today):
    """表示対象の期間 (開始日, 終了日) を決める。両端を含む。

    - 両方省略: today の1日分
    - date_from のみ: その1日分
    - 両方指定: その期間
    - date_to のみ: 開始日が決まらないのでエラー
    """
    if date_from is None and date_to is not None:
        raise ValueError("--to を指定する場合は --from も指定してください")
    if date_from is None:
        date_from = today
    if date_to is None:
        date_to = date_from
    if date_from > date_to:
        raise ValueError("--from は --to 以前の日付を指定してください")
    return date_from, date_to


def to_jst(published_parsed):
    """feedparser の published_parsed(UTC) を日本時間の datetime に変換する。"""
    published_utc = datetime(*published_parsed[:6], tzinfo=timezone.utc)
    return published_utc.astimezone(JST)


def print_entries(date_from, date_to):
    """期間内(JST 基準・両端を含む)に公開された記事を表示する。"""
    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries:
        published = entry.get("published_parsed")

        if published is None:
            continue

        published_jst = to_jst(published)

        if date_from <= published_jst.date() <= date_to:
            print("タイトル:", entry.get("title"))
            print("公開日時:", published_jst)
            print("URL:", entry.get("link"))
            print("----------")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Snowflake のブログ記事を、公開日(日本時間)で絞り込んで表示する"
    )
    parser.add_argument(
        "--from",
        dest="date_from",
        type=parse_date,
        help="開始日 YYYY-MM-DD(--to 省略時はこの1日のみ)。省略時は今日",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        type=parse_date,
        help="終了日 YYYY-MM-DD(この日を含む)。--from と一緒に指定する",
    )
    args = parser.parse_args(argv)

    today = datetime.now(JST).date()
    try:
        date_from, date_to = resolve_range(args.date_from, args.date_to, today)
    except ValueError as e:
        parser.error(str(e))

    print_entries(date_from, date_to)


if __name__ == "__main__":
    main()
