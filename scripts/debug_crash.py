import sys
import traceback

try:
    from main import GameEngine
    print("Attempting to init GameEngine...")
    engine = GameEngine()
    print("GameEngine initialized successfully.")
except Exception:
    with open("crash_log.txt", "w") as f:
        traceback.print_exc(file=f)
    print("Crash log written to crash_log.txt")
