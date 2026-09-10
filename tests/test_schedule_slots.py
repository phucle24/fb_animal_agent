import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.schedule_service import posting_slots_for_date, generate_future_schedule
from app.topic_bank import get_topic_by_index, ANATOMY_TOPICS, GENERAL_TOPIC_BANKS


class TestScheduleSlotsAndTopicRouting(unittest.TestCase):
    def test_posting_slots_times(self):
        # Every day should have 10:00 morning and 22:00 night
        for weekday in range(7):
            sample_day = date(2026, 9, 10 + weekday)
            slots = posting_slots_for_date(sample_day)
            self.assertEqual(len(slots), 2)
            self.assertEqual(slots[0], ("morning", 10, 0))
            self.assertEqual(slots[1], ("night", 22, 0))

    def test_night_slot_returns_anatomy(self):
        # Night slot must always return anatomy_infographic
        for idx in range(min(5, len(ANATOMY_TOPICS))):
            topic = get_topic_by_index(idx, slot="night")
            self.assertEqual(topic["topic_type"], "anatomy_infographic")
            self.assertIn("labels", topic)

    def test_morning_slot_returns_general_and_not_anatomy(self):
        # Morning slot must rotate across general formats and never pick anatomy
        seen_types = set()
        for idx in range(12):
            topic = get_topic_by_index(idx, slot="morning")
            self.assertNotEqual(topic["topic_type"], "anatomy_infographic")
            seen_types.add(topic["topic_type"])

        # Should have rotated across multiple general types
        self.assertTrue(len(seen_types) >= 4)

    def test_general_topic_banks_structure(self):
        # GENERAL_TOPIC_BANKS should not contain anatomy_infographic
        bank_types = [t_type for t_type, _ in GENERAL_TOPIC_BANKS]
        self.assertNotIn("anatomy_infographic", bank_types)
        self.assertIn("matchup_versus", bank_types)
        self.assertIn("one_story", bank_types)
        self.assertIn("myth_vs_fact", bank_types)


if __name__ == "__main__":
    unittest.main()
