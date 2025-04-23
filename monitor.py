import requests, time, threading, json, hashlib
from flask import Flask, jsonify, send_from_directory

BOOTSTRAP = "http://bootstrap:8000"
POLL_EVERY = 2 # seconds

app = Flask(__name__, static_folder="dashboard")

state = {
    "nodes": {},
    "links": []
}

def sha1_int(s):
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)

def poll():
    while True:
        try:
            peers = requests.get(f"{BOOTSTRAP}/peers", timeout=3).json()["peers"]
            new_nodes = {}
            links = []
            
            for pid, addr in peers.items():
                try:
                    m = requests.get(f"{addr}/metrics", timeout=2).text.splitlines()
                    parsed = {line.split('{')[0]: float(line.split()[1]) for line in m if line.strip()}
                    
                    new_nodes[pid] = {
                        "addr": addr,
                        "sent": parsed.get("p2p_messages_sent", 0),
                        "recv": parsed.get("p2p_messages_received", 0),
                        "hash": sha1_int(pid)
                    }
                except Exception:
                    pass
                
            # crude ring-successor edges for quick graph
            ordering = sorted(new_nodes.values(), key=lambda x: x["hash"])
            links = [
                {"source": ordering[i]["addr"], "target": ordering[(i + 1) % len(ordering)]["addr"]}
                for i in range(len(ordering))
            ]
            
            state["nodes"], state["links"] = new_nodes, links
        except Exception:
            pass
        
        time.sleep(POLL_EVERY)
        
@app.route("/api/state")
def api_state():
    return jsonify(state)

@app.route("/")
def index():
    return send_from_directory("dashboard", "index.html")

if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    app.run(host="0.0.0.0", port=9000)