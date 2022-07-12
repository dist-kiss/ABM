from shapely.geometry import Point, LineString
from shapely.ops import split, nearest_points, snap


def generate_random_orig_dest(polygon, min_dist, rng):
    """Create random origin and destination coordinates inside model polygon boundaries
    with a minimum distance of min_dist (meter) apart.

    Parameters
    ----------
    allowed_polygon : shapely.geometry.polygon.Polygon
        Polygon - sets spatial boundaries to the origin and destination points 
    min_dist : float
        minimum distance between origin and destination

    Returns
    -------
    Point, Point
        Origin and destination as shapely.geometry.point.Point
    """
    # Init random number generator
    points = []
    minx, miny, maxx, maxy = polygon.bounds.values[0]
    while len(points) < 2:
        pnt = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        # check if point in allowed area
        if polygon.contains(pnt).values[0]:
            # check if there is a origin already
            if len(points) == 1:
                # make sure next point is at least min_dist apart
                distance = points[0].distance(pnt)
                if distance > min_dist:
                    points.append(pnt)
            else:
                # set origin
                points.append(pnt)
    return points[0], points[1]        

def get_nearest_node(nodes, point):
    """Return the nearest node to a given point from of a set of nodes.

        Parameters
        ----------
        nodes : geopandas.GeoDataFrame
            GeoDataFrame with multiple point geometries 
        point : shapely.geometry.point.Point
            Point  

        Returns
        -------
        Index
            The GeoDataFrame index of the nearest node 
    """
    multipoint = nodes.geometry.unary_union
    queried_geom, nearest_geom = nearest_points(point, multipoint)
    res = nodes.index[nodes['geometry'] == nearest_geom].tolist()[0]
    return res


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

