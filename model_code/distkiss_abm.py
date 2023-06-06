# Model design
import agentpy as ap
import networkx as nx
import random
import geopandas
import pandas as pd
import momepy
import datetime
from collections import Counter
import math
import numpy as np
from pathlib import Path
from shapely.ops import substring, Point, LineString

# Custom libs
import movement
import graph_helpers as gh
import spatial_output_creator as soc
import dsg_scenes as scenes

class Pedestrian(ap.Agent):

    def setup(self):
        """Initializes an agent of type pedestrian with its attributes
        """

        """ Initialize random number generators. """
        # Use seeds produced by model random generator (using model seed) for reproducibilty.
        # Generate seeds for: generic random numbers, random weights, random destinations (and origins)
        seed = self.model.random.getrandbits(128)
        weightSeed = self.model.random.getrandbits(128)
        destinationSeed = self.model.random.getrandbits(128)
        # Init three separate random number generator for each agent using seeds for reproducibility
        self.rng = random.Random(seed)
        self.randomWeightsGenerator = random.Random(weightSeed)
        self.randomDestinationGenerator = np.random.default_rng(destinationSeed)
        
        """ Initialize agent weights and derived attributes. """
        # Weights:
        self.constant_weight = self.randomWeightsGenerator.gauss(self.model.p.constant_weight_mean, self.model.p.constant_weight_sd)
        self.rtd_weight = self.randomWeightsGenerator.gauss(self.model.p.rtd_weight_mean, self.model.p.rtd_weight_sd)
        self.ows_weight = self.randomWeightsGenerator.gauss(self.model.p.ows_weight_mean, self.model.p.ows_weight_sd)
        # walking speed is based on average walking speed and its standard deviation
        # Source: Satish Chandra and Anish Khumar Bharti 2013, p. 662, "Speed Distribution Curves for Pedestrians during Walking and Crossing"
        self.walking_speed = self.randomWeightsGenerator.gauss(self.model.p.walking_speed_mean, self.model.p.walking_speed_std)
        # Derived attributes:
        self.walking_distance = self.walking_speed * self.model.p.duration

        """ Initialize other attributes. """
        # Graph representations
        self.global_graph = self.model.G
        self.personal_network = self.model.G.to_undirected()
        # Route specific
        self.metric_path = []
        self.init_shortest_path_length = 0
        self.num_detours = 0
        self.remaining_dist_on_edge = 0
        self.len_traversed = 0
        self.route_counter = 0
        self.finished = False
        self.total_detour = 0
        self.final_path = []
        # Reporter attributes
        self.non_comp_probs = []
        self.comp_probs = []
        self.compliance_nodes = []
        self.non_compliance_nodes = []
        self.random_rerouting_nodes = []
        self.no_route_change_nodes = []

        """ Assign origin and destination. """
        if(self.model.p.origin_destination_pairs):
            # Choose origin and destination pair from model parameters
            self.assign_od_node_pair(self.model.p.origin_destination_pairs)
        else:
            # Choose random origin and destination within street network
            self.assign_random_od(250, False)

            # for debugging:
            if(self.model.p.destination_log):
                self.destination_dict = {'agentID': self.id, 'initial_dest': self.dest['point'],}

        """ Compute initial path and set reporter attributes. """
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
        
    def assign_random_od(self, min_dist, keep_prev_dest_as_orig):
        """Assigns a random origin-destination pair within the street network, with a given minimum distance bewteen both points.
            
            Args:
                min_dist (float): minimum distance between origin and destination
                keep_prev_dest_as_orig (boolean): whether to keep the destination of the previous 
                    route as origin for the following route or to create new origin
        """
        if(keep_prev_dest_as_orig):
            # reuse previous destination as origin and only generate new destination
            self.orig = self.dest.copy()
            self.dest = movement.get_random_dest(self.personal_network, self.orig, self.model.edges, self.randomDestinationGenerator, min_dist)
        else:
            # generate new origin and destination
            self.orig, self.dest = movement.get_random_org_dest(self.personal_network, self.model.edges, self.randomDestinationGenerator, min_dist)
        # create intermediate nodes in personal graph at origin and destination location
        # Use the following name scheme: A{ID of Agent}S{Route Counter}, e.g. A1S1 for the origin of the first route of agent 1. 
        self.orig_name = "A"+str(self.id)+"S"+str(self.route_counter)
        # Use the following name scheme: A{ID of Agent}D{Route Counter}, e.g. A1D1 for the destination of the first route of agent 1. 
        self.dest_name = "A"+str(self.id)+"D"+str(self.route_counter)
        # Add intermediate nodes to personal graph
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
        # store length of shortest path in agent attributes
        self.init_shortest_path_length = self.metric_path_length

    def init_reporters(self):
        """Calculates the first position of an agent and creates a location dict to store location information of the agent. 
            Also sets further attributes, such as edge counter attributes and the remaining distance to the next node. 
        """        
        # Update people counter of edge the agent is currently on by one
        self.graph_edge = self.global_graph[self.orig['nearer_node']][self.orig['remote_node']]
        gh.increase_edge_counter(self.graph_edge, 1)
        self.previous_edge = self.personal_network[self.orig['nearer_node']][self.orig['remote_node']]

        # Get the edge the agent starts on (corrected direction)
        self.current_edge = movement.get_directed_edge(self.personal_network, self.metric_path[0], self.metric_path[1])
        
        # Set distance to next intersection (graph node)
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
        # if random origin is used instead of predefined od-pairs, remove intermediate node from graph
        # shall avoid that the agent uses it in rerouting and reduce computation time
        if(not self.model.p.origin_destination_pairs):
            self.personal_network.remove_node(self.orig_name)


    def setup_pos(self, space):
        """Store the poistion of the agent in the AgentPy-specific space. Used for animation only. 
        """
        self.space = space
        self.neighbors = space.neighbors
        self.pos = space.positions[self]

    def assign_new_destination(self):
        """Assigns a new origin and destination to the agent. Conceptually this is equivalent to "spawning" a new agent, 
            but reuses the instance of an agent that has arrived at it's destination. 
           Then calculates shortest path between origin and destination and assigns path to the agent.
        """
        # increase route counter to keep track of the number of routes of the agent instance
        self.route_counter += 1

        if(self.model.p.origin_destination_pairs): 
            # Generate new origin and destination pair from model parameter origin_destination_pairs
            self.assign_od_node_pair(self.model.p.origin_destination_pairs)
        else:
            # Generate new origin (only if reuse_previous_dest_as_orig is False) and destination:
            self.assign_random_od(250, self.model.p.reuse_previous_dest_as_orig)

        # Compute shortest path to destination and initalise reporter variables
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
        # add total path length (TPL), shortest path length (SPL) and normalized observed detour (NOD)
        self.model.TPLs.append(self.len_traversed)
        self.model.SPLs.append(self.init_shortest_path_length)
        self.model.NODs.append(nod)
        # add non-compliance and compliance probablities of current route
        self.model.non_comp_probs.extend(self.non_comp_probs)
        self.model.comp_probs.extend(self.comp_probs)
        # add counter numbers of several types of rerouting events of current route to global model counters
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
        # reset values of agent variables
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
        # increase length traversed by the remaining distance to next intersection
        self.len_traversed += self.remaining_dist_on_edge
        # Get location of next intersection
        next_location = Point(self.personal_network.nodes[self.metric_path[1]]['pos'])
        # Reduce people counter of current edge by 1
        gh.decrease_edge_counter(self.graph_edge, 1)

        # erase first node from current path list 
        prev = self.metric_path.pop(0)
        # add that node to the final chosen path
        self.final_path.append(prev)
        if(prev in self.personal_network.nodes):    
            # this cannot be done for the origin node, as it was removed by this time already, 
            # but previous edge was alread set during initalization (see function init_reporters()) in that case
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
        """Check whether agent reaches next intersection within this timestep and walk until 
            intersection or until timestep is over.
        """
        would_walk_beyond_next_node = (self.walking_distance > self.remaining_dist_on_edge)
        if would_walk_beyond_next_node:
            self.stop_walking_at_node()
        else:
            self.stop_walking_after_timestep()

    def finish_route_and_calc_statistics(self):
        """Calculate final metrics of path and update model reporters. Depending on model parameters, 
            optionally trigger new origin/destination assignment.
        """
        nod = (self.total_detour / self.init_shortest_path_length)
        self.update_model_reporters(nod)
        # if there is an intermediate destination node, remove it from the agent's personal network
        if(not self.model.p.origin_destination_pairs):
            self.personal_network.remove_node(self.dest_name)
        
        # for debugging:
        if(self.model.p.destination_log and self.route_counter > 0):
            self.destination_dict['new_assigned_dest'] = self.dest['point']

        # check if new agents shall be appear in the model after an agent reached its destination
        if(self.model.p.assign_new_destinations):
            # assign new destination to walk towards
            self.assign_new_destination()
            self.space.move_to(self, [self.location['geometry'].x - self.model.x_min, self.location['geometry'].y - self.model.y_min])
        else:
            # mark agent as finished and let it stay at its location
            self.finished = True


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
            deviate_from_path = self.rerouting_decision(detour, next_edge, one_way_street, True)

            # if alternative route is forbidden, re-evaluate decision to reroute
            alt_next_edge = movement.get_directed_edge(self.global_graph, alt_path[0],alt_path[1])
            is_alt_path_forbidden = alt_next_edge['one_way_reversed']
            if(is_alt_path_forbidden and deviate_from_path):
                if(self.model.p.scenario == 'simple_compliance'):
                    deviate_from_path = False
                else:
                    deviate_from_path = not(self.rerouting_decision(-detour, alt_next_edge, 1, self.model.p.record_second_opinion_ncps))

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
                if(self.model.p.rerouting_allowed):
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

    def extract_edge_data(self):
        current_node = self.location['latest_node']
        previous_node = [key for key, value in self.personal_network.adj[current_node].items() if self.previous_edge == value][0]

        adjacent_nodes_with_edge_data = list(self.personal_network.adj[current_node].items())

        signs = []
        crowds = []
        distances = []

        # set index for "direction" key
        i = 1

        for next_node, edge_data in adjacent_nodes_with_edge_data:
            # skip calculations for the previous edge of the agent
            if next_node == previous_node:
                continue

            if edge_data['density'] > 0:
                pass

            distance = self.calculate_remaining_distance(next_node, current_node, previous_node)

            # check, whether edge has the correct orientation
            corrected_edge = movement.get_directed_edge(self.personal_network, current_node, next_node)

            # translate ows-boolean to streetsign-string
            sign = scenes.get_signage(corrected_edge)
            # translate density into corresponding integer
            crowdedness = scenes.get_crowdedness(edge_data)

            # only apply overlays if there are any
            if sign is not None:
                signs.append({'direction': i, 'sign': sign})
            if crowdedness is not None:
                crowds.append({'direction': i, 'crowdedness': crowdedness})
            distances.append({'direction': i, 'distance': distance})
            i += 1

        return signs, crowds, distances

    def calculate_remaining_distance(self, next_node, current_node, previous_node):
        network = self.personal_network.copy()

        # remove edge agent was previously standing from network (agents cannot turn around)
        network[current_node][previous_node]['walkable'] = False

        # filter function for creating graph views
        def filter_edge(n1, n2):
            return network[n1][n2].get("walkable", True)

        # make edges 'unwalkable' that should be ignored for the shortest path
        nodes_from_paths_to_remove = [node for node in network.adj[current_node].keys() if node != next_node]
        for node in nodes_from_paths_to_remove:
            network[current_node][node]['walkable'] = False

        # subgraph view. All edges except the edge to "next_node" are removed
        view = nx.subgraph_view(network, filter_edge=filter_edge)

        # calculate shortest path on remaining path
        shortest_path_to_dest = nx.dijkstra_path(view, source=current_node, target=self.dest_name,
                                                 weight='mm_len')
        remaining_distance_on_route = nx.path_weight(network, shortest_path_to_dest, weight='mm_len')

        # round for better reprensentation in the IVE
        remaining_distance_on_route = round(remaining_distance_on_route)

        # reset walkability
        for node in nodes_from_paths_to_remove:
            network[current_node][node]['walkable'] = True

        return remaining_distance_on_route


    def rerouting_decision(self, detour, edge, ows, record_non_comp_prob):
        """Evalutes whether agent reroutes or continues on its intended path based on one way street interventions and the detour of the alternative path 
            Decision is returned as boolean.
            Formula F(x1,...,xn) for the chance to comply is:
            F(rtd=relative total detour, ows=one way street) = rtd * rtd_weight + ows * ows_weight

        Args:
            detour (float): The detour length the alternative option would result in 
            edge (_type_): The edge belonging to the next intended street
            ows (int): Presence of one way street on the next intended street (1 = ows, 0 = no ows)
            record_non_comp_prob (boolean): Whether to record non compliance probability (depends on definition of the term)

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

            if 0.48 <= prop_no_deviation <= 0.52: #TODO: add a suitable threshold
                # keys for DSG-JSON
                scenario_name_key = self.model.p.name_dsg_scenario
                location_name_key = self.location['latest_node']

                # TODO: change degree - 1, if agents could also turn around at a node
                # "-1" because e.g. a node with degree == 3 has 2 outgoing streets (the agent is coming from one route and he cant turn around and go back)
                degree_key = self.personal_network.nodes[self.metric_path[0]]['degree'] - 1

                # get edge data from the personal network of the agent
                signs, crowds, distances = self.extract_edge_data()

                # JSON for POST-Request
                scene_json = {
                    "scenario_name": scenario_name_key,
                    "location_name": location_name_key,
                    "degree": degree_key,
                    "signs": signs,
                    "crowds": crowds,
                    "distances": distances,
                }
                # save scene JSON
                self.model.scene_dictionaries.append(scene_json)

            if(ows and record_non_comp_prob):
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

# ---- UPDATER FUNCTIONS ---- 
    def update_graph_edge_to_next(self):
        """ Update the agents graph edge to edge between first two nodes of its path.
        """
        self.graph_edge = self.global_graph[self.metric_path[0]][self.metric_path[1]]
        # self.set_graph_edge(self.metric_path[0], self.metric_path[1])
    
    def update_graph_edge_to_final(self):
        """ Update the agents graph edge to edge of the destination location
        """
        self.graph_edge = self.global_graph[self.dest['nearer_node']][self.dest['remote_node']]

    def update_edge_attributes(self):
        """ Update the agents current edge to next edge on path, set remaining distance on edge
            to edge distance and update edge counter.
        """
        self.current_edge = movement.get_directed_edge(self.personal_network, self.metric_path[0], self.metric_path[1])
        self.remaining_dist_on_edge = self.current_edge['mm_len']
        gh.increase_edge_counter(self.graph_edge, 1)



class DistanceKeepingModel(ap.Model):

    def setup(self):
        """Setup the model. """

        """Create the graph using the street input file. """  
        self.create_graph(streets_gpkg=self.p.streets_path)
        
        """Initialize model variables. """  
        # Create lists for position and edge data and compliance counter
        self.scene_dictionaries = []
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
        # non compliance probabilities and compliance probabilities 
        self.non_comp_probs = []
        self.comp_probs = []
        # for debugging:
        if(self.p.destination_log):
            self.destination_list = []

        """Set animation variables. """ 
        # Variables for animation (fixed to the current input file)
        # TODO: Make generic by using input file to infer variables
        self.x_max = 32429731.2
        self.y_max = 5837205.5
        self.x_min = 32428935.9
        self.y_min = 5836544.6
        self.width = math.ceil(self.x_max - self.x_min)
        self.height = math.ceil(self.y_max - self.y_min)

        """Create a list of agents. """ 
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)

        self.space = ap.Space(self, shape=[self.width, self.height])
        self.space.add_agents(self.agents, self.agents.init_pos)
        self.agents.setup_pos(self.space)

                    
    def step(self):
        """Call a method for every agent. 
        """
        
        """ Select different groups of agents. """ 
        # Select agents that are on intersections
        not_finished = self.agents.select(self.agents.finished == False)
        on_node = not_finished.select(not_finished.remaining_dist_on_edge == 0)
        on_path_node = on_node.select(ap.AttrIter(list((map(len, on_node.metric_path)))) != 2)
        on_penultimate_node = on_node.select(ap.AttrIter(list((map(len, on_node.metric_path)))) == 2)
        
        """ Let agents evaluate their situation and update reporter variables. """
        # Reset compliance status from previous edge
        on_node.reset_compliance_status()
        # Check for interventions unless destination is on next edge
        on_path_node.evaluate_and_choose_path()
        # Update next edge (depending on whether final edge or any other)
        on_path_node.update_graph_edge_to_next()
        on_penultimate_node.update_graph_edge_to_final()
        # Update edge attributes for reporters
        on_node.update_edge_attributes()

        """ Movement of agents. """ 
        # let all agents walk for duration of one timestep or until next intersection is reached
        not_finished.walk()

        """ Update reporters for agent who reached their destination in this timestep. """ 
        # select agents thats have reached destination and calculate route statistics
        at_final_node = not_finished.select(ap.AttrIter(list((map(len, not_finished.metric_path)))) == 1)
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
        time = datetime.datetime(2000, 1, 1, self.step_counter * self.p.duration // 3600, (self.step_counter * self.p.duration // 60) % 60 , self.step_counter * self.p.duration % 60)
        
        if(self.p.positions):
        # store all the agents current location in list and add time and counter attributes
            positions = self.agents.location.copy()
            for agent_position in positions:
                agent_position['time']= time
                agent_position['counter']= self.step_counter
                self.position_list.append(agent_position)

        # store edge information in dataframe
        nx.set_edge_attributes(self.model.G, self.step_counter, "counter")
        nx.set_edge_attributes(self.model.G, time, "time")

        if(self.p.edges):
            edges = momepy.nx_to_gdf(self.model.G, points=False)
            self.edge_gdf.append(edges)

        # if all agents finished their routes -> end model run. 
        # Event can only occur if model parameter "assign_new_destinations" == False
        if(len(self.agents.select(self.agents.finished == True)) == self.p.agents):
            self.model.stop()

    def end(self):
        """ Compute evaluation measures (means, standard deviations, variances). """
        self.mean_nod = np.mean(self.NODs)
        self.std_nod = np.std(self.NODs)
        self.var_nod = np.var(self.NODs)
        # compliance probabilites are only relevant in complex_compliance scenario, otherwise set values to None
        if self.p.scenario == "complex_compliance":
            self.mean_non_comp_prob = np.mean(self.non_comp_probs)
            self.std_non_comp_prob = np.std(self.non_comp_probs)
            self.var_non_comp_prob = np.var(self.non_comp_probs)
            self.mean_comp_prob = np.mean(self.comp_probs)
            self.std_comp_prob = np.std(self.comp_probs)
        else:
            self.mean_non_comp_prob = None
            self.std_non_comp_prob = None
            self.var_non_comp_prob = None
            self.mean_comp_prob = None
            self.std_comp_prob = None


        """ Report an evaluation measure. """
        self.report('mean_nod')
        self.report('std_nod')
        self.report('var_nod')
        self.report('mean_non_comp_prob')
        self.report('std_non_comp_prob')
        self.report('var_non_comp_prob')
        self.report('mean_comp_prob')
        self.report('std_comp_prob')
        self.report(['non_compliances', 'compliances', 'no_route_changes', 'random_reroutings'])
        self.report('SPLs')
        self.report('TPLs')
        self.report('NODs')
        self.report('non_comp_probs')
        self.report('comp_probs')

        """ Produce spatial output files. """
        # create output directory
        Path("./Experiment/output/%d" % self.p.epoch_time).mkdir(parents=True, exist_ok=True)
        # If not an Experiment set self._run_id object (sampleID and iteration in experiments)
        if(self._run_id == None):
            self._run_id = ["X","X"]
        if(self.p.max_densities):
            # output density maximum per street
            soc.save_maximum_densities_to_file(self.G, self.max_density, self.p.epoch_time, self._run_id[0], self._run_id[1])    
        if(self.p.positions):
            # output position data as gpkg
            soc.save_positions_to_file(self.position_list, self.p.epoch_time, self._run_id[0], self._run_id[1])
        if(self.p.edges):
            # output edge data as gpkg
            soc.save_edges_to_file(self.edge_gdf, self.p.epoch_time, self._run_id[0], self._run_id[1])
        if(self.p.compliance_nodes):
            # output compliance nodes as gpkg
            soc.save_compliance_nodes_to_file(self.nodes, self.p.epoch_time, self._run_id[0], self._run_id[1])
        if(self.p.destination_log):
            for agent in self.agents:
                self.destination_list.append(agent.destination_dict) # just for bugfixing
            # output destination data as gpkg
            soc.save_destinations_to_file(self.destination_list, self.p.epoch_time)
        
        """ Logs for debugging. """
        if (self.p.logging):
            print("Compliances: " + str(self.compliances) + "; Non-Compliances: " + str(self.non_compliances))
            print(f" absolute non-compliance-probabilities: {len(self.non_comp_probs)}")
            print(f" absolute compliance-probabilities: {len(self.comp_probs)}")
            print(f" absolute NODs: {len(self.NODs)}")

        print(self.scene_dictionaries[:5])
        print(len(self.scene_dictionaries))

            
    def create_graph(self, streets_gpkg):
        """Creates the network graph for the model based on an given gpkg linestring file. 

        Args:
            streets_gpkg (str): Path to gpkg linestring file
        """
        # Read street network as geopackage and convert it to GeoDataFrame
        streets: geopandas.GeoDataFrame = geopandas.read_file(streets_gpkg)
        # if one way street information is missing, assume there is no one way street
        streets['one_way'] = streets['one_way'].fillna(False)
        streets['one_way_reversed'] = streets['one_way_reversed'].fillna(False)
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

