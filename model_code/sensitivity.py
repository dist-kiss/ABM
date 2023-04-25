import distkiss_abm
import agentpy as ap
import time
import sensitivity_plots as splot

run = False
load_and_calc = True


# Model parameters for sensitivity analysis (SA)
lower_range_modifier = 0.25
upper_range_modifier = 1.25

sa_parameters = {
    # TODO: Think about varying the number of agents (decrease or increase?)
    'agents': 100, # number of agents
    'steps': 2000, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached)
    'duration': 5,
    'streets_path': "../input_data/quakenbrueck_street_width.gpkg",
    # For SA set SD values to 0 and only vary mean value -> all agents within one model run will get the same parameters
    # Range (mean-2*SD, mean+2*SD) is used here.
    'constant_weight_mean': ap.Range(0.3424823265591154-2*0.4042530941646003, 0.3424823265591154+2*0.4042530941646003),
    'constant_weight_sd': 0,
    'rtd_weight_mean': ap.Range(4.062769564671944-2*1.7983272569373019, 4.062769564671944+2*1.7983272569373019),
    'rtd_weight_sd': 0,
    'ows_weight_mean': ap.Range(-1.686987748677264-2*0.453969999609177449, -1.686987748677264+2*0.453969999609177449),
    'ows_weight_sd': 0,
    'walking_speed_mean': ap.Range(1.25-2*0.21, 1.25+2*0.21),
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
    # False -> No new agent generation | True -> New agent generation
    'assign_new_destinations': False,
    # Whether only new destinations shall be assigned and previous destination is used as origin
    'reuse_previous_dest_as_orig': False,
    'epoch_time': int(time.time()),
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
sample = ap.Sample(
    sa_parameters,
    n=1024,
    method='saltelli',
    calc_second_order=True
)

if run:
    # Run experiment.
    sa_exp = ap.Experiment(distkiss_abm.DistanceKeepingModel, sample, iterations=1, record=False)
    results = sa_exp.run(n_jobs=-1, verbose=10)
    # Save results to "./sensitivity_data/SA_Exp_Saltelli_01" (change exp_id for multiple runs)
    results.save(exp_name='SA_Exp_Saltelli', exp_id="low_0,25_up_1,25_N16_Iter_100", path='sensitivity_data', display=True)
    # Plot histograms of reporters.
    results.reporters.hist()

    # Calulcate sobol statistics on a given set of output metrics (mean_non_comp_prob and var_non_comp_prob)
    # TODO: Add other output metrics such as NOD etc.
    sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'mean_nod'])

    # Plot sensitivty results as barchart.
    splot.plot_sobol_all_indices_horizontal(sob_results)

if load_and_calc:
    # load results from "./sensitivity_data/SA_Exp_Saltelli_low_0,5_up_2"
    results = ap.DataDict.load(exp_name='SA_Exp_Saltelli', exp_id="low_-2sd_up_+2sd_N1024_Iter_1_Agents_100", path='sensitivity_data', display=True)
    # Calulcate sobol statistics on a given set of output metrics (mean_non_comp_prob and var_non_comp_prob)
    sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'mean_nod'])
    # Plot sensitivty results as barchart.
    #splot.plot_sobol_all_indices_horizontal(sob_results)
    #splot.plot_vertical_barchart(sob_results)
    print(sob_results.sensitivity)
