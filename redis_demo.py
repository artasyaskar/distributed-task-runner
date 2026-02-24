#!/usr/bin/env python3
"""
Demo script for Redis-based distributed task system
"""
import asyncio
import time
import requests
import json


async def redis_demo():
    """Demonstrate Redis-based distributed task processing"""
    print("🚀 Redis Distributed Task System Demo")
    print("=" * 50)
    
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
    
    # Check Redis connection
    try:
        response = requests.get(f"{base_url}/tasks/queue/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Redis connected - Queue size: {stats['queue_size']}")
        else:
            print("⚠️ Redis may not be connected")
    except:
        print("⚠️ Cannot connect to Redis queue stats")
        print("💡 Make sure Redis is running: redis-server")
    
    print("\n📝 Creating tasks for distributed processing...")
    
    # Create different types of tasks
    tasks_to_create = [
        {
            "name": "Text Processing",
            "task_type": "text_processing",
            "payload": {"text": "This text will be processed by Redis workers!"}
        },
        {
            "name": "AI Summarization",
            "task_type": "ai_summarization",
            "payload": {"document": "This document contains important information about distributed systems and task processing."}
        },
        {
            "name": "Batch Processing",
            "task_type": "batch_processing",
            "payload": {"data": [f"item_{i}" for i in range(10)]}
        },
        {
            "name": "Image Processing",
            "task_type": "image_processing",
            "payload": {"image_url": "https://example.com/demo-image.jpg"}
        }
    ]
    
    created_tasks = []
    
    # Create tasks via API
    for task_info in tasks_to_create:
        print(f"\n📤 Creating {task_info['name']} task...")
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
            print(f"✅ Task {task_data['id']} created and queued")
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Error: {response.text}")
    
    # Show queue stats
    print(f"\n📊 Queue Statistics:")
    response = requests.get(f"{base_url}/tasks/queue/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Tasks in queue: {stats['queue_size']}")
        print(f"   Currently processing: {stats['processing']}")
        print(f"   Total pending: {stats['total_pending']}")
    
    # Monitor task progress
    print(f"\n⏳ Monitoring task progress...")
    print("💡 Make sure Redis worker is running: python run_redis_worker.py")
    
    completed_count = 0
    start_time = time.time()
    max_wait = 60  # seconds
    
    while completed_count < len(created_tasks) and (time.time() - start_time) < max_wait:
        print(f"\n--- Checking progress ({completed_count}/{len(created_tasks)} completed) ---")
        
        for task in created_tasks:
            if task.get('checked'):
                continue
                
            response = requests.get(f"{base_url}/tasks/{task['id']}")
            if response.status_code == 200:
                current_task = response.json()
                status = current_task['status']
                
                print(f"Task {task['id']} ({task['task_type']}): {status}")
                
                if status == 'completed':
                    print(f"  ✅ Completed! Result: {current_task.get('result', 'N/A')[:100]}...")
                    task['checked'] = True
                    completed_count += 1
                elif status == 'failed':
                    print(f"  ❌ Failed! Error: {current_task.get('error_message', 'Unknown')}")
                    task['checked'] = True
                    completed_count += 1
                elif status == 'running':
                    print(f"  🔄 Currently processing...")
        
        if completed_count < len(created_tasks):
            print("⏰ Waiting 5 seconds before next check...")
            await asyncio.sleep(5)
    
    # Final results
    print(f"\n🎯 Final Results:")
    response = requests.get(f"{base_url}/tasks/")
    if response.status_code == 200:
        all_tasks = response.json()
        for task in all_tasks:
            if task['id'] in [t['id'] for t in created_tasks]:
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌', 
                    'running': '🔄',
                    'pending': '⏳'
                }.get(task['status'], '❓')
                print(f"   {status_emoji} Task {task['id']}: {task['status']}")
    
    print(f"\n🎉 Redis demo completed!")
    print(f"\n💡 Key improvements with Redis:")
    print(f"   • True process decoupling - API and workers run independently")
    print(f"   • Multiple workers can process from same queue")
    print(f"   • Tasks persist even if workers crash")
    print(f"   • Real-time queue statistics")
    print(f"   • Automatic cleanup of stale tasks")
    print(f"   • Production-ready distributed architecture")


if __name__ == "__main__":
    try:
        asyncio.run(redis_demo())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
