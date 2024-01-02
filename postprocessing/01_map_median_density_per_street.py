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
            # Double check if streets are the same geometries
            # else:
            #     for f in dict[feat['properties']['ID']]:
            #         is_same_length = f['properties']['mm_len'] == feat['properties']['mm_len']
            #         if(not is_same_length):
            #             print(is_same_length)
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
        # print(json.dumps(density_stats,
        #     sort_keys=True, indent=4))
    return density_stats

def plot_distributions(street_dicts, scenario_strs, seed):
    random.seed(seed)
    rndm_keys = random.sample(list(street_dicts[0]), 5)
    bins3=np.arange(0,0.5,0.01)
    # f, axs = plt.subplots(3,5,figsize=(10, 10))
    f = plt.figure(constrained_layout=True)
    f.suptitle('Histograms of all densities (nine random streets)')
    subfigs = f.subfigures(nrows=3, ncols=1)
    for row, subfig in enumerate(subfigs):
        subfig.suptitle(scenario_strs[row])

        # create 1x3 subplots per subfig
        axs = subfig.subplots(nrows=1, ncols=5)
        # oragnize data:
        density_stats = {}
        for key in street_dicts[row]:
            df = pd.DataFrame(street_dicts[row][key])
            densities = []
            for x in df.properties:
                densities.append(x['density'])
            density_stats[key] = densities    
        values = [density_stats[k] for k in rndm_keys]

        for col, ax in enumerate(axs):
            ax.hist(values[col], bins=bins3, density=True)
            ax.set_title('Street ID: ' + str(rndm_keys[col]))
            # ax.set_ylim([0, 600])
            # ax.set_title(f'Plot title {col}')
    f.suptitle(f'Histograms of all densities ({len(rndm_keys)} random streets)', fontsize=16)
    plt.show()


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

def plot_maps(file_names, outnames):
    ymax_mean = 0
    ymax_median = 0
    ymax_std = 0
    ymax_95th = 0
    for file in file_names:
        gdf = geopandas.read_file(file)
        max_gdf = gdf.max()
        ymax_mean = max(ymax_mean,max_gdf.mean_density)
        ymax_median = max(ymax_median,max_gdf.median_density)
        ymax_std = max(ymax_std,max_gdf.std_density)
        ymax_95th = max(ymax_95th,max_gdf['95th_percentile'])

    sns.set()
    f, ax = plt.subplots(figsize=(6, 4))
    # getting the original colormap using cm.get_cmap() function
    orig_map=plt.cm.get_cmap('magma')    
    # reversing the original colormap using reversed() function
    reversed_map = orig_map.reversed()
    
    gdf = geopandas.read_file(file_names[0])
    gdf.plot(ax=ax, column='mean_density', legend=True, legend_kwds={"label": "people / $m^2$", "orientation": "vertical"}, cmap=reversed_map, vmin=0, vmax=ymax_mean, linewidth=3)
    # ax.set_ylabel("Crowdedness in people / $m^2$")
    ax.set_xticks([])
    ax.set_yticks([])

    plt.savefig("%s/differences/" % text + "base_map" + ".pdf", bbox_inches='tight')
    plt.show()

    f, axs = plt.subplots(len(file_names),4,figsize=(15, 10))
    cols = ['{}'.format(col) for col in ['Mean', 'Median', 'Standard deviation', '95th percentile']]
    rows = ['{}'.format(row) for row in outnames]
    for ax, col in zip(axs[0], cols):
        ax.set_title(col)

    for ax, row in zip(axs[:,0], rows):
        ax.set_ylabel(row, rotation=90, size='large')

    for index, file in enumerate(file_names):
        gdf = geopandas.read_file(file)
        gdf.plot(ax=axs[index, 0], column='mean_density', legend=True, cmap=reversed_map, vmin=0, vmax=ymax_mean)
        # axs[index, 0].legend()
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])

        gdf.plot(ax=axs[index, 1], column='median_density', legend=True, cmap=reversed_map, vmin=0, vmax=ymax_median)
        # axs[index, 1].legend()
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])

        gdf.plot(ax=axs[index, 2], column='std_density', legend=True, cmap=reversed_map, vmin=0, vmax=ymax_std)
        # axs[index, 2].legend()
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])

        gdf.plot(ax=axs[index, 3], column='95th_percentile', legend=True, cmap=reversed_map, vmin=0, vmax=ymax_95th)
        # axs[index, 3].legend()
        axs[index, 3].set_xticks([])
        axs[index, 3].set_yticks([])
    plt.savefig("%s/averages/map_densities.pdf" % text, bbox_inches='tight')
    plt.savefig("%s/averages/map_densities.png" % text, bbox_inches='tight')
    # plt.show()

# text = input("Please enter file path: ")
text = "Experiment/output/1683637657"
outnames = ['stats_by_street_no_interv', 'stats_by_street_full_comp', 'stats_by_street_cali_comp']
# outnames = ['4_ows', '10_ows']

no_comp_files = list()
full_comp_files = list()
cali_comp_files = list()
max_density_files = list()
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
        elif file.startswith("max_density_"):
            if file.endswith(".gpkg"):
                max_density_files += [os.path.join(dirpath, file)]

Path("%s/averages/" % text).mkdir(parents=True, exist_ok=True)
# no compliance
no_comp_dict = sort_by_street(no_comp_files)
no_comp_stats = calc_stats_by_street(no_comp_dict)
no_max_mean, no_max_median, no_max_std, no_max_95, no_min_mean, no_min_median, no_min_std, no_min_95 = write_to_gpk(text + "/averages/stats_by_street_" + outnames[0] + ".gpgk", max_density_files[0], no_comp_stats)
# full compliance
full_comp_dict = sort_by_street(full_comp_files)
full_comp_stats = calc_stats_by_street(full_comp_dict)
full_max_mean, full_max_median, full_max_std, full_max_95, full_min_mean, full_min_median, full_min_std, full_min_95 = write_to_gpk(text + "/averages/stats_by_street_" + outnames[1] + ".gpgk", max_density_files[0], full_comp_stats)
# calibrated compliance
if len(cali_comp_files) > 0:
    cali_comp_dict = sort_by_street(cali_comp_files)
    cali_comp_stats = calc_stats_by_street(cali_comp_dict)
    cali_max_mean, cali_max_median, cali_max_std, cali_max_95, cali_min_mean, cali_min_median, cali_min_std, cali_min_95 = write_to_gpk(text + "/averages/stats_by_street_" + outnames[2] + ".gpgk", max_density_files[0], cali_comp_stats)

# max_mean = max(full_max_mean, no_max_mean, cali_max_mean)
# max_median = max(full_max_median, no_max_median, cali_max_median)
# max_std = max(full_max_std, no_max_std, cali_max_std)
# max_95 = max(full_max_95, no_max_95, cali_max_95)
# min_mean = min(full_min_mean, no_min_mean, cali_min_mean)
# min_median = min(full_min_median, no_min_median, cali_min_median)
# min_std = min(full_min_std, no_min_std, cali_min_std)
# min_95 = min(full_min_95, no_min_95, cali_min_95)

plot_maps([text + "/averages/stats_by_street_" + outnames[0] + ".gpgk", text + "/averages/stats_by_street_" + outnames[1] + ".gpgk" , text + "/averages/stats_by_street_" + outnames[2] + ".gpgk"], outnames)
# plot_maps([text + "/averages/stats_by_street_" + outnames[0] + ".gpgk", text + "/averages/stats_by_street_" + outnames[1] + ".gpgk"], outnames)


print("done")