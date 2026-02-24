#!/usr/bin/env python3
"""
Run the worker process
"""
import asyncio
from app.workers.worker import main

if __name__ == "__main__":
    asyncio.run(main())
