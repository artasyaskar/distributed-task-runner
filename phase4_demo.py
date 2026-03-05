#!/usr/bin/env python3
"""
Demo script for Phase 4: Advanced Logging & Monitoring
"""
import asyncio
import time
import requests
import json


async def phase4_demo():
    """Demonstrate advanced logging and monitoring capabilities"""
    print("🚀 Phase 4: Advanced Logging & Monitoring Demo")
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
    
    print("\n🎯 Phase 4 Features:")
    print("   • Enhanced structured logging with correlation")
    print("   • Comprehensive metrics collection")
    print("   • Real-time system monitoring")
    print("   • Performance analysis and alerting")
    print("   • Health checks for all components")
    print("   • Log aggregation and analysis")
    
    # Show system health
    print(f"\n🏥 System Health Check:")
    response = requests.get(f"{base_url}/monitoring/health")
    if response.status_code == 200:
        health = response.json()
        print(f"   Overall Status: {health['overall'].upper()}")
        print(f"   Components: {len(health['components'])}")
        print(f"   Issues: {len(health['issues'])}")
        
        for component, status in health['components'].items():
            status_emoji = "🟢" if status['status'] == 'healthy' else "🟡" if status['status'] == 'warning' else "🔴"
            print(f"   {status_emoji} {component.title()}: {status['status']}")
    
    # Show system overview
    print(f"\n📊 System Overview:")
    response = requests.get(f"{base_url}/monitoring/status/overview")
    if response.status_code == 200:
        overview = response.json()
        print(f"   System Status: {overview['system_status'].upper()}")
        print(f"   Total Tasks: {overview['task_summary']['total_tasks']}")
        print(f"   Success Rate: {overview['task_summary']['success_rate']}%")
        print(f"   CPU Usage: {overview['current_performance']['cpu_usage']:.1f}%")
        print(f"   Memory Usage: {overview['current_performance']['memory_usage']:.1f}%")
        print(f"   Queue Size: {overview['current_performance']['queue_size']}")
        print(f"   Active Workers: {overview['current_performance']['active_workers']}")
        print(f"   Critical Alerts: {overview['recent_issues']['critical_alerts']}")
    
    # Show logging statistics
    print(f"\n📝 Logging System Statistics:")
    response = requests.get(f"{base_url}/monitoring/logs/stats")
    if response.status_code == 200:
        log_stats = response.json()
        print(f"   Log Level: {log_stats['log_level']}")
        print(f"   Log Format: {log_stats['log_format']}")
        print(f"   Log Directory: {log_stats['log_directory']}")
        print(f"   Active Handlers: {log_stats['active_handlers']}")
        print(f"   Component Loggers: {log_stats['component_loggers']}")
    
    # Show alert thresholds
    print(f"\n⚠️ Alert Thresholds:")
    response = requests.get(f"{base_url}/monitoring/alerts/thresholds")
    if response.status_code == 200:
        thresholds = response.json()
        print(f"   CPU Warning: {thresholds['cpu_warning']:.0%}")
        print(f"   CPU Critical: {thresholds['cpu_critical']:.0%}")
        print(f"   Memory Warning: {thresholds['memory_warning']:.0%}")
        print(f"   Memory Critical: {thresholds['memory_critical']:.0%}")
        print(f"   Queue Warning: {thresholds['queue_size_warning']} tasks")
        print(f"   Queue Critical: {thresholds['queue_size_critical']} tasks")
        print(f"   Failure Rate Warning: {thresholds['failure_rate_warning']:.0%}")
        print(f"   Failure Rate Critical: {thresholds['failure_rate_critical']:.0%}")
    
    print(f"\n🧪 Creating Tasks to Generate Monitoring Data...")
    
    # Create tasks to generate monitoring data
    tasks_to_create = [
        {
            "name": "Text Processing Task",
            "task_type": "text_processing",
            "payload": {"text": "This task will generate monitoring data for our Phase 4 demo"}
        },
        {
            "name": "AI Summarization Task",
            "task_type": "ai_summarization",
            "payload": {"document": "This document will be processed to demonstrate monitoring capabilities"}
        },
        {
            "name": "Batch Processing Task",
            "task_type": "batch_processing",
            "payload": {"data": [f"monitoring_item_{i}" for i in range(5)]}
        },
        {
            "name": "Image Processing Task",
            "task_type": "image_processing",
            "payload": {"image_url": "https://example.com/monitoring-demo.jpg"}
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
    
    print(f"\n⏳ Monitoring Task Execution...")
    print("💡 Make sure enhanced worker is running: python run_enhanced_worker.py")
    
    # Monitor tasks and collect metrics
    completed_count = 0
    start_time = time.time()
    max_wait = 30  # seconds
    
    while completed_count < len(created_tasks) and (time.time() - start_time) < max_wait:
        print(f"\n--- Monitoring Progress ({completed_count}/{len(created_tasks)} completed) ---")
        
        # Check system metrics
        response = requests.get(f"{base_url}/monitoring/metrics/system?minutes=1")
        if response.status_code == 200:
            metrics = response.json()
            if metrics:
                print(f"   📈 System Metrics (last 1 min):")
                print(f"      Avg CPU: {metrics.get('avg_cpu_usage', 0):.1%}")
                print(f"      Avg Memory: {metrics.get('avg_memory_usage', 0):.1%}")
                print(f"      Avg Queue: {metrics.get('avg_queue_size', 0):.1f}")
                print(f"      Avg Workers: {metrics.get('avg_active_workers', 0):.1f}")
        
        # Check task metrics
        response = requests.get(f"{base_url}/monitoring/metrics/tasks")
        if response.status_code == 200:
            task_metrics = response.json()
            if task_metrics:
                print(f"   📋 Task Metrics:")
                for task_type, stats in list(task_metrics.items())[:2]:  # Show first 2
                    print(f"      {task_type}: {stats.get('total', 0)} total, {stats.get('success_rate', 0):.1%} success")
        
        # Check alerts
        response = requests.get(f"{base_url}/monitoring/alerts?minutes=1")
        if response.status_code == 200:
            alerts_data = response.json()
            if alerts_data['alerts']:
                print(f"   🚨 Recent Alerts: {len(alerts_data['alerts'])}")
                for alert in alerts_data['alerts'][:2]:  # Show first 2
                    print(f"      {alert['severity'].upper()}: {alert['message']}")
        
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
                    task['checked'] = True
                    completed_count += 1
                elif status == 'running':
                    print(f"   ⚡ Task {task['id']} ({task['task_type']}): RUNNING")
        
        if completed_count < len(created_tasks):
            print("⏰ Waiting 3 seconds before next check...")
            await asyncio.sleep(3)
    
    # Show comprehensive dashboard
    print(f"\n📊 Comprehensive Monitoring Dashboard:")
    response = requests.get(f"{base_url}/monitoring/dashboard")
    if response.status_code == 200:
        dashboard = response.json()
        
        print(f"   🏥 System Health: {dashboard['system_health']['overall'].upper()}")
        
        if dashboard['task_statistics']:
            print(f"   📋 Task Statistics:")
            for task_type, stats in list(dashboard['task_statistics'].items())[:2]:
                print(f"      {task_type}: {stats.get('total', 0)} tasks, {stats.get('success_rate', 0):.1%} success")
        
        if dashboard['system_metrics']:
            metrics = dashboard['system_metrics']
            print(f"   📈 System Performance:")
            print(f"      CPU: {metrics.get('avg_cpu_usage', 0):.1%}, Memory: {metrics.get('avg_memory_usage', 0):.1%}")
            print(f"      Queue: {metrics.get('avg_queue_size', 0):.1f}, Workers: {metrics.get('avg_active_workers', 0):.1f}")
        
        if dashboard['recent_alerts']:
            print(f"   🚨 Recent Alerts: {len(dashboard['recent_alerts'])}")
        
        if dashboard['error_patterns']:
            print(f"   💀 Error Patterns: {len(dashboard['error_patterns'])} types")
    
    # Show performance summary
    print(f"\n📈 Performance Summary:")
    response = requests.get(f"{base_url}/monitoring/performance/summary")
    if response.status_code == 200:
        summary = response.json()
        print(f"   Performance Summary Generated: {summary['summary_generated']}")
        
        for task_type, stats in summary['task_types'].items():
            print(f"   📊 {task_type}:")
            print(f"      Executions: {stats['total_executions']}")
            print(f"      Success Rate: {stats['success_rate']:.1f}%")
            print(f"      Avg Time: {stats['avg_execution_time']:.2f}s")
            print(f"      Retry Rate: {stats['retry_rate']:.1f}%")
    
    # Show recent logs
    print(f"\n📝 Recent Log Entries:")
    response = requests.get(f"{base_url}/monitoring/logs/recent?lines=5")
    if response.status_code == 200:
        logs_data = response.json()
        if logs_data.get('logs'):
            print(f"   Last {len(logs_data['logs'])} log entries from {logs_data['log_file']}:")
            for i, log_line in enumerate(logs_data['logs'][-3:], 1):  # Show last 3
                print(f"   {i}. {log_line}")
        else:
            print("   No recent logs found")
    
    # Demonstrate alert threshold adjustment
    print(f"\n⚙️ Demonstrating Alert Threshold Adjustment...")
    new_thresholds = {
        "cpu_warning": 0.6,
        "queue_size_warning": 25,
        "failure_rate_warning": 0.03
    }
    
    response = requests.put(f"{base_url}/monitoring/alerts/thresholds", json=new_thresholds)
    if response.status_code == 200:
        print("✅ Alert thresholds updated successfully")
        print(f"   CPU Warning: {new_thresholds['cpu_warning']:.0%}")
        print(f"   Queue Warning: {new_thresholds['queue_size_warning']} tasks")
        print(f"   Failure Rate Warning: {new_thresholds['failure_rate_warning']:.0%}")
    
    print(f"\n🎉 Phase 4 Demo Completed!")
    print(f"\n💡 Key Phase 4 Achievements:")
    print(f"   • Structured logging with correlation IDs")
    print(f"   • Comprehensive metrics collection")
    print(f"   • Real-time system health monitoring")
    print(f"   • Performance analysis and trending")
    print(f"   • Intelligent alerting with thresholds")
    print(f"   • Component-level health checks")
    print(f"   • Log aggregation and analysis")
    print(f"   • Production-ready observability")


if __name__ == "__main__":
    try:
        asyncio.run(phase4_demo())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
