import unittest
from datetime import date
from unittest.mock import patch, MagicMock

from app.google_drive_service import extract_file_number
from app.reel_service import (
    reel_slots_for_date,
    generate_future_reel_schedule,
    get_existing_reel_keys,
)
from app.facebook_service import publish_reel


class TestReelService(unittest.TestCase):
    def test_extract_file_number(self):
        self.assertEqual(extract_file_number("066_The Gioi Muon Loai_vi.mp4"), (66, "066"))
        self.assertEqual(extract_file_number("070_The Gioi Muon Loai.txt"), (70, "070"))
        self.assertEqual(extract_file_number("123.mp4"), (123, "123"))
        self.assertIsNone(extract_file_number("abc_test.mp4"))

    def test_reel_slots_times(self):
        # 12:15 and 20:00
        slots = reel_slots_for_date(date(2026, 10, 8))
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0], ("reel_1", 12, 15))
        self.assertEqual(slots[1], ("reel_2", 20, 0))

    def test_generate_future_reel_schedule(self):
        slots = generate_future_reel_schedule(target_slots=6, lookahead_days=5)
        self.assertEqual(len(slots), 6)
        # Check slot names alternate reel_1 and reel_2
        slot_names = [s[0] for s in slots]
        for i in range(len(slot_names) - 1):
            if slot_names[i] == "reel_1":
                self.assertEqual(slot_names[i + 1], "reel_2")
            else:
                self.assertEqual(slot_names[i + 1], "reel_1")

    def test_publish_reel_validates_file_exists(self):
        with self.assertRaises(FileNotFoundError):
            publish_reel("/nonexistent/video.mp4", "caption")


if __name__ == "__main__":
    unittest.main()
