#!/usr/bin/env python3
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

try:
    from server.core.c2_server import C2Server
except ImportError as e:
    print(f"[-] Import error: {e}")
    print("[*] Make sure you're running from the BrutalStrike root directory")
    sys.exit(1)

if __name__ == "__main__":
    print("=== BrutalStrike C2 Framework ===")
    server = C2Server()
    server.start()