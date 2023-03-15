# Model design
import agentpy as ap
import networkx as nx
import random
import geopandas
import pandas as pd
import momepy
import datetime
from collections import Counter
import movement
import graph_helpers as gh
import math
import os
import numpy as np
from pathlib import Path
import time    
from shapely.ops import substring, Point, LineString

# Visualization
import matplotlib.pyplot as plt 

# TODO: 
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
        self.walking_speed = self.rng.gauss(self.model.p.walking_speed_mean, self.model.p.walking_speed_std)
        self.walking_distance = self.walking_speed * self.model.p.duration

         # Choose agent weights
        self.constant_weight = self.rng.gauss(self.model.p.constant_weight_mean, self.model.p.constant_weight_sd)
        self.rtd_weight = self.rng.gauss(self.model.p.rtd_weight_mean, self.model.p.rtd_weight_sd)
        self.ows_weight = self.rng.gauss(self.model.p.ows_weight_mean, self.model.p.ows_weight_sd)

        # Initialize variables 
        self.global_graph = self.model.G
        self.personal_network = self.model.G.to_undirected()
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
        self.total_detour = 0
        self.final_path = []

        if(self.model.p.origin_destination_pairs):
            # Choose origin and destination pair from model parameters
            self.assign_od_node_pair(self.model.p.origin_destination_pairs)
        else:
            # Choose random origin and destination within street network
            self.assign_random_od(250)
            #TODO: Place agents in the model at different times            
        
        # Compute shortest path to destination
        self.agent_compute_initial_shortest_path(self.orig_name, self.dest_name)
        # init reporter variables with agent location
        self.init_reporters()
        self.init_pos = [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min]

    def assign_od_node_pair(self, od_pairs):
        """Assigns a random origin-destination pair from a tuple of origin-destination-tuples.
            
            Args:
                od_apirs (tuple): Tuple of OD-Tuples
        """        
        i = self.randomDestinationGenerator.integers(0, len(od_pairs))
        self.orig_name = od_pairs[i][0]
        self.dest_name = od_pairs[i][1]
        
    def assign_random_od(self, min_dist):
        """Assigns a random origin-destination pair within the street network, with a given minimum distance bewteen both points.
            
            Args:
                min_dist (float): minimum distance between origin and destination
        """                
        self.orig, self.dest = movement.get_random_org_dest(self.personal_network, self.model.edges, self.randomDestinationGenerator, min_dist)
        self.orig_name = "A"+str(self.id)+"S"+str(self.route_counter)
        self.dest_name = "A"+str(self.id)+"D"+str(self.route_counter)
        gh.add_temporary_node(self.personal_network, self.orig['nearer_node'], self.orig['remote_node'], 
            self.orig['dist_from_nearer'], self.orig_name, self.orig['point'].x,self.orig['point'].y)
        gh.add_temporary_node(self.personal_network, self.dest['nearer_node'], self.dest['remote_node'], 
            self.dest['dist_from_nearer'], self.dest_name, self.dest['point'].x,self.dest['point'].y)


    def agent_compute_initial_shortest_path(self, orig, dest):
        """Calculate the shortest path from the agents current location to its destination and the length of the path.
            Stores result as agent variables (list of nodes in a shortest path, float).

        Args:
            start_node (int): ID of path starting node
            dest_node (int): ID of path destination node
        """
        self.metric_path = nx.dijkstra_path(self.personal_network, source=orig, target=dest, weight='mm_len')
        self.metric_path_length = nx.path_weight(self.personal_network, self.metric_path, weight='mm_len')
        self.init_shortest_path_length = self.metric_path_length

    def init_reporters(self):
        """Calculates the first position of an agent and creates a location dict to store location information of the agent. 
            Also sets further attributes, such as edge counter attributes and the remaining distance to the next node. 
        """        
        # Update people counter of current edge
        # graph_edge = self.network[self.metric_path[0]][self.metric_path[1]]
        self.graph_edge = self.global_graph[self.orig['nearer_node']][self.orig['remote_node']]
        gh.increase_edge_counter(self.graph_edge, 1)
        self.previous_edge = self.personal_network[self.orig['nearer_node']][self.orig['remote_node']]
        # Get the edge the agent starts on (corrected direction)
        self.current_edge = movement.get_directed_edge(self.personal_network, self.metric_path[0], self.metric_path[1])
        
        # Set distance to next node
        self.remaining_dist_on_edge = self.current_edge['mm_len']
        
        # Create dict for agent location and related attributes
        self.location = {
            'geometry': self.orig['point'],
            'agentID': self.id,
            'route_counter': self.route_counter,
            'latest_node': self.metric_path[0],
            'non_compliance': False,
            'compliance': False,
            'no_route_change': False,
            'random_rerouting': False
        }
        if(not self.model.p.origin_destination_pairs):
            self.personal_network.remove_node(self.orig_name)


    def setup_pos(self, space):
            self.space = space
            self.neighbors = space.neighbors
            self.pos = space.positions[self]

    def assign_new_destination(self):
        """Assigns a new origin and destination to the agent. 
           Then calculates shortest path between these and assigns path to the agent. 
        """
        # increase route counter
        self.route_counter += 1

        if(self.model.p.origin_destination_pairs): 
            # Generate new origin and destination pair from model parameter origin_destination_pairs
            self.assign_od_node_pair(self.model.p.origin_destination_pairs)
        else:
            # UNCOMMENT if you want to assign new destination only:
            # self.orig = self.dest.copy()
            # self.dest = movement.get_random_dest(self.orig, self.model.edges, self.randomDestinationGenerator, 250)

            # Generate new origin and destination:
            self.assign_random_od(250)

        # Compute shortest path to destination
        self.agent_compute_initial_shortest_path(self.orig_name, self.dest_name)
        self.init_reporters()


    def reset_compliance_status(self):
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
        self.len_traversed = 0
        self.total_detour = 0
        self.final_path = []

                        
    def stop_walking_at_node(self):
        """Simulate agent walking until the next node. Update path and agent attributes. 
        """
        gh.decrease_edge_counter(self.graph_edge, 1)
        next_location = Point(self.personal_network.nodes[self.metric_path[1]]['pos'])
        # increase length traversed by the remaining distance to next node
        self.len_traversed += self.remaining_dist_on_edge
        # erase first node from current path list 
        prev = self.metric_path.pop(0)
        self.final_path.append(prev)
        if(prev in self.personal_network.nodes):       
            self.previous_edge = self.personal_network[prev][self.metric_path[0]]  
        # update remaining path length
        self.metric_path_length = self.metric_path_length - self.remaining_dist_on_edge 
        # reset remaining distance
        self.remaining_dist_on_edge = 0
        # update location of agent accordingly
        self.location.update( [('latest_node', self.metric_path[0]),('geometry', next_location)] )
        self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])


    def stop_walking_after_timestep(self):
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
        next_location = self.current_edge['geometry'].interpolate(self.current_edge['mm_len'] - self.remaining_dist_on_edge)
        self.location.update([('geometry', next_location)])
        self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])
    
    def walk(self):
        would_walk_beyond_next_node = (self.walking_distance > self.remaining_dist_on_edge)
        if would_walk_beyond_next_node:
            self.stop_walking_at_node()
        else:
            self.stop_walking_after_timestep()

    def finish_route_and_calc_statistics(self):
        """Calculate final metrics of path and update model reporters. Eventually trigger new origin destination assignement.
        """
        nod = (self.total_detour / self.init_shortest_path_length)
        self.update_model_reporters(nod)
        if(not self.model.p.origin_destination_pairs):
            self.personal_network.remove_node(self.dest_name)
        # assign new destination to walk towards
        self.assign_new_destination()
        self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])


    def evaluate_and_choose_path(self):
        """Check whether the next street segement has an intervention, evaluates alternative routes and chooses its subsequent path. 
        """
        # get next street
        next_edge = movement.get_directed_edge(self.global_graph, self.metric_path[0],self.metric_path[1])
        # check whether it is one way street
        one_way_street = (1 if next_edge['one_way_reversed'] else 0)
        
        # if there is no alternative street at this node, assume agent just keeps walking
        if(self.personal_network.nodes[self.metric_path[0]]['degree'] == 2):
            # no deviation + one way street = non compliance
            if(one_way_street):
                self.location['non_compliance'] = True
                self.non_compliance_nodes.append(self.metric_path[0])
            # no deviation + normal street = no_route_change
            else: 
                self.location['no_route_change'] = True
                self.no_route_change_nodes.append(self.metric_path[0])

        # degree > 2 = intersection of at least two streets
        else:
            # calculate alternative path and detour
            alt_path, detour = gh.get_alternative_path(self.personal_network, self.metric_path, self.metric_path_length, self.previous_edge, one_way_street, self.id)

            # evaluate whether to reroute or not
            deviate_from_path = self.rerouting_decision(detour, next_edge, one_way_street)

            # if alternative route is forbidden, re-evaluate decision to reroute
            alt_next_edge = movement.get_directed_edge(self.global_graph, alt_path[0],alt_path[1])
            is_alt_path_forbidden = alt_next_edge['one_way_reversed']
            if(is_alt_path_forbidden and deviate_from_path):
                if(self.model.p.scenario == 'simple_compliance'):
                    deviate_from_path = False
                else:
                    deviate_from_path = not(self.rerouting_decision(-detour, alt_next_edge, 1))

            if(deviate_from_path):
                # deviation + inital was one_way_street = compliance
                if(one_way_street):
                    self.location['compliance'] = True
                    self.compliance_nodes.append(self.metric_path[0])
                # deviation + initial was normal street = random rerouting
                else:
                    self.location['random_rerouting'] = True
                    self.random_rerouting_nodes.append(self.metric_path[0])
                # deviation + alternative street is one way street = non-compliance
                if(is_alt_path_forbidden):
                    self.location['non_compliance'] = True
                    self.non_compliance_nodes.append(self.metric_path[0])

                # replace initial path by alternative one
                self.metric_path = alt_path
                self.metric_path_length += detour
                self.total_detour += detour
                self.num_detours += 1

            # no deviation + one way street = non compliance
            elif(one_way_street):
                self.location['non_compliance'] = True
                self.non_compliance_nodes.append(self.metric_path[0])
            # no deviation + normal street = no_route_change
            else: 
                self.location['no_route_change'] = True
                self.no_route_change_nodes.append(self.metric_path[0])


    def rerouting_decision(self, detour, edge, ows):
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
        # in simple_compliance scenario always comply if ows
        if self.model.p.scenario == 'simple_compliance' and ows == 1: 
            return True
        else:
            x = self.rng.random()
            rel_tot_detour = detour / (self.len_traversed + self.metric_path_length)
            z = self.constant_weight + rel_tot_detour * self.rtd_weight + ows * self.ows_weight + edge['density'] * self.model.p.weight_density
            # compute probability to stay on path (if ows, this equals non-compliance probability)
            prop_no_deviation = 1 / (1 + math.exp(-z))
            
            if(ows):
                # record compliance and non_compliance probabilities for model output
                self.non_comp_probs.append(prop_no_deviation)
                self.comp_probs.append(1 - prop_no_deviation)

            if(x > prop_no_deviation):
                # deviate from path
                return True
            else:
                # if logging: print probability, x and id of agent not complying
                if(self.model.p.logging and ows):
                    print("P: " + str(prop_no_deviation) + "; X: " + str(x))
                    print("Non-Compliance, " + str(self.id))
                return False 


    # def get_alternative_path(self, path, metric_path_length, ows):
    #     """Returns an alternative path from the model graph to the agents destination, which does not use the first edge of the current path.
    #         If first edge of the current path has one way street reversed intervention, than iteratively call this function until alternative path is not
    #         or until there is no alternative path left. In that case, return inital path.
        
    #     Args:
    #         path (list): Given path to find alternative to 
    #         metric_path_length (float): Length of the inital path 

    #     Returns:
    #         list, float, float: The alternative path, its length and distance between penultimate node and exact destination
    #     """
    #     # create variables for current node, the next node and the last node (destination) on the current path
    #     current_node = path[0]
    #     next_node = path[1]
        
    #     # filter out next edge on path
    #     self.personal_network[current_node][next_node]["walkable"] = False
    #     # and if next street is not a ows, filter previous edge (forbids turning around!)
    #     if(not ows):
    #         self.previous_edge['walkable'] = False
    #     def filter_edge(n1, n2):
    #         return self.personal_network[n1][n2].get("walkable", True)
    #     view = nx.subgraph_view(self.personal_network, filter_edge=filter_edge)

    #     try:
    #         # compute alternative path and its length on subview
    #         alt_path = nx.dijkstra_path(view, source=current_node, target=self.dest_name, weight='mm_len')
    #         alt_length = nx.path_weight(view, alt_path, weight='mm_len')
    #         # reset walkability attribute of graph
    #         self.personal_network[current_node][next_node]["walkable"] = True
    #         self.previous_edge['walkable'] = True
    #         if(self.model.p.logging):
    #             # if logging: print alternative and current path lengths
    #             print('alt: '+ str(alt_length) + ' orig: ' + str(metric_path_length))
    #         return alt_path, alt_length - metric_path_length
        
    #     # if there is no alternative path return inital path
    #     except (nx.NetworkXNoPath) as e:
    #         print("No alternative for agent " + str(self.id) + ' at node ' + str(self.location['latest_node'])+ '.')
    #         # reset walkability attribute of graph 
    #         self.personal_network[current_node][next_node]["walkable"] = True
    #         self.previous_edge['walkable'] = True
    #         return path, 0
        

# ---- UPDATE FUNCTIONS ---- 
    def update_graph_edge_to_next(self):
        """ Update the agents graph edge to edge between first two nodes of its path.
        """
        self.graph_edge = self.global_graph[self.metric_path[0]][self.metric_path[1]]
        # self.set_graph_edge(self.metric_path[0], self.metric_path[1])
    
    def update_graph_edge_to_final(self):
        """ Update the agents graph edge to edge of the destination location
        """
        self.graph_edge = self.global_graph[self.dest['nearer_node']][self.dest['remote_node']]
        # self.set_graph_edge(self.dest['nearer_node'], self.dest['remote_node'])

    def update_edge_attributes(self):
        self.current_edge = movement.get_directed_edge(self.personal_network, self.metric_path[0], self.metric_path[1])
        # self.set_local_graph_edge(self.metric_path[0], self.metric_path[1])
        self.remaining_dist_on_edge = self.current_edge['mm_len']
        # self.set_remaining_dist_on_edge(self.current_edge['mm_len'])
        gh.increase_edge_counter(self.graph_edge, 1)



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

        # Animation variables
        self.x_max = 32429731.2
        self.y_max = 5837205.5
        self.x_min = 32428935.9
        self.y_min = 5836544.6
        self.width = math.ceil(self.x_max - self.x_min)
        self.height = math.ceil(self.y_max - self.y_min)

        # Create a list of agents 
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)

        self.space = ap.Space(self, shape=[self.width, self.height])
        self.space.add_agents(self.agents, self.agents.init_pos)
        self.agents.setup_pos(self.space)

                    
    def step(self):
        """Call a method for every agent. 
        """
        # Select agents that are on intersections
        on_node = self.agents.select(self.agents.remaining_dist_on_edge == 0)
        on_path_node = on_node.select(ap.AttrIter(list((map(len, on_node.metric_path)))) != 2)
        on_penultimate_node = on_node.select(ap.AttrIter(list((map(len, on_node.metric_path)))) == 2)
        
        # Reset compliance status from previous edge
        on_node.reset_compliance_status()
        # Check for interventions unless destination is on next edge
        on_path_node.evaluate_and_choose_path()
        # Update next edge (depending on whether final edge or any other)
        on_path_node.update_graph_edge_to_next()
        on_penultimate_node.update_graph_edge_to_final()
        # Update edge attributes for reporters
        on_node.update_edge_attributes()

        # let all agents walk for duration of one timestep or until next intersection is reached
        self.agents.walk()

        # select agents thats have reached destination and calculate route statistics
        at_final_node = self.agents.select(ap.AttrIter(list((map(len, self.agents.metric_path)))) == 1)
        at_final_node.finish_route_and_calc_statistics()

        self.step_counter += 1

    def update(self):
        # update edge pedestrian counter attributes
        ppl_count = Counter(nx.get_edge_attributes(self.model.G, "ppl_count"))
        temp_count = Counter(nx.get_edge_attributes(self.model.G, "temp_ppl_increase"))
        length = nx.get_edge_attributes(self.model.G, "mm_len")
        width = nx.get_edge_attributes(self.model.G, "sidewalk_width")
        density = dict(Counter({key : ppl_count[key] / (length[key] * width[key]) for key in ppl_count}))
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
        time = datetime.datetime(2000, 1, 1, self.step_counter * self.model.p.duration // 3600, (self.step_counter * self.model.p.duration // 60) % 60 , self.step_counter * self.model.p.duration % 60)
        
        # store all the agents current location in list and add time and counter attributes
        if(self.model.p.positions):
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
        Path("./Experiment/output/%d" % self.p.epoch_time).mkdir(parents=True, exist_ok=True)
        # output density maximum per street
        nx.set_edge_attributes(self.G, self.max_density, "max_density")
        max_density_gdf = momepy.nx_to_gdf(self.G, points=False)
        max_density_gdf.to_file("./Experiment/output/%d/max_density_%s.gpkg" % (self.p.epoch_time, (str(self._run_id[0]) + "_" + str(self._run_id[1]))), driver='GPKG', layer='Max Density Edges') 
        # output position data as gpkg
        if(self.model.p.positions):
            all_positions = pd.DataFrame(self.position_list) 
            final_gdf = geopandas.GeoDataFrame(all_positions, geometry=all_positions['geometry'], crs="EPSG:5652")
            final_gdf.to_file('./Experiment/output/%d/positions_%s.gpkg' % (self.p.epoch_time, (str(self._run_id[0]) + "_" + str(self._run_id[1]))), driver='GPKG', layer='Agents_temporal') 
        # output edge data as gpkg
        final_edge_gdf = pd.concat(self.edge_gdf, ignore_index=True)        
        final_edge_gdf.to_file('./Experiment/output/%d/edges_%s.gpkg' % (self.p.epoch_time, (str(self._run_id[0]) + "_" + str(self._run_id[1]))), driver='GPKG', layer='Edges_temporal')
        self.nodes[['degree', 'nodeID', 'geometry', 'compliances','non_compliances', 'random_reroutings', 'no_route_changes']].to_file('./Experiment/output/%d/compliance_locations_%s.gpkg' % (self.p.epoch_time, (str(self._run_id[0]) + "_" + str(self._run_id[1]))), driver='GPKG', layer='Compliance Occurences')
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
        streets: geopandas.GeoDataFrame = geopandas.read_file(streets_gpkg)
        streets = streets.set_index("ID", drop=False)
        # add default sidwalk_width of 1.5m if none is given
        mask_res = streets['highway'] == 'residential'
        mask_path = streets['highway'] == 'path'
        mask_living = streets['highway'] == 'living_street'
        streets.loc[mask_res, 'sidewalk_width'] = 5
        streets.loc[mask_path, 'sidewalk_width'] = 3
        streets.loc[mask_living, 'sidewalk_width'] = 10
        # Transform GeoDataFrame to networkx Graph
        self.G = momepy.gdf_to_nx(streets, approach='primal', multigraph=False)        
        # Calculate degree of nodes
        self.G = momepy.node_degree(self.G, name='degree')
        # self.G2 = momepy.node_degree(self.G2, name='degree')
        if(self.p.scenario == "no_interventions"):
            nx.set_edge_attributes(self.G, False, "one_way_reversed")
            nx.set_edge_attributes(self.G, False, "one_way")
        # Convert graph back to GeoDataFrames with nodes and edges
        self.nodes, self.edges, sw = momepy.nx_to_gdf(self.G, points=True, lines=True, spatial_weights=True)
        # self.nodes2, self.edges2, sw = momepy.nx_to_gdf(self.G2, points=True, lines=True, spatial_weights=True)
        self.nodes['y']=self.nodes['geometry'].y
        self.nodes['xy']=list(zip(self.nodes['geometry'].x, self.nodes['geometry'].y))
        pos=pd.Series(self.nodes.xy.values,index=self.nodes.nodeID).to_dict()
        # set index column, and rename nodes in graph
        self.nodes = self.nodes.set_index("nodeID", drop=False)
        self.nodes = self.nodes.rename_axis([None])
        self.nodes['compliances'] = 0
        self.nodes['non_compliances'] = 0
        self.nodes['random_reroutings'] = 0
        self.nodes['no_route_changes'] = 0
        pos_inv=pd.Series(self.nodes.nodeID.values,index=self.nodes.xy).to_dict()
        self.G = nx.relabel_nodes(self.G, pos_inv)
        nx.set_node_attributes(self.G, pos, "pos")
        # self.G = nx.convert_node_labels_to_integers(self.G, first_label=0, ordering='default', label_attribute="pos")
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
#     'streets_path': "./input-data/quakenbrueck_street_width.gpkg",
#     'logging': False,
#     # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
#     # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
#     # Scenario 2: 'simple_complicance' = Agents comply with every measure
#     # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
#     'scenario': 'complex_compliance',
#     'epoch_time': int(time.time()),
#     'origin_destination_pairs': False,
#     'positions': False

# }

# model = DistanceKeepingModel(exp)
# results = model.run()
# --------------------------------–-----



# --------------------------------–-----
# To perform experiment use commented code:

exp_parameters = {
    'agents': 20,
    'steps': 720,
    'viz': False,
    'duration': 5,
    'constant_weight_mean': 0.3424823265591154,
    'constant_weight_sd': 0.4042530941646003,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    'seed': 43,
    'weight_density': 0,
    'streets_path': "./input-data/quakenbrueck_street_width.gpkg",
    'logging': False,
    'walking_speed_mean': 1.25,
    'walking_speed_std': 0.21,
    # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
    # Scenario 2: 'simple_complicance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': ap.Values('no_interventions', 'simple_compliance', 'complex_compliance'),
    'epoch_time': int(time.time()),
    'origin_destination_pairs': False,
    # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
    'positions': False
}

sample = ap.Sample(exp_parameters, randomize=False)

# Perform experiment
exp = ap.Experiment(DistanceKeepingModel, sample, iterations=10, record=True)
results = exp.run(n_jobs=-1, verbose=10)
results.save(exp_name='Test_experiment', exp_id=exp_parameters['epoch_time'], path='Experiment', display=True)

# TO RUN SINGLE MODEL RUN, COMMENT PREVIOUS LINES AND UNCOMMENT NEXT TWO LINES:
# model = DistanceKeepingModel(exp_parameters)
# results = model.run()


#  ------ ANIMATION ------------------------
anim_parameters = {
    'agents': 2000,
    'steps': 720,
    'viz': False,
    'duration': 5,
    'constant_weight_mean': 0.3424823265591154, 
    'constant_weight_sd': 0.4042530941646003,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    'seed': 43,
    'weight_density': 0,
    'streets_path': "./input-data/quakenbrueck_street_width.gpkg",
    'logging': False,
    'walking_speed_mean': 1.25,
    'walking_speed_std': 0.21,
    # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
    # Scenario 2: 'simple_complicance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': 'complex_compliance',
    'epoch_time': int(time.time()),
    'origin_destination_pairs': False,
    # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
    'positions': False
}

from IPython.display import HTML

def animation_plot_single(m, ax):
    ndim = 2
    ax.set_title(f"Dist-KISS Model {ndim}D t={m.t}")
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
    animation = ap.animate(m(p), fig, ax, animation_plot_single)    
    with open("data_%d.html" % m(p).p.epoch_time, "w") as file:
        file.write(animation.to_jshtml(fps=10))
    # return HTML(animation.to_jshtml(fps=20))
import matplotlib
matplotlib.rcParams['animation.embed_limit'] = 2**128

# TO PRODUCE ANIMATION UMCOMMENT THE FOLLOWING LINE:
# animation_plot(DistanceKeepingModel, anim_parameters)
print("Script completed.")
# --------------------------------–-----


# ---------------   EXTERNAL PARAMETERS   -----------------–-----
# To use external parameters for experiment use commented code:
# external_parameters = "put_external_parameters_here"

# sample = ap.Sample(external_parameters, randomize=False)

# # Perform experiment
# exp = ap.Experiment(DistanceKeepingModel, sample, iterations=1, record=True)
# results = exp.run(n_jobs=-1, verbose = 10)
# results.save(exp_name='Test_experiment', exp_id=None, path='Experiment', display=True)

