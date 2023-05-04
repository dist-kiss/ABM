import agentpy as ap
import sensitivity_plots as splot

# load results from "./sensitivity_data/<exp_name>_<exp_id>"
results = ap.DataDict.load(exp_name='SA_Exp_Saltelli', exp_id="low_-2sd_up_+2sd_N1024_Iter_1_Agents_100", path='sensitivity_data', display=True)

# Calculate sobol indices on a given set of output metrics
sob_results = results.calc_sobol(reporters=['mean_non_comp_prob', 'mean_nod'])

# Plot sensitivity results as barchart.
splot.plot_horizontal_stacked_barchart(sob_results)
#splot.plot_vertical_barchart(sob_results)