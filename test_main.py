import contextlib
import importlib
import io
import sys
import types
import unittest
from datetime import date, datetime
from unittest import mock

RSS_URL = "https://www.snowflake.com/feed/"


def load_main(entries=()):
    """feedparser を偽物に差し替えて main を import し、(main, parse モック) を返す。

    ネットワークも feedparser のインストールも不要。
    """
    fake = types.ModuleType("feedparser")
    fake.parse = mock.Mock(return_value=types.SimpleNamespace(entries=list(entries)))
    with mock.patch.dict(sys.modules, {"feedparser": fake}):
        sys.modules.pop("main", None)
        main = importlib.import_module("main")
    sys.modules.pop("main", None)
    return main, fake.parse


def entry(title, link, published_parsed):
    """published_parsed は UTC の (年, 月, 日, 時, 分, 秒)。"""
    return {"title": title, "link": link, "published_parsed": published_parsed}


def run(entries, argv):
    """main.main(argv) を実行して標準出力を返す。"""
    main, parse = load_main(entries)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main.main(argv)
    return buf.getvalue(), parse


class TestImport(unittest.TestCase):
    def test_import_has_no_side_effects(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            _, parse = load_main([entry("a", "u", (2026, 11, 12, 0, 0, 0))])
        self.assertEqual(out.getvalue(), "")
        parse.assert_not_called()


class TestParseDate(unittest.TestCase):
    def setUp(self):
        self.main, _ = load_main()

    def test_valid(self):
        self.assertEqual(self.main.parse_date("2026-11-12"), date(2026, 11, 12))

    def test_invalid(self):
        import argparse

        for bad in ["2026/11/12", "20261112", "abc", "2026-13-01", ""]:
            with self.subTest(bad=bad):
                with self.assertRaises(argparse.ArgumentTypeError):
                    self.main.parse_date(bad)


class TestResolveRange(unittest.TestCase):
    def setUp(self):
        self.main, _ = load_main()
        self.today = date(2026, 11, 20)

    def test_defaults_to_today(self):
        self.assertEqual(
            self.main.resolve_range(None, None, self.today), (self.today, self.today)
        )

    def test_from_only_is_single_day(self):
        d = date(2026, 11, 12)
        self.assertEqual(self.main.resolve_range(d, None, self.today), (d, d))

    def test_range(self):
        a, b = date(2026, 11, 10), date(2026, 11, 12)
        self.assertEqual(self.main.resolve_range(a, b, self.today), (a, b))

    def test_same_day_range_ok(self):
        d = date(2026, 11, 12)
        self.assertEqual(self.main.resolve_range(d, d, self.today), (d, d))

    def test_to_only_is_error(self):
        with self.assertRaises(ValueError):
            self.main.resolve_range(None, date(2026, 11, 12), self.today)

    def test_reversed_range_is_error(self):
        with self.assertRaises(ValueError):
            self.main.resolve_range(
                date(2026, 11, 12), date(2026, 11, 10), self.today
            )


class TestToJst(unittest.TestCase):
    def test_converts_utc_to_jst(self):
        main, _ = load_main()
        result = main.to_jst((2026, 11, 11, 15, 30, 0))
        self.assertEqual(result.date(), date(2026, 11, 12))
        self.assertEqual((result.hour, result.minute), (0, 30))
        self.assertEqual(result.utcoffset().total_seconds(), 9 * 3600)


class TestMainOutput(unittest.TestCase):
    def test_fetches_expected_feed_url(self):
        _, parse = run([], ["--from", "2026-11-12"])
        parse.assert_called_once_with(RSS_URL)

    def test_empty_feed_prints_nothing(self):
        out, _ = run([], ["--from", "2026-11-12"])
        self.assertEqual(out, "")

    def test_single_day_output_format(self):
        out, _ = run(
            [entry("対象記事", "https://example.com/a", (2026, 11, 12, 3, 0, 0))],
            ["--from", "2026-11-12"],
        )
        self.assertEqual(
            out,
            "タイトル: 対象記事\n"
            "公開日時: 2026-11-12 12:00:00+09:00\n"
            "URL: https://example.com/a\n"
            "----------\n",
        )

    def test_single_day_skips_other_dates(self):
        out, _ = run(
            [
                entry("前日", "u1", (2026, 11, 11, 3, 0, 0)),
                entry("翌日", "u2", (2026, 11, 13, 3, 0, 0)),
            ],
            ["--from", "2026-11-12"],
        )
        self.assertEqual(out, "")

    def test_range_is_inclusive_on_both_ends(self):
        out, _ = run(
            [
                entry("範囲前", "u0", (2026, 11, 9, 3, 0, 0)),
                entry("開始日", "u1", (2026, 11, 10, 3, 0, 0)),
                entry("中間", "u2", (2026, 11, 11, 3, 0, 0)),
                entry("終了日", "u3", (2026, 11, 12, 3, 0, 0)),
                entry("範囲後", "u4", (2026, 11, 13, 3, 0, 0)),
            ],
            ["--from", "2026-11-10", "--to", "2026-11-12"],
        )
        for title in ["開始日", "中間", "終了日"]:
            self.assertIn(f"タイトル: {title}", out)
        for title in ["範囲前", "範囲後"]:
            self.assertNotIn(title, out)

    def test_range_boundaries_use_jst(self):
        # UTC 11/9 15:00 = JST 11/10 00:00 -> 開始日として含まれる
        # UTC 11/12 15:00 = JST 11/13 00:00 -> 終了日の翌日なので含まれない
        out, _ = run(
            [
                entry("JST開始日0時", "u1", (2026, 11, 9, 15, 0, 0)),
                entry("JST終了翌日0時", "u2", (2026, 11, 12, 15, 0, 0)),
            ],
            ["--from", "2026-11-10", "--to", "2026-11-12"],
        )
        self.assertIn("JST開始日0時", out)
        self.assertNotIn("JST終了翌日0時", out)

    def test_keeps_feed_order(self):
        out, _ = run(
            [
                entry("1件目", "u1", (2026, 11, 12, 0, 0, 0)),
                entry("2件目", "u2", (2026, 11, 11, 0, 0, 0)),
            ],
            ["--from", "2026-11-11", "--to", "2026-11-12"],
        )
        self.assertLess(out.index("1件目"), out.index("2件目"))

    def test_skips_entries_without_published_date(self):
        out, _ = run(
            [
                {"title": "日付なし", "link": "u1"},
                entry("日付None", "u2", None),
            ],
            ["--from", "2026-11-12"],
        )
        self.assertEqual(out, "")

    def test_missing_title_and_link_print_none(self):
        out, _ = run(
            [{"published_parsed": (2026, 11, 12, 3, 0, 0)}], ["--from", "2026-11-12"]
        )
        self.assertIn("タイトル: None", out)
        self.assertIn("URL: None", out)

    def test_no_args_uses_today_jst(self):
        main, _ = load_main(
            [
                entry("今日", "u1", (2026, 11, 20, 3, 0, 0)),
                entry("昨日", "u2", (2026, 11, 19, 3, 0, 0)),
            ]
        )
        fixed_now = datetime(2026, 11, 20, 12, 0, tzinfo=main.JST)
        buf = io.StringIO()
        with mock.patch.object(main, "datetime") as dt:
            dt.now.return_value = fixed_now
            dt.side_effect = datetime
            with contextlib.redirect_stdout(buf):
                main.main([])
        self.assertIn("タイトル: 今日", buf.getvalue())
        self.assertNotIn("昨日", buf.getvalue())


class TestMainErrors(unittest.TestCase):
    def assert_exits_with_error(self, argv):
        main, _ = load_main()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                main.main(argv)
        self.assertEqual(cm.exception.code, 2)
        return err.getvalue()

    def test_invalid_date_format(self):
        msg = self.assert_exits_with_error(["--from", "2026/11/12"])
        self.assertIn("YYYY-MM-DD", msg)

    def test_to_without_from(self):
        msg = self.assert_exits_with_error(["--to", "2026-11-12"])
        self.assertIn("--from", msg)

    def test_reversed_range(self):
        self.assert_exits_with_error(["--from", "2026-11-12", "--to", "2026-11-10"])


if __name__ == "__main__":
    unittest.main()
