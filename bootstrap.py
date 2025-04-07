import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Generate a unique ID for this bootstrap node
node_id = str(uuid.uuid4())

# Dictionary to store peer information (id -> address mapping)
peers = {}

@app.route('/', methods=['GET'])
def root():
    """Return basic information about the bootstrap node"""
    return jsonify({
        "message": f"Bootstrap node {node_id} is running!",
        "peers": len(peers)
    })

@app.route('/status', methods=['GET'])
def status():
    """Return status information about the bootstrap node"""
    return jsonify({
        'id': node_id,
        'type': 'bootstrap',
        'peers_count': len(peers),
        'status': 'active'
    })

@app.route('/register', methods=['POST'])
def register_peer():
    """Register a new peer to the network"""
    data = request.get_json()

    if not data or 'id' not in data or 'address' not in data:
        return jsonify({'error': 'Invalid peer data'}), 400

    peer_id = data['id']
    peer_address = data['address']

    # Add the peer to our registry
    peers[peer_id] = peer_address
    print(f"Registered new peer: {peer_id} at {peer_address}")

    return jsonify({
        'status': 'success', 
        'peers': len(peers),
        'message': f'Peer {peer_id} registered successfully'
    })

@app.route('/peers', methods=['GET'])
def get_peers():
    """Return the list of all registered peers"""
    return jsonify({
        'peers': peers
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'peers_count': len(peers)
    })

if __name__ == '__main__':
    import sys
    
    # Default port is 8000, but can be overridden
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    print(f"Starting bootstrap node with ID: {node_id}")
    print(f"Bootstrap server running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)