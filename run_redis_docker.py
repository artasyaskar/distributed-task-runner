#!/usr/bin/env python3
"""
Simple script to run Redis with Docker for Phase 5 testing
"""
import subprocess
import sys
import time

def main():
    print("🚀 Starting Redis with Docker...")
    
    try:
        # Start Redis with Docker
        process = subprocess.Popen([
            "docker-compose", "-f", "docker-compose-redis.yml", "up", "-d"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("✅ Redis starting...")
        
        # Wait for Redis to be ready
        print("⏳ Waiting for Redis to be ready...")
        time.sleep(10)
        
        # Test Redis connection
        import redis
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis is ready and connected!")
            print(f"📊 Redis version: {r.info()['redis_version']}")
            print(f"🔧 Redis running on localhost:6379")
            
            print("\n🎉 Redis is now running for Phase 5 testing!")
            print("📝 Your distributed task system can now use Redis for:")
            print("   • Message queuing")
            print("   • Task distribution")
            print("   • Worker coordination")
            print("   • Persistent storage")
            
            print("\n💡 Keep this terminal open while testing Phase 5")
            print("   Press Ctrl+C to stop Redis")
            
            # Keep the process running
            process.wait()
            
        except Exception as e:
            print(f"❌ Redis connection test failed: {str(e}")
            return 1
            
    except Exception as e:
        print(f"❌ Failed to start Redis: {str(e)}")
        return 1
    
    finally:
        # Cleanup
        print("\n🛑 Stopping Redis...")
        subprocess.run(["docker-compose", "-f", "docker-compose-redis.yml", "down"], 
                      capture_output=True, text=True)
        print("✅ Redis stopped")

if __name__ == "__main__":
    main()
