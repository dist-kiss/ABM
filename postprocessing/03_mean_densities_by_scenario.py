import fiona
import json
import os
from pathlib import Path
import pandas as pd
from statistics import mean, stdev, median
import json
import geopandas
import matplotlib.pyplot as plt 
import random
import numpy as np
import scipy.stats as st
import json
import seaborn as sns
import itertools



def sort_by_street(input_file, output_name):
    """ Takes several spatial vector files with the same spatial features and returns a dict, that groups features by ID.
        Returns:
            Dict {
            "1":[feature1, feature 2, ...],
            "2":[feature1, feature 2, ...],
            ...
        }
    """
    density_list = []
    for file in input_file:
        shape = fiona.open(file)
        for feat in shape:
            density_list.append([feat['properties']['ID'], feat['properties']['density']])
    all_dens = pd.DataFrame(density_list, columns=['ID','density'])
    all_dens.to_csv(output_name, index=False)
    return all_dens

def plot_overall_distributions(street_dict, scenario_str, xmax=1,ymax=125000):
    sns.set()
    color_palette = itertools.cycle(sns.color_palette())
    # set bin sixe
    bins=np.arange(0,1,0.01)    
    f, ax = plt.subplots()
    all_dens = []

    # plot densites as histogram
    for index, data in enumerate(street_dict, start=1):
        densities = data['density']
        all_dens.append(densities)
        n,x,_ = ax.hist(densities, bins, label=str(scenario_str[index-1]), color=next(color_palette), histtype=u'step', alpha=0.5)

    # add distance threshold line
    ax.axvline(0.16, alpha = 1, linestyle = "-", color = "red", label="Density limit 1m distance keeping")

    # add labels and plot styling
    plt.legend(loc='upper right')
    f.suptitle('Crowdedness on streets at 0.2 Hz', fontsize=16)
    plt.xlim(0, xmax)
    plt.ylim(0, ymax)
    plt.ylabel("Frequency")
    plt.xlabel("Crowdedness in people / m^2")

    # save to file and show
    plt.savefig("%s/averages/fixed_x_y_bins_0_01_outline_hists.pdf" % text, bbox_inches='tight')
    plt.savefig("%s/averages/fixed_x_y_bins_0_01_outline_hists.png" % text, bbox_inches='tight')
    plt.show()



def plot_boxplots(street_dict, scenario_str, xmax=1,ymax=125000):
    # create folder
    Path("%s/boxplots/" % text).mkdir(parents=True, exist_ok=True)
    sns.set()
    f, ax = plt.subplots()
    # add scenairo column to data
    for index, data in enumerate(street_dict, start=0):
        data['scenario'] = scenario_str[index]
    all_den_df = pd.concat(street_dict)

    # plot violins 
    sns.violinplot(all_den_df, x='scenario', y='density', ax=ax, hue='scenario')
    # plot threshold
    ax.axhline(0.16, alpha = 1, linestyle = "-", color = "red", label="Limit for keeping distance of 1m")
    # add labels and legend
    plt.ylabel("Crowdedness in people / m^2")
    plt.xlabel("Scenario")
    plt.legend(loc='best')
    # save figure and display
    plt.savefig("%s/boxplots/violin_plots.png" % text, bbox_inches='tight')
    plt.show()



# ---------------------------- MAIN --------------------------------
# list of folder names (adapt filenaming and axis titles if other experiment was other than a compliance scenario test)
ids = ['compliance_study']
for i in ids:
    text = "Experiment/output/" + i
    no_comp_dict_path = "%s/averages/no_comp_dict.csv" % text
    full_comp_dict_path = "%s/averages/full_comp_dict.csv" % text
    cali_comp_dict_path = "%s/averages/cali_comp_dict.csv" % text
    no_comp_files = list()
    full_comp_files = list()
    cali_comp_files = list()
    for (dirpath, dirnames, filenames) in os.walk(text):
        for file in filenames:
            if file.startswith("edges_"):
                if file.endswith(".gpkg"):
                    if file.startswith("edges_0"):
                        no_comp_files += [os.path.join(dirpath, file)]
                    elif file.startswith("edges_1"):
                        full_comp_files += [os.path.join(dirpath, file)]
                    elif file.startswith("edges_2"):
                        cali_comp_files += [os.path.join(dirpath, file)]

    # Create folder
    Path("%s/averages/" % text).mkdir(parents=True, exist_ok=True)
    # no compliance (== no interventions)
    if(os.path.isfile(no_comp_dict_path)):
        no_comp_dict = pd.read_csv(no_comp_dict_path)
    else:
        no_comp_dict = sort_by_street(no_comp_files, no_comp_dict_path)
    # full compliance
    if(os.path.isfile(full_comp_dict_path)):
        full_comp_dict = pd.read_csv(full_comp_dict_path)
    else:
        full_comp_dict = sort_by_street(full_comp_files, full_comp_dict_path)
    # calibrated compliance
    if(os.path.isfile(cali_comp_dict_path)):
        cali_comp_dict = pd.read_csv(cali_comp_dict_path)
    else:
        cali_comp_dict = sort_by_street(cali_comp_files, cali_comp_dict_path)

    # Plot data
    plot_overall_distributions([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"], xmax=0.9, ymax=70000)
    plot_boxplots([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"], i)
print("Script complete.")