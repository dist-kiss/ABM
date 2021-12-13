# Model design
import agentpy as ap
import networkx as nx
from shapely.geometry import Point, LineString
from shapely.ops import split, nearest_points, snap
import geopandas
from pandas import concat
import momepy
import datetime
from collections import Counter

# Visualization
import matplotlib.pyplot as plt 



class Pedestrian(ap.Agent):

    def setup(self):
        # Init random number generator
        rng = self.model.random
        
        # Initialize attributes and variables
        self.walking_speed = rng.random() + 1
        self.walking_distance = self.walking_speed * self.model.p.duration
        self.density_threshold = round(5 + rng.random() * 5)
        self.metric_path = []
        self.leftover_distance = 0
        
        # Choose random origin within boundaries of Quakenbrueck
        self.orig, self.dest = self.generate_random_orig_dest(self.model.area_polygon, 250)
                
        # Find the closest nodes in the network for origin and destination
        self.orig_node_id = self.get_nearest_node(self.model.nodes, self.orig)
        self.dest_node_id = self.get_nearest_node(self.model.nodes, self.dest)
        
        #TODO: Place agents in the model at different times
        
        
        # Set current location to the origin node
        self.location = self.model.nodes.loc[[self.orig_node_id]]
        self.location['agentID'] = self.id
        self.location['density_threshold'] = self.density_threshold
                
        # Compute shortest path to destination
        self.agent_compute_path()

    def generate_random_orig_dest(self, polygon, min_dist):
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
        rng = self.model.random
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

    def get_nearest_node(self, nodes, point):
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
        self.metric_path = nx.dijkstra_path(self.model.G, source=self.location['nodeID'].values[0], target=self.dest_node_id, weight='mm_len')
    
                    
    def get_next_position(self):
        """
            Calculates the position of an agent after the next timestep, dependet on the duration of a timestep and the walking speed of the agent.

            Parameters
            ----------
            duration : float
                The duration of a timestep in seconds.  
        """
        # if path is shorter than 2, destination is reached, return
        if len(self.metric_path) < 2:
            return 
        else:

            # calculate the distance the agent passes by during the current timestep, to prevent agent from walking further than the next node
            next_node = self.model.nodes.loc[[self.metric_path[1]]]
            edge_data = self.model.G.get_edge_data(self.metric_path[0],self.metric_path[1])
            current_edge = list(edge_data.values())[0]
            
            if(self.leftover_distance == 0):
                if(self.check_next_street_segment(current_edge)):
                    next_node = self.model.nodes.loc[[self.metric_path[1]]]
                    edge_data = self.model.G.get_edge_data(self.metric_path[0],self.metric_path[1])
                    current_edge = list(edge_data.values())[0]
                    # return
            
            # check if linestring starts at current node (and ends at next node)
            if(current_edge['geometry'].coords[0] != self.model.nodes.loc[self.model.nodes['nodeID'] == self.metric_path[0]]['geometry'].values[0].coords[0]):
                # invert indice order
                current_edge['geometry'] = LineString(list(current_edge['geometry'].coords)[::-1])
                
            distance_to_next_point = 0
            # check whether pedestrian is on edge (leftover_distance != 0) or on node (leftover_distance == 0) 
            if(self.leftover_distance != 0):
                distance_to_next_point = self.leftover_distance
            else:
                distance_to_next_point = current_edge['mm_len']
                for key in self.model.G[self.metric_path[0]][self.metric_path[1]]._atlas:
                    self.model.G[self.metric_path[0]][self.metric_path[1]][key]['temp_ppl_increase']+=1
                
            # check if pedestrian would walk past next node, in that case:
            if distance_to_next_point < self.walking_distance:                
                # set current node to location of next node
                self.leftover_distance = 0
                for key in self.model.G[self.metric_path[0]][self.metric_path[1]]._atlas:
                    # self.model.G[self.metric_path[0]][self.metric_path[1]][key]['temp_ppl_decrease']+=1
                    self.model.G[self.metric_path[0]][self.metric_path[1]][key]['temp_ppl_increase']-=1
                self.metric_path.pop(0)
                self.location = next_node
                self.location['agentID'] = self.id
                self.location['density_threshold'] = self.density_threshold
                return
            # if next node is not reached go on with calculation of next position
            else:
                new_location = current_edge['geometry'].interpolate(current_edge['mm_len'] - distance_to_next_point + self.walking_distance)
                self.location['geometry'] = new_location
                self.leftover_distance = distance_to_next_point - self.walking_distance
                return
    
    def check_next_street_segment(self, edge):
        """
            Check whether the next street segement is too crowded or has an intervention that stops the agent from accessing it.
            If there is an obstacle, recalculates the agents path and overwrites the previous path.
        """
        # TODO: implement this function!
        # print(edge['ppl_count'])
        if(edge['ppl_count'] > self.density_threshold):
            edge["walkable"] = False
            def filter_edge(n1, n2, key):
                # print(self.model.G[n1][n2][key].get("cross_me", True))
                return self.model.G[n1][n2][key].get("walkable", True)
            view = nx.subgraph_view(self.model.G, filter_edge=filter_edge)
            print(self.id)
            self.metric_path = nx.dijkstra_path(view, source=self.metric_path[0], target=self.metric_path[-1], weight='mm_len')
            edge["walkable"] = True
            return True
        else: 
            return False
        
        # if(next_edge['people_count'] > self.people_count):
            
            
        
class MyModel(ap.Model):

    def setup(self):
        self.step_counter = 0 
        # Read boundary polygon and make sure it uses CRS EPSG:3857
        self.area_polygon = geopandas.read_file("./boundaries/crop_area.shp")
        self.area_polygon = self.area_polygon.to_crs('EPSG:3857')
        
        # Read street network as geopackage and convert it to GeoDataFrame
        streets = geopandas.read_file("./network-data/quakenbrueck_clean.gpkg")
        # Transform GeoDataFrame to networkx Graph
        self.G = momepy.gdf_to_nx(streets, approach='primal')
        # Calculate degree of nodes
        self.G = momepy.node_degree(self.G, name='degree')
        # Convert graph back to GeoDataFrames with nodes and edges
        self.nodes, self.edges, sw = momepy.nx_to_gdf(self.G, points=True, lines=True, spatial_weights=True)
        # set index column, and rename nodes in graph 
        # print(self.nodes)
        self.nodes = self.nodes.set_index("nodeID", drop=False)
        self.nodes = self.nodes.rename_axis([None])
        sorted(self.G)
        # print(self.nodes['nodeID'])
        varX= self.nodes.index[self.nodes['nodeID']-1].tolist()
        varY = [(geom.x, geom.y) for geom in self.nodes['geometry'].tolist()]
        mapping = dict(zip([(geom.x, geom.y) for geom in self.nodes['geometry'].tolist()], self.nodes.index[self.nodes['nodeID']-1].tolist()))
        self.G = nx.relabel_nodes(self.G, mapping)
        nx.set_edge_attributes(self.G, 0, "ppl_count")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_increase")
        nx.set_edge_attributes(self.G, 0, "temp_ppl_decrease")
        # opt. visualize network nodes, edges and degree values
        if self.p.viz:
            f, ax = plt.subplots(figsize=(10, 10))
            self.nodes.plot(ax=ax, column='degree', cmap='tab20b', markersize=(2 + self.nodes['nodeID'] * 4), zorder=2)
            self.edges.plot(ax=ax, color='lightgrey', zorder=1)
            ax.set_axis_off()
            plt.show()
        # Create a list of agents 
        self.agents = ap.AgentList(self, self.p.agents, Pedestrian)
        
        # Store list of inital paths into global list  
        self.gdf = []

                    
    def step(self):
        """ Call a method for every agent. """
        # Calculate next position for all agents 
        self.agents.get_next_position()
        self.step_counter += 1

    def update(self):
        ppl_count = Counter(nx.get_edge_attributes(self.model.G, "ppl_count"))
        temp_count = Counter(nx.get_edge_attributes(self.model.G, "temp_ppl_increase"))
        ppl_count.update(temp_count)
        ppl_count=dict(ppl_count)
        nx.set_edge_attributes(self.model.G, ppl_count, "ppl_count")
        nx.set_edge_attributes(self.model.G, 0, "temp_ppl_increase")
        # for x in self.model.G.edges(data=True,keys=True):
        #     x[3]['ppl_count'] = x[3]['ppl_count'] + x[3]['temp_ppl_increase'] 
        #     # - x[3]['temp_ppl_decrease']
        #     x[3]['temp_ppl_increase'] = 0
        #     # x[3]['temp_ppl_decrease'] = 0
        """ Record a dynamic variable. """
        # TODO: Record agents position as shapefile
        self.agents.record('metric_path')
        self.model.record('G')
        # store all the agents current location in list 
        self.positions = self.agents.location.copy()
        for agent_position in self.positions:
            agent_position['time']= datetime.datetime(2000, 1, 1, self.step_counter * self.model.p.duration // 3600, self.step_counter * self.model.p.duration // 60, self.step_counter * self.model.p.duration % 60)
            agent_position['counter']= self.step_counter
            self.gdf.append(agent_position)

    def end(self):
        """ Report an evaluation measure. """
        final_gdf = concat(self.gdf, ignore_index=True)
        final_gdf.to_file('./output/positions.gpkg', driver='GPKG', layer='Agents_Timesteps')  


# specify some parameters
parameters = {
    'agents': 100,
    'steps': 100,
    'viz': False,
    'duration': 5
}

# Run the model!
model = MyModel(parameters)
results = model.run()