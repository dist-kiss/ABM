import distkiss_abm
import agentpy as ap
import time
import os

# Compliance Case Study - Eight one-way-streets, 4000 agents

parameters_compliance_study = {
    'agents': 4000, # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': 'input_data/quakenbrueck_street_width_8_ows.gpkg',
    # Model weights
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
    'out_name': "compliance_study",
    # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
    # Scenario 2: 'simple_compliance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': ap.Values('no_interventions', 'simple_compliance', 'complex_compliance'),
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
    'positions': False,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

sample_compliance_study = ap.Sample(parameters_compliance_study, randomize=False)

# Perform experiment
exp_compliance_study = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample_compliance_study, iterations=10, record=True)
results_compliance_study = exp_compliance_study.run(n_jobs=6, verbose=100)
results_compliance_study.save(exp_name='E', exp_id=parameters_compliance_study['out_name'], path='Experiment', display=True)



# Scenario 0 - No one-way-streets

parameters_no_ows = {
    'agents': ap.Values(2000, 4000, 10000), # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': 'input_data/quakenbrueck_street_width_no_ows.gpkg',
    # Model weights
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
    'out_name': "0_ows",
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
    'positions': False,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

sample_no_ows = ap.Sample(parameters_no_ows, randomize=False)

# Perform experiment
exp_no_ows = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample_no_ows, iterations=10, record=True)
results_no_ows = exp_no_ows.run(n_jobs=5, verbose=100)
results_no_ows.save(exp_name='E', exp_id=parameters_no_ows['out_name'], path='Experiment', display=True)


# Scenario 1 - Four one-way-streets

parameters_4_ows = {
    'agents': ap.Values(2000, 4000, 10000), # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': 'input_data/quakenbrueck_street_width_4_ows.gpkg',
    # Model weights
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
    'out_name': "4_ows",
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
    'positions': False,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

sample_4_ows = ap.Sample(parameters_4_ows, randomize=False)

# Perform experiment
exp_4_ows = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample_4_ows, iterations=10, record=True)
results_4_ows = exp_4_ows.run(n_jobs=5, verbose=100)
results_4_ows.save(exp_name='E', exp_id=parameters_4_ows['out_name'], path='Experiment', display=True)


# Scenario 2 - Eight one-way-streets

parameters_8_ows = {
    'agents': ap.Values(2000, 4000, 10000), # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': 'input_data/quakenbrueck_street_width_8_ows.gpkg',
    # Model weights
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
    'out_name': "8_ows",
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
    'positions': False,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

sample_8_ows = ap.Sample(parameters_8_ows, randomize=False)

# Perform experiment
exp_8_ows = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample_8_ows, iterations=10, record=True)
results_8_ows = exp_8_ows.run(n_jobs=5, verbose=100)
results_8_ows.save(exp_name='E', exp_id=parameters_8_ows['out_name'], path='Experiment', display=True)

# Scenario 3 - Ten one-way-streets

parameters_10_ows = {
    'agents': ap.Values(2000, 4000, 10000), # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': 'input_data/quakenbrueck_street_width_10_ows.gpkg',
    # Model weights
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
    'out_name': "10_ows",
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
    'positions': False,
    'edges' : True,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': True,
    # Add logs for debugging
    'logging': False,
}

sample_10_ows = ap.Sample(parameters_10_ows, randomize=False)

# Perform experiment
exp_10_ows = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample_10_ows, iterations=10, record=True)
results_10_ows = exp_10_ows.run(n_jobs=5, verbose=100)
results_10_ows.save(exp_name='E', exp_id=parameters_10_ows['out_name'], path='Experiment', display=True)