import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# Function for plotting
def plot_sobol(results):
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