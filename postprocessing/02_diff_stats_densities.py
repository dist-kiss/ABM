import fiona
import json
import os
from pathlib import Path
import pandas as pd
from statistics import mean, stdev, median
import json
import geopandas
import matplotlib.pyplot as plt 
import seaborn as sns


def create_dict_from_files(base, compare, outfile):
    base_gdf = geopandas.read_file(base)
    base_gdf['diff_mean'] = None
    base_gdf['diff_median'] = None
    base_gdf['diff_std'] = None
    base_gdf['diff_95th_percentile'] = None

    compare_gdf = geopandas.read_file(compare)
    # for row in compare_gdf:
    base_gdf['diff_mean'] = base_gdf['mean_density'].subtract(compare_gdf['mean_density'])
    base_gdf['diff_median'] = base_gdf['median_density'].subtract(compare_gdf['median_density'])
    base_gdf['diff_std'] = base_gdf['std_density'].subtract(compare_gdf['std_density'])
    base_gdf['diff_95th_percentile'] = base_gdf['95th_percentile'].subtract(compare_gdf['95th_percentile'])
    base_gdf.to_file(outfile, driver="GPKG")

def calc_diffs(input_dict):
    diff_dict = {}
    for key in input_dict:
        diff = input_dict[key][0] - input_dict[key][1]
        diff_dict[str(key)] = diff
        print(json.dumps(diff_dict,
            sort_keys=True, indent=4))
    return diff_dict

def write_to_gpk(outfile, infile, dicts):
    gdf = geopandas.read_file(infile)
    diffs_mean = []
    diffs_median = []
    diffs_std = []
    for row in gdf["ID"]:
            diffs_mean.append(dicts[0][str(row)])
            diffs_median.append(dicts[1][str(row)])
            diffs_std.append(dicts[2][str(row)])
    gdf["diff_mean"] = diffs_mean
    gdf["diff_median"] = diffs_median
    gdf["diff_std"] = diffs_std
    gdf.to_file(outfile, driver="GPKG")


# text = input("Please enter file path: ")
text = "Experiment/output/1683637657"
# list_of_files = ["%s/averages/stats_by_street_4_ows" % text, "%s/averages/stats_by_street_8_ows" % text,"%s/averages/stats_by_street_10_ows" % text]
list_of_files = ["%s/averages/stats_by_street_no_interv.gpgk" % text,"%s/averages/stats_by_street_full_comp.gpgk" % text,"%s/averages/stats_by_street_cali_comp.gpgk" % text]

Path("%s/differences/" % text).mkdir(parents=True, exist_ok=True)
create_dict_from_files(base="%s/averages/stats_by_street_cali_comp.gpgk" % text, compare="%s/averages/stats_by_street_full_comp.gpgk" % text,outfile="%s/differences/cali_full" % text)
create_dict_from_files(base="%s/averages/stats_by_street_cali_comp.gpgk" % text, compare="%s/averages/stats_by_street_no_interv.gpgk" % text,outfile="%s/differences/cali_no" % text)
# no compliance

def plot_maps(file_names):
    ymax_mean = 0
    ymax_median = 0
    ymax_std = 0
    ymax_95th = 0
    for file in file_names:
        gdf = geopandas.read_file(file)
        max_gdf = gdf.max()
        min_gdf = gdf.min()
        ymax_mean = max(ymax_mean,max_gdf.diff_mean,abs(min_gdf.diff_mean))
        ymax_median = max(ymax_median,max_gdf.diff_median,abs(min_gdf.diff_median))
        ymax_std = max(ymax_std,max_gdf.diff_std,abs(min_gdf.diff_std))
        ymax_95th = max(ymax_95th,max_gdf['diff_95th_percentile'],abs(min_gdf['diff_95th_percentile']))


    f, axs = plt.subplots(len(file_names),4,figsize=(15, 10))
    viridis = plt.cm.get_cmap('PiYG', 256)
    cols = ['{}'.format(col) for col in ['Mean', 'Median', 'Standard deviation', '95th']]
    rows = ['{}'.format(row) for row in ['Calibrated - Full Compliance', 'Calibrated - No Interventions']]
    for ax, col in zip(axs[0], cols):
        ax.set_title(col)

    for ax, row in zip(axs[:,0], rows):
        ax.set_ylabel(row, rotation=90, size='large')

    for index, file in enumerate(file_names):
        gdf = geopandas.read_file(file)
        gdf.plot(ax=axs[index, 0], column='diff_mean', legend=True, cmap=viridis, vmin=-ymax_mean, vmax=ymax_mean)
        # axs[index, 0].legend()
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])
        
        gdf.plot(ax=axs[index, 1], column='diff_median', legend=True, cmap=viridis, vmin=-ymax_median, vmax=ymax_median)
        # axs[index, 1].legend()
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])

        gdf.plot(ax=axs[index, 2], column='diff_std', legend=True, cmap=viridis, vmin=-ymax_std, vmax=ymax_std)
        # axs[index, 2].legend()
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])

        gdf.plot(ax=axs[index, 3], column='diff_95th_percentile', legend=True, cmap=viridis, vmin=-ymax_95th, vmax=ymax_95th)
        # axs[index, 3].legend()
        axs[index, 3].set_xticks([])
        axs[index, 3].set_yticks([])
    plt.savefig("%s/differences/map_diff_scenarios_densities.pdf" % text, bbox_inches='tight')
    plt.savefig("%s/differences/map_diff_scenarios_densities.png" % text, bbox_inches='tight')
    plt.show()


def plot_single_map(file, title, outname):
    # ymax_mean = 0
    # ymax_median = 0
    # ymax_std = 0
    # ymax_95th = 0
    # gdf = geopandas.read_file(file)
    # max_gdf = gdf.max()
    # min_gdf = gdf.min()
    # ymax_mean = max(ymax_mean,max_gdf.diff_mean,abs(min_gdf.diff_mean))
    # ymax_median = max(ymax_median,max_gdf.diff_median,abs(min_gdf.diff_median))
    # ymax_std = max(ymax_std,max_gdf.diff_std,abs(min_gdf.diff_std))
    # ymax_95th = max(ymax_95th,max_gdf['diff_95th_percentile'],abs(min_gdf['diff_95th_percentile']))

    sns.set()
    sns.set_style(rc = {'axes.facecolor': '#989898'})

    viridis = plt.cm.get_cmap('PiYG', 256)
    f, ax = plt.subplots(figsize=(6, 4))
    # ax.set_title(title)
    gdf = geopandas.read_file(file)
    print(gdf['diff_mean'])
    
    gdf.plot(ax=ax, column='diff_mean', legend=True, legend_kwds={"label": "difference in people / $m^2$", "orientation": "vertical"},  cmap=viridis, vmin=-ymax_mean, vmax=ymax_mean, linewidth=3)
    # axs[index, 0].legend()
    # for idx, row in gdf.iterrows():
    #     plt.annotate(text=round(row['diff_mean'], 3), xy=(row['geometry'].centroid.x, row['geometry'].centroid.y), horizontalalignment='center', color='blue', fontsize="xx-small")   
    ax.set_xticks([])
    ax.set_yticks([])
    # Get the images on an axis
    # ax.legend(title="people / $m^2$")
    # ax.set_ylabel("Difference in crowdedness in people / $m^2$")
    plt.savefig("%s/differences/" % text + outname + ".pdf", bbox_inches='tight')
    plt.show()


for file in ["%s/differences/cali_full" % text, "%s/differences/cali_no" % text]:
    ymax_mean = 0
    gdf = geopandas.read_file(file)
    max_gdf = gdf.max()
    min_gdf = gdf.min()
    ymax_mean = max(ymax_mean,max_gdf.diff_mean,abs(min_gdf.diff_mean))
plot_single_map("%s/differences/cali_full" % text, 'Calibrated - Full Compliance', "cali_full")
plot_single_map("%s/differences/cali_no" % text, 'Calibrated - No Interventions', "cali_no")

print("done")