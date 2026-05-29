import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.generated_topic_service import find_duplicate_reason, load_generated_topics
from app.topic_bank import COMPARISON_TOPICS, MATCHUP_TOPICS, SINGLE_TOPICS


if __name__ == "__main__":
    static_topics = COMPARISON_TOPICS + SINGLE_TOPICS + MATCHUP_TOPICS
    generated_topics = load_generated_topics()
    all_topics = static_topics + generated_topics

    print(f"Static topics: {len(static_topics)}")
    print(f"Generated topics: {len(generated_topics)}")

    duplicates = []
    previous = []
    for topic in all_topics:
        reason = find_duplicate_reason(topic, previous)
        if reason:
            duplicates.append((topic.get("topic_key"), topic.get("topic_type"), reason))
        previous.append(topic)

    if not duplicates:
        print("No duplicate-like topics found.")
        sys.exit(0)

    print(f"Duplicate-like topics found: {len(duplicates)}")
    for topic_key, topic_type, reason in duplicates:
        print(f"- {topic_key} | {topic_type} | {reason}")
