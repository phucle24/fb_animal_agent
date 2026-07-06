import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.generated_topic_service import generate_topic, load_generated_topics, save_generated_topic
from app.topic_bank import (
    ANATOMY_TOPICS,
    BEFORE_AFTER_TOPICS,
    COMPARISON_TOPICS,
    GUESS_QUIZ_TOPICS,
    MATCHUP_TOPICS,
    MYTH_VS_FACT_TOPICS,
    ONE_STORY_TOPICS,
    SINGLE_TOPICS,
)


if __name__ == "__main__":
    topic_type = sys.argv[1] if len(sys.argv) > 1 else "anatomy_infographic"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    allowed_types = {
        "anatomy_infographic",
        "comparison_top5",
        "single_card",
        "matchup_versus",
        "myth_vs_fact",
        "guess_quiz",
        "one_story",
        "before_after",
    }
    if topic_type not in allowed_types:
        print(
            "Usage: python scripts/generate_topics.py "
            "anatomy_infographic|comparison_top5|single_card|matchup_versus|myth_vs_fact|guess_quiz|one_story|before_after [count]"
        )
        sys.exit(1)

    existing_topics = (
        ANATOMY_TOPICS
        + COMPARISON_TOPICS
        + SINGLE_TOPICS
        + MATCHUP_TOPICS
        + MYTH_VS_FACT_TOPICS
        + GUESS_QUIZ_TOPICS
        + ONE_STORY_TOPICS
        + BEFORE_AFTER_TOPICS
        + load_generated_topics()
    )
    for _ in range(count):
        topic = generate_topic(topic_type, existing_topics)
        save_generated_topic(topic)
        existing_topics.append(topic)
        print(f"Generated {topic['topic_type']} | {topic['topic_key']} | {topic.get('subject_vi')}")
