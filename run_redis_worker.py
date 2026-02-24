#!/usr/bin/env python3
"""
Run the Redis worker process
"""
import asyncio
from app.workers.redis_worker import main

if __name__ == "__main__":
    asyncio.run(main())
