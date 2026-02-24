#!/usr/bin/env python3
"""
Demo script to test the distributed task system via API
"""
import requests
import time
import json


def demo_api():
    """Demonstrate the API functionality"""
    base_url = "http://localhost:8000"
    
    print("🚀 Distributed Task Processing System Demo")
    print("=" * 50)
    
    # Check health
    print("\n1. Checking system health...")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        print(f"✅ System is healthy: {response.json()}")
    else:
        print(f"❌ System health check failed: {response.status_code}")
        return
    
    # Create different types of tasks
    tasks_to_create = [
        {
            "name": "Text Processing",
            "task_type": "text_processing",
            "payload": {"text": "This is a sample text that will be processed by our distributed system!"}
        },
        {
            "name": "AI Summarization", 
            "task_type": "ai_summarization",
            "payload": {"document": "This is a long document about artificial intelligence and machine learning. It contains many technical details and concepts that need to be summarized for easier consumption."}
        },
        {
            "name": "Batch Processing",
            "task_type": "batch_processing", 
            "payload": {"data": ["user1", "user2", "user3", "user4", "user5"]}
        },
        {
            "name": "Image Processing",
            "task_type": "image_processing",
            "payload": {"image_url": "https://example.com/sample-image.jpg"}
        }
    ]
    
    created_tasks = []
    
    # Create tasks
    print("\n2. Creating tasks...")
    for task_info in tasks_to_create:
        print(f"\n📝 Creating {task_info['name']} task...")
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
            print(f"✅ Task created with ID: {task_data['id']}")
            print(f"   Status: {task_data['status']}")
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Error: {response.text}")
    
    # Monitor task progress
    print("\n3. Monitoring task progress...")
    for task in created_tasks:
        task_id = task['id']
        print(f"\n⏳ Monitoring Task {task_id} ({task['task_type']})...")
        
        # Poll for completion
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(f"{base_url}/tasks/{task_id}")
            
            if response.status_code == 200:
                current_task = response.json()
                status = current_task['status']
                
                if status == 'completed':
                    print(f"✅ Task {task_id} completed!")
                    print(f"   Result: {json.dumps(json.loads(current_task['result']), indent=2)}")
                    break
                elif status == 'failed':
                    print(f"❌ Task {task_id} failed!")
                    print(f"   Error: {current_task.get('error_message', 'Unknown error')}")
                    break
                else:
                    print(f"   Status: {status}...")
                    time.sleep(2)
            else:
                print(f"❌ Failed to check task status: {response.status_code}")
                break
        else:
            print(f"⏰ Task {task_id} did not complete within {max_wait} seconds")
    
    # List all tasks
    print("\n4. Listing all tasks...")
    response = requests.get(f"{base_url}/tasks/")
    if response.status_code == 200:
        all_tasks = response.json()
        print(f"📋 Total tasks in system: {len(all_tasks)}")
        for task in all_tasks:
            print(f"   Task {task['id']}: {task['task_type']} - {task['status']}")
    else:
        print(f"❌ Failed to list tasks: {response.status_code}")
    
    print("\n🎉 Demo completed!")
    print("\n💡 Key concepts demonstrated:")
    print("   • Non-blocking API - tasks return immediately")
    print("   • Background processing - workers handle heavy tasks")
    print("   • Status polling - check task progress asynchronously")
    print("   • Multiple task types - flexible processing system")
    print("   • Persistent storage - tasks survive restarts")


if __name__ == "__main__":
    try:
        demo_api()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("💡 Make sure the API server is running: python run_api.py")
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
