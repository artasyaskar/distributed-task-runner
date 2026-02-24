#!/usr/bin/env python3
"""
Integrated demo showing API + Worker in same process
"""
import asyncio
import json
from app.services.task_queue import task_queue
from app.services.task_executor import task_executor
from app.workers.worker import Worker


async def integrated_demo():
    """Demo with API and worker working together"""
    print("🚀 Integrated Distributed Task System Demo")
    print("=" * 60)
    
    # Initialize the task queue
    await task_queue.initialize()
    print("✅ Task queue initialized")
    
    # Create tasks
    print("\n📝 Creating tasks...")
    tasks_to_create = [
        {
            "name": "Text Processing",
            "task_type": "text_processing",
            "payload": {"text": "This text will be processed asynchronously!"}
        },
        {
            "name": "AI Summarization",
            "task_type": "ai_summarization", 
            "payload": {"document": "Long document about AI and ML that needs summarization."}
        },
        {
            "name": "Batch Processing",
            "task_type": "batch_processing",
            "payload": {"data": ["item1", "item2", "item3", "item4", "item5"]}
        }
    ]
    
    created_tasks = []
    for task_info in tasks_to_create:
        task = await task_queue.create_task(
            task_info["task_type"],
            task_info["payload"]
        )
        created_tasks.append(task)
        print(f"✅ Created {task_info['name']} task (ID: {task.id})")
    
    # Start worker to process tasks
    print("\n🔄 Starting worker to process tasks...")
    worker = Worker()
    
    # Process a few tasks
    tasks_processed = 0
    max_tasks = len(created_tasks)
    
    while tasks_processed < max_tasks:
        print(f"\n⏳ Waiting for next task...")
        task = await task_queue.get_next_task()
        
        if task:
            print(f"🎯 Processing task {task.id} ({task.task_type})...")
            try:
                result = await task_executor.execute_task(task)
                print(f"✅ Task {task.id} completed successfully!")
                print(f"📊 Result: {json.dumps(result, indent=2)}")
                tasks_processed += 1
            except Exception as e:
                print(f"❌ Task {task.id} failed: {str(e)}")
                tasks_processed += 1
        else:
            print("💤 No tasks available, waiting...")
            await asyncio.sleep(1)
    
    print(f"\n🎉 All {tasks_processed} tasks processed!")
    
    # Show final task states
    print("\n📋 Final task states:")
    for task in created_tasks:
        updated_task = await task_queue.get_task(task.id)
        print(f"   Task {task.id}: {updated_task.status.value}")
        if updated_task.result:
            result = json.loads(updated_task.result)
            print(f"   Processing time: {result.get('processing_time', 'N/A')}s")
    
    print("\n💡 Key concepts demonstrated:")
    print("   • Async task creation and processing")
    print("   • Background worker execution")
    print("   • Task state management (pending → running → completed)")
    print("   • Persistent task storage")
    print("   • Different task types with different processing times")
    print("   • Fault tolerance and error handling")


if __name__ == "__main__":
    asyncio.run(integrated_demo())
