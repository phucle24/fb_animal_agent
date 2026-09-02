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


if __name__ == "__main__":
    unittest.main()
