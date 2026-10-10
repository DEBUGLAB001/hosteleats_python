import heapq

CAMPUS_GRAPH = {
    "Hostel A": {"Library": 5, "Quad": 10, "Hostel B": 7},
    "Hostel B": {"Hostel A": 7, "Library": 2, "Gym": 4},
    "Hostel C": {"Gym": 4, "Canteen": 8},
    "Library": {"Hostel A": 5, "Hostel B": 2, "Quad": 2, "Canteen": 12, "Science Block": 3},
    "Quad": {"Hostel A": 10, "Library": 2, "Gym": 6, "Canteen": 4},
    "Gym": {"Hostel B": 4, "Quad": 6, "Hostel C": 4, "Canteen": 3},
    "Canteen": {"Library": 12, "Quad": 4, "Gym": 3, "Hostel C": 8},
    "Auditorium": {"Quad": 3, "Sports Ground": 5, "Science Block": 6},
    "Sports Ground": {"Auditorium": 5, "Gym": 4},
    "Science Block": {"Library": 3, "Auditorium": 6},
}


def shortest_route(graph, source, target):
    if source not in graph or target not in graph:
        return None
    distances = {node: float("inf") for node in graph}
    previous = {}
    distances[source] = 0
    queue = [(0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        if node == target:
            break
        for neighbor, weight in graph[node].items():
            if neighbor not in distances:
                continue
            if weight < distances[neighbor]:
                distances[neighbor] = weight
                previous[neighbor] = node
                heapq.heappush(queue, (distances[neighbor], neighbor))
    if distances[target] == float("inf"):
        return None
    path = [target]
    seen = {target}
    while path[-1] != source:
        parent = previous.get(path[-1])
        if parent is None or parent in seen:
            return None
        path.append(parent)
        seen.add(parent)
    path.reverse()
    return {"minutes": distances[target], "path": path}
