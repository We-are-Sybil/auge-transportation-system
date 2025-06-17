import yaml
import subprocess
import time
import sys
import os

def wait_for_kafka():
    """Wait for Kafka to be ready"""
    print("Waiting for Kafka...")
    for i in range(30):
        try:
            result = subprocess.run([
                "kafka-broker-api-versions", 
                "--bootstrap-server", "kafka:29092"
            ], capture_output=True, timeout=10)
            if result.returncode == 0:
                print("✅ Kafka ready")
                return True
        except:
            pass
        time.sleep(2)
    return False

def create_topic(name, config):
    """Create single topic"""
    cmd = [
        "kafka-topics",
        "--bootstrap-server", "kafka:29092",
        "--create", "--topic", name,
        "--partitions", str(config["partitions"]),
        "--replication-factor", str(config["replication_factor"])
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 or "already exists" in result.stderr:
        # Set retention
        retention_ms = config["retention_hours"] * 3600000
        subprocess.run([
            "kafka-configs",
            "--bootstrap-server", "kafka:29092", 
            "--alter", "--entity-type", "topics",
            "--entity-name", name,
            "--add-config", f"retention.ms={retention_ms}"
        ], capture_output=True)
        return True
    return False

def main():
    if not wait_for_kafka():
        sys.exit(1)

    with open("/config/kafka-topics.yaml") as f:
        config = yaml.safe_load(f)

    success = 0
    total = len(config["topics"])

    for name, topic_config in config["topics"].items():
        if create_topic(name, topic_config):
            print(f"✅ {name}")
            success += 1
        else:
            print(f"❌ {name}")

    print(f"Created {success}/{total} topics")
    sys.exit(0 if success == total else 1)

if __name__ == "__main__":
    main()
