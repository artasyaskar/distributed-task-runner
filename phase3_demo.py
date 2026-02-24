#!/usr/bin/env python3
"""
Demo script for Phase 3: Advanced Retry Logic & Failure Handling
"""
import asyncio
import time
import requests
import json


async def phase3_demo():
    """Demonstrate advanced retry logic and failure handling"""
    print("🚀 Phase 3: Advanced Retry Logic & Failure Handling Demo")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Check if API is running
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            print("❌ API server is not running!")
            print("💡 Start with: python run_api.py")
            return
        print("✅ API server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("💡 Start with: python run_api.py")
        return
    
    print("\n🎯 Phase 3 Features:")
    print("   • Exponential backoff retry strategies")
    print("   • Circuit breakers for fault tolerance")
    print("   • Dead letter queue for failed tasks")
    print("   • Advanced error handling and monitoring")
    print("   • Task execution statistics")
    
    # Show initial stats
    print(f"\n📊 Initial System Statistics:")
    response = requests.get(f"{base_url}/retry/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Tasks executed: {stats['execution_stats']['total_executed']}")
        print(f"   Success rate: {stats['execution_stats'].get('success_rate', 0):.1f}%")
        print(f"   Circuit breakers: {stats['circuit_breaker_stats']['total_circuit_breakers']}")
        print(f"   Dead letters: {stats['dead_letter_stats']['total_dead_letters']}")
    
    print(f"\n🧪 Testing Circuit Breakers...")
    
    # Simulate failures to trigger circuit breaker
    print("   Simulating failures for text_processing tasks...")
    for i in range(6):  # Exceed failure threshold (5)
        response = requests.post(f"{base_url}/retry/simulate-failure", 
                                params={"task_type": "text_processing", "error_type": "NetworkError"})
        if response.status_code == 200:
            print(f"   ✅ Simulated failure {i+1}")
        await asyncio.sleep(0.1)
    
    # Check circuit breaker status
    print(f"\n⚡ Circuit Breaker Status:")
    response = requests.get(f"{base_url}/retry/circuit-breakers")
    if response.status_code == 200:
        circuit_breakers = response.json()
        for cb in circuit_breakers:
            if cb.state == "open":
                print(f"   🔴 {cb.task_type}: {cb.state} ({cb.failures} failures)")
            elif cb.state == "half_open":
                print(f"   🟡 {cb.task_type}: {cb.state} ({cb.failures} failures)")
            else:
                print(f"   🟢 {cb.task_type}: {cb.state} ({cb.failures} failures)")
    
    print(f"\n📝 Creating Tasks with Simulated Failures...")
    
    # Create tasks that will likely fail
    tasks_to_create = [
        {
            "name": "Text Processing (will fail)",
            "task_type": "text_processing",
            "payload": {"text": "This task will experience simulated failures"}
        },
        {
            "name": "AI Summarization (rate limited)",
            "task_type": "ai_summarization",
            "payload": {"document": "This document might hit rate limits"}
        },
        {
            "name": "Batch Processing (database errors)",
            "task_type": "batch_processing",
            "payload": {"data": [f"item_{i}" for i in range(8)]}
        },
        {
            "name": "Image Processing (service errors)",
            "task_type": "image_processing",
            "payload": {"image_url": "https://example.com/test-image.jpg"}
        }
    ]
    
    created_tasks = []
    
    # Create tasks via API
    for task_info in tasks_to_create:
        print(f"\n📤 Creating {task_info['name']}...")
        response = requests.post(
            f"{base_url}/tasks/",
            json={
                "task_type": task_info["task_type"],
                "payload": task_info["payload"]
            }
        )
        
        if response.status_code == 201:
            task_data = response.json()
            created_tasks.append(task_data)
            print(f"✅ Task {task_data['id']} created")
        else:
            print(f"❌ Failed to create task: {response.status_code}")
    
    print(f"\n⏳ Monitoring Task Execution (with retries)...")
    print("💡 Make sure enhanced worker is running: python run_enhanced_worker.py")
    
    # Monitor tasks for a while
    completed_count = 0
    failed_count = 0
    start_time = time.time()
    max_wait = 45  # seconds
    
    while (completed_count + failed_count) < len(created_tasks) and (time.time() - start_time) < max_wait:
        print(f"\n--- Progress Update ({completed_count + failed_count}/{len(created_tasks)} processed) ---")
        
        # Check stats
        response = requests.get(f"{base_url}/retry/stats")
        if response.status_code == 200:
            stats = response.json()
            exec_stats = stats['execution_stats']
            print(f"   Total executed: {exec_stats['total_executed']}")
            print(f"   Successful: {exec_stats['successful']}")
            print(f"   Failed: {exec_stats['failed']}")
            print(f"   Retried: {exec_stats['retried']}")
            print(f"   Success rate: {exec_stats.get('success_rate', 0):.1f}%")
        
        # Check individual task status
        for task in created_tasks:
            if task.get('checked'):
                continue
                
            response = requests.get(f"{base_url}/tasks/{task['id']}")
            if response.status_code == 200:
                current_task = response.json()
                status = current_task['status']
                
                if status == 'completed':
                    print(f"   ✅ Task {task['id']} ({task['task_type']}): COMPLETED")
                    task['checked'] = True
                    completed_count += 1
                elif status == 'failed':
                    print(f"   ❌ Task {task['id']} ({task['task_type']}): FAILED")
                    print(f"      Error: {current_task.get('error_message', 'Unknown')}")
                    task['checked'] = True
                    failed_count += 1
                elif status == 'retrying':
                    print(f"   🔄 Task {task['id']} ({task['task_type']}): RETRYING (attempt {current_task['retry_count']})")
                elif status == 'running':
                    print(f"   ⚡ Task {task['id']} ({task['task_type']}): RUNNING")
        
        if (completed_count + failed_count) < len(created_tasks):
            print("⏰ Waiting 5 seconds before next check...")
            await asyncio.sleep(5)
    
    # Check dead letter queue
    print(f"\n💀 Dead Letter Queue:")
    response = requests.get(f"{base_url}/retry/dead-letters")
    if response.status_code == 200:
        dead_letters = response.json()
        if dead_letters:
            print(f"   Found {len(dead_letters)} dead letter tasks:")
            for dl in dead_letters[:3]:  # Show first 3
                print(f"     • Task {dl['task_id']} ({dl['task_type']}): {dl['error_type']}")
            if len(dead_letters) > 3:
                print(f"     ... and {len(dead_letters) - 3} more")
        else:
            print("   No dead letter tasks")
    
    # Demonstrate retrying a dead letter
    if dead_letters:
        print(f"\n🔄 Retrying a Dead Letter Task...")
        first_dead = dead_letters[0]
        response = requests.post(f"{base_url}/retry/dead-letters/{first_dead['task_id']}/retry")
        if response.status_code == 200:
            print(f"✅ Dead letter task {first_dead['task_id']} requeued for retry")
        else:
            print(f"❌ Failed to retry dead letter task")
    
    # Reset circuit breaker for demo
    print(f"\n🔧 Resetting Circuit Breakers...")
    response = requests.post(f"{base_url}/retry/circuit-breakers/text_processing/reset")
    if response.status_code == 200:
        print("✅ Circuit breaker for text_processing reset")
    
    # Final statistics
    print(f"\n📈 Final System Statistics:")
    response = requests.get(f"{base_url}/retry/stats")
    if response.status_code == 200:
        stats = response.json()
        exec_stats = stats['execution_stats']
        cb_stats = stats['circuit_breaker_stats']
        dl_stats = stats['dead_letter_stats']
        
        print(f"   📊 Execution:")
        print(f"      Total tasks: {exec_stats['total_executed']}")
        print(f"      Success rate: {exec_stats.get('success_rate', 0):.1f}%")
        print(f"      Retry rate: {exec_stats.get('retry_rate', 0):.1f}%")
        
        print(f"   ⚡ Circuit Breakers:")
        print(f"      Total: {cb_stats['total_circuit_breakers']}")
        print(f"      Open: {cb_stats['open_circuits']}")
        print(f"      Closed: {cb_stats['closed_circuits']}")
        
        print(f"   💀 Dead Letters:")
        print(f"      Total: {dl_stats['total_dead_letters']}")
        if dl_stats['by_task_type']:
            print(f"      By type: {dl_stats['by_task_type']}")
    
    print(f"\n🎉 Phase 3 Demo Completed!")
    print(f"\n💡 Key Phase 3 Achievements:")
    print(f"   • Exponential backoff prevents system overload")
    print(f"   • Circuit breakers protect against cascading failures")
    print(f"   • Dead letter queue handles permanently failed tasks")
    print(f"   • Advanced monitoring and statistics")
    print(f"   • Production-grade error handling")
    print(f"   • Fault-tolerant distributed architecture")


if __name__ == "__main__":
    try:
        asyncio.run(phase3_demo())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
