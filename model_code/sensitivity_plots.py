import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import seaborn as sns

# Function for plotting
def plot_sobol_all_indices_horizontal(results):
    """ Bar plot of Sobol sensitivity indices. """

    sns.set()
    fig, axs = plt.subplots(1, 2, figsize=(8, 4))
    si_list = results.sensitivity.sobol.groupby(by='reporter')
    si_conf_list = results.sensitivity.sobol_conf.groupby(by='reporter')

    for (key, si), (_, err), ax in zip(si_list, si_conf_list, axs):
        si = si.droplevel('reporter')
        err = err.droplevel('reporter')
        si.plot.barh(xerr=err, title=key, ax=ax, capsize = 3)
        ax.set_xlim(0)

    axs[0].get_legend().remove()
    axs[1].set(ylabel=None, yticklabels=[])
    axs[1].tick_params(left=False)
    plt.tight_layout()
    plt.show()


def plot_barchart(contributions_to_var_nod, contributions_to_var_non_comp_prob):
    """Deprecated. Just keep this as a Code-Snippet for possible later use."""
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


def plot_vertical_barchart(results):
    # get dataframe with all S1-indices for the reporters
    si_list = list(results.sensitivity.sobol.groupby(by='reporter')['S1'])

    # get DataFrames for the output parameters
    _, df_mean_nod = si_list[0]
    _, df_mean_non_comp_prob = si_list[1]
    # clean up DataFrames
    df_mean_nod = df_mean_nod.droplevel('reporter')
    df_mean_non_comp_prob = df_mean_non_comp_prob.droplevel('reporter')

    contribution_to_variance_in_mean_nod = []
    contribution_to_variance_in_mean_non_comp_prob = []

    # transform dataframe values into a list
    for _, percentage in df_mean_nod.items():
        contribution_to_variance_in_mean_nod.append(percentage)

    for _, percentage in df_mean_non_comp_prob.items():
        contribution_to_variance_in_mean_non_comp_prob.append(percentage)

    #contribution_to_variance_in_mean_nod_by_snd_order_effects = 1 - sum(contribution_to_variance_in_mean_nod)
    #contribution_to_variance_in_mean_non_comp_prob_by_snd_order_effects = 1 - sum(contribution_to_variance_in_mean_non_comp_prob)
    output_parameters = ('mean normalised-observed-detour', 'mean non-compliance-probability')

    # Dictionary of input parameters and their contribution to the variance mean_nod and mean_non_comp_prob. Also used for labeling the bars in the plot
    percentages = {
        'regression constant': [contribution_to_variance_in_mean_nod[0], contribution_to_variance_in_mean_non_comp_prob[0]],
        'weight relative-total-detour': [contribution_to_variance_in_mean_nod[1], contribution_to_variance_in_mean_non_comp_prob[1]],
        'weight oneway-street': [contribution_to_variance_in_mean_nod[2], contribution_to_variance_in_mean_non_comp_prob[2]],
        'mean walking speed': [contribution_to_variance_in_mean_nod[3], contribution_to_variance_in_mean_non_comp_prob[3]],
        #'snd_order_effects': [contribution_to_variance_in_mean_nod_by_snd_order_effects, contribution_to_variance_in_mean_non_comp_prob_by_snd_order_effects]
    }
    matplotlib.rcParams.update({'font.size': 18})

    fig, ax = plt.subplots()
    # create array of 0 to store the different layers in the bars
    bottom = np.zeros(2)
    # label x-label locations
    x_pos = [0, 0.25]
    width_bar = 0.2

    # loop through all Label+Percentage-Tuples to create the bars for the plot
    for label, percentage in percentages.items():
        ax.bar(x_pos, percentage, width=width_bar, label=label, bottom=bottom)
        # base values to put the next "Layer" of values ontop
        bottom += percentage

    ax.set_title("Sobol-first-order-indices")
    ax.set_ylim([0, 1])
    ax.set_ylabel('contribution to model output variance')
    ax.set_xticks(x_pos, output_parameters)
    ax.set_xlabel('model output')
    plt.tight_layout()
    # create bottom-centered legend, outside of the axes. The legend is aligned to the figure, instead of the Axes-Object.
    plt.legend(bbox_to_anchor=(0.02, 0.02, 1, 0.02), loc="lower center", bbox_transform=fig.transFigure, ncol=2)
    plt.subplots_adjust(bottom=0.3)

    plt.show()







