import subprocess
import yaml
import os

def check_topics_exist():
    """Verify all configured topics exist"""
    print("🔍 Checking topics exist...")

    with open("config/kafka-topics.yaml") as f:
        config = yaml.safe_load(f)

    # List topics
    result = subprocess.run([
        "podman", "exec", "transportation_kafka",
        "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        return False

    existing = set(result.stdout.strip().split('\n'))
    expected = set(config["topics"].keys())
    missing = expected - existing

    if missing:
        print(f"❌ Missing topics: {missing}")
        return False

    print(f"✅ All {len(expected)} topics exist")
    return True

def main():
    print("🚀 Topic Verification")
    print("=" * 25)

    if check_topics_exist():
        print("\n🎉 TOPICS READY!")
        print("Step 3.3 complete")
    else:
        print("\n❌ Topics missing")

if __name__ == "__main__":
    main()
