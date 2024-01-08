import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


# Function for plotting
def plot_sobol_all_indices_horizontal(results):
    """ Bar plot of Sobol sensitivity indices. Plots indices of all orders that were calculated"""


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


def get_data_from_DataDict(datadict, get_second_order_data=False):
    """Returns dictionary with sobol-first-order indices for each tested input parameter. Each entry is a list with
    one value per output parameter"""

    # get dataframe with all S1-indices for the reporters
    df_mean_nod = datadict.sensitivity.sobol['S1']['mean_nod']
    df_mean_non_comp_prob = datadict.sensitivity.sobol['S1']['mean_non_comp_prob']

    contribution_to_variance_in_mean_nod = []
    contribution_to_variance_in_mean_non_comp_prob = []

    # transform dataframe values into a list
    for percentage in df_mean_nod:
        contribution_to_variance_in_mean_nod.append(percentage)

    for percentage in df_mean_non_comp_prob:
        contribution_to_variance_in_mean_non_comp_prob.append(percentage)

    # Dictionary of input parameters and their contribution to the variance mean_nod and mean_non_comp_prob. Also used for labeling the bars in the plot
    percentages = {
        r'$\alpha$': [contribution_to_variance_in_mean_nod[0], contribution_to_variance_in_mean_non_comp_prob[0]], # 'regression constant'
        r'$\beta_{rtd}$': [contribution_to_variance_in_mean_nod[1], contribution_to_variance_in_mean_non_comp_prob[1]], # 'weight relative-total-detour'
        r'$\beta_{forbidden}$': [contribution_to_variance_in_mean_nod[2], contribution_to_variance_in_mean_non_comp_prob[2]], # 'weight oneway-street'
        'ws': [contribution_to_variance_in_mean_nod[3], contribution_to_variance_in_mean_non_comp_prob[3]], # 'mean walking speed'
    }

    # Add second-order indice data to percentages dict
    if get_second_order_data:
        contribution_to_variance_in_mean_nod_by_snd_order_effects = 1 - sum(contribution_to_variance_in_mean_nod)
        contribution_to_variance_in_mean_non_comp_prob_by_snd_order_effects = 1 - sum(contribution_to_variance_in_mean_non_comp_prob)
        percentages['snd_order_effects'] = [
            contribution_to_variance_in_mean_nod_by_snd_order_effects,
            contribution_to_variance_in_mean_non_comp_prob_by_snd_order_effects
        ]

    return percentages


def plot_vertical_stacked_barchart(results,print_second_order_indices=False):
    # Adjust the code, to create the needed plot

    percentages = get_data_from_DataDict(results, print_second_order_indices)

    fig, ax = plt.subplots(figsize=(2, 2), dpi=250)
    output_parameters = ('mean\n normalised\n detour', 'mean\n non-compliance\n probability')

    # create array of 0 to store the different layers in the bars
    bottom = np.zeros(len(output_parameters))
    width_bar = 0.7

    # set colors for each stacked parameter
    if print_second_order_indices:
        colors = ['cornflowerblue', 'orange', 'plum', 'limegreen', "green"]
    else:
        colors = ['cornflowerblue', 'orange', 'plum', 'limegreen']

    # loop through all Label+Percentage-Tuples to create the bars for the plot
    for color, data in zip(colors, percentages.items()):
        label = data[0]
        percentage = data[1]
        ax.bar(x=output_parameters, height=percentage, width=width_bar, label=label, bottom=bottom, color=color)
        # base values to put the next "Layer" of values ontop
        bottom += percentage

    # Format axes information
    ax.set_title("Sobol First Order Indices", fontsize=9)
    ax.set_xlabel('model output')
    ax.set_xlim(-0.7, len(output_parameters)-0.3)

    ax.set_ylabel('contribution to model output variance')
    ax.set_ylim([0, 1])


    # create bottom-centered legend, outside of the axes. The legend is aligned to the figure, instead of the Axes-Object.
    plt.legend(bbox_to_anchor=(0.02, 0.02, 1, 0.02), loc="lower center", bbox_transform=fig.transFigure, ncol=2)
    plt.subplots_adjust(bottom=0.4, left=0.3, right=0.5) # make room for legend

    plt.tight_layout()
    plt.show()
    Path("Plots/").mkdir(parents=True, exist_ok=True)
    fig.savefig("Plots/vertical_barchart_sobol_indices.pdf", dpi=250, bbox_inches='tight')

def plot_horizontal_stacked_barchart(results, print_second_order_indices=False):
    # Adjust the code, to create the needed plot

    percentages = get_data_from_DataDict(results, print_second_order_indices)

    fig, ax = plt.subplots(figsize=(5.9, 2.5), dpi=250)
    output_parameters = ('mean\n normalised\n detour', 'mean\n non-compliance\n probability')

    # create array of 0 to store the different layers in the bars
    left = np.zeros(len(output_parameters))
    height_bar = 0.7

    # set colors for each stacked parameter
    if print_second_order_indices:
        colors = ['cornflowerblue', 'orange', 'plum', 'limegreen', "green"]
    else:
        colors = ['cornflowerblue', 'orange', 'plum', 'limegreen']


    # loop through all Label+Percentage-Tuples to create the bars for the plot
    for color, data in zip(colors, percentages.items()):
        label = data[0]
        percentage = data[1]
        ax.barh(y=output_parameters, width=percentage, left=left, height=height_bar, label=label, color=color)
        # base values to put the next "Layer" of values on top
        left += percentage

    # Format axes information
    ax.set_title("Sobol First Order Indices", fontsize=9)
    ax.set_xlim([0, 1])
    ax.set_xlabel('contribution to model output variance', fontsize=8)
    ax.tick_params(axis="x", direction="in")
    ax.tick_params(axis='y', labelsize=8)

    ax.set_ylim(-0.635, 2.11)
    ax.yaxis.set_ticks_position('none')
    ax.set_ylabel('model output', fontsize=9)

    # create legend inside the axes
    plt.legend(loc='upper center', ncol=2, fontsize=8, frameon=False)
    plt.tight_layout()
    #plt.subplots_adjust(bottom=0.4, left=0.292, right=0.962, top=0.912) # make room for legend
    plt.show()
    Path("Plots/").mkdir(parents=True, exist_ok=True)
    fig.savefig("Plots/horizontal_barchart_sobol_indices.pdf", dpi=250, bbox_inches='tight')




