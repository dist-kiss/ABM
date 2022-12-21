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
import os
import numpy as np
from pathlib import Path
import time    

# Visualization
import matplotlib.pyplot as plt 

# TODO: 
# - use results of the study to calibrate the ows threshold
# - sensitivity analysis -> parameters vs. relative detour | mean & sd compliance rates

class Pedestrian(ap.Agent):

    def setup(self):
        """Initializes an agent of type pedestrian with its attributes
        """

        # Init random number generator for each agent using seed; for reproducibility
        seed = self.model.random.getrandbits(128)
        destinationSeed = self.model.random.getrandbits(128)
        self.rng = random.Random(seed)
        self.randomDestinationGenerator = np.random.default_rng(destinationSeed)
        
        # Initialize attributes
        # walking speed is based on average walking speed and its standard deviation
        # Source: Satish Chandra and Anish Khumar Bharti 2013, p. 662, "Speed Distribution Curves for Pedestrians during Walking and Crossing"
        self.walking_speed = self.rng.gauss(1.25, 0.21)
        self.walking_distance = self.walking_speed * self.model.p.duration
        self.network = self.model.G.to_directed()
        self.density_threshold = round( 0.03 + self.rng.random() * 0.07, 4)
        # self.ows_threshold = 0.75 + self.rng.random() * 0.25
        # self.detour_threshold = 0.75 + self.rng.random() * 0.25

        # TODO: Justify risk_appetite value. Is this concept valid 
        # Higher values -> more willingness to not comply with measures
        self.risk_appetite = self.rng.gauss(self.model.p.risk_appetite_mean, self.model.p.risk_appetite_std)

        # Initialize variables 
        self.num_detours = 0
        self.metric_path = []
        self.remaining_dist_on_edge = 0
        self.len_traversed = 0
        self.route_counter = 0
        self.init_shortest_path_length = 0
        self.non_comp_probs = []
        # Choose random origin and destination within street network
        self.orig, self.dest = movement.get_random_org_dest(self.model.edges, self.randomDestinationGenerator, 250)

        # Get the closest nodes in the network for origin and destination
        self.orig_node_id = self.orig['nearer_node']
        self.dest_node_id = self.dest['nearer_node']
        #TODO: Place agents in the model at different times
        
        # Compute shortest path to destination
        self.agent_compute_path(self.orig_node_id, self.dest_node_id)

        # Add actual origin and destination to the node based path
        self.add_exact_orig_to_path()
        self.metric_path, self.metric_path_length, self.distance_penult_node_to_dest = self.add_exact_dest_to_path(self.metric_path, self.metric_path_length)
        self.init_shortest_path_length = self.metric_path_length
        # set the location of the agent to its origin
        self.first_position()

        
    def agent_compute_path(self, start_node, dest_node):
        """Calculate the shortest path from the agents current location to its destination and the length of the path.
            Stores result as agent variables (list of nodes in a shortest path, float).

        Args:
            start_node (int): ID of path starting node
            dest_node (int): ID of path destination node
        """
        self.metric_path = nx.dijkstra_path(self.model.G, source=start_node, target=dest_node, weight='mm_len')
        self.metric_path_length = nx.path_weight(self.model.G, self.metric_path, weight='mm_len')

    def add_exact_orig_to_path(self):
        """Check whether node based path includes exact origin location and add another node if necessary. 
            Set starting offset distance to distance between first node in graph and exact origin location.  
        """

        origin_not_on_first_edge = len(self.metric_path) < 2 or self.metric_path[1] != self.orig['remote_node']
        if origin_not_on_first_edge:
            # add remote node of origin to path as first node (now origin will be on first edge of path)
            self.metric_path.insert(0, self.orig['remote_node'])
            # set distance between first node of path and origin
            self.start_at_dist = self.orig['dist_from_remote']
            self.metric_path_length += self.orig['dist_from_nearer'] 
        else:
            # set distance between first node of path and origin
            self.start_at_dist = self.orig['dist_from_nearer']
            self.metric_path_length += self.orig['dist_from_remote'] 


    def add_exact_dest_to_path(self, path, path_length):
        """Check whether node based path includes exact destination location and add another node if necessary. 
            Set destination offset distance to distance between penultimate node in graph and exact destination location.  
        Args:
            path (list): The path as list of nodes 
            path_length (float): The length of the path

        Returns:
            List: Manipulated path
            Float: Manipulated path length
        """

        destination_not_on_last_edge = len(path) < 2 or path[-2] != self.dest['remote_node']
        if destination_not_on_last_edge:
            # add remote node of destination to path as last node (now destination will be on last edge of path)
            path.append(self.dest['remote_node'])
            # set distance between penultimate node of path and destination
            distance_penultimate_to_dest = self.dest['dist_from_nearer']
            path_length += distance_penultimate_to_dest
        else:
            # set distance between penultimate node of path and destination
            distance_penultimate_to_dest = self.dest['dist_from_remote']
            path_length -= self.dest['dist_from_nearer']

        return path, path_length, distance_penultimate_to_dest


    def first_position(self):
        """Calculates the first position of an agent and creates a location dict to store location information of the agent. 
            Also sets further attributes, such as edge counter attributes and the remaining distance to the next node. 
        """        
        # Update people counter of current edge
        current_undirected_edge = self.model.G[self.metric_path[0]][self.metric_path[1]]
        current_undirected_edge['temp_ppl_increase']+=1
        current_undirected_edge['ppl_total']+=1
        
        # Get the edge the agent starts on (corrected direction)
        current_directed_edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0], self.metric_path[1])
        
        # Set distance to next node
        self.remaining_dist_on_edge = current_directed_edge['mm_len'] - self.start_at_dist
        
        # Create dict for agent location and related attributes
        self.location = {
            'geometry': current_directed_edge['geometry'].interpolate(self.start_at_dist),
            'agentID': self.id,
            'route_counter': self.route_counter,
            'density_threshold': self.density_threshold,
            'latest_node': self.metric_path[0],
            'non_compliance': False,
            'compliance': False
        }


    def assign_new_destination(self):
        """Assigns a new destination to the agent. 
            Function uses previous destination as new origin and generates 
            new destination. Then calculates a new path between these and assigns 
            path to the agent. 
        """        
        # increase route counter
        self.route_counter += 1

        # reset non-compliance probability array
        self.non_comp_probs = []

        # use previous destination as origin
        self.orig = self.dest.copy()

        # Find new random destination within street network
        self.dest = movement.get_random_dest(self.orig, self.model.edges, self.randomDestinationGenerator, 250)

        # Get the closest nodes in the network for origin and destination
        self.orig_node_id = self.orig['nearer_node']
        self.dest_node_id = self.dest['nearer_node']
        
        # Compute shortest path to destination
        self.agent_compute_path(self.orig_node_id, self.dest_node_id)

        # Add actual origin and destination to the node based path
        self.add_exact_orig_to_path()
        self.metric_path, self.metric_path_length, self.distance_penult_node_to_dest = self.add_exact_dest_to_path(self.metric_path, self.metric_path_length)
        self.init_shortest_path_length = self.metric_path_length
        # Calculate first position and attributes
        self.first_position()   

                    
    def reset_location_compliance(self):
        """Resets location compliance values.
        """
        self.location['non_compliance'] = False
        self.location['compliance'] = False 
        self.location['random_rerouting'] = False
    
    
    def check_next_node(self):
        """For agents that are on street intersection, evaluates next street for possible interventions.
        """        

        is_agent_on_node = (self.remaining_dist_on_edge == 0)
        if(is_agent_on_node):
            if self.model.p.scenario in ["simple_compliance", "complex_compliance"]:
                # agent left last edges, so reset compliance attributes
                self.reset_location_compliance()
            
            current_undirected_edge = None 

            is_on_penultimate_node = (len(self.metric_path) == 2)
            if is_on_penultimate_node:
                # get next edge
                current_undirected_edge = self.model.G[self.metric_path[0]][self.metric_path[1]]
                # Set remaining distance to distance between penultimate graph node and destination
                self.remaining_dist_on_edge = self.distance_penult_node_to_dest
            else: # not on penultimate node
                # evaluate next street segment regarding interventions or random rerouting
                self.check_next_street_segment()
                # get next edge
                current_undirected_edge = self.model.G[self.metric_path[0]][self.metric_path[1]]
                # Set remaining distance to edge length
                self.remaining_dist_on_edge = current_undirected_edge['mm_len']

            # Update people counter of next edge
            current_undirected_edge['temp_ppl_increase'] += 1
            current_undirected_edge['ppl_total'] += 1
            # TODO: Implement waiting at node if there is no alternative option and pedestrian is unsatisfied

                           
    def walkUntilNode(self, next_location):
        """Simulate agent walking until the next node. Update path and agent attributes. 
        """
        # increase length traversed by the remaining distance to next node
        self.len_traversed += self.remaining_dist_on_edge
        # erase first node from current path list 
        self.metric_path.pop(0)
        # update remaining path length
        self.metric_path_length = self.metric_path_length - self.remaining_dist_on_edge 
        # reset remaining distance
        self.remaining_dist_on_edge = 0
        # update location of agent accordingly
        self.location.update( [('latest_node', self.metric_path[0]),('geometry', next_location)] )

    def walkAlongStreet(self, current_directed_edge, edge_length):
        """Simulate agent walking along the street for duration of one time step. 
            Update path and agent attributes. 
        """
        # increase length traversed by the remaining distance to next node
        self.len_traversed += self.walking_distance
        # update remaining path length
        self.metric_path_length = self.metric_path_length - self.walking_distance 
        # update location of agent using walking distance within current timestep
        self.remaining_dist_on_edge = self.remaining_dist_on_edge - self.walking_distance
        # update location of agent accordingly
        next_location = current_directed_edge['geometry'].interpolate(edge_length - self.remaining_dist_on_edge)
        self.location.update([('geometry', next_location)])

    def get_next_position(self):
        """Calculates the position of an agent after the next timestep, dependent on the duration 
            of a timestep and the walking speed of the agent.
        """
        current_directed_edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0], self.metric_path[1])
        would_walk_beyond_next_node = (self.walking_distance > self.remaining_dist_on_edge)
        is_on_last_edge = (len(self.metric_path) == 2)

        if(is_on_last_edge):
            if would_walk_beyond_next_node:
                final_location = current_directed_edge['geometry'].interpolate(self.distance_penult_node_to_dest)
                self.walkUntilNode(final_location)
                nod = (self.len_traversed / self.init_shortest_path_length) - 1
                # add normalized observed detour (NOD) to model reporter
                self.model.TPLs.append(self.len_traversed)
                self.model.SPLs.append(self.init_shortest_path_length)
                self.model.NODs.append(nod)
                # add non-compliance probablities of current route to model reporter
                self.model.non_comp_probs.extend(self.non_comp_probs)
                # assign new destination to walk towards
                self.assign_new_destination()
            else: # will not reach destination in this timestep
                self.walkAlongStreet(current_directed_edge, self.distance_penult_node_to_dest)

        else: # not on last edge
            if would_walk_beyond_next_node:
                # agent stops at that next node instead, get node location
                next_node = self.model.nodes.loc[[self.metric_path[1]]].to_dict(orient='records')[0]
                # reduce people counter of current edge
                self.model.G[self.metric_path[0]][self.metric_path[1]]['temp_ppl_increase']-=1
                self.walkUntilNode(next_node['geometry'])
            else: # will not reach next node in this timestep
                self.walkAlongStreet(current_directed_edge, current_directed_edge['mm_len'])


    def check_next_street_segment(self):
        """Checks whether the next street segement has an intervention 
            that stops the agent from accessing it. If there is an obstacle, 
            evaluate whether to comply and eventually change the agents path.
        """
        next_edge = movement.get_directed_edge(self.model.G, self.model.nodes, self.metric_path[0],self.metric_path[1])

        # calculate alternative path and detour
        alt_path, detour, distance_penult_node_to_dest = self.get_alternative_path(self.metric_path, self.metric_path_length)
        
        if(next_edge['one_way_reversed']): # next street entry forbidden
            if self.model.p.scenario in ["simple_compliance", "complex_compliance"]:
                decides_to_comply = self.ows_evaluation(detour, next_edge)
                if(decides_to_comply):
                    self.location['compliance'] = True
                    self.model.compliances += 1
                    # replace initial path by alternative one
                    self.metric_path = alt_path
                    self.metric_path_length += detour
                    self.distance_penult_node_to_dest = distance_penult_node_to_dest
                    self.num_detours += 1
                else: 
                    self.location['non_compliance'] = True
                    self.model.non_compliances += 1
            else:
                self.model.non_compliances += 1
            return

        # TODO: Check if agents should be allowed to walk through forbidden paths as result of random rerouting, 
        # currently restricted by get_alternative_path() function
        if(self.model.p.generic_reouting_method == 'regression' and self.generic_rerouting_regression(detour)): 
            self.metric_path = alt_path
            self.metric_path_length += detour
            self.distance_penult_node_to_dest = distance_penult_node_to_dest
            self.location['random_rerouting'] = True

        elif(self.generic_rerouting_probability()):
            self.metric_path = alt_path
            self.metric_path_length += detour
            self.distance_penult_node_to_dest = distance_penult_node_to_dest
            self.location['random_rerouting'] = True

    def generic_rerouting_probability(self):
        """Evaluates at every node whether an agent would stay on his current path or take an alternative path.
        The alternative path will be the second-shortest-path. The corresponding probability threshold can be modified
        in the model parameters.

        Returns
            Boolean: True if the agent would take an alternative path, False if not.
        """
        # TODO: Check if probabilty should be replaced by regression!
        # generate a random number between 0.0 and 1.0. This marks the probability, whether an agent takes an alternative path or not.
        node_rerouting_probability = self.rng.random()
        probability_threshold = self.model.p.random_rerouting_probability
        
        if(node_rerouting_probability < probability_threshold):
            return True

    def generic_rerouting_regression(self, detour):
        """Evaluates at every node whether an agent would stay on his current path or take an alternative path.
        The alternative path will be the second-shortest-path. The corresponding probability threshold can be modified
        in the model parameters.

        Returns
            Boolean: True if the agent would take an alternative path, False if not.
        """
        # generate a random number between 0.0 and 1.0. This marks the probability, whether an agent takes an alternative path or not.

        x = self.rng.random()
        rel_tot_detour = detour/(self.len_traversed + self.metric_path_length)
        rel_curr_detour = detour/(self.metric_path_length)
        z = -0.0957 + rel_tot_detour * 6.1942 - rel_curr_detour * 2.5212
        prop_rerouting = 1 - 1/(1+ math.exp(-z))


        if(x > prop_rerouting):
            return False
        else: 
            return True



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
        if self.model.p.scenario == 'simple_compliance': # always comply
            return True
        else: # complex compliance scenario
            x = self.rng.random()
            forbidden = 1
            rel_tot_detour = detour / (self.len_traversed + self.metric_path_length)
            z = self.model.p.w_constant + rel_tot_detour * self.model.p.w_rtd + forbidden * self.model.p.w_forbidden
            prop_non_compliance = 1 / (1 + math.exp(-z))

            if (self.model.p.density):
                prop_non_compliance += edge['density'] * self.model.p.density_weight
                # self.density_threshold?

            # TODO: Check if impatience is still a thing! If not delete code snippet
            if (self.model.p.impatience):
                prop_non_compliance += self.num_detours * self.model.p.impatience_weight

            # TODO: See initialisation of risk_appetite: Justify concept!
            prop_non_compliance = prop_non_compliance * self.risk_appetite
            self.non_comp_probs.append(prop_non_compliance)
            if(x > prop_non_compliance):
                return True
            else:
                # if logging: print probability, x and id of agent not complying
                if(self.model.p.logging):
                    print("P: " + str(prop_non_compliance) + "; X: " + str(x))
                    print("Non-Compliance, " + str(self.id))
                return False 

        
    def get_alternative_path(self, path, metric_path_length):
        """Returns an alternative path from the model graph to the agents destination, which does not use the first edge of the current path.
            If first edge of the current path has one way street reversed intervention, than iteratively call this function until alternative path is not
            or until there is no alternative path left. In that case, return inital path.
        
        Args:
            path (list): Given path to find alternative to 
            metric_path_length (float): Length of the inital path 

        Returns:
            list, float, float: The alternative path, its length and distance between penultimate node and exact destination
        """
        # create variables for current node, the next node and the last node (destination) on the current path
        current_node = path[0]
        next_node = path[1]
        destination = self.dest_node_id
        
        # filter out next edge on path from graph in a subview
        self.network[current_node][next_node]["walkable"] = False
        def filter_edge(n1, n2):
            return self.network[n1][n2].get("walkable", True)
        view = nx.subgraph_view(self.network, filter_edge=filter_edge)
        
        try:
            # compute alternative path and its length on subview
            alternative_path = nx.dijkstra_path(view, source=current_node, target=destination, weight='mm_len')
            length = nx.path_weight(view, alternative_path, weight='mm_len')
            alternative_path, length, distance_penult_node_to_dest = self.add_exact_dest_to_path(alternative_path, length)
            # check whether next edge on alternative path is one way street (forbidden to enter)
            next_edge = movement.get_directed_edge(self.model.G, self.model.nodes, alternative_path[0],alternative_path[1])
            if(next_edge['one_way_reversed']):
                # iteratively call this function (until alternative path has no intervention on first edge)
                next_path, next_detour, next_distance_penult_node_to_dest = self.get_alternative_path(alternative_path, metric_path_length)
                self.network[current_node][next_node]["walkable"] = True
                return next_path, next_detour, next_distance_penult_node_to_dest
            else:
                # reset walkability attribute of graph 
                self.network[current_node][next_node]["walkable"] = True
                if(self.model.p.logging):
                    # if logging: print alternative and current path lengths 
                    print('alt: '+ str(length) + ' orig: ' + str(metric_path_length))
                return alternative_path, length - metric_path_length, distance_penult_node_to_dest
        
        # if there is no alternative path return inital path
        except (nx.NetworkXNoPath) as e:
            print("No alternative for agent " + str(self.id) + ' at node ' + str(self.location['latest_node'])+ '.')
            # reset walkability attribute of graph 
            self.network[current_node][next_node]["walkable"] = True
            return path, 0, self.distance_penult_node_to_dest

class DistanceKeepingModel(ap.Model):

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
        # Normalized observed detours
        self.NODs = []
        # Shortest path lengths
        self.SPLs = []
        # Total path lengths
        self.TPLs = []
        self.non_comp_probs = []
                    
    def step(self):
        """Call a method for every agent. 
        """
        # Calculate next position for all agents
        self.agents.check_next_node()
        self.agents.get_next_position()
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
        if self.model.p.scenario in ["simple_compliance", "complex_compliance"]:
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
        self.mean_nod = np.mean(self.NODs)
        self.std_nod = np.std(self.NODs)
        if self.model.p.scenario == "complex_compliance":
            self.mean_non_comp_prob = np.mean(self.non_comp_probs)
            self.std_non_comp_prob = np.std(self.non_comp_probs)
        else:
            self.mean_non_comp_prob = 0
            self.std_non_comp_prob = 0

        """ Report an evaluation measure. """
        self.report('mean_nod')
        self.report('std_nod')
        self.report('mean_non_comp_prob')
        self.report('std_non_comp_prob')
        self.report(['non_compliances', 'compliances'])
        self.report('SPLs')
        self.report('TPLs')
        self.report('NODs')
        self.report('non_comp_probs')
        # create output directory
        Path("./Experiment/output/%d" % self.model.p.epoch_time).mkdir(parents=True, exist_ok=True)
        # output density maximum per street
        nx.set_edge_attributes(self.model.G, self.max_density, "max_density")
        max_density_gdf = momepy.nx_to_gdf(self.model.G, points=False)
        max_density_gdf.to_file("./Experiment/output/%d/max_density_%s.gpkg" % (self.model.p.epoch_time, (str(self.model._run_id[0]) + "_" + str(self.model._run_id[1]))), driver='GPKG', layer='Max Density Edges') 
        # output position data as gpkg 
        all_positions = DataFrame(self.position_list) 
        final_gdf = geopandas.GeoDataFrame(all_positions, geometry=all_positions['geometry'], crs="EPSG:3857")
        final_gdf.to_file('./Experiment/output/%d/positions_%s.gpkg' % (self.model.p.epoch_time, (str(self.model._run_id[0]) + "_" + str(self.model._run_id[1]))), driver='GPKG', layer='Agents_temporal') 
        # output edge data as gpkg 
        final_edge_gdf = concat(self.edge_gdf, ignore_index=True)
        final_edge_gdf.to_file('./Experiment/output/%d/edges_%s.gpkg' % (self.model.p.epoch_time, (str(self.model._run_id[0]) + "_" + str(self.model._run_id[1]))), driver='GPKG', layer='Edges_temporal')
        if (self.p.logging):
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
        nx.set_edge_attributes(self.G, 0, "ppl_count")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_increase")
        nx.set_edge_attributes(self.G, 0, "ppl_total")
        nx.set_edge_attributes(self.G, 0, "density")
        density = nx.get_edge_attributes(self.G, "density")
        self.max_density = density
        nx.set_edge_attributes(self.G, 0, "max_density")


# specify model parameters
# --------------------------------–-----
# To run the model once using optimal parameters use the following code:

# optimal_parameters = {
#     'agents': 400,
#     'steps': 100,
#     'viz': False,
#     'duration': 5,
#     # Including participants walking through forbidden streets as result of random rerouting:
#     # 'random_rerouting_probability': 0.28,
#     # Excluding participants walking through forbidden streets as result of random rerouting:
#     'random_rerouting_probability': 0.235,
#     # TODO: Calibrate risk appetite standard deviation
#     'risk_appetite_std': 0.1,
#     'risk_appetite_mean': 1,
#     'w_constant': 0.1899,
#     'w_rtd': 3.8243,
#     'w_forbidden': -1.2794,
#     'density': False,
#     'impatience': False,
#     'seed': 40,
#     'density_weight': 1,
#     'impatience_weight': -0.5,
#     'streets_path': "./input-data/quakenbrueck.gpkg",
#     'logging': False,
#     # Choose value from ['no_compliance', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
#     # Scenario 1: 'no_compliance' = Agents behave like there are no measures 
#     # Scenario 2: 'simple_complicance' = Agents comply with every measure
#     # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
#     'scenario': 'complex_compliance',
#     # Choose value from ['regression', 'simple'] for parameter to decide which method to use for generic rerouting
#     'generic_reouting_method': 'simple',
#     'epoch_time': int(time.time())
# }

# model = DistanceKeepingModel(optimal_parameters)
# results = model.run()
# --------------------------------–-----



# --------------------------------–-----
# To perform experiment use commented code:

exp_parameters = {
    'agents': ap.Values(1000),
    'steps': 250,
    'viz': False,
    'duration': 5,
    # Including participants walking through forbidden streets as result of random rerouting:
    # 'random_rerouting_probability': 0.28,
    # Excluding participants walking through forbidden streets as result of random rerouting:
    'random_rerouting_probability': 0.235,
    # TODO: Calibrate risk appetite standard deviation
    'risk_appetite_std': 0.1,
    'risk_appetite_mean': 1,
    'w_constant': 0.1899,
    'w_rtd': 3.8243,
    'w_forbidden': -1.2794,
    'density': False,
    'impatience': False,
    'seed': 42,
    'density_weight': 1,
    'impatience_weight': -0.5,
    'streets_path': "./input-data/quakenbrueck.gpkg",
    'logging': False,
    # Choose value from ['no_compliance', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_compliance' = Agents behave like there are no measures 
    # Scenario 2: 'simple_complicance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': ap.Values('no_compliance', 'simple_compliance', 'complex_compliance'),
    # Choose value from ['regression', 'simple'] for parameter to decide which method to use for generic rerouting
    'generic_reouting_method': 'simple',
    'epoch_time': int(time.time())
}

sample = ap.Sample(exp_parameters, randomize=False)

# Perform experiment
exp = ap.Experiment(DistanceKeepingModel, sample, iterations=10, record=True)
results = exp.run(n_jobs=-1, verbose=10)
results.save(exp_name='Test_experiment', exp_id=exp_parameters['epoch_time'], path='Experiment', display=True)

# --------------------------------–-----

# --------------------------------–-----
# To use external parameters for experiment use commented code:
# external_parameters = "put_external_parameters_here"

# sample = ap.Sample(external_parameters, randomize=False)

# # Perform experiment
# exp = ap.Experiment(DistanceKeepingModel, sample, iterations=1, record=True)
# results = exp.run(n_jobs=-1, verbose = 10)
# results.save(exp_name='Test_experiment', exp_id=None, path='Experiment', display=True)

