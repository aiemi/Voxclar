"""PyInstaller entry point for Voxclar Local Engine."""
import asyncio
import sys
import os

# Ensure src package is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.server import main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(main())
