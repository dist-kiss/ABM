import distkiss_abm
import agentpy as ap
import time

optimal_parameters = {
    'agents': 2000,
    'steps': 720,
    'duration': 5,
    'streets_path': "../input_data/quakenbrueck_street_width.gpkg",
    'constant_weight_mean': 0.3424823265591154,
    'constant_weight_sd': 0.4042530941646003,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    'walking_speed_mean': 1.25,
    'walking_speed_std': 0.21,
    # Density not used as weight so far.
    'weight_density': 0,
    'seed': 43,
    'out_name': int(time.time()),
    # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
    # Scenario 2: 'simple_compliance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': 'complex_compliance',
    # Choose when to record non compliance probability (basically choose definition of non compliance); Default is True:
    # False = Non compliance is only where agent initially wanted to walk into forbidden one way street
    # True = Additionally in situations, in which agent keeps its route doing a second evalutation after initally 
    #       wanting to (randomly) reroute into ows.
    'record_second_opinion_ncps': True,
    # Whether agents can reroute from inital path, by default True. Only turn of if agents shall be restricted to inital path!
    'rerouting_allowed': True,
    # Whether to assign new origin & destinations to agents after having reached their destination.
    'assign_new_destinations': True,
    # Whether only new destinations shall be assigned and previous destination is used as origin
    'reuse_previous_dest_as_orig': False,
    'origin_destination_pairs': False,
    # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
    # Whether positions, edges and destination should be saved as gpkg files:
    'positions': True,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': True,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

model = distkiss_abm.DistanceKeepingModel(optimal_parameters)
results = model.run()