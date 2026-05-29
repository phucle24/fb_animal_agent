from copy import deepcopy


COMPARISON_TOPICS = [
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_fastest_land_animals",
        "subject_vi": "Top 5 con vật chạy nhanh nhất trên cạn",
        "subject_en": "Top 5 fastest land animals",
        "comparison_angle": "speed",
        "items": [
            {"rank": 1, "name_vi": "Báo Săn", "name_en": "Cheetah", "stat": "110 km/h"},
            {"rank": 2, "name_vi": "Linh Dương Sừng Nhánh", "name_en": "Pronghorn", "stat": "88 km/h"},
            {"rank": 3, "name_vi": "Linh Dương Springbok", "name_en": "Springbok", "stat": "88 km/h"},
            {"rank": 4, "name_vi": "Linh Dương Đầu Bò Xanh", "name_en": "Blue wildebeest", "stat": "80 km/h"},
            {"rank": 5, "name_vi": "Sư Tử", "name_en": "Lion", "stat": "80 km/h"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_tallest_land_animals",
        "subject_vi": "Top 5 loài động vật cao nhất trên cạn",
        "subject_en": "Top 5 tallest land animals",
        "comparison_angle": "height",
        "items": [
            {"rank": 1, "name_vi": "Hươu Cao Cổ", "name_en": "Giraffe", "stat": "5.5 m"},
            {"rank": 2, "name_vi": "Voi Châu Phi", "name_en": "African elephant", "stat": "4.0 m"},
            {"rank": 3, "name_vi": "Lạc Đà Một Bướu", "name_en": "Dromedary camel", "stat": "2.3 m"},
            {"rank": 4, "name_vi": "Nai Sừng Tấm", "name_en": "Moose", "stat": "2.1 m"},
            {"rank": 5, "name_vi": "Ngựa Shire", "name_en": "Shire horse", "stat": "2.0 m"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_heaviest_land_animals",
        "subject_vi": "Top 5 động vật trên cạn nặng nhất",
        "subject_en": "Top 5 heaviest land animals",
        "comparison_angle": "weight",
        "items": [
            {"rank": 1, "name_vi": "Voi Châu Phi", "name_en": "African elephant", "stat": "6000 kg"},
            {"rank": 2, "name_vi": "Voi Châu Á", "name_en": "Asian elephant", "stat": "5000 kg"},
            {"rank": 3, "name_vi": "Tê Giác Trắng", "name_en": "White rhinoceros", "stat": "2300 kg"},
            {"rank": 4, "name_vi": "Hà Mã", "name_en": "Hippopotamus", "stat": "1800 kg"},
            {"rank": 5, "name_vi": "Hươu Cao Cổ", "name_en": "Giraffe", "stat": "1200 kg"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_biggest_birds",
        "subject_vi": "Top 5 loài chim lớn nhất thế giới",
        "subject_en": "Top 5 biggest birds in the world",
        "comparison_angle": "size",
        "items": [
            {"rank": 1, "name_vi": "Đà Điểu Châu Phi", "name_en": "Ostrich", "stat": "156 kg"},
            {"rank": 2, "name_vi": "Đà Điểu Somali", "name_en": "Somali ostrich", "stat": "130 kg"},
            {"rank": 3, "name_vi": "Đà Điểu Emu", "name_en": "Emu", "stat": "45 kg"},
            {"rank": 4, "name_vi": "Chim Đầu Mào Phương Nam", "name_en": "Southern cassowary", "stat": "44 kg"},
            {"rank": 5, "name_vi": "Đại Bàng Biển Steller", "name_en": "Steller's sea eagle", "stat": "9 kg"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_famous_carnivorous_plants",
        "subject_vi": "Top 5 loài cây ăn thịt nổi bật",
        "subject_en": "Top 5 famous carnivorous plants",
        "comparison_angle": "special ability",
        "items": [
            {"rank": 1, "name_vi": "Cây Bắt Ruồi Venus", "name_en": "Venus flytrap", "stat": "Bẫy kẹp"},
            {"rank": 2, "name_vi": "Cây Nắp Ấm", "name_en": "Pitcher plant", "stat": "Bẫy hố"},
            {"rank": 3, "name_vi": "Gọng Vó", "name_en": "Sundew", "stat": "Lá dính"},
            {"rank": 4, "name_vi": "Bèo Bắt Mồi", "name_en": "Bladderwort", "stat": "Bẫy hút"},
            {"rank": 5, "name_vi": "Cây Bơ Hồng", "name_en": "Butterwort", "stat": "Lá nhớt"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_strongest_bite_animals",
        "subject_vi": "Top 5 loài vật có lực cắn đáng sợ",
        "subject_en": "Top 5 animals with terrifying bite force",
        "comparison_angle": "bite force",
        "items": [
            {"rank": 1, "name_vi": "Cá Sấu Nước Mặn", "name_en": "Saltwater crocodile", "stat": "3700 PSI"},
            {"rank": 2, "name_vi": "Cá Sấu Sông Nile", "name_en": "Nile crocodile", "stat": "3000 PSI"},
            {"rank": 3, "name_vi": "Hà Mã", "name_en": "Hippopotamus", "stat": "1800 PSI"},
            {"rank": 4, "name_vi": "Báo Đốm Mỹ", "name_en": "Jaguar", "stat": "1500 PSI"},
            {"rank": 5, "name_vi": "Khỉ Đột", "name_en": "Gorilla", "stat": "1300 PSI"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_most_venomous_animals",
        "subject_vi": "Top 5 loài có nọc độc khiến ai cũng tò mò",
        "subject_en": "Top 5 fascinating venomous animals",
        "comparison_angle": "venom",
        "items": [
            {"rank": 1, "name_vi": "Sứa Hộp", "name_en": "Box jellyfish", "stat": "Cực độc"},
            {"rank": 2, "name_vi": "Rắn Taipan Nội Địa", "name_en": "Inland taipan", "stat": "Nọc mạnh"},
            {"rank": 3, "name_vi": "Bạch Tuộc Đốm Xanh", "name_en": "Blue-ringed octopus", "stat": "Tê liệt"},
            {"rank": 4, "name_vi": "Ốc Cối", "name_en": "Cone snail", "stat": "Phóng lao"},
            {"rank": 5, "name_vi": "Cá Đá", "name_en": "Stonefish", "stat": "Gai độc"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_longest_lived_animals",
        "subject_vi": "Top 5 loài vật sống lâu đến khó tin",
        "subject_en": "Top 5 incredibly long-lived animals",
        "comparison_angle": "lifespan",
        "items": [
            {"rank": 1, "name_vi": "Sò Đại Dương Quahog", "name_en": "Ocean quahog", "stat": "500 năm"},
            {"rank": 2, "name_vi": "Cá Mập Greenland", "name_en": "Greenland shark", "stat": "400 năm"},
            {"rank": 3, "name_vi": "Cá Voi Đầu Cong", "name_en": "Bowhead whale", "stat": "200 năm"},
            {"rank": 4, "name_vi": "Rùa Khổng Lồ", "name_en": "Giant tortoise", "stat": "150 năm"},
            {"rank": 5, "name_vi": "Nhím Biển Đỏ", "name_en": "Red sea urchin", "stat": "100 năm"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_camouflage_masters",
        "subject_vi": "Top 5 bậc thầy ngụy trang trong tự nhiên",
        "subject_en": "Top 5 camouflage masters in nature",
        "comparison_angle": "camouflage",
        "items": [
            {"rank": 1, "name_vi": "Bạch Tuộc Bắt Chước", "name_en": "Mimic octopus", "stat": "Đổi dáng"},
            {"rank": 2, "name_vi": "Mực Nang", "name_en": "Cuttlefish", "stat": "Đổi màu"},
            {"rank": 3, "name_vi": "Tắc Kè Đuôi Lá", "name_en": "Leaf-tailed gecko", "stat": "Giống lá"},
            {"rank": 4, "name_vi": "Bọ Que", "name_en": "Stick insect", "stat": "Giống cành"},
            {"rank": 5, "name_vi": "Cá Đá", "name_en": "Stonefish", "stat": "Giống đá"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_glowing_animals",
        "subject_vi": "Top 5 loài phát sáng đẹp như phim viễn tưởng",
        "subject_en": "Top 5 glowing animals that look unreal",
        "comparison_angle": "bioluminescence",
        "items": [
            {"rank": 1, "name_vi": "Đom Đóm", "name_en": "Firefly", "stat": "Tín hiệu sáng"},
            {"rank": 2, "name_vi": "Cá Cần Câu", "name_en": "Anglerfish", "stat": "Mồi phát sáng"},
            {"rank": 3, "name_vi": "Giun Phát Sáng", "name_en": "Glowworm", "stat": "Hang sao"},
            {"rank": 4, "name_vi": "Sứa Lược", "name_en": "Comb jelly", "stat": "Sắc cầu vồng"},
            {"rank": 5, "name_vi": "Bọ Cạp", "name_en": "Scorpion", "stat": "Huỳnh quang"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_fastest_sea_animals",
        "subject_vi": "Top 5 sinh vật biển lao nhanh nhất",
        "subject_en": "Top 5 fastest sea animals",
        "comparison_angle": "speed",
        "items": [
            {"rank": 1, "name_vi": "Cá Cờ", "name_en": "Sailfish", "stat": "110 km/h"},
            {"rank": 2, "name_vi": "Cá Kiếm", "name_en": "Swordfish", "stat": "97 km/h"},
            {"rank": 3, "name_vi": "Cá Marlin Đen", "name_en": "Black marlin", "stat": "82 km/h"},
            {"rank": 4, "name_vi": "Cá Ngừ Vây Vàng", "name_en": "Yellowfin tuna", "stat": "75 km/h"},
            {"rank": 5, "name_vi": "Cá Heo Thường", "name_en": "Common dolphin", "stat": "60 km/h"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_weirdest_plants",
        "subject_vi": "Top 5 loài cây kỳ lạ nhất hành tinh",
        "subject_en": "Top 5 weirdest plants on Earth",
        "comparison_angle": "special ability",
        "items": [
            {"rank": 1, "name_vi": "Hoa Xác Thối", "name_en": "Corpse flower", "stat": "Mùi xác"},
            {"rank": 2, "name_vi": "Hoa Rafflesia", "name_en": "Rafflesia flower", "stat": "Hoa khổng lồ"},
            {"rank": 3, "name_vi": "Cây Máu Rồng", "name_en": "Dragon blood tree", "stat": "Nhựa đỏ"},
            {"rank": 4, "name_vi": "Cây Trinh Nữ", "name_en": "Sensitive plant", "stat": "Cụp lá"},
            {"rank": 5, "name_vi": "Cây Welwitschia", "name_en": "Welwitschia", "stat": "Sống lâu"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_dangerous_plants",
        "subject_vi": "Top 5 loài cây nguy hiểm hơn vẻ ngoài",
        "subject_en": "Top 5 dangerous plants that look harmless",
        "comparison_angle": "toxicity",
        "items": [
            {"rank": 1, "name_vi": "Cây Thầu Dầu", "name_en": "Castor bean plant", "stat": "Ricin"},
            {"rank": 2, "name_vi": "Cây Phụ Tử", "name_en": "Monkshood", "stat": "Aconitine"},
            {"rank": 3, "name_vi": "Trúc Đào", "name_en": "Oleander", "stat": "Độc tim"},
            {"rank": 4, "name_vi": "Cây Cà Độc Dược", "name_en": "Jimsonweed", "stat": "Gây ảo giác"},
            {"rank": 5, "name_vi": "Cây Manchineel", "name_en": "Manchineel tree", "stat": "Nhựa độc"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_animal_architects",
        "subject_vi": "Top 5 kiến trúc sư siêu đẳng trong tự nhiên",
        "subject_en": "Top 5 animal architects in nature",
        "comparison_angle": "building ability",
        "items": [
            {"rank": 1, "name_vi": "Hải Ly", "name_en": "Beaver", "stat": "Đập nước"},
            {"rank": 2, "name_vi": "Mối", "name_en": "Termite", "stat": "Tháp đất"},
            {"rank": 3, "name_vi": "Chim Sẻ Dòng Dọc", "name_en": "Weaverbird", "stat": "Tổ dệt"},
            {"rank": 4, "name_vi": "Ong Mật", "name_en": "Honeybee", "stat": "Tổ lục giác"},
            {"rank": 5, "name_vi": "Kiến Cắt Lá", "name_en": "Leafcutter ant", "stat": "Trang trại nấm"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_animal_super_senses",
        "subject_vi": "Top 5 siêu giác quan khiến con người phải ghen tị",
        "subject_en": "Top 5 animal super senses",
        "comparison_angle": "special ability",
        "items": [
            {"rank": 1, "name_vi": "Cá Mập", "name_en": "Shark", "stat": "Cảm điện"},
            {"rank": 2, "name_vi": "Dơi", "name_en": "Bat", "stat": "Định vị âm"},
            {"rank": 3, "name_vi": "Rắn Hổ Lục", "name_en": "Pit viper", "stat": "Cảm nhiệt"},
            {"rank": 4, "name_vi": "Đại Bàng", "name_en": "Eagle", "stat": "Mắt siêu xa"},
            {"rank": 5, "name_vi": "Chó", "name_en": "Dog", "stat": "Khứu giác mạnh"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_extreme_survivors",
        "subject_vi": "Top 5 sinh vật sống sót ở nơi khắc nghiệt",
        "subject_en": "Top 5 extreme survivors in nature",
        "comparison_angle": "survival",
        "items": [
            {"rank": 1, "name_vi": "Gấu Nước", "name_en": "Tardigrade", "stat": "Cực hạn"},
            {"rank": 2, "name_vi": "Vi Khuẩn Deinococcus", "name_en": "Deinococcus radiodurans", "stat": "Chịu bức xạ"},
            {"rank": 3, "name_vi": "Lạc Đà Một Bướu", "name_en": "Dromedary camel", "stat": "Chịu khát"},
            {"rank": 4, "name_vi": "Cá Phổi", "name_en": "Lungfish", "stat": "Ngủ bùn"},
            {"rank": 5, "name_vi": "Chim Cánh Cụt Hoàng Đế", "name_en": "Emperor penguin", "stat": "Băng giá"},
        ],
    },
    {
        "topic_type": "comparison_top5",
        "topic_key": "top5_surprising_parenting_animals",
        "subject_vi": "Top 5 ông bố bà mẹ tận tụy trong thế giới động vật",
        "subject_en": "Top 5 surprising animal parents",
        "comparison_angle": "parenting",
        "items": [
            {
                "rank": 1,
                "name_vi": "Chim Cánh Cụt Hoàng Đế",
                "name_en": "Emperor penguin",
                "stat": "Ấp trứng",
                "detail_vi": "con đực giữ trứng trên chân qua mùa đông băng giá",
            },
            {
                "rank": 2,
                "name_vi": "Cá Ngựa",
                "name_en": "Seahorse",
                "stat": "Con đực mang thai",
                "detail_vi": "con cái gửi trứng vào túi ấp của con đực",
            },
            {
                "rank": 3,
                "name_vi": "Cá Sấu",
                "name_en": "Crocodile",
                "stat": "Bảo vệ con",
                "detail_vi": "mẹ cá sấu ngậm con rất nhẹ để đưa xuống nước",
            },
            {
                "rank": 4,
                "name_vi": "Ếch Phi Tiêu Độc",
                "name_en": "Poison dart frog",
                "stat": "Cõng nòng nọc",
                "detail_vi": "bố mẹ chở nòng nọc tới vũng nước nhỏ an toàn",
            },
            {
                "rank": 5,
                "name_vi": "Voi",
                "name_en": "Elephant",
                "stat": "Cả đàn chăm",
                "detail_vi": "voi con được mẹ, dì và cả đàn cùng bảo vệ",
            },
        ],
    },
]

SINGLE_TOPICS = [
    {
        "topic_type": "single_card",
        "topic_key": "cheetah_speed_card",
        "subject_vi": "Báo Săn",
        "subject_en": "Cheetah",
        "fact_label": "speed",
        "fact_value": "110 km/h",
        "fact_detail": "one of the fastest land animals on Earth",
        "detail_vi": "có thể bứt tốc cực nhanh trong vài giây ngắn",
    },
    {
        "topic_type": "single_card",
        "topic_key": "mantis_shrimp_punch_card",
        "subject_vi": "Tôm Tít",
        "subject_en": "Mantis shrimp",
        "fact_label": "special ability",
        "fact_value": "cú đấm siêu tốc",
        "fact_detail": "its strike is among the fastest animal movements and can crack shells",
        "detail_vi": "cú đấm tạo lực mạnh đến mức có thể làm nứt vỏ con mồi",
    },
    {
        "topic_type": "single_card",
        "topic_key": "electric_eel_shock_card",
        "subject_vi": "Lươn Điện",
        "subject_en": "Electric eel",
        "fact_label": "special ability",
        "fact_value": "phóng điện mạnh",
        "fact_detail": "it can generate powerful electric pulses to hunt and defend itself",
        "detail_vi": "dùng xung điện mạnh để săn mồi và tự vệ dưới nước",
    },
    {
        "topic_type": "single_card",
        "topic_key": "immortal_jellyfish_card",
        "subject_vi": "Sứa Bất Tử",
        "subject_en": "Immortal jellyfish",
        "fact_label": "special ability",
        "fact_value": "đảo ngược tuổi",
        "fact_detail": "it can revert to an earlier life stage under stress",
        "detail_vi": "khi gặp căng thẳng, nó có thể quay về giai đoạn non hơn",
    },
    {
        "topic_type": "single_card",
        "topic_key": "axolotl_regeneration_card",
        "subject_vi": "Kỳ Giông Mexico",
        "subject_en": "Axolotl",
        "fact_label": "regeneration",
        "fact_value": "tái tạo chi",
        "fact_detail": "it can regrow limbs and repair parts of its body with unusual ability",
        "detail_vi": "có thể mọc lại chi và sửa chữa một số mô bị tổn thương",
    },
    {
        "topic_type": "single_card",
        "topic_key": "archerfish_water_shot_card",
        "subject_vi": "Cá Mang Rổ",
        "subject_en": "Archerfish",
        "fact_label": "hunting ability",
        "fact_value": "bắn tia nước",
        "fact_detail": "it shoots water jets to knock insects off branches above the surface",
        "detail_vi": "bắn tia nước chính xác để hạ côn trùng trên cành cây",
    },
    {
        "topic_type": "single_card",
        "topic_key": "mimic_octopus_card",
        "subject_vi": "Bạch Tuộc Bắt Chước",
        "subject_en": "Mimic octopus",
        "fact_label": "camouflage",
        "fact_value": "giả dạng bậc thầy",
        "fact_detail": "it can imitate the look and movement of several dangerous sea animals",
        "detail_vi": "bắt chước hình dáng và cách di chuyển của loài biển nguy hiểm",
    },
    {
        "topic_type": "single_card",
        "topic_key": "lyrebird_voice_card",
        "subject_vi": "Chim Lia",
        "subject_en": "Lyrebird",
        "fact_label": "sound mimicry",
        "fact_value": "nhại âm siêu thật",
        "fact_detail": "it is famous for copying natural and artificial sounds with striking accuracy",
        "detail_vi": "có thể bắt chước nhiều âm thanh tự nhiên và nhân tạo rất giống",
    },
    {
        "topic_type": "single_card",
        "topic_key": "pangolin_armor_card",
        "subject_vi": "Tê Tê",
        "subject_en": "Pangolin",
        "fact_label": "defense",
        "fact_value": "áo giáp vảy",
        "fact_detail": "its keratin scales help it curl into a tough defensive ball",
        "detail_vi": "cuộn tròn thành quả bóng vảy cứng để tự bảo vệ",
    },
    {
        "topic_type": "single_card",
        "topic_key": "tardigrade_survival_card",
        "subject_vi": "Gấu Nước",
        "subject_en": "Tardigrade",
        "fact_label": "survival",
        "fact_value": "sống cực hạn",
        "fact_detail": "it can survive extreme environments by entering a dormant state",
        "detail_vi": "chuyển sang trạng thái ngủ sâu để chịu điều kiện khắc nghiệt",
    },
    {
        "topic_type": "single_card",
        "topic_key": "corpse_flower_card",
        "subject_vi": "Hoa Xác Thối",
        "subject_en": "Corpse flower",
        "fact_label": "plant ability",
        "fact_value": "mùi xác thối",
        "fact_detail": "its odor attracts pollinators that are drawn to decaying organic matter",
        "detail_vi": "tỏa mùi giống xác thối để thu hút côn trùng thụ phấn",
    },
    {
        "topic_type": "single_card",
        "topic_key": "rafflesia_giant_flower_card",
        "subject_vi": "Hoa Rafflesia",
        "subject_en": "Rafflesia flower",
        "fact_label": "plant record",
        "fact_value": "hoa khổng lồ",
        "fact_detail": "it produces one of the largest individual flowers in the world",
        "detail_vi": "tạo ra một trong những bông hoa đơn lẻ lớn nhất thế giới",
    },
    {
        "topic_type": "single_card",
        "topic_key": "dragon_blood_tree_card",
        "subject_vi": "Cây Máu Rồng",
        "subject_en": "Dragon blood tree",
        "fact_label": "plant feature",
        "fact_value": "nhựa đỏ",
        "fact_detail": "its red resin gives the tree its dramatic name and unusual appearance",
        "detail_vi": "nhựa cây màu đỏ khiến nó có vẻ ngoài rất kỳ lạ",
    },
    {
        "topic_type": "single_card",
        "topic_key": "owl_silent_flight_card",
        "subject_vi": "Cú Mèo",
        "subject_en": "Owl",
        "fact_label": "special ability",
        "fact_value": "bay gần như im lặng",
        "fact_detail": "its wing structure helps reduce turbulence and noise",
        "detail_vi": "cấu trúc lông cánh giúp giảm tiếng động khi lao xuống săn mồi",
    },
    {
        "topic_type": "single_card",
        "topic_key": "exploding_ant_defense_card",
        "subject_vi": "Kiến Nổ",
        "subject_en": "Exploding ant",
        "fact_label": "defense",
        "fact_value": "tự nổ bảo vệ đàn",
        "fact_detail": "some worker ants rupture their own bodies to release sticky defensive fluid",
        "detail_vi": "một số kiến thợ hy sinh thân mình để phun chất dính bảo vệ tổ",
    },
    {
        "topic_type": "single_card",
        "topic_key": "venus_flytrap_card",
        "subject_vi": "Cây Bắt Ruồi Venus",
        "subject_en": "Venus flytrap",
        "fact_label": "special ability",
        "fact_value": "cây ăn thịt",
        "fact_detail": "it traps insects with a fast snap-trap mechanism",
        "detail_vi": "khép bẫy rất nhanh để giữ côn trùng làm nguồn dinh dưỡng",
    },
]


MATCHUP_TOPICS = [
    {
        "topic_type": "matchup_versus",
        "topic_key": "tibetan_mastiff_vs_bengal_tiger",
        "subject_vi": "Chó Ngao Tây Tạng đối đầu Hổ Bengal",
        "subject_en": "Tibetan Mastiff versus Bengal tiger",
        "left": {
            "name_vi": "Chó Ngao Tây Tạng",
            "name_en": "Tibetan Mastiff",
            "height": "76 cm",
            "weight": "70 kg",
            "bite_force": "550 PSI",
            "edge_vi": "lông cổ dày, thân hình lớn, tiếng sủa uy hiếp",
        },
        "right": {
            "name_vi": "Hổ Bengal",
            "name_en": "Bengal tiger",
            "height": "110 cm",
            "weight": "220 kg",
            "bite_force": "1050 PSI",
            "edge_vi": "khối cơ bùng nổ, móng vuốt, bản năng săn mồi độc lập",
        },
        "verdict_vi": "Hổ Bengal vượt trội rõ rệt về khối lượng, lực cắn, tốc độ và vũ khí tự nhiên.",
        "reality_note_vi": "Đây là so sánh giả định dựa trên số liệu sinh học, không cổ vũ cho động vật đối đầu thật.",
        "debate_question_vi": "Bạn nghĩ ưu thế nào quyết định nhiều nhất: cân nặng, lực cắn hay bản năng săn mồi?",
    },
    {
        "topic_type": "matchup_versus",
        "topic_key": "gray_wolf_vs_spotted_hyena",
        "subject_vi": "Sói Xám đối đầu Linh Cẩu Đốm",
        "subject_en": "Gray wolf versus spotted hyena",
        "left": {
            "name_vi": "Sói Xám",
            "name_en": "Gray wolf",
            "height": "85 cm",
            "weight": "55 kg",
            "bite_force": "400 PSI",
            "edge_vi": "sức bền cao, phối hợp bầy đàn, phản xạ linh hoạt",
        },
        "right": {
            "name_vi": "Linh Cẩu Đốm",
            "name_en": "Spotted hyena",
            "height": "90 cm",
            "weight": "70 kg",
            "bite_force": "1100 PSI",
            "edge_vi": "hàm cực khỏe, thân trước mạnh, chịu va chạm tốt",
        },
        "verdict_vi": "Linh cẩu đốm có lợi thế lớn trong va chạm trực diện nhờ hàm và thể lực.",
        "reality_note_vi": "Ngoài tự nhiên, môi trường, số lượng bầy và tình huống mới là yếu tố quyết định.",
        "debate_question_vi": "Nếu bỏ qua bầy đàn, bạn chọn sự bền bỉ của sói hay lực hàm của linh cẩu?",
    },
    {
        "topic_type": "matchup_versus",
        "topic_key": "gorilla_vs_grizzly_bear",
        "subject_vi": "Khỉ Đột đối đầu Gấu Xám Bắc Mỹ",
        "subject_en": "Gorilla versus grizzly bear",
        "left": {
            "name_vi": "Khỉ Đột",
            "name_en": "Gorilla",
            "height": "170 cm",
            "weight": "180 kg",
            "bite_force": "1300 PSI",
            "edge_vi": "tay rất khỏe, lực cắn lớn, khả năng vật lộn tốt",
        },
        "right": {
            "name_vi": "Gấu Xám",
            "name_en": "Grizzly bear",
            "height": "150 cm",
            "weight": "270 kg",
            "bite_force": "975 PSI",
            "edge_vi": "cơ thể nặng hơn, móng vuốt dài, lớp mỡ và cơ dày",
        },
        "verdict_vi": "Gấu xám thường có lợi thế nhờ khối lượng, móng vuốt và khả năng chịu đòn.",
        "reality_note_vi": "Đây là so sánh giả định; hai loài sống ở môi trường khác nhau và không nên bị đặt vào đối đầu.",
        "debate_question_vi": "Theo bạn, sức tay của khỉ đột có đủ bù lại khối lượng của gấu xám không?",
    },
    {
        "topic_type": "matchup_versus",
        "topic_key": "komodo_dragon_vs_king_cobra",
        "subject_vi": "Rồng Komodo đối đầu Rắn Hổ Mang Chúa",
        "subject_en": "Komodo dragon versus king cobra",
        "left": {
            "name_vi": "Rồng Komodo",
            "name_en": "Komodo dragon",
            "height": "60 cm",
            "weight": "70 kg",
            "bite_force": "600 PSI",
            "edge_vi": "da dày, hàm răng sắc, sức kéo mạnh",
        },
        "right": {
            "name_vi": "Rắn Hổ Mang Chúa",
            "name_en": "King cobra",
            "height": "Nâng đầu 150 cm",
            "weight": "9 kg",
            "bite_force": "Nọc độc",
            "edge_vi": "tầm đánh nhanh, nọc thần kinh, khả năng cảnh báo mạnh",
        },
        "verdict_vi": "Komodo áp đảo về thể hình, còn hổ mang chúa nguy hiểm nhờ nọc và khoảng cách tấn công.",
        "reality_note_vi": "Kết quả giả định phụ thuộc rất lớn vào cú tấn công đầu tiên và môi trường.",
        "debate_question_vi": "Bạn nghĩ thể hình Komodo hay nọc độc hổ mang chúa đáng sợ hơn?",
    },
]


def get_topic_by_index(index: int) -> dict:
    """Rotate evenly across Top 5, single-card, and matchup topics."""
    topic_group = index % 3
    group_index = index // 3

    if topic_group == 0:
        comparison_slot_index = group_index
        if comparison_slot_index < len(COMPARISON_TOPICS):
            return deepcopy(COMPARISON_TOPICS[comparison_slot_index])

        from app.generated_topic_service import get_generated_topic

        generated_index = comparison_slot_index - len(COMPARISON_TOPICS)
        return get_generated_topic(
            "comparison_top5",
            generated_index,
            COMPARISON_TOPICS + SINGLE_TOPICS + MATCHUP_TOPICS,
        )

    if topic_group == 1:
        single_slot_index = group_index
        if single_slot_index < len(SINGLE_TOPICS):
            return deepcopy(SINGLE_TOPICS[single_slot_index])

        from app.generated_topic_service import get_generated_topic

        generated_index = single_slot_index - len(SINGLE_TOPICS)
        return get_generated_topic(
            "single_card",
            generated_index,
            COMPARISON_TOPICS + SINGLE_TOPICS + MATCHUP_TOPICS,
        )

    matchup_slot_index = group_index
    if matchup_slot_index < len(MATCHUP_TOPICS):
        return deepcopy(MATCHUP_TOPICS[matchup_slot_index])

    from app.generated_topic_service import get_generated_topic

    generated_index = matchup_slot_index - len(MATCHUP_TOPICS)
    return get_generated_topic(
        "matchup_versus",
        generated_index,
        COMPARISON_TOPICS + SINGLE_TOPICS + MATCHUP_TOPICS,
    )
