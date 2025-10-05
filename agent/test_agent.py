#!/usr/bin/env python3
from http_agent import HTTPAgent

def main():
    # Test with different server URLs
    servers = [
        "http://127.0.0.1:8080",      # Localhost
        "http://192.168.100.2:8080",   # Your Kali IP
        "http://172.17.0.1:8080",      # Docker bridge
    ]
    
    for server in servers:
        try:
            print(f"[*] Testing connection to {server}")
            agent = HTTPAgent(server_url=server, sleep_interval=30)
            agent.run()
            break
        except Exception as e:
            print(f"[-] Failed with {server}: {e}")
            continue

if __name__ == "__main__":
    main()