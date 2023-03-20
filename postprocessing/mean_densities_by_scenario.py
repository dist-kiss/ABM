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

def plot_distributions(street_dict, scenario_str, seed):
    density_stats = {}
    for key in street_dict:
        df = pd.DataFrame(street_dict[key])
        densities = []
        for x in df.properties:
            densities.append(x['density'])
        density_stats[str(key)] = densities
        # print(json.dumps(density_stats,
        #     sort_keys=True, indent=4))
    
    # rndm_keys = random.sample(range(0, len(street_dict)), 9)
    random.seed(seed)
    rndm_keys = random.sample(list(density_stats), 9)
    values = [density_stats[k] for k in rndm_keys]
    bins=[0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
    bins2=[0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.325, 0.35, 0.375, 0.4, 0.425, 0.45, 0.475, 0.5]
    bins3=np.arange(0,0.5,0.01)
    f, axs = plt.subplots(3,3,figsize=(10, 10))
    for index, value in enumerate(values):
        axs[(index+1)%3, int(index/3)].hist(value, bins=bins3)
        axs[(index+1)%3, int(index/3)].set_title('Street ID: ' + str(rndm_keys[index]))
        axs[(index+1)%3, int(index/3)].set_ylim([0, 600])
        f.suptitle('%s - Histograms of all densities (nine random streets)' % scenario_str, fontsize=16)
    plt.show()

def plot_overall_distributions(street_dict, scenario_str):
    f, axs = plt.subplots(3,1,figsize=(10, 10))
    for index, data in enumerate(street_dict, start=1):
        densities = []
        for key in data:
            df = pd.DataFrame(data[key])
            for x in df.properties:
                densities.append(x['density'])

        bins3=np.arange(0,0.3,0.005)
        # axs[(index*2)-2].hist(densities, bins=bins3)
        # axs[(index*2)-1].hist(densities, density=True, bins=bins3)
        # axs[(index*2)-2].set_title(scenario_str[index-1])
        # axs[(index*2)-2].set_ylim([0, 18000])
        # # axs[(index*2)-1].set_ylim([0, 18000])

        axs[index-1].hist(densities, density=True, alpha = 0.65, bins=bins3)
        axs[index-1].set_title(scenario_str[index-1])
        axs[index-1].set_xlim(0, 0.27)

        mn, mx = axs[index-1].get_xlim()
        # plt.xlim(mn, mx)
        kde_xs = np.linspace(mn, mx, 300)
        kde = st.gaussian_kde(densities)
        axs[index-1].plot(kde_xs, kde.pdf(kde_xs), label="PDF")


        # Calculate percentiles
        # quant_5, quant_25, quant_50, quant_75, quant_95 = densities.quantile(0.05), densities.quantile(0.25), densities.quantile(0.5), densities.quantile(0.75), densities.quantile(0.95)
        quant_5, quant_25, quant_50, quant_75, quant_95 = np.percentile(densities, [5, 25, 50, 75, 95])

        # [quantile, opacity, length]
        quants = [[quant_5, 0.6, 0.16], [quant_25, 0.8, 0.26], [quant_50, 1, 0.36],  [quant_75, 0.8, 0.46], [quant_95, 0.6, 0.56]]

        # Plot the lines with a loop
        for i in quants:
            axs[index-1].axvline(i[0], alpha = i[1], ymax = i[2], linestyle = ":")

        axs[index-1].text(quant_5-.005, 0.57, "5th", size = 10, alpha = 0.8)
        axs[index-1].text(quant_25-.008, 1.27, "25th", size = 11, alpha = 0.85)
        axs[index-1].text(quant_50-.008, 1.70, "50th", size = 12, alpha = 1)
        axs[index-1].text(quant_75-.008, 2.27, "75th", size = 11, alpha = 0.85)
        axs[index-1].text(quant_95+0.005, 2.77, "95th Percentile", size = 10, alpha =.8)
    f.suptitle('Histograms of crowdedness over all streets combined', fontsize=16)
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
text = "Experiment/output/1677443804"

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
plot_overall_distributions([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"])


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
# plot_maps(["%s/averages/out_no_comp.gpgk" % text,"%s/averages/out_full_comp.gpgk" % text,"%s/averages/out_cali_comp.gpgk" % text])

print("done")