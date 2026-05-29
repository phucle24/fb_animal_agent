import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.generated_topic_service import generate_topic, load_generated_topics, save_generated_topic
from app.topic_bank import COMPARISON_TOPICS, SINGLE_TOPICS


if __name__ == "__main__":
    topic_type = sys.argv[1] if len(sys.argv) > 1 else "comparison_top5"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if topic_type not in {"comparison_top5", "single_card", "matchup_versus"}:
        print("Usage: python scripts/generate_topics.py comparison_top5|single_card|matchup_versus [count]")
        sys.exit(1)

    existing_topics = COMPARISON_TOPICS + SINGLE_TOPICS + load_generated_topics()
    for _ in range(count):
        topic = generate_topic(topic_type, existing_topics)
        save_generated_topic(topic)
        existing_topics.append(topic)
        print(f"Generated {topic['topic_type']} | {topic['topic_key']} | {topic.get('subject_vi')}")
