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


def plot_boxplots(street_dict, scenario_str, ax, i):
    for index, data in enumerate(street_dict, start=0):
        data['scenario'] = scenario_str[index]
    all_den_df = pd.concat(street_dict)

    sns.violinplot(all_den_df, x='scenario', y='density', ax=ax, hue="scenario", cut=0)
    ax.set_ylabel("")
    ax.axhline(0.16, alpha = 1, linestyle = "-", color = "red", label="Density limit to keep distance of 1m")
    # make sure label does not overlap data --> might need to change limits if running a different model configuration
    if(i == 0):
        ax.set_ylim(bottom=None, top=0.3)
    

# ---------------------------- MAIN --------------------------------
ids = ['2000_agents', '4000_agents', '10000_agents']
sns.set()
f, axs = plt.subplots(1,3,sharey=False, figsize=(12, 4))

for index, i in enumerate(ids, start=0):
    target_folder = "Experiment/output/" + i
    zero_ows_dict_path = "%s/averages/zero_ows_dict.csv" % target_folder
    four_ows_dict_path = "%s/averages/four_ows_dict.csv" % target_folder
    eight_ows_dict_path = "%s/averages/eight_ows_dict.csv" % target_folder
    ten_ows_dict_path = "%s/averages/ten_ows_dict.csv" % target_folder
    zero_ows_files = list()
    four_ows_files = list()
    eight_ows_files = list()
    ten_ows_files = list()
    for (dirpath, dirnames, filenames) in os.walk("Experiment/output/"):
        for file in filenames:
            if file.startswith("edges_" + str(index)):
                if file.endswith(".gpkg"):
                    if dirpath.startswith("Experiment/output/0_ows"):
                        zero_ows_files += [os.path.join(dirpath, file)]
                    if dirpath.startswith("Experiment/output/4_ows"):
                        four_ows_files += [os.path.join(dirpath, file)]
                    if dirpath.startswith("Experiment/output/8_ows"):
                        eight_ows_files += [os.path.join(dirpath, file)]
                    if dirpath.startswith("Experiment/output/10_ows"):
                        ten_ows_files += [os.path.join(dirpath, file)]

    Path("%s/averages/" % target_folder).mkdir(parents=True, exist_ok=True)

    # no ows
    if(os.path.isfile(zero_ows_dict_path)):
        zero_ows_dict = pd.read_csv(zero_ows_dict_path)
    else:
        zero_ows_dict = sort_by_street(zero_ows_files, zero_ows_dict_path)
    # 4 ows compliance
    if(os.path.isfile(four_ows_dict_path)):
        four_ows_dict = pd.read_csv(four_ows_dict_path)
    else:
        four_ows_dict = sort_by_street(four_ows_files, four_ows_dict_path)
    # 8 ows compliance
    if(os.path.isfile(eight_ows_dict_path)):
        eight_ows_dict = pd.read_csv(eight_ows_dict_path)
    else:
        eight_ows_dict = sort_by_street(eight_ows_files, eight_ows_dict_path)
    # 10 ows compliance
    if(os.path.isfile(ten_ows_dict_path)):
        ten_ows_dict = pd.read_csv(ten_ows_dict_path)
    else:
        ten_ows_dict = sort_by_street(ten_ows_files, ten_ows_dict_path)

    # plot violins
    plot_boxplots([zero_ows_dict,four_ows_dict,eight_ows_dict,ten_ows_dict], ["0", "4", "8", "10"], axs[index], index)

# Plot labeling and styling
plt.xlabel("Scenario")
axs[0].set_title('2000 agents')
axs[1].set_title('4000 agents')
axs[2].set_title('10000 agents')
axs[0].set_xlabel('Number of interventions')
axs[1].set_xlabel('Number of interventions')
axs[2].set_xlabel('Number of interventions')
axs[0].legend(loc='best')
axs[0].set_ylabel("Pedestrian density in people / m^2") # hide tick and tick label of the big axis
f.tight_layout()

# Save plot to file and show
Path("Experiment/output/boxplot/").mkdir(parents=True, exist_ok=True)
plt.savefig("Experiment/output/boxplot/violin_plots.png", bbox_inches='tight')
plt.savefig("Experiment/output/boxplot/violin_plots.pdf", bbox_inches='tight')
plt.show()
print("Script completed.")