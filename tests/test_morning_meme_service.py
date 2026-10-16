import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import TIMEZONE
from app.morning_meme_service import (
    MORNING_MEME_BANK,
    WEEKDAY_INFO,
    get_morning_meme_topic,
    get_weekday_info,
)
from app.post_service import build_post_payload


class TestMorningMemeService(unittest.TestCase):
    def test_curated_bank_size_and_fields(self):
        # Must have at least 21 memes (3 for each day of week)
        self.assertGreaterEqual(len(MORNING_MEME_BANK), 21)
        for meme in MORNING_MEME_BANK:
            self.assertEqual(meme["topic_type"], "morning_meme")
            self.assertIn("concept", meme)
            self.assertIn("day_of_week", meme)
            self.assertIn("animal", meme)
            self.assertIn("caption", meme)
            self.assertIn("image_prompt", meme)
            self.assertIn("hashtags", meme)
            self.assertGreaterEqual(meme.get("score", 0), 80)

            # Caption constraint: <= 15 words
            words = meme["caption"].split()
            self.assertLessEqual(len(words), 16, f"Caption too long: {meme['caption']}")

            # Strict no text constraint in image prompt
            prompt_lower = meme["image_prompt"].lower()
            self.assertTrue(
                "no text" in prompt_lower or "zero text" in prompt_lower,
                f"Prompt missing zero-text constraint: {meme['image_prompt']}",
            )

    def test_weekday_info_mapping(self):
        # 0 = Thứ Hai, 6 = Chủ Nhật
        self.assertEqual(len(WEEKDAY_INFO), 7)
        self.assertEqual(WEEKDAY_INFO[0]["name"], "Thứ Hai")
        self.assertEqual(WEEKDAY_INFO[5]["name"], "Thứ Bảy")
        self.assertEqual(WEEKDAY_INFO[6]["name"], "Chủ Nhật")

    def test_get_morning_meme_topic_weekday_dispatch(self):
        tz = ZoneInfo(TIMEZONE)
        # Saturday 2026-10-17
        sat_dt = datetime(2026, 10, 17, 7, 5, tzinfo=tz)
        topic = get_morning_meme_topic(sat_dt)
        self.assertEqual(topic["topic_type"], "morning_meme")
        self.assertEqual(topic["day_of_week"], "Thứ Bảy")
        self.assertIn("QuyenDuocSongCham", " ".join(topic.get("hashtags", [])))

    def test_build_post_payload_for_morning_meme(self):
        meme = MORNING_MEME_BANK[0]
        payload = build_post_payload(meme, "2026-10-19 07:05:00", "morning")
        self.assertEqual(payload["topic_type"], "morning_meme")
        self.assertEqual(payload["slot"], "morning")
        self.assertEqual(payload["status"], "READY")
        self.assertIn("#TheGioiMuonLoai", payload["caption"])
        self.assertIn("#KiepTrauNgua", payload["caption"])
        self.assertIsNone(payload["overlay_title"])
        self.assertIsNone(payload["overlay_subtitle"])


if __name__ == "__main__":
    unittest.main()
