import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.schedule_service import posting_slots_for_date, generate_future_schedule
from app.topic_bank import get_topic_by_index, ANATOMY_TOPICS, GENERAL_TOPIC_BANKS


class TestScheduleSlotsAndTopicRouting(unittest.TestCase):
    def test_posting_slots_times(self):
        # Every day should have 1 photo post at 07:05 morning
        for weekday in range(7):
            sample_day = date(2026, 9, 10 + weekday)
            slots = posting_slots_for_date(sample_day)
            self.assertEqual(len(slots), 1)
            self.assertEqual(slots[0], ("morning", 7, 5))

    def test_night_slot_returns_anatomy(self):
        # Night slot if queried returns anatomy_infographic
        for idx in range(min(5, len(ANATOMY_TOPICS))):
            topic = get_topic_by_index(idx, slot="night")
            self.assertEqual(topic["topic_type"], "anatomy_infographic")
            self.assertIn("labels", topic)

    def test_morning_slot_uses_morning_meme(self):
        # Morning slot is dedicated to Master Prompt V2.0 morning animal memes
        topic = get_topic_by_index(0, slot="morning")
        self.assertEqual(topic["topic_type"], "morning_meme")
        self.assertIn("animal", topic)
        self.assertIn("caption", topic)
        self.assertIn("image_prompt", topic)
        self.assertTrue(len(topic["caption"].split()) <= 16)
        self.assertIn("no text", topic["image_prompt"].lower())

    def test_morning_slot_day_of_week_routing(self):
        # Morning slot correctly maps each day of week (Mon-Sun) to theme
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo
        from app.config import TIMEZONE

        # Mon=2026-10-19 to Sun=2026-10-25
        expected_days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        with patch("app.morning_meme_service.generate_morning_meme_via_llm", return_value=None):
            for day_offset, expected_name in enumerate(expected_days):
                dt = datetime(2026, 10, 19 + day_offset, 7, 5, tzinfo=ZoneInfo(TIMEZONE))
                topic = get_topic_by_index(0, slot="morning", dt=dt)
                self.assertEqual(topic["topic_type"], "morning_meme")
                self.assertEqual(topic["day_of_week"], expected_name)

    def test_general_topic_banks_structure(self):
        # GENERAL_TOPIC_BANKS contains all topic types including anatomy_infographic
        bank_types = [t_type for t_type, _ in GENERAL_TOPIC_BANKS]
        self.assertIn("species_profile", bank_types)
        self.assertIn("anatomy_infographic", bank_types)
        self.assertIn("matchup_versus", bank_types)
        self.assertIn("one_story", bank_types)
        self.assertIn("myth_vs_fact", bank_types)

    def test_count_future_posts_exclude_topic_type(self):
        import sqlite3
        from unittest.mock import patch
        from app.db import count_future_posts

        def create_mock_conn():
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY,
                    scheduled_at TEXT,
                    status TEXT,
                    topic_type TEXT
                )
            """)
            cur.execute("INSERT INTO posts VALUES (1, '2026-10-18 07:05:00', 'READY', 'guess_quiz')")
            cur.execute("INSERT INTO posts VALUES (2, '2026-10-18 11:50:00', 'READY', 'reel')")
            cur.execute("INSERT INTO posts VALUES (3, '2026-10-18 20:15:00', 'READY', 'reel')")
            conn.commit()
            return conn

        with patch("app.db.get_conn", side_effect=create_mock_conn):
            # All future posts
            self.assertEqual(count_future_posts("2026-10-17 00:00:00"), 3)
            # Future posts excluding reels
            self.assertEqual(count_future_posts("2026-10-17 00:00:00", exclude_topic_type="reel"), 1)


if __name__ == "__main__":
    unittest.main()
