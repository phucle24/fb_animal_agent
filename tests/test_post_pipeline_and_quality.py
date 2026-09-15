import unittest
from app.post_service import (
    CAPTION_HASHTAGS,
    append_caption_hashtags,
    finalize_caption,
    normalize_caption_opening,
    normalize_generated_caption_text,
    remove_ai_disclaimer,
    replace_caption_cliches,
)
from app.product_comment_service import (
    pick_products_for_context,
    rank_products_for_context,
)


class TestPostPipelineAndQuality(unittest.TestCase):
    def test_caption_hashtags_spelling(self):
        # Must not contain old misspelled hashtags
        self.assertNotIn("topdongbat", CAPTION_HASHTAGS)
        self.assertNotIn("reivew", CAPTION_HASHTAGS)
        # Must contain correct hashtags
        self.assertIn("#topdongvat", CAPTION_HASHTAGS)
        self.assertIn("#reviewthegioidongvat", CAPTION_HASHTAGS)
        self.assertIn("#thegioimuonloai", CAPTION_HASHTAGS)

    def test_remove_ai_disclaimer(self):
        sample = "Báo hoa mai là thợ săn bậc thầy.\n\nẢnh minh họa AI."
        cleaned = remove_ai_disclaimer(sample)
        self.assertNotIn("Ảnh minh họa AI", cleaned)
        self.assertEqual(cleaned, "Báo hoa mai là thợ săn bậc thầy.")

        sample2 = "Đại bàng dũng mãnh.\nẢnh minh hoạ AI"
        cleaned2 = remove_ai_disclaimer(sample2)
        self.assertNotIn("Ảnh minh hoạ AI", cleaned2)

    def test_normalize_caption_opening(self):
        self.assertEqual(
            normalize_caption_opening("Bạn có biết? Báo săn là loài chạy nhanh nhất."),
            "Báo săn là loài chạy nhanh nhất.",
        )
        self.assertEqual(
            normalize_caption_opening("Trong thế giới động vật, cá voi xanh nặng tới 200 tấn."),
            "Cá voi xanh nặng tới 200 tấn.",
        )
        self.assertEqual(
            normalize_caption_opening("Thiên nhiên luôn ẩn chứa những điều kỳ diệu: mực nang đổi màu."),
            "Mực nang đổi màu.",
        )

    def test_replace_caption_cliches(self):
        text = "Đây là một khả năng đặc biệt rất thú vị khiến ai cũng vô cùng kinh ngạc."
        cleaned = replace_caption_cliches(text)
        self.assertNotIn("khả năng đặc biệt", cleaned)
        self.assertNotIn("vô cùng", cleaned)
        self.assertNotIn("khiến ai cũng", cleaned)

    def test_finalize_caption_appends_hashtags_cleanly(self):
        caption = "Cá mập trắng có cú đớp mạnh mẽ.\nBạn nghĩ sao về điều này?"
        final = finalize_caption(caption)
        self.assertTrue(final.endswith(CAPTION_HASHTAGS))
        # Ensure hashtags not duplicated if run twice
        final_twice = finalize_caption(final)
        self.assertEqual(final_twice.count(CAPTION_HASHTAGS), 1)

    def test_product_ranking_contextual_matching(self):
        sample_products = [
            {
                "name": "Balo thú cưng phi hành gia cho mèo",
                "raw_name": "Balo thú cưng phi hành gia cho mèo chó",
                "link": "https://s.shopee.vn/cat_pack",
                "sold": "10k",
                "sold_value": 10000,
                "categories": {"pet", "cat"},
                "match_tokens": {"balo", "thu", "cung", "meo"},
            },
            {
                "name": "Mô hình lắp ráp khủng long bạo chúa T-Rex",
                "raw_name": "Mô hình lắp ráp khủng long T-Rex 3D",
                "link": "https://s.shopee.vn/dino_toy",
                "sold": "5k",
                "sold_value": 5000,
                "categories": {"animal_toy"},
                "match_tokens": {"mo", "hinh", "lap", "rap", "khung", "long", "rex"},
            },
            {
                "name": "Quạt mini cầm tay",
                "raw_name": "Quạt mini cầm tay đa năng",
                "link": "https://s.shopee.vn/fan",
                "sold": "100k",
                "sold_value": 100000,
                "categories": set(),
                "match_tokens": {"quat", "mini"},
            },
        ]

        # Dino topic should rank dinosaur toy first despite fan having 100k sold
        ranked_dino = rank_products_for_context(
            sample_products,
            seed=1,
            title="Khủng long bạo chúa T-Rex săn mồi như thế nào?",
            caption="Hóa thạch khủng long cho thấy lực cắn khủng khiếp.",
        )
        self.assertEqual(ranked_dino[0][1]["name"], "Mô hình lắp ráp khủng long bạo chúa T-Rex")
        self.assertTrue(ranked_dino[0][0] > 0)

    def test_pick_products_for_context_fallback_and_no_duplicates(self):
        picked = pick_products_for_context(
            seed=42,
            count=3,
            title="Hổ Siberia đối đầu gấu xám",
            caption="Trận chiến giữa hai kẻ săn mồi thảo nguyên.",
        )
        # Should return products
        if picked:
            links = [p.get("link") for p in picked if p.get("link")]
            self.assertEqual(len(links), len(set(links)), "Duplicate product links found in picked products!")


if __name__ == "__main__":
    unittest.main()
