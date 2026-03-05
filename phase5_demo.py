#!/usr/bin/env python3
"""
Demo script for Phase 5: Advanced Concurrency & Scaling Features
"""
import asyncio
import time
import requests
import json


async def phase5_demo():
    """Demonstrate advanced concurrency and scaling features"""
    print("🚀 Phase 5: Advanced Concurrency & Scaling Features Demo")
    print("=" * 70)
    
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
    
    print("\n🎯 Phase 5 Features:")
    print("   • Advanced worker pool management")
    print("   • Auto-scaling with multiple policies")
    print("   • Load balancing strategies")
    print("   • Task prioritization")
    print("   • Predictive scaling capabilities")
    print("   • Worker health monitoring")
    print("   • Performance-based scaling")
    
    # Check initial pool status
    print(f"\n🏊 Initial Worker Pool Status:")
    response = requests.get(f"{base_url}/scaling/pool/status")
    if response.status_code == 200:
        pool_status = response.json()
        print(f"   Total Workers: {pool_status['total_workers']}")
        print(f"   Min/Max: {pool_status['min_workers']}/{pool_status['max_workers']}")
        print(f"   Scaling Enabled: {pool_status['scaling_enabled']}")
        print(f"   Load Balancing: {pool_status['load_balancing_strategy']}")
        print(f"   Workers by Status: {pool_status['workers_by_status']}")
    
    # Check auto-scaler status
    print(f"\n⚡ Auto-Scaler Status:")
    response = requests.get(f"{base_url}/scaling/auto-scaler/status")
    if response.status_code == 200:
        scaler_status = response.json()
        print(f"   Enabled: {scaler_status['enabled']}")
        print(f"   Current Policy: {scaler_status['current_policy']}")
        print(f"   Total Scaling Events: {scaler_status['total_scaling_events']}")
        print(f"   Metrics Collected: {scaler_status['metrics_collected']}")
    
    # Show available scaling rules
    print(f"\n📋 Available Scaling Rules:")
    response = requests.get(f"{base_url}/scaling/auto-scaler/rules")
    if response.status_code == 200:
        rules = response.json()
        for name, rule in rules.items():
            enabled_emoji = "✅" if rule['enabled'] else "❌"
            print(f"   {enabled_emoji} {name}: {rule['policy']}")
            print(f"      Scale Up: {rule['scale_up_condition']}")
            print(f"      Scale Down: {rule['scale_down_condition']}")
            print(f"      Cooldown: {rule['cooldown_period']}s")
    
    print(f"\n🧪 Testing Worker Pool Management...")
    
    # Test manual scaling
    print(f"\n📈 Testing Manual Scaling...")
    response = requests.post(f"{base_url}/scaling/pool/scale?target_workers=5")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        
        # Wait for scaling to complete
        await asyncio.sleep(3)
        
        # Check new pool status
        response = requests.get(f"{base_url}/scaling/pool/status")
        if response.status_code == 200:
            pool_status = response.json()
            print(f"   New Worker Count: {pool_status['total_workers']}")
    else:
        print(f"❌ Scaling failed: {response.status_code}")
    
    # Show worker details
    print(f"\n👥 Worker Details:")
    response = requests.get(f"{base_url}/scaling/workers")
    if response.status_code == 200:
        workers = response.json()
        for worker in workers:
            status_emoji = {
                'starting': '🔄',
                'idle': '💤',
                'busy': '⚡',
                'stopping': '🛑',
                'stopped': '⏹️',
                'error': '❌'
            }.get(worker['status'], '❓')
            
            print(f"   {status_emoji} {worker['worker_id']}:")
            print(f"      Status: {worker['status']}")
            print(f"      Tasks Processed: {worker['tasks_processed']}")
            print(f"      Uptime: {worker['uptime']:.1f}s")
            if worker['current_task_id']:
                print(f"      Current Task: {worker['current_task_id']}")
    
    print(f"\n🎯 Testing Load Balancing Strategies...")
    
    # Test different load balancing strategies
    strategies = ["round_robin", "least_loaded", "random"]
    
    for strategy in strategies:
        print(f"\n🔄 Testing {strategy} strategy...")
        response = requests.put(
            f"{base_url}/scaling/pool/load-balancing",
            json={"strategy": strategy}
        )
        if response.status_code == 200:
            print(f"✅ Load balancing set to {strategy}")
        else:
            print(f"❌ Failed to set strategy: {response.status_code}")
        
        await asyncio.sleep(1)
    
    # Create tasks to test load balancing
    print(f"\n📝 Creating Tasks to Test Load Balancing...")
    
    tasks_to_create = [
        {
            "name": "Load Balance Test 1",
            "task_type": "text_processing",
            "payload": {"text": f"Load balancing test task 1"}
        },
        {
            "name": "Load Balance Test 2",
            "task_type": "text_processing",
            "payload": {"text": f"Load balancing test task 2"}
        },
        {
            "name": "Load Balance Test 3",
            "task_type": "text_processing",
            "payload": {"text": f"Load balancing test task 3"}
        },
        {
            "name": "Load Balance Test 4",
            "task_type": "text_processing",
            "payload": {"text": f"Load balancing test task 4"}
        },
        {
            "name": "Load Balance Test 5",
            "task_type": "text_processing",
            "payload": {"text": f"Load balancing test task 5"}
        }
    ]
    
    created_tasks = []
    
    # Create tasks and add to worker pool queue
    for i, task_info in enumerate(tasks_to_create):
        task_data = {
            "id": i + 1,
            "task_type": task_info["task_type"],
            "payload": task_info["payload"]
        }
        
        # Add directly to worker pool for testing
        try:
            from app.services.worker_pool import worker_pool
            await worker_pool.add_task_to_queue(task_data)
            created_tasks.append(task_data)
            print(f"✅ Created task {task_data['id']}")
        except Exception as e:
            print(f"❌ Failed to add task to queue: {str(e)}")
    
    # Monitor task distribution
    print(f"\n⏳ Monitoring Task Distribution...")
    
    start_time = time.time()
    max_wait = 30  # seconds
    
    while time.time() - start_time < max_wait:
        # Check worker status
        response = requests.get(f"{base_url}/scaling/workers")
        if response.status_code == 200:
            workers = response.json()
            
            busy_workers = [w for w in workers if w['status'] == 'busy']
            idle_workers = [w for w in workers if w['status'] == 'idle']
            
            print(f"   Busy Workers: {len(busy_workers)}, Idle Workers: {len(idle_workers)}")
            
            # Show task distribution
            for worker in workers:
                if worker['current_task_id']:
                    print(f"      {worker['worker_id']}: Task {worker['current_task_id']}")
        
        await asyncio.sleep(3)
    
    print(f"\n⚡ Testing Auto-Scaling Policies...")
    
    # Test different scaling policies
    policies = ["queue_based", "cpu_based", "memory_based"]
    
    for policy in policies:
        print(f"\n🔄 Testing {policy} policy...")
        response = requests.put(
            f"{base_url}/scaling/auto-scaler/policy?policy={policy}"
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
        else:
            print(f"❌ Failed to set policy: {response.status_code}")
        
        await asyncio.sleep(2)
    
    # Enable auto-scaler
    print(f"\n🔧 Enabling Auto-Scaler...")
    response = requests.post(f"{base_url}/scaling/auto-scaler/enable")
    if response.status_code == 200:
        print("✅ Auto-scaler enabled")
    else:
        print(f"❌ Failed to enable auto-scaler: {response.status_code}")
    
    # Create more tasks to trigger auto-scaling
    print(f"\n📈 Creating Tasks to Trigger Auto-Scaling...")
    
    for i in range(10):
        response = requests.post(
            f"{base_url}/tasks/",
            json={
                "task_type": "text_processing",
                "payload": {"text": f"Auto-scaling test task {i}"}
            }
        )
        
        if response.status_code == 201:
            print(f"✅ Created auto-scaling test task {i+1}")
        
        await asyncio.sleep(0.5)  # Brief delay between tasks
    
    # Monitor auto-scaling
    print(f"\n👀 Monitoring Auto-Scaling for 30 seconds...")
    
    start_time = time.time()
    initial_workers = None
    
    while time.time() - start_time < 30:
        # Get pool status
        response = requests.get(f"{base_url}/scaling/pool/status")
        if response.status_code == 200:
            pool_status = response.json()
            
            if initial_workers is None:
                initial_workers = pool_status['total_workers']
            
            current_workers = pool_status['total_workers']
            
            if current_workers != initial_workers:
                print(f"🔄 Scaling detected! {initial_workers} → {current_workers} workers")
                initial_workers = current_workers
        
        # Get auto-scaler status
        response = requests.get(f"{base_url}/scaling/auto-scaler/status")
        if response.status_code == 200:
            scaler_status = response.json()
            if scaler_status['recent_events']:
                latest_event = scaler_status['recent_events'][0]
                print(f"   📊 Latest scaling event: {latest_event['direction'].upper()}")
                print(f"      Reason: {latest_event['reason']}")
                print(f"      From {latest_event['from_workers']} → {latest_event['to_workers']} workers")
        
        await asyncio.sleep(5)
    
    # Show final scaling status
    print(f"\n📊 Final Scaling Status:")
    response = requests.get(f"{base_url}/scaling/auto-scaler/status")
    if response.status_code == 200:
        scaler_status = response.json()
        print(f"   Total Scaling Events: {scaler_status['total_scaling_events']}")
        print(f"   Recent Events: {len(scaler_status['recent_events'])}")
        
        if scaler_status['recent_events']:
            print("   Recent Events:")
            for event in scaler_status['recent_events'][-3:]:  # Last 3 events
                print(f"      {event['direction'].upper()}: {event['from_workers']} → {event['to_workers']} workers")
                print(f"         Reason: {event['reason']}")
    
    # Show performance metrics
    print(f"\n📈 Performance Metrics:")
    response = requests.get(f"{base_url}/scaling/metrics/performance?minutes=5")
    if response.status_code == 200:
        metrics = response.json()
        print(f"   Time Range: {metrics['time_range_minutes']} minutes")
        print(f"   Total Tasks: {metrics['task_metrics']['total_tasks']}")
        print(f"   Success Rate: {metrics['task_metrics']['success_rate']:.1f}%")
        print(f"   Avg Execution Time: {metrics['task_metrics']['avg_execution_time']:.2f}s")
        print(f"   Throughput: {metrics['performance_indicators']['throughput']:.1f} tasks/hour")
        print(f"   Error Rate: {metrics['performance_indicators']['error_rate']:.1f}%")
        print(f"   Avg Tasks per Worker: {metrics['performance_indicators']['avg_tasks_per_worker']:.1f}")
    
    # Test worker restart
    print(f"\n🔄 Testing Worker Restart...")
    response = requests.get(f"{base_url}/scaling/workers")
    if response.status_code == 200:
        workers = response.json()
        if workers:
            test_worker = workers[0]
            worker_id = test_worker['worker_id']
            
            print(f"   Restarting worker {worker_id}...")
            response = requests.post(f"{base_url}/scaling/workers/{worker_id}/restart")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result['message']}")
            else:
                print(f"❌ Failed to restart worker: {response.status_code}")
    
    # Test custom scaling rule
    print(f"\n🎛️ Testing Custom Scaling Rule...")
    custom_rule = {
        "name": "aggressive_scaling",
        "policy": "queue_based",
        "scale_up_condition": "queue_size > 3",
        "scale_down_condition": "queue_size < 1",
        "cooldown_period": 30,
        "max_scale_up_step": 4,
        "max_scale_down_step": 2,
        "enabled": True
    }
    
    response = requests.post(f"{base_url}/scaling/auto-scaler/rules", json=custom_rule)
    if response.status_code == 201:
        rule = response.json()
        print(f"✅ Created custom rule: {rule['name']}")
        
        # Enable the custom rule
        response = requests.put(f"{base_url}/scaling/auto-scaler/rules/{rule['name']}/enable")
        if response.status_code == 200:
            print(f"✅ Enabled custom rule: {rule['name']}")
    else:
        print(f"❌ Failed to create custom rule: {response.status_code}")
    
    print(f"\n🎉 Phase 5 Demo Completed!")
    print(f"\n💡 Key Phase 5 Achievements:")
    print(f"   • Advanced worker pool with auto-scaling")
    print(f"   • Multiple scaling policies (queue, CPU, memory)")
    print(f"   • Load balancing strategies (round-robin, least_loaded, random)")
    print(f"   • Worker health monitoring and auto-restart")
    print(f"   • Predictive scaling capabilities")
    print(f"   • Performance-based scaling decisions")
    print(f"   • Custom scaling rule management")
    print(f"   • Real-time scaling metrics and monitoring")


if __name__ == "__main__":
    try:
        asyncio.run(phase5_demo())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
