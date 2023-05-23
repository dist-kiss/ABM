import networkx as nx
import movement
from shapely.ops import substring, Point, LineString


# TODO: FIX initial position bug (still TODO?)
def add_temporary_node(graph: nx.Graph, edge_start, edge_end, split_dist, name, x, y):
        """Adds a temporary node to a given graph.
        
        Args: 
            graph (nx.Graph): Graph to add node to
            edge_start: starting node of edge on which new node will be placed
            edge_end: ending node of edge on which new node will be placed
            split_dist: distance from starting node along edge at which new node shall be placed 
            name: name of new node
            x: x-coordinate of new node
            y: y-coordinate of new node
        """

        edge = movement.get_directed_edge(graph, edge_start, edge_end)
        near_to_exact = substring(edge['geometry'], start_dist=0, end_dist=split_dist)
        near_to_exact = LineString(list(near_to_exact.coords)[::-1])
        exact_to_remote = substring(edge['geometry'], start_dist=split_dist, end_dist=edge['geometry'].length)
        graph.add_node(name, pos=(x,y), nodeID='name', degree=2)
        graph.add_edge(name,edge_start, mm_len=split_dist, 
                    geometry=near_to_exact, ID=str(name+"_1"), one_way = not edge['one_way'],
                    one_way_reversed = not edge['one_way_reversed'], highway = edge['highway'],
                    sidewalk_width = edge['sidewalk_width'])
        graph.add_edge(name, edge_end, mm_len=(edge['geometry'].length - split_dist),
                    geometry=exact_to_remote, ID=str(name+"_2"), one_way=edge['one_way'],
                    one_way_reversed=edge['one_way_reversed'], highway = edge['highway'],
                    sidewalk_width = edge['sidewalk_width'])


def remove_intermediate_node(graph, name):
        """Removes a node from a given graph
        
            Args:
                graph: graph to remove node from
                name: name of node to remove
        """
        graph.remove_node(name)


# --- SETTER FUNCTIONS ------

def increase_edge_counter(edge, amount):
        """ Increase people counter for a given edge by a given amount

            Args:
            edge: The edge to increase the counter of 
            amount: The amount to increase counter by 
        """
        edge['temp_ppl_increase'] += amount
        edge['ppl_total'] += amount

def decrease_edge_counter(edge, amount):
        """ Decrease people counter for a given edge by a given amount

                Args:
                edge: The edge to decrease the counter of 
                amount: The amount to decrease counter by 
        """
        edge['temp_ppl_increase'] -= amount

# --- Alternative Path Computation --------
def get_alternative_path(network, path, metric_path_length, previous_edge, ows, id, logging=False):
        """ Returns an alternative path from the current node of an agent to its destination, 
            which does not use the first edge of the current path. In general turning around is forbidden, 
            unless a (forbidden to enter) one way street is on the next edge. Then agent is allowed to turn around. 
            If there is no alternative path, return inital path.
        
        Args:
            network (nx.Graph): Graph to search for alternative path
            path (list): Given path to find alternative to 
            metric_path_length (float): Length of the inital path 
            previous_edge: the previously walked edge/street
            ows (boolean): whether next intended edge is (forbidden to enter) one way street  
            id (int): id of the current agent  
            logging (boolean): whether logging shall be enabled (for debugging)

        Returns:
            list, float : The alternative path and the detour it takes
        """
        # create variables for current node, the next node and the last node (destination) on the current path
        current_node = path[0]
        next_node = path[1]
        destination = path[-1]
        
        # define function to remove edges from a network
        def filter_edge(n1, n2):
            return network[n1][n2].get("walkable", True)
        
        # temporarily remove next intended edge from graph
        network[current_node][next_node]["walkable"] = False
        # if next street is not a ows, filter also previous edge (forbids turning around!)
        if(not ows):
            previous_edge['walkable'] = False
        view = nx.subgraph_view(network, filter_edge=filter_edge)

        # try finding an alternative path
        try:
            # compute alternative path and its length
            alt_path = nx.dijkstra_path(view, source=current_node, target=destination, weight='mm_len')
            alt_length = nx.path_weight(view, alt_path, weight='mm_len')
            # reset filter attribute for next intended edge and previous
            network[current_node][next_node]["walkable"] = True
            previous_edge['walkable'] = True
            if(logging):
                # if logging: print alternative and current path lengths
                print('alt: '+ str(alt_length) + ' orig: ' + str(metric_path_length))
            return alt_path, alt_length - metric_path_length
        
        # if there is no alternative path return inital path
        except (nx.NetworkXNoPath) as e:
            print("No alternative for agent " + str(id) + ' at node ' + str(current_node)+ '.')
            # reset filter attribute for next intended edge and previous
            network[current_node][next_node]["walkable"] = True
            previous_edge['walkable'] = True
            return path, 0