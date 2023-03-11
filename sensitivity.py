import abm
import agentpy as ap
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# input part (change parameters of the model)
input_parameters = ['walking_speed_std', 'constant_weight_sd', 'rtd_weight_sd', 'ows_weight_sd']
doctitles = ["walking_speed_stochastic", "constant_weight_stochastic", "rtd_weight_stochastic", "ows_weight_stochastic"]

loop_params = {'agents': 100,
               'steps': 100}

# change these values to execute specific parts of the script
run = False
# run_with_sobol = False
calc_contribution = True
plot = False

# Loop part (run model with the different inputs and save the output)
if run:
    # calculate variances with all parameters stochastic
    abm.exp_parameters['agents'] = loop_params['agents']
    abm.exp_parameters['steps'] = loop_params['steps']
    sample = ap.Sample(abm.exp_parameters, randomize=False)
    exp = ap.Experiment(abm.DistanceKeepingModel, sample, iterations=1, record=True)
    print("Run with all_stochastic\n \n")
    results = exp.run(n_jobs=-1, verbose=10)
    # converts reporters for the variances into a dictionary
    d = {'var_nod': list(results.reporters['var_nod']),
         'var_non_comp_prob': list(results.reporters['var_non_comp_prob'])}
    df = pd.DataFrame(data=d, index=['all_stochastic'])
    df.to_csv(f"./sensitivity_data/variances_all_stochastic.csv", index=True)

    # calculates variances for stochastic parameters
    for param, title in zip(input_parameters, doctitles):
        # create list of parameters, which will be fixed to their mean
        non_stochastic_parameters = [ele for ele in input_parameters if ele != param]
        default_values = []
        for p in non_stochastic_parameters:
            # save old parameter value
            default_values.append(abm.exp_parameters[p])
            # fix choosen parameter distribution to its mean (by setting the sd of the normal distribution to 0)
            abm.exp_parameters[p] = 0

        # create sample of input parameters for the model, where only one parameter is stochastic
        sample = ap.Sample(abm.exp_parameters, randomize=False)
        exp = ap.Experiment(abm.DistanceKeepingModel, sample, iterations=1, record=True)
        print(f"Run with {title}\n\n")
        results = exp.run(n_jobs=-1, verbose=10)
        # converts reporters for the variances into a dictionary
        d = {'var_nod': list(results.reporters['var_nod']),
             'var_non_comp_prob': list(results.reporters['var_non_comp_prob'])}
        df = pd.DataFrame(data=d, index=[title])
        df.to_csv(f"./sensitivity_data/variances_{title}.csv", index=True)

        # reset fixed parameters to their old values
        for val, p in zip(default_values, non_stochastic_parameters):
            abm.exp_parameters[p] = val

# if run_with_sobol:
#     # calculate sobol indices with all parameters stochastic
#     abm.exp_parameters['agents'] = loop_params['agents']
#     abm.exp_parameters['steps'] = loop_params['steps']
#
#     problem = {
#         'num_vars': 4,
#         'names': ['walking_speed', 'constant_weight', 'rtd_weight', 'ows_weight'],
#         'bounds': [[abm.exp_parameters['walking_speed_mean'], abm.exp_parameters['walking_speed_std']],
#                    [abm.exp_parameters['constant_weight_mean'], abm.exp_parameters['constant_weight_sd']],
#                    [abm.exp_parameters['rtd_weight_mean'], abm.exp_parameters['rtd_weight_sd']],
#                    [abm.exp_parameters['ows_weight_mean'], abm.exp_parameters['ows_weight_sd']]
#                    ],
#         'dists': ['norm', 'norm', 'norm', 'norm']
#     }
#
#     sample = ap.Sample(problem, n=2, method='saltelli', randomize=False)
#     exp = ap.Experiment(abm.DistanceKeepingModel, sample, iterations=1, record=True)
#     results = exp.run(n_jobs=-1, verbose=10)
#     Si = results.calc_sobol(['var_nod', 'var_non_comp_prob'])
#     print(Si)

if calc_contribution:
    # load variance data saved from an experiment
    variances = pd.concat(map(pd.read_csv, ['./sensitivity_data/variances_all_stochastic.csv',
                                            './sensitivity_data/variances_walking_speed_stochastic.csv',
                                            './sensitivity_data/variances_constant_weight_stochastic.csv',
                                            './sensitivity_data/variances_rtd_weight_stochastic.csv',
                                            './sensitivity_data/variances_ows_weight_stochastic.csv']),
                                            ignore_index=True)

    # calculate contribution of the parameters to the model variances
    print(variances)
    indexes = list(variances.index)

    # indexes of "variances"-DataFrame
    # 0 = all_stochastic
    # 1 = walking_speed_stochastic
    # 2 = constant_weight_stochastic
    # 3 = rtd_weight_stochastic
    # 4 = ows_weight_stochastic

    # calculate parameter contribution to var_nod
    contributions_to_var_nod = []

    for idx in indexes[1:]:
        res = variances.loc[idx, "var_nod"] / variances.loc[0, "var_nod"]
        contributions_to_var_nod.append(res * 100)  # mult by 100 to get "%"

    # calculate parameter contribution to var_non_comp_prob
    contributions_to_var_non_comp_prob = []

    for idx in indexes[1:]:
        res = variances.loc[idx, "var_non_comp_prob"] / variances.loc[0, "var_non_comp_prob"]
        contributions_to_var_non_comp_prob.append(res * 100)  # mult by 100 to get "%"

    print(f"Contribution to var_nod: {contributions_to_var_nod}")
    print(f"Contribution to var_non_comp_prob: {contributions_to_var_non_comp_prob}")

    controlsum_var_nod = sum(contributions_to_var_nod)
    controlsum_non_comp_prob = sum(contributions_to_var_non_comp_prob)

    print(f"Sum of contributions_to_var_nod: {controlsum_var_nod}%")
    print(f"Sum of contributions_to_var_non_comp_prob: {controlsum_non_comp_prob}%")


def plot_barchart():
    # Labels for the bars
    model_outputs = ('var_nod', 'var_non_comp_prob')

    # Dictionary with values of the contribution to the variances. Also used for labeling the bars in the plot
    percentages = {
        'walking_speed': [contributions_to_var_nod[0], contributions_to_var_non_comp_prob[0]],
        'constant_weight': [contributions_to_var_nod[1], contributions_to_var_non_comp_prob[1]],
        'rtd_weight': [contributions_to_var_nod[2], contributions_to_var_non_comp_prob[2]],
        'ows_weight': [contributions_to_var_nod[3], contributions_to_var_non_comp_prob[3]]
    }

    fig, ax = plt.subplots()
    # create array of 0 to store the different layers in the bars
    bottom = np.zeros(2)

    # loop through all Label+Percentage-Tuples to create the bars for the plot
    for label, percentage in percentages.items():
        ax.bar(model_outputs, percentage, width=0.5, label=label, bottom=bottom)
        # base values to put the next "Layer" of values ontop
        bottom += percentage

    ax.set_title("Sensitivity Analysis")
    ax.set_ylabel('contribution to total variance [in %]')
    plt.tight_layout(rect=[0, 0, 0.75, 1])
    # create right-aligned legend
    ax.legend(title='input parameters', bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)

    plt.show()


if plot:
    plot_barchart()
