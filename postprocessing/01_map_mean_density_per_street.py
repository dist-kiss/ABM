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
import seaborn as sns




def sort_by_street(input_file):
    """ Takes several spatial vector files with the same spatial features and returns a dict, that groups features by ID.
        Returns:
            Dict {
            "1":[feature1, feature 2, ...],
            "2":[feature1, feature 2, ...],
            ...
        }
    """
    dict = {}
    for file in input_file:
        shape = fiona.open(file)
        for feat in shape:
            if not feat['properties']['ID'] in dict:
                dict[feat['properties']['ID']] = []
            dict[feat['properties']['ID']].append(feat)
    return dict


def calc_stats_by_street(street_dict):
    """ Takes dict with grouped features by ID and produces dict with mean, median and std for each ID.
        Returns:
            Dict {
            "1_mean": 0.12,
            "1_median": 0.14,
            "1_std": 0.02,
            "2_mean": 0.16,
            "2_median": 0.17,
            "2_std": 0.01,
            ...
        }
    """
    density_stats = {}
    for key in street_dict:
        df = pd.DataFrame(street_dict[key])
        densities = []
        for x in df.properties:
            densities.append(x['density'])
        quant_50, quant_95 = np.percentile(densities, [50, 95])
        density_stats[str(key) + "_mean"] = mean(densities)
        density_stats[str(key) + "_median"] = median(densities)
        density_stats[str(key) + "_std"] = stdev(densities)
        density_stats[str(key) + "_95th_perc"] = quant_95
    return density_stats


def write_to_gpk(outfile, infile, density_stats):
    """ Takes dict with mean, median and std of max_density for each ID and geopackage file with same IDs
        and produces new geopackage file with attributes mean, median and std of max_density for all features.
    """

    gdf = geopandas.read_file(infile)
    col_list = ['ID', 'one_way', 'one_way_reversed', 'mm_len', 'geometry']
    gdf = gdf[col_list]
    means = []
    medians = []
    stds = []
    perc95s = []
    for row in gdf["ID"]:
            means.append(density_stats[str(row) + "_mean"])
            medians.append(density_stats[str(row) + "_median"])
            stds.append(density_stats[str(row) + "_std"])      
            perc95s.append(density_stats[str(row) + "_95th_perc"])      
    gdf["mean_density"] = means
    gdf["median_density"] = medians
    gdf["std_density"] = stds
    gdf["95th_percentile"] = perc95s
    gdf.to_file(outfile, driver="GPKG")
    return max(gdf['mean_density']), max(gdf['median_density']), max(gdf['std_density']), max(gdf['95th_percentile']), min(gdf['mean_density']), min(gdf['median_density']), min(gdf['std_density']), min(gdf['95th_percentile'])

def plot_maps(prefix, file_names, base_path):
    # get max values for each relevant column to set axis limits
    ymax_mean = 0
    ymax_median = 0
    ymax_std = 0
    ymax_95th = 0
    for file_name in file_names:
        file_path = base_path + prefix + file_name + ".gpgk"
        gdf = geopandas.read_file(file_path)
        max_gdf = gdf.max(numeric_only=True)
        ymax_mean = max(ymax_mean,max_gdf.mean_density)
        ymax_median = max(ymax_median,max_gdf.median_density)
        ymax_std = max(ymax_std,max_gdf.std_density)
        ymax_95th = max(ymax_95th,max_gdf['95th_percentile'])

    sns.set()
    f, ax = plt.subplots(figsize=(6, 4))
    # get reversed magma colormap for the plots
    reversed_magma = plt.colormaps['magma'].reversed()

    # Create single map of mean density per street in the base scenario (no interventions)
    base_scenario_path = base_path + prefix + file_names[0] + ".gpgk"
    gdf = geopandas.read_file(base_scenario_path)
    gdf.plot(ax=ax, column='mean_density', legend=True, legend_kwds={"label": "people / $m^2$", "orientation": "vertical"}, cmap=reversed_magma, vmin=0, vmax=ymax_mean, linewidth=3)
    ax.set_xticks([])
    ax.set_yticks([])
    # save to file and show map 
    Path("%s/differences/" % base_path).mkdir(parents=True, exist_ok=True)
    plt.savefig("%s/differences/" % base_path + "base_map" + ".pdf", bbox_inches='tight')
    plt.savefig("%s/differences/" % base_path + "base_map" + ".png", bbox_inches='tight')
    plt.show()

    # Create maps of for all relevant statistics (see cols) of densities per street for all scenarios and plot as matrix
    f, axs = plt.subplots(len(file_names),4,figsize=(15, 10))
    cols = ['{}'.format(col) for col in ['Mean', 'Median', 'Standard deviation', '95th percentile']]
    rows = ['{}'.format(row) for row in file_names]
    for ax, col in zip(axs[0], cols):
        ax.set_title(col)

    for ax, row in zip(axs[:,0], rows):
        ax.set_ylabel(row, rotation=90, size='large')

    for index, file_name in enumerate(file_names):
        file_path = base_path + prefix + file_name + ".gpgk"
        gdf = geopandas.read_file(file_path)
        gdf.plot(ax=axs[index, 0], column='mean_density', legend=True, cmap=reversed_magma, vmin=0, vmax=ymax_mean)
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])

        gdf.plot(ax=axs[index, 1], column='median_density', legend=True, cmap=reversed_magma, vmin=0, vmax=ymax_median)
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])

        gdf.plot(ax=axs[index, 2], column='std_density', legend=True, cmap=reversed_magma, vmin=0, vmax=ymax_std)
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])

        gdf.plot(ax=axs[index, 3], column='95th_percentile', legend=True, cmap=reversed_magma, vmin=0, vmax=ymax_95th)
        axs[index, 3].set_xticks([])
        axs[index, 3].set_yticks([])

    # save to file and show
    plt.savefig("%s/averages/map_densities.pdf" % base_path, bbox_inches='tight')
    plt.savefig("%s/averages/map_densities.png" % base_path, bbox_inches='tight')
    plt.show()


# ---------------------------- MAIN --------------------------------
folder_name = "compliance_study"
base_path = "Experiment/output/" + folder_name 
outnames = ['no_interv', 'full_comp', 'cali_comp']

no_comp_files = list()
full_comp_files = list()
cali_comp_files = list()
max_density_files = list()
for (dirpath, dirnames, filenames) in os.walk(base_path):
    for file in filenames:
        if file.startswith("edges_"):
            if file.endswith(".gpkg"):
                if file.startswith("edges_0"):
                    no_comp_files += [os.path.join(dirpath, file)]
                elif file.startswith("edges_1"):
                    full_comp_files += [os.path.join(dirpath, file)]
                elif file.startswith("edges_2"):
                    cali_comp_files += [os.path.join(dirpath, file)]
        elif file.startswith("max_density_"):
            if file.endswith(".gpkg"):
                max_density_files += [os.path.join(dirpath, file)]

Path("%s/averages/" % base_path).mkdir(parents=True, exist_ok=True)
# TODO: Fix sort bystreets to csv or fix calcstats by streets, by using only the relevant field!
# no compliance
no_comp_dict = sort_by_street(no_comp_files)
no_comp_stats = calc_stats_by_street(no_comp_dict)
no_max_mean, no_max_median, no_max_std, no_max_95, no_min_mean, no_min_median, no_min_std, no_min_95 = write_to_gpk(base_path + "/averages/stats_by_street_" + outnames[0] + ".gpgk", max_density_files[0], no_comp_stats)

# full compliance
full_comp_dict = sort_by_street(full_comp_files)
full_comp_stats = calc_stats_by_street(full_comp_dict)
full_max_mean, full_max_median, full_max_std, full_max_95, full_min_mean, full_min_median, full_min_std, full_min_95 = write_to_gpk(base_path + "/averages/stats_by_street_" + outnames[1] + ".gpgk", max_density_files[0], full_comp_stats)

# calibrated compliance
if len(cali_comp_files) > 0:
    cali_comp_dict = sort_by_street(cali_comp_files)
    cali_comp_stats = calc_stats_by_street(cali_comp_dict)
    cali_max_mean, cali_max_median, cali_max_std, cali_max_95, cali_min_mean, cali_min_median, cali_min_std, cali_min_95 = write_to_gpk(base_path + "/averages/stats_by_street_" + outnames[2] + ".gpgk", max_density_files[0], cali_comp_stats)

# plot maps with statistics
plot_maps("/averages/stats_by_street_", outnames, base_path)
print("Script completed.")