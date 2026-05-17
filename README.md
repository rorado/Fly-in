*This project has been created as part of the 42 curriculum by soahrich.*

# ✈️ Fly-in Project

## 📌 Description

Fly-in is a drone simulation project that models autonomous drone navigation through a network of interconnected zones.

The project:

* Parses a configuration file describing hubs and connections
* Builds a graph representation of the environment
* Computes valid paths between start and end zones
* Simulates drone movement in real time
* Visualizes the simulation using Pygame

The objective of the project is to explore:

* Graph theory
* Pathfinding algorithms
* Turn-based simulation systems
* Dynamic routing
* Real-time visualization

---

# ⚙️ Instructions

## 📥 Input Format

The program takes a configuration file describing the simulation environment.

The file contains:

* Number of drones
* Start and end hubs
* Intermediate hubs
* Connections between hubs
* Optional metadata:

  * Zone type
  * Capacity
  * Colors
  * Link limits

---

## 🔄 Program Workflow

When executed, the program performs the following steps:

### 1. Parsing

* Reads and validates the configuration file
* Creates structured configuration objects

### 2. Graph Construction

* Builds an adjacency-list graph
* Connects all hubs through edges

### 3. Pathfinding

* Computes multiple candidate paths
* Selects paths according to drone distribution

### 4. Simulation

* Spawns drones at the start hub
* Simulates movement turn by turn

### 5. Visualization

* Displays zones, connections, and drone movement in real time

---

## 🔧 Requirements

* Python 3.10+
* pip
* pygame
* pydantic
* webcolors
* flake8
* mypy

---

# 🚀 Usage

## 📦 Install Dependencies

```bash
make install
```

## ▶️ Run the Program

```bash id="yc3sdp"
make run
```

## 🐛 Debug Mode

```bash id="7vtqwc"
make debug
```

## 🧹 Clean Cache Files

```bash id="hz4gb1"
make clean
```

## 🧪 Lint

```bash id="7mvgm8"
make lint
```

## 🔒 Strict Lint

```bash id="q7hj3w"
make lint-strict
```

---

# 🧠 Algorithm Explanation

## 🧭 Graph Representation

The environment is represented as a weighted graph:

* Nodes represent zones
* Edges represent connections between zones

The graph is implemented using an adjacency list for efficient traversal and lookup operations.

---

## 🛤️ Pathfinding Algorithm

The project uses a Dijkstra-based pathfinding system.

### Core Principle

* Each connection has a traversal cost
* Dijkstra’s algorithm computes the shortest path between the start and end hubs
* Multiple candidate paths are generated instead of a single path

---

## 🔀 Multi-Path Strategy

The number of candidate paths depends on the number of drones (`nb_drones`).

The system:

* Computes several alternative shortest paths
* Evaluates remaining traversal cost
* Selects routes dynamically during simulation

This strategy helps:

* Reduce congestion
* Distribute drones across the graph
* Improve traffic flow efficiency

---

## 🔄 Dynamic Rerouting

When a drone cannot continue because:

* A zone is full
* A connection reached maximum capacity

The simulation:

* Evaluates alternative candidate paths
* Chooses the lowest valid remaining cost
* Reroutes the drone dynamically

---

## 🚧 Constraint Management

Movement is restricted by:

* Zone capacity (`max_drones`)
* Connection capacity (`max_link_capacity`)

These constraints force drones to:

* Wait
* Or reroute to alternative paths


---

## ⏱️ Turn-Based Simulation

The simulation operates using discrete turns.

Each turn:

* Processes every drone
* Updates movement state
* Handles transitions
* Applies capacity constraints

---

## 🚁 Drone States

A drone can be in two states:

### 1. Inside a zone

The drone is waiting or preparing to move.

### 2. In-flight

The drone is moving between two zones over multiple turns.

This creates smoother and more realistic movement behavior.

---

## 📄 Example Input & Expected Output

### 🧾 Example Configuration File (`map.txt`)

### input:
```txt
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]

hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]

connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

### output:

```
D1-corridorA D2-hub-roof1
D2-roof1 D1-tunnelB D3-corridorA
D1-goal D2-roof2 D3-tunnelB D4-corridorA D5-hub-roof1
D5-roof1 D2-goal D3-goal D4-tunnelB
D4-goal D5-roof2
D5-goal
```

The program output represents a **turn-based simulation log** of all drones moving through the graph.

Each line corresponds to **one simulation turn**, and contains all drone actions that happened during that turn
- `D<id>-<zone>`  
  → The drone has arrived at a zone

- `D<id>-<from>-<to>`  
  → The drone is currently moving between two zones (in-flight)


---

# 🎮 Visual Representation Features

The project includes a real-time visualization system built using Pygame.

---

## 🗺️ Graph Visualization

* Zones are displayed as circles
* Connections are displayed as lines
* Positions are based on zone coordinates

This provides a clear visual representation of the network.

---

## 🎨 Zone Visualization

Zones use:

* Colors
* Labels
* Different visual states

to represent:

* Normal zones
* Restricted zones
* Priority zones

---

## 🚁 Drone Visualization

* Drones are animated in real time
* Each drone displays a unique identifier
* Movement between zones is interpolated smoothly

This allows users to follow drone movement visually.

---

## ⏱️ Real-Time Animation

The renderer synchronizes with the simulation engine:

* Each simulation turn updates the display
* Transitions are animated progressively

---

## 🔄 Live State Updates

The visualization reflects:

* Zone occupancy
* Connection usage
* Drone movement
* Dynamic rerouting

---

## 🎯 User Experience Benefits

The visualization system improves usability by:

* Making graph structures easier to understand
* Showing congestion visually
* Helping debug deadlocks and routing issues
* Providing immediate feedback on drone behavior

---

# 📚 Resources

## 📖 Documentation & References

* Python Documentation
  https://docs.python.org/3/

* Pygame Documentation
  https://www.pygame.org/docs/

* Drone Map Visualizer
  https://flyin-drone-map-visualizer.vercel.app/

---

## 🤖 AI Usage

AI tools were used as development assistants for:

### 🧩 Debugging

* Resolving runtime and MyPy errors
* Understanding pdb debugging workflows

### 🧠 Concept Explanations

* Graph structures
* Pygame rendering and event handling

### 🛠 Development Support

* Improving project structure
* Refactoring code for readability
* Assisting with documentation organization

AI was used as a support tool for learning, debugging, and documentation only.
