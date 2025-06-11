import subprocess
import time
import sys
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Get ports from .env
ZOOKEEPER_PORT = os.getenv("ZOOKEEPER_CLIENT_PORT", "2181")
KAFKA_EXTERNAL_PORT = os.getenv("KAFKA_EXTERNAL_PORT", "9092")
TEST_TOPIC = f"test-topic-{uuid.uuid4()}"

def run_kafka_command(cmd):
    """Run kafka command in container"""
    full_cmd = [
        "podman", "exec", "transportation_kafka",
        "bash", "-c", cmd
    ]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"

def test_zookeeper_connection():
    """Test 1: Zookeeper connectivity via Kafka tools"""
    print("🔍 Test 1: Zookeeper connection...")
    
    # Use kafka-configs to test Zookeeper connectivity
    success, stdout, stderr = run_kafka_command(
        f"kafka-configs --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT} --describe --entity-type brokers"
    )
    if success:
        print("✅ Zookeeper responding (via Kafka)")
        return True
    else:
        print(f"❌ Zookeeper connection failed: {stderr}")
        return False

def test_kafka_broker():
    """Test 2: Kafka broker connectivity"""
    print("\n🔍 Test 2: Kafka broker...")
    
    success, stdout, stderr = run_kafka_command(
        f"kafka-broker-api-versions --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT}"
    )
    if success:
        print("✅ Kafka broker responding")
        return True
    else:
        print(f"❌ Kafka broker failed: {stderr}")
        return False

def test_topic_operations():
    """Test 3: Topic creation and listing"""
    print("\n🔍 Test 3: Topic operations...")
    
    # Create test topic
    success, stdout, stderr = run_kafka_command(
        f"kafka-topics --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT} --create --topic {TEST_TOPIC} --partitions 1 --replication-factor 1"
    )
    if not success:
        print(f"❌ Topic creation failed: {stderr}")
        return False
    
    # List topics
    success, stdout, stderr = run_kafka_command(
        f"kafka-topics --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT} --list"
    )
    if success and TEST_TOPIC in stdout:
        print("✅ Topic created and listed")
        return True
    else:
        print(f"❌ Topic listing failed: {stderr}")
        return False

def test_producer_consumer():
    """Test 4: Basic produce/consume"""
    print("\n🔍 Test 4: Producer/Consumer...")
    
    test_message = "Hello Kafka from Step 3.1!"
    
    # Produce message
    produce_cmd = f'echo "{test_message}" | kafka-console-producer --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT} --topic test-topic'
    success, stdout, stderr = run_kafka_command(produce_cmd)
    if not success:
        print(f"❌ Producer failed: {stderr}")
        return False
    
    print("✅ Message produced")
    
    # Give producer time to complete
    import time
    time.sleep(2)
    
    # Consume message (with timeout)
    consume_cmd = f"timeout 10s kafka-console-consumer --bootstrap-server localhost:{KAFKA_EXTERNAL_PORT} --topic test-topic --from-beginning --max-messages 1 2>/dev/null"
    success, stdout, stderr = run_kafka_command(consume_cmd)
    
    if success and test_message in stdout:
        print("✅ Message consumed")
        return True
    else:
        print(f"❌ Consumer failed: stdout='{stdout}', stderr='{stderr}'")
        return False

def check_containers_running():
    """Check if required containers are running"""
    print("🔍 Checking containers...")
    
    containers = ["transportation_zookeeper", "transportation_kafka"]
    for container in containers:
        result = subprocess.run(
            ["podman", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if container not in result.stdout:
            print(f"❌ Container {container} not running")
            return False
    
    print("✅ All containers running")
    return True

def main():
    print("🚀 Kafka Cluster Test")
    print("=" * 40)
    print("Prerequisites:")
    print("- podman-compose up -d (wait 2-3 minutes)")
    print("=" * 40)
    
    # Check containers first
    if not check_containers_running():
        print("\n❌ Start containers first: podman-compose up -d")
        sys.exit(1)
    
    # Wait a bit for Kafka to be fully ready
    print("\n⏱️ Waiting 10 seconds for Kafka to be ready...")
    time.sleep(10)
    
    tests = [
        ("Zookeeper Connection", test_zookeeper_connection),
        ("Kafka Broker", test_kafka_broker),
        ("Topic Operations", test_topic_operations),
        ("Producer/Consumer", test_producer_consumer)
    ]
    
    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))
        if not success:
            break  # Stop on first failure for debugging
    
    print("\n" + "=" * 40)
    print("📊 RESULTS")
    print("=" * 40)
    
    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    if all_passed:
        print("\n🎉 KAFKA CLUSTER READY!")
        print("Step 3.1 complete")
    else:
        print("\n❌ Tests failed - check container logs:")
        print("podman logs transportation_kafka")
        print("podman logs transportation_zookeeper")

if __name__ == "__main__":
    main()
