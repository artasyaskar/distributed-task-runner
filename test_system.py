#!/usr/bin/env python3
"""
Integration test for the distributed task system
"""
import asyncio
import json
from app.services.task_queue import task_queue
from app.services.task_executor import task_executor
from app.workers.worker import Worker


async def test_system():
    """Test the complete system"""
    print("🚀 Starting Distributed Task System Test")
    
    # Initialize the task queue
    await task_queue.initialize()
    print("✅ Task queue initialized")
    
    # Create a test task
    task = await task_queue.create_task(
        "text_processing", 
        {"text": "This is a test for our distributed task system!"}
    )
    print(f"✅ Created task {task.id} with status {task.status.value}")
    
    # Create and start worker
    worker = Worker()
    
    # Process the task manually for this test
    print("🔄 Processing task...")
    try:
        result = await task_executor.execute_task(task)
        print(f"✅ Task completed successfully!")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
        
        # Check final task status
        updated_task = await task_queue.get_task(task.id)
        print(f"📋 Final task status: {updated_task.status.value}")
        
    except Exception as e:
        print(f"❌ Task failed: {str(e)}")
    
    print("\n🎉 System test completed!")
    
    # Test different task types
    print("\n🧪 Testing different task types...")
    
    task_types = [
        ("ai_summarization", {"document": "This is a long document that needs summarization."}),
        ("batch_processing", {"data": ["item1", "item2", "item3"]}),
        ("image_processing", {"image_url": "http://example.com/image.jpg"})
    ]
    
    for task_type, payload in task_types:
        print(f"\n📝 Testing {task_type}...")
        task = await task_queue.create_task(task_type, payload)
        print(f"✅ Created task {task.id}")
        
        try:
            result = await task_executor.execute_task(task)
            print(f"✅ {task_type} completed successfully")
        except Exception as e:
            print(f"❌ {task_type} failed: {str(e)}")
    
    print("\n🏁 All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_system())
