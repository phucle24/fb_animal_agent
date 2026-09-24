import unittest
from app.product_comment_service import (
    PRODUCT_COMMENT_TEMPLATES,
    DONATE_COMMENT_TEMPLATES,
    build_product_comment,
    product_comment_line,
)


class TestProductCommentService(unittest.TestCase):
    def setUp(self):
        self.sample_product_with_sold = {
            "name": "Mô hình lắp ráp khủng long bạo chúa T-Rex",
            "raw_name": "Mô hình lắp ráp khủng long bạo chúa T-Rex 3D",
            "link": "https://s.shopee.vn/test12345",
            "sold": "1.2k",
        }
        self.sample_product_no_sold = {
            "name": "Balo thú cưng phi hành gia",
            "raw_name": "Balo thú cưng phi hành gia cao cấp",
            "link": "https://s.shopee.vn/test67890",
            "sold": "",
        }

    def test_product_comment_line_with_sold(self):
        line = product_comment_line(self.sample_product_with_sold)
        self.assertIn("Mô hình lắp ráp khủng long bạo chúa T-Rex", line)
        self.assertIn("với hơn 1.2k lượt bán", line)
        self.assertIn("👉 https://s.shopee.vn/test12345", line)

    def test_product_comment_line_no_sold(self):
        line = product_comment_line(self.sample_product_no_sold)
        self.assertIn("Balo thú cưng phi hành gia", line)
        self.assertNotIn("lượt bán", line)
        self.assertIn("👉 https://s.shopee.vn/test67890", line)

    def test_user_requested_phrases_in_templates(self):
        all_templates_lower = " ".join(PRODUCT_COMMENT_TEMPLATES).lower()
        self.assertIn("nếu như video này hay thì click ủng hộ mình với nhé", all_templates_lower)
        self.assertIn("thêm mắm thêm muối cho những video tiếp theo giúp mình nhé", all_templates_lower)
        self.assertIn("cứu bé ở đây với nhé", all_templates_lower)

    def test_build_product_comment_formatting(self):
        msg = build_product_comment(self.sample_product_with_sold, comment_index=1, seed=42)
        self.assertIn("Mô hình lắp ráp khủng long bạo chúa T-Rex", msg)
        self.assertIn("👉 https://s.shopee.vn/test12345", msg)
        self.assertTrue(len(msg.splitlines()) >= 2)

    def test_consecutive_comments_on_same_post_differ(self):
        for seed in (1, 2, 42, 100, 9999, "fb_test_reel_123"):
            comment1 = build_product_comment(self.sample_product_with_sold, comment_index=1, seed=seed)
            comment2 = build_product_comment(self.sample_product_no_sold, comment_index=2, seed=seed)
            prefix1 = comment1.splitlines()[0]
            prefix2 = comment2.splitlines()[0]
            self.assertNotEqual(prefix1, prefix2, f"Collision on seed={seed}")

    def test_backward_compatibility_call_without_seed(self):
        msg1 = build_product_comment(self.sample_product_with_sold, comment_index=1)
        msg2 = build_product_comment(self.sample_product_with_sold, comment_index=2)
        self.assertIn("👉 https://s.shopee.vn/test12345", msg1)
        self.assertIn("👉 https://s.shopee.vn/test12345", msg2)

    def test_donate_templates_have_user_ctas(self):
        donate_templates_lower = " ".join(DONATE_COMMENT_TEMPLATES).lower()
        self.assertIn("nếu như video này hay thì click ủng hộ mình với nhé", donate_templates_lower)
        self.assertIn("thêm mắm thêm muối cho những video tiếp theo giúp mình nhé", donate_templates_lower)
        self.assertIn("cứu bé ở đây với nhé", donate_templates_lower)

    def test_schedule_timing_aff_at_30m_and_donate_at_35m(self):
        from unittest.mock import patch
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.config import TIMEZONE
        from app.product_comment_service import schedule_product_comments_for_post

        tz = ZoneInfo(TIMEZONE)
        posted_at = datetime(2026, 9, 17, 10, 0, 0, tzinfo=tz)
        post = {
            "id": 101,
            "title": "Sư tử săn mồi",
            "caption": "Chúa sơn lâm đại chiến",
            "topic_type": "comparison_top5",
            "topic_payload": "{}",
            "final_image_path": "assets/final/101.mp4",
        }

        inserted_records = []

        def mock_insert(data):
            inserted_records.append(data)
            return True

        mock_products = [
            {"name": "Đồ chơi sư tử", "link": "https://shopee.vn/lion", "sold": "100"},
            {"name": "Mô hình hổ", "link": "https://shopee.vn/tiger", "sold": "200"},
        ]

        with patch("app.product_comment_service.pick_products_for_context", return_value=mock_products), \
             patch("app.product_comment_service.insert_product_comment", side_effect=mock_insert), \
             patch("app.product_comment_service.DONATE_COMMENT_URL", "https://zypage.com/gopmotchut"):

            count = schedule_product_comments_for_post(post, "fb_test_post_101", posted_at=posted_at)
            self.assertEqual(count, 3)

            # Record 1: Affiliate product 1 scheduled at 10:30 (30 mins after post)
            self.assertEqual(inserted_records[0]["comment_index"], 1)
            self.assertEqual(inserted_records[0]["scheduled_at"], "2026-09-17 10:30:00")
            self.assertEqual(inserted_records[0]["product_name"], "Đồ chơi sư tử")

            # Record 2: Affiliate product 2 scheduled at 10:32
            self.assertEqual(inserted_records[1]["comment_index"], 2)
            self.assertEqual(inserted_records[1]["scheduled_at"], "2026-09-17 10:32:00")
            self.assertEqual(inserted_records[1]["product_name"], "Mô hình hổ")

            # Record 3: Donate link scheduled at 10:35 (35 mins after post, 5 mins after aff link)
            self.assertEqual(inserted_records[2]["comment_index"], 3)
            self.assertEqual(inserted_records[2]["scheduled_at"], "2026-09-17 10:35:00")
            self.assertEqual(inserted_records[2]["product_name"], "Ủng hộ kênh")
            self.assertIn("https://zypage.com/gopmotchut", inserted_records[2]["message"])

    def test_schedule_product_comments_for_post_with_sqlite_row(self):
        import sqlite3
        from unittest.mock import patch
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.config import TIMEZONE
        from app.product_comment_service import schedule_product_comments_for_post

        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                title TEXT,
                caption TEXT,
                topic_type TEXT,
                topic_payload TEXT,
                final_image_path TEXT
            )"""
        )
        cur.execute(
            """INSERT INTO posts (id, title, caption, topic_type, topic_payload, final_image_path)
               VALUES (102, 'Báo gấm', 'Tốc độ xé gió', 'standard', '{}', 'assets/final/102.jpg')"""
        )
        row = cur.fetchone()

        tz = ZoneInfo(TIMEZONE)
        posted_at = datetime(2026, 9, 17, 10, 0, 0, tzinfo=tz)

        with patch("app.product_comment_service.pick_products_for_context", return_value=[]), \
             patch("app.product_comment_service.insert_product_comment", return_value=True), \
             patch("app.product_comment_service.DONATE_COMMENT_URL", "https://zypage.com/gopmotchut"):
            count = schedule_product_comments_for_post(row, "fb_test_post_102", posted_at=posted_at)
            self.assertEqual(count, 1)

    def test_schedule_recent_donate_comments_timing_and_order(self):
        from unittest.mock import patch
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.config import TIMEZONE
        from app.product_comment_service import schedule_recent_donate_comments

        tz = ZoneInfo(TIMEZONE)
        video_created = datetime(2026, 9, 17, 12, 0, 0, tzinfo=tz)
        scan_now = datetime(2026, 9, 17, 12, 10, 0, tzinfo=tz)

        mock_video_objects = [
            {
                "fb_post_id": "reel_video_999",
                "created_at": video_created,
                "source": "video_reels",
                "title": "Gấu bắc cực săn mồi",
                "caption": "Cuộc chiến sinh tồn của gấu tuyết",
            }
        ]

        mock_products = [
            {"name": "Gấu bông tuyết", "link": "https://shopee.vn/bear", "sold": "500"},
        ]

        with patch("app.product_comment_service.normalize_external_video_objects", return_value=mock_video_objects), \
             patch("app.product_comment_service.pick_products_for_context", return_value=mock_products), \
             patch("app.product_comment_service.DONATE_COMMENT_URL", "https://zypage.com/gopmotchut"):

            results = schedule_recent_donate_comments(now=scan_now, dry_run=True)
            self.assertEqual(len(results), 2)

            # First item: Affiliate link at 12:30 (30 minutes after created)
            self.assertEqual(results[0]["kind"], "product")
            self.assertEqual(results[0]["scheduled_at"], "2026-09-17 12:30:00")
            self.assertEqual(results[0]["product_name"], "Gấu bông tuyết")

            # Second item: Donate link at 12:35 (35 minutes after created, 5 minutes after aff)
            self.assertEqual(results[1]["kind"], "donate")
            self.assertEqual(results[1]["scheduled_at"], "2026-09-17 12:35:00")


if __name__ == "__main__":
    unittest.main()
