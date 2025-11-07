from math import inf
import json


current_heading = 0  # Initial orientation in degrees

# --- Graph class adapted from old project ---
class Graph:
    def __init__(self):
        self.adj = {}  # Dictionary representation of the graph
        self.opposites = {'h': 'b', 'd': 'g', 'b': 'h', 'g': 'd'}  # For reverse direction

    def add_edge(self, a, b, weight, direction):
        # Add edge from a to b
        if a not in self.adj:
            self.adj[a] = {}
        self.adj[a][b] = (weight, direction)
        # Add reverse edge from b to a using opposite direction
        if b not in self.adj:
            self.adj[b] = {}
        self.adj[b][a] = (weight, self.opposites[direction])

    def dijkstra(self, start, target):
        #print(self.adj.items())
        dist = {node: inf for node in self.adj}
        prev = {node: None for node in self.adj}
        dist[start] = 0
        unvisited = set(self.adj.keys())

        while unvisited:
            current = min(unvisited, key=lambda node: dist[node])
            if current == target:
                break
            unvisited.remove(current)
            for neighbor, (w, _) in self.adj[current].items():
                alt = dist[current] + w
                if alt < dist[neighbor]:
                    dist[neighbor] = alt
                    prev[neighbor] = current
        # Reconstruct path from start to target
        path = []
        node = target
        while node is not None:
            path.insert(0, node)
            node = prev[node]
        return path

# --- Command Generation Functions ---
def angle_for_direction(direction):
    # Map a direction letter to an angle (in degrees)
    global current_heading
    #print(current_heading)
    mapping = {'h': 0-current_heading, 'd': 90-current_heading, 'b': 180-current_heading, 'g': 270-current_heading}
    update_heading(mapping[direction])
    return mapping.get(direction, 0)

def update_heading(turn_angle):
    global current_heading
    current_heading = (current_heading + turn_angle) % 360
    return current_heading


def generate_commands(graph, path, current_heading=0):
    """
    For each consecutive pair of nodes in the path, generate:
      - A turn command (to face the direction of the edge)
      - A move command (to move the required distance)
    """
    commands = []
    if len(path) < 2:
        return commands  # Nothing to do if the path is too short
    

#    # Determine the desired heading for the first edge
#     _, (weight, direction) = next(iter(graph.adj[path[0]].items()))
#     desired_heading = angle_for_direction(direction)  # e.g., maps 'h'->0, 'd'->90, etc.

#     # Compute the rotation needed to reorient the robot
#     rotation_needed = (desired_heading - current_heading) % 360
#     if rotation_needed != 0:
#         commands.append({"command": "turn", "float_data": [rotation_needed]})


    for i in range(len(path) - 1):
        src = path[i]
        dst = path[i + 1]
        weight, direction = graph.adj[src][dst]
        turn_angle = angle_for_direction(direction)
        # Append turn and move commands
        commands.append({"command": "turn", "float_data": [turn_angle]})
        commands.append({"command": "move", "float_data": [weight]})
    return commands

# --- Integration Function ---
def handle_navigation_command(current_room, target_room):
    """
    Computes the shortest path from current_room to target_room,
    generates corresponding movement commands, and returns them as a JSON string.
    """
    # Create and populate the graph (this could be loaded from a file or defined elsewhere)
    graph = Graph()
    # Example graph edges
    graph.add_edge('corner one', 'corner two', 2, 'd')
    graph.add_edge('corner two', 'corner three', 1, 'h')
    graph.add_edge('corner three', 'corner four', 2, 'g')
    graph.add_edge('corner four', 'end', 1, 'b')
    # ... additional nodes and edges as required for hospital map

    # Compute the shortest path using Dijkstra's algorithm
    current_room = current_room.strip("\"")
    target_room = target_room.strip("\"")

    if current_room not in graph.adj:
        return json.dumps({"error": f"Room {current_room} does not exist. Try again"})
    if target_room not in graph.adj:
        return json.dumps({"error": f"Room {target_room} does not exist. Try again"})
    
    path = graph.dijkstra(current_room, target_room)
    print("Path from", current_room, "to", target_room, ":", path)

    # Generate commands based on the computed path
    commands = generate_commands(graph, path, current_heading)
    # Return the commands as a JSON string
    return json.dumps(commands)

# --- Example Usage ---
if __name__ == "__main__":
    # Simulate receiving a navigation command (e.g., "go to RoomC")
    current_node = "RoomA"
    target_node = "RoomC"
    json_commands = handle_navigation_command(current_node, target_node)
    print("Generated JSON Commands:")
    print(json_commands)
