# if(self.model.p.destination_log):
import pandas as pd
import geopandas as gpd
import networkx as nx
import momepy


def save_positions_to_file(position_list, epoch_time, sample_id, iteration ):
    """Create gpkg file with all positions of all agents within the model run, annotated with a time and Agent-ID label."""
    all_positions = pd.DataFrame(position_list) 
    final_gdf = gpd.GeoDataFrame(all_positions, geometry=all_positions['geometry'], crs="EPSG:5652")
    final_gdf.to_file('./Experiment/output/%d/positions_%s.gpkg' % (epoch_time, (str(sample_id) + "_" + str(iteration))), driver='GPKG', layer='Agents_temporal') 

def save_edges_to_file(edges, epoch_time, sample_id, iteration):
    """Create gpkg file with one features for each edge in every timestep, annotated with the people counters and time label."""
    final_edge_gdf = pd.concat(edges, ignore_index=True)        
    final_edge_gdf.to_file('./Experiment/output/%d/edges_%s.gpkg' % (epoch_time, (str(sample_id) + "_" + str(iteration))), driver='GPKG', layer='Edges_temporal')

def save_maximum_densities_to_file(graph, max_density, epoch_time, sample_id, iteration):
    """Create gpkg file with edges, annotated with the maximum density per edge at any point in time over the full model running time."""
    nx.set_edge_attributes(graph, max_density, "max_density")
    max_density_gdf = momepy.nx_to_gdf(graph, points=False)
    max_density_gdf.to_file("./Experiment/output/%d/max_density_%s.gpkg" % (epoch_time, (str(sample_id) + "_" + str(iteration))), driver='GPKG', layer='Max Density Edges') 

def save_compliance_nodes_to_file(nodes, epoch_time, sample_id, iteration):   
    """Create gpkg file with node positions, annotated with the amount of compliances at each node."""
    nodes[['degree', 'nodeID', 'geometry', 'compliances','non_compliances', 'random_reroutings', 'no_route_changes']].to_file('./Experiment/output/%d/compliance_locations_%s.gpkg' % (epoch_time, (str(sample_id) + "_" + str(iteration))), driver='GPKG', layer='Compliance Occurences')

def save_destinations_to_file(destination_list, epoch_time):
    """Create gpkg file with all destinations."""
    all_destinations = pd.DataFrame(destination_list)
    # clears out the column "new_assigned_dest" if there are any new assigned destinations in the destinations Dataframe
    if 'new_assigned_dest' in all_destinations.columns:
        initial_destinations = all_destinations.drop(['new_assigned_dest'], axis=1)
    else:
        initial_destinations = all_destinations
    # drop duplicate geometry and build geodataFrame
    initial_destination_gdf = gpd.GeoDataFrame(initial_destinations.drop('initial_dest', axis=1),
                                                    geometry=initial_destinations['initial_dest'],
                                                    crs="EPSG:5652")
    initial_destination_gdf.to_file(f'./output/initial_destinations_{str(epoch_time)}.gpkg',
                                    driver='GPKG', layer=f'initial_dest_{str(epoch_time)}')

    # clear out NaNs in 'new_assigned_dest' (they come from agents, that dont get a new destination assigned)
    if 'new_assigned_dest' in all_destinations.columns:
        new_assigned_dest = all_destinations.dropna(axis=0, how='any', inplace=False)
        new_assigned_dest = new_assigned_dest.drop('initial_dest', axis=1)
        new_assigned_dest = new_assigned_dest.reset_index(drop=True)
        # drop duplicate geometry and build geodataFrame
        new_assigned_gdf = gpd.GeoDataFrame(new_assigned_dest.drop('new_assigned_dest', axis=1),
                                                geometry=new_assigned_dest['new_assigned_dest'],
                                                crs="EPSG:5652")
        new_assigned_gdf.to_file(f'./output/new_assigned_destinations_{str(epoch_time)}.gpkg',
                                driver='GPKG', layer=f'new_assigned_dest_{str(epoch_time)}')

