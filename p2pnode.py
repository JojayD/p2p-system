import uuid
import requests
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import random
import socket
import time
import threading
import hashlib, json, os

returnVals = ['good', 'bad']


class P2PNode:
    def __init__(self, port, bootstrap_url=None):
        # Assign a unique identifier to this node
        self.id = str(uuid.uuid4())
        self.port = port
        self.peers = {}  # Dictionary to store information about peer nodes
        self.keyvalue = {}  # The in-memory storage
        self.bootstrap_url = bootstrap_url
        self.stats = {"sent": 0, "recv": 0}
        self.node_hash = self.sha1_int(self.id)
        self.address = f"http://{socket.gethostname()}:{self.port}"

        # Initialize Flask application
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()

    def print_value(self, key):
        print(key)

    def hash_key_to_node(self, key):
        # hash key with SHA-1 and choose from sorted addresses
        key_str = str(key)
        h_int = int(hashlib.sha1(key_str.encode()).hexdigest(), 16)
        # build a stable, sorted list of node addresses
        my_container = f"node{self.port-8000}" if self.port != 8000 else "bootstrap"
        my_address = f"http://{my_container}:{self.port}"
        nodes = sorted(list(self.peers.values()) + [my_address])
        idx = h_int % len(nodes)
        resp_addr = nodes[idx]
        print(
            f"DEBUG: key={key} idx={idx}/{len(nodes)} -> {resp_addr}", flush=True)
        return resp_addr

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
            
            # metrics
            self.stats["recv"] += 1

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

            # determine if the file exists or not
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

            # Check if the info sent is correct and the json / json content is there
            if not data:
                return jsonify({'status': 'incomplete', 'message': 'No values passed'}), 400
            if 'key' not in data:
                return jsonify({'status': 'incomplete', 'message': 'missing the key info'}), 400
            if 'value' not in data:
                return jsonify({'status': 'incomplete', 'message': 'missing the value info'}), 400

            key = data['key']
            value = data['value']
            print(
                f"Processing request to store key: {key} with value: {value}")

            # Find the responsible node for this key
            responsible_node_address = self.hash_key_to_node(
                key)

            # Get my container name and address
            my_container_name = f"node{self.port-8000}" if self.port != 8000 else "bootstrap"
            my_address = f"http://{my_container_name}:{self.port}"

            # Forward the request if we're not the responsible node
            if responsible_node_address != my_address:
                try:
                    print(
                        f"Forwarding key {key} to node at {responsible_node_address}")
                    # Ensure we're using the container name, not localhost in Docker networking
                    forwarded_response = requests.post(
                        responsible_node_address + "/kv", json=data)
                    print(
                        f"Forwarded response status: {forwarded_response.status_code}")
                    return forwarded_response.text, forwarded_response.status_code
                except requests.exceptions.RequestException as e:
                    print(f"ERROR forwarding request: {str(e)}")
                    return jsonify({"error": f"Error forwarding request: {str(e)}"}), 500

            # We are the responsible node, store the key-value pair
            print(f"I am the responsible node for key {key}, storing locally")
            self.keyvalue[key] = value
            os.makedirs("/app/storage", exist_ok=True)
            with open("/app/storage/data.json", "w") as fh:
                json.dump(self.keyvalue, fh, indent=2)
            return {'status': 'stored', 'node_id': self.id, 'node_address': self.address}, 200

            return jsonify({
                'status': 'success',
                'message': f'Stored {key}:{value} on node {self.id}',
                'node': self.id
            }), 200

        @self.app.route('/kv/<key>', methods=['GET'])
        def get_KVPair(key):
            """Return the value based on the key"""
            print(f"Processing request to retrieve key: {key}")

            # Find the responsible node for this key
            responsible_node_address = self.hash_key_to_node(
                key)

            # Get my container name and address
            my_container_name = f"node{self.port-8000}" if self.port != 8000 else "bootstrap"
            my_address = f"http://{my_container_name}:{self.port}"

            # Forward the request if we're not the responsible node
            if responsible_node_address != my_address:
                try:
                    print(
                        f"Forwarding key lookup for {key} to node at {responsible_node_address}")
                    forwarded_response = requests.get(
                        f"{responsible_node_address}/kv/{key}")
                    print(
                        f"Forwarded GET response status: {forwarded_response.status_code}")
                    return forwarded_response.text, forwarded_response.status_code
                except requests.exceptions.RequestException as e:
                    print(f"ERROR forwarding GET request: {str(e)}")
                    return jsonify({"error": f"Error forwarding request: {str(e)}"}), 500

            # We are the responsible node, return the value if it exists
            print(
                f"I am the responsible node for key {key}, checking local storage")
            value = self.keyvalue.get(key, None)
            if value is not None:
                print(f"Found value for key {key}: {value}")
                return jsonify({"key": key, "value": value, "node_id": self.id, "responsible_node_address": responsible_node_address}), 200
            else:
                print(f"Key {key} not found in my storage")
                return jsonify({"error": "Key not found"}), 404
            
        @self.app.route('/metrics', methods=["GET"])
        def metrics():
            lines = [
                f'p2p_messages_sent{{instance="{self.address}"}} {self.stats["sent"]}',
                f'p2p_messages_received{{instance="{self.address}"}} {self.stats["recv"]}',
                f'p2p_peers{{instance="{self.address}"}} {len(self.peers)}'
            ]
            
            return Response("\n".join(lines), mimetype="text/plain")

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
            'debug': True,
            'use_reloader': False
        })
        flask_thread.start()

        for x in range(random.randint(1,20)):
            self.send_message()

    def register_with_bootstrap(self):
        """Register this node with the bootstrap node"""
        # For Docker networking, use container name instead of localhost
        container_name = f"node{self.port-8000}" if self.port != 8000 else "bootstrap"
        my_address = f"http://{container_name}:{self.port}"

        retries = 5
        for attempt in range(retries):
            try:
                print(f"Attempt {attempt+1} to register with bootstrap node")
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
                    return
                else:
                    print(
                        f"Failed to register with bootstrap node: {response.status_code}")
            except requests.RequestException as e:
                print(f"Error connecting to bootstrap node: {e}")

            # Wait before retry
            print(f"Waiting before retry {attempt+1}")
            time.sleep(2)

        print("ERROR: Failed to register with bootstrap after multiple attempts")

    def get_peers_from_bootstrap(self):
        """Get the list of peers from the bootstrap node"""
        try:
            response = requests.get(f"{self.bootstrap_url}/peers", timeout=5)
            if response.status_code == 200:
                peer_list = response.json().get('peers', {})
                peer_count = 0
                for peer_id, peer_address in peer_list.items():
                    if peer_id != self.id:  # Don't add ourselves
                        self.peers[peer_id] = peer_address
                        peer_count += 1

                print(f"Got {peer_count} peers from bootstrap node")
                print(f"Full peer list: {self.peers}")
            else:
                print(f"Failed to get peers: {response.status_code}")
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

        # Retrieves a random key, value pair from dictionary
        peer_id, peer_address = random.choice(list(self.peers.items()))

        try:
            # variables used in post request
            values = peer_address.split(":")
            node_name = socket.gethostname()
            alive = f"{peer_address}/status"
            url = f"{peer_address}/message"

            # alive = f"http://localhost:{values[2]}/status"
            # url = f"http://localhost:{values[2]}/message"

            # r = requests.get(alive, timeout=5)

            if self.node_active(alive):
                print(
                    f"This is {node_name}, Sending a message to {peer_id} at {peer_address}")
                print(f"Sending to {url}")
                
                # metrics
                self.stats["sent"] += 1

                response = requests.post(
                    url, json={"sender": node_name, "msg": f"This is {node_name}, How is your day? "})
                print(f"Got response: {response.content}")

        except requests.RequestException as e:
            print(f"Error connecting to node: {e}")

    @staticmethod
    def sha1_int(s: str) -> int:
        return int(hashlib.sha1(s.encode()).hexdigest(), 16)
    
    def ring(self):
        peers_hashed = [(self.sha1_int(pid), addr) for pid, addr in self.peers.items()]
        peers_hashed.append((self.node_hash, self.address))
        return sorted(peers_hashed, key=lambda x: x[0])
    
    def responsible_addr(self, key: str) -> str:
        h = self.sha1_int(key)
        for nh, addr in self.ring():
            if h <= nh:
                return addr
            
        return self.ring()[0][1]



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
