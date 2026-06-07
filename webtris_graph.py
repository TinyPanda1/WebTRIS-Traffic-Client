from collections import deque
import heapq
from webtris_client import DataFetch, ClientWebTRIS
import time

class Location:
    """
    I designed this class to act as a vertex in  adjacency list repr of the road network m25
    Instead of only storing names, the object can take care of its outer edges, which keeps the 
    graph logic kept in a single location + keeps main graph class from turning too complex 
    """
    def __init__(self, name: str) -> None:
        self.name: str = name
        # Maps the destination object directly to the travel time cost for O(1) lookups
        self.connections: dict['Location', float] = {}


    def add_connection(self, destination: 'Location', travel_time_mins: float) -> None:
        """
        I added a directed edge from this location to a destination
        made this directed one-way by default because the assignment wanted  
        a clockwise journey on the M25 road network. Treating as a directed graph keeps the 
        algorithm from accidentally directing us back to front counter-clockwise
        """

        self.connections[destination] = travel_time_mins

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return False
        return self.name == other.name



    def __hash__(self) -> int:
        # I implemented the __hash__ method so we can use the Locations objects as prospective keys for dictionaries 
        # like the cheapest_times table in Dijkstra's algorithm as well as inside visited sets when employing DFS or BFS
        return hash(self.name)

    def __lt__(self, other: object) -> bool:
        """
        added this specifically specifically to prevent crashes occuring during Dijkstra's Algorithm
        Since the `heapq` module pops the lowest value, if two routes have the 
        same travel time, the heap tries to compare location objects themselves. 
        This method works as the tie-breaker, sorting alphabetically by name to prevent a TypeError 
        from being thrown when the algorithm tries to compare two Location objects.
        """

        if not isinstance(other, Location):
            raise TypeError("Comparisons should be between location objects only")
        return self.name < other.name

    def __repr__(self) -> str:
        return f"Location({self.name!r})"


class RouteGraph:
    """
    I built this container class to manage overall network of the Locations objects and their connections. 
    It supplies methods for adding locations and edges, as well as getting location objects by their name
    It acts as a central portal to building the graph prior to running search algorithms
    """

    def __init__(self) -> None:
        # this stores vertices in a dict keyed by name for O(1) lookups instead of O(N) list searches
        self.locations: dict[str, Location] = {}


    def add_location(self, name: str) -> Location:
        """
        Creates a new Location if it doesn't exist, adds it to the graph, then returns it
        I designed it to return the object so I can chain my creations and connections easily in the main() file
        """

        if name not in self.locations:
            self.locations[name] = Location(name)
        return self.locations[name]

    def location_getter(self, name: str) -> Location | None:

        # gets a location by str name and returns None if it doesn't exist
        return self.locations.get(name)


    def add_direct_edge(self, origin_name: str, dest_name: str, travel_time: float) -> None:
        """
        should connect 2 location objects. I designed to automatically create 
        locations if they don't already exist in graph, which saves from having to write a
        redundant initialization for all the junctions in the main 
        """

        origin = self.add_location(origin_name)
        destination = self.add_location(dest_name)
        origin.add_connection(destination, travel_time)


def get_edge_time(sensor_readings: list[dict], distance_miles: float) -> float:
    """
    I created this helper method to loop thru list of sensor dictionaries for specific edge
    
    I intended to filter out any sensors where the average_mph is None before finding the combined avg speed.
    This makes sure that a broken sensor shouldn't crash entire best route calculation logic
    """
    valid_speeds = []
    
    # iterates thru list of dicts for the edge, pulling out the avg mph readings and filtering out any that are broken sensors
    for reading in sensor_readings:
        speed = reading.get("average_mph")
        if speed is not None:
            valid_speeds.append(speed)
            
    # If all sensors are broken, we probably should have a fallback. I chose a basic 40 mph default for this
    # to keep graph algorithms from raising a divide by 0 error
    if len(valid_speeds) == 0:
        avg_speed = 40.0 
    else:
        avg_speed = sum(valid_speeds) / len(valid_speeds)
        
    # Time = Distance/Speed * by 60 to turn hours into minutes
    travel_time_mins = (distance_miles / avg_speed) * 60.0
    return travel_time_mins



def build_m25(offline_data: dict) -> RouteGraph:
    """
    I designed this builder function to take in raw dictionary data and translate it 
    into our object oriented RouteGraph. I kept graph building logic separate from the 
    graph class to keep clean segregation of main issues.
    """

    m25_graph = RouteGraph()
    # Route A: Direct Route (J7 - J12 - J13 - J14]
    # The assignment defined Gatwick to J12 as 23 miles total. To confirm BFS accurately counts locations, 
    # I divided 23 miles evenly across 5 junction areas each 4.6 miles
    time_per_segment = get_edge_time(offline_data.get("7-12", []), 4.6)
    m25_graph.add_direct_edge("Junction 7", "Junction 8", time_per_segment)
    m25_graph.add_direct_edge("Junction 8", "Junction 9", time_per_segment)
    m25_graph.add_direct_edge("Junction 9", "Junction 10", time_per_segment)
    m25_graph.add_direct_edge("Junction 10", "Junction 11", time_per_segment)
    m25_graph.add_direct_edge("Junction 11", "Junction 12", time_per_segment)

    # Distance: 3 miles
    time_12_13 = get_edge_time(offline_data.get("12-13", []), 3.0)
    m25_graph.add_direct_edge("Junction 12", "Junction 13", time_12_13)
    # Distance: 3 miles
    # I split this into J13-J14 and J14-Heathrow to use the different 14-Heathrow sensors.
    time_13_14 = get_edge_time(offline_data.get("13-14", []), 2.0)
    time_14_heathrow = get_edge_time(offline_data.get("14-Heathrow", []), 1.0)
    
    m25_graph.add_direct_edge("Junction 13", "Junction 14", time_13_14)
    m25_graph.add_direct_edge("Junction 14", "Heathrow Airport", time_14_heathrow)
    
    # Route B: M3 diverting through Sunbury [J12 - Sunbury - Heathrow]
    # The assignment states to assume this local roads diversion takes 20 minutes at all times 
    # because it doesn't have WebTRIS sensors. Therefore, I bypass the calculation helper entirely for this scenario and just add the flat time directly to graph.
    m25_graph.add_direct_edge("Junction 12", "Sunbury-on-Thames", 12.0) # hypotetical time to Sunbury
    m25_graph.add_direct_edge("Sunbury-on-Thames", "Heathrow Airport", 20.0)    
    # Route C: A30 Diversion using Staines [J13 - Staines -Heathrow]
    # Distance: 3.8 miles. Using the A30 key from our offline 
    # dictionary to find time for the first edge, then adds a flat 5 min local time to Heathrow 
    time_a30 = get_edge_time(offline_data.get("A30", []), 3.8)
    m25_graph.add_direct_edge("Junction 13", "Staines-upon-Thames", time_a30)
    
    # Since I'm assuming A30 time calculated before gets us to Heathrow, or adding flat rate for the final stretch.
    # To connect it correctly to our final vertex, I add short 5 min assumed local time from Staines to the airport.
    m25_graph.add_direct_edge("Staines-upon-Thames", "Heathrow Airport", 5.0)
    return m25_graph

def bfs_least_stops(graph: RouteGraph, start_name: str, target_name: str) -> tuple[list[str], float]:
    """
    should find the route between 2 locations that needs passing through the fewest edges.
    
    I implemented this using Breadth-First Search (BFS) because it should naturally explore the graph 
    level by level, guaranteeing that first time we reach target, we have found the 
    path with the fewest edges 
    """
    # ensures the starting location actually exists in our graph
    start_loc = graph.location_getter(start_name)
    if not start_loc:
        return [], 0.0

    # using a deque because lists are somewhat slow when popping from front
    # The queue stores a tuple containing current_node_name, path_taken_so_far, accumulated_time
    # I designed it this way so the algorithm naturally tracks its own route and weight without 
    # requiring separate, complex dictionary for backtracking processes like Dijkstra's
    queue = deque([(start_name, [start_name], 0.0)])
    
    # I kept a set of visited nodes to prevent infinite loops
    visited = {start_name}

    while queue:
        curr_name, path, total_time = queue.popleft()

        # If we reached our target, we should return the path and its corresponding weight, the total travel time
        if curr_name == target_name:
            return path, total_time

        curr_loc = graph.location_getter(curr_name)
        if curr_loc is not None:
            # checks for all outbound edges from our current location
            for neighbor, travel_time in curr_loc.connections.items():
                if neighbor.name not in visited:
                    # marking the neighbors as visited on the queue to stop any mroe duplicate queue additions
                    visited.add(neighbor.name)
                    
                    # Should create a a new path list with neighbor appended, and then add the travel times together for the new total time
                    new_path = path + [neighbor.name]
                    new_total_time = total_time + travel_time
                    
                    queue.append((neighbor.name, new_path, new_total_time))

    # If queue becomes empty and never reached our intended target, no path exists
    return [], 0.0

def dfs_explore(graph: RouteGraph, curr_name: str, target_name: str, 
                     visited: set[str] | None = None, curr_path: list[str] | None = None, 
                     accumulated_time: float = 0.0) -> tuple[list[str], float]:
    """
    Finds a working path between two location objects recursively

    Because DFS recursively goes down the 1st branch it runs into, the final route 
    is dependent on order of insertion of the connections dict. 
    It should find a working path, but not often best or the most efficient one
    """

    # Initialize the mutable default args first. As a defensive habit, I try to use None 
    # in signature and intialized them inside function to prevent a
    # constant default input trap throughout all of the multiple function calls
    if visited is None:
        visited = set()
    if curr_path is None:
        curr_path = []

    #marks current node as visited and add to tracking path
    visited.add(curr_name)
    curr_path.append(curr_name)

    # Base Case scenario is if we hit the target, we should return the path + time it took to get there
    if curr_name == target_name:
        return list(curr_path), accumulated_time
    curr_loc = graph.location_getter(curr_name)
    if curr_loc is not None:
        # Recursive Case: Dive into the unvisited neighbors
        for neighbor, travel_time in curr_loc.connections.items():
            if neighbor.name not in visited:
                # Recursively call DFS on the neighbor, passing down the updated time
                result_path, result_time = dfs_explore(
                    graph, 
                    neighbor.name, 
                    target_name, 
                    visited, 
                    curr_path, 
                    accumulated_time + travel_time
                )
                
                # If recursive call found a working path to target, it would surface up pretty much immediately
                # This is what should make DFS stop searching once finding its first valid route
                if result_path:
                    return result_path, result_time

    # Backtracking step: If the path led to dead end, we could just remove the current node 
    # from the path tracker prior to returning so it doesn't clutter up final returned output list
    curr_path.pop()
    
    return [], 0.0

def dijkstra_time(graph: RouteGraph, start_name: str, target_name: str) -> tuple[list[str], float]:
    """
    Finds the best efficient path between the two locations with minimum travel time involved
    
    I Implemented using heapq to greedily get the lowest known travel time in O(1) time.
    """

    start_loc = graph.location_getter(start_name)
    if not start_loc:
        return [], 0.0


    # stores the lowest travel time found from start to any given location
    cheapest_times: dict[str, float] = {start_name: 0.0}
    
    # Acts as my breadcrumb trail in case of backtracking needs. Maps a location name to location we came from to get back there.
    prev_loc: dict[str, str | None] = {start_name: None}
    
    visited: set[str] = set()
    
    # The Priority Queue stores tuples of the accumulated_time and Location_Object
    #  reasoning for why I implemented  __lt__ magic method in Location class
    # If two routes have same exact time, heapq needs to compare the Location objects to break tie while also not crashing
    pq: list[tuple[float, Location]] = [(0.0, start_loc)]
    
    while pq:
        # greedy extract-min the unvisited location with lowest known travel time
        curr_time, curr_loc = heapq.heappop(pq)
        
        # If we have already found and positioned in the shortest path to this node, skip it
        if curr_loc.name in visited:
            continue
            
        visited.add(curr_loc.name)
        
        # If we just popped our target, we know we have found the best mathematically optimal  
        # route because priority queue guarantees for no other path can be shorter
        if curr_loc.name == target_name:
            break
            
        # Look at all of the outbound edges
        for neighbor, travel_time in curr_loc.connections.items():
            if neighbor.name in visited:
                continue
                
            new_time = curr_time + travel_time
            
            # If this is the first time seeing this neighbor, or if we found a strictly faster route
            if neighbor.name not in cheapest_times or new_time < cheapest_times[neighbor.name]:
                cheapest_times[neighbor.name] = new_time
                prev_loc[neighbor.name] = curr_loc.name
                heapq.heappush(pq, (new_time, neighbor))

    # Route Reconstruction
    # I separated the route recreation logic to keep the algorithmic loop uncluttered and focused on Dijkstra's main logic
    # We walk back from target using breadcrumb trail I made in prev_loc
    route: list[str] = []
    curr_step: str | None = target_name
    # If the target is not in prev_loc, it means it was unreachable
    if target_name not in prev_loc:
        return [], 0.0
        
    while curr_step is not None:
        route.append(curr_step)
        curr_step = prev_loc.get(curr_step)
        
    # Reverse the backwards path to get Gatwick to Heathrow
    route.reverse()
    
    return route, cheapest_times[target_name]

def get_m25_dataset(sensor_map: dict[str, list[dict]], target_date: str) -> dict:
    """
    I designed this method to automatically fetch from the WebTRIS API for all sensors 
    defined, bridging client with my graph file.
    
    I implemented the mandatory time.sleep between the requests as told to avoid 
    hitting API rate limits. I also wrapped fetch call in a try/except block. 
    If specific sensor times out, it appends `None` for the speed and relies on my get_edge_time helper to filter out later without crashing
    """
    live_data: dict[str, list[dict]] = {}
    
    # constructs the original webtris client using live DataFetch strategy
    curr_fetcher = DataFetch()
    client = ClientWebTRIS(curr_fetcher)
    
    print(f"Getting from live WebTRIS data for {target_date}...")
    print("this will prolly take a few minutes due to API rate limit delays... beep boop\n")
    

    for route_leg, sensors in sensor_map.items():
        live_data[route_leg] = []
        print(f"  -> Getting data for leg: {route_leg} ({len(sensors)} sensors)")
        
        for sensor in sensors:
            sensor_id = str(sensor["id"])
            
            try:
                # get the instantiated Site object from webtris client code
                site_data = client.report_getter(sensor_id, target_date)
                
                # take out the daily avg speed from the site object
                avg_speed = site_data.avg_mph() if len(site_data) > 0 else None
                    
                live_data[route_leg].append({
                    "id": sensor_id,
                    "average_mph": avg_speed
                })
                
            except Exception:
                #  if the API drops, append None and move on
                live_data[route_leg].append({
                    "id": sensor_id,
                    "average_mph": None
                })
                
            # required API rate limit delay to prevent getting blocked
            time.sleep(2)
            
    return live_data

if __name__ == "__main__":
    """
    I intended for the main execution bloc to specifically compare these 3 algorithms outlined in the project.
    By printing out route sequences as well as complete total travel time for each of them, I can directly look at the 
    trade off that was cited in the assignment, that being that the route with the fewest stops might not be 
    the fastest route if M25 is congested
    """
    print("Starting M25 Route Planner")
    
    # This map holds the IDs. use for telling our live getter what to query through the WebTRIS client
    SENSOR_MAP = {
        "7-12": [{"id": 138}, {"id": 144}, {"id": 479}, {"id": 544}, {"id": 547}, {"id": 598}, {"id": 699}, {"id": 752}, {"id": 778}, {"id": 885}, {"id": 1069}, {"id": 1135}, {"id": 1221}, {"id": 1270}, {"id": 1442}, {"id": 1479}, {"id": 1914}, {"id": 1990}, {"id": 2005}, {"id": 2089}, {"id": 2097}, {"id": 2149}, {"id": 2419}, {"id": 2486}, {"id": 2530}, {"id": 2636}, {"id": 3003}, {"id": 3323}, {"id": 3437}, {"id": 3714}, {"id": 3835}, {"id": 3897}, {"id": 4000}, {"id": 4092}, {"id": 4145}, {"id": 4202}, {"id": 4223}, {"id": 4714}, {"id": 4719}, {"id": 4761}, {"id": 4894}, {"id": 5107}, {"id": 5118}, {"id": 5138}, {"id": 5176}, {"id": 5261}, {"id": 5288}, {"id": 5457}, {"id": 5526}, {"id": 5546}, {"id": 5712}, {"id": 5842}, {"id": 5875}, {"id": 5914}, {"id": 5990}, {"id": 6156}, {"id": 6252}],
        "12-13": [{"id": 8}, {"id": 1811}, {"id": 1910}, {"id": 2952}, {"id": 2992}, {"id": 3319}, {"id": 5245}, {"id": 5662}, {"id": 5681}],
        "13-14": [{"id": 279}, {"id": 737}, {"id": 3671}, {"id": 4053}, {"id": 4354}, {"id": 5317}],
        "14-Heathrow": [{"id": 746}, {"id": 2153}, {"id": 2977}],
        "A30": [{"id": 9005}]
    }

    # Get live data using webtris Client
    target_api_date = "19012026" 
    live_m25_data = get_m25_dataset(SENSOR_MAP, target_api_date)

    # builds graph using the live data
    print("\nBuilding Graph and getting edge weights from live data")
    m25_network = build_m25(live_m25_data)
    print("Graph built successfully.\n")

    start_node = "Junction 7"
    end_node = "Heathrow Airport"
    print(f"Looking at Routes from Gatwick ({start_node}) to {end_node}\n")
    # run BFS
    print("Breadth First Search (target the fewest junctions):")
    bfs_route, bfs_time = bfs_least_stops(m25_network, start_node, end_node)
    print(f"   Route: {' -> '.join(bfs_route)}")
    print(f"   Total Nodes Visited: {len(bfs_route)}")
    print(f"   Estimated Time: {bfs_time:.2f} minutes\n")
    # run DFS
    print("Depth First Search (targeting first working path found):")
    dfs_route, dfs_time = dfs_explore(m25_network, start_node, end_node)
    print(f"   Route: {' -> '.join(dfs_route)}")
    print(f"   Total Nodes Visited: {len(dfs_route)}")
    print(f"   ET (Estimated Time): {dfs_time:.2f} minutes\n")
    # run Dijkstra's Algorithm
    print("Dijkstra's Algorithm (Targeting abs min travel time):")
    dijkstra_route, best_time = dijkstra_time(m25_network, start_node, end_node)
    print(f"   Route: {' -> '.join(dijkstra_route)}")
    print(f"   Total Nodes Visited: {len(dijkstra_route)}")
    print(f"   Estimated Time: {best_time:.2f} minutes\n")
    
    print(" Completed M25 route analysis")

