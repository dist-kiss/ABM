import agentpy as ap
import sensitivity_plots as splot

# run this script to perform the sensitivity analysis on already calculated model-outputs (e.g. with "run_sensitivity.py")

if __name__ == "__main__":
    # load results from "./sensitivity_data/<exp_name>_<exp_id>"
    results = ap.DataDict.load(exp_name='SA_Exp_Saltelli', exp_id="Agents_100_Iterations_1_N_1024",
                               path='sensitivity_data', display=True)

    # Calculate sobol indices on a given set of output metrics
    sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'mean_nod'])

    # Plot sensitivity results as barchart.
    #splot.plot_sobol_all_indices_horizontal(sob_results)
    splot.plot_horizontal_stacked_barchart(sob_results)

