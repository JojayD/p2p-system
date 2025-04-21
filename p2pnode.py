import uuid
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import random
import socket
import time
import threading

returnVals = ['good', 'bad']

class P2PNode:
    def __init__(self, port, bootstrap_url=None):
        # Assign a unique identifier to this node
        self.id = str(uuid.uuid4())
        self.port = port
        self.peers = {}  # Dictionary to store information about peer nodes
        self.keyvalue = {} # The in-memory storage
        self.bootstrap_url = bootstrap_url

        # Initialize Flask application
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()

    def setup_routes(self):
        """Configure the API endpoints for this node"""

        @self.app.route('/', methods=['GET'])
        def root():
          """Return basic information when accessing the root URL"""
          return jsonify({
              "message": f"Node {self.id} is running!"
          })

        @self.app.route('/status', methods=['GET'])
        def status():
            """Return basic information about this node"""
            return jsonify({
                'id': self.id,
                'port': self.port,
                'peers': len(self.peers),
                "message": "Node is running"
            }), 200

        @self.app.route('/register', methods=['POST'])
        def register_peer():
            """Register a new peer to this node"""
            data = request.get_json()

            if not data or 'id' not in data or 'address' not in data:
                return jsonify({'error': 'Invalid peer data'}), 400

            peer_id = data['id']
            peer_address = data['address']

            # Add the peer to our list
            if peer_id != self.id:  # Don't add ourselves
                self.peers[peer_id] = peer_address
                print(f"Registered new peer: {peer_id} at {peer_address}")

            return jsonify({'status': 'success', 'peers': len(self.peers)}), 200


        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            """Return the list of peers"""
            return jsonify({
                'peers': self.peers
            })

        @self.app.route('/message', methods=['POST'])
        def receive_message():
            """Handle incoming messages from peers"""
            data = request.get_json()

            if not data or 'sender' not in data or 'msg' not in data:
                return jsonify({'error': 'Invalid message format'}), 400

            sender = data["sender"]
            message = data["msg"]
            node_name = socket.gethostname()

            response = f"Received message from {sender}: {message}. "

            response += f"This is {node_name}, It is a {random.choice(returnVals)} day"

            # You could add logic here to forward the message to other peers
            # or process it in some way
            

            return jsonify({'status': 'received',
                            'msg': message,
                            'from': sender,
                            'current_node': node_name,
                            'reply': response})
    
        @self.app.route('/upload', methods=['POST'])
        def upload_file():
            """Upload a file to the container"""

            # An example link would be something like
            # curl -F 'file=@localFileName' http://localhost:{numeric numbers}/upload

            file = request.files.get('file')

            #determine if the file exists or not
            if file:
                file.save(f"/app/storage/{file.filename}")
            else:
                return "File name is missing", 400
            
            return f"{file.filename} has been uploaded to the shared volume", 200
        
        @self.app.route('/download/<filename>', methods=['GET'])
        def retrieve_file(filename):
            """Allow the local user to download the file that is stored 
            inside /app/storage by using something like 
            http://localhost:6969/download/filename """

            return send_from_directory("/app/storage", filename)
        
        @self.app.route('/kv', methods=['POST'])
        def store_KVPairs():
            """Store the key-value pairs that a Anon sends via a curl json message"""

            data = request.get_json()

            #Check if the info sent is correct and the json / json content is there
            if not data:
                return jsonify({'status': 'incomplete', 'message': 'No values passed'}), 400
            if 'key' not in data:
                return jsonify({'status': 'incomplete', 'message': 'missing the key info'}), 400
            if 'value' not in data:
                return jsonify({'status': 'incomplete', 'message': 'missing the value info'}), 400
            
            #retrieve the values out
            key = data['key']
            value = data['value']

            self.keyvalue[key] = value

            return jsonify({'status': 'success', 'message': f'Stored the {key}:{value} pair'}), 200
        
        @self.app.route('/kv/<key>', methods=['GET'])
        def get_KVPair(key):
            """Return the value based on the key"""

            #See if the key actually exists in the dictionary
            value = self.keyvalue.get(key, None)
            if value is not None:
                return value, 200
            else:
                return "Incorrect Key", 400


        

    def start(self):
        """Start the HTTP server"""
        
        print(f"Starting P2P node with ID: {self.id}")
        print(f"Node is running on http://localhost:{self.port}")

        # If we have a bootstrap node, register with it
        if self.bootstrap_url:
            time.sleep(5)
            self.register_with_bootstrap()

        # Use threading so that the send message function will actually run
        flask_thread = threading.Thread(target=self.app.run, kwargs={
            'host': '0.0.0.0',
            'port': self.port,
            'debug': False,
            'use_reloader': False
        })
        flask_thread.start()

        for x in range(3):
            self.send_message()
        

    def register_with_bootstrap(self):
        """Register this node with the bootstrap node"""
        # For Docker networking, use container name instead of localhost
        container_name = f"node{self.port-8000}" if self.port != 8000 else "bootstrap"
        my_address = f"http://{container_name}:{self.port}"

        try:
            response = requests.post(
                f"{self.bootstrap_url}/register",
                json={"id": self.id, "address": my_address},
                timeout=5
            )
            if response.status_code == 200:
                print(
                    f"Successfully registered with bootstrap node at {self.bootstrap_url}")
                # Get the list of peers from the bootstrap node
                self.get_peers_from_bootstrap()
            else:
                print(
                    f"Failed to register with bootstrap node: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error connecting to bootstrap node: {e}")

    def get_peers_from_bootstrap(self):
        """Get the list of peers from the bootstrap node"""
        try:
            response = requests.get(f"{self.bootstrap_url}/peers", timeout=5)
            if response.status_code == 200:
                peer_list = response.json().get('peers', {})
                for peer_id, peer_address in peer_list.items():
                    if peer_id != self.id:  # Don't add ourselves
                        self.peers[peer_id] = peer_address
                print(f"Got {len(peer_list)} peers from bootstrap node")
        except requests.RequestException as e:
            print(f"Error getting peers from bootstrap node: {e}")


    def node_active(self, url, retries=8):
        """Trying to check if node address is active with Flask or not"""
        for i in range(retries):
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(2)
        return False
    
    def send_message(self):
        """Sending a message to a random peer in the peerlist"""

        if not self.peers:
            return

        #Retrieves a random key, value pair from dictionary
        peer_id, peer_address = random.choice(list(self.peers.items()))

        try: 
            #variables used in post request
            values = peer_address.split(":")
            node_name = socket.gethostname()
            alive = f"{peer_address}/status"
            url = f"{peer_address}/message"

            # alive = f"http://localhost:{values[2]}/status"
            # url = f"http://localhost:{values[2]}/message"
            

            # r = requests.get(alive, timeout=5)
            
            if self.node_active(alive):
                print(f"This is {node_name}, Sending a message to {peer_id} at {peer_address}")
                print(f"Sending to {url}")

                response = requests.post(url, json={"sender": node_name, "msg": f"This is {node_name}, How is your day? "})
                print(f"Got response: {response.content}")

        except requests.RequestException as e:
            print(f"Error connecting to node: {e}")

    



# Example usage
if __name__ == "__main__":
    import sys

    # Check if we should be a bootstrap node or regular node
    if len(sys.argv) > 1 and sys.argv[1] == "--bootstrap":
        # Start as a bootstrap node (no bootstrap URL)
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        node = P2PNode(port=port)
        print("Starting as BOOTSTRAP node")
        # node.app.run(host='0.0.0.0', port = node.port)
    else:
        # Start as a regular node with bootstrap URL
        # Changed default from 8001 to 8000
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
        bootstrap = sys.argv[2] if len(
            sys.argv) > 2 else "http://localhost:8000"
        node = P2PNode(port=port, bootstrap_url=bootstrap)
        print(
            f"Starting as regular node, connecting to bootstrap: {bootstrap}")

    node.start()
