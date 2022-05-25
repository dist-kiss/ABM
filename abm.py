# Model design
import agentpy as ap
import networkx as nx
from numpy import random
from shapely.geometry import Point, LineString
from shapely.ops import split, nearest_points, snap
import geopandas
from pandas import concat, DataFrame
import momepy
import datetime
from collections import Counter
# from random import random, shuffle

# Visualization
import matplotlib.pyplot as plt 



class Pedestrian(ap.Agent):

    def setup(self):
        # Init random number generator
        rng = self.model.random
        
        # Initialize attributes and variables
        self.walking_speed = rng.random() + 1
        self.walking_distance = self.walking_speed * self.model.p.duration
        self.density_threshold = round( 0.03 + rng.random() * 0.07, 4)
        self.metric_path = []
        self.leftover_distance = 0
        self.network = self.model.G.to_directed()
        self.ows_threshold = 0.75 + rng.random() * 0.25
        # self.detour_threshold = 0.75 + rng.random() * 0.25
        self.ovr_risk_tolerance = 0.8 + rng.random() * 0.2
        self.num_detours = 0
        
        # = rng.random()
        # TODO: 
        # - use results of the study to calibrate the ows threshold
        # - add patience_threshold that reduces the willingness to comply over time spend or detours taken
        # - DONE: consider remaining path lengths when making decision on when to comply or not to comply
        # - fix directed one way streets 
                
        # Choose random origin within boundaries of Quakenbrueck
        self.orig, self.dest = Pedestrian.generate_random_orig_dest(self.model.area_polygon, 250, rng)
                
        # Find the closest nodes in the network for origin and destination
        self.orig_node_id = Pedestrian.get_nearest_node(self.model.nodes, self.orig)
        self.dest_node_id = Pedestrian.get_nearest_node(self.model.nodes, self.dest)
        
        #TODO: Place agents in the model at different times
        
        
        # Set current location to the origin node
        self.location = self.model.nodes.loc[[self.orig_node_id]].to_dict(orient='records')[0]
        self.location['agentID'] = self.id
        self.location['finished'] = False
        self.location['density_threshold'] = self.density_threshold
        
        # Compute shortest path to destination
        self.agent_compute_path()
        # self.agent_compute_all_path()
        

    def generate_random_orig_dest(polygon, min_dist, rng):
        """
        Create random origin and destination coordinates inside model polygon boundaries
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
                # check if there is a origin already, if so: make sure next point is at least min_dist apart
                if len(points) == 1:
                    distance = points[0].distance(pnt)
                    if distance > min_dist:
                        points.append(pnt)
                else:
                    points.append(pnt)
        return points[0], points[1]        

    def get_nearest_node(nodes, point):
        """
            Return the nearest node to a given point from of a set of nodes.

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
        
    def agent_compute_path(self):
        """
            Calculate the shortest path from the agents current location to its destination.
            Stores result as list of nodes in a shortest path.
        """
        self.metric_path = nx.dijkstra_path(self.model.G, source=self.location['nodeID'], target=self.dest_node_id, weight='mm_len')
        self.metric_path_length = nx.path_weight(self.model.G, self.metric_path, weight='mm_len')

    def agent_compute_all_path(self):
        """
            Calculate the shortest path from the agents current location to its destination.
            Stores result as list of nodes in a shortest path.
        """
        self.all_simple_paths = nx.shortest_simple_paths(self.model.G, source=self.location['nodeID'], target=self.dest_node_id, weight='mm_len')

    def reached_destination(self):
        # if path is shorter than 2, destination is reached, return
        if len(self.metric_path) < 2:
            self.location['finished'] = True
                    
    def get_next_position(self):
        """
            Calculates the position of an agent after the next timestep, dependent on the duration 
            of a timestep and the walking speed of the agent.

        """
        if (self.location['finished']):
            return 
        else:
            # check if agent is on node
            if(self.leftover_distance == 0):
                # self.metric_path_backup = self.metric_path.copy()
                # evaluate next street segment regarding ows and density
                self.check_next_street_segment()
                # TODO: Implement waiting at node if there is no alternative option and pedestrian is unsatisfied
                    # if false is returned restore path from backup
                    # self.metric_path = self.metric_path_backup
                    # return

            # get the edge (street) the agent currently walks on
            current_edge = self.get_edge_directed(self.metric_path[0], self.metric_path[1])

            distance_to_next_point = self.distance_to_next_node(current_edge)

            # check if pedestrian would walk past next node, in that case:
            if  self.walking_distance > distance_to_next_point:
                self.reach_next_node()            
                return
            # if next node is not reached go on with calculation of next position
            else:
                self.stay_on_edge(current_edge, distance_to_next_point)
                return
            
    def reach_next_node(self):
        # set current node to location of next node
        # reset leftover distance
        self.leftover_distance = 0
        # reduce people counter of current edge
        self.model.G[self.metric_path[0]][self.metric_path[1]]['temp_ppl_increase']-=1
        # erase first node from current path list 
        self.metric_path.pop(0)
        # update remaining path length
        self.metric_path_length = nx.path_weight(self.model.G, self.metric_path, weight='mm_len')
        # update location of agent
        new_location = self.model.nodes.loc[[self.metric_path[0]]].to_dict(orient='records')[0]
        self.location.update( [('nodeID', new_location['nodeID']),('geometry', new_location['geometry'])] )

    def stay_on_edge(self, edge, distance):
        # update location of agent using walking distance within current timestep
        self.leftover_distance = distance - self.walking_distance
        self.location['geometry'] = edge['geometry'].interpolate(edge['mm_len'] - self.leftover_distance)

        
    def distance_to_next_node(self, edge):
        """
            Calculate the distance the agent passes by during the current timestep, to prevent agent from walking further than the next node and update counter off current edge.
            
            Parameters
            ----------
            edge : shapely.geometry.line.Linestring
                Edge from graph

            Returns
            -------
            Number
                The distance to the next node 
        """
        # calculate the distance the agent passes by during the current timestep, to prevent agent from walking further than the next node    
        distance_to_next_point = 0
        # check whether pedestrian is on edge (leftover_distance != 0) or on node (leftover_distance == 0) 
        if(self.leftover_distance != 0):
            distance_to_next_point = self.leftover_distance
        else:
            distance_to_next_point = edge['mm_len']
            self.model.G[self.metric_path[0]][self.metric_path[1]]['temp_ppl_increase']+=1
            self.model.G[self.metric_path[0]][self.metric_path[1]]['ppl_total']+=1
        return distance_to_next_point



    def get_edge_directed(self, start, end):
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
        edge = self.model.G.get_edge_data(start, end)
        if(edge['geometry'].coords[0] != self.model.nodes.loc[self.model.nodes['nodeID'] == start]['geometry'].values[0].coords[0]):
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
    
    

    
    def check_next_street_segment(self):
        """
            Check whether the next street segement is too crowded or has an intervention 
            that stops the agent from accessing it. If there is an obstacle, 
            recalculate the agents path and overwrite previous path.
        """
        edge = self.get_edge_directed(self.metric_path[0],self.metric_path[1])
        # edge = self.model.G.get_edge_data(self.metric_path[0],self.metric_path[1])
        # if(edge['density'] > self.density_threshold):
        #     return self.density_evaluation()
        # el
        if(edge['one_way_reversed']):
            alt_path, detour = self.get_alternative_path(self.metric_path, self.metric_path_length)
            # if (alt_path ==  self.metric_path):
            #     return True
            if(self.ows_evaluation(detour, edge)):
                self.metric_path = alt_path
                self.num_detours += 1
                return True
                # self.check_next_street_segment()
        else:
            return True

    # def density_evaluation(self, edge):
    #     # x = random.rand()
    #     x = 0
    #     if(x<self.density_threshold):
    #         return self.comply_crowdedness()
    #     else:
    #         return Pedestrian.ignore_obstacle()    

    def ows_evaluation(self, detour, edge):
        x = random.rand() * 100
        compliance = 0
        norm_detour = detour/self.metric_path_length
        # print(norm_detour)
        # compliance += max(self.ows_threshold - self.ows_threshold * norm_detour, 0) * 100
        compliance += max(1 - 0.5 * norm_detour, 0) * 100
        if(self.model.p.density):
            compliance += edge['density'] / self.density_threshold * 50
        # print(self.num_detours)
        if(self.model.p.impatience):
            compliance -= self.num_detours * 10
        compliance = compliance * self.ovr_risk_tolerance
        # print("agent: " + str(self.id) + "compliance: " + str(compliance) + " - x: " + str(x))
        if(x < compliance):
            # print("Compliance, " + str(self.id))
            self.model.compliances += 1
            return True
        else:
            self.model.non_compliances += 1
            print("Non-Compliance, " + str(self.id))
            return False   
        
    def get_alternative_path(self, path, metric_path_length):
        current_node = path[0]
        next_node = path[1]
        destination = path[-1]
        self.network[current_node][next_node]["walkable"] = False
        def filter_edge(n1, n2):
            return self.network[n1][n2].get("walkable", True)
        view = nx.subgraph_view(self.network, filter_edge=filter_edge)
        try:
            alternative_path = nx.dijkstra_path(view, source=current_node, target=destination, weight='mm_len')
            length = nx.path_weight(view, alternative_path, weight='mm_len')
            # TODO: evaluate path length influence on compliance decision
            next_edge = self.get_edge_directed(alternative_path[0],alternative_path[1])
            if(next_edge['one_way_reversed']):
                return self.get_alternative_path(alternative_path, metric_path_length)
            else:
                self.network[current_node][next_node]["walkable"] = True
                print('alt: '+ str(length) + 'orig: ' + str(metric_path_length))
                return alternative_path, length - metric_path_length
            
        except (nx.NetworkXNoPath) as e:
            print("No alternative for agent " + str(self.id) + ' at node ' + str(self.location['nodeID'])+ '.')
            self.network[current_node][next_node]["walkable"] = True
            return path, 0

    
    # def ignore_obstacle():            
    #     return True
        
    # def comply_crowdedness(self):
    #     current_node = self.metric_path[0]
    #     next_node = self.metric_path[1]
    #     self.network[current_node][next_node]["walkable"] = False
    #     def filter_edge(n1, n2):
    #         return self.network[n1][n2].get("walkable", True)
    #     view = nx.subgraph_view(self.network, filter_edge=filter_edge)
    #     print(self.id)
    #     try:
    #         self.metric_path = nx.dijkstra_path(view, source=self.metric_path[0], target=self.metric_path[-1], weight='mm_len')
    #         length = nx.path_weight(view, self.metric_path, weight='mm_len')
    #         # TODO: evaluate path length influence on compliance decision
    #         path_free = self.check_next_street_segment()
    #         self.network[current_node][next_node]["walkable"] = True
    #         return path_free
            
    #     except (nx.NetworkXNoPath) as e:
    #         print("Agent " + str(self.id) + ' needs to wait at current node.')
    #         self.network[current_node][next_node]["walkable"] = True
    #         return False

    def comply_ows(self):
        if (self.network.has_edge(self.metric_path[0],self.metric_path[1])):
            self.network.remove_edge(self.metric_path[0],self.metric_path[1])
        def filter_edge(n1, n2):
            return self.network[n1][n2].get("walkable", True)
        view = nx.subgraph_view(self.network, filter_edge=filter_edge)
        print("oneway_street" + str(self.id))
        try:
            self.metric_path = nx.dijkstra_path(view, source=self.metric_path[0], target=self.metric_path[-1], weight='mm_len')
            length = nx.path_weight(view, self.metric_path, weight='mm_len')
            # TODO: evaluate path length influence on compliance decision
            path_free = self.check_next_street_segment()
            return path_free
            
        except (nx.NetworkXNoPath) as e:
            print("Agent " + str(self.id) + ' last option is blocked by intervention.')
            return False


class MyModel(ap.Model):

    def setup(self):
        self.step_counter = 0 
        self.create_graph(area_shp="./boundaries/crop_area.shp", crs='EPSG:3857', streets_gpk="./network-data/quakenbrueck_clean.gpkg")
        # opt. visualize network nodes, edges and degree values
        if self.p.viz:
            self.visualize_model()
                # Create a list of agents 
        
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)
        
        # Store list of inital paths into global list  
        self.gdf = []
        self.edge_gdf = []
        self.compliances = 0
        self.non_compliances = 0
                    
    def step(self):
        """ Call a method for every agent. """
        # Calculate next position for all agents 
        self.agents.reached_destination()
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
        nx.set_edge_attributes(self.model.G, ppl_count, "ppl_count")
        nx.set_edge_attributes(self.model.G, density, "density")
        nx.set_edge_attributes(self.model.G, 0, "temp_ppl_increase")

        """ Record a dynamic variable. """
        # self.agents.record('metric_path')
        # self.model.record('G')
        
        # update fake date for temporal viz in qgis
        time = datetime.datetime(2000, 1, 1, self.step_counter * self.model.p.duration // 3600, self.step_counter * self.model.p.duration // 60, self.step_counter * self.model.p.duration % 60)
        
        # store all the agents current location in list 
        self.positions = self.agents.location.copy()
        for agent_position in self.positions:
            agent_position['time']= time
            agent_position['counter']= self.step_counter
            self.gdf.append(agent_position)

        # store edge information in dataframe
        nx.set_edge_attributes(self.model.G, self.step_counter, "counter")
        nx.set_edge_attributes(self.model.G, time, "time")
        edges = momepy.nx_to_gdf(self.model.G, points=False)
        self.edge_gdf.append(edges)

    def end(self):
        """ Report an evaluation measure. """
        current_positions = DataFrame(self.gdf) 
        final_gdf = geopandas.GeoDataFrame(current_positions, geometry=current_positions['geometry'], crs="EPSG:3857")
        final_gdf.to_file('./output/positions1.gpkg', driver='GPKG', layer='Agents_Timesteps') 
        final_edge_gdf = concat(self.edge_gdf, ignore_index=True)
        final_edge_gdf.to_file('./output/edges1.gpkg', driver='GPKG', layer='Edges_Timestamps')
        print("Compliances: " + str(self.compliances) + "; Non-Compliances: " + str(self.non_compliances))

    def visualize_model(self):
        f, ax = plt.subplots(figsize=(10, 10))
        self.nodes.plot(ax=ax, column='degree', cmap='tab20b', markersize=(2 + self.nodes['nodeID'] * 4), zorder=2)
        self.edges.plot(ax=ax, color='lightgrey', zorder=1)
        ax.set_axis_off()
        plt.show()
    
    def create_graph(self, area_shp, crs, streets_gpk):
        # Read boundary polygon and make sure it uses CRS EPSG:3857
        self.area_polygon = geopandas.read_file(area_shp)
        self.area_polygon = self.area_polygon.to_crs(crs)
        
        # Read street network as geopackage and convert it to GeoDataFrame
        streets = geopandas.read_file(streets_gpk)
        # Transform GeoDataFrame to networkx Graph
        self.G = nx.Graph(momepy.gdf_to_nx(streets, approach='primal'))
        # Calculate degree of nodes
        self.G = momepy.node_degree(self.G, name='degree')
        # Convert graph back to GeoDataFrames with nodes and edges
        self.nodes, self.edges, sw = momepy.nx_to_gdf(self.G, points=True, lines=True, spatial_weights=True)
        # set index column, and rename nodes in graph
        self.nodes = self.nodes.set_index("nodeID", drop=False)
        self.nodes = self.nodes.rename_axis([None])
        self.G = nx.convert_node_labels_to_integers(self.G, first_label=1, ordering='default', label_attribute=None)
        # mapping = dict(zip([(geom.x, geom.y) for geom in self.nodes['geometry'].tolist()], self.nodes.index[self.nodes['nodeID']-1].tolist()))
        # self.G = nx.relabel_nodes(self.G, mapping)
        nx.set_edge_attributes(self.G, 0, "ppl_count")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_increase")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_decrease")
        nx.set_edge_attributes(self.G, 0, "ppl_total")
        nx.set_edge_attributes(self.G, 0, "density")
        # nx.set_edge_attributes(self.G, False, "oneway_from")


# specify some parameters
parameters = {
    'agents': 200,
    'steps': 100,
    'viz': False,
    'duration': 5,
    'density': False,
    'impatience': False
}

# Run the model!
model = MyModel(parameters)
results = model.run()