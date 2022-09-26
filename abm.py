# Model design
import agentpy as ap
import networkx as nx
import random
import geopandas
from pandas import concat, DataFrame
import momepy
import datetime
from collections import Counter
import movement
import math


# Visualization
import matplotlib.pyplot as plt 

# TODO: 
# - use results of the study to calibrate the ows threshold
# - add probability to take another path (without intervention)
# - sensitivity analysis -> parameters vs. relative detour | mean & sd compliance rates

class Pedestrian(ap.Agent):

    def setup(self):
        """Initializes an agent of type pedestrian with its attributes
        """

        # Init random number generator for each agent using seed; for reproducibility
        seed = self.model.random.getrandbits(128)
        self.rng = random.Random(seed)
        
        # Initialize attributes
        # walking speed is based on average walking speed and its standard deviation
        # Source: Satish Chandra and Anish Khumar Bharti 2013, p. 662, "Speed Distribution Curves for Pedestrians during Walking and Crossing"
        self.walking_speed = self.rng.gauss(1.25, 0.21)
        self.walking_distance = self.walking_speed * self.model.p.duration
        self.network = self.model.G.to_directed()
        self.density_threshold = round( 0.03 + self.rng.random() * 0.07, 4)
        # self.ows_threshold = 0.75 + self.rng.random() * 0.25
        # self.detour_threshold = 0.75 + self.rng.random() * 0.25
        self.ovr_risk_tolerance = 0.8 + self.rng.random() * 0.2

        # Initialize variables 
        self.num_detours = 0
        self.metric_path = []
        self.leftover_distance = 0
        self.len_traversed = 0

        # Choose random origin and destination within street network
        self.orig, self.dest = movement.get_random_org_dest(self.model.edges, seed, 250)

        # Get the closest nodes in the network for origin and destination
        self.orig_node_id = self.orig['nearer_node']
        self.dest_node_id = self.dest['nearer_node']
        #TODO: Place agents in the model at different times
        
        # Compute shortest path to destination
        self.agent_compute_path(self.orig_node_id, self.dest_node_id)

        # if origin not on first edge of metric path
        if len(self.metric_path) < 2 or self.metric_path[1] != self.orig['remote_node']:
            # add remote node of origin to path as first node (now origin will be on first edge of path)
            self.metric_path.insert(0, self.orig['remote_node'])
            # set distance between first node of path and origin
            self.start_at_dist = self.orig['dist_from_remote']
        else:
            # set distance between first node of path and origin
            self.start_at_dist = self.orig['dist_from_nearer']

        # if destination not on last edge of metric path
        if len(self.metric_path) < 2 or self.metric_path[-2] != self.dest['remote_node']:
            # add remote node of destination to path as last node (now destination will be on last edge of path)
            self.metric_path.append(self.dest['remote_node'])
            # set distance between penultimate node of path and destination
            self.walk_to_dest = self.dest['dist_from_nearer']
        else:
            # set distance between penultimate node of path and destination
            self.walk_to_dest = self.dest['dist_from_remote']
            
        # set the location of the agent to its origin
        self.first_position()        

        
    def agent_compute_path(self, start_node, dest_node):
        """Calculate the shortest path from the agents current location to its destination.
            Stores result as list of nodes in a shortest path.
        """
        self.metric_path = nx.dijkstra_path(self.model.G, source=start_node, target=dest_node, weight='mm_len')
        self.metric_path_length = nx.path_weight(self.model.G, self.metric_path, weight='mm_len')

    def first_position(self):
        """Calculates the first position of an agent and creates a location dict to store location information of the agent. 
            Also sets further attributes, such as edge counter attributes and the leftover distance to the next node. 
        """        
        # Update people counter of current edge
        current_undirected_edge = self.model.G[self.metric_path[0]][self.metric_path[1]]
        current_undirected_edge['temp_ppl_increase']+=1
        current_undirected_edge['ppl_total']+=1
        
        # Get the edge the agent starts on (corrected direction)
        current_directed_edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0], self.metric_path[1])
        
        # Set distance to next node
        self.leftover_distance = current_directed_edge['mm_len'] - self.start_at_dist
        
        # Create dict for agent location and related attributes
        self.location = {
            'geometry': current_directed_edge['geometry'].interpolate(self.start_at_dist),
            'agentID': self.id,
            'finished': False,
            'density_threshold': self.density_threshold,
            'latest_node': self.metric_path[0],
            'non-compliance': False,
            'compliance': False
        }

                    
    def reset_location_compliance(self):
        """Resets location compliance values.
        """
        self.location['non-compliance'] = False
        self.location['compliance'] = False 
    
    def not_reached_destination(self):
        """Checks whether agent has not reached its destination yet and returns boolean.

        Returns:
            Boolean: Boolean indicating if agent has not yet reached its destination
        """
        # if agent reached its destination, return
        if len(self.metric_path) < 2:
            self.location['finished'] = True
            self.reset_location_compliance()
            return False
        else: 
            return True
    
    def check_next_node(self):
            # check if agent is on node 
        if(self.leftover_distance == 0):
            # agent left last edges, so reset compliance attributes
            self.reset_location_compliance()

            # evaluate next street segment regarding interventions 
            self.check_next_street_segment()
            
            # get next edge and set agent leftover distance and edge attributes
            current_undirected_edge = self.model.G[self.metric_path[0]][self.metric_path[1]]
            
            # If on penultimate node, then use walk_to_dest distance to only walk until destination point on edge is reached
            if len(self.metric_path) == 2:
                self.leftover_distance = self.walk_to_dest
            # else use length of next edge for leftover_distance to continue walking along the path
            else:
                self.leftover_distance = current_undirected_edge['mm_len']
            
            # Update people counter of next edge
            current_undirected_edge['temp_ppl_increase']+=1
            current_undirected_edge['ppl_total']+=1
            # TODO: Implement waiting at node if there is no alternative option and pedestrian is unsatisfied

                           
    def get_next_position(self):
        """Calculates the position of an agent after the next timestep, dependent on the duration 
            of a timestep and the walking speed of the agent.
        """
        # get the edge the agent walks on
        current_directed_edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0], self.metric_path[1])

        # if pedestrian would walk past next node stop at next node instead 
        if  self.walking_distance > self.leftover_distance:
            # increase length traversed by leftover distance
            self.len_traversed += self.leftover_distance
            # reset leftover distance
            self.leftover_distance = 0
            # reduce people counter of current edge
            self.model.G[self.metric_path[0]][self.metric_path[1]]['temp_ppl_increase']-=1
            # erase first node from current path list 
            self.metric_path.pop(0)
            # update remaining path length
            self.metric_path_length = nx.path_weight(self.model.G, self.metric_path, weight='mm_len')
            # get current node as dict
            new_location_node = self.model.nodes.loc[[self.metric_path[0]]].to_dict(orient='records')[0]
            
            
            # if agent has reached final destination, update location of agent accordingly
            if len(self.metric_path) == 1:
                final_location = current_directed_edge['geometry'].interpolate(self.walk_to_dest)
                self.location.update( [('latest_node', self.metric_path[0]),('geometry', final_location)] )
            # else use next node location to update agent location
            else:
                self.location.update( [('latest_node', self.metric_path[0]),('geometry', new_location_node['geometry'])] )
        # if next node is not reached go on with calculation of next position
        else:
            # increase length traversed by walking_distance
            self.len_traversed += self.walking_distance
            # update location of agent using walking distance within current timestep
            self.leftover_distance = self.leftover_distance - self.walking_distance
            
            # if on last edge use walk_to_distance instead of edge length for next location calculation
            if len(self.metric_path) == 3:
                self.location['geometry'] = current_directed_edge['geometry'].interpolate(self.walk_to_dest - self.leftover_distance)
            else:
                self.location['geometry'] = current_directed_edge['geometry'].interpolate(current_directed_edge['mm_len'] - self.leftover_distance)
            

    def check_next_street_segment(self):
        """Checks whether the next street segement has an intervention 
            that stops the agent from accessing it. If there is an obstacle, 
            evaluate whether to comply and eventually change the agents path.
        """
        edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0],self.metric_path[1])
        # if one way street forbidden to enter
        if(edge['one_way_reversed']):
            # calculate alternative patha and detour
            alt_path, detour = self.get_alternative_path(self.metric_path, self.metric_path_length)
            # if (alt_path ==  self.metric_path):
            #     return True
            
            # evaulate compliance and eventually change path
            if(self.ows_evaluation(detour, edge)):
                self.metric_path = alt_path
                self.num_detours += 1


    def ows_evaluation(self, detour, edge):
        """Evalutes whether agent complies with one way street intervention and returns decision as boolean.
            Formula F(x1,...,xn) for the chance to comply is:
            F(detour, remaining_shortest_path_length = rspl, edge_density, impatience) 
            = detour/rspl * detour_weight + edge_density * density_weight + impatience * impatience_weight

        Args:
            detour (float): The detour length the alternative option would result in 
            edge (_type_): The one way street edge

        Returns:
            Boolean: True if the agent complies with the intervention, False if it does not comply
        """
        # TODO: Look at regression and how to potentially use it for the evaluation part
        x = self.rng.random()
        forbidden = 1
        rel_tot_detour = detour/(self.len_traversed + self.metric_path_length)
        z = 0.1899 + rel_tot_detour * 3.8243 - forbidden * 1.2794 
        prop_noncompliance = 1/(1+ math.exp(-z))
        # norm_detour = detour/self.metric_path_length
        # # detour
        # prop_noncompliance += detour * self.model.p.detour_weight
        # prop_noncompliance += norm_detour * self.model.p.remaining_length_weight
        if(self.model.p.density):
            prop_noncompliance += edge['density'] * self.model.p.density_weight 
            # self.density_threshold?
        if(self.model.p.impatience):
            prop_noncompliance += self.num_detours * self.model.p.impatience_weight
        prop_noncompliance = prop_noncompliance * self.ovr_risk_tolerance
        if(x > prop_noncompliance):
            # print("Compliance, " + str(self.id))
            self.location['compliance'] = True
            self.model.compliances += 1
            return True
        else:
            print("P: " + str(prop_noncompliance) + "; X: " + str(x))
            self.location['non-compliance'] = True
            self.model.non_compliances += 1
            print("Non-Compliance, " + str(self.id))
            return False   

    # def deprecated_ows_evaluation(self, detour, edge):
    #     """Evalutes whether agent complies with one way street intervention and returns decision as boolean.
    #         Formula F(x1,...,xn) for the chance to comply is:
    #         F(detour, remaining_shortest_path_length = rspl, edge_density, impatience) 
    #         = detour/rspl * detour_weight + edge_density * density_weight + impatience * impatience_weight

    #     Args:
    #         detour (float): The detour length the alternative option would result in 
    #         edge (_type_): The one way street edge

    #     Returns:
    #         Boolean: True if the agent complies with the intervention, False if it does not comply
    #     """
    #     x = self.rng.random() * 100
    #     compliance = 0
    #     norm_detour = detour/self.metric_path_length
    #     compliance += max(1 - 0.5 * norm_detour, 0) * 100
    #     if(self.model.p.density):
    #         compliance += edge['density'] / self.density_threshold * 50
    #     if(self.model.p.impatience):
    #         compliance -= self.num_detours * 10
    #     compliance = compliance * self.ovr_risk_tolerance
    #     if(x < compliance):
    #         # print("Compliance, " + str(self.id))
    #         self.location['compliance'] = True
    #         self.model.compliances += 1
    #         return True
    #     else:
    #         self.location['non-compliance'] = True
    #         self.model.non_compliances += 1
    #         print("Non-Compliance, " + str(self.id))
    #         return False   

        
    def get_alternative_path(self, path, metric_path_length):
        """Returns an alternative path from the model graph to the agents destination, which does not use the first edge of the current path.
            If first edge of the current path has one way street reversed intervention, than iteratively call this function until alternative path is not
            or until there is no alternative path left. In that case, return inital path.
        
        Args:
            path (list): Given path to find alternative to 
            metric_path_length (float): Length of the inital path 

        Returns:
            list, float: The alternative path and its length         
        """
        # create variables for current node, the next node and the last node (destination) on the current path
        current_node = path[0]
        next_node = path[1]
        destination = path[-1]
        
        # filter out next edge on path from graph in a subview
        self.network[current_node][next_node]["walkable"] = False
        def filter_edge(n1, n2):
            return self.network[n1][n2].get("walkable", True)
        view = nx.subgraph_view(self.network, filter_edge=filter_edge)
        
        try:
            # compute alternative path and its length on subview
            alternative_path = nx.dijkstra_path(view, source=current_node, target=destination, weight='mm_len')
            length = nx.path_weight(view, alternative_path, weight='mm_len')
            # check whether next edge on alternative path is one way street (forbidden to enter)
            next_edge = movement.get_directed_edge(self.model.G, self.model.nodes, alternative_path[0],alternative_path[1])
            if(next_edge['one_way_reversed']):
                # iteratively call this function (until alternative path has no intervention on first edge)
                return self.get_alternative_path(alternative_path, metric_path_length)
            else:
                # reset walkability attribute of graph 
                self.network[current_node][next_node]["walkable"] = True
                # print('alt: '+ str(length) + 'orig: ' + str(metric_path_length))
                return alternative_path, length - metric_path_length
        
        # if there is no alternative path return inital path
        except (nx.NetworkXNoPath) as e:
            print("No alternative for agent " + str(self.id) + ' at node ' + str(self.location['nodeID'])+ '.')
            # reset walkability attribute of graph 
            self.network[current_node][next_node]["walkable"] = True
            return path, 0

class MyModel(ap.Model):

    def setup(self):
        self.create_graph(streets_gpkg=self.p.streets_path)
        
        # opt. visualize network nodes, edges and degree values
        if self.p.viz:
            self.visualize_model()

        # Create a list of agents 
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)
        
        # Create lists for position and edge data and compliance counter 
        self.position_list = []
        self.edge_gdf = []
        self.compliances = 0
        self.non_compliances = 0
        self.step_counter = 0

                    
    def step(self):
        """Call a method for every agent. 
        """
        # Calculate next position for all agents
        selected_agents = self.agents.select(self.agents.not_reached_destination()) 
        selected_agents.check_next_node()
        selected_agents.get_next_position()
        self.step_counter += 1

    def update(self):
        # update edge pedestrian counter attributes
        ppl_count = Counter(nx.get_edge_attributes(self.model.G, "ppl_count"))
        temp_count = Counter(nx.get_edge_attributes(self.model.G, "temp_ppl_increase"))
        length = nx.get_edge_attributes(self.model.G, "mm_len")
        density = dict(Counter({key : ppl_count[key] / length[key] for key in ppl_count}))
        ppl_count.update(temp_count)
        ppl_count=dict(ppl_count)
        self.max_density = {k:max(density.get(k,float('-inf')), self.max_density.get(k, float('-inf'))) for k in density.keys()}
        nx.set_edge_attributes(self.model.G, ppl_count, "ppl_count")
        nx.set_edge_attributes(self.model.G, density, "density")
        nx.set_edge_attributes(self.model.G, 0, "temp_ppl_increase")

        """ Record a dynamic variable. """
        # self.agents.record('metric_path')
        self.model.record('non_compliances')
        self.model.record('compliances')
        
        # update fake date for temporal viz in qgis
        time = datetime.datetime(2000, 1, 1, self.step_counter * self.model.p.duration // 3600, self.step_counter * self.model.p.duration // 60, self.step_counter * self.model.p.duration % 60)
        
        # store all the agents current location in list and add time abd counter attributes
        positions = self.agents.location.copy()
        for agent_position in positions:
            agent_position['time']= time
            agent_position['counter']= self.step_counter
            self.position_list.append(agent_position)

        # store edge information in dataframe
        nx.set_edge_attributes(self.model.G, self.step_counter, "counter")
        nx.set_edge_attributes(self.model.G, time, "time")
        edges = momepy.nx_to_gdf(self.model.G, points=False)
        self.edge_gdf.append(edges)

    def end(self):
        """ Report an evaluation measure. """
        # output density maximum per street
        nx.set_edge_attributes(self.model.G, self.max_density, "max_density")
        max_density_gdf = momepy.nx_to_gdf(self.model.G, points=False)
        max_density_gdf.to_file('./output/max_density.gpkg', driver='GPKG', layer='Max Density Edges') 
        # output position data as gpkg 
        all_positions = DataFrame(self.position_list) 
        final_gdf = geopandas.GeoDataFrame(all_positions, geometry=all_positions['geometry'], crs="EPSG:3857")
        final_gdf.to_file('./output/positions.gpkg', driver='GPKG', layer='Agents_temporal') 
        # output edge data as gpkg 
        final_edge_gdf = concat(self.edge_gdf, ignore_index=True)
        final_edge_gdf.to_file('./output/edges.gpkg', driver='GPKG', layer='Edges_temporal')
        # print compliance statistics         
        print("Compliances: " + str(self.compliances) + "; Non-Compliances: " + str(self.non_compliances))

    def visualize_model(self):
        """Visualizes the model as animation.
            TODO: Update visualization part.
        """
        f, ax = plt.subplots(figsize=(10, 10))
        self.nodes.plot(ax=ax, column='degree', cmap='tab20b', markersize=(2 + self.nodes['nodeID'] * 4), zorder=2)
        self.edges.plot(ax=ax, color='lightgrey', zorder=1)
        ax.set_axis_off()
        plt.show()
            
    def create_graph(self, streets_gpkg):
        """Creates the network graph for the model based on an given gpkg linestring file. 

        Args:
            streets_gpkg (str): Path to gpkg linestring file
        """
        # Read street network as geopackage and convert it to GeoDataFrame
        streets = geopandas.read_file(streets_gpkg)
        # Transform GeoDataFrame to networkx Graph
        self.G = nx.Graph(momepy.gdf_to_nx(streets, approach='primal'))
        # Calculate degree of nodes
        self.G = momepy.node_degree(self.G, name='degree')
        # Convert graph back to GeoDataFrames with nodes and edges
        self.nodes, self.edges, sw = momepy.nx_to_gdf(self.G, points=True, lines=True, spatial_weights=True)
        # set index column, and rename nodes in graph
        self.nodes = self.nodes.set_index("nodeID", drop=False)
        self.nodes = self.nodes.rename_axis([None])
        self.G = nx.convert_node_labels_to_integers(self.G, first_label=0, ordering='default', label_attribute=None)
        # mapping = dict(zip([(geom.x, geom.y) for geom in self.nodes['geometry'].tolist()], self.nodes.index[self.nodes['nodeID']-1].tolist()))
        # self.G = nx.relabel_nodes(self.G, mapping)
        nx.set_edge_attributes(self.G, 0, "ppl_count")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_increase")
        nx.set_edge_attributes(self.G, 0, "ppl_total")
        nx.set_edge_attributes(self.G, 0, "density")
        density = nx.get_edge_attributes(self.G, "density")
        self.max_density = density
        nx.set_edge_attributes(self.G, 0, "max_density")
        # nx.set_edge_attributes(self.G, False, "oneway_from")


# specify model parameters
parameters = {
    'agents': 400,
    'steps': 100,
    'viz': False,
    'duration': 5,
    'density': False,
    'impatience': False,
    'seed': 40,
    'detour_weight': 0.1,
    'remaining_length_weight': 50,
    'density_weight': 1,
    'impatience_weight': -0.5,
    'streets_path': "./network-data/quakenbrueck_clean_alternate_ows.gpkg"
}

# Run the model!
model = MyModel(parameters)
results = model.run()