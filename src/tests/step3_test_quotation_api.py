import requests
import asyncio
import json
import time
from datetime import datetime, timedelta
from aiokafka import AIOKafkaConsumer

BASE_URL = "http://localhost:8000"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

def test_create_quotation_request():
    """Test 1: Create quotation request via API"""
    print("🔍 Test 1: Create quotation request...")
    
    try:
        quotation_data = {
            "client_cc_nit": f"12345678-{int(time.time()) % 1000}",
            "nombre_solicitante": "María García",
            "celular_contacto": "3001234567",
            "quien_solicita": "María García",
            "fecha_inicio_servicio": (datetime.now() + timedelta(days=1)).isoformat(),
            "hora_inicio_servicio": "14:30",
            "direccion_inicio": "Calle 100 #15-20, Bogotá",
            "direccion_terminacion": "Aeropuerto El Dorado, Bogotá",
            "caracteristicas_servicio": "Transporte ejecutivo al aeropuerto",
            "cantidad_pasajeros": 2,
            "equipaje_carga": True,
            "user_id": "test_user_api"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotations/requests", json=quotation_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Request created: {result['form_number']}")
            print(f"✅ Database ID: {result['request_id']}")
            print(f"✅ Kafka sent: {result['kafka_sent']}")
            return True, result['request_id']
        else:
            print(f"❌ API failed: {response.status_code} - {response.text}")
            return False, None
    
    except Exception as e:
        print(f"❌ Request creation failed: {e}")
        return False, None

def test_create_quotation_response(request_id):
    """Test 2: Create quotation response via API"""
    print("\n🔍 Test 2: Create quotation response...")
    
    try:
        response_data = {
            "request_id": request_id,
            "precio_base": 80000.0,
            "precio_total": 95000.0,
            "condiciones_servicio": "Servicio puerta a puerta, vehículo ejecutivo",
            "condiciones_pago": "Pago 50% anticipado, 50% al finalizar servicio"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotations/responses", json=response_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response created: {result['quotation_id']}")
            print(f"✅ Price: ${result['precio_total']:,.0f}")
            print(f"✅ Kafka sent: {result['kafka_sent']}")
            return True, result['quotation_id']
        else:
            print(f"❌ API failed: {response.status_code} - {response.text}")
            return False, None
    
    except Exception as e:
        print(f"❌ Response creation failed: {e}")
        return False, None

def test_accept_quotation(quotation_id):
    """Test 3: Accept quotation via API"""
    print("\n🔍 Test 3: Accept quotation...")
    
    try:
        billing_data = {
            "facturar_a_nombre": "María García Empresa SAS",
            "nit_facturacion": "901234567-1",
            "direccion_facturacion": "Calle 100 #15-20, Bogotá",
            "email_facturacion": "maria@empresa.com",
            "responsable_servicio": "María García",
            "celular_responsable": "3001234567"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/quotations/{quotation_id}/accept",
            json=billing_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Quotation accepted: {result['quotation_id']}")
            print(f"✅ Service order: {result['service_order_id']}")
            print(f"✅ Kafka sent: {result['kafka_sent']}")
            return True
        else:
            print(f"❌ API failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Acceptance failed: {e}")
        return False

async def test_consume_quotation_events():
    """Test 4: Verify events appear in Kafka"""
    print("\n🔍 Test 4: Consume quotation events from Kafka...")
    
    consumer = AIOKafkaConsumer(
        "quotation.requests",
        "quotation.responses", 
        "quotation.confirmations",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=8000
    )
    
    try:
        await consumer.start()
        print("✅ Kafka consumer started")
        
        events_found = []
        start_time = time.time()
        
        async for msg in consumer:
            message_data = msg.value
            event_type = message_data.get("event_type")
            
            print(f"📥 Found event: {event_type} in {msg.topic}")
            
            if event_type in ["quotation_request", "quotation_response", "quotation_confirmation"]:
                events_found.append(event_type)
                
                # Log event details
                event_data = message_data.get("event_data", {})
                if event_type == "quotation_request":
                    print(f"   Request: {event_data.get('form_number', 'unknown')}")
                elif event_type == "quotation_response":
                    print(f"   Quote: {event_data.get('quotation_id', 'unknown')} - ${event_data.get('precio_total', 'unknown')}")
                elif event_type == "quotation_confirmation":
                    print(f"   Decision: {event_data.get('decision', 'unknown')}")
            
            # Stop after finding events or timeout
            if len(events_found) >= 3 or time.time() - start_time > 8:
                break
        
        print(f"✅ Found {len(events_found)} quotation events")
        return len(events_found) > 0
        
    except Exception as e:
        print(f"❌ Kafka consumption failed: {e}")
        return False
    finally:
        await consumer.stop()

def test_fastapi_health():
    """Test 0: FastAPI health check"""
    print("🔍 Test 0: FastAPI health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        result = response.json()
        
        kafka_status = result.get("services", {}).get("kafka", {}).get("kafka_producer", {}).get("status")
        
        success = response.status_code == 200 and kafka_status == "healthy"
        print(f"✅ FastAPI health: {result.get('status')}")
        print(f"✅ Kafka status: {kafka_status}")
        return success
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

async def main():
    print("🚀 Quotation API Integration Test")
    print("=" * 45)
    print("Prerequisites:")
    print("- podman-compose up -d")
    print("- uv run uvicorn src.webhook_service.main:app --reload")
    print("=" * 45)
    
    # Test 0: Health check
    if not test_fastapi_health():
        print("\n❌ FastAPI/Kafka not ready")
        return
    
    # Test 1: Create quotation request
    request_success, request_id = test_create_quotation_request()
    if not request_success or not request_id:
        print("\n❌ Request creation failed")
        return
    
    # Small delay
    await asyncio.sleep(1)
    
    # Test 2: Create quotation response
    response_success, quotation_id = test_create_quotation_response(request_id)
    if not response_success or not quotation_id:
        print("\n❌ Response creation failed")
        return
    
    # Small delay
    await asyncio.sleep(1)
    
    # Test 3: Accept quotation
    accept_success = test_accept_quotation(quotation_id)
    if not accept_success:
        print("\n❌ Quotation acceptance failed")
        return
    
    # Wait for Kafka messages to be available
    await asyncio.sleep(2)
    
    # Test 4: Verify events in Kafka
    kafka_success = await test_consume_quotation_events()
    
    print("\n" + "=" * 45)
    print("📊 RESULTS")
    print("=" * 45)
    
    tests = [
        ("FastAPI Health", True),
        ("Request Creation", request_success),
        ("Response Creation", response_success),
        ("Quotation Acceptance", accept_success),
        ("Kafka Events", kafka_success)
    ]
    
    all_passed = all(success for _, success in tests)
    for name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    if all_passed:
        print("\n🎉 QUOTATION API INTEGRATION WORKING!")
        print("You should now see:")
        print("- ✅ Quotation events in Kafka logs")
        print("- ✅ Database records created")
        print("- ✅ Complete quotation workflow")
        print("\nStep 3.7 complete - Quotation events flowing through system!")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main())
