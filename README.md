# **Group Project 3: Distribution and Scalability**
- Joseph David: 031644494
- Jayden Tran: 018148739
- Dominique Legaspi: 032094567

# Overview
This project implements a peer-to-peer networking using Docker containers consisting of 50-100 nodes, each acting as both a client and a server. 

# Installation
To run this program in your local environment, you will need the following programs:

## Prerequisites
- Docker Desktop, Docker Compose
- Visual Studio Code
- Python 3.9+

## Running this program
1. Clone the repository using `git clone <url> <project_name-optional>` and open the project
2. Open Docker Desktop
3. Go to `Dockerfile` and click on `Run All Services`
4. Navigate back to Docker Desktop and select the proper container to see the logs

# Learning Outcomes
## Launch the node
```
# Node 1 on port 5001
docker run -d -p 5001:5000 -v "$(pwd)/storage1:/app/storage" --name node1 p2p-node

# Node 2 on port 5002
docker run -d -p 5002:5000 -v "$(pwd)/storage2:/app/storage" --name node2 p2p-node

# Node 3 on port 5003
docker run -d -p 5003:5000 -v "$(pwd)/storage3:/app/storage" --name node3 p2p-node
```

## Using the API
```
curl -F "file=@mydoc.txt" http://localhost:5001/upload
```
Expected output
```
{ "status": "uploaded", "filename": "mydoc.txt" }
```
## Key Value Store
```
curl -X POST http://localhost:5001/kv \
  -H "Content-Type: application/json" \
  -d '{"key": "color", "value": "blue"}'
```

Expected output:
```
{ "status": "stored", "key": "color", "node": "node1" }
```
### Get
```
curl http://localhost:5001/kv/color
```

Response
```
{ "key": "color", "value": "blue" }
```

## DHT Routing
```
if current_node != responsible_node:
    res = requests.post(f"http://{responsible_node}/kv", json=data)
```

## Visualization and Monitoring
```
# macOS (Homebrew)
brew install node

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y nodejs npm
```
Go to the localhost:8000 to see the charts and nodes.