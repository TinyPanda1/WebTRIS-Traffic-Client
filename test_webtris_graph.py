import pytest
from webtris_graph import ( 
    RouteGraph, 
    get_edge_time, 
    bfs_least_stops, 
    dfs_explore, 
    dijkstra_time
)

@pytest.fixture


def mock_graph() -> RouteGraph:
    """
    creates a fake controlled, predictable graph for testing for the 3 algorithms
    start is mid point (Time: 10)
    midpoint is target (Time: 10)   
    start is target (Time: 30) - A direct, but heavily trafficed path
    
    This design should test the trade offs: 
    - BFS should choose start - target (1 jump)
    - Dijkstra should pick start - midpoint - target which is 2 jumps, but 20 mins instead of 30
    """
    graph = RouteGraph()
    graph.add_direct_edge("start", "midpoint", 10.0)
    graph.add_direct_edge("midpoint", "target", 10.0)
    graph.add_direct_edge("start", "target", 30.0)
    
    return graph
def test_location_graph():
    """tests the main neighboring list logic/math for making the nodes + directed edges."""
    graph = RouteGraph()
    graph.add_direct_edge("A", "B", 15.0)
    
    loc_alpha = graph.location_getter("A")
    loc_beta = graph.location_getter("B")
    
    # verifies nodes were created
    assert loc_alpha is not None
    assert loc_beta is not None
    # shows directed edge and weight
    assert loc_beta in loc_alpha.connections
    assert loc_alpha.connections[loc_beta] == 15.0
    
    # verify it is directed, should not be bidirectional
    assert loc_alpha not in loc_beta.connections


def test_edge_getter():
    """tests the helper method for edge cases"""
    
    # case 1- Standard calculation, so 60 miles for 60 mph should be 60 mins
    valid_sensor_list = [{"average_mph": 60.0}, {"average_mph": 60.0}]
    assert get_edge_time(valid_sensor_list, 60.0) == 60.0
    # Case 2- Broken sensor filtration by ignoring the None, averages the 50 mph
    mixed_sensor_list = [{"average_mph": 50.0}, {"average_mph": None}]
    assert get_edge_time(mixed_sensor_list, 50.0) == 60.0 # 50 miles at 50mph gives 60 minutes
    # Case 3- Complete failure falls back and defaults to 40 mph
    broken_sensor_list = [{"average_mph": None}, {"average_mph": None}]
    assert get_edge_time(broken_sensor_list, 40.0) == 60.0 # 40 miles at 40mph default = 60 mins


def test_bfs_algo(mock_graph):
    """
    proves BFS looks first at the fewest edges
    It should take theh 30 minute direct route because it is only 1 jump
    """

    route, time = bfs_least_stops(mock_graph, "start", "target")
    
    assert route == ["start", "target"]
    assert time == 30.0
    assert len(route) == 2 # Only 2 nodes touched, start and target



def test_dijkstra(mock_graph):
    """
    Shows that Dijkstra's looks first at the minimum travel time
    It should ignore 1-jump direct route and input in the 2-jump midpoint route because it is faster (20 mins instead of 30) even though it is more jumps
    """
    route, time = dijkstra_time(mock_graph, "start", "target")
    
    assert route == ["start", "midpoint", "target"]
    assert time == 20.0 # 10 + 10
    assert len(route) == 3


def test_dfs_algo(mock_graph):
    """
    Proves DFS finds a working, connected path but does not guarantee its efficiency
    """
    route, time = dfs_explore(mock_graph, "start", "target")
    # makes sure that the route actually starts and ends correctly

    assert route[0] == "start"
    assert route[-1] == "target"

    # should not return a 0.0 time failure message, should find the time for the route it finds
    assert time > 0.0


def test_unreachable_dest(mock_graph):
    """proves  algorithms handle the impossible routes well without crashing"""
    # tests unreachable destination for BFS 
    # adds node that has no connections to graph
    mock_graph.add_location("island")
    
    route, time = dijkstra_time(mock_graph, "start", "island")
    assert route == []
    assert time == 0.0