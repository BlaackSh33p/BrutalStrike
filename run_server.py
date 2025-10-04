#!/usr/bin/env python3
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.core.server import BrutalStrike

if __name__ == "__main__":
    server = C2Server(host='0.0.0.0', port=4444)
    server.start()