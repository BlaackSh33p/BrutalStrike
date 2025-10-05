"""
Network Scanner Module
"""

MODULE_INFO = {
    'name': 'Network Scanner',
    'description': 'Scan local network for hosts and services',
    'category': 'Discovery',
    'platforms': ['windows', 'linux', 'macos'],
    'privileges': 'user',
}

def execute(arguments, agent_context):
    try:
        import subprocess
        import platform
        
        target = arguments.get('target', 'localhost')
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows ping
            cmd = f'ping -n 1 {target}'
        else:
            # Linux/Mac ping
            cmd = f'ping -c 1 {target}'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"Host {target} is reachable\n{result.stdout}"
        else:
            return f"Host {target} is not reachable\n{result.stderr}"
            
    except Exception as e:
        return f"Network scan failed: {str(e)}"