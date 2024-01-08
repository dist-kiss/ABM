import distkiss_abm
import agentpy as ap
import time
import sensitivity_plots as splot

# Model parameters for sensitivity analysis (SA)
sa_parameters = {
    # TODO: Think about varying the number of agents (decrease or increase?)
    'agents': 100, # number of agents 
    'steps': 2000, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': "../input_data/quakenbrueck_street_width.gpkg",
    # For SA set SD values to 0 and only vary mean value -> all agents within one model run will get the same parameters
    # Range (mean-SD, mean+SD) is used here. TODO: Vary range. E.g. use (mean*0.5, mean*2) or similar 
    'constant_weight_mean': ap.Range(0.3424823265591154-0.4042530941646003, 0.3424823265591154+0.4042530941646003),
    'constant_weight_sd': 0,
    'rtd_weight_mean': ap.Range(4.062769564671944-1.7983272569373019, 4.062769564671944+1.7983272569373019), 
    'rtd_weight_sd': 0,
    'ows_weight_mean': ap.Range(-1.686987748677264-0.453969999609177449, -1.686987748677264+0.453969999609177449), 
    'ows_weight_sd': 0,
    # TODO: IF OUTPUT METRICS STAY AS THEY ARE (non_comp_prob and nod) WALKING SPEED DOES NOT NEED TO BE CONSIDERED IN SA!
    'walking_speed_mean': ap.Range(1.25-0.21, 1.25+0.21),
    'walking_speed_std': 0,
    # Density not used as weight so far.
    'weight_density': 0,
    'seed': 43,
    'scenario': 'complex_compliance',
    # Choose when to record non compliance probability (basically choose definition of non compliance); Default is True:
    # False = Non compliance is only where agent initially wanted to walk into forbidden one way street
    # True = Additionally in situations, in which agent keeps its route doing a second evalutation after initally 
    #       wanting to (randomly) reroute into ows.
    'record_second_opinion_ncps': True,
    # Whether agents can reroute from inital path, by default True. Only turn of if agents shall be restricted to inital path!
    'rerouting_allowed': True,
    # TODO: Decide whether to run the model with agents getting new destinations assigned after having reached their destination.
    # False -> No new agent generation | True -> New agent generation
    'assign_new_destinations': False,
    # Whether only new destinations shall be assigned and previous destination is used as origin
    'reuse_previous_dest_as_orig': False,
    'out_name': int(time.time()),
    'origin_destination_pairs': False,
    # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
    # Whether positions, edges and destination should be saved as gpkg files:
    'positions': False,
    'edges' : False,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': False,
    # Add logs for debugging
    'logging': False,
}

# Create Saltelli samples
# TODO: Increase number of samples.
sample = ap.Sample(
    sa_parameters,
    n=8,
    method='saltelli',
    calc_second_order=True
)
# Run experiment.
# TODO: Vary number of iterations (most likely increase)
sa_exp = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample, iterations=30, record=False)
results = sa_exp.run(n_jobs=-1, verbose=10)
# Save results to "./sensitivity_data/SA_Exp_Saltelli_01" (change exp_id for multiple runs)
results.save(exp_name='SA_Exp_Saltelli', exp_id="01", path='sensitivity_data', display=True)
# Plot histograms of reporters.
results.reporters.hist()

# Calulcate sobol statistics on a given set of output metrics (mean_non_comp_prob and var_non_comp_prob)
# TODO: Add other output metrics such as NOD etc.
sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'var_non_comp_prob'])

# Plot sensitivty results as barchart.
splot.plot_sobol(sob_results)
