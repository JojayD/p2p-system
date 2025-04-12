# **Group Project 2: A Try of Peer-To-Peer**
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
## Phase 1: Running a Single Node
In Phase 1, we wrote a basic P2P node application where each node assigns itself a unique identifier using `uuid` and starts a minimal HTTP server using `Flask` to receive requests.

### Building and running a single node:
```
docker build -t p2p-node .
docker run -d -p 8000:8000 --name node1 p2p-node
```
### Expected Output:
Visit `http://localhost:8000` to see the following:
```
{"message": "Node <UUID> is running!"}
```

## Phase 2: Developing a Basic P2P Node
In Phase 2, each node stores a list of known peers and sends and receives messages between nodes.

### Start multiple nodes
```
docker run -d --name node1 -p 8001:8000 p2p-node
docker run -d --name node2 -p 8002:8000 p2p-node
```
### Send a Message Between Nodes
```
curl -X POST http://localhost:8002/message -H "Content-Type: application/json" -d '{"sender": "Node1", "msg": "Hello Node2!"}'
```
### Expected Output:
```
{"status": "received"}
Received message from Node1: Hello Node2!
```

## Phase 3: Bootstrapping P2P Network and Communication
In Phase 3, we enable automatic peer discovery using a bootstrap node, then explore P2P communication without bootstrap node.

### Start Bootstrap Node in Docker
```
docker build -t bootstrap-node -f bootstrap.Dockerfile .
docker run -d --name bootstrap -p 8000:8000 bootstrap-node
```

### Start Nodes
```
docker run -d --name node1 -p 8001:8000 p2p-node
docker run -d --name node2 -p 8002:8000 p2p-node
```

### Check Peer Registration
```
curl http://localhost:8000/peers
```

### Expected output
```
{"peers": ["http://localhost:8000", "http://node2:8000"]}
```

### Testing Peer Communication Without Bootstrap
```
docker build -t bootstrap-node -f bootstrap.Dockerfile .
docker run -d --name bootstrap -p 8000:8000 bootstrap-node
```

### Start Nodes
```
docker run -d --name node1 -p 8001:8000 p2p-node
docker run -d --name node2 -p 8002:8000 p2p-node
```

### Send Message Between Nodes
```
curl -X POST http://localhost:8001/message -H "Content-Type: application/json" -d '{"sender": "Node2", "msg": "Hello Node1!"}'

curl -X POST http://localhost:8002/message -H "Content-Type: application/json" -d '{"sender": "Node1", "msg": "Hey Node2, how are you?"}'
```