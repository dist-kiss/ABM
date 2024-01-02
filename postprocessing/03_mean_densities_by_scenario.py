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



def sort_by_street(input_file, out_name):
    """ Takes several spatial vector files with the same spatial features and returns a dict, that groups features by ID.
        Returns:
            Dict {
            "1":[feature1, feature 2, ...],
            "2":[feature1, feature 2, ...],
            ...
        }
    """


    # dict = {}
    density_list = []
    for file in input_file:
        shape = fiona.open(file)
        for feat in shape:
            density_list.append([feat['properties']['ID'], feat['properties']['density']])
            # if not feat['properties']['ID'] in dict:
            #     dict[feat['properties']['ID']] = []
            # Double check if streets are the same geometries
            # else:
            #     for f in dict[feat['properties']['ID']]:
            #         is_same_length = f['properties']['mm_len'] == feat['properties']['mm_len']
            #         if(not is_same_length):
            #             print(is_same_length)
            # dict[feat['properties']['ID']].append(feat)
    all_dens = pd.DataFrame(density_list, columns=['ID','density'])
    # .set_index(['ID'])
    all_dens.to_csv(out_name, index=False)
    # json.dump(dict, open(out_name,'w'))
    return all_dens



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

def plot_overall_distributions(street_dict, scenario_str, xmax=1,ymax=125000):

    # all_dens = []
    # for index, data in enumerate(street_dict, start=1):
    #     densities = []
    #     for key in data:
    #         df = pd.DataFrame(data[key])
    #         for x in df.properties:
    #             densities.append(x['density'])
    #     all_dens.append(densities)
    # bins=np.histogram(np.hstack((street_dict[0]['density'],street_dict[1]['density'], street_dict[2]['density'])), bins=40)[1]
    bins=np.arange(0,1,0.01)

    
    f, ax = plt.subplots()
    all_dens = []
    # f, axs = plt.subplots(3,1,figsize=(10, 10), sharex=True)
    for index, data in enumerate(street_dict, start=1):
        densities = data['density']
        all_dens.append(densities)
        # densities = []
        # for key in data:
        #     df = pd.DataFrame(data[key])
        #     for x in df.properties:
        #         densities.append(x['density'])
        # axs[(index*2)-2].hist(densities, bins=bins3)
        # axs[(index*2)-1].hist(densities, density=True, bins=bins3)
        # axs[(index*2)-2].set_title(scenario_str[index-1])
        # axs[(index*2)-2].set_ylim([0, 18000])
        # # axs[(index*2)-1].set_ylim([0, 18000])
        col = next(ax._get_lines.prop_cycler)['color']

        # ax.hist(densities, bins, alpha=0.5, label=str(scenario_str[index-1]), color=col, log=True)
        n,x,_ = ax.hist(densities, bins, label=str(scenario_str[index-1]), color=col, histtype=u'step', alpha=0.5)
        # bin_centers = 0.5*(x[1:]+x[:-1])
        # ax.plot(bin_centers,n, color=col) ## using bin_centers rather than edges
        # plt.pyplot.hist(y, bins, alpha=0.5, label='y')
        # axs[index-1].hist(densities, density=True, alpha = 0.65, bins=bins3)
        # axs[index-1].set_title(scenario_str[index-1])
        # axs[index-1].set_xlim(left=0)
        # axs[index-1].set_ylim(0,30)

        # mn, mx = axs[index-1].get_xlim()
        # # plt.xlim(mn, mx)
        # kde_xs = np.linspace(mn, mx, 400)
        # kde = st.gaussian_kde(densities)
        # axs[index-1].plot(kde_xs, kde.pdf(kde_xs), label="PDF")


        # Calculate percentiles
        quant_5, quant_25, quant_50, quant_75, quant_95 = densities.quantile(0.05), densities.quantile(0.25), densities.quantile(0.5), densities.quantile(0.75), densities.quantile(0.95)
        quant_5, quant_25, quant_50, quant_75, quant_95 = np.percentile(densities, [5, 25, 50, 75, 95])

        # # [quantile, opacity, length]
        quants = [[quant_5, 0.6, 0.16], [quant_25, 0.8, 0.26], [quant_50, 1, 0.36],  [quant_75, 0.8, 0.46], [quant_95, 0.6, 0.56]]

        # # Plot the lines with a loop
        # for i in quants:

        # ax.axvline(quant_95, alpha = 0.6, ymax = 0.56, linestyle = ":", color = col, label=str(scenario_str[index-1]) + " 95th %ile")
    ax.axvline(0.16, alpha = 1, linestyle = "-", color = "red", label="Density limit 1m distance keeping")

        # plt.text(quant_5-.005, 0.57, "5th", size = 10, alpha = 0.8)
        # plt.text(quant_25-.008, 1.27, "25th", size = 11, alpha = 0.85)
        # plt.text(quant_50-.008, 1.70, "50th", size = 12, alpha = 0.85)
        # plt.text(quant_75-.008, 2.27, "75th", size = 11, alpha = 0.85)
    # ax.text(quant_95+0.005, 2.77, "95th Percentile", size = 10, alpha =.8)
    plt.legend(loc='upper right')
    f.suptitle('Crowdedness on streets at 0.2 Hz', fontsize=16)
    plt.xlim(0, xmax)
    plt.ylim(0, ymax)
    plt.ylabel("Frequency")
    plt.xlabel("Crowdedness in people / m^2")
    plt.savefig("%s/averages/fixed_x_y_bins_0_005_outline_hists.pdf" % text, bbox_inches='tight')
    plt.savefig("%s/averages/overlay_hists.png" % text, bbox_inches='tight')
    plt.show()

    # f = plt.figure()
    # plt.hist(all_dens, bins, label=scenario_str, density=True, alpha=0.9, log=True)
    # plt.axvline(0.16, alpha = 1, linestyle = "-", color = "red")
    # plt.legend(loc='upper right')
    # plt.savefig("%s/averages/adjacent_hists.pdf" % text, bbox_inches='tight')
    # plt.savefig("%s/averages/adjacent_hists.png" % text, bbox_inches='tight')
    # plt.show()


def plot_boxplots(street_dict, scenario_str, xmax=1,ymax=125000):
    Path("%s/boxplots/" % text).mkdir(parents=True, exist_ok=True)
    sns.set()
    f, ax = plt.subplots()
    # all_dens = []
    for index, data in enumerate(street_dict, start=0):
        data['scenario'] = scenario_str[index]
    all_den_df = pd.concat(street_dict)
    # for index, data in enumerate(street_dict, start=1):
    #     data['scenario'] = scenario_str[index]
    #     densities = data['density']
    #     all_dens.append(densities)
    #     col = next(ax._get_lines.prop_cycler)['color']
        # ax.boxplot(densities)
    sns.violinplot(all_den_df, x='scenario', y='density', ax=ax, log_scale=True)
    # ax.axhline(0.16, alpha = 1, linestyle = "-", color = "red", label="Limit for keeping distance of 1m")
    plt.ylabel("Crowdedness in people / m^2")
    plt.xlabel("Scenario")
    # plt.ylim(0,1.1)
    plt.legend(loc='best')
    plt.savefig("%s/boxplots/violin_plots.png" % text, bbox_inches='tight')
    plt.show()
    # sns.boxplot(all_den_df, x='scenario', y='density', ax=ax)
    # plt.show()
    # plt.legend(loc='upper right')
    # f.suptitle('Crowdedness on streets at 0.2 Hz', fontsize=16)
    # plt.xlim(0, xmax)
    # plt.ylim(0, ymax)
    # plt.xlabel("Frequency")
    # plt.ylabel("Crowdedness in people / m^2")
    # plt.savefig("%s/averages/fixed_x_y_bins_0_005_outline_hists.pdf" % text, bbox_inches='tight')
    # plt.savefig("%s/averages/overlay_hists.png" % text, bbox_inches='tight')
    # plt.show()


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



# ---------------------------- MAIN --------------------------------
# text = input("Please enter file path: ")
# ids = ['1683636344', '1683637657', '1684934235']
# ids = ['1685014788', '1685017497']
ids = ['1685019490']
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

    Path("%s/averages/" % text).mkdir(parents=True, exist_ok=True)

    # no_comp_dict_path = "%s/averages/no_comp_dict.csv" % text
    # no compliance
    if(os.path.isfile(no_comp_dict_path)):
        no_comp_dict = pd.read_csv(no_comp_dict_path)
    else:
        no_comp_dict = sort_by_street(no_comp_files, no_comp_dict_path)
    # full_comp_dict_path = "%s/averages/full_comp_dict.csv" % text
    # full compliance
    if(os.path.isfile(full_comp_dict_path)):
        full_comp_dict = pd.read_csv(full_comp_dict_path)
    else:
        full_comp_dict = sort_by_street(full_comp_files, full_comp_dict_path)
    # cali_comp_dict_path = "%s/averages/cali_comp_dict.csv" % text
    # calibrated compliance
    # if(os.path.isfile(cali_comp_dict_path)):
    #     cali_comp_dict = pd.read_csv(cali_comp_dict_path)
    # else:
    #     cali_comp_dict = sort_by_street(cali_comp_files, cali_comp_dict_path)
    # plot_overall_distributions([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"], xmax=0.9, ymax=70000)
    # plot_overall_distributions([no_comp_dict,full_comp_dict], ["4 OWS", "10 OWS"], xmax=0.9, ymax=70000)
    # plot_boxplots([no_comp_dict,full_comp_dict,cali_comp_dict], ["4 OWS", "8 OWS","10 OWS"], xmax=0.9, ymax=70000)
    plot_boxplots([no_comp_dict,full_comp_dict], ["4 OWS", "10 OWS"], xmax=0.9, ymax=70000)
    # plot_boxplots([no_comp_dict,full_comp_dict,cali_comp_dict], ["No interventions", "Full compliance", "Calibrated Compliance"], i)
print("done")