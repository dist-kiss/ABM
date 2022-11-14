from shapely.geometry import Point, LineString
from shapely.ops import split, nearest_points, snap
import numpy as np


def generate_random_point_on_line(edges, rng):
    """Create random origin, destination pair with minimum distance of min_dist between both points.
    
    Parameters
    ----------
    edges : geopandas.geodataframe.GeoDataFrame
        Edges from networkx graph containing start and end node information
    rng : numpy.random._generator.Generator
       random generator with fixed seed

    Returns
    -------
    random_point_with_information : Dict
        Dict of random point on an edge from input parameter edges, 
        nearest node on edge, other node on edge, distance to nearest node and 
        distance to other, far node.
    """
    # Create weight list by edge length
    weights = edges['mm_len'] / edges['mm_len'].sum()
    # Get random edge index using weight list as probability function
    index = rng.choice(edges.index, size=1, p=weights)
    # Get random edge as dict
    rn_edge = edges.loc[index].to_dict('records')[0]
    # Get random distance along edge 
    distance = rn_edge['mm_len'] * rng.random()
    # Create point using rn_edge and distance 
    point = rn_edge['geometry'].interpolate(distance)

    # Get nearer and more remote node, and distances to both
    if distance <= rn_edge['mm_len']/2:
        nearer_node = rn_edge['node_start']
        remote_node = rn_edge['node_end']
        dist_from_nearest = distance
        dist_from_remote = rn_edge['mm_len'] - distance
    else:
        nearer_node = rn_edge['node_end']
        remote_node = rn_edge['node_start']
        dist_from_nearest = rn_edge['mm_len'] - distance
        dist_from_remote = distance

    # Create dict with random point on edge and node information
    return {
            'point': point,
            'nearer_node': nearer_node,
            'remote_node': remote_node,
            'dist_from_nearer': dist_from_nearest,
            'dist_from_remote': dist_from_remote
            }

def get_random_org_dest(edges, seed, min_dist):
    """Create random origin, destination pair with minimum distance of min_dist between both points.
    
    Parameters
    ----------
    edges : geopandas.geodataframe.GeoDataFrame
        Edges from networkx graph containing start and end node information
    min_dist : number
        minimum distance between origin and destination

    Returns
    -------
    Origin, Destination: Dict, Dict
        Dicts for origin and destination and including nearest node id and id of wider away other node on edge, and distances to both. 

    """
    rng = np.random.default_rng(seed)
    orig = generate_random_point_on_line(edges, rng)
    dest = generate_random_point_on_line(edges, rng)
    while orig['point'].distance(dest['point']) < min_dist:
        dest = generate_random_point_on_line(edges, rng)
    return orig, dest

def get_random_dest(orig, edges, seed, min_dist):
    """Create random origin, destination pair with minimum distance of min_dist between both points.
    
    Parameters
    ----------
    edges : geopandas.geodataframe.GeoDataFrame
        Edges from networkx graph containing start and end node information
    min_dist : number
        minimum distance between origin and destination

    Returns
    -------
    Origin, Destination: Dict, Dict
        Dicts for origin and destination and including nearest node id and id of wider away other node on edge, and distances to both. 

    """
    rng = np.random.default_rng(seed)
    dest = generate_random_point_on_line(edges, rng)
    while orig['point'].distance(dest['point']) < min_dist:
        dest = generate_random_point_on_line(edges, rng)
    return dest



def get_directed_edge(graph, nodes, start, end):
    """
        Get edge from graph and check whether the edge starts at current node and ends at next node or the other way around, eventually switch direction and adjust one way attributes. 
        
        Parameters
        ----------
        edge : shapely.geometry.line.Linestring
            Edge from graph

        Returns
        -------
        edge
            The corrected edge 
    """
    edge = graph.get_edge_data(start, end)
    if(edge['geometry'].coords[0] != nodes.loc[nodes['nodeID'] == start]['geometry'].values[0].coords[0]):
    # invert indice order
        owr = False
        ow = False
        if edge['one_way']:
            owr = True
        if edge['one_way_reversed']:
            ow = True
        edge['one_way'] = ow
        edge['one_way_reversed'] = owr 
        edge['geometry'] = LineString(list(edge['geometry'].coords)[::-1])
    return edge

