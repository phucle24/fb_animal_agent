import unittest
from app.topic_bank import SPECIES_PROFILE_TOPICS, GENERAL_TOPIC_BANKS, get_topic_by_index
from app.post_service import (
    build_post_payload,
    build_species_profile_image_prompt,
    build_species_profile_caption,
    MODEL_RENDERED_TOPIC_TYPES,
)
from app.generated_topic_service import validate_generated_topic


class TestSpeciesProfileTopic(unittest.TestCase):
    def test_species_profile_topics_bank(self):
        self.assertGreaterEqual(len(SPECIES_PROFILE_TOPICS), 8)
        broadbill = SPECIES_PROFILE_TOPICS[0]
        self.assertEqual(broadbill["topic_key"], "black_and_red_broadbill_profile")
        self.assertEqual(broadbill["animal_vi"], "Chim mỏ rộng đen đỏ")
        self.assertEqual(broadbill["scientific_name"], "Cymbirhynchus macrorhynchos")

        for key in ("scientific_box", "group_box", "size_box", "habitat_box", "diet_box", "highlights_box"):
            self.assertIn(key, broadbill)

        self.assertEqual(broadbill["scientific_box"]["title"], "TÊN KHOA HỌC")
        self.assertEqual(broadbill["group_box"]["title"], "NHÓM")
        self.assertEqual(broadbill["size_box"]["title"], "KÍCH THƯỚC")
        self.assertEqual(broadbill["habitat_box"]["title"], "MÔI TRƯỜNG SỐNG")
        self.assertEqual(broadbill["diet_box"]["title"], "THỨC ĂN")
        self.assertEqual(broadbill["highlights_box"]["title"], "ĐẶC ĐIỂM NỔI BẬT")
        self.assertGreaterEqual(len(broadbill["highlights_box"]["bullets"]), 3)

    def test_species_profile_image_prompt_replaces_old_text(self):
        topic = SPECIES_PROFILE_TOPICS[0]
        content = {
            "title": "ĐÂY LÀ CHIM MỎ RỘNG ĐEN ĐỎ – THẾ GIỚI MUÔN LOÀI",
            "caption_intro": topic["summary_vi"],
            "image_prompt": topic["hero_prompt_en"],
        }
        prompt = build_species_profile_image_prompt(topic, content)

        # 1. Must replace 'KIẾN THỨC ĐỘNG VẬT' with 'THẾ GIỚI MUÔN LOÀI'
        self.assertIn("THẾ GIỚI MUÔN LOÀI", prompt)
        self.assertNotIn("KIẾN THỨC ĐỘNG VẬT", prompt)

        # 2. Must contain all 6 info boxes
        self.assertIn("TÊN KHOA HỌC", prompt)
        self.assertIn("NHÓM", prompt)
        self.assertIn("KÍCH THƯỚC", prompt)
        self.assertIn("MÔI TRƯỜNG SỐNG", prompt)
        self.assertIn("THỨC ĂN", prompt)
        self.assertIn("ĐẶC ĐIỂM NỔI BẬT", prompt)

        # 3. Must contain scientific Latin name & animal name
        self.assertIn("Cymbirhynchus macrorhynchos", prompt)
        self.assertIn("CHIM MỎ RỘNG ĐEN ĐỎ", prompt)
        self.assertIn("ĐÂY LÀ", prompt)

        # 4. Strict text rules
        self.assertIn("STRICT ZERO ENGLISH TEXT", prompt)
        self.assertIn("STRICT NO 'THỦ BẠT'", prompt)

    def test_species_profile_caption(self):
        topic = SPECIES_PROFILE_TOPICS[0]
        content = {
            "title": "ĐÂY LÀ CHIM MỎ RỘNG ĐEN ĐỎ – THẾ GIỚI MUÔN LOÀI",
            "caption_intro": topic["summary_vi"],
            "image_prompt": topic["hero_prompt_en"],
        }
        caption = build_species_profile_caption(topic, content)

        self.assertIn("ĐÂY LÀ CHIM MỎ RỘNG ĐEN ĐỎ – THẾ GIỚI MUÔN LOÀI", caption)
        self.assertIn("HỒ SƠ LOÀI (THẾ GIỚI MUÔN LOÀI):", caption)
        self.assertIn("Tên khoa học: Cymbirhynchus macrorhynchos", caption)
        self.assertIn("Nhóm / Phân loại:", caption)
        self.assertIn("Kích thước:", caption)
        self.assertIn("Môi trường sống:", caption)
        self.assertIn("Thức ăn:", caption)
        self.assertIn("Đặc điểm nổi bật:", caption)
        self.assertIn("#thegioimuonloai", caption)
        self.assertNotIn("Ảnh minh họa AI", caption)

    def test_species_profile_in_model_rendered_types(self):
        self.assertIn("species_profile", MODEL_RENDERED_TOPIC_TYPES)

    def test_species_profile_in_general_banks(self):
        bank_names = [name for name, _ in GENERAL_TOPIC_BANKS]
        self.assertIn("species_profile", bank_names)

    def test_build_post_payload(self):
        topic = SPECIES_PROFILE_TOPICS[0]
        payload = build_post_payload(topic, "2026-10-04 10:00:00", "morning")
        self.assertEqual(payload["topic_type"], "species_profile")
        self.assertEqual(payload["topic_key"], "black_and_red_broadbill_profile")
        self.assertEqual(payload["status"], "READY")
        self.assertIn("THẾ GIỚI MUÔN LOÀI", payload["image_prompt"])
        self.assertNotIn("KIẾN THỨC ĐỘNG VẬT", payload["image_prompt"])

    def test_validate_generated_topic(self):
        topic = {
            "topic_type": "species_profile",
            "topic_key": "test_species_profile",
            "subject_vi": "Chim bói cá",
            "subject_en": "Common kingfisher",
            "animal_vi": "Chim bói cá",
            "animal_en": "Common kingfisher",
            "scientific_name": "Alcedo atthis",
            "summary_vi": "Chim bói cá là loài chim nhỏ với bộ lông lam cam rực rỡ, lao nhanh như tên bắn bắt cá.",
            "scientific_box": {"title": "TÊN KHOA HỌC", "value": "Alcedo atthis", "visual_en": "Macro head shot"},
            "group_box": {"title": "NHÓM", "value": "Chim, bộ Coraciiformes", "visual_en": "Perched view"},
            "size_box": {"title": "KÍCH THƯỚC", "value": "16 cm", "scale_bracket": "16 cm", "visual_en": "Profile"},
            "habitat_box": {"title": "MÔI TRƯỜNG SỐNG", "value": "Ven hồ, sông", "visual_en": "River habitat"},
            "diet_box": {"title": "THỨC ĂN", "value": "Cá nhỏ, côn trùng", "visual_en": "Holding fish"},
            "highlights_box": {
                "title": "ĐẶC ĐIỂM NỔI BẬT",
                "bullets": ["Lao xuống nước bắt cá", "Bộ lông lam cam rực", "Thị giác xuyên nước"],
                "visual_en": "Diving action",
            },
            "hero_prompt_en": "Kingfisher on reed",
            "hook_vi": "Cú bổ nhào chớp nhoáng không trượt phát nào.",
            "question_vi": "Bạn thấy tài bắt cá này thế nào?",
        }
        validated = validate_generated_topic(topic, "species_profile", [])
        self.assertEqual(validated["topic_key"], "test_species_profile")


if __name__ == "__main__":
    unittest.main()
