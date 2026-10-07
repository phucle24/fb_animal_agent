import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.reel_service import ensure_future_reels, get_unposted_drive_reels


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    max_reels = int(args[0]) if args else None

    print("Checking unposted reels on Google Drive...")
    unposted = get_unposted_drive_reels()
    print(f"Found {len(unposted)} unposted reels on Drive:")
    for r in unposted:
        v_size_mb = int(r["video_file"].get("size", 0)) / (1024 * 1024)
        print(f"  #{r['number_str']}: {r['title']} ({v_size_mb:.1f} MB)")

    if "--dry-run" in sys.argv:
        print("Dry run complete. No reels downloaded or scheduled.")
        sys.exit(0)

    print("\nEnsuring future reel schedules and downloading media...")
    result = ensure_future_reels(max_reels=max_reels)
    print(f"Result: {result['message']}")
    for item in result["items"]:
        print(
            f"Scheduled ID={item['id']} | {item['scheduled_at']} | "
            f"slot={item['slot']} | {item['topic_key']} | {item['title']}"
        )
