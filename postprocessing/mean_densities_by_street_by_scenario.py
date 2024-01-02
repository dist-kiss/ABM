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
        mean_density = mean(densities)
        median_density = median(densities)
        std_density = stdev(densities)
        density_stats[str(key) + "_mean"] = mean_density
        density_stats[str(key) + "_median"] = median_density
        density_stats[str(key) + "_std"] = std_density
        # print(json.dumps(density_stats,
        #     sort_keys=True, indent=4))
    return density_stats

def plot_distributions(street_dicts, scenario_strs, seed):
    random.seed(seed)
    # rndm_keys = random.sample(list(street_dicts[0]), 5)
    rndm_keys = list([35,42,46,52,58])
    bins3=np.arange(0,0.5,0.01)
    # f, axs = plt.subplots(3,5,figsize=(10, 10))
    f = plt.figure(constrained_layout=True)
    f.suptitle('Histograms of all densities (nine random streets)')
    subfigs = f.subfigures(nrows=3, ncols=1)
    
    all_dens = []
    for row, subfig in enumerate(subfigs):
        density_stats = {}
        for key in street_dicts[row]:
            df = pd.DataFrame(street_dicts[row][key])
            densities = []
            for x in df.properties:
                densities.append(x['density'])
            density_stats[key] = densities    
        values = [density_stats[k] for k in rndm_keys]
        all_dens.append(values)

    for row, subfig in enumerate(subfigs):
        subfig.suptitle(scenario_strs[row])

        # create 1x3 subplots per subfig
        axs = subfig.subplots(nrows=1, ncols=5)
        # oragnize data:
        # density_stats = {}
        # for key in street_dicts[row]:
        #     df = pd.DataFrame(street_dicts[row][key])
        #     densities = []
        #     for x in df.properties:
        #         densities.append(x['density'])
        #     density_stats[key] = densities    
        # values = [density_stats[k] for k in rndm_keys]
        for col, ax in enumerate(axs):
            bins = np.histogram(np.hstack((all_dens[0][col],all_dens[1][col], all_dens[2][col])), bins=20)[1]
            ax.hist(all_dens[row][col], bins=bins, density=True, log=True)
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
    avgs = []
    medians = []
    stds = []
    for row in gdf["ID"]:
            avgs.append(density_stats[str(row) + "_mean"])
            medians.append(density_stats[str(row) + "_median"])
            stds.append(density_stats[str(row) + "_std"])      
    gdf["avg_max_density"] = avgs
    gdf["median_max_density"] = medians
    gdf["std_max_density"] = stds
    gdf.to_file(outfile, driver="GPKG")

# text = input("Please enter file path: ")
text = "Experiment/output/1683635583"

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

Path("%s/averages/" % text).mkdir(parents=True, exist_ok=True)
# no compliance
no_comp_dict = sort_by_street(no_comp_files)
# plot_distributions(no_comp_dict, "No interventions", 42)
# no_comp_stats = calc_stats_by_street(no_comp_dict)
# write_to_gpk("%s/averages/out_no_comp.gpgk" % text, no_comp_files[0], no_comp_stats)
# full compliance
full_comp_dict = sort_by_street(full_comp_files)
# plot_distributions(full_comp_dict, "Full Compliance", 42)
# full_comp_stats = calc_stats_by_street(full_comp_dict)
# write_to_gpk("%s/averages/out_full_comp.gpgk" % text, full_comp_files[0], full_comp_stats)
# calibrated compliance
cali_comp_dict = sort_by_street(cali_comp_files)
# plot_distributions(cali_comp_dict, "Calibrated Compliance", 42)
# cali_comp_stats = calc_stats_by_street(cali_comp_dict)
# write_to_gpk("%s/averages/out_cali_comp.gpgk" % text, cali_comp_files[0], cali_comp_stats)
plot_distributions([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"], 42)


def plot_maps(file_names):
    f, axs = plt.subplots(len(file_names),3,figsize=(10, 10))
    # getting the original colormap using cm.get_cmap() function
    orig_map=plt.cm.get_cmap('magma')    
    # reversing the original colormap using reversed() function
    reversed_map = orig_map.reversed()
    cols = ['{}'.format(col) for col in ['Mean', 'Median', 'Standard deviation']]
    rows = ['{}'.format(row) for row in ['No interventions', 'Full compliance', 'Calibrated compliance']]
    for ax, col in zip(axs[0], cols):
        ax.set_title(col)

    for ax, row in zip(axs[:,0], rows):
        ax.set_ylabel(row, rotation=90, size='large')

    for index, file in enumerate(file_names):
        gdf = geopandas.read_file(file)
        gdf.plot(ax=axs[index, 0], column='avg_max_density', legend=True, cmap=reversed_map, vmin=0, vmax=0.6)
        axs[index, 0].legend()
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])

        gdf.plot(ax=axs[index, 1], column='median_max_density', legend=True, cmap=reversed_map, vmin=0, vmax=0.6)
        axs[index, 1].legend()
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])

        gdf.plot(ax=axs[index, 2], column='std_max_density', legend=True, cmap=reversed_map, vmin=0, vmax=0.1)
        axs[index, 2].legend()
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])
    plt.show()

print("done")