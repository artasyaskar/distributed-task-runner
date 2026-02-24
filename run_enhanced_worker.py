#!/usr/bin/env python3
"""
Run the enhanced worker process with advanced retry logic
"""
import asyncio
from app.workers.enhanced_worker import main

if __name__ == "__main__":
    asyncio.run(main())
