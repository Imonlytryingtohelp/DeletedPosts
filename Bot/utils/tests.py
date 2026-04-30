import unittest
import datetime as dt
from pathlib import Path
from .actions import (
    Flair,
    get_flair,
    string_to_dt,
    submission_is_older,
    parse_cmd_line_args,
)
from logger import Logger


class DummyPosts:
    def __init__(self, path):
        self.path = path


class TestActions(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_get_flair(self) -> None:
        solved = get_flair("Solved")
        self.assertEqual(solved, Flair.SOLVED)
        abandoned = get_flair('Abandoned')
        self.assertEqual(abandoned, Flair.ABANDONED)
        uknown = get_flair('Uknown')
        self.assertEqual(uknown, Flair.UKNOWN)
        uknown = get_flair('fsdafsd')
        self.assertEqual(uknown, Flair.UKNOWN)

    def test_string_to_dt(self) -> None:
        datetime = dt.datetime.now()
        string_dt = str(datetime)
        back_to_dt = string_to_dt(string_dt)
        self.assertEqual(datetime, back_to_dt)

    def test_submission_is_older(self) -> None:
        max_days = 7
        today = dt.datetime.now()

        post_made = today - dt.timedelta(days=3)
        result = submission_is_older(post_made.date(), max_days)
        self.assertFalse(result)

        post_made = today - dt.timedelta(days=max_days)
        result = submission_is_older(post_made.date(), max_days)
        self.assertFalse(result)

        post_made = today - dt.timedelta(days=(max_days + 1))
        result = submission_is_older(post_made.date(), max_days)
        self.assertTrue(result)

    def test_parse_cmd_line_args_reset_config_and_db(self) -> None:
        tmp = Path(__file__).parent / "tmp_test"
        tmp.mkdir(exist_ok=True)
        cfg_file = tmp / "config.py"
        # ensure file exists with junk content
        cfg_file.write_text("not important")
        db_file = tmp / "db.sqlite"
        db_file.write_text("x")
        posts = DummyPosts(db_file)
        logger = Logger(1)

        # reset_config should rewrite the config file
        result = parse_cmd_line_args(["prog", "reset_config"], logger, cfg_file, posts)
        self.assertTrue(result)
        self.assertTrue(cfg_file.exists())
        content = cfg_file.read_text()
        self.assertIn("client_id", content)

        # reset_db should remove the database file
        db_file.write_text("x")
        result = parse_cmd_line_args(["prog", "reset_db"], logger, cfg_file, posts)
        self.assertTrue(result)
        self.assertFalse(db_file.exists())
