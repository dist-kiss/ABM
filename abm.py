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
        self.constant_weight = self.rng.gauss(self.model.p.constant_weight_mean, self.model.p.constant_weight_sd)
        self.rtd_weight = self.rng.gauss(self.model.p.rtd_weight_mean, self.model.p.rtd_weight_sd)
        self.ows_weight = self.rng.gauss(self.model.p.ows_weight_mean, self.model.p.ows_weight_sd)
        # Initialize variables 
        self.num_detours = 0
        self.metric_path = []
        self.remaining_dist_on_edge = 0
        self.len_traversed = 0
        self.route_counter = 0
        self.init_shortest_path_length = 0
        self.non_comp_probs = []
        self.comp_probs = []
        self.compliance_nodes = []
        self.non_compliance_nodes = []
        self.random_rerouting_nodes = []
        self.no_route_change_nodes = []

        if(self.model.p.origin_destination_pairs): 
            i = self.randomDestinationGenerator.integers(0, 3)
            self.orig_node_id = self.model.p.origin_destination_pairs[i][0]
            self.dest_node_id = self.model.p.origin_destination_pairs[i][1]
            self.agent_compute_path(self.orig_node_id, self.dest_node_id)
            self.init_shortest_path_length = self.metric_path_length
            self.start_at_dist = 0
            self.distance_penult_node_to_dest = self.model.G[self.metric_path[-2]][self.metric_path[-1]]['mm_len']
            self.first_position()
        else:
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

        self.init_pos = [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min]


        
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
            'latest_node': self.metric_path[0],
            'non_compliance': False,
            'compliance': False,
            'no_route_change': False,
            'random_rerouting': False
        }


    def setup_pos(self, space):

            self.space = space
            self.neighbors = space.neighbors
            self.pos = space.positions[self]

    def assign_new_destination(self):
        """Assigns a new destination to the agent. 
            Function uses previous destination as new origin and generates 
            new destination. Then calculates a new path between these and assigns 
            path to the agent. 
        """
        # increase route counter
        self.route_counter += 1

        if(self.model.p.origin_destination_pairs): 
            i = self.randomDestinationGenerator.integers(0, 3)
            self.orig_node_id = self.model.p.origin_destination_pairs[i][0]
            self.dest_node_id = self.model.p.origin_destination_pairs[i][1]
            self.agent_compute_path(self.orig_node_id, self.dest_node_id)
            self.init_shortest_path_length = self.metric_path_length
            self.start_at_dist = 0
            self.distance_penult_node_to_dest = self.model.G[self.metric_path[-2]][self.metric_path[-1]]['mm_len']
            self.first_position()

        else:
            # Assign new destination only:
            # self.orig = self.dest.copy()
            # self.dest = movement.get_random_dest(self.orig, self.model.edges, self.randomDestinationGenerator, 250)

            # Generate new origin and destination:
            self.orig, self.dest = movement.get_random_org_dest(self.model.edges, self.randomDestinationGenerator, 250)

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
        self.location['no_route_change'] = False

    def update_model_reporters(self, nod):
        """Update model reporters and reset agent variables.
        """
        # add total path length (TPL), shortest path length (SPL) 
        # and normalized observed detour (NOD)
        self.model.TPLs.append(self.len_traversed)
        self.model.SPLs.append(self.init_shortest_path_length)
        self.model.NODs.append(nod)
        # add non-compliance and compliance probablities of current route
        self.model.non_comp_probs.extend(self.non_comp_probs)
        self.model.comp_probs.extend(self.comp_probs)
        # add counter numbers of several types of rerouting events of current route
        # to global model counters
        self.model.compliances += len(self.compliance_nodes)
        self.model.non_compliances += len(self.non_compliance_nodes)
        self.model.random_reroutings += len(self.random_rerouting_nodes)
        self.model.no_route_changes += len(self.no_route_change_nodes)
        # update compliance location counters
        for node in self.compliance_nodes:
            self.model.nodes.at[node, 'compliances'] +=1
        for node in self.non_compliance_nodes:
            self.model.nodes.at[node, 'non_compliances'] +=1
        for node in self.random_rerouting_nodes:
            self.model.nodes.at[node, 'random_reroutings'] +=1
        for node in self.no_route_change_nodes:
            self.model.nodes.at[node, 'no_route_changes'] +=1
        # reset values of variables
        self.non_comp_probs = []
        self.comp_probs = []
        self.compliance_nodes = []
        self.non_compliance_nodes = [] 
        self.random_rerouting_nodes = []
        self.no_route_change_nodes = []

    
    def check_next_node(self):
        """For agents that are on street intersection, evaluates next street for possible interventions.
        """        

        is_agent_on_node = (self.remaining_dist_on_edge == 0)
        if(is_agent_on_node):
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
        self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])


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
        self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])


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
                self.update_model_reporters(nod)
                # assign new destination to walk towards
                self.assign_new_destination()
                self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])
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
        
        # check for one way street
        one_way_street = (1 if next_edge['one_way_reversed'] else 0)
        
        # evaluate whether to reroute or not
        deviate_from_path = self.rerouting_evaluation(detour, next_edge, one_way_street)

        if(deviate_from_path):
            # deviation + one_way_street = compliance
            if(one_way_street):
                self.location['compliance'] = True
                self.compliance_nodes.append(self.metric_path[0])
            # deviation + normal street = random rerouting
            else:
                self.location['random_rerouting'] = True
                self.random_rerouting_nodes.append(self.metric_path[0])
            # replace initial path by alternative one
            self.metric_path = alt_path
            self.metric_path_length += detour
            self.distance_penult_node_to_dest = distance_penult_node_to_dest
            self.num_detours += 1

        # no deviation + one way street = non compliance
        elif(one_way_street):
            self.location['non_compliance'] = True
            self.non_compliance_nodes.append(self.metric_path[0])
        # no deviation + normal street = no_route_change
        else: 
            self.location['no_route_change'] = True
            self.no_route_change_nodes.append(self.metric_path[0])


    def rerouting_evaluation(self, detour, edge, ows):
        """Evalutes whether agent reroutes or continues on its intended path based on one way street interventions and the detour of the alternative path 
            Decision is returned as boolean.
            Formula F(x1,...,xn) for the chance to comply is:
            F(rtd=relative total detour, ows=one way street) = rtd * rtd_weight + ows * ows_weight

        Args:
            detour (float): The detour length the alternative option would result in 
            edge (_type_): The edge belonging to the next intended street
            ows (int): Presence of one way street on the next intended street (1 = ows, 0 = no ows)

        Returns:
            Boolean: True if the agent reroutes, False if it stays on its intended route
        """
        if self.model.p.scenario == 'simple_compliance' and ows == 1: 
            # always comply in simple_compliance scenario
            return True
        else:
            x = self.rng.random()
            rel_tot_detour = detour / (self.len_traversed + self.metric_path_length)
            z = self.constant_weight + rel_tot_detour * self.rtd_weight + ows * self.ows_weight + edge['density'] * self.model.p.weight_density
            prop_non_compliance = 1 / (1 + math.exp(-z))
            
            if(ows):
                # record compliance and non_compliance probabilities for model output
                self.non_comp_probs.append(prop_non_compliance)
                self.comp_probs.append(1 - prop_non_compliance)

            if(x > prop_non_compliance):
                return True
            else:
                # if logging: print probability, x and id of agent not complying
                if(self.model.p.logging and ows):
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
            alt_path = nx.dijkstra_path(view, source=current_node, target=destination, weight='mm_len')
            alt_length = nx.path_weight(view, alt_path, weight='mm_len')
            if(self.model.p.origin_destination_pairs):
                alt_distance_penult_node_to_dest = self.model.G[alt_path[-2]][alt_path[-1]]['mm_len']
            else:    
                alt_path, alt_length, alt_distance_penult_node_to_dest = self.add_exact_dest_to_path(alt_path, alt_length)
            # check whether next edge on alternative path is one way street (forbidden to enter)
            alt_next_edge = movement.get_directed_edge(self.model.G, self.model.nodes, alt_path[0],alt_path[1])
            if(alt_next_edge['one_way_reversed']):
                # iteratively call this function (until alternative path has no intervention on first edge)
                alt_path, alt_detour, alt_distance_penult_node_to_dest = self.get_alternative_path(alt_path, metric_path_length)
                self.network[current_node][next_node]["walkable"] = True
                return alt_path, alt_detour, alt_distance_penult_node_to_dest
            else:
                # reset walkability attribute of graph 
                self.network[current_node][next_node]["walkable"] = True
                if(self.model.p.logging):
                    # if logging: print alternative and current path lengths 
                    print('alt: '+ str(alt_length) + ' orig: ' + str(metric_path_length))
                return alt_path, alt_length - metric_path_length, alt_distance_penult_node_to_dest
        
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

        
        # Create lists for position and edge data and compliance counter 
        self.position_list = []
        self.node_list = []
        self.edge_gdf = []
        self.compliances = 0
        self.non_compliances = 0
        self.random_reroutings = 0
        self.no_route_changes = 0
        self.step_counter = 0
        # Normalized observed detours
        self.NODs = []
        # Shortest path lengths
        self.SPLs = []
        # Total path lengths
        self.TPLs = []
        self.non_comp_probs = []
        self.comp_probs = []

        self.width = math.ceil(886072.6897017769515514 - 884895.6310000000521541)
        self.x_min = 884895.6310000000521541
        self.height = math.ceil(6924018.9868618501350284 - 6922980.4000000003725290)
        self.y_min = 6922980.4000000003725290

        # Create a list of agents 
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)

        self.space = ap.Space(self, shape=[self.width, self.height])
        self.space.add_agents(self.agents, self.agents.init_pos)
        self.agents.setup_pos(self.space)

                    
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
            self.mean_comp_prob = np.mean(self.comp_probs)
            self.std_comp_prob = np.std(self.comp_probs)
        else:
            self.mean_non_comp_prob = None
            self.std_non_comp_prob = None
            self.mean_comp_prob = None
            self.std_comp_prob = None


        """ Report an evaluation measure. """
        self.report('mean_nod')
        self.report('std_nod')
        self.report('mean_non_comp_prob')
        self.report('std_non_comp_prob')
        self.report('mean_comp_prob')
        self.report('std_comp_prob')
        self.report(['non_compliances', 'compliances', 'no_route_changes', 'random_reroutings'])
        self.report('SPLs')
        self.report('TPLs')
        self.report('NODs')
        self.report('non_comp_probs')
        self.report('comp_probs')
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
        self.nodes.to_file('./Experiment/output/%d/compliance_locations_%s.gpkg' % (self.model.p.epoch_time, (str(self.model._run_id[0]) + "_" + str(self.model._run_id[1]))), driver='GPKG', layer='Compliance Occurences')
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
        if(self.model.p.scenario == "no_compliance"):
            nx.set_edge_attributes(self.G, False, "one_way_reversed")
            nx.set_edge_attributes(self.G, False, "one_way")
        # Convert graph back to GeoDataFrames with nodes and edges
        self.nodes, self.edges, sw = momepy.nx_to_gdf(self.G, points=True, lines=True, spatial_weights=True)
        # set index column, and rename nodes in graph
        self.nodes = self.nodes.set_index("nodeID", drop=False)
        self.nodes = self.nodes.rename_axis([None])
        self.nodes['compliances'] = 0
        self.nodes['non_compliances'] = 0
        self.nodes['random_reroutings'] = 0
        self.nodes['no_route_changes'] = 0
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
#     'weight_constant': 0.1899,
#     'weight_rtd': 3.8243,
#     'weight_ows': -1.2794,
#     'seed': 40,
#     'weight_density': 0,
#     'streets_path': "./input-data/quakenbrueck.gpkg",
#     'logging': False,
#     # Choose value from ['no_compliance', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
#     # Scenario 1: 'no_compliance' = Agents behave like there are no measures 
#     # Scenario 2: 'simple_complicance' = Agents comply with every measure
#     # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
#     'scenario': 'complex_compliance',
#     'epoch_time': int(time.time())
# }

# model = DistanceKeepingModel(optimal_parameters)
# results = model.run()
# --------------------------------–-----



# --------------------------------–-----
# To perform experiment use commented code:

exp_parameters = {
    'agents': ap.Values(6),
    'steps': 250,
    'viz': False,
    'duration': 5,
    # Including participants walking through forbidden streets as result of random rerouting:
    # 'random_rerouting_probability': 0.28,
    # Excluding participants walking through forbidden streets as result of random rerouting:
    'random_rerouting_probability': 0.235,
    'constant_weight_mean': 0.3424823265591154, 
    'constant_weight_sd': 0.4042530941646003,
    # 'weight_constant': 0.1899,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    # 'weight_rtd': 3.8243,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    # 'weight_ows': -1.2794,
    'seed': 42,
    'weight_density': 0,
    'streets_path': "./input-data/quakenbrueck.gpkg",
    'logging': False,
    # Choose value from ['no_compliance', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_compliance' = Agents behave like there are no measures 
    # Scenario 2: 'simple_complicance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': ap.Values('no_compliance', 'simple_compliance', 'complex_compliance'),
    'epoch_time': int(time.time()),
    'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])])
}

# sample = ap.Sample(exp_parameters, randomize=False)

# # Perform experiment
# exp = ap.Experiment(DistanceKeepingModel, sample, iterations=2, record=True)
# results = exp.run(n_jobs=-1, verbose=10)
# results.save(exp_name='Test_experiment', exp_id=exp_parameters['epoch_time'], path='Experiment', display=True)



# def my_plot(model, ax):
#     pass  # Call pyplot functions here

# fig, ax = plt.subplots()
# my_model = DistanceKeepingModel(exp_parameters)
# animation = ap.animate(my_model, fig, ax, my_plot)


anim_parameters = {
    'agents': 500,
    'steps': 250,
    'viz': False,
    'duration': 5,
    # Including participants walking through forbidden streets as result of random rerouting:
    # 'random_rerouting_probability': 0.28,
    # Excluding participants walking through forbidden streets as result of random rerouting:
    'random_rerouting_probability': 0.235,
    'constant_weight_mean': 0.3424823265591154, 
    'constant_weight_sd': 0.4042530941646003,
    # 'weight_constant': 0.1899,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    # 'weight_rtd': 3.8243,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    # 'weight_ows': -1.2794,
    'seed': 42,
    'weight_density': 0,
    'streets_path': "./input-data/quakenbrueck.gpkg",
    'x_min': 884895.6310000000521541,
    'y_min': 6922980.4000000003725290,
    'logging': False,
    # Choose value from ['no_compliance', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_compliance' = Agents behave like there are no measures 
    # Scenario 2: 'simple_complicance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': 'complex_compliance',
    'epoch_time': int(time.time()),
    'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])])
}

from IPython.display import HTML
# HTML(animation.to_jshtml())

def animation_plot_single(m, ax):
    ndim = 2
    ax.set_title(f"Boids Flocking Model {ndim}D t={m.t}")
    pos = m.space.positions.values()
    pos = np.array(list(pos)).T  # Transform
    lines = m.edges.translate(xoff=-m.x_min, yoff=-m.y_min, zoff=0.0)
    lines.plot(ax=ax,color = 'green', label = 'network', zorder=1)
    ax.scatter(*pos, s=2, c='black', zorder=2)
    ax.set_xlim(0, m.width)
    ax.set_ylim(0, m.height)
    ax.set_axis_off()

def animation_plot(m, p):
    projection = None
    fig = plt.figure(figsize=(7,7))
    ax = fig.add_subplot(111, projection=projection)
    # newax = fig.add_axes(ax.get_position())
    # newax.patch.set_visible(False)
    # streets = geopandas.read_file(anim_parameters['streets_path'])
    # lines = streets.translate(xoff=-anim_parameters['x_min'], yoff=-anim_parameters['y_min'], zoff=0.0)
    # lines.plot(ax=newax,color = 'green', label = 'network', zorder=1)
    animation = ap.animate(m(p), fig, ax, animation_plot_single)    
    with open("data_%d.html" % m(p).p.epoch_time, "w") as file:
        file.write(animation.to_jshtml(fps=10))
    # return HTML(animation.to_jshtml(fps=20))
import matplotlib
matplotlib.rcParams['animation.embed_limit'] = 2**128

animation_plot(DistanceKeepingModel, anim_parameters)
print("Done")
# --------------------------------–-----

# --------------------------------–-----
# To use external parameters for experiment use commented code:
# external_parameters = "put_external_parameters_here"

# sample = ap.Sample(external_parameters, randomize=False)

# # Perform experiment
# exp = ap.Experiment(DistanceKeepingModel, sample, iterations=1, record=True)
# results = exp.run(n_jobs=-1, verbose = 10)
# results.save(exp_name='Test_experiment', exp_id=None, path='Experiment', display=True)

