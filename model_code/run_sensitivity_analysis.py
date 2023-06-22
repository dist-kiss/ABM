import distkiss_abm
import agentpy as ap
import time
import sensitivity_plots as splot

# Before using, please inform yourself about agentpy's sensitivity analysis functions (they use the python library "SALib")
# use this script to calculate model-outputs to use for a sensitivity analysis.

if __name__ == "__main__":
    # MODEL PARAMETERS FOR SENSITIVITY ANALYSIS (SA)
    sa_parameters = {
        'agents': 100,  # number of agents in the model
        'steps': 2000,
        # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached)
        'duration': 5,  # duration of a timepstep
        'streets_path': "../input_data/quakenbrueck_street_width.gpkg",  # street network of the model
        # Range (mean-2*SD, mean+2*SD) is used for all "input parameters" of the sensitivity analysis. This is used to draw samples from
        # with Saltelli' Sampling Method. This data was collected by doing a bootstrap of study data.
        'constant_weight_mean': ap.Range(0.3424823265591154 - 2 * 0.4042530941646003,
                                         0.3424823265591154 + 2 * 0.4042530941646003),
        'constant_weight_sd': 0,
        'rtd_weight_mean': ap.Range(4.062769564671944 - 2 * 1.7983272569373019,
                                    4.062769564671944 + 2 * 1.7983272569373019),
        'rtd_weight_sd': 0,
        'ows_weight_mean': ap.Range(-1.686987748677264 - 2 * 0.453969999609177449,
                                    -1.686987748677264 + 2 * 0.453969999609177449),
        'ows_weight_sd': 0,
        'walking_speed_mean': ap.Range(1.25 - 2 * 0.21, 1.25 + 2 * 0.21),
        'walking_speed_std': 0,
        # Density not used as weight so far.
        'weight_density': 0,
        'seed': 43,  # seed for the RNG used in the model
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
        'epoch_time': int(time.time()),  # artificial time used to enum outputs
        'origin_destination_pairs': False,
        # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
        # Whether positions, edges and destination should be saved as gpkg files:
        'positions': False,
        'edges': False,
        'destination_log': False,
        'compliance_nodes': False,
        'max_densities': False,
        # Add logs for debugging
        'logging': False,
    }
    # SENSITIVITY ANALYSIS SPECIFIC PARAMETERS

    # Runtime increases significantly with larger samplesize.
    # 1024 has proven to achieve proper convergence of the sobol sequence for this model.
    number_of_samples = 1024  # should be choosen as power of 2.

    # Defines how often the model-run is repeated with the same saltelli sample.
    # More Iterations haven't shown improved results in the later analysis, so it's set to 1.
    number_of_model_iterations = 1

    # name for saving the experiment.
    exp_name = 'SA_Exp_Saltelli'

    # ID for the experiment
    exp_id = f'Agents_{sa_parameters[f"agents"]}_Iterations_{number_of_model_iterations}_N_{number_of_samples}'

    # Create Saltelli samples
    saltelli_sample = ap.Sample(
        sa_parameters,
        n=number_of_samples,
        method='saltelli',
        calc_second_order=True
    )

    # Run experiment.
    sa_exp = ap.Experiment(distkiss_abm.DistanceKeepingModel, saltelli_sample, iterations=number_of_model_iterations,
                           record=False)
    results = sa_exp.run(n_jobs=-1, verbose=10)

    # Save results to "./sensitivity_data/<exp_name>_<exp_id>" (change exp_id for multiple runs)
    results.save(exp_name=exp_name, exp_id=exp_id, path='sensitivity_data', display=True)

    # Plot histograms of reporters.
    results.reporters.hist()

    # Calculate sobol indices on a given set of output metrics
    sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'mean_nod'])

    # Plot sensitivity results as barchart.
    splot.plot_sobol_all_indices_horizontal(sob_results)



