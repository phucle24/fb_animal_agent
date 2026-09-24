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

    def test_image_templates_no_visual_journalism_and_forbid_thu_bat(self):
        from app.post_service import (
            ANATOMY_MASTER_PROMPT_TEMPLATE,
            ENGAGEMENT_IMAGE_TEMPLATE,
            INFOGRAPHIC_IMAGE_TEMPLATE,
            MATCHUP_IMAGE_TEMPLATE,
            SINGLE_CARD_IMAGE_TEMPLATE,
            TEXT_DEDUP_RULES,
        )

        templates = [
            INFOGRAPHIC_IMAGE_TEMPLATE,
            SINGLE_CARD_IMAGE_TEMPLATE,
            MATCHUP_IMAGE_TEMPLATE,
            ENGAGEMENT_IMAGE_TEMPLATE,
            ANATOMY_MASTER_PROMPT_TEMPLATE,
        ]

        for t in templates:
            self.assertNotIn(
                "visual journalism poster",
                t.lower(),
                "Template must not contain 'visual journalism poster' which causes AI text leaks",
            )

        # TEXT_DEDUP_RULES must explicitly enforce zero English and forbid 'Thủ bạt'
        self.assertIn("STRICT ZERO ENGLISH TEXT", TEXT_DEDUP_RULES)
        self.assertIn("Thủ bạt", TEXT_DEDUP_RULES)
        self.assertIn("NO TOP HEADER BARS OR PILL TAGS", TEXT_DEDUP_RULES)

    def test_sanitize_scene_prompt(self):
        from app.prompt_safety import sanitize_scene_prompt

        bad_prompt = "a macro shot with visual journalism poster layout and rank list"
        self.assertEqual(sanitize_scene_prompt(bad_prompt), "")

        bad_thu_bat = "close up of animal, thủ bạt tag on top"
        self.assertEqual(sanitize_scene_prompt(bad_thu_bat), "")

        good_prompt = "a colorful sea mouse crawling on dark sand, macro lens, dramatic lighting"
        self.assertEqual(sanitize_scene_prompt(good_prompt), good_prompt)

    def test_enforce_prompt_language_and_safety(self):
        from app.prompt_safety import MODEL_RENDERED_TEXT_MARKER, enforce_prompt_language_and_safety

        leaked_prompt = f"{MODEL_RENDERED_TEXT_MARKER}\nCreate a visual journalism poster with wildlife."
        cleaned = enforce_prompt_language_and_safety(leaked_prompt)
        self.assertNotIn("visual journalism poster", cleaned.lower())
        self.assertIn("STRICT ZERO ENGLISH TEXT", cleaned)
        self.assertIn("STRICT NO 'THỦ BẠT'", cleaned)

    def test_prompt_builders_enforce_vietnamese_and_forbid_thu_bat(self):
        from app.post_service import (
            build_anatomy_image_prompt,
            build_engagement_image_prompt,
            build_model_rendered_infographic_prompt,
        )

        # 1. Engagement (myth_vs_fact)
        topic_engagement = {
            "topic_type": "myth_vs_fact",
            "subject_vi": "Lông Cầu Vồng Có Độc?",
            "subject_en": "Sea mouse iridescent bristles",
            "hook_vi": "Tưởng hiền, ai ngờ đầy độc",
            "main_fact_vi": "Lông dẫn sáng kiêm luôn kim độc",
            "twist_vi": "Gai độc tự vệ dưới đáy biển",
        }
        content_engagement = {
            "overlay_title": "LÔNG CẦU VỒNG CÓ ĐỘC?",
            "overlay_primary": "Tưởng hiền, ai ngờ đầy độc",
            "overlay_secondary": "LÔNG DẪN SÁNG KIÊM LUÔN KIM ĐỘC",
            "image_prompt": "a sea mouse on dark seabed with rainbow bristles",
        }
        engagement_prompt = build_engagement_image_prompt(topic_engagement, content_engagement)
        self.assertNotIn("visual journalism poster", engagement_prompt.lower())
        self.assertIn("STRICT ZERO ENGLISH TEXT", engagement_prompt)
        self.assertIn("Thủ bạt", engagement_prompt)

        # 2. Single card
        topic_single = {
            "topic_type": "single_card",
            "subject_vi": "Cá Mập Trắng",
            "subject_en": "Great white shark",
            "fact_value": "18000 N",
            "detail_vi": "lực cắn kinh hoàng",
        }
        content_single = {
            "overlay_title": "LỰC CẮN CÁ MẬP TRẮNG",
            "overlay_stat": "18.000 N",
            "overlay_hook": "Cú đớp nghiền nát con mồi",
            "image_prompt": "great white shark emerging from deep blue water",
        }
        single_prompt = build_model_rendered_infographic_prompt("", topic_single, content_single)
        self.assertNotIn("visual journalism poster", single_prompt.lower())
        self.assertIn("STRICT ZERO ENGLISH TEXT", single_prompt)
        self.assertIn("Thủ bạt", single_prompt)

        # 3. Top 5 comparison
        topic_top5 = {
            "topic_type": "comparison_top5",
            "subject_vi": "Top 5 Vua Tốc Độ",
            "subject_en": "Top 5 fastest animals",
            "items": [
                {"rank": 1, "name_vi": "Báo Săn", "name_en": "Cheetah", "stat": "110 km/h", "detail_vi": "chạy nước rút"},
                {"rank": 2, "name_vi": "Linh Dương", "name_en": "Pronghorn", "stat": "88 km/h", "detail_vi": "bền bỉ"},
                {"rank": 3, "name_vi": "Linh Dương Đầu Bò", "name_en": "Wildebeest", "stat": "80 km/h", "detail_vi": "băng đồng"},
                {"rank": 4, "name_vi": "Sư Tử", "name_en": "Lion", "stat": "74 km/h", "detail_vi": "mai phục"},
                {"rank": 5, "name_vi": "Chó Hoang Châu Phi", "name_en": "African wild dog", "stat": "70 km/h", "detail_vi": "săn bầy"},
            ],
        }
        content_top5 = {
            "overlay_subtitle": "TOP 5 ĐỘNG VẬT NHANH NHẤT",
            "image_prompt": "cheetah running full speed across savanna",
        }
        top5_prompt = build_model_rendered_infographic_prompt("", topic_top5, content_top5)
        self.assertNotIn("visual journalism poster", top5_prompt.lower())
        self.assertIn("STRICT ZERO ENGLISH TEXT", top5_prompt)
        self.assertIn("Thủ bạt", top5_prompt)

        # 4. Matchup versus
        topic_matchup = {
            "topic_type": "matchup_versus",
            "subject_vi": "Báo Đốm VS Báo Hoa Mai",
            "left": {"name_vi": "Báo Đốm", "name_en": "Jaguar", "weight": "100 kg", "bite_force": "1350 psi", "edge_vi": "lực hàm cực mạnh"},
            "right": {"name_vi": "Báo Hoa Mai", "name_en": "Leopard", "weight": "70 kg", "bite_force": "500 psi", "edge_vi": "leo cây điêu luyện"},
        }
        content_matchup = {
            "overlay_title": "BÁO ĐỐM VS BÁO HOA MAI",
            "image_prompt": "jaguar and leopard in split screen",
        }
        matchup_prompt = build_model_rendered_infographic_prompt("", topic_matchup, content_matchup)
        self.assertNotIn("visual journalism poster", matchup_prompt.lower())
        self.assertIn("STRICT ZERO ENGLISH TEXT", matchup_prompt)
        self.assertIn("Thủ bạt", matchup_prompt)

        # 5. Anatomy infographic
        topic_anatomy = {
            "topic_type": "anatomy_infographic",
            "subject_vi": "Cấu Tạo Ong Mật",
            "animal_vi": "Ong mật",
            "animal_en": "Honey bee",
            "hook_vi": "Cỗ máy thụ phấn kỳ diệu",
            "main_fact_vi": "Cấu tạo túi phấn đặc biệt",
            "labels": [
                {"label_vi": "Mắt kép", "target_en": "compound eye", "description_vi": "nhìn góc rộng"},
                {"label_vi": "Túi phấn", "target_en": "pollen basket", "description_vi": "giữ hạt phấn"},
            ],
        }
        content_anatomy = {
            "title": "Cấu Tạo Ong Mật",
            "caption": "Ong mật có cấu tạo tuyệt đẹp.",
            "image_prompt": "honey bee macro cutaway specimen",
        }
        anatomy_prompt = build_anatomy_image_prompt(topic_anatomy, content_anatomy)
        self.assertNotIn("visual journalism poster", anatomy_prompt.lower())
        self.assertIn("Thủ bạt", anatomy_prompt)
        self.assertIn("English words", anatomy_prompt)


if __name__ == "__main__":
    unittest.main()

