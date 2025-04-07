import uuid
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


class P2PNode:
    def __init__(self, port, bootstrap_url=None):
        # Assign a unique identifier to this node
        self.id = str(uuid.uuid4())
        self.port = port
        self.peers = {}  # Dictionary to store information about peer nodes
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
            })

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

            return jsonify({'status': 'success', 'peers': len(self.peers)})

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

            sender = data['sender']
            message = data['msg']

            print(f"Received message from {sender}: {message}")

            # You could add logic here to forward the message to other peers
            # or process it in some way

            return jsonify({'status': 'received'})

    def start(self):
        """Start the HTTP server"""
        print(f"Starting P2P node with ID: {self.id}")
        print(f"Node is running on http://localhost:{self.port}")

        # If we have a bootstrap node, register with it
        if self.bootstrap_url:
            self.register_with_bootstrap()

        self.app.run(host='0.0.0.0', port=self.port, debug=True)

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


# Example usage
if __name__ == "__main__":
    import sys

    # Check if we should be a bootstrap node or regular node
    if len(sys.argv) > 1 and sys.argv[1] == "--bootstrap":
        # Start as a bootstrap node (no bootstrap URL)
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        node = P2PNode(port=port)
        print("Starting as BOOTSTRAP node")
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
